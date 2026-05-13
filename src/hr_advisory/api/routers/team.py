"""Team management endpoints for line managers.

Surface for any employee with ≥1 direct report (derived from
`Employee.reporting_manager_id`). Owners and HR managers can also
hit these endpoints — but typically they use the broader admin
surfaces. The /team endpoints are scoped to the caller's direct
team only — owners viewing /team see the people who report
directly to *them* (often nobody for a top-of-pyramid owner) which
matches the "my team" mental model.

Endpoints:
- GET /api/team/size           — count of direct reports (for nav)
- GET /api/team/dashboard      — bundled cards for the /team page
- GET /api/team/members        — roster with employment meta

Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
finding P1-A (line-manager role didn't exist as a workflow).
P4-MG-3 in workspaces/obayashi/todos/active/P4-MG-manager-role.md.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud, manager_scope

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enrich_employee_names(rows: list[dict], company_id: int) -> dict[int, str]:
    """Resolve employee_id → human name for a batch of records.

    Builds a single lookup by reading the Employee rows (which carry
    user_id) and then the matching User rows. Caches in-memory for the
    call duration. Returns an emp_id → name map.
    """
    emp_ids = {r.get("employee_id") for r in rows if r.get("employee_id")}
    if not emp_ids:
        return {}
    name_by_emp: dict[int, str] = {}
    for emp_id in emp_ids:
        emps = dataflow_crud.list_records(
            "Employee", {"id": emp_id, "company_id": company_id}, limit=1
        )
        if not emps:
            continue
        emp = emps[0]
        user_id = emp.get("user_id")
        if not user_id:
            continue
        users = dataflow_crud.list_records("User", {"id": user_id}, limit=1)
        if users:
            name_by_emp[emp_id] = users[0].get("name", "")
    return name_by_emp


def _team_employees(
    current_user: dict, *, active_only: bool = True
) -> list[dict]:
    """Resolve the caller's direct-report employee records.

    Uses manager_scope (preserves the security model: cross-tenant
    isolation, self-reference guard) and joins to User for name/email.
    Returns enriched dicts with `name`, `email`, `id`, `department`,
    etc. — the minimum a roster card needs.
    """
    team_ids = manager_scope.get_managed_employee_ids(
        current_user, active_only=active_only
    )
    if not team_ids:
        return []
    company_id = get_current_company_id(current_user)
    out = []
    for emp_id in team_ids:
        emps = dataflow_crud.list_records(
            "Employee", {"id": emp_id, "company_id": company_id}, limit=1
        )
        if not emps:
            continue
        emp = emps[0]
        user_id = emp.get("user_id")
        user = None
        if user_id:
            users = dataflow_crud.list_records("User", {"id": user_id}, limit=1)
            if users:
                user = users[0]
        out.append(
            {
                "id": emp.get("id"),
                "user_id": user_id,
                "name": (user or {}).get("name", ""),
                "email": (user or {}).get("email", ""),
                "department": emp.get("department", ""),
                "designation": emp.get("designation", ""),
                "employment_type": emp.get("employment_type", ""),
                "pass_type": emp.get("pass_type", ""),
                "confirmation_status": emp.get("confirmation_status", ""),
                "start_date": emp.get("start_date", ""),
                "is_active": emp.get("is_active", True),
            }
        )
    out.sort(key=lambda e: e.get("name", "").lower())
    return out


# ---------------------------------------------------------------------------
# GET /api/team/size — used by sidebar to show/hide the Team link.
# ---------------------------------------------------------------------------


@router.get("/size")
async def team_size(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return the count of the caller's direct reports.

    Cheap call so the frontend can decide whether to show the
    'Team' nav entry without fetching the full dashboard.

    A response of 0 simply means the caller has no direct reports
    — not an error.
    """
    if get_current_company_id(current_user) is None:
        return {"team_size": 0}
    team_ids = manager_scope.get_managed_employee_ids(
        current_user, active_only=True
    )
    return {"team_size": len(team_ids)}


# ---------------------------------------------------------------------------
# GET /api/team/dashboard — bundled cards for the /team page.
# ---------------------------------------------------------------------------


@router.get("/dashboard")
async def team_dashboard(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return the bundled data for the manager's /team page.

    Cards returned (all keyed off the caller's direct reports):

    - **pending_approvals**: count of leave + claims + timesheets
      awaiting the caller's decision. Surfaced as a single number
      so the UI can render a "X pending — review" CTA.
    - **on_leave_today**: list of {employee_name, leave_type,
      return_date} for direct reports on approved leave today.
    - **upcoming_leave**: approved leave starting in the next 14
      days. Used for capacity planning.
    - **team_members**: minimal roster for the table card.

    Owners and HR managers get the same shape — but typically with
    empty results since they aren't usually anyone's direct manager.
    They have the broader admin surfaces (`/payroll`, `/employees`)
    for company-wide views.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Resolve scope once.
    team_ids = manager_scope.get_managed_employee_ids(
        current_user, active_only=True
    )
    if not team_ids:
        # Empty dashboard — keeps the API contract stable so a
        # newly-promoted employee can hit /team without a 404.
        return {
            "team_size": 0,
            "pending_approvals": {
                "leave": 0,
                "claims": 0,
                "timesheets": 0,
                "total": 0,
            },
            "on_leave_today": [],
            "upcoming_leave": [],
            "team_members": [],
        }

    today = date.today()
    horizon = today + timedelta(days=14)

    # ── Pending approvals (3 entity types) ────────────────────────
    # DataFlow's equality filter doesn't support IN clauses so we
    # widen to company scope and post-filter by employee_id. For a
    # SG SME this is a bounded result.
    all_leave = dataflow_crud.list_records(
        "LeaveApplication", {"company_id": company_id, "status": "pending"}
    )
    pending_leave_count = sum(
        1 for a in all_leave if a.get("employee_id") in team_ids
    )

    all_claims = dataflow_crud.list_records(
        "Claim", {"company_id": company_id, "status": "pending_approval"}
    )
    pending_claims_count = sum(
        1 for c in all_claims if c.get("employee_id") in team_ids
    )

    all_ts = dataflow_crud.list_records(
        "TimesheetApproval", {"company_id": company_id, "status": "pending"}
    )
    pending_ts_count = sum(
        1 for t in all_ts if t.get("employee_id") in team_ids
    )

    pending_total = pending_leave_count + pending_claims_count + pending_ts_count

    # ── On leave today + upcoming-14-days ─────────────────────────
    approved_leave = dataflow_crud.list_records(
        "LeaveApplication", {"company_id": company_id, "status": "approved"}
    )
    name_map = _enrich_employee_names(approved_leave, company_id)

    on_leave_today: list[dict] = []
    upcoming: list[dict] = []
    for app in approved_leave:
        if app.get("employee_id") not in team_ids:
            continue
        try:
            start = date.fromisoformat(app.get("start_date", ""))
            end = date.fromisoformat(app.get("end_date", ""))
        except (ValueError, TypeError):
            continue
        entry = {
            "employee_id": app.get("employee_id"),
            "employee_name": name_map.get(app.get("employee_id"), ""),
            "leave_type": app.get("leave_type_code", ""),
            "start_date": app.get("start_date", ""),
            "end_date": app.get("end_date", ""),
            "return_date": (end + timedelta(days=1)).isoformat(),
        }
        if start <= today <= end:
            on_leave_today.append(entry)
        elif today < start <= horizon:
            upcoming.append(entry)

    on_leave_today.sort(key=lambda e: e["end_date"])
    upcoming.sort(key=lambda e: e["start_date"])

    return {
        "team_size": len(team_ids),
        "pending_approvals": {
            "leave": pending_leave_count,
            "claims": pending_claims_count,
            "timesheets": pending_ts_count,
            "total": pending_total,
        },
        "on_leave_today": on_leave_today,
        "upcoming_leave": upcoming,
        "team_members": _team_employees(current_user, active_only=True),
    }


# ---------------------------------------------------------------------------
# GET /api/team/members — flat roster for the table card.
# ---------------------------------------------------------------------------


@router.get("/members")
async def team_members(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return the caller's direct-report roster.

    `active_only=True` (default) filters out terminated / paused
    employees — the current-roster view that a team-dashboard
    consumer typically wants. Pass `active_only=false` to include
    ex-employees (useful for off-boarding tasks).
    """
    members = _team_employees(current_user, active_only=active_only)
    return {"members": members, "count": len(members)}
