"""Unit tests for the server-side feature-flag router (round-13 S1-T2).

The router persists three allow-listed beta toggles on the company record
and exposes ``GET / PATCH /companies/me/feature-flags``. These tests
mock the DataFlow ``_execute_node`` helper so they're pure unit-level —
no real database is touched. Coverage:

  1. GET returns the merged allow-list with defaults applied.
  2. GET 403s when the JWT has no company_id (non-admin path) — actually
     it returns ``defaulted: true`` instead since onboarding hasn't run.
  3. PATCH merges (never replaces) and persists the union.
  4. PATCH 400s on unknown flag names.
  5. PATCH 400s on non-boolean values.
  6. PATCH 403s for non-owners (RBAC enforced via require_role).
  7. Cross-tenant isolation: a tenant-A user can't read or write
     tenant-B flags. The router derives company_id from the JWT, so the
     defence is "JWT is the only source of truth" — we verify by giving
     two different fake users two different company_ids and confirming
     each touches only their own record.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.routers.feature_flags import (
    ALLOWED_FLAGS,
    DEFAULT_FLAGS,
    router,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the feature_flags router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/companies")
    return app


def _fake_user(
    *,
    user_id: int = 10,
    company_id: int | None = 1,
    role: str = "owner",
) -> dict:
    return {
        "sub": user_id,
        "email": f"user{user_id}@example.com",
        "role": role,
        "company_id": company_id,
    }


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Drop rate-limit buckets between tests so PATCH doesn't 429."""
    from hr_advisory.api.middleware.rate_limit import reset_rate_limit_state

    reset_rate_limit_state()
    yield
    reset_rate_limit_state()


@pytest.fixture()
def app() -> FastAPI:
    return _make_app()


# ---------------------------------------------------------------------------
# 1. GET — defaults & merge
# ---------------------------------------------------------------------------


class TestGetFlags:
    """GET /companies/me/feature-flags returns the company's flags."""

    def test_returns_defaults_when_company_has_no_flags(self, app):
        """A company with feature_flags=None gets the default-off allow-list."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user()

        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec:
            mock_exec.return_value = {"id": 1, "name": "Acme", "feature_flags": None}
            client = TestClient(app)
            resp = client.get("/companies/me/feature-flags")

        assert resp.status_code == 200
        data = resp.json()
        assert data["company_id"] == 1
        assert data["flags"] == DEFAULT_FLAGS
        assert set(data["flags"].keys()) == set(ALLOWED_FLAGS)

    def test_returns_persisted_flags(self, app):
        """Stored flags are surfaced verbatim, with missing keys defaulted."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user()

        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec:
            mock_exec.return_value = {
                "id": 1,
                "name": "Acme",
                # Only one of three flags persisted — others default off.
                "feature_flags": {"chat-onboarding": True},
            }
            client = TestClient(app)
            resp = client.get("/companies/me/feature-flags")

        assert resp.status_code == 200
        flags = resp.json()["flags"]
        assert flags["chat-onboarding"] is True
        assert flags["ai-scorecards"] is False
        assert flags["tafep-ai"] is False

    def test_no_company_returns_defaults_with_defaulted_marker(self, app):
        """Pre-onboarding users get defaults and ``defaulted: true``."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(
            company_id=None, role="owner"
        )
        client = TestClient(app)
        resp = client.get("/companies/me/feature-flags")

        assert resp.status_code == 200
        data = resp.json()
        assert data["company_id"] is None
        assert data["defaulted"] is True
        assert data["flags"] == DEFAULT_FLAGS

    def test_404_when_company_record_missing(self, app):
        """A stale JWT pointing at a deleted company surfaces as 404."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user()

        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec:
            # DataFlow ReadNode returns a falsy/error result when the row
            # is missing — the helper should turn that into a 404.
            mock_exec.return_value = {"error": "not found"}
            client = TestClient(app)
            resp = client.get("/companies/me/feature-flags")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. PATCH — merge semantics, validation, RBAC
# ---------------------------------------------------------------------------


class TestPatchFlags:
    """PATCH /companies/me/feature-flags merges flags with strict validation."""

    def test_merges_partial_flags_into_existing(self, app):
        """PATCH does NOT replace — unspecified keys keep their stored value."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(role="owner")

        existing = {
            "id": 1,
            "name": "Acme",
            "feature_flags": {"ai-scorecards": True, "tafep-ai": False},
        }

        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec:
            # First call: read; second call: update. Use side_effect to
            # emit each in turn and capture what we asked DataFlow to write.
            mock_exec.side_effect = [existing, {"updated": True}]
            client = TestClient(app)
            resp = client.patch(
                "/companies/me/feature-flags",
                json={"flags": {"chat-onboarding": True}},
            )

        assert resp.status_code == 200
        merged = resp.json()["flags"]
        assert merged["chat-onboarding"] is True
        # Pre-existing values must survive the merge.
        assert merged["ai-scorecards"] is True
        assert merged["tafep-ai"] is False

        # Inspect the UPDATE call — it should have written the merged map.
        update_call = mock_exec.call_args_list[1]
        params = update_call.args[2]
        assert params["filter"] == {"id": 1}
        assert params["fields"]["feature_flags"]["chat-onboarding"] is True
        assert params["fields"]["feature_flags"]["ai-scorecards"] is True

    def test_accepts_flat_flag_map_without_wrapper(self, app):
        """PATCH body can be a flat ``{flag: bool}`` map for convenience."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(role="owner")

        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec:
            mock_exec.side_effect = [
                {"id": 1, "feature_flags": {}},
                {"updated": True},
            ]
            client = TestClient(app)
            resp = client.patch(
                "/companies/me/feature-flags",
                json={"tafep-ai": True},
            )

        assert resp.status_code == 200
        assert resp.json()["flags"]["tafep-ai"] is True

    def test_rejects_unknown_flag_keys(self, app):
        """Keys outside the allow-list are rejected with 400."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(role="owner")
        client = TestClient(app)
        resp = client.patch(
            "/companies/me/feature-flags",
            json={"flags": {"hack-everything": True}},
        )

        assert resp.status_code == 400
        assert "hack-everything" in resp.json()["detail"]

    def test_rejects_non_boolean_values(self, app):
        """Flag values must be JSON booleans — strings/ints/None all fail."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(role="owner")
        client = TestClient(app)
        resp = client.patch(
            "/companies/me/feature-flags",
            json={"flags": {"chat-onboarding": "yes"}},
        )
        assert resp.status_code == 400
        assert "boolean" in resp.json()["detail"].lower()

    def test_rejects_non_dict_body(self, app):
        """Body must be a JSON object."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(role="owner")
        client = TestClient(app)
        # Send a JSON array — not a dict.
        resp = client.patch("/companies/me/feature-flags", json=["chat-onboarding"])
        assert resp.status_code == 400

    def test_non_owner_is_forbidden(self, app):
        """Only owners (and platform_admin) can flip flags. hr_manager 403s."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        # require_role uses get_current_user under the hood — overriding
        # the latter is enough to flow a non-owner JWT through.
        app.dependency_overrides[get_current_user] = lambda: _fake_user(
            role="hr_manager"
        )
        client = TestClient(app)
        resp = client.patch(
            "/companies/me/feature-flags",
            json={"flags": {"chat-onboarding": True}},
        )
        assert resp.status_code == 403

    def test_employee_role_is_forbidden(self, app):
        """Employees can't change company-wide settings."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(role="employee")
        client = TestClient(app)
        resp = client.patch(
            "/companies/me/feature-flags",
            json={"flags": {"chat-onboarding": True}},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3. Cross-tenant isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    """A user from company A cannot read or write company B's flags.

    The router NEVER takes a company_id from the body or path — it derives
    it from the JWT. So 'cross-tenant access' is structurally impossible:
    each call only ever touches the user's own company. We verify this by
    swapping the fake user between requests and confirming each request
    targets a different DataFlow row.
    """

    def test_each_user_only_touches_their_own_company(self, app):
        """Two owners with different company_ids hit different records."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        # First request: user from company 1.
        app.dependency_overrides[get_current_user] = lambda: _fake_user(
            user_id=10, company_id=1, role="owner"
        )

        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec:
            mock_exec.return_value = {"id": 1, "feature_flags": {"tafep-ai": True}}
            client = TestClient(app)
            resp_a = client.get("/companies/me/feature-flags")
            assert resp_a.status_code == 200
            assert resp_a.json()["company_id"] == 1
            # The DataFlow read used the JWT's company_id — not anything
            # the caller could influence.
            assert mock_exec.call_args_list[0].args[2] == {"id": 1}

        # Second request: a different user from company 2.
        app.dependency_overrides[get_current_user] = lambda: _fake_user(
            user_id=20, company_id=2, role="owner"
        )
        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec_b:
            mock_exec_b.return_value = {
                "id": 2,
                "feature_flags": {"chat-onboarding": True},
            }
            client = TestClient(app)
            resp_b = client.get("/companies/me/feature-flags")
            assert resp_b.status_code == 200
            assert resp_b.json()["company_id"] == 2
            # User B only ever touches row id=2.
            assert mock_exec_b.call_args_list[0].args[2] == {"id": 2}

        # Tenant A's flags do not appear in tenant B's response.
        assert resp_a.json()["flags"]["tafep-ai"] is True
        assert resp_b.json()["flags"]["tafep-ai"] is False

    def test_patch_writes_only_to_own_company(self, app):
        """A PATCH from tenant A's owner targets row id=A, not anyone else."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(
            user_id=10, company_id=42, role="owner"
        )

        with patch(
            "hr_advisory.api.routers.feature_flags._execute_node"
        ) as mock_exec:
            mock_exec.side_effect = [
                {"id": 42, "feature_flags": {}},
                {"updated": True},
            ]
            client = TestClient(app)
            resp = client.patch(
                "/companies/me/feature-flags",
                json={"flags": {"chat-onboarding": True}},
            )

        assert resp.status_code == 200
        # The UPDATE filter is locked to the JWT's company_id.
        update_filter = mock_exec.call_args_list[1].args[2]["filter"]
        assert update_filter == {"id": 42}

    def test_patch_blocked_for_user_with_no_company(self, app):
        """An owner role with no company_id (anomalous) gets 403, not silent write."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _fake_user(
            company_id=None, role="owner"
        )
        client = TestClient(app)
        resp = client.patch(
            "/companies/me/feature-flags",
            json={"flags": {"chat-onboarding": True}},
        )
        assert resp.status_code == 403
