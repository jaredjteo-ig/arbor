"""Unit tests for the quality rubric scoring system.

Tests automated checks (citation quality, risk awareness, response structure,
disclaimer presence), RubricResult calculation, and LLM judge integration.

TDD: These tests are written FIRST. Implementation follows.
"""

from __future__ import annotations

import pytest

from hr_advisory.quality.rubric import QualityRubric, RubricResult
from hr_advisory.quality.automated_checks import AutomatedChecks


# ---------------------------------------------------------------------------
# Fixtures: well-formed and malformed advisory responses
# ---------------------------------------------------------------------------

GOOD_GREEN_RESPONSE = {
    "response_text": (
        "## Summary\n"
        "All employees covered by the Employment Act are entitled to paid "
        "annual leave based on years of service.\n\n"
        "## What the law says\n"
        "Under the Employment Act Part X [EA-PART-X-annual-leave], employees "
        "in their first year of service are entitled to a minimum of 7 days "
        "of annual leave [EA-S95-KETs]. Entitlement increases by 1 day per "
        "year of service up to a maximum of 14 days [EA-KET].\n\n"
        "## What you need to do\n"
        "1. Review your employee's years of service.\n"
        "2. Ensure the employment contract specifies at least the statutory minimum.\n"
        "3. Track leave balances and pro-rate for incomplete years.\n"
    ),
    "risk_tier": "green",
    "cited_provisions": ["EA-PART-X-annual-leave", "EA-S95-KETs", "EA-KET"],
    "confidence": 0.92,
    "domains": ["employment_act"],
}

GOOD_RED_RESPONSE = {
    "response_text": (
        "## Summary\n"
        "A workplace injury requires immediate action including medical "
        "attention, statutory reporting, and WICA compliance.\n\n"
        "## Legal basis\n"
        "Under the WSH Act [WSHA-S12] employers have a duty of care. "
        "Workplace injuries must be reported via iReport within 10 days "
        "[WSH-incident-reporting]. The employer must also comply with WICA "
        "obligations [WICA-employer-obligations].\n\n"
        "## Action steps\n"
        "1. Ensure the employee receives immediate medical attention.\n"
        "2. Report the incident via MOM iReport within 10 days.\n"
        "3. File a WICA claim if applicable.\n"
        "4. We strongly recommend you consult an employment law specialist "
        "given the legal complexity and potential liability.\n\n"
        "## Important\n"
        "This situation involves significant legal or financial implications. "
        "The guidance below is based on current regulations, but given the "
        "complexity, we strongly recommend consulting an employment law "
        "specialist before taking action.\n"
    ),
    "risk_tier": "red",
    "cited_provisions": ["WSHA-S12", "WSH-incident-reporting", "WICA-employer-obligations"],
    "confidence": 0.85,
    "domains": ["wsh"],
}

GOOD_AMBER_RESPONSE = {
    "response_text": (
        "## Summary\n"
        "Dismissal for misconduct requires following due inquiry procedures.\n\n"
        "## What the law says\n"
        "Under EA s14 [EA-S14-misconduct-dismissal], an employer may dismiss "
        "an employee without notice for misconduct, but only after conducting "
        "a due inquiry. The Tripartite Guidelines [TGFEP-fair-dismissal] "
        "set out best practices for fair dismissal procedures.\n\n"
        "## What you need to do\n"
        "1. Conduct a formal inquiry before making any dismissal decision.\n"
        "2. Document all evidence and give the employee an opportunity to respond.\n"
        "3. Keep records of the entire process.\n\n"
        "Based on current Employment Act provisions...\n"
    ),
    "risk_tier": "amber",
    "cited_provisions": ["EA-S14-misconduct-dismissal", "TGFEP-fair-dismissal"],
    "confidence": 0.80,
    "domains": ["employment_act"],
}

NO_CITATIONS_RESPONSE = {
    "response_text": (
        "You should give your employee some leave. The amount depends on how "
        "long they have worked for you."
    ),
    "risk_tier": "green",
    "cited_provisions": [],
    "confidence": 0.70,
    "domains": ["employment_act"],
}

NO_STRUCTURE_RESPONSE = {
    "response_text": (
        "Yes, you need to pay overtime. The rate is 1.5 times. "
        "Check the Employment Act for details."
    ),
    "risk_tier": "green",
    "cited_provisions": ["EA-PART-IV-hours"],
    "confidence": 0.75,
    "domains": ["employment_act"],
}

RED_MISSING_CONSULT_RESPONSE = {
    "response_text": (
        "## Summary\n"
        "A workplace injury happened. Just file the report and move on.\n\n"
        "## What the law says\n"
        "Under WSH Act [WSHA-S12], you have obligations.\n\n"
        "## What you need to do\n"
        "1. File the report.\n"
        "2. Nothing else to worry about.\n"
    ),
    "risk_tier": "red",
    "cited_provisions": ["WSHA-S12"],
    "confidence": 0.60,
    "domains": ["wsh"],
}

AMBER_SAYS_NO_WORRIES_RESPONSE = {
    "response_text": (
        "## Summary\n"
        "Misconduct dismissal is straightforward — no action needed really.\n\n"
        "## What the law says\n"
        "Under EA s14 [EA-S14-misconduct-dismissal], dismissal for misconduct "
        "is allowed.\n\n"
        "## What you need to do\n"
        "There is nothing to worry about. Just dismiss the employee.\n\n"
        "Based on current Employment Act provisions...\n"
    ),
    "risk_tier": "amber",
    "cited_provisions": ["EA-S14-misconduct-dismissal"],
    "confidence": 0.70,
    "domains": ["employment_act"],
}

GREEN_WITH_URGENT_RESPONSE = {
    "response_text": (
        "## Summary\n"
        "Annual leave is straightforward. URGENT: immediate action required!\n\n"
        "## What the law says\n"
        "Under EA Part X [EA-PART-X-annual-leave], minimum 7 days first year "
        "[EA-S95-KETs] [EA-KET].\n\n"
        "## What you need to do\n"
        "1. Check your employee's years of service.\n"
    ),
    "risk_tier": "green",
    "cited_provisions": ["EA-PART-X-annual-leave", "EA-S95-KETs", "EA-KET"],
    "confidence": 0.85,
    "domains": ["employment_act"],
}

RED_NO_DISCLAIMER_RESPONSE = {
    "response_text": (
        "## Summary\n"
        "The employee filed a TAFEP complaint.\n\n"
        "## Legal basis\n"
        "Under TGFEP [TGFEP-fair-employment] [TAFEP-complaint-process], "
        "you must cooperate. We strongly recommend you consult an employment "
        "law specialist.\n\n"
        "## Action steps\n"
        "1. Do not retaliate.\n"
        "2. Cooperate with the investigation.\n"
    ),
    "risk_tier": "red",
    "cited_provisions": ["TGFEP-fair-employment", "TAFEP-complaint-process"],
    "confidence": 0.75,
    "domains": ["fair_employment"],
}


# ===================================================================
# Test: RubricResult dataclass
# ===================================================================


class TestRubricResult:
    """Test RubricResult calculation and properties."""

    def test_overall_score_is_minimum(self) -> None:
        """Overall score must be the minimum across all dimensions."""
        result = RubricResult(
            dimension_scores={
                "legal_accuracy": 5.0,
                "contextual_relevance": 4.0,
                "conversational_coherence": 3.0,
                "actionability": 5.0,
                "risk_awareness": 2.0,
                "citation_quality": 4.0,
                "language_understanding": 5.0,
                "completeness": 4.0,
            },
            details={},
        )
        assert result.overall_score == 2.0

    def test_passed_when_all_above_threshold(self) -> None:
        """Passed should be True when overall_score >= 3.0."""
        result = RubricResult(
            dimension_scores={
                "legal_accuracy": 4.0,
                "contextual_relevance": 3.0,
                "conversational_coherence": 5.0,
                "actionability": 4.0,
                "risk_awareness": 3.0,
                "citation_quality": 3.0,
                "language_understanding": 5.0,
                "completeness": 4.0,
            },
            details={},
        )
        assert result.passed is True
        assert result.overall_score == 3.0

    def test_failed_when_any_below_threshold(self) -> None:
        """Passed should be False when any dimension < 3.0."""
        result = RubricResult(
            dimension_scores={
                "legal_accuracy": 5.0,
                "contextual_relevance": 5.0,
                "conversational_coherence": 5.0,
                "actionability": 5.0,
                "risk_awareness": 2.0,
                "citation_quality": 5.0,
                "language_understanding": 5.0,
                "completeness": 5.0,
            },
            details={},
        )
        assert result.passed is False

    def test_dimension_flags_lists_failing_dimensions(self) -> None:
        """dimension_flags should list every dimension scoring below 3.0."""
        result = RubricResult(
            dimension_scores={
                "legal_accuracy": 2.0,
                "contextual_relevance": 5.0,
                "conversational_coherence": 5.0,
                "actionability": 1.0,
                "risk_awareness": 5.0,
                "citation_quality": 5.0,
                "language_understanding": 5.0,
                "completeness": 5.0,
            },
            details={},
        )
        assert "legal_accuracy" in result.dimension_flags
        assert "actionability" in result.dimension_flags
        assert len(result.dimension_flags) == 2

    def test_no_flags_when_all_pass(self) -> None:
        """dimension_flags should be empty when all dimensions >= 3.0."""
        result = RubricResult(
            dimension_scores={
                "legal_accuracy": 3.0,
                "contextual_relevance": 4.0,
                "conversational_coherence": 3.0,
                "actionability": 5.0,
                "risk_awareness": 3.0,
                "citation_quality": 4.0,
                "language_understanding": 3.0,
                "completeness": 3.0,
            },
            details={},
        )
        assert result.dimension_flags == []

    def test_requires_all_eight_dimensions(self) -> None:
        """RubricResult must raise ValueError if not all 8 dimensions are present."""
        with pytest.raises(ValueError, match="exactly 8 dimensions"):
            RubricResult(
                dimension_scores={
                    "legal_accuracy": 5.0,
                    "citation_quality": 5.0,
                },
                details={},
            )

    def test_rejects_unknown_dimension(self) -> None:
        """RubricResult must reject scores with unknown dimension keys."""
        with pytest.raises(ValueError, match="Unknown dimension"):
            RubricResult(
                dimension_scores={
                    "legal_accuracy": 5.0,
                    "contextual_relevance": 5.0,
                    "conversational_coherence": 5.0,
                    "actionability": 5.0,
                    "risk_awareness": 5.0,
                    "citation_quality": 5.0,
                    "language_understanding": 5.0,
                    "unknown_dimension": 5.0,
                },
                details={},
            )

    def test_rejects_score_out_of_range(self) -> None:
        """Scores must be between 1.0 and 5.0 inclusive."""
        with pytest.raises(ValueError, match="between 1.0 and 5.0"):
            RubricResult(
                dimension_scores={
                    "legal_accuracy": 0.0,
                    "contextual_relevance": 5.0,
                    "conversational_coherence": 5.0,
                    "actionability": 5.0,
                    "risk_awareness": 5.0,
                    "citation_quality": 5.0,
                    "language_understanding": 5.0,
                    "completeness": 5.0,
                },
                details={},
            )

        with pytest.raises(ValueError, match="between 1.0 and 5.0"):
            RubricResult(
                dimension_scores={
                    "legal_accuracy": 6.0,
                    "contextual_relevance": 5.0,
                    "conversational_coherence": 5.0,
                    "actionability": 5.0,
                    "risk_awareness": 5.0,
                    "citation_quality": 5.0,
                    "language_understanding": 5.0,
                    "completeness": 5.0,
                },
                details={},
            )


# ===================================================================
# Test: Automated Checks — Citation Quality
# ===================================================================


class TestCitationQualityCheck:
    """Test automated citation quality scoring."""

    def test_three_plus_citations_scores_5(self) -> None:
        """3 or more properly formatted citations should score 5."""
        score, explanation = AutomatedChecks.check_citation_quality(
            response_text="Under [EA-S10] and [TGFEP-fair-dismissal] and [EA-S14-misconduct]...",
            cited_provisions=["EA-S10-notice", "TGFEP-fair-dismissal", "EA-S14-misconduct-dismissal"],
        )
        assert score == 5.0
        assert explanation

    def test_two_citations_scores_4(self) -> None:
        """2 citations should score 4."""
        score, explanation = AutomatedChecks.check_citation_quality(
            response_text="Under [EA-S10] and [TGFEP-fair-dismissal]...",
            cited_provisions=["EA-S10-notice", "TGFEP-fair-dismissal"],
        )
        assert score == 4.0

    def test_one_citation_scores_3(self) -> None:
        """1 citation should score 3."""
        score, explanation = AutomatedChecks.check_citation_quality(
            response_text="Under [EA-S10-notice]...",
            cited_provisions=["EA-S10-notice"],
        )
        assert score == 3.0

    def test_no_citations_scores_1(self) -> None:
        """0 citations should score 1."""
        score, explanation = AutomatedChecks.check_citation_quality(
            response_text="Just give them leave.",
            cited_provisions=[],
        )
        assert score == 1.0
        assert "no citation" in explanation.lower() or "0 citation" in explanation.lower()

    def test_citations_in_response_text_counted(self) -> None:
        """Citations with bracket format [X] in the text should be counted."""
        score, _ = AutomatedChecks.check_citation_quality(
            response_text=(
                "As per [EA-PART-X-annual-leave], employees get leave. "
                "Also see [EA-S95-KETs] and [EA-KET]."
            ),
            cited_provisions=["EA-PART-X-annual-leave", "EA-S95-KETs", "EA-KET"],
        )
        assert score == 5.0


# ===================================================================
# Test: Automated Checks — Risk Awareness
# ===================================================================


class TestRiskAwarenessCheck:
    """Test automated risk tier consistency checking."""

    def test_green_consistent_scores_5(self) -> None:
        """A green response with no alarming language should score 5."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text="Annual leave entitlement is straightforward. 7 days minimum.",
            risk_tier="green",
        )
        assert score == 5.0

    def test_red_with_consult_scores_5(self) -> None:
        """A red response that recommends consulting a professional should score 5."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text=(
                "This is a complex situation. We strongly recommend you consult "
                "an employment law specialist before taking action."
            ),
            risk_tier="red",
        )
        assert score == 5.0

    def test_red_with_seek_professional_advice_scores_5(self) -> None:
        """A red response with 'seek professional advice' language should score 5."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text="Given the risks, please seek professional advice immediately.",
            risk_tier="red",
        )
        assert score == 5.0

    def test_red_without_consult_scores_lower(self) -> None:
        """A red response without consult/professional language should score lower."""
        score, explanation = AutomatedChecks.check_risk_awareness(
            response_text="Just file the report and handle it internally.",
            risk_tier="red",
        )
        assert score <= 3.0
        assert "consult" in explanation.lower() or "professional" in explanation.lower()

    def test_amber_with_no_action_needed_scores_lower(self) -> None:
        """An amber response saying 'no action needed' should score lower."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text="This is an amber risk matter. No action needed at this stage.",
            risk_tier="amber",
        )
        assert score <= 3.0

    def test_amber_with_nothing_to_worry_about_scores_lower(self) -> None:
        """An amber response saying 'nothing to worry about' should score lower."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text="There is nothing to worry about in this situation.",
            risk_tier="amber",
        )
        assert score <= 3.0

    def test_green_with_urgent_scores_lower(self) -> None:
        """A green response with 'urgent' or 'immediate action required' should score lower."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text="URGENT: immediate action required for this annual leave question!",
            risk_tier="green",
        )
        assert score <= 3.0

    def test_green_with_immediate_action_required_scores_lower(self) -> None:
        """A green response with 'immediate action required' should score lower."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text="You need to take immediate action required to address leave balance.",
            risk_tier="green",
        )
        assert score <= 3.0

    def test_multiple_failures_score_1(self) -> None:
        """Multiple risk consistency failures should score 1."""
        score, _ = AutomatedChecks.check_risk_awareness(
            response_text="Nothing to worry about. No action needed here.",
            risk_tier="amber",
        )
        assert score == 1.0


# ===================================================================
# Test: Automated Checks — Response Structure
# ===================================================================


class TestResponseStructureCheck:
    """Test automated response structure scoring."""

    def test_all_sections_present_scores_5(self) -> None:
        """Response with Summary, Legal basis, and Action steps scores 5."""
        score, _ = AutomatedChecks.check_response_structure(
            "## Summary\nLeave info.\n\n"
            "## What the law says\nEA Part X.\n\n"
            "## What you need to do\n1. Check entitlement.\n"
        )
        assert score == 5.0

    def test_alternative_section_names_accepted(self) -> None:
        """Alternative section names (Legal basis, Action steps) should also score well."""
        score, _ = AutomatedChecks.check_response_structure(
            "## Summary\nOverview.\n\n"
            "## Legal basis\nLaw here.\n\n"
            "## Action steps\n1. Do X.\n"
        )
        assert score == 5.0

    def test_two_of_three_sections_scores_4(self) -> None:
        """Response with 2 of 3 key sections should score 4."""
        score, _ = AutomatedChecks.check_response_structure(
            "## Summary\nOverview.\n\n"
            "## What the law says\nLaw here.\n"
        )
        assert score == 4.0

    def test_one_of_three_sections_scores_3(self) -> None:
        """Response with 1 of 3 key sections should score 3."""
        score, _ = AutomatedChecks.check_response_structure(
            "## Summary\nBrief overview of the situation.\n"
        )
        assert score == 3.0

    def test_no_sections_scores_1(self) -> None:
        """Response with no key sections should score 1."""
        score, explanation = AutomatedChecks.check_response_structure(
            "Just do what you need to do, it's fine."
        )
        assert score == 1.0
        assert "section" in explanation.lower() or "structure" in explanation.lower()


# ===================================================================
# Test: Automated Checks — Disclaimer Presence
# ===================================================================


class TestDisclaimerPresenceCheck:
    """Test automated disclaimer presence checking."""

    def test_red_with_appropriate_disclaimer_scores_5(self) -> None:
        """Red response with professional referral disclaimer scores 5."""
        score, _ = AutomatedChecks.check_disclaimer_presence(
            response_text=(
                "Answer here.\n\n"
                "This situation involves significant legal or financial implications. "
                "We strongly recommend consulting an employment law specialist "
                "before taking action."
            ),
            risk_tier="red",
        )
        assert score == 5.0

    def test_red_with_generic_disclaimer_scores_3(self) -> None:
        """Red response with only a generic disclaimer scores 3."""
        score, _ = AutomatedChecks.check_disclaimer_presence(
            response_text=(
                "Answer here.\n\n"
                "This is general information only and not legal advice."
            ),
            risk_tier="red",
        )
        assert score == 3.0

    def test_red_without_disclaimer_scores_1(self) -> None:
        """Red response with no disclaimer at all scores 1."""
        score, explanation = AutomatedChecks.check_disclaimer_presence(
            response_text="Just handle the workplace injury internally.",
            risk_tier="red",
        )
        assert score == 1.0
        assert "disclaimer" in explanation.lower()

    def test_green_without_disclaimer_scores_5(self) -> None:
        """Green response does not require a disclaimer — scores 5."""
        score, _ = AutomatedChecks.check_disclaimer_presence(
            response_text="Annual leave is 7 days minimum in the first year.",
            risk_tier="green",
        )
        assert score == 5.0

    def test_amber_with_framing_scores_5(self) -> None:
        """Amber response with domain framing text scores 5."""
        score, _ = AutomatedChecks.check_disclaimer_presence(
            response_text=(
                "Answer here.\n\n"
                "Based on current Employment Act provisions..."
            ),
            risk_tier="amber",
        )
        assert score == 5.0

    def test_amber_without_any_framing_scores_1(self) -> None:
        """Amber response with no framing or disclaimer scores 1."""
        score, _ = AutomatedChecks.check_disclaimer_presence(
            response_text="Just dismiss the employee for misconduct.",
            risk_tier="amber",
        )
        assert score == 1.0


# ===================================================================
# Test: AutomatedChecks.run_all — composite scoring
# ===================================================================


class TestAutomatedChecksRunAll:
    """Test the composite run_all method returns all expected keys."""

    def test_run_all_returns_four_dimensions(self) -> None:
        """run_all should return scores for all 4 automated dimensions."""
        scores, details = AutomatedChecks.run_all(
            response_text=GOOD_GREEN_RESPONSE["response_text"],
            risk_tier=GOOD_GREEN_RESPONSE["risk_tier"],
            cited_provisions=GOOD_GREEN_RESPONSE["cited_provisions"],
        )
        assert "citation_quality" in scores
        assert "risk_awareness" in scores
        assert "response_structure" in scores
        assert "disclaimer_presence" in scores
        assert len(scores) == 4
        # All scores must be between 1 and 5
        for key, val in scores.items():
            assert 1.0 <= val <= 5.0, f"{key} score {val} out of range"

    def test_good_response_scores_high(self) -> None:
        """A well-formed response should score well across automated checks."""
        scores, _ = AutomatedChecks.run_all(
            response_text=GOOD_GREEN_RESPONSE["response_text"],
            risk_tier=GOOD_GREEN_RESPONSE["risk_tier"],
            cited_provisions=GOOD_GREEN_RESPONSE["cited_provisions"],
        )
        for key, val in scores.items():
            assert val >= 4.0, f"Expected {key} >= 4.0, got {val}"

    def test_bad_response_scores_low(self) -> None:
        """A response with no citations and no structure should score low."""
        scores, _ = AutomatedChecks.run_all(
            response_text=NO_CITATIONS_RESPONSE["response_text"],
            risk_tier=NO_CITATIONS_RESPONSE["risk_tier"],
            cited_provisions=NO_CITATIONS_RESPONSE["cited_provisions"],
        )
        assert scores["citation_quality"] == 1.0

    def test_red_response_without_consult_flags_risk(self) -> None:
        """A red-tier response missing 'consult' language should flag risk_awareness."""
        scores, _ = AutomatedChecks.run_all(
            response_text=RED_MISSING_CONSULT_RESPONSE["response_text"],
            risk_tier=RED_MISSING_CONSULT_RESPONSE["risk_tier"],
            cited_provisions=RED_MISSING_CONSULT_RESPONSE["cited_provisions"],
        )
        assert scores["risk_awareness"] <= 3.0


# ===================================================================
# Test: LLM Judge (unit-level, mocked)
# ===================================================================


class TestLLMJudge:
    """Test the LLMJudge class behavior (LLM calls mocked for unit tests)."""

    def test_judge_returns_score_and_explanation(self) -> None:
        """LLMJudge.evaluate should return (score, explanation) tuple."""
        from unittest.mock import patch, MagicMock
        from hr_advisory.quality.llm_judge import LLMJudge

        judge = LLMJudge()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"score": 4, "explanation": "Good coverage."}'))
        ]

        with patch.object(judge, "_call_llm", return_value=mock_response):
            score, explanation = judge.evaluate(
                dimension_name="legal_accuracy",
                query="How much annual leave?",
                response_text="Under EA Part X...",
                context={},
                risk_tier="green",
                citations=["EA-PART-X-annual-leave"],
            )
        assert score == 4.0
        assert explanation == "Good coverage."

    def test_judge_handles_llm_error_gracefully(self) -> None:
        """On LLM failure, judge should return score 3 with explanation."""
        from unittest.mock import patch
        from hr_advisory.quality.llm_judge import LLMJudge

        judge = LLMJudge()

        with patch.object(judge, "_call_llm", side_effect=Exception("API down")):
            score, explanation = judge.evaluate(
                dimension_name="legal_accuracy",
                query="How much annual leave?",
                response_text="Under EA Part X...",
                context={},
                risk_tier="green",
                citations=[],
            )
        assert score == 3.0
        assert "unavailable" in explanation.lower() or "error" in explanation.lower()

    def test_judge_handles_malformed_json_gracefully(self) -> None:
        """On malformed LLM JSON response, judge should return score 3."""
        from unittest.mock import patch, MagicMock
        from hr_advisory.quality.llm_judge import LLMJudge

        judge = LLMJudge()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This is not valid JSON"))
        ]

        with patch.object(judge, "_call_llm", return_value=mock_response):
            score, explanation = judge.evaluate(
                dimension_name="legal_accuracy",
                query="test query",
                response_text="test response",
                context={},
                risk_tier="green",
                citations=[],
            )
        assert score == 3.0
        assert "unavailable" in explanation.lower() or "parse" in explanation.lower()

    def test_judge_clamps_score_to_valid_range(self) -> None:
        """Scores outside 1-5 should be clamped to valid range."""
        from unittest.mock import patch, MagicMock
        from hr_advisory.quality.llm_judge import LLMJudge

        judge = LLMJudge()

        # Score above 5
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"score": 10, "explanation": "Perfect"}'))
        ]

        with patch.object(judge, "_call_llm", return_value=mock_response):
            score, _ = judge.evaluate(
                dimension_name="legal_accuracy",
                query="test",
                response_text="test",
                context={},
                risk_tier="green",
                citations=[],
            )
        assert score == 5.0

        # Score below 1
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"score": -1, "explanation": "Terrible"}'))
        ]

        with patch.object(judge, "_call_llm", return_value=mock_response):
            score, _ = judge.evaluate(
                dimension_name="legal_accuracy",
                query="test",
                response_text="test",
                context={},
                risk_tier="green",
                citations=[],
            )
        assert score == 1.0


# ===================================================================
# Test: QualityRubric.score (with mocked LLM)
# ===================================================================


class TestQualityRubricScore:
    """Test the full rubric scoring pipeline with mocked LLM judge."""

    def _make_rubric_with_mock_judge(self, judge_score: float = 4.0):
        """Create a QualityRubric with a mocked LLM judge returning a fixed score."""
        from unittest.mock import MagicMock
        rubric = QualityRubric()
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = (judge_score, f"Mocked: score {judge_score}")
        rubric._llm_judge = mock_judge
        return rubric

    def test_score_returns_rubric_result(self) -> None:
        """score() should return a RubricResult with all 8 dimensions."""
        rubric = self._make_rubric_with_mock_judge(4.0)
        result = rubric.score(
            query="How much annual leave?",
            response=GOOD_GREEN_RESPONSE,
        )
        assert isinstance(result, RubricResult)
        assert len(result.dimension_scores) == 8

    def test_good_response_passes(self) -> None:
        """A well-formed response with good LLM scores should pass."""
        rubric = self._make_rubric_with_mock_judge(4.0)
        result = rubric.score(
            query="How much annual leave?",
            response=GOOD_GREEN_RESPONSE,
        )
        assert result.passed is True

    def test_bad_citations_fails_overall(self) -> None:
        """A response with no citations should fail (citation_quality = 1)."""
        rubric = self._make_rubric_with_mock_judge(4.0)
        result = rubric.score(
            query="How much annual leave?",
            response=NO_CITATIONS_RESPONSE,
        )
        assert result.passed is False
        assert "citation_quality" in result.dimension_flags

    def test_automated_checks_run_before_llm(self) -> None:
        """Automated checks should populate citation_quality, risk_awareness, etc."""
        rubric = self._make_rubric_with_mock_judge(4.0)
        result = rubric.score(
            query="How much annual leave?",
            response=GOOD_GREEN_RESPONSE,
        )
        # Citation quality should be set by automated checks (3+ citations = 5.0)
        assert result.dimension_scores["citation_quality"] == 5.0

    def test_context_passed_to_judge(self) -> None:
        """When context is provided, it should be passed to the LLM judge."""
        from unittest.mock import MagicMock
        rubric = QualityRubric()
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = (4.0, "Fine")
        rubric._llm_judge = mock_judge

        context = {"sector": "F&B", "headcount": 25}
        rubric.score(
            query="How much annual leave?",
            response=GOOD_GREEN_RESPONSE,
            context=context,
        )

        # Verify context was passed to at least one judge call
        calls = mock_judge.evaluate.call_args_list
        assert len(calls) > 0
        for call in calls:
            assert call.kwargs.get("context") == context or call[1].get("context") == context


# ===================================================================
# Test: score_batch
# ===================================================================


class TestScoreBatch:
    """Test the batch scoring function."""

    def test_batch_returns_list_of_results(self) -> None:
        """score_batch should return a list of RubricResult, one per test case."""
        from unittest.mock import MagicMock
        from hr_advisory.quality import score_batch

        rubric = QualityRubric()
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = (4.0, "OK")
        rubric._llm_judge = mock_judge

        test_cases = [
            {
                "query": "Annual leave entitlement?",
                "response": GOOD_GREEN_RESPONSE,
                "context": {},
            },
            {
                "query": "Workplace injury steps?",
                "response": GOOD_RED_RESPONSE,
                "context": {},
            },
        ]

        results = score_batch(test_cases, rubric=rubric)
        assert len(results) == 2
        assert all(isinstance(r, RubricResult) for r in results)

    def test_batch_creates_default_rubric_when_none(self) -> None:
        """score_batch should create a default QualityRubric if none provided."""
        from unittest.mock import patch, MagicMock
        from hr_advisory.quality import score_batch

        # Patch QualityRubric to avoid needing real LLM
        with patch("hr_advisory.quality.rubric.QualityRubric") as MockRubric:
            mock_instance = MagicMock()
            mock_instance.score.return_value = RubricResult(
                dimension_scores={
                    "legal_accuracy": 4.0,
                    "contextual_relevance": 4.0,
                    "conversational_coherence": 4.0,
                    "actionability": 4.0,
                    "risk_awareness": 4.0,
                    "citation_quality": 4.0,
                    "language_understanding": 4.0,
                    "completeness": 4.0,
                },
                details={},
            )
            MockRubric.return_value = mock_instance

            results = score_batch([
                {"query": "test", "response": GOOD_GREEN_RESPONSE, "context": {}},
            ])
            assert len(results) == 1


# ===================================================================
# Test: Module exports
# ===================================================================


class TestModuleExports:
    """Test that the quality module exports the expected public API."""

    def test_init_exports(self) -> None:
        """The quality __init__.py should export QualityRubric, RubricResult, AutomatedChecks, score_batch."""
        from hr_advisory.quality import QualityRubric, RubricResult, AutomatedChecks, score_batch
        assert QualityRubric is not None
        assert RubricResult is not None
        assert AutomatedChecks is not None
        assert score_batch is not None
