"""Inventory management endpoints.

Handles asset locations, categories, items, item lifecycle
(reserve, issue, acknowledge, return, dispose), movement history,
and employee item requests with approval workflow.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
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


def _get_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Resolve the Employee record for a given user_id + company_id."""
    records = _dataflow_list(
        "EmployeeListNode",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


def _verify_item_ownership(item_id: int, company_id: int) -> dict:
    """Load an inventory item and verify tenant ownership. Raises 404 on failure."""
    item = _dataflow_read("InventoryItemReadNode", item_id)
    if not item or item.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Item not found.")
    return item


def _record_movement(item_id: int, action: str, actor_id: int, **kwargs) -> dict:
    """Create an inventory movement audit record."""
    return _dataflow_create(
        "InventoryMovementCreateNode",
        {
            "item_id": item_id,
            "action": action,
            "performed_by": actor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        },
    )


# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------


@router.get("/locations")
async def list_locations(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all inventory locations for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    locations = _dataflow_list(
        "InventoryLocationListNode", {"company_id": company_id}
    )
    return {"locations": locations, "count": len(locations)}


@router.post("/locations")
async def create_location(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new inventory location."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Location name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    location = _dataflow_create(
        "InventoryLocationCreateNode",
        {
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
            "address": body.get("address", ""),
        },
    )
    return {"location": location}


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------


@router.get("/categories")
async def list_categories(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all inventory categories for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    categories = _dataflow_list(
        "InventoryCategoryListNode", {"company_id": company_id}
    )
    return {"categories": categories, "count": len(categories)}


@router.post("/categories")
async def create_category(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new inventory category."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    category = _dataflow_create(
        "InventoryCategoryCreateNode",
        {
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
        },
    )
    return {"category": category}


# --------------------------------------------------------------------------
# Items
# --------------------------------------------------------------------------


@router.get("/items")
async def list_items(
    location_id: int | None = Query(None),
    category_id: int | None = Query(None),
    status: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List inventory items with optional filters."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if location_id:
        filters["location_id"] = location_id
    if category_id:
        filters["category_id"] = category_id
    if status:
        filters["status"] = status

    items = _dataflow_list("InventoryItemListNode", filters)
    return {"items": items, "count": len(items)}


@router.post("/items")
async def create_item(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new inventory item."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Item name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    purchase_price = float(body.get("purchase_price", body.get("purchase_cost", 0.0)))
    if not math.isfinite(purchase_price):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")

    actor_id = int(current_user.get("sub", 0))
    item = _dataflow_create(
        "InventoryItemCreateNode",
        {
            "company_id": company_id,
            "name": name,
            "serial_number": body.get("serial_number", ""),
            "category_id": body.get("category_id"),
            "location_id": body.get("location_id"),
            "quantity": body.get("quantity", 0),
            "purchase_date": body.get("purchase_date", ""),
            "purchase_price": purchase_price,
            "warranty_expiry": body.get("warranty_expiry", ""),
            "status": "available",
        },
    )
    _record_movement(item.get("id", 0), "created", actor_id)
    return {"item": item}


@router.patch("/items/{item_id}")
async def update_item(
    item_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an inventory item."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_item_ownership(item_id, company_id)

    body = await request.json()
    allowed = {
        "name", "serial_number",
        "category_id", "location_id", "quantity", "purchase_date",
        "purchase_price", "warranty_expiry", "condition", "notes",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = _dataflow_update("InventoryItemUpdateNode", item_id, updates)
    return {"item": result}


# --------------------------------------------------------------------------
# My items (employee self-service)
# --------------------------------------------------------------------------


@router.get("/items/me")
async def list_my_items(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List inventory items assigned to the current employee."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    emp = _get_employee_for_user(user_id, company_id)
    if not emp:
        return {"items": [], "count": 0}

    items = _dataflow_list(
        "InventoryItemListNode",
        {"company_id": company_id, "assigned_to_employee_id": emp.get("id")},
    )
    return {"items": items, "count": len(items)}


# --------------------------------------------------------------------------
# Item lifecycle transitions
# --------------------------------------------------------------------------


@router.post("/items/{item_id}/reserve")
async def reserve_item(
    item_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reserve an item for an employee."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    item = _verify_item_ownership(item_id, company_id)
    if item.get("status") != "available":
        raise HTTPException(status_code=400, detail="Item is not available for reservation.")

    body = await request.json()
    employee_id = body.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id is required.")

    actor_id = int(current_user.get("sub", 0))
    _dataflow_update(
        "InventoryItemUpdateNode",
        item_id,
        {
            "status": "reserved",
            "assigned_to_employee_id": employee_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _record_movement(item_id, "reserved", actor_id, employee_id=employee_id)
    return {"detail": "Item reserved.", "item_id": item_id, "employee_id": employee_id}


@router.post("/items/{item_id}/issue")
async def issue_item(
    item_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Issue an item to an employee."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    item = _verify_item_ownership(item_id, company_id)
    if item.get("status") not in ("available", "reserved"):
        raise HTTPException(status_code=400, detail="Item cannot be issued in current status.")

    body = await request.json()
    employee_id = body.get("employee_id") or item.get("assigned_to_employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id is required.")

    actor_id = int(current_user.get("sub", 0))
    _dataflow_update(
        "InventoryItemUpdateNode",
        item_id,
        {
            "status": "issued",
            "assigned_to_employee_id": employee_id,
            "issued_date": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _record_movement(item_id, "issued", actor_id, employee_id=employee_id)
    return {"detail": "Item issued.", "item_id": item_id, "employee_id": employee_id}


@router.post("/items/{item_id}/acknowledge")
async def acknowledge_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Employee acknowledges receipt of an issued item."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    item = _verify_item_ownership(item_id, company_id)
    if item.get("status") != "issued":
        raise HTTPException(status_code=400, detail="Item must be in issued status.")

    user_id = int(current_user.get("sub", 0))
    emp = _get_employee_for_user(user_id, company_id)
    if not emp or emp.get("id") != item.get("assigned_to_employee_id"):
        raise HTTPException(
            status_code=403, detail="Only the assigned employee can acknowledge."
        )

    _dataflow_update(
        "InventoryItemUpdateNode",
        item_id,
        {
            "status": "acknowledged",
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _record_movement(item_id, "acknowledged", user_id, employee_id=emp.get("id"))
    return {"detail": "Item acknowledged."}


@router.post("/items/{item_id}/return")
async def return_item(
    item_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return an item. Employees can return their own items; HR can return any."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    item = _verify_item_ownership(item_id, company_id)
    if item.get("status") not in ("issued", "acknowledged"):
        raise HTTPException(status_code=400, detail="Item is not currently issued.")

    user_id = int(current_user.get("sub", 0))
    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        emp = _get_employee_for_user(user_id, company_id)
        if not emp or emp.get("id") != item.get("assigned_to_employee_id"):
            raise HTTPException(status_code=403, detail="Access denied.")

    body = await request.json() if True else {}  # body optional
    _dataflow_update(
        "InventoryItemUpdateNode",
        item_id,
        {
            "status": "available",
            "assigned_to_employee_id": None,
            "issued_date": None,
            "acknowledged_at": None,
            "return_condition": body.get("condition", "good"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _record_movement(
        item_id, "returned", user_id, condition=body.get("condition", "good")
    )
    return {"detail": "Item returned."}


@router.post("/items/{item_id}/dispose")
async def dispose_item(
    item_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Dispose of an inventory item."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    item = _verify_item_ownership(item_id, company_id)
    if item.get("status") == "disposed":
        raise HTTPException(status_code=400, detail="Item is already disposed.")

    body = await request.json()
    actor_id = int(current_user.get("sub", 0))
    _dataflow_update(
        "InventoryItemUpdateNode",
        item_id,
        {
            "status": "disposed",
            "disposal_reason": body.get("reason", ""),
            "disposal_date": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _record_movement(item_id, "disposed", actor_id, reason=body.get("reason", ""))
    return {"detail": "Item disposed."}


# --------------------------------------------------------------------------
# Movement history
# --------------------------------------------------------------------------


@router.get("/items/{item_id}/history")
async def item_history(
    item_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the movement audit trail for an item."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_item_ownership(item_id, company_id)
    movements = _dataflow_list("InventoryMovementListNode", {"item_id": item_id})
    return {"movements": movements, "count": len(movements)}


# --------------------------------------------------------------------------
# Item requests (employee self-service)
# --------------------------------------------------------------------------


@router.post("/requests")
async def create_item_request(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Employee requests an item."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    emp = _get_employee_for_user(user_id, company_id)
    if not emp:
        raise HTTPException(status_code=403, detail="Employee record not found.")

    body = await request.json()
    item_name = body.get("item_name", "").strip()
    if not item_name:
        raise HTTPException(status_code=400, detail="item_name is required.")

    _validate_text_length(item_name, "item_name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("reason", ""), "reason")

    req = _dataflow_create(
        "InventoryRequestCreateNode",
        {
            "company_id": company_id,
            "employee_id": emp.get("id"),
            "item_name": item_name,
            "category_id": body.get("category_id"),
            "reason": body.get("reason", ""),
            "quantity": body.get("quantity", 1),
            "status": "pending",
            "created_by": user_id,
        },
    )
    return {"request": req}


@router.get("/requests")
async def list_item_requests(
    status: str | None = Query(None),
    employee_id: int | None = Query(None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List item requests. Employees see own; HR sees all."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    role = current_user.get("role", "employee")

    if role in ("owner", "hr_manager"):
        if employee_id:
            filters["employee_id"] = employee_id
    else:
        user_id = int(current_user.get("sub", 0))
        emp = _get_employee_for_user(user_id, company_id)
        if emp:
            filters["employee_id"] = emp.get("id")

    if status:
        filters["status"] = status

    requests = _dataflow_list("InventoryRequestListNode", filters)
    return {"requests": requests, "count": len(requests)}


@router.put("/requests/{request_id}/approve")
async def approve_item_request(
    request_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Approve an item request."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = _dataflow_read("InventoryRequestReadNode", request_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Request not found.")

    if existing.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending.")

    result = _dataflow_update(
        "InventoryRequestUpdateNode",
        request_id,
        {
            "status": "approved",
            "approved_by": int(current_user.get("sub", 0)),
            "approved_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"request": result, "detail": "Request approved."}


@router.put("/requests/{request_id}/deny")
async def deny_item_request(
    request_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Deny an item request."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = _dataflow_read("InventoryRequestReadNode", request_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Request not found.")

    if existing.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending.")

    body = await request.json()
    result = _dataflow_update(
        "InventoryRequestUpdateNode",
        request_id,
        {
            "status": "denied",
            "denied_by": int(current_user.get("sub", 0)),
            "denial_reason": body.get("reason", ""),
            "denied_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"request": result, "detail": "Request denied."}
