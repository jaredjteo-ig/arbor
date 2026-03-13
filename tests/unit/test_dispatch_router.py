"""Unit tests for the deterministic DispatchRouter.

The DispatchRouter replaces the OrchestratorAgent by mapping QueryAnalyzer
output to specialist dispatch plans without an LLM call.

Tier 1 (Unit): Fast, isolated, no external dependencies.
"""

from __future__ import annotations

import pytest

from hr_advisory.agents.orchestration.dispatch_router import (
    DOMAIN_TO_SPECIALIST,
    DispatchPlan,
    DispatchRouter,
    _FALLBACK_DOMAIN,
    _MAX_SPECIALISTS,
)


@pytest.fixture
def router() -> DispatchRouter:
    return DispatchRouter()


# ------------------------------------------------------------------
# DispatchPlan dataclass
# ------------------------------------------------------------------


class TestDispatchPlan:
    """Verify the DispatchPlan dataclass defaults and structure."""

    def test_default_values(self):
        plan = DispatchPlan(mode="router")
        assert plan.mode == "router"
        assert plan.specialists == []
        assert plan.include_compliance_gate is False

    def test_explicit_values(self):
        plan = DispatchPlan(
            mode="parallel",
            specialists=["cpf", "tax"],
            include_compliance_gate=True,
        )
        assert plan.mode == "parallel"
        assert plan.specialists == ["cpf", "tax"]
        assert plan.include_compliance_gate is True


# ------------------------------------------------------------------
# Single-domain routing
# ------------------------------------------------------------------


class TestSingleDomainRouting:
    """When the QueryAnalyzer identifies a single domain."""

    def test_single_known_domain_returns_router_mode(self, router: DispatchRouter):
        analysis = {
            "domains": ["cpf"],
            "routing_decision": {"strategy": "router"},
            "risk_tier": "green",
        }
        plan = router.route(analysis)
        assert plan.mode == "router"
        assert plan.specialists == ["cpf"]
        assert plan.include_compliance_gate is False

    def test_each_known_domain_maps_correctly(self, router: DispatchRouter):
        """Every domain with a specialist should route to itself."""
        domains_with_agents = [
            "employment_act",
            "cpf",
            "foreign_manpower",
            "fair_employment",
            "tax",
            "wsh",
            "compliance",
            "pdpa",
        ]
        for domain in domains_with_agents:
            plan = router.route(
                {
                    "domains": [domain],
                    "routing_decision": {"strategy": "router"},
                    "risk_tier": "green",
                }
            )
            assert plan.specialists == [domain], f"Failed for domain: {domain}"
            assert plan.mode == "router"

    def test_general_domain_falls_back(self, router: DispatchRouter):
        """'general' has no dedicated specialist -- should fall back."""
        plan = router.route(
            {
                "domains": ["general"],
                "routing_decision": {"strategy": "router"},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == [_FALLBACK_DOMAIN]
        assert plan.mode == "router"


# ------------------------------------------------------------------
# Multi-domain routing
# ------------------------------------------------------------------


class TestMultiDomainRouting:
    """When the QueryAnalyzer identifies multiple domains."""

    def test_two_domains_parallel_mode(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["cpf", "tax"],
                "routing_decision": {"strategy": "parallel"},
                "risk_tier": "amber",
            }
        )
        assert plan.mode == "parallel"
        assert plan.specialists == ["cpf", "tax"]
        assert plan.include_compliance_gate is True

    def test_two_domains_sequential_mode(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["employment_act", "cpf"],
                "routing_decision": {"strategy": "sequential"},
                "risk_tier": "green",
            }
        )
        assert plan.mode == "sequential"
        assert plan.specialists == ["employment_act", "cpf"]
        assert plan.include_compliance_gate is True

    def test_multiple_domains_default_to_parallel(self, router: DispatchRouter):
        """When no strategy hint is provided, multiple domains -> parallel."""
        plan = router.route(
            {
                "domains": ["cpf", "tax"],
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        assert plan.mode == "parallel"

    def test_max_three_specialists(self, router: DispatchRouter):
        """Never dispatch more than 3 specialists, even with more domains."""
        plan = router.route(
            {
                "domains": ["cpf", "tax", "wsh", "employment_act", "fair_employment"],
                "routing_decision": {"strategy": "parallel"},
                "risk_tier": "red",
            }
        )
        assert len(plan.specialists) == _MAX_SPECIALISTS

    def test_compliance_gate_on_for_two_plus(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["cpf", "wsh"],
                "routing_decision": {"strategy": "parallel"},
                "risk_tier": "green",
            }
        )
        assert plan.include_compliance_gate is True

    def test_compliance_gate_off_for_single(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["cpf"],
                "routing_decision": {"strategy": "router"},
                "risk_tier": "green",
            }
        )
        assert plan.include_compliance_gate is False


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    """Defensive handling of malformed or missing data."""

    def test_empty_domains_fallback(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": [],
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == [_FALLBACK_DOMAIN]
        assert plan.mode == "router"

    def test_missing_domains_key(self, router: DispatchRouter):
        plan = router.route(
            {
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == [_FALLBACK_DOMAIN]
        assert plan.mode == "router"

    def test_none_domains(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": None,
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == [_FALLBACK_DOMAIN]

    def test_unknown_domain_skipped(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["unknown_domain", "cpf"],
                "routing_decision": {"strategy": "router"},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == ["cpf"]
        assert plan.mode == "router"

    def test_all_unknown_domains_fallback(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["unknown_a", "unknown_b"],
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == [_FALLBACK_DOMAIN]

    def test_duplicate_domains_deduplicated(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["cpf", "cpf", "cpf"],
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == ["cpf"]
        assert plan.mode == "router"

    def test_missing_routing_decision(self, router: DispatchRouter):
        """Missing routing_decision should not crash."""
        plan = router.route(
            {
                "domains": ["tax"],
                "risk_tier": "green",
            }
        )
        assert plan.specialists == ["tax"]
        assert plan.mode == "router"

    def test_empty_analysis(self, router: DispatchRouter):
        """Completely empty dict should produce a safe fallback."""
        plan = router.route({})
        assert plan.specialists == [_FALLBACK_DOMAIN]
        assert plan.mode == "router"

    def test_general_plus_known_domain(self, router: DispatchRouter):
        """'general' should collapse into fallback; if the known domain
        IS the fallback, no duplicates."""
        plan = router.route(
            {
                "domains": ["general", "employment_act"],
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        # "general" maps to employment_act, and employment_act is already
        # in the list, so deduplication should give us a single entry.
        assert plan.specialists == ["employment_act"]
        assert plan.mode == "router"

    def test_general_plus_different_domain(self, router: DispatchRouter):
        """'general' collapses into fallback; different domain is kept."""
        plan = router.route(
            {
                "domains": ["general", "cpf"],
                "routing_decision": {},
                "risk_tier": "green",
            }
        )
        assert plan.specialists == ["employment_act", "cpf"]
        assert plan.mode == "parallel"


# ------------------------------------------------------------------
# Strategy hint logic
# ------------------------------------------------------------------


class TestStrategyHints:
    """Verify how the QueryAnalyzer's strategy hint is honoured."""

    def test_router_hint_overridden_for_multiple(self, router: DispatchRouter):
        """'router' strategy with multiple specialists should become 'parallel'."""
        plan = router.route(
            {
                "domains": ["cpf", "tax"],
                "routing_decision": {"strategy": "router"},
                "risk_tier": "green",
            }
        )
        assert plan.mode == "parallel"

    def test_sequential_hint_honoured(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["employment_act", "compliance"],
                "routing_decision": {"strategy": "sequential"},
                "risk_tier": "amber",
            }
        )
        assert plan.mode == "sequential"

    def test_invalid_strategy_defaults_to_parallel(self, router: DispatchRouter):
        plan = router.route(
            {
                "domains": ["cpf", "tax"],
                "routing_decision": {"strategy": "invalid_mode"},
                "risk_tier": "green",
            }
        )
        assert plan.mode == "parallel"

    def test_single_domain_always_router_regardless_of_hint(self, router: DispatchRouter):
        """Single domain -> 'router' mode, even if hint says parallel."""
        plan = router.route(
            {
                "domains": ["cpf"],
                "routing_decision": {"strategy": "parallel"},
                "risk_tier": "green",
            }
        )
        assert plan.mode == "router"


# ------------------------------------------------------------------
# Domain mapping coverage
# ------------------------------------------------------------------


class TestDomainMapping:
    """Verify the DOMAIN_TO_SPECIALIST mapping is complete."""

    def test_all_expected_domains_present(self):
        expected = {
            "employment_act",
            "cpf",
            "foreign_manpower",
            "fair_employment",
            "tax",
            "wsh",
            "compliance",
            "pdpa",
            "general",
        }
        assert set(DOMAIN_TO_SPECIALIST.keys()) == expected

    def test_pdpa_mapped_to_agent(self):
        assert DOMAIN_TO_SPECIALIST["pdpa"] == "PDPAAgent"

    def test_general_maps_to_none(self):
        assert DOMAIN_TO_SPECIALIST["general"] is None

    def test_fallback_domain_is_employment_act(self):
        assert _FALLBACK_DOMAIN == "employment_act"

    def test_max_specialists_is_three(self):
        assert _MAX_SPECIALISTS == 3
