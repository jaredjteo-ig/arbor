"""Xero Accounting API adapter.

Handles OAuth 2.0 authentication, chart of accounts retrieval,
payroll and claims journal posting, and trial balance queries.

Xero API docs: https://developer.xero.com/documentation/api/accounting
Rate limits: 60 calls/min, 5,000 calls/day per connection.
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

XERO_API_BASE = "https://api.xero.com/api.xro/2.0/"
XERO_IDENTITY_URL = "https://identity.xero.com/connect/token"
XERO_AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
XERO_CONNECTIONS_URL = "https://api.xero.com/connections"

PROVIDER_NAME = "xero"

# Rate limit: 60 calls/min, 5000 calls/day
DAILY_LIMIT = 5000
MINUTE_LIMIT = 60

# Cache TTL for chart of accounts: 24 hours
COA_CACHE_TTL = 86400


class XeroRateLimitError(Exception):
    """Raised when Xero API rate limit is hit."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Xero rate limit exceeded. Retry after {retry_after}s.")


class XeroAPIError(Exception):
    """Raised for non-2xx Xero API responses."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Xero API error {status_code}: {detail}")


class XeroAdapter:
    """Adapter for Xero Accounting API.

    Manages OAuth 2.0 flow, respects rate limits, caches chart of accounts,
    and uses circuit breaker for resilience.

    Usage::

        adapter = XeroAdapter()

        # Start OAuth flow
        url = adapter.get_authorization_url("company_123", "https://app.example.com/callback")
        # User visits URL, authorizes, redirected to callback with code

        # Exchange code for tokens
        await adapter.handle_oauth_callback("company_123", code, redirect_uri)

        # Use API
        coa = await adapter.get_chart_of_accounts("company_123")
        result = await adapter.post_payroll_journal("company_123", journal_data)
    """

    def __init__(self):
        self._client_id = os.environ.get("XERO_CLIENT_ID", "")
        self._client_secret = os.environ.get("XERO_CLIENT_SECRET", "")
        self._circuit = get_circuit("xero")
        self._token_manager = get_token_manager()

        # In-memory cache: {tenant_id: {"data": [...], "cached_at": float}}
        self._coa_cache: dict[str, dict[str, Any]] = {}

        # Daily call counter: {date_str: count}
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
        """Generate OAuth 2.0 authorization URL for Xero.

        Args:
            tenant_id: Company ID (stored as state for CSRF protection).
            redirect_uri: Callback URL after authorization.
            scopes: OAuth scopes. Defaults to accounting and offline access.

        Returns:
            URL to redirect the user to for Xero authorization.
        """
        if not self._client_id:
            raise ValueError("XERO_CLIENT_ID not configured")

        if scopes is None:
            scopes = [
                "openid",
                "profile",
                "email",
                "accounting.transactions",
                "accounting.reports.read",
                "accounting.settings.read",
                "offline_access",
            ]

        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
        }

        url = f"{XERO_AUTHORIZE_URL}?{httpx.QueryParams(params)}"

        logger.info("Generated Xero OAuth URL for tenant=%s", tenant_id)
        return url

    async def handle_oauth_callback(
        self,
        tenant_id: str,
        code: str,
        redirect_uri: str,
    ) -> dict:
        """Exchange authorization code for access and refresh tokens.

        Args:
            tenant_id: Company ID.
            code: Authorization code from Xero callback.
            redirect_uri: Same redirect URI used in authorization.

        Returns:
            Dict with connection status and Xero tenant ID.
        """
        if not self._client_id or not self._client_secret:
            raise ValueError("XERO_CLIENT_ID and XERO_CLIENT_SECRET must be configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                XERO_IDENTITY_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                auth=(self._client_id, self._client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise XeroAPIError(response.status_code, response.text)

            token_data = response.json()

            # Store encrypted tokens
            self._token_manager.store_token(tenant_id, PROVIDER_NAME, token_data)

            # Register refresh callback
            self._token_manager.register_refresh_callback(PROVIDER_NAME, self._refresh_token)

            # Fetch Xero tenant (org) ID
            xero_tenant_id = await self._get_xero_tenant_id(token_data["access_token"])

            logger.info(
                "Xero OAuth completed for tenant=%s, xero_tenant=%s",
                tenant_id,
                xero_tenant_id,
            )

            return {
                "status": "connected",
                "provider": PROVIDER_NAME,
                "xero_tenant_id": xero_tenant_id,
            }

    async def _refresh_token(self, tenant_id: str, refresh_token: str) -> dict:
        """Refresh an expired Xero access token.

        Called automatically by ExternalTokenManager.refresh_if_expired().
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                XERO_IDENTITY_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                auth=(self._client_id, self._client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise XeroAPIError(response.status_code, response.text)

            return response.json()

    async def _get_xero_tenant_id(self, access_token: str) -> str:
        """Fetch the Xero tenant (organization) ID from connections endpoint."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                XERO_CONNECTIONS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 200:
                raise XeroAPIError(response.status_code, response.text)

            connections = response.json()
            if not connections:
                raise XeroAPIError(404, "No Xero organizations connected")

            # Return the first (most recent) connection's tenant ID
            return connections[0]["tenantId"]

    # ------------------------------------------------------------------
    # Rate limit enforcement
    # ------------------------------------------------------------------

    def _check_rate_limit(self, tenant_id: str) -> None:
        """Enforce both per-minute and daily rate limits.

        Per-minute check uses the centralized check_rate_limit() helper
        from resilience.py. Daily limit is tracked locally.
        """
        # Per-minute check via centralized rate limiter (raises RateLimitExceeded)
        check_rate_limit(tenant_id, PROVIDER_NAME)

        # Daily limit check
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_key = f"{tenant_id}:{today}"
        current = self._daily_calls.get(daily_key, 0)
        if current >= DAILY_LIMIT:
            raise XeroRateLimitError(retry_after=3600)
        self._daily_calls[daily_key] = current + 1

    # ------------------------------------------------------------------
    # Authenticated API call helper
    # ------------------------------------------------------------------

    async def _api_call(
        self,
        tenant_id: str,
        method: str,
        endpoint: str,
        xero_tenant_id: Optional[str] = None,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated Xero API call with rate limiting and circuit breaker.

        Args:
            tenant_id: Arbor company ID (for token lookup).
            method: HTTP method (GET, POST, PUT).
            endpoint: API endpoint path (e.g., "Accounts", "ManualJournals").
            xero_tenant_id: Xero organization tenant ID (required for data calls).
            json_data: JSON body for POST/PUT.
            params: Query parameters.

        Returns:
            Parsed JSON response.
        """
        self._check_rate_limit(tenant_id)

        # Get valid access token (auto-refresh if expired)
        access_token = await self._token_manager.refresh_if_expired(tenant_id, PROVIDER_NAME)
        if not access_token:
            raise XeroAPIError(401, "No valid Xero token. Re-authorization required.")

        url = f"{XERO_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if xero_tenant_id:
            headers["Xero-Tenant-Id"] = xero_tenant_id

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
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise XeroRateLimitError(retry_after=retry_after)

                if response.status_code >= 400:
                    raise XeroAPIError(response.status_code, response.text[:500])

                return response.json()

        return await self._circuit.call(_do_request)

    # ------------------------------------------------------------------
    # Chart of Accounts (cached 24hr)
    # ------------------------------------------------------------------

    async def get_chart_of_accounts(
        self,
        tenant_id: str,
        xero_tenant_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> list[dict]:
        """Fetch chart of accounts from Xero with 24hr caching.

        Args:
            tenant_id: Arbor company ID.
            xero_tenant_id: Xero organization tenant ID.
            force_refresh: Skip cache and fetch fresh data.

        Returns:
            List of account dicts with Code, Name, Type, Status.
        """
        cache_key = tenant_id
        now = time.monotonic()

        if not force_refresh and cache_key in self._coa_cache:
            cached = self._coa_cache[cache_key]
            if now - cached["cached_at"] < COA_CACHE_TTL:
                logger.debug("Returning cached chart of accounts for %s", tenant_id)
                return cached["data"]

        response = await self._api_call(
            tenant_id=tenant_id,
            method="GET",
            endpoint="Accounts",
            xero_tenant_id=xero_tenant_id,
        )

        accounts = response.get("Accounts", [])
        normalized = [
            {
                "account_id": acc.get("AccountID", ""),
                "code": acc.get("Code", ""),
                "name": acc.get("Name", ""),
                "type": acc.get("Type", ""),
                "status": acc.get("Status", ""),
                "class": acc.get("Class", ""),
                "tax_type": acc.get("TaxType", ""),
                "description": acc.get("Description", ""),
                "enable_payments": acc.get("EnablePaymentsToAccount", False),
            }
            for acc in accounts
        ]

        self._coa_cache[cache_key] = {"data": normalized, "cached_at": now}
        logger.info("Fetched %d accounts from Xero for tenant=%s", len(normalized), tenant_id)
        return normalized

    # ------------------------------------------------------------------
    # Post payroll journal
    # ------------------------------------------------------------------

    async def post_payroll_journal(
        self,
        tenant_id: str,
        journal_data: dict,
        xero_tenant_id: Optional[str] = None,
    ) -> dict:
        """Post a payroll journal entry to Xero as a ManualJournal.

        Args:
            tenant_id: Arbor company ID.
            journal_data: Dict with:
                - narration: str (description/memo)
                - date: str (ISO format YYYY-MM-DD)
                - lines: list of dicts with:
                    - account_code: str
                    - description: str
                    - amount: float (positive = debit, negative = credit)
                    - tax_type: str (optional)

        Returns:
            Dict with journal_id, status, and Xero ManualJournalID.
        """
        # Build Xero ManualJournal payload
        journal_lines = []
        for line in journal_data.get("lines", []):
            amount = line["amount"]
            xero_line: dict[str, Any] = {
                "AccountCode": line["account_code"],
                "Description": line.get("description", ""),
            }

            # Xero: positive LineAmount = debit, negative = credit
            xero_line["LineAmount"] = round(amount, 2)

            if line.get("tax_type"):
                xero_line["TaxType"] = line["tax_type"]

            journal_lines.append(xero_line)

        # Validate debits equal credits
        total = sum(line["LineAmount"] for line in journal_lines)
        if abs(total) > 0.01:
            raise ValueError(
                f"Journal does not balance: total={total:.2f}. "
                "Debits (positive) must equal credits (negative)."
            )

        payload = {
            "ManualJournals": [
                {
                    "Narration": journal_data.get("narration", "Payroll journal"),
                    "Date": journal_data.get(
                        "date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    ),
                    "Status": "POSTED",
                    "JournalLines": journal_lines,
                }
            ]
        }

        response = await self._api_call(
            tenant_id=tenant_id,
            method="POST",
            endpoint="ManualJournals",
            xero_tenant_id=xero_tenant_id,
            json_data=payload,
        )

        journals = response.get("ManualJournals", [])
        if not journals:
            raise XeroAPIError(500, "No journal returned in Xero response")

        journal = journals[0]
        result = {
            "journal_id": journal.get("ManualJournalID", ""),
            "status": journal.get("Status", ""),
            "narration": journal.get("Narration", ""),
            "date": journal.get("Date", ""),
            "line_count": len(journal.get("JournalLines", [])),
            "provider": PROVIDER_NAME,
        }

        logger.info(
            "Posted payroll journal to Xero: id=%s, lines=%d, tenant=%s",
            result["journal_id"],
            result["line_count"],
            tenant_id,
        )
        return result

    # ------------------------------------------------------------------
    # Post claims journal
    # ------------------------------------------------------------------

    async def post_claims_journal(
        self,
        tenant_id: str,
        claims_data: dict,
        xero_tenant_id: Optional[str] = None,
    ) -> dict:
        """Post claims reimbursement journal to Xero.

        Args:
            tenant_id: Arbor company ID.
            claims_data: Dict with:
                - narration: str
                - date: str (ISO)
                - lines: list of dicts with account_code, description, amount
                  Claims lines: debit expense accounts, credit payable/bank

        Returns:
            Dict with journal_id and status.
        """
        # Claims journals use the same ManualJournal endpoint
        return await self.post_payroll_journal(
            tenant_id=tenant_id,
            journal_data=claims_data,
            xero_tenant_id=xero_tenant_id,
        )

    # ------------------------------------------------------------------
    # Trial balance
    # ------------------------------------------------------------------

    async def get_trial_balance(
        self,
        tenant_id: str,
        xero_tenant_id: Optional[str] = None,
        date: Optional[str] = None,
    ) -> dict:
        """Fetch trial balance report from Xero.

        Args:
            tenant_id: Arbor company ID.
            xero_tenant_id: Xero org tenant ID.
            date: Report date in YYYY-MM-DD format. Defaults to today.

        Returns:
            Dict with report title, rows, and total debits/credits.
        """
        params = {}
        if date:
            params["date"] = date

        response = await self._api_call(
            tenant_id=tenant_id,
            method="GET",
            endpoint="Reports/TrialBalance",
            xero_tenant_id=xero_tenant_id,
            params=params or None,
        )

        reports = response.get("Reports", [])
        if not reports:
            return {"title": "Trial Balance", "rows": [], "total_debit": 0.0, "total_credit": 0.0}

        report = reports[0]
        rows = []
        total_debit = 0.0
        total_credit = 0.0

        for section in report.get("Rows", []):
            if section.get("RowType") == "Section":
                for row in section.get("Rows", []):
                    cells = row.get("Cells", [])
                    if len(cells) >= 3:
                        account_name = cells[0].get("Value", "")
                        debit = _parse_amount(cells[1].get("Value", "0"))
                        credit = _parse_amount(cells[2].get("Value", "0"))
                        rows.append(
                            {
                                "account": account_name,
                                "debit": debit,
                                "credit": credit,
                            }
                        )
                        total_debit += debit
                        total_credit += credit

        return {
            "title": report.get("ReportName", "Trial Balance"),
            "report_date": report.get("ReportDate", ""),
            "rows": rows,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "provider": PROVIDER_NAME,
        }

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def is_connected(self, tenant_id: str) -> bool:
        """Check if a tenant has a valid Xero connection."""
        return self._token_manager.is_connected(tenant_id, PROVIDER_NAME)

    async def disconnect(self, tenant_id: str) -> bool:
        """Revoke Xero connection for a tenant."""
        revoked = self._token_manager.revoke_token(tenant_id, PROVIDER_NAME)
        if tenant_id in self._coa_cache:
            del self._coa_cache[tenant_id]
        logger.info("Disconnected Xero for tenant=%s", tenant_id)
        return revoked


def _parse_amount(value: str) -> float:
    """Parse a Xero amount string to float, handling commas and empty strings."""
    if not value or value.strip() == "":
        return 0.0
    try:
        return float(value.replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


# Module-level singleton
_adapter: Optional[XeroAdapter] = None


def get_xero_adapter() -> XeroAdapter:
    """Get or create the Xero adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = XeroAdapter()
    return _adapter
