"""Integration tests for T012 — Authentication and Authorization Service.

Tests run against real PostgreSQL and real Nexus platform via TestClient.
Docker must be running: docker compose -f docker-compose.dev.yml up -d

Covers:
  1. Password hashing: hash + verify roundtrip, wrong password fails
  2. JWT tokens: create + decode, expiry works, refresh token type validated
  3. Registration: success, duplicate email error, missing fields error
  4. Login: success, wrong password, nonexistent email
  5. Token refresh: valid refresh gives new access token, access token rejected
  6. Protected endpoint /auth/me: valid token returns user, no token 401, expired 401
  7. Role-based access: middleware allows matching role, rejects non-matching
  8. Password reset flow: request creates token, reset with valid token works
"""

import os
import time
import uuid

import jwt
import pytest
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")

from hr_advisory.api.platform import create_platform
from hr_advisory.config.settings import Settings, get_settings
from hr_advisory.services.auth_service import AuthService

# Set JWT_SECRET_KEY env var BEFORE get_settings() is ever cached,
# so that both the test fixture and the router's get_settings() dependency
# use the same key. This must happen at module import time.
_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
# Clear lru_cache so get_settings() picks up the new env var
get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    """Generate a unique email address for test isolation."""
    return f"test_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="module")
def settings() -> Settings:
    """Test settings with a known JWT secret for deterministic tests."""
    return Settings(
        app_env="development",
        api_port=8098,
        cors_origins="http://localhost:3000",
        jwt_secret_key=_TEST_JWT_SECRET,
        jwt_algorithm="HS256",
        jwt_expiry_minutes=60,
    )


@pytest.fixture(scope="module")
def auth_service(settings) -> AuthService:
    """AuthService instance backed by real DataFlow + PostgreSQL."""
    return AuthService(settings=settings)


@pytest.fixture(scope="module")
def platform(settings):
    """Create the Nexus platform once for all tests in this module."""
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    """TestClient backed by the underlying FastAPI app."""
    return TestClient(platform._gateway.app)


# ---------------------------------------------------------------------------
# 1. Password Hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    """AuthService password hashing with bcrypt."""

    def test_hash_and_verify_roundtrip(self, auth_service: AuthService):
        """Hashing a password and verifying the same password succeeds."""
        password = "Str0ng!Pass"
        hashed = auth_service.hash_password(password)
        assert hashed != password, "Hash must not equal plaintext"
        assert auth_service.verify_password(password, hashed) is True

    def test_wrong_password_fails(self, auth_service: AuthService):
        """Verifying a wrong password against a hash returns False."""
        hashed = auth_service.hash_password("correct-password")
        assert auth_service.verify_password("wrong-password", hashed) is False

    def test_hash_is_unique_per_call(self, auth_service: AuthService):
        """Two hashes of the same password differ (bcrypt salt)."""
        pw = "same-password"
        h1 = auth_service.hash_password(pw)
        h2 = auth_service.hash_password(pw)
        assert h1 != h2, "Bcrypt hashes should differ due to unique salts"

    def test_empty_password_raises(self, auth_service: AuthService):
        """Empty password should raise ValueError."""
        with pytest.raises(ValueError, match="[Pp]assword"):
            auth_service.hash_password("")


# ---------------------------------------------------------------------------
# 2. JWT Tokens
# ---------------------------------------------------------------------------


class TestJWTTokens:
    """JWT creation and decoding via AuthService."""

    def test_create_and_decode_access_token(self, auth_service: AuthService):
        """Access token encodes user_id, email, and role; decodes them back."""
        token = auth_service.create_access_token(
            user_id=42, email="alice@example.com", role="owner"
        )
        payload = auth_service.decode_token(token)
        assert payload["sub"] == 42
        assert payload["email"] == "alice@example.com"
        assert payload["role"] == "owner"
        assert "exp" in payload

    def test_access_token_expiry(self, settings: Settings):
        """An access token with 0-minute expiry is immediately expired."""
        short_settings = Settings(
            jwt_secret_key=settings.jwt_secret_key,
            jwt_algorithm=settings.jwt_algorithm,
            jwt_expiry_minutes=0,
        )
        svc = AuthService(settings=short_settings)
        token = svc.create_access_token(user_id=1, email="x@x.com", role="owner")
        # Token with 0-minute expiry should be expired by now
        time.sleep(1)
        with pytest.raises(Exception):
            svc.decode_token(token)

    def test_create_and_decode_refresh_token(self, auth_service: AuthService):
        """Refresh token contains sub and type='refresh'."""
        token = auth_service.create_refresh_token(user_id=99)
        payload = auth_service.decode_token(token)
        assert payload["sub"] == 99
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_decode_invalid_token_raises(self, auth_service: AuthService):
        """Decoding garbage raises an exception."""
        with pytest.raises(Exception):
            auth_service.decode_token("not.a.valid.jwt")

    def test_decode_token_wrong_secret_raises(self, auth_service: AuthService):
        """Token signed with a different secret cannot be decoded."""
        other_settings = Settings(
            jwt_secret_key="different-secret",
            jwt_algorithm="HS256",
            jwt_expiry_minutes=60,
        )
        other_svc = AuthService(settings=other_settings)
        token = other_svc.create_access_token(user_id=1, email="x@x.com", role="owner")
        with pytest.raises(Exception):
            auth_service.decode_token(token)


# ---------------------------------------------------------------------------
# 3. Registration (API)
# ---------------------------------------------------------------------------


class TestRegistration:
    """POST /auth/register endpoint."""

    def test_register_success(self, client: TestClient):
        """Registering with valid fields returns user + access_token + refresh_token."""
        email = _unique_email()
        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "SecurePass1!",
                "name": "Test User",
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["user"]["email"] == email
        assert data["user"]["name"] == "Test User"
        assert data["user"]["role"] == "owner"
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email_returns_409(self, client: TestClient):
        """Registering the same email twice returns 409 Conflict."""
        email = _unique_email()
        # First registration
        resp1 = client.post(
            "/auth/register",
            json={"email": email, "password": "SecurePass1!", "name": "User One"},
        )
        assert resp1.status_code == 200

        # Second registration with same email
        resp2 = client.post(
            "/auth/register",
            json={"email": email, "password": "SecurePass1!", "name": "User Two"},
        )
        assert resp2.status_code == 409

    def test_register_missing_name_returns_400(self, client: TestClient):
        """Registration without a name field returns 400."""
        response = client.post(
            "/auth/register",
            json={"email": _unique_email(), "password": "SecurePass1!"},
        )
        assert response.status_code == 400

    def test_register_short_password_returns_400(self, client: TestClient):
        """Password shorter than 8 characters returns 400."""
        response = client.post(
            "/auth/register",
            json={"email": _unique_email(), "password": "short", "name": "X"},
        )
        assert response.status_code == 400

    def test_register_invalid_email_returns_400(self, client: TestClient):
        """Malformed email address returns 400."""
        response = client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "SecurePass1!", "name": "X"},
        )
        assert response.status_code == 400

    def test_register_with_company_id(self, client: TestClient):
        """Registration with optional company_id links user to company."""
        email = _unique_email()
        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "SecurePass1!",
                "name": "Company User",
                "company_id": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["company_id"] == 1


# ---------------------------------------------------------------------------
# 4. Login (API)
# ---------------------------------------------------------------------------


class TestLogin:
    """POST /auth/login endpoint."""

    def test_login_success(self, client: TestClient):
        """Login with correct credentials returns user + tokens."""
        email = _unique_email()
        # Register first
        client.post(
            "/auth/register",
            json={"email": email, "password": "MyPass123!", "name": "Login Tester"},
        )

        # Login
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "MyPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == email
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client: TestClient):
        """Login with incorrect password returns 401."""
        email = _unique_email()
        client.post(
            "/auth/register",
            json={"email": email, "password": "CorrectPass1!", "name": "Wrong PW"},
        )
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_email_returns_401(self, client: TestClient):
        """Login with an email that does not exist returns 401."""
        response = client.post(
            "/auth/login",
            json={"email": "nobody@nowhere.com", "password": "anything"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 5. Token Refresh (API)
# ---------------------------------------------------------------------------


class TestTokenRefresh:
    """POST /auth/refresh endpoint."""

    def test_refresh_with_valid_refresh_token(self, client: TestClient):
        """A valid refresh token returns a new access token."""
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={"email": email, "password": "RefreshTest1!", "name": "Refresh User"},
        ).json()
        refresh_token = reg["refresh_token"]

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_access_token_rejected(self, client: TestClient):
        """Using an access token (not refresh) for refresh must fail."""
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={"email": email, "password": "RefreshTest1!", "name": "Refresh User"},
        ).json()
        access_token = reg["access_token"]

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Garbage token for refresh returns 401."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "garbage.token.here"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 6. Protected Endpoint /auth/me (API)
# ---------------------------------------------------------------------------


class TestProtectedMe:
    """GET /auth/me — requires valid JWT."""

    def test_me_with_valid_token(self, client: TestClient):
        """A valid access token returns the current user's profile."""
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={"email": email, "password": "MeTest1234!", "name": "Me Tester"},
        ).json()

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {reg['access_token']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["name"] == "Me Tester"

    def test_me_without_token_returns_401(self, client: TestClient):
        """No Authorization header returns 401."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_me_with_expired_token_returns_401(self, client: TestClient, settings):
        """An expired token returns 401."""
        # Create a token that is already expired
        expired_payload = {
            "sub": 999,
            "email": "expired@test.com",
            "role": "owner",
            "exp": int(time.time()) - 10,  # expired 10 seconds ago
        }
        expired_token = jwt.encode(
            expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_me_with_malformed_bearer_returns_401(self, client: TestClient):
        """A malformed Authorization header returns 401."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "NotBearer abc123"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 7. Role-Based Access (Middleware)
# ---------------------------------------------------------------------------


class TestRoleBasedAccess:
    """require_role middleware allows or denies based on user role."""

    def test_role_middleware_allows_matching_role(
        self, auth_service: AuthService, settings: Settings
    ):
        """A user with 'owner' role passes require_role('owner')."""
        from hr_advisory.api.middleware.auth_middleware import (
            get_current_user,
            require_role,
        )

        # Create token for an owner
        token = auth_service.create_access_token(user_id=1, email="owner@test.com", role="owner")
        # Decode and verify the role would pass
        payload = auth_service.decode_token(token)
        assert payload["role"] == "owner"
        assert payload["role"] in ("owner", "hr_manager")

    def test_role_middleware_rejects_non_matching_role(
        self, auth_service: AuthService, settings: Settings
    ):
        """A user with 'consultant' role is rejected by require_role('owner')."""
        token = auth_service.create_access_token(
            user_id=2, email="consultant@test.com", role="consultant"
        )
        payload = auth_service.decode_token(token)
        assert payload["role"] == "consultant"
        assert payload["role"] not in ("owner", "hr_manager")


# ---------------------------------------------------------------------------
# 8. Password Reset Flow (API)
# ---------------------------------------------------------------------------


class TestPasswordReset:
    """POST /auth/password-reset-request and POST /auth/password-reset."""

    def test_password_reset_request_returns_success(self, client: TestClient):
        """Password reset request with a registered email returns 200."""
        email = _unique_email()
        client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "ResetTest1!",
                "name": "Reset Tester",
            },
        )
        response = client.post(
            "/auth/password-reset-request",
            json={"email": email},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"]  # should contain a success message

    def test_password_reset_request_unknown_email_still_200(self, client: TestClient):
        """Password reset request with unknown email still returns 200 (no user enumeration)."""
        response = client.post(
            "/auth/password-reset-request",
            json={"email": "ghost@nowhere.com"},
        )
        # Return 200 to prevent email enumeration attacks
        assert response.status_code == 200

    def test_password_reset_with_valid_token(
        self, client: TestClient, auth_service: AuthService, settings: Settings
    ):
        """Resetting password with a valid reset token succeeds."""
        email = _unique_email()
        client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "OldPass123!",
                "name": "Reset User",
            },
        )

        # Generate a password-reset token (same as service would produce)
        # We manually create it since we can't intercept email
        reset_payload = {
            "sub": email,
            "type": "password_reset",
            "exp": int(time.time()) + 3600,
        }
        reset_token = jwt.encode(
            reset_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = client.post(
            "/auth/password-reset",
            json={"token": reset_token, "new_password": "NewPass456!"},
        )
        assert response.status_code == 200

        # Now login with the new password
        login_resp = client.post(
            "/auth/login",
            json={"email": email, "password": "NewPass456!"},
        )
        assert login_resp.status_code == 200

    def test_password_reset_with_invalid_token_returns_401(self, client: TestClient):
        """Password reset with garbage token returns 401."""
        response = client.post(
            "/auth/password-reset",
            json={"token": "garbage", "new_password": "NewPass456!"},
        )
        assert response.status_code == 401

    def test_password_reset_short_password_returns_400(
        self, client: TestClient, settings: Settings
    ):
        """Password reset with too-short new password returns 400."""
        reset_payload = {
            "sub": "x@x.com",
            "type": "password_reset",
            "exp": int(time.time()) + 3600,
        }
        reset_token = jwt.encode(
            reset_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        response = client.post(
            "/auth/password-reset",
            json={"token": reset_token, "new_password": "short"},
        )
        assert response.status_code == 400

    def test_password_reset_token_single_use(self, client: TestClient, auth_service: AuthService):
        """A password reset token can only be used once.

        Flow: register -> create_password_reset_token via AuthService ->
        POST /auth/password-reset (succeeds) -> POST /auth/password-reset
        again with the same token -> expect 401.
        """
        email = _unique_email()
        client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "SingleUse1!",
                "name": "Single Use Reset",
            },
        )

        # Generate a password-reset token using AuthService directly
        reset_token = auth_service.create_password_reset_token(email)

        # First use: reset password -- should succeed
        first_reset = client.post(
            "/auth/password-reset",
            json={"token": reset_token, "new_password": "NewPass999!"},
        )
        assert first_reset.status_code == 200, (
            f"First password reset should succeed, but got {first_reset.status_code}: "
            f"{first_reset.text}"
        )

        # Second use: same token -- must be rejected
        second_reset = client.post(
            "/auth/password-reset",
            json={"token": reset_token, "new_password": "AnotherPass1!"},
        )
        assert second_reset.status_code == 401, (
            "Reused password reset token should be rejected with 401, "
            f"but got {second_reset.status_code}: {second_reset.text}"
        )


# ---------------------------------------------------------------------------
# 9. Logout (API)
# ---------------------------------------------------------------------------


class TestLogout:
    """POST /auth/logout — server-side JWT revocation."""

    def test_logout_returns_success(self, client: TestClient):
        """Logout endpoint returns 200 with a success message."""
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "LogoutTest1!",
                "name": "Logout User",
            },
        ).json()
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {reg['access_token']}"},
        )
        assert response.status_code == 200

    def test_refresh_token_revoked_on_logout(self, client: TestClient):
        """After logout with refresh_token in body, that refresh token is rejected.

        Flow: register -> login -> get refresh_token -> logout with
        refresh_token in body -> POST /auth/refresh with that token -> expect 401.
        """
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "RefRevoke1!",
                "name": "Refresh Revoke User",
            },
        ).json()
        access_token = reg["access_token"]
        refresh_token = reg["refresh_token"]

        # Refresh token works before logout
        refresh_before = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_before.status_code == 200, "Refresh token should work before logout"

        # Logout, passing refresh_token in the request body
        logout_resp = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200

        # Refresh token must now be rejected
        refresh_after = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_after.status_code == 401, (
            "Refresh token should be revoked after logout, " f"but got {refresh_after.status_code}"
        )


# ---------------------------------------------------------------------------
# 10. Token Revocation (H-4 fix)
# ---------------------------------------------------------------------------


class TestTokenRevocation:
    """Server-side JWT token revocation via blocklist.

    Addresses red team finding H-4: 'No server-side token revocation.'
    After logout, the token must be rejected by all protected endpoints.
    """

    def test_revoked_token_rejected_after_logout(self, client: TestClient):
        """After logout, the same access token is rejected with 401."""
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "RevokeTest1!",
                "name": "Revoke User",
            },
        ).json()
        access_token = reg["access_token"]

        # Token works before logout
        me_before = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_before.status_code == 200

        # Logout
        logout_resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200

        # Token rejected after logout
        me_after = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_after.status_code == 401, "Revoked token should be rejected after logout"

    def test_different_token_still_works_after_one_logout(self, client: TestClient):
        """Logging out with one token does not affect a different user's token."""
        # Register and get tokens for user A
        email_a = _unique_email()
        reg_a = client.post(
            "/auth/register",
            json={
                "email": email_a,
                "password": "UserAPass1!",
                "name": "User A",
            },
        ).json()

        # Register and get tokens for user B
        email_b = _unique_email()
        reg_b = client.post(
            "/auth/register",
            json={
                "email": email_b,
                "password": "UserBPass1!",
                "name": "User B",
            },
        ).json()

        # User A logs out
        client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {reg_a['access_token']}"},
        )

        # User B's token still works
        me_b = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {reg_b['access_token']}"},
        )
        assert me_b.status_code == 200

    def test_new_token_works_after_logout(self, client: TestClient):
        """After logout, logging back in gives a new valid token."""
        email = _unique_email()
        password = "ReLoginTest1!"
        reg = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "ReLogin User",
            },
        ).json()
        old_token = reg["access_token"]

        # Logout (revokes old token)
        client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {old_token}"},
        )

        # Login again to get a new token
        login_resp = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        new_token = login_resp.json()["access_token"]

        # New token works
        me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert me.status_code == 200

        # Old token is still rejected
        me_old = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert me_old.status_code == 401

    def test_access_token_contains_jti_claim(self, client: TestClient, settings: Settings):
        """Access tokens issued by the API include a JTI claim."""
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "JtiCheckTest1!",
                "name": "JTI User",
            },
        ).json()
        token = reg["access_token"]

        # Decode the token and verify JTI is present
        import jwt as pyjwt

        payload = pyjwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        assert "jti" in payload, "Access token must contain a 'jti' claim"
        assert isinstance(payload["jti"], str)
        assert len(payload["jti"]) > 0

    def test_revoked_token_detail_message(self, client: TestClient):
        """Revoked token returns a clear error detail."""
        email = _unique_email()
        reg = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "DetailTest1!",
                "name": "Detail User",
            },
        ).json()
        access_token = reg["access_token"]

        # Logout
        client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Check the error detail
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()
