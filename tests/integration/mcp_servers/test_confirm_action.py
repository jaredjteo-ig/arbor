"""Integration tests for the human-in-the-loop approval gate.

Tests:
- Create approval request -> pending status
- Approve -> approved status
- Reject -> rejected status with reason
- Double-approve -> error
- Approve after reject -> error
- List pending filtered by tenant
- Expired approval handling (manual status check)
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.confirm_action import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStore,
    check_approval,
    confirm_action,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> ApprovalStore:
    """Fresh approval store for each test."""
    return ApprovalStore()


# ---------------------------------------------------------------------------
# Create Request
# ---------------------------------------------------------------------------


class TestCreateRequest:
    """Creating approval requests."""

    def test_create_returns_approval_request(self, store):
        req = store.create_request(
            description="Submit CPF for March 2026",
            action_type="government_submission",
            tenant_id="company_100",
        )
        assert isinstance(req, ApprovalRequest)

    def test_initial_status_is_pending(self, store):
        req = store.create_request(
            description="Submit CPF",
            action_type="government_submission",
        )
        assert req.status == ApprovalStatus.PENDING

    def test_id_is_uuid_string(self, store):
        req = store.create_request(
            description="Submit CPF",
            action_type="government_submission",
        )
        assert isinstance(req.id, str)
        assert len(req.id) == 36  # UUID4 with dashes

    def test_amount_and_count_stored(self, store):
        req = store.create_request(
            description="GIRO payment",
            action_type="bank_payment",
            amount=45230.00,
            count=23,
        )
        assert req.amount == 45230.00
        assert req.count == 23

    def test_metadata_stored(self, store):
        req = store.create_request(
            description="Bulk payslip email",
            action_type="bulk_email",
            metadata={"template": "payslip", "month": "March"},
        )
        assert req.metadata == {"template": "payslip", "month": "March"}

    def test_requested_by_stored(self, store):
        req = store.create_request(
            description="Submit IR8A",
            action_type="government_submission",
            requested_by="shadow_agent",
        )
        assert req.requested_by == "shadow_agent"

    def test_tenant_id_stored(self, store):
        req = store.create_request(
            description="GIRO payment",
            action_type="bank_payment",
            tenant_id="company_100",
        )
        assert req.tenant_id == "company_100"

    def test_unique_ids_for_multiple_requests(self, store):
        req1 = store.create_request(description="A", action_type="test")
        req2 = store.create_request(description="B", action_type="test")
        assert req1.id != req2.id


# ---------------------------------------------------------------------------
# Check Approval
# ---------------------------------------------------------------------------


class TestCheckApproval:
    """Polling approval status."""

    def test_check_pending_returns_status(self, store):
        req = store.create_request(description="Test", action_type="test")
        result = store.check_approval(req.id)
        assert result["status"] == "pending_approval"

    def test_check_unknown_id_returns_error(self, store):
        result = store.check_approval("nonexistent-uuid")
        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_check_returns_description(self, store):
        req = store.create_request(
            description="Submit CPF contributions",
            action_type="government_submission",
        )
        result = store.check_approval(req.id)
        assert result["description"] == "Submit CPF contributions"


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------


class TestApprove:
    """Approving pending requests."""

    def test_approve_changes_status(self, store):
        req = store.create_request(description="Test", action_type="test")
        result = store.approve(req.id, decided_by="admin_1")
        assert result["status"] == "approved"

    def test_approve_sets_decided_by(self, store):
        req = store.create_request(description="Test", action_type="test")
        result = store.approve(req.id, decided_by="admin_1")
        assert result["decided_by"] == "admin_1"

    def test_approve_sets_decided_at(self, store):
        req = store.create_request(description="Test", action_type="test")
        result = store.approve(req.id, decided_by="admin_1")
        assert "decided_at" in result

    def test_approve_unknown_id_returns_error(self, store):
        result = store.approve("nonexistent-uuid", decided_by="admin")
        assert result["status"] == "error"

    def test_double_approve_returns_error(self, store):
        req = store.create_request(description="Test", action_type="test")
        store.approve(req.id, decided_by="admin_1")
        result = store.approve(req.id, decided_by="admin_2")
        assert result["status"] == "error"
        assert "already" in result["message"]


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------


class TestReject:
    """Rejecting pending requests."""

    def test_reject_changes_status(self, store):
        req = store.create_request(description="Test", action_type="test")
        result = store.reject(req.id, reason="Too expensive", decided_by="admin_1")
        assert result["status"] == "rejected"

    def test_reject_stores_reason(self, store):
        req = store.create_request(description="Test", action_type="test")
        result = store.reject(req.id, reason="Budget exceeded", decided_by="admin_1")
        assert result["rejection_reason"] == "Budget exceeded"

    def test_reject_sets_decided_by(self, store):
        req = store.create_request(description="Test", action_type="test")
        result = store.reject(req.id, reason="No", decided_by="admin_1")
        assert result["decided_by"] == "admin_1"

    def test_reject_unknown_id_returns_error(self, store):
        result = store.reject("nonexistent-uuid", reason="No")
        assert result["status"] == "error"

    def test_approve_after_reject_returns_error(self, store):
        req = store.create_request(description="Test", action_type="test")
        store.reject(req.id, reason="Rejected first", decided_by="admin_1")
        result = store.approve(req.id, decided_by="admin_2")
        assert result["status"] == "error"
        assert "already" in result["message"]

    def test_reject_after_approve_returns_error(self, store):
        req = store.create_request(description="Test", action_type="test")
        store.approve(req.id, decided_by="admin_1")
        result = store.reject(req.id, reason="Changed my mind", decided_by="admin_2")
        assert result["status"] == "error"
        assert "already" in result["message"]


# ---------------------------------------------------------------------------
# List Pending (Tenant Isolation)
# ---------------------------------------------------------------------------


class TestListPending:
    """List pending requests filtered by tenant."""

    def test_list_pending_for_tenant(self, store):
        store.create_request(description="A", action_type="test", tenant_id="company_100")
        store.create_request(description="B", action_type="test", tenant_id="company_200")
        store.create_request(description="C", action_type="test", tenant_id="company_100")

        pending = store.list_pending("company_100")
        assert len(pending) == 2
        assert all(p["tenant_id"] == "company_100" for p in pending)

    def test_list_pending_excludes_approved(self, store):
        req1 = store.create_request(
            description="Approved", action_type="test", tenant_id="company_100"
        )
        store.create_request(
            description="Still pending", action_type="test", tenant_id="company_100"
        )
        store.approve(req1.id, decided_by="admin")

        pending = store.list_pending("company_100")
        assert len(pending) == 1
        assert pending[0]["description"] == "Still pending"

    def test_list_pending_excludes_rejected(self, store):
        req1 = store.create_request(
            description="Rejected", action_type="test", tenant_id="company_100"
        )
        store.create_request(
            description="Still pending", action_type="test", tenant_id="company_100"
        )
        store.reject(req1.id, reason="No", decided_by="admin")

        pending = store.list_pending("company_100")
        assert len(pending) == 1

    def test_empty_tenant_returns_empty_list(self, store):
        pending = store.list_pending("nonexistent_company")
        assert pending == []

    def test_list_pending_sorted_newest_first(self, store):
        store.create_request(description="First", action_type="test", tenant_id="company_100")
        store.create_request(description="Second", action_type="test", tenant_id="company_100")
        pending = store.list_pending("company_100")
        assert pending[0]["requested_at"] >= pending[1]["requested_at"]


# ---------------------------------------------------------------------------
# Expired Approval
# ---------------------------------------------------------------------------


class TestExpiredApproval:
    """Expired approval status handling."""

    def test_manually_expired_cannot_be_approved(self, store):
        req = store.create_request(description="Expired test", action_type="test")
        # Manually set to expired (simulating timeout logic)
        req.status = ApprovalStatus.EXPIRED

        result = store.approve(req.id, decided_by="admin")
        assert result["status"] == "error"
        assert "already" in result["message"]

    def test_manually_expired_cannot_be_rejected(self, store):
        req = store.create_request(description="Expired test", action_type="test")
        req.status = ApprovalStatus.EXPIRED

        result = store.reject(req.id, reason="Too late", decided_by="admin")
        assert result["status"] == "error"

    def test_expired_not_in_pending_list(self, store):
        req = store.create_request(
            description="Expired", action_type="test", tenant_id="company_100"
        )
        req.status = ApprovalStatus.EXPIRED
        store.create_request(description="Active", action_type="test", tenant_id="company_100")

        pending = store.list_pending("company_100")
        assert len(pending) == 1
        assert pending[0]["description"] == "Active"


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Test module-level confirm_action and check_approval."""

    def test_confirm_action_returns_pending(self):
        result = confirm_action(
            description="Bulk GIRO payment",
            action_type="bank_payment",
            amount=50000.00,
            count=30,
            tenant_id="company_test",
            requested_by="test_agent",
        )
        assert result["status"] == "pending_approval"
        assert "approval_id" in result

    def test_check_approval_returns_status(self):
        result = confirm_action(
            description="Test action",
            action_type="test",
            tenant_id="company_test",
        )
        status = check_approval(result["approval_id"])
        assert status["status"] == "pending_approval"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    """Verify _request_to_dict output."""

    def test_dict_contains_required_keys(self, store):
        req = store.create_request(
            description="Test",
            action_type="government_submission",
            amount=1000.00,
            count=5,
            tenant_id="company_100",
            requested_by="agent",
        )
        d = store.check_approval(req.id)
        required_keys = {
            "status",
            "approval_id",
            "description",
            "action_type",
            "tenant_id",
            "requested_by",
            "requested_at",
        }
        assert required_keys.issubset(set(d.keys()))

    def test_amount_present_when_set(self, store):
        req = store.create_request(
            description="Payment",
            action_type="bank_payment",
            amount=5000.00,
        )
        d = store.check_approval(req.id)
        assert d["amount"] == 5000.00

    def test_amount_absent_when_not_set(self, store):
        req = store.create_request(
            description="Non-monetary",
            action_type="data_deletion",
        )
        d = store.check_approval(req.id)
        assert "amount" not in d
