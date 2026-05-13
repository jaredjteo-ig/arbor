"""Unit tests for `services.manager_scope`.

Derives manager scope from `Employee.reporting_manager_id` without
adding a fourth auth role. Origin: P4-MG-1 in
workspaces/obayashi/todos/active/P4-MG-manager-role.md (closed by
this work).
"""

from __future__ import annotations

from typing import Any

import pytest

from hr_advisory.services import manager_scope


# ---------------------------------------------------------------------------
# Fixtures — fake DataFlow surface
# ---------------------------------------------------------------------------


class FakeEmployeesDb:
    """In-memory stand-in for `dataflow_crud.list_records("Employee", ...)`.

    Records is a flat list of dicts matching the Employee model
    shape closely enough for the manager_scope helpers.
    """

    def __init__(self, employees: list[dict[str, Any]]):
        self._employees = employees
        self.calls: list[dict[str, Any]] = []

    def list_records(
        self,
        model_name: str,
        filter_dict: dict[str, Any] | None = None,
        limit: int = 1000,
        cache_ttl: int | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "model": model_name,
                "filter": dict(filter_dict or {}),
                "limit": limit,
            }
        )
        if model_name != "Employee":
            return []
        rows = self._employees
        if filter_dict:
            for key, val in filter_dict.items():
                rows = [r for r in rows if r.get(key) == val]
        return rows[:limit]


@pytest.fixture
def org_chart(monkeypatch):
    """Seed a small Engineering org chart and patch dataflow_crud.

    Rajesh (id=3, user_id=4) is the manager. Marcus (id=10),
    Priya (id=6), Chen Wei (id=5) report to him. Lily (id=29)
    reports to nobody. Grace (id=25) is HR manager — no employee
    row in this fixture.
    """
    employees = [
        {"id": 3, "user_id": 4, "company_id": 1, "reporting_manager_id": None},
        {"id": 10, "user_id": 11, "company_id": 1, "reporting_manager_id": 3},
        {"id": 6, "user_id": 7, "company_id": 1, "reporting_manager_id": 3},
        {"id": 5, "user_id": 6, "company_id": 1, "reporting_manager_id": 3},
        {"id": 29, "user_id": 30, "company_id": 1, "reporting_manager_id": None},
        # Foreign company — must never leak across tenant.
        {"id": 99, "user_id": 99, "company_id": 2, "reporting_manager_id": 3},
    ]
    fake = FakeEmployeesDb(employees)
    monkeypatch.setattr(
        "hr_advisory.services.dataflow_crud.list_records",
        fake.list_records,
    )
    return fake


# ---------------------------------------------------------------------------
# get_my_employee_id
# ---------------------------------------------------------------------------


def test_resolves_caller_employee_id_from_jwt(org_chart):
    rajesh_jwt = {"sub": "4", "company_id": 1, "role": "employee"}
    assert manager_scope.get_my_employee_id(rajesh_jwt) == 3


def test_returns_none_when_no_company_context(org_chart):
    no_company = {"sub": "4", "role": "platform_admin"}
    assert manager_scope.get_my_employee_id(no_company) is None


def test_returns_none_when_no_user_id(org_chart):
    headless = {"company_id": 1}
    assert manager_scope.get_my_employee_id(headless) is None


def test_returns_none_when_user_has_no_employee_row(org_chart):
    grace_jwt = {"sub": "25", "company_id": 1, "role": "hr_manager"}
    assert manager_scope.get_my_employee_id(grace_jwt) is None


# ---------------------------------------------------------------------------
# get_managed_employee_ids
# ---------------------------------------------------------------------------


def test_manager_sees_their_direct_reports(org_chart):
    rajesh_jwt = {"sub": "4", "company_id": 1, "role": "employee"}
    reports = manager_scope.get_managed_employee_ids(rajesh_jwt)
    assert reports == {5, 6, 10}, (
        "Rajesh must see exactly his 3 direct reports — not the "
        "foreign-company employee (99), not himself, not the IC "
        "with no manager (29)."
    )


def test_non_manager_employee_sees_empty_set(org_chart):
    marcus_jwt = {"sub": "11", "company_id": 1, "role": "employee"}
    assert manager_scope.get_managed_employee_ids(marcus_jwt) == set()


def test_lily_no_reports_returns_empty(org_chart):
    lily_jwt = {"sub": "30", "company_id": 1, "role": "employee"}
    assert manager_scope.get_managed_employee_ids(lily_jwt) == set()


def test_hr_manager_with_no_employee_row_returns_empty(org_chart):
    """HR managers see everyone via their role, not via the org chart.
    The helper deliberately returns empty for them so callers route
    through role-based scope, not manager-based scope."""
    grace_jwt = {"sub": "25", "company_id": 1, "role": "hr_manager"}
    assert manager_scope.get_managed_employee_ids(grace_jwt) == set()


def test_cross_tenant_isolation(org_chart):
    """If Rajesh's user_id somehow appeared under company 2, the
    helper must scope to company 1 only — the seed includes a
    company_id=2 record to make this test meaningful."""
    rajesh_jwt = {"sub": "4", "company_id": 1, "role": "employee"}
    reports = manager_scope.get_managed_employee_ids(rajesh_jwt)
    assert 99 not in reports, (
        "Cross-tenant leak: employee id 99 belongs to company 2 and "
        "must never appear in company 1's manager scope."
    )


# ---------------------------------------------------------------------------
# is_manager + is_manager_of
# ---------------------------------------------------------------------------


def test_is_manager_true_for_someone_with_reports(org_chart):
    rajesh_jwt = {"sub": "4", "company_id": 1, "role": "employee"}
    assert manager_scope.is_manager(rajesh_jwt) is True


def test_is_manager_false_for_ic(org_chart):
    marcus_jwt = {"sub": "11", "company_id": 1, "role": "employee"}
    assert manager_scope.is_manager(marcus_jwt) is False


def test_is_manager_of_accepts_direct_report(org_chart):
    rajesh_jwt = {"sub": "4", "company_id": 1, "role": "employee"}
    assert manager_scope.is_manager_of(rajesh_jwt, 10) is True


def test_is_manager_of_rejects_non_report(org_chart):
    rajesh_jwt = {"sub": "4", "company_id": 1, "role": "employee"}
    # Lily (id=29) is not on Rajesh's team.
    assert manager_scope.is_manager_of(rajesh_jwt, 29) is False


def test_is_manager_of_rejects_cross_tenant(org_chart):
    rajesh_jwt = {"sub": "4", "company_id": 1, "role": "employee"}
    assert manager_scope.is_manager_of(rajesh_jwt, 99) is False
