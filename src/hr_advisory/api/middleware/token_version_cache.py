"""Token version cache for instant JWT invalidation.

Provides a thread-safe in-memory cache mapping user_id -> token_version
with a 30-second TTL. On cache miss, fetches the current token_version
from the database via dataflow_crud.

This enables instant session termination when an employee is deactivated
or a password is reset: the user's token_version is incremented in the
database, the cache is invalidated, and the next request with the old
token_version will be rejected.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

# Default TTL: 30 seconds. Worst case, a terminated employee can make
# requests for 30 more seconds before the cache entry expires.
_DEFAULT_TTL_SECONDS = 30


class TokenVersionCache:
    """Thread-safe in-memory cache for user token versions.

    Each entry stores (token_version, expires_at) where expires_at is
    a monotonic clock timestamp. Entries older than TTL are treated as
    cache misses.
    """

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._cache: dict[int, tuple[int, float]] = {}  # user_id -> (token_version, expires_at)
        self._lock = threading.Lock()

    def get(self, user_id: int) -> int | None:
        """Get cached token_version for a user, or None if expired/missing."""
        with self._lock:
            entry = self._cache.get(user_id)
            if entry is None:
                return None
            tv, expires_at = entry
            if time.monotonic() > expires_at:
                del self._cache[user_id]
                return None
            return tv

    def set(self, user_id: int, token_version: int) -> None:
        """Cache a token_version for a user with TTL."""
        with self._lock:
            self._cache[user_id] = (token_version, time.monotonic() + self._ttl)

    def invalidate(self, user_id: int) -> None:
        """Remove a user's entry from the cache, forcing a DB lookup on next check."""
        with self._lock:
            self._cache.pop(user_id, None)

    def get_or_fetch(self, user_id: int) -> int:
        """Get token_version from cache, or fetch from DB on miss.

        Returns the current token_version (defaults to 1 if the user
        record has no token_version field or user is not found).
        """
        cached = self.get(user_id)
        if cached is not None:
            return cached

        # Cache miss — fetch from database
        try:
            from hr_advisory.services import dataflow_crud

            user_record = dataflow_crud.read("User", user_id)
            tv = (user_record or {}).get("token_version", 1)
        except Exception as exc:
            logger.warning(
                "Failed to fetch token_version for user %s, defaulting to 1: %s",
                user_id,
                exc,
            )
            tv = 1

        self.set(user_id, tv)
        return tv


# -- Singleton instance ------------------------------------------------------

_cache_instance: TokenVersionCache | None = None
_cache_lock = threading.Lock()


def get_token_version_cache() -> TokenVersionCache:
    """Get the singleton TokenVersionCache instance."""
    global _cache_instance

    if _cache_instance is not None:
        return _cache_instance

    with _cache_lock:
        if _cache_instance is not None:
            return _cache_instance

        _cache_instance = TokenVersionCache()
        return _cache_instance


def reset_token_version_cache() -> None:
    """Reset the singleton instance (for testing only)."""
    global _cache_instance
    with _cache_lock:
        _cache_instance = None
