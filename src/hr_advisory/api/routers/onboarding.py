"""Onboarding management endpoints.

Handles onboarding templates, modules, steps, employee assignments,
progress tracking, pre-boarding tasks, and employee self-service.

Roles:
    owner, hr_manager — template CRUD, module/step management, assignments, pre-boarding
    employee — self-service progress, step completion, document upload, policy acknowledgment
"""

import logging
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Input length limits
MAX_TEXT_LENGTH = 2000
MAX_NAME_LENGTH = 200
MAX_BODY_CONTENT_LENGTH = 50_000
MAX_CHECKLIST_LENGTH = 10_000
MAX_MEDIA_URL_LENGTH = 2_000
MAX_FORM_DATA_LENGTH = 10_000
MAX_NOTES_LENGTH = 5_000

# Upload directory for onboarding documents
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.getcwd(), "uploads", "documents"))
ONBOARDING_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "onboarding")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# --------------------------------------------------------------------------
# DataFlow helpers
# --------------------------------------------------------------------------

from hr_advisory.services import dataflow_crud


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------


def _validate_text_length(value: str, field_name: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    """Validate text input to maximum length."""
    if value and len(value) > max_len:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {max_len} characters.",
        )
    return value


def _validate_step_content_fields(body: dict) -> None:
    """Validate length limits on step content fields.

    Applies to both admin step creation/update and employee step completion.
    """
    if "body_content" in body and body["body_content"]:
        _validate_text_length(body["body_content"], "body_content", MAX_BODY_CONTENT_LENGTH)
    if "checklist_items" in body and body["checklist_items"]:
        _validate_text_length(body["checklist_items"], "checklist_items", MAX_CHECKLIST_LENGTH)
    if "media_url" in body and body["media_url"]:
        url = body["media_url"]
        _validate_text_length(url, "media_url", MAX_MEDIA_URL_LENGTH)
        if not url.startswith("http://") and not url.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="media_url must start with http:// or https://.",
            )
    if "form_data" in body and body["form_data"]:
        _validate_text_length(body["form_data"], "form_data", MAX_FORM_DATA_LENGTH)
    if "notes" in body and body["notes"]:
        _validate_text_length(body["notes"], "notes", MAX_NOTES_LENGTH)


# Magic byte signatures for file validation
_MAGIC_BYTES = {
    ".pdf": b"%PDF",
    ".jpg": [b"\xff\xd8\xff"],  # JFIF/Exif JPEG
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": b"\x89PNG",
    ".docx": b"PK",  # OOXML ZIP container
}


def _validate_magic_bytes(file_content: bytes, extension: str) -> None:
    """Validate file content matches the expected magic bytes for its extension."""
    if not file_content:
        return
    expected = _MAGIC_BYTES.get(extension)
    if expected is None:
        return
    if isinstance(expected, list):
        if not any(file_content.startswith(sig) for sig in expected):
            raise HTTPException(
                status_code=400,
                detail=f"File content does not match expected format for {extension}.",
            )
    else:
        if not file_content.startswith(expected):
            raise HTTPException(
                status_code=400,
                detail=f"File content does not match expected format for {extension}.",
            )


def _get_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Resolve the Employee record for a given user_id + company_id."""
    records = dataflow_crud.list_records(
        "Employee",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


def _verify_template_ownership(template_id: int, company_id: int) -> dict:
    """Load an onboarding template and verify tenant ownership."""
    template = dataflow_crud.read("OnboardingTemplate", template_id)
    if not template or template.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Onboarding template not found.")
    return template


def _verify_module_ownership(module_id: int, company_id: int) -> dict:
    """Load an onboarding module and verify tenant ownership."""
    module = dataflow_crud.read("OnboardingModule", module_id)
    if not module or module.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Onboarding module not found.")
    return module


def _verify_assignment_ownership(assignment_id: int, company_id: int) -> dict:
    """Load an onboarding assignment and verify tenant ownership."""
    assignment = dataflow_crud.read("OnboardingAssignment", assignment_id)
    if not assignment or assignment.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Onboarding assignment not found.")
    return assignment


def _get_modules_for_template(template_id: int) -> list[dict]:
    """Fetch all modules for a template, sorted by order."""
    modules = dataflow_crud.list_records(
        "OnboardingModule",
        {"template_id": template_id},
    )
    return sorted(modules, key=lambda m: m.get("sort_order", 0))


def _get_steps_for_module(module_id: int) -> list[dict]:
    """Fetch all steps for a module, sorted by order."""
    steps = dataflow_crud.list_records(
        "OnboardingStep",
        {"module_id": module_id},
    )
    return sorted(steps, key=lambda s: s.get("sort_order", 0))


def _get_all_steps_for_template(template_id: int) -> list[dict]:
    """Fetch all steps across all modules for a template."""
    modules = _get_modules_for_template(template_id)
    all_steps = []
    for module in modules:
        steps = _get_steps_for_module(module.get("id"))
        all_steps.extend(steps)
    return all_steps


def _calculate_completion(assignment_id: int) -> tuple[float, int, int]:
    """Calculate completion percentage for an assignment.

    Returns:
        Tuple of (percentage, completed_count, total_count).
    """
    progress_records = dataflow_crud.list_records(
        "OnboardingStepProgress",
        {"assignment_id": assignment_id},
    )
    total = len(progress_records)
    if total == 0:
        return 0.0, 0, 0
    completed = sum(1 for p in progress_records if p.get("status") == "completed")
    percentage = round((completed / total) * 100, 1)
    return percentage, completed, total


def _update_assignment_status(assignment_id: int) -> dict:
    """Recalculate and update assignment completion status.

    Checks completion percentage and due date to set status correctly.
    Returns the updated assignment.
    """
    assignment = dataflow_crud.read("OnboardingAssignment", assignment_id)
    if not assignment:
        return {}

    percentage, completed, total = _calculate_completion(assignment_id)
    now = datetime.now(timezone.utc)
    updates: dict = {"completion_percentage": percentage}

    if completed == total and total > 0:
        updates["status"] = "completed"
        updates["completed_at"] = now.isoformat()
    elif assignment.get("due_date"):
        due_str = assignment["due_date"]
        try:
            due_date = datetime.fromisoformat(due_str)
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            if now > due_date and assignment.get("status") != "completed":
                updates["status"] = "overdue"
        except (ValueError, TypeError):
            pass

    dataflow_crud.update("OnboardingAssignment", assignment_id, updates)
    assignment.update(updates)
    return assignment


def _enrich_assignment(assignment: dict) -> dict:
    """Enrich an assignment with progress details and computed fields."""
    assignment_id = assignment.get("id")
    percentage, completed, total = _calculate_completion(assignment_id)
    assignment["completion_percentage"] = percentage
    assignment["completed_steps"] = completed
    assignment["total_steps"] = total

    # Check overdue status on read
    if assignment.get("status") == "in_progress" and assignment.get("due_date"):
        try:
            due_date = datetime.fromisoformat(assignment["due_date"])
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > due_date:
                assignment["status"] = "overdue"
                dataflow_crud.update(
                    "OnboardingAssignment", assignment_id, {"status": "overdue"}
                )
        except (ValueError, TypeError):
            pass

    # Enrich with employee name
    employee = dataflow_crud.read("Employee", assignment.get("employee_id"))
    if employee:
        first = employee.get("first_name", "")
        last = employee.get("last_name", "")
        assignment["employee_name"] = f"{first} {last}".strip()

    # Enrich with template name
    template = dataflow_crud.read("OnboardingTemplate", assignment.get("template_id"))
    if template:
        assignment["template_name"] = template.get("name", "")

    return assignment


def _sanitize_filename(extension: str) -> str:
    """Generate a UUID-based safe filename with the given extension."""
    return f"{uuid.uuid4().hex}{extension}"


# ==========================================================================
# TEMPLATE MANAGEMENT (admin)
# ==========================================================================


@router.get("/templates")
async def list_templates(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all onboarding templates for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    templates = dataflow_crud.list_records(
        "OnboardingTemplate",
        {"company_id": company_id},
    )
    # Filter to active by default
    active_templates = [t for t in templates if t.get("is_active", True)]
    return {"templates": active_templates, "count": len(active_templates)}


@router.post("/templates")
async def create_template(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new onboarding template."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Template name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    # If marked as default, unset existing defaults for this company
    is_default = body.get("is_default", False)
    if is_default:
        existing = dataflow_crud.list_records(
            "OnboardingTemplate",
            {"company_id": company_id, "is_default": True},
        )
        for t in existing:
            dataflow_crud.update("OnboardingTemplate", t["id"], {"is_default": False})

    template = dataflow_crud.create(
        "OnboardingTemplate",
        {
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
            "is_default": is_default,
            "version": 1,
            "is_active": True,
            "created_by": actor_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    logger.info(
        "Onboarding template created: id=%s, company_id=%s, name=%s",
        template.get("id"),
        company_id,
        name,
    )
    return {"template": template}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a template with all its modules and steps (nested response)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    template = _verify_template_ownership(template_id, company_id)

    # Build nested response: template -> modules -> steps
    modules = _get_modules_for_template(template_id)
    modules_with_steps = []
    total_steps = 0
    total_estimated_minutes = 0
    for module in modules:
        steps = _get_steps_for_module(module.get("id"))
        total_steps += len(steps)
        total_estimated_minutes += module.get("estimated_duration_minutes", 0)
        modules_with_steps.append({
            **module,
            "steps": steps,
            "step_count": len(steps),
        })

    return {
        "template": {
            **template,
            "modules": modules_with_steps,
            "module_count": len(modules_with_steps),
            "total_steps": total_steps,
            "total_estimated_minutes": total_estimated_minutes,
        }
    }


@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a template. Increments version automatically."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    template = _verify_template_ownership(template_id, company_id)
    body = await request.json()

    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if "name" in body:
        name = body["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="Template name cannot be empty.")
        _validate_text_length(name, "name", MAX_NAME_LENGTH)
        updates["name"] = name

    if "description" in body:
        _validate_text_length(body["description"], "description")
        updates["description"] = body["description"]

    if "is_default" in body and body["is_default"]:
        # Unset existing defaults
        existing = dataflow_crud.list_records(
            "OnboardingTemplate",
            {"company_id": company_id, "is_default": True},
        )
        for t in existing:
            if t["id"] != template_id:
                dataflow_crud.update("OnboardingTemplate", t["id"], {"is_default": False})
        updates["is_default"] = True
    elif "is_default" in body:
        updates["is_default"] = False

    # Increment version
    updates["version"] = template.get("version", 1) + 1

    result = dataflow_crud.update("OnboardingTemplate", template_id, updates)
    logger.info("Onboarding template updated: id=%s, version=%s", template_id, updates["version"])
    return {"template": result}


@router.delete("/templates/{template_id}")
async def archive_template(
    template_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Archive a template (soft delete). Fails if active assignments exist."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_template_ownership(template_id, company_id)

    # Check for active assignments
    assignments = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"template_id": template_id, "company_id": company_id},
    )
    active_assignments = [
        a for a in assignments if a.get("status") in ("in_progress", "overdue")
    ]
    if active_assignments:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot archive template: {len(active_assignments)} active assignment(s) exist. "
            "Complete or cancel them first.",
        )

    dataflow_crud.update(
        "OnboardingTemplate",
        template_id,
        {
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("Onboarding template archived: id=%s", template_id)
    return {"message": "Template archived.", "template_id": template_id}


@router.post("/templates/{template_id}/duplicate")
async def duplicate_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Clone a template with all its modules and steps."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    template = _verify_template_ownership(template_id, company_id)
    body = await request.json() if request.headers.get("content-length", "0") != "0" else {}

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    new_name = body.get("name", f"{template.get('name', '')} (Copy)").strip()
    _validate_text_length(new_name, "name", MAX_NAME_LENGTH)

    # Create the new template
    new_template = dataflow_crud.create(
        "OnboardingTemplate",
        {
            "company_id": company_id,
            "name": new_name,
            "description": template.get("description", ""),
            "is_default": False,
            "version": 1,
            "is_active": True,
            "created_by": actor_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    new_template_id = new_template.get("id")

    # Clone modules and steps
    modules = _get_modules_for_template(template_id)
    modules_cloned = 0
    steps_cloned = 0
    for module in modules:
        new_module = dataflow_crud.create(
            "OnboardingModule",
            {
                "template_id": new_template_id,
                "company_id": company_id,
                "name": module.get("name", ""),
                "description": module.get("description", ""),
                "phase": module.get("phase", "custom"),
                "sort_order": module.get("sort_order", 0),
                "estimated_duration_minutes": module.get("estimated_duration_minutes", 0),
                "is_mandatory": module.get("is_mandatory", True),
                "is_role_specific": module.get("is_role_specific", False),
                "role_filter": module.get("role_filter", ""),
            },
        )
        modules_cloned += 1

        steps = _get_steps_for_module(module.get("id"))
        for step in steps:
            dataflow_crud.create(
                "OnboardingStep",
                {
                    "module_id": new_module.get("id"),
                    "title": step.get("title", ""),
                    "description": step.get("description", ""),
                    "sort_order": step.get("sort_order", 0),
                    "step_type": step.get("step_type", "content"),
                    "body_content": step.get("body_content", ""),
                    "checklist_items": step.get("checklist_items", ""),
                    "media_url": step.get("media_url", ""),
                    "requires_completion": step.get("requires_completion", True),
                    "policy_id": step.get("policy_id"),
                    "requires_previous_completion": step.get("requires_previous_completion", False),
                },
            )
            steps_cloned += 1

    logger.info(
        "Onboarding template duplicated: source=%s, new=%s, modules=%d, steps=%d",
        template_id,
        new_template_id,
        modules_cloned,
        steps_cloned,
    )
    return {
        "template": new_template,
        "modules_cloned": modules_cloned,
        "steps_cloned": steps_cloned,
    }


@router.post("/templates/import")
async def import_template(
    file: UploadFile = File(..., description="Onboarding template .xlsx file"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Import an onboarding template from an Excel (.xlsx) file.

    Parses the uploaded spreadsheet and creates a template with modules
    and steps based on the parsed content. Only .xlsx files up to 10MB
    are accepted.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Validate file extension
    original_filename = file.filename or ""
    _, ext = os.path.splitext(original_filename.lower())
    if ext != ".xlsx":
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx files are accepted for template import.",
        )

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Parse the template
    from hr_advisory.services.onboarding_parser import parse_onboarding_template

    try:
        parsed = parse_onboarding_template(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Server missing required package for parsing .xlsx files.",
        )

    parse_errors = parsed.get("errors", [])
    parse_warnings = parsed.get("warnings", [])
    parsed_modules = parsed.get("modules", [])
    parsed_steps = parsed.get("steps", [])

    # If there are fatal parse errors and no modules at all, reject
    if parse_errors and not parsed_modules:
        raise HTTPException(
            status_code=400,
            detail=f"Template parsing failed: {'; '.join(parse_errors)}",
        )

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    # Derive template name from file or company profile
    company_profile = parsed.get("company_profile", {})
    template_name = company_profile.get("company_name", "")
    if not template_name:
        # Use filename without extension
        template_name = os.path.splitext(original_filename)[0]
    template_name = f"{template_name} Onboarding".strip()
    _validate_text_length(template_name, "template name", MAX_NAME_LENGTH)

    # Create the template record
    template = dataflow_crud.create(
        "OnboardingTemplate",
        {
            "company_id": company_id,
            "name": template_name,
            "description": f"Imported from {original_filename}",
            "is_default": False,
            "version": 1,
            "is_active": True,
            "created_by": actor_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    template_id = template.get("id")

    # Phase mapping for parsed modules
    valid_phases = {"orientation", "compliance", "benefits", "probation", "custom"}
    modules_created = 0
    steps_created = 0

    # Build module name -> module_id lookup for linking steps
    module_id_map: dict[str, int] = {}

    for idx, mod_data in enumerate(parsed_modules):
        mod_name = str(mod_data.get("module_name") or mod_data.get("name") or f"Module {idx + 1}").strip()
        phase = str(mod_data.get("phase", "custom")).strip().lower()
        if phase not in valid_phases:
            phase = "custom"

        duration = 0
        raw_duration = mod_data.get("duration")
        if raw_duration is not None:
            try:
                duration = int(raw_duration)
            except (ValueError, TypeError):
                pass

        is_mandatory = True
        raw_required = mod_data.get("required")
        if raw_required is not None:
            if isinstance(raw_required, bool):
                is_mandatory = raw_required
            elif isinstance(raw_required, str):
                is_mandatory = raw_required.strip().lower() not in ("no", "false", "optional")

        new_module = dataflow_crud.create(
            "OnboardingModule",
            {
                "template_id": template_id,
                "company_id": company_id,
                "name": mod_name[:MAX_NAME_LENGTH],
                "description": str(mod_data.get("description") or "")[:MAX_TEXT_LENGTH],
                "phase": phase,
                "sort_order": idx,
                "estimated_duration_minutes": duration,
                "is_mandatory": is_mandatory,
                "is_role_specific": bool(mod_data.get("role_specific")),
                "role_filter": "",
            },
        )
        module_id_map[mod_name] = new_module.get("id")
        modules_created += 1

    # Create steps and link to modules by module_name
    step_order_by_module: dict[int, int] = {}
    for step_data in parsed_steps:
        parent_module_name = str(step_data.get("module_name") or "").strip()
        parent_module_id = module_id_map.get(parent_module_name)
        if parent_module_id is None:
            # Try to find a close match or assign to the first module
            if module_id_map:
                parent_module_id = next(iter(module_id_map.values()))
            else:
                parse_warnings.append(
                    f"Step '{step_data.get('step_name', '?')}' has no matching module, skipped."
                )
                continue

        order = step_order_by_module.get(parent_module_id, 0)
        step_order_by_module[parent_module_id] = order + 1

        step_title = str(step_data.get("heading") or step_data.get("step_name") or f"Step {order + 1}").strip()

        # Build body content
        body_content = str(step_data.get("body_content") or "")

        # Build checklist items (parser may return a list)
        raw_checklist = step_data.get("checklist_items", "")
        if isinstance(raw_checklist, list):
            checklist_str = "\n".join(str(item) for item in raw_checklist if item)
        else:
            checklist_str = str(raw_checklist or "")

        media_url = str(step_data.get("media") or "")

        dataflow_crud.create(
            "OnboardingStep",
            {
                "module_id": parent_module_id,
                "title": step_title[:MAX_NAME_LENGTH],
                "description": "",
                "sort_order": order,
                "step_type": "content",
                "body_content": body_content[:MAX_BODY_CONTENT_LENGTH],
                "checklist_items": checklist_str[:MAX_CHECKLIST_LENGTH],
                "media_url": media_url[:MAX_MEDIA_URL_LENGTH] if media_url.startswith(("http://", "https://")) else "",
                "requires_completion": True,
                "policy_id": None,
                "requires_previous_completion": False,
            },
        )
        steps_created += 1

    logger.info(
        "Onboarding template imported: template_id=%s, modules=%d, steps=%d, warnings=%d, errors=%d",
        template_id,
        modules_created,
        steps_created,
        len(parse_warnings),
        len(parse_errors),
    )
    return {
        "template_id": template_id,
        "modules_created": modules_created,
        "steps_created": steps_created,
        "warnings": parse_warnings,
        "errors": parse_errors,
    }


# ==========================================================================
# MODULE MANAGEMENT (admin)
# ==========================================================================


@router.post("/templates/{template_id}/modules")
async def add_module(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a module to a template."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_template_ownership(template_id, company_id)

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Module name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")

    # Determine order: append after last module
    existing_modules = _get_modules_for_template(template_id)
    max_order = max((m.get("sort_order", 0) for m in existing_modules), default=-1)

    valid_phases = {"orientation", "compliance", "benefits", "probation", "custom"}
    phase = body.get("phase", "custom")
    if phase not in valid_phases:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase. Must be one of: {', '.join(sorted(valid_phases))}.",
        )

    module = dataflow_crud.create(
        "OnboardingModule",
        {
            "template_id": template_id,
            "company_id": company_id,
            "name": name,
            "description": body.get("description", ""),
            "phase": phase,
            "sort_order": body.get("sort_order", max_order + 1),
            "estimated_duration_minutes": body.get("estimated_duration_minutes", 0),
            "is_mandatory": body.get("is_mandatory", True),
            "is_role_specific": body.get("is_role_specific", False),
            "role_filter": body.get("role_filter", ""),
        },
    )

    # Bump template updated_at
    dataflow_crud.update(
        "OnboardingTemplate",
        template_id,
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info("Onboarding module added: id=%s, template_id=%s", module.get("id"), template_id)
    return {"module": module}


@router.put("/modules/{module_id}")
async def update_module(
    module_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a module."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    module = _verify_module_ownership(module_id, company_id)

    body = await request.json()
    updates: dict = {}

    if "name" in body:
        name = body["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="Module name cannot be empty.")
        _validate_text_length(name, "name", MAX_NAME_LENGTH)
        updates["name"] = name

    if "description" in body:
        _validate_text_length(body["description"], "description")
        updates["description"] = body["description"]

    valid_phases = {"orientation", "compliance", "benefits", "probation", "custom"}
    if "phase" in body:
        if body["phase"] not in valid_phases:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phase. Must be one of: {', '.join(sorted(valid_phases))}.",
            )
        updates["phase"] = body["phase"]

    for field in ("sort_order", "estimated_duration_minutes", "is_mandatory", "is_role_specific", "role_filter"):
        if field in body:
            updates[field] = body[field]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = dataflow_crud.update("OnboardingModule", module_id, updates)

    # Bump template updated_at
    dataflow_crud.update(
        "OnboardingTemplate",
        module.get("template_id"),
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info("Onboarding module updated: id=%s", module_id)
    return {"module": result}


@router.delete("/modules/{module_id}")
async def delete_module(
    module_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a module and cascade delete its steps."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    module = _verify_module_ownership(module_id, company_id)

    # Cascade delete steps
    steps = _get_steps_for_module(module_id)
    for step in steps:
        dataflow_crud.delete("OnboardingStep", step["id"])

    dataflow_crud.delete("OnboardingModule", module_id)

    # Bump template updated_at
    dataflow_crud.update(
        "OnboardingTemplate",
        module.get("template_id"),
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info(
        "Onboarding module deleted: id=%s, cascade_deleted_steps=%d",
        module_id,
        len(steps),
    )
    return {
        "message": "Module deleted.",
        "module_id": module_id,
        "steps_deleted": len(steps),
    }


@router.patch("/templates/{template_id}/reorder")
async def reorder_modules(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reorder modules within a template. Accepts an ordered list of module IDs."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_template_ownership(template_id, company_id)

    body = await request.json()
    module_ids = body.get("module_ids", [])
    if not module_ids or not isinstance(module_ids, list):
        raise HTTPException(status_code=400, detail="module_ids must be a non-empty list.")

    # Verify all modules belong to this template and company
    existing_modules = _get_modules_for_template(template_id)
    existing_ids = {m["id"] for m in existing_modules}
    for mid in module_ids:
        if mid not in existing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Module {mid} does not belong to template {template_id}.",
            )

    # Update order
    for idx, mid in enumerate(module_ids):
        dataflow_crud.update("OnboardingModule", mid, {"sort_order": idx})

    dataflow_crud.update(
        "OnboardingTemplate",
        template_id,
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info("Modules reordered for template %s: %s", template_id, module_ids)
    return {"message": "Modules reordered.", "module_ids": module_ids}


# ==========================================================================
# STEP MANAGEMENT (admin)
# ==========================================================================


@router.post("/modules/{module_id}/steps")
async def add_step(
    module_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a step to a module."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    module = _verify_module_ownership(module_id, company_id)

    body = await request.json()
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Step title is required.")

    _validate_text_length(title, "title", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")
    _validate_step_content_fields(body)

    valid_step_types = {
        "content", "checklist", "document_upload",
        "policy_acknowledgment", "form", "approval",
    }
    step_type = body.get("step_type", "content")
    if step_type not in valid_step_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step_type. Must be one of: {', '.join(sorted(valid_step_types))}.",
        )

    # If policy_acknowledgment step, validate policy_id
    policy_id = body.get("policy_id")
    if step_type == "policy_acknowledgment" and not policy_id:
        raise HTTPException(
            status_code=400,
            detail="policy_id is required for policy_acknowledgment steps.",
        )
    if policy_id:
        policy = dataflow_crud.read("CompanyPolicy", policy_id)
        if not policy or policy.get("company_id") != company_id:
            raise HTTPException(status_code=400, detail="Referenced policy not found in this company.")

    # Determine order: append after last step
    existing_steps = _get_steps_for_module(module_id)
    max_order = max((s.get("sort_order", 0) for s in existing_steps), default=-1)

    step = dataflow_crud.create(
        "OnboardingStep",
        {
            "module_id": module_id,
            "title": title,
            "description": body.get("description", ""),
            "sort_order": body.get("sort_order", max_order + 1),
            "step_type": step_type,
            "body_content": body.get("body_content", ""),
            "checklist_items": body.get("checklist_items", ""),
            "media_url": body.get("media_url", ""),
            "requires_completion": body.get("requires_completion", True),
            "policy_id": policy_id,
            "requires_previous_completion": body.get("requires_previous_completion", False),
        },
    )

    # Bump template updated_at
    dataflow_crud.update(
        "OnboardingTemplate",
        module.get("template_id"),
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info("Onboarding step added: id=%s, module_id=%s", step.get("id"), module_id)
    return {"step": step}


@router.put("/steps/{step_id}")
async def update_step(
    step_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a step."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    step = dataflow_crud.read("OnboardingStep", step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Onboarding step not found.")

    # Verify parent module belongs to this company
    module = _verify_module_ownership(step.get("module_id"), company_id)

    body = await request.json()
    updates: dict = {}

    if "title" in body:
        title = body["title"].strip()
        if not title:
            raise HTTPException(status_code=400, detail="Step title cannot be empty.")
        _validate_text_length(title, "title", MAX_NAME_LENGTH)
        updates["title"] = title

    if "description" in body:
        _validate_text_length(body["description"], "description")
        updates["description"] = body["description"]

    _validate_step_content_fields(body)

    valid_step_types = {
        "content", "checklist", "document_upload",
        "policy_acknowledgment", "form", "approval",
    }
    if "step_type" in body:
        if body["step_type"] not in valid_step_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid step_type. Must be one of: {', '.join(sorted(valid_step_types))}.",
            )
        updates["step_type"] = body["step_type"]

    if "policy_id" in body and body["policy_id"]:
        policy = dataflow_crud.read("CompanyPolicy", body["policy_id"])
        if not policy or policy.get("company_id") != company_id:
            raise HTTPException(status_code=400, detail="Referenced policy not found in this company.")
        updates["policy_id"] = body["policy_id"]

    for field in (
        "sort_order", "body_content", "checklist_items", "media_url",
        "requires_completion", "requires_previous_completion",
    ):
        if field in body:
            updates[field] = body[field]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = dataflow_crud.update("OnboardingStep", step_id, updates)

    # Bump template updated_at
    dataflow_crud.update(
        "OnboardingTemplate",
        module.get("template_id"),
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info("Onboarding step updated: id=%s", step_id)
    return {"step": result}


@router.delete("/steps/{step_id}")
async def delete_step(
    step_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a step."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    step = dataflow_crud.read("OnboardingStep", step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Onboarding step not found.")

    # Verify parent module belongs to this company
    module = _verify_module_ownership(step.get("module_id"), company_id)

    dataflow_crud.delete("OnboardingStep", step_id)

    # Bump template updated_at
    dataflow_crud.update(
        "OnboardingTemplate",
        module.get("template_id"),
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info("Onboarding step deleted: id=%s", step_id)
    return {"message": "Step deleted.", "step_id": step_id}


@router.patch("/modules/{module_id}/reorder-steps")
async def reorder_steps(
    module_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reorder steps within a module. Accepts an ordered list of step IDs."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_module_ownership(module_id, company_id)

    body = await request.json()
    step_ids = body.get("step_ids", [])
    if not step_ids or not isinstance(step_ids, list):
        raise HTTPException(status_code=400, detail="step_ids must be a non-empty list.")

    # Verify all steps belong to this module
    existing_steps = _get_steps_for_module(module_id)
    existing_ids = {s["id"] for s in existing_steps}
    for sid in step_ids:
        if sid not in existing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Step {sid} does not belong to module {module_id}.",
            )

    for idx, sid in enumerate(step_ids):
        dataflow_crud.update("OnboardingStep", sid, {"sort_order": idx})

    logger.info("Steps reordered for module %s: %s", module_id, step_ids)
    return {"message": "Steps reordered.", "step_ids": step_ids}


# ==========================================================================
# ASSIGNMENT (admin)
# ==========================================================================


@router.post("/assign")
async def assign_template(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Assign an onboarding template to an employee.

    Creates the assignment record and individual step progress records
    for every step in the template.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"onboarding_assign:{company_id}",
        max_requests=20,
        window_seconds=60,
        action_name="onboarding assignment",
    )

    body = await request.json()
    employee_id = body.get("employee_id")
    template_id = body.get("template_id")
    due_date = body.get("due_date")

    if not employee_id or not template_id:
        raise HTTPException(
            status_code=400,
            detail="employee_id and template_id are required.",
        )

    # Verify employee belongs to company
    employee = dataflow_crud.read("Employee", employee_id)
    if not employee or employee.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found in this company.")

    # Verify template belongs to company and is active
    template = _verify_template_ownership(template_id, company_id)
    if not template.get("is_active", True):
        raise HTTPException(status_code=400, detail="Cannot assign an archived template.")

    # Check for existing active assignment for this employee + template
    existing = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"employee_id": employee_id, "template_id": template_id, "company_id": company_id},
    )
    active_existing = [
        a for a in existing if a.get("status") in ("in_progress", "overdue")
    ]
    if active_existing:
        raise HTTPException(
            status_code=400,
            detail="Employee already has an active assignment for this template.",
        )

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    assignment = dataflow_crud.create(
        "OnboardingAssignment",
        {
            "employee_id": employee_id,
            "template_id": template_id,
            "template_version": template.get("version", 1),
            "company_id": company_id,
            "assigned_by": actor_id,
            "assigned_at": now,
            "due_date": due_date or None,
            "status": "in_progress",
            "completed_at": None,
            "completion_percentage": 0.0,
        },
    )
    assignment_id = assignment.get("id")

    # Create step progress records for every step in the template
    all_steps = _get_all_steps_for_template(template_id)
    for step in all_steps:
        dataflow_crud.create(
            "OnboardingStepProgress",
            {
                "assignment_id": assignment_id,
                "step_id": step["id"],
                "employee_id": employee_id,
                "status": "pending",
                "completed_at": None,
                "completed_by": None,
                "document_url": "",
                "form_data": "",
                "notes": "",
                "acknowledged_at": None,
            },
        )

    logger.info(
        "Onboarding assigned: assignment_id=%s, employee_id=%s, template_id=%s, steps=%d",
        assignment_id,
        employee_id,
        template_id,
        len(all_steps),
    )
    return {
        "assignment": assignment,
        "steps_created": len(all_steps),
    }


@router.post("/assign-bulk")
async def assign_template_bulk(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Assign an onboarding template to multiple employees at once."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"onboarding_bulk:{company_id}",
        max_requests=10,
        window_seconds=3600,
        action_name="bulk onboarding assignment",
    )

    body = await request.json()
    employee_ids = body.get("employee_ids", [])
    template_id = body.get("template_id")
    due_date = body.get("due_date")

    if not employee_ids or not isinstance(employee_ids, list):
        raise HTTPException(status_code=400, detail="employee_ids must be a non-empty list.")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id is required.")

    if len(employee_ids) > 200:
        raise HTTPException(status_code=400, detail="Cannot assign to more than 200 employees at once.")

    # Verify template
    template = _verify_template_ownership(template_id, company_id)
    if not template.get("is_active", True):
        raise HTTPException(status_code=400, detail="Cannot assign an archived template.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()
    all_steps = _get_all_steps_for_template(template_id)

    results: list[dict] = []
    errors: list[dict] = []

    for emp_id in employee_ids:
        # Verify employee
        employee = dataflow_crud.read("Employee", emp_id)
        if not employee or employee.get("company_id") != company_id:
            errors.append({"employee_id": emp_id, "error": "Employee not found in this company."})
            continue

        # Check for existing active assignment
        existing = dataflow_crud.list_records(
            "OnboardingAssignment",
            {"employee_id": emp_id, "template_id": template_id, "company_id": company_id},
        )
        active_existing = [
            a for a in existing if a.get("status") in ("in_progress", "overdue")
        ]
        if active_existing:
            errors.append({"employee_id": emp_id, "error": "Already has an active assignment."})
            continue

        assignment = dataflow_crud.create(
            "OnboardingAssignment",
            {
                "employee_id": emp_id,
                "template_id": template_id,
                "template_version": template.get("version", 1),
                "company_id": company_id,
                "assigned_by": actor_id,
                "assigned_at": now,
                "due_date": due_date or None,
                "status": "in_progress",
                "completed_at": None,
                "completion_percentage": 0.0,
            },
        )
        assignment_id = assignment.get("id")

        for step in all_steps:
            dataflow_crud.create(
                "OnboardingStepProgress",
                {
                    "assignment_id": assignment_id,
                    "step_id": step["id"],
                    "employee_id": emp_id,
                    "status": "pending",
                    "completed_at": None,
                    "completed_by": None,
                    "document_url": "",
                    "form_data": "",
                    "notes": "",
                    "acknowledged_at": None,
                },
            )

        results.append({"employee_id": emp_id, "assignment_id": assignment_id})

    logger.info(
        "Bulk onboarding assigned: template_id=%s, success=%d, errors=%d",
        template_id,
        len(results),
        len(errors),
    )
    return {
        "assigned": results,
        "errors": errors,
        "total_assigned": len(results),
        "total_errors": len(errors),
    }


@router.get("/assignments")
async def list_assignments(
    status: str = Query(None, description="Filter by status: in_progress, completed, overdue"),
    employee_id: int = Query(None, description="Filter by employee ID"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List onboarding assignments, with optional filters."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        valid_statuses = {"in_progress", "completed", "overdue", "cancelled"}
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status filter. Must be one of: {', '.join(sorted(valid_statuses))}.",
            )
        filters["status"] = status
    if employee_id:
        filters["employee_id"] = employee_id

    assignments = dataflow_crud.list_records("OnboardingAssignment", filters)

    # Enrich each assignment
    enriched = [_enrich_assignment(a) for a in assignments]

    return {"assignments": enriched, "count": len(enriched)}


@router.get("/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a single assignment with full progress details."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    assignment = _verify_assignment_ownership(assignment_id, company_id)
    assignment = _enrich_assignment(assignment)

    # Fetch step progress with step details
    progress_records = dataflow_crud.list_records(
        "OnboardingStepProgress",
        {"assignment_id": assignment_id},
    )

    # Enrich progress with step metadata
    enriched_progress = []
    for prog in progress_records:
        step = dataflow_crud.read("OnboardingStep", prog.get("step_id"))
        if step:
            prog["step_title"] = step.get("title", "")
            prog["step_type"] = step.get("step_type", "")
            prog["step_description"] = step.get("description", "")
            prog["module_id"] = step.get("module_id")
        enriched_progress.append(prog)

    # Group progress by module
    modules = _get_modules_for_template(assignment.get("template_id"))
    module_map = {m["id"]: {**m, "steps_progress": []} for m in modules}
    for prog in enriched_progress:
        mid = prog.get("module_id")
        if mid and mid in module_map:
            module_map[mid]["steps_progress"].append(prog)

    assignment["modules"] = list(module_map.values())
    return {"assignment": assignment}


@router.delete("/assignments/{assignment_id}")
async def cancel_assignment(
    assignment_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Cancel an onboarding assignment."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    assignment = _verify_assignment_ownership(assignment_id, company_id)

    if assignment.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed assignment.")

    dataflow_crud.update(
        "OnboardingAssignment",
        assignment_id,
        {"status": "cancelled"},
    )

    logger.info("Onboarding assignment cancelled: id=%s", assignment_id)
    return {"message": "Assignment cancelled.", "assignment_id": assignment_id}


@router.get("/employees/{employee_id}/onboarding")
async def get_employee_onboarding(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Shortcut: get an employee's latest active onboarding assignment."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Verify employee belongs to company
    employee = dataflow_crud.read("Employee", employee_id)
    if not employee or employee.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found in this company.")

    assignments = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"employee_id": employee_id, "company_id": company_id},
    )

    # Find latest active (in_progress or overdue)
    active = [a for a in assignments if a.get("status") in ("in_progress", "overdue")]
    if not active:
        return {"assignment": None, "message": "No active onboarding assignment."}

    # Sort by assigned_at descending, pick latest
    active.sort(key=lambda a: a.get("assigned_at", ""), reverse=True)
    latest = _enrich_assignment(active[0])
    return {"assignment": latest}


# ==========================================================================
# EMPLOYEE SELF-SERVICE
# ==========================================================================


@router.get("/my-progress")
async def get_my_progress(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the current user's active onboarding progress.

    Returns null/empty if no active onboarding, not 404.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if not employee:
        return {"assignment": None, "message": "No employee record found."}

    employee_id = employee.get("id")
    assignments = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"employee_id": employee_id, "company_id": company_id},
    )

    # Find active assignment
    active = [a for a in assignments if a.get("status") in ("in_progress", "overdue")]
    if not active:
        return {"assignment": None, "message": "No active onboarding."}

    active.sort(key=lambda a: a.get("assigned_at", ""), reverse=True)
    assignment = active[0]
    assignment = _enrich_assignment(assignment)

    # Fetch step progress with step details
    progress_records = dataflow_crud.list_records(
        "OnboardingStepProgress",
        {"assignment_id": assignment["id"]},
    )

    enriched_progress = []
    for prog in progress_records:
        step = dataflow_crud.read("OnboardingStep", prog.get("step_id"))
        if step:
            prog["step_title"] = step.get("title", "")
            prog["step_type"] = step.get("step_type", "")
            prog["step_description"] = step.get("description", "")
            prog["body_content"] = step.get("body_content", "")
            prog["checklist_items"] = step.get("checklist_items", "")
            prog["media_url"] = step.get("media_url", "")
            prog["module_id"] = step.get("module_id")
        enriched_progress.append(prog)

    # Group by module for structured response
    modules = _get_modules_for_template(assignment.get("template_id"))
    module_progress = []
    for module in modules:
        mod_steps = [p for p in enriched_progress if p.get("module_id") == module["id"]]
        mod_completed = sum(1 for s in mod_steps if s.get("status") == "completed")
        module_progress.append({
            "module_id": module["id"],
            "module_name": module.get("name", ""),
            "phase": module.get("phase", ""),
            "is_mandatory": module.get("is_mandatory", True),
            "steps": mod_steps,
            "step_count": len(mod_steps),
            "completed_count": mod_completed,
        })

    assignment["modules"] = module_progress
    return {"assignment": assignment}


@router.post("/steps/{progress_id}/complete")
async def complete_step(
    progress_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Mark a step as completed. Verifies the step belongs to the user's assignment."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found.")

    # Verify the progress record exists and belongs to this employee
    progress = dataflow_crud.read("OnboardingStepProgress", progress_id)
    if not progress or progress.get("employee_id") != employee.get("id"):
        raise HTTPException(status_code=404, detail="Step progress not found.")

    if progress.get("status") == "completed":
        return {"message": "Step already completed.", "progress": progress}

    # Verify assignment is still active
    assignment = dataflow_crud.read("OnboardingAssignment", progress.get("assignment_id"))
    if not assignment or assignment.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if assignment.get("status") not in ("in_progress", "overdue"):
        raise HTTPException(status_code=400, detail="Assignment is not active.")

    # Check sequential enforcement
    step = dataflow_crud.read("OnboardingStep", progress.get("step_id"))
    if step and step.get("requires_previous_completion"):
        module_id = step.get("module_id")
        module_steps = _get_steps_for_module(module_id)
        current_order = step.get("sort_order", 0)
        # Find all steps with lower order in this module
        for prev_step in module_steps:
            if prev_step.get("sort_order", 0) < current_order and prev_step.get("requires_completion", True):
                # Check if previous step is completed
                prev_progress = dataflow_crud.list_records(
                    "OnboardingStepProgress",
                    {
                        "assignment_id": progress.get("assignment_id"),
                        "step_id": prev_step["id"],
                    },
                    limit=1,
                )
                if prev_progress and prev_progress[0].get("status") != "completed":
                    raise HTTPException(
                        status_code=400,
                        detail="Previous required steps must be completed first.",
                    )

    # Optional notes from body
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": "completed",
        "completed_at": now,
        "completed_by": user_id,
    }
    _validate_step_content_fields(body)
    if body.get("notes"):
        updates["notes"] = body["notes"]
    if body.get("form_data"):
        updates["form_data"] = body["form_data"]

    result = dataflow_crud.update("OnboardingStepProgress", progress_id, updates)

    # Update assignment status/completion
    _update_assignment_status(progress.get("assignment_id"))

    logger.info(
        "Onboarding step completed: progress_id=%s, employee_id=%s",
        progress_id,
        employee.get("id"),
    )
    return {"message": "Step completed.", "progress": result}


@router.post("/steps/{progress_id}/upload")
async def upload_step_document(
    progress_id: int,
    file: UploadFile = File(..., description="Document file (PDF, JPG, PNG, or DOCX)"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Upload a document for a document_upload step.

    Validates file type (PDF/JPG/PNG/DOCX), max 10MB, UUID filename,
    and magic-byte content verification.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found.")

    # Verify the progress record exists and belongs to this employee
    progress = dataflow_crud.read("OnboardingStepProgress", progress_id)
    if not progress or progress.get("employee_id") != employee.get("id"):
        raise HTTPException(status_code=404, detail="Step progress not found.")

    # Verify this is a document_upload step
    step = dataflow_crud.read("OnboardingStep", progress.get("step_id"))
    if not step or step.get("step_type") != "document_upload":
        raise HTTPException(status_code=400, detail="This step does not accept document uploads.")

    # Verify assignment is still active
    assignment = dataflow_crud.read("OnboardingAssignment", progress.get("assignment_id"))
    if not assignment or assignment.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if assignment.get("status") not in ("in_progress", "overdue"):
        raise HTTPException(status_code=400, detail="Assignment is not active.")

    # Validate filename extension
    original_filename = file.filename or ""
    _, ext = os.path.splitext(original_filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )

    # Validate content type
    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Content type not allowed. Accepted: {', '.join(sorted(ALLOWED_MIME_TYPES))}.",
        )

    # Read and validate file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )
    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Validate magic bytes match the claimed extension
    _validate_magic_bytes(file_content, ext)

    # Save file with UUID filename
    import stat

    safe_filename = _sanitize_filename(ext)
    company_dir = os.path.join(ONBOARDING_UPLOAD_DIR, str(company_id))
    os.makedirs(company_dir, mode=0o700, exist_ok=True)
    file_path = os.path.join(company_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(file_content)
    os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)

    # Construct relative URL
    document_url = f"/uploads/documents/onboarding/{company_id}/{safe_filename}"

    # Update progress record
    now = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update(
        "OnboardingStepProgress",
        progress_id,
        {
            "document_url": document_url,
            "status": "completed",
            "completed_at": now,
            "completed_by": user_id,
        },
    )

    # Update assignment status
    _update_assignment_status(progress.get("assignment_id"))

    logger.info(
        "Onboarding document uploaded: progress_id=%s, file=%s",
        progress_id,
        safe_filename,
    )
    return {
        "message": "Document uploaded.",
        "progress": result,
        "document_url": document_url,
    }


@router.post("/steps/{progress_id}/acknowledge")
async def acknowledge_policy_step(
    progress_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Acknowledge a policy step. Also creates a PolicyAcknowledgment record."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found.")

    employee_id = employee.get("id")

    # Verify the progress record
    progress = dataflow_crud.read("OnboardingStepProgress", progress_id)
    if not progress or progress.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Step progress not found.")

    # Verify this is a policy_acknowledgment step
    step = dataflow_crud.read("OnboardingStep", progress.get("step_id"))
    if not step or step.get("step_type") != "policy_acknowledgment":
        raise HTTPException(status_code=400, detail="This step is not a policy acknowledgment step.")

    policy_id = step.get("policy_id")
    if not policy_id:
        raise HTTPException(status_code=400, detail="No policy linked to this step.")

    # Verify assignment is still active
    assignment = dataflow_crud.read("OnboardingAssignment", progress.get("assignment_id"))
    if not assignment or assignment.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if assignment.get("status") not in ("in_progress", "overdue"):
        raise HTTPException(status_code=400, detail="Assignment is not active.")

    # Already acknowledged?
    if progress.get("status") == "completed" and progress.get("acknowledged_at"):
        return {"message": "Policy already acknowledged.", "progress": progress}

    now = datetime.now(timezone.utc).isoformat()

    # Create PolicyAcknowledgment record (if not already present for this version)
    policy = dataflow_crud.read("CompanyPolicy", policy_id)
    if policy and policy.get("company_id") == company_id:
        version_number = policy.get("version_number", 1)

        existing_ack = dataflow_crud.list_records(
            "PolicyAcknowledgment",
            {
                "company_id": company_id,
                "policy_id": policy_id,
                "employee_id": employee_id,
                "version_acknowledged": version_number,
            },
            limit=1,
        )
        if not existing_ack:
            # Extract client IP for audit
            ip_address = ""
            try:
                client = request.client
                if client:
                    ip_address = client.host or ""
            except Exception:
                pass

            dataflow_crud.create(
                "PolicyAcknowledgment",
                {
                    "company_id": company_id,
                    "policy_id": policy_id,
                    "employee_id": employee_id,
                    "version_acknowledged": version_number,
                    "acknowledged_at": now,
                    "ip_address": ip_address,
                },
            )
            logger.info(
                "PolicyAcknowledgment created via onboarding: policy_id=%s, employee_id=%s",
                policy_id,
                employee_id,
            )

    # Update onboarding step progress
    result = dataflow_crud.update(
        "OnboardingStepProgress",
        progress_id,
        {
            "status": "completed",
            "completed_at": now,
            "completed_by": user_id,
            "acknowledged_at": now,
        },
    )

    # Update assignment status
    _update_assignment_status(progress.get("assignment_id"))

    logger.info(
        "Onboarding policy step acknowledged: progress_id=%s, policy_id=%s",
        progress_id,
        policy_id,
    )
    return {"message": "Policy acknowledged.", "progress": result}


@router.post("/steps/{progress_id}/approve")
async def approve_step(
    progress_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Approve an approval-type onboarding step on behalf of an employee.

    Only HR managers and owners can approve. Verifies the step belongs to the
    admin's company and that the step_type is "approval".
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    admin_user_id = int(current_user.get("sub", 0))

    # 1. Verify the progress record exists and belongs to this company
    progress = dataflow_crud.read("OnboardingStepProgress", progress_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Step progress not found.")

    assignment = dataflow_crud.read("OnboardingAssignment", progress.get("assignment_id"))
    if not assignment or assignment.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Step progress not found.")

    # 2. Verify the step type is "approval"
    step = dataflow_crud.read("OnboardingStep", progress.get("step_id"))
    if not step or step.get("step_type") != "approval":
        raise HTTPException(status_code=400, detail="This step is not an approval step.")

    # Already completed?
    if progress.get("status") == "completed":
        return {"message": "Step already approved.", "progress": progress}

    # Verify assignment is still active
    if assignment.get("status") not in ("in_progress", "overdue"):
        raise HTTPException(status_code=400, detail="Assignment is not active.")

    # Optional notes from body
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": "completed",
        "completed_at": now,
        "completed_by": admin_user_id,
    }
    if body.get("notes"):
        _validate_text_length(body["notes"], "notes", MAX_NOTES_LENGTH)
        updates["notes"] = body["notes"]

    result = dataflow_crud.update("OnboardingStepProgress", progress_id, updates)

    # 5. Update assignment completion percentage
    updated_assignment = _update_assignment_status(progress.get("assignment_id"))

    logger.info(
        "Onboarding step approved: progress_id=%s, approved_by=%s, employee_id=%s",
        progress_id,
        admin_user_id,
        progress.get("employee_id"),
    )
    return {
        "message": "Step approved.",
        "progress": result,
        "assignment_completion_percentage": updated_assignment.get("completion_percentage", 0),
    }


# ==========================================================================
# PRE-BOARDING (admin)
# ==========================================================================


@router.get("/preboarding/{employee_id}")
async def list_preboarding_tasks(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List pre-boarding tasks for an employee."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Verify employee belongs to company
    employee = dataflow_crud.read("Employee", employee_id)
    if not employee or employee.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found in this company.")

    tasks = dataflow_crud.list_records(
        "PreboardingTaskInstance",
        {"employee_id": employee_id, "company_id": company_id},
    )

    # Check overdue tasks
    now = datetime.now(timezone.utc)
    for task in tasks:
        if task.get("status") == "pending" and task.get("deadline_date"):
            try:
                deadline = datetime.fromisoformat(task["deadline_date"])
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                task["is_overdue"] = now > deadline
            except (ValueError, TypeError):
                task["is_overdue"] = False
        else:
            task["is_overdue"] = False

    pending = [t for t in tasks if t.get("status") == "pending"]
    done = [t for t in tasks if t.get("status") == "done"]

    return {
        "tasks": tasks,
        "total": len(tasks),
        "pending": len(pending),
        "done": len(done),
    }


@router.patch("/preboarding/{task_id}")
async def update_preboarding_task(
    task_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Mark a pre-boarding task as done (or update notes)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    task = dataflow_crud.read("PreboardingTaskInstance", task_id)
    if not task or task.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Pre-boarding task not found.")

    body = await request.json()
    updates: dict = {}

    if body.get("status") == "done" and task.get("status") != "done":
        actor_id = int(current_user.get("sub", 0))
        updates["status"] = "done"
        updates["completed_at"] = datetime.now(timezone.utc).isoformat()
        updates["completed_by"] = actor_id

    if "notes" in body:
        _validate_text_length(body["notes"], "notes")
        updates["notes"] = body["notes"]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = dataflow_crud.update("PreboardingTaskInstance", task_id, updates)
    logger.info("Pre-boarding task updated: id=%s, status=%s", task_id, result.get("status"))
    return {"task": result}
