"""Generic accounting export adapter.

Generates standard journal entry files (CSV, JSON) compatible with
any accounting software. Used as a fallback when no direct API
integration is available.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

PROVIDER_NAME = "generic"


class GenericExportError(Exception):
    """Raised when export generation fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Export error: {detail}")


class GenericExportAdapter:
    """Adapter for generic accounting file export.

    Generates standard CSV and JSON formats that can be imported
    into any accounting software (Xero, QBO, Zoho, MYOB, Sage, etc.)

    Usage::

        adapter = GenericExportAdapter()
        csv_content = adapter.export_csv(payroll_data)
        json_content = adapter.export_json(payroll_data)
    """

    def export_csv(
        self,
        payroll_data: dict,
        include_header_comment: bool = True,
    ) -> str:
        """Generate a standard journal entry CSV file.

        The CSV format uses a common layout accepted by most accounting
        platforms: Date, Account Code, Account Name, Debit, Credit,
        Reference, Description, Tax Code.

        Args:
            payroll_data: Dict with:
                - date: str (ISO YYYY-MM-DD)
                - reference: str (e.g., "PAYROLL-2026-03")
                - company_name: str (optional)
                - currency: str (default "SGD")
                - lines: list of dicts with:
                    - account_code: str
                    - account_name: str
                    - description: str
                    - amount: float (positive = debit, negative = credit)
                    - tax_code: str (optional, e.g., "SR" for SG GST)
            include_header_comment: Whether to include metadata as comment rows.

        Returns:
            CSV content as a string.
        """
        lines = payroll_data.get("lines", [])
        if not lines:
            raise GenericExportError("No journal lines provided")

        journal_date = payroll_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        reference = payroll_data.get("reference", "")
        company_name = payroll_data.get("company_name", "")
        currency = payroll_data.get("currency", "SGD")

        # Validate balance
        total_debit = sum(l["amount"] for l in lines if l["amount"] > 0)
        total_credit = sum(abs(l["amount"]) for l in lines if l["amount"] < 0)
        if abs(total_debit - total_credit) > 0.01:
            raise GenericExportError(
                f"Journal does not balance: debits={total_debit:.2f}, "
                f"credits={total_credit:.2f}"
            )

        output = io.StringIO()
        writer = csv.writer(output)

        # Optional metadata comment rows
        if include_header_comment:
            writer.writerow(["# Journal Entry Export"])
            writer.writerow([f"# Date: {journal_date}"])
            if company_name:
                writer.writerow([f"# Company: {company_name}"])
            writer.writerow([f"# Reference: {reference}"])
            writer.writerow([f"# Currency: {currency}"])
            writer.writerow(
                [f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"]
            )
            writer.writerow([])

        # Column headers
        writer.writerow(
            [
                "Date",
                "Account Code",
                "Account Name",
                "Debit",
                "Credit",
                "Reference",
                "Description",
                "Tax Code",
                "Currency",
            ]
        )

        # Detail lines
        for line in lines:
            amount = line["amount"]
            debit = f"{amount:.2f}" if amount > 0 else ""
            credit = f"{abs(amount):.2f}" if amount < 0 else ""

            writer.writerow(
                [
                    journal_date,
                    line.get("account_code", ""),
                    line.get("account_name", ""),
                    debit,
                    credit,
                    reference,
                    line.get("description", ""),
                    line.get("tax_code", ""),
                    currency,
                ]
            )

        # Summary row
        writer.writerow([])
        writer.writerow(
            [
                "",
                "",
                "TOTAL",
                f"{total_debit:.2f}",
                f"{total_credit:.2f}",
                "",
                "",
                "",
                "",
            ]
        )

        content = output.getvalue()

        logger.info(
            "Generated CSV journal export: %d lines, ref=%s, total=%.2f",
            len(lines),
            reference,
            total_debit,
        )

        return content

    def export_json(
        self,
        payroll_data: dict,
    ) -> str:
        """Generate a structured JSON journal entry export.

        The JSON format is designed for maximum interoperability.
        It includes metadata, a validated list of journal lines,
        and summary totals.

        Args:
            payroll_data: Dict with same structure as export_csv.

        Returns:
            Pretty-printed JSON string.
        """
        lines = payroll_data.get("lines", [])
        if not lines:
            raise GenericExportError("No journal lines provided")

        journal_date = payroll_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        reference = payroll_data.get("reference", "")
        company_name = payroll_data.get("company_name", "")
        currency = payroll_data.get("currency", "SGD")

        # Build structured line items
        structured_lines = []
        total_debit = 0.0
        total_credit = 0.0

        for line in lines:
            amount = line["amount"]
            entry: dict = {
                "account_code": line.get("account_code", ""),
                "account_name": line.get("account_name", ""),
                "description": line.get("description", ""),
            }

            if amount >= 0:
                entry["debit"] = round(amount, 2)
                entry["credit"] = 0.0
                total_debit += amount
            else:
                entry["debit"] = 0.0
                entry["credit"] = round(abs(amount), 2)
                total_credit += abs(amount)

            if line.get("tax_code"):
                entry["tax_code"] = line["tax_code"]

            structured_lines.append(entry)

        # Validate balance
        if abs(total_debit - total_credit) > 0.01:
            raise GenericExportError(
                f"Journal does not balance: debits={total_debit:.2f}, "
                f"credits={total_credit:.2f}"
            )

        export = {
            "export_format": "aite_journal_v1",
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "company_name": company_name,
                "currency": currency,
                "source": "AITE HR Advisory Platform",
            },
            "journal_entry": {
                "date": journal_date,
                "reference": reference,
                "status": "draft",
                "lines": structured_lines,
            },
            "summary": {
                "total_debit": round(total_debit, 2),
                "total_credit": round(total_credit, 2),
                "line_count": len(structured_lines),
                "balanced": abs(total_debit - total_credit) < 0.01,
            },
        }

        content = json.dumps(export, indent=2, ensure_ascii=False)

        logger.info(
            "Generated JSON journal export: %d lines, ref=%s, total=%.2f",
            len(lines),
            reference,
            total_debit,
        )

        return content

    def export_payroll_summary_csv(
        self,
        payroll_run: dict,
        payslips: list[dict],
        employees: list[dict],
    ) -> str:
        """Generate a payroll summary CSV for accounting reconciliation.

        This is not a journal entry but a detailed payroll register
        showing each employee's gross, deductions, and net pay.

        Args:
            payroll_run: Payroll run dict with period, pay_date.
            payslips: List of payslip dicts.
            employees: List of employee dicts.

        Returns:
            CSV content with payroll summary.
        """
        emp_by_id = {e.get("id"): e for e in employees}
        period = f"{payroll_run.get('period_start', '')} to {payroll_run.get('period_end', '')}"

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["# Payroll Register"])
        writer.writerow([f"# Period: {period}"])
        writer.writerow([f"# Pay Date: {payroll_run.get('pay_date', '')}"])
        writer.writerow([])

        writer.writerow(
            [
                "Employee Name",
                "Employee ID",
                "Basic Salary",
                "Gross Salary",
                "Employee CPF",
                "Employer CPF",
                "SDL",
                "Net Salary",
            ]
        )

        total_basic = 0.0
        total_gross = 0.0
        total_emp_cpf = 0.0
        total_er_cpf = 0.0
        total_sdl = 0.0
        total_net = 0.0

        for ps in payslips:
            emp = emp_by_id.get(ps.get("employee_id"), {})
            name = emp.get("name", "") or emp.get("employee_name", "Employee")
            emp_id = emp.get("employee_id_internal", "")

            basic = ps.get("basic_salary", 0.0)
            gross = ps.get("gross_salary", 0.0)
            emp_cpf = ps.get("employee_cpf", 0.0)
            er_cpf = ps.get("employer_cpf", 0.0)
            sdl = ps.get("sdl", 0.0)
            net = ps.get("net_salary", 0.0)

            writer.writerow(
                [
                    name,
                    emp_id,
                    f"{basic:.2f}",
                    f"{gross:.2f}",
                    f"{emp_cpf:.2f}",
                    f"{er_cpf:.2f}",
                    f"{sdl:.2f}",
                    f"{net:.2f}",
                ]
            )

            total_basic += basic
            total_gross += gross
            total_emp_cpf += emp_cpf
            total_er_cpf += er_cpf
            total_sdl += sdl
            total_net += net

        writer.writerow([])
        writer.writerow(
            [
                "TOTAL",
                "",
                f"{total_basic:.2f}",
                f"{total_gross:.2f}",
                f"{total_emp_cpf:.2f}",
                f"{total_er_cpf:.2f}",
                f"{total_sdl:.2f}",
                f"{total_net:.2f}",
            ]
        )

        content = output.getvalue()
        logger.info("Generated payroll summary CSV: %d employees", len(payslips))
        return content


# Module-level singleton
_adapter: Optional[GenericExportAdapter] = None


def get_generic_export_adapter() -> GenericExportAdapter:
    """Get or create the generic export adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = GenericExportAdapter()
    return _adapter
