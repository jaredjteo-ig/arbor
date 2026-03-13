"""DataFlow models for the human QA review workflow.

These models support the QA reviewer interface and instruction fine-tuning
pipeline. They store QA sessions, per-turn evaluations, instruction patches,
and test run results.

See: workspaces/hr-ai-advisory/01-analysis/01-research/12-human-qa-workflow-design.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from hr_advisory.models.database import db


# ---------------------------------------------------------------------------
# Enums (string-based for DataFlow compatibility)
# ---------------------------------------------------------------------------


class SessionStatus:
    """QA session lifecycle status."""

    ACTIVE = "active"
    COMPLETED = "completed"


class EvaluationFailureCategory:
    """Categorisation of advisory response failures."""

    WRONG_LAW = "wrong_law_cited"
    WRONG_INTERPRETATION = "correct_law_wrong_interpretation"
    MISSED_NUANCE = "missed_critical_nuance"
    IGNORED_CONTEXT = "ignored_company_context"
    LOST_CONTEXT = "lost_conversation_context"
    OVERLY_GENERIC = "overly_generic"
    WRONG_ROUTING = "wrong_domain_routing"
    FABRICATED_CITATION = "fabricated_citation"
    OTHER = "other"


class TargetAgent:
    """Agent identifiers for the advisory pipeline."""

    EMPLOYMENT_ACT = "employment_act_specialist"
    CPF = "cpf_specialist"
    FOREIGN_MANPOWER = "foreign_manpower_specialist"
    FAIR_EMPLOYMENT = "fair_employment_specialist"
    TAX = "tax_specialist"
    WSH = "wsh_specialist"
    PDPA = "pdpa_specialist"
    QUERY_ANALYZER = "query_analyzer"
    ORCHESTRATOR = "orchestrator"
    RESPONSE_SYNTHESIZER = "response_synthesizer"


class PatchStatus:
    """Instruction patch lifecycle status."""

    PROPOSED = "proposed"
    TESTING = "testing"
    READY_FOR_APPROVAL = "ready_for_approval"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class TestRunType:
    """Type of automated test run against an instruction patch."""

    PRE_PATCH = "pre_patch"
    POST_PATCH = "post_patch"
    REGRESSION = "regression"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_score(score: float) -> float:
    """Validate that a QA evaluation score is between 1 and 5 inclusive.

    Args:
        score: The score to validate.

    Returns:
        The validated score.

    Raises:
        ValueError: If the score is outside the 1-5 range.
    """
    if score < 1.0 or score > 5.0:
        raise ValueError(f"Score {score} is out of range: must be between 1 and 5 inclusive")
    return score


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@db.model
@dataclass
class QASession:
    """A structured QA review session.

    A reviewer starts a session with optional filters (date range, risk tier,
    domain, confidence range). The session groups evaluations and produces
    a summary with aggregate scores at completion.
    """

    reviewer_id: int = 0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    filters: Optional[dict] = None
    status: str = SessionStatus.ACTIVE
    summary: Optional[dict] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_qa_session_reviewer", "fields": ["reviewer_id"]},
            {"name": "idx_qa_session_status", "fields": ["status"]},
        ],
    }


@db.model
@dataclass
class QAEvaluation:
    """Evaluation of a single advisory response (one turn).

    Stores rubric scores across 8 quality dimensions, citation flags,
    material corrections, failure classification, and the affected agent.
    All scores are floats in the range 1.0-5.0.
    """

    session_id: int = 0
    conversation_id: str = ""
    turn_number: int = 0

    # Quality dimension scores (1.0 - 5.0)
    score_legal_accuracy: float = 0.0
    score_contextual_relevance: float = 0.0
    score_coherence: float = 0.0
    score_actionability: float = 0.0
    score_risk_awareness: float = 0.0
    score_citation_quality: float = 0.0
    score_language: float = 0.0
    score_completeness: float = 0.0

    # Citation flags: list of {provision_id, status, correction?}
    citation_flags: Optional[dict] = None

    # Material correction
    has_material_correction: bool = False
    correction_text: Optional[str] = None

    # Failure classification
    failure_category: Optional[str] = None
    affected_agent: Optional[str] = None

    created_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_qa_eval_session", "fields": ["session_id"]},
            {"name": "idx_qa_eval_conversation", "fields": ["conversation_id"]},
        ],
    }


@db.model
@dataclass
class InstructionPatch:
    """A proposed change to an agent's system prompt instructions.

    Tracks the full lifecycle from proposal through testing, approval,
    deployment, and potential rollback. Each patch is linked to the
    QA evaluations that motivated it via evidence_ids.
    """

    target_agent: str = ""
    patch_type: str = ""
    old_text: Optional[str] = None
    new_text: str = ""
    evidence_count: int = 0
    evidence_ids: Optional[dict] = None

    # Test results stored as JSON dict
    test_results: Optional[dict] = None

    # Lifecycle
    status: str = PatchStatus.PROPOSED
    proposed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    approved_by: Optional[int] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_patch_agent", "fields": ["target_agent"]},
            {"name": "idx_patch_status", "fields": ["status"]},
        ],
    }


@db.model
@dataclass
class PatchTestResult:
    """Result of an automated test run comparing pre/post patch quality.

    Records how many test scenarios were run, how many passed/failed,
    and the average score delta. Used to decide whether a patch should
    be promoted or rejected.
    """

    patch_id: int = 0
    run_type: str = TestRunType.PRE_PATCH
    scenarios_run: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    avg_score_before: float = 0.0
    avg_score_after: float = 0.0
    score_delta: float = 0.0
    failing_scenario_ids: Optional[dict] = None
    run_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_test_run_patch", "fields": ["patch_id"]},
            {"name": "idx_test_run_type", "fields": ["run_type"]},
        ],
    }
