"""Regression tests for engagement-survey red-team Phase 2 fixes (D1-D4).

D1 — Manager view themes-only at n=3-4 (SG-SME fit).
D2 — Goal title input on accept modal (frontend; source check).
D3 — HR viewed_at + 3-state loop-closing copy.
D4 — Theme-based action matching instead of substring.

Each test fails BEFORE its fix and passes AFTER.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")
os.environ.setdefault("DATAFLOW_POOL_SIZE", "3")
os.environ.setdefault("DATAFLOW_POOL_MAX_OVERFLOW", "2")


# ───────────────────────────────────────────────────────────────────
# D1 — Manager view themes-only at n=3-4
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_d1_manager_view_threshold_constants():
    """`THEMES_ONLY_THRESHOLD` (3) < `MIN_COHORT_SIZE` (5)."""
    from hr_advisory.api.routers.engagement_surveys import (
        MIN_COHORT_SIZE,
        THEMES_ONLY_THRESHOLD,
    )
    assert THEMES_ONLY_THRESHOLD == 3
    assert MIN_COHORT_SIZE == 5
    assert THEMES_ONLY_THRESHOLD < MIN_COHORT_SIZE


@pytest.mark.regression
def test_d1_manager_view_three_band_response_structure():
    """Source-level pin: handler returns three bands.

    - n < THEMES_ONLY_THRESHOLD: is_visible=False (suppress)
    - n in [3, 5): is_visible=True, is_limited=True, themes only
    - n >= 5: is_visible=True, is_limited=False, full aggregate
    """
    src_path = (
        "/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/"
        "routers/engagement_surveys.py"
    )
    with open(src_path) as f:
        src = f.read()
    assert "THEMES_ONLY_THRESHOLD" in src
    assert '"is_limited": True' in src
    assert '"is_limited": False' in src
    # The friendly limited-preview message must be present.
    assert "Limited preview" in src
    # And the message must reference themes-only protection.
    assert "themes only" in src.lower() or "themes-only" in src.lower()


# ───────────────────────────────────────────────────────────────────
# D2 — Goal title input on accept modal (frontend source check)
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_d2_goal_title_input_in_accept_modal():
    """Pre-fix: goal_title was auto-derived from action text:
        `Engagement: ${editedText.slice(0, 80)}` — verbose + ugly.

    Post-fix: a `goalTitle` state + input field, defaulted to a concise
    `<Cohort>: <theme> action` format that HR can edit before submit.
    """
    src_path = (
        "/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/app/"
        "(dashboard)/engagement/surveys/[id]/page.tsx"
    )
    with open(src_path) as f:
        src = f.read()
    # D2 fix: explicit goalTitle state.
    assert "goalTitle" in src
    assert "setGoalTitle" in src
    # D2 fix: defaultGoalTitle uses cohort + theme, not full action.
    assert "defaultGoalTitle" in src
    # D2 fix: input rendered when createGoal is checked.
    assert "Goal title (shown in /goals)" in src or (
        "Goal title" in src and 'value={goalTitle}' in src
    )


# ───────────────────────────────────────────────────────────────────
# D3 — HR viewed_at + 3-state loop-closing
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_d3_engagement_survey_has_last_viewed_field():
    from hr_advisory.models.company_user import EngagementSurvey
    annotations = EngagementSurvey.__annotations__
    assert "last_viewed_by_admin_at" in annotations


@pytest.mark.regression
def test_d3_loop_closing_payload_returns_three_states(monkeypatch):
    """compute_loop_closing_payload returns one of three statuses based
    on (action_taken, last_viewed_by_admin_at) state."""
    from hr_advisory.services import engagement_actions

    closed_at = "2026-04-01T10:00:00"
    common_survey = {
        "id": 100, "company_id": 1, "is_archived": False,
        "closed_at": closed_at,
    }
    response_with_growth = {
        "id": 1000, "company_id": 1, "survey_id": 100,
        "submitted_at": "2026-04-01T09:00:00", "is_void": False,
        "themes": json.dumps(["growth"]),
    }

    def make_fake_list(survey_override, actions_override):
        def fake_list(model, where, **_):
            if model == "EngagementSurvey":
                return [survey_override]
            if model == "EngagementSurveyResponse":
                return [response_with_growth]
            if model == "EngagementAction":
                return actions_override
            return []
        return fake_list

    def fake_read(model, rid):
        if model == "Goal":
            return {"id": rid, "title": "Q2 L&D pilot"}
        return None

    monkeypatch.setattr(
        engagement_actions.dataflow_crud, "read", fake_read
    )

    # State 1: action_taken — accepted action with growth theme exists.
    monkeypatch.setattr(
        engagement_actions.dataflow_crud,
        "list_records",
        make_fake_list(
            survey_override=dict(common_survey, last_viewed_by_admin_at=None),
            actions_override=[{
                "id": 50, "company_id": 1, "status": "accepted",
                "theme": "growth", "linked_goal_id": 99,
                "suggested_action_text": "Run skip-level on growth",
                "next_pulse_question": "How clear is your career path?",
                "created_at": "2026-04-02T00:00:00",
            }],
        ),
    )
    payload = engagement_actions.compute_loop_closing_payload(1)
    assert payload is not None
    assert payload["status"] == "action_taken"
    assert payload["action_taken"]["headline"] == "Run skip-level on growth"

    # State 2: under_review — admin viewed but no accepted action.
    monkeypatch.setattr(
        engagement_actions.dataflow_crud,
        "list_records",
        make_fake_list(
            survey_override=dict(
                common_survey, last_viewed_by_admin_at="2026-04-03T00:00:00"
            ),
            actions_override=[],
        ),
    )
    payload = engagement_actions.compute_loop_closing_payload(1)
    assert payload["status"] == "under_review"
    assert payload["action_taken"] is None

    # State 3: notified — no admin view, no action.
    monkeypatch.setattr(
        engagement_actions.dataflow_crud,
        "list_records",
        make_fake_list(
            survey_override=dict(common_survey, last_viewed_by_admin_at=None),
            actions_override=[],
        ),
    )
    payload = engagement_actions.compute_loop_closing_payload(1)
    assert payload["status"] == "notified"
    assert payload["action_taken"] is None


@pytest.mark.regression
def test_d3_get_survey_handler_sets_last_viewed():
    """Source pin: GET /surveys/{id} handler updates last_viewed_by_admin_at
    on closed surveys."""
    src_path = (
        "/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/"
        "routers/engagement_surveys.py"
    )
    with open(src_path) as f:
        src = f.read()
    assert "last_viewed_by_admin_at" in src
    # The set must happen inside get_survey, gated on closed_at.
    get_survey_idx = src.find("async def get_survey(")
    list_responses_idx = src.find("async def list_responses(")
    assert get_survey_idx > 0
    assert list_responses_idx > get_survey_idx
    handler_block = src[get_survey_idx:list_responses_idx]
    assert "last_viewed_by_admin_at" in handler_block
    assert 'survey.get("closed_at")' in handler_block


# ───────────────────────────────────────────────────────────────────
# D4 — Theme-based action matching (exact, not substring)
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_d4_engagement_action_has_theme_field():
    from hr_advisory.models.company_user import EngagementAction
    annotations = EngagementAction.__annotations__
    assert "theme" in annotations


@pytest.mark.regression
def test_d4_loop_closing_uses_exact_theme_match(monkeypatch):
    """Pre-fix: substring-search of finding_summary OR suggested_action_text
    matched any theme appearing in those strings — false positives + brittle.

    Post-fix: exact match on action.theme. Falls back to substring only
    for legacy actions that have no theme set (theme=="").
    """
    from hr_advisory.services import engagement_actions

    survey = {
        "id": 100, "company_id": 1, "is_archived": False,
        "closed_at": "2026-04-01T10:00:00",
        "last_viewed_by_admin_at": None,
    }
    response_with_growth = {
        "id": 1000, "company_id": 1, "survey_id": 100,
        "submitted_at": "2026-04-01T09:00:00", "is_void": False,
        "themes": json.dumps(["growth"]),
    }

    # Create three accepted actions:
    # - One with theme="manager" (different theme, must not match)
    # - One with theme="growth" (exact match — should be chosen)
    # - One with theme="" but finding_summary mentions growth (legacy
    #   fallback — should NOT match while exact-matches exist)
    actions = [
        {
            "id": 1, "company_id": 1, "status": "accepted",
            "theme": "manager", "linked_goal_id": 0,
            "suggested_action_text": "1:1 training (mentions growth)",
            "next_pulse_question": "", "finding_summary": "manager skill",
            "created_at": "2026-04-02T08:00:00",
        },
        {
            "id": 2, "company_id": 1, "status": "accepted",
            "theme": "growth", "linked_goal_id": 0,
            "suggested_action_text": "L&D pilot",
            "next_pulse_question": "How clear is your career?",
            "finding_summary": "growth signals",
            "created_at": "2026-04-02T09:00:00",
        },
        {
            "id": 3, "company_id": 1, "status": "accepted",
            "theme": "",  # legacy
            "suggested_action_text": "growth chats",
            "next_pulse_question": "", "finding_summary": "growth ad-hoc",
            "linked_goal_id": 0,
            "created_at": "2026-04-02T10:00:00",
        },
    ]

    def fake_list(model, where, **_):
        if model == "EngagementSurvey":
            return [survey]
        if model == "EngagementSurveyResponse":
            return [response_with_growth]
        if model == "EngagementAction":
            return actions
        return []

    monkeypatch.setattr(
        engagement_actions.dataflow_crud, "list_records", fake_list
    )
    monkeypatch.setattr(
        engagement_actions.dataflow_crud, "read", lambda m, i: None
    )

    payload = engagement_actions.compute_loop_closing_payload(1)
    assert payload is not None
    # Action #2 is the exact theme match — must be chosen even though
    # actions #1 and #3 also contain "growth" as a substring.
    assert payload["action_taken"] is not None
    assert payload["action_taken"]["headline"] == "L&D pilot"


@pytest.mark.regression
def test_d4_loop_closing_legacy_fallback_when_no_exact_match(monkeypatch):
    """If NO action has the explicit theme field set, fall back to
    substring scan over finding_summary / suggested_action_text — but
    ONLY for actions whose theme field is empty (legacy)."""
    from hr_advisory.services import engagement_actions

    survey = {
        "id": 100, "company_id": 1, "is_archived": False,
        "closed_at": "2026-04-01T10:00:00",
        "last_viewed_by_admin_at": None,
    }
    response_with_growth = {
        "id": 1000, "company_id": 1, "survey_id": 100,
        "submitted_at": "2026-04-01T09:00:00", "is_void": False,
        "themes": json.dumps(["growth"]),
    }
    legacy_action = {
        "id": 9, "company_id": 1, "status": "accepted",
        "theme": "",
        "suggested_action_text": "L&D for growth ICs",
        "next_pulse_question": "", "finding_summary": "",
        "linked_goal_id": 0,
        "created_at": "2026-04-02T00:00:00",
    }

    def fake_list(model, where, **_):
        if model == "EngagementSurvey":
            return [survey]
        if model == "EngagementSurveyResponse":
            return [response_with_growth]
        if model == "EngagementAction":
            return [legacy_action]
        return []

    monkeypatch.setattr(
        engagement_actions.dataflow_crud, "list_records", fake_list
    )
    monkeypatch.setattr(
        engagement_actions.dataflow_crud, "read", lambda m, i: None
    )

    payload = engagement_actions.compute_loop_closing_payload(1)
    assert payload is not None
    assert payload["action_taken"] is not None
    assert payload["action_taken"]["headline"] == "L&D for growth ICs"
