"""QuickBooks Online (QBO) Accounting API adapter.

Handles OAuth 2.0 authentication, chart of accounts queries,
and journal entry posting for payroll and claims.

QBO API docs: https://developer.intuit.com/app/developer/qbo/docs
Rate limits: 500 calls/min, 10 concurrent requests.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.token_store import get_token_manager
from hr_advisory.mcp_servers.resilience import get_circuit, RATE_LIMITERS

logger = logging.getLogger(__name__)

QBO_AUTHORIZE_URL = "https://appcenter.intuit.com/connect/oauth2"
QBO_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QBO_API_BASE = "https://quickbooks.api.intuit.com/v3/company/"

PROVIDER_NAME = "quickbooks"

# Rate limits
MINUTE_LIMIT = 500
MAX_CONCURRENT = 10


class QBORateLimitError(Exception):
    """Raised when QBO API rate limit is hit."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"QuickBooks rate limit exceeded. Retry after {retry_after}s.")


class QBOAPIError(Exception):
    """Raised for non-2xx QBO API responses."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"QuickBooks API error {status_code}: {detail}")


class QuickBooksAdapter:
    """Adapter for QuickBooks Online Accounting API.

    Manages OAuth 2.0 flow, respects rate limits, and uses
    circuit breaker for resilience.

    Usage::

        adapter = QuickBooksAdapter()
        url = adapter.get_authorization_url("company_123", "https://...")
        await adapter.handle_oauth_callback("company_123", code, realm_id, redirect_uri)

        coa = await adapter.get_chart_of_accounts("company_123", "realm_id")
        result = await adapter.post_journal_entry("company_123", "realm_id", journal_data)
    """

    def __init__(self):
        self._client_id = os.environ.get("QBO_CLIENT_ID", "")
        self._client_secret = os.environ.get("QBO_CLIENT_SECRET", "")
        self._circuit = get_circuit("quickbooks")
        self._rate_limiter = RATE_LIMITERS.get("quickbooks")
        self._token_manager = get_token_manager()

        # Store realm_id per tenant: {tenant_id: realm_id}
        self._realm_ids: dict[str, str] = {}

        # Chart of accounts cache: {tenant_id: {"data": [...], "cached_at": float}}
        self._coa_cache: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # OAuth 2.0 flow
    # ------------------------------------------------------------------

    def get_authorization_url(
        self,
        tenant_id: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """Generate OAuth 2.0 authorization URL for QuickBooks.

        Args:
            tenant_id: AITE company ID.
            redirect_uri: Callback URL after authorization.
            scopes: OAuth scopes. Defaults to accounting.

        Returns:
            URL to redirect the user to for QBO authorization.
        """
        if not self._client_id:
            raise ValueError("QBO_CLIENT_ID not configured")

        if scopes is None:
            scopes = ["com.intuit.quickbooks.accounting"]

        state = f"{tenant_id}:{uuid.uuid4().hex[:16]}"

        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "scope": " ".join(scopes),
            "redirect_uri": redirect_uri,
            "state": state,
        }

        url = f"{QBO_AUTHORIZE_URL}?{httpx.QueryParams(params)}"
        logger.info("Generated QBO OAuth URL for tenant=%s", tenant_id)
        return url

    async def handle_oauth_callback(
        self,
        tenant_id: str,
        code: str,
        realm_id: str,
        redirect_uri: str,
    ) -> dict:
        """Exchange authorization code for tokens.

        Args:
            tenant_id: AITE company ID.
            code: Authorization code from QBO callback.
            realm_id: QBO company ID (from callback query param realmId).
            redirect_uri: Same redirect URI used in authorization.

        Returns:
            Dict with connection status and realm_id.
        """
        if not self._client_id or not self._client_secret:
            raise ValueError("QBO_CLIENT_ID and QBO_CLIENT_SECRET must be configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                QBO_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                auth=(self._client_id, self._client_secret),
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise QBOAPIError(response.status_code, response.text)

            token_data = response.json()
            self._token_manager.store_token(tenant_id, PROVIDER_NAME, token_data)
            self._realm_ids[tenant_id] = realm_id

            # Register refresh callback
            self._token_manager.register_refresh_callback(PROVIDER_NAME, self._refresh_token)

            logger.info("QBO OAuth completed for tenant=%s, realm=%s", tenant_id, realm_id)

            return {
                "status": "connected",
                "provider": PROVIDER_NAME,
                "realm_id": realm_id,
            }

    async def _refresh_token(self, tenant_id: str, refresh_token: str) -> dict:
        """Refresh an expired QBO access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                QBO_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                auth=(self._client_id, self._client_secret),
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise QBOAPIError(response.status_code, response.text)

            return response.json()

    # ------------------------------------------------------------------
    # Rate limit enforcement
    # ------------------------------------------------------------------

    def _check_rate_limit(self, tenant_id: str) -> None:
        """Enforce per-minute rate limits."""
        if self._rate_limiter and not self._rate_limiter.check(tenant_id, PROVIDER_NAME):
            raise QBORateLimitError(retry_after=60)

    # ------------------------------------------------------------------
    # Authenticated API call helper
    # ------------------------------------------------------------------

    async def _api_call(
        self,
        tenant_id: str,
        realm_id: str,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated QBO API call.

        Args:
            tenant_id: AITE company ID.
            realm_id: QBO company realm ID.
            method: HTTP method.
            endpoint: API endpoint path (appended to company base URL).
            json_data: JSON body for POST/PUT.
            params: Query parameters.

        Returns:
            Parsed JSON response.
        """
        self._check_rate_limit(tenant_id)

        access_token = await self._token_manager.refresh_if_expired(tenant_id, PROVIDER_NAME)
        if not access_token:
            raise QBOAPIError(401, "No valid QBO token. Re-authorization required.")

        url = f"{QBO_API_BASE}{realm_id}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # QBO requires minorversion param
        if params is None:
            params = {}
        params.setdefault("minorversion", "73")

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
                    raise QBORateLimitError(retry_after=60)

                if response.status_code >= 400:
                    raise QBOAPIError(response.status_code, response.text[:500])

                return response.json()

        return await self._circuit.call(_do_request)

    # ------------------------------------------------------------------
    # Chart of Accounts
    # ------------------------------------------------------------------

    async def get_chart_of_accounts(
        self,
        tenant_id: str,
        realm_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> list[dict]:
        """Fetch chart of accounts from QuickBooks via query endpoint.

        QBO uses a query API: GET /query?query=SELECT * FROM Account

        Args:
            tenant_id: AITE company ID.
            realm_id: QBO realm ID. Uses stored value if not provided.
            force_refresh: Skip cache and fetch fresh.

        Returns:
            List of normalized account dicts.
        """
        import time

        cache_key = tenant_id
        now = time.monotonic()
        cache_ttl = 86400  # 24 hours

        if not force_refresh and cache_key in self._coa_cache:
            cached = self._coa_cache[cache_key]
            if now - cached["cached_at"] < cache_ttl:
                return cached["data"]

        realm_id = realm_id or self._realm_ids.get(tenant_id)
        if not realm_id:
            raise ValueError(f"No QBO realm_id for tenant {tenant_id}. Re-authorize.")

        response = await self._api_call(
            tenant_id=tenant_id,
            realm_id=realm_id,
            method="GET",
            endpoint="query",
            params={
                "query": "SELECT * FROM Account MAXRESULTS 1000",
            },
        )

        query_response = response.get("QueryResponse", {})
        accounts = query_response.get("Account", [])

        normalized = [
            {
                "account_id": acc.get("Id", ""),
                "code": acc.get("AcctNum", ""),
                "name": acc.get("Name", ""),
                "type": acc.get("AccountType", ""),
                "sub_type": acc.get("AccountSubType", ""),
                "active": acc.get("Active", True),
                "classification": acc.get("Classification", ""),
                "balance": acc.get("CurrentBalance", 0.0),
            }
            for acc in accounts
        ]

        self._coa_cache[cache_key] = {"data": normalized, "cached_at": now}
        logger.info("Fetched %d accounts from QBO for tenant=%s", len(normalized), tenant_id)
        return normalized

    # ------------------------------------------------------------------
    # Post journal entry
    # ------------------------------------------------------------------

    async def post_journal_entry(
        self,
        tenant_id: str,
        journal_data: dict,
        realm_id: Optional[str] = None,
    ) -> dict:
        """Post a journal entry to QuickBooks.

        Args:
            tenant_id: AITE company ID.
            journal_data: Dict with:
                - memo: str (description)
                - date: str (ISO format YYYY-MM-DD)
                - lines: list of dicts with:
                    - account_id: str (QBO Account.Id)
                    - description: str
                    - amount: float (positive = debit, negative = credit)
                    - account_name: str (optional, for display)
            realm_id: QBO realm ID. Uses stored if not provided.

        Returns:
            Dict with journal entry ID, status, and details.
        """
        realm_id = realm_id or self._realm_ids.get(tenant_id)
        if not realm_id:
            raise ValueError(f"No QBO realm_id for tenant {tenant_id}. Re-authorize.")

        # Build QBO JournalEntry payload
        qbo_lines = []
        for line in journal_data.get("lines", []):
            amount = line["amount"]
            posting_type = "Debit" if amount >= 0 else "Credit"

            qbo_line = {
                "JournalEntryLineDetail": {
                    "PostingType": posting_type,
                    "AccountRef": {
                        "value": line["account_id"],
                    },
                },
                "DetailType": "JournalEntryLineDetail",
                "Amount": abs(round(amount, 2)),
                "Description": line.get("description", ""),
            }

            if line.get("account_name"):
                qbo_line["JournalEntryLineDetail"]["AccountRef"]["name"] = line["account_name"]

            qbo_lines.append(qbo_line)

        # Validate balance
        total_debit = sum(
            abs(l["amount"]) for l in journal_data.get("lines", []) if l["amount"] >= 0
        )
        total_credit = sum(
            abs(l["amount"]) for l in journal_data.get("lines", []) if l["amount"] < 0
        )
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(
                f"Journal does not balance: debits={total_debit:.2f}, "
                f"credits={total_credit:.2f}"
            )

        payload = {
            "TxnDate": journal_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "Line": qbo_lines,
        }

        if journal_data.get("memo"):
            payload["PrivateNote"] = journal_data["memo"]

        response = await self._api_call(
            tenant_id=tenant_id,
            realm_id=realm_id,
            method="POST",
            endpoint="journalentry",
            json_data=payload,
        )

        entry = response.get("JournalEntry", {})
        result = {
            "journal_entry_id": entry.get("Id", ""),
            "sync_token": entry.get("SyncToken", ""),
            "txn_date": entry.get("TxnDate", ""),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "line_count": len(entry.get("Line", [])),
            "provider": PROVIDER_NAME,
        }

        logger.info(
            "Posted journal entry to QBO: id=%s, lines=%d, tenant=%s",
            result["journal_entry_id"],
            result["line_count"],
            tenant_id,
        )
        return result

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def is_connected(self, tenant_id: str) -> bool:
        """Check if a tenant has a valid QBO connection."""
        return self._token_manager.is_connected(tenant_id, PROVIDER_NAME)

    def get_realm_id(self, tenant_id: str) -> Optional[str]:
        """Get the stored QBO realm ID for a tenant."""
        return self._realm_ids.get(tenant_id)

    async def disconnect(self, tenant_id: str) -> bool:
        """Revoke QBO connection for a tenant."""
        revoked = self._token_manager.revoke_token(tenant_id, PROVIDER_NAME)
        self._realm_ids.pop(tenant_id, None)
        self._coa_cache.pop(tenant_id, None)
        logger.info("Disconnected QBO for tenant=%s", tenant_id)
        return revoked


# Module-level singleton
_adapter: Optional[QuickBooksAdapter] = None


def get_quickbooks_adapter() -> QuickBooksAdapter:
    """Get or create the QuickBooks adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = QuickBooksAdapter()
    return _adapter
