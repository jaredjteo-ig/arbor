# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Tool registration for the Arbor Delegate.

Registers Arbor's platform capabilities as tools in the kaizen-agents
ToolRegistry. Tools are organized in two tiers:

1. Always-active (~15 tools): KB search, calculators, navigation, context
2. Discoverable via search_tools: All 600+ HRIS CRUD endpoints

The search_tools meta-tool enables the LLM to discover capabilities
without overwhelming the context window with 600+ tool definitions.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any

from kaizen_agents.delegate.loop import ToolDef, ToolRegistry

logger = logging.getLogger(__name__)

# Stop words for BM25 search
_STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "for",
        "to",
        "in",
        "of",
        "and",
        "or",
        "with",
        "my",
        "me",
        "i",
        "we",
        "you",
        "it",
        "this",
        "that",
    }
)


def _tokenize(text: str) -> list[str]:
    """Simple word tokenization with stopword removal."""
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 2]


class ToolHydrator:
    """Manages active vs deferred tool schemas for context-efficient LLM calls.

    Always-active tools are sent to the LLM on every call. Deferred tools
    are discoverable via the search_tools meta-tool and hydrated (added to
    the active set) when the LLM requests them.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        always_active: set[str] | None = None,
    ) -> None:
        self._registry = registry
        self._always_active = always_active or set()
        self._hydrated: set[str] = set()
        self._index: dict[str, list[str]] = {}
        self._tool_summaries: dict[str, str] = {}

    def build_index(self) -> None:
        """Build search index over all registered tools."""
        for name in self._registry.tool_names:
            tool = self._registry._tools[name]
            self._tool_summaries[name] = tool.description
            for token in _tokenize(f"{name} {tool.description}"):
                self._index.setdefault(token, []).append(name)

    def get_active_tools(self) -> list[dict[str, Any]]:
        """Return tool schemas for the active set only."""
        active_names = self._always_active | self._hydrated
        tools = []
        for name in active_names:
            if self._registry.has_tool(name):
                tools.append(self._registry._tools[name].to_openai_format())
        # Always include the search meta-tool
        tools.append(_search_tools_schema())
        return tools

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        """Search deferred tools by description. Auto-hydrates results."""
        query_tokens = _tokenize(query)
        scores: Counter = Counter()

        for token in query_tokens:
            for name in self._index.get(token, []):
                scores[name] += 1

        results = []
        for name, _score in scores.most_common(limit):
            self._hydrated.add(name)
            results.append(
                {
                    "name": name,
                    "description": self._tool_summaries.get(name, ""),
                }
            )

        return results

    def reset_hydration(self) -> None:
        """Clear hydrated tools between conversations."""
        self._hydrated.clear()


def _search_tools_schema() -> dict[str, Any]:
    """Schema for the search_tools meta-tool."""
    return {
        "type": "function",
        "function": {
            "name": "search_tools",
            "description": (
                "Search for available platform tools by what you want to do. "
                "Returns tool names and descriptions. After finding the right "
                "tool, call it directly. Examples: 'create employee', "
                "'apply for leave', 'run payroll', 'submit CPF'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you want to do",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    }


def register_arbor_tools(
    registry: ToolRegistry,
    jwt_token: str | None = None,
    company_id: int | None = None,
) -> ToolHydrator:
    """Register all Arbor tools and return a ToolHydrator.

    Args:
        registry: The kaizen-agents ToolRegistry to populate.
        jwt_token: JWT for authenticated REST API calls.
        company_id: Company ID for tenant-scoped operations.

    Returns:
        A ToolHydrator with always-active tools and search index.
    """
    always_active: set[str] = set()

    # ── 1. KB Search ──────────────────────────────────────────
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
    always_active.add("search_kb")

    # ── 2. Calculators ────────────────────────────────────────
    async def _calculate(calculator_type: str, **kwargs: Any) -> str:
        from hr_advisory.agents.actions.calculator import CalculatorAgent

        calc = CalculatorAgent()
        result = calc.calculate(calculator_type, kwargs)
        return json.dumps(result, default=str)

    for calc_name, calc_desc, calc_params in [
        (
            "calculate_cpf",
            "Calculate CPF contributions. Returns employer/employee amounts.",
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
                    "bonus": {"type": "number", "description": "Additional wages (bonus) SGD"},
                },
                "required": ["monthly_wage"],
            },
        ),
        (
            "calculate_leave",
            "Calculate statutory leave entitlements under the Employment Act.",
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
        (
            "calculate_quota_levy",
            "Calculate foreign worker quota and levy costs under EFMA.",
            {
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "enum": ["services", "manufacturing", "construction", "process", "marine"],
                    },
                    "headcount_local": {"type": "integer"},
                    "headcount_ep": {"type": "integer"},
                    "headcount_sp": {"type": "integer"},
                    "headcount_wp": {"type": "integer"},
                },
                "required": ["sector", "headcount_local"],
            },
        ),
    ]:
        calc_type = calc_name.replace("calculate_", "")

        async def _calc_wrapper(_type: str = calc_type, **kw: Any) -> str:
            return await _calculate(_type, **kw)

        registry.register(calc_name, calc_desc, calc_params, _calc_wrapper)
        always_active.add(calc_name)

    # ── 3. Company Context ────────────────────────────────────
    async def _get_company_context(cid: int = 0) -> str:
        _cid = cid or company_id
        if not _cid:
            return json.dumps({"error": "No company_id available"})
        try:
            from kailash import LocalRuntime, WorkflowBuilder

            wf = WorkflowBuilder()
            wf.add_node(
                "CompanyListNode",
                "find",
                {"filter": {"id": int(_cid)}, "limit": 1, "enable_cache": False},
            )
            with LocalRuntime() as runtime:
                results, _ = runtime.execute(wf.build())
            records = results.get("find", {})
            items = records.get("records", []) if isinstance(records, dict) else []
            if items:
                return json.dumps(items[0], default=str)
            return json.dumps({"error": "Company not found"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    registry.register(
        "get_company_context",
        "Get company profile including sector, headcount, and compliance status.",
        {
            "type": "object",
            "properties": {
                "company_id": {"type": "integer", "description": "Company ID"},
            },
        },
        _get_company_context,
    )
    always_active.add("get_company_context")

    # ── 4. HRIS REST API tools (discoverable via search_tools) ─
    try:
        from hr_advisory.delegate.hris_tools import register_hris_tools

        hris_count = register_hris_tools(
            registry,
            jwt_token=jwt_token,
            base_url="http://localhost:8000",
        )
        logger.info("Registered %d HRIS REST API tools", hris_count)
    except Exception as exc:
        logger.warning("Failed to register HRIS tools: %s", exc)

    # ── 5. MCP server tools (discoverable via search_tools) ──
    try:
        from hr_advisory.delegate.mcp_tools import register_mcp_tools

        mcp_count = register_mcp_tools(registry)
        logger.info("Registered %d MCP server tools", mcp_count)
    except Exception as exc:
        logger.warning("Failed to register MCP tools: %s", exc)

    # ── 6. Build hydrator and index ───────────────────────────
    hydrator = ToolHydrator(registry, always_active)
    hydrator.build_index()

    logger.info(
        "Arbor tools registered: %d always-active, %d total, search index built",
        len(always_active),
        len(registry.tool_names),
    )

    return hydrator
