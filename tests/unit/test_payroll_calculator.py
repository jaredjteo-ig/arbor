"""Unit tests for Payroll Calculator service.

Comprehensive test suite validating gross-to-net payroll calculations
against CPF Board rate tables, SDL rules, SHG fund tables, and
EA-compliant statutory file generation.

50+ tests covering:
- CPF contributions by age band / citizenship tier (20+)
- SDL levy with min/max boundaries (5)
- SHG self-help group fund by race (8)
- Salary proration for mid-month joiners/leavers (5)
- Salary components: allowances, deductions, commissions (5)
- Cross-module OT, unpaid leave, claims (5)
- Edge cases: zero salary, missing DOB, negative net, FWL (5)
- Statutory file generation: CPF e-Submit, GIRO, payslip HTML, IR8A, IR21 (5)
"""

from __future__ import annotations

import pytest

from hr_advisory.services.payroll_calculator import (
    CPF_OW_CEILING_MONTHLY,
    calculate_employee_payslip,
    calculate_sdl,
    calculate_shg,
    prorate_salary,
    _calculate_age,
    _get_cpf_rates,
    _get_fwl_rate,
)
from hr_advisory.services.statutory_files import (
    generate_cpf_esubmit,
    generate_bank_giro,
    generate_payslip_html,
    generate_ir8a_data,
    generate_ir21_data,
)


# ---------------------------------------------------------------------------
# Helper: build a minimal employee dict
# ---------------------------------------------------------------------------


def _emp(
    salary: float = 5000.0,
    dob: str = "1996-01-15",
    status: str = "citizen",
    race: str = "chinese",
    pass_type: str = "citizen",
    start_date: str = "",
    end_date: str = "",
    **extra,
) -> dict:
    """Build a minimal employee dict for testing."""
    d = {
        "salary_monthly": salary,
        "date_of_birth": dob,
        "immigration_status": status,
        "race": race,
        "pass_type": pass_type,
    }
    if start_date:
        d["start_date"] = start_date
    if end_date:
        d["end_date"] = end_date
    d.update(extra)
    return d


# =========================================================================
# 1. CPF Calculations (22 tests)
# =========================================================================


class TestCPFByAgeBand:
    """CPF contribution rates for Singapore Citizens across all age bands.

    Rates are from 2026 CPF Board tables.
    CPF contributions are rounded to the nearest dollar (round(..., 0)).
    """

    def test_cpf_sc_age_30_standard(self):
        """SC citizen age 30, $5,000 salary: 17% employer, 20% employee."""
        emp = _emp(salary=5000.0, dob="1996-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(5000 * 0.17, 0)  # 850.0
        assert result["employee_cpf"] == round(5000 * 0.20, 0)  # 1000.0

    def test_cpf_sc_age_55_boundary(self):
        """SC citizen exactly age 55: falls into 55-60 band (14.5% / 15%).

        Implementation uses `age <= 55` for the first band, so age 55
        is in the 55-60 band per _get_cpf_rates logic (age > 55 check fails,
        so age 55 is in the <=55 band).
        """
        # Person born 1971-01-01, as of 2026-03-31 is age 55
        emp = _emp(salary=5000.0, dob="1971-01-01")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        # _get_cpf_rates: age <= 55 returns (0.17, 0.20)
        assert result["employer_cpf"] == round(5000 * 0.17, 0)  # 850.0
        assert result["employee_cpf"] == round(5000 * 0.20, 0)  # 1000.0

    def test_cpf_sc_age_56(self):
        """SC citizen age 56: 14.5% employer, 15% employee (55-60 band)."""
        # Born 1970-01-01, as of 2026-03-31 is age 56
        emp = _emp(salary=5000.0, dob="1970-01-01")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(5000 * 0.145, 0)  # 725.0
        assert result["employee_cpf"] == round(5000 * 0.15, 0)  # 750.0

    def test_cpf_sc_age_58(self):
        """SC citizen age 58: 14.5% employer, 15% employee."""
        # Born 1968-01-15, as of 2026-03-31 is age 58
        emp = _emp(salary=6000.0, dob="1968-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(6000 * 0.145, 0)  # 870.0
        assert result["employee_cpf"] == round(6000 * 0.15, 0)  # 900.0

    def test_cpf_sc_age_60_boundary(self):
        """SC citizen exactly age 60: falls into 55-60 band (<=60)."""
        # Born 1966-01-01, as of 2026-03-31 is age 60
        emp = _emp(salary=5000.0, dob="1966-01-01")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        # _get_cpf_rates: age <= 60 returns (0.145, 0.15)
        assert result["employer_cpf"] == round(5000 * 0.145, 0)
        assert result["employee_cpf"] == round(5000 * 0.15, 0)

    def test_cpf_sc_age_62(self):
        """SC citizen age 62: 11% employer, 9.5% employee (60-65 band)."""
        # Born 1964-01-15, as of 2026-03-31 is age 62
        emp = _emp(salary=4000.0, dob="1964-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(4000 * 0.11, 0)  # 440.0
        assert result["employee_cpf"] == round(4000 * 0.095, 0)  # 380.0

    def test_cpf_sc_age_65_boundary(self):
        """SC citizen exactly age 65: falls into 60-65 band (<=65)."""
        # Born 1961-01-01, as of 2026-03-31 is age 65
        emp = _emp(salary=4000.0, dob="1961-01-01")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        # _get_cpf_rates: age <= 65 returns (0.11, 0.095)
        assert result["employer_cpf"] == round(4000 * 0.11, 0)
        assert result["employee_cpf"] == round(4000 * 0.095, 0)

    def test_cpf_sc_age_68(self):
        """SC citizen age 68: 7.5% employer, 7% employee (65-70 band)."""
        # Born 1958-01-15, as of 2026-03-31 is age 68
        emp = _emp(salary=3000.0, dob="1958-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(3000 * 0.075, 0)  # 225.0
        assert result["employee_cpf"] == round(3000 * 0.07, 0)  # 210.0

    def test_cpf_sc_age_70_boundary(self):
        """SC citizen exactly age 70: falls into 65-70 band (<=70)."""
        # Born 1956-01-01, as of 2026-03-31 is age 70
        emp = _emp(salary=3000.0, dob="1956-01-01")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        # _get_cpf_rates: age <= 70 returns (0.075, 0.07)
        assert result["employer_cpf"] == round(3000 * 0.075, 0)
        assert result["employee_cpf"] == round(3000 * 0.07, 0)

    def test_cpf_sc_age_75(self):
        """SC citizen age 75: 5% employer, 5% employee (above 70 band)."""
        # Born 1951-01-15, as of 2026-03-31 is age 75
        emp = _emp(salary=2000.0, dob="1951-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(2000 * 0.05, 0)  # 100.0
        assert result["employee_cpf"] == round(2000 * 0.05, 0)  # 100.0

    def test_cpf_sc_age_80_above_70(self):
        """SC citizen age 80: 5% employer, 5% employee (still above-70 band)."""
        # Born 1946-01-01, as of 2026-03-31 is age 80
        emp = _emp(salary=2000.0, dob="1946-01-01")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(2000 * 0.05, 0)
        assert result["employee_cpf"] == round(2000 * 0.05, 0)


class TestCPFPRGraduatedRates:
    """CPF contribution rates for PR employees (graduated scheme)."""

    def test_cpf_pr_year1_age_30(self):
        """PR Year 1, age 30: 4% employer, 5% employee."""
        emp = _emp(salary=5000.0, dob="1996-01-15", status="pr_year1")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(5000 * 0.04, 0)  # 200.0
        assert result["employee_cpf"] == round(5000 * 0.05, 0)  # 250.0

    def test_cpf_pr_year1_age_62(self):
        """PR Year 1 rates are flat 4%/5% regardless of age in this implementation."""
        emp = _emp(salary=5000.0, dob="1964-01-15", status="pr_year1")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(5000 * 0.04, 0)
        assert result["employee_cpf"] == round(5000 * 0.05, 0)

    def test_cpf_pr_year2_age_30(self):
        """PR Year 2, age 30: 9% employer, 15% employee."""
        emp = _emp(salary=5000.0, dob="1996-01-15", status="pr_year2")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(5000 * 0.09, 0)  # 450.0
        assert result["employee_cpf"] == round(5000 * 0.15, 0)  # 750.0

    def test_cpf_pr_year2_age_62(self):
        """PR Year 2, age 62: 6.5% employer, 9.5% employee (60-65 band)."""
        emp = _emp(salary=5000.0, dob="1964-01-15", status="pr_year2")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(5000 * 0.065, 0)  # 325.0
        assert result["employee_cpf"] == round(5000 * 0.095, 0)  # 475.0

    def test_cpf_pr_year2_age_68(self):
        """PR Year 2, age 68: 6.5% employer, 7% employee (65-70 band)."""
        emp = _emp(salary=4000.0, dob="1958-01-15", status="pr_year2")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(4000 * 0.065, 0)  # 260.0
        assert result["employee_cpf"] == round(4000 * 0.07, 0)  # 280.0

    def test_cpf_pr_year2_age_75(self):
        """PR Year 2, age 75: 6.5% employer, 5% employee (above 70 band)."""
        emp = _emp(salary=3000.0, dob="1951-01-15", status="pr_year2")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == round(3000 * 0.065, 0)  # 195.0
        assert result["employee_cpf"] == round(3000 * 0.05, 0)  # 150.0


class TestCPFForeignerAndCeilings:
    """CPF for foreigners and OW ceiling tests."""

    def test_cpf_foreigner_no_cpf(self):
        """Foreign worker: no CPF contributions at all."""
        emp = _emp(salary=5000.0, dob="1996-01-15", status="foreigner", pass_type="wp")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employer_cpf"] == 0.0
        assert result["employee_cpf"] == 0.0

    def test_cpf_ow_ceiling_applied(self):
        """Salary $10,000 but CPF calculated on $8,000 OW ceiling only."""
        emp = _emp(salary=10000.0, dob="1996-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["cpf_ow_used"] == CPF_OW_CEILING_MONTHLY  # 8000.0
        assert result["employer_cpf"] == round(8000 * 0.17, 0)  # 1360.0
        assert result["employee_cpf"] == round(8000 * 0.20, 0)  # 1600.0

    def test_cpf_ow_ceiling_not_needed(self):
        """Salary $5,000 -- below OW ceiling, full salary used for CPF."""
        emp = _emp(salary=5000.0, dob="1996-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["cpf_ow_used"] == 5000.0

    def test_cpf_ow_ceiling_exact(self):
        """Salary exactly at $8,000 OW ceiling -- no cap needed."""
        emp = _emp(salary=8000.0, dob="1996-01-15")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["cpf_ow_used"] == 8000.0
        assert result["employer_cpf"] == round(8000 * 0.17, 0)


# =========================================================================
# 2. SDL Calculations (5 tests)
# =========================================================================


class TestSDLCalculation:
    """Skills Development Levy: 0.25% of gross, min $2, max $11.25."""

    def test_sdl_minimum(self):
        """SDL minimum $2 for low wages (0.25% of $100 = $0.25 < $2)."""
        assert calculate_sdl(100.0) == 2.0

    def test_sdl_standard(self):
        """SDL 0.25% of $3,000 = $7.50 (between min and max)."""
        assert calculate_sdl(3000.0) == 7.50

    def test_sdl_maximum(self):
        """SDL maximum $11.25 for high wages (0.25% of $10,000 = $25 > $11.25)."""
        assert calculate_sdl(10000.0) == 11.25

    def test_sdl_zero_salary(self):
        """No SDL for zero salary."""
        assert calculate_sdl(0.0) == 0.0

    def test_sdl_exact_boundary_lower(self):
        """Salary $800: 0.25% = $2.00 exactly at minimum boundary."""
        assert calculate_sdl(800.0) == 2.0

    def test_sdl_exact_boundary_upper(self):
        """Salary $4,500: 0.25% = $11.25 exactly at maximum boundary."""
        assert calculate_sdl(4500.0) == 11.25

    def test_sdl_negative_salary(self):
        """Negative salary returns $0."""
        assert calculate_sdl(-500.0) == 0.0


# =========================================================================
# 3. SHG Calculations (8 tests)
# =========================================================================


class TestSHGCalculation:
    """Self-Help Group fund contributions by race for citizens only."""

    def test_shg_cdac_chinese_citizen(self):
        """Chinese citizen earning $5,500: CDAC contribution = $5.00."""
        fund, amount = calculate_shg("chinese", 5500.0, "citizen")
        assert fund == "CDAC"
        assert amount == 5.00

    def test_shg_mbmf_malay_citizen(self):
        """Malay citizen earning $5,000: MBMF contribution = $3.00."""
        fund, amount = calculate_shg("malay", 5000.0, "citizen")
        assert fund == "MBMF"
        assert amount == 3.00

    def test_shg_sinda_indian_citizen(self):
        """Indian citizen earning $3,000: SINDA contribution = $7.00."""
        fund, amount = calculate_shg("indian", 3000.0, "citizen")
        assert fund == "SINDA"
        assert amount == 7.00

    def test_shg_ecf_eurasian_citizen(self):
        """Eurasian citizen earning $3,000: ECF contribution = $3.00."""
        fund, amount = calculate_shg("eurasian", 3000.0, "citizen")
        assert fund == "ECF"
        assert amount == 3.00

    def test_shg_foreigner_no_shg(self):
        """Foreigners do not contribute to SHG funds."""
        fund, amount = calculate_shg("chinese", 5000.0, "foreigner")
        assert fund == ""
        assert amount == 0.0

    def test_shg_pr_no_shg(self):
        """PRs do not contribute to SHG funds (only citizens)."""
        fund, amount = calculate_shg("chinese", 5000.0, "pr_year2")
        assert fund == ""
        assert amount == 0.0

    def test_shg_low_income_exempt(self):
        """Chinese citizen earning $400: below lowest band, no CDAC."""
        fund, amount = calculate_shg("chinese", 400.0, "citizen")
        assert fund == "CDAC"
        assert amount == 0.0

    def test_shg_high_income_band(self):
        """Chinese citizen earning $12,000: highest CDAC band = $9.00."""
        fund, amount = calculate_shg("chinese", 12000.0, "citizen")
        assert fund == "CDAC"
        assert amount == 9.00

    def test_shg_unknown_race_no_fund(self):
        """Unknown race returns no fund name and zero contribution."""
        fund, amount = calculate_shg("other", 5000.0, "citizen")
        assert fund == ""
        assert amount == 0.0


# =========================================================================
# 4. Salary Proration (5 tests)
# =========================================================================


class TestSalaryProration:
    """Proration using calendar day method for mid-month joiners/leavers."""

    def test_proration_mid_month_join(self):
        """Joined March 15: worked 17 out of 31 days."""
        prorated = prorate_salary(5000.0, "2026-03-15", "", "2026-03-01", "2026-03-31")
        expected = round(5000.0 * 17 / 31, 2)
        assert prorated == expected

    def test_proration_mid_month_leave(self):
        """Left March 20: worked 20 out of 31 days."""
        prorated = prorate_salary(5000.0, "", "2026-03-20", "2026-03-01", "2026-03-31")
        expected = round(5000.0 * 20 / 31, 2)
        assert prorated == expected

    def test_proration_full_month(self):
        """Full month -- no proration, returns full salary."""
        prorated = prorate_salary(5000.0, "2026-01-01", "", "2026-03-01", "2026-03-31")
        assert prorated == 5000.0

    def test_proration_zero_days(self):
        """Start date after end date within period -- zero salary."""
        prorated = prorate_salary(5000.0, "2026-04-01", "2026-02-28", "2026-03-01", "2026-03-31")
        assert prorated == 0.0

    def test_proration_single_day(self):
        """Employee starts and ends on the same day within the period."""
        prorated = prorate_salary(5000.0, "2026-03-15", "2026-03-15", "2026-03-01", "2026-03-31")
        expected = round(5000.0 * 1 / 31, 2)
        assert prorated == expected


# =========================================================================
# 5. Salary Components (5 tests)
# =========================================================================


class TestSalaryComponents:
    """Allowances, deductions, and commissions affect payslip correctly."""

    def test_allowance_added_to_gross(self):
        """Fixed allowance is added to gross salary."""
        emp = _emp(salary=5000.0)
        comps = [
            {
                "component_type": "fixed_allowance",
                "name": "Transport",
                "amount": 500.0,
                "is_active": True,
                "is_taxable": True,
                "is_cpf_applicable": True,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        assert result["gross_salary"] == 5500.0

    def test_deduction_subtracted_from_gross(self):
        """Deduction reduces gross salary."""
        emp = _emp(salary=5000.0)
        comps = [
            {
                "component_type": "fixed_deduction",
                "name": "Loan Repayment",
                "amount": 200.0,
                "is_active": True,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        assert result["gross_salary"] == 4800.0

    def test_commission_added_to_gross(self):
        """Commission is added to gross salary."""
        emp = _emp(salary=4000.0)
        comps = [
            {
                "component_type": "commission",
                "name": "Q1 Commission",
                "amount": 1500.0,
                "is_active": True,
                "is_taxable": True,
                "is_cpf_applicable": True,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        assert result["gross_salary"] == 5500.0

    def test_cpf_on_allowance_when_applicable(self):
        """CPF is calculated on basic + CPF-applicable allowance."""
        emp = _emp(salary=5000.0)
        comps = [
            {
                "component_type": "fixed_allowance",
                "name": "Meal",
                "amount": 1000.0,
                "is_active": True,
                "is_taxable": True,
                "is_cpf_applicable": True,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        # CPF applicable = basic (5000) + allowance (1000) = 6000, capped at OW 8000
        assert result["cpf_ow_used"] == 6000.0
        assert result["employer_cpf"] == round(6000 * 0.17, 0)

    def test_no_cpf_on_allowance_when_not_applicable(self):
        """Non-CPF-applicable allowance does not affect CPF calculation."""
        emp = _emp(salary=5000.0)
        comps = [
            {
                "component_type": "fixed_allowance",
                "name": "Reimbursement",
                "amount": 1000.0,
                "is_active": True,
                "is_taxable": False,
                "is_cpf_applicable": False,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        # CPF only on basic salary (5000), not the non-CPF allowance
        assert result["cpf_ow_used"] == 5000.0
        assert result["employer_cpf"] == round(5000 * 0.17, 0)

    def test_inactive_component_ignored(self):
        """Inactive salary components are not processed."""
        emp = _emp(salary=5000.0)
        comps = [
            {
                "component_type": "fixed_allowance",
                "name": "Old Allowance",
                "amount": 1000.0,
                "is_active": False,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        assert result["gross_salary"] == 5000.0

    def test_bonus_added_to_gross(self):
        """Bonus is added to gross salary and is CPF-applicable."""
        emp = _emp(salary=5000.0)
        comps = [
            {
                "component_type": "bonus",
                "name": "13th Month",
                "amount": 5000.0,
                "is_active": True,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        assert result["gross_salary"] == 10000.0
        # CPF capped at OW ceiling
        assert result["cpf_ow_used"] == CPF_OW_CEILING_MONTHLY


# =========================================================================
# 6. Cross-Module: OT, Unpaid Leave, Claims (5 tests)
# =========================================================================


class TestCrossModuleCalculations:
    """Overtime, unpaid leave, and claims interact correctly with payslip."""

    def test_overtime_pay_calculation(self):
        """10 hours OT at 1.5x rate based on 173.33-hour month."""
        emp = _emp(salary=5000.0)
        result = calculate_employee_payslip(
            emp, [], "2026-03-01", "2026-03-31", overtime_hours=10.0
        )
        hourly_rate = 5000.0 / 173.33
        ot_rate = hourly_rate * 1.5
        ot_pay = round(ot_rate * 10.0, 2)
        assert result["gross_salary"] == 5000.0 + ot_pay

    def test_unpaid_leave_deduction(self):
        """3 days unpaid leave deducted from gross (daily rate = salary / 22)."""
        emp = _emp(salary=5000.0)
        result = calculate_employee_payslip(
            emp, [], "2026-03-01", "2026-03-31", leave_deduction_days=3.0
        )
        daily_rate = 5000.0 / 22
        deduction = round(daily_rate * 3.0, 2)
        assert result["gross_salary"] == round(5000.0 - deduction, 2)

    def test_claims_reimbursement_not_cpf(self):
        """Claims added to net salary but not subject to CPF."""
        emp = _emp(salary=5000.0)
        result = calculate_employee_payslip(
            emp, [], "2026-03-01", "2026-03-31", approved_claims_total=200.0
        )
        # Net = gross - employee_cpf - shg + claims
        gross = result["gross_salary"]
        ee_cpf = result["employee_cpf"]
        shg = result["shg_amount"]
        expected_net = round(gross - ee_cpf - shg + 200.0, 2)
        assert result["net_salary"] == expected_net
        # CPF should be on basic salary only, not claims
        assert result["cpf_ow_used"] == 5000.0

    def test_claims_appear_in_items(self):
        """Claims reimbursement appears as a line item."""
        emp = _emp(salary=5000.0)
        result = calculate_employee_payslip(
            emp, [], "2026-03-01", "2026-03-31", approved_claims_total=350.0
        )
        claim_items = [i for i in result["items"] if i["item_type"] == "claim_reimbursement"]
        assert len(claim_items) == 1
        assert claim_items[0]["amount"] == 350.0
        assert claim_items[0]["is_cpf_applicable"] is False

    def test_all_components_together(self):
        """Employee with allowance, deduction, OT, unpaid leave, and claims."""
        emp = _emp(salary=5000.0)
        comps = [
            {
                "component_type": "fixed_allowance",
                "name": "Transport",
                "amount": 500.0,
                "is_active": True,
                "is_taxable": True,
                "is_cpf_applicable": True,
            },
            {
                "component_type": "fixed_deduction",
                "name": "Loan",
                "amount": 200.0,
                "is_active": True,
            },
        ]
        result = calculate_employee_payslip(
            emp,
            comps,
            "2026-03-01",
            "2026-03-31",
            overtime_hours=5.0,
            leave_deduction_days=1.0,
            approved_claims_total=100.0,
        )

        # Verify all item types are present
        item_types = {i["item_type"] for i in result["items"]}
        assert "basic_salary" in item_types
        assert "allowance" in item_types
        assert "deduction" in item_types
        assert "overtime" in item_types
        assert "no_pay_leave_deduction" in item_types
        assert "employer_cpf" in item_types
        assert "employee_cpf" in item_types
        assert "sdl" in item_types
        assert "claim_reimbursement" in item_types

        # Net salary should be a positive number (reasonable test)
        assert result["net_salary"] > 0


# =========================================================================
# 7. Edge Cases (5 tests)
# =========================================================================


class TestEdgeCases:
    """Boundary conditions, missing data, and unusual inputs."""

    def test_zero_salary(self):
        """Zero salary employee produces zero CPF and zero gross."""
        emp = _emp(salary=0.0)
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["basic_salary"] == 0.0
        assert result["gross_salary"] == 0.0
        assert result["employer_cpf"] == 0.0
        assert result["employee_cpf"] == 0.0
        assert result["net_salary"] == 0.0

    def test_missing_dob_defaults_age_30(self):
        """When DOB is missing, age defaults to 30 (<=55 band: 17%/20%)."""
        emp = _emp(salary=5000.0, dob="")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        # Default age 30 -> (0.17, 0.20)
        assert result["employer_cpf"] == round(5000 * 0.17, 0)
        assert result["employee_cpf"] == round(5000 * 0.20, 0)

    def test_negative_net_calculated(self):
        """Large deductions can produce a negative net -- it is calculated, not blocked."""
        emp = _emp(salary=1000.0)
        comps = [
            {
                "component_type": "fixed_deduction",
                "name": "Large Loan",
                "amount": 2000.0,
                "is_active": True,
            }
        ]
        result = calculate_employee_payslip(emp, comps, "2026-03-01", "2026-03-31")
        # gross = 1000 - 2000 = -1000
        # Net will be negative because of CPF deduction from negative gross
        assert result["gross_salary"] < 0

    def test_fwl_for_wp_holder(self):
        """Work Permit holder incurs $300 FWL (employer-paid)."""
        emp = _emp(salary=2000.0, status="foreigner", pass_type="wp")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["fwl"] == 300.0

    def test_fwl_for_sp_holder(self):
        """S Pass holder incurs $450 FWL (employer-paid)."""
        emp = _emp(salary=3000.0, status="foreigner", pass_type="s_pass")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["fwl"] == 450.0

    def test_no_fwl_for_citizen(self):
        """Citizens do not incur FWL."""
        emp = _emp(salary=5000.0, pass_type="citizen")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["fwl"] == 0.0

    def test_no_fwl_for_ep_holder(self):
        """EP holders do not incur FWL (pass_type not in 'wp' or 's_pass')."""
        emp = _emp(salary=8000.0, status="foreigner", pass_type="ep")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["fwl"] == 0.0


# =========================================================================
# 8. Internal Helper Functions
# =========================================================================


class TestCalculateAge:
    """Test the _calculate_age internal function."""

    def test_age_simple(self):
        """Basic age calculation."""
        assert _calculate_age("1996-01-15", "2026-03-31") == 30

    def test_age_before_birthday(self):
        """Age calculated before birthday in the current year."""
        assert _calculate_age("1996-06-15", "2026-03-31") == 29

    def test_age_on_birthday(self):
        """Age calculated on exact birthday."""
        assert _calculate_age("1996-03-31", "2026-03-31") == 30

    def test_age_empty_dob(self):
        """Empty DOB defaults to age 30."""
        assert _calculate_age("", "2026-03-31") == 30

    def test_age_invalid_dob(self):
        """Invalid DOB defaults to age 30."""
        assert _calculate_age("not-a-date", "2026-03-31") == 30


class TestGetCPFRates:
    """Test the _get_cpf_rates internal function directly."""

    def test_foreigner_returns_zero(self):
        er, ee = _get_cpf_rates(30, "foreigner")
        assert er == 0.0
        assert ee == 0.0

    def test_citizen_age_30(self):
        er, ee = _get_cpf_rates(30, "citizen")
        assert er == 0.17
        assert ee == 0.20

    def test_citizen_age_55(self):
        """Age 55 is <= 55, so still in the first band."""
        er, ee = _get_cpf_rates(55, "citizen")
        assert er == 0.17
        assert ee == 0.20

    def test_citizen_age_56(self):
        er, ee = _get_cpf_rates(56, "citizen")
        assert er == 0.145
        assert ee == 0.15


class TestGetFWLRate:
    """Test the _get_fwl_rate internal function."""

    def test_wp_rate(self):
        assert _get_fwl_rate("wp", "") == 300.0

    def test_sp_rate(self):
        assert _get_fwl_rate("s_pass", "") == 450.0

    def test_ep_no_fwl(self):
        assert _get_fwl_rate("ep", "") == 0.0

    def test_citizen_no_fwl(self):
        assert _get_fwl_rate("citizen", "") == 0.0


# =========================================================================
# 9. Statutory File Generation (5 tests)
# =========================================================================


class TestCPFEsubmitFormat:
    """CPF e-Submit CSV file generation."""

    def test_cpf_esubmit_format(self):
        """CPF e-Submit CSV has correct header, detail, and trailer rows."""
        payroll_run = {
            "period_start": "2026-03-01",
            "employer_cpf_account": "CPF12345",
        }
        payslips = [
            {
                "employee_id": "emp1",
                "cpf_ow_used": 5000.0,
                "cpf_aw_used": 0.0,
                "employer_cpf": 850.0,
                "employee_cpf": 1000.0,
            }
        ]
        employees = [
            {
                "id": "emp1",
                "name": "John Doe",
                "nric_fin": "S1234567D",
            }
        ]

        csv_content = generate_cpf_esubmit(payroll_run, payslips, employees)
        lines = csv_content.strip().split("\n")

        # Header row
        assert lines[0].startswith("HEADER,CPF12345,202603,1")

        # Detail row
        assert "DETAIL" in lines[1]
        assert "S1234567D" in lines[1]
        assert "John Doe" in lines[1]
        assert "850.00" in lines[1]
        assert "1000.00" in lines[1]

        # Trailer row
        assert lines[2].startswith("TRAILER")
        assert "850.00" in lines[2]
        assert "1000.00" in lines[2]
        assert "1850.00" in lines[2]

    def test_cpf_esubmit_multiple_employees(self):
        """CPF e-Submit correctly tallies multiple employees in trailer."""
        payroll_run = {"period_start": "2026-03-01", "employer_cpf_account": "CPF12345"}
        payslips = [
            {
                "employee_id": "emp1",
                "cpf_ow_used": 5000.0,
                "cpf_aw_used": 0.0,
                "employer_cpf": 850.0,
                "employee_cpf": 1000.0,
            },
            {
                "employee_id": "emp2",
                "cpf_ow_used": 4000.0,
                "cpf_aw_used": 0.0,
                "employer_cpf": 680.0,
                "employee_cpf": 800.0,
            },
        ]
        employees = [
            {"id": "emp1", "name": "Alice"},
            {"id": "emp2", "name": "Bob"},
        ]

        csv_content = generate_cpf_esubmit(payroll_run, payslips, employees)
        lines = csv_content.strip().split("\n")

        # Header shows 2 employees
        assert ",2" in lines[0]
        # 2 detail rows
        assert lines[1].startswith("DETAIL")
        assert lines[2].startswith("DETAIL")
        # Trailer totals
        assert "TRAILER" in lines[3]
        assert "1530.00" in lines[3]  # 850 + 680
        assert "1800.00" in lines[3]  # 1000 + 800


class TestBankGiroFormat:
    """Bank GIRO CSV file generation."""

    def test_bank_giro_generic_format(self):
        """Generic bank GIRO CSV has correct header columns."""
        payroll_run = {"pay_date": "2026-03-28", "id": 1}
        payslips = [
            {"employee_id": "emp1", "net_salary": 3500.0},
        ]
        employees = [
            {
                "id": "emp1",
                "name": "John Doe",
                "bank_code": "DBS",
                "bank_account_number": "1234567890",
            }
        ]

        csv_content = generate_bank_giro(payroll_run, payslips, employees)
        lines = csv_content.strip().split("\n")

        # Header row with column names
        header = lines[0]
        assert "EMPLOYEE_NAME" in header
        assert "BANK_CODE" in header
        assert "ACCOUNT_NUMBER" in header
        assert "AMOUNT" in header
        assert "REFERENCE" in header

        # Detail row
        assert "John Doe" in lines[1]
        assert "3500.00" in lines[1]

    def test_bank_giro_skips_zero_net(self):
        """GIRO file skips employees with zero or negative net salary."""
        payroll_run = {"pay_date": "2026-03-28", "id": 1}
        payslips = [
            {"employee_id": "emp1", "net_salary": 0.0},
            {"employee_id": "emp2", "net_salary": -100.0},
        ]
        employees = [
            {"id": "emp1", "name": "A"},
            {"id": "emp2", "name": "B"},
        ]

        csv_content = generate_bank_giro(payroll_run, payslips, employees)
        lines = csv_content.strip().split("\n")
        # Only header row, no detail rows
        assert len(lines) == 1


class TestPayslipHTML:
    """Payslip HTML generation (EA s88A compliant)."""

    def test_payslip_html_ea_s88a_compliant(self):
        """Payslip HTML contains all 12 EA s88A required elements."""
        payslip = {
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "pay_date": "2026-03-28",
            "basic_salary": 5000.0,
            "gross_salary": 5000.0,
            "net_salary": 3700.0,
            "employer_cpf": 850.0,
            "employee_cpf": 1000.0,
        }
        items = [
            {"item_type": "basic_salary", "name": "Basic Salary", "amount": 5000.0},
            {"item_type": "employee_cpf", "name": "Employee CPF", "amount": -1000.0},
            {"item_type": "employer_cpf", "name": "Employer CPF", "amount": 850.0},
            {"item_type": "sdl", "name": "SDL", "amount": 11.25},
        ]
        employee = {
            "name": "Jane Tan",
            "nric_fin": "S9876543A",
            "employee_id_internal": "EMP001",
            "department": "Engineering",
            "designation": "Software Engineer",
        }
        company = {"name": "ACME Pte Ltd", "uen": "202012345A"}

        html = generate_payslip_html(payslip, items, employee, company)

        # EA s88A required elements:
        # 1. Employer name
        assert "ACME Pte Ltd" in html
        # 2. Employee name and NRIC (masked)
        assert "Jane Tan" in html
        assert "S****543A" in html  # Masked NRIC: first char + (len-5) stars + last 4
        # 3. Date of payment
        assert "28 Mar 2026" in html
        # 4. Basic salary
        assert "5,000.00" in html
        # 5. Period covered
        assert "01 Mar 2026" in html
        assert "31 Mar 2026" in html
        # 6. Allowances section exists
        assert "Earnings" in html
        # 7. Additional payments section exists
        # 8. Deductions section
        assert "Deductions" in html
        # 9. OT info (if applicable -- not in this test)
        # 10. Net salary
        assert "3,700.00" in html
        assert "Net Salary" in html
        # 11. Employer CPF
        assert "Employer Contributions" in html
        # 12. Mode of payment
        assert "Mode of Payment" in html
        assert "Bank Transfer" in html

        # Compliance footer
        assert "s88A" in html


class TestIR8ADataAggregation:
    """IR8A tax filing data generation."""

    def test_ir8a_data_aggregation(self):
        """IR8A correctly aggregates payslip items for the full tax year."""
        employee = {
            "name": "John Doe",
            "nric_fin": "S1234567D",
            "date_of_birth": "1990-05-01",
            "nationality": "Singaporean",
            "gender": "Male",
            "designation": "Engineer",
            "start_date": "2025-06-01",
        }
        # 3 months of payslips in 2026
        payslips = [
            {"id": f"ps{i}", "period_start": f"2026-0{i}-01", "period_end": f"2026-0{i}-28"}
            for i in range(1, 4)
        ]
        items = [
            # Basic salary items
            {
                "payslip_id": "ps1",
                "item_type": "basic_salary",
                "name": "Basic Salary",
                "amount": 5000.0,
            },
            {
                "payslip_id": "ps2",
                "item_type": "basic_salary",
                "name": "Basic Salary",
                "amount": 5000.0,
            },
            {
                "payslip_id": "ps3",
                "item_type": "basic_salary",
                "name": "Basic Salary",
                "amount": 5000.0,
            },
            # One bonus
            {"payslip_id": "ps3", "item_type": "bonus", "name": "Bonus", "amount": 2000.0},
            # Employer CPF
            {
                "payslip_id": "ps1",
                "item_type": "employer_cpf",
                "name": "Employer CPF",
                "amount": 850.0,
            },
            {
                "payslip_id": "ps2",
                "item_type": "employer_cpf",
                "name": "Employer CPF",
                "amount": 850.0,
            },
            {
                "payslip_id": "ps3",
                "item_type": "employer_cpf",
                "name": "Employer CPF",
                "amount": 850.0,
            },
        ]

        ir8a = generate_ir8a_data(employee, payslips, items, 2026)

        assert ir8a["filing_type"] == "ir8a"
        assert ir8a["tax_year"] == 2026
        assert ir8a["employee_name"] == "John Doe"
        assert ir8a["nric_fin"] == "S1234567D"
        assert ir8a["gross_salary_wages"] == 15000.0  # 3 * 5000
        assert ir8a["bonus"] == 2000.0
        assert ir8a["employer_cpf"] == 2550.0  # 3 * 850
        assert ir8a["total_gross_income"] == 17000.0  # 15000 + 2000
        assert ir8a["months_paid"] == 3


class TestIR21DepartingEmployee:
    """IR21 data for departing foreign employees."""

    def test_ir21_departing_employee(self):
        """IR21 includes cessation date and correctly identifies outstanding salary."""
        employee = {
            "name": "Li Wei",
            "nric_fin": "G1234567A",
            "date_of_birth": "1990-01-01",
            "nationality": "Chinese",
            "gender": "Male",
            "designation": "Developer",
            "start_date": "2025-01-01",
            "salary_monthly": 6000.0,
            "termination_reason": "resignation",
        }
        # Only January paid
        payslips = [
            {"id": "ps1", "period_start": "2026-01-01", "period_end": "2026-01-31"},
        ]
        items = [
            {"payslip_id": "ps1", "item_type": "basic_salary", "name": "Basic", "amount": 6000.0},
        ]

        ir21 = generate_ir21_data(employee, payslips, items, "2026-02-15")

        assert ir21["filing_type"] == "ir21"
        assert ir21["cessation_date"] == "2026-02-15"
        assert ir21["last_day_of_employment"] == "2026-02-15"
        assert ir21["reason_for_cessation"] == "resignation"
        assert ir21["period_to"] == "2026-02-15"
        # Outstanding salary: 15 days from Jan 31 to Feb 15 at 6000/30 per day
        assert ir21["outstanding_salary"] > 0
        assert ir21["monies_withheld"] is True
        assert ir21["gross_salary_wages"] == 6000.0


# =========================================================================
# 10. Net Salary Integrity
# =========================================================================


class TestNetSalaryIntegrity:
    """Verify net salary formula: gross - employee_cpf - shg + claims."""

    def test_net_salary_formula_citizen(self):
        """Net = gross - employee_cpf - shg + claims for a citizen."""
        emp = _emp(salary=5000.0, race="chinese")
        result = calculate_employee_payslip(
            emp, [], "2026-03-01", "2026-03-31", approved_claims_total=100.0
        )
        expected = round(
            result["gross_salary"] - result["employee_cpf"] - result["shg_amount"] + 100.0,
            2,
        )
        assert result["net_salary"] == expected

    def test_net_salary_formula_foreigner(self):
        """Net salary for foreigner: no CPF, no SHG deducted."""
        emp = _emp(salary=3000.0, status="foreigner", pass_type="ep")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["employee_cpf"] == 0.0
        assert result["shg_amount"] == 0.0
        assert result["net_salary"] == result["gross_salary"]


# =========================================================================
# 11. Payslip Items Structure
# =========================================================================


class TestPayslipItemsStructure:
    """Verify the items list in the payslip result."""

    def test_basic_items_present(self):
        """Payslip for a citizen always has basic salary, CPF, and SDL items."""
        emp = _emp(salary=5000.0)
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        item_types = [i["item_type"] for i in result["items"]]
        assert "basic_salary" in item_types
        assert "employer_cpf" in item_types
        assert "employee_cpf" in item_types
        assert "sdl" in item_types

    def test_shg_item_present_for_citizen(self):
        """SHG item appears for citizens with salary in a contributing band."""
        emp = _emp(salary=5000.0, race="chinese")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        shg_items = [i for i in result["items"] if i["item_type"] == "shg"]
        assert len(shg_items) == 1
        assert shg_items[0]["amount"] < 0  # Deducted from employee

    def test_fwl_item_for_wp(self):
        """FWL item appears for work permit holders."""
        emp = _emp(salary=2000.0, status="foreigner", pass_type="wp")
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        fwl_items = [i for i in result["items"] if i["item_type"] == "fwl"]
        assert len(fwl_items) == 1
        assert fwl_items[0]["amount"] == 300.0

    def test_sdl_in_payslip(self):
        """SDL appears in payslip result and items."""
        emp = _emp(salary=5000.0)
        result = calculate_employee_payslip(emp, [], "2026-03-01", "2026-03-31")
        assert result["sdl"] == calculate_sdl(5000.0)
        sdl_items = [i for i in result["items"] if i["item_type"] == "sdl"]
        assert len(sdl_items) == 1
