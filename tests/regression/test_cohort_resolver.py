"""Regression tests for cohort resolver (T04).

Pins the eight filter dimensions individually + the union/intersect
semantics. Uses monkeypatched `dataflow_crud.list_records` to inject
deterministic employee data.

Acceptance criteria (from M0 T04 + Z03):
- All 8 filter keys validate and resolve correctly.
- Tenure filter computes off start_date.
- Inactive employees never appear in the result.
- ad_hoc_employee_ids unions with the dimensional result.
- P1-only validation rejects multi-dimension combinators that defer
  to M8 T91.
"""

from __future__ import annotations

from datetime import date

import pytest

from hr_advisory.services import cohort_resolver


@pytest.fixture
def seed_employees(monkeypatch):
    """Seed a 6-employee fixture spanning all filter dimensions."""
    employees = [
        {
            "id": 1,
            "company_id": 1,
            "is_active": True,
            "department": "Engineering",
            "designation": "Senior Engineer",
            "pass_type": "Citizen",
            "start_date": "2023-01-15",  # ~2.3 years tenure as of 2025-04-01
            "reporting_manager_id": 10,
        },
        {
            "id": 2,
            "company_id": 1,
            "is_active": True,
            "department": "Engineering",
            "designation": "Junior Engineer",
            "pass_type": "EP",
            "start_date": "2025-01-15",  # ~76 days as of 2025-04-01
            "reporting_manager_id": 10,
        },
        {
            "id": 3,
            "company_id": 1,
            "is_active": True,
            "department": "Sales",
            "designation": "Account Director",
            "pass_type": "Citizen",
            "start_date": "2020-06-01",  # 4+ years
            "reporting_manager_id": 11,
        },
        {
            "id": 4,
            "company_id": 1,
            "is_active": False,  # terminated — never appears
            "department": "Engineering",
            "designation": "Senior Engineer",
            "pass_type": "Citizen",
            "start_date": "2022-01-01",
            "reporting_manager_id": 10,
        },
        {
            "id": 5,
            "company_id": 1,
            "is_active": True,
            "department": "Marketing",
            "designation": "Content Lead",
            "pass_type": "PR",
            "start_date": "2024-08-01",
            "reporting_manager_id": 12,
        },
        {
            "id": 6,
            "company_id": 1,
            "is_active": True,
            "department": "Sales",
            "designation": "Account Manager",
            "pass_type": "EP",
            "start_date": "2024-12-01",
            "reporting_manager_id": 11,
        },
    ]

    def fake_list(model, where, **_):
        if model == "Employee":
            return [
                e for e in employees
                if e["company_id"] == where.get("company_id")
            ]
        return []

    monkeypatch.setattr(
        cohort_resolver.dataflow_crud, "list_records", fake_list
    )
    return employees


@pytest.fixture
def fixed_today():
    return date(2025, 4, 1)


@pytest.mark.regression
def test_all_active_returns_only_active_employees(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"all_active": True},
        today=fixed_today,
    )
    # Excludes terminated employee 4
    assert result == [1, 2, 3, 5, 6]


@pytest.mark.regression
def test_department_filter(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"departments": ["Engineering"]},
        today=fixed_today,
    )
    assert result == [1, 2]  # 4 is inactive


@pytest.mark.regression
def test_department_filter_case_insensitive(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"departments": ["engineering"]},
        today=fixed_today,
    )
    assert result == [1, 2]


@pytest.mark.regression
def test_designations_like_substring_match(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"designations_like": ["engineer"]},
        today=fixed_today,
    )
    assert result == [1, 2]


@pytest.mark.regression
def test_pass_types_filter(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"pass_types": ["EP"]},
        today=fixed_today,
    )
    assert result == [2, 6]


@pytest.mark.regression
def test_tenure_max_days_filter_for_new_joiners(seed_employees, fixed_today):
    """The 'new joiners under 90 days' P1 preset."""
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"tenure_max_days": 90},
        today=fixed_today,
    )
    # Only employee 2 (start 2025-01-15, ~76 days) matches.
    assert result == [2]


@pytest.mark.regression
def test_tenure_min_days_filter(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"tenure_min_days": 365},
        today=fixed_today,
    )
    # Employees with >= 1 year tenure as of 2025-04-01.
    # 1 (2023-01-15, 807d), 3 (2020-06-01, 1765d) — yes.
    # 5 (2024-08-01, 243d), 2 (2025-01-15, 76d), 6 (2024-12-01, 121d) — no.
    assert result == [1, 3]


@pytest.mark.regression
def test_manager_ids_filter(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"manager_ids": [10]},
        today=fixed_today,
    )
    assert result == [1, 2]


@pytest.mark.regression
def test_ad_hoc_unions_with_dimensional(seed_employees, fixed_today):
    """ad_hoc adds employees outside the dimensional match."""
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={
            "departments": ["Engineering"],
            "ad_hoc_employee_ids": [3],  # add Sales account director
        },
        today=fixed_today,
    )
    assert result == [1, 2, 3]


@pytest.mark.regression
def test_ad_hoc_skips_inactive_employees(seed_employees, fixed_today):
    """Even via ad_hoc, terminated employees never appear (C1)."""
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"ad_hoc_employee_ids": [4]},
        today=fixed_today,
    )
    assert result == []


@pytest.mark.regression
def test_intersect_two_dimensions(seed_employees, fixed_today):
    """Engineering + EP → only employee 2."""
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={
            "departments": ["Engineering"],
            "pass_types": ["EP"],
        },
        today=fixed_today,
    )
    assert result == [2]


@pytest.mark.regression
def test_empty_result_returns_empty_list(seed_employees, fixed_today):
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={"departments": ["Nonexistent"]},
        today=fixed_today,
    )
    assert result == []


@pytest.mark.regression
def test_result_is_sorted_and_unique(seed_employees, fixed_today):
    """Even with overlapping ad_hoc + dimensional matches, the result
    is sorted unique integers.
    """
    result = cohort_resolver.resolve_cohort(
        company_id=1,
        filter_spec={
            "departments": ["Engineering"],
            "ad_hoc_employee_ids": [1, 2],  # already in dimensional
        },
        today=fixed_today,
    )
    assert result == [1, 2]


# --- validate_filter_spec ---


@pytest.mark.regression
def test_validate_rejects_unknown_key():
    with pytest.raises(ValueError, match="Unknown filter keys"):
        cohort_resolver.validate_filter_spec({"made_up_key": "x"})


@pytest.mark.regression
def test_validate_rejects_negative_tenure():
    with pytest.raises(ValueError, match="non-negative"):
        cohort_resolver.validate_filter_spec({"tenure_min_days": -5})


@pytest.mark.regression
def test_validate_rejects_inverted_tenure_range():
    with pytest.raises(ValueError, match="<= tenure_max_days"):
        cohort_resolver.validate_filter_spec(
            {"tenure_min_days": 100, "tenure_max_days": 50}
        )


@pytest.mark.regression
def test_validate_rejects_non_list_departments():
    with pytest.raises(ValueError, match="must be a list"):
        cohort_resolver.validate_filter_spec({"departments": "Engineering"})


@pytest.mark.regression
def test_validate_p1_only_rejects_full_builder_keys():
    """At P1 the cohort UI exposes only presets + ad_hoc.

    Multi-dimension combinators like manager_ids + designations_like
    defer to M8 T91. The P1 handler enforces this; the resolver
    itself accepts them so saved cohorts keep working post-M8.
    """
    with pytest.raises(ValueError, match="P1 supports only"):
        cohort_resolver.validate_filter_spec(
            {"manager_ids": [10]}, p1_only=True
        )


@pytest.mark.regression
def test_validate_p1_only_accepts_presets():
    cohort_resolver.validate_filter_spec(
        {"all_active": True}, p1_only=True
    )
    cohort_resolver.validate_filter_spec(
        {"departments": ["Engineering"]}, p1_only=True
    )
    cohort_resolver.validate_filter_spec(
        {"tenure_max_days": 90}, p1_only=True
    )
    cohort_resolver.validate_filter_spec(
        {"ad_hoc_employee_ids": [1, 2]}, p1_only=True
    )
    # No exception raised → all four pass.
