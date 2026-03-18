"""Unit tests for CSV import returning invite tokens (T285).

Verifies that the POST /employees/import/confirm endpoint returns
invitation URLs alongside the existing created/stipped counts.

Tests use FastAPI TestClient with mocked DataFlow operations.
"""

from __future__ import annotations

import sys
import types
import uuid
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Pre-populate sys.modules with stubs for all broken kailash submodules.
#
# The installed kailash SDK has import chain breakages (version mismatch).
# Rather than patching each broken attribute one at a time, we inject stub
# modules for the entire kailash.runtime / kailash.workflow chain BEFORE
# anything tries to import them through the hr_advisory import chain.
#
# We ONLY stub modules that are NOT already loaded (preserving real modules
# that DO work, like kailash itself and kailash.nodes).
# ---------------------------------------------------------------------------


class _StubModule(types.ModuleType):
    """A stub module that returns MagicMock for any missing attribute.

    This handles `from some.module import AnyName` without needing to
    enumerate every possible name upfront.
    """

    def __init__(self, name: str, attrs: dict | None = None):
        super().__init__(name)
        self.__path__ = []  # Makes it look like a package
        self.__file__ = f"<stub:{name}>"
        if attrs:
            for k, v in attrs.items():
                setattr(self, k, v)

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return MagicMock


def _stub_module(name: str, attrs: dict | None = None) -> _StubModule:
    """Create a stub module with __path__ and catch-all __getattr__."""
    return _StubModule(name, attrs)


_RUNTIME_ATTRS = {
    "LocalRuntime": MagicMock,
    "AsyncLocalRuntime": MagicMock,
    "BaseRuntime": MagicMock,
}

_WORKFLOW_ATTRS = {
    "Workflow": MagicMock,
    "WorkflowBuilder": MagicMock,
    "workflow": MagicMock,
}

_NODE_ATTRS = {
    "Node": MagicMock,
    "NodeParameter": MagicMock,
    "nodes": MagicMock,
}

# DataFlow stub: DataFlow() must be callable and return a mock
_DATAFLOW_ATTRS = {
    "DataFlow": MagicMock,
    "Model": MagicMock,
}

# Modules to stub -- only stubbed if NOT already in sys.modules
_STUBS: dict[str, dict | None] = {
    # dataflow (must come before hr_advisory.models.database)
    "dataflow": _DATAFLOW_ATTRS,
    # kailash.runtime chain
    "kailash.runtime": _RUNTIME_ATTRS,
    "kailash.runtime.async_local": _RUNTIME_ATTRS,
    "kailash.runtime.local": _RUNTIME_ATTRS,
    "kailash.runtime.base": _RUNTIME_ATTRS,
    # kailash.workflow chain
    "kailash.workflow": _WORKFLOW_ATTRS,
    "kailash.workflow.builder": _WORKFLOW_ATTRS,
    # kailash.nodes chain (patch missing attributes)
    "kailash.nodes": _NODE_ATTRS,
    "kailash.nodes.base": _NODE_ATTRS,
    # kaizen chain
    "kaizen": {"BaseAgent": MagicMock},
    "kaizen.core": {"BaseAgent": MagicMock, "base_agent": MagicMock},
    "kaizen.core.base_agent": {"BaseAgent": MagicMock},
    "kaizen.core.signature": {"Signature": MagicMock},
    "kaizen.core.chain_of_thought": {"ChainOfThought": MagicMock},
    "kaizen.memory": {"SharedMemoryPool": MagicMock},
    "kaizen.signatures": {"Signature": MagicMock},
}

for _name, _attrs in _STUBS.items():
    if _name not in sys.modules:
        sys.modules[_name] = _stub_module(_name, _attrs)
    else:
        # Module exists but may be missing attributes
        _existing = sys.modules[_name]
        if _attrs:
            for _k, _v in _attrs.items():
                if not hasattr(_existing, _k):
                    setattr(_existing, _k, _v)

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from hr_advisory.api.routers.employees import router  # noqa: E402
from hr_advisory.api.middleware.auth_middleware import get_current_user  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers and fixtures
# ---------------------------------------------------------------------------


def _fake_owner() -> dict:
    return {
        "sub": "10",
        "email": "owner@example.com",
        "role": "owner",
        "company_id": 1,
    }


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the employees router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/employees")
    return app


@pytest.fixture()
def owner_client():
    """Test client authenticated as company owner."""
    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_owner()
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: CSV import/confirm returns invitations
# ---------------------------------------------------------------------------


class TestCSVImportReturnsInviteTokens:
    """POST /employees/import/confirm must return invite URLs for each
    successfully created invitation."""

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_successful_import_returns_invitations_list(self, mock_create_inv, owner_client):
        """Each created invitation should appear in response.invitations."""
        mock_create_inv.return_value = {"id": 1}

        records = [
            {"valid": True, "email": "alice@example.com", "name": "Alice"},
            {"valid": True, "email": "bob@example.com", "name": "Bob"},
        ]

        resp = owner_client.post("/employees/import/confirm", json={"records": records})
        assert resp.status_code == 200
        data = resp.json()

        # Backward compatibility: existing fields still present
        assert data["created"] == 2
        assert data["skipped"] == 0
        assert "message" in data
        assert "errors" in data

        # New field: invitations list
        assert "invitations" in data
        assert len(data["invitations"]) == 2

        emails_in_response = {inv["email"] for inv in data["invitations"]}
        assert emails_in_response == {"alice@example.com", "bob@example.com"}

        for inv in data["invitations"]:
            assert "invite_url" in inv
            assert inv["invite_url"].startswith("http")
            assert "token=" in inv["invite_url"]

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_invite_url_uses_frontend_url_env(self, mock_create_inv, owner_client):
        """invite_url must use FRONTEND_URL from environment."""
        mock_create_inv.return_value = {"id": 1}

        records = [
            {"valid": True, "email": "carol@example.com", "name": "Carol"},
        ]

        with patch.dict("os.environ", {"FRONTEND_URL": "https://app.example.com"}):
            resp = owner_client.post("/employees/import/confirm", json={"records": records})

        data = resp.json()
        assert len(data["invitations"]) == 1
        assert data["invitations"][0]["invite_url"].startswith(
            "https://app.example.com/signup?token="
        )

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_invite_url_defaults_to_localhost(self, mock_create_inv, owner_client):
        """When FRONTEND_URL is not set, default to localhost:3000."""
        mock_create_inv.return_value = {"id": 1}

        records = [
            {"valid": True, "email": "dave@example.com", "name": "Dave"},
        ]

        import os

        original = os.environ.pop("FRONTEND_URL", None)
        try:
            resp = owner_client.post("/employees/import/confirm", json={"records": records})
        finally:
            if original is not None:
                os.environ["FRONTEND_URL"] = original

        data = resp.json()
        assert len(data["invitations"]) == 1
        assert data["invitations"][0]["invite_url"].startswith(
            "http://localhost:3000/signup?token="
        )

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_skipped_records_not_in_invitations(self, mock_create_inv, owner_client):
        """Invalid/skipped records must NOT appear in invitations list."""
        mock_create_inv.return_value = {"id": 1}

        records = [
            {"valid": True, "email": "alice@example.com", "name": "Alice"},
            {"valid": False, "email": "bad@example.com", "name": "Bad"},
        ]

        resp = owner_client.post("/employees/import/confirm", json={"records": records})
        data = resp.json()

        assert data["created"] == 1
        assert data["skipped"] == 1
        assert len(data["invitations"]) == 1
        assert data["invitations"][0]["email"] == "alice@example.com"

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_failed_invitation_not_in_invitations(self, mock_create_inv, owner_client):
        """If _create_invitation raises, that email should NOT be in invitations."""
        mock_create_inv.side_effect = [
            {"id": 1},  # First succeeds
            Exception("DB error"),  # Second fails
        ]

        records = [
            {"valid": True, "email": "alice@example.com", "name": "Alice"},
            {"valid": True, "email": "fail@example.com", "name": "Fail"},
        ]

        resp = owner_client.post("/employees/import/confirm", json={"records": records})
        data = resp.json()

        assert data["created"] == 1
        assert data["skipped"] == 1
        assert len(data["invitations"]) == 1
        assert data["invitations"][0]["email"] == "alice@example.com"

        # The failed one should be in errors
        assert len(data["errors"]) == 1
        assert data["errors"][0]["email"] == "fail@example.com"

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_empty_email_record_skipped_no_invitation(self, mock_create_inv, owner_client):
        """Records with empty email should be skipped, no invitation created."""
        records = [
            {"valid": True, "email": "", "name": "NoEmail"},
        ]

        resp = owner_client.post("/employees/import/confirm", json={"records": records})
        data = resp.json()

        assert data["created"] == 0
        assert data["skipped"] == 1
        assert len(data["invitations"]) == 0
        mock_create_inv.assert_not_called()

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_no_records_returns_error(self, mock_create_inv, owner_client):
        """Empty records list should return 400."""
        resp = owner_client.post("/employees/import/confirm", json={"records": []})
        assert resp.status_code == 400

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_invitations_contain_valid_uuid_tokens(self, mock_create_inv, owner_client):
        """Each invite_url must contain a valid UUID token."""
        mock_create_inv.return_value = {"id": 1}

        records = [
            {"valid": True, "email": "test@example.com", "name": "Test"},
        ]

        resp = owner_client.post("/employees/import/confirm", json={"records": records})
        data = resp.json()

        invite_url = data["invitations"][0]["invite_url"]
        token_str = invite_url.split("token=")[1]

        # Should be a valid UUID
        parsed = uuid.UUID(token_str)
        assert str(parsed) == token_str

    @patch("hr_advisory.api.routers.employees._create_invitation")
    def test_backward_compatibility_fields_preserved(self, mock_create_inv, owner_client):
        """All original response fields must still be present."""
        mock_create_inv.return_value = {"id": 1}

        records = [
            {"valid": True, "email": "alice@example.com", "name": "Alice"},
        ]

        resp = owner_client.post("/employees/import/confirm", json={"records": records})
        data = resp.json()

        # Original fields
        assert "message" in data
        assert "created" in data
        assert "skipped" in data
        assert "errors" in data

        # Message still has the expected format
        assert "1 invitations sent" in data["message"] or "1 invitation" in data["message"]
