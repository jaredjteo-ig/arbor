"""CPF Contribution Calculator — pure deterministic functions.

Computes Singapore CPF contributions for any employee given:
citizenship_status, pr_year, age, monthly_ow, monthly_aw (optional).

All rate tables are embedded as constants — no DB lookups needed
for the standard calculation path. For historical rate lookups,
use the KB rate table via DataFlow.

Rate tables reflect CPF contribution rates effective 1 January 2026.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# CPF Rate Table — effective 1 January 2026
# Key: (citizenship_tier, age_band)
# Value: (employer_rate, employee_rate)
# Rates are as a fraction (0.17 = 17%)
# ---------------------------------------------------------------------------

CPF_RATE_TABLE: dict[tuple[str, str], tuple[float, float]] = {
    # Singapore Citizens — full rates
    ("sc_full", "55_below"): (0.17, 0.20),
    ("sc_full", "55_60"): (0.145, 0.15),
    ("sc_full", "60_65"): (0.11, 0.095),
    ("sc_full", "65_70"): (0.075, 0.07),
    ("sc_full", "above_70"): (0.05, 0.05),
    # PR Year 1 — Graduated Employee, Graduated Employer (default)
    ("pr_year1", "55_below"): (0.04, 0.05),
    ("pr_year1", "55_60"): (0.04, 0.05),
    ("pr_year1", "60_65"): (0.035, 0.05),
    ("pr_year1", "65_70"): (0.035, 0.05),
    ("pr_year1", "above_70"): (0.035, 0.05),
    # PR Year 2 — Graduated Employee, Graduated Employer (default)
    ("pr_year2", "55_below"): (0.09, 0.15),
    ("pr_year2", "55_60"): (0.09, 0.15),
    ("pr_year2", "60_65"): (0.065, 0.095),
    ("pr_year2", "65_70"): (0.065, 0.07),
    ("pr_year2", "above_70"): (0.065, 0.05),
    # PR Year 3+ — same as SC
    ("pr_year3_plus", "55_below"): (0.17, 0.20),
    ("pr_year3_plus", "55_60"): (0.145, 0.15),
    ("pr_year3_plus", "60_65"): (0.11, 0.095),
    ("pr_year3_plus", "65_70"): (0.075, 0.07),
    ("pr_year3_plus", "above_70"): (0.05, 0.05),
}

# CPF allocation rates to OA, SA, MA — effective 1 January 2026
# Key: age_band → (oa_rate, sa_rate, ma_rate) as fraction of total wages
CPF_ALLOCATION_TABLE: dict[str, tuple[float, float, float]] = {
    "55_below": (
        0.2308,
        0.0616,
        0.0811,
    ),  # ~23.08% OA, ~6.16% SA, ~8.11% MA of total wages (totals ~37% of wages when combined with rounding)
    "55_60": (0.1282, 0.0350, 0.1068),  # For 29.5% total
    "60_65": (0.0357, 0.0175, 0.1468),  # For 20.5% total
    "65_70": (0.0100, 0.0100, 0.1250),  # For 14.5% total
    "above_70": (0.0100, 0.0100, 0.0800),  # For 10% total
}

# Wage ceilings
OW_CEILING_MONTHLY = 8000.0  # Ordinary Wage ceiling per month (effective 1 Jan 2026)
AW_CEILING_ANNUAL = 102000.0  # Additional Wage ceiling per year


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CPFInput:
    """Input parameters for CPF contribution calculation."""

    citizenship_status: str  # "SC", "PR", "foreigner"
    age: int
    monthly_ow: float  # Ordinary Wages (basic + fixed allowances)
    monthly_aw: float = 0.0  # Additional Wages (bonus, etc.)
    pr_year: Optional[int] = None  # 1, 2, or 3+ for PRs
    ytd_ow: float = 0.0  # Year-to-date OW already contributed on
    ytd_aw: float = 0.0  # Year-to-date AW already contributed on


@dataclass(frozen=True)
class CPFResult:
    """Output of CPF contribution calculation."""

    employer_contribution: float
    employee_contribution: float
    total_contribution: float
    employer_rate: float
    employee_rate: float
    total_rate: float
    cpf_applicable: bool
    cpf_tier: str
    age_band: str
    ow_subject_to_cpf: float
    aw_subject_to_cpf: float
    ow_capped: bool
    aw_capped: bool
    allocation_oa: float
    allocation_sa: float
    allocation_ma: float
    breakdown: dict


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------


def _determine_age_band(age: int) -> str:
    """Map age to CPF age band."""
    if age < 55:
        return "55_below"
    elif age < 60:
        return "55_60"
    elif age < 65:
        return "60_65"
    elif age < 70:
        return "65_70"
    else:
        return "above_70"


def _determine_cpf_tier(citizenship_status: str, pr_year: Optional[int]) -> tuple[bool, str]:
    """Determine CPF applicability and tier.

    Returns:
        (applicable, tier)
    """
    if citizenship_status == "SC":
        return True, "sc_full"
    elif citizenship_status == "PR":
        if pr_year is None:
            raise ValueError("pr_year is required for PR employees")
        if pr_year == 1:
            return True, "pr_year1"
        elif pr_year == 2:
            return True, "pr_year2"
        else:
            return True, "pr_year3_plus"
    else:
        return False, "none"


def _apply_ow_ceiling(monthly_ow: float) -> tuple[float, bool]:
    """Apply the OW ceiling.

    Returns:
        (ow_subject_to_cpf, was_capped)
    """
    if monthly_ow > OW_CEILING_MONTHLY:
        return OW_CEILING_MONTHLY, True
    return monthly_ow, False


def _apply_aw_ceiling(monthly_aw: float, ytd_ow: float) -> tuple[float, bool]:
    """Apply the AW ceiling.

    AW ceiling = $102,000 - Total OW subject to CPF for the year.
    ytd_ow should include the current month's OW (capped).

    Returns:
        (aw_subject_to_cpf, was_capped)
    """
    aw_ceiling = max(0.0, AW_CEILING_ANNUAL - ytd_ow)
    if monthly_aw > aw_ceiling:
        return aw_ceiling, True
    return monthly_aw, False


def _round_cpf(amount: float) -> float:
    """Round CPF contribution to nearest dollar.

    CPF Board rounds to the nearest dollar (0.50 rounds up).
    """
    return round(amount)


def calculate_cpf_contributions(input_data: CPFInput) -> CPFResult:
    """Calculate CPF contributions for a single month.

    This is a pure, deterministic function. No DB or API calls.

    Args:
        input_data: CPF calculation input parameters.

    Returns:
        CPFResult with full breakdown.

    Raises:
        ValueError: If inputs are invalid (negative wages, missing pr_year, etc.)
    """
    # Validate
    if input_data.monthly_ow < 0:
        raise ValueError("monthly_ow must be non-negative")
    if input_data.monthly_aw < 0:
        raise ValueError("monthly_aw must be non-negative")
    if input_data.age < 0:
        raise ValueError("age must be non-negative")

    # Determine tier and age band
    cpf_applicable, cpf_tier = _determine_cpf_tier(
        input_data.citizenship_status, input_data.pr_year
    )
    age_band = _determine_age_band(input_data.age)

    # If CPF not applicable (foreigner), return zeros
    if not cpf_applicable:
        return CPFResult(
            employer_contribution=0.0,
            employee_contribution=0.0,
            total_contribution=0.0,
            employer_rate=0.0,
            employee_rate=0.0,
            total_rate=0.0,
            cpf_applicable=False,
            cpf_tier="none",
            age_band=age_band,
            ow_subject_to_cpf=0.0,
            aw_subject_to_cpf=0.0,
            ow_capped=False,
            aw_capped=False,
            allocation_oa=0.0,
            allocation_sa=0.0,
            allocation_ma=0.0,
            breakdown={},
        )

    # Look up rates
    rate_key = (cpf_tier, age_band)
    if rate_key not in CPF_RATE_TABLE:
        raise ValueError(f"No CPF rate found for tier={cpf_tier}, age_band={age_band}")

    employer_rate, employee_rate = CPF_RATE_TABLE[rate_key]
    total_rate = employer_rate + employee_rate

    # Apply ceilings
    ow_subject, ow_capped = _apply_ow_ceiling(input_data.monthly_ow)
    # For AW ceiling, include current month's capped OW in YTD
    total_ytd_ow = input_data.ytd_ow + ow_subject
    aw_subject, aw_capped = _apply_aw_ceiling(input_data.monthly_aw, total_ytd_ow)

    total_wages = ow_subject + aw_subject

    # Calculate contributions
    employer_contribution = _round_cpf(total_wages * employer_rate)
    employee_contribution = _round_cpf(total_wages * employee_rate)
    total_contribution = employer_contribution + employee_contribution

    # Allocate to accounts
    alloc = CPF_ALLOCATION_TABLE.get(age_band, (0.0, 0.0, 0.0))
    # Allocation is based on total contribution, not wages
    # The allocation percentages are of total wages, not of total contribution
    allocation_oa = _round_cpf(total_wages * alloc[0])
    allocation_sa = _round_cpf(total_wages * alloc[1])
    allocation_ma = total_contribution - allocation_oa - allocation_sa

    # Build breakdown
    breakdown = {
        "ow": {
            "gross": input_data.monthly_ow,
            "subject_to_cpf": ow_subject,
            "capped": ow_capped,
            "employer_cpf": _round_cpf(ow_subject * employer_rate),
            "employee_cpf": _round_cpf(ow_subject * employee_rate),
        },
        "aw": {
            "gross": input_data.monthly_aw,
            "subject_to_cpf": aw_subject,
            "capped": aw_capped,
            "employer_cpf": _round_cpf(aw_subject * employer_rate),
            "employee_cpf": _round_cpf(aw_subject * employee_rate),
        },
        "rates": {
            "employer": employer_rate,
            "employee": employee_rate,
            "total": total_rate,
        },
        "ceilings": {
            "ow_ceiling": OW_CEILING_MONTHLY,
            "aw_ceiling_remaining": max(0.0, AW_CEILING_ANNUAL - total_ytd_ow),
        },
    }

    return CPFResult(
        employer_contribution=employer_contribution,
        employee_contribution=employee_contribution,
        total_contribution=total_contribution,
        employer_rate=employer_rate,
        employee_rate=employee_rate,
        total_rate=total_rate,
        cpf_applicable=True,
        cpf_tier=cpf_tier,
        age_band=age_band,
        ow_subject_to_cpf=ow_subject,
        aw_subject_to_cpf=aw_subject,
        ow_capped=ow_capped,
        aw_capped=aw_capped,
        allocation_oa=allocation_oa,
        allocation_sa=allocation_sa,
        allocation_ma=allocation_ma,
        breakdown=breakdown,
    )
