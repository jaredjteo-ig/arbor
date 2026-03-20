# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""LLM observability — structured logging for every LLM call.

Emits structured log events for monitoring, alerting, and debugging.
Uses structlog if available, falls back to stdlib logging.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

__all__ = [
    "log_llm_call",
    "log_budget_warning",
    "log_budget_exceeded",
    "log_key_invalid",
    "log_provider_fallback",
    "llm_call_timer",
]


def log_llm_call(
    company_id: int,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    duration_ms: float,
    is_byok: bool,
) -> None:
    """Log a completed LLM call with full metadata."""
    logger.info(
        "llm.call company_id=%d provider=%s model=%s input_tokens=%d "
        "output_tokens=%d cost_usd=%.6f duration_ms=%.0f is_byok=%s",
        company_id,
        provider,
        model,
        input_tokens,
        output_tokens,
        cost_usd,
        duration_ms,
        is_byok,
    )


def log_budget_warning(company_id: int, used_usd: float, limit_usd: float) -> None:
    """Log when a company approaches their budget limit (80%)."""
    logger.warning(
        "llm.budget.warning company_id=%d used_usd=%.2f limit_usd=%.2f pct=%.0f%%",
        company_id,
        used_usd,
        limit_usd,
        (used_usd / limit_usd * 100) if limit_usd > 0 else 0,
    )


def log_budget_exceeded(company_id: int) -> None:
    """Log when a company's budget is fully consumed."""
    logger.warning("llm.budget.exceeded company_id=%d", company_id)


def log_key_invalid(company_id: int, provider: str) -> None:
    """Log when a BYOK key is detected as invalid (401/403)."""
    logger.warning("llm.key.invalid company_id=%d provider=%s", company_id, provider)


def log_provider_fallback(company_id: int, from_provider: str, to_provider: str) -> None:
    """Log when the pipeline falls back from BYOK to server key."""
    logger.info(
        "llm.fallback company_id=%d from=%s to=%s",
        company_id,
        from_provider,
        to_provider,
    )


@contextmanager
def llm_call_timer():
    """Context manager to measure LLM call duration.

    Usage:
        with llm_call_timer() as timer:
            result = agent.run(...)
        duration_ms = timer.elapsed_ms
    """
    start = time.monotonic()

    class Timer:
        elapsed_ms: float = 0.0

    timer = Timer()
    try:
        yield timer
    finally:
        timer.elapsed_ms = (time.monotonic() - start) * 1000
