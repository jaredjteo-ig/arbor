"""Probation lifecycle service.

Centralizes the rules around probation_end_date computation and the
on-probation → confirmed auto-transition. Surfaced as a service so the
employee create path, employee update path, manual confirm endpoint,
extend-probation endpoint, AND the daily scheduler all agree on what
'probation end' means.

Red-team finding M5 (workspaces/obayashi/04-validate/
13-redteam-comprehensive-2026-05-19.md): the live walk found Marcus Tan
sitting in confirmation_status="on_probation" 6 weeks past his expected
probation end. Root cause: employee create never wrote
probation_end_date, AND there was no scheduler to flip the status when
the period elapsed. This module fixes both at the source.

Pattern: deterministic compute on create / update; daily idempotent
tick reconciles state. The tick writes an EmploymentEvent +
AuditLogEntry per auto-confirm so the chain stays complete.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


# Default probation period when caller doesn't supply one. Mirrors the
# Employee model default (probation_months: int = 3).
DEFAULT_PROBATION_MONTHS = 3


def compute_probation_end_date(
    start_date: str | None,
    probation_months: int | None,
) -> str:
    """Compute probation_end_date deterministically from start_date.

    Returns an ISO-8601 date string ("YYYY-MM-DD") or "" if the input
    is missing/invalid. Never raises — bad data falls back to empty so
    employee create doesn't fail just because a CSV cell was malformed.

    Examples:
        >>> compute_probation_end_date("2026-01-06", 3)
        '2026-04-06'
        >>> compute_probation_end_date("", 3)
        ''
        >>> compute_probation_end_date("2026-01-31", 1)
        '2026-02-28'
    """
    if not start_date:
        return ""

    months = probation_months if probation_months is not None else DEFAULT_PROBATION_MONTHS
    try:
        months_int = int(months)
    except (TypeError, ValueError):
        months_int = DEFAULT_PROBATION_MONTHS

    if months_int <= 0:
        return ""

    try:
        start = date.fromisoformat(start_date)
    except (TypeError, ValueError):
        return ""

    end = start + relativedelta(months=months_int)
    return end.isoformat()


def ensure_probation_end_date_in_payload(payload: dict) -> dict:
    """Mutate `payload` in place so probation_end_date is set when omitted.

    Called by Employee create paths so every new employee record has a
    deterministic, queryable probation end date. If the caller already
    supplied a non-empty value we leave it alone (manual override wins).
    """
    if payload.get("probation_end_date"):
        return payload

    start = payload.get("start_date")
    months = payload.get("probation_months", DEFAULT_PROBATION_MONTHS)
    computed = compute_probation_end_date(start, months)
    if computed:
        payload["probation_end_date"] = computed
    return payload


def is_probation_elapsed(
    probation_end_date: str | None,
    as_of: Optional[date] = None,
) -> bool:
    """Return True when probation_end_date is on or before `as_of`.

    Empty / malformed dates return False (we cannot decide → stay
    on probation rather than auto-confirm someone we don't have data
    for).
    """
    if not probation_end_date:
        return False
    try:
        end = date.fromisoformat(probation_end_date)
    except (TypeError, ValueError):
        return False
    today = as_of or datetime.now(timezone.utc).date()
    return end <= today


def auto_confirm_due_probations(as_of: Optional[date] = None) -> dict:
    """Flip on_probation → confirmed for every employee whose period has elapsed.

    Idempotent — running this twice on the same day is a no-op for any
    employee already flipped. Designed to be invoked from a daily
    scheduler tick.

    For each flip the function:
        1. Updates Employee.confirmation_status = "confirmed"
        2. Writes an EmploymentEvent (mutable, queryable per-employee)
        3. Appends to AuditLogEntry (immutable chain, tamper-evident)

    Returns a summary dict for observability:
        {"checked": N, "confirmed": M, "errors": [...]}.

    Per pattern P58: a single failed audit append must not abort the
    sweep — we log and continue.
    """
    from hr_advisory.services import audit_log as _audit_log
    from hr_advisory.services import dataflow_crud

    today = as_of or datetime.now(timezone.utc).date()
    iso_today = today.isoformat()

    on_probation = dataflow_crud.list_records(
        "Employee",
        {"confirmation_status": "on_probation", "is_active": True},
        cache_ttl=0,
    )

    summary = {"checked": len(on_probation), "confirmed": 0, "errors": []}

    for emp in on_probation:
        end_date = emp.get("probation_end_date") or ""

        # Backfill any active probationer who's missing probation_end_date.
        # The legacy seed wrote probation_months but never probation_end_date,
        # so this self-heals existing rows on first run.
        if not end_date:
            computed = compute_probation_end_date(
                emp.get("start_date"),
                emp.get("probation_months", DEFAULT_PROBATION_MONTHS),
            )
            if computed:
                try:
                    dataflow_crud.update(
                        "Employee", emp["id"], {"probation_end_date": computed}
                    )
                    end_date = computed
                except Exception as exc:
                    summary["errors"].append(
                        {"employee_id": emp.get("id"), "stage": "backfill", "error": str(exc)}
                    )
                    continue

        if not is_probation_elapsed(end_date, as_of=today):
            continue

        try:
            dataflow_crud.update(
                "Employee", emp["id"], {"confirmation_status": "confirmed"}
            )
        except Exception as exc:
            summary["errors"].append(
                {"employee_id": emp.get("id"), "stage": "update", "error": str(exc)}
            )
            continue

        # EmploymentEvent — mutable, queryable per-employee.
        try:
            dataflow_crud.create(
                "EmploymentEvent",
                {
                    "employee_id": emp["id"],
                    "company_id": emp.get("company_id"),
                    "event_type": "confirmed",
                    "event_date": iso_today,
                    "description": "Auto-confirmed: probation period elapsed",
                    "effective_date": iso_today,
                    "approved_by": 0,  # system actor
                    "notes": f"Probation ended {end_date}",
                },
            )
        except Exception as exc:
            # Log and continue — the immutable AuditLogEntry below is
            # the chain-of-truth.
            logger.warning(
                "EmploymentEvent auto-confirm write failed for employee %s: %s",
                emp.get("id"),
                exc,
            )

        # AuditLogEntry — immutable chain.
        try:
            _audit_log.record_event(
                company_id=int(emp.get("company_id") or 0),
                actor_id=0,
                event_type="employee.auto_confirmed",
                payload={
                    "employee_id": int(emp["id"]),
                    "fields_changed": {
                        "confirmation_status": {
                            "from": "on_probation",
                            "to": "confirmed",
                        }
                    },
                    "probation_end_date": end_date,
                    "reason": "scheduler.auto_confirm_due_probations",
                },
            )
        except Exception as exc:
            logger.warning(
                "AuditLogEntry append failed for auto-confirm employee %s: %s",
                emp.get("id"),
                exc,
            )

        summary["confirmed"] += 1

    if summary["confirmed"] or summary["errors"]:
        logger.info(
            "Probation auto-confirm tick: checked=%s confirmed=%s errors=%s",
            summary["checked"],
            summary["confirmed"],
            len(summary["errors"]),
        )
    return summary
