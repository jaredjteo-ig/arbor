"""Unit tests for invitation lifecycle management endpoints (T283).

Tests the three new endpoints:
1. GET /employees/invitations -- List pending invitations for the company
2. DELETE /employees/invite/{invitation_id} -- Revoke an invitation
3. POST /employees/invite/{invitation_id}/resend -- Resend with fresh token

Also tests the new helper functions:
- _find_invitation_by_id
- _list_invitations_for_company
- _compute_invitation_status

Tier 1 (Unit): Fast, isolated, mocks DataFlow helpers.
The employees module is imported via importlib after pre-mocking kailash
and dataflow dependencies to avoid triggering the full SDK import chain.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the employees router normally — Kailash SDK is installed.
# DataFlow helpers are mocked at the test level, not by corrupting sys.modules.
import hr_advisory.models  # noqa: F401 — ensure models registered
from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.routers import employees as _employees_mod

MODULE = "hr_advisory.api.routers.employees"


# ---------------------------------------------------------------------------
# Test data factories
# ---------------------------------------------------------------------------


def _make_invitation(
    *,
    id: int = 1,
    email: str = "alice@example.com",
    role: str = "employee",
    company_id: int = 10,
    inviter_id: int = 99,
    token: str = "tok-abc",
    is_active: bool = True,
    accepted_at: str | None = None,
    created_at: str | None = None,
    expires_at: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": id,
        "email": email,
        "role": role,
        "company_id": company_id,
        "inviter_id": inviter_id,
        "token": token,
        "is_active": is_active,
        "accepted_at": accepted_at,
        "created_at": created_at or now.isoformat(),
        "expires_at": expires_at or (now + timedelta(days=7)).isoformat(),
    }


def _owner_user(company_id: int = 10) -> dict:
    return {
        "sub": "99",
        "email": "owner@example.com",
        "role": "owner",
        "company_id": company_id,
    }


def _hr_user(company_id: int = 10) -> dict:
    return {
        "sub": "50",
        "email": "hr@example.com",
        "role": "hr_manager",
        "company_id": company_id,
    }


# ---------------------------------------------------------------------------
# FastAPI TestClient fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the employees router mounted."""
    app = FastAPI()
    app.include_router(_employees_mod.router, prefix="/employees")
    return app


@pytest.fixture()
def owner_client():
    """Test client authenticated as company owner."""
    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _owner_user()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def hr_client():
    """Test client authenticated as HR manager."""
    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _hr_user()
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. _compute_invitation_status (pure logic, no mocking needed)
# ---------------------------------------------------------------------------


class TestComputeInvitationStatus:
    """Tests for status derivation logic.

    Priority order: accepted > revoked > expired > pending.
    """

    def test_accepted_status(self):
        """Invitation with accepted_at is 'accepted'."""
        inv = _make_invitation(accepted_at=datetime.now(timezone.utc).isoformat())
        assert _employees_mod._compute_invitation_status(inv) == "accepted"

    def test_revoked_status(self):
        """Invitation with is_active=False and no accepted_at is 'revoked'."""
        inv = _make_invitation(is_active=False)
        assert _employees_mod._compute_invitation_status(inv) == "revoked"

    def test_expired_status(self):
        """Active invitation past expires_at is 'expired'."""
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        inv = _make_invitation(expires_at=past)
        assert _employees_mod._compute_invitation_status(inv) == "expired"

    def test_pending_status(self):
        """Active invitation not expired and not accepted is 'pending'."""
        future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        inv = _make_invitation(expires_at=future)
        assert _employees_mod._compute_invitation_status(inv) == "pending"

    def test_revoked_takes_precedence_over_expired(self):
        """If both is_active=False and past expiry, status is 'revoked' (explicit action)."""
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        inv = _make_invitation(is_active=False, expires_at=past)
        assert _employees_mod._compute_invitation_status(inv) == "revoked"

    def test_accepted_takes_precedence_over_everything(self):
        """If accepted_at is set, status is always 'accepted' regardless of is_active or expiry."""
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        inv = _make_invitation(
            is_active=False,
            expires_at=past,
            accepted_at=datetime.now(timezone.utc).isoformat(),
        )
        assert _employees_mod._compute_invitation_status(inv) == "accepted"

    def test_missing_expires_at_is_pending(self):
        """Invitation with empty expires_at is 'pending' (active, not expired)."""
        inv = _make_invitation()
        inv["expires_at"] = ""
        assert _employees_mod._compute_invitation_status(inv) == "pending"

    def test_unparseable_expires_at_treated_as_expired(self):
        """Malformed expires_at string is treated as expired for safety."""
        inv = _make_invitation(expires_at="not-a-date")
        assert _employees_mod._compute_invitation_status(inv) == "expired"


# ---------------------------------------------------------------------------
# 2. GET /employees/invitations endpoint
# ---------------------------------------------------------------------------


class TestListInvitationsEndpoint:
    """Tests for the list invitations endpoint."""

    @patch(f"{MODULE}._list_invitations_for_company")
    def test_returns_invitations_with_status(self, mock_list, owner_client):
        """Endpoint returns invitations enriched with computed status."""
        future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        inv = _make_invitation(expires_at=future, company_id=10)
        mock_list.return_value = [inv]

        resp = owner_client.get("/employees/invitations")
        assert resp.status_code == 200
        data = resp.json()

        assert "invitations" in data
        assert data["count"] == 1
        assert data["company_id"] == 10

        invitation = data["invitations"][0]
        assert invitation["id"] == 1
        assert invitation["email"] == "alice@example.com"
        assert invitation["role"] == "employee"
        assert invitation["status"] == "pending"
        assert invitation["sent_date"] is not None
        assert invitation["expires_at"] is not None
        assert invitation["accepted_at"] is None

    @patch(f"{MODULE}._list_invitations_for_company")
    def test_returns_empty_list_when_no_invitations(self, mock_list, owner_client):
        """Endpoint returns empty invitations list when none exist."""
        mock_list.return_value = []

        resp = owner_client.get("/employees/invitations")
        assert resp.status_code == 200
        data = resp.json()

        assert data["invitations"] == []
        assert data["count"] == 0

    @patch(f"{MODULE}._list_invitations_for_company")
    def test_multiple_statuses(self, mock_list, owner_client):
        """Endpoint correctly computes different statuses for each invitation."""
        future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        now_str = datetime.now(timezone.utc).isoformat()

        invitations = [
            _make_invitation(id=1, expires_at=future),  # pending
            _make_invitation(id=2, expires_at=past),  # expired
            _make_invitation(id=3, is_active=False),  # revoked
            _make_invitation(id=4, accepted_at=now_str),  # accepted
        ]
        mock_list.return_value = invitations

        resp = owner_client.get("/employees/invitations")
        assert resp.status_code == 200
        data = resp.json()

        assert data["count"] == 4
        statuses = {inv["id"]: inv["status"] for inv in data["invitations"]}
        assert statuses[1] == "pending"
        assert statuses[2] == "expired"
        assert statuses[3] == "revoked"
        assert statuses[4] == "accepted"

    @patch(f"{MODULE}._list_invitations_for_company")
    def test_hr_manager_can_list(self, mock_list, hr_client):
        """HR managers should also be able to list invitations."""
        mock_list.return_value = []
        resp = hr_client.get("/employees/invitations")
        assert resp.status_code == 200

    @patch(f"{MODULE}._list_invitations_for_company")
    def test_response_fields_complete(self, mock_list, owner_client):
        """Each invitation in the response has all required fields."""
        now_str = datetime.now(timezone.utc).isoformat()
        inv = _make_invitation(
            id=42,
            email="bob@example.com",
            role="hr_manager",
            created_at=now_str,
        )
        mock_list.return_value = [inv]

        resp = owner_client.get("/employees/invitations")
        data = resp.json()
        item = data["invitations"][0]

        required_fields = {
            "id",
            "email",
            "role",
            "status",
            "sent_date",
            "expires_at",
            "accepted_at",
        }
        assert required_fields.issubset(set(item.keys()))


# ---------------------------------------------------------------------------
# 3. DELETE /employees/invite/{invitation_id} -- Revoke
# ---------------------------------------------------------------------------


class TestRevokeInvitationEndpoint:
    """Tests for the revocation endpoint."""

    @patch(f"{MODULE}._update_invitation")
    @patch(f"{MODULE}._find_invitation_by_id")
    def test_revoke_active_invitation(self, mock_find, mock_update, owner_client):
        """Revoking an active invitation returns success."""
        inv = _make_invitation(id=5, company_id=10)
        mock_find.return_value = inv
        mock_update.return_value = {"id": 5, "is_active": False}

        resp = owner_client.delete("/employees/invite/5")
        assert resp.status_code == 200
        data = resp.json()
        assert "revoked" in data["message"].lower()

        mock_update.assert_called_once_with(5, {"is_active": False})

    @patch(f"{MODULE}._find_invitation_by_id")
    def test_revoke_nonexistent_returns_404(self, mock_find, owner_client):
        """Revoking a nonexistent invitation returns 404."""
        mock_find.return_value = None

        resp = owner_client.delete("/employees/invite/99999")
        assert resp.status_code == 404

    @patch(f"{MODULE}._find_invitation_by_id")
    def test_revoke_other_company_returns_404(self, mock_find, owner_client):
        """Revoking an invitation from another company returns 404."""
        inv = _make_invitation(id=5, company_id=999)  # Different company
        mock_find.return_value = inv

        resp = owner_client.delete("/employees/invite/5")
        assert resp.status_code == 404

    @patch(f"{MODULE}._find_invitation_by_id")
    def test_revoke_accepted_returns_409(self, mock_find, owner_client):
        """Revoking an already-accepted invitation returns 409."""
        inv = _make_invitation(
            id=5,
            company_id=10,
            accepted_at=datetime.now(timezone.utc).isoformat(),
        )
        mock_find.return_value = inv

        resp = owner_client.delete("/employees/invite/5")
        assert resp.status_code == 409
        assert "accepted" in resp.json()["detail"].lower()

    @patch(f"{MODULE}._find_invitation_by_id")
    def test_revoke_already_revoked_returns_409(self, mock_find, owner_client):
        """Revoking an already-revoked invitation returns 409."""
        inv = _make_invitation(id=5, company_id=10, is_active=False)
        mock_find.return_value = inv

        resp = owner_client.delete("/employees/invite/5")
        assert resp.status_code == 409
        assert "revoked" in resp.json()["detail"].lower()

    @patch(f"{MODULE}._update_invitation")
    @patch(f"{MODULE}._find_invitation_by_id")
    def test_hr_manager_can_revoke(self, mock_find, mock_update, hr_client):
        """HR managers should also be able to revoke invitations."""
        inv = _make_invitation(id=5, company_id=10)
        mock_find.return_value = inv
        mock_update.return_value = {"id": 5, "is_active": False}

        resp = hr_client.delete("/employees/invite/5")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. POST /employees/invite/{invitation_id}/resend -- Resend
# ---------------------------------------------------------------------------


class TestResendInvitationEndpoint:
    """Tests for the resend endpoint."""

    @patch(f"{MODULE}._create_invitation")
    @patch(f"{MODULE}._update_invitation")
    @patch(f"{MODULE}._find_invitation_by_id")
    def test_resend_active_invitation(self, mock_find, mock_update, mock_create, owner_client):
        """Resending an active invitation creates a new one and returns invite URL."""
        inv = _make_invitation(id=5, email="alice@example.com", role="employee", company_id=10)
        mock_find.return_value = inv
        mock_update.return_value = {"id": 5, "is_active": False}
        mock_create.return_value = {"id": 6}

        resp = owner_client.post("/employees/invite/5/resend")
        assert resp.status_code == 200
        data = resp.json()

        assert "resent" in data["message"].lower()
        assert "invite_url" in data
        assert "/signup?token=" in data["invite_url"]
        assert data["invitation"]["email"] == "alice@example.com"
        assert data["invitation"]["role"] == "employee"
        assert data["invitation"]["company_id"] == 10
        assert data["invitation"]["expires_at"] is not None

        # Old invitation should be deactivated
        mock_update.assert_called_once_with(5, {"is_active": False})
        # New invitation should be created
        mock_create.assert_called_once()

    @patch(f"{MODULE}._create_invitation")
    @patch(f"{MODULE}._update_invitation")
    @patch(f"{MODULE}._find_invitation_by_id")
    def test_resend_preserves_email_and_role(
        self, mock_find, mock_update, mock_create, owner_client
    ):
        """Resend creates a new invitation with the same email and role."""
        inv = _make_invitation(id=5, email="bob@example.com", role="hr_manager", company_id=10)
        mock_find.return_value = inv
        mock_update.return_value = {"id": 5, "is_active": False}
        mock_create.return_value = {"id": 7}

        resp = owner_client.post("/employees/invite/5/resend")
        assert resp.status_code == 200

        # Verify _create_invitation was called with the original email and role
        create_call = mock_create.call_args
        assert create_call.kwargs.get("email") == "bob@example.com"
        assert create_call.kwargs.get("role") == "hr_manager"

    @patch(f"{MODULE}._find_invitation_by_id")
    def test_resend_nonexistent_returns_404(self, mock_find, owner_client):
        """Resending a nonexistent invitation returns 404."""
        mock_find.return_value = None

        resp = owner_client.post("/employees/invite/99999/resend")
        assert resp.status_code == 404

    @patch(f"{MODULE}._find_invitation_by_id")
    def test_resend_other_company_returns_404(self, mock_find, owner_client):
        """Resending an invitation from another company returns 404."""
        inv = _make_invitation(id=5, company_id=999)
        mock_find.return_value = inv

        resp = owner_client.post("/employees/invite/5/resend")
        assert resp.status_code == 404

    @patch(f"{MODULE}._find_invitation_by_id")
    def test_resend_accepted_returns_409(self, mock_find, owner_client):
        """Resending an already-accepted invitation returns 409."""
        inv = _make_invitation(
            id=5,
            company_id=10,
            accepted_at=datetime.now(timezone.utc).isoformat(),
        )
        mock_find.return_value = inv

        resp = owner_client.post("/employees/invite/5/resend")
        assert resp.status_code == 409
        assert "accepted" in resp.json()["detail"].lower()

    @patch(f"{MODULE}._create_invitation")
    @patch(f"{MODULE}._update_invitation")
    @patch(f"{MODULE}._find_invitation_by_id")
    def test_resend_uses_frontend_url_env(self, mock_find, mock_update, mock_create, owner_client):
        """Resend invite URL uses FRONTEND_URL from environment."""
        inv = _make_invitation(id=5, company_id=10)
        mock_find.return_value = inv
        mock_update.return_value = {"id": 5, "is_active": False}
        mock_create.return_value = {"id": 8}

        with patch.dict("os.environ", {"FRONTEND_URL": "https://app.example.com"}):
            resp = owner_client.post("/employees/invite/5/resend")

        data = resp.json()
        assert data["invite_url"].startswith("https://app.example.com/signup?token=")

    @patch(f"{MODULE}._create_invitation")
    @patch(f"{MODULE}._update_invitation")
    @patch(f"{MODULE}._find_invitation_by_id")
    def test_resend_expired_invitation_succeeds(
        self, mock_find, mock_update, mock_create, owner_client
    ):
        """Resending an expired (but not accepted) invitation should succeed."""
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        inv = _make_invitation(id=5, company_id=10, expires_at=past)
        mock_find.return_value = inv
        mock_update.return_value = {"id": 5, "is_active": False}
        mock_create.return_value = {"id": 9}

        resp = owner_client.post("/employees/invite/5/resend")
        assert resp.status_code == 200

    @patch(f"{MODULE}._create_invitation")
    @patch(f"{MODULE}._update_invitation")
    @patch(f"{MODULE}._find_invitation_by_id")
    def test_hr_manager_can_resend(self, mock_find, mock_update, mock_create, hr_client):
        """HR managers should also be able to resend invitations."""
        inv = _make_invitation(id=5, company_id=10)
        mock_find.return_value = inv
        mock_update.return_value = {"id": 5, "is_active": False}
        mock_create.return_value = {"id": 10}

        resp = hr_client.post("/employees/invite/5/resend")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. _find_invitation_by_id helper
# ---------------------------------------------------------------------------


class TestFindInvitationById:
    """Tests for the DataFlow helper that finds an invitation by ID."""

    def test_finds_existing_invitation(self):
        """Returns invitation dict when found."""
        inv = _make_invitation(id=7)
        with (
            patch("kailash.runtime.LocalRuntime") as MockRT,
            patch("kailash.workflow.builder.WorkflowBuilder") as MockWB,
        ):
            mock_runtime = MagicMock()
            mock_runtime.execute.return_value = (
                {"find_inv": {"records": [inv], "count": 1}},
                "run-f1",
            )
            MockRT.return_value = mock_runtime
            MockWB.return_value = MagicMock()

            result = _employees_mod._find_invitation_by_id(7)
            assert result is not None
            assert result["id"] == 7

    def test_returns_none_for_missing(self):
        """Returns None when invitation not found."""
        with (
            patch("kailash.runtime.LocalRuntime") as MockRT,
            patch("kailash.workflow.builder.WorkflowBuilder") as MockWB,
        ):
            mock_runtime = MagicMock()
            mock_runtime.execute.return_value = (
                {"find_inv": {"records": [], "count": 0}},
                "run-f2",
            )
            MockRT.return_value = mock_runtime
            MockWB.return_value = MagicMock()

            result = _employees_mod._find_invitation_by_id(999)
            assert result is None

    def test_filters_by_id(self):
        """Helper must use InvitationListNode with id filter."""
        with (
            patch("kailash.runtime.LocalRuntime") as MockRT,
            patch("kailash.workflow.builder.WorkflowBuilder") as MockWB,
        ):
            mock_runtime = MagicMock()
            mock_runtime.execute.return_value = (
                {"find_inv": {"records": [], "count": 0}},
                "run-f3",
            )
            MockRT.return_value = mock_runtime
            mock_wf = MagicMock()
            MockWB.return_value = mock_wf

            _employees_mod._find_invitation_by_id(42)

            mock_wf.add_node.assert_called_once()
            call_args = mock_wf.add_node.call_args
            node_type = call_args[0][0]
            params = call_args[0][2]
            assert node_type == "InvitationListNode"
            assert params["filter"]["id"] == 42


# ---------------------------------------------------------------------------
# 6. _list_invitations_for_company helper
# ---------------------------------------------------------------------------


class TestListInvitationsForCompanyHelper:
    """Tests for the DataFlow helper that lists invitations by company."""

    def test_returns_list(self):
        """Helper returns a list of invitation dicts."""
        inv = _make_invitation()
        with (
            patch("kailash.runtime.LocalRuntime") as MockRT,
            patch("kailash.workflow.builder.WorkflowBuilder") as MockWB,
        ):
            mock_runtime = MagicMock()
            mock_runtime.execute.return_value = (
                {"list_inv": {"records": [inv], "count": 1}},
                "run-1",
            )
            MockRT.return_value = mock_runtime
            MockWB.return_value = MagicMock()

            result = _employees_mod._list_invitations_for_company(10)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["email"] == "alice@example.com"

    def test_returns_empty_list_when_none(self):
        """Helper returns empty list when no invitations exist."""
        with (
            patch("kailash.runtime.LocalRuntime") as MockRT,
            patch("kailash.workflow.builder.WorkflowBuilder") as MockWB,
        ):
            mock_runtime = MagicMock()
            mock_runtime.execute.return_value = (
                {"list_inv": {"records": [], "count": 0}},
                "run-2",
            )
            MockRT.return_value = mock_runtime
            MockWB.return_value = MagicMock()

            result = _employees_mod._list_invitations_for_company(10)
            assert result == []

    def test_passes_company_id_filter(self):
        """Helper must filter by company_id with caching disabled."""
        with (
            patch("kailash.runtime.LocalRuntime") as MockRT,
            patch("kailash.workflow.builder.WorkflowBuilder") as MockWB,
        ):
            mock_runtime = MagicMock()
            mock_runtime.execute.return_value = (
                {"list_inv": {"records": [], "count": 0}},
                "run-3",
            )
            MockRT.return_value = mock_runtime
            mock_wf = MagicMock()
            MockWB.return_value = mock_wf

            _employees_mod._list_invitations_for_company(42)

            mock_wf.add_node.assert_called_once()
            call_args = mock_wf.add_node.call_args
            node_type = call_args[0][0]
            params = call_args[0][2]
            assert node_type == "InvitationListNode"
            assert params["filter"]["company_id"] == 42
            assert params["enable_cache"] is False
