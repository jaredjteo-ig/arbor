"""Unit tests for the QA workflow API router.

Tests all 9 endpoints under /admin/qa:
1. POST /sessions -- create QA session
2. GET /sessions -- list sessions
3. GET /sessions/{id} -- session detail
4. GET /sessions/{id}/conversations -- conversations matching filters
5. POST /evaluations -- submit evaluation
6. GET /evaluations -- list evaluations
7. GET /patches -- list patches
8. POST /patches/{id}/approve -- approve patch
9. POST /patches/{id}/reject -- reject patch

Also tests:
- Admin-only access (non-admin gets 403)
- Request validation (missing fields, bad scores)
- Response format correctness
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.routers.qa import router
from hr_advisory.models.qa import (
    PatchStatus,
)


# ---------------------------------------------------------------------------
# Helpers and fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the QA router mounted."""
    app = FastAPI()
    # The router has prefix="/admin/qa" built in
    app.include_router(router)
    return app


def _fake_admin(role: str = "owner") -> dict:
    return {
        "sub": 10,
        "email": "admin@example.com",
        "role": role,
        "company_id": 1,
        "id": "admin-10",
    }


def _fake_regular_user() -> dict:
    return {
        "sub": 99,
        "email": "user@example.com",
        "role": "employee",
        "company_id": 1,
    }


@pytest.fixture()
def admin_client():
    """Test client with admin auth (owner role)."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_admin("owner")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def hr_manager_client():
    """Test client with hr_manager role."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_admin("hr_manager")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def regular_user_client():
    """Test client with regular (non-admin) user auth."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_regular_user()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client():
    """Test client with no auth override (will fail on get_current_user)."""
    app = _make_app()
    yield TestClient(app)


# ---------------------------------------------------------------------------
# Session store mock fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_qa_stores():
    """Clear in-memory QA stores before each test."""
    from hr_advisory.api.routers.qa import _evaluations, _patches, _sessions

    _sessions.clear()
    _evaluations.clear()
    _patches.clear()
    yield
    _sessions.clear()
    _evaluations.clear()
    _patches.clear()


# ---------------------------------------------------------------------------
# 1. POST /admin/qa/sessions -- create session
# ---------------------------------------------------------------------------


class TestCreateSession:
    """POST /admin/qa/sessions creates a new QA review session."""

    def test_create_session_success(self, admin_client) -> None:
        """Creating a session with valid filters returns 201."""
        resp = admin_client.post(
            "/admin/qa/sessions",
            json={
                "date_range_start": "2026-03-01T00:00:00Z",
                "date_range_end": "2026-03-07T00:00:00Z",
                "filters": {
                    "risk_tier": ["amber", "red"],
                    "flagged_only": True,
                },
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "active"
        assert data["reviewer_id"] == 10
        assert "id" in data

    def test_create_session_minimal(self, admin_client) -> None:
        """Creating a session without optional fields returns 201."""
        resp = admin_client.post(
            "/admin/qa/sessions",
            json={},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "active"

    def test_create_session_hr_manager(self, hr_manager_client) -> None:
        """HR managers can also create QA sessions."""
        resp = hr_manager_client.post(
            "/admin/qa/sessions",
            json={},
        )
        assert resp.status_code == 201

    def test_create_session_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot create QA sessions (403)."""
        resp = regular_user_client.post(
            "/admin/qa/sessions",
            json={},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 2. GET /admin/qa/sessions -- list sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    """GET /admin/qa/sessions lists all QA sessions."""

    def test_list_sessions_empty(self, admin_client) -> None:
        """When no sessions exist, returns empty list."""
        resp = admin_client.get("/admin/qa/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    def test_list_sessions_returns_created(self, admin_client) -> None:
        """After creating a session, it appears in the list."""
        admin_client.post("/admin/qa/sessions", json={})
        resp = admin_client.get("/admin/qa/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["sessions"]) == 1

    def test_list_sessions_active_first(self, admin_client) -> None:
        """Active sessions should appear before completed ones."""
        # Create two sessions
        resp1 = admin_client.post("/admin/qa/sessions", json={})
        session_1_id = resp1.json()["id"]

        resp2 = admin_client.post("/admin/qa/sessions", json={})
        session_2_id = resp2.json()["id"]

        # Complete the first one by posting to a completion endpoint
        # (We manipulate the store directly since completion is part of the router logic)
        from hr_advisory.api.routers.qa import _sessions

        _sessions[session_1_id]["status"] = "completed"

        resp = admin_client.get("/admin/qa/sessions")
        data = resp.json()
        assert data["total"] == 2
        # Active session should come first
        assert data["sessions"][0]["status"] == "active"
        assert data["sessions"][1]["status"] == "completed"

    def test_list_sessions_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot list QA sessions."""
        resp = regular_user_client.get("/admin/qa/sessions")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3. GET /admin/qa/sessions/{id} -- session detail
# ---------------------------------------------------------------------------


class TestGetSession:
    """GET /admin/qa/sessions/{id} returns session detail."""

    def test_get_session_success(self, admin_client) -> None:
        """Fetching an existing session returns its full detail."""
        create_resp = admin_client.post(
            "/admin/qa/sessions",
            json={
                "filters": {"risk_tier": ["red"]},
            },
        )
        session_id = create_resp.json()["id"]

        resp = admin_client.get(f"/admin/qa/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == session_id
        assert data["filters"]["risk_tier"] == ["red"]

    def test_get_session_not_found(self, admin_client) -> None:
        """Fetching a non-existent session returns 404."""
        resp = admin_client.get("/admin/qa/sessions/99999")
        assert resp.status_code == 404

    def test_get_session_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot view session detail."""
        resp = regular_user_client.get("/admin/qa/sessions/1")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. GET /admin/qa/sessions/{id}/conversations -- conversations matching filters
# ---------------------------------------------------------------------------


class TestGetSessionConversations:
    """GET /admin/qa/sessions/{id}/conversations returns filtered conversations."""

    @patch("hr_advisory.api.routers.qa._fetch_conversations_for_session")
    def test_get_conversations_success(self, mock_fetch, admin_client) -> None:
        """Returns conversations matching session filters."""
        mock_fetch.return_value = [
            {
                "conversation_id": "ADV-001",
                "risk_tier": "amber",
                "confidence_score": 0.72,
                "turns": 3,
            },
            {
                "conversation_id": "ADV-002",
                "risk_tier": "red",
                "confidence_score": 0.45,
                "turns": 2,
            },
        ]
        create_resp = admin_client.post(
            "/admin/qa/sessions",
            json={"filters": {"risk_tier": ["amber", "red"]}},
        )
        session_id = create_resp.json()["id"]

        resp = admin_client.get(f"/admin/qa/sessions/{session_id}/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert "conversations" in data
        assert len(data["conversations"]) == 2

    def test_get_conversations_session_not_found(self, admin_client) -> None:
        """Returns 404 when session does not exist."""
        resp = admin_client.get("/admin/qa/sessions/99999/conversations")
        assert resp.status_code == 404

    def test_get_conversations_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot view session conversations."""
        resp = regular_user_client.get("/admin/qa/sessions/1/conversations")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 5. POST /admin/qa/evaluations -- submit evaluation
# ---------------------------------------------------------------------------


class TestSubmitEvaluation:
    """POST /admin/qa/evaluations submits a turn evaluation."""

    def test_submit_evaluation_success(self, admin_client) -> None:
        """Submitting a valid evaluation returns 201."""
        # First create a session
        create_resp = admin_client.post("/admin/qa/sessions", json={})
        session_id = create_resp.json()["id"]

        resp = admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": session_id,
                "conversation_id": "ADV-2026-03-10-0042",
                "turn_number": 2,
                "score_legal_accuracy": 3.0,
                "score_contextual_relevance": 4.0,
                "score_coherence": 4.0,
                "score_actionability": 2.0,
                "score_risk_awareness": 3.0,
                "score_citation_quality": 4.0,
                "score_language": 4.0,
                "score_completeness": 5.0,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["score_legal_accuracy"] == 3.0

    def test_submit_evaluation_with_correction(self, admin_client) -> None:
        """Evaluations can include material corrections."""
        create_resp = admin_client.post("/admin/qa/sessions", json={})
        session_id = create_resp.json()["id"]

        resp = admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": session_id,
                "conversation_id": "ADV-001",
                "turn_number": 1,
                "score_legal_accuracy": 2.0,
                "score_contextual_relevance": 3.0,
                "score_coherence": 3.0,
                "score_actionability": 2.0,
                "score_risk_awareness": 3.0,
                "score_citation_quality": 3.0,
                "score_language": 3.0,
                "score_completeness": 3.0,
                "has_material_correction": True,
                "correction_text": "The aggregate cap applies.",
                "failure_category": "missed_critical_nuance",
                "affected_agent": "employment_act_specialist",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["has_material_correction"] is True
        assert data["correction_text"] == "The aggregate cap applies."

    def test_submit_evaluation_invalid_score_too_high(self, admin_client) -> None:
        """Score above 5 should be rejected with 422."""
        create_resp = admin_client.post("/admin/qa/sessions", json={})
        session_id = create_resp.json()["id"]

        resp = admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": session_id,
                "conversation_id": "ADV-001",
                "turn_number": 1,
                "score_legal_accuracy": 6.0,
                "score_contextual_relevance": 4.0,
                "score_coherence": 4.0,
                "score_actionability": 4.0,
                "score_risk_awareness": 4.0,
                "score_citation_quality": 4.0,
                "score_language": 4.0,
                "score_completeness": 4.0,
            },
        )
        assert resp.status_code == 422

    def test_submit_evaluation_invalid_score_too_low(self, admin_client) -> None:
        """Score below 1 should be rejected with 422."""
        create_resp = admin_client.post("/admin/qa/sessions", json={})
        session_id = create_resp.json()["id"]

        resp = admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": session_id,
                "conversation_id": "ADV-001",
                "turn_number": 1,
                "score_legal_accuracy": 0.0,
                "score_contextual_relevance": 4.0,
                "score_coherence": 4.0,
                "score_actionability": 4.0,
                "score_risk_awareness": 4.0,
                "score_citation_quality": 4.0,
                "score_language": 4.0,
                "score_completeness": 4.0,
            },
        )
        assert resp.status_code == 422

    def test_submit_evaluation_session_not_found(self, admin_client) -> None:
        """Submitting to a non-existent session returns 404."""
        resp = admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": 99999,
                "conversation_id": "ADV-001",
                "turn_number": 1,
                "score_legal_accuracy": 4.0,
                "score_contextual_relevance": 4.0,
                "score_coherence": 4.0,
                "score_actionability": 4.0,
                "score_risk_awareness": 4.0,
                "score_citation_quality": 4.0,
                "score_language": 4.0,
                "score_completeness": 4.0,
            },
        )
        assert resp.status_code == 404

    def test_submit_evaluation_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot submit evaluations."""
        resp = regular_user_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": 1,
                "conversation_id": "ADV-001",
                "turn_number": 1,
                "score_legal_accuracy": 4.0,
                "score_contextual_relevance": 4.0,
                "score_coherence": 4.0,
                "score_actionability": 4.0,
                "score_risk_awareness": 4.0,
                "score_citation_quality": 4.0,
                "score_language": 4.0,
                "score_completeness": 4.0,
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 6. GET /admin/qa/evaluations -- list evaluations
# ---------------------------------------------------------------------------


class TestListEvaluations:
    """GET /admin/qa/evaluations lists evaluations with optional filters."""

    def test_list_evaluations_empty(self, admin_client) -> None:
        """When no evaluations exist, returns empty list."""
        resp = admin_client.get("/admin/qa/evaluations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["evaluations"] == []
        assert data["total"] == 0

    def test_list_evaluations_returns_submitted(self, admin_client) -> None:
        """After submitting evaluations, they appear in the list."""
        # Create session and submit evaluation
        create_resp = admin_client.post("/admin/qa/sessions", json={})
        session_id = create_resp.json()["id"]

        admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": session_id,
                "conversation_id": "ADV-001",
                "turn_number": 1,
                "score_legal_accuracy": 4.0,
                "score_contextual_relevance": 4.0,
                "score_coherence": 4.0,
                "score_actionability": 4.0,
                "score_risk_awareness": 4.0,
                "score_citation_quality": 4.0,
                "score_language": 4.0,
                "score_completeness": 4.0,
            },
        )

        resp = admin_client.get("/admin/qa/evaluations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_list_evaluations_filter_by_session(self, admin_client) -> None:
        """Evaluations can be filtered by session_id."""
        # Create two sessions
        resp1 = admin_client.post("/admin/qa/sessions", json={})
        session_1_id = resp1.json()["id"]
        resp2 = admin_client.post("/admin/qa/sessions", json={})
        session_2_id = resp2.json()["id"]

        # Submit evaluation to session 1
        admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": session_1_id,
                "conversation_id": "ADV-001",
                "turn_number": 1,
                "score_legal_accuracy": 4.0,
                "score_contextual_relevance": 4.0,
                "score_coherence": 4.0,
                "score_actionability": 4.0,
                "score_risk_awareness": 4.0,
                "score_citation_quality": 4.0,
                "score_language": 4.0,
                "score_completeness": 4.0,
            },
        )

        # Submit evaluation to session 2
        admin_client.post(
            "/admin/qa/evaluations",
            json={
                "session_id": session_2_id,
                "conversation_id": "ADV-002",
                "turn_number": 1,
                "score_legal_accuracy": 3.0,
                "score_contextual_relevance": 3.0,
                "score_coherence": 3.0,
                "score_actionability": 3.0,
                "score_risk_awareness": 3.0,
                "score_citation_quality": 3.0,
                "score_language": 3.0,
                "score_completeness": 3.0,
            },
        )

        # Filter by session 1
        resp = admin_client.get(f"/admin/qa/evaluations?session_id={session_1_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["evaluations"][0]["session_id"] == session_1_id

    def test_list_evaluations_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot list evaluations."""
        resp = regular_user_client.get("/admin/qa/evaluations")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 7. GET /admin/qa/patches -- list patches
# ---------------------------------------------------------------------------


class TestListPatches:
    """GET /admin/qa/patches lists instruction patches."""

    def test_list_patches_empty(self, admin_client) -> None:
        """When no patches exist, returns empty list."""
        resp = admin_client.get("/admin/qa/patches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["patches"] == []
        assert data["total"] == 0

    def test_list_patches_with_data(self, admin_client) -> None:
        """When patches exist, they are returned."""
        from hr_advisory.api.routers.qa import _patches

        _patches[1] = {
            "id": 1,
            "target_agent": "employment_act_specialist",
            "patch_type": "qa_learned_rule",
            "old_text": None,
            "new_text": "Aggregate cap rule.",
            "evidence_count": 5,
            "evidence_ids": [1, 2, 3, 4, 5],
            "test_results": None,
            "status": "proposed",
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": None,
            "deployed_at": None,
            "approved_by": None,
        }

        resp = admin_client.get("/admin/qa/patches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["patches"][0]["target_agent"] == "employment_act_specialist"

    def test_list_patches_filter_by_status(self, admin_client) -> None:
        """Patches can be filtered by status."""
        from hr_advisory.api.routers.qa import _patches

        _patches[1] = {
            "id": 1,
            "target_agent": "ea_specialist",
            "patch_type": "rule",
            "old_text": None,
            "new_text": "Rule A.",
            "evidence_count": 3,
            "evidence_ids": [1, 2, 3],
            "test_results": None,
            "status": "proposed",
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": None,
            "deployed_at": None,
            "approved_by": None,
        }
        _patches[2] = {
            "id": 2,
            "target_agent": "cpf_specialist",
            "patch_type": "rule",
            "old_text": None,
            "new_text": "Rule B.",
            "evidence_count": 2,
            "evidence_ids": [4, 5],
            "test_results": None,
            "status": "approved",
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": datetime.now(tz=timezone.utc).isoformat(),
            "deployed_at": None,
            "approved_by": 10,
        }

        resp = admin_client.get("/admin/qa/patches?status=proposed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["patches"][0]["status"] == "proposed"

    def test_list_patches_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot list patches."""
        resp = regular_user_client.get("/admin/qa/patches")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 8. POST /admin/qa/patches/{id}/approve -- approve patch
# ---------------------------------------------------------------------------


class TestApprovePatch:
    """POST /admin/qa/patches/{id}/approve approves an instruction patch."""

    def test_approve_patch_success(self, admin_client) -> None:
        """Approving a ready_for_approval patch returns 200."""
        from hr_advisory.api.routers.qa import _patches

        _patches[1] = {
            "id": 1,
            "target_agent": "employment_act_specialist",
            "patch_type": "qa_learned_rule",
            "old_text": None,
            "new_text": "Aggregate cap rule.",
            "evidence_count": 5,
            "evidence_ids": [1, 2, 3, 4, 5],
            "test_results": {"scenarios_improved": 4, "scenarios_regressed": 0},
            "status": "ready_for_approval",
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": None,
            "deployed_at": None,
            "approved_by": None,
        }

        resp = admin_client.post("/admin/qa/patches/1/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == 10
        assert data["approved_at"] is not None

    def test_approve_patch_not_found(self, admin_client) -> None:
        """Approving a non-existent patch returns 404."""
        resp = admin_client.post("/admin/qa/patches/99999/approve")
        assert resp.status_code == 404

    def test_approve_already_approved_patch(self, admin_client) -> None:
        """Approving an already approved patch returns 400."""
        from hr_advisory.api.routers.qa import _patches

        _patches[1] = {
            "id": 1,
            "target_agent": "employment_act_specialist",
            "patch_type": "qa_learned_rule",
            "old_text": None,
            "new_text": "Rule.",
            "evidence_count": 3,
            "evidence_ids": [1, 2, 3],
            "test_results": None,
            "status": "approved",
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": datetime.now(tz=timezone.utc).isoformat(),
            "deployed_at": None,
            "approved_by": 10,
        }

        resp = admin_client.post("/admin/qa/patches/1/approve")
        assert resp.status_code == 400

    def test_approve_patch_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot approve patches."""
        resp = regular_user_client.post("/admin/qa/patches/1/approve")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 9. POST /admin/qa/patches/{id}/reject -- reject patch
# ---------------------------------------------------------------------------


class TestRejectPatch:
    """POST /admin/qa/patches/{id}/reject rejects an instruction patch."""

    def test_reject_patch_success(self, admin_client) -> None:
        """Rejecting a pending patch returns 200."""
        from hr_advisory.api.routers.qa import _patches

        _patches[1] = {
            "id": 1,
            "target_agent": "employment_act_specialist",
            "patch_type": "qa_learned_rule",
            "old_text": None,
            "new_text": "Rule.",
            "evidence_count": 3,
            "evidence_ids": [1, 2, 3],
            "test_results": None,
            "status": "ready_for_approval",
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": None,
            "deployed_at": None,
            "approved_by": None,
        }

        resp = admin_client.post("/admin/qa/patches/1/reject")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    def test_reject_patch_not_found(self, admin_client) -> None:
        """Rejecting a non-existent patch returns 404."""
        resp = admin_client.post("/admin/qa/patches/99999/reject")
        assert resp.status_code == 404

    def test_reject_already_rejected_patch(self, admin_client) -> None:
        """Rejecting an already rejected patch returns 400."""
        from hr_advisory.api.routers.qa import _patches

        _patches[1] = {
            "id": 1,
            "target_agent": "employment_act_specialist",
            "patch_type": "qa_learned_rule",
            "old_text": None,
            "new_text": "Rule.",
            "evidence_count": 3,
            "evidence_ids": [1, 2, 3],
            "test_results": None,
            "status": "rejected",
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": None,
            "deployed_at": None,
            "approved_by": None,
        }

        resp = admin_client.post("/admin/qa/patches/1/reject")
        assert resp.status_code == 400

    def test_reject_patch_non_admin_forbidden(self, regular_user_client) -> None:
        """Regular users cannot reject patches."""
        resp = regular_user_client.post("/admin/qa/patches/1/reject")
        assert resp.status_code == 403
