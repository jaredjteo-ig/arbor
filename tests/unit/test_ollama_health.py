"""Unit tests for Ollama health checking and model discovery.

Tests endpoint reachability detection, model listing, model name
matching (exact and tag-stripped), and error handling for timeouts
and malformed responses.

T429 — BYOK API Keys: Ollama health unit tests.
"""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from hr_advisory.services.ollama_health import OllamaHealthResult, check_ollama_health


# ---------------------------------------------------------------------------
# OllamaHealthResult
# ---------------------------------------------------------------------------


class TestOllamaHealthResult:
    """Test OllamaHealthResult dataclass and serialization."""

    def test_to_dict_reachable(self) -> None:
        """to_dict() for a reachable endpoint with models."""
        result = OllamaHealthResult(
            reachable=True,
            models=["llama3.1:70b", "qwen2.5:32b-instruct-q8_0"],
            model_available=True,
        )
        d = result.to_dict()
        assert d["reachable"] is True
        assert d["models"] == ["llama3.1:70b", "qwen2.5:32b-instruct-q8_0"]
        assert d["model_available"] is True
        assert d["error"] == ""

    def test_to_dict_unreachable(self) -> None:
        """to_dict() for an unreachable endpoint."""
        result = OllamaHealthResult(
            reachable=False,
            models=[],
            error="Cannot reach endpoint: Connection refused",
        )
        d = result.to_dict()
        assert d["reachable"] is False
        assert d["models"] == []
        assert d["model_available"] is False
        assert "Connection refused" in d["error"]

    def test_default_values(self) -> None:
        """Default model_available=False and error=''."""
        result = OllamaHealthResult(reachable=True, models=[])
        assert result.model_available is False
        assert result.error == ""


# ---------------------------------------------------------------------------
# check_ollama_health — connection failure cases
# ---------------------------------------------------------------------------


class TestCheckOllamaHealthUnreachable:
    """Test health check for unreachable endpoints."""

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_connection_refused(self, mock_urlopen) -> None:
        """Connection refused returns reachable=False."""
        mock_urlopen.side_effect = urllib.error.URLError(reason="Connection refused")

        result = check_ollama_health("http://localhost:11434")
        assert result.reachable is False
        assert result.models == []
        assert "Connection refused" in result.error

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_timeout(self, mock_urlopen) -> None:
        """Timeout returns reachable=False with timeout message."""
        mock_urlopen.side_effect = TimeoutError()

        result = check_ollama_health("http://localhost:11434", timeout=3)
        assert result.reachable is False
        assert "timed out" in result.error.lower()

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_dns_failure(self, mock_urlopen) -> None:
        """DNS failure returns reachable=False."""
        mock_urlopen.side_effect = urllib.error.URLError(reason="Name or service not known")

        result = check_ollama_health("http://nonexistent.host.invalid:11434")
        assert result.reachable is False
        assert result.models == []

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_generic_exception(self, mock_urlopen) -> None:
        """Any other exception returns reachable=False with error text."""
        mock_urlopen.side_effect = RuntimeError("Unexpected error in socket layer")

        result = check_ollama_health("http://localhost:11434")
        assert result.reachable is False
        assert "Unexpected error" in result.error


# ---------------------------------------------------------------------------
# check_ollama_health — successful connection cases
# ---------------------------------------------------------------------------


def _mock_ollama_response(models: list[dict]) -> MagicMock:
    """Create a mock urllib response with the given model list."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({"models": models}).encode()
    return resp


class TestCheckOllamaHealthReachable:
    """Test health check for reachable endpoints."""

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_reachable_with_models(self, mock_urlopen) -> None:
        """Reachable endpoint with models returns model list."""
        models = [
            {"name": "llama3.1:70b"},
            {"name": "qwen2.5:32b-instruct-q8_0"},
            {"name": "nomic-embed-text:latest"},
        ]
        mock_urlopen.return_value = _mock_ollama_response(models)

        result = check_ollama_health("http://localhost:11434")
        assert result.reachable is True
        assert "llama3.1:70b" in result.models
        assert "qwen2.5:32b-instruct-q8_0" in result.models
        assert "nomic-embed-text:latest" in result.models
        assert result.model_available is True  # No model filter = True
        assert result.error == ""

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_reachable_empty_models(self, mock_urlopen) -> None:
        """Reachable endpoint with no models."""
        mock_urlopen.return_value = _mock_ollama_response([])

        result = check_ollama_health("http://localhost:11434")
        assert result.reachable is True
        assert result.models == []
        assert result.model_available is True  # No model filter = True

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_model_exact_match(self, mock_urlopen) -> None:
        """Exact model name match sets model_available=True."""
        models = [{"name": "llama3.1:70b"}, {"name": "mistral:7b"}]
        mock_urlopen.return_value = _mock_ollama_response(models)

        result = check_ollama_health(
            "http://localhost:11434",
            model="llama3.1:70b",
        )
        assert result.reachable is True
        assert result.model_available is True

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_model_tag_stripped_match(self, mock_urlopen) -> None:
        """Model matches when tag portion is stripped (e.g. 'llama3.1' matches 'llama3.1:70b')."""
        models = [{"name": "llama3.1:70b"}]
        mock_urlopen.return_value = _mock_ollama_response(models)

        result = check_ollama_health(
            "http://localhost:11434",
            model="llama3.1",
        )
        assert result.model_available is True

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_model_not_found(self, mock_urlopen) -> None:
        """When requested model is not in the list, model_available=False."""
        models = [{"name": "llama3.1:70b"}, {"name": "mistral:7b"}]
        mock_urlopen.return_value = _mock_ollama_response(models)

        result = check_ollama_health(
            "http://localhost:11434",
            model="phi3:latest",
        )
        assert result.reachable is True
        assert result.model_available is False

    @patch("hr_advisory.services.ollama_health.urllib.request.urlopen")
    def test_url_trailing_slash_stripped(self, mock_urlopen) -> None:
        """Trailing slashes in base_url are handled correctly."""
        mock_urlopen.return_value = _mock_ollama_response([{"name": "test:1b"}])

        result = check_ollama_health("http://localhost:11434/")
        assert result.reachable is True
        # Verify the URL was constructed correctly
        call_args = mock_urlopen.call_args
        # The Request object is the first positional arg
        request_obj = call_args[0][0]
        assert request_obj.full_url == "http://localhost:11434/api/tags"
