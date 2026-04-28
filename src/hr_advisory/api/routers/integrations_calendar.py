"""Google Calendar integration endpoints (T-R055).

Routes (mounted under ``/integrations/google-calendar``):

* ``GET  /auth-url``     — return the OAuth consent URL
* ``GET  /callback``     — handle the OAuth redirect (verifies signed state)
* ``GET  /status``       — connection status for the current company
* ``POST /disconnect``   — revoke + delete the stored connection
* ``POST /webhook``      — Google push-notification receiver (channel-token auth)
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hr_advisory.api.middleware.auth_middleware import require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.integrations.google_calendar import oauth, sync
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _connection_for(company_id: int) -> dict[str, Any] | None:
    return oauth._load_connection(company_id)


def _connection_summary(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {
            "connected": False,
            "expires_at": None,
            "last_synced_at": None,
            "scope": None,
        }
    return {
        "connected": (record.get("status", "connected") == "connected"),
        "expires_at": record.get("expires_at") or None,
        "last_synced_at": record.get("last_synced_at") or None,
        "scope": record.get("scope") or None,
        "channel_id": record.get("channel_id") or None,
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get("/auth-url")
async def google_calendar_auth_url(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Return the Google OAuth consent URL for this company."""

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"gcal_auth_url:{user_id}",
        max_requests=10,
        window_seconds=60,
        action_name="generate Google Calendar auth URL",
    )

    try:
        return oauth.get_authorization_url(company_id)
    except RuntimeError as exc:
        # GOOGLE_OAUTH_CLIENT_ID/SECRET missing — surface a clear error to the
        # frontend so the user knows the integration has not been configured.
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/callback")
async def google_calendar_callback(request: Request) -> HTMLResponse:
    """Handle the OAuth redirect from Google.

    Validates the signed ``state`` (binds the callback to a specific company),
    exchanges the code for tokens, and renders a small HTML page that closes
    the popup window and notifies the parent tab via ``postMessage``.
    """

    code = request.query_params.get("code")
    signed_state = request.query_params.get("state", "")
    error = request.query_params.get("error")

    if error:
        logger.info("Google Calendar OAuth callback error: %s", error)
        return HTMLResponse(
            content=f"<html><body><h2>Google Calendar connection cancelled</h2><p>{error}</p></body></html>",
            status_code=400,
        )

    if not code or not signed_state:
        raise HTTPException(status_code=400, detail="Missing code or state in callback.")

    try:
        record = oauth.exchange_code(code=code, signed_state=signed_state)
    except oauth.OAuthStateError as exc:
        logger.warning("Rejected Google Calendar OAuth callback: %s", exc)
        raise HTTPException(status_code=400, detail=f"Invalid state: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to exchange Google Calendar OAuth code")
        raise HTTPException(status_code=502, detail="Could not exchange OAuth code with Google.") from exc

    # Best-effort: register a webhook so Google pushes us updates.
    webhook_base = os.environ.get("ARBOR_API_URL", "http://localhost:8001")
    webhook_url = f"{webhook_base.rstrip('/')}/integrations/google-calendar/webhook"
    channel_id = secrets.token_urlsafe(24)
    channel_token = secrets.token_urlsafe(32)
    watch_result = sync.watch_events(
        company_id=int(record["company_id"]),
        channel_id=channel_id,
        channel_token=channel_token,
        webhook_url=webhook_url,
    )
    if watch_result:
        try:
            dataflow_crud.update(
                "GoogleCalendarConnection",
                record.get("id"),
                {
                    "channel_id": channel_id,
                    "channel_token": channel_token,
                    "channel_resource_id": watch_result.get("resourceId", ""),
                    "channel_expiration": watch_result.get("expiration", ""),
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist Google Calendar webhook channel: %s", exc)

    return HTMLResponse(
        content=(
            "<html><body><h2>Google Calendar connected</h2>"
            "<p>You may close this tab.</p>"
            "<script>"
            "if (window.opener) {"
            "window.opener.postMessage({source:'arbor',event:'google_calendar_connected'},'*');"
            "}"
            "window.close();"
            "</script></body></html>"
        ),
        status_code=200,
    )


@router.get("/status")
async def google_calendar_status(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Return whether Google Calendar is connected for the current company."""

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    record = _connection_for(company_id)
    return _connection_summary(record)


@router.post("/disconnect")
async def google_calendar_disconnect(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Revoke the OAuth grant and delete the stored connection."""

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"gcal_disconnect:{user_id}",
        max_requests=10,
        window_seconds=60,
        action_name="disconnect Google Calendar",
    )

    removed = oauth.disconnect(company_id)
    return {"disconnected": removed}


# --------------------------------------------------------------------------
# Webhook
# --------------------------------------------------------------------------


def _interview_for_event(google_event_id: str, company_id: int) -> dict[str, Any] | None:
    """Find the InterviewSchedule row that owns ``google_event_id``."""

    rows = dataflow_crud.list_records(
        "InterviewSchedule",
        {"company_id": int(company_id), "google_event_id": google_event_id},
        limit=1,
    )
    return rows[0] if rows else None


def _patch_interview_from_event(interview: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Project a Google Calendar event onto an InterviewSchedule update dict."""

    updates: dict[str, Any] = {}

    location = event.get("location")
    if location is not None and location != interview.get("location"):
        updates["location"] = location

    start = (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get("date")
    if start and start != interview.get("scheduled_at"):
        updates["scheduled_at"] = start

    if event.get("status") == "cancelled" and interview.get("status") != "cancelled":
        updates["status"] = "cancelled"

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updates


@router.post("/webhook")
async def google_calendar_webhook(request: Request):
    """Receive Google Calendar push notifications.

    Authenticated via the ``X-Goog-Channel-Token`` header which we generated
    when subscribing.  We look up the matching ``GoogleCalendarConnection``
    row by channel id, fetch the changed event, and patch the matching
    ``InterviewSchedule`` row.
    """

    channel_id = request.headers.get("X-Goog-Channel-ID", "")
    channel_token = request.headers.get("X-Goog-Channel-Token", "")
    resource_state = request.headers.get("X-Goog-Resource-State", "")
    resource_id = request.headers.get("X-Goog-Resource-ID", "")

    if not channel_id or not channel_token:
        raise HTTPException(status_code=400, detail="Missing channel headers.")

    rows = dataflow_crud.list_records(
        "GoogleCalendarConnection",
        {"channel_id": channel_id},
        limit=1,
    )
    if not rows:
        # Unknown channel — return 200 so Google stops retrying, but don't act.
        logger.info("Google Calendar webhook for unknown channel %s", channel_id)
        return JSONResponse({"ok": True})

    record = rows[0]
    if not secrets.compare_digest(str(record.get("channel_token", "")), channel_token):
        logger.warning("Google Calendar webhook channel-token mismatch (channel=%s)", channel_id)
        raise HTTPException(status_code=401, detail="Invalid channel token.")

    company_id = int(record["company_id"])

    if resource_state == "sync":
        # Initial sync notification — nothing to patch.
        return JSONResponse({"ok": True})

    # We don't get the event id directly; pull the recent change list.
    # The body is empty for Calendar push; we must call ``events.list`` with
    # ``updatedMin`` or look up by ``resourceId`` -> calendar mapping.  In
    # practice the ``X-Goog-Resource-ID`` is the resource being watched (the
    # whole calendar), and we discover changes through ``events.list``.

    try:
        body_text = (await request.body()).decode("utf-8", errors="replace")
    except Exception:
        body_text = ""
    payload: dict[str, Any] = {}
    if body_text:
        try:
            payload = json.loads(body_text)
        except Exception:  # noqa: BLE001
            payload = {}

    google_event_id = payload.get("id") or payload.get("eventId") or ""
    if not google_event_id:
        # No event id in the body — best we can do is mark the connection as
        # touched so the next sync run will reconcile.
        dataflow_crud.update(
            "GoogleCalendarConnection",
            record.get("id"),
            {"last_synced_at": datetime.now(timezone.utc).isoformat()},
        )
        return JSONResponse({"ok": True})

    event = sync.fetch_event(company_id, google_event_id)
    if not event:
        return JSONResponse({"ok": True})

    interview = _interview_for_event(google_event_id, company_id)
    if not interview:
        return JSONResponse({"ok": True})

    updates = _patch_interview_from_event(interview, event)
    if updates:
        dataflow_crud.update("InterviewSchedule", interview.get("id"), updates)

    dataflow_crud.update(
        "GoogleCalendarConnection",
        record.get("id"),
        {"last_synced_at": datetime.now(timezone.utc).isoformat()},
    )

    return JSONResponse({"ok": True, "resource_state": resource_state, "resource_id": resource_id})
