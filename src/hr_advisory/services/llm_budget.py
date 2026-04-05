# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""LLM budget enforcement service — per-company monthly usage tracking.

Tracks token usage and estimated cost against a configurable monthly
budget.  Every advisory query checks the budget before proceeding and
records usage after completion.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = [
    "BudgetCheckResult",
    "MODEL_PRICING",
    "DEFAULT_MONTHLY_BUDGET_USD",
    "check_budget",
    "record_usage",
    "get_usage_summary",
]


# ---------------------------------------------------------------------------
# Pricing table: (input_per_million_tokens, output_per_million_tokens) in USD
# ---------------------------------------------------------------------------

MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-5-mini-2025-08-07": (0.25, 2.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-chat-latest": (1.25, 10.00),
    "gpt-5": (1.25, 10.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    # Anthropic
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-haiku-4-5": (0.80, 4.00),
    # Google
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    # DeepSeek
    "deepseek-chat": (0.14, 0.28),
    "deepseek-reasoner": (0.55, 2.19),
    # Mistral
    "mistral-large-latest": (2.00, 6.00),
    "mistral-small-latest": (0.10, 0.30),
    # Ollama / local models — zero cost
    "ollama": (0.0, 0.0),
}

# Fallback pricing for unknown models — conservative estimate
_FALLBACK_PRICING: tuple[float, float] = (2.50, 10.00)

DEFAULT_MONTHLY_BUDGET_USD: float = 5.00
BUDGET_WARNING_THRESHOLD: float = 0.80  # 80%


# ---------------------------------------------------------------------------
# Budget check result
# ---------------------------------------------------------------------------


@dataclass
class BudgetCheckResult:
    """Result of a pre-query budget check."""

    allowed: bool
    remaining_usd: float
    warning: bool  # True if >80% of budget consumed
    used_usd: float
    query_count: int
    limit_usd: float

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "remaining_usd": round(self.remaining_usd, 4),
            "warning": self.warning,
            "used_usd": round(self.used_usd, 4),
            "query_count": self.query_count,
            "limit_usd": round(self.limit_usd, 2),
        }


from hr_advisory.services import dataflow_crud


def _current_month_key() -> str:
    """Return the current month in YYYY-MM-01 format."""
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}-01"


def _get_or_create_usage(company_id: int) -> dict:
    """Get the current month's usage record, creating one if needed."""
    month_key = _current_month_key()

    records = dataflow_crud.list_records(
        "CompanyLLMUsage",
        {"company_id": company_id, "month": month_key},
        limit=1,
    )
    if records:
        return records[0]

    # Create a new usage record for this month
    create_result = dataflow_crud.create(
        "CompanyLLMUsage",
        {
            "company_id": company_id,
            "month": month_key,
            "query_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
        },
    )

    # Fetch back to get the ID
    usage_id = create_result.get("id")
    if usage_id is None:
        records = dataflow_crud.list_records(
            "CompanyLLMUsage",
            {"company_id": company_id, "month": month_key},
            limit=1,
        )
        if records:
            return records[-1]

    return create_result


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> float:
    """Estimate cost in USD for given token counts and model."""
    pricing = MODEL_PRICING.get(model, _FALLBACK_PRICING)
    input_cost = (input_tokens / 1_000_000) * pricing[0]
    output_cost = (output_tokens / 1_000_000) * pricing[1]
    return input_cost + output_cost


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_budget(
    company_id: int,
    budget_limit_usd: Optional[float] = None,
) -> BudgetCheckResult:
    """Check whether the company has remaining budget for this month.

    Args:
        company_id: The company to check.
        budget_limit_usd: Override monthly budget limit. Defaults to
            DEFAULT_MONTHLY_BUDGET_USD.

    Returns:
        BudgetCheckResult with allowed=True if under budget.
    """
    limit = budget_limit_usd if budget_limit_usd is not None else DEFAULT_MONTHLY_BUDGET_USD

    # Validate the limit — reject NaN/Inf
    if not math.isfinite(limit) or limit < 0:
        logger.error("Invalid budget limit for company_id=%s: %s — blocking", company_id, limit)
        return BudgetCheckResult(
            allowed=False,
            remaining_usd=0.0,
            warning=True,
            used_usd=0.0,
            query_count=0,
            limit_usd=0.0,
        )

    usage = _get_or_create_usage(company_id)
    used = float(usage.get("estimated_cost", 0.0))
    query_count = int(usage.get("query_count", 0))

    # Validate used cost — NaN/Inf protection
    if not math.isfinite(used):
        logger.error(
            "Corrupted usage cost for company_id=%s: %s — blocking",
            company_id,
            used,
        )
        return BudgetCheckResult(
            allowed=False,
            remaining_usd=0.0,
            warning=True,
            used_usd=0.0,
            query_count=query_count,
            limit_usd=limit,
        )

    remaining = limit - used
    warning = (used / limit) >= BUDGET_WARNING_THRESHOLD if limit > 0 else True
    allowed = remaining > 0

    return BudgetCheckResult(
        allowed=allowed,
        remaining_usd=max(remaining, 0.0),
        warning=warning,
        used_usd=used,
        query_count=query_count,
        limit_usd=limit,
    )


def record_usage(
    company_id: int,
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> dict:
    """Record token usage after an advisory query completes.

    Note on concurrency: This is a read-modify-write operation. Concurrent
    requests from the same company can race, potentially losing one update's
    increment. With a soft budget cap (check before, record after), the worst
    case is a small overage (~$0.01-0.02 at gpt-5-mini pricing). This is
    acceptable for the $5/month budget. Full atomic SQL-level increment
    would require raw SQL or an upstream DataFlow enhancement.

    Args:
        company_id: The company that consumed the tokens.
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
        model: Model name used (for cost estimation).

    Returns:
        Updated usage record dict.
    """
    # Validate inputs — block NaN/Inf/negative
    if not math.isfinite(float(input_tokens)) or input_tokens < 0:
        logger.error("Invalid input_tokens=%s — rejecting", input_tokens)
        raise ValueError(f"Invalid input_tokens: {input_tokens}")
    if not math.isfinite(float(output_tokens)) or output_tokens < 0:
        logger.error("Invalid output_tokens=%s — rejecting", output_tokens)
        raise ValueError(f"Invalid output_tokens: {output_tokens}")

    cost = _estimate_cost(input_tokens, output_tokens, model)
    if not math.isfinite(cost):
        logger.error(
            "Cost calculation returned non-finite value for model=%s — rejecting",
            model,
        )
        raise ValueError(f"Non-finite cost: {cost}")

    usage = _get_or_create_usage(company_id)
    usage_id = usage.get("id")
    if usage_id is None:
        logger.error("No usage record ID for company_id=%s — cannot update", company_id)
        raise RuntimeError(f"No usage record found for company_id={company_id}")

    new_query_count = int(usage.get("query_count", 0)) + 1
    new_input_tokens = int(usage.get("input_tokens", 0)) + input_tokens
    new_output_tokens = int(usage.get("output_tokens", 0)) + output_tokens
    new_cost = float(usage.get("estimated_cost", 0.0)) + cost

    # Validate accumulated values
    if not math.isfinite(new_cost):
        logger.error(
            "Accumulated cost became non-finite for company_id=%s — rejecting",
            company_id,
        )
        raise ValueError(f"Accumulated cost non-finite: {new_cost}")

    dataflow_crud.update(
        "CompanyLLMUsage",
        usage_id,
        {
            "query_count": new_query_count,
            "input_tokens": new_input_tokens,
            "output_tokens": new_output_tokens,
            "estimated_cost": round(new_cost, 6),
        },
    )

    logger.info(
        "Recorded LLM usage: company_id=%s, model=%s, +%d/%d tokens, +$%.4f (total $%.4f)",
        company_id,
        model,
        input_tokens,
        output_tokens,
        cost,
        new_cost,
    )

    return {
        "company_id": company_id,
        "month": usage.get("month", _current_month_key()),
        "query_count": new_query_count,
        "input_tokens": new_input_tokens,
        "output_tokens": new_output_tokens,
        "estimated_cost": round(new_cost, 6),
        "last_query_cost": round(cost, 6),
    }


def get_usage_summary(company_id: int) -> dict:
    """Get the current month's usage summary for a company.

    Returns a dict with usage stats and budget status.
    """
    usage = _get_or_create_usage(company_id)
    budget = check_budget(company_id)

    return {
        "company_id": company_id,
        "month": usage.get("month", _current_month_key()),
        "query_count": int(usage.get("query_count", 0)),
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "estimated_cost_usd": round(float(usage.get("estimated_cost", 0.0)), 4),
        "budget": budget.to_dict(),
    }
