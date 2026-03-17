"""Attendance and time-tracking management endpoints.

Handles clock-in/out, daily attendance records, monthly summaries,
attendance settings, and timesheet approval workflows.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

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
