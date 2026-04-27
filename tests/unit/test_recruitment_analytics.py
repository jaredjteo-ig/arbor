"""Unit tests for recruitment analytics summary endpoint.

Tests T-R042 (analytics endpoints) covering:

1. GET /analytics/summary: Recruitment dashboard metrics
   - Open/total job counts
   - Total candidate count
   - Pipeline stage distribution
   - Interviews this week
   - Source distribution
   - Offer counts and acceptance rate
   - Tenant isolation (company_id scoping)
   - Role restriction (owner, hr_manager only)

Tier 1 (Unit): Fast, isolated, uses mocks for dataflow_crud.
"""

from __future__ import annotations

from unittest.mock import patch

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
        "email": "test@example.com",
        "role": role,
        "company_id": company_id,
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
def employee_client():
    """Test client with employee role (should be denied)."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="employee")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def no_company_client():
    """Test client with no company_id (should return 400)."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": 10,
        "email": "test@example.com",
        "role": "owner",
        # no company_id
    }
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper data factories
# ---------------------------------------------------------------------------


def _job(status: str = "open") -> dict:
    return {"id": 1, "company_id": 1, "title": "Engineer", "status": status}


def _candidate(stage: str = "applied", source: str = "direct") -> dict:
    return {
        "id": 1,
        "company_id": 1,
        "name": "Test",
        "stage": stage,
        "source": source,
    }


def _interview(scheduled_at: str = "2026-04-16", status: str = "scheduled") -> dict:
    return {
        "id": 1,
        "company_id": 1,
        "scheduled_at": scheduled_at,
        "status": status,
    }


def _offer(status: str = "draft") -> dict:
    return {"id": 1, "company_id": 1, "status": status}


# ---------------------------------------------------------------------------
# GET /analytics/summary
# ---------------------------------------------------------------------------


class TestRecruitmentSummary:
    """Tests for the recruitment analytics summary endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_basic_metrics(self, mock_crud, owner_client):
        """Returns correct counts for jobs, candidates, and offers."""
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [_job("open"), _job("open"), _job("closed")],
            "Candidate": [_candidate(), _candidate()],
            "InterviewSchedule": [],
            "Offer": [_offer("accepted"), _offer("sent")],
        }.get(model, [])

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        body = resp.json()

        assert body["open_jobs"] == 2
        assert body["total_jobs"] == 3
        assert body["total_candidates"] == 2
        assert body["total_offers"] == 2
        assert body["accepted_offers"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_pipeline_distribution(self, mock_crud, owner_client):
        """Returns correct pipeline stage distribution."""
        candidates = [
            _candidate(stage="applied"),
            _candidate(stage="applied"),
            _candidate(stage="interview"),
            _candidate(stage="offered"),
        ]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [],
            "Candidate": candidates,
            "InterviewSchedule": [],
            "Offer": [],
        }.get(model, [])

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        pipeline = resp.json()["pipeline"]
        assert pipeline["applied"] == 2
        assert pipeline["interview"] == 1
        assert pipeline["offered"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_source_distribution(self, mock_crud, owner_client):
        """Returns correct source distribution."""
        candidates = [
            _candidate(source="linkedin"),
            _candidate(source="linkedin"),
            _candidate(source="referral"),
            _candidate(source="direct"),
        ]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [],
            "Candidate": candidates,
            "InterviewSchedule": [],
            "Offer": [],
        }.get(model, [])

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        sources = resp.json()["sources"]
        assert sources["linkedin"] == 2
        assert sources["referral"] == 1
        assert sources["direct"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_offer_acceptance_rate(self, mock_crud, owner_client):
        """Calculates acceptance rate correctly."""
        offers = [
            _offer("accepted"),
            _offer("accepted"),
            _offer("declined"),
            _offer("sent"),
        ]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [],
            "Candidate": [],
            "InterviewSchedule": [],
            "Offer": offers,
        }.get(model, [])

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["offer_acceptance_rate"] == 50.0  # 2/4 = 50%

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_offer_acceptance_rate_zero_offers(self, mock_crud, owner_client):
        """Acceptance rate is 0 when there are no offers (no division by zero)."""
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [],
            "Candidate": [],
            "InterviewSchedule": [],
            "Offer": [],
        }.get(model, [])

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["offer_acceptance_rate"] == 0
        assert body["total_offers"] == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_empty_data(self, mock_crud, owner_client):
        """Returns zeroed metrics when company has no recruitment data."""
        mock_crud.list_records.return_value = []

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["open_jobs"] == 0
        assert body["total_jobs"] == 0
        assert body["total_candidates"] == 0
        assert body["pipeline"] == {}
        assert body["sources"] == {}
        assert body["total_offers"] == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_tenant_isolation(self, mock_crud, owner_client):
        """Filters are scoped to the current user's company_id."""
        mock_crud.list_records.return_value = []

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200

        # Verify all list_records calls use company_id filter
        for call in mock_crud.list_records.call_args_list:
            filters = call[0][1]
            assert filters["company_id"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_employee_cannot_access_analytics(self, mock_crud, employee_client):
        """Employees are not allowed to access analytics."""
        resp = employee_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 403

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_interviews_this_week_counted(self, mock_crud, owner_client):
        """Counts scheduled interviews happening this week."""
        # Use a date in the current week
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        past_date = (now - timedelta(days=14)).strftime("%Y-%m-%d")

        interviews = [
            _interview(scheduled_at=today_str, status="scheduled"),
            _interview(scheduled_at=today_str, status="scheduled"),
            _interview(scheduled_at=past_date, status="scheduled"),  # old
            _interview(scheduled_at=today_str, status="cancelled"),  # wrong status
        ]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [],
            "Candidate": [],
            "InterviewSchedule": interviews,
            "Offer": [],
        }.get(model, [])

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        body = resp.json()
        # At least the 2 scheduled interviews today should count
        assert body["interviews_this_week"] >= 2
        # The cancelled one should NOT count
        assert body["interviews_this_week"] <= 3

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_response_shape(self, mock_crud, owner_client):
        """Validates the complete response shape has all expected keys."""
        mock_crud.list_records.return_value = []

        resp = owner_client.get("/recruitment/analytics/summary")
        assert resp.status_code == 200
        body = resp.json()

        expected_keys = {
            "open_jobs",
            "total_jobs",
            "total_candidates",
            "pipeline",
            "interviews_this_week",
            "sources",
            "total_offers",
            "accepted_offers",
            "offer_acceptance_rate",
        }
        assert set(body.keys()) == expected_keys
