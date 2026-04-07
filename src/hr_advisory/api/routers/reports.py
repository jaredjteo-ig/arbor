"""Report generation endpoints.

Provides read-only report endpoints for payroll, leave, claims,
attendance, employees, and project costing data.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from hr_advisory.api.middleware.auth_middleware import require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------
# DataFlow helpers
# --------------------------------------------------------------------------

from hr_advisory.services import dataflow_crud


# --------------------------------------------------------------------------
# Payroll reports
# --------------------------------------------------------------------------


@router.get("/turnover")
async def turnover_report(
    start_date: str = Query(None),
    end_date: str = Query(None),
    department: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Employee turnover report.

    Returns monthly hires, terminations, headcount, and turnover rate.
    Defaults to the last 12 months if no date range is provided.
    """
    from datetime import date as _date, timedelta

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    today = _date.today()
    if not start_date:
        start_date = (today.replace(day=1) - timedelta(days=365)).replace(day=1).isoformat()
    if not end_date:
        end_date = today.isoformat()

    # Fetch all employees (active and inactive) for the company
    filters: dict = {"company_id": company_id}
    if department:
        filters["department"] = department

    all_active = dataflow_crud.list_records("Employee", {**filters, "is_active": True})
    all_inactive = dataflow_crud.list_records("Employee", {**filters, "is_active": False})
    all_employees = all_active + all_inactive

    # Build month buckets between start_date and end_date
    from datetime import date as _d

    start = _d.fromisoformat(start_date).replace(day=1)
    end = _d.fromisoformat(end_date)
    months: list[str] = []
    cursor = start
    while cursor <= end:
        months.append(cursor.strftime("%Y-%m"))
        # Advance to next month
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    # Count hires and terminations per month
    hires_by_month: dict[str, int] = {m: 0 for m in months}
    terms_by_month: dict[str, int] = {m: 0 for m in months}

    for emp in all_employees:
        emp_start = emp.get("start_date", "")
        emp_end = emp.get("end_date", "")
        if emp_start and len(emp_start) >= 7:
            month_key = emp_start[:7]
            if month_key in hires_by_month:
                hires_by_month[month_key] += 1
        if emp_end and len(emp_end) >= 7:
            month_key = emp_end[:7]
            if month_key in terms_by_month:
                terms_by_month[month_key] += 1

    # Build rows with running headcount
    total_active = len(all_active)
    # Work backwards to find headcount at start: current active + terms after start - hires after start
    cumulative_terms_after = sum(terms_by_month.get(m, 0) for m in months)
    cumulative_hires_after = sum(hires_by_month.get(m, 0) for m in months)
    headcount = total_active + cumulative_terms_after - cumulative_hires_after

    rows = []
    for m in months:
        hires = hires_by_month.get(m, 0)
        terms = terms_by_month.get(m, 0)
        headcount = headcount + hires - terms
        avg_headcount = max(headcount, 1)
        turnover_rate = round((terms / avg_headcount) * 100, 2)
        rows.append({
            "month": m,
            "hires": hires,
            "terminations": terms,
            "headcount": headcount,
            "turnover_rate": turnover_rate,
        })

    from datetime import datetime as _dt, timezone as _tz

    return {
        "rows": rows,
        "generated_at": _dt.now(_tz.utc).isoformat(),
    }


@router.get("/payroll")
async def payroll_summary_report(
    period_start: str = Query(None),
    period_end: str = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Payroll summary report for a given period.

    If period_start / period_end are omitted, defaults to the current calendar month.
    """
    from datetime import date as _date

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Default to current month if dates not provided
    if not period_start:
        today = _date.today()
        period_start = today.replace(day=1).isoformat()
    if not period_end:
        today = _date.today()
        period_end = today.isoformat()

    runs = dataflow_crud.list_records(
        "PayrollRun",
        {"company_id": company_id, "period_start": period_start, "period_end": period_end},
    )

    total_gross = 0.0
    total_net = 0.0
    total_employer_cpf = 0.0
    total_employee_cpf = 0.0
    run_summaries = []

    for run in runs:
        run_id = run.get("id")
        payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run_id})
        run_gross = sum(p.get("gross_pay", 0.0) for p in payslips)
        run_net = sum(p.get("net_pay", 0.0) for p in payslips)
        run_er_cpf = sum(p.get("employer_cpf", 0.0) for p in payslips)
        run_ee_cpf = sum(p.get("employee_cpf", 0.0) for p in payslips)

        total_gross += run_gross
        total_net += run_net
        total_employer_cpf += run_er_cpf
        total_employee_cpf += run_ee_cpf

        run_summaries.append({
            "run_id": run_id,
            "status": run.get("status"),
            "employee_count": run.get("employee_count", 0),
            "gross_pay": round(run_gross, 2),
            "net_pay": round(run_net, 2),
            "employer_cpf": round(run_er_cpf, 2),
            "employee_cpf": round(run_ee_cpf, 2),
        })

    return {
        "period_start": period_start,
        "period_end": period_end,
        "runs": run_summaries,
        "totals": {
            "gross_pay": round(total_gross, 2),
            "net_pay": round(total_net, 2),
            "employer_cpf": round(total_employer_cpf, 2),
            "employee_cpf": round(total_employee_cpf, 2),
        },
    }


@router.get("/payroll/cpf")
async def cpf_breakdown_report(
    period_start: str = Query(...),
    period_end: str = Query(...),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """CPF contribution breakdown by employee."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    runs = dataflow_crud.list_records(
        "PayrollRun",
        {"company_id": company_id, "period_start": period_start, "period_end": period_end},
    )

    employee_cpf: dict[int, dict] = {}
    for run in runs:
        payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run.get("id")})
        for ps in payslips:
            emp_id = ps.get("employee_id", 0)
            if emp_id not in employee_cpf:
                employee_cpf[emp_id] = {
                    "employee_id": emp_id,
                    "employee_name": ps.get("employee_name", ""),
                    "employer_cpf": 0.0,
                    "employee_cpf": 0.0,
                    "total_cpf": 0.0,
                }
            employee_cpf[emp_id]["employer_cpf"] += ps.get("employer_cpf", 0.0)
            employee_cpf[emp_id]["employee_cpf"] += ps.get("employee_cpf", 0.0)
            employee_cpf[emp_id]["total_cpf"] += (
                ps.get("employer_cpf", 0.0) + ps.get("employee_cpf", 0.0)
            )

    breakdown = list(employee_cpf.values())
    for entry in breakdown:
        entry["employer_cpf"] = round(entry["employer_cpf"], 2)
        entry["employee_cpf"] = round(entry["employee_cpf"], 2)
        entry["total_cpf"] = round(entry["total_cpf"], 2)

    return {"period_start": period_start, "period_end": period_end, "breakdown": breakdown}


@router.get("/payroll/banks")
async def payroll_by_bank_report(
    period_start: str = Query(...),
    period_end: str = Query(...),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Payroll amounts grouped by employee bank."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    runs = dataflow_crud.list_records(
        "PayrollRun",
        {"company_id": company_id, "period_start": period_start, "period_end": period_end},
    )

    bank_totals: dict[str, dict] = {}
    for run in runs:
        payslips = dataflow_crud.list_records("Payslip", {"payroll_run_id": run.get("id")})
        for ps in payslips:
            emp_id = ps.get("employee_id", 0)
            # Look up employee bank info
            employees = dataflow_crud.list_records(
                "Employee", {"id": emp_id}, limit=1
            )
            bank_name = "Unknown"
            if employees:
                bank_name = employees[0].get("bank_name", "Unknown") or "Unknown"

            if bank_name not in bank_totals:
                bank_totals[bank_name] = {"bank": bank_name, "total": 0.0, "count": 0}
            bank_totals[bank_name]["total"] += ps.get("net_pay", 0.0)
            bank_totals[bank_name]["count"] += 1

    banks = list(bank_totals.values())
    for b in banks:
        b["total"] = round(b["total"], 2)

    return {"period_start": period_start, "period_end": period_end, "banks": banks}


@router.get("/payroll/ytd")
async def salary_ytd_report(
    year: int = Query(...),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Year-to-date salary summary by employee."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    ytd_records = dataflow_crud.list_records(
        "CpfYtd",
        {"company_id": company_id, "year": year},
    )
    return {"year": year, "records": ytd_records, "count": len(ytd_records)}


@router.get("/payroll/variance")
async def payroll_variance_report(
    period1_start: str = Query(...),
    period1_end: str = Query(...),
    period2_start: str = Query(...),
    period2_end: str = Query(...),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Month-over-month payroll variance between two periods."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    def _period_total(p_start: str, p_end: str) -> dict:
        runs = dataflow_crud.list_records(
            "PayrollRun",
            {"company_id": company_id, "period_start": p_start, "period_end": p_end},
        )
        gross = 0.0
        net = 0.0
        for run in runs:
            payslips = dataflow_crud.list_records(
                "Payslip", {"payroll_run_id": run.get("id")}
            )
            gross += sum(p.get("gross_pay", 0.0) for p in payslips)
            net += sum(p.get("net_pay", 0.0) for p in payslips)
        return {"gross_pay": round(gross, 2), "net_pay": round(net, 2)}

    period1 = _period_total(period1_start, period1_end)
    period2 = _period_total(period2_start, period2_end)

    return {
        "period1": {"start": period1_start, "end": period1_end, **period1},
        "period2": {"start": period2_start, "end": period2_end, **period2},
        "variance": {
            "gross_pay": round(period2["gross_pay"] - period1["gross_pay"], 2),
            "net_pay": round(period2["net_pay"] - period1["net_pay"], 2),
        },
    }


# --------------------------------------------------------------------------
# Leave reports
# --------------------------------------------------------------------------


@router.get("/leave")
async def leave_applications_report(
    year: int = Query(None),
    status: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Leave applications report."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status

    applications = dataflow_crud.list_records("LeaveApplication", filters)

    # Client-side year filtering if provided
    if year:
        year_str = str(year)
        applications = [
            a for a in applications
            if a.get("start_date", "").startswith(year_str)
        ]

    return {"applications": applications, "count": len(applications)}


@router.get("/leave/balances")
async def leave_balance_report(
    year: int = Query(...),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Leave balance report for all employees."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    balances = dataflow_crud.list_records(
        "LeaveBalance",
        {"company_id": company_id, "year": year},
    )
    return {"year": year, "balances": balances, "count": len(balances)}


# --------------------------------------------------------------------------
# Claims report
# --------------------------------------------------------------------------


@router.get("/claims")
async def claims_report(
    year: int = Query(None),
    status: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Claims report."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status

    claims = dataflow_crud.list_records("Claim", filters)

    if year:
        year_str = str(year)
        claims = [
            c for c in claims
            if c.get("created_at", "").startswith(year_str)
            or c.get("claim_date", "").startswith(year_str)
        ]

    total_amount = sum(c.get("amount", 0.0) for c in claims)
    return {
        "claims": claims,
        "count": len(claims),
        "total_amount": round(total_amount, 2),
    }


# --------------------------------------------------------------------------
# Attendance report
# --------------------------------------------------------------------------


@router.get("/attendance")
async def attendance_report(
    date_from: str = Query(...),
    date_to: str = Query(...),
    employee_id: int | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Attendance hours report."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if employee_id:
        filters["employee_id"] = employee_id

    records = dataflow_crud.list_records("AttendanceRecord", filters)

    # Client-side date filtering
    records = [
        r for r in records
        if date_from <= r.get("date", "") <= date_to
    ]

    total_hours = sum(r.get("hours_worked", 0.0) for r in records)
    total_ot = sum(r.get("overtime_hours", 0.0) for r in records)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "records": records,
        "count": len(records),
        "total_hours": round(total_hours, 2),
        "total_overtime": round(total_ot, 2),
    }


# --------------------------------------------------------------------------
# Employee details report
# --------------------------------------------------------------------------


@router.get("/employees")
async def employee_details_report(
    is_active: bool = Query(True),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Employee details report."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    employees = dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "is_active": is_active},
    )
    return {"employees": employees, "count": len(employees)}


# --------------------------------------------------------------------------
# Project costing report
# --------------------------------------------------------------------------


@router.get("/projects")
async def project_costing_report(
    project_id: int | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Project costing summary report."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if project_id:
        filters["id"] = project_id

    projects = dataflow_crud.list_records("Project", filters)

    summaries = []
    for proj in projects:
        pid = proj.get("id")
        entries = dataflow_crud.list_records("TimesheetEntry", {"project_id": pid})
        overheads = dataflow_crud.list_records("ProjectOverhead", {"project_id": pid})
        assignments = dataflow_crud.list_records(
            "ProjectAssignment", {"project_id": pid}
        )

        total_hours = sum(e.get("hours", 0.0) for e in entries)
        overhead_total = sum(o.get("amount", 0.0) for o in overheads)

        summaries.append({
            "project_id": pid,
            "project_name": proj.get("name", ""),
            "status": proj.get("status", ""),
            "budget": proj.get("budget", 0.0),
            "total_hours": round(total_hours, 2),
            "overhead_total": round(overhead_total, 2),
            "employee_count": len(assignments),
        })

    return {"projects": summaries, "count": len(summaries)}
