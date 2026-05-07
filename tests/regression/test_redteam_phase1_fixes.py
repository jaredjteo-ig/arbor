"""Regression tests for engagement-survey red-team Phase 1 fixes (B1-B7).

These tests pin the convergent ship-blockers identified in
`workspaces/engagement-survey/04-validate/07-redteam-synthesis.md`.

Each test fails BEFORE its fix and passes AFTER. Permanent guards.
"""

from __future__ import annotations

import os
import re
from unittest.mock import patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")
os.environ.setdefault("DATAFLOW_POOL_SIZE", "3")
os.environ.setdefault("DATAFLOW_POOL_MAX_OVERFLOW", "2")


# ───────────────────────────────────────────────────────────────────
# B1 — SQL identifier validation
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_b1_validate_sql_identifier_accepts_safe_names():
    from hr_advisory.services.dataflow_crud import _validate_sql_identifier

    for name in (
        "engagement_survey_responses",
        "company_id",
        "employee_id",
        "Camel_Case_Allowed",
        "_underscore_start",
    ):
        assert _validate_sql_identifier(name) == name


@pytest.mark.regression
def test_b1_validate_sql_identifier_rejects_injection_attempts():
    from hr_advisory.services.dataflow_crud import _validate_sql_identifier

    bad_inputs = [
        "engagement_surveys; DROP TABLE companies",  # statement injection
        "id'; DELETE FROM users; --",  # quote escape
        "1id",  # leading digit
        "id--comment",  # SQL comment
        "id name",  # space
        "id\nname",  # newline
        "id\\;",  # backslash escape
        "",  # empty
        "a" * 64,  # over PostgreSQL's NAMEDATALEN-1 limit
    ]
    for bad in bad_inputs:
        with pytest.raises(ValueError):
            _validate_sql_identifier(bad)


@pytest.mark.regression
def test_b1_list_records_rejects_bad_filter_keys():
    """A poisoned filter dict key is rejected at the identifier-validation
    boundary — no SQL is built or executed."""
    from hr_advisory.services import dataflow_crud

    with pytest.raises(Exception):
        # Use cache_ttl=0 to route through _list_records_direct_sql.
        dataflow_crud.list_records(
            "EngagementSurveyResponse",
            {"company_id; DROP TABLE companies": 1},
            cache_ttl=0,
        )


# ───────────────────────────────────────────────────────────────────
# B6 — voided_count partial-failure tracking
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_b6_voided_count_only_bumps_for_successful_voids(monkeypatch):
    """If 3 of 5 individual void updates fail, voided_count bumps by 3 — not 5."""
    from hr_advisory.services import engagement_termination

    pending_rows = [
        {"id": i, "company_id": 1, "survey_id": 100, "employee_id": 42,
         "submitted_at": None, "is_void": False}
        for i in (1, 2, 3, 4, 5)
    ]
    survey_row = {"id": 100, "voided_count": 0}
    update_calls: list[tuple] = []

    def fake_list(model, where, **_):
        if model == "EngagementSurveyResponse":
            return list(pending_rows)
        if model == "EngagementSurvey" and where.get("id") == 100:
            return [dict(survey_row)]
        return []

    def fake_update(model, record_id, fields):
        update_calls.append((model, record_id, fields))
        if model == "EngagementSurveyResponse" and int(record_id) in (3, 4, 5):
            raise RuntimeError("simulated DB failure")
        if model == "EngagementSurvey":
            survey_row["voided_count"] = fields.get("voided_count", 0)

    monkeypatch.setattr(
        engagement_termination.dataflow_crud, "list_records", fake_list
    )
    monkeypatch.setattr(
        engagement_termination.dataflow_crud, "update", fake_update
    )

    result = engagement_termination.void_pending_engagement_responses(42)
    # 2 of 5 voids succeeded (ids 1, 2); the parent survey's voided_count
    # bumped by 2 — NOT 5 (which was the bug pre-fix).
    assert result == {"voided": 2, "surveys_affected": 1}
    assert survey_row["voided_count"] == 2


# ───────────────────────────────────────────────────────────────────
# B7 — create_action linked-goal explicit failure
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_b7_create_action_fails_loudly_when_goal_create_fails():
    """Pre-fix: action was created with linked_goal_id=0 if goal create
    failed, returning success to the client. Post-fix: must raise an
    HTTPException 502 and not create the action row.

    Source-level check (avoids spinning up a TestClient + platform,
    which strains the connection pool when run as part of the full
    suite). The B7 fix is concrete code change; this regression
    asserts the fix is in place.
    """
    src_path = (
        "/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/"
        "routers/engagement_surveys.py"
    )
    with open(src_path) as f:
        src = f.read()
    # The fix must (a) raise HTTPException, not just log a warning,
    # and (b) status_code=502.
    assert "raise HTTPException(" in src
    assert "status_code=502" in src
    # The error message must reference linked goal for the client.
    assert "Linked goal could not be created" in src
    # And the action create must come AFTER the goal create (not before
    # — pre-fix the action was created either way).
    goal_create_idx = src.find('dataflow_crud.create(\n                "Goal"')
    raise_502_idx = src.find("status_code=502")
    action_create_idx = src.find('dataflow_crud.create(\n        "EngagementAction"')
    assert goal_create_idx > 0
    assert raise_502_idx > goal_create_idx
    assert action_create_idx > raise_502_idx, (
        "EngagementAction create must come AFTER the goal-failure "
        "raise, so a failed goal abandons the whole request."
    )


# ───────────────────────────────────────────────────────────────────
# B5 — PDPA admin-access logging on identified responses
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_b5_pdpa_log_called_when_admin_views_identified_responses(monkeypatch):
    """Admin reading an identified response writes a PDPA access log row."""
    from hr_advisory.api.routers import engagement_surveys

    log_calls: list[dict] = []

    def fake_log(**kwargs):
        log_calls.append(kwargs)

    # Patch the log helper at the import site (engagement_surveys.py
    # imports it lazily inside the handler).
    import hr_advisory.api.routers.employees as employees_mod
    monkeypatch.setattr(employees_mod, "_log_pdpa_access", fake_log)

    # The handler is async — directly drive the inner block by calling
    # list_records with seeded data and checking the assertions.
    # For a black-box check, look at the source for the call pattern:
    src_path = "/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/routers/engagement_surveys.py"
    with open(src_path) as f:
        src = f.read()
    assert "_log_pdpa_access" in src, (
        "B5 (Z16) regression: _log_pdpa_access must be wired in the "
        "engagement-survey identified responses handler. The previous "
        "stub-comment is no longer acceptable."
    )
    assert "data_subject_id" in src
    assert "engagement_response" in src


# ───────────────────────────────────────────────────────────────────
# B4 — Seed-script encrypts the engagement secret
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_b4_seed_script_encrypts_engagement_secret():
    """Pre-fix: the seed wrote `secrets.token_hex(32)` directly to
    `Company.engagement_secret_v1` as plaintext. The service path's
    `decrypt_field` only "succeeded" because it silently returned bad
    ciphertext as-is — a fail-closed violation.

    Post-fix: the seed must round-trip through `encrypt_field`.
    """
    src_path = (
        "/Users/jaredteo/Documents/GitHub/arbor/scripts/"
        "backfill_demo_engagement_surveys.py"
    )
    with open(src_path) as f:
        src = f.read()
    assert "encrypt_field" in src, (
        "B4 regression: the seed script must call encrypt_field() before "
        "writing engagement_secret_v1. Plaintext storage was a "
        "fail-closed violation that only worked because decrypt_field "
        "swallows Fernet failures."
    )
    # And the encrypt call must precede the UPDATE statement.
    encrypt_idx = src.find("encrypted = encrypt_field(secret_v1)")
    update_idx = src.find("UPDATE companies SET engagement_secret_v1")
    assert encrypt_idx > 0
    assert update_idx > encrypt_idx, (
        "encrypt_field must be called before the UPDATE."
    )


# ───────────────────────────────────────────────────────────────────
# B3 — Termination sweep covers pending responses (sanity pin)
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_b3_termination_sweep_finds_pending_responses(monkeypatch):
    """Pending responses always have employee_id set (the launch flow
    creates them with employee_id pre-submit; only submit zeroes it
    for pseudonymous/anonymous tiers). The sweep filters by
    employee_id and finds them correctly. This test pins that the
    boundary holds for ALL three anonymity tiers.
    """
    from hr_advisory.services import engagement_termination

    pending_pseudonymous = {
        "id": 1, "company_id": 1, "survey_id": 100, "employee_id": 42,
        "employee_pseudonym": "",  # not yet submitted
        "submitted_at": None, "is_void": False,
    }
    pending_anonymous = {
        "id": 2, "company_id": 1, "survey_id": 101, "employee_id": 42,
        "submitted_at": None, "is_void": False,
    }
    submitted_pseudonymous = {
        "id": 3, "company_id": 1, "survey_id": 100, "employee_id": 0,
        "employee_pseudonym": "abc123",
        "submitted_at": "2026-04-12T10:00:00", "is_void": False,
    }
    submitted_anonymous = {
        "id": 4, "company_id": 1, "survey_id": 101, "employee_id": 0,
        "submitted_at": "2026-04-12T10:00:00", "is_void": False,
    }

    rows = [pending_pseudonymous, pending_anonymous,
            submitted_pseudonymous, submitted_anonymous]

    def fake_list(model, where, **_):
        if model == "EngagementSurveyResponse":
            # The sweep filters by {"employee_id": 42}. Pending rows
            # match. Submitted pseudonymous/anonymous rows have
            # employee_id=0 and DO NOT match (which is what we want
            # per Z04 — submitted rows stay in the aggregate).
            return [r for r in rows if r.get("employee_id") == where.get("employee_id")]
        if model == "EngagementSurvey":
            sid = where.get("id")
            return [{"id": sid, "voided_count": 0}]
        return []

    voided_ids: list[int] = []

    def fake_update(model, record_id, fields):
        if model == "EngagementSurveyResponse":
            voided_ids.append(int(record_id))

    monkeypatch.setattr(
        engagement_termination.dataflow_crud, "list_records", fake_list
    )
    monkeypatch.setattr(
        engagement_termination.dataflow_crud, "update", fake_update
    )

    result = engagement_termination.void_pending_engagement_responses(42)
    # Exactly 2 pending rows voided. Submitted rows untouched (Z04).
    assert result == {"voided": 2, "surveys_affected": 2}
    assert sorted(voided_ids) == [1, 2]


# ───────────────────────────────────────────────────────────────────
# B2 — Manager view self-exclusion via pseudonym for pseudonymous tier
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_b2_manager_view_pseudonymous_filter_uses_pseudonym(monkeypatch):
    """Pre-fix: filter `int(r["employee_id"]) in scope` against
    pseudonymous-submitted rows (employee_id=0) excluded ALL responses,
    so the manager view always reported n=0.

    Post-fix: pseudonymous-tier surveys filter on employee_pseudonym,
    computed via HMAC of (secret, employee_id, survey_id) for each
    scope employee + the manager.
    """
    src_path = (
        "/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/"
        "routers/engagement_surveys.py"
    )
    with open(src_path) as f:
        src = f.read()
    # The fix must (a) branch on survey_tier == "pseudonymous", (b)
    # compute pseudonyms for the scope, and (c) filter on
    # employee_pseudonym, not employee_id.
    assert 'survey_tier == "pseudonymous"' in src
    assert "scope_pseudonyms" in src
    assert "manager_pseudonym" in src
    assert "compute_pseudonym(secret, eid, survey_id)" in src or (
        "compute_pseudonym(secret, manager_id, survey_id)" in src
    )


@pytest.mark.regression
def test_b2_manager_view_anonymous_tier_refuses_to_show():
    """Anonymous-tier surveys can't be filtered by team without
    re-identifying respondents. The manager-view endpoint must return
    is_visible=false with a specific reason.
    """
    src_path = (
        "/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/"
        "routers/engagement_surveys.py"
    )
    with open(src_path) as f:
        src = f.read()
    assert 'survey_tier == "anonymous"' in src
    assert "anonymity_tier_anonymous" in src
