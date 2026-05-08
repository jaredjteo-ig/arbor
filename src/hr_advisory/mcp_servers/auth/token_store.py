"""Encrypted OAuth token store for external API credentials.

Per-tenant, per-provider token management. Tokens stored encrypted
using Fernet (same key, ``INTEGRATION_ENCRYPTION_KEY``, as PII
encryption in hr_advisory/security/encryption.py).

Persisted via the ``IntegrationToken`` DataFlow model so tokens
survive backend restart and are visible across uvicorn workers.
In-process cache fronts the DB for hot-path adapter calls; cache
entries are written through on store/refresh and invalidated on
revoke. Soft-deletes via ``disconnected_at`` preserve audit history.

T205 → P1.3: persisted token store.
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
        # In-process write-through cache, keyed by "{tenant_id}:{provider}".
        # Avoids hitting the DB on every adapter API call. Invalidated on
        # store/refresh/revoke so multi-worker uvicorn stays consistent
        # across token refreshes (workers re-read from DB on cache miss).
        self._store: dict[str, StoredToken] = {}
        self._refresh_callbacks: dict[str, callable] = {}

    def _key(self, tenant_id: str, provider: str) -> str:
        return f"{tenant_id}:{provider}"

    @staticmethod
    def _row_to_stored(row: dict) -> StoredToken:
        return StoredToken(
            tenant_id=str(row.get("tenant_id", "")),
            provider=str(row.get("provider", "")),
            access_token_encrypted=str(row.get("access_token_encrypted", "")),
            refresh_token_encrypted=(
                str(row["refresh_token_encrypted"])
                if row.get("refresh_token_encrypted")
                else None
            ),
            expires_at=(
                float(row["expires_at"]) if row.get("expires_at") else None
            ),
            scopes=str(row.get("scopes", "")).split() if row.get("scopes") else [],
        )

    def _read_active_row(self, tenant_id: str, provider: str) -> Optional[dict]:
        """Fetch the active (not disconnected) IntegrationToken row, if any."""
        from hr_advisory.services import dataflow_crud

        rows = dataflow_crud.list_records(
            "IntegrationToken",
            {
                "tenant_id": tenant_id,
                "provider": provider,
                "disconnected_at": "",
            },
            cache_ttl=0,
        )
        return rows[0] if rows else None

    def store_token(
        self,
        tenant_id: str,
        provider: str,
        token_data: dict,
    ) -> None:
        """Store an OAuth token (encrypted at rest, persisted to DB).

        Idempotent upsert keyed by (tenant_id, provider) — overwrites the
        active row, preserves any disconnected rows for audit.

        Args:
            tenant_id: Company/tenant ID (stringified).
            provider: External API name (e.g., "xero", "cpf_apex").
            token_data: Dict with access_token, refresh_token, expires_in,
                scope. Optional: xero_tenant_id, xero_tenant_name (Xero
                org id and display name resolved at OAuth callback time);
                connected_by (Arbor user id who clicked Connect).
        """
        from hr_advisory.services import dataflow_crud

        access_encrypted = encrypt_value(token_data["access_token"])
        refresh_encrypted = ""
        if token_data.get("refresh_token"):
            refresh_encrypted = encrypt_value(token_data["refresh_token"])

        expires_at = 0.0
        if token_data.get("expires_in"):
            expires_at = time.time() + token_data["expires_in"]

        scope_value = token_data.get("scope") or ""
        scopes_str = (
            scope_value
            if isinstance(scope_value, str)
            else " ".join(scope_value)
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        existing = self._read_active_row(tenant_id, provider)
        payload = {
            "tenant_id": tenant_id,
            "provider": provider,
            "access_token_encrypted": access_encrypted,
            "refresh_token_encrypted": refresh_encrypted,
            "expires_at": expires_at,
            "scopes": scopes_str,
            "xero_tenant_id": str(token_data.get("xero_tenant_id", "")),
            "xero_tenant_name": str(token_data.get("xero_tenant_name", "")),
            "connected_by": int(token_data.get("connected_by", 0) or 0),
            "connected_at": (
                existing.get("connected_at") if existing else now_iso
            ),
            "disconnected_at": "",
        }

        if existing:
            dataflow_crud.update("IntegrationToken", existing["id"], payload)
        else:
            dataflow_crud.create("IntegrationToken", payload)

        # Refresh the in-process cache.
        scopes_list = scopes_str.split() if scopes_str else []
        self._store[self._key(tenant_id, provider)] = StoredToken(
            tenant_id=tenant_id,
            provider=provider,
            access_token_encrypted=access_encrypted,
            refresh_token_encrypted=refresh_encrypted or None,
            expires_at=expires_at if expires_at > 0 else None,
            scopes=scopes_list,
        )
        logger.info(
            "Stored token for %s/%s (expires_at=%s)",
            tenant_id,
            provider,
            expires_at,
        )

    def get_stored_token(
        self, tenant_id: str, provider: str
    ) -> Optional[StoredToken]:
        """Get the full stored token object, hitting cache then DB."""
        key = self._key(tenant_id, provider)
        cached = self._store.get(key)
        if cached is not None:
            return cached
        row = self._read_active_row(tenant_id, provider)
        if not row:
            return None
        stored = self._row_to_stored(row)
        self._store[key] = stored
        return stored

    def get_valid_token(self, tenant_id: str, provider: str) -> Optional[str]:
        """Get a valid access token, or None if expired / absent.

        Does NOT auto-refresh. Call ``refresh_if_expired`` for that.
        """
        stored = self.get_stored_token(tenant_id, provider)
        if stored is None:
            return None
        if stored.is_expired:
            logger.warning("Token expired for %s/%s", tenant_id, provider)
            return None
        return stored.access_token

    def has_token(self, tenant_id: str, provider: str) -> bool:
        """True if an active (non-disconnected) token row exists."""
        return self.get_stored_token(tenant_id, provider) is not None

    def is_connected(self, tenant_id: str, provider: str) -> bool:
        """True if an active connection exists, even if access-token is stale.

        "Connected" means we have an active (non-disconnected) row with a
        refresh_token. The access_token may be expired — the next API
        call will refresh transparently. Returning False on expiry
        breaks the UI status badge after every 30-minute idle period.
        """
        stored = self.get_stored_token(tenant_id, provider)
        if stored is None:
            return False
        # Either the access token is still good, or we can refresh.
        if not stored.is_expired:
            return True
        return stored.refresh_token is not None

    def get_xero_tenant_id(self, tenant_id: str) -> str:
        """Provider-specific helper: persisted Xero org id for this tenant."""
        row = self._read_active_row(tenant_id, "xero")
        return str(row.get("xero_tenant_id", "")) if row else ""

    def revoke_token(self, tenant_id: str, provider: str) -> bool:
        """Soft-delete the active token row.

        Sets ``disconnected_at`` so audit history is preserved. Returns
        True if a row was updated.
        """
        from hr_advisory.services import dataflow_crud

        existing = self._read_active_row(tenant_id, provider)
        if not existing:
            self._store.pop(self._key(tenant_id, provider), None)
            return False

        dataflow_crud.update(
            "IntegrationToken",
            existing["id"],
            {"disconnected_at": datetime.now(timezone.utc).isoformat()},
        )
        self._store.pop(self._key(tenant_id, provider), None)
        logger.info("Revoked token for %s/%s", tenant_id, provider)
        return True

    def hard_delete(self, tenant_id: str, provider: str) -> bool:
        """PDPA hard-delete: drop the active token row entirely.

        Used when the customer disconnects — the purpose for holding
        the OAuth grant has ended. Disconnected (already soft-deleted)
        rows are preserved for audit; only the active row is removed.

        Returns True if an active row existed and was deleted.
        """
        from hr_advisory.services import dataflow_crud

        existing = self._read_active_row(tenant_id, provider)
        self._store.pop(self._key(tenant_id, provider), None)
        if not existing:
            return False
        try:
            dataflow_crud.delete("IntegrationToken", existing["id"])
            logger.info(
                "Hard-deleted token for %s/%s", tenant_id, provider
            )
            return True
        except Exception:
            logger.exception(
                "Failed to hard-delete token for %s/%s",
                tenant_id,
                provider,
            )
            return False

    def list_connections(self, tenant_id: str) -> list[dict]:
        """List all active (non-disconnected) providers for a tenant."""
        from hr_advisory.services import dataflow_crud

        rows = dataflow_crud.list_records(
            "IntegrationToken",
            {"tenant_id": tenant_id, "disconnected_at": ""},
            cache_ttl=0,
        )
        connections = []
        for row in rows:
            expires_at = row.get("expires_at")
            iso_expires: Optional[str] = None
            if expires_at:
                iso_expires = datetime.fromtimestamp(
                    float(expires_at), tz=timezone.utc
                ).isoformat()
            scopes_list = (
                str(row.get("scopes", "")).split() if row.get("scopes") else []
            )
            stored = self._row_to_stored(row)
            connections.append(
                {
                    "provider": str(row.get("provider", "")),
                    "connected": not stored.is_expired,
                    "expires_at": iso_expires,
                    "scopes": scopes_list,
                    "xero_tenant_id": str(row.get("xero_tenant_id", "")),
                    "xero_tenant_name": str(row.get("xero_tenant_name", "")),
                    "connected_at": str(row.get("connected_at", "")),
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
