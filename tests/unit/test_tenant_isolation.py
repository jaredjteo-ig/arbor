"""Unit tests for tenant isolation middleware and dependencies.

Tests the core tenant isolation logic without any external services:
1. get_current_company_id extracts company_id from JWT payload
2. require_company_access validates user can only access their own company data
3. Admin/platform_admin roles can access any company
4. Missing company_id in token raises clear error
5. Mismatched company_id raises 403
"""

import pytest
from fastapi import HTTPException

from hr_advisory.api.middleware.tenant_isolation import (
    get_current_company_id,
    validate_company_access,
)


# ---------------------------------------------------------------------------
# 1. get_current_company_id
# ---------------------------------------------------------------------------


class TestGetCurrentCompanyId:
    """Extract company_id from the decoded JWT payload."""

    def test_extracts_company_id_from_payload(self):
        """A payload with company_id returns the integer company_id."""
        payload = {"sub": 1, "email": "a@b.com", "role": "owner", "company_id": 42}
        assert get_current_company_id(payload) == 42

    def test_missing_company_id_raises_403(self):
        """A payload without company_id raises HTTPException 403."""
        payload = {"sub": 1, "email": "a@b.com", "role": "owner"}
        with pytest.raises(HTTPException) as exc_info:
            get_current_company_id(payload)
        assert exc_info.value.status_code == 403
        assert "company" in exc_info.value.detail.lower()

    def test_none_company_id_raises_403(self):
        """A payload with company_id=None raises HTTPException 403."""
        payload = {"sub": 1, "email": "a@b.com", "role": "owner", "company_id": None}
        with pytest.raises(HTTPException) as exc_info:
            get_current_company_id(payload)
        assert exc_info.value.status_code == 403

    def test_platform_admin_without_company_id_returns_none(self):
        """platform_admin role without company_id returns None (can access all)."""
        payload = {"sub": 1, "email": "admin@platform.com", "role": "platform_admin"}
        result = get_current_company_id(payload)
        assert result is None


# ---------------------------------------------------------------------------
# 2. validate_company_access
# ---------------------------------------------------------------------------


class TestValidateCompanyAccess:
    """Validate that the user can access data for the requested company_id."""

    def test_matching_company_id_passes(self):
        """User accessing their own company data is allowed."""
        user = {"sub": 1, "email": "a@b.com", "role": "owner", "company_id": 10}
        # Should not raise
        validate_company_access(user, requested_company_id=10)

    def test_mismatched_company_id_raises_403(self):
        """User accessing another company's data raises 403."""
        user = {"sub": 1, "email": "a@b.com", "role": "owner", "company_id": 10}
        with pytest.raises(HTTPException) as exc_info:
            validate_company_access(user, requested_company_id=20)
        assert exc_info.value.status_code == 403
        assert (
            "not authorized" in exc_info.value.detail.lower()
            or "access" in exc_info.value.detail.lower()
        )

    def test_platform_admin_can_access_any_company(self):
        """platform_admin role can access any company's data."""
        user = {"sub": 1, "email": "admin@platform.com", "role": "platform_admin"}
        # Should not raise for any company_id
        validate_company_access(user, requested_company_id=10)
        validate_company_access(user, requested_company_id=20)
        validate_company_access(user, requested_company_id=999)

    def test_none_requested_company_id_passes(self):
        """When no company_id is requested (None), access is allowed."""
        user = {"sub": 1, "email": "a@b.com", "role": "owner", "company_id": 10}
        # Should not raise -- no specific company data requested
        validate_company_access(user, requested_company_id=None)

    def test_user_without_company_id_denied_specific_company(self):
        """A user without a company_id in their token cannot access any specific company."""
        user = {"sub": 1, "email": "a@b.com", "role": "owner"}
        with pytest.raises(HTTPException) as exc_info:
            validate_company_access(user, requested_company_id=10)
        assert exc_info.value.status_code == 403

    def test_user_with_none_company_id_denied_specific_company(self):
        """A user with company_id=None in their token cannot access any specific company."""
        user = {"sub": 1, "email": "a@b.com", "role": "owner", "company_id": None}
        with pytest.raises(HTTPException) as exc_info:
            validate_company_access(user, requested_company_id=10)
        assert exc_info.value.status_code == 403

    def test_error_message_is_generic(self):
        """The 403 error message must NOT leak the requested company ID."""
        user = {"sub": 5, "email": "a@b.com", "role": "owner", "company_id": 10}
        with pytest.raises(HTTPException) as exc_info:
            validate_company_access(user, requested_company_id=20)
        detail = exc_info.value.detail
        # Should be a generic authorization message
        assert "not authorized" in detail.lower()
        # Must NOT include the requested company ID (information disclosure)
        assert "20" not in detail
