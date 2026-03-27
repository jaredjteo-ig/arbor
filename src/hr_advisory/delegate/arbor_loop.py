# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Arbor Delegate loop — wires kaizen-agents AgentLoop with Arbor tools.

Creates an autonomous agent that uses gpt-5-chat-latest with the full
Arbor HRIS tool surface, streaming tokens via SSE.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from kaizen_agents.delegate.config.loader import KzConfig
from kaizen_agents.delegate.loop import AgentLoop, ToolRegistry

from hr_advisory.delegate.system_prompt import build_system_prompt
from hr_advisory.delegate.tools import ToolHydrator, register_arbor_tools

logger = logging.getLogger(__name__)


@dataclass
class DelegateConfig:
    """Configuration for the Arbor Delegate."""

    model: str = ""
    api_key: str = ""
    base_url: str | None = None
    max_turns: int = 30
    max_tokens: int = 16384
    budget_usd: float | None = None
    company_id: int | None = None
    jwt_token: str | None = None
    company_context: dict[str, Any] | None = None
    user_context: dict[str, Any] | None = None


def create_delegate(
    config: DelegateConfig | None = None,
) -> tuple[AgentLoop, ToolHydrator]:
    """Create an Arbor Delegate agent loop.

    Returns (AgentLoop, ToolHydrator) — the loop for execution and
    the hydrator for tool search/hydration.
    """
    if config is None:
        config = DelegateConfig()

    # ── Resolve LLM provider settings ────────────────────────
    # Generic env vars (LLM_*) take precedence over provider-specific (OPENAI_*).
    # This supports any OpenAI-compatible endpoint: OpenAI, Ollama, vLLM, TGI, SGLang.
    model = (
        config.model
        or os.environ.get("LLM_MODEL")
        or os.environ.get("DEFAULT_LLM_MODEL")
        or os.environ.get("OPENAI_PROD_MODEL")
        or "gpt-5-chat-latest"
    )

    api_key = (
        config.api_key
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or "not-needed"  # Local inference (Ollama, vLLM) doesn't require a key
    )

    base_url = (
        config.base_url
        or os.environ.get("LLM_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        # No default — None means use OpenAI's default endpoint
    )

    logger.info(
        "Delegate LLM config: model=%s, base_url=%s, key=%s",
        model,
        base_url or "(default: OpenAI)",
        f"{api_key[:8]}..." if len(api_key) > 12 else "(local)",
    )

    # Build tool registry
    registry = ToolRegistry()
    hydrator = register_arbor_tools(
        registry,
        jwt_token=config.jwt_token,
        company_id=config.company_id,
    )

    # Build KzConfig for the AgentLoop
    kz_config = KzConfig(
        model=model,
        max_turns=config.max_turns,
        max_tokens=config.max_tokens,
    )

    # Build OpenAI-compatible client (works with any provider)
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)

    # Build system prompt
    system_prompt = build_system_prompt(
        company_context=config.company_context,
        user_context=config.user_context,
    )

    # Create the AgentLoop
    loop = AgentLoop(
        config=kz_config,
        tools=registry,
        client=client,
        system_prompt=system_prompt,
    )

    return loop, hydrator


async def run_delegate(
    message: str,
    config: DelegateConfig | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run the delegate and collect the full response (non-streaming).

    For streaming, use create_delegate() and loop.run_turn() directly.
    """
    loop, hydrator = create_delegate(config)

    # Inject conversation history if provided
    if conversation_history:
        for msg in conversation_history:
            if msg.get("role") == "user":
                loop._conversation.add_user(msg["content"])
            elif msg.get("role") == "assistant":
                loop._conversation.add_assistant(msg["content"])

    # Run the turn and collect response
    chunks: list[str] = []
    async for chunk in loop.run_turn(message):
        chunks.append(chunk)

    response_text = "".join(chunks)

    return {
        "response_text": response_text,
        "risk_tier": "green",  # TODO: extract from response
        "confidence": 0.9,
        "domains": [],
        "citations": [],
        "tools_called": [],
        "usage": {
            "input_tokens": loop._usage.prompt_tokens,
            "output_tokens": loop._usage.completion_tokens,
        },
        "degraded": False,
    }
