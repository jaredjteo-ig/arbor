# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""LLM-based intent classifier for the Shadow Agent.

Takes a user message and optional page context, classifies it into a
structured ShadowIntent that the executor can act on. Uses OpenAI
(same pattern as the scope guard in guardrails.py) with structured
JSON output.

All API keys come from environment variables — never hardcoded.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

__all__ = [
    "ShadowIntent",
    "ShadowIntentClassifier",
]


@dataclass
class ShadowIntent:
    """Structured intent extracted from a user message."""

    module: str  # "employees", "payroll", "leave", "attendance", etc.
    action: str  # "create", "list", "approve", "navigate", etc.
    entities: dict  # extracted parameters {"name": "John", "salary": 5000}
    trust_level: str  # "autonomous", "propose", "always_propose"
    requires_confirmation: bool
    confirmation_message: str  # human-readable preview of what will happen
    has_attachment: bool  # whether user is uploading / referencing a file
    attachment_intent: str  # "bulk_import", "document_upload", "receipt_upload", ""
    raw_query: str  # original user message

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON responses."""
        return {
            "module": self.module,
            "action": self.action,
            "entities": self.entities,
            "trust_level": self.trust_level,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_message": self.confirmation_message,
            "has_attachment": self.has_attachment,
            "attachment_intent": self.attachment_intent,
            "raw_query": self.raw_query,
        }


# Trust level classification rules:
# - autonomous: read-only operations (list, get, search, view, navigate)
# - propose: write operations (create, update, approve, reject)
# - always_propose: dangerous operations (delete, terminate, cancel payroll)

_AUTONOMOUS_ACTIONS = frozenset(
    {
        "list",
        "get",
        "view",
        "search",
        "navigate",
        "check",
        "balance",
        "summary",
        "history",
        "calendar",
        "dashboard",
        "status",
        "count",
        "download",
        "export",
        "my_payslips",
        "my_leave",
        "my_schedule",
    }
)

_ALWAYS_PROPOSE_ACTIONS = frozenset(
    {
        "delete",
        "terminate",
        "cancel",
        "cancel_payroll",
        "mark_paid",
        "bulk_delete",
        "reset",
        "revoke",
        "deactivate",
        "remove",
    }
)


def _classify_trust_level(action: str) -> tuple[str, bool]:
    """Determine trust level and confirmation requirement from the action.

    Returns:
        (trust_level, requires_confirmation) tuple.
    """
    if action in _AUTONOMOUS_ACTIONS:
        return "autonomous", False
    if action in _ALWAYS_PROPOSE_ACTIONS:
        return "always_propose", True
    # Default: propose (standard write operations need confirmation)
    return "propose", True


# --- Classification prompt ---
# This prompt is the core of the intent classifier. It describes all 19
# modules with their descriptions and common actions so the LLM can route
# accurately.

_CLASSIFICATION_PROMPT = """You are the intent classifier for Arbor, an AI-powered HR platform for Singapore SMEs.
Given a user message and the current page context, classify the user's intent into a structured JSON response.

## Available Modules

1. **employees** — Employee directory, profiles, onboarding, offboarding, family members, skills, documents, custom fields, org chart, bulk import
   Actions: list, get, create, update, delete, search, invite, confirm_probation, extend_probation, import, export, org_chart

2. **payroll** — Payroll runs, payslips, CPF calculations, tax filings (IR8A/IR21), pay items, pay schemes, variance reports, bank files
   Actions: calculate, list_runs, get_run, approve_run, mark_paid, cancel_run, my_payslips, get_payslip, cpf_ytd, generate_ir8a, generate_ir21, simulate, create_adhoc, variance, line_items

3. **leave** — Leave applications, balances, types, policies, public holidays, calendar, encashment, off-in-lieu
   Actions: apply, list, approve, reject, withdraw, cancel, balance, types, policies, calendar, encash, off_in_lieu, public_holidays

4. **attendance** — Clock in/out, daily records, timesheets, lateness/early departure settings, dashboard
   Actions: clock_in, clock_out, today, records, summary, update_record, settings, submit_timesheet, approve_timesheet, reject_timesheet, list_timesheets, dashboard

5. **claims** — Expense claims, categories, receipts, claim groups, approval workflows
   Actions: create, list, get, submit, approve, reject, add_item, upload_receipt, categories, groups, create_group, submit_group, payroll_ready

6. **shifts** — Shift templates, schedules, assignments, publishing, availability, hourly rates, multipliers
   Actions: list_templates, create_template, schedule, create_assignment, publish, my_schedule, availability, hours, hourly_rates, multipliers

7. **appraisals** — Performance review templates, periods, individual appraisals, self-assessment
   Actions: list_templates, create_template, list_periods, create_period, launch_period, my_appraisals, get_appraisal, update_appraisal

8. **projects** — Project management, tasks, time tracking, team assignments
   Actions: list, create, update, delete, list_tasks, create_task, assign, track_time

9. **inventory** — Asset and inventory management, assignments, maintenance
   Actions: list, create, update, delete, assign, unassign, maintenance

10. **recruitment** — Job postings, candidates, interviews, hiring pipeline
    Actions: list_jobs, create_job, publish_job, close_job, list_candidates, add_candidate, update_candidate, list_interviews

11. **reports** — Analytics and reporting across modules
    Actions: payroll_summary, payroll_ytd, headcount, leave_summary, attendance_summary, custom

12. **documents** — Document templates, generation, preview, download, history
    Actions: list_templates, get_template, preview, generate, download, history

13. **compliance** — Regulatory compliance checks, audits, gap analysis
    Actions: check, list, dashboard

14. **settings** — Company settings, policies, configurations
    Actions: get, update, leave_policies, attendance_settings, payslip_settings

15. **advisory** — HR employment law advisory (routes to existing advisory pipeline)
    Actions: query, stream

16. **navigation** — Page navigation within the app (no API call)
    Actions: navigate

17. **calculator** — CPF calculator, overtime calculator, leave proration
    Actions: calculate_cpf, calculate_overtime, calculate_leave

18. **approval_groups** — Multi-level approval workflows
    Actions: list, create, update, delete

19. **search** — Global search across all modules
    Actions: search

## Attachment Detection

If the user mentions uploading, attaching, importing from CSV/Excel/file, or references a document they want to add:
- Set has_attachment to true
- Set attachment_intent to one of: "bulk_import" (CSV/Excel employee import), "document_upload" (general document), "receipt_upload" (claim receipt), "payroll_import" (payroll data), ""

## Trust Level Rules

- "autonomous": Read-only operations (list, get, search, view, navigate, check, balance, summary, history, calendar, dashboard, status, download, export)
- "propose": Standard write operations (create, update, approve, reject, apply, submit, generate)
- "always_propose": Dangerous operations (delete, terminate, cancel, mark_paid, bulk_delete, reset, revoke, deactivate)

## Output Format

Return ONLY valid JSON (no markdown fences, no explanation):
{
    "module": "string — one of the module names above",
    "action": "string — the specific action",
    "entities": {"key": "value pairs extracted from the message"},
    "confirmation_message": "string — human-readable description of what Arbor will do"
}

## Examples

User: "Show me all employees"
Page: dashboard
→ {"module": "employees", "action": "list", "entities": {}, "confirmation_message": "List all employees in your company"}

User: "Apply 2 days annual leave next Monday"
Page: leave
→ {"module": "leave", "action": "apply", "entities": {"leave_type": "annual", "days": 2, "start_date": "next Monday"}, "confirmation_message": "Apply for 2 days of annual leave starting next Monday"}

User: "Run payroll for March"
Page: payroll
→ {"module": "payroll", "action": "calculate", "entities": {"month": "March"}, "confirmation_message": "Calculate payroll for March 2026"}

User: "Delete employee John Tan"
Page: employees
→ {"module": "employees", "action": "delete", "entities": {"name": "John Tan"}, "confirmation_message": "Delete employee record for John Tan (this action is irreversible)"}

User: "Go to leave calendar"
Page: dashboard
→ {"module": "navigation", "action": "navigate", "entities": {"route": "/leave/calendar"}, "confirmation_message": "Navigate to the leave calendar page"}

User: "What's the notice period for termination?"
Page: any
→ {"module": "advisory", "action": "query", "entities": {"topic": "notice period", "context": "termination"}, "confirmation_message": "Look up Singapore employment law on notice periods for termination"}

User: "I want to upload a CSV of new employees"
Page: employees
→ {"module": "employees", "action": "import", "entities": {"format": "csv"}, "confirmation_message": "Import employees from a CSV file"}

User: "Clock me in"
Page: attendance
→ {"module": "attendance", "action": "clock_in", "entities": {}, "confirmation_message": "Record your clock-in for today"}

---

User message: {message}
Current page: {page_context}

Respond with JSON only:"""


class ShadowIntentClassifier:
    """LLM-based intent classifier for the Shadow Agent.

    Uses an OpenAI model to classify user messages into structured intents.
    Falls back to a rule-based classifier when the LLM is unavailable.
    """

    def classify(
        self,
        message: str,
        page_context: str = "dashboard",
    ) -> ShadowIntent:
        """Classify a user message into a structured ShadowIntent.

        Args:
            message: The raw user message.
            page_context: The current page in the frontend (e.g. "dashboard",
                "employees", "payroll").

        Returns:
            A ShadowIntent with module, action, entities, and trust level.
        """
        # Try LLM classification first
        llm_result = self._classify_with_llm(message, page_context)
        if llm_result is not None:
            return llm_result

        # Fall back to rule-based classification
        logger.info("LLM classifier unavailable — using rule-based fallback")
        return self._classify_rule_based(message, page_context)

    def _classify_with_llm(
        self,
        message: str,
        page_context: str,
    ) -> ShadowIntent | None:
        """Attempt LLM-based classification.

        Returns None if the LLM is unavailable or the call fails.
        """
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return None

        try:
            import openai

            client = openai.OpenAI(api_key=api_key)
            model = os.environ.get(
                "OPENAI_DEV_MODEL",
                os.environ.get("OPENAI_PROD_MODEL", "gpt-5-mini-2025-08-07"),
            )

            prompt = _CLASSIFICATION_PROMPT.format(
                message=message,
                page_context=page_context,
            )

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0,
            )

            raw_content = response.choices[0].message.content or ""
            # Strip markdown fences if present
            content = raw_content.strip()
            if content.startswith("```"):
                # Remove ```json and ``` markers
                lines = content.split("\n")
                lines = [line for line in lines if not line.strip().startswith("```")]
                content = "\n".join(lines)

            parsed = json.loads(content)

            module = parsed.get("module", "advisory")
            action = parsed.get("action", "query")
            entities = parsed.get("entities", {})
            confirmation_message = parsed.get("confirmation_message", "")

            # Determine trust level based on action
            trust_level, requires_confirmation = _classify_trust_level(action)

            # Detect attachment references
            has_attachment, attachment_intent = self._detect_attachment(message)

            return ShadowIntent(
                module=module,
                action=action,
                entities=entities,
                trust_level=trust_level,
                requires_confirmation=requires_confirmation,
                confirmation_message=confirmation_message,
                has_attachment=has_attachment,
                attachment_intent=attachment_intent,
                raw_query=message,
            )

        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON: %s", e)
            return None
        except Exception as e:
            logger.warning("LLM intent classification failed: %s", e)
            return None

    def _detect_attachment(self, message: str) -> tuple[bool, str]:
        """Detect file attachment references in the user message.

        Returns:
            (has_attachment, attachment_intent) tuple.
        """
        msg_lower = message.lower()

        # Bulk import patterns
        import_keywords = [
            "csv",
            "excel",
            "xlsx",
            "spreadsheet",
            "bulk import",
            "import file",
            "upload employees",
        ]
        if any(kw in msg_lower for kw in import_keywords):
            return True, "bulk_import"

        # Receipt upload patterns
        receipt_keywords = ["receipt", "upload receipt", "attach receipt", "claim receipt"]
        if any(kw in msg_lower for kw in receipt_keywords):
            return True, "receipt_upload"

        # Document upload patterns
        doc_keywords = [
            "upload document",
            "attach document",
            "upload file",
            "attach file",
            "upload pdf",
            "attach pdf",
            "upload contract",
            "upload letter",
        ]
        if any(kw in msg_lower for kw in doc_keywords):
            return True, "document_upload"

        # Payroll import patterns
        payroll_keywords = ["upload payroll", "import payroll", "payroll file", "payroll csv"]
        if any(kw in msg_lower for kw in payroll_keywords):
            return True, "payroll_import"

        # Generic file references
        generic_keywords = ["upload", "attach", "file", ".csv", ".xlsx", ".pdf", ".doc"]
        if any(kw in msg_lower for kw in generic_keywords):
            return True, ""

        return False, ""

    def _classify_rule_based(
        self,
        message: str,
        page_context: str,
    ) -> ShadowIntent:
        """Rule-based fallback classifier when LLM is unavailable.

        Uses keyword matching to classify the most common intents.
        Falls back to the advisory module for anything unrecognized.
        """
        msg_lower = message.lower().strip()

        # Navigation patterns
        nav_routes = {
            "dashboard": "/my-dashboard",
            "employees": "/employees",
            "payroll": "/payroll",
            "leave": "/leave",
            "attendance": "/attendance",
            "claims": "/claims",
            "shifts": "/shifts",
            "appraisals": "/appraisals",
            "projects": "/projects",
            "inventory": "/inventory",
            "recruitment": "/recruitment",
            "reports": "/reports",
            "documents": "/documents",
            "compliance": "/compliance",
            "settings": "/settings",
            "calculator": "/calculator",
            "advisory": "/advisory",
            "leave calendar": "/leave/calendar",
            "org chart": "/employees/org-chart",
        }
        for keyword, route in nav_routes.items():
            if msg_lower.startswith("go to") and keyword in msg_lower:
                return ShadowIntent(
                    module="navigation",
                    action="navigate",
                    entities={"route": route},
                    trust_level="autonomous",
                    requires_confirmation=False,
                    confirmation_message=f"Navigate to {keyword}",
                    has_attachment=False,
                    attachment_intent="",
                    raw_query=message,
                )

        # Employee patterns
        if any(
            kw in msg_lower
            for kw in ["show employees", "list employees", "all employees", "employee list"]
        ):
            return ShadowIntent(
                module="employees",
                action="list",
                entities={},
                trust_level="autonomous",
                requires_confirmation=False,
                confirmation_message="List all employees in your company",
                has_attachment=False,
                attachment_intent="",
                raw_query=message,
            )

        # Leave patterns
        if any(kw in msg_lower for kw in ["leave balance", "my leave", "how many days leave"]):
            return ShadowIntent(
                module="leave",
                action="balance",
                entities={},
                trust_level="autonomous",
                requires_confirmation=False,
                confirmation_message="Check your leave balance",
                has_attachment=False,
                attachment_intent="",
                raw_query=message,
            )
        if any(kw in msg_lower for kw in ["apply leave", "take leave", "apply for leave"]):
            return ShadowIntent(
                module="leave",
                action="apply",
                entities={},
                trust_level="propose",
                requires_confirmation=True,
                confirmation_message="Apply for leave",
                has_attachment=False,
                attachment_intent="",
                raw_query=message,
            )

        # Attendance patterns
        if any(kw in msg_lower for kw in ["clock in", "clock me in", "punch in"]):
            return ShadowIntent(
                module="attendance",
                action="clock_in",
                entities={},
                trust_level="propose",
                requires_confirmation=True,
                confirmation_message="Record your clock-in for today",
                has_attachment=False,
                attachment_intent="",
                raw_query=message,
            )
        if any(kw in msg_lower for kw in ["clock out", "clock me out", "punch out"]):
            return ShadowIntent(
                module="attendance",
                action="clock_out",
                entities={},
                trust_level="propose",
                requires_confirmation=True,
                confirmation_message="Record your clock-out for today",
                has_attachment=False,
                attachment_intent="",
                raw_query=message,
            )

        # Payroll patterns
        if any(kw in msg_lower for kw in ["my payslip", "my payslips", "show payslip"]):
            return ShadowIntent(
                module="payroll",
                action="my_payslips",
                entities={},
                trust_level="autonomous",
                requires_confirmation=False,
                confirmation_message="View your payslips",
                has_attachment=False,
                attachment_intent="",
                raw_query=message,
            )
        if any(kw in msg_lower for kw in ["run payroll", "calculate payroll", "process payroll"]):
            return ShadowIntent(
                module="payroll",
                action="calculate",
                entities={},
                trust_level="propose",
                requires_confirmation=True,
                confirmation_message="Calculate payroll",
                has_attachment=False,
                attachment_intent="",
                raw_query=message,
            )

        # Attachment detection
        has_attachment, attachment_intent = self._detect_attachment(message)

        # Default: route to advisory pipeline
        return ShadowIntent(
            module="advisory",
            action="query",
            entities={"query": message},
            trust_level="autonomous",
            requires_confirmation=False,
            confirmation_message="Ask the HR advisory about your question",
            has_attachment=has_attachment,
            attachment_intent=attachment_intent,
            raw_query=message,
        )
