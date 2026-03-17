"""Integration tests for SubmissionLedger (idempotency layer).

Tests:
- Create a new submission record
- Block duplicate submissions (same tenant, type, period)
- Allow retry after failure or cancellation
- Cancel a pending submission
- Mark submitted/confirmed/failed lifecycle
- List and filter submissions
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.idempotency import (
    DuplicateSubmissionError,
    SubmissionLedger,
    SubmissionStatus,
    SubmissionType,
)

from .conftest import TENANT_A, TENANT_B


# ---------------------------------------------------------------------------
# Create submission
# ---------------------------------------------------------------------------


class TestCreateSubmission:
    """Creating a new submission record."""

    def test_create_returns_record(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert record.tenant_id == TENANT_A
        assert record.submission_type == SubmissionType.CPF
        assert record.period == "2026-03"
        assert record.status == SubmissionStatus.PENDING

    def test_create_sets_idempotency_key(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert record.idempotency_key == f"{TENANT_A}:cpf:2026-03"

    def test_create_with_amount_and_count(self, ledger: SubmissionLedger):
        record = ledger.create_submission(
            TENANT_A,
            SubmissionType.CPF,
            "2026-03",
            amount=38450.00,
            employee_count=47,
        )
        assert record.amount == 38450.00
        assert record.employee_count == 47

    def test_create_assigns_unique_ids(self, ledger: SubmissionLedger):
        r1 = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-01")
        r2 = ledger.create_submission(TENANT_A, SubmissionType.IR8A, "2026")
        assert r1.id != r2.id

    def test_create_sets_timestamps(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert record.created_at is not None
        assert record.updated_at is not None
        assert record.confirmed_at is None


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    """Blocking duplicate submissions for the same (tenant, type, period)."""

    def test_duplicate_pending_blocked(self, ledger: SubmissionLedger):
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        with pytest.raises(DuplicateSubmissionError) as exc_info:
            ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert exc_info.value.existing.status == SubmissionStatus.PENDING

    def test_duplicate_submitted_blocked(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_submitted(record.id, external_ref="CPF-123")
        with pytest.raises(DuplicateSubmissionError) as exc_info:
            ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert exc_info.value.existing.status == SubmissionStatus.SUBMITTED

    def test_duplicate_confirmed_blocked(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_submitted(record.id)
        ledger.mark_confirmed(record.id)
        with pytest.raises(DuplicateSubmissionError) as exc_info:
            ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert exc_info.value.existing.status == SubmissionStatus.CONFIRMED

    def test_different_tenant_not_considered_duplicate(self, ledger: SubmissionLedger):
        """Tenant A's submission does not block Tenant B for the same type/period."""
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        record_b = ledger.create_submission(TENANT_B, SubmissionType.CPF, "2026-03")
        assert record_b.tenant_id == TENANT_B

    def test_different_type_not_considered_duplicate(self, ledger: SubmissionLedger):
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        record = ledger.create_submission(TENANT_A, SubmissionType.IR8A, "2026-03")
        assert record.submission_type == SubmissionType.IR8A

    def test_different_period_not_considered_duplicate(self, ledger: SubmissionLedger):
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-04")
        assert record.period == "2026-04"

    def test_duplicate_error_message_contains_details(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_submitted(record.id, external_ref="CPF-ABC-123")
        with pytest.raises(DuplicateSubmissionError) as exc_info:
            ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        msg = str(exc_info.value)
        assert "cpf" in msg
        assert "2026-03" in msg
        assert "CPF-ABC-123" in msg


# ---------------------------------------------------------------------------
# Allow retry after failure
# ---------------------------------------------------------------------------


class TestRetryAfterFailure:
    """Failed submissions allow a new submission for the same (tenant, type, period)."""

    def test_retry_allowed_after_failure(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_failed(record.id, "API timeout")

        # Retry should succeed
        retry = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert retry.status == SubmissionStatus.PENDING
        assert retry.id != record.id

    def test_failed_record_preserves_error_detail(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_failed(record.id, "Connection refused")
        failed = ledger.get_submission(record.id)
        assert failed.status == SubmissionStatus.FAILED
        assert failed.error_detail == "Connection refused"

    def test_retry_allowed_after_cancellation(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.cancel(record.id)

        retry = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert retry.status == SubmissionStatus.PENDING


# ---------------------------------------------------------------------------
# Cancel submission
# ---------------------------------------------------------------------------


class TestCancelSubmission:
    """Cancelling pending or failed submissions."""

    def test_cancel_pending_submission(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.cancel(record.id)
        cancelled = ledger.get_submission(record.id)
        assert cancelled.status == SubmissionStatus.CANCELLED

    def test_cancel_failed_submission(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_failed(record.id, "timeout")
        ledger.cancel(record.id)
        assert ledger.get_submission(record.id).status == SubmissionStatus.CANCELLED

    def test_cannot_cancel_submitted(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_submitted(record.id)
        with pytest.raises(ValueError, match="Cannot cancel"):
            ledger.cancel(record.id)

    def test_cannot_cancel_confirmed(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        ledger.mark_submitted(record.id)
        ledger.mark_confirmed(record.id)
        with pytest.raises(ValueError, match="Cannot cancel"):
            ledger.cancel(record.id)

    def test_cancel_unknown_raises(self, ledger: SubmissionLedger):
        with pytest.raises(ValueError, match="Unknown submission"):
            ledger.cancel("nonexistent-id")


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


class TestLifecycleTransitions:
    """Full lifecycle: pending -> submitted -> confirmed."""

    def test_full_lifecycle(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        assert record.status == SubmissionStatus.PENDING

        ledger.mark_submitted(record.id, external_ref="CPF-2026-03-ABC")
        current = ledger.get_submission(record.id)
        assert current.status == SubmissionStatus.SUBMITTED
        assert current.external_reference_id == "CPF-2026-03-ABC"

        ledger.mark_confirmed(record.id)
        current = ledger.get_submission(record.id)
        assert current.status == SubmissionStatus.CONFIRMED
        assert current.confirmed_at is not None

    def test_mark_submitted_unknown_raises(self, ledger: SubmissionLedger):
        with pytest.raises(ValueError, match="Unknown submission"):
            ledger.mark_submitted("bad-id")

    def test_mark_confirmed_unknown_raises(self, ledger: SubmissionLedger):
        with pytest.raises(ValueError, match="Unknown submission"):
            ledger.mark_confirmed("bad-id")

    def test_mark_failed_unknown_raises(self, ledger: SubmissionLedger):
        with pytest.raises(ValueError, match="Unknown submission"):
            ledger.mark_failed("bad-id", "some error")


# ---------------------------------------------------------------------------
# List and filter
# ---------------------------------------------------------------------------


class TestListSubmissions:
    """Listing and filtering submission records."""

    def test_list_all(self, ledger: SubmissionLedger):
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-01")
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-02")
        ledger.create_submission(TENANT_B, SubmissionType.IR8A, "2026")
        records = ledger.list_submissions()
        assert len(records) == 3

    def test_filter_by_tenant(self, ledger: SubmissionLedger):
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-01")
        ledger.create_submission(TENANT_B, SubmissionType.CPF, "2026-01")
        records = ledger.list_submissions(tenant_id=TENANT_A)
        assert len(records) == 1
        assert records[0].tenant_id == TENANT_A

    def test_filter_by_type(self, ledger: SubmissionLedger):
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-01")
        ledger.create_submission(TENANT_A, SubmissionType.IR8A, "2026")
        records = ledger.list_submissions(submission_type=SubmissionType.IR8A)
        assert len(records) == 1
        assert records[0].submission_type == SubmissionType.IR8A

    def test_filter_by_status(self, ledger: SubmissionLedger):
        r1 = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-01")
        ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-02")
        ledger.mark_submitted(r1.id)

        pending = ledger.list_submissions(status=SubmissionStatus.PENDING)
        assert len(pending) == 1
        submitted = ledger.list_submissions(status=SubmissionStatus.SUBMITTED)
        assert len(submitted) == 1

    def test_list_limit(self, ledger: SubmissionLedger):
        for month in range(1, 6):
            ledger.create_submission(TENANT_A, SubmissionType.CPF, f"2026-{month:02d}")
        records = ledger.list_submissions(limit=3)
        assert len(records) == 3

    def test_list_sorted_newest_first(self, ledger: SubmissionLedger):
        r1 = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-01")
        r2 = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-02")
        records = ledger.list_submissions()
        assert records[0].created_at >= records[1].created_at

    def test_get_submission_by_id(self, ledger: SubmissionLedger):
        record = ledger.create_submission(TENANT_A, SubmissionType.CPF, "2026-03")
        fetched = ledger.get_submission(record.id)
        assert fetched is not None
        assert fetched.id == record.id

    def test_get_unknown_submission_returns_none(self, ledger: SubmissionLedger):
        assert ledger.get_submission("nonexistent-id") is None
