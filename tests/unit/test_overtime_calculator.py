"""Unit tests for Overtime Calculator.

Covers EA Part IV provisions for Singapore employment law:
- Salary eligibility thresholds for workmen vs non-workmen
- OT rate multipliers by day type (normal, rest day, public holiday)
- Monthly-to-hourly rate conversion (salary / 208)
- OT salary cap at $2,600 for calculation purposes (EA s38(6))
- Max OT hours warning at 72h/month (EA s38)
"""

from __future__ import annotations

import pytest

from hr_advisory.workflows.calculators.overtime_calculator import (
    OvertimeInput,
    OvertimeResult,
    calculate_overtime,
)


# ---------------------------------------------------------------------------
# Constants (mirrored from source for assertion clarity)
# ---------------------------------------------------------------------------
NON_WORKMAN_SALARY_CEILING = 2600.0
MAX_OT_HOURS_PER_MONTH = 72.0
OT_SALARY_CAP = 2600.0


class TestPartIVEligibility:
    """Test EA Part IV eligibility determination."""

    def test_workman_always_eligible_regardless_of_salary(self) -> None:
        """Workmen are covered by Part IV at any salary level."""
        inp = OvertimeInput(monthly_salary=10000.0, is_workman=True, hours_worked=50.0)
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is True

    def test_non_workman_eligible_below_ceiling(self) -> None:
        """Non-workmen earning below $2,600 are Part IV eligible."""
        inp = OvertimeInput(monthly_salary=2000.0, is_workman=False, hours_worked=50.0)
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is True

    def test_non_workman_eligible_at_exactly_ceiling(self) -> None:
        """Non-workmen earning exactly $2,600 are Part IV eligible (<=)."""
        inp = OvertimeInput(monthly_salary=2600.0, is_workman=False, hours_worked=50.0)
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is True

    def test_non_workman_ineligible_above_ceiling(self) -> None:
        """Non-workmen earning above $2,600 are NOT Part IV eligible."""
        inp = OvertimeInput(monthly_salary=2600.01, is_workman=False, hours_worked=50.0)
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is False

    def test_ineligible_result_zeroes_all_fields(self) -> None:
        """When ineligible, all numeric OT fields should be zero."""
        inp = OvertimeInput(monthly_salary=5000.0, is_workman=False, hours_worked=80.0)
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is False
        assert result.ot_hours == 0.0
        assert result.hourly_basic_rate == 0.0
        assert result.ot_rate_multiplier == 0.0
        assert result.ot_pay == 0.0
        assert result.warnings == []

    def test_ineligible_explanation_mentions_salary_and_threshold(self) -> None:
        """Ineligible explanation should state the employee's salary and the threshold."""
        inp = OvertimeInput(monthly_salary=3000.0, is_workman=False)
        result = calculate_overtime(inp)
        assert "$3,000" in result.explanation
        assert "$2,600" in result.explanation
        assert "not a workman" in result.explanation


class TestHourlyRateConversion:
    """Test monthly-to-hourly rate conversion: salary / 208."""

    def test_standard_salary_hourly_rate(self) -> None:
        """$2,080 monthly should yield $10.00/hour (2080/208)."""
        inp = OvertimeInput(monthly_salary=2080.0, is_workman=True, hours_worked=50.0)
        result = calculate_overtime(inp)
        assert result.hourly_basic_rate == 10.0

    def test_ceiling_salary_hourly_rate(self) -> None:
        """$2,600 monthly should yield $12.50/hour (2600/208)."""
        inp = OvertimeInput(monthly_salary=2600.0, is_workman=True, hours_worked=50.0)
        result = calculate_overtime(inp)
        assert result.hourly_basic_rate == 12.50

    def test_salary_above_cap_uses_capped_rate(self) -> None:
        """When salary exceeds OT cap ($2,600), hourly rate uses capped salary."""
        inp = OvertimeInput(monthly_salary=4000.0, is_workman=True, hours_worked=50.0)
        result = calculate_overtime(inp)
        # Hourly rate should be based on $2,600, not $4,000
        expected_rate = round(2600.0 / 208.0, 2)
        assert result.hourly_basic_rate == expected_rate


class TestOTRateMultipliers:
    """Test OT rate multipliers for different day types."""

    def test_normal_day_multiplier_is_1_5x(self) -> None:
        """Normal weekday OT is 1.5x per EA s37."""
        inp = OvertimeInput(
            monthly_salary=2080.0, is_workman=True, hours_worked=50.0, day_type="normal"
        )
        result = calculate_overtime(inp)
        assert result.ot_rate_multiplier == 1.5

    def test_rest_day_multiplier_is_2x(self) -> None:
        """Rest day OT is 2.0x."""
        inp = OvertimeInput(
            monthly_salary=2080.0, is_workman=True, hours_worked=50.0, day_type="rest_day"
        )
        result = calculate_overtime(inp)
        assert result.ot_rate_multiplier == 2.0

    def test_public_holiday_multiplier_is_2x(self) -> None:
        """Public holiday OT is 2.0x."""
        inp = OvertimeInput(
            monthly_salary=2080.0, is_workman=True, hours_worked=50.0, day_type="public_holiday"
        )
        result = calculate_overtime(inp)
        assert result.ot_rate_multiplier == 2.0

    def test_unknown_day_type_defaults_to_1_5x(self) -> None:
        """Unknown day type should default to 1.5x (safe fallback)."""
        inp = OvertimeInput(
            monthly_salary=2080.0, is_workman=True, hours_worked=50.0, day_type="unknown"
        )
        result = calculate_overtime(inp)
        assert result.ot_rate_multiplier == 1.5


class TestOTPayCalculation:
    """Test the core OT pay arithmetic."""

    def test_basic_normal_day_ot_pay(self) -> None:
        """6 hours OT at $10/hr * 1.5x = $90.00."""
        inp = OvertimeInput(
            monthly_salary=2080.0,
            is_workman=True,
            hours_worked=50.0,
            normal_hours=44.0,
            day_type="normal",
        )
        result = calculate_overtime(inp)
        assert result.ot_hours == 6.0
        assert result.hourly_basic_rate == 10.0
        assert result.ot_pay == 90.0  # 6 * 10.0 * 1.5

    def test_rest_day_ot_pay(self) -> None:
        """10 hours OT at $12.50/hr * 2.0x = $250.00."""
        inp = OvertimeInput(
            monthly_salary=2600.0,
            is_workman=True,
            hours_worked=54.0,
            normal_hours=44.0,
            day_type="rest_day",
        )
        result = calculate_overtime(inp)
        assert result.ot_hours == 10.0
        assert result.ot_pay == 250.0  # 10 * 12.50 * 2.0

    def test_no_ot_hours_produces_zero_pay(self) -> None:
        """If hours worked <= normal hours, OT pay is zero."""
        inp = OvertimeInput(
            monthly_salary=2080.0, is_workman=True, hours_worked=44.0, normal_hours=44.0
        )
        result = calculate_overtime(inp)
        assert result.ot_hours == 0.0
        assert result.ot_pay == 0.0

    def test_hours_below_normal_produces_zero_ot(self) -> None:
        """Hours below normal hours should yield zero OT, not negative."""
        inp = OvertimeInput(
            monthly_salary=2080.0, is_workman=True, hours_worked=30.0, normal_hours=44.0
        )
        result = calculate_overtime(inp)
        assert result.ot_hours == 0.0
        assert result.ot_pay == 0.0

    def test_salary_cap_applied_in_ot_calculation(self) -> None:
        """Workman earning $4,000 has OT calculated on capped $2,600."""
        inp = OvertimeInput(
            monthly_salary=4000.0,
            is_workman=True,
            hours_worked=54.0,
            normal_hours=44.0,
            day_type="normal",
        )
        result = calculate_overtime(inp)
        # Hourly rate = 2600/208 = 12.50
        # OT pay = 10 * 12.50 * 1.5 = 187.50
        assert result.hourly_basic_rate == 12.50
        assert result.ot_pay == 187.50

    def test_ot_pay_is_rounded_to_two_decimals(self) -> None:
        """OT pay should be rounded to 2 decimal places."""
        # Use a salary that produces a non-terminating hourly rate
        inp = OvertimeInput(
            monthly_salary=1000.0,
            is_workman=True,
            hours_worked=47.0,
            normal_hours=44.0,
            day_type="normal",
        )
        result = calculate_overtime(inp)
        # 1000/208 = 4.807692...
        # 3 * 4.807692... * 1.5 = 21.634615...
        # Should be rounded to 2 decimals
        assert result.ot_pay == round(3.0 * (1000.0 / 208.0) * 1.5, 2)

    def test_fractional_ot_hours(self) -> None:
        """Fractional OT hours should be calculated correctly."""
        inp = OvertimeInput(
            monthly_salary=2080.0,
            is_workman=True,
            hours_worked=46.5,
            normal_hours=44.0,
            day_type="normal",
        )
        result = calculate_overtime(inp)
        assert result.ot_hours == 2.5
        assert result.ot_pay == round(2.5 * 10.0 * 1.5, 2)


class TestOTHoursWarnings:
    """Test EA s38 monthly OT limit warnings."""

    def test_no_warning_within_limit(self) -> None:
        """No warning when OT hours are within 72-hour limit."""
        inp = OvertimeInput(
            monthly_salary=2080.0,
            is_workman=True,
            hours_worked=44.0 + 72.0,
            normal_hours=44.0,
        )
        result = calculate_overtime(inp)
        assert result.ot_hours == 72.0
        assert not any("exceed" in w.lower() for w in result.warnings)

    def test_warning_when_exceeding_limit(self) -> None:
        """Warning when OT hours exceed 72-hour monthly limit."""
        inp = OvertimeInput(
            monthly_salary=2080.0,
            is_workman=True,
            hours_worked=44.0 + 73.0,
            normal_hours=44.0,
        )
        result = calculate_overtime(inp)
        assert result.ot_hours == 73.0
        assert len(result.warnings) >= 1
        assert any("72" in w and "MOM" in w for w in result.warnings)

    def test_salary_cap_warning_for_high_earners(self) -> None:
        """Warning when salary exceeds the OT calculation cap of $2,600."""
        inp = OvertimeInput(
            monthly_salary=3000.0,
            is_workman=True,
            hours_worked=50.0,
            normal_hours=44.0,
        )
        result = calculate_overtime(inp)
        assert any("cap" in w.lower() or "$2,600" in w for w in result.warnings)

    def test_no_salary_cap_warning_at_cap(self) -> None:
        """No salary cap warning when salary is at exactly $2,600."""
        inp = OvertimeInput(
            monthly_salary=2600.0,
            is_workman=True,
            hours_worked=50.0,
            normal_hours=44.0,
        )
        result = calculate_overtime(inp)
        assert not any("cap" in w.lower() for w in result.warnings)

    def test_both_warnings_can_appear_together(self) -> None:
        """Both OT hours and salary cap warnings can appear simultaneously."""
        inp = OvertimeInput(
            monthly_salary=3000.0,
            is_workman=True,
            hours_worked=44.0 + 80.0,
            normal_hours=44.0,
        )
        result = calculate_overtime(inp)
        assert len(result.warnings) == 2


class TestExplanation:
    """Test that explanations contain relevant information."""

    def test_eligible_explanation_contains_key_details(self) -> None:
        """Eligible explanation should include rate, multiplier, and pay."""
        inp = OvertimeInput(
            monthly_salary=2080.0,
            is_workman=True,
            hours_worked=50.0,
            day_type="normal",
        )
        result = calculate_overtime(inp)
        assert "1.5" in result.explanation
        assert "$10.00" in result.explanation
        assert "normal" in result.explanation


class TestEdgeCases:
    """Test boundary conditions and edge cases."""

    def test_zero_hours_worked(self) -> None:
        """Zero hours worked should produce zero OT."""
        inp = OvertimeInput(monthly_salary=2080.0, is_workman=True, hours_worked=0.0)
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is True
        assert result.ot_hours == 0.0
        assert result.ot_pay == 0.0

    def test_very_low_salary(self) -> None:
        """Very low salary should still calculate correctly."""
        inp = OvertimeInput(
            monthly_salary=100.0, is_workman=True, hours_worked=50.0, normal_hours=44.0
        )
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is True
        expected_rate = round(100.0 / 208.0, 2)
        assert result.hourly_basic_rate == expected_rate

    def test_default_input_values(self) -> None:
        """Default input values should produce a valid result."""
        inp = OvertimeInput(monthly_salary=2000.0)
        result = calculate_overtime(inp)
        assert isinstance(result, OvertimeResult)
        assert result.is_part_iv_eligible is False or result.is_part_iv_eligible is True

    def test_non_workman_at_exactly_one_cent_above_ceiling(self) -> None:
        """$2,600.01 should make non-workman ineligible."""
        inp = OvertimeInput(monthly_salary=2600.01, is_workman=False, hours_worked=50.0)
        result = calculate_overtime(inp)
        assert result.is_part_iv_eligible is False
