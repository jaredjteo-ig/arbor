"""Shadow Agent API — contextual intelligence and command execution.

Provides two layers of functionality:

1. **Context API** (deterministic, no LLM) — page-aware compliance insights,
   regulatory alerts, deadline reminders, and inline annotations that the
   shadow agent UI renders as margin notes and inline risk labels.

2. **Execution API** (LLM-powered) — the intelligence layer that understands
   user intent and executes actions on their behalf through the PACE loop
   (Preview, Approve, Confirm, Exit).

Context data is sourced from the compliance checker, regulatory update
pipeline, and KB provision content. Execution uses the Shadow Agent
engine (intent classifier, tool registry, executor, PACE manager).
"""

from __future__ import annotations

import logging
from collections import OrderedDict, deque
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.workflows.compliance_checker import (
    ComplianceCheckInput,
    ComplianceFinding,
    check_compliance,
)
from hr_advisory.workflows.regulatory_updates import (
    UpdateStatus,
    UpdateUrgency,
    list_updates,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Page-to-domain mapping ────────────────────────────────────
# Maps frontend page names to the regulatory domains that are
# relevant for annotations on that page.

_PAGE_DOMAINS: dict[str, list[str]] = {
    "dashboard": [
        "Employment Act",
        "CPF",
        "Workplace Safety & Health",
        "Fair Employment",
        "Foreign Manpower",
    ],
    "compliance": [
        "Employment Act",
        "CPF",
        "Workplace Safety & Health",
        "Fair Employment",
        "Foreign Manpower",
    ],
    "employees": ["Employment Act", "CPF", "Foreign Manpower"],
    "payroll": ["Employment Act", "CPF"],
    "calculator": ["CPF"],
    "documents": ["Employment Act"],
    "leave": ["Employment Act"],
    "settings": [],
}

# ── Provision-level annotation data ───────────────────────────
# Deterministic mapping from compliance checker provision IDs to
# annotation metadata (element targets, severity, fine amounts).
# These are rendered as inline margin notes on specific UI elements.

_PROVISION_ANNOTATIONS: dict[str, dict[str, Any]] = {
    "EA-S95-KETs": {
        "element_id": "ket-checkbox",
        "text": "Mandatory — fine up to $5,000 per offence (EA s95A)",
        "severity": "high",
        "fine_amount": "$5,000 per offence",
        "provision_ref": "EA s95A",
    },
    "EA-KET": {
        "element_id": "contracts-section",
        "text": "Written contracts required for employees earning up to $4,500 (EA)",
        "severity": "medium",
        "fine_amount": None,
        "provision_ref": "EA",
    },
    "EA-S88A-payslip": {
        "element_id": "payslip-checkbox",
        "text": "Mandatory — fine up to $5,000 per offence (EA s88A)",
        "severity": "high",
        "fine_amount": "$5,000 per offence",
        "provision_ref": "EA s88A",
    },
    "EA-PART-X-annual-leave": {
        "element_id": "leave-records-section",
        "text": "Leave records required for MOM inspections (EA Part X)",
        "severity": "medium",
        "fine_amount": None,
        "provision_ref": "EA Part X",
    },
    "EA-PART-IV-hours": {
        "element_id": "overtime-records-section",
        "text": "OT records required for Part IV employees (EA Part IV)",
        "severity": "medium",
        "fine_amount": None,
        "provision_ref": "EA Part IV",
    },
    "WSHA-S12": {
        "element_id": "safety-policy-section",
        "text": "WSH policy required for companies with 10+ employees or foreign workers (WSH Act s12)",
        "severity": "high",
        "fine_amount": "Up to $200,000",
        "provision_ref": "WSH Act s12",
    },
    "TGFEP-GRIEVANCE": {
        "element_id": "grievance-section",
        "text": "Recommended by Tripartite Guidelines on Fair Employment Practices",
        "severity": "low",
        "fine_amount": None,
        "provision_ref": "TGFEP",
    },
    "CPFA-S52": {
        "element_id": "cpf-registration-section",
        "text": "Late CPF payment incurs 18% p.a. interest (CPF Act s52)",
        "severity": "high",
        "fine_amount": "18% p.a. interest + penalties",
        "provision_ref": "CPF Act s52",
    },
    "TGFWAR-request-process": {
        "element_id": "fwa-policy-section",
        "text": "Employers must respond to FWA requests within 2 months (TG-FWAR)",
        "severity": "low",
        "fine_amount": None,
        "provision_ref": "TG-FWAR",
    },
    "EFMA-conditions": {
        "element_id": "foreign-worker-section",
        "text": "Ensure all work passes are valid and conditions are met (EFMA)",
        "severity": "low",
        "fine_amount": "Pass revocation + fines",
        "provision_ref": "EFMA",
    },
}

# ── Calculator-specific annotation data ──────────────────────
# Static regulatory context notes for calculator pages.

_CALCULATOR_ANNOTATIONS: list[dict[str, str]] = [
    {
        "context": "cpf",
        "text": "2026 OW ceiling: $8,000. Contributions on OW above this are not required.",
    },
    {
        "context": "cpf",
        "text": (
            "2026 AW ceiling: $102,000 minus total OW subject to CPF for the year. "
            "Contributions on AW above this are not required."
        ),
    },
    {
        "context": "cpf",
        "text": (
            "Senior worker CPF rates (aged 55-70) increase in 2026 as part of "
            "the scheduled step-up plan."
        ),
    },
    {
        "context": "overtime",
        "text": (
            "OT rate: 1.5x hourly basic rate. Hourly rate = monthly basic / (26 x 8). "
            "Maximum 72 hours OT per month (EA s37)."
        ),
    },
]

# ── Known deadline patterns ───────────────────────────────────
# Static deadlines that recur monthly/annually. Days remaining
# is computed dynamically at request time.

_RECURRING_DEADLINES: list[dict[str, Any]] = [
    {
        "id": "cpf-deadline",
        "type": "deadline",
        "title": "CPF submission deadline",
        "description": "Monthly CPF contributions due by 14th of the following month",
        "day_of_month": 14,
    },
    {
        "id": "ir8a-deadline",
        "type": "deadline",
        "title": "IR8A filing deadline",
        "description": "Annual IR8A returns to IRAS due by 1 March",
        "month": 3,
        "day_of_month": 1,
    },
    {
        "id": "levy-deadline",
        "type": "deadline",
        "title": "Foreign worker levy payment",
        "description": "Monthly foreign worker levy due by 14th of the following month",
        "day_of_month": 14,
    },
]


def _days_until_next_occurrence(
    today: date,
    day_of_month: int,
    month: int | None = None,
) -> int:
    """Calculate days remaining until the next occurrence of a deadline.

    For monthly deadlines (month=None), returns days until the given
    day_of_month in the current or next month.

    For annual deadlines, returns days until that month/day this year
    or next year.
    """
    if month is not None:
        # Annual deadline
        try:
            target = date(today.year, month, day_of_month)
        except ValueError:
            target = date(today.year, month, 28)
        if target < today:
            try:
                target = date(today.year + 1, month, day_of_month)
            except ValueError:
                target = date(today.year + 1, month, 28)
        return (target - today).days

    # Monthly deadline
    try:
        target = date(today.year, today.month, day_of_month)
    except ValueError:
        target = date(today.year, today.month, 28)

    if target < today:
        # Move to next month
        if today.month == 12:
            try:
                target = date(today.year + 1, 1, day_of_month)
            except ValueError:
                target = date(today.year + 1, 1, 28)
        else:
            try:
                target = date(today.year, today.month + 1, day_of_month)
            except ValueError:
                target = date(today.year, today.month + 1, 28)

    return (target - today).days


def _build_compliance_insights(
    findings: list[ComplianceFinding],
    page_domains: list[str],
) -> list[dict[str, Any]]:
    """Convert compliance findings into shadow agent insight entries.

    Filters findings to only those relevant to the current page's
    domains. Each insight carries an action with a navigation target
    so the shadow UI can link to the appropriate page.
    """
    # Domain-to-page mapping for action targets
    domain_nav: dict[str, str] = {
        "Employment Act": "/documents",
        "CPF": "/calculator",
        "Workplace Safety & Health": "/compliance",
        "Fair Employment": "/compliance",
        "Foreign Manpower": "/employees",
    }

    insights: list[dict[str, Any]] = []
    for finding in findings:
        if finding.domain not in page_domains:
            continue

        annotation = _PROVISION_ANNOTATIONS.get(finding.provision_id, {})
        insight: dict[str, Any] = {
            "id": f"compliance-{finding.provision_id}",
            "type": "compliance_gap",
            "severity": finding.severity,
            "title": finding.issue,
            "description": finding.recommendation,
            "provision": annotation.get("provision_ref", finding.provision_id),
            "action": {
                "type": "navigate",
                "target": domain_nav.get(finding.domain, "/compliance"),
            },
        }
        fine = annotation.get("fine_amount")
        if fine:
            insight["fine_amount"] = fine

        insights.append(insight)

    return insights


def _build_regulatory_alerts(page_domains: list[str]) -> list[dict[str, Any]]:
    """Build regulatory alert entries from published updates and seed alerts.

    Returns alerts relevant to the current page's domains, plus
    deadline reminders.
    """
    alerts: list[dict[str, Any]] = []
    today = date.today()

    # Pull published regulatory updates from the update pipeline
    published = list_updates(UpdateStatus.PUBLISHED)
    for update in published:
        # Check domain overlap with page
        update_domains_lower = [d.lower() for d in update.domains_affected]
        page_domains_lower = [d.lower() for d in page_domains]
        has_overlap = any(
            ud in pd or pd in ud for ud in update_domains_lower for pd in page_domains_lower
        )

        if not has_overlap and page_domains:
            continue

        days_since = (today - update.effective_date).days
        alerts.append(
            {
                "id": f"update-{update.id}",
                "type": "regulatory_update",
                "title": update.title,
                "description": update.description,
                "source": update.source,
                "urgency": update.urgency.value,
                "effective_date": update.effective_date.isoformat(),
                "days_since_effective": max(0, days_since),
            }
        )

    # Add seed alerts from the alerts router for broader coverage
    from hr_advisory.api.routers.alerts import _get_seed_alerts

    seed_alerts = _get_seed_alerts()
    existing_ids = {a["id"] for a in alerts}
    for alert in seed_alerts:
        if alert["id"] in existing_ids:
            continue

        # Filter by domain relevance
        alert_domains = alert.get("domains_affected", [])
        alert_domains_lower = [d.lower() for d in alert_domains]
        page_domains_lower = [d.lower() for d in page_domains]
        has_overlap = any(
            ad in pd or pd in ad for ad in alert_domains_lower for pd in page_domains_lower
        )
        if not has_overlap and page_domains:
            continue

        urgency = alert.get("urgency", "medium")
        # Only include critical and high urgency alerts in shadow context
        if urgency not in ("critical", "high"):
            continue

        alerts.append(
            {
                "id": alert["id"],
                "type": "regulatory_update",
                "title": alert["title"],
                "description": alert.get("impact_summary", alert["description"]),
                "source": alert.get("source", ""),
                "urgency": urgency,
                "effective_date": alert.get("effective_date", ""),
            }
        )

    # Add recurring deadline reminders
    for deadline in _RECURRING_DEADLINES:
        days_remaining = _days_until_next_occurrence(
            today,
            deadline["day_of_month"],
            deadline.get("month"),
        )
        # Only show deadlines within 30 days
        if days_remaining <= 30:
            # Check domain relevance
            deadline_id = deadline["id"]
            relevant = not page_domains  # show on all pages if no filter
            if not relevant:
                page_lower = [d.lower() for d in page_domains]
                if "cpf" in deadline_id and any("cpf" in d for d in page_lower):
                    relevant = True
                elif "ir8a" in deadline_id:
                    relevant = True  # Tax is broadly relevant
                elif "levy" in deadline_id and any("foreign" in d for d in page_lower):
                    relevant = True
                # On dashboard, show all deadlines
                elif any("employment" in d for d in page_lower):
                    relevant = True

            if relevant:
                alerts.append(
                    {
                        "id": deadline["id"],
                        "type": "deadline",
                        "title": deadline["title"],
                        "description": deadline["description"],
                        "days_remaining": days_remaining,
                    }
                )

    return alerts


def _build_annotations(
    findings: list[ComplianceFinding],
    page: str,
) -> dict[str, list[dict[str, str]]]:
    """Build page-specific inline annotations from compliance findings and KB data.

    Returns two annotation categories:
    - compliance: mapped to specific UI elements with severity and provision refs
    - calculators: contextual notes for calculator pages
    """
    compliance_annotations: list[dict[str, str]] = []
    for finding in findings:
        annotation_data = _PROVISION_ANNOTATIONS.get(finding.provision_id)
        if not annotation_data:
            continue

        compliance_annotations.append(
            {
                "element_id": annotation_data["element_id"],
                "text": annotation_data["text"],
                "severity": annotation_data["severity"],
            }
        )

    # Calculator annotations — only on relevant pages
    calculator_annotations: list[dict[str, str]] = []
    if page in ("calculator", "payroll", "dashboard"):
        for ann in _CALCULATOR_ANNOTATIONS:
            calculator_annotations.append(
                {
                    "context": ann["context"],
                    "text": ann["text"],
                }
            )

    result: dict[str, list[dict[str, str]]] = {}
    if compliance_annotations:
        result["compliance"] = compliance_annotations
    if calculator_annotations:
        result["calculators"] = calculator_annotations

    return result


# ── Endpoints ─────────────────────────────────────────────────


@router.get("/context")
async def shadow_context(
    page: str = "dashboard",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return contextual data for the shadow agent based on the current page.

    The response includes compliance insights, regulatory alerts, and
    page-specific annotations that the shadow margin and inline annotation
    system will render.

    Query Parameters:
        page: The current page name (e.g. "dashboard", "compliance",
              "employees", "payroll", "calculator", "documents", "leave").
    """
    company_id = get_current_company_id(current_user)
    page_domains = _PAGE_DOMAINS.get(page, _PAGE_DOMAINS["dashboard"])

    # Run compliance check with a default input profile.
    # In production this would load the company's actual compliance state
    # from the database. For now we use a conservative default that
    # surfaces the most common gaps.
    compliance_input = ComplianceCheckInput(
        company_size=10,
        has_foreign_workers=True,
        sector="general",
        has_ket_issued=False,
        has_written_contracts=False,
        has_payslip_system=True,
        has_leave_records=True,
        has_ot_records=False,
        has_safety_policy=False,
        has_grievance_process=False,
        has_cpf_registered=True,
        has_fwa_policy=False,
    )

    result = check_compliance(compliance_input)

    insights = _build_compliance_insights(result.findings, page_domains)
    alerts = _build_regulatory_alerts(page_domains)
    annotations = _build_annotations(result.findings, page)

    logger.info(
        "Shadow context for page=%s, company_id=%s: %d insights, %d alerts, %d annotation groups",
        page,
        company_id,
        len(insights),
        len(alerts),
        len(annotations),
    )

    return {
        "page": page,
        "company_id": company_id,
        "compliance_score": result.score,
        "risk_tier": result.risk_tier,
        "insights": insights,
        "alerts": alerts,
        "annotations": annotations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# Shadow Agent Execution Engine — the intelligence layer
# ══════════════════════════════════════════════════════════════
#
# These endpoints power the command bar. Arbor understands intent
# and EXECUTES — it is NOT a chatbot.
#
# PACE loop: Preview → Approve → Confirm → Exit
# Trust levels: autonomous (reads), propose (writes), always_propose (dangerous)

# In-memory action history per user (bounded, for undo/history)
_MAX_HISTORY_PER_USER = 100
_action_history: dict[str, deque] = {}  # user_id → deque of action dicts
_MAX_HISTORY_USERS = 10000


def _get_jwt_token(request: Request) -> str:
    """Extract the raw JWT token from the Authorization header.

    The Shadow Agent executor forwards this exact token to API calls,
    ensuring it operates with the same permissions as the user.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return ""


def _record_action(user_id: str, action: dict) -> None:
    """Record a completed action in the user's history (bounded deque)."""
    if len(_action_history) >= _MAX_HISTORY_USERS and user_id not in _action_history:
        # Evict oldest user
        try:
            oldest_key = next(iter(_action_history))
            _action_history.pop(oldest_key, None)
        except StopIteration:
            pass

    if user_id not in _action_history:
        _action_history[user_id] = deque(maxlen=_MAX_HISTORY_PER_USER)
    _action_history[user_id].appendleft(action)


@router.post("/execute")
async def shadow_execute(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Main command entry point for the Shadow Agent.

    Classifies the user's intent from their message, then either:
    - Executes immediately (autonomous trust level — reads)
    - Returns a PACE preview for confirmation (propose/always_propose — writes)
    - Routes to the advisory pipeline (advisory module)
    - Returns a navigation instruction (navigation module)

    Request body:
        message: str — the user's command/question
        page_context: str — current frontend page (default: "dashboard")

    Returns a structured response with Arbor identity.
    """
    from hr_advisory.shadow.intent_classifier import ShadowIntentClassifier
    from hr_advisory.shadow.tool_registry import get_tool_registry
    from hr_advisory.shadow.executor import ShadowExecutor
    from hr_advisory.shadow.pace import PaceStep, get_pace_manager
    from hr_advisory.shadow.formatter import ArborFormatter
    from hr_advisory.workflows.guardrails import (
        ScreeningResult,
        screen_injection,
        screen_scope,
    )

    body = await request.json()
    message = body.get("message", "").strip()
    page_context = body.get("page_context", "dashboard")
    user_id = str(current_user.get("sub", "anonymous"))
    jwt_token = _get_jwt_token(request)

    if not message:
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    # ── Step 1: Guardrails — scope check and injection detection ──
    scope_result = screen_scope(message)
    if scope_result.result == ScreeningResult.BLOCK:
        formatter = ArborFormatter()
        return {
            "type": "out_of_scope",
            "message": formatter.format_error(scope_result.reason),
            "alternative_guidance": scope_result.alternative_guidance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    injection_result = screen_injection(message, user_id=user_id)
    if injection_result.result == ScreeningResult.BLOCK:
        formatter = ArborFormatter()
        return {
            "type": "blocked",
            "message": formatter.format_error(injection_result.reason),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Step 2: Intent classification ─────────────────────────────
    classifier = ShadowIntentClassifier()
    intent = classifier.classify(message, page_context)

    logger.info(
        "Shadow intent: module=%s, action=%s, trust=%s, user=%s",
        intent.module,
        intent.action,
        intent.trust_level,
        user_id,
    )

    formatter = ArborFormatter()

    # ── Step 3: Route by module ───────────────────────────────────

    # 3a. Advisory — route to the existing advisory pipeline
    if intent.module == "advisory":
        return {
            "type": "advisory",
            "message": formatter.format_advisory_routing(message),
            "intent": intent.to_dict(),
            "route_to": "/advisory/query",
            "query": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # 3b. Navigation — return route for frontend to navigate to
    if intent.module == "navigation":
        route = intent.entities.get("route", "/my-dashboard")
        description = intent.confirmation_message or route
        nav = formatter.format_navigation(route, description)
        return {
            "type": "navigation",
            "message": nav["message"],
            "route": nav["route"],
            "intent": intent.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # 3c. Attachment detected — prompt for file upload
    if intent.has_attachment and intent.attachment_intent:
        return {
            "type": "attachment_required",
            "message": formatter.format_attachment_prompt(intent.attachment_intent),
            "intent": intent.to_dict(),
            "attachment_intent": intent.attachment_intent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Step 4: Resolve tool from registry ────────────────────────
    registry = get_tool_registry()
    tool = registry.resolve_tool(intent.module, intent.action)

    if tool is None:
        # No registered tool — suggest advisory or navigation fallback
        logger.warning(
            "No tool found for %s.%s — falling back to advisory",
            intent.module,
            intent.action,
        )
        return {
            "type": "advisory",
            "message": formatter.format_advisory_routing(message),
            "intent": intent.to_dict(),
            "route_to": "/advisory/query",
            "query": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Step 5: Trust level enforcement ───────────────────────────

    if intent.trust_level == "autonomous":
        # Read-only — execute immediately
        executor = ShadowExecutor()
        result = await executor.execute(tool, intent.entities, jwt_token)

        if result.success:
            display_message = formatter.format_read(result.data, intent.module, intent.action)
        else:
            display_message = formatter.format_error(result.error)

        # Record in history
        _record_action(
            user_id,
            {
                "session_id": None,
                "module": intent.module,
                "action": intent.action,
                "trust_level": "autonomous",
                "success": result.success,
                "timestamp": result.timestamp,
                "message": message,
            },
        )

        return {
            "type": "result",
            "message": display_message,
            "data": result.data if result.success else None,
            "success": result.success,
            "error": result.error if not result.success else None,
            "intent": intent.to_dict(),
            "execution": result.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    else:
        # propose or always_propose — create PACE session for confirmation
        pace_manager = get_pace_manager()

        step = PaceStep(
            description=tool.description,
            tool_module=tool.module,
            tool_action=tool.action,
            method=tool.method,
            path=tool.path,
            params=dict(intent.entities),
        )

        session = pace_manager.create_session(
            user_id=user_id,
            intent_module=intent.module,
            intent_action=intent.action,
            confirmation_message=intent.confirmation_message,
            steps=[step],
        )

        preview_message = formatter.format_preview(session.to_dict())

        return {
            "type": "preview",
            "message": preview_message,
            "session_id": session.id,
            "session": session.to_dict(),
            "intent": intent.to_dict(),
            "requires_confirmation": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/confirm")
async def shadow_confirm(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Confirm and execute a pending PACE session.

    Request body:
        session_id: str — the PACE session ID to confirm
    """
    from hr_advisory.shadow.pace import get_pace_manager
    from hr_advisory.shadow.formatter import ArborFormatter

    body = await request.json()
    session_id = body.get("session_id", "")
    user_id = str(current_user.get("sub", "anonymous"))
    jwt_token = _get_jwt_token(request)

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")

    pace_manager = get_pace_manager()
    session = pace_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please try again.",
        )

    # Tenant isolation: verify the session belongs to this user
    if session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.status != "preview":
        raise HTTPException(
            status_code=409,
            detail=f"Session cannot be confirmed — current status is '{session.status}'.",
        )

    # Execute the session
    executed = await pace_manager.execute_session(session_id, jwt_token)
    if executed is None:
        raise HTTPException(status_code=500, detail="Session execution failed.")

    formatter = ArborFormatter()

    if executed.status == "done":
        # Format based on the primary step's result
        if executed.results:
            first_result = executed.results[0]
            if first_result.get("success"):
                display_message = formatter.format_write(
                    first_result.get("data", {}),
                    executed.intent_module,
                    executed.intent_action,
                )
            else:
                display_message = formatter.format_error(first_result.get("error", "Unknown error"))
        else:
            display_message = formatter.format_multi_step(executed.to_dict())
    else:
        display_message = formatter.format_multi_step(executed.to_dict())

    # Record in history
    _record_action(
        user_id,
        {
            "session_id": session_id,
            "module": executed.intent_module,
            "action": executed.intent_action,
            "trust_level": "propose",
            "success": executed.status == "done",
            "timestamp": executed.completed_at or datetime.now(timezone.utc).isoformat(),
            "message": executed.confirmation_message,
        },
    )

    return {
        "type": "result",
        "message": display_message,
        "session_id": session_id,
        "session": executed.to_dict(),
        "success": executed.status == "done",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/cancel")
async def shadow_cancel(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Cancel a pending PACE session.

    Request body:
        session_id: str — the PACE session ID to cancel
    """
    from hr_advisory.shadow.pace import get_pace_manager
    from hr_advisory.shadow.formatter import ArborFormatter

    body = await request.json()
    session_id = body.get("session_id", "")
    user_id = str(current_user.get("sub", "anonymous"))

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")

    pace_manager = get_pace_manager()
    session = pace_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired.",
        )

    # Tenant isolation
    if session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found.")

    cancelled = pace_manager.cancel_session(session_id)
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail=f"Session cannot be cancelled — current status is '{session.status}'.",
        )

    formatter = ArborFormatter()
    return {
        "type": "cancelled",
        "message": formatter.PREFIX + "Action cancelled.",
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/undo")
async def shadow_undo(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Undo a recently completed action.

    Undo support is limited to actions that have a logical inverse.
    Currently supported: leave applications (withdraw), claims (withdraw).
    Other actions return an informational message about manual reversal.

    Request body:
        session_id: str — (optional) specific session to undo. If not
            provided, undoes the most recent undoable action.
    """
    from hr_advisory.shadow.formatter import ArborFormatter

    body = await request.json()
    target_session_id = body.get("session_id", "")
    user_id = str(current_user.get("sub", "anonymous"))

    formatter = ArborFormatter()

    history = _action_history.get(user_id, deque())
    if not history:
        return {
            "type": "info",
            "message": formatter.PREFIX + "No recent actions to undo.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Find the target action
    target_action = None
    if target_session_id:
        for action in history:
            if action.get("session_id") == target_session_id:
                target_action = action
                break
    else:
        # Find the most recent successful write action
        for action in history:
            if action.get("success") and action.get("trust_level") != "autonomous":
                target_action = action
                break

    if target_action is None:
        return {
            "type": "info",
            "message": formatter.PREFIX + "No undoable actions found in your recent history.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Check if the action type supports undo
    module = target_action.get("module", "")
    action = target_action.get("action", "")
    undoable_actions = {
        ("leave", "apply"): "You can withdraw this leave application from the Leave page.",
        (
            "claims",
            "create",
        ): "You can delete this claim from the Claims page before submitting it.",
        (
            "claims",
            "submit",
        ): "You can ask your manager to reject this claim, or contact HR to reverse it.",
        ("attendance", "clock_in"): "Clock-in records can be corrected by your HR administrator.",
        ("attendance", "clock_out"): "Clock-out records can be corrected by your HR administrator.",
    }

    guidance = undoable_actions.get((module, action))
    if guidance:
        return {
            "type": "undo_guidance",
            "message": formatter.PREFIX + guidance,
            "original_action": target_action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "type": "undo_not_supported",
        "message": formatter.PREFIX
        + (
            f"The '{action}' action on '{module}' cannot be automatically undone. "
            "Please contact your HR administrator for assistance."
        ),
        "original_action": target_action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
async def shadow_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
) -> dict:
    """List recent Arbor actions for the current user.

    Query parameters:
        limit: int — maximum number of actions to return (default: 20, max: 100)

    Returns the user's action history in reverse chronological order.
    """
    user_id = str(current_user.get("sub", "anonymous"))
    max_limit = min(limit, 100)

    history = _action_history.get(user_id, deque())
    actions = list(history)[:max_limit]

    return {
        "actions": actions,
        "total": len(history),
        "showing": len(actions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# Shadow Agent Ambient Layer — briefing & nudges
# ══════════════════════════════════════════════════════════════
#
# Deterministic (no LLM) endpoints that power the proactive
# dashboard briefing and contextual page nudges.


@router.get("/briefing")
async def shadow_briefing(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return a morning briefing for the current user's dashboard.

    The briefing aggregates pending actions, upcoming deadlines,
    attention items, and quick stats from across all HRIS modules.
    All data is deterministic — no LLM calls.

    Returns a categorized briefing dict with:
        pending_actions, upcoming_deadlines, attention_needed, quick_stats
    """
    from hr_advisory.shadow.briefing import generate_briefing

    company_id = get_current_company_id(current_user)
    user_role = current_user.get("role", "employee")

    briefing = generate_briefing(company_id, user_role)

    logger.info(
        "Briefing generated for company_id=%s: %d actions, %d deadlines, %d attention items",
        company_id,
        len(briefing.get("pending_actions", [])),
        len(briefing.get("upcoming_deadlines", [])),
        len(briefing.get("attention_needed", [])),
    )

    return {
        **briefing,
        "company_id": company_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/nudges")
async def shadow_nudges(
    page: str = "dashboard",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return contextual nudges for the current page.

    Nudges are page-aware proactive suggestions based on company data
    and regulatory calendar. Maximum 3 nudges per request, sorted by
    urgency.

    Query Parameters:
        page: The current frontend page name (e.g. "dashboard",
              "employees", "payroll", "leave", "claims").

    Returns a list of nudge dicts, each with: id, type, message,
    action_type, route, dismissible, priority.
    """
    from hr_advisory.shadow.nudges import get_nudges

    company_id = get_current_company_id(current_user)
    user_id = str(current_user.get("sub", "anonymous"))
    user_role = current_user.get("role", "employee")

    nudges = get_nudges(company_id, user_id, page, user_role)

    logger.info(
        "Nudges for page=%s, company_id=%s: %d nudges",
        page,
        company_id,
        len(nudges),
    )

    return {
        "nudges": nudges,
        "page": page,
        "company_id": company_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
