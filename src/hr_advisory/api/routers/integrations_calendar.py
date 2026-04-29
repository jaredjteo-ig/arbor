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
import re
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


# Round-13 CRIT-S2: only these schemes/hosts are allowed as the webhook URL
# we register with Google. ``ARBOR_API_URL`` flows from server config but
# without validation an env-injection attacker (or a misconfigured deploy)
# could redirect every Google push notification to a third-party host.
#
# Production: must be ``https://`` and the host must end in one of the
# Foundation-controlled domains. Localhost is permitted ONLY for dev
# (http://localhost:PORT or http://127.0.0.1:PORT). Anything else is
# rejected so we fail loudly at OAuth-callback time rather than silently
# leaking interview data to an attacker.
_ALLOWED_WEBHOOK_HOSTS_PROD = (".terrene.foundation", ".terrene.dev")
_LOCALHOST_RE = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")


def _validate_webhook_base_url(url: str) -> str:
    """Validate ``ARBOR_API_URL`` and return a normalised value.

    Raises ``ValueError`` (caller turns into 503) if the URL is not on the
    allowlist. Localhost is permitted only when ``APP_ENV`` is ``development``
    or unset.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        raise ValueError("ARBOR_API_URL must be set to register Calendar webhooks")

    app_env = os.environ.get("APP_ENV", "development").strip().lower()

    if _LOCALHOST_RE.match(cleaned):
        if app_env in ("production", "prod"):
            raise ValueError(
                "ARBOR_API_URL points at localhost but APP_ENV is production"
            )
        return cleaned.rstrip("/")

    if not cleaned.startswith("https://"):
        raise ValueError(
            "ARBOR_API_URL must use https:// (or http://localhost in dev)"
        )

    # Pull the host out without depending on urllib parsing edge cases.
    after_scheme = cleaned[len("https://"):]
    host = after_scheme.split("/", 1)[0].split(":", 1)[0].lower()
    if not any(host.endswith(suffix) for suffix in _ALLOWED_WEBHOOK_HOSTS_PROD):
        raise ValueError(
            f"ARBOR_API_URL host '{host}' is not on the webhook allowlist "
            f"(allowed suffixes: {_ALLOWED_WEBHOOK_HOSTS_PROD})"
        )

    return cleaned.rstrip("/")


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
        return oauth.get_authorization_url(company_id, user_id)
    except RuntimeError as exc:
        # GOOGLE_OAUTH_CLIENT_ID/SECRET missing — surface a clear error to the
        # frontend so the user knows the integration has not been configured.
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/callback")
async def google_calendar_callback(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> HTMLResponse:
    """Handle the OAuth redirect from Google.

    Round-13 CRIT-S3: this endpoint NOW REQUIRES the same authenticated
    session that started the flow. Combined with state HMAC binding to
    user_id, this prevents an attacker who steals a state from another
    user (or who is unauthenticated) from completing the OAuth flow and
    binding their own Google tokens to the victim company.

    Practical effect: the auth-url popup must be opened from a logged-in
    Arbor browser session; the same browser receives the redirect, so the
    auth cookie travels with the callback request automatically.
    """

    code = request.query_params.get("code")
    signed_state = request.query_params.get("state", "")
    error = request.query_params.get("error")

    if error:
        logger.info(
            "Google Calendar OAuth callback error: %s", error
        )
        from html import escape as _esc

        return HTMLResponse(
            content=(
                "<html><body><h2>Google Calendar connection cancelled</h2>"
                f"<p>{_esc(error)}</p></body></html>"
            ),
            status_code=400,
        )

    if not code or not signed_state:
        raise HTTPException(status_code=400, detail="Missing code or state in callback.")

    callback_user_id = int(current_user.get("sub", 0))

    try:
        record = oauth.exchange_code(
            code=code,
            signed_state=signed_state,
            expected_user_id=callback_user_id,
        )
    except oauth.OAuthStateError as exc:
        logger.warning("Rejected Google Calendar OAuth callback: %s", exc)
        raise HTTPException(status_code=400, detail=f"Invalid state: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to exchange Google Calendar OAuth code")
        raise HTTPException(status_code=502, detail="Could not exchange OAuth code with Google.") from exc

    # Best-effort: register a webhook so Google pushes us updates.
    # Round-13 CRIT-S2: validate ARBOR_API_URL against an https-allowlist
    # (or http://localhost in dev) so an env-injection or misconfigured
    # deploy can't redirect Google's push notifications to a third-party
    # host. If the URL is invalid we skip webhook registration entirely
    # rather than register a poisoned URL — Calendar sync still works
    # one-way (Arbor → Google) until ARBOR_API_URL is fixed.
    raw_webhook_base = os.environ.get("ARBOR_API_URL", "http://localhost:8001")
    watch_result = None
    try:
        webhook_base = _validate_webhook_base_url(raw_webhook_base)
    except ValueError as exc:
        logger.warning(
            "Skipping Calendar webhook registration — ARBOR_API_URL invalid: %s",
            exc,
        )
        webhook_base = None
        channel_id = ""
        channel_token = ""

    if webhook_base:
        webhook_url = f"{webhook_base}/integrations/google-calendar/webhook"
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
# Watch refresh (S3-T2)
# --------------------------------------------------------------------------
#
# Google Calendar webhook channels expire after 7 days. Without an active
# refresh, push notifications silently die a week after a customer first
# connects. This endpoint re-watches every connection whose
# `channel_expiration` is within 24 hours of expiry.
#
# Operationally this should be called by a cron job (or admin-triggered
# manually). The endpoint is admin-protected; idempotent — running it
# every 6 hours is safe.


_WATCH_REFRESH_WINDOW_MS = 24 * 60 * 60 * 1000  # 24 hours in ms


def _channel_expires_within(connection: dict, window_ms: int = _WATCH_REFRESH_WINDOW_MS) -> bool:
    """Return True if `channel_expiration` is within `window_ms` of now.

    Google returns `expiration` as a Unix-epoch millisecond integer (string-
    serialized). Missing / unparseable values count as "expired" so the
    refresh proactively re-watches dormant connections.
    """
    raw = connection.get("channel_expiration", "")
    if not raw:
        return True
    try:
        expiration_ms = int(raw)
    except (TypeError, ValueError):
        return True
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return (expiration_ms - now_ms) <= window_ms


@router.post("/refresh-watches")
async def refresh_watches(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Re-watch any connection whose channel expires within 24 hours.

    Owner / hr_manager scoped — refresh runs ONLY for the caller's company.
    A platform-wide cron job should iterate companies separately.

    Returns a summary of {refreshed, skipped, failed} counts so the
    operator can see what happened.
    """

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"gcal_refresh:{user_id}",
        max_requests=20,
        window_seconds=60,
        action_name="refresh Calendar watches",
    )

    rows = dataflow_crud.list_records(
        "GoogleCalendarConnection",
        {"company_id": company_id},
    )

    raw_webhook_base = os.environ.get("ARBOR_API_URL", "http://localhost:8001")
    try:
        webhook_base = _validate_webhook_base_url(raw_webhook_base)
    except ValueError as exc:
        logger.warning(
            "refresh_watches skipping all rows — ARBOR_API_URL invalid: %s", exc
        )
        return {"refreshed": 0, "skipped": 0, "failed": len(rows), "reason": "invalid_webhook_url"}

    webhook_url = f"{webhook_base}/integrations/google-calendar/webhook"

    refreshed = 0
    skipped = 0
    failed = 0
    for row in rows:
        if not _channel_expires_within(row):
            skipped += 1
            continue
        new_channel_id = secrets.token_urlsafe(24)
        new_channel_token = secrets.token_urlsafe(32)
        watch_result = sync.watch_events(
            company_id=int(row["company_id"]),
            channel_id=new_channel_id,
            channel_token=new_channel_token,
            webhook_url=webhook_url,
        )
        if not watch_result:
            failed += 1
            logger.warning(
                "refresh_watches failed for connection_id=%s company_id=%s",
                row.get("id"),
                row.get("company_id"),
            )
            continue
        try:
            dataflow_crud.update(
                "GoogleCalendarConnection",
                row.get("id"),
                {
                    "channel_id": new_channel_id,
                    "channel_token": new_channel_token,
                    "channel_resource_id": watch_result.get("resourceId", ""),
                    "channel_expiration": watch_result.get("expiration", ""),
                },
            )
            refreshed += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "refresh_watches persistence failed for connection_id=%s: %s",
                row.get("id"),
                exc,
            )
            failed += 1

    return {
        "refreshed": refreshed,
        "skipped": skipped,
        "failed": failed,
    }


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

    # S3-T8d: webhook body cap. Google Calendar push notifications are
    # always tiny (an empty body or a few hundred bytes). Anything over
    # 64 KB is either a misconfigured proxy or a hostile probe attempting
    # to OOM the worker. Reject early to keep memory bounded.
    _CALENDAR_WEBHOOK_MAX_BYTES = 64 * 1024
    content_length_header = request.headers.get("content-length", "")
    try:
        declared_length = int(content_length_header)
    except (TypeError, ValueError):
        declared_length = 0
    if declared_length and declared_length > _CALENDAR_WEBHOOK_MAX_BYTES:
        logger.warning(
            "Google Calendar webhook rejected — body exceeds 64KB cap "
            "(declared=%s, channel=%s)",
            declared_length,
            channel_id,
        )
        raise HTTPException(status_code=413, detail="Webhook body too large.")

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

    # Round-13 H3: also verify the resource id matches what Google handed us
    # at watch-creation time. A stale token leaked from a rotated channel
    # cannot be replayed against a different channel's resource. Google's
    # X-Goog-Resource-ID is the calendar identifier we subscribed to.
    expected_resource_id = str(record.get("channel_resource_id", ""))
    if expected_resource_id and resource_id and not secrets.compare_digest(
        expected_resource_id, resource_id
    ):
        logger.warning(
            "Google Calendar webhook resource-id mismatch (channel=%s, expected=%s, got=%s)",
            channel_id,
            expected_resource_id,
            resource_id,
        )
        raise HTTPException(status_code=401, detail="Invalid resource id.")

    company_id = int(record["company_id"])

    if resource_state == "sync":
        # Initial sync notification — nothing to patch.
        return JSONResponse({"ok": True})

    # We don't get the event id directly; pull the recent change list.
    # The body is empty for Calendar push; we must call ``events.list`` with
    # ``updatedMin`` or look up by ``resourceId`` -> calendar mapping.  In
    # practice the ``X-Goog-Resource-ID`` is the resource being watched (the
    # whole calendar), and we discover changes through ``events.list``.

    # Webhook body decode — Google may send empty bodies (the typical
    # case) or malformed bytes if a downstream proxy mangled the request.
    # Either way we proceed without a payload; surface unexpected
    # exception classes in the debug log rather than swallow silently.
    try:
        body_text = (await request.body()).decode("utf-8", errors="replace")
    except (UnicodeDecodeError, ConnectionError):
        body_text = ""
    except Exception as exc:  # noqa: BLE001
        logger.debug("calendar webhook body read non-decode failure: %s", type(exc).__name__)
        body_text = ""
    payload: dict[str, Any] = {}
    if body_text:
        try:
            payload = json.loads(body_text)
        except Exception:  # noqa: BLE001
            payload = {}

    google_event_id = payload.get("id") or payload.get("eventId") or ""

    # S3-T1: Calendar push notifications are typically empty-bodied — we
    # don't get the changed event id directly. Walk the diff via syncToken.
    # On 410 Gone we drop the persisted token and the next webhook does a
    # full re-fetch (paying the one-time cost so subsequent webhooks are
    # incremental again).
    persisted_sync_token = str(record.get("sync_token", "") or "")
    events, new_sync_token = sync.list_changes_since(
        company_id=company_id, sync_token=persisted_sync_token
    )

    if new_sync_token == sync.SYNC_TOKEN_INVALID:
        # Reset the token so the NEXT webhook does a full resync.
        dataflow_crud.update(
            "GoogleCalendarConnection",
            record.get("id"),
            {
                "sync_token": "",
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return JSONResponse({"ok": True, "sync_token_reset": True})

    patched = 0
    for event in events:
        evt_id = event.get("id")
        if not evt_id:
            continue
        interview = _interview_for_event(evt_id, company_id)
        if not interview:
            # The event isn't tied to an Arbor interview — could be a
            # personal event on the same calendar; skip.
            continue
        updates = _patch_interview_from_event(interview, event)
        if updates:
            dataflow_crud.update("InterviewSchedule", interview.get("id"), updates)
            patched += 1

    # If a single-event payload also arrived (some older Google clients
    # emit one), preserve the legacy single-event patch path so behaviour
    # doesn't regress.
    if google_event_id and not events:
        single_event = sync.fetch_event(company_id, google_event_id)
        if single_event:
            interview = _interview_for_event(google_event_id, company_id)
            if interview:
                updates = _patch_interview_from_event(interview, single_event)
                if updates:
                    dataflow_crud.update("InterviewSchedule", interview.get("id"), updates)
                    patched += 1

    persistence_updates: dict[str, Any] = {
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }
    if new_sync_token:
        persistence_updates["sync_token"] = new_sync_token
    dataflow_crud.update(
        "GoogleCalendarConnection",
        record.get("id"),
        persistence_updates,
    )

    return JSONResponse(
        {
            "ok": True,
            "resource_state": resource_state,
            "resource_id": resource_id,
            "patched": patched,
        }
    )
