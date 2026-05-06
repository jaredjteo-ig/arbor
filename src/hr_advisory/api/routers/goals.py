"""Goals / OKR router — P2-GO obayashi.

Endpoints:
  GET   /goals?employee_id=N&status=X
  POST  /goals
  GET   /goals/{id}
  PATCH /goals/{id}
  DELETE /goals/{id}                  (soft-archive)
  GET   /goals/{id}/checkins
  POST  /goals/{id}/checkins

Status state machine (enforced in PATCH):
  draft → active
  active ↔ at_risk
  active|at_risk → done | cancelled
  done | cancelled = terminal
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import (
    get_current_user,
    require_role,
)
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.api.routers._helpers import _resolve_user_names
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"draft", "active", "cancelled"},
    "active": {"active", "at_risk", "done", "cancelled"},
    "at_risk": {"at_risk", "active", "done", "cancelled"},
    "done": {"done"},
    "cancelled": {"cancelled"},
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _verify_goal(goal_id: int, company_id: int) -> dict:
    rows = dataflow_crud.list_records(
        "Goal", {"id": goal_id, "company_id": company_id}, cache_ttl=0
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Goal not found.")
    return rows[0]


def _is_admin(user: dict) -> bool:
    return user.get("role") in ("owner", "hr_manager")


def _employee_for_user(user_id: int, company_id: int) -> dict | None:
    rows = dataflow_crud.list_records(
        "Employee",
        {"user_id": user_id, "company_id": company_id},
        cache_ttl=0,
    )
    return rows[0] if rows else None


def _verify_goal_in_scope(goal_id: int, current_user: dict) -> dict:
    """Round-12 redteam H1: get/patch/checkin must enforce the same scope
    filter as list — admin sees all, manager sees own + direct reports,
    employee sees only own. Without this guard, a non-admin employee
    could read or write any goal in their company by guessing the ID.

    404 (not 403) on out-of-scope to avoid ID enumeration.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    goal = _verify_goal(goal_id, company_id)

    if _is_admin(current_user):
        return goal

    user_id = int(current_user.get("sub", 0))
    my_emp = _employee_for_user(user_id, company_id)
    my_emp_id = my_emp.get("id") if my_emp else None
    if goal.get("employee_id") == my_emp_id:
        return goal
    # Direct reports — manager scope.
    if my_emp_id:
        reports = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id, "reporting_manager_id": my_emp_id},
            cache_ttl=0,
        )
        report_ids = {r.get("id") for r in reports if r.get("id")}
        if goal.get("employee_id") in report_ids:
            return goal

    raise HTTPException(status_code=404, detail="Goal not found.")


@router.get("")
async def list_goals(
    employee_id: int | None = None,
    status: str | None = None,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    rows = dataflow_crud.list_records(
        "Goal", {"company_id": company_id}, cache_ttl=0
    )
    if not include_archived:
        rows = [r for r in rows if not r.get("is_archived")]

    # Scope: admin sees all; manager sees their reports + own; employee
    # sees only their own.
    if not _is_admin(current_user):
        my_emp = _employee_for_user(user_id, company_id)
        my_emp_id = my_emp.get("id") if my_emp else None
        # Direct reports
        my_reports_ids: set[int] = set()
        if my_emp_id:
            reports = dataflow_crud.list_records(
                "Employee",
                {"company_id": company_id, "reporting_manager_id": my_emp_id},
                cache_ttl=0,
            )
            my_reports_ids = {r.get("id") for r in reports if r.get("id")}
        rows = [
            r
            for r in rows
            if r.get("employee_id") == my_emp_id
            or r.get("employee_id") in my_reports_ids
        ]

    if employee_id is not None:
        rows = [r for r in rows if r.get("employee_id") == employee_id]
    if status:
        rows = [r for r in rows if r.get("status") == status]

    rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return {"goals": rows, "count": len(rows)}


@router.post("")
async def create_goal(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"goal_create:{user_id}",
        max_requests=30,
        window_seconds=3600,
        action_name="create goal",
    )

    body = await request.json()
    employee_id = body.get("employee_id")
    title = (body.get("title") or "").strip()
    if not employee_id or not title:
        raise HTTPException(
            status_code=400, detail="employee_id and title are required."
        )

    # Tenant + scope guard. Non-admin can only create goals for themselves.
    if not _is_admin(current_user):
        my_emp = _employee_for_user(user_id, company_id)
        if not my_emp or my_emp.get("id") != int(employee_id):
            raise HTTPException(
                status_code=403,
                detail="Employees can only create their own goals.",
            )

    target = dataflow_crud.list_records(
        "Employee",
        {"id": int(employee_id), "company_id": company_id},
        cache_ttl=0,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Employee not found.")

    now = _now()
    record = dataflow_crud.create(
        "Goal",
        {
            "company_id": company_id,
            "employee_id": int(employee_id),
            "manager_id": int(body.get("manager_id") or 0),
            "period_id": int(body.get("period_id") or 0),
            "title": title,
            "description": body.get("description") or "",
            "metric": body.get("metric") or "",
            "target_value": body.get("target_value") or "",
            "start_date": body.get("start_date") or "",
            "due_date": body.get("due_date") or "",
            "status": body.get("status", "draft"),
            "progress_pct": int(body.get("progress_pct") or 0),
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"goal": record}


@router.get("/{goal_id}")
async def get_goal(
    goal_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    goal = _verify_goal_in_scope(goal_id, current_user)
    return {"goal": goal}


@router.patch("/{goal_id}")
async def update_goal(
    goal_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    goal = _verify_goal_in_scope(goal_id, current_user)

    body = await request.json()
    allowed = {
        "title",
        "description",
        "metric",
        "target_value",
        "start_date",
        "due_date",
        "manager_id",
        "period_id",
        "status",
        "progress_pct",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    if "status" in updates:
        old_status = goal.get("status", "draft")
        new_status = updates["status"]
        valid = VALID_STATUS_TRANSITIONS.get(old_status, set())
        if new_status not in valid:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition status from {old_status!r} to {new_status!r}.",
            )
        if new_status == "done":
            updates["progress_pct"] = 100

    if "progress_pct" in updates:
        pct = int(updates["progress_pct"])
        if pct < 0 or pct > 100:
            raise HTTPException(
                status_code=400, detail="progress_pct must be 0..100"
            )
        updates["progress_pct"] = pct

    updates["updated_at"] = _now()
    dataflow_crud.update("Goal", goal_id, updates)
    return {"goal": dataflow_crud.read("Goal", goal_id)}


@router.delete("/{goal_id}")
async def archive_goal(
    goal_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    _verify_goal(goal_id, company_id)
    dataflow_crud.update(
        "Goal", goal_id, {"is_archived": True, "updated_at": _now()}
    )
    return {"message": "Goal archived.", "id": goal_id}


@router.get("/{goal_id}/checkins")
async def list_checkins(
    goal_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _verify_goal_in_scope(goal_id, current_user)
    company_id = get_current_company_id(current_user)
    rows = dataflow_crud.list_records(
        "GoalCheckIn",
        {"goal_id": goal_id, "company_id": company_id},
        cache_ttl=0,
    )
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)

    # Resolve actor_user_id → User.name so the timeline never says "User #N".
    actor_ids = {
        r.get("actor_user_id") for r in rows if r.get("actor_user_id")
    }
    name_map = _resolve_user_names(actor_ids, company_id)
    for r in rows:
        r["actor_name"] = name_map.get(r.get("actor_user_id"), "")

    return {"checkins": rows, "count": len(rows)}


@router.post("/{goal_id}/checkins")
async def add_checkin(
    goal_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    goal = _verify_goal_in_scope(goal_id, current_user)
    company_id = get_current_company_id(current_user)

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"goal_checkin:{user_id}",
        max_requests=20,
        window_seconds=3600,
        action_name="goal check-in",
    )

    body = await request.json()
    pct = int(body.get("progress_pct") or 0)
    note = (body.get("note") or "").strip()
    if pct < 0 or pct > 100:
        raise HTTPException(
            status_code=400, detail="progress_pct must be 0..100"
        )

    now = _now()
    record = dataflow_crud.create(
        "GoalCheckIn",
        {
            "goal_id": goal_id,
            "company_id": company_id,
            "actor_user_id": user_id,
            "progress_pct": pct,
            "note": note,
            "created_at": now,
        },
    )
    # Mirror the latest progress on the parent goal.
    new_status = goal.get("status", "draft")
    if pct >= 100 and new_status not in ("done", "cancelled"):
        new_status = "done"
    elif new_status == "draft":
        new_status = "active"
    dataflow_crud.update(
        "Goal",
        goal_id,
        {"progress_pct": pct, "status": new_status, "updated_at": now},
    )
    return {"checkin": record}
