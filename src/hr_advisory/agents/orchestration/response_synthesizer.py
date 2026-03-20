"""ResponseSynthesizerAgent -- synthesizes final advisory response.

Reads all specialist outputs from SharedMemoryPool, then produces
a plain-language answer with citations and risk-tier disclaimers
suitable for Singapore SME owners and managers.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from kaizen.core.base_agent import BaseAgent
from kaizen.memory import SharedMemoryPool

from hr_advisory.agents.config import ResponseSynthesizerConfig, UNCERTAINTY_DEFAULTS
from hr_advisory.agents.signatures import ResponseSynthesizerSignature
from hr_advisory.workflows.guardrails import SYSTEM_PROMPT_SECURITY_FOOTER

logger = logging.getLogger(__name__)

RISK_DISCLAIMERS = {
    "green": [],
    "amber": [
        "This topic involves nuances that may vary by circumstances. "
        "We recommend professional review before acting on this advice."
    ],
    "red": [
        "This topic carries significant legal or financial risk. "
        "Mandatory professional review is required before taking any action."
    ],
}

_RISK_TIER_SEVERITY = {"green": 0, "amber": 1, "red": 2}


class ResponseSynthesizerAgent(BaseAgent):
    """Synthesize specialist outputs into a plain-language advisory.

    Extension points used:
      - _default_signature()      -> ResponseSynthesizerSignature
      - _generate_system_prompt() -> synthesis prompt with citation rules
    """

    def __init__(
        self,
        config: Optional[ResponseSynthesizerConfig] = None,
        shared_memory: Optional[SharedMemoryPool] = None,
        **kwargs,
    ):
        config = config or ResponseSynthesizerConfig()
        super().__init__(
            config=config,
            signature=ResponseSynthesizerSignature(),
            shared_memory=shared_memory,
            agent_id="response_synthesizer",
            mcp_servers=[],
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Extension points
    # ------------------------------------------------------------------

    def _default_signature(self):
        return ResponseSynthesizerSignature()

    def _generate_system_prompt(self) -> str:
        return (
            "You are a plain-language HR advisory writer for Singapore SMEs.\n\n"
            "TASK: Combine the specialist outputs into a single, clear, actionable "
            "response. You are the last step before the user sees the answer -- your "
            "job is to make complex regulatory guidance accessible and useful.\n\n"
            "== MANDATORY RESPONSE TEMPLATE ==\n"
            "Every response_text MUST follow this structure in order:\n\n"
            "1. **Summary** (1-2 sentences): The direct answer to the user's question. "
            "Lead with the bottom line -- do not bury the answer.\n\n"
            "2. **What the law says**: Specific provisions that apply to this situation. "
            "Cite inline as [Act s.X] (e.g. [Employment Act s.38], [CPF Act s.7]). "
            "Group by domain if multiple acts are involved.\n\n"
            "3. **What you need to do**: Numbered action steps the user can take today. "
            "Be concrete -- include deadlines, amounts, and who is responsible where "
            "possible.\n\n"
            "4. **Watch out for**: Risks, deadlines, escalation triggers, and penalties. "
            "OMIT this section entirely if there are no material risks or caveats to "
            "flag -- do not include it with filler content.\n\n"
            "5. **Disclaimer**: A risk-tier appropriate disclaimer. For GREEN tier, a "
            "brief general disclaimer is sufficient. For AMBER, recommend professional "
            "review. For RED, state that professional legal advice is required before "
            "acting.\n\n"
            "== TONE RULES ==\n"
            "- Plain English; no legalese unless quoting a provision directly.\n"
            "- Singapore English is acceptable (but not required).\n"
            "- No condescension; treat the reader as a capable SME owner who simply "
            "is not a legal specialist.\n"
            "- Use 'you' language: 'You need to...' not 'The employer should...'\n"
            "- Be direct: 'Do this' not 'It would be advisable to consider...'\n"
            "- Users may write in Singlish (Singapore colloquial English). Always "
            "understand Singlish input but respond in clear standard English.\n\n"
            "== LENGTH GUIDANCE BY RISK TIER ==\n"
            "- GREEN: 200-350 words. Concise and action-focused. Get to the point.\n"
            "- AMBER: 350-500 words. More detail, nuance, and caveats where needed.\n"
            "- RED: 500-700 words. Thorough analysis with an explicit 'consult a "
            "lawyer' call-to-action. Do not cut corners on high-risk advice.\n\n"
            "== CONFLICT RESOLUTION ==\n"
            "If compliance_results contains contradictions between specialist outputs:\n"
            "- Name the contradiction explicitly: 'There is a potential conflict "
            "between [domain A] and [domain B] regarding [topic].'\n"
            "- State which provision takes precedence, if determinable (e.g. a "
            "specific act overrides a general guideline).\n"
            "- If precedence is NOT determinable, explicitly recommend seeking "
            "professional advice on the specific conflict.\n"
            "- NEVER silently choose one side -- always surface the conflict to the "
            "user so they can make an informed decision.\n\n"
            "== PARTIAL CONFIDENCE HANDLING ==\n"
            "If any specialist output has confidence < 0.4:\n"
            "- Prefix the relevant section with 'Based on limited information'.\n"
            "- Use hedging language: 'you may need to' instead of 'you must'.\n"
            "- Do NOT use definitive language for low-confidence advice.\n"
            "- If ALL specialist outputs have confidence < 0.4, begin the Summary "
            "with 'We have limited information on this topic' and escalate the "
            "disclaimer accordingly.\n\n"
            "== CITATION RULES ==\n"
            "- Inline citations: [Employment Act s.38], [CPF Act s.7], [PDPA s.13]\n"
            "- ONLY cite provisions that appear in the specialist outputs -- never "
            "fabricate section numbers or legislative references.\n"
            "- Collect all cited provisions into a 'Sources' list at the end of "
            "response_text, formatted as a bulleted list.\n"
            "- If a specialist cited a provision, you MUST include it in your "
            "citations array even if you paraphrased the content.\n\n"
            "== COMMON MISTAKES TO AVOID ==\n"
            "- Do not merge advice from different domains without attribution. If "
            "Employment Act and PDPA both apply, keep the guidance clearly separated "
            "by domain.\n"
            "- Do not downplay RED-tier risks. If any specialist flagged red, your "
            "response must reflect that severity.\n"
            "- Do not add action steps that are not grounded in a specialist output. "
            "You synthesize -- you do not originate legal advice.\n"
            "- Do not use generic filler ('It is important to note that...', "
            "'As always...'). Every sentence should carry information.\n"
            "- Do not omit the Disclaimer section regardless of risk tier.\n\n"
            "OUTPUT: Respond with a JSON object:\n"
            '  "response_text": "the full advisory following the template above",\n'
            '  "citations": [{"provision": "...", "section": "...", "act": "..."}],\n'
            '  "disclaimers": ["..."],\n'
            '  "final_risk_tier": "green" | "amber" | "red"\n\n'
            "Respond ONLY with valid JSON."
        ) + SYSTEM_PROMPT_SECURITY_FOOTER

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(
        self,
        specialist_outputs: List[Dict[str, Any]],
        risk_tier: str = "green",
        company_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[str] = None,
        compliance_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synthesize specialist outputs into a final advisory response.

        Args:
            specialist_outputs: List of specialist output dicts
                (from SharedMemoryPool or passed directly).
            risk_tier: Initial risk tier from QueryAnalyzer.
            company_context: Optional company profile dict for
                personalisation of the synthesized response.
            conversation_history: Optional formatted string of previous
                conversation turns for multi-turn context.
            compliance_results: Optional compliance gate output dict
                with contradictions, risk_escalation, and
                override_risk_tier for the synthesizer to address.

        Returns:
            Dict with keys: response_text, citations, disclaimers,
            final_risk_tier. May include degraded=True when synthesis
            encountered errors or all specialists failed.
        """
        degraded = False

        # Determine the highest risk tier from specialist outputs — this
        # is the floor.  The synthesizer must never produce a final tier
        # BELOW what any specialist flagged.
        floor_risk_tier = risk_tier
        all_degraded = True
        for output in specialist_outputs:
            output_tier = output.get("risk_tier", "green")
            if _RISK_TIER_SEVERITY.get(output_tier, 0) > _RISK_TIER_SEVERITY.get(
                floor_risk_tier, 0
            ):
                floor_risk_tier = output_tier
            if not output.get("degraded", False):
                all_degraded = False

        # If ALL specialist outputs are degraded, escalate to red
        if all_degraded and specialist_outputs:
            logger.warning(
                "All %d specialist outputs are degraded — escalating to red",
                len(specialist_outputs),
            )
            floor_risk_tier = "red"
            degraded = True

        try:
            outputs_json = json.dumps(specialist_outputs)
            ctx_str = json.dumps(company_context) if company_context else "{}"
            history_str = conversation_history if conversation_history else ""
            compliance_str = json.dumps(compliance_results) if compliance_results else "{}"

            result = self.run(
                specialist_outputs=outputs_json,
                risk_tier=floor_risk_tier,
                company_context=ctx_str,
                conversation_history=history_str,
                compliance_results=compliance_str,
            )

            response_text = self.extract_str(result, "response_text", default="")
            citations = self.extract_list(result, "citations", default=[])
            disclaimers = self.extract_list(result, "disclaimers", default=[])
            final_risk_tier = self.extract_str(result, "final_risk_tier", default=floor_risk_tier)

            # Validate risk tier
            if final_risk_tier not in ("green", "amber", "red"):
                logger.warning(
                    "ResponseSynthesizer returned invalid risk_tier '%s', " "using floor tier '%s'",
                    final_risk_tier,
                    floor_risk_tier,
                )
                final_risk_tier = floor_risk_tier

            # Enforce monotonic escalation: final tier can never be below the
            # highest specialist tier
            if _RISK_TIER_SEVERITY.get(final_risk_tier, 0) < _RISK_TIER_SEVERITY.get(
                floor_risk_tier, 0
            ):
                logger.warning(
                    "ResponseSynthesizer tried to downgrade risk from '%s' to '%s' "
                    "— preserving higher tier",
                    floor_risk_tier,
                    final_risk_tier,
                )
                final_risk_tier = floor_risk_tier

            # If synthesis returned empty text, use a degraded fallback
            if not response_text.strip():
                response_text = UNCERTAINTY_DEFAULTS["fallback_message"]
                degraded = True
                if _RISK_TIER_SEVERITY.get(final_risk_tier, 0) < _RISK_TIER_SEVERITY.get(
                    UNCERTAINTY_DEFAULTS["risk_tier"], 0
                ):
                    final_risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]

        except Exception as exc:
            logger.error(
                "ResponseSynthesizer failed: %s",
                exc,
                exc_info=True,
            )
            degraded = True
            final_risk_tier = "red" if all_degraded else floor_risk_tier
            # Ensure at least amber on any synthesis failure
            if _RISK_TIER_SEVERITY.get(final_risk_tier, 0) < _RISK_TIER_SEVERITY.get("amber", 0):
                final_risk_tier = "amber"
            response_text = UNCERTAINTY_DEFAULTS["critical_fallback_message"]
            citations = []
            disclaimers = []

        # If any specialist was degraded, append a completeness warning
        if degraded or all_degraded:
            completeness_warning = (
                "This response may be incomplete — please verify with a professional."
            )
            if completeness_warning not in disclaimers:
                disclaimers.append(completeness_warning)

        # Ensure appropriate disclaimers are present based on final risk tier
        tier_disclaimers = RISK_DISCLAIMERS.get(final_risk_tier, [])
        for d in tier_disclaimers:
            if d not in disclaimers:
                disclaimers.append(d)

        synthesis: Dict[str, Any] = {
            "response_text": response_text,
            "citations": citations,
            "disclaimers": disclaimers,
            "final_risk_tier": final_risk_tier,
        }

        if degraded:
            synthesis["degraded"] = True

        # Write final response to shared memory
        self.write_to_memory(
            content=synthesis,
            tags=["final_response", final_risk_tier],
            importance=1.0,
            segment="synthesis",
        )

        return synthesis
