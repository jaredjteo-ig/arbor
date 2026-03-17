"""Zoho Books API adapter.

Handles OAuth 2.0 authentication, chart of accounts retrieval,
and journal posting for payroll and claims.

Zoho Books API docs: https://www.zoho.com/books/api/v3/
Rate limits: 2,500 calls/day per organization.
Aggressive caching required due to low daily limit.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.token_store import get_token_manager
from hr_advisory.mcp_servers.resilience import check_rate_limit, get_circuit

logger = logging.getLogger(__name__)

ZOHO_API_BASE = "https://www.zohoapis.com/books/v3/"
ZOHO_ACCOUNTS_URL = "https://accounts.zoho.com/oauth/v2/token"
ZOHO_AUTHORIZE_URL = "https://accounts.zoho.com/oauth/v2/auth"

PROVIDER_NAME = "zoho"

# Rate limits: 2500/day => ~1.7/min average
# Conservative: 40/min burst, track daily usage
DAILY_LIMIT = 2500
DAILY_WARNING_THRESHOLD = 0.80  # Warn at 80% usage

# AGGRESSIVE cache: 48hr for chart of accounts (Zoho has very low daily limit)
COA_CACHE_TTL = 172800  # 48 hours in seconds


class ZohoRateLimitError(Exception):
    """Raised when Zoho API rate limit is hit or approaching."""

    def __init__(self, retry_after: int = 3600, remaining: int = 0):
        self.retry_after = retry_after
        self.remaining = remaining
        super().__init__(
            f"Zoho rate limit: {remaining} calls remaining today. Retry after {retry_after}s."
        )


class ZohoAPIError(Exception):
    """Raised for non-2xx Zoho API responses."""

    def __init__(self, status_code: int, detail: str, code: int = 0):
        self.status_code = status_code
        self.detail = detail
        self.zoho_code = code
        super().__init__(f"Zoho API error {status_code} (code={code}): {detail}")


class ZohoAdapter:
    """Adapter for Zoho Books API.

    Manages OAuth 2.0 flow, respects rate limits aggressively (2500/day),
    caches chart of accounts for 48 hours, and uses circuit breaker.

    Usage::

        adapter = ZohoAdapter()
        url = adapter.get_authorization_url("company_123", "https://...")
        await adapter.handle_oauth_callback("company_123", code, redirect_uri)

        coa = await adapter.get_chart_of_accounts("company_123", "org_id")
        result = await adapter.post_journal("company_123", "org_id", journal_data)
    """

    def __init__(self):
        self._client_id = os.environ.get("ZOHO_CLIENT_ID", "")
        self._client_secret = os.environ.get("ZOHO_CLIENT_SECRET", "")
        self._circuit = get_circuit("zoho")
        self._token_manager = get_token_manager()

        # Organization ID per tenant: {tenant_id: organization_id}
        self._org_ids: dict[str, str] = {}

        # Chart of accounts cache: {tenant_id: {"data": [...], "cached_at": float}}
        self._coa_cache: dict[str, dict[str, Any]] = {}

        # Daily call tracking: {"YYYY-MM-DD:tenant_id": count}
        self._daily_calls: dict[str, int] = {}

    # ------------------------------------------------------------------
    # OAuth 2.0 flow
    # ------------------------------------------------------------------

    def get_authorization_url(
        self,
        tenant_id: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """Generate OAuth 2.0 authorization URL for Zoho Books.

        Args:
            tenant_id: AITE company ID.
            redirect_uri: Callback URL after authorization.
            scopes: OAuth scopes. Defaults to Zoho Books full access.

        Returns:
            URL to redirect the user to for Zoho authorization.
        """
        if not self._client_id:
            raise ValueError("ZOHO_CLIENT_ID not configured")

        if scopes is None:
            scopes = [
                "ZohoBooks.fullaccess.all",
            ]

        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "scope": ",".join(scopes),
            "redirect_uri": redirect_uri,
            "access_type": "offline",  # Required for refresh token
            "prompt": "consent",
        }

        url = f"{ZOHO_AUTHORIZE_URL}?{httpx.QueryParams(params)}"
        logger.info("Generated Zoho OAuth URL for tenant=%s", tenant_id)
        return url

    async def handle_oauth_callback(
        self,
        tenant_id: str,
        code: str,
        redirect_uri: str,
    ) -> dict:
        """Exchange authorization code for tokens.

        Args:
            tenant_id: AITE company ID.
            code: Authorization code from Zoho callback.
            redirect_uri: Same redirect URI used in authorization.

        Returns:
            Dict with connection status.
        """
        if not self._client_id or not self._client_secret:
            raise ValueError("ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET must be configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ZOHO_ACCOUNTS_URL,
                params={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                raise ZohoAPIError(response.status_code, response.text)

            token_data = response.json()

            if "error" in token_data:
                raise ZohoAPIError(
                    400,
                    token_data.get("error", "Unknown error"),
                )

            self._token_manager.store_token(tenant_id, PROVIDER_NAME, token_data)

            # Register refresh callback
            self._token_manager.register_refresh_callback(PROVIDER_NAME, self._refresh_token)

            # Fetch organization ID
            org_id = await self._get_organization_id(tenant_id)
            if org_id:
                self._org_ids[tenant_id] = org_id

            logger.info("Zoho OAuth completed for tenant=%s, org=%s", tenant_id, org_id)

            return {
                "status": "connected",
                "provider": PROVIDER_NAME,
                "organization_id": org_id,
            }

    async def _refresh_token(self, tenant_id: str, refresh_token: str) -> dict:
        """Refresh an expired Zoho access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ZOHO_ACCOUNTS_URL,
                params={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )

            if response.status_code != 200:
                raise ZohoAPIError(response.status_code, response.text)

            data = response.json()
            # Zoho refresh responses don't include refresh_token again
            # Preserve the existing one
            data["refresh_token"] = refresh_token
            return data

    async def _get_organization_id(self, tenant_id: str) -> Optional[str]:
        """Fetch the Zoho Books organization ID for a connected tenant."""
        access_token = self._token_manager.get_valid_token(tenant_id, PROVIDER_NAME)
        if not access_token:
            return None

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{ZOHO_API_BASE}organizations",
                headers={
                    "Authorization": f"Zoho-oauthtoken {access_token}",
                },
            )

            if response.status_code != 200:
                logger.warning("Failed to fetch Zoho orgs for tenant=%s", tenant_id)
                return None

            data = response.json()
            orgs = data.get("organizations", [])
            if not orgs:
                return None

            # Return the first active organization
            for org in orgs:
                if org.get("is_default_org") or org.get("status") == "active":
                    return org.get("organization_id")

            return orgs[0].get("organization_id")

    # ------------------------------------------------------------------
    # Rate limit enforcement (aggressive due to 2500/day limit)
    # ------------------------------------------------------------------

    def _check_rate_limit(self, tenant_id: str) -> None:
        """Enforce rate limits with daily tracking and warning at 80%.

        Per-minute burst limit uses the centralized check_rate_limit()
        from resilience.py. Daily limit is tracked locally.
        """
        # Per-minute burst limit via centralized helper (raises RateLimitExceeded)
        check_rate_limit(tenant_id, PROVIDER_NAME)

        # Daily limit tracking
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_key = f"{today}:{tenant_id}"
        current = self._daily_calls.get(daily_key, 0)

        if current >= DAILY_LIMIT:
            raise ZohoRateLimitError(retry_after=3600, remaining=0)

        # Warning at 80% threshold
        if current >= int(DAILY_LIMIT * DAILY_WARNING_THRESHOLD):
            remaining = DAILY_LIMIT - current
            logger.warning(
                "Zoho daily limit warning: %d/%d calls used for tenant=%s (%d remaining)",
                current,
                DAILY_LIMIT,
                tenant_id,
                remaining,
            )

        self._daily_calls[daily_key] = current + 1

    def get_daily_usage(self, tenant_id: str) -> dict:
        """Get current daily API usage for a tenant.

        Returns:
            Dict with used, remaining, limit, and warning flag.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_key = f"{today}:{tenant_id}"
        used = self._daily_calls.get(daily_key, 0)
        remaining = max(0, DAILY_LIMIT - used)

        return {
            "used": used,
            "remaining": remaining,
            "limit": DAILY_LIMIT,
            "warning": used >= int(DAILY_LIMIT * DAILY_WARNING_THRESHOLD),
            "date": today,
        }

    # ------------------------------------------------------------------
    # Authenticated API call helper
    # ------------------------------------------------------------------

    async def _api_call(
        self,
        tenant_id: str,
        organization_id: str,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated Zoho Books API call.

        Args:
            tenant_id: AITE company ID.
            organization_id: Zoho Books organization ID.
            method: HTTP method.
            endpoint: API endpoint path (e.g., "chartofaccounts", "journals").
            json_data: JSON body for POST/PUT.
            params: Query parameters.

        Returns:
            Parsed JSON response.
        """
        self._check_rate_limit(tenant_id)

        access_token = await self._token_manager.refresh_if_expired(tenant_id, PROVIDER_NAME)
        if not access_token:
            raise ZohoAPIError(401, "No valid Zoho token. Re-authorization required.")

        url = f"{ZOHO_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json",
        }

        if params is None:
            params = {}
        params["organization_id"] = organization_id

        async def _do_request() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    params=params,
                )

                if response.status_code == 429:
                    raise ZohoRateLimitError(retry_after=3600, remaining=0)

                data = response.json()

                # Zoho returns code: 0 for success, non-zero for errors
                zoho_code = data.get("code", 0)
                if response.status_code >= 400 or zoho_code != 0:
                    raise ZohoAPIError(
                        response.status_code,
                        data.get("message", response.text[:500]),
                        code=zoho_code,
                    )

                return data

        return await self._circuit.call(_do_request)

    # ------------------------------------------------------------------
    # Chart of Accounts (cached 48hr — aggressive due to low daily limit)
    # ------------------------------------------------------------------

    async def get_chart_of_accounts(
        self,
        tenant_id: str,
        organization_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> list[dict]:
        """Fetch chart of accounts from Zoho Books with 48hr caching.

        Uses aggressive caching because Zoho has a very low daily API limit
        (2500/day). Chart of accounts rarely changes.

        Args:
            tenant_id: AITE company ID.
            organization_id: Zoho org ID. Uses stored value if not provided.
            force_refresh: Skip cache and fetch fresh data.

        Returns:
            List of normalized account dicts.
        """
        cache_key = tenant_id
        now = time.monotonic()

        if not force_refresh and cache_key in self._coa_cache:
            cached = self._coa_cache[cache_key]
            if now - cached["cached_at"] < COA_CACHE_TTL:
                logger.debug("Returning 48hr-cached chart of accounts for %s", tenant_id)
                return cached["data"]

        org_id = organization_id or self._org_ids.get(tenant_id)
        if not org_id:
            raise ValueError(f"No Zoho organization_id for tenant {tenant_id}. Re-authorize.")

        response = await self._api_call(
            tenant_id=tenant_id,
            organization_id=org_id,
            method="GET",
            endpoint="chartofaccounts",
        )

        accounts_raw = response.get("chartofaccounts", [])
        normalized = [
            {
                "account_id": acc.get("account_id", ""),
                "code": acc.get("account_code", ""),
                "name": acc.get("account_name", ""),
                "type": acc.get("account_type", ""),
                "parent_account_id": acc.get("parent_account_id", ""),
                "active": acc.get("is_active", True),
                "description": acc.get("description", ""),
                "is_user_created": acc.get("is_user_created", False),
            }
            for acc in accounts_raw
        ]

        self._coa_cache[cache_key] = {"data": normalized, "cached_at": now}
        logger.info("Fetched %d accounts from Zoho for tenant=%s", len(normalized), tenant_id)
        return normalized

    # ------------------------------------------------------------------
    # Post journal
    # ------------------------------------------------------------------

    async def post_journal(
        self,
        tenant_id: str,
        journal_data: dict,
        organization_id: Optional[str] = None,
    ) -> dict:
        """Post a journal entry to Zoho Books.

        Args:
            tenant_id: AITE company ID.
            journal_data: Dict with:
                - notes: str (description/memo)
                - date: str (ISO YYYY-MM-DD)
                - reference_number: str (optional, e.g., payroll run ID)
                - lines: list of dicts with:
                    - account_id: str (Zoho account ID)
                    - description: str
                    - amount: float (positive = debit, negative = credit)
            organization_id: Zoho org ID. Uses stored if not provided.

        Returns:
            Dict with journal_id, status, and details.
        """
        org_id = organization_id or self._org_ids.get(tenant_id)
        if not org_id:
            raise ValueError(f"No Zoho organization_id for tenant {tenant_id}. Re-authorize.")

        # Build Zoho journal payload
        zoho_lines = []
        for line in journal_data.get("lines", []):
            amount = line["amount"]
            zoho_line = {
                "account_id": line["account_id"],
                "description": line.get("description", ""),
            }

            if amount >= 0:
                zoho_line["debit_or_credit"] = "debit"
                zoho_line["amount"] = round(abs(amount), 2)
            else:
                zoho_line["debit_or_credit"] = "credit"
                zoho_line["amount"] = round(abs(amount), 2)

            zoho_lines.append(zoho_line)

        # Validate balance
        total_debit = sum(l["amount"] for l in zoho_lines if l["debit_or_credit"] == "debit")
        total_credit = sum(l["amount"] for l in zoho_lines if l["debit_or_credit"] == "credit")
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(
                f"Journal does not balance: debits={total_debit:.2f}, "
                f"credits={total_credit:.2f}"
            )

        payload = {
            "journal_date": journal_data.get(
                "date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
            ),
            "notes": journal_data.get("notes", ""),
            "line_items": zoho_lines,
        }

        if journal_data.get("reference_number"):
            payload["reference_number"] = journal_data["reference_number"]

        response = await self._api_call(
            tenant_id=tenant_id,
            organization_id=org_id,
            method="POST",
            endpoint="journals",
            json_data={"JSONString": payload},  # Zoho wraps in JSONString
        )

        journal = response.get("journal", {})
        result = {
            "journal_id": journal.get("journal_id", ""),
            "journal_number": journal.get("journal_number", ""),
            "journal_date": journal.get("journal_date", ""),
            "total": journal.get("total", 0.0),
            "line_count": len(journal.get("line_items", [])),
            "status": "posted",
            "provider": PROVIDER_NAME,
        }

        logger.info(
            "Posted journal to Zoho: id=%s, lines=%d, tenant=%s",
            result["journal_id"],
            result["line_count"],
            tenant_id,
        )
        return result

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def is_connected(self, tenant_id: str) -> bool:
        """Check if a tenant has a valid Zoho connection."""
        return self._token_manager.is_connected(tenant_id, PROVIDER_NAME)

    async def disconnect(self, tenant_id: str) -> bool:
        """Revoke Zoho connection for a tenant."""
        revoked = self._token_manager.revoke_token(tenant_id, PROVIDER_NAME)
        self._org_ids.pop(tenant_id, None)
        self._coa_cache.pop(tenant_id, None)
        logger.info("Disconnected Zoho for tenant=%s", tenant_id)
        return revoked


# Module-level singleton
_adapter: Optional[ZohoAdapter] = None


def get_zoho_adapter() -> ZohoAdapter:
    """Get or create the Zoho adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = ZohoAdapter()
    return _adapter
