# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Normalize LLM provider errors into safe, user-facing categories.

NEVER pass raw provider error text to the frontend — it may leak key validity
information or internal implementation details.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

__all__ = ["normalize_llm_error", "LLMErrorResult"]


@dataclass
class LLMErrorResult:
    category: str  # key_invalid, quota_exceeded, rate_limited, service_unavailable, timeout, endpoint_unreachable, model_unavailable, unknown
    message: str  # User-facing plain-language message
    retryable: bool = False

    def to_dict(self) -> dict:
        return {
            "error": self.category,
            "message": self.message,
            "retryable": self.retryable,
        }


def normalize_llm_error(error: Exception, provider: str) -> LLMErrorResult:
    """Map a provider exception to a safe, normalized error result.

    Args:
        error: The raw exception from the provider SDK or HTTP call.
        provider: "openai", "anthropic", "ollama", etc.

    Returns:
        LLMErrorResult with category, user-facing message, and retryability.
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # OpenAI / OpenAI-compatible errors
    if provider in ("openai", "deepseek", "mistral", "custom"):
        return _normalize_openai_error(error, error_str, error_type)

    # Anthropic errors
    if provider == "anthropic":
        return _normalize_anthropic_error(error, error_str, error_type)

    # Ollama / local endpoint errors
    if provider == "ollama":
        return _normalize_ollama_error(error, error_str, error_type)

    # Gemini errors
    if provider == "gemini":
        return _normalize_gemini_error(error, error_str, error_type)

    return LLMErrorResult(
        category="unknown",
        message="The AI service encountered an unexpected error. Please try again.",
        retryable=True,
    )


def _normalize_openai_error(error: Exception, error_str: str, error_type: str) -> LLMErrorResult:
    # Authentication errors (401)
    if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
        return LLMErrorResult(
            category="key_invalid",
            message="Your API key is no longer valid. Please update it in Settings.",
        )

    # Quota / billing errors (402, 429 with quota message)
    if "insufficient_quota" in error_str or "402" in error_str or "billing" in error_str:
        return LLMErrorResult(
            category="quota_exceeded",
            message="Your OpenAI account needs more credits. Check your billing at platform.openai.com.",
        )

    # Rate limiting (429)
    if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
        return LLMErrorResult(
            category="rate_limited",
            message="The AI service is busy right now. Please try again in a moment.",
            retryable=True,
        )

    # Server errors (500, 503)
    if "500" in error_str or "503" in error_str or "server error" in error_str:
        return LLMErrorResult(
            category="service_unavailable",
            message="The AI service is temporarily down. Please try again shortly.",
            retryable=True,
        )

    # Timeout
    if "timeout" in error_str or "timed out" in error_str or "timeout" in error_type.lower():
        return LLMErrorResult(
            category="timeout",
            message="The request took too long. Please try a shorter question.",
            retryable=True,
        )

    # Connection error
    if "connection" in error_str or error_type in ("ConnectionError", "ConnectError"):
        return LLMErrorResult(
            category="service_unavailable",
            message="Cannot reach the AI service. Please check your internet connection.",
            retryable=True,
        )

    return LLMErrorResult(
        category="unknown",
        message="The AI service encountered an error. Please try again.",
        retryable=True,
    )


def _normalize_anthropic_error(error: Exception, error_str: str, error_type: str) -> LLMErrorResult:
    if "401" in error_str or "authentication" in error_str:
        return LLMErrorResult(
            category="key_invalid",
            message="Your Anthropic API key is no longer valid. Please update it in Settings.",
        )
    if "429" in error_str or "rate" in error_str:
        return LLMErrorResult(
            category="rate_limited",
            message="The AI service is busy. Please try again in a moment.",
            retryable=True,
        )
    if "overloaded" in error_str or "529" in error_str:
        return LLMErrorResult(
            category="service_unavailable",
            message="The AI service is experiencing high demand. Please try again shortly.",
            retryable=True,
        )
    return LLMErrorResult(
        category="unknown",
        message="The AI service encountered an error. Please try again.",
        retryable=True,
    )


def _normalize_ollama_error(error: Exception, error_str: str, error_type: str) -> LLMErrorResult:
    if "connection refused" in error_str or "urlopen" in error_str:
        return LLMErrorResult(
            category="endpoint_unreachable",
            message="Cannot reach the local AI service. Please check that it's running.",
        )
    if "model" in error_str and ("not found" in error_str or "unknown" in error_str):
        return LLMErrorResult(
            category="model_unavailable",
            message="The selected AI model is not available on the service. Please check the model name in Settings.",
        )
    if "timeout" in error_str or "timed out" in error_str or "timeout" in error_type.lower():
        return LLMErrorResult(
            category="timeout",
            message="The local AI service took too long to respond. Try a shorter question.",
            retryable=True,
        )
    return LLMErrorResult(
        category="unknown",
        message="The local AI service encountered an error. Please check that it's running correctly.",
        retryable=True,
    )


def _normalize_gemini_error(error: Exception, error_str: str, error_type: str) -> LLMErrorResult:
    if "403" in error_str or "api key" in error_str:
        return LLMErrorResult(
            category="key_invalid",
            message="Your Google API key is not valid for Gemini. Please update it in Settings.",
        )
    if "429" in error_str or "quota" in error_str:
        return LLMErrorResult(
            category="rate_limited",
            message="The AI service rate limit has been reached. Please try again shortly.",
            retryable=True,
        )
    return LLMErrorResult(
        category="unknown",
        message="The AI service encountered an error. Please try again.",
        retryable=True,
    )
