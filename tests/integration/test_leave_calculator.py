"""Tests for leave entitlement calculator."""

import pytest

from hr_advisory.workflows.calculators.leave_calculator import (
    LeaveInput,
    LeaveResult,
    calculate_leave_entitlement,
)


class TestAnnualLeave:
    """Annual leave calculation tests."""

    def test_less_than_3_months(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=0.2,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.eligible is False
        assert result.days_entitled == 0

    def test_first_year_pro_rated(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=0.5,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.eligible is True
        assert result.pro_rated is True
        assert result.days_entitled == 3.5  # 0.5 * 7 = 3.5

    def test_year_1_full(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 7

    def test_year_2(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=2,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled == 8

    def test_year_5(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=5,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled == 11

    def test_year_8_max(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=8,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled == 14

    def test_year_15_still_max_14(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=15,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled == 14

    def test_who_pays_employer(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.who_pays == "employer"


class TestSickLeave:
    """Sick leave calculation tests."""

    def test_less_than_3_months(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=0.2,
                employment_type="full_time",
                leave_type="sick_leave",
                citizenship_status="SC",
            )
        )
        assert result.eligible is False

    def test_3_months_pro_rated(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=0.25,
                employment_type="full_time",
                leave_type="sick_leave",
                citizenship_status="SC",
            )
        )
        assert result.eligible is True
        assert result.pro_rated is True
        assert result.days_entitled == 15  # 5 outpatient + 10 hospitalisation

    def test_6_months_full(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=0.5,
                employment_type="full_time",
                leave_type="sick_leave",
                citizenship_status="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 60  # 14 outpatient + 46 hospitalisation


class TestMaternityLeave:
    """Maternity leave calculation tests."""

    def test_sc_child_16_weeks(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="maternity_leave",
                citizenship_status="SC",
                child_citizenship="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 112  # 16 weeks * 7
        assert result.who_pays == "split"

    def test_non_sc_child_8_weeks(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="maternity_leave",
                citizenship_status="SC",
                child_citizenship="",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 56  # 8 weeks * 7
        assert result.who_pays == "employer"

    def test_third_child_all_government(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="maternity_leave",
                citizenship_status="SC",
                child_citizenship="SC",
                child_order=3,
            )
        )
        assert result.who_pays == "government"

    def test_less_than_3_months(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=0.2,
                employment_type="full_time",
                leave_type="maternity_leave",
                citizenship_status="SC",
                child_citizenship="SC",
            )
        )
        assert result.eligible is False


class TestPaternityLeave:
    """Paternity leave calculation tests."""

    def test_sc_father_sc_child(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="paternity_leave",
                citizenship_status="SC",
                child_citizenship="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 28  # 4 weeks
        assert result.who_pays == "government"
        assert result.government_claim_cap == 2500.0

    def test_foreigner_not_eligible(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="paternity_leave",
                citizenship_status="foreigner",
                child_citizenship="SC",
            )
        )
        assert result.eligible is False

    def test_non_sc_child(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="paternity_leave",
                citizenship_status="SC",
                child_citizenship="PR",
            )
        )
        assert result.eligible is False


class TestChildcareLeave:
    """Childcare leave calculation tests."""

    def test_sc_parent_sc_child_under_7(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="childcare_leave",
                citizenship_status="SC",
                child_ages=[3],
                child_citizenship="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 6
        assert result.who_pays == "split"

    def test_no_children_under_7(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="childcare_leave",
                citizenship_status="SC",
                child_ages=[8, 10],
                child_citizenship="SC",
            )
        )
        assert result.eligible is False

    def test_non_sc_child(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="childcare_leave",
                citizenship_status="SC",
                child_ages=[3],
                child_citizenship="PR",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 2
        assert result.who_pays == "employer"

    def test_foreigner_not_eligible(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="childcare_leave",
                citizenship_status="foreigner",
                child_ages=[3],
                child_citizenship="SC",
            )
        )
        assert result.eligible is False


class TestInfantCareLeave:
    """Infant care leave calculation tests."""

    def test_sc_parent_infant_under_2(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="infant_care_leave",
                citizenship_status="SC",
                child_ages=[1],
                child_citizenship="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 6

    def test_no_infants(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="infant_care_leave",
                citizenship_status="SC",
                child_ages=[3, 5],
                child_citizenship="SC",
            )
        )
        assert result.eligible is False


class TestSharedParentalLeave:
    """Shared parental leave calculation tests."""

    def test_sc_father_sc_child(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="shared_parental_leave",
                citizenship_status="SC",
                child_citizenship="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 28  # 4 weeks
        assert result.who_pays == "government"


class TestAdoptionLeave:
    """Adoption leave calculation tests."""

    def test_sc_child(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="adoption_leave",
                citizenship_status="SC",
                child_citizenship="SC",
            )
        )
        assert result.eligible is True
        assert result.days_entitled == 84  # 12 weeks
        assert result.who_pays == "split"

    def test_non_sc_child(self):
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="adoption_leave",
                citizenship_status="SC",
                child_citizenship="",
            )
        )
        assert result.eligible is False


class TestInvalidLeaveType:
    """Invalid leave type handling."""

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown leave type"):
            calculate_leave_entitlement(
                LeaveInput(
                    years_of_service=1,
                    employment_type="full_time",
                    leave_type="sabbatical",
                    citizenship_status="SC",
                )
            )
