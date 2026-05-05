"""Onboarding management endpoints.

Handles onboarding templates, modules, steps, employee assignments,
progress tracking, pre-boarding tasks, and employee self-service.

Roles:
    owner, hr_manager — template CRUD, module/step management, assignments, pre-boarding
    employee — self-service progress, step completion, document upload, policy acknowledgment
"""

import csv
import html
import io
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import Response

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()


# S3-T7: per-tenant lock guarding the "set is_default" sequence on
# OnboardingTemplate. The clear-then-set pattern (unset every other
# template, then set this one) is non-atomic; two concurrent POSTs
# could each see only the OLD default, both un-set it, both set their
# own template default → leaving two defaults. The lock serializes the
# full sequence within a process. Multi-worker deploys should add a
# DB-level partial unique index on (company_id) WHERE is_default=TRUE.
_default_template_locks: dict[int, threading.Lock] = {}
_default_template_locks_lock = threading.Lock()


def _get_default_template_lock(company_id: int) -> threading.Lock:
    with _default_template_locks_lock:
        lock = _default_template_locks.get(company_id)
        if lock is None:
            lock = threading.Lock()
            _default_template_locks[company_id] = lock
        return lock


# B19: shared MAX_TEXT_LENGTH, MAX_NAME_LENGTH, _validate_text_length come
# from _helpers.py. Onboarding-specific limits stay local below.
from hr_advisory.api.routers._helpers import (  # noqa: E402
    MAX_TEXT_LENGTH,
    MAX_NAME_LENGTH,
    _validate_text_length,
)

# Input length limits (onboarding-specific)
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
# Internal helpers (text-length helper imported from _helpers.py — B19)
# --------------------------------------------------------------------------


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


def _ensure_unique_template_name(
    company_id: int,
    name: str,
    *,
    exclude_template_id: int | None = None,
) -> None:
    """Reject the request if another active template in the company has this name.

    Round-12 redteam H4: prod had three active templates named
    'HR Technology / SaaS Onboarding'. Admins couldn't tell which one
    new hires would actually be assigned to. Names are now unique per
    (company_id, active) — case-insensitive, whitespace-collapsed.
    """
    normalized = " ".join(name.split()).casefold()
    existing = dataflow_crud.list_records(
        "OnboardingTemplate",
        {"company_id": company_id, "is_active": True},
        cache_ttl=0,
    )
    for t in existing:
        if exclude_template_id is not None and t.get("id") == exclude_template_id:
            continue
        other = " ".join((t.get("name") or "").split()).casefold()
        if other == normalized:
            raise HTTPException(
                status_code=409,
                detail=(
                    "An active onboarding template with this name already exists. "
                    "Pick a different name or archive the existing one first."
                ),
            )


def _next_available_template_name(company_id: int, base_name: str) -> str:
    """Return `base_name`, or `base_name (Copy 2)`, etc. if it collides.

    Used by the duplicate endpoint so repeated duplications don't crash.
    """
    candidate = base_name
    suffix = 2
    while True:
        try:
            _ensure_unique_template_name(company_id, candidate)
            return candidate
        except HTTPException:
            candidate = f"{base_name} {suffix}"
            suffix += 1
            if suffix > 100:
                # Pathological case — surface as 409 rather than spin forever.
                raise HTTPException(
                    status_code=409,
                    detail="Too many duplicate templates with this base name.",
                )


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


def _get_steps_for_module(module_id: int, include_archived: bool = False) -> list[dict]:
    """Fetch all steps for a module, sorted by order.

    S3-T5: by default, archived (`is_active=False`) steps are filtered out
    so employees on a NEW assignment do not see soft-deleted steps. Pass
    `include_archived=True` for admin views (template editor, audit) where
    archived rows should still be visible. Existing OnboardingAssignments
    keep their step progress regardless — assignments resolve steps from
    their own `OnboardingStepProgress` rows, not from a fresh fetch here.
    """
    steps = dataflow_crud.list_records(
        "OnboardingStep",
        {"module_id": module_id},
    )
    if not include_archived:
        steps = [s for s in steps if s.get("is_active", True)]
    return sorted(steps, key=lambda s: s.get("sort_order", 0))


def _get_all_steps_for_template(
    template_id: int,
    employee: dict | None = None,
) -> list[dict]:
    """Fetch all steps across all modules for a template.

    When *employee* is provided, modules are filtered by role_filter:
    - If a module's role_filter is empty/null, it is universal and always included.
    - If role_filter is a JSON array, the module is included only when the
      employee's designation or department (case-insensitive) matches an entry.
    """
    modules = _get_modules_for_template(template_id)

    if employee is not None:
        emp_designation = (employee.get("designation") or "").strip().lower()
        emp_department = (employee.get("department") or "").strip().lower()
        filtered_modules = []
        for mod in modules:
            role_filter_str = mod.get("role_filter", "")
            if role_filter_str:
                try:
                    roles = json.loads(role_filter_str)
                    if isinstance(roles, list) and roles:
                        roles_lower = [r.strip().lower() for r in roles if r]
                        if emp_designation not in roles_lower and emp_department not in roles_lower:
                            continue  # skip module — does not match employee
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Malformed role_filter on module %s — skipping", mod.get("id"))
                    continue  # fail-closed: skip module with bad filter
            filtered_modules.append(mod)
        modules = filtered_modules

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
        cache_ttl=0,
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
    now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    updates: dict = {"completion_percentage": percentage}

    if completed == total and total > 0:
        updates["status"] = "completed"
        updates["completed_at"] = now_dt
    elif assignment.get("due_date"):
        due_str = assignment["due_date"]
        try:
            due_date = datetime.fromisoformat(due_str)
            if due_date.tzinfo:
                due_date = due_date.replace(tzinfo=None)
            if now_dt > due_date and assignment.get("status") != "completed":
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

    # Enrich with employee name and department
    employee = dataflow_crud.read("Employee", assignment.get("employee_id"))
    if employee:
        user = dataflow_crud.read("User", employee.get("user_id"))
        assignment["employee_name"] = user.get("name", "") if user else ""
        assignment["department"] = employee.get("department", "")
    else:
        assignment["employee_name"] = ""
        assignment["department"] = ""

    # Enrich with template name
    template = dataflow_crud.read("OnboardingTemplate", assignment.get("template_id"))
    if template:
        assignment["template_name"] = template.get("name", "")

    # Enrich with buddy details
    buddy_eid = assignment.get("buddy_employee_id")
    if buddy_eid:
        buddy_emp = dataflow_crud.read("Employee", buddy_eid)
        if buddy_emp:
            buddy_user = dataflow_crud.read("User", buddy_emp.get("user_id"))
            assignment["buddy_name"] = buddy_user.get("name", "") if buddy_user else ""
            assignment["buddy_email"] = buddy_user.get("email", "") if buddy_user else ""
            assignment["buddy_department"] = buddy_emp.get("department", "")
            assignment["buddy_designation"] = buddy_emp.get("designation", "")

    return assignment


def auto_assign_default_onboarding(
    employee_id: int,
    company_id: int,
    employee: dict | None = None,
) -> dict | None:
    """Auto-assign the company's default onboarding template to an employee.

    Called during employee registration to give new hires their onboarding
    path automatically. Returns the assignment dict on success, or None
    if no default template exists or the assignment cannot be created.

    This function is intentionally non-raising so that callers can wrap it
    in a try/except without risking the parent operation.
    """
    # Find the company's default template
    templates = dataflow_crud.list_records(
        "OnboardingTemplate",
        {"company_id": company_id, "is_default": True},
    )
    active_defaults = [t for t in templates if t.get("is_active", True)]
    if not active_defaults:
        return None

    template = active_defaults[0]
    template_id = template["id"]

    # Load the employee record if not provided
    if employee is None:
        employee = dataflow_crud.read("Employee", employee_id)
    if not employee:
        logger.warning(
            "auto_assign_default_onboarding: employee_id=%s not found", employee_id
        )
        return None
    if employee.get("company_id") != company_id:
        logger.warning(
            "auto_assign_default_onboarding: employee %s does not belong to company %s",
            employee_id, company_id,
        )
        return None

    # Check for existing active assignment (avoid duplicates)
    existing = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"employee_id": employee_id, "template_id": template_id, "company_id": company_id},
    )
    active_existing = [a for a in existing if a.get("status") in ("in_progress", "overdue")]
    if active_existing:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    # Create the assignment
    assignment = dataflow_crud.create(
        "OnboardingAssignment",
        {
            "employee_id": employee_id,
            "template_id": template_id,
            "template_version": template.get("version", 1),
            "company_id": company_id,
            "assigned_by": 0,  # system-assigned
            "assigned_at": now,
            "due_date": None,
            "status": "in_progress",
            "completed_at": None,
            "completion_percentage": 0.0,
            "buddy_employee_id": None,
        },
    )
    assignment_id = assignment.get("id")

    # Create role-filtered step progress records
    all_steps = _get_all_steps_for_template(template_id, employee=employee)
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

    # Copy template-level pre-boarding tasks
    try:
        template_tasks = dataflow_crud.list_records(
            "PreboardingTaskInstance",
            {"template_id": template_id, "employee_id": 0},
        )
        start_date = employee.get("start_date", "")
        for task in template_tasks:
            task_data = {
                "company_id": company_id,
                "template_id": template_id,
                "employee_id": employee_id,
                "task_name": task.get("task_name", ""),
                "owner_role": task.get("owner_role", "hr"),
                "trigger": task.get("trigger", ""),
                "status": "pending",
                "notes": task.get("notes", ""),
            }
            if start_date and task.get("notes", ""):
                try:
                    days_match = re.search(
                        r"(-?\d+)\s*days?\s*(?:before|relative)",
                        task.get("notes", ""),
                    )
                    if days_match:
                        rel_days = int(days_match.group(1))
                        sd = (
                            datetime.fromisoformat(start_date)
                            if isinstance(start_date, str)
                            else start_date
                        )
                        task_data["deadline_date"] = (sd + timedelta(days=rel_days)).isoformat()
                except (ValueError, TypeError):
                    pass
            dataflow_crud.create("PreboardingTaskInstance", task_data)
    except Exception as exc:
        logger.warning("auto_assign: failed to create pre-boarding tasks: %s", exc)

    # Auto-create 30/60/90-day review milestones
    try:
        start_date = employee.get("start_date", "")
        if start_date:
            base_date = (
                datetime.fromisoformat(start_date)
                if isinstance(start_date, str)
                else start_date
            )
        else:
            base_date = datetime.fromisoformat(now) if isinstance(now, str) else now
        for mtype, days in [("day_30", 30), ("day_60", 60), ("day_90", 90)]:
            scheduled = (base_date + timedelta(days=days)).isoformat()
            dataflow_crud.create(
                "OnboardingMilestone",
                {
                    "assignment_id": assignment_id,
                    "company_id": company_id,
                    "employee_id": employee_id,
                    "milestone_type": mtype,
                    "scheduled_date": scheduled,
                    "status": "pending",
                    "completed_at": None,
                    "notes": "",
                    "reviewed_by": None,
                },
            )
    except Exception as exc:
        logger.warning("auto_assign: failed to create milestones: %s", exc)

    logger.info(
        "Auto-assigned default onboarding: assignment_id=%s, employee_id=%s, template_id=%s, steps=%d",
        assignment_id,
        employee_id,
        template_id,
        len(all_steps),
    )
    return assignment


def _sanitize_filename(extension: str) -> str:
    """Generate a UUID-based safe filename with the given extension."""
    return f"{uuid.uuid4().hex}{extension}"


def _sanitize_csv_filename(title: str, extension: str = ".csv") -> str:
    """Sanitize a title for use in Content-Disposition headers.

    Removes all characters except alphanumeric, hyphen, underscore, dot, and space.
    Replaces spaces with hyphens, truncates to 100 characters.
    """
    safe = re.sub(r"[^a-zA-Z0-9\-_. ]", "", title)
    safe = safe.replace(" ", "-")
    safe = re.sub(r"-+", "-", safe).strip("-")
    max_base = 100 - len(extension)
    if len(safe) > max_base:
        safe = safe[:max_base]
    if not safe:
        safe = "export"
    return safe + extension


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

    # H4: reject creates that collide with an existing active template name.
    _ensure_unique_template_name(company_id, name)

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    # If marked as default, unset existing defaults for this company.
    # S3-T7: serialize the clear-then-set sequence under a per-tenant lock.
    is_default = body.get("is_default", False)
    if is_default:
        with _get_default_template_lock(company_id):
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
                    "is_default": True,
                    "version": 1,
                    "is_active": True,
                    "created_by": actor_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )
    else:
        template = dataflow_crud.create(
            "OnboardingTemplate",
            {
                "company_id": company_id,
                "name": name,
                "description": body.get("description", ""),
                "is_default": False,
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
    # S3-T5: this endpoint is admin-only (owner/hr_manager) — include archived
    # steps so the template editor can show greyed-out soft-deleted rows.
    modules = _get_modules_for_template(template_id)
    modules_with_steps = []
    total_steps = 0
    total_estimated_minutes = 0
    for module in modules:
        steps = _get_steps_for_module(module.get("id"), include_archived=True)
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

    updates: dict = {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}

    if "name" in body:
        name = body["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="Template name cannot be empty.")
        _validate_text_length(name, "name", MAX_NAME_LENGTH)
        # H4: a rename collides with another active template -> 409.
        _ensure_unique_template_name(
            company_id, name, exclude_template_id=template_id
        )
        updates["name"] = name

    if "description" in body:
        _validate_text_length(body["description"], "description")
        updates["description"] = body["description"]

    # S3-T7: serialize the clear-then-set under a per-tenant lock to
    # prevent two concurrent updates from leaving two defaults.
    if "is_default" in body and body["is_default"]:
        with _get_default_template_lock(company_id):
            existing = dataflow_crud.list_records(
                "OnboardingTemplate",
                {"company_id": company_id, "is_default": True},
            )
            for t in existing:
                if t["id"] != template_id:
                    dataflow_crud.update("OnboardingTemplate", t["id"], {"is_default": False})
            updates["is_default"] = True
            # Increment version (inside lock so version bump is also serialized)
            updates["version"] = template.get("version", 1) + 1
            result = dataflow_crud.update("OnboardingTemplate", template_id, updates)
            logger.info("Onboarding template updated: id=%s, version=%s", template_id, updates["version"])
            return {"template": result}

    if "is_default" in body:
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
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
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
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    new_name = body.get("name", f"{template.get('name', '')} (Copy)").strip()
    _validate_text_length(new_name, "name", MAX_NAME_LENGTH)
    # H4: when the user supplied a name, surface the collision as a 409 so
    # they can pick another. When we generated the "(Copy)" suffix, append
    # an integer suffix until it's unique rather than failing.
    if "name" in body:
        _ensure_unique_template_name(company_id, new_name)
    else:
        new_name = _next_available_template_name(company_id, new_name)

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

    check_rate_limit(f"onboarding_upload:{company_id}", max_requests=10, window_seconds=300, action_name="template upload")

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
        logger.warning("Template import validation failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid template format. Please check the file and try again.")
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
    # Onboarding tables use ``timestamp without time zone`` — store naive
    # ISO strings so asyncpg does not mix tz-aware and tz-naive datetimes
    # during downstream reads.
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

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

    # Counters for additionally created records
    preboarding_tasks_created = 0
    policy_steps_created = 0

    # ------------------------------------------------------------------
    # Sheet 1 — Company Profile: enrich template description
    # ------------------------------------------------------------------
    if company_profile:
        desc_parts = [f"Imported from {original_filename}"]
        if company_profile.get("company_name"):
            desc_parts.append(f"Company: {company_profile['company_name']}")
        if company_profile.get("mission"):
            desc_parts.append(f"Mission: {company_profile['mission']}")
        if company_profile.get("vision"):
            desc_parts.append(f"Vision: {company_profile['vision']}")
        core_values = company_profile.get("core_values", [])
        if core_values:
            desc_parts.append(f"Core Values: {', '.join(core_values)}")
        enriched_desc = "\n".join(desc_parts)
        dataflow_crud.update(
            "OnboardingTemplate",
            template_id,
            {"description": enriched_desc[:MAX_BODY_CONTENT_LENGTH], "updated_at": now},
        )

    # ------------------------------------------------------------------
    # Sheet 2 — Org Structure: add department overview step
    # ------------------------------------------------------------------
    departments = parsed.get("departments", [])
    if departments:
        # Find the first Orientation module
        orientation_module_id = None
        all_modules = _get_modules_for_template(template_id)
        for m in all_modules:
            if m.get("phase") == "orientation":
                orientation_module_id = m.get("id")
                break

        if orientation_module_id is None and module_id_map:
            # Fallback: use the first module
            orientation_module_id = next(iter(module_id_map.values()))

        if orientation_module_id is not None:
            dept_lines = ["## Department Overview\n"]
            for dept in departments:
                name = dept.get("department_name", "Unknown")
                head = dept.get("department_head", "")
                title = dept.get("head_title", "")
                desc = dept.get("description", "")
                size = dept.get("team_size", "")
                line = f"**{name}**"
                if head:
                    head_str = f"{head} ({title})" if title else head
                    line += f" — Led by {head_str}"
                if size:
                    line += f" | Team size: {size}"
                if desc:
                    line += f"\n{desc}"
                dept_lines.append(line)
            dept_body = "\n\n".join(dept_lines)

            order = step_order_by_module.get(orientation_module_id, 0)
            step_order_by_module[orientation_module_id] = order + 1
            dataflow_crud.create(
                "OnboardingStep",
                {
                    "module_id": orientation_module_id,
                    "title": "Department Overview",
                    "description": "Overview of company departments and leadership",
                    "sort_order": order,
                    "step_type": "content",
                    "body_content": dept_body[:MAX_BODY_CONTENT_LENGTH],
                    "checklist_items": "",
                    "media_url": "",
                    "requires_completion": True,
                    "policy_id": None,
                    "requires_previous_completion": False,
                },
            )
            steps_created += 1

    # ------------------------------------------------------------------
    # Sheet 5 — Role Configuration: set role_filter + store metadata
    # ------------------------------------------------------------------
    role_configs = parsed.get("role_configs", [])
    if role_configs:
        # Set role_filter on matching modules
        all_modules = _get_modules_for_template(template_id)
        for rc in role_configs:
            role_name = rc.get("role", "")
            additional_modules = rc.get("additional_modules", [])
            if role_name and additional_modules:
                for mod in all_modules:
                    if mod.get("name") in additional_modules:
                        existing_filter = mod.get("role_filter", "")
                        try:
                            roles = json.loads(existing_filter) if existing_filter else []
                        except (json.JSONDecodeError, TypeError):
                            roles = []
                        if role_name not in roles:
                            roles.append(role_name)
                        dataflow_crud.update(
                            "OnboardingModule",
                            mod.get("id"),
                            {"role_filter": json.dumps(roles)},
                        )

        # Store buddy info and 30-60-90 goals as template metadata
        metadata_parts = []
        for rc in role_configs:
            role_name = rc.get("role", "Unknown")
            buddy = rc.get("buddy_assignment", "")
            goals = rc.get("goals_summary", "")
            if buddy or goals:
                part = f"Role: {role_name}"
                if buddy:
                    part += f" | Buddy: {buddy}"
                if goals:
                    part += f" | Goals: {goals}"
                metadata_parts.append(part)
        if metadata_parts:
            # Append role metadata to template description
            tmpl = dataflow_crud.read("OnboardingTemplate", template_id)
            current_desc = tmpl.get("description", "") if tmpl else ""
            role_section = "\n\n--- Role Configuration ---\n" + "\n".join(metadata_parts)
            updated_desc = (current_desc + role_section)[:MAX_BODY_CONTENT_LENGTH]
            dataflow_crud.update(
                "OnboardingTemplate",
                template_id,
                {"description": updated_desc, "updated_at": now},
            )

    # ------------------------------------------------------------------
    # Sheet 6 — IT Provisioning: create PreboardingTaskInstance records
    # ------------------------------------------------------------------
    it_tasks = parsed.get("it_tasks", [])
    for it_task in it_tasks:
        tool_name = it_task.get("tool", "")
        if not tool_name:
            continue
        trigger_val = it_task.get("sla", "") or ""
        notes_parts = []
        if it_task.get("category"):
            notes_parts.append(f"Category: {it_task['category']}")
        if it_task.get("access_level"):
            notes_parts.append(f"Access: {it_task['access_level']}")
        if it_task.get("setup_url"):
            notes_parts.append(f"Setup: {it_task['setup_url']}")
        if it_task.get("notes"):
            notes_parts.append(it_task["notes"])

        dataflow_crud.create(
            "PreboardingTaskInstance",
            {
                "company_id": company_id,
                "template_id": template_id,
                "employee_id": 0,
                "task_name": f"Provision: {tool_name}"[:MAX_NAME_LENGTH],
                "owner_role": "it",
                "trigger": str(trigger_val)[:MAX_TEXT_LENGTH],
                "deadline_date": None,
                "status": "pending",
                "completed_at": None,
                "completed_by": None,
                "notes": " | ".join(notes_parts)[:MAX_NOTES_LENGTH] if notes_parts else "",
            },
        )
        preboarding_tasks_created += 1

    # ------------------------------------------------------------------
    # Sheet 7 — Policies: create policy_acknowledgment steps
    # ------------------------------------------------------------------
    policies = parsed.get("policies", [])
    if policies:
        # Pre-fetch existing company policies for matching
        existing_policies = dataflow_crud.list_records(
            "CompanyPolicy",
            {"company_id": company_id},
        )
        # Build a lookup by normalised title
        policy_lookup: dict[str, dict] = {}
        for ep in existing_policies:
            normalised = (ep.get("title") or "").strip().lower()
            if normalised:
                policy_lookup[normalised] = ep

        # Find or create a compliance module for policy steps
        compliance_module_id = None
        all_modules = _get_modules_for_template(template_id)
        for m in all_modules:
            if m.get("phase") == "compliance":
                compliance_module_id = m.get("id")
                break
        if compliance_module_id is None:
            # Create a compliance module
            new_compliance = dataflow_crud.create(
                "OnboardingModule",
                {
                    "template_id": template_id,
                    "company_id": company_id,
                    "name": "Policies & Compliance",
                    "description": "Company policies requiring review and acknowledgment",
                    "phase": "compliance",
                    "sort_order": modules_created,
                    "estimated_duration_minutes": 30,
                    "is_mandatory": True,
                    "is_role_specific": False,
                    "role_filter": "",
                },
            )
            compliance_module_id = new_compliance.get("id")
            module_id_map["Policies & Compliance"] = compliance_module_id
            modules_created += 1

        for pol in policies:
            policy_name = pol.get("policy_name", "")
            if not policy_name:
                continue

            ack_required = pol.get("acknowledgement_required", "")
            is_ack = True
            if isinstance(ack_required, str):
                is_ack = ack_required.strip().lower() not in ("no", "false", "")
            elif isinstance(ack_required, bool):
                is_ack = ack_required

            # Try to match against existing CompanyPolicy records
            matched_policy = policy_lookup.get(policy_name.strip().lower())
            matched_policy_id = matched_policy.get("id") if matched_policy else None

            order = step_order_by_module.get(compliance_module_id, 0)
            step_order_by_module[compliance_module_id] = order + 1

            if is_ack and matched_policy_id:
                # Policy acknowledgment step linked to existing policy
                dataflow_crud.create(
                    "OnboardingStep",
                    {
                        "module_id": compliance_module_id,
                        "title": f"Acknowledge: {policy_name}"[:MAX_NAME_LENGTH],
                        "description": pol.get("description", "") or "",
                        "sort_order": order,
                        "step_type": "policy_acknowledgment",
                        "body_content": "",
                        "checklist_items": "",
                        "media_url": "",
                        "requires_completion": True,
                        "policy_id": matched_policy_id,
                        "requires_previous_completion": False,
                    },
                )
            else:
                # Content step with policy description
                body_parts = []
                if pol.get("description"):
                    body_parts.append(pol["description"])
                if pol.get("category"):
                    body_parts.append(f"Category: {pol['category']}")
                if pol.get("document_url"):
                    body_parts.append(f"Document: {pol['document_url']}")
                if pol.get("review_deadline"):
                    body_parts.append(f"Review by: {pol['review_deadline']}")
                body = "\n\n".join(body_parts) if body_parts else policy_name

                step_type = "policy_acknowledgment" if is_ack else "content"
                dataflow_crud.create(
                    "OnboardingStep",
                    {
                        "module_id": compliance_module_id,
                        "title": f"Review: {policy_name}"[:MAX_NAME_LENGTH],
                        "description": "",
                        "sort_order": order,
                        "step_type": step_type,
                        "body_content": body[:MAX_BODY_CONTENT_LENGTH],
                        "checklist_items": "",
                        "media_url": "",
                        "requires_completion": True,
                        "policy_id": None,
                        "requires_previous_completion": False,
                    },
                )

            steps_created += 1
            policy_steps_created += 1

    # ------------------------------------------------------------------
    # Sheet 8 — Benefits: create content steps in a Benefits module
    # ------------------------------------------------------------------
    benefits = parsed.get("benefits", [])
    if benefits:
        # Find or create a benefits module
        benefits_module_id = None
        all_modules = _get_modules_for_template(template_id)
        for m in all_modules:
            if m.get("phase") == "benefits":
                benefits_module_id = m.get("id")
                break
        if benefits_module_id is None:
            new_benefits = dataflow_crud.create(
                "OnboardingModule",
                {
                    "template_id": template_id,
                    "company_id": company_id,
                    "name": "Benefits Overview",
                    "description": "Company benefits and enrollment information",
                    "phase": "benefits",
                    "sort_order": modules_created,
                    "estimated_duration_minutes": 15,
                    "is_mandatory": True,
                    "is_role_specific": False,
                    "role_filter": "",
                },
            )
            benefits_module_id = new_benefits.get("id")
            module_id_map["Benefits Overview"] = benefits_module_id
            modules_created += 1

        for ben in benefits:
            benefit_name = ben.get("benefit_name", "")
            if not benefit_name:
                continue

            body_parts = []
            if ben.get("description"):
                body_parts.append(ben["description"])
            if ben.get("category"):
                body_parts.append(f"**Category:** {ben['category']}")
            if ben.get("eligibility"):
                body_parts.append(f"**Eligibility:** {ben['eligibility']}")
            if ben.get("enrollment_deadline"):
                body_parts.append(f"**Enrollment Deadline:** {ben['enrollment_deadline']}")
            if ben.get("provider"):
                body_parts.append(f"**Provider:** {ben['provider']}")
            if ben.get("contact_url"):
                body_parts.append(f"**More Info:** {ben['contact_url']}")
            body = "\n\n".join(body_parts) if body_parts else benefit_name

            order = step_order_by_module.get(benefits_module_id, 0)
            step_order_by_module[benefits_module_id] = order + 1
            dataflow_crud.create(
                "OnboardingStep",
                {
                    "module_id": benefits_module_id,
                    "title": benefit_name[:MAX_NAME_LENGTH],
                    "description": "",
                    "sort_order": order,
                    "step_type": "content",
                    "body_content": body[:MAX_BODY_CONTENT_LENGTH],
                    "checklist_items": "",
                    "media_url": "",
                    "requires_completion": True,
                    "policy_id": None,
                    "requires_previous_completion": False,
                },
            )
            steps_created += 1

    # ------------------------------------------------------------------
    # Sheet 9 — Probation: create checklist steps for 30/60/90 goals
    # ------------------------------------------------------------------
    probation_config = parsed.get("probation_config", {})
    if probation_config:
        goal_fields = [
            ("goal_30_day", "30-Day Goals"),
            ("goal_60_day", "60-Day Goals"),
            ("goal_90_day", "90-Day Goals"),
        ]
        goal_steps_to_create = []
        for field_key, step_title in goal_fields:
            goal_text = probation_config.get(field_key, "")
            if goal_text:
                goal_steps_to_create.append((step_title, goal_text))

        if goal_steps_to_create:
            # Find or create a probation module
            probation_module_id = None
            all_modules = _get_modules_for_template(template_id)
            for m in all_modules:
                if m.get("phase") == "probation":
                    probation_module_id = m.get("id")
                    break
            if probation_module_id is None:
                new_probation = dataflow_crud.create(
                    "OnboardingModule",
                    {
                        "template_id": template_id,
                        "company_id": company_id,
                        "name": "Probation & Goals",
                        "description": "Probation milestones and goal tracking",
                        "phase": "probation",
                        "sort_order": modules_created,
                        "estimated_duration_minutes": 0,
                        "is_mandatory": True,
                        "is_role_specific": False,
                        "role_filter": "",
                    },
                )
                probation_module_id = new_probation.get("id")
                module_id_map["Probation & Goals"] = probation_module_id
                modules_created += 1

            for step_title, goal_text in goal_steps_to_create:
                # Split goal text into checklist items (by newline or semicolon)
                items = re.split(r"[;\n]+", goal_text)
                checklist_str = "\n".join(item.strip() for item in items if item.strip())

                order = step_order_by_module.get(probation_module_id, 0)
                step_order_by_module[probation_module_id] = order + 1
                dataflow_crud.create(
                    "OnboardingStep",
                    {
                        "module_id": probation_module_id,
                        "title": step_title[:MAX_NAME_LENGTH],
                        "description": "",
                        "sort_order": order,
                        "step_type": "checklist",
                        "body_content": "",
                        "checklist_items": checklist_str[:MAX_CHECKLIST_LENGTH],
                        "media_url": "",
                        "requires_completion": True,
                        "policy_id": None,
                        "requires_previous_completion": False,
                    },
                )
                steps_created += 1

    # ------------------------------------------------------------------
    # Sheet 10 — Communications: content step in Orientation module
    # ------------------------------------------------------------------
    communications = parsed.get("communications", [])
    if communications:
        # Find the Orientation module (or first module)
        orientation_module_id = None
        all_modules = _get_modules_for_template(template_id)
        for m in all_modules:
            if m.get("phase") == "orientation":
                orientation_module_id = m.get("id")
                break
        if orientation_module_id is None and module_id_map:
            orientation_module_id = next(iter(module_id_map.values()))

        if orientation_module_id is not None:
            comms_lines = ["## Communication Channels & Meeting Cadences\n"]
            for comm in communications:
                channel = comm.get("channel", "Unknown")
                comm_type = comm.get("type", "")
                purpose = comm.get("purpose", "")
                frequency = comm.get("frequency", "")
                platform = comm.get("platform", "")
                line = f"**{channel}**"
                if comm_type:
                    line += f" ({comm_type})"
                if purpose:
                    line += f"\n{purpose}"
                details = []
                if frequency:
                    details.append(f"Frequency: {frequency}")
                if platform:
                    details.append(f"Platform: {platform}")
                if comm.get("access_instructions"):
                    details.append(f"Access: {comm['access_instructions']}")
                if details:
                    line += "\n" + " | ".join(details)
                comms_lines.append(line)
            comms_body = "\n\n".join(comms_lines)

            order = step_order_by_module.get(orientation_module_id, 0)
            step_order_by_module[orientation_module_id] = order + 1
            dataflow_crud.create(
                "OnboardingStep",
                {
                    "module_id": orientation_module_id,
                    "title": "Communication Channels",
                    "description": "Company communication tools and meeting schedule",
                    "sort_order": order,
                    "step_type": "content",
                    "body_content": comms_body[:MAX_BODY_CONTENT_LENGTH],
                    "checklist_items": "",
                    "media_url": "",
                    "requires_completion": True,
                    "policy_id": None,
                    "requires_previous_completion": False,
                },
            )
            steps_created += 1

    # ------------------------------------------------------------------
    # Sheet 11 — Key Contacts: content step listing contacts
    # ------------------------------------------------------------------
    contacts = parsed.get("contacts", [])
    if contacts:
        # Find the Orientation module (or first module)
        orientation_module_id = None
        all_modules = _get_modules_for_template(template_id)
        for m in all_modules:
            if m.get("phase") == "orientation":
                orientation_module_id = m.get("id")
                break
        if orientation_module_id is None and module_id_map:
            orientation_module_id = next(iter(module_id_map.values()))

        if orientation_module_id is not None:
            contact_lines = ["## Key Contacts\n"]
            for ct in contacts:
                name = ct.get("name", "Unknown")
                role = ct.get("role", "")
                dept = ct.get("department", "")
                email = ct.get("email", "")
                line = f"**{name}**"
                if role:
                    line += f" — {role}"
                if dept:
                    line += f" ({dept})"
                if email:
                    line += f"\nEmail: {email}"
                if ct.get("notes"):
                    line += f"\n{ct['notes']}"
                contact_lines.append(line)
            contacts_body = "\n\n".join(contact_lines)

            order = step_order_by_module.get(orientation_module_id, 0)
            step_order_by_module[orientation_module_id] = order + 1
            dataflow_crud.create(
                "OnboardingStep",
                {
                    "module_id": orientation_module_id,
                    "title": "Key Contacts",
                    "description": "Important contacts for new employees",
                    "sort_order": order,
                    "step_type": "content",
                    "body_content": contacts_body[:MAX_BODY_CONTENT_LENGTH],
                    "checklist_items": "",
                    "media_url": "",
                    "requires_completion": True,
                    "policy_id": None,
                    "requires_previous_completion": False,
                },
            )
            steps_created += 1

    # ------------------------------------------------------------------
    # Sheet 12 — Pre-boarding Checklist: create PreboardingTaskInstance
    # ------------------------------------------------------------------
    preboarding_tasks = parsed.get("preboarding_tasks", [])
    for pb_task in preboarding_tasks:
        task_name = pb_task.get("task", "")
        if not task_name:
            continue

        owner = str(pb_task.get("owner", "hr")).strip().lower()
        # Normalise owner to valid enum values
        valid_owners = {"hr", "manager", "it", "office_manager"}
        if owner not in valid_owners:
            owner = "hr"

        trigger_val = str(pb_task.get("trigger", "")).strip()

        # Parse deadline column (values like "-14", "-7", "-1" = days relative to start)
        deadline_raw = pb_task.get("deadline")
        relative_days_note = ""
        if deadline_raw is not None:
            try:
                days = int(str(deadline_raw).strip())
                relative_days_note = f"Relative deadline: {days} days from start date"
            except (ValueError, TypeError):
                relative_days_note = f"Deadline: {deadline_raw}"

        notes_parts = []
        if relative_days_note:
            notes_parts.append(relative_days_note)
        if pb_task.get("dependency"):
            notes_parts.append(f"Depends on: {pb_task['dependency']}")
        if pb_task.get("notes"):
            notes_parts.append(pb_task["notes"])

        dataflow_crud.create(
            "PreboardingTaskInstance",
            {
                "company_id": company_id,
                "template_id": template_id,
                "employee_id": 0,
                "task_name": task_name[:MAX_NAME_LENGTH],
                "owner_role": owner,
                "trigger": trigger_val[:MAX_TEXT_LENGTH] if trigger_val else "",
                "deadline_date": None,
                "status": "pending",
                "completed_at": None,
                "completed_by": None,
                "notes": " | ".join(notes_parts)[:MAX_NOTES_LENGTH] if notes_parts else "",
            },
        )
        preboarding_tasks_created += 1

    logger.info(
        "Onboarding template imported: template_id=%s, modules=%d, steps=%d, "
        "preboarding_tasks=%d, policy_steps=%d, warnings=%d, errors=%d",
        template_id,
        modules_created,
        steps_created,
        preboarding_tasks_created,
        policy_steps_created,
        len(parse_warnings),
        len(parse_errors),
    )
    return {
        "template_id": template_id,
        "modules_created": modules_created,
        "steps_created": steps_created,
        "preboarding_tasks_created": preboarding_tasks_created,
        "policy_steps_created": policy_steps_created,
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
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
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
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
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
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
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
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
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
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
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
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
    )

    logger.info("Onboarding step updated: id=%s", step_id)
    return {"step": result}


@router.delete("/steps/{step_id}")
async def delete_step(
    step_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Soft-delete a step (S3-T5).

    A hard delete would orphan every `OnboardingStepProgress` row for
    in-progress assignments — employees would see blanks and percentages
    would skew. Soft-delete sets `is_active=False`: existing assignments
    keep their progress, and the step is hidden from any new assignment.

    Admins can still see and re-activate the step via the list endpoints
    (which filter is_active=True for employee views but include archived
    rows for admin views).
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    step = dataflow_crud.read("OnboardingStep", step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Onboarding step not found.")

    # Verify parent module belongs to this company
    module = _verify_module_ownership(step.get("module_id"), company_id)

    # S3-T5: idempotent soft-delete
    if step.get("is_active") is False:
        return {"message": "Step is already archived.", "step_id": step_id}

    dataflow_crud.update("OnboardingStep", step_id, {"is_active": False})

    # Bump template updated_at
    dataflow_crud.update(
        "OnboardingTemplate",
        module.get("template_id"),
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
    )

    logger.info("Onboarding step soft-deleted: id=%s", step_id)
    return {"message": "Step archived.", "step_id": step_id}


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
    buddy_employee_id = body.get("buddy_employee_id")

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

    # Verify buddy if provided
    if buddy_employee_id:
        buddy_employee_id = int(buddy_employee_id)
        if buddy_employee_id == employee_id:
            raise HTTPException(
                status_code=400,
                detail="Buddy cannot be the same as the assigned employee.",
            )
        buddy = dataflow_crud.read("Employee", buddy_employee_id)
        if not buddy or buddy.get("company_id") != company_id:
            raise HTTPException(status_code=404, detail="Buddy employee not found in this company.")
        if not buddy.get("is_active", True):
            raise HTTPException(status_code=400, detail="Buddy employee is not active.")

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
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

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
            "buddy_employee_id": buddy_employee_id or None,
        },
    )
    assignment_id = assignment.get("id")

    # Create step progress records for role-filtered steps in the template
    all_steps = _get_all_steps_for_template(template_id, employee=employee)
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

    # Copy template-level pre-boarding tasks to per-employee instances
    preboarding_created = 0
    try:
        template_tasks = dataflow_crud.list_records(
            "PreboardingTaskInstance",
            {"template_id": template_id, "employee_id": 0},
        )
        start_date = employee.get("start_date", "")
        for task in template_tasks:
            task_data = {
                "company_id": company_id,
                "template_id": template_id,
                "employee_id": employee_id,
                "task_name": task.get("task_name", ""),
                "owner_role": task.get("owner_role", "hr"),
                "trigger": task.get("trigger", ""),
                "status": "pending",
                "notes": task.get("notes", ""),
            }
            # Calculate deadline from start_date if we have relative days in notes
            if start_date and task.get("notes", ""):
                try:
                    import re as _re
                    days_match = _re.search(r"(-?\d+)\s*days?\s*(?:before|relative)", task.get("notes", ""))
                    if days_match:
                        from datetime import timedelta
                        rel_days = int(days_match.group(1))
                        sd = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
                        task_data["deadline_date"] = (sd + timedelta(days=rel_days)).isoformat()
                except (ValueError, TypeError):
                    pass
            dataflow_crud.create("PreboardingTaskInstance", task_data)
            preboarding_created += 1
    except Exception as exc:
        logger.warning("Failed to create pre-boarding tasks: %s", exc)

    # Auto-create 30/60/90-day review milestones
    milestones_created = 0
    try:
        start_date = employee.get("start_date", "")
        if start_date:
            base_date = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
        else:
            base_date = datetime.fromisoformat(now) if isinstance(now, str) else now
        for mtype, days in [("day_30", 30), ("day_60", 60), ("day_90", 90)]:
            scheduled = (base_date + timedelta(days=days)).isoformat()
            dataflow_crud.create(
                "OnboardingMilestone",
                {
                    "assignment_id": assignment_id,
                    "company_id": company_id,
                    "employee_id": employee_id,
                    "milestone_type": mtype,
                    "scheduled_date": scheduled,
                    "status": "pending",
                    "completed_at": None,
                    "notes": "",
                    "reviewed_by": None,
                },
            )
            milestones_created += 1
    except Exception as exc:
        logger.warning("Failed to create onboarding milestones: %s", exc)

    logger.info(
        "Onboarding assigned: assignment_id=%s, employee_id=%s, template_id=%s, steps=%d, preboarding=%d, milestones=%d",
        assignment_id,
        employee_id,
        template_id,
        len(all_steps),
        preboarding_created,
        milestones_created,
    )
    return {
        "assignment": assignment,
        "steps_created": len(all_steps),
        "milestones_created": milestones_created,
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
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

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

        # Role-filter steps per employee (different employees may have
        # different designations/departments)
        emp_steps = _get_all_steps_for_template(template_id, employee=employee)
        for step in emp_steps:
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


@router.get("/assignments/export")
async def export_assignments_csv(
    status: str = Query(None, description="Filter by status: in_progress, completed, overdue"),
    department: str = Query(None, description="Filter by employee department"),
    template_id: int = Query(None, description="Filter by template ID"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> Response:
    """Export onboarding assignments as a downloadable CSV file.

    Returns a CSV with columns: Employee Name, Department, Template,
    Assigned Date, Due Date, Status, Completion %, Days Since Start.
    Supports optional filtering by status, department, and template.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Build base filters
    filters: dict = {"company_id": company_id}
    if status:
        valid_statuses = {"in_progress", "completed", "overdue", "cancelled"}
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status filter. Must be one of: {', '.join(sorted(valid_statuses))}.",
            )
        filters["status"] = status
    if template_id:
        filters["template_id"] = template_id

    assignments = dataflow_crud.list_records("OnboardingAssignment", filters)

    # Enrich each assignment (adds employee_name, department, template_name, etc.)
    enriched = [_enrich_assignment(a) for a in assignments]

    # Apply department filter (post-enrichment since department comes from Employee)
    if department:
        dept_lower = department.lower()
        enriched = [
            a for a in enriched
            if (a.get("department", "") or "").lower() == dept_lower
        ]

    # CSV injection prevention
    def _safe_csv(value: str) -> str:
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Employee Name",
        "Department",
        "Template",
        "Assigned Date",
        "Due Date",
        "Status",
        "Completion %",
        "Days Since Start",
    ])

    now = datetime.now(timezone.utc)
    for a in enriched:
        # Calculate days since start
        days_since_start = ""
        assigned_at = a.get("assigned_at")
        if assigned_at:
            try:
                assigned_dt = datetime.fromisoformat(assigned_at)
                if assigned_dt.tzinfo is None:
                    assigned_dt = assigned_dt.replace(tzinfo=timezone.utc)
                days_since_start = str((now - assigned_dt).days)
            except (ValueError, TypeError):
                pass

        writer.writerow([
            _safe_csv(a.get("employee_name", "")),
            _safe_csv(a.get("department", "")),
            _safe_csv(a.get("template_name", "")),
            a.get("assigned_at", "")[:10] if a.get("assigned_at") else "",
            a.get("due_date", "")[:10] if a.get("due_date") else "",
            a.get("status", ""),
            f"{a.get('completion_percentage', 0):.1f}",
            days_since_start,
        ])

    csv_content = output.getvalue()
    today_str = now.strftime("%Y-%m-%d")
    filename = _sanitize_csv_filename(f"onboarding-assignments-{today_str}", ".csv")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
        cache_ttl=0,
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

    # Fetch step progress with step details (bypass cache for fresh status)
    progress_records = dataflow_crud.list_records(
        "OnboardingStepProgress",
        {"assignment_id": assignment["id"]},
        cache_ttl=0,
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
                    cache_ttl=0,
                )
                if prev_progress and prev_progress[0].get("status") != "completed":
                    raise HTTPException(
                        status_code=400,
                        detail="Previous required steps must be completed first.",
                    )

    # Optional notes from body. We accept JSON or no-body POSTs; only
    # JSONDecodeError / a missing-body Exception class should be swallowed
    # silently. Any other exception (network blow-up, decoder corruption)
    # surfaces in logs so we can debug.
    body = {}
    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError):
        # No body or malformed JSON — treat as empty and proceed.
        pass
    except Exception as exc:  # noqa: BLE001
        logger.debug("complete_step body parse non-JSON failure: %s", exc)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
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
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
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

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

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
            # Extract client IP for audit. AttributeError covers the case
            # where the test client doesn't expose .client.host; anything
            # broader is a real bug we want to see in the logs.
            ip_address = ""
            try:
                client = request.client
                if client:
                    ip_address = client.host or ""
            except AttributeError as exc:
                logger.debug("policy ack ip-extraction missing attr: %s", exc)

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

    # Optional notes from body. Same narrow-catch pattern as complete_step.
    body = {}
    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError):
        pass
    except Exception as exc:  # noqa: BLE001
        logger.debug("admin-complete-step body parse non-JSON failure: %s", exc)

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
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
        updates["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        updates["completed_by"] = actor_id

    if "notes" in body:
        _validate_text_length(body["notes"], "notes")
        updates["notes"] = body["notes"]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = dataflow_crud.update("PreboardingTaskInstance", task_id, updates)
    logger.info("Pre-boarding task updated: id=%s, status=%s", task_id, result.get("status"))
    return {"task": result}


# ==========================================================================
# IT PROVISIONING (admin) — filtered view of PreboardingTaskInstance
# ==========================================================================

_VALID_IT_STATUSES = {"pending", "in_progress", "completed"}


@router.get("/it-provisioning/{employee_id}")
async def list_it_provisioning(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List IT provisioning tasks for an employee.

    Filters PreboardingTaskInstance records where owner_role='it'.
    Adds overdue detection for tasks with a deadline.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Verify employee belongs to company
    employee = dataflow_crud.read("Employee", employee_id)
    if not employee or employee.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found in this company.")

    all_tasks = dataflow_crud.list_records(
        "PreboardingTaskInstance",
        {"employee_id": employee_id, "company_id": company_id},
    )

    # Filter to IT-owned tasks only
    it_tasks = [t for t in all_tasks if t.get("owner_role") == "it"]

    # Overdue detection
    now = datetime.now(timezone.utc)
    for task in it_tasks:
        if task.get("status") in ("pending", "in_progress") and task.get("deadline_date"):
            try:
                deadline = datetime.fromisoformat(task["deadline_date"])
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                task["is_overdue"] = now > deadline
            except (ValueError, TypeError):
                task["is_overdue"] = False
        else:
            task["is_overdue"] = False

    # Extract category from notes (stored as "Category: <value> | ...")
    for task in it_tasks:
        notes = task.get("notes", "")
        category = ""
        for part in notes.split(" | "):
            if part.startswith("Category: "):
                category = part[len("Category: "):]
                break
        task["category"] = category

    pending = [t for t in it_tasks if t.get("status") == "pending"]
    in_progress = [t for t in it_tasks if t.get("status") == "in_progress"]
    completed = [t for t in it_tasks if t.get("status") in ("completed", "done")]

    return {
        "tasks": it_tasks,
        "total": len(it_tasks),
        "pending": len(pending),
        "in_progress": len(in_progress),
        "completed": len(completed),
    }


@router.patch("/it-provisioning/{task_id}")
async def update_it_provisioning(
    task_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an IT provisioning task status and optional notes.

    Valid status transitions: pending -> in_progress -> completed.
    Accepts optional 'notes' field.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    task = dataflow_crud.read("PreboardingTaskInstance", task_id)
    if not task or task.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="IT provisioning task not found.")

    if task.get("owner_role") != "it":
        raise HTTPException(status_code=400, detail="This task is not an IT provisioning task.")

    body = await request.json()
    updates: dict = {}

    new_status = body.get("status")
    if new_status:
        if new_status not in _VALID_IT_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(sorted(_VALID_IT_STATUSES))}.",
            )
        current_status = task.get("status", "pending")
        # Allow transitions: pending->in_progress, in_progress->completed, pending->completed
        valid_transitions = {
            "pending": {"in_progress", "completed"},
            "in_progress": {"completed"},
            "completed": set(),
            "done": set(),  # legacy status — no further transitions
        }
        allowed = valid_transitions.get(current_status, set())
        if new_status != current_status and new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{current_status}' to '{new_status}'.",
            )
        if new_status != current_status:
            updates["status"] = new_status
            if new_status == "completed":
                actor_id = int(current_user.get("sub", 0))
                updates["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
                updates["completed_by"] = actor_id

    if "notes" in body:
        _validate_text_length(body["notes"], "notes")
        updates["notes"] = body["notes"]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = dataflow_crud.update("PreboardingTaskInstance", task_id, updates)
    logger.info("IT provisioning task updated: id=%s, status=%s", task_id, result.get("status"))
    return {"task": result}


# ==========================================================================
# MILESTONES (30/60/90-day reviews)
# ==========================================================================


@router.get("/milestones/{assignment_id}")
async def list_milestones(
    assignment_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List 30/60/90-day review milestones for an onboarding assignment."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Verify assignment belongs to company
    assignment = dataflow_crud.read("OnboardingAssignment", assignment_id)
    if not assignment or assignment.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    milestones = dataflow_crud.list_records(
        "OnboardingMilestone",
        {"assignment_id": assignment_id, "company_id": company_id},
    )

    # Sort by milestone_type order: day_30, day_60, day_90
    type_order = {"day_30": 0, "day_60": 1, "day_90": 2}
    milestones.sort(key=lambda m: type_order.get(m.get("milestone_type", ""), 99))

    return {"milestones": milestones, "count": len(milestones)}


@router.patch("/milestones/{milestone_id}")
async def update_milestone(
    milestone_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Mark a milestone as completed, add notes, or set reviewed_by."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    milestone = dataflow_crud.read("OnboardingMilestone", milestone_id)
    if not milestone or milestone.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Milestone not found.")

    body = await request.json()
    updates: dict = {}
    actor_id = int(current_user.get("sub", 0))

    if body.get("status") == "completed" and milestone.get("status") != "completed":
        updates["status"] = "completed"
        updates["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        updates["reviewed_by"] = actor_id

    if "notes" in body:
        _validate_text_length(body["notes"], "notes", MAX_NOTES_LENGTH)
        updates["notes"] = body["notes"]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    result = dataflow_crud.update("OnboardingMilestone", milestone_id, updates)
    logger.info(
        "Onboarding milestone updated: id=%s, type=%s, status=%s",
        milestone_id,
        result.get("milestone_type"),
        result.get("status"),
    )
    return {"milestone": result}


@router.get("/my-milestones")
async def get_my_milestones(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get milestones for the current employee's active onboarding assignment."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if not employee:
        return {"milestones": [], "message": "No employee record found."}

    employee_id = employee.get("id")

    # Find active assignment
    assignments = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"employee_id": employee_id, "company_id": company_id},
    )
    active = [a for a in assignments if a.get("status") in ("in_progress", "overdue")]
    if not active:
        return {"milestones": [], "message": "No active onboarding."}

    active.sort(key=lambda a: a.get("assigned_at", ""), reverse=True)
    assignment = active[0]

    milestones = dataflow_crud.list_records(
        "OnboardingMilestone",
        {"assignment_id": assignment["id"], "company_id": company_id},
    )

    type_order = {"day_30": 0, "day_60": 1, "day_90": 2}
    milestones.sort(key=lambda m: type_order.get(m.get("milestone_type", ""), 99))

    return {"milestones": milestones, "count": len(milestones)}


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------


@router.get("/analytics")
async def get_onboarding_analytics(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Aggregate onboarding analytics for the company.

    Returns completion rates, average completion time, status counts,
    breakdowns by department and module, and average survey scores.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # ------------------------------------------------------------------
    # 1. Fetch all assignments for the company
    # ------------------------------------------------------------------
    assignments = dataflow_crud.list_records(
        "OnboardingAssignment", {"company_id": company_id}
    )

    # Refresh overdue status for in-progress assignments
    now_dt = datetime.now(timezone.utc)
    for a in assignments:
        if a.get("status") == "in_progress" and a.get("due_date"):
            try:
                due_date = datetime.fromisoformat(a["due_date"])
                if due_date.tzinfo is not None:
                    due_date = due_date.replace(tzinfo=None)
                if now_dt > due_date:
                    a["status"] = "overdue"
                    dataflow_crud.update(
                        "OnboardingAssignment", a["id"], {"status": "overdue"}
                    )
            except (ValueError, TypeError):
                pass

    total_assignments = len(assignments)
    completed_count = sum(1 for a in assignments if a.get("status") == "completed")
    in_progress_count = sum(1 for a in assignments if a.get("status") == "in_progress")
    overdue_count = sum(1 for a in assignments if a.get("status") == "overdue")
    completion_rate = round((completed_count / total_assignments) * 100, 1) if total_assignments > 0 else 0.0

    # ------------------------------------------------------------------
    # 2. Average completion time (days from assigned_at to completed_at)
    # ------------------------------------------------------------------
    completion_days: list[float] = []
    for a in assignments:
        if a.get("status") == "completed" and a.get("assigned_at") and a.get("completed_at"):
            try:
                assigned = datetime.fromisoformat(a["assigned_at"])
                completed = datetime.fromisoformat(a["completed_at"])
                if assigned.tzinfo is not None:
                    assigned = assigned.replace(tzinfo=None)
                if completed.tzinfo is not None:
                    completed = completed.replace(tzinfo=None)
                delta = (completed - assigned).total_seconds() / 86400
                if delta >= 0:
                    completion_days.append(round(delta, 1))
            except (ValueError, TypeError):
                pass

    avg_completion_days = round(sum(completion_days) / len(completion_days), 1) if completion_days else 0.0

    # ------------------------------------------------------------------
    # 3. By department
    # ------------------------------------------------------------------
    dept_stats: dict[str, dict] = {}
    for a in assignments:
        employee = dataflow_crud.read("Employee", a.get("employee_id"))
        dept = (employee.get("department") if employee else None) or "Unassigned"
        if dept not in dept_stats:
            dept_stats[dept] = {"total": 0, "completed": 0}
        dept_stats[dept]["total"] += 1
        if a.get("status") == "completed":
            dept_stats[dept]["completed"] += 1

    by_department = sorted(
        [
            {
                "department": dept,
                "total": stats["total"],
                "completed": stats["completed"],
                "rate": round((stats["completed"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0.0,
            }
            for dept, stats in dept_stats.items()
        ],
        key=lambda d: d["department"],
    )

    # ------------------------------------------------------------------
    # 4. By module — steps completed across all assignments
    # ------------------------------------------------------------------
    # Gather all template IDs in use
    template_ids = {a.get("template_id") for a in assignments if a.get("template_id")}
    module_stats: dict[str, dict] = {}
    for tid in template_ids:
        modules = _get_modules_for_template(tid)
        for mod in modules:
            mod_name = mod.get("name", f"Module {mod.get('id')}")
            mod_id = mod.get("id")
            steps = _get_steps_for_module(mod_id)
            step_ids = {s.get("id") for s in steps}
            if not step_ids:
                continue

            # Count step progress across all assignments for this template
            for a in assignments:
                if a.get("template_id") != tid:
                    continue
                progress_records = dataflow_crud.list_records(
                    "OnboardingStepProgress",
                    {"assignment_id": a.get("id")},
                    cache_ttl=0,
                )
                for pr in progress_records:
                    if pr.get("step_id") in step_ids:
                        if mod_name not in module_stats:
                            module_stats[mod_name] = {"total_steps": 0, "completed_steps": 0}
                        module_stats[mod_name]["total_steps"] += 1
                        if pr.get("status") == "completed":
                            module_stats[mod_name]["completed_steps"] += 1

    by_module = sorted(
        [
            {
                "module_name": name,
                "total_steps": stats["total_steps"],
                "completed_steps": stats["completed_steps"],
                "rate": round((stats["completed_steps"] / stats["total_steps"]) * 100, 1) if stats["total_steps"] > 0 else 0.0,
            }
            for name, stats in module_stats.items()
        ],
        key=lambda m: m["module_name"],
    )

    # ------------------------------------------------------------------
    # 5. Pulse survey scores (if model exists)
    # ------------------------------------------------------------------
    avg_survey_score: float | None = None
    flagged_employees = 0
    try:
        surveys = dataflow_crud.list_records("PulseSurvey", {"company_id": company_id})
        if surveys:
            scores = [s.get("average_score") for s in surveys if s.get("average_score") is not None]
            avg_survey_score = round(sum(scores) / len(scores), 1) if scores else None
            flagged_employees = sum(1 for s in surveys if s.get("flagged"))
    except Exception as exc:
        logger.warning("Failed to fetch pulse survey data for analytics: %s", exc)

    logger.info(
        "Onboarding analytics: company_id=%s, total=%d, completed=%d, overdue=%d",
        company_id, total_assignments, completed_count, overdue_count,
    )

    return {
        "total_assignments": total_assignments,
        "completed": completed_count,
        "in_progress": in_progress_count,
        "overdue": overdue_count,
        "completion_rate": completion_rate,
        "avg_completion_days": avg_completion_days,
        "by_department": by_department,
        "by_module": by_module,
        "avg_survey_score": avg_survey_score,
        "flagged_employees": flagged_employees,
    }


# ==========================================================================
# PULSE SURVEYS
# ==========================================================================

PULSE_QUESTIONS = [
    (1, "I understand my role and responsibilities clearly"),
    (2, "I feel welcomed and included by my team"),
    (3, "My manager has been supportive during my onboarding"),
    (4, "I have the tools and resources I need to do my job"),
    (5, "Overall, how would you rate your onboarding experience?"),
]

VALID_SURVEY_TYPES = {"day_30", "day_60"}
FLAG_THRESHOLD = 3.5


@router.post("/surveys/trigger")
async def trigger_pulse_survey(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a pulse survey for an onboarding employee.

    Accepts: employee_id, assignment_id, survey_type (day_30 or day_60).
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    employee_id = body.get("employee_id")
    assignment_id = body.get("assignment_id")
    survey_type = body.get("survey_type", "day_30")

    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id is required.")
    if not assignment_id:
        raise HTTPException(status_code=400, detail="assignment_id is required.")
    if survey_type not in VALID_SURVEY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"survey_type must be one of: {', '.join(sorted(VALID_SURVEY_TYPES))}.",
        )

    # Verify employee belongs to this company
    employee = dataflow_crud.read("Employee", employee_id)
    if not employee or employee.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Verify assignment belongs to this company
    assignment = dataflow_crud.read("OnboardingAssignment", assignment_id)
    if not assignment or assignment.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Onboarding assignment not found.")

    # Check for duplicate — same assignment and survey_type
    existing = dataflow_crud.list_records(
        "PulseSurvey",
        {"assignment_id": assignment_id, "survey_type": survey_type},
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A {survey_type} survey already exists for this assignment.",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    survey = dataflow_crud.create(
        "PulseSurvey",
        {
            "company_id": company_id,
            "employee_id": int(employee_id),
            "assignment_id": int(assignment_id),
            "survey_type": survey_type,
            "status": "pending",
            "sent_at": now,
            "average_score": 0.0,
            "flagged": False,
        },
    )
    logger.info(
        "Pulse survey triggered: id=%s, employee_id=%s, type=%s",
        survey.get("id"),
        employee_id,
        survey_type,
    )
    return {"survey": survey}


@router.get("/surveys")
async def list_pulse_surveys(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all pulse surveys for the current company.

    Enriches each survey with the employee name.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    surveys = dataflow_crud.list_records(
        "PulseSurvey",
        {"company_id": company_id},
    )

    enriched = []
    for s in surveys:
        emp = dataflow_crud.read("Employee", s.get("employee_id"))
        employee_name = ""
        if emp:
            user = dataflow_crud.read("User", emp.get("user_id"))
            employee_name = user.get("name", "") if user else ""
        s["employee_name"] = employee_name
        enriched.append(s)

    return {"surveys": enriched, "count": len(enriched)}


@router.get("/my-surveys")
async def list_my_surveys(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List pending pulse surveys for the currently logged-in employee."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if not employee:
        return {"surveys": [], "count": 0}

    employee_id = employee.get("id")
    surveys = dataflow_crud.list_records(
        "PulseSurvey",
        {"employee_id": employee_id, "status": "pending"},
    )

    # Enrich with questions
    for s in surveys:
        s["questions"] = [
            {"number": num, "text": text} for num, text in PULSE_QUESTIONS
        ]

    return {"surveys": surveys, "count": len(surveys)}


@router.post("/surveys/{survey_id}/respond")
async def respond_to_survey(
    survey_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit responses to a pulse survey.

    Accepts an array of {question_number, score, comment}.
    Calculates average score and flags if below threshold.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found.")

    # Verify survey belongs to this employee
    survey = dataflow_crud.read("PulseSurvey", survey_id)
    if not survey or survey.get("employee_id") != employee.get("id"):
        raise HTTPException(status_code=404, detail="Survey not found.")

    if survey.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Survey already completed.")

    body = await request.json()
    responses = body.get("responses", [])
    if not responses:
        raise HTTPException(status_code=400, detail="responses array is required.")
    if len(responses) > len(PULSE_QUESTIONS):
        raise HTTPException(status_code=400, detail=f"Maximum {len(PULSE_QUESTIONS)} responses allowed.")

    # Validate responses — no duplicate question numbers
    valid_numbers = {num for num, _ in PULSE_QUESTIONS}
    question_lookup = {num: text for num, text in PULSE_QUESTIONS}
    seen_questions: set[int] = set()
    total_score = 0
    created_responses = []

    for resp in responses:
        q_num = resp.get("question_number")
        score = resp.get("score")
        comment = resp.get("comment", "")

        if q_num in seen_questions:
            raise HTTPException(status_code=400, detail=f"Duplicate response for question {q_num}.")
        seen_questions.add(q_num)

        if q_num not in valid_numbers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid question_number: {q_num}. Valid: {sorted(valid_numbers)}.",
            )
        if not isinstance(score, int) or score < 1 or score > 5:
            raise HTTPException(
                status_code=400,
                detail=f"Score for question {q_num} must be an integer from 1 to 5.",
            )
        if comment:
            _validate_text_length(comment, f"comment for question {q_num}")

        total_score += score
        response_record = dataflow_crud.create(
            "PulseSurveyResponse",
            {
                "survey_id": survey_id,
                "question_number": int(q_num),
                "question_text": question_lookup.get(q_num, ""),
                "score": score,
                "comment": comment,
            },
        )
        created_responses.append(response_record)

    # Calculate average and flag
    avg_score = round(total_score / len(responses), 2) if responses else 0.0
    flagged = avg_score < FLAG_THRESHOLD
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    dataflow_crud.update(
        "PulseSurvey",
        survey_id,
        {
            "status": "completed",
            "completed_at": now,
            "average_score": avg_score,
            "flagged": flagged,
        },
    )

    logger.info(
        "Pulse survey completed: id=%s, avg=%.2f, flagged=%s",
        survey_id,
        avg_score,
        flagged,
    )

    return {
        "message": "Thank you for your feedback!",
        "survey_id": survey_id,
        "average_score": avg_score,
        "flagged": flagged,
        "responses": created_responses,
    }


@router.get("/surveys/{survey_id}/results")
async def get_survey_results(
    survey_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a pulse survey with all its responses (admin view)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    survey = dataflow_crud.read("PulseSurvey", survey_id)
    if not survey or survey.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Survey not found.")

    # Enrich with employee name
    emp = dataflow_crud.read("Employee", survey.get("employee_id"))
    if emp:
        user = dataflow_crud.read("User", emp.get("user_id"))
        survey["employee_name"] = user.get("name", "") if user else ""
    else:
        survey["employee_name"] = ""

    # Fetch all responses
    responses = dataflow_crud.list_records(
        "PulseSurveyResponse",
        {"survey_id": survey_id},
    )
    responses.sort(key=lambda r: r.get("question_number", 0))

    return {"survey": survey, "responses": responses}


# ==========================================================================
# T207: Email reminders for overdue onboarding steps
# ==========================================================================
#
# A small periodic-friendly endpoint that scans OnboardingStepProgress rows
# where status="pending" and the parent OnboardingAssignment.due_date is in
# the past, and sends each affected employee a reminder email via Resend.
#
# Heavily rate-limited (5 calls / hour / company) so a misbehaving cron or
# manual click cannot spam employees. Idempotency is best-effort: a future
# enhancement could persist last_reminded_at on the progress row so the
# same step isn't reminded more than once per N hours.
#
# Owner/hr_manager only.


def _build_overdue_reminder_email(
    employee_name: str,
    template_name: str,
    overdue_steps: list[dict],
    due_date: str | None,
    company_name: str,
) -> str:
    """Render a simple HTML reminder body for overdue onboarding steps.

    S3-T8c: use html.escape() (covers `<`, `>`, `&`, `"`, `'`) instead of
    manual `<>`-only replace which left ampersand+quote injection vectors
    open. The reminder body is rendered into a Resend HTML email.
    """
    safe_employee = html.escape(employee_name or "there", quote=True)
    safe_template = html.escape(template_name or "your onboarding", quote=True)
    safe_company = html.escape(company_name or "your company", quote=True)

    items_html = "".join(
        f"<li>{html.escape(s.get('title') or 'Untitled step', quote=True)}</li>"
        for s in overdue_steps
    )
    due_line = ""
    if due_date:
        due_line = (
            f"<p style='margin:0 0 12px 0;color:#666;'>"
            f"Your assignment was due on <strong>{due_date}</strong>.</p>"
        )

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:560px;margin:0 auto;padding:24px;color:#222;">
      <h2 style="margin:0 0 16px 0;color:#1a1a1a;">Reminder: outstanding onboarding tasks</h2>
      <p style="margin:0 0 12px 0;">Hi {safe_employee},</p>
      <p style="margin:0 0 12px 0;">
        You still have outstanding tasks in <strong>{safe_template}</strong> at {safe_company}.
        Please complete them as soon as possible.
      </p>
      {due_line}
      <ul style="margin:0 0 16px 18px;padding:0;color:#333;">
        {items_html}
      </ul>
      <p style="margin:0 0 12px 0;">
        Open the My Onboarding page in the platform to continue.
      </p>
      <p style="margin:24px 0 0 0;color:#999;font-size:12px;">
        If you've already completed these tasks, you can ignore this email.
      </p>
    </div>
    """


async def _send_overdue_reminders_for_company(company_id: int) -> dict:
    """Scan + send overdue onboarding reminders for a single company.

    Returns a summary dict with counts of assignments scanned, employees
    notified, emails sent, and a list of skipped reasons (no email,
    template missing, etc.).
    """
    summary = {
        "assignments_scanned": 0,
        "overdue_assignments": 0,
        "employees_notified": 0,
        "emails_sent": 0,
        "skipped": 0,
        "errors": 0,
    }

    if not os.environ.get("RESEND_API_KEY"):
        logger.info(
            "Onboarding reminders: RESEND_API_KEY not configured — skipping for company_id=%s",
            company_id,
        )
        summary["skipped"] = -1  # sentinel: email transport unavailable
        return summary

    # Lazy imports — adapter only loaded when this endpoint is hit
    try:
        from hr_advisory.mcp_servers.adapters.resend_email import ResendAdapter
    except Exception as exc:  # pragma: no cover - optional dependency path
        logger.warning("Onboarding reminders: ResendAdapter unavailable: %s", exc)
        summary["errors"] = 1
        return summary

    adapter = ResendAdapter()

    # Lookup company for personalisation
    company = dataflow_crud.read("Company", company_id) or {}
    company_name = company.get("name", "your company")

    assignments = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"company_id": company_id},
        cache_ttl=0,
    )
    summary["assignments_scanned"] = len(assignments)

    now_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    for assignment in assignments:
        if assignment.get("status") in ("completed", "cancelled"):
            continue

        due_str = assignment.get("due_date")
        if not due_str:
            continue

        try:
            due_dt = datetime.fromisoformat(due_str)
            if due_dt.tzinfo:
                due_dt = due_dt.replace(tzinfo=None)
        except (ValueError, TypeError):
            continue

        if now_dt <= due_dt:
            continue  # not overdue yet

        # S4-T4: 24-hour debounce. Skip if we already reminded this
        # employee within the last 24 hours, so the daily cron can run
        # safely without spamming employees.
        last_reminder_str = assignment.get("last_reminder_sent_at")
        if last_reminder_str:
            try:
                if isinstance(last_reminder_str, datetime):
                    last_reminder_dt = last_reminder_str
                else:
                    last_reminder_dt = datetime.fromisoformat(str(last_reminder_str))
                if last_reminder_dt.tzinfo:
                    last_reminder_dt = last_reminder_dt.replace(tzinfo=None)
                if (now_dt - last_reminder_dt) < timedelta(hours=24):
                    summary["skipped"] += 1
                    continue
            except (ValueError, TypeError):
                pass  # unparseable — fall through and remind anyway

        # Find pending step-progress rows for this assignment
        progress_rows = dataflow_crud.list_records(
            "OnboardingStepProgress",
            {"assignment_id": assignment["id"], "status": "pending"},
            cache_ttl=0,
        )
        if not progress_rows:
            continue

        summary["overdue_assignments"] += 1

        # Resolve employee + user
        employee_id = assignment.get("employee_id")
        employee = dataflow_crud.read("Employee", employee_id) if employee_id else None
        if not employee:
            summary["skipped"] += 1
            continue

        user = dataflow_crud.read("User", employee.get("user_id")) if employee.get("user_id") else None
        if not user or not user.get("email"):
            summary["skipped"] += 1
            continue

        employee_email = user["email"]
        employee_name = user.get("name", "")

        # Resolve template name for friendlier copy
        template = dataflow_crud.read("OnboardingTemplate", assignment.get("template_id")) or {}
        template_name = template.get("name", "your onboarding")

        # Resolve step titles for the digest
        overdue_steps: list[dict] = []
        for row in progress_rows[:25]:  # cap at 25 to keep email small
            step = dataflow_crud.read("OnboardingStep", row.get("step_id"))
            if step:
                overdue_steps.append({"title": step.get("title", "")})

        if not overdue_steps:
            summary["skipped"] += 1
            continue

        html_body = _build_overdue_reminder_email(
            employee_name=employee_name,
            template_name=template_name,
            overdue_steps=overdue_steps,
            due_date=due_str.split("T")[0] if "T" in due_str else due_str,
            company_name=company_name,
        )

        try:
            await adapter.send_email(
                to=employee_email,
                subject=f"Reminder: complete your onboarding tasks ({template_name})",
                html_body=html_body,
                tags=[
                    {"name": "category", "value": "onboarding_reminder"},
                    {"name": "company_id", "value": str(company_id)},
                ],
            )
            summary["emails_sent"] += 1
            summary["employees_notified"] += 1
            # S4-T4: stamp the assignment so the next 24h of cron runs skip it.
            try:
                dataflow_crud.update(
                    "OnboardingAssignment",
                    assignment["id"],
                    {"last_reminder_sent_at": now_dt},
                )
            except Exception as stamp_exc:
                logger.warning(
                    "Failed to stamp last_reminder_sent_at on assignment %s: %s",
                    assignment.get("id"),
                    stamp_exc,
                )
            logger.info(
                "Onboarding reminder sent: company_id=%s, employee_id=%s, steps=%d",
                company_id,
                employee_id,
                len(overdue_steps),
            )
        except Exception as exc:
            logger.warning(
                "Onboarding reminder failed for employee_id=%s: %s", employee_id, exc
            )
            summary["errors"] += 1

    return summary


@router.post("/reminders/send-overdue")
async def send_overdue_reminders(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Send email reminders for overdue onboarding steps in this company.

    Designed for periodic invocation (manually by an admin, or via an
    external scheduler). Heavily rate-limited so cron mistakes or
    repeated clicks cannot spam employees: max 5 invocations per hour
    per company.

    Returns a summary of how many reminders were dispatched. Failures
    inside the loop are logged but do not abort the batch.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Heavy rate limit — onboarding reminders are designed to be infrequent.
    check_rate_limit(
        f"onboarding_reminders:{company_id}",
        max_requests=5,
        window_seconds=3600,
        action_name="onboarding reminder dispatch",
    )

    summary = await _send_overdue_reminders_for_company(company_id)
    return {
        "message": "Overdue onboarding reminders processed.",
        "company_id": company_id,
        "summary": summary,
    }
