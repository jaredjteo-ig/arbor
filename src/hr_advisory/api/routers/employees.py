"""Employee management endpoints.

Handles employee invitations, listing, self-service access, salary components,
emergency contacts, employment history, and document management.
Admins (owner, hr_manager) can invite employees and view the full roster.
Employees can view their own record via /employees/me.
"""

import csv
import io
import json
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
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
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node("UserReadNode", "read", {"id": user_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


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
        "date_of_birth": emp.get("date_of_birth", ""),
        "gender": emp.get("gender", ""),
        "marital_status": emp.get("marital_status", ""),
        "race": emp.get("race", ""),
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
        # Address
        "residential_address": emp.get("residential_address", ""),
        "postal_code": emp.get("postal_code", ""),
        # Organisational
        "reporting_manager_id": emp.get("reporting_manager_id"),
        # Probation
        "probation_months": emp.get("probation_months", 3),
        "probation_end_date": emp.get("probation_end_date", ""),
        "confirmation_status": emp.get("confirmation_status", "on_probation"),
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

    # Enrich with user details
    enriched = []
    for emp in employees:
        user = _find_user_by_id(emp.get("user_id"))
        enriched.append(_serialize_employee(emp, user))

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

    Status codes:
        200: Success
        404: No employee record found
    """
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    if company_id is None:
        raise HTTPException(
            status_code=404,
            detail="No employee record found.",
        )

    employee = _find_employee_by_user_id(user_id, company_id)
    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="No employee record found.",
        )

    user = _find_user_by_id(user_id)
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
        {"conditions": {"id": employee["id"]}, "updates": updates},
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
# --------------------------------------------------------------------------


@router.get("/policies")
async def list_policies(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List company policies for the current user's company.

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
    records = []
    errors = []

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
            "date_of_birth": row.get("date_of_birth", "").strip(),
            "nric_fin": row.get("nric_fin", "").strip(),
            "bank_name": row.get("bank_name", "").strip(),
            "bank_account_number": row.get("bank_account_number", "").strip(),
            "start_date": row.get("start_date", "").strip(),
            "work_pass_number": row.get("work_pass_number", "").strip(),
            "work_pass_expiry": row.get("work_pass_expiry", "").strip(),
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
