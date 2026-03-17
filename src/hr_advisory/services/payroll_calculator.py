"""Payroll calculation service.

Deterministic payroll engine -- zero LLM involvement.
Processes gross-to-net calculations for all employees in a company.
"""

import logging
import math
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# CPF OW monthly ceiling (effective 1 Jan 2026 -- aligned with tested cpf_calculator.py)
CPF_OW_CEILING_MONTHLY = 8000.0
# CPF annual salary ceiling
CPF_ANNUAL_CEILING = 102000.0

# SDL rates
SDL_RATE = 0.0025  # 0.25%
SDL_MIN = 2.0
SDL_MAX = 11.25

# Self-Help Group fund rates (2026)
# Format: {race: [(min_wage, max_wage, amount), ...]}
SHG_RATES: dict[str, list[tuple[float, float, float]]] = {
    "chinese": [  # CDAC
        (0, 500, 0.0),
        (500, 1000, 0.50),
        (1000, 1500, 1.00),
        (1500, 2000, 1.50),
        (2000, 3500, 2.00),
        (3500, 5000, 3.00),
        (5000, 7500, 5.00),
        (7500, 10000, 7.00),
        (10000, 999999999, 9.00),
    ],
    "malay": [  # MBMF
        (0, 1000, 0.0),
        (1000, 2000, 1.00),
        (2000, 3000, 1.50),
        (3000, 4000, 2.00),
        (4000, 6000, 3.00),
        (6000, 8000, 4.00),
        (8000, 10000, 5.50),
        (10000, 999999999, 7.00),
    ],
    "indian": [  # SINDA
        (0, 1000, 0.0),
        (1000, 1501, 1.00),
        (1501, 2001, 3.00),
        (2001, 2501, 5.00),
        (2501, 3501, 7.00),
        (3501, 5001, 9.00),
        (5001, 7501, 11.00),
        (7501, 999999999, 13.00),
    ],
    "eurasian": [  # ECF
        (0, 1000, 0.0),
        (1000, 1501, 1.00),
        (1501, 2501, 2.00),
        (2501, 999999999, 3.00),
    ],
}


def calculate_shg(race: str, monthly_wage: float, immigration_status: str) -> tuple[str, float]:
    """Calculate Self-Help Group fund contribution.

    Returns: (fund_name, amount). Only Singapore citizens contribute.
    """
    if immigration_status != "citizen":
        return ("", 0.0)

    rates = SHG_RATES.get(race.lower())
    if not rates:
        return ("", 0.0)

    fund_names = {"chinese": "CDAC", "malay": "MBMF", "indian": "SINDA", "eurasian": "ECF"}
    fund_name = fund_names.get(race.lower(), "")

    for min_wage, max_wage, amount in rates:
        if min_wage <= monthly_wage < max_wage:
            return (fund_name, amount)

    return (fund_name, 0.0)


def calculate_sdl(gross_wage: float) -> float:
    """Calculate Skills Development Levy.

    SDL = 0.25% of gross monthly remuneration.
    Minimum $2, maximum $11.25 per employee per month.
    """
    if gross_wage <= 0:
        return 0.0
    sdl = gross_wage * SDL_RATE
    sdl = max(sdl, SDL_MIN)
    sdl = min(sdl, SDL_MAX)
    return round(sdl, 2)


def prorate_salary(
    monthly_salary: float,
    start_date: str,
    end_date: str,
    period_start: str,
    period_end: str,
) -> float:
    """Prorate salary for mid-month joiners/leavers.

    Uses calendar day method (most common in Singapore).
    """
    p_start = date.fromisoformat(period_start)
    p_end = date.fromisoformat(period_end)
    days_in_month = (p_end - p_start).days + 1

    # Determine actual working period within the payroll period
    actual_start = p_start
    actual_end = p_end

    if start_date:
        emp_start = date.fromisoformat(start_date)
        if emp_start > p_start:
            actual_start = emp_start

    if end_date:
        emp_end = date.fromisoformat(end_date)
        if emp_end < p_end:
            actual_end = emp_end

    if actual_start > actual_end:
        return 0.0

    worked_days = (actual_end - actual_start).days + 1

    if worked_days >= days_in_month:
        return monthly_salary

    return round(monthly_salary * worked_days / days_in_month, 2)


def calculate_employee_payslip(
    employee: dict,
    salary_components: list[dict],
    period_start: str,
    period_end: str,
    ytd_ow_total: float = 0.0,
    leave_deduction_days: float = 0.0,
    overtime_hours: float = 0.0,
    approved_claims_total: float = 0.0,
) -> dict:
    """Calculate a single employee's payslip.

    Returns a dict with all payslip fields and a list of items.
    This is the core calculation -- completely deterministic.
    """
    # Validate financial inputs
    salary = employee.get("salary_monthly", 0.0)
    if not isinstance(salary, (int, float)) or not math.isfinite(salary) or salary < 0:
        salary = 0.0
        employee = {**employee, "salary_monthly": salary}

    # 1. Basic salary (pro-rated if needed)
    basic_salary = prorate_salary(
        employee.get("salary_monthly", 0.0),
        employee.get("start_date", ""),
        employee.get("end_date", ""),
        period_start,
        period_end,
    )

    items: list[dict] = []
    if basic_salary > 0:
        items.append(
            {
                "item_type": "basic_salary",
                "name": "Basic Salary",
                "amount": basic_salary,
                "is_taxable": True,
                "is_cpf_applicable": True,
            }
        )

    # 2. Salary components (allowances, deductions, commissions)
    total_allowances = 0.0
    total_deductions = 0.0

    for comp in salary_components:
        if not comp.get("is_active", True):
            continue

        comp_type = comp.get("component_type", "")
        amount = comp.get("amount", 0.0)

        if comp_type in ("fixed_allowance", "variable_allowance"):
            items.append(
                {
                    "item_type": "allowance",
                    "name": comp.get("name", "Allowance"),
                    "amount": amount,
                    "is_taxable": comp.get("is_taxable", True),
                    "is_cpf_applicable": comp.get("is_cpf_applicable", True),
                }
            )
            total_allowances += amount

        elif comp_type in ("fixed_deduction", "variable_deduction"):
            items.append(
                {
                    "item_type": "deduction",
                    "name": comp.get("name", "Deduction"),
                    "amount": -abs(amount),  # Deductions are negative
                    "is_taxable": False,
                    "is_cpf_applicable": False,
                }
            )
            total_deductions += abs(amount)

        elif comp_type == "commission":
            items.append(
                {
                    "item_type": "commission",
                    "name": comp.get("name", "Commission"),
                    "amount": amount,
                    "is_taxable": comp.get("is_taxable", True),
                    "is_cpf_applicable": comp.get("is_cpf_applicable", True),
                }
            )
            total_allowances += amount

        elif comp_type == "bonus":
            items.append(
                {
                    "item_type": "bonus",
                    "name": comp.get("name", "Bonus"),
                    "amount": amount,
                    "is_taxable": True,
                    "is_cpf_applicable": True,
                }
            )
            total_allowances += amount

    # 3. Overtime pay
    if overtime_hours > 0:
        # Hourly rate for Part IV employees: monthly salary / (52 * 44) * 12
        # Simplified: monthly_salary / 173.33 hours
        hourly_rate = basic_salary / 173.33 if basic_salary > 0 else 0
        ot_rate = hourly_rate * 1.5
        ot_pay = round(ot_rate * overtime_hours, 2)
        items.append(
            {
                "item_type": "overtime",
                "name": f"Overtime ({overtime_hours}h @ ${ot_rate:.2f}/h)",
                "amount": ot_pay,
                "is_taxable": True,
                "is_cpf_applicable": True,
            }
        )
        total_allowances += ot_pay

    # 4. No-pay leave deduction
    if leave_deduction_days > 0:
        # Working days approximation: 22 per month
        working_days = 22
        daily_rate = basic_salary / working_days if basic_salary > 0 else 0
        deduction = round(daily_rate * leave_deduction_days, 2)
        items.append(
            {
                "item_type": "no_pay_leave_deduction",
                "name": f"No-Pay Leave ({leave_deduction_days} days)",
                "amount": -deduction,
                "is_taxable": False,
                "is_cpf_applicable": False,
            }
        )
        total_deductions += deduction

    # 5. Gross salary
    gross = basic_salary + total_allowances - total_deductions

    # 6. CPF calculation
    # CPF is calculated on OW (Ordinary Wages) = monthly salary capped at ceiling
    cpf_applicable_amount = sum(
        item["amount"] for item in items if item.get("is_cpf_applicable") and item["amount"] > 0
    )

    # Cap OW at monthly ceiling
    ow_for_cpf = min(cpf_applicable_amount, CPF_OW_CEILING_MONTHLY)

    # Get CPF rates based on age and citizenship
    age = _calculate_age(employee.get("date_of_birth", ""), period_end)
    immigration_status = employee.get("immigration_status", "citizen")
    employer_cpf_rate, employee_cpf_rate = _get_cpf_rates(age, immigration_status)

    employer_cpf = round(ow_for_cpf * employer_cpf_rate, 0)  # CPF rounded to nearest dollar
    employee_cpf = round(ow_for_cpf * employee_cpf_rate, 0)

    items.append(
        {
            "item_type": "employer_cpf",
            "name": f"Employer CPF ({employer_cpf_rate * 100:.1f}%)",
            "amount": employer_cpf,
            "is_taxable": False,
            "is_cpf_applicable": False,
            "notes": "Employer contribution -- not deducted from employee",
        }
    )
    items.append(
        {
            "item_type": "employee_cpf",
            "name": f"Employee CPF ({employee_cpf_rate * 100:.1f}%)",
            "amount": -employee_cpf,
            "is_taxable": False,
            "is_cpf_applicable": False,
        }
    )

    # 7. SDL
    sdl = calculate_sdl(gross)
    items.append(
        {
            "item_type": "sdl",
            "name": "Skills Development Levy",
            "amount": sdl,
            "is_taxable": False,
            "is_cpf_applicable": False,
            "notes": "Employer contribution",
        }
    )

    # 8. FWL (Foreign Worker Levy) -- only for work permit holders
    fwl = 0.0
    if employee.get("pass_type") in ("wp", "s_pass"):
        # FWL rates vary by sector and tier -- use flat estimate for now
        # Production: look up from rate tables based on sector
        fwl = _get_fwl_rate(employee.get("pass_type", ""), "")
        if fwl > 0:
            items.append(
                {
                    "item_type": "fwl",
                    "name": "Foreign Worker Levy",
                    "amount": fwl,
                    "is_taxable": False,
                    "is_cpf_applicable": False,
                    "notes": "Employer contribution",
                }
            )

    # 9. SHG (Self-Help Group fund)
    shg_fund, shg_amount = calculate_shg(
        employee.get("race", ""),
        gross,
        immigration_status,
    )
    if shg_amount > 0:
        items.append(
            {
                "item_type": "shg",
                "name": f"Self-Help Group ({shg_fund})",
                "amount": -shg_amount,
                "is_taxable": False,
                "is_cpf_applicable": False,
            }
        )

    # 10. Claims reimbursement (not subject to CPF/tax)
    if approved_claims_total > 0:
        items.append(
            {
                "item_type": "claim_reimbursement",
                "name": "Claims Reimbursement",
                "amount": approved_claims_total,
                "is_taxable": False,
                "is_cpf_applicable": False,
            }
        )

    # 11. Net salary
    net = gross - employee_cpf - shg_amount + approved_claims_total

    return {
        "basic_salary": basic_salary,
        "gross_salary": round(gross, 2),
        "net_salary": round(net, 2),
        "employer_cpf": employer_cpf,
        "employee_cpf": employee_cpf,
        "sdl": sdl,
        "fwl": fwl,
        "shg_fund": shg_fund,
        "shg_amount": shg_amount,
        "cpf_ow_used": ow_for_cpf,
        "cpf_aw_used": 0.0,  # Set during bonus runs
        "items": items,
    }


def _calculate_age(dob_str: str, as_of_str: str) -> int:
    """Calculate age as of a given date."""
    if not dob_str:
        return 30  # Default assumption if DOB not provided
    try:
        dob = date.fromisoformat(dob_str)
        as_of = date.fromisoformat(as_of_str) if as_of_str else date.today()
        age = as_of.year - dob.year
        if (as_of.month, as_of.day) < (dob.month, dob.day):
            age -= 1
        return age
    except (ValueError, TypeError):
        return 30


def _get_cpf_rates(age: int, immigration_status: str) -> tuple[float, float]:
    """Get employer and employee CPF contribution rates.

    Returns: (employer_rate, employee_rate) as decimals (e.g. 0.17 for 17%).
    Rates are for 2026 based on CPF Board tables.
    """
    if immigration_status == "foreigner":
        return (0.0, 0.0)

    # PR graduated rates
    if immigration_status == "pr_year1":
        if age <= 55:
            return (0.04, 0.05)
        elif age <= 60:
            return (0.04, 0.05)
        elif age <= 65:
            return (0.04, 0.05)
        else:
            return (0.04, 0.05)

    if immigration_status == "pr_year2":
        if age <= 55:
            return (0.09, 0.15)
        elif age <= 60:
            return (0.09, 0.15)
        elif age <= 65:
            return (0.065, 0.095)
        elif age <= 70:
            return (0.065, 0.07)
        else:
            return (0.065, 0.05)

    # Citizens and PR Year 3+ — aligned with tested cpf_calculator.py rates
    if age <= 55:
        return (0.17, 0.20)
    elif age <= 60:
        return (0.145, 0.15)
    elif age <= 65:
        return (0.11, 0.095)
    elif age <= 70:
        return (0.075, 0.07)
    else:
        return (0.05, 0.05)


def _get_fwl_rate(pass_type: str, sector: str) -> float:
    """Get Foreign Worker Levy rate.

    Simplified -- in production, look up from rate tables by sector and tier.
    """
    if pass_type == "wp":
        return 300.0  # Base tier, non-manufacturing
    elif pass_type == "s_pass":
        return 450.0  # S Pass levy
    return 0.0
