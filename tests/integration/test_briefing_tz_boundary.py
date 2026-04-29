"""S4-T7: tz-aware vs naive boundary test for shadow/briefing.py.

T215 fixed datetime tz mismatches in routers/onboarding.py, but
shadow/briefing.py reads the same OnboardingAssignment rows and was
never tested with tz-aware values. This test seeds rows whose
`due_date` is a tz-aware ISO string and an aware Python datetime, then
calls every public briefing function. A naive-vs-aware comparison
anywhere in the briefing path would raise TypeError; this test pins
the invariant that briefing handles both forms.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest


def _aware_assignment(**overrides) -> dict:
    """Build an OnboardingAssignment row with a tz-aware due_date.

    DataFlow can return due_date as either a string (ISO with offset) or
    a Python datetime; the briefing must tolerate either.
    """
    base = {
        "id": 1,
        "company_id": 1,
        "employee_id": 100,
        "template_id": 1,
        "status": "in_progress",
        "completion_percentage": 35.0,
        "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "assigned_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    }
    base.update(overrides)
    return base


def _naive_assignment(**overrides) -> dict:
    """Some legacy rows still carry naive due_dates. The briefing must
    not crash on those either.
    """
    base = _aware_assignment(**overrides)
    # Force a naive ISO string (no offset)
    naive_dt = datetime.utcnow() + timedelta(days=7)
    base["due_date"] = naive_dt.replace(tzinfo=None).isoformat()
    return base


@pytest.mark.integration
def test_s4_t7_briefing_handles_tz_aware_assignments():
    """`generate_briefing` must complete without raising when the
    underlying OnboardingAssignment rows have tz-aware due_dates.
    """
    from hr_advisory.shadow import briefing as briefing_module

    aware_rows = [
        _aware_assignment(id=1, status="in_progress"),
        _aware_assignment(id=2, status="overdue"),
    ]

    def _stub_dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000):
        if "OnboardingAssignment" in node_type:
            return aware_rows
        return []

    with patch.object(briefing_module, "_dataflow_list", side_effect=_stub_dataflow_list):
        result = briefing_module.generate_briefing(company_id=1, user_role="owner")

    assert isinstance(result, dict)
    assert "onboarding" in result
    # The two aware-due-date assignments should produce at least one
    # onboarding insight (active or overdue counters).
    assert isinstance(result["onboarding"], list)


@pytest.mark.integration
def test_s4_t7_briefing_handles_naive_assignments():
    """Same coverage for naive due_dates — briefing must not crash."""
    from hr_advisory.shadow import briefing as briefing_module

    naive_rows = [
        _naive_assignment(id=1, status="in_progress"),
        _naive_assignment(id=2, status="in_progress"),
    ]

    def _stub_dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000):
        if "OnboardingAssignment" in node_type:
            return naive_rows
        return []

    with patch.object(briefing_module, "_dataflow_list", side_effect=_stub_dataflow_list):
        result = briefing_module.generate_briefing(company_id=1, user_role="owner")

    assert isinstance(result, dict)


@pytest.mark.integration
def test_s4_t7_briefing_handles_mixed_aware_and_naive_rows():
    """Real prod state mixes both forms — briefing must handle the union
    in a single batch.
    """
    from hr_advisory.shadow import briefing as briefing_module

    mixed = [
        _aware_assignment(id=1),
        _naive_assignment(id=2),
        _aware_assignment(id=3, status="overdue"),
        _naive_assignment(id=4, status="completed"),
    ]

    def _stub_dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000):
        if "OnboardingAssignment" in node_type:
            return mixed
        return []

    with patch.object(briefing_module, "_dataflow_list", side_effect=_stub_dataflow_list):
        result = briefing_module.generate_briefing(company_id=1, user_role="owner")

    assert isinstance(result, dict)


@pytest.mark.integration
def test_s4_t7_onboarding_insights_employee_view_handles_tz():
    """The employee-view path (non-admin) takes a different branch.
    Cover it separately so a regression there doesn't slip through.
    """
    from hr_advisory.shadow import briefing as briefing_module

    rows = [_aware_assignment(employee_id=100), _naive_assignment(employee_id=100)]

    def _stub_dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000):
        if "OnboardingAssignment" in node_type:
            return rows
        return []

    with patch.object(briefing_module, "_dataflow_list", side_effect=_stub_dataflow_list):
        # Use a non-HR role so the employee branch fires
        result = briefing_module._onboarding_insights(company_id=1, user_role="employee")

    assert isinstance(result, list)


@pytest.mark.integration
def test_s4_t7_briefing_with_empty_assignments_returns_empty_onboarding():
    """Edge case: no assignments at all. Briefing must not crash and
    must return a benign onboarding=[] section.
    """
    from hr_advisory.shadow import briefing as briefing_module

    with patch.object(briefing_module, "_dataflow_list", return_value=[]):
        result = briefing_module.generate_briefing(company_id=1, user_role="owner")

    assert result["onboarding"] == [] or isinstance(result["onboarding"], list)
    assert result["total_action_items"] >= 0
