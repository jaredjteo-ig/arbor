"""Google Calendar OAuth flow (T-R055).

Implements:

* ``get_authorization_url(company_id, user_id)`` — builds an OAuth consent
  URL with a signed ``state`` parameter that binds the round-trip to the
  initiating user AND company so a stolen state cannot be replayed against a
  different session (round-13 CRIT-S3).
* ``exchange_code(code, signed_state, expected_user_id)`` — verifies the
  state, asserts the in-flight user matches, exchanges the authorization
  code for tokens, and persists them as a ``GoogleCalendarConnection`` row.
* ``get_credentials(company_id)`` — returns refreshed
  ``google.oauth2.credentials.Credentials`` (auto-refreshes via the stored
  refresh token).
* ``disconnect(company_id)`` — best-effort token revocation + row removal.

Secrets ``GOOGLE_OAUTH_CLIENT_ID`` and ``GOOGLE_OAUTH_CLIENT_SECRET`` are
read from the environment. The ``state`` parameter is HMAC-signed using a
dedicated ``OAUTH_STATE_SECRET`` env var (round-13 H2 — domain separation
from the JWT signing key, fail-fast if unset rather than the previous
``"change-this-in-production"`` fallback).
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


_BAD_DEFAULT_SECRETS = frozenset(
    {
        "",
        "change-this-in-production",
        "change-me",
        "change-this-to-a-random-string-at-least-32-chars",
    }
)


def _oauth_state_secret() -> bytes:
    """Return the secret used to HMAC-sign OAuth state parameters.

    Round-13 H2 fix: this secret is **dedicated** to OAuth state binding
    (no domain-cross with the session JWT signing key) and **fails fast**
    if unset or set to a known-default placeholder. Earlier code fell back
    to ``"change-this-in-production"`` so any deploy with a forgotten env
    var signed state with a publicly-known string — anyone could forge a
    state and connect tokens to any company.

    Reads ``OAUTH_STATE_SECRET`` first; for backwards compatibility falls
    back to ``JWT_SECRET_KEY`` ONLY if that one is also non-default.
    """

    secret = (os.environ.get("OAUTH_STATE_SECRET") or "").strip()
    if secret and secret not in _BAD_DEFAULT_SECRETS:
        return secret.encode("utf-8")

    legacy = (os.environ.get("JWT_SECRET_KEY") or "").strip()
    if legacy and legacy not in _BAD_DEFAULT_SECRETS:
        return legacy.encode("utf-8")

    raise RuntimeError(
        "OAUTH_STATE_SECRET (or JWT_SECRET_KEY as a fallback) must be set to "
        "a non-default value in the environment to use the Google Calendar "
        "integration. Refusing to sign OAuth state with a publicly-known "
        "default — that would let an attacker forge state and bind tokens to "
        "any company."
    )


def _b64url_encode(payload: bytes) -> str:
    return urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padded = text + "=" * (-len(text) % 4)
    return urlsafe_b64decode(padded.encode("ascii"))


def build_signed_state(
    company_id: int, user_id: int, *, now: Optional[float] = None
) -> str:
    """Build a signed ``state`` parameter binding the OAuth callback to
    BOTH ``company_id`` AND ``user_id``.

    Round-13 CRIT-S3 fix: binding to user_id alone (not just company_id)
    means a state stolen / phished from one user cannot be exchanged by a
    different user, even within the same company. The callback verifier
    asserts the in-flight user matches the user that started the flow.

    Format: ``base64url({company_id, user_id, ts, nonce}).base64url(hmac_sha256)``.
    """

    ts = int(now if now is not None else time.time())
    payload = {
        "company_id": int(company_id),
        "user_id": int(user_id),
        "ts": ts,
        # 16 random bytes hex — guards against accidental state reuse if the
        # consent screen is hit twice in the same second.
        "nonce": os.urandom(16).hex(),
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_oauth_state_secret(), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(sig)}"


def verify_signed_state(
    signed_state: str, *, now: Optional[float] = None
) -> tuple[int, int]:
    """Verify a signed state and return ``(company_id, user_id)``.

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

    expected = hmac.new(_oauth_state_secret(), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig):
        raise OAuthStateError("state signature mismatch")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise OAuthStateError(f"state payload is not JSON: {exc}") from exc

    company_id = payload.get("company_id")
    user_id = payload.get("user_id")
    ts = payload.get("ts")
    if (
        not isinstance(company_id, int)
        or not isinstance(user_id, int)
        or not isinstance(ts, int)
    ):
        raise OAuthStateError("state payload missing required fields")

    current = int(now if now is not None else time.time())
    if current - ts > _STATE_TTL_SECONDS:
        raise OAuthStateError("state expired")
    if ts - current > 60:  # clock skew leeway
        raise OAuthStateError("state issued in the future")

    return company_id, user_id


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


def get_authorization_url(company_id: int, user_id: int) -> dict[str, str]:
    """Return the URL the user should be redirected to in order to grant access.

    Returns ``{"auth_url": ..., "state": ...}``.  ``state`` is signed with
    ``OAUTH_STATE_SECRET`` and binds BOTH ``company_id`` AND ``user_id``;
    the callback verifier asserts the in-flight session user matches, so a
    state stolen / phished from one user cannot be exchanged by anyone else
    (round-13 CRIT-S3).
    """

    state = build_signed_state(company_id, user_id)
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
    """Build the persistable row from a Credentials object.

    Round-13 H1: ``access_token`` and ``refresh_token`` are encrypted at
    rest using the platform's shared Fernet key (``SALARY_ENCRYPTION_KEY``)
    so a DB leak doesn't directly expose third-party OAuth credentials.
    Tests can opt out by leaving the env unset; in that case ``encrypt_field``
    returns the value unchanged (development-only behaviour, matched by the
    rest of the platform's PII fields).
    """
    from hr_advisory.security.encryption import encrypt_field

    expires_at = ""
    expiry = getattr(creds, "expiry", None)
    if expiry is not None:
        # google.oauth2.credentials.Credentials.expiry is a naive UTC datetime
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        expires_at = expiry.astimezone(timezone.utc).isoformat()

    raw_access = getattr(creds, "token", "") or ""
    raw_refresh = getattr(creds, "refresh_token", "") or ""

    return {
        "company_id": int(company_id),
        "access_token": encrypt_field(raw_access),
        "refresh_token": encrypt_field(raw_refresh),
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


def exchange_code(
    code: str,
    signed_state: str,
    *,
    expected_user_id: int,
    connected_by: Optional[int] = None,
) -> dict[str, Any]:
    """Exchange an OAuth code for tokens and persist them.

    Verifies the signed state first AND asserts that ``expected_user_id``
    (the user the callback request was authenticated as) matches the
    user_id baked into the state. This is the round-13 CRIT-S3 defence:
    even if someone steals a state from a victim's auth-url response, they
    cannot redeem it because the callback now requires authentication and
    rejects state issued for a different user.

    Returns the persisted record dict.
    """

    company_id, state_user_id = verify_signed_state(signed_state)

    if state_user_id != int(expected_user_id):
        raise OAuthStateError(
            "state was issued for a different user than the one completing "
            "the OAuth callback"
        )

    flow = _build_flow(state=signed_state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    record = _credentials_to_record(
        creds,
        company_id=company_id,
        connected_by=int(connected_by if connected_by is not None else expected_user_id),
    )
    return _persist_connection(record)


def _record_to_credentials(record: dict[str, Any]):
    """Hydrate ``google.oauth2.credentials.Credentials`` from a persisted row.

    Round-13 H1: tokens are stored encrypted via Fernet; this helper
    decrypts at the read boundary. ``decrypt_field`` is tolerant of
    plaintext input so a row written before the encryption fix still
    works without a migration.
    """
    from google.oauth2.credentials import Credentials  # type: ignore

    from hr_advisory.security.encryption import decrypt_field

    return Credentials(
        token=decrypt_field(record.get("access_token") or "") or None,
        refresh_token=decrypt_field(record.get("refresh_token") or "") or None,
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
            # Log exception type only — Google client errors can include the
            # bearer token in their string form. Round-13 H5/H7.
            logger.warning(
                "Failed to refresh Google Calendar credentials for company %s: %s",
                company_id,
                type(exc).__name__,
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
    # Round-13 H1: stored refresh_token is encrypted; decrypt before sending
    # to Google's revoke endpoint. ``decrypt_field`` is tolerant of plaintext
    # so a row written before encryption shipped still works.
    from hr_advisory.security.encryption import decrypt_field

    raw_refresh = decrypt_field(record.get("refresh_token") or "")
    if raw_refresh:
        try:
            import httpx

            httpx.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": raw_refresh},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5.0,
            )
        except Exception as exc:  # noqa: BLE001
            # Log type only — never the value, which is the OAuth token. This
            # closes round-13 H5 / H7 (token bytes appearing in tracebacks).
            logger.info(
                "Could not revoke Google Calendar token for company %s: %s",
                company_id,
                type(exc).__name__,
            )

    rec_id = record.get("id")
    if rec_id is not None:
        dataflow_crud.delete("GoogleCalendarConnection", rec_id)
    return True
