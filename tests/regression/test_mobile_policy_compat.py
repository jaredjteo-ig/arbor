"""Regression tests for mobile app policy compatibility (T036).

Verifies that the backend changes to the Company Policy feature do not
break the existing mobile Flutter app, which depends on:

1. CompanyPolicy model retaining the ``policy_type`` field (not renamed)
2. Seeded policy_type values remain unchanged: leave, fwa, handbook, wsh/safety
3. Deprecated GET /employees/policies endpoint still exists and returns
   the expected response shape (id, policy_type, title, content,
   effective_date, is_active)

These tests are permanent regression guards. NEVER delete them.
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

from hr_advisory.config.settings import Settings, get_settings

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
get_settings.cache_clear()

from hr_advisory.api.platform import create_platform

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8096,
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


def _make_token(settings: Settings, user_id: int, company_id: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": f"mobile_compat_{uuid.uuid4().hex[:8]}@example.com",
        "role": "owner",
        "company_id": company_id,
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture(scope="module")
def owner_token(settings) -> str:
    return _make_token(settings, user_id=301, company_id=1)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. CompanyPolicy model still has policy_type field
# ---------------------------------------------------------------------------


class TestCompanyPolicyModel:
    """Verify CompanyPolicy model retains the policy_type field.

    The Flutter mobile app reads ``policy_type`` from API responses.
    Renaming or removing this field would break the mobile app.
    """

    @pytest.mark.regression
    def test_company_policy_has_policy_type_field(self):
        """CompanyPolicy model must have a 'policy_type' field.

        Regression guard: the mobile app's compliance_screen.dart
        and other screens parse the policy_type field from the API.
        Renaming to 'category' or removing it would break the mobile app.

        DataFlow @db.model uses __annotations__ and _dataflow_meta for
        field definitions rather than class-level attribute descriptors,
        so we check both __annotations__ and _dataflow_meta['fields'].
        """
        from hr_advisory.models.company_user import CompanyPolicy

        # Check via __annotations__ (Python type hints)
        assert "policy_type" in CompanyPolicy.__annotations__, (
            "CompanyPolicy must retain the 'policy_type' field for mobile compatibility. "
            "The Flutter app depends on this field name."
        )
        # Also verify via DataFlow metadata
        meta = getattr(CompanyPolicy, "_dataflow_meta", {})
        if isinstance(meta, dict) and "fields" in meta:
            assert "policy_type" in meta["fields"], (
                "CompanyPolicy._dataflow_meta must include 'policy_type' field."
            )

    @pytest.mark.regression
    def test_company_policy_has_required_mobile_fields(self):
        """CompanyPolicy must have all fields the mobile app expects."""
        from hr_advisory.models.company_user import CompanyPolicy

        required_fields = [
            "policy_type",
            "title",
            "content",
            "effective_date",
            "is_active",
            "company_id",
        ]
        annotations = CompanyPolicy.__annotations__
        for field_name in required_fields:
            assert field_name in annotations, (
                f"CompanyPolicy must retain the '{field_name}' field for mobile compatibility."
            )


# ---------------------------------------------------------------------------
# 2. Seeded policy_type values are unchanged
# ---------------------------------------------------------------------------


class TestSeededPolicyTypes:
    """Verify the canonical seeded policy_type values are unchanged.

    The mobile app and default company setup depend on these values.
    Both profile.py and company_seeding.py define DEFAULT_POLICIES
    with known policy_type values.
    """

    @pytest.mark.regression
    def test_profile_seeded_policy_types_unchanged(self):
        """profile.py DEFAULT_POLICIES contains the expected policy_type values.

        The original set: leave, fwa, handbook, safety.
        """
        from hr_advisory.api.routers.profile import DEFAULT_POLICIES

        seeded_types = {p["policy_type"] for p in DEFAULT_POLICIES}
        expected = {"leave", "fwa", "handbook", "safety"}
        assert expected.issubset(seeded_types), (
            f"profile.py DEFAULT_POLICIES must contain policy_types {expected}, "
            f"but found {seeded_types}. Removing or renaming seeded types breaks "
            f"the mobile app and existing company data."
        )

    @pytest.mark.regression
    def test_company_seeding_policy_types_unchanged(self):
        """company_seeding.py DEFAULT_POLICIES contains the expected policy_type values.

        The set: leave, fwa, handbook, wsh.
        """
        from hr_advisory.services.company_seeding import DEFAULT_POLICIES

        seeded_types = {p["policy_type"] for p in DEFAULT_POLICIES}
        expected = {"leave", "fwa", "handbook", "wsh"}
        assert expected.issubset(seeded_types), (
            f"company_seeding.py DEFAULT_POLICIES must contain policy_types {expected}, "
            f"but found {seeded_types}. Removing or renaming seeded types breaks "
            f"existing company data."
        )

    @pytest.mark.regression
    def test_seeded_policies_have_title_and_content(self):
        """All seeded policies must have non-empty title and content."""
        from hr_advisory.api.routers.profile import DEFAULT_POLICIES as profile_policies
        from hr_advisory.services.company_seeding import DEFAULT_POLICIES as seeding_policies

        for policies, source in [
            (profile_policies, "profile.py"),
            (seeding_policies, "company_seeding.py"),
        ]:
            for p in policies:
                assert p.get("title"), (
                    f"Seeded policy in {source} with policy_type='{p.get('policy_type')}' "
                    f"must have a non-empty title."
                )
                assert p.get("content"), (
                    f"Seeded policy in {source} with policy_type='{p.get('policy_type')}' "
                    f"must have non-empty content."
                )


# ---------------------------------------------------------------------------
# 3. Deprecated GET /employees/policies endpoint still exists
# ---------------------------------------------------------------------------


class TestDeprecatedEndpoint:
    """Verify the deprecated GET /employees/policies endpoint still works.

    The mobile app currently calls this endpoint. It must remain functional
    until the mobile app is updated to use GET /policies/ instead.
    """

    @pytest.mark.regression
    def test_deprecated_endpoint_exists(self, client: TestClient, owner_token: str):
        """GET /employees/policies returns 200 (not 404 or 405).

        The endpoint is deprecated but must remain functional for
        backward compatibility with the Flutter mobile app.
        """
        resp = client.get("/employees/policies", headers=_auth(owner_token))
        assert resp.status_code == 200, (
            f"GET /employees/policies must still exist (got {resp.status_code}). "
            "The mobile app depends on this deprecated endpoint."
        )

    @pytest.mark.regression
    def test_deprecated_endpoint_response_shape(self, client: TestClient, owner_token: str):
        """GET /employees/policies returns the expected response shape.

        The mobile app expects: {policies: [{id, policy_type, title, content,
        effective_date, is_active}], count: int}
        """
        resp = client.get("/employees/policies", headers=_auth(owner_token))
        assert resp.status_code == 200
        data = resp.json()

        # Top-level keys
        assert "policies" in data, "Response must have 'policies' key"
        assert "count" in data, "Response must have 'count' key"
        assert isinstance(data["policies"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["policies"])

        # Each policy must have the fields the mobile app reads
        mobile_required_fields = {
            "id",
            "policy_type",
            "title",
            "content",
            "effective_date",
            "is_active",
        }
        for policy in data["policies"]:
            missing = mobile_required_fields - set(policy.keys())
            assert not missing, (
                f"Deprecated endpoint policy record missing fields: {missing}. "
                f"The mobile app expects: {mobile_required_fields}"
            )

    @pytest.mark.regression
    def test_deprecated_endpoint_requires_auth(self, client: TestClient):
        """GET /employees/policies without auth returns 401."""
        resp = client.get("/employees/policies")
        assert resp.status_code == 401

    @pytest.mark.regression
    def test_deprecated_endpoint_returns_only_active_policies(
        self, client: TestClient, owner_token: str
    ):
        """The deprecated endpoint returns only active policies (is_active=True)."""
        resp = client.get("/employees/policies", headers=_auth(owner_token))
        assert resp.status_code == 200
        for policy in resp.json()["policies"]:
            assert policy["is_active"] is True, (
                "Deprecated endpoint must only return active policies."
            )

    @pytest.mark.regression
    def test_new_policies_endpoint_also_returns_policy_type(
        self, client: TestClient, owner_token: str
    ):
        """GET /policies/ (new endpoint) also includes policy_type for consistency.

        Even though the mobile app uses the deprecated endpoint, the new
        endpoint should also return policy_type to support migration.
        """
        resp = client.get("/policies/", headers=_auth(owner_token))
        assert resp.status_code == 200
        for policy in resp.json()["policies"]:
            assert "policy_type" in policy, (
                "New GET /policies/ endpoint must include 'policy_type' in response "
                "to support mobile app migration from the deprecated endpoint."
            )
