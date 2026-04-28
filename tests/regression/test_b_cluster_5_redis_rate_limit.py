"""Cluster 5 regression: T-RX07 Redis-backed rate limiter.

Verifies:
1. With a real Redis available, INCR + EXPIRE drives the limit and the count
   is visible in Redis (cross-process semantics).
2. With Redis unreachable, the limiter falls back to in-memory and STILL
   enforces the limit — there must never be a path that silently disables
   rate limiting.
3. Failing Redis connections back off so we don't pound on a dead server.

These tests use the local docker Postgres+Redis stack (or env REDIS_URL).
If Redis is not reachable, the Redis-backend test is skipped and only the
fallback test runs — that mirrors CI environments without Redis.
"""

from __future__ import annotations

import os

import pytest
from fastapi import HTTPException

from hr_advisory.api.middleware import rate_limit


# ── Detect if a real Redis is reachable for this test run ───────────


def _redis_is_reachable() -> bool:
    """Probe the configured Redis URL once."""
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return False
    try:
        import redis as _redis
    except ImportError:
        return False
    try:
        client = _redis.Redis.from_url(
            url, socket_connect_timeout=0.5, socket_timeout=0.5
        )
        client.ping()
        return True
    except Exception:
        return False


_REAL_REDIS = _redis_is_reachable()


@pytest.fixture(autouse=True)
def _isolate_state():
    """Drop in-memory + Redis state between tests so counts don't bleed."""
    rate_limit.reset_rate_limit_state()
    yield
    rate_limit.reset_rate_limit_state()


@pytest.mark.regression
@pytest.mark.skipif(not _REAL_REDIS, reason="Local Redis not reachable")
def test_t_rx07_redis_backend_enforces_limit_and_persists_count() -> None:
    """With Redis reachable, the limiter must use Redis and persist the count.

    The persistence is what makes T-RX07 valuable: in a multi-worker deploy,
    every worker increments the same key and they share the limit.
    """
    key = "tx07:redis_backend"
    for _ in range(3):
        rate_limit.check_rate_limit(
            key, max_requests=3, window_seconds=10, action_name="rx07-redis"
        )

    with pytest.raises(HTTPException) as excinfo:
        rate_limit.check_rate_limit(
            key, max_requests=3, window_seconds=10, action_name="rx07-redis"
        )
    assert excinfo.value.status_code == 429
    assert "Retry-After" in excinfo.value.headers

    # Confirm the active backend is actually Redis and the count is visible.
    client = rate_limit._get_redis_client()
    assert client is not None, "Redis client should be live"
    redis_count = client.get(f"rate:{key}".encode("utf-8"))
    assert redis_count is not None, "Redis must hold the rate counter"
    assert int(redis_count) >= 3


@pytest.mark.regression
def test_t_rx07_falls_back_to_in_memory_when_redis_unreachable(monkeypatch) -> None:
    """When REDIS_URL points at a closed port, the limiter must NOT silently
    disable rate limiting — it falls back to the in-memory limiter and still
    raises 429 on the (max_requests + 1)th call.
    """
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")

    key = "tx07:fallback"
    # Three calls under the limit succeed
    for _ in range(3):
        rate_limit.check_rate_limit(
            key, max_requests=3, window_seconds=10, action_name="rx07-fallback"
        )

    with pytest.raises(HTTPException) as excinfo:
        rate_limit.check_rate_limit(
            key, max_requests=3, window_seconds=10, action_name="rx07-fallback"
        )
    assert excinfo.value.status_code == 429

    # Confirm the active backend after the failure is None (i.e. in-memory).
    assert rate_limit._get_redis_client() is None, (
        "Redis should be marked unavailable after the connection fails"
    )


@pytest.mark.regression
def test_t_rx07_backs_off_after_failure(monkeypatch) -> None:
    """After Redis fails, the limiter must NOT try to reconnect on every call —
    it sets a backoff window so the dead server isn't hammered."""
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")

    # First call — triggers connection failure and sets the backoff
    rate_limit.check_rate_limit(
        "tx07:backoff", max_requests=10, window_seconds=10, action_name="rx07-backoff"
    )
    assert rate_limit._redis_unavailable_until > 0, (
        "After a failed connection, the limiter must record a backoff time"
    )
    backoff_set_at = rate_limit._redis_unavailable_until

    # Second call should not move the backoff forward (no retry yet)
    rate_limit.check_rate_limit(
        "tx07:backoff", max_requests=10, window_seconds=10, action_name="rx07-backoff"
    )
    assert rate_limit._redis_unavailable_until == backoff_set_at, (
        "Limiter retried Redis instead of honouring its own backoff window"
    )
