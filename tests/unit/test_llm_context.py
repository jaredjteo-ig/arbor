"""Unit tests for LLMKeyContext — per-request LLM configuration.

Tests construction, key masking in __repr__ and to_dict(), factory methods
(from_server_env, for_ollama), and clear_key() memory cleanup.

T424 — BYOK API Keys: LLMKeyContext unit tests.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from unittest.mock import MagicMock
import sys

# Prevent Kaizen import chain (pre-existing SDK version mismatch:
# kailash 2.0.0-enterprise doesn't export Node from kailash.nodes.base)
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

from hr_advisory.agents.llm_context import LLMKeyContext


class TestLLMKeyContextCreation:
    """Test LLMKeyContext dataclass construction with all field combinations."""

    def test_defaults(self) -> None:
        """Default LLMKeyContext has no key, provider=gemini, empty model."""
        ctx = LLMKeyContext()
        assert ctx.api_key is None
        assert ctx.provider == "gemini"
        assert ctx.model == ""
        assert ctx.base_url is None
        assert ctx.is_byok is False
        assert ctx.company_id is None
        assert ctx.user_id is None

    def test_full_construction(self) -> None:
        """All fields can be set explicitly."""
        ctx = LLMKeyContext(
            api_key="sk-test-1234567890abcdef",
            provider="anthropic",
            model="claude-sonnet-4-6",
            base_url="https://custom.endpoint.com",
            is_byok=True,
            company_id=42,
            user_id=7,
        )
        assert ctx.api_key == "sk-test-1234567890abcdef"
        assert ctx.provider == "anthropic"
        assert ctx.model == "claude-sonnet-4-6"
        assert ctx.base_url == "https://custom.endpoint.com"
        assert ctx.is_byok is True
        assert ctx.company_id == 42
        assert ctx.user_id == 7

    def test_ollama_context_no_key(self) -> None:
        """Ollama context should work without an API key."""
        ctx = LLMKeyContext(
            provider="ollama",
            model="llama3.1:70b",
            base_url="http://localhost:11434",
            is_byok=True,
            company_id=1,
        )
        assert ctx.api_key is None
        assert ctx.provider == "ollama"
        assert ctx.model == "llama3.1:70b"


class TestKeyMasking:
    """Test that API keys are never exposed in __repr__ or to_dict."""

    def test_repr_masks_long_key(self) -> None:
        """__repr__ should show first 3 + '...' + last 4 chars for keys > 8 chars."""
        ctx = LLMKeyContext(api_key="sk-test-1234567890abcdef", provider="openai")
        r = repr(ctx)
        # The full key must NOT appear
        assert "sk-test-1234567890abcdef" not in r
        # The masked version should: first 3 chars = "sk-", last 4 = "cdef"
        assert "sk-...cdef" in r

    def test_repr_masks_short_key(self) -> None:
        """__repr__ should show '****' for keys <= 8 chars."""
        ctx = LLMKeyContext(api_key="short", provider="openai")
        r = repr(ctx)
        assert "short" not in r
        assert "****" in r

    def test_repr_shows_none_for_missing_key(self) -> None:
        """__repr__ should show '<none>' when no key is set."""
        ctx = LLMKeyContext()
        r = repr(ctx)
        assert "<none>" in r

    def test_to_dict_masks_long_key(self) -> None:
        """to_dict() should mask the API key, not expose it."""
        ctx = LLMKeyContext(
            api_key="sk-abc123def456ghi789",
            provider="openai",
            model="gpt-5-mini",
            is_byok=True,
            company_id=1,
        )
        d = ctx.to_dict()
        assert d["api_key"] == "sk-...i789"
        assert d["provider"] == "openai"
        assert d["model"] == "gpt-5-mini"
        assert d["is_byok"] is True
        assert d["company_id"] == 1
        # user_id is NOT in to_dict (security: don't leak user ownership)
        assert "user_id" not in d

    def test_to_dict_masks_short_key(self) -> None:
        """to_dict() should use '****' for short keys."""
        ctx = LLMKeyContext(api_key="abc")
        d = ctx.to_dict()
        assert d["api_key"] == "****"

    def test_to_dict_none_key(self) -> None:
        """to_dict() shows '<none>' for missing key."""
        ctx = LLMKeyContext()
        d = ctx.to_dict()
        assert d["api_key"] == "<none>"

    def test_repr_field_is_excluded(self) -> None:
        """api_key should have repr=False in the dataclass field, meaning
        the default repr (if it were generated) would not include it.
        Our custom __repr__ handles masking explicitly."""
        ctx = LLMKeyContext(api_key="sk-secret-key-value-12345678")
        # The raw key value must never appear in any string representation
        assert "sk-secret-key-value-12345678" not in repr(ctx)
        assert "sk-secret-key-value-12345678" not in str(ctx.to_dict())


class TestFromServerEnv:
    """Test LLMKeyContext.from_server_env() factory method."""

    def test_with_openai_key(self, monkeypatch) -> None:
        """When OPENAI_API_KEY is the only provider key, returns openai context."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test-key-for-unit-tests")
        monkeypatch.setenv("OPENAI_PROD_MODEL", "gpt-5-chat-latest")
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            ctx = LLMKeyContext.from_server_env(company_id=10)
            assert ctx.provider == "openai"
            assert ctx.api_key == "sk-env-test-key-for-unit-tests"
            assert ctx.model == "gpt-5-chat-latest"
            assert ctx.is_byok is False
            assert ctx.company_id == 10
        finally:
            get_settings.cache_clear()

    def test_without_openai_key_falls_back_to_ollama(self, monkeypatch) -> None:
        """When no provider keys are set, falls back to Ollama context."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            ctx = LLMKeyContext.from_server_env(company_id=5)
            assert ctx.provider == "ollama"
            assert ctx.api_key is None
            assert ctx.model == "llama3.1:8b"
            assert ctx.base_url == "http://localhost:11434"
            assert ctx.is_byok is False
            assert ctx.company_id == 5
        finally:
            get_settings.cache_clear()


class TestForOllama:
    """Test LLMKeyContext.for_ollama() factory method."""

    def test_basic_ollama_context(self) -> None:
        """for_ollama() returns correctly configured Ollama context."""
        ctx = LLMKeyContext.for_ollama(
            base_url="http://dgx.university.edu:11434",
            model="qwen2.5:32b-instruct-q8_0",
            company_id=99,
        )
        assert ctx.provider == "ollama"
        assert ctx.model == "qwen2.5:32b-instruct-q8_0"
        assert ctx.base_url == "http://dgx.university.edu:11434"
        assert ctx.is_byok is True
        assert ctx.company_id == 99
        assert ctx.api_key is None

    def test_ollama_without_company_id(self) -> None:
        """for_ollama() works without a company_id."""
        ctx = LLMKeyContext.for_ollama(
            base_url="http://localhost:11434",
            model="llama3.1:70b",
        )
        assert ctx.company_id is None
        assert ctx.is_byok is True


class TestClearKey:
    """Test clear_key() drops the API key reference."""

    def test_clear_key_sets_none(self) -> None:
        """clear_key() should set api_key to None."""
        ctx = LLMKeyContext(api_key="sk-secret-to-be-cleared-12345")
        assert ctx.api_key is not None
        ctx.clear_key()
        assert ctx.api_key is None

    def test_clear_key_idempotent(self) -> None:
        """Calling clear_key() twice should not raise."""
        ctx = LLMKeyContext()
        assert ctx.api_key is None
        ctx.clear_key()
        assert ctx.api_key is None

    def test_repr_after_clear(self) -> None:
        """After clear_key(), repr should show '<none>'."""
        ctx = LLMKeyContext(api_key="sk-will-be-cleared-soon-1234")
        ctx.clear_key()
        assert "<none>" in repr(ctx)
