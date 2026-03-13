"""Deterministic specialist dispatch based on QueryAnalyzer output.

Replaces the OrchestratorAgent which added an unnecessary LLM round-trip.
The QueryAnalyzer already produces structured routing decisions; this class
executes them without LLM involvement.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Map from domain keys to specialist agent class names.
# These mirror the specialist agents registered in hr_advisory.agents.specialists.
DOMAIN_TO_SPECIALIST: Dict[str, str | None] = {
    "employment_act": "EmploymentActAgent",
    "cpf": "CPFAgent",
    "foreign_manpower": "ForeignManpowerAgent",
    "fair_employment": "FairEmploymentAgent",
    "tax": "TaxAgent",
    "wsh": "WSHAgent",
    "compliance": "ComplianceAgent",
    "pdpa": "PDPAAgent",
    "general": None,  # No dedicated agent; falls back to employment_act
}

# Default fallback domain when no specialist is available.
_FALLBACK_DOMAIN = "employment_act"

# Maximum number of specialists dispatched per query.
_MAX_SPECIALISTS = 3


@dataclass
class DispatchPlan:
    """Immutable dispatch plan produced by the router.

    Attributes:
        mode: Execution strategy -- "router" (single specialist),
              "parallel" (independent specialists), or "sequential"
              (one specialist's output feeds the next).
        specialists: Ordered list of domain names to dispatch to.
              Maximum length is 3.
        include_compliance_gate: Whether to run ComplianceAgent after
              the specialists complete.  True when 2+ specialists are
              dispatched, since cross-domain interactions raise
              compliance risk.
    """

    mode: str  # "router", "parallel", "sequential"
    specialists: List[str] = field(default_factory=list)
    include_compliance_gate: bool = False


class DispatchRouter:
    """Deterministic specialist dispatch router.

    Pure Python -- no LLM call, no Kaizen BaseAgent, no signatures.
    Accepts the structured output of QueryAnalyzerAgent.analyze() and
    returns a DispatchPlan describing which specialists to call and how.

    Usage::

        router = DispatchRouter()
        plan = router.route(analysis_result)
        # plan.mode -> "router" | "parallel" | "sequential"
        # plan.specialists -> ["employment_act", "cpf"]
    """

    def __init__(self) -> None:
        self._domain_map = dict(DOMAIN_TO_SPECIALIST)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, analysis_result: Dict[str, Any]) -> DispatchPlan:
        """Produce a dispatch plan from the query analysis.

        Args:
            analysis_result: Output dict from QueryAnalyzerAgent.analyze().
                Expected keys:
                    - domains: list[str]
                    - routing_decision: dict with "strategy" key
                    - risk_tier: str ("green", "amber", "red")

        Returns:
            A DispatchPlan with mode, specialists, and compliance gate flag.
        """
        domains = analysis_result.get("domains") or []
        routing_decision = analysis_result.get("routing_decision") or {}
        strategy = routing_decision.get("strategy", "")

        # Resolve domains to known specialists, filtering unknowns and
        # replacing domains that have no agent with the fallback.
        resolved = self._resolve_domains(domains)

        if not resolved:
            resolved = [_FALLBACK_DOMAIN]
            logger.debug(
                "No valid domains in analysis; falling back to %s",
                _FALLBACK_DOMAIN,
            )

        # Enforce the cap
        resolved = resolved[:_MAX_SPECIALISTS]

        # Determine mode
        mode = self._determine_mode(resolved, strategy)

        # Compliance gate triggers when multiple specialists are involved
        include_compliance_gate = len(resolved) >= 2

        plan = DispatchPlan(
            mode=mode,
            specialists=resolved,
            include_compliance_gate=include_compliance_gate,
        )

        logger.info(
            "DispatchRouter: mode=%s specialists=%s compliance_gate=%s",
            plan.mode,
            plan.specialists,
            plan.include_compliance_gate,
        )

        return plan

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_domains(self, domains: List[str]) -> List[str]:
        """Map raw domain names to dispatchable domain keys.

        - Known domains with a specialist agent are kept as-is.
        - The "general" domain (no specialist) is replaced with the
          fallback domain.
        - Unknown domains are dropped with a warning.
        - Duplicates are removed while preserving order.
        """
        seen: set[str] = set()
        resolved: List[str] = []

        for domain in domains:
            if domain in seen:
                continue

            if domain not in self._domain_map:
                logger.warning("Unknown domain '%s' -- skipping", domain)
                continue

            specialist = self._domain_map[domain]
            if specialist is None:
                # "general" or any domain with no agent -> fallback
                target = _FALLBACK_DOMAIN
            else:
                target = domain

            if target not in seen:
                seen.add(target)
                resolved.append(target)

        return resolved

    def _determine_mode(self, specialists: List[str], strategy_hint: str) -> str:
        """Pick the execution mode.

        Rules:
        1. If the QueryAnalyzer explicitly requested a valid strategy,
           honour it (as long as it makes sense for the specialist count).
        2. Single specialist -> always "router".
        3. Multiple specialists -> "parallel" by default, unless the
           strategy hint says "sequential".
        """
        valid_modes = {"router", "parallel", "sequential"}

        if len(specialists) == 1:
            return "router"

        # Multiple specialists
        if strategy_hint in valid_modes:
            # "router" doesn't make sense for multiple specialists
            if strategy_hint == "router":
                return "parallel"
            return strategy_hint

        return "parallel"
