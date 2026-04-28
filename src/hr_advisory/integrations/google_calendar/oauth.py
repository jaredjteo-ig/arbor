"""Google Calendar OAuth flow (T-R055).

Implements:

* ``get_authorization_url(company_id)`` — builds an OAuth consent URL with a
  signed ``state`` parameter so a spoofed callback cannot connect a different
  company's tokens.
* ``exchange_code(code, signed_state)`` — verifies the state, exchanges the
  authorization code for tokens, and persists them as a
  ``GoogleCalendarConnection`` row.
* ``get_credentials(company_id)`` — returns refreshed
  ``google.oauth2.credentials.Credentials`` (auto-refreshes via the stored
  refresh token).
* ``disconnect(company_id)`` — best-effort token revocation + row removal.

Secrets ``GOOGLE_OAUTH_CLIENT_ID`` and ``GOOGLE_OAUTH_CLIENT_SECRET`` are read
from the environment.  ``JWT_SECRET_KEY`` is used to sign the ``state``
parameter so cross-company hijack of the OAuth callback is rejected.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "GOOGLE_CALENDAR_SCOPE",
    "OAuthStateError",
    "build_signed_state",
    "verify_signed_state",
    "get_authorization_url",
    "exchange_code",
    "get_credentials",
    "disconnect",
    "_load_connection",
]


# Per the brief: only the scope required to manage events.
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"

# 15-minute window for the signed state to be exchanged.  Plenty for a normal
# OAuth round-trip and short enough that replay is meaningless.
_STATE_TTL_SECONDS = 15 * 60


class OAuthStateError(ValueError):
    """Raised when the OAuth state parameter is missing, malformed, or invalid."""


def _jwt_secret() -> bytes:
    """Return the JWT secret as bytes.  Same secret used everywhere else in Arbor."""

    secret = os.environ.get("JWT_SECRET_KEY", "change-this-in-production")
    return secret.encode("utf-8")


def _b64url_encode(payload: bytes) -> str:
    return urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padded = text + "=" * (-len(text) % 4)
    return urlsafe_b64decode(padded.encode("ascii"))


def build_signed_state(company_id: int, *, now: Optional[float] = None) -> str:
    """Build a signed ``state`` parameter binding the OAuth callback to ``company_id``.

    Format: ``base64url({company_id, ts, nonce}).base64url(hmac_sha256)``.
    """

    ts = int(now if now is not None else time.time())
    payload = {
        "company_id": int(company_id),
        "ts": ts,
        # 16 random bytes hex — guards against accidental state reuse if the
        # consent screen is hit twice in the same second.
        "nonce": os.urandom(16).hex(),
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_jwt_secret(), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(sig)}"


def verify_signed_state(signed_state: str, *, now: Optional[float] = None) -> int:
    """Verify a signed state and return the bound ``company_id``.

    Raises ``OAuthStateError`` on any tampering, expiry, or malformed input.
    """

    if not signed_state or "." not in signed_state:
        raise OAuthStateError("malformed state")
    try:
        payload_b64, sig_b64 = signed_state.split(".", 1)
        payload_bytes = _b64url_decode(payload_b64)
        sig = _b64url_decode(sig_b64)
    except Exception as exc:  # pragma: no cover - defensive
        raise OAuthStateError(f"could not decode state: {exc}") from exc

    expected = hmac.new(_jwt_secret(), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig):
        raise OAuthStateError("state signature mismatch")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise OAuthStateError(f"state payload is not JSON: {exc}") from exc

    company_id = payload.get("company_id")
    ts = payload.get("ts")
    if not isinstance(company_id, int) or not isinstance(ts, int):
        raise OAuthStateError("state payload missing required fields")

    current = int(now if now is not None else time.time())
    if current - ts > _STATE_TTL_SECONDS:
        raise OAuthStateError("state expired")
    if ts - current > 60:  # clock skew leeway
        raise OAuthStateError("state issued in the future")

    return company_id


def _redirect_uri() -> str:
    """The redirect URI registered with Google.

    Read from ``GOOGLE_OAUTH_REDIRECT_URI`` so dev/staging/prod can differ.
    Falls back to a localhost dev URL.
    """

    return os.environ.get(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://localhost:8001/integrations/google-calendar/callback",
    )


def _client_config() -> dict[str, Any]:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set "
            "in the environment to use the Google Calendar integration.",
        )
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_redirect_uri()],
        }
    }


def _build_flow(state: Optional[str] = None):
    """Construct a ``Flow`` from the installed ``google-auth-oauthlib`` library.

    Imported lazily so unit tests that patch ``google_auth_oauthlib.flow.Flow``
    do not require the package at module import time.
    """

    from google_auth_oauthlib.flow import Flow  # type: ignore

    flow = Flow.from_client_config(
        _client_config(),
        scopes=[GOOGLE_CALENDAR_SCOPE],
        state=state,
    )
    flow.redirect_uri = _redirect_uri()
    return flow


def get_authorization_url(company_id: int) -> dict[str, str]:
    """Return the URL the user should be redirected to in order to grant access.

    Returns ``{"auth_url": ..., "state": ...}``.  ``state`` is signed with
    ``JWT_SECRET_KEY`` so a spoofed callback cannot connect tokens to a
    different company.
    """

    state = build_signed_state(company_id)
    flow = _build_flow(state=state)
    auth_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # ``returned_state`` from google-auth-oauthlib equals the state we passed
    # in.  We rely on our own value to keep semantics explicit.
    return {"auth_url": auth_url, "state": state, "google_state": returned_state}


def _credentials_to_record(creds, company_id: int, connected_by: int) -> dict[str, Any]:
    expires_at = ""
    expiry = getattr(creds, "expiry", None)
    if expiry is not None:
        # google.oauth2.credentials.Credentials.expiry is a naive UTC datetime
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        expires_at = expiry.astimezone(timezone.utc).isoformat()

    return {
        "company_id": int(company_id),
        "access_token": getattr(creds, "token", "") or "",
        "refresh_token": getattr(creds, "refresh_token", "") or "",
        "expires_at": expires_at,
        "scope": " ".join(getattr(creds, "scopes", []) or []),
        "token_uri": getattr(creds, "token_uri", "https://oauth2.googleapis.com/token"),
        "connected_by": int(connected_by),
        "status": "connected",
    }


def _load_connection(company_id: int) -> Optional[dict[str, Any]]:
    """Return the GoogleCalendarConnection row for ``company_id`` (or None)."""

    from hr_advisory.services import dataflow_crud

    rows = dataflow_crud.list_records(
        "GoogleCalendarConnection",
        {"company_id": int(company_id)},
        limit=1,
    )
    return rows[0] if rows else None


def _persist_connection(record: dict[str, Any]) -> dict[str, Any]:
    """Upsert a connection row keyed by ``company_id``."""

    from hr_advisory.services import dataflow_crud

    existing = _load_connection(record["company_id"])
    if existing:
        rec_id = existing.get("id")
        # Don't blow away the webhook channel if we are just refreshing tokens.
        merged = {**existing, **record}
        dataflow_crud.update("GoogleCalendarConnection", rec_id, merged)
        return {**merged, "id": rec_id}
    return dataflow_crud.create("GoogleCalendarConnection", record)


def exchange_code(code: str, signed_state: str, *, connected_by: int = 0) -> dict[str, Any]:
    """Exchange an OAuth code for tokens and persist them.

    Verifies the signed state first so an attacker cannot swap the company id.
    Returns the persisted record dict.
    """

    company_id = verify_signed_state(signed_state)

    flow = _build_flow(state=signed_state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    record = _credentials_to_record(creds, company_id=company_id, connected_by=connected_by)
    return _persist_connection(record)


def _record_to_credentials(record: dict[str, Any]):
    """Hydrate ``google.oauth2.credentials.Credentials`` from a persisted row."""

    from google.oauth2.credentials import Credentials  # type: ignore

    return Credentials(
        token=record.get("access_token") or None,
        refresh_token=record.get("refresh_token") or None,
        token_uri=record.get("token_uri") or "https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
        scopes=[s for s in (record.get("scope") or "").split() if s] or [GOOGLE_CALENDAR_SCOPE],
    )


def get_credentials(company_id: int):
    """Return refreshed Google ``Credentials`` for ``company_id`` (or None)."""

    record = _load_connection(company_id)
    if not record:
        return None

    creds = _record_to_credentials(record)

    expires_at = record.get("expires_at") or ""
    needs_refresh = False
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            needs_refresh = exp_dt <= datetime.now(timezone.utc)
        except Exception:  # noqa: BLE001
            needs_refresh = True
    else:
        needs_refresh = True

    if needs_refresh and creds.refresh_token:
        try:
            from google.auth.transport.requests import Request  # type: ignore

            creds.refresh(Request())
            # Persist the freshly minted access token.
            record.update(_credentials_to_record(creds, company_id, record.get("connected_by", 0)))
            from hr_advisory.services import dataflow_crud

            dataflow_crud.update("GoogleCalendarConnection", record.get("id"), record)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to refresh Google Calendar credentials for company %s: %s",
                company_id,
                exc,
            )
            return None
    return creds


def disconnect(company_id: int) -> bool:
    """Best-effort revoke + delete the connection row.  Returns True if a row was removed."""

    from hr_advisory.services import dataflow_crud

    record = _load_connection(company_id)
    if not record:
        return False

    # Try to revoke at Google.  Failure is non-fatal — we still want the local
    # row gone so the user can reconnect cleanly.
    refresh_token = record.get("refresh_token")
    if refresh_token:
        try:
            import httpx

            httpx.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": refresh_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5.0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "Could not revoke Google Calendar token for company %s: %s",
                company_id,
                exc,
            )

    rec_id = record.get("id")
    if rec_id is not None:
        dataflow_crud.delete("GoogleCalendarConnection", rec_id)
    return True
