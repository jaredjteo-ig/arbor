"""Attendance and time-tracking management endpoints.

Handles clock-in/out, daily attendance records, monthly summaries,
attendance settings, and timesheet approval workflows.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Input length limits
MAX_TEXT_LENGTH = 2000
MAX_NAME_LENGTH = 200


def _validate_text_length(value: str, field_name: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    """Validate text input to maximum length."""
    if value and len(value) > max_len:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {max_len} characters.",
        )
    return value


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


def _find_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Look up the employee record for a given user in a company."""
    records = _dataflow_list(
        "EmployeeListNode",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


def _get_attendance_settings(company_id: int) -> dict:
    """Fetch attendance settings for a company, returning defaults if none exist."""
    settings = _dataflow_list(
        "AttendanceSettingsListNode",
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
    """Determine attendance status based on clock-in time vs settings."""
    from hr_advisory.models.company_user import AttendanceStatus

    try:
        work_start_h, work_start_m = _parse_time(settings.get("work_start_time", "09:00"))
        grace = settings.get("grace_period_minutes", 15)

        # Extract HH:MM from ISO datetime
        if "T" in clock_in_time:
            time_part = clock_in_time.split("T")[1][:5]
        else:
            time_part = clock_in_time[:5]
        clock_h, clock_m = _parse_time(time_part)

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
    existing = _dataflow_list(
        "AttendanceRecordListNode",
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

    record = _dataflow_create(
        "AttendanceRecordCreateNode",
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
    existing = _dataflow_list(
        "AttendanceRecordListNode",
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

    _dataflow_update(
        "AttendanceRecordUpdateNode",
        record["id"],
        {
            "clock_out": now,
            "clock_out_location": body.get("location"),
            "clock_out_photo": body.get("photo", ""),
            "work_hours": work_hours,
            "overtime_hours": overtime_hours,
        },
    )

    updated = _dataflow_read("AttendanceRecordReadNode", record["id"])
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
    records = _dataflow_list(
        "AttendanceRecordListNode",
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
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List attendance records. Supports ?employee_id=, ?month=, ?year= filters.

    Admins can query any employee; employees only see their own.
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
            return {"records": [], "count": 0}
        filter_dict["employee_id"] = emp["id"]
    elif employee_id_param:
        filter_dict["employee_id"] = int(employee_id_param)

    records = _dataflow_list("AttendanceRecordListNode", filter_dict)

    # Client-side filtering for month/year (DataFlow doesn't support partial date matching)
    if month_param and year_param:
        prefix = f"{year_param}-{month_param.zfill(2)}"
        records = [r for r in records if r.get("date", "").startswith(prefix)]
    elif year_param:
        records = [r for r in records if r.get("date", "").startswith(year_param)]

    records.sort(key=lambda r: r.get("date", ""), reverse=True)
    return {"records": records, "count": len(records)}


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

    records = _dataflow_list(
        "AttendanceRecordListNode",
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
    record = _dataflow_read("AttendanceRecordReadNode", record_id)
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

    _dataflow_update("AttendanceRecordUpdateNode", record_id, updates)
    updated = _dataflow_read("AttendanceRecordReadNode", record_id)
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
    existing = _dataflow_list(
        "AttendanceSettingsListNode",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        _dataflow_update("AttendanceSettingsUpdateNode", existing[0]["id"], fields)
        updated = _dataflow_read("AttendanceSettingsReadNode", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = _dataflow_create("AttendanceSettingsCreateNode", fields)

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
    existing = _dataflow_list(
        "TimesheetApprovalListNode",
        {"employee_id": emp["id"], "month": month},
        limit=1,
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Timesheet for {month} already submitted (status: {existing[0].get('status')}).",
        )

    # Aggregate attendance for the month
    records = _dataflow_list(
        "AttendanceRecordListNode",
        {"employee_id": emp["id"], "company_id": company_id},
    )
    month_records = [r for r in records if r.get("date", "").startswith(month)]
    total_work = round(sum(r.get("work_hours", 0.0) for r in month_records), 2)
    total_ot = round(sum(r.get("overtime_hours", 0.0) for r in month_records), 2)

    now = datetime.now(timezone.utc).isoformat()
    timesheet = _dataflow_create(
        "TimesheetApprovalCreateNode",
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


@router.patch("/timesheet/{timesheet_id}/approve")
async def approve_timesheet(
    timesheet_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Approve a pending timesheet."""
    company_id = get_current_company_id(current_user)
    ts = _dataflow_read("TimesheetApprovalReadNode", timesheet_id)
    if ts is None or ts.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Timesheet not found.")

    if ts.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending timesheets can be approved.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    _dataflow_update(
        "TimesheetApprovalUpdateNode",
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
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reject a pending timesheet."""
    company_id = get_current_company_id(current_user)
    ts = _dataflow_read("TimesheetApprovalReadNode", timesheet_id)
    if ts is None or ts.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Timesheet not found.")

    if ts.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending timesheets can be rejected.")

    _dataflow_update("TimesheetApprovalUpdateNode", timesheet_id, {"status": "rejected"})
    return {"message": "Timesheet rejected.", "status": "rejected"}


@router.get("/timesheets")
async def list_timesheets(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List timesheets. Admins see all; employees see their own.

    Supports ?status= filter.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    filter_dict: dict = {"company_id": company_id}

    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None:
            return {"timesheets": [], "count": 0}
        filter_dict["employee_id"] = emp["id"]

    status_filter = request.query_params.get("status")
    if status_filter:
        filter_dict["status"] = status_filter

    timesheets = _dataflow_list("TimesheetApprovalListNode", filter_dict)
    timesheets.sort(key=lambda t: t.get("month", ""), reverse=True)
    return {"timesheets": timesheets, "count": len(timesheets)}


# ==========================================================================
# LATENESS & EARLY DEPARTURE SETTINGS (T354)
# ==========================================================================


def _get_lateness_settings(company_id: int) -> dict:
    """Fetch lateness settings for a company, returning defaults if none exist."""
    settings = _dataflow_list(
        "LatenessSettingsListNode",
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
    settings = _dataflow_list(
        "EarlyDepartureSettingsListNode",
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

    existing = _dataflow_list(
        "LatenessSettingsListNode",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        _dataflow_update("LatenessSettingsUpdateNode", existing[0]["id"], fields)
        updated = _dataflow_read("LatenessSettingsReadNode", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = _dataflow_create("LatenessSettingsCreateNode", fields)

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

    existing = _dataflow_list(
        "EarlyDepartureSettingsListNode",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        _dataflow_update("EarlyDepartureSettingsUpdateNode", existing[0]["id"], fields)
        updated = _dataflow_read("EarlyDepartureSettingsReadNode", existing[0]["id"])
    else:
        fields["company_id"] = company_id
        updated = _dataflow_create("EarlyDepartureSettingsCreateNode", fields)

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

    # Fetch all active employees
    employees = _dataflow_list(
        "EmployeeListNode",
        {"company_id": company_id, "is_active": True},
    )

    # Fetch today's attendance records for the company
    records = _dataflow_list(
        "AttendanceRecordListNode",
        {"company_id": company_id, "date": today},
    )
    records_by_emp = {r.get("employee_id"): r for r in records}

    # Fetch approved leave for today
    leave_apps = _dataflow_list(
        "LeaveApplicationListNode",
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
            user = _dataflow_read("UserReadNode", user_id)
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
    all_records = _dataflow_list(
        "AttendanceRecordListNode",
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
        emp_records = _dataflow_list("EmployeeListNode", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = _dataflow_read("UserReadNode", emp.get("user_id")) if emp.get("user_id") else None
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
