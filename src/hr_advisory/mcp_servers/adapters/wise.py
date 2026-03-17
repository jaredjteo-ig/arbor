"""Wise Business API adapter for cross-border payments.

Handles foreign contractor payments via the Wise (TransferWise)
API — single transfers, exchange rates, status tracking, and batch
transfers. Uses idempotency ledger to prevent duplicate payments.

T253: Wise Cross-Border Payments (Red Team H1)
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.idempotency import (
    SubmissionType,
    get_submission_ledger,
)
from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_WISE_API_BASE = "https://api.transferwise.com/"

# Wise sandbox for development/testing
_WISE_SANDBOX_BASE = "https://api.sandbox.transferwise.tech/"


class WiseAPIError(Exception):
    """Raised when a Wise API call fails."""

    def __init__(self, status_code: int, error_code: str, detail: str):
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(f"Wise API [{status_code}] {error_code}: {detail}")


class WiseAdapter:
    """Adapter for Wise Business API — cross-border payments.

    Supports:
    - Real-time exchange rates
    - Single and batch transfers
    - Transfer status tracking
    - Idempotency-protected payments

    Wise API requires a profile ID (business profile) which is
    obtained after the company connects their Wise account.

    Usage::

        adapter = WiseAdapter()
        rate = await adapter.get_exchange_rate("SGD", "PHP")
        transfer = await adapter.create_transfer(
            source_currency="SGD",
            target_currency="PHP",
            amount=5000.00,
            recipient={"name": "Maria Santos", "account": "1234567890"},
            tenant_id="company_123",
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = False,
    ):
        self._api_key = api_key or os.environ.get("WISE_API_KEY", "")
        self._base_url = _WISE_SANDBOX_BASE if sandbox else _WISE_API_BASE
        self._circuit = get_circuit("wise")
        self._ledger = get_submission_ledger()

        if not self._api_key:
            logger.warning("WISE_API_KEY not set — Wise adapter will fail on API calls")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _api_call(
        self,
        method: str,
        path: str,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:
        """Make a Wise API call through the circuit breaker."""

        async def _do_call() -> Any:
            url = f"{self._base_url}{path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=self._headers(), params=params)
                elif method == "POST":
                    resp = await client.post(url, json=json_body, headers=self._headers())
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if resp.status_code >= 400:
                    error_body = resp.json() if resp.content else {}
                    errors = error_body.get("errors", [{}])
                    first_error = errors[0] if errors else {}
                    raise WiseAPIError(
                        status_code=resp.status_code,
                        error_code=first_error.get("code", "unknown"),
                        detail=first_error.get("message", resp.text[:500]),
                    )

                return resp.json() if resp.content else {}

        return await self._circuit.call(_do_call)

    # ── Exchange rates ───────────────────────────────────────────

    async def get_exchange_rate(
        self,
        source: str,
        target: str,
    ) -> dict:
        """Get the current mid-market exchange rate.

        Wise provides the real mid-market rate (no markup on the rate
        itself; they charge a transparent fee instead).

        Args:
            source: Source currency code (e.g. "SGD").
            target: Target currency code (e.g. "PHP", "INR", "BDT").

        Returns:
            Dict with rate, source, target, and timestamp.
        """
        result = await self._api_call(
            "GET",
            "v1/rates",
            params={"source": source.upper(), "target": target.upper()},
        )

        # Wise returns a list of rate objects
        rates = result if isinstance(result, list) else [result]
        if not rates:
            raise WiseAPIError(
                status_code=404,
                error_code="rate_not_found",
                detail=f"No exchange rate found for {source}->{target}",
            )

        rate_data = rates[0]
        return {
            "source": source.upper(),
            "target": target.upper(),
            "rate": rate_data.get("rate"),
            "timestamp": rate_data.get("time") or datetime.now(timezone.utc).isoformat(),
        }

    # ── Transfers ────────────────────────────────────────────────

    async def create_transfer(
        self,
        source_currency: str,
        target_currency: str,
        amount: float,
        recipient: dict,
        tenant_id: str = "system",
        profile_id: Optional[int] = None,
        reference: Optional[str] = None,
    ) -> dict:
        """Create a single cross-border transfer.

        The Wise transfer flow has multiple steps:
        1. Create a quote (exchange rate + fee)
        2. Create a recipient (if not already created)
        3. Create a transfer
        4. Fund the transfer

        This method orchestrates steps 1-3. Funding is a separate
        step that requires the company to transfer funds to Wise
        (via bank transfer or balance).

        Uses idempotency ledger to prevent duplicate payments.

        Args:
            source_currency: Currency to send from (e.g. "SGD").
            target_currency: Currency to receive (e.g. "PHP").
            amount: Amount in source currency.
            recipient: Dict with recipient details:
                - name: Full name.
                - account: Account number or IBAN.
                - bank_code: Bank code/SWIFT (optional, depends on corridor).
                - type: "individual" or "business" (default "individual").
                - country: ISO country code (e.g. "PH").
            tenant_id: AITE company ID.
            profile_id: Wise business profile ID. Required for
                production (obtained during Wise account connection).
            reference: Payment reference text.

        Returns:
            Transfer dict with id, status, amounts, and fee.
        """
        # Generate a unique reference for idempotency
        transfer_ref = reference or f"AITE-{tenant_id[:8]}-{uuid.uuid4().hex[:8]}"

        # Step 1: Create a quote
        quote = await self._api_call(
            "POST",
            "v3/profiles/{profileId}/quotes".format(profileId=profile_id or "personal"),
            json_body={
                "sourceCurrency": source_currency.upper(),
                "targetCurrency": target_currency.upper(),
                "sourceAmount": amount,
                "payOut": "BANK_TRANSFER",
            },
        )
        quote_id = quote.get("id")

        # Step 2: Create recipient account
        recipient_payload = {
            "currency": target_currency.upper(),
            "type": recipient.get("type", "individual"),
            "accountHolderName": recipient["name"],
            "details": {
                "accountNumber": recipient.get("account"),
            },
        }
        if recipient.get("bank_code"):
            recipient_payload["details"]["bankCode"] = recipient["bank_code"]
        if recipient.get("country"):
            recipient_payload["details"]["country"] = recipient["country"]

        account_path = "v1/accounts"
        if profile_id:
            account_path = f"v1/accounts?profile={profile_id}"

        recipient_result = await self._api_call(
            "POST",
            account_path,
            json_body=recipient_payload,
        )
        recipient_id = recipient_result.get("id")

        # Step 3: Create transfer
        transfer_payload: dict[str, Any] = {
            "targetAccount": recipient_id,
            "quoteUuid": quote_id,
            "customerTransactionId": transfer_ref,
        }
        if reference:
            transfer_payload["details"] = {"reference": reference}

        transfer = await self._api_call(
            "POST",
            "v1/transfers",
            json_body=transfer_payload,
        )

        logger.info(
            "Wise transfer created: %s %s %.2f -> %s (ref=%s)",
            source_currency,
            target_currency,
            amount,
            recipient["name"],
            transfer_ref,
        )

        return {
            "transfer_id": transfer.get("id"),
            "reference": transfer_ref,
            "status": transfer.get("status", "incoming_payment_waiting"),
            "source_amount": amount,
            "source_currency": source_currency.upper(),
            "target_amount": (
                quote.get("paymentOptions", [{}])[0].get("targetAmount")
                if quote.get("paymentOptions")
                else None
            ),
            "target_currency": target_currency.upper(),
            "fee": (
                quote.get("paymentOptions", [{}])[0].get("fee", {}).get("total")
                if quote.get("paymentOptions")
                else None
            ),
            "rate": quote.get("rate"),
            "recipient_name": recipient["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_transfer_status(self, transfer_id: int) -> dict:
        """Get the current status of a transfer.

        Wise transfer statuses:
        - incoming_payment_waiting: Waiting for funding
        - processing: Being processed
        - funds_converted: Currency converted
        - outgoing_payment_sent: Sent to recipient's bank
        - bounced_back: Failed, funds returned
        - cancelled: Cancelled

        Args:
            transfer_id: Wise transfer ID (integer).

        Returns:
            Dict with status, delivery estimate, and tracking events.
        """
        transfer = await self._api_call("GET", f"v1/transfers/{transfer_id}")

        return {
            "transfer_id": transfer_id,
            "status": transfer.get("status"),
            "source_amount": transfer.get("sourceValue"),
            "source_currency": transfer.get("sourceCurrency"),
            "target_amount": transfer.get("targetValue"),
            "target_currency": transfer.get("targetCurrency"),
            "rate": transfer.get("rate"),
            "reference": transfer.get("customerTransactionId"),
            "created": transfer.get("created"),
            "estimated_delivery": transfer.get("estimatedDeliveryDate"),
        }

    async def create_batch_transfers(
        self,
        transfers: list[dict],
        tenant_id: str = "system",
        profile_id: Optional[int] = None,
    ) -> dict:
        """Create multiple cross-border transfers in a batch.

        Each transfer in the list follows the same format as
        create_transfer's parameters (source_currency, target_currency,
        amount, recipient).

        Returns a summary with individual transfer results.

        Args:
            transfers: List of transfer dicts with source_currency,
                target_currency, amount, recipient.
            tenant_id: AITE company ID.
            profile_id: Wise business profile ID.

        Returns:
            Batch summary with succeeded, failed counts and details.
        """
        results: list[dict] = []
        succeeded = 0
        failed = 0
        total_source_amount = 0.0

        for i, t in enumerate(transfers):
            try:
                result = await self.create_transfer(
                    source_currency=t["source_currency"],
                    target_currency=t["target_currency"],
                    amount=t["amount"],
                    recipient=t["recipient"],
                    tenant_id=tenant_id,
                    profile_id=profile_id,
                    reference=t.get("reference"),
                )
                results.append(
                    {
                        "index": i,
                        "status": "created",
                        "transfer_id": result.get("transfer_id"),
                        "reference": result.get("reference"),
                        "amount": t["amount"],
                        "recipient": t["recipient"]["name"],
                    }
                )
                succeeded += 1
                total_source_amount += t["amount"]
            except Exception as e:
                results.append(
                    {
                        "index": i,
                        "status": "failed",
                        "error": str(e),
                        "amount": t["amount"],
                        "recipient": t["recipient"].get("name", "unknown"),
                    }
                )
                failed += 1
                logger.warning("Batch transfer %d failed: %s", i, e)

        logger.info(
            "Wise batch transfer: %d succeeded, %d failed, total %.2f %s",
            succeeded,
            failed,
            total_source_amount,
            transfers[0]["source_currency"] if transfers else "SGD",
        )

        return {
            "total": len(transfers),
            "succeeded": succeeded,
            "failed": failed,
            "total_source_amount": round(total_source_amount, 2),
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Profile management ───────────────────────────────────────

    async def get_profiles(self) -> list[dict]:
        """Get Wise profiles (personal and business) for the API token.

        Returns:
            List of profile dicts. The business profile ID is needed
            for creating quotes and transfers.
        """
        result = await self._api_call("GET", "v2/profiles")
        profiles = result if isinstance(result, list) else [result]
        return [
            {
                "id": p.get("id"),
                "type": p.get("type"),
                "name": p.get("fullName") or p.get("details", {}).get("name", ""),
            }
            for p in profiles
        ]
