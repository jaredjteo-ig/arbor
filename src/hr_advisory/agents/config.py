"""Domain configuration for HR advisory agents.

All API keys and model names come from Settings (environment variables).
These dataclasses are auto-converted to BaseAgentConfig by Kaizen.

Provider resolution order:
  1. OpenAI (if OPENAI_API_KEY is set)
  2. Ollama (if ollama is running locally with a model available)
"""

import logging
from dataclasses import dataclass

from hr_advisory.config.settings import get_settings

logger = logging.getLogger(__name__)

# Cache the resolved provider/model so detection runs once per process
_resolved_provider: str | None = None
_resolved_model: str | None = None


def _detect_ollama() -> str | None:
    """Check if ollama is running and return the best available model, or None."""
    settings = get_settings()

    # If OLLAMA_MODEL is explicitly configured, use it
    if settings.ollama_model:
        return settings.ollama_model

    # Auto-detect from running ollama instance
    try:
        import urllib.request
        import json

        url = f"{settings.ollama_base_url}/api/tags"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]

        # Prefer instruction-tuned models for agent work
        preferred = [m for m in models if "instruct" in m or "qwen" in m]
        if preferred:
            return preferred[0]
        # Fall back to any non-embedding model
        text_models = [m for m in models if "embed" not in m and "bakllava" not in m]
        if text_models:
            return text_models[0]
        if models:
            return models[0]
    except Exception:
        pass
    return None


def _resolve_provider_and_model() -> tuple[str, str]:
    """Resolve the LLM provider and model name.

    Returns (provider, model) tuple.
    """
    global _resolved_provider, _resolved_model
    if _resolved_provider is not None:
        return _resolved_provider, _resolved_model  # type: ignore[return-value]

    settings = get_settings()

    # Priority 1: OpenAI
    if settings.openai_api_key:
        _resolved_provider = "openai"
        _resolved_model = settings.openai_prod_model or settings.default_llm_model
        logger.info("LLM provider: openai (model=%s)", _resolved_model)
        return _resolved_provider, _resolved_model

    # Priority 2: Ollama
    ollama_model = _detect_ollama()
    if ollama_model:
        _resolved_provider = "ollama"
        _resolved_model = ollama_model
        logger.info("LLM provider: ollama (model=%s)", _resolved_model)
        return _resolved_provider, _resolved_model

    # Fallback: openai with default model (will fail at call time without key)
    _resolved_provider = "openai"
    _resolved_model = settings.openai_prod_model or settings.default_llm_model
    logger.warning("No LLM provider available — defaulting to openai (will fail without API key)")
    return _resolved_provider, _resolved_model


def _resolve_model() -> str:
    """Return the configured LLM model from environment."""
    _, model = _resolve_provider_and_model()
    return model


def _resolve_provider() -> str:
    """Return the resolved LLM provider."""
    provider, _ = _resolve_provider_and_model()
    return provider


def _resolve_api_key() -> str:
    """Return the OpenAI API key from environment."""
    return get_settings().openai_api_key


def has_llm_available() -> bool:
    """Return True if any LLM provider (OpenAI or ollama) is usable."""
    settings = get_settings()
    if settings.openai_api_key:
        return True
    return _detect_ollama() is not None


@dataclass
class QueryAnalyzerConfig:
    """Config for the query classification agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1  # deterministic classification
    max_tokens: int = 1024

    def __post_init__(self):
        if not self.model:
            self.model = _resolve_model()
        if not self.llm_provider:
            self.llm_provider = _resolve_provider()


@dataclass
class QueryClarifierConfig:
    """Config for the query clarification agent.

    Uses minimal tokens and zero temperature for fast, deterministic
    ambiguity detection.  This agent runs on every query so it must be
    cheap and fast.
    """

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.0  # fully deterministic
    max_tokens: int = 256  # tiny output: bool + short question

    def __post_init__(self):
        if not self.model:
            self.model = _resolve_model()
        if not self.llm_provider:
            self.llm_provider = _resolve_provider()


@dataclass
class OrchestratorConfig:
    """Config for the dispatch planner agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 512

    def __post_init__(self):
        if not self.model:
            self.model = _resolve_model()
        if not self.llm_provider:
            self.llm_provider = _resolve_provider()


@dataclass
class ResponseSynthesizerConfig:
    """Config for the response synthesis agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.3  # slight creativity for plain-language
    max_tokens: int = 2048

    def __post_init__(self):
        if not self.model:
            self.model = _resolve_model()
        if not self.llm_provider:
            self.llm_provider = _resolve_provider()


# ---------------------------------------------------------------------------
# Specialist agents
# ---------------------------------------------------------------------------


@dataclass
class SpecialistConfig:
    """Config shared by all domain specialist agents.

    Low temperature for factual regulatory advice.
    """

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1  # factual, citation-heavy output
    max_tokens: int = 2048

    def __post_init__(self):
        if not self.model:
            self.model = _resolve_model()
        if not self.llm_provider:
            self.llm_provider = _resolve_provider()


@dataclass
class ComplianceConfig:
    """Config for the cross-domain compliance agent.

    Slightly higher token limit because it ingests multiple specialist
    outputs and must reason across domains.
    """

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 2048

    def __post_init__(self):
        if not self.model:
            self.model = _resolve_model()
        if not self.llm_provider:
            self.llm_provider = _resolve_provider()


# ---------------------------------------------------------------------------
# Action agents
# ---------------------------------------------------------------------------


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


@dataclass
class DocumentGenerationConfig:
    """Config for the document generation agent."""

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.2  # mostly template-driven, little creativity
    max_tokens: int = 4096  # documents can be long

    def __post_init__(self):
        if not self.model:
            self.model = _resolve_model()
        if not self.llm_provider:
            self.llm_provider = _resolve_provider()
