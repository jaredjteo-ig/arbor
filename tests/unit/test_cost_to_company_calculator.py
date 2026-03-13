"""Unit tests for Cost-to-Company Calculator.

Covers total employment cost calculation for Singapore including:
- CPF employer contributions by citizenship tier and age band
- Skills Development Levy (SDL): 0.25% rate, $2 min, $11.25 max
- Foreign worker levy by pass type (SP $550, WP $450)
- WICA insurance estimate (foreign workers only)
- Total monthly/annual cost arithmetic
- Breakdown dictionary completeness
"""

from __future__ import annotations

import pytest

from hr_advisory.workflows.calculators.cost_to_company_calculator import (
    CostToCompanyInput,
    CostToCompanyResult,
    calculate_cost_to_company,
)
from hr_advisory.workflows.calculators.cpf_calculator import CPF_RATE_TABLE


# ---------------------------------------------------------------------------
# Constants (mirrored from source for assertion clarity)
# ---------------------------------------------------------------------------
SDL_RATE = 0.0025
SDL_MIN = 2.0
SDL_MAX = 11.25
LEVY_SP = 550.0
LEVY_WP = 450.0
WICA_MONTHLY = 15.0


class TestSDLCalculation:
    """Test Skills Development Levy calculation."""

    def test_sdl_at_minimum(self) -> None:
        """Very low salary should produce the $2 minimum SDL."""
        # 0.25% of $100 = $0.25, which is below $2 min
        inp = CostToCompanyInput(monthly_salary=100.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.sdl == SDL_MIN

    def test_sdl_at_standard_rate(self) -> None:
        """Mid-range salary should use the 0.25% rate."""
        # 0.25% of $3,000 = $7.50 (between $2 and $11.25)
        inp = CostToCompanyInput(monthly_salary=3000.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.sdl == 7.50

    def test_sdl_at_maximum(self) -> None:
        """High salary should be capped at $11.25."""
        # 0.25% of $10,000 = $25.00, which exceeds $11.25 max
        inp = CostToCompanyInput(monthly_salary=10000.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.sdl == SDL_MAX

    def test_sdl_exactly_at_lower_boundary(self) -> None:
        """Salary of $800 should produce exactly $2.00 (0.25% * 800 = 2.00)."""
        inp = CostToCompanyInput(monthly_salary=800.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.sdl == 2.0

    def test_sdl_exactly_at_upper_boundary(self) -> None:
        """Salary of $4,500 should produce exactly $11.25 (0.25% * 4500 = 11.25)."""
        inp = CostToCompanyInput(monthly_salary=4500.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.sdl == 11.25

    def test_sdl_just_below_lower_boundary(self) -> None:
        """Salary of $799 should still produce $2.00 (min applies)."""
        inp = CostToCompanyInput(monthly_salary=799.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.sdl == SDL_MIN

    def test_sdl_just_above_upper_boundary(self) -> None:
        """Salary of $4,501 should cap at $11.25."""
        inp = CostToCompanyInput(monthly_salary=4501.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.sdl == SDL_MAX


class TestCPFEmployerContribution:
    """Test CPF employer contribution rates by citizenship and age."""

    def test_sc_below_55_full_rate(self) -> None:
        """Singapore Citizen below 55 gets 17% employer CPF."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.17, 2)

    def test_sc_age_55_to_59(self) -> None:
        """SC aged 55-59 gets 14.5% employer CPF."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=56)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.145, 2)

    def test_sc_age_60_to_64(self) -> None:
        """SC aged 60-64 gets 11% employer CPF."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=62)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.11, 2)

    def test_sc_age_65_to_69(self) -> None:
        """SC aged 65-69 gets 7.5% employer CPF."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=67)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.075, 2)

    def test_sc_age_70_plus(self) -> None:
        """SC aged 70+ gets 5% employer CPF."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=71)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.05, 2)

    def test_pr_year_1(self) -> None:
        """PR year 1 below 55 gets 4% employer CPF."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="pr", age=30, pr_year=1)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.04, 2)

    def test_pr_year_2(self) -> None:
        """PR year 2 below 55 gets 9% employer CPF."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="pr", age=30, pr_year=2)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.09, 2)

    def test_pr_year_3_plus_same_as_sc(self) -> None:
        """PR year 3+ should match SC full rate (17% below 55)."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="pr", age=30, pr_year=3)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * 0.17, 2)

    def test_ep_no_cpf(self) -> None:
        """EP holders have no CPF contribution."""
        inp = CostToCompanyInput(monthly_salary=8000.0, citizenship="ep")
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == 0.0

    def test_sp_no_cpf(self) -> None:
        """SP holders have no CPF contribution."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sp")
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == 0.0

    def test_wp_no_cpf(self) -> None:
        """WP holders have no CPF contribution."""
        inp = CostToCompanyInput(monthly_salary=2000.0, citizenship="wp")
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == 0.0


class TestCPFAgeBoundaries:
    """Test exact age boundaries for CPF rate bands.

    The bands use strict '<' comparisons:
    - Below 55: age < 55 (i.e., 54 and below)
    - 55-59:    55 <= age < 60
    - 60-64:    60 <= age < 65
    - 65-69:    65 <= age < 70
    - 70+:      age >= 70
    """

    @pytest.mark.parametrize(
        "age,expected_rate",
        [
            (54, 0.17),  # Last year in "55_below" band
            (55, 0.145),  # First year in "55_60" band
            (59, 0.145),  # Last year in "55_60" band
            (60, 0.11),  # First year in "60_65" band
            (64, 0.11),  # Last year in "60_65" band
            (65, 0.075),  # First year in "65_70" band
            (69, 0.075),  # Last year in "65_70" band
            (70, 0.05),  # First year in "above_70" band
        ],
    )
    def test_sc_age_boundary(self, age: int, expected_rate: float) -> None:
        """Verify correct CPF rate at each age boundary for SC."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=age)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == round(5000.0 * expected_rate, 2)


class TestForeignWorkerLevy:
    """Test foreign worker levy for different pass types."""

    def test_sp_levy(self) -> None:
        """S Pass holders incur $550/month levy."""
        inp = CostToCompanyInput(monthly_salary=3000.0, citizenship="sp", pass_type="sp")
        result = calculate_cost_to_company(inp)
        assert result.levy == LEVY_SP

    def test_wp_levy(self) -> None:
        """Work Permit holders incur $450/month levy."""
        inp = CostToCompanyInput(monthly_salary=2000.0, citizenship="wp", pass_type="wp")
        result = calculate_cost_to_company(inp)
        assert result.levy == LEVY_WP

    def test_ep_no_levy(self) -> None:
        """EP holders have no foreign worker levy."""
        inp = CostToCompanyInput(monthly_salary=8000.0, citizenship="ep", pass_type="ep")
        result = calculate_cost_to_company(inp)
        assert result.levy == 0.0

    def test_sc_no_levy(self) -> None:
        """Singapore Citizens have no levy."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.levy == 0.0

    def test_pr_no_levy(self) -> None:
        """PRs have no levy."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="pr", pr_year=3)
        result = calculate_cost_to_company(inp)
        assert result.levy == 0.0

    def test_citizenship_used_as_pass_type_when_pass_type_empty(self) -> None:
        """When pass_type is empty, citizenship is used as effective pass type."""
        inp = CostToCompanyInput(monthly_salary=2000.0, citizenship="wp", pass_type="")
        result = calculate_cost_to_company(inp)
        assert result.levy == LEVY_WP


class TestWICAInsurance:
    """Test WICA insurance estimate."""

    def test_foreign_worker_gets_wica(self) -> None:
        """Foreign workers (EP, SP, WP) get WICA insurance estimate."""
        for cit in ["ep", "sp", "wp"]:
            inp = CostToCompanyInput(monthly_salary=3000.0, citizenship=cit)
            result = calculate_cost_to_company(inp)
            assert result.insurance_estimate == WICA_MONTHLY, f"Failed for {cit}"

    def test_sc_no_wica(self) -> None:
        """SC employees do not get WICA estimate."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc")
        result = calculate_cost_to_company(inp)
        assert result.insurance_estimate == 0.0

    def test_pr_no_wica(self) -> None:
        """PR employees do not get WICA estimate."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="pr", pr_year=3)
        result = calculate_cost_to_company(inp)
        assert result.insurance_estimate == 0.0


class TestTotalCostArithmetic:
    """Test that total cost = base + cpf + levy + sdl + insurance."""

    def test_sc_total_monthly(self) -> None:
        """SC total = salary + CPF employer + SDL (no levy, no insurance)."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        sdl = round(min(max(5000.0 * SDL_RATE, SDL_MIN), SDL_MAX), 2)  # $11.25 (capped)
        expected = 5000.0 + round(5000.0 * 0.17, 2) + sdl + 0.0 + 0.0
        assert result.total_monthly_cost == round(expected, 2)

    def test_wp_total_monthly(self) -> None:
        """WP total = salary + levy + SDL + WICA (no CPF)."""
        inp = CostToCompanyInput(monthly_salary=2000.0, citizenship="wp", pass_type="wp")
        result = calculate_cost_to_company(inp)
        sdl = round(min(max(2000.0 * SDL_RATE, SDL_MIN), SDL_MAX), 2)
        expected = 2000.0 + 0.0 + LEVY_WP + sdl + WICA_MONTHLY
        assert result.total_monthly_cost == round(expected, 2)

    def test_annual_is_twelve_times_monthly(self) -> None:
        """Annual cost should be exactly 12 * monthly cost."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        assert result.total_annual_cost == round(result.total_monthly_cost * 12, 2)

    def test_total_equals_sum_of_components(self) -> None:
        """Total monthly must equal the sum of all individual components."""
        inp = CostToCompanyInput(monthly_salary=4000.0, citizenship="pr", age=45, pr_year=2)
        result = calculate_cost_to_company(inp)
        component_sum = (
            result.monthly_salary
            + result.cpf_employer
            + result.levy
            + result.sdl
            + result.insurance_estimate
        )
        assert result.total_monthly_cost == round(component_sum, 2)


class TestBreakdownDictionary:
    """Test the breakdown dictionary completeness and accuracy."""

    def test_breakdown_has_all_keys(self) -> None:
        """Breakdown dict should contain all cost component keys."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        expected_keys = {"base_salary", "cpf_employer", "levy", "sdl", "insurance_estimate"}
        assert set(result.breakdown.keys()) == expected_keys

    def test_breakdown_values_match_result_fields(self) -> None:
        """Breakdown values should match the corresponding result fields."""
        inp = CostToCompanyInput(monthly_salary=4000.0, citizenship="sp", pass_type="sp")
        result = calculate_cost_to_company(inp)
        assert result.breakdown["base_salary"] == result.monthly_salary
        assert result.breakdown["cpf_employer"] == result.cpf_employer
        assert result.breakdown["levy"] == result.levy
        assert result.breakdown["sdl"] == result.sdl
        assert result.breakdown["insurance_estimate"] == result.insurance_estimate


class TestCPFRateTableConsistency:
    """Verify cost-to-company CPF rates match the canonical CPF rate table."""

    @pytest.mark.parametrize(
        "citizenship,age,pr_year,expected_tier",
        [
            ("sc", 30, 3, "sc_full"),
            ("sc", 56, 3, "sc_full"),
            ("pr", 30, 1, "pr_year1"),
            ("pr", 30, 2, "pr_year2"),
            ("pr", 30, 3, "pr_year3_plus"),
        ],
    )
    def test_employer_rate_matches_cpf_table(
        self, citizenship: str, age: int, pr_year: int, expected_tier: str
    ) -> None:
        """Cost-to-company calculator must use the same rates as the CPF table."""
        inp = CostToCompanyInput(
            monthly_salary=5000.0, citizenship=citizenship, age=age, pr_year=pr_year
        )
        result = calculate_cost_to_company(inp)

        # Determine expected age band
        if age < 55:
            band = "55_below"
        elif age < 60:
            band = "55_60"
        elif age < 65:
            band = "60_65"
        elif age < 70:
            band = "65_70"
        else:
            band = "above_70"

        expected_employer_rate, _ = CPF_RATE_TABLE[(expected_tier, band)]
        expected_cpf = round(5000.0 * expected_employer_rate, 2)
        assert result.cpf_employer == expected_cpf


class TestExplanation:
    """Test explanation string content."""

    def test_sc_explanation_contains_cpf(self) -> None:
        """SC explanation should mention CPF contribution."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        assert "CPF" in result.explanation

    def test_sp_explanation_contains_levy(self) -> None:
        """SP explanation should mention foreign worker levy."""
        inp = CostToCompanyInput(monthly_salary=3000.0, citizenship="sp", pass_type="sp")
        result = calculate_cost_to_company(inp)
        assert "levy" in result.explanation.lower()

    def test_explanation_contains_total(self) -> None:
        """Explanation should include total monthly and annual cost."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        assert "Total monthly" in result.explanation
        assert "Total annual" in result.explanation


class TestEdgeCases:
    """Test boundary conditions and unusual inputs."""

    def test_zero_salary(self) -> None:
        """Zero salary should still produce valid results (SDL = $2 min)."""
        inp = CostToCompanyInput(monthly_salary=0.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        assert result.cpf_employer == 0.0
        assert result.sdl == SDL_MIN  # Min SDL applies
        assert result.total_monthly_cost == round(0.0 + 0.0 + 0.0 + SDL_MIN + 0.0, 2)

    def test_very_high_salary(self) -> None:
        """Very high salary should cap SDL at $11.25."""
        inp = CostToCompanyInput(monthly_salary=50000.0, citizenship="sc", age=30)
        result = calculate_cost_to_company(inp)
        assert result.sdl == SDL_MAX

    def test_pr_year_defaults_to_3_plus(self) -> None:
        """PR with pr_year > 3 should use year 3+ rates."""
        inp = CostToCompanyInput(monthly_salary=5000.0, citizenship="pr", age=30, pr_year=5)
        result = calculate_cost_to_company(inp)
        # Year 3+ is same as SC full rate: 17%
        assert result.cpf_employer == round(5000.0 * 0.17, 2)
