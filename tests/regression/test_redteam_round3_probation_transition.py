"""Red-team round-3 — probation auto-transition (P1).

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding M5 / O8 — Marcus Tan was sitting at confirmation_status =
"on_probation" with probation_end_date = "" for 6 weeks past his
expected probation end. Root cause:

  1. Employee create never computed probation_end_date from
     start_date + probation_months.
  2. There was no scheduler to flip on_probation → confirmed when the
     period elapsed.

This file pins:
  - services.probation.compute_probation_end_date is deterministic.
  - Employee create paths invoke ensure_probation_end_date_in_payload.
  - The auto-confirm sweep flips the right rows and writes both an
    EmploymentEvent and an AuditLogEntry (P58) — and is idempotent.
  - platform.py registers the daily scheduler.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EMP_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "employees.py"
AUTH_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "auth.py"
PLATFORM = REPO_ROOT / "src" / "hr_advisory" / "api" / "platform.py"


# ---------------------------------------------------------------------------
# compute_probation_end_date — deterministic math
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_compute_probation_basic():
    from hr_advisory.services.probation import compute_probation_end_date

    # Marcus's exact case from the live walk
    assert compute_probation_end_date("2026-01-06", 3) == "2026-04-06"
    # 1-month probation starting end-of-January handles short-month edge
    assert compute_probation_end_date("2026-01-31", 1) == "2026-02-28"
    # 6-month probation
    assert compute_probation_end_date("2026-01-01", 6) == "2026-07-01"


@pytest.mark.regression
def test_redteam3_compute_probation_handles_missing_input():
    from hr_advisory.services.probation import compute_probation_end_date

    assert compute_probation_end_date("", 3) == ""
    assert compute_probation_end_date(None, 3) == ""
    assert compute_probation_end_date("not-a-date", 3) == ""
    # Negative / zero months → empty (no probation)
    assert compute_probation_end_date("2026-01-01", 0) == ""
    assert compute_probation_end_date("2026-01-01", -1) == ""


# ---------------------------------------------------------------------------
# ensure_probation_end_date_in_payload — mutates create payload
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_ensure_writes_into_payload():
    from hr_advisory.services.probation import ensure_probation_end_date_in_payload

    payload = {"start_date": "2026-01-06", "probation_months": 3}
    ensure_probation_end_date_in_payload(payload)
    assert payload["probation_end_date"] == "2026-04-06"


@pytest.mark.regression
def test_redteam3_ensure_respects_caller_override():
    """If the caller already provided probation_end_date, leave it alone.
    Manual override wins so HR can set non-default dates."""
    from hr_advisory.services.probation import ensure_probation_end_date_in_payload

    payload = {
        "start_date": "2026-01-06",
        "probation_months": 3,
        "probation_end_date": "2026-12-31",
    }
    ensure_probation_end_date_in_payload(payload)
    assert payload["probation_end_date"] == "2026-12-31"


@pytest.mark.regression
def test_redteam3_ensure_handles_missing_start_date():
    """No start_date → no probation_end_date — graceful empty fallback."""
    from hr_advisory.services.probation import ensure_probation_end_date_in_payload

    payload = {"probation_months": 3}
    ensure_probation_end_date_in_payload(payload)
    assert "probation_end_date" not in payload or not payload["probation_end_date"]


# ---------------------------------------------------------------------------
# Source-level pins — Employee create paths invoke the helper
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_employees_create_wires_probation_helper():
    src = EMP_ROUTER.read_text()
    create_section = src[src.index("def _create_employee(data: dict)") :]
    create_section = create_section[: 800]
    assert "ensure_probation_end_date_in_payload" in create_section, (
        "_create_employee MUST call ensure_probation_end_date_in_payload "
        "so every new Employee gets a deterministic probation_end_date."
    )


@pytest.mark.regression
def test_redteam3_auth_invite_accept_wires_probation_helper():
    src = AUTH_ROUTER.read_text()
    assert "ensure_probation_end_date_in_payload" in src, (
        "auth.py invitation-accept path MUST set probation_end_date "
        "before creating the Employee row."
    )


@pytest.mark.regression
def test_redteam3_update_employee_recomputes_probation_end():
    """When start_date or probation_months changes via PATCH, the
    handler must recompute probation_end_date (unless the caller
    supplied one explicitly)."""
    src = EMP_ROUTER.read_text()
    section = src[src.index("async def update_employee") : src.index("async def list_salary_components")]
    assert "compute_probation_end_date" in section
    assert "start_date" in section and "probation_months" in section


# ---------------------------------------------------------------------------
# auto_confirm_due_probations — behavioural pins
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_auto_confirm_flips_status_and_writes_chain():
    """An employee whose probation_end_date is past today should be flipped
    to confirmed AND a row appended to the immutable chain."""
    from hr_advisory.services import probation as probation_svc

    fake_rows = [
        {
            "id": 9,
            "company_id": 1,
            "start_date": "2026-01-06",
            "probation_months": 3,
            "probation_end_date": "2026-04-06",
            "confirmation_status": "on_probation",
            "is_active": True,
        }
    ]
    updates = []
    audit_events = []
    events_created = []

    with (
        patch("hr_advisory.services.dataflow_crud.list_records", return_value=fake_rows),
        patch(
            "hr_advisory.services.dataflow_crud.update",
            side_effect=lambda model, rid, payload: updates.append((model, rid, payload)),
        ),
        patch(
            "hr_advisory.services.dataflow_crud.create",
            side_effect=lambda model, payload: events_created.append((model, payload)),
        ),
        patch(
            "hr_advisory.services.audit_log.record_event",
            side_effect=lambda **kw: audit_events.append(kw),
        ),
    ):
        summary = probation_svc.auto_confirm_due_probations(as_of=date(2026, 5, 19))

    assert summary["confirmed"] == 1, summary
    assert any(
        u[0] == "Employee" and u[2].get("confirmation_status") == "confirmed"
        for u in updates
    ), updates
    assert any(p[0] == "EmploymentEvent" for p in events_created), events_created
    assert any(e["event_type"] == "employee.auto_confirmed" for e in audit_events), audit_events


@pytest.mark.regression
def test_redteam3_auto_confirm_backfills_missing_end_date():
    """Marcus's exact bug: on_probation employee whose probation_end_date
    is empty should get backfilled from start_date, then flipped."""
    from hr_advisory.services import probation as probation_svc

    fake_rows = [
        {
            "id": 9,
            "company_id": 1,
            "start_date": "2026-01-06",
            "probation_months": 3,
            "probation_end_date": "",  # the bug from M5
            "confirmation_status": "on_probation",
            "is_active": True,
        }
    ]
    updates = []
    with (
        patch("hr_advisory.services.dataflow_crud.list_records", return_value=fake_rows),
        patch(
            "hr_advisory.services.dataflow_crud.update",
            side_effect=lambda model, rid, payload: updates.append(payload),
        ),
        patch("hr_advisory.services.dataflow_crud.create"),
        patch("hr_advisory.services.audit_log.record_event"),
    ):
        summary = probation_svc.auto_confirm_due_probations(as_of=date(2026, 5, 19))

    # First write backfills the date; second write confirms the status.
    assert any("probation_end_date" in u for u in updates), updates
    assert any(u.get("confirmation_status") == "confirmed" for u in updates), updates
    assert summary["confirmed"] == 1


@pytest.mark.regression
def test_redteam3_auto_confirm_is_idempotent():
    """Running the sweep twice in a single day must not double-write or flip
    already-confirmed employees."""
    from hr_advisory.services import probation as probation_svc

    # Second-pass view: already confirmed, no rows match the on_probation filter.
    with (
        patch("hr_advisory.services.dataflow_crud.list_records", return_value=[]),
        patch("hr_advisory.services.dataflow_crud.update") as upd,
        patch("hr_advisory.services.dataflow_crud.create") as cr,
        patch("hr_advisory.services.audit_log.record_event") as audit,
    ):
        summary = probation_svc.auto_confirm_due_probations(as_of=date(2026, 5, 19))

    assert summary == {"checked": 0, "confirmed": 0, "errors": []}
    upd.assert_not_called()
    cr.assert_not_called()
    audit.assert_not_called()


@pytest.mark.regression
def test_redteam3_auto_confirm_skips_employees_still_in_window():
    """Probation ends 1 Aug; we sweep on 19 May → no flip."""
    from hr_advisory.services import probation as probation_svc

    fake_rows = [
        {
            "id": 11,
            "company_id": 1,
            "start_date": "2026-05-01",
            "probation_months": 3,
            "probation_end_date": "2026-08-01",
            "confirmation_status": "on_probation",
            "is_active": True,
        }
    ]
    with (
        patch("hr_advisory.services.dataflow_crud.list_records", return_value=fake_rows),
        patch("hr_advisory.services.dataflow_crud.update") as upd,
        patch("hr_advisory.services.dataflow_crud.create"),
        patch("hr_advisory.services.audit_log.record_event"),
    ):
        summary = probation_svc.auto_confirm_due_probations(as_of=date(2026, 5, 19))

    assert summary["confirmed"] == 0
    upd.assert_not_called()


# ---------------------------------------------------------------------------
# Platform startup wiring
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_platform_registers_lifecycle_tick():
    src = PLATFORM.read_text()
    assert "_register_daily_lifecycle_ticks" in src, (
        "platform.py MUST register a daily lifecycle tick."
    )
    assert "auto_confirm_due_probations" in src, (
        "lifecycle tick MUST invoke probation.auto_confirm_due_probations."
    )
    # The env-disable flag exists so tests / CI don't fire the loop.
    assert "ARBOR_DISABLE_BACKGROUND_TICKS" in src
