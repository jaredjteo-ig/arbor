"""OrchestratorAgent -- plans specialist dispatch.

Receives the output of QueryAnalyzerAgent and produces a dispatch plan:
which specialist agents to call, in what order, and whether to run them
in parallel, sequentially, or via a single router.

Uses a supervisor-worker pattern: the orchestrator decides, specialists execute.
"""

import dataclasses
import json
import logging
from typing import Any, Dict, List, Optional

try:
    from kaizen import BaseAgent
except ImportError:
    from kaizen import CoreAgent as BaseAgent

from hr_advisory.agents.config import OrchestratorConfig
from hr_advisory.agents.signatures import OrchestratorSignature
from hr_advisory.agents.specialists._base import _KaizenCompatMixin

logger = logging.getLogger(__name__)

# Map from domain keys to specialist identifiers
DOMAIN_TO_SPECIALIST = {
    "employment_act": "employment_act_specialist",
    "cpf": "cpf_specialist",
    "foreign_manpower": "foreign_manpower_specialist",
    "fair_employment": "fair_employment_specialist",
    "tax": "tax_specialist",
    "wsh": "wsh_specialist",
    "pdpa": "pdpa_specialist",
    "compliance": "compliance_specialist",
    "general": "general_hr_specialist",
}


class OrchestratorAgent(_KaizenCompatMixin, BaseAgent):
    """Plan which specialist agents to engage and in what order.

    Extension points used:
      - _default_signature()      -> OrchestratorSignature
      - _generate_system_prompt() -> dispatch-planning prompt
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        shared_memory: Any = None,
        **kwargs,
    ):
        config = config or OrchestratorConfig()
        super().__init__(
            agent_id="orchestrator",
            config=dataclasses.asdict(config),
            signature=OrchestratorSignature(),
        )
        self.shared_memory = shared_memory

    # ------------------------------------------------------------------
    # Extension points
    # ------------------------------------------------------------------

    def _default_signature(self):
        return OrchestratorSignature()

    def _generate_system_prompt(self) -> str:
        specialist_list = "\n".join(f"  - {k}: {v}" for k, v in DOMAIN_TO_SPECIALIST.items())
        return (
            "You are the dispatch planner for a multi-agent HR advisory system.\n\n"
            "AVAILABLE SPECIALISTS:\n"
            f"{specialist_list}\n\n"
            "RULES:\n"
            "1. At most 3 specialists per query\n"
            "2. Always include the primary domain specialist\n"
            "3. Use 'parallel' when specialists are independent\n"
            "4. Use 'sequential' when one specialist's output feeds another\n"
            "5. Use 'router' when only one specialist is needed\n\n"
            "OUTPUT: Respond with a JSON object:\n"
            '  "dispatch_plan": {\n'
            '    "mode": "parallel" | "sequential" | "router",\n'
            '    "specialists": [\n'
            '      {"domain": "...", "priority": 1, "reason": "..."}\n'
            "    ],\n"
            '    "estimated_tokens": <integer>\n'
            "  }\n\n"
            "Respond ONLY with valid JSON."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a dispatch plan from the query analysis.

        Args:
            analysis_result: Output from QueryAnalyzerAgent.analyze().

        Returns:
            Dict with key "dispatch_plan" containing mode, specialists,
            and estimated_tokens.
        """
        analysis_json = json.dumps(analysis_result)
        result = self.run(analysis_result=analysis_json)

        dispatch_plan = self.extract_dict(
            result,
            "dispatch_plan",
            default=self._fallback_plan(analysis_result),
        )

        # Validate that specialists map to known domains
        specialists = dispatch_plan.get("specialists", [])
        validated = []
        for spec in specialists:
            domain = spec.get("domain", "general")
            if domain in DOMAIN_TO_SPECIALIST:
                validated.append(spec)
        if not validated:
            validated = [
                {
                    "domain": analysis_result.get("domains", ["general"])[0],
                    "priority": 1,
                    "reason": "primary domain",
                }
            ]
        dispatch_plan["specialists"] = validated

        # Validate mode
        if dispatch_plan.get("mode") not in ("parallel", "sequential", "router"):
            dispatch_plan["mode"] = "router" if len(validated) == 1 else "parallel"

        # Write plan to shared memory
        self.write_to_memory(
            content={"dispatch_plan": dispatch_plan},
            tags=["dispatch_plan"],
            importance=0.8,
            segment="orchestration",
        )

        return {"dispatch_plan": dispatch_plan}

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_plan(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a safe fallback plan from analysis domains."""
        domains = analysis_result.get("domains", ["general"])
        specialists = [
            {"domain": d, "priority": i + 1, "reason": "from analysis"}
            for i, d in enumerate(domains[:3])
        ]
        mode = "router" if len(specialists) == 1 else "parallel"
        return {
            "mode": mode,
            "specialists": specialists,
            "estimated_tokens": 500 * len(specialists),
        }
