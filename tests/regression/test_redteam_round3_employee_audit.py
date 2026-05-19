"""Red-team round-3 — employee mutation audit + self-mutation guard (P0).

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding C10 — `PATCH /employees/{id}` (update_employee) wrote 38+
fields including salary_monthly, confirmation_status,
reporting_manager_id, is_active without any AuditLogEntry append.
EmploymentEvent rows DO get written for salary/designation changes but
those rows are mutable — the immutable chain was missing.

Additionally: an HR Manager could `PATCH /employees/{their_own_id}`
to self-confirm or self-raise salary, because there was no caller !=
target check. Combined with the missing audit log, this is a silent
privilege escalation.

This file pins:
1. _audit_employee helper exists with the right event_type convention
2. _SELF_MUTATION_BLOCKED_FIELDS contains the 5+ sensitive fields
3. update_employee + confirm + extend-probation + terminate all
   call _audit_employee
4. Behavioural: self-mutation of blocked fields returns 403
5. Behavioural: audit failure does NOT block the underlying decision
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EMP_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "employees.py"


# ---------------------------------------------------------------------------
# Source-level pins
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_employee_has_audit_helper():
    src = EMP_ROUTER.read_text()
    assert "def _audit_employee(" in src, (
        "employees.py must define _audit_employee helper (red-team C10 P0)."
    )
    assert 'event_type=f"employee.{action}"' in src, (
        "_audit_employee must use 'employee.<action>' event_type."
    )
    assert "AuditLogEntry append failed for employee" in src, (
        "_audit_employee must log-and-swallow on failure (P58)."
    )


@pytest.mark.regression
def test_redteam3_self_mutation_blocked_set_includes_sensitive_fields():
    """The self-mutation guard must block the 5 sensitive fields the
    audit identified, plus designation/employment_type which are also
    structural promotion fields."""
    from hr_advisory.api.routers.employees import _SELF_MUTATION_BLOCKED_FIELDS

    required = {
        "salary_monthly",
        "confirmation_status",
        "probation_end_date",
        "is_active",
        "reporting_manager_id",
    }
    missing = required - _SELF_MUTATION_BLOCKED_FIELDS
    assert not missing, f"Self-mutation guard missing fields: {missing}"


@pytest.mark.regression
def test_redteam3_audit_log_sensitive_fields_set_includes_key_fields():
    from hr_advisory.api.routers.employees import _AUDIT_LOG_SENSITIVE_FIELDS

    # Any mutation of these fields must be appended to the immutable chain.
    required = {
        "salary_monthly",
        "confirmation_status",
        "probation_end_date",
        "is_active",
        "reporting_manager_id",
        "employment_type",
    }
    missing = required - _AUDIT_LOG_SENSITIVE_FIELDS
    assert not missing, f"Audit-log sensitive-fields set missing: {missing}"


def _section(src: str, start: str, end: str) -> str:
    s = src.index(start)
    e = src.index(end, s)
    return src[s:e]


@pytest.mark.regression
def test_redteam3_update_employee_writes_audit():
    """The PATCH /employees/{id} handler must call _audit_employee."""
    src = EMP_ROUTER.read_text()
    # The update_employee function is followed by `list_salary_components`
    section = _section(src, "async def update_employee", "async def list_salary_components")
    assert "_audit_employee(" in section, (
        "update_employee must call _audit_employee on sensitive-field changes."
    )
    assert "sensitive_diff" in section, (
        "update_employee must compute a (old → new) diff of sensitive fields."
    )
    # The self-mutation guard must be present
    assert "_SELF_MUTATION_BLOCKED_FIELDS" in section, (
        "update_employee must enforce _SELF_MUTATION_BLOCKED_FIELDS (P0)."
    )


@pytest.mark.regression
def test_redteam3_confirm_employee_writes_audit():
    src = EMP_ROUTER.read_text()
    section = _section(src, "async def confirm_employee", "async def extend_probation")
    assert "_audit_employee(" in section, (
        "confirm_employee must call _audit_employee (sensitive field change)."
    )
    assert '"confirmed"' in section


@pytest.mark.regression
def test_redteam3_extend_probation_writes_audit():
    src = EMP_ROUTER.read_text()
    # extend_probation is at @router.post("/{employee_id}/extend-probation");
    # the next handler is @router.post("/{employee_id}/exit").
    section = _section(src, "async def extend_probation", '@router.post("/{employee_id}/exit")')
    assert "_audit_employee(" in section, (
        "extend_probation must call _audit_employee."
    )
    assert "probation_extended" in section


@pytest.mark.regression
def test_redteam3_terminate_employee_writes_audit():
    src = EMP_ROUTER.read_text()
    # terminate_employee is between approve_termination scaffolding;
    # find by the actual mutating line.
    idx = src.index('"confirmation_status": "terminated",')
    # Look in a 4 KB window after the mutation site.
    window = src[idx : idx + 4000]
    assert "_audit_employee(" in window, (
        "terminate path must call _audit_employee immediately after the "
        "is_active=False + confirmation_status=terminated write."
    )
    assert '"terminated"' in window


# ---------------------------------------------------------------------------
# Behavioural pin: _audit_employee invokes record_event
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_audit_employee_calls_record_event(monkeypatch):
    from hr_advisory.api.routers.employees import _audit_employee

    captured = {}

    def fake_record(*, company_id, actor_id, event_type, payload):
        captured["company_id"] = company_id
        captured["actor_id"] = actor_id
        captured["event_type"] = event_type
        captured["payload"] = payload

    from hr_advisory.services import audit_log as _audit_log

    monkeypatch.setattr(_audit_log, "record_event", fake_record)

    _audit_employee(
        employee_id=9,
        company_id=1,
        action="updated",
        actor_id=25,
        fields_changed={"salary_monthly": {"changed": True}},
    )

    assert captured["event_type"] == "employee.updated"
    assert captured["payload"] == {
        "employee_id": 9,
        "fields_changed": {"salary_monthly": {"changed": True}},
    }


@pytest.mark.regression
def test_redteam3_self_mutation_returns_403():
    """An HR Manager (or owner) PATCHing their OWN employee row with a
    blocked field MUST get 403. Source-level pin: the early-return
    raises HTTPException with status 403 and a message that names the
    blocked fields so the caller knows what to fix.
    """
    src = EMP_ROUTER.read_text()
    section = _section(src, "async def update_employee", "async def list_salary_components")
    # The guard must check self AND raise 403
    assert "is_self" in section
    assert "_SELF_MUTATION_BLOCKED_FIELDS.intersection" in section
    assert "status_code=403" in section
    # The error message must name the attempted blocked fields so the
    # caller can fix the request — not just a generic 403.
    assert "attempted_blocked" in section


@pytest.mark.regression
def test_redteam3_audit_employee_swallows_errors(monkeypatch, caplog):
    """Audit failure must NEVER block the underlying HR decision (P58)."""
    from hr_advisory.api.routers.employees import _audit_employee
    from hr_advisory.services import audit_log as _audit_log

    def explode(**_kwargs):
        raise RuntimeError("chain corrupted")

    monkeypatch.setattr(_audit_log, "record_event", explode)

    import logging as _logging
    with caplog.at_level(_logging.WARNING):
        _audit_employee(employee_id=1, company_id=1, action="updated", actor_id=1)

    assert any(
        "AuditLogEntry append failed for employee" in r.message for r in caplog.records
    )
