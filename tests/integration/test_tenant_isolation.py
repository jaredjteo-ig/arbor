"""Integration tests for tenant isolation on company-scoped endpoints.

Tests that:
1. User A cannot access User B's company data via API
2. Admin (platform_admin) users can access all companies
3. Unauthenticated requests are rejected with 401
4. Company-scoped endpoints enforce tenant isolation

Uses real Nexus TestClient with real JWT tokens -- no mocking.
"""

import os
import time
import uuid

import jwt as pyjwt
import pytest
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")

pytestmark = pytest.mark.requires_postgres

from hr_advisory.config.settings import Settings, get_settings

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
get_settings.cache_clear()

from hr_advisory.api.platform import create_platform
from hr_advisory.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"tenant_test_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8099,
        cors_origins="*",
        jwt_secret_key=_TEST_JWT_SECRET,
        jwt_algorithm="HS256",
        jwt_expiry_minutes=60,
    )


@pytest.fixture(scope="module")
def auth_service(settings) -> AuthService:
    return AuthService(settings=settings)


@pytest.fixture(scope="module")
def platform(settings):
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    return TestClient(platform._gateway.app)


def _make_token(
    settings: Settings, user_id: int, email: str, role: str, company_id: int | None = None
) -> str:
    """Create a JWT token with optional company_id claim."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + 3600,
    }
    if company_id is not None:
        payload["company_id"] = company_id
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture(scope="module")
def company_a_token(settings) -> str:
    """Token for user in company 1."""
    return _make_token(
        settings, user_id=101, email="usera@company-a.com", role="owner", company_id=1
    )


@pytest.fixture(scope="module")
def company_b_token(settings) -> str:
    """Token for user in company 2."""
    return _make_token(
        settings, user_id=102, email="userb@company-b.com", role="owner", company_id=2
    )


@pytest.fixture(scope="module")
def admin_token(settings) -> str:
    """Token for platform_admin (no company constraint)."""
    return _make_token(settings, user_id=100, email="admin@platform.com", role="platform_admin")


@pytest.fixture(scope="module")
def no_company_token(settings) -> str:
    """Token for user with no company_id."""
    return _make_token(settings, user_id=103, email="orphan@example.com", role="owner")


# ---------------------------------------------------------------------------
# 1. Unauthenticated requests are rejected
# ---------------------------------------------------------------------------


class TestUnauthenticatedRejection:
    """Unauthenticated requests to company-scoped endpoints return 401."""

    def test_profile_requires_auth(self, client: TestClient):
        """GET /profile/{company_id} without token returns 401."""
        resp = client.get("/profile/1")
        assert resp.status_code == 401

    def test_compliance_status_requires_auth(self, client: TestClient):
        """GET /compliance/status/{company_id} without token returns 401."""
        resp = client.get("/compliance/status/1")
        assert resp.status_code == 401

    def test_compliance_check_requires_auth(self, client: TestClient):
        """POST /compliance/check without token returns 401."""
        resp = client.post("/compliance/check", json={"company_id": 1})
        assert resp.status_code == 401

    def test_advisory_query_requires_auth(self, client: TestClient):
        """POST /advisory/query without token returns 401."""
        resp = client.post("/advisory/query", json={"query": "test", "company_id": 1})
        assert resp.status_code == 401

    def test_document_generate_requires_auth(self, client: TestClient):
        """POST /document/generate without token returns 401."""
        resp = client.post("/document/generate", json={"template_id": 1, "company_id": 1})
        assert resp.status_code == 401

    def test_kb_acts_requires_auth(self, client: TestClient):
        """GET /kb/acts without token returns 401."""
        resp = client.get("/kb/acts")
        assert resp.status_code == 401

    def test_kb_domains_requires_auth(self, client: TestClient):
        """GET /kb/domains without token returns 401."""
        resp = client.get("/kb/domains")
        assert resp.status_code == 401

    def test_document_templates_requires_auth(self, client: TestClient):
        """GET /document/templates without token returns 401."""
        resp = client.get("/document/templates")
        assert resp.status_code == 401

    def test_document_template_by_id_requires_auth(self, client: TestClient):
        """GET /document/templates/1 without token returns 401."""
        resp = client.get("/document/templates/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Tenant isolation on profile endpoints
# ---------------------------------------------------------------------------


class TestProfileTenantIsolation:
    """Company profile endpoints enforce tenant isolation."""

    def test_user_can_access_own_company_profile(self, client: TestClient, company_a_token: str):
        """User in company 1 can access GET /profile/1."""
        resp = client.get(
            "/profile/1",
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 200

    def test_user_cannot_access_other_company_profile(
        self, client: TestClient, company_a_token: str
    ):
        """User in company 1 cannot access GET /profile/2."""
        resp = client.get(
            "/profile/2",
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_user_cannot_access_other_company_workforce(
        self, client: TestClient, company_a_token: str
    ):
        """User in company 1 cannot access GET /profile/2/workforce."""
        resp = client.get(
            "/profile/2/workforce",
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_user_cannot_update_other_company_profile(
        self, client: TestClient, company_a_token: str
    ):
        """User in company 1 cannot PUT /profile/2."""
        resp = client.put(
            "/profile/2",
            json={"name": "Hacked Company"},
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_access_any_company_profile(self, client: TestClient, admin_token: str):
        """platform_admin can access GET /profile/1 and GET /profile/2."""
        resp1 = client.get(
            "/profile/1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp1.status_code == 200

        resp2 = client.get(
            "/profile/2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# 3. Tenant isolation on compliance endpoints
# ---------------------------------------------------------------------------


class TestComplianceTenantIsolation:
    """Compliance endpoints enforce tenant isolation."""

    def test_user_can_check_own_company_compliance(self, client: TestClient, company_a_token: str):
        """User in company 1 can POST /compliance/check with company_id=1."""
        resp = client.post(
            "/compliance/check",
            json={"company_id": 1, "domains": ["employment_act"]},
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 200

    def test_user_cannot_check_other_company_compliance(
        self, client: TestClient, company_a_token: str
    ):
        """User in company 1 cannot POST /compliance/check with company_id=2."""
        resp = client.post(
            "/compliance/check",
            json={"company_id": 2, "domains": ["employment_act"]},
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_user_cannot_view_other_company_compliance_status(
        self, client: TestClient, company_a_token: str
    ):
        """User in company 1 cannot GET /compliance/status/2."""
        resp = client.get(
            "/compliance/status/2",
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_user_cannot_gap_analyse_other_company(self, client: TestClient, company_a_token: str):
        """User in company 1 cannot POST /compliance/gap-analysis for company_id=2."""
        resp = client.post(
            "/compliance/gap-analysis",
            json={"company_id": 2},
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_check_any_company_compliance(self, client: TestClient, admin_token: str):
        """platform_admin can POST /compliance/check for any company."""
        resp = client.post(
            "/compliance/check",
            json={"company_id": 999, "domains": ["cpf"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. Tenant isolation on advisory endpoints
# ---------------------------------------------------------------------------


class TestAdvisoryTenantIsolation:
    """Advisory endpoints enforce tenant isolation."""

    def test_user_can_query_own_company(self, client: TestClient, company_a_token: str):
        """User in company 1 can POST /advisory/query with company_id=1."""
        resp = client.post(
            "/advisory/query",
            json={"query": "What are the CPF contribution rates?", "company_id": 1},
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 200

    def test_user_cannot_query_other_company(self, client: TestClient, company_a_token: str):
        """User in company 1 cannot POST /advisory/query with company_id=2."""
        resp = client.post(
            "/advisory/query",
            json={"query": "What are the CPF rates?", "company_id": 2},
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_user_can_query_without_company_id(self, client: TestClient, company_a_token: str):
        """User can POST /advisory/query without specifying company_id (general query)."""
        resp = client.post(
            "/advisory/query",
            json={"query": "What are the CPF contribution rates?"},
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. Tenant isolation on document endpoints
# ---------------------------------------------------------------------------


class TestDocumentTenantIsolation:
    """Document endpoints enforce tenant isolation."""

    def test_user_cannot_generate_doc_for_other_company(
        self, client: TestClient, company_a_token: str
    ):
        """User in company 1 cannot POST /document/generate with company_id=2."""
        resp = client.post(
            "/document/generate",
            json={
                "template_id": 1,
                "company_id": 2,
                "fields": {
                    "company_name": "Test",
                    "employee_name": "Test",
                    "position": "Test",
                    "start_date": "2026-01-01",
                    "salary": "5000",
                    "probation_months": "3",
                    "annual_leave_days": "14",
                    "sick_leave_days": "14",
                    "notice_period": "1 month",
                },
            },
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_user_can_generate_doc_for_own_company(self, client: TestClient, company_a_token: str):
        """User in company 1 can POST /document/generate with company_id=1."""
        resp = client.post(
            "/document/generate",
            json={
                "template_id": 1,
                "company_id": 1,
                "fields": {
                    "company_name": "Test Co",
                    "company_uen": "202400001A",
                    "company_address": "1 Test Road",
                    "employee_name": "John Doe",
                    "nric_fin": "S1234567A",
                    "job_title": "Engineer",
                    "department": "Engineering",
                    "start_date": "2026-01-01",
                    "basic_monthly_salary": "5000",
                    "salary_period": "Monthly",
                },
            },
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 6. Cross-tenant data leakage prevention
# ---------------------------------------------------------------------------


class TestCrossTenantLeakage:
    """Verify that responses never leak data from other tenants."""

    def test_company_b_cannot_see_company_a_profile(
        self, client: TestClient, company_a_token: str, company_b_token: str
    ):
        """User B cannot read company A's profile, and vice versa."""
        # A accesses own profile - OK
        resp_a = client.get(
            "/profile/1",
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp_a.status_code == 200

        # B cannot access A's company
        resp_b = client.get(
            "/profile/1",
            headers={"Authorization": f"Bearer {company_b_token}"},
        )
        assert resp_b.status_code == 403

        # B accesses own company - OK
        resp_b_own = client.get(
            "/profile/2",
            headers={"Authorization": f"Bearer {company_b_token}"},
        )
        assert resp_b_own.status_code == 200

    def test_user_without_company_cannot_access_company_data(
        self, client: TestClient, no_company_token: str
    ):
        """A user with no company_id in their token cannot access any company profile."""
        resp = client.get(
            "/profile/1",
            headers={"Authorization": f"Bearer {no_company_token}"},
        )
        assert resp.status_code == 403

    def test_document_history_filtered_by_tenant(
        self, client: TestClient, company_a_token: str, company_b_token: str
    ):
        """Document history endpoint filters by user's company."""
        # User A requests history for company 2 -- should be denied
        resp = client.get(
            "/document/history?company_id=2",
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert resp.status_code == 403

    def test_cross_tenant_document_download_rejected(
        self, client: TestClient, company_a_token: str, company_b_token: str
    ):
        """User B cannot download a document generated by User A's company.

        Flow: User A generates a document for company_id=1, then User B
        (company_id=2) tries to download it via /document/download/{id}.
        The server must return 403.
        """
        # User A generates a document for company 1
        gen_resp = client.post(
            "/document/generate",
            json={
                "template_id": 1,
                "company_id": 1,
                "fields": {
                    "company_name": "Company A Ltd",
                    "company_uen": "202400001A",
                    "company_address": "1 Alpha Road",
                    "employee_name": "Alice A",
                    "nric_fin": "S1234567A",
                    "job_title": "Engineer",
                    "department": "Engineering",
                    "start_date": "2026-01-01",
                    "basic_monthly_salary": "5000",
                    "salary_period": "Monthly",
                },
            },
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert gen_resp.status_code == 200, f"Document generation failed: {gen_resp.text}"
        document_id = gen_resp.json()["document_id"]

        # User A can download their own document
        dl_a = client.get(
            f"/document/download/{document_id}",
            headers={"Authorization": f"Bearer {company_a_token}"},
        )
        assert dl_a.status_code == 200, "Owner should be able to download their own document"

        # User B (company 2) tries to download User A's document -- must be rejected
        dl_b = client.get(
            f"/document/download/{document_id}",
            headers={"Authorization": f"Bearer {company_b_token}"},
        )
        assert dl_b.status_code == 403, (
            "Cross-tenant document download must be rejected with 403, "
            f"but got {dl_b.status_code}"
        )
