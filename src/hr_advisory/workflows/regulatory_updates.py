"""Regulatory Change Management Pipeline.

Phase 1 (launch): Manual update workflow with staging, review, and publication.
Phase 2 (post-launch): Automated source monitoring.

Each regulatory update goes through: Draft → Review → Approved/Rejected → Published.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional


class UpdateStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class UpdateUrgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AffectedProvision:
    """A provision that is affected by the regulatory update."""

    provision_id: str
    current_text: str
    new_text: str
    change_type: str  # "amendment" | "new" | "repeal"


@dataclass
class RegulatoryUpdate:
    """A staged regulatory update awaiting review and publication."""

    id: str
    title: str
    description: str
    source: str  # e.g. "MOM", "CPF Board", "IRAS", "TAFEP"
    source_url: str
    urgency: UpdateUrgency
    status: UpdateStatus
    affected_provisions: list[AffectedProvision]
    effective_date: date
    created_at: datetime
    created_by: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    published_at: Optional[datetime] = None
    domains_affected: list[str] = field(default_factory=list)
    alert_message: str = ""
    impact_summary: str = ""


@dataclass
class StalenessRecord:
    """Tracks when provisions were last reviewed."""

    provision_id: str
    last_reviewed: date
    next_review_date: date
    reviewer: str
    is_stale: bool = False


# ── In-memory store (production: DataFlow models) ────────────

_updates: dict[str, RegulatoryUpdate] = {}
_staleness: dict[str, StalenessRecord] = {}


def create_update(update: RegulatoryUpdate) -> RegulatoryUpdate:
    """Create a new regulatory update in draft status."""
    update.status = UpdateStatus.DRAFT
    update.created_at = datetime.now()
    _updates[update.id] = update
    return update


def submit_for_review(update_id: str) -> RegulatoryUpdate:
    """Move a draft update to in-review status."""
    update = _updates.get(update_id)
    if update is None:
        raise ValueError(f"Update {update_id} not found")
    if update.status != UpdateStatus.DRAFT:
        raise ValueError(f"Update must be in draft status, got {update.status}")
    update.status = UpdateStatus.IN_REVIEW
    return update


def approve_update(
    update_id: str,
    reviewer: str,
    notes: str = "",
) -> RegulatoryUpdate:
    """Approve a reviewed update (human-in-the-loop gate)."""
    update = _updates.get(update_id)
    if update is None:
        raise ValueError(f"Update {update_id} not found")
    if update.status != UpdateStatus.IN_REVIEW:
        raise ValueError(f"Update must be in review, got {update.status}")
    update.status = UpdateStatus.APPROVED
    update.reviewed_by = reviewer
    update.reviewed_at = datetime.now()
    update.review_notes = notes
    return update


def reject_update(
    update_id: str,
    reviewer: str,
    notes: str = "",
) -> RegulatoryUpdate:
    """Reject a reviewed update."""
    update = _updates.get(update_id)
    if update is None:
        raise ValueError(f"Update {update_id} not found")
    if update.status != UpdateStatus.IN_REVIEW:
        raise ValueError(f"Update must be in review, got {update.status}")
    update.status = UpdateStatus.REJECTED
    update.reviewed_by = reviewer
    update.reviewed_at = datetime.now()
    update.review_notes = notes
    return update


def publish_update(update_id: str) -> RegulatoryUpdate:
    """Publish an approved update — updates KB and generates alerts."""
    update = _updates.get(update_id)
    if update is None:
        raise ValueError(f"Update {update_id} not found")
    if update.status != UpdateStatus.APPROVED:
        raise ValueError(f"Update must be approved, got {update.status}")
    update.status = UpdateStatus.PUBLISHED
    update.published_at = datetime.now()
    # In production: update KB provisions, generate user alerts, update rate tables
    return update


def list_updates(
    status: Optional[UpdateStatus] = None,
) -> list[RegulatoryUpdate]:
    """List regulatory updates, optionally filtered by status."""
    updates = list(_updates.values())
    if status is not None:
        updates = [u for u in updates if u.status == status]
    return sorted(updates, key=lambda u: u.created_at, reverse=True)


def get_update(update_id: str) -> Optional[RegulatoryUpdate]:
    """Get a specific regulatory update."""
    return _updates.get(update_id)


# ── Staleness tracking ───────────────────────────────────────


def record_review(
    provision_id: str,
    reviewer: str,
    next_review_date: date,
) -> StalenessRecord:
    """Record that a provision has been reviewed."""
    record = StalenessRecord(
        provision_id=provision_id,
        last_reviewed=date.today(),
        next_review_date=next_review_date,
        reviewer=reviewer,
    )
    _staleness[provision_id] = record
    return record


def get_stale_provisions() -> list[StalenessRecord]:
    """Get provisions that are past their next review date."""
    today = date.today()
    stale = []
    for record in _staleness.values():
        if record.next_review_date <= today:
            record.is_stale = True
            stale.append(record)
    return sorted(stale, key=lambda r: r.next_review_date)


def get_staleness_summary() -> dict[str, int]:
    """Get a summary of provision staleness status."""
    today = date.today()
    stale_count = sum(1 for r in _staleness.values() if r.next_review_date <= today)
    upcoming_count = sum(
        1
        for r in _staleness.values()
        if today
        < r.next_review_date
        <= date(today.year, today.month + 1 if today.month < 12 else 1, today.day)
    )
    return {
        "total_tracked": len(_staleness),
        "stale": stale_count,
        "upcoming_review": upcoming_count,
        "current": len(_staleness) - stale_count,
    }
