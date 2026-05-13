"""Appraisal management endpoints.

Handles appraisal templates, periods, individual appraisals,
scoring, submission, and employee sign-off.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

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

from hr_advisory.services import dataflow_crud, manager_scope


def _get_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Resolve the Employee record for a given user_id + company_id."""
    records = dataflow_crud.list_records(
        "Employee",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


def _audit_appraisal(
    appraisal_id: int,
    company_id: int,
    action: str,
    actor_id: int,
    details: dict | None = None,
) -> None:
    """Append a hash-chained audit entry for an appraisal action.

    Modelled on `_audit_claim`. Writes to the immutable AuditLogEntry
    so `reviewed_by`/`reviewed_at` on the record (mutable via
    `dataflow_crud.update`) can be independently verified against
    the append-only chain. Failures are logged but do NOT block
    the user action. Origin: red-team round-2 P1 finding.
    """
    try:
        from hr_advisory.services import audit_log as _audit_log

        _audit_log.record_event(
            company_id=int(company_id),
            actor_id=int(actor_id) if actor_id else 0,
            event_type=f"appraisal.{action}",
            payload={"appraisal_id": appraisal_id, "details": details or {}},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "AuditLogEntry append failed for appraisal %s action=%s: %s",
            appraisal_id,
            action,
            exc,
        )


def _enrich_appraisals(appraisals: list, company_id: int) -> list:
    """Enrich appraisal records with employee_name (resolved via Employee.user_id → User.name).

    Mirrors the bulk-lookup pattern from leave.py to avoid N+1 queries.
    """
    if not appraisals:
        return appraisals

    employee_ids = {
        a.get("employee_id") for a in appraisals if a.get("employee_id")
    }

    emp_name_map: dict[int, str] = {}
    if employee_ids:
        employees = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id},
        )
        # Build employee_id -> user_id and reverse-lookup names from User
        uid_to_eids: dict[int, list[int]] = {}
        for emp in employees:
            eid = emp.get("id")
            if eid in employee_ids:
                uid = emp.get("user_id")
                if uid:
                    uid_to_eids.setdefault(uid, []).append(eid)
        if uid_to_eids:
            users = dataflow_crud.list_records(
                "User", {"company_id": company_id}
            )
            for user in users:
                uid = user.get("id")
                if uid in uid_to_eids:
                    name = user.get("name", "")
                    for eid in uid_to_eids[uid]:
                        emp_name_map[eid] = name

    for a in appraisals:
        a["employee_name"] = emp_name_map.get(a.get("employee_id"), "")

    return appraisals


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------


@router.get("/templates")
async def list_templates(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all appraisal templates for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    templates = dataflow_crud.list_records(
        "AppraisalTemplate",
        {"company_id": company_id, "is_archived": False},
    )
    return {"templates": templates, "count": len(templates)}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a single appraisal template by ID."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    template = dataflow_crud.read("AppraisalTemplate", template_id)
    if not template or template.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Template not found.")

    return template


@router.post("/templates")
async def create_template(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new appraisal template."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_appraisal_template:{user_id}", max_requests=30, window_seconds=60, action_name="create appraisal template")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Template name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    template = dataflow_crud.create(
        "AppraisalTemplate",
        {
            "company_id": company_id,
            "name": name,
            "sections": body.get("sections", "[]"),
            "enable_weightage": body.get("enable_weightage", True),
            "require_employee_signoff": body.get("require_employee_signoff", True),
            "is_archived": False,
        },
    )
    return {"template": template}


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an appraisal template."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = current_user.get("sub")
    check_rate_limit(
        f"update_appraisal_template:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="update appraisal template",
    )

    existing = dataflow_crud.read("AppraisalTemplate", template_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Template not found.")

    body = await request.json()
    allowed = {"name", "sections", "enable_weightage", "require_employee_signoff"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("AppraisalTemplate", template_id, updates)
    return {"template": result}


@router.delete("/templates/{template_id}")
async def archive_template(
    template_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Soft-delete (archive) an appraisal template."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = current_user.get("sub")
    check_rate_limit(
        f"archive_appraisal_template:{user_id}",
        max_requests=20,
        window_seconds=60,
        action_name="archive appraisal template",
    )

    existing = dataflow_crud.read("AppraisalTemplate", template_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Template not found.")

    dataflow_crud.update("AppraisalTemplate", template_id, {"is_archived": True})
    return {"detail": "Template archived."}


# --------------------------------------------------------------------------
# Periods
# --------------------------------------------------------------------------


@router.get("/periods")
async def list_periods(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List appraisal periods for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    periods = dataflow_crud.list_records(
        "AppraisalPeriod",
        {"company_id": company_id},
    )
    return {"periods": periods, "count": len(periods)}


@router.post("/periods")
async def create_period(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new appraisal period."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_appraisal_period:{user_id}", max_requests=30, window_seconds=60, action_name="create appraisal period")

    body = await request.json()
    name = body.get("name", "").strip()
    start_date = body.get("start_date", "")
    end_date = body.get("end_date", "")
    template_id = body.get("template_id")

    if not name or not start_date or not end_date:
        raise HTTPException(
            status_code=400, detail="name, start_date, and end_date are required."
        )

    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    period = dataflow_crud.create(
        "AppraisalPeriod",
        {
            "company_id": company_id,
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "template_id": template_id,
            "status": "draft",
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"period": period}


@router.patch("/periods/{period_id}")
async def update_period(
    period_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an appraisal period."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = current_user.get("sub")
    check_rate_limit(
        f"update_appraisal_period:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="update appraisal period",
    )

    existing = dataflow_crud.read("AppraisalPeriod", period_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Period not found.")

    body = await request.json()
    allowed = {"name", "start_date", "end_date", "template_id"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("AppraisalPeriod", period_id, updates)
    return {"period": result}


@router.post("/periods/{period_id}/launch")
async def launch_period(
    period_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Launch an appraisal period: create Appraisal records for all active employees."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"launch_appraisal_period:{user_id}", max_requests=30, window_seconds=60, action_name="launch appraisal period")

    period = dataflow_crud.read("AppraisalPeriod", period_id)
    if not period or period.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Period not found.")

    if period.get("status") not in ("draft",):
        raise HTTPException(
            status_code=400, detail="Period must be in draft status to launch."
        )

    employees = dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "is_active": True},
    )
    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found.")

    created = []
    actor_id = int(current_user.get("sub", 0))
    for emp in employees:
        appraisal = dataflow_crud.create(
            "Appraisal",
            {
                "company_id": company_id,
                "period_id": period_id,
                "employee_id": emp.get("id"),
                "template_id": period.get("template_id"),
                "status": "pending",
                "created_by": actor_id,
            },
        )
        created.append(appraisal)

    # Move period to in_progress (matches seed + UI badge label)
    dataflow_crud.update("AppraisalPeriod", period_id, {"status": "in_progress"})

    return {
        "detail": f"Launched {len(created)} appraisals.",
        "appraisals_created": len(created),
    }


@router.post("/periods/{period_id}/close")
async def close_period(
    period_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Close an in-progress appraisal period (mark it completed)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"close_appraisal_period:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="close appraisal period",
    )

    period = dataflow_crud.read("AppraisalPeriod", period_id)
    if not period or period.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Period not found.")

    if period.get("status") not in ("in_progress", "active"):
        raise HTTPException(
            status_code=400,
            detail="Period must be in progress to close.",
        )

    result = dataflow_crud.update(
        "AppraisalPeriod",
        period_id,
        {"status": "completed"},
    )
    return {"period": result}


# --------------------------------------------------------------------------
# List appraisals (for current user or all for admins)
# --------------------------------------------------------------------------


@router.get("/my")
async def list_my_appraisals(
    period_id: int | None = Query(None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List appraisals for the current user.

    Employees see only their own; HR/owners see all for the company.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    filters: dict = {"company_id": company_id}

    if period_id:
        filters["period_id"] = period_id

    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _get_employee_for_user(user_id, company_id)
        if emp:
            filters["employee_id"] = emp.get("id")
        else:
            return {"appraisals": [], "count": 0}

    appraisals = dataflow_crud.list_records("Appraisal", filters)
    appraisals = _enrich_appraisals(appraisals, company_id)
    return {"appraisals": appraisals, "count": len(appraisals)}


# --------------------------------------------------------------------------
# Manager review queue (P4-MG-4)
#
# IMPORTANT: this route must be declared BEFORE `/{appraisal_id}` so
# FastAPI's path matcher doesn't try to coerce the literal string
# `to-review` into an int and 422 the request.
# --------------------------------------------------------------------------


@router.get("/to-review")
async def list_appraisals_to_review(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List submitted appraisals awaiting the caller's manager review.

    Scope (P4-MG-4):
    - Line managers see appraisals from their direct reports in
      `status == 'submitted'`.
    - Owners + HR managers see every submitted appraisal company-wide
      (they act as the de-facto reviewer for skip-level ICs or
      owner-direct reports).
    - Regular employees with no reports get an empty list — not a
      403, so a `/team` page surfacing the count renders cleanly
      for ICs too.

    Returns Appraisal shape enriched with `employee_name` and
    `period_name` so the FE can render the queue without N+1 fetches.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    submitted = dataflow_crud.list_records(
        "Appraisal",
        {"company_id": company_id, "status": "submitted"},
    )

    if role in ("owner", "hr_manager"):
        in_scope = submitted
    else:
        team_ids = manager_scope.get_managed_employee_ids(
            current_user, active_only=True
        )
        if not team_ids:
            return {"appraisals": [], "count": 0}
        in_scope = [a for a in submitted if a.get("employee_id") in team_ids]

    out: list[dict] = []
    for app in in_scope:
        emp_id = app.get("employee_id")
        period_id = app.get("appraisal_period_id")
        emp_name = ""
        if emp_id:
            emps = dataflow_crud.list_records(
                "Employee", {"id": emp_id, "company_id": company_id}, limit=1
            )
            if emps and emps[0].get("user_id"):
                users = dataflow_crud.list_records(
                    "User", {"id": emps[0]["user_id"]}, limit=1
                )
                if users:
                    emp_name = users[0].get("name", "")
        period_name = ""
        if period_id:
            periods = dataflow_crud.list_records(
                "AppraisalPeriod",
                {"id": period_id, "company_id": company_id},
                limit=1,
            )
            if periods:
                period_name = periods[0].get("name", "")
        out.append(
            {**app, "employee_name": emp_name, "period_name": period_name}
        )

    out.sort(key=lambda a: a.get("submitted_at", ""), reverse=True)
    return {"appraisals": out, "count": len(out)}


# --------------------------------------------------------------------------
# Individual appraisals
# --------------------------------------------------------------------------


@router.get("/{appraisal_id}")
async def get_appraisal(
    appraisal_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get an individual appraisal.

    Read scope (P4-MG-4):
    - Owners + HR managers see any appraisal in the company.
    - The appraised employee sees their own.
    - The direct line-manager of the appraised employee sees it too,
      so managers can read submissions before clicking through to
      the manager-review form.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    appraisal = dataflow_crud.read("Appraisal", appraisal_id)
    if not appraisal or appraisal.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Appraisal not found.")

    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _get_employee_for_user(user_id, company_id)
        target_emp_id = appraisal.get("employee_id")
        is_own = bool(emp and emp.get("id") == target_emp_id)
        is_manager = (
            target_emp_id is not None
            and manager_scope.is_manager_of(current_user, int(target_emp_id))
        )
        if not (is_own or is_manager):
            raise HTTPException(status_code=403, detail="Access denied.")

    return {"appraisal": appraisal}


@router.put("/{appraisal_id}")
async def update_appraisal(
    appraisal_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update an appraisal (responses, scores, comments).

    Employees can update their own pending appraisals; HR/owners can update any.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = current_user.get("sub")
    check_rate_limit(
        f"update_appraisal:{user_id}",
        max_requests=60,
        window_seconds=60,
        action_name="update appraisal",
    )

    appraisal = dataflow_crud.read("Appraisal", appraisal_id)
    if not appraisal or appraisal.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Appraisal not found.")

    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _get_employee_for_user(user_id, company_id)
        if not emp or emp.get("id") != appraisal.get("employee_id"):
            raise HTTPException(status_code=403, detail="Access denied.")
        if appraisal.get("status") not in ("pending", "in_progress"):
            raise HTTPException(
                status_code=400, detail="Appraisal is not editable in current status."
            )

    body = await request.json()
    allowed = {"responses", "scores", "overall_score", "reviewer_comments", "employee_comments"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    if appraisal.get("status") == "pending":
        updates["status"] = "in_progress"
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = dataflow_crud.update("Appraisal", appraisal_id, updates)
    return {"appraisal": result}


@router.post("/{appraisal_id}/submit")
async def submit_appraisal(
    appraisal_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit an appraisal for review.

    Employees submit their own; HR can submit on behalf.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"submit_appraisal:{user_id}", max_requests=30, window_seconds=60, action_name="submit appraisal")

    appraisal = dataflow_crud.read("Appraisal", appraisal_id)
    if not appraisal or appraisal.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Appraisal not found.")

    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _get_employee_for_user(user_id, company_id)
        if not emp or emp.get("id") != appraisal.get("employee_id"):
            raise HTTPException(status_code=403, detail="Access denied.")

    if appraisal.get("status") not in ("pending", "in_progress"):
        raise HTTPException(
            status_code=400, detail="Appraisal must be pending or in_progress to submit."
        )

    result = dataflow_crud.update(
        "Appraisal",
        appraisal_id,
        {
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"appraisal": result, "detail": "Appraisal submitted."}


@router.post("/{appraisal_id}/manager-review")
async def manager_review_appraisal(
    appraisal_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Manager submits their review of a direct report's appraisal.

    Transitions `status: submitted → reviewed`. Records the reviewer
    (manager) and timestamp. Reviewer comments + overall_score may
    be passed in the body.

    Scope (P4-MG-4):
    - Owners + HR managers may review any submitted appraisal.
    - Line managers may review their direct reports' appraisals.
    - Anyone else: 403.
    - Self-review is denied — an employee cannot review their own
      appraisal even if they manage themselves through a data bug
      (the manager_scope helper already screens self-references,
      but the explicit guard belt-and-braces it here).
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"manager_review_appraisal:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="manager review appraisal",
    )

    appraisal = dataflow_crud.read("Appraisal", appraisal_id)
    if not appraisal or appraisal.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Appraisal not found.")

    target_emp_id = appraisal.get("employee_id")

    # Self-review guard
    emp = _get_employee_for_user(user_id, company_id)
    if emp and emp.get("id") == target_emp_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot review your own appraisal.",
        )

    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        if not target_emp_id or not manager_scope.is_manager_of(
            current_user, int(target_emp_id)
        ):
            raise HTTPException(
                status_code=403,
                detail="You are not the manager of this employee.",
            )

    if appraisal.get("status") != "submitted":
        raise HTTPException(
            status_code=400,
            detail="Appraisal must be in 'submitted' status to be reviewed.",
        )

    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        pass

    updates: dict = {
        "status": "reviewed",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": user_id,
    }
    if "reviewer_comments" in body:
        updates["reviewer_comments"] = body["reviewer_comments"]
    if "overall_score" in body:
        # Score validation is light here — appraisal-period config
        # owns the score scale; the FE typically enforces 1-5.
        try:
            updates["overall_score"] = float(body["overall_score"])
        except (ValueError, TypeError):
            pass

    result = dataflow_crud.update("Appraisal", appraisal_id, updates)

    _audit_appraisal(
        appraisal_id,
        company_id,
        "manager_reviewed",
        user_id,
        {
            "employee_id": target_emp_id,
            "has_reviewer_comments": "reviewer_comments" in body,
            "overall_score": updates.get("overall_score"),
        },
    )

    return {"appraisal": result, "detail": "Manager review recorded."}


@router.post("/{appraisal_id}/sign-off")
async def sign_off_appraisal(
    appraisal_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Employee signs off on a completed appraisal.

    This acknowledges the final appraisal result.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"sign_off_appraisal:{user_id}", max_requests=30, window_seconds=60, action_name="sign off appraisal")

    appraisal = dataflow_crud.read("Appraisal", appraisal_id)
    if not appraisal or appraisal.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Appraisal not found.")

    user_id = int(current_user.get("sub", 0))
    emp = _get_employee_for_user(user_id, company_id)
    if not emp or emp.get("id") != appraisal.get("employee_id"):
        raise HTTPException(
            status_code=403, detail="Only the appraised employee can sign off."
        )

    if appraisal.get("status") not in ("submitted", "reviewed"):
        raise HTTPException(
            status_code=400,
            detail="Appraisal must be submitted or reviewed before sign-off.",
        )

    result = dataflow_crud.update(
        "Appraisal",
        appraisal_id,
        {
            "status": "signed_off",
            "signed_off_at": datetime.now(timezone.utc).isoformat(),
            "signed_off_by": user_id,
        },
    )
    return {"appraisal": result, "detail": "Appraisal signed off."}
