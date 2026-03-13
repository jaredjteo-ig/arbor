"""Unit tests for Retrenchment Benefit Calculator.

Covers Singapore retrenchment benefit estimation:
- No statutory minimum (Singapore has no mandatory retrenchment benefits)
- Market norms by sector (Tripartite Advisory on Managing Excess Manpower)
- Benefit arithmetic: (monthly_salary / 4) * weeks_per_year * years_of_service
- Sector-specific norms: services (2w), manufacturing (2w), construction (1.5w),
  technology (3w), finance (3w)
- Default norm for unlisted sectors (2 weeks)
- Pro-rata for partial years
"""

from __future__ import annotations

import pytest

from hr_advisory.workflows.calculators.retrenchment_calculator import (
    RetrenchmentInput,
    RetrenchmentResult,
    calculate_retrenchment,
)


class TestStatutoryMinimum:
    """Test that statutory_minimum is always None (Singapore has no mandatory minimum)."""

    def test_no_statutory_minimum(self) -> None:
        """Singapore does not mandate retrenchment benefits."""
        inp = RetrenchmentInput(years_of_service=10.0, monthly_salary=5000.0)
        result = calculate_retrenchment(inp)
        assert result.statutory_minimum is None

    def test_no_statutory_minimum_any_service_length(self) -> None:
        """No statutory minimum regardless of service length."""
        for years in [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]:
            inp = RetrenchmentInput(years_of_service=years, monthly_salary=5000.0)
            result = calculate_retrenchment(inp)
            assert result.statutory_minimum is None, f"Failed for {years} years"


class TestSectorNorms:
    """Test sector-specific market norms for retrenchment benefits."""

    def test_services_sector_2_weeks(self) -> None:
        """Services sector: 2 weeks per year of service."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="services")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 2.0, 2)
        assert result.market_norm_per_year == expected_per_year

    def test_manufacturing_sector_2_weeks(self) -> None:
        """Manufacturing sector: 2 weeks per year of service."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="manufacturing")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 2.0, 2)
        assert result.market_norm_per_year == expected_per_year

    def test_construction_sector_1_5_weeks(self) -> None:
        """Construction sector: 1.5 weeks per year of service."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="construction")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 1.5, 2)
        assert result.market_norm_per_year == expected_per_year

    def test_technology_sector_3_weeks(self) -> None:
        """Technology sector: 3 weeks per year of service."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="technology")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 3.0, 2)
        assert result.market_norm_per_year == expected_per_year

    def test_finance_sector_3_weeks(self) -> None:
        """Finance sector: 3 weeks per year of service."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="finance")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 3.0, 2)
        assert result.market_norm_per_year == expected_per_year

    def test_unknown_sector_uses_default_2_weeks(self) -> None:
        """Unknown sector defaults to 2 weeks per year."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="aerospace")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 2.0, 2)
        assert result.market_norm_per_year == expected_per_year

    def test_empty_sector_uses_default(self) -> None:
        """Empty sector string defaults to 2 weeks per year."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 2.0, 2)
        assert result.market_norm_per_year == expected_per_year

    def test_sector_case_insensitive(self) -> None:
        """Sector lookup should be case-insensitive."""
        inp_lower = RetrenchmentInput(
            years_of_service=5.0, monthly_salary=4000.0, sector="technology"
        )
        inp_upper = RetrenchmentInput(
            years_of_service=5.0, monthly_salary=4000.0, sector="Technology"
        )
        result_lower = calculate_retrenchment(inp_lower)
        result_upper = calculate_retrenchment(inp_upper)
        assert result_lower.market_norm_per_year == result_upper.market_norm_per_year
        assert result_lower.market_norm_total == result_upper.market_norm_total


class TestBenefitArithmetic:
    """Test core benefit calculation: (salary/4) * weeks_per_year * years."""

    def test_basic_calculation(self) -> None:
        """5 years at $4,000/month, services (2 weeks/year)."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="services")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0  # $1,000
        per_year = round(weekly_salary * 2.0, 2)  # $2,000
        total = round(per_year * 5.0, 2)  # $10,000
        assert result.market_norm_per_year == per_year
        assert result.market_norm_total == total

    def test_technology_10_years(self) -> None:
        """10 years at $8,000/month, technology (3 weeks/year)."""
        inp = RetrenchmentInput(years_of_service=10.0, monthly_salary=8000.0, sector="technology")
        result = calculate_retrenchment(inp)
        weekly_salary = 8000.0 / 4.0  # $2,000
        per_year = round(weekly_salary * 3.0, 2)  # $6,000
        total = round(per_year * 10.0, 2)  # $60,000
        assert result.market_norm_per_year == per_year
        assert result.market_norm_total == total

    def test_total_is_per_year_times_years(self) -> None:
        """Total benefit should always equal per_year * years_of_service."""
        inp = RetrenchmentInput(years_of_service=7.0, monthly_salary=6000.0, sector="finance")
        result = calculate_retrenchment(inp)
        assert result.market_norm_total == round(
            result.market_norm_per_year * inp.years_of_service, 2
        )


class TestProRatedPartialYears:
    """Test that partial years are pro-rated (not rounded to completed years)."""

    def test_half_year_service(self) -> None:
        """0.5 years of service should give half of the per-year benefit."""
        inp = RetrenchmentInput(years_of_service=0.5, monthly_salary=4000.0, sector="services")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        per_year = round(weekly_salary * 2.0, 2)
        expected_total = round(per_year * 0.5, 2)
        assert result.market_norm_total == expected_total

    def test_3_point_5_years(self) -> None:
        """3.5 years of service should pro-rate correctly."""
        inp = RetrenchmentInput(years_of_service=3.5, monthly_salary=4000.0, sector="services")
        result = calculate_retrenchment(inp)
        weekly_salary = 4000.0 / 4.0
        per_year = round(weekly_salary * 2.0, 2)
        expected_total = round(per_year * 3.5, 2)
        assert result.market_norm_total == expected_total

    def test_fractional_year(self) -> None:
        """Arbitrary fractional years should work."""
        inp = RetrenchmentInput(years_of_service=2.75, monthly_salary=6000.0, sector="technology")
        result = calculate_retrenchment(inp)
        weekly_salary = 6000.0 / 4.0
        per_year = round(weekly_salary * 3.0, 2)
        expected_total = round(per_year * 2.75, 2)
        assert result.market_norm_total == expected_total


class TestSectorNotes:
    """Test sector_notes field for each recognized sector."""

    def test_services_sector_note(self) -> None:
        inp = RetrenchmentInput(years_of_service=3.0, monthly_salary=4000.0, sector="services")
        result = calculate_retrenchment(inp)
        assert "Services" in result.sector_notes or "services" in result.sector_notes.lower()

    def test_construction_sector_note(self) -> None:
        inp = RetrenchmentInput(years_of_service=3.0, monthly_salary=4000.0, sector="construction")
        result = calculate_retrenchment(inp)
        assert (
            "Construction" in result.sector_notes or "construction" in result.sector_notes.lower()
        )

    def test_technology_sector_note(self) -> None:
        inp = RetrenchmentInput(years_of_service=3.0, monthly_salary=4000.0, sector="technology")
        result = calculate_retrenchment(inp)
        assert "Technology" in result.sector_notes or "technology" in result.sector_notes.lower()

    def test_unknown_sector_gets_general_note(self) -> None:
        inp = RetrenchmentInput(years_of_service=3.0, monthly_salary=4000.0, sector="mining")
        result = calculate_retrenchment(inp)
        assert "General" in result.sector_notes or "general" in result.sector_notes.lower()


class TestExplanation:
    """Test explanation string content."""

    def test_explanation_mentions_no_statutory_minimum(self) -> None:
        """Explanation should clarify there is no statutory minimum."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0)
        result = calculate_retrenchment(inp)
        assert "no" in result.explanation.lower() and "statutory" in result.explanation.lower()

    def test_explanation_mentions_tripartite_advisory(self) -> None:
        """Explanation should reference the Tripartite Advisory."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0)
        result = calculate_retrenchment(inp)
        assert "Tripartite" in result.explanation

    def test_explanation_mentions_2_year_eligibility(self) -> None:
        """Explanation should mention the 2-year general eligibility norm."""
        inp = RetrenchmentInput(years_of_service=1.0, monthly_salary=4000.0)
        result = calculate_retrenchment(inp)
        assert "2 years" in result.explanation

    def test_explanation_shows_calculation(self) -> None:
        """Explanation should contain the estimated benefit amount."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0, sector="services")
        result = calculate_retrenchment(inp)
        assert f"${result.market_norm_total:,.2f}" in result.explanation


class TestEdgeCases:
    """Test boundary conditions and unusual inputs."""

    def test_less_than_2_years_still_calculates(self) -> None:
        """Even if <2 years, the calculator should still produce a benefit estimate.

        The 2-year minimum is a policy guideline, not a calculator restriction.
        The explanation should warn about ineligibility.
        """
        inp = RetrenchmentInput(years_of_service=1.0, monthly_salary=4000.0)
        result = calculate_retrenchment(inp)
        assert result.market_norm_total > 0.0
        assert "2 years" in result.explanation

    def test_zero_service_years(self) -> None:
        """Zero years of service should produce zero benefit."""
        inp = RetrenchmentInput(years_of_service=0.0, monthly_salary=4000.0)
        result = calculate_retrenchment(inp)
        assert result.market_norm_total == 0.0

    def test_very_long_service(self) -> None:
        """30 years of service should calculate correctly with no cap."""
        inp = RetrenchmentInput(years_of_service=30.0, monthly_salary=5000.0, sector="services")
        result = calculate_retrenchment(inp)
        weekly_salary = 5000.0 / 4.0
        per_year = round(weekly_salary * 2.0, 2)
        expected_total = round(per_year * 30.0, 2)
        assert result.market_norm_total == expected_total

    def test_zero_salary(self) -> None:
        """Zero salary should produce zero benefit."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=0.0)
        result = calculate_retrenchment(inp)
        assert result.market_norm_per_year == 0.0
        assert result.market_norm_total == 0.0

    def test_very_high_salary_no_cap(self) -> None:
        """There is no salary cap for retrenchment benefit calculation."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=50000.0, sector="finance")
        result = calculate_retrenchment(inp)
        weekly_salary = 50000.0 / 4.0
        per_year = round(weekly_salary * 3.0, 2)
        expected_total = round(per_year * 5.0, 2)
        assert result.market_norm_total == expected_total

    def test_result_is_frozen_dataclass(self) -> None:
        """Result should be immutable (frozen dataclass)."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=5000.0)
        result = calculate_retrenchment(inp)
        with pytest.raises(AttributeError):
            result.market_norm_total = 999.0  # type: ignore[misc]

    def test_default_sector_is_empty_string(self) -> None:
        """Default sector is empty string, which triggers the default norm."""
        inp = RetrenchmentInput(years_of_service=5.0, monthly_salary=4000.0)
        result = calculate_retrenchment(inp)
        # Default norm is 2 weeks
        weekly_salary = 4000.0 / 4.0
        expected_per_year = round(weekly_salary * 2.0, 2)
        assert result.market_norm_per_year == expected_per_year
