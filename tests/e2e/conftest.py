"""E2E test configuration and fixtures (T058).

Provides Playwright fixtures and helpers for comprehensive
end-to-end testing of the Arbor HR advisory platform.

Test coverage:
- Onboarding flow
- Advisory Q&A
- All calculators (CPF, leave, quota/levy)
- Document generation
- Compliance check
- Emergency flow
- Multi-client switching
- Admin operations

Uses real API server (no mocks for Tier 3 testing).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest


@dataclass
class TestConfig:
    """E2E test configuration."""

    base_url: str
    api_url: str
    timeout_ms: int
    headless: bool
    slow_mo: int  # milliseconds between actions


def get_test_config() -> TestConfig:
    """Get E2E test configuration from environment."""
    return TestConfig(
        base_url=os.environ.get("E2E_BASE_URL", "http://localhost:3000"),
        api_url=os.environ.get("E2E_API_URL", "http://localhost:8000"),
        timeout_ms=int(os.environ.get("E2E_TIMEOUT_MS", "30000")),
        headless=os.environ.get("E2E_HEADLESS", "true").lower() == "true",
        slow_mo=int(os.environ.get("E2E_SLOW_MO", "0")),
    )


# ── Test user fixtures ──────────────────────────────────────


@dataclass
class TestUser:
    """A test user for E2E scenarios."""

    email: str
    password: str
    company_name: str
    sector: str
    employee_count: int
    persona: str  # A (new employer), B (growing SME), C (consultant), D (employee)


TEST_USERS = {
    "persona_a": TestUser(
        email="test_new_employer@example.com",
        password="TestPass123!",
        company_name="Fresh Start Pte Ltd",
        sector="Technology",
        employee_count=3,
        persona="A",
    ),
    "persona_b": TestUser(
        email="test_growing_sme@example.com",
        password="TestPass123!",
        company_name="Growing SME Pte Ltd",
        sector="F&B",
        employee_count=25,
        persona="B",
    ),
    "persona_c": TestUser(
        email="test_consultant@example.com",
        password="TestPass123!",
        company_name="HR Advisory Consulting",
        sector="Professional Services",
        employee_count=5,
        persona="C",
    ),
    "persona_d": TestUser(
        email="test_employee@example.com",
        password="TestPass123!",
        company_name="Employee Check Corp",
        sector="Retail",
        employee_count=50,
        persona="D",
    ),
}


@pytest.fixture
def test_config() -> TestConfig:
    """Provide test configuration."""
    return get_test_config()


@pytest.fixture(params=["persona_a", "persona_b", "persona_c", "persona_d"])
def test_user(request: pytest.FixtureRequest) -> TestUser:
    """Provide test users (parameterised across all personas)."""
    return TEST_USERS[request.param]
