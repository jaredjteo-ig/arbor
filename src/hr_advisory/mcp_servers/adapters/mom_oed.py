"""MOM Occupational Employment Dataset (OED) adapter.

Submits Occupational Employment Data to the Ministry of Manpower
via the GovTech APEX gateway. The OED survey is mandatory under the
Statistics Act for selected companies.

APEX endpoint: POST /mom/oed/v1/submission
Sandbox:       POST /mom/oed/v1/submission (on sandbox.api.apex.gov.sg)

Reference:
- MOM OED API Technical Specification
- Statistics Act (Chapter 317)
- GovTech APEX Cloud documentation

The OED collects data on:
- Occupational breakdown (SSOC codes)
- Employment counts by type (full-time, part-time, contract)
- Nationality breakdown (citizen, PR, foreigner)
- Salary ranges by occupation
- Vacancy information

Prerequisites:
- OSP vendor registration at onestoppayroll.gov.sg
- CorpPass authorization
"""

from __future__ import annotations

import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APEX_BASE_URL = os.environ.get("APEX_BASE_URL", "https://api.apex.gov.sg")
APEX_BASE_URL_SANDBOX = os.environ.get("APEX_BASE_URL_SANDBOX", "https://sandbox.api.apex.gov.sg")
APEX_USE_SANDBOX = os.environ.get("APEX_USE_SANDBOX", "true").lower() == "true"
APEX_API_KEY = os.environ.get("APEX_API_KEY", "")

OED_SUBMISSION_PATH = "/mom/oed/v1/submission"
OED_STATUS_PATH = "/mom/oed/v1/submission/{submission_id}/status"

_health = get_health_monitor()


class MOMSubmissionError(Exception):
    """Error during MOM OED submission."""

    def __init__(self, message: str, error_code: str = "mom_error", details: Optional[dict] = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


def _get_base_url() -> str:
    return APEX_BASE_URL_SANDBOX if APEX_USE_SANDBOX else APEX_BASE_URL


# ---------------------------------------------------------------------------
# SSOC mapping (Singapore Standard Occupational Classification 2020)
# ---------------------------------------------------------------------------

# Common designation-to-SSOC mappings for SG SMEs
_DESIGNATION_SSOC_MAP = {
    # Management
    "managing director": "1112",
    "chief executive officer": "1112",
    "ceo": "1112",
    "general manager": "1120",
    "operations manager": "1219",
    "hr manager": "1212",
    "human resource manager": "1212",
    "finance manager": "1211",
    "marketing manager": "1221",
    "sales manager": "1221",
    "it manager": "1330",
    "project manager": "1213",
    # Professionals
    "accountant": "2411",
    "software engineer": "2512",
    "software developer": "2512",
    "system administrator": "2522",
    "network engineer": "2523",
    "data analyst": "2511",
    "business analyst": "2421",
    "hr executive": "2423",
    "hr officer": "2423",
    "marketing executive": "2431",
    "legal counsel": "2611",
    "lawyer": "2611",
    "architect": "2161",
    "engineer": "2149",
    "teacher": "2320",
    "lecturer": "2310",
    "nurse": "2221",
    "doctor": "2211",
    # Technicians and associate professionals
    "technician": "3119",
    "designer": "3432",
    "graphic designer": "3432",
    "sales executive": "3322",
    "admin executive": "3341",
    "administrative executive": "3341",
    "customer service officer": "4225",
    # Clerical support
    "clerk": "4110",
    "admin assistant": "4110",
    "administrative assistant": "4110",
    "receptionist": "4226",
    "secretary": "4120",
    "data entry": "4132",
    # Service and sales
    "waiter": "5131",
    "waitress": "5131",
    "cook": "5120",
    "chef": "3434",
    "security guard": "5414",
    "driver": "8322",
    # Plant and machine operators
    "machine operator": "8100",
    "factory worker": "8100",
    "production operator": "8100",
    # Elementary occupations
    "cleaner": "9112",
    "labourer": "9311",
    "packer": "9321",
    "helper": "9100",
}


def _map_designation_to_ssoc(designation: str) -> str:
    """Map employee designation to SSOC 2020 code.

    Uses a best-effort lookup against common SG designations.
    Falls back to "0000" (not classified) if no match found.
    """
    if not designation:
        return "0000"
    designation_lower = designation.strip().lower()

    # Exact match
    if designation_lower in _DESIGNATION_SSOC_MAP:
        return _DESIGNATION_SSOC_MAP[designation_lower]

    # Partial match — check if any key is contained in the designation
    for key, ssoc in _DESIGNATION_SSOC_MAP.items():
        if key in designation_lower:
            return ssoc

    return "0000"


def _map_employment_type(emp_type: str) -> str:
    """Map internal employment type to MOM OED type code."""
    mapping = {
        "full_time": "FT",
        "part_time": "PT",
        "contract": "CT",
        "temporary": "TP",
        "casual": "CS",
    }
    return mapping.get(emp_type, "FT")


def _map_nationality_status(immigration_status: str) -> str:
    """Map immigration status to MOM nationality classification."""
    mapping = {
        "citizen": "SC",
        "pr_year1": "PR",
        "pr_year2": "PR",
        "pr_year3_plus": "PR",
        "foreigner": "FN",
    }
    return mapping.get(immigration_status, "SC")


def _salary_range_code(monthly_salary: float) -> str:
    """Map monthly salary to MOM salary range code.

    MOM salary ranges (monthly gross):
    01: Below $1,000
    02: $1,000 - $1,499
    03: $1,500 - $1,999
    04: $2,000 - $2,499
    05: $2,500 - $2,999
    06: $3,000 - $3,499
    07: $3,500 - $3,999
    08: $4,000 - $4,499
    09: $4,500 - $4,999
    10: $5,000 - $5,999
    11: $6,000 - $6,999
    12: $7,000 - $7,999
    13: $8,000 - $8,999
    14: $9,000 - $9,999
    15: $10,000 - $11,999
    16: $12,000 - $14,999
    17: $15,000 - $19,999
    18: $20,000 and above
    """
    if monthly_salary < 1000:
        return "01"
    elif monthly_salary < 1500:
        return "02"
    elif monthly_salary < 2000:
        return "03"
    elif monthly_salary < 2500:
        return "04"
    elif monthly_salary < 3000:
        return "05"
    elif monthly_salary < 3500:
        return "06"
    elif monthly_salary < 4000:
        return "07"
    elif monthly_salary < 4500:
        return "08"
    elif monthly_salary < 5000:
        return "09"
    elif monthly_salary < 6000:
        return "10"
    elif monthly_salary < 7000:
        return "11"
    elif monthly_salary < 8000:
        return "12"
    elif monthly_salary < 9000:
        return "13"
    elif monthly_salary < 10000:
        return "14"
    elif monthly_salary < 12000:
        return "15"
    elif monthly_salary < 15000:
        return "16"
    elif monthly_salary < 20000:
        return "17"
    else:
        return "18"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_oed_data(
    tenant_id: str,
    company: dict,
    employees: list[dict],
    reference_date: Optional[str] = None,
) -> dict:
    """Generate OED submission payload from employee records.

    Aggregates employee data into the occupational categories and
    breakdowns required by MOM's OED survey.

    Args:
        tenant_id: Company/tenant ID.
        company: Company dict with UEN, name, sector.
        employees: List of active employee dicts.
        reference_date: Survey reference date (defaults to today).

    Returns:
        Dict containing the OED submission payload and summary.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Filter to active employees only
    active_employees = [e for e in employees if e.get("is_active", True)]

    # Build occupation-level aggregation
    # Group by SSOC code
    occ_groups: dict[str, list[dict]] = defaultdict(list)
    for emp in active_employees:
        ssoc = _map_designation_to_ssoc(emp.get("designation", ""))
        occ_groups[ssoc].append(emp)

    occupation_records = []
    for ssoc_code, group_employees in sorted(occ_groups.items()):
        # Count by nationality
        sc_count = sum(
            1
            for e in group_employees
            if _map_nationality_status(e.get("immigration_status", "citizen")) == "SC"
        )
        pr_count = sum(
            1
            for e in group_employees
            if _map_nationality_status(e.get("immigration_status", "")) == "PR"
        )
        fn_count = sum(
            1
            for e in group_employees
            if _map_nationality_status(e.get("immigration_status", "")) == "FN"
        )

        # Count by employment type
        ft_count = sum(
            1
            for e in group_employees
            if _map_employment_type(e.get("employment_type", "full_time")) == "FT"
        )
        pt_count = sum(
            1 for e in group_employees if _map_employment_type(e.get("employment_type", "")) == "PT"
        )
        ct_count = sum(
            1 for e in group_employees if _map_employment_type(e.get("employment_type", "")) == "CT"
        )

        # Salary distribution
        salary_distribution: dict[str, int] = defaultdict(int)
        for emp in group_employees:
            salary = emp.get("salary_monthly", 0.0)
            if salary > 0:
                range_code = _salary_range_code(salary)
                salary_distribution[range_code] += 1

        # Gender breakdown
        male_count = sum(1 for e in group_employees if e.get("gender", "").lower() == "male")
        female_count = sum(1 for e in group_employees if e.get("gender", "").lower() == "female")

        # Representative designation for the group
        designations = [e.get("designation", "") for e in group_employees if e.get("designation")]
        common_designation = max(set(designations), key=designations.count) if designations else ""

        occupation_records.append(
            {
                "ssocCode": ssoc_code,
                "occupationTitle": common_designation,
                "totalEmployees": len(group_employees),
                "nationalityBreakdown": {
                    "singaporeCitizen": sc_count,
                    "permanentResident": pr_count,
                    "foreigner": fn_count,
                },
                "employmentTypeBreakdown": {
                    "fullTime": ft_count,
                    "partTime": pt_count,
                    "contract": ct_count,
                },
                "genderBreakdown": {
                    "male": male_count,
                    "female": female_count,
                },
                "salaryDistribution": dict(salary_distribution),
                "vacancies": 0,  # To be updated by the employer
            }
        )

    # Company-level totals
    total_employees = len(active_employees)
    total_sc = sum(r["nationalityBreakdown"]["singaporeCitizen"] for r in occupation_records)
    total_pr = sum(r["nationalityBreakdown"]["permanentResident"] for r in occupation_records)
    total_fn = sum(r["nationalityBreakdown"]["foreigner"] for r in occupation_records)

    payload = {
        "header": {
            "submissionId": str(uuid.uuid4()),
            "surveyType": "OED",
            "referenceDate": reference_date,
            "employerUen": company.get("uen", ""),
            "employerName": company.get("name", ""),
            "ssicCode": company.get("sub_sector", company.get("sector", "")),
            "totalEmployees": total_employees,
            "submissionDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "contactPersonName": "",
            "contactNumber": "",
            "contactEmail": "",
        },
        "companySummary": {
            "totalEmployees": total_employees,
            "singaporeCitizen": total_sc,
            "permanentResident": total_pr,
            "foreigner": total_fn,
            "totalVacancies": 0,
        },
        "occupations": occupation_records,
    }

    return {
        "payload": payload,
        "summary": {
            "reference_date": reference_date,
            "total_employees": total_employees,
            "occupation_groups": len(occupation_records),
            "nationality_breakdown": {
                "citizen": total_sc,
                "pr": total_pr,
                "foreigner": total_fn,
            },
        },
    }


async def submit_oed(
    tenant_id: str,
    period: str,
    payload: dict,
) -> dict:
    """Submit OED data to MOM via APEX.

    Args:
        tenant_id: Company/tenant ID.
        period: Survey period identifier (e.g., "2026-Q2").
        payload: The OED payload from generate_oed_data().

    Returns:
        Dict with submission status and MOM acknowledgement.

    Raises:
        DuplicateSubmissionError: If already submitted for this period.
        MOMSubmissionError: If MOM rejects the submission.
    """
    ledger = get_submission_ledger()
    employee_count = payload.get("header", {}).get("totalEmployees", 0)

    record = ledger.create_submission(
        tenant_id=tenant_id,
        submission_type=SubmissionType.OED,
        period=period,
        employee_count=employee_count,
    )

    try:
        access_token = await get_valid_token(tenant_id)
        base_url = _get_base_url()
        url = f"{base_url}{OED_SUBMISSION_PATH}"

        circuit = get_circuit("mom")

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
                    raise MOMSubmissionError(
                        f"MOM OED submission rejected (HTTP {resp.status_code})",
                        error_code="mom_oed_rejected",
                        details={"http_status": resp.status_code, "body": body[:1000]},
                    )

        result = await circuit.call(_do_submit)

        external_ref = result.get("acknowledgementNo", result.get("submissionRef", ""))
        ledger.mark_submitted(record.id, external_ref=external_ref)

        _health.record_success("mom")

        logger.info(
            "MOM OED submission successful: tenant=%s period=%s ref=%s",
            tenant_id,
            period,
            external_ref,
        )

        return {
            "status": "submitted",
            "submission_id": record.id,
            "external_reference": external_ref,
            "acknowledgement": result,
            "summary": {
                "period": period,
                "employee_count": employee_count,
            },
        }

    except (DuplicateSubmissionError, MOMSubmissionError):
        raise
    except CorpPassError:
        ledger.mark_failed(record.id, "CorpPass authentication failed")
        raise
    except Exception as e:
        ledger.mark_failed(record.id, str(e))
        _health.record_error("mom", str(e))
        raise MOMSubmissionError(
            f"MOM OED submission failed: {e}",
            error_code="mom_oed_failed",
        ) from e


async def check_status(
    tenant_id: str,
    submission_id: str,
) -> dict:
    """Check the status of an OED submission.

    MOM processes OED submissions asynchronously. Possible statuses:
    - RECEIVED: Submission received
    - PROCESSING: Under validation
    - ACCEPTED: Submission accepted
    - REJECTED: Submission rejected with errors
    - QUERY: MOM has follow-up queries

    Args:
        tenant_id: Company/tenant ID.
        submission_id: Our internal submission ID.

    Returns:
        Dict with current status and any queries/errors.
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
            "message": "Submission not yet sent to MOM",
            "submission_id": submission_id,
        }

    try:
        access_token = await get_valid_token(tenant_id)
        base_url = _get_base_url()
        url = f"{base_url}{OED_STATUS_PATH.format(submission_id=external_ref)}"

        circuit = get_circuit("mom")

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
                return {"submissionStatus": "UNKNOWN", "httpStatus": resp.status_code}

        result = await circuit.call(_check)

        mom_status = result.get("status", result.get("submissionStatus", "UNKNOWN"))

        if mom_status in ("ACCEPTED", "COMPLETED"):
            ledger.mark_confirmed(submission_id)
        elif mom_status in ("REJECTED", "ERROR"):
            error_msg = result.get("errors", result.get("errorMessage", "Unknown error"))
            ledger.mark_failed(submission_id, str(error_msg))

        _health.record_success("mom")

        return {
            "status": mom_status.lower(),
            "submission_id": submission_id,
            "external_reference": external_ref,
            "details": result,
            "queries": result.get("queries", []),
        }

    except CorpPassError as e:
        return {"status": "error", "message": str(e), "submission_id": submission_id}
    except Exception as e:
        _health.record_error("mom", str(e))
        return {
            "status": "error",
            "message": f"Status check failed: {e}",
            "submission_id": submission_id,
        }
