"""Simple in-memory rate limiter for sensitive endpoints.

Uses a sliding window approach with per-company-id tracking.
Not suitable for multi-process deployments — use Redis-based
rate limiting in production.
"""

import time
import logging
from collections import OrderedDict, deque
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# Store: {key: deque([timestamp1, timestamp2, ...], maxlen=max_requests + 1)}
# T-RX05: Each key's deque is bounded to max_requests + 1 — exactly the smallest
# size that lets us reject a burst at the limit without losing any in-window
# entries. The OrderedDict is also bounded (MAX_RATE_KEYS) for global safety.
_request_log: OrderedDict[str, deque] = OrderedDict()
MAX_RATE_KEYS = 50_000

def _clean_old_entries(key: str, window_seconds: int) -> None:
    """Remove entries older than the window."""
    cutoff = time.time() - window_seconds
    if key in _request_log:
        dq = _request_log[key]
        while dq and dq[0] <= cutoff:
            dq.popleft()

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

    if len(_request_log.get(identifier, [])) >= max_requests:
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

    # Evict oldest entries if at capacity
    while len(_request_log) >= MAX_RATE_KEYS:
        _request_log.popitem(last=False)

    if identifier not in _request_log:
        _request_log[identifier] = deque(maxlen=max_requests + 1)
    _request_log[identifier].append(time.time())
    # Move to end so LRU eviction removes least-recently-used keys
    _request_log.move_to_end(identifier)
