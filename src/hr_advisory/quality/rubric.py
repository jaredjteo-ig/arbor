"""Quality rubric scoring system for HR advisory responses.

Scores responses across 8 dimensions (1-5 each). Overall score uses the
weakest-link principle: overall = min(all dimension scores).

Usage:
    rubric = QualityRubric()
    result = rubric.score(query, response, context)
    print(result.passed, result.overall_score, result.dimension_flags)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from hr_advisory.quality.automated_checks import AutomatedChecks
from hr_advisory.quality.llm_judge import LLMJudge, SEMANTIC_DIMENSIONS

logger = logging.getLogger(__name__)

# The 8 canonical dimension names
VALID_DIMENSIONS = frozenset([
    "legal_accuracy",
    "contextual_relevance",
    "conversational_coherence",
    "actionability",
    "risk_awareness",
    "citation_quality",
    "language_understanding",
    "completeness",
])

# The 4 automated dimensions (subset of the 8)
AUTOMATED_DIMENSIONS = frozenset([
    "citation_quality",
    "risk_awareness",
    "response_structure",
    "disclaimer_presence",
])


@dataclass
class RubricResult:
    """Result of scoring a response across all 8 quality dimensions.

    Attributes:
        dimension_scores: dict mapping each of the 8 dimension names to a
            float score in [1.0, 5.0].
        overall_score: min of all dimension scores (weakest-link).
        passed: True if overall_score >= 3.0.
        dimension_flags: list of dimension names scoring below 3.0.
        details: per-dimension explanation text.
    """

    dimension_scores: dict[str, float]
    details: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate exactly 8 known dimensions
        keys = set(self.dimension_scores.keys())
        if len(keys) != 8:
            raise ValueError(
                f"RubricResult requires exactly 8 dimensions, got {len(keys)}: "
                f"{sorted(keys)}"
            )
        unknown = keys - VALID_DIMENSIONS
        if unknown:
            raise ValueError(
                f"Unknown dimension(s) in scores: {sorted(unknown)}. "
                f"Valid dimensions: {sorted(VALID_DIMENSIONS)}"
            )
        for dim, score in self.dimension_scores.items():
            if not (1.0 <= score <= 5.0):
                raise ValueError(
                    f"Score for '{dim}' is {score}; must be between 1.0 and 5.0 inclusive."
                )

    @property
    def overall_score(self) -> float:
        """Weakest-link: min across all dimensions."""
        return min(self.dimension_scores.values())

    @property
    def passed(self) -> bool:
        """True if overall score meets the 3.0 threshold."""
        return self.overall_score >= 3.0

    @property
    def dimension_flags(self) -> list[str]:
        """Dimensions scoring below the 3.0 threshold."""
        return [dim for dim, score in self.dimension_scores.items() if score < 3.0]


class QualityRubric:
    """Orchestrates automated checks + LLM-as-judge to produce a RubricResult.

    Automated checks run first (fast, deterministic) for citation_quality,
    risk_awareness, response_structure, and disclaimer_presence.

    Then the LLM judge evaluates the remaining semantic dimensions:
    legal_accuracy, contextual_relevance, conversational_coherence,
    actionability, language_understanding, completeness.

    The automated response_structure and disclaimer_presence checks are
    factored into the risk_awareness score (averaged with the LLM judge's
    risk_awareness score) but are NOT separate dimensions in the final 8.
    """

    def __init__(self) -> None:
        self._llm_judge: LLMJudge | None = None

    def _get_judge(self) -> LLMJudge:
        """Lazy-initialize the LLM judge."""
        if self._llm_judge is None:
            self._llm_judge = LLMJudge()
        return self._llm_judge

    def score(
        self,
        query: str,
        response: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> RubricResult:
        """Score an advisory response across all 8 dimensions.

        Args:
            query: The user's original HR question.
            response: Dict with keys: response_text, risk_tier, cited_provisions,
                confidence, domains.
            context: Optional company context dict.

        Returns:
            RubricResult with all 8 dimension scores.
        """
        response_text = response.get("response_text", "")
        risk_tier = response.get("risk_tier", "green")
        cited_provisions = response.get("cited_provisions", [])
        context = context or {}

        if not response_text:
            raise ValueError(
                "Cannot score an empty response. 'response_text' is required."
            )

        # ── Step 1: Automated checks (fast, deterministic) ────────────
        auto_scores, auto_details = AutomatedChecks.run_all(
            response_text=response_text,
            risk_tier=risk_tier,
            cited_provisions=cited_provisions,
        )

        # ── Step 2: LLM judge for semantic dimensions ────────────────
        judge = self._get_judge()
        llm_scores: dict[str, float] = {}
        llm_details: dict[str, str] = {}

        for dim in SEMANTIC_DIMENSIONS:
            score_val, explanation = judge.evaluate(
                dimension_name=dim,
                query=query,
                response_text=response_text,
                context=context,
                risk_tier=risk_tier,
                citations=cited_provisions,
            )
            llm_scores[dim] = score_val
            llm_details[dim] = explanation

        # ── Step 3: Merge into final 8-dimension result ──────────────
        # Automated dimensions: citation_quality, risk_awareness
        # LLM dimensions: legal_accuracy, contextual_relevance,
        #   conversational_coherence, actionability, language_understanding,
        #   completeness
        #
        # risk_awareness: combine automated risk check with LLM risk_awareness
        # by taking the minimum (conservative: if either flags an issue, it shows)
        #
        # response_structure and disclaimer_presence are auxiliary automated
        # signals. They factor into the overall risk_awareness and actionability
        # scores but are not standalone dimensions.

        dimension_scores: dict[str, float] = {}
        details: dict[str, str] = {}

        # citation_quality — purely automated
        dimension_scores["citation_quality"] = auto_scores["citation_quality"]
        details["citation_quality"] = auto_details["citation_quality"]

        # risk_awareness — combine automated + LLM (take minimum)
        auto_risk = auto_scores["risk_awareness"]
        llm_risk = llm_scores.get("risk_awareness", auto_risk)
        # Also factor in disclaimer presence as a secondary risk signal
        disclaimer_score = auto_scores["disclaimer_presence"]
        combined_risk = min(auto_risk, disclaimer_score)
        dimension_scores["risk_awareness"] = combined_risk
        details["risk_awareness"] = (
            f"Automated: {auto_details['risk_awareness']} | "
            f"Disclaimer: {auto_details['disclaimer_presence']}"
        )

        # actionability — LLM score, but penalize if response lacks structure
        llm_action = llm_scores.get("actionability", 3.0)
        structure_score = auto_scores["response_structure"]
        # If structure is poor (< 3), it limits actionability
        if structure_score < 3.0:
            dimension_scores["actionability"] = min(llm_action, structure_score)
        else:
            dimension_scores["actionability"] = llm_action
        details["actionability"] = (
            llm_details.get("actionability", "")
            + f" [Structure: {auto_details['response_structure']}]"
        )

        # Pure LLM dimensions
        for dim in ["legal_accuracy", "contextual_relevance",
                     "conversational_coherence", "language_understanding",
                     "completeness"]:
            dimension_scores[dim] = llm_scores.get(dim, 3.0)
            details[dim] = llm_details.get(dim, "")

        return RubricResult(
            dimension_scores=dimension_scores,
            details=details,
        )


def score_batch(
    test_cases: list[dict],
    rubric: QualityRubric | None = None,
) -> list[RubricResult]:
    """Score multiple test cases in sequence.

    Args:
        test_cases: List of dicts, each with keys: "query", "response", "context".
        rubric: Optional QualityRubric instance. Creates one if not provided.

    Returns:
        List of RubricResult, one per test case.
    """
    if rubric is None:
        rubric = QualityRubric()

    results: list[RubricResult] = []
    for i, case in enumerate(test_cases):
        query = case.get("query", "")
        response = case.get("response", {})
        context = case.get("context")

        if not query:
            raise ValueError(f"Test case {i} is missing 'query'.")
        if not response:
            raise ValueError(f"Test case {i} is missing 'response'.")

        result = rubric.score(query=query, response=response, context=context)
        results.append(result)

    return results
