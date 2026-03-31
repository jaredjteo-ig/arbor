"""Registration flow E2E tests — M60 atomic user + company creation.

Tests the POST /auth/register endpoint end-to-end via FastAPI TestClient
(Tier 3, no mocking). Covers:

    1. Register with company_name → user.company_id is not null
    2. Register without company_name → user.company_id is null (backward compat)
    3. Login after registration with company → company_id matches
    4. Duplicate email → 409 Conflict
    5. CPF calculator NaN rejection → 400 or 422

The TestClient exercises the full application stack: FastAPI router →
AuthService → DataFlow DataModel → SQLite file DB (when PostgreSQL is
unavailable) or PostgreSQL (when running in CI with a live database).

Database selection: The tests prefer PostgreSQL (production parity) but fall
back to a temporary SQLite file when PostgreSQL is unreachable at localhost:5432.
The DATABASE_URL env var is set before any imports so that the Settings
dataclass and the cached get_settings() use the test database.

CSRF note: The Nexus SAAS preset enables CSRF validation via Origin/Referer
header checking. The TestClient does not inject browser headers automatically,
so all state-changing requests include `Origin: http://localhost:3000` — the
configured allowed origin — to satisfy the CSRFMiddleware.
"""

from __future__ import annotations

import os
import socket
import tempfile
import uuid

import pytest
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Database selection — must happen BEFORE any hr_advisory imports so that
# the Settings dataclass (which calls load_dotenv at module import time) and
# the cached get_settings() both pick up the correct DATABASE_URL.
# ---------------------------------------------------------------------------

_POSTGRES_HOST = "localhost"
_POSTGRES_PORT = 5432


def _postgres_reachable() -> bool:
    try:
        with socket.create_connection((_POSTGRES_HOST, _POSTGRES_PORT), timeout=1):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


_POSTGRES_AVAILABLE = _postgres_reachable()

if not _POSTGRES_AVAILABLE:
    # Use a per-run SQLite file in a temp directory.
    # A named file (not :memory:) is required because the Nexus gateway
    # spawns async tasks that open the DB from separate coroutines, and
    # aiosqlite `:memory:` connections are not shared across connections.
    _DB_FILE = tempfile.NamedTemporaryFile(suffix=".db", prefix="arbor_e2e_reg_", delete=False)
    _DB_FILE.close()
    _TEST_DB_URL = f"sqlite:///{_DB_FILE.name}"
    os.environ["DATABASE_URL"] = _TEST_DB_URL

from hr_advisory.api.platform import create_platform  # noqa: E402
from hr_advisory.config.settings import Settings, get_settings  # noqa: E402

# Force clear the cached get_settings() so it picks up our DATABASE_URL,
# even when running after unit tests that may have mocked it.
get_settings.cache_clear()

# The CORS origin configured in Settings must be used as the Origin header
# on all POST/PUT/DELETE requests to pass CSRFMiddleware validation.
_ALLOWED_ORIGIN = "http://localhost:3000"
_CSRF_HEADERS = {"Origin": _ALLOWED_ORIGIN}


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def settings() -> Settings:
    """Use development settings with a dedicated test port and test database."""
    kwargs: dict = {
        "app_env": "development",
        "api_port": 8199,
        "cors_origins": _ALLOWED_ORIGIN,
    }
    if not _POSTGRES_AVAILABLE:
        kwargs["database_url"] = _TEST_DB_URL
    return Settings(**kwargs)


@pytest.fixture(scope="module")
def platform(settings: Settings):
    """Instantiate the full Nexus platform once per module."""
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    """Provide a TestClient wrapping the Nexus gateway."""
    return TestClient(platform._gateway.app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    """Generate a collision-proof email for each test run."""
    return f"e2e_reg_{uuid.uuid4().hex[:12]}@example.com"


def _register(client: TestClient, payload: dict) -> tuple[int, dict]:
    """POST /auth/register with CSRF Origin header; return (status_code, body)."""
    resp = client.post("/auth/register", json=payload, headers=_CSRF_HEADERS)
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


# ---------------------------------------------------------------------------
# Test 1 — Register with company_name returns user with company_id
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_register_with_company_name_sets_company_id(client: TestClient) -> None:
    """POST /auth/register with company_name must return user.company_id != null.

    This is the M60 core requirement: atomic user + company creation so the
    first-time owner immediately has a company linked to their account.
    """
    email = _unique_email()
    status, body = _register(
        client,
        {
            "name": "Test Owner",
            "email": email,
            "password": "TestPass123!",
            "company_name": "Acme Pte Ltd",
        },
    )

    assert status == 200, (
        f"Expected 200 for valid registration with company_name. " f"Got {status}: {body}"
    )
    assert "user" in body, f"Response must contain 'user' key. Got: {body}"
    assert "access_token" in body, f"Response must contain 'access_token'. Got: {body}"
    assert "refresh_token" in body, f"Response must contain 'refresh_token'. Got: {body}"

    user = body["user"]
    assert user.get("company_id") is not None, (
        "user.company_id must be set when company_name is provided at registration. "
        f"Got user={user}"
    )
    assert isinstance(
        user["company_id"], int
    ), f"user.company_id must be an integer. Got: {user['company_id']!r}"
    assert (
        user["company_id"] > 0
    ), f"user.company_id must be a positive integer. Got: {user['company_id']}"

    # State persistence: verify the company_id survives a /auth/me lookup.
    me_resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert (
        me_resp.status_code == 200
    ), f"GET /auth/me failed after registration. Got {me_resp.status_code}: {me_resp.text}"
    me = me_resp.json()
    assert me.get("company_id") == user["company_id"], (
        f"company_id from /auth/me ({me.get('company_id')}) must match "
        f"company_id from registration ({user['company_id']})"
    )


# ---------------------------------------------------------------------------
# Test 2 — Register without company_name still works (backward compat)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_register_without_company_name_backward_compatible(client: TestClient) -> None:
    """POST /auth/register without company_name must succeed with user.company_id == null.

    Pre-M60 registration did not create companies. Users who omit company_name
    (e.g., employees joining via invitation flow later) must still be able to
    register successfully.
    """
    email = _unique_email()
    status, body = _register(
        client,
        {
            "name": "No Company User",
            "email": email,
            "password": "TestPass123!",
            # Deliberately omitting company_name
        },
    )

    assert status == 200, (
        f"Expected 200 for valid registration without company_name. " f"Got {status}: {body}"
    )
    assert "user" in body, f"Response must contain 'user' key. Got: {body}"
    assert "access_token" in body

    user = body["user"]
    assert user.get("company_id") is None, (
        "user.company_id must be null when company_name is omitted. "
        f"Got company_id={user.get('company_id')}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Login after registration with company matches company_id
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_login_after_registration_returns_same_company_id(client: TestClient) -> None:
    """Login after registering with a company must return the same company_id.

    Verifies the full round-trip: register (creates user + company) →
    login (fetches same user from DB) → company_id matches.
    """
    email = _unique_email()
    password = "TestPass123!"

    # Step 1: Register
    reg_status, reg_body = _register(
        client,
        {
            "name": "Login Flow User",
            "email": email,
            "password": password,
            "company_name": "Login Flow Co",
        },
    )
    assert reg_status == 200, f"Registration step failed. Got {reg_status}: {reg_body}"
    reg_company_id = reg_body["user"]["company_id"]
    assert (
        reg_company_id is not None
    ), "Registration must return a non-null company_id for this test to be meaningful."

    # Step 2: Login with the same credentials
    login_resp = client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=_CSRF_HEADERS,
    )
    assert login_resp.status_code == 200, (
        f"Login failed after successful registration. "
        f"Got {login_resp.status_code}: {login_resp.text}"
    )
    login_body = login_resp.json()

    assert "user" in login_body, f"Login response must contain 'user'. Got: {login_body}"
    assert "access_token" in login_body
    login_company_id = login_body["user"].get("company_id")

    assert login_company_id == reg_company_id, (
        f"company_id from login ({login_company_id}) must match "
        f"company_id from registration ({reg_company_id}). "
        "The company link is not persisted across the auth boundary."
    )


# ---------------------------------------------------------------------------
# Test 4 — Duplicate email returns 409
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_duplicate_email_returns_409(client: TestClient) -> None:
    """POST /auth/register with an already-registered email must return 409.

    Prevents silent account collisions. The second registration attempt
    must be rejected with HTTP 409 Conflict, not 200 or 500.
    """
    email = _unique_email()

    # First registration — must succeed
    status1, body1 = _register(
        client,
        {
            "name": "Original User",
            "email": email,
            "password": "TestPass123!",
        },
    )
    assert status1 == 200, f"First registration failed unexpectedly. Got {status1}: {body1}"

    # Second registration with same email — must fail with 409
    status2, body2 = _register(
        client,
        {
            "name": "Duplicate User",
            "email": email,
            "password": "AnotherPass456!",
        },
    )
    assert status2 == 409, (
        f"Expected 409 Conflict for duplicate email. "
        f"Got {status2}: {body2}. "
        "This means duplicate accounts can be silently created."
    )

    # The error detail should mention the email or duplication
    detail = str(body2.get("detail", "")).lower()
    assert any(
        kw in detail for kw in ("already", "duplicate", "registered", "exist")
    ), f"409 error detail should mention duplication. Got detail={body2.get('detail')!r}"


# ---------------------------------------------------------------------------
# Test 5 — CPF calculator NaN rejection
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_cpf_calculator_rejects_nan_monthly_ow(client: TestClient) -> None:
    """POST /calculator/cpf with monthly_ow=NaN must return 400 or 422.

    NaN inputs to the CPF calculator can produce garbage output silently
    (NaN propagates through arithmetic, bypasses range checks, and returns
    a "successful" response with NaN contribution amounts). The endpoint
    must reject NaN at the validation layer.

    The security memory in HRIS notes: "NaN guard — C2" was a red team
    finding. This test is a permanent regression guard for that fix.
    """
    # First, register a user to obtain an auth token (calculator requires auth)
    email = _unique_email()
    reg_status, reg_body = _register(
        client,
        {
            "name": "NaN Tester",
            "email": email,
            "password": "TestPass123!",
        },
    )
    assert reg_status == 200, f"Setup registration failed: {reg_body}"
    token = reg_body["access_token"]
    headers = {"Authorization": f"Bearer {token}", **_CSRF_HEADERS}

    # Attempt CPF calculation with NaN as monthly_ow
    # JSON spec does not support NaN literals — we send the string "NaN"
    # which Python's float("NaN") accepts. The endpoint must reject it.
    nan_payload = {
        "gross_salary": "NaN",
        "employee_age": 30,
        "citizenship_status": "SC",
    }
    resp = client.post("/calculator/cpf", json=nan_payload, headers=headers)

    assert resp.status_code in (400, 422), (
        f"Expected 400 or 422 when monthly_ow=NaN, but got {resp.status_code}. "
        f"Response body: {resp.text}. "
        "NaN inputs must be rejected — they produce garbage CPF contributions."
    )

    # Verify no NaN values leaked into the response
    body_text = resp.text.lower()
    assert "nan" not in body_text or resp.status_code in (
        400,
        422,
    ), "If the endpoint returned 200, it must not contain NaN in the response."


@pytest.mark.e2e
def test_cpf_calculator_rejects_negative_salary(client: TestClient) -> None:
    """POST /calculator/cpf with negative gross_salary must return 422.

    Negative salaries are economically nonsensical and would produce negative
    CPF contributions. The endpoint must reject them with a validation error.
    """
    email = _unique_email()
    reg_status, reg_body = _register(
        client,
        {
            "name": "Negative Salary Tester",
            "email": email,
            "password": "TestPass123!",
        },
    )
    assert reg_status == 200, f"Setup registration failed: {reg_body}"
    token = reg_body["access_token"]
    headers = {"Authorization": f"Bearer {token}", **_CSRF_HEADERS}

    resp = client.post(
        "/calculator/cpf",
        json={
            "gross_salary": -1000,
            "employee_age": 30,
            "citizenship_status": "SC",
        },
        headers=headers,
    )

    assert resp.status_code in (
        400,
        422,
    ), f"Expected 400 or 422 for negative salary. Got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Supplementary: validate auth token structure (JWT shape)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_registration_tokens_are_non_empty_strings(client: TestClient) -> None:
    """access_token and refresh_token from registration must be non-empty strings.

    Guards against regressions where token generation silently fails and
    the endpoint returns empty-string tokens that will fail all downstream
    auth checks.
    """
    email = _unique_email()
    status, body = _register(
        client,
        {
            "name": "Token Shape User",
            "email": email,
            "password": "TestPass123!",
            "company_name": "Token Test Co",
        },
    )
    assert status == 200, f"Registration failed: {body}"

    access_token = body.get("access_token", "")
    refresh_token = body.get("refresh_token", "")

    assert (
        isinstance(access_token, str) and len(access_token) > 20
    ), f"access_token must be a non-trivial string. Got: {access_token!r}"
    assert (
        isinstance(refresh_token, str) and len(refresh_token) > 20
    ), f"refresh_token must be a non-trivial string. Got: {refresh_token!r}"

    # JWT tokens have exactly 3 dot-separated segments
    assert (
        access_token.count(".") == 2
    ), f"access_token does not look like a JWT (expected 2 dots). Got: {access_token[:50]}..."
    assert (
        refresh_token.count(".") == 2
    ), f"refresh_token does not look like a JWT (expected 2 dots). Got: {refresh_token[:50]}..."


# ---------------------------------------------------------------------------
# Supplementary: whitespace-only company_name is treated as absent
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_whitespace_company_name_treated_as_no_company(client: TestClient) -> None:
    """A company_name consisting only of whitespace must be treated as absent.

    The router strips and null-checks the value: `company_name.strip() or None`.
    This test verifies that "   " does not create a blank-named company.
    """
    email = _unique_email()
    status, body = _register(
        client,
        {
            "name": "Whitespace Co User",
            "email": email,
            "password": "TestPass123!",
            "company_name": "   ",
        },
    )

    assert status == 200, f"Registration with whitespace company_name failed: {body}"
    user = body.get("user", {})
    assert user.get("company_id") is None, (
        "Whitespace-only company_name must not create a company. "
        f"Got company_id={user.get('company_id')}"
    )
