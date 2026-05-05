"""Unit tests for FCF (Fair Consideration Framework) compliance endpoints.

Tests T-R028 covering:

1. GET /jobs/{job_id}/fcf-check: Check FCF compliance for a job listing
   - Company with <10 employees (exempt)
   - Salary >$22,500/month (exempt)
   - Non-exempt company, no MCF posting
   - Non-exempt with MCF posting <14 days
   - Non-exempt with MCF posting >=14 days
   - Tenant isolation (company_id check)
2. POST /jobs/{job_id}/mcf-posted: Record MCF posting date
   - Records posting date on the job listing
   - Tenant isolation

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


def _job_record(
    job_id: int = 1,
    company_id: int = 1,
    salary_range_max: float = 8000.0,
    mcf_posted_date: str = "",
) -> dict:
    return {
        "id": job_id,
        "company_id": company_id,
        "title": "Software Engineer",
        "employment_type": "full_time",
        "salary_range_min": 5000.0,
        "salary_range_max": salary_range_max,
        "status": "open",
        "mcf_posted_date": mcf_posted_date,
    }


def _employee_record(employee_id: int = 1, company_id: int = 1) -> dict:
    return {
        "id": employee_id,
        "company_id": company_id,
        "name": f"Employee {employee_id}",
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
# GET /jobs/{job_id}/fcf-check
# ---------------------------------------------------------------------------


class TestFCFCheck:
    """Tests for the FCF compliance check endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_exempt_fewer_than_10_employees(self, mock_crud, owner_client):
        """Company with fewer than 10 employees is exempt from FCF advertising."""
        # _verify_job_ownership uses list_records (not read).
        job_row = _job_record(salary_range_max=8000.0)
        # 5 employees — under the 10-employee threshold
        employees = [_employee_record(i) for i in range(5)]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [job_row],
            "Employee": employees,
        }.get(model, [])

        resp = owner_client.get("/recruitment/jobs/1/fcf-check")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fcf_exempt"] is True
        assert body["employee_count"] == 5
        assert "fewer than 10" in body["exemption_reason"].lower()
        assert body["mcf_requirement_met"] is True

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_exempt_salary_above_22500(self, mock_crud, owner_client):
        """Salary above $22,500/month is exempt from FCF advertising."""
        job_row = _job_record(salary_range_max=25000.0)
        # 15 employees — above threshold
        employees = [_employee_record(i) for i in range(15)]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [job_row],
            "Employee": employees,
        }.get(model, [])

        resp = owner_client.get("/recruitment/jobs/1/fcf-check")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fcf_exempt"] is True
        assert body["salary_max"] == 25000.0
        assert "22,500" in body["exemption_reason"]
        assert body["mcf_requirement_met"] is True

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_non_exempt_no_mcf_posting(self, mock_crud, owner_client):
        """Non-exempt company without MCF posting fails compliance."""
        job_row = _job_record(salary_range_max=8000.0, mcf_posted_date="")
        employees = [_employee_record(i) for i in range(15)]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [job_row],
            "Employee": employees,
        }.get(model, [])

        resp = owner_client.get("/recruitment/jobs/1/fcf-check")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fcf_exempt"] is False
        assert body["mcf_posted"] is False
        assert body["mcf_requirement_met"] is False
        assert "14 days" in body["advisory"].lower() or "MyCareersFuture" in body["advisory"]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_non_exempt_mcf_posting_under_14_days(self, mock_crud, owner_client):
        """Non-exempt company with MCF posting under 14 days is not yet compliant."""
        # Posted 5 days ago
        posted_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        job_row = _job_record(salary_range_max=8000.0, mcf_posted_date=posted_date)
        employees = [_employee_record(i) for i in range(15)]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [job_row],
            "Employee": employees,
        }.get(model, [])

        resp = owner_client.get("/recruitment/jobs/1/fcf-check")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fcf_exempt"] is False
        assert body["mcf_posted"] is True
        assert body["days_since_posting"] >= 4  # Allow 1-day tolerance for test timing
        assert body["days_since_posting"] <= 6
        assert body["mcf_requirement_met"] is False

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_non_exempt_mcf_posting_14_days_or_more(self, mock_crud, owner_client):
        """Non-exempt company with MCF posting >=14 days is compliant."""
        # Posted 20 days ago
        posted_date = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        job_row = _job_record(salary_range_max=8000.0, mcf_posted_date=posted_date)
        employees = [_employee_record(i) for i in range(15)]
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [job_row],
            "Employee": employees,
        }.get(model, [])

        resp = owner_client.get("/recruitment/jobs/1/fcf-check")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fcf_exempt"] is False
        assert body["mcf_posted"] is True
        assert body["days_since_posting"] >= 19
        assert body["mcf_requirement_met"] is True
        assert "completed" in body["advisory"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_job_not_found_returns_404(self, mock_crud, owner_client):
        """Non-existent job returns 404."""
        # _verify_job_ownership uses list_records — empty result raises 404.
        mock_crud.list_records.return_value = []

        resp = owner_client.get("/recruitment/jobs/999/fcf-check")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_tenant_isolation(self, mock_crud, owner_client):
        """Job belonging to a different company returns 404."""
        # _verify_job_ownership filters by (id, company_id); a job belonging
        # to company 999 won't match the filter so list_records returns [].
        mock_crud.list_records.return_value = []

        resp = owner_client.get("/recruitment/jobs/1/fcf-check")
        assert resp.status_code == 404

    def test_employee_role_denied(self, employee_client):
        """Employees cannot access FCF check."""
        resp = employee_client.get("/recruitment/jobs/1/fcf-check")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/mcf-posted
# ---------------------------------------------------------------------------


class TestRecordMCFPosting:
    """Tests for the MCF posting date recording endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_record_mcf_posting(self, mock_crud, owner_client):
        """Recording MCF posting sets mcf_posted_date on the job."""
        # _verify_job_ownership uses list_records.
        mock_crud.list_records.return_value = [_job_record()]
        mock_crud.update.return_value = {
            **_job_record(),
            "mcf_posted_date": "2026-04-16T00:00:00+00:00",
        }

        resp = owner_client.post("/recruitment/jobs/1/mcf-posted")
        assert resp.status_code == 200
        body = resp.json()
        assert "job" in body
        assert body["message"] == "MCF posting date recorded."

        # Verify update was called with mcf_posted_date
        mock_crud.update.assert_called_once()
        call_args = mock_crud.update.call_args
        assert call_args[0][0] == "JobListing"
        assert call_args[0][1] == 1
        assert "mcf_posted_date" in call_args[0][2]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_mcf_posting_tenant_isolation(self, mock_crud, owner_client):
        """Cannot record MCF posting for another company's job."""
        # Wrong-tenant lookup returns empty under list_records-based ownership.
        mock_crud.list_records.return_value = []

        resp = owner_client.post("/recruitment/jobs/1/mcf-posted")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_hr_manager_can_record_mcf(self, mock_crud, hr_manager_client):
        """HR managers can record MCF posting."""
        mock_crud.list_records.return_value = [_job_record()]
        mock_crud.update.return_value = _job_record()

        resp = hr_manager_client.post("/recruitment/jobs/1/mcf-posted")
        assert resp.status_code == 200

    def test_employee_cannot_record_mcf(self, employee_client):
        """Employees cannot record MCF posting."""
        resp = employee_client.post("/recruitment/jobs/1/mcf-posted")
        assert resp.status_code == 403
