"""Project costing and timesheet endpoints.

Handles projects, employee assignments, roles, overheads,
timesheet entries, allocations, cost calculations, and reports.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

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


def _get_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Resolve the Employee record for a given user_id + company_id."""
    records = dataflow_crud.list_records("Employee",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


def _verify_project_ownership(project_id: int, company_id: int) -> dict:
    """Load a project and verify tenant ownership. Raises 404 on failure."""
    project = dataflow_crud.read("Project", project_id)
    if not project or project.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


# --------------------------------------------------------------------------
# Projects CRUD
# --------------------------------------------------------------------------


@router.get("/")
async def list_projects(
    status: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all projects for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status
    projects = dataflow_crud.list_records("Project", filters)
    return {"projects": projects, "count": len(projects)}


@router.post("/")
async def create_project(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    budget_amount = float(body.get("budget_amount", body.get("budget", 0.0)))
    if not math.isfinite(budget_amount):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")

    project = dataflow_crud.create("Project",
        {
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
            "start_date": body.get("start_date", ""),
            "end_date": body.get("end_date", ""),
            "budget_amount": budget_amount,
            "is_archived": False,
        },
    )
    return {"project": project}


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a single project by ID."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    project = _verify_project_ownership(project_id, company_id)
    return {"project": project}


@router.patch("/{project_id}")
async def update_project(
    project_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)

    body = await request.json()
    allowed = {
        "name",
        "description",
        "start_date",
        "end_date",
        "budget_amount",
        "status",
        "is_archived",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("Project", project_id, updates)
    return {"project": result}


@router.delete("/{project_id}")
async def archive_project(
    project_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Soft-delete (archive) a project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)
    dataflow_crud.update("Project", project_id, {"status": "archived"})
    return {"detail": "Project archived."}


# --------------------------------------------------------------------------
# Assignments
# --------------------------------------------------------------------------


@router.get("/{project_id}/assignments")
async def list_assignments(
    project_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List employee assignments for a project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)
    assignments = dataflow_crud.list_records("ProjectAssignment",
        {"project_id": project_id},
    )
    return {"assignments": assignments, "count": len(assignments)}


@router.post("/{project_id}/assignments")
async def assign_employees(
    project_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Assign employees to a project (bulk).

    Body: {"assignments": [{"employee_id": 1, "role_id": 2, "hourly_rate": 50.0}, ...]}
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)

    body = await request.json()
    assignment_list = body.get("assignments", [])
    if not assignment_list:
        raise HTTPException(status_code=400, detail="assignments list is required.")

    created = []
    actor_id = int(current_user.get("sub", 0))
    for item in assignment_list:
        employee_id = item.get("employee_id")
        if not employee_id:
            continue
        hourly_rate = float(item.get("hourly_rate", 0.0))
        if not math.isfinite(hourly_rate):
            raise HTTPException(status_code=400, detail="Invalid numeric value.")
        assignment = dataflow_crud.create("ProjectAssignment",
            {
                "project_id": project_id,
                "employee_id": employee_id,
                "role_id": item.get("role_id"),
                "hourly_rate": hourly_rate,
                "start_date": item.get("start_date", ""),
                "end_date": item.get("end_date", ""),
                "created_by": actor_id,
            },
        )
        created.append(assignment)

    return {"assignments": created, "count": len(created)}


@router.delete("/{project_id}/assignments/{assignment_id}")
async def unassign_employee(
    project_id: int,
    assignment_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Remove an employee assignment from a project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)

    existing = dataflow_crud.read("ProjectAssignment", assignment_id)
    if not existing or existing.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    dataflow_crud.delete("ProjectAssignment", assignment_id)
    return {"detail": "Assignment removed."}


# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------


@router.get("/roles")
async def list_project_roles(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List project roles for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    roles = dataflow_crud.list_records("ProjectRole", {"company_id": company_id})
    return {"roles": roles, "count": len(roles)}


@router.post("/roles")
async def create_project_role(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new project role."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Role name is required.")

    role = dataflow_crud.create("ProjectRole",
        {
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
            "default_hourly_rate": body.get("default_hourly_rate", 0.0),
        },
    )
    return {"role": role}


@router.patch("/roles/{role_id}")
async def update_project_role(
    role_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a project role."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("ProjectRole", role_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Role not found.")

    body = await request.json()
    allowed = {"name", "description", "default_hourly_rate"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = dataflow_crud.update("ProjectRole", role_id, updates)
    return {"role": result}


# --------------------------------------------------------------------------
# Overheads
# --------------------------------------------------------------------------


@router.get("/{project_id}/overheads")
async def list_overheads(
    project_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List overheads for a project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)
    overheads = dataflow_crud.list_records("ProjectOverhead", {"project_id": project_id})
    return {"overheads": overheads, "count": len(overheads)}


@router.post("/{project_id}/overheads")
async def add_overhead(
    project_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add an overhead cost to a project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)

    body = await request.json()
    name = body.get("name", "").strip()
    amount = body.get("amount", 0.0)
    if not name:
        raise HTTPException(status_code=400, detail="Overhead name is required.")

    overhead = dataflow_crud.create("ProjectOverhead",
        {
            "project_id": project_id,
            "name": name,
            "description": body.get("description", ""),
            "amount": amount,
            "overhead_type": body.get("overhead_type", "fixed"),
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"overhead": overhead}


@router.patch("/{project_id}/overheads/{overhead_id}")
async def update_overhead(
    project_id: int,
    overhead_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an overhead cost."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)

    existing = dataflow_crud.read("ProjectOverhead", overhead_id)
    if not existing or existing.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Overhead not found.")

    body = await request.json()
    allowed = {"name", "description", "amount", "overhead_type"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = dataflow_crud.update("ProjectOverhead", overhead_id, updates)
    return {"overhead": result}


@router.delete("/{project_id}/overheads/{overhead_id}")
async def delete_overhead(
    project_id: int,
    overhead_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete an overhead cost."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_project_ownership(project_id, company_id)

    existing = dataflow_crud.read("ProjectOverhead", overhead_id)
    if not existing or existing.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Overhead not found.")

    dataflow_crud.delete("ProjectOverhead", overhead_id)
    return {"detail": "Overhead deleted."}


# --------------------------------------------------------------------------
# Timesheets
# --------------------------------------------------------------------------


@router.post("/timesheets/entries")
async def create_timesheet_entry(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a timesheet entry.

    Employees can create their own entries; HR/owners can create for anyone.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    project_id = body.get("project_id")
    entry_date = body.get("date", "")
    hours = body.get("hours", 0.0)

    if not project_id or not entry_date or hours <= 0:
        raise HTTPException(
            status_code=400, detail="project_id, date, and hours (>0) are required."
        )

    _verify_project_ownership(project_id, company_id)

    role = current_user.get("role", "employee")
    user_id = int(current_user.get("sub", 0))
    employee_id = body.get("employee_id")

    if role not in ("owner", "hr_manager"):
        emp = _get_employee_for_user(user_id, company_id)
        if not emp:
            raise HTTPException(status_code=403, detail="Employee record not found.")
        employee_id = emp.get("id")
    elif not employee_id:
        emp = _get_employee_for_user(user_id, company_id)
        employee_id = emp.get("id") if emp else None

    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id is required.")

    entry = dataflow_crud.create("TimesheetEntry",
        {
            "project_id": project_id,
            "employee_id": employee_id,
            "date": entry_date,
            "hours": hours,
            "description": body.get("description", ""),
            "task": body.get("task", ""),
            "created_by": user_id,
        },
    )
    return {"entry": entry}


@router.get("/timesheets")
async def list_timesheet_entries(
    project_id: int | None = Query(None),
    employee_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List timesheet entries with optional filters.

    Employees see only their own entries unless they are HR/owner.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    user_id = int(current_user.get("sub", 0))

    filters: dict = {"company_id": company_id}  # Always include tenant isolation
    if project_id:
        filters["project_id"] = project_id
    if employee_id and role in ("owner", "hr_manager"):
        filters["employee_id"] = employee_id
    elif role not in ("owner", "hr_manager"):
        emp = _get_employee_for_user(user_id, company_id)
        if emp:
            filters["employee_id"] = emp.get("id")

    entries = dataflow_crud.list_records("TimesheetEntry", filters)

    # Client-side date filtering (DataFlow may not support range queries directly)
    if date_from:
        entries = [e for e in entries if e.get("date", "") >= date_from]
    if date_to:
        entries = [e for e in entries if e.get("date", "") <= date_to]

    return {"entries": entries, "count": len(entries)}


@router.put("/timesheets/entries/{entry_id}")
async def update_timesheet_entry(
    entry_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update a timesheet entry."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("TimesheetEntry", entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found.")

    # Verify tenant isolation
    if existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Entry not found.")

    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _get_employee_for_user(user_id, company_id)
        if not emp or emp.get("id") != existing.get("employee_id"):
            raise HTTPException(status_code=403, detail="Access denied.")

    body = await request.json()
    allowed = {"hours", "description", "task", "date"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("TimesheetEntry", entry_id, updates)
    return {"entry": result}


@router.delete("/timesheets/entries/{entry_id}")
async def delete_timesheet_entry(
    entry_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Delete a timesheet entry."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("TimesheetEntry", entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found.")

    # Verify tenant isolation
    if existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Entry not found.")

    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _get_employee_for_user(user_id, company_id)
        if not emp or emp.get("id") != existing.get("employee_id"):
            raise HTTPException(status_code=403, detail="Access denied.")

    dataflow_crud.delete("TimesheetEntry", entry_id)
    return {"detail": "Entry deleted."}


# --------------------------------------------------------------------------
# Allocations
# --------------------------------------------------------------------------


@router.get("/allocations")
async def list_allocations(
    project_id: int | None = Query(None),
    employee_id: int | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List resource allocations."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if project_id:
        filters["project_id"] = project_id
    if employee_id:
        filters["employee_id"] = employee_id

    allocations = dataflow_crud.list_records("ProjectAllocation", filters)
    return {"allocations": allocations, "count": len(allocations)}


@router.post("/allocations")
async def create_allocation(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a resource allocation."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    project_id = body.get("project_id")
    employee_id = body.get("employee_id")
    percentage = body.get("percentage", 100)

    if not project_id or not employee_id:
        raise HTTPException(status_code=400, detail="project_id and employee_id are required.")

    _verify_project_ownership(project_id, company_id)

    allocation = dataflow_crud.create("ProjectAllocation",
        {
            "company_id": company_id,
            "project_id": project_id,
            "employee_id": employee_id,
            "percentage": percentage,
            "start_date": body.get("start_date", ""),
            "end_date": body.get("end_date", ""),
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"allocation": allocation}


# --------------------------------------------------------------------------
# Cost calculation & reports
# --------------------------------------------------------------------------


@router.post("/calculate")
async def calculate_project_costs(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate cost calculations for a project.

    Sums labour costs (timesheet hours * hourly rates) + overheads.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required.")

    project = _verify_project_ownership(project_id, company_id)

    # Fetch timesheet entries
    entries = dataflow_crud.list_records("TimesheetEntry", {"project_id": project_id})

    # Fetch assignments for hourly rates
    assignments = dataflow_crud.list_records("ProjectAssignment", {"project_id": project_id})
    rate_map: dict[int, float] = {}
    for a in assignments:
        rate_map[a.get("employee_id", 0)] = a.get("hourly_rate", 0.0)

    # Calculate labour costs
    total_hours = 0.0
    labour_cost = 0.0
    employee_costs: dict[int, dict] = {}
    for entry in entries:
        emp_id = entry.get("employee_id", 0)
        hours = entry.get("hours", 0.0)
        rate = rate_map.get(emp_id, 0.0)
        cost = hours * rate
        total_hours += hours
        labour_cost += cost
        if emp_id not in employee_costs:
            employee_costs[emp_id] = {"employee_id": emp_id, "hours": 0.0, "cost": 0.0}
        employee_costs[emp_id]["hours"] += hours
        employee_costs[emp_id]["cost"] += cost

    # Fetch overheads
    overheads = dataflow_crud.list_records("ProjectOverhead", {"project_id": project_id})
    overhead_total = sum(o.get("amount", 0.0) for o in overheads)

    total_cost = labour_cost + overhead_total
    budget = project.get("budget", 0.0)

    return {
        "project_id": project_id,
        "total_hours": round(total_hours, 2),
        "labour_cost": round(labour_cost, 2),
        "overhead_cost": round(overhead_total, 2),
        "total_cost": round(total_cost, 2),
        "budget": round(budget, 2),
        "variance": round(budget - total_cost, 2),
        "employee_breakdown": list(employee_costs.values()),
        "overheads": overheads,
    }


@router.get("/report")
async def project_report(
    project_id: int = Query(...),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate a summary report for a project."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    project = _verify_project_ownership(project_id, company_id)

    assignments = dataflow_crud.list_records("ProjectAssignment", {"project_id": project_id})
    entries = dataflow_crud.list_records("TimesheetEntry", {"project_id": project_id})
    overheads = dataflow_crud.list_records("ProjectOverhead", {"project_id": project_id})

    total_hours = sum(e.get("hours", 0.0) for e in entries)
    overhead_total = sum(o.get("amount", 0.0) for o in overheads)

    return {
        "project": project,
        "total_employees": len(assignments),
        "total_hours": round(total_hours, 2),
        "total_entries": len(entries),
        "overhead_total": round(overhead_total, 2),
    }
