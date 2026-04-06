"""Claims and expenses management endpoints.

Handles claim categories, claim lifecycle (draft -> submit -> approve/reject -> pay),
claim items with receipt uploads, and audit trail.
"""

import logging
import math
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory for claim receipts
RECEIPT_UPLOAD_DIR = os.environ.get(
    "RECEIPT_UPLOAD_DIR", os.path.join(os.getcwd(), "uploads", "receipts")
)
MAX_RECEIPT_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_RECEIPT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


def _find_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Look up the employee record for a given user in a company."""
    records = dataflow_crud.list_records(
        "Employee",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


def _audit_claim(
    claim_id: int, company_id: int, action: str, actor_id: int, details: dict | None = None
) -> dict:
    """Create a ClaimAuditEntry for a claim action."""
    return dataflow_crud.create(
        "ClaimAuditEntry",
        {
            "claim_id": claim_id,
            "company_id": company_id,
            "action": action,
            "actor_id": actor_id,
            "details": details,
        },
    )


def _recalculate_claim_total(claim_id: int) -> float:
    """Sum all item amounts for a claim and update the total_amount."""
    items = dataflow_crud.list_records("ClaimItem", {"claim_id": claim_id})
    total = sum(item.get("amount", 0.0) for item in items)
    dataflow_crud.update("Claim", claim_id, {"total_amount": round(total, 2)})
    return round(total, 2)


# --------------------------------------------------------------------------
# Claim Categories — CRUD
# --------------------------------------------------------------------------


@router.get("/categories")
async def list_claim_categories(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all active claim categories for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    categories = dataflow_crud.list_records(
        "ClaimCategory",
        {"company_id": company_id, "is_active": True},
    )
    return {"categories": categories, "count": len(categories)}


@router.post("/categories")
async def create_claim_category(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new claim category."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required.")

    monthly_limit = float(body.get("monthly_limit", 0.0))
    if not math.isfinite(monthly_limit):
        raise HTTPException(status_code=400, detail="monthly_limit must be a finite number")
    per_claim_limit = float(body.get("per_claim_limit", 0.0))
    if not math.isfinite(per_claim_limit):
        raise HTTPException(status_code=400, detail="per_claim_limit must be a finite number")

    category = dataflow_crud.create(
        "ClaimCategory",
        {
            "company_id": company_id,
            "name": name,
            "monthly_limit": monthly_limit,
            "per_claim_limit": per_claim_limit,
            "requires_receipt": body.get("requires_receipt", True),
            "is_active": True,
        },
    )
    return {"category": category}


@router.patch("/categories/{category_id}")
async def update_claim_category(
    category_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a claim category."""
    company_id = get_current_company_id(current_user)
    cat = dataflow_crud.read("ClaimCategory", category_id)
    if cat is None or cat.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Category not found.")

    body = await request.json()
    allowed = {"name", "monthly_limit", "per_claim_limit", "requires_receipt", "is_active"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    if "monthly_limit" in updates:
        updates["monthly_limit"] = float(updates["monthly_limit"])
        if not math.isfinite(updates["monthly_limit"]):
            raise HTTPException(status_code=400, detail="monthly_limit must be a finite number")
    if "per_claim_limit" in updates:
        updates["per_claim_limit"] = float(updates["per_claim_limit"])
        if not math.isfinite(updates["per_claim_limit"]):
            raise HTTPException(status_code=400, detail="per_claim_limit must be a finite number")

    dataflow_crud.update("ClaimCategory", category_id, updates)
    updated = dataflow_crud.read("ClaimCategory", category_id)
    return {"category": updated}


# --------------------------------------------------------------------------
# Claims — lifecycle
# --------------------------------------------------------------------------


@router.post("")
async def create_claim(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a new expense claim in draft status."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None:
        raise HTTPException(status_code=400, detail="Employee record not found.")

    body = await request.json()
    claim_month = body.get("claim_month", "")
    if not claim_month:
        raise HTTPException(status_code=400, detail="claim_month is required (e.g. '2026-03').")

    claim = dataflow_crud.create(
        "Claim",
        {
            "employee_id": emp["id"],
            "company_id": company_id,
            "claim_month": claim_month,
            "status": "draft",
            "total_amount": 0.0,
            "submitted_at": "",
            "reviewer_remarks": "",
        },
    )

    actor_id = int(current_user.get("sub", 0))
    _audit_claim(claim["id"], company_id, "created", actor_id)

    return {"claim": claim}


@router.get("")
async def list_claims(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List claims. Employees see their own; admins see all. Supports ?status= filter."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    status_filter = request.query_params.get("status")

    filter_dict: dict = {"company_id": company_id}

    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None:
            return {"claims": [], "count": 0}
        filter_dict["employee_id"] = emp["id"]

    if status_filter:
        filter_dict["status"] = status_filter

    claims = dataflow_crud.list_records("Claim", filter_dict)
    claims.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    return {"claims": claims, "count": len(claims)}


@router.get("/pending-for-payroll")
async def pending_for_payroll(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List approved claims that are ready for inclusion in a payroll run."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    claims = dataflow_crud.list_records(
        "Claim",
        {"company_id": company_id, "status": "approved"},
    )
    # Exclude claims already linked to a payroll run
    pending = [c for c in claims if not c.get("paid_in_payroll_run_id")]
    return {"claims": pending, "count": len(pending)}


@router.get("/{claim_id}")
async def get_claim_detail(
    claim_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a claim with its items."""
    company_id = get_current_company_id(current_user)
    claim = dataflow_crud.read("Claim", claim_id)
    if claim is None or claim.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim not found.")

    # Employees can only see their own
    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None or claim.get("employee_id") != emp["id"]:
            raise HTTPException(status_code=403, detail="Access denied.")

    items = dataflow_crud.list_records("ClaimItem", {"claim_id": claim_id})
    # Strip internal filesystem paths from items before returning
    safe_items = []
    for item in items:
        clean = {k: v for k, v in item.items() if k != "receipt_paths"}
        paths = item.get("receipt_paths")
        if paths and isinstance(paths, list):
            clean["receipt_files"] = [os.path.basename(str(p)) for p in paths if p]
        safe_items.append(clean)
    return {"claim": claim, "items": safe_items}


@router.patch("/{claim_id}/submit")
async def submit_claim(
    claim_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit a draft claim for approval."""
    company_id = get_current_company_id(current_user)
    claim = dataflow_crud.read("Claim", claim_id)
    if claim is None or claim.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim not found.")

    # Only the claim owner can submit
    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None or claim.get("employee_id") != emp["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    if claim.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft claims can be submitted.")

    # Must have at least one item
    items = dataflow_crud.list_records("ClaimItem", {"claim_id": claim_id})
    if not items:
        raise HTTPException(status_code=400, detail="Cannot submit a claim with no items.")

    now = datetime.now(timezone.utc).isoformat()
    dataflow_crud.update(
        "Claim",
        claim_id,
        {"status": "pending_approval", "submitted_at": now},
    )
    _audit_claim(claim_id, company_id, "submitted", user_id)

    return {"message": "Claim submitted for approval.", "status": "pending_approval"}


@router.patch("/{claim_id}/approve")
async def approve_claim(
    claim_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Approve a pending claim."""
    company_id = get_current_company_id(current_user)
    claim = dataflow_crud.read("Claim", claim_id)
    if claim is None or claim.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim not found.")

    if claim.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Only pending claims can be approved.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    dataflow_crud.update(
        "Claim",
        claim_id,
        {
            "status": "approved",
            "reviewed_by": actor_id,
            "reviewed_at": now,
        },
    )
    _audit_claim(claim_id, company_id, "approved", actor_id)

    return {"message": "Claim approved.", "status": "approved"}


@router.patch("/{claim_id}/reject")
async def reject_claim(
    claim_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reject a pending claim. Reviewer remarks are required."""
    company_id = get_current_company_id(current_user)
    claim = dataflow_crud.read("Claim", claim_id)
    if claim is None or claim.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim not found.")

    if claim.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Only pending claims can be rejected.")

    body = await request.json()
    remarks = body.get("reviewer_remarks", "").strip()
    if not remarks:
        raise HTTPException(status_code=400, detail="reviewer_remarks is required when rejecting.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    dataflow_crud.update(
        "Claim",
        claim_id,
        {
            "status": "rejected",
            "reviewed_by": actor_id,
            "reviewed_at": now,
            "reviewer_remarks": remarks,
        },
    )
    _audit_claim(claim_id, company_id, "rejected", actor_id, {"remarks": remarks})

    return {"message": "Claim rejected.", "status": "rejected"}


# --------------------------------------------------------------------------
# Claim Items
# --------------------------------------------------------------------------


@router.post("/{claim_id}/items")
async def add_claim_item(
    claim_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Add an item to a draft claim. Validates category limits."""
    company_id = get_current_company_id(current_user)
    claim = dataflow_crud.read("Claim", claim_id)
    if claim is None or claim.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim not found.")

    if claim.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Items can only be added to draft claims.")

    # Only the claim owner can add items
    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None or claim.get("employee_id") != emp["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    body = await request.json()
    category_id = body.get("category_id")
    amount = float(body.get("amount", 0))
    if not math.isfinite(amount):
        raise HTTPException(status_code=400, detail="Invalid amount value.")
    description = body.get("description", "")
    receipt_date = body.get("receipt_date", "")

    if not category_id or amount <= 0:
        raise HTTPException(status_code=400, detail="category_id and positive amount are required.")

    # Validate category exists and belongs to company
    cat = dataflow_crud.read("ClaimCategory", category_id)
    if cat is None or cat.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim category not found.")

    # Validate per-claim limit
    per_claim_limit = cat.get("per_claim_limit", 0.0)
    if per_claim_limit > 0 and amount > per_claim_limit:
        raise HTTPException(
            status_code=400,
            detail=f"Amount {amount} exceeds per-claim limit of {per_claim_limit} for category '{cat.get('name')}'.",
        )

    # Validate monthly limit — sum existing items for same category in this claim month
    monthly_limit = cat.get("monthly_limit", 0.0)
    if monthly_limit > 0:
        # Find all claims for this employee in the same month
        month_claims = dataflow_crud.list_records(
            "Claim",
            {"employee_id": emp["id"], "claim_month": claim.get("claim_month", "")},
        )
        month_total = 0.0
        for mc in month_claims:
            items = dataflow_crud.list_records(
                "ClaimItem",
                {"claim_id": mc["id"], "category_id": category_id},
            )
            month_total += sum(i.get("amount", 0.0) for i in items)
        if month_total + amount > monthly_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Adding {amount} would exceed monthly limit of {monthly_limit} for category '{cat.get('name')}' (current: {month_total}).",
            )

    item = dataflow_crud.create(
        "ClaimItem",
        {
            "claim_id": claim_id,
            "company_id": company_id,
            "category_id": category_id,
            "description": description,
            "amount": amount,
            "receipt_date": receipt_date,
            "notes": body.get("notes", ""),
        },
    )

    # Recalculate claim total
    new_total = _recalculate_claim_total(claim_id)

    return {"item": item, "claim_total": new_total}


# --------------------------------------------------------------------------
# Receipt Upload
# --------------------------------------------------------------------------


@router.post("/{claim_id}/items/{item_id}/receipts")
async def upload_receipt(
    claim_id: int,
    item_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Upload a receipt for a claim item (multipart/form-data)."""
    company_id = get_current_company_id(current_user)
    claim = dataflow_crud.read("Claim", claim_id)
    if claim is None or claim.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim not found.")

    # Only claim owner can upload receipts
    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None or claim.get("employee_id") != emp["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Verify item belongs to claim
    item = dataflow_crud.read("ClaimItem", item_id)
    if item is None or item.get("claim_id") != claim_id:
        raise HTTPException(status_code=404, detail="Claim item not found.")

    form = await request.form()
    file = form.get("file")
    if file is None:
        raise HTTPException(status_code=400, detail="File is required.")

    content = await file.read()
    if len(content) > MAX_RECEIPT_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit.")

    content_type = getattr(file, "content_type", "application/octet-stream")
    if content_type not in ALLOWED_RECEIPT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Use PDF, JPG, or PNG.",
        )

    # Save file
    os.makedirs(RECEIPT_UPLOAD_DIR, exist_ok=True)
    file_ext = os.path.splitext(file.filename or "receipt")[1]
    ALLOWED_RECEIPT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    if file_ext.lower() not in ALLOWED_RECEIPT_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension '{file_ext}' not allowed.")
    stored_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(RECEIPT_UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Update item's receipt_paths (append to existing list)
    existing_paths = item.get("receipt_paths") or []
    if isinstance(existing_paths, str):
        import json

        try:
            existing_paths = json.loads(existing_paths)
        except (json.JSONDecodeError, TypeError):
            existing_paths = []
    existing_paths.append(file_path)

    dataflow_crud.update("ClaimItem", item_id, {"receipt_paths": existing_paths})

    return {"message": "Receipt uploaded.", "file_name": stored_name}


# --------------------------------------------------------------------------
# Audit Trail
# --------------------------------------------------------------------------


@router.get("/{claim_id}/audit-trail")
async def get_claim_audit_trail(
    claim_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the audit trail for a claim."""
    company_id = get_current_company_id(current_user)
    claim = dataflow_crud.read("Claim", claim_id)
    if claim is None or claim.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim not found.")

    # Employees can only see audit trail for their own claims
    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None or claim.get("employee_id") != emp["id"]:
            raise HTTPException(status_code=403, detail="Access denied.")

    entries = dataflow_crud.list_records("ClaimAuditEntry", {"claim_id": claim_id})
    entries.sort(key=lambda e: e.get("created_at", ""))
    return {"audit_trail": entries, "count": len(entries)}


# ==========================================================================
# CLAIM GROUPS (T350)
# ==========================================================================


@router.get("/groups")
async def list_claim_groups(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List claim groups. Employees see their own; admins see all."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    filter_dict: dict = {"company_id": company_id}

    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None:
            return {"groups": [], "count": 0}
        filter_dict["employee_id"] = emp["id"]

    groups = dataflow_crud.list_records("ClaimGroup", filter_dict)
    groups.sort(key=lambda g: g.get("created_at", ""), reverse=True)
    return {"groups": groups, "count": len(groups)}


@router.post("/groups")
async def create_claim_group(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a new claim group to bundle multiple claims."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None:
        raise HTTPException(status_code=400, detail="Employee record not found.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")

    claim_ids = body.get("claim_ids", [])

    # Validate claim_ids belong to the employee
    for cid in claim_ids:
        claim = dataflow_crud.read("Claim", cid)
        if claim is None or claim.get("company_id") != company_id:
            raise HTTPException(status_code=404, detail=f"Claim {cid} not found.")
        if claim.get("employee_id") != emp["id"]:
            raise HTTPException(status_code=403, detail=f"Claim {cid} does not belong to you.")

    now = datetime.now(timezone.utc).isoformat()

    group = dataflow_crud.create(
        "ClaimGroup",
        {
            "employee_id": emp["id"],
            "company_id": company_id,
            "name": name,
            "claim_ids": claim_ids,
            "status": "draft",
            "total_amount": 0.0,
            "created_at": now,
        },
    )

    # Calculate total from linked claims
    total = 0.0
    for cid in claim_ids:
        claim = dataflow_crud.read("Claim", cid)
        if claim:
            total += claim.get("total_amount", 0.0)

    if total > 0:
        dataflow_crud.update("ClaimGroup", group["id"], {"total_amount": round(total, 2)})
        group["total_amount"] = round(total, 2)

    return {"group": group}


@router.patch("/groups/{group_id}")
async def update_claim_group(
    group_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update a claim group (add/remove claims, rename)."""
    company_id = get_current_company_id(current_user)
    group = dataflow_crud.read("ClaimGroup", group_id)
    if group is None or group.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim group not found.")

    # Only the owner or admins can update
    role = current_user.get("role", "employee")
    if role not in ("owner", "hr_manager"):
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_for_user(user_id, company_id)
        if emp is None or group.get("employee_id") != emp["id"]:
            raise HTTPException(status_code=403, detail="Access denied.")

    if group.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft groups can be updated.")

    body = await request.json()
    allowed = {"name", "claim_ids"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # If claim_ids updated, recalculate total
    if "claim_ids" in updates:
        total = 0.0
        for cid in updates["claim_ids"]:
            claim = dataflow_crud.read("Claim", cid)
            if claim and claim.get("company_id") == company_id:
                total += claim.get("total_amount", 0.0)
        updates["total_amount"] = round(total, 2)

    dataflow_crud.update("ClaimGroup", group_id, updates)
    updated = dataflow_crud.read("ClaimGroup", group_id)
    return {"group": updated}


@router.post("/groups/{group_id}/submit")
async def submit_claim_group(
    group_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit a claim group for approval. Submits all linked claims."""
    company_id = get_current_company_id(current_user)
    group = dataflow_crud.read("ClaimGroup", group_id)
    if group is None or group.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Claim group not found.")

    user_id = int(current_user.get("sub", 0))
    emp = _find_employee_for_user(user_id, company_id)
    if emp is None or group.get("employee_id") != emp["id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    if group.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft groups can be submitted.")

    claim_ids = group.get("claim_ids", [])
    if not claim_ids:
        raise HTTPException(status_code=400, detail="Cannot submit a group with no claims.")

    now = datetime.now(timezone.utc).isoformat()

    # Submit each claim in the group that is in draft status
    submitted_count = 0
    for cid in claim_ids:
        claim = dataflow_crud.read("Claim", cid)
        if claim and claim.get("status") == "draft":
            # Verify it has items
            items = dataflow_crud.list_records("ClaimItem", {"claim_id": cid})
            if items:
                dataflow_crud.update(
                    "Claim", cid,
                    {"status": "pending_approval", "submitted_at": now},
                )
                _audit_claim(cid, company_id, "submitted_via_group", user_id, {"group_id": group_id})
                submitted_count += 1

    dataflow_crud.update(
        "ClaimGroup", group_id,
        {"status": "submitted", "submitted_at": now},
    )

    return {
        "message": f"Group submitted with {submitted_count} claim(s).",
        "status": "submitted",
    }


# ==========================================================================
# CLAIMS PAYROLL INTEGRATION (T352)
# ==========================================================================


@router.get("/payroll-ready")
async def get_payroll_ready_claims(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get approved claims ready for payroll inclusion.

    Supports optional ?cutoff_date= filter. Claims approved on or before
    the cutoff are included.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    cutoff_date = request.query_params.get("cutoff_date", "")

    claims = dataflow_crud.list_records(
        "Claim",
        {"company_id": company_id, "status": "approved"},
    )

    # Exclude claims already linked to a payroll run
    ready = [c for c in claims if not c.get("paid_in_payroll_run_id")]

    # Apply cutoff filter if provided
    if cutoff_date:
        ready = [
            c for c in ready
            if c.get("submitted_at", "")[:10] <= cutoff_date
        ]

    # Enrich with employee names
    enriched = []
    for c in ready:
        emp_records = dataflow_crud.list_records(
            "Employee", {"id": c.get("employee_id")}, limit=1
        )
        emp = emp_records[0] if emp_records else {}
        enriched.append(
            {
                **c,
                "employee_name": emp.get("first_name", ""),
            }
        )

    total_amount = round(sum(c.get("total_amount", 0.0) for c in ready), 2)

    return {
        "claims": enriched,
        "count": len(enriched),
        "total_amount": total_amount,
    }
