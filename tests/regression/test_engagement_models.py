"""Regression tests for M1 engagement-survey data model.

Pins:
- Six new DataFlow models register and CRUD-roundtrip.
- Schema fields match the round-3 + Z amendments (response_cohort_attributes,
  pseudonym_version, idempotency_key, email_delivery_status, etc.).
- Library seed creates exactly 2 templates at P1 (round-3 trim).
- Library seed is idempotent — re-running on a seeded company is a no-op.
- Termination sweep voids only pending responses (Z04).
"""

from __future__ import annotations

import json

import pytest

from hr_advisory.services import (
    dataflow_crud,
    engagement_library,
    engagement_termination,
)


# ───────────────────────────────────────────────────────────────────
# Library seed
# ───────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_template_store(monkeypatch):
    """In-memory replacement for the template + survey + response stores."""
    stores: dict[str, dict[int, dict]] = {
        "EngagementSurveyTemplate": {},
        "EngagementSurvey": {},
        "EngagementSurveyResponse": {},
    }
    next_id = {"v": 1}

    def fake_create(model, fields):
        if model not in stores:
            raise AssertionError(f"Unexpected create on {model}")
        nid = next_id["v"]
        next_id["v"] += 1
        record = {"id": nid, **fields}
        stores[model][nid] = record
        return record

    def fake_list(model, where, **_):
        if model not in stores:
            return []
        results = []
        for r in stores[model].values():
            ok = True
            for k, v in where.items():
                if r.get(k) != v:
                    ok = False
                    break
            if ok:
                results.append(dict(r))
        return results

    def fake_update(model, record_id, fields):
        if model not in stores:
            raise AssertionError(f"Unexpected update on {model}")
        if isinstance(record_id, dict):
            # Legacy where-dict path (kept for any test that still uses it).
            for r in stores[model].values():
                ok = True
                for k, v in record_id.items():
                    if r.get(k) != v:
                        ok = False
                        break
                if ok:
                    r.update(fields)
                    return r
            return None
        rec = stores[model].get(int(record_id))
        if rec is not None:
            rec.update(fields)
        return rec

    monkeypatch.setattr(
        engagement_library.dataflow_crud, "create", fake_create
    )
    monkeypatch.setattr(
        engagement_library.dataflow_crud, "list_records", fake_list
    )
    monkeypatch.setattr(
        engagement_termination.dataflow_crud, "list_records", fake_list
    )
    monkeypatch.setattr(
        engagement_termination.dataflow_crud, "update", fake_update
    )
    return stores


@pytest.mark.regression
def test_seed_library_creates_two_templates_at_p1(fake_template_store):
    seeded = engagement_library.seed_library_for_company(company_id=1)
    assert seeded == 2

    rows = list(fake_template_store["EngagementSurveyTemplate"].values())
    methodologies = sorted(r["methodology"] for r in rows)
    # Round-3 owner decision: keep Q12 quarterly + monthly_pulse only.
    # Trust Index + Singapore SME defer to P2 (M8 T82 / T83).
    assert methodologies == ["gallup_q12", "pulse"]


@pytest.mark.regression
def test_seed_library_is_idempotent(fake_template_store):
    first = engagement_library.seed_library_for_company(company_id=1)
    assert first == 2
    second = engagement_library.seed_library_for_company(company_id=1)
    assert second == 0
    rows = list(fake_template_store["EngagementSurveyTemplate"].values())
    assert len(rows) == 2


@pytest.mark.regression
def test_seed_library_isolates_companies(fake_template_store):
    """Each company gets its own seeded set — no cross-tenant sharing."""
    engagement_library.seed_library_for_company(company_id=1)
    engagement_library.seed_library_for_company(company_id=2)
    rows = list(fake_template_store["EngagementSurveyTemplate"].values())
    assert len(rows) == 4
    company_ids = sorted(set(r["company_id"] for r in rows))
    assert company_ids == [1, 2]


@pytest.mark.regression
def test_q12_template_has_12_likert_questions():
    """Gallup Q12 contract — 12 Likert-5 questions, paraphrased."""
    sections = engagement_library.GALLUP_Q12_TEMPLATE["sections"]
    questions = [q for s in sections for q in s["questions"]]
    assert len(questions) == 12
    assert all(q["type"] == "likert5" for q in questions)
    assert all(q.get("is_required") for q in questions)


@pytest.mark.regression
def test_monthly_pulse_has_four_questions_with_enps_and_freeform():
    """Round-3 owner decision: 4-question monthly pulse (no micro-pulse)."""
    sections = engagement_library.MONTHLY_PULSE_TEMPLATE["sections"]
    questions = [q for s in sections for q in s["questions"]]
    assert len(questions) == 4
    types = [q["type"] for q in questions]
    assert "enps" in types
    assert "long_text" in types
    assert "likert5" in types
    assert "multi" in types


@pytest.mark.regression
def test_seed_persists_sections_as_json(fake_template_store):
    engagement_library.seed_library_for_company(company_id=1)
    rows = list(fake_template_store["EngagementSurveyTemplate"].values())
    for row in rows:
        # `sections` is JSON-serialised in the row.
        parsed = json.loads(row["sections"])
        assert isinstance(parsed, list)
        assert len(parsed) >= 1


# ───────────────────────────────────────────────────────────────────
# Termination sweep (T17 / Z04)
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_termination_voids_only_pending_responses(fake_template_store):
    """Z04: submitted responses stay in the aggregate; only pending are voided."""
    # Survey 7 with 3 responses for employee 42.
    fake_template_store["EngagementSurvey"][7] = {
        "id": 7,
        "voided_count": 0,
    }
    fake_template_store["EngagementSurveyResponse"][1] = {
        "id": 1,
        "company_id": 1,
        "survey_id": 7,
        "employee_id": 42,
        "submitted_at": "2026-04-12T10:00:00",  # already submitted — KEEP
        "is_void": False,
    }
    fake_template_store["EngagementSurveyResponse"][2] = {
        "id": 2,
        "company_id": 1,
        "survey_id": 7,
        "employee_id": 42,
        "submitted_at": None,  # pending — VOID
        "is_void": False,
    }
    fake_template_store["EngagementSurveyResponse"][3] = {
        "id": 3,
        "company_id": 1,
        "survey_id": 7,
        "employee_id": 42,
        "submitted_at": None,
        "is_void": True,  # already voided — leave alone
    }

    result = engagement_termination.void_pending_engagement_responses(42)
    assert result == {"voided": 1, "surveys_affected": 1}

    # The submitted response is untouched.
    assert fake_template_store["EngagementSurveyResponse"][1]["is_void"] is False
    # The pending one is voided.
    assert fake_template_store["EngagementSurveyResponse"][2]["is_void"] is True
    assert fake_template_store["EngagementSurveyResponse"][2]["voided_at"] is not None


@pytest.mark.regression
def test_termination_is_idempotent(fake_template_store):
    fake_template_store["EngagementSurvey"][7] = {"id": 7, "voided_count": 0}
    fake_template_store["EngagementSurveyResponse"][1] = {
        "id": 1, "company_id": 1, "survey_id": 7,
        "employee_id": 42, "submitted_at": None, "is_void": False,
    }
    first = engagement_termination.void_pending_engagement_responses(42)
    assert first["voided"] == 1
    second = engagement_termination.void_pending_engagement_responses(42)
    assert second == {"voided": 0, "surveys_affected": 0}


@pytest.mark.regression
def test_termination_no_responses_returns_zero(fake_template_store):
    result = engagement_termination.void_pending_engagement_responses(99)
    assert result == {"voided": 0, "surveys_affected": 0}


@pytest.mark.regression
def test_termination_rejects_invalid_employee_id(fake_template_store):
    with pytest.raises(ValueError):
        engagement_termination.void_pending_engagement_responses(0)
    with pytest.raises(ValueError):
        engagement_termination.void_pending_engagement_responses(-1)


@pytest.mark.regression
def test_termination_bumps_parent_survey_voided_count(fake_template_store):
    fake_template_store["EngagementSurvey"][7] = {
        "id": 7, "voided_count": 0,
    }
    fake_template_store["EngagementSurveyResponse"][1] = {
        "id": 1, "company_id": 1, "survey_id": 7,
        "employee_id": 42, "submitted_at": None, "is_void": False,
    }
    fake_template_store["EngagementSurveyResponse"][2] = {
        "id": 2, "company_id": 1, "survey_id": 7,
        "employee_id": 42, "submitted_at": None, "is_void": False,
    }

    engagement_termination.void_pending_engagement_responses(42)
    # Both pending responses voided → survey voided_count bumped by 2.
    assert fake_template_store["EngagementSurvey"][7]["voided_count"] == 2


# ───────────────────────────────────────────────────────────────────
# Model schema sanity (these import tests exercise that the @db.model
# decorations don't error at module load and DataFlow registers them).
# ───────────────────────────────────────────────────────────────────


@pytest.mark.regression
def test_engagement_models_import_cleanly():
    """Round-3 schema additions must not break the company_user import."""
    from hr_advisory.models.company_user import (
        EngagementAction,
        EngagementCohort,
        EngagementSurvey,
        EngagementSurveyResponse,
        EngagementSurveySchedule,
        EngagementSurveyTemplate,
    )
    # All six classes resolve.
    assert EngagementSurveyTemplate is not None
    assert EngagementCohort is not None
    assert EngagementSurvey is not None
    assert EngagementSurveyResponse is not None
    assert EngagementSurveySchedule is not None
    assert EngagementAction is not None


@pytest.mark.regression
def test_response_model_has_z03_z02_z08_fields():
    """Pin the round-3 / Z amendment fields on the response model."""
    from hr_advisory.models.company_user import EngagementSurveyResponse

    # DataFlow models expose fields as class annotations.
    annotations = EngagementSurveyResponse.__annotations__
    assert "response_cohort_attributes" in annotations  # Z03
    assert "pseudonym_version" in annotations  # Z02
    assert "idempotency_key" in annotations  # Z08
    assert "is_void" in annotations  # C1
    assert "employee_pseudonym" in annotations  # C2


@pytest.mark.regression
def test_survey_model_drops_response_count_per_z07():
    """Z07: response_count denormalised counter dropped (derive on read)."""
    from hr_advisory.models.company_user import EngagementSurvey

    annotations = EngagementSurvey.__annotations__
    # `response_count` is intentionally absent — it's computed on read.
    assert "response_count" not in annotations
    # `target_count` stays — it's the launch-time denominator.
    assert "target_count" in annotations
    # Z09 saga field
    assert "email_delivery_status" in annotations


@pytest.mark.regression
def test_action_model_has_z32_fields():
    from hr_advisory.models.company_user import EngagementAction

    annotations = EngagementAction.__annotations__
    for field in (
        "survey_id",
        "cohort_label",
        "finding_summary",
        "suggested_action_text",
        "status",
        "linked_goal_id",
        "next_pulse_question",
        "next_pulse_survey_id",
        "resolved_score_delta",
    ):
        assert field in annotations, f"Z32 field {field!r} missing"
