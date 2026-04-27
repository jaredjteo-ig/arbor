"""Unit tests for recruitment offer approval workflow endpoints.

Tests T-R038 (offer approval) and T-R040 (offer tracking) covering:

1. POST /offers/{id}/approve: Approve a draft/pending offer
   - Tenant isolation (company_id check)
   - Status transition validation (only draft/pending_approval -> approved)
   - approved_by and approved_at fields set
   - Role restriction (owner, hr_manager only)
2. POST /offers/{id}/send: Send an approved offer to candidate
   - Tenant isolation
   - Status transition validation (only draft/approved -> sent)
   - Candidate stage update to 'offered'
   - Email dispatch (non-blocking)
3. GET /offers: List offers for the company
   - Tenant isolation
   - Status filter
   - Candidate name enrichment
4. POST /offers/{id}/respond: Accept or decline a sent offer
   - Status must be 'sent'
   - Only 'accepted' or 'declined' responses allowed
   - responded_at timestamp set

Tier 1 (Unit): Fast, isolated, uses mocks for dataflow_crud.
"""

from __future__ import annotations

from datetime import datetime, timezone
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


def _offer_record(
    offer_id: int = 1,
    company_id: int = 1,
    candidate_id: int = 5,
    status: str = "draft",
    salary: float = 5000.0,
) -> dict:
    return {
        "id": offer_id,
        "company_id": company_id,
        "candidate_id": candidate_id,
        "job_listing_id": 1,
        "salary": salary,
        "currency": "SGD",
        "salary_period": "monthly",
        "start_date": "2026-06-01",
        "position_title": "Software Engineer",
        "employment_type": "full_time",
        "status": status,
        "expiry_date": "2026-05-15",
        "created_by": 10,
    }


def _candidate_record(
    candidate_id: int = 5,
    company_id: int = 1,
    email: str = "candidate@example.com",
    name: str = "Alice Tan",
    stage: str = "interview",
) -> dict:
    return {
        "id": candidate_id,
        "company_id": company_id,
        "job_listing_id": 1,
        "name": name,
        "email": email,
        "stage": stage,
    }


@pytest.fixture()
def owner_client():
    """Test client with owner role (can approve and send offers)."""
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
    """Test client with employee role (can respond to offers)."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="employee")
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /offers/{id}/approve
# ---------------------------------------------------------------------------


class TestApproveOffer:
    """Tests for the offer approval endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_approve_draft_offer(self, mock_crud, owner_client):
        """Approving a draft offer sets status to 'approved' with approver info."""
        mock_crud.read.return_value = _offer_record(status="draft")
        mock_crud.update.return_value = {**_offer_record(status="approved"), "approved_by": 10}

        resp = owner_client.post("/recruitment/offers/1/approve")
        assert resp.status_code == 200
        body = resp.json()
        assert body["offer"]["status"] == "approved"
        assert "message" in body

        # Verify update was called with correct fields
        mock_crud.update.assert_called_once()
        call_args = mock_crud.update.call_args
        assert call_args[0][0] == "Offer"
        assert call_args[0][1] == 1
        update_data = call_args[0][2]
        assert update_data["status"] == "approved"
        assert update_data["approved_by"] == 10
        assert "approved_at" in update_data

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_approve_pending_approval_offer(self, mock_crud, owner_client):
        """Offers with status 'pending_approval' can also be approved."""
        mock_crud.read.return_value = _offer_record(status="pending_approval")
        mock_crud.update.return_value = _offer_record(status="approved")

        resp = owner_client.post("/recruitment/offers/1/approve")
        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_approve_already_sent_offer_rejected(self, mock_crud, owner_client):
        """Cannot approve an offer that has already been sent."""
        mock_crud.read.return_value = _offer_record(status="sent")

        resp = owner_client.post("/recruitment/offers/1/approve")
        assert resp.status_code == 400
        assert "cannot be approved" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_approve_accepted_offer_rejected(self, mock_crud, owner_client):
        """Cannot approve an offer that was already accepted."""
        mock_crud.read.return_value = _offer_record(status="accepted")

        resp = owner_client.post("/recruitment/offers/1/approve")
        assert resp.status_code == 400

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_approve_nonexistent_offer_404(self, mock_crud, owner_client):
        """Returns 404 when offer does not exist."""
        mock_crud.read.return_value = None

        resp = owner_client.post("/recruitment/offers/99/approve")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_approve_offer_wrong_company_404(self, mock_crud, owner_client):
        """Returns 404 when offer belongs to a different company."""
        mock_crud.read.return_value = _offer_record(company_id=999)

        resp = owner_client.post("/recruitment/offers/1/approve")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_hr_manager_can_approve(self, mock_crud, hr_manager_client):
        """HR managers can approve offers."""
        mock_crud.read.return_value = _offer_record(status="draft")
        mock_crud.update.return_value = _offer_record(status="approved")

        resp = hr_manager_client.post("/recruitment/offers/1/approve")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /offers/{id}/send
# ---------------------------------------------------------------------------


class TestSendOffer:
    """Tests for the offer sending endpoint."""

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_approved_offer(self, mock_crud, mock_email, owner_client):
        """Sending an approved offer transitions to 'sent' and emails candidate."""
        candidate = _candidate_record()
        company = {"id": 1, "name": "Acme Corp"}
        offer = _offer_record(status="approved")

        def _read_side_effect(model, record_id):
            if model == "Offer":
                return offer
            if model == "Candidate":
                return candidate
            if model == "Company":
                return company
            return None

        mock_crud.read.side_effect = _read_side_effect
        mock_crud.update.return_value = {**offer, "status": "sent"}
        mock_email.return_value = True

        resp = owner_client.post("/recruitment/offers/1/send")
        assert resp.status_code == 200
        body = resp.json()
        assert body["offer"]["status"] == "sent"
        assert "message" in body

        # Verify email was attempted
        mock_email.assert_called_once()
        email_kwargs = mock_email.call_args
        assert email_kwargs[1]["to"] == "candidate@example.com" or email_kwargs[0][0] == "candidate@example.com"

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_draft_offer_allowed(self, mock_crud, mock_email, owner_client):
        """Sending a draft offer (skipping approval) is allowed."""
        mock_crud.read.side_effect = lambda model, rid: (
            _offer_record(status="draft") if model == "Offer"
            else _candidate_record() if model == "Candidate"
            else {"id": 1, "name": "Test Co"} if model == "Company"
            else None
        )
        mock_crud.update.return_value = _offer_record(status="sent")
        mock_email.return_value = True

        resp = owner_client.post("/recruitment/offers/1/send")
        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_already_sent_rejected(self, mock_crud, owner_client):
        """Cannot send an offer that was already sent."""
        mock_crud.read.return_value = _offer_record(status="sent")

        resp = owner_client.post("/recruitment/offers/1/send")
        assert resp.status_code == 400
        assert "cannot be sent" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_declined_offer_rejected(self, mock_crud, owner_client):
        """Cannot send an offer that was declined."""
        mock_crud.read.return_value = _offer_record(status="declined")

        resp = owner_client.post("/recruitment/offers/1/send")
        assert resp.status_code == 400

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_nonexistent_offer_404(self, mock_crud, owner_client):
        """Returns 404 when offer does not exist."""
        mock_crud.read.return_value = None

        resp = owner_client.post("/recruitment/offers/99/send")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_offer_wrong_company_404(self, mock_crud, owner_client):
        """Returns 404 when offer belongs to a different company."""
        mock_crud.read.return_value = _offer_record(company_id=999)

        resp = owner_client.post("/recruitment/offers/1/send")
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email")
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_send_updates_candidate_stage(self, mock_crud, mock_email, owner_client):
        """Sending an offer should update the candidate's stage to 'offered'."""
        offer = _offer_record(status="approved", candidate_id=5)
        mock_crud.read.side_effect = lambda model, rid: (
            offer if model == "Offer"
            else _candidate_record() if model == "Candidate"
            else {"id": 1, "name": "Test Co"} if model == "Company"
            else None
        )
        mock_crud.update.return_value = {**offer, "status": "sent"}
        mock_email.return_value = True

        resp = owner_client.post("/recruitment/offers/1/send")
        assert resp.status_code == 200

        # Check that candidate update was called with stage='offered'
        update_calls = mock_crud.update.call_args_list
        candidate_update = [c for c in update_calls if c[0][0] == "Candidate"]
        assert len(candidate_update) == 1
        assert candidate_update[0][0][2]["stage"] == "offered"

# ---------------------------------------------------------------------------
# GET /offers
# ---------------------------------------------------------------------------


class TestListOffers:
    """Tests for listing offers."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_all_offers(self, mock_crud, owner_client):
        """Lists all offers for the company."""
        offers = [_offer_record(offer_id=1), _offer_record(offer_id=2)]
        mock_crud.list_records.return_value = offers
        mock_crud.read.return_value = _candidate_record()

        resp = owner_client.get("/recruitment/offers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert len(body["offers"]) == 2

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_offers_with_status_filter(self, mock_crud, owner_client):
        """Filters offers by status when provided."""
        mock_crud.list_records.return_value = [_offer_record(status="sent")]
        mock_crud.read.return_value = _candidate_record()

        resp = owner_client.get("/recruitment/offers?status=sent")
        assert resp.status_code == 200

        # Verify the filter was passed to list_records
        call_args = mock_crud.list_records.call_args
        filters = call_args[0][1]
        assert filters["status"] == "sent"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_offers_enriches_candidate_names(self, mock_crud, owner_client):
        """Each offer should include the candidate's name."""
        offers = [_offer_record(offer_id=1, candidate_id=5)]
        mock_crud.list_records.return_value = offers
        mock_crud.read.return_value = _candidate_record(name="Alice Tan")

        resp = owner_client.get("/recruitment/offers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["offers"][0]["candidate_name"] == "Alice Tan"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_offers_missing_candidate_graceful(self, mock_crud, owner_client):
        """Handles missing candidate records gracefully (empty name)."""
        offers = [_offer_record(offer_id=1, candidate_id=999)]
        mock_crud.list_records.return_value = offers
        mock_crud.read.return_value = None

        resp = owner_client.get("/recruitment/offers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["offers"][0]["candidate_name"] == ""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_offers_empty(self, mock_crud, owner_client):
        """Returns empty list when no offers exist."""
        mock_crud.list_records.return_value = []

        resp = owner_client.get("/recruitment/offers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["offers"] == []

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_employee_cannot_list_offers(self, mock_crud, employee_client):
        """Employees cannot list offers (role restriction)."""
        resp = employee_client.get("/recruitment/offers")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /offers/{id}/respond
# ---------------------------------------------------------------------------


class TestRespondToOffer:
    """Tests for the offer accept/decline endpoint."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_accept_sent_offer(self, mock_crud, owner_client):
        """Accepting a sent offer sets status to 'accepted'."""
        mock_crud.read.return_value = _offer_record(status="sent")
        mock_crud.update.return_value = _offer_record(status="accepted")

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": "accepted"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["offer"]["status"] == "accepted"

        # Verify update
        update_data = mock_crud.update.call_args[0][2]
        assert update_data["status"] == "accepted"
        assert "responded_at" in update_data

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_decline_sent_offer(self, mock_crud, owner_client):
        """Declining a sent offer sets status to 'declined'."""
        mock_crud.read.return_value = _offer_record(status="sent")
        mock_crud.update.return_value = _offer_record(status="declined")

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": "declined"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["offer"]["status"] == "declined"

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_respond_to_draft_offer_rejected(self, mock_crud, owner_client):
        """Cannot respond to an offer that has not been sent."""
        mock_crud.read.return_value = _offer_record(status="draft")

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": "accepted"},
        )
        assert resp.status_code == 400
        assert "not in a respondable state" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_respond_invalid_response_rejected(self, mock_crud, owner_client):
        """Only 'accepted' and 'declined' are valid responses."""
        mock_crud.read.return_value = _offer_record(status="sent")

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": "maybe"},
        )
        assert resp.status_code == 400
        assert "must be" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_respond_empty_response_rejected(self, mock_crud, owner_client):
        """Empty string response is rejected."""
        mock_crud.read.return_value = _offer_record(status="sent")

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": ""},
        )
        assert resp.status_code == 400

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_respond_nonexistent_offer_404(self, mock_crud, owner_client):
        """Returns 404 when offer does not exist."""
        mock_crud.read.return_value = None

        resp = owner_client.post(
            "/recruitment/offers/99/respond",
            json={"response": "accepted"},
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_respond_wrong_company_404(self, mock_crud, owner_client):
        """Returns 404 when offer belongs to a different company."""
        mock_crud.read.return_value = _offer_record(company_id=999)

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": "accepted"},
        )
        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_respond_case_insensitive(self, mock_crud, owner_client):
        """Response value should be case-insensitive."""
        mock_crud.read.return_value = _offer_record(status="sent")
        mock_crud.update.return_value = _offer_record(status="accepted")

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": "ACCEPTED"},
        )
        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_respond_message_reflects_action(self, mock_crud, owner_client):
        """Response message includes the action taken (accepted/declined)."""
        mock_crud.read.return_value = _offer_record(status="sent")
        mock_crud.update.return_value = _offer_record(status="declined")

        resp = owner_client.post(
            "/recruitment/offers/1/respond",
            json={"response": "declined"},
        )
        assert resp.status_code == 200
        assert "declined" in resp.json()["message"].lower()
