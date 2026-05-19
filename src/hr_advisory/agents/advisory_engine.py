# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Autonomous advisory engine using LLM function calling.

Replaces the rigid 13-step Kaizen agent pipeline with a single LLM
that decides what tools to call, in what order, and when it has enough
information to answer. The safety chain (input/output guardrails,
trust lineage) wraps this engine — it does not replace the LLM's
reasoning.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from hr_advisory.agents.llm_context import GEMINI_OPENAI_BASE_URL
from hr_advisory.workflows.guardrails import screen_injection, ScreeningResult

logger = logging.getLogger(__name__)

__all__ = ["AdvisoryEngine"]

# Hard cap on tool-calling rounds to prevent runaway loops
MAX_TOOL_ROUNDS = 10


# -- Tool definitions (OpenAI function calling schema) -----------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": (
                "Search the Singapore employment law knowledge base for legal "
                "provisions. Returns matching provisions with section numbers, "
                "formal text, and plain-language summaries. Call this BEFORE "
                "answering any legal question — never rely on memory alone."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query — use specific legal terms like "
                            "'maternity leave entitlement', 'EP salary threshold', "
                            "'CPF contribution rates', 'notice period termination'"
                        ),
                    },
                    "domain": {
                        "type": "string",
                        "description": "Optional domain filter to narrow results",
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
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_cpf",
            "description": (
                "Calculate CPF (Central Provident Fund) contributions for an "
                "employee. Returns employer/employee contribution amounts and "
                "breakdown by ordinary wages and additional wages (bonus)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_wage": {
                        "type": "number",
                        "description": "Gross monthly ordinary wages in SGD",
                    },
                    "age_band": {
                        "type": "string",
                        "description": "Employee age band for CPF rate lookup",
                        "enum": [
                            "55_and_below",
                            "above_55_to_60",
                            "above_60_to_65",
                            "above_65_to_70",
                            "above_70",
                        ],
                    },
                    "bonus": {
                        "type": "number",
                        "description": "Additional wages (bonus) in SGD, if any",
                    },
                },
                "required": ["monthly_wage"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_leave",
            "description": (
                "Calculate statutory leave entitlements under the Employment Act. "
                "Returns annual leave days and/or sick leave (outpatient + "
                "hospitalisation) based on years of service."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "years_of_service": {
                        "type": "number",
                        "description": "Completed years of service with employer",
                    },
                    "leave_type": {
                        "type": "string",
                        "description": "Type of leave to calculate",
                        "enum": ["annual", "sick", "all"],
                    },
                },
                "required": ["years_of_service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_salary",
            "description": (
                "Calculate salary proration for partial months or overtime pay "
                "under the Employment Act. For overtime, uses the statutory "
                "1.5x rate for Part IV employees."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_salary": {
                        "type": "number",
                        "description": "Gross monthly salary in SGD",
                    },
                    "calculation_type": {
                        "type": "string",
                        "description": "Type of salary calculation",
                        "enum": ["proration", "overtime"],
                    },
                    "days_worked": {
                        "type": "integer",
                        "description": "Days worked in partial month (for proration)",
                    },
                    "total_working_days": {
                        "type": "integer",
                        "description": "Total working days in the month (for proration)",
                    },
                    "overtime_hours": {
                        "type": "number",
                        "description": "Overtime hours in the month (for overtime calc)",
                    },
                },
                "required": ["monthly_salary", "calculation_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_quota_levy",
            "description": (
                "Calculate foreign worker quota utilisation and levy costs under "
                "EFMA. Shows current DRC usage, headroom for hiring, and monthly "
                "levy amounts. Can also project the impact of proposed hires."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "description": "Industry sector for DRC limits",
                        "enum": [
                            "services",
                            "manufacturing",
                            "construction",
                            "process",
                            "marine",
                        ],
                    },
                    "headcount_local": {
                        "type": "integer",
                        "description": "Number of local employees (SC + PR)",
                    },
                    "headcount_ep": {
                        "type": "integer",
                        "description": "Number of Employment Pass holders",
                    },
                    "headcount_sp": {
                        "type": "integer",
                        "description": "Number of S Pass holders",
                    },
                    "headcount_wp": {
                        "type": "integer",
                        "description": "Number of Work Permit holders",
                    },
                    "scenario_hire_sp": {
                        "type": "integer",
                        "description": "Proposed additional S Pass hires (for projection)",
                    },
                    "scenario_hire_wp": {
                        "type": "integer",
                        "description": "Proposed additional WP hires (for projection)",
                    },
                },
                "required": ["sector", "headcount_local"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_company_policies",
            "description": (
                "Search the user's company internal policies (leave, FWA, "
                "handbook, safety, benefits, etc.). Returns matching company "
                "policies with title, category, content excerpt, and effective "
                "date. Use this ALONGSIDE search_kb when the user asks about "
                "their company's specific rules — company policies supplement "
                "statutory law, they do not replace it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query — use terms matching company policy "
                            "topics like 'annual leave', 'work from home', "
                            "'safety procedures', 'benefits'"
                        ),
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter to narrow results",
                        "enum": [
                            "leave",
                            "flexible_work",
                            "workplace_safety",
                            "benefits",
                            "code_of_conduct",
                            "compensation",
                            "handbook",
                            "termination",
                            "custom",
                        ],
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_context",
            "description": (
                "Retrieve the company profile including sector, headcount "
                "breakdown, and compliance status. Use this when the user's "
                "question depends on their company's specific situation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_id": {
                        "type": "integer",
                        "description": "The company ID to look up",
                    },
                },
                "required": ["company_id"],
            },
        },
    },
]


# -- System prompt -----------------------------------------------------------


def _build_system_prompt(
    company_context: dict | None = None,
    user_context: dict | None = None,
    onboarding_context: str = "",
) -> str:
    """Build the system prompt for the advisory engine."""
    # Load anti-amnesia constraints
    try:
        from hr_advisory.trust.eatp_lineage import get_anti_amnesia_injection

        anti_amnesia = get_anti_amnesia_injection("orchestrator")
    except Exception:
        anti_amnesia = ""

    # Load security footer
    try:
        from hr_advisory.workflows.guardrails import SYSTEM_PROMPT_SECURITY_FOOTER

        security_footer = SYSTEM_PROMPT_SECURITY_FOOTER
    except Exception:
        security_footer = ""

    base = (
        "You are Arbor — a senior HR advisor for Singapore SMEs. You have deep "
        "expertise in Singapore employment law, HR operations, payroll, and "
        "workforce management.\n\n"
        "You advise real business owners making real decisions. Answer like a "
        "trusted consultant who happens to know the law — not like a legal "
        "database.\n\n"
        "TOOLS:\n"
        "- search_kb: Singapore employment law provisions. Use it to ground "
        "legal claims with specific section numbers. If it returns nothing, "
        "you still know the law — answer anyway.\n"
        "- search_company_policies: The user's company internal policies "
        "(leave, FWA, handbook, safety, benefits). Use alongside search_kb "
        "when the question involves the company's specific rules.\n"
        "- Calculators (CPF, leave, salary, quota/levy): Use when the user "
        "needs exact numbers. These are deterministic.\n"
        "- get_company_context: The user's company profile for personalisation.\n\n"
        "COMPANY POLICY RULES:\n"
        "- ALWAYS state the statutory position first, then the company position.\n"
        "- If a company policy is below the statutory minimum: say so explicitly "
        "— the statutory minimum prevails.\n"
        "- If a company policy exceeds the statutory minimum: note this "
        "positively — the company offers more than required by law.\n"
        "- If no company policy exists on a topic: say so, and fall back to "
        "the statutory position.\n"
        "- NEVER present a company policy as having the force of law — company "
        "policies are internal rules, not legislation.\n\n"
        "BOUNDARIES:\n"
        "- Do not fabricate section numbers. If you cite a provision, it must "
        "be real. If unsure of the exact section, describe the rule without "
        "a section number.\n"
        "- Distinguish legal requirements from practical recommendations. "
        "'You must' = law. 'Most companies' / 'In practice' = guidance.\n"
        "- For high-stakes matters (termination disputes, potential litigation, "
        "union negotiations), recommend professional legal review.\n"
        "- Singlish input is fine. Respond in clear English but don't be "
        "stiff about it.\n\n"
        "NEVER DO THESE:\n"
        "- Never use flattery, filler phrases, or hollow affirmations.\n"
        "- Never start with 'Great question!' or 'That's a really important "
        "topic' or any preamble. Lead with the answer.\n"
        "- Never speculate beyond what you know. When data is limited, say so "
        "honestly.\n"
        "- Never give a thin answer. If the question is complex, the answer "
        "must be comprehensive — cover the law, practical steps, pitfalls, "
        "edge cases, and strategic considerations.\n\n"
        "CONFIDENCE LADDER:\n"
        "Modulate your language based on how well-supported your answer is:\n"
        "- >90% confident (KB provision + calculator): State as fact.\n"
        "- 70-90% (KB provision, no exact match): 'Based on the Employment "
        "Act...' / 'Under current regulations...'\n"
        "- 50-70% (general knowledge, no KB match): 'In practice, most "
        "companies...' / 'Generally speaking...'\n"
        "- <50%: 'You may want to check with a lawyer on this specific point' "
        "— never present low-confidence guidance as definitive.\n\n"
        "Use markdown for structure when it helps readability.\n\n"
        "At the end of your response, on a new line:\n"
        "  [CONFIDENCE: X.XX] [RISK: green|amber|red]\n"
    )

    # Add user context if available (like Iris's dynamic prompt injection)
    context_section = ""
    if user_context:
        role = user_context.get("role", "")
        name = user_context.get("name", "")
        role_hint = ""
        if role == "owner":
            role_hint = "They are the business owner — give strategic, decision-maker advice."
        elif role == "hr_admin":
            role_hint = "They are an HR admin — give operational, process-focused advice."
        elif role == "employee":
            role_hint = "They are an employee — give rights-focused, clear advice."
        if name or role_hint:
            context_section += f"\nUSER: {name} ({role}).{(' ' + role_hint) if role_hint else ''}\n"

    if company_context:
        context_section += (
            "\nCOMPANY CONTEXT (use this to personalise your advice):\n"
            f"{json.dumps(company_context, indent=2, default=str)}\n"
        )

    if onboarding_context:
        context_section += (
            "\nONBOARDING CONTEXT (this employee is currently being onboarded — "
            "use this to answer company-specific onboarding questions like "
            "first-day instructions, buddy info, policies, benefits, checklists, "
            "and 30-60-90 day goals. For legal questions, still use search_kb "
            "for the statutory position):\n"
            f"{onboarding_context}\n"
        )

    return base + context_section + "\n" + anti_amnesia + security_footer


# -- KB search with Python content fallback -----------------------------------


def _search_kb_with_fallback(query: str, domain: str | None = None, limit: int = 5) -> list:
    """Search KB via DataFlow, falling back to Python content modules if DB is empty."""
    # Try the DB first
    try:
        from hr_advisory.kb.admin import search_provisions

        results = search_provisions(query=query, domain=domain, limit=limit)
        if results:
            return results
    except Exception:
        pass

    # Fallback: search the Python content modules directly
    return _search_python_kb(query, domain, limit)


def _search_python_kb(query: str, domain: str | None = None, limit: int = 5) -> list:
    """Search provisions from Python KB content modules (no DB needed)."""
    from hr_advisory.kb.content import (
        employment_act,
        cpf,
        foreign_manpower,
        tafep,
        remaining_domains,
    )
    from hr_advisory.kb.content import industrial_relations

    # Map domain filter names to content modules
    domain_modules = {
        "Employment Act": [employment_act],
        "CPF": [cpf],
        "Foreign Manpower": [foreign_manpower],
        "Fair Employment": [tafep],
        "Workplace Safety and Health": [remaining_domains],
        "Tax": [remaining_domains],
        "Industrial Relations": [industrial_relations],
        "Retrenchment": [industrial_relations],
    }

    all_modules = [
        employment_act,
        cpf,
        foreign_manpower,
        tafep,
        remaining_domains,
        industrial_relations,
    ]
    modules_to_search = domain_modules.get(domain, []) if domain else all_modules

    # Collect all provisions from selected modules
    all_provisions = []
    for mod in modules_to_search:
        try:
            bundle = mod.get_bundle()
            for prov in bundle.get("provisions", []):
                all_provisions.append(prov)
        except Exception:
            continue

    if not all_provisions:
        return []

    # Score by keyword overlap
    query_lower = query.lower()
    stop = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "have",
        "has",
        "do",
        "does",
        "did",
        "will",
        "would",
        "can",
        "need",
        "must",
        "i",
        "me",
        "my",
        "we",
        "you",
        "your",
        "he",
        "she",
        "it",
        "they",
        "this",
        "that",
        "what",
        "which",
        "who",
        "how",
        "when",
        "where",
        "why",
        "if",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "by",
        "from",
        "about",
        "not",
        "no",
        "or",
        "and",
        "but",
        "so",
        "as",
    }
    query_words = [w for w in query_lower.split() if len(w) > 2 and w not in stop]

    if not query_words:
        return all_provisions[:limit]

    scored = []
    for prov in all_provisions:
        searchable = " ".join(
            str(prov.get(f, "")) for f in ("section", "title", "formal_text", "plain_summary")
        ).lower()
        score = sum(1 for w in query_words if w in searchable)
        if score > 0:
            scored.append((score, prov))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


# -- Tool execution ----------------------------------------------------------


def _execute_tool_call(name: str, arguments: dict, company_id: int | None = None) -> str:
    """Execute a tool call and return the result as a JSON string.

    Args:
        name: Tool function name.
        arguments: Tool call arguments from the LLM.
        company_id: Company ID for company-scoped tool calls (e.g. search_company_policies).
    """
    try:
        if name == "search_company_policies":
            if company_id is None:
                return json.dumps({"error": "company_id is required for policy search"})

            from hr_advisory.services.company_policy_search import search_company_policies

            raw_results = search_company_policies(
                query=arguments.get("query", ""),
                company_id=company_id,
                category=arguments.get("category"),
                limit=5,
            )

            # Handle both list and structured dict returns (Fix 14)
            if isinstance(raw_results, dict):
                # Structured zero-result response — pass through directly
                return json.dumps(raw_results, default=str)
            results = raw_results

            # T013: Screen each result's content_excerpt for injection attempts
            screened_results = []
            for r in results:
                excerpt = r.get("content_excerpt", "")
                if excerpt:
                    injection_check = screen_injection(excerpt)
                    if injection_check.result == ScreeningResult.BLOCK:
                        logger.warning(
                            "Injection detected in company policy %s (policy_id=%s), stripping content",
                            r.get("title", ""),
                            r.get("policy_id", ""),
                        )
                        continue  # Strip flagged content entirely
                screened_results.append(r)

            if not screened_results and results:
                # ALL results were stripped due to injection
                return json.dumps(
                    {
                        "results": [],
                        "results_screened": True,
                        "message": (
                            "Relevant company policies were found but their content "
                            "could not be included."
                        ),
                    }
                )

            return json.dumps(screened_results, default=str)

        elif name == "search_kb":
            results = _search_kb_with_fallback(
                query=arguments.get("query", ""),
                domain=arguments.get("domain"),
                limit=5,
            )
            # search_provisions returns provision rows from the DB; the
            # PracticalExample table is separate. Bulk-fetch examples for the
            # matched provision ids in one query and attach.
            provision_ids = [r.get("id") for r in results if r.get("id")]
            examples_by_provision: dict[int, list] = {}
            if provision_ids:
                try:
                    from hr_advisory.services import dataflow_crud

                    for pid in provision_ids:
                        rows = dataflow_crud.list_records(
                            "PracticalExample", {"provision_id": pid}
                        )
                        if rows:
                            examples_by_provision[pid] = [
                                {
                                    "title": row.get("title", ""),
                                    "scenario": row.get("scenario", ""),
                                    "outcome": row.get("outcome", ""),
                                }
                                for row in rows
                            ]
                except Exception:  # noqa: BLE001 — best-effort enrichment
                    examples_by_provision = {}

            # Include enough context for comprehensive answers — plain_summary
            # alone is too thin for a senior advisor to give thorough guidance.
            enriched = []
            for r in results:
                entry = {
                    "section": r.get("section", ""),
                    "title": r.get("title", ""),
                    "plain_summary": r.get("plain_summary", ""),
                    "authority_level": r.get("authority_level", ""),
                }
                # Include interpretation notes (edge cases, penalties, thresholds)
                notes = r.get("interpretation_notes", "")
                if notes:
                    entry["interpretation_notes"] = notes
                # Include practical examples (worked scenarios with numbers).
                # Prefer rows already attached to the provision (Python KB
                # fallback path); otherwise pick up the bulk-fetched DB rows.
                examples = r.get("practical_examples") or examples_by_provision.get(
                    r.get("id")
                )
                if examples:
                    entry["practical_examples"] = examples
                enriched.append(entry)
            return json.dumps(enriched, default=str)

        elif name == "calculate_cpf":
            from hr_advisory.agents.actions.calculator import CalculatorAgent

            calc = CalculatorAgent()
            result = calc.calculate("cpf", arguments)
            return json.dumps(result, default=str)

        elif name == "calculate_leave":
            from hr_advisory.agents.actions.calculator import CalculatorAgent

            calc = CalculatorAgent()
            result = calc.calculate("leave", arguments)
            return json.dumps(result, default=str)

        elif name == "calculate_salary":
            from hr_advisory.agents.actions.calculator import CalculatorAgent

            calc = CalculatorAgent()
            result = calc.calculate("salary", arguments)
            return json.dumps(result, default=str)

        elif name == "calculate_quota_levy":
            from hr_advisory.agents.actions.calculator import CalculatorAgent

            calc = CalculatorAgent()
            result = calc.calculate("quota_levy", arguments)
            return json.dumps(result, default=str)

        elif name == "get_company_context":
            # Use the caller-provided company_id for tenant isolation.
            # Ignore the LLM-provided argument to prevent cross-tenant data access.
            if company_id is None:
                return json.dumps({"error": "company_id is required for company context lookup"})
            try:
                from kailash import LocalRuntime, WorkflowBuilder

                wf = WorkflowBuilder()
                wf.add_node(
                    "CompanyListNode",
                    "find",
                    {"filter": {"id": int(company_id)}, "limit": 1, "enable_cache": False},
                )
                runtime = LocalRuntime()
                results, _ = runtime.execute(wf.build())
                records = results.get("find", {})
                items = records.get("records", []) if isinstance(records, dict) else []
                if items:
                    return json.dumps(items[0], default=str)
                return json.dumps({"error": "Company not found"})
            except Exception as fetch_exc:
                logger.exception(
                    "Failed to fetch company context for company_id=%s: %s",
                    company_id,
                    fetch_exc,
                )
                return json.dumps({"error": "Company context could not be retrieved."})

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as exc:
        logger.exception("Tool call %s failed: %s", name, exc)
        return json.dumps({"error": "An internal error occurred while executing this tool."})


# -- Confidence/risk extraction -----------------------------------------------


def _parse_confidence_and_risk(
    response_text: str,
) -> tuple[str, float, str]:
    """Extract [CONFIDENCE: X.XX] [RISK: tier] from the response tail.

    Returns (cleaned_text, confidence, risk_tier).
    """
    import re

    confidence = 0.7  # default
    risk_tier = "amber"  # default — safer than green

    # Match the confidence/risk markers
    pattern = r"\[CONFIDENCE:\s*([\d.]+)\]\s*\[RISK:\s*(green|amber|red)\]"
    match = re.search(pattern, response_text)
    if match:
        try:
            confidence = float(match.group(1))
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            confidence = 0.7
        risk_tier = match.group(2)
        # Remove the markers from the response
        cleaned = response_text[: match.start()].rstrip()
    else:
        cleaned = response_text

    return cleaned, confidence, risk_tier


# -- The engine ---------------------------------------------------------------


class AdvisoryEngine:
    """Autonomous advisory engine using LLM function calling.

    The LLM decides what tools to call, in what order, and when it has
    enough information to answer. No keyword routing. No fallback templates.
    No hardcoded domain detection.
    """

    def __init__(self, llm_context=None):
        """Initialize with an optional LLMKeyContext.

        If no context is provided, builds one from server .env defaults.
        """
        if llm_context is None:
            from hr_advisory.agents.llm_context import LLMKeyContext

            llm_context = LLMKeyContext.from_server_env()
        self._ctx = llm_context

    def run(
        self,
        query: str,
        conversation_history: list[dict[str, str]],
        company_context: dict | None = None,
        company_id: int | None = None,
        user_context: dict | None = None,
        onboarding_context: str = "",
    ) -> dict[str, Any]:
        """Run the advisory engine.

        Args:
            query: The user's question.
            conversation_history: Prior turns as [{role, content}, ...].
            company_context: Company profile dict for personalisation.
            company_id: Company ID for tool calls.
            user_context: User profile dict (role, name) for personalisation.
            onboarding_context: Formatted onboarding content for employees
                with active onboarding assignments.

        Returns:
            Dict with keys: response_text, risk_tier, confidence, domains,
            citations, usage, degraded.
        """
        from openai import OpenAI

        # Build the OpenAI client
        client = self._build_client()
        model = self._ctx.model or os.environ.get("DEFAULT_LLM_MODEL", "gemini-2.5-flash")

        # Build messages
        system_prompt = _build_system_prompt(company_context, user_context, onboarding_context)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": query})

        # Track usage across rounds
        total_input_tokens = 0
        total_output_tokens = 0
        tools_called: list[str] = []
        kb_results_seen: list[dict] = []
        company_policy_results_seen: list[dict] = []

        # Red-team C3 / O2: pre-retrieval domain classifier. Without
        # this, the engine waits for the LLM to call search_kb — and
        # when the model answers from parametric memory (as gemini /
        # gpt did for CPF), no search_kb runs, domains falls back to
        # "general", and stale training-data answers leak through.
        # Pre-fetching grounded provisions per detected domain and
        # injecting them as a system message ensures the model
        # always has KB content in context from turn 1.
        try:
            from hr_advisory.services.advisory_domain_classifier import (
                classify_domains,
            )

            detected_domains = classify_domains(query)
        except Exception as exc:  # pragma: no cover — defensive
            logger.debug("domain classifier failed: %s", exc)
            detected_domains = []

        if detected_domains:
            # Route per-domain KB lookup through the shared
            # domain_lookup module (red-team P5-AD-followup, 2026-05-19).
            # The previous path called `_search_kb_with_fallback(domain=dom)`
            # which filters by `Domain.name == "cpf"` and got zero rows
            # because the prod KB stores sub-domain rows ("CPF
            # Contribution Rates", "CPF Wage Ceilings", ...) instead.
            # The shared module resolves domain → Act.short_name → all
            # provisions for that Act, mirroring how the compliance
            # health check counts provisions per domain.
            from hr_advisory.kb.domain_lookup import provisions_for_domain

            preseed_lines: list[str] = []
            for dom in detected_domains:
                try:
                    hits = provisions_for_domain(dom, limit=3, query=query)
                except Exception as exc:
                    logger.debug(
                        "pre-fetch failed for domain %s: %s", dom, exc
                    )
                    hits = []
                if hits:
                    # Track so citation extraction picks these up even
                    # if the LLM never explicitly calls search_kb.
                    kb_results_seen.extend(hits)
                    for h in hits:
                        # Provision rows from DataFlow have different
                        # field names than the search_kb wrapper output.
                        # Use the provision-row fields: title + section
                        # + plain_summary.
                        title = (
                            h.get("title")
                            or h.get("section")
                            or h.get("provision_id")
                            or ""
                        )
                        section = h.get("section") or ""
                        pid = h.get("provision_id") or h.get("id") or ""
                        body = (
                            h.get("plain_summary")
                            or h.get("content")
                            or h.get("formal_text")
                            or h.get("text")
                            or ""
                        )[:600]
                        if title or body:
                            preseed_lines.append(
                                f"[{dom.upper()} · {section or pid}] {title}\n{body}"
                            )
            if preseed_lines:
                preseed = (
                    "Relevant Singapore-statute provisions for this question "
                    "(detected domains: "
                    + ", ".join(detected_domains)
                    + "):\n\n"
                    + "\n\n".join(preseed_lines)
                    + "\n\nUse these as your primary grounding. Cite them in "
                    "your answer. If they are insufficient, call search_kb "
                    "for more, but do not answer from parametric memory."
                )
                # Inject just before the user turn so the model treats it
                # as authoritative context, not prior conversation.
                messages.insert(-1, {"role": "system", "content": preseed})
                tools_called.append("preseed_kb")

        try:
            for round_num in range(MAX_TOOL_ROUNDS):
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    timeout=60,
                )

                # Track tokens
                if response.usage:
                    total_input_tokens += response.usage.prompt_tokens
                    total_output_tokens += response.usage.completion_tokens

                choice = response.choices[0]

                # If the model wants to call tools, execute them
                if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                    # Add the assistant message with tool calls.
                    # Strip None/null values — Gemini's OpenAI-compatible endpoint
                    # rejects 'null' struct values on subsequent rounds.
                    msg = choice.message.model_dump(exclude_none=True)
                    messages.append(msg)

                    for tool_call in choice.message.tool_calls:
                        fn_name = tool_call.function.name
                        try:
                            fn_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            fn_args = {}

                        tools_called.append(fn_name)
                        result_str = _execute_tool_call(
                            fn_name, fn_args, company_id=company_id
                        )

                        # Track KB results for citation extraction
                        if fn_name == "search_kb":
                            try:
                                kb_results_seen.extend(json.loads(result_str))
                            except (json.JSONDecodeError, TypeError):
                                pass

                        # Track company policy results for citation extraction
                        if fn_name == "search_company_policies":
                            try:
                                parsed = json.loads(result_str)
                                if isinstance(parsed, list):
                                    company_policy_results_seen.extend(parsed)
                            except (json.JSONDecodeError, TypeError):
                                pass

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": result_str,
                            }
                        )

                    # Steering: if we've done 5+ search_kb calls, nudge the model
                    # to synthesize. gpt-5-mini tends to keep searching indefinitely
                    # on multi-domain queries without this.
                    kb_call_count = sum(1 for t in tools_called if t == "search_kb")
                    if kb_call_count >= 5 and round_num >= 3:
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "You have retrieved enough provisions. "
                                    "Please synthesize your answer now based on "
                                    "what you have found. Do not search further."
                                ),
                            }
                        )

                    # T015: Statutory primacy nudge — if the LLM searched company
                    # policies for a regulated topic but hasn't searched the KB,
                    # nudge it to look up the statutory position first.
                    policy_call_count = sum(
                        1 for t in tools_called if t == "search_company_policies"
                    )
                    if policy_call_count > 0 and kb_call_count == 0:
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "You checked the company's internal policies but "
                                    "have not yet looked up the statutory position. "
                                    "Please search the knowledge base (search_kb) for "
                                    "the relevant legal provisions first — statutory "
                                    "law takes precedence over company policies."
                                ),
                            }
                        )

                    continue  # Next round — let LLM process tool results

                # Model is done — extract the response
                response_text = choice.message.content or ""
                cleaned_text, confidence, risk_tier = _parse_confidence_and_risk(response_text)

                # Extract domains: union of (a) which search_kb calls
                # the LLM made and (b) which domains the pre-retrieval
                # classifier seeded. Red-team C3 / O2: without (b), a
                # CPF question that the LLM answered from memory falls
                # back to "general"; we now preserve the classifier's
                # signal so the response carries the correct domain.
                domains_from_llm = set(self._extract_domains_from_tools(messages))
                domains_from_llm.discard("general")
                combined = sorted(domains_from_llm | set(detected_domains))
                domains = combined or ["general"]

                # Build citations from KB results and company policy results
                citations = self._extract_citations(
                    kb_results_seen, company_policy_results_seen
                )

                return {
                    "response_text": cleaned_text,
                    "risk_tier": risk_tier,
                    "confidence": confidence,
                    "domains": domains,
                    "citations": citations,
                    "tools_called": tools_called,
                    "usage": {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                    },
                    "degraded": False,
                }

            # Exhausted all rounds — use whatever we have
            logger.warning(
                "Advisory engine hit MAX_TOOL_ROUNDS (%d) for query: %.100s",
                MAX_TOOL_ROUNDS,
                query,
            )
            last_content = ""
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    last_content = msg.get("content", "")
                    if last_content:
                        break

            cleaned_text, confidence, risk_tier = _parse_confidence_and_risk(
                last_content or "I was unable to fully process your query. Please try rephrasing."
            )
            return {
                "response_text": cleaned_text,
                "risk_tier": "amber",
                "confidence": min(confidence, 0.5),
                "domains": self._extract_domains_from_tools(messages),
                "citations": self._extract_citations(
                    kb_results_seen, company_policy_results_seen
                ),
                "tools_called": tools_called,
                "usage": {
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                },
                "degraded": True,
            }

        except Exception as exc:
            logger.error("Advisory engine failed: %s", exc, exc_info=True)
            # Translate the most common transient failure modes into copy
            # the user can act on instead of a flat "try again later".
            msg = str(exc).lower()
            if "503" in msg or "unavailable" in msg or "overloaded" in msg:
                response_text = (
                    "The advisory model is temporarily overloaded — usually "
                    "clears in 30-60 seconds. Please try the question again. "
                    "If it keeps failing, ask your HR admin to check the LLM "
                    "provider status."
                )
            elif "429" in msg or "rate" in msg or "quota" in msg:
                response_text = (
                    "We've hit the company's advisory rate limit for the "
                    "moment. Try again in a minute or contact your HR admin "
                    "to review the budget."
                )
            elif "timeout" in msg or "timed out" in msg:
                response_text = (
                    "The advisory engine took too long to respond. Try a "
                    "shorter or more specific question, or retry in a moment."
                )
            else:
                response_text = (
                    "I couldn't generate a grounded answer for this question "
                    "right now. Please try rewording it, or escalate to an "
                    "Employment Law Specialist using the link below."
                )
            return {
                "response_text": response_text,
                "risk_tier": "amber",
                "confidence": 0.3,
                "domains": [],
                "citations": [],
                "tools_called": tools_called,
                "usage": {
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                },
                "degraded": True,
            }

    def _build_client(self):
        """Build an OpenAI-compatible client from the LLM context.

        Google Gemini is supported via Google's OpenAI-compatible endpoint
        (https://ai.google.dev/gemini-api/docs/openai). This means we use
        the OpenAI SDK with Gemini's base_url — no separate SDK needed.
        """
        from openai import OpenAI

        if self._ctx.provider == "ollama":
            base_url = (self._ctx.base_url or "http://localhost:11434").rstrip("/")
            if not base_url.endswith("/v1"):
                base_url += "/v1"
            return OpenAI(api_key="ollama", base_url=base_url)

        if self._ctx.provider == "gemini":
            # Google's OpenAI-compatible endpoint for Gemini
            return OpenAI(
                api_key=self._ctx.api_key,
                base_url=GEMINI_OPENAI_BASE_URL,
            )

        # OpenAI and OpenAI-compatible providers (DeepSeek, Mistral, etc.)
        kwargs: dict[str, Any] = {}
        if self._ctx.api_key:
            kwargs["api_key"] = self._ctx.api_key
        if self._ctx.base_url:
            kwargs["base_url"] = self._ctx.base_url
        return OpenAI(**kwargs)

    @staticmethod
    def _extract_domains_from_tools(messages: list[dict]) -> list[str]:
        """Extract which KB domains were searched from tool call messages."""
        domains = set()
        domain_map = {
            "Employment Act": "employment_act",
            "CPF": "cpf",
            "Foreign Manpower": "foreign_manpower",
            "Fair Employment": "fair_employment",
            "Workplace Safety and Health": "wsh",
            "Tax": "tax",
        }
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            # Check assistant messages for tool calls
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    fn = tc if isinstance(tc, dict) else tc
                    fn_obj = fn.get("function", fn) if isinstance(fn, dict) else fn
                    name = (
                        fn_obj.get("name", "")
                        if isinstance(fn_obj, dict)
                        else getattr(fn_obj, "name", "")
                    )
                    args_str = (
                        fn_obj.get("arguments", "{}")
                        if isinstance(fn_obj, dict)
                        else getattr(fn_obj, "arguments", "{}")
                    )
                    if name == "search_kb":
                        try:
                            args = json.loads(args_str) if isinstance(args_str, str) else args_str
                            domain = args.get("domain", "")
                            if domain and domain in domain_map:
                                domains.add(domain_map[domain])
                        except (json.JSONDecodeError, AttributeError):
                            pass
        return sorted(domains) if domains else ["general"]

    @staticmethod
    def _extract_citations(
        kb_results: list[dict],
        company_policy_results: list[dict] | None = None,
    ) -> list[dict]:
        """Build citation list from KB search results and company policy results.

        Args:
            kb_results: Results from search_kb tool calls.
            company_policy_results: Results from search_company_policies tool calls.

        Returns:
            List of citation dicts with provision_id, title, authority_level.
        """
        seen: set[str] = set()
        citations: list[dict] = []

        # KB citations (statutory, tripartite, etc.)
        for r in kb_results:
            section = r.get("section", "")
            if section and section not in seen:
                seen.add(section)
                citations.append(
                    {
                        "provision_id": section,
                        "title": r.get("title", ""),
                        "authority_level": r.get("authority_level", "statute"),
                    }
                )

        # Company policy citations (T016)
        if company_policy_results:
            for r in company_policy_results:
                policy_id = r.get("policy_id")
                if policy_id is not None:
                    provision_id = f"policy-{policy_id}"
                    if provision_id not in seen:
                        seen.add(provision_id)
                        citations.append(
                            {
                                "provision_id": provision_id,
                                "title": r.get("title", ""),
                                "authority_level": "company_policy",
                            }
                        )

        return citations
