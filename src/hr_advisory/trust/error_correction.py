"""Error Correction and Transparency Process (T047).

Handles:
- Error discovery and logging
- Affected user notification identification
- KB correction tracking
- Transparent correction log (publicly visible)
- Post-correction consistency audit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ErrorSource(str, Enum):
    """How the error was discovered."""

    USER_REPORT = "user_report"
    EXPERT_AUDIT = "expert_audit"
    REGULATORY_CHANGE_LAG = "regulatory_change_lag"
    AUTOMATED_DETECTION = "automated_detection"
    INTERNAL_REVIEW = "internal_review"


class CorrectionStatus(str, Enum):
    """Status of a correction."""

    IDENTIFIED = "identified"
    INVESTIGATING = "investigating"
    CORRECTED = "corrected"
    VERIFIED = "verified"
    NOTIFIED = "notified"


@dataclass
class ErrorRecord:
    """Record of an identified error in advisory output or KB content."""

    id: str
    source: ErrorSource
    description: str
    affected_provision_ids: list[str]
    affected_domains: list[str]
    severity: str  # critical, high, medium, low
    discovered_at: datetime
    discovered_by: str
    status: CorrectionStatus = CorrectionStatus.IDENTIFIED
    correction_description: str = ""
    corrected_at: Optional[datetime] = None
    corrected_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    notification_sent_at: Optional[datetime] = None
    affected_session_ids: list[str] = field(default_factory=list)
    kb_update_lag_days: int = 0  # days between regulatory change and KB update


@dataclass
class CorrectionNotification:
    """Notification to send to affected users."""

    error_id: str
    user_ids: list[str]
    session_ids: list[str]
    notification_type: str  # "email", "in_app", "both"
    subject: str
    body: str
    sent_at: Optional[datetime] = None


@dataclass
class TransparentCorrectionEntry:
    """Entry in the public correction log."""

    error_id: str
    date_identified: str
    date_corrected: str
    domain: str
    description: str
    impact: str
    what_was_wrong: str
    what_was_corrected: str
    kb_lag_disclosure: str  # e.g., "Regulation changed on X. KB updated on Y."


# ── In-memory stores ─────────────────────────────────────────

_error_records: dict[str, ErrorRecord] = {}
_correction_log: list[TransparentCorrectionEntry] = []


def report_error(
    error_id: str,
    source: ErrorSource,
    description: str,
    affected_provision_ids: list[str],
    affected_domains: list[str],
    severity: str,
    discovered_by: str,
) -> ErrorRecord:
    """Report a new error for investigation."""
    record = ErrorRecord(
        id=error_id,
        source=source,
        description=description,
        affected_provision_ids=affected_provision_ids,
        affected_domains=affected_domains,
        severity=severity,
        discovered_at=datetime.now(),
        discovered_by=discovered_by,
    )
    _error_records[error_id] = record
    return record


def start_investigation(error_id: str) -> ErrorRecord:
    """Move an error to investigating status."""
    record = _error_records.get(error_id)
    if record is None:
        raise ValueError(f"Error {error_id} not found")
    record.status = CorrectionStatus.INVESTIGATING
    return record


def apply_correction(
    error_id: str,
    correction_description: str,
    corrected_by: str,
) -> ErrorRecord:
    """Apply a correction to an identified error."""
    record = _error_records.get(error_id)
    if record is None:
        raise ValueError(f"Error {error_id} not found")
    record.status = CorrectionStatus.CORRECTED
    record.correction_description = correction_description
    record.corrected_at = datetime.now()
    record.corrected_by = corrected_by
    return record


def verify_correction(error_id: str, verified_by: str) -> ErrorRecord:
    """Verify that a correction is accurate and consistent."""
    record = _error_records.get(error_id)
    if record is None:
        raise ValueError(f"Error {error_id} not found")
    record.status = CorrectionStatus.VERIFIED
    record.verified_at = datetime.now()
    record.verified_by = verified_by

    # Add to public correction log
    _correction_log.append(
        TransparentCorrectionEntry(
            error_id=error_id,
            date_identified=record.discovered_at.strftime("%Y-%m-%d"),
            date_corrected=record.corrected_at.strftime("%Y-%m-%d") if record.corrected_at else "",
            domain=", ".join(record.affected_domains),
            description=record.description,
            impact=f"Affected {len(record.affected_session_ids)} advisory sessions",
            what_was_wrong=record.description,
            what_was_corrected=record.correction_description,
            kb_lag_disclosure=(
                f"KB was updated {record.kb_update_lag_days} day(s) after the regulatory change."
                if record.kb_update_lag_days > 0
                else "KB was current at time of error."
            ),
        )
    )

    return record


def identify_affected_sessions(
    error_id: str,
    provision_ids: list[str],
) -> list[str]:
    """Identify sessions that received advice based on incorrect provisions.

    Scans the in-memory trust chain store for sessions whose attestations
    reference any of the given provision_ids. In production with DataFlow
    persistence, this would be a database query on AdvisorySession records.

    Returns list of affected session IDs.
    """
    record = _error_records.get(error_id)
    if record is None:
        raise ValueError(f"Error {error_id} not found")

    from hr_advisory.trust.eatp_lineage import _trust_chains

    provision_set = set(provision_ids)
    affected: list[str] = []

    for session_id, chain in _trust_chains.items():
        for attestation in chain.attestations:
            if provision_set & set(attestation.provisions_retrieved):
                affected.append(session_id)
                break

    record.affected_session_ids = affected
    return record.affected_session_ids


def get_correction_log() -> list[TransparentCorrectionEntry]:
    """Get the public correction log (most recent first)."""
    return list(reversed(_correction_log))


def get_error_records(
    status: Optional[CorrectionStatus] = None,
) -> list[ErrorRecord]:
    """Get error records, optionally filtered by status."""
    records = list(_error_records.values())
    if status is not None:
        records = [r for r in records if r.status == status]
    return sorted(records, key=lambda r: r.discovered_at, reverse=True)
