"""Red-team round-3 — payroll audit-log + rate-limit (P0 security).

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding C10 — payroll.py approve_payroll_run, mark_payroll_paid,
cancel_payroll_run wrote `status` changes to the mutable PayrollRun
record but never appended to the immutable hash-chained
AuditLogEntry. These are the highest-financial-impact endpoints in
the system (one approve cascades to every payslip + every approved
claim for the period). Per pattern P58 they MUST dual-write.

Also: no `check_rate_limit` on any of the three — a leaked HR JWT
could brute-force approve/mark-paid/cancel hundreds of runs.

Source-level pins prevent regression; the helper signature and the
event_type prefix are both pinned so future refactors that drop the
audit call are caught at test time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYROLL_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "payroll.py"


# ---------------------------------------------------------------------------
# Helper exists, with the correct event-type convention.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_payroll_has_audit_helper():
    src = PAYROLL_ROUTER.read_text()
    assert "def _audit_payroll(" in src, (
        "payroll.py must define _audit_payroll helper (red-team C10 P0)."
    )
    assert 'event_type=f"payroll.{action}"' in src, (
        "_audit_payroll must use 'payroll.<action>' event_type so the "
        "AuditLogEntry chain is queryable by entity prefix (P58)."
    )
    # P58: audit failure NEVER blocks the underlying HR decision
    assert "AuditLogEntry append failed for payroll" in src, (
        "_audit_payroll must log-and-swallow on failure (P58 last paragraph)."
    )


# ---------------------------------------------------------------------------
# Each of the 3 financial endpoints calls _audit_payroll + check_rate_limit.
# ---------------------------------------------------------------------------


def _section(src: str, start: str, end: str) -> str:
    s = src.index(start)
    e = src.index(end, s)
    return src[s:e]


@pytest.mark.regression
def test_redteam3_payroll_approve_writes_audit_and_rate_limit():
    src = PAYROLL_ROUTER.read_text()
    section = _section(src, "async def approve_payroll_run", "async def mark_payroll_paid")
    assert "_audit_payroll(" in section, (
        "approve_payroll_run must call _audit_payroll (red-team C10 P0)."
    )
    assert '"approved"' in section, "Audit must record the 'approved' action."
    assert 'check_rate_limit(\n        f"payroll_approve:' in section, (
        "approve_payroll_run must call check_rate_limit (red-team P1)."
    )


@pytest.mark.regression
def test_redteam3_payroll_mark_paid_writes_audit_and_rate_limit():
    src = PAYROLL_ROUTER.read_text()
    section = _section(src, "async def mark_payroll_paid", "async def cancel_payroll_run")
    assert "_audit_payroll(" in section, (
        "mark_payroll_paid must call _audit_payroll."
    )
    assert '"marked_paid"' in section, (
        "Audit must record the 'marked_paid' action (distinct from 'approved')."
    )
    assert 'check_rate_limit(\n        f"payroll_mark_paid:' in section, (
        "mark_payroll_paid must call check_rate_limit."
    )


@pytest.mark.regression
def test_redteam3_payroll_cancel_writes_audit_and_rate_limit():
    src = PAYROLL_ROUTER.read_text()
    # The cancel block ends at the next handler — get_my_payslips.
    section = _section(src, "async def cancel_payroll_run", "async def get_my_payslips")
    assert "_audit_payroll(" in section, (
        "cancel_payroll_run must call _audit_payroll."
    )
    assert '"cancelled"' in section, "Audit must record the 'cancelled' action."
    assert 'check_rate_limit(\n        f"payroll_cancel:' in section, (
        "cancel_payroll_run must call check_rate_limit."
    )


# ---------------------------------------------------------------------------
# Behavioural pin: _audit_payroll wires through services.audit_log.record_event.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_audit_payroll_calls_record_event(monkeypatch):
    """The helper must actually invoke services.audit_log.record_event.

    Pinned because earlier round-2 work had a near-miss where a helper
    was added but never invoked record_event (silent no-op). We pin the
    invocation so future refactors of audit_log can't silently break
    payroll audit.
    """
    from hr_advisory.api.routers.payroll import _audit_payroll

    captured = {}

    def fake_record(*, company_id, actor_id, event_type, payload):
        captured["company_id"] = company_id
        captured["actor_id"] = actor_id
        captured["event_type"] = event_type
        captured["payload"] = payload

    from hr_advisory.services import audit_log as _audit_log

    monkeypatch.setattr(_audit_log, "record_event", fake_record)

    _audit_payroll(
        run_id=42,
        company_id=1,
        action="approved",
        actor_id=99,
        details={"total_gross": 100_000, "period_end": "2026-04-30"},
    )

    assert captured["company_id"] == 1
    assert captured["actor_id"] == 99
    assert captured["event_type"] == "payroll.approved"
    assert captured["payload"] == {
        "run_id": 42,
        "details": {"total_gross": 100_000, "period_end": "2026-04-30"},
    }


@pytest.mark.regression
def test_redteam3_audit_payroll_swallows_errors(monkeypatch, caplog):
    """Audit failure MUST NOT block the HR decision (P58 last paragraph).

    If record_event raises, _audit_payroll logs a warning and returns
    None — the caller (approve/mark-paid/cancel handler) carries on so
    the user-facing operation succeeds.
    """
    from hr_advisory.api.routers.payroll import _audit_payroll
    from hr_advisory.services import audit_log as _audit_log

    def explode(**_kwargs):
        raise RuntimeError("chain corrupted")

    monkeypatch.setattr(_audit_log, "record_event", explode)

    # Must NOT raise. The handler upstream depends on this.
    import logging as _logging
    with caplog.at_level(_logging.WARNING):
        _audit_payroll(run_id=1, company_id=1, action="approved", actor_id=1)

    assert any("AuditLogEntry append failed for payroll" in r.message for r in caplog.records)
