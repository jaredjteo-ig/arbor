"""Cohort resolution for engagement surveys (T04).

Takes a `filter_spec` JSON shape and returns the list of matching
`employee_id`s. Used by:

- M2 T22 / T23 — saving cohorts and previewing matches.
- M3 T30 — at launch time, the resolver fans out responses to each
  matched employee.
- M3 T34 / T35 — trend and manager-view aggregations resolve cohorts
  for filtering.

Round-3 product revision trimmed the P1 cohort UI to "3 presets +
ad-hoc list" (M4 T43); the resolver itself still supports the full
filter spec because saved cohorts authored in P1 must keep working
when M8 T91 ships the full builder.

Design choice: one Employee.list_records call per company, in-memory
filter. Avoids N+1 and keeps the resolver pure (the only DB read is a
predictable bulk list).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

__all__ = [
    "resolve_cohort",
    "validate_filter_spec",
    "ALLOWED_FILTER_KEYS",
    "P1_PRESET_KEYS",
]

# Full filter spec — supported by the resolver since v1, exposed in UI
# at M8 T91 (full builder). P1 UI restricts to a subset.
ALLOWED_FILTER_KEYS = {
    "all_active",
    "departments",
    "designations_like",
    "pass_types",
    "tenure_min_days",
    "tenure_max_days",
    "manager_ids",
    "ad_hoc_employee_ids",
}

# P1 UI is restricted to these keys (preset + ad-hoc list).
# M2 T22 enforces this at the create-cohort handler.
P1_PRESET_KEYS = {
    "all_active",
    "departments",
    "tenure_max_days",
    "ad_hoc_employee_ids",
}


def validate_filter_spec(
    filter_spec: dict,
    *,
    p1_only: bool = False,
) -> None:
    """Raise ValueError if `filter_spec` is malformed.

    Called from the M2 T22 cohorts CRUD handler. Pass `p1_only=True`
    at P1 to reject multi-dimension combinators that defer to M8 T91.
    """
    if not isinstance(filter_spec, dict):
        raise ValueError("filter_spec must be a JSON object.")

    unknown = set(filter_spec.keys()) - ALLOWED_FILTER_KEYS
    if unknown:
        raise ValueError(
            f"Unknown filter keys: {sorted(unknown)}. "
            f"Allowed: {sorted(ALLOWED_FILTER_KEYS)}"
        )

    if p1_only:
        unknown_at_p1 = set(filter_spec.keys()) - P1_PRESET_KEYS
        if unknown_at_p1:
            raise ValueError(
                "Multi-dimension cohort builder ships at v2. "
                f"P1 supports only {sorted(P1_PRESET_KEYS)}; "
                f"got extra: {sorted(unknown_at_p1)}."
            )

    for int_key in ("tenure_min_days", "tenure_max_days"):
        if int_key in filter_spec and filter_spec[int_key] is not None:
            v = filter_spec[int_key]
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"{int_key} must be a non-negative integer.")

    if (
        filter_spec.get("tenure_min_days") is not None
        and filter_spec.get("tenure_max_days") is not None
    ):
        if filter_spec["tenure_min_days"] > filter_spec["tenure_max_days"]:
            raise ValueError(
                "tenure_min_days must be <= tenure_max_days."
            )

    for list_key in (
        "departments",
        "designations_like",
        "pass_types",
        "manager_ids",
        "ad_hoc_employee_ids",
    ):
        if list_key in filter_spec:
            v = filter_spec[list_key]
            if not isinstance(v, list):
                raise ValueError(f"{list_key} must be a list.")

    for int_list_key in ("manager_ids", "ad_hoc_employee_ids"):
        if int_list_key in filter_spec:
            for entry in filter_spec[int_list_key]:
                if not isinstance(entry, int):
                    raise ValueError(
                        f"{int_list_key} entries must be integers."
                    )


def _parse_iso_date(value: Any) -> date | None:
    """Parse an ISO-8601 date string. Returns None on failure."""
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Accept "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS..."
        try:
            return date.fromisoformat(s.split("T")[0])
        except ValueError:
            return None
    return None


def _tenure_days(employee: dict, *, today: date | None = None) -> int | None:
    """Compute tenure in days from start_date. None if unparseable.

    Note: re-hires keep their original `start_date` in the existing
    schema. M-finding M10 documented this — for tenure purposes, this
    matches "time since first hire". A future schema extension could
    track latest re-hire date if needed.
    """
    start = _parse_iso_date(employee.get("start_date"))
    if start is None:
        return None
    today = today or date.today()
    return (today - start).days


def resolve_cohort(
    company_id: int,
    filter_spec: dict,
    *,
    today: date | None = None,
) -> list[int]:
    """Return a sorted list of unique employee_ids matching the filter.

    Combine semantics:
    - `all_active=True` is shorthand for "all employees with is_active=True"
      and bypasses the dimensional filters.
    - Otherwise, every dimensional filter present narrows the set
      (intersect). Empty list values are ignored (treated as "no filter").
    - `ad_hoc_employee_ids` is UNIONed with the dimensional result so HR
      can scoop in additional employees outside the preset.
    - The final result is intersected with `is_active=True` so terminated
      employees never appear (C1 anonymity invariant).

    Args:
        company_id: target company. The resolver only ever returns
            employees from this company.
        filter_spec: validated filter shape (call validate_filter_spec
            first if you don't trust the source).
        today: override for tests. Defaults to date.today().

    Returns:
        Sorted unique list of int employee_ids.
    """
    validate_filter_spec(filter_spec, p1_only=False)

    employees = dataflow_crud.list_records(
        "Employee",
        {"company_id": int(company_id)},
        cache_ttl=0,
    )
    if not employees:
        return []

    # Pre-compute lookup-by-id for ad_hoc.
    by_id = {int(e["id"]): e for e in employees if e.get("id")}

    # Stage 1 — dimensional match.
    if filter_spec.get("all_active"):
        dimensional = [e for e in employees if e.get("is_active")]
    else:
        dimensional_ids: set[int] = set()
        # Default: start with all active employees of this company.
        # Each dimensional filter intersects.
        candidates = [e for e in employees if e.get("is_active")]
        first_filter = True

        if filter_spec.get("departments"):
            depts = {d.lower() for d in filter_spec["departments"]}
            matched = [
                e for e in candidates
                if (e.get("department") or "").lower() in depts
            ]
            dimensional_ids = (
                set(int(e["id"]) for e in matched if e.get("id"))
                if first_filter
                else dimensional_ids
                & set(int(e["id"]) for e in matched if e.get("id"))
            )
            first_filter = False

        if filter_spec.get("designations_like"):
            patterns = [p.lower() for p in filter_spec["designations_like"]]
            matched = [
                e for e in candidates
                if any(
                    p in (e.get("designation") or "").lower()
                    for p in patterns
                )
            ]
            new_ids = set(int(e["id"]) for e in matched if e.get("id"))
            dimensional_ids = new_ids if first_filter else dimensional_ids & new_ids
            first_filter = False

        if filter_spec.get("pass_types"):
            passes = {p.lower() for p in filter_spec["pass_types"]}
            matched = [
                e for e in candidates
                if (e.get("pass_type") or "").lower() in passes
            ]
            new_ids = set(int(e["id"]) for e in matched if e.get("id"))
            dimensional_ids = new_ids if first_filter else dimensional_ids & new_ids
            first_filter = False

        if filter_spec.get("manager_ids"):
            target_managers = {int(m) for m in filter_spec["manager_ids"]}
            matched = [
                e for e in candidates
                if (e.get("reporting_manager_id") or 0) in target_managers
            ]
            new_ids = set(int(e["id"]) for e in matched if e.get("id"))
            dimensional_ids = new_ids if first_filter else dimensional_ids & new_ids
            first_filter = False

        # Tenure filter — applied after the dimensional intersect.
        if (
            filter_spec.get("tenure_min_days") is not None
            or filter_spec.get("tenure_max_days") is not None
        ):
            tmin = filter_spec.get("tenure_min_days")
            tmax = filter_spec.get("tenure_max_days")
            tenure_match: set[int] = set()
            for e in candidates:
                td = _tenure_days(e, today=today)
                if td is None:
                    continue
                if tmin is not None and td < tmin:
                    continue
                if tmax is not None and td > tmax:
                    continue
                if e.get("id"):
                    tenure_match.add(int(e["id"]))
            dimensional_ids = (
                tenure_match
                if first_filter
                else dimensional_ids & tenure_match
            )
            first_filter = False

        # If no dimensional filter was applied, dimensional_ids is empty.
        # That's correct — without filters, only ad_hoc adds employees.
        # (all_active is the explicit "everyone" path above.)
        dimensional = [
            e for e_id in dimensional_ids if (e := by_id.get(e_id))
        ]

    # Stage 2 — union with ad_hoc.
    result_ids: set[int] = set()
    for e in dimensional:
        if e.get("id") and e.get("is_active"):
            result_ids.add(int(e["id"]))

    for emp_id in filter_spec.get("ad_hoc_employee_ids") or []:
        emp = by_id.get(int(emp_id))
        if emp and emp.get("is_active"):
            result_ids.add(int(emp_id))

    return sorted(result_ids)
