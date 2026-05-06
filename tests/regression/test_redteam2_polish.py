"""Regression: round-2 redteam polish (M + L findings).

These pin the smaller-but-customer-visible fixes from round-2:
- Activity feed entries resolve internal IDs to human-readable names
- Exit-survey preflight returns semantic reasons (invalid / not_found /
  already_submitted) instead of leaking the bare 401 from token decode
- Training records PATCH endpoint accepts editable fields and rejects
  attempts to retarget the record to a different employee
"""
from __future__ import annotations

import pytest


@pytest.mark.regression
def test_activity_feed_humanizes_employee_ids(monkeypatch):
    """Round-2 L: activity summaries must NOT contain "employee #N" or
    "assignment #N" — every internal id is resolved to a user/employee
    name before the feed reaches the client."""
    from hr_advisory.api.routers import strategy as strategy_mod

    employees = [
        {"id": 1, "user_id": 11, "designation": "MD"},
        {"id": 2, "user_id": 12, "designation": "Engineer"},
    ]
    users = [
        {"id": 11, "name": "Tanaka Hiroshi"},
        {"id": 12, "name": "Lim Mei"},
    ]
    candidates = [{"id": 99, "name": "Ada Lovelace"}]
    assignments = [{"id": 7, "employee_id": 1}]
    interviews = [
        {
            "candidate_id": 99,
            "status": "scheduled",
            "created_at": "2999-01-01T00:00:00",
        }
    ]
    progresses = [
        {
            "assignment_id": 7,
            "status": "completed",
            "completed_at": "2999-01-01T00:00:00",
        }
    ]
    appraisals = [
        {
            "employee_id": 2,
            "status": "submitted",
            "submitted_at": "2999-01-01T00:00:00",
        }
    ]
    events = [
        {
            "employee_id": 1,
            "event_type": "PROMOTED",
            "created_at": "2999-01-01T00:00:00",
        }
    ]

    def fake_list(model, _filter, **_kw):
        return {
            "User": users,
            "Candidate": candidates,
            "OnboardingAssignment": assignments,
            "OnboardingStepProgress": progresses,
            "Appraisal": appraisals,
            "InterviewSchedule": interviews,
        }.get(model, [])

    monkeypatch.setattr(strategy_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(strategy_mod, "_events_for_company", lambda _c: events)
    monkeypatch.setattr(strategy_mod, "_safe_list", lambda *_a, **_k: [])

    feed = strategy_mod._activity(company_id=1, employees=employees)

    summaries = [r["summary"] for r in feed]
    joined = " | ".join(summaries)
    assert "employee #" not in joined, joined
    assert "assignment #" not in joined, joined
    assert "candidate #" not in joined, joined
    assert "Tanaka Hiroshi" in joined or "Lim Mei" in joined
    assert "Ada Lovelace" in joined


@pytest.mark.regression
def test_exit_survey_preflight_returns_semantic_reason(monkeypatch):
    """Round-2 L: the preflight endpoint must return a semantic body
    (ok / invalid_or_expired / not_found / already_submitted) so the
    frontend can render the correct empty state."""
    from hr_advisory.api.routers import exit_interviews as ei_mod

    # Case 1: invalid token → ok=False, reason=invalid_or_expired
    from fastapi import HTTPException

    def raise_invalid(_t):
        raise HTTPException(status_code=401, detail="Invalid token.")

    monkeypatch.setattr(ei_mod, "_decode_token", raise_invalid)
    import asyncio

    body = asyncio.run(ei_mod.validate_token("bad-token"))
    assert body["ok"] is False
    assert body["reason"] == "invalid_or_expired"

    # Case 2: token decodes but interview is gone
    monkeypatch.setattr(
        ei_mod, "_decode_token", lambda _t: {"ei": 99, "co": 1}
    )
    monkeypatch.setattr(
        ei_mod.dataflow_crud, "list_records", lambda *_a, **_k: []
    )
    body = asyncio.run(ei_mod.validate_token("ok-but-missing"))
    assert body["ok"] is False
    assert body["reason"] == "not_found"

    # Case 3: already submitted
    monkeypatch.setattr(
        ei_mod.dataflow_crud,
        "list_records",
        lambda *_a, **_k: [
            {"id": 99, "submitted_at": "2026-01-02T00:00:00", "is_anonymous": False}
        ],
    )
    body = asyncio.run(ei_mod.validate_token("already-done"))
    assert body["ok"] is False
    assert body["reason"] == "already_submitted"
    assert body["submitted_at"] == "2026-01-02T00:00:00"

    # Case 4: ready for the user
    monkeypatch.setattr(
        ei_mod.dataflow_crud,
        "list_records",
        lambda *_a, **_k: [
            {
                "id": 99,
                "submitted_at": None,
                "is_anonymous": True,
                "triggered_at": "2026-01-01T00:00:00",
            }
        ],
    )
    body = asyncio.run(ei_mod.validate_token("good"))
    assert body["ok"] is True
    assert body["is_anonymous"] is True
    assert body["triggered_at"] == "2026-01-01T00:00:00"


@pytest.mark.regression
def test_training_record_patch_allows_typo_fix_and_completion_date(monkeypatch):
    """Round-2 (training records editable): PATCH must accept the
    fields exposed by the edit modal (course_name, course_provider,
    course_type, hours, completion_date) and pass them through to the
    underlying update call. employee_id MUST be silently dropped — the
    audit-cleanliness contract is that records are never retargeted."""
    from hr_advisory.api.routers import training as training_mod

    captured: dict = {}

    def fake_verify(_model, _rid, _company_id):
        return {"id": _rid, "company_id": _company_id, "is_archived": False}

    def fake_update(_model, rid, updates):
        captured["update"] = (rid, dict(updates))

    def fake_read(_model, rid):
        return {"id": rid, **captured.get("update", (0, {}))[1]}

    monkeypatch.setattr(
        training_mod, "_verify_record_ownership", fake_verify
    )
    monkeypatch.setattr(
        training_mod.dataflow_crud, "update", fake_update
    )
    monkeypatch.setattr(training_mod.dataflow_crud, "read", fake_read)
    monkeypatch.setattr(
        training_mod, "get_current_company_id", lambda _u: 1
    )

    class FakeRequest:
        async def json(self):
            return {
                "course_name": "Singapore Employment Act 101",
                "course_provider": "Internal HR — fixed typo",
                "hours": 2.5,
                "completion_date": "2026-05-06",
                # Should be dropped:
                "employee_id": 999,
                "id": 123,
                "company_id": 999,
            }

    import asyncio

    body = asyncio.run(
        training_mod.update_training_record(
            record_id=42, request=FakeRequest(), current_user={"sub": "1"}
        )
    )

    rid, updates = captured["update"]
    assert rid == 42
    assert "employee_id" not in updates, (
        "employee_id MUST NOT be patched — records are not retargeted"
    )
    assert updates["course_name"] == "Singapore Employment Act 101"
    assert updates["course_provider"] == "Internal HR — fixed typo"
    assert updates["hours"] == 2.5
    assert updates["completion_date"] == "2026-05-06"
    assert "updated_at" in updates
    assert "record" in body


@pytest.mark.regression
def test_appraisals_my_resolves_employee_names(monkeypatch):
    """Round-3 polish: GET /appraisals/my MUST return employee_name on
    every record (resolved via Employee.user_id → User.name) so the
    frontend never has to fall back to "Employee #N"."""
    from hr_advisory.api.routers import appraisals as ap_mod
    import asyncio

    rows = [
        {"id": 1, "employee_id": 4, "status": "draft"},
        {"id": 2, "employee_id": 5, "status": "submitted"},
        {"id": 3, "employee_id": 6, "status": "draft"},
    ]
    employees = [
        {"id": 4, "user_id": 14, "company_id": 1},
        {"id": 5, "user_id": 15, "company_id": 1},
        {"id": 6, "user_id": 16, "company_id": 1},
    ]
    users = [
        {"id": 14, "name": "Alice Tan", "company_id": 1},
        {"id": 15, "name": "Bob Lee", "company_id": 1},
        {"id": 16, "name": "Cher Lim", "company_id": 1},
    ]

    def fake_list(model, _filter, **_kw):
        return {
            "Appraisal": rows,
            "Employee": employees,
            "User": users,
        }.get(model, [])

    monkeypatch.setattr(ap_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(ap_mod, "get_current_company_id", lambda _u: 1)

    body = asyncio.run(
        ap_mod.list_my_appraisals(
            period_id=None,
            current_user={"sub": "1", "role": "owner"},
        )
    )

    names = {a["employee_name"] for a in body["appraisals"]}
    assert names == {"Alice Tan", "Bob Lee", "Cher Lim"}, names
    # No record may be missing the field, even when names cannot be resolved
    assert all("employee_name" in a for a in body["appraisals"])


@pytest.mark.regression
def test_appraisal_period_launch_uses_in_progress_status(monkeypatch):
    """Round-3 polish: launch MUST set period.status = "in_progress"
    (matches seed data + UI badge label). Previously set "active",
    which the badge styles as green/Active and confused HR admins."""
    from hr_advisory.api.routers import appraisals as ap_mod
    import asyncio

    captured: dict = {}

    def fake_read(model, rid):
        return {
            "id": rid,
            "company_id": 1,
            "template_id": 7,
            "status": "draft",
        }

    def fake_list(model, _filter, **_kw):
        if model == "Employee":
            return [{"id": 4, "company_id": 1, "is_active": True}]
        return []

    def fake_create(_model, payload):
        return {"id": 99, **payload}

    def fake_update(model, rid, updates):
        captured.setdefault("updates", []).append((model, rid, dict(updates)))

    monkeypatch.setattr(ap_mod.dataflow_crud, "read", fake_read)
    monkeypatch.setattr(ap_mod.dataflow_crud, "list_records", fake_list)
    monkeypatch.setattr(ap_mod.dataflow_crud, "create", fake_create)
    monkeypatch.setattr(ap_mod.dataflow_crud, "update", fake_update)
    monkeypatch.setattr(ap_mod, "get_current_company_id", lambda _u: 1)
    monkeypatch.setattr(ap_mod, "check_rate_limit", lambda *_a, **_k: None)

    asyncio.run(
        ap_mod.launch_period(
            period_id=42,
            current_user={"sub": "1", "role": "owner"},
        )
    )

    period_updates = [u for u in captured["updates"] if u[0] == "AppraisalPeriod"]
    assert period_updates, "launch must update AppraisalPeriod status"
    _, _, fields = period_updates[-1]
    assert fields["status"] == "in_progress", (
        f"launch must set status=in_progress, got {fields['status']}"
    )


@pytest.mark.regression
def test_appraisal_period_close_marks_completed(monkeypatch):
    """Round-3 polish: HR admins must be able to close an in_progress
    review cycle. POST /periods/{id}/close MUST move status to
    "completed" and reject closing a non-running period."""
    from hr_advisory.api.routers import appraisals as ap_mod
    from fastapi import HTTPException
    import asyncio

    captured: dict = {}

    def fake_update(model, rid, updates):
        captured["update"] = (model, rid, dict(updates))
        return {"id": rid, **updates}

    monkeypatch.setattr(ap_mod, "get_current_company_id", lambda _u: 1)
    monkeypatch.setattr(ap_mod, "check_rate_limit", lambda *_a, **_k: None)
    monkeypatch.setattr(ap_mod.dataflow_crud, "update", fake_update)

    # Valid: in_progress → completed
    monkeypatch.setattr(
        ap_mod.dataflow_crud,
        "read",
        lambda _m, _r: {"id": _r, "company_id": 1, "status": "in_progress"},
    )
    asyncio.run(
        ap_mod.close_period(
            period_id=42,
            current_user={"sub": "1", "role": "owner"},
        )
    )
    assert captured["update"] == ("AppraisalPeriod", 42, {"status": "completed"})

    # Invalid: cannot close a draft period
    monkeypatch.setattr(
        ap_mod.dataflow_crud,
        "read",
        lambda _m, _r: {"id": _r, "company_id": 1, "status": "draft"},
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            ap_mod.close_period(
                period_id=42,
                current_user={"sub": "1", "role": "owner"},
            )
        )
    assert exc.value.status_code == 400
