# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Briefing Service — morning briefing and dashboard intelligence.

Generates a categorized briefing for the current user based on their
company data. All logic is deterministic (no LLM) — pure DataFlow
queries against leave, payroll, attendance, and employee records.

Categories:
    - pending_actions: items awaiting the user's review/action
    - upcoming_deadlines: regulatory and payroll deadlines within 14 days
    - attention_needed: anomalies, expiring work passes, overdue tasks
    - quick_stats: at-a-glance counts for the dashboard
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "generate_briefing",
]


from hr_advisory.services import dataflow_crud


# ── Briefing category builders ────────────────────────────────


def _pending_actions(company_id: int, user_role: str) -> list[dict[str, Any]]:
    """Find items awaiting the user's attention.

    For admin/hr roles: pending leave requests, draft payroll runs,
    pending claims. For employees: own pending submissions.
    """
    actions: list[dict[str, Any]] = []

    if user_role in ("admin", "hr", "hr_admin", "owner", "manager"):
        # Pending leave applications
        try:
            pending_leave = dataflow_crud.list_records(
                "LeaveApplication",
                {"company_id": company_id, "status": "pending"},
                limit=100,
            )
            if pending_leave:
                actions.append(
                    {
                        "id": "pending-leave",
                        "category": "pending_actions",
                        "title": f"{len(pending_leave)} leave request{'s' if len(pending_leave) != 1 else ''} awaiting approval",
                        "count": len(pending_leave),
                        "action_type": "navigate",
                        "route": "/leave",
                        "priority": "high" if len(pending_leave) >= 5 else "medium",
                    }
                )
        except Exception:
            logger.debug("Failed to query pending leave applications", exc_info=True)

        # Draft payroll runs
        try:
            draft_runs = dataflow_crud.list_records(
                "PayrollRun",
                {"company_id": company_id, "status": "draft"},
                limit=10,
            )
            if draft_runs:
                actions.append(
                    {
                        "id": "draft-payroll",
                        "category": "pending_actions",
                        "title": f"{len(draft_runs)} draft payroll run{'s' if len(draft_runs) != 1 else ''} need processing",
                        "count": len(draft_runs),
                        "action_type": "navigate",
                        "route": "/payroll",
                        "priority": "high",
                    }
                )
        except Exception:
            logger.debug("Failed to query draft payroll runs", exc_info=True)

        # Pending claims
        try:
            pending_claims = dataflow_crud.list_records(
                "Claim",
                {"company_id": company_id, "status": "submitted"},
                limit=100,
            )
            if pending_claims:
                actions.append(
                    {
                        "id": "pending-claims",
                        "category": "pending_actions",
                        "title": f"{len(pending_claims)} claim{'s' if len(pending_claims) != 1 else ''} awaiting review",
                        "count": len(pending_claims),
                        "action_type": "navigate",
                        "route": "/claims",
                        "priority": "medium",
                    }
                )
        except Exception:
            logger.debug("Failed to query pending claims", exc_info=True)

    return actions


def _upcoming_deadlines(company_id: int) -> list[dict[str, Any]]:
    """Compute upcoming regulatory and payroll deadlines.

    Checks:
    - CPF submission (14th of each month)
    - IR8A filing (1 March annually)
    - Foreign worker levy (14th of each month)
    - Payroll processing (based on draft runs with approaching pay dates)
    """
    deadlines: list[dict[str, Any]] = []
    today = date.today()
    horizon = today + timedelta(days=14)

    # ── Static regulatory deadlines ────────────────────────────
    _recurring = [
        {
            "id": "cpf-submission",
            "title": "CPF contribution submission deadline",
            "description": "Monthly CPF contributions due by the 14th of the following month.",
            "day_of_month": 14,
            "month": None,
            "priority": "high",
            "route": "/payroll",
        },
        {
            "id": "ir8a-filing",
            "title": "IR8A filing deadline",
            "description": "Annual IR8A returns to IRAS due by 1 March.",
            "day_of_month": 1,
            "month": 3,
            "priority": "high",
            "route": "/payroll",
        },
        {
            "id": "fw-levy",
            "title": "Foreign worker levy payment",
            "description": "Monthly foreign worker levy due by the 14th of the following month.",
            "day_of_month": 14,
            "month": None,
            "priority": "medium",
            "route": "/payroll",
        },
    ]

    for deadline in _recurring:
        target = _next_occurrence(
            today,
            deadline["day_of_month"],
            deadline.get("month"),
        )
        days_remaining = (target - today).days

        if days_remaining <= 14:
            deadlines.append(
                {
                    "id": deadline["id"],
                    "category": "upcoming_deadlines",
                    "title": deadline["title"],
                    "description": deadline["description"],
                    "days_remaining": days_remaining,
                    "due_date": target.isoformat(),
                    "action_type": "navigate",
                    "route": deadline["route"],
                    "priority": deadline["priority"] if days_remaining <= 3 else "medium",
                }
            )

    return deadlines


def _attention_needed(company_id: int) -> list[dict[str, Any]]:
    """Surface items that need urgent attention.

    Checks:
    - Work pass expiries within 60 days
    - Probation ending within 14 days
    """
    items: list[dict[str, Any]] = []
    today = date.today()

    # ── Work pass expiries ──────────────────────────────────────
    try:
        employees = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id, "is_active": True},
            limit=10000,
        )

        expiring_passes: list[dict] = []
        for emp in employees:
            expiry_str = emp.get("work_pass_expiry", "")
            if not expiry_str:
                continue
            try:
                expiry_date = date.fromisoformat(expiry_str[:10])
            except (ValueError, TypeError):
                continue

            days_until = (expiry_date - today).days
            if 0 <= days_until <= 60:
                name = (
                    emp.get("full_name")
                    or emp.get("designation")
                    or f"Employee #{emp.get('id', '?')}"
                )
                expiring_passes.append(
                    {
                        "name": name,
                        "expiry_date": expiry_str[:10],
                        "days_until": days_until,
                    }
                )

        if expiring_passes:
            expiring_passes.sort(key=lambda x: x["days_until"])
            most_urgent = expiring_passes[0]

            title = (
                f"{len(expiring_passes)} work pass{'es' if len(expiring_passes) != 1 else ''} "
                f"expiring within 60 days"
            )
            description = (
                f"Most urgent: {most_urgent['name']} — expires in {most_urgent['days_until']} day{'s' if most_urgent['days_until'] != 1 else ''} "
                f"({most_urgent['expiry_date']})"
            )
            items.append(
                {
                    "id": "work-pass-expiry",
                    "category": "attention_needed",
                    "title": title,
                    "description": description,
                    "count": len(expiring_passes),
                    "action_type": "navigate",
                    "route": "/employees",
                    "priority": "high" if most_urgent["days_until"] <= 14 else "medium",
                }
            )

    except Exception:
        logger.debug("Failed to query employees for work pass expiries", exc_info=True)

    # ── Probation ending soon ───────────────────────────────────
    try:
        employees = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id, "is_active": True},
            limit=10000,
        )

        ending_probation: list[str] = []
        for emp in employees:
            probation_end = emp.get("probation_end_date", "")
            if not probation_end:
                continue
            try:
                prob_date = date.fromisoformat(probation_end[:10])
            except (ValueError, TypeError):
                continue

            days_until = (prob_date - today).days
            if 0 <= days_until <= 14:
                name = (
                    emp.get("full_name")
                    or emp.get("designation")
                    or f"Employee #{emp.get('id', '?')}"
                )
                ending_probation.append(name)

        if ending_probation:
            items.append(
                {
                    "id": "probation-ending",
                    "category": "attention_needed",
                    "title": f"{len(ending_probation)} employee{'s' if len(ending_probation) != 1 else ''} ending probation soon",
                    "description": f"Employees: {', '.join(ending_probation[:3])}{'...' if len(ending_probation) > 3 else ''}",
                    "count": len(ending_probation),
                    "action_type": "navigate",
                    "route": "/employees",
                    "priority": "medium",
                }
            )

    except Exception:
        logger.debug("Failed to query employees for probation", exc_info=True)

    return items


def _quick_stats(company_id: int) -> dict[str, Any]:
    """Compute at-a-glance stats for the dashboard.

    Returns counts that are useful for a morning overview:
    active employee count, pending leave count, current month payroll status.
    """
    stats: dict[str, Any] = {}

    # Active employee count
    try:
        employees = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id, "is_active": True},
            limit=10000,
        )
        stats["active_employees"] = len(employees)
    except Exception:
        stats["active_employees"] = None
        logger.debug("Failed to query employee count", exc_info=True)

    # Pending leave count
    try:
        pending = dataflow_crud.list_records(
            "LeaveApplication",
            {"company_id": company_id, "status": "pending"},
            limit=10000,
        )
        stats["pending_leave_requests"] = len(pending)
    except Exception:
        stats["pending_leave_requests"] = None
        logger.debug("Failed to query pending leave count", exc_info=True)

    # Current month payroll status
    try:
        today = date.today()
        period_start = today.replace(day=1).isoformat()
        runs = dataflow_crud.list_records(
            "PayrollRun",
            {"company_id": company_id},
            limit=100,
        )
        current_month_runs = [r for r in runs if r.get("period_start", "") >= period_start]
        if current_month_runs:
            latest = current_month_runs[-1]
            stats["payroll_status"] = latest.get("status", "unknown")
        else:
            stats["payroll_status"] = "not_started"
    except Exception:
        stats["payroll_status"] = None
        logger.debug("Failed to query payroll status", exc_info=True)

    return stats


# ── CPF validation ────────────────────────────────────────────


def _cpf_validation(company_id: int) -> list[dict[str, Any]]:
    """Check CPF-related items that need attention.

    Checks:
    - Whether the CPF submission deadline is approaching (within 7 days)
    - Month-over-month payroll variance for CPF contribution anomalies
    """
    items: list[dict[str, Any]] = []
    today = date.today()

    # CPF deadline reminder (14th of each month)
    try:
        day_of_month = 14
        try:
            this_month_deadline = date(today.year, today.month, day_of_month)
        except ValueError:
            this_month_deadline = date(today.year, today.month, 28)

        if today.month == 12:
            next_deadline = date(today.year + 1, 1, day_of_month)
        else:
            try:
                next_deadline = date(today.year, today.month + 1, day_of_month)
            except ValueError:
                next_deadline = date(today.year, today.month + 1, 28)

        target = this_month_deadline if this_month_deadline >= today else next_deadline
        days_left = (target - today).days

        if days_left <= 7:
            items.append(
                {
                    "id": "cpf-deadline-check",
                    "category": "attention_needed",
                    "title": f"CPF submission due in {days_left} day{'s' if days_left != 1 else ''}",
                    "description": "Ensure payroll is processed and CPF contributions are submitted on time. Late payment incurs 18% p.a. interest.",
                    "action_type": "navigate",
                    "route": "/payroll",
                    "priority": "high" if days_left <= 3 else "medium",
                }
            )
    except Exception:
        logger.debug("Failed to compute CPF deadline for briefing", exc_info=True)

    # Month-over-month payroll comparison for CPF anomalies
    try:
        runs = dataflow_crud.list_records(
            "PayrollRun",
            {"company_id": company_id},
            limit=100,
        )
        # Sort by period_start descending to get the two most recent
        sorted_runs = sorted(runs, key=lambda r: r.get("period_start", ""), reverse=True)
        completed_runs = [r for r in sorted_runs if r.get("status") in ("approved", "paid")]

        if len(completed_runs) >= 2:
            current = completed_runs[0]
            previous = completed_runs[1]
            curr_total = float(current.get("total_gross", 0) or 0)
            prev_total = float(previous.get("total_gross", 0) or 0)

            if prev_total > 0:
                variance_pct = abs(curr_total - prev_total) / prev_total * 100
                if variance_pct > 15:
                    direction = "increased" if curr_total > prev_total else "decreased"
                    items.append(
                        {
                            "id": "cpf-variance-check",
                            "category": "attention_needed",
                            "title": f"Payroll {direction} {variance_pct:.0f}% from last month",
                            "description": (
                                f"Total gross went from ${prev_total:,.2f} to ${curr_total:,.2f}. "
                                "Review for accuracy before CPF submission."
                            ),
                            "action_type": "navigate",
                            "route": "/payroll",
                            "priority": "high" if variance_pct > 30 else "medium",
                        }
                    )
    except Exception:
        logger.debug("Failed to compute payroll variance for CPF check", exc_info=True)

    return items


# ── Date helpers ──────────────────────────────────────────────


def _next_occurrence(
    today: date,
    day_of_month: int,
    month: int | None = None,
) -> date:
    """Calculate the next occurrence of a recurring deadline.

    For monthly deadlines (month=None), returns the day_of_month in the
    current or next month. For annual deadlines, returns that month/day
    this year or next year.
    """
    if month is not None:
        try:
            target = date(today.year, month, day_of_month)
        except ValueError:
            target = date(today.year, month, 28)
        if target < today:
            try:
                target = date(today.year + 1, month, day_of_month)
            except ValueError:
                target = date(today.year + 1, month, 28)
        return target

    try:
        target = date(today.year, today.month, day_of_month)
    except ValueError:
        target = date(today.year, today.month, 28)

    if target < today:
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

    return target


# ── Public API ────────────────────────────────────────────────


def generate_briefing(company_id: int, user_role: str) -> dict[str, Any]:
    """Generate a categorized morning briefing for the dashboard.

    Args:
        company_id: The company to generate the briefing for.
        user_role: The user's role (admin, hr, employee, etc.).

    Returns:
        A dict with categorized briefing sections:
            pending_actions: list of items needing user action
            upcoming_deadlines: list of deadlines within 14 days
            attention_needed: list of anomalies/urgent items
            quick_stats: dict of at-a-glance dashboard numbers
    """
    logger.info(
        "Generating briefing for company_id=%s, role=%s",
        company_id,
        user_role,
    )

    pending = _pending_actions(company_id, user_role)
    deadlines = _upcoming_deadlines(company_id)
    attention = _attention_needed(company_id)
    cpf_items = _cpf_validation(company_id)
    # Merge CPF items into attention, avoiding duplicate IDs
    existing_ids = {item.get("id") for item in attention}
    for item in cpf_items:
        if item.get("id") not in existing_ids:
            attention.append(item)
    stats = _quick_stats(company_id)

    # Compute total action count for headline
    total_items = len(pending) + len(attention)

    return {
        "pending_actions": pending,
        "upcoming_deadlines": deadlines,
        "attention_needed": attention,
        "quick_stats": stats,
        "total_action_items": total_items,
        "generated_date": date.today().isoformat(),
    }
