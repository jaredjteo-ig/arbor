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

from hr_advisory.services import dataflow_crud


def _get_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Resolve the Employee record for a given user_id + company_id."""
    records = dataflow_crud.list_records(
        "Employee",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


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

    # Move period to active
    dataflow_crud.update("AppraisalPeriod", period_id, {"status": "active"})

    return {
        "detail": f"Launched {len(created)} appraisals.",
        "appraisals_created": len(created),
    }


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
    return {"appraisals": appraisals, "count": len(appraisals)}


# --------------------------------------------------------------------------
# Individual appraisals
# --------------------------------------------------------------------------


@router.get("/{appraisal_id}")
async def get_appraisal(
    appraisal_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get an individual appraisal.

    Employees can view their own appraisals; HR/owners can view any.
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
        if not emp or emp.get("id") != appraisal.get("employee_id"):
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
