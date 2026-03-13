"""Unit tests for Notice Period Calculator.

Covers EA s10 statutory notice periods for Singapore:
- Service length tiers: <26 weeks, 26 weeks to <2 years, 2 to <5 years, 5+ years
- Contractual notice period override (only when >= statutory minimum)
- Salary in lieu calculation (weekly salary * notice weeks)
- Source attribution (statutory vs contractual)
"""

from __future__ import annotations

import pytest

from hr_advisory.workflows.calculators.notice_period_calculator import (
    NoticePeriodInput,
    NoticePeriodResult,
    calculate_notice_period,
)


class TestStatutoryNoticePeriods:
    """Test EA s10 statutory minimum notice periods by service length."""

    def test_less_than_26_weeks_is_1_week(self) -> None:
        """Less than 26 weeks (0.5 years) of service: 1 week notice."""
        inp = NoticePeriodInput(years_of_service=0.3, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 1
        assert result.notice_period_weeks == 1
        assert result.source == "statutory"

    def test_exactly_26_weeks_is_1_week(self) -> None:
        """Exactly 26 weeks (0.5 years) of service: 1 week notice."""
        inp = NoticePeriodInput(years_of_service=0.5, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 1
        assert result.notice_period_weeks == 1

    def test_1_year_service_is_1_week(self) -> None:
        """1 year of service (26 weeks to <2 years tier): 1 week notice."""
        inp = NoticePeriodInput(years_of_service=1.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 1

    def test_just_under_2_years_is_1_week(self) -> None:
        """1.99 years of service: still 1 week notice."""
        inp = NoticePeriodInput(years_of_service=1.99, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 1

    def test_exactly_2_years_is_2_weeks(self) -> None:
        """Exactly 2 years of service: 2 weeks notice."""
        inp = NoticePeriodInput(years_of_service=2.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 2
        assert result.notice_period_weeks == 2

    def test_3_years_is_2_weeks(self) -> None:
        """3 years of service: 2 weeks notice."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 2

    def test_just_under_5_years_is_2_weeks(self) -> None:
        """4.99 years of service: still 2 weeks notice."""
        inp = NoticePeriodInput(years_of_service=4.99, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 2

    def test_exactly_5_years_is_4_weeks(self) -> None:
        """Exactly 5 years of service: 4 weeks notice."""
        inp = NoticePeriodInput(years_of_service=5.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 4
        assert result.notice_period_weeks == 4

    def test_10_years_is_4_weeks(self) -> None:
        """10 years of service: still 4 weeks notice (max tier)."""
        inp = NoticePeriodInput(years_of_service=10.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 4

    def test_30_years_is_4_weeks(self) -> None:
        """30 years of service: 4 weeks notice (no higher tier)."""
        inp = NoticePeriodInput(years_of_service=30.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 4


class TestContractualOverride:
    """Test contractual notice period override logic."""

    def test_contractual_overrides_when_higher(self) -> None:
        """Contractual notice replaces statutory when >= statutory minimum."""
        inp = NoticePeriodInput(
            years_of_service=1.0,
            monthly_salary=5000.0,
            contractual_notice_weeks=4,
        )
        result = calculate_notice_period(inp)
        # Statutory minimum is 1 week, contractual is 4 weeks (higher)
        assert result.notice_period_weeks == 4
        assert result.source == "contractual"
        assert result.statutory_minimum_weeks == 1

    def test_contractual_equal_to_statutory_uses_contractual(self) -> None:
        """When contractual exactly equals statutory, contractual source is used."""
        inp = NoticePeriodInput(
            years_of_service=3.0,
            monthly_salary=5000.0,
            contractual_notice_weeks=2,  # Same as statutory for 2-5 years
        )
        result = calculate_notice_period(inp)
        assert result.notice_period_weeks == 2
        assert result.source == "contractual"

    def test_contractual_below_statutory_uses_statutory(self) -> None:
        """When contractual is below statutory, statutory minimum applies."""
        inp = NoticePeriodInput(
            years_of_service=6.0,
            monthly_salary=5000.0,
            contractual_notice_weeks=2,  # Below 4-week statutory for 5+ years
        )
        result = calculate_notice_period(inp)
        assert result.notice_period_weeks == 4
        assert result.source == "statutory"
        assert result.statutory_minimum_weeks == 4

    def test_no_contractual_uses_statutory(self) -> None:
        """When contractual notice is None, statutory applies."""
        inp = NoticePeriodInput(
            years_of_service=3.0,
            monthly_salary=5000.0,
            contractual_notice_weeks=None,
        )
        result = calculate_notice_period(inp)
        assert result.source == "statutory"

    def test_contractual_zero_weeks_uses_statutory(self) -> None:
        """Zero contractual weeks should fall back to statutory (0 < statutory)."""
        inp = NoticePeriodInput(
            years_of_service=3.0,
            monthly_salary=5000.0,
            contractual_notice_weeks=0,
        )
        result = calculate_notice_period(inp)
        # 0 < 2 (statutory), so statutory applies
        assert result.notice_period_weeks == 2
        assert result.source == "statutory"


class TestSalaryInLieu:
    """Test salary-in-lieu calculation."""

    def test_basic_salary_in_lieu(self) -> None:
        """Salary in lieu = (monthly_salary / 4) * notice_weeks."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=8000.0)
        result = calculate_notice_period(inp)
        # 2 weeks statutory, weekly salary = 8000/4 = 2000
        assert result.salary_in_lieu == 4000.0  # 2000 * 2

    def test_salary_in_lieu_4_weeks(self) -> None:
        """4 weeks salary in lieu = one full month's salary."""
        inp = NoticePeriodInput(years_of_service=6.0, monthly_salary=6000.0)
        result = calculate_notice_period(inp)
        # 4 weeks, weekly = 6000/4 = 1500, total = 1500 * 4 = 6000
        assert result.salary_in_lieu == 6000.0

    def test_salary_in_lieu_1_week(self) -> None:
        """1 week salary in lieu = quarter of monthly salary."""
        inp = NoticePeriodInput(years_of_service=1.0, monthly_salary=4000.0)
        result = calculate_notice_period(inp)
        assert result.salary_in_lieu == 1000.0  # 4000/4 * 1

    def test_salary_in_lieu_with_contractual(self) -> None:
        """Salary in lieu uses the applicable notice period, not just statutory."""
        inp = NoticePeriodInput(
            years_of_service=1.0,
            monthly_salary=8000.0,
            contractual_notice_weeks=8,
        )
        result = calculate_notice_period(inp)
        # 8 weeks contractual, weekly = 8000/4 = 2000
        assert result.salary_in_lieu == 16000.0  # 2000 * 8

    def test_salary_in_lieu_rounded_to_two_decimals(self) -> None:
        """Salary in lieu should be rounded to 2 decimal places."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=3333.0)
        result = calculate_notice_period(inp)
        # weekly = 3333/4 = 833.25, * 2 weeks = 1666.50
        assert result.salary_in_lieu == 1666.50


class TestTerminatingParty:
    """Test that who_terminates does not affect the calculation.

    The EA s10 notice period is the same regardless of who terminates.
    The calculator accepts this field for context but the output should
    be identical for employer and employee.
    """

    def test_employer_termination(self) -> None:
        """Employer termination uses same notice period."""
        inp = NoticePeriodInput(
            years_of_service=3.0, monthly_salary=5000.0, who_terminates="employer"
        )
        result = calculate_notice_period(inp)
        assert result.notice_period_weeks == 2

    def test_employee_termination_same_period(self) -> None:
        """Employee termination uses same notice period as employer."""
        inp_employer = NoticePeriodInput(
            years_of_service=3.0, monthly_salary=5000.0, who_terminates="employer"
        )
        inp_employee = NoticePeriodInput(
            years_of_service=3.0, monthly_salary=5000.0, who_terminates="employee"
        )
        result_employer = calculate_notice_period(inp_employer)
        result_employee = calculate_notice_period(inp_employee)
        assert result_employer.notice_period_weeks == result_employee.notice_period_weeks
        assert result_employer.salary_in_lieu == result_employee.salary_in_lieu


class TestExplanation:
    """Test explanation string content."""

    def test_short_service_explanation_mentions_26_weeks(self) -> None:
        """Short service explanation should reference 26 weeks / EA s10(3)."""
        inp = NoticePeriodInput(years_of_service=0.3, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert "26 weeks" in result.explanation

    def test_mid_service_explanation_mentions_2_years(self) -> None:
        """Mid service explanation should reference the 2 to <5 year tier."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert "2" in result.explanation and "5" in result.explanation

    def test_long_service_explanation_mentions_5_plus(self) -> None:
        """Long service explanation should reference the 5+ year tier."""
        inp = NoticePeriodInput(years_of_service=6.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert "5+" in result.explanation

    def test_explanation_mentions_source(self) -> None:
        """Explanation should state whether the period is statutory or contractual."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.source in result.explanation

    def test_explanation_mentions_salary_in_lieu(self) -> None:
        """Explanation should reference EA s11 salary in lieu."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert "salary in lieu" in result.explanation.lower()


class TestEdgeCases:
    """Test boundary conditions and edge cases."""

    def test_zero_service_years(self) -> None:
        """Zero years of service should get 1 week notice."""
        inp = NoticePeriodInput(years_of_service=0.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 1
        assert result.notice_period_weeks == 1

    def test_very_long_service(self) -> None:
        """40 years of service: still 4 weeks (no escalation beyond 5+ tier)."""
        inp = NoticePeriodInput(years_of_service=40.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 4

    def test_fractional_service_years(self) -> None:
        """Fractional years should be handled correctly at boundaries."""
        # 2.5 years is in the 2 to <5 tier
        inp = NoticePeriodInput(years_of_service=2.5, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        assert result.statutory_minimum_weeks == 2

    def test_zero_salary_produces_zero_in_lieu(self) -> None:
        """Zero salary should produce $0 salary in lieu."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=0.0)
        result = calculate_notice_period(inp)
        assert result.salary_in_lieu == 0.0

    def test_result_is_frozen_dataclass(self) -> None:
        """Result should be immutable (frozen dataclass)."""
        inp = NoticePeriodInput(years_of_service=3.0, monthly_salary=5000.0)
        result = calculate_notice_period(inp)
        with pytest.raises(AttributeError):
            result.notice_period_weeks = 10  # type: ignore[misc]
