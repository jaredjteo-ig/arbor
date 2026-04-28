"""Company policy management endpoints.

Handles policy CRUD, file uploads with text extraction, versioning,
and employee acknowledgment tracking. Supports both manual text entry
and file upload (PDF/DOCX/TXT) workflows.

Roles:
    owner, hr_manager — full CRUD, upload, view acknowledgments
    employee — read active policies, acknowledge, view pending acknowledgments
"""

import hashlib
import logging
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.workflows.guardrails import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory for policy files
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.getcwd(), "uploads", "documents"))
POLICY_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "policies")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

# Input length limits
MAX_TITLE_LENGTH = 500
MAX_CONTENT_LENGTH = 500_000  # 500KB of text

POLICY_CATEGORIES = [
    "employment_terms",
    "leave_absence",
    "compensation_benefits",
    "workplace_safety",
    "fair_employment",
    "foreign_worker",
    "tax_filing",
    "general_hr",
    "code_of_conduct",
]


# --------------------------------------------------------------------------
# DataFlow helpers
# --------------------------------------------------------------------------

from hr_advisory.services import dataflow_crud


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------


from hr_advisory.api.routers._helpers import _find_employee_for_user  # noqa: E402


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of policy content for integrity verification."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _validate_category(category: str) -> None:
    """Validate that category is a non-empty string when provided.

    The 9 predefined categories in POLICY_CATEGORIES are suggestions, not
    a hard whitelist. Custom categories are allowed per stakeholder
    decision D6 (9 predefined + custom categories).
    """
    # Empty string = no category selected, which is fine
    if not category:
        return
    # Any non-empty string is accepted (predefined or custom)
    if category not in POLICY_CATEGORIES:
        logger.info("Custom policy category used: '%s'", category)


def _strip_policy_internals(policy: dict) -> dict:
    """Remove internal fields (e.g. file_path) from a policy record before returning."""
    return {k: v for k, v in policy.items() if k not in ("file_path",)}


def _truncate_content(content: str, max_length: int = 200) -> str:
    """Truncate content for list-view summaries."""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."


def _is_admin_role(role: str) -> bool:
    """Check if role has admin-level policy management access."""
    return role in ("owner", "hr_manager", "platform_admin")


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(date_str: str) -> bool:
    """Check if *date_str* matches the ``YYYY-MM-DD`` format.

    Returns ``True`` when the string is a valid calendar date,
    ``False`` otherwise.
    """
    if not _DATE_RE.match(date_str):
        return False
    # Also verify it represents a real calendar date
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------
# GET /policies/ --- List policies for current company
# --------------------------------------------------------------------------


@router.get("")
async def list_policies(
    category: str = "",
    status: str = "",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List company policies for the current user's company.

    Query params:
        category: Filter by policy category (optional).
        status: Filter by status (optional). Employees always see only "active".

    Returns all policies matching the filters with content truncated
    to 200 characters for the list view.

    Status codes:
        200: Success
        400: Invalid category filter
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        return {"policies": [], "count": 0}

    if category:
        _validate_category(category)

    user_role = current_user.get("role", "")
    filter_dict: dict = {"company_id": company_id}

    # Employees can only see active policies
    if not _is_admin_role(user_role):
        filter_dict["status"] = "active"
        filter_dict["is_active"] = True
    elif status:
        filter_dict["status"] = status

    if category:
        filter_dict["category"] = category

    policies = dataflow_crud.list_records("CompanyPolicy", filter_dict)
    return {
        "policies": [
            {
                "id": p.get("id"),
                "title": p.get("title", ""),
                "policy_type": p.get("policy_type", ""),
                "category": p.get("category", ""),
                "content": _truncate_content(p.get("content", "")),
                "effective_date": p.get("effective_date", ""),
                "is_active": p.get("is_active", True),
                "status": p.get("status", "active"),
                "version_number": p.get("version_number", 1),
                "file_type": p.get("file_type", ""),
                "file_name": p.get("file_name", ""),
                "file_size_bytes": p.get("file_size_bytes", 0),
                "requires_acknowledgment": p.get("requires_acknowledgment", False),
                "extraction_status": p.get("extraction_status", ""),
                "created_at": p.get("created_at", ""),
                "updated_at": p.get("updated_at", ""),
            }
            for p in policies
        ],
        "count": len(policies),
    }


# --------------------------------------------------------------------------
# GET /policies/pending-acknowledgments --- Pending for current employee
# NOTE: Must be declared BEFORE /{policy_id} to avoid FastAPI path capture.
# --------------------------------------------------------------------------


@router.get("/pending-acknowledgments")
async def get_pending_acknowledgments(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get policies requiring acknowledgment that the current employee
    has not yet acknowledged.

    Status codes:
        200: Success
        400: No employee record found
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        return {"pending_policies": [], "count": 0}

    user_id = int(current_user.get("sub", 0))
    employee = _find_employee_for_user(user_id, company_id)
    if employee is None:
        raise HTTPException(
            status_code=400,
            detail="No employee record found for your account in this company.",
        )
    employee_id = employee.get("id")

    # Get all active policies requiring acknowledgment
    policies = dataflow_crud.list_records(
        "CompanyPolicy",
        {
            "company_id": company_id,
            "is_active": True,
            "status": "active",
            "requires_acknowledgment": True,
        },
    )

    if not policies:
        return {"pending_policies": [], "count": 0}

    # Get all acknowledgments by this employee
    acks = dataflow_crud.list_records(
        "PolicyAcknowledgment",
        {"company_id": company_id, "employee_id": employee_id},
    )

    # Build set of (policy_id, version_acknowledged) pairs
    acked_set = {
        (a.get("policy_id"), a.get("version_acknowledged"))
        for a in acks
    }

    pending = [
        {
            "id": p.get("id"),
            "title": p.get("title", ""),
            "category": p.get("category", ""),
            "version_number": p.get("version_number", 1),
            "effective_date": p.get("effective_date", ""),
            "content": _truncate_content(p.get("content", "")),
            "status": p.get("status", "active"),
            "requires_acknowledgment": p.get("requires_acknowledgment", False),
            "file_type": p.get("file_type", ""),
        }
        for p in policies
        if (p.get("id"), p.get("version_number", 1)) not in acked_set
    ]

    return {"pending_policies": pending, "count": len(pending)}


# --------------------------------------------------------------------------
# GET /policies/{policy_id} --- Single policy with full content
# --------------------------------------------------------------------------


@router.get("/{policy_id}")
async def get_policy(
    policy_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Retrieve a single policy with full content.

    Tenant-isolated: verifies the policy belongs to the user's company.

    Status codes:
        200: Success
        404: Policy not found or access denied
    """
    company_id = get_current_company_id(current_user)
    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        logger.warning(
            "Tenant isolation: user company_id=%s tried to access policy company_id=%s",
            company_id,
            policy.get("company_id"),
        )
        raise HTTPException(status_code=404, detail="Policy not found.")

    # Employees can only see active policies
    user_role = current_user.get("role", "")
    if not _is_admin_role(user_role):
        if policy.get("status") != "active" or not policy.get("is_active", True):
            raise HTTPException(status_code=404, detail="Policy not found.")

    return {"policy": _strip_policy_internals(policy)}


# --------------------------------------------------------------------------
# POST /policies/ --- Create policy from manual text entry
# --------------------------------------------------------------------------


@router.post("")
async def create_policy(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new company policy from manual text entry.

    Accepts JSON body with: title, category, content, effective_date,
    requires_acknowledgment, status, policy_type.

    Sets file_type="text" for manually entered policies.

    Status codes:
        201: Created
        400: Validation error
        429: Rate limit exceeded
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    if not check_rate_limit(
        f"policy_create:{company_id}",
        max_requests=30,
        window_seconds=60,
        action_name="creating policies",
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many policy creation requests. Please wait before trying again.",
        )

    body = await request.json()

    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    if len(title) > MAX_TITLE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters.",
        )

    category = (body.get("category") or "").strip()
    _validate_category(category)

    effective_date = (body.get("effective_date") or "").strip()
    if effective_date and not _validate_date(effective_date):
        raise HTTPException(
            status_code=400,
            detail="Invalid effective_date format. Expected YYYY-MM-DD.",
        )

    requires_ack = bool(body.get("requires_acknowledgment", False))
    status_val = (body.get("status") or "active").strip()
    if status_val not in ("active", "draft"):
        raise HTTPException(
            status_code=400,
            detail="Status must be 'active' or 'draft' for new policies.",
        )

    content = (body.get("content") or "").strip()
    # Drafts may have empty content; active policies require it
    if status_val == "active" and not content:
        raise HTTPException(status_code=400, detail="Content is required for active policies.")
    if len(content) > MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Content exceeds maximum length of {MAX_CONTENT_LENGTH} characters.",
        )

    policy_type = (body.get("policy_type") or category or "general_hr").strip()
    actor_id = int(current_user.get("sub", 0))

    policy = dataflow_crud.create(
        "CompanyPolicy",
        {
            "company_id": company_id,
            "policy_type": policy_type,
            "title": title,
            "content": content,
            "effective_date": effective_date,
            "is_active": status_val == "active",
            "category": category,
            "version_number": 1,
            "uploaded_by": actor_id,
            "file_type": "text",
            "content_hash": _compute_content_hash(content),
            "extraction_status": "complete",
            "requires_acknowledgment": requires_ack,
            "status": status_val,
        },
    )

    logger.info(
        "Policy created: id=%s, title='%s', company_id=%s, by user=%s",
        policy.get("id"),
        title,
        company_id,
        actor_id,
    )

    # Run statutory floor check (non-blocking warnings)
    statutory_floor_warnings: list[dict] = []
    if content and category:
        try:
            from hr_advisory.services.statutory_floor_check import (
                check_policy_against_statutory_floor,
            )

            statutory_floor_warnings = check_policy_against_statutory_floor(
                content, category,
            )
        except Exception as exc:
            logger.warning(
                "Statutory floor check failed for policy id=%s: %s",
                policy.get("id"),
                exc,
            )

    return {
        "policy": _strip_policy_internals(policy),
        "message": "Policy created successfully.",
        "statutory_floor_warnings": statutory_floor_warnings,
    }


# --------------------------------------------------------------------------
# POST /policies/upload --- Upload policy file
# --------------------------------------------------------------------------


@router.post("/upload")
async def upload_policy(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Upload a policy document file and extract text content.

    Accepts multipart/form-data with fields:
        file (required): PDF, DOCX, or TXT file (max 10MB).
        title (required): Policy title.
        category (optional): Policy category.
        effective_date (optional): Effective date string.
        requires_acknowledgment (optional): Boolean, default false.

    The file text is extracted automatically. If extraction fails,
    the policy is created with extraction_status="failed" and empty
    content that can be edited later via PUT /policies/{id}/content.

    Status codes:
        201: Created
        400: Validation error (file too large, wrong type, missing title)
        413: File too large
        429: Rate limit exceeded
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    if not check_rate_limit(
        f"policy_upload:{company_id}",
        max_requests=10,
        window_seconds=60,
        action_name="uploading policies",
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many policy upload requests. Please wait before trying again.",
        )

    form = await request.form()
    file = form.get("file")
    if file is None:
        raise HTTPException(status_code=400, detail="File is required.")

    title = (form.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    if len(title) > MAX_TITLE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters.",
        )

    category = (form.get("category") or "").strip()
    _validate_category(category)

    effective_date = (form.get("effective_date") or "").strip()
    if effective_date and not _validate_date(effective_date):
        raise HTTPException(
            status_code=400,
            detail="Invalid effective_date format. Expected YYYY-MM-DD.",
        )

    requires_ack_raw = (form.get("requires_acknowledgment") or "false").strip()
    requires_ack = requires_ack_raw.lower() in ("true", "1", "yes")

    # --- File validation (size check before full read) ---
    # Check Content-Length header first for early rejection
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    # Read in chunks with size guard to avoid unbounded memory usage
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 64)  # 64KB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
            )
        chunks.append(chunk)
    file_content = b"".join(chunks)

    original_filename = getattr(file, "filename", None) or "policy"
    file_ext = os.path.splitext(original_filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File extension '{file_ext}' not allowed. "
                f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    content_type = getattr(file, "content_type", "application/octet-stream")
    if content_type not in ALLOWED_MIME_TYPES:
        if content_type == "application/octet-stream":
            # Generic MIME type from some browsers — extension already validated above
            logger.warning(
                "MIME type '%s' is generic for file '%s'. "
                "Proceeding based on validated extension '%s'.",
                content_type,
                original_filename,
                file_ext,
            )
        else:
            # Both extension and MIME type don't match — reject
            raise HTTPException(
                status_code=400,
                detail=(
                    f"File MIME type '{content_type}' does not match allowed types. "
                    f"Supported formats: PDF, DOCX, TXT."
                ),
            )

    # --- Save file to disk ---
    os.makedirs(POLICY_UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{file_ext}"
    stored_path = os.path.join(POLICY_UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(file_content)

    # --- Extract text ---
    from hr_advisory.services.policy_parser import (
        extract_text,
        validate_extraction_quality,
    )

    extracted_content = ""
    extraction_status = "failed"
    try:
        extracted_content, ext_status = extract_text(file_content, file_ext)
        # Map parser status to our status vocabulary
        if ext_status == "success":
            extraction_status = "complete"
        elif ext_status == "timeout":
            extraction_status = "failed"
            logger.warning(
                "Text extraction timed out for file '%s'",
                original_filename,
            )
        elif ext_status == "partial":
            extraction_status = "partial"
        else:
            extraction_status = "failed"
    except (ValueError, Exception) as exc:
        extraction_status = "failed"
        logger.error(
            "Text extraction failed for file '%s' (ext=%s): %s",
            original_filename,
            file_ext,
            exc,
        )

    # --- Validate extraction quality ---
    if extracted_content and extraction_status in ("complete", "partial"):
        quality_status, quality_warnings = validate_extraction_quality(extracted_content)
        if quality_status in ("low_quality", "empty"):
            extraction_status = quality_status
            logger.warning(
                "Low extraction quality for file '%s': %s",
                original_filename,
                "; ".join(quality_warnings),
            )

    content_hash = _compute_content_hash(extracted_content) if extracted_content else ""
    actor_id = int(current_user.get("sub", 0))
    policy_type = category or "general_hr"

    policy = dataflow_crud.create(
        "CompanyPolicy",
        {
            "company_id": company_id,
            "policy_type": policy_type,
            "title": title,
            "content": extracted_content,
            "effective_date": effective_date,
            "is_active": True,
            "category": category,
            "version_number": 1,
            "uploaded_by": actor_id,
            "file_name": original_filename,
            "file_path": stored_path,
            "file_type": file_ext.lstrip("."),
            "file_size_bytes": len(file_content),
            "content_hash": content_hash,
            "extraction_status": extraction_status,
            "requires_acknowledgment": requires_ack,
            "status": "active",
        },
    )

    logger.info(
        "Policy uploaded: id=%s, title='%s', file='%s', extraction=%s, company_id=%s",
        policy.get("id"),
        title,
        original_filename,
        extraction_status,
        company_id,
    )

    # Run statutory floor check on extracted content (non-blocking warnings)
    statutory_floor_warnings: list[dict] = []
    if extracted_content and category:
        try:
            from hr_advisory.services.statutory_floor_check import (
                check_policy_against_statutory_floor,
            )

            statutory_floor_warnings = check_policy_against_statutory_floor(
                extracted_content, category,
            )
        except Exception as exc:
            logger.warning(
                "Statutory floor check failed for uploaded policy id=%s: %s",
                policy.get("id"),
                exc,
            )

    return {
        "policy": _strip_policy_internals(policy),
        "extraction_status": extraction_status,
        "message": (
            "Policy uploaded and text extracted successfully."
            if extraction_status == "complete"
            else "Policy uploaded but text extraction failed. "
            "You can manually enter content via PUT /policies/{id}/content."
        ),
        "statutory_floor_warnings": statutory_floor_warnings,
    }


# --------------------------------------------------------------------------
# PUT /policies/{policy_id} --- Update policy (with versioning)
# --------------------------------------------------------------------------


@router.put("/{policy_id}")
async def update_policy(
    policy_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a company policy.

    If content changes: deactivates the old version (is_active=False,
    status="archived", superseded_by_id set) and creates a new record
    with version_number incremented by 1.

    If only metadata changes (title, category, effective_date,
    requires_acknowledgment, status): updates the existing record in place.

    Race protection (T008): if another request has already created a newer
    version, returns 409 Conflict.

    Status codes:
        200: Updated in place (metadata only)
        201: New version created (content changed)
        404: Policy not found
        409: Version conflict
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("status") == "archived":
        raise HTTPException(
            status_code=400,
            detail="Cannot update an archived policy. Update the current active version instead.",
        )

    body = await request.json()
    new_content = body.get("content")
    content_changed = (
        new_content is not None
        and new_content.strip() != (policy.get("content") or "").strip()
    )

    if content_changed:
        # --- Version creation with race protection (T008) ---
        # Re-query to check no other version was created since we read
        current_version = policy.get("version_number", 1)
        active_versions = dataflow_crud.list_records(
            "CompanyPolicy",
            {
                "company_id": company_id,
                "policy_type": policy.get("policy_type", ""),
                "is_active": True,
            },
        )
        # Check that the version we read is still the active one
        latest_active = max(
            (v for v in active_versions),
            key=lambda v: v.get("version_number", 0),
            default=None,
        )
        if latest_active and latest_active.get("version_number", 0) != current_version:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Version conflict: expected version {current_version} "
                    f"but found version {latest_active.get('version_number')}. "
                    "Another update may have occurred. Please refresh and retry."
                ),
            )

        new_content_stripped = new_content.strip()
        if len(new_content_stripped) > MAX_CONTENT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Content exceeds maximum length of {MAX_CONTENT_LENGTH} characters.",
            )

        actor_id = int(current_user.get("sub", 0))

        # Create new version
        new_category = (body.get("category") or policy.get("category", "")).strip()
        _validate_category(new_category)
        new_policy = dataflow_crud.create(
            "CompanyPolicy",
            {
                "company_id": company_id,
                "policy_type": body.get("policy_type", policy.get("policy_type", "")),
                "title": body.get("title", policy.get("title", "")).strip(),
                "content": new_content_stripped,
                "effective_date": (
                    body.get("effective_date", policy.get("effective_date", ""))
                ).strip(),
                "is_active": True,
                "category": new_category,
                "version_number": current_version + 1,
                "uploaded_by": actor_id,
                "file_name": policy.get("file_name", ""),
                "file_path": policy.get("file_path", ""),
                "file_type": body.get("file_type", policy.get("file_type", "text")),
                "file_size_bytes": policy.get("file_size_bytes", 0),
                "content_hash": _compute_content_hash(new_content_stripped),
                "extraction_status": "complete",
                "requires_acknowledgment": body.get(
                    "requires_acknowledgment",
                    policy.get("requires_acknowledgment", False),
                ),
                "status": "active",
            },
        )

        # Archive old version
        dataflow_crud.update(
            "CompanyPolicy",
            policy_id,
            {
                "is_active": False,
                "status": "archived",
                "superseded_by_id": new_policy.get("id", 0),
            },
        )

        logger.info(
            "Policy versioned: old_id=%s (v%s) -> new_id=%s (v%s), company_id=%s",
            policy_id,
            current_version,
            new_policy.get("id"),
            current_version + 1,
            company_id,
        )
        return {
            "policy": _strip_policy_internals(new_policy),
            "previous_version_id": policy_id,
            "message": f"New version (v{current_version + 1}) created. Previous version archived.",
        }

    # --- Metadata-only update ---
    updates: dict = {}
    if "title" in body:
        new_title = body["title"].strip()
        if not new_title:
            raise HTTPException(status_code=400, detail="Title cannot be empty.")
        if len(new_title) > MAX_TITLE_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters.",
            )
        updates["title"] = new_title

    if "category" in body:
        new_category = body["category"].strip()
        _validate_category(new_category)
        updates["category"] = new_category

    if "effective_date" in body:
        ed = body["effective_date"].strip()
        if ed and not _validate_date(ed):
            raise HTTPException(
                status_code=400,
                detail="Invalid effective_date format. Expected YYYY-MM-DD.",
            )
        updates["effective_date"] = ed

    if "requires_acknowledgment" in body:
        updates["requires_acknowledgment"] = bool(body["requires_acknowledgment"])

    if "status" in body:
        new_status = body["status"].strip()
        if new_status not in ("active", "draft", "archived"):
            raise HTTPException(
                status_code=400,
                detail="Status must be 'active', 'draft', or 'archived'.",
            )
        updates["status"] = new_status
        if new_status == "archived":
            updates["is_active"] = False
        elif new_status == "active":
            updates["is_active"] = True

    if "policy_type" in body:
        updates["policy_type"] = body["policy_type"].strip()

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    dataflow_crud.update("CompanyPolicy", policy_id, updates)

    updated_policy = dataflow_crud.read("CompanyPolicy", policy_id)
    logger.info(
        "Policy updated (metadata): id=%s, fields=%s, company_id=%s",
        policy_id,
        list(updates.keys()),
        company_id,
    )
    return {
        "policy": _strip_policy_internals(updated_policy),
        "message": "Policy updated.",
    }


# --------------------------------------------------------------------------
# PUT /policies/{policy_id}/content --- Edit extracted text
# --------------------------------------------------------------------------


@router.put("/{policy_id}/content")
async def update_policy_content(
    policy_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Edit the extracted text content of a policy.

    Used to correct or fill in content after file upload, especially
    when text extraction failed or produced poor results.

    Status codes:
        200: Content updated
        400: Validation error
        404: Policy not found
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Policy not found.")

    body = await request.json()
    new_content = (body.get("content") or "").strip()
    if not new_content:
        raise HTTPException(status_code=400, detail="Content is required.")
    if len(new_content) > MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Content exceeds maximum length of {MAX_CONTENT_LENGTH} characters.",
        )

    content_hash = _compute_content_hash(new_content)
    dataflow_crud.update(
        "CompanyPolicy",
        policy_id,
        {
            "content": new_content,
            "content_hash": content_hash,
            "extraction_status": "manual",
        },
    )

    logger.info(
        "Policy content updated: id=%s, hash=%s, company_id=%s",
        policy_id,
        content_hash[:12],
        company_id,
    )
    return {
        "policy_id": policy_id,
        "content_hash": content_hash,
        "message": "Policy content updated.",
    }


# --------------------------------------------------------------------------
# DELETE /policies/{policy_id} --- Soft delete (archive)
# --------------------------------------------------------------------------


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Soft-delete a policy by archiving it.

    Sets status="archived" and is_active=False. The record remains
    in the database for audit purposes.

    Status codes:
        200: Archived
        404: Policy not found
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Policy not found.")

    if policy.get("status") == "archived":
        return {"message": "Policy is already archived.", "policy_id": policy_id}

    dataflow_crud.update(
        "CompanyPolicy",
        policy_id,
        {"status": "archived", "is_active": False},
    )

    logger.info("Policy archived: id=%s, company_id=%s", policy_id, company_id)
    return {"message": "Policy archived.", "policy_id": policy_id}


# --------------------------------------------------------------------------
# GET /policies/{policy_id}/versions --- Version history
# --------------------------------------------------------------------------


@router.get("/{policy_id}/versions")
async def list_policy_versions(
    policy_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List the version history for a policy.

    Returns all records sharing the same policy_type and company_id,
    ordered by version_number descending.

    Status codes:
        200: Success
        404: Policy not found
    """
    company_id = get_current_company_id(current_user)
    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Policy not found.")

    policy_type = policy.get("policy_type", "")
    all_versions = dataflow_crud.list_records(
        "CompanyPolicy",
        {"company_id": company_id, "policy_type": policy_type},
    )

    # Sort by version_number descending
    all_versions.sort(key=lambda v: v.get("version_number", 0), reverse=True)

    return {
        "policy_id": policy_id,
        "policy_type": policy_type,
        "versions": [
            {
                "id": v.get("id"),
                "version_number": v.get("version_number", 1),
                "status": v.get("status", ""),
                "is_active": v.get("is_active", False),
                "effective_date": v.get("effective_date", ""),
                "content": _truncate_content(v.get("content", "")),
                "superseded_by_id": v.get("superseded_by_id", 0),
                "uploaded_by": v.get("uploaded_by", 0),
                "created_at": v.get("created_at", ""),
            }
            for v in all_versions
        ],
        "count": len(all_versions),
    }


# --------------------------------------------------------------------------
# GET /policies/{policy_id}/compliance-check --- Statutory floor check
# --------------------------------------------------------------------------


@router.get("/{policy_id}/compliance-check")
async def compliance_check(
    policy_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Run statutory floor checks on an existing policy.

    Compares the policy's leave entitlements against Singapore Employment
    Act statutory minimums and returns any findings. Does not modify the
    policy record.

    Status codes:
        200: Findings returned (may be empty for non-leave categories)
        404: Policy not found
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Policy not found.")

    content = policy.get("content", "")
    category = policy.get("category", "")

    from hr_advisory.services.statutory_floor_check import (
        check_policy_against_statutory_floor,
    )

    findings = check_policy_against_statutory_floor(content, category)

    logger.info(
        "Compliance check run: policy_id=%s, category=%s, findings=%d, company_id=%s",
        policy_id,
        category,
        len(findings),
        company_id,
    )

    return {
        "policy_id": policy_id,
        "category": category,
        "findings": findings,
        "findings_count": len(findings),
    }


# --------------------------------------------------------------------------
# POST /policies/{policy_id}/acknowledge --- Employee acknowledgment
# --------------------------------------------------------------------------


@router.post("/{policy_id}/acknowledge")
async def acknowledge_policy(
    policy_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Acknowledge a company policy.

    Creates a PolicyAcknowledgment record for the current employee.
    Idempotent: re-acknowledging the same version is a no-op.

    Status codes:
        200: Already acknowledged (idempotent)
        201: Acknowledgment recorded
        400: No employee record found
        404: Policy not found
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("status") != "active":
        raise HTTPException(status_code=400, detail="Can only acknowledge active policies.")

    user_id = int(current_user.get("sub", 0))
    employee = _find_employee_for_user(user_id, company_id)
    if employee is None:
        raise HTTPException(
            status_code=400,
            detail="No employee record found for your account in this company.",
        )
    employee_id = employee.get("id")

    version_number = policy.get("version_number", 1)

    # Check for existing acknowledgment (idempotent)
    existing = dataflow_crud.list_records(
        "PolicyAcknowledgment",
        {
            "company_id": company_id,
            "policy_id": policy_id,
            "employee_id": employee_id,
            "version_acknowledged": version_number,
        },
        limit=1,
    )
    if existing:
        return {
            "message": "Policy already acknowledged.",
            "acknowledgment": existing[0],
        }

    # Extract client IP for audit
    ip_address = ""
    try:
        client = request.client
        if client:
            ip_address = client.host or ""
    except Exception:
        pass

    ack = dataflow_crud.create(
        "PolicyAcknowledgment",
        {
            "company_id": company_id,
            "policy_id": policy_id,
            "employee_id": employee_id,
            "version_acknowledged": version_number,
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
            "ip_address": ip_address,
        },
    )

    logger.info(
        "Policy acknowledged: policy_id=%s (v%s), employee_id=%s, company_id=%s",
        policy_id,
        version_number,
        employee_id,
        company_id,
    )
    return {"message": "Policy acknowledged.", "acknowledgment": ack}


# --------------------------------------------------------------------------
# GET /policies/{policy_id}/acknowledgments --- Acknowledgment status
# --------------------------------------------------------------------------


@router.get("/{policy_id}/acknowledgments")
async def list_acknowledgments(
    policy_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List acknowledgment status for a policy.

    Returns which employees have acknowledged and which have not.
    Owner/HR manager only.

    Status codes:
        200: Success
        404: Policy not found
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if policy.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Policy not found.")

    version_number = policy.get("version_number", 1)

    # Get all acknowledgments for this policy version
    acknowledgments = dataflow_crud.list_records(
        "PolicyAcknowledgment",
        {"company_id": company_id, "policy_id": policy_id},
    )
    # Filter to current version
    current_acks = [
        a for a in acknowledgments
        if a.get("version_acknowledged") == version_number
    ]
    acknowledged_employee_ids = {a.get("employee_id") for a in current_acks}

    # Get all active employees in the company
    all_employees = dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "is_active": True},
    )

    not_acknowledged = [
        {
            "employee_id": emp.get("id"),
            "full_name": emp.get("full_name", ""),
            "email": emp.get("email", ""),
        }
        for emp in all_employees
        if emp.get("id") not in acknowledged_employee_ids
    ]

    return {
        "policy_id": policy_id,
        "version_number": version_number,
        "total_employees": len(all_employees),
        "acknowledged_count": len(current_acks),
        "not_acknowledged_count": len(not_acknowledged),
        "acknowledged": [
            {
                "employee_id": a.get("employee_id"),
                "acknowledged_at": a.get("acknowledged_at", ""),
                "ip_address": a.get("ip_address", ""),
            }
            for a in current_acks
        ],
        "not_acknowledged": not_acknowledged,
    }


