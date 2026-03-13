"""QA workflow API router -- human QA review and instruction patching.

Provides 9 endpoints under /admin/qa for:
- QA session management (create, list, get, conversations)
- Turn-level evaluation submission and listing
- Instruction patch management (list, approve, reject)

All endpoints require owner or hr_manager role.

NOTE: Uses in-memory stores for MVP. Migrate to DataFlow persistence
when the QA workflow is validated end-to-end.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.models.qa import PatchStatus, SessionStatus, validate_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/qa", tags=["qa"])

# ---------------------------------------------------------------------------
# In-memory stores (MVP -- migrate to DataFlow later)
# ---------------------------------------------------------------------------

_sessions: Dict[int, Dict[str, Any]] = {}
_evaluations: Dict[int, Dict[str, Any]] = {}
_patches: Dict[int, Dict[str, Any]] = {}

_next_session_id = 1
_next_evaluation_id = 1
_next_patch_id = 1

# Controls whether LLM-dependent background tasks (pre-approval testing,
# regression testing) are actually executed. Disabled by default to prevent
# blocking in unit tests where FastAPI TestClient runs background tasks
# synchronously. Enable explicitly in production via enable_llm_background_tasks().
_llm_background_tasks_enabled: bool = False


def enable_llm_background_tasks() -> None:
    """Enable LLM-dependent background tasks (pre-approval, regression).

    Call this at application startup to enable the PatchRunner background
    tasks. This must be called explicitly to avoid blocking in test
    environments where FastAPI TestClient runs tasks synchronously.
    """
    global _llm_background_tasks_enabled
    _llm_background_tasks_enabled = True
    logger.info("LLM background tasks enabled for QA patch testing")


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class SubmitEvaluationRequest(BaseModel):
    session_id: int
    conversation_id: str
    turn_number: int
    score_legal_accuracy: float
    score_contextual_relevance: float
    score_coherence: float
    score_actionability: float
    score_risk_awareness: float
    score_citation_quality: float
    score_language: float
    score_completeness: float
    citation_flags: Optional[List[Dict[str, Any]]] = None
    has_material_correction: bool = False
    correction_text: Optional[str] = None
    failure_category: Optional[str] = None
    affected_agent: Optional[str] = None

    @field_validator(
        "score_legal_accuracy",
        "score_contextual_relevance",
        "score_coherence",
        "score_actionability",
        "score_risk_awareness",
        "score_citation_quality",
        "score_language",
        "score_completeness",
    )
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        validate_score(v)
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(user: dict) -> None:
    """Raise 403 if user is not owner or hr_manager."""
    if user.get("role") not in ("owner", "hr_manager"):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions — requires owner or hr_manager role",
        )


def _run_pattern_detection() -> None:
    """Run PatternDetector and MutationEngine as a background task.

    Scans all evaluations for recurring failure patterns and proposes
    InstructionPatch candidates for any new clusters found. After a patch
    is proposed, schedules PatchRunner.test_pre_approval() to automatically
    test the patch before it can be approved.

    This function is designed to be called as a FastAPI BackgroundTask
    after an evaluation is submitted. It must never raise -- all errors
    are logged and swallowed to avoid disrupting the QA workflow.
    """
    global _next_patch_id

    try:
        from hr_advisory.quality.pattern_detector import PatternDetector
        from hr_advisory.quality.mutation_engine import MutationEngine

        detector = PatternDetector(evaluations=_evaluations, patches=_patches)
        clusters = detector.run()

        if not clusters:
            return

        engine = MutationEngine()
        for cluster in clusters:
            try:
                patch_dict = engine.propose(cluster)
                if patch_dict is not None:
                    patch_id = _next_patch_id
                    _next_patch_id += 1
                    patch_dict["id"] = patch_id
                    _patches[patch_id] = patch_dict
                    logger.info(
                        "Created patch %d for agent=%s, category=%s",
                        patch_id,
                        cluster["affected_agent"],
                        cluster["failure_category"],
                    )
                    # Schedule pre-approval testing for the new patch
                    if _llm_background_tasks_enabled:
                        _run_pre_approval_test(patch_id)
                    else:
                        logger.info(
                            "Skipping pre-approval test for patch %d: "
                            "LLM background tasks not enabled",
                            patch_id,
                        )
            except Exception as exc:
                logger.error(
                    "Failed to propose patch for cluster agent=%s, category=%s: %s",
                    cluster.get("affected_agent"),
                    cluster.get("failure_category"),
                    exc,
                    exc_info=True,
                )
    except Exception as exc:
        logger.error(
            "Pattern detection background task failed: %s",
            exc,
            exc_info=True,
        )


def _run_pre_approval_test(patch_id: int) -> None:
    """Run PatchRunner.test_pre_approval() for a patch as a background task.

    Updates the patch status based on the test result:
    - READY_FOR_APPROVAL if the patch improves scores
    - REJECTED if the patch does not improve scores

    This function must never raise -- all errors are logged and swallowed.
    """
    try:
        from hr_advisory.quality.patch_runner import PatchRunner

        patch = _patches.get(patch_id)
        if patch is None:
            logger.error(
                "Pre-approval test: patch %d not found in _patches store",
                patch_id,
            )
            return

        patch["status"] = PatchStatus.TESTING
        logger.info("Starting pre-approval test for patch %d", patch_id)

        runner = PatchRunner()
        result = runner.test_pre_approval(patch)

        patch["test_results"] = result
        patch["status"] = result["status_recommendation"]

        logger.info(
            "Pre-approval test for patch %d completed: recommendation=%s, delta=%.2f",
            patch_id,
            result["status_recommendation"],
            result.get("score_delta", 0.0),
        )
    except Exception as exc:
        logger.error(
            "Pre-approval test failed for patch %d: %s",
            patch_id,
            exc,
            exc_info=True,
        )
        # Leave patch in TESTING status on failure -- admin can re-trigger or reject
        patch = _patches.get(patch_id)
        if patch is not None:
            patch["status"] = PatchStatus.PROPOSED
            patch["test_results"] = {"error": str(exc)}


def _run_regression_test(patch_id: int) -> None:
    """Run PatchRunner.run_regression() for a patch as a background task.

    Updates the patch status based on the regression result:
    - DEPLOYED if no category regressions detected
    - ROLLED_BACK if any category regresses beyond threshold

    This function must never raise -- all errors are logged and swallowed.
    """
    try:
        from hr_advisory.quality.patch_runner import PatchRunner

        patch = _patches.get(patch_id)
        if patch is None:
            logger.error(
                "Regression test: patch %d not found in _patches store",
                patch_id,
            )
            return

        logger.info("Starting regression test for patch %d", patch_id)

        runner = PatchRunner()
        result = runner.run_regression(patch)

        patch["test_results"] = result
        patch["status"] = result["status_recommendation"]

        if result["status_recommendation"] == PatchStatus.DEPLOYED:
            patch["deployed_at"] = datetime.now(tz=timezone.utc).isoformat()

        logger.info(
            "Regression test for patch %d completed: recommendation=%s, " "rolled_back=%s",
            patch_id,
            result["status_recommendation"],
            result.get("rolled_back", False),
        )
    except Exception as exc:
        logger.error(
            "Regression test failed for patch %d: %s",
            patch_id,
            exc,
            exc_info=True,
        )
        # On regression failure, leave patch in approved status
        patch = _patches.get(patch_id)
        if patch is not None:
            patch["test_results"] = {"error": str(exc)}


def _fetch_conversations_for_session(
    session: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Fetch conversations matching session filters.

    MVP stub -- returns empty list. Will be wired to conversation
    storage when the advisory pipeline persists conversations.
    """
    return []


# ---------------------------------------------------------------------------
# 1. POST /sessions -- create QA session
# ---------------------------------------------------------------------------


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new QA review session."""
    _require_admin(user)

    global _next_session_id
    session_id = _next_session_id
    _next_session_id += 1

    reviewer_id = user.get("sub", user.get("id"))

    session = {
        "id": session_id,
        "reviewer_id": reviewer_id,
        "status": SessionStatus.ACTIVE,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "completed_at": None,
        "date_range_start": body.date_range_start,
        "date_range_end": body.date_range_end,
        "filters": body.filters,
        "summary": None,
    }
    _sessions[session_id] = session
    return session


# ---------------------------------------------------------------------------
# 2. GET /sessions -- list sessions
# ---------------------------------------------------------------------------


@router.get("/sessions")
async def list_sessions(
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all QA sessions, active first."""
    _require_admin(user)

    sessions = list(_sessions.values())
    # Sort: active sessions first, then by created_at descending
    sessions.sort(
        key=lambda s: (0 if s["status"] == "active" else 1, s.get("created_at", "")),
    )
    return {"sessions": sessions, "total": len(sessions)}


# ---------------------------------------------------------------------------
# 3. GET /sessions/{id} -- session detail
# ---------------------------------------------------------------------------


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get session detail by ID."""
    _require_admin(user)

    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ---------------------------------------------------------------------------
# 4. GET /sessions/{id}/conversations -- conversations matching filters
# ---------------------------------------------------------------------------


@router.get("/sessions/{session_id}/conversations")
async def get_session_conversations(
    session_id: int,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get conversations matching session filters."""
    _require_admin(user)

    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    conversations = _fetch_conversations_for_session(session)
    return {"conversations": conversations, "total": len(conversations)}


# ---------------------------------------------------------------------------
# 4b. POST /sessions/{id}/complete -- complete a QA session
# ---------------------------------------------------------------------------


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: int,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark a QA session as completed."""
    _require_admin(user)

    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Session is already completed",
        )

    session["status"] = SessionStatus.COMPLETED
    session["completed_at"] = datetime.now(tz=timezone.utc).isoformat()

    # Compute aggregate scores from evaluations
    session_evals = [e for e in _evaluations.values() if e["session_id"] == session_id]
    if session_evals:
        score_fields = [
            "score_legal_accuracy",
            "score_contextual_relevance",
            "score_coherence",
            "score_actionability",
            "score_risk_awareness",
            "score_citation_quality",
            "score_language",
            "score_completeness",
        ]
        dimension_labels = [
            "Legal Accuracy",
            "Contextual Relevance",
            "Coherence",
            "Actionability",
            "Risk Awareness",
            "Citation Quality",
            "Language Understanding",
            "Completeness",
        ]
        dimension_scores = []
        all_scores = []
        for field, label in zip(score_fields, dimension_labels):
            avg = sum(e[field] for e in session_evals) / len(session_evals)
            dimension_scores.append({"dimension": label, "average_score": round(avg, 2)})
            all_scores.append(avg)
        session["dimension_scores"] = dimension_scores
        session["average_overall_score"] = round(sum(all_scores) / len(all_scores), 2)

        # Failure category breakdown
        from collections import Counter

        failure_counts: Counter[str] = Counter()
        for e in session_evals:
            if e.get("has_material_correction") and e.get("failure_category"):
                failure_counts[e["failure_category"]] += 1
        session["failure_categories"] = [
            {"category": cat, "count": count} for cat, count in failure_counts.most_common()
        ]
    else:
        session["dimension_scores"] = []
        session["failure_categories"] = []
        session["average_overall_score"] = None

    return session


# ---------------------------------------------------------------------------
# 5. POST /evaluations -- submit evaluation
# ---------------------------------------------------------------------------


@router.post("/evaluations", status_code=201)
async def submit_evaluation(
    body: SubmitEvaluationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Submit a turn-level QA evaluation.

    After storing the evaluation, schedules a background task to run
    PatternDetector. If recurring failure patterns are found, MutationEngine
    proposes InstructionPatch candidates automatically.
    """
    _require_admin(user)

    # Verify session exists
    if body.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    global _next_evaluation_id
    eval_id = _next_evaluation_id
    _next_evaluation_id += 1

    evaluation = {
        "id": eval_id,
        "session_id": body.session_id,
        "conversation_id": body.conversation_id,
        "turn_number": body.turn_number,
        "score_legal_accuracy": body.score_legal_accuracy,
        "score_contextual_relevance": body.score_contextual_relevance,
        "score_coherence": body.score_coherence,
        "score_actionability": body.score_actionability,
        "score_risk_awareness": body.score_risk_awareness,
        "score_citation_quality": body.score_citation_quality,
        "score_language": body.score_language,
        "score_completeness": body.score_completeness,
        "citation_flags": body.citation_flags,
        "has_material_correction": body.has_material_correction,
        "correction_text": body.correction_text,
        "failure_category": body.failure_category,
        "affected_agent": body.affected_agent,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    _evaluations[eval_id] = evaluation

    # Schedule pattern detection as a background task
    background_tasks.add_task(_run_pattern_detection)

    return evaluation


# ---------------------------------------------------------------------------
# 6. GET /evaluations -- list evaluations
# ---------------------------------------------------------------------------


@router.get("/evaluations")
async def list_evaluations(
    session_id: Optional[int] = None,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """List evaluations, optionally filtered by session_id."""
    _require_admin(user)

    evals = list(_evaluations.values())
    if session_id is not None:
        evals = [e for e in evals if e["session_id"] == session_id]
    return {"evaluations": evals, "total": len(evals)}


# ---------------------------------------------------------------------------
# 7. GET /patches -- list patches
# ---------------------------------------------------------------------------


@router.get("/patches")
async def list_patches(
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """List instruction patches, optionally filtered by status."""
    _require_admin(user)

    patches = list(_patches.values())
    if status is not None:
        patches = [p for p in patches if p["status"] == status]
    return {"patches": patches, "total": len(patches)}


# ---------------------------------------------------------------------------
# 8. POST /patches/{id}/approve -- approve patch
# ---------------------------------------------------------------------------


@router.post("/patches/{patch_id}/approve")
async def approve_patch(
    patch_id: int,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Approve an instruction patch and schedule regression testing.

    The patch must be in 'ready_for_approval' status (i.e., it must have
    passed pre-approval testing). After approval, a regression test is
    scheduled as a background task to run the full 64-scenario suite.
    """
    _require_admin(user)

    patch = _patches.get(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    if patch["status"] in (PatchStatus.APPROVED, PatchStatus.DEPLOYED):
        raise HTTPException(
            status_code=400,
            detail=f"Patch is already {patch['status']}",
        )

    if patch["status"] != PatchStatus.READY_FOR_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Patch must be in 'ready_for_approval' status to approve, "
                f"but is currently '{patch['status']}'. Patches must pass "
                f"pre-approval testing before they can be approved."
            ),
        )

    patch["status"] = PatchStatus.APPROVED
    patch["approved_at"] = datetime.now(tz=timezone.utc).isoformat()
    patch["approved_by"] = user.get("sub", user.get("id"))

    # Schedule regression testing as a background task
    if _llm_background_tasks_enabled:
        background_tasks.add_task(_run_regression_test, patch_id)
    else:
        logger.info(
            "Skipping regression test for patch %d: "
            "LLM background tasks not enabled. Call "
            "enable_llm_background_tasks() at application startup "
            "to enable automated regression testing.",
            patch_id,
        )

    return patch


# ---------------------------------------------------------------------------
# 9. POST /patches/{id}/reject -- reject patch
# ---------------------------------------------------------------------------


@router.post("/patches/{patch_id}/reject")
async def reject_patch(
    patch_id: int,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Reject an instruction patch."""
    _require_admin(user)

    patch = _patches.get(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    if patch["status"] == PatchStatus.REJECTED:
        raise HTTPException(
            status_code=400,
            detail="Patch is already rejected",
        )

    patch["status"] = PatchStatus.REJECTED
    return patch
