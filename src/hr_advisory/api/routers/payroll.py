"""Payroll management endpoints.

Handles payroll run lifecycle: calculate, review, approve, mark paid.
Also handles payslip access, CPF YTD tracking, and payroll reports.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
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

    records = _dataflow_list(
        "CpfYtdRecordListNode",
        {
            "employee_id": employee_id,
            "year": year,
        },
    )

    # Verify employee belongs to company
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

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
