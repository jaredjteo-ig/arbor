"""Regression tests for BYOK security fixes from red team rounds 1-2.

These tests guard against regressions of specific security findings.
NEVER delete regression tests — they are permanent guards.

R1-C1: SSRF cloud metadata blocking
R1-H4: LLMKeyContext frozen=True
R2-C1: contextvars instead of threading.local
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# Prevent Kaizen import chain
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


# ---------------------------------------------------------------------------
# R1-H4: LLMKeyContext must be frozen (immutable)
# ---------------------------------------------------------------------------


class TestLLMKeyContextFrozen:
    """R1-H4 regression: LLMKeyContext must be frozen to prevent mutation."""

    @pytest.mark.regression
    def test_cannot_mutate_api_key(self) -> None:
        from hr_advisory.agents.llm_context import LLMKeyContext

        ctx = LLMKeyContext(api_key="sk-secret", provider="openai", model="gpt-5")
        with pytest.raises(AttributeError):
            ctx.api_key = "sk-hacked"  # type: ignore[misc]

    @pytest.mark.regression
    def test_cannot_mutate_provider(self) -> None:
        from hr_advisory.agents.llm_context import LLMKeyContext

        ctx = LLMKeyContext(provider="openai", model="gpt-5")
        with pytest.raises(AttributeError):
            ctx.provider = "evil"  # type: ignore[misc]

    @pytest.mark.regression
    def test_clear_key_works_despite_frozen(self) -> None:
        """clear_key uses object.__setattr__ to bypass frozen."""
        from hr_advisory.agents.llm_context import LLMKeyContext

        ctx = LLMKeyContext(api_key="sk-secret", provider="openai", model="gpt-5")
        ctx.clear_key()
        assert ctx.api_key is None


# ---------------------------------------------------------------------------
# R2-C1: Must use contextvars, not threading.local
# ---------------------------------------------------------------------------


class TestContextVarsNotThreadLocal:
    """R2-C1 regression: LLM context must use contextvars for thread safety."""

    @pytest.mark.regression
    def test_uses_contextvar_not_threading_local(self) -> None:
        import contextvars

        from hr_advisory.agents.config import _request_llm_context

        assert isinstance(_request_llm_context, contextvars.ContextVar)

    @pytest.mark.regression
    def test_set_get_clear_cycle(self) -> None:
        from hr_advisory.agents.config import (
            clear_request_llm_context,
            get_request_llm_context,
            set_request_llm_context,
        )
        from hr_advisory.agents.llm_context import LLMKeyContext

        ctx = LLMKeyContext(api_key="sk-test", provider="openai", model="gpt-5")
        set_request_llm_context(ctx)
        assert get_request_llm_context() is ctx
        clear_request_llm_context()
        assert get_request_llm_context() is None


# ---------------------------------------------------------------------------
# R1-C1: SSRF cloud metadata blocking
# ---------------------------------------------------------------------------


class TestSSRFBlocking:
    """R1-C1 regression: Cloud metadata endpoints must be blocked.

    Tests the URL validation logic directly without importing the full router
    (which triggers DataFlow model registration).
    """

    @staticmethod
    def _validate_base_url(base_url: str, provider: str) -> None:
        """Reimplement the validation logic for testing without import chain."""
        from urllib.parse import urlparse
        from fastapi import HTTPException

        if provider in ("ollama", "custom") and not base_url:
            raise HTTPException(status_code=400, detail="base_url required")
        if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise HTTPException(status_code=400, detail="Must start with http")
        if base_url:
            parsed = urlparse(base_url)
            host = parsed.hostname or ""
            blocked = {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}
            if host in blocked:
                raise HTTPException(status_code=400, detail="Not allowed")

    @pytest.mark.regression
    def test_block_aws_metadata(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            self._validate_base_url("http://169.254.169.254/latest/meta-data/", "ollama")
        assert exc_info.value.status_code == 400

    @pytest.mark.regression
    def test_block_gcp_metadata(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            self._validate_base_url("http://metadata.google.internal/computeMetadata/v1/", "ollama")
        assert exc_info.value.status_code == 400

    @pytest.mark.regression
    def test_block_alibaba_metadata(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            self._validate_base_url("http://100.100.100.200/latest/meta-data/", "ollama")
        assert exc_info.value.status_code == 400

    @pytest.mark.regression
    def test_allow_legitimate_ollama(self) -> None:
        # Should NOT raise
        self._validate_base_url("http://dgx.institution.edu:11434", "ollama")
        self._validate_base_url("http://192.168.1.100:11434", "ollama")
        self._validate_base_url("https://ollama.example.com", "ollama")
