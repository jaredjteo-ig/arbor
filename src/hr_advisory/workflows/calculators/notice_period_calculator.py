"""Notice Period Calculator — pure deterministic function.

Calculates applicable notice period based on:
- Years of service
- Contractual notice period (if specified)
- Who is terminating (employer or employee)
- EA s10 statutory minimums

Output: applicable period, source (statutory vs contractual), salary-in-lieu.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoticePeriodInput:
    years_of_service: float
    monthly_salary: float
    contractual_notice_weeks: int | None = None
    who_terminates: str = "employer"  # "employer" | "employee"


@dataclass(frozen=True)
class NoticePeriodResult:
    notice_period_weeks: int
    source: str  # "statutory" | "contractual"
    salary_in_lieu: float
    explanation: str
    statutory_minimum_weeks: int


def _statutory_notice_weeks(years_of_service: float) -> int:
    """Determine statutory minimum notice period per EA s10."""
    if years_of_service < 0.5:
        return 1  # Less than 26 weeks
    if years_of_service < 2.0:
        return 1
    if years_of_service < 5.0:
        return 2
    return 4


def calculate_notice_period(inp: NoticePeriodInput) -> NoticePeriodResult:
    """Calculate the applicable notice period.

    If a contractual notice period is specified and exceeds the statutory
    minimum, the contractual period applies. Otherwise, the statutory
    minimum under EA s10 governs.
    """
    statutory_weeks = _statutory_notice_weeks(inp.years_of_service)

    if (
        inp.contractual_notice_weeks is not None
        and inp.contractual_notice_weeks >= statutory_weeks
    ):
        notice_weeks = inp.contractual_notice_weeks
        source = "contractual"
    else:
        notice_weeks = statutory_weeks
        source = "statutory"

    # Salary in lieu = (monthly salary / 4) * notice weeks
    weekly_salary = inp.monthly_salary / 4.0
    salary_in_lieu = round(weekly_salary * notice_weeks, 2)

    if inp.years_of_service < 0.5:
        statutory_desc = "less than 26 weeks of service — 1 day notice (EA s10(3))"
    elif inp.years_of_service < 2.0:
        statutory_desc = "26 weeks to <2 years — 1 week notice (EA s10(2))"
    elif inp.years_of_service < 5.0:
        statutory_desc = "2 to <5 years — 2 weeks notice (EA s10(2))"
    else:
        statutory_desc = "5+ years — 4 weeks notice (EA s10(2))"

    explanation = (
        f"Statutory minimum: {statutory_desc}. "
        f"Applicable period: {notice_weeks} week(s) ({source}). "
        f"Either party may pay salary in lieu of notice (EA s11)."
    )

    return NoticePeriodResult(
        notice_period_weeks=notice_weeks,
        source=source,
        salary_in_lieu=salary_in_lieu,
        explanation=explanation,
        statutory_minimum_weeks=statutory_weeks,
    )
