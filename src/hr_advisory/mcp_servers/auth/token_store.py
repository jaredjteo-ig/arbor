"""Encrypted OAuth token store for external API credentials.

Per-tenant, per-provider token management. Tokens stored encrypted using
Fernet (same pattern as PII encryption in hr_advisory/security/encryption.py).
In-memory cache with TTL for hot path.

T205: Encrypted OAuth Token Store
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Attempt to use existing encryption infrastructure
try:
    from hr_advisory.security.encryption import encrypt_value, decrypt_value
except ImportError:
    # Fallback: use Fernet directly
    from cryptography.fernet import Fernet

    _KEY = os.environ.get("INTEGRATION_ENCRYPTION_KEY", "")

    def _get_fernet() -> Fernet:
        environment = os.environ.get("ENVIRONMENT", "development")
        if not _KEY and environment == "production":
            raise RuntimeError(
                "INTEGRATION_ENCRYPTION_KEY must be set in production. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        key = _KEY or Fernet.generate_key().decode()
        if not _KEY:
            logger.warning(
                "INTEGRATION_ENCRYPTION_KEY not set — using ephemeral key (tokens lost on restart)"
            )
        return Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt_value(value: str) -> str:
        return _get_fernet().encrypt(value.encode()).decode()

    def decrypt_value(encrypted: str) -> str:
        return _get_fernet().decrypt(encrypted.encode()).decode()


@dataclass
class StoredToken:
    """A stored OAuth token for an external API."""

    tenant_id: str
    provider: str
    access_token_encrypted: str
    refresh_token_encrypted: Optional[str] = None
    expires_at: Optional[float] = None  # Unix timestamp
    scopes: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at - 60  # 60s safety margin

    @property
    def access_token(self) -> str:
        return decrypt_value(self.access_token_encrypted)

    @property
    def refresh_token(self) -> Optional[str]:
        if self.refresh_token_encrypted is None:
            return None
        return decrypt_value(self.refresh_token_encrypted)


class ExternalTokenManager:
    """Manages OAuth tokens for external APIs per tenant.

    In-memory storage with encryption. Production should persist to
    database (DataFlow IntegrationToken model).

    Usage::

        manager = ExternalTokenManager()
        manager.store_token("company_123", "xero", {
            "access_token": "xa_...",
            "refresh_token": "xr_...",
            "expires_in": 1800,
            "scope": "accounting.transactions",
        })

        token = manager.get_valid_token("company_123", "xero")
    """

    def __init__(self):
        self._store: dict[str, StoredToken] = {}  # key: "{tenant_id}:{provider}"
        self._refresh_callbacks: dict[str, callable] = {}

    def _key(self, tenant_id: str, provider: str) -> str:
        return f"{tenant_id}:{provider}"

    def store_token(
        self,
        tenant_id: str,
        provider: str,
        token_data: dict,
    ) -> None:
        """Store an OAuth token (encrypted at rest).

        Args:
            tenant_id: Company/tenant ID.
            provider: External API name (e.g., "xero", "cpf_apex").
            token_data: Dict with access_token, refresh_token, expires_in, scope.
        """
        access_encrypted = encrypt_value(token_data["access_token"])
        refresh_encrypted = None
        if token_data.get("refresh_token"):
            refresh_encrypted = encrypt_value(token_data["refresh_token"])

        expires_at = None
        if token_data.get("expires_in"):
            expires_at = time.time() + token_data["expires_in"]

        scopes = []
        if token_data.get("scope"):
            scopes = (
                token_data["scope"].split()
                if isinstance(token_data["scope"], str)
                else token_data["scope"]
            )

        stored = StoredToken(
            tenant_id=tenant_id,
            provider=provider,
            access_token_encrypted=access_encrypted,
            refresh_token_encrypted=refresh_encrypted,
            expires_at=expires_at,
            scopes=scopes,
        )
        self._store[self._key(tenant_id, provider)] = stored
        logger.info("Stored token for %s/%s (expires_at=%s)", tenant_id, provider, expires_at)

    def get_valid_token(self, tenant_id: str, provider: str) -> Optional[str]:
        """Get a valid access token, or None if not available.

        Does NOT auto-refresh. Call refresh_token() explicitly if expired.
        """
        key = self._key(tenant_id, provider)
        stored = self._store.get(key)
        if stored is None:
            return None
        if stored.is_expired:
            logger.warning("Token expired for %s/%s", tenant_id, provider)
            return None
        return stored.access_token

    def get_stored_token(self, tenant_id: str, provider: str) -> Optional[StoredToken]:
        """Get the full stored token object."""
        return self._store.get(self._key(tenant_id, provider))

    def has_token(self, tenant_id: str, provider: str) -> bool:
        """Check if a token exists for this tenant/provider."""
        return self._key(tenant_id, provider) in self._store

    def is_connected(self, tenant_id: str, provider: str) -> bool:
        """Check if tenant has a valid (non-expired) connection."""
        token = self.get_valid_token(tenant_id, provider)
        return token is not None

    def revoke_token(self, tenant_id: str, provider: str) -> bool:
        """Delete a stored token. Returns True if existed."""
        key = self._key(tenant_id, provider)
        if key in self._store:
            del self._store[key]
            logger.info("Revoked token for %s/%s", tenant_id, provider)
            return True
        return False

    def list_connections(self, tenant_id: str) -> list[dict]:
        """List all connected providers for a tenant."""
        connections = []
        for key, stored in self._store.items():
            if stored.tenant_id == tenant_id:
                connections.append(
                    {
                        "provider": stored.provider,
                        "connected": not stored.is_expired,
                        "expires_at": (
                            datetime.fromtimestamp(stored.expires_at, tz=timezone.utc).isoformat()
                            if stored.expires_at
                            else None
                        ),
                        "scopes": stored.scopes,
                    }
                )
        return connections

    def register_refresh_callback(self, provider: str, callback: callable) -> None:
        """Register a token refresh callback for a provider.

        The callback receives (tenant_id, refresh_token) and should return
        new token_data dict.
        """
        self._refresh_callbacks[provider] = callback

    async def refresh_if_expired(self, tenant_id: str, provider: str) -> Optional[str]:
        """Attempt to refresh an expired token. Returns new access token or None."""
        stored = self.get_stored_token(tenant_id, provider)
        if stored is None:
            return None
        if not stored.is_expired:
            return stored.access_token

        refresh = stored.refresh_token
        if refresh is None:
            logger.warning(
                "No refresh token for %s/%s — re-authentication required", tenant_id, provider
            )
            return None

        callback = self._refresh_callbacks.get(provider)
        if callback is None:
            logger.warning("No refresh callback registered for provider %s", provider)
            return None

        try:
            new_data = await callback(tenant_id, refresh)
            self.store_token(tenant_id, provider, new_data)
            return new_data["access_token"]
        except Exception:
            logger.exception("Token refresh failed for %s/%s", tenant_id, provider)
            return None


# Singleton instance
_token_manager: Optional[ExternalTokenManager] = None


def get_token_manager() -> ExternalTokenManager:
    """Get or create the global token manager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = ExternalTokenManager()
    return _token_manager
