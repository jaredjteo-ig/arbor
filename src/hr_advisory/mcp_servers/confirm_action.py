"""Shared confirm_action MCP tool for human-in-the-loop approval.

Creates an approval request that the UI displays as a modal.
Used by sagas before executing irreversible operations (government
submissions, bank payments, bulk emails).

The approval store is in-memory for now. In production, this should
be backed by Redis or the database for persistence across restarts.

T268: Human-in-the-Loop Confirm Action Gate
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A single approval request record."""

    id: str
    description: str
    action_type: str
    amount: Optional[float] = None
    count: Optional[int] = None
    metadata: dict = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str = ""
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str = ""
    decided_at: Optional[datetime] = None
    rejection_reason: str = ""
    tenant_id: str = ""


class ApprovalStore:
    """In-memory store for approval requests.

    Thread-safe for single-process use. For multi-process deployments,
    replace with Redis-backed implementation.

    Usage::

        store = get_approval_store()
        req = store.create_request(
            description="Submit CPF contributions for March 2026",
            action_type="government_submission",
            amount=45230.00,
            count=23,
            tenant_id="company_123",
            requested_by="shadow_agent",
        )
        # UI polls or receives websocket notification
        status = store.check_approval(req.id)
        # User clicks Approve in the modal
        store.approve(req.id, decided_by="user_456")
    """

    def __init__(self):
        self._requests: dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        description: str,
        action_type: str,
        amount: Optional[float] = None,
        count: Optional[int] = None,
        metadata: Optional[dict] = None,
        tenant_id: str = "",
        requested_by: str = "",
    ) -> ApprovalRequest:
        """Create a new approval request.

        Args:
            description: Human-readable description of what will happen
                (e.g., "Submit CPF contributions for March 2026 — 23 employees, $45,230").
            action_type: Category of the action for UI grouping. Known types:
                - "government_submission" (CPF, IR8A, MOM)
                - "bank_payment" (GIRO, PayNow bulk)
                - "bulk_email" (payslip distribution, notifications)
                - "data_deletion" (PDPA right-to-erasure)
            amount: Optional monetary amount (for display in the modal).
            count: Optional count (e.g., number of employees affected).
            metadata: Optional additional data for the UI modal.
            tenant_id: Company ID for tenant isolation.
            requested_by: ID of the agent or user that initiated the request.

        Returns:
            The created ApprovalRequest.
        """
        request = ApprovalRequest(
            id=str(uuid.uuid4()),
            description=description,
            action_type=action_type,
            amount=amount,
            count=count,
            metadata=metadata or {},
            tenant_id=tenant_id,
            requested_by=requested_by,
        )
        self._requests[request.id] = request

        logger.info(
            "Approval request created: id=%s type=%s tenant=%s description='%s'",
            request.id,
            action_type,
            tenant_id,
            description[:80],
        )
        return request

    def check_approval(self, approval_id: str) -> dict:
        """Check the current status of an approval request.

        Args:
            approval_id: UUID of the approval request.

        Returns:
            Dict with status and request details.
        """
        request = self._requests.get(approval_id)
        if request is None:
            return {
                "status": "error",
                "message": f"Approval request not found: {approval_id}",
            }

        return self._request_to_dict(request)

    def approve(
        self,
        approval_id: str,
        decided_by: str = "",
    ) -> dict:
        """Approve a pending request.

        Args:
            approval_id: UUID of the approval request.
            decided_by: User ID of the approver.

        Returns:
            Updated request dict.
        """
        request = self._requests.get(approval_id)
        if request is None:
            return {
                "status": "error",
                "message": f"Approval request not found: {approval_id}",
            }

        if request.status != ApprovalStatus.PENDING:
            return {
                "status": "error",
                "message": (
                    f"Cannot approve: request is already {request.status.value}. "
                    f"Only pending requests can be approved."
                ),
            }

        request.status = ApprovalStatus.APPROVED
        request.decided_by = decided_by
        request.decided_at = datetime.now(timezone.utc)

        logger.info(
            "Approval granted: id=%s by=%s type=%s",
            approval_id,
            decided_by,
            request.action_type,
        )
        return self._request_to_dict(request)

    def reject(
        self,
        approval_id: str,
        reason: str = "",
        decided_by: str = "",
    ) -> dict:
        """Reject a pending request.

        Args:
            approval_id: UUID of the approval request.
            reason: Human-readable rejection reason.
            decided_by: User ID of the rejector.

        Returns:
            Updated request dict.
        """
        request = self._requests.get(approval_id)
        if request is None:
            return {
                "status": "error",
                "message": f"Approval request not found: {approval_id}",
            }

        if request.status != ApprovalStatus.PENDING:
            return {
                "status": "error",
                "message": (
                    f"Cannot reject: request is already {request.status.value}. "
                    f"Only pending requests can be rejected."
                ),
            }

        request.status = ApprovalStatus.REJECTED
        request.decided_by = decided_by
        request.decided_at = datetime.now(timezone.utc)
        request.rejection_reason = reason

        logger.info(
            "Approval rejected: id=%s by=%s reason='%s'",
            approval_id,
            decided_by,
            reason[:80],
        )
        return self._request_to_dict(request)

    def list_pending(self, tenant_id: str) -> list[dict]:
        """List all pending approval requests for a tenant.

        Args:
            tenant_id: Company ID.

        Returns:
            List of pending request dicts.
        """
        pending = [
            self._request_to_dict(r)
            for r in self._requests.values()
            if r.tenant_id == tenant_id and r.status == ApprovalStatus.PENDING
        ]
        pending.sort(key=lambda r: r["requested_at"], reverse=True)
        return pending

    @staticmethod
    def _request_to_dict(request: ApprovalRequest) -> dict:
        """Convert an ApprovalRequest to a serializable dict."""
        result: dict[str, Any] = {
            "status": request.status.value,
            "approval_id": request.id,
            "description": request.description,
            "action_type": request.action_type,
            "tenant_id": request.tenant_id,
            "requested_by": request.requested_by,
            "requested_at": request.requested_at.isoformat(),
        }
        if request.amount is not None:
            result["amount"] = request.amount
        if request.count is not None:
            result["count"] = request.count
        if request.metadata:
            result["metadata"] = request.metadata
        if request.decided_by:
            result["decided_by"] = request.decided_by
        if request.decided_at:
            result["decided_at"] = request.decided_at.isoformat()
        if request.rejection_reason:
            result["rejection_reason"] = request.rejection_reason
        return result


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_store: Optional[ApprovalStore] = None


def get_approval_store() -> ApprovalStore:
    """Get or create the global approval store."""
    global _store
    if _store is None:
        _store = ApprovalStore()
    return _store


# ---------------------------------------------------------------------------
# Convenience function for MCP tools and sagas
# ---------------------------------------------------------------------------


def confirm_action(
    description: str,
    action_type: str,
    amount: Optional[float] = None,
    count: Optional[int] = None,
    metadata: Optional[dict] = None,
    tenant_id: str = "",
    requested_by: str = "",
) -> dict:
    """Create an approval request and return the pending status.

    This is the primary entry point used by MCP tools and saga steps.
    The caller should check the returned status and wait for approval
    before proceeding with the irreversible action.

    Args:
        description: What the action will do.
        action_type: Category (government_submission, bank_payment, etc.).
        amount: Optional monetary amount.
        count: Optional affected record count.
        metadata: Optional additional context.
        tenant_id: Company ID.
        requested_by: Initiator ID.

    Returns:
        Dict with status="pending_approval", approval_id, and details.
    """
    store = get_approval_store()
    request = store.create_request(
        description=description,
        action_type=action_type,
        amount=amount,
        count=count,
        metadata=metadata,
        tenant_id=tenant_id,
        requested_by=requested_by,
    )
    return store._request_to_dict(request)


def check_approval(approval_id: str) -> dict:
    """Poll the status of an approval request.

    Returns the current status. The saga or tool should keep polling
    until the status changes from "pending_approval" to "approved"
    or "rejected".
    """
    store = get_approval_store()
    return store.check_approval(approval_id)
