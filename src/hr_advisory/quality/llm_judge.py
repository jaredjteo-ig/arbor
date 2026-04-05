"""LLM-as-judge for semantic quality dimensions.

Evaluates HR advisory responses on dimensions that require semantic
understanding: legal accuracy, contextual relevance, conversational
coherence, actionability, language understanding, and completeness.

Model name comes from .env via get_settings() — never hardcoded.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from hr_advisory.config.settings import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Judge prompt criteria per dimension
# ---------------------------------------------------------------------------

DIMENSION_CRITERIA: dict[str, dict[str, str]] = {
    "legal_accuracy": {
        "description": "Legal Accuracy: provisions cited exist and apply correctly",
        "criteria_1": "Cites non-existent laws or completely wrong provisions",
        "criteria_2": "Cites real provisions but applies them incorrectly",
        "criteria_3": "Cites correct provisions with minor application gaps",
        "criteria_4": "Correct provisions, correctly applied, minor detail missing",
        "criteria_5": "All cited provisions are correct, current, and precisely applied",
    },
    "contextual_relevance": {
        "description": "Contextual Relevance: advice matches the company's sector, size, and situation",
        "criteria_1": "Advice is completely generic with no contextual adaptation",
        "criteria_2": "Mentions context but advice does not actually adapt to it",
        "criteria_3": "Partially adapted to context with some gaps",
        "criteria_4": "Well-adapted to context with minor omissions",
        "criteria_5": "Perfectly tailored to the specific company context, sector, and situation",
    },
    "conversational_coherence": {
        "description": "Conversational Coherence: references prior turns correctly, no contradictions",
        "criteria_1": "Contradicts itself or ignores the question entirely",
        "criteria_2": "Partially addresses the question with internal inconsistencies",
        "criteria_3": "Addresses the question coherently with minor gaps",
        "criteria_4": "Coherent and on-topic with good flow",
        "criteria_5": "Perfectly coherent, directly addresses the query, no contradictions",
    },
    "actionability": {
        "description": "Actionability: contains concrete next steps the user can take today",
        "criteria_1": "No actionable steps provided at all",
        "criteria_2": "Vague suggestions but nothing the user can act on today",
        "criteria_3": "Some actionable steps but lacking specifics (who, when, how)",
        "criteria_4": "Clear actionable steps with most details (who to contact, deadlines)",
        "criteria_5": "Highly specific, ordered action steps with timelines, contacts, and forms",
    },
    "language_understanding": {
        "description": "Language Understanding: handles Singlish, abbreviations, and implicit context",
        "criteria_1": "Completely misunderstands the query or local context",
        "criteria_2": "Misinterprets key terms or local abbreviations",
        "criteria_3": "Understands the core question but misses local nuance",
        "criteria_4": "Good understanding of local context and abbreviations",
        "criteria_5": "Excellent handling of Singlish, abbreviations, and implicit local context",
    },
    "completeness": {
        "description": "Completeness: all parts of a multi-part question are answered",
        "criteria_1": "Answers only one aspect and ignores the rest",
        "criteria_2": "Addresses some parts but misses major components",
        "criteria_3": "Addresses most parts with gaps in coverage",
        "criteria_4": "Addresses all parts with minor gaps in depth",
        "criteria_5": "Thoroughly addresses every part of the query with appropriate depth",
    },
}

# The 6 semantic dimensions evaluated by LLM
SEMANTIC_DIMENSIONS = list(DIMENSION_CRITERIA.keys())

_JUDGE_PROMPT_TEMPLATE = """\
You are evaluating an HR advisory response for {dimension_description}.

QUERY: {query}
RESPONSE: {response_text}
COMPANY CONTEXT: {context}
RISK TIER: {risk_tier}
CITATIONS: {citations}

Score this response on {dimension_name} from 1-5:
1 = {criteria_1}
2 = {criteria_2}
3 = {criteria_3}
4 = {criteria_4}
5 = {criteria_5}

Respond ONLY with JSON: {{"score": X, "explanation": "..."}}
"""


class LLMJudge:
    """LLM-based evaluator for semantic quality dimensions.

    Uses OpenAI chat completions (model from settings) to score each
    dimension independently.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.openai_prod_model or settings.default_llm_model
        self._api_key = settings.openai_api_key
        if not self._model:
            raise ValueError(
                "LLM judge requires a model name. Set OPENAI_PROD_MODEL or "
                "DEFAULT_LLM_MODEL in your .env file."
            )

    def evaluate(
        self,
        dimension_name: str,
        query: str,
        response_text: str,
        context: dict[str, Any],
        risk_tier: str,
        citations: list[str],
    ) -> tuple[float, str]:
        """Evaluate a single dimension via LLM-as-judge.

        Args:
            dimension_name: One of the SEMANTIC_DIMENSIONS keys.
            query: The user's original query.
            response_text: The advisory response text.
            context: Company context dict.
            risk_tier: "green", "amber", or "red".
            citations: List of cited provision IDs.

        Returns:
            (score, explanation) tuple. On error returns (3.0, "evaluation unavailable").
        """
        if dimension_name not in DIMENSION_CRITERIA:
            raise ValueError(
                f"Unknown dimension '{dimension_name}'. "
                f"Valid dimensions: {list(DIMENSION_CRITERIA.keys())}"
            )

        criteria = DIMENSION_CRITERIA[dimension_name]

        prompt = _JUDGE_PROMPT_TEMPLATE.format(
            dimension_description=criteria["description"],
            dimension_name=dimension_name,
            query=query,
            response_text=response_text,
            context=json.dumps(context) if context else "{}",
            risk_tier=risk_tier,
            citations=", ".join(citations) if citations else "none",
            criteria_1=criteria["criteria_1"],
            criteria_2=criteria["criteria_2"],
            criteria_3=criteria["criteria_3"],
            criteria_4=criteria["criteria_4"],
            criteria_5=criteria["criteria_5"],
        )

        try:
            response = self._call_llm(prompt)
            content = response.choices[0].message.content.strip()
            parsed = json.loads(content)

            raw_score = float(parsed["score"])
            explanation = str(parsed.get("explanation", ""))

            # Clamp score to valid range
            score = max(1.0, min(5.0, raw_score))
            return score, explanation

        except json.JSONDecodeError as exc:
            logger.warning(
                "LLM judge returned non-JSON for %s: %s",
                dimension_name,
                exc,
            )
            return 3.0, f"Evaluation unavailable: could not parse LLM response."

        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "LLM judge returned invalid structure for %s: %s",
                dimension_name,
                exc,
            )
            return 3.0, f"Evaluation unavailable: invalid response structure."

        except Exception as exc:
            logger.error(
                "LLM judge error for %s: %s",
                dimension_name,
                exc,
                exc_info=True,
            )
            return 3.0, f"Evaluation unavailable: {type(exc).__name__}."

    def _call_llm(self, prompt: str) -> Any:
        """Make the actual LLM API call.

        Separated for testability — unit tests can mock this method.
        """
        import asyncio
        from kaizen_agents.delegate import Delegate, TextDelta

        delegate = Delegate(
            model=self._model,
            system_prompt=(
                "You are an expert evaluator of HR advisory responses "
                "for Singapore employment law. Respond only with valid JSON."
            ),
            max_turns=1,
        )
        text_parts: list[str] = []

        async def _run() -> None:
            async for event in delegate.run(prompt):
                if isinstance(event, TextDelta):
                    text_parts.append(event.text)

        try:
            asyncio.run(_run())
        except RuntimeError:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(lambda: asyncio.run(_run())).result(timeout=30)

        # Return a minimal response-like object so callers using .choices[0].message.content
        # continue to work without modification.
        class _Msg:
            content = "".join(text_parts)

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        return _Resp()
