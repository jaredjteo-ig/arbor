"""Shift scheduling endpoints.

Handles shift templates, assignments, publishing, employee schedule views,
availability checks, and weekly hours tracking with Employment Act limits.
"""

import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()

# B19: shared helpers consolidated in _helpers.py.
from hr_advisory.api.routers._helpers import (  # noqa: E402
    MAX_TEXT_LENGTH,
    MAX_NAME_LENGTH,
    _validate_text_length,
)


# --------------------------------------------------------------------------
# DataFlow helpers
# --------------------------------------------------------------------------

from hr_advisory.services import dataflow_crud


def _find_user_by_id(user_id: int) -> dict | None:
    return dataflow_crud.read("User", user_id)


def _week_dates(week_start: str) -> list[str]:
    """Return a list of 7 date strings (Mon-Sun) starting from week_start."""
    start = date.fromisoformat(week_start)
    return [(start + timedelta(days=i)).isoformat() for i in range(7)]


from hr_advisory.api.routers._helpers import _find_employee_for_user  # noqa: E402


# --------------------------------------------------------------------------
# Shift Templates (admin only)
# --------------------------------------------------------------------------


@router.get("/templates")
async def list_shift_templates(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all shift templates for the current company."""
    company_id = get_current_company_id(current_user)
    templates = dataflow_crud.list_records("ShiftTemplate", {"company_id": company_id})
    return {"templates": templates, "count": len(templates)}


@router.post("/templates")
async def create_shift_template(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new shift template."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_shift_template:{user_id}", max_requests=30, window_seconds=60, action_name="create shift template")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    template = dataflow_crud.create(
        "ShiftTemplate",
        {
            "company_id": company_id,
            "name": name,
            "start_time": body.get("start_time", "09:00"),
            "end_time": body.get("end_time", "17:00"),
            "break_minutes": body.get("break_minutes", 60),
            "work_hours": body.get("work_hours", 8.0),
            "colour": body.get("colour", "#4A90C4"),
            "is_active": body.get("is_active", True),
        },
    )
    return {"template": template}


@router.patch("/templates/{template_id}")
async def update_shift_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an existing shift template."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"update_shift_template:{user_id}", max_requests=30, window_seconds=60, action_name="update shift template")
    company_id = get_current_company_id(current_user)
    existing = dataflow_crud.read("ShiftTemplate", template_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Shift template not found.")

    body = await request.json()
    allowed_fields = {
        "name",
        "start_time",
        "end_time",
        "break_minutes",
        "work_hours",
        "colour",
        "is_active",
    }
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    dataflow_crud.update("ShiftTemplate", template_id, updates)
    updated = dataflow_crud.read("ShiftTemplate", template_id)
    return {"template": updated}


# --------------------------------------------------------------------------
# Shift Assignments (admin)
# --------------------------------------------------------------------------


@router.get("/schedule")
async def get_weekly_schedule(
    week_start: str = "",
    department: str = "",
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the weekly schedule grid grouped by employee and date.

    Query params:
        week_start: ISO date for the Monday of the week (defaults to current week).
        department: Optional department filter.
    """
    company_id = get_current_company_id(current_user)

    if not week_start:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()

    dates = _week_dates(week_start)

    # Fetch all assignments for the week
    all_assignments = []
    for d in dates:
        day_assignments = dataflow_crud.list_records(
            "ShiftAssignment",
            {"company_id": company_id, "date": d},
        )
        all_assignments.extend(day_assignments)

    # Fetch employees (optionally filtered by department)
    emp_filter: dict = {"company_id": company_id, "is_active": True}
    if department:
        emp_filter["department"] = department
    employees = dataflow_crud.list_records("Employee", emp_filter)

    # Fetch templates for enrichment
    templates = dataflow_crud.list_records("ShiftTemplate", {"company_id": company_id})
    template_map = {t["id"]: t for t in templates}

    # Build grid: employee -> date -> assignment
    emp_ids = {e["id"] for e in employees}
    grid: dict[int, dict] = {}
    for emp in employees:
        user = _find_user_by_id(emp.get("user_id"))
        grid[emp["id"]] = {
            "employee_id": emp["id"],
            "name": user.get("name", "") if user else "",
            "department": emp.get("department", ""),
            "shifts": {},
        }

    for assignment in all_assignments:
        emp_id = assignment.get("employee_id")
        if emp_id not in emp_ids:
            continue
        d = assignment.get("date", "")
        tmpl = template_map.get(assignment.get("shift_template_id"), {})
        grid.setdefault(emp_id, {"employee_id": emp_id, "name": "", "department": "", "shifts": {}})
        grid[emp_id]["shifts"][d] = {
            **assignment,
            "template_name": tmpl.get("name", ""),
            "start_time": tmpl.get("start_time", ""),
            "end_time": tmpl.get("end_time", ""),
            "colour": tmpl.get("colour", ""),
        }

    # Build a flat assignments list (with employee_name + template_name)
    # so the weekly grid in the web app can render directly.
    flat_assignments: list[dict] = []
    emp_name_map = {row["employee_id"]: row.get("name", "") for row in grid.values()}
    for assignment in all_assignments:
        emp_id = assignment.get("employee_id")
        if emp_id not in emp_ids:
            continue
        tmpl = template_map.get(assignment.get("shift_template_id"), {})
        flat_assignments.append(
            {
                **assignment,
                "employee_name": emp_name_map.get(emp_id, ""),
                "template_name": tmpl.get("name", ""),
                "template_colour": tmpl.get("colour", ""),
            }
        )

    return {
        "week_start": week_start,
        "dates": dates,
        "schedule": list(grid.values()),
        "assignments": flat_assignments,
    }


@router.post("/assignments")
async def create_shift_assignment(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a shift assignment for an employee on a specific date."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_shift_assignment:{user_id}", max_requests=30, window_seconds=60, action_name="create shift assignment")

    body = await request.json()
    employee_id = body.get("employee_id")
    shift_template_id = body.get("shift_template_id")
    assign_date = body.get("date", "")

    if not employee_id or not shift_template_id or not assign_date:
        raise HTTPException(
            status_code=400,
            detail="employee_id, shift_template_id, and date are required.",
        )

    # Verify employee belongs to company
    emp_records = dataflow_crud.list_records("Employee", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Verify template belongs to company
    template = dataflow_crud.read("ShiftTemplate", shift_template_id)
    if template is None or template.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Shift template not found.")

    assignment = dataflow_crud.create(
        "ShiftAssignment",
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "shift_template_id": shift_template_id,
            "date": assign_date,
            "status": "scheduled",
            "actual_start": "",
            "actual_end": "",
            "notes": body.get("notes", ""),
        },
    )
    return {"assignment": assignment}


@router.patch("/assignments/{assignment_id}")
async def update_shift_assignment(
    assignment_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a shift assignment (e.g. change template, actual times, status)."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"update_shift_assignment:{user_id}", max_requests=30, window_seconds=60, action_name="update shift assignment")
    company_id = get_current_company_id(current_user)
    existing = dataflow_crud.read("ShiftAssignment", assignment_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Shift assignment not found.")

    body = await request.json()
    allowed_fields = {
        "shift_template_id",
        "date",
        "status",
        "actual_start",
        "actual_end",
        "notes",
    }
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    dataflow_crud.update("ShiftAssignment", assignment_id, updates)
    updated = dataflow_crud.read("ShiftAssignment", assignment_id)
    return {"assignment": updated}


@router.delete("/assignments/{assignment_id}")
async def cancel_shift_assignment(
    assignment_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Cancel a shift assignment (soft-cancel by setting status to cancelled)."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"cancel_shift_assignment:{user_id}", max_requests=30, window_seconds=60, action_name="cancel shift assignment")
    company_id = get_current_company_id(current_user)
    existing = dataflow_crud.read("ShiftAssignment", assignment_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Shift assignment not found.")

    dataflow_crud.update("ShiftAssignment", assignment_id, {"status": "cancelled"})
    return {"message": "Shift assignment cancelled.", "status": "cancelled"}


# --------------------------------------------------------------------------
# Publishing
# --------------------------------------------------------------------------


@router.post("/publish")
async def publish_schedule(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Publish a weekly schedule (creates an audit record)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"publish_schedule:{user_id}", max_requests=30, window_seconds=60, action_name="publish schedule")

    body = await request.json()
    week_start = body.get("week_start", "")
    if not week_start:
        raise HTTPException(status_code=400, detail="week_start is required.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    record = dataflow_crud.create(
        "ShiftPublish",
        {
            "company_id": company_id,
            "week_start": week_start,
            "published_at": now,
            "published_by": actor_id,
        },
    )
    return {"publish": record}


# --------------------------------------------------------------------------
# Employee views
# --------------------------------------------------------------------------


@router.get("/my-schedule")
async def get_my_schedule(
    week_start: str = "",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the current employee's shift schedule for a given week."""
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    if company_id is None:
        return {"shifts": []}

    emp = _find_employee_for_user(user_id, company_id)
    if emp is None:
        return {"shifts": []}

    if not week_start:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()

    dates = _week_dates(week_start)

    # Fetch templates for enrichment
    templates = dataflow_crud.list_records("ShiftTemplate", {"company_id": company_id})
    template_map = {t["id"]: t for t in templates}

    shifts = []
    for d in dates:
        day_assignments = dataflow_crud.list_records(
            "ShiftAssignment",
            {"employee_id": emp["id"], "date": d},
        )
        for assignment in day_assignments:
            if assignment.get("status") == "cancelled":
                continue
            tmpl = template_map.get(assignment.get("shift_template_id"), {})
            shifts.append(
                {
                    **assignment,
                    "template_name": tmpl.get("name", ""),
                    "start_time": tmpl.get("start_time", ""),
                    "end_time": tmpl.get("end_time", ""),
                    "colour": tmpl.get("colour", ""),
                }
            )

    shifts.sort(key=lambda s: s.get("date", ""))
    return {"week_start": week_start, "shifts": shifts}


# --------------------------------------------------------------------------
# Availability
# --------------------------------------------------------------------------


@router.get("/availability")
async def get_availability(
    date_str: str = "",
    department: str = "",
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Check which employees are available on a given date.

    An employee is unavailable if they have approved leave covering that date
    or already have a non-cancelled shift assignment on that date.

    Query params:
        date_str: ISO date to check (defaults to today).
        department: Optional department filter.
    """
    company_id = get_current_company_id(current_user)

    if not date_str:
        date_str = date.today().isoformat()

    # Fetch active employees
    emp_filter: dict = {"company_id": company_id, "is_active": True}
    if department:
        emp_filter["department"] = department
    employees = dataflow_crud.list_records("Employee", emp_filter)

    # Fetch approved leave applications for this company
    leave_apps = dataflow_crud.list_records(
        "LeaveApplication",
        {"company_id": company_id, "status": "approved"},
    )

    # Build set of employee IDs on leave on the target date
    on_leave: set[int] = set()
    for la in leave_apps:
        start = la.get("start_date", "")
        end = la.get("end_date", "")
        if start <= date_str <= end:
            on_leave.add(la.get("employee_id"))

    # Fetch shift assignments for the date
    day_assignments = dataflow_crud.list_records(
        "ShiftAssignment",
        {"company_id": company_id, "date": date_str},
    )
    already_assigned: set[int] = set()
    for a in day_assignments:
        if a.get("status") != "cancelled":
            already_assigned.add(a.get("employee_id"))

    available = []
    unavailable = []
    for emp in employees:
        emp_id = emp["id"]
        user = _find_user_by_id(emp.get("user_id"))
        entry = {
            "employee_id": emp_id,
            "name": user.get("name", "") if user else "",
            "department": emp.get("department", ""),
        }
        if emp_id in on_leave:
            entry["reason"] = "on_leave"
            unavailable.append(entry)
        elif emp_id in already_assigned:
            entry["reason"] = "already_assigned"
            unavailable.append(entry)
        else:
            available.append(entry)

    return {
        "date": date_str,
        "available": available,
        "unavailable": unavailable,
    }


# --------------------------------------------------------------------------
# Hours tracking
# --------------------------------------------------------------------------

EMPLOYMENT_ACT_WEEKLY_LIMIT = 44.0


@router.get("/hours")
async def get_weekly_hours(
    week_start: str = "",
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get hours per employee for a given week, with Employment Act warnings.

    Flags any employee exceeding 44 hours per week.

    Query params:
        week_start: ISO date for the Monday of the week (defaults to current week).
    """
    company_id = get_current_company_id(current_user)

    if not week_start:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()

    dates = _week_dates(week_start)

    # Fetch all non-cancelled assignments for the week
    all_assignments = []
    for d in dates:
        day_assignments = dataflow_crud.list_records(
            "ShiftAssignment",
            {"company_id": company_id, "date": d},
        )
        all_assignments.extend(a for a in day_assignments if a.get("status") != "cancelled")

    # Fetch templates for work_hours lookup
    templates = dataflow_crud.list_records("ShiftTemplate", {"company_id": company_id})
    template_map = {t["id"]: t for t in templates}

    # Sum hours per employee
    hours_by_emp: dict[int, float] = defaultdict(float)
    for a in all_assignments:
        tmpl = template_map.get(a.get("shift_template_id"), {})
        hours_by_emp[a.get("employee_id")] += tmpl.get("work_hours", 0.0)

    # Build response with employee names and warnings
    employees_data = []
    warnings = []

    emp_ids = list(hours_by_emp.keys())
    for emp_id in emp_ids:
        total = round(hours_by_emp[emp_id], 2)
        emp_records = dataflow_crud.list_records("Employee", {"id": emp_id}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = _find_user_by_id(emp.get("user_id")) if emp else None
        name = user.get("name", "") if user else ""

        entry = {
            "employee_id": emp_id,
            "name": name,
            "department": emp.get("department", ""),
            "total_hours": total,
            "exceeds_limit": total > EMPLOYMENT_ACT_WEEKLY_LIMIT,
        }
        employees_data.append(entry)

        if total > EMPLOYMENT_ACT_WEEKLY_LIMIT:
            warnings.append(
                f"{name or emp_id} is scheduled for {total}h "
                f"(exceeds {EMPLOYMENT_ACT_WEEKLY_LIMIT}h Employment Act limit)"
            )

    employees_data.sort(key=lambda e: e.get("total_hours", 0), reverse=True)

    return {
        "week_start": week_start,
        "employees": employees_data,
        "warnings": warnings,
    }


# ==========================================================================
# HOURLY RATES (T357)
# ==========================================================================


@router.get("/hourly-rates")
async def list_hourly_rates(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List shift hourly rates for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    rates = dataflow_crud.list_records("ShiftHourlyRate", {"company_id": company_id})
    return {"hourly_rates": rates, "count": len(rates)}


@router.post("/hourly-rates")
async def create_hourly_rate(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new shift hourly rate."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_hourly_rate:{user_id}", max_requests=30, window_seconds=60, action_name="create hourly rate")

    body = await request.json()
    name = body.get("name", "").strip()
    rate = float(body.get("rate", 0))

    if not math.isfinite(rate):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")
    if not name or rate <= 0:
        raise HTTPException(status_code=400, detail="name and a positive rate are required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    record = dataflow_crud.create(
        "ShiftHourlyRate",
        {
            "company_id": company_id,
            "name": name,
            "rate": rate,
            "currency": body.get("currency", "SGD"),
            "description": body.get("description", ""),
            "is_active": True,
        },
    )
    return {"hourly_rate": record}


@router.patch("/hourly-rates/{rate_id}")
async def update_hourly_rate(
    rate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a shift hourly rate."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"update_hourly_rate:{user_id}", max_requests=30, window_seconds=60, action_name="update hourly rate")
    company_id = get_current_company_id(current_user)
    existing = dataflow_crud.read("ShiftHourlyRate", rate_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Hourly rate not found.")

    body = await request.json()
    allowed = {"name", "rate", "currency", "description", "is_active"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    dataflow_crud.update("ShiftHourlyRate", rate_id, updates)
    updated = dataflow_crud.read("ShiftHourlyRate", rate_id)
    return {"hourly_rate": updated}


# ==========================================================================
# MULTIPLIERS (T357)
# ==========================================================================


@router.get("/multipliers")
async def list_multipliers(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List shift multipliers (OT, PH, weekend rates) for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    multipliers = dataflow_crud.list_records("ShiftMultiplier", {"company_id": company_id})
    return {"multipliers": multipliers, "count": len(multipliers)}


@router.post("/multipliers")
async def create_multiplier(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a shift multiplier (e.g. 1.5x OT, 2x PH).

    Body: {name, multiplier, applies_to, description}
    applies_to: weekday_ot, weekend, public_holiday, night, custom
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_multiplier:{user_id}", max_requests=30, window_seconds=60, action_name="create multiplier")

    body = await request.json()
    name = body.get("name", "").strip()
    multiplier = float(body.get("multiplier", 0))
    applies_to = body.get("applies_to", "").strip()

    if not math.isfinite(multiplier):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")
    if not name or multiplier <= 0:
        raise HTTPException(status_code=400, detail="name and a positive multiplier are required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    valid_applies_to = {"weekday_ot", "weekend", "public_holiday", "night", "custom"}
    if applies_to and applies_to not in valid_applies_to:
        raise HTTPException(
            status_code=400,
            detail=f"applies_to must be one of: {', '.join(sorted(valid_applies_to))}.",
        )

    record = dataflow_crud.create(
        "ShiftMultiplier",
        {
            "company_id": company_id,
            "name": name,
            "multiplier": multiplier,
            "applies_to": applies_to,
            "description": body.get("description", ""),
            "is_active": True,
        },
    )
    return {"multiplier": record}


# ==========================================================================
# PUBLISH SINGLE SHIFT (T358)
# ==========================================================================


@router.post("/{shift_id}/publish")
async def publish_single_shift(
    shift_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Publish a single shift assignment (makes it visible to the employee)."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"publish_single_shift:{user_id}", max_requests=30, window_seconds=60, action_name="publish shift")
    company_id = get_current_company_id(current_user)
    existing = dataflow_crud.read("ShiftAssignment", shift_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Shift assignment not found.")

    if existing.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot publish a cancelled shift.")

    now = datetime.now(timezone.utc).isoformat()
    actor_id = int(current_user.get("sub", 0))

    dataflow_crud.update(
        "ShiftAssignment",
        shift_id,
        {
            "status": "published",
            "published_at": now,
            "published_by": actor_id,
        },
    )

    updated = dataflow_crud.read("ShiftAssignment", shift_id)
    return {"assignment": updated, "message": "Shift published."}
