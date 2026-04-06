# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Nudge Service — contextual, page-aware proactive suggestions.

Generates up to 3 nudges based on the user's current page, company
state, and regulatory calendar. All logic is deterministic (no LLM).

Nudge types:
    - deadline: upcoming regulatory/payroll deadlines
    - anomaly: unusual patterns (empty payroll, missing records)
    - completion: actions that are partially done
    - regulatory: regulatory changes that affect the current page
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "get_nudges",
]

# Maximum nudges returned per request
_MAX_NUDGES = 3


# ── DataFlow helper ───────────────────────────────────────────


def _dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000) -> list:
    """Execute a DataFlow ListNode query and return the record list."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        node_type,
        "list",
        {"filter": filter_dict, "limit": limit, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    raw = results["list"]
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    if isinstance(raw, list):
        return raw
    return []


# ── Page-specific nudge generators ────────────────────────────


def _nudges_dashboard(company_id: int, user_role: str) -> list[dict[str, Any]]:
    """Nudges for the main dashboard page."""
    nudges: list[dict[str, Any]] = []
    today = date.today()

    # CPF deadline nudge (if within 5 days)
    try:
        day_of_month = 14
        if today.month == 12:
            next_deadline = date(today.year + 1, 1, day_of_month)
        else:
            try:
                next_deadline = date(today.year, today.month + 1, day_of_month)
            except ValueError:
                next_deadline = date(today.year, today.month + 1, 28)
        # Check this month's deadline too
        try:
            this_month_deadline = date(today.year, today.month, day_of_month)
        except ValueError:
            this_month_deadline = date(today.year, today.month, 28)

        target = this_month_deadline if this_month_deadline >= today else next_deadline
        days_left = (target - today).days

        if days_left <= 5:
            nudges.append(
                {
                    "id": "nudge-cpf-deadline",
                    "type": "deadline",
                    "message": f"CPF contributions are due in {days_left} day{'s' if days_left != 1 else ''}. Make sure payroll is processed and submitted.",
                    "action_type": "navigate",
                    "route": "/payroll",
                    "dismissible": True,
                    "priority": 1 if days_left <= 2 else 2,
                }
            )
    except Exception:
        logger.debug("Failed to compute CPF deadline nudge", exc_info=True)

    # Pending leave requests nudge (for admin roles)
    if user_role in ("admin", "hr", "hr_admin", "owner", "manager"):
        try:
            pending = _dataflow_list(
                "LeaveApplicationListNode",
                {"company_id": company_id, "status": "pending"},
                limit=100,
            )
            if len(pending) >= 3:
                nudges.append(
                    {
                        "id": "nudge-pending-leave",
                        "type": "completion",
                        "message": f"{len(pending)} leave requests are waiting for your approval.",
                        "action_type": "navigate",
                        "route": "/leave",
                        "dismissible": True,
                        "priority": 2,
                    }
                )
        except Exception:
            logger.debug("Failed to query pending leave for nudge", exc_info=True)

    return nudges


def _nudges_employees(company_id: int) -> list[dict[str, Any]]:
    """Nudges for the employees page."""
    nudges: list[dict[str, Any]] = []
    today = date.today()

    # Work pass expiry nudge
    try:
        employees = _dataflow_list(
            "EmployeeListNode",
            {"company_id": company_id, "is_active": True},
            limit=10000,
        )

        expiring_count = 0
        for emp in employees:
            expiry_str = emp.get("work_pass_expiry", "")
            if not expiry_str:
                continue
            try:
                expiry_date = date.fromisoformat(expiry_str[:10])
            except (ValueError, TypeError):
                continue
            if 0 <= (expiry_date - today).days <= 30:
                expiring_count += 1

        if expiring_count > 0:
            nudges.append(
                {
                    "id": "nudge-work-pass-expiry",
                    "type": "regulatory",
                    "message": f"{expiring_count} employee{'s have' if expiring_count != 1 else ' has'} work passes expiring within 30 days. Renew early to avoid gaps.",
                    "action_type": "navigate",
                    "route": "/employees",
                    "dismissible": True,
                    "priority": 1,
                }
            )

    except Exception:
        logger.debug("Failed to query work pass expiries for nudge", exc_info=True)

    return nudges


def _nudges_payroll(company_id: int) -> list[dict[str, Any]]:
    """Nudges for the payroll page."""
    nudges: list[dict[str, Any]] = []
    today = date.today()

    # Draft payroll runs that haven't been processed
    try:
        draft_runs = _dataflow_list(
            "PayrollRunListNode",
            {"company_id": company_id, "status": "draft"},
            limit=10,
        )
        if draft_runs:
            nudges.append(
                {
                    "id": "nudge-draft-payroll",
                    "type": "completion",
                    "message": f"You have {len(draft_runs)} draft payroll run{'s' if len(draft_runs) != 1 else ''} that still need to be calculated and approved.",
                    "action_type": "navigate",
                    "route": "/payroll",
                    "dismissible": True,
                    "priority": 1,
                }
            )
    except Exception:
        logger.debug("Failed to query draft payroll runs for nudge", exc_info=True)

    # Payroll not started for current month (after the 20th)
    if today.day >= 20:
        try:
            period_start = today.replace(day=1).isoformat()
            all_runs = _dataflow_list(
                "PayrollRunListNode",
                {"company_id": company_id},
                limit=100,
            )
            current_month_runs = [r for r in all_runs if r.get("period_start", "") >= period_start]
            if not current_month_runs:
                nudges.append(
                    {
                        "id": "nudge-payroll-not-started",
                        "type": "anomaly",
                        "message": "Payroll for this month hasn't been created yet. The CPF deadline is on the 14th of next month.",
                        "action_type": "navigate",
                        "route": "/payroll",
                        "dismissible": True,
                        "priority": 1,
                    }
                )
        except Exception:
            logger.debug("Failed to check current month payroll for nudge", exc_info=True)

    return nudges


def _nudges_leave(company_id: int, user_role: str) -> list[dict[str, Any]]:
    """Nudges for the leave page."""
    nudges: list[dict[str, Any]] = []

    if user_role in ("admin", "hr", "hr_admin", "owner", "manager"):
        try:
            pending = _dataflow_list(
                "LeaveApplicationListNode",
                {"company_id": company_id, "status": "pending"},
                limit=100,
            )

            # Nudge: pending leave approvals for managers
            if pending:
                nudges.append(
                    {
                        "id": "nudge-pending-leave-approvals",
                        "type": "completion",
                        "message": f"You have {len(pending)} leave request{'s' if len(pending) != 1 else ''} awaiting your approval.",
                        "action_type": "navigate",
                        "route": "/leave",
                        "dismissible": True,
                        "priority": 1,
                    }
                )

            # Nudge: stale pending applications (pending for more than 3 days)
            today = date.today()
            stale_count = 0
            for app in pending:
                applied_at = app.get("applied_at", "") or app.get("created_at", "")
                if not applied_at:
                    continue
                try:
                    applied_date = date.fromisoformat(applied_at[:10])
                except (ValueError, TypeError):
                    continue
                if (today - applied_date).days >= 3:
                    stale_count += 1

            if stale_count > 0:
                nudges.append(
                    {
                        "id": "nudge-stale-leave",
                        "type": "completion",
                        "message": f"{stale_count} leave request{'s have' if stale_count != 1 else ' has'} been pending for 3+ days. Timely responses improve team trust.",
                        "action_type": "navigate",
                        "route": "/leave",
                        "dismissible": True,
                        "priority": 1,
                    }
                )
        except Exception:
            logger.debug("Failed to query pending leave requests for nudge", exc_info=True)

    return nudges


def _nudges_claims(company_id: int, user_role: str) -> list[dict[str, Any]]:
    """Nudges for the claims page."""
    nudges: list[dict[str, Any]] = []

    if user_role in ("admin", "hr", "hr_admin", "owner", "manager"):
        try:
            pending_claims = _dataflow_list(
                "ClaimListNode",
                {"company_id": company_id, "status": "submitted"},
                limit=100,
            )
            if pending_claims:
                nudges.append(
                    {
                        "id": "nudge-pending-claims",
                        "type": "completion",
                        "message": f"{len(pending_claims)} submitted claim{'s are' if len(pending_claims) != 1 else ' is'} awaiting your review.",
                        "action_type": "navigate",
                        "route": "/claims",
                        "dismissible": True,
                        "priority": 2,
                    }
                )
        except Exception:
            logger.debug("Failed to query pending claims for nudge", exc_info=True)

    return nudges


# ── Observation-based personalized suggestions ──────────────

# Maps frequently observed action_type or page patterns to
# personalized suggestion nudges. Each entry: (threshold, nudge_factory).
# threshold = minimum number of observations of this pattern in 30 days.

_OBSERVATION_SUGGESTION_RULES: list[dict[str, Any]] = [
    {
        "pattern_field": "page",
        "pattern_value": "payroll",
        "threshold": 3,
        "nudge_factory": lambda company_id: _suggestion_payroll_due(company_id),
    },
    {
        "pattern_field": "page",
        "pattern_value": "leave",
        "threshold": 3,
        "nudge_factory": lambda company_id: _suggestion_pending_leave(company_id),
    },
    {
        "pattern_field": "page",
        "pattern_value": "employees",
        "threshold": 3,
        "nudge_factory": lambda company_id: _suggestion_probation_ending(company_id),
    },
    {
        "pattern_field": "page",
        "pattern_value": "compliance",
        "threshold": 2,
        "nudge_factory": lambda company_id: _suggestion_compliance_score(company_id),
    },
]


def _suggestion_payroll_due(company_id: int) -> dict[str, Any] | None:
    """Suggest payroll run timing based on frequent payroll page views."""
    today = date.today()
    # Calculate days until next CPF deadline (14th of next month)
    if today.month == 12:
        next_deadline = date(today.year + 1, 1, 14)
    else:
        next_deadline = date(today.year, today.month + 1, 14)
    # Check this month's deadline too
    try:
        this_month_deadline = date(today.year, today.month, 14)
    except ValueError:
        this_month_deadline = date(today.year, today.month, 28)
    target = this_month_deadline if this_month_deadline >= today else next_deadline
    days_left = (target - today).days

    return {
        "id": "nudge-personal-payroll-due",
        "type": "personalized",
        "message": f"Your next payroll run is due in {days_left} day{'s' if days_left != 1 else ''} (CPF deadline: {target.isoformat()}).",
        "action_type": "navigate",
        "route": "/payroll",
        "dismissible": True,
        "priority": 2,
    }


def _suggestion_pending_leave(company_id: int) -> dict[str, Any] | None:
    """Suggest pending leave approvals based on frequent leave page views."""
    try:
        pending = _dataflow_list(
            "LeaveApplicationListNode",
            {"company_id": company_id, "status": "pending"},
            limit=100,
        )
        if pending:
            return {
                "id": "nudge-personal-pending-leave",
                "type": "personalized",
                "message": f"You have {len(pending)} pending leave approval{'s' if len(pending) != 1 else ''}.",
                "action_type": "navigate",
                "route": "/leave",
                "dismissible": True,
                "priority": 2,
            }
    except Exception:
        logger.debug("Failed to query pending leave for personalized nudge", exc_info=True)
    return None


def _suggestion_probation_ending(company_id: int) -> dict[str, Any] | None:
    """Suggest probation reviews based on frequent employee page views."""
    today = date.today()
    try:
        employees = _dataflow_list(
            "EmployeeListNode",
            {"company_id": company_id, "is_active": True},
            limit=10000,
        )
        ending_count = 0
        for emp in employees:
            probation_end = emp.get("probation_end_date", "")
            if not probation_end:
                continue
            try:
                prob_date = date.fromisoformat(probation_end[:10])
            except (ValueError, TypeError):
                continue
            if 0 <= (prob_date - today).days <= 30:
                ending_count += 1

        if ending_count > 0:
            return {
                "id": "nudge-personal-probation",
                "type": "personalized",
                "message": f"{ending_count} employee{'s are' if ending_count != 1 else ' is'} in probation ending this month.",
                "action_type": "navigate",
                "route": "/employees",
                "dismissible": True,
                "priority": 3,
            }
    except Exception:
        logger.debug("Failed to query probation for personalized nudge", exc_info=True)
    return None


def _suggestion_compliance_score(company_id: int) -> dict[str, Any] | None:
    """Suggest compliance review based on frequent compliance page views."""
    try:
        from hr_advisory.workflows.compliance_checker import (
            ComplianceCheckInput,
            check_compliance,
        )

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
        gap_count = len([f for f in result.findings if f.severity in ("high", "critical")])
        if gap_count > 0:
            return {
                "id": "nudge-personal-compliance",
                "type": "personalized",
                "message": f"Your compliance score is {result.score}% — {gap_count} item{'s' if gap_count != 1 else ''} need attention.",
                "action_type": "navigate",
                "route": "/compliance",
                "dismissible": True,
                "priority": 3,
            }
    except Exception:
        logger.debug("Failed to compute compliance score for personalized nudge", exc_info=True)
    return None


def _generate_suggestions_from_observations(
    user_id: str,
    company_id: int,
) -> list[dict[str, Any]]:
    """Generate personalized suggestions from recent user observations.

    Reads observations from the last 30 days, groups by action_type and page,
    counts frequency of each, and maps frequent patterns to helpful suggestions
    using a rule-based mapping.

    Args:
        user_id: The user to generate suggestions for.
        company_id: The user's company ID for data queries.

    Returns:
        List of up to 3 personalized nudge dicts.
    """
    from collections import Counter
    from hr_advisory.shadow.observation import get_observation_store

    store = get_observation_store()
    # 30 days = 720 hours
    observations = store.get_user_observations(user_id, since_hours=720)
    if not observations:
        return []

    # Count by page
    page_counts: Counter[str] = Counter()
    for obs in observations:
        page = obs.get("page", "")
        if page:
            page_counts[page] += 1

    suggestions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for rule in _OBSERVATION_SUGGESTION_RULES:
        pattern_field = rule["pattern_field"]
        pattern_value = rule["pattern_value"]
        threshold = rule["threshold"]
        nudge_factory = rule["nudge_factory"]

        count = page_counts.get(pattern_value, 0) if pattern_field == "page" else 0
        if count >= threshold:
            try:
                nudge = nudge_factory(company_id)
                if nudge is not None and nudge["id"] not in seen_ids:
                    suggestions.append(nudge)
                    seen_ids.add(nudge["id"])
            except Exception:
                logger.debug(
                    "Failed to generate personalized suggestion for %s=%s",
                    pattern_field,
                    pattern_value,
                    exc_info=True,
                )

        if len(suggestions) >= 3:
            break

    return suggestions


# ── Page routing table ────────────────────────────────────────

_PAGE_NUDGE_GENERATORS: dict[str, Any] = {
    "dashboard": lambda cid, uid, role: _nudges_dashboard(cid, role),
    "employees": lambda cid, uid, role: _nudges_employees(cid),
    "payroll": lambda cid, uid, role: _nudges_payroll(cid),
    "leave": lambda cid, uid, role: _nudges_leave(cid, role),
    "claims": lambda cid, uid, role: _nudges_claims(cid, role),
}


# ── Public API ────────────────────────────────────────────────


def get_nudges(
    company_id: int,
    user_id: str,
    page_context: str,
    user_role: str = "admin",
) -> list[dict[str, Any]]:
    """Get contextual nudges for the current page.

    Combines page-specific nudges with personalized suggestions derived
    from the user's recent observation patterns (last 30 days).

    Args:
        company_id: The company ID to query data for.
        user_id: The current user's ID (for personalization).
        page_context: The current page name (e.g. "dashboard", "employees").
        user_role: The user's role for role-based nudge filtering.

    Returns:
        A list of up to 3 nudge dicts, sorted by priority (1 = most urgent).
        Each nudge has: id, type, message, action_type, route, dismissible, priority.
    """
    logger.info(
        "Generating nudges for company_id=%s, user=%s, page=%s",
        company_id,
        user_id,
        page_context,
    )

    generator = _PAGE_NUDGE_GENERATORS.get(page_context)
    if generator is None:
        # For pages without specific nudges, fall back to dashboard nudges
        generator = _PAGE_NUDGE_GENERATORS["dashboard"]

    try:
        nudges = generator(company_id, user_id, user_role)
    except Exception:
        logger.warning("Failed to generate nudges for page=%s", page_context, exc_info=True)
        nudges = []

    # Merge personalized suggestions from observation patterns
    try:
        personalized = _generate_suggestions_from_observations(user_id, company_id)
        existing_ids = {n["id"] for n in nudges}
        for suggestion in personalized:
            if suggestion["id"] not in existing_ids:
                nudges.append(suggestion)
    except Exception:
        logger.debug("Failed to generate personalized suggestions", exc_info=True)

    # Sort by priority (lower = more urgent) and cap at max
    nudges.sort(key=lambda n: n.get("priority", 99))
    return nudges[:_MAX_NUDGES]
