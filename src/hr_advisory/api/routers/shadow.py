"""Shadow Agent context API — contextual intelligence for the shadow margin.

Provides page-aware compliance insights, regulatory alerts, deadline
reminders, and inline annotations that the shadow agent UI renders
as margin notes and inline risk labels.

All data is deterministic (no LLM calls) — sourced from the compliance
checker, regulatory update pipeline, and KB provision content.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

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
            ud in pd or pd in ud
            for ud in update_domains_lower
            for pd in page_domains_lower
        )

        if not has_overlap and page_domains:
            continue

        days_since = (today - update.effective_date).days
        alerts.append({
            "id": f"update-{update.id}",
            "type": "regulatory_update",
            "title": update.title,
            "description": update.description,
            "source": update.source,
            "urgency": update.urgency.value,
            "effective_date": update.effective_date.isoformat(),
            "days_since_effective": max(0, days_since),
        })

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
            ad in pd or pd in ad
            for ad in alert_domains_lower
            for pd in page_domains_lower
        )
        if not has_overlap and page_domains:
            continue

        urgency = alert.get("urgency", "medium")
        # Only include critical and high urgency alerts in shadow context
        if urgency not in ("critical", "high"):
            continue

        alerts.append({
            "id": alert["id"],
            "type": "regulatory_update",
            "title": alert["title"],
            "description": alert.get("impact_summary", alert["description"]),
            "source": alert.get("source", ""),
            "urgency": urgency,
            "effective_date": alert.get("effective_date", ""),
        })

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
                elif "levy" in deadline_id and any(
                    "foreign" in d for d in page_lower
                ):
                    relevant = True
                # On dashboard, show all deadlines
                elif any("employment" in d for d in page_lower):
                    relevant = True

            if relevant:
                alerts.append({
                    "id": deadline["id"],
                    "type": "deadline",
                    "title": deadline["title"],
                    "description": deadline["description"],
                    "days_remaining": days_remaining,
                })

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

        compliance_annotations.append({
            "element_id": annotation_data["element_id"],
            "text": annotation_data["text"],
            "severity": annotation_data["severity"],
        })

    # Calculator annotations — only on relevant pages
    calculator_annotations: list[dict[str, str]] = []
    if page in ("calculator", "payroll", "dashboard"):
        for ann in _CALCULATOR_ANNOTATIONS:
            calculator_annotations.append({
                "context": ann["context"],
                "text": ann["text"],
            })

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
