"""QueryClarifier -- lightweight pre-classification ambiguity detector.

This agent runs BEFORE QueryAnalyzerAgent.  It only fires when the query
is genuinely ambiguous -- not on every query.  When it does fire it
produces a single targeted clarifying question so the user can refine
their query before we classify and route it.

Uses a fast, cheap LLM call (max_tokens=256, temperature=0.0) because
it sits in the critical path of every request.
"""

import logging
from typing import Any, Optional

from kaizen import Agent as BaseAgent  # kaizen 2.3.1+ canonical import

from hr_advisory.agents.config import QueryClarifierConfig
from hr_advisory.agents.signatures import QueryClarifierSignature
from hr_advisory.agents.specialists._base import _KaizenCompatMixin

logger = logging.getLogger(__name__)

# Domain keywords that indicate the query is already clear enough to route.
# If any of these appear in the query, we almost certainly do not need
# clarification.
_DOMAIN_KEYWORDS = frozenset(
    [
        # Employment Act
        "leave",
        "annual leave",
        "sick leave",
        "mc",
        "medical leave",
        "notice period",
        "termination",
        "dismiss",
        "dismissal",
        "retrenchment",
        "overtime",
        "ot",
        "salary",
        "wages",
        "probation",
        "resign",
        "resignation",
        "contract",
        # CPF
        "cpf",
        "contribution",
        "ordinary wages",
        "additional wages",
        "ow",
        "aw",
        # Foreign manpower
        "work permit",
        "s pass",
        "ep",
        "employment pass",
        "levy",
        "quota",
        "compass",
        "dependency ratio",
        "foreign worker",
        # Fair employment
        "discrimination",
        "tafep",
        "flexible work",
        "fwa",
        "grievance",
        "harassment",
        # Tax
        "ir21",
        "tax clearance",
        "benefits in kind",
        "iras",
        "appendix 8a",
        "appendix 8b",
        # WSH
        "safety",
        "wsh",
        "incident",
        "risk assessment",
        "workplace safety",
        # PDPA
        "pdpa",
        "personal data",
        "data protection",
        "nric",
        "consent",
        "data breach",
        # Compliance
        "compliance",
        "audit",
        "mom inspection",
        "mom",
    ]
)

# Minimum word count below which a query lacking domain keywords is
# likely too terse to classify.
_MIN_WORD_COUNT = 8


class QueryClarifier(_KaizenCompatMixin, BaseAgent):
    """Lightweight agent that detects ambiguous queries before classification.

    Only fires when the query is genuinely ambiguous -- not on every query.
    Uses a fast, cheap LLM call (max_tokens=256, temperature=0.0).
    """

    def __init__(
        self,
        config: Optional[QueryClarifierConfig] = None,
        shared_memory: Any = None,
        **kwargs,
    ):
        import os

        config = config or QueryClarifierConfig()
        model = os.environ.get("OPENAI_PROD_MODEL", os.environ.get("DEFAULT_LLM_MODEL", ""))
        super().__init__(model=model, system_prompt=self._generate_system_prompt())
        self.agent_id = "query_clarifier"
        self.shared_memory = shared_memory
        self._clarifier_config = config

    # ------------------------------------------------------------------
    # Extension points
    # ------------------------------------------------------------------

    def _default_signature(self):
        return QueryClarifierSignature()

    def _generate_system_prompt(self) -> str:
        from hr_advisory.workflows.singlish import SINGLISH_SYSTEM_PROMPT

        base_prompt = (
            "You determine whether a Singapore HR query is too ambiguous to "
            "classify and route to the right specialist agent.\n\n"
            "TASK: Decide if the query needs a clarifying question. Do NOT "
            "answer the HR question itself.\n\n"
            "AMBIGUOUS EXAMPLES (return is_ambiguous=true):\n"
            '  - "my staff wants to leave" -> resign or take leave? AMBIGUOUS\n'
            '  - "can I deduct this from their pay?" -> which deduction type? AMBIGUOUS\n'
            '  - "what are the rules for part-timers?" -> which obligation '
            "(CPF, EA, leave, overtime)? AMBIGUOUS\n"
            '  - "how to handle this?" -> no context at all, AMBIGUOUS\n'
            '  - "what about that policy?" -> pronoun without antecedent, AMBIGUOUS\n\n'
            "CLEAR EXAMPLES (return is_ambiguous=false):\n"
            '  - "can I dismiss someone for misconduct?" -> clear intent\n'
            '  - "how do I calculate overtime for a $2,400 salary?" -> clear\n'
            '  - "what\'s the CPF contribution for a 35-year-old?" -> clear\n'
            '  - "my staff resign already, need pay notice period or not?" -> clear\n'
            '  - "how many days annual leave for new staff?" -> clear\n'
            '  - "can deduct salary for damage or not?" -> clear (EA deduction)\n\n'
            "DECISION CRITERIA:\n"
            "  - Only return is_ambiguous=true when the query genuinely cannot be\n"
            "    routed without more information.\n"
            "  - If conversation_history provides enough context to resolve\n"
            "    pronouns or references, the query is NOT ambiguous.\n"
            "  - Queries with specific domain keywords (CPF, leave, overtime,\n"
            "    termination, etc.) are almost never ambiguous.\n"
            "  - Short queries CAN be clear if they contain domain keywords.\n"
            "  - Singlish phrasing does NOT make a query ambiguous.\n\n"
            "WHEN GENERATING A CLARIFYING QUESTION:\n"
            "  - Ask exactly ONE question.\n"
            "  - Make it specific and answerable in one sentence.\n"
            "  - Phrase it in plain, warm English (not jargon).\n"
            "  - Frame the options so the user can pick without HR knowledge.\n\n"
            "OUTPUT: Respond with a JSON object containing exactly:\n"
            '  "is_ambiguous": "true" or "false",\n'
            '  "clarification_question": "..." (empty string if not ambiguous),\n'
            '  "ambiguity_reason": "..." (empty string if not ambiguous)\n\n'
            "Respond ONLY with valid JSON. No explanation outside the JSON."
        )

        return f"{base_prompt}\n\n{SINGLISH_SYSTEM_PROMPT}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def needs_clarification(
        self,
        query_text: str,
        conversation_history: str = "",
    ) -> bool:
        """Return True only for genuinely ambiguous queries.

        Applies fast heuristic checks first.  Only calls the LLM when
        heuristics are inconclusive.

        Ambiguity heuristics:
        - Queries under 8 words with no domain keyword -> likely ambiguous
        - Queries using pronouns without antecedents (unless
          conversation_history provides context)
        - Queries with multiple possible intents at equal probability

        MUST NOT fire on:
        - Clear domain queries ("What are my CPF obligations?")
        - Questions with salary/leave/amount specifics
        - Company-specific questions with context
        - Follow-up questions in a conversation with clear history
        """
        query_lower = query_text.lower().strip()

        # Fast-path: if the query contains a domain keyword it is almost
        # certainly clear enough to route without clarification.
        if self._has_domain_keyword(query_lower):
            return False

        # Fast-path: if we have conversation history and the query looks
        # like a follow-up ("what about", "and", "also"), let it through
        # because the analyzer can use history for context.
        if conversation_history and self._is_follow_up(query_lower):
            return False

        # Heuristic: very short queries without domain keywords are suspect.
        word_count = len(query_lower.split())
        if word_count < _MIN_WORD_COUNT:
            # Short + no domain keyword -> ask LLM to confirm ambiguity
            return self._llm_check(query_text, conversation_history)

        # For longer queries without domain keywords, defer to LLM.
        return self._llm_check(query_text, conversation_history)

    def generate_question(
        self,
        query_text: str,
        conversation_history: str = "",
    ) -> str:
        """Generate a single targeted clarifying question.

        Returns a plain-language question that helps disambiguate.
        Returns empty string if the LLM determines the query is not
        actually ambiguous on deeper inspection.
        """
        result = self._run_clarifier(query_text, conversation_history)
        return result.get("clarification_question", "")

    def clarify(
        self,
        query_text: str,
        conversation_history: str = "",
    ) -> dict:
        """Full clarification check: returns is_ambiguous, question, and reason.

        Convenience method that combines needs_clarification and
        generate_question into a single LLM call.

        Returns:
            Dict with keys: is_ambiguous (bool), clarification_question (str),
            ambiguity_reason (str).
        """
        query_lower = query_text.lower().strip()

        # Fast-path exits (no LLM call needed)
        if self._has_domain_keyword(query_lower):
            return {
                "is_ambiguous": False,
                "clarification_question": "",
                "ambiguity_reason": "",
            }

        if conversation_history and self._is_follow_up(query_lower):
            return {
                "is_ambiguous": False,
                "clarification_question": "",
                "ambiguity_reason": "",
            }

        # LLM call
        result = self._run_clarifier(query_text, conversation_history)

        is_ambiguous = result.get("is_ambiguous", False)

        self.write_to_memory(
            content={
                "query": query_text,
                "is_ambiguous": is_ambiguous,
                "clarification_question": result.get("clarification_question", ""),
                "ambiguity_reason": result.get("ambiguity_reason", ""),
            },
            tags=["query_clarification"],
            importance=0.7 if is_ambiguous else 0.3,
            segment="query_clarification",
        )

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_domain_keyword(query_lower: str) -> bool:
        """Check if the query contains any known HR domain keyword."""
        for keyword in _DOMAIN_KEYWORDS:
            if keyword in query_lower:
                return True
        return False

    @staticmethod
    def _is_follow_up(query_lower: str) -> bool:
        """Detect queries that look like conversational follow-ups."""
        follow_up_starters = (
            "what about",
            "how about",
            "and ",
            "also ",
            "then ",
            "so ",
            "but ",
            "ok ",
            "okay ",
            "what if",
            "same for",
            "same thing",
        )
        return query_lower.startswith(follow_up_starters)

    def _llm_check(
        self,
        query_text: str,
        conversation_history: str,
    ) -> bool:
        """Call the LLM to assess ambiguity. Returns True if ambiguous."""
        result = self._run_clarifier(query_text, conversation_history)
        return result.get("is_ambiguous", False)

    def _run_clarifier(
        self,
        query_text: str,
        conversation_history: str,
    ) -> dict:
        """Execute the LLM clarification check and parse the result.

        Returns:
            Dict with is_ambiguous (bool), clarification_question (str),
            ambiguity_reason (str).
        """
        try:
            result = self.run(
                query_text=query_text,
                conversation_history=conversation_history or "",
            )

            is_ambiguous_str = self.extract_str(result, "is_ambiguous", default="false")
            clarification_question = self.extract_str(result, "clarification_question", default="")
            ambiguity_reason = self.extract_str(result, "ambiguity_reason", default="")

            is_ambiguous = is_ambiguous_str.lower().strip() == "true"

            return {
                "is_ambiguous": is_ambiguous,
                "clarification_question": clarification_question if is_ambiguous else "",
                "ambiguity_reason": ambiguity_reason if is_ambiguous else "",
            }

        except Exception as exc:
            logger.error(
                "QueryClarifier failed for query: %.100s -- %s",
                query_text,
                exc,
                exc_info=True,
            )
            # On failure, assume the query is clear enough to proceed.
            # Better to attempt classification than to block the user.
            return {
                "is_ambiguous": False,
                "clarification_question": "",
                "ambiguity_reason": "",
            }
