"""Base class for domain specialist agents.

All seven specialist agents share the same public API shape and memory
interaction pattern.  This base class captures that common logic so
individual specialists only need to supply:

  1. Their domain key (e.g. ``"employment_act"``)
  2. Their Signature subclass
  3. Their system prompt (via ``_generate_system_prompt``)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from kaizen.core.base_agent import BaseAgent
from kaizen.memory import SharedMemoryPool

from hr_advisory.agents.config import SpecialistConfig, UNCERTAINTY_DEFAULTS

logger = logging.getLogger(__name__)

VALID_RISK_TIERS = frozenset(["green", "amber", "red"])


class BaseDomainSpecialist(BaseAgent):
    """Abstract specialist that advises on a single HR regulatory domain.

    Subclasses MUST set ``domain`` and override ``_generate_system_prompt``.
    """

    # Subclasses override these class-level attributes.
    domain: str = ""  # e.g. "cpf"
    domain_label: str = ""  # e.g. "CPF"

    def __init__(
        self,
        config: Optional[SpecialistConfig] = None,
        shared_memory: Optional[SharedMemoryPool] = None,
        signature=None,
        **kwargs,
    ):
        config = config or SpecialistConfig()
        super().__init__(
            config=config,
            signature=signature,
            shared_memory=shared_memory,
            agent_id=f"{self.domain}_specialist",
            mcp_servers=[],
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def advise(
        self,
        query_text: str,
        company_context: Optional[Dict[str, Any]] = None,
        relevant_provisions: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Produce a domain-scoped advisory for the given query.

        Args:
            query_text: The user's HR question.
            company_context: Optional company profile dict.
            relevant_provisions: Optional list of KB provision dicts.
            conversation_history: Optional formatted string of previous
                conversation turns for multi-turn context.

        Returns:
            Dict with keys: answer_text, cited_provisions, confidence,
            risk_tier, cross_domain_flags, domain. May also include
            degraded=True when the specialist encountered errors.
        """
        degraded = False

        try:
            ctx_str = json.dumps(company_context) if company_context else "{}"
            prov_str = json.dumps(relevant_provisions) if relevant_provisions else "[]"
            history_str = conversation_history if conversation_history else ""

            result = self.run(
                query_text=query_text,
                company_context=ctx_str,
                relevant_provisions=prov_str,
                conversation_history=history_str,
            )

            answer_text = self.extract_str(
                result,
                "answer_text",
                default="",
            )
            cited_provisions = self.extract_list(result, "cited_provisions", default=[])
            confidence_str = self.extract_str(
                result, "confidence", default=str(UNCERTAINTY_DEFAULTS["confidence"])
            )
            risk_tier = self.extract_str(
                result, "risk_tier", default=UNCERTAINTY_DEFAULTS["risk_tier"]
            )
            cross_domain_flags = self.extract_list(result, "cross_domain_flags", default=[])

            # Validate confidence — escalate on parse failure, never assume medium
            try:
                confidence = float(confidence_str)
                confidence = max(0.0, min(1.0, confidence))
            except (TypeError, ValueError):
                logger.warning(
                    "Specialist %s returned unparseable confidence '%s', "
                    "defaulting to %.1f (uncertainty)",
                    self.domain,
                    confidence_str,
                    UNCERTAINTY_DEFAULTS["confidence"],
                )
                confidence = UNCERTAINTY_DEFAULTS["confidence"]
                degraded = True

            # Validate risk tier — escalate on invalid, never suppress
            if risk_tier not in VALID_RISK_TIERS:
                logger.warning(
                    "Specialist %s returned invalid risk_tier '%s', escalating to amber",
                    self.domain,
                    risk_tier,
                )
                risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]
                degraded = True

            # If the LLM returned empty answer text, treat as a degraded response
            if not answer_text.strip():
                answer_text = (
                    f"I was unable to provide a fully analyzed response for this "
                    f"{self.domain_label} question. Please consult a professional "
                    f"for guidance."
                )
                degraded = True
                confidence = min(confidence, UNCERTAINTY_DEFAULTS["confidence"])
                risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]

        except Exception as exc:
            logger.error(
                "Specialist %s failed for query: %.100s — %s",
                self.domain,
                query_text,
                exc,
                exc_info=True,
            )
            degraded = True
            answer_text = (
                f"Our {self.domain_label} specialist is temporarily unavailable. "
                f"The relevant provisions are listed below for your reference. "
                f"You can also connect with an employment law specialist for guidance."
            )
            cited_provisions = []
            confidence = 0.2
            risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]
            cross_domain_flags = []

        advisory: Dict[str, Any] = {
            "domain": self.domain,
            "answer_text": answer_text,
            "cited_provisions": cited_provisions,
            "confidence": confidence,
            "risk_tier": risk_tier,
            "cross_domain_flags": cross_domain_flags,
        }

        if degraded:
            advisory["degraded"] = True

        # Write to shared memory for downstream consumption
        self.write_to_memory(
            content=advisory,
            tags=[self.domain, "specialist_output"],
            importance=confidence,
            segment="specialist_output",
        )

        return advisory
