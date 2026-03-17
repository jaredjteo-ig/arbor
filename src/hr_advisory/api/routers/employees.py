"""Employee management endpoints.

Handles employee invitations, listing, and self-service access.
Admins (owner, hr_manager) can invite employees and view the full roster.
Employees can view their own record via /employees/me.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import (
    get_current_company_id,
    validate_company_access,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Invitation validity period
_INVITATION_EXPIRY_DAYS = 7


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

    # Token is NOT included in the response — it should only be delivered
    # via a secure side-channel (email to the invitee). Exposing it in the
    # API response risks interception via proxies, logs, or browser devtools.
    return {
        "message": "Invitation sent successfully.",
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

    return {
        "valid": True,
        "email": invitation.get("email"),
        "role": invitation.get("role"),
        "company_id": invitation.get("company_id"),
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
        enriched.append(
            {
                "id": emp.get("id"),
                "user_id": emp.get("user_id"),
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
                "is_active": emp.get("is_active", True),
            }
        )

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

    return {
        "id": employee.get("id"),
        "user_id": employee.get("user_id"),
        "company_id": employee.get("company_id"),
        "employee_id_internal": employee.get("employee_id_internal", ""),
        "department": employee.get("department", ""),
        "designation": employee.get("designation", ""),
        "employment_type": employee.get("employment_type", ""),
        "start_date": employee.get("start_date", ""),
        "end_date": employee.get("end_date", ""),
        "nationality": employee.get("nationality", ""),
        "pass_type": employee.get("pass_type", ""),
        "salary_monthly": employee.get("salary_monthly", 0.0),
        "notice_period_days": employee.get("notice_period_days", 0),
        "is_active": employee.get("is_active", True),
    }
