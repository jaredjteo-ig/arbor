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
