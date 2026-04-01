# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Per-request LLM context for BYOK and multi-provider support.

LLMKeyContext bundles the API key, provider, model, and base URL for a
single advisory request.  It is resolved once per request from the company's
stored config (BYOK / Ollama) or the server's .env defaults, then threaded
through the entire advisory pipeline so every Kaizen agent call uses the
correct credentials.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = ["LLMKeyContext", "GEMINI_OPENAI_BASE_URL"]

# Google's OpenAI-compatible endpoint for Gemini models.
# See: https://ai.google.dev/gemini-api/docs/openai
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


@dataclass(frozen=True)
class LLMKeyContext:
    """Immutable per-request LLM configuration.

    Attributes:
        api_key: Decrypted API key (None for Ollama / no-key providers).
        provider: "openai" | "anthropic" | "gemini" | "deepseek" | "mistral"
                  | "ollama" | "custom".
        model: Model name (e.g. "gpt-5-chat-latest", "llama3.1:70b").
        base_url: Custom endpoint URL (required for Ollama, optional for
                  OpenAI-compatible providers like DeepSeek/Mistral).
        is_byok: True when the key came from CompanyLLMConfig / UserLLMConfig,
                 False when using server .env defaults.
        company_id: Company that owns this context (for budget tracking).
        user_id: User who triggered this request (for per-user key resolution).
    """

    api_key: Optional[str] = field(default=None, repr=False)
    provider: str = "gemini"
    model: str = ""
    base_url: Optional[str] = None
    is_byok: bool = False
    company_id: Optional[int] = None
    user_id: Optional[int] = None

    # -- Display helpers (mask the key) ----------------------------------

    def __repr__(self) -> str:
        masked = self._mask_key()
        return (
            f"LLMKeyContext(provider={self.provider!r}, model={self.model!r}, "
            f"api_key={masked!r}, base_url={self.base_url!r}, "
            f"is_byok={self.is_byok}, company_id={self.company_id})"
        )

    def _mask_key(self) -> str:
        if not self.api_key:
            return "<none>"
        if len(self.api_key) <= 8:
            return "****"
        return self.api_key[:3] + "..." + self.api_key[-4:]

    def to_dict(self) -> dict:
        """Serialize for logging / response metadata.  Key is always masked."""
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self._mask_key(),
            "base_url": self.base_url,
            "is_byok": self.is_byok,
            "company_id": self.company_id,
        }

    # -- Factory methods -------------------------------------------------

    @classmethod
    def from_server_env(cls, company_id: Optional[int] = None) -> "LLMKeyContext":
        """Build context from the server's .env defaults."""
        from hr_advisory.config.settings import get_settings

        settings = get_settings()
        # Priority 1: Gemini
        if settings.gemini_api_key:
            return cls(
                api_key=settings.gemini_api_key,
                provider="gemini",
                model=settings.gemini_model or "gemini-2.5-flash",
                is_byok=False,
                company_id=company_id,
            )
        # Priority 2: OpenAI
        if settings.openai_api_key:
            return cls(
                api_key=settings.openai_api_key,
                provider="openai",
                model=settings.openai_prod_model or settings.default_llm_model,
                is_byok=False,
                company_id=company_id,
            )
        # Priority 3: Ollama
        return cls(
            provider="ollama",
            model=settings.ollama_model or "",
            base_url=settings.ollama_base_url,
            is_byok=False,
            company_id=company_id,
        )

    @classmethod
    def for_ollama(
        cls,
        base_url: str,
        model: str,
        company_id: Optional[int] = None,
    ) -> "LLMKeyContext":
        """Build context for a company's custom Ollama / DGX endpoint."""
        return cls(
            provider="ollama",
            model=model,
            base_url=base_url,
            is_byok=True,
            company_id=company_id,
        )

    # -- Cleanup ---------------------------------------------------------

    def clear_key(self) -> None:
        """Best-effort clearing of the decrypted key from memory.

        Python strings are immutable so we cannot overwrite bytes in place,
        but we can drop the reference so the GC can reclaim it sooner.
        """
        object.__setattr__(self, "api_key", None)
