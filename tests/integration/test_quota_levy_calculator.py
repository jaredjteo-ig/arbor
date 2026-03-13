"""Tests for foreign worker quota and levy calculator."""

import pytest

from hr_advisory.workflows.calculators.quota_levy_calculator import (
    QuotaLevyInput,
    QuotaLevyResult,
    SECTOR_DRC,
    calculate_quota_levy,
)


class TestSectorDRC:
    """Verify sector DRC tables."""

    def test_all_sectors_present(self):
        for sector in ("services", "manufacturing", "construction", "process", "marine"):
            assert sector in SECTOR_DRC

    def test_services_drc(self):
        assert SECTOR_DRC["services"]["overall_drc"] == 0.35
        assert SECTOR_DRC["services"]["sp_sub_drc"] == 0.15

    def test_manufacturing_drc(self):
        assert SECTOR_DRC["manufacturing"]["overall_drc"] == 0.60
        assert SECTOR_DRC["manufacturing"]["wp_sub_drc"] == 0.25


class TestQuotaBasic:
    """Basic quota calculation tests."""

    def test_services_within_quota(self):
        """Services company well within DRC."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=3,
                headcount_wp=2,
            )
        )
        assert result.within_limit is True
        # 5 foreign / 25 total = 20% < 35%
        assert result.current_ratio == round(5 / 25, 4)
        assert result.drc_limit == 0.35

    def test_services_at_limit(self):
        """Services company at DRC limit."""
        # 35% ratio: need foreign / total = 0.35
        # If local = 13, foreign = 7: 7/20 = 0.35
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=13,
                headcount_sp=3,
                headcount_wp=4,
            )
        )
        assert result.within_limit is True  # at limit is within

    def test_services_exceeds_limit(self):
        """Services company exceeding DRC."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=10,
                headcount_sp=5,
                headcount_wp=5,
            )
        )
        # 10 foreign / 20 total = 50% > 35%
        assert result.within_limit is False

    def test_manufacturing_higher_limit(self):
        """Manufacturing has higher 60% DRC."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="manufacturing",
                headcount_local=10,
                headcount_sp=5,
                headcount_wp=8,
            )
        )
        # 13 foreign / 23 total = 56.5% < 60%
        assert result.within_limit is True

    def test_zero_workforce(self):
        """Zero workforce should return zero ratios."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=0,
            )
        )
        assert result.current_ratio == 0.0
        assert result.within_limit is True

    def test_invalid_sector_raises(self):
        with pytest.raises(ValueError, match="Unknown sector"):
            calculate_quota_levy(
                QuotaLevyInput(
                    sector="invalid",
                    headcount_local=10,
                )
            )


class TestSubQuota:
    """Sub-quota tests (S Pass and WP sub-DRC)."""

    def test_services_sp_sub_quota(self):
        """Services sector S Pass sub-quota at 15%."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=4,
                headcount_wp=1,
            )
        )
        # SP: 4/25 = 16% > 15%
        assert result.sp_sub_drc == 0.15
        assert result.sp_within_sub_limit is False

    def test_manufacturing_wp_sub_quota(self):
        """Manufacturing WP sub-quota at 25%."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="manufacturing",
                headcount_local=10,
                headcount_sp=2,
                headcount_wp=8,
            )
        )
        # WP: 8/20 = 40% > 25%
        assert result.wp_sub_drc == 0.25
        assert result.wp_within_sub_limit is False


class TestScenario:
    """What-if scenario tests."""

    def test_feasible_hire(self):
        """Hiring within quota limits."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=2,
                headcount_wp=1,
                scenario_hire_sp=1,
            )
        )
        # Current: 3/23 = 13% < 35% ✓
        # Projected: 4/24 = 16.7% < 35% ✓
        assert result.scenario_feasible is True
        assert result.projected_within_limit is True

    def test_infeasible_hire(self):
        """Hiring would exceed quota."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=10,
                headcount_sp=3,
                headcount_wp=2,
                scenario_hire_wp=5,
            )
        )
        # Current: 5/15 = 33% < 35% ✓
        # Projected: 10/20 = 50% > 35% ✗
        assert result.scenario_feasible is False
        assert result.projected_within_limit is False
        assert any("not feasible" in w for w in result.warnings)

    def test_sp_sub_quota_breach_in_scenario(self):
        """Scenario breaches S Pass sub-quota even if overall DRC OK."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=2,
                headcount_wp=1,
                scenario_hire_sp=3,
            )
        )
        # Current SP: 2/23 = 8.7% < 15% ✓
        # Projected SP: 5/26 = 19.2% > 15% ✗
        # Overall: 8/26 = 30.8% < 35% ✓
        assert result.projected_within_limit is True
        assert result.projected_sp_within_sub_limit is False
        assert result.scenario_feasible is False


class TestLevy:
    """Levy calculation tests."""

    def test_services_wp_levy(self):
        """Services sector WP levy."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_wp=3,
            )
        )
        # 3 WPs * $450 = $1,350
        assert result.current_monthly_levy_wp == 1350.0

    def test_services_sp_levy(self):
        """Services sector S Pass levy."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=2,
            )
        )
        # 2 SPs * $550 = $1,100
        assert result.current_monthly_levy_sp == 1100.0

    def test_levy_increase_from_scenario(self):
        """Levy increases from hiring scenario."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=2,
                headcount_wp=1,
                scenario_hire_wp=2,
            )
        )
        # Current: 2 SP * $550 + 1 WP * $450 = $1,550
        # Projected: 2 SP * $550 + 3 WP * $450 = $2,450
        assert result.current_total_monthly_levy == 1550.0
        assert result.projected_total_monthly_levy == 2450.0
        assert result.levy_increase == 900.0

    def test_no_foreign_workers_no_levy(self):
        """No foreign workers = no levy."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
            )
        )
        assert result.current_total_monthly_levy == 0.0


class TestHeadroom:
    """Headroom calculation tests."""

    def test_headroom_services(self):
        """Calculate remaining foreign worker headroom."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=2,
                headcount_wp=1,
            )
        )
        # DRC = 35%, local = 20, EP = 0, foreign = 3
        # max_foreign = 0.35 * 20 / 0.65 = 10.77 → 10
        # headroom = 10 - 3 = 7
        assert result.headroom_foreign == 7

    def test_headroom_with_ep(self):
        """EP workers don't count in DRC but increase total."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_ep=5,
                headcount_sp=2,
                headcount_wp=1,
            )
        )
        # max_foreign = 0.35 * (20 + 5) / 0.65 = 13.46 → 13
        # headroom = 13 - 3 = 10
        assert result.headroom_foreign == 10

    def test_approaching_ceiling_warning(self):
        """Warning when DRC utilisation > 90%."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=13,
                headcount_sp=3,
                headcount_wp=4,
            )
        )
        # 7/20 = 35% = 100% utilisation
        assert result.drc_utilisation >= 90.0
        assert any("Approaching DRC" in w for w in result.warnings)


class TestEdgeCases:
    """Edge case and validation tests."""

    def test_negative_headcount_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_quota_levy(
                QuotaLevyInput(
                    sector="services",
                    headcount_local=-1,
                )
            )

    def test_all_sectors_supported(self):
        """All five sectors produce valid results."""
        for sector in ("services", "manufacturing", "construction", "process", "marine"):
            result = calculate_quota_levy(
                QuotaLevyInput(
                    sector=sector,
                    headcount_local=10,
                    headcount_sp=1,
                    headcount_wp=1,
                )
            )
            assert result.sector == sector
            assert result.total_workforce == 12

    def test_case_insensitive_sector(self):
        """Sector should be case-insensitive."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="Services",
                headcount_local=10,
            )
        )
        assert result.drc_limit == 0.35
