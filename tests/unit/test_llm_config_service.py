"""Unit tests for LLM config service and agents/config.py — provider resolution.

Tests resolve_provider_and_model() with and without LLMKeyContext,
has_llm_available() detection, and the Kaizen provider patch installation.

T428 — BYOK API Keys: Config service unit tests.
"""

from __future__ import annotations

import os
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

from hr_advisory.agents.config import (
    clear_request_llm_context,
    get_request_llm_context,
    has_llm_available,
    install_kaizen_provider_patch,
    resolve_provider_and_model,
    set_request_llm_context,
)
from hr_advisory.agents.llm_context import LLMKeyContext
from hr_advisory.services.llm_config import VALID_PROVIDERS


# ---------------------------------------------------------------------------
# resolve_provider_and_model
# ---------------------------------------------------------------------------


class TestResolveProviderAndModel:
    """Test provider/model resolution with and without LLMKeyContext."""

    def test_with_byok_openai_context(self) -> None:
        """LLMKeyContext with api_key and provider returns context values."""
        ctx = LLMKeyContext(
            api_key="sk-byok-test-key-1234567890",
            provider="openai",
            model="gpt-5-chat-latest",
            is_byok=True,
        )
        provider, model = resolve_provider_and_model(ctx)
        assert provider == "openai"
        assert model == "gpt-5-chat-latest"

    def test_with_byok_anthropic_context(self) -> None:
        """Anthropic BYOK context returns anthropic provider."""
        ctx = LLMKeyContext(
            api_key="sk-ant-test-key-value-9999",
            provider="anthropic",
            model="claude-sonnet-4-6",
            is_byok=True,
        )
        provider, model = resolve_provider_and_model(ctx)
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-6"

    def test_with_ollama_context(self) -> None:
        """Ollama context (no key, has base_url) returns ollama provider."""
        ctx = LLMKeyContext(
            provider="ollama",
            model="llama3.1:70b",
            base_url="http://dgx.uni.edu:11434",
            is_byok=True,
        )
        provider, model = resolve_provider_and_model(ctx)
        assert provider == "ollama"
        assert model == "llama3.1:70b"

    @patch("hr_advisory.agents.config._detect_ollama", return_value=None)
    def test_without_context_uses_env_openai(self, mock_detect, monkeypatch) -> None:
        """Without context, falls back to OPENAI_API_KEY from env."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key-for-resolve-test")
        monkeypatch.setenv("OPENAI_PROD_MODEL", "gpt-4o")
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            provider, model = resolve_provider_and_model()
            assert provider == "openai"
            assert model == "gpt-4o"
        finally:
            get_settings.cache_clear()

    @patch("hr_advisory.agents.config._detect_ollama", return_value="qwen2.5:32b")
    def test_without_context_no_openai_falls_to_ollama(self, mock_detect, monkeypatch) -> None:
        """Without context and no provider keys, tries Ollama auto-detect."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            provider, model = resolve_provider_and_model()
            assert provider == "ollama"
            assert model == "qwen2.5:32b"
        finally:
            get_settings.cache_clear()

    @patch("hr_advisory.agents.config._detect_ollama", return_value=None)
    def test_without_context_no_providers_defaults_to_openai(
        self, mock_detect, monkeypatch
    ) -> None:
        """No provider keys, no Ollama: returns openai as fallback (will fail at call time)."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            provider, model = resolve_provider_and_model()
            assert provider == "openai"
            # model should be the default from settings
            assert model != ""
        finally:
            get_settings.cache_clear()

    def test_context_with_key_but_no_provider_falls_through(self) -> None:
        """Context where api_key is set but provider is empty falls through
        to the ctx.provider == 'ollama' check and then to env."""
        ctx = LLMKeyContext(
            api_key="sk-test",
            provider="",
            model="some-model",
        )
        # provider="" is falsy, so `ctx.api_key and ctx.provider` is falsy
        # This should fall through to the env-based path
        with patch("hr_advisory.agents.config._detect_ollama", return_value=None):
            from hr_advisory.config.settings import get_settings

            get_settings.cache_clear()
            try:
                provider, model = resolve_provider_and_model(ctx)
                # Should have fallen through to server defaults
                assert isinstance(provider, str)
                assert isinstance(model, str)
            finally:
                get_settings.cache_clear()


# ---------------------------------------------------------------------------
# has_llm_available
# ---------------------------------------------------------------------------


class TestHasLLMAvailable:
    """Test has_llm_available() availability detection."""

    @patch("hr_advisory.agents.config._detect_ollama", return_value=None)
    def test_returns_true_when_env_key_set(self, mock_detect, monkeypatch) -> None:
        """Returns True when OPENAI_API_KEY is set in environment."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key-for-availability")
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            assert has_llm_available() is True
        finally:
            get_settings.cache_clear()

    @patch("hr_advisory.agents.config._detect_ollama", return_value=None)
    def test_returns_false_when_no_providers(self, mock_detect, monkeypatch) -> None:
        """Returns False when no keys and no Ollama."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            assert has_llm_available() is False
        finally:
            get_settings.cache_clear()

    @patch("hr_advisory.agents.config._detect_ollama", return_value="llama3.1:8b")
    def test_returns_true_when_ollama_available(self, mock_detect, monkeypatch) -> None:
        """Returns True when Ollama auto-detect finds a model."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        try:
            assert has_llm_available() is True
        finally:
            get_settings.cache_clear()

    @patch("hr_advisory.services.llm_config.get_active_llm_config")
    @patch("hr_advisory.agents.config._detect_ollama", return_value=None)
    def test_returns_true_when_company_byok_exists(
        self, mock_detect, mock_config, monkeypatch
    ) -> None:
        """Returns True when company has active BYOK config in DB."""
        from hr_advisory.config.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()

        mock_config.return_value = {
            "id": 1,
            "provider": "openai",
            "encrypted_key": "encrypted-value",
            "status": "active",
        }

        try:
            assert has_llm_available(company_id=42) is True
        finally:
            get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Thread-local request context
# ---------------------------------------------------------------------------


class TestRequestLLMContext:
    """Test thread-local request LLM context management."""

    def test_set_and_get_context(self) -> None:
        """Setting a context makes it retrievable in the same thread."""
        ctx = LLMKeyContext(
            api_key="sk-thread-test-key-1234",
            provider="openai",
            model="gpt-5-mini",
        )
        set_request_llm_context(ctx)
        try:
            retrieved = get_request_llm_context()
            assert retrieved is ctx
            assert retrieved.api_key == "sk-thread-test-key-1234"
        finally:
            clear_request_llm_context()

    def test_clear_context(self) -> None:
        """Clearing context sets it to None."""
        ctx = LLMKeyContext(api_key="sk-temp-key")
        set_request_llm_context(ctx)
        clear_request_llm_context()
        assert get_request_llm_context() is None

    def test_default_context_is_none(self) -> None:
        """Without setting, context should be None."""
        clear_request_llm_context()
        assert get_request_llm_context() is None


# ---------------------------------------------------------------------------
# VALID_PROVIDERS
# ---------------------------------------------------------------------------


class TestValidProviders:
    """Test the VALID_PROVIDERS frozenset."""

    def test_expected_providers(self) -> None:
        """All documented providers are in VALID_PROVIDERS."""
        expected = {"openai", "anthropic", "gemini", "deepseek", "mistral", "ollama", "custom"}
        assert VALID_PROVIDERS == expected

    def test_is_frozenset(self) -> None:
        """VALID_PROVIDERS is immutable."""
        assert isinstance(VALID_PROVIDERS, frozenset)


# ---------------------------------------------------------------------------
# install_kaizen_provider_patch (import safety)
# ---------------------------------------------------------------------------


class TestKaizenProviderPatch:
    """Test that install_kaizen_provider_patch handles missing kaizen gracefully."""

    @patch.dict(
        "sys.modules", {"kaizen": None, "kaizen.config": None, "kaizen.config.providers": None}
    )
    def test_patch_skips_when_kaizen_not_installed(self) -> None:
        """When kaizen is not installed, patch should log warning and not crash."""
        import hr_advisory.agents.config as config_module

        # Reset the patched flag so we can test the import path
        original = config_module._kaizen_patched
        config_module._kaizen_patched = False
        try:
            # This should not raise even though kaizen is not importable
            install_kaizen_provider_patch()
        except Exception:
            pytest.fail("install_kaizen_provider_patch raised with kaizen uninstalled")
        finally:
            config_module._kaizen_patched = original
