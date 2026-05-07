"""Integration tests for the engagement-survey router (M2: T20-T24).

Hits the live FastAPI app via TestClient with a fresh test company.
Covers:
- Templates CRUD + auth/role gating + tenant isolation.
- Library lazy seed on first GET (P1: 2 templates).
- Cohorts CRUD with P1 preset+ad-hoc enforcement.
- Cohort preview: matched_count, sample_names, anonymity gate, overlap warnings.
- Cross-tenant ad_hoc_employee_ids guard.

Docker must be running: docker compose -f docker-compose.dev.yml up -d
"""

from __future__ import annotations

import logging
import os
import time
import uuid

import jwt as pyjwt
import pytest
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")
# DataFlow defaults exceed Postgres max_connections — match the project pattern.
os.environ.setdefault("DATAFLOW_POOL_SIZE", "5")
os.environ.setdefault("DATAFLOW_POOL_MAX_OVERFLOW", "2")

from hr_advisory.config.settings import Settings, get_settings

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
get_settings.cache_clear()

from hr_advisory.api.platform import create_platform
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Fixtures — fresh test company so we don't collide with seeded data
# ────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8098,
        cors_origins="http://localhost:3000",
        jwt_secret_key=_TEST_JWT_SECRET,
        jwt_algorithm="HS256",
        jwt_expiry_minutes=60,
    )


@pytest.fixture(scope="module")
def platform(settings):
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    return TestClient(platform._gateway.app)


@pytest.fixture(scope="module")
def test_company():
    """A fresh company with two employees so cohort preview / overlap tests work.

    Uses a unique suffix per session so reruns don't pile up.
    """
    suffix = uuid.uuid4().hex[:8]
    company = dataflow_crud.create(
        "Company",
        {
            "name": f"EngagementTest {suffix}",
            "uen": f"E{suffix.upper()[:9]}",
            "sector": "Technology",
        },
    )
    company_id = company["id"]

    employees: list[dict] = []
    user_ids: list[int] = []
    for i in range(7):
        # 7 employees so anonymity gate (n>=5) is testable both ways.
        user = dataflow_crud.create(
            "User",
            {
                "email": f"emp_engagement_{suffix}_{i}@example.com",
                "name": f"Test Employee {i}",
                "company_id": company_id,
                "role": "employee",
                "is_active": True,
            },
        )
        emp = dataflow_crud.create(
            "Employee",
            {
                "user_id": user["id"],
                "company_id": company_id,
                "department": "Engineering" if i < 4 else "Sales",
                "designation": "Engineer" if i < 4 else "Sales Rep",
                "pass_type": "Citizen",
                "is_active": True,
                "start_date": "2024-01-01",
            },
        )
        employees.append(emp)
        user_ids.append(user["id"])

    yield {
        "company_id": company_id,
        "employees": employees,
        "user_ids": user_ids,
    }

    # Cleanup — best-effort.
    for e in employees:
        try:
            dataflow_crud.delete("Employee", e["id"])
        except Exception:
            pass
    for uid in user_ids:
        try:
            dataflow_crud.delete("User", uid)
        except Exception:
            pass
    try:
        dataflow_crud.delete("Company", company_id)
    except Exception:
        pass


def _make_token(
    settings: Settings,
    user_id: int,
    email: str,
    role: str,
    company_id: int,
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + 3600,
        "company_id": company_id,
    }
    return pyjwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


@pytest.fixture
def owner_token(settings, test_company) -> str:
    return _make_token(
        settings,
        user_id=999_001,
        email="owner@engagement-test.com",
        role="owner",
        company_id=test_company["company_id"],
    )


@pytest.fixture
def employee_token(settings, test_company) -> str:
    return _make_token(
        settings,
        user_id=999_002,
        email="employee@engagement-test.com",
        role="employee",
        company_id=test_company["company_id"],
    )


@pytest.fixture
def other_tenant_token(settings) -> str:
    """A token for a DIFFERENT company — used to test tenant isolation."""
    return _make_token(
        settings,
        user_id=999_999,
        email="cross@other.com",
        role="owner",
        company_id=99_999,
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ────────────────────────────────────────────────────────────────────
# Templates (T21)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_templates_list_seeds_library_on_first_call(
    client, owner_token, test_company
):
    """First GET on a fresh company seeds 2 P1 templates (Q12 + monthly_pulse)."""
    resp = client.get("/engagement-surveys/templates", headers=_auth(owner_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    methodologies = sorted(t["methodology"] for t in body["templates"])
    # Round-3 P1 trim — Trust Index + SG SME defer to M8.
    assert methodologies == ["gallup_q12", "pulse"]
    assert body["count"] == 2


@pytest.mark.integration
def test_templates_employee_role_gets_403(client, employee_token):
    resp = client.get(
        "/engagement-surveys/templates", headers=_auth(employee_token)
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_templates_no_auth_gets_401(client):
    resp = client.get("/engagement-surveys/templates")
    assert resp.status_code == 401


@pytest.mark.integration
def test_create_template_succeeds(client, owner_token):
    resp = client.post(
        "/engagement-surveys/templates",
        json={
            "name": "Custom culture pulse",
            "description": "Deep dive on culture themes",
            "methodology": "custom",
            "sections": [
                {
                    "title": "Culture",
                    "questions": [
                        {
                            "id": "q1",
                            "text": "How would you rate our culture?",
                            "type": "likert5",
                            "is_required": True,
                        },
                    ],
                },
            ],
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 200, resp.text
    template = resp.json()["template"]
    assert template["name"] == "Custom culture pulse"
    assert template["methodology"] == "custom"


@pytest.mark.integration
def test_create_template_rejects_invalid_methodology(client, owner_token):
    resp = client.post(
        "/engagement-surveys/templates",
        json={"name": "x", "methodology": "made_up"},
        headers=_auth(owner_token),
    )
    assert resp.status_code == 400
    assert "methodology" in resp.json()["detail"].lower()


@pytest.mark.integration
def test_create_template_rejects_empty_name(client, owner_token):
    resp = client.post(
        "/engagement-surveys/templates",
        json={"name": "", "methodology": "custom"},
        headers=_auth(owner_token),
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_clone_template(client, owner_token):
    """Clone via ?clone_from=N copies sections/methodology/description."""
    # Find a seeded template to clone.
    listing = client.get(
        "/engagement-surveys/templates", headers=_auth(owner_token)
    ).json()
    src = next(t for t in listing["templates"] if t["methodology"] == "gallup_q12")

    resp = client.post(
        f"/engagement-surveys/templates?clone_from={src['id']}",
        json={},
        headers=_auth(owner_token),
    )
    assert resp.status_code == 200, resp.text
    cloned = resp.json()["template"]
    assert "(copy)" in cloned["name"].lower()
    assert cloned["methodology"] == "gallup_q12"
    assert cloned["sections"] == src["sections"]


@pytest.mark.integration
def test_get_template_404_for_other_tenant(
    client, other_tenant_token, owner_token
):
    """Cross-tenant read returns 404, not 403 (don't leak existence)."""
    listing = client.get(
        "/engagement-surveys/templates", headers=_auth(owner_token)
    ).json()
    src_id = listing["templates"][0]["id"]

    resp = client.get(
        f"/engagement-surveys/templates/{src_id}",
        headers=_auth(other_tenant_token),
    )
    assert resp.status_code == 404


@pytest.mark.integration
def test_patch_template_whitelist(client, owner_token):
    """PATCH ignores non-whitelist fields and applies the rest."""
    create = client.post(
        "/engagement-surveys/templates",
        json={"name": "Patch test"},
        headers=_auth(owner_token),
    ).json()["template"]

    resp = client.patch(
        f"/engagement-surveys/templates/{create['id']}",
        json={
            "name": "Patched name",
            "company_id": 99_999,  # whitelist excludes this
            "id": 99_999,
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 200
    updated = resp.json()["template"]
    assert updated["name"] == "Patched name"
    # Tenant guard preserved — the row's company_id wasn't overwritten.
    assert updated["company_id"] == create["company_id"]


@pytest.mark.integration
def test_archive_template_soft_deletes(client, owner_token):
    create = client.post(
        "/engagement-surveys/templates",
        json={"name": "Archive me"},
        headers=_auth(owner_token),
    ).json()["template"]

    resp = client.delete(
        f"/engagement-surveys/templates/{create['id']}",
        headers=_auth(owner_token),
    )
    assert resp.status_code == 200

    # Subsequent list should not include it.
    listing = client.get(
        "/engagement-surveys/templates", headers=_auth(owner_token)
    ).json()
    assert all(t["id"] != create["id"] for t in listing["templates"])


# ────────────────────────────────────────────────────────────────────
# Cohorts (T22)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_create_cohort_with_preset_filter(client, owner_token):
    """P1 preset (department) + ad_hoc list is the canonical happy path."""
    resp = client.post(
        "/engagement-surveys/cohorts",
        json={
            "name": "Engineering only",
            "filter_spec": {"departments": ["Engineering"]},
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 200, resp.text
    cohort = resp.json()["cohort"]
    assert cohort["name"] == "Engineering only"


@pytest.mark.integration
def test_create_cohort_p1_rejects_multi_dimension(client, owner_token):
    """Round-3 trim: deep slices defer to M8 T91 full builder."""
    resp = client.post(
        "/engagement-surveys/cohorts",
        json={
            "name": "deep slice",
            "filter_spec": {
                "departments": ["Engineering"],
                "manager_ids": [1, 2],  # NOT in P1 preset set
            },
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 400
    assert "v2" in resp.json()["detail"].lower() or "P1" in resp.json()["detail"]


@pytest.mark.integration
def test_create_cohort_rejects_unknown_filter_key(client, owner_token):
    resp = client.post(
        "/engagement-surveys/cohorts",
        json={
            "name": "bad",
            "filter_spec": {"some_made_up_key": "x"},
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 400


# ────────────────────────────────────────────────────────────────────
# Cohort preview (T23) + overlap helper (T24)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_preview_returns_matched_count_and_sample_names(
    client, owner_token, test_company
):
    """Preview a department cohort. 4 Engineering employees in fixture."""
    resp = client.post(
        "/engagement-surveys/cohorts/preview",
        json={
            "filter_spec": {"departments": ["Engineering"]},
            "anonymity_tier": "identified",
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["matched_count"] == 4
    assert body["anonymity_safe"] is True  # identified tier always safe
    # Names resolved from User.name (4 names in sample).
    assert len(body["sample_names"]) == 4
    assert all("Test Employee" in n for n in body["sample_names"])
    # No overlap warnings yet (no surveys launched).
    assert body["warnings"] == []


@pytest.mark.integration
def test_preview_anonymity_gate_pseudonymous_under_threshold(
    client, owner_token, test_company
):
    """Pseudonymous + matched_count < 5 → anonymity_unsafe warning."""
    # Sales has only 3 employees in fixture (i=4,5,6).
    resp = client.post(
        "/engagement-surveys/cohorts/preview",
        json={
            "filter_spec": {"departments": ["Sales"]},
            "anonymity_tier": "pseudonymous",
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched_count"] == 3
    assert body["anonymity_safe"] is False
    warning = next(w for w in body["warnings"] if w["kind"] == "anonymity_unsafe")
    assert warning["min_cohort_size"] == 5
    assert warning["matched_count"] == 3


@pytest.mark.integration
def test_preview_anonymity_safe_for_identified_tier_below_threshold(
    client, owner_token, test_company
):
    """Identified tier doesn't need n>=5 — names are visible by design."""
    resp = client.post(
        "/engagement-surveys/cohorts/preview",
        json={
            "filter_spec": {"departments": ["Sales"]},  # n=3
            "anonymity_tier": "identified",
        },
        headers=_auth(owner_token),
    )
    body = resp.json()
    assert body["matched_count"] == 3
    assert body["anonymity_safe"] is True
    # No anonymity_unsafe warning.
    assert all(w["kind"] != "anonymity_unsafe" for w in body["warnings"])


@pytest.mark.integration
def test_preview_rejects_cross_tenant_ad_hoc_ids(
    client, owner_token, test_company
):
    """Round-2 M4: cross-tenant guard — ad_hoc IDs outside the company → 400."""
    resp = client.post(
        "/engagement-surveys/cohorts/preview",
        json={
            "filter_spec": {"ad_hoc_employee_ids": [99_999_999]},
            "anonymity_tier": "identified",
        },
        headers=_auth(owner_token),
    )
    assert resp.status_code == 400
    assert "company" in resp.json()["detail"].lower()


@pytest.mark.integration
def test_preview_all_active_returns_all_seven_employees(
    client, owner_token, test_company
):
    resp = client.post(
        "/engagement-surveys/cohorts/preview",
        json={
            "filter_spec": {"all_active": True},
            "anonymity_tier": "pseudonymous",
        },
        headers=_auth(owner_token),
    )
    body = resp.json()
    assert body["matched_count"] == 7
    assert body["anonymity_safe"] is True  # 7 >= 5
