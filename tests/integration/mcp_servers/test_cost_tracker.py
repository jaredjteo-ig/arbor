"""Integration tests for the per-tenant API cost tracker.

Tests:
- Record cost -> monthly total correct
- Multiple providers -> breakdown correct
- Cost ceiling warning at 80%
- Cost ceiling exceeded at 100%
- Different months tracked separately
- Known provider costs auto-applied
- Recent entries retrieval
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.cost_tracker import (
    PROVIDER_COSTS,
    CostTracker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tracker() -> CostTracker:
    return CostTracker()


TENANT = "company_100"


# ---------------------------------------------------------------------------
# Record and Monthly Total
# ---------------------------------------------------------------------------


class TestRecordCost:
    """Record costs and verify monthly totals."""

    def test_single_cost_recorded(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "fetch_person_data", cost_cents=100)
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_cents"] == 100

    def test_total_sgd_matches_cents(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "fetch_person_data", cost_cents=550)
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_sgd"] == 5.50

    def test_multiple_costs_accumulate(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "fetch1", cost_cents=100)
        tracker.record_cost(TENANT, "myinfo", "fetch2", cost_cents=100)
        tracker.record_cost(TENANT, "myinfo", "fetch3", cost_cents=100)
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_cents"] == 300

    def test_zero_cost_not_recorded(self, tracker):
        tracker.record_cost(TENANT, "free_api", "call", cost_cents=0)
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_cents"] == 0

    def test_known_provider_cost_auto_applied(self, tracker):
        """When cost_cents is not provided, use the known per-call cost."""
        tracker.record_cost(TENANT, "myinfo", "auto_cost")
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_cents"] == PROVIDER_COSTS["myinfo"]  # 100 cents

    def test_acra_known_cost(self, tracker):
        tracker.record_cost(TENANT, "acra", "verify_uen")
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_cents"] == PROVIDER_COSTS["acra"]  # 550 cents

    def test_unknown_provider_no_cost_applied(self, tracker):
        """Unknown providers with no explicit cost_cents default to 0 (no recording)."""
        tracker.record_cost(TENANT, "unknown_api", "call")
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_cents"] == 0


# ---------------------------------------------------------------------------
# Provider Breakdown
# ---------------------------------------------------------------------------


class TestProviderBreakdown:
    """Cost breakdown by provider."""

    def test_breakdown_by_provider(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call1", cost_cents=100)
        tracker.record_cost(TENANT, "acra", "call1", cost_cents=550)
        tracker.record_cost(TENANT, "myinfo", "call2", cost_cents=100)

        monthly = tracker.get_monthly_cost(TENANT)
        costs = monthly["costs_by_provider"]

        assert costs["myinfo"] == 200
        assert costs["acra"] == 550

    def test_total_is_sum_of_providers(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=100)
        tracker.record_cost(TENANT, "acra", "call", cost_cents=550)
        tracker.record_cost(TENANT, "whatsapp", "msg", cost_cents=1)

        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["total_cents"] == 651

    def test_tenant_id_in_response(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=100)
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["tenant_id"] == TENANT

    def test_currency_in_response(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=100)
        monthly = tracker.get_monthly_cost(TENANT)
        assert monthly["currency"] == "SGD"


# ---------------------------------------------------------------------------
# Cost Ceiling
# ---------------------------------------------------------------------------


class TestCostCeiling:
    """Cost ceiling warnings and exceeded thresholds."""

    def test_status_ok_under_80_percent(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=3000)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["status"] == "ok"
        assert result["usage_percent"] == 60.0

    def test_warning_at_80_percent(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=4000)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["status"] == "warning"
        assert result["usage_percent"] == 80.0

    def test_warning_between_80_and_100(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=4500)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["status"] == "warning"
        assert result["usage_percent"] == 90.0

    def test_exceeded_at_100_percent(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=5000)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["status"] == "exceeded"
        assert result["usage_percent"] == 100.0

    def test_exceeded_over_100_percent(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=6000)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["status"] == "exceeded"
        assert result["usage_percent"] == 120.0

    def test_remaining_cents_correct(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=3000)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["remaining_cents"] == 2000

    def test_remaining_cents_zero_when_exceeded(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=6000)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["remaining_cents"] == 0

    def test_ceiling_response_fields(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call", cost_cents=1000)
        result = tracker.check_cost_ceiling(TENANT, ceiling_cents=5000)
        assert result["tenant_id"] == TENANT
        assert result["total_cents"] == 1000
        assert result["ceiling_cents"] == 5000


# ---------------------------------------------------------------------------
# Monthly Isolation
# ---------------------------------------------------------------------------


class TestMonthlyIsolation:
    """Different months tracked separately."""

    def test_different_months_separated(self, tracker):
        # Record in a specific month by checking the current month
        tracker.record_cost(TENANT, "myinfo", "call1", cost_cents=100)

        # Get current month total
        current_monthly = tracker.get_monthly_cost(TENANT)
        assert current_monthly["total_cents"] == 100

        # A different month should be empty
        past_monthly = tracker.get_monthly_cost(TENANT, year_month="2020-01")
        assert past_monthly["total_cents"] == 0

    def test_empty_month_returns_zero_total(self, tracker):
        monthly = tracker.get_monthly_cost(TENANT, year_month="2020-06")
        assert monthly["total_cents"] == 0
        assert monthly["total_sgd"] == 0.0
        assert monthly["costs_by_provider"] == {}

    def test_period_in_response(self, tracker):
        monthly = tracker.get_monthly_cost(TENANT, year_month="2026-03")
        assert monthly["period"] == "2026-03"


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    """Costs are isolated between tenants."""

    def test_different_tenants_tracked_separately(self, tracker):
        tracker.record_cost("company_100", "myinfo", "call", cost_cents=100)
        tracker.record_cost("company_200", "acra", "call", cost_cents=550)

        monthly_100 = tracker.get_monthly_cost("company_100")
        monthly_200 = tracker.get_monthly_cost("company_200")

        assert monthly_100["total_cents"] == 100
        assert monthly_200["total_cents"] == 550

    def test_ceiling_check_per_tenant(self, tracker):
        tracker.record_cost("company_100", "myinfo", "call", cost_cents=4500)
        tracker.record_cost("company_200", "myinfo", "call", cost_cents=1000)

        result_100 = tracker.check_cost_ceiling("company_100", ceiling_cents=5000)
        result_200 = tracker.check_cost_ceiling("company_200", ceiling_cents=5000)

        assert result_100["status"] == "warning"
        assert result_200["status"] == "ok"


# ---------------------------------------------------------------------------
# Recent Entries
# ---------------------------------------------------------------------------


class TestRecentEntries:
    """Recent cost entry retrieval."""

    def test_recent_entries_returned(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "call1", cost_cents=100)
        tracker.record_cost(TENANT, "acra", "call2", cost_cents=550)

        entries = tracker.get_recent_entries(TENANT)
        assert len(entries) == 2

    def test_entry_structure(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "fetch_person", cost_cents=100)

        entries = tracker.get_recent_entries(TENANT)
        entry = entries[0]
        assert entry["provider"] == "myinfo"
        assert entry["endpoint"] == "fetch_person"
        assert entry["cost_cents"] == 100
        assert entry["currency"] == "SGD"
        assert "timestamp" in entry

    def test_limit_applied(self, tracker):
        for i in range(10):
            tracker.record_cost(TENANT, "myinfo", f"call{i}", cost_cents=100)

        entries = tracker.get_recent_entries(TENANT, limit=5)
        assert len(entries) == 5

    def test_newest_first(self, tracker):
        tracker.record_cost(TENANT, "myinfo", "first", cost_cents=100)
        tracker.record_cost(TENANT, "acra", "second", cost_cents=550)

        entries = tracker.get_recent_entries(TENANT)
        assert entries[0]["timestamp"] >= entries[1]["timestamp"]

    def test_filtered_by_tenant(self, tracker):
        tracker.record_cost("company_100", "myinfo", "call", cost_cents=100)
        tracker.record_cost("company_200", "acra", "call", cost_cents=550)

        entries_100 = tracker.get_recent_entries("company_100")
        entries_200 = tracker.get_recent_entries("company_200")

        assert len(entries_100) == 1
        assert len(entries_200) == 1
        assert entries_100[0]["provider"] == "myinfo"
        assert entries_200[0]["provider"] == "acra"


# ---------------------------------------------------------------------------
# Known Provider Costs
# ---------------------------------------------------------------------------


class TestKnownProviderCosts:
    """Verify PROVIDER_COSTS constants."""

    def test_myinfo_cost(self):
        assert PROVIDER_COSTS["myinfo"] == 100  # $1.00

    def test_acra_cost(self):
        assert PROVIDER_COSTS["acra"] == 550  # $5.50

    def test_whatsapp_cost(self):
        assert PROVIDER_COSTS["whatsapp"] == 1  # ~$0.01

    def test_sms_cost(self):
        assert PROVIDER_COSTS["sms"] == 5  # ~$0.05
