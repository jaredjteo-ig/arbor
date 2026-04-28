"""Unit tests for the rate limiter (T-RX05 / T-RX07).

The in-memory limiter uses ``collections.deque`` bounded to
``max_requests + 1``. These tests guard that bound: hammering the limiter
with more requests than ``maxlen`` must NOT cause unbounded memory growth.

T-RX07 added a Redis backend. These tests target the in-memory fallback,
so the autouse fixture points REDIS_URL at a closed port and resets all
limiter state between tests.
"""

from __future__ import annotations

import time

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _isolate_rate_log(monkeypatch):
    """Force Redis-unreachable + clear all limiter state for each test."""
    from hr_advisory.api.middleware import rate_limit as rl

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    rl.reset_rate_limit_state()
    yield
    rl.reset_rate_limit_state()


class TestDequeBounded:
    """T-RX05: per-key deques must be bounded by ``max_requests + 1``."""

    def test_per_key_deque_bound_holds_under_burst(self):
        """Hammer a single key with > maxlen requests; deque size is capped."""
        from hr_advisory.api.middleware import rate_limit as rl

        max_requests = 5
        identifier = "burst:co-1"

        # Fire 200 calls. Most will raise 429, but the limiter must not
        # accumulate more than max_requests + 1 entries for the key.
        for _ in range(200):
            try:
                rl.check_rate_limit(
                    identifier,
                    max_requests=max_requests,
                    window_seconds=3600,
                    action_name="burst test",
                )
            except HTTPException as exc:
                # Expected once we exceed the limit.
                assert exc.status_code == 429

        dq = rl._request_log[identifier]
        assert dq.maxlen == max_requests + 1, (
            f"deque maxlen={dq.maxlen} does not match max_requests+1={max_requests + 1}"
        )
        assert len(dq) <= dq.maxlen, (
            f"deque size {len(dq)} exceeded its maxlen {dq.maxlen} — "
            f"unbounded growth detected"
        )

    def test_log_uses_deque_not_list(self):
        """Defensive: container must be a deque (memory-bounded)."""
        from collections import deque

        from hr_advisory.api.middleware import rate_limit as rl

        identifier = "container-check:co-2"
        try:
            rl.check_rate_limit(
                identifier, max_requests=3, window_seconds=60,
            )
        except HTTPException:
            pass
        assert isinstance(rl._request_log[identifier], deque)

    def test_old_entries_eviction_keeps_size_small(self):
        """When the window slides, _clean_old_entries pops the deque's left."""
        from hr_advisory.api.middleware import rate_limit as rl

        identifier = "slide:co-3"
        # Pre-populate with timestamps that are well outside the window.
        # Use a 1s window, then pause briefly so old entries become stale.
        try:
            rl.check_rate_limit(identifier, max_requests=2, window_seconds=1)
        except HTTPException:
            pass
        # Mutate the deque to simulate old timestamps without sleeping.
        dq = rl._request_log[identifier]
        old_ts = time.time() - 10.0  # well before any 1s window
        dq.clear()
        dq.append(old_ts)
        dq.append(old_ts)

        # New call with the same window should clean old entries first.
        rl.check_rate_limit(identifier, max_requests=2, window_seconds=1)
        assert len(rl._request_log[identifier]) == 1, (
            "old entries should have been evicted before recording new one"
        )


class TestGlobalLRUBound:
    """The OrderedDict that maps key -> deque is also bounded (MAX_RATE_KEYS)."""

    def test_global_log_size_is_bounded(self):
        """Loading more than MAX_RATE_KEYS distinct keys evicts the oldest."""
        from hr_advisory.api.middleware import rate_limit as rl

        # Temporarily lower the cap so the test stays fast.
        original = rl.MAX_RATE_KEYS
        try:
            rl.MAX_RATE_KEYS = 50
            for i in range(120):
                try:
                    rl.check_rate_limit(
                        f"lru:{i}",
                        max_requests=1,
                        window_seconds=60,
                    )
                except HTTPException:
                    pass
            assert len(rl._request_log) <= rl.MAX_RATE_KEYS, (
                f"global log size {len(rl._request_log)} exceeds MAX_RATE_KEYS "
                f"{rl.MAX_RATE_KEYS}"
            )
        finally:
            rl.MAX_RATE_KEYS = original
