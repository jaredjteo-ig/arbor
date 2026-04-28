"""ScorecardAgent — generates AI candidate scorecards (T-R054).

Given a candidate profile, the relevant job listing, the company's
scorecard template, and any interview feedback collected so far, the
agent produces a structured scorecard:

  - overall fit (1-5)
  - per-competency ratings keyed against the template criteria
  - strengths (list of short bullet points)
  - concerns (list of short bullet points)
  - recommended decision: proceed | reject | further_interview
  - free-text narrative summary

Provider/model resolution follows the same flow used by every other
agent in this codebase — Settings -> resolve_provider_and_model() ->
LLMKeyContext for BYOK overrides. No model strings are hardcoded.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from kaizen.core.base_agent import BaseAgent
from kaizen.memory import SharedMemoryPool
from kaizen.signatures import InputField, OutputField, Signature

from hr_advisory.agents.config import resolve_provider_and_model

logger = logging.getLogger(__name__)

VALID_DECISIONS = frozenset({"proceed", "reject", "further_interview"})


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------


class ScorecardSignature(Signature):
    """You are an expert recruitment analyst.

    Given a candidate's profile, a job listing's requirements, an
    interview-scorecard template (criteria + weights), and any
    interview feedback collected so far, produce a structured candidate
    scorecard. Be balanced, evidence-based, and avoid bias.
    """

    __intent__ = "Generate a structured candidate scorecard from profile + job + feedback"
    __guidelines__ = [
        "Score every criterion in the template on a 1-5 scale (1=poor, 5=excellent).",
        "Only score against evidence in the inputs — never invent qualifications.",
        "Strengths and concerns must be short, specific, evidence-anchored bullet points.",
        "Recommend 'proceed' only when the candidate clearly meets the role requirements.",
        "Recommend 'further_interview' if there is meaningful uncertainty.",
        "Recommend 'reject' only when there is a clear fit gap.",
        "Never reference protected attributes (race, religion, age, family status, gender).",
        "Output strictly valid JSON for every field — no prose outside JSON values.",
    ]

    # Inputs
    candidate_profile: str = InputField(
        description=(
            "JSON object describing the candidate: name, email, current_role, "
            "experience_summary, skills, education, resume_excerpt."
        ),
    )
    job_listing: str = InputField(
        description=(
            "JSON object describing the job listing: title, department, "
            "employment_type, description, requirements."
        ),
    )
    scorecard_template: str = InputField(
        description=(
            "JSON object describing the scorecard template: name, description, "
            "and a 'criteria' list of {name, weight} objects (weights sum to 1.0)."
        ),
    )
    interview_feedback: str = InputField(
        description=(
            "JSON list of interview-feedback records collected so far. Each item "
            "may include overall_rating, strengths, weaknesses, notes, recommendation. "
            "Empty list ('[]') if no feedback has been recorded yet."
        ),
        default="[]",
        required=False,
    )

    # Outputs
    overall_fit: str = OutputField(
        description="Overall fit score from 1-5 as a decimal string (e.g. '4.2').",
    )
    competency_ratings: str = OutputField(
        description=(
            "JSON object mapping each criterion name from the template to a 1-5 "
            "rating, e.g. {\"Technical depth\": 4, \"Communication\": 3}."
        ),
    )
    strengths: str = OutputField(
        description="JSON list of short, evidence-anchored strength bullet points.",
    )
    concerns: str = OutputField(
        description="JSON list of short, evidence-anchored concern bullet points.",
    )
    recommended_decision: str = OutputField(
        description=(
            "One of: 'proceed', 'reject', 'further_interview'. "
            "Reflects the recommended next step based on the scorecard."
        ),
    )
    narrative: str = OutputField(
        description=(
            "Plain-language, 2-4 sentence narrative summary that ties the "
            "ratings, strengths, and concerns together for the interviewer."
        ),
    )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class ScorecardAgentConfig:
    """Domain config for the scorecard agent.

    Auto-resolves provider+model from .env / Settings if not supplied.
    No model strings are hardcoded — DEFAULT_LLM_MODEL flows through
    resolve_provider_and_model().
    """

    llm_provider: str = ""
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048

    def __post_init__(self) -> None:
        if not self.model or not self.llm_provider:
            provider, model = resolve_provider_and_model()
            if not self.llm_provider:
                self.llm_provider = provider
            if not self.model:
                self.model = model


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ScorecardAgent(BaseAgent):
    """Kaizen agent that produces structured candidate scorecards.

    Public API:
        agent.generate(candidate, job, template, feedback=None) -> dict
    """

    domain = "scorecard"
    domain_label = "Candidate Scorecard"

    def __init__(
        self,
        config: Optional[ScorecardAgentConfig] = None,
        shared_memory: Optional[SharedMemoryPool] = None,
        **kwargs: Any,
    ) -> None:
        config = config or ScorecardAgentConfig()
        super().__init__(
            config=config,
            signature=ScorecardSignature(),
            shared_memory=shared_memory,
            agent_id="scorecard_agent",
            mcp_servers=[],
            **kwargs,
        )

    def _default_signature(self) -> ScorecardSignature:
        return ScorecardSignature()

    def _generate_system_prompt(self) -> str:
        return (
            "You are an expert recruitment analyst writing structured candidate "
            "scorecards for hiring managers.\n\n"
            "TASK: Read the candidate profile, the job listing, the scorecard "
            "template (criteria + weights), and any interview feedback collected "
            "so far. Produce a balanced, evidence-based scorecard.\n\n"
            "RULES:\n"
            "1. Rate every criterion from the template on a 1-5 scale.\n"
            "2. Anchor strengths and concerns to specific evidence in the inputs.\n"
            "3. Never invent qualifications, employment history, or skills.\n"
            "4. Never reference protected attributes (race, religion, age, "
            "family status, gender, nationality, disability).\n"
            "5. Recommend 'proceed' only when the candidate clearly meets the "
            "role requirements; 'further_interview' for meaningful uncertainty; "
            "'reject' only for a clear fit gap.\n"
            "6. Keep the narrative to 2-4 plain-language sentences.\n\n"
            "OUTPUT: All fields are JSON-serialisable strings/objects/lists as "
            "described in the signature. Respond ONLY with the structured JSON "
            "fields — no markdown, no code fences, no surrounding prose."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        candidate_profile: Dict[str, Any],
        job_listing: Dict[str, Any],
        scorecard_template: Dict[str, Any],
        interview_feedback: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate a structured scorecard for a candidate.

        Args:
            candidate_profile: Candidate dict (name, role, skills, etc.).
            job_listing: Job listing dict (title, requirements, etc.).
            scorecard_template: Template dict with a ``criteria`` list of
                {name, weight}. ``criteria`` may also be a JSON string —
                this is normalised before being sent to the LLM.
            interview_feedback: Optional list of interview-feedback dicts.

        Returns:
            Dict with keys: scorecard (the structured template-shaped result),
            degraded (bool, True if any field had to be defaulted), and
            template_id passthrough for the caller.
        """
        criteria = self._normalise_criteria(scorecard_template)
        criteria_names = [c["name"] for c in criteria]

        normalised_template = {
            "id": scorecard_template.get("id"),
            "name": scorecard_template.get("name", ""),
            "description": scorecard_template.get("description", ""),
            "criteria": criteria,
        }

        try:
            result = self.run(
                candidate_profile=json.dumps(candidate_profile, default=str),
                job_listing=json.dumps(job_listing, default=str),
                scorecard_template=json.dumps(normalised_template, default=str),
                interview_feedback=json.dumps(interview_feedback or [], default=str),
            )
        except Exception as exc:  # noqa: BLE001 — fail-safe path, see fallback
            logger.error("ScorecardAgent LLM call failed: %s", exc, exc_info=True)
            return self._fallback_scorecard(criteria_names, reason=str(exc))

        degraded = False

        overall_fit_str = self.extract_str(result, "overall_fit", default="")
        try:
            overall_fit = float(overall_fit_str) if overall_fit_str else 0.0
            overall_fit = max(1.0, min(5.0, overall_fit)) if overall_fit_str else 0.0
        except (TypeError, ValueError):
            logger.warning(
                "ScorecardAgent returned unparseable overall_fit '%s'", overall_fit_str,
            )
            overall_fit = 0.0
            degraded = True

        ratings_raw = self.extract_dict(result, "competency_ratings", default={})
        ratings = self._coerce_ratings(ratings_raw, criteria_names)
        if len(ratings) != len(criteria_names):
            degraded = True

        strengths = self._coerce_string_list(
            self.extract_list(result, "strengths", default=[]),
        )
        concerns = self._coerce_string_list(
            self.extract_list(result, "concerns", default=[]),
        )

        decision = self.extract_str(
            result, "recommended_decision", default="further_interview",
        ).strip().lower().replace(" ", "_")
        if decision not in VALID_DECISIONS:
            logger.warning(
                "ScorecardAgent returned invalid decision '%s', defaulting to further_interview",
                decision,
            )
            decision = "further_interview"
            degraded = True

        narrative = self.extract_str(result, "narrative", default="").strip()
        if not narrative:
            narrative = (
                "An automated scorecard could not produce a complete narrative "
                "for this candidate. Please review the ratings, strengths, and "
                "concerns directly before deciding."
            )
            degraded = True

        scorecard: Dict[str, Any] = {
            "template_id": normalised_template.get("id"),
            "template_name": normalised_template.get("name", ""),
            "overall_fit": round(overall_fit, 2),
            "competency_ratings": ratings,
            "strengths": strengths,
            "concerns": concerns,
            "recommended_decision": decision,
            "narrative": narrative,
            "criteria": criteria,
        }

        output = {"scorecard": scorecard, "degraded": degraded}

        try:
            self.write_to_memory(
                content={
                    "template_id": normalised_template.get("id"),
                    "decision": decision,
                    "overall_fit": scorecard["overall_fit"],
                },
                tags=["scorecard", "ai_generated"],
                importance=0.6,
                segment="action_output",
            )
        except Exception:  # noqa: BLE001 — memory write must never break generation
            logger.debug("ScorecardAgent: shared-memory write skipped", exc_info=True)

        return output

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_criteria(template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Accept either a list or a JSON string for template['criteria']."""
        criteria_field = template.get("criteria", [])
        if isinstance(criteria_field, str):
            try:
                criteria_field = json.loads(criteria_field)
            except (TypeError, ValueError):
                criteria_field = []
        if not isinstance(criteria_field, list):
            return []

        cleaned: List[Dict[str, Any]] = []
        for item in criteria_field:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            try:
                weight = float(item.get("weight", 0))
            except (TypeError, ValueError):
                weight = 0.0
            cleaned.append({"name": name, "weight": weight})
        return cleaned

    @staticmethod
    def _coerce_ratings(
        raw: Dict[str, Any], criteria_names: List[str],
    ) -> Dict[str, int]:
        """Map LLM ratings onto template criterion names, clamped to 1-5."""
        ratings: Dict[str, int] = {}
        if not isinstance(raw, dict):
            return ratings

        # Build a case-insensitive lookup so the LLM can use slight name variants.
        lookup = {name.lower(): name for name in criteria_names}
        for key, value in raw.items():
            canonical = lookup.get(str(key).strip().lower())
            if canonical is None:
                continue
            try:
                rating = int(round(float(value)))
            except (TypeError, ValueError):
                continue
            ratings[canonical] = max(1, min(5, rating))
        return ratings

    @staticmethod
    def _coerce_string_list(items: Any) -> List[str]:
        if not isinstance(items, list):
            return []
        return [str(item).strip() for item in items if str(item).strip()]

    @staticmethod
    def _fallback_scorecard(
        criteria_names: List[str], reason: str,
    ) -> Dict[str, Any]:
        return {
            "scorecard": {
                "template_id": None,
                "template_name": "",
                "overall_fit": 0.0,
                "competency_ratings": {name: 0 for name in criteria_names},
                "strengths": [],
                "concerns": [],
                "recommended_decision": "further_interview",
                "narrative": (
                    "The AI scorecard service was unable to generate a "
                    "scorecard for this candidate. Please complete the "
                    "scorecard manually."
                ),
                "criteria": [{"name": n, "weight": 0.0} for n in criteria_names],
                "error": reason,
            },
            "degraded": True,
        }


__all__ = [
    "ScorecardAgent",
    "ScorecardAgentConfig",
    "ScorecardSignature",
    "VALID_DECISIONS",
]
