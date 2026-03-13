"""Tests for CPF contribution calculator.

Tests both the pure calculator functions and the Kailash workflow wrapper.
Includes tests against CPF Board published examples.
"""

import pytest

from hr_advisory.workflows.calculators.cpf_calculator import (
    CPFInput,
    CPFResult,
    CPF_RATE_TABLE,
    OW_CEILING_MONTHLY,
    AW_CEILING_ANNUAL,
    calculate_cpf_contributions,
)


# ── Pure function tests ─────────────────────────────────────────────


class TestCPFRateTable:
    """Verify the rate table covers all required combinations."""

    def test_sc_all_age_bands(self):
        for band in ("55_below", "55_60", "60_65", "65_70", "above_70"):
            assert ("sc_full", band) in CPF_RATE_TABLE

    def test_pr_year1_all_age_bands(self):
        for band in ("55_below", "55_60", "60_65", "65_70", "above_70"):
            assert ("pr_year1", band) in CPF_RATE_TABLE

    def test_pr_year2_all_age_bands(self):
        for band in ("55_below", "55_60", "60_65", "65_70", "above_70"):
            assert ("pr_year2", band) in CPF_RATE_TABLE

    def test_pr_year3_plus_all_age_bands(self):
        for band in ("55_below", "55_60", "60_65", "65_70", "above_70"):
            assert ("pr_year3_plus", band) in CPF_RATE_TABLE

    def test_sc_below_55_rates(self):
        er, ee = CPF_RATE_TABLE[("sc_full", "55_below")]
        assert er == 0.17
        assert ee == 0.20

    def test_sc_55_60_rates(self):
        er, ee = CPF_RATE_TABLE[("sc_full", "55_60")]
        assert er == 0.145
        assert ee == 0.15

    def test_pr_year1_below_55(self):
        er, ee = CPF_RATE_TABLE[("pr_year1", "55_below")]
        assert er == 0.04
        assert ee == 0.05

    def test_pr_year3_same_as_sc(self):
        """PR year 3+ should have same rates as SC."""
        for band in ("55_below", "55_60", "60_65", "65_70", "above_70"):
            sc_rates = CPF_RATE_TABLE[("sc_full", band)]
            pr3_rates = CPF_RATE_TABLE[("pr_year3_plus", band)]
            assert sc_rates == pr3_rates, f"PR3+ rates differ from SC for {band}"


class TestCPFCalculatorBasic:
    """Basic CPF calculation scenarios."""

    def test_sc_below_55_standard_salary(self):
        """SC employee, age 30, $5,000 OW."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
            )
        )
        assert result.cpf_applicable is True
        assert result.cpf_tier == "sc_full"
        assert result.age_band == "55_below"
        assert result.employer_rate == 0.17
        assert result.employee_rate == 0.20
        assert result.employer_contribution == round(5000 * 0.17)  # $850
        assert result.employee_contribution == round(5000 * 0.20)  # $1000
        assert result.total_contribution == 850 + 1000  # $1850

    def test_sc_age_57(self):
        """SC employee, age 57, $5,000 OW."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=57,
                monthly_ow=5000.0,
            )
        )
        assert result.age_band == "55_60"
        assert result.employer_rate == 0.145
        assert result.employee_rate == 0.15
        assert result.employer_contribution == round(5000 * 0.145)  # $725
        assert result.employee_contribution == round(5000 * 0.15)  # $750

    def test_sc_age_62(self):
        """SC employee, age 62."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=62,
                monthly_ow=4000.0,
            )
        )
        assert result.age_band == "60_65"
        assert result.employer_rate == 0.11
        assert result.employee_rate == 0.095

    def test_sc_age_67(self):
        """SC employee, age 67."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=67,
                monthly_ow=3000.0,
            )
        )
        assert result.age_band == "65_70"
        assert result.employer_rate == 0.075
        assert result.employee_rate == 0.07

    def test_sc_age_72(self):
        """SC employee, age 72."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=72,
                monthly_ow=2000.0,
            )
        )
        assert result.age_band == "above_70"
        assert result.employer_rate == 0.05
        assert result.employee_rate == 0.05

    def test_foreigner_no_cpf(self):
        """Foreigner — no CPF contributions."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="foreigner",
                age=30,
                monthly_ow=8000.0,
            )
        )
        assert result.cpf_applicable is False
        assert result.employer_contribution == 0.0
        assert result.employee_contribution == 0.0
        assert result.total_contribution == 0.0

    def test_zero_salary(self):
        """Zero OW — no contributions."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=0.0,
            )
        )
        assert result.total_contribution == 0.0


class TestCPFPRRates:
    """PR employee CPF calculations."""

    def test_pr_year1(self):
        """PR year 1, age 30, $5,000 OW."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="PR",
                age=30,
                monthly_ow=5000.0,
                pr_year=1,
            )
        )
        assert result.cpf_tier == "pr_year1"
        assert result.employer_rate == 0.04
        assert result.employee_rate == 0.05
        assert result.employer_contribution == round(5000 * 0.04)  # $200
        assert result.employee_contribution == round(5000 * 0.05)  # $250

    def test_pr_year2(self):
        """PR year 2, age 30, $5,000 OW."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="PR",
                age=30,
                monthly_ow=5000.0,
                pr_year=2,
            )
        )
        assert result.cpf_tier == "pr_year2"
        assert result.employer_rate == 0.09
        assert result.employee_rate == 0.15
        assert result.employer_contribution == round(5000 * 0.09)  # $450
        assert result.employee_contribution == round(5000 * 0.15)  # $750

    def test_pr_year3_plus(self):
        """PR year 3+, age 30, $5,000 OW — same as SC."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="PR",
                age=30,
                monthly_ow=5000.0,
                pr_year=5,
            )
        )
        assert result.cpf_tier == "pr_year3_plus"
        assert result.employer_rate == 0.17
        assert result.employee_rate == 0.20

    def test_pr_missing_year_raises(self):
        """PR without pr_year should raise."""
        with pytest.raises(ValueError, match="pr_year is required"):
            calculate_cpf_contributions(
                CPFInput(
                    citizenship_status="PR",
                    age=30,
                    monthly_ow=5000.0,
                )
            )


class TestCPFCeilings:
    """OW and AW ceiling tests."""

    def test_ow_below_ceiling(self):
        """OW below $8,000 — no cap applied."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
            )
        )
        assert result.ow_subject_to_cpf == 5000.0
        assert result.ow_capped is False

    def test_ow_at_ceiling(self):
        """OW exactly at $8,000 — not capped."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=8000.0,
            )
        )
        assert result.ow_subject_to_cpf == 8000.0
        assert result.ow_capped is False

    def test_ow_above_ceiling(self):
        """OW above $8,000 — capped to $8,000."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=10000.0,
            )
        )
        assert result.ow_subject_to_cpf == 8000.0
        assert result.ow_capped is True
        # Contributions should be based on capped OW
        assert result.employer_contribution == round(8000 * 0.17)

    def test_aw_within_ceiling(self):
        """AW within annual ceiling."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
                monthly_aw=10000.0,
                ytd_ow=50000.0,  # 10 months of $5,000
            )
        )
        # AW ceiling = $102,000 - (50,000 + 5,000) = $47,000
        assert result.aw_capped is False
        assert result.aw_subject_to_cpf == 10000.0

    def test_aw_exceeds_ceiling(self):
        """AW exceeds annual ceiling — should be capped."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=8000.0,
                monthly_aw=30000.0,
                ytd_ow=86000.0,  # 11 months at ceiling ($8,000 * 10 + partial)
            )
        )
        # AW ceiling = $102,000 - (86,000 + 8,000) = $8,000
        assert result.aw_capped is True
        assert result.aw_subject_to_cpf == 8000.0

    def test_aw_ceiling_exhausted(self):
        """AW ceiling already exhausted — no AW CPF."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=8000.0,
                monthly_aw=5000.0,
                ytd_ow=94000.0,  # YTD OW such that ceiling is exhausted
            )
        )
        # AW ceiling = $102,000 - (94,000 + 8,000) = $0
        assert result.aw_capped is True
        assert result.aw_subject_to_cpf == 0.0


class TestCPFAllocation:
    """Allocation to OA, SA, MA tests."""

    def test_allocation_below_55(self):
        """Allocation for age below 55."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
            )
        )
        # OA + SA + MA should equal total contribution
        assert (
            result.allocation_oa + result.allocation_sa + result.allocation_ma
            == result.total_contribution
        )
        # OA should be the largest allocation for <55
        assert result.allocation_oa > result.allocation_sa
        assert result.allocation_oa > result.allocation_ma

    def test_allocation_above_60(self):
        """Allocation for age 60-65 — MA should be largest."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=62,
                monthly_ow=4000.0,
            )
        )
        assert (
            result.allocation_oa + result.allocation_sa + result.allocation_ma
            == result.total_contribution
        )
        assert result.allocation_ma > result.allocation_oa

    def test_allocation_foreigner_zero(self):
        """Foreigner should have zero allocation."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="foreigner",
                age=30,
                monthly_ow=5000.0,
            )
        )
        assert result.allocation_oa == 0.0
        assert result.allocation_sa == 0.0
        assert result.allocation_ma == 0.0


class TestCPFWithAW:
    """CPF calculations with Additional Wages (bonus)."""

    def test_ow_plus_aw(self):
        """Standard calculation with OW and AW."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
                monthly_aw=2000.0,
            )
        )
        total_wages = 5000 + 2000
        assert result.employer_contribution == round(total_wages * 0.17)
        assert result.employee_contribution == round(total_wages * 0.20)

    def test_ow_capped_aw_uncapped(self):
        """OW capped but AW still within ceiling."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=10000.0,
                monthly_aw=5000.0,
            )
        )
        # OW capped to $8,000
        total_wages = 8000 + 5000
        assert result.ow_capped is True
        assert result.aw_capped is False
        assert result.employer_contribution == round(total_wages * 0.17)


class TestCPFBreakdown:
    """Test the detailed breakdown output."""

    def test_breakdown_structure(self):
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
                monthly_aw=1000.0,
            )
        )
        assert "ow" in result.breakdown
        assert "aw" in result.breakdown
        assert "rates" in result.breakdown
        assert "ceilings" in result.breakdown

    def test_breakdown_ow_values(self):
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
            )
        )
        ow = result.breakdown["ow"]
        assert ow["gross"] == 5000.0
        assert ow["subject_to_cpf"] == 5000.0
        assert ow["capped"] is False
        assert ow["employer_cpf"] == round(5000 * 0.17)
        assert ow["employee_cpf"] == round(5000 * 0.20)


class TestCPFEdgeCases:
    """Edge case tests."""

    def test_negative_ow_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cpf_contributions(
                CPFInput(
                    citizenship_status="SC",
                    age=30,
                    monthly_ow=-1000.0,
                )
            )

    def test_negative_aw_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cpf_contributions(
                CPFInput(
                    citizenship_status="SC",
                    age=30,
                    monthly_ow=5000.0,
                    monthly_aw=-500.0,
                )
            )

    def test_negative_age_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cpf_contributions(
                CPFInput(
                    citizenship_status="SC",
                    age=-1,
                    monthly_ow=5000.0,
                )
            )

    def test_boundary_age_55(self):
        """Age exactly 55 — should be in 55_60 band."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=55,
                monthly_ow=5000.0,
            )
        )
        assert result.age_band == "55_60"

    def test_boundary_age_60(self):
        """Age exactly 60 — should be in 60_65 band."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=60,
                monthly_ow=5000.0,
            )
        )
        assert result.age_band == "60_65"

    def test_boundary_age_65(self):
        """Age exactly 65 — should be in 65_70 band."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=65,
                monthly_ow=5000.0,
            )
        )
        assert result.age_band == "65_70"

    def test_boundary_age_70(self):
        """Age exactly 70 — should be in above_70 band."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=70,
                monthly_ow=5000.0,
            )
        )
        assert result.age_band == "above_70"


# ── Workflow tests ───────────────────────────────────────────────────


class TestCPFWorkflow:
    """Test the Kailash workflow wrapper."""

    def test_workflow_sc_standard(self):
        """Run the CPF workflow for a standard SC employee."""
        from kailash.runtime import LocalRuntime
        from hr_advisory.workflows.calculators.cpf_workflow import create_cpf_calculator_workflow

        runtime = LocalRuntime()
        workflow = create_cpf_calculator_workflow(
            citizenship_status="SC",
            age=30,
            monthly_ow=5000.0,
        )
        results, _ = runtime.execute(workflow)
        summary = results["summarize"]["result"]

        assert summary["cpf_applicable"] is True
        assert summary["cpf_tier"] == "sc_full"
        assert summary["employer_contribution"] == round(5000 * 0.17)
        assert summary["employee_contribution"] == round(5000 * 0.20)

    def test_workflow_pr_year1(self):
        """Run workflow for PR year 1 employee."""
        from kailash.runtime import LocalRuntime
        from hr_advisory.workflows.calculators.cpf_workflow import create_cpf_calculator_workflow

        runtime = LocalRuntime()
        workflow = create_cpf_calculator_workflow(
            citizenship_status="PR",
            age=30,
            monthly_ow=5000.0,
            pr_year=1,
        )
        results, _ = runtime.execute(workflow)
        summary = results["summarize"]["result"]

        assert summary["cpf_tier"] == "pr_year1"
        assert summary["employer_contribution"] == round(5000 * 0.04)
        assert summary["employee_contribution"] == round(5000 * 0.05)

    def test_workflow_foreigner(self):
        """Run workflow for foreigner."""
        from kailash.runtime import LocalRuntime
        from hr_advisory.workflows.calculators.cpf_workflow import create_cpf_calculator_workflow

        runtime = LocalRuntime()
        workflow = create_cpf_calculator_workflow(
            citizenship_status="foreigner",
            age=30,
            monthly_ow=8000.0,
        )
        results, _ = runtime.execute(workflow)
        summary = results["summarize"]["result"]

        assert summary["cpf_applicable"] is False
        assert summary["total_contribution"] == 0

    def test_workflow_ow_ceiling(self):
        """Workflow correctly caps OW."""
        from kailash.runtime import LocalRuntime
        from hr_advisory.workflows.calculators.cpf_workflow import create_cpf_calculator_workflow

        runtime = LocalRuntime()
        workflow = create_cpf_calculator_workflow(
            citizenship_status="SC",
            age=30,
            monthly_ow=10000.0,
        )
        results, _ = runtime.execute(workflow)
        summary = results["summarize"]["result"]

        assert summary["ow_capped"] is True
        assert summary["ow_subject_to_cpf"] == 8000.0
        assert summary["employer_contribution"] == round(8000 * 0.17)

    def test_workflow_with_aw(self):
        """Workflow handles AW correctly."""
        from kailash.runtime import LocalRuntime
        from hr_advisory.workflows.calculators.cpf_workflow import create_cpf_calculator_workflow

        runtime = LocalRuntime()
        workflow = create_cpf_calculator_workflow(
            citizenship_status="SC",
            age=30,
            monthly_ow=5000.0,
            monthly_aw=3000.0,
        )
        results, _ = runtime.execute(workflow)
        summary = results["summarize"]["result"]

        total_wages = 5000 + 3000
        assert summary["employer_contribution"] == round(total_wages * 0.17)

    def test_workflow_matches_pure_function(self):
        """Workflow and pure function should produce the same results."""
        from kailash.runtime import LocalRuntime
        from hr_advisory.workflows.calculators.cpf_workflow import create_cpf_calculator_workflow

        pure = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=45,
                monthly_ow=6000.0,
                monthly_aw=2000.0,
            )
        )

        runtime = LocalRuntime()
        workflow = create_cpf_calculator_workflow(
            citizenship_status="SC",
            age=45,
            monthly_ow=6000.0,
            monthly_aw=2000.0,
        )
        results, _ = runtime.execute(workflow)
        wf_result = results["summarize"]["result"]

        assert wf_result["employer_contribution"] == pure.employer_contribution
        assert wf_result["employee_contribution"] == pure.employee_contribution
        assert wf_result["total_contribution"] == pure.total_contribution
        assert wf_result["allocation_oa"] == pure.allocation_oa
        assert wf_result["allocation_sa"] == pure.allocation_sa
        assert wf_result["allocation_ma"] == pure.allocation_ma


# ── CPF Board published examples ────────────────────────────────────


class TestCPFPublishedExamples:
    """Tests based on CPF Board published calculation examples.

    These verify our calculator matches official CPF Board guidance.
    """

    def test_cpf_board_example_sc_30_5000(self):
        """Standard SC employee, age 30, $5,000 OW.

        Expected: ER 17% = $850, EE 20% = $1,000, Total = $1,850
        """
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=30,
                monthly_ow=5000.0,
            )
        )
        assert result.employer_contribution == 850
        assert result.employee_contribution == 1000
        assert result.total_contribution == 1850

    def test_cpf_board_example_sc_58_6000(self):
        """SC employee, age 58, $6,000 OW.

        Expected: ER 14.5% = $870, EE 15% = $900, Total = $1,770
        """
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=58,
                monthly_ow=6000.0,
            )
        )
        assert result.employer_contribution == 870
        assert result.employee_contribution == 900
        assert result.total_contribution == 1770

    def test_cpf_board_example_ow_ceiling(self):
        """SC employee, age 40, $10,000 OW — exceeds OW ceiling.

        CPF computed on capped OW of $8,000 only.
        Expected: ER 17% of $8,000 = $1,360, EE 20% of $8,000 = $1,600
        """
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=40,
                monthly_ow=10000.0,
            )
        )
        assert result.ow_capped is True
        assert result.ow_subject_to_cpf == 8000.0
        assert result.employer_contribution == 1360
        assert result.employee_contribution == 1600

    def test_cpf_board_example_pr_year1(self):
        """PR year 1, age 30, $5,000 OW — graduated rates.

        Expected: ER 4% = $200, EE 5% = $250, Total = $450
        """
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="PR",
                age=30,
                monthly_ow=5000.0,
                pr_year=1,
            )
        )
        assert result.employer_contribution == 200
        assert result.employee_contribution == 250
        assert result.total_contribution == 450
