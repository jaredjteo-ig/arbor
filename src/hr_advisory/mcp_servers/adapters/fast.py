"""FAST payment file generators for DBS IDEAL and UOB BIBPlus.

Generates bank-specific file formats for same-day FAST salary transfers.
FAST (Fast And Secure Transfers) settles in real-time via the FAST
clearing network operated by the Banking Computer Services (BCS).

DBS IDEAL: Proprietary fixed-width format for DBS corporate e-banking.
UOB BIBPlus: Pipe-delimited format for UOB bulk FAST/GIRO uploads.
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

PROVIDER_NAME = "fast"

# DBS IDEAL FAST format field widths
# Record Type (1) | Receiving Bank (4) | Account No (20) | Amount cents (15)
# | Emp Name (40) | Reference (20) | Payment Type (4) | Instruction (35)
DBS_PAYMENT_TYPE_FAST = "FAST"
DBS_PAYMENT_TYPE_GIRO = "GIRO"

# UOB BIBPlus delimiter
UOB_DELIMITER = "|"


class FASTGenerationError(Exception):
    """Raised when FAST payment file generation fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"FAST generation error: {detail}")


class FASTAdapter:
    """FAST payment file generator for DBS and UOB.

    Generates bank-specific file formats for bulk FAST salary transfers.
    These files are uploaded to the bank's corporate e-banking portal
    for same-day settlement.

    Usage::

        adapter = FASTAdapter()

        dbs_content = adapter.generate_dbs_fast(
            payroll_run={"id": "PR-2026-03", "pay_date": "2026-03-25", ...},
            payslips=[{"employee_id": "emp1", "net_salary": 4500.00, ...}],
            employees=[{"id": "emp1", "bank_code": "7023", ...}],
        )

        uob_content = adapter.generate_uob_fast(
            payroll_run={"id": "PR-2026-03", "pay_date": "2026-03-25", ...},
            payslips=[{"employee_id": "emp1", "net_salary": 4500.00, ...}],
            employees=[{"id": "emp1", "bank_code": "7171", ...}],
        )
    """

    def generate_dbs_fast(
        self,
        payroll_run: dict,
        payslips: list[dict],
        employees: list[dict],
        company_id: Optional[str] = None,
    ) -> str:
        """Generate DBS IDEAL FAST payment file.

        DBS IDEAL format:
        - Header record (H): originator info, dates, company ID
        - Detail records (D): one per employee payment
        - Trailer record (T): totals and count

        Fixed-width format with specific field positions.

        Args:
            payroll_run: Dict with id, pay_date, company_id.
            payslips: List of payslip dicts with employee_id, net_salary.
            employees: List of employee dicts with id, bank_code,
                bank_account_number, name.
            company_id: Override company ID / UEN (uses payroll_run.company_id).

        Returns:
            Fixed-width text content for DBS IDEAL upload.
        """
        emp_by_id = {e.get("id"): e for e in employees}
        pay_date_str = payroll_run.get("pay_date", "")
        run_id = str(payroll_run.get("id", ""))
        cid = company_id or str(payroll_run.get("company_id", ""))

        if not pay_date_str:
            raise FASTGenerationError("pay_date is required in payroll_run")

        # Parse and format date as DDMMYYYY
        try:
            pd = date.fromisoformat(pay_date_str)
            formatted_date = f"{pd.day:02d}{pd.month:02d}{pd.year}"
        except (ValueError, TypeError):
            raise FASTGenerationError(f"Invalid pay_date format: {pay_date_str}")

        # Creation date (today)
        creation_date = datetime.now(timezone.utc).strftime("%d%m%Y")

        lines: list[str] = []

        # ------------------------------------------------------------------
        # Header record
        # ------------------------------------------------------------------
        # H | Originator (20) | Creation Date (8) | Value Date (8) | Company ID (12) | Payment Type (4)
        header = (
            "H"
            + " " * 20  # Originator (blank for FAST, bank fills)
            + creation_date.ljust(8)
            + formatted_date.ljust(8)
            + cid.rjust(12)
            + DBS_PAYMENT_TYPE_FAST.ljust(4)
        )
        lines.append(header)

        # ------------------------------------------------------------------
        # Detail records
        # ------------------------------------------------------------------
        total_cents = 0
        count = 0

        for ps in payslips:
            emp_id = ps.get("employee_id", "")
            emp = emp_by_id.get(emp_id, {})
            net_salary = ps.get("net_salary", 0.0)

            if net_salary <= 0:
                continue

            amount_cents = int(round(net_salary * 100))
            total_cents += amount_cents
            count += 1

            emp_name = emp.get("name", "") or emp.get("employee_name", "Employee")
            bank_code = emp.get("bank_code", "").strip()
            account_no = emp.get("bank_account_number", "").strip()
            reference = f"SAL-{run_id}"

            # D | Receiving Bank (4) | Account No (20) | Amount in cents (15)
            # | Employee Name (40) | Reference (20) | Payment Type (4)
            # | Instruction (35)
            detail = (
                "D"
                + bank_code.rjust(4)
                + account_no.rjust(20)
                + str(amount_cents).zfill(15)
                + emp_name.ljust(40)[:40]
                + reference.ljust(20)[:20]
                + DBS_PAYMENT_TYPE_FAST.ljust(4)
                + f"Salary {payroll_run.get('period_start', '')}".ljust(35)[:35]
            )
            lines.append(detail)

        if count == 0:
            raise FASTGenerationError("No valid payment records")

        # ------------------------------------------------------------------
        # Trailer record
        # ------------------------------------------------------------------
        # T | Total Amount in cents (15) | Record count (6) | Hash Total (15)
        # Hash total = sum of all account numbers (for reconciliation)
        trailer = "T" + str(total_cents).zfill(15) + str(count).zfill(6)
        lines.append(trailer)

        content = "\n".join(lines) + "\n"

        logger.info(
            "Generated DBS FAST file: %d payments, total=$%.2f, run=%s",
            count,
            total_cents / 100,
            run_id,
        )

        return content

    def generate_uob_fast(
        self,
        payroll_run: dict,
        payslips: list[dict],
        employees: list[dict],
        company_account: Optional[str] = None,
    ) -> str:
        """Generate UOB BIBPlus bulk FAST/GIRO payment file.

        UOB BIBPlus format (v3.04):
        - Pipe-delimited (|) records
        - Header row: H|record_type|company_account|value_date|...
        - Detail rows: D|seq|beneficiary_name|bank_code|account_no|amount|reference|...
        - Trailer row: T|total_amount|record_count

        Args:
            payroll_run: Dict with id, pay_date, company_id.
            payslips: List of payslip dicts.
            employees: List of employee dicts.
            company_account: Originator's UOB account number.

        Returns:
            Pipe-delimited text content for UOB BIBPlus upload.
        """
        emp_by_id = {e.get("id"): e for e in employees}
        pay_date_str = payroll_run.get("pay_date", "")
        run_id = str(payroll_run.get("id", ""))
        company_acct = company_account or str(payroll_run.get("company_account", ""))

        if not pay_date_str:
            raise FASTGenerationError("pay_date is required in payroll_run")

        # Parse and format date as DDMMYYYY
        try:
            pd = date.fromisoformat(pay_date_str)
            formatted_date = f"{pd.day:02d}{pd.month:02d}{pd.year}"
        except (ValueError, TypeError):
            raise FASTGenerationError(f"Invalid pay_date format: {pay_date_str}")

        lines: list[str] = []

        # ------------------------------------------------------------------
        # Header record
        # ------------------------------------------------------------------
        header_fields = [
            "H",  # Record type
            "FAST",  # Payment type
            company_acct,  # Debit account number
            formatted_date,  # Value date (DDMMYYYY)
            "SGD",  # Currency
            "N",  # Batch booking (N=individual)
            run_id,  # Batch reference
        ]
        lines.append(UOB_DELIMITER.join(header_fields))

        # ------------------------------------------------------------------
        # Detail records
        # ------------------------------------------------------------------
        total_amount = 0.0
        count = 0
        seq = 0

        for ps in payslips:
            emp_id = ps.get("employee_id", "")
            emp = emp_by_id.get(emp_id, {})
            net_salary = ps.get("net_salary", 0.0)

            if net_salary <= 0:
                continue

            total_amount += net_salary
            count += 1
            seq += 1

            emp_name = emp.get("name", "") or emp.get("employee_name", "Employee")
            bank_code = emp.get("bank_code", "").strip()
            account_no = emp.get("bank_account_number", "").strip()
            reference = f"SAL-{run_id}-{seq:04d}"
            period_desc = (
                f"Salary {payroll_run.get('period_start', '')} "
                f"to {payroll_run.get('period_end', '')}"
            )

            detail_fields = [
                "D",  # Record type
                str(seq),  # Sequence number
                emp_name[:40],  # Beneficiary name (max 40)
                bank_code,  # Receiving bank code
                account_no,  # Beneficiary account number
                f"{net_salary:.2f}",  # Amount
                "SGD",  # Currency
                reference[:20],  # Payment reference (max 20)
                period_desc[:35],  # Payment details (max 35)
                "",  # Beneficiary email (optional)
                "",  # Beneficiary phone (optional)
            ]
            lines.append(UOB_DELIMITER.join(detail_fields))

        if count == 0:
            raise FASTGenerationError("No valid payment records")

        # ------------------------------------------------------------------
        # Trailer record
        # ------------------------------------------------------------------
        trailer_fields = [
            "T",  # Record type
            f"{total_amount:.2f}",  # Total amount
            str(count),  # Total record count
        ]
        lines.append(UOB_DELIMITER.join(trailer_fields))

        content = "\n".join(lines) + "\n"

        logger.info(
            "Generated UOB FAST file: %d payments, total=$%.2f, run=%s",
            count,
            total_amount,
            run_id,
        )

        return content


# Module-level singleton
_adapter: Optional[FASTAdapter] = None


def get_fast_adapter() -> FASTAdapter:
    """Get or create the FAST adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = FASTAdapter()
    return _adapter
