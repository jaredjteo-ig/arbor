"""Integration tests for the Employee Classification Engine.

Tests the deterministic Singapore employment classification workflow
covering EA coverage, Part IV applicability, CPF status, pass validation,
and leave entitlements.

All tests run against real Kailash Core SDK infrastructure (LocalRuntime).
NO MOCKING -- every test exercises the actual workflow pipeline.
"""

import pytest

from hr_advisory.workflows.classification import (
    EmployeeClassificationInput,
    EmployeeClassificationResult,
    create_employee_classification_workflow,
)
from hr_advisory.workflows.classification.rules import (
    classify_cpf_status,
    classify_ea_coverage,
    classify_part_iv,
    determine_cpf_age_band,
    determine_leave_entitlements,
    validate_pass_type,
)


# ===================================================================
# Helper: run the full workflow and return the classification result
# ===================================================================


def _run_classification(input_data: EmployeeClassificationInput) -> EmployeeClassificationResult:
    """Execute the classification workflow and return the result.

    Uses real Kailash LocalRuntime -- no mocking.
    """
    from kailash.runtime import LocalRuntime

    wf = create_employee_classification_workflow(input_data)
    with LocalRuntime() as runtime:
        results, run_id = runtime.execute(wf)

    assert run_id is not None, "Workflow must produce a run_id"

    # The final node 'summarize' contains the classification result
    summarize_output = results.get("summarize")
    assert summarize_output is not None, "Workflow must produce 'summarize' node output"
    assert "result" in summarize_output, "summarize node must produce a 'result' key"

    result_data = summarize_output["result"]
    return EmployeeClassificationResult(**result_data)


# ===================================================================
# 1. Pure rules unit tests (Tier 1 -- no SDK needed)
# ===================================================================


class TestClassifyEACoverage:
    """Test Employment Act coverage classification rules."""

    def test_regular_employee_covered(self):
        """Regular full-time employee is EA covered."""
        covered, reason = classify_ea_coverage(
            is_domestic_worker=False,
            is_seafarer=False,
            is_government=False,
        )
        assert covered is True
        assert reason is None

    def test_domestic_worker_excluded(self):
        """Domestic workers are excluded from the EA."""
        covered, reason = classify_ea_coverage(
            is_domestic_worker=True,
            is_seafarer=False,
            is_government=False,
        )
        assert covered is False
        assert reason is not None
        assert "domestic" in reason.lower()

    def test_seafarer_excluded(self):
        """Seafarers are excluded from the EA."""
        covered, reason = classify_ea_coverage(
            is_domestic_worker=False,
            is_seafarer=True,
            is_government=False,
        )
        assert covered is False
        assert reason is not None
        assert "seafarer" in reason.lower()

    def test_government_employee_excluded(self):
        """Government employees (statutory board/civil service) are excluded."""
        covered, reason = classify_ea_coverage(
            is_domestic_worker=False,
            is_seafarer=False,
            is_government=True,
        )
        assert covered is False
        assert reason is not None
        assert "government" in reason.lower()

    def test_multiple_exclusions_reports_first(self):
        """When multiple exclusions apply, at least one reason is reported."""
        covered, reason = classify_ea_coverage(
            is_domestic_worker=True,
            is_seafarer=True,
            is_government=False,
        )
        assert covered is False
        assert reason is not None


class TestClassifyPartIV:
    """Test EA Part IV (rest days, hours, overtime) applicability rules."""

    def test_manager_executive_not_applicable(self):
        """Managers/executives are never covered by Part IV, regardless of salary."""
        applicable, reason = classify_part_iv(
            ea_covered=True,
            is_manager_executive=True,
            is_workman=False,
            monthly_basic_salary=2000.0,
        )
        assert applicable is False
        assert "manager" in reason.lower() or "executive" in reason.lower()

    def test_workman_below_threshold_applicable(self):
        """Workman earning <=4500 is covered by Part IV."""
        applicable, reason = classify_part_iv(
            ea_covered=True,
            is_manager_executive=False,
            is_workman=True,
            monthly_basic_salary=3000.0,
        )
        assert applicable is True

    def test_workman_at_threshold_applicable(self):
        """Workman earning exactly 4500 is covered by Part IV."""
        applicable, reason = classify_part_iv(
            ea_covered=True,
            is_manager_executive=False,
            is_workman=True,
            monthly_basic_salary=4500.0,
        )
        assert applicable is True

    def test_workman_above_threshold_not_applicable(self):
        """Workman earning >4500 is NOT covered by Part IV."""
        applicable, reason = classify_part_iv(
            ea_covered=True,
            is_manager_executive=False,
            is_workman=True,
            monthly_basic_salary=5000.0,
        )
        assert applicable is False
        assert "4500" in reason or "threshold" in reason.lower()

    def test_non_workman_below_2600_applicable(self):
        """Non-workman, non-manager earning <=2600 is covered by Part IV."""
        applicable, reason = classify_part_iv(
            ea_covered=True,
            is_manager_executive=False,
            is_workman=False,
            monthly_basic_salary=2000.0,
        )
        assert applicable is True

    def test_non_workman_at_2600_applicable(self):
        """Non-workman, non-manager earning exactly 2600 is covered by Part IV."""
        applicable, reason = classify_part_iv(
            ea_covered=True,
            is_manager_executive=False,
            is_workman=False,
            monthly_basic_salary=2600.0,
        )
        assert applicable is True

    def test_non_workman_above_2600_not_applicable(self):
        """Non-workman, non-manager earning >2600 is NOT covered by Part IV."""
        applicable, reason = classify_part_iv(
            ea_covered=True,
            is_manager_executive=False,
            is_workman=False,
            monthly_basic_salary=3000.0,
        )
        assert applicable is False
        assert "2600" in reason or "threshold" in reason.lower()

    def test_not_ea_covered_not_applicable(self):
        """If not EA covered, Part IV does not apply."""
        applicable, reason = classify_part_iv(
            ea_covered=False,
            is_manager_executive=False,
            is_workman=False,
            monthly_basic_salary=2000.0,
        )
        assert applicable is False
        assert "ea" in reason.lower() or "employment act" in reason.lower()


class TestClassifyCPFStatus:
    """Test CPF status classification rules."""

    def test_singapore_citizen_full_cpf(self):
        """SC gets full CPF from day one."""
        applicable, tier = classify_cpf_status(
            citizenship_status="SC",
            pr_year=None,
        )
        assert applicable is True
        assert tier == "sc_full"

    def test_pr_year_1(self):
        """PR Year 1 gets graduated CPF rates."""
        applicable, tier = classify_cpf_status(
            citizenship_status="PR",
            pr_year=1,
        )
        assert applicable is True
        assert tier == "pr_year1"

    def test_pr_year_2(self):
        """PR Year 2 gets graduated CPF rates."""
        applicable, tier = classify_cpf_status(
            citizenship_status="PR",
            pr_year=2,
        )
        assert applicable is True
        assert tier == "pr_year2"

    def test_pr_year_3_plus(self):
        """PR Year 3+ gets full CPF rates."""
        applicable, tier = classify_cpf_status(
            citizenship_status="PR",
            pr_year=3,
        )
        assert applicable is True
        assert tier == "pr_year3_plus"

    def test_pr_year_5_is_3_plus(self):
        """PR Year 5 still classified as 3+."""
        applicable, tier = classify_cpf_status(
            citizenship_status="PR",
            pr_year=5,
        )
        assert applicable is True
        assert tier == "pr_year3_plus"

    def test_foreigner_no_cpf(self):
        """Foreigners (EP, S-Pass, WP) get no CPF."""
        applicable, tier = classify_cpf_status(
            citizenship_status="foreigner",
            pr_year=None,
        )
        assert applicable is False
        assert tier == "none"

    def test_pr_without_year_raises_error(self):
        """PR status without pr_year must raise an error."""
        with pytest.raises(ValueError, match="pr_year"):
            classify_cpf_status(
                citizenship_status="PR",
                pr_year=None,
            )

    def test_invalid_citizenship_raises_error(self):
        """Invalid citizenship status must raise an error."""
        with pytest.raises(ValueError, match="citizenship_status"):
            classify_cpf_status(
                citizenship_status="invalid",
                pr_year=None,
            )


class TestDetermineCPFAgeBand:
    """Test CPF age band determination."""

    def test_age_below_55(self):
        assert determine_cpf_age_band(30) == "55_below"

    def test_age_exactly_55(self):
        assert determine_cpf_age_band(55) == "55_60"

    def test_age_57(self):
        assert determine_cpf_age_band(57) == "55_60"

    def test_age_exactly_60(self):
        assert determine_cpf_age_band(60) == "60_65"

    def test_age_63(self):
        assert determine_cpf_age_band(63) == "60_65"

    def test_age_exactly_65(self):
        assert determine_cpf_age_band(65) == "65_70"

    def test_age_68(self):
        assert determine_cpf_age_band(68) == "65_70"

    def test_age_exactly_70(self):
        assert determine_cpf_age_band(70) == "above_70"

    def test_age_75(self):
        assert determine_cpf_age_band(75) == "above_70"

    def test_age_54(self):
        assert determine_cpf_age_band(54) == "55_below"


class TestValidatePassType:
    """Test work pass type validation."""

    def test_sc_no_pass_needed(self):
        """SC does not need a pass."""
        valid, msg = validate_pass_type(
            citizenship_status="SC",
            pass_type=None,
            monthly_basic_salary=3000.0,
            sector="services",
        )
        assert valid is True

    def test_pr_no_pass_needed(self):
        """PR does not need a pass."""
        valid, msg = validate_pass_type(
            citizenship_status="PR",
            pass_type=None,
            monthly_basic_salary=3000.0,
            sector="services",
        )
        assert valid is True

    def test_ep_valid_salary(self):
        """EP holder earning >=5000 is valid."""
        valid, msg = validate_pass_type(
            citizenship_status="foreigner",
            pass_type="ep",
            monthly_basic_salary=6000.0,
            sector="services",
        )
        assert valid is True

    def test_ep_invalid_salary(self):
        """EP holder earning <5000 is invalid."""
        valid, msg = validate_pass_type(
            citizenship_status="foreigner",
            pass_type="ep",
            monthly_basic_salary=4000.0,
            sector="services",
        )
        assert valid is False
        assert "5000" in msg or "minimum" in msg.lower()

    def test_ep_exactly_5000_valid(self):
        """EP holder earning exactly 5000 is valid."""
        valid, msg = validate_pass_type(
            citizenship_status="foreigner",
            pass_type="ep",
            monthly_basic_salary=5000.0,
            sector="services",
        )
        assert valid is True

    def test_sp_valid_salary_services(self):
        """S-Pass holder in services earning >=3150 is valid."""
        valid, msg = validate_pass_type(
            citizenship_status="foreigner",
            pass_type="sp",
            monthly_basic_salary=3500.0,
            sector="services",
        )
        assert valid is True

    def test_sp_invalid_salary(self):
        """S-Pass holder earning <3150 is invalid."""
        valid, msg = validate_pass_type(
            citizenship_status="foreigner",
            pass_type="sp",
            monthly_basic_salary=2500.0,
            sector="services",
        )
        assert valid is False
        assert "3150" in msg or "minimum" in msg.lower()

    def test_wp_no_salary_threshold(self):
        """Work permit has no minimum salary threshold."""
        valid, msg = validate_pass_type(
            citizenship_status="foreigner",
            pass_type="wp",
            monthly_basic_salary=1500.0,
            sector="construction",
        )
        assert valid is True

    def test_foreigner_without_pass_type_raises_error(self):
        """Foreigner without pass_type must raise an error."""
        with pytest.raises(ValueError, match="pass_type"):
            validate_pass_type(
                citizenship_status="foreigner",
                pass_type=None,
                monthly_basic_salary=5000.0,
                sector="services",
            )

    def test_foreigner_invalid_pass_type_raises_error(self):
        """Foreigner with invalid pass_type must raise an error."""
        with pytest.raises(ValueError, match="pass_type"):
            validate_pass_type(
                citizenship_status="foreigner",
                pass_type="invalid",
                monthly_basic_salary=5000.0,
                sector="services",
            )


class TestDetermineLeaveEntitlements:
    """Test leave entitlement determination."""

    def test_ea_covered_full_time_sc(self):
        """EA-covered full-time SC gets comprehensive leave."""
        leaves = determine_leave_entitlements(
            ea_covered=True,
            citizenship_status="SC",
            employment_type="full_time",
        )
        assert "annual_leave" in leaves
        assert "sick_leave" in leaves
        assert "maternity_leave" in leaves
        assert "paternity_leave" in leaves
        assert "childcare_leave" in leaves
        assert "shared_parental_leave" in leaves
        assert "adoption_leave" in leaves
        assert "unpaid_infant_care_leave" in leaves

    def test_ea_covered_full_time_pr(self):
        """EA-covered full-time PR gets comprehensive leave (same as SC for EA leave)."""
        leaves = determine_leave_entitlements(
            ea_covered=True,
            citizenship_status="PR",
            employment_type="full_time",
        )
        assert "annual_leave" in leaves
        assert "sick_leave" in leaves
        assert "maternity_leave" in leaves

    def test_ea_not_covered_minimal_leave(self):
        """Non-EA-covered employee gets no statutory leave."""
        leaves = determine_leave_entitlements(
            ea_covered=False,
            citizenship_status="SC",
            employment_type="full_time",
        )
        assert len(leaves) == 0

    def test_foreigner_wp_ea_covered(self):
        """EA-covered WP foreigner gets EA leave entitlements."""
        leaves = determine_leave_entitlements(
            ea_covered=True,
            citizenship_status="foreigner",
            employment_type="full_time",
        )
        # Foreigners get EA leave if EA covered, but not CCDA-based leave
        assert "annual_leave" in leaves
        assert "sick_leave" in leaves
        assert "maternity_leave" in leaves

    def test_part_time_ea_covered(self):
        """Part-time EA-covered employee gets pro-rated leave."""
        leaves = determine_leave_entitlements(
            ea_covered=True,
            citizenship_status="SC",
            employment_type="part_time",
        )
        assert "annual_leave" in leaves
        assert "sick_leave" in leaves


# ===================================================================
# 2. Full workflow integration tests (Tier 2 -- real SDK runtime)
# ===================================================================


class TestLocalClerkClassification:
    """Local clerk earning $2,000/month -- full EA + Part IV."""

    def test_local_clerk_full_coverage(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=2000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=30,
            is_workman=False,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.ea_exclusion_reason is None
        assert result.part_iv_applicable is True
        assert result.cpf_applicable is True
        assert result.cpf_tier == "sc_full"
        assert result.cpf_age_band == "55_below"
        assert result.pass_valid is True
        assert "annual_leave" in result.applicable_leave_types
        assert "sick_leave" in result.applicable_leave_types
        assert len(result.warnings) == 0


class TestLocalManagerClassification:
    """Local manager earning $8,000/month -- EA covered, Part IV NOT applicable."""

    def test_local_manager_no_part_iv(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=8000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=45,
            is_workman=False,
            is_manager_executive=True,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is False
        assert (
            "manager" in result.part_iv_reason.lower()
            or "executive" in result.part_iv_reason.lower()
        )
        assert result.cpf_applicable is True
        assert result.cpf_tier == "sc_full"
        assert result.cpf_age_band == "55_below"
        assert result.pass_valid is True


class TestLocalWorkmanBelowThreshold:
    """Local workman earning $3,000/month -- EA + Part IV."""

    def test_workman_below_threshold(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=3000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="construction",
            age=35,
            is_workman=True,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is True
        assert result.cpf_applicable is True
        assert result.cpf_tier == "sc_full"


class TestLocalWorkmanAboveThreshold:
    """Local workman earning $5,000/month -- EA, Part IV NOT applicable."""

    def test_workman_above_threshold(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=5000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="manufacturing",
            age=40,
            is_workman=True,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is False
        assert "4500" in result.part_iv_reason or "threshold" in result.part_iv_reason.lower()
        assert result.cpf_applicable is True


class TestPRYear1Classification:
    """PR Year 1 employee -- graduated CPF."""

    def test_pr_year_1_graduated_cpf(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="PR",
            employment_type="full_time",
            sector="services",
            age=32,
            is_workman=False,
            is_manager_executive=False,
            pr_year=1,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.cpf_applicable is True
        assert result.cpf_tier == "pr_year1"
        assert result.pass_valid is True


class TestPRYear3PlusClassification:
    """PR Year 3+ employee -- full CPF rates."""

    def test_pr_year_3_plus_full_cpf(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=5000.0,
            citizenship_status="PR",
            employment_type="full_time",
            sector="services",
            age=28,
            is_workman=False,
            is_manager_executive=False,
            pr_year=3,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.cpf_applicable is True
        assert result.cpf_tier == "pr_year3_plus"


class TestEPHolderValidSalary:
    """EP holder earning $6,000/month -- EA covered, no CPF."""

    def test_ep_holder_valid(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=6000.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="services",
            age=35,
            is_workman=False,
            is_manager_executive=False,
            pass_type="ep",
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.cpf_applicable is False
        assert result.cpf_tier == "none"
        assert result.pass_valid is True
        assert (
            result.pass_validation_message == ""
            or "valid" in result.pass_validation_message.lower()
        )


class TestEPHolderInvalidSalary:
    """EP holder earning $4,000/month -- invalid pass (below EP min salary)."""

    def test_ep_holder_invalid_salary(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="services",
            age=30,
            is_workman=False,
            is_manager_executive=False,
            pass_type="ep",
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.pass_valid is False
        assert (
            "5000" in result.pass_validation_message
            or "minimum" in result.pass_validation_message.lower()
        )
        assert len(result.warnings) > 0


class TestSPassHolderClassification:
    """S-Pass holder in services sector."""

    def test_spass_holder_services(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=3500.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="services",
            age=28,
            is_workman=False,
            is_manager_executive=False,
            pass_type="sp",
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.cpf_applicable is False
        assert result.cpf_tier == "none"
        assert result.pass_valid is True


class TestWorkPermitHolderClassification:
    """Work Permit holder in construction."""

    def test_wp_holder_construction(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=1800.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="construction",
            age=25,
            is_workman=True,
            is_manager_executive=False,
            pass_type="wp",
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is True  # workman <=4500
        assert result.cpf_applicable is False
        assert result.cpf_tier == "none"
        assert result.pass_valid is True


class TestDomesticWorkerClassification:
    """Domestic worker -- EA exclusion."""

    def test_domestic_worker_excluded(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=800.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="services",
            age=30,
            is_workman=False,
            is_manager_executive=False,
            pass_type="wp",
            is_domestic_worker=True,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is False
        assert result.ea_exclusion_reason is not None
        assert "domestic" in result.ea_exclusion_reason.lower()
        assert result.part_iv_applicable is False
        assert len(result.applicable_leave_types) == 0


class TestPartTimeEmployeeClassification:
    """Part-time employee classification."""

    def test_part_time_sc(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=1500.0,
            citizenship_status="SC",
            employment_type="part_time",
            sector="services",
            age=22,
            is_workman=False,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is True  # non-workman <=2600
        assert result.cpf_applicable is True
        assert result.cpf_tier == "sc_full"
        assert "annual_leave" in result.applicable_leave_types


class TestAgeCPFTiers:
    """Test CPF age band tiers through the workflow."""

    def test_age_55_cpf_band(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=55,
        )
        result = _run_classification(input_data)
        assert result.cpf_age_band == "55_60"

    def test_age_60_cpf_band(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=60,
        )
        result = _run_classification(input_data)
        assert result.cpf_age_band == "60_65"

    def test_age_65_cpf_band(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=65,
        )
        result = _run_classification(input_data)
        assert result.cpf_age_band == "65_70"

    def test_age_72_cpf_band(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=72,
        )
        result = _run_classification(input_data)
        assert result.cpf_age_band == "above_70"


class TestEdgeCaseExactly2600:
    """Non-workman earning exactly $2,600 -- Part IV APPLIES."""

    def test_exactly_2600_part_iv_applies(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=2600.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=30,
            is_workman=False,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is True


class TestEdgeCaseExactly4500:
    """Workman earning exactly $4,500 -- Part IV APPLIES."""

    def test_exactly_4500_workman_part_iv_applies(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4500.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="manufacturing",
            age=35,
            is_workman=True,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is True


class TestEdgeCaseAbove2600NonWorkman:
    """Non-workman earning $2,601 -- Part IV does NOT apply."""

    def test_above_2600_no_part_iv(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=2601.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=30,
            is_workman=False,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is False


class TestEdgeCaseAbove4500Workman:
    """Workman earning $4,501 -- Part IV does NOT apply."""

    def test_above_4500_workman_no_part_iv(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4501.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="manufacturing",
            age=35,
            is_workman=True,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.part_iv_applicable is False


class TestClassificationSummary:
    """Test that classification summary is populated with meaningful information."""

    def test_summary_not_empty(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=30,
        )
        result = _run_classification(input_data)
        assert result.classification_summary != ""
        assert len(result.classification_summary) > 10

    def test_invalid_pass_generates_warning(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="services",
            age=30,
            pass_type="ep",
        )
        result = _run_classification(input_data)
        assert len(result.warnings) > 0

    def test_government_employee_summary_mentions_exclusion(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=5000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="services",
            age=40,
            is_government=True,
        )
        result = _run_classification(input_data)
        assert result.ea_covered is False
        assert "government" in result.ea_exclusion_reason.lower()


class TestSeafarerClassification:
    """Seafarer -- EA exclusion."""

    def test_seafarer_excluded(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=4000.0,
            citizenship_status="SC",
            employment_type="full_time",
            sector="marine_shipyard",
            age=35,
            is_seafarer=True,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is False
        assert "seafarer" in result.ea_exclusion_reason.lower()
        assert result.part_iv_applicable is False


class TestContractEmployeeClassification:
    """Contract employee classification."""

    def test_contract_employee(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=3000.0,
            citizenship_status="SC",
            employment_type="contract",
            sector="services",
            age=28,
            is_workman=False,
            is_manager_executive=False,
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert result.cpf_applicable is True
        assert result.cpf_tier == "sc_full"


class TestForeignerLeaveEntitlements:
    """Foreigner leave entitlements -- EA covered but limited CCDA benefits."""

    def test_foreigner_ea_covered_leave(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=3500.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="services",
            age=30,
            pass_type="sp",
        )
        result = _run_classification(input_data)

        assert result.ea_covered is True
        assert "annual_leave" in result.applicable_leave_types
        assert "sick_leave" in result.applicable_leave_types
        assert "maternity_leave" in result.applicable_leave_types


class TestSPassInvalidSalary:
    """S-Pass holder with salary below minimum threshold."""

    def test_spass_below_minimum(self):
        input_data = EmployeeClassificationInput(
            monthly_basic_salary=2500.0,
            citizenship_status="foreigner",
            employment_type="full_time",
            sector="services",
            age=25,
            pass_type="sp",
        )
        result = _run_classification(input_data)

        assert result.pass_valid is False
        assert len(result.warnings) > 0
