"""Integration tests for CircuitBreaker and RateLimiter resilience layer.

Tests:
- Circuit state transitions: closed -> open -> half_open -> closed
- ExternalAPIUnavailable raised when circuit is open
- Recovery after timeout
- Error rate tracking
- RateLimiter window tracking and remaining count
- get_circuit() auto-creation
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from hr_advisory.mcp_servers.resilience import (
    CircuitBreaker,
    CircuitState,
    ExternalAPIUnavailable,
    RateLimiter,
    get_circuit,
)


# ---------------------------------------------------------------------------
# Circuit breaker state transitions
# ---------------------------------------------------------------------------


class TestCircuitStateTransitions:
    """Circuit breaker transitions: closed -> open -> half_open -> closed."""

    def test_initial_state_is_closed(self, circuit_breaker: CircuitBreaker):
        assert circuit_breaker.state == CircuitState.CLOSED

    async def test_stays_closed_on_success(self, circuit_breaker: CircuitBreaker):
        async def success():
            return "ok"

        result = await circuit_breaker.call(success)
        assert result == "ok"
        assert circuit_breaker.state == CircuitState.CLOSED

    async def test_stays_closed_below_threshold(self, circuit_breaker: CircuitBreaker):
        """Failures below the threshold keep the circuit closed."""

        async def failing():
            raise ConnectionError("down")

        for _ in range(circuit_breaker.failure_threshold - 1):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        assert circuit_breaker.state == CircuitState.CLOSED

    async def test_opens_after_threshold_failures(self, circuit_breaker: CircuitBreaker):
        """Circuit opens after reaching the failure threshold."""

        async def failing():
            raise ConnectionError("down")

        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        assert circuit_breaker.state == CircuitState.OPEN

    async def test_open_circuit_raises_unavailable(self, circuit_breaker: CircuitBreaker):
        """An open circuit raises ExternalAPIUnavailable without calling the function."""

        async def failing():
            raise ConnectionError("down")

        # Trip the breaker
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        call_count = 0

        async def should_not_run():
            nonlocal call_count
            call_count += 1
            return "ok"

        with pytest.raises(ExternalAPIUnavailable) as exc_info:
            await circuit_breaker.call(should_not_run)

        assert exc_info.value.service == "test_service"
        assert exc_info.value.retry_after == circuit_breaker.recovery_timeout
        assert call_count == 0, "Function must not be called when circuit is open"

    async def test_transitions_to_half_open_after_recovery_timeout(
        self, circuit_breaker: CircuitBreaker
    ):
        """After the recovery timeout, the circuit transitions to half_open."""

        async def failing():
            raise ConnectionError("down")

        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        assert circuit_breaker._state == CircuitState.OPEN

        # Simulate recovery timeout elapsing by patching time.monotonic
        future_time = time.monotonic() + circuit_breaker.recovery_timeout + 1
        with patch("hr_advisory.mcp_servers.resilience.time.monotonic", return_value=future_time):
            assert circuit_breaker.state == CircuitState.HALF_OPEN

    async def test_half_open_closes_on_success(self, circuit_breaker: CircuitBreaker):
        """A successful call in half_open state closes the circuit."""

        async def failing():
            raise ConnectionError("down")

        async def success():
            return "recovered"

        # Trip to open
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        # Fast-forward past recovery timeout
        future_time = time.monotonic() + circuit_breaker.recovery_timeout + 1
        with patch("hr_advisory.mcp_servers.resilience.time.monotonic", return_value=future_time):
            result = await circuit_breaker.call(success)

        assert result == "recovered"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker._failures == 0

    async def test_half_open_reopens_on_failure(self, circuit_breaker: CircuitBreaker):
        """A failed call in half_open state reopens the circuit."""

        async def failing():
            raise ConnectionError("still down")

        # Trip to open
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        # Fast-forward past recovery timeout
        future_time = time.monotonic() + circuit_breaker.recovery_timeout + 1
        with patch("hr_advisory.mcp_servers.resilience.time.monotonic", return_value=future_time):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        # Should be back to open (failures now exceed threshold again)
        assert circuit_breaker._state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# Error rate and metrics
# ---------------------------------------------------------------------------


class TestCircuitMetrics:
    """Error rate tracking and status reporting."""

    def test_initial_error_rate_is_zero(self, circuit_breaker: CircuitBreaker):
        assert circuit_breaker.error_rate == 0.0

    async def test_error_rate_after_mixed_calls(self, circuit_breaker: CircuitBreaker):
        async def success():
            return "ok"

        async def fail():
            raise ValueError("bad")

        await circuit_breaker.call(success)
        await circuit_breaker.call(success)
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail)

        assert circuit_breaker._total_calls == 3
        assert circuit_breaker._total_failures == 1
        assert abs(circuit_breaker.error_rate - 1 / 3) < 0.01

    def test_get_status_dict(self, circuit_breaker: CircuitBreaker):
        status = circuit_breaker.get_status()
        assert status["name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failures"] == 0
        assert status["failure_threshold"] == 3
        assert status["recovery_timeout"] == 1
        assert status["error_rate"] == 0.0
        assert status["total_calls"] == 0

    async def test_total_calls_increments(self, circuit_breaker: CircuitBreaker):
        async def success():
            return "ok"

        await circuit_breaker.call(success)
        await circuit_breaker.call(success)
        assert circuit_breaker._total_calls == 2

    async def test_last_success_updated(self, circuit_breaker: CircuitBreaker):
        async def success():
            return "ok"

        assert circuit_breaker._last_success_time == 0.0
        await circuit_breaker.call(success)
        assert circuit_breaker._last_success_time > 0.0


# ---------------------------------------------------------------------------
# Manual reset
# ---------------------------------------------------------------------------


class TestCircuitReset:
    """Manual circuit breaker reset."""

    async def test_reset_closes_open_circuit(self, circuit_breaker: CircuitBreaker):
        async def failing():
            raise ConnectionError("down")

        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        assert circuit_breaker._state == CircuitState.OPEN
        circuit_breaker.reset()
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker._failures == 0

    async def test_calls_succeed_after_reset(self, circuit_breaker: CircuitBreaker):
        async def failing():
            raise ConnectionError("down")

        async def success():
            return "ok"

        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing)

        circuit_breaker.reset()
        result = await circuit_breaker.call(success)
        assert result == "ok"


# ---------------------------------------------------------------------------
# get_circuit() factory
# ---------------------------------------------------------------------------


class TestGetCircuit:
    """get_circuit() retrieves known circuits or creates new ones."""

    def test_get_known_circuit(self):
        cb = get_circuit("xero")
        assert cb.name == "xero"
        assert cb.failure_threshold == 5  # Pre-configured value

    def test_get_unknown_circuit_creates_default(self):
        cb = get_circuit("brand_new_api")
        assert cb.name == "brand_new_api"
        assert cb.failure_threshold == 5  # CircuitBreaker default


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """Rate limiter window tracking."""

    def test_allows_calls_within_limit(self, rate_limiter: RateLimiter):
        assert rate_limiter.check("tenant_1", "xero") is True
        assert rate_limiter.check("tenant_1", "xero") is True
        assert rate_limiter.check("tenant_1", "xero") is True

    def test_blocks_calls_over_limit(self, rate_limiter: RateLimiter):
        for _ in range(3):
            rate_limiter.check("tenant_1", "xero")
        assert rate_limiter.check("tenant_1", "xero") is False

    def test_separate_tenants_have_separate_limits(self, rate_limiter: RateLimiter):
        for _ in range(3):
            rate_limiter.check("tenant_1", "xero")
        # tenant_1 is exhausted, but tenant_2 should still be allowed
        assert rate_limiter.check("tenant_2", "xero") is True

    def test_separate_providers_have_separate_limits(self, rate_limiter: RateLimiter):
        for _ in range(3):
            rate_limiter.check("tenant_1", "xero")
        # xero is exhausted for tenant_1, but qbo should be fine
        assert rate_limiter.check("tenant_1", "qbo") is True

    def test_remaining_count_decreases(self, rate_limiter: RateLimiter):
        assert rate_limiter.get_remaining("tenant_1", "xero") == 3
        rate_limiter.check("tenant_1", "xero")
        assert rate_limiter.get_remaining("tenant_1", "xero") == 2
        rate_limiter.check("tenant_1", "xero")
        assert rate_limiter.get_remaining("tenant_1", "xero") == 1
        rate_limiter.check("tenant_1", "xero")
        assert rate_limiter.get_remaining("tenant_1", "xero") == 0

    def test_window_resets_after_timeout(self, rate_limiter: RateLimiter):
        """After the window elapses, calls are allowed again."""
        for _ in range(3):
            rate_limiter.check("tenant_1", "xero")
        assert rate_limiter.check("tenant_1", "xero") is False

        # Simulate window expiry by backdating the recorded timestamps
        key = rate_limiter._key("tenant_1", "xero")
        old_time = time.monotonic() - rate_limiter.window_seconds - 1
        rate_limiter._calls[key] = [old_time] * 3

        assert rate_limiter.check("tenant_1", "xero") is True


# ---------------------------------------------------------------------------
# ExternalAPIUnavailable exception
# ---------------------------------------------------------------------------


class TestExternalAPIUnavailable:
    """Exception carries useful metadata."""

    def test_exception_message(self):
        exc = ExternalAPIUnavailable("cpf_board", 120)
        assert "cpf_board" in str(exc)
        assert "120" in str(exc)
        assert exc.service == "cpf_board"
        assert exc.retry_after == 120
