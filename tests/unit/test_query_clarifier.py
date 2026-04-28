"""Unit tests for the QueryClarifier agent.

The QueryClarifier is a lightweight pre-classification stage that detects
ambiguous queries and generates a single targeted clarifying question.

Tier 1 (Unit): Fast, isolated, no external dependencies.
Uses llm_provider="mock" so no real LLM call is made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hr_advisory.agents.config import QueryClarifierConfig
from hr_advisory.agents.orchestration.query_clarifier import (
    QueryClarifier,
    _DOMAIN_KEYWORDS,
    _MIN_WORD_COUNT,
)
from hr_advisory.agents.signatures import QueryClarifierSignature


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def mock_config() -> QueryClarifierConfig:
    """Config that uses the mock provider to avoid real LLM calls."""
    return QueryClarifierConfig(llm_provider="mock", model="mock-model")


@pytest.fixture
def clarifier(mock_config: QueryClarifierConfig) -> QueryClarifier:
    """A QueryClarifier instance wired to the mock provider."""
    return QueryClarifier(config=mock_config)


# ------------------------------------------------------------------
# Initialization and structure
# ------------------------------------------------------------------


class TestInitialization:
    """Verify that the QueryClarifier initializes correctly."""

    def test_import_and_instantiate(self, clarifier: QueryClarifier):
        assert clarifier is not None

    def test_agent_id(self, clarifier: QueryClarifier):
        assert clarifier.agent_id == "query_clarifier"

    def test_signature_type(self, clarifier: QueryClarifier):
        sig = clarifier._default_signature()
        assert isinstance(sig, QueryClarifierSignature)

    def test_config_defaults(self):
        config = QueryClarifierConfig(llm_provider="mock", model="mock-model")
        assert config.temperature == 0.0
        assert config.max_tokens == 256

    def test_system_prompt_generated(self, clarifier: QueryClarifier):
        prompt = clarifier._generate_system_prompt()
        assert "ambiguous" in prompt.lower()
        assert "is_ambiguous" in prompt
        assert "clarification_question" in prompt
        assert "Singlish" in prompt


# ------------------------------------------------------------------
# Signature
# ------------------------------------------------------------------


class TestSignature:
    """Verify the QueryClarifierSignature fields."""

    def test_input_fields(self):
        sig = QueryClarifierSignature()
        field_names = list(sig.input_fields.keys())
        assert "query_text" in field_names
        assert "conversation_history" in field_names

    def test_output_fields(self):
        sig = QueryClarifierSignature()
        field_names = list(sig.output_fields.keys())
        assert "is_ambiguous" in field_names
        assert "clarification_question" in field_names
        assert "ambiguity_reason" in field_names


# ------------------------------------------------------------------
# Domain keyword heuristic (no LLM call)
# ------------------------------------------------------------------


class TestDomainKeywordHeuristic:
    """Queries with domain keywords should fast-path to 'not ambiguous'."""

    @pytest.mark.parametrize(
        "query",
        [
            "What are my CPF obligations?",
            "How to calculate overtime for a $2,400 salary?",
            "Can I dismiss someone for misconduct?",
            "How many days annual leave for new staff?",
            "What is the notice period for termination?",
            "My staff resign already, need pay notice period or not?",
            "Can deduct salary for damage or not?",
            "What's the levy for foreign worker?",
            "PDPA consent requirements for employee data",
            "WSH risk assessment requirements",
            "MOM inspection coming, what need prepare?",
        ],
    )
    def test_clear_domain_queries_not_ambiguous(self, clarifier: QueryClarifier, query: str):
        """Queries with clear domain keywords should not need clarification.

        These use the fast heuristic path -- no LLM call at all.
        """
        result = clarifier.needs_clarification(query)
        assert result is False

    def test_has_domain_keyword_static_method(self):
        assert QueryClarifier._has_domain_keyword("what about cpf rates") is True
        assert QueryClarifier._has_domain_keyword("hello world") is False
        assert QueryClarifier._has_domain_keyword("annual leave question") is True

    def test_domain_keywords_set_nonempty(self):
        assert len(_DOMAIN_KEYWORDS) > 20  # sanity: substantial keyword list

    def test_min_word_count_is_eight(self):
        assert _MIN_WORD_COUNT == 8


# ------------------------------------------------------------------
# Follow-up heuristic (no LLM call)
# ------------------------------------------------------------------


class TestFollowUpHeuristic:
    """Follow-up queries with conversation history should fast-path out."""

    @pytest.mark.parametrize(
        "query",
        [
            "what about part-timers?",
            "how about for S Pass holders?",
            "and if they are above 55?",
            "also for foreign workers?",
            "then what happens next?",
            "so I need to file that?",
            "but can I appeal?",
            "same for contract staff?",
        ],
    )
    def test_follow_ups_with_history_not_ambiguous(self, clarifier: QueryClarifier, query: str):
        history = "User: What are the CPF rates?\nAssistant: The CPF rates are..."
        result = clarifier.needs_clarification(query, conversation_history=history)
        assert result is False

    def test_follow_up_without_history_may_trigger_llm(self, clarifier: QueryClarifier):
        """Without history, a follow-up-style query might still need LLM check."""
        # "what about them?" has no domain keyword and no history
        # It would fall through to _llm_check.  With mock provider it
        # returns False by default (error path returns not-ambiguous).
        result = clarifier.needs_clarification("what about them?")
        # We just verify it returns a bool, not crash
        assert isinstance(result, bool)


# ------------------------------------------------------------------
# needs_clarification return type
# ------------------------------------------------------------------


class TestNeedsClarificationReturnType:
    """Verify that needs_clarification always returns a bool."""

    def test_returns_bool_for_clear_query(self, clarifier: QueryClarifier):
        result = clarifier.needs_clarification("What is my CPF contribution?")
        assert isinstance(result, bool)
        assert result is False

    def test_returns_bool_for_short_query(self, clarifier: QueryClarifier):
        result = clarifier.needs_clarification("help me")
        assert isinstance(result, bool)

    def test_returns_bool_with_history(self, clarifier: QueryClarifier):
        result = clarifier.needs_clarification(
            "what about that?",
            conversation_history="User: CPF rates?\nAssistant: Here are the rates...",
        )
        assert isinstance(result, bool)


# ------------------------------------------------------------------
# generate_question return type
# ------------------------------------------------------------------


class TestGenerateQuestion:
    """Verify that generate_question always returns a string."""

    def test_returns_string(self, clarifier: QueryClarifier):
        result = clarifier.generate_question("help me")
        assert isinstance(result, str)

    def test_returns_string_for_clear_query(self, clarifier: QueryClarifier):
        # Even for clear queries, the method goes through the LLM path.
        # With mock provider it returns empty string (default).
        result = clarifier.generate_question("What is my CPF?")
        assert isinstance(result, str)


# ------------------------------------------------------------------
# clarify() combined method
# ------------------------------------------------------------------


class TestClarifyMethod:
    """Verify the combined clarify() convenience method."""

    def test_clear_query_returns_not_ambiguous(self, clarifier: QueryClarifier):
        result = clarifier.clarify("What is the CPF contribution rate?")
        assert result["is_ambiguous"] is False
        assert result["clarification_question"] == ""
        assert result["ambiguity_reason"] == ""

    def test_follow_up_with_history_returns_not_ambiguous(self, clarifier: QueryClarifier):
        result = clarifier.clarify(
            "what about them?",
            conversation_history="User: CPF rules for PRs?\nAssistant: The rules are...",
        )
        assert result["is_ambiguous"] is False

    def test_result_has_required_keys(self, clarifier: QueryClarifier):
        result = clarifier.clarify("some unclear thing")
        assert "is_ambiguous" in result
        assert "clarification_question" in result
        assert "ambiguity_reason" in result

    def test_is_ambiguous_is_bool(self, clarifier: QueryClarifier):
        result = clarifier.clarify("What is CPF?")
        assert isinstance(result["is_ambiguous"], bool)


# ------------------------------------------------------------------
# Conversation history reduces ambiguity
# ------------------------------------------------------------------


class TestConversationHistoryContext:
    """Conversation history should help resolve otherwise ambiguous queries."""

    def test_pronoun_with_history_resolved_via_follow_up(self, clarifier: QueryClarifier):
        """'what about that?' is a follow-up -- with history it fast-paths."""
        history = (
            "User: What are the rules for terminating an employee?\n"
            "Assistant: Under the Employment Act, employers must give notice..."
        )
        result = clarifier.needs_clarification(
            "what about that for contract staff?",
            conversation_history=history,
        )
        assert result is False

    def test_domain_keyword_overrides_short_query(self, clarifier: QueryClarifier):
        """Even a 3-word query is clear if it has a domain keyword."""
        result = clarifier.needs_clarification("CPF rates?")
        assert result is False


# ------------------------------------------------------------------
# LLM call with mocked run()
# ------------------------------------------------------------------


class TestLLMPathWithMockedRun:
    """Test the LLM-dependent code path by mocking self.run()."""

    def test_ambiguous_query_detected(self, clarifier: QueryClarifier):
        """When the LLM says ambiguous, needs_clarification returns True.

        Uses a query without domain keywords so heuristics do not fast-path.
        """
        fake_result = {
            "is_ambiguous": "true",
            "clarification_question": "Could you tell me more about what you need help with?",
            "ambiguity_reason": "Query is too vague to determine the regulatory domain",
        }
        with patch.object(clarifier, "run", return_value=fake_result):
            with patch.object(
                clarifier, "extract_str", side_effect=lambda r, k, default="": r.get(k, default)
            ):
                result = clarifier.needs_clarification("what should I do about this?")
                assert result is True

    def test_clear_query_via_llm(self, clarifier: QueryClarifier):
        """When the LLM says not ambiguous, needs_clarification returns False."""
        fake_result = {
            "is_ambiguous": "false",
            "clarification_question": "",
            "ambiguity_reason": "",
        }
        with patch.object(clarifier, "run", return_value=fake_result):
            with patch.object(
                clarifier, "extract_str", side_effect=lambda r, k, default="": r.get(k, default)
            ):
                result = clarifier.needs_clarification("how to handle this?")
                assert result is False

    def test_generate_question_returns_llm_question(self, clarifier: QueryClarifier):
        fake_result = {
            "is_ambiguous": "true",
            "clarification_question": "Which deduction are you asking about?",
            "ambiguity_reason": "Multiple deduction types exist",
        }
        with patch.object(clarifier, "run", return_value=fake_result):
            with patch.object(
                clarifier, "extract_str", side_effect=lambda r, k, default="": r.get(k, default)
            ):
                question = clarifier.generate_question("can I deduct this from their pay?")
                assert "deduction" in question.lower()

    def test_clarify_full_result_ambiguous(self, clarifier: QueryClarifier):
        fake_result = {
            "is_ambiguous": "true",
            "clarification_question": "Which obligation are you asking about -- CPF, leave, or overtime?",
            "ambiguity_reason": "Multiple obligations apply to part-timers",
        }
        with patch.object(clarifier, "run", return_value=fake_result):
            with patch.object(
                clarifier, "extract_str", side_effect=lambda r, k, default="": r.get(k, default)
            ):
                result = clarifier.clarify("what are the rules for part-timers?")
                assert result["is_ambiguous"] is True
                assert len(result["clarification_question"]) > 0
                assert len(result["ambiguity_reason"]) > 0


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------


class TestErrorHandling:
    """When the LLM call fails, the clarifier should fail open."""

    def test_llm_failure_returns_not_ambiguous(self, clarifier: QueryClarifier):
        """On LLM error, assume query is clear -- fail open, not closed."""
        with patch.object(clarifier, "run", side_effect=RuntimeError("LLM down")):
            result = clarifier.needs_clarification("something vague")
            assert result is False

    def test_llm_failure_clarify_returns_not_ambiguous(self, clarifier: QueryClarifier):
        with patch.object(clarifier, "run", side_effect=RuntimeError("LLM down")):
            result = clarifier.clarify("something vague")
            assert result["is_ambiguous"] is False
            assert result["clarification_question"] == ""

    def test_generate_question_on_failure_returns_empty(self, clarifier: QueryClarifier):
        with patch.object(clarifier, "run", side_effect=RuntimeError("LLM down")):
            question = clarifier.generate_question("something vague")
            assert question == ""


# ------------------------------------------------------------------
# Export from orchestration package
# ------------------------------------------------------------------


class TestPackageExport:
    """QueryClarifier is intentionally NOT exported from the orchestration package
    after the AdvisoryEngine overhaul (commit 4b3d4c6) — it belongs to the old
    Kaizen pipeline kept for reference only."""

    def test_not_exported_from_orchestration(self):
        """The old Kaizen QueryClarifier must not appear in the public API."""
        from hr_advisory.agents.orchestration import __all__

        assert "QueryClarifier" not in __all__
