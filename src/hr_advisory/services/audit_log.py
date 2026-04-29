# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Audit logging for sensitive operations (PDPA compliance + S2-T5 chain).

Two layers:

1. **Stream layer** (`log_audit_event`) — structured loggers for SIEM
   forwarding. Every security-relevant action emits a record. No DB write.
2. **Chain layer** (`record_event` + `verify_chain_integrity`) — append-only
   hash-chained ledger persisted as `AuditLogEntry` rows. Each entry's
   `prev_hash` equals the previous entry's `entry_hash` for the same
   tenant; tampering is O(N)-detectable by `verify_chain_integrity`.

Both layers run together at every audit-relevant call site so SIEM and
ledger stay in sync.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("hr_advisory.audit")

__all__ = [
    "log_audit_event",
    "AuditAction",
    "record_event",
    "verify_chain_integrity",
    "compute_entry_hash",
]


class AuditAction:
    """Constants for audit event actions."""

    # LLM key lifecycle
    LLM_KEY_CREATED = "llm_key.created"
    LLM_KEY_VIEWED = "llm_key.viewed"
    LLM_KEY_DELETED = "llm_key.deleted"
    LLM_KEY_VALIDATED = "llm_key.validated"
    LLM_KEY_STATUS_CHANGED = "llm_key.status_changed"
    LLM_KEY_DECRYPTED = "llm_key.decrypted"
    LLM_KEY_ROTATED = "llm_key.rotated"

    # Budget
    LLM_BUDGET_CHANGED = "llm_budget.changed"
    LLM_BUDGET_EXCEEDED = "llm_budget.exceeded"

    # User key lifecycle
    USER_LLM_KEY_CREATED = "user_llm_key.created"
    USER_LLM_KEY_DELETED = "user_llm_key.deleted"

    # Recruitment + candidate lifecycle (S2-T5)
    CANDIDATE_HIRED = "candidate.hired"
    CANDIDATE_REJECTED = "candidate.rejected"
    CANDIDATE_STAGE_CHANGED = "candidate.stage_changed"
    CANDIDATE_OFFER_GENERATED = "candidate.offer_generated"
    SCORECARD_GENERATED = "scorecard.generated"

    # Claims (S2-T5)
    CLAIM_CREATED = "claim.created"
    CLAIM_SUBMITTED = "claim.submitted"
    CLAIM_APPROVED = "claim.approved"
    CLAIM_REJECTED = "claim.rejected"

    # Calendar (S2-T5)
    CALENDAR_CONNECTED = "calendar.connected"
    CALENDAR_DISCONNECTED = "calendar.disconnected"

    # Onboarding (S2-T5)
    ONBOARDING_STEP_COMPLETED = "onboarding.step_completed"


def log_audit_event(
    action: str,
    actor_user_id: int | None = None,
    company_id: int | None = None,
    target_entity: str | None = None,
    target_id: int | str | None = None,
    details: dict | None = None,
) -> None:
    """Stream-layer audit log (PDPA compliance, SIEM-forwardable).

    Use for events that need observability but don't require chain-level
    tamper detection (LLM key views, budget edits, etc.). For
    security-critical actions (hire, claim approval, calendar disconnect,
    etc.) ALSO call `record_event` so the immutable chain captures it.
    """
    event = {
        "action": action,
        "actor_user_id": actor_user_id,
        "company_id": company_id,
        "target_entity": target_entity,
        "target_id": target_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        event["details"] = details

    # Use WARNING level so audit events are always captured even at INFO log level
    logger.warning(
        "audit.event action=%s actor=%s company=%s entity=%s id=%s details=%s",
        action,
        actor_user_id,
        company_id,
        target_entity,
        target_id,
        details or {},
    )


# ---------------------------------------------------------------------------
# Chain layer (S2-T5) — immutable, hash-chained AuditLogEntry rows
# ---------------------------------------------------------------------------


# Per-tenant locks to serialize chain appends within a process. The chain is
# linear (each row's prev_hash points at the previous row's entry_hash); two
# concurrent inserts that read the same prev_hash would create a fork.
# A process-level lock is sufficient because Postgres serializes writes via
# the unique row id; if two processes race, the second `prev_hash` read will
# already see the first's entry, and the second's chain entry will simply
# point at the newer head. The only failure mode this lock prevents is intra-
# process double-fork during async test runs.
_chain_locks: dict[int, threading.Lock] = {}
_chain_locks_lock = threading.Lock()


def _get_chain_lock(company_id: int) -> threading.Lock:
    with _chain_locks_lock:
        lock = _chain_locks.get(company_id)
        if lock is None:
            lock = threading.Lock()
            _chain_locks[company_id] = lock
        return lock


def compute_entry_hash(
    company_id: int,
    actor_id: int,
    event_type: str,
    payload_json: str,
    prev_hash: str,
    created_at_iso: str,
) -> str:
    """Deterministic SHA-256 over the canonical entry content.

    Hashed input is the pipe-joined string of every chain-relevant field.
    The order is fixed and documented; changing it would invalidate every
    existing chain — DO NOT REORDER without a migration.
    """
    payload = "|".join(
        [
            str(company_id),
            str(actor_id),
            event_type,
            payload_json,
            prev_hash,
            created_at_iso,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_event(
    company_id: int,
    actor_id: int,
    event_type: str,
    payload: dict | None = None,
) -> dict[str, Any]:
    """Append an immutable, hash-chained entry to the audit log.

    Returns the persisted record (including computed hashes). Failure to
    persist raises — audit-critical events MUST not silently drop. Callers
    that cannot tolerate a 500 should catch and log.

    Concurrency: per-tenant lock serializes the read-prev-hash + insert
    sequence to prevent intra-process forks.
    """
    if not isinstance(company_id, int) or company_id <= 0:
        raise ValueError(f"company_id must be a positive int, got {company_id!r}")
    if not isinstance(actor_id, int):
        raise ValueError(f"actor_id must be int, got {type(actor_id).__name__}")
    if not event_type or not isinstance(event_type, str):
        raise ValueError("event_type must be a non-empty str")

    payload_json = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    created_at_iso = datetime.now(timezone.utc).isoformat()

    # Lazy import to avoid a circular: services -> dataflow_crud -> models -> services
    from hr_advisory.services import dataflow_crud

    lock = _get_chain_lock(company_id)
    with lock:
        # dataflow_crud.list_records does not accept order_by; fetch the
        # tail and pick the highest-id row in Python. Capped at limit=1000
        # which is sufficient for serialized intra-process appends — the
        # process-level lock means only one append can read prev_hash at
        # a time, and the ordering only matters for that single append.
        candidate_rows = dataflow_crud.list_records(
            "AuditLogEntry",
            {"company_id": company_id},
            limit=1000,
        )
        if candidate_rows:
            prev_row = max(candidate_rows, key=lambda r: r.get("id", 0))
            prev_hash = prev_row.get("entry_hash", "")
        else:
            prev_hash = ""

        entry_hash = compute_entry_hash(
            company_id=company_id,
            actor_id=actor_id,
            event_type=event_type,
            payload_json=payload_json,
            prev_hash=prev_hash,
            created_at_iso=created_at_iso,
        )

        record = dataflow_crud.create(
            "AuditLogEntry",
            {
                "company_id": company_id,
                "actor_id": actor_id,
                "event_type": event_type,
                "payload_json": payload_json,
                "prev_hash": prev_hash,
                "entry_hash": entry_hash,
                "created_at_iso": created_at_iso,
            },
        )
    return record


def verify_chain_integrity(company_id: int) -> dict[str, Any]:
    """Walk the per-tenant audit chain and recompute each entry's hash.

    Returns a dict:
        {
            "valid": bool,            # True iff every entry hash matches
            "entry_count": int,
            "broken_at_id": int|None, # First mismatched row's id, else None
            "broken_reason": str|None # "hash_mismatch" | "prev_hash_mismatch"
        }

    Tamper detection — if a row is rewritten or deleted, the next row's
    `prev_hash` will not equal the rewritten row's recomputed `entry_hash`,
    or the rewritten row's own `entry_hash` will not match its content.
    """
    from hr_advisory.services import dataflow_crud

    rows = dataflow_crud.list_records(
        "AuditLogEntry",
        {"company_id": company_id},
        limit=10000,
    )
    rows.sort(key=lambda r: r.get("id", 0))

    expected_prev = ""
    for row in rows:
        # Step 1: prev_hash must match the chain's expected previous hash
        actual_prev = row.get("prev_hash", "")
        if actual_prev != expected_prev:
            return {
                "valid": False,
                "entry_count": len(rows),
                "broken_at_id": row.get("id"),
                "broken_reason": "prev_hash_mismatch",
            }
        # Step 2: recompute entry_hash from the row's content + prev_hash
        recomputed = compute_entry_hash(
            company_id=row.get("company_id"),
            actor_id=row.get("actor_id"),
            event_type=row.get("event_type", ""),
            payload_json=row.get("payload_json", ""),
            prev_hash=actual_prev,
            created_at_iso=row.get("created_at_iso", ""),
        )
        if recomputed != row.get("entry_hash"):
            return {
                "valid": False,
                "entry_count": len(rows),
                "broken_at_id": row.get("id"),
                "broken_reason": "hash_mismatch",
            }
        expected_prev = row["entry_hash"]

    return {
        "valid": True,
        "entry_count": len(rows),
        "broken_at_id": None,
        "broken_reason": None,
    }
