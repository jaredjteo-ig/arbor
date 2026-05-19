"""Headcount source-of-truth service.

Red-team finding X1 / C2 (workspaces/obayashi/04-validate/
13-redteam-comprehensive-2026-05-19.md): the live walk turned up
disagreement across four surfaces that all claim to count
"employees": /reports said 29, /strategy/lifecycle said 28,
/employees list said 28, /analytics said 28. Each was running its
own DataFlow query with a slightly different filter — the +1
discrepancy was a row with `is_active=True` AND
`confirmation_status="terminated"`, because the termination path
wasn't writing both fields atomically.

This module centralizes the definition of "active employee" so every
surface routes through one function:

    active ⇔ is_active=True
             AND (end_date IS NULL or end_date == "" or end_date > as_of)
             AND confirmation_status != "terminated"

Future surfaces (compliance check headcount, payroll-eligible count,
report sums) should call this instead of writing their own
list-and-filter logic. When the definition needs to evolve, it
evolves in one place.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


def _is_active_on(emp: dict, as_of: date) -> bool:
    """Apply the canonical 'active employee' predicate to a single row."""
    if not emp.get("is_active"):
        return False
    if (emp.get("confirmation_status") or "") == "terminated":
        return False
    end_date_str = emp.get("end_date") or ""
    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except (TypeError, ValueError):
            # Malformed end_date → treat as still active. We don't want
            # a single bad cell to drop someone from headcount.
            return True
        if end_date <= as_of:
            return False
    return True


def filter_active_employees(
    employees: Iterable[dict],
    as_of: Optional[date] = None,
) -> list[dict]:
    """Filter an existing employee list by the canonical 'active' predicate.

    Use this when you already hold the employee rows (avoids a second
    DB round-trip from list_active_employees). Most callers will use
    list_active_employees below.
    """
    today = as_of or datetime.now(timezone.utc).date()
    return [e for e in employees if _is_active_on(e, today)]


def list_active_employees(
    company_id: int,
    as_of: Optional[date] = None,
    extra_filters: Optional[dict] = None,
) -> list[dict]:
    """List every employee that is active on `as_of` (default: today).

    Always issues `cache_ttl=0` for the underlying DataFlow read so the
    count reflects an in-flight write (termination, hire) without
    staleness.

    `extra_filters` is forwarded to DataFlow (e.g., {"department": "Sales"}).
    """
    from hr_advisory.services import dataflow_crud

    today = as_of or datetime.now(timezone.utc).date()
    filters: dict = {"company_id": company_id}
    if extra_filters:
        filters.update(extra_filters)

    # We pull `is_active=True` first because that's an indexed predicate
    # in most schemas. The `confirmation_status != terminated` and
    # end_date checks happen in Python — small N (28 in the live
    # walk), large N would benefit from a custom DataFlow predicate.
    rows = dataflow_crud.list_records("Employee", filters, cache_ttl=0)
    rows = [r for r in rows if _is_active_on(r, today)]
    return rows


def get_active_employee_count(
    company_id: int,
    as_of: Optional[date] = None,
    extra_filters: Optional[dict] = None,
) -> int:
    """Canonical "how many active employees do we have" function.

    Replaces ad-hoc `len(dataflow_crud.list_records("Employee", {...}))`
    calls scattered across reports / strategy / analytics / compliance.
    """
    return len(list_active_employees(company_id, as_of, extra_filters))
