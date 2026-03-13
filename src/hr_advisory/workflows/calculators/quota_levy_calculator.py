"""Foreign Worker Quota & Levy Calculator — pure deterministic functions.

Computes:
- Current dependency ratio and DRC utilisation
- Projected ratio after a hiring scenario
- Sub-quota checks (S Pass, WP)
- Levy tier and monthly cost

All constants reflect MOM regulations effective 1 January 2026.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# DRC by sector — Dependency Ratio Ceiling
# Key: sector → (overall_drc, wp_sub_drc or None, sp_sub_drc or None)
# ---------------------------------------------------------------------------

SECTOR_DRC: dict[str, dict] = {
    "services": {
        "overall_drc": 0.35,
        "wp_sub_drc": None,
        "sp_sub_drc": 0.15,
    },
    "manufacturing": {
        "overall_drc": 0.60,
        "wp_sub_drc": 0.25,
        "sp_sub_drc": None,
    },
    "construction": {
        "overall_drc": 0.875,
        "wp_sub_drc": None,
        "sp_sub_drc": 0.15,
    },
    "process": {
        "overall_drc": 0.60,
        "wp_sub_drc": 0.25,
        "sp_sub_drc": None,
    },
    "marine": {
        "overall_drc": 0.60,
        "wp_sub_drc": 0.25,
        "sp_sub_drc": None,
    },
}

# ---------------------------------------------------------------------------
# Levy rates by sector and pass type
# Key: (sector, pass_type) → list of tiers
# Each tier: (threshold_pct, monthly_levy)
# threshold_pct is the DRC utilisation band upper limit
# ---------------------------------------------------------------------------

LEVY_RATES: dict[tuple[str, str], list[tuple[float, float]]] = {
    ("services", "wp"): [
        (1.0, 450.0),  # Tier 1 (basic)
        (1.0, 650.0),  # Tier 2 (higher — applied to WPs beyond basic tier)
    ],
    ("services", "sp"): [
        (0.10, 550.0),  # Tier 1 (up to 10% of workforce)
        (1.0, 650.0),  # Tier 2 (beyond 10%)
    ],
    ("manufacturing", "wp"): [
        (1.0, 450.0),
        (1.0, 650.0),
    ],
    ("manufacturing", "sp"): [
        (0.10, 550.0),
        (1.0, 650.0),
    ],
    ("construction", "wp"): [
        (1.0, 450.0),
        (1.0, 650.0),
    ],
    ("construction", "sp"): [
        (0.10, 550.0),
        (1.0, 650.0),
    ],
    ("process", "wp"): [
        (1.0, 450.0),
        (1.0, 650.0),
    ],
    ("process", "sp"): [
        (0.10, 550.0),
        (1.0, 650.0),
    ],
    ("marine", "wp"): [
        (1.0, 300.0),
        (1.0, 450.0),
    ],
    ("marine", "sp"): [
        (0.10, 550.0),
        (1.0, 650.0),
    ],
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuotaLevyInput:
    """Input for quota and levy calculation."""

    sector: str
    headcount_local: int  # SC + PR
    headcount_ep: int = 0
    headcount_sp: int = 0
    headcount_wp: int = 0
    # Scenario: what we want to hire
    scenario_hire_sp: int = 0
    scenario_hire_wp: int = 0


@dataclass(frozen=True)
class QuotaLevyResult:
    """Output of quota and levy calculation."""

    sector: str
    total_workforce: int
    local_count: int
    foreign_count: int
    current_ratio: float
    drc_limit: float
    drc_utilisation: float  # current_ratio / drc_limit as percentage
    within_limit: bool
    headroom_foreign: int  # how many more foreign workers can be hired
    # Sub-quota results
    sp_ratio: float
    sp_sub_drc: Optional[float]
    sp_within_sub_limit: bool
    wp_ratio: float
    wp_sub_drc: Optional[float]
    wp_within_sub_limit: bool
    # Scenario projection
    projected_ratio: float
    projected_within_limit: bool
    projected_sp_within_sub_limit: bool
    projected_wp_within_sub_limit: bool
    scenario_feasible: bool
    # Levy
    current_monthly_levy_sp: float
    current_monthly_levy_wp: float
    current_total_monthly_levy: float
    projected_monthly_levy_sp: float
    projected_monthly_levy_wp: float
    projected_total_monthly_levy: float
    levy_increase: float
    # Warnings
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------


def _get_sector_drc(sector: str) -> dict:
    """Get DRC configuration for a sector."""
    sector_lower = sector.lower()
    if sector_lower not in SECTOR_DRC:
        raise ValueError(
            f"Unknown sector '{sector}'. " f"Valid sectors: {sorted(SECTOR_DRC.keys())}"
        )
    return SECTOR_DRC[sector_lower]


def _calculate_ratio(foreign_count: int, total_workforce: int) -> float:
    """Calculate the dependency ratio (foreign / total)."""
    if total_workforce == 0:
        return 0.0
    return foreign_count / total_workforce


def _calculate_sub_ratio(pass_count: int, total_workforce: int) -> float:
    """Calculate a sub-quota ratio."""
    if total_workforce == 0:
        return 0.0
    return pass_count / total_workforce


def _calculate_headroom(
    drc_limit: float,
    local_count: int,
    current_foreign: int,
    ep_count: int,
) -> int:
    """Calculate how many more foreign workers (SP+WP) can be hired.

    Formula: max_foreign = (drc_limit * total) / (1 - drc_limit) approximately
    But we need to solve: foreign / (local + ep + foreign) <= drc_limit
    => foreign <= drc_limit * (local + ep) / (1 - drc_limit)
    """
    if drc_limit >= 1.0:
        return 999  # No effective limit
    denominator = 1.0 - drc_limit
    max_foreign_total = int(drc_limit * (local_count + ep_count) / denominator)
    headroom = max(0, max_foreign_total - current_foreign)
    return headroom


def _calculate_levy(
    sector: str,
    pass_type: str,
    count: int,
    total_workforce: int,
) -> float:
    """Calculate monthly levy for a given pass type and count.

    For simplicity, uses the basic (Tier 1) rate for all workers
    of that type. In practice, tiering depends on DRC utilisation
    bands which are more complex.
    """
    key = (sector.lower(), pass_type.lower())
    tiers = LEVY_RATES.get(key)
    if not tiers or count == 0:
        return 0.0

    # Use basic tier rate for all workers of this type
    basic_rate = tiers[0][1]
    return basic_rate * count


def calculate_quota_levy(input_data: QuotaLevyInput) -> QuotaLevyResult:
    """Calculate foreign worker quota utilisation and levy costs.

    Pure deterministic function — no DB or API calls.

    Args:
        input_data: Quota/levy calculation input.

    Returns:
        QuotaLevyResult with current and projected metrics.

    Raises:
        ValueError: If sector is invalid or headcount is negative.
    """
    # Validate
    if input_data.headcount_local < 0:
        raise ValueError("headcount_local must be non-negative")
    if input_data.headcount_ep < 0:
        raise ValueError("headcount_ep must be non-negative")
    if input_data.headcount_sp < 0:
        raise ValueError("headcount_sp must be non-negative")
    if input_data.headcount_wp < 0:
        raise ValueError("headcount_wp must be non-negative")

    sector_config = _get_sector_drc(input_data.sector)
    drc_limit = sector_config["overall_drc"]
    sp_sub_drc = sector_config["sp_sub_drc"]
    wp_sub_drc = sector_config["wp_sub_drc"]

    # Current state
    foreign_sp_wp = input_data.headcount_sp + input_data.headcount_wp
    total = input_data.headcount_local + input_data.headcount_ep + foreign_sp_wp

    current_ratio = _calculate_ratio(foreign_sp_wp, total)
    sp_ratio = _calculate_sub_ratio(input_data.headcount_sp, total)
    wp_ratio = _calculate_sub_ratio(input_data.headcount_wp, total)

    within_limit = current_ratio <= drc_limit
    drc_utilisation = (current_ratio / drc_limit * 100) if drc_limit > 0 else 0.0

    sp_within_sub = True
    if sp_sub_drc is not None:
        sp_within_sub = sp_ratio <= sp_sub_drc

    wp_within_sub = True
    if wp_sub_drc is not None:
        wp_within_sub = wp_ratio <= wp_sub_drc

    headroom = _calculate_headroom(
        drc_limit, input_data.headcount_local, foreign_sp_wp, input_data.headcount_ep
    )

    # Projected state (after scenario)
    proj_sp = input_data.headcount_sp + input_data.scenario_hire_sp
    proj_wp = input_data.headcount_wp + input_data.scenario_hire_wp
    proj_foreign = proj_sp + proj_wp
    proj_total = input_data.headcount_local + input_data.headcount_ep + proj_foreign

    proj_ratio = _calculate_ratio(proj_foreign, proj_total)
    proj_sp_ratio = _calculate_sub_ratio(proj_sp, proj_total)
    proj_wp_ratio = _calculate_sub_ratio(proj_wp, proj_total)

    proj_within_limit = proj_ratio <= drc_limit

    proj_sp_within_sub = True
    if sp_sub_drc is not None:
        proj_sp_within_sub = proj_sp_ratio <= sp_sub_drc

    proj_wp_within_sub = True
    if wp_sub_drc is not None:
        proj_wp_within_sub = proj_wp_ratio <= wp_sub_drc

    scenario_feasible = proj_within_limit and proj_sp_within_sub and proj_wp_within_sub

    # Levy calculations
    sector = input_data.sector.lower()
    current_levy_sp = _calculate_levy(sector, "sp", input_data.headcount_sp, total)
    current_levy_wp = _calculate_levy(sector, "wp", input_data.headcount_wp, total)
    current_total_levy = current_levy_sp + current_levy_wp

    proj_levy_sp = _calculate_levy(sector, "sp", proj_sp, proj_total)
    proj_levy_wp = _calculate_levy(sector, "wp", proj_wp, proj_total)
    proj_total_levy = proj_levy_sp + proj_levy_wp
    levy_increase = proj_total_levy - current_total_levy

    # Warnings
    warnings = []
    if drc_utilisation > 90:
        warnings.append(
            f"Approaching DRC ceiling: {drc_utilisation:.1f}% utilised. "
            f"Only {headroom} more foreign workers can be hired."
        )
    if not scenario_feasible:
        reasons = []
        if not proj_within_limit:
            reasons.append(f"overall DRC ({proj_ratio:.2%} > {drc_limit:.0%})")
        if not proj_sp_within_sub:
            reasons.append(f"S Pass sub-quota ({proj_sp_ratio:.2%} > {sp_sub_drc:.0%})")
        if not proj_wp_within_sub:
            reasons.append(f"WP sub-quota ({proj_wp_ratio:.2%} > {wp_sub_drc:.0%})")
        warnings.append(f"Scenario not feasible: exceeds {', '.join(reasons)}")

    return QuotaLevyResult(
        sector=input_data.sector,
        total_workforce=total,
        local_count=input_data.headcount_local,
        foreign_count=foreign_sp_wp,
        current_ratio=round(current_ratio, 4),
        drc_limit=drc_limit,
        drc_utilisation=round(drc_utilisation, 1),
        within_limit=within_limit,
        headroom_foreign=headroom,
        sp_ratio=round(sp_ratio, 4),
        sp_sub_drc=sp_sub_drc,
        sp_within_sub_limit=sp_within_sub,
        wp_ratio=round(wp_ratio, 4),
        wp_sub_drc=wp_sub_drc,
        wp_within_sub_limit=wp_within_sub,
        projected_ratio=round(proj_ratio, 4),
        projected_within_limit=proj_within_limit,
        projected_sp_within_sub_limit=proj_sp_within_sub,
        projected_wp_within_sub_limit=proj_wp_within_sub,
        scenario_feasible=scenario_feasible,
        current_monthly_levy_sp=current_levy_sp,
        current_monthly_levy_wp=current_levy_wp,
        current_total_monthly_levy=current_total_levy,
        projected_monthly_levy_sp=proj_levy_sp,
        projected_monthly_levy_wp=proj_levy_wp,
        projected_total_monthly_levy=proj_total_levy,
        levy_increase=levy_increase,
        warnings=warnings,
    )
