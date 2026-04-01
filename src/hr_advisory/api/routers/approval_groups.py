"""Approval group management endpoints.

Handles CRUD for approval groups used across modules (leave, claims, etc.).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import require_role
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


def _dataflow_delete(node_type: str, record_id: int) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, "delete", {"id": record_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["delete"]


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get("")
async def list_approval_groups(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all approval groups for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    groups = _dataflow_list(
        "ApprovalGroupListNode", {"company_id": company_id}
    )
    return {"approval_groups": groups, "count": len(groups)}


@router.post("")
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

    group = _dataflow_create(
        "ApprovalGroupCreateNode",
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

    existing = _dataflow_read("ApprovalGroupReadNode", group_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Approval group not found.")

    body = await request.json()
    allowed = {"name", "description", "approvers", "approval_type", "modules"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = _dataflow_update("ApprovalGroupUpdateNode", group_id, updates)
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

    existing = _dataflow_read("ApprovalGroupReadNode", group_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Approval group not found.")

    _dataflow_delete("ApprovalGroupDeleteNode", group_id)
    return {"detail": "Approval group deleted."}
