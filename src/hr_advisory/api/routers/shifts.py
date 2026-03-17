"""Shift scheduling endpoints.

Handles shift templates, assignments, publishing, employee schedule views,
availability checks, and weekly hours tracking with Employment Act limits.
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

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


def _find_user_by_id(user_id: int) -> dict | None:
    return _dataflow_read("UserReadNode", user_id)


def _week_dates(week_start: str) -> list[str]:
    """Return a list of 7 date strings (Mon-Sun) starting from week_start."""
    start = date.fromisoformat(week_start)
    return [(start + timedelta(days=i)).isoformat() for i in range(7)]


def _find_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Look up the Employee record for a given user and company."""
    records = _dataflow_list(
        "EmployeeListNode",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


# --------------------------------------------------------------------------
# Shift Templates (admin only)
# --------------------------------------------------------------------------


@router.get("/templates")
async def list_shift_templates(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all shift templates for the current company."""
    company_id = get_current_company_id(current_user)
    templates = _dataflow_list("ShiftTemplateListNode", {"company_id": company_id})
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

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")

    template = _dataflow_create(
        "ShiftTemplateCreateNode",
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
    company_id = get_current_company_id(current_user)
    existing = _dataflow_read("ShiftTemplateReadNode", template_id)
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

    _dataflow_update("ShiftTemplateUpdateNode", template_id, updates)
    updated = _dataflow_read("ShiftTemplateReadNode", template_id)
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
        day_assignments = _dataflow_list(
            "ShiftAssignmentListNode",
            {"company_id": company_id, "date": d},
        )
        all_assignments.extend(day_assignments)

    # Fetch employees (optionally filtered by department)
    emp_filter: dict = {"company_id": company_id, "is_active": True}
    if department:
        emp_filter["department"] = department
    employees = _dataflow_list("EmployeeListNode", emp_filter)

    # Fetch templates for enrichment
    templates = _dataflow_list("ShiftTemplateListNode", {"company_id": company_id})
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

    return {
        "week_start": week_start,
        "dates": dates,
        "schedule": list(grid.values()),
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
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Verify template belongs to company
    template = _dataflow_read("ShiftTemplateReadNode", shift_template_id)
    if template is None or template.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Shift template not found.")

    assignment = _dataflow_create(
        "ShiftAssignmentCreateNode",
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
    company_id = get_current_company_id(current_user)
    existing = _dataflow_read("ShiftAssignmentReadNode", assignment_id)
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

    _dataflow_update("ShiftAssignmentUpdateNode", assignment_id, updates)
    updated = _dataflow_read("ShiftAssignmentReadNode", assignment_id)
    return {"assignment": updated}


@router.delete("/assignments/{assignment_id}")
async def cancel_shift_assignment(
    assignment_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Cancel a shift assignment (soft-cancel by setting status to cancelled)."""
    company_id = get_current_company_id(current_user)
    existing = _dataflow_read("ShiftAssignmentReadNode", assignment_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Shift assignment not found.")

    _dataflow_update("ShiftAssignmentUpdateNode", assignment_id, {"status": "cancelled"})
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

    body = await request.json()
    week_start = body.get("week_start", "")
    if not week_start:
        raise HTTPException(status_code=400, detail="week_start is required.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    record = _dataflow_create(
        "ShiftPublishCreateNode",
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
    templates = _dataflow_list("ShiftTemplateListNode", {"company_id": company_id})
    template_map = {t["id"]: t for t in templates}

    shifts = []
    for d in dates:
        day_assignments = _dataflow_list(
            "ShiftAssignmentListNode",
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
    employees = _dataflow_list("EmployeeListNode", emp_filter)

    # Fetch approved leave applications for this company
    leave_apps = _dataflow_list(
        "LeaveApplicationListNode",
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
    day_assignments = _dataflow_list(
        "ShiftAssignmentListNode",
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
        day_assignments = _dataflow_list(
            "ShiftAssignmentListNode",
            {"company_id": company_id, "date": d},
        )
        all_assignments.extend(a for a in day_assignments if a.get("status") != "cancelled")

    # Fetch templates for work_hours lookup
    templates = _dataflow_list("ShiftTemplateListNode", {"company_id": company_id})
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
        emp_records = _dataflow_list("EmployeeListNode", {"id": emp_id}, limit=1)
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
