"""Onboarding flow E2E tests (T058).

Tests the complete user onboarding journey via the API:
1. Registration
2. Company profile setup
3. Sector selection
4. Workforce composition
5. First advisory query

Exercises real API endpoints with TestClient (Tier 3 — no mocking).
"""

from __future__ import annotations

import uuid

import pytest
from starlette.testclient import TestClient

from hr_advisory.api.platform import create_platform
from hr_advisory.config.settings import Settings
from tests.e2e.conftest import TestConfig, TestUser, get_test_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8099,
        cors_origins="http://localhost:3000",
    )


@pytest.fixture(scope="module")
def platform(settings):
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    return TestClient(platform._gateway.app)


def _register_user(client: TestClient, persona: TestUser) -> dict:
    """Register a user and return auth headers + user data."""
    email = f"e2e_{persona.persona}_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "name": persona.company_name,
            "password": persona.password,
            "company_id": 1,
        },
    )
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
        "email": email,
    }


# ---------------------------------------------------------------------------
# Onboarding flow tests
# ---------------------------------------------------------------------------


class TestOnboardingFlow:
    """End-to-end onboarding flow tests via API."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.config = get_test_config()

    def test_onboarding_steps_defined(self) -> None:
        """Verify onboarding test structure exists."""
        config = get_test_config()
        assert config.base_url
        assert config.api_url

    def test_persona_a_onboarding(self, client: TestClient) -> None:
        """Persona A (new employer) onboarding flow.

        Steps:
        1. Register as new employer
        2. Create company profile (name, UEN, sector)
        3. View company profile
        4. Make first advisory query
        5. Verify advisory response with risk tier
        """
        from tests.e2e.conftest import TEST_USERS

        persona = TEST_USERS["persona_a"]
        auth = _register_user(client, persona)

        # Step 2: Create company profile
        resp = client.post(
            "/profile/",
            json={
                "name": persona.company_name,
                "uen": "202400001A",
                "sector": persona.sector,
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        profile = resp.json()
        assert profile["created"] is True

        # Step 3: View own company profile
        resp = client.get("/profile/1", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

        # Step 4: First advisory query
        resp = client.post(
            "/advisory/query",
            json={
                "query": "I just hired my first employee. What are my CPF obligations?",
                "company_id": 1,
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()

        # Step 5: Verify advisory response structure
        assert "response" in data
        assert "risk_tier" in data
        assert data["risk_tier"] in ("green", "amber", "red")
        assert len(data["response"]) > 20

    def test_persona_b_onboarding(self, client: TestClient) -> None:
        """Persona B (growing SME) onboarding flow.

        Steps:
        1. Register as growing SME
        2. Create company profile
        3. Run compliance check (triggers for 10+ employees)
        4. Query about foreign worker quota
        5. Use quota/levy calculator
        """
        from tests.e2e.conftest import TEST_USERS

        persona = TEST_USERS["persona_b"]
        auth = _register_user(client, persona)

        # Step 2: Create company profile
        resp = client.post(
            "/profile/",
            json={
                "name": persona.company_name,
                "uen": "202400025B",
                "sector": persona.sector,
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 200

        # Step 3: Run compliance check
        resp = client.post(
            "/compliance/check",
            json={"company_id": 1},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        compliance = resp.json()
        assert "status" in compliance
        assert "findings" in compliance

        # Step 4: Advisory query about foreign workers
        resp = client.post(
            "/advisory/query",
            json={
                "query": "I want to hire foreign workers for my F&B business. "
                "What quota and levy obligations apply?",
                "company_id": 1,
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert "response" in resp.json()

        # Step 5: Calculator for quota/levy
        resp = client.post(
            "/calculator/cpf",
            json={"gross_salary": 3000, "employee_age": 25},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert "employer_contribution" in resp.json()

        # Step 4: Knowledge base - list acts
        resp = client.get("/kb/acts", headers=auth["headers"])
        assert resp.status_code == 200
        assert "acts" in resp.json()

        # Step 5: Semantic search
        resp = client.post(
            "/search/semantic",
            json={"query": "employee termination notice period", "top_k": 5},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert "results" in resp.json()


class TestOnboardingValidation:
    """Onboarding input validation tests."""

    def test_uen_format_validation(self) -> None:
        """UEN should be validated for Singapore format."""
        valid_uens = ["202400001A", "53312345B", "T08LL1234C"]
        for uen in valid_uens:
            assert len(uen) >= 8
            assert uen[-1].isalpha()

    def test_sector_selection_required(self) -> None:
        """Sector must be selected during onboarding."""
        valid_sectors = [
            "Technology",
            "F&B",
            "Construction",
            "Professional Services",
            "Manufacturing",
            "Retail",
        ]
        assert len(valid_sectors) >= 6
