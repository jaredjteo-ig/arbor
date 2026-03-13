"""Response caching with TTL management (T057).

Provides in-memory caching for:
- Calculator results (long TTL — rates change infrequently)
- KB retrieval results (medium TTL — provisions are stable)
- Advisory responses (short TTL — context-dependent)

In production, backed by Redis for shared cache across instances.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


@dataclass
class CacheConfig:
    """Configuration for a cache category."""

    category: str
    ttl_seconds: int
    max_entries: int


@dataclass
class CacheEntry:
    """A single cache entry."""

    key: str
    category: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=datetime.now)
    hit_count: int = 0


# Default cache configurations
CACHE_CONFIGS: dict[str, CacheConfig] = {
    "calculator": CacheConfig(
        category="calculator",
        ttl_seconds=86400,  # 24 hours — rates rarely change
        max_entries=1000,
    ),
    "kb_retrieval": CacheConfig(
        category="kb_retrieval",
        ttl_seconds=3600,  # 1 hour — provisions are stable
        max_entries=500,
    ),
    "advisory": CacheConfig(
        category="advisory",
        ttl_seconds=300,  # 5 minutes — context-dependent
        max_entries=200,
    ),
    "provision_detail": CacheConfig(
        category="provision_detail",
        ttl_seconds=7200,  # 2 hours
        max_entries=300,
    ),
}


class ResponseCache:
    """In-memory response cache with TTL and LRU eviction.

    In production, replaced by Redis cache with the same interface.
    """

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._configs = dict(CACHE_CONFIGS)
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    @staticmethod
    def _make_key(category: str, params: dict[str, Any]) -> str:
        """Generate a deterministic cache key from category + params."""
        serialised = json.dumps(params, sort_keys=True, default=str)
        digest = hashlib.sha256(serialised.encode()).hexdigest()[:16]
        return f"{category}:{digest}"

    def get(
        self,
        category: str,
        params: dict[str, Any],
    ) -> Optional[Any]:
        """Get a cached value if it exists and hasn't expired."""
        key = self._make_key(category, params)
        entry = self._entries.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return None
        if datetime.now() > entry.expires_at:
            del self._entries[key]
            self._stats["misses"] += 1
            return None
        entry.hit_count += 1
        self._stats["hits"] += 1
        return entry.value

    def set(
        self,
        category: str,
        params: dict[str, Any],
        value: Any,
    ) -> CacheEntry:
        """Store a value in the cache."""
        config = self._configs.get(category)
        ttl = config.ttl_seconds if config else 300
        max_entries = config.max_entries if config else 100

        key = self._make_key(category, params)
        now = datetime.now()
        entry = CacheEntry(
            key=key,
            category=category,
            value=value,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )
        self._entries[key] = entry

        # Evict if over capacity (LRU by hit_count)
        category_entries = [e for e in self._entries.values() if e.category == category]
        if len(category_entries) > max_entries:
            sorted_entries = sorted(category_entries, key=lambda e: e.hit_count)
            to_evict = sorted_entries[: len(category_entries) - max_entries]
            for e in to_evict:
                self._entries.pop(e.key, None)
                self._stats["evictions"] += 1

        return entry

    def invalidate(self, category: str) -> int:
        """Invalidate all entries in a category. Returns count removed."""
        keys_to_remove = [k for k, v in self._entries.items() if v.category == category]
        for key in keys_to_remove:
            del self._entries[key]
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries.clear()

    @property
    def stats(self) -> dict[str, object]:
        """Get cache hit/miss statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = round(self._stats["hits"] / total * 100, 1) if total > 0 else 0.0
        return {
            **self._stats,
            "total_entries": len(self._entries),
            "hit_rate_percent": hit_rate,
        }


# ── Singleton cache instance ────────────────────────────────

_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get the singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache
