"""Idempotency ledger for high-stakes external submissions.

Prevents double-submission of government filings and bank payments.
Every high-stakes tool checks the ledger before executing.

T208: Idempotency Ledger (Red Team C3)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SubmissionType(str, Enum):
    CPF = "cpf"
    IR8A = "ir8a"
    IR21 = "ir21"
    IR8S = "ir8s"
    OED = "oed"
    GIRO = "giro"
    FAST = "fast"
    PAYNOW = "paynow"
    ASPIRE_PAYOUT = "aspire_payout"
    WISE_TRANSFER = "wise_transfer"
    XERO_JOURNAL = "xero_journal"
    QBO_JOURNAL = "qbo_journal"
    ZOHO_JOURNAL = "zoho_journal"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubmissionRecord:
    """A ledger record for an external submission."""

    id: str
    tenant_id: str
    submission_type: SubmissionType
    period: str  # e.g., "2026-03" for monthly, "2026" for annual
    status: SubmissionStatus
    idempotency_key: str
    external_reference_id: Optional[str] = None
    amount: Optional[float] = None
    employee_count: Optional[int] = None
    error_detail: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None


class DuplicateSubmissionError(Exception):
    """Raised when a duplicate submission is detected."""

    def __init__(self, existing: SubmissionRecord):
        self.existing = existing
        super().__init__(
            f"Duplicate submission blocked: {existing.submission_type.value} "
            f"for period {existing.period} already {existing.status.value} "
            f"(ref: {existing.external_reference_id or existing.id})"
        )


class SubmissionLedger:
    """Tracks all high-stakes external submissions for idempotency.

    Usage::

        ledger = get_submission_ledger()

        # Before submitting CPF:
        record = ledger.create_submission("company_123", SubmissionType.CPF, "2026-03")
        # If duplicate exists, raises DuplicateSubmissionError

        # After successful submission:
        ledger.mark_submitted(record.id, external_ref="CPF-2026-03-ABC123")

        # After confirmation received:
        ledger.mark_confirmed(record.id)

        # If submission failed (allows retry):
        ledger.mark_failed(record.id, "API timeout")
    """

    def __init__(self):
        self._records: dict[str, SubmissionRecord] = {}  # id -> record
        self._index: dict[str, str] = {}  # idempotency_key -> record_id

    @staticmethod
    def _make_idempotency_key(
        tenant_id: str,
        submission_type: SubmissionType,
        period: str,
    ) -> str:
        return f"{tenant_id}:{submission_type.value}:{period}"

    def create_submission(
        self,
        tenant_id: str,
        submission_type: SubmissionType,
        period: str,
        amount: Optional[float] = None,
        employee_count: Optional[int] = None,
    ) -> SubmissionRecord:
        """Create a new submission record. Raises DuplicateSubmissionError if exists.

        A submission is considered duplicate if there's an existing record with
        the same (tenant, type, period) in a non-terminal state (pending/submitted/confirmed).
        Failed and cancelled submissions allow retry.
        """
        idempotency_key = self._make_idempotency_key(tenant_id, submission_type, period)

        existing_id = self._index.get(idempotency_key)
        if existing_id:
            existing = self._records.get(existing_id)
            if existing and existing.status in (
                SubmissionStatus.PENDING,
                SubmissionStatus.SUBMITTED,
                SubmissionStatus.CONFIRMED,
            ):
                raise DuplicateSubmissionError(existing)

        record = SubmissionRecord(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            submission_type=submission_type,
            period=period,
            status=SubmissionStatus.PENDING,
            idempotency_key=idempotency_key,
            amount=amount,
            employee_count=employee_count,
        )
        self._records[record.id] = record
        self._index[idempotency_key] = record.id
        logger.info(
            "Created submission: %s %s for %s (id=%s)",
            submission_type.value,
            period,
            tenant_id,
            record.id,
        )
        return record

    def mark_submitted(
        self,
        record_id: str,
        external_ref: Optional[str] = None,
    ) -> None:
        """Mark a submission as submitted to the external system."""
        record = self._records.get(record_id)
        if record is None:
            raise ValueError(f"Unknown submission: {record_id}")
        record.status = SubmissionStatus.SUBMITTED
        record.external_reference_id = external_ref
        record.updated_at = datetime.now(timezone.utc)
        logger.info("Submission %s marked SUBMITTED (ref=%s)", record_id, external_ref)

    def mark_confirmed(self, record_id: str) -> None:
        """Mark a submission as confirmed by the external system."""
        record = self._records.get(record_id)
        if record is None:
            raise ValueError(f"Unknown submission: {record_id}")
        record.status = SubmissionStatus.CONFIRMED
        record.confirmed_at = datetime.now(timezone.utc)
        record.updated_at = datetime.now(timezone.utc)
        logger.info("Submission %s CONFIRMED", record_id)

    def mark_failed(self, record_id: str, error: str) -> None:
        """Mark a submission as failed (allows retry)."""
        record = self._records.get(record_id)
        if record is None:
            raise ValueError(f"Unknown submission: {record_id}")
        record.status = SubmissionStatus.FAILED
        record.error_detail = error
        record.updated_at = datetime.now(timezone.utc)
        # Remove from index so retry is allowed
        if record.idempotency_key in self._index:
            del self._index[record.idempotency_key]
        logger.warning("Submission %s FAILED: %s", record_id, error)

    def cancel(self, record_id: str) -> None:
        """Cancel a pending submission."""
        record = self._records.get(record_id)
        if record is None:
            raise ValueError(f"Unknown submission: {record_id}")
        if record.status not in (SubmissionStatus.PENDING, SubmissionStatus.FAILED):
            raise ValueError(f"Cannot cancel submission in state {record.status.value}")
        record.status = SubmissionStatus.CANCELLED
        record.updated_at = datetime.now(timezone.utc)
        if record.idempotency_key in self._index:
            del self._index[record.idempotency_key]
        logger.info("Submission %s CANCELLED", record_id)

    def get_submission(self, record_id: str) -> Optional[SubmissionRecord]:
        """Get a submission record by ID."""
        return self._records.get(record_id)

    def list_submissions(
        self,
        tenant_id: Optional[str] = None,
        submission_type: Optional[SubmissionType] = None,
        status: Optional[SubmissionStatus] = None,
        limit: int = 50,
    ) -> list[SubmissionRecord]:
        """List submission records with optional filters."""
        records = list(self._records.values())
        if tenant_id:
            records = [r for r in records if r.tenant_id == tenant_id]
        if submission_type:
            records = [r for r in records if r.submission_type == submission_type]
        if status:
            records = [r for r in records if r.status == status]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]


# Singleton
_ledger: Optional[SubmissionLedger] = None


def get_submission_ledger() -> SubmissionLedger:
    """Get or create the global submission ledger."""
    global _ledger
    if _ledger is None:
        _ledger = SubmissionLedger()
    return _ledger
