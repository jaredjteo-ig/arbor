"""Employee management endpoints.

Handles employee invitations, listing, self-service access, salary components,
emergency contacts, employment history, and document management.
Admins (owner, hr_manager) can invite employees and view the full roster.
Employees can view their own record via /employees/me.
"""

import calendar
import csv
import io
import json
import logging
import math
import os
import uuid
from datetime import date as date_type, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import (
    get_current_company_id,
    validate_company_access,
)
from hr_advisory.security.encryption import (
    encrypt_field,
    decrypt_field,
    mask_nric,
    mask_bank_account,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory for employee documents
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.getcwd(), "uploads", "documents"))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Invitation validity period
_INVITATION_EXPIRY_DAYS = 7

# Input length limits
MAX_TEXT_LENGTH = 2000
MAX_NAME_LENGTH = 200
MAX_ADDRESS_LENGTH = 500

# CSV import row limit
MAX_IMPORT_ROWS = 500


def _validate_text_length(value: str, field_name: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    """Validate and truncate text input to maximum length."""
    if value and len(value) > max_len:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {max_len} characters.",
        )
    return value


# --------------------------------------------------------------------------
# DataFlow helpers
# --------------------------------------------------------------------------


def _create_invitation(
    company_id: int,
    inviter_id: int,
    email: str,
    role: str,
    token: str,
    expires_at: str,
) -> dict:
    """Create an Invitation record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "InvitationCreateNode",
        "create",
        {
            "company_id": company_id,
            "inviter_id": inviter_id,
            "email": email,
            "role": role,
            "token": token,
            "expires_at": expires_at,
            "is_active": True,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _find_invitation_by_token(token: str) -> dict | None:
    """Look up an invitation by its unique token."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "InvitationListNode",
        "find",
        {"filter": {"token": token}, "limit": 1, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    records = results["find"].get("records", [])
    return records[0] if records else None


def _update_invitation(invitation_id: int, updates: dict) -> dict:
    """Update an invitation record."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "InvitationUpdateNode",
        "update",
        {"filter": {"id": invitation_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _find_invitation_by_id(invitation_id: int) -> dict | None:
    """Look up an invitation by its primary key ID."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "InvitationListNode",
        "find_inv",
        {"filter": {"id": invitation_id}, "limit": 1, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    records = results["find_inv"].get("records", [])
    return records[0] if records else None


def _list_invitations_for_company(company_id: int) -> list:
    """List all invitations for a company."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "InvitationListNode",
        "list_inv",
        {
            "filter": {"company_id": company_id},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list_inv"].get("records", [])


def _compute_invitation_status(invitation: dict) -> str:
    """Derive the display status of an invitation.

    Priority order:
    1. accepted — accepted_at is set (terminal state)
    2. revoked — is_active is False (explicit admin action)
    3. expired — expires_at is in the past
    4. pending — active, not expired, not accepted
    """
    if invitation.get("accepted_at"):
        return "accepted"
    if not invitation.get("is_active"):
        return "revoked"

    expires_at_str = invitation.get("expires_at", "")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                return "expired"
        except ValueError:
            return "expired"

    return "pending"


def _list_employees_for_company(company_id: int) -> list:
    """List all employees for a company."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeListNode",
        "list",
        {
            "filter": {"company_id": company_id},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list"].get("records", [])


def _find_employee_by_user_id(user_id: int, company_id: int) -> dict | None:
    """Find an employee record by user_id and company_id."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeListNode",
        "find",
        {
            "filter": {"user_id": user_id, "company_id": company_id},
            "limit": 1,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    records = results["find"].get("records", [])
    return records[0] if records else None


def _find_user_by_id(user_id: int) -> dict | None:
    """Look up a user by ID."""
    return dataflow_crud.read("User", user_id)


def _bulk_find_users(user_ids: list[int]) -> dict[int, dict]:
    """Bulk-fetch users by IDs. Returns {user_id: user_dict}."""
    if not user_ids:
        return {}
    all_users = dataflow_crud.list_records("User", {}, limit=10000)
    id_set = set(user_ids)
    return {u["id"]: u for u in all_users if u.get("id") in id_set}


def _serialize_employee_summary(emp: dict, user: dict | None = None) -> dict:
    """Lightweight serializer for list view — no decryption, no sensitive fields."""
    return {
        "id": emp.get("id"),
        "user_id": emp.get("user_id"),
        "company_id": emp.get("company_id"),
        "email": user.get("email", "") if user else "",
        "name": user.get("name", "") if user else "",
        "employee_id_internal": emp.get("employee_id_internal", ""),
        "department": emp.get("department", ""),
        "designation": emp.get("designation", ""),
        "employment_type": emp.get("employment_type", ""),
        "start_date": emp.get("start_date", ""),
        "end_date": emp.get("end_date", ""),
        "is_active": emp.get("is_active", True),
        "confirmation_status": emp.get("confirmation_status", "on_probation"),
        "nationality": emp.get("nationality", ""),
        "pass_type": emp.get("pass_type", ""),
        "photo_url": emp.get("photo_url", ""),
        "phone": emp.get("phone", ""),
    }


def _list_policies_for_company(company_id: int) -> list:
    """List all active policies for a company."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "CompanyPolicyListNode",
        "list",
        {
            "filter": {"company_id": company_id, "is_active": True},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    raw = results["list"]
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    if isinstance(raw, list):
        return raw
    return []


def _get_leave_balances(employee_id: int, company_id: int) -> list:
    """Get leave balances for an employee in the current year."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    current_year = datetime.now(timezone.utc).year
    wf = WorkflowBuilder()
    wf.add_node(
        "LeaveBalanceListNode",
        "list",
        {
            "filter": {
                "employee_id": employee_id,
                "company_id": company_id,
                "year": current_year,
            },
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    raw = results["list"]
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    if isinstance(raw, list):
        return raw
    return []


def _update_employee(employee_id: int, updates: dict) -> dict:
    """Update an employee record."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeUpdateNode",
        "update",
        {"filter": {"id": employee_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _find_employee_by_id(employee_id: int) -> dict | None:
    """Find an employee by ID."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeReadNode", "read", {"id": employee_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Salary Component helpers ---


def _list_salary_components(employee_id: int) -> list:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "SalaryComponentListNode",
        "list",
        {
            "filter": {"employee_id": employee_id, "is_active": True},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list"].get("records", [])


def _create_salary_component(data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("SalaryComponentCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_salary_component(component_id: int, updates: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "SalaryComponentUpdateNode",
        "update",
        {"filter": {"id": component_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_salary_component(component_id: int) -> dict | None:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("SalaryComponentReadNode", "read", {"id": component_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Emergency Contact helpers ---


def _list_emergency_contacts(employee_id: int) -> list:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmergencyContactListNode",
        "list",
        {
            "filter": {"employee_id": employee_id},
            "limit": 10,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list"].get("records", [])


def _create_emergency_contact(data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmergencyContactCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_emergency_contact(contact_id: int, updates: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmergencyContactUpdateNode",
        "update",
        {"filter": {"id": contact_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_emergency_contact(contact_id: int) -> dict | None:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmergencyContactReadNode", "read", {"id": contact_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Employment Event helpers ---


def _list_employment_events(employee_id: int) -> list:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmploymentEventListNode",
        "list",
        {
            "filter": {"employee_id": employee_id},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list"].get("records", [])


def _create_employment_event(data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmploymentEventCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


# --- Employee Document helpers ---


def _list_employee_documents(employee_id: int) -> list:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeDocumentListNode",
        "list",
        {
            "filter": {"employee_id": employee_id, "is_active": True},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list"].get("records", [])


def _create_employee_document(data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeDocumentCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_employee_document(doc_id: int, updates: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeDocumentUpdateNode",
        "update",
        {"filter": {"id": doc_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_employee_document(doc_id: int) -> dict | None:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeDocumentReadNode", "read", {"id": doc_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Employee Create helper ---


def _create_employee(data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


# --- PDPA Access Log helpers ---


def _create_pdpa_log(data: dict) -> dict:
    """Create a PdpaAccessLog record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("PdpaAccessLogCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _list_pdpa_logs(filter_dict: dict) -> list:
    """List PdpaAccessLog records matching the given filter."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "PdpaAccessLogListNode",
        "list",
        {"filter": filter_dict, "limit": 10000, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list"].get("records", [])


def _log_pdpa_access(
    accessed_by: int,
    company_id: int,
    data_subject_id: int,
    categories: list[str],
    action: str,
    ip_address: str = "",
) -> None:
    """Log PDPA access for one or more data categories.

    Creates a separate audit log entry for each category accessed.
    Failures are logged but never block the API response.
    """
    for category in categories:
        try:
            _create_pdpa_log(
                {
                    "accessed_by": accessed_by,
                    "company_id": company_id,
                    "data_subject_id": data_subject_id,
                    "data_category": category,
                    "action": action,
                    "ip_address": ip_address,
                }
            )
        except Exception:
            logger.exception(
                "Failed to write PDPA audit log: subject=%s category=%s action=%s",
                data_subject_id,
                category,
                action,
            )


# --- Employee Event helpers ---


def _create_employee_event(data: dict) -> dict:
    """Create an EmployeeEvent timeline record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeEventCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _list_employee_events(employee_id: int) -> list:
    """List EmployeeEvent records for an employee."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeEventListNode",
        "list",
        {
            "filter": {"employee_id": employee_id},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list"].get("records", [])


# --- Family Member helpers ---


def _list_family_members(employee_id: int) -> list:
    """List family members for an employee."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "FamilyMemberListNode",
        "list_fm",
        {"filter": {"employee_id": employee_id}, "limit": 10000, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list_fm"].get("records", [])


def _create_family_member(data: dict) -> dict:
    """Create a FamilyMember record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("FamilyMemberCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_family_member(member_id: int, updates: dict) -> dict:
    """Update a FamilyMember record."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "FamilyMemberUpdateNode",
        "update",
        {"filter": {"id": member_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_family_member(member_id: int) -> dict | None:
    """Read a FamilyMember by ID."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("FamilyMemberReadNode", "read", {"id": member_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Employee Note helpers ---


def _list_employee_notes(employee_id: int) -> list:
    """List notes for an employee."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeNoteListNode",
        "list_notes",
        {"filter": {"employee_id": employee_id}, "limit": 10000, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list_notes"].get("records", [])


def _create_employee_note(data: dict) -> dict:
    """Create an EmployeeNote record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeNoteCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_employee_note(note_id: int, updates: dict) -> dict:
    """Update an EmployeeNote record."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeNoteUpdateNode",
        "update",
        {"filter": {"id": note_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_employee_note(note_id: int) -> dict | None:
    """Read an EmployeeNote by ID."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeNoteReadNode", "read", {"id": note_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Employee Skill helpers ---


def _list_employee_skills(employee_id: int) -> list:
    """List skills/certifications for an employee."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeSkillListNode",
        "list_skills",
        {"filter": {"employee_id": employee_id}, "limit": 10000, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list_skills"].get("records", [])


def _create_employee_skill(data: dict) -> dict:
    """Create an EmployeeSkill record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeSkillCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_employee_skill(skill_id: int, updates: dict) -> dict:
    """Update an EmployeeSkill record."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeSkillUpdateNode",
        "update",
        {"filter": {"id": skill_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_employee_skill(skill_id: int) -> dict | None:
    """Read an EmployeeSkill by ID."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("EmployeeSkillReadNode", "read", {"id": skill_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Custom Field Definition helpers ---


def _list_custom_field_definitions(company_id: int, applies_to: str = "") -> list:
    """List custom field definitions for a company."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    filter_dict: dict = {"company_id": company_id}
    if applies_to:
        filter_dict["applies_to"] = applies_to

    wf = WorkflowBuilder()
    wf.add_node(
        "CustomFieldDefinitionListNode",
        "list_defs",
        {"filter": filter_dict, "limit": 10000, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list_defs"].get("records", [])


def _create_custom_field_definition(data: dict) -> dict:
    """Create a CustomFieldDefinition record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("CustomFieldDefinitionCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_custom_field_definition(field_id: int, updates: dict) -> dict:
    """Update a CustomFieldDefinition record."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "CustomFieldDefinitionUpdateNode",
        "update",
        {"filter": {"id": field_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_custom_field_definition(field_id: int) -> dict | None:
    """Read a CustomFieldDefinition by ID."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("CustomFieldDefinitionReadNode", "read", {"id": field_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Custom Field Value helpers ---


def _list_custom_field_values(entity_type: str, entity_id: int, company_id: int) -> list:
    """List custom field values for an entity."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "CustomFieldValueListNode",
        "list_vals",
        {
            "filter": {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "company_id": company_id,
            },
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["list_vals"].get("records", [])


def _create_custom_field_value(data: dict) -> dict:
    """Create a CustomFieldValue record via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("CustomFieldValueCreateNode", "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _update_custom_field_value(value_id: int, updates: dict) -> dict:
    """Update a CustomFieldValue record."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "CustomFieldValueUpdateNode",
        "update",
        {"filter": {"id": value_id}, "fields": updates},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _read_custom_field_value(value_id: int) -> dict | None:
    """Read a CustomFieldValue by ID."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("CustomFieldValueReadNode", "read", {"id": value_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


# --- Serialisation helpers ---


def _mask_sensitive(value: str) -> str:
    """Mask a sensitive string, showing only last 4 characters."""
    if not value or len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


def _serialize_employee(
    emp: dict, user: dict | None = None, include_sensitive: bool = False
) -> dict:
    """Serialize an employee record for API response.

    When include_sensitive=True, encrypted PII fields are decrypted before
    returning. When False, NRIC and bank account numbers are masked using
    PDPA-compliant masking (first+last4 for NRIC, last4 for bank).
    """
    if include_sensitive:
        nric_value = decrypt_field(emp.get("nric_fin", ""))
        bank_value = decrypt_field(emp.get("bank_account_number", ""))
        work_pass_value = decrypt_field(emp.get("work_pass_number", ""))
    else:
        # Decrypt first so masking operates on the real value
        raw_nric = decrypt_field(emp.get("nric_fin", ""))
        raw_bank = decrypt_field(emp.get("bank_account_number", ""))
        raw_work_pass = decrypt_field(emp.get("work_pass_number", ""))
        nric_value = mask_nric(raw_nric)
        bank_value = mask_bank_account(raw_bank)
        work_pass_value = _mask_sensitive(raw_work_pass)

    result = {
        "id": emp.get("id"),
        "user_id": emp.get("user_id"),
        "company_id": emp.get("company_id"),
        "email": user.get("email", "") if user else "",
        "name": user.get("name", "") if user else "",
        "employee_id_internal": emp.get("employee_id_internal", ""),
        "department": emp.get("department", ""),
        "designation": emp.get("designation", ""),
        "employment_type": emp.get("employment_type", ""),
        "start_date": emp.get("start_date", ""),
        "end_date": emp.get("end_date", ""),
        "nationality": emp.get("nationality", ""),
        "pass_type": emp.get("pass_type", ""),
        "salary_monthly": emp.get("salary_monthly", 0.0),
        "notice_period_days": emp.get("notice_period_days", 0),
        "is_active": emp.get("is_active", True),
        # Personal details
        "alias": emp.get("alias", ""),
        "phone": emp.get("phone", ""),
        "photo_url": emp.get("photo_url", ""),
        "date_of_birth": emp.get("date_of_birth", ""),
        "gender": emp.get("gender", ""),
        "marital_status": emp.get("marital_status", ""),
        "race": emp.get("race", ""),
        "religion": emp.get("religion", ""),
        # Identity — encrypted at rest, decrypted/masked here
        "nric_fin": nric_value,
        "nric_fin_last4": emp.get("nric_fin_last4", ""),
        # Work pass — encrypted at rest
        "work_pass_number": work_pass_value,
        "work_pass_expiry": emp.get("work_pass_expiry", ""),
        "immigration_status": emp.get("immigration_status", "citizen"),
        "immigration_effective_date": emp.get("immigration_effective_date", ""),
        # Banking — encrypted at rest, decrypted/masked here
        "bank_name": emp.get("bank_name", ""),
        "bank_account_number": bank_value,
        "bank_account_last4": emp.get("bank_account_last4", ""),
        "bank_code": emp.get("bank_code", ""),
        "branch_code": emp.get("branch_code", ""),
        # Address
        "residential_address": emp.get("residential_address", ""),
        "postal_code": emp.get("postal_code", ""),
        "address_block": emp.get("address_block", ""),
        "address_street": emp.get("address_street", ""),
        "address_unit": emp.get("address_unit", ""),
        "address_building": emp.get("address_building", ""),
        "address_postal_code": emp.get("address_postal_code", ""),
        # Organisational
        "reporting_manager_id": emp.get("reporting_manager_id"),
        # Probation
        "probation_months": emp.get("probation_months", 3),
        "probation_end_date": emp.get("probation_end_date", ""),
        "confirmation_status": emp.get("confirmation_status", "on_probation"),
        # Tax & CPF
        "iras_auto_inclusion": emp.get("iras_auto_inclusion", True),
        "tax_reference": emp.get("tax_reference", ""),
        "cpf_status": emp.get("cpf_status", "include"),
        "amcs_enabled": emp.get("amcs_enabled", False),
        "pmbs_enabled": emp.get("pmbs_enabled", False),
        "community_chest_amount": emp.get("community_chest_amount", 0.0),
        "shg_override_amount": emp.get("shg_override_amount", 0.0),
    }
    return result


def _statutory_defaults() -> list[dict]:
    """Return statutory default leave balances for Singapore employees.

    These are the minimum entitlements under the Employment Act for
    a first-year employee. Used as a fallback when no leave balances
    have been recorded.
    """
    current_year = datetime.now(timezone.utc).year
    return [
        {
            "leave_type": "annual",
            "year": current_year,
            "entitlement_days": 7.0,
            "used_days": 0.0,
            "pending_days": 0.0,
        },
        {
            "leave_type": "sick",
            "year": current_year,
            "entitlement_days": 14.0,
            "used_days": 0.0,
            "pending_days": 0.0,
        },
        {
            "leave_type": "hospitalization",
            "year": current_year,
            "entitlement_days": 60.0,
            "used_days": 0.0,
            "pending_days": 0.0,
        },
    ]


# --------------------------------------------------------------------------
# POST /employees/invite — Admin sends invitation
# --------------------------------------------------------------------------


@router.post("/invite")
async def invite_employee(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Invite an employee to join the company on the platform.

    Creates an invitation with a unique token valid for 7 days.
    The invitation email address and role are specified in the request body.

    Status codes:
        200: Invitation created
        400: Missing or invalid fields
        403: Insufficient permissions
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(
            status_code=400,
            detail="No company associated with your account.",
        )

    check_rate_limit(
        f"invite:{company_id}",
        max_requests=50,
        window_seconds=3600,
        action_name="sending invitations",
    )

    body = await request.json()
    email = body.get("email", "").strip().lower()
    role = body.get("role", "employee")

    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    # Validate role — only employee or hr_manager can be invited
    if role not in ("employee", "hr_manager"):
        raise HTTPException(
            status_code=400,
            detail="Invited role must be 'employee' or 'hr_manager'.",
        )

    # T281: Duplicate invitation guard — check for existing user or active invite
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder
    import hr_advisory.models  # noqa: F401

    wf_check = WorkflowBuilder()
    wf_check.add_node(
        "UserListNode",
        "check_user",
        {"filter": {"email": email}, "limit": 10, "enable_cache": False},
    )
    rt = LocalRuntime()
    res, _ = rt.execute(wf_check.build())
    existing_users = (
        res["check_user"].get("records", []) if isinstance(res["check_user"], dict) else []
    )
    for u in existing_users:
        if u.get("company_id") == company_id:
            raise HTTPException(
                status_code=409,
                detail=f"{email} is already a member of this company.",
            )

    # Deactivate any existing active invitation for this email + company
    wf_inv = WorkflowBuilder()
    wf_inv.add_node(
        "InvitationListNode",
        "check_inv",
        {"filter": {"email": email, "company_id": company_id}, "limit": 100, "enable_cache": False},
    )
    rt2 = LocalRuntime()
    res2, _ = rt2.execute(wf_inv.build())
    existing_invites = (
        res2["check_inv"].get("records", []) if isinstance(res2["check_inv"], dict) else []
    )
    for inv in existing_invites:
        if inv.get("is_active") and not inv.get("accepted_at"):
            _update_invitation(inv["id"], {"is_active": False})
            logger.info("Deactivated previous invitation %s for %s", inv["id"], email)

    # Generate unique token and expiry
    token = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(days=_INVITATION_EXPIRY_DAYS)).isoformat()

    inviter_id = int(current_user.get("sub", 0))
    _create_invitation(
        company_id=company_id,
        inviter_id=inviter_id,
        email=email,
        role=role,
        token=token,
        expires_at=expires_at,
    )

    logger.info(
        "Invitation created: email=%s, role=%s, company=%s, inviter=%s",
        email,
        role,
        company_id,
        inviter_id,
    )

    # T284: Return token in response — single-use, email-locked, 7-day expiry
    # makes interception low-risk. Admin shares link via WhatsApp/email.
    import os

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    invite_url = f"{frontend_url}/signup?token={token}"

    return {
        "message": "Invitation created successfully.",
        "invite_url": invite_url,
        "invitation": {
            "email": email,
            "role": role,
            "expires_at": expires_at,
            "company_id": company_id,
        },
    }


# --------------------------------------------------------------------------
# GET /employees/invite/{token} — Validate invitation token (public)
# --------------------------------------------------------------------------


@router.get("/invite/{token}")
async def validate_invitation(token: str) -> dict:
    """Validate an invitation token.

    This is a public endpoint used during the employee registration flow
    to verify the invitation is valid before showing the registration form.

    Status codes:
        200: Valid invitation
        404: Invalid, expired, or already accepted
    """
    invitation = _find_invitation_by_token(token)
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    # Check if already accepted
    if invitation.get("accepted_at"):
        raise HTTPException(
            status_code=404,
            detail="This invitation has already been used.",
        )

    # Check if deactivated
    if not invitation.get("is_active", True):
        raise HTTPException(status_code=404, detail="Invitation not found.")

    # Check expiry
    expires_at_str = invitation.get("expires_at", "")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            # Make offset-aware if naive
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(
                    status_code=404,
                    detail="This invitation has expired.",
                )
        except ValueError:
            # If the date can't be parsed, treat as expired for safety
            raise HTTPException(
                status_code=404,
                detail="This invitation has expired.",
            )

    # T282: Look up company name so frontend can show it during invite acceptance
    company_name = ""
    inv_company_id = invitation.get("company_id")
    if inv_company_id:
        try:
            from kailash.runtime import LocalRuntime as _LR
            from kailash.workflow.builder import WorkflowBuilder as _WB
            import hr_advisory.models  # noqa: F401

            _wf = _WB()
            _wf.add_node("CompanyReadNode", "read_co", {"id": inv_company_id})
            _rt = _LR()
            _res, _ = _rt.execute(_wf.build())
            company_name = _res["read_co"].get("name", "") if _res.get("read_co") else ""
        except Exception:
            company_name = ""

    return {
        "valid": True,
        "email": invitation.get("email"),
        "role": invitation.get("role"),
        "company_id": inv_company_id,
        "company_name": company_name,
    }


# --------------------------------------------------------------------------
# GET /employees/invitations — List invitations for current company (T283)
# --------------------------------------------------------------------------


@router.get("/invitations")
async def list_invitations(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all invitations for the current user's company.

    Returns each invitation enriched with a computed status:
    - pending: active, not expired, not accepted
    - expired: past expires_at
    - accepted: accepted_at is set
    - revoked: is_active=False (admin revoked)

    Status codes:
        200: Success with list of invitations
        400: No company associated with the user
        403: Insufficient permissions
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(
            status_code=400,
            detail="No company associated with your account.",
        )

    invitations = _list_invitations_for_company(company_id)

    enriched = []
    for inv in invitations:
        status = _compute_invitation_status(inv)
        enriched.append(
            {
                "id": inv.get("id"),
                "email": inv.get("email"),
                "role": inv.get("role"),
                "status": status,
                "sent_date": inv.get("created_at"),
                "created_at": inv.get("created_at"),
                "expires_at": inv.get("expires_at"),
                "accepted_at": inv.get("accepted_at"),
            }
        )

    return {
        "invitations": enriched,
        "count": len(enriched),
        "company_id": company_id,
    }


# --------------------------------------------------------------------------
# DELETE /employees/invite/{invitation_id} — Revoke an invitation (T283)
# --------------------------------------------------------------------------


@router.delete("/invite/{invitation_id}")
async def revoke_invitation(
    invitation_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Revoke a pending invitation.

    Sets is_active=False on the invitation, preventing the token from being
    used to register. Only active, non-accepted invitations can be revoked.

    Status codes:
        200: Invitation revoked successfully
        400: No company associated with the user
        404: Invitation not found or belongs to another company
        409: Invitation already accepted or already revoked
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(
            status_code=400,
            detail="No company associated with your account.",
        )

    invitation = _find_invitation_by_id(invitation_id)
    if invitation is None or invitation.get("company_id") != company_id:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found.",
        )

    if invitation.get("accepted_at"):
        raise HTTPException(
            status_code=409,
            detail="Cannot revoke an invitation that has already been accepted.",
        )

    if not invitation.get("is_active"):
        raise HTTPException(
            status_code=409,
            detail="Invitation has already been revoked.",
        )

    _update_invitation(invitation_id, {"is_active": False})

    logger.info(
        "Invitation %s revoked by user %s (company %s)",
        invitation_id,
        current_user.get("sub"),
        company_id,
    )

    return {"message": "Invitation revoked successfully."}


# --------------------------------------------------------------------------
# POST /employees/invite/{invitation_id}/resend — Resend invitation (T283)
# --------------------------------------------------------------------------


@router.post("/invite/{invitation_id}/resend")
async def resend_invitation(
    invitation_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Resend an invitation with a fresh token and 7-day expiry.

    Deactivates the original invitation and creates a new one with the same
    email and role but a fresh token. Returns the new invite URL for sharing.

    Status codes:
        200: New invitation created with fresh token
        400: No company associated with the user
        404: Invitation not found or belongs to another company
        409: Invitation already accepted
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(
            status_code=400,
            detail="No company associated with your account.",
        )

    invitation = _find_invitation_by_id(invitation_id)
    if invitation is None or invitation.get("company_id") != company_id:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found.",
        )

    if invitation.get("accepted_at"):
        raise HTTPException(
            status_code=409,
            detail="Cannot resend an invitation that has already been accepted.",
        )

    # Deactivate old invitation
    _update_invitation(invitation_id, {"is_active": False})

    # Create new invitation with fresh token and expiry
    new_token = str(uuid.uuid4())
    new_expires_at = (
        datetime.now(timezone.utc) + timedelta(days=_INVITATION_EXPIRY_DAYS)
    ).isoformat()
    inviter_id = int(current_user.get("sub", 0))

    _create_invitation(
        company_id=company_id,
        inviter_id=inviter_id,
        email=invitation["email"],
        role=invitation["role"],
        token=new_token,
        expires_at=new_expires_at,
    )

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    invite_url = f"{frontend_url}/signup?token={new_token}"

    logger.info(
        "Invitation %s resent as new invitation for %s by user %s (company %s)",
        invitation_id,
        invitation["email"],
        current_user.get("sub"),
        company_id,
    )

    return {
        "message": "Invitation resent successfully.",
        "invite_url": invite_url,
        "invitation": {
            "email": invitation["email"],
            "role": invitation["role"],
            "expires_at": new_expires_at,
            "company_id": company_id,
        },
    }


# --------------------------------------------------------------------------
# GET /employees — List employees for current company (admin only)
# --------------------------------------------------------------------------


@router.get("")
async def list_employees(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all employees for the current user's company.

    Returns employee records enriched with user email and name.

    Status codes:
        200: Success
        403: Insufficient permissions
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(
            status_code=400,
            detail="No company associated with your account.",
        )

    employees = _list_employees_for_company(company_id)

    # Bulk-fetch user details (1 query instead of N)
    user_ids = [emp.get("user_id") for emp in employees if emp.get("user_id")]
    users_map = _bulk_find_users(user_ids)

    # Lightweight serialization (no decryption for list view)
    enriched = []
    for emp in employees:
        user = users_map.get(emp.get("user_id"))
        enriched.append(_serialize_employee_summary(emp, user))

    return {
        "employees": enriched,
        "count": len(enriched),
        "company_id": company_id,
    }


# --------------------------------------------------------------------------
# GET /employees/me — Get current employee's own record
# --------------------------------------------------------------------------


@router.get("/me")
async def get_my_employee_record(
    current_user: dict = Depends(require_role("employee", "owner", "hr_manager")),
) -> dict:
    """Get the current user's employee record.

    Any authenticated user with an employee record can access this.
    If no employee record exists, returns a synthesized record from
    the user's auth data to avoid 404 console errors on the frontend.

    Status codes:
        200: Success (may return synthesized data if no employee record)
        404: No user data available at all
    """
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    if company_id is None:
        # No company yet — return a synthesized record from user data
        # instead of 404 to avoid console errors on the frontend.
        user = _find_user_by_id(user_id)
        if user is not None:
            role = current_user.get("role", "")
            return {
                "id": 0,
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "department": "",
                "designation": role.replace("_", " ").title() if role else "Employee",
                "start_date": "",
                "employment_type": "full_time",
            }
        raise HTTPException(
            status_code=404,
            detail="No employee record found.",
        )

    employee = _find_employee_by_user_id(user_id, company_id)
    user = _find_user_by_id(user_id)

    # Auto-create an employee record for owner/hr_manager users who don't
    # have one yet (e.g. the company creator visiting My Profile for the
    # first time).  This prevents 404 errors on the profile page.
    if employee is None:
        role = current_user.get("role")
        if role in ("owner", "hr_manager") and user is not None:
            try:
                _create_employee({
                    "user_id": user_id,
                    "company_id": company_id,
                    "department": "",
                    "designation": role.replace("_", " ").title(),
                    "employment_type": "full_time",
                    "start_date": "",
                    "is_active": True,
                })
                employee = _find_employee_by_user_id(user_id, company_id)
            except Exception as exc:
                logger.warning(
                    "Auto-create employee failed for user_id=%s: %s", user_id, exc
                )

    if employee is None:
        # Return a synthesized record from user data instead of 404.
        # This prevents console errors on the frontend for owner/hr_manager
        # users who may not have a full employee record yet.
        if user is not None:
            role = current_user.get("role", "")
            return {
                "id": 0,
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "department": "",
                "designation": role.replace("_", " ").title() if role else "Employee",
                "start_date": "",
                "employment_type": "full_time",
            }
        raise HTTPException(
            status_code=404,
            detail="No employee record found.",
        )

    return _serialize_employee(employee, user, include_sensitive=False)


# --------------------------------------------------------------------------
# PUT /employees/me — Update own profile (employee self-service, T309/T316)
# --------------------------------------------------------------------------


@router.put("/me")
async def update_my_profile(
    request: Request,
    current_user: dict = Depends(require_role("employee", "owner", "hr_manager")),
) -> dict:
    """Update the current employee's personal profile fields.

    Employees can update their own personal data (name, phone, address,
    bank details, etc.) but NOT HR-sensitive fields (salary, department,
    designation). Those are admin-only via PUT /employees/{id}.
    """
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    if company_id is None:
        raise HTTPException(status_code=404, detail="No employee record found.")

    employee = _find_employee_by_user_id(user_id, company_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="No employee record found.")

    body = await request.json()

    # Fields employees can update themselves
    SELF_SERVICE_FIELDS = {
        "name",
        "alias",
        "date_of_birth",
        "gender",
        "race",
        "nationality",
        "religion",
        "marital_status",
        "phone",
        "photo_url",
        "nric_fin",
        "nric_fin_last4",
        "residential_address",
        "postal_code",
        "address_block",
        "address_street",
        "address_unit",
        "address_building",
        "address_postal_code",
        "bank_name",
        "bank_account_number",
        "bank_account_last4",
        "bank_code",
        "branch_code",
    }

    updates = {k: v for k, v in body.items() if k in SELF_SERVICE_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # Auto-set last4 masks for sensitive fields
    if "nric_fin" in updates and updates["nric_fin"]:
        updates["nric_fin_last4"] = updates["nric_fin"][-4:]
    if "bank_account_number" in updates and updates["bank_account_number"]:
        updates["bank_account_last4"] = updates["bank_account_number"][-4:]

    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder
    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        "EmployeeUpdateNode",
        "update_me",
        {"filter": {"id": employee["id"]}, "fields": updates},
    )
    runtime = LocalRuntime()
    runtime.execute(wf.build())

    # PDPA audit log for sensitive field access
    sensitive_accessed = {"nric_fin", "bank_account_number"} & set(updates.keys())
    if sensitive_accessed:
        _log_pdpa_access(
            accessed_by=user_id,
            company_id=company_id,
            data_subject_id=employee["id"],
            categories=list(sensitive_accessed),
            action="self_service_update",
        )

    return {"updated": True, "fields": list(updates.keys())}


# --------------------------------------------------------------------------
# GET /employees/me/leave — Get current employee's leave balances
# --------------------------------------------------------------------------


@router.get("/me/leave")
async def get_my_leave_balances(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get leave balances for the current employee.

    Returns leave balances for the current year. If no balances have been
    recorded, returns the statutory minimum entitlements under the
    Singapore Employment Act.

    Status codes:
        200: Success (may return statutory defaults if no records exist)
    """
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    if company_id is None:
        return {"balances": _statutory_defaults()}

    employee = _find_employee_by_user_id(user_id, company_id)
    if employee is None:
        # Return statutory defaults for non-employee users (admins viewing their own)
        return {"balances": _statutory_defaults()}

    balances = _get_leave_balances(employee["id"], company_id)
    if not balances:
        return {"balances": _statutory_defaults()}

    return {
        "balances": [
            {
                "leave_type": b.get("leave_type", ""),
                "year": b.get("year", 0),
                "entitlement_days": b.get("entitlement_days", 0.0),
                "used_days": b.get("used_days", 0.0),
                "pending_days": b.get("pending_days", 0.0),
            }
            for b in balances
        ],
    }


# --------------------------------------------------------------------------
# GET /employees/policies — List company policies
# DEPRECATED: The canonical endpoint is now GET /policies/ with full CRUD,
# versioning, file uploads, and acknowledgment tracking. This endpoint is
# retained for backward compatibility and will be removed in a future release.
# --------------------------------------------------------------------------


@router.get("/policies", deprecated=True)
async def list_policies(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List company policies for the current user's company.

    .. deprecated::
        Use ``GET /policies/`` instead, which supports filtering by
        category/status, versioning, and acknowledgment tracking.

    Returns all active policies (leave, FWA, handbook, safety, etc.)
    that have been configured for the company. Default policies are
    seeded automatically when a company profile is created.

    Status codes:
        200: Success
    """
    company_id = current_user.get("company_id")
    if company_id is None:
        return {"policies": [], "count": 0}

    policies = _list_policies_for_company(company_id)
    return {
        "policies": [
            {
                "id": p.get("id"),
                "policy_type": p.get("policy_type", ""),
                "title": p.get("title", ""),
                "content": p.get("content", ""),
                "effective_date": p.get("effective_date", ""),
                "is_active": p.get("is_active", True),
            }
            for p in policies
        ],
        "count": len(policies),
    }


# --------------------------------------------------------------------------
# GET /employees/pdpa-logs — View PDPA access audit trail (owner only)
# --------------------------------------------------------------------------


@router.get("/pdpa-logs")
async def get_pdpa_logs(
    employee_id: int = 0,
    current_user: dict = Depends(require_role("owner")),
) -> dict:
    """View PDPA access logs. Owner only.

    Returns the most recent 100 audit entries for the company, optionally
    filtered by a specific employee (data subject).
    """
    company_id = get_current_company_id(current_user)
    filter_dict: dict = {"company_id": company_id}
    if employee_id:
        filter_dict["data_subject_id"] = employee_id
    logs = _list_pdpa_logs(filter_dict)
    logs.sort(key=lambda entry: entry.get("created_at", ""), reverse=True)
    return {"logs": logs[:100]}


# --------------------------------------------------------------------------
# Custom Field Definition CRUD (company-level)
# MUST be placed BEFORE /{employee_id} to avoid path conflicts
# --------------------------------------------------------------------------


@router.get("/custom-fields")
async def list_custom_field_definitions(
    applies_to: str = "",
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List custom field definitions for the company.

    Optionally filter by applies_to (employee/leave/claim).
    """
    company_id = get_current_company_id(current_user)
    definitions = _list_custom_field_definitions(company_id, applies_to=applies_to)
    definitions.sort(key=lambda d: d.get("display_order", 0))
    return {"definitions": definitions, "count": len(definitions)}


@router.post("/custom-fields")
async def create_custom_field_definition(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a custom field definition for the company."""
    company_id = get_current_company_id(current_user)
    body = await request.json()

    field_name = body.get("field_name", "").strip()
    field_label = body.get("field_label", "").strip()
    if not field_name:
        raise HTTPException(status_code=400, detail="'field_name' is required.")
    if not field_label:
        raise HTTPException(status_code=400, detail="'field_label' is required.")

    _validate_text_length(field_name, "field_name", MAX_NAME_LENGTH)
    _validate_text_length(field_label, "field_label", MAX_NAME_LENGTH)

    field_type = body.get("field_type", "text")
    valid_types = ("text", "number", "date", "dropdown", "checkbox")
    if field_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"field_type must be one of: {', '.join(valid_types)}.",
        )

    applies_to = body.get("applies_to", "employee")
    valid_applies = ("employee", "leave", "claim")
    if applies_to not in valid_applies:
        raise HTTPException(
            status_code=400,
            detail=f"applies_to must be one of: {', '.join(valid_applies)}.",
        )

    dropdown_options = body.get("dropdown_options", "")
    if dropdown_options and isinstance(dropdown_options, list):
        dropdown_options = json.dumps(dropdown_options)

    definition = _create_custom_field_definition(
        {
            "company_id": company_id,
            "field_name": field_name,
            "field_label": field_label,
            "field_type": field_type,
            "dropdown_options": dropdown_options if dropdown_options else "",
            "is_required": bool(body.get("is_required", False)),
            "display_order": int(body.get("display_order", 0)),
            "applies_to": applies_to,
        }
    )

    return {"definition": definition}


@router.patch("/custom-fields/{field_id}")
async def update_custom_field_definition_endpoint(
    field_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a custom field definition."""
    company_id = get_current_company_id(current_user)
    existing = _read_custom_field_definition(field_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Custom field definition not found.")

    body = await request.json()
    allowed_fields = {
        "field_name",
        "field_label",
        "field_type",
        "dropdown_options",
        "is_required",
        "display_order",
        "applies_to",
    }
    updates = {}
    for key in allowed_fields:
        if key in body:
            updates[key] = body[key]

    if "field_name" in updates:
        _validate_text_length(updates["field_name"], "field_name", MAX_NAME_LENGTH)
    if "field_label" in updates:
        _validate_text_length(updates["field_label"], "field_label", MAX_NAME_LENGTH)
    if "field_type" in updates:
        valid_types = ("text", "number", "date", "dropdown", "checkbox")
        if updates["field_type"] not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"field_type must be one of: {', '.join(valid_types)}.",
            )
    if "applies_to" in updates:
        valid_applies = ("employee", "leave", "claim")
        if updates["applies_to"] not in valid_applies:
            raise HTTPException(
                status_code=400,
                detail=f"applies_to must be one of: {', '.join(valid_applies)}.",
            )
    if "dropdown_options" in updates and isinstance(updates["dropdown_options"], list):
        updates["dropdown_options"] = json.dumps(updates["dropdown_options"])

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = _update_custom_field_definition(field_id, updates)
    return {"definition": result}


@router.delete("/custom-fields/{field_id}")
async def delete_custom_field_definition_endpoint(
    field_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a custom field definition (soft-delete via is_active flag)."""
    company_id = get_current_company_id(current_user)
    existing = _read_custom_field_definition(field_id)
    if existing is None or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Custom field definition not found.")

    # Soft-delete: we mark the field_name to indicate deletion rather than
    # hard-deleting, preserving referential integrity for existing values.
    _update_custom_field_definition(
        field_id,
        {"field_name": f"__deleted__{existing.get('field_name', '')}"},
    )
    return {"message": "Custom field definition deleted."}


# --------------------------------------------------------------------------
# GET /employees/{id} — Get a specific employee (admin only)
# --------------------------------------------------------------------------


@router.get("/{employee_id}")
async def get_employee(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a specific employee by ID. Admin only.

    Returns decrypted PII fields and logs a PDPA access audit entry.
    """
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")
    user = _find_user_by_id(emp.get("user_id"))

    # PDPA audit — log that sensitive data was viewed
    actor_id = int(current_user.get("sub", 0))
    _log_pdpa_access(
        accessed_by=actor_id,
        company_id=company_id,
        data_subject_id=employee_id,
        categories=["nric", "bank_account", "salary", "work_pass"],
        action="view",
    )

    return _serialize_employee(emp, user, include_sensitive=True)


# --------------------------------------------------------------------------
# PATCH /employees/{id} — Update employee (admin only)
# --------------------------------------------------------------------------


@router.patch("/{employee_id}")
async def update_employee(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an employee record. Admin only.

    Accepts partial updates — only fields provided will be changed.
    Auto-generates employment events for significant changes (salary, designation).
    """
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()

    # Whitelist of updatable fields
    allowed_fields = {
        "department",
        "designation",
        "employment_type",
        "start_date",
        "end_date",
        "nationality",
        "pass_type",
        "salary_monthly",
        "notice_period_days",
        "date_of_birth",
        "gender",
        "marital_status",
        "race",
        "religion",
        "phone",
        "nric_fin",
        "work_pass_number",
        "work_pass_expiry",
        "immigration_status",
        "immigration_effective_date",
        "bank_name",
        "bank_account_number",
        "bank_code",
        "residential_address",
        "postal_code",
        "reporting_manager_id",
        "probation_months",
        "probation_end_date",
        "confirmation_status",
        "is_active",
        "employee_id_internal",
        "iras_auto_inclusion",
        "tax_reference",
        "cpf_status",
        "amcs_enabled",
        "pmbs_enabled",
        "community_chest_amount",
        "shg_override_amount",
    }

    updates = {k: v for k, v in body.items() if k in allowed_fields}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # Auto-derive last4 fields (plaintext) then encrypt the full values
    pdpa_modified_categories: list[str] = []

    if "nric_fin" in updates and updates["nric_fin"]:
        updates["nric_fin_last4"] = updates["nric_fin"][-4:]
        updates["nric_fin"] = encrypt_field(updates["nric_fin"])
        pdpa_modified_categories.append("nric")

    if "bank_account_number" in updates and updates["bank_account_number"]:
        updates["bank_account_last4"] = updates["bank_account_number"][-4:]
        updates["bank_account_number"] = encrypt_field(updates["bank_account_number"])
        pdpa_modified_categories.append("bank_account")

    if "work_pass_number" in updates and updates["work_pass_number"]:
        updates["work_pass_number"] = encrypt_field(updates["work_pass_number"])
        pdpa_modified_categories.append("work_pass")

    if "salary_monthly" in updates:
        pdpa_modified_categories.append("salary")

    # Track significant changes for employment events
    actor_id = int(current_user.get("sub", 0))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if "salary_monthly" in updates and updates["salary_monthly"] != emp.get("salary_monthly"):
        _create_employment_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "salary_revision",
                "event_date": today,
                "description": "Salary revised",
                "old_value": {"salary_monthly": emp.get("salary_monthly", 0)},
                "new_value": {"salary_monthly": updates["salary_monthly"]},
                "effective_date": today,
                "approved_by": actor_id,
            }
        )

    if "designation" in updates and updates["designation"] != emp.get("designation"):
        _create_employment_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "promoted",
                "event_date": today,
                "description": f"Designation changed to {updates['designation']}",
                "old_value": {"designation": emp.get("designation", "")},
                "new_value": {"designation": updates["designation"]},
                "effective_date": today,
                "approved_by": actor_id,
            }
        )

    if "department" in updates and updates["department"] != emp.get("department"):
        _create_employment_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "transferred",
                "event_date": today,
                "description": f"Transferred to {updates['department']}",
                "old_value": {"department": emp.get("department", "")},
                "new_value": {"department": updates["department"]},
                "effective_date": today,
                "approved_by": actor_id,
            }
        )

    for field in ["department", "designation", "residential_address", "postal_code"]:
        if field in updates and isinstance(updates[field], str):
            _validate_text_length(
                updates[field],
                field,
                MAX_ADDRESS_LENGTH if "address" in field else MAX_NAME_LENGTH,
            )

    # PDPA audit — log modification of protected fields
    if pdpa_modified_categories:
        _log_pdpa_access(
            accessed_by=actor_id,
            company_id=company_id,
            data_subject_id=employee_id,
            categories=pdpa_modified_categories,
            action="modify",
        )

    _update_employee(employee_id, updates)
    updated_emp = _find_employee_by_id(employee_id)
    user = _find_user_by_id(updated_emp.get("user_id"))
    return _serialize_employee(updated_emp, user, include_sensitive=True)


# --------------------------------------------------------------------------
# GET /employees/{id}/salary-components — List salary components
# --------------------------------------------------------------------------


@router.get("/{employee_id}/salary-components")
async def list_salary_components(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List active salary components for an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    components = _list_salary_components(employee_id)
    total_allowances = sum(
        c.get("amount", 0)
        for c in components
        if c.get("component_type") in ("fixed_allowance", "variable_allowance")
    )
    total_deductions = sum(
        c.get("amount", 0)
        for c in components
        if c.get("component_type") in ("fixed_deduction", "variable_deduction")
    )
    basic_salary = emp.get("salary_monthly", 0.0)

    return {
        "components": components,
        "summary": {
            "basic_salary": basic_salary,
            "total_allowances": total_allowances,
            "total_deductions": total_deductions,
            "gross_monthly": basic_salary + total_allowances - total_deductions,
        },
    }


# --------------------------------------------------------------------------
# POST /employees/{id}/salary-components — Add a salary component
# --------------------------------------------------------------------------


@router.post("/{employee_id}/salary-components")
async def create_salary_component_endpoint(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a salary component to an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()
    required = ["component_type", "name", "amount"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"'{field}' is required.")

    amount = float(body["amount"])
    if not math.isfinite(amount) or amount < 0:
        raise HTTPException(status_code=400, detail="Invalid amount.")

    component = _create_salary_component(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "component_type": body["component_type"],
            "name": body["name"],
            "amount": amount,
            "frequency": body.get("frequency", "monthly"),
            "is_taxable": body.get("is_taxable", True),
            "is_cpf_applicable": body.get("is_cpf_applicable", True),
            "effective_from": body.get("effective_from", ""),
            "effective_to": body.get("effective_to", ""),
            "is_active": True,
        }
    )

    return {"component": component}


# --------------------------------------------------------------------------
# PATCH /employees/{id}/salary-components/{component_id}
# --------------------------------------------------------------------------


@router.patch("/{employee_id}/salary-components/{component_id}")
async def update_salary_component_endpoint(
    employee_id: int,
    component_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update or deactivate a salary component."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    component = _read_salary_component(component_id)
    if component is None or component.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Salary component not found.")

    body = await request.json()
    allowed = {
        "name",
        "amount",
        "frequency",
        "is_taxable",
        "is_cpf_applicable",
        "effective_from",
        "effective_to",
        "is_active",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    if "amount" in updates:
        amt = float(updates["amount"])
        if not math.isfinite(amt) or amt < 0:
            raise HTTPException(status_code=400, detail="Invalid amount.")

    _update_salary_component(component_id, updates)
    return {"message": "Salary component updated."}


# --------------------------------------------------------------------------
# Emergency Contacts CRUD
# --------------------------------------------------------------------------


@router.get("/{employee_id}/emergency-contacts")
async def list_emergency_contacts_endpoint(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "employee")),
) -> dict:
    """List emergency contacts for an employee."""
    company_id = get_current_company_id(current_user)
    role = current_user.get("role", "employee")

    if role == "employee":
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_by_user_id(user_id, company_id)
        if emp is None or emp.get("id") != employee_id:
            raise HTTPException(status_code=403, detail="Access denied.")
    else:
        emp = _find_employee_by_id(employee_id)
        if emp is None or emp.get("company_id") != company_id:
            raise HTTPException(status_code=404, detail="Employee not found.")

    contacts = _list_emergency_contacts(employee_id)
    return {"contacts": contacts}


@router.post("/{employee_id}/emergency-contacts")
async def create_emergency_contact_endpoint(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add an emergency contact for an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _list_emergency_contacts(employee_id)
    if len(existing) >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 emergency contacts allowed.")

    body = await request.json()
    if not body.get("name") or not body.get("phone_primary"):
        raise HTTPException(status_code=400, detail="Name and phone are required.")

    contact = _create_emergency_contact(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "name": body["name"],
            "relationship": body.get("relationship", ""),
            "phone_primary": body["phone_primary"],
            "phone_secondary": body.get("phone_secondary", ""),
            "email": body.get("email", ""),
            "is_next_of_kin": body.get("is_next_of_kin", False),
            "priority": len(existing) + 1,
        }
    )

    return {"contact": contact}


@router.patch("/{employee_id}/emergency-contacts/{contact_id}")
async def update_emergency_contact_endpoint(
    employee_id: int,
    contact_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an emergency contact."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    contact = _read_emergency_contact(contact_id)
    if contact is None or contact.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Emergency contact not found.")

    body = await request.json()
    allowed = {
        "name",
        "relationship",
        "phone_primary",
        "phone_secondary",
        "email",
        "is_next_of_kin",
        "priority",
    }
    updates = {k: v for k, v in body.items() if k in allowed}

    _update_emergency_contact(contact_id, updates)
    return {"message": "Emergency contact updated."}


# --------------------------------------------------------------------------
# Employment History
# --------------------------------------------------------------------------


@router.get("/{employee_id}/history")
async def list_employment_history(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "employee")),
) -> dict:
    """Get employment event timeline for an employee."""
    company_id = get_current_company_id(current_user)
    role = current_user.get("role", "employee")

    if role == "employee":
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_by_user_id(user_id, company_id)
        if emp is None or emp.get("id") != employee_id:
            raise HTTPException(status_code=403, detail="Access denied.")
    else:
        emp = _find_employee_by_id(employee_id)
        if emp is None or emp.get("company_id") != company_id:
            raise HTTPException(status_code=404, detail="Employee not found.")

    events = _list_employment_events(employee_id)
    # Sort by event_date descending (most recent first)
    events.sort(key=lambda e: e.get("event_date", ""), reverse=True)
    return {"events": events}


@router.post("/{employee_id}/history")
async def add_employment_event(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Manually add an employment event (for backdating historical records)."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()
    if not body.get("event_type") or not body.get("event_date"):
        raise HTTPException(status_code=400, detail="event_type and event_date are required.")

    actor_id = int(current_user.get("sub", 0))
    event = _create_employment_event(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "event_type": body["event_type"],
            "event_date": body["event_date"],
            "description": body.get("description", ""),
            "old_value": body.get("old_value"),
            "new_value": body.get("new_value"),
            "effective_date": body.get("effective_date", body["event_date"]),
            "approved_by": actor_id,
            "notes": body.get("notes", ""),
        }
    )

    return {"event": event}


# --------------------------------------------------------------------------
# Employee Documents
# --------------------------------------------------------------------------


@router.get("/{employee_id}/documents")
async def list_employee_documents_endpoint(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "employee")),
) -> dict:
    """List documents for an employee."""
    company_id = get_current_company_id(current_user)
    role = current_user.get("role", "employee")

    if role == "employee":
        user_id = int(current_user.get("sub", 0))
        emp = _find_employee_by_user_id(user_id, company_id)
        if emp is None or emp.get("id") != employee_id:
            raise HTTPException(status_code=403, detail="Access denied.")
        docs = _list_employee_documents(employee_id)
        # Employees can't see confidential documents
        docs = [d for d in docs if not d.get("is_confidential", False)]
    else:
        emp = _find_employee_by_id(employee_id)
        if emp is None or emp.get("company_id") != company_id:
            raise HTTPException(status_code=404, detail="Employee not found.")
        docs = _list_employee_documents(employee_id)

    return {"documents": docs}


@router.post("/{employee_id}/documents")
async def upload_employee_document(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Upload a document for an employee.

    Accepts multipart/form-data with fields: file, document_type, description, is_confidential.
    """
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    form = await request.form()
    file = form.get("file")
    if file is None:
        raise HTTPException(status_code=400, detail="File is required.")

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit.")

    content_type = getattr(file, "content_type", "application/octet-stream")
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Use PDF, JPG, PNG, or DOCX.",
        )

    # Save file to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_ext = os.path.splitext(file.filename or "file")[1]
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
    if file_ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension '{file_ext}' not allowed.")
    stored_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    actor_id = int(current_user.get("sub", 0))
    doc = _create_employee_document(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "document_type": form.get("document_type", "other"),
            "file_name": file.filename or "unknown",
            "file_path": file_path,
            "file_size": len(content),
            "mime_type": content_type,
            "uploaded_by": actor_id,
            "description": form.get("description", ""),
            "is_confidential": form.get("is_confidential", "false").lower() == "true",
            "is_active": True,
        }
    )

    return {
        "document": {k: v for k, v in doc.items() if k != "file_path"},
        "file_name": stored_name,
    }


@router.delete("/{employee_id}/documents/{document_id}")
async def delete_employee_document(
    employee_id: int,
    document_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Soft-delete an employee document."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    doc = _read_employee_document(document_id)
    if doc is None or doc.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    _update_employee_document(document_id, {"is_active": False})
    return {"message": "Document deleted."}


# --------------------------------------------------------------------------
# GET /employees/org-chart — Organisational hierarchy
# --------------------------------------------------------------------------


@router.get("/org-chart/data")
async def get_org_chart(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get organisational chart data derived from reporting manager relationships."""
    company_id = get_current_company_id(current_user)
    employees = _list_employees_for_company(company_id)

    nodes = []
    for emp in employees:
        user = _find_user_by_id(emp.get("user_id"))
        nodes.append(
            {
                "id": emp.get("id"),
                "name": user.get("name", "") if user else "",
                "designation": emp.get("designation", ""),
                "department": emp.get("department", ""),
                "reporting_manager_id": emp.get("reporting_manager_id"),
            }
        )

    return {"nodes": nodes}


# --------------------------------------------------------------------------
# POST /employees/import/preview — CSV import preview
# --------------------------------------------------------------------------


@router.post("/import/preview")
async def import_preview(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Parse and validate a CSV file for bulk employee import.

    Returns a preview of parsed records with validation errors flagged.
    Does not create any records.
    """
    form = await request.form()
    file = form.get("file")
    if file is None:
        raise HTTPException(status_code=400, detail="CSV file is required.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))
    # Normalize headers to lowercase/snake_case so CSVs with any casing work
    if reader.fieldnames:
        reader.fieldnames = [f.strip().lower().replace(" ", "_") for f in reader.fieldnames]
    records = []
    errors = []

    def _parse_date(raw: str) -> str:
        """Try common date formats and return YYYY-MM-DD or empty string."""
        if not raw:
            return ""
        for fmt in ("%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return raw

    for i, row in enumerate(reader, start=2):  # Row 1 is header
        if i > MAX_IMPORT_ROWS + 1:  # +1 because i starts at 2
            errors.append({"row": i, "error": f"CSV exceeds maximum of {MAX_IMPORT_ROWS} rows."})
            break
        record = {
            "row": i,
            "name": row.get("name", "").strip(),
            "email": row.get("email", "").strip().lower(),
            "designation": row.get("designation", "").strip(),
            "department": row.get("department", "").strip(),
            "employment_type": row.get("employment_type", "full_time").strip(),
            "nationality": row.get("nationality", "").strip(),
            "pass_type": row.get("pass_type", "").strip(),
            "salary_monthly": row.get("salary_monthly", "0").strip(),
            "date_of_birth": _parse_date(row.get("date_of_birth", "")),
            "nric_fin": row.get("nric_fin", "").strip(),
            "bank_name": row.get("bank_name", "").strip(),
            "bank_account_number": row.get("bank_account_number", "").strip(),
            "start_date": _parse_date(row.get("start_date", "")),
            "work_pass_number": row.get("work_pass_number", "").strip(),
            "work_pass_expiry": _parse_date(row.get("work_pass_expiry", "")),
        }

        row_errors = []
        if not record["name"]:
            row_errors.append("Name is required.")
        if not record["email"]:
            row_errors.append("Email is required.")
        elif "@" not in record["email"]:
            row_errors.append("Invalid email format.")
        try:
            salary = float(record["salary_monthly"])
            if salary < 0:
                row_errors.append("Salary cannot be negative.")
            record["salary_monthly"] = salary
        except ValueError:
            row_errors.append("Invalid salary value.")
            record["salary_monthly"] = 0

        record["errors"] = row_errors
        record["valid"] = len(row_errors) == 0
        records.append(record)
        errors.extend([{"row": i, "error": e} for e in row_errors])

    valid_count = sum(1 for r in records if r["valid"])
    return {
        "records": records,
        "total": len(records),
        "valid": valid_count,
        "invalid": len(records) - valid_count,
        "errors": errors,
    }


# --------------------------------------------------------------------------
# POST /employees/import/confirm — Execute CSV import
# --------------------------------------------------------------------------


@router.post("/import/confirm")
async def import_confirm(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Execute bulk employee import from previously previewed CSV data.

    Creates employee records and sends invitations for valid entries.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    records = body.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No records to import.")

    inviter_id = int(current_user.get("sub", 0))
    created = 0
    skipped = 0
    import_errors = []
    invitations = []

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    for record in records:
        if not record.get("valid", True):
            skipped += 1
            continue

        email = record.get("email", "").strip().lower()
        if not email:
            skipped += 1
            continue

        try:
            # Create invitation (employee will register via invitation link)
            token = str(uuid.uuid4())
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=_INVITATION_EXPIRY_DAYS)
            ).isoformat()

            _create_invitation(
                company_id=company_id,
                inviter_id=inviter_id,
                email=email,
                role="employee",
                token=token,
                expires_at=expires_at,
            )

            created += 1
            invite_url = f"{frontend_url}/signup?token={token}"
            invitations.append({"email": email, "invite_url": invite_url})
        except Exception as exc:
            logger.warning("Import failed for %s: %s", email, exc)
            import_errors.append(
                {"email": email, "error": "Failed to create invitation. Please try again."}
            )
            skipped += 1

    return {
        "message": f"Import complete. {created} invitations sent, {skipped} skipped.",
        "created": created,
        "skipped": skipped,
        "errors": import_errors,
        "invitations": invitations,
    }


# --------------------------------------------------------------------------
# GET /employees/probation/due — Employees nearing probation end
# --------------------------------------------------------------------------


@router.get("/probation/due")
async def get_probation_due(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get employees approaching probation end date (within 30 days)."""
    company_id = get_current_company_id(current_user)
    employees = _list_employees_for_company(company_id)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    thirty_days = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

    due = []
    for emp in employees:
        if emp.get("confirmation_status") != "on_probation":
            continue
        end_date = emp.get("probation_end_date", "")
        if end_date and today <= end_date <= thirty_days:
            user = _find_user_by_id(emp.get("user_id"))
            due.append(
                {
                    "id": emp.get("id"),
                    "name": user.get("name", "") if user else "",
                    "department": emp.get("department", ""),
                    "designation": emp.get("designation", ""),
                    "probation_end_date": end_date,
                    "start_date": emp.get("start_date", ""),
                }
            )

    return {"employees": due, "count": len(due)}


# --------------------------------------------------------------------------
# POST /employees/{id}/confirm — Confirm employee after probation
# --------------------------------------------------------------------------


@router.post("/{employee_id}/confirm")
async def confirm_employee(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Confirm an employee after probation."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    if emp.get("confirmation_status") not in ("on_probation", "extended"):
        raise HTTPException(status_code=400, detail="Employee is not on probation.")

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    actor_id = int(current_user.get("sub", 0))

    _update_employee(employee_id, {"confirmation_status": "confirmed"})
    _create_employment_event(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "event_type": "confirmed",
            "event_date": today,
            "description": "Confirmed after probation",
            "effective_date": today,
            "approved_by": actor_id,
            "notes": body.get("remarks", ""),
        }
    )

    return {"message": "Employee confirmed."}


# --------------------------------------------------------------------------
# POST /employees/{id}/extend-probation — Extend probation period
# --------------------------------------------------------------------------


@router.post("/{employee_id}/extend-probation")
async def extend_probation(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Extend an employee's probation period."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()
    new_end_date = body.get("new_end_date")
    if not new_end_date:
        raise HTTPException(status_code=400, detail="new_end_date is required.")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    actor_id = int(current_user.get("sub", 0))

    _update_employee(
        employee_id,
        {
            "confirmation_status": "extended",
            "probation_end_date": new_end_date,
        },
    )
    _create_employment_event(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "event_type": "confirmed",
            "event_date": today,
            "description": f"Probation extended to {new_end_date}",
            "old_value": {"probation_end_date": emp.get("probation_end_date", "")},
            "new_value": {"probation_end_date": new_end_date},
            "effective_date": today,
            "approved_by": actor_id,
            "notes": body.get("remarks", ""),
        }
    )

    return {"message": f"Probation extended to {new_end_date}."}


# --------------------------------------------------------------------------
# POST /employees/{id}/exit — Process employee exit (resignation/termination)
# --------------------------------------------------------------------------

_VALID_EXIT_TYPES = {"resignation", "termination", "retrenchment", "contract_end"}


@router.post("/{employee_id}/exit")
async def process_employee_exit(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Process employee exit and calculate final settlement.

    Accepts exit_type, last_working_day, reason, notice_served.
    Calculates: pro-rated salary, leave encashment, notice period
    payment/deduction, and retrenchment benefit (if applicable).
    Updates employee status to inactive and creates an EmploymentEvent.
    """
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    if not emp.get("is_active"):
        raise HTTPException(status_code=400, detail="Employee is already inactive.")

    body = await request.json()

    # --- Validate inputs ---
    exit_type = (body.get("exit_type") or "").strip().lower()
    if exit_type not in _VALID_EXIT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"exit_type must be one of: {', '.join(sorted(_VALID_EXIT_TYPES))}",
        )

    last_working_day = (body.get("last_working_day") or "").strip()
    if not last_working_day:
        raise HTTPException(status_code=400, detail="last_working_day is required.")

    # Validate date format
    try:
        lwd = date_type.fromisoformat(last_working_day)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="last_working_day must be in YYYY-MM-DD format.",
        )

    reason = _validate_text_length(
        (body.get("reason") or "").strip(), "reason", MAX_TEXT_LENGTH
    )
    notice_served = bool(body.get("notice_served", False))

    actor_id = int(current_user.get("sub", 0))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    monthly_salary = float(emp.get("salary_monthly") or 0.0)
    if not math.isfinite(monthly_salary) or monthly_salary < 0:
        monthly_salary = 0.0

    notice_period_days = int(emp.get("notice_period_days") or 0)

    # --- 1. Pro-rated salary for partial month ---
    # Calculate the partial month of the last working day
    lwd_month_start = lwd.replace(day=1)
    _, days_in_lwd_month = calendar.monthrange(lwd.year, lwd.month)
    lwd_month_end = lwd.replace(day=days_in_lwd_month)

    from hr_advisory.services.payroll_calculator import prorate_salary

    prorated_salary = prorate_salary(
        monthly_salary,
        emp.get("start_date", ""),
        last_working_day,
        lwd_month_start.isoformat(),
        lwd_month_end.isoformat(),
    )

    # --- 2. Outstanding leave encashment ---
    # Get unused annual leave and calculate encashment at daily rate
    leave_balances = _get_leave_balances(employee_id, company_id)
    annual_balance = None
    for bal in leave_balances:
        lt = (bal.get("leave_type") or "").lower()
        if lt == "annual":
            annual_balance = bal
            break

    unused_leave_days = 0.0
    if annual_balance:
        entitlement = float(annual_balance.get("entitlement_days") or 0.0)
        used = float(annual_balance.get("used_days") or 0.0)
        pending = float(annual_balance.get("pending_days") or 0.0)
        unused_leave_days = max(0.0, entitlement - used - pending)

    # Daily rate = monthly salary / 26 (Singapore norm for working days)
    daily_rate = monthly_salary / 26.0 if monthly_salary > 0 else 0.0
    leave_encashment = round(unused_leave_days * daily_rate, 2)

    # --- 3. Notice period payment/deduction ---
    notice_payment = 0.0
    notice_shortfall_days = 0

    if notice_period_days > 0 and not notice_served:
        # Calculate days between today and last working day
        today_date = datetime.now(timezone.utc).date()
        days_given = max(0, (lwd - today_date).days)
        notice_shortfall_days = max(0, notice_period_days - days_given)

        if notice_shortfall_days > 0:
            if exit_type == "resignation":
                # Employee owes company for shortfall (deduction)
                notice_payment = -round(daily_rate * notice_shortfall_days, 2)
            elif exit_type in ("termination", "retrenchment"):
                # Company owes employee salary in lieu of notice
                notice_payment = round(daily_rate * notice_shortfall_days, 2)

    # --- 4. Retrenchment benefit (if applicable) ---
    retrenchment_benefit = 0.0
    retrenchment_explanation = ""

    if exit_type == "retrenchment":
        # Calculate years of service
        start_date_str = emp.get("start_date", "")
        years_of_service = 0.0
        if start_date_str:
            try:
                start_dt = date_type.fromisoformat(start_date_str)
                service_days = (lwd - start_dt).days
                years_of_service = max(0.0, service_days / 365.25)
            except (ValueError, TypeError):
                years_of_service = 0.0

        # Use the existing retrenchment calculator
        from hr_advisory.workflows.calculators.retrenchment_calculator import (
            calculate_retrenchment,
            RetrenchmentInput,
        )

        company_record = None
        try:
            from kailash.runtime import LocalRuntime
            from kailash.workflow.builder import WorkflowBuilder

            import hr_advisory.models  # noqa: F401

            wf = WorkflowBuilder()
            wf.add_node("CompanyReadNode", "read_company", {"id": company_id})
            runtime = LocalRuntime()
            results, _ = runtime.execute(wf.build())
            company_record = results.get("read_company", {})
        except Exception:
            logger.debug("Could not read company record for sector lookup")

        sector = (company_record or {}).get("sector", "") or ""

        retrench_result = calculate_retrenchment(
            RetrenchmentInput(
                years_of_service=years_of_service,
                monthly_salary=monthly_salary,
                sector=sector,
            )
        )
        retrenchment_benefit = retrench_result.market_norm_total
        retrenchment_explanation = retrench_result.explanation

    # --- 5. Calculate total settlement ---
    total_settlement = round(
        prorated_salary + leave_encashment + notice_payment + retrenchment_benefit, 2
    )

    # --- 6. Update employee record ---
    _update_employee(
        employee_id,
        {
            "is_active": False,
            "end_date": last_working_day,
            "confirmation_status": "terminated",
        },
    )

    # --- 7. Create EmploymentEvent ---
    event_type_map = {
        "resignation": "resigned",
        "termination": "terminated",
        "retrenchment": "retrenched",
        "contract_end": "terminated",
    }
    _create_employment_event(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "event_type": event_type_map.get(exit_type, "terminated"),
            "event_date": today,
            "description": f"Exit processed: {exit_type.replace('_', ' ').title()}",
            "effective_date": last_working_day,
            "approved_by": actor_id,
            "notes": reason,
            "new_value": {
                "exit_type": exit_type,
                "last_working_day": last_working_day,
                "notice_served": notice_served,
                "total_settlement": total_settlement,
            },
        }
    )

    # --- 8. Build settlement breakdown ---
    settlement = {
        "employee_id": employee_id,
        "exit_type": exit_type,
        "last_working_day": last_working_day,
        "notice_served": notice_served,
        "breakdown": {
            "prorated_salary": prorated_salary,
            "leave_encashment": {
                "unused_days": unused_leave_days,
                "daily_rate": round(daily_rate, 2),
                "amount": leave_encashment,
            },
            "notice_period": {
                "notice_period_days": notice_period_days,
                "shortfall_days": notice_shortfall_days,
                "amount": notice_payment,
                "note": (
                    "Employee owes company (salary in lieu of notice)"
                    if notice_payment < 0
                    else (
                        "Company owes employee (salary in lieu of notice)"
                        if notice_payment > 0
                        else "Notice fully served or not applicable"
                    )
                ),
            },
            "retrenchment_benefit": {
                "amount": retrenchment_benefit,
                "explanation": retrenchment_explanation,
            }
            if exit_type == "retrenchment"
            else None,
        },
        "total_settlement": total_settlement,
        "message": f"Exit processed for employee. Total settlement: ${total_settlement:,.2f}",
    }

    return settlement


# ==========================================================================
# Family Member CRUD
# ==========================================================================


# --------------------------------------------------------------------------
# GET /employees/{id}/family-members — List family members
# --------------------------------------------------------------------------


@router.get("/{employee_id}/family-members")
async def list_family_members(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List family members for an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    members = _list_family_members(employee_id)

    # Decrypt/mask NRIC for display
    actor_id = int(current_user.get("sub", 0))
    has_nric = False
    for member in members:
        raw_nric = decrypt_field(member.get("nric_fin", ""))
        if raw_nric:
            has_nric = True
            member["nric_fin"] = mask_nric(raw_nric)

    # PDPA audit if sensitive data accessed
    if has_nric:
        _log_pdpa_access(
            accessed_by=actor_id,
            company_id=company_id,
            data_subject_id=employee_id,
            categories=["family_nric"],
            action="view_family_members",
        )

    return {"family_members": members, "count": len(members)}


# --------------------------------------------------------------------------
# POST /employees/{id}/family-members — Add family member
# --------------------------------------------------------------------------


@router.post("/{employee_id}/family-members")
async def create_family_member_endpoint(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a family member to an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()

    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'name' is required.")
    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    relationship = body.get("relationship", "").strip()
    valid_relationships = ("spouse", "child", "parent")
    if relationship not in valid_relationships:
        raise HTTPException(
            status_code=400,
            detail=f"relationship must be one of: {', '.join(valid_relationships)}.",
        )

    citizenship_status = body.get("citizenship_status", "").strip()
    if citizenship_status:
        valid_citizenship = ("citizen", "pr", "foreigner")
        if citizenship_status not in valid_citizenship:
            raise HTTPException(
                status_code=400,
                detail=f"citizenship_status must be one of: {', '.join(valid_citizenship)}.",
            )

    gender = body.get("gender", "").strip()
    if gender:
        valid_genders = ("male", "female")
        if gender not in valid_genders:
            raise HTTPException(
                status_code=400,
                detail=f"gender must be one of: {', '.join(valid_genders)}.",
            )

    # Encrypt NRIC if provided
    nric_fin = body.get("nric_fin", "").strip()
    encrypted_nric = encrypt_field(nric_fin) if nric_fin else ""

    member = _create_family_member(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "name": name,
            "relationship": relationship,
            "date_of_birth": body.get("date_of_birth", ""),
            "gender": gender,
            "citizenship_status": citizenship_status,
            "nric_fin": encrypted_nric,
        }
    )

    # PDPA audit for NRIC write
    if nric_fin:
        actor_id = int(current_user.get("sub", 0))
        _log_pdpa_access(
            accessed_by=actor_id,
            company_id=company_id,
            data_subject_id=employee_id,
            categories=["family_nric"],
            action="create_family_member",
        )

    # Timeline event
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    actor_id = int(current_user.get("sub", 0))
    try:
        _create_employee_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "family_member_added",
                "description": f"Family member added: {name} ({relationship})",
                "changed_by": actor_id,
                "new_value": json.dumps({"name": name, "relationship": relationship}),
                "event_date": today,
            }
        )
    except Exception:
        logger.exception("Failed to create timeline event for family member addition")

    # Mask NRIC in response
    if member.get("nric_fin"):
        raw = decrypt_field(member["nric_fin"])
        member["nric_fin"] = mask_nric(raw)

    return {"family_member": member}


# --------------------------------------------------------------------------
# PATCH /employees/{id}/family-members/{member_id} — Update family member
# --------------------------------------------------------------------------


@router.patch("/{employee_id}/family-members/{member_id}")
async def update_family_member_endpoint(
    employee_id: int,
    member_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a family member."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _read_family_member(member_id)
    if existing is None or existing.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    body = await request.json()
    allowed_fields = {
        "name",
        "relationship",
        "date_of_birth",
        "gender",
        "citizenship_status",
        "nric_fin",
    }
    updates: dict = {}
    for key in allowed_fields:
        if key in body:
            updates[key] = body[key]

    if "name" in updates:
        _validate_text_length(updates["name"], "name", MAX_NAME_LENGTH)
    if "relationship" in updates:
        valid_relationships = ("spouse", "child", "parent")
        if updates["relationship"] not in valid_relationships:
            raise HTTPException(
                status_code=400,
                detail=f"relationship must be one of: {', '.join(valid_relationships)}.",
            )
    if "citizenship_status" in updates and updates["citizenship_status"]:
        valid_citizenship = ("citizen", "pr", "foreigner")
        if updates["citizenship_status"] not in valid_citizenship:
            raise HTTPException(
                status_code=400,
                detail=f"citizenship_status must be one of: {', '.join(valid_citizenship)}.",
            )
    if "gender" in updates and updates["gender"]:
        valid_genders = ("male", "female")
        if updates["gender"] not in valid_genders:
            raise HTTPException(
                status_code=400,
                detail=f"gender must be one of: {', '.join(valid_genders)}.",
            )

    # Encrypt NRIC if being updated
    if "nric_fin" in updates:
        nric_raw = updates["nric_fin"].strip()
        updates["nric_fin"] = encrypt_field(nric_raw) if nric_raw else ""
        actor_id = int(current_user.get("sub", 0))
        _log_pdpa_access(
            accessed_by=actor_id,
            company_id=company_id,
            data_subject_id=employee_id,
            categories=["family_nric"],
            action="update_family_member",
        )

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = _update_family_member(member_id, updates)

    # Mask NRIC in response
    if result.get("nric_fin"):
        raw = decrypt_field(result["nric_fin"])
        result["nric_fin"] = mask_nric(raw)

    return {"family_member": result}


# --------------------------------------------------------------------------
# DELETE /employees/{id}/family-members/{member_id} — Delete family member
# --------------------------------------------------------------------------


@router.delete("/{employee_id}/family-members/{member_id}")
async def delete_family_member_endpoint(
    employee_id: int,
    member_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a family member (soft-delete by clearing name)."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _read_family_member(member_id)
    if existing is None or existing.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    # Soft-delete: clear PII and mark as deleted
    _update_family_member(
        member_id,
        {"name": "__deleted__", "nric_fin": "", "date_of_birth": ""},
    )

    # Timeline event
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    actor_id = int(current_user.get("sub", 0))
    try:
        _create_employee_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "family_member_removed",
                "description": f"Family member removed: {existing.get('name', '')} ({existing.get('relationship', '')})",
                "changed_by": actor_id,
                "old_value": json.dumps(
                    {
                        "name": existing.get("name", ""),
                        "relationship": existing.get("relationship", ""),
                    }
                ),
                "event_date": today,
            }
        )
    except Exception:
        logger.exception("Failed to create timeline event for family member removal")

    return {"message": "Family member deleted."}


# ==========================================================================
# Employee Note CRUD
# ==========================================================================


# --------------------------------------------------------------------------
# GET /employees/{id}/notes — List notes
# --------------------------------------------------------------------------


@router.get("/{employee_id}/notes")
async def list_employee_notes_endpoint(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List notes for an employee.

    Confidential notes are only visible to owners and the note creator.
    """
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    notes = _list_employee_notes(employee_id)
    actor_id = int(current_user.get("sub", 0))
    user_role = current_user.get("role", "")

    # Filter confidential notes: only owner or the note creator can see them
    visible_notes = []
    for note in notes:
        if note.get("is_confidential") and user_role != "owner":
            if note.get("created_by") != actor_id:
                continue
        visible_notes.append(note)

    # Sort by created_at descending
    visible_notes.sort(key=lambda n: n.get("created_at", ""), reverse=True)

    return {"notes": visible_notes, "count": len(visible_notes)}


# --------------------------------------------------------------------------
# POST /employees/{id}/notes — Add note
# --------------------------------------------------------------------------


@router.post("/{employee_id}/notes")
async def create_employee_note_endpoint(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a note to an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()

    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="'content' is required.")
    _validate_text_length(content, "content", MAX_TEXT_LENGTH)

    note_type = body.get("note_type", "general").strip()
    valid_types = ("general", "performance", "disciplinary", "confidential")
    if note_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"note_type must be one of: {', '.join(valid_types)}.",
        )

    is_confidential = bool(body.get("is_confidential", False))
    # Confidential type implies confidential flag
    if note_type == "confidential":
        is_confidential = True

    actor_id = int(current_user.get("sub", 0))
    note = _create_employee_note(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "note_type": note_type,
            "content": content,
            "created_by": actor_id,
            "is_confidential": is_confidential,
        }
    )

    # Timeline event
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        _create_employee_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "note_added",
                "description": f"Note added ({note_type})",
                "changed_by": actor_id,
                "event_date": today,
            }
        )
    except Exception:
        logger.exception("Failed to create timeline event for note addition")

    return {"note": note}


# --------------------------------------------------------------------------
# PATCH /employees/{id}/notes/{note_id} — Update note
# --------------------------------------------------------------------------


@router.patch("/{employee_id}/notes/{note_id}")
async def update_employee_note_endpoint(
    employee_id: int,
    note_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a note on an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _read_employee_note(note_id)
    if existing is None or existing.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Note not found.")

    # Only the creator or an owner can update a note
    actor_id = int(current_user.get("sub", 0))
    user_role = current_user.get("role", "")
    if existing.get("created_by") != actor_id and user_role != "owner":
        raise HTTPException(status_code=403, detail="You can only edit your own notes.")

    body = await request.json()
    allowed_fields = {"content", "note_type", "is_confidential"}
    updates: dict = {}
    for key in allowed_fields:
        if key in body:
            updates[key] = body[key]

    if "content" in updates:
        _validate_text_length(updates["content"], "content", MAX_TEXT_LENGTH)
    if "note_type" in updates:
        valid_types = ("general", "performance", "disciplinary", "confidential")
        if updates["note_type"] not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"note_type must be one of: {', '.join(valid_types)}.",
            )
        if updates["note_type"] == "confidential":
            updates["is_confidential"] = True

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = _update_employee_note(note_id, updates)
    return {"note": result}


# --------------------------------------------------------------------------
# DELETE /employees/{id}/notes/{note_id} — Delete note
# --------------------------------------------------------------------------


@router.delete("/{employee_id}/notes/{note_id}")
async def delete_employee_note_endpoint(
    employee_id: int,
    note_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a note on an employee (soft-delete by clearing content)."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _read_employee_note(note_id)
    if existing is None or existing.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Note not found.")

    # Only the creator or an owner can delete a note
    actor_id = int(current_user.get("sub", 0))
    user_role = current_user.get("role", "")
    if existing.get("created_by") != actor_id and user_role != "owner":
        raise HTTPException(status_code=403, detail="You can only delete your own notes.")

    _update_employee_note(note_id, {"content": "__deleted__", "note_type": "general"})
    return {"message": "Note deleted."}


# ==========================================================================
# Employee Skill CRUD
# ==========================================================================


# --------------------------------------------------------------------------
# GET /employees/{id}/skills — List skills/certifications
# --------------------------------------------------------------------------


@router.get("/{employee_id}/skills")
async def list_employee_skills_endpoint(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List skills and certifications for an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    skills = _list_employee_skills(employee_id)
    return {"skills": skills, "count": len(skills)}


# --------------------------------------------------------------------------
# POST /employees/{id}/skills — Add skill
# --------------------------------------------------------------------------


@router.post("/{employee_id}/skills")
async def create_employee_skill_endpoint(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a skill or certification to an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()

    skill_name = body.get("skill_name", "").strip()
    if not skill_name:
        raise HTTPException(status_code=400, detail="'skill_name' is required.")
    _validate_text_length(skill_name, "skill_name", MAX_NAME_LENGTH)

    proficiency_level = body.get("proficiency_level", "").strip()
    if proficiency_level:
        valid_levels = ("basic", "intermediate", "advanced", "expert")
        if proficiency_level not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"proficiency_level must be one of: {', '.join(valid_levels)}.",
            )

    certification_name = body.get("certification_name", "").strip()
    if certification_name:
        _validate_text_length(certification_name, "certification_name", MAX_NAME_LENGTH)

    issuing_body = body.get("issuing_body", "").strip()
    if issuing_body:
        _validate_text_length(issuing_body, "issuing_body", MAX_NAME_LENGTH)

    skill = _create_employee_skill(
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "skill_name": skill_name,
            "proficiency_level": proficiency_level,
            "certification_name": certification_name,
            "certification_number": body.get("certification_number", "").strip(),
            "certified_date": body.get("certified_date", ""),
            "expiry_date": body.get("expiry_date", ""),
            "issuing_body": issuing_body,
        }
    )

    # Timeline event
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    actor_id = int(current_user.get("sub", 0))
    try:
        _create_employee_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "skill_added",
                "description": f"Skill added: {skill_name}",
                "changed_by": actor_id,
                "new_value": json.dumps(
                    {"skill_name": skill_name, "certification_name": certification_name}
                ),
                "event_date": today,
            }
        )
    except Exception:
        logger.exception("Failed to create timeline event for skill addition")

    return {"skill": skill}


# --------------------------------------------------------------------------
# PATCH /employees/{id}/skills/{skill_id} — Update skill
# --------------------------------------------------------------------------


@router.patch("/{employee_id}/skills/{skill_id}")
async def update_employee_skill_endpoint(
    employee_id: int,
    skill_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a skill or certification."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _read_employee_skill(skill_id)
    if existing is None or existing.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Skill not found.")

    body = await request.json()
    allowed_fields = {
        "skill_name",
        "proficiency_level",
        "certification_name",
        "certification_number",
        "certified_date",
        "expiry_date",
        "issuing_body",
    }
    updates: dict = {}
    for key in allowed_fields:
        if key in body:
            updates[key] = body[key]

    if "skill_name" in updates:
        _validate_text_length(updates["skill_name"], "skill_name", MAX_NAME_LENGTH)
    if "proficiency_level" in updates and updates["proficiency_level"]:
        valid_levels = ("basic", "intermediate", "advanced", "expert")
        if updates["proficiency_level"] not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"proficiency_level must be one of: {', '.join(valid_levels)}.",
            )
    if "certification_name" in updates:
        _validate_text_length(updates["certification_name"], "certification_name", MAX_NAME_LENGTH)
    if "issuing_body" in updates:
        _validate_text_length(updates["issuing_body"], "issuing_body", MAX_NAME_LENGTH)

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = _update_employee_skill(skill_id, updates)
    return {"skill": result}


# --------------------------------------------------------------------------
# DELETE /employees/{id}/skills/{skill_id} — Delete skill
# --------------------------------------------------------------------------


@router.delete("/{employee_id}/skills/{skill_id}")
async def delete_employee_skill_endpoint(
    employee_id: int,
    skill_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a skill or certification (soft-delete by clearing name)."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _read_employee_skill(skill_id)
    if existing is None or existing.get("employee_id") != employee_id:
        raise HTTPException(status_code=404, detail="Skill not found.")

    _update_employee_skill(skill_id, {"skill_name": "__deleted__"})

    # Timeline event
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    actor_id = int(current_user.get("sub", 0))
    try:
        _create_employee_event(
            {
                "employee_id": employee_id,
                "company_id": company_id,
                "event_type": "skill_removed",
                "description": f"Skill removed: {existing.get('skill_name', '')}",
                "changed_by": actor_id,
                "old_value": json.dumps({"skill_name": existing.get("skill_name", "")}),
                "event_date": today,
            }
        )
    except Exception:
        logger.exception("Failed to create timeline event for skill removal")

    return {"message": "Skill deleted."}


# ==========================================================================
# Custom Field Value CRUD (per-entity)
# ==========================================================================


# --------------------------------------------------------------------------
# GET /employees/{id}/custom-field-values — List values for employee
# --------------------------------------------------------------------------


@router.get("/{employee_id}/custom-field-values")
async def list_custom_field_values_endpoint(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List custom field values for an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    values = _list_custom_field_values("employee", employee_id, company_id)
    return {"values": values, "count": len(values)}


# --------------------------------------------------------------------------
# POST /employees/{id}/custom-field-values — Set value
# --------------------------------------------------------------------------


@router.post("/{employee_id}/custom-field-values")
async def create_custom_field_value_endpoint(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Set a custom field value for an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    body = await request.json()

    field_definition_id = body.get("field_definition_id")
    if not field_definition_id:
        raise HTTPException(status_code=400, detail="'field_definition_id' is required.")

    # Validate the field definition exists and belongs to this company
    definition = _read_custom_field_definition(int(field_definition_id))
    if definition is None or definition.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Custom field definition not found.")

    value = body.get("value", "")
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    _validate_text_length(str(value), "value", MAX_TEXT_LENGTH)

    # Check if a value already exists for this entity+field — if so, update it
    existing_values = _list_custom_field_values("employee", employee_id, company_id)
    existing_match = None
    for v in existing_values:
        if v.get("field_definition_id") == int(field_definition_id):
            existing_match = v
            break

    if existing_match:
        result = _update_custom_field_value(existing_match["id"], {"value": str(value)})
        return {"value": result, "updated": True}

    result = _create_custom_field_value(
        {
            "entity_type": "employee",
            "entity_id": employee_id,
            "field_definition_id": int(field_definition_id),
            "company_id": company_id,
            "value": str(value),
        }
    )
    return {"value": result, "updated": False}


# --------------------------------------------------------------------------
# PATCH /employees/{id}/custom-field-values/{value_id} — Update value
# --------------------------------------------------------------------------


@router.patch("/{employee_id}/custom-field-values/{value_id}")
async def update_custom_field_value_endpoint(
    employee_id: int,
    value_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a custom field value for an employee."""
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    existing = _read_custom_field_value(value_id)
    if existing is None or existing.get("entity_id") != employee_id:
        raise HTTPException(status_code=404, detail="Custom field value not found.")
    if existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Custom field value not found.")

    body = await request.json()
    value = body.get("value", "")
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    _validate_text_length(str(value), "value", MAX_TEXT_LENGTH)

    result = _update_custom_field_value(value_id, {"value": str(value)})
    return {"value": result}


# ==========================================================================
# Admin Leave Balances for specific employee
# ==========================================================================


# --------------------------------------------------------------------------
# GET /employees/{id}/leave-balances — Admin view of employee leave balances
# --------------------------------------------------------------------------


@router.get("/{employee_id}/leave-balances")
async def get_employee_leave_balances(
    employee_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get leave balances for a specific employee (admin only).

    Returns the employee's leave balances for the current year,
    falling back to statutory defaults if no balances have been recorded.
    """
    company_id = get_current_company_id(current_user)
    emp = _find_employee_by_id(employee_id)
    if emp is None or emp.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Try to ensure leave balances exist via the leave engine
    try:
        from hr_advisory.services.leave_engine import ensure_leave_balances

        ensure_leave_balances(employee_id, company_id)
    except Exception:
        logger.debug("Leave engine not available, falling back to direct query")

    balances = _get_leave_balances(employee_id, company_id)

    if not balances:
        balances = _statutory_defaults()

    return {
        "employee_id": employee_id,
        "balances": balances,
        "count": len(balances),
    }
