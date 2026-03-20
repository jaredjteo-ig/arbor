"""Unit tests for LLM budget enforcement — check_budget and record_usage.

Tests budget checking at various usage levels, cost calculation for
different models, NaN/Inf/negative token rejection, and MODEL_PRICING
completeness.

T425 — BYOK API Keys: Budget service unit tests.
"""

from __future__ import annotations

import math
import sys
from unittest.mock import MagicMock, patch

import pytest

# Prevent Kaizen import chain (pre-existing SDK version mismatch)
_kaizen_mods = [
    "kaizen",
    "kaizen.core",
    "kaizen.core.base_agent",
    "kaizen.memory",
    "kaizen.config",
    "kaizen.config.providers",
    "kaizen.signatures",
    "kaizen.core.workflow_generator",
    "kaizen.nodes",
    "kaizen.nodes.ai",
    "kaizen.nodes.ai.llm_agent",
]
for _m in _kaizen_mods:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

from hr_advisory.services.llm_budget import (
    BUDGET_WARNING_THRESHOLD,
    DEFAULT_MONTHLY_BUDGET_USD,
    MODEL_PRICING,
    BudgetCheckResult,
    _estimate_cost,
    check_budget,
    record_usage,
)


# ---------------------------------------------------------------------------
# Helpers — mock _get_or_create_usage and _execute_node to avoid DataFlow
# ---------------------------------------------------------------------------


def _mock_usage(
    estimated_cost: float = 0.0,
    query_count: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    usage_id: int = 1,
) -> dict:
    """Build a mock usage record dict matching DataFlow shape."""
    return {
        "id": usage_id,
        "company_id": 1,
        "month": "2026-03-01",
        "query_count": query_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost": estimated_cost,
    }


# ---------------------------------------------------------------------------
# BudgetCheckResult
# ---------------------------------------------------------------------------


class TestBudgetCheckResult:
    """Test BudgetCheckResult dataclass and serialization."""

    def test_to_dict(self) -> None:
        """to_dict() serializes all fields with proper rounding."""
        result = BudgetCheckResult(
            allowed=True,
            remaining_usd=3.14159,
            warning=False,
            used_usd=1.85841,
            query_count=5,
            limit_usd=5.00,
        )
        d = result.to_dict()
        assert d["allowed"] is True
        assert d["remaining_usd"] == 3.1416  # rounded to 4 decimals
        assert d["warning"] is False
        assert d["used_usd"] == 1.8584
        assert d["query_count"] == 5
        assert d["limit_usd"] == 5.00


# ---------------------------------------------------------------------------
# check_budget
# ---------------------------------------------------------------------------


class TestCheckBudget:
    """Test check_budget() at various usage levels."""

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_under_budget_allowed(self, mock_get_usage) -> None:
        """Under budget: allowed=True, warning=False."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=1.00, query_count=3)

        result = check_budget(company_id=1, budget_limit_usd=5.00)
        assert result.allowed is True
        assert result.warning is False
        assert result.remaining_usd == pytest.approx(4.00)
        assert result.used_usd == pytest.approx(1.00)
        assert result.limit_usd == pytest.approx(5.00)
        assert result.query_count == 3

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_at_80_percent_shows_warning(self, mock_get_usage) -> None:
        """At 80% usage: allowed=True, warning=True."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=4.00, query_count=10)

        result = check_budget(company_id=1, budget_limit_usd=5.00)
        assert result.allowed is True
        assert result.warning is True
        assert result.remaining_usd == pytest.approx(1.00)

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_at_90_percent_shows_warning(self, mock_get_usage) -> None:
        """At 90% usage: allowed=True, warning=True."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=4.50, query_count=15)

        result = check_budget(company_id=1, budget_limit_usd=5.00)
        assert result.allowed is True
        assert result.warning is True

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_at_100_percent_blocked(self, mock_get_usage) -> None:
        """At 100% usage: allowed=False."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=5.00, query_count=20)

        result = check_budget(company_id=1, budget_limit_usd=5.00)
        assert result.allowed is False
        assert result.warning is True
        assert result.remaining_usd == 0.0

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_over_budget_blocked(self, mock_get_usage) -> None:
        """Over budget: allowed=False, remaining clamped to 0."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=7.50, query_count=25)

        result = check_budget(company_id=1, budget_limit_usd=5.00)
        assert result.allowed is False
        assert result.remaining_usd == 0.0

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_default_budget_limit(self, mock_get_usage) -> None:
        """Without explicit limit, uses DEFAULT_MONTHLY_BUDGET_USD ($5)."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=0.0)

        result = check_budget(company_id=1)
        assert result.limit_usd == DEFAULT_MONTHLY_BUDGET_USD
        assert result.allowed is True

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_zero_budget_blocks_everything(self, mock_get_usage) -> None:
        """A $0 budget should block all usage."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=0.0)

        result = check_budget(company_id=1, budget_limit_usd=0.0)
        assert result.allowed is False
        assert result.warning is True

    def test_nan_budget_limit_blocks(self) -> None:
        """NaN budget limit should be rejected (fail-closed)."""
        result = check_budget(company_id=1, budget_limit_usd=float("nan"))
        assert result.allowed is False
        assert result.warning is True
        assert result.limit_usd == 0.0

    def test_inf_budget_limit_blocks(self) -> None:
        """Inf budget limit should be rejected (fail-closed)."""
        result = check_budget(company_id=1, budget_limit_usd=float("inf"))
        assert result.allowed is False
        assert result.warning is True

    def test_negative_budget_limit_blocks(self) -> None:
        """Negative budget limit should be rejected (fail-closed)."""
        result = check_budget(company_id=1, budget_limit_usd=-10.0)
        assert result.allowed is False

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_nan_usage_cost_blocks(self, mock_get_usage) -> None:
        """NaN in stored usage cost should trigger fail-closed."""
        mock_get_usage.return_value = _mock_usage(estimated_cost=float("nan"))

        result = check_budget(company_id=1, budget_limit_usd=5.00)
        assert result.allowed is False


# ---------------------------------------------------------------------------
# _estimate_cost (internal function, tested because it's the cost engine)
# ---------------------------------------------------------------------------


class TestEstimateCost:
    """Test cost estimation for various models."""

    def test_gpt5_mini_cost(self) -> None:
        """gpt-5-mini: $0.25/$2.00 per million tokens."""
        # 1000 input, 500 output
        cost = _estimate_cost(1000, 500, "gpt-5-mini")
        expected = (1000 / 1_000_000) * 0.25 + (500 / 1_000_000) * 2.00
        assert cost == pytest.approx(expected)

    def test_gpt5_chat_latest_cost(self) -> None:
        """gpt-5-chat-latest: $1.25/$10.00 per million tokens."""
        cost = _estimate_cost(10000, 5000, "gpt-5-chat-latest")
        expected = (10000 / 1_000_000) * 1.25 + (5000 / 1_000_000) * 10.00
        assert cost == pytest.approx(expected)

    def test_claude_sonnet_cost(self) -> None:
        """claude-sonnet-4-6: $3.00/$15.00 per million tokens."""
        cost = _estimate_cost(2000, 1000, "claude-sonnet-4-6")
        expected = (2000 / 1_000_000) * 3.00 + (1000 / 1_000_000) * 15.00
        assert cost == pytest.approx(expected)

    def test_ollama_zero_cost(self) -> None:
        """Ollama models have zero cost."""
        cost = _estimate_cost(100000, 50000, "ollama")
        assert cost == 0.0

    def test_unknown_model_uses_fallback_pricing(self) -> None:
        """Unknown model names use the conservative fallback pricing."""
        cost = _estimate_cost(1000, 1000, "totally-unknown-model-v99")
        # Fallback: $2.50 input, $10.00 output per million
        expected = (1000 / 1_000_000) * 2.50 + (1000 / 1_000_000) * 10.00
        assert cost == pytest.approx(expected)

    def test_zero_tokens_zero_cost(self) -> None:
        """Zero tokens should produce zero cost."""
        assert _estimate_cost(0, 0, "gpt-5-mini") == 0.0

    def test_deepseek_chat_cost(self) -> None:
        """deepseek-chat: $0.14/$0.28 per million tokens."""
        cost = _estimate_cost(5000, 2000, "deepseek-chat")
        expected = (5000 / 1_000_000) * 0.14 + (2000 / 1_000_000) * 0.28
        assert cost == pytest.approx(expected)


# ---------------------------------------------------------------------------
# MODEL_PRICING completeness
# ---------------------------------------------------------------------------


class TestModelPricing:
    """Test that MODEL_PRICING contains expected entries."""

    def test_has_openai_models(self) -> None:
        """MODEL_PRICING includes OpenAI models."""
        assert "gpt-5-mini" in MODEL_PRICING
        assert "gpt-5-chat-latest" in MODEL_PRICING
        assert "gpt-5" in MODEL_PRICING
        assert "gpt-4o" in MODEL_PRICING
        assert "gpt-4o-mini" in MODEL_PRICING

    def test_has_anthropic_models(self) -> None:
        """MODEL_PRICING includes Anthropic models."""
        assert "claude-sonnet-4-6" in MODEL_PRICING
        assert "claude-haiku-4-5" in MODEL_PRICING

    def test_has_gemini_models(self) -> None:
        """MODEL_PRICING includes Gemini models."""
        assert "gemini-2.5-flash" in MODEL_PRICING
        assert "gemini-2.5-pro" in MODEL_PRICING

    def test_has_deepseek_models(self) -> None:
        """MODEL_PRICING includes DeepSeek models."""
        assert "deepseek-chat" in MODEL_PRICING
        assert "deepseek-reasoner" in MODEL_PRICING

    def test_has_mistral_models(self) -> None:
        """MODEL_PRICING includes Mistral models."""
        assert "mistral-large-latest" in MODEL_PRICING
        assert "mistral-small-latest" in MODEL_PRICING

    def test_has_ollama_entry(self) -> None:
        """MODEL_PRICING includes ollama at zero cost."""
        assert "ollama" in MODEL_PRICING
        assert MODEL_PRICING["ollama"] == (0.0, 0.0)

    def test_all_prices_are_non_negative(self) -> None:
        """All pricing entries should be non-negative tuples."""
        for model, (input_price, output_price) in MODEL_PRICING.items():
            assert input_price >= 0, f"{model} has negative input price"
            assert output_price >= 0, f"{model} has negative output price"

    def test_all_prices_are_finite(self) -> None:
        """All pricing entries should be finite values."""
        for model, (input_price, output_price) in MODEL_PRICING.items():
            assert math.isfinite(input_price), f"{model} has non-finite input price"
            assert math.isfinite(output_price), f"{model} has non-finite output price"


# ---------------------------------------------------------------------------
# record_usage — validation (mocked DataFlow)
# ---------------------------------------------------------------------------


class TestRecordUsageValidation:
    """Test record_usage() input validation without hitting DataFlow."""

    def test_nan_input_tokens_rejected(self) -> None:
        """NaN input_tokens should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid input_tokens"):
            record_usage(
                company_id=1,
                input_tokens=int(float("nan")) if False else -1,
                output_tokens=100,
                model="gpt-5-mini",
            )
        # Direct NaN test via float cast path
        with pytest.raises((ValueError, OverflowError)):
            record_usage(
                company_id=1,
                input_tokens=float("nan"),  # type: ignore[arg-type]
                output_tokens=100,
                model="gpt-5-mini",
            )

    def test_inf_input_tokens_rejected(self) -> None:
        """Inf input_tokens should raise ValueError."""
        with pytest.raises((ValueError, OverflowError)):
            record_usage(
                company_id=1,
                input_tokens=float("inf"),  # type: ignore[arg-type]
                output_tokens=100,
                model="gpt-5-mini",
            )

    def test_negative_input_tokens_rejected(self) -> None:
        """Negative input_tokens should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid input_tokens"):
            record_usage(
                company_id=1,
                input_tokens=-100,
                output_tokens=100,
                model="gpt-5-mini",
            )

    def test_negative_output_tokens_rejected(self) -> None:
        """Negative output_tokens should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid output_tokens"):
            record_usage(
                company_id=1,
                input_tokens=100,
                output_tokens=-50,
                model="gpt-5-mini",
            )

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    @patch("hr_advisory.services.llm_budget._execute_node")
    def test_record_usage_calculates_cost(self, mock_exec, mock_get_usage) -> None:
        """record_usage() correctly calculates and accumulates cost."""
        mock_get_usage.return_value = _mock_usage(
            estimated_cost=0.50,
            query_count=5,
            input_tokens=10000,
            output_tokens=5000,
            usage_id=42,
        )
        mock_exec.return_value = {}

        result = record_usage(
            company_id=1,
            input_tokens=2000,
            output_tokens=1000,
            model="gpt-5-mini",
        )

        # Cost for gpt-5-mini: (2000/1M)*0.25 + (1000/1M)*2.00
        expected_query_cost = (2000 / 1_000_000) * 0.25 + (1000 / 1_000_000) * 2.00
        assert result["last_query_cost"] == pytest.approx(expected_query_cost, abs=1e-6)
        assert result["query_count"] == 6
        assert result["input_tokens"] == 12000
        assert result["output_tokens"] == 6000
        assert result["estimated_cost"] == pytest.approx(0.50 + expected_query_cost, abs=1e-6)

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    @patch("hr_advisory.services.llm_budget._execute_node")
    def test_record_usage_gpt5_chat_latest(self, mock_exec, mock_get_usage) -> None:
        """record_usage() cost for gpt-5-chat-latest at $1.25/$10.00."""
        mock_get_usage.return_value = _mock_usage(usage_id=10)
        mock_exec.return_value = {}

        result = record_usage(
            company_id=1,
            input_tokens=5000,
            output_tokens=2000,
            model="gpt-5-chat-latest",
        )

        expected_cost = (5000 / 1_000_000) * 1.25 + (2000 / 1_000_000) * 10.00
        assert result["last_query_cost"] == pytest.approx(expected_cost, abs=1e-6)

    @patch("hr_advisory.services.llm_budget._get_or_create_usage")
    def test_record_usage_no_id_raises(self, mock_get_usage) -> None:
        """record_usage() raises RuntimeError if usage record has no ID."""
        mock_get_usage.return_value = {
            "company_id": 1,
            "month": "2026-03-01",
            "query_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            # "id" is missing
        }

        with pytest.raises(RuntimeError, match="No usage record"):
            record_usage(
                company_id=1,
                input_tokens=100,
                output_tokens=50,
                model="gpt-5-mini",
            )
