"""Unit tests for M12 advanced recruitment features.

Tests T-R050 (Talent Pool), T-R051 (Employee Referral), and T-R052
(Hiring Manager Filtered View) covering:

1. GET /talent-pool: Search across all candidates
   - Search by name, email, stage, source, tag
   - Enrichment with job title
   - Tenant isolation (company_id scoping)
   - Role restriction (owner, hr_manager only)

2. POST /candidates/{id}/reapply: Move to new job pipeline
   - Creates new candidate record for new job
   - Preserves original candidate data
   - Validates job ownership
   - Rejects when missing job_listing_id

3. POST /referrals: Submit employee referral
   - Creates referral from employee
   - Validates required fields (name, email, job_listing_id)
   - Requires employee record for referrer
   - Any authenticated user can submit

4. GET /referrals: List referrals
   - HR sees all company referrals
   - Employees see only their own
   - Enrichment with job title

5. GET /my-department/candidates: Department-filtered view
   - Returns candidates for jobs in user's department
   - Returns empty if no department assigned
   - Returns empty if no employee record
   - Enrichment with job title

Tier 1 (Unit): Fast, isolated, uses mocks for dataflow_crud.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

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


def _fake_user(
    company_id: int = 1,
    role: str = "owner",
    sub: int = 10,
) -> dict:
    return {
        "sub": sub,
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
def hr_client():
    """Test client with hr_manager role."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="hr_manager")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def employee_client():
    """Test client with employee role."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="employee", sub=20)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def no_company_client():
    """Test client with no company_id."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": 10,
        "email": "test@example.com",
        "role": "owner",
    }
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper data factories
# ---------------------------------------------------------------------------


def _candidate(
    candidate_id: int = 1,
    company_id: int = 1,
    job_listing_id: int = 100,
    name: str = "Alice Wong",
    email: str = "alice@example.com",
    stage: str = "applied",
    source: str = "direct",
    notes: str = "",
    phone: str = "91234567",
    nationality: str = "Singaporean",
    citizenship_status: str = "citizen",
    resume_url: str = "",
    pdpa_consent: bool = True,
    pdpa_consent_date: str = "2026-01-01",
) -> dict:
    return {
        "id": candidate_id,
        "company_id": company_id,
        "job_listing_id": job_listing_id,
        "name": name,
        "email": email,
        "phone": phone,
        "stage": stage,
        "source": source,
        "notes": notes,
        "nationality": nationality,
        "citizenship_status": citizenship_status,
        "resume_url": resume_url,
        "pdpa_consent": pdpa_consent,
        "pdpa_consent_date": pdpa_consent_date,
    }


def _job(
    job_id: int = 100,
    company_id: int = 1,
    title: str = "Software Engineer",
    department: str = "Engineering",
    status: str = "open",
) -> dict:
    return {
        "id": job_id,
        "company_id": company_id,
        "title": title,
        "department": department,
        "status": status,
    }


def _employee(
    employee_id: int = 50,
    user_id: int = 10,
    company_id: int = 1,
    department: str = "Engineering",
) -> dict:
    return {
        "id": employee_id,
        "user_id": user_id,
        "company_id": company_id,
        "department": department,
    }


def _referral(
    referral_id: int = 1,
    company_id: int = 1,
    referrer_employee_id: int = 50,
    job_listing_id: int = 100,
    candidate_name: str = "Bob Tan",
    candidate_email: str = "bob@example.com",
    status: str = "pending",
) -> dict:
    return {
        "id": referral_id,
        "company_id": company_id,
        "referrer_employee_id": referrer_employee_id,
        "job_listing_id": job_listing_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "status": status,
    }


# ===========================================================================
# T-R050: Talent Pool — GET /talent-pool
# ===========================================================================


class TestTalentPoolSearch:
    """Tests for the talent pool search endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_search_all_candidates(self, mock_crud, owner_client):
        """Returns all candidates for the company when no filters applied."""
        candidates = [
            _candidate(candidate_id=1, name="Alice Wong"),
            _candidate(candidate_id=2, name="Bob Tan", email="bob@example.com"),
        ]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job()

        resp = owner_client.get("/recruitment/talent-pool")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert len(body["candidates"]) == 2

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_search_by_name(self, mock_crud, owner_client):
        """Filters candidates by name substring (case-insensitive)."""
        candidates = [
            _candidate(candidate_id=1, name="Alice Wong", email="alice@example.com"),
            _candidate(candidate_id=2, name="Bob Tan", email="bob@example.com"),
        ]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job()

        resp = owner_client.get("/recruitment/talent-pool?query=bob")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["candidates"][0]["name"] == "Bob Tan"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_search_by_email(self, mock_crud, owner_client):
        """Filters candidates by email substring (case-insensitive)."""
        candidates = [
            _candidate(candidate_id=1, email="alice@example.com"),
            _candidate(candidate_id=2, email="bob@company.com"),
        ]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job()

        resp = owner_client.get("/recruitment/talent-pool?query=bob@company")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["candidates"][0]["email"] == "bob@company.com"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_filter_by_stage(self, mock_crud, owner_client):
        """Filters candidates by pipeline stage."""
        candidates = [
            _candidate(candidate_id=1, stage="interview"),
            _candidate(candidate_id=2, stage="applied"),
            _candidate(candidate_id=3, stage="interview"),
        ]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job()

        resp = owner_client.get("/recruitment/talent-pool?stage=interview")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        for c in body["candidates"]:
            assert c["stage"] == "interview"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_filter_by_source(self, mock_crud, owner_client):
        """Filters candidates by source channel."""
        candidates = [
            _candidate(candidate_id=1, source="linkedin"),
            _candidate(candidate_id=2, source="direct"),
            _candidate(candidate_id=3, source="linkedin"),
        ]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job()

        resp = owner_client.get("/recruitment/talent-pool?source=linkedin")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        for c in body["candidates"]:
            assert c["source"] == "linkedin"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_filter_by_tag_in_notes(self, mock_crud, owner_client):
        """Filters candidates by tag substring in notes."""
        candidates = [
            _candidate(candidate_id=1, notes="Strong Python skills"),
            _candidate(candidate_id=2, notes="Java developer"),
            _candidate(candidate_id=3, notes="python and react"),
        ]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job()

        resp = owner_client.get("/recruitment/talent-pool?tag=python")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_enriches_with_job_title(self, mock_crud, owner_client):
        """Each candidate is enriched with their job listing title."""
        candidates = [_candidate(candidate_id=1, job_listing_id=100)]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job(title="Backend Engineer")

        resp = owner_client.get("/recruitment/talent-pool")
        assert resp.status_code == 200
        body = resp.json()
        assert body["candidates"][0]["job_title"] == "Backend Engineer"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_tenant_isolation(self, mock_crud, owner_client):
        """Only returns candidates scoped to the user's company."""
        mock_crud.list_records.return_value = []

        resp = owner_client.get("/recruitment/talent-pool")
        assert resp.status_code == 200

        call_args = mock_crud.list_records.call_args
        assert call_args[0][1]["company_id"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_employee_cannot_access(self, mock_crud, employee_client):
        """Employees are denied access to the talent pool."""
        resp = employee_client.get("/recruitment/talent-pool")
        assert resp.status_code == 403

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_company_returns_403(self, mock_crud, no_company_client):
        """Returns 403 when user has no associated company (tenant isolation)."""
        resp = no_company_client.get("/recruitment/talent-pool")
        assert resp.status_code == 403

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_combined_filters(self, mock_crud, owner_client):
        """Multiple filters combine correctly."""
        candidates = [
            _candidate(candidate_id=1, name="Alice", email="alice@one.com", stage="interview", source="linkedin", notes="Python"),
            _candidate(candidate_id=2, name="Alice", email="alice@two.com", stage="interview", source="direct", notes="Python"),
            _candidate(candidate_id=3, name="Bob", email="bob@one.com", stage="interview", source="linkedin", notes="Python"),
        ]
        mock_crud.list_records.return_value = candidates
        mock_crud.read.return_value = _job()

        resp = owner_client.get(
            "/recruitment/talent-pool?query=alice&stage=interview&source=linkedin&tag=python"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["candidates"][0]["name"] == "Alice"
        assert body["candidates"][0]["source"] == "linkedin"


# ===========================================================================
# T-R050: Talent Pool — POST /candidates/{id}/reapply
# ===========================================================================


class TestReapplyCandidate:
    """Tests for the reapply-to-new-job endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_reapply_creates_new_candidate(self, mock_crud, owner_client):
        """Creates a new candidate record for the target job."""
        original = _candidate(candidate_id=5, name="Alice Wong", email="alice@example.com")
        target_job = _job(job_id=200, company_id=1)

        # _verify_candidate_ownership and _verify_job_ownership both use
        # list_records (not read) — see recruitment.py:200-228.
        def _list(model, filt, **_kwargs):
            if model == "Candidate" and filt.get("id") == 5:
                return [original]
            if model == "JobListing" and filt.get("id") == 200:
                return [target_job]
            return []

        mock_crud.list_records.side_effect = _list
        mock_crud.create.return_value = {**original, "id": 99, "job_listing_id": 200, "source": "talent_pool"}

        resp = owner_client.post(
            "/recruitment/candidates/5/reapply",
            json={"job_listing_id": 200},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["candidate"]["source"] == "talent_pool"
        assert "Re-applied from talent pool" in body["message"] or "new job pipeline" in body["message"]

        # Verify create was called with correct data
        create_call = mock_crud.create.call_args
        assert create_call[0][0] == "Candidate"
        create_data = create_call[0][1]
        assert create_data["job_listing_id"] == 200
        assert create_data["source"] == "talent_pool"
        assert create_data["stage"] == "new"
        assert create_data["name"] == "Alice Wong"
        assert create_data["email"] == "alice@example.com"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_reapply_requires_job_listing_id(self, mock_crud, owner_client):
        """Returns 400 when job_listing_id is not provided."""
        original = _candidate(candidate_id=5)
        mock_crud.list_records.return_value = [original]

        resp = owner_client.post(
            "/recruitment/candidates/5/reapply",
            json={},
        )
        assert resp.status_code == 400
        assert "job_listing_id" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_reapply_validates_candidate_ownership(self, mock_crud, owner_client):
        """Returns 404 when candidate belongs to a different company."""
        # _verify_candidate_ownership filters by (id, company_id) — when the
        # candidate belongs to a different tenant the list returns empty.
        mock_crud.list_records.return_value = []

        resp = owner_client.post(
            "/recruitment/candidates/5/reapply",
            json={"job_listing_id": 200},
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_reapply_validates_job_ownership(self, mock_crud, owner_client):
        """Returns 404 when target job belongs to a different company."""
        original = _candidate(candidate_id=5, company_id=1)

        def _list(model, filt, **_kwargs):
            if model == "Candidate" and filt.get("id") == 5:
                return [original]
            # JobListing filtered by (id=200, company_id=1) — different
            # tenant means the lookup returns empty.
            return []

        mock_crud.list_records.side_effect = _list

        resp = owner_client.post(
            "/recruitment/candidates/5/reapply",
            json={"job_listing_id": 200},
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_reapply_candidate_not_found(self, mock_crud, owner_client):
        """Returns 404 when candidate does not exist."""
        mock_crud.list_records.return_value = []

        resp = owner_client.post(
            "/recruitment/candidates/999/reapply",
            json={"job_listing_id": 200},
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_employee_cannot_reapply(self, mock_crud, employee_client):
        """Employees cannot move candidates between jobs."""
        resp = employee_client.post(
            "/recruitment/candidates/5/reapply",
            json={"job_listing_id": 200},
        )
        assert resp.status_code == 403

    # -- T-RX02: PDPA consent reset on re-apply -----------------------------

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_reapply_resets_pdpa_consent_to_false(self, mock_crud, owner_client):
        """T-RX02: New candidate must start with pdpa_consent=False/empty date.

        Even if the original candidate had pdpa_consent=True, a fresh consent
        is required for the new application.
        """
        original = _candidate(
            candidate_id=5,
            name="Alice Wong",
            email="alice@example.com",
            pdpa_consent=True,
            pdpa_consent_date="2024-01-01T00:00:00Z",
        )
        mock_crud.read.side_effect = lambda model, record_id: {
            ("Candidate", 5): original,
            ("JobListing", 200): _job(job_id=200, company_id=1),
        }.get((model, record_id))
        mock_crud.create.return_value = {**original, "id": 99, "job_listing_id": 200}

        resp = owner_client.post(
            "/recruitment/candidates/5/reapply",
            json={"job_listing_id": 200},
        )
        assert resp.status_code == 200

        create_data = mock_crud.create.call_args[0][1]
        assert create_data["pdpa_consent"] is False, (
            "T-RX02: re-apply must reset pdpa_consent to False"
        )
        assert create_data["pdpa_consent_date"] == "", (
            "T-RX02: re-apply must clear pdpa_consent_date"
        )
        # Notes carry the audit-trail explanation
        assert "PDPA consent must be re-confirmed" in create_data["notes"]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_reapply_response_contains_note_field(self, mock_crud, owner_client):
        """T-RX02: response must include a top-level ``note`` field warning HR."""
        original = _candidate(candidate_id=5, pdpa_consent=True)
        mock_crud.read.side_effect = lambda model, record_id: {
            ("Candidate", 5): original,
            ("JobListing", 200): _job(job_id=200, company_id=1),
        }.get((model, record_id))
        mock_crud.create.return_value = {**original, "id": 99}

        resp = owner_client.post(
            "/recruitment/candidates/5/reapply",
            json={"job_listing_id": 200},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "note" in body, "T-RX02: response missing 'note' field"
        assert "PDPA" in body["note"]


# ===========================================================================
# T-R051: Employee Referrals — POST /referrals
# ===========================================================================


class TestCreateReferral:
    """Tests for the employee referral submission endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_referral_success(self, mock_crud, employee_client):
        """Successfully creates a referral with all required fields."""
        mock_crud.read.return_value = _job(job_id=100, company_id=1)
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "Employee": [_employee(employee_id=50, user_id=20, company_id=1)],
        }.get(model, [])
        mock_crud.create.return_value = _referral()

        resp = employee_client.post(
            "/recruitment/referrals",
            json={
                "job_listing_id": 100,
                "candidate_name": "Bob Tan",
                "candidate_email": "bob@example.com",
                "candidate_phone": "91234567",
                "notes": "Great colleague from previous company",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "referral" in body
        assert body["message"] == "Referral submitted."

        # Verify create was called
        create_call = mock_crud.create.call_args
        assert create_call[0][0] == "Referral"
        create_data = create_call[0][1]
        assert create_data["candidate_name"] == "Bob Tan"
        assert create_data["candidate_email"] == "bob@example.com"
        assert create_data["referrer_employee_id"] == 50
        assert create_data["status"] == "pending"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_referral_requires_job_listing_id(self, mock_crud, employee_client):
        """Returns 400 when job_listing_id is missing."""
        resp = employee_client.post(
            "/recruitment/referrals",
            json={
                "candidate_name": "Bob Tan",
                "candidate_email": "bob@example.com",
            },
        )
        assert resp.status_code == 400
        assert "job_listing_id" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_referral_requires_name_and_email(self, mock_crud, employee_client):
        """Returns 400 when candidate name or email is missing."""
        mock_crud.read.return_value = _job(job_id=100, company_id=1)

        # Missing name
        resp = employee_client.post(
            "/recruitment/referrals",
            json={
                "job_listing_id": 100,
                "candidate_email": "bob@example.com",
            },
        )
        assert resp.status_code == 400

        # Missing email
        resp = employee_client.post(
            "/recruitment/referrals",
            json={
                "job_listing_id": 100,
                "candidate_name": "Bob Tan",
            },
        )
        assert resp.status_code == 400

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_referral_requires_employee_record(self, mock_crud, employee_client):
        """Returns 400 when referrer has no employee record."""
        mock_crud.read.return_value = _job(job_id=100, company_id=1)
        mock_crud.list_records.return_value = []  # No employee record

        resp = employee_client.post(
            "/recruitment/referrals",
            json={
                "job_listing_id": 100,
                "candidate_name": "Bob Tan",
                "candidate_email": "bob@example.com",
            },
        )
        assert resp.status_code == 400
        assert "employee" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_referral_validates_job_ownership(self, mock_crud, employee_client):
        """Returns 404 when job belongs to a different company."""
        mock_crud.read.return_value = _job(job_id=100, company_id=999)

        resp = employee_client.post(
            "/recruitment/referrals",
            json={
                "job_listing_id": 100,
                "candidate_name": "Bob Tan",
                "candidate_email": "bob@example.com",
            },
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_owner_can_submit_referral(self, mock_crud, owner_client):
        """Owners can also submit referrals (any authenticated user)."""
        mock_crud.read.return_value = _job(job_id=100, company_id=1)
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "Employee": [_employee(employee_id=50, user_id=10, company_id=1)],
        }.get(model, [])
        mock_crud.create.return_value = _referral()

        resp = owner_client.post(
            "/recruitment/referrals",
            json={
                "job_listing_id": 100,
                "candidate_name": "Bob Tan",
                "candidate_email": "bob@example.com",
            },
        )
        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_company_returns_403(self, mock_crud, no_company_client):
        """Returns 403 when user has no company (tenant isolation)."""
        resp = no_company_client.post(
            "/recruitment/referrals",
            json={
                "job_listing_id": 100,
                "candidate_name": "Bob",
                "candidate_email": "bob@example.com",
            },
        )
        assert resp.status_code == 403


# ===========================================================================
# T-R051: Employee Referrals — GET /referrals
# ===========================================================================


class TestListReferrals:
    """Tests for the referral listing endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_hr_sees_all_referrals(self, mock_crud, hr_client):
        """HR managers see all referrals for the company."""
        referrals = [
            _referral(referral_id=1, referrer_employee_id=50),
            _referral(referral_id=2, referrer_employee_id=60),
        ]
        mock_crud.list_records.return_value = referrals
        mock_crud.read.return_value = _job(title="Engineer")

        resp = hr_client.get("/recruitment/referrals")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert len(body["referrals"]) == 2

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_employee_sees_only_own_referrals(self, mock_crud, employee_client):
        """Employees see only referrals they submitted."""
        employee_record = _employee(employee_id=50, user_id=20, company_id=1)
        own_referral = _referral(referral_id=1, referrer_employee_id=50)

        def mock_list(model, filters, **kw):
            if model == "Employee":
                return [employee_record]
            if model == "Referral":
                # Should filter by referrer_employee_id
                assert filters.get("referrer_employee_id") == 50
                return [own_referral]
            return []

        mock_crud.list_records.side_effect = mock_list
        mock_crud.read.return_value = _job(title="Engineer")

        resp = employee_client.get("/recruitment/referrals")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_employee_with_no_employee_record_sees_empty(self, mock_crud, employee_client):
        """Employee with no employee record gets empty list."""
        mock_crud.list_records.return_value = []

        resp = employee_client.get("/recruitment/referrals")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["referrals"] == []

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_referrals_enriched_with_job_title(self, mock_crud, hr_client):
        """Referrals are enriched with the job listing title."""
        referrals = [_referral(referral_id=1, job_listing_id=100)]
        mock_crud.list_records.return_value = referrals
        mock_crud.read.return_value = _job(title="Product Manager")

        resp = hr_client.get("/recruitment/referrals")
        assert resp.status_code == 200
        body = resp.json()
        assert body["referrals"][0]["job_title"] == "Product Manager"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_owner_sees_all_referrals(self, mock_crud, owner_client):
        """Owners also see all referrals."""
        referrals = [_referral(), _referral(referral_id=2)]
        mock_crud.list_records.return_value = referrals
        mock_crud.read.return_value = _job()

        resp = owner_client.get("/recruitment/referrals")
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_tenant_isolation(self, mock_crud, hr_client):
        """Referral queries are scoped to the user's company."""
        mock_crud.list_records.return_value = []

        resp = hr_client.get("/recruitment/referrals")
        assert resp.status_code == 200

        call_args = mock_crud.list_records.call_args
        assert call_args[0][1]["company_id"] == 1


# ===========================================================================
# T-R052: Hiring Manager Filtered View — GET /my-department/candidates
# ===========================================================================


class TestDepartmentCandidates:
    """Tests for the department-filtered candidate view."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_returns_candidates_for_department_jobs(self, mock_crud, employee_client):
        """Returns candidates only for jobs in the user's department."""
        employee_record = _employee(employee_id=50, user_id=20, department="Engineering")
        eng_job = _job(job_id=100, department="Engineering", title="Backend Dev")
        eng_candidate = _candidate(candidate_id=1, job_listing_id=100)
        other_candidate = _candidate(candidate_id=2, job_listing_id=200)  # different department

        def mock_list(model, filters, **kw):
            if model == "Employee":
                return [employee_record]
            if model == "JobListing":
                if filters.get("department") == "Engineering":
                    return [eng_job]
                return []
            if model == "Candidate":
                return [eng_candidate, other_candidate]
            return []

        mock_crud.list_records.side_effect = mock_list
        mock_crud.read.return_value = eng_job

        resp = employee_client.get("/recruitment/my-department/candidates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["department"] == "Engineering"
        assert body["count"] == 1
        assert body["candidates"][0]["id"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_employee_record_returns_empty(self, mock_crud, employee_client):
        """Returns empty list when user has no employee record."""
        mock_crud.list_records.return_value = []

        resp = employee_client.get("/recruitment/my-department/candidates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["candidates"] == []
        assert body["count"] == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_department_returns_empty(self, mock_crud, employee_client):
        """Returns empty list when employee has no department assigned."""
        employee_record = _employee(department="")
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "Employee": [employee_record],
        }.get(model, [])

        resp = employee_client.get("/recruitment/my-department/candidates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert "department" in body.get("message", "").lower() or body["count"] == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_candidates_enriched_with_job_title(self, mock_crud, employee_client):
        """Department candidates are enriched with job title."""
        employee_record = _employee(department="Sales")
        sales_job = _job(job_id=100, department="Sales", title="Sales Manager")
        candidate = _candidate(candidate_id=1, job_listing_id=100)

        def mock_list(model, filters, **kw):
            if model == "Employee":
                return [employee_record]
            if model == "JobListing":
                return [sales_job]
            if model == "Candidate":
                return [candidate]
            return []

        mock_crud.list_records.side_effect = mock_list
        mock_crud.read.return_value = sales_job

        resp = employee_client.get("/recruitment/my-department/candidates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["candidates"][0]["job_title"] == "Sales Manager"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_hr_can_access_department_view(self, mock_crud, hr_client):
        """HR managers can also use the department-filtered view."""
        employee_record = _employee(user_id=10, department="HR")
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "Employee": [employee_record],
            "JobListing": [],
            "Candidate": [],
        }.get(model, [])

        resp = hr_client.get("/recruitment/my-department/candidates")
        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_company_returns_403(self, mock_crud, no_company_client):
        """Returns 403 when user has no company (tenant isolation)."""
        resp = no_company_client.get("/recruitment/my-department/candidates")
        assert resp.status_code == 403

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_jobs_in_department_returns_empty(self, mock_crud, employee_client):
        """Returns empty when department has no job listings."""
        employee_record = _employee(department="Legal")

        def mock_list(model, filters, **kw):
            if model == "Employee":
                return [employee_record]
            if model == "JobListing":
                return []  # No jobs in Legal
            if model == "Candidate":
                return []
            return []

        mock_crud.list_records.side_effect = mock_list

        resp = employee_client.get("/recruitment/my-department/candidates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
