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

from kaizen import Agent as BaseAgent  # kaizen 2.3.1+ canonical import

from hr_advisory.agents.config import SpecialistConfig, UNCERTAINTY_DEFAULTS
from hr_advisory.workflows.guardrails import SYSTEM_PROMPT_SECURITY_FOOTER

logger = logging.getLogger(__name__)

VALID_RISK_TIERS = frozenset(["green", "amber", "red"])


class _KaizenCompatMixin:
    """Compatibility shims for kailash-kaizen 2.3.1.

    Agent(model, system_prompt) replaced old BaseAgent(agent_id, config, signature).
    Agent.run(task) is task-based; this mixin provides run(**kwargs) → run_sync(task).
    """

    shared_memory: Any = None
    agent_id: str = ""

    def run(self, **inputs: Any) -> Dict[str, Any]:
        """Convert keyword inputs to a task string for Agent.run_sync(task)."""
        task = json.dumps(inputs, default=str)
        result = super().run_sync(task)  # type: ignore[misc]
        text = result.text if hasattr(result, "text") else str(result)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"answer_text": text}

    def write_to_memory(
        self,
        content: Any,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        segment: str = "execution",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write insights to shared memory if available."""
        if not self.shared_memory:
            return
        content_str = json.dumps(content) if isinstance(content, (dict, list)) else str(content)
        insight: Dict[str, Any] = {
            "agent_id": getattr(self, "agent_id", ""),
            "content": content_str,
            "tags": tags or [],
            "importance": importance,
            "segment": segment,
            "metadata": metadata or {},
        }
        if hasattr(self.shared_memory, "write_insight"):
            self.shared_memory.write_insight(insight)

    def extract_str(self, result: Dict[str, Any], field_name: str, default: str = "") -> str:
        """Extract a string field from result with type safety."""
        field_value = result.get(field_name, default)
        return str(field_value) if field_value is not None else default

    def extract_list(
        self, result: Dict[str, Any], field_name: str, default: Optional[List] = None
    ) -> List:
        """Extract a list field from result, parsing JSON strings if needed."""
        if default is None:
            default = []
        field_value = result.get(field_name, default)
        if isinstance(field_value, list):
            return field_value
        if isinstance(field_value, str):
            try:
                parsed = json.loads(field_value) if field_value else default
                return parsed if isinstance(parsed, list) else default
            except Exception:
                return default
        return default

    def extract_dict(
        self, result: Dict[str, Any], field_name: str, default: Optional[Dict] = None
    ) -> Dict:
        """Extract a dict field from result, parsing JSON strings if needed."""
        if default is None:
            default = {}
        field_value = result.get(field_name, default)
        if isinstance(field_value, dict):
            return field_value
        if isinstance(field_value, str):
            try:
                parsed = json.loads(field_value) if field_value else default
                return parsed if isinstance(parsed, dict) else default
            except Exception:
                return default
        return default


class BaseDomainSpecialist(_KaizenCompatMixin, BaseAgent):
    """Abstract specialist that advises on a single HR regulatory domain.

    Subclasses MUST set ``domain`` and override ``_generate_system_prompt``.
    The security footer is automatically appended to all system prompts.
    """

    # Subclasses override these class-level attributes.
    domain: str = ""  # e.g. "cpf"
    domain_label: str = ""  # e.g. "CPF"

    def __init__(
        self,
        config: Optional[SpecialistConfig] = None,
        shared_memory: Any = None,
        signature=None,
        **kwargs,
    ):
        import os

        config = config or SpecialistConfig()
        model = os.environ.get("OPENAI_PROD_MODEL", os.environ.get("DEFAULT_LLM_MODEL", ""))
        system_prompt = self._domain_system_prompt() + SYSTEM_PROMPT_SECURITY_FOOTER
        super().__init__(
            model=model,
            system_prompt=system_prompt,
        )
        self.agent_id = f"{self.domain}_specialist"
        self.shared_memory = shared_memory
        self._specialist_config = config

    def write_to_memory(
        self,
        content: Any,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        segment: str = "execution",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write insights to shared memory if available."""
        if not self.shared_memory:
            return
        content_str = json.dumps(content) if isinstance(content, (dict, list)) else str(content)
        insight = {
            "agent_id": self.agent_id,
            "content": content_str,
            "tags": tags or [],
            "importance": importance,
            "segment": segment,
            "metadata": metadata or {},
        }
        if hasattr(self.shared_memory, "write_insight"):
            self.shared_memory.write_insight(insight)

    def extract_str(self, result: Dict[str, Any], field_name: str, default: str = "") -> str:
        """Extract a string field from result with type safety."""
        field_value = result.get(field_name, default)
        return str(field_value) if field_value is not None else default

    def extract_list(
        self, result: Dict[str, Any], field_name: str, default: Optional[List] = None
    ) -> List:
        """Extract a list field from result, parsing JSON strings if needed."""
        if default is None:
            default = []
        field_value = result.get(field_name, default)
        if isinstance(field_value, list):
            return field_value
        if isinstance(field_value, str):
            try:
                parsed = json.loads(field_value) if field_value else default
                return parsed if isinstance(parsed, list) else default
            except Exception:
                return default
        return default

    def extract_dict(
        self, result: Dict[str, Any], field_name: str, default: Optional[Dict] = None
    ) -> Dict:
        """Extract a dict field from result, parsing JSON strings if needed."""
        if default is None:
            default = {}
        field_value = result.get(field_name, default)
        if isinstance(field_value, dict):
            return field_value
        if isinstance(field_value, str):
            try:
                parsed = json.loads(field_value) if field_value else default
                return parsed if isinstance(parsed, dict) else default
            except Exception:
                return default
        return default

    def _generate_system_prompt(self) -> str:
        """Override to append security footer to all specialist prompts."""
        base_prompt = self._domain_system_prompt()
        return base_prompt + SYSTEM_PROMPT_SECURITY_FOOTER

    def _domain_system_prompt(self) -> str:
        """Subclasses override this instead of _generate_system_prompt."""
        return f"You are a {self.domain_label} specialist for Singapore employment matters."

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
