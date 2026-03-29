"""ResponseSynthesizerAgent -- synthesizes final advisory response.

Reads all specialist outputs from SharedMemoryPool, then produces
a plain-language answer with citations and risk-tier disclaimers
suitable for Singapore SME owners and managers.
"""

import dataclasses
import json
import logging
from typing import Any, Dict, List, Optional

try:
    from kaizen import BaseAgent
except ImportError:
    from kaizen import CoreAgent as BaseAgent

from hr_advisory.agents.config import ResponseSynthesizerConfig, UNCERTAINTY_DEFAULTS
from hr_advisory.agents.signatures import ResponseSynthesizerSignature
from hr_advisory.agents.specialists._base import _KaizenCompatMixin
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


class ResponseSynthesizerAgent(_KaizenCompatMixin, BaseAgent):
    """Synthesize specialist outputs into a plain-language advisory.

    Extension points used:
      - _default_signature()      -> ResponseSynthesizerSignature
      - _generate_system_prompt() -> synthesis prompt with citation rules
    """

    def __init__(
        self,
        config: Optional[ResponseSynthesizerConfig] = None,
        shared_memory: Any = None,
        **kwargs,
    ):
        config = config or ResponseSynthesizerConfig()
        super().__init__(
            agent_id="response_synthesizer",
            config=dataclasses.asdict(config),
            signature=ResponseSynthesizerSignature(),
        )
        self.shared_memory = shared_memory

    # ------------------------------------------------------------------
    # Extension points
    # ------------------------------------------------------------------

    def _default_signature(self):
        return ResponseSynthesizerSignature()

    def _generate_system_prompt(self) -> str:
        return (
            "You are Arbor — a senior HR advisor synthesizing specialist analysis "
            "into clear, actionable guidance for Singapore SME owners.\n\n"
            "You receive specialist outputs covering legal provisions, compliance "
            "checks, and domain analysis. Your job is to turn this into advice "
            "a business owner can act on.\n\n"
            "BOUNDARIES:\n"
            "- Only cite provisions that appear in the specialist outputs. Never "
            "fabricate section numbers.\n"
            "- If specialists conflict, surface the conflict — never silently "
            "pick one side.\n"
            "- Never downgrade risk tier below what any specialist flagged.\n"
            "- Low-confidence specialist outputs (< 0.4) → hedge language, not "
            "definitive claims.\n"
            "- For RED-tier risks, always recommend professional legal review.\n\n"
            "QUALITY:\n"
            "- Lead with the answer, not the preamble.\n"
            "- Be as thorough as the question demands. Cover the law, the "
            "practical steps, the pitfalls, and the edge cases.\n"
            "- Use 'you' language. Be direct. No filler.\n"
            "- Use markdown for structure when it helps.\n\n"
            "OUTPUT: JSON object with:\n"
            '  "response_text": "the full advisory",\n'
            '  "citations": [{"provision": "...", "section": "...", "act": "..."}],\n'
            '  "disclaimers": ["..."],\n'
            '  "final_risk_tier": "green" | "amber" | "red"\n\n'
            "Respond ONLY with valid JSON."
        ) + SYSTEM_PROMPT_SECURITY_FOOTER

    # ------------------------------------------------------------------
    # Direct LLM fallback (bypasses Kaizen signature parsing)
    # ------------------------------------------------------------------

    def _direct_llm_synthesis(
        self,
        outputs_json: str,
        risk_tier: str,
        company_context: str,
        conversation_history: str,
        compliance_results: str,
    ) -> str:
        """Call the LLM directly when Kaizen signature extraction fails.

        Returns the raw LLM text as a string (not a dict). The caller
        treats string results as the response_text directly.
        """
        import os

        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
            model = os.environ.get("DEFAULT_LLM_MODEL", "gpt-5-mini-2025-08-07")

            system_prompt = self._generate_system_prompt()
            user_prompt = (
                f"Specialist outputs:\n{outputs_json}\n\n"
                f"Risk tier: {risk_tier}\n"
                f"Company context: {company_context}\n"
            )
            if conversation_history:
                user_prompt += f"\nConversation history:\n{conversation_history}\n"
            if compliance_results and compliance_results != "{}":
                user_prompt += f"\nCompliance results:\n{compliance_results}\n"
            user_prompt += (
                "\nWrite the advisory response following the mandatory template. "
                "Return ONLY the response text, no JSON wrapping."
            )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            text = response.choices[0].message.content or ""
            logger.info("Direct LLM synthesis succeeded (%d chars)", len(text))
            return text
        except Exception as exc:
            logger.error("Direct LLM synthesis failed: %s", exc)
            raise

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

            # Detect Kaizen error dicts — these are NOT usable responses
            if isinstance(result, dict) and result.get("success") is False:
                logger.warning(
                    "ResponseSynthesizer Kaizen extraction failed: %s — trying direct LLM call",
                    result.get("error", "unknown"),
                )
                # Bypass Kaizen signature parsing — call LLM directly
                result = self._direct_llm_synthesis(
                    outputs_json, floor_risk_tier, ctx_str, history_str, compliance_str
                )

            # Extract structured fields, falling back to raw text if parsing fails
            try:
                response_text = self.extract_str(result, "response_text", default="")
            except Exception:
                response_text = ""

            # If structured extraction failed but we have raw text, use it
            if not response_text and result is not None:
                raw = str(result) if not isinstance(result, str) else result
                # Only use raw text if it looks like actual content (not error dicts)
                if raw and len(raw) > 50 and "error" not in raw[:50].lower():
                    response_text = raw
                    logger.info(
                        "Using raw LLM output as response_text (structured extraction failed)"
                    )

            try:
                citations = self.extract_list(result, "citations", default=[])
            except Exception:
                citations = []
            try:
                disclaimers = self.extract_list(result, "disclaimers", default=[])
            except Exception:
                disclaimers = []
            try:
                final_risk_tier = self.extract_str(
                    result, "final_risk_tier", default=floor_risk_tier
                )
            except Exception:
                final_risk_tier = floor_risk_tier

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
