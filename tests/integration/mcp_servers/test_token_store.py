"""Integration tests for ExternalTokenManager (encrypted OAuth token store).

Tests:
- Store/retrieve/revoke tokens
- Expiry detection (expired tokens return None)
- Encryption verification (stored encrypted value != plaintext)
- Connection listing per tenant
- Refresh callback mechanism
- Tenant isolation (tenant A cannot see tenant B tokens)
"""

from __future__ import annotations

import time

import pytest

from hr_advisory.mcp_servers.auth.token_store import ExternalTokenManager, StoredToken

from .conftest import TENANT_A, TENANT_B


# ---------------------------------------------------------------------------
# Store and retrieve
# ---------------------------------------------------------------------------


class TestStoreAndRetrieve:
    """Basic token storage and retrieval lifecycle."""

    def test_store_and_retrieve_access_token(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "xa_abc123", "expires_in": 1800},
        )
        token = token_manager.get_valid_token(TENANT_A, "xero")
        assert token == "xa_abc123"

    def test_retrieve_nonexistent_token_returns_none(self, token_manager: ExternalTokenManager):
        assert token_manager.get_valid_token("ghost_tenant", "xero") is None

    def test_has_token_true_when_stored(self, token_manager: ExternalTokenManager):
        token_manager.store_token(TENANT_A, "xero", {"access_token": "tok"})
        assert token_manager.has_token(TENANT_A, "xero") is True

    def test_has_token_false_when_not_stored(self, token_manager: ExternalTokenManager):
        assert token_manager.has_token(TENANT_A, "xero") is False

    def test_store_with_refresh_token(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {
                "access_token": "xa_123",
                "refresh_token": "xr_456",
                "expires_in": 1800,
            },
        )
        stored = token_manager.get_stored_token(TENANT_A, "xero")
        assert stored is not None
        assert stored.refresh_token == "xr_456"

    def test_store_without_refresh_token(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "cpf_apex",
            {"access_token": "cpf_tok"},
        )
        stored = token_manager.get_stored_token(TENANT_A, "cpf_apex")
        assert stored is not None
        assert stored.refresh_token is None

    def test_store_parses_scopes_from_string(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {
                "access_token": "tok",
                "scope": "accounting.transactions accounting.contacts",
            },
        )
        stored = token_manager.get_stored_token(TENANT_A, "xero")
        assert stored.scopes == ["accounting.transactions", "accounting.contacts"]

    def test_store_parses_scopes_from_list(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {
                "access_token": "tok",
                "scope": ["accounting.transactions"],
            },
        )
        stored = token_manager.get_stored_token(TENANT_A, "xero")
        assert stored.scopes == ["accounting.transactions"]

    def test_overwrite_existing_token(self, token_manager: ExternalTokenManager):
        token_manager.store_token(TENANT_A, "xero", {"access_token": "old_token"})
        token_manager.store_token(TENANT_A, "xero", {"access_token": "new_token"})
        assert token_manager.get_valid_token(TENANT_A, "xero") == "new_token"


# ---------------------------------------------------------------------------
# Expiry detection
# ---------------------------------------------------------------------------


class TestExpiryDetection:
    """Token expiry with the 60-second safety margin."""

    def test_non_expired_token_is_valid(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "valid_tok", "expires_in": 3600},
        )
        assert token_manager.get_valid_token(TENANT_A, "xero") == "valid_tok"
        assert token_manager.is_connected(TENANT_A, "xero") is True

    def test_expired_token_returns_none(self, token_manager: ExternalTokenManager):
        """A token whose expires_at is in the past returns None."""
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "expired_tok", "expires_in": 1},
        )
        # Manually backdate expires_at so the token is truly expired
        stored = token_manager.get_stored_token(TENANT_A, "xero")
        stored.expires_at = time.time() - 120  # 2 minutes in the past
        assert token_manager.get_valid_token(TENANT_A, "xero") is None
        assert token_manager.is_connected(TENANT_A, "xero") is False

    def test_token_within_safety_margin_is_expired(self, token_manager: ExternalTokenManager):
        """A token expiring in 30 seconds is treated as expired (60s safety margin)."""
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "marginal_tok", "expires_in": 30},
        )
        assert token_manager.get_valid_token(TENANT_A, "xero") is None

    def test_token_without_expiry_never_expires(self, token_manager: ExternalTokenManager):
        """A token stored without expires_in is treated as non-expiring."""
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "forever_tok"},
        )
        assert token_manager.get_valid_token(TENANT_A, "xero") == "forever_tok"

    def test_is_expired_property(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "tok", "expires_in": 10},
        )
        stored = token_manager.get_stored_token(TENANT_A, "xero")
        # expires_in=10 with 60s safety margin means it's expired immediately
        assert stored.is_expired is True


# ---------------------------------------------------------------------------
# Encryption verification
# ---------------------------------------------------------------------------


class TestEncryptionVerification:
    """Stored encrypted values must not match plaintext."""

    def test_stored_access_token_is_encrypted(self, token_manager: ExternalTokenManager):
        plaintext = "xa_super_secret_token_12345"
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": plaintext},
        )
        stored = token_manager.get_stored_token(TENANT_A, "xero")
        assert stored.access_token_encrypted != plaintext
        # But decryption returns the original
        assert stored.access_token == plaintext

    def test_stored_refresh_token_is_encrypted(self, token_manager: ExternalTokenManager):
        plaintext_refresh = "xr_refresh_secret_789"
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "tok", "refresh_token": plaintext_refresh},
        )
        stored = token_manager.get_stored_token(TENANT_A, "xero")
        assert stored.refresh_token_encrypted != plaintext_refresh
        assert stored.refresh_token == plaintext_refresh

    def test_different_tokens_produce_different_ciphertexts(
        self, token_manager: ExternalTokenManager
    ):
        """Two different plaintext tokens must produce different encrypted values."""
        token_manager.store_token(TENANT_A, "xero", {"access_token": "token_alpha"})
        token_manager.store_token(TENANT_B, "xero", {"access_token": "token_beta"})
        stored_a = token_manager.get_stored_token(TENANT_A, "xero")
        stored_b = token_manager.get_stored_token(TENANT_B, "xero")
        assert stored_a.access_token_encrypted != stored_b.access_token_encrypted


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------


class TestRevoke:
    """Token revocation."""

    def test_revoke_existing_token(self, token_manager: ExternalTokenManager):
        token_manager.store_token(TENANT_A, "xero", {"access_token": "to_revoke"})
        assert token_manager.revoke_token(TENANT_A, "xero") is True
        assert token_manager.get_valid_token(TENANT_A, "xero") is None

    def test_revoke_nonexistent_token_returns_false(self, token_manager: ExternalTokenManager):
        assert token_manager.revoke_token("ghost", "xero") is False

    def test_has_token_false_after_revoke(self, token_manager: ExternalTokenManager):
        token_manager.store_token(TENANT_A, "xero", {"access_token": "tok"})
        token_manager.revoke_token(TENANT_A, "xero")
        assert token_manager.has_token(TENANT_A, "xero") is False


# ---------------------------------------------------------------------------
# Connection listing
# ---------------------------------------------------------------------------


class TestConnectionListing:
    """list_connections() returns per-tenant provider summary."""

    def test_list_connections_for_tenant(self, token_manager_with_tokens: ExternalTokenManager):
        connections = token_manager_with_tokens.list_connections(TENANT_A)
        providers = [c["provider"] for c in connections]
        assert "xero" in providers
        assert "cpf_apex" in providers

    def test_list_connections_excludes_other_tenant(
        self, token_manager_with_tokens: ExternalTokenManager
    ):
        connections = token_manager_with_tokens.list_connections(TENANT_B)
        providers = [c["provider"] for c in connections]
        assert "cpf_apex" not in providers  # Only TENANT_A has cpf_apex
        assert "xero" in providers

    def test_list_connections_shows_connected_status(
        self, token_manager_with_tokens: ExternalTokenManager
    ):
        connections = token_manager_with_tokens.list_connections(TENANT_A)
        xero_conn = next(c for c in connections if c["provider"] == "xero")
        assert xero_conn["connected"] is True
        assert xero_conn["expires_at"] is not None

    def test_list_connections_shows_scopes(self, token_manager_with_tokens: ExternalTokenManager):
        connections = token_manager_with_tokens.list_connections(TENANT_A)
        xero_conn = next(c for c in connections if c["provider"] == "xero")
        assert "accounting.transactions" in xero_conn["scopes"]

    def test_empty_connections_for_unknown_tenant(
        self, token_manager_with_tokens: ExternalTokenManager
    ):
        assert token_manager_with_tokens.list_connections("unknown_tenant") == []


# ---------------------------------------------------------------------------
# Refresh callback
# ---------------------------------------------------------------------------


class TestRefreshCallback:
    """Token refresh using registered callbacks."""

    async def test_refresh_expired_token(self, token_manager: ExternalTokenManager):
        """Refresh callback is invoked when token is expired."""
        # Store a token and then backdate its expiry to force expiration
        token_manager.store_token(
            TENANT_A,
            "xero",
            {
                "access_token": "old_access",
                "refresh_token": "xr_refresh",
                "expires_in": 1,
            },
        )
        token_manager.get_stored_token(TENANT_A, "xero").expires_at = time.time() - 120

        async def mock_refresh(tenant_id: str, refresh_token: str) -> dict:
            assert tenant_id == TENANT_A
            assert refresh_token == "xr_refresh"
            return {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 1800,
            }

        token_manager.register_refresh_callback("xero", mock_refresh)
        new_token = await token_manager.refresh_if_expired(TENANT_A, "xero")
        assert new_token == "new_access_token"

    async def test_refresh_returns_none_when_no_callback(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "cpf_apex",
            {
                "access_token": "old",
                "refresh_token": "refresh",
                "expires_in": 1,
            },
        )
        token_manager.get_stored_token(TENANT_A, "cpf_apex").expires_at = time.time() - 120
        result = await token_manager.refresh_if_expired(TENANT_A, "cpf_apex")
        assert result is None

    async def test_refresh_returns_none_when_no_refresh_token(
        self, token_manager: ExternalTokenManager
    ):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "old", "expires_in": 1},
        )
        token_manager.get_stored_token(TENANT_A, "xero").expires_at = time.time() - 120
        token_manager.register_refresh_callback("xero", lambda t, r: {})
        result = await token_manager.refresh_if_expired(TENANT_A, "xero")
        assert result is None

    async def test_refresh_returns_none_on_unknown_token(self, token_manager: ExternalTokenManager):
        result = await token_manager.refresh_if_expired("ghost", "xero")
        assert result is None

    async def test_refresh_skipped_when_not_expired(self, token_manager: ExternalTokenManager):
        """Non-expired tokens should be returned directly without refresh."""
        token_manager.store_token(
            TENANT_A,
            "xero",
            {"access_token": "still_valid", "expires_in": 3600},
        )
        callback_called = False

        async def should_not_be_called(t, r):
            nonlocal callback_called
            callback_called = True
            return {}

        token_manager.register_refresh_callback("xero", should_not_be_called)
        result = await token_manager.refresh_if_expired(TENANT_A, "xero")
        assert result == "still_valid"
        assert callback_called is False

    async def test_refresh_handles_callback_exception(self, token_manager: ExternalTokenManager):
        token_manager.store_token(
            TENANT_A,
            "xero",
            {
                "access_token": "old",
                "refresh_token": "xr_ref",
                "expires_in": 1,
            },
        )
        token_manager.get_stored_token(TENANT_A, "xero").expires_at = time.time() - 120

        async def failing_refresh(t, r):
            raise ConnectionError("OAuth server down")

        token_manager.register_refresh_callback("xero", failing_refresh)
        result = await token_manager.refresh_if_expired(TENANT_A, "xero")
        assert result is None
