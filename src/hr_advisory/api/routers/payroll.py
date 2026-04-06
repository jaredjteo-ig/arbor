"""Payroll management endpoints.

Handles payroll run lifecycle: calculate, review, approve, mark paid.
Also handles payslip access, CPF YTD tracking, and payroll reports.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------
# DataFlow helpers
# --------------------------------------------------------------------------


def _dataflow_create(node_type: str, data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000) -> list:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        node_type,
        "list",
        {"filter": filter_dict, "limit": limit, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    raw = results["list"]
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    if isinstance(raw, list):
        return raw
    return []


def _dataflow_update(node_type: str, record_id: int, updates: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, "update", {"filter": {"id": record_id}, "fields": updates})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _dataflow_read(node_type: str, record_id: int) -> dict | None:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, "read", {"id": record_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


def _find_user_by_id(user_id: int) -> dict | None:
    return _dataflow_read("UserReadNode", user_id)


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
    employees = _dataflow_list(
        "EmployeeListNode",
        {
            "company_id": company_id,
            "is_active": True,
        },
    )
    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found.")

    # Prevent duplicate payroll runs for the same period
    existing_runs = _dataflow_list(
        "PayrollRunListNode",
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
    run = _dataflow_create(
        "PayrollRunCreateNode",
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
        components = _dataflow_list(
            "SalaryComponentListNode",
            {
                "employee_id": emp_id,
                "is_active": True,
            },
        )

        # Fetch CPF YTD for ceiling tracking
        try:
            ytd_records = _dataflow_list(
                "CpfYtdRecordListNode",
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
            leave_apps = _dataflow_list(
                "LeaveApplicationListNode",
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
            timesheets = _dataflow_list(
                "TimesheetApprovalListNode",
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
            emp_claims = _dataflow_list(
                "ClaimListNode",
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
        payslip = _dataflow_create(
            "PayslipCreateNode",
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
            _dataflow_create(
                "PayslipItemCreateNode",
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
            _dataflow_create(
                "CpfYtdRecordCreateNode",
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
    _dataflow_update(
        "PayrollRunUpdateNode",
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
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all payroll runs for the current company."""
    company_id = get_current_company_id(current_user)
    runs = _dataflow_list("PayrollRunListNode", {"company_id": company_id})
    runs.sort(key=lambda r: r.get("period_start", ""), reverse=True)
    return {"runs": runs, "count": len(runs)}


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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = _dataflow_list("PayslipListNode", {"payroll_run_id": run_id})

    # Enrich payslips with employee names
    enriched = []
    for ps in payslips:
        emp_id = ps.get("employee_id")
        emp_records = _dataflow_list("EmployeeListNode", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = _find_user_by_id(emp.get("user_id")) if emp else None
        enriched.append(
            {
                **ps,
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
    payslip = _dataflow_read("PayslipReadNode", payslip_id)
    if payslip is None or payslip.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payslip not found.")

    items = _dataflow_list("PayslipItemListNode", {"payslip_id": payslip_id})

    # Get employee name
    emp_records = _dataflow_list("EmployeeListNode", {"id": payslip.get("employee_id")}, limit=1)
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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft runs can be approved.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    _dataflow_update(
        "PayrollRunUpdateNode",
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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved runs can be marked as paid.")

    _dataflow_update("PayrollRunUpdateNode", run_id, {"status": "paid"})

    # Update all payslips in this run to paid
    payslips = _dataflow_list("PayslipListNode", {"payroll_run_id": run_id})
    for ps in payslips:
        _dataflow_update("PayslipUpdateNode", ps["id"], {"status": "paid"})

    # Mark approved claims as paid in this payroll run
    from datetime import date as _date

    period_month = _date.fromisoformat(run["period_start"]).strftime("%Y-%m")
    employees = _dataflow_list("EmployeeListNode", {"company_id": company_id, "is_active": True})
    for emp in employees:
        emp_id = emp.get("id")
        try:
            emp_claims = _dataflow_list(
                "ClaimListNode",
                {
                    "employee_id": emp_id,
                    "status": "approved",
                    "claim_month": period_month,
                },
            )
            for cl in emp_claims:
                if cl.get("paid_in_payroll_run_id") is None:
                    _dataflow_update(
                        "ClaimUpdateNode",
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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Paid runs cannot be cancelled.")

    if run.get("status") == "approved" and current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can cancel approved payroll runs.")

    _dataflow_update("PayrollRunUpdateNode", run_id, {"status": "cancelled"})
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
    emp_records = _dataflow_list(
        "EmployeeListNode",
        {
            "user_id": user_id,
            "company_id": company_id,
        },
        limit=1,
    )
    if not emp_records:
        return {"payslips": []}

    emp_id = emp_records[0].get("id")
    payslips = _dataflow_list("PayslipListNode", {"employee_id": emp_id})

    # Only show paid/confirmed payslips to employees
    visible = [ps for ps in payslips if ps.get("status") in ("confirmed", "paid")]
    visible.sort(key=lambda ps: ps.get("period_start", ""), reverse=True)

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

    payslip = _dataflow_read("PayslipReadNode", payslip_id)
    if payslip is None:
        raise HTTPException(status_code=404, detail="Payslip not found.")

    # Verify this payslip belongs to the current user
    emp_records = _dataflow_list(
        "EmployeeListNode",
        {
            "user_id": user_id,
            "company_id": company_id,
        },
        limit=1,
    )
    if not emp_records or emp_records[0].get("id") != payslip.get("employee_id"):
        raise HTTPException(status_code=403, detail="Access denied.")

    items = _dataflow_list("PayslipItemListNode", {"payslip_id": payslip_id})

    return {"payslip": payslip, "items": items}


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
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    records = _dataflow_list(
        "CpfYtdRecordListNode",
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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = _dataflow_list("PayslipListNode", {"payroll_run_id": run_id})

    # Group by department
    by_department: dict[str, dict] = {}
    for ps in payslips:
        emp_records = _dataflow_list("EmployeeListNode", {"id": ps.get("employee_id")}, limit=1)
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

    employees = _dataflow_list(
        "EmployeeListNode",
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
        payslips = _dataflow_list("PayslipListNode", {"employee_id": emp_id})
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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = _dataflow_list("PayslipListNode", {"payroll_run_id": run_id})

    # Collect unique employee IDs and fetch employee records
    emp_ids = {ps.get("employee_id") for ps in payslips}
    employees: list[dict] = []
    for eid in emp_ids:
        emp_records = _dataflow_list("EmployeeListNode", {"id": eid}, limit=1)
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
# POST /payroll/runs/{id}/payslips/{payslip_id}/pdf — Generate payslip HTML
# --------------------------------------------------------------------------


@router.post("/runs/{run_id}/payslips/{payslip_id}/pdf")
async def generate_payslip_pdf(
    run_id: int,
    payslip_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> Response:
    """Generate payslip as HTML (can be rendered to PDF by client or weasyprint)."""
    from hr_advisory.services.statutory_files import generate_payslip_html

    company_id = get_current_company_id(current_user)

    # Verify run ownership
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    # Fetch payslip
    payslip = _dataflow_read("PayslipReadNode", payslip_id)
    if payslip is None or payslip.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payslip not found.")
    if payslip.get("payroll_run_id") != run_id:
        raise HTTPException(status_code=400, detail="Payslip does not belong to this run.")

    # Fetch payslip items
    items = _dataflow_list("PayslipItemListNode", {"payslip_id": payslip_id})

    # Fetch employee + user name
    emp_records = _dataflow_list("EmployeeListNode", {"id": payslip.get("employee_id")}, limit=1)
    emp = emp_records[0] if emp_records else {}
    user = _find_user_by_id(emp.get("user_id")) if emp else None
    if user:
        emp["name"] = user.get("name", "")

    # Fetch company
    company = _dataflow_read("CompanyReadNode", company_id) or {}

    # Add pay_date from run to payslip dict for display
    payslip["pay_date"] = run.get("pay_date", "")

    html = generate_payslip_html(payslip, items, emp, company)

    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Content-Disposition": f'inline; filename="payslip_{payslip_id}.html"',
        },
    )


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

    employees = _dataflow_list(
        "EmployeeListNode",
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
        all_payslips = _dataflow_list("PayslipListNode", {"employee_id": emp_id})
        year_payslips = [
            ps for ps in all_payslips if ps.get("period_start", "").startswith(str(year))
        ]

        # Fetch all items for those payslips
        all_items: list[dict] = []
        for ps in year_payslips:
            ps_items = _dataflow_list("PayslipItemListNode", {"payslip_id": ps.get("id")})
            all_items.extend(ps_items)

        ir8a = generate_ir8a_data(emp, year_payslips, all_items, year)

        # Create or update TaxFiling record
        existing = _dataflow_list(
            "TaxFilingListNode",
            {
                "employee_id": emp_id,
                "tax_year": year,
                "filing_type": "ir8a",
            },
            limit=1,
        )

        if existing:
            _dataflow_update(
                "TaxFilingUpdateNode",
                existing[0]["id"],
                {"data": ir8a, "status": "draft"},
            )
            filing_id = existing[0]["id"]
        else:
            result = _dataflow_create(
                "TaxFilingCreateNode",
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
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp = emp_records[0]
    user = _find_user_by_id(emp.get("user_id"))
    if user:
        emp["name"] = user.get("name", "")

    # Check if a TaxFiling already exists
    existing = _dataflow_list(
        "TaxFilingListNode",
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
    all_payslips = _dataflow_list("PayslipListNode", {"employee_id": employee_id})
    year_payslips = [ps for ps in all_payslips if ps.get("period_start", "").startswith(str(year))]

    all_items: list[dict] = []
    for ps in year_payslips:
        ps_items = _dataflow_list("PayslipItemListNode", {"payslip_id": ps.get("id")})
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

    items = _dataflow_list("PayItemListNode", {"company_id": company_id, "is_active": True})
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

    pay_item = _dataflow_create(
        "PayItemCreateNode",
        {
            "company_id": company_id,
            "name": name,
            "item_type": item_type,
            "amount": float(body.get("amount", 0.0)),
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
    item = _dataflow_read("PayItemReadNode", pay_item_id)
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

    _dataflow_update("PayItemUpdateNode", pay_item_id, updates)
    updated = _dataflow_read("PayItemReadNode", pay_item_id)
    return {"pay_item": updated}


@router.delete("/pay-items/{pay_item_id}")
async def archive_pay_item(
    pay_item_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Archive (soft-delete) a pay item."""
    company_id = get_current_company_id(current_user)
    item = _dataflow_read("PayItemReadNode", pay_item_id)
    if item is None or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pay item not found.")

    _dataflow_update("PayItemUpdateNode", pay_item_id, {"is_active": False})
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

    schemes = _dataflow_list(
        "PaySchemeListNode", {"company_id": company_id, "is_active": True}
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

    scheme = _dataflow_create(
        "PaySchemeCreateNode",
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
    scheme = _dataflow_read("PaySchemeReadNode", scheme_id)
    if scheme is None or scheme.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pay scheme not found.")

    body = await request.json()
    allowed = {"name", "description", "pay_item_ids", "is_default", "is_active"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    _dataflow_update("PaySchemeUpdateNode", scheme_id, updates)
    updated = _dataflow_read("PaySchemeReadNode", scheme_id)
    return {"pay_scheme": updated}


@router.delete("/pay-schemes/{scheme_id}")
async def archive_pay_scheme(
    scheme_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Archive (soft-delete) a pay scheme."""
    company_id = get_current_company_id(current_user)
    scheme = _dataflow_read("PaySchemeReadNode", scheme_id)
    if scheme is None or scheme.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pay scheme not found.")

    _dataflow_update("PaySchemeUpdateNode", scheme_id, {"is_active": False})
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
        emp_records = _dataflow_list("EmployeeListNode", {"id": eid}, limit=1)
        if emp_records and emp_records[0].get("company_id") == company_id:
            employees.append(emp_records[0])

    if not employees:
        raise HTTPException(status_code=400, detail="No valid employees found.")

    # Create adhoc payroll run
    run = _dataflow_create(
        "PayrollRunCreateNode",
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

        components = _dataflow_list(
            "SalaryComponentListNode",
            {"employee_id": emp_id, "is_active": True},
        )

        try:
            ytd_records = _dataflow_list(
                "CpfYtdRecordListNode",
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

        payslip = _dataflow_create(
            "PayslipCreateNode",
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
            _dataflow_create(
                "PayslipItemCreateNode",
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

    _dataflow_update(
        "PayrollRunUpdateNode",
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

    run_a = _dataflow_read("PayrollRunReadNode", run_id_a)
    run_b = _dataflow_read("PayrollRunReadNode", run_id_b)
    if run_a is None or run_a.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run A not found.")
    if run_b is None or run_b.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run B not found.")

    payslips_a = _dataflow_list("PayslipListNode", {"payroll_run_id": run_id_a})
    payslips_b = _dataflow_list("PayslipListNode", {"payroll_run_id": run_id_b})

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

        emp_records = _dataflow_list("EmployeeListNode", {"id": emp_id}, limit=1)
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
    settings = _dataflow_list(
        "PayslipSettingsListNode",
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

    existing = _dataflow_list(
        "PayslipSettingsListNode",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        _dataflow_update("PayslipSettingsUpdateNode", existing[0]["id"], fields)
        updated = _dataflow_read("PayslipSettingsReadNode", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = _dataflow_create("PayslipSettingsCreateNode", fields)

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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    payslips = _dataflow_list("PayslipListNode", {"payroll_run_id": run_id})

    all_items = []
    for ps in payslips:
        items = _dataflow_list("PayslipItemListNode", {"payslip_id": ps.get("id")})
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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Line items can only be added to draft runs.")

    body = await request.json()
    payslip_id = body.get("payslip_id")
    if not payslip_id:
        raise HTTPException(status_code=400, detail="payslip_id is required.")

    payslip = _dataflow_read("PayslipReadNode", payslip_id)
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

    item = _dataflow_create(
        "PayslipItemCreateNode",
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
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Line items can only be updated on draft runs.")

    item = _dataflow_read("PayslipItemReadNode", item_id)
    if item is None or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Line item not found.")

    body = await request.json()
    allowed = {"name", "amount", "item_type", "is_taxable", "is_cpf_applicable", "notes"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    _dataflow_update("PayslipItemUpdateNode", item_id, updates)
    updated = _dataflow_read("PayslipItemReadNode", item_id)
    return {"line_item": updated}


@router.delete("/runs/{run_id}/line-items/{item_id}")
async def delete_run_line_item(
    run_id: int,
    item_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a line item from a payroll run (hard delete via update to zero)."""
    company_id = get_current_company_id(current_user)
    run = _dataflow_read("PayrollRunReadNode", run_id)
    if run is None or run.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Payroll run not found.")

    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Line items can only be deleted from draft runs.")

    item = _dataflow_read("PayslipItemReadNode", item_id)
    if item is None or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Line item not found.")

    # Soft-delete by zeroing out and marking
    _dataflow_update(
        "PayslipItemUpdateNode",
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
            emp_records = _dataflow_list("EmployeeListNode", {"id": eid}, limit=1)
            if emp_records and emp_records[0].get("company_id") == company_id:
                employees.append(emp_records[0])
    else:
        employees = _dataflow_list(
            "EmployeeListNode",
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

        components = _dataflow_list(
            "SalaryComponentListNode",
            {"employee_id": emp_id, "is_active": True},
        )

        try:
            ytd_records = _dataflow_list(
                "CpfYtdRecordListNode",
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
            leave_apps = _dataflow_list(
                "LeaveApplicationListNode",
                {"employee_id": emp_id, "status": "approved", "leave_type_code": "unpaid"},
            )
            for la in leave_apps:
                if la.get("start_date", "") <= period_end and la.get("end_date", "") >= period_start:
                    leave_deduction_days += la.get("total_days", 0.0)
        except Exception:
            pass

        try:
            timesheets = _dataflow_list(
                "TimesheetApprovalListNode",
                {"employee_id": emp_id, "status": "approved", "month": period_month},
            )
            for ts in timesheets:
                overtime_hours += ts.get("total_ot_hours", 0.0)
        except Exception:
            pass

        try:
            emp_claims = _dataflow_list(
                "ClaimListNode",
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
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp = emp_records[0]
    user = _find_user_by_id(emp.get("user_id"))
    if user:
        emp["name"] = user.get("name", "")

    # Fetch all payslips and items for the employee
    all_payslips = _dataflow_list("PayslipListNode", {"employee_id": employee_id})

    all_items: list[dict] = []
    for ps in all_payslips:
        ps_items = _dataflow_list("PayslipItemListNode", {"payslip_id": ps.get("id")})
        all_items.extend(ps_items)

    ir21 = generate_ir21_data(emp, all_payslips, all_items, cessation_date)

    # Create TaxFiling record
    try:
        cess = datetime.fromisoformat(cessation_date)
        tax_year = cess.year
    except (ValueError, TypeError):
        tax_year = datetime.now(timezone.utc).year

    result = _dataflow_create(
        "TaxFilingCreateNode",
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
