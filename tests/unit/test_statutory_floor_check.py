"""Unit tests for the statutory floor check service.

Validates that company leave policies are checked against Singapore
Employment Act statutory minimums:
- Annual leave: 7 days minimum (EA s.88A, first year)
- Sick leave: 14 days outpatient minimum (EA s.89)
- Hospitalisation leave: 60 days maximum entitlement (EA s.89)

Covers: value extraction via regex, comparison logic, category filtering,
edge cases, and multi-entitlement policies.
"""

from __future__ import annotations

import pytest

from hr_advisory.services.statutory_floor_check import (
    check_policy_against_statutory_floor,
)


# ===========================================================================
# Non-leave categories return empty results
# ===========================================================================


class TestNonLeaveCategories:
    """Non-leave categories should return an empty list with no processing."""

    def test_workplace_safety_returns_empty(self) -> None:
        result = check_policy_against_statutory_floor(
            "Employees are entitled to 5 days annual leave.",
            "workplace_safety",
        )
        assert result == []

    def test_employment_terms_returns_empty(self) -> None:
        result = check_policy_against_statutory_floor(
            "Annual leave is 10 days per year.",
            "employment_terms",
        )
        assert result == []

    def test_compensation_benefits_returns_empty(self) -> None:
        result = check_policy_against_statutory_floor(
            "Sick leave is 5 days.",
            "compensation_benefits",
        )
        assert result == []

    def test_general_hr_returns_empty(self) -> None:
        result = check_policy_against_statutory_floor(
            "All employees get 3 days annual leave.",
            "general_hr",
        )
        assert result == []

    def test_empty_category_returns_empty(self) -> None:
        result = check_policy_against_statutory_floor(
            "Employees are entitled to 5 days annual leave.",
            "",
        )
        assert result == []

    def test_code_of_conduct_returns_empty(self) -> None:
        result = check_policy_against_statutory_floor(
            "All employees must abide by 7 days notice.",
            "code_of_conduct",
        )
        assert result == []


# ===========================================================================
# Annual leave detection and comparison
# ===========================================================================


class TestAnnualLeaveFloorCheck:
    """Annual leave: statutory minimum is 7 days (EA s.88A, first year)."""

    def test_below_minimum_5_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Employees are entitled to 5 days of annual leave per year.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 5
        assert annual[0]["statutory_minimum"] == 7
        assert annual[0]["status"] == "below_minimum"
        assert "statutory minimum" in annual[0]["message"].lower() or "Employment Act" in annual[0]["message"]

    def test_meets_minimum_7_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "All staff receive 7 days annual leave.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 7
        assert annual[0]["status"] == "meets_minimum"

    def test_above_minimum_14_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Employees are entitled to 14 days of annual leave.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 14
        assert annual[0]["status"] == "above_minimum"

    def test_above_minimum_21_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Each employee gets 21 working days of annual leave per calendar year.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 21
        assert annual[0]["status"] == "above_minimum"

    def test_abbreviation_AL(self) -> None:
        """'AL' abbreviation should be recognized."""
        result = check_policy_against_statutory_floor(
            "All employees are entitled to 10 days AL per annum.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 10
        assert annual[0]["status"] == "above_minimum"

    def test_exactly_at_minimum_boundary(self) -> None:
        """Exactly 7 days should be meets_minimum, not below."""
        result = check_policy_against_statutory_floor(
            "Annual leave entitlement: 7 days.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["status"] == "meets_minimum"
        assert annual[0]["company_value"] == 7


# ===========================================================================
# Sick leave detection and comparison
# ===========================================================================


class TestSickLeaveFloorCheck:
    """Sick leave: statutory minimum is 14 outpatient days (EA s.89)."""

    def test_below_minimum_10_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Employees are entitled to 10 days of sick leave per year.",
            "leave_absence",
        )
        sick = [f for f in result if f["field"] == "sick_leave"]
        assert len(sick) == 1
        assert sick[0]["company_value"] == 10
        assert sick[0]["statutory_minimum"] == 14
        assert sick[0]["status"] == "below_minimum"

    def test_meets_minimum_14_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Sick leave: 14 days outpatient sick leave per year.",
            "leave_absence",
        )
        sick = [f for f in result if f["field"] == "sick_leave"]
        assert len(sick) == 1
        assert sick[0]["company_value"] == 14
        assert sick[0]["status"] == "meets_minimum"

    def test_above_minimum_21_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Employees get 21 days sick leave annually.",
            "leave_absence",
        )
        sick = [f for f in result if f["field"] == "sick_leave"]
        assert len(sick) == 1
        assert sick[0]["company_value"] == 21
        assert sick[0]["status"] == "above_minimum"

    def test_outpatient_keyword(self) -> None:
        """'outpatient' keyword near a number should match sick leave."""
        result = check_policy_against_statutory_floor(
            "Outpatient sick leave: 8 days per calendar year.",
            "leave_absence",
        )
        sick = [f for f in result if f["field"] == "sick_leave"]
        assert len(sick) == 1
        assert sick[0]["company_value"] == 8
        assert sick[0]["status"] == "below_minimum"

    def test_medical_leave_synonym(self) -> None:
        """'medical leave' is a common synonym for sick leave."""
        result = check_policy_against_statutory_floor(
            "Employees receive 14 days medical leave.",
            "leave_absence",
        )
        sick = [f for f in result if f["field"] == "sick_leave"]
        assert len(sick) == 1
        assert sick[0]["company_value"] == 14
        assert sick[0]["status"] == "meets_minimum"


# ===========================================================================
# Hospitalisation leave detection and comparison
# ===========================================================================


class TestHospitalisationLeaveFloorCheck:
    """Hospitalisation leave: statutory maximum entitlement is 60 days (EA s.89)."""

    def test_below_minimum_30_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Hospitalisation leave: 30 days per year.",
            "leave_absence",
        )
        hosp = [f for f in result if f["field"] == "hospitalisation_leave"]
        assert len(hosp) == 1
        assert hosp[0]["company_value"] == 30
        assert hosp[0]["statutory_minimum"] == 60
        assert hosp[0]["status"] == "below_minimum"

    def test_meets_minimum_60_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Hospitalisation leave is 60 days.",
            "leave_absence",
        )
        hosp = [f for f in result if f["field"] == "hospitalisation_leave"]
        assert len(hosp) == 1
        assert hosp[0]["company_value"] == 60
        assert hosp[0]["status"] == "meets_minimum"

    def test_above_minimum_90_days(self) -> None:
        result = check_policy_against_statutory_floor(
            "Company provides 90 days hospitalisation leave.",
            "leave_absence",
        )
        hosp = [f for f in result if f["field"] == "hospitalisation_leave"]
        assert len(hosp) == 1
        assert hosp[0]["company_value"] == 90
        assert hosp[0]["status"] == "above_minimum"


# ===========================================================================
# Not detected cases
# ===========================================================================


class TestNotDetected:
    """Policies with ambiguous or missing leave information."""

    def test_no_leave_mentions_at_all(self) -> None:
        """Policy text with no leave-related keywords at all."""
        result = check_policy_against_statutory_floor(
            "This policy covers workplace conduct and dress code.",
            "leave_absence",
        )
        # Should still return findings for each leave type, with not_detected
        for finding in result:
            assert finding["status"] == "not_detected"
            assert finding["company_value"] is None

    def test_ambiguous_leave_text(self) -> None:
        """Leave mentioned but no numeric value extractable."""
        result = check_policy_against_statutory_floor(
            "Annual leave will be determined by the HR department based on seniority.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["status"] == "not_detected"
        assert annual[0]["company_value"] is None
        assert "manual" in annual[0]["message"].lower() or "verify" in annual[0]["message"].lower()

    def test_number_without_leave_context(self) -> None:
        """Numbers present but not associated with leave types."""
        result = check_policy_against_statutory_floor(
            "The office is open 5 days a week. Report to floor 7.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        # Should not pick up "5 days" (office days) or "7" (floor) as leave values
        assert annual[0]["status"] == "not_detected"


# ===========================================================================
# Multi-entitlement policies
# ===========================================================================


class TestMultiEntitlementPolicy:
    """Policies containing multiple leave types in one document."""

    def test_annual_and_sick_and_hospitalisation(self) -> None:
        content = (
            "Leave Policy\n"
            "1. Annual leave: 10 days per year.\n"
            "2. Sick leave: 14 days outpatient per year.\n"
            "3. Hospitalisation leave: 60 days per year.\n"
        )
        result = check_policy_against_statutory_floor(content, "leave_absence")

        fields = {f["field"]: f for f in result}
        assert "annual_leave" in fields
        assert "sick_leave" in fields
        assert "hospitalisation_leave" in fields

        assert fields["annual_leave"]["company_value"] == 10
        assert fields["annual_leave"]["status"] == "above_minimum"

        assert fields["sick_leave"]["company_value"] == 14
        assert fields["sick_leave"]["status"] == "meets_minimum"

        assert fields["hospitalisation_leave"]["company_value"] == 60
        assert fields["hospitalisation_leave"]["status"] == "meets_minimum"

    def test_all_below_minimum(self) -> None:
        content = (
            "Staff are entitled to:\n"
            "- 3 days annual leave\n"
            "- 5 days sick leave\n"
            "- 20 days hospitalisation leave\n"
        )
        result = check_policy_against_statutory_floor(content, "leave_absence")

        fields = {f["field"]: f for f in result}
        assert fields["annual_leave"]["status"] == "below_minimum"
        assert fields["annual_leave"]["company_value"] == 3
        assert fields["sick_leave"]["status"] == "below_minimum"
        assert fields["sick_leave"]["company_value"] == 5
        assert fields["hospitalisation_leave"]["status"] == "below_minimum"
        assert fields["hospitalisation_leave"]["company_value"] == 20


# ===========================================================================
# Edge cases and robustness
# ===========================================================================


class TestEdgeCases:
    """Edge cases: empty content, special characters, large numbers."""

    def test_empty_content(self) -> None:
        """Empty string should not crash, returns not_detected for all."""
        result = check_policy_against_statutory_floor("", "leave_absence")
        assert isinstance(result, list)
        for finding in result:
            assert finding["status"] == "not_detected"

    def test_none_content_does_not_crash(self) -> None:
        """None content should be handled gracefully (empty string equivalent)."""
        # The function should handle None defensively or raise a clear error
        try:
            result = check_policy_against_statutory_floor(None, "leave_absence")
            # If it doesn't raise, should return not_detected findings
            assert isinstance(result, list)
        except (TypeError, ValueError):
            # Also acceptable — clear error for bad input
            pass

    def test_very_large_number(self) -> None:
        """Unreasonably large numbers should still be extracted."""
        result = check_policy_against_statutory_floor(
            "Employees get 365 days annual leave.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 365
        assert annual[0]["status"] == "above_minimum"

    def test_zero_days_below_minimum(self) -> None:
        """0 days should be below_minimum."""
        result = check_policy_against_statutory_floor(
            "Annual leave: 0 days for probation employees.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 0
        assert annual[0]["status"] == "below_minimum"

    def test_case_insensitive_matching(self) -> None:
        """Keywords should match regardless of casing."""
        result = check_policy_against_statutory_floor(
            "ANNUAL LEAVE: 10 DAYS PER YEAR.",
            "leave_absence",
        )
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 10

    def test_multiline_policy(self) -> None:
        """Policy spread across many lines should still extract values."""
        content = """
        LEAVE POLICY

        Section 4.1 - Annual Leave
        All permanent employees shall be entitled to
        12 days of annual leave per calendar year.

        Section 4.2 - Sick Leave
        Employees are entitled to 14 days of outpatient
        sick leave per calendar year.
        """
        result = check_policy_against_statutory_floor(content, "leave_absence")
        annual = [f for f in result if f["field"] == "annual_leave"]
        assert len(annual) == 1
        assert annual[0]["company_value"] == 12
        assert annual[0]["status"] == "above_minimum"


# ===========================================================================
# Return structure validation
# ===========================================================================


class TestReturnStructure:
    """Validate the shape and required keys of each finding dict."""

    def test_finding_has_required_keys(self) -> None:
        result = check_policy_against_statutory_floor(
            "Annual leave is 10 days.",
            "leave_absence",
        )
        assert len(result) > 0
        for finding in result:
            assert "field" in finding
            assert "company_value" in finding
            assert "statutory_minimum" in finding
            assert "status" in finding
            assert "message" in finding

    def test_status_values_are_valid(self) -> None:
        result = check_policy_against_statutory_floor(
            "Annual leave is 10 days. Sick leave: 14 days.",
            "leave_absence",
        )
        valid_statuses = {"below_minimum", "meets_minimum", "above_minimum", "not_detected"}
        for finding in result:
            assert finding["status"] in valid_statuses, (
                f"Invalid status '{finding['status']}' for field '{finding['field']}'"
            )

    def test_message_is_nonempty_string(self) -> None:
        result = check_policy_against_statutory_floor(
            "Annual leave: 5 days.",
            "leave_absence",
        )
        for finding in result:
            assert isinstance(finding["message"], str)
            assert len(finding["message"]) > 0
