"""Integration tests for the ISO 20022 GIRO payment file adapter.

Tests:
- pain.001.001.03 XML generation and structure validation
- Correct ISO 20022 namespace
- BIC code resolution for DBS, OCBC, UOB
- Amount accuracy against input payslip data
- Employee count in GrpHdr
- Multi-employee, multi-bank scenarios
- Validation errors for missing fields and invalid bank codes
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from hr_advisory.mcp_servers.adapters.giro import (
    PAIN001_NAMESPACE,
    SG_BANK_BIC,
    SG_BANK_CODE_TO_BIC,
    GiroAdapter,
    GiroGenerationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NAMESPACE = {"ns": PAIN001_NAMESPACE}


@pytest.fixture()
def adapter() -> GiroAdapter:
    return GiroAdapter()


@pytest.fixture()
def bank_config() -> dict:
    return {
        "originator_name": "ACME PTE LTD",
        "originator_account": "0129876543",
        "originator_bank_bic": "DBSSSGSG",
        "uen": "201234567K",
        "batch_booking": True,
        "charge_bearer": "SLEV",
    }


@pytest.fixture()
def payroll_run() -> dict:
    return {
        "id": "PR-2026-03",
        "pay_date": "2026-03-25",
        "period_start": "2026-03-01",
        "period_end": "2026-03-31",
        "company_id": "company_100",
    }


@pytest.fixture()
def single_payslip() -> list[dict]:
    return [{"employee_id": "emp1", "net_salary": 4500.00}]


@pytest.fixture()
def single_employee() -> list[dict]:
    return [
        {
            "id": "emp1",
            "name": "Alice Tan",
            "bank_code": "7171",
            "bank_account_number": "0012345678",
        }
    ]


@pytest.fixture()
def multi_payslips() -> list[dict]:
    return [
        {"employee_id": "emp1", "net_salary": 4500.00},
        {"employee_id": "emp2", "net_salary": 3200.00},
        {"employee_id": "emp3", "net_salary": 5800.50},
    ]


@pytest.fixture()
def multi_employees() -> list[dict]:
    return [
        {
            "id": "emp1",
            "name": "Alice Tan",
            "bank_code": "7171",
            "bank_account_number": "0012345678",
        },
        {
            "id": "emp2",
            "name": "Bob Lee",
            "bank_code": "7023",
            "bank_account_number": "6543210987",
        },
        {
            "id": "emp3",
            "name": "Charlie Ng",
            "bank_code": "7375",
            "bank_account_number": "9988776655",
        },
    ]


def _strip_ns(root: ET.Element) -> ET.Element:
    """Remove the namespace prefix from all element tags for easier XPath queries."""
    ns_prefix = f"{{{PAIN001_NAMESPACE}}}"
    for el in root.iter():
        if el.tag.startswith(ns_prefix):
            el.tag = el.tag[len(ns_prefix) :]
    return root


def _parse_xml(xml_string: str) -> ET.Element:
    """Parse the generated XML and return the root <Document> element with namespace stripped."""
    raw = xml_string.split("\n", 1)[1] if xml_string.startswith("<?xml") else xml_string
    root = ET.fromstring(raw)
    return _strip_ns(root)


# ---------------------------------------------------------------------------
# XML Structure Tests
# ---------------------------------------------------------------------------


class TestPain001Structure:
    """Verify overall pain.001.001.03 XML structure."""

    def test_xml_is_parseable(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        assert root is not None

    def test_document_namespace(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        # Check the raw XML string contains the correct namespace declaration
        assert PAIN001_NAMESPACE in xml
        assert f'xmlns="{PAIN001_NAMESPACE}"' in xml
        # After namespace stripping, root tag should be "Document"
        root = _parse_xml(xml)
        assert root.tag == "Document"

    def test_xml_declaration_present(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_cstmr_cdt_trf_initn_present(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        initn = root.find("CstmrCdtTrfInitn")
        assert initn is not None, "CstmrCdtTrfInitn element must exist"

    def test_grp_hdr_present(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        grp_hdr = root.find(".//GrpHdr")
        assert grp_hdr is not None, "GrpHdr element must exist"

    def test_pmt_inf_present(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        pmt_inf = root.find(".//PmtInf")
        assert pmt_inf is not None, "PmtInf element must exist"

    def test_cdt_trf_tx_inf_present(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        tx_inf = root.find(".//CdtTrfTxInf")
        assert tx_inf is not None, "CdtTrfTxInf element must exist"


# ---------------------------------------------------------------------------
# GrpHdr Tests
# ---------------------------------------------------------------------------


class TestGroupHeader:
    """Verify GrpHdr element contents."""

    def test_msg_id_present_and_max_35_chars(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        msg_id = root.find(".//GrpHdr/MsgId")
        assert msg_id is not None
        assert 1 <= len(msg_id.text) <= 35

    def test_creation_datetime_format(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        cre_dt_tm = root.find(".//GrpHdr/CreDtTm")
        assert cre_dt_tm is not None
        # Should be ISO-like: YYYY-MM-DDTHH:MM:SS
        assert "T" in cre_dt_tm.text
        assert len(cre_dt_tm.text) >= 19

    def test_nb_of_txs_single_employee(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        nb_of_txs = root.find(".//GrpHdr/NbOfTxs")
        assert nb_of_txs.text == "1"

    def test_nb_of_txs_multi_employee(
        self, adapter, payroll_run, multi_payslips, multi_employees, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, multi_payslips, multi_employees, bank_config)
        root = _parse_xml(xml)
        nb_of_txs = root.find(".//GrpHdr/NbOfTxs")
        assert nb_of_txs.text == "3"

    def test_ctrl_sum_matches_total(
        self, adapter, payroll_run, multi_payslips, multi_employees, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, multi_payslips, multi_employees, bank_config)
        root = _parse_xml(xml)
        ctrl_sum = root.find(".//GrpHdr/CtrlSum")
        expected = sum(ps["net_salary"] for ps in multi_payslips)
        assert float(ctrl_sum.text) == pytest.approx(expected, abs=0.01)

    def test_initiating_party_name(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        nm = root.find(".//GrpHdr/InitgPty/Nm")
        assert nm.text == "ACME PTE LTD"

    def test_initiating_party_uen(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        org_id = root.find(".//GrpHdr/InitgPty/Id/OrgId/Othr/Id")
        assert org_id is not None
        assert org_id.text == "201234567K"


# ---------------------------------------------------------------------------
# PmtInf Tests
# ---------------------------------------------------------------------------


class TestPaymentInformation:
    """Verify PmtInf element contents."""

    def test_payment_method_is_transfer(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        pmt_mtd = root.find(".//PmtInf/PmtMtd")
        assert pmt_mtd.text == "TRF"

    def test_batch_booking_true_by_default(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        btch = root.find(".//PmtInf/BtchBookg")
        assert btch.text == "true"

    def test_category_purpose_is_salary(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        ctgy = root.find(".//PmtInf/PmtTpInf/CtgyPurp/Cd")
        assert ctgy.text == "SALA"

    def test_requested_execution_date(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        reqd = root.find(".//PmtInf/ReqdExctnDt")
        assert reqd.text == "2026-03-25"

    def test_debtor_name(self, adapter, payroll_run, single_payslip, single_employee, bank_config):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        dbtr_nm = root.find(".//PmtInf/Dbtr/Nm")
        assert dbtr_nm.text == "ACME PTE LTD"

    def test_debtor_account(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        dbtr_acct = root.find(".//PmtInf/DbtrAcct/Id/Othr/Id")
        assert dbtr_acct.text == "0129876543"

    def test_debtor_agent_bic(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        bic = root.find(".//PmtInf/DbtrAgt/FinInstnId/BIC")
        assert bic.text == "DBSSSGSG"

    def test_charge_bearer(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        chrg = root.find(".//PmtInf/ChrgBr")
        assert chrg.text == "SLEV"


# ---------------------------------------------------------------------------
# CdtTrfTxInf Tests (per-employee transaction)
# ---------------------------------------------------------------------------


class TestCreditTransferTransaction:
    """Verify per-employee CdtTrfTxInf elements."""

    def test_amount_matches_payslip(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        instd_amt = root.find(".//CdtTrfTxInf/Amt/InstdAmt")
        assert instd_amt.text == "4500.00"
        assert instd_amt.get("Ccy") == "SGD"

    def test_creditor_name(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        cdtr_nm = root.find(".//CdtTrfTxInf/Cdtr/Nm")
        assert cdtr_nm.text == "Alice Tan"

    def test_creditor_account(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        cdtr_acct = root.find(".//CdtTrfTxInf/CdtrAcct/Id/Othr/Id")
        assert cdtr_acct.text == "0012345678"

    def test_employee_bank_bic_dbs(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        bic = root.find(".//CdtTrfTxInf/CdtrAgt/FinInstnId/BIC")
        assert bic is not None
        assert bic.text == "DBSSSGSG"

    def test_end_to_end_id_present(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        e2e = root.find(".//CdtTrfTxInf/PmtId/EndToEndId")
        assert e2e is not None
        assert len(e2e.text) <= 35

    def test_remittance_information(
        self, adapter, payroll_run, single_payslip, single_employee, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, bank_config)
        root = _parse_xml(xml)
        ustrd = root.find(".//CdtTrfTxInf/RmtInf/Ustrd")
        assert "2026-03-01" in ustrd.text
        assert "2026-03-31" in ustrd.text


# ---------------------------------------------------------------------------
# Multi-bank Tests
# ---------------------------------------------------------------------------


class TestMultiBankScenario:
    """Verify correct BIC resolution for employees at different banks."""

    def test_three_transactions_generated(
        self, adapter, payroll_run, multi_payslips, multi_employees, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, multi_payslips, multi_employees, bank_config)
        root = _parse_xml(xml)
        tx_list = root.findall(".//CdtTrfTxInf")
        assert len(tx_list) == 3

    def test_bic_codes_per_employee(
        self, adapter, payroll_run, multi_payslips, multi_employees, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, multi_payslips, multi_employees, bank_config)
        root = _parse_xml(xml)
        tx_list = root.findall(".//CdtTrfTxInf")
        bics = [tx.find("CdtrAgt/FinInstnId/BIC").text for tx in tx_list]
        # emp1=DBS (7171), emp2=OCBC (7023), emp3=UOB (7375)
        assert bics == ["DBSSSGSG", "OCBCSGSG", "UOVBSGSG"]

    def test_amounts_match_each_payslip(
        self, adapter, payroll_run, multi_payslips, multi_employees, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, multi_payslips, multi_employees, bank_config)
        root = _parse_xml(xml)
        tx_list = root.findall(".//CdtTrfTxInf")
        amounts = [float(tx.find("Amt/InstdAmt").text) for tx in tx_list]
        assert amounts == pytest.approx([4500.00, 3200.00, 5800.50], abs=0.01)

    def test_ctrl_sum_in_pmt_inf_matches(
        self, adapter, payroll_run, multi_payslips, multi_employees, bank_config
    ):
        xml = adapter.generate_pain001(payroll_run, multi_payslips, multi_employees, bank_config)
        root = _parse_xml(xml)
        ctrl_sum = root.find(".//PmtInf/CtrlSum")
        expected = 4500.00 + 3200.00 + 5800.50
        assert float(ctrl_sum.text) == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# BIC Code Verification
# ---------------------------------------------------------------------------


class TestBICCodes:
    """Verify BIC/SWIFT code constants are correct."""

    def test_dbs_bic(self):
        assert SG_BANK_BIC["DBS"] == "DBSSSGSG"

    def test_posb_bic_is_dbs(self):
        assert SG_BANK_BIC["POSB"] == "DBSSSGSG"

    def test_ocbc_bic(self):
        assert SG_BANK_BIC["OCBC"] == "OCBCSGSG"

    def test_uob_bic(self):
        assert SG_BANK_BIC["UOB"] == "UOVBSGSG"

    def test_bank_code_7171_is_dbs(self):
        assert SG_BANK_CODE_TO_BIC["7171"] == "DBSSSGSG"

    def test_bank_code_7023_is_ocbc(self):
        assert SG_BANK_CODE_TO_BIC["7023"] == "OCBCSGSG"

    def test_bank_code_7375_is_uob(self):
        assert SG_BANK_CODE_TO_BIC["7375"] == "UOVBSGSG"


# ---------------------------------------------------------------------------
# Bank Config via bank_code (no BIC)
# ---------------------------------------------------------------------------


class TestBankCodeResolution:
    """Verify originator BIC is resolved from bank_code when BIC not given."""

    def test_originator_bic_from_bank_code(
        self, adapter, payroll_run, single_payslip, single_employee
    ):
        config = {
            "originator_name": "ACME PTE LTD",
            "originator_account": "0129876543",
            "originator_bank_code": "7171",
            "uen": "201234567K",
        }
        xml = adapter.generate_pain001(payroll_run, single_payslip, single_employee, config)
        root = _parse_xml(xml)
        bic = root.find(".//PmtInf/DbtrAgt/FinInstnId/BIC")
        assert bic.text == "DBSSSGSG"


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    """Verify generate_pain001 raises GiroGenerationError for invalid input."""

    def test_missing_pay_date_raises(self, adapter, single_payslip, single_employee, bank_config):
        run = {"id": "PR-001"}
        with pytest.raises(GiroGenerationError, match="pay_date is required"):
            adapter.generate_pain001(run, single_payslip, single_employee, bank_config)

    def test_empty_payslips_raises(self, adapter, payroll_run, single_employee, bank_config):
        with pytest.raises(GiroGenerationError, match="No payslips with positive net salary"):
            adapter.generate_pain001(payroll_run, [], single_employee, bank_config)

    def test_zero_salary_payslips_raises(self, adapter, payroll_run, single_employee, bank_config):
        payslips = [{"employee_id": "emp1", "net_salary": 0}]
        with pytest.raises(GiroGenerationError, match="No payslips with positive net salary"):
            adapter.generate_pain001(payroll_run, payslips, single_employee, bank_config)

    def test_missing_originator_name_raises(
        self, adapter, payroll_run, single_payslip, single_employee
    ):
        config = {
            "originator_account": "0129876543",
            "originator_bank_bic": "DBSSSGSG",
        }
        with pytest.raises(GiroGenerationError, match="originator_name is required"):
            adapter.generate_pain001(payroll_run, single_payslip, single_employee, config)

    def test_missing_originator_account_raises(
        self, adapter, payroll_run, single_payslip, single_employee
    ):
        config = {
            "originator_name": "ACME PTE LTD",
            "originator_bank_bic": "DBSSSGSG",
        }
        with pytest.raises(GiroGenerationError, match="originator_account is required"):
            adapter.generate_pain001(payroll_run, single_payslip, single_employee, config)

    def test_missing_bic_and_bank_code_raises(
        self, adapter, payroll_run, single_payslip, single_employee
    ):
        config = {
            "originator_name": "ACME PTE LTD",
            "originator_account": "0129876543",
        }
        with pytest.raises(
            GiroGenerationError, match="originator_bank_bic or originator_bank_code"
        ):
            adapter.generate_pain001(payroll_run, single_payslip, single_employee, config)


# ---------------------------------------------------------------------------
# Bank Config Validation
# ---------------------------------------------------------------------------


class TestBankConfigValidation:
    """Verify validate_bank_config returns correct error lists."""

    def test_valid_config_returns_empty(self, adapter, bank_config):
        errors = adapter.validate_bank_config(bank_config)
        assert errors == []

    def test_missing_name_reported(self, adapter):
        errors = adapter.validate_bank_config(
            {"originator_account": "123", "originator_bank_bic": "DBSSSGSG"}
        )
        assert any("originator_name" in e for e in errors)

    def test_missing_account_reported(self, adapter):
        errors = adapter.validate_bank_config(
            {"originator_name": "X", "originator_bank_bic": "DBSSSGSG"}
        )
        assert any("originator_account" in e for e in errors)

    def test_unknown_bank_code_reported(self, adapter):
        config = {
            "originator_name": "X",
            "originator_account": "123",
            "originator_bank_code": "9999",
        }
        errors = adapter.validate_bank_config(config)
        assert any("Unknown bank code" in e for e in errors)

    def test_valid_bank_code_accepted(self, adapter):
        config = {
            "originator_name": "X",
            "originator_account": "123",
            "originator_bank_code": "7171",
        }
        errors = adapter.validate_bank_config(config)
        assert errors == []


# ---------------------------------------------------------------------------
# Supported Banks
# ---------------------------------------------------------------------------


class TestSupportedBanks:
    def test_get_supported_banks_returns_list(self, adapter):
        banks = adapter.get_supported_banks()
        assert isinstance(banks, list)
        assert len(banks) >= 8  # At least the major SG banks

    def test_each_bank_has_name_and_bic(self, adapter):
        banks = adapter.get_supported_banks()
        for bank in banks:
            assert "name" in bank
            assert "bic" in bank
            assert len(bank["bic"]) == 8  # SWIFT BIC is 8 chars
