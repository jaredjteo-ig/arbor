"""Unit tests for recruitment rejection endpoint and audit trail.

Tests T-R025 (structured rejection endpoint) and T-R026 (audit trail for
stage transitions) covering:

1. POST /candidates/{id}/reject: structured rejection with reason
   - Requires a non-empty rejection reason
   - Updates candidate stage to "rejected" with rejection_reason
   - Prevents rejecting a hired candidate
   - Sends rejection email when candidate has email and send_email is not False
   - Skips email when send_email is explicitly False
   - Validates text lengths (reason, notes)
   - Tenant isolation (candidate ownership)
   - Returns 400 when no company associated
2. _log_candidate_activity: audit trail helper
   - Appends timestamped entries to candidate notes
   - Prepends new entries (newest first)
   - Handles candidates with no existing notes
   - Handles candidates with existing notes
   - Includes details when provided
   - No-ops when candidate not found
3. Audit trail integration:
   - reject_candidate logs activity
   - hire_candidate logs activity
   - update_candidate logs stage transitions
4. T-R019: Interview invitation email
   - schedule_interview sends interview_invitation email to candidate
5. T-R021: Candidate-to-employee data pre-fill on hire
   - hire_candidate includes phone, department, designation, salary from offer
6. T-R023: Auto-close job logging on hire
   - hire_candidate logs hired count for the job
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

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


def _fake_user(company_id: int = 1, role: str = "owner") -> dict:
    return {
        "sub": 10,
        "email": "hr@example.com",
        "role": role,
        "company_id": company_id,
    }


def _candidate_record(
    candidate_id: int = 1,
    company_id: int = 1,
    stage: str = "interview",
    email: str = "alice@example.com",
    name: str = "Alice Tan",
    job_listing_id: int = 1,
    notes: str = "",
) -> dict:
    return {
        "id": candidate_id,
        "company_id": company_id,
        "job_listing_id": job_listing_id,
        "name": name,
        "email": email,
        "phone": "+6591234567",
        "stage": stage,
        "notes": notes,
    }


def _job_record(job_id: int = 1, company_id: int = 1, title: str = "Software Engineer") -> dict:
    return {
        "id": job_id,
        "company_id": company_id,
        "title": title,
        "department": "Engineering",
    }


def _company_record(company_id: int = 1, name: str = "Acme Pte Ltd") -> dict:
    return {
        "id": company_id,
        "name": name,
    }


# ---------------------------------------------------------------------------
# T-R025: Structured rejection endpoint
# ---------------------------------------------------------------------------


class TestRejectCandidate:
    """Verify POST /candidates/{id}/reject endpoint."""

    def _setup_mocks(self, mock_crud, mock_company_id, candidate=None, job=None, company=None):
        """Common mock setup for rejection tests."""
        if candidate is None:
            candidate = _candidate_record()
        if job is None:
            job = _job_record()
        if company is None:
            company = _company_record()

        mock_company_id.return_value = 1

        def read_side_effect(model, record_id):
            if model == "Candidate":
                if record_id == candidate["id"]:
                    return candidate
                return None
            if model == "JobListing":
                return job
            if model == "Company":
                return company
            return None

        mock_crud.read.side_effect = read_side_effect
        mock_crud.update.return_value = {**candidate, "stage": "rejected", "rejection_reason": "Not a fit"}

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_success(self, mock_company_id, mock_crud, mock_send_email):
        """Reject a candidate with a valid reason updates stage and returns result."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        self._setup_mocks(mock_crud, mock_company_id)
        mock_send_email.return_value = True

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "Not a cultural fit"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "candidate" in data
        assert data["message"] == "Candidate rejected."

        # Verify update was called with rejection data
        update_calls = [c for c in mock_crud.update.call_args_list if c[0][0] == "Candidate" and c[0][1] == 1]
        assert len(update_calls) >= 1
        update_data = update_calls[0][0][2]
        assert update_data["stage"] == "rejected"
        assert update_data["rejection_reason"] == "Not a cultural fit"

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_sends_rejection_email(self, mock_company_id, mock_crud, mock_send_email):
        """Rejection sends a rejection_notice email to the candidate."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        self._setup_mocks(mock_crud, mock_company_id)
        mock_send_email.return_value = True

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "Position filled"},
        )
        assert resp.status_code == 200

        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert call_kwargs["to"] == "alice@example.com"
        assert call_kwargs["template_name"] == "rejection_notice"
        assert call_kwargs["variables"]["candidate_name"] == "Alice Tan"

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_skips_email_when_send_email_false(self, mock_company_id, mock_crud, mock_send_email):
        """When send_email is explicitly False, no rejection email is sent."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        self._setup_mocks(mock_crud, mock_company_id)

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "Not a fit", "send_email": False},
        )
        assert resp.status_code == 200
        mock_send_email.assert_not_called()

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_requires_reason(self, mock_company_id, mock_crud, mock_send_email):
        """Rejection without a reason returns 400."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        self._setup_mocks(mock_crud, mock_company_id)

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": ""},
        )
        assert resp.status_code == 400
        assert "reason" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_requires_reason_not_just_whitespace(self, mock_company_id, mock_crud, mock_send_email):
        """Rejection with whitespace-only reason returns 400."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        self._setup_mocks(mock_crud, mock_company_id)

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "   "},
        )
        assert resp.status_code == 400

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_hired_candidate_returns_400(self, mock_company_id, mock_crud, mock_send_email):
        """Cannot reject a candidate who is already hired."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        hired_candidate = _candidate_record(stage="hired")
        self._setup_mocks(mock_crud, mock_company_id, candidate=hired_candidate)

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "Changed mind"},
        )
        assert resp.status_code == 400
        assert "hired" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_with_notes(self, mock_company_id, mock_crud, mock_send_email):
        """Rejection with optional notes includes them in the update."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        self._setup_mocks(mock_crud, mock_company_id)
        mock_send_email.return_value = True

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "Overqualified", "notes": "Great candidate but salary expectations too high"},
        )
        assert resp.status_code == 200

        # Verify notes were included in the update
        update_calls = [c for c in mock_crud.update.call_args_list if c[0][0] == "Candidate" and c[0][1] == 1]
        assert len(update_calls) >= 1
        update_data = update_calls[0][0][2]
        assert update_data.get("notes") == "Great candidate but salary expectations too high"

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=None)
    def test_reject_candidate_no_company_returns_400(self, mock_company_id, mock_crud, mock_send_email):
        """Rejection without a company association returns 400."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "Not a fit"},
        )
        assert resp.status_code == 400
        assert "company" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_not_found_returns_404(self, mock_company_id, mock_crud, mock_send_email):
        """Rejection of non-existent candidate returns 404."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        mock_crud.read.return_value = None  # Candidate not found

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/999/reject",
            json={"reason": "Not a fit"},
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_candidate_reason_too_long_returns_400(self, mock_company_id, mock_crud, mock_send_email):
        """Rejection with an excessively long reason returns 400."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        self._setup_mocks(mock_crud, mock_company_id)

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "x" * 2001},
        )
        assert resp.status_code == 400
        assert "length" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# T-R026: Audit trail — _log_candidate_activity helper
# ---------------------------------------------------------------------------


class TestLogCandidateActivity:
    """Verify _log_candidate_activity helper creates audit entries."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_logs_activity_with_empty_notes(self, mock_crud):
        """Activity is logged when candidate has no existing notes."""
        from hr_advisory.api.routers.recruitment import _log_candidate_activity

        mock_crud.read.return_value = _candidate_record(notes="")

        _log_candidate_activity(1, "Rejected", 10, "Not a fit")

        mock_crud.update.assert_called_once()
        update_data = mock_crud.update.call_args[0][2]
        assert "Rejected" in update_data["notes"]
        assert "Not a fit" in update_data["notes"]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_logs_activity_prepends_to_existing_notes(self, mock_crud):
        """New activity entry is prepended to existing notes."""
        from hr_advisory.api.routers.recruitment import _log_candidate_activity

        mock_crud.read.return_value = _candidate_record(notes="Previous entry")

        _log_candidate_activity(1, "Hired", 10)

        mock_crud.update.assert_called_once()
        update_data = mock_crud.update.call_args[0][2]
        new_notes = update_data["notes"]
        # New entry at start, old entry at end
        assert new_notes.index("Hired") < new_notes.index("Previous entry")

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_logs_activity_includes_timestamp(self, mock_crud):
        """Activity entry includes a UTC timestamp."""
        from hr_advisory.api.routers.recruitment import _log_candidate_activity

        mock_crud.read.return_value = _candidate_record(notes="")

        _log_candidate_activity(1, "Stage changed", 10)

        update_data = mock_crud.update.call_args[0][2]
        # Timestamp format: [YYYY-MM-DD HH:MM UTC]
        assert "UTC" in update_data["notes"]
        assert "[" in update_data["notes"]
        assert "]" in update_data["notes"]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_logs_activity_includes_details_when_provided(self, mock_crud):
        """When details string is provided, it appears in the entry."""
        from hr_advisory.api.routers.recruitment import _log_candidate_activity

        mock_crud.read.return_value = _candidate_record(notes="")

        _log_candidate_activity(1, "Rejected", 10, "Salary mismatch")

        update_data = mock_crud.update.call_args[0][2]
        assert "Salary mismatch" in update_data["notes"]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_logs_activity_no_details_omits_dash(self, mock_crud):
        """When no details, entry does not include the separator dash."""
        from hr_advisory.api.routers.recruitment import _log_candidate_activity

        mock_crud.read.return_value = _candidate_record(notes="")

        _log_candidate_activity(1, "Hired", 10)

        update_data = mock_crud.update.call_args[0][2]
        # Should not contain the details separator when no details
        lines = update_data["notes"].strip().split("\n")
        assert len(lines) == 1
        # The line should end with the action, not have a trailing " -- "
        assert lines[0].strip().endswith("Hired")

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_logs_activity_noop_when_candidate_not_found(self, mock_crud):
        """When candidate does not exist, activity log is a no-op."""
        from hr_advisory.api.routers.recruitment import _log_candidate_activity

        mock_crud.read.return_value = None

        _log_candidate_activity(999, "Rejected", 10, "Not found")

        mock_crud.update.assert_not_called()


# ---------------------------------------------------------------------------
# T-R026: Audit trail integration — reject logs activity
# ---------------------------------------------------------------------------


class TestRejectCandidateAuditTrail:
    """Verify reject_candidate logs activity via _log_candidate_activity."""

    @patch("hr_advisory.api.routers.recruitment._log_candidate_activity")
    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_reject_logs_activity(self, mock_company_id, mock_crud, mock_send_email, mock_log):
        """reject_candidate calls _log_candidate_activity with reason."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        candidate = _candidate_record()
        mock_crud.read.side_effect = lambda model, record_id: {
            "Candidate": candidate,
            "JobListing": _job_record(),
            "Company": _company_record(),
        }.get(model)
        mock_crud.update.return_value = {**candidate, "stage": "rejected"}
        mock_send_email.return_value = True

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/reject",
            json={"reason": "Skills mismatch"},
        )
        assert resp.status_code == 200
        mock_log.assert_called_once_with(1, "Rejected", 10, "Skills mismatch")


# ---------------------------------------------------------------------------
# T-R026: Audit trail integration — hire logs activity
# ---------------------------------------------------------------------------


class TestHireCandidateAuditTrail:
    """Verify hire_candidate logs activity via _log_candidate_activity."""

    @patch("hr_advisory.api.routers.recruitment._log_candidate_activity")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    def test_hire_logs_activity(self, mock_rate_limit, mock_company_id, mock_crud, mock_log):
        """hire_candidate calls _log_candidate_activity."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        candidate = _candidate_record(stage="offered")
        mock_crud.read.side_effect = lambda model, record_id: {
            "Candidate": candidate,
            "JobListing": _job_record(),
            "Company": _company_record(),
        }.get(model)
        mock_crud.create.return_value = {"id": 100, "token": "abc"}
        mock_crud.update.return_value = {**candidate, "stage": "hired"}
        mock_crud.list_records.return_value = []

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/hire",
            json={},
        )
        assert resp.status_code == 200
        mock_log.assert_called_once_with(1, "Hired", 10)


# ---------------------------------------------------------------------------
# T-R026: Audit trail integration — update_candidate logs stage changes
# ---------------------------------------------------------------------------


class TestUpdateCandidateAuditTrail:
    """Verify PATCH /candidates/{id} logs activity when stage changes."""

    @patch("hr_advisory.api.routers.recruitment._log_candidate_activity")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_stage_change_logs_activity(self, mock_company_id, mock_crud, mock_log):
        """When stage changes in PATCH, activity is logged."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        candidate = _candidate_record(stage="applied")
        mock_crud.read.return_value = candidate
        mock_crud.update.return_value = {**candidate, "stage": "interview"}

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.patch(
            "/recruitment/candidates/1",
            json={"stage": "interview"},
        )
        assert resp.status_code == 200
        mock_log.assert_called_once_with(1, "Stage changed to interview", 10)

    @patch("hr_advisory.api.routers.recruitment._log_candidate_activity")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_no_stage_change_does_not_log(self, mock_company_id, mock_crud, mock_log):
        """When stage does not change in PATCH, no activity is logged."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        candidate = _candidate_record(stage="applied")
        mock_crud.read.return_value = candidate
        mock_crud.update.return_value = {**candidate, "notes": "Updated notes"}

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.patch(
            "/recruitment/candidates/1",
            json={"notes": "Updated notes"},
        )
        assert resp.status_code == 200
        mock_log.assert_not_called()


# ---------------------------------------------------------------------------
# T-R019: Interview invitation email
# ---------------------------------------------------------------------------


class TestScheduleInterviewEmail:
    """Verify schedule_interview sends interview_invitation email."""

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_schedule_interview_sends_email(self, mock_company_id, mock_crud, mock_send_email):
        """When interview is scheduled, interview_invitation email is sent to candidate."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        candidate = _candidate_record()
        job = _job_record()
        company = _company_record()

        def read_side_effect(model, record_id):
            if model == "Candidate":
                return candidate
            if model == "JobListing":
                return job
            if model == "Company":
                return company
            return None

        mock_crud.read.side_effect = read_side_effect
        mock_crud.create.return_value = {"id": 50, "status": "scheduled"}
        mock_crud.update.return_value = {**candidate, "stage": "interview"}
        mock_send_email.return_value = True

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/interviews",
            json={
                "scheduled_at": "2026-04-20T10:00:00",
                "duration_minutes": 45,
                "interview_type": "video",
                "location": "https://meet.example.com/abc",
            },
        )
        assert resp.status_code == 200

        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        assert call_kwargs["to"] == "alice@example.com"
        assert call_kwargs["template_name"] == "interview_invitation"
        assert call_kwargs["variables"]["candidate_name"] == "Alice Tan"
        assert call_kwargs["variables"]["job_title"] == "Software Engineer"
        assert call_kwargs["variables"]["company_name"] == "Acme Pte Ltd"
        assert call_kwargs["variables"]["interview_date"] == "2026-04-20"
        assert call_kwargs["variables"]["interview_time"] == "10:00"
        assert call_kwargs["variables"]["duration"] == "45"
        assert call_kwargs["variables"]["interview_format"] == "video"
        assert call_kwargs["variables"]["location_or_link"] == "https://meet.example.com/abc"

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_schedule_interview_no_email_when_candidate_has_no_email(self, mock_company_id, mock_crud, mock_send_email):
        """When candidate has no email, no interview invitation is sent."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        candidate = _candidate_record(email="")
        mock_crud.read.side_effect = lambda model, record_id: candidate if model == "Candidate" else None
        mock_crud.create.return_value = {"id": 50, "status": "scheduled"}
        mock_crud.update.return_value = {**candidate, "stage": "interview"}

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/interviews",
            json={"scheduled_at": "2026-04-20T10:00:00"},
        )
        assert resp.status_code == 200
        mock_send_email.assert_not_called()


# ---------------------------------------------------------------------------
# T-R021: Candidate-to-employee data pre-fill on hire
# ---------------------------------------------------------------------------


class TestHireCandidateDataPrefill:
    """Verify hire_candidate creates invitation with full candidate data."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    def test_hire_prefills_invitation_with_candidate_data(self, mock_rate_limit, mock_company_id, mock_crud):
        """Invitation includes phone, department, designation, salary from offer."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        candidate = _candidate_record(stage="offered")
        job = _job_record(title="Senior Engineer")
        offer = {
            "id": 10,
            "candidate_id": 1,
            "company_id": 1,
            "salary": 8000.0,
        }

        def read_side_effect(model, record_id):
            if model == "Candidate":
                return candidate
            if model == "JobListing":
                return job
            if model == "Company":
                return _company_record()
            return None

        mock_crud.read.side_effect = read_side_effect
        mock_crud.list_records.return_value = [offer]
        mock_crud.create.return_value = {"id": 100, "token": "abc"}
        mock_crud.update.return_value = {**candidate, "stage": "hired"}

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        resp = client.post(
            "/recruitment/candidates/1/hire",
            json={"department": "Engineering", "designation": "Senior Engineer"},
        )
        assert resp.status_code == 200

        # Verify create was called with enriched invitation data
        create_calls = [c for c in mock_crud.create.call_args_list if c[0][0] == "Invitation"]
        assert len(create_calls) == 1
        invitation_data = create_calls[0][0][1]
        assert invitation_data["email"] == "alice@example.com"
        assert invitation_data["name"] == "Alice Tan"
        assert invitation_data["phone"] == "+6591234567"
        assert invitation_data["department"] == "Engineering"
        assert invitation_data["designation"] == "Senior Engineer"
        assert invitation_data["salary"] == 8000.0


# ---------------------------------------------------------------------------
# T-R023: Auto-close job logging on hire
# ---------------------------------------------------------------------------


class TestHireCandidateJobLogging:
    """Verify hire_candidate logs hired count for job auto-close tracking."""

    @patch("hr_advisory.api.routers.recruitment._log_candidate_activity")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    def test_hire_logs_hired_count(self, mock_rate_limit, mock_company_id, mock_crud, mock_log, caplog):
        """hire_candidate logs the number of hired candidates for the job."""
        from hr_advisory.api.middleware.auth_middleware import get_current_user
        import logging

        candidate = _candidate_record(stage="offered")
        job = _job_record()

        def read_side_effect(model, record_id):
            if model == "Candidate":
                return candidate
            if model == "JobListing":
                return job
            if model == "Company":
                return _company_record()
            return None

        mock_crud.read.side_effect = read_side_effect
        # list_records called for offers first, then for all_candidates
        mock_crud.list_records.side_effect = [
            [],  # offers
            [_candidate_record(stage="hired"), _candidate_record(candidate_id=2, stage="interview")],  # all candidates
        ]
        mock_crud.create.return_value = {"id": 100, "token": "abc"}
        mock_crud.update.return_value = {**candidate, "stage": "hired"}

        app = _make_app()
        app.dependency_overrides[get_current_user] = lambda: _fake_user()
        client = TestClient(app)

        with caplog.at_level(logging.INFO, logger="hr_advisory.api.routers.recruitment"):
            resp = client.post(
                "/recruitment/candidates/1/hire",
                json={},
            )
        assert resp.status_code == 200
        # Verify logging occurred — the exact message contains the job id and count
        assert any("hired candidates" in record.message.lower() for record in caplog.records)
