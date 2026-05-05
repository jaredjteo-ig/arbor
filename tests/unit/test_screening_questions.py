"""Unit tests for screening question CRUD endpoints.

Tests T-R031 (models) and T-R032 (endpoints) covering:

1. GET /jobs/{job_id}/questions — list screening questions for a job
2. POST /jobs/{job_id}/questions — create a screening question
3. PATCH /questions/{question_id} — update a screening question
4. DELETE /questions/{question_id} — delete a screening question
5. Validation: required fields, text length limits, allowed update fields
6. Tenant isolation: questions belong to the caller's company
7. Sorting: questions returned in sort_order
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.routers.recruitment import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
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


def _job_record(job_id: int = 1, company_id: int = 1) -> dict:
    return {
        "id": job_id,
        "company_id": company_id,
        "title": "Software Engineer",
        "description": "Build things",
        "requirements": "Python experience",
        "status": "open",
    }


def _question_record(
    question_id: int = 1,
    job_listing_id: int = 1,
    company_id: int = 1,
    question_text: str = "Are you eligible to work in Singapore?",
    question_type: str = "boolean",
    sort_order: int = 0,
) -> dict:
    return {
        "id": question_id,
        "job_listing_id": job_listing_id,
        "company_id": company_id,
        "question_text": question_text,
        "question_type": question_type,
        "options": "",
        "is_required": True,
        "is_knockout": False,
        "sort_order": sort_order,
    }


@pytest.fixture()
def client():
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. List screening questions
# ---------------------------------------------------------------------------


class TestListScreeningQuestions:
    """GET /recruitment/jobs/{job_id}/questions"""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_returns_questions_sorted_by_sort_order(self, mock_crud, client):
        mock_crud.read.return_value = _job_record()
        mock_crud.list_records.return_value = [
            _question_record(question_id=2, sort_order=2),
            _question_record(question_id=1, sort_order=1),
            _question_record(question_id=3, sort_order=0),
        ]

        resp = client.get("/recruitment/jobs/1/questions")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        # Sorted by sort_order ascending
        orders = [q["sort_order"] for q in data["questions"]]
        assert orders == sorted(orders)

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_empty_when_no_questions(self, mock_crud, client):
        # _verify_job_ownership uses list_records on JobListing; the
        # screening-question list query uses list_records on ScreeningQuestion.
        mock_crud.list_records.side_effect = lambda model, filters, **kw: {
            "JobListing": [_job_record()],
            "ScreeningQuestion": [],
        }.get(model, [])

        resp = client.get("/recruitment/jobs/1/questions")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["questions"] == []

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_rejects_wrong_company_job(self, mock_crud, client):
        """Job belongs to company_id=999 but caller is company_id=1."""
        # _verify_job_ownership filters by (id, company_id); cross-tenant
        # lookup returns empty under list_records.
        mock_crud.list_records.return_value = []

        resp = client.get("/recruitment/jobs/1/questions")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. Create screening question
# ---------------------------------------------------------------------------


class TestCreateScreeningQuestion:
    """POST /recruitment/jobs/{job_id}/questions"""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_succeeds_with_valid_data(self, mock_crud, client):
        mock_crud.read.return_value = _job_record()
        mock_crud.create.return_value = _question_record()

        resp = client.post(
            "/recruitment/jobs/1/questions",
            json={
                "question_text": "Are you eligible to work in Singapore?",
                "question_type": "boolean",
                "is_required": True,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "question" in data
        assert data["question"]["question_text"] == "Are you eligible to work in Singapore?"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_fails_without_question_text(self, mock_crud, client):
        mock_crud.read.return_value = _job_record()

        resp = client.post(
            "/recruitment/jobs/1/questions",
            json={"question_type": "text"},
        )

        assert resp.status_code == 400
        assert "required" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_fails_with_empty_question_text(self, mock_crud, client):
        mock_crud.read.return_value = _job_record()

        resp = client.post(
            "/recruitment/jobs/1/questions",
            json={"question_text": "   "},
        )

        assert resp.status_code == 400
        assert "required" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_fails_with_too_long_text(self, mock_crud, client):
        mock_crud.read.return_value = _job_record()

        resp = client.post(
            "/recruitment/jobs/1/questions",
            json={"question_text": "x" * 2001},
        )

        assert resp.status_code == 400
        assert "length" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_rejects_wrong_company_job(self, mock_crud, client):
        # _verify_job_ownership filters by (id, company_id); cross-tenant
        # lookup returns empty under list_records.
        mock_crud.list_records.return_value = []

        resp = client.post(
            "/recruitment/jobs/1/questions",
            json={"question_text": "Test question?"},
        )

        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_passes_all_fields_to_dataflow(self, mock_crud, client):
        mock_crud.read.return_value = _job_record()
        mock_crud.create.return_value = _question_record()

        resp = client.post(
            "/recruitment/jobs/1/questions",
            json={
                "question_text": "Select your skills",
                "question_type": "multiple_choice",
                "options": '["Python","Java","Go"]',
                "is_required": True,
                "is_knockout": True,
                "sort_order": 5,
            },
        )

        assert resp.status_code == 200
        # Verify create was called with the right fields
        call_args = mock_crud.create.call_args
        assert call_args is not None
        model_name, data = call_args[0]
        assert model_name == "ScreeningQuestion"
        assert data["question_type"] == "multiple_choice"
        assert data["is_knockout"] is True
        assert data["sort_order"] == 5


# ---------------------------------------------------------------------------
# 3. Update screening question
# ---------------------------------------------------------------------------


class TestUpdateScreeningQuestion:
    """PATCH /recruitment/questions/{question_id}"""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_update_succeeds(self, mock_crud, client):
        mock_crud.read.return_value = _question_record(question_id=5)
        mock_crud.update.return_value = {
            **_question_record(question_id=5),
            "question_text": "Updated question?",
        }

        resp = client.patch(
            "/recruitment/questions/5",
            json={"question_text": "Updated question?"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "question" in data

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_update_rejects_wrong_company(self, mock_crud, client):
        mock_crud.read.return_value = _question_record(company_id=999)

        resp = client.patch(
            "/recruitment/questions/5",
            json={"question_text": "Updated?"},
        )

        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_update_rejects_invalid_fields(self, mock_crud, client):
        mock_crud.read.return_value = _question_record()

        resp = client.patch(
            "/recruitment/questions/1",
            json={"company_id": 999, "job_listing_id": 999},
        )

        assert resp.status_code == 400
        assert "no valid fields" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_update_allows_sort_order(self, mock_crud, client):
        mock_crud.read.return_value = _question_record()
        mock_crud.update.return_value = {**_question_record(), "sort_order": 10}

        resp = client.patch(
            "/recruitment/questions/1",
            json={"sort_order": 10},
        )

        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_update_not_found(self, mock_crud, client):
        mock_crud.read.return_value = None

        resp = client.patch(
            "/recruitment/questions/999",
            json={"question_text": "Updated?"},
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Delete screening question
# ---------------------------------------------------------------------------


class TestDeleteScreeningQuestion:
    """DELETE /recruitment/questions/{question_id}"""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_delete_succeeds(self, mock_crud, client):
        mock_crud.read.return_value = _question_record()
        mock_crud.delete.return_value = {}

        resp = client.delete("/recruitment/questions/1")

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_delete_rejects_wrong_company(self, mock_crud, client):
        mock_crud.read.return_value = _question_record(company_id=999)

        resp = client.delete("/recruitment/questions/1")

        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_delete_not_found(self, mock_crud, client):
        mock_crud.read.return_value = None

        resp = client.delete("/recruitment/questions/999")

        assert resp.status_code == 404
