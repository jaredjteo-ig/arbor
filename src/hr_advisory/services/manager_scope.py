"""Manager-scope derivation from the org chart.

The product has 3 explicit roles (`owner`, `hr_manager`, `employee`).
Line-manager-ness is NOT a role — it's *derived* from
`Employee.reporting_manager_id`: anyone with ≥1 direct report
implicitly becomes a manager for the purposes of approval queues
and team views.

This keeps the auth system small (no fourth role to plumb through
every `require_role(...)` site, no JWT-claim migration), and
preserves a natural fallback: if HR rearranges the org chart and
Rajesh's reports get reassigned, the manager scope updates without
a role flip.

Used by:
- Team approval endpoints (leave / claims / timesheets) — widen
  the list scope to include team members when the caller has reports.
- /api/team/dashboard — pending approvals, on-leave-today, etc.
- Cross-team-approve guard — refuse manager actions on employees
  outside the caller's report tree.

Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
finding P1-A (line-manager role didn't exist as a workflow).
"""

from __future__ import annotations

import logging
from typing import Any

from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

__all__ = [
    "get_my_employee_id",
    "get_managed_employee_ids",
    "is_manager",
    "is_manager_of",
]


def _company_id_from(current_user: dict[str, Any]) -> int | None:
    """Extract company_id from a JWT-derived user dict.

    Tolerates both shapes the rest of the codebase uses: top-level
    `company_id` (the modern shape) or absent (e.g. platform_admin).
    """
    cid = current_user.get("company_id")
    if cid is None:
        return None
    try:
        return int(cid)
    except (ValueError, TypeError):
        return None


def _user_id_from(current_user: dict[str, Any]) -> int | None:
    """Extract user_id from a JWT-derived user dict.

    The JWT uses `sub` as the subject (string-encoded user id). The
    middleware also stamps `id` on the user dict in some paths.
    """
    raw = current_user.get("sub") or current_user.get("id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def get_my_employee_id(current_user: dict[str, Any]) -> int | None:
    """Resolve the caller's `Employee.id` from their JWT.

    Returns None for owners / hr_managers who don't have a matching
    employee row, or when company context is missing.
    """
    user_id = _user_id_from(current_user)
    company_id = _company_id_from(current_user)
    if user_id is None or company_id is None:
        return None
    rows = dataflow_crud.list_records(
        "Employee",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    if not rows:
        return None
    raw_id = rows[0].get("id")
    if raw_id is None:
        return None
    try:
        return int(raw_id)
    except (ValueError, TypeError):
        return None


def get_managed_employee_ids(current_user: dict[str, Any]) -> set[int]:
    """Return the `Employee.id`s reporting *directly* to the caller.

    Implementation note: direct reports only for v1. Transitive
    (skip-level + below) is deferred — most enterprise needs are
    served by direct-only, and skip-level access is HR_manager's
    job. When this changes, evolve to a recursive CTE on the
    `idx_employee_manager` index rather than chained list calls.

    Returns an empty set for any caller who is not the manager of
    anyone — including owners and HR managers (who use their role,
    not their position in the org chart, to see everyone).
    """
    my_emp_id = get_my_employee_id(current_user)
    if my_emp_id is None:
        return set()
    company_id = _company_id_from(current_user)
    if company_id is None:
        return set()

    reports = dataflow_crud.list_records(
        "Employee",
        {"reporting_manager_id": my_emp_id, "company_id": company_id},
    )
    out: set[int] = set()
    for row in reports:
        raw = row.get("id")
        if raw is None:
            continue
        try:
            out.add(int(raw))
        except (ValueError, TypeError):
            continue
    return out


def is_manager(current_user: dict[str, Any]) -> bool:
    """True if the caller has at least one direct report."""
    return len(get_managed_employee_ids(current_user)) > 0


def is_manager_of(
    current_user: dict[str, Any],
    target_employee_id: int,
) -> bool:
    """True if `target_employee_id` reports directly to the caller.

    Used by team-approval endpoints to reject cross-team actions
    with a 403 before they reach the underlying CRUD.
    """
    return target_employee_id in get_managed_employee_ids(current_user)
