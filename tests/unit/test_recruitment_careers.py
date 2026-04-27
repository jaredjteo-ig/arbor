"""Unit tests for public careers page and candidate self-service endpoints.

Tests M10 (T-R044: public careers page) and M11 (T-R048: candidate
self-service) covering:

1. GET /careers/jobs: public job listing
   - Returns only open jobs for a given company slug
   - Returns 404 when company not found
   - Strips internal fields (salary, etc.) from public response
   - Falls back to company name lookup when slug not found

2. GET /careers/jobs/{job_id}: public job detail
   - Returns published job with screening questions
   - Returns 404 for non-open jobs
   - Returns 404 for missing jobs

3. POST /careers/jobs/{job_id}/apply: public application
   - Creates candidate with PDPA consent
   - Requires name and email
   - Requires PDPA consent
   - Returns 409 for duplicate applications
   - Saves screening responses
   - Sends confirmation email
   - Returns 404 for non-open jobs
   - Validates input lengths

4. GET /careers/application-status: candidate self-service
   - Returns friendly stage labels for each internal stage
   - Returns 404 for unknown email/job combination
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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


def _company_record(company_id: int = 1, name: str = "Acme Pte Ltd") -> dict:
    return {
        "id": company_id,
        "name": name,
    }


def _job_record(
    job_id: int = 1,
    company_id: int = 1,
    status: str = "open",
    title: str = "Software Engineer",
    department: str = "Engineering",
    location: str = "Singapore",
    employment_type: str = "full_time",
    description: str = "Build great software.",
    requirements: str = "3 years experience",
    published_at: str = "2026-01-15",
    salary_range_min: float = 5000.0,
    salary_range_max: float = 8000.0,
) -> dict:
    return {
        "id": job_id,
        "company_id": company_id,
        "title": title,
        "department": department,
        "location": location,
        "employment_type": employment_type,
        "description": description,
        "requirements": requirements,
        "status": status,
        "published_at": published_at,
        "salary_range_min": salary_range_min,
        "salary_range_max": salary_range_max,
        "created_by": 10,
    }


def _screening_question(
    question_id: int = 1,
    job_listing_id: int = 1,
    company_id: int = 1,
    question_text: str = "Why do you want to work here?",
    question_type: str = "text",
    options: str = "",
    is_required: bool = True,
    sort_order: int = 1,
) -> dict:
    return {
        "id": question_id,
        "job_listing_id": job_listing_id,
        "company_id": company_id,
        "question_text": question_text,
        "question_type": question_type,
        "options": options,
        "is_required": is_required,
        "sort_order": sort_order,
    }


def _candidate_record(
    candidate_id: int = 1,
    company_id: int = 1,
    job_listing_id: int = 1,
    name: str = "Alice Tan",
    email: str = "alice@example.com",
    stage: str = "new",
) -> dict:
    return {
        "id": candidate_id,
        "company_id": company_id,
        "job_listing_id": job_listing_id,
        "name": name,
        "email": email,
        "stage": stage,
        "source": "careers_page",
        "created_at": "2026-01-20T10:00:00",
    }


@pytest.fixture()
def public_client():
    """Test client with NO auth overrides (public endpoints need no auth)."""
    app = _make_app()
    yield TestClient(app)


# ---------------------------------------------------------------------------
# M10: GET /careers/jobs — Public job listing
# ---------------------------------------------------------------------------


class TestPublicListJobs:
    """Verify GET /careers/jobs returns only open jobs for a company."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_returns_open_jobs_for_company(self, mock_crud, public_client):
        """Open jobs are returned; draft/closed jobs are excluded."""
        company = _company_record()
        open_job = _job_record(job_id=1, status="open")
        draft_job = _job_record(job_id=2, status="draft")
        closed_job = _job_record(job_id=3, status="closed")

        def _list_records(model, filters):
            if model == "Company":
                # Slug lookup
                return [company]
            if model == "JobListing":
                # The endpoint filters by status="open", so only open jobs returned
                assert filters.get("status") == "open"
                return [open_job]
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["jobs"][0]["title"] == "Software Engineer"
        assert data["company_name"] == "Acme Pte Ltd"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_strips_internal_fields(self, mock_crud, public_client):
        """Salary ranges and internal metadata must not appear in response."""
        company = _company_record()
        job = _job_record()

        def _list_records(model, filters):
            if model == "Company":
                return [company]
            if model == "JobListing":
                return [job]
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs")
        assert resp.status_code == 200
        pub_job = resp.json()["jobs"][0]
        # Salary fields must NOT appear in public response
        assert "salary_range_min" not in pub_job
        assert "salary_range_max" not in pub_job
        assert "created_by" not in pub_job
        # Public fields must exist
        assert "title" in pub_job
        assert "department" in pub_job
        assert "description" in pub_job

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_company_not_found_returns_404(self, mock_crud, public_client):
        """404 when company slug matches nothing."""
        mock_crud.list_records.return_value = []

        resp = public_client.get("/recruitment/careers/nonexistent/jobs")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_empty_jobs_returns_zero_count(self, mock_crud, public_client):
        """Company exists but has no open jobs => empty list, count=0."""
        company = _company_record()

        def _list_records(model, filters):
            if model == "Company":
                return [company]
            if model == "JobListing":
                return []
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["jobs"] == []

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_fallback_to_name_lookup(self, mock_crud, public_client):
        """When slug lookup returns nothing, falls back to name lookup."""
        company = _company_record()
        call_count = {"n": 0}

        def _list_records(model, filters):
            if model == "Company":
                call_count["n"] += 1
                if call_count["n"] == 1:
                    # First call (slug lookup) returns nothing
                    return []
                # Second call (name lookup) succeeds
                return [company]
            if model == "JobListing":
                return []
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs")
        # Name fallback was removed (T-RX04) to prevent company enumeration
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# M10: GET /careers/jobs/{job_id} — Public job detail
# ---------------------------------------------------------------------------


class TestPublicGetJob:
    """Verify GET /careers/jobs/{job_id} returns job detail with screening questions."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_returns_open_job_with_questions(self, mock_crud, public_client):
        """An open job returns detail plus its screening questions."""
        job = _job_record(job_id=5, status="open")
        company = _company_record()
        q1 = _screening_question(question_id=1, sort_order=2, question_text="Q2")
        q2 = _screening_question(question_id=2, sort_order=1, question_text="Q1")

        def _read(model, record_id):
            if model == "JobListing":
                return job if record_id == 5 else None
            if model == "Company":
                return company
            return None

        def _list_records(model, filters, **kwargs):
            if model == "Company":
                return [company]
            if model == "ScreeningQuestion":
                return [q1, q2]
            if model == "JobListing":
                # New endpoint queries by unique_slug first, then falls back to read by id
                if filters.get("unique_slug") in ("5", job.get("unique_slug", "")):
                    return [job]
                return []
            return []

        mock_crud.read.side_effect = _read
        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs/5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job"]["title"] == "Software Engineer"
        assert data["company_name"] == "Acme Pte Ltd"
        # Questions should be sorted by sort_order
        assert len(data["screening_questions"]) == 2
        assert data["screening_questions"][0]["question_text"] == "Q1"
        assert data["screening_questions"][1]["question_text"] == "Q2"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_non_open_job_returns_404(self, mock_crud, public_client):
        """Draft or closed jobs are not visible publicly."""
        job = _job_record(job_id=5, status="draft")
        company = _company_record()

        def _list_records(model, filters, **kwargs):
            if model == "Company":
                return [company]
            return []

        mock_crud.read.return_value = job
        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs/5")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_missing_job_returns_404(self, mock_crud, public_client):
        """Non-existent job ID returns 404."""
        company = _company_record()

        def _list_records(model, filters, **kwargs):
            if model == "Company":
                return [company]
            return []

        mock_crud.read.return_value = None
        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs/999")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_does_not_expose_salary(self, mock_crud, public_client):
        """Salary ranges must not appear in public job detail."""
        job = _job_record(job_id=5, status="open")
        company = _company_record()

        mock_crud.read.side_effect = lambda model, rid: (
            job if model == "JobListing" else company
        )

        def _list_records(model, filters, **kwargs):
            if model == "Company":
                return [company]
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-pte-ltd/jobs/5")
        assert resp.status_code == 200
        pub_job = resp.json()["job"]
        assert "salary_range_min" not in pub_job
        assert "salary_range_max" not in pub_job


# ---------------------------------------------------------------------------
# M10: POST /careers/jobs/{job_id}/apply — Public application
# ---------------------------------------------------------------------------


class TestPublicApply:
    """Verify POST /careers/jobs/{job_id}/apply creates a candidate."""

    def _setup_mocks(self, mock_crud, mock_rate, job=None, company=None, existing_candidates=None):
        """Common mock wiring for application tests."""
        if job is None:
            job = _job_record(job_id=1, status="open")
        if company is None:
            company = _company_record()
        if existing_candidates is None:
            existing_candidates = []

        created_candidate = _candidate_record(candidate_id=42)

        def _read(model, record_id):
            if model == "JobListing":
                return job if record_id == job.get("id") else None
            if model == "Company":
                return company
            return None

        def _list_records(model, filters, **kwargs):
            if model == "Company":
                # Slug-only lookup returns the seeded company
                return [company]
            if model == "Candidate":
                return existing_candidates
            if model == "JobListing":
                # Match either by id or unique_slug; tests pass numeric slug
                target_id = job.get("id")
                if filters.get("id") == target_id:
                    return [job]
                if filters.get("unique_slug") in (str(target_id), job.get("unique_slug", "")):
                    return [job]
                return []
            if model == "ScreeningQuestion":
                # Return valid questions for the job (question ids 1 and 2)
                return [
                    _screening_question(question_id=1, job_listing_id=1),
                    _screening_question(question_id=2, job_listing_id=1),
                ]
            return []

        mock_crud.read.side_effect = _read
        mock_crud.list_records.side_effect = _list_records
        mock_crud.create.return_value = created_candidate

        return created_candidate

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_creates_candidate_with_pdpa_consent(self, mock_crud, mock_rate, mock_email, public_client):
        """Valid application creates a candidate record."""
        self._setup_mocks(mock_crud, mock_rate)
        mock_email.return_value = True

        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={
                "name": "Bob Lee",
                "email": "bob@example.com",
                "pdpa_consent": True,
                "screening_responses": [
                    {"question_id": 1, "response_text": "I love this company"},
                    {"question_id": 2, "response_text": "Yes"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Application submitted successfully."
        assert data["application_id"] == 42

        # Verify candidate creation call (first create call, before ScreeningResponse calls)
        create_calls = mock_crud.create.call_args_list
        create_call = next(c for c in create_calls if c[0][0] == "Candidate")
        candidate_data = create_call[0][1]
        assert candidate_data["name"] == "Bob Lee"
        assert candidate_data["email"] == "bob@example.com"
        assert candidate_data["pdpa_consent"] is True
        assert candidate_data["source"] == "careers_page"
        assert candidate_data["stage"] == "new"

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_requires_name_and_email(self, mock_crud, mock_rate, mock_email, public_client):
        """Application without name or email returns 400."""
        self._setup_mocks(mock_crud, mock_rate)

        # Missing name
        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={"email": "bob@example.com", "pdpa_consent": True},
        )
        assert resp.status_code == 400
        assert "Name and email" in resp.json()["detail"]

        # Missing email
        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={"name": "Bob", "pdpa_consent": True},
        )
        assert resp.status_code == 400
        assert "Name and email" in resp.json()["detail"]

    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_requires_pdpa_consent(self, mock_crud, mock_rate, public_client):
        """Application without PDPA consent returns 400."""
        self._setup_mocks(mock_crud, mock_rate)

        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={"name": "Bob", "email": "bob@example.com", "pdpa_consent": False},
        )
        assert resp.status_code == 400
        assert "PDPA consent" in resp.json()["detail"]

    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_duplicate_application_returns_generic_received(self, mock_crud, mock_rate, public_client):
        """Re-applying returns the same generic 'received' shape — no enumeration oracle."""
        existing = _candidate_record(candidate_id=99, email="bob@example.com")
        self._setup_mocks(mock_crud, mock_rate, existing_candidates=[existing])

        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={"name": "Bob", "email": "bob@example.com", "pdpa_consent": True},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["application_id"] == 99
        assert body["reference_number"].startswith("APP-")

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_saves_screening_responses(self, mock_crud, mock_rate, mock_email, public_client):
        """Screening responses are saved alongside the application."""
        self._setup_mocks(mock_crud, mock_rate)
        mock_email.return_value = True

        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={
                "name": "Bob Lee",
                "email": "bob@example.com",
                "pdpa_consent": True,
                "screening_responses": [
                    {"question_id": 1, "response_text": "I love the mission."},
                    {"question_id": 2, "response_text": "5 years."},
                ],
            },
        )
        assert resp.status_code == 200
        # Two ScreeningResponse creates: one for "Candidate" + two for "ScreeningResponse"
        create_calls = mock_crud.create.call_args_list
        screening_creates = [c for c in create_calls if c[0][0] == "ScreeningResponse"]
        assert len(screening_creates) == 2

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_sends_confirmation_email(self, mock_crud, mock_rate, mock_email, public_client):
        """Confirmation email is sent after successful application."""
        self._setup_mocks(mock_crud, mock_rate)
        mock_email.return_value = True

        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={
                "name": "Bob Lee",
                "email": "bob@example.com",
                "pdpa_consent": True,
                "screening_responses": [
                    {"question_id": 1, "response_text": "I love this company"},
                    {"question_id": 2, "response_text": "Yes"},
                ],
            },
        )
        assert resp.status_code == 200
        mock_email.assert_called_once()
        call_kwargs = mock_email.call_args
        assert call_kwargs[1]["to"] == "bob@example.com" or call_kwargs[0][0] == "bob@example.com"
        # Verify template name
        if call_kwargs[1]:
            assert call_kwargs[1].get("template_name") == "application_received" or \
                   (len(call_kwargs[0]) > 1 and call_kwargs[0][1] == "application_received")
        else:
            assert call_kwargs[0][1] == "application_received"

    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_non_open_job_returns_404(self, mock_crud, mock_rate, public_client):
        """Cannot apply to a draft/closed job."""
        closed_job = _job_record(job_id=1, status="closed")
        self._setup_mocks(mock_crud, mock_rate, job=closed_job)

        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={"name": "Bob", "email": "bob@example.com", "pdpa_consent": True},
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.check_rate_limit")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_validates_name_length(self, mock_crud, mock_rate, mock_email, public_client):
        """Names exceeding MAX_NAME_LENGTH are rejected."""
        self._setup_mocks(mock_crud, mock_rate)

        long_name = "A" * 201  # MAX_NAME_LENGTH is 200
        resp = public_client.post(
            "/recruitment/careers/acme-pte-ltd/jobs/1/apply",
            json={"name": long_name, "email": "bob@example.com", "pdpa_consent": True},
        )
        assert resp.status_code == 400
        assert "maximum length" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# M11: GET /careers/application-status — Candidate self-service
# ---------------------------------------------------------------------------


class TestPublicApplicationStatus:
    """Verify GET /careers/{slug}/application-status returns friendly stage labels.

    The endpoint is tenant-scoped and returns the same generic shape whether
    or not the application exists, so it can't be used as an enumeration oracle.
    """

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_returns_correct_stage_labels(self, mock_crud, public_client):
        """Each internal stage maps to the correct candidate-friendly label."""
        stage_map = {
            "new": "Under Review",
            "screening": "Under Review",
            "interview": "Interview Stage",
            "offered": "Offer Extended",
            "hired": "Hired",
            "rejected": "Application Closed",
            "withdrawn": "Withdrawn",
        }
        for internal_stage, expected_label in stage_map.items():
            candidate = _candidate_record(stage=internal_stage)

            def _list_records(model, filters, **kwargs):
                if model == "Company":
                    return [_company_record()]
                if model == "JobListing":
                    return [_job_record()]
                if model == "Candidate":
                    return [candidate]
                return []

            mock_crud.list_records.side_effect = _list_records

            resp = public_client.get(
                "/recruitment/careers/acme-pte-ltd/application-status",
                params={"email": "alice@example.com", "job_slug": "1"},
            )
            assert resp.status_code == 200, f"Failed for stage={internal_stage}"
            assert resp.json()["status"] == expected_label, (
                f"Stage '{internal_stage}' should map to '{expected_label}', "
                f"got '{resp.json()['status']}'"
            )

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_unknown_email_returns_generic_response(self, mock_crud, public_client):
        """No matching application returns a generic 200 (no enumeration oracle)."""
        def _list_records(model, filters, **kwargs):
            if model == "Company":
                return [_company_record()]
            if model == "JobListing":
                return [_job_record()]
            if model == "Candidate":
                return []
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get(
            "/recruitment/careers/acme-pte-ltd/application-status",
            params={"email": "nobody@example.com", "job_slug": "999"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "Under Review"
        assert body["applied_month"] == ""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_unknown_company_returns_generic_response(self, mock_crud, public_client):
        """Unknown company slug returns the same generic shape (no enumeration)."""
        mock_crud.list_records.return_value = []

        resp = public_client.get(
            "/recruitment/careers/nonexistent/application-status",
            params={"email": "anyone@example.com", "job_slug": "1"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Under Review"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_returns_applied_month_coarsened(self, mock_crud, public_client):
        """Response coarsens applied date to YYYY-MM (not full timestamp)."""
        candidate = _candidate_record(stage="new")
        candidate["created_at"] = "2026-01-20T10:00:00"

        def _list_records(model, filters, **kwargs):
            if model == "Company":
                return [_company_record()]
            if model == "JobListing":
                return [_job_record()]
            if model == "Candidate":
                return [candidate]
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get(
            "/recruitment/careers/acme-pte-ltd/application-status",
            params={"email": "alice@example.com", "job_slug": "1"},
        )
        assert resp.status_code == 200
        # Coarsened to month only — no day/time leakage
        assert resp.json()["applied_month"] == "2026-01"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_unknown_stage_defaults_to_under_review(self, mock_crud, public_client):
        """An unknown internal stage shows 'Under Review' to the candidate."""
        candidate = _candidate_record(stage="some_custom_stage")

        def _list_records(model, filters, **kwargs):
            if model == "Company":
                return [_company_record()]
            if model == "JobListing":
                return [_job_record()]
            if model == "Candidate":
                return [candidate]
            return []

        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get(
            "/recruitment/careers/acme-pte-ltd/application-status",
            params={"email": "alice@example.com", "job_slug": "1"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Under Review"
