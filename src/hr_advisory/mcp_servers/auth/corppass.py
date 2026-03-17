"""CorpPass OAuth 2.1 authorization flow for Singapore government APIs.

CorpPass is the corporate digital identity for businesses in Singapore.
It provides OAuth 2.1 with PKCE for authenticating employers to submit
CPF contributions, IRAS tax filings, MOM occupational data, and other
statutory returns via the GovTech APEX gateway.

Endpoints:
- Authorization: https://saml.corppass.gov.sg/cpauth/login/eservloginpage
- Token: https://api.apex.gov.sg/oauth2/token
- Sandbox: https://sandbox.api.apex.gov.sg/oauth2/token

Reference: https://docs.developer.tech.gov.sg/docs/complete-apex-user-guide/
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import time
import urllib.parse
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.token_store import ExternalTokenManager, get_token_manager
from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration from environment — never hardcoded
# ---------------------------------------------------------------------------

CORPPASS_AUTH_URL = os.environ.get(
    "CORPPASS_AUTH_URL",
    "https://saml.corppass.gov.sg/cpauth/login/eservloginpage",
)
CORPPASS_AUTH_URL_SANDBOX = os.environ.get(
    "CORPPASS_AUTH_URL_SANDBOX",
    "https://stg-saml.corppass.gov.sg/cpauth/login/eservloginpage",
)
APEX_TOKEN_URL = os.environ.get(
    "APEX_TOKEN_URL",
    "https://api.apex.gov.sg/oauth2/token",
)
APEX_TOKEN_URL_SANDBOX = os.environ.get(
    "APEX_TOKEN_URL_SANDBOX",
    "https://sandbox.api.apex.gov.sg/oauth2/token",
)
APEX_REVOKE_URL = os.environ.get(
    "APEX_REVOKE_URL",
    "https://api.apex.gov.sg/oauth2/revoke",
)

# APEX client credentials — from environment
APEX_CLIENT_ID = os.environ.get("APEX_CLIENT_ID", "")
APEX_CLIENT_SECRET = os.environ.get("APEX_CLIENT_SECRET", "")
APEX_APP_ID = os.environ.get("APEX_APP_ID", "")

# CorpPass e-Service ID assigned during OSP registration
CORPPASS_ESERVICE_ID = os.environ.get("CORPPASS_ESERVICE_ID", "")

# Whether to use sandbox endpoints
APEX_USE_SANDBOX = os.environ.get("APEX_USE_SANDBOX", "true").lower() == "true"

# Provider name used consistently in the token store
PROVIDER_NAME = "corppass"

# Token validity window (CorpPass tokens typically valid 30 min)
DEFAULT_TOKEN_EXPIRY = 1800  # 30 minutes


class CorpPassError(Exception):
    """Error during CorpPass authentication flow."""

    def __init__(
        self, message: str, error_code: str = "corppass_error", details: Optional[dict] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class PKCEChallenge:
    """PKCE (Proof Key for Code Exchange) challenge for OAuth 2.1.

    OAuth 2.1 mandates PKCE for all authorization code flows.
    Generates a code_verifier and derives code_challenge using S256.
    """

    def __init__(self):
        # RFC 7636: code_verifier is 43-128 characters from [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
        self.code_verifier = secrets.token_urlsafe(64)[:128]
        digest = hashlib.sha256(self.code_verifier.encode("ascii")).digest()
        self.code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        self.code_challenge_method = "S256"


# ---------------------------------------------------------------------------
# In-memory state store for PKCE + CSRF protection during auth flow
# ---------------------------------------------------------------------------

# Maps state -> {tenant_id, pkce, callback_url, created_at}
_pending_flows: dict[str, dict[str, Any]] = {}

# Expire pending flows after 10 minutes
_FLOW_EXPIRY = 600


def _clean_expired_flows() -> None:
    """Remove expired pending authorization flows."""
    now = time.time()
    expired = [k for k, v in _pending_flows.items() if now - v["created_at"] > _FLOW_EXPIRY]
    for k in expired:
        del _pending_flows[k]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def initiate_auth(
    tenant_id: str,
    callback_url: str,
    scopes: Optional[list[str]] = None,
) -> dict:
    """Build CorpPass authorization URL for the user to visit.

    This starts the OAuth 2.1 + PKCE authorization code flow.
    The tenant's admin navigates to the returned URL, authenticates
    via CorpPass (Singpass for business), and is redirected back
    to callback_url with an authorization code.

    Args:
        tenant_id: Company/tenant ID initiating the connection.
        callback_url: URL where CorpPass redirects after auth.
        scopes: Optional list of APEX API scopes to request.

    Returns:
        Dict with authorization_url, state token, and expiry info.
    """
    _clean_expired_flows()

    if not APEX_CLIENT_ID:
        raise CorpPassError(
            "APEX_CLIENT_ID not configured. Set the environment variable before initiating CorpPass auth.",
            error_code="missing_config",
        )

    # Generate PKCE challenge
    pkce = PKCEChallenge()

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)

    # Default scopes for HR statutory submissions
    if scopes is None:
        scopes = [
            "cpf.submission",
            "iras.ais",
            "mom.oed",
        ]

    # Store flow state for callback verification
    _pending_flows[state] = {
        "tenant_id": tenant_id,
        "pkce": pkce,
        "callback_url": callback_url,
        "scopes": scopes,
        "created_at": time.time(),
    }

    # Build authorization URL
    auth_base = CORPPASS_AUTH_URL_SANDBOX if APEX_USE_SANDBOX else CORPPASS_AUTH_URL

    params = {
        "response_type": "code",
        "client_id": APEX_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": pkce.code_challenge,
        "code_challenge_method": pkce.code_challenge_method,
        # CorpPass-specific: e-Service ID identifies our application
        "esrvcId": CORPPASS_ESERVICE_ID,
        # APEX-specific: app ID for routing
        "app_id": APEX_APP_ID,
        # Nonce for replay protection
        "nonce": secrets.token_urlsafe(16),
    }

    authorization_url = f"{auth_base}?{urllib.parse.urlencode(params)}"

    logger.info(
        "Initiated CorpPass auth for tenant=%s (state=%s...)",
        tenant_id,
        state[:8],
    )

    return {
        "authorization_url": authorization_url,
        "state": state,
        "expires_in": _FLOW_EXPIRY,
        "scopes": scopes,
    }


async def handle_callback(
    auth_code: str,
    state: str,
) -> dict:
    """Exchange authorization code for tokens after CorpPass redirect.

    Validates the state parameter against our pending flows, then
    exchanges the auth code + PKCE verifier for access and refresh tokens.

    Args:
        auth_code: Authorization code from CorpPass callback.
        state: State parameter for CSRF validation.

    Returns:
        Dict with tenant_id, access_token status, scopes, and token expiry.

    Raises:
        CorpPassError: If state is invalid/expired or token exchange fails.
    """
    _clean_expired_flows()

    # Validate state
    flow = _pending_flows.pop(state, None)
    if flow is None:
        raise CorpPassError(
            "Invalid or expired authorization state. Please restart the CorpPass login.",
            error_code="invalid_state",
        )

    tenant_id = flow["tenant_id"]
    pkce: PKCEChallenge = flow["pkce"]
    callback_url = flow["callback_url"]
    scopes = flow["scopes"]

    # Exchange authorization code for tokens via APEX token endpoint
    token_url = APEX_TOKEN_URL_SANDBOX if APEX_USE_SANDBOX else APEX_TOKEN_URL

    token_payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": callback_url,
        "client_id": APEX_CLIENT_ID,
        "client_secret": APEX_CLIENT_SECRET,
        "code_verifier": pkce.code_verifier,
    }

    circuit = get_circuit("corppass")

    async def _exchange() -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                token_url,
                data=token_payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                error_body = resp.text
                logger.error(
                    "CorpPass token exchange failed (HTTP %d): %s",
                    resp.status_code,
                    error_body[:500],
                )
                raise CorpPassError(
                    f"Token exchange failed (HTTP {resp.status_code})",
                    error_code="token_exchange_failed",
                    details={"http_status": resp.status_code, "body": error_body[:500]},
                )
            return resp.json()

    token_data = await circuit.call(_exchange)

    # Store tokens encrypted in the token manager
    manager = get_token_manager()
    manager.store_token(
        tenant_id=tenant_id,
        provider=PROVIDER_NAME,
        token_data={
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in", DEFAULT_TOKEN_EXPIRY),
            "scope": " ".join(scopes),
        },
    )

    # Extract CorpPass-specific claims (UEN, CorpPass user info)
    corppass_info = {
        "uen": token_data.get("userInfo", {}).get("CPEntID", ""),
        "corppass_user_id": token_data.get("userInfo", {}).get("CPUID", ""),
        "entity_name": token_data.get("userInfo", {}).get("CPEntName", ""),
    }

    logger.info(
        "CorpPass auth completed for tenant=%s (UEN=%s)",
        tenant_id,
        corppass_info.get("uen", "unknown"),
    )

    return {
        "status": "connected",
        "tenant_id": tenant_id,
        "provider": PROVIDER_NAME,
        "scopes": scopes,
        "expires_in": token_data.get("expires_in", DEFAULT_TOKEN_EXPIRY),
        "corppass_info": corppass_info,
    }


async def get_valid_token(tenant_id: str) -> str:
    """Get a valid CorpPass access token, auto-refreshing if expired.

    This is the primary method adapters call before making APEX API requests.
    It checks the token store, refreshes if expired, and returns a valid
    bearer token string.

    Args:
        tenant_id: Company/tenant ID.

    Returns:
        Valid access token string.

    Raises:
        CorpPassError: If no token exists or refresh fails.
    """
    manager = get_token_manager()

    # Try cached token first
    token = manager.get_valid_token(tenant_id, PROVIDER_NAME)
    if token:
        return token

    # Attempt refresh
    stored = manager.get_stored_token(tenant_id, PROVIDER_NAME)
    if stored is None:
        raise CorpPassError(
            "No CorpPass connection found. Please connect via the CorpPass authorization flow.",
            error_code="not_connected",
        )

    refresh_token = stored.refresh_token
    if refresh_token is None:
        raise CorpPassError(
            "CorpPass token expired and no refresh token available. Please re-authenticate.",
            error_code="token_expired_no_refresh",
        )

    # Refresh the token
    new_token_data = await _refresh_token(tenant_id, refresh_token)
    return new_token_data["access_token"]


async def _refresh_token(tenant_id: str, refresh_token: str) -> dict:
    """Refresh an expired CorpPass token using the refresh_token grant.

    Args:
        tenant_id: Company/tenant ID.
        refresh_token: The refresh token from the previous token exchange.

    Returns:
        New token data dict.

    Raises:
        CorpPassError: If refresh fails (user must re-authenticate).
    """
    token_url = APEX_TOKEN_URL_SANDBOX if APEX_USE_SANDBOX else APEX_TOKEN_URL

    refresh_payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": APEX_CLIENT_ID,
        "client_secret": APEX_CLIENT_SECRET,
    }

    circuit = get_circuit("corppass")

    async def _do_refresh() -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                token_url,
                data=refresh_payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                logger.error(
                    "CorpPass token refresh failed (HTTP %d) for tenant=%s",
                    resp.status_code,
                    tenant_id,
                )
                raise CorpPassError(
                    "Token refresh failed. Please re-authenticate via CorpPass.",
                    error_code="refresh_failed",
                    details={"http_status": resp.status_code},
                )
            return resp.json()

    token_data = await circuit.call(_do_refresh)

    # Store refreshed tokens
    manager = get_token_manager()
    manager.store_token(
        tenant_id=tenant_id,
        provider=PROVIDER_NAME,
        token_data={
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", refresh_token),
            "expires_in": token_data.get("expires_in", DEFAULT_TOKEN_EXPIRY),
            "scope": token_data.get("scope", ""),
        },
    )

    logger.info("CorpPass token refreshed for tenant=%s", tenant_id)
    return token_data


async def revoke_token(tenant_id: str) -> dict:
    """Revoke CorpPass tokens and disconnect the tenant.

    Args:
        tenant_id: Company/tenant ID.

    Returns:
        Dict with revocation status.
    """
    manager = get_token_manager()
    stored = manager.get_stored_token(tenant_id, PROVIDER_NAME)

    if stored is None:
        return {"status": "not_connected", "tenant_id": tenant_id}

    # Attempt to revoke at APEX if we have a token
    try:
        access_token = stored.access_token
        async with httpx.AsyncClient(timeout=15.0) as client:
            revoke_url = APEX_REVOKE_URL
            await client.post(
                revoke_url,
                data={
                    "token": access_token,
                    "client_id": APEX_CLIENT_ID,
                    "client_secret": APEX_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except Exception:
        # Best effort — still remove local token
        logger.warning("Failed to revoke CorpPass token at APEX for tenant=%s", tenant_id)

    # Remove from local store
    manager.revoke_token(tenant_id, PROVIDER_NAME)

    logger.info("CorpPass disconnected for tenant=%s", tenant_id)
    return {"status": "disconnected", "tenant_id": tenant_id}


def is_connected(tenant_id: str) -> bool:
    """Check if a tenant has an active CorpPass connection."""
    manager = get_token_manager()
    return manager.is_connected(tenant_id, PROVIDER_NAME)


# ---------------------------------------------------------------------------
# Register refresh callback with the token manager
# ---------------------------------------------------------------------------


def _register_refresh_callback() -> None:
    """Register the CorpPass token refresh callback with the global token manager."""
    manager = get_token_manager()

    async def _refresh_cb(tenant_id: str, refresh_token: str) -> dict:
        return await _refresh_token(tenant_id, refresh_token)

    manager.register_refresh_callback(PROVIDER_NAME, _refresh_cb)


# Auto-register on module import
_register_refresh_callback()
