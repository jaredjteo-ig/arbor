"""Strategy hub router — Cox 8-stage Employee Lifecycle dashboard.

Phase 1 P1-1 (obayashi): single consolidated aggregator endpoint that
returns hero counters + per-stage health-pill + D&I snapshot + recent
activity in one round-trip.

Health-pill thresholds are codified here and pinned by regression tests
in tests/regression/test_p1_lifecycle_thresholds.py. See
workspaces/obayashi/02-plans/02-lifecycle-dashboard-spec.md for the
full spec including the 8 stage panels and their KPI maps.

All reads pass cache_ttl=0 for the live counters that the lifecycle
dashboard renders alongside the existing dashboard tile — the round-12
NEW-3 lesson was that snapshot drift between live and cached views
makes the page look broken.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Health-pill thresholds (per spec; pinned by regression tests)
# ---------------------------------------------------------------------------


def _pill_strategy(headcount_actual: int, headcount_target: int) -> str:
    if headcount_target <= 0:
        return "amber"  # No plan set yet
    delta_pct = abs(headcount_actual - headcount_target) / headcount_target
    if delta_pct <= 0.10:
        return "green"
    if delta_pct <= 0.20:
        return "amber"
    return "red"


def _pill_attract(applies_30d: int, sources_30d: int) -> str:
    if applies_30d == 0:
        return "red"
    if sources_30d >= 3:
        return "green"
    return "amber"


def _pill_recruit(active_jobs: int, stale_jobs: int, total_candidates: int) -> str:
    if active_jobs == 0:
        return "amber"
    if stale_jobs == active_jobs or total_candidates == 0:
        return "red"
    if stale_jobs >= 1:
        return "amber"
    return "green"


def _pill_onboard(avg_completion: float, overdue: int) -> str:
    if avg_completion < 0.50 or overdue >= 3:
        return "red"
    if avg_completion < 0.75 or overdue >= 1:
        return "amber"
    return "green"


def _pill_lnd(avg_hours: float, has_data: bool) -> str:
    if not has_data or avg_hours < 5:
        return "red"
    if avg_hours < 10:
        return "amber"
    return "green"


def _pill_reward(payroll_status: str, recognitions_30d: int, headcount: int) -> str:
    if payroll_status == "failed":
        return "red"
    # ≥1 recognition per employee per quarter ≈ headcount/3 per month.
    target = max(1, headcount // 3)
    if payroll_status == "late" or recognitions_30d == 0:
        if recognitions_30d == 0 and payroll_status != "ok":
            return "red"
        return "amber"
    if recognitions_30d < target:
        return "amber"
    return "green"


def _pill_progression(due_total: int, due_completed: int) -> str:
    if due_total == 0:
        return "amber"
    rate = due_completed / due_total
    if rate < 0.50:
        return "red"
    if rate < 0.80:
        return "amber"
    return "green"


def _pill_retain(churn_yoy_delta_ppt: float) -> str:
    if churn_yoy_delta_ppt > 3.0:
        return "red"
    if churn_yoy_delta_ppt > 1.0:
        return "amber"
    return "green"


# ---------------------------------------------------------------------------
# Aggregator — single endpoint, no N+1
# ---------------------------------------------------------------------------


def _safe_get(records: list[dict], **filters) -> list[dict]:
    """Filter a list of records by all key=value pairs in filters."""
    out = []
    for r in records:
        if all(r.get(k) == v for k, v in filters.items()):
            out.append(r)
    return out


def _events_for_company(company_id: int) -> list[dict]:
    return dataflow_crud.list_records(
        "EmploymentEvent", {"company_id": company_id}, cache_ttl=0
    )


def _employees_for_company(company_id: int) -> list[dict]:
    return dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "is_active": True},
        cache_ttl=0,
    )


def _safe_list(model: str, filter_dict: dict) -> list[dict]:
    """List records from a DataFlow model. Returns [] if the model
    isn't registered (Phase 2 models like TrainingRecord, Recognition,
    Goal, ExitInterview land later — the dashboard must still render).
    """
    try:
        return dataflow_crud.list_records(model, filter_dict, cache_ttl=0)
    except ValueError as exc:
        if "not found" in str(exc).lower() or "not registered" in str(exc).lower():
            return []
        raise


def _all_employees_including_terminated(company_id: int) -> list[dict]:
    """For churn calculation — needs both active and inactive rows."""
    return dataflow_crud.list_records(
        "Employee", {"company_id": company_id}, cache_ttl=0
    )


def _company(company_id: int) -> dict:
    row = dataflow_crud.read("Company", company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Company not found.")
    return row


def _hero(company_id: int, employees: list[dict], jobs: list[dict]) -> dict:
    """Workforce strategy summary band."""
    headcount_actual = len(employees)
    company = _company(company_id)
    target = (
        (company.get("headcount_local") or 0)
        + (company.get("headcount_pr") or 0)
        + (company.get("headcount_ep") or 0)
        + (company.get("headcount_sp") or 0)
        + (company.get("headcount_wp") or 0)
    )
    if target == 0:
        target = headcount_actual  # No plan; default to actual

    open_jobs_list = [j for j in jobs if j.get("status") in ("open", "published")]
    stale_threshold = (datetime.utcnow() - timedelta(days=14)).isoformat()
    stale_jobs = [
        j
        for j in open_jobs_list
        if (j.get("created_at") or "") < stale_threshold
    ]

    today = date.today()
    year_start = date(today.year, 1, 1).isoformat()
    last_year_start = date(today.year - 1, 1, 1).isoformat()
    last_year_end = date(today.year - 1, 12, 31).isoformat()

    events = _events_for_company(company_id)
    exits_ytd = [
        e
        for e in events
        if e.get("event_type") in ("RESIGNED", "TERMINATED", "RETRENCHED")
        and (e.get("created_at") or "") >= year_start
    ]
    exits_last_year = [
        e
        for e in events
        if e.get("event_type") in ("RESIGNED", "TERMINATED", "RETRENCHED")
        and last_year_start <= (e.get("created_at") or "") <= last_year_end
    ]
    churn_ytd_pct = (
        (len(exits_ytd) / max(1, headcount_actual)) * 100.0
        if headcount_actual > 0
        else 0.0
    )
    churn_yoy_delta = churn_ytd_pct - (
        (len(exits_last_year) / max(1, headcount_actual)) * 100.0
        if headcount_actual > 0
        else 0.0
    )

    return {
        "headcount_actual": headcount_actual,
        "headcount_target": target,
        "open_jobs": len(open_jobs_list),
        "stale_jobs": len(stale_jobs),
        "critical_roles_at_risk": 0,  # Phase 3: SuccessionPlan
        "churn_ytd_pct": round(churn_ytd_pct, 1),
        "churn_yoy_delta": round(churn_yoy_delta, 1),
    }


def _stages(  # noqa: PLR0915 — 8 stages each ~5 lines is intentional
    company_id: int, employees: list[dict], jobs: list[dict]
) -> dict:
    """Per-stage health-pill + headline KPI."""
    today = date.today()
    today_iso = today.isoformat()
    cutoff_30d = (today - timedelta(days=30)).isoformat()
    headcount = len(employees)

    # ─ Strategy ─────────────────────────────────────────────────────
    company = _company(company_id)
    target = (
        (company.get("headcount_local") or 0)
        + (company.get("headcount_pr") or 0)
        + (company.get("headcount_ep") or 0)
        + (company.get("headcount_sp") or 0)
        + (company.get("headcount_wp") or 0)
    ) or headcount
    delta = headcount - target
    strategy = {
        "health": _pill_strategy(headcount, target),
        "kpi": {"delta": delta, "target": target, "actual": headcount},
    }

    # ─ Attract ──────────────────────────────────────────────────────
    candidates = dataflow_crud.list_records(
        "Candidate", {"company_id": company_id}, cache_ttl=0
    )
    applies_30d_list = [
        c for c in candidates if (c.get("created_at") or "") >= cutoff_30d
    ]
    sources_30d = len(
        {c.get("source") for c in applies_30d_list if c.get("source")}
    )
    attract = {
        "health": _pill_attract(len(applies_30d_list), sources_30d),
        "kpi": {"applies_30d": len(applies_30d_list), "sources": sources_30d},
    }

    # ─ Recruit ──────────────────────────────────────────────────────
    open_jobs_list = [j for j in jobs if j.get("status") in ("open", "published")]
    stale_threshold = (datetime.utcnow() - timedelta(days=14)).isoformat()
    stale_count = sum(
        1
        for j in open_jobs_list
        if (j.get("created_at") or "") < stale_threshold
    )
    recruit = {
        "health": _pill_recruit(
            len(open_jobs_list), stale_count, len(candidates)
        ),
        "kpi": {
            "active_jobs": len(open_jobs_list),
            "stale": stale_count,
            "candidates": len(candidates),
        },
    }

    # ─ Onboard ──────────────────────────────────────────────────────
    assignments = dataflow_crud.list_records(
        "OnboardingAssignment", {"company_id": company_id}, cache_ttl=0
    )
    active_assignments = [
        a for a in assignments if a.get("status") in ("in_progress", "overdue")
    ]
    if active_assignments:
        avg_completion = sum(
            (a.get("completion_pct") or 0) for a in active_assignments
        ) / max(1, len(active_assignments))
        avg_completion = avg_completion / 100.0  # Stored 0–100; convert to 0–1
    else:
        avg_completion = 1.0  # No active assignments == nothing overdue
    overdue = sum(1 for a in assignments if a.get("status") == "overdue")
    onboard = {
        "health": _pill_onboard(avg_completion, overdue),
        "kpi": {
            "avg_completion": round(avg_completion, 2),
            "overdue": overdue,
            "active": len(active_assignments),
        },
    }

    # ─ L&D (Phase 1: signal-only — TrainingRecord lands in P2-LD) ──
    training_records = _safe_list("TrainingRecord", {"company_id": company_id})
    has_lnd_data = bool(training_records)
    if has_lnd_data and headcount > 0:
        total_hours = sum(
            (r.get("hours") or 0) for r in training_records
        )
        avg_hours = total_hours / headcount
    else:
        avg_hours = 0.0
    lnd = {
        "health": _pill_lnd(avg_hours, has_lnd_data),
        "kpi": {
            "avg_hours_per_employee": round(avg_hours, 1),
            "data_missing": not has_lnd_data,
            "records": len(training_records),
        },
    }

    # ─ Reward ───────────────────────────────────────────────────────
    payroll_runs = dataflow_crud.list_records(
        "PayrollRun", {"company_id": company_id}, cache_ttl=0
    )
    paid_runs = sorted(
        [r for r in payroll_runs if r.get("status") == "paid"],
        key=lambda r: r.get("period_end") or "",
        reverse=True,
    )
    last_paid = paid_runs[0] if paid_runs else None
    payroll_status = "ok" if last_paid else "failed"
    if last_paid:
        # "Late" if more than 35 days have elapsed since the period end.
        try:
            period_end = date.fromisoformat(last_paid.get("period_end"))
            if (today - period_end).days > 35:
                payroll_status = "late"
        except (ValueError, TypeError):
            pass
    recognitions = _safe_list("Recognition", {"company_id": company_id})
    recognitions_30d = [
        r for r in recognitions if (r.get("created_at") or "") >= cutoff_30d
    ]
    reward = {
        "health": _pill_reward(payroll_status, len(recognitions_30d), headcount),
        "kpi": {
            "last_payroll": payroll_status,
            "recognitions_30d": len(recognitions_30d),
            "last_payroll_period_end": (
                last_paid.get("period_end") if last_paid else None
            ),
        },
    }

    # ─ Progression ──────────────────────────────────────────────────
    appraisals = dataflow_crud.list_records(
        "Appraisal", {"company_id": company_id}, cache_ttl=0
    )
    in_flight = [a for a in appraisals if a.get("status") in ("draft", "submitted")]
    completed = [a for a in appraisals if a.get("status") == "signed_off"]
    due_total = len(in_flight) + len(completed)
    progression = {
        "health": _pill_progression(due_total, len(completed)),
        "kpi": {
            "due_reviews": len(in_flight),
            "completed": len(completed),
            "in_flight": len(in_flight),
        },
    }

    # ─ Retain ───────────────────────────────────────────────────────
    events = _events_for_company(company_id)
    year_start = date(today.year, 1, 1).isoformat()
    last_year_start = date(today.year - 1, 1, 1).isoformat()
    last_year_end = date(today.year - 1, 12, 31).isoformat()
    exit_types = ("RESIGNED", "TERMINATED", "RETRENCHED")
    exits_ytd = [
        e
        for e in events
        if e.get("event_type") in exit_types
        and (e.get("created_at") or "") >= year_start
    ]
    exits_last_year = [
        e
        for e in events
        if e.get("event_type") in exit_types
        and last_year_start <= (e.get("created_at") or "") <= last_year_end
    ]
    churn_ytd_pct = (
        (len(exits_ytd) / max(1, headcount)) * 100.0
        if headcount > 0
        else 0.0
    )
    churn_last_year_pct = (
        (len(exits_last_year) / max(1, headcount)) * 100.0
        if headcount > 0
        else 0.0
    )
    yoy_delta_ppt = churn_ytd_pct - churn_last_year_pct
    retain = {
        "health": _pill_retain(yoy_delta_ppt),
        "kpi": {
            "churn_ytd": round(churn_ytd_pct, 1),
            "yoy_delta_ppt": round(yoy_delta_ppt, 1),
            "exits_ytd": len(exits_ytd),
        },
    }

    return {
        "strategy": strategy,
        "attract": attract,
        "recruit": recruit,
        "onboard": onboard,
        "lnd": lnd,
        "reward": reward,
        "progression": progression,
        "retain": retain,
    }


def _di_snapshot(company_id: int, employees: list[dict]) -> dict:
    """D&I cross-cutting tile — derived from existing fields only."""
    if not employees:
        return {
            "composition": {},
            "completeness": {},
            "headline": "Add your first employees to populate this view.",
        }

    def _bucket(field: str, default: str = "Not reported") -> dict[str, int]:
        out: dict[str, int] = {}
        for emp in employees:
            raw = (emp.get(field) or "").strip()
            key = raw if raw else default
            out[key] = out.get(key, 0) + 1
        return out

    gender = _bucket("gender")
    pass_type = {}
    for emp in employees:
        raw = (emp.get("pass_type") or "").strip().lower()
        key = raw or "citizen"
        pass_type[key] = pass_type.get(key, 0) + 1

    completeness = {
        "gender": sum(1 for e in employees if (e.get("gender") or "").strip())
        / len(employees),
        "pass_type": sum(
            1 for e in employees if (e.get("pass_type") or "").strip()
        )
        / len(employees),
        "date_of_birth": sum(
            1 for e in employees if (e.get("date_of_birth") or "").strip()
        )
        / len(employees),
        "nationality": sum(
            1 for e in employees if (e.get("nationality") or "").strip()
        )
        / len(employees),
    }

    return {
        "composition": {"gender": gender, "pass_type": pass_type},
        "completeness": {
            k: round(v, 2) for k, v in completeness.items()
        },
        "headline": (
            f"{len(employees)} employees · "
            f"{round(completeness['gender'] * 100)}% gender complete · "
            f"{round(completeness['pass_type'] * 100)}% pass-type complete"
        ),
    }


def _activity(company_id: int, employees: list[dict]) -> list[dict]:
    """Recent cross-stage activity — last 14 days, capped at 20."""
    cutoff = (datetime.utcnow() - timedelta(days=14)).isoformat()
    employees_by_id = {e.get("id"): e for e in employees}

    feed: list[dict] = []

    # EmploymentEvent — hire / promotion / exit
    events = _events_for_company(company_id)
    for ev in events:
        if (ev.get("created_at") or "") < cutoff:
            continue
        emp = employees_by_id.get(ev.get("employee_id"))
        emp_name = emp.get("user_id") if emp else "Unknown"
        feed.append(
            {
                "stage": "strategy",
                "kind": ev.get("event_type", "EVENT"),
                "ts": ev.get("created_at"),
                "summary": f"{ev.get('event_type', 'Event')} — employee #{ev.get('employee_id')}",
            }
        )

    # InterviewSchedule — recruit
    interviews = dataflow_crud.list_records(
        "InterviewSchedule", {"company_id": company_id}, cache_ttl=0
    )
    for iv in interviews:
        if (iv.get("created_at") or "") < cutoff:
            continue
        feed.append(
            {
                "stage": "recruit",
                "kind": "INTERVIEW",
                "ts": iv.get("created_at"),
                "summary": f"Interview {iv.get('status')} for candidate #{iv.get('candidate_id')}",
            }
        )

    # OnboardingStepProgress — onboard
    progresses = dataflow_crud.list_records(
        "OnboardingStepProgress", {}, cache_ttl=0
    )
    for p in progresses:
        if (p.get("completed_at") or "") < cutoff:
            continue
        if p.get("status") != "completed":
            continue
        feed.append(
            {
                "stage": "onboard",
                "kind": "STEP_COMPLETE",
                "ts": p.get("completed_at"),
                "summary": f"Onboarding step completed for assignment #{p.get('assignment_id')}",
            }
        )

    # Appraisal — progression
    appraisals = dataflow_crud.list_records(
        "Appraisal", {"company_id": company_id}, cache_ttl=0
    )
    for ap in appraisals:
        ts = ap.get("submitted_at") or ap.get("signed_off_at") or ap.get("updated_at")
        if not ts or ts < cutoff:
            continue
        feed.append(
            {
                "stage": "progression",
                "kind": "APPRAISAL",
                "ts": ts,
                "summary": f"Appraisal {ap.get('status')} for employee #{ap.get('employee_id')}",
            }
        )

    # Sort desc by timestamp, cap at 20
    feed.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return feed[:20]


@router.get("/lifecycle-dashboard")
async def lifecycle_dashboard(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Cox 8-stage lifecycle aggregator — single round-trip.

    Returns hero counters + per-stage health-pill + D&I snapshot +
    recent activity in one payload. All reads bypass list cache so the
    dashboard never lags behind the underlying tiles.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    employees = _employees_for_company(company_id)
    jobs = dataflow_crud.list_records(
        "JobListing", {"company_id": company_id}, cache_ttl=0
    )

    return {
        "company_id": company_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hero": _hero(company_id, employees, jobs),
        "stages": _stages(company_id, employees, jobs),
        "di_snapshot": _di_snapshot(company_id, employees),
        "activity": _activity(company_id, employees),
    }


# ---------------------------------------------------------------------------
# P1-9 — onboarding tour dismissal flag
# ---------------------------------------------------------------------------


@router.post("/lifecycle-tour/dismiss")
async def dismiss_lifecycle_tour(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Mark the lifecycle-tour pop-over as dismissed for this company.

    Persists `seen_lifecycle_tour=true` into the Company.feature_flags
    JSON map so the next render skips the pop-over.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    company = dataflow_crud.read("Company", company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    flags_raw = company.get("feature_flags")
    if isinstance(flags_raw, str):
        try:
            flags = json.loads(flags_raw) if flags_raw else {}
        except json.JSONDecodeError:
            flags = {}
    elif isinstance(flags_raw, dict):
        flags = dict(flags_raw)
    else:
        flags = {}

    flags["seen_lifecycle_tour"] = True
    dataflow_crud.update(
        "Company", company_id, {"feature_flags": json.dumps(flags)}
    )
    return {"ok": True, "feature_flags": flags}
