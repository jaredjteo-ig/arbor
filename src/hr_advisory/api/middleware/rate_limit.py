"""Rate limiter for sensitive endpoints.

The primary backend is Redis (`INCR`/`EXPIRE`) so limits hold across multiple
worker processes and containers. If Redis is unreachable (URL unset, network
failure, server down) we fall back to a per-process in-memory sliding-window
limiter so the application still rate-limits — just at the per-process level.

Production deploys MUST set ``REDIS_URL`` (the platform already does).

Per ``rules/zero-tolerance.md``: failures fall back loudly (logged) but never
silently disable rate limiting.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict, deque
from typing import Optional

from fastapi import HTTPException

try:
    import redis  # type: ignore[import-not-found]
    from redis.exceptions import RedisError  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover — redis is in pyproject extras
    redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)

# ── In-memory fallback store ────────────────────────────────────────
# T-RX05: per-key deques bounded to max_requests + 1 — exactly the smallest
# size that lets us reject a burst at the limit without losing any in-window
# entries. The OrderedDict is also bounded (MAX_RATE_KEYS) for global safety.
_request_log: OrderedDict[str, deque] = OrderedDict()
MAX_RATE_KEYS = 50_000

# ── Redis client (lazy, with backoff after a failure) ───────────────
_redis_client: Optional["redis.Redis"] = None
_redis_init_lock = threading.Lock()
_redis_unavailable_until: float = 0.0
_REDIS_RETRY_SECONDS = 30  # don't pound on a dead Redis; back off then retry


def _build_redis_client() -> Optional["redis.Redis"]:
    """Construct and ping a Redis client; return None on any failure.

    Failures are logged and we back off ``_REDIS_RETRY_SECONDS`` before
    trying again.
    """
    global _redis_unavailable_until

    if redis is None:
        logger.info("redis package not installed — rate limiter using in-memory only")
        _redis_unavailable_until = time.time() + _REDIS_RETRY_SECONDS
        return None

    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        logger.info("REDIS_URL not set — rate limiter using in-memory only")
        _redis_unavailable_until = time.time() + _REDIS_RETRY_SECONDS
        return None

    try:
        client = redis.Redis.from_url(
            url,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            decode_responses=False,
        )
        client.ping()
        logger.info("Rate limiter using Redis backend (url=%s)", url)
        return client
    except (RedisError, OSError) as exc:
        logger.warning(
            "Redis unavailable for rate limiting (%s); falling back to in-memory "
            "for %ds",
            exc,
            _REDIS_RETRY_SECONDS,
        )
        _redis_unavailable_until = time.time() + _REDIS_RETRY_SECONDS
        return None


def _get_redis_client() -> Optional["redis.Redis"]:
    """Return a healthy Redis client, or None if Redis is unreachable.

    Honors a backoff window after a failure so we don't pound on a dead
    Redis with every request.
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    if time.time() < _redis_unavailable_until:
        return None

    with _redis_init_lock:
        if _redis_client is not None:
            return _redis_client
        if time.time() < _redis_unavailable_until:
            return None
        _redis_client = _build_redis_client()
        return _redis_client


def _mark_redis_failed(exc: BaseException) -> None:
    """Drop the cached client and back off."""
    global _redis_client, _redis_unavailable_until
    logger.warning(
        "Redis rate-limit operation failed (%s); falling back to in-memory for %ds",
        exc,
        _REDIS_RETRY_SECONDS,
    )
    _redis_client = None
    _redis_unavailable_until = time.time() + _REDIS_RETRY_SECONDS


def _check_via_redis(
    client: "redis.Redis",
    identifier: str,
    window_seconds: int,
) -> Optional[int]:
    """INCR + EXPIRE the rate key; return current count, or None on Redis error.

    Uses a pipeline so the increment and TTL are sent in one round-trip.
    ``EXPIRE ... NX`` only sets the TTL on the first increment in a window —
    subsequent increments don't reset the window.
    """
    redis_key = f"rate:{identifier}".encode("utf-8")
    try:
        pipe = client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds, nx=True)
        results = pipe.execute()
        return int(results[0])
    except (RedisError, OSError) as exc:
        _mark_redis_failed(exc)
        return None


# ── In-memory implementation (fallback) ─────────────────────────────


def _clean_old_entries(key: str, window_seconds: int) -> None:
    """Remove entries older than the window."""
    cutoff = time.time() - window_seconds
    if key in _request_log:
        dq = _request_log[key]
        while dq and dq[0] <= cutoff:
            dq.popleft()


def _check_in_memory(
    identifier: str,
    max_requests: int,
    window_seconds: int,
    action_name: str,
) -> None:
    """Sliding-window per-process fallback. Raises 429 on excess."""
    _clean_old_entries(identifier, window_seconds)

    if len(_request_log.get(identifier, [])) >= max_requests:
        logger.warning(
            "Rate limit exceeded (in-memory): %s (key=%s, limit=%d/%ds)",
            action_name,
            identifier,
            max_requests,
            window_seconds,
        )
        raise HTTPException(
            status_code=429,
            detail=(
                f"Too many requests for {action_name}. "
                f"Please try again in {window_seconds} seconds."
            ),
            headers={"Retry-After": str(window_seconds)},
        )

    while len(_request_log) >= MAX_RATE_KEYS:
        _request_log.popitem(last=False)

    if identifier not in _request_log:
        _request_log[identifier] = deque(maxlen=max_requests + 1)
    _request_log[identifier].append(time.time())
    _request_log.move_to_end(identifier)


# ── Public API ──────────────────────────────────────────────────────


def check_rate_limit(
    identifier: str,
    max_requests: int,
    window_seconds: int,
    action_name: str = "this action",
) -> None:
    """Enforce a rate limit on ``identifier``. Raises 429 if exceeded.

    Args:
        identifier: Unique key (e.g., ``f"hire:{company_id}"``). Will be
            namespaced with ``rate:`` in Redis to avoid collisions with other
            data.
        max_requests: Maximum requests allowed in the window.
        window_seconds: Window size in seconds (Redis backend uses fixed-window
            TTL; in-memory uses sliding window).
        action_name: Human-readable name for the 429 detail.
    """
    client = _get_redis_client()
    if client is not None:
        count = _check_via_redis(client, identifier, window_seconds)
        if count is not None:
            if count > max_requests:
                logger.warning(
                    "Rate limit exceeded (redis): %s (key=%s, count=%d, limit=%d/%ds)",
                    action_name,
                    identifier,
                    count,
                    max_requests,
                    window_seconds,
                )
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Too many requests for {action_name}. "
                        f"Please try again in {window_seconds} seconds."
                    ),
                    headers={"Retry-After": str(window_seconds)},
                )
            return

    # Redis unavailable or just failed mid-call — use in-memory fallback.
    _check_in_memory(identifier, max_requests, window_seconds, action_name)


def reset_rate_limit_state() -> None:
    """Test/dev helper: drop in-memory and Redis state for the limiter.

    Production callers should never invoke this. Tests use it between
    cases to avoid cross-test pollution.
    """
    global _redis_client, _redis_unavailable_until

    _request_log.clear()

    client = _redis_client
    if client is not None:
        try:
            for key in client.scan_iter(match="rate:*"):
                client.delete(key)
        except (RedisError, OSError) as exc:
            logger.warning("Could not flush Redis rate-limit keys (%s)", exc)

    _redis_client = None
    _redis_unavailable_until = 0.0
