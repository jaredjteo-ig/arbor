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

import json
import logging
import re
from collections import OrderedDict, deque
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.workflows.guardrails import check_rate_limit
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


# ── HRIS data-driven compliance context ──────────────────────


def _build_compliance_context(company_id: int) -> dict[str, Any]:
    """Query real HRIS data to build a compliance context profile.

    Fetches up to 8 data sources via dataflow_crud and returns a dict
    with the company's actual compliance posture. This replaces the
    hardcoded defaults in the shadow context endpoint so compliance
    insights reflect the real state of the company's data.

    Returns:
        A dict with compliance-relevant fields derived from HRIS records.
    """
    from hr_advisory.services import dataflow_crud

    ctx: dict[str, Any] = {
        "company_size": 0,
        "has_foreign_workers": False,
        "sector": "general",
        "has_ket_issued": False,
        "has_written_contracts": False,
        "has_payslip_system": False,
        "has_leave_records": False,
        "has_ot_records": False,
        "has_safety_policy": False,
        "has_grievance_process": False,
        "has_cpf_registered": False,
        "has_fwa_policy": False,
    }

    # 1. Company profile
    try:
        companies = dataflow_crud.list_records(
            "Company", {"id": company_id}, limit=1
        )
        if companies:
            company = companies[0]
            ctx["sector"] = company.get("sector", "general") or "general"
            total_headcount = (
                (company.get("headcount_local", 0) or 0)
                + (company.get("headcount_pr", 0) or 0)
                + (company.get("headcount_ep", 0) or 0)
                + (company.get("headcount_sp", 0) or 0)
                + (company.get("headcount_wp", 0) or 0)
            )
            ctx["company_size"] = total_headcount
            foreign = (
                (company.get("headcount_ep", 0) or 0)
                + (company.get("headcount_sp", 0) or 0)
                + (company.get("headcount_wp", 0) or 0)
            )
            ctx["has_foreign_workers"] = foreign > 0
    except Exception:
        logger.debug("Compliance context: failed to load company profile", exc_info=True)

    # 2. Employee count fallback
    if ctx["company_size"] == 0:
        try:
            employees = dataflow_crud.list_records(
                "Employee", {"company_id": company_id, "is_active": True}, limit=10000
            )
            ctx["company_size"] = len(employees)
        except Exception:
            logger.debug("Compliance context: failed to count employees", exc_info=True)

    # 3. Policies / KET documents
    try:
        policies = dataflow_crud.list_records(
            "CompanyPolicy", {"company_id": company_id}, limit=100
        )
        policy_types = {p.get("policy_type", "").lower() for p in policies}
        ctx["has_safety_policy"] = "wsh" in policy_types or "safety" in policy_types
        ctx["has_grievance_process"] = "grievance" in policy_types
        ctx["has_fwa_policy"] = "fwa" in policy_types or "flexible_work" in policy_types
        ctx["has_written_contracts"] = "employment_contract" in policy_types or "ket" in policy_types
        ctx["has_ket_issued"] = "ket" in policy_types
    except Exception:
        logger.debug("Compliance context: failed to load policies", exc_info=True)

    # 4. Payroll runs (implies payslip system)
    try:
        runs = dataflow_crud.list_records(
            "PayrollRun", {"company_id": company_id}, limit=10
        )
        if runs:
            ctx["has_payslip_system"] = True
            ctx["has_cpf_registered"] = True
    except Exception:
        logger.debug("Compliance context: failed to load payroll runs", exc_info=True)

    # 5. Leave configurations (implies leave records)
    try:
        leave_configs = dataflow_crud.list_records(
            "LeaveTypeConfig", {"company_id": company_id}, limit=10
        )
        ctx["has_leave_records"] = len(leave_configs) > 0
    except Exception:
        logger.debug("Compliance context: failed to load leave configs", exc_info=True)

    # 6. Shift templates (implies OT records tracking)
    try:
        shifts = dataflow_crud.list_records(
            "ShiftTemplate", {"company_id": company_id}, limit=5
        )
        ctx["has_ot_records"] = len(shifts) > 0
    except Exception:
        logger.debug("Compliance context: failed to load shift templates", exc_info=True)

    # 7. Content updates (regulatory awareness)
    try:
        updates = dataflow_crud.list_records(
            "ContentUpdate", {"company_id": company_id}, limit=5
        )
        # Just informational — included in return for transparency
        ctx["recent_content_updates"] = len(updates)
    except Exception:
        ctx["recent_content_updates"] = 0
        logger.debug("Compliance context: failed to load content updates", exc_info=True)

    return ctx


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
    try:
        company_id = get_current_company_id(current_user)
    except Exception:
        company_id = None
    page_domains = _PAGE_DOMAINS.get(page, _PAGE_DOMAINS["dashboard"])

    # Build compliance input from real HRIS data when a company is available,
    # falling back to conservative defaults that surface common gaps.
    if company_id:
        ctx = _build_compliance_context(company_id)
        compliance_input = ComplianceCheckInput(
            company_size=ctx.get("company_size", 10) or 10,
            has_foreign_workers=ctx.get("has_foreign_workers", True),
            sector=ctx.get("sector", "general") or "general",
            has_ket_issued=ctx.get("has_ket_issued", False),
            has_written_contracts=ctx.get("has_written_contracts", False),
            has_payslip_system=ctx.get("has_payslip_system", True),
            has_leave_records=ctx.get("has_leave_records", True),
            has_ot_records=ctx.get("has_ot_records", False),
            has_safety_policy=ctx.get("has_safety_policy", False),
            has_grievance_process=ctx.get("has_grievance_process", False),
            has_cpf_registered=ctx.get("has_cpf_registered", True),
            has_fwa_policy=ctx.get("has_fwa_policy", False),
        )
    else:
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


# ── Shadow payroll validation ────────────────────────────────


@router.get("/payroll/validate")
async def shadow_payroll_validate(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Validate the latest payroll run against common compliance checks.

    Runs 4 checks on the most recent payroll run:
    1. Employee coverage -- are all active employees included?
    2. CPF rate sanity -- are CPF contributions within expected ranges?
    3. Zero-salary detection -- flag employees with zero gross pay
    4. Month-over-month variance -- large swings from the previous run

    Requires owner or hr_manager role.
    """
    from hr_advisory.services import dataflow_crud

    company_id = get_current_company_id(current_user)
    if not company_id:
        raise HTTPException(status_code=400, detail="No company associated with your account.")

    issues: list[dict[str, Any]] = []

    # Fetch the latest payroll run
    try:
        runs = dataflow_crud.list_records(
            "PayrollRun", {"company_id": company_id}, limit=100
        )
    except Exception as exc:
        logger.error("Payroll validate: failed to fetch runs: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load payroll data.") from exc

    if not runs:
        return {
            "valid": True,
            "issues": [],
            "message": "No payroll runs found. Nothing to validate.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    sorted_runs = sorted(runs, key=lambda r: r.get("period_start", ""), reverse=True)
    latest = sorted_runs[0]
    run_id = latest.get("id")

    # Fetch payslips for the latest run
    payslips: list[dict] = []
    try:
        payslips = dataflow_crud.list_records(
            "Payslip", {"payroll_run_id": run_id}, limit=10000
        )
    except Exception:
        logger.debug("Payroll validate: failed to fetch payslips", exc_info=True)

    # Fetch active employees for coverage check
    active_employees: list[dict] = []
    try:
        active_employees = dataflow_crud.list_records(
            "Employee", {"company_id": company_id, "is_active": True}, limit=10000
        )
    except Exception:
        logger.debug("Payroll validate: failed to fetch employees", exc_info=True)

    # Check 1: Employee coverage
    if active_employees and payslips:
        payslip_emp_ids = {p.get("employee_id") for p in payslips}
        active_emp_ids = {e.get("id") for e in active_employees}
        missing = active_emp_ids - payslip_emp_ids
        if missing:
            issues.append({
                "check": "employee_coverage",
                "severity": "high",
                "message": f"{len(missing)} active employee(s) not included in the latest payroll run.",
                "count": len(missing),
            })

    # Check 2: CPF rate sanity (employee CPF should be 5-20% of gross for most workers)
    for slip in payslips:
        gross = float(slip.get("gross_pay", 0) or 0)
        cpf_employee = float(slip.get("cpf_employee", 0) or 0)
        if gross > 0 and cpf_employee > 0:
            rate = cpf_employee / gross * 100
            if rate > 25 or rate < 3:
                emp_id = slip.get("employee_id", "?")
                issues.append({
                    "check": "cpf_rate",
                    "severity": "medium",
                    "message": f"Employee #{emp_id}: CPF rate {rate:.1f}% is outside the normal 5-20% range.",
                    "employee_id": emp_id,
                    "rate": round(rate, 1),
                })

    # Check 3: Zero-salary detection
    zero_salary = [s for s in payslips if float(s.get("gross_pay", 0) or 0) == 0]
    if zero_salary:
        issues.append({
            "check": "zero_salary",
            "severity": "high",
            "message": f"{len(zero_salary)} employee(s) have zero gross pay in the latest run.",
            "count": len(zero_salary),
        })

    # Check 4: Month-over-month variance
    completed = [r for r in sorted_runs if r.get("status") in ("approved", "paid")]
    if len(completed) >= 2:
        curr_total = float(completed[0].get("total_gross", 0) or 0)
        prev_total = float(completed[1].get("total_gross", 0) or 0)
        if prev_total > 0:
            variance_pct = abs(curr_total - prev_total) / prev_total * 100
            if variance_pct > 15:
                direction = "increased" if curr_total > prev_total else "decreased"
                issues.append({
                    "check": "month_variance",
                    "severity": "medium" if variance_pct <= 30 else "high",
                    "message": f"Total gross {direction} {variance_pct:.0f}% from last month (${prev_total:,.2f} to ${curr_total:,.2f}).",
                    "variance_percent": round(variance_pct, 1),
                })

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "payroll_run_id": run_id,
        "period_start": latest.get("period_start", ""),
        "period_end": latest.get("period_end", ""),
        "payslip_count": len(payslips),
        "employee_count": len(active_employees),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Shadow leave team balances ───────────────────────────────


@router.get("/leave/team-balances")
async def shadow_leave_team_balances(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Aggregate leave balances for all employees, with low-balance alerts.

    Returns per-employee leave balance summaries and flags employees
    whose remaining balance is below a configurable threshold.
    Also includes a count of pending approval requests.

    Requires owner or hr_manager role.
    """
    from hr_advisory.services import dataflow_crud

    company_id = get_current_company_id(current_user)
    if not company_id:
        raise HTTPException(status_code=400, detail="No company associated with your account.")

    # Fetch active employees
    try:
        employees = dataflow_crud.list_records(
            "Employee", {"company_id": company_id, "is_active": True}, limit=10000
        )
    except Exception as exc:
        logger.error("Leave team balances: failed to fetch employees: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load employee data.") from exc

    # Fetch leave balances
    balances: list[dict] = []
    try:
        balances = dataflow_crud.list_records(
            "LeaveBalance", {"company_id": company_id}, limit=10000
        )
    except Exception:
        logger.debug("Leave team balances: failed to fetch balances", exc_info=True)

    # Fetch pending leave applications
    pending_count = 0
    try:
        pending = dataflow_crud.list_records(
            "LeaveApplication", {"company_id": company_id, "status": "pending"}, limit=10000
        )
        pending_count = len(pending)
    except Exception:
        logger.debug("Leave team balances: failed to count pending", exc_info=True)

    # Build employee lookup
    emp_lookup = {e.get("id"): e for e in employees}

    # Aggregate balances by employee
    LOW_BALANCE_THRESHOLD = 3  # days
    employee_balances: list[dict[str, Any]] = []
    low_balance_alerts: list[dict[str, Any]] = []

    # Group balances by employee_id
    from collections import defaultdict

    by_employee: dict[int, list[dict]] = defaultdict(list)
    for bal in balances:
        emp_id = bal.get("employee_id")
        if emp_id is not None:
            by_employee[emp_id].append(bal)

    for emp_id, emp_balances in by_employee.items():
        emp = emp_lookup.get(emp_id, {})
        name = emp.get("full_name") or emp.get("designation") or f"Employee #{emp_id}"

        total_entitled = 0.0
        total_used = 0.0
        total_remaining = 0.0
        leave_types: list[dict] = []

        for bal in emp_balances:
            entitled = float(bal.get("entitled_days", 0) or 0)
            used = float(bal.get("used_days", 0) or 0)
            remaining = entitled - used

            total_entitled += entitled
            total_used += used
            total_remaining += remaining

            leave_types.append({
                "leave_type_id": bal.get("leave_type_config_id"),
                "entitled": entitled,
                "used": used,
                "remaining": remaining,
            })

        employee_entry = {
            "employee_id": emp_id,
            "name": name,
            "total_entitled": round(total_entitled, 1),
            "total_used": round(total_used, 1),
            "total_remaining": round(total_remaining, 1),
            "leave_types": leave_types,
        }
        employee_balances.append(employee_entry)

        if total_remaining <= LOW_BALANCE_THRESHOLD and total_entitled > 0:
            low_balance_alerts.append({
                "employee_id": emp_id,
                "name": name,
                "remaining_days": round(total_remaining, 1),
                "message": f"{name} has only {total_remaining:.1f} day(s) of leave remaining.",
            })

    return {
        "employee_balances": employee_balances,
        "low_balance_alerts": low_balance_alerts,
        "pending_approval_count": pending_count,
        "total_employees": len(employees),
        "company_id": company_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
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

# In-memory action history per user (bounded OrderedDict for LRU eviction)
_MAX_HISTORY_PER_USER = 100
_action_history: OrderedDict[str, deque] = OrderedDict()
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
    """Record a completed action in the user's history (bounded, LRU eviction)."""
    if user_id in _action_history:
        # Move to end for LRU ordering
        _action_history.move_to_end(user_id)
    elif len(_action_history) >= _MAX_HISTORY_USERS:
        # Evict least-recently-used user
        _action_history.popitem(last=False)

    if user_id not in _action_history:
        _action_history[user_id] = deque(maxlen=_MAX_HISTORY_PER_USER)
    _action_history[user_id].appendleft(action)


@router.post("/execute")
async def shadow_execute(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Main command entry point for the Shadow Agent.

    Uses the kaizen-agents Delegate to autonomously handle the user's
    request. The LLM reasons about intent, discovers and calls tools,
    and streams a response. This endpoint collects the full response
    and returns a structured JSON matching the ShadowResponse contract.

    Request body:
        message: str — the user's command/question
        page_context: str — current frontend page (default: "dashboard")

    Returns a structured response with Arbor identity.
    """
    from hr_advisory.delegate.arbor_loop import DelegateConfig, create_delegate
    from kaizen_agents.delegate import TextDelta, ToolCallStart, ToolCallEnd, ErrorEvent
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

    # Rate limit — /execute triggers LLM calls
    if not check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    if not message:
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    if len(message) > 2000:
        raise HTTPException(
            status_code=400, detail="Message exceeds maximum length (2000 characters)."
        )

    # Validate page_context against known pages
    _KNOWN_PAGES = {
        "dashboard",
        "employees",
        "payroll",
        "leave",
        "attendance",
        "claims",
        "shifts",
        "appraisals",
        "projects",
        "inventory",
        "recruitment",
        "reports",
        "documents",
        "compliance",
        "settings",
        "calculator",
        "advisory",
        "my-dashboard",
        "my-leave",
        "my-payslips",
        "my-timesheets",
        "my-inventory",
        "my-profile",
        "admin",
        "alerts",
        "emergency",
        "help",
        "analytics",
        "learning",
        "approvals",
        "policies",
        "profile",
    }
    if page_context not in _KNOWN_PAGES:
        page_context = "dashboard"

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

    # ── Step 2: Run the Delegate ──────────────────────────────────
    # The LLM reasons about intent, picks tools, executes, and responds.
    # We inject page context into the prompt so the LLM is aware of where
    # the user is in the app.

    company_id = current_user.get("company_id")
    delegate_config = DelegateConfig(
        jwt_token=jwt_token,
        company_id=int(company_id) if company_id else None,
        user_context={
            "role": current_user.get("role", ""),
            "name": current_user.get("name", ""),
        },
    )

    delegate = create_delegate(delegate_config)

    prompt = message
    if page_context and page_context != "dashboard":
        prompt = f"[User is on the {page_context} page] {message}"

    # Helper: synthesize intent dict from Delegate tool calls for frontend compat
    _WRITE_VERBS = {
        "create",
        "update",
        "delete",
        "approve",
        "reject",
        "terminate",
        "cancel",
        "submit",
        "post",
        "import",
    }
    _DESTRUCTIVE_VERBS = {"delete", "terminate", "cancel"}

    def _synthesize_intent(tool_calls_list: list[dict]) -> dict:
        """Build an intent dict matching ShadowResponse.intent shape."""
        if not tool_calls_list:
            return {
                "module": "advisory",
                "action": "query",
                "trust_level": "autonomous",
                "entities": {},
            }
        primary = tool_calls_list[-1]
        name = primary["name"]
        parts = name.replace("hris_", "").split("_", 1)
        module = parts[0] if parts else "hris"
        action = parts[1] if len(parts) > 1 else name
        is_write = any(v in name.lower() for v in _WRITE_VERBS)
        is_destructive = any(v in name.lower() for v in _DESTRUCTIVE_VERBS)
        if is_destructive:
            trust = "double_confirm"
        elif is_write:
            trust = "always_propose"
        else:
            trust = "autonomous"
        return {"module": module, "action": action, "trust_level": trust, "entities": {}}

    # Collect full response — tool calls and text
    full_text: list[str] = []
    tool_calls: list[dict] = []
    error_msg: str | None = None

    try:
        async for event in delegate.run(prompt):
            if isinstance(event, TextDelta):
                full_text.append(event.text)
            elif isinstance(event, ToolCallStart):
                tool_calls.append({"name": event.name, "call_id": event.call_id})
            elif isinstance(event, ToolCallEnd):
                # Attach result to matching tool call
                for tc in tool_calls:
                    if tc.get("call_id") == event.call_id:
                        tc["result"] = event.result
                        tc["error"] = event.error
                        break
            elif isinstance(event, ErrorEvent):
                error_msg = event.error
    except Exception as exc:
        logger.error("Delegate execution failed: %s", exc, exc_info=True)
        error_msg = "The assistant encountered an error processing your request."

    response_text = "".join(full_text).strip()
    formatter = ArborFormatter()
    now = datetime.now(timezone.utc).isoformat()

    # ── Step 3: Map result to ShadowResponse shape ────────────────
    # The response must match the ShadowResponse TypeScript interface.
    # Frontend expects: result, preview, navigation, advisory,
    # out_of_scope, blocked, attachment_required, error.

    intent = _synthesize_intent(tool_calls)

    # Strip any existing "Arbor:" prefix from LLM output to avoid doubling
    _clean_text = re.sub(r"^Arbor:\s*", "", response_text) if response_text else ""

    def _arbor_msg(text: str, fallback: str = "") -> str:
        return f"Arbor: {text}" if text else f"Arbor: {fallback}"

    if error_msg:
        return {
            "type": "error",
            "message": formatter.format_error(error_msg),
            "success": False,
            "error": error_msg,
            "intent": intent,
            "timestamp": now,
        }

    tool_names_called = [tc["name"] for tc in tool_calls]

    # ── 3a. Navigation detection ─────────────────────────────────
    # If the response suggests navigating to a page, return navigation type
    # so the frontend can router.push() to it.
    _NAV_PAGES = {
        "dashboard": "/dashboard",
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
        "my-dashboard": "/my-dashboard",
        "my-leave": "/my-leave",
        "my-payslips": "/my-payslips",
        "profile": "/profile",
    }
    _lower_msg = message.lower()
    _nav_keywords = ("go to", "navigate to", "open", "show me the", "take me to")
    if any(_lower_msg.startswith(kw) or kw in _lower_msg for kw in _nav_keywords):
        for page_name, route in _NAV_PAGES.items():
            if page_name in _lower_msg:
                return {
                    "type": "navigation",
                    "message": f"Arbor: Taking you to {page_name}.",
                    "route": route,
                    "intent": {
                        "module": "navigation",
                        "action": "navigate",
                        "trust_level": "autonomous",
                        "entities": {"route": route},
                    },
                    "timestamp": now,
                }

    # ── 3b. No tools called → advisory text response ─────────────
    if not tool_names_called:
        return {
            "type": "advisory",
            "message": (
                _arbor_msg(_clean_text)
                if _clean_text
                else formatter.format_advisory_routing(message)
            ),
            "route_to": "/advisory/stream",
            "query": message,
            "intent": intent,
            "timestamp": now,
        }

    # ── 3c. Write operations → PACE preview ──────────────────────
    # If the Delegate called a write tool, create a PACE session so
    # the frontend can show the PaceCard for confirmation.
    _WRITE_VERBS = {
        "create",
        "update",
        "delete",
        "approve",
        "reject",
        "terminate",
        "cancel",
        "submit",
        "post",
        "import",
    }
    _DESTRUCTIVE_VERBS = {"delete", "terminate", "cancel"}

    write_calls = [
        tc for tc in tool_calls if any(verb in tc["name"].lower() for verb in _WRITE_VERBS)
    ]

    if write_calls:
        from hr_advisory.shadow.pace import PaceStep, get_pace_manager
        from hr_advisory.shadow.tool_registry import get_tool_registry as _get_shadow_registry

        primary = write_calls[-1]
        is_destructive = any(v in primary["name"].lower() for v in _DESTRUCTIVE_VERBS)
        trust_level = "double_confirm" if is_destructive else "always_propose"

        # Build PACE steps — resolve REST metadata from the shadow tool registry
        # so /confirm can execute them via ShadowExecutor HTTP calls.
        shadow_registry = _get_shadow_registry()
        steps = []
        for tc in write_calls:
            # Delegate tool names: "hris_employees_create" → module="employees", action="create"
            parts = tc["name"].replace("hris_", "").split("_", 1)
            tc_module = parts[0] if parts else "hris"
            tc_action = parts[1] if len(parts) > 1 else tc["name"]

            resolved = shadow_registry.resolve_tool(tc_module, tc_action)
            if resolved:
                steps.append(
                    PaceStep(
                        description=resolved.description or tc["name"],
                        tool_module=resolved.module,
                        tool_action=resolved.action,
                        method=resolved.method,
                        path=resolved.path,
                        params={},
                    ),
                )
            else:
                steps.append(
                    PaceStep(
                        description=(
                            f"{tc['name']} — {response_text[:100]}" if response_text else tc["name"]
                        ),
                        tool_module=tc_module,
                        tool_action=tc_action,
                        method="POST",
                        path=f"/{tc_module}/{tc_action}",
                        params={},
                    ),
                )

        pace_manager = get_pace_manager()
        _primary_parts = primary["name"].replace("hris_", "").split("_", 1)
        session = pace_manager.create_session(
            user_id=user_id,
            intent_module=_primary_parts[0] if _primary_parts else "hris",
            intent_action=_primary_parts[1] if len(_primary_parts) > 1 else primary["name"],
            confirmation_message=(
                response_text[:200]
                if response_text
                else f"Arbor wants to execute: {primary['name']}"
            ),
            steps=steps,
            trust_level=trust_level,
        )

        preview_message = formatter.format_preview(session.to_dict())

        return {
            "type": "preview",
            "message": preview_message,
            "session_id": session.id,
            "session": session.to_dict(),
            "intent": intent,
            "requires_confirmation": True,
            "requires_double_confirm": is_destructive,
            "timestamp": now,
        }

    # ── 3d. Read operations → immediate result ───────────────────
    primary = tool_calls[-1]
    result_data = None
    if primary.get("result"):
        try:
            result_data = (
                json.loads(primary["result"])
                if isinstance(primary["result"], str)
                else primary["result"]
            )
        except (json.JSONDecodeError, TypeError):
            result_data = {"raw": primary.get("result", "")}

    success = not primary.get("error")

    _record_action(
        user_id,
        {
            "session_id": None,
            "module": primary["name"],
            "action": "delegate",
            "trust_level": "autonomous",
            "success": success,
            "timestamp": now,
            "message": message,
        },
    )

    return {
        "type": "result",
        "message": _arbor_msg(_clean_text, "Here are the results."),
        "data": result_data,
        "success": success,
        "error": primary.get("error") if not success else None,
        "intent": intent,
        "timestamp": now,
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

    if not check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

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

    if session.status not in ("preview", "awaiting_double_confirm"):
        raise HTTPException(
            status_code=409,
            detail=f"Session cannot be confirmed — current status is '{session.status}'.",
        )

    # Two-step confirmation gate for double_confirm sessions
    confirmed_session, ready_to_execute = pace_manager.confirm_session(session_id)
    if confirmed_session is None:
        raise HTTPException(status_code=500, detail="Session confirmation failed.")

    if not ready_to_execute:
        # First confirmation received — need second confirmation
        from hr_advisory.shadow.formatter import ArborFormatter as _AF

        _fmt = _AF()
        return {
            "type": "double_confirm_required",
            "message": _fmt.PREFIX
            + (
                "This is a government/financial action that requires double confirmation. "
                f"Please confirm again: {session.confirmation_message}"
            ),
            "session_id": session_id,
            "session": confirmed_session.to_dict(),
            "confirmed_count": confirmed_session.confirmed_count,
            "requires_double_confirm": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

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

    # Check undo window on PACE sessions (8-second limit)
    from hr_advisory.shadow.pace import get_pace_manager as _get_pm

    _pm = _get_pm()

    # Find the target action
    target_action = None
    if target_session_id:
        for action in history:
            if action.get("session_id") == target_session_id:
                target_action = action
                break
        # Check undo window if the session exists
        if target_action and target_session_id:
            session = _pm.get_session(target_session_id)
            if session and not session.is_undoable():
                return {
                    "type": "undo_expired",
                    "message": formatter.PREFIX
                    + "The undo window (8 seconds) has expired for this action.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
    else:
        # Find the most recent successful write action within undo window
        for action in history:
            if action.get("success") and action.get("trust_level") != "autonomous":
                sid = action.get("session_id")
                if sid:
                    session = _pm.get_session(sid)
                    if session and session.is_undoable():
                        target_action = action
                        break
                else:
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
# SSE Streaming for PACE Execution Progress (Task 3)
# ══════════════════════════════════════════════════════════════
#
# Streams real-time step-by-step progress events during PACE
# session execution via Server-Sent Events (SSE).


async def _generate_sse_events(
    session_id: str,
    jwt_token: str,
    pace_manager: Any | None = None,
    current_user: dict | None = None,
) -> Any:
    """Async generator that yields SSE-formatted events during PACE execution.

    Yields events of three types:
    - step: emitted for each step as it begins execution, with step_index and status
    - complete: emitted once after all steps finish, with full session result
    - error: emitted if the session is not found or cannot be executed

    Each event is formatted as ``data: {json}\\n\\n`` per the SSE specification.

    Args:
        session_id: The PACE session ID to execute and stream.
        jwt_token: The user's JWT for authorization forwarding.
        pace_manager: Optional PaceManager instance (uses singleton if None).
        current_user: The decoded JWT claims for MCP tenant context.

    Yields:
        SSE-formatted strings ready for StreamingResponse.
    """
    import json as _json
    from hr_advisory.shadow.executor import ShadowExecutor
    from hr_advisory.shadow.tool_registry import ToolDefinition

    if pace_manager is None:
        from hr_advisory.shadow.pace import get_pace_manager

        pace_manager = get_pace_manager()

    session = pace_manager.get_session(session_id)
    if session is None:
        yield f"data: {_json.dumps({'event': 'error', 'data': {'message': 'Session not found or expired.'}})}\n\n"
        return

    if session.status not in ("preview", "awaiting_double_confirm"):
        yield f"data: {_json.dumps({'event': 'error', 'data': {'message': f'Session cannot be executed — current status is {session.status!r}.'}})}\n\n"
        return

    # Double-confirm guard
    if session.requires_double_confirm and session.confirmed_count < 2:
        yield f"data: {_json.dumps({'event': 'error', 'data': {'message': 'Session requires double confirmation before execution.'}})}\n\n"
        return

    import time

    executor = ShadowExecutor()
    session.status = "executing"
    all_succeeded = True

    for step_index, step in enumerate(session.steps):
        step.status = "executing"

        tool = ToolDefinition(
            module=step.tool_module,
            action=step.tool_action,
            method=step.method,
            path=step.path,
            params=[],
            trust_level=session.trust_level,
            description=step.description,
            is_mcp=step.method.upper() == "MCP",
        )

        result = await executor.execute(tool, step.params, jwt_token, current_user=current_user)
        session.results.append(result.to_dict())

        if result.success:
            step.status = "done"
        else:
            step.status = "failed"
            all_succeeded = False

        # Emit step event with execution outcome
        yield f"data: {_json.dumps({'event': 'step', 'data': {'step_index': step_index, 'status': step.status, 'description': step.description, 'tool_module': step.tool_module, 'tool_action': step.tool_action, 'success': result.success, 'error': result.error if not result.success else ''}})}\n\n"

        # Stop on write failure
        if not result.success and step.method.upper() != "GET":
            idx = session.steps.index(step)
            for remaining_step in session.steps[idx + 1 :]:
                remaining_step.status = "cancelled"
            break

    session.status = "done" if all_succeeded else "failed"
    session.completed_at = datetime.now(timezone.utc).isoformat()
    session._completed_ts = time.monotonic()

    # Emit complete event
    yield f"data: {_json.dumps({'event': 'complete', 'data': {'session_id': session_id, 'status': session.status, 'results': session.results, 'completed_at': session.completed_at}})}\n\n"


@router.post("/confirm/stream")
async def shadow_confirm_stream(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Confirm and execute a PACE session with real-time SSE progress streaming.

    Streams step-by-step execution progress as Server-Sent Events so the
    frontend can show real-time updates instead of waiting for the full
    batch result.

    Request body:
        session_id: str -- the PACE session ID to confirm and stream

    Returns a StreamingResponse with content type text/event-stream.
    Each event is formatted as ``data: {json}\\n\\n`` with event types:
    - step: progress update for each execution step
    - complete: final result with full session data
    - error: if the session cannot be executed
    """
    from hr_advisory.shadow.pace import get_pace_manager

    body = await request.json()
    session_id = body.get("session_id", "")
    user_id = str(current_user.get("sub", "anonymous"))
    jwt_token = _get_jwt_token(request)

    if not check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

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

    if session.status not in ("preview", "awaiting_double_confirm"):
        raise HTTPException(
            status_code=409,
            detail=f"Session cannot be confirmed — current status is '{session.status}'.",
        )

    # Two-step confirmation gate for double_confirm sessions
    confirmed_session, ready_to_execute = pace_manager.confirm_session(session_id)
    if confirmed_session is None:
        raise HTTPException(status_code=500, detail="Session confirmation failed.")

    if not ready_to_execute:
        raise HTTPException(
            status_code=409,
            detail="This session requires double confirmation. Please confirm again.",
        )

    logger.info(
        "SSE streaming PACE execution: session=%s, user=%s, steps=%d",
        session_id,
        user_id,
        len(session.steps),
    )

    return StreamingResponse(
        _generate_sse_events(session_id, jwt_token, pace_manager, current_user=current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════
# File Upload / Attachment Execution Path (Task 4)
# ══════════════════════════════════════════════════════════════
#
# Handles file uploads for attachment intents detected by the
# intent classifier (bulk_import, document_upload, receipt_upload,
# payroll_import). Routes each file to the appropriate handler.

_SUPPORTED_ATTACHMENT_INTENTS = {
    "bulk_import",
    "document_upload",
    "receipt_upload",
    "payroll_import",
}


async def _route_upload(
    attachment_intent: str,
    file_content: bytes,
    file_name: str,
    content_type: str,
    company_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Route an uploaded file to the appropriate handler based on attachment intent.

    This function contains the core routing logic separated from the endpoint
    so it can be tested independently.

    Args:
        attachment_intent: One of the supported attachment intents.
        file_content: The raw bytes of the uploaded file.
        file_name: The original filename.
        content_type: The MIME type of the file.
        company_id: The authenticated user's company ID.
        user_id: The authenticated user's ID.

    Returns:
        A dict with preview/confirmation data appropriate to the intent.

    Raises:
        ValueError: If the attachment_intent is not supported.
    """
    if attachment_intent not in _SUPPORTED_ATTACHMENT_INTENTS:
        raise ValueError(
            f"Unsupported attachment intent: {attachment_intent!r}. "
            f"Must be one of: {', '.join(sorted(_SUPPORTED_ATTACHMENT_INTENTS))}"
        )

    if attachment_intent == "bulk_import":
        return await _handle_bulk_import(file_content, file_name, company_id)
    elif attachment_intent == "document_upload":
        return _handle_document_upload(file_content, file_name, content_type, company_id, user_id)
    elif attachment_intent == "receipt_upload":
        return _handle_receipt_upload(file_content, file_name, content_type, company_id, user_id)
    elif attachment_intent == "payroll_import":
        return await _handle_payroll_import(file_content, file_name, company_id)

    # Unreachable due to the guard above, but explicit for clarity
    raise ValueError(f"Unsupported attachment intent: {attachment_intent!r}")


async def _handle_bulk_import(
    file_content: bytes,
    file_name: str,
    company_id: int,
) -> dict[str, Any]:
    """Parse and validate a CSV file for bulk employee import.

    Reuses the same parsing logic as the /employees/import/preview endpoint
    but operates on raw bytes instead of a form upload.

    Returns a preview dict with records, totals, and validation errors.
    """
    import csv
    import io

    try:
        text = file_content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        raise ValueError("File must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames:
        reader.fieldnames = [f.strip().lower().replace(" ", "_") for f in reader.fieldnames]

    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    max_rows = 500

    for i, row in enumerate(reader, start=2):
        if i > max_rows + 1:
            errors.append({"row": i, "error": f"CSV exceeds maximum of {max_rows} rows."})
            break

        record: dict[str, Any] = {
            "row": i,
            "name": row.get("name", "").strip(),
            "email": row.get("email", "").strip().lower(),
            "designation": row.get("designation", "").strip(),
            "department": row.get("department", "").strip(),
            "employment_type": row.get("employment_type", "full_time").strip(),
        }

        row_errors: list[str] = []
        if not record["name"]:
            row_errors.append("Name is required.")
        if not record["email"]:
            row_errors.append("Email is required.")
        elif "@" not in record["email"]:
            row_errors.append("Invalid email format.")

        record["errors"] = row_errors
        record["valid"] = len(row_errors) == 0
        records.append(record)
        errors.extend([{"row": i, "error": e} for e in row_errors])

    valid_count = sum(1 for r in records if r["valid"])
    return {
        "action": "bulk_import",
        "records": records,
        "total": len(records),
        "valid": valid_count,
        "invalid": len(records) - valid_count,
        "errors": errors,
        "file_name": file_name,
        "company_id": company_id,
    }


def _handle_document_upload(
    file_content: bytes,
    file_name: str,
    content_type: str,
    company_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Prepare a document upload preview.

    Does NOT save the file yet — returns a confirmation preview so the
    user can approve via the PACE loop before the document is persisted.

    Returns a dict describing what will be uploaded.
    """
    return {
        "action": "document_upload",
        "file_name": file_name,
        "file_size": len(file_content),
        "content_type": content_type,
        "company_id": company_id,
        "uploaded_by": user_id,
        "confirmation_message": f"Upload document '{file_name}' ({len(file_content)} bytes) to company documents?",
    }


def _handle_receipt_upload(
    file_content: bytes,
    file_name: str,
    content_type: str,
    company_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Prepare a receipt upload preview.

    Returns a confirmation preview for attaching a receipt to a claim.
    The actual persistence happens after PACE approval.
    """
    return {
        "action": "receipt_upload",
        "file_name": file_name,
        "file_size": len(file_content),
        "content_type": content_type,
        "company_id": company_id,
        "uploaded_by": user_id,
        "confirmation_message": f"Attach receipt '{file_name}' to your claim?",
    }


async def _handle_payroll_import(
    file_content: bytes,
    file_name: str,
    company_id: int,
) -> dict[str, Any]:
    """Parse and preview a payroll data import file.

    Returns a summary of the rows found in the CSV for user confirmation.
    """
    import csv
    import io

    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("File must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames:
        reader.fieldnames = [f.strip().lower().replace(" ", "_") for f in reader.fieldnames]

    max_rows = 500
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(reader, start=2):
        if i - 1 > max_rows:
            break
        rows.append({"row": i, **{k: v.strip() for k, v in row.items() if v}})

    return {
        "action": "payroll_import",
        "total": len(rows),
        "rows_preview": rows[:10],  # Show first 10 rows as preview
        "file_name": file_name,
        "company_id": company_id,
        "confirmation_message": f"Import payroll data from '{file_name}' ({len(rows)} rows)?",
    }


@router.post("/upload")
async def shadow_upload(
    request: Request,
    file: UploadFile = File(...),
    attachment_intent: str = Form(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Handle file uploads for attachment intents detected by the Shadow Agent.

    Accepts multipart/form-data with a file and an attachment_intent field.
    Routes the file to the appropriate handler based on the intent:
    - bulk_import: CSV/Excel employee import preview
    - document_upload: Company document upload preview
    - receipt_upload: Claim receipt attachment preview
    - payroll_import: Payroll data import preview

    Returns a PACE-style preview of what the import/upload will do,
    so the user can approve before the action is executed.

    Form fields:
        file: The uploaded file (required)
        attachment_intent: One of the supported intent types (required)
    """
    from hr_advisory.shadow.formatter import ArborFormatter

    company_id = get_current_company_id(current_user)
    user_id = int(current_user.get("sub", 0))

    if not check_rate_limit(str(user_id)):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    if attachment_intent not in _SUPPORTED_ATTACHMENT_INTENTS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported attachment_intent: {attachment_intent!r}. "
                f"Must be one of: {', '.join(sorted(_SUPPORTED_ATTACHMENT_INTENTS))}"
            ),
        )

    # Read file content
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_file_size = 10 * 1024 * 1024  # 10MB
    if len(file_content) > max_file_size:
        raise HTTPException(status_code=400, detail="File exceeds 10MB size limit.")

    file_name = re.sub(r"[^\w.\-]", "_", file.filename or "unknown")
    content_type = file.content_type or "application/octet-stream"

    # Content-type validation per attachment intent
    _ALLOWED_CONTENT_TYPES: dict[str, set[str]] = {
        "bulk_import": {
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        "payroll_import": {
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        "document_upload": {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "image/png",
            "image/jpeg",
            "image/jpg",
            "text/plain",
        },
        "receipt_upload": {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/jpg",
        },
    }
    allowed = _ALLOWED_CONTENT_TYPES.get(attachment_intent)
    if allowed and content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported for {attachment_intent}. Accepted: {', '.join(sorted(allowed))}",
        )

    try:
        result = await _route_upload(
            attachment_intent=attachment_intent,
            file_content=file_content,
            file_name=file_name,
            content_type=content_type,
            company_id=company_id,
            user_id=user_id,
        )
    except ValueError as exc:
        logger.warning("Upload processing failed: %s", exc)
        raise HTTPException(status_code=400, detail="The uploaded file could not be processed.")

    formatter = ArborFormatter()
    confirmation_msg = result.get("confirmation_message", "")
    if not confirmation_msg:
        if attachment_intent == "bulk_import":
            valid = result.get("valid", 0)
            total = result.get("total", 0)
            confirmation_msg = f"Import {valid} of {total} employees from CSV?"
        else:
            confirmation_msg = f"Process uploaded file '{file_name}'?"

    logger.info(
        "Shadow upload: intent=%s, file=%s, size=%d, company=%s, user=%s",
        attachment_intent,
        file_name,
        len(file_content),
        company_id,
        user_id,
    )

    return {
        "type": "upload_preview",
        "message": formatter.PREFIX + confirmation_msg,
        "attachment_intent": attachment_intent,
        "preview": result,
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

    import asyncio

    _cid = company_id or 0
    loop = asyncio.get_event_loop()
    briefing = await loop.run_in_executor(None, generate_briefing, _cid, user_role)

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

    import asyncio

    _cid = company_id or 0
    loop = asyncio.get_event_loop()
    nudges = await loop.run_in_executor(None, get_nudges, _cid, user_id, page, user_role)

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


# ══════════════════════════════════════════════════════════════
# Shadow Agent Observation & Memory Layer
# ══════════════════════════════════════════════════════════════
#
# Tracks user session behavior (page views, clicks) and distills
# observations into persistent preferences and patterns.


@router.post("/observe")
async def shadow_observe(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Record a user session observation and return inferred nudges.

    The frontend calls this endpoint on page transitions and significant
    interactions. The observation is stored and immediately analyzed for
    patterns that trigger proactive suggestions.

    Request body:
        page: str -- the current page name (required)
        action_type: str -- the type of action (required, e.g. "page_view", "click")
        details: dict -- optional additional details about the interaction

    Returns:
        recorded: bool -- whether the observation was successfully recorded
        nudges: list[str] -- inferred suggestions based on recent patterns
    """
    from hr_advisory.shadow.observation import get_observation_store

    body = await request.json()
    page = body.get("page", "").strip()
    action_type = body.get("action_type", "").strip()
    details = body.get("details", {})
    user_id = str(current_user.get("sub", "anonymous"))

    if not page:
        raise HTTPException(status_code=400, detail="page is required.")
    if not action_type:
        raise HTTPException(status_code=400, detail="action_type is required.")

    store = get_observation_store()
    store.record_observation(
        user_id=user_id,
        page=page,
        action_type=action_type,
        details=details if isinstance(details, dict) else {},
    )

    # Infer suggestions from the observation pattern
    nudges = store.infer_intent(user_id)

    logger.info(
        "Observation recorded: user=%s, page=%s, action=%s, nudges=%d",
        user_id,
        page,
        action_type,
        len(nudges),
    )

    return {
        "recorded": True,
        "nudges": nudges,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/memory")
async def shadow_memory(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return the user's distilled memory (themes, patterns, preferences).

    The memory is built from accumulated observations and represents
    the user's behavioral profile. If no memory has been distilled yet,
    returns empty defaults.

    Returns:
        themes: list[str] -- high-level behavioral themes
        patterns: list[str] -- detected action sequences
        preferences: dict -- key-value user preferences (top pages, actions)
        last_distilled: str -- ISO 8601 timestamp of last distillation
    """
    from hr_advisory.shadow.memory import get_memory_store

    user_id = str(current_user.get("sub", "anonymous"))
    store = get_memory_store()
    memory = store.get_memory(user_id)

    logger.info(
        "Memory retrieved for user=%s: %d themes, %d patterns",
        user_id,
        len(memory.themes),
        len(memory.patterns),
    )

    return {
        **memory.to_dict(),
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/distill")
async def shadow_distill(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Trigger memory distillation for the current user.

    Reads all recent observations for this user and distills them
    into persistent themes, patterns, and preferences. Call this
    at session end or periodically.

    Returns:
        The distilled UserMemory dict with themes, patterns, preferences.
    """
    from hr_advisory.shadow.observation import get_observation_store
    from hr_advisory.shadow.memory import get_memory_store

    user_id = str(current_user.get("sub", "anonymous"))

    obs_store = get_observation_store()
    observations = obs_store.get_user_observations(user_id, since_hours=168)  # 1 week

    mem_store = get_memory_store()
    memory = mem_store.distill(user_id, observations)

    logger.info(
        "Memory distilled for user=%s: %d themes, %d patterns, %d prefs",
        user_id,
        len(memory.themes),
        len(memory.patterns),
        len(memory.preferences),
    )

    return {
        **memory.to_dict(),
        "user_id": user_id,
        "observations_processed": len(observations),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
