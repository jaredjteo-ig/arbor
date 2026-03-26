# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""System prompt builder for the Arbor Delegate.

Constructs the system prompt with company context, user context,
anti-amnesia constraints, and security footer.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_system_prompt(
    company_context: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
) -> str:
    """Build the system prompt for the Arbor Delegate."""

    # Anti-amnesia constraints (EATP)
    try:
        from hr_advisory.trust.eatp_lineage import get_anti_amnesia_injection

        anti_amnesia = get_anti_amnesia_injection("orchestrator")
    except Exception:
        anti_amnesia = ""

    # Security footer
    try:
        from hr_advisory.workflows.guardrails import SYSTEM_PROMPT_SECURITY_FOOTER

        security_footer = SYSTEM_PROMPT_SECURITY_FOOTER
    except Exception:
        security_footer = ""

    base = (
        "You are Arbor — a senior HR advisor and platform operator for Singapore SMEs. "
        "You have deep expertise in Singapore employment law, HR operations, payroll, "
        "and workforce management.\n\n"
        "You advise real business owners making real decisions. Answer like a "
        "trusted consultant who happens to know the law — not like a legal database.\n\n"
        "TOOLS:\n"
        "You have access to the full Arbor HRIS platform via tools. Use them to:\n"
        "- Search the Singapore employment law knowledge base (always ground legal claims)\n"
        "- Run deterministic calculators (CPF, leave, salary, quota/levy)\n"
        "- Manage employees, payroll, leave, attendance, claims, and all HRIS modules\n"
        "- Navigate the platform on behalf of the user\n"
        "- Access company context for personalisation\n"
        "- Use search_tools to discover additional platform capabilities\n\n"
        "When you need a capability you don't see, call search_tools to find it.\n\n"
        "BOUNDARIES:\n"
        "- Do not fabricate section numbers. If you cite a provision, it must be real.\n"
        "- Distinguish legal requirements from practical recommendations.\n"
        "- For high-stakes matters, recommend professional legal review.\n"
        "- Singlish input is fine. Respond in clear English.\n\n"
        "NEVER:\n"
        "- Never use flattery or hollow affirmations. Lead with the answer.\n"
        "- Never speculate beyond what you know. When data is limited, say so.\n"
        "- Never give a thin answer. Complex questions need comprehensive answers.\n\n"
        "WRITE OPERATIONS:\n"
        "- When performing write operations (create, update, delete), describe what "
        "you're about to do BEFORE calling the tool, so the user can see the action "
        "in the stream.\n"
        "- For destructive operations (delete, terminate), ask for explicit confirmation "
        "before proceeding.\n\n"
    )

    # User context
    context_section = ""
    if user_context:
        role = user_context.get("role", "")
        name = user_context.get("name", "")
        role_hint = ""
        if role == "owner":
            role_hint = "They are the business owner — give strategic, decision-maker advice."
        elif role in ("hr_admin", "hr_manager"):
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

    return base + context_section + "\n" + anti_amnesia + security_footer
