"""Unit tests for the learning pipeline router endpoints.

Tests the admin-facing learning pipeline endpoints that expose:
1. GET /admin/learning/gaps -- KB gap listing with priority filter
2. GET /admin/learning/recommendations -- recommendation listing with status filter
3. POST /admin/learning/recommendations/{id}/apply -- apply approved recommendation
4. GET /admin/learning/patterns -- query pattern summary
5. GET /admin/learning/feedback -- feedback summary
6. GET /admin/learning/report -- latest monthly report
7. POST /admin/learning/feedback -- record new feedback
8. Auth enforcement: all endpoints require admin role (owner or hr_manager)
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.routers.learning import router
from hr_advisory.trust.learning_pipeline import (
    FeedbackCategory,
    RecommendationStatus,
    RecommendationType,
    _feedback_records,
    _kb_gaps,
    _monthly_reports,
    _query_patterns,
    _recommendations,
    _resolution_patterns,
    _routing_insights,
    detect_kb_gap,
    propose_recommendation,
    record_feedback,
    record_query_pattern,
    review_recommendation,
)


# ---------------------------------------------------------------------------
# Helpers and fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the learning router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/learning")
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


@pytest.fixture(autouse=True)
def _clean_learning_stores():
    """Clear in-memory learning stores before each test."""
    _feedback_records.clear()
    _kb_gaps.clear()
    _monthly_reports.clear()
    _query_patterns.clear()
    _recommendations.clear()
    _resolution_patterns.clear()
    _routing_insights.clear()
    yield
    _feedback_records.clear()
    _kb_gaps.clear()
    _monthly_reports.clear()
    _query_patterns.clear()
    _recommendations.clear()
    _resolution_patterns.clear()
    _routing_insights.clear()


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
    """Test client with regular user auth (employee role)."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_regular_user()
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. GET /admin/learning/gaps -- KB gap listing
# ---------------------------------------------------------------------------


class TestAdminKbGaps:
    """GET /learning/admin/gaps returns KB gaps for admin users."""

    def test_returns_empty_list_when_no_gaps(self, admin_client):
        """When no gaps exist, returns empty list with total=0."""
        resp = admin_client.get("/learning/admin/gaps")
        assert resp.status_code == 200
        data = resp.json()
        assert data["gaps"] == []
        assert data["total"] == 0

    def test_returns_all_gaps(self, admin_client):
        """Returns all detected KB gaps."""
        detect_kb_gap("g-1", ["cpf"], "Missing CPF data", 10, 0.4, 5)
        detect_kb_gap("g-2", ["employment_act"], "Unclear provision", 5, 0.6, 3)
        resp = admin_client.get("/learning/admin/gaps")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["gaps"]) == 2

    def test_filter_by_priority(self, admin_client):
        """Supports priority filter parameter."""
        detect_kb_gap("g-1", ["cpf"], "Critical gap", 50, 0.2, 12)
        detect_kb_gap("g-2", ["employment_act"], "Low gap", 2, 0.8, 1)
        resp = admin_client.get("/learning/admin/gaps?priority=critical")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["gaps"][0]["gap_id"] == "g-1"

    def test_invalid_priority_returns_400(self, admin_client):
        """Invalid priority value returns 400."""
        resp = admin_client.get("/learning/admin/gaps?priority=invalid")
        assert resp.status_code == 400

    def test_gap_response_structure(self, admin_client):
        """Each gap entry contains all required fields."""
        detect_kb_gap("g-1", ["cpf"], "Missing data", 10, 0.4, 5, ["Add CPF tables"])
        resp = admin_client.get("/learning/admin/gaps")
        data = resp.json()
        gap = data["gaps"][0]
        assert "gap_id" in gap
        assert "domains" in gap
        assert "description" in gap
        assert "evidence_query_count" in gap
        assert "avg_confidence" in gap
        assert "negative_feedback_count" in gap
        assert "priority" in gap
        assert "detected_at" in gap
        assert "suggested_provisions" in gap

    def test_requires_admin_role(self, regular_user_client):
        """Non-admin users get 403."""
        resp = regular_user_client.get("/learning/admin/gaps")
        assert resp.status_code == 403

    def test_hr_manager_can_access(self, hr_manager_client):
        """HR managers can access admin learning endpoints."""
        resp = hr_manager_client.get("/learning/admin/gaps")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2. GET /admin/learning/recommendations -- recommendation listing
# ---------------------------------------------------------------------------


class TestAdminRecommendations:
    """GET /learning/admin/recommendations returns recommendations for admin."""

    def test_returns_empty_when_no_recommendations(self, admin_client):
        """When no recommendations exist, returns empty list."""
        resp = admin_client.get("/learning/admin/recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommendations"] == []
        assert data["total"] == 0

    def test_returns_all_recommendations(self, admin_client):
        """Returns all recommendations without filter."""
        propose_recommendation(
            "rec-1",
            RecommendationType.KB_EXPANSION,
            "Title 1",
            "Desc 1",
            5,
            ["cpf"],
            "high",
        )
        propose_recommendation(
            "rec-2",
            RecommendationType.KB_CORRECTION,
            "Title 2",
            "Desc 2",
            3,
            ["employment_act"],
            "medium",
        )
        resp = admin_client.get("/learning/admin/recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_filter_by_status(self, admin_client):
        """Supports status filter parameter."""
        propose_recommendation(
            "rec-1",
            RecommendationType.KB_EXPANSION,
            "Title 1",
            "Desc 1",
            5,
            ["cpf"],
            "high",
        )
        propose_recommendation(
            "rec-2",
            RecommendationType.KB_CORRECTION,
            "Title 2",
            "Desc 2",
            3,
            ["employment_act"],
            "medium",
        )
        review_recommendation("rec-2", approved=True, reviewed_by="admin@example.com")

        resp = admin_client.get("/learning/admin/recommendations?status=approved")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["recommendations"][0]["recommendation_id"] == "rec-2"

    def test_invalid_status_returns_400(self, admin_client):
        """Invalid status value returns 400."""
        resp = admin_client.get("/learning/admin/recommendations?status=invalid_status")
        assert resp.status_code == 400

    def test_recommendation_response_structure(self, admin_client):
        """Each recommendation entry contains all required fields."""
        propose_recommendation(
            "rec-1",
            RecommendationType.KB_EXPANSION,
            "Add S Pass tables",
            "Missing data for 2026",
            12,
            ["foreign_manpower"],
            "high",
        )
        resp = admin_client.get("/learning/admin/recommendations")
        data = resp.json()
        rec = data["recommendations"][0]
        assert "recommendation_id" in rec
        assert "type" in rec
        assert "title" in rec
        assert "description" in rec
        assert "priority" in rec
        assert "evidence_count" in rec
        assert "affected_domains" in rec
        assert "status" in rec
        assert "proposed_at" in rec

    def test_requires_admin_role(self, regular_user_client):
        """Non-admin users get 403."""
        resp = regular_user_client.get("/learning/admin/recommendations")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 3. POST /admin/learning/recommendations/{id}/apply -- apply recommendation
# ---------------------------------------------------------------------------


class TestApplyRecommendation:
    """POST /learning/admin/recommendations/{id}/apply applies a recommendation."""

    def test_apply_approved_recommendation(self, admin_client):
        """Applying an approved recommendation changes status to IMPLEMENTED."""
        propose_recommendation(
            "rec-1",
            RecommendationType.KB_EXPANSION,
            "Add tables",
            "Missing data",
            10,
            ["cpf"],
            "high",
        )
        review_recommendation("rec-1", approved=True, reviewed_by="admin@example.com")

        resp = admin_client.post(
            "/learning/admin/recommendations/rec-1/apply",
            json={"notes": "Applied and verified"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommendation_id"] == "rec-1"
        assert data["status"] == "implemented"
        assert data["applied"] is True

    def test_apply_non_approved_returns_400(self, admin_client):
        """Cannot apply a recommendation that has not been approved."""
        propose_recommendation(
            "rec-2",
            RecommendationType.KB_CORRECTION,
            "Fix data",
            "Wrong info",
            5,
            ["cpf"],
            "medium",
        )
        resp = admin_client.post(
            "/learning/admin/recommendations/rec-2/apply",
            json={},
        )
        assert resp.status_code == 400
        assert "approved" in resp.json()["detail"].lower()

    def test_apply_nonexistent_returns_404(self, admin_client):
        """Applying a nonexistent recommendation returns 404."""
        resp = admin_client.post(
            "/learning/admin/recommendations/nonexistent/apply",
            json={},
        )
        assert resp.status_code == 404

    def test_apply_already_implemented_returns_400(self, admin_client):
        """Cannot apply an already-implemented recommendation."""
        propose_recommendation(
            "rec-3",
            RecommendationType.KB_EXPANSION,
            "Title",
            "Desc",
            5,
            ["cpf"],
            "high",
        )
        review_recommendation("rec-3", approved=True, reviewed_by="admin@example.com")
        # Apply once
        admin_client.post("/learning/admin/recommendations/rec-3/apply", json={})
        # Try to apply again
        resp = admin_client.post("/learning/admin/recommendations/rec-3/apply", json={})
        assert resp.status_code == 400
        assert (
            "already" in resp.json()["detail"].lower()
            or "implemented" in resp.json()["detail"].lower()
        )

    def test_requires_admin_role(self, regular_user_client):
        """Non-admin users get 403."""
        resp = regular_user_client.post("/learning/admin/recommendations/rec-1/apply", json={})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. GET /admin/learning/patterns -- query patterns summary
# ---------------------------------------------------------------------------


class TestAdminQueryPatterns:
    """GET /learning/admin/patterns returns query pattern summary."""

    def test_returns_empty_when_no_patterns(self, admin_client):
        """When no patterns exist, returns empty list."""
        resp = admin_client.get("/learning/admin/patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert data["patterns"] == []
        assert data["total"] == 0

    def test_returns_all_patterns(self, admin_client):
        """Returns all tracked query patterns."""
        record_query_pattern("cpf:green", "CPF green", ["cpf"], 0.9, 1.0, "What are CPF rates?")
        record_query_pattern("ea:amber", "EA amber", ["employment_act"], 0.6, 0.5)
        resp = admin_client.get("/learning/admin/patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["patterns"]) == 2

    def test_pattern_response_structure(self, admin_client):
        """Each pattern entry contains all required fields."""
        record_query_pattern("cpf:green", "CPF queries", ["cpf"], 0.9, 1.0, "What are CPF rates?")
        resp = admin_client.get("/learning/admin/patterns")
        data = resp.json()
        pattern = data["patterns"][0]
        assert "pattern_id" in pattern
        assert "description" in pattern
        assert "domains" in pattern
        assert "frequency" in pattern
        assert "avg_confidence" in pattern
        assert "avg_satisfaction" in pattern
        assert "first_seen" in pattern
        assert "last_seen" in pattern
        assert "example_queries" in pattern

    def test_patterns_sorted_by_frequency(self, admin_client):
        """Patterns are sorted by frequency descending."""
        record_query_pattern("cpf:green", "CPF", ["cpf"], 0.9, 1.0)
        record_query_pattern("cpf:green", "CPF", ["cpf"], 0.8, 0.9)
        record_query_pattern("cpf:green", "CPF", ["cpf"], 0.85, 0.95)
        record_query_pattern("ea:green", "EA", ["employment_act"], 0.7, 1.0)

        resp = admin_client.get("/learning/admin/patterns")
        data = resp.json()
        assert data["patterns"][0]["pattern_id"] == "cpf:green"
        assert data["patterns"][0]["frequency"] == 3
        assert data["patterns"][1]["pattern_id"] == "ea:green"
        assert data["patterns"][1]["frequency"] == 1

    def test_requires_admin_role(self, regular_user_client):
        """Non-admin users get 403."""
        resp = regular_user_client.get("/learning/admin/patterns")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 5. GET /admin/learning/feedback -- feedback summary
# ---------------------------------------------------------------------------


class TestAdminFeedbackSummary:
    """GET /learning/admin/feedback returns feedback summary."""

    def test_returns_empty_summary(self, admin_client):
        """When no feedback exists, returns zeros."""
        resp = admin_client.get("/learning/admin/feedback")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_feedback"] == 0
        assert data["positive_count"] == 0
        assert data["negative_count"] == 0

    def test_returns_correct_counts(self, admin_client):
        """Returns accurate counts of positive and negative feedback."""
        record_feedback("fb-1", "s-1", is_positive=True)
        record_feedback("fb-2", "s-2", is_positive=True)
        record_feedback("fb-3", "s-3", is_positive=False, category=FeedbackCategory.WRONG_ANSWER)
        record_feedback("fb-4", "s-4", is_positive=False, category=FeedbackCategory.OUTDATED_INFO)

        resp = admin_client.get("/learning/admin/feedback")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_feedback"] == 4
        assert data["positive_count"] == 2
        assert data["negative_count"] == 2
        assert data["positive_rate"] == pytest.approx(0.5, abs=0.01)

    def test_includes_category_breakdown(self, admin_client):
        """Includes breakdown of negative feedback by category."""
        record_feedback("fb-1", "s-1", is_positive=False, category=FeedbackCategory.WRONG_ANSWER)
        record_feedback("fb-2", "s-2", is_positive=False, category=FeedbackCategory.WRONG_ANSWER)
        record_feedback("fb-3", "s-3", is_positive=False, category=FeedbackCategory.OUTDATED_INFO)
        record_feedback("fb-4", "s-4", is_positive=True)

        resp = admin_client.get("/learning/admin/feedback")
        data = resp.json()
        assert "category_breakdown" in data
        assert data["category_breakdown"]["wrong_answer"] == 2
        assert data["category_breakdown"]["outdated_info"] == 1

    def test_includes_recent_feedback(self, admin_client):
        """Includes list of recent feedback records."""
        record_feedback("fb-1", "s-1", is_positive=True)
        record_feedback("fb-2", "s-2", is_positive=False, category=FeedbackCategory.WRONG_ANSWER)

        resp = admin_client.get("/learning/admin/feedback")
        data = resp.json()
        assert "recent" in data
        assert len(data["recent"]) == 2

    def test_requires_admin_role(self, regular_user_client):
        """Non-admin users get 403."""
        resp = regular_user_client.get("/learning/admin/feedback")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 6. GET /admin/learning/report -- latest monthly report
# ---------------------------------------------------------------------------


class TestAdminReport:
    """GET /learning/admin/report returns the latest monthly report."""

    def test_no_reports_returns_empty_placeholder(self, admin_client):
        """When no reports have been generated, returns 200 with empty placeholder."""
        resp = admin_client.get("/learning/admin/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["empty"] is True
        assert data["report_id"] is None
        assert data["total_queries"] == 0

    def test_returns_latest_report(self, admin_client):
        """Returns the most recently generated report."""
        from hr_advisory.trust.learning_pipeline import generate_monthly_report

        generate_monthly_report("report-1", "2026-01", 100)
        generate_monthly_report("report-2", "2026-02", 200)

        resp = admin_client.get("/learning/admin/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == "report-2"
        assert data["period"] == "2026-02"
        assert data["total_queries"] == 200

    def test_report_response_structure(self, admin_client):
        """Report response contains all required fields."""
        from hr_advisory.trust.learning_pipeline import generate_monthly_report

        record_feedback("fb-1", "s-1", is_positive=True)
        generate_monthly_report("report-1", "2026-03", 150)

        resp = admin_client.get("/learning/admin/report")
        data = resp.json()
        assert "report_id" in data
        assert "period" in data
        assert "total_queries" in data
        assert "total_feedback" in data
        assert "positive_feedback_rate" in data
        assert "kb_gaps_count" in data
        assert "recommendations_count" in data
        assert "generated_at" in data

    def test_requires_admin_role(self, regular_user_client):
        """Non-admin users get 403."""
        resp = regular_user_client.get("/learning/admin/report")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 7. POST /admin/learning/feedback -- record new feedback (admin)
# ---------------------------------------------------------------------------


class TestAdminRecordFeedback:
    """POST /learning/admin/feedback records new feedback via admin endpoint."""

    def test_record_positive_feedback(self, admin_client):
        """Records positive feedback and returns confirmation."""
        resp = admin_client.post(
            "/learning/admin/feedback",
            json={
                "session_id": "sess-001",
                "is_positive": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recorded"] is True
        assert "feedback_id" in data
        assert "timestamp" in data

    def test_record_negative_feedback_with_category(self, admin_client):
        """Records negative feedback with a category."""
        resp = admin_client.post(
            "/learning/admin/feedback",
            json={
                "session_id": "sess-002",
                "is_positive": False,
                "category": "wrong_answer",
                "domains": ["cpf"],
                "query_snippet": "How much CPF?",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recorded"] is True

    def test_missing_session_id_generates_uuid(self, admin_client):
        """Missing session_id auto-generates a UUID and succeeds."""
        resp = admin_client.post(
            "/learning/admin/feedback",
            json={
                "is_positive": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("recorded") is True
        assert "feedback_id" in data

    def test_invalid_category_returns_400(self, admin_client):
        """Invalid feedback category returns 400 error."""
        resp = admin_client.post(
            "/learning/admin/feedback",
            json={
                "session_id": "sess-003",
                "is_positive": False,
                "category": "nonexistent_category",
            },
        )
        assert resp.status_code == 400
        assert (
            "category" in resp.json()["detail"].lower() or "valid" in resp.json()["detail"].lower()
        )

    def test_requires_admin_role(self, regular_user_client):
        """Non-admin users get 403."""
        resp = regular_user_client.post(
            "/learning/admin/feedback",
            json={"session_id": "s", "is_positive": True},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 8. Auth enforcement -- existing endpoints still work
# ---------------------------------------------------------------------------


class TestExistingEndpointsPreserved:
    """Verify existing learning router endpoints still function correctly.

    These are the non-admin endpoints that were already present.
    """

    def test_feedback_submission_still_works(self, admin_client):
        """POST /learning/feedback still accepts feedback from authenticated users."""
        resp = admin_client.post(
            "/learning/feedback",
            json={
                "session_id": "sess-001",
                "is_positive": True,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["recorded"] is True

    def test_gaps_endpoint_still_works(self, admin_client):
        """GET /learning/gaps still returns gaps for authenticated users."""
        resp = admin_client.get("/learning/gaps")
        assert resp.status_code == 200

    def test_recommendations_endpoint_still_works(self, admin_client):
        """GET /learning/recommendations still returns recs for authenticated users."""
        resp = admin_client.get("/learning/recommendations")
        assert resp.status_code == 200

    def test_reports_endpoint_still_works(self, admin_client):
        """GET /learning/reports still returns reports for owner/hr_manager users."""
        resp = admin_client.get("/learning/reports")
        assert resp.status_code == 200
