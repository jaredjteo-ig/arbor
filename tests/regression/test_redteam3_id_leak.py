"""Regression: round-3 redteam — raw-ID leakage across endpoints.

The user found "Employee #6 / #5 / #4" on the My Appraisals tab. A wide
audit revealed the same bug class lurking in 7 endpoints. These tests
pin every endpoint to the contract: list responses MUST resolve every
internal ID to the linked User.name (or candidate name) before reaching
the client.

Live leak that triggered the round:
- /policies/{id}/acknowledgments — both `acknowledged` and
  `not_acknowledged` lists were missing names entirely (acknowledged)
  or trying to read non-existent Employee.full_name (not_acknowledged).

Defensive fixes (code paths that leak when real data lands):
- /projects/{id}/assignments — ProjectAssignment rows had no name
- /projects/timesheets — TimesheetEntry rows had no name or project_name
- /shifts/schedule — return path returned only `schedule` grid; the web
  app expected a flat `assignments` array with employee_name + template_name
- /inventory/requests — InventoryRequest rows had no employee_name
- /employees/{id}/notes — EmployeeNote rows had no created_by_name
"""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Policies acknowledgments — the live-confirmed leak
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_policy_acknowledgments_resolve_names_and_emails(monkeypatch):
    """Round-3 H: list_acknowledgments MUST return full_name + email on
    BOTH the `acknowledged` and `not_acknowledged` lists. Names live on
    User; Employee has no name/email column. Reading emp.get('full_name')
    or emp.get('email') always returns "" — the previous code shipped
    blank columns and a hardcoded "Employee #N" template on the frontend.
    """
    from hr_advisory.api.routers import policies as pol_mod

    employees = [
        {"id": 4, "user_id": 14, "company_id": 1, "is_active": True},
        {"id": 5, "user_id": 15, "company_id": 1, "is_active": True},
        {"id": 6, "user_id": 16, "company_id": 1, "is_active": True},
    ]
    users = [
        {"id": 14, "name": "Alice Tan", "email": "alice@x.sg", "company_id": 1},
        {"id": 15, "name": "Bob Lee", "email": "bob@x.sg", "company_id": 1},
        {"id": 16, "name": "Cher Lim", "email": "cher@x.sg", "company_id": 1},
    ]
    acks = [
        {
            "id": 100,
            "policy_id": 3,
            "version_acknowledged": 1,
            "employee_id": 4,
            "company_id": 1,
            "acknowledged_at": "2026-04-15T08:00:00",
            "ip_address": "10.0.0.1",
        },
    ]

    def fake_read(model, _rid):
        return {
            "id": 3,
            "company_id": 1,
            "version_number": 1,
        }

    def fake_list(model, _filter, **_kw):
        return {
            "PolicyAcknowledgment": acks,
            "Employee": employees,
            "User": users,
        }.get(model, [])

    monkeypatch.setattr(pol_mod.dataflow_crud, "read", fake_read)
    monkeypatch.setattr(pol_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(pol_mod, "get_current_company_id", lambda _u: 1)

    body = asyncio.run(
        pol_mod.list_acknowledgments(
            policy_id=3,
            current_user={"sub": "1", "role": "owner"},
        )
    )

    # Acknowledged row must resolve to a real name + email.
    assert len(body["acknowledged"]) == 1
    ack = body["acknowledged"][0]
    assert ack["full_name"] == "Alice Tan", ack
    assert ack["email"] == "alice@x.sg", ack
    assert ack["employee_id"] == 4
    assert ack["acknowledged_at"] == "2026-04-15T08:00:00"

    # Pending list must include both Bob and Cher with names + emails.
    pending_names = sorted(p["full_name"] for p in body["not_acknowledged"])
    assert pending_names == ["Bob Lee", "Cher Lim"], pending_names
    pending_emails = sorted(p["email"] for p in body["not_acknowledged"])
    assert pending_emails == ["bob@x.sg", "cher@x.sg"], pending_emails


# ---------------------------------------------------------------------------
# Projects — assignments + timesheets
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_project_assignments_resolve_employee_name(monkeypatch):
    """Round-3 M: list_assignments MUST return employee_name on every
    row so the project detail page never falls back to "#${id}"."""
    from hr_advisory.api.routers import projects as pj_mod

    employees = [{"id": 4, "user_id": 14, "company_id": 1}]
    users = [{"id": 14, "name": "Alice Tan", "company_id": 1}]
    assignments = [
        {"id": 1, "project_id": 7, "employee_id": 4, "hourly_rate": 50.0}
    ]

    def fake_list(model, _filter, **_kw):
        return {
            "ProjectAssignment": assignments,
            "Employee": employees,
            "User": users,
        }.get(model, [])

    monkeypatch.setattr(pj_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(
        pj_mod, "_verify_project_ownership", lambda _p, _c: {"id": _p}
    )
    monkeypatch.setattr(pj_mod, "get_current_company_id", lambda _u: 1)

    body = asyncio.run(
        pj_mod.list_assignments(
            project_id=7,
            current_user={"sub": "1", "role": "owner"},
        )
    )
    assert body["assignments"][0]["employee_name"] == "Alice Tan"


@pytest.mark.regression
def test_project_timesheets_resolve_employee_and_project_name(monkeypatch):
    """Round-3 M: list_timesheet_entries MUST return employee_name AND
    project_name on every row so /approvals timesheet tab + /projects
    timesheet tab never render raw IDs."""
    from hr_advisory.api.routers import projects as pj_mod

    employees = [{"id": 4, "user_id": 14, "company_id": 1}]
    users = [{"id": 14, "name": "Alice Tan", "company_id": 1}]
    projects = [{"id": 7, "name": "Mobile App", "company_id": 1}]
    entries = [
        {
            "id": 1,
            "project_id": 7,
            "employee_id": 4,
            "entry_date": "2026-04-01",
            "hours": 4,
        }
    ]

    def fake_list(model, _filter, **_kw):
        return {
            "TimesheetEntry": entries,
            "Employee": employees,
            "User": users,
            "Project": projects,
        }.get(model, [])

    monkeypatch.setattr(pj_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(pj_mod, "get_current_company_id", lambda _u: 1)

    body = asyncio.run(
        pj_mod.list_timesheet_entries(
            project_id=None,
            employee_id=None,
            date_from=None,
            date_to=None,
            current_user={"sub": "1", "role": "owner"},
        )
    )

    e = body["entries"][0]
    assert e["employee_name"] == "Alice Tan"
    assert e["project_name"] == "Mobile App"


# ---------------------------------------------------------------------------
# Shifts — schedule must include flat assignments with employee_name
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_shifts_schedule_returns_flat_assignments_with_names(monkeypatch):
    """Round-3 M: /shifts/schedule MUST return a top-level `assignments`
    array (the web app reads scheduleRes.assignments). Each entry MUST
    include employee_name + template_name so the weekly grid never
    renders "Emp #N"."""
    from hr_advisory.api.routers import shifts as sh_mod

    employees = [
        {
            "id": 4,
            "user_id": 14,
            "company_id": 1,
            "is_active": True,
            "department": "Engineering",
        }
    ]
    users = [{"id": 14, "name": "Alice Tan"}]
    assignments_by_day = [
        {
            "id": 1,
            "company_id": 1,
            "employee_id": 4,
            "shift_template_id": 9,
            "date": "2026-05-04",
        }
    ]
    templates = [
        {"id": 9, "name": "Morning", "start_time": "09:00", "colour": "#aaa"}
    ]

    def fake_list(model, _filter, **_kw):
        if model == "ShiftAssignment":
            return [
                a for a in assignments_by_day if a["date"] == _filter.get("date")
            ]
        return {
            "Employee": employees,
            "ShiftTemplate": templates,
        }.get(model, [])

    def fake_read(_m, uid):
        return next((u for u in users if u["id"] == uid), None)

    monkeypatch.setattr(sh_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(sh_mod.dataflow_crud, "read", fake_read)
    monkeypatch.setattr(sh_mod, "get_current_company_id", lambda _u: 1)

    body = asyncio.run(
        sh_mod.get_weekly_schedule(
            week_start="2026-05-04",
            department=None,
            current_user={"sub": "1", "role": "owner"},
        )
    )

    assert "assignments" in body
    assert len(body["assignments"]) == 1
    a = body["assignments"][0]
    assert a["employee_name"] == "Alice Tan"
    assert a["template_name"] == "Morning"


# ---------------------------------------------------------------------------
# Inventory — requests
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_inventory_requests_resolve_employee_name(monkeypatch):
    """Round-3 M: /inventory/requests MUST return employee_name so the
    Approvals → Inventory Requests tab never says "Employee #N"."""
    from hr_advisory.api.routers import inventory as inv_mod

    employees = [{"id": 4, "user_id": 14, "company_id": 1}]
    users = [{"id": 14, "name": "Alice Tan", "company_id": 1}]
    requests = [
        {"id": 1, "company_id": 1, "employee_id": 4, "status": "pending"}
    ]

    def fake_list(model, _filter, **_kw):
        return {
            "InventoryRequest": requests,
            "Employee": employees,
            "User": users,
        }.get(model, [])

    monkeypatch.setattr(inv_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(inv_mod, "get_current_company_id", lambda _u: 1)

    body = asyncio.run(
        inv_mod.list_item_requests(
            status=None,
            employee_id=None,
            current_user={"sub": "1", "role": "owner"},
        )
    )

    assert body["requests"][0]["employee_name"] == "Alice Tan"


# ---------------------------------------------------------------------------
# Employee notes — created_by → User.name
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_employee_notes_resolve_created_by_name(monkeypatch):
    """Round-3 L: /employees/{id}/notes MUST return created_by_name so
    the timeline never renders "Created by #N"."""
    from hr_advisory.api.routers import employees as emp_mod

    users = [{"id": 99, "name": "HR Admin", "company_id": 1}]
    notes = [
        {
            "id": 1,
            "employee_id": 4,
            "company_id": 1,
            "content": "Note 1",
            "created_by": 99,
            "is_confidential": False,
            "created_at": "2026-05-01T00:00:00",
        }
    ]

    monkeypatch.setattr(
        emp_mod, "_find_employee_by_id", lambda _eid: {"id": 4, "company_id": 1}
    )
    monkeypatch.setattr(emp_mod, "_list_employee_notes", lambda _eid: notes)
    monkeypatch.setattr(emp_mod, "get_current_company_id", lambda _u: 1)
    monkeypatch.setattr(
        emp_mod.dataflow_crud,
        "list_records",
        lambda model, _filter, **_kw: users if model == "User" else [],
    )

    body = asyncio.run(
        emp_mod.list_employee_notes_endpoint(
            employee_id=4,
            current_user={"sub": "1", "role": "owner"},
        )
    )

    assert body["notes"][0]["created_by_name"] == "HR Admin"


# ---------------------------------------------------------------------------
# Shared helper — robustness when the user row is missing
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_resolve_employee_names_handles_missing_user(monkeypatch):
    """Round-3: if an Employee.user_id points at a deleted User row, the
    helper MUST return "" for that employee instead of raising. Keeps
    the listing endpoints crash-safe when historical data drifts."""
    from hr_advisory.api.routers import _helpers as h

    employees = [
        {"id": 4, "user_id": 14, "company_id": 1},
        {"id": 5, "user_id": 999, "company_id": 1},  # orphaned
    ]
    users = [{"id": 14, "name": "Alice Tan", "company_id": 1}]

    def fake_list(model, _filter, **_kw):
        return {"Employee": employees, "User": users}.get(model, [])

    monkeypatch.setattr(h.dataflow_crud, "list_records", fake_list)

    name_map = h._resolve_employee_names({4, 5}, company_id=1)
    assert name_map.get(4) == "Alice Tan"
    # Missing user → not present in the map; callers default to ""
    assert 5 not in name_map
