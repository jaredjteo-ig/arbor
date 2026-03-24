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
    with LocalRuntime() as runtime:
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
        # Old pending applications (pending for more than 3 days)
        try:
            pending = _dataflow_list(
                "LeaveApplicationListNode",
                {"company_id": company_id, "status": "pending"},
                limit=100,
            )
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
            logger.debug("Failed to query stale leave requests for nudge", exc_info=True)

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
        return []

    # Sort by priority (lower = more urgent) and cap at max
    nudges.sort(key=lambda n: n.get("priority", 99))
    return nudges[:_MAX_NUDGES]
