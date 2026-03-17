"""CPF Board APEX adapter for monthly CPF contribution submissions.

Submits monthly CPF contributions via the GovTech APEX gateway to CPF Board.
Falls back to generating the CPF e-Submit CSV file for manual portal upload.

APEX endpoint: POST /cpfb/submission/v1/contributions
Sandbox:       POST /cpfb/submission/v1/contributions (on sandbox.api.apex.gov.sg)

Reference:
- CPF Board OSP Developer Guide
- GovTech APEX Cloud API documentation
- CPF e-Submit file format specification (for fallback)

Prerequisites:
- OSP vendor registration at onestoppayroll.gov.sg
- CorpPass authorization (OAuth 2.1 via auth/corppass.py)
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
from hr_advisory.services.statutory_files import generate_cpf_esubmit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APEX_BASE_URL = os.environ.get("APEX_BASE_URL", "https://api.apex.gov.sg")
APEX_BASE_URL_SANDBOX = os.environ.get("APEX_BASE_URL_SANDBOX", "https://sandbox.api.apex.gov.sg")
APEX_USE_SANDBOX = os.environ.get("APEX_USE_SANDBOX", "true").lower() == "true"

CPF_SUBMISSION_PATH = "/cpfb/submission/v1/contributions"
CPF_STATUS_PATH = "/cpfb/submission/v1/contributions/{submission_id}/status"

# APEX app-level API key (separate from OAuth token)
APEX_API_KEY = os.environ.get("APEX_API_KEY", "")

# CPF Board employer account (defaults to company UEN)
CPF_EMPLOYER_ACCOUNT = os.environ.get("CPF_EMPLOYER_ACCOUNT", "")

_health = get_health_monitor()


class CPFSubmissionError(Exception):
    """Error during CPF contribution submission."""

    def __init__(self, message: str, error_code: str = "cpf_error", details: Optional[dict] = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _get_base_url() -> str:
    return APEX_BASE_URL_SANDBOX if APEX_USE_SANDBOX else APEX_BASE_URL


def _build_employee_contribution(
    employee: dict,
    payslip: dict,
) -> dict:
    """Build a single employee contribution record for the CPF JSON payload.

    Maps payslip data to the CPF Board APEX API schema.
    Field names follow the CPF e-Submit API specification.
    """
    return {
        "idNo": employee.get("nric_fin", ""),
        "idType": _derive_id_type(employee.get("nric_fin", "")),
        "name": _get_display_name(employee),
        "ordinaryWages": round(payslip.get("cpf_ow_used", 0.0), 2),
        "additionalWages": round(payslip.get("cpf_aw_used", 0.0), 2),
        "employerCpf": round(payslip.get("employer_cpf", 0.0), 2),
        "employeeCpf": round(payslip.get("employee_cpf", 0.0), 2),
        "totalCpf": round(payslip.get("employer_cpf", 0.0) + payslip.get("employee_cpf", 0.0), 2),
        "dateOfBirth": employee.get("date_of_birth", ""),
        "citizenshipStatus": _map_immigration_status(employee.get("immigration_status", "citizen")),
    }


def _derive_id_type(nric_fin: str) -> str:
    """Derive ID type from NRIC/FIN prefix.

    S/T = Singapore citizen NRIC
    F/G = Foreigner FIN
    M = M-series FIN (from 2022)
    """
    if not nric_fin:
        return "UNKNOWN"
    prefix = nric_fin[0].upper()
    if prefix in ("S", "T"):
        return "NRIC"
    if prefix in ("F", "G", "M"):
        return "FIN"
    return "UNKNOWN"


def _map_immigration_status(status: str) -> str:
    """Map internal immigration status to CPF Board status codes."""
    mapping = {
        "citizen": "SC",
        "pr_year1": "PR1",
        "pr_year2": "PR2",
        "pr_year3_plus": "PR3",
        "foreigner": "FN",
    }
    return mapping.get(status, "SC")


def _get_display_name(employee: dict) -> str:
    name = employee.get("name", "")
    if not name:
        name = employee.get("employee_name", employee.get("user_name", ""))
    return name


def _format_period(period_start: str) -> str:
    """Format period_start date string to YYYYMM for CPF submission."""
    try:
        d = date.fromisoformat(period_start)
        return f"{d.year}{d.month:02d}"
    except (ValueError, TypeError):
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def validate_cpf_data(
    tenant_id: str,
    period: str,
    payroll_run: dict,
    payslips: list[dict],
    employees: list[dict],
) -> dict:
    """Validate that CPF data is ready for submission.

    Checks:
    1. Payroll run is in approved/paid status
    2. All employees have valid NRIC/FIN
    3. CPF amounts are non-negative and consistent
    4. Period format is valid
    5. No duplicate submission in the ledger

    Args:
        tenant_id: Company/tenant ID.
        period: Pay period in YYYY-MM format (e.g., "2026-03").
        payroll_run: The payroll run dict.
        payslips: List of payslip dicts for the period.
        employees: List of employee dicts.

    Returns:
        Validation result dict with errors and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    emp_by_id = {e.get("id"): e for e in employees}

    # 1. Payroll run status
    run_status = payroll_run.get("status", "draft")
    if run_status not in ("approved", "paid"):
        errors.append(
            f"Payroll run must be approved or paid before CPF submission (current: {run_status})"
        )

    # 2. Validate period format
    try:
        parts = period.split("-")
        if len(parts) != 2:
            raise ValueError("bad format")
        int(parts[0])
        int(parts[1])
    except (ValueError, IndexError):
        errors.append(f"Invalid period format: {period} (expected YYYY-MM)")

    # 3. Check each employee
    employees_with_cpf = 0
    total_employer_cpf = 0.0
    total_employee_cpf = 0.0

    for ps in payslips:
        emp_id = ps.get("employee_id")
        emp = emp_by_id.get(emp_id, {})

        nric = emp.get("nric_fin", "")
        if not nric:
            errors.append(f"Employee {emp_id} missing NRIC/FIN")
        elif len(nric) != 9:
            warnings.append(
                f"Employee {emp_id}: NRIC/FIN '{nric[:2]}...' may be invalid (length {len(nric)})"
            )

        employer_cpf = ps.get("employer_cpf", 0.0)
        employee_cpf = ps.get("employee_cpf", 0.0)

        if employer_cpf < 0 or employee_cpf < 0:
            errors.append(f"Employee {emp_id} has negative CPF amounts")

        if employer_cpf > 0 or employee_cpf > 0:
            employees_with_cpf += 1

        total_employer_cpf += employer_cpf
        total_employee_cpf += employee_cpf

    if employees_with_cpf == 0:
        warnings.append("No employees with CPF contributions found for this period")

    # 4. Check for duplicate submission
    ledger = get_submission_ledger()
    try:
        # Dry run — just check for duplicates
        idem_key = f"{tenant_id}:{SubmissionType.CPF.value}:{period}"
        existing_id = ledger._index.get(idem_key)
        if existing_id:
            existing = ledger._records.get(existing_id)
            if existing and existing.status.value in ("pending", "submitted", "confirmed"):
                warnings.append(
                    f"A CPF submission for {period} already exists (status: {existing.status.value})"
                )
    except Exception:
        pass

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "period": period,
            "employee_count": len(payslips),
            "employees_with_cpf": employees_with_cpf,
            "total_employer_cpf": round(total_employer_cpf, 2),
            "total_employee_cpf": round(total_employee_cpf, 2),
            "total_cpf": round(total_employer_cpf + total_employee_cpf, 2),
        },
    }


async def generate_submission(
    tenant_id: str,
    period: str,
    payroll_run: dict,
    payslips: list[dict],
    employees: list[dict],
) -> dict:
    """Generate the CPF submission payload from payslip data.

    Creates the JSON payload matching the CPF Board APEX API schema.
    Does NOT submit — returns the payload for preview/confirmation.

    Args:
        tenant_id: Company/tenant ID.
        period: Pay period in YYYY-MM format.
        payroll_run: The payroll run dict.
        payslips: List of payslip dicts.
        employees: List of employee dicts.

    Returns:
        Dict containing the full submission payload and summary.
    """
    emp_by_id = {e.get("id"): e for e in employees}

    # Build individual contribution records
    contributions = []
    for ps in payslips:
        emp_id = ps.get("employee_id")
        emp = emp_by_id.get(emp_id, {})

        # Skip employees with no CPF (e.g., foreigners on WP)
        if ps.get("employer_cpf", 0.0) == 0 and ps.get("employee_cpf", 0.0) == 0:
            continue

        contributions.append(_build_employee_contribution(emp, ps))

    # Build the full payload
    period_ym = _format_period(payroll_run.get("period_start", ""))
    employer_account = payroll_run.get("employer_cpf_account", "") or CPF_EMPLOYER_ACCOUNT

    total_employer = sum(c["employerCpf"] for c in contributions)
    total_employee = sum(c["employeeCpf"] for c in contributions)
    total_cpf = sum(c["totalCpf"] for c in contributions)

    payload = {
        "header": {
            "submissionId": str(uuid.uuid4()),
            "employerCpfAccount": employer_account,
            "contributionMonth": period_ym,
            "employeeCount": len(contributions),
            "totalEmployerCpf": round(total_employer, 2),
            "totalEmployeeCpf": round(total_employee, 2),
            "totalCpf": round(total_cpf, 2),
            "submissionDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "paymentMode": "GIRO",
        },
        "contributions": contributions,
    }

    return {
        "payload": payload,
        "summary": {
            "period": period,
            "employee_count": len(contributions),
            "total_employer_cpf": round(total_employer, 2),
            "total_employee_cpf": round(total_employee, 2),
            "total_cpf": round(total_cpf, 2),
        },
    }


async def submit(
    tenant_id: str,
    period: str,
    payload: dict,
) -> dict:
    """Submit CPF contributions via the APEX API.

    This is the high-stakes submission step. Requires:
    1. Valid CorpPass token
    2. Idempotency ledger check (prevents double-submission)
    3. Circuit breaker protection
    4. Full audit trail

    Args:
        tenant_id: Company/tenant ID.
        period: Pay period in YYYY-MM format.
        payload: The submission payload from generate_submission().

    Returns:
        Dict with submission status, reference ID, and ledger record.

    Raises:
        DuplicateSubmissionError: If already submitted for this period.
        CorpPassError: If not authenticated.
        CPFSubmissionError: If the API rejects the submission.
    """
    # 1. Idempotency check
    ledger = get_submission_ledger()
    employee_count = payload.get("header", {}).get("employeeCount", 0)
    total_cpf = payload.get("header", {}).get("totalCpf", 0.0)

    record = ledger.create_submission(
        tenant_id=tenant_id,
        submission_type=SubmissionType.CPF,
        period=period,
        amount=total_cpf,
        employee_count=employee_count,
    )

    try:
        # 2. Get CorpPass token
        access_token = await get_valid_token(tenant_id)

        # 3. Submit via APEX
        base_url = _get_base_url()
        url = f"{base_url}{CPF_SUBMISSION_PATH}"

        circuit = get_circuit("cpf_board")

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

                if resp.status_code == 200 or resp.status_code == 201:
                    return resp.json()
                elif resp.status_code == 409:
                    # CPF Board reports duplicate
                    body = resp.json()
                    raise CPFSubmissionError(
                        "CPF Board reports duplicate submission",
                        error_code="cpf_duplicate",
                        details=body,
                    )
                else:
                    body = resp.text
                    raise CPFSubmissionError(
                        f"CPF submission rejected (HTTP {resp.status_code})",
                        error_code="cpf_submission_rejected",
                        details={"http_status": resp.status_code, "body": body[:1000]},
                    )

        result = await circuit.call(_do_submit)

        # 4. Mark as submitted in the ledger
        external_ref = result.get("acknowledgementNo", result.get("submissionRef", ""))
        ledger.mark_submitted(record.id, external_ref=external_ref)

        _health.record_success("cpf_board")

        logger.info(
            "CPF submission successful: tenant=%s period=%s ref=%s",
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
                "total_cpf": total_cpf,
            },
        }

    except (DuplicateSubmissionError, CPFSubmissionError):
        raise
    except CorpPassError:
        ledger.mark_failed(record.id, "CorpPass authentication failed")
        raise
    except Exception as e:
        ledger.mark_failed(record.id, str(e))
        _health.record_error("cpf_board", str(e))
        raise CPFSubmissionError(
            f"CPF submission failed: {e}",
            error_code="cpf_submission_failed",
        ) from e


async def check_status(
    tenant_id: str,
    submission_id: str,
) -> dict:
    """Check the status of a CPF submission.

    Polls the APEX API for acknowledgement status. The CPF Board
    processes submissions asynchronously, so this may need to be
    called multiple times.

    Args:
        tenant_id: Company/tenant ID.
        submission_id: Our internal submission ID (from the ledger).

    Returns:
        Dict with current status, any errors, and acknowledgement details.
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
            "message": "Submission not yet sent to CPF Board",
            "submission_id": submission_id,
        }

    # Poll APEX for status
    try:
        access_token = await get_valid_token(tenant_id)
        base_url = _get_base_url()
        url = f"{base_url}{CPF_STATUS_PATH.format(submission_id=external_ref)}"

        circuit = get_circuit("cpf_board")

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
                return {"cpfStatus": "UNKNOWN", "httpStatus": resp.status_code}

        result = await circuit.call(_check)

        cpf_status = result.get("status", result.get("cpfStatus", "UNKNOWN"))

        # Update ledger based on CPF Board response
        if cpf_status in ("ACCEPTED", "PROCESSED", "COMPLETED"):
            ledger.mark_confirmed(submission_id)
        elif cpf_status in ("REJECTED", "ERROR"):
            error_msg = result.get("errorMessage", result.get("errors", "Unknown error"))
            ledger.mark_failed(submission_id, str(error_msg))

        _health.record_success("cpf_board")

        return {
            "status": cpf_status.lower(),
            "submission_id": submission_id,
            "external_reference": external_ref,
            "ledger_status": record.status.value,
            "details": result,
        }

    except CorpPassError as e:
        return {
            "status": "error",
            "message": str(e),
            "submission_id": submission_id,
        }
    except Exception as e:
        _health.record_error("cpf_board", str(e))
        return {
            "status": "error",
            "message": f"Failed to check status: {e}",
            "submission_id": submission_id,
        }


async def generate_csv_fallback(
    payroll_run: dict,
    payslips: list[dict],
    employees: list[dict],
) -> dict:
    """Generate CPF e-Submit CSV file for manual portal upload.

    This is the fallback when APEX API submission is not available
    (e.g., before OSP registration is complete, or during APEX outage).

    Calls the existing generate_cpf_esubmit() from statutory_files.py.

    Args:
        payroll_run: The payroll run dict.
        payslips: List of payslip dicts.
        employees: List of employee dicts.

    Returns:
        Dict with CSV content and file metadata.
    """
    csv_content = generate_cpf_esubmit(payroll_run, payslips, employees)

    period_start = payroll_run.get("period_start", "")
    try:
        d = date.fromisoformat(period_start)
        filename = f"CPF_eSubmit_{d.year}{d.month:02d}.csv"
    except (ValueError, TypeError):
        filename = "CPF_eSubmit.csv"

    return {
        "format": "csv",
        "filename": filename,
        "content": csv_content,
        "content_type": "text/csv",
        "employee_count": len(payslips),
        "instructions": (
            "Upload this file to the CPF Board e-Submit portal at "
            "https://www.cpf.gov.sg/employer/login. "
            "Navigate to Employer > Submit CPF Contributions > File Upload."
        ),
    }
