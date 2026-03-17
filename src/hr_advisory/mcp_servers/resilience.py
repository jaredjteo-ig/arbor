"""Circuit breaker and resilience patterns for external API calls.

Per-external-API circuit breakers prevent cascade failures when
external services go down. Each breaker has configurable failure
thresholds and recovery timeouts.

T206: Circuit Breaker + Resilience Layer
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal — requests flow through
    OPEN = "open"  # Failing — requests blocked
    HALF_OPEN = "half_open"  # Testing — one request allowed through


class ExternalAPIUnavailable(Exception):
    """Raised when a circuit breaker is open."""

    def __init__(self, service: str, retry_after: int):
        self.service = service
        self.retry_after = retry_after
        super().__init__(f"{service} is temporarily unavailable. Retry after {retry_after}s.")


class RateLimitExceeded(Exception):
    """Raised when a provider's rate limit has been exceeded."""

    def __init__(self, provider: str, retry_after: int, remaining: int = 0):
        self.provider = provider
        self.retry_after = retry_after
        self.remaining = remaining
        super().__init__(
            f"Rate limit exceeded for {provider}. "
            f"Retry after {retry_after}s ({remaining} calls remaining)."
        )


@dataclass
class CircuitBreaker:
    """Per-integration circuit breaker.

    States: closed (normal) -> open (failing) -> half_open (testing)

    Usage::

        breaker = CircuitBreaker("cpf_board", failure_threshold=3, recovery_timeout=120)

        async def submit_cpf():
            return await breaker.call(cpf_api.submit, data)
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    _failures: int = 0
    _state: CircuitState = CircuitState.CLOSED
    _last_failure_time: float = 0.0
    _last_success_time: float = 0.0
    _total_calls: int = 0
    _total_failures: int = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    @property
    def error_rate(self) -> float:
        if self._total_calls == 0:
            return 0.0
        return self._total_failures / self._total_calls

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute a function through the circuit breaker.

        Raises ExternalAPIUnavailable if the circuit is open.
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise ExternalAPIUnavailable(self.name, self.recovery_timeout)

        if current_state == CircuitState.HALF_OPEN:
            logger.info("Circuit %s half-open — testing with one request", self.name)

        self._total_calls += 1
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self) -> None:
        """Record a successful call."""
        self._last_success_time = time.monotonic()
        if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info("Circuit %s recovered — closing", self.name)
        self._state = CircuitState.CLOSED
        self._failures = 0

    def _on_failure(self, error: Exception) -> None:
        """Record a failed call."""
        self._failures += 1
        self._total_failures += 1
        self._last_failure_time = time.monotonic()

        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                "Circuit %s OPEN after %d consecutive failures (last: %s)",
                self.name,
                self._failures,
                type(error).__name__,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failures = 0
        logger.info("Circuit %s manually reset", self.name)

    def get_status(self) -> dict:
        """Return current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self._failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "error_rate": round(self.error_rate, 3),
            "total_calls": self._total_calls,
            "last_success": self._last_success_time,
            "last_failure": self._last_failure_time,
        }


class RateLimiter:
    """Per-tenant, per-provider rate limiter.

    Tracks call counts in a sliding window and blocks when limit is reached.
    """

    def __init__(self, max_calls: int, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = {}  # key -> [timestamps]

    def _key(self, tenant_id: str, provider: str) -> str:
        return f"{tenant_id}:{provider}"

    def check(self, tenant_id: str, provider: str) -> bool:
        """Return True if the call is allowed, False if rate limited."""
        key = self._key(tenant_id, provider)
        now = time.monotonic()

        if key not in self._calls:
            self._calls[key] = []

        # Remove old entries outside the window
        cutoff = now - self.window_seconds
        self._calls[key] = [t for t in self._calls[key] if t > cutoff]

        if len(self._calls[key]) >= self.max_calls:
            return False

        self._calls[key].append(now)
        return True

    def get_remaining(self, tenant_id: str, provider: str) -> int:
        """Return remaining calls in the current window."""
        key = self._key(tenant_id, provider)
        now = time.monotonic()
        cutoff = now - self.window_seconds
        calls = [t for t in self._calls.get(key, []) if t > cutoff]
        return max(0, self.max_calls - len(calls))


# Pre-configured circuit breakers for known external APIs
CIRCUITS: dict[str, CircuitBreaker] = {
    "cpf_board": CircuitBreaker("cpf_board", failure_threshold=3, recovery_timeout=120),
    "iras": CircuitBreaker("iras", failure_threshold=3, recovery_timeout=120),
    "mom": CircuitBreaker("mom", failure_threshold=3, recovery_timeout=120),
    "myinfo": CircuitBreaker("myinfo", failure_threshold=3, recovery_timeout=60),
    "data_gov_sg": CircuitBreaker("data_gov_sg", failure_threshold=5, recovery_timeout=30),
    "xero": CircuitBreaker("xero", failure_threshold=5, recovery_timeout=60),
    "quickbooks": CircuitBreaker("quickbooks", failure_threshold=5, recovery_timeout=60),
    "zoho": CircuitBreaker("zoho", failure_threshold=5, recovery_timeout=60),
    "dbs": CircuitBreaker("dbs", failure_threshold=3, recovery_timeout=300),
    "uob": CircuitBreaker("uob", failure_threshold=3, recovery_timeout=300),
    "ocbc": CircuitBreaker("ocbc", failure_threshold=3, recovery_timeout=300),
    "aspire": CircuitBreaker("aspire", failure_threshold=5, recovery_timeout=60),
    "wise": CircuitBreaker("wise", failure_threshold=5, recovery_timeout=60),
    "resend": CircuitBreaker("resend", failure_threshold=10, recovery_timeout=30),
    "ses": CircuitBreaker("ses", failure_threshold=10, recovery_timeout=30),
    "whatsapp": CircuitBreaker("whatsapp", failure_threshold=5, recovery_timeout=60),
    "telegram": CircuitBreaker("telegram", failure_threshold=5, recovery_timeout=30),
    "slack": CircuitBreaker("slack", failure_threshold=5, recovery_timeout=60),
    "teams": CircuitBreaker("teams", failure_threshold=5, recovery_timeout=60),
    "google_calendar": CircuitBreaker("google_calendar", failure_threshold=5, recovery_timeout=60),
    "microsoft_graph": CircuitBreaker("microsoft_graph", failure_threshold=5, recovery_timeout=60),
    "talenox": CircuitBreaker("talenox", failure_threshold=5, recovery_timeout=60),
    "hreasily": CircuitBreaker("hreasily", failure_threshold=5, recovery_timeout=60),
    "skillsfuture": CircuitBreaker("skillsfuture", failure_threshold=5, recovery_timeout=60),
    "acra": CircuitBreaker("acra", failure_threshold=3, recovery_timeout=120),
}

# Pre-configured rate limiters
RATE_LIMITERS: dict[str, RateLimiter] = {
    "xero": RateLimiter(max_calls=60, window_seconds=60),  # 60/min
    "quickbooks": RateLimiter(max_calls=500, window_seconds=60),  # 500/min
    "zoho": RateLimiter(max_calls=40, window_seconds=60),  # ~2500/day ≈ 40/min conservative
    "data_gov_sg": RateLimiter(max_calls=30, window_seconds=10),  # 30/10s
    "telegram": RateLimiter(max_calls=30, window_seconds=1),  # 30 msg/s
    "whatsapp": RateLimiter(max_calls=80, window_seconds=1),  # 80 msg/s
}


def get_circuit(name: str) -> CircuitBreaker:
    """Get a circuit breaker by name, creating a default if not found."""
    if name not in CIRCUITS:
        CIRCUITS[name] = CircuitBreaker(name)
    return CIRCUITS[name]


def get_all_circuit_statuses() -> list[dict]:
    """Return status of all circuit breakers."""
    return [cb.get_status() for cb in CIRCUITS.values()]


def check_rate_limit(tenant_id: str, provider: str) -> None:
    """Check rate limit for a provider and raise if exceeded.

    Centralized helper that adapters call before each API request.
    If no rate limiter is configured for the provider, passes through silently.

    Args:
        tenant_id: AITE company/tenant ID.
        provider: Provider key matching RATE_LIMITERS (e.g. "xero", "zoho").

    Raises:
        RateLimitExceeded: If the tenant has exceeded the provider's rate limit.
    """
    limiter = RATE_LIMITERS.get(provider)
    if limiter is None:
        return

    if not limiter.check(tenant_id, provider):
        remaining = limiter.get_remaining(tenant_id, provider)
        raise RateLimitExceeded(
            provider=provider,
            retry_after=limiter.window_seconds,
            remaining=remaining,
        )
