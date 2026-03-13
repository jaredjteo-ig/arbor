"""Overtime Calculator — pure deterministic function.

Calculates overtime pay based on:
- Employment type (Part IV eligible or not)
- Monthly salary and hourly/daily rates
- Is workman (covered regardless of salary) or non-workman (covered if ≤$2,600)
- Hours worked and day type (normal/rest day/public holiday)

Implements EA Part IV: s37 (overtime rate), s38 (max 72h/month).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OvertimeInput:
    monthly_salary: float
    is_workman: bool = False
    hours_worked: float = 0.0  # Total hours in the period
    normal_hours: float = 44.0  # Normal hours per week
    day_type: str = "normal"  # "normal" | "rest_day" | "public_holiday"
    is_monthly_rated: bool = True


@dataclass(frozen=True)
class OvertimeResult:
    is_part_iv_eligible: bool
    ot_hours: float
    hourly_basic_rate: float
    ot_rate_multiplier: float
    ot_pay: float
    explanation: str
    warnings: list[str]


# EA Part IV salary ceiling for non-workmen
_NON_WORKMAN_SALARY_CEILING = 2600.0
# EA s38 max OT per month
_MAX_OT_HOURS_PER_MONTH = 72.0
# OT rate cap for salary calculation purposes (EA s38(6))
_OT_SALARY_CAP = 2600.0


def _hourly_rate(monthly_salary: float) -> float:
    """Calculate hourly basic rate for monthly-rated employee.

    Formula per EA: monthly salary / (26 * 8) = salary / 208
    (26 working days * 8 hours per day)
    """
    return monthly_salary / 208.0


def _ot_multiplier(day_type: str) -> float:
    """OT rate multiplier per EA s37 and rest day/PH provisions."""
    if day_type == "normal":
        return 1.5  # EA s37: not less than 1.5x
    if day_type == "rest_day":
        return 2.0  # Rest day work
    if day_type == "public_holiday":
        return 2.0  # PH work (base already paid, so extra 1x or 2x depending)
    return 1.5


def calculate_overtime(inp: OvertimeInput) -> OvertimeResult:
    """Calculate overtime pay per EA Part IV provisions."""
    warnings: list[str] = []

    # Determine Part IV eligibility
    if inp.is_workman:
        is_eligible = True
    else:
        is_eligible = inp.monthly_salary <= _NON_WORKMAN_SALARY_CEILING

    if not is_eligible:
        return OvertimeResult(
            is_part_iv_eligible=False,
            ot_hours=0.0,
            hourly_basic_rate=0.0,
            ot_rate_multiplier=0.0,
            ot_pay=0.0,
            explanation=(
                f"Employee earns ${inp.monthly_salary:,.0f}/month and is not a workman. "
                f"Part IV of the EA (overtime provisions) applies only to workmen (any salary) "
                f"or non-workmen earning ≤${_NON_WORKMAN_SALARY_CEILING:,.0f}/month. "
                f"OT terms are governed by the employment contract."
            ),
            warnings=[],
        )

    # Calculate OT hours
    ot_hours = max(0.0, inp.hours_worked - inp.normal_hours)

    # For OT calculation, salary is capped at $2,600 (EA s38(6))
    capped_salary = min(inp.monthly_salary, _OT_SALARY_CAP)
    hourly_rate = _hourly_rate(capped_salary)
    multiplier = _ot_multiplier(inp.day_type)
    ot_pay = round(ot_hours * hourly_rate * multiplier, 2)

    # Warnings
    if ot_hours > _MAX_OT_HOURS_PER_MONTH:
        warnings.append(
            f"OT hours ({ot_hours:.1f}) exceed the EA s38 monthly limit of "
            f"{_MAX_OT_HOURS_PER_MONTH:.0f} hours. Employer requires MOM exemption."
        )

    if inp.monthly_salary > _OT_SALARY_CAP:
        warnings.append(
            f"Salary (${inp.monthly_salary:,.0f}) exceeds the OT calculation cap "
            f"of ${_OT_SALARY_CAP:,.0f}. OT rate calculated using the capped amount."
        )

    explanation = (
        f"Part IV eligible: {'workman' if inp.is_workman else f'non-workman ≤${_NON_WORKMAN_SALARY_CEILING:,.0f}'}. "
        f"Hourly rate: ${hourly_rate:.2f} (based on ${capped_salary:,.0f}/208). "
        f"OT rate: {multiplier}x for {inp.day_type.replace('_', ' ')} work. "
        f"OT pay: {ot_hours:.1f}h × ${hourly_rate:.2f} × {multiplier} = ${ot_pay:,.2f}."
    )

    return OvertimeResult(
        is_part_iv_eligible=True,
        ot_hours=ot_hours,
        hourly_basic_rate=round(hourly_rate, 2),
        ot_rate_multiplier=multiplier,
        ot_pay=ot_pay,
        explanation=explanation,
        warnings=warnings,
    )
