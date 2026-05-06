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
    stale_threshold = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14)).isoformat()
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
        if (e.get("event_type") or "").upper() in ("RESIGNED", "TERMINATED", "RETRENCHED", "RETIRED")
        and (e.get("created_at") or "") >= year_start
    ]
    exits_last_year = [
        e
        for e in events
        if (e.get("event_type") or "").upper() in ("RESIGNED", "TERMINATED", "RETRENCHED", "RETIRED")
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
    stale_threshold = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14)).isoformat()
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
    # Round-2 redteam H5: include Goals/OKR signal — appraisals alone
    # are once-a-year; goals are the in-cycle data this stage needs.
    goals = _safe_list("Goal", {"company_id": company_id})
    goals_active = sum(
        1 for g in goals if g.get("status") in ("active", "at_risk")
    )
    goals_at_risk = sum(1 for g in goals if g.get("status") == "at_risk")
    progression = {
        "health": _pill_progression(due_total, len(completed)),
        "kpi": {
            "due_reviews": len(in_flight),
            "completed": len(completed),
            "in_flight": len(in_flight),
            "active_goals": goals_active,
            "at_risk_goals": goals_at_risk,
        },
    }

    # ─ Retain ───────────────────────────────────────────────────────
    events = _events_for_company(company_id)
    year_start = date(today.year, 1, 1).isoformat()
    last_year_start = date(today.year - 1, 1, 1).isoformat()
    last_year_end = date(today.year - 1, 12, 31).isoformat()
    exit_types = ("RESIGNED", "TERMINATED", "RETRENCHED", "RETIRED")
    exits_ytd = [
        e
        for e in events
        if (e.get("event_type") or "").upper() in exit_types
        and (e.get("created_at") or "") >= year_start
    ]
    exits_last_year = [
        e
        for e in events
        if (e.get("event_type") or "").upper() in exit_types
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
    # Round-2 redteam H4: include ExitInterview signal so the panel
    # doesn't read churn=0 while showing 2 completed exit interviews.
    exit_interviews_all = _safe_list("ExitInterview", {"company_id": company_id})
    submitted_interviews = [
        ei for ei in exit_interviews_all if ei.get("submitted_at")
    ]
    response_rate = (
        len(submitted_interviews) / len(exit_interviews_all)
        if exit_interviews_all
        else 0.0
    )
    retain = {
        "health": _pill_retain(yoy_delta_ppt),
        "kpi": {
            "churn_ytd": round(churn_ytd_pct, 1),
            "yoy_delta_ppt": round(yoy_delta_ppt, 1),
            "exits_ytd": len(exits_ytd),
            "exit_interviews_total": len(exit_interviews_all),
            "exit_response_rate": round(response_rate, 2),
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
    """Recent cross-stage activity — last 14 days, capped at 20.

    Round-2 redteam L finding: humanize summaries — resolve internal IDs
    (employee_id, candidate_id, assignment_id) to human-readable names.
    Buyers shouldn't see "assignment #3" or "employee #2".
    """
    cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14)).isoformat()
    employees_by_id = {e.get("id"): e for e in employees}

    # Resolve user_id → user.name once for every employee referenced in
    # the feed. Cheap because Employee count is small.
    user_ids = {e.get("user_id") for e in employees if e.get("user_id")}
    users = dataflow_crud.list_records(
        "User", {"company_id": company_id}, cache_ttl=0
    ) if user_ids else []
    user_name_by_id: dict[int, str] = {
        u.get("id"): (u.get("name") or u.get("email") or f"#{u.get('id')}")
        for u in users
    }

    def _emp_name(emp_id: int | None) -> str:
        emp = employees_by_id.get(emp_id) if emp_id else None
        if not emp:
            return f"employee #{emp_id}" if emp_id else "an employee"
        name = user_name_by_id.get(emp.get("user_id"))
        if name:
            return name
        return emp.get("designation") or f"employee #{emp_id}"

    candidates = dataflow_crud.list_records(
        "Candidate", {"company_id": company_id}, cache_ttl=0
    )
    candidate_name_by_id: dict[int, str] = {
        c.get("id"): (c.get("name") or f"candidate #{c.get('id')}")
        for c in candidates
        if c.get("id")
    }

    onboarding_assignments = dataflow_crud.list_records(
        "OnboardingAssignment",
        {"company_id": company_id},
        cache_ttl=0,
    )
    assignment_emp_id: dict[int, int] = {
        a.get("id"): a.get("employee_id")
        for a in onboarding_assignments
        if a.get("id")
    }

    feed: list[dict] = []

    # Map raw kudos category enums to buyer-facing labels. Snake-case
    # technical values like "above_and_beyond" or "customer" leak into
    # the feed verbatim otherwise.
    KUDOS_LABEL = {
        "teamwork": "Teamwork",
        "values": "Values",
        "customer": "Customer",
        "innovation": "Innovation",
        "above_and_beyond": "Above and beyond",
        "growth": "Growth",
        "leadership": "Leadership",
        "delivery": "Delivery",
    }

    def _kudos_label(raw: str | None) -> str:
        if not raw:
            return "recognition"
        return KUDOS_LABEL.get(raw, raw.replace("_", " ").capitalize())

    # Map raw EmploymentEvent type → buyer-facing verb.
    EVENT_VERB = {
        "HIRED": "Hired",
        "PROMOTED": "Promoted",
        "RESIGNED": "Resigned",
        "RETIRED": "Retired",
        "TERMINATED": "Terminated",
        "RETRENCHED": "Retrenched",
        "SALARY_REVISION": "Salary revised",
        "TRANSFERRED": "Transferred",
        "CONFIRMED": "Confirmation",
    }

    # EmploymentEvent — hire / promotion / exit
    events = _events_for_company(company_id)
    for ev in events:
        if (ev.get("created_at") or "") < cutoff:
            continue
        et_raw = (ev.get("event_type") or "EVENT").upper()
        verb = EVENT_VERB.get(et_raw, et_raw.title())
        feed.append(
            {
                "stage": "strategy",
                "kind": et_raw,
                "ts": ev.get("created_at"),
                "summary": f"{verb}: {_emp_name(ev.get('employee_id'))}",
            }
        )

    # InterviewSchedule — recruit
    interviews = dataflow_crud.list_records(
        "InterviewSchedule", {"company_id": company_id}, cache_ttl=0
    )
    for iv in interviews:
        if (iv.get("created_at") or "") < cutoff:
            continue
        cand_name = candidate_name_by_id.get(
            iv.get("candidate_id"), f"candidate #{iv.get('candidate_id')}"
        )
        feed.append(
            {
                "stage": "recruit",
                "kind": "INTERVIEW",
                "ts": iv.get("created_at"),
                "summary": f"Interview {iv.get('status')}: {cand_name}",
            }
        )

    # OnboardingStepProgress — onboard. Round-2 redteam B1: roll up to
    # one entry PER ASSIGNMENT (highest-watermark step), not one entry
    # per step, and scope to this company's assignments. Otherwise the
    # feed reads as 7 duplicates of the same employee finishing 7 steps.
    progresses = dataflow_crud.list_records(
        "OnboardingStepProgress", {}, cache_ttl=0
    )
    latest_per_assignment: dict[int, dict] = {}
    for p in progresses:
        if p.get("status") != "completed":
            continue
        ts = p.get("completed_at") or ""
        if ts < cutoff:
            continue
        aid = p.get("assignment_id")
        if aid not in assignment_emp_id:
            continue
        prev = latest_per_assignment.get(aid)
        if prev is None or (prev.get("completed_at") or "") < ts:
            latest_per_assignment[aid] = p
    for aid, p in latest_per_assignment.items():
        feed.append(
            {
                "stage": "onboard",
                "kind": "STEP_COMPLETE",
                "ts": p.get("completed_at"),
                "summary": f"Onboarding progress: {_emp_name(assignment_emp_id.get(aid))}",
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
                "summary": f"Appraisal {ap.get('status')}: {_emp_name(ap.get('employee_id'))}",
            }
        )

    # Recognition — reward
    for r in _safe_list("Recognition", {"company_id": company_id}):
        ts = r.get("created_at") or ""
        if not ts or ts < cutoff:
            continue
        if r.get("is_archived"):
            continue
        if not r.get("is_public", True):
            continue
        feed.append(
            {
                "stage": "reward",
                "kind": "KUDOS",
                "ts": ts,
                "summary": (
                    f"Kudos for {_emp_name(r.get('to_employee_id'))} "
                    f"({_kudos_label(r.get('category'))})"
                ),
            }
        )

    # ExitInterview — retain
    for ei in _safe_list("ExitInterview", {"company_id": company_id}):
        ts = ei.get("submitted_at") or ei.get("triggered_at") or ""
        if not ts or ts < cutoff:
            continue
        if ei.get("is_archived"):
            continue
        emp_label = (
            "anonymous leaver"
            if ei.get("is_anonymous")
            else _emp_name(ei.get("employee_id"))
        )
        feed.append(
            {
                "stage": "retain",
                "kind": "EXIT_INTERVIEW",
                "ts": ts,
                "summary": (
                    f"Exit interview {'submitted' if ei.get('submitted_at') else 'triggered'}: {emp_label}"
                ),
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


# ===========================================================================
# Phase 3 — Strategic depth (P3 obayashi)
# ===========================================================================


def _now_dt() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

#
# WorkforcePlan + SkillsInventory + SuccessionPlan + retention-risk
# derived view + pay-equity dashboard. Each section is small and
# read-mostly except WorkforcePlan, which is the authoring surface.


# ---------------------------------------------------------------------------
# P3-1 — WorkforcePlan
# ---------------------------------------------------------------------------


@router.get("/workforce-plan")
async def list_workforce_plans(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    rows = dataflow_crud.list_records(
        "WorkforcePlan", {"company_id": company_id}, cache_ttl=0
    )
    rows = [r for r in rows if r.get("status") != "archived"]
    rows.sort(key=lambda r: r.get("period_start") or "", reverse=True)
    return {"plans": rows, "count": len(rows)}


@router.post("/workforce-plan")
async def create_workforce_plan(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    body = await request.json()
    name = (body.get("name") or "").strip()
    period_start = body.get("period_start") or ""
    period_end = body.get("period_end") or ""
    if not name or not period_start or not period_end:
        raise HTTPException(
            status_code=400,
            detail="name, period_start, period_end are required.",
        )

    now = _now_dt()
    record = dataflow_crud.create(
        "WorkforcePlan",
        {
            "company_id": company_id,
            "period_start": period_start,
            "period_end": period_end,
            "name": name,
            "status": body.get("status", "draft"),
            "headcount_targets": json.dumps(body.get("headcount_targets") or {}),
            "skills_priorities": json.dumps(
                body.get("skills_priorities") or []
            ),
            "retention_focus": json.dumps(body.get("retention_focus") or []),
            "narrative": body.get("narrative") or "",
            "created_by": user_id,
            "approved_by": 0,
            "approved_at": None,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"plan": record}


@router.patch("/workforce-plan/{plan_id}")
async def update_workforce_plan(
    plan_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    rows = dataflow_crud.list_records(
        "WorkforcePlan",
        {"id": plan_id, "company_id": company_id},
        cache_ttl=0,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Plan not found.")
    body = await request.json()
    user_id = int(current_user.get("sub", 0))
    updates: dict[str, Any] = {}
    for k in ("name", "period_start", "period_end", "narrative", "status"):
        if k in body:
            updates[k] = body[k]
    for k in ("headcount_targets", "skills_priorities", "retention_focus"):
        if k in body:
            updates[k] = json.dumps(body[k])
    if updates.get("status") == "published":
        updates["approved_by"] = user_id
        updates["approved_at"] = _now_dt()
    updates["updated_at"] = _now_dt()
    dataflow_crud.update("WorkforcePlan", plan_id, updates)
    return {"plan": dataflow_crud.read("WorkforcePlan", plan_id)}


# ---------------------------------------------------------------------------
# P3-2 — SkillsInventory
# ---------------------------------------------------------------------------


@router.get("/skills")
async def list_skills(
    employee_id: int | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    rows = dataflow_crud.list_records(
        "SkillsInventoryEntry", {"company_id": company_id}, cache_ttl=0
    )
    rows = [r for r in rows if not r.get("is_archived")]
    if employee_id is not None:
        rows = [r for r in rows if r.get("employee_id") == employee_id]
    return {"skills": rows, "count": len(rows)}


@router.get("/skills/coverage")
async def skills_coverage(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    rows = dataflow_crud.list_records(
        "SkillsInventoryEntry", {"company_id": company_id}, cache_ttl=0
    )
    rows = [r for r in rows if not r.get("is_archived")]
    coverage: dict[str, int] = {}
    for r in rows:
        name = (r.get("skill_name") or "").strip()
        if name:
            coverage[name] = coverage.get(name, 0) + 1
    return {
        "coverage": [
            {"skill": k, "count": v}
            for k, v in sorted(coverage.items(), key=lambda x: x[1], reverse=True)
        ],
        "total_entries": len(rows),
    }


@router.post("/skills")
async def create_skill(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    body = await request.json()
    employee_id = body.get("employee_id")
    skill_name = (body.get("skill_name") or "").strip()
    if not employee_id or not skill_name:
        raise HTTPException(
            status_code=400,
            detail="employee_id and skill_name are required.",
        )
    proficiency = int(body.get("proficiency") or 3)
    if proficiency < 1 or proficiency > 5:
        raise HTTPException(
            status_code=400, detail="proficiency must be 1..5"
        )
    now = _now_dt()
    record = dataflow_crud.create(
        "SkillsInventoryEntry",
        {
            "company_id": company_id,
            "employee_id": int(employee_id),
            "skill_name": skill_name,
            "proficiency": proficiency,
            "years_experience": float(body.get("years_experience") or 0.0),
            "last_used_date": body.get("last_used_date") or "",
            "verified_by_user_id": int(
                body.get("verified_by_user_id") or 0
            ),
            "notes": body.get("notes") or "",
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"skill": record}


# ---------------------------------------------------------------------------
# P3-3 — SuccessionPlan
# ---------------------------------------------------------------------------


@router.get("/succession")
async def list_succession(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    rows = dataflow_crud.list_records(
        "SuccessionPlan", {"company_id": company_id}, cache_ttl=0
    )
    rows = [r for r in rows if not r.get("is_archived")]
    return {"plans": rows, "count": len(rows)}


@router.post("/succession")
async def create_succession(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    body = await request.json()
    role = (body.get("role_title") or "").strip()
    if not role:
        raise HTTPException(status_code=400, detail="role_title is required.")
    now = _now_dt()
    record = dataflow_crud.create(
        "SuccessionPlan",
        {
            "company_id": company_id,
            "role_title": role,
            "incumbent_employee_id": int(
                body.get("incumbent_employee_id") or 0
            ),
            "criticality": body.get("criticality", "medium"),
            "successors": json.dumps(body.get("successors") or []),
            "notes": body.get("notes") or "",
            "last_reviewed_at": now,
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"plan": record}


# ---------------------------------------------------------------------------
# P3-4 — Retention risk derived view (read-only, no new PII)
# ---------------------------------------------------------------------------


@router.get("/retention-risk")
async def retention_risk(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Compute a simple risk score (0..100) per active employee.

    Inputs (all from existing fields, no new PII):
      - tenure_months  (lower → higher risk; 0..6 spike, 6..24 mid, 24+ low)
      - PROMOTED count YTD (positive signal)
      - SALARY_REVISION count YTD (positive signal)
      - leave usage trend (high → ambiguous; we treat very-high as risk)
      - latest appraisal score (low → risk)

    Output: for each employee, a {score, drivers, recommendation} object.
    Bucket counts < 5 are not redacted (we expose individual scores to
    HR). Per spec: never persisted, always recomputed.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    employees = _employees_for_company(company_id)
    events = _events_for_company(company_id)
    appraisals = dataflow_crud.list_records(
        "Appraisal", {"company_id": company_id}, cache_ttl=0
    )
    leaves = dataflow_crud.list_records(
        "LeaveApplication", {"company_id": company_id}, cache_ttl=0
    )
    goals = _safe_list("Goal", {"company_id": company_id})
    recognitions = _safe_list("Recognition", {"company_id": company_id})

    today = date.today()
    year_start = date(today.year, 1, 1).isoformat()
    cutoff_90d = (today - timedelta(days=90)).isoformat()
    cutoff_30d = (today - timedelta(days=30)).isoformat()

    risk_rows = []
    for emp in employees:
        emp_id = emp.get("id")
        score = 50  # baseline
        drivers: list[str] = []

        # Tenure — Round-2 redteam H3: widened so every active employee
        # produces at least one driver. The previous bands left 26/28
        # employees with empty drivers, which read as a placeholder.
        start_iso = emp.get("start_date") or ""
        tenure_months: int | None = None
        if start_iso:
            try:
                start = date.fromisoformat(start_iso)
                tenure_months = (
                    (today.year - start.year) * 12 + today.month - start.month
                )
                if tenure_months < 6:
                    score += 15
                    drivers.append(f"Short tenure ({tenure_months} months)")
                elif tenure_months < 18:
                    score += 5
                    drivers.append(f"Building tenure ({tenure_months} months)")
                elif tenure_months > 36:
                    score -= 5
                    drivers.append(f"Long tenure ({tenure_months} months) — flight risk if stagnant")
            except (ValueError, TypeError):
                pass

        # Pass class — work-pass holders carry visa-renewal risk.
        pass_type = (emp.get("pass_type") or "").strip().lower()
        if pass_type in ("ep", "sp", "wp"):
            score += 5
            drivers.append(f"Foreign worker ({pass_type.upper()}) — pass renewal cycle")

        # Confirmation status — unconfirmed = probation = elevated risk.
        confirmation = (emp.get("confirmation_status") or "").strip().lower()
        if confirmation == "probation":
            score += 10
            drivers.append("On probation")

        # Promotions / salary revisions YTD = positive signals.
        ytd_events = [
            e
            for e in events
            if e.get("employee_id") == emp_id
            and (e.get("created_at") or "") >= year_start
        ]
        promo_count = sum(
            1 for e in ytd_events if e.get("event_type") == "PROMOTED"
        )
        rev_count = sum(
            1 for e in ytd_events if e.get("event_type") == "SALARY_REVISION"
        )
        if promo_count > 0:
            score -= 10
            drivers.append(f"{promo_count} promotion this year")
        if rev_count > 0:
            score -= 5
            drivers.append(f"{rev_count} salary revision this year")

        # No promotion + no salary revision in 18+ months → stagnation risk.
        if tenure_months and tenure_months >= 18 and promo_count == 0 and rev_count == 0:
            score += 5
            drivers.append("No promotion or revision in 18+ months")

        # Latest appraisal score.
        my_apps = [
            a for a in appraisals if a.get("employee_id") == emp_id
        ]
        if my_apps:
            latest = max(my_apps, key=lambda a: a.get("updated_at") or "")
            overall = float(latest.get("overall_score") or 0.0)
            if overall and overall < 3.0:
                score += 15
                drivers.append("Recent appraisal score low (< 3.0/5)")
            elif overall >= 4.5:
                score -= 5
                drivers.append(f"Recent appraisal strong ({overall:.1f}/5)")
        else:
            # Round-2 redteam H3: no appraisal on file is itself a signal.
            drivers.append("No appraisal on file")

        # Leave usage YTD — very high → risk.
        my_leaves_days = sum(
            float(la.get("total_days") or 0.0)
            for la in leaves
            if la.get("employee_id") == emp_id
            and la.get("status") == "approved"
            and (la.get("start_date") or "") >= year_start
        )
        if my_leaves_days > 20:
            score += 10
            drivers.append(f"Very high leave usage ({int(my_leaves_days)} days YTD)")
        elif my_leaves_days == 0 and tenure_months and tenure_months > 6:
            # Zero leave is itself amber — burnout proxy.
            score += 5
            drivers.append("No leave taken this year (burnout risk)")

        # Goals at risk — direct progression signal.
        my_goals_at_risk = sum(
            1
            for g in goals
            if g.get("employee_id") == emp_id and g.get("status") == "at_risk"
        )
        if my_goals_at_risk > 0:
            score += 8
            drivers.append(f"{my_goals_at_risk} goal at risk")

        # Recognition received in 30d — positive signal.
        my_kudos_30d = sum(
            1
            for r in recognitions
            if r.get("to_employee_id") == emp_id
            and (r.get("created_at") or "") >= cutoff_30d
            and not r.get("is_archived")
        )
        if my_kudos_30d > 0:
            score -= 5
            drivers.append(f"{my_kudos_30d} kudos in last 30 days")

        score = max(0, min(100, score))
        if score >= 70:
            recommendation = "High risk — schedule a stay-interview this month."
        elif score >= 55:
            recommendation = "Watchlist — ensure recent 1:1, address any goals at risk."
        elif score >= 40:
            recommendation = "Stable — quarterly check-in is sufficient."
        else:
            recommendation = "Low risk — engaged + supported. Keep doing what's working."

        risk_rows.append(
            {
                "employee_id": emp_id,
                "score": score,
                "drivers": drivers,
                "recommendation": recommendation,
            }
        )

    risk_rows.sort(key=lambda r: r["score"], reverse=True)
    return {
        "rows": risk_rows,
        "top_at_risk": risk_rows[:5],
        "headcount": len(employees),
    }


# ---------------------------------------------------------------------------
# P3-5 — Pay-equity dashboard
# ---------------------------------------------------------------------------


@router.get("/pay-equity")
async def pay_equity(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Pay gap by gender + pass-type cohort.

    Bucket counts < 5 collapse to '—' to prevent re-identification.
    Reads from Employee.salary_monthly only — no payslip-level PII.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    employees = _employees_for_company(company_id)

    def _bucket_avg(field: str) -> list[dict]:
        buckets: dict[str, list[float]] = {}
        for emp in employees:
            raw = (emp.get(field) or "").strip().lower() or "unknown"
            sal = float(emp.get("salary_monthly") or 0.0)
            buckets.setdefault(raw, []).append(sal)
        out = []
        all_avg = (
            sum(s for vals in buckets.values() for s in vals) / max(1, sum(len(v) for v in buckets.values()))
            if buckets
            else 0.0
        )
        for k, vals in buckets.items():
            if len(vals) < 5:
                out.append(
                    {
                        "bucket": k,
                        "count": "—",
                        "avg_salary": "—",
                        "gap_vs_overall_pct": "—",
                    }
                )
                continue
            avg = sum(vals) / len(vals)
            gap = (avg - all_avg) / all_avg * 100 if all_avg > 0 else 0
            out.append(
                {
                    "bucket": k,
                    "count": len(vals),
                    "avg_salary": round(avg, 2),
                    "gap_vs_overall_pct": round(gap, 1),
                }
            )
        return out

    return {
        "by_gender": _bucket_avg("gender"),
        "by_pass_type": _bucket_avg("pass_type"),
        "headcount": len(employees),
        "note": (
            "Buckets with fewer than 5 employees are collapsed to '—' to "
            "prevent individual re-identification."
        ),
    }
