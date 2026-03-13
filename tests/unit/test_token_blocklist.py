"""Unit tests for token blocklist (JWT revocation).

Tests the in-memory token blocklist that enables server-side JWT invalidation.
Addresses red team finding H-4: "No server-side token revocation."

Tier 1 (Unit): Fast, isolated, no external dependencies.
"""

from __future__ import annotations

import time
import uuid

import pytest


class TestTokenBlocklist:
    """Core blocklist operations: revoke and check."""

    def test_revoke_token_marks_jti_as_revoked(self):
        """After revoking a JTI, is_revoked returns True for that JTI."""
        from hr_advisory.api.middleware.token_blocklist import (
            InMemoryBlocklist,
        )

        blocklist = InMemoryBlocklist()
        jti = str(uuid.uuid4())
        expires_at = int(time.time()) + 3600  # 1 hour from now

        blocklist.revoke_token(jti, expires_at)
        assert blocklist.is_revoked(jti) is True

    def test_non_revoked_token_returns_false(self):
        """A JTI that was never revoked returns False."""
        from hr_advisory.api.middleware.token_blocklist import (
            InMemoryBlocklist,
        )

        blocklist = InMemoryBlocklist()
        jti = str(uuid.uuid4())
        assert blocklist.is_revoked(jti) is False

    def test_expired_entries_are_cleaned_up(self):
        """Entries with past expiry are removed during cleanup."""
        from hr_advisory.api.middleware.token_blocklist import (
            InMemoryBlocklist,
        )

        blocklist = InMemoryBlocklist()
        expired_jti = str(uuid.uuid4())
        # Expired 10 seconds ago
        blocklist.revoke_token(expired_jti, int(time.time()) - 10)

        valid_jti = str(uuid.uuid4())
        blocklist.revoke_token(valid_jti, int(time.time()) + 3600)

        blocklist.cleanup_expired()

        # Expired entry should be gone
        assert blocklist.is_revoked(expired_jti) is False
        # Valid entry should remain
        assert blocklist.is_revoked(valid_jti) is True

    def test_multiple_revocations_independent(self):
        """Revoking multiple JTIs works independently."""
        from hr_advisory.api.middleware.token_blocklist import (
            InMemoryBlocklist,
        )

        blocklist = InMemoryBlocklist()
        jti_a = str(uuid.uuid4())
        jti_b = str(uuid.uuid4())
        jti_c = str(uuid.uuid4())
        expires_at = int(time.time()) + 3600

        blocklist.revoke_token(jti_a, expires_at)
        blocklist.revoke_token(jti_b, expires_at)

        assert blocklist.is_revoked(jti_a) is True
        assert blocklist.is_revoked(jti_b) is True
        assert blocklist.is_revoked(jti_c) is False

    def test_revoke_same_jti_twice_is_idempotent(self):
        """Revoking the same JTI twice does not raise and stays revoked."""
        from hr_advisory.api.middleware.token_blocklist import (
            InMemoryBlocklist,
        )

        blocklist = InMemoryBlocklist()
        jti = str(uuid.uuid4())
        expires_at = int(time.time()) + 3600

        blocklist.revoke_token(jti, expires_at)
        blocklist.revoke_token(jti, expires_at)  # Should not raise

        assert blocklist.is_revoked(jti) is True


class TestTokenBlocklistValidation:
    """Input validation on the blocklist."""

    def test_revoke_empty_jti_raises(self):
        """An empty JTI string should raise ValueError."""
        from hr_advisory.api.middleware.token_blocklist import (
            InMemoryBlocklist,
        )

        blocklist = InMemoryBlocklist()
        with pytest.raises(ValueError, match="[Jj][Tt][Ii]"):
            blocklist.revoke_token("", int(time.time()) + 3600)

    def test_is_revoked_empty_jti_raises(self):
        """Checking an empty JTI should raise ValueError."""
        from hr_advisory.api.middleware.token_blocklist import (
            InMemoryBlocklist,
        )

        blocklist = InMemoryBlocklist()
        with pytest.raises(ValueError, match="[Jj][Tt][Ii]"):
            blocklist.is_revoked("")


class TestBlocklistSingleton:
    """The get_blocklist() function returns a usable blocklist."""

    def test_get_blocklist_returns_blocklist_instance(self):
        """get_blocklist() returns an object with revoke_token and is_revoked methods."""
        from hr_advisory.api.middleware.token_blocklist import get_blocklist

        blocklist = get_blocklist()
        assert hasattr(blocklist, "revoke_token")
        assert hasattr(blocklist, "is_revoked")

    def test_get_blocklist_is_functional(self):
        """get_blocklist() returns a working blocklist."""
        from hr_advisory.api.middleware.token_blocklist import get_blocklist

        blocklist = get_blocklist()
        jti = str(uuid.uuid4())
        assert blocklist.is_revoked(jti) is False

        blocklist.revoke_token(jti, int(time.time()) + 3600)
        assert blocklist.is_revoked(jti) is True


class TestJTIInAccessToken:
    """Access tokens must include a JTI claim for revocation."""

    def test_access_token_contains_jti(self):
        """create_access_token embeds a 'jti' claim in the payload."""
        from hr_advisory.config.settings import Settings
        from hr_advisory.services.auth_service import AuthService

        settings = Settings(
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            jwt_expiry_minutes=60,
        )
        svc = AuthService(settings=settings)
        token = svc.create_access_token(user_id=1, email="test@test.com", role="owner")
        payload = svc.decode_token(token)

        assert "jti" in payload, "Access token must contain a 'jti' claim"
        assert isinstance(payload["jti"], str)
        assert len(payload["jti"]) > 0

    def test_access_token_jti_is_unique(self):
        """Each access token gets a unique JTI."""
        from hr_advisory.config.settings import Settings
        from hr_advisory.services.auth_service import AuthService

        settings = Settings(
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            jwt_expiry_minutes=60,
        )
        svc = AuthService(settings=settings)

        token1 = svc.create_access_token(user_id=1, email="test@test.com", role="owner")
        token2 = svc.create_access_token(user_id=1, email="test@test.com", role="owner")

        payload1 = svc.decode_token(token1)
        payload2 = svc.decode_token(token2)

        assert payload1["jti"] != payload2["jti"], "Each token must have a unique JTI"


class TestRefreshTokenJTI:
    """Refresh tokens should also include JTI for revocation."""

    def test_refresh_token_contains_jti(self):
        """create_refresh_token embeds a 'jti' claim in the payload."""
        from hr_advisory.config.settings import Settings
        from hr_advisory.services.auth_service import AuthService

        settings = Settings(
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            jwt_expiry_minutes=60,
        )
        svc = AuthService(settings=settings)
        token = svc.create_refresh_token(user_id=1)
        payload = svc.decode_token(token)

        assert "jti" in payload, "Refresh token must contain a 'jti' claim"
        assert isinstance(payload["jti"], str)
        assert len(payload["jti"]) > 0
