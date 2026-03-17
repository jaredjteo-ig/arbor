"""Claims-to-accounting synchronization adapter.

Groups approved claims by expense category, builds journal entries,
and routes them to the connected accounting provider (Xero, QBO, Zoho)
or generates a file export (Financio, generic CSV/JSON).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Default expense account mapping for SG SME claim categories
DEFAULT_CLAIM_ACCOUNT_MAP: dict[str, dict[str, str]] = {
    "transport": {
        "account_code": "6200",
        "account_name": "Transport & Travel",
        "description": "Employee transport claims",
    },
    "meal": {
        "account_code": "6210",
        "account_name": "Entertainment & Meals",
        "description": "Employee meal claims",
    },
    "accommodation": {
        "account_code": "6220",
        "account_name": "Accommodation",
        "description": "Employee accommodation claims",
    },
    "medical": {
        "account_code": "6230",
        "account_name": "Medical Expenses",
        "description": "Employee medical claims",
    },
    "office_supplies": {
        "account_code": "6240",
        "account_name": "Office Supplies",
        "description": "Office supply purchases",
    },
    "software": {
        "account_code": "6250",
        "account_name": "Software & Subscriptions",
        "description": "Software and SaaS subscriptions",
    },
    "training": {
        "account_code": "6260",
        "account_name": "Training & Development",
        "description": "Employee training expenses",
    },
    "equipment": {
        "account_code": "6270",
        "account_name": "Equipment & Hardware",
        "description": "Equipment purchases",
    },
    "general": {
        "account_code": "6300",
        "account_name": "General Expenses",
        "description": "Miscellaneous employee claims",
    },
}

# Credit account for claims payable
CLAIMS_PAYABLE_ACCOUNT = {
    "account_code": "2300",
    "account_name": "Claims Payable",
}


class ClaimsSyncError(Exception):
    """Raised when claims sync fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Claims sync error: {detail}")


class ClaimsSyncAdapter:
    """Claims-to-accounting synchronization.

    Groups approved claims by expense category, generates balanced
    journal entries, and posts to the connected accounting provider.

    Usage::

        adapter = ClaimsSyncAdapter()
        result = await adapter.sync_claims_to_accounting(
            tenant_id="company_123",
            claims=[
                {"id": "CLM-001", "category": "transport", "amount": 45.00, ...},
                {"id": "CLM-002", "category": "meal", "amount": 32.50, ...},
            ],
            provider="xero",
            xero_tenant_id="xero-org-123",
        )
    """

    def __init__(
        self,
        account_mapping: Optional[dict[str, dict[str, str]]] = None,
    ):
        """Initialize with optional custom account mapping.

        Args:
            account_mapping: Override default claim category to account mapping.
        """
        self._account_map = account_mapping or DEFAULT_CLAIM_ACCOUNT_MAP

    async def sync_claims_to_accounting(
        self,
        tenant_id: str,
        claims: list[dict],
        provider: str,
        account_mapping: Optional[dict[str, dict[str, str]]] = None,
        xero_tenant_id: Optional[str] = None,
        qbo_realm_id: Optional[str] = None,
        zoho_org_id: Optional[str] = None,
        date: Optional[str] = None,
        reference: Optional[str] = None,
    ) -> dict:
        """Sync approved claims to an accounting provider.

        Groups claims by expense category, creates a balanced journal
        entry (debit expense accounts, credit claims payable), and
        posts to the specified accounting provider.

        Args:
            tenant_id: AITE company ID.
            claims: List of approved claim dicts with:
                - id: str
                - category: str (maps to expense account)
                - amount: float (positive, total approved amount)
                - description: str (optional)
                - employee_name: str (optional)
            provider: Accounting provider name:
                "xero", "quickbooks", "zoho", "financio", "csv", "json"
            account_mapping: Override claim category to account mapping.
            xero_tenant_id: Required for Xero.
            qbo_realm_id: Required for QuickBooks.
            zoho_org_id: Required for Zoho.
            date: Journal date (ISO). Defaults to today.
            reference: Journal reference. Auto-generated if not provided.

        Returns:
            Dict with journal_id, claim_ids synced, totals, and status.
        """
        if not claims:
            raise ClaimsSyncError("No claims provided")

        mapping = account_mapping or self._account_map
        journal_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        claim_ids = [c.get("id", "") for c in claims]
        ref = reference or f"CLAIMS-{journal_date}"

        # ------------------------------------------------------------------
        # Group claims by category and build journal lines
        # ------------------------------------------------------------------
        category_totals: dict[str, float] = {}
        category_descriptions: dict[str, list[str]] = {}
        grand_total = 0.0

        for claim in claims:
            category = claim.get("category", "general").lower()
            amount = claim.get("amount", 0.0)

            if amount <= 0:
                logger.warning(
                    "Skipping claim %s with non-positive amount: %.2f", claim.get("id"), amount
                )
                continue

            grand_total += amount
            category_totals[category] = category_totals.get(category, 0.0) + amount

            desc = claim.get("description", "")
            emp = claim.get("employee_name", "")
            claim_ref = claim.get("id", "")
            line_desc = f"{claim_ref}"
            if emp:
                line_desc += f" ({emp})"
            if desc:
                line_desc += f" - {desc}"
            category_descriptions.setdefault(category, []).append(line_desc)

        if grand_total <= 0:
            raise ClaimsSyncError("No claims with positive amounts")

        # Build journal lines: debit expense accounts
        journal_lines: list[dict] = []

        for category, total in sorted(category_totals.items()):
            account = mapping.get(
                category, mapping.get("general", DEFAULT_CLAIM_ACCOUNT_MAP["general"])
            )
            descriptions = category_descriptions.get(category, [])

            journal_lines.append(
                {
                    "account_code": account["account_code"],
                    "account_name": account["account_name"],
                    "account_id": account.get("account_id", ""),
                    "description": "; ".join(descriptions)[:200],
                    "amount": round(total, 2),  # Positive = debit
                }
            )

        # Credit line: claims payable (total)
        journal_lines.append(
            {
                "account_code": CLAIMS_PAYABLE_ACCOUNT["account_code"],
                "account_name": CLAIMS_PAYABLE_ACCOUNT["account_name"],
                "account_id": "",
                "description": f"Claims payable - {len(claims)} claims",
                "amount": -round(grand_total, 2),  # Negative = credit
            }
        )

        # Build journal data structure
        journal_data = {
            "date": journal_date,
            "narration": f"Employee claims reimbursement - {len(claims)} claims",
            "notes": f"Employee claims reimbursement - {len(claims)} claims",
            "memo": f"Employee claims reimbursement - {len(claims)} claims",
            "reference": ref,
            "reference_number": ref,
            "lines": journal_lines,
        }

        # ------------------------------------------------------------------
        # Route to the appropriate provider
        # ------------------------------------------------------------------
        if provider == "xero":
            result = await self._post_to_xero(tenant_id, journal_data, xero_tenant_id)
        elif provider == "quickbooks":
            result = await self._post_to_quickbooks(tenant_id, journal_data, qbo_realm_id)
        elif provider == "zoho":
            result = await self._post_to_zoho(tenant_id, journal_data, zoho_org_id)
        elif provider == "financio":
            result = self._export_financio(journal_data)
        elif provider == "csv":
            result = self._export_csv(journal_data)
        elif provider == "json":
            result = self._export_json(journal_data)
        else:
            raise ClaimsSyncError(f"Unknown accounting provider: {provider}")

        # Enrich result with sync metadata
        result["claim_ids"] = claim_ids
        result["claims_count"] = len(claims)
        result["grand_total"] = round(grand_total, 2)
        result["categories"] = {k: round(v, 2) for k, v in category_totals.items()}
        result["journal_date"] = journal_date

        logger.info(
            "Synced %d claims ($%.2f) to %s for tenant=%s",
            len(claims),
            grand_total,
            provider,
            tenant_id,
        )

        return result

    # ------------------------------------------------------------------
    # Provider routing
    # ------------------------------------------------------------------

    async def _post_to_xero(
        self,
        tenant_id: str,
        journal_data: dict,
        xero_tenant_id: Optional[str],
    ) -> dict:
        """Post claims journal to Xero."""
        from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

        adapter = get_xero_adapter()
        return await adapter.post_claims_journal(
            tenant_id=tenant_id,
            claims_data=journal_data,
            xero_tenant_id=xero_tenant_id,
        )

    async def _post_to_quickbooks(
        self,
        tenant_id: str,
        journal_data: dict,
        qbo_realm_id: Optional[str],
    ) -> dict:
        """Post claims journal to QuickBooks."""
        from hr_advisory.mcp_servers.adapters.quickbooks import get_quickbooks_adapter

        adapter = get_quickbooks_adapter()
        return await adapter.post_journal_entry(
            tenant_id=tenant_id,
            journal_data=journal_data,
            realm_id=qbo_realm_id,
        )

    async def _post_to_zoho(
        self,
        tenant_id: str,
        journal_data: dict,
        zoho_org_id: Optional[str],
    ) -> dict:
        """Post claims journal to Zoho Books."""
        from hr_advisory.mcp_servers.adapters.zoho import get_zoho_adapter

        adapter = get_zoho_adapter()
        return await adapter.post_journal(
            tenant_id=tenant_id,
            journal_data=journal_data,
            organization_id=zoho_org_id,
        )

    def _export_financio(self, journal_data: dict) -> dict:
        """Export claims journal as Financio GL posting file."""
        from hr_advisory.mcp_servers.adapters.financio import get_financio_adapter

        adapter = get_financio_adapter()
        content = adapter.export_claims_journal(journal_data)
        return {
            "status": "exported",
            "provider": "financio",
            "format": "text/tab-separated-values",
            "content": content,
            "line_count": len(journal_data.get("lines", [])),
        }

    def _export_csv(self, journal_data: dict) -> dict:
        """Export claims journal as generic CSV."""
        from hr_advisory.mcp_servers.adapters.generic_export import get_generic_export_adapter

        adapter = get_generic_export_adapter()
        content = adapter.export_csv(journal_data)
        return {
            "status": "exported",
            "provider": "csv",
            "format": "text/csv",
            "content": content,
            "line_count": len(journal_data.get("lines", [])),
        }

    def _export_json(self, journal_data: dict) -> dict:
        """Export claims journal as structured JSON."""
        from hr_advisory.mcp_servers.adapters.generic_export import get_generic_export_adapter

        adapter = get_generic_export_adapter()
        content = adapter.export_json(journal_data)
        return {
            "status": "exported",
            "provider": "json",
            "format": "application/json",
            "content": content,
            "line_count": len(journal_data.get("lines", [])),
        }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_supported_categories(self) -> list[dict]:
        """Return list of supported claim categories with account mappings."""
        return [
            {
                "category": category,
                "account_code": mapping["account_code"],
                "account_name": mapping["account_name"],
            }
            for category, mapping in sorted(self._account_map.items())
        ]

    def update_account_mapping(
        self,
        category: str,
        account_code: str,
        account_name: str,
        account_id: str = "",
    ) -> None:
        """Update the account mapping for a claim category.

        Used when the company customizes their chart of accounts.
        """
        self._account_map[category] = {
            "account_code": account_code,
            "account_name": account_name,
            "account_id": account_id,
            "description": f"{account_name} ({category})",
        }
        logger.info(
            "Updated claims account mapping: %s -> %s %s", category, account_code, account_name
        )


# Module-level singleton
_adapter: Optional[ClaimsSyncAdapter] = None


def get_claims_sync_adapter() -> ClaimsSyncAdapter:
    """Get or create the claims sync adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = ClaimsSyncAdapter()
    return _adapter
