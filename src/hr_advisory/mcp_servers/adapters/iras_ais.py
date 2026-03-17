"""IRAS Auto-Inclusion Scheme (AIS) API 2.0 adapter.

Submits annual employment income forms (IR8A, Appendix 8A, IR8S, IR21)
to the Inland Revenue Authority of Singapore via the AIS-API 2.0 on
the GovTech APEX gateway.

APEX endpoints:
- POST /iras/ais/v2/ir8a          — Annual employment income
- POST /iras/ais/v2/appendix8a    — Benefits in kind
- POST /iras/ais/v2/ir8s          — Excess/voluntary CPF contributions
- POST /iras/ais/v2/ir21          — Departing foreign employees
- GET  /iras/ais/v2/filing/{id}   — Filing acknowledgement status

Reference:
- IRAS AIS-API 2.0 Technical Guide
- IRAS validation test spec (annual Sep-Nov)
- GovTech APEX Cloud documentation

Prerequisites:
- OSP vendor registration at onestoppayroll.gov.sg
- Annual IRAS validation test pass (Sep-Nov window)
- CorpPass authorization
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.corppass import CorpPassError, get_valid_token
from hr_advisory.mcp_servers.health import get_health_monitor
from hr_advisory.mcp_servers.idempotency import (
    DuplicateSubmissionError,
    SubmissionType,
    get_submission_ledger,
)
from hr_advisory.mcp_servers.resilience import get_circuit
from hr_advisory.services.statutory_files import generate_ir8a_data, generate_ir21_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APEX_BASE_URL = os.environ.get("APEX_BASE_URL", "https://api.apex.gov.sg")
APEX_BASE_URL_SANDBOX = os.environ.get("APEX_BASE_URL_SANDBOX", "https://sandbox.api.apex.gov.sg")
APEX_USE_SANDBOX = os.environ.get("APEX_USE_SANDBOX", "true").lower() == "true"
APEX_API_KEY = os.environ.get("APEX_API_KEY", "")

AIS_IR8A_PATH = "/iras/ais/v2/ir8a"
AIS_APPENDIX_8A_PATH = "/iras/ais/v2/appendix8a"
AIS_IR8S_PATH = "/iras/ais/v2/ir8s"
AIS_IR21_PATH = "/iras/ais/v2/ir21"
AIS_FILING_STATUS_PATH = "/iras/ais/v2/filing/{submission_id}"

_health = get_health_monitor()


class IRASSubmissionError(Exception):
    """Error during IRAS AIS submission."""

    def __init__(
        self, message: str, error_code: str = "iras_error", details: Optional[dict] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


def _get_base_url() -> str:
    return APEX_BASE_URL_SANDBOX if APEX_USE_SANDBOX else APEX_BASE_URL


# ---------------------------------------------------------------------------
# IR8A — Annual Employment Income
# ---------------------------------------------------------------------------


async def generate_ir8a_payload(
    tenant_id: str,
    year_of_assessment: int,
    company: dict,
    employees: list[dict],
    all_payslips: list[dict],
    all_items: list[dict],
) -> dict:
    """Generate IR8A submission payload for all employees in a company.

    Creates a complete AIS-API 2.0 compliant JSON payload containing
    IR8A records for every employee who was paid during the basis year.
    The basis year is the calendar year before the year of assessment
    (e.g., YA 2027 = basis year 2026).

    Args:
        tenant_id: Company/tenant ID.
        year_of_assessment: IRAS year of assessment (e.g., 2027).
        company: Company dict with UEN, name.
        employees: List of employee dicts.
        all_payslips: All payslips for the company.
        all_items: All payslip items for the company.

    Returns:
        Dict containing the submission payload and per-employee summaries.
    """
    basis_year = year_of_assessment - 1

    # Generate IR8A data for each employee using existing statutory_files logic
    ir8a_records = []
    employee_summaries = []

    for emp in employees:
        emp_id = emp.get("id")
        emp_payslips = [ps for ps in all_payslips if ps.get("employee_id") == emp_id]
        emp_items = [
            item
            for item in all_items
            if item.get("payslip_id") in {ps.get("id") for ps in emp_payslips}
        ]

        ir8a_data = generate_ir8a_data(emp, emp_payslips, emp_items, basis_year)

        # Skip employees with zero income for the year
        if ir8a_data.get("total_gross_income", 0) == 0 and ir8a_data.get("months_paid", 0) == 0:
            continue

        # Map to AIS-API 2.0 schema
        record = _map_ir8a_to_ais_schema(ir8a_data, company)
        ir8a_records.append(record)

        employee_summaries.append(
            {
                "employee_id": emp_id,
                "name": ir8a_data.get("employee_name", ""),
                "nric_fin": ir8a_data.get("nric_fin", ""),
                "total_gross_income": ir8a_data.get("total_gross_income", 0),
                "employer_cpf": ir8a_data.get("employer_cpf", 0),
                "months_paid": ir8a_data.get("months_paid", 0),
            }
        )

    payload = {
        "header": {
            "submissionId": str(uuid.uuid4()),
            "formType": "IR8A",
            "yearOfAssessment": year_of_assessment,
            "basisYear": basis_year,
            "employerUen": company.get("uen", ""),
            "employerName": company.get("name", ""),
            "employeeCount": len(ir8a_records),
            "submissionDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "authorizedPersonName": "",
            "authorizedPersonDesignation": "",
            "contactNumber": "",
            "emailAddress": "",
        },
        "records": ir8a_records,
    }

    total_income = sum(s.get("total_gross_income", 0) for s in employee_summaries)

    return {
        "payload": payload,
        "summary": {
            "year_of_assessment": year_of_assessment,
            "basis_year": basis_year,
            "employee_count": len(ir8a_records),
            "total_gross_income": round(total_income, 2),
        },
        "employee_summaries": employee_summaries,
    }


def _map_ir8a_to_ais_schema(ir8a_data: dict, company: dict) -> dict:
    """Map our internal IR8A data structure to the IRAS AIS-API 2.0 JSON schema.

    Field names follow the IRAS AIS-API 2.0 technical specification.
    """
    return {
        "employeeIdNo": ir8a_data.get("nric_fin", ""),
        "employeeIdType": _derive_id_type(ir8a_data.get("nric_fin", "")),
        "employeeName": ir8a_data.get("employee_name", ""),
        "dateOfBirth": ir8a_data.get("date_of_birth", ""),
        "nationality": ir8a_data.get("nationality", ""),
        "sex": _map_gender(ir8a_data.get("gender", "")),
        "designation": ir8a_data.get("designation", ""),
        "periodOfEmploymentFrom": ir8a_data.get("period_from", ""),
        "periodOfEmploymentTo": ir8a_data.get("period_to", ""),
        # Section A — Employment Income
        "salaryWages": ir8a_data.get("gross_salary_wages", 0),
        "bonus": ir8a_data.get("bonus", 0),
        "directorsRemuneration": ir8a_data.get("director_fees", 0),
        "commission": ir8a_data.get("commission", 0),
        "pension": ir8a_data.get("pension_provident_fund", 0),
        "overtimePay": ir8a_data.get("overtime_pay", 0),
        # Section B — Allowances
        "transportAllowance": ir8a_data.get("transport_allowance", 0),
        "entertainmentAllowance": ir8a_data.get("entertainment_allowance", 0),
        "otherAllowances": ir8a_data.get("other_allowances", 0),
        "totalAllowances": ir8a_data.get("total_allowances", 0),
        # Section C — Gross Total
        "totalGrossIncome": ir8a_data.get("total_gross_income", 0),
        # CPF Contributions
        "employeeCpfContribution": ir8a_data.get("employee_cpf", 0),
        "employerCpfContribution": ir8a_data.get("employer_cpf", 0),
        # Benefits in kind indicator
        "appendix8AApplicable": False,
        # IR8S indicator
        "ir8SApplicable": False,
        # Employer details
        "employerUen": company.get("uen", ""),
    }


def _derive_id_type(nric_fin: str) -> str:
    """Map NRIC/FIN to IRAS ID type code."""
    if not nric_fin:
        return ""
    prefix = nric_fin[0].upper()
    if prefix in ("S", "T"):
        return "1"  # NRIC
    if prefix in ("F", "G", "M"):
        return "2"  # FIN
    return "3"  # Others


def _map_gender(gender: str) -> str:
    """Map internal gender to IRAS code."""
    return {"male": "M", "female": "F"}.get(gender.lower(), "")


async def submit_ir8a(
    tenant_id: str,
    year_of_assessment: int,
    payload: dict,
) -> dict:
    """Submit IR8A records via AIS-API 2.0.

    Args:
        tenant_id: Company/tenant ID.
        year_of_assessment: IRAS year of assessment.
        payload: The submission payload from generate_ir8a_payload().

    Returns:
        Dict with submission status and IRAS acknowledgement.

    Raises:
        DuplicateSubmissionError: If already submitted for this YA.
        IRASSubmissionError: If IRAS rejects the submission.
    """
    period = str(year_of_assessment)
    return await _submit_ais_form(
        tenant_id=tenant_id,
        period=period,
        submission_type=SubmissionType.IR8A,
        api_path=AIS_IR8A_PATH,
        payload=payload,
        form_type="IR8A",
    )


# ---------------------------------------------------------------------------
# Appendix 8A — Benefits in Kind
# ---------------------------------------------------------------------------


async def generate_appendix_8a_payload(
    tenant_id: str,
    year_of_assessment: int,
    company: dict,
    employees: list[dict],
    benefits_data: list[dict],
) -> dict:
    """Generate Appendix 8A payload for benefits-in-kind reporting.

    Benefits in kind include: housing, car, driver, utilities,
    hotel accommodation, holiday passages, interest subsidies,
    insurance premiums, club memberships, and gains from stock options.

    Args:
        tenant_id: Company/tenant ID.
        year_of_assessment: IRAS year of assessment.
        company: Company dict.
        employees: List of employee dicts.
        benefits_data: List of benefit records per employee with fields:
            employee_id, benefit_type, value, description, period_from, period_to

    Returns:
        Dict containing the submission payload and summary.
    """
    basis_year = year_of_assessment - 1
    emp_by_id = {e.get("id"): e for e in employees}

    records = []
    for benefit in benefits_data:
        emp_id = benefit.get("employee_id")
        emp = emp_by_id.get(emp_id, {})
        if not emp:
            continue

        record = {
            "employeeIdNo": emp.get("nric_fin", ""),
            "employeeIdType": _derive_id_type(emp.get("nric_fin", "")),
            "employeeName": emp.get("name", emp.get("employee_name", "")),
            # Appendix 8A section fields
            "placeOfResidence": {
                "address": benefit.get("housing_address", ""),
                "annualValue": benefit.get("housing_annual_value", 0),
                "rentPaidByEmployer": benefit.get("housing_rent", 0),
                "rentPaidByEmployee": benefit.get("housing_employee_contribution", 0),
                "periodFrom": benefit.get("period_from", f"{basis_year}-01-01"),
                "periodTo": benefit.get("period_to", f"{basis_year}-12-31"),
                "furnished": benefit.get("housing_furnished", False),
                "sharedWithOthers": benefit.get("housing_shared", False),
            },
            "motorCar": {
                "providedByEmployer": benefit.get("car_provided", False),
                "makeAndModel": benefit.get("car_model", ""),
                "costToEmployer": benefit.get("car_cost", 0),
                "amountPaidByEmployee": benefit.get("car_employee_contribution", 0),
            },
            "otherBenefits": {
                "holidayPassages": benefit.get("holiday_passages", 0),
                "educationSubsidy": benefit.get("education_subsidy", 0),
                "entertainmentExpenses": benefit.get("entertainment_expenses", 0),
                "insurancePremiums": benefit.get("insurance_premiums", 0),
                "clubMembership": benefit.get("club_membership", 0),
                "gainFromStockOptions": benefit.get("stock_option_gains", 0),
                "otherNonMonetaryAwards": benefit.get("other_non_monetary", 0),
                "totalValueOfBenefits": benefit.get("total_benefit_value", 0),
            },
            "employerUen": company.get("uen", ""),
        }
        records.append(record)

    payload = {
        "header": {
            "submissionId": str(uuid.uuid4()),
            "formType": "APPENDIX_8A",
            "yearOfAssessment": year_of_assessment,
            "basisYear": basis_year,
            "employerUen": company.get("uen", ""),
            "employerName": company.get("name", ""),
            "employeeCount": len(records),
            "submissionDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "records": records,
    }

    return {
        "payload": payload,
        "summary": {
            "year_of_assessment": year_of_assessment,
            "employee_count": len(records),
        },
    }


async def submit_appendix_8a(
    tenant_id: str,
    year_of_assessment: int,
    payload: dict,
) -> dict:
    """Submit Appendix 8A records via AIS-API 2.0."""
    period = f"{year_of_assessment}-A8A"
    return await _submit_ais_form(
        tenant_id=tenant_id,
        period=period,
        submission_type=SubmissionType.IR8A,  # Grouped with IR8A in ledger
        api_path=AIS_APPENDIX_8A_PATH,
        payload=payload,
        form_type="APPENDIX_8A",
    )


# ---------------------------------------------------------------------------
# IR8S — Excess/Voluntary CPF Contributions
# ---------------------------------------------------------------------------


async def generate_ir8s_payload(
    tenant_id: str,
    year_of_assessment: int,
    company: dict,
    employees: list[dict],
    ir8s_data: list[dict],
) -> dict:
    """Generate IR8S payload for excess/voluntary CPF contribution refunds.

    IR8S is filed when:
    1. Employee received a CPF refund during the year
    2. Employer made voluntary CPF contributions above mandatory rates
    3. Excess CPF contributions need to be reported

    Args:
        tenant_id: Company/tenant ID.
        year_of_assessment: IRAS year of assessment.
        company: Company dict.
        employees: List of employee dicts.
        ir8s_data: List of IR8S records per employee with fields:
            employee_id, refund_amount, refund_date, refund_type,
            voluntary_employer_cpf, voluntary_employee_cpf

    Returns:
        Dict containing the submission payload and summary.
    """
    basis_year = year_of_assessment - 1
    emp_by_id = {e.get("id"): e for e in employees}

    records = []
    for data in ir8s_data:
        emp_id = data.get("employee_id")
        emp = emp_by_id.get(emp_id, {})
        if not emp:
            continue

        record = {
            "employeeIdNo": emp.get("nric_fin", ""),
            "employeeIdType": _derive_id_type(emp.get("nric_fin", "")),
            "employeeName": emp.get("name", emp.get("employee_name", "")),
            # Refund details
            "cpfRefundType": data.get("refund_type", "EXCESS"),
            "cpfRefundAmount": data.get("refund_amount", 0),
            "cpfRefundDate": data.get("refund_date", ""),
            # Contribution details for the year
            "mandatoryEmployerCpf": data.get("mandatory_employer_cpf", 0),
            "mandatoryEmployeeCpf": data.get("mandatory_employee_cpf", 0),
            "voluntaryEmployerCpf": data.get("voluntary_employer_cpf", 0),
            "voluntaryEmployeeCpf": data.get("voluntary_employee_cpf", 0),
            "totalEmployerCpf": data.get("total_employer_cpf", 0),
            "totalEmployeeCpf": data.get("total_employee_cpf", 0),
            # Month-by-month breakdown (12 months)
            "monthlyBreakdown": data.get("monthly_breakdown", []),
            "employerUen": company.get("uen", ""),
        }
        records.append(record)

    payload = {
        "header": {
            "submissionId": str(uuid.uuid4()),
            "formType": "IR8S",
            "yearOfAssessment": year_of_assessment,
            "basisYear": basis_year,
            "employerUen": company.get("uen", ""),
            "employerName": company.get("name", ""),
            "employeeCount": len(records),
            "submissionDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "records": records,
    }

    return {
        "payload": payload,
        "summary": {
            "year_of_assessment": year_of_assessment,
            "employee_count": len(records),
            "total_refund": sum(d.get("refund_amount", 0) for d in ir8s_data),
        },
    }


async def submit_ir8s(
    tenant_id: str,
    year_of_assessment: int,
    payload: dict,
) -> dict:
    """Submit IR8S records via AIS-API 2.0."""
    period = str(year_of_assessment)
    return await _submit_ais_form(
        tenant_id=tenant_id,
        period=period,
        submission_type=SubmissionType.IR8S,
        api_path=AIS_IR8S_PATH,
        payload=payload,
        form_type="IR8S",
    )


# ---------------------------------------------------------------------------
# IR21 — Departing Foreign Employees
# ---------------------------------------------------------------------------


async def generate_ir21_payload(
    tenant_id: str,
    employee: dict,
    payslips: list[dict],
    items: list[dict],
    cessation_date: str,
    company: dict,
) -> dict:
    """Generate IR21 payload for a departing foreign employee.

    IR21 must be filed at least 1 month before the foreign employee's
    last day of employment. The employer must withhold all monies due
    until IRAS issues a tax clearance letter.

    Args:
        tenant_id: Company/tenant ID.
        employee: The departing employee dict.
        payslips: All payslips for this employee.
        items: All payslip items for this employee.
        cessation_date: Last day of employment (ISO format).
        company: Company dict.

    Returns:
        Dict containing the IR21 payload and summary.
    """
    ir21_data = generate_ir21_data(employee, payslips, items, cessation_date)

    # Map to AIS-API 2.0 schema
    record = {
        "employeeIdNo": ir21_data.get("nric_fin", ""),
        "employeeIdType": _derive_id_type(ir21_data.get("nric_fin", "")),
        "employeeName": ir21_data.get("employee_name", ""),
        "dateOfBirth": ir21_data.get("date_of_birth", ""),
        "nationality": ir21_data.get("nationality", ""),
        "sex": _map_gender(ir21_data.get("gender", "")),
        "designation": ir21_data.get("designation", ""),
        "periodOfEmploymentFrom": ir21_data.get("period_from", ""),
        "periodOfEmploymentTo": ir21_data.get("period_to", ""),
        # Cessation details
        "lastDayOfEmployment": ir21_data.get("last_day_of_employment", ""),
        "reasonForCessation": _map_cessation_reason(
            ir21_data.get("reason_for_cessation", "resignation")
        ),
        "dateOfDepartureFromSG": "",  # To be filled by employer
        # Income
        "salaryWages": ir21_data.get("gross_salary_wages", 0),
        "bonus": ir21_data.get("bonus", 0),
        "commission": ir21_data.get("commission", 0),
        "overtimePay": ir21_data.get("overtime_pay", 0),
        "transportAllowance": ir21_data.get("transport_allowance", 0),
        "entertainmentAllowance": ir21_data.get("entertainment_allowance", 0),
        "otherAllowances": ir21_data.get("other_allowances", 0),
        "totalGrossIncome": ir21_data.get("total_gross_income", 0),
        # CPF
        "employeeCpfContribution": ir21_data.get("employee_cpf", 0),
        "employerCpfContribution": ir21_data.get("employer_cpf", 0),
        # Outstanding amounts
        "outstandingSalary": ir21_data.get("outstanding_salary", 0),
        "outstandingBonus": ir21_data.get("outstanding_bonus", 0),
        "moniesWithheld": ir21_data.get("monies_withheld", False),
        "amountWithheld": ir21_data.get("amount_withheld", 0),
        # Employer details
        "employerUen": company.get("uen", ""),
    }

    try:
        cess = date.fromisoformat(cessation_date)
        ya = cess.year + 1 if cess.month >= 1 else cess.year
    except (ValueError, TypeError):
        ya = date.today().year + 1

    payload = {
        "header": {
            "submissionId": str(uuid.uuid4()),
            "formType": "IR21",
            "yearOfAssessment": ya,
            "employerUen": company.get("uen", ""),
            "employerName": company.get("name", ""),
            "employeeCount": 1,
            "submissionDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "records": [record],
    }

    return {
        "payload": payload,
        "summary": {
            "employee_name": ir21_data.get("employee_name", ""),
            "nric_fin": ir21_data.get("nric_fin", ""),
            "cessation_date": cessation_date,
            "total_gross_income": ir21_data.get("total_gross_income", 0),
            "amount_withheld": ir21_data.get("amount_withheld", 0),
        },
    }


def _map_cessation_reason(reason: str) -> str:
    """Map internal cessation reason to IRAS IR21 reason code."""
    mapping = {
        "resignation": "01",
        "termination": "02",
        "retrenchment": "03",
        "retirement": "04",
        "contract_expired": "05",
        "transfer": "06",
        "death": "07",
        "other": "99",
    }
    return mapping.get(reason.lower(), "99")


async def submit_ir21(
    tenant_id: str,
    employee_id: str,
    payload: dict,
) -> dict:
    """Submit IR21 for a departing foreign employee via AIS-API 2.0.

    IR21 uses the employee_id as part of the period key for idempotency,
    since multiple IR21s can be filed in the same year for different employees.
    """
    ya = payload.get("header", {}).get("yearOfAssessment", date.today().year + 1)
    period = f"{ya}-IR21-{employee_id}"
    return await _submit_ais_form(
        tenant_id=tenant_id,
        period=period,
        submission_type=SubmissionType.IR21,
        api_path=AIS_IR21_PATH,
        payload=payload,
        form_type="IR21",
    )


# ---------------------------------------------------------------------------
# Filing Status
# ---------------------------------------------------------------------------


async def check_filing_status(
    tenant_id: str,
    submission_id: str,
) -> dict:
    """Check the acknowledgement status of an IRAS AIS filing.

    IRAS processes filings asynchronously. Status values:
    - RECEIVED: Filing received, awaiting processing
    - PROCESSING: Being validated by IRAS
    - ACCEPTED: Filing accepted successfully
    - REJECTED: Filing rejected with error details
    - PARTIALLY_ACCEPTED: Some records accepted, some rejected

    Args:
        tenant_id: Company/tenant ID.
        submission_id: Our internal submission ID.

    Returns:
        Dict with current status and any validation errors.
    """
    ledger = get_submission_ledger()
    record = ledger.get_submission(submission_id)
    if record is None:
        return {"status": "error", "message": f"Unknown submission: {submission_id}"}

    if record.tenant_id != tenant_id:
        return {"status": "error", "message": "Submission does not belong to this tenant"}

    external_ref = record.external_reference_id
    if not external_ref:
        return {
            "status": record.status.value,
            "message": "Filing not yet sent to IRAS",
            "submission_id": submission_id,
        }

    try:
        access_token = await get_valid_token(tenant_id)
        base_url = _get_base_url()
        url = f"{base_url}{AIS_FILING_STATUS_PATH.format(submission_id=external_ref)}"

        circuit = get_circuit("iras")

        async def _check() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                        "X-API-Key": APEX_API_KEY,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"filingStatus": "UNKNOWN", "httpStatus": resp.status_code}

        result = await circuit.call(_check)

        filing_status = result.get("status", result.get("filingStatus", "UNKNOWN"))

        # Update ledger
        if filing_status in ("ACCEPTED", "COMPLETED"):
            ledger.mark_confirmed(submission_id)
        elif filing_status == "REJECTED":
            error_msg = result.get("errors", result.get("validationErrors", ""))
            ledger.mark_failed(submission_id, str(error_msg))

        _health.record_success("iras")

        return {
            "status": filing_status.lower(),
            "submission_id": submission_id,
            "external_reference": external_ref,
            "details": result,
            "validation_errors": result.get("validationErrors", []),
            "accepted_count": result.get("acceptedCount", 0),
            "rejected_count": result.get("rejectedCount", 0),
        }

    except CorpPassError as e:
        return {"status": "error", "message": str(e), "submission_id": submission_id}
    except Exception as e:
        _health.record_error("iras", str(e))
        return {
            "status": "error",
            "message": f"Status check failed: {e}",
            "submission_id": submission_id,
        }


# ---------------------------------------------------------------------------
# Shared submission logic
# ---------------------------------------------------------------------------


async def _submit_ais_form(
    tenant_id: str,
    period: str,
    submission_type: SubmissionType,
    api_path: str,
    payload: dict,
    form_type: str,
) -> dict:
    """Generic AIS form submission via APEX.

    Shared by IR8A, Appendix 8A, IR8S, and IR21.
    Handles idempotency, authentication, circuit breaker, and audit.
    """
    ledger = get_submission_ledger()
    employee_count = payload.get("header", {}).get("employeeCount", 0)

    record = ledger.create_submission(
        tenant_id=tenant_id,
        submission_type=submission_type,
        period=period,
        employee_count=employee_count,
    )

    try:
        access_token = await get_valid_token(tenant_id)
        base_url = _get_base_url()
        url = f"{base_url}{api_path}"

        circuit = get_circuit("iras")

        async def _do_submit() -> dict:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-API-Key": APEX_API_KEY,
                        "X-Correlation-ID": record.id,
                    },
                )

                if resp.status_code in (200, 201, 202):
                    return resp.json()
                else:
                    body = resp.text
                    raise IRASSubmissionError(
                        f"IRAS {form_type} submission rejected (HTTP {resp.status_code})",
                        error_code=f"iras_{form_type.lower()}_rejected",
                        details={"http_status": resp.status_code, "body": body[:1000]},
                    )

        result = await circuit.call(_do_submit)

        external_ref = result.get("filingReferenceNo", result.get("submissionRef", ""))
        ledger.mark_submitted(record.id, external_ref=external_ref)

        _health.record_success("iras")

        logger.info(
            "IRAS %s submission successful: tenant=%s period=%s ref=%s",
            form_type,
            tenant_id,
            period,
            external_ref,
        )

        return {
            "status": "submitted",
            "form_type": form_type,
            "submission_id": record.id,
            "external_reference": external_ref,
            "acknowledgement": result,
            "employee_count": employee_count,
        }

    except (DuplicateSubmissionError, IRASSubmissionError):
        raise
    except CorpPassError:
        ledger.mark_failed(record.id, "CorpPass authentication failed")
        raise
    except Exception as e:
        ledger.mark_failed(record.id, str(e))
        _health.record_error("iras", str(e))
        raise IRASSubmissionError(
            f"IRAS {form_type} submission failed: {e}",
            error_code=f"iras_{form_type.lower()}_failed",
        ) from e
