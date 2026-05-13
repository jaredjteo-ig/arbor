"""Attendance and time-tracking management endpoints.

Handles clock-in/out, daily attendance records, monthly summaries,
attendance settings, and timesheet approval workflows.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud, manager_scope

logger = logging.getLogger(__name__)

router = APIRouter()

# B19: shared helpers consolidated in _helpers.py.
from hr_advisory.api.routers._helpers import (  # noqa: E402
    MAX_TEXT_LENGTH,
    MAX_NAME_LENGTH,
    _validate_text_length,
)


from hr_advisory.api.routers._helpers import _find_employee_for_user  # noqa: E402


def _get_attendance_settings(company_id: int) -> dict:
    """Fetch attendance settings for a company, returning defaults if none exist."""
    settings = dataflow_crud.list_records(
        "AttendanceSettings",
        {"company_id": company_id},
        limit=1,
    )
    if settings:
        return settings[0]
    # Return defaults
    return {
        "work_start_time": "09:00",
        "work_end_time": "18:00",
        "grace_period_minutes": 15,
        "overtime_threshold_minutes": 30,
        "require_gps": False,
        "require_photo": False,
        "allowed_locations": None,
    }


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse an HH:MM time string into (hours, minutes)."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def _determine_status(clock_in_time: str, settings: dict) -> str:
    """Determine attendance status based on clock-in time vs settings.

    The clock-in timestamp is recorded in UTC; the configured work-start
    time is the company's local time (Singapore SGT, UTC+8 by default).
    Convert before comparing — otherwise a clock-in at 9:30am SGT (which
    is 1:30am UTC) is incorrectly compared against 9:00am UTC and the
    employee gets stamped "late". (Round-7 redteam M10.)
    """
    from hr_advisory.models.company_user import AttendanceStatus

    try:
        work_start_h, work_start_m = _parse_time(settings.get("work_start_time", "09:00"))
        grace = settings.get("grace_period_minutes", 15)

        # Convert the ISO clock-in to SGT (UTC+8). Falls back to raw HH:MM
        # if the string is already a wall-clock time without a TZ offset.
        clock_h: int
        clock_m: int
        if "T" in clock_in_time:
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td

            try:
                dt = _dt.fromisoformat(clock_in_time.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=_tz.utc)
                local = dt.astimezone(_tz(_td(hours=8)))  # SGT default
                clock_h, clock_m = local.hour, local.minute
            except ValueError:
                time_part = clock_in_time.split("T")[1][:5]
                clock_h, clock_m = _parse_time(time_part)
        else:
            clock_h, clock_m = _parse_time(clock_in_time[:5])

        # Convert to minutes since midnight for comparison
        start_minutes = work_start_h * 60 + work_start_m
        clock_minutes = clock_h * 60 + clock_m

        if clock_minutes <= start_minutes + grace:
            return AttendanceStatus.PRESENT
        return AttendanceStatus.LATE
    except (ValueError, IndexError):
        return AttendanceStatus.PRESENT


def _calculate_hours(clock_in: str, clock_out: str, settings: dict) -> tuple[float, float]:
    """Calculate work hours and overtime hours from clock-in/out times.

    Returns (work_hours, overtime_hours).
    """
    try:
        dt_in = datetime.fromisoformat(clock_in)
        dt_out = datetime.fromisoformat(clock_out)
        delta = dt_out - dt_in
        total_minutes = max(delta.total_seconds() / 60, 0)

        # Standard work duration from settings
        start_h, start_m = _parse_time(settings.get("work_start_time", "09:00"))
        end_h, end_m = _parse_time(settings.get("work_end_time", "18:00"))
        standard_minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)

        ot_threshold = settings.get("overtime_threshold_minutes", 30)

        work_hours = round(min(total_minutes, standard_minutes) / 60, 2)
        overtime_minutes = total_minutes - standard_minutes
        if overtime_minutes > ot_threshold:
            overtime_hours = round(overtime_minutes / 60, 2)
        else:
            overtime_hours = 0.0

        return work_hours, overtime_hours
    except (ValueError, TypeError):
        return 0.0, 0.0


# --------------------------------------------------------------------------
# POST /attendance/clock-in
# --------------------------------------------------------------------------


@router.post("/clock-in")
async def clock_in(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Clock in for the current day."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"clock:{user_id}", max_requests=20, window_seconds=60, action_name="clock in/out"
    )

    emp = _find_employee_for_user(user_id, company_id)
    if emp is None:
        raise HTTPException(status_code=400, detail="Employee record not found.")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()

    # Check if already clocked in today
    existing = dataflow_crud.list_records(
        "AttendanceRecord",
        {"employee_id": emp["id"], "date": today},
        limit=1,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already clocked in for today.")

    body = (
        await request.json()
        if request.headers.get("content-type", "").startswith("application/json")
        else {}
    )

    settings = _get_attendance_settings(company_id)
    status = _determine_status(now, settings)

    try:
        record = dataflow_crud.create(
            "AttendanceRecord",
            {
                "employee_id": emp["id"],
                "company_id": company_id,
                "date": today,
                "clock_in": now,
                "clock_out": "",
                "clock_in_location": body.get("location"),
                "clock_in_photo": body.get("photo", ""),
                "status": status,
                "work_hours": 0.0,
                "overtime_hours": 0.0,
                "remarks": "",
                "is_manual": False,
            },
        )
    except Exception:
        # Handle TOCTOU race: another request may have created a record
        # between our check and create. Return the existing record instead.
        dup = dataflow_crud.list_records(
            "AttendanceRecord",
            {"employee_id": emp["id"], "date": today},
            limit=1,
        )
        if dup:
            return {"record": dup[0]}
        raise HTTPException(status_code=400, detail="Already clocked in for today.")
    return {"record": record}


# --------------------------------------------------------------------------
# POST /attendance/clock-out
# --------------------------------------------------------------------------


@router.post("/clock-out")
async def clock_out(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Clock out for the current day."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"clock:{user_id}", max_requests=20, window_seconds=60, action_name="clock in/out"
    )

    emp = _find_employee_for_user(user_id, company_id)
    if emp is None:
        raise HTTPException(status_code=400, detail="Employee record not found.")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()

    # Find today's record
    existing = dataflow_crud.list_records(
        "AttendanceRecord",
        {"employee_id": emp["id"], "date": today},
        limit=1,
    )
    if not existing:
        raise HTTPException(status_code=400, detail="No clock-in record found for today.")

    record = existing[0]
    if record.get("clock_out"):
        raise HTTPException(status_code=400, detail="Already clocked out for today.")

    body = (
        await request.json()
        if request.headers.get("content-type", "").startswith("application/json")
        else {}
    )

    settings = _get_attendance_settings(company_id)
    work_hours, overtime_hours = _calculate_hours(record["clock_in"], now, settings)

    dataflow_crud.update(
        "AttendanceRecord",
        record["id"],
        {
            "clock_out": now,
            "clock_out_location": body.get("location"),
            "clock_out_photo": body.get("photo", ""),
            "work_hours": work_hours,
            "overtime_hours": overtime_hours,
        },
    )

    updated = dataflow_crud.read("AttendanceRecord", record["id"])
    return {"record": updated}


# --------------------------------------------------------------------------
# GET /attendance/today
# --------------------------------------------------------------------------


@router.get("/today")
async def get_today_record(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the current employee's attendance record for today."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None:
        return {"record": None}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = dataflow_crud.list_records(
        "AttendanceRecord",
        {"employee_id": emp["id"], "date": today},
        limit=1,
    )
    return {"record": records[0] if records else None}


# --------------------------------------------------------------------------
# GET /attendance/records
# --------------------------------------------------------------------------


@router.get("/records")
async def list_attendance_records(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List attendance records. Supports ?employee_id=, ?month=, ?year= filters.

    Admins can query any employee; employees only see their own.
    Supports pagination via page and page_size query parameters.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    filter_dict: dict = {"company_id": company_id}

    employee_id_param = request.query_params.get("employee_id")
    month_param = request.query_params.get("month")
    year_param = request.query_params.get("year")

    if role not in ("owner", "hr_manager"):
        # Employee can only see own records
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None:
            return {"records": [], "count": 0, "page": page, "page_size": page_size, "total": 0, "pages": 0}
        filter_dict["employee_id"] = emp["id"]
    elif employee_id_param:
        filter_dict["employee_id"] = int(employee_id_param)

    records = dataflow_crud.list_records("AttendanceRecord", filter_dict)

    # Client-side filtering for month/year (DataFlow doesn't support partial date matching)
    if month_param and year_param:
        prefix = f"{year_param}-{month_param.zfill(2)}"
        records = [r for r in records if r.get("date", "").startswith(prefix)]
    elif year_param:
        records = [r for r in records if r.get("date", "").startswith(year_param)]

    records.sort(key=lambda r: r.get("date", ""), reverse=True)

    # Pagination
    total_count = len(records)
    offset = (page - 1) * page_size
    page_records = records[offset : offset + page_size]

    return {
        "records": page_records,
        "count": len(page_records),
        "page": page,
        "page_size": page_size,
        "total": total_count,
        "pages": math.ceil(total_count / page_size) if total_count > 0 else 0,
    }


# --------------------------------------------------------------------------
# GET /attendance/summary
# --------------------------------------------------------------------------


@router.get("/summary")
async def attendance_summary(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Monthly attendance summary: present/absent/late counts, total work/OT hours.

    Query params: ?employee_id= (admin), ?month= (e.g. 03), ?year= (e.g. 2026).
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    employee_id_param = request.query_params.get("employee_id")
    month_param = request.query_params.get("month")
    year_param = request.query_params.get("year")

    now = datetime.now(timezone.utc)
    if not year_param:
        year_param = str(now.year)
    if not month_param:
        month_param = str(now.month).zfill(2)

    # Determine employee_id
    if role not in ("owner", "hr_manager") or not employee_id_param:
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None:
            return {"summary": None}
        target_employee_id = emp["id"]
    else:
        target_employee_id = int(employee_id_param)

    records = dataflow_crud.list_records(
        "AttendanceRecord",
        {"employee_id": target_employee_id, "company_id": company_id},
    )

    prefix = f"{year_param}-{month_param.zfill(2)}"
    month_records = [r for r in records if r.get("date", "").startswith(prefix)]

    present_count = sum(1 for r in month_records if r.get("status") == "present")
    absent_count = sum(1 for r in month_records if r.get("status") == "absent")
    late_count = sum(1 for r in month_records if r.get("status") == "late")
    half_day_count = sum(1 for r in month_records if r.get("status") == "half_day")
    on_leave_count = sum(1 for r in month_records if r.get("status") == "on_leave")
    total_work_hours = round(sum(r.get("work_hours", 0.0) for r in month_records), 2)
    total_ot_hours = round(sum(r.get("overtime_hours", 0.0) for r in month_records), 2)

    return {
        "summary": {
            "employee_id": target_employee_id,
            "year": year_param,
            "month": month_param,
            "present": present_count,
            "absent": absent_count,
            "late": late_count,
            "half_day": half_day_count,
            "on_leave": on_leave_count,
            "total_work_hours": total_work_hours,
            "total_ot_hours": total_ot_hours,
            "total_records": len(month_records),
        }
    }


# --------------------------------------------------------------------------
# PATCH /attendance/{id} — Admin correction
# --------------------------------------------------------------------------


@router.patch("/{record_id}")
async def admin_correct_attendance(
    record_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Admin correction of an attendance record."""
    company_id = get_current_company_id(current_user)
    record = dataflow_crud.read("AttendanceRecord", record_id)
    if record is None or record.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    body = await request.json()
    allowed = {
        "clock_in",
        "clock_out",
        "status",
        "work_hours",
        "overtime_hours",
        "remarks",
        "is_manual",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # Mark as manual correction
    updates["is_manual"] = True

    # If clock_in and clock_out provided, recalculate hours
    clock_in = updates.get("clock_in", record.get("clock_in", ""))
    clock_out = updates.get("clock_out", record.get("clock_out", ""))
    if clock_in and clock_out and ("clock_in" in updates or "clock_out" in updates):
        settings = _get_attendance_settings(company_id)
        work_hours, overtime_hours = _calculate_hours(clock_in, clock_out, settings)
        updates["work_hours"] = work_hours
        updates["overtime_hours"] = overtime_hours

    dataflow_crud.update("AttendanceRecord", record_id, updates)
    updated = dataflow_crud.read("AttendanceRecord", record_id)
    return {"record": updated}


# --------------------------------------------------------------------------
# Attendance Settings
# --------------------------------------------------------------------------


@router.get("/settings")
async def get_attendance_settings(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the company's attendance settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    settings = _get_attendance_settings(company_id)
    return {"settings": settings}


@router.put("/settings")
async def update_attendance_settings(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create or update the company's attendance settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    allowed = {
        "work_start_time",
        "work_end_time",
        "grace_period_minutes",
        "overtime_threshold_minutes",
        "require_gps",
        "require_photo",
        "allowed_locations",
    }
    fields = {k: v for k, v in body.items() if k in allowed}

    # Check if settings already exist
    existing = dataflow_crud.list_records(
        "AttendanceSettings",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        dataflow_crud.update("AttendanceSettings", existing[0]["id"], fields)
        updated = dataflow_crud.read("AttendanceSettings", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = dataflow_crud.create("AttendanceSettings", fields)

    return {"settings": updated}


# --------------------------------------------------------------------------
# Timesheet Approval
# --------------------------------------------------------------------------


@router.post("/timesheet/submit")
async def submit_timesheet(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit a monthly timesheet for approval.

    Aggregates attendance records for the given month and creates
    a TimesheetApproval record.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None:
        raise HTTPException(status_code=400, detail="Employee record not found.")

    body = await request.json()
    month = body.get("month", "")  # e.g. "2026-03"
    if not month:
        raise HTTPException(status_code=400, detail="month is required (e.g. '2026-03').")

    # Check for existing timesheet for this month
    existing = dataflow_crud.list_records(
        "TimesheetApproval",
        {"employee_id": emp["id"], "month": month},
        limit=1,
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Timesheet for {month} already submitted (status: {existing[0].get('status')}).",
        )

    # Aggregate attendance for the month
    records = dataflow_crud.list_records(
        "AttendanceRecord",
        {"employee_id": emp["id"], "company_id": company_id},
    )
    month_records = [r for r in records if r.get("date", "").startswith(month)]
    total_work = round(sum(r.get("work_hours", 0.0) for r in month_records), 2)
    total_ot = round(sum(r.get("overtime_hours", 0.0) for r in month_records), 2)

    now = datetime.now(timezone.utc).isoformat()
    timesheet = dataflow_crud.create(
        "TimesheetApproval",
        {
            "employee_id": emp["id"],
            "company_id": company_id,
            "month": month,
            "status": "pending",
            "total_work_hours": total_work,
            "total_ot_hours": total_ot,
            "submitted_at": now,
        },
    )
    return {"timesheet": timesheet}


def _authorize_review_timesheet(current_user: dict, ts: dict) -> None:
    """Guard for approve/reject timesheet actions (P4-MG-2).

    Allowed: owner, hr_manager, or direct line-manager of
    `ts.employee_id`. Self-approval denied.
    """
    role = current_user.get("role", "employee")
    target_emp_id = ts.get("employee_id")
    company_id = ts.get("company_id")
    try:
        user_id = int(current_user.get("sub", 0))
    except (ValueError, TypeError):
        user_id = 0
    caller_emp = (
        _find_employee_for_user(user_id, company_id) if company_id else None
    )
    if caller_emp and caller_emp.get("id") == target_emp_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot review your own timesheet.",
        )
    if role in ("owner", "hr_manager"):
        return
    if not target_emp_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    if not manager_scope.is_manager_of(current_user, int(target_emp_id)):
        raise HTTPException(
            status_code=403,
            detail="You are not the manager of this employee.",
        )


@router.patch("/timesheet/{timesheet_id}/approve")
async def approve_timesheet(
    timesheet_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Approve a pending timesheet.

    Scope (P4-MG-2): owner / HR / line-manager of the timesheet's
    employee. Self-approval denied.
    """
    company_id = get_current_company_id(current_user)
    ts = dataflow_crud.read("TimesheetApproval", timesheet_id)
    if ts is None or ts.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Timesheet not found.")

    _authorize_review_timesheet(current_user, ts)

    if ts.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending timesheets can be approved.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    dataflow_crud.update(
        "TimesheetApproval",
        timesheet_id,
        {
            "status": "approved",
            "approved_by": actor_id,
            "approved_at": now,
        },
    )
    return {"message": "Timesheet approved.", "status": "approved"}


@router.patch("/timesheet/{timesheet_id}/reject")
async def reject_timesheet(
    timesheet_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Reject a pending timesheet. Same scope as approve (P4-MG-2)."""
    company_id = get_current_company_id(current_user)
    ts = dataflow_crud.read("TimesheetApproval", timesheet_id)
    if ts is None or ts.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Timesheet not found.")

    _authorize_review_timesheet(current_user, ts)

    if ts.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending timesheets can be rejected.")

    dataflow_crud.update("TimesheetApproval", timesheet_id, {"status": "rejected"})
    return {"message": "Timesheet rejected.", "status": "rejected"}


@router.get("/timesheets")
async def list_timesheets(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List timesheets with role-and-org-chart-aware scope (P4-MG-2).

    - Owners + HR managers see the whole company.
    - Line managers see their own + their team's timesheets.
    - Regular employees see their own only.

    Supports ?status= filter.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    status_filter = request.query_params.get("status")

    if role in ("owner", "hr_manager"):
        filter_dict: dict = {"company_id": company_id}
        if status_filter:
            filter_dict["status"] = status_filter
        timesheets = dataflow_crud.list_records("TimesheetApproval", filter_dict)
    else:
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None:
            return {"timesheets": [], "count": 0}
        own_emp_id = emp["id"]
        team_ids = manager_scope.get_managed_employee_ids(current_user)
        scope_ids = set(team_ids) | {own_emp_id}
        if not team_ids:
            filter_dict = {"employee_id": own_emp_id, "company_id": company_id}
            if status_filter:
                filter_dict["status"] = status_filter
            timesheets = dataflow_crud.list_records(
                "TimesheetApproval", filter_dict
            )
        else:
            timesheets = dataflow_crud.list_records(
                "TimesheetApproval", {"company_id": company_id}
            )
            timesheets = [
                t for t in timesheets if t.get("employee_id") in scope_ids
            ]
            if status_filter:
                timesheets = [t for t in timesheets if t.get("status") == status_filter]

    timesheets.sort(key=lambda t: t.get("month", ""), reverse=True)
    return {"timesheets": timesheets, "count": len(timesheets)}


# ==========================================================================
# LATENESS & EARLY DEPARTURE SETTINGS (T354)
# ==========================================================================


def _get_lateness_settings(company_id: int) -> dict:
    """Fetch lateness settings for a company, returning defaults if none exist."""
    settings = dataflow_crud.list_records(
        "LatenessSettings",
        {"company_id": company_id},
        limit=1,
    )
    if settings:
        return settings[0]
    return {
        "grace_period_minutes": 15,
        "deduction_enabled": False,
        "deduction_per_incident": 0.0,
        "max_incidents_per_month": 0,
        "auto_flag": True,
    }


def _get_early_departure_settings(company_id: int) -> dict:
    """Fetch early departure settings for a company, returning defaults if none exist."""
    settings = dataflow_crud.list_records(
        "EarlyDepartureSettings",
        {"company_id": company_id},
        limit=1,
    )
    if settings:
        return settings[0]
    return {
        "threshold_minutes": 30,
        "deduction_enabled": False,
        "deduction_per_incident": 0.0,
        "auto_flag": True,
    }


@router.get("/lateness-settings")
async def get_lateness_settings_endpoint(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the company's lateness settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    settings = _get_lateness_settings(company_id)
    return {"settings": settings}


@router.put("/lateness-settings")
async def update_lateness_settings(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create or update the company's lateness settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    allowed = {
        "grace_period_minutes",
        "deduction_enabled",
        "deduction_per_incident",
        "max_incidents_per_month",
        "auto_flag",
    }
    fields = {k: v for k, v in body.items() if k in allowed}

    if "deduction_per_incident" in fields:
        val = float(fields["deduction_per_incident"])
        if not math.isfinite(val):
            raise HTTPException(status_code=400, detail="Invalid numeric value.")
        fields["deduction_per_incident"] = val

    existing = dataflow_crud.list_records(
        "LatenessSettings",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        dataflow_crud.update("LatenessSettings", existing[0]["id"], fields)
        updated = dataflow_crud.read("LatenessSettings", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = dataflow_crud.create("LatenessSettings", fields)

    return {"settings": updated}


@router.get("/early-departure-settings")
async def get_early_departure_settings_endpoint(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the company's early departure settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    settings = _get_early_departure_settings(company_id)
    return {"settings": settings}


@router.put("/early-departure-settings")
async def update_early_departure_settings(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create or update the company's early departure settings."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    allowed = {
        "threshold_minutes",
        "deduction_enabled",
        "deduction_per_incident",
        "auto_flag",
    }
    fields = {k: v for k, v in body.items() if k in allowed}

    if "deduction_per_incident" in fields:
        val = float(fields["deduction_per_incident"])
        if not math.isfinite(val):
            raise HTTPException(status_code=400, detail="Invalid numeric value.")
        fields["deduction_per_incident"] = val

    existing = dataflow_crud.list_records(
        "EarlyDepartureSettings",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        dataflow_crud.update("EarlyDepartureSettings", existing[0]["id"], fields)
        updated = dataflow_crud.read("EarlyDepartureSettings", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = dataflow_crud.create("EarlyDepartureSettings", fields)

    return {"settings": updated}


# ==========================================================================
# ADMIN DASHBOARD VIEWS (T356)
# ==========================================================================


@router.get("/today/dashboard")
async def today_dashboard(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Real-time dashboard: who's in, who's late, who's absent today."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # H1 redteam (round-12): only employees who actually clock in/out should
    # appear on the daily status board. Salaried desk staff don't have a
    # clock-in workflow, so listing them as "Absent" every day was misleading.
    # The frontend Attendance page consumes this list — filtering at the
    # source keeps the page honest without a UI-side workaround.
    employees = dataflow_crud.list_records(
        "Employee",
        {
            "company_id": company_id,
            "is_active": True,
            "tracks_attendance": True,
        },
    )

    # Fetch today's attendance records for the company
    records = dataflow_crud.list_records(
        "AttendanceRecord",
        {"company_id": company_id, "date": today},
    )
    records_by_emp = {r.get("employee_id"): r for r in records}

    # Fetch approved leave for today
    leave_apps = dataflow_crud.list_records(
        "LeaveApplication",
        {"company_id": company_id, "status": "approved"},
    )
    on_leave_ids: set[int] = set()
    for la in leave_apps:
        start = la.get("start_date", "")
        end = la.get("end_date", "")
        if start <= today <= end:
            on_leave_ids.add(la.get("employee_id"))

    present = []
    late = []
    absent = []
    on_leave = []

    for emp in employees:
        emp_id = emp.get("id")
        user_id = emp.get("user_id")
        user = None
        if user_id:
            user = dataflow_crud.read("User", user_id)
        name = user.get("name", "") if user else ""
        entry = {
            "employee_id": emp_id,
            "name": name,
            "department": emp.get("department", ""),
        }

        if emp_id in on_leave_ids:
            on_leave.append(entry)
        elif emp_id in records_by_emp:
            record = records_by_emp[emp_id]
            entry["clock_in"] = record.get("clock_in", "")
            entry["clock_out"] = record.get("clock_out", "")
            status = record.get("status", "present")
            if status == "late":
                late.append(entry)
            else:
                present.append(entry)
        else:
            absent.append(entry)

    return {
        "date": today,
        "present": present,
        "late": late,
        "absent": absent,
        "on_leave": on_leave,
        "counts": {
            "present": len(present),
            "late": len(late),
            "absent": len(absent),
            "on_leave": len(on_leave),
            "total": len(employees),
        },
    }


@router.get("/today/overview")
async def today_overview(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Today's attendance overview — returns a list of employees with status.

    This is the format expected by the frontend attendance page for admin users.
    """
    dashboard = await today_dashboard(current_user)
    employees = []
    for emp in dashboard.get("present", []):
        employees.append({**emp, "status": "present"})
    for emp in dashboard.get("late", []):
        employees.append({**emp, "status": "late"})
    for emp in dashboard.get("absent", []):
        employees.append({**emp, "status": "absent"})
    for emp in dashboard.get("on_leave", []):
        employees.append({**emp, "status": "on_leave"})
    return {"employees": employees, "counts": dashboard.get("counts", {})}


@router.get("/summary/aggregated")
async def aggregated_summary(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Aggregated attendance hours for a date range across all employees.

    Query params: ?start_date=, ?end_date= (ISO dates).
    Returns per-employee totals for the range.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    start_date = request.query_params.get("start_date", "")
    end_date = request.query_params.get("end_date", "")

    if not start_date or not end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date and end_date query parameters are required.",
        )

    # Fetch all attendance records for company
    all_records = dataflow_crud.list_records(
        "AttendanceRecord",
        {"company_id": company_id},
    )

    # Filter to date range
    range_records = [r for r in all_records if start_date <= r.get("date", "") <= end_date]

    # Aggregate per employee
    from collections import defaultdict

    emp_totals: dict[int, dict] = defaultdict(
        lambda: {
            "total_work_hours": 0.0,
            "total_ot_hours": 0.0,
            "present_days": 0,
            "late_days": 0,
            "absent_days": 0,
        }
    )

    for r in range_records:
        emp_id = r.get("employee_id")
        emp_totals[emp_id]["total_work_hours"] += r.get("work_hours", 0.0)
        emp_totals[emp_id]["total_ot_hours"] += r.get("overtime_hours", 0.0)
        status = r.get("status", "")
        if status == "present":
            emp_totals[emp_id]["present_days"] += 1
        elif status == "late":
            emp_totals[emp_id]["late_days"] += 1
        elif status == "absent":
            emp_totals[emp_id]["absent_days"] += 1

    # Enrich with employee info
    results = []
    for emp_id, totals in emp_totals.items():
        emp_records = dataflow_crud.list_records("Employee", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = dataflow_crud.read("User", emp.get("user_id")) if emp.get("user_id") else None
        results.append(
            {
                "employee_id": emp_id,
                "name": user.get("name", "") if user else "",
                "department": emp.get("department", ""),
                "total_work_hours": round(totals["total_work_hours"], 2),
                "total_ot_hours": round(totals["total_ot_hours"], 2),
                "present_days": totals["present_days"],
                "late_days": totals["late_days"],
                "absent_days": totals["absent_days"],
            }
        )

    results.sort(key=lambda r: r.get("name", ""))

    return {
        "start_date": start_date,
        "end_date": end_date,
        "employees": results,
        "count": len(results),
    }
