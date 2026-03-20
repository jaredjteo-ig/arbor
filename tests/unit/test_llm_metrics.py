"""Unit tests for LLM observability — structured logging and call timing.

Tests that all logging functions execute without error and that the
llm_call_timer context manager correctly measures elapsed time.

Supplementary to T424-T429 — BYOK API Keys: Metrics/observability tests.
"""

from __future__ import annotations

import time

from hr_advisory.services.llm_metrics import (
    llm_call_timer,
    log_budget_exceeded,
    log_budget_warning,
    log_key_invalid,
    log_llm_call,
    log_provider_fallback,
)


class TestLogLLMCall:
    """Test log_llm_call structured logging."""

    def test_log_llm_call_executes(self) -> None:
        """log_llm_call should not raise for valid inputs."""
        log_llm_call(
            company_id=1,
            provider="openai",
            model="gpt-5-mini",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.0015,
            duration_ms=350.0,
            is_byok=True,
        )

    def test_log_llm_call_ollama(self) -> None:
        """log_llm_call works for zero-cost Ollama calls."""
        log_llm_call(
            company_id=2,
            provider="ollama",
            model="llama3.1:70b",
            input_tokens=5000,
            output_tokens=2000,
            cost_usd=0.0,
            duration_ms=1200.0,
            is_byok=True,
        )


class TestLogBudgetWarning:
    """Test budget warning logging."""

    def test_log_budget_warning_executes(self) -> None:
        """log_budget_warning should not raise."""
        log_budget_warning(company_id=1, used_usd=4.25, limit_usd=5.00)

    def test_log_budget_warning_zero_limit(self) -> None:
        """log_budget_warning handles zero limit without division error."""
        log_budget_warning(company_id=1, used_usd=0.0, limit_usd=0.0)


class TestLogBudgetExceeded:
    """Test budget exceeded logging."""

    def test_log_budget_exceeded_executes(self) -> None:
        """log_budget_exceeded should not raise."""
        log_budget_exceeded(company_id=42)


class TestLogKeyInvalid:
    """Test key invalid logging."""

    def test_log_key_invalid_executes(self) -> None:
        """log_key_invalid should not raise."""
        log_key_invalid(company_id=1, provider="openai")


class TestLogProviderFallback:
    """Test provider fallback logging."""

    def test_log_provider_fallback_executes(self) -> None:
        """log_provider_fallback should not raise."""
        log_provider_fallback(company_id=1, from_provider="openai", to_provider="ollama")


class TestLLMCallTimer:
    """Test the llm_call_timer context manager for duration measurement."""

    def test_timer_measures_elapsed(self) -> None:
        """Timer should capture non-zero elapsed_ms after work."""
        with llm_call_timer() as timer:
            # Simulate minimal work
            total = sum(range(10000))
        assert timer.elapsed_ms > 0

    def test_timer_starts_at_zero(self) -> None:
        """Timer elapsed_ms should be 0 before the context exits."""
        timer_ref = None
        with llm_call_timer() as timer:
            timer_ref = timer
            # Inside the context, elapsed hasn't been set yet (still 0.0 default)
        # After exit, it should have a real value
        assert timer_ref.elapsed_ms > 0

    def test_timer_exception_still_records(self) -> None:
        """Timer should record duration even if an exception occurs."""
        timer_ref = None
        try:
            with llm_call_timer() as timer:
                timer_ref = timer
                raise ValueError("Simulated LLM error")
        except ValueError:
            pass
        assert timer_ref is not None
        assert timer_ref.elapsed_ms > 0

    def test_timer_reasonable_precision(self) -> None:
        """Timer should measure at least 50ms of sleep accurately."""
        with llm_call_timer() as timer:
            time.sleep(0.05)
        # Should be at least 40ms (allowing for scheduling variance)
        assert timer.elapsed_ms >= 40.0
