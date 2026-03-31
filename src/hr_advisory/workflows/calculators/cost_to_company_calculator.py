"""Cost-to-Company Calculator — pure deterministic function.

Calculates total employment cost including:
- Base salary
- CPF employer contribution
- Foreign worker levy (if applicable)
- Skills Development Levy (SDL)
- Estimated insurance (WICA)

Provides full cost breakdown for budgeting purposes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hr_advisory.workflows.calculators.cpf_calculator import (
    CPF_RATE_TABLE,
)


@dataclass(frozen=True)
class CostToCompanyInput:
    monthly_salary: float
    citizenship: str  # "sc" | "pr" | "ep" | "sp" | "wp"
    age: int = 30
    pr_year: int = 3  # For PRs: 1, 2, or 3+
    pass_type: str = ""  # "ep" | "sp" | "wp" (for foreign workers)
    sector: str = "services"


@dataclass(frozen=True)
class CostToCompanyResult:
    monthly_salary: float
    cpf_employer: float
    levy: float
    sdl: float
    insurance_estimate: float
    total_monthly_cost: float
    total_annual_cost: float
    breakdown: dict[str, float]
    explanation: str


# SDL rate: 0.25% of monthly remuneration, min $2, max $11.25
_SDL_RATE = 0.0025
_SDL_MIN = 2.0
_SDL_MAX = 11.25

# Levy rates by pass type (basic tier — actual tier depends on quota position)
_LEVY_RATES: dict[str, float] = {
    "sp": 550.0,  # S Pass: $550-$650 depending on tier
    "wp": 450.0,  # WP: $300-$950 depending on sector and tier
}

# WICA insurance estimate (monthly equivalent)
_WICA_MONTHLY_ESTIMATE = 15.0  # Varies by industry, ~$150-$300/year


def _calculate_sdl(monthly_salary: float) -> float:
    """Calculate Skills Development Levy."""
    sdl = monthly_salary * _SDL_RATE
    return round(min(max(sdl, _SDL_MIN), _SDL_MAX), 2)


def _cpf_employer_rate(citizenship: str, age: int, pr_year: int) -> float:
    """Get CPF employer contribution rate.

    CPF_RATE_TABLE uses tuple keys: (tier, age_band) -> (employer_rate, employee_rate)
    Rates are already decimals (e.g. 0.17 = 17%).
    """
    if citizenship == "sc":
        tier = "sc_full"
    elif citizenship == "pr":
        if pr_year <= 1:
            tier = "pr_year1"
        elif pr_year == 2:
            tier = "pr_year2"
        else:
            tier = "pr_year3_plus"
    else:
        return 0.0  # No CPF for EP, SP, WP

    # Determine age band (must use strict < to match cpf_calculator boundaries)
    if age < 55:
        band = "55_below"
    elif age < 60:
        band = "55_60"
    elif age < 65:
        band = "60_65"
    elif age < 70:
        band = "65_70"
    else:
        band = "above_70"

    rates = CPF_RATE_TABLE.get((tier, band))
    if rates is None:
        return 0.0
    employer_rate, _ = rates
    return employer_rate


def calculate_cost_to_company(inp: CostToCompanyInput) -> CostToCompanyResult:
    """Calculate total cost of employing one person."""
    if not math.isfinite(inp.monthly_salary) or inp.monthly_salary < 0:
        raise ValueError("monthly_salary must be a finite non-negative number")
    if not math.isfinite(inp.age) or inp.age < 0:
        raise ValueError("age must be a finite non-negative number")
    # CPF employer contribution
    cpf_rate = _cpf_employer_rate(inp.citizenship, inp.age, inp.pr_year)
    cpf_employer = round(inp.monthly_salary * cpf_rate, 2)

    # Foreign worker levy
    levy = 0.0
    effective_pass = inp.pass_type or inp.citizenship
    if effective_pass in _LEVY_RATES:
        levy = _LEVY_RATES[effective_pass]

    # SDL
    sdl = _calculate_sdl(inp.monthly_salary)

    # Insurance estimate
    insurance = _WICA_MONTHLY_ESTIMATE if inp.citizenship not in ("sc", "pr") else 0.0

    # Totals
    total_monthly = round(inp.monthly_salary + cpf_employer + levy + sdl + insurance, 2)
    total_annual = round(total_monthly * 12, 2)

    breakdown = {
        "base_salary": inp.monthly_salary,
        "cpf_employer": cpf_employer,
        "levy": levy,
        "sdl": sdl,
        "insurance_estimate": insurance,
    }

    parts: list[str] = [f"Base salary: ${inp.monthly_salary:,.2f}"]
    if cpf_employer > 0:
        parts.append(f"CPF employer ({cpf_rate * 100:.1f}%): ${cpf_employer:,.2f}")
    if levy > 0:
        parts.append(f"Foreign worker levy ({effective_pass.upper()}): ${levy:,.2f}")
    parts.append(f"SDL: ${sdl:.2f}")
    if insurance > 0:
        parts.append(f"WICA insurance estimate: ${insurance:.2f}")
    parts.append(f"Total monthly cost: ${total_monthly:,.2f}")
    parts.append(f"Total annual cost: ${total_annual:,.2f}")

    explanation = " | ".join(parts)

    return CostToCompanyResult(
        monthly_salary=inp.monthly_salary,
        cpf_employer=cpf_employer,
        levy=levy,
        sdl=sdl,
        insurance_estimate=insurance,
        total_monthly_cost=total_monthly,
        total_annual_cost=total_annual,
        breakdown=breakdown,
        explanation=explanation,
    )
