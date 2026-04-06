"""Simple in-memory rate limiter for sensitive endpoints.

Uses a sliding window approach with per-company-id tracking.
Not suitable for multi-process deployments — use Redis-based
rate limiting in production.

Uses an OrderedDict with LRU eviction to bound memory usage.
Maximum of MAX_RATE_KEYS entries; oldest keys are evicted when
the limit is reached.
"""

import time
import logging
from collections import OrderedDict
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# Maximum number of rate-limit keys tracked in memory.
# Prevents unbounded memory growth in long-running processes.
MAX_RATE_KEYS = 50000

# Store: {key: [timestamp1, timestamp2, ...]} with LRU eviction
_request_log: OrderedDict[str, list[float]] = OrderedDict()

def _clean_old_entries(key: str, window_seconds: int) -> None:
    """Remove entries older than the window."""
    if key not in _request_log:
        return
    cutoff = time.time() - window_seconds
    _request_log[key] = [t for t in _request_log[key] if t > cutoff]
    # Remove the key entirely if no entries remain
    if not _request_log[key]:
        del _request_log[key]

def check_rate_limit(
    identifier: str,
    max_requests: int,
    window_seconds: int,
    action_name: str = "this action",
) -> None:
    """Check rate limit and raise 429 if exceeded.

    Args:
        identifier: Unique key (e.g., f"hire:{company_id}")
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        action_name: Human-readable action name for error message
    """
    _clean_old_entries(identifier, window_seconds)

    if identifier in _request_log and len(_request_log[identifier]) >= max_requests:
        retry_after = window_seconds
        logger.warning(
            "Rate limit exceeded: %s (key=%s, limit=%d/%ds)",
            action_name, identifier, max_requests, window_seconds,
        )
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests for {action_name}. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # LRU eviction: if at capacity, remove the oldest key
    while len(_request_log) >= MAX_RATE_KEYS:
        evicted_key, _ = _request_log.popitem(last=False)
        logger.debug("Rate limiter evicted oldest key: %s", evicted_key)

    # Record the request and move to end for LRU ordering
    if identifier not in _request_log:
        _request_log[identifier] = []
    _request_log[identifier].append(time.time())
    _request_log.move_to_end(identifier)
