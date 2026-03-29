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

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from kaizen_agents.delegate import (
    Delegate,
    DelegateEvent,
    TextDelta,
    ToolCallStart,
    ToolCallEnd,
    TurnComplete,
    BudgetExhausted,
    ErrorEvent,
)
from kaizen_agents.delegate.tools import ToolRegistry
from kaizen_agents.delegate.tools.base import Tool, ToolResult

from hr_advisory.delegate.system_prompt import build_system_prompt

logger = logging.getLogger(__name__)

__all__ = [
    "DelegateConfig",
    "FunctionTool",
    "create_delegate",
    "stream_delegate",
]


class FunctionTool(Tool):
    """Generic tool wrapper that adapts an async function to the Tool ABC.

    Usage:
        tool = FunctionTool("search_kb", "Search knowledge base", schema, my_async_func)
        registry.register(tool)
    """

    def __init__(
        self,
        tool_name: str,
        tool_description: str,
        tool_parameters: dict[str, Any],
        executor: Any,
    ) -> None:
        self._name = tool_name
        self._description = tool_description
        self._parameters = tool_parameters
        self._executor = executor

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = await self._executor(**kwargs)
            return ToolResult(output=str(result), error="", is_error=False)
        except Exception as exc:
            return ToolResult(output="", error=str(exc), is_error=True)


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

    # Build tool registry with Arbor tools
    registry = ToolRegistry()
    _register_arbor_tools(registry, config)

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

    # Set provider via env for the underlying adapter
    if base_url:
        os.environ.setdefault("OPENAI_BASE_URL", base_url)
    if api_key and api_key != "not-needed":
        os.environ.setdefault("OPENAI_API_KEY", api_key)

    return delegate


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


def _register_arbor_tools(registry: ToolRegistry, config: DelegateConfig) -> None:
    """Register all Arbor tools in the registry."""

    # ── 1. KB Search (always active) ──
    async def _search_kb(query: str, domain: str = "", limit: int = 5) -> str:
        from hr_advisory.agents.advisory_engine import _search_kb_with_fallback

        results = _search_kb_with_fallback(query, domain or None, limit)
        enriched = []
        for r in results:
            entry = {
                "section": r.get("section", ""),
                "title": r.get("title", ""),
                "plain_summary": r.get("plain_summary", ""),
                "authority_level": r.get("authority_level", ""),
            }
            notes = r.get("interpretation_notes", "")
            if notes:
                entry["interpretation_notes"] = notes
            enriched.append(entry)
        return json.dumps(enriched, default=str)

    registry.register(
        FunctionTool(
            "search_kb",
            "Search Singapore employment law knowledge base for legal provisions. "
            "Returns section numbers, formal text, and plain-language summaries. "
            "Call this BEFORE answering any legal question.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Legal search query"},
                    "domain": {
                        "type": "string",
                        "description": "Optional domain filter",
                        "enum": [
                            "Employment Act",
                            "CPF",
                            "Foreign Manpower",
                            "Fair Employment",
                            "Workplace Safety and Health",
                            "Tax",
                            "Industrial Relations",
                            "Retrenchment",
                        ],
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            _search_kb,
        )
    )

    # ── 2. Calculators (always active) ──
    async def _calculate(calculator_type: str, **kwargs: Any) -> str:
        from hr_advisory.agents.actions.calculator import CalculatorAgent

        calc = CalculatorAgent()
        result = calc.calculate(calculator_type, kwargs)
        return json.dumps(result, default=str)

    for calc_name, calc_desc, calc_params in [
        (
            "calculate_cpf",
            "Calculate CPF contributions for an employee.",
            {
                "type": "object",
                "properties": {
                    "monthly_wage": {"type": "number", "description": "Gross monthly wages SGD"},
                    "age_band": {
                        "type": "string",
                        "enum": [
                            "55_and_below",
                            "above_55_to_60",
                            "above_60_to_65",
                            "above_65_to_70",
                            "above_70",
                        ],
                    },
                },
                "required": ["monthly_wage"],
            },
        ),
        (
            "calculate_leave",
            "Calculate statutory leave entitlements.",
            {
                "type": "object",
                "properties": {
                    "years_of_service": {"type": "number"},
                    "leave_type": {"type": "string", "enum": ["annual", "sick", "all"]},
                },
                "required": ["years_of_service"],
            },
        ),
        (
            "calculate_salary",
            "Calculate salary proration or overtime pay.",
            {
                "type": "object",
                "properties": {
                    "monthly_salary": {"type": "number"},
                    "calculation_type": {"type": "string", "enum": ["proration", "overtime"]},
                    "days_worked": {"type": "integer"},
                    "total_working_days": {"type": "integer"},
                    "overtime_hours": {"type": "number"},
                },
                "required": ["monthly_salary", "calculation_type"],
            },
        ),
    ]:
        _type = calc_name.replace("calculate_", "")

        async def _wrapper(_t=_type, **kw: Any) -> str:
            return await _calculate(_t, **kw)

        registry.register(FunctionTool(calc_name, calc_desc, calc_params, _wrapper))

    # ── 3. HRIS REST API tools (discoverable via search_tools) ──
    try:
        from hr_advisory.delegate.hris_tools import register_hris_tools

        hris_count = register_hris_tools(registry, jwt_token=config.jwt_token)
        logger.info("Registered %d HRIS REST API tools", hris_count)
    except Exception as exc:
        logger.warning("Failed to register HRIS tools: %s", exc)

    # ── 4. MCP server tools (discoverable via search_tools) ──
    try:
        from hr_advisory.delegate.mcp_tools import register_mcp_tools

        mcp_count = register_mcp_tools(registry)
        logger.info("Registered %d MCP server tools", mcp_count)
    except Exception as exc:
        logger.warning("Failed to register MCP tools: %s", exc)
