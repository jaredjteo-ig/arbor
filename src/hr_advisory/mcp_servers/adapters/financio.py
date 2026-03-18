"""Financio (ABSS) GL Posting export adapter.

Generates text files in Financio GL Posting import format for
manual upload. No API integration yet (requires ABSS partnership).

Financio accepts fixed-width or CSV GL posting files that can be
imported via their "Import Transactions" feature.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Financio GL Posting format columns:
# Date | Account Code | Account Name | Debit | Credit | Reference | Description
FINANCIO_HEADER = "Date\tAccount Code\tAccount Name\tDebit\tCredit\tReference\tDescription"

PROVIDER_NAME = "financio"


class FinancioExportError(Exception):
    """Raised when Financio export generation fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Financio export error: {detail}")


class FinancioAdapter:
    """Adapter for Financio (ABSS) GL Posting file generation.

    Generates tab-delimited text files compatible with Financio's
    "Import Transactions" feature. This is a file-based fallback
    since Financio does not have a public API yet.

    Usage::

        adapter = FinancioAdapter()
        content = adapter.export_payroll_journal(payroll_data)
        # Save content as .txt file for manual import
    """

    def export_payroll_journal(
        self,
        payroll_data: dict,
        account_mapping: Optional[dict] = None,
    ) -> str:
        """Generate a Financio GL Posting text file from payroll data.

        Args:
            payroll_data: Dict with:
                - date: str (ISO YYYY-MM-DD)
                - reference: str (e.g., payroll run ID or period)
                - company_name: str
                - lines: list of dicts with:
                    - account_code: str
                    - account_name: str
                    - description: str
                    - amount: float (positive = debit, negative = credit)
            account_mapping: Optional dict mapping Arbor account types to
                Financio account codes. Used when chart of accounts differs.

        Returns:
            Tab-delimited text content for Financio import.
        """
        lines = payroll_data.get("lines", [])
        if not lines:
            raise FinancioExportError("No journal lines provided")

        journal_date = payroll_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        reference = payroll_data.get("reference", "PAYROLL")
        company_name = payroll_data.get("company_name", "")

        # Validate balance
        total_debit = sum(l["amount"] for l in lines if l["amount"] > 0)
        total_credit = sum(abs(l["amount"]) for l in lines if l["amount"] < 0)
        if abs(total_debit - total_credit) > 0.01:
            raise FinancioExportError(
                f"Journal does not balance: debits={total_debit:.2f}, "
                f"credits={total_credit:.2f}"
            )

        # Format date as DD/MM/YYYY for Financio
        try:
            d = datetime.strptime(journal_date, "%Y-%m-%d")
            formatted_date = d.strftime("%d/%m/%Y")
        except ValueError:
            formatted_date = journal_date

        output = io.StringIO()

        # File header with comment line
        output.write(f"# Financio GL Posting Import\n")
        output.write(
            f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        )
        if company_name:
            output.write(f"# Company: {company_name}\n")
        output.write(f"# Reference: {reference}\n")
        output.write(f"#\n")

        # Column headers
        output.write(f"{FINANCIO_HEADER}\n")

        # Detail lines
        for line in lines:
            amount = line["amount"]

            # Apply account mapping if provided
            account_code = line.get("account_code", "")
            account_name = line.get("account_name", "")

            if account_mapping and account_code in account_mapping:
                mapped = account_mapping[account_code]
                account_code = mapped.get("code", account_code)
                account_name = mapped.get("name", account_name)

            description = line.get("description", "")

            if amount >= 0:
                debit_str = f"{amount:.2f}"
                credit_str = ""
            else:
                debit_str = ""
                credit_str = f"{abs(amount):.2f}"

            output.write(
                f"{formatted_date}\t"
                f"{account_code}\t"
                f"{account_name}\t"
                f"{debit_str}\t"
                f"{credit_str}\t"
                f"{reference}\t"
                f"{description}\n"
            )

        # Summary footer (comment)
        output.write(f"#\n")
        output.write(f"# Total Debits: {total_debit:.2f}\n")
        output.write(f"# Total Credits: {total_credit:.2f}\n")
        output.write(f"# Lines: {len(lines)}\n")

        content = output.getvalue()

        logger.info(
            "Generated Financio GL posting file: %d lines, ref=%s",
            len(lines),
            reference,
        )

        return content

    def export_claims_journal(
        self,
        claims_data: dict,
        account_mapping: Optional[dict] = None,
    ) -> str:
        """Generate a Financio GL Posting file for claims reimbursements.

        Uses the same format as payroll journals. Claims are grouped by
        expense category with individual claim references.

        Args:
            claims_data: Dict with same structure as payroll_data.
            account_mapping: Optional account code mapping.

        Returns:
            Tab-delimited text content for Financio import.
        """
        # Claims use the same GL posting format
        return self.export_payroll_journal(claims_data, account_mapping)

    @staticmethod
    def get_default_account_mapping() -> dict:
        """Return default Financio account code mapping for SG payroll.

        These are common Financio/ABSS account codes for Singapore
        payroll entries. Actual codes depend on the company's chart
        of accounts in Financio.
        """
        return {
            "salary_expense": {
                "code": "6000",
                "name": "Salaries & Wages",
            },
            "cpf_employer": {
                "code": "6010",
                "name": "CPF - Employer Contribution",
            },
            "sdl": {
                "code": "6020",
                "name": "Skills Development Levy",
            },
            "fwl": {
                "code": "6030",
                "name": "Foreign Worker Levy",
            },
            "shg": {
                "code": "6040",
                "name": "Self-Help Group Fund",
            },
            "cpf_payable": {
                "code": "2100",
                "name": "CPF Payable",
            },
            "net_salary_payable": {
                "code": "2200",
                "name": "Net Salary Payable",
            },
            "claims_expense": {
                "code": "6100",
                "name": "Staff Claims & Reimbursements",
            },
            "claims_payable": {
                "code": "2300",
                "name": "Claims Payable",
            },
        }


# Module-level singleton
_adapter: Optional[FinancioAdapter] = None


def get_financio_adapter() -> FinancioAdapter:
    """Get or create the Financio adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = FinancioAdapter()
    return _adapter
