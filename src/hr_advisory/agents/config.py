# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Domain configuration for HR advisory agents.

All API keys and model names come from Settings (environment variables)
or from per-request LLMKeyContext (BYOK / Ollama overrides).

Provider resolution order:
  1. Per-request LLMKeyContext (BYOK key or company Ollama endpoint)
  2. OpenAI server key (from OPENAI_API_KEY env var)
  3. Gemini server key (from GOOGLE_API_KEY env var)
  4. Ollama (if running locally with a model available)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from hr_advisory.config.settings import get_settings
from hr_advisory.agents.llm_context import GEMINI_OPENAI_BASE_URL

if TYPE_CHECKING:
    from hr_advisory.agents.llm_context import LLMKeyContext

logger = logging.getLogger(__name__)

__all__ = [
    "QueryAnalyzerConfig",
    "QueryClarifierConfig",
    "OrchestratorConfig",
    "ResponseSynthesizerConfig",
    "SpecialistConfig",
    "ComplianceConfig",
    "DocumentGenerationConfig",
    "has_llm_available",
    "resolve_provider_and_model",
    "install_kaizen_provider_patch",
    "UNCERTAINTY_DEFAULTS",
]


# ---------------------------------------------------------------------------
# Kaizen provider monkey-patch
# ---------------------------------------------------------------------------
# Kaizen's get_openai_config() reads os.getenv("OPENAI_API_KEY") directly
# with no override parameter.  Until the upstream PR lands, we patch it to
# accept optional api_key/base_url overrides via a context variable.
#
# Uses contextvars.ContextVar (not threading.local) so the context
# propagates correctly to child threads spawned by Kaizen agents and
# is properly scoped per async task in FastAPI.
#
# See: 01-analysis/13-byok-api-keys/07-kaizen-investigation.md

import contextvars

_request_llm_context: contextvars.ContextVar[Optional["LLMKeyContext"]] = contextvars.ContextVar(
    "_request_llm_context", default=None
)


def set_request_llm_context(ctx: Optional["LLMKeyContext"]) -> None:
    """Set the LLM context for the current task/thread."""
    _request_llm_context.set(ctx)


def get_request_llm_context() -> Optional["LLMKeyContext"]:
    """Get the LLM context for the current task/thread, or None."""
    return _request_llm_context.get()


def clear_request_llm_context() -> None:
    """Clear the LLM context for the current task/thread."""
    _request_llm_context.set(None)


_kaizen_patched = False


def install_kaizen_provider_patch() -> None:
    """Monkey-patch Kaizen's provider config functions to respect per-request
    LLMKeyContext overrides.

    This is safe because:
    - We control both repos (Terrene Foundation)
    - The override is additive (falls back to original behavior)
    - It will be removed when the upstream PR is merged
    """
    global _kaizen_patched
    if _kaizen_patched:
        return

    try:
        import kaizen.config.providers as kp

        _original_get_openai = kp.get_openai_config
        _original_get_ollama = kp.get_ollama_config

        def _patched_get_openai_config(model=None):
            # Check if this is a Gemini request routed through OpenAI-compatible endpoint
            gemini_result = _patched_get_openai_config_for_gemini(model)
            if gemini_result is not None:
                return gemini_result
            ctx = get_request_llm_context()
            if ctx and ctx.api_key and ctx.provider == "openai":
                from kaizen.config.providers import ProviderConfig

                return ProviderConfig(
                    provider="openai",
                    model=model
                    or ctx.model
                    or os.getenv("KAIZEN_OPENAI_MODEL", "gpt-5-mini-2025-08-07"),
                    api_key=ctx.api_key,
                    base_url=ctx.base_url,
                    timeout=int(os.getenv("KAIZEN_TIMEOUT", "30")),
                    max_retries=int(os.getenv("KAIZEN_MAX_RETRIES", "3")),
                )
            return _original_get_openai(model)

        def _patched_get_openai_config_for_gemini(model=None):
            """Route Gemini provider through OpenAI-compatible endpoint."""
            ctx = get_request_llm_context()
            if ctx and ctx.provider == "gemini" and ctx.api_key:
                from kaizen.config.providers import ProviderConfig

                return ProviderConfig(
                    provider="openai",  # Kaizen uses OpenAI SDK
                    model=model or ctx.model or "gemini-2.5-flash",
                    api_key=ctx.api_key,
                    base_url=GEMINI_OPENAI_BASE_URL,
                    timeout=int(os.getenv("KAIZEN_TIMEOUT", "30")),
                    max_retries=int(os.getenv("KAIZEN_MAX_RETRIES", "3")),
                )
            return None

        def _patched_get_ollama_config(model=None):
            ctx = get_request_llm_context()
            if ctx and ctx.provider == "ollama" and ctx.base_url:
                from kaizen.config.providers import ProviderConfig

                return ProviderConfig(
                    provider="ollama",
                    model=model or ctx.model or "llama3.1:70b",
                    base_url=ctx.base_url,
                    timeout=int(os.getenv("KAIZEN_TIMEOUT", "60")),
                    max_retries=int(os.getenv("KAIZEN_MAX_RETRIES", "3")),
                )
            return _original_get_ollama(model)

        kp.get_openai_config = _patched_get_openai_config
        kp.get_ollama_config = _patched_get_ollama_config
        _kaizen_patched = True
        logger.info("Kaizen provider functions patched for BYOK support")
    except ImportError:
        logger.warning("kaizen not installed — provider patch skipped")


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------


def _detect_ollama(base_url: Optional[str] = None) -> Optional[str]:
    """Check if ollama is running and return the best available model, or None."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url

    # If OLLAMA_MODEL is explicitly configured, use it
    if not base_url and settings.ollama_model:
        return settings.ollama_model

    # Auto-detect from running ollama instance
    try:
        import json
        import urllib.request

        req = urllib.request.Request(f"{url}/api/tags")
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]

        # Prefer instruction-tuned models for agent work
        preferred = [m for m in models if "instruct" in m or "qwen" in m]
        if preferred:
            return preferred[0]
        text_models = [m for m in models if "embed" not in m and "bakllava" not in m]
        if text_models:
            return text_models[0]
        if models:
            return models[0]
    except Exception:
        pass
    return None


def resolve_provider_and_model(
    ctx: Optional["LLMKeyContext"] = None,
) -> tuple[str, str]:
    """Resolve the LLM provider and model name.

    If *ctx* is provided (per-request BYOK / Ollama context), its values
    take precedence.  Otherwise falls back to server .env settings.

    Returns (provider, model) tuple.
    """
    # Per-request override
    if ctx is not None and ctx.api_key and ctx.provider:
        return ctx.provider, ctx.model
    if ctx is not None and ctx.provider == "ollama" and ctx.base_url:
        model = ctx.model or _detect_ollama(ctx.base_url) or ""
        return "ollama", model

    # Server defaults
    settings = get_settings()

    # Priority 1: OpenAI from env
    if settings.openai_api_key:
        model = settings.openai_prod_model or settings.default_llm_model
        return "openai", model

    # Priority 2: Gemini from env
    if settings.gemini_api_key:
        model = settings.gemini_model or "gemini-2.5-flash"
        return "gemini", model

    # Priority 3: Ollama auto-detect
    ollama_model = _detect_ollama()
    if ollama_model:
        return "ollama", ollama_model

    # Fallback: openai with default model (will fail at call time without key)
    model = settings.openai_prod_model or settings.default_llm_model
    logger.warning("No LLM provider available — defaulting to openai (will fail without API key)")
    return "openai", model


def has_llm_available(
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> bool:
    """Return True if any LLM provider is usable.

    Checks (in order):
    1. User's BYOK key (if user_id given)
    2. Company's BYOK key or Ollama endpoint (if company_id given)
    3. Server OPENAI_API_KEY from .env
    4. Local Ollama auto-detect
    """
    # Check company/user config in DB if IDs provided
    if company_id is not None or user_id is not None:
        try:
            from hr_advisory.services.llm_config import get_active_llm_config

            config = get_active_llm_config(company_id=company_id, user_id=user_id)
            if config is not None:
                return True
        except Exception:
            pass  # DB might not be ready yet — fall through to env check

    # Server env check
    settings = get_settings()
    if settings.gemini_api_key:
        return True
    if settings.openai_api_key:
        return True
    return _detect_ollama() is not None


# ---------------------------------------------------------------------------
# Agent config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class QueryAnalyzerConfig:
    """Config for the query classification agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 1024

    def __post_init__(self):
        if not self.model or not self.llm_provider:
            p, m = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = p
            if not self.model:
                self.model = m


@dataclass
class QueryClarifierConfig:
    """Config for the query clarification agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.0
    max_tokens: int = 256

    def __post_init__(self):
        if not self.model or not self.llm_provider:
            p, m = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = p
            if not self.model:
                self.model = m


@dataclass
class OrchestratorConfig:
    """Config for the dispatch planner agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 512

    def __post_init__(self):
        if not self.model or not self.llm_provider:
            p, m = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = p
            if not self.model:
                self.model = m


@dataclass
class ResponseSynthesizerConfig:
    """Config for the response synthesis agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096

    def __post_init__(self):
        if not self.model or not self.llm_provider:
            p, m = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = p
            if not self.model:
                self.model = m


@dataclass
class SpecialistConfig:
    """Config shared by all domain specialist agents."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 2048

    def __post_init__(self):
        if not self.model or not self.llm_provider:
            p, m = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = p
            if not self.model:
                self.model = m


@dataclass
class ComplianceConfig:
    """Config for the cross-domain compliance agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 2048

    def __post_init__(self):
        if not self.model or not self.llm_provider:
            p, m = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = p
            if not self.model:
                self.model = m


@dataclass
class DocumentGenerationConfig:
    """Config for the document generation agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 4096

    def __post_init__(self):
        if not self.model or not self.llm_provider:
            p, m = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = p
            if not self.model:
                self.model = m


# ---------------------------------------------------------------------------
# Uncertainty defaults — used when any agent encounters an error
# ---------------------------------------------------------------------------

UNCERTAINTY_DEFAULTS = {
    "risk_tier": "amber",
    "confidence": 0.3,
    "degraded": True,
    "fallback_message": (
        "Our AI advisory service is temporarily unable to generate a detailed analysis. "
        "The relevant legal provisions have been identified and are shown below for your reference. "
        "You can browse these provisions directly in the Knowledge Base, or connect with "
        "an employment law specialist for personalised guidance."
    ),
    "critical_fallback_message": (
        "Our AI advisory service is temporarily unavailable for this query. "
        "The relevant provisions from Singapore employment law are listed below. "
        "For matters with legal or financial implications, we recommend connecting "
        "with an employment law specialist who can review your specific situation."
    ),
}
