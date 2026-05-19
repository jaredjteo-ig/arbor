"""Red-team round-3 — headcount source-of-truth (P2 / X1).

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding X1 / C2 — /reports said 29, /lifecycle said 28, /employees
list said 28, /analytics said 28. The +1 was caused by an Employee
row carrying `is_active=True` but `confirmation_status="terminated"`
(termination path wrote one field without the other). Each surface
ran its own DataFlow query with a slightly different predicate.

This file pins:
  - services.headcount has the canonical predicate.
  - The predicate matches the documented rule:
      is_active=True AND end_date in future AND confirmation_status != terminated.
  - The four surfaces (strategy, reports, profile, profile-workforce)
    route through it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "strategy.py"
REPORTS = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "reports.py"
PROFILE = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "profile.py"
HEADCOUNT = REPO_ROOT / "src" / "hr_advisory" / "services" / "headcount.py"


# ---------------------------------------------------------------------------
# Predicate behaviour
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_active_predicate_excludes_terminated():
    """The +1 bug: an Employee row with is_active=True AND
    confirmation_status='terminated' must be excluded from headcount."""
    from hr_advisory.services.headcount import _is_active_on

    row = {
        "is_active": True,
        "confirmation_status": "terminated",
        "end_date": "",
    }
    assert _is_active_on(row, date(2026, 5, 19)) is False


@pytest.mark.regression
def test_redteam3_active_predicate_excludes_past_end_date():
    """An employee whose end_date has passed must be excluded even if
    is_active wasn't flipped to False."""
    from hr_advisory.services.headcount import _is_active_on

    row = {
        "is_active": True,
        "confirmation_status": "confirmed",
        "end_date": "2024-01-01",
    }
    assert _is_active_on(row, date(2026, 5, 19)) is False


@pytest.mark.regression
def test_redteam3_active_predicate_includes_active_confirmed():
    """The happy-path active row IS counted."""
    from hr_advisory.services.headcount import _is_active_on

    row = {
        "is_active": True,
        "confirmation_status": "confirmed",
        "end_date": "",
    }
    assert _is_active_on(row, date(2026, 5, 19)) is True


@pytest.mark.regression
def test_redteam3_active_predicate_includes_future_end_date():
    """A future end_date (e.g. fixed-contract employee with planned end)
    still counts as active today."""
    from hr_advisory.services.headcount import _is_active_on

    row = {
        "is_active": True,
        "confirmation_status": "confirmed",
        "end_date": "2099-01-01",
    }
    assert _is_active_on(row, date(2026, 5, 19)) is True


@pytest.mark.regression
def test_redteam3_active_predicate_includes_on_probation():
    """An employee still on probation IS active — they're working,
    just not confirmed yet."""
    from hr_advisory.services.headcount import _is_active_on

    row = {
        "is_active": True,
        "confirmation_status": "on_probation",
        "end_date": "",
    }
    assert _is_active_on(row, date(2026, 5, 19)) is True


# ---------------------------------------------------------------------------
# Call-site wiring
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_strategy_routes_through_headcount_service():
    src = STRATEGY.read_text()
    assert "from hr_advisory.services.headcount import list_active_employees" in src, (
        "strategy.py _employees_for_company must route through the "
        "canonical headcount predicate."
    )


@pytest.mark.regression
def test_redteam3_reports_routes_through_headcount_service():
    src = REPORTS.read_text()
    assert "list_active_employees" in src, (
        "reports.py turnover analysis must route the 'active' branch "
        "through the canonical headcount predicate."
    )


@pytest.mark.regression
def test_redteam3_profile_dashboard_routes_through_headcount_service():
    src = PROFILE.read_text()
    # The dashboard live-headcount tile + the pass-type bucket counter
    # must both come from the same predicate.
    assert src.count("list_active_employees") >= 2, (
        "profile.py must route BOTH the live-headcount tile and the "
        "pass-type breakdown through list_active_employees."
    )


# ---------------------------------------------------------------------------
# get_active_employee_count integration smoke
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_get_active_employee_count_uses_canonical_filter():
    from unittest.mock import patch

    from hr_advisory.services import headcount as svc

    # Simulate the live walk's bug: 29 rows returned from DataFlow,
    # one of which is `is_active=True AND confirmation_status=terminated`.
    rows = [{"id": i, "is_active": True, "confirmation_status": "confirmed", "end_date": ""} for i in range(28)]
    rows.append({"id": 99, "is_active": True, "confirmation_status": "terminated", "end_date": ""})

    with patch(
        "hr_advisory.services.dataflow_crud.list_records", return_value=rows
    ):
        assert svc.get_active_employee_count(1) == 28
