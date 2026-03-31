"""Leave Entitlement Calculator — pure deterministic functions.

Computes Singapore statutory leave entitlements:
- Annual leave (EA Section 88A)
- Sick leave (EA Section 89)
- Maternity leave (EA Part IX + CDCSA)
- Paternity leave (CDCSA)
- Shared parental leave (CDCSA)
- Childcare leave (CDCSA)
- Infant care leave (CDCSA)
- Adoption leave (CDCSA)

All calculations reflect statutory minimums as at 1 January 2026.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeaveInput:
    """Input for leave entitlement calculation."""

    years_of_service: float  # can be fractional for pro-ration
    employment_type: str  # "full_time", "part_time"
    leave_type: str  # which leave to calculate
    citizenship_status: str  # "SC", "PR", "foreigner"
    number_of_children: int = 0
    child_ages: list[int] = field(default_factory=list)
    child_citizenship: str = ""  # "SC", "PR", or ""
    child_order: int = 1  # 1st, 2nd, 3rd+ child (for maternity)


@dataclass(frozen=True)
class LeaveResult:
    """Output of leave entitlement calculation."""

    leave_type: str
    eligible: bool
    days_entitled: float
    calculation_basis: str
    who_pays: str  # "employer", "government", "split"
    government_claim_cap: Optional[float]  # per-period cap if government-paid
    pro_rated: bool
    notes: str


# ---------------------------------------------------------------------------
# Annual leave (EA Section 88A)
# ---------------------------------------------------------------------------


def _calculate_annual_leave(input_data: LeaveInput) -> LeaveResult:
    """7 days first year, +1 per year, max 14 days.

    Pro-rated for partial years. Requires 3 months minimum service.
    """
    if input_data.years_of_service < 0.25:
        return LeaveResult(
            leave_type="annual_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Minimum 3 months of service required.",
            who_pays="employer",
            government_claim_cap=None,
            pro_rated=False,
            notes="Employee has less than 3 months of service.",
        )

    completed_years = int(input_data.years_of_service)
    fractional_year = input_data.years_of_service - completed_years

    # Entitlement for completed year
    if completed_years == 0:
        # First year, pro-rate
        year_entitlement = 7
        days = round(fractional_year * year_entitlement * 2) / 2  # nearest half-day
        return LeaveResult(
            leave_type="annual_leave",
            eligible=True,
            days_entitled=days,
            calculation_basis=f"Pro-rated: {input_data.years_of_service:.1f} years x {year_entitlement} days = {days} days",
            who_pays="employer",
            government_claim_cap=None,
            pro_rated=True,
            notes="First year: pro-rated from start date.",
        )

    year_entitlement = min(7 + (completed_years - 1), 14)
    if fractional_year > 0:
        days = round(fractional_year * year_entitlement * 2) / 2
        return LeaveResult(
            leave_type="annual_leave",
            eligible=True,
            days_entitled=days,
            calculation_basis=f"Year {completed_years + 1}: pro-rated {fractional_year:.2f} x {year_entitlement} = {days} days",
            who_pays="employer",
            government_claim_cap=None,
            pro_rated=True,
            notes=f"Year {completed_years + 1} entitlement: {year_entitlement} days (pro-rated for partial year).",
        )

    return LeaveResult(
        leave_type="annual_leave",
        eligible=True,
        days_entitled=year_entitlement,
        calculation_basis=f"Year {completed_years}: {year_entitlement} days (7 base + {max(0, completed_years - 1)} additional, max 14)",
        who_pays="employer",
        government_claim_cap=None,
        pro_rated=False,
        notes=f"Full year entitlement for year {completed_years} of service.",
    )


# ---------------------------------------------------------------------------
# Sick leave (EA Section 89)
# ---------------------------------------------------------------------------

SICK_LEAVE_TABLE = {
    3: (5, 15),
    4: (8, 30),
    5: (11, 45),
    6: (14, 60),
}


def _calculate_sick_leave(input_data: LeaveInput) -> LeaveResult:
    """14 outpatient + 60 hospitalisation days (after 6 months).

    Pro-rated for 3-5 months. Not eligible under 3 months.
    """
    months = int(input_data.years_of_service * 12)

    if months < 3:
        return LeaveResult(
            leave_type="sick_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Minimum 3 months of service required.",
            who_pays="employer",
            government_claim_cap=None,
            pro_rated=False,
            notes="Employee has less than 3 months of service.",
        )

    if months >= 6:
        outpatient, hospitalisation = 14, 60
    elif months in SICK_LEAVE_TABLE:
        outpatient, hospitalisation = SICK_LEAVE_TABLE[months]
    else:
        outpatient, hospitalisation = 14, 60

    total = hospitalisation  # hospitalisation includes outpatient days
    return LeaveResult(
        leave_type="sick_leave",
        eligible=True,
        days_entitled=total,
        calculation_basis=f"{outpatient} outpatient + {hospitalisation - outpatient} hospitalisation-only = {hospitalisation} total days",
        who_pays="employer",
        government_claim_cap=None,
        pro_rated=months < 6,
        notes=f"After {months} months: {outpatient} outpatient days, up to {hospitalisation} total if hospitalised.",
    )


# ---------------------------------------------------------------------------
# Maternity leave (EA Part IX + CDCSA)
# ---------------------------------------------------------------------------


def _calculate_maternity_leave(input_data: LeaveInput) -> LeaveResult:
    """16 weeks (CDCSA for SC child) or 8 weeks (EA only)."""
    if input_data.years_of_service < 0.25:
        return LeaveResult(
            leave_type="maternity_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Minimum 3 months of service required.",
            who_pays="employer",
            government_claim_cap=None,
            pro_rated=False,
            notes="Employee has less than 3 months of service for paid maternity leave.",
        )

    if input_data.child_citizenship == "SC":
        weeks = 16
        days = weeks * 7
        if input_data.child_order >= 3:
            who_pays = "government"
            notes = f"Third or subsequent child: all {weeks} weeks government-paid."
            gov_cap = 10000.0  # per 4-week period
        else:
            who_pays = "split"
            notes = f"First 8 weeks employer-paid, last 8 weeks government-paid."
            gov_cap = 10000.0
        return LeaveResult(
            leave_type="maternity_leave",
            eligible=True,
            days_entitled=days,
            calculation_basis=f"{weeks} weeks ({days} days) under CDCSA",
            who_pays=who_pays,
            government_claim_cap=gov_cap,
            pro_rated=False,
            notes=notes,
        )

    # Non-SC child or child citizenship not specified
    weeks = 8
    days = weeks * 7
    return LeaveResult(
        leave_type="maternity_leave",
        eligible=True,
        days_entitled=days,
        calculation_basis=f"{weeks} weeks ({days} days) under EA Part IX",
        who_pays="employer",
        government_claim_cap=None,
        pro_rated=False,
        notes="8 weeks employer-paid maternity leave (non-SC child).",
    )


# ---------------------------------------------------------------------------
# Paternity leave (CDCSA)
# ---------------------------------------------------------------------------


def _calculate_paternity_leave(input_data: LeaveInput) -> LeaveResult:
    """4 weeks government-paid (since 1 Jan 2025)."""
    if input_data.citizenship_status == "foreigner":
        return LeaveResult(
            leave_type="paternity_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Not available to foreign employees.",
            who_pays="government",
            government_claim_cap=None,
            pro_rated=False,
            notes="Paternity leave requires SC or PR citizenship.",
        )

    if input_data.child_citizenship != "SC":
        return LeaveResult(
            leave_type="paternity_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Child must be a Singapore citizen.",
            who_pays="government",
            government_claim_cap=None,
            pro_rated=False,
            notes="Government-paid paternity leave requires child to be SC.",
        )

    weeks = 4
    days = weeks * 7
    return LeaveResult(
        leave_type="paternity_leave",
        eligible=True,
        days_entitled=days,
        calculation_basis=f"{weeks} weeks ({days} days) government-paid",
        who_pays="government",
        government_claim_cap=2500.0,  # per week
        pro_rated=False,
        notes="4 weeks government-paid paternity leave (capped at $2,500/week, since 1 Jan 2025).",
    )


# ---------------------------------------------------------------------------
# Childcare leave (CDCSA)
# ---------------------------------------------------------------------------


def _calculate_childcare_leave(input_data: LeaveInput) -> LeaveResult:
    """6 days/year per parent for child below age 7."""
    if input_data.citizenship_status == "foreigner":
        return LeaveResult(
            leave_type="childcare_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Not available to foreign employees.",
            who_pays="split",
            government_claim_cap=None,
            pro_rated=False,
            notes="Childcare leave requires SC or PR citizenship.",
        )

    eligible_children = [age for age in input_data.child_ages if age < 7]
    if not eligible_children:
        return LeaveResult(
            leave_type="childcare_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="No children below age 7.",
            who_pays="split",
            government_claim_cap=None,
            pro_rated=False,
            notes="Childcare leave requires at least one child below age 7.",
        )

    if input_data.child_citizenship != "SC":
        days = 2
        return LeaveResult(
            leave_type="childcare_leave",
            eligible=True,
            days_entitled=days,
            calculation_basis=f"{days} days (non-SC child)",
            who_pays="employer",
            government_claim_cap=None,
            pro_rated=False,
            notes="2 days employer-paid childcare leave (child is not SC).",
        )

    days = 6
    return LeaveResult(
        leave_type="childcare_leave",
        eligible=True,
        days_entitled=days,
        calculation_basis=f"{days} days per year (first 3 employer-paid, next 3 government-paid)",
        who_pays="split",
        government_claim_cap=500.0,  # per day
        pro_rated=False,
        notes="6 days: 3 employer-paid + 3 government-paid (capped $500/day).",
    )


# ---------------------------------------------------------------------------
# Infant care leave (CDCSA)
# ---------------------------------------------------------------------------


def _calculate_infant_care_leave(input_data: LeaveInput) -> LeaveResult:
    """6 days/year per parent for child below age 2."""
    if input_data.citizenship_status == "foreigner":
        return LeaveResult(
            leave_type="infant_care_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Not available to foreign employees.",
            who_pays="split",
            government_claim_cap=None,
            pro_rated=False,
            notes="Infant care leave requires SC or PR citizenship.",
        )

    eligible_infants = [age for age in input_data.child_ages if age < 2]
    if not eligible_infants:
        return LeaveResult(
            leave_type="infant_care_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="No children below age 2.",
            who_pays="split",
            government_claim_cap=None,
            pro_rated=False,
            notes="Infant care leave requires at least one child below age 2.",
        )

    days = 6
    return LeaveResult(
        leave_type="infant_care_leave",
        eligible=True,
        days_entitled=days,
        calculation_basis=f"{days} days per year (first 2 employer-paid, next 4 government-paid)",
        who_pays="split",
        government_claim_cap=500.0,
        pro_rated=False,
        notes="6 days: 2 employer-paid + 4 government-paid. In addition to childcare leave.",
    )


# ---------------------------------------------------------------------------
# Shared parental leave (CDCSA)
# ---------------------------------------------------------------------------


def _calculate_shared_parental_leave(input_data: LeaveInput) -> LeaveResult:
    """Father can share up to 4 weeks from mother's 16-week maternity."""
    if input_data.citizenship_status == "foreigner":
        return LeaveResult(
            leave_type="shared_parental_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Not available to foreign employees.",
            who_pays="government",
            government_claim_cap=None,
            pro_rated=False,
            notes="Shared parental leave requires SC or PR citizenship.",
        )

    if input_data.child_citizenship != "SC":
        return LeaveResult(
            leave_type="shared_parental_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Child must be a Singapore citizen.",
            who_pays="government",
            government_claim_cap=None,
            pro_rated=False,
            notes="Shared parental leave requires child to be SC.",
        )

    weeks = 4
    days = weeks * 7
    return LeaveResult(
        leave_type="shared_parental_leave",
        eligible=True,
        days_entitled=days,
        calculation_basis=f"Up to {weeks} weeks ({days} days) shared from mother's maternity leave",
        who_pays="government",
        government_claim_cap=2500.0,
        pro_rated=False,
        notes="4 weeks government-paid, shared from mother's 16-week maternity entitlement.",
    )


# ---------------------------------------------------------------------------
# Adoption leave (CDCSA)
# ---------------------------------------------------------------------------


def _calculate_adoption_leave(input_data: LeaveInput) -> LeaveResult:
    """12 weeks for adoptive mothers."""
    if input_data.child_citizenship != "SC":
        return LeaveResult(
            leave_type="adoption_leave",
            eligible=False,
            days_entitled=0,
            calculation_basis="Child must be a Singapore citizen.",
            who_pays="split",
            government_claim_cap=None,
            pro_rated=False,
            notes="Adoption leave requires child to be SC and under 12 months.",
        )

    weeks = 12
    days = weeks * 7
    return LeaveResult(
        leave_type="adoption_leave",
        eligible=True,
        days_entitled=days,
        calculation_basis=f"{weeks} weeks ({days} days): first 4 employer-paid, next 8 government-paid",
        who_pays="split",
        government_claim_cap=10000.0,
        pro_rated=False,
        notes="12 weeks total: 4 weeks employer-paid + 8 weeks government-paid.",
    )


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

LEAVE_CALCULATORS = {
    "annual_leave": _calculate_annual_leave,
    "sick_leave": _calculate_sick_leave,
    "maternity_leave": _calculate_maternity_leave,
    "paternity_leave": _calculate_paternity_leave,
    "childcare_leave": _calculate_childcare_leave,
    "infant_care_leave": _calculate_infant_care_leave,
    "shared_parental_leave": _calculate_shared_parental_leave,
    "adoption_leave": _calculate_adoption_leave,
}


def calculate_leave_entitlement(input_data: LeaveInput) -> LeaveResult:
    """Calculate leave entitlement for a specific leave type.

    Pure deterministic function — no DB or API calls.

    Args:
        input_data: Leave calculation input with leave_type specified.

    Returns:
        LeaveResult with entitlement details.

    Raises:
        ValueError: If leave_type is not recognized or inputs are invalid.
    """
    # NaN/Inf guard — years_of_service is a float that feeds into numeric
    # comparisons (< 0.25, int(), etc.). NaN bypasses all comparisons silently;
    # Inf produces incorrect int() conversions. Validate finiteness first.
    if not math.isfinite(input_data.years_of_service) or input_data.years_of_service < 0:
        raise ValueError("years_of_service must be a finite non-negative number")

    calculator = LEAVE_CALCULATORS.get(input_data.leave_type)
    if calculator is None:
        raise ValueError(
            f"Unknown leave type '{input_data.leave_type}'. "
            f"Valid types: {sorted(LEAVE_CALCULATORS.keys())}"
        )
    return calculator(input_data)
