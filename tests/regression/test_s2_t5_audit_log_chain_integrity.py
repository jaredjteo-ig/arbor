"""Regression: S2-T5 — immutable audit log hash chain (round-12 HIGH).

Pins the hash-chain contract:

  1. `compute_entry_hash` is deterministic — same inputs always produce the
     same hash. The argument order is FIXED and load-bearing; any reorder
     invalidates every existing chain.
  2. `record_event` builds a per-tenant chain where each entry's `prev_hash`
     equals the previous entry's `entry_hash` for that company_id.
  3. `verify_chain_integrity` recomputes hashes and detects:
        - Direct row tampering (entry_hash mismatch)
        - prev_hash mismatch (e.g., a row was deleted)
  4. Tenants are isolated — verifying company A's chain ignores company B's.

These tests use mocked dataflow_crud to keep them tier-1 (no real DB
needed). Tier-2/3 tests against real Postgres live in
`tests/integration/test_audit_log_persistence.py` (deferred to next pass).
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Hash function determinism
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t5_compute_entry_hash_is_deterministic():
    """Same inputs always produce the same hash. This is the entire
    foundation of tamper detection — without determinism the chain is
    unverifiable.
    """
    from hr_advisory.services.audit_log import compute_entry_hash

    h1 = compute_entry_hash(
        company_id=1,
        actor_id=10,
        event_type="candidate.hired",
        payload_json='{"candidate_id":5}',
        prev_hash="",
        created_at_iso="2026-04-29T00:00:00+00:00",
    )
    h2 = compute_entry_hash(
        company_id=1,
        actor_id=10,
        event_type="candidate.hired",
        payload_json='{"candidate_id":5}',
        prev_hash="",
        created_at_iso="2026-04-29T00:00:00+00:00",
    )
    assert h1 == h2
    # SHA-256 hex digest
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


@pytest.mark.regression
def test_s2_t5_compute_entry_hash_changes_on_any_field():
    """Changing ANY chain-relevant field must change the hash. This
    guarantees that flipping a single byte in any field is detectable.
    """
    from hr_advisory.services.audit_log import compute_entry_hash

    base_kwargs: dict[str, Any] = dict(
        company_id=1,
        actor_id=10,
        event_type="candidate.hired",
        payload_json='{"candidate_id":5}',
        prev_hash="",
        created_at_iso="2026-04-29T00:00:00+00:00",
    )
    base = compute_entry_hash(**base_kwargs)
    seen = {base}
    for field, mutated_value in [
        ("company_id", 2),
        ("actor_id", 11),
        ("event_type", "candidate.rejected"),
        ("payload_json", '{"candidate_id":6}'),
        ("prev_hash", "deadbeef"),
        ("created_at_iso", "2026-04-29T00:00:01+00:00"),
    ]:
        kwargs = dict(base_kwargs)
        kwargs[field] = mutated_value
        h = compute_entry_hash(**kwargs)
        assert h != base, f"Mutating {field} did not change the hash"
        assert h not in seen, f"Mutating {field} produced a hash collision"
        seen.add(h)


# ---------------------------------------------------------------------------
# Chain construction via record_event
# ---------------------------------------------------------------------------


class _FakeDataflowCrud:
    """In-memory stand-in for dataflow_crud, used to drive record_event +
    verify_chain_integrity through a deterministic state machine.
    """

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._next_id = 1

    def list_records(self, model_name: str, filter_dict: dict, limit: int = 10000):
        assert model_name == "AuditLogEntry"
        company_id = filter_dict.get("company_id")
        return [r for r in self.rows if r["company_id"] == company_id][:limit]

    def create(self, model_name: str, fields: dict):
        assert model_name == "AuditLogEntry"
        record = dict(fields)
        record["id"] = self._next_id
        self._next_id += 1
        self.rows.append(record)
        return record


@pytest.mark.regression
def test_s2_t5_first_entry_has_empty_prev_hash():
    """The genesis entry per tenant has prev_hash="" — no prior row to
    chain to. Every subsequent entry's prev_hash matches the previous
    entry's entry_hash.
    """
    from hr_advisory.services import audit_log as audit_module

    fake = _FakeDataflowCrud()
    with patch("hr_advisory.services.dataflow_crud.list_records", fake.list_records), \
         patch("hr_advisory.services.dataflow_crud.create", fake.create):
        r1 = audit_module.record_event(1, 10, "candidate.hired", {"candidate_id": 5})
        r2 = audit_module.record_event(1, 10, "candidate.rejected", {"candidate_id": 6})
        r3 = audit_module.record_event(1, 10, "candidate.stage_changed", {"candidate_id": 7})

    assert r1["prev_hash"] == ""
    assert r2["prev_hash"] == r1["entry_hash"]
    assert r3["prev_hash"] == r2["entry_hash"]
    # Each entry hash is unique
    assert len({r1["entry_hash"], r2["entry_hash"], r3["entry_hash"]}) == 3


@pytest.mark.regression
def test_s2_t5_per_tenant_chains_are_isolated():
    """Two companies' chains are independent — company B's first entry
    has prev_hash="" even though company A already has entries.
    """
    from hr_advisory.services import audit_log as audit_module

    fake = _FakeDataflowCrud()
    with patch("hr_advisory.services.dataflow_crud.list_records", fake.list_records), \
         patch("hr_advisory.services.dataflow_crud.create", fake.create):
        a1 = audit_module.record_event(1, 10, "candidate.hired", {"id": 1})
        b1 = audit_module.record_event(2, 20, "candidate.hired", {"id": 2})
        a2 = audit_module.record_event(1, 10, "candidate.rejected", {"id": 3})
        b2 = audit_module.record_event(2, 20, "candidate.rejected", {"id": 4})

    assert a1["prev_hash"] == ""
    assert b1["prev_hash"] == "", "Company B's first entry must NOT chain to company A"
    assert a2["prev_hash"] == a1["entry_hash"]
    assert b2["prev_hash"] == b1["entry_hash"]


# ---------------------------------------------------------------------------
# Tamper detection via verify_chain_integrity
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t5_verify_clean_chain_returns_valid():
    from hr_advisory.services import audit_log as audit_module

    fake = _FakeDataflowCrud()
    with patch("hr_advisory.services.dataflow_crud.list_records", fake.list_records), \
         patch("hr_advisory.services.dataflow_crud.create", fake.create):
        for i in range(3):
            audit_module.record_event(1, 10, f"event.{i}", {"i": i})
        result = audit_module.verify_chain_integrity(1)

    assert result["valid"] is True
    assert result["entry_count"] == 3
    assert result["broken_at_id"] is None
    assert result["broken_reason"] is None


@pytest.mark.regression
def test_s2_t5_verify_detects_payload_tamper():
    """If a row's payload is rewritten without recomputing the hash, the
    verifier reports hash_mismatch at that row.
    """
    from hr_advisory.services import audit_log as audit_module

    fake = _FakeDataflowCrud()
    with patch("hr_advisory.services.dataflow_crud.list_records", fake.list_records), \
         patch("hr_advisory.services.dataflow_crud.create", fake.create):
        audit_module.record_event(1, 10, "claim.approved", {"amount": 100})
        audit_module.record_event(1, 10, "claim.approved", {"amount": 200})
        audit_module.record_event(1, 10, "claim.approved", {"amount": 300})

        # Tamper: rewrite row 2's payload (e.g., a malicious admin tool
        # changing the approved amount from 200 to 999) WITHOUT updating
        # entry_hash.
        fake.rows[1]["payload_json"] = json.dumps({"amount": 999}, separators=(",", ":"))

        result = audit_module.verify_chain_integrity(1)

    assert result["valid"] is False
    assert result["broken_at_id"] == 2
    assert result["broken_reason"] == "hash_mismatch"


@pytest.mark.regression
def test_s2_t5_verify_detects_row_deletion():
    """Deleting row N from the middle breaks the chain — row N+1's
    `prev_hash` no longer matches row N-1's `entry_hash`.
    """
    from hr_advisory.services import audit_log as audit_module

    fake = _FakeDataflowCrud()
    with patch("hr_advisory.services.dataflow_crud.list_records", fake.list_records), \
         patch("hr_advisory.services.dataflow_crud.create", fake.create):
        audit_module.record_event(1, 10, "event.1", {})
        audit_module.record_event(1, 10, "event.2", {})
        audit_module.record_event(1, 10, "event.3", {})
        audit_module.record_event(1, 10, "event.4", {})

        # Tamper: delete row 2 entirely (e.g., a privileged user issuing
        # DELETE on the table).
        fake.rows = [r for r in fake.rows if r["id"] != 2]

        result = audit_module.verify_chain_integrity(1)

    # The verifier walks the chain in id order. After id=1 the next row is
    # id=3 whose prev_hash points at id=2 — broken.
    assert result["valid"] is False
    assert result["broken_at_id"] == 3
    assert result["broken_reason"] == "prev_hash_mismatch"


@pytest.mark.regression
def test_s2_t5_verify_empty_chain_is_valid():
    """A tenant with no entries is trivially valid (count=0).
    """
    from hr_advisory.services import audit_log as audit_module

    fake = _FakeDataflowCrud()
    with patch("hr_advisory.services.dataflow_crud.list_records", fake.list_records), \
         patch("hr_advisory.services.dataflow_crud.create", fake.create):
        result = audit_module.verify_chain_integrity(999)

    assert result == {
        "valid": True,
        "entry_count": 0,
        "broken_at_id": None,
        "broken_reason": None,
    }


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t5_record_event_rejects_invalid_company_id():
    from hr_advisory.services.audit_log import record_event

    with pytest.raises(ValueError):
        record_event(0, 10, "test")  # company_id must be > 0
    with pytest.raises(ValueError):
        record_event(-1, 10, "test")
    with pytest.raises(ValueError):
        record_event("1", 10, "test")  # type: ignore[arg-type]


@pytest.mark.regression
def test_s2_t5_record_event_rejects_empty_event_type():
    from hr_advisory.services.audit_log import record_event

    with pytest.raises(ValueError):
        record_event(1, 10, "")
    with pytest.raises(ValueError):
        record_event(1, 10, None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Source-level wiring guards
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t5_log_candidate_activity_writes_chain():
    """`recruitment._log_candidate_activity` must dual-write to the chain
    so every recruitment event (hire, reject, stage change, scorecard,
    offer generated) is captured immutably.
    """
    import inspect

    from hr_advisory.api.routers import recruitment as recruitment_module

    src = inspect.getsource(recruitment_module._log_candidate_activity)
    assert "audit_log" in src or "record_event" in src, (
        "_log_candidate_activity must dual-write to the immutable chain — "
        "the mutable Candidate.notes field can be rewritten by a buggy "
        "admin tool, but the chain entry cannot be silently altered."
    )


@pytest.mark.regression
def test_s2_t5_audit_claim_writes_chain():
    """`claims._audit_claim` must dual-write to the chain so every claim
    transition (created, submitted, approved, rejected) is captured
    immutably.
    """
    import inspect

    from hr_advisory.api.routers import claims as claims_module

    src = inspect.getsource(claims_module._audit_claim)
    assert "audit_log" in src or "record_event" in src, (
        "_audit_claim must dual-write to the immutable chain so a buggy "
        "tool that overwrites ClaimAuditEntry rows is detectable."
    )
