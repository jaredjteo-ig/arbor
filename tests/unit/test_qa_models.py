"""Unit tests for QA workflow DataFlow models.

Tests the QASession, QAEvaluation, InstructionPatch, and PatchTestResult
models covering:
1. Model creation with required and default fields
2. Evaluation score validation (1-5 range)
3. Session lifecycle (create -> complete)
4. Patch status transitions
5. Field type correctness

Note: DataFlow @db.model classes do not support kwargs in their constructors.
Fields are set via attribute assignment after instantiation, which is the
standard DataFlow pattern. Factory helpers (_make_session, etc.) wrap this.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hr_advisory.models.qa import (
    EvaluationFailureCategory,
    InstructionPatch,
    PatchStatus,
    QAEvaluation,
    QASession,
    SessionStatus,
    TargetAgent,
    PatchTestResult,
    TestRunType,
    validate_score,
)


# ---------------------------------------------------------------------------
# DataFlow model factory helpers (attribute-assignment pattern)
# ---------------------------------------------------------------------------


def _make_session(**kwargs) -> QASession:
    """Create a QASession with the given field values."""
    session = QASession()
    for key, value in kwargs.items():
        setattr(session, key, value)
    return session


def _make_evaluation(**kwargs) -> QAEvaluation:
    """Create a QAEvaluation with the given field values."""
    evaluation = QAEvaluation()
    for key, value in kwargs.items():
        setattr(evaluation, key, value)
    return evaluation


def _make_patch(**kwargs) -> InstructionPatch:
    """Create an InstructionPatch with the given field values."""
    patch = InstructionPatch()
    for key, value in kwargs.items():
        setattr(patch, key, value)
    return patch


def _make_test_run(**kwargs) -> PatchTestResult:
    """Create a PatchTestResult with the given field values."""
    result = PatchTestResult()
    for key, value in kwargs.items():
        setattr(result, key, value)
    return result


# ---------------------------------------------------------------------------
# 1. QASession model tests
# ---------------------------------------------------------------------------


class TestQASessionCreation:
    """Test QASession model instantiation and field defaults."""

    def test_create_session_with_required_fields(self) -> None:
        """A QA session needs only a reviewer_id to be created."""
        session = _make_session(reviewer_id=1)
        assert session.reviewer_id == 1
        assert session.status == SessionStatus.ACTIVE

    def test_session_defaults(self) -> None:
        """Unspecified optional fields should have sensible defaults."""
        session = _make_session(reviewer_id=1)
        assert session.completed_at is None
        assert session.date_range_start is None
        assert session.date_range_end is None
        assert session.filters is None
        assert session.summary is None

    def test_session_with_filters(self) -> None:
        """Filters should accept a JSON-serialisable dict."""
        filters = {
            "risk_tier": ["amber", "red"],
            "domain": ["employment_act"],
            "flagged_only": True,
            "confidence_min": 0.0,
            "confidence_max": 0.7,
        }
        session = _make_session(reviewer_id=1, filters=filters)
        assert session.filters == filters
        assert session.filters["risk_tier"] == ["amber", "red"]
        assert session.filters["flagged_only"] is True

    def test_session_with_date_range(self) -> None:
        """Sessions can have a date range for scoping conversations."""
        start = datetime(2026, 3, 1, tzinfo=timezone.utc)
        end = datetime(2026, 3, 7, tzinfo=timezone.utc)
        session = _make_session(
            reviewer_id=1,
            date_range_start=start,
            date_range_end=end,
        )
        assert session.date_range_start == start
        assert session.date_range_end == end

    def test_session_status_values(self) -> None:
        """SessionStatus should have 'active' and 'completed' values."""
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.COMPLETED == "completed"


class TestQASessionLifecycle:
    """Test session transitions from creation through completion."""

    def test_new_session_is_active(self) -> None:
        """A freshly created session must be in 'active' status."""
        session = _make_session(reviewer_id=1)
        assert session.status == SessionStatus.ACTIVE

    def test_complete_session(self) -> None:
        """Completing a session sets status and completed_at."""
        session = _make_session(reviewer_id=1, status=SessionStatus.ACTIVE)
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(tz=timezone.utc)
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None

    def test_session_summary_on_completion(self) -> None:
        """Session summary should store aggregate scores."""
        summary = {
            "count_evaluated": 24,
            "avg_overall_score": 3.8,
            "per_dimension_averages": {
                "legal_accuracy": 3.6,
                "citation_quality": 4.1,
                "relevance": 4.0,
                "actionability": 3.2,
                "risk_awareness": 3.5,
                "language": 4.2,
                "completeness": 4.3,
            },
        }
        session = _make_session(
            reviewer_id=1,
            status=SessionStatus.COMPLETED,
            summary=summary,
        )
        assert session.summary["count_evaluated"] == 24
        assert session.summary["avg_overall_score"] == 3.8
        assert "per_dimension_averages" in session.summary


# ---------------------------------------------------------------------------
# 2. QAEvaluation model tests
# ---------------------------------------------------------------------------


class TestQAEvaluationCreation:
    """Test QAEvaluation model instantiation."""

    def test_create_evaluation_with_all_scores(self) -> None:
        """An evaluation needs session_id, conversation_id, turn, and all scores."""
        evaluation = _make_evaluation(
            session_id=1,
            conversation_id="ADV-2026-03-10-0042",
            turn_number=2,
            score_legal_accuracy=3.0,
            score_contextual_relevance=4.0,
            score_coherence=4.0,
            score_actionability=2.0,
            score_risk_awareness=3.0,
            score_citation_quality=4.0,
            score_language=4.0,
            score_completeness=5.0,
        )
        assert evaluation.session_id == 1
        assert evaluation.conversation_id == "ADV-2026-03-10-0042"
        assert evaluation.turn_number == 2
        assert evaluation.score_legal_accuracy == 3.0
        assert evaluation.score_completeness == 5.0

    def test_evaluation_defaults(self) -> None:
        """Optional fields should default to safe values."""
        evaluation = _make_evaluation(
            session_id=1,
            conversation_id="ADV-001",
            turn_number=1,
            score_legal_accuracy=4.0,
            score_contextual_relevance=4.0,
            score_coherence=4.0,
            score_actionability=4.0,
            score_risk_awareness=4.0,
            score_citation_quality=4.0,
            score_language=4.0,
            score_completeness=4.0,
        )
        assert evaluation.citation_flags is None
        assert evaluation.has_material_correction is False
        assert evaluation.correction_text is None
        assert evaluation.failure_category is None
        assert evaluation.affected_agent is None

    def test_evaluation_with_citation_flags(self) -> None:
        """Citation flags should store a list of provision flag dicts."""
        flags = [
            {"provision_id": "EA-s27-1", "status": "correct"},
            {"provision_id": "EA-s27A", "status": "incorrect", "correction": "EA-s27-2a"},
        ]
        evaluation = _make_evaluation(
            session_id=1,
            conversation_id="ADV-001",
            turn_number=1,
            score_legal_accuracy=3.0,
            score_contextual_relevance=4.0,
            score_coherence=4.0,
            score_actionability=2.0,
            score_risk_awareness=3.0,
            score_citation_quality=3.0,
            score_language=4.0,
            score_completeness=3.0,
            citation_flags=flags,
        )
        assert len(evaluation.citation_flags) == 2
        assert evaluation.citation_flags[0]["status"] == "correct"

    def test_evaluation_with_material_correction(self) -> None:
        """Material corrections should include the flag and correction text."""
        evaluation = _make_evaluation(
            session_id=1,
            conversation_id="ADV-001",
            turn_number=1,
            score_legal_accuracy=2.0,
            score_contextual_relevance=3.0,
            score_coherence=3.0,
            score_actionability=2.0,
            score_risk_awareness=3.0,
            score_citation_quality=3.0,
            score_language=3.0,
            score_completeness=3.0,
            has_material_correction=True,
            correction_text="The EA s.27 deduction cap applies to aggregate deductions.",
        )
        assert evaluation.has_material_correction is True
        assert "aggregate" in evaluation.correction_text

    def test_evaluation_failure_category_values(self) -> None:
        """Failure categories should include all defined types."""
        assert EvaluationFailureCategory.WRONG_LAW == "wrong_law_cited"
        assert EvaluationFailureCategory.WRONG_INTERPRETATION == "correct_law_wrong_interpretation"
        assert EvaluationFailureCategory.MISSED_NUANCE == "missed_critical_nuance"
        assert EvaluationFailureCategory.IGNORED_CONTEXT == "ignored_company_context"
        assert EvaluationFailureCategory.LOST_CONTEXT == "lost_conversation_context"
        assert EvaluationFailureCategory.OVERLY_GENERIC == "overly_generic"
        assert EvaluationFailureCategory.WRONG_ROUTING == "wrong_domain_routing"
        assert EvaluationFailureCategory.FABRICATED_CITATION == "fabricated_citation"

    def test_evaluation_target_agent_values(self) -> None:
        """Target agent enum should cover all pipeline agents."""
        assert TargetAgent.EMPLOYMENT_ACT == "employment_act_specialist"
        assert TargetAgent.CPF == "cpf_specialist"
        assert TargetAgent.FOREIGN_MANPOWER == "foreign_manpower_specialist"
        assert TargetAgent.FAIR_EMPLOYMENT == "fair_employment_specialist"
        assert TargetAgent.QUERY_ANALYZER == "query_analyzer"
        assert TargetAgent.ORCHESTRATOR == "orchestrator"
        assert TargetAgent.RESPONSE_SYNTHESIZER == "response_synthesizer"


class TestScoreValidation:
    """Test that evaluation scores are constrained to 1-5 range."""

    def test_valid_scores_accepted(self) -> None:
        """Scores of 1.0, 2.5, 3.0, 4.5, 5.0 should all be valid."""
        for score in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]:
            assert validate_score(score) == score

    def test_score_below_minimum_raises(self) -> None:
        """A score below 1 must raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 5"):
            validate_score(0.5)

    def test_score_above_maximum_raises(self) -> None:
        """A score above 5 must raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 5"):
            validate_score(5.5)

    def test_score_zero_raises(self) -> None:
        """A score of 0 must raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 5"):
            validate_score(0.0)

    def test_score_negative_raises(self) -> None:
        """A negative score must raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 5"):
            validate_score(-1.0)

    def test_boundary_scores(self) -> None:
        """Exact boundary values 1.0 and 5.0 should be valid."""
        assert validate_score(1.0) == 1.0
        assert validate_score(5.0) == 5.0


# ---------------------------------------------------------------------------
# 3. InstructionPatch model tests
# ---------------------------------------------------------------------------


class TestInstructionPatchCreation:
    """Test InstructionPatch model instantiation."""

    def test_create_patch_with_required_fields(self) -> None:
        """A patch needs target_agent, patch_type, and new_text."""
        patch = _make_patch(
            target_agent="employment_act_specialist",
            patch_type="qa_learned_rule",
            new_text="When advising on EA s.27, specify aggregate cap.",
            evidence_count=5,
            evidence_ids=[1, 2, 3, 4, 5],
        )
        assert patch.target_agent == "employment_act_specialist"
        assert patch.new_text == "When advising on EA s.27, specify aggregate cap."
        assert patch.evidence_count == 5
        assert len(patch.evidence_ids) == 5

    def test_patch_defaults(self) -> None:
        """Optional fields should have sensible defaults."""
        patch = _make_patch(
            target_agent="cpf_specialist",
            patch_type="expertise_addition",
            new_text="Age band boundary clarification.",
            evidence_count=3,
            evidence_ids=[10, 11, 12],
        )
        assert patch.old_text is None
        assert patch.status == PatchStatus.PROPOSED
        assert patch.approved_at is None
        assert patch.deployed_at is None
        assert patch.approved_by is None
        assert patch.test_results is None

    def test_patch_with_old_text(self) -> None:
        """Patches can include old text for before/after diff."""
        patch = _make_patch(
            target_agent="employment_act_specialist",
            patch_type="qa_learned_rule",
            old_text="Part IV protections (rest days, hours of work)",
            new_text="Part IV protections including aggregate deduction cap",
            evidence_count=5,
            evidence_ids=[1, 2, 3, 4, 5],
        )
        assert patch.old_text is not None
        assert "Part IV" in patch.old_text


class TestPatchStatusTransitions:
    """Test valid patch status transitions."""

    def test_patch_status_values(self) -> None:
        """PatchStatus should have all required lifecycle values."""
        assert PatchStatus.PROPOSED == "proposed"
        assert PatchStatus.TESTING == "testing"
        assert PatchStatus.READY_FOR_APPROVAL == "ready_for_approval"
        assert PatchStatus.APPROVED == "approved"
        assert PatchStatus.DEPLOYED == "deployed"
        assert PatchStatus.REJECTED == "rejected"
        assert PatchStatus.ROLLED_BACK == "rolled_back"

    def test_proposed_to_testing(self) -> None:
        """A proposed patch can move to testing."""
        patch = _make_patch(
            target_agent="cpf_specialist",
            patch_type="qa_learned_rule",
            new_text="Test rule.",
            evidence_count=3,
            evidence_ids=[1, 2, 3],
            status=PatchStatus.PROPOSED,
        )
        patch.status = PatchStatus.TESTING
        assert patch.status == PatchStatus.TESTING

    def test_testing_to_ready_for_approval(self) -> None:
        """After testing, a patch can be marked ready for approval."""
        patch = _make_patch(
            target_agent="cpf_specialist",
            patch_type="qa_learned_rule",
            new_text="Test rule.",
            evidence_count=3,
            evidence_ids=[1, 2, 3],
            status=PatchStatus.TESTING,
        )
        patch.test_results = {
            "scenarios_run": 5,
            "scenarios_improved": 4,
            "scenarios_regressed": 0,
        }
        patch.status = PatchStatus.READY_FOR_APPROVAL
        assert patch.status == PatchStatus.READY_FOR_APPROVAL
        assert patch.test_results is not None

    def test_approve_patch(self) -> None:
        """Approving a patch sets status, approved_at, and approved_by."""
        patch = _make_patch(
            target_agent="cpf_specialist",
            patch_type="qa_learned_rule",
            new_text="Test rule.",
            evidence_count=3,
            evidence_ids=[1, 2, 3],
            status=PatchStatus.READY_FOR_APPROVAL,
        )
        now = datetime.now(tz=timezone.utc)
        patch.status = PatchStatus.APPROVED
        patch.approved_at = now
        patch.approved_by = 10
        assert patch.status == PatchStatus.APPROVED
        assert patch.approved_at == now
        assert patch.approved_by == 10

    def test_reject_patch(self) -> None:
        """Rejecting a patch sets status to rejected."""
        patch = _make_patch(
            target_agent="cpf_specialist",
            patch_type="qa_learned_rule",
            new_text="Test rule.",
            evidence_count=3,
            evidence_ids=[1, 2, 3],
            status=PatchStatus.READY_FOR_APPROVAL,
        )
        patch.status = PatchStatus.REJECTED
        assert patch.status == PatchStatus.REJECTED

    def test_deploy_approved_patch(self) -> None:
        """An approved patch can be deployed."""
        patch = _make_patch(
            target_agent="cpf_specialist",
            patch_type="qa_learned_rule",
            new_text="Test rule.",
            evidence_count=3,
            evidence_ids=[1, 2, 3],
            status=PatchStatus.APPROVED,
        )
        now = datetime.now(tz=timezone.utc)
        patch.status = PatchStatus.DEPLOYED
        patch.deployed_at = now
        assert patch.status == PatchStatus.DEPLOYED
        assert patch.deployed_at == now

    def test_rollback_deployed_patch(self) -> None:
        """A deployed patch can be rolled back."""
        patch = _make_patch(
            target_agent="cpf_specialist",
            patch_type="qa_learned_rule",
            new_text="Test rule.",
            evidence_count=3,
            evidence_ids=[1, 2, 3],
            status=PatchStatus.DEPLOYED,
        )
        patch.status = PatchStatus.ROLLED_BACK
        assert patch.status == PatchStatus.ROLLED_BACK


# ---------------------------------------------------------------------------
# 4. PatchTestResult model tests
# ---------------------------------------------------------------------------


class TestPatchTestResultModel:
    """Test PatchTestResult model instantiation."""

    def test_create_test_run_result(self) -> None:
        """A test run result records pre/post patch comparison."""
        result = _make_test_run(
            patch_id=1,
            run_type=TestRunType.POST_PATCH,
            scenarios_run=5,
            scenarios_passed=4,
            scenarios_failed=1,
            avg_score_before=2.8,
            avg_score_after=4.1,
            score_delta=1.3,
        )
        assert result.patch_id == 1
        assert result.run_type == TestRunType.POST_PATCH
        assert result.scenarios_run == 5
        assert result.scenarios_passed == 4
        assert result.scenarios_failed == 1
        assert result.avg_score_before == 2.8
        assert result.avg_score_after == 4.1
        assert result.score_delta == 1.3

    def test_run_type_values(self) -> None:
        """TestRunType should have pre_patch, post_patch, regression."""
        assert TestRunType.PRE_PATCH == "pre_patch"
        assert TestRunType.POST_PATCH == "post_patch"
        assert TestRunType.REGRESSION == "regression"

    def test_result_with_failing_scenarios(self) -> None:
        """Failing scenario IDs should be stored as JSON list."""
        result = _make_test_run(
            patch_id=1,
            run_type=TestRunType.POST_PATCH,
            scenarios_run=5,
            scenarios_passed=3,
            scenarios_failed=2,
            avg_score_before=2.8,
            avg_score_after=3.5,
            score_delta=0.7,
            failing_scenario_ids=[101, 104],
        )
        assert result.failing_scenario_ids == [101, 104]
        assert len(result.failing_scenario_ids) == 2

    def test_result_defaults(self) -> None:
        """Optional fields should default correctly."""
        result = _make_test_run(
            patch_id=1,
            run_type=TestRunType.PRE_PATCH,
            scenarios_run=10,
            scenarios_passed=10,
            scenarios_failed=0,
            avg_score_before=3.0,
            avg_score_after=3.0,
            score_delta=0.0,
        )
        assert result.failing_scenario_ids is None

    def test_pre_patch_run(self) -> None:
        """Pre-patch runs establish the baseline scores."""
        result = _make_test_run(
            patch_id=1,
            run_type=TestRunType.PRE_PATCH,
            scenarios_run=5,
            scenarios_passed=2,
            scenarios_failed=3,
            avg_score_before=2.5,
            avg_score_after=2.5,
            score_delta=0.0,
        )
        assert result.run_type == TestRunType.PRE_PATCH
        assert result.score_delta == 0.0

    def test_regression_run(self) -> None:
        """Regression runs check that existing passing scenarios still pass."""
        result = _make_test_run(
            patch_id=1,
            run_type=TestRunType.REGRESSION,
            scenarios_run=20,
            scenarios_passed=20,
            scenarios_failed=0,
            avg_score_before=4.0,
            avg_score_after=4.0,
            score_delta=0.0,
        )
        assert result.run_type == TestRunType.REGRESSION
        assert result.scenarios_failed == 0
