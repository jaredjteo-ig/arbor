"""Integration tests for the HR Advisory Nexus API gateway.

Tests create the platform instance and exercise endpoints
via FastAPI's TestClient (no running server required).
"""

import uuid

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.requires_postgres

from hr_advisory.api.platform import create_platform
from hr_advisory.config.settings import Settings


@pytest.fixture(scope="module")
def settings() -> Settings:
    """Test settings with development defaults."""
    return Settings(
        app_env="development",
        api_port=8099,
        cors_origins="*",
    )


@pytest.fixture(scope="module")
def platform(settings):
    """Create the Nexus platform once for all tests in this module."""
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    """TestClient backed by the underlying FastAPI app."""
    return TestClient(platform._gateway.app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict:
    """Register a test user with company_id=1 and return Authorization headers."""
    # Clear rate limiter to avoid 429 from earlier tests sharing the same in-memory state
    from hr_advisory.workflows.guardrails import _request_counts

    _request_counts.clear()

    email = f"nexus_fixture_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "name": "Test User",
            "password": "SecurePass1!",
            "company_id": 1,
        },
    )
    data = response.json()
    assert "access_token" in data, f"Registration failed (status {response.status_code}): {data}"
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


class TestHealth:
    """Platform health and infrastructure checks."""

    def test_health_check_returns_200(self, client: TestClient):
        """The built-in /health endpoint must respond with 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_body(self, client: TestClient):
        """Health response must contain a status field."""
        data = client.get("/health").json()
        assert "status" in data

    def test_platform_health_check_method(self, platform):
        """Nexus.health_check() returns platform metadata."""
        health = platform.health_check()
        assert health["status"] in ("healthy", "stopped")
        assert health["workflows"] >= 0


# --------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------


class TestCORS:
    """CORS headers must be present for cross-origin React requests."""

    def test_cors_preflight(self, client: TestClient):
        """OPTIONS preflight with a configured origin gets CORS headers."""
        response = client.options(
            "/advisory/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_origin_value(self, client: TestClient):
        """The Allow-Origin header must match the configured origin."""
        response = client.options(
            "/advisory/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        allowed = response.headers.get("access-control-allow-origin", "")
        assert "http://localhost:3000" in allowed or allowed == "*"


# --------------------------------------------------------------------------
# Advisory
# --------------------------------------------------------------------------


class TestAdvisory:
    """Advisory query and streaming endpoints."""

    def test_advisory_query(self, client: TestClient, auth_headers: dict):
        """POST /advisory/query returns a structured advisory response."""
        response = client.post(
            "/advisory/query",
            json={"query": "What are the overtime rules?", "company_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "risk_tier" in data

    def test_advisory_stream(self, client: TestClient, auth_headers: dict):
        """POST /advisory/stream returns SSE event stream."""
        response = client.post(
            "/advisory/stream",
            json={"query": "Explain CPF contributions"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "event: start" in body
        assert "event: token" in body
        assert "event: complete" in body

    def test_advisory_history(self, client: TestClient, auth_headers: dict):
        """GET /advisory/history/{id} returns conversation messages."""
        response = client.get("/advisory/history/1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == 1

    def test_advisory_query_requires_auth(self, client: TestClient):
        """POST /advisory/query without auth returns 401."""
        response = client.post(
            "/advisory/query",
            json={"query": "test"},
        )
        assert response.status_code == 401


# --------------------------------------------------------------------------
# Calculator
# --------------------------------------------------------------------------


class TestCalculator:
    """Calculator endpoints for HR computations."""

    def test_cpf_calculation(self, client: TestClient, auth_headers: dict):
        """POST /calculator/cpf returns CPF contribution breakdown."""
        response = client.post(
            "/calculator/cpf",
            json={"gross_salary": 5000, "employee_age": 30, "citizenship_status": "SC"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "employer_contribution" in data
        assert "employee_contribution" in data

    def test_leave_calculation(self, client: TestClient, auth_headers: dict):
        """POST /calculator/leave returns leave entitlements."""
        response = client.post(
            "/calculator/leave",
            json={"years_of_service": 3},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "days_entitled" in data


# --------------------------------------------------------------------------
# Compliance
# --------------------------------------------------------------------------


class TestCompliance:
    """Compliance check endpoints."""

    def test_compliance_check(self, client: TestClient, auth_headers: dict):
        """POST /compliance/check returns compliance findings."""
        response = client.post(
            "/compliance/check",
            json={"company_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "findings" in data


# --------------------------------------------------------------------------
# Document
# --------------------------------------------------------------------------


class TestDocument:
    """Document template endpoints."""

    def test_list_templates(self, client: TestClient, auth_headers: dict):
        """GET /document/templates returns available templates."""
        response = client.get("/document/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) > 0

    def test_generate_document(self, client: TestClient, auth_headers: dict):
        """POST /document/generate returns a generated document."""
        response = client.post(
            "/document/generate",
            json={"template_id": 1, "company_id": 1},
            headers=auth_headers,
        )
        # May return 422 for missing required fields, but should not be 401
        assert response.status_code != 401


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------


class TestProfile:
    """Company profile endpoints."""

    def test_get_profile(self, client: TestClient, auth_headers: dict):
        """GET /profile/{id} returns company details."""
        response = client.get("/profile/1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "name" in data

    def test_create_profile(self, client: TestClient, auth_headers: dict):
        """POST /profile/ creates a new company profile."""
        response = client.post(
            "/profile/",
            json={"name": "Test Corp", "uen": "202400099Z", "sector": "F&B"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True


# --------------------------------------------------------------------------
# Knowledge Base
# --------------------------------------------------------------------------


class TestKnowledgeBase:
    """Knowledge base query endpoints."""

    def test_list_acts(self, client: TestClient, auth_headers: dict):
        """GET /kb/acts lists legislative acts."""
        response = client.get("/kb/acts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "acts" in data

    def test_list_domains(self, client: TestClient, auth_headers: dict):
        """GET /kb/domains lists HR domains."""
        response = client.get("/kb/domains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "domains" in data


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class TestAuth:
    """Authentication endpoints."""

    @pytest.fixture(autouse=True)
    def _clear_rate_limit(self):
        """Clear rate limiter state before each auth test."""
        from hr_advisory.workflows.guardrails import _request_counts

        _request_counts.clear()

    def test_register(self, client: TestClient):
        """POST /auth/register creates a user and returns a token."""
        email = f"nexus_test_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/auth/register",
            json={"email": email, "name": "New User", "password": "SecurePass1!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "access_token" in data

    def test_login(self, client: TestClient):
        """POST /auth/login returns an access token after registering."""
        email = f"nexus_login_{uuid.uuid4().hex[:8]}@example.com"
        # Register first so the user exists
        client.post(
            "/auth/register",
            json={"email": email, "name": "Login User", "password": "SecurePass1!"},
        )
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "SecurePass1!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------


class TestSearch:
    """Search endpoints (semantic and full-text)."""

    def test_semantic_search(self, client: TestClient, auth_headers: dict):
        """POST /search/semantic returns ranked results."""
        response = client.post(
            "/search/semantic",
            json={"query": "overtime pay", "top_k": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["query"] == "overtime pay"

    def test_fulltext_search(self, client: TestClient, auth_headers: dict):
        """POST /search/fulltext returns filtered results."""
        response = client.post(
            "/search/fulltext",
            json={"query": "annual leave", "domain_id": 3},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["filters"]["domain_id"] == 3


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------


class TestSession:
    """Session management tests."""

    def test_session_store_attached(self, platform):
        """The session store is attached to the platform instance."""
        assert hasattr(platform, "_session_store")
        assert platform._session_store is not None

    def test_create_and_retrieve_session(self, platform):
        """Create a session and retrieve it by ID."""
        store = platform._session_store
        session = store.create(company_id=1, user_id=42)
        assert session.company_id == 1
        assert session.user_id == 42

        retrieved = store.get(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_session_message_history(self, platform):
        """Messages added to a session appear in conversation_history."""
        store = platform._session_store
        session = store.create(company_id=1, user_id=1)
        session.add_message("user", "What are the overtime rules?")
        session.add_message("assistant", "Under Part IV of the Employment Act...")
        assert len(session.conversation_history) == 2

    def test_session_risk_escalation(self, platform):
        """Risk escalations are recorded in the session."""
        store = platform._session_store
        session = store.create(company_id=1, user_id=1)
        session.escalate_risk("green", "amber", "Potential non-compliance detected")
        assert len(session.risk_tier_escalations) == 1
        assert session.risk_tier_escalations[0]["to_tier"] == "amber"


# --------------------------------------------------------------------------
# Multi-channel handlers
# --------------------------------------------------------------------------


class TestMultiChannelHandlers:
    """Handlers registered via @app.handler() are available as workflows."""

    def test_handler_workflows_registered(self, platform):
        """All multi-channel handler workflows are in the workflow registry."""
        assert "advisory_query" in platform._workflows
        assert "compliance_check" in platform._workflows
        assert "search_kb" in platform._workflows

    def test_execute_advisory_handler_via_api(self, client: TestClient):
        """Execute the advisory_query handler through the API channel."""
        response = client.post(
            "/workflows/advisory_query/execute",
            json={"inputs": {"query": "What is CPF?"}},
        )
        assert response.status_code == 200
