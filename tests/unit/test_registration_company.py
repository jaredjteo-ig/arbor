"""Unit tests for atomic User + Company creation during owner registration.

Verifies that register_user() with a company_name parameter creates both a
User AND a Company in one call, returning a user dict with a non-null
company_id so the JWT includes it.

Also verifies backward compatibility: registering without company_name
still works exactly as before.

Tier 1 (Unit): Fast, isolated, mocks DataFlow workflow execution.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hr_advisory.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    *,
    id: int = 1,
    email: str = "owner@example.com",
    name: str = "Owner",
    role: str = "owner",
    company_id: int | None = None,
    password_hash: str = "$2b$12$fakehash",
    is_active: bool = True,
) -> dict:
    return {
        "id": id,
        "email": email,
        "name": name,
        "role": role,
        "company_id": company_id,
        "password_hash": password_hash,
        "is_active": is_active,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegisterUserWithCompanyName:
    """register_user(company_name=...) creates both User and Company."""

    @patch.object(AuthService, "_find_user_by_id")
    @patch.object(AuthService, "_create_company_for_registration")
    @patch.object(AuthService, "_find_user_by_email")
    @patch.object(AuthService, "_create_user")
    def test_creates_company_and_links_to_user(
        self,
        mock_create_user: MagicMock,
        mock_find_by_email: MagicMock,
        mock_create_company: MagicMock,
        mock_find_by_id: MagicMock,
    ) -> None:
        """When company_name is provided and company_id is None, a Company is
        created, the user is updated with the new company_id, and the returned
        user dict has that company_id."""
        user_without_company = _make_user(company_id=None)
        user_with_company = _make_user(company_id=42)

        # _find_user_by_email returns None (no duplicate)
        mock_find_by_email.return_value = None

        # _create_user returns user without company_id initially
        mock_create_user.return_value = user_without_company

        # _create_company_for_registration succeeds and returns company_id=42
        mock_create_company.return_value = 42

        # _find_user_by_id re-fetches the user with company_id set
        mock_find_by_id.return_value = user_with_company

        auth = AuthService()
        result = auth.register_user(
            email="owner@example.com",
            password="securepassword123",
            name="Owner",
            company_name="Test Co",
        )

        # The returned user MUST have a non-null company_id
        assert result["user"]["company_id"] == 42
        assert result["user"]["email"] == "owner@example.com"
        assert result["access_token"]
        assert result["refresh_token"]

        # _create_company_for_registration must have been called with
        # the company name and user id
        mock_create_company.assert_called_once_with("Test Co", 1)

    @patch.object(AuthService, "_find_user_by_email")
    @patch.object(AuthService, "_create_user")
    def test_register_without_company_name_backward_compatible(
        self,
        mock_create_user: MagicMock,
        mock_find_by_email: MagicMock,
    ) -> None:
        """Registering without company_name still works exactly as before --
        no Company is created, user has company_id=None."""
        user = _make_user(company_id=None)

        mock_find_by_email.return_value = None
        mock_create_user.return_value = user

        auth = AuthService()
        result = auth.register_user(
            email="owner@example.com",
            password="securepassword123",
            name="Owner",
        )

        assert result["user"]["company_id"] is None
        assert result["user"]["email"] == "owner@example.com"
        assert result["access_token"]
        assert result["refresh_token"]

    @patch.object(AuthService, "_find_user_by_email")
    @patch.object(AuthService, "_create_user")
    def test_register_with_existing_company_id_skips_creation(
        self,
        mock_create_user: MagicMock,
        mock_find_by_email: MagicMock,
    ) -> None:
        """When company_id is already provided, company_name is ignored and
        no new company is created."""
        user = _make_user(company_id=99)

        mock_find_by_email.return_value = None
        mock_create_user.return_value = user

        auth = AuthService()
        result = auth.register_user(
            email="owner@example.com",
            password="securepassword123",
            name="Owner",
            company_id=99,
            company_name="Ignored Co",
        )

        # company_id is the one passed in, not a newly created one
        assert result["user"]["company_id"] == 99

    @patch.object(AuthService, "_create_company_for_registration")
    @patch.object(AuthService, "_find_user_by_email")
    @patch.object(AuthService, "_create_user")
    def test_company_creation_failure_does_not_block_registration(
        self,
        mock_create_user: MagicMock,
        mock_find_by_email: MagicMock,
        mock_create_company: MagicMock,
    ) -> None:
        """If company creation fails (returns None), the user is still
        registered without a company. The failure is logged, not raised."""
        user = _make_user(company_id=None)

        mock_find_by_email.return_value = None
        mock_create_user.return_value = user

        # _create_company_for_registration returns None on failure
        mock_create_company.return_value = None

        auth = AuthService()
        result = auth.register_user(
            email="owner@example.com",
            password="securepassword123",
            name="Owner",
            company_name="Doomed Co",
        )

        # User is still created, just without a company
        assert result["user"]["email"] == "owner@example.com"
        assert result["user"]["company_id"] is None
        assert result["access_token"]

    @patch.object(AuthService, "_find_user_by_email")
    @patch.object(AuthService, "_create_user")
    def test_empty_company_name_treated_as_none(
        self,
        mock_create_user: MagicMock,
        mock_find_by_email: MagicMock,
    ) -> None:
        """An empty or whitespace-only company_name is treated as None --
        no company created."""
        user = _make_user(company_id=None)

        mock_find_by_email.return_value = None
        mock_create_user.return_value = user

        auth = AuthService()
        result = auth.register_user(
            email="owner@example.com",
            password="securepassword123",
            name="Owner",
            company_name="   ",
        )

        assert result["user"]["company_id"] is None
