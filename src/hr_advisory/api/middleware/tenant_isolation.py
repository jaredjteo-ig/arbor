"""Tenant isolation middleware for company-scoped data access.

Ensures users can only access data belonging to their own company,
with platform_admin having cross-company access.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_current_company_id(current_user: dict) -> Optional[int]:
    """Extract company_id from the decoded JWT payload.

    Returns:
        The company_id as an integer, or None for platform_admin users
        (who can access any company's data).

    Raises:
        HTTPException(403): If non-admin user has no company_id.
    """
    role = current_user.get("role", "")

    # Platform admins can access all companies
    if role == "platform_admin":
        return current_user.get("company_id")  # May be None — that's fine

    company_id = current_user.get("company_id")
    if company_id is None:
        raise HTTPException(
            status_code=403,
            detail="No company associated with this account. Contact support.",
        )

    return company_id


def validate_company_access(
    current_user: dict,
    requested_company_id: Optional[int],
) -> None:
    """Validate that the user can access data for the requested company.

    Args:
        current_user: The decoded JWT payload (from get_current_user).
        requested_company_id: The company_id being accessed. None means
            no specific company is being targeted (e.g., user's own data).

    Raises:
        HTTPException(403): If the user is not authorized for the requested company.
    """
    # No specific company requested — allow
    if requested_company_id is None:
        return

    role = current_user.get("role", "")

    # Platform admins can access any company
    if role == "platform_admin":
        return

    user_company_id = current_user.get("company_id")

    # User has no company — deny access to any specific company
    if user_company_id is None:
        logger.warning(
            "Tenant isolation: user %s (no company) tried to access company %s",
            current_user.get("sub"),
            requested_company_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this resource.",
        )

    # User's company must match the requested company
    if user_company_id != requested_company_id:
        logger.warning(
            "Tenant isolation: user %s (company %s) tried to access company %s",
            current_user.get("sub"),
            user_company_id,
            requested_company_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this resource.",
        )
