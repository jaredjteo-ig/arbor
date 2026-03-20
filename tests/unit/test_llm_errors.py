"""Unit tests for LLM error normalization — provider-agnostic error mapping.

Tests that raw provider exceptions are mapped to safe, user-facing error
categories without leaking internal details, raw error text, or key validity.

T427 — BYOK API Keys: Error normalization unit tests.
"""

from __future__ import annotations

from hr_advisory.services.llm_errors import LLMErrorResult, normalize_llm_error


# ---------------------------------------------------------------------------
# LLMErrorResult
# ---------------------------------------------------------------------------


class TestLLMErrorResult:
    """Test LLMErrorResult dataclass and serialization."""

    def test_to_dict(self) -> None:
        """to_dict() includes error, message, and retryable."""
        result = LLMErrorResult(
            category="key_invalid",
            message="Your API key is invalid.",
            retryable=False,
        )
        d = result.to_dict()
        assert d["error"] == "key_invalid"
        assert d["message"] == "Your API key is invalid."
        assert d["retryable"] is False

    def test_retryable_default_false(self) -> None:
        """Default retryable is False."""
        result = LLMErrorResult(category="test", message="test")
        assert result.retryable is False


# ---------------------------------------------------------------------------
# OpenAI errors
# ---------------------------------------------------------------------------


class TestOpenAIErrors:
    """Test error normalization for OpenAI / OpenAI-compatible providers."""

    def test_401_maps_to_key_invalid(self) -> None:
        """HTTP 401 should map to key_invalid."""
        error = Exception("Error code: 401 - Unauthorized")
        result = normalize_llm_error(error, "openai")
        assert result.category == "key_invalid"
        assert result.retryable is False
        assert "Settings" in result.message

    def test_invalid_api_key_maps_to_key_invalid(self) -> None:
        """'invalid api key' text should map to key_invalid."""
        error = Exception("Invalid API key provided")
        result = normalize_llm_error(error, "openai")
        assert result.category == "key_invalid"

    def test_429_maps_to_rate_limited(self) -> None:
        """HTTP 429 should map to rate_limited."""
        error = Exception("Error code: 429 - Rate limit exceeded")
        result = normalize_llm_error(error, "openai")
        assert result.category == "rate_limited"
        assert result.retryable is True

    def test_rate_limit_text_maps_to_rate_limited(self) -> None:
        """'rate limit' in error text should map to rate_limited."""
        error = Exception("You have hit the rate limit for this model")
        result = normalize_llm_error(error, "openai")
        assert result.category == "rate_limited"
        assert result.retryable is True

    def test_too_many_requests_maps_to_rate_limited(self) -> None:
        """'too many requests' should map to rate_limited."""
        error = Exception("Too many requests")
        result = normalize_llm_error(error, "openai")
        assert result.category == "rate_limited"

    def test_402_maps_to_quota_exceeded(self) -> None:
        """HTTP 402 should map to quota_exceeded."""
        error = Exception("Error code: 402 - Payment required")
        result = normalize_llm_error(error, "openai")
        assert result.category == "quota_exceeded"
        assert result.retryable is False

    def test_insufficient_quota_maps_to_quota_exceeded(self) -> None:
        """'insufficient_quota' text should map to quota_exceeded."""
        error = Exception("insufficient_quota: You exceeded your current quota")
        result = normalize_llm_error(error, "openai")
        assert result.category == "quota_exceeded"

    def test_billing_text_maps_to_quota_exceeded(self) -> None:
        """'billing' text in error should map to quota_exceeded."""
        error = Exception("Billing hard limit has been reached")
        result = normalize_llm_error(error, "openai")
        assert result.category == "quota_exceeded"

    def test_500_maps_to_service_unavailable(self) -> None:
        """Server error 500 should map to service_unavailable."""
        error = Exception("Error code: 500 - Internal server error")
        result = normalize_llm_error(error, "openai")
        assert result.category == "service_unavailable"
        assert result.retryable is True

    def test_503_maps_to_service_unavailable(self) -> None:
        """Server error 503 should map to service_unavailable."""
        error = Exception("Error code: 503 - Service Unavailable")
        result = normalize_llm_error(error, "openai")
        assert result.category == "service_unavailable"

    def test_timeout_maps_to_timeout(self) -> None:
        """Timeout error should map to timeout."""
        error = Exception("Request timeout after 30s")
        result = normalize_llm_error(error, "openai")
        assert result.category == "timeout"
        assert result.retryable is True

    def test_timeout_class_maps_to_timeout(self) -> None:
        """Exception with class name 'Timeout' should map to timeout."""

        class Timeout(Exception):
            pass

        error = Timeout("Read operation exceeded deadline")
        result = normalize_llm_error(error, "openai")
        assert result.category == "timeout"
        assert result.retryable is True

    def test_connection_error_maps_to_service_unavailable(self) -> None:
        """Connection error should map to service_unavailable."""
        error = ConnectionError("Connection refused")
        result = normalize_llm_error(error, "openai")
        assert result.category == "service_unavailable"
        assert result.retryable is True

    def test_unknown_openai_error(self) -> None:
        """Unknown OpenAI error should map to 'unknown' with retryable=True."""
        error = Exception("Something completely unexpected")
        result = normalize_llm_error(error, "openai")
        assert result.category == "unknown"
        assert result.retryable is True

    def test_deepseek_uses_openai_path(self) -> None:
        """DeepSeek provider uses the OpenAI error normalization path."""
        error = Exception("Error code: 401 - Unauthorized")
        result = normalize_llm_error(error, "deepseek")
        assert result.category == "key_invalid"

    def test_mistral_uses_openai_path(self) -> None:
        """Mistral provider uses the OpenAI error normalization path."""
        error = Exception("Error code: 429 - Rate limit")
        result = normalize_llm_error(error, "mistral")
        assert result.category == "rate_limited"

    def test_custom_uses_openai_path(self) -> None:
        """Custom provider uses the OpenAI error normalization path."""
        error = Exception("Error code: 402 - insufficient_quota")
        result = normalize_llm_error(error, "custom")
        assert result.category == "quota_exceeded"


# ---------------------------------------------------------------------------
# Anthropic errors
# ---------------------------------------------------------------------------


class TestAnthropicErrors:
    """Test error normalization for Anthropic provider."""

    def test_401_maps_to_key_invalid(self) -> None:
        """Anthropic 401 should map to key_invalid."""
        error = Exception("Error code: 401 - Authentication error")
        result = normalize_llm_error(error, "anthropic")
        assert result.category == "key_invalid"
        assert result.retryable is False

    def test_429_maps_to_rate_limited(self) -> None:
        """Anthropic 429 should map to rate_limited."""
        error = Exception("Error code: 429 - Rate limit exceeded")
        result = normalize_llm_error(error, "anthropic")
        assert result.category == "rate_limited"
        assert result.retryable is True

    def test_overloaded_maps_to_service_unavailable(self) -> None:
        """Anthropic 'overloaded' should map to service_unavailable."""
        error = Exception("Overloaded — too many requests")
        result = normalize_llm_error(error, "anthropic")
        assert result.category == "service_unavailable"
        assert result.retryable is True

    def test_529_maps_to_service_unavailable(self) -> None:
        """Anthropic 529 should map to service_unavailable."""
        error = Exception("Error code: 529 - API overloaded")
        result = normalize_llm_error(error, "anthropic")
        assert result.category == "service_unavailable"

    def test_unknown_anthropic_error(self) -> None:
        """Unknown Anthropic error should map to 'unknown'."""
        error = Exception("Weird anthropic issue")
        result = normalize_llm_error(error, "anthropic")
        assert result.category == "unknown"
        assert result.retryable is True


# ---------------------------------------------------------------------------
# Ollama errors
# ---------------------------------------------------------------------------


class TestOllamaErrors:
    """Test error normalization for Ollama / local endpoint provider."""

    def test_connection_refused_maps_to_endpoint_unreachable(self) -> None:
        """'connection refused' should map to endpoint_unreachable."""
        error = Exception("connection refused at http://localhost:11434")
        result = normalize_llm_error(error, "ollama")
        assert result.category == "endpoint_unreachable"
        assert result.retryable is False
        assert "running" in result.message.lower()

    def test_urlopen_error_maps_to_endpoint_unreachable(self) -> None:
        """URLError (urlopen) should map to endpoint_unreachable."""
        error = Exception("urlopen error: [Errno 111] Connection refused")
        result = normalize_llm_error(error, "ollama")
        assert result.category == "endpoint_unreachable"

    def test_model_not_found_maps_to_model_unavailable(self) -> None:
        """'model not found' should map to model_unavailable."""
        error = Exception("model 'llama3.1:70b' not found")
        result = normalize_llm_error(error, "ollama")
        assert result.category == "model_unavailable"
        assert "model name" in result.message.lower() or "model" in result.message.lower()

    def test_model_unknown_maps_to_model_unavailable(self) -> None:
        """'model unknown' text should map to model_unavailable."""
        error = Exception("model 'nonexistent-model' unknown")
        result = normalize_llm_error(error, "ollama")
        assert result.category == "model_unavailable"

    def test_ollama_timeout_maps_to_timeout(self) -> None:
        """Ollama timeout should map to timeout."""
        error = Exception("Request timeout after 60s")
        result = normalize_llm_error(error, "ollama")
        assert result.category == "timeout"
        assert result.retryable is True

    def test_unknown_ollama_error(self) -> None:
        """Unknown Ollama error defaults to 'unknown'."""
        error = Exception("CUDA out of memory")
        result = normalize_llm_error(error, "ollama")
        assert result.category == "unknown"
        assert result.retryable is True


# ---------------------------------------------------------------------------
# Gemini errors
# ---------------------------------------------------------------------------


class TestGeminiErrors:
    """Test error normalization for Google Gemini provider."""

    def test_403_maps_to_key_invalid(self) -> None:
        """Gemini 403 should map to key_invalid."""
        error = Exception("Error code: 403 - Forbidden")
        result = normalize_llm_error(error, "gemini")
        assert result.category == "key_invalid"
        assert result.retryable is False

    def test_api_key_text_maps_to_key_invalid(self) -> None:
        """'api key' text should map to key_invalid."""
        error = Exception("API key not valid. Please pass a valid API key.")
        result = normalize_llm_error(error, "gemini")
        assert result.category == "key_invalid"

    def test_429_maps_to_rate_limited(self) -> None:
        """Gemini 429 should map to rate_limited."""
        error = Exception("Error code: 429 - Resource exhausted")
        result = normalize_llm_error(error, "gemini")
        assert result.category == "rate_limited"
        assert result.retryable is True

    def test_quota_maps_to_rate_limited(self) -> None:
        """Gemini 'quota' text should map to rate_limited."""
        error = Exception("Quota exceeded for this model")
        result = normalize_llm_error(error, "gemini")
        assert result.category == "rate_limited"

    def test_unknown_gemini_error(self) -> None:
        """Unknown Gemini error defaults to 'unknown'."""
        error = Exception("Some other gemini error")
        result = normalize_llm_error(error, "gemini")
        assert result.category == "unknown"
        assert result.retryable is True


# ---------------------------------------------------------------------------
# Unknown provider
# ---------------------------------------------------------------------------


class TestUnknownProvider:
    """Test error normalization for completely unknown providers."""

    def test_unknown_provider_returns_unknown_category(self) -> None:
        """An unknown provider should always map to 'unknown'."""
        error = Exception("Some error from a brand new provider")
        result = normalize_llm_error(error, "totally_new_provider")
        assert result.category == "unknown"
        assert result.retryable is True

    def test_empty_provider_returns_unknown(self) -> None:
        """Empty provider string should map to 'unknown'."""
        error = Exception("Error")
        result = normalize_llm_error(error, "")
        assert result.category == "unknown"


# ---------------------------------------------------------------------------
# User-friendly message policy
# ---------------------------------------------------------------------------


class TestMessageSafety:
    """Verify that error messages are user-friendly and don't leak internals."""

    def test_no_raw_error_in_openai_messages(self) -> None:
        """OpenAI error messages should be user-facing, not raw exception text."""
        raw_errors = [
            ("Error code: 401 - {'error': {'message': 'Invalid API key'}}", "openai"),
            ("Error code: 429 - rate_limit_exceeded", "openai"),
            ("Error code: 402 - insufficient_quota", "openai"),
        ]
        for error_text, provider in raw_errors:
            result = normalize_llm_error(Exception(error_text), provider)
            # The user-facing message should NOT contain raw JSON, error codes, or
            # internal identifiers
            msg = result.message
            assert "{'error'" not in msg, f"Raw JSON leaked in message: {msg}"
            assert "error code:" not in msg.lower(), f"Raw error code leaked: {msg}"

    def test_no_raw_error_in_ollama_messages(self) -> None:
        """Ollama error messages should be user-facing."""
        error = Exception("connection refused at http://192.168.1.100:11434")
        result = normalize_llm_error(error, "ollama")
        # Should not contain the internal IP address
        assert "192.168.1.100" not in result.message

    def test_messages_are_non_empty(self) -> None:
        """All error categories produce non-empty messages."""
        providers_and_errors = [
            ("openai", Exception("Error code: 401")),
            ("openai", Exception("Error code: 429")),
            ("openai", Exception("Error code: 402")),
            ("anthropic", Exception("Error code: 401")),
            ("ollama", Exception("connection refused")),
            ("ollama", Exception("model not found")),
            ("gemini", Exception("Error code: 403")),
            ("unknown", Exception("Something failed")),
        ]
        for provider, error in providers_and_errors:
            result = normalize_llm_error(error, provider)
            assert len(result.message) > 10, f"Message too short for {provider}: {result.message}"
