"""ComplianceAgent -- Cross-domain compliance checker.

Unlike other specialists, the ComplianceAgent does NOT advise on a
single domain.  Instead it:

  1. Reads all specialist outputs from SharedMemoryPool
  2. Identifies cross-domain compliance issues or contradictions
  3. Flags gaps where no specialist addressed a relevant aspect
  4. CANNOT make legal determinations -- only flags issues

This agent runs AFTER the domain specialists, as a quality gate.
"""

import dataclasses
import json
import logging
from typing import Any, Dict, List, Optional

from kaizen import CoreAgent as BaseAgent

from hr_advisory.agents.config import ComplianceConfig, UNCERTAINTY_DEFAULTS
from hr_advisory.agents.specialists._base import _KaizenCompatMixin
from hr_advisory.agents.specialists.signatures import ComplianceSignature

logger = logging.getLogger(__name__)

VALID_RISK_TIERS = frozenset(["green", "amber", "red"])


class ComplianceAgent(_KaizenCompatMixin, BaseAgent):
    """Cross-domain compliance checker.

    Extension points used:
      - _default_signature()      -> ComplianceSignature
      - _generate_system_prompt() -> cross-domain analysis prompt
    """

    domain = "compliance"
    domain_label = "Compliance"

    def __init__(
        self,
        config: Optional[ComplianceConfig] = None,
        shared_memory: Any = None,
        **kwargs,
    ):
        config = config or ComplianceConfig()
        super().__init__(
            agent_id="compliance_specialist",
            config=dataclasses.asdict(config),
            signature=ComplianceSignature(),
        )
        self.shared_memory = shared_memory

    def _default_signature(self):
        return ComplianceSignature()

    def _generate_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return self._domain_system_prompt()

    def _domain_system_prompt(self) -> str:
        return (
            "You are a cross-domain compliance reviewer for Singapore HR regulations.\n\n"
            "ROLE: You do NOT advise on any single domain. Instead, you review "
            "outputs from multiple specialist agents and identify:\n"
            "  1. Cross-domain compliance issues (e.g. EA and CPF interaction)\n"
            "  2. Contradictions between specialist outputs\n"
            "  3. Gaps where no specialist addressed a relevant aspect\n"
            "  4. Escalation triggers requiring professional legal review\n\n"
            "CONSTRAINT: You CANNOT make legal determinations. You can only flag "
            "issues for human review.\n\n"
            "OUTPUT: Respond with a JSON object containing:\n"
            '  "compliance_flags": [\n'
            '    {"issue": "...", "domains": ["domain1", "domain2"], "severity": "low|medium|high"}\n'
            "  ],\n"
            '  "gaps_identified": ["description of gap 1", ...],\n'
            '  "risk_tier": "green|amber|red",\n'
            '  "recommendations": ["recommended action 1", ...]\n\n'
            "Respond ONLY with valid JSON."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_compliance(
        self,
        query_text: str,
        specialist_outputs: List[Dict[str, Any]],
        company_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Review specialist outputs for cross-domain compliance issues.

        Args:
            query_text: The original HR query.
            specialist_outputs: List of specialist output dicts from SharedMemoryPool.
            company_context: Optional company profile dict.

        Returns:
            Dict with keys: compliance_flags, gaps_identified, risk_tier,
            recommendations, risk_escalation (bool), override_risk_tier.
            May include degraded=True on errors.
        """
        degraded = False

        # Determine the highest specialist risk tier to detect escalation
        _severity = {"green": 0, "amber": 1, "red": 2}
        max_specialist_tier = "green"
        for output in specialist_outputs:
            output_tier = output.get("risk_tier", "green")
            if _severity.get(output_tier, 0) > _severity.get(max_specialist_tier, 0):
                max_specialist_tier = output_tier

        try:
            ctx_str = json.dumps(company_context) if company_context else "{}"
            outputs_str = json.dumps(specialist_outputs)

            result = self.run(
                query_text=query_text,
                specialist_outputs=outputs_str,
                company_context=ctx_str,
            )

            compliance_flags = self.extract_list(result, "compliance_flags", default=[])
            gaps_identified = self.extract_list(result, "gaps_identified", default=[])
            risk_tier = self.extract_str(
                result, "risk_tier", default=UNCERTAINTY_DEFAULTS["risk_tier"]
            )
            recommendations = self.extract_list(result, "recommendations", default=[])

            # Validate risk tier — escalate on invalid, never suppress
            if risk_tier not in VALID_RISK_TIERS:
                logger.warning(
                    "ComplianceAgent returned invalid risk_tier '%s', escalating to amber",
                    risk_tier,
                )
                risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]
                degraded = True

        except Exception as exc:
            logger.error(
                "ComplianceAgent check failed for query: %.100s — %s",
                query_text,
                exc,
                exc_info=True,
            )
            degraded = True
            compliance_flags = []
            gaps_identified = [
                "Compliance review was unable to complete — manual review recommended."
            ]
            risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]
            recommendations = ["Professional compliance review recommended due to system error."]

        # Determine whether compliance review escalated the risk tier
        # beyond what any individual specialist flagged.
        risk_escalation = _severity.get(risk_tier, 0) > _severity.get(
            max_specialist_tier, 0
        ) or bool(compliance_flags)

        review: Dict[str, Any] = {
            "domain": "compliance",
            "compliance_flags": compliance_flags,
            "gaps_identified": gaps_identified,
            "risk_tier": risk_tier,
            "recommendations": recommendations,
            "risk_escalation": risk_escalation,
            "override_risk_tier": risk_tier,
        }

        if degraded:
            review["degraded"] = True

        self.write_to_memory(
            content=review,
            tags=["compliance", "cross_domain"],
            importance=0.85,
            segment="compliance_review",
        )

        return review
