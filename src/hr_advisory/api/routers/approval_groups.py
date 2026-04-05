"""Approval group management endpoints.

Handles CRUD for approval groups used across modules (leave, claims, etc.).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get("/")
async def list_approval_groups(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all approval groups for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    groups = dataflow_crud.list_records("ApprovalGroup", {"company_id": company_id}
    )
    return {"approval_groups": groups, "count": len(groups)}


@router.post("/")
async def create_approval_group(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new approval group."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required.")

    approvers = body.get("approvers", [])
    if not approvers:
        raise HTTPException(
            status_code=400, detail="At least one approver is required."
        )

    group = dataflow_crud.create("ApprovalGroup",
        {
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
            "approvers": approvers,
            "approval_type": body.get("approval_type", "any"),
            "modules": body.get("modules", []),
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"approval_group": group}


@router.patch("/{group_id}")
async def update_approval_group(
    group_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an approval group."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("ApprovalGroup", group_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Approval group not found.")

    body = await request.json()
    allowed = {"name", "description", "approvers", "approval_type", "modules"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("ApprovalGroup", group_id, updates)
    return {"approval_group": result}


@router.delete("/{group_id}")
async def delete_approval_group(
    group_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete an approval group."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("ApprovalGroup", group_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Approval group not found.")

    dataflow_crud.delete("ApprovalGroup", group_id)
    return {"detail": "Approval group deleted."}
