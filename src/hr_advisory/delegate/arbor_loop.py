# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Arbor Delegate — wires kaizen-agents Delegate with Arbor tools.

Uses the Delegate facade (kaizen-agents 0.4.0) which provides:
- True incremental token streaming via typed events (TextDelta, ToolCallStart, etc.)
- ToolHydrator for progressive tool disclosure (search_tools meta-tool)
- Budget tracking and enforcement
- Provider-agnostic (OpenAI, Ollama, vLLM, TGI, any OpenAI-compatible endpoint)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from kaizen_agents.delegate import Delegate, DelegateEvent, TextDelta, ErrorEvent
from kaizen_agents.delegate.loop import ToolRegistry

from hr_advisory.delegate.system_prompt import build_system_prompt
from hr_advisory.delegate.tools import register_arbor_tools

logger = logging.getLogger(__name__)

__all__ = [
    "DelegateConfig",
    "create_delegate",
    "run_delegate_sync",
    "stream_delegate",
]


@dataclass
class DelegateConfig:
    """Configuration for the Arbor Delegate."""

    model: str = ""
    api_key: str = ""
    base_url: str | None = None
    max_turns: int = 30
    budget_usd: float | None = None
    company_id: int | None = None
    jwt_token: str | None = None
    company_context: dict[str, Any] | None = None
    user_context: dict[str, Any] | None = None


def _resolve_llm_settings(config: DelegateConfig) -> tuple[str, str, str | None]:
    """Resolve model, api_key, base_url from config + env vars.

    Priority: config > LLM_* (generic) > OPENAI_* (provider-specific) > defaults.
    """
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
        or "not-needed"
    )

    base_url = (
        config.base_url or os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    )

    return model, api_key, base_url


def create_delegate(config: DelegateConfig | None = None) -> Delegate:
    """Create an Arbor Delegate agent.

    Returns a Delegate instance ready for streaming via delegate.run(prompt).
    """
    if config is None:
        config = DelegateConfig()

    model, api_key, base_url = _resolve_llm_settings(config)

    logger.info(
        "Delegate LLM: model=%s, base_url=%s",
        model,
        base_url or "(default: OpenAI)",
    )

    # Set provider env BEFORE creating the Delegate (adapter reads these)
    if base_url:
        os.environ.setdefault("OPENAI_BASE_URL", base_url)
    if api_key and api_key != "not-needed":
        os.environ.setdefault("OPENAI_API_KEY", api_key)

    # Build tool registry with all Arbor tools
    registry = ToolRegistry()
    register_arbor_tools(
        registry,
        jwt_token=config.jwt_token,
        company_id=config.company_id,
    )

    # Build system prompt
    system_prompt = build_system_prompt(
        company_context=config.company_context,
        user_context=config.user_context,
    )

    # Create the Delegate
    delegate = Delegate(
        model=model,
        tools=registry,
        system_prompt=system_prompt,
        max_turns=config.max_turns,
        budget_usd=config.budget_usd,
    )

    # Configure the hydrator's always-active tools so the LLM sees them
    # without needing to call search_tools first.
    _ALWAYS_ACTIVE = frozenset(
        {
            "search_tools",
            "search_kb",
            "calculate_cpf",
            "calculate_leave",
            "calculate_salary",
            "calculate_quota_levy",
            "get_company_context",
        }
    )
    if hasattr(delegate.loop, "_hydrator") and delegate.loop._hydrator is not None:
        delegate.loop._hydrator.base_tool_names = _ALWAYS_ACTIVE

    return delegate


def run_delegate_sync(
    prompt: str,
    config: DelegateConfig | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run the Delegate synchronously and return a result dict.

    Collects the full streamed response into a dict matching the format
    expected by /advisory/query:
        {response_text, risk_tier, confidence, domains, citations,
         tools_called, usage, degraded}

    Conversation history is prepended to the prompt as context.
    """
    import asyncio
    import re

    delegate = create_delegate(config)

    # Build the full prompt with conversation context
    full_prompt = prompt
    if conversation_history:
        context_parts = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                context_parts.append(f"[{role}]: {content}")
        if context_parts:
            full_prompt = (
                "Previous conversation:\n" + "\n".join(context_parts) + f"\n\n[user]: {prompt}"
            )

    # Collect full response
    text_parts: list[str] = []
    tools_called: list[str] = []
    usage_data: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}

    async def _run() -> None:
        async for event in delegate.run(full_prompt):
            if isinstance(event, TextDelta):
                text_parts.append(event.text)
            elif hasattr(event, "tool_name"):
                tools_called.append(event.tool_name)
            elif hasattr(event, "usage"):
                u = event.usage
                if hasattr(u, "prompt_tokens"):
                    usage_data["input_tokens"] += u.prompt_tokens
                if hasattr(u, "completion_tokens"):
                    usage_data["output_tokens"] += u.completion_tokens

    try:
        asyncio.run(_run())
    except RuntimeError:
        # Already in an async context — use a new event loop in a thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(lambda: asyncio.run(_run())).result(timeout=60)

    response_text = "".join(text_parts)

    # Extract confidence/risk markers if present
    confidence = 0.7
    risk_tier = "amber"
    pattern = r"\[CONFIDENCE:\s*([\d.]+)\]\s*\[RISK:\s*(green|amber|red)\]"
    match = re.search(pattern, response_text)
    if match:
        try:
            confidence = max(0.0, min(1.0, float(match.group(1))))
        except ValueError:
            confidence = 0.7
        risk_tier = match.group(2)
        response_text = response_text[: match.start()].rstrip()

    # Extract domains from tools called
    domains = ["general"]
    if any(t == "search_kb" for t in tools_called):
        domains = ["employment_law"]
    if any(t == "calculate_cpf" for t in tools_called):
        domains = ["cpf"] if domains == ["general"] else domains + ["cpf"]

    return {
        "response_text": response_text,
        "risk_tier": risk_tier,
        "confidence": confidence,
        "domains": domains,
        "citations": [],
        "tools_called": tools_called,
        "usage": usage_data,
        "degraded": not bool(response_text),
    }


async def stream_delegate(
    prompt: str,
    config: DelegateConfig | None = None,
) -> AsyncGenerator[DelegateEvent, None]:
    """Create a delegate and stream events for a single prompt.

    Convenience wrapper for one-shot usage:
        async for event in stream_delegate("What is CPF?"):
            if isinstance(event, TextDelta):
                yield event
    """
    delegate = create_delegate(config)
    async for event in delegate.run(prompt):
        yield event
