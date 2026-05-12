"""Payroll management endpoints.

Handles payroll run lifecycle: calculate, review, approve, mark paid.
Also handles payslip access, CPF YTD tracking, payroll reports, and exports.
Includes parallel run support for comparing Arbor calculations against external HRIS data.
"""

import csv
import io
import logging
import math
import re
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for parallel payroll run uploads (production: use database).
# Bounded to prevent memory exhaustion in long-running processes.
_parallel_runs: OrderedDict[str, dict] = OrderedDict()
MAX_PARALLEL_RUNS = 10


def _find_user_by_id(user_id: int) -> dict | None:
    return dataflow_crud.read("User", user_id)


def _sanitize_filename(title: str, extension: str = ".csv") -> str:
    """Sanitize a title for use in Content-Disposition headers.

    Removes all characters except alphanumeric, hyphen, underscore, dot, and space.
    Replaces spaces with hyphens, truncates to 100 characters.
    """
    safe = re.sub(r"[^a-zA-Z0-9\-_. ]", "", title)
    safe = safe.replace(" ", "-")
    safe = re.sub(r"-+", "-", safe).strip("-")
    max_base = 100 - len(extension)
    if len(safe) > max_base:
        safe = safe[:max_base]
    if not safe:
        safe = "export"
    return safe + extension


# --------------------------------------------------------------------------
# POST /payroll/calculate — Run payroll for a period
# --------------------------------------------------------------------------


@router.post("/calculate")
async def calculate_payroll(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Calculate payroll for all active employees in the current company.

    Creates a PayrollRun in 'draft' status with Payslips and PayslipItems.
    Does NOT pay anyone — this is a preview for review.
    """
    from hr_advisory.services.payroll_calculator import calculate_employee_payslip

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(f"payroll_calc:{company_id}", max_requests=20, window_seconds=3600, action_name="payroll calculation")

    body = await request.json()
    period_start = body.get("period_start", "")
    period_end = body.get("period_end", "")
    pay_date = body.get("pay_date", "")
    payroll_type = body.get("payroll_type", "monthly")

    if not period_start or not period_end or not pay_date:
        raise HTTPException(
            status_code=400,
            detail="period_start, period_end, and pay_date are required.",
        )

    actor_id = int(current_user.get("sub", 0))

    # Fetch active employees
    employees = dataflow_crud.list_records(
        "Employee",
        {
            "company_id": company_id,
            "is_active": True,
        },
    )
    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found.")

    # Prevent duplicate payroll runs for the same period
    existing_runs = dataflow_crud.list_records(
        "PayrollRun",
        {
            "company_id": company_id,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    active_runs = [r for r in existing_runs if r.get("status") != "cancelled"]
    if active_runs:
        raise HTTPException(status_code=400, detail="A payroll run already exists for this period.")

    # Create payroll run
    run = dataflow_crud.create(
        "PayrollRun",
        {
            "company_id": company_id,
            "period_start": period_start,
            "period_end": period_end,
            "pay_date": pay_date,
            "status": "draft",
            "payroll_type": payroll_type,
            "employee_count": len(employees),
            "created_by": actor_id,
        },
    )
    run_id = run.get("id")

    # Derive period month (e.g. "2026-03") for cross-module queries
    from datetime import date

    period_date = date.fromisoformat(period_start)
    period_month = period_date.strftime("%Y-%m")

    # Calculate payslip for each employee
    total_gross = 0.0
    total_net = 0.0
    total_employer_cpf = 0.0
    total_employee_cpf = 0.0
    total_sdl = 0.0
    total_fwl = 0.0
    total_shg = 0.0
    payslips_summary = []

    for emp in employees:
        emp_id = emp.get("id")

        # Fetch salary components
        components = dataflow_crud.list_records(
            "SalaryComponent",
            {
                "employee_id": emp_id,
                "is_active": True,
            },
        )

        # Fetch CPF YTD for ceiling tracking
        try:
            ytd_records = dataflow_crud.list_records(
                "CpfYtdRecord",
                {
                    "employee_id": emp_id,
                    "year": period_date.year,
                },
            )
            ytd_ow_total = sum(r.get("ow_subject_to_cpf", 0.0) for r in ytd_records)
        except Exception:
            ytd_ow_total = 0.0

        # ------------------------------------------------------------------
        # Cross-module data: leave, overtime, claims (M25 integration)
        # ------------------------------------------------------------------

        # 1. Unpaid leave deductions
        leave_deduction_days = 0.0
        try:
            leave_apps = dataflow_crud.list_records(
                "LeaveApplication",
                {
                    "employee_id": emp_id,
                    "status": "approved",
                    "leave_type_code": "unpaid",
                },
            )
            for la in leave_apps:
                la_start = la.get("start_date", "")
                la_end = la.get("end_date", "")
                # Include leave that overlaps with the payroll period
                if la_start and la_end and la_start <= period_end and la_end >= period_start:
                    leave_deduction_days += la.get("total_days", 0.0)
        except Exception as exc:
            logger.warning("Failed to fetch leave data for employee %s: %s", emp_id, exc)

        # 2. Overtime hours from approved timesheets
        overtime_hours = 0.0
        try:
            timesheets = dataflow_crud.list_records(
                "TimesheetApproval",
                {
                    "employee_id": emp_id,
                    "status": "approved",
                    "month": period_month,
                },
            )
            for ts in timesheets:
                overtime_hours += ts.get("total_ot_hours", 0.0)
        except Exception as exc:
            logger.warning("Failed to fetch timesheets for employee %s: %s", emp_id, exc)

        # 3. Approved claims not yet paid
        approved_claims_total = 0.0
        try:
            emp_claims = dataflow_crud.list_records(
                "Claim",
                {
                    "employee_id": emp_id,
                    "status": "approved",
                    "claim_month": period_month,
                },
            )
            for cl in emp_claims:
                if cl.get("paid_in_payroll_run_id") is None:
                    approved_claims_total += cl.get("total_amount", 0.0)
        except Exception as exc:
            logger.warning("Failed to fetch claims for employee %s: %s", emp_id, exc)

        # Calculate payslip
        result = calculate_employee_payslip(
            employee=emp,
            salary_components=components,
            period_start=period_start,
            period_end=period_end,
            ytd_ow_total=ytd_ow_total,
            leave_deduction_days=leave_deduction_days,
            overtime_hours=overtime_hours,
            approved_claims_total=approved_claims_total,
        )

        # Create Payslip record
        payslip = dataflow_crud.create(
            "Payslip",
            {
                "payroll_run_id": run_id,
                "employee_id": emp_id,
                "company_id": company_id,
                "period_start": period_start,
                "period_end": period_end,
                "basic_salary": result["basic_salary"],
                "gross_salary": result["gross_salary"],
                "net_salary": result["net_salary"],
                "employer_cpf": result["employer_cpf"],
                "employee_cpf": result["employee_cpf"],
                "sdl": result["sdl"],
                "fwl": result["fwl"],
                "shg_fund": result["shg_fund"],
                "shg_amount": result["shg_amount"],
                "cpf_ow_used": result["cpf_ow_used"],
                "cpf_aw_used": result["cpf_aw_used"],
                "status": "draft",
            },
        )
        payslip_id = payslip.get("id")

        # Create PayslipItems
        for item in result.get("items", []):
            dataflow_crud.create(
                "PayslipItem",
                {
                    "payslip_id": payslip_id,
                    "company_id": company_id,
                    "item_type": item["item_type"],
                    "name": item["name"],
                    "amount": item["amount"],
                    "is_taxable": item.get("is_taxable", True),
                    "is_cpf_applicable": item.get("is_cpf_applicable", True),
                    "notes": item.get("notes", ""),
                },
            )

        # Create CPF YTD record
        try:
            period_date = date.fromisoformat(period_start)
            dataflow_crud.create(
                "CpfYtdRecord",
                {
                    "employee_id": emp_id,
                    "company_id": company_id,
                    "year": period_date.year,
                    "month": period_date.month,
                    "ow_subject_to_cpf": result["cpf_ow_used"],
                    "aw_subject_to_cpf": result["cpf_aw_used"],
                    "ytd_ow_total": ytd_ow_total + result["cpf_ow_used"],
                    "ytd_aw_total": 0.0,
                    "employer_cpf": result["employer_cpf"],
                    "employee_cpf": result["employee_cpf"],
                    "payslip_id": payslip_id,
                },
            )
        except Exception:
            logger.warning("Failed to create CPF YTD record for employee %s", emp_id)

        # Accumulate totals
        total_gross += result["gross_salary"]
        total_net += result["net_salary"]
        total_employer_cpf += result["employer_cpf"]
        total_employee_cpf += result["employee_cpf"]
        total_sdl += result["sdl"]
        total_fwl += result["fwl"]
        total_shg += result["shg_amount"]

        # Summary for response
        user = _find_user_by_id(emp.get("user_id"))
        payslips_summary.append(
            {
                "payslip_id": payslip_id,
                "employee_id": emp_id,
                "name": user.get("name", "") if user else "",
                "basic_salary": result["basic_salary"],
                "gross_salary": result["gross_salary"],
                "net_salary": result["net_salary"],
                "employer_cpf": result["employer_cpf"],
                "employee_cpf": result["employee_cpf"],
            }
        )

    # Update run with totals
    dataflow_crud.update(
        "PayrollRun",
        run_id,
        {
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
            "total_employer_cpf": round(total_employer_cpf, 2),
            "total_employee_cpf": round(total_employee_cpf, 2),
            "total_sdl": round(total_sdl, 2),
            "total_fwl": round(total_fwl, 2),
            "total_shg": round(total_shg, 2),
        },
    )

    return {
        "payroll_run": {
            "id": run_id,
            "period_start": period_start,
            "period_end": period_end,
            "pay_date": pay_date,
            "status": "draft",
            "payroll_type": payroll_type,
            "employee_count": len(employees),
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
            "total_employer_cpf": round(total_employer_cpf, 2),
            "total_employee_cpf": round(total_employee_cpf, 2),
            "total_sdl": round(total_sdl, 2),
            "total_fwl": round(total_fwl, 2),
            "total_shg": round(total_shg, 2),
        },
        "payslips": payslips_summary,
    }


# --------------------------------------------------------------------------
# GET /payroll/runs — List payroll runs
# --------------------------------------------------------------------------


@router.get("/runs")
async def list_payroll_runs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all payroll runs for the current company.

    Supports pagination via page and page_size query parameters.
    """
    company_id = get_current_company_id(current_user)
    runs = dataflow_crud.list_records("PayrollRun", {"company_id": company_id})
    runs.sort(key=lambda r: r.get("period_start", ""), reverse=True)

    # Pagination
    total_count = len(runs)
    offset = (page - 1) * page_size
    page_runs = runs[offset : offset + page_size]

    return {
        "runs": page_runs,
        "count": len(page_runs),
        "page": page,
        "page_size": page_size,
        "total": total_count,
        "pages": math.ceil(total_count / page_size) if total_count > 0 else 0,
    }


# --------------------------------------------------------------------------
# GET /payroll/runs/{id} — Get payroll run detail
# --------------------------------------------------------------------------


@router.get("/runs/{run_id}")
async def get_payroll_run(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a payroll run with all payslips."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id})

    # Enrich payslips with employee names
    enriched = []
    for ps in payslips:
        emp_id = ps.get("employee_id")
        emp_records = dataflow_crud.list_records("Employee", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = _find_user_by_id(emp.get("user_id")) if emp else None
        enriched.append(
            {
                **ps,
                "payslip_id": ps.get("id"),
                "employee_name": user.get("name", "") if user else "",
                "employee_email": user.get("email", "") if user else "",
            }
        )

    return {"run": run, "payslips": enriched}


# --------------------------------------------------------------------------
# GET /payroll/runs/{id}/payslips/{payslip_id} — Single payslip with items
# --------------------------------------------------------------------------


@router.get("/runs/{run_id}/payslips/{payslip_id}")
async def get_payslip_detail(
    run_id: int,
    payslip_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a single payslip with all line items."""
    company_id = get_current_company_id(current_user)
    payslip = dataflow_crud.read("Payslip", payslip_id)
    if payslip is None or payslip.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payslip not found.")

    items = dataflow_crud.list_records("PayslipItem", {"payslip_id": payslip_id})

    # Get employee name
    emp_records = dataflow_crud.list_records("Employee", {"id": payslip.get("employee_id")}, limit=1)
    emp = emp_records[0] if emp_records else {}
    user = _find_user_by_id(emp.get("user_id")) if emp else None

    return {
        "payslip": {
            **payslip,
            "employee_name": user.get("name", "") if user else "",
        },
        "items": items,
    }


# --------------------------------------------------------------------------
# POST /payroll/runs/{id}/approve — Approve a payroll run
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/approve")
async def approve_payroll_run(
    run_id: int,
    current_user: dict = Depends(require_role("owner")),
) -> dict:
    """Approve a payroll run. Owner only."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft runs can be approved.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    dataflow_crud.update(
        "PayrollRun",
        run_id,
        {
            "status": "approved",
            "approved_by": actor_id,
            "approved_at": now,
        },
    )

    return {"message": "Payroll run approved.", "status": "approved"}


# --------------------------------------------------------------------------
# POST /payroll/runs/{id}/mark-paid — Mark a payroll run as paid
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/mark-paid")
async def mark_payroll_paid(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Mark a payroll run as paid."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved runs can be marked as paid.")

    # H3 redteam (round-12): block paying a later month when an earlier
    # one is still draft/approved. Pay-out-of-sequence almost always means
    # a missed month or a duplicate, and downstream CPF/IR8A reporting
    # depends on chronological ordering.
    period_end = run.get("period_end") or ""
    if period_end:
        siblings = dataflow_crud.list_records(
            "PayrollRun",
            {"company_id": company_id},
            cache_ttl=0,
        )
        earlier_pending = [
            s
            for s in siblings
            if s.get("id") != run_id
            and s.get("status") in ("draft", "approved")
            and (s.get("period_end") or "") < period_end
        ]
        if earlier_pending:
            blocker = sorted(
                earlier_pending,
                key=lambda s: s.get("period_end") or "",
            )[0]
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Earlier payroll run for period ending "
                    f"{blocker.get('period_end')} is still "
                    f"{blocker.get('status')}. Resolve it before paying "
                    f"a later run."
                ),
            )

    dataflow_crud.update("PayrollRun", run_id, {"status": "paid"})

    # Update all payslips in this run to paid
    payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id})
    for ps in payslips:
        dataflow_crud.update("Payslip", ps["id"], {"status": "paid"})

    # Mark approved claims as paid in this payroll run
    from datetime import date as _date

    period_month = _date.fromisoformat(run["period_start"]).strftime("%Y-%m")
    employees = dataflow_crud.list_records("Employee", {"company_id": company_id, "is_active": True})
    for emp in employees:
        emp_id = emp.get("id")
        try:
            emp_claims = dataflow_crud.list_records(
                "Claim",
                {
                    "employee_id": emp_id,
                    "status": "approved",
                    "claim_month": period_month,
                },
            )
            for cl in emp_claims:
                if cl.get("paid_in_payroll_run_id") is None:
                    dataflow_crud.update(
                        "Claim",
                        cl["id"],
                        {
                            "status": "paid",
                            "paid_in_payroll_run_id": run_id,
                        },
                    )
        except Exception:
            logger.warning(
                "Failed to mark claims as paid for employee %s in run %s",
                emp_id,
                run_id,
            )

    return {"message": "Payroll run marked as paid.", "status": "paid"}


# --------------------------------------------------------------------------
# POST /payroll/runs/{id}/cancel — Cancel a payroll run
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/cancel")
async def cancel_payroll_run(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Cancel a payroll run (only if not yet paid)."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Paid runs cannot be cancelled.")

    if run.get("status") == "approved" and current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can cancel approved payroll runs.")

    dataflow_crud.update("PayrollRun", run_id, {"status": "cancelled"})
    return {"message": "Payroll run cancelled.", "status": "cancelled"}


# --------------------------------------------------------------------------
# GET /payroll/my-payslips — Employee's own payslips
# --------------------------------------------------------------------------


@router.get("/my-payslips")
async def get_my_payslips(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the current employee's payslips across all runs."""
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    if company_id is None:
        return {"payslips": []}

    # Find employee record
    emp_records = dataflow_crud.list_records(
        "Employee",
        {
            "user_id": user_id,
            "company_id": company_id,
        },
        limit=1,
    )
    if not emp_records:
        return {"payslips": []}

    emp_id = emp_records[0].get("id")
    payslips = dataflow_crud.list_records("Payslip", {"employee_id": emp_id})

    # Only show paid/confirmed payslips to employees
    visible = [ps for ps in payslips if ps.get("status") in ("confirmed", "paid")]
    visible.sort(key=lambda ps: ps.get("period_start", ""), reverse=True)

    # The run-detail endpoint exposes the primary key as `payslip_id`; the
    # /my-payslips list previously returned the raw row which has only
    # `id`, causing the frontend to fetch `/my-payslips/undefined` (422)
    # when the user expanded a card. Mirror the run-detail contract.
    for ps in visible:
        ps.setdefault("payslip_id", ps.get("id"))

    return {"payslips": visible}


# --------------------------------------------------------------------------
# GET /payroll/my-payslips/{id} — Single payslip for employee
# --------------------------------------------------------------------------


@router.get("/my-payslips/{payslip_id}")
async def get_my_payslip_detail(
    payslip_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a specific payslip with line items (employee self-service)."""
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    payslip = dataflow_crud.read("Payslip", payslip_id)
    if payslip is None:
        raise HTTPException(status_code=404, detail="Payslip not found.")

    # Verify this payslip belongs to the current user
    emp_records = dataflow_crud.list_records(
        "Employee",
        {
            "user_id": user_id,
            "company_id": company_id,
        },
        limit=1,
    )
    if not emp_records or emp_records[0].get("id") != payslip.get("employee_id"):
        raise HTTPException(status_code=403, detail="Access denied.")

    items = dataflow_crud.list_records("PayslipItem", {"payslip_id": payslip_id})

    return {"payslip": payslip, "items": items}


# --------------------------------------------------------------------------
# GET /payroll/my-payslips/{id}/pdf — Employee's own payslip PDF download
# --------------------------------------------------------------------------


@router.get("/my-payslips/{payslip_id}/pdf")
async def get_my_payslip_pdf(
    payslip_id: int,
    current_user: dict = Depends(get_current_user),
) -> Response:
    """Download a PDF of the employee's own payslip (EA s88A compliant)."""
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    payslip = dataflow_crud.read("Payslip", payslip_id)
    if payslip is None:
        raise HTTPException(status_code=404, detail="Payslip not found.")

    # Verify this payslip belongs to the current user
    emp_records = dataflow_crud.list_records(
        "Employee",
        {
            "user_id": user_id,
            "company_id": company_id,
        },
        limit=1,
    )
    if not emp_records or emp_records[0].get("id") != payslip.get("employee_id"):
        raise HTTPException(status_code=403, detail="Access denied.")

    emp = emp_records[0]
    user = _find_user_by_id(emp.get("user_id"))
    if user:
        emp["name"] = user.get("name", "")

    items = dataflow_crud.list_records("PayslipItem", {"payslip_id": payslip_id})
    company = dataflow_crud.read("Company", company_id) or {}

    # Attach pay_date from the payroll run
    run_id = payslip.get("payroll_run_id")
    if run_id:
        run = dataflow_crud.read("PayrollRun", run_id)
        if run:
            payslip["pay_date"] = run.get("pay_date", "")

    return _build_payslip_pdf_response(payslip, items, emp, company)


# --------------------------------------------------------------------------
# GET /payroll/cpf-ytd/{employee_id} — CPF YTD breakdown
# --------------------------------------------------------------------------


@router.get("/cpf-ytd/{employee_id}")
async def get_cpf_ytd(
    employee_id: int,
    year: int = 0,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get CPF year-to-date breakdown by month for an employee."""
    company_id = get_current_company_id(current_user)
    if year == 0:
        year = datetime.now(timezone.utc).year

    # Verify employee belongs to company BEFORE fetching any records
    emp_records = dataflow_crud.list_records("Employee", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    records = dataflow_crud.list_records(
        "CpfYtdRecord",
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "year": year,
        },
    )

    records.sort(key=lambda r: r.get("month", 0))
    return {"year": year, "records": records}


# --------------------------------------------------------------------------
# GET /payroll/reports/summary — Payroll summary report
# --------------------------------------------------------------------------


@router.get("/reports/summary")
async def payroll_summary_report(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate payroll summary report for a run."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id})

    # Group by department
    by_department: dict[str, dict] = {}
    for ps in payslips:
        emp_records = dataflow_crud.list_records("Employee", {"id": ps.get("employee_id")}, limit=1)
        dept = emp_records[0].get("department", "Unassigned") if emp_records else "Unassigned"
        if dept not in by_department:
            by_department[dept] = {
                "department": dept,
                "employee_count": 0,
                "total_gross": 0.0,
                "total_net": 0.0,
                "total_employer_cpf": 0.0,
                "total_employee_cpf": 0.0,
            }
        by_department[dept]["employee_count"] += 1
        by_department[dept]["total_gross"] += ps.get("gross_salary", 0.0)
        by_department[dept]["total_net"] += ps.get("net_salary", 0.0)
        by_department[dept]["total_employer_cpf"] += ps.get("employer_cpf", 0.0)
        by_department[dept]["total_employee_cpf"] += ps.get("employee_cpf", 0.0)

    return {
        "run": run,
        "by_department": list(by_department.values()),
    }


# --------------------------------------------------------------------------
# GET /payroll/reports/ytd — YTD report for all employees
# --------------------------------------------------------------------------


@router.get("/reports/ytd")
async def ytd_report(
    year: int = 0,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate year-to-date report for all employees."""
    company_id = get_current_company_id(current_user)
    if year == 0:
        year = datetime.now(timezone.utc).year

    employees = dataflow_crud.list_records(
        "Employee",
        {
            "company_id": company_id,
            "is_active": True,
        },
    )

    report = []
    for emp in employees:
        emp_id = emp.get("id")
        user = _find_user_by_id(emp.get("user_id"))

        # Get all payslips for this employee in the year
        payslips = dataflow_crud.list_records("Payslip", {"employee_id": emp_id})
        year_payslips = [ps for ps in payslips if ps.get("period_start", "").startswith(str(year))]

        ytd_gross = sum(ps.get("gross_salary", 0.0) for ps in year_payslips)
        ytd_net = sum(ps.get("net_salary", 0.0) for ps in year_payslips)
        ytd_employer_cpf = sum(ps.get("employer_cpf", 0.0) for ps in year_payslips)
        ytd_employee_cpf = sum(ps.get("employee_cpf", 0.0) for ps in year_payslips)

        report.append(
            {
                "employee_id": emp_id,
                "name": user.get("name", "") if user else "",
                "department": emp.get("department", ""),
                "ytd_gross": round(ytd_gross, 2),
                "ytd_net": round(ytd_net, 2),
                "ytd_employer_cpf": round(ytd_employer_cpf, 2),
                "ytd_employee_cpf": round(ytd_employee_cpf, 2),
                "months_paid": len(year_payslips),
            }
        )

    return {"year": year, "employees": report}


# --------------------------------------------------------------------------
# Helpers: fetch payroll run + payslips + employees for statutory generation
# --------------------------------------------------------------------------


def _fetch_run_payslips_employees(
    run_id: int, company_id: int
) -> tuple[dict, list[dict], list[dict]]:
    """Fetch a payroll run, its payslips, and the corresponding employees.

    Raises HTTPException if the run is not found or does not belong to the company.
    Returns (run, payslips, employees).
    """
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id})

    # Collect unique employee IDs and fetch employee records
    emp_ids = {ps.get("employee_id") for ps in payslips}
    employees: list[dict] = []
    for eid in emp_ids:
        emp_records = dataflow_crud.list_records("Employee", {"id": eid}, limit=1)
        if emp_records:
            emp = emp_records[0]
            # Enrich with user name
            user = _find_user_by_id(emp.get("user_id"))
            if user:
                emp["name"] = user.get("name", "")
            employees.append(emp)

    return run, payslips, employees


# --------------------------------------------------------------------------
# POST /payroll/runs/{id}/cpf-file — Generate CPF e-Submit file
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/cpf-file")
async def generate_cpf_file(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> Response:
    """Generate CPF Board e-Submit CSV file for a payroll run."""
    from hr_advisory.services.statutory_files import generate_cpf_esubmit

    company_id = get_current_company_id(current_user)
    run, payslips, employees = _fetch_run_payslips_employees(run_id, company_id)

    csv_content = generate_cpf_esubmit(run, payslips, employees)

    period = run.get("period_start", "").replace("-", "")
    filename = f"cpf_esubmit_{period}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------
# POST /payroll/runs/{id}/bank-file — Generate bank GIRO file
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/bank-file")
async def generate_bank_file(
    run_id: int,
    format: str = Query("generic", pattern="^(generic|dbs|uob|ocbc)$"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> Response:
    """Generate bank payment file for a payroll run.

    Query parameter `format` accepts: generic, dbs, uob, ocbc.
    """
    from hr_advisory.services.statutory_files import generate_bank_giro

    company_id = get_current_company_id(current_user)
    run, payslips, employees = _fetch_run_payslips_employees(run_id, company_id)

    file_content = generate_bank_giro(run, payslips, employees, bank_format=format)

    period = run.get("period_start", "").replace("-", "")
    if format == "dbs":
        filename = f"giro_dbs_{period}.txt"
        media_type = "text/plain"
    else:
        filename = f"giro_{format}_{period}.csv"
        media_type = "text/csv"

    return Response(
        content=file_content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------
# Payslip PDF helpers (shared by admin and self-service endpoints)
# --------------------------------------------------------------------------


def _resolve_payslip_for_pdf(
    run_id: int,
    payslip_id: int,
    company_id: int,
) -> tuple[dict, list, dict, dict, dict]:
    """Fetch and validate all data needed to render a payslip PDF.

    Returns (payslip, items, employee, company, run).
    Raises HTTPException on any validation failure.
    """
    # Verify run ownership
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    # Fetch payslip
    payslip = dataflow_crud.read("Payslip", payslip_id)
    if payslip is None or payslip.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payslip not found.")
    if payslip.get("payroll_run_id") != run_id:
        raise HTTPException(status_code=400, detail="Payslip does not belong to this run.")

    # Fetch payslip items
    items = dataflow_crud.list_records("PayslipItem", {"payslip_id": payslip_id})

    # Fetch employee + user name
    emp_records = dataflow_crud.list_records("Employee", {"id": payslip.get("employee_id")}, limit=1)
    emp = emp_records[0] if emp_records else {}
    user = _find_user_by_id(emp.get("user_id")) if emp else None
    if user:
        emp["name"] = user.get("name", "")

    # Fetch company
    company = dataflow_crud.read("Company", company_id) or {}

    # Add pay_date from run to payslip dict for display
    payslip["pay_date"] = run.get("pay_date", "")

    return payslip, items, emp, company, run


def _build_payslip_pdf_response(
    payslip: dict,
    items: list,
    emp: dict,
    company: dict,
) -> Response:
    """Generate a PDF payslip and return it as a downloadable Response."""
    from hr_advisory.services.statutory_files import generate_payslip_pdf

    pdf_bytes = generate_payslip_pdf(payslip, items, emp, company)

    emp_name = emp.get("name", "employee")
    period = payslip.get("period_start", "period")
    filename = _sanitize_filename(f"payslip-{emp_name}-{period}", ".pdf")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# --------------------------------------------------------------------------
# POST /payroll/runs/{id}/payslips/{payslip_id}/pdf — Generate payslip PDF
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/payslips/{payslip_id}/pdf")
async def generate_payslip_pdf_endpoint(
    run_id: int,
    payslip_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> Response:
    """Generate payslip as a downloadable PDF (EA s88A compliant)."""
    company_id = get_current_company_id(current_user)
    payslip, items, emp, company, _run = _resolve_payslip_for_pdf(
        run_id, payslip_id, company_id
    )
    return _build_payslip_pdf_response(payslip, items, emp, company)


# --------------------------------------------------------------------------
# POST /payroll/runs/{id}/email-payslips — Send payslip emails (placeholder)
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/email-payslips")
async def email_payslips(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Send payslip emails to all employees in a payroll run.

    Generates HTML payslips and emails them to each employee.
    Currently returns the list of employees that would receive emails.
    Email delivery will be wired when the notification service is available.
    """
    company_id = get_current_company_id(current_user)
    run, payslips, employees = _fetch_run_payslips_employees(run_id, company_id)

    emp_by_id = {e.get("id"): e for e in employees}
    recipients: list[dict] = []

    for ps in payslips:
        emp = emp_by_id.get(ps.get("employee_id"), {})
        user = _find_user_by_id(emp.get("user_id")) if emp else None
        email = user.get("email", "") if user else ""
        recipients.append(
            {
                "employee_id": ps.get("employee_id"),
                "name": emp.get("name", ""),
                "email": email,
                "payslip_id": ps.get("id"),
                "status": "queued" if email else "no_email",
            }
        )

    return {
        "run_id": run_id,
        "total": len(recipients),
        "recipients": recipients,
        "message": "Payslip emails queued for delivery.",
    }


# --------------------------------------------------------------------------
# POST /payroll/tax/generate-ir8a — Generate IR8A for all employees
# --------------------------------------------------------------------------


@router.post("/tax/generate-ir8a")
async def generate_ir8a_all(
    year: int = Query(0),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate IR8A tax filing data for all active employees in a tax year.

    Creates or updates TaxFiling records in draft status.
    """
    from hr_advisory.services.statutory_files import generate_ir8a_data

    company_id = get_current_company_id(current_user)
    if year == 0:
        year = datetime.now(timezone.utc).year

    employees = dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "is_active": True},
    )
    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found.")

    filings: list[dict] = []

    for emp in employees:
        emp_id = emp.get("id")

        # Enrich with user name
        user = _find_user_by_id(emp.get("user_id"))
        if user:
            emp["name"] = user.get("name", "")

        # Fetch all payslips for this employee in the year
        all_payslips = dataflow_crud.list_records("Payslip", {"employee_id": emp_id})
        year_payslips = [
            ps for ps in all_payslips if ps.get("period_start", "").startswith(str(year))
        ]

        # Fetch all items for those payslips
        all_items: list[dict] = []
        for ps in year_payslips:
            ps_items = dataflow_crud.list_records("PayslipItem", {"payslip_id": ps.get("id")})
            all_items.extend(ps_items)

        ir8a = generate_ir8a_data(emp, year_payslips, all_items, year)

        # Create or update TaxFiling record
        existing = dataflow_crud.list_records(
            "TaxFiling",
            {
                "employee_id": emp_id,
                "tax_year": year,
                "filing_type": "ir8a",
            },
            limit=1,
        )

        if existing:
            dataflow_crud.update(
                "TaxFiling",
                existing[0]["id"],
                {"data": ir8a, "status": "draft"},
            )
            filing_id = existing[0]["id"]
        else:
            result = dataflow_crud.create(
                "TaxFiling",
                {
                    "company_id": company_id,
                    "employee_id": emp_id,
                    "tax_year": year,
                    "filing_type": "ir8a",
                    "data": ir8a,
                    "status": "draft",
                },
            )
            filing_id = result.get("id")

        filings.append(
            {
                "filing_id": filing_id,
                "employee_id": emp_id,
                "employee_name": emp.get("name", ""),
                "total_gross_income": ir8a.get("total_gross_income", 0.0),
                "employer_cpf": ir8a.get("employer_cpf", 0.0),
            }
        )

    return {
        "year": year,
        "filings_count": len(filings),
        "filings": filings,
    }


# --------------------------------------------------------------------------
# GET /payroll/tax/ir8a/{employee_id} — Get IR8A data
# --------------------------------------------------------------------------


@router.get("/tax/ir8a/{employee_id}")
async def get_ir8a(
    employee_id: int,
    year: int = Query(0),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get IR8A filing data for a specific employee and year."""
    from hr_advisory.services.statutory_files import generate_ir8a_data

    company_id = get_current_company_id(current_user)
    if year == 0:
        year = datetime.now(timezone.utc).year

    # Verify employee belongs to company
    emp_records = dataflow_crud.list_records("Employee", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp = emp_records[0]
    user = _find_user_by_id(emp.get("user_id"))
    if user:
        emp["name"] = user.get("name", "")

    # Check if a TaxFiling already exists
    existing = dataflow_crud.list_records(
        "TaxFiling",
        {
            "employee_id": employee_id,
            "tax_year": year,
            "filing_type": "ir8a",
        },
        limit=1,
    )

    if existing and existing[0].get("data"):
        return {
            "filing_id": existing[0].get("id"),
            "status": existing[0].get("status", "draft"),
            "ir8a": existing[0]["data"],
        }

    # Generate on-the-fly
    all_payslips = dataflow_crud.list_records("Payslip", {"employee_id": employee_id})
    year_payslips = [ps for ps in all_payslips if ps.get("period_start", "").startswith(str(year))]

    all_items: list[dict] = []
    for ps in year_payslips:
        ps_items = dataflow_crud.list_records("PayslipItem", {"payslip_id": ps.get("id")})
        all_items.extend(ps_items)

    ir8a = generate_ir8a_data(emp, year_payslips, all_items, year)

    return {
        "filing_id": None,
        "status": "not_filed",
        "ir8a": ir8a,
    }


# ==========================================================================
# PAY ITEMS — CRUD (T336)
# ==========================================================================


@router.get("/pay-items")
async def list_pay_items(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all pay items for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    items = dataflow_crud.list_records("PayItem", {"company_id": company_id, "is_archived": False})
    return {"pay_items": items, "count": len(items)}


@router.post("/pay-items")
async def create_pay_item(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new pay item (allowance, deduction, or contribution)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    item_type = body.get("item_type", "").strip()  # allowance, deduction, contribution
    if not name or not item_type:
        raise HTTPException(status_code=400, detail="name and item_type are required.")

    if item_type not in ("allowance", "deduction", "contribution"):
        raise HTTPException(
            status_code=400,
            detail="item_type must be one of: allowance, deduction, contribution.",
        )

    import math

    amount = float(body.get("amount", 0.0))
    if not math.isfinite(amount) or amount < 0:
        raise HTTPException(status_code=400, detail="Invalid amount: must be a finite non-negative number.")

    pay_item = dataflow_crud.create(
        "PayItem",
        {
            "company_id": company_id,
            "name": name,
            "item_type": item_type,
            "amount": amount,
            "is_taxable": body.get("is_taxable", True),
            "is_cpf_applicable": body.get("is_cpf_applicable", True),
            "is_recurring": body.get("is_recurring", False),
            "is_active": True,
        },
    )
    return {"pay_item": pay_item}


@router.patch("/pay-items/{pay_item_id}")
async def update_pay_item(
    pay_item_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a pay item."""
    company_id = get_current_company_id(current_user)
    item = dataflow_crud.read("PayItem", pay_item_id)
    if item is None or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pay item not found.")

    body = await request.json()
    allowed = {
        "name", "item_type", "amount", "is_taxable",
        "is_cpf_applicable", "is_recurring", "is_active",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    dataflow_crud.update("PayItem", pay_item_id, updates)
    updated = dataflow_crud.read("PayItem", pay_item_id)
    return {"pay_item": updated}


@router.delete("/pay-items/{pay_item_id}")
async def archive_pay_item(
    pay_item_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Archive (soft-delete) a pay item."""
    company_id = get_current_company_id(current_user)
    item = dataflow_crud.read("PayItem", pay_item_id)
    if item is None or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pay item not found.")

    dataflow_crud.update("PayItem", pay_item_id, {"is_archived": True})
    return {"message": "Pay item archived."}


# ==========================================================================
# PAY SCHEMES — CRUD (T337)
# ==========================================================================


@router.get("/pay-schemes")
async def list_pay_schemes(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all pay schemes for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    schemes = dataflow_crud.list_records(
        "PayScheme", {"company_id": company_id, "is_archived": False}
    )
    return {"pay_schemes": schemes, "count": len(schemes)}


@router.post("/pay-schemes")
async def create_pay_scheme(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new pay scheme."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")

    scheme = dataflow_crud.create(
        "PayScheme",
        {
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
            "pay_item_ids": body.get("pay_item_ids", []),
            "is_default": body.get("is_default", False),
            "is_active": True,
        },
    )
    return {"pay_scheme": scheme}


@router.patch("/pay-schemes/{scheme_id}")
async def update_pay_scheme(
    scheme_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a pay scheme."""
    company_id = get_current_company_id(current_user)
    scheme = dataflow_crud.read("PayScheme", scheme_id)
    if scheme is None or scheme.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pay scheme not found.")

    body = await request.json()
    allowed = {"name", "description", "pay_item_ids", "is_default", "is_active"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    dataflow_crud.update("PayScheme", scheme_id, updates)
    updated = dataflow_crud.read("PayScheme", scheme_id)
    return {"pay_scheme": updated}


@router.delete("/pay-schemes/{scheme_id}")
async def archive_pay_scheme(
    scheme_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Archive (soft-delete) a pay scheme."""
    company_id = get_current_company_id(current_user)
    scheme = dataflow_crud.read("PayScheme", scheme_id)
    if scheme is None or scheme.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pay scheme not found.")

    dataflow_crud.update("PayScheme", scheme_id, {"is_archived": True})
    return {"message": "Pay scheme archived."}


# ==========================================================================
# ADHOC PAYROLL (T338)
# ==========================================================================


@router.post("/runs/adhoc")
async def create_adhoc_payroll(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create an adhoc payroll run for selected employees.

    payroll_type must be one of: adhoc, final_salary, bonus.
    employee_ids is a list of employee IDs to include.
    """
    from hr_advisory.services.payroll_calculator import calculate_employee_payslip

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    period_start = body.get("period_start", "")
    period_end = body.get("period_end", "")
    pay_date = body.get("pay_date", "")
    payroll_type = body.get("payroll_type", "adhoc")
    employee_ids = body.get("employee_ids", [])

    if not period_start or not period_end or not pay_date:
        raise HTTPException(
            status_code=400,
            detail="period_start, period_end, and pay_date are required.",
        )
    if payroll_type not in ("adhoc", "final_salary", "bonus"):
        raise HTTPException(
            status_code=400,
            detail="payroll_type must be one of: adhoc, final_salary, bonus.",
        )
    if not employee_ids:
        raise HTTPException(status_code=400, detail="employee_ids is required.")

    actor_id = int(current_user.get("sub", 0))

    from datetime import date as _date

    period_date = _date.fromisoformat(period_start)
    period_month = period_date.strftime("%Y-%m")

    # Validate and fetch selected employees
    employees = []
    for eid in employee_ids:
        emp_records = dataflow_crud.list_records("Employee", {"id": eid}, limit=1)
        if emp_records and emp_records[0].get("company_id") == company_id:
            employees.append(emp_records[0])

    if not employees:
        raise HTTPException(status_code=400, detail="No valid employees found.")

    # Create adhoc payroll run
    run = dataflow_crud.create(
        "PayrollRun",
        {
            "company_id": company_id,
            "period_start": period_start,
            "period_end": period_end,
            "pay_date": pay_date,
            "status": "draft",
            "payroll_type": payroll_type,
            "employee_count": len(employees),
            "created_by": actor_id,
        },
    )
    run_id = run.get("id")

    total_gross = 0.0
    total_net = 0.0
    payslips_summary = []

    for emp in employees:
        emp_id = emp.get("id")

        components = dataflow_crud.list_records(
            "SalaryComponent",
            {"employee_id": emp_id, "is_active": True},
        )

        try:
            ytd_records = dataflow_crud.list_records(
                "CpfYtdRecord",
                {"employee_id": emp_id, "year": period_date.year},
            )
            ytd_ow_total = sum(r.get("ow_subject_to_cpf", 0.0) for r in ytd_records)
        except Exception:
            ytd_ow_total = 0.0

        result = calculate_employee_payslip(
            employee=emp,
            salary_components=components,
            period_start=period_start,
            period_end=period_end,
            ytd_ow_total=ytd_ow_total,
        )

        payslip = dataflow_crud.create(
            "Payslip",
            {
                "payroll_run_id": run_id,
                "employee_id": emp_id,
                "company_id": company_id,
                "period_start": period_start,
                "period_end": period_end,
                "basic_salary": result["basic_salary"],
                "gross_salary": result["gross_salary"],
                "net_salary": result["net_salary"],
                "employer_cpf": result["employer_cpf"],
                "employee_cpf": result["employee_cpf"],
                "sdl": result["sdl"],
                "fwl": result["fwl"],
                "shg_fund": result["shg_fund"],
                "shg_amount": result["shg_amount"],
                "cpf_ow_used": result["cpf_ow_used"],
                "cpf_aw_used": result["cpf_aw_used"],
                "status": "draft",
            },
        )

        for item in result.get("items", []):
            dataflow_crud.create(
                "PayslipItem",
                {
                    "payslip_id": payslip.get("id"),
                    "company_id": company_id,
                    "item_type": item["item_type"],
                    "name": item["name"],
                    "amount": item["amount"],
                    "is_taxable": item.get("is_taxable", True),
                    "is_cpf_applicable": item.get("is_cpf_applicable", True),
                    "notes": item.get("notes", ""),
                },
            )

        total_gross += result["gross_salary"]
        total_net += result["net_salary"]

        user = _find_user_by_id(emp.get("user_id"))
        payslips_summary.append(
            {
                "payslip_id": payslip.get("id"),
                "employee_id": emp_id,
                "name": user.get("name", "") if user else "",
                "gross_salary": result["gross_salary"],
                "net_salary": result["net_salary"],
            }
        )

    dataflow_crud.update(
        "PayrollRun",
        run_id,
        {
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
        },
    )

    return {
        "payroll_run": {
            "id": run_id,
            "payroll_type": payroll_type,
            "status": "draft",
            "employee_count": len(employees),
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
        },
        "payslips": payslips_summary,
    }


# ==========================================================================
# VARIANCE REPORT (T339)
# ==========================================================================


@router.get("/variance")
async def payroll_variance(
    run_id_a: int = Query(..., description="First payroll run ID (earlier month)"),
    run_id_b: int = Query(..., description="Second payroll run ID (later month)"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Compare two payroll runs and return per-employee variance."""
    company_id = get_current_company_id(current_user)

    run_a = dataflow_crud.read("PayrollRun", run_id_a)
    run_b = dataflow_crud.read("PayrollRun", run_id_b)
    if run_a is None or run_a.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run A not found.")
    if run_b is None or run_b.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run B not found.")

    payslips_a = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id_a})
    payslips_b = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id_b})

    map_a = {ps.get("employee_id"): ps for ps in payslips_a}
    map_b = {ps.get("employee_id"): ps for ps in payslips_b}

    all_emp_ids = set(map_a.keys()) | set(map_b.keys())
    variances = []

    for emp_id in all_emp_ids:
        ps_a = map_a.get(emp_id, {})
        ps_b = map_b.get(emp_id, {})

        gross_a = ps_a.get("gross_salary", 0.0)
        gross_b = ps_b.get("gross_salary", 0.0)
        net_a = ps_a.get("net_salary", 0.0)
        net_b = ps_b.get("net_salary", 0.0)

        # Only include if there is an actual change
        if gross_a == gross_b and net_a == net_b:
            continue

        emp_records = dataflow_crud.list_records("Employee", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = _find_user_by_id(emp.get("user_id")) if emp else None

        variances.append(
            {
                "employee_id": emp_id,
                "name": user.get("name", "") if user else "",
                "gross_a": gross_a,
                "gross_b": gross_b,
                "gross_change": round(gross_b - gross_a, 2),
                "net_a": net_a,
                "net_b": net_b,
                "net_change": round(net_b - net_a, 2),
            }
        )

    variances.sort(key=lambda v: abs(v.get("gross_change", 0)), reverse=True)

    return {
        "run_a": {"id": run_id_a, "period_start": run_a.get("period_start")},
        "run_b": {"id": run_id_b, "period_start": run_b.get("period_start")},
        "variances": variances,
        "count": len(variances),
    }


# ==========================================================================
# PAYSLIP SETTINGS (T340)
# ==========================================================================


def _get_payslip_settings(company_id: int) -> dict:
    """Fetch payslip display settings for a company, returning defaults if none exist."""
    settings = dataflow_crud.list_records(
        "PayslipSettings",
        {"company_id": company_id},
        limit=1,
    )
    if settings:
        return settings[0]
    return {
        "show_ytd": True,
        "show_employer_cpf": False,
        "show_company_logo": True,
        "company_name_override": "",
        "footer_text": "",
        "date_format": "DD/MM/YYYY",
    }


@router.get("/payslip-settings")
async def get_payslip_settings_endpoint(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the company's payslip display settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    settings = _get_payslip_settings(company_id)
    return {"settings": settings}


@router.put("/payslip-settings")
async def update_payslip_settings(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create or update the company's payslip display settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    allowed = {
        "show_ytd", "show_employer_cpf", "show_company_logo",
        "company_name_override", "footer_text", "date_format",
    }
    fields = {k: v for k, v in body.items() if k in allowed}

    existing = dataflow_crud.list_records(
        "PayslipSettings",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        dataflow_crud.update("PayslipSettings", existing[0]["id"], fields)
        updated = dataflow_crud.read("PayslipSettings", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = dataflow_crud.create("PayslipSettings", fields)

    return {"settings": updated}


# ==========================================================================
# PAYROLL LINE ITEMS — manual adjustments (T342)
# ==========================================================================


@router.get("/runs/{run_id}/line-items")
async def list_run_line_items(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all payslip items (line items) for a payroll run."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id})

    all_items = []
    for ps in payslips:
        items = dataflow_crud.list_records("PayslipItem", {"payslip_id": ps.get("id")})
        for item in items:
            item["payslip_id"] = ps.get("id")
            item["employee_id"] = ps.get("employee_id")
        all_items.extend(items)

    return {"line_items": all_items, "count": len(all_items)}


@router.post("/runs/{run_id}/line-items")
async def add_run_line_item(
    run_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a manual line item to a payslip within a payroll run."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Line items can only be added to draft runs.")

    body = await request.json()
    payslip_id = body.get("payslip_id")
    if not payslip_id:
        raise HTTPException(status_code=400, detail="payslip_id is required.")

    payslip = dataflow_crud.read("Payslip", payslip_id)
    if payslip is None or payslip.get("payroll_run_id") != run_id:
        raise HTTPException(status_code=404, detail="Payslip not found in this run.")

    name = body.get("name", "").strip()
    amount = float(body.get("amount", 0))
    item_type = body.get("item_type", "allowance")
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")

    import math
    if not math.isfinite(amount):
        raise HTTPException(status_code=400, detail="Invalid amount value.")

    item = dataflow_crud.create(
        "PayslipItem",
        {
            "payslip_id": payslip_id,
            "company_id": company_id,
            "item_type": item_type,
            "name": name,
            "amount": amount,
            "is_taxable": body.get("is_taxable", True),
            "is_cpf_applicable": body.get("is_cpf_applicable", True),
            "notes": body.get("notes", ""),
        },
    )
    return {"line_item": item}


@router.patch("/runs/{run_id}/line-items/{item_id}")
async def update_run_line_item(
    run_id: int,
    item_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a line item within a payroll run."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Line items can only be updated on draft runs.")

    item = dataflow_crud.read("PayslipItem", item_id)
    if item is None or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Line item not found.")

    body = await request.json()
    allowed = {"name", "amount", "item_type", "is_taxable", "is_cpf_applicable", "notes"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    dataflow_crud.update("PayslipItem", item_id, updates)
    updated = dataflow_crud.read("PayslipItem", item_id)
    return {"line_item": updated}


@router.delete("/runs/{run_id}/line-items/{item_id}")
async def delete_run_line_item(
    run_id: int,
    item_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a line item from a payroll run (hard delete via update to zero)."""
    company_id = get_current_company_id(current_user)
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Line items can only be deleted from draft runs.")

    item = dataflow_crud.read("PayslipItem", item_id)
    if item is None or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Line item not found.")

    # Soft-delete by zeroing out and marking
    dataflow_crud.update(
        "PayslipItem",
        item_id,
        {"amount": 0.0, "name": f"[DELETED] {item.get('name', '')}", "notes": "deleted"},
    )
    return {"message": "Line item deleted."}


# ==========================================================================
# PAYROLL SIMULATION (T371)
# ==========================================================================


@router.post("/simulate")
async def simulate_payroll(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Run payroll calculation without saving — returns a preview.

    Same inputs as /calculate but nothing is persisted.
    """
    from hr_advisory.services.payroll_calculator import calculate_employee_payslip

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(f"payroll_sim:{company_id}", max_requests=30, window_seconds=3600, action_name="payroll simulation")

    body = await request.json()
    period_start = body.get("period_start", "")
    period_end = body.get("period_end", "")
    employee_ids = body.get("employee_ids")  # optional: simulate for specific employees

    if not period_start or not period_end:
        raise HTTPException(
            status_code=400,
            detail="period_start and period_end are required.",
        )

    from datetime import date as _date

    period_date = _date.fromisoformat(period_start)
    period_month = period_date.strftime("%Y-%m")

    # Fetch employees
    if employee_ids:
        employees = []
        for eid in employee_ids:
            emp_records = dataflow_crud.list_records("Employee", {"id": eid}, limit=1)
            if emp_records and emp_records[0].get("company_id") == company_id:
                employees.append(emp_records[0])
    else:
        employees = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id, "is_active": True},
        )

    if not employees:
        raise HTTPException(status_code=400, detail="No employees found.")

    total_gross = 0.0
    total_net = 0.0
    total_employer_cpf = 0.0
    total_employee_cpf = 0.0
    simulation_results = []

    for emp in employees:
        emp_id = emp.get("id")

        components = dataflow_crud.list_records(
            "SalaryComponent",
            {"employee_id": emp_id, "is_active": True},
        )

        try:
            ytd_records = dataflow_crud.list_records(
                "CpfYtdRecord",
                {"employee_id": emp_id, "year": period_date.year},
            )
            ytd_ow_total = sum(r.get("ow_subject_to_cpf", 0.0) for r in ytd_records)
        except Exception:
            ytd_ow_total = 0.0

        # Cross-module data
        leave_deduction_days = 0.0
        overtime_hours = 0.0
        approved_claims_total = 0.0

        try:
            leave_apps = dataflow_crud.list_records(
                "LeaveApplication",
                {"employee_id": emp_id, "status": "approved", "leave_type_code": "unpaid"},
            )
            for la in leave_apps:
                if la.get("start_date", "") <= period_end and la.get("end_date", "") >= period_start:
                    leave_deduction_days += la.get("total_days", 0.0)
        except Exception:
            pass

        try:
            timesheets = dataflow_crud.list_records(
                "TimesheetApproval",
                {"employee_id": emp_id, "status": "approved", "month": period_month},
            )
            for ts in timesheets:
                overtime_hours += ts.get("total_ot_hours", 0.0)
        except Exception:
            pass

        try:
            emp_claims = dataflow_crud.list_records(
                "Claim",
                {"employee_id": emp_id, "status": "approved", "claim_month": period_month},
            )
            for cl in emp_claims:
                if cl.get("paid_in_payroll_run_id") is None:
                    approved_claims_total += cl.get("total_amount", 0.0)
        except Exception:
            pass

        result = calculate_employee_payslip(
            employee=emp,
            salary_components=components,
            period_start=period_start,
            period_end=period_end,
            ytd_ow_total=ytd_ow_total,
            leave_deduction_days=leave_deduction_days,
            overtime_hours=overtime_hours,
            approved_claims_total=approved_claims_total,
        )

        user = _find_user_by_id(emp.get("user_id"))
        simulation_results.append(
            {
                "employee_id": emp_id,
                "name": user.get("name", "") if user else "",
                "basic_salary": result["basic_salary"],
                "gross_salary": result["gross_salary"],
                "net_salary": result["net_salary"],
                "employer_cpf": result["employer_cpf"],
                "employee_cpf": result["employee_cpf"],
                "sdl": result["sdl"],
                "fwl": result["fwl"],
                "items": result.get("items", []),
            }
        )

        total_gross += result["gross_salary"]
        total_net += result["net_salary"]
        total_employer_cpf += result["employer_cpf"]
        total_employee_cpf += result["employee_cpf"]

    return {
        "simulation": True,
        "period_start": period_start,
        "period_end": period_end,
        "employee_count": len(employees),
        "total_gross": round(total_gross, 2),
        "total_net": round(total_net, 2),
        "total_employer_cpf": round(total_employer_cpf, 2),
        "total_employee_cpf": round(total_employee_cpf, 2),
        "employees": simulation_results,
    }


# --------------------------------------------------------------------------
# POST /payroll/tax/generate-ir21/{employee_id} — Generate IR21
# --------------------------------------------------------------------------


@router.post("/tax/generate-ir21/{employee_id}")
async def generate_ir21(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate IR21 filing data for a departing foreign employee.

    Requires `cessation_date` in the request body.
    """
    from hr_advisory.services.statutory_files import generate_ir21_data

    company_id = get_current_company_id(current_user)

    body = await request.json()
    cessation_date = body.get("cessation_date", "")
    if not cessation_date:
        raise HTTPException(status_code=400, detail="cessation_date is required.")

    # Verify employee belongs to company
    emp_records = dataflow_crud.list_records("Employee", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp = emp_records[0]
    user = _find_user_by_id(emp.get("user_id"))
    if user:
        emp["name"] = user.get("name", "")

    # Fetch all payslips and items for the employee
    all_payslips = dataflow_crud.list_records("Payslip", {"employee_id": employee_id})

    all_items: list[dict] = []
    for ps in all_payslips:
        ps_items = dataflow_crud.list_records("PayslipItem", {"payslip_id": ps.get("id")})
        all_items.extend(ps_items)

    ir21 = generate_ir21_data(emp, all_payslips, all_items, cessation_date)

    # Create TaxFiling record
    try:
        cess = datetime.fromisoformat(cessation_date)
        tax_year = cess.year
    except (ValueError, TypeError):
        tax_year = datetime.now(timezone.utc).year

    result = dataflow_crud.create(
        "TaxFiling",
        {
            "company_id": company_id,
            "employee_id": employee_id,
            "tax_year": tax_year,
            "filing_type": "ir21",
            "data": ir21,
            "status": "draft",
        },
    )

    return {
        "filing_id": result.get("id"),
        "status": "draft",
        "ir21": ir21,
    }


# ==========================================================================
# CPF RECONCILIATION REPORT (T166)
# ==========================================================================


@router.get("/reports/cpf-reconciliation")
async def cpf_reconciliation_report(
    year: int = Query(..., description="Tax/contribution year"),
    month: int = Query(0, description="Month (1-12). 0 = full year."),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """CPF reconciliation report comparing payslip CPF totals against YTD records.

    For each employee, aggregates employer CPF, employee CPF, and total CPF from
    payslips for the given period and compares against CpfYtdRecord totals.
    Any discrepancies are flagged.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    if month and (month < 1 or month > 12):
        raise HTTPException(status_code=400, detail="month must be between 1 and 12.")

    # Fetch all payroll runs for the period
    all_runs = dataflow_crud.list_records("PayrollRun", {"company_id": company_id})
    period_runs = []
    for run in all_runs:
        ps = run.get("period_start", "")
        if not ps:
            continue
        try:
            from datetime import date as _date
            run_date = _date.fromisoformat(ps)
            if run_date.year != year:
                continue
            if month and run_date.month != month:
                continue
            period_runs.append(run)
        except (ValueError, TypeError):
            continue

    # Fetch all active employees
    employees = dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "is_active": True},
    )

    reconciliation: list[dict] = []
    total_discrepancies = 0

    for emp in employees:
        emp_id = emp.get("id")
        user = _find_user_by_id(emp.get("user_id"))
        emp_name = user.get("name", "") if user else ""

        # Aggregate CPF from payslips
        payslip_employer_cpf = 0.0
        payslip_employee_cpf = 0.0

        for run in period_runs:
            run_id = run.get("id")
            payslips = dataflow_crud.list_records(
                "Payslip",
                {"payroll_run_id": run_id, "employee_id": emp_id},
            )
            for ps in payslips:
                payslip_employer_cpf += ps.get("employer_cpf", 0.0)
                payslip_employee_cpf += ps.get("employee_cpf", 0.0)

        payslip_total_cpf = payslip_employer_cpf + payslip_employee_cpf

        # Get CPF YTD records for comparison
        ytd_filter: dict = {
            "employee_id": emp_id,
            "company_id": company_id,
            "year": year,
        }
        if month:
            ytd_filter["month"] = month

        ytd_records = dataflow_crud.list_records("CpfYtdRecord", ytd_filter)
        ytd_employer_cpf = sum(r.get("employer_cpf", 0.0) for r in ytd_records)
        ytd_employee_cpf = sum(r.get("employee_cpf", 0.0) for r in ytd_records)
        ytd_total_cpf = ytd_employer_cpf + ytd_employee_cpf

        # Determine discrepancy (tolerance of 1 cent for rounding)
        employer_diff = round(payslip_employer_cpf - ytd_employer_cpf, 2)
        employee_diff = round(payslip_employee_cpf - ytd_employee_cpf, 2)
        total_diff = round(payslip_total_cpf - ytd_total_cpf, 2)
        has_discrepancy = abs(employer_diff) > 0.01 or abs(employee_diff) > 0.01

        if has_discrepancy:
            total_discrepancies += 1

        reconciliation.append(
            {
                "employee_id": emp_id,
                "employee_name": emp_name,
                "nric_fin_last4": emp.get("nric_fin_last4", ""),
                # Payslip totals
                "payslip_employer_cpf": round(payslip_employer_cpf, 2),
                "payslip_employee_cpf": round(payslip_employee_cpf, 2),
                "payslip_total_cpf": round(payslip_total_cpf, 2),
                # YTD record totals
                "ytd_employer_cpf": round(ytd_employer_cpf, 2),
                "ytd_employee_cpf": round(ytd_employee_cpf, 2),
                "ytd_total_cpf": round(ytd_total_cpf, 2),
                # Discrepancy
                "employer_cpf_diff": employer_diff,
                "employee_cpf_diff": employee_diff,
                "total_cpf_diff": total_diff,
                "has_discrepancy": has_discrepancy,
            }
        )

    period_label = f"{year}-{month:02d}" if month else str(year)

    return {
        "year": year,
        "month": month if month else None,
        "period": period_label,
        "employee_count": len(reconciliation),
        "discrepancy_count": total_discrepancies,
        "reconciliation": reconciliation,
    }


# ==========================================================================
# IR8A CSV EXPORT — IRAS AIS FORMAT (T168)
# ==========================================================================


@router.post("/tax/ir8a-csv")
async def export_ir8a_csv(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> Response:
    """Export IR8A data as CSV in IRAS Auto-Inclusion Scheme format.

    Accepts JSON body with `year` (required) and optional `employee_ids` list.
    If employee_ids is omitted, exports for all active employees.
    Returns a downloadable CSV file.
    """
    from hr_advisory.services.statutory_files import generate_ir8a_data

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    year = body.get("year", 0)
    employee_ids = body.get("employee_ids")

    if not year:
        raise HTTPException(status_code=400, detail="year is required.")

    # Fetch employees
    if employee_ids:
        employees = []
        for eid in employee_ids:
            emp_records = dataflow_crud.list_records("Employee", {"id": eid}, limit=1)
            if emp_records and emp_records[0].get("company_id") == company_id:
                employees.append(emp_records[0])
    else:
        employees = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id, "is_active": True},
        )

    if not employees:
        raise HTTPException(status_code=400, detail="No employees found.")

    # Generate IR8A data for each employee and build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # IRAS AIS CSV header
    writer.writerow(
        [
            "Employee ID",
            "Employee Name",
            "ID Type",
            "ID Number",
            "Date of Birth",
            "Date of Commencement",
            "Date of Cessation",
            "Gross Salary",
            "Bonus",
            "Director's Fee",
            "Others",
            "Total",
            "Employee CPF",
            "Employer CPF",
        ]
    )

    for emp in employees:
        emp_id = emp.get("id")
        user = _find_user_by_id(emp.get("user_id"))
        if user:
            emp["name"] = user.get("name", "")

        # Fetch payslips and items for the year
        all_payslips = dataflow_crud.list_records("Payslip", {"employee_id": emp_id})
        year_payslips = [
            ps for ps in all_payslips if ps.get("period_start", "").startswith(str(year))
        ]

        all_items: list[dict] = []
        for ps in year_payslips:
            ps_items = dataflow_crud.list_records("PayslipItem", {"payslip_id": ps.get("id")})
            all_items.extend(ps_items)

        ir8a = generate_ir8a_data(emp, year_payslips, all_items, year)

        # Determine ID type
        nric_fin = emp.get("nric_fin", "")
        if nric_fin.upper().startswith(("S", "T")):
            id_type = "NRIC"
        elif nric_fin.upper().startswith(("F", "G", "M")):
            id_type = "FIN"
        else:
            id_type = "NRIC"

        # Others = commission + overtime + other allowances
        others = (
            ir8a.get("commission", 0.0)
            + ir8a.get("overtime_pay", 0.0)
            + ir8a.get("total_allowances", 0.0)
        )

        writer.writerow(
            [
                emp.get("employee_id_internal", str(emp_id)),
                ir8a.get("employee_name", ""),
                id_type,
                nric_fin,
                emp.get("date_of_birth", ""),
                emp.get("start_date", ""),
                emp.get("end_date", ""),
                f"{ir8a.get('gross_salary_wages', 0.0):.2f}",
                f"{ir8a.get('bonus', 0.0):.2f}",
                f"{ir8a.get('director_fees', 0.0):.2f}",
                f"{others:.2f}",
                f"{ir8a.get('total_gross_income', 0.0):.2f}",
                f"{ir8a.get('employee_cpf', 0.0):.2f}",
                f"{ir8a.get('employer_cpf', 0.0):.2f}",
            ]
        )

    csv_content = output.getvalue()
    filename = _sanitize_filename(f"ir8a_ais_{year}", ".csv")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==========================================================================
# APPENDIX 8A — BENEFITS IN KIND (T169)
# ==========================================================================


@router.get("/tax/appendix-8a/{employee_id}")
async def get_appendix_8a(
    employee_id: int,
    year: int = Query(0),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get Appendix 8A (Benefits in Kind) data for a specific employee and year.

    Returns the standard Appendix 8A structure with housing, car, utilities,
    and other benefit categories. Values will be zero for employees who receive
    only cash compensation.
    """
    from hr_advisory.services.statutory_files import generate_appendix_8a

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    if year == 0:
        year = datetime.now(timezone.utc).year

    # Verify employee belongs to company
    emp_records = dataflow_crud.list_records("Employee", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp = emp_records[0]
    user = _find_user_by_id(emp.get("user_id"))
    if user:
        emp["name"] = user.get("name", "")

    # Fetch payslips and items for the year
    all_payslips = dataflow_crud.list_records("Payslip", {"employee_id": employee_id})
    year_payslips = [
        ps for ps in all_payslips if ps.get("period_start", "").startswith(str(year))
    ]

    all_items: list[dict] = []
    for ps in year_payslips:
        ps_items = dataflow_crud.list_records("PayslipItem", {"payslip_id": ps.get("id")})
        all_items.extend(ps_items)

    appendix_8a = generate_appendix_8a(emp, year_payslips, all_items, year)

    return {
        "employee_id": employee_id,
        "year": year,
        "appendix_8a": appendix_8a,
    }


# ==========================================================================
# PAYROLL DATA CSV EXPORT (T189)
# ==========================================================================


@router.get("/export")
async def export_payroll_csv(
    start_date: str = Query(..., description="Period start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Period end date (YYYY-MM-DD)"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> Response:
    """Export payroll data as a downloadable CSV file.

    Fetches all payroll runs within the date range and exports a row per
    employee per payroll period with salary breakdown, statutory contributions,
    and net pay.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Validate date inputs
    from datetime import date as _date
    try:
        _date.fromisoformat(start_date)
        _date.fromisoformat(end_date)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date.")

    # Fetch payroll runs in the date range
    all_runs = dataflow_crud.list_records("PayrollRun", {"company_id": company_id})
    period_runs = [
        r for r in all_runs
        if r.get("period_start", "") >= start_date and r.get("period_end", "") <= end_date
    ]
    period_runs.sort(key=lambda r: r.get("period_start", ""))

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Period",
            "Employee Name",
            "Employee ID",
            "Basic Salary",
            "Gross Salary",
            "Employee CPF",
            "Employer CPF",
            "SDL",
            "FWL",
            "SHG",
            "Net Pay",
            "Status",
        ]
    )

    for run in period_runs:
        run_id = run.get("id")
        period = f"{run.get('period_start', '')} to {run.get('period_end', '')}"
        run_status = run.get("status", "")

        payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id})

        for ps in payslips:
            emp_id = ps.get("employee_id")
            emp_records = dataflow_crud.list_records("Employee", {"id": emp_id}, limit=1)
            emp = emp_records[0] if emp_records else {}
            user = _find_user_by_id(emp.get("user_id")) if emp else None
            emp_name = user.get("name", "") if user else ""
            emp_id_internal = emp.get("employee_id_internal", str(emp_id))

            writer.writerow(
                [
                    period,
                    emp_name,
                    emp_id_internal,
                    f"{ps.get('basic_salary', 0.0):.2f}",
                    f"{ps.get('gross_salary', 0.0):.2f}",
                    f"{ps.get('employee_cpf', 0.0):.2f}",
                    f"{ps.get('employer_cpf', 0.0):.2f}",
                    f"{ps.get('sdl', 0.0):.2f}",
                    f"{ps.get('fwl', 0.0):.2f}",
                    f"{ps.get('shg_amount', 0.0):.2f}",
                    f"{ps.get('net_salary', 0.0):.2f}",
                    run_status,
                ]
            )

    csv_content = output.getvalue()
    filename = _sanitize_filename(f"payroll_{start_date}_to_{end_date}", ".csv")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==========================================================================
# PARALLEL PAYROLL RUN — Compare Arbor vs External HRIS
# ==========================================================================

# Expected CSV columns (case-insensitive, whitespace-trimmed):
#   Employee Name | Employee ID | Period | Gross Salary | Net Salary
#   | Employee CPF | Employer CPF | SDL (optional)
#
# At least one of Employee Name or Employee ID must be present per row.

_PARALLEL_CSV_REQUIRED_COLUMNS = {
    "gross_salary",
    "net_salary",
    "employee_cpf",
    "employer_cpf",
}

# Map of normalised header -> canonical field name
_PARALLEL_CSV_COLUMN_MAP: dict[str, str] = {
    "employee name": "employee_name",
    "employee_name": "employee_name",
    "name": "employee_name",
    "employee id": "employee_id",
    "employee_id": "employee_id",
    "id": "employee_id",
    "period": "period",
    "month": "period",
    "pay period": "period",
    "gross salary": "gross_salary",
    "gross_salary": "gross_salary",
    "gross": "gross_salary",
    "net salary": "net_salary",
    "net_salary": "net_salary",
    "net": "net_salary",
    "net pay": "net_salary",
    "employee cpf": "employee_cpf",
    "employee_cpf": "employee_cpf",
    "cpf employee": "employee_cpf",
    "employer cpf": "employer_cpf",
    "employer_cpf": "employer_cpf",
    "cpf employer": "employer_cpf",
    "sdl": "sdl",
}


def _normalise_header(header: str) -> str:
    """Lowercase, strip whitespace, collapse multiple spaces."""
    return re.sub(r"\s+", " ", header.strip().lower())


def _parse_float(value: str, field_name: str, row_num: int) -> float:
    """Parse a numeric string to float, raising a clear error on failure."""
    cleaned = value.strip().replace(",", "").replace("$", "")
    if not cleaned:
        return 0.0
    try:
        result = float(cleaned)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Row {row_num}: '{field_name}' value '{value}' is not a valid number.",
        )
    if not math.isfinite(result):
        raise HTTPException(
            status_code=400,
            detail=f"Row {row_num}: '{field_name}' value '{value}' is not a valid number.",
        )
    return result


@router.post("/parallel/upload")
async def upload_parallel_payroll(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Upload external payslip data (CSV) for parallel comparison with Arbor.

    Accepts multipart/form-data with a CSV file. The CSV must contain columns
    for employee identification (name or ID), salary figures (gross, net),
    and statutory contributions (employee CPF, employer CPF).

    Returns the parsed rows and a parallel_run_id for use in the compare endpoint.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"parallel_upload:{company_id}",
        max_requests=30,
        window_seconds=3600,
        action_name="parallel payroll upload",
    )

    # --- Read the uploaded file from multipart form ---
    form = await request.form()
    file = form.get("file")
    if file is None:
        raise HTTPException(status_code=400, detail="CSV file is required. Upload as 'file' field in multipart/form-data.")

    content_bytes = await file.read()
    if len(content_bytes) > 5 * 1024 * 1024:  # 5 MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5MB.")

    filename = getattr(file, "filename", "upload.csv") or "upload.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    # --- Decode and parse CSV ---
    try:
        text = content_bytes.decode("utf-8-sig")  # Handle BOM from Excel exports
    except UnicodeDecodeError:
        try:
            text = content_bytes.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Unable to decode CSV file. Use UTF-8 or Latin-1 encoding.")

    reader = csv.reader(io.StringIO(text))

    # --- Parse header row ---
    try:
        raw_headers = next(reader)
    except StopIteration:
        raise HTTPException(status_code=400, detail="CSV file is empty.")

    column_map: dict[int, str] = {}
    for idx, raw_header in enumerate(raw_headers):
        normalised = _normalise_header(raw_header)
        canonical = _PARALLEL_CSV_COLUMN_MAP.get(normalised)
        if canonical:
            column_map[idx] = canonical

    # Validate that required columns are present
    mapped_fields = set(column_map.values())
    missing_required = _PARALLEL_CSV_REQUIRED_COLUMNS - mapped_fields
    if missing_required:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {', '.join(sorted(missing_required))}. "
            f"Found: {', '.join(sorted(mapped_fields))}.",
        )

    has_name = "employee_name" in mapped_fields
    has_id = "employee_id" in mapped_fields
    if not has_name and not has_id:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least one of 'Employee Name' or 'Employee ID' columns.",
        )

    # --- Parse data rows ---
    rows: list[dict] = []
    for row_num, raw_row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in raw_row):
            continue  # Skip blank rows

        row_data: dict = {}
        for col_idx, field_name in column_map.items():
            if col_idx < len(raw_row):
                row_data[field_name] = raw_row[col_idx].strip()
            else:
                row_data[field_name] = ""

        # Validate employee identification
        emp_name = row_data.get("employee_name", "").strip()
        emp_id = row_data.get("employee_id", "").strip()
        if not emp_name and not emp_id:
            raise HTTPException(
                status_code=400,
                detail=f"Row {row_num}: must have at least an employee name or employee ID.",
            )

        # Parse numeric fields
        parsed_row = {
            "employee_name": emp_name,
            "employee_id": emp_id,
            "period": row_data.get("period", ""),
            "gross_salary": _parse_float(row_data.get("gross_salary", "0"), "Gross Salary", row_num),
            "net_salary": _parse_float(row_data.get("net_salary", "0"), "Net Salary", row_num),
            "employee_cpf": _parse_float(row_data.get("employee_cpf", "0"), "Employee CPF", row_num),
            "employer_cpf": _parse_float(row_data.get("employer_cpf", "0"), "Employer CPF", row_num),
            "sdl": _parse_float(row_data.get("sdl", "0"), "SDL", row_num),
        }
        rows.append(parsed_row)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no data rows.")

    # --- Store the parallel run ---
    run_id = str(uuid.uuid4())

    while len(_parallel_runs) >= MAX_PARALLEL_RUNS:
        _parallel_runs.popitem(last=False)  # Evict oldest entry

    _parallel_runs[run_id] = {
        "id": run_id,
        "company_id": company_id,
        "filename": filename,
        "uploaded_by": int(current_user.get("sub", 0)),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "rows": rows,
    }

    return {
        "parallel_run_id": run_id,
        "filename": filename,
        "row_count": len(rows),
        "rows": rows,
    }


@router.post("/parallel/compare")
async def compare_parallel_payroll(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Compare external payslip data against an Arbor payroll run.

    For each employee present in both datasets, compares gross salary, net salary,
    employee CPF, and employer CPF. Gross salary must match exactly; other fields
    allow a $1.00 tolerance (statutory rounding differences are common).

    Returns per-employee comparison details and an overall summary.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"parallel_compare:{company_id}",
        max_requests=60,
        window_seconds=3600,
        action_name="parallel payroll comparison",
    )

    body = await request.json()
    parallel_run_id = body.get("parallel_run_id", "")
    payroll_run_id = body.get("payroll_run_id")

    if not parallel_run_id:
        raise HTTPException(status_code=400, detail="parallel_run_id is required.")
    if payroll_run_id is None:
        raise HTTPException(status_code=400, detail="payroll_run_id is required (Arbor payroll run).")

    try:
        payroll_run_id = int(payroll_run_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="payroll_run_id must be an integer.")

    # --- Retrieve the parallel run ---
    parallel = _parallel_runs.get(parallel_run_id)
    if parallel is None:
        raise HTTPException(
            status_code=404,
            detail="Parallel run not found. It may have expired — please re-upload.",
        )
    if parallel.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Parallel run not found.")

    # --- Retrieve the Arbor payroll run ---
    arbor_run = dataflow_crud.read("PayrollRun", payroll_run_id)
    if arbor_run is None or arbor_run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Arbor payroll run not found.")

    payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": payroll_run_id})

    # --- Build Arbor lookup keyed by normalised name and employee ID ---
    arbor_by_name: dict[str, dict] = {}
    arbor_by_emp_id: dict[str, dict] = {}

    for ps in payslips:
        emp_id = ps.get("employee_id")
        emp_records = dataflow_crud.list_records("Employee", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = _find_user_by_id(emp.get("user_id")) if emp else None
        emp_name = (user.get("name", "") if user else "").strip()
        emp_id_internal = (emp.get("employee_id_internal", "") or "").strip()

        arbor_record = {
            "employee_name": emp_name,
            "employee_id_internal": emp_id_internal,
            "gross_salary": ps.get("gross_salary", 0.0),
            "net_salary": ps.get("net_salary", 0.0),
            "employee_cpf": ps.get("employee_cpf", 0.0),
            "employer_cpf": ps.get("employer_cpf", 0.0),
            "sdl": ps.get("sdl", 0.0),
        }

        if emp_name:
            arbor_by_name[emp_name.lower()] = arbor_record
        if emp_id_internal:
            arbor_by_emp_id[emp_id_internal.lower()] = arbor_record

    # --- Compare each external row against Arbor ---
    comparisons: list[dict] = []
    total_matches = 0
    total_mismatches = 0
    unmatched_external: list[dict] = []
    largest_deviation = 0.0
    largest_deviation_field = ""
    largest_deviation_employee = ""

    TOLERANCE_EXACT = 0.005  # Gross: essentially exact (half-cent for float precision)
    TOLERANCE_STATUTORY = 1.005  # CPF/net: $1.00 tolerance for rounding

    for ext_row in parallel["rows"]:
        ext_name = ext_row.get("employee_name", "").strip()
        ext_id = ext_row.get("employee_id", "").strip()

        # Try to match: first by employee ID, then by name
        arbor_record = None
        matched_by = ""
        if ext_id and ext_id.lower() in arbor_by_emp_id:
            arbor_record = arbor_by_emp_id[ext_id.lower()]
            matched_by = "employee_id"
        elif ext_name and ext_name.lower() in arbor_by_name:
            arbor_record = arbor_by_name[ext_name.lower()]
            matched_by = "employee_name"

        if arbor_record is None:
            unmatched_external.append({
                "employee_name": ext_name,
                "employee_id": ext_id,
                "reason": "No matching employee found in Arbor payroll run.",
            })
            continue

        # Compare fields
        fields_to_compare = [
            ("gross_salary", TOLERANCE_EXACT),
            ("net_salary", TOLERANCE_STATUTORY),
            ("employee_cpf", TOLERANCE_STATUTORY),
            ("employer_cpf", TOLERANCE_STATUTORY),
        ]

        field_results: list[dict] = []
        row_has_mismatch = False

        for field_name, tolerance in fields_to_compare:
            ext_val = ext_row.get(field_name, 0.0)
            arbor_val = arbor_record.get(field_name, 0.0)
            diff = round(ext_val - arbor_val, 2)
            abs_diff = abs(diff)
            is_match = abs_diff < tolerance

            field_results.append({
                "field": field_name,
                "external": round(ext_val, 2),
                "arbor": round(arbor_val, 2),
                "difference": diff,
                "match": is_match,
                "tolerance": round(tolerance, 2),
            })

            if not is_match:
                row_has_mismatch = True
                if abs_diff > largest_deviation:
                    largest_deviation = abs_diff
                    largest_deviation_field = field_name
                    largest_deviation_employee = ext_name or ext_id

        # Also compare SDL if both datasets have it
        ext_sdl = ext_row.get("sdl", 0.0)
        arbor_sdl = arbor_record.get("sdl", 0.0)
        if ext_sdl > 0 or arbor_sdl > 0:
            sdl_diff = round(ext_sdl - arbor_sdl, 2)
            sdl_match = abs(sdl_diff) < TOLERANCE_STATUTORY
            field_results.append({
                "field": "sdl",
                "external": round(ext_sdl, 2),
                "arbor": round(arbor_sdl, 2),
                "difference": sdl_diff,
                "match": sdl_match,
                "tolerance": round(TOLERANCE_STATUTORY, 2),
            })
            if not sdl_match:
                row_has_mismatch = True
                if abs(sdl_diff) > largest_deviation:
                    largest_deviation = abs(sdl_diff)
                    largest_deviation_field = "sdl"
                    largest_deviation_employee = ext_name or ext_id

        if row_has_mismatch:
            total_mismatches += 1
        else:
            total_matches += 1

        comparisons.append({
            "employee_name": ext_name or arbor_record.get("employee_name", ""),
            "employee_id": ext_id or arbor_record.get("employee_id_internal", ""),
            "matched_by": matched_by,
            "overall_match": not row_has_mismatch,
            "fields": field_results,
        })

    # --- Build unmatched Arbor employees (in Arbor but not in external) ---
    matched_arbor_names = set()
    matched_arbor_ids = set()
    for comp in comparisons:
        if comp.get("matched_by") == "employee_name":
            matched_arbor_names.add((comp.get("employee_name") or "").lower())
        elif comp.get("matched_by") == "employee_id":
            matched_arbor_ids.add((comp.get("employee_id") or "").lower())

    unmatched_arbor: list[dict] = []
    for ps in payslips:
        emp_id = ps.get("employee_id")
        emp_records = dataflow_crud.list_records("Employee", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = _find_user_by_id(emp.get("user_id")) if emp else None
        emp_name = (user.get("name", "") if user else "").strip()
        emp_id_internal = (emp.get("employee_id_internal", "") or "").strip()

        name_matched = emp_name and emp_name.lower() in matched_arbor_names
        id_matched = emp_id_internal and emp_id_internal.lower() in matched_arbor_ids
        if not name_matched and not id_matched:
            unmatched_arbor.append({
                "employee_name": emp_name,
                "employee_id_internal": emp_id_internal,
                "reason": "Employee exists in Arbor but not in uploaded external data.",
            })

    return {
        "parallel_run_id": parallel_run_id,
        "payroll_run_id": payroll_run_id,
        "arbor_run_period": f"{arbor_run.get('period_start', '')} to {arbor_run.get('period_end', '')}",
        "arbor_run_status": arbor_run.get("status", ""),
        "summary": {
            "employees_compared": len(comparisons),
            "full_matches": total_matches,
            "mismatches": total_mismatches,
            "unmatched_external": len(unmatched_external),
            "unmatched_arbor": len(unmatched_arbor),
            "largest_deviation": round(largest_deviation, 2),
            "largest_deviation_field": largest_deviation_field,
            "largest_deviation_employee": largest_deviation_employee,
        },
        "comparisons": comparisons,
        "unmatched_external": unmatched_external,
        "unmatched_arbor": unmatched_arbor,
    }


# --------------------------------------------------------------------------
# Xero payroll-journal export
# --------------------------------------------------------------------------
#
# Lifecycle:
#   1. User OAuth-connects Xero in Settings → Integrations
#      (existing flow — uses XeroAdapter token store).
#   2. GET /payroll/xero/status — UI checks if Xero is connected and
#      whether an account mapping has been saved.
#   3. GET /payroll/xero/chart-of-accounts — populates dropdowns in the
#      mapping modal.
#   4. GET /payroll/xero/account-mapping — returns saved mapping if any,
#      otherwise auto-match suggestions from the chart of accounts.
#   5. PUT /payroll/xero/account-mapping — persists the user-confirmed
#      mapping (idempotent upsert keyed by company_id).
#   6. POST /payroll/runs/{run_id}/export-xero — builds the journal,
#      posts to Xero, stamps xero_journal_id + xero_exported_at on the
#      PayrollRun. Run must be in 'approved' or 'paid' status.

_XERO_PROVIDER = "xero"

# Advisory-lock namespace for Xero exports. Postgres advisory locks
# accept two int4s; we use a stable hash of "xero-export" as the
# class id and (company_id << 16) | (run_id & 0xFFFF) as the object
# id. Collisions across companies are mathematically possible but
# benign — they just serialize unrelated exports under contention,
# which is a soft failure not a correctness one.
_XERO_LOCK_CLASS_ID = 0x7E70_E000  # arbitrary stable namespace constant


def _xero_lock_object_id(company_id: int, run_id: int) -> int:
    return ((company_id & 0xFFFF) << 16) | (run_id & 0xFFFF)


class _XeroExportInProgress(Exception):
    """Raised when an advisory lock for the same run is already held."""


class _xero_export_lock:
    """Context manager that takes a Postgres session-level advisory lock
    keyed on (company_id, run_id) for the duration of an export.

    Concurrent calls for the same run get ``pg_try_advisory_lock = false``
    and we raise ``_XeroExportInProgress`` immediately rather than
    blocking — caller surfaces as 409.

    Implemented as a sync class because psycopg2 is sync; called via
    ``run_in_executor`` from the async endpoint so the event loop
    stays free during the Xero round-trip.
    """

    def __init__(self, company_id: int, run_id: int):
        self.company_id = company_id
        self.run_id = run_id
        self._conn = None
        self._cur = None
        self._object_id = _xero_lock_object_id(company_id, run_id)

    def __enter__(self):
        import os as _os

        import psycopg2

        self._conn = psycopg2.connect(_os.environ["DATABASE_URL"])
        self._conn.autocommit = True  # advisory locks don't need a tx
        self._cur = self._conn.cursor()
        self._cur.execute(
            "SELECT pg_try_advisory_lock(%s, %s)",
            (_XERO_LOCK_CLASS_ID, self._object_id),
        )
        acquired = bool(self._cur.fetchone()[0])
        if not acquired:
            self._cleanup()
            raise _XeroExportInProgress(
                f"Another Xero export is already in progress for run "
                f"{self.run_id}."
            )
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self._cur.execute(
                "SELECT pg_advisory_unlock(%s, %s)",
                (_XERO_LOCK_CLASS_ID, self._object_id),
            )
        finally:
            self._cleanup()
        return False

    def _cleanup(self) -> None:
        if self._cur is not None:
            try:
                self._cur.close()
            except Exception:
                pass
            self._cur = None
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


def _get_xero_mapping(company_id: int) -> dict | None:
    rows = dataflow_crud.list_records(
        "XeroAccountMapping",
        {"company_id": company_id},
        cache_ttl=0,
    )
    return rows[0] if rows else None


@router.get("/xero/status")
async def get_xero_status(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Connection + mapping status for the Xero export feature."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    adapter = get_xero_adapter()
    connected = adapter.is_connected(str(company_id))
    mapping = _get_xero_mapping(company_id)

    from hr_advisory.services.xero_payroll_journal import mapping_is_complete

    return {
        "connected": connected,
        "mapping_present": mapping is not None,
        "mapping_complete": bool(mapping and mapping_is_complete(mapping)),
    }


@router.get("/xero/chart-of-accounts")
async def get_xero_chart_of_accounts(
    refresh: bool = False,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Fetch the company's Xero chart of accounts for dropdown population.

    ``refresh=true`` bypasses the 24h cache — used by the mapping page's
    "Refresh accounts from Xero" button when an accountant has renamed
    or archived an account on the Xero side.
    """
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    adapter = get_xero_adapter()
    if not adapter.is_connected(str(company_id)):
        raise HTTPException(
            status_code=409,
            detail="Xero is not connected. Connect it in Settings → Integrations first.",
        )

    try:
        accounts = await adapter.get_chart_of_accounts(
            str(company_id), force_refresh=refresh
        )
    except Exception as exc:
        logger.exception("Failed to fetch Xero chart of accounts")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch chart of accounts from Xero: {exc}",
        ) from exc

    return {"accounts": accounts}


@router.get("/xero/mapping-health")
async def get_xero_mapping_health(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Compare the saved mapping against the current Xero chart.

    Returns the codes that are now archived (still exist but inactive),
    missing (no longer in the chart at all), or system-managed (Xero
    rejects manual journals against them). The frontend mapping page
    shows a banner for any non-empty result so the customer fixes
    their mapping BEFORE the next export attempt fails.
    """
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter
    from hr_advisory.services.xero_payroll_journal import MAPPING_FIELDS

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    saved = _get_xero_mapping(company_id)
    if saved is None:
        return {
            "archived": [],
            "missing": [],
            "system_managed": [],
            "ok": True,
        }

    adapter = get_xero_adapter()
    if not adapter.is_connected(str(company_id)):
        raise HTTPException(
            status_code=409,
            detail="Xero is not connected.",
        )

    try:
        accounts = await adapter.get_chart_of_accounts(str(company_id))
    except Exception as exc:
        logger.exception("mapping-health: failed to fetch CoA")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch chart of accounts from Xero: {exc}",
        ) from exc

    by_code = {str(a.get("code") or ""): a for a in accounts if a.get("code")}
    archived: list[str] = []
    missing: list[str] = []
    system: list[str] = []
    for field in MAPPING_FIELDS:
        code = str(saved.get(field) or "").strip()
        if not code:
            continue
        acc = by_code.get(code)
        if acc is None:
            missing.append(code)
            continue
        status = str(acc.get("status") or "").upper()
        if status and status != "ACTIVE":
            archived.append(code)
            continue
        if acc.get("system_account"):
            system.append(code)

    return {
        "archived": archived,
        "missing": missing,
        "system_managed": system,
        "ok": not (archived or missing or system),
    }


@router.get("/runs/{run_id}/xero-export-status")
async def get_xero_export_status(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Most recent XeroExportLog status for a payroll run.

    Used by the run detail page to show an accurate badge for runs
    whose last export attempt failed or was voided — `xero_journal_id`
    alone doesn't tell us whether the most recent attempt succeeded.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    rows = dataflow_crud.list_records(
        "XeroExportLog",
        {"company_id": company_id, "payroll_run_id": run_id},
        cache_ttl=0,
    )
    rows.sort(key=lambda r: r.get("posted_at") or "", reverse=True)
    last = rows[0] if rows else None

    return {
        "current_journal_id": run.get("xero_journal_id") or "",
        "current_exported_at": run.get("xero_exported_at") or "",
        "last_attempt": (
            None
            if last is None
            else {
                "status": last.get("status"),
                "journal_id": last.get("journal_id"),
                "posted_at": last.get("posted_at"),
                "error_message": last.get("error_message"),
                "actor_id": last.get("actor_id"),
            }
        ),
        "attempt_count": len(rows),
    }


@router.get("/runs/{run_id}/xero-suggested-bonus")
async def get_xero_suggested_bonus(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Sum bonus + commission PayslipItems for the run.

    The export modal pre-fills its bonus_total field from this so the
    Salary/Bonus expense split mirrors what was actually paid, instead
    of relying on the user to type a number from memory (M2-T05).
    """
    from hr_advisory.services.xero_payroll_journal import compute_bonus_total

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    suggested = compute_bonus_total(run_id, company_id)
    return {"suggested_bonus_total": suggested}


@router.get("/xero/account-mapping")
async def get_xero_account_mapping(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Return saved mapping or auto-match suggestions from Xero accounts."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter
    from hr_advisory.services.xero_payroll_journal import (
        MAPPING_FIELDS,
        auto_match_accounts,
        mapping_is_complete,
    )

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    saved = _get_xero_mapping(company_id)
    if saved:
        return {
            "source": "saved",
            "mapping": {field: saved.get(field, "") for field in MAPPING_FIELDS},
            "complete": mapping_is_complete(saved),
            "last_updated_at": saved.get("last_updated_at", ""),
        }

    adapter = get_xero_adapter()
    if not adapter.is_connected(str(company_id)):
        return {
            "source": "empty",
            "mapping": {field: "" for field in MAPPING_FIELDS},
            "complete": False,
            "last_updated_at": "",
        }

    try:
        accounts = await adapter.get_chart_of_accounts(str(company_id))
    except Exception:
        logger.exception("Auto-match: failed to fetch chart of accounts")
        return {
            "source": "empty",
            "mapping": {field: "" for field in MAPPING_FIELDS},
            "complete": False,
            "last_updated_at": "",
        }

    suggestions = auto_match_accounts(accounts)
    return {
        "source": "auto_match",
        "mapping": suggestions,
        "complete": mapping_is_complete(suggestions),
        "last_updated_at": "",
    }


@router.put("/xero/account-mapping")
async def put_xero_account_mapping(
    request: Request,
    current_user: dict = Depends(require_role("owner")),
) -> dict:
    """Persist the user-confirmed Xero account mapping (upsert per company)."""
    from hr_advisory.services.xero_payroll_journal import (
        MAPPING_FIELDS,
        mapping_is_complete,
    )

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    mapping_input = body.get("mapping") or {}
    if not isinstance(mapping_input, dict):
        raise HTTPException(status_code=400, detail="mapping must be an object.")

    cleaned = {
        field: str(mapping_input.get(field, "") or "").strip()
        for field in MAPPING_FIELDS
    }

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    existing = _get_xero_mapping(company_id)
    payload = {
        **cleaned,
        "last_updated_by": actor_id,
        "last_updated_at": now,
    }
    if existing:
        dataflow_crud.update("XeroAccountMapping", existing["id"], payload)
    else:
        dataflow_crud.create(
            "XeroAccountMapping",
            {"company_id": company_id, **payload},
        )

    # Append-only change history (M3-T03). Only diff against the
    # prior saved row — first-time saves have no history rows.
    if existing:
        for field in MAPPING_FIELDS:
            previous = str(existing.get(field) or "").strip()
            new = cleaned[field]
            if previous != new:
                try:
                    dataflow_crud.create(
                        "XeroAccountMappingHistory",
                        {
                            "company_id": company_id,
                            "field_name": field,
                            "previous_code": previous,
                            "new_code": new,
                            "changed_by": actor_id,
                            "changed_at": now,
                        },
                    )
                except Exception:
                    logger.exception(
                        "Failed to write XeroAccountMappingHistory row "
                        "(field=%s, company=%s)",
                        field,
                        company_id,
                    )

    return {
        "mapping": cleaned,
        "complete": mapping_is_complete(cleaned),
        "last_updated_at": now,
    }


@router.get("/xero/mapping-history")
async def get_xero_mapping_history(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Mapping change log for the current company (M3-T03).

    Most recent first. Used by the settings page to surface "On
    2026-04-15, Jared changed Salary Expense from 477 to 478"
    entries so accountant questions can be answered without DB
    forensics.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    rows = dataflow_crud.list_records(
        "XeroAccountMappingHistory",
        {"company_id": company_id},
        cache_ttl=0,
    )
    rows.sort(key=lambda r: r.get("changed_at") or "", reverse=True)
    return {
        "history": [
            {
                "field_name": r.get("field_name"),
                "previous_code": r.get("previous_code"),
                "new_code": r.get("new_code"),
                "changed_by": r.get("changed_by"),
                "changed_at": r.get("changed_at"),
            }
            for r in rows[:100]  # cap to keep payload small
        ],
        "total": len(rows),
    }


@router.post("/runs/{run_id}/export-xero")
async def export_payroll_run_to_xero(
    run_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner")),
) -> dict:
    """Push an approved payroll run to Xero as a ManualJournal.

    Body (optional):
        bonus_total: float — portion of total_gross paid as bonus, if
            tracked separately. Defaults to 0.0 (all gross is salary).
        narration: str — override the default journal memo.
        force: bool — re-export even if xero_journal_id is already set.

    Returns:
        Dict with journal_id, status, narration, date, line_count.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"payroll_xero_export:{company_id}",
        max_requests=20,
        window_seconds=3600,
        action_name="Xero payroll export",
    )

    # Serialize concurrent exports for the same run via a Postgres
    # advisory lock. Without this, two clicks within the same
    # millisecond can race on the read-then-write of xero_force_counter
    # and produce duplicate journals at Xero — a silent correctness
    # bug not detectable post-hoc. The lock is non-blocking; the
    # second caller gets 409.
    try:
        lock_ctx = _xero_export_lock(company_id, run_id)
        lock_ctx.__enter__()
    except _XeroExportInProgress as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Lock infrastructure failure (DB unreachable, etc.) — be loud
        # and fail closed rather than silently skipping the lock.
        logger.exception("Failed to acquire Xero export lock")
        raise HTTPException(
            status_code=503,
            detail="Could not coordinate concurrent exports. Please retry.",
        ) from exc

    try:
        return await _do_xero_export(
            run_id=run_id,
            request=request,
            current_user=current_user,
            company_id=company_id,
        )
    finally:
        lock_ctx.__exit__(None, None, None)


@router.get("/xero/operations-summary")
async def xero_operations_summary(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Rolling-24h operations summary for the company.

    Used by ops dashboards / alerting (M3-T02). Surfaces:
    - export attempts and per-status counts (POSTED / FAILED / VOIDED)
    - success rate
    - most recent failure (with redacted error text)

    Alerting thresholds documented in
    ``deploy/xero-deployment-runbook.md``: refresh failure rate >5%/h,
    export 4xx rate >10%/h, any 429 hit.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    rows = dataflow_crud.list_records(
        "XeroExportLog",
        {"company_id": company_id},
        cache_ttl=0,
    )
    recent = [r for r in rows if (r.get("posted_at") or "") >= cutoff]

    by_status: dict[str, int] = {}
    last_failure: dict | None = None
    for r in recent:
        status = str(r.get("status") or "").upper() or "UNKNOWN"
        by_status[status] = by_status.get(status, 0) + 1
        if status == "FAILED":
            if (
                last_failure is None
                or (r.get("posted_at") or "")
                > (last_failure.get("posted_at") or "")
            ):
                last_failure = r

    total = sum(by_status.values())
    posted = by_status.get("POSTED", 0)
    success_rate = (posted / total) if total else 1.0

    return {
        "window_hours": 24,
        "total_attempts": total,
        "by_status": by_status,
        "success_rate": round(success_rate, 4),
        "last_failure": (
            None
            if last_failure is None
            else {
                "posted_at": last_failure.get("posted_at"),
                "run_id": last_failure.get("payroll_run_id"),
                "error_message": last_failure.get("error_message"),
            }
        ),
    }


@router.post("/runs/bulk-export-xero")
async def bulk_export_runs_to_xero(
    request: Request,
    current_user: dict = Depends(require_role("owner")),
) -> dict:
    """Export multiple payroll runs to Xero in series (M3-T04).

    Body: ``{run_ids: [int]}``. Processes runs one at a time to
    respect Xero's per-org rate limits. A failure on one run does
    not abort the batch — each result carries its own status so the
    caller can show per-run feedback.

    Use case: customer onboarding mid-year wants to backfill 6
    months of journals instead of clicking Export per run.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    actor_id = int(current_user.get("sub", 0))
    body = await request.json()
    run_ids = body.get("run_ids") or []
    if not isinstance(run_ids, list) or not run_ids:
        raise HTTPException(
            status_code=400, detail="run_ids must be a non-empty list of ids."
        )
    # Cap to avoid runaway long requests / rate-limit blowups.
    if len(run_ids) > 24:
        raise HTTPException(
            status_code=400,
            detail="Bulk export supports up to 24 runs at a time. Split the batch.",
        )

    check_rate_limit(
        f"payroll_xero_bulk_export:{company_id}",
        max_requests=4,
        window_seconds=3600,
        action_name="Xero bulk export",
    )

    results: list[dict] = []
    for raw_id in run_ids:
        try:
            run_id = int(raw_id)
        except (TypeError, ValueError):
            results.append({"run_id": raw_id, "ok": False, "error": "invalid id"})
            continue

        # Take the per-run advisory lock so concurrent bulk requests
        # don't race against each other. Skip the run with a 409
        # result if we can't acquire — caller can retry.
        try:
            lock = _xero_export_lock(company_id, run_id)
            lock.__enter__()
        except _XeroExportInProgress:
            results.append(
                {
                    "run_id": run_id,
                    "ok": False,
                    "status_code": 409,
                    "error": "Another export in progress for this run.",
                }
            )
            continue

        try:
            single_result = await _do_xero_export(
                run_id=run_id,
                request=request,
                current_user=current_user,
                company_id=company_id,
            )
            results.append(
                {
                    "run_id": run_id,
                    "ok": True,
                    "journal_id": single_result.get("journal_id", ""),
                }
            )
        except HTTPException as exc:
            results.append(
                {
                    "run_id": run_id,
                    "ok": False,
                    "status_code": exc.status_code,
                    "error": (
                        exc.detail
                        if isinstance(exc.detail, str)
                        else (exc.detail or {}).get("message", "error")
                    ),
                }
            )
        except Exception as exc:
            logger.exception(
                "Bulk export: unexpected error for run %s", run_id
            )
            results.append(
                {"run_id": run_id, "ok": False, "error": str(exc)[:200]}
            )
        finally:
            lock.__exit__(None, None, None)

    success_count = sum(1 for r in results if r.get("ok"))
    return {
        "submitted": len(run_ids),
        "succeeded": success_count,
        "failed": len(run_ids) - success_count,
        "results": results,
        "actor_id": actor_id,
    }


@router.post("/runs/{run_id}/void-xero-export")
async def void_payroll_run_xero_export(
    run_id: int,
    current_user: dict = Depends(require_role("owner")),
) -> dict:
    """Void the Xero ManualJournal previously posted for this run.

    Reverses a wrongly-exported run without producing a duplicate at
    Xero. The journal stays visible in the customer's Xero (status
    VOIDED, original date) so the audit trail is preserved — see
    ``02-data-retention.md``. Clears ``xero_journal_id`` on the
    PayrollRun so the run is treated as "not yet exported" again
    (the next export uses a fresh idempotency key, no force needed).
    """
    from hr_advisory.mcp_servers.adapters.xero import (
        XeroAPIError,
        XeroReauthRequired,
        get_xero_adapter,
    )

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    actor_id = int(current_user.get("sub", 0))
    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    journal_id = (run.get("xero_journal_id") or "").strip()
    if not journal_id:
        raise HTTPException(
            status_code=400,
            detail="This run has not been exported to Xero — nothing to void.",
        )

    adapter = get_xero_adapter()
    try:
        result = await adapter.void_journal(str(company_id), journal_id)
    except XeroReauthRequired as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Reconnect Xero to void this journal.",
                "action": "reconnect",
                "reconnect_url": "/settings/integrations?reconnect=xero",
            },
        ) from exc
    except XeroAPIError as exc:
        logger.warning(
            "Void failed for run=%s journal=%s: %s", run_id, journal_id, exc
        )
        raise HTTPException(
            status_code=502,
            detail=f"Xero rejected the void: {exc}",
        ) from exc

    now = datetime.now(timezone.utc).isoformat()
    dataflow_crud.update(
        "PayrollRun",
        run_id,
        {
            "xero_journal_id": "",
            "xero_exported_at": "",
        },
    )
    # Audit log row for the void.
    try:
        dataflow_crud.create(
            "XeroExportLog",
            {
                "company_id": company_id,
                "payroll_run_id": run_id,
                "journal_id": journal_id,
                "posted_at": now,
                "actor_id": actor_id,
                "line_count": 0,
                "payload_hash": "",
                "status": "VOIDED",
                "error_message": "",
                "bonus_total": 0.0,
                "forced_reexport": False,
            },
        )
    except Exception:
        logger.exception("Failed to write XeroExportLog VOIDED row")

    logger.info(
        "Voided Xero journal %s for run=%s, company=%s",
        journal_id,
        run_id,
        company_id,
    )
    return {
        "voided_journal_id": journal_id,
        "status": result.get("status", "VOIDED"),
        "voided_at": now,
    }


async def _do_xero_export(
    *,
    run_id: int,
    request: Request,
    current_user: dict,
    company_id: int,
) -> dict:
    """Body of the export — runs under the advisory lock."""
    from hr_advisory.mcp_servers.adapters.xero import (
        XeroAccountInvalid,
        XeroAPIError,
        XeroRateLimitError,
        XeroReauthRequired,
        XeroScopeMissing,
        assert_xero_scopes,
        get_xero_adapter,
    )
    from hr_advisory.mcp_servers.auth.token_store import get_token_manager
    from hr_advisory.services.xero_payroll_journal import build_journal_lines

    run = dataflow_crud.read("PayrollRun", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") not in ("approved", "paid"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only approved or paid payroll runs can be exported to Xero. "
                f"Current status: {run.get('status', 'unknown')}."
            ),
        )

    # Require an explicit pay_date — Xero interprets JournalDate in the
    # org's local timezone, so a UTC fallback near month-end can post
    # to the wrong accounting period. Fail fast before any Xero call.
    if not (run.get("pay_date") or "").strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Pay date is required before exporting to Xero. "
                "Set pay_date on the payroll run first — Xero posts the "
                "journal to that date in your organisation's timezone."
            ),
        )

    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    bonus_total = float(body.get("bonus_total") or 0.0)
    narration_override = body.get("narration") or None
    force = bool(body.get("force"))

    if run.get("xero_journal_id") and not force:
        raise HTTPException(
            status_code=409,
            detail=(
                "This run was already exported to Xero. "
                f"Existing journal id: {run['xero_journal_id']}. "
                "Pass force=true to re-export."
            ),
        )

    mapping = _get_xero_mapping(company_id)
    if mapping is None:
        raise HTTPException(
            status_code=409,
            detail="Xero account mapping not configured. Save a mapping first.",
        )

    adapter = get_xero_adapter()
    if not adapter.is_connected(str(company_id)):
        raise HTTPException(
            status_code=409,
            detail="Xero is not connected. Reconnect it in Settings → Integrations.",
        )

    # Scope guard (M2-T08). Tokens issued before a feature was added
    # may lack a required scope; surface a typed 403 with a reconnect
    # link rather than letting the call fail with a generic 502.
    stored = get_token_manager().get_stored_token(str(company_id), "xero")
    if stored is not None:
        try:
            assert_xero_scopes(stored.scopes, feature="post_payroll_journal")
        except XeroScopeMissing as exc:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": (
                        "Your Xero connection is missing a required permission. "
                        "Reconnect Xero to grant the additional scope."
                    ),
                    "action": "reconnect_for_scope",
                    "missing_scopes": exc.missing_scopes,
                    "reconnect_url": "/settings/integrations?reconnect=xero",
                },
            ) from exc

    try:
        journal_data = build_journal_lines(
            payroll_run=run,
            mapping=mapping,
            bonus_total=bonus_total,
            narration=narration_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Hash the payload before posting — included in the audit log so we
    # can later prove exactly what was sent without storing line text.
    import hashlib
    import json as _json

    payload_hash = hashlib.sha256(
        _json.dumps(journal_data, sort_keys=True).encode()
    ).hexdigest()
    actor_id = int(current_user.get("sub", 0))

    def _write_audit(
        *,
        journal_id: str,
        status: str,
        error_message: str = "",
    ) -> None:
        """Append an immutable XeroExportLog row. Best-effort — never
        raises into the request path."""
        try:
            dataflow_crud.create(
                "XeroExportLog",
                {
                    "company_id": company_id,
                    "payroll_run_id": run_id,
                    "journal_id": journal_id,
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                    "actor_id": actor_id,
                    "line_count": len(journal_data["lines"]),
                    "payload_hash": payload_hash,
                    "status": status,
                    "error_message": error_message[:500],
                    "bonus_total": bonus_total,
                    "forced_reexport": force,
                },
            )
        except Exception:
            logger.exception(
                "Failed to write XeroExportLog (run=%s)", run_id
            )

    # Stable Idempotency-Key — same key on retry returns the original
    # response from Xero (24h dedupe window). Increments only on
    # force=true so each forced re-export is genuinely new.
    next_force_counter = (
        int(run.get("xero_force_counter") or 0) + (1 if force else 0)
    )
    idempotency_key = (
        f"xero-payroll:{company_id}:{run_id}:{next_force_counter}"
    )

    # If this is a forced re-export of a previously-posted run, void the
    # prior Xero journal first. Otherwise the customer's books end up
    # with two posted journals for the same payroll period — a real
    # reconciliation problem. If void fails, abort the export so we
    # never leave duplicates behind.
    prior_journal_id = run.get("xero_journal_id") or ""
    if force and prior_journal_id:
        try:
            await adapter.void_journal(str(company_id), prior_journal_id)
        except XeroAPIError as exc:
            logger.warning(
                "Force-re-export aborted — could not void prior journal %s: %s",
                prior_journal_id,
                exc,
            )
            _write_audit(
                journal_id=prior_journal_id,
                status="FAILED",
                error_message=f"void_failed: {exc}",
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Could not void the prior Xero journal "
                    f"({prior_journal_id}). Re-export aborted to avoid "
                    f"duplicate journals: {exc}"
                ),
            ) from exc
        else:
            _write_audit(
                journal_id=prior_journal_id, status="VOIDED"
            )

    try:
        result = await adapter.post_payroll_journal(
            str(company_id),
            journal_data,
            idempotency_key=idempotency_key,
        )
    except XeroReauthRequired as exc:
        # Refresh-token cliff or revocation at source. Adapter has
        # already hard-disconnected the local row. Surface a typed
        # 401 with reconnect_url so the modal can render a clear
        # "Reconnect Xero" CTA (M1-T03).
        _write_audit(
            journal_id="",
            status="FAILED",
            error_message=f"reauth_required: {exc.reason}",
        )
        raise HTTPException(
            status_code=401,
            detail={
                "message": (
                    "Your Xero connection expired or was revoked. "
                    "Reconnect to continue exporting."
                ),
                "action": "reconnect",
                "reconnect_url": "/settings/integrations?reconnect=xero",
            },
        ) from exc
    except XeroAccountInvalid as exc:
        # A mapped account is archived or no longer exists. The
        # adapter has already invalidated the CoA cache. Surface 409
        # with the offending codes so the modal can deep-link the
        # user to fix their mapping.
        _write_audit(
            journal_id="",
            status="FAILED",
            error_message=f"account_invalid: {','.join(exc.offending_codes)}",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Xero rejected one or more account codes. They may "
                    "have been archived or renamed since your last "
                    "export. Update your mapping and retry."
                ),
                "offending_codes": exc.offending_codes,
                "mapping_url": "/settings/integrations/xero",
            },
        ) from exc
    except XeroRateLimitError as exc:
        _write_audit(
            journal_id="", status="FAILED", error_message=f"rate_limit: {exc}"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Xero rate limit hit. Retry after {exc.retry_after}s.",
        ) from exc
    except XeroAPIError as exc:
        logger.warning(
            "Xero rejected payroll journal for run %s: %s", run_id, exc
        )
        _write_audit(
            journal_id="", status="FAILED", error_message=str(exc)
        )
        raise HTTPException(
            status_code=502,
            detail=f"Xero rejected the journal: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error posting Xero journal")
        _write_audit(
            journal_id="", status="FAILED", error_message=str(exc)
        )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to post journal to Xero: {exc}",
        ) from exc

    journal_id = result.get("journal_id", "")
    now = datetime.now(timezone.utc).isoformat()
    dataflow_crud.update(
        "PayrollRun",
        run_id,
        {
            "xero_journal_id": journal_id,
            "xero_exported_at": now,
            "xero_force_counter": next_force_counter,
        },
    )
    _write_audit(journal_id=journal_id, status="POSTED")
    # Structured log for ops dashboards / alerting (M3-T01).
    from hr_advisory.mcp_servers.adapters.xero import xero_log_event

    xero_log_event(
        "export_run",
        outcome="success",
        company_id=company_id,
        run_id=run_id,
        journal_id=journal_id,
        line_count=len(journal_data["lines"]),
        forced=force,
    )

    logger.info(
        "Exported payroll run %s to Xero as journal %s (company=%s)",
        run_id,
        journal_id,
        company_id,
    )

    return {
        "journal_id": journal_id,
        "status": result.get("status", ""),
        "narration": result.get("narration", ""),
        "date": result.get("date", ""),
        "line_count": result.get("line_count", 0),
        "exported_at": now,
        "lines_preview": journal_data["lines"],
    }
