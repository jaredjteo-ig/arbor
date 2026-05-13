"""P4-MG-3 regression tests — /team dashboard.

New BE endpoints:
- GET /api/team/size       — used by sidebar to show/hide Team link
- GET /api/team/dashboard  — bundled cards for the page
- GET /api/team/members    — flat roster

FE: /team page + conditional sidebar entry driven by useTeamSize().

Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
finding P1-A.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "team.py"
)
ROUTERS_INIT = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "__init__.py"
)
PLATFORM = REPO_ROOT / "src" / "hr_advisory" / "api" / "platform.py"
SIDEBAR = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "components"
    / "shell"
    / "NavigationSidebar.tsx"
)
TEAM_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "team"
    / "page.tsx"
)
USE_TEAM_HOOK = (
    REPO_ROOT / "apps" / "web" / "src" / "hooks" / "api" / "useTeam.ts"
)


# ---------------------------------------------------------------------------
# Source-level: router exists, wired in __init__, mounted in platform.py.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg3_team_router_module_exists():
    assert TEAM_ROUTER.exists(), (
        "team router must live at src/hr_advisory/api/routers/team.py"
    )


@pytest.mark.regression
def test_mg3_team_router_registers_three_endpoints():
    """The team router must expose /size, /dashboard, /members.
    /size is the cheap visibility check; /dashboard is the bundled
    page payload; /members is the roster-only call.
    """
    src = TEAM_ROUTER.read_text()
    for path in ['@router.get("/size")', '@router.get("/dashboard")', '@router.get("/members")']:
        assert path in src, f"team.py missing endpoint decorator {path}"


@pytest.mark.regression
def test_mg3_team_router_exported_from_init():
    src = ROUTERS_INIT.read_text()
    assert "team_router" in src, (
        "team_router must be re-exported from routers/__init__.py"
    )
    assert (
        "from hr_advisory.api.routers.team import router as team_router"
        in src
    ), "team_router import line missing"


@pytest.mark.regression
def test_mg3_team_router_mounted_under_team_prefix():
    src = PLATFORM.read_text()
    assert (
        'include_router(team_router, prefix="/team"' in src
    ), "team_router must be mounted at /team in platform.py"


# ---------------------------------------------------------------------------
# Behavioural: empty-team and populated-team responses.
# ---------------------------------------------------------------------------


@pytest.mark.regression
async def test_mg3_team_size_returns_zero_for_non_manager():
    """An IC with no direct reports gets `team_size: 0` — not 404,
    so the sidebar can quietly hide the Team link."""
    from hr_advisory.api.routers.team import team_size

    marcus = {"sub": "11", "role": "employee", "company_id": 1}
    with patch(
        "hr_advisory.services.manager_scope.get_managed_employee_ids",
        return_value=set(),
    ):
        result = await team_size(current_user=marcus)
    assert result == {"team_size": 0}


@pytest.mark.regression
async def test_mg3_team_size_returns_count_for_manager():
    from hr_advisory.api.routers.team import team_size

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}
    with patch(
        "hr_advisory.services.manager_scope.get_managed_employee_ids",
        return_value={10, 6, 5, 7, 8, 9, 28},
    ):
        result = await team_size(current_user=rajesh)
    assert result["team_size"] == 7


@pytest.mark.regression
async def test_mg3_team_dashboard_returns_empty_shape_for_non_manager():
    """Non-managers must get a stable empty shape, not a 404 — the
    sidebar caches team_size and could be stale; the page must
    render cleanly even if the user reached it accidentally.
    """
    from hr_advisory.api.routers.team import team_dashboard

    marcus = {"sub": "11", "role": "employee", "company_id": 1}
    with patch(
        "hr_advisory.services.manager_scope.get_managed_employee_ids",
        return_value=set(),
    ):
        result = await team_dashboard(current_user=marcus)

    assert result["team_size"] == 0
    # NB: P4-MG-4 added an `appraisals` count to the pending tile.
    assert result["pending_approvals"] == {
        "leave": 0,
        "claims": 0,
        "timesheets": 0,
        "appraisals": 0,
        "total": 0,
    }
    assert result["on_leave_today"] == []
    assert result["upcoming_leave"] == []
    assert result["team_members"] == []


@pytest.mark.regression
async def test_mg3_team_dashboard_aggregates_for_manager():
    """A line-manager view aggregates pending counts + on-leave +
    upcoming + roster, scoped strictly to their team."""
    from datetime import date, timedelta

    from hr_advisory.api.routers.team import team_dashboard

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}
    team = {10, 6}  # Marcus, Priya

    today_iso = date.today().isoformat()
    tomorrow_iso = (date.today() + timedelta(days=1)).isoformat()
    next_week_start = (date.today() + timedelta(days=5)).isoformat()
    next_week_end = (date.today() + timedelta(days=7)).isoformat()

    def fake_list(model_name, filter_dict=None, **kwargs):
        f = filter_dict or {}
        if model_name == "LeaveApplication":
            if f.get("status") == "pending":
                # Two pending: one on-team, one off-team
                return [
                    {"id": 1, "employee_id": 10, "status": "pending"},
                    {"id": 2, "employee_id": 99, "status": "pending"},
                ]
            if f.get("status") == "approved":
                return [
                    # On leave today (Marcus)
                    {
                        "id": 3,
                        "employee_id": 10,
                        "status": "approved",
                        "start_date": today_iso,
                        "end_date": tomorrow_iso,
                        "leave_type_code": "annual",
                    },
                    # Upcoming (Priya)
                    {
                        "id": 4,
                        "employee_id": 6,
                        "status": "approved",
                        "start_date": next_week_start,
                        "end_date": next_week_end,
                        "leave_type_code": "annual",
                    },
                    # Off-team — must NOT appear
                    {
                        "id": 5,
                        "employee_id": 99,
                        "status": "approved",
                        "start_date": today_iso,
                        "end_date": tomorrow_iso,
                        "leave_type_code": "annual",
                    },
                ]
        if model_name == "Claim" and f.get("status") == "pending_approval":
            return [{"id": 11, "employee_id": 6}]  # 1 on-team
        if model_name == "TimesheetApproval" and f.get("status") == "pending":
            return [
                {"id": 21, "employee_id": 10},
                {"id": 22, "employee_id": 99},  # off-team
            ]
        if model_name == "Employee":
            emps = {
                10: {"id": 10, "user_id": 11, "department": "Engineering"},
                6: {"id": 6, "user_id": 7, "department": "Engineering"},
            }
            if "id" in f:
                emp = emps.get(f["id"])
                return [emp] if emp else []
            return []
        if model_name == "User":
            users = {11: {"id": 11, "name": "Marcus Tan"}, 7: {"id": 7, "name": "Priya Nair"}}
            if "id" in f:
                u = users.get(f["id"])
                return [u] if u else []
        return []

    with patch(
        "hr_advisory.services.manager_scope.get_managed_employee_ids",
        return_value=team,
    ), patch(
        "hr_advisory.services.dataflow_crud.list_records", side_effect=fake_list
    ):
        result = await team_dashboard(current_user=rajesh)

    assert result["team_size"] == 2
    # NB: P4-MG-4 added `appraisals` count. The fake_list helper in
    # this test doesn't return Appraisal rows, so the count is 0 —
    # which is the realistic case for a small SG SME mid-quarter
    # (appraisal cycles are infrequent).
    assert result["pending_approvals"] == {
        "leave": 1,
        "claims": 1,
        "timesheets": 1,
        "appraisals": 0,
        "total": 3,
    }, "off-team pending records must be excluded from the count"

    assert len(result["on_leave_today"]) == 1
    assert result["on_leave_today"][0]["employee_name"] == "Marcus Tan"

    assert len(result["upcoming_leave"]) == 1
    assert result["upcoming_leave"][0]["employee_name"] == "Priya Nair"


# ---------------------------------------------------------------------------
# Frontend: sidebar conditional, page file, hook.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg3_sidebar_renders_team_conditionally():
    src = SIDEBAR.read_text()
    assert "useTeamSize" in src, (
        "Sidebar must call useTeamSize() to gate the Team link."
    )
    assert '"/team"' in src, "Sidebar must include a /team href when hasTeam."
    # The conditional injection must be at component level, not at the
    # static array level — otherwise it can't react to teamSize changes.
    assert "hasTeam" in src, (
        "Sidebar must derive a hasTeam boolean from useTeamSize()."
    )


@pytest.mark.regression
def test_mg3_team_page_exists_with_required_cards():
    src = TEAM_PAGE.read_text()
    # Title + 4 cards
    assert "Your team" in src, "Team page must render the 'Your team' header."
    for marker in [
        "Pending approvals",
        "On leave today",
        "Upcoming (14 days)",
        "Direct reports",
    ]:
        assert marker in src, f"Team page must include the '{marker}' card."


@pytest.mark.regression
def test_mg3_team_page_handles_empty_state():
    """If team_size === 0 the page must render a benign 'No direct
    reports' panel — not crash or 404 — so stale sidebar caches
    or mid-session org-chart changes don't blow up the page.
    """
    src = TEAM_PAGE.read_text()
    assert "No direct reports" in src, (
        "Team page must include a no-team empty state."
    )


@pytest.mark.regression
def test_mg3_use_team_hook_exposes_size_and_dashboard():
    src = USE_TEAM_HOOK.read_text()
    assert "useTeamSize" in src, "useTeamSize hook missing"
    assert "useTeamDashboard" in src, "useTeamDashboard hook missing"
    assert "staleTime" in src, (
        "useTeamSize should cache for a few minutes to avoid hammering "
        "the size endpoint on every nav re-render."
    )
