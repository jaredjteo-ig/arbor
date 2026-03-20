# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Ollama / DGX endpoint health checking and model discovery."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

__all__ = ["check_ollama_health", "OllamaHealthResult"]


@dataclass
class OllamaHealthResult:
    reachable: bool
    models: list[str]
    model_available: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "reachable": self.reachable,
            "models": self.models,
            "model_available": self.model_available,
            "error": self.error,
        }


def check_ollama_health(
    base_url: str,
    model: str | None = None,
    timeout: int = 5,
) -> OllamaHealthResult:
    """Check if an Ollama endpoint is reachable and optionally verify a model.

    Args:
        base_url: Ollama API base URL (e.g. "http://dgx.institution.edu:11434").
        model: If provided, verify this specific model is available.
        timeout: Connection timeout in seconds.

    Returns:
        OllamaHealthResult with reachability, available models, and model match.
    """
    url = base_url.rstrip("/")
    try:
        req = urllib.request.Request(f"{url}/api/tags")
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]

        model_available = False
        if model:
            # Match exact name or name without tag
            model_available = model in models or any(
                m.split(":")[0] == model.split(":")[0] for m in models
            )

        return OllamaHealthResult(
            reachable=True,
            models=models,
            model_available=model_available if model else True,
        )
    except urllib.error.URLError as e:
        return OllamaHealthResult(
            reachable=False,
            models=[],
            error=f"Cannot reach endpoint: {e.reason}",
        )
    except TimeoutError:
        return OllamaHealthResult(
            reachable=False,
            models=[],
            error=f"Connection timed out after {timeout}s",
        )
    except Exception as e:
        return OllamaHealthResult(
            reachable=False,
            models=[],
            error=str(e),
        )
