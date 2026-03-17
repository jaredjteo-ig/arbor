"""Aspire Gateway Payout API adapter.

Handles single and bulk payouts via Aspire's neobank API.
Supports domestic (SGD via FAST/GIRO) and cross-border transfers.

Aspire API docs: https://docs.gateway.aspireapp.com
Auth: Client ID + API key.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit, RATE_LIMITERS

logger = logging.getLogger(__name__)

ASPIRE_API_BASE = "https://api.aspireapp.com/"
ASPIRE_SANDBOX_BASE = "https://sandbox.aspireapp.com/"

PROVIDER_NAME = "aspire"


class AspireAPIError(Exception):
    """Raised for Aspire API errors."""

    def __init__(self, status_code: int, detail: str, error_code: str = ""):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(f"Aspire API error {status_code}: {detail}")


class AspireRateLimitError(Exception):
    """Raised when Aspire rate limit is hit."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Aspire rate limit exceeded. Retry after {retry_after}s.")


class AspireAdapter:
    """Adapter for Aspire Gateway Payout API.

    Supports single payouts, bulk salary disbursement, and payout
    status tracking. Uses Client ID + API key authentication.

    Usage::

        adapter = AspireAdapter()

        # Single payout
        result = await adapter.initiate_payout(
            recipient={"name": "John Tan", "bank_code": "7171", "account": "1234567890"},
            amount=4500.00,
            currency="SGD",
            reference="SAL-2026-03-001",
        )

        # Bulk payout
        results = await adapter.initiate_bulk_payout([
            {"recipient": {...}, "amount": 4500.00, "currency": "SGD", "reference": "..."},
            {"recipient": {...}, "amount": 3200.00, "currency": "SGD", "reference": "..."},
        ])

        # Check status
        status = await adapter.get_payout_status("payout_id_123")
    """

    def __init__(self):
        self._client_id = os.environ.get("ASPIRE_CLIENT_ID", "")
        self._api_key = os.environ.get("ASPIRE_API_KEY", "")
        self._use_sandbox = os.environ.get("ASPIRE_SANDBOX", "true").lower() == "true"
        self._circuit = get_circuit("aspire")

    @property
    def _base_url(self) -> str:
        return ASPIRE_SANDBOX_BASE if self._use_sandbox else ASPIRE_API_BASE

    # ------------------------------------------------------------------
    # Authenticated API call helper
    # ------------------------------------------------------------------

    async def _api_call(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated Aspire API call.

        Args:
            method: HTTP method (GET, POST).
            endpoint: API endpoint path.
            json_data: JSON body for POST.
            params: Query parameters.

        Returns:
            Parsed JSON response.
        """
        if not self._client_id or not self._api_key:
            raise AspireAPIError(401, "ASPIRE_CLIENT_ID and ASPIRE_API_KEY must be configured")

        url = f"{self._base_url}{endpoint}"
        headers = {
            "X-Client-Id": self._client_id,
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

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
                    raise AspireRateLimitError(retry_after=retry_after)

                if response.status_code >= 400:
                    error_body = {}
                    try:
                        error_body = response.json()
                    except Exception:
                        pass
                    raise AspireAPIError(
                        response.status_code,
                        error_body.get("message", response.text[:500]),
                        error_code=error_body.get("error_code", ""),
                    )

                return response.json()

        return await self._circuit.call(_do_request)

    # ------------------------------------------------------------------
    # Single payout
    # ------------------------------------------------------------------

    async def initiate_payout(
        self,
        recipient: dict,
        amount: float,
        currency: str = "SGD",
        reference: str = "",
        description: str = "",
        payment_method: str = "FAST",
    ) -> dict:
        """Initiate a single payout via Aspire.

        Args:
            recipient: Dict with:
                - name: str (recipient full name)
                - bank_code: str (bank clearing code or SWIFT)
                - account: str (bank account number)
                - email: str (optional, for notification)
            amount: Payment amount.
            currency: Currency code (default "SGD").
            reference: Payment reference / invoice number.
            description: Payment description / purpose.
            payment_method: "FAST", "GIRO", or "WIRE" (default "FAST").

        Returns:
            Dict with payout_id, status, and details.
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive. Got: {amount}")

        if not recipient.get("name"):
            raise ValueError("Recipient name is required")
        if not recipient.get("account"):
            raise ValueError("Recipient bank account is required")

        # Generate idempotency key to prevent double payments
        idempotency_key = reference or f"AITE-{uuid.uuid4().hex[:12]}"

        payload: dict[str, Any] = {
            "amount": round(amount, 2),
            "currency": currency,
            "payment_method": payment_method,
            "reference": reference[:50] if reference else "",
            "description": description[:140] if description else "",
            "idempotency_key": idempotency_key,
            "beneficiary": {
                "name": recipient["name"],
                "bank_account_number": recipient["account"],
            },
        }

        if recipient.get("bank_code"):
            payload["beneficiary"]["bank_code"] = recipient["bank_code"]
        if recipient.get("email"):
            payload["beneficiary"]["email"] = recipient["email"]

        response = await self._api_call(
            method="POST",
            endpoint="v1/payouts",
            json_data=payload,
        )

        payout = response.get("data", response)
        result = {
            "payout_id": payout.get("id", ""),
            "status": payout.get("status", "pending"),
            "amount": payout.get("amount", amount),
            "currency": payout.get("currency", currency),
            "reference": reference,
            "payment_method": payment_method,
            "created_at": payout.get("created_at", datetime.now(timezone.utc).isoformat()),
            "provider": PROVIDER_NAME,
        }

        logger.info(
            "Initiated Aspire payout: id=%s, amount=%.2f %s, ref=%s, method=%s",
            result["payout_id"],
            amount,
            currency,
            reference,
            payment_method,
        )

        return result

    # ------------------------------------------------------------------
    # Bulk payout
    # ------------------------------------------------------------------

    async def initiate_bulk_payout(
        self,
        payouts: list[dict],
        batch_reference: str = "",
    ) -> dict:
        """Initiate a bulk salary payout via Aspire.

        Args:
            payouts: List of dicts, each with:
                - recipient: dict (same as initiate_payout)
                - amount: float
                - currency: str (default "SGD")
                - reference: str
                - description: str (optional)
                - payment_method: str (default "FAST")
            batch_reference: Reference for the entire batch.

        Returns:
            Dict with batch_id, individual payout results, and summary.
        """
        if not payouts:
            raise ValueError("No payouts provided")

        batch_id = batch_reference or f"BATCH-{uuid.uuid4().hex[:12]}"

        # Build batch payload
        transfers = []
        total_amount = 0.0

        for i, payout in enumerate(payouts):
            recipient = payout.get("recipient", {})
            amount = payout.get("amount", 0)
            currency = payout.get("currency", "SGD")
            reference = payout.get("reference", f"{batch_id}-{i+1:04d}")

            if amount <= 0:
                continue

            total_amount += amount
            transfers.append(
                {
                    "amount": round(amount, 2),
                    "currency": currency,
                    "payment_method": payout.get("payment_method", "FAST"),
                    "reference": reference[:50],
                    "description": payout.get("description", "")[:140],
                    "beneficiary": {
                        "name": recipient.get("name", ""),
                        "bank_account_number": recipient.get("account", ""),
                        "bank_code": recipient.get("bank_code", ""),
                    },
                }
            )

        if not transfers:
            raise ValueError("No valid payouts with positive amounts")

        payload = {
            "batch_reference": batch_id,
            "transfers": transfers,
            "idempotency_key": batch_id,
        }

        response = await self._api_call(
            method="POST",
            endpoint="v1/payouts/batch",
            json_data=payload,
        )

        batch_data = response.get("data", response)

        # Extract individual results
        individual_results = []
        for item in batch_data.get("transfers", transfers):
            individual_results.append(
                {
                    "payout_id": item.get("id", ""),
                    "status": item.get("status", "pending"),
                    "amount": item.get("amount", 0),
                    "reference": item.get("reference", ""),
                }
            )

        result = {
            "batch_id": batch_data.get("id", batch_id),
            "status": batch_data.get("status", "processing"),
            "total_amount": round(total_amount, 2),
            "transfer_count": len(transfers),
            "transfers": individual_results,
            "created_at": batch_data.get("created_at", datetime.now(timezone.utc).isoformat()),
            "provider": PROVIDER_NAME,
        }

        logger.info(
            "Initiated Aspire bulk payout: batch=%s, count=%d, total=$%.2f",
            result["batch_id"],
            len(transfers),
            total_amount,
        )

        return result

    # ------------------------------------------------------------------
    # Payout status
    # ------------------------------------------------------------------

    async def get_payout_status(self, payout_id: str) -> dict:
        """Check the status of a payout.

        Args:
            payout_id: Aspire payout ID.

        Returns:
            Dict with current status, timestamps, and details.
        """
        if not payout_id:
            raise ValueError("payout_id is required")

        response = await self._api_call(
            method="GET",
            endpoint=f"v1/payouts/{payout_id}",
        )

        payout = response.get("data", response)

        result = {
            "payout_id": payout.get("id", payout_id),
            "status": payout.get("status", "unknown"),
            "amount": payout.get("amount", 0),
            "currency": payout.get("currency", "SGD"),
            "reference": payout.get("reference", ""),
            "payment_method": payout.get("payment_method", ""),
            "created_at": payout.get("created_at", ""),
            "completed_at": payout.get("completed_at", ""),
            "failure_reason": payout.get("failure_reason", ""),
            "provider": PROVIDER_NAME,
        }

        return result

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Check if Aspire credentials are configured."""
        return bool(self._client_id and self._api_key)

    async def verify_connection(self) -> dict:
        """Verify Aspire API connection is working.

        Makes a lightweight API call to check credentials.
        """
        if not self.is_configured():
            return {
                "status": "not_configured",
                "provider": PROVIDER_NAME,
                "message": "ASPIRE_CLIENT_ID and ASPIRE_API_KEY not set",
            }

        try:
            response = await self._api_call(
                method="GET",
                endpoint="v1/account",
            )
            return {
                "status": "connected",
                "provider": PROVIDER_NAME,
                "sandbox": self._use_sandbox,
                "account_name": response.get("data", {}).get("name", ""),
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": PROVIDER_NAME,
                "error": str(e),
            }


# Module-level singleton
_adapter: Optional[AspireAdapter] = None


def get_aspire_adapter() -> AspireAdapter:
    """Get or create the Aspire adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = AspireAdapter()
    return _adapter
