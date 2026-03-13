"""Retrenchment Benefit Calculator — pure deterministic function.

Calculates retrenchment benefit based on:
- Years of service
- Monthly salary
- Sector (for market norm reference)

Note: There is no statutory minimum for retrenchment benefits in Singapore.
The EA does not mandate retrenchment benefits. However, the Tripartite
Advisory on Managing Excess Manpower recommends a market norm.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrenchmentInput:
    years_of_service: float
    monthly_salary: float
    sector: str = ""


@dataclass(frozen=True)
class RetrenchmentResult:
    statutory_minimum: float | None  # None = no statutory minimum
    market_norm_per_year: float
    market_norm_total: float
    explanation: str
    sector_notes: str


# Market norms by sector (weeks of salary per year of service)
# Source: Tripartite Advisory on Managing Excess Manpower
_SECTOR_NORMS: dict[str, tuple[float, str]] = {
    "services": (
        2.0,
        "Services sector norm: 2 weeks per year of service",
    ),
    "manufacturing": (
        2.0,
        "Manufacturing sector norm: 2 weeks per year of service",
    ),
    "construction": (
        1.5,
        "Construction sector norm: 1-2 weeks per year (lower end due to project-based work)",
    ),
    "technology": (
        3.0,
        "Technology sector: 2-4 weeks per year (higher end of market norm)",
    ),
    "finance": (
        3.0,
        "Financial services: 2-4 weeks per year (higher end of market norm)",
    ),
}
_DEFAULT_NORM = (2.0, "General market norm: 2 weeks of salary per year of service")


def calculate_retrenchment(inp: RetrenchmentInput) -> RetrenchmentResult:
    """Calculate retrenchment benefit estimates.

    Singapore has NO statutory minimum for retrenchment benefits.
    The Tripartite Advisory recommends a prevailing market norm of
    2 weeks to 1 month of salary per completed year of service.
    """
    weeks_per_year, sector_note = _SECTOR_NORMS.get(
        inp.sector.lower(), _DEFAULT_NORM
    )

    weekly_salary = inp.monthly_salary / 4.0
    per_year_benefit = round(weekly_salary * weeks_per_year, 2)
    total_benefit = round(per_year_benefit * inp.years_of_service, 2)

    explanation = (
        f"Singapore does not have a statutory minimum for retrenchment benefits. "
        f"The Tripartite Advisory on Managing Excess Manpower recommends "
        f"retrenchment benefits as a norm, not a legal requirement. "
        f"Market norm: {weeks_per_year:.1f} weeks of salary per completed year of service. "
        f"Estimated benefit: ${per_year_benefit:,.2f}/year × {inp.years_of_service:.1f} years "
        f"= ${total_benefit:,.2f}. "
        f"Employees with less than 2 years of service are generally not eligible "
        f"for retrenchment benefits under most company policies."
    )

    return RetrenchmentResult(
        statutory_minimum=None,
        market_norm_per_year=per_year_benefit,
        market_norm_total=total_benefit,
        explanation=explanation,
        sector_notes=sector_note,
    )
