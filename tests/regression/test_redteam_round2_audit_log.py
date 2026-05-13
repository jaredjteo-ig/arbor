"""Red-team round-2 fixes — immutable audit log + rate limits.

Origin: workspaces/obayashi/04-validate/12-redteam-round2-wider-2026-05-13.md

P1: HR-decision endpoints (leave / timesheet / appraisal-manager-review)
must write to the hash-chained AuditLogEntry, not just stamp
`reviewed_by` on the mutable entity record. Pattern modelled on the
existing `_audit_claim` in routers/claims.py.

P2: same endpoints must be rate-limited so a leaked JWT can't
brute-force approve thousands of records.

Source-level pins prevent regression; behavioural pins exercise
the audit-log path through a mocked `audit_log.record_event`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAVE_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "leave.py"
ATT_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "attendance.py"
APPR_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "appraisals.py"
)


# ---------------------------------------------------------------------------
# Source-level pins — helpers exist, callers reference them.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam2_leave_has_audit_helper():
    src = LEAVE_ROUTER.read_text()
    assert "def _audit_leave(" in src, (
        "leave.py must define _audit_leave helper (red-team P1)."
    )
    assert 'event_type=f"leave.{action}"' in src, (
        "_audit_leave must use 'leave.<action>' event_type so the "
        "AuditLogEntry chain is queryable by entity prefix."
    )


@pytest.mark.regression
def test_redteam2_leave_approve_writes_audit_and_rate_limit():
    src = LEAVE_ROUTER.read_text()
    # approve handler must call both
    approve_section = src[src.index("async def approve_application"):]
    approve_section = approve_section[:approve_section.index("async def reject_application")]
    assert "_audit_leave(" in approve_section, (
        "approve_application must call _audit_leave (red-team P1)."
    )
    assert 'check_rate_limit(\n        f"leave_approve:' in approve_section, (
        "approve_application must call check_rate_limit (red-team P2)."
    )
    # Audit call records the 'approved' action
    assert '"approved"' in approve_section


@pytest.mark.regression
def test_redteam2_leave_reject_writes_audit_and_rate_limit():
    src = LEAVE_ROUTER.read_text()
    reject_section = src[src.index("async def reject_application"):]
    reject_section = reject_section[:reject_section.index("async def withdraw")]
    assert "_audit_leave(" in reject_section, (
        "reject_application must call _audit_leave."
    )
    assert 'check_rate_limit(\n        f"leave_reject:' in reject_section, (
        "reject_application must call check_rate_limit."
    )
    assert '"rejected"' in reject_section


@pytest.mark.regression
def test_redteam2_timesheet_has_audit_helper():
    src = ATT_ROUTER.read_text()
    assert "def _audit_timesheet(" in src
    assert 'event_type=f"timesheet.{action}"' in src


@pytest.mark.regression
def test_redteam2_timesheet_approve_reject_audited_and_rate_limited():
    src = ATT_ROUTER.read_text()
    approve_section = src[src.index("async def approve_timesheet"):]
    approve_section = approve_section[:approve_section.index("async def reject_timesheet")]
    assert "_audit_timesheet(" in approve_section
    assert 'check_rate_limit(\n        f"timesheet_approve:' in approve_section

    reject_section = src[src.index("async def reject_timesheet"):]
    # reject section continues until next handler or end
    end_marker = "@router.get(" if "@router.get(" in reject_section[10:] else None
    if end_marker:
        reject_section = reject_section[:reject_section.index(end_marker, 10)]
    assert "_audit_timesheet(" in reject_section
    assert 'check_rate_limit(\n        f"timesheet_reject:' in reject_section


@pytest.mark.regression
def test_redteam2_appraisal_has_audit_helper():
    src = APPR_ROUTER.read_text()
    assert "def _audit_appraisal(" in src
    assert 'event_type=f"appraisal.{action}"' in src


@pytest.mark.regression
def test_redteam2_appraisal_manager_review_audited():
    src = APPR_ROUTER.read_text()
    mr_section = src[src.index("async def manager_review_appraisal"):]
    mr_section = mr_section[:mr_section.index("@router.post")]  # next route
    assert "_audit_appraisal(" in mr_section, (
        "manager_review_appraisal must call _audit_appraisal "
        "(red-team P1 — new endpoint shipped without audit)."
    )
    assert '"manager_reviewed"' in mr_section


# ---------------------------------------------------------------------------
# Behavioural — the audit_log.record_event gets called with the right
# event_type when the handler reaches the success path.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam2_audit_failure_does_not_block_action(caplog):
    """Audit failures MUST log a warning but NOT raise — HR
    decisions must complete even if the audit subsystem is down.
    """
    import logging

    from hr_advisory.api.routers.leave import _audit_leave

    with patch(
        "hr_advisory.services.audit_log.record_event",
        side_effect=RuntimeError("audit subsystem unavailable"),
    ), caplog.at_level(logging.WARNING, logger="hr_advisory.api.routers.leave"):
        # Must not raise
        _audit_leave(
            application_id=42,
            company_id=1,
            action="approved",
            actor_id=4,
            details={"employee_id": 10},
        )

    assert any(
        "AuditLogEntry append failed" in record.message
        for record in caplog.records
    ), "Audit failure must be logged at WARNING so SRE can alert on it."


@pytest.mark.regression
def test_redteam2_leave_audit_event_type_format():
    """`_audit_leave` must produce event_type='leave.<action>'."""
    from hr_advisory.api.routers.leave import _audit_leave

    captured: dict = {}

    def fake_record(company_id, actor_id, event_type, payload):
        captured["event_type"] = event_type
        captured["payload"] = payload
        return {"id": 1}

    with patch(
        "hr_advisory.services.audit_log.record_event", side_effect=fake_record
    ):
        _audit_leave(
            application_id=99,
            company_id=1,
            action="approved",
            actor_id=4,
            details={"employee_id": 10, "remarks": "ok"},
        )

    assert captured["event_type"] == "leave.approved"
    assert captured["payload"]["leave_application_id"] == 99
    assert captured["payload"]["details"]["remarks"] == "ok"


@pytest.mark.regression
def test_redteam2_timesheet_audit_event_type_format():
    from hr_advisory.api.routers.attendance import _audit_timesheet

    captured: dict = {}

    def fake_record(company_id, actor_id, event_type, payload):
        captured["event_type"] = event_type
        return {"id": 1}

    with patch(
        "hr_advisory.services.audit_log.record_event", side_effect=fake_record
    ):
        _audit_timesheet(50, 1, "rejected", 4)
    assert captured["event_type"] == "timesheet.rejected"


@pytest.mark.regression
def test_redteam2_appraisal_audit_event_type_format():
    from hr_advisory.api.routers.appraisals import _audit_appraisal

    captured: dict = {}

    def fake_record(company_id, actor_id, event_type, payload):
        captured["event_type"] = event_type
        return {"id": 1}

    with patch(
        "hr_advisory.services.audit_log.record_event", side_effect=fake_record
    ):
        _audit_appraisal(100, 1, "manager_reviewed", 4)
    assert captured["event_type"] == "appraisal.manager_reviewed"
