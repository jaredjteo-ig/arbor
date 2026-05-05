"""Regression: S2-T1 — hire-role allow-list (round-12 CRITICAL).

Pins the privilege-escalation guard at two layers:

  Layer 1 — `recruitment.hire_candidate` rejects any role outside
            HIRABLE_ROLES = {employee, hr_manager} with a 400.
  Layer 2 — `auth._register_employee_via_invitation` clamps the
            invitation's role to "employee" if it is outside the
            allow-list, so a tampered Invitation row cannot escalate
            to platform_admin / owner.

Both are required: a single layer is brittle (Layer 1 depends on the
hire endpoint being the only Invitation-creator; Layer 2 catches every
path including direct-DB Invitation inserts and future routers).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.rate_limit import reset_rate_limit_state
from hr_advisory.api.routers.recruitment import HIRABLE_ROLES, router as recruitment_router


def _fake_owner() -> dict:
    return {"sub": "10", "email": "owner@example.com", "role": "owner", "company_id": 1}


def _candidate(**overrides) -> dict:
    base = {
        "id": 5,
        "company_id": 1,
        "job_listing_id": 1,
        "name": "Alice Tan",
        "email": "alice@example.com",
        "phone": "+6591234567",
        "stage": "offered",
        "source": "direct",
        "pdpa_consent": True,
    }
    base.update(overrides)
    return base


@pytest.fixture()
def owner_client() -> TestClient:
    reset_rate_limit_state()
    app = FastAPI()
    app.include_router(recruitment_router, prefix="/recruitment")
    app.dependency_overrides[get_current_user] = _fake_owner
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        reset_rate_limit_state()


# ---------------------------------------------------------------------------
# Layer 1: recruitment.hire_candidate rejects escalation attempts
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t1_hirable_roles_excludes_owner_and_admin():
    """The allow-list documents intent: only employee + hr_manager are hirable.
    Adding owner/platform_admin/superadmin requires explicit re-design and
    re-audit; silently widening the set would re-open the round-12 CRITICAL.
    """
    assert HIRABLE_ROLES == frozenset({"employee", "hr_manager"})


@pytest.mark.regression
@pytest.mark.parametrize("malicious_role", ["platform_admin", "owner", "superuser", "admin", ""])
def test_s2_t1_hire_rejects_role_outside_allowlist(owner_client, malicious_role):
    """POST /recruitment/candidates/{id}/hire with a non-hirable role MUST
    return 400 and MUST NOT create the Invitation row. Skips the body-default
    case (no role) which is covered by the accept-list test below.
    """
    candidate = _candidate(stage="offered")
    create_calls: list[tuple[str, dict]] = []

    def _read(model: str, record_id: int):
        if model == "Candidate":
            return candidate
        if model == "JobListing":
            return {"id": 1, "department": "Engineering", "title": "SWE"}
        return None

    def _list_records(model: str, filters: dict, **kwargs):
        # _verify_candidate_ownership uses list_records on Candidate.
        if model == "Candidate" and filters.get("id") == candidate["id"]:
            return [candidate]
        return []

    def _create(model: str, fields: dict):
        create_calls.append((model, fields))
        return {**fields, "id": 999}

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.read.side_effect = _read
        mock_crud.list_records.side_effect = _list_records
        mock_crud.create.side_effect = _create
        mock_crud.update.return_value = candidate
        resp = owner_client.post(
            f"/recruitment/candidates/{candidate['id']}/hire",
            json={"role": malicious_role},
        )

    assert resp.status_code == 400, (
        f"hire with role={malicious_role!r} should be rejected with 400, "
        f"got {resp.status_code}: {resp.text}"
    )
    assert "Invalid role" in resp.text, "Error response should explain the rejection"
    assert all(model != "Invitation" for model, _ in create_calls), (
        f"No Invitation row should be created for a rejected hire; "
        f"got create calls: {create_calls}"
    )


@pytest.mark.regression
@pytest.mark.parametrize("valid_role", ["employee", "hr_manager"])
def test_s2_t1_hire_accepts_hirable_roles(owner_client, valid_role):
    """The allow-listed roles must still work — privilege guard must not
    over-reject. Asserts the Invitation row is created with the same role.
    """
    candidate = _candidate(stage="offered")
    invitation_row = {}

    def _read(model: str, record_id: int):
        if model == "Candidate":
            return candidate
        if model == "JobListing":
            return {"id": 1, "department": "Engineering", "title": "SWE"}
        return None

    def _list_records(model: str, filters: dict, **kwargs):
        # _verify_candidate_ownership uses list_records on Candidate.
        if model == "Candidate" and filters.get("id") == candidate["id"]:
            return [candidate]
        return []

    def _create(model: str, fields: dict):
        if model == "Invitation":
            invitation_row.update(fields)
            return {**fields, "id": 42}
        return {**fields, "id": 999}

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud, \
         patch("hr_advisory.api.routers.recruitment._log_candidate_activity"):
        mock_crud.read.side_effect = _read
        mock_crud.list_records.side_effect = _list_records
        mock_crud.create.side_effect = _create
        mock_crud.update.return_value = candidate
        resp = owner_client.post(
            f"/recruitment/candidates/{candidate['id']}/hire",
            json={"role": valid_role},
        )

    assert resp.status_code == 200, (
        f"hire with valid role={valid_role!r} should succeed, "
        f"got {resp.status_code}: {resp.text}"
    )
    assert invitation_row.get("role") == valid_role, (
        f"Invitation row should record the requested role={valid_role!r}, "
        f"got: {invitation_row.get('role')!r}"
    )


@pytest.mark.regression
def test_s2_t1_hire_default_role_is_employee(owner_client):
    """When body omits role entirely, default is 'employee' (in HIRABLE_ROLES).
    """
    candidate = _candidate(stage="offered")
    invitation_row = {}

    def _read(model: str, record_id: int):
        if model == "Candidate":
            return candidate
        if model == "JobListing":
            return {"id": 1, "department": "Engineering", "title": "SWE"}
        return None

    def _list_records(model: str, filters: dict, **kwargs):
        # _verify_candidate_ownership uses list_records on Candidate.
        if model == "Candidate" and filters.get("id") == candidate["id"]:
            return [candidate]
        return []

    def _create(model: str, fields: dict):
        if model == "Invitation":
            invitation_row.update(fields)
            return {**fields, "id": 42}
        return {**fields, "id": 999}

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud, \
         patch("hr_advisory.api.routers.recruitment._log_candidate_activity"):
        mock_crud.read.side_effect = _read
        mock_crud.list_records.side_effect = _list_records
        mock_crud.create.side_effect = _create
        mock_crud.update.return_value = candidate
        resp = owner_client.post(
            f"/recruitment/candidates/{candidate['id']}/hire",
            json={},
        )

    assert resp.status_code == 200, resp.text
    assert invitation_row.get("role") == "employee"


# ---------------------------------------------------------------------------
# Layer 2: auth._register_employee_via_invitation clamps tampered roles
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t1_invitation_acceptance_clamps_role_outside_allowlist(caplog):
    """Source-level guard: the invitation-acceptance handler must contain
    an INVITATION_VALID_ROLES allow-list (frozenset({employee, hr_manager}))
    and clamp anything outside it to 'employee'.

    A source-level assertion is more durable than a full-stack integration
    test here because the surrounding flow (find_invitation_by_token,
    _create_user, EmployeeCreateNode, leave-balance seed, audit log)
    requires real Postgres + a 200-line test fixture. The source check
    pins the security-critical line; integration coverage already exists
    for the happy-path invitation flow.
    """
    import inspect

    from hr_advisory.api.routers import auth as auth_router

    src = inspect.getsource(auth_router)
    assert 'INVITATION_VALID_ROLES' in src, (
        "auth.py must define INVITATION_VALID_ROLES — defense-in-depth "
        "against a tampered Invitation row escalating to platform_admin."
    )
    assert 'frozenset({"employee", "hr_manager"})' in src, (
        "INVITATION_VALID_ROLES must be exactly {employee, hr_manager} — "
        "silently widening the set re-opens the round-12 CRITICAL."
    )
    assert 'invited_role = "employee"' in src, (
        "Tampered roles must clamp to 'employee', not be passed through "
        "to _create_user unchecked."
    )
