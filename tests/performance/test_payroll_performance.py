"""Performance tests for Payroll Calculator.

Validates that the deterministic payroll engine can process a realistic
200-employee company within acceptable time bounds. Uses the calculator
directly (no API layer) to isolate computation performance.

Employee distribution mirrors a typical Singapore SME:
  - 60% Singapore Citizens
  - 20% Permanent Residents (mix of year 1, 2, 3+)
  - 10% Employment Pass holders
  - 10% S Pass / Work Permit holders
"""

from __future__ import annotations

import random
import time
from datetime import date, timedelta

import pytest

from hr_advisory.services.payroll_calculator import (
    calculate_employee_payslip,
    calculate_sdl,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMPLOYEE_COUNT = 200
TIME_LIMIT_SECONDS = 30
PERIOD_START = "2026-03-01"
PERIOD_END = "2026-03-31"

DEPARTMENTS = [
    "Engineering",
    "Sales",
    "Marketing",
    "Finance",
    "Operations",
    "HR",
    "Customer Service",
    "Product",
    "Legal",
    "Admin",
]

RACES = ["chinese", "malay", "indian", "eurasian"]

# Salary component templates used to build realistic payslip inputs
ALLOWANCE_TEMPLATES = [
    {"name": "Transport Allowance", "component_type": "fixed_allowance", "is_taxable": True, "is_cpf_applicable": True},
    {"name": "Meal Allowance", "component_type": "fixed_allowance", "is_taxable": True, "is_cpf_applicable": False},
    {"name": "Phone Allowance", "component_type": "fixed_allowance", "is_taxable": True, "is_cpf_applicable": False},
    {"name": "Housing Allowance", "component_type": "fixed_allowance", "is_taxable": True, "is_cpf_applicable": True},
]


# ---------------------------------------------------------------------------
# Employee generation
# ---------------------------------------------------------------------------


def _random_dob(rng: random.Random, min_age: int = 25, max_age: int = 65) -> str:
    """Generate a random date of birth for a given age range as of 2026-03-31."""
    as_of = date(2026, 3, 31)
    age = rng.randint(min_age, max_age)
    # Approximate: subtract years, randomize month/day
    birth_year = as_of.year - age
    birth_month = rng.randint(1, 12)
    birth_day = rng.randint(1, 28)  # Safe for all months
    return date(birth_year, birth_month, birth_day).isoformat()


def _generate_employees(count: int, seed: int = 42) -> list[dict]:
    """Generate a deterministic set of employees with realistic SG payroll data.

    Distribution:
      - 60% citizens
      - 20% PRs (split across year1/year2/year3+)
      - 10% EP (foreigner, no CPF)
      - 10% SP/WP (foreigner, with FWL)
    """
    rng = random.Random(seed)
    employees = []

    # Define the immigration status buckets
    # 120 citizens, 40 PRs (14 yr1, 13 yr2, 13 yr3+), 20 EP, 20 SP/WP
    statuses: list[tuple[str, str]] = []
    statuses.extend([("citizen", "citizen")] * 120)
    statuses.extend([("pr_year1", "pr")] * 14)
    statuses.extend([("pr_year2", "pr")] * 13)
    statuses.extend([("citizen", "pr")] * 13)  # PR year 3+ uses citizen rates
    statuses.extend([("foreigner", "ep")] * 20)
    statuses.extend([("foreigner", "wp")] * 10)
    statuses.extend([("foreigner", "s_pass")] * 10)

    rng.shuffle(statuses)

    for i in range(count):
        immigration_status, pass_type = statuses[i]

        # Salary range: $2,500 - $15,000 with realistic distribution
        # Lower salaries more common (skewed toward median ~$4,500)
        salary = round(rng.triangular(2500, 15000, 4500), 2)

        employee = {
            "id": f"EMP-{i + 1:04d}",
            "name": f"Employee {i + 1}",
            "salary_monthly": salary,
            "date_of_birth": _random_dob(rng),
            "immigration_status": immigration_status,
            "pass_type": pass_type,
            "race": rng.choice(RACES),
            "department": rng.choice(DEPARTMENTS),
            "start_date": "",  # Full-month employee (no proration)
            "end_date": "",
        }
        employees.append(employee)

    return employees


def _generate_salary_components(rng: random.Random, salary: float) -> list[dict]:
    """Generate 0-3 salary components for an employee."""
    num_components = rng.randint(0, 3)
    if num_components == 0:
        return []

    components = []
    selected = rng.sample(ALLOWANCE_TEMPLATES, min(num_components, len(ALLOWANCE_TEMPLATES)))

    for template in selected:
        # Allowance amount: 5-15% of base salary
        amount = round(salary * rng.uniform(0.05, 0.15), 2)
        comp = {**template, "amount": amount, "is_active": True}
        components.append(comp)

    return components


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestPayrollPerformance:
    """Performance validation for the payroll calculation engine."""

    def test_payroll_200_employees_under_30s(self):
        """T186: Payroll for 200 employees completes in under 30 seconds.

        This test exercises the full gross-to-net pipeline for each employee:
        basic salary, allowances, CPF, SDL, SHG, and FWL where applicable.
        """
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)

        # Pre-generate salary components for each employee (not timed)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        # --- Timed section: pure calculation ---
        start = time.perf_counter()

        payslips = []
        for emp, components in zip(employees, employee_components):
            payslip = calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )
            payslips.append(payslip)

        elapsed = time.perf_counter() - start

        # --- Assertions ---
        assert elapsed < TIME_LIMIT_SECONDS, (
            f"Payroll calculation took {elapsed:.2f}s for {EMPLOYEE_COUNT} employees, "
            f"exceeding the {TIME_LIMIT_SECONDS}s limit"
        )
        assert len(payslips) == EMPLOYEE_COUNT, (
            f"Expected {EMPLOYEE_COUNT} payslips, got {len(payslips)}"
        )

    def test_all_payslips_have_valid_structure(self):
        """Every payslip contains the required fields with sane values."""
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        payslips = []
        for emp, components in zip(employees, employee_components):
            payslip = calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )
            payslips.append((emp, payslip))

        required_keys = {
            "basic_salary",
            "gross_salary",
            "net_salary",
            "employer_cpf",
            "employee_cpf",
            "sdl",
            "fwl",
            "shg_fund",
            "shg_amount",
            "cpf_ow_used",
            "items",
        }

        for emp, payslip in payslips:
            emp_id = emp["id"]
            missing = required_keys - set(payslip.keys())
            assert not missing, f"{emp_id}: missing payslip keys {missing}"

            assert payslip["basic_salary"] > 0, f"{emp_id}: basic_salary must be positive"
            assert payslip["gross_salary"] > 0, f"{emp_id}: gross_salary must be positive"
            assert payslip["net_salary"] > 0, f"{emp_id}: net_salary should be positive for these salary ranges"
            assert len(payslip["items"]) >= 1, f"{emp_id}: payslip must have at least one item"

    def test_cpf_nonzero_for_citizens_and_prs(self):
        """Citizens and PRs must have non-zero CPF contributions."""
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        citizens_and_prs_checked = 0

        for emp, components in zip(employees, employee_components):
            payslip = calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )

            status = emp["immigration_status"]
            emp_id = emp["id"]

            if status in ("citizen", "pr_year1", "pr_year2"):
                assert payslip["employer_cpf"] > 0, (
                    f"{emp_id} ({status}): employer CPF must be > 0, "
                    f"got {payslip['employer_cpf']}"
                )
                assert payslip["employee_cpf"] > 0, (
                    f"{emp_id} ({status}): employee CPF must be > 0, "
                    f"got {payslip['employee_cpf']}"
                )
                citizens_and_prs_checked += 1

        # Verify we actually checked a meaningful number
        # 120 citizens + 14 pr_year1 + 13 pr_year2 + 13 pr_year3+(citizen rates) = 160
        assert citizens_and_prs_checked >= 147, (
            f"Expected at least 147 citizen/PR employees with CPF checks, "
            f"got {citizens_and_prs_checked}"
        )

    def test_foreigners_have_zero_cpf(self):
        """EP/SP/WP holders (foreigners) must have zero CPF contributions."""
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        foreigners_checked = 0

        for emp, components in zip(employees, employee_components):
            if emp["immigration_status"] != "foreigner":
                continue

            payslip = calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )

            emp_id = emp["id"]
            assert payslip["employer_cpf"] == 0, (
                f"{emp_id} (foreigner): employer CPF must be 0, "
                f"got {payslip['employer_cpf']}"
            )
            assert payslip["employee_cpf"] == 0, (
                f"{emp_id} (foreigner): employee CPF must be 0, "
                f"got {payslip['employee_cpf']}"
            )
            foreigners_checked += 1

        # 20 EP + 10 WP + 10 S Pass = 40 foreigners
        assert foreigners_checked == 40, (
            f"Expected 40 foreigner employees, got {foreigners_checked}"
        )

    def test_sdl_calculated_for_all_employees(self):
        """SDL must be calculated for every employee with positive gross."""
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        for emp, components in zip(employees, employee_components):
            payslip = calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )

            emp_id = emp["id"]
            assert payslip["sdl"] > 0, (
                f"{emp_id}: SDL must be > 0 for employees with positive gross salary"
            )
            # SDL bounds: min $2, max $11.25
            assert 2.0 <= payslip["sdl"] <= 11.25, (
                f"{emp_id}: SDL {payslip['sdl']} outside valid range [$2.00, $11.25]"
            )

    def test_fwl_applied_to_wp_and_spass_only(self):
        """Foreign Worker Levy applies only to WP and S Pass holders."""
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        wp_spass_with_fwl = 0
        others_without_fwl = 0

        for emp, components in zip(employees, employee_components):
            payslip = calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )

            emp_id = emp["id"]
            pass_type = emp["pass_type"]

            if pass_type in ("wp", "s_pass"):
                assert payslip["fwl"] > 0, (
                    f"{emp_id} ({pass_type}): FWL must be > 0"
                )
                wp_spass_with_fwl += 1
            else:
                assert payslip["fwl"] == 0, (
                    f"{emp_id} ({pass_type}): FWL must be 0 for non-WP/SP"
                )
                others_without_fwl += 1

        # 10 WP + 10 S Pass = 20
        assert wp_spass_with_fwl == 20, (
            f"Expected 20 WP/SP employees with FWL, got {wp_spass_with_fwl}"
        )
        assert others_without_fwl == 180, (
            f"Expected 180 employees without FWL, got {others_without_fwl}"
        )

    def test_shg_only_for_citizens(self):
        """Self-Help Group contributions apply only to Singapore Citizens."""
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        citizens_with_shg = 0

        for emp, components in zip(employees, employee_components):
            payslip = calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )

            status = emp["immigration_status"]

            if status == "citizen" and emp["race"] in ("chinese", "malay", "indian", "eurasian"):
                # Citizens with a recognized race should have SHG
                if payslip["shg_amount"] > 0:
                    citizens_with_shg += 1
                    assert payslip["shg_fund"] in ("CDAC", "MBMF", "SINDA", "ECF"), (
                        f"{emp['id']}: unexpected SHG fund name '{payslip['shg_fund']}'"
                    )
            elif status != "citizen":
                assert payslip["shg_amount"] == 0, (
                    f"{emp['id']} ({status}): SHG must be 0 for non-citizens"
                )

        # At least some citizens should have SHG (most salaries are above $500)
        assert citizens_with_shg > 0, "Expected at least some citizens with SHG contributions"

    def test_per_employee_calculation_time(self):
        """Individual payslip calculation should be well under 150ms each.

        This catches regressions where a single calculation becomes expensive
        (e.g., accidentally quadratic algorithm, slow date parsing).
        """
        rng = random.Random(42)
        employees = _generate_employees(EMPLOYEE_COUNT, seed=42)
        employee_components = [
            _generate_salary_components(rng, emp["salary_monthly"])
            for emp in employees
        ]

        max_single = 0.0
        slow_employees = []

        for emp, components in zip(employees, employee_components):
            start = time.perf_counter()
            calculate_employee_payslip(
                employee=emp,
                salary_components=components,
                period_start=PERIOD_START,
                period_end=PERIOD_END,
            )
            elapsed = time.perf_counter() - start

            if elapsed > max_single:
                max_single = elapsed

            if elapsed > 0.150:
                slow_employees.append((emp["id"], elapsed))

        assert not slow_employees, (
            f"{len(slow_employees)} employees exceeded 150ms per calculation: "
            + ", ".join(f"{eid}={t:.3f}s" for eid, t in slow_employees[:5])
        )
