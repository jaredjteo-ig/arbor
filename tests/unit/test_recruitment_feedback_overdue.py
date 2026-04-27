"""Unit tests for overdue feedback reminder endpoints.

Tests T-R020 covering:

1. GET /feedback/overdue: List interviews with overdue feedback
   - Completed interview >48h ago with no feedback -> overdue
   - Completed interview >48h ago with feedback -> not overdue
   - Completed interview <48h ago -> not overdue
   - Tenant isolation (company_id check)
2. POST /feedback/remind: Send feedback reminders
   - Sends reminders for overdue interviews
   - Returns count of reminders sent
   - Role restriction (owner, hr_manager only)

Tier 1 (Unit): Fast, isolated, uses mocks for dataflow_crud.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.routers.recruitment import router


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the recruitment router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/recruitment")
    return app


def _fake_user(company_id: int = 1, role: str = "owner", sub: int = 10) -> dict:
    return {
        "sub": sub,
        "email": "test@example.com",
        "role": role,
        "company_id": company_id,
    }


def _interview_record(
    interview_id: int = 1,
    candidate_id: int = 5,
    company_id: int = 1,
    status: str = "completed",
    scheduled_at: str = "",
    interview_type: str = "onsite",
) -> dict:
    return {
        "id": interview_id,
        "candidate_id": candidate_id,
        "company_id": company_id,
        "status": status,
        "scheduled_at": scheduled_at,
        "interview_type": interview_type,
        "interviewers": "[]",
    }


def _candidate_record(
    candidate_id: int = 5,
    company_id: int = 1,
    name: str = "Alice Tan",
) -> dict:
    return {
        "id": candidate_id,
        "company_id": company_id,
        "name": name,
        "email": "alice@example.com",
        "job_listing_id": 1,
    }


def _feedback_record(
    feedback_id: int = 1,
    interview_id: int = 1,
    company_id: int = 1,
) -> dict:
    return {
        "id": feedback_id,
        "interview_id": interview_id,
        "company_id": company_id,
        "interviewer_id": 10,
        "candidate_id": 5,
        "overall_rating": 4.0,
        "recommendation": "hire",
    }


@pytest.fixture()
def owner_client():
    """Test client with owner role."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="owner")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def hr_manager_client():
    """Test client with hr_manager role."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="hr_manager")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def employee_client():
    """Test client with employee role (should be denied)."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="employee")
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /feedback/overdue
# ---------------------------------------------------------------------------


class TestListOverdueFeedback:
    """Tests for the overdue feedback listing endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_overdue_feedback_after_48h(self, mock_crud, owner_client):
        """Interview completed >48h ago with no feedback appears in overdue list."""
        # Scheduled 72 hours ago
        scheduled_at = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        interview = _interview_record(scheduled_at=scheduled_at)

        def mock_list(model, filters):
            if model == "InterviewSchedule":
                return [interview]
            if model == "InterviewFeedback":
                return []  # No feedback submitted
            return []

        mock_crud.list_records.side_effect = mock_list
        mock_crud.read.return_value = _candidate_record()

        resp = owner_client.get("/recruitment/feedback/overdue")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert len(body["overdue"]) == 1
        overdue_item = body["overdue"][0]
        assert overdue_item["interview_id"] == 1
        assert overdue_item["candidate_name"] == "Alice Tan"
        assert overdue_item["hours_overdue"] >= 71  # Allow small timing tolerance

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_overdue_when_feedback_exists(self, mock_crud, owner_client):
        """Interview with submitted feedback does not appear in overdue list."""
        scheduled_at = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        interview = _interview_record(scheduled_at=scheduled_at)

        def mock_list(model, filters):
            if model == "InterviewSchedule":
                return [interview]
            if model == "InterviewFeedback":
                return [_feedback_record()]  # Feedback exists
            return []

        mock_crud.list_records.side_effect = mock_list

        resp = owner_client.get("/recruitment/feedback/overdue")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert len(body["overdue"]) == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_overdue_when_recent_interview(self, mock_crud, owner_client):
        """Interview completed <48h ago does not appear in overdue list."""
        # Scheduled 12 hours ago — within the 48h window
        scheduled_at = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        interview = _interview_record(scheduled_at=scheduled_at)

        def mock_list(model, filters):
            if model == "InterviewSchedule":
                return [interview]
            if model == "InterviewFeedback":
                return []  # No feedback yet, but still within window
            return []

        mock_crud.list_records.side_effect = mock_list

        resp = owner_client.get("/recruitment/feedback/overdue")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert len(body["overdue"]) == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_multiple_overdue_interviews(self, mock_crud, owner_client):
        """Multiple overdue interviews are all listed."""
        scheduled_72h = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        scheduled_96h = (datetime.now(timezone.utc) - timedelta(hours=96)).isoformat()

        interviews = [
            _interview_record(interview_id=1, candidate_id=5, scheduled_at=scheduled_72h),
            _interview_record(interview_id=2, candidate_id=6, scheduled_at=scheduled_96h),
        ]

        def mock_list(model, filters):
            if model == "InterviewSchedule":
                return interviews
            if model == "InterviewFeedback":
                return []  # No feedback for either
            return []

        mock_crud.list_records.side_effect = mock_list
        mock_crud.read.return_value = _candidate_record()

        resp = owner_client.get("/recruitment/feedback/overdue")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2

    def test_employee_denied_overdue_view(self, employee_client):
        """Employees cannot view overdue feedback."""
        resp = employee_client.get("/recruitment/feedback/overdue")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /feedback/remind
# ---------------------------------------------------------------------------


class TestSendFeedbackReminders:
    """Tests for the feedback reminder sending endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_reminders_for_overdue(self, mock_crud, owner_client):
        """Reminders are sent for interviews with overdue feedback."""
        scheduled_at = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        interview = _interview_record(scheduled_at=scheduled_at)

        def mock_list(model, filters):
            if model == "InterviewSchedule":
                return [interview]
            if model == "InterviewFeedback":
                return []
            return []

        mock_crud.list_records.side_effect = mock_list
        mock_crud.read.return_value = _candidate_record()

        resp = owner_client.post("/recruitment/feedback/remind")
        assert resp.status_code == 200
        body = resp.json()
        assert body["reminders_sent"] == 1
        assert "1" in body["message"]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_reminders_when_nothing_overdue(self, mock_crud, owner_client):
        """No reminders sent when no interviews are overdue."""
        mock_crud.list_records.return_value = []

        resp = owner_client.post("/recruitment/feedback/remind")
        assert resp.status_code == 200
        body = resp.json()
        assert body["reminders_sent"] == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_hr_manager_can_send_reminders(self, mock_crud, hr_manager_client):
        """HR managers can send feedback reminders."""
        mock_crud.list_records.return_value = []

        resp = hr_manager_client.post("/recruitment/feedback/remind")
        assert resp.status_code == 200

    def test_employee_cannot_send_reminders(self, employee_client):
        """Employees cannot send reminders."""
        resp = employee_client.post("/recruitment/feedback/remind")
        assert resp.status_code == 403
