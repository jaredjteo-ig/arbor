"""Server-side JWT token blocklist for revocation.

Addresses red team finding H-4: "No server-side token revocation."

Provides an in-memory blocklist with automatic expiry cleanup.
When Redis is available (REDIS_URL configured), uses Redis for persistence
across process restarts.

Usage:
    from hr_advisory.api.middleware.token_blocklist import get_blocklist

    blocklist = get_blocklist()
    blocklist.revoke_token(jti="abc123", expires_at=1700000000)
    blocklist.is_revoked(jti="abc123")  # True
"""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TokenBlocklist(ABC):
    """Abstract base for token blocklist implementations."""

    @abstractmethod
    def revoke_token(self, jti: str, expires_at: int) -> None:
        """Mark a token as revoked.

        Args:
            jti: The JWT ID to revoke.
            expires_at: Unix timestamp when the token naturally expires.
                        The blocklist entry is kept until this time.

        Raises:
            ValueError: If jti is empty.
        """

    @abstractmethod
    def is_revoked(self, jti: str) -> bool:
        """Check whether a token has been revoked.

        Args:
            jti: The JWT ID to check.

        Returns:
            True if the token has been revoked, False otherwise.

        Raises:
            ValueError: If jti is empty.
        """

    @abstractmethod
    def cleanup_expired(self) -> None:
        """Remove expired entries to prevent unbounded memory growth."""


class InMemoryBlocklist(TokenBlocklist):
    """Thread-safe in-memory token blocklist.

    Stores revoked JTIs with their expiry timestamps.
    Entries are automatically cleaned up when cleanup_expired() is called.
    Cleanup also runs periodically during revoke_token() calls to prevent
    unbounded memory growth.
    """

    # Run cleanup every 100 revocations to keep memory bounded
    _CLEANUP_INTERVAL = 100

    def __init__(self) -> None:
        self._revoked: dict[str, int] = {}  # jti -> expires_at
        self._lock = threading.Lock()
        self._revocation_count = 0

    def revoke_token(self, jti: str, expires_at: int) -> None:
        """Mark a token as revoked in the in-memory store.

        Args:
            jti: The JWT ID to revoke.
            expires_at: Unix timestamp when the token naturally expires.

        Raises:
            ValueError: If jti is empty.
        """
        if not jti:
            raise ValueError("JTI must not be empty")

        with self._lock:
            self._revoked[jti] = expires_at
            self._revocation_count += 1

            # Periodic cleanup to prevent memory leak
            if self._revocation_count % self._CLEANUP_INTERVAL == 0:
                self._cleanup_locked()

        logger.info("Token revoked: jti=%s, expires_at=%s", jti, expires_at)

    def is_revoked(self, jti: str) -> bool:
        """Check whether a token JTI has been revoked.

        Args:
            jti: The JWT ID to check.

        Returns:
            True if the token is in the blocklist, False otherwise.

        Raises:
            ValueError: If jti is empty.
        """
        if not jti:
            raise ValueError("JTI must not be empty")

        with self._lock:
            return jti in self._revoked

    def cleanup_expired(self) -> None:
        """Remove expired entries from the blocklist."""
        with self._lock:
            self._cleanup_locked()

    def _cleanup_locked(self) -> None:
        """Internal cleanup, must be called with self._lock held."""
        now = int(time.time())
        expired_jtis = [jti for jti, exp in self._revoked.items() if exp <= now]
        for jti in expired_jtis:
            del self._revoked[jti]
        if expired_jtis:
            logger.info("Cleaned up %d expired blocklist entries", len(expired_jtis))


class RedisBlocklist(TokenBlocklist):
    """Redis-backed token blocklist.

    Uses Redis SET with TTL so entries auto-expire without manual cleanup.
    Each revoked JTI is stored as a key with prefix 'blocklist:'.
    """

    _KEY_PREFIX = "blocklist:"

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    def revoke_token(self, jti: str, expires_at: int) -> None:
        """Mark a token as revoked in Redis with auto-expiry.

        Args:
            jti: The JWT ID to revoke.
            expires_at: Unix timestamp when the token naturally expires.

        Raises:
            ValueError: If jti is empty.
        """
        if not jti:
            raise ValueError("JTI must not be empty")

        ttl = max(expires_at - int(time.time()), 1)
        key = f"{self._KEY_PREFIX}{jti}"
        self._redis.setex(key, ttl, "1")
        logger.info("Token revoked in Redis: jti=%s, ttl=%ds", jti, ttl)

    def is_revoked(self, jti: str) -> bool:
        """Check whether a token JTI has been revoked in Redis.

        Args:
            jti: The JWT ID to check.

        Returns:
            True if the token is in the Redis blocklist, False otherwise.

        Raises:
            ValueError: If jti is empty.
        """
        if not jti:
            raise ValueError("JTI must not be empty")

        key = f"{self._KEY_PREFIX}{jti}"
        return self._redis.exists(key) > 0

    def cleanup_expired(self) -> None:
        """No-op for Redis: TTL handles expiry automatically."""


# ── Singleton blocklist instance ──────────────────────────────

_blocklist_instance: TokenBlocklist | None = None
_blocklist_lock = threading.Lock()


def get_blocklist() -> TokenBlocklist:
    """Get the singleton blocklist instance.

    Tries to connect to Redis (from REDIS_URL env var). If Redis is
    unavailable, falls back to the in-memory implementation.

    Returns:
        A TokenBlocklist instance (Redis-backed or in-memory).
    """
    global _blocklist_instance

    if _blocklist_instance is not None:
        return _blocklist_instance

    with _blocklist_lock:
        # Double-check after acquiring lock
        if _blocklist_instance is not None:
            return _blocklist_instance

        _blocklist_instance = _try_redis_blocklist()
        if _blocklist_instance is None:
            logger.info("Redis unavailable, using in-memory token blocklist")
            _blocklist_instance = InMemoryBlocklist()
        else:
            logger.info("Using Redis-backed token blocklist")

        return _blocklist_instance


def _try_redis_blocklist() -> RedisBlocklist | None:
    """Attempt to create a Redis-backed blocklist.

    Returns None if Redis is unavailable or redis package is not installed.
    Validates that the Redis URL uses a safe scheme (redis:// or rediss://).
    """
    import os

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None

    # Validate URL scheme to prevent injection via malformed URLs
    if not redis_url.startswith(("redis://", "rediss://")):
        logger.warning(
            "REDIS_URL has invalid scheme (must be redis:// or rediss://). "
            "Falling back to in-memory blocklist."
        )
        return None

    try:
        import redis

        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return RedisBlocklist(client)
    except Exception as exc:
        logger.warning("Could not connect to Redis for token blocklist: %s", exc)
        return None


def reset_blocklist() -> None:
    """Reset the singleton blocklist instance (for testing only)."""
    global _blocklist_instance
    with _blocklist_lock:
        _blocklist_instance = None
