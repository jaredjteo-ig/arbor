"""ISO 20022 GIRO payment file generator.

Generates pain.001.001.03 XML files for bulk salary GIRO payments
compatible with all Singapore banks: DBS, OCBC, UOB, Maybank, HSBC,
Standard Chartered.

ISO 20022 standard: urn:iso:std:iso:20022:tech:xsd:pain.001.001.03
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

logger = logging.getLogger(__name__)

# ISO 20022 namespace
PAIN001_NAMESPACE = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"

# Singapore bank BIC/SWIFT codes
SG_BANK_BIC: dict[str, str] = {
    "DBS": "DBSSSGSG",
    "POSB": "DBSSSGSG",  # POSB is DBS
    "OCBC": "OCBCSGSG",
    "UOB": "UOVBSGSG",
    "MAYBANK": "MBBESGSG",
    "HSBC": "HSBCSGSG",
    "SCB": "SCBLSGSG",  # Standard Chartered
    "CITI": "CITISGSG",
    "BOC": "BKCHSGSG",  # Bank of China
    "ICBC": "ICBKSGSG",
}

# Bank codes to BIC mapping (MAS clearing codes)
SG_BANK_CODE_TO_BIC: dict[str, str] = {
    "7171": "DBSSSGSG",  # DBS
    "7339": "DBSSSGSG",  # POSB
    "7023": "OCBCSGSG",  # OCBC
    "7375": "UOVBSGSG",  # UOB
    "7302": "MBBESGSG",  # Maybank
    "7232": "HSBCSGSG",  # HSBC
    "7153": "SCBLSGSG",  # Standard Chartered
    "7214": "CITISGSG",  # Citibank
    "7065": "BKCHSGSG",  # Bank of China
    "7153": "SCBLSGSG",  # SCB
}

# Payment purpose codes (ISO 20022 Category Purpose)
PURPOSE_SALARY = "SALA"
PURPOSE_BONUS = "BONU"
PURPOSE_PENSION = "PENS"

PROVIDER_NAME = "giro_iso20022"


class GiroGenerationError(Exception):
    """Raised when GIRO file generation fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"GIRO generation error: {detail}")


class GiroAdapter:
    """ISO 20022 pain.001.001.03 GIRO payment file generator.

    Generates XML payment instruction files that can be uploaded to
    any Singapore bank's corporate e-banking portal for bulk salary
    GIRO payments.

    Usage::

        adapter = GiroAdapter()
        xml_content = adapter.generate_pain001(
            payroll_run={"id": "PR-2026-03", "pay_date": "2026-03-25", ...},
            payslips=[{"employee_id": "emp1", "net_salary": 4500.00, ...}],
            employees=[{"id": "emp1", "bank_code": "7171", "bank_account_number": "...", ...}],
            bank_config={"originator_name": "ACME PTE LTD", "originator_account": "...", ...},
        )
    """

    def generate_pain001(
        self,
        payroll_run: dict,
        payslips: list[dict],
        employees: list[dict],
        bank_config: dict,
    ) -> str:
        """Generate ISO 20022 pain.001.001.03 XML for bulk salary GIRO.

        Args:
            payroll_run: Dict with:
                - id: str (payroll run ID, used as message ID)
                - pay_date: str (ISO YYYY-MM-DD, requested execution date)
                - period_start: str
                - period_end: str
                - company_id: str
            payslips: List of payslip dicts with:
                - employee_id: str
                - net_salary: float
            employees: List of employee dicts with:
                - id: str
                - name: str (or employee_name)
                - bank_code: str (4-digit MAS clearing code)
                - bank_account_number: str
                - bank_name: str (optional, for BIC lookup)
            bank_config: Dict with:
                - originator_name: str (company legal name)
                - originator_account: str (company bank account number)
                - originator_bank_bic: str (company bank BIC/SWIFT)
                - originator_bank_code: str (4-digit, alternative to BIC)
                - uen: str (company UEN, used as Organization ID)
                - batch_booking: bool (default True)
                - charge_bearer: str (default "SLEV" = service level)

        Returns:
            Pretty-printed XML string (pain.001.001.03).

        Raises:
            GiroGenerationError: If required fields are missing or validation fails.
        """
        emp_by_id = {e.get("id"): e for e in employees}
        pay_date = payroll_run.get("pay_date", "")
        run_id = str(payroll_run.get("id", ""))

        if not pay_date:
            raise GiroGenerationError("pay_date is required in payroll_run")

        # Filter to payslips with positive net salary
        valid_payslips = [ps for ps in payslips if ps.get("net_salary", 0) > 0]
        if not valid_payslips:
            raise GiroGenerationError("No payslips with positive net salary")

        originator_name = bank_config.get("originator_name", "")
        originator_account = bank_config.get("originator_account", "")
        originator_bic = bank_config.get("originator_bank_bic", "")
        originator_bank_code = bank_config.get("originator_bank_code", "")
        uen = bank_config.get("uen", "")
        batch_booking = bank_config.get("batch_booking", True)
        charge_bearer = bank_config.get("charge_bearer", "SLEV")

        if not originator_name:
            raise GiroGenerationError("originator_name is required in bank_config")
        if not originator_account:
            raise GiroGenerationError("originator_account is required in bank_config")

        # Resolve originator BIC from bank code if not provided
        if not originator_bic and originator_bank_code:
            originator_bic = SG_BANK_CODE_TO_BIC.get(originator_bank_code, "")

        if not originator_bic:
            raise GiroGenerationError("originator_bank_bic or originator_bank_code is required")

        # Calculate totals
        total_amount = sum(ps.get("net_salary", 0) for ps in valid_payslips)
        num_transactions = len(valid_payslips)

        # Generate unique message ID
        msg_id = f"Arbor-{run_id}-{uuid.uuid4().hex[:8]}".upper()[:35]  # Max 35 chars
        creation_time = datetime.now(timezone.utc)

        # Build XML document
        root = Element("Document")
        root.set("xmlns", PAIN001_NAMESPACE)
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        cstmr_cdt_trf = SubElement(root, "CstmrCdtTrfInitn")

        # ------------------------------------------------------------------
        # Group Header (GrpHdr)
        # ------------------------------------------------------------------
        grp_hdr = SubElement(cstmr_cdt_trf, "GrpHdr")
        SubElement(grp_hdr, "MsgId").text = msg_id
        SubElement(grp_hdr, "CreDtTm").text = creation_time.strftime("%Y-%m-%dT%H:%M:%S")
        SubElement(grp_hdr, "NbOfTxs").text = str(num_transactions)
        SubElement(grp_hdr, "CtrlSum").text = f"{total_amount:.2f}"

        # Initiating party
        initg_pty = SubElement(grp_hdr, "InitgPty")
        SubElement(initg_pty, "Nm").text = originator_name[:70]
        if uen:
            initg_pty_id = SubElement(initg_pty, "Id")
            org_id = SubElement(initg_pty_id, "OrgId")
            other = SubElement(org_id, "Othr")
            SubElement(other, "Id").text = uen

        # ------------------------------------------------------------------
        # Payment Information (PmtInf)
        # ------------------------------------------------------------------
        pmt_inf = SubElement(cstmr_cdt_trf, "PmtInf")
        pmt_inf_id = f"PMT-{run_id}".upper()[:35]
        SubElement(pmt_inf, "PmtInfId").text = pmt_inf_id
        SubElement(pmt_inf, "PmtMtd").text = "TRF"  # Transfer
        SubElement(pmt_inf, "BtchBookg").text = "true" if batch_booking else "false"
        SubElement(pmt_inf, "NbOfTxs").text = str(num_transactions)
        SubElement(pmt_inf, "CtrlSum").text = f"{total_amount:.2f}"

        # Payment type information
        pmt_tp_inf = SubElement(pmt_inf, "PmtTpInf")
        svc_lvl = SubElement(pmt_tp_inf, "SvcLvl")
        SubElement(svc_lvl, "Cd").text = "NORM"  # Normal
        ctgy_purp = SubElement(pmt_tp_inf, "CtgyPurp")
        SubElement(ctgy_purp, "Cd").text = PURPOSE_SALARY

        # Requested execution date
        SubElement(pmt_inf, "ReqdExctnDt").text = pay_date

        # Debtor (originator/company)
        dbtr = SubElement(pmt_inf, "Dbtr")
        SubElement(dbtr, "Nm").text = originator_name[:70]
        if uen:
            dbtr_id = SubElement(dbtr, "Id")
            dbtr_org_id = SubElement(dbtr_id, "OrgId")
            dbtr_other = SubElement(dbtr_org_id, "Othr")
            SubElement(dbtr_other, "Id").text = uen

        # Debtor account
        dbtr_acct = SubElement(pmt_inf, "DbtrAcct")
        dbtr_acct_id = SubElement(dbtr_acct, "Id")
        dbtr_acct_id_other = SubElement(dbtr_acct_id, "Othr")
        SubElement(dbtr_acct_id_other, "Id").text = originator_account

        # Debtor agent (originator's bank)
        dbtr_agt = SubElement(pmt_inf, "DbtrAgt")
        dbtr_fin_instn = SubElement(dbtr_agt, "FinInstnId")
        SubElement(dbtr_fin_instn, "BIC").text = originator_bic

        # Charge bearer
        SubElement(pmt_inf, "ChrgBr").text = charge_bearer

        # ------------------------------------------------------------------
        # Credit Transfer Transaction Information (CdtTrfTxInf) per employee
        # ------------------------------------------------------------------
        for ps in valid_payslips:
            emp_id = ps.get("employee_id", "")
            emp = emp_by_id.get(emp_id, {})
            net_salary = ps.get("net_salary", 0)

            if net_salary <= 0:
                continue

            emp_name = emp.get("name", "") or emp.get("employee_name", "Employee")
            emp_bank_code = emp.get("bank_code", "")
            emp_account = emp.get("bank_account_number", "")
            emp_bank_name = emp.get("bank_name", "").upper()

            # Resolve employee's bank BIC
            emp_bic = SG_BANK_CODE_TO_BIC.get(emp_bank_code, "")
            if not emp_bic and emp_bank_name:
                emp_bic = SG_BANK_BIC.get(emp_bank_name, "")

            cdtrf = SubElement(pmt_inf, "CdtTrfTxInf")

            # Payment ID
            pmt_id = SubElement(cdtrf, "PmtId")
            end_to_end_id = f"SAL-{run_id}-{emp_id}"[:35]
            SubElement(pmt_id, "EndToEndId").text = end_to_end_id

            # Amount
            amt = SubElement(cdtrf, "Amt")
            instd_amt = SubElement(amt, "InstdAmt")
            instd_amt.set("Ccy", "SGD")
            instd_amt.text = f"{net_salary:.2f}"

            # Creditor agent (employee's bank)
            if emp_bic:
                cdtr_agt = SubElement(cdtrf, "CdtrAgt")
                cdtr_fin_instn = SubElement(cdtr_agt, "FinInstnId")
                SubElement(cdtr_fin_instn, "BIC").text = emp_bic

            # Creditor (employee)
            cdtr = SubElement(cdtrf, "Cdtr")
            SubElement(cdtr, "Nm").text = emp_name[:70]

            # Creditor account
            cdtr_acct = SubElement(cdtrf, "CdtrAcct")
            cdtr_acct_id = SubElement(cdtr_acct, "Id")
            cdtr_acct_other = SubElement(cdtr_acct_id, "Othr")
            SubElement(cdtr_acct_other, "Id").text = emp_account

            # Remittance information (creditor reference)
            rmt_inf = SubElement(cdtrf, "RmtInf")
            SubElement(rmt_inf, "Ustrd").text = (
                f"Salary {payroll_run.get('period_start', '')} to {payroll_run.get('period_end', '')}"
            )

        # ------------------------------------------------------------------
        # Serialize to pretty-printed XML
        # ------------------------------------------------------------------
        rough_string = tostring(root, encoding="unicode", xml_declaration=False)
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        pretty_xml = parseString(rough_string).toprettyxml(indent="  ", encoding=None)

        # Remove extra xml declaration added by minidom (we add our own)
        if pretty_xml.startswith("<?xml"):
            pretty_xml = pretty_xml.split("\n", 1)[1]

        content = xml_declaration + pretty_xml

        logger.info(
            "Generated ISO 20022 pain.001 GIRO file: %d transactions, " "total=%.2f SGD, msg_id=%s",
            num_transactions,
            total_amount,
            msg_id,
        )

        return content

    def validate_bank_config(self, bank_config: dict) -> list[str]:
        """Validate bank configuration for GIRO file generation.

        Returns list of validation errors (empty = valid).
        """
        errors = []

        if not bank_config.get("originator_name"):
            errors.append("originator_name is required")
        if not bank_config.get("originator_account"):
            errors.append("originator_account is required")

        has_bic = bool(bank_config.get("originator_bank_bic"))
        has_code = bool(bank_config.get("originator_bank_code"))

        if not has_bic and not has_code:
            errors.append("originator_bank_bic or originator_bank_code is required")
        elif has_code and bank_config["originator_bank_code"] not in SG_BANK_CODE_TO_BIC:
            errors.append(
                f"Unknown bank code: {bank_config['originator_bank_code']}. "
                f"Known codes: {', '.join(sorted(SG_BANK_CODE_TO_BIC.keys()))}"
            )

        return errors

    @staticmethod
    def get_supported_banks() -> list[dict]:
        """Return list of supported Singapore banks with BIC codes."""
        return [{"name": name, "bic": bic} for name, bic in sorted(SG_BANK_BIC.items())]


# Module-level singleton
_adapter: Optional[GiroAdapter] = None


def get_giro_adapter() -> GiroAdapter:
    """Get or create the GIRO adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = GiroAdapter()
    return _adapter
