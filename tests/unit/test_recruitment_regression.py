"""Regression tests for recently added recruitment + cross-cutting features.

Covers:
    T-RX08  composite index on Candidate
    T-RX09  pagination on list endpoints
    T-RX10  stage transition validation
    T-RX11  job closure cascade
    T-R001  job listing field rename (title / status)
    T-R020  POST /feedback/run-overdue-reminder-sweep
    T-R022  auto-trigger onboarding on hire
    T-R030  PDPA pre-purge sweep
    T-R035  scorecard CRUD + weighted total
    T-R053  TAFEP scan_with_ai fallback
    T-R060  shadow tool registry alignment
    T-R061  recruitment nudges
    B19     ``_validate_text_length`` helper extraction
    B21     headcount sync warning
    T204    auto-seed default onboarding template on company creation
    T205    onboarding overdue nudges

All tests are Tier 1 (unit) and use mocks for dataflow_crud.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from hr_advisory.api.routers.recruitment import router as recruitment_router


# ===========================================================================
# Shared fixtures (matched to tests/unit/test_recruitment_advanced.py style)
# ===========================================================================


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(recruitment_router, prefix="/recruitment")
    return app


def _fake_user(company_id: int = 1, role: str = "owner", sub: int = 10) -> dict:
    return {
        "sub": sub,
        "email": "test@example.com",
        "role": role,
        "company_id": company_id,
    }


@pytest.fixture()
def owner_client():
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="owner")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def employee_client():
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user(role="employee")
    yield TestClient(app)
    app.dependency_overrides.clear()


def _job(job_id=100, company_id=1, status="open", title="Engineer"):
    return {
        "id": job_id,
        "company_id": company_id,
        "title": title,
        "department": "Engineering",
        "status": status,
        "description": "",
        "requirements": "",
    }


def _candidate(
    candidate_id=1,
    company_id=1,
    job_listing_id=100,
    stage="new",
    name="Alice",
    email="alice@example.com",
    created_at: str | None = None,
    pdpa_purge_warned_at=None,
):
    rec = {
        "id": candidate_id,
        "company_id": company_id,
        "job_listing_id": job_listing_id,
        "name": name,
        "email": email,
        "phone": "",
        "stage": stage,
        "source": "direct",
        "notes": "",
        "pdpa_consent": True,
        "pdpa_consent_date": "2026-01-01",
        "pdpa_purge_warned_at": pdpa_purge_warned_at,
    }
    if created_at is not None:
        rec["created_at"] = created_at
    return rec


# Auto-rate-limit reset between tests so check_rate_limit doesn't bleed across.
# Clears both the in-memory log AND the Redis-backed rate-limit keys we know
# this module uses; if Redis is unavailable, the FLUSHDB is a no-op.
@pytest.fixture(autouse=True)
def _reset_rate_limit():
    from hr_advisory.api.middleware import rate_limit as rl

    rl._request_log.clear()
    # Best-effort flush of the Redis-backed rate-limit keys for the keys
    # exercised by these tests. The test suite must be deterministic across
    # repeat runs, even when a Redis instance with persistent rate-limit
    # state is bound to localhost.
    try:
        client = rl._get_redis_client()
        if client is not None:
            for key in client.keys("rate:*"):
                try:
                    client.delete(key)
                except Exception:
                    pass
    except Exception:
        pass

    yield
    rl._request_log.clear()


# ===========================================================================
# T-RX08: Composite index on Candidate
# ===========================================================================


class TestCandidateCompositeIndex:
    """Candidate model must declare the (job_listing_id, email) composite index."""

    def test_candidate_has_composite_job_email_index(self):
        from hr_advisory.models.company_user import Candidate

        indexes = Candidate.__dataflow__["indexes"]
        composite = [idx for idx in indexes if idx["fields"] == ["job_listing_id", "email"]]
        assert composite, (
            "T-RX08: Candidate.__dataflow__['indexes'] must include a "
            "composite index on (job_listing_id, email)"
        )
        # Single index entry, not duplicated
        assert len(composite) == 1
        assert composite[0]["name"] == "idx_candidate_job_email"


# ===========================================================================
# T-RX09: Pagination on list endpoints
# ===========================================================================


class TestPaginationShape:
    """List endpoints must return items/total/page/page_size."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_jobs_returns_pagination_envelope(self, mock_crud, owner_client):
        mock_crud.list_records.return_value = [
            {"id": i, "company_id": 1, "title": f"J{i}", "status": "open"}
            for i in range(15)
        ]
        resp = owner_client.get("/recruitment/jobs?page=2&page_size=5")
        assert resp.status_code == 200
        body = resp.json()
        for key in ("items", "total", "page", "page_size"):
            assert key in body, f"list_jobs missing pagination key '{key}'"
        assert body["total"] == 15
        assert body["page"] == 2
        assert body["page_size"] == 5
        assert len(body["items"]) == 5

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_candidates_returns_pagination_envelope(
        self, mock_crud, owner_client,
    ):
        mock_crud.read.return_value = _job(job_id=100)
        mock_crud.list_records.return_value = [
            _candidate(candidate_id=i, job_listing_id=100) for i in range(7)
        ]
        resp = owner_client.get(
            "/recruitment/jobs/100/candidates?page=1&page_size=3",
        )
        assert resp.status_code == 200
        body = resp.json()
        for key in ("items", "total", "page", "page_size"):
            assert key in body
        assert body["total"] == 7
        assert body["page_size"] == 3
        assert len(body["items"]) == 3

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_search_talent_pool_returns_pagination_envelope(
        self, mock_crud, owner_client,
    ):
        mock_crud.list_records.return_value = [
            _candidate(candidate_id=i) for i in range(11)
        ]
        mock_crud.read.return_value = _job()
        resp = owner_client.get(
            "/recruitment/talent-pool?page=2&page_size=4",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 11
        assert body["page"] == 2
        assert body["page_size"] == 4
        assert len(body["items"]) == 4

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_referrals_returns_pagination_envelope(
        self, mock_crud, owner_client,
    ):
        # Owner -> sees all referrals, no Employee lookup needed.
        mock_crud.list_records.return_value = [
            {
                "id": i,
                "company_id": 1,
                "referrer_employee_id": 50,
                "job_listing_id": 100,
                "candidate_name": f"C{i}",
                "candidate_email": f"c{i}@x.com",
                "status": "pending",
            }
            for i in range(8)
        ]
        mock_crud.read.return_value = _job()
        resp = owner_client.get("/recruitment/referrals?page=1&page_size=3")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 8
        assert body["page_size"] == 3
        assert len(body["items"]) == 3

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_list_overdue_feedback_returns_pagination_envelope(
        self, mock_crud, owner_client,
    ):
        # No interviews -> empty page, but envelope still present.
        mock_crud.list_records.return_value = []
        resp = owner_client.get(
            "/recruitment/feedback/overdue?page=1&page_size=10",
        )
        assert resp.status_code == 200
        body = resp.json()
        for key in ("items", "total", "page", "page_size"):
            assert key in body


# ===========================================================================
# T-RX10: Stage transition validation
# ===========================================================================


class TestStageTransitionValidation:
    """_validate_stage_transition enforces the directed pipeline graph."""

    def test_no_op_transitions_are_allowed(self):
        from hr_advisory.api.routers.recruitment import _validate_stage_transition

        for stage in (
            "new", "screening", "interview", "assessment",
            "offered", "hired", "rejected", "withdrawn",
        ):
            # Should not raise.
            _validate_stage_transition(stage, stage)

    @pytest.mark.parametrize(
        "old,new",
        [
            ("new", "screening"),
            ("new", "rejected"),
            ("new", "withdrawn"),
            ("screening", "interview"),
            ("screening", "rejected"),
            ("interview", "assessment"),
            ("interview", "offered"),
            ("interview", "rejected"),
            ("assessment", "offered"),
            ("offered", "hired"),
            ("offered", "rejected"),
            ("offered", "withdrawn"),
        ],
    )
    def test_valid_edges_pass(self, old, new):
        from hr_advisory.api.routers.recruitment import _validate_stage_transition

        # Should not raise for any documented edge.
        _validate_stage_transition(old, new)

    @pytest.mark.parametrize(
        "old,new",
        [
            # Skipping ahead
            ("new", "hired"),
            ("new", "offered"),
            ("new", "interview"),
            ("screening", "offered"),
            # Reverse moves
            ("interview", "new"),
            ("offered", "screening"),
            # Terminal escapes
            ("hired", "screening"),
            ("hired", "interview"),
            ("rejected", "new"),
            ("withdrawn", "interview"),
        ],
    )
    def test_invalid_edges_return_400(self, old, new):
        from hr_advisory.api.routers.recruitment import _validate_stage_transition

        with pytest.raises(HTTPException) as exc_info:
            _validate_stage_transition(old, new)
        assert exc_info.value.status_code == 400

    def test_unknown_source_stage_does_not_brick_legacy_records(self):
        """Unknown old stages should be permissive (legacy data)."""
        from hr_advisory.api.routers.recruitment import _validate_stage_transition

        _validate_stage_transition("legacy_unknown", "screening")  # no raise


# ===========================================================================
# T-RX11: Job closure cascade
# ===========================================================================


class TestJobClosureCascade:
    """Closing a job moves active candidates -> withdrawn and pending offers -> expired."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_close_job_cascades_active_candidates_and_offers(
        self, mock_crud, owner_client,
    ):
        # The job + 3 candidates in different stages + 1 pending offer.
        job = _job(job_id=100, status="open")
        cand_active = _candidate(
            candidate_id=1, job_listing_id=100, stage="screening",
        )
        cand_interview = _candidate(
            candidate_id=2, job_listing_id=100, stage="interview",
        )
        cand_hired = _candidate(
            candidate_id=3, job_listing_id=100, stage="hired",
        )
        offer_sent = {
            "id": 11,
            "company_id": 1,
            "candidate_id": 1,
            "job_listing_id": 100,
            "status": "sent",
        }

        # mock_crud.read by (model, id) — kept for any per-id lookup paths
        # (e.g. _log_candidate_activity reads Candidate by id).
        candidate_lookup = {1: cand_active, 2: cand_interview, 3: cand_hired}

        def fake_read(model, record_id):
            if model == "JobListing":
                return job
            if model == "Candidate":
                return candidate_lookup.get(record_id, {})
            return {}

        def fake_list(model, filters, **kwargs):
            # _verify_job_ownership uses list_records on JobListing.
            if model == "JobListing":
                return [job]
            if model == "Candidate":
                return [cand_active, cand_interview, cand_hired]
            if model == "Offer":
                return [offer_sent]
            return []

        mock_crud.read.side_effect = fake_read
        mock_crud.list_records.side_effect = fake_list
        mock_crud.update.return_value = {"id": 100, "status": "closed"}

        resp = owner_client.post("/recruitment/jobs/100/close")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["candidates_withdrawn"] == 2, (
            "Only the 2 non-terminal candidates should be auto-withdrawn"
        )
        assert body["offers_expired"] == 1

        # Verify candidate update calls used rejection_reason='job_closed'.
        cand_updates = [
            c for c in mock_crud.update.call_args_list
            if c[0][0] == "Candidate"
        ]
        # We expect 2 candidate withdrawals + (notes append from
        # _log_candidate_activity). Check that at least one update has the
        # right rejection reason / stage.
        withdrawal_updates = [
            c for c in cand_updates
            if c[0][2].get("stage") == "withdrawn"
        ]
        assert len(withdrawal_updates) == 2
        for call in withdrawal_updates:
            payload = call[0][2]
            assert payload["rejection_reason"] == "job_closed"

        # Verify offer was marked expired
        offer_updates = [
            c for c in mock_crud.update.call_args_list
            if c[0][0] == "Offer"
        ]
        assert any(c[0][2].get("status") == "expired" for c in offer_updates)

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_close_already_closed_job_returns_400(self, mock_crud, owner_client):
        """Closing a job that is already closed is rejected with 400."""
        # _verify_job_ownership uses list_records (not read).
        mock_crud.list_records.return_value = [_job(job_id=100, status="closed")]
        resp = owner_client.post("/recruitment/jobs/100/close")
        assert resp.status_code == 400


# ===========================================================================
# T-R001: Seed field rename — JobListing.title (not position_title), status="open"
# ===========================================================================


class TestSeedJobFieldNames:
    """Seeded job listings must use the renamed fields."""

    def test_default_listings_use_title_and_status_open(self):
        from hr_advisory.services.company_seeding import DEFAULT_JOB_LISTINGS

        for listing in DEFAULT_JOB_LISTINGS:
            assert "title" in listing, "T-R001: each seed listing needs 'title'"
            assert "position_title" not in listing, (
                "T-R001: 'position_title' was renamed to 'title'"
            )
            assert listing.get("status") == "open", (
                "T-R001: seeded listings must use status='open' (not is_published)"
            )
            assert "is_published" not in listing


# ===========================================================================
# T-R020: POST /feedback/run-overdue-reminder-sweep
# ===========================================================================


class TestOverdueReminderSweep:
    """Cron-callable sweep that fires feedback reminders."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_sweep_with_no_overdue_returns_zero(self, mock_crud, owner_client):
        mock_crud.list_records.return_value = []
        resp = owner_client.post(
            "/recruitment/feedback/run-overdue-reminder-sweep",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["reminders_sent"] == 0
        assert body["overdue_count"] == 0

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_sweep_calls_send_feedback_reminders(self, mock_crud, owner_client):
        # One completed interview from 50h ago with no feedback.
        old_dt = (datetime.now(timezone.utc) - timedelta(hours=50)).isoformat()
        interview = {
            "id": 1,
            "company_id": 1,
            "candidate_id": 5,
            "scheduled_at": old_dt,
            "status": "completed",
            "interview_type": "onsite",
        }
        candidate = _candidate(candidate_id=5)

        def fake_list(model, filters, **kwargs):
            if model == "InterviewSchedule":
                return [interview]
            if model == "InterviewFeedback":
                return []
            return []

        mock_crud.list_records.side_effect = fake_list
        mock_crud.read.return_value = candidate

        resp = owner_client.post(
            "/recruitment/feedback/run-overdue-reminder-sweep",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["overdue_count"] == 1
        # send_feedback_reminders is invoked internally — it counted 1 reminder.
        assert body["reminders_sent"] == 1

    def test_sweep_requires_admin_role(self, employee_client):
        """Non-admin users (employee role) get 403."""
        resp = employee_client.post(
            "/recruitment/feedback/run-overdue-reminder-sweep",
        )
        assert resp.status_code == 403


# ===========================================================================
# T-R022: Auto-trigger onboarding on hire
# ===========================================================================


class TestHireDeferredOnboarding:
    """hire_candidate does NOT create an OnboardingAssignment directly.

    Onboarding assignment is deferred to invitation acceptance time
    (auth.py::_register_employee_via_invitation -> auto_assign_default_onboarding),
    when the Employee row actually exists. Creating it eagerly in the hire
    endpoint produced dangling rows with employee_id=0.
    """

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_hire_does_not_create_onboarding_assignment_directly(
        self, mock_crud, owner_client,
    ):
        candidate = _candidate(candidate_id=5, stage="offered")
        offer = {
            "id": 1, "company_id": 1, "candidate_id": 5,
            "salary": 6000.0, "status": "sent",
        }

        def fake_list(model, filters, **kwargs):
            if model == "Offer":
                return [offer]
            if model == "Candidate":
                return [candidate]
            return []

        def fake_read(model, record_id):
            if model == "Candidate":
                return candidate
            if model == "JobListing":
                return _job(job_id=candidate["job_listing_id"])
            return {}

        mock_crud.list_records.side_effect = fake_list
        mock_crud.read.side_effect = fake_read
        created = []

        def fake_create(model, data):
            created.append((model, data))
            return {**data, "id": 1000 + len(created)}

        mock_crud.create.side_effect = fake_create
        mock_crud.update.return_value = candidate

        resp = owner_client.post(
            "/recruitment/candidates/5/hire", json={"role": "employee"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # The hire response no longer includes onboarding_assignment_id —
        # assignment happens at invitation acceptance.
        assert "onboarding_assignment_id" not in body or body.get("onboarding_assignment_id") is None
        assert body["candidate_id"] == 5

        # Verify NO OnboardingAssignment is created in the hire flow.
        assignment_creates = [c for c in created if c[0] == "OnboardingAssignment"]
        assert len(assignment_creates) == 0, (
            "OnboardingAssignment should be deferred to invitation acceptance, "
            "not created at hire time (would produce employee_id=0 dangling row)"
        )

        # Verify the Invitation IS still created (the user-facing artifact).
        invitation_creates = [c for c in created if c[0] == "Invitation"]
        assert len(invitation_creates) == 1, "Invitation should be created at hire"


# ===========================================================================
# T-R030: PDPA pre-purge sweep
# ===========================================================================


class TestPdpaRetentionSweep:
    """run-data-retention-sweep finds 700d-old candidates and sends warnings."""

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_sweep_warns_eligible_candidates(
        self, mock_crud, mock_send, owner_client,
    ):
        # Candidate created 705 days ago, never warned, not hired.
        old_iso = (datetime.now(timezone.utc) - timedelta(days=705)).isoformat()
        recent_iso = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        eligible = _candidate(
            candidate_id=1, stage="rejected",
            created_at=old_iso, pdpa_purge_warned_at=None,
        )
        too_recent = _candidate(
            candidate_id=2, stage="rejected",
            created_at=recent_iso, pdpa_purge_warned_at=None,
        )

        def fake_list(model, filters, **kwargs):
            if model == "Candidate":
                return [eligible, too_recent]
            return []

        def fake_read(model, record_id):
            if model == "Company":
                return {"id": 1, "name": "Acme"}
            if model == "JobListing":
                return _job(job_id=100, title="Engineer")
            return {}

        mock_crud.list_records.side_effect = fake_list
        mock_crud.read.side_effect = fake_read
        mock_send.return_value = True

        resp = owner_client.post("/recruitment/run-data-retention-sweep")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["eligible_candidates"] == 1
        assert body["notified"] == 1

        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        assert kwargs["template_name"] == "data_retention_warning"

        # The pdpa_purge_warned_at stamp must be persisted.
        update_calls = [
            c for c in mock_crud.update.call_args_list
            if c[0][0] == "Candidate"
        ]
        assert any(
            "pdpa_purge_warned_at" in c[0][2] for c in update_calls
        ), "T-R030: pdpa_purge_warned_at must be stamped after warning"

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_sweep_is_idempotent_when_already_warned(
        self, mock_crud, mock_send, owner_client,
    ):
        """Already-warned candidates are skipped (no second email)."""
        already_warned = _candidate(
            candidate_id=1, stage="rejected",
            created_at=(datetime.now(timezone.utc) - timedelta(days=705)).isoformat(),
            pdpa_purge_warned_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        def fake_list(model, filters, **kwargs):
            if model == "Candidate":
                return [already_warned]
            return []

        mock_crud.list_records.side_effect = fake_list
        mock_crud.read.return_value = {"id": 1, "name": "Acme"}
        mock_send.return_value = True

        resp = owner_client.post("/recruitment/run-data-retention-sweep")
        assert resp.status_code == 200
        body = resp.json()
        assert body["eligible_candidates"] == 0
        assert body["notified"] == 0
        mock_send.assert_not_called()


# ===========================================================================
# T-R035: Scorecard CRUD + weighted total
# ===========================================================================


class TestScorecardCRUD:
    """Scorecard templates + entries with weight validation and weighted average."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_template_happy_path(self, mock_crud, owner_client):
        mock_crud.create.return_value = {"id": 1, "name": "Engineer Tech", "criteria": "[]"}
        resp = owner_client.post(
            "/recruitment/scorecard-templates",
            json={
                "name": "Engineer Tech",
                "description": "",
                "criteria": [
                    {"name": "coding", "weight": 0.6},
                    {"name": "system_design", "weight": 0.4},
                ],
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["template"]["id"] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_template_rejects_weights_not_summing_to_one(
        self, mock_crud, owner_client,
    ):
        resp = owner_client.post(
            "/recruitment/scorecard-templates",
            json={
                "name": "Bad Weights",
                "criteria": [
                    {"name": "a", "weight": 0.5},
                    {"name": "b", "weight": 0.3},
                ],
            },
        )
        assert resp.status_code == 400
        assert "1.0" in resp.json()["detail"]

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_create_entry_computes_weighted_total(self, mock_crud, owner_client):
        import json

        feedback = {"id": 9, "company_id": 1}
        template = {
            "id": 1,
            "company_id": 1,
            "criteria": json.dumps([
                {"name": "coding", "weight": 0.6},
                {"name": "system_design", "weight": 0.4},
            ]),
        }

        def fake_read(model, record_id):
            if model == "InterviewFeedback":
                return feedback
            if model == "ScorecardTemplate":
                return template
            return {}

        mock_crud.read.side_effect = fake_read
        mock_crud.create.return_value = {"id": 100}

        resp = owner_client.post(
            "/recruitment/interview-feedback/9/scorecards",
            json={
                "template_id": 1,
                "scores": {"coding": 5, "system_design": 4},
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Weighted: (5*0.6 + 4*0.4) / 1.0 = 4.6
        assert body["total_score"] == pytest.approx(4.6, abs=0.01)


# ===========================================================================
# T-R053: TAFEP scan_with_ai fallback
# ===========================================================================


class TestTafepScanWithAI:
    """scan_with_ai falls back to ai_unavailable=True on any failure."""

    def test_no_api_keys_returns_ai_unavailable(self, monkeypatch):
        from hr_advisory.services.tafep_scanner import scan_with_ai

        # Strip every key that scan_with_ai might use.
        for var in (
            "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
            "OPENAI_PROD_MODEL", "DEFAULT_LLM_MODEL", "GEMINI_MODEL",
        ):
            monkeypatch.delenv(var, raising=False)

        result = scan_with_ai("Looking for young Singaporeans only.")
        assert result["findings"] == []
        assert result.get("ai_unavailable") is True
        assert "reason" in result

    def test_llm_failure_path_falls_back(self, monkeypatch):
        """When the LLM call raises, we get ai_unavailable=True (never raises)."""
        from hr_advisory.services import tafep_scanner

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_PROD_MODEL", "test-model")

        # Patch the OpenAI import path so the call raises.
        class _FakeOpenAI:
            def __init__(self, *a, **kw):
                raise RuntimeError("network unavailable")

        # Build a stub module with an OpenAI symbol.
        import sys
        import types

        fake_mod = types.ModuleType("openai")
        fake_mod.OpenAI = _FakeOpenAI
        monkeypatch.setitem(sys.modules, "openai", fake_mod)

        result = tafep_scanner.scan_with_ai("Some advert text.")
        assert result["findings"] == []
        assert result.get("ai_unavailable") is True

    def test_ai_check_returns_findings_when_llm_succeeds(self, monkeypatch):
        """Smoke-test the success path: fake LLM returns one finding."""
        from hr_advisory.services import tafep_scanner

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_PROD_MODEL", "test-model")

        class _FakeChoice:
            class message:
                content = (
                    '{"findings": [{"matched_text": "young", '
                    '"category": "age", "suggestion": "soften"}]}'
                )

        class _FakeResponse:
            choices = [_FakeChoice()]

        class _FakeChat:
            class completions:
                @staticmethod
                def create(*args, **kwargs):
                    return _FakeResponse()

        class _FakeClient:
            def __init__(self, *a, **kw):
                self.chat = _FakeChat()

        import sys
        import types

        fake_mod = types.ModuleType("openai")
        fake_mod.OpenAI = _FakeClient
        monkeypatch.setitem(sys.modules, "openai", fake_mod)

        result = tafep_scanner.scan_with_ai("we want young people")
        assert "ai_unavailable" not in result
        assert len(result["findings"]) == 1
        f = result["findings"][0]
        assert f["matched_text"] == "young"
        assert f["category"] == "age"
        assert f["source"] == "ai"


# ===========================================================================
# T-R060: Shadow tool registry alignment with real recruitment routes
# ===========================================================================


class TestShadowToolRegistryAlignment:
    """Every recruitment tool entry must point at a real recruitment route."""

    def test_every_recruitment_tool_resolves_to_a_real_route(self):
        from hr_advisory.api.routers.recruitment import router as rec_router
        from hr_advisory.shadow.tool_registry import get_tool_registry

        # Index real routes by (method, normalized_path) where path is keyed
        # on parameter NAMES from the router (because tool registry might use
        # different placeholder names like {id} vs {job_id}).
        real_routes: dict[tuple[str, str], str] = {}
        for route in rec_router.routes:
            if not hasattr(route, "methods"):
                continue
            for method in route.methods:
                if method in ("HEAD", "OPTIONS"):
                    continue
                # Normalize {anything} -> {} for comparison
                import re
                norm = re.sub(r"\{[^}]+\}", "{}", route.path)
                real_routes[(method.upper(), norm)] = route.path

        registry = get_tool_registry()
        recruitment_tools = registry.get_tools("recruitment")
        assert recruitment_tools, "Recruitment registry section is empty"

        import re

        missing = []
        for tool in recruitment_tools:
            # Strip the /recruitment prefix the registry uses.
            tool_path = tool.path
            if tool_path.startswith("/recruitment"):
                tool_path = tool_path[len("/recruitment") :] or "/"
            norm = re.sub(r"\{[^}]+\}", "{}", tool_path)
            key = (tool.method.upper(), norm)
            if key not in real_routes:
                missing.append((tool.action, tool.method, tool.path))

        assert not missing, (
            f"Shadow tool registry has entries with no matching real route:\n"
            + "\n".join(f"  - {a}: {m} {p}" for a, m, p in missing)
        )


# ===========================================================================
# T-R061: Recruitment nudges
# ===========================================================================


class TestRecruitmentNudges:
    """_nudges_recruitment surfaces the 3 documented nudges given seeded data."""

    @patch("hr_advisory.shadow.nudges._dataflow_list")
    def test_emits_three_nudges_when_all_conditions_met(self, mock_list):
        from hr_advisory.shadow.nudges import _nudges_recruitment

        # 1. Stalled-interview candidate (last update >7d ago).
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).date().isoformat()
        # 2. Completed interview missing feedback.
        # 3. Offer expiring in <72h.
        soon_date = (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat()

        def fake_list(node_type, filters, limit=10000):
            if node_type == "CandidateListNode" and filters.get("stage") == "interview":
                return [
                    {"id": 1, "stage": "interview", "updated_at": old_date},
                ]
            if node_type == "InterviewScheduleListNode" and filters.get("status") == "completed":
                return [{"id": 9, "company_id": 1}]
            if node_type == "InterviewFeedbackListNode":
                # No feedback for interview 9.
                return []
            if node_type == "OfferListNode":
                return [
                    {"status": "sent", "expiry_date": soon_date},
                ]
            return []

        mock_list.side_effect = fake_list
        nudges = _nudges_recruitment(company_id=1, user_role="hr_manager")
        ids = {n["id"] for n in nudges}
        assert "nudge-recruitment-interview-stalled" in ids
        assert "nudge-recruitment-feedback-missing" in ids
        assert "nudge-recruitment-offer-expiring" in ids
        assert len(nudges) >= 3

    def test_non_admin_role_gets_empty(self):
        from hr_advisory.shadow.nudges import _nudges_recruitment

        result = _nudges_recruitment(company_id=1, user_role="employee")
        assert result == []


# ===========================================================================
# B05: Alert email delivery — severity gating
# ===========================================================================


class TestAlertEmailGating:
    """notify_users_of_alert sends only for critical/high severity."""

    async def test_low_severity_does_not_send(self):
        from hr_advisory.api.routers.alerts import notify_users_of_alert

        with patch(
            "hr_advisory.mcp_servers.adapters.resend_email.ResendAdapter"
        ) as mock_adapter:
            instance = MagicMock()
            instance.send_email = AsyncMock()
            mock_adapter.return_value = instance

            sent = await notify_users_of_alert(
                alert_title="Routine update",
                alert_description="...",
                severity="low",
            )
            assert sent == 0
            instance.send_email.assert_not_called()

    async def test_critical_severity_triggers_email(self, monkeypatch):
        from hr_advisory.api.routers.alerts import notify_users_of_alert

        monkeypatch.setenv("RESEND_API_KEY", "re_test")

        # Patch dataflow_crud.list_records used inside the function.
        with patch(
            "hr_advisory.services.dataflow_crud.list_records"
        ) as mock_list, patch(
            "hr_advisory.services.dataflow_crud.read"
        ) as mock_read, patch(
            "hr_advisory.mcp_servers.adapters.resend_email.ResendAdapter"
        ) as mock_adapter:
            mock_list.return_value = [
                {
                    "id": 1, "email": "owner@x.com",
                    "role": "owner", "is_active": True, "company_id": 1,
                },
            ]
            mock_read.return_value = {"id": 1, "name": "Acme"}
            instance = MagicMock()
            instance.send_email = AsyncMock(return_value={"id": "ok"})
            mock_adapter.return_value = instance

            sent = await notify_users_of_alert(
                alert_title="MOM CPF rate change",
                alert_description="...",
                severity="critical",
                company_id=1,
            )
            assert sent == 1
            instance.send_email.assert_awaited_once()


# ===========================================================================
# B19: _validate_text_length helper extraction
# ===========================================================================


class TestValidateTextLengthHelperExtraction:
    """All routers must import _validate_text_length from _helpers (single source)."""

    def test_helper_is_shared_across_routers(self):
        from hr_advisory.api.routers import (
            _helpers,
            appraisals,
            attendance,
            inventory,
            leave,
            onboarding,
            projects,
            shifts,
        )

        canonical = _helpers._validate_text_length
        for module in (appraisals, attendance, inventory, leave,
                       onboarding, projects, shifts):
            symbol = getattr(module, "_validate_text_length", None)
            assert symbol is canonical, (
                f"B19: {module.__name__}._validate_text_length is not the "
                f"shared helper from _helpers.py"
            )


# ===========================================================================
# B21: Headcount sync warning
# ===========================================================================


class TestHeadcountSyncWarning:
    """profile response includes actual_employee_count + drift warning."""

    def test_response_includes_actual_employee_count(self):
        from hr_advisory.api.routers.profile import _company_to_response

        with patch("hr_advisory.services.dataflow_crud.list_records") as mock_list:
            mock_list.return_value = [
                {"id": i, "is_active": True, "pass_type": "citizen"}
                for i in range(10)
            ]
            response = _company_to_response({
                "id": 1,
                "name": "Acme",
                "headcount_local": 10,
                "headcount_pr": 0,
                "headcount_ep": 0,
                "headcount_sp": 0,
                "headcount_wp": 0,
            })
        assert response["actual_employee_count"] == 10
        # Drift is 0% — no warning.
        assert "headcount_warning" not in response

    def test_drift_above_10pc_emits_warning(self):
        from hr_advisory.api.routers.profile import _company_to_response

        # Manual fields say 10 employees, but only 5 actual — 50% drift.
        with patch("hr_advisory.services.dataflow_crud.list_records") as mock_list:
            mock_list.return_value = [
                {"id": i, "is_active": True} for i in range(5)
            ]
            response = _company_to_response({
                "id": 1,
                "name": "Acme",
                "headcount_local": 10,
                "headcount_pr": 0,
                "headcount_ep": 0,
                "headcount_sp": 0,
                "headcount_wp": 0,
            })
        assert response["actual_employee_count"] == 5
        assert "headcount_warning" in response


# ===========================================================================
# T204: Auto-seed default onboarding template on company creation
# ===========================================================================


class TestAutoSeedOnboardingTemplate:
    """Creating a company seeds a default onboarding template (T204)."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_seed_creates_default_onboarding_template(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_onboarding_template

        # No existing templates.
        mock_crud.list_records.return_value = []
        created: list[tuple[str, dict]] = []

        def fake_create(model, data):
            created.append((model, data))
            return {**data, "id": len(created)}

        mock_crud.create.side_effect = fake_create

        result = _seed_onboarding_template(company_id=42)
        assert "skipped" not in result

        template_creates = [c for c in created if c[0] == "OnboardingTemplate"]
        assert len(template_creates) == 1
        payload = template_creates[0][1]
        assert payload["is_default"] is True
        assert payload["is_active"] is True
        assert payload["company_id"] == 42

        # Modules + steps are also created.
        modules = [c for c in created if c[0] == "OnboardingModule"]
        assert modules, "T204: at least one OnboardingModule must be seeded"

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_seed_is_idempotent(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_onboarding_template

        mock_crud.list_records.return_value = [{"id": 1, "name": "Existing"}]

        result = _seed_onboarding_template(company_id=42)
        assert result.get("skipped") is True
        mock_crud.create.assert_not_called()

    def test_onboarding_template_is_in_seed_list(self):
        """seed_company_defaults registers the onboarding seeder."""
        from hr_advisory.services.company_seeding import seed_company_defaults

        with patch(
            "hr_advisory.services.company_seeding.dataflow_crud"
        ) as mock_crud, patch(
            "hr_advisory.services.company_seeding._execute_node"
        ) as mock_exec:
            mock_crud.list_records.return_value = [{"id": 1}]  # skip everything
            mock_crud.create.return_value = {"id": 1}
            mock_exec.return_value = []

            summary = seed_company_defaults(company_id=1)
        assert "onboarding_template" in summary, (
            "T204: seed_company_defaults must call _seed_onboarding_template"
        )


# ===========================================================================
# T205: Onboarding overdue nudges
# ===========================================================================


class TestOnboardingOverdueNudges:
    """Nudge generator surfaces new hires with steps overdue >3 days."""

    @patch("hr_advisory.shadow.nudges._dataflow_list")
    def test_emits_nudge_when_steps_overdue_more_than_3_days(self, mock_list):
        from hr_advisory.shadow.nudges import _nudges_onboarding

        old_due = (datetime.now(timezone.utc) - timedelta(days=10)).date().isoformat()

        def fake_list(node_type, filters, limit=10000):
            if node_type == "OnboardingStepProgressListNode":
                return [{"assignment_id": 99, "due_date": old_due}]
            if node_type == "OnboardingAssignmentListNode":
                return [
                    {
                        "id": 99,
                        "company_id": 1,
                        "employee_id": 200,
                        "due_date": old_due,
                    },
                ]
            return []

        mock_list.side_effect = fake_list

        nudges = _nudges_onboarding(company_id=1, user_role="hr_manager")
        assert any(n["id"] == "nudge-onboarding-overdue" for n in nudges)

    @patch("hr_advisory.shadow.nudges._dataflow_list")
    def test_no_nudge_when_due_dates_are_recent(self, mock_list):
        from hr_advisory.shadow.nudges import _nudges_onboarding

        recent_due = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()

        def fake_list(node_type, filters, limit=10000):
            if node_type == "OnboardingStepProgressListNode":
                return [{"assignment_id": 99, "due_date": recent_due}]
            if node_type == "OnboardingAssignmentListNode":
                return [
                    {
                        "id": 99,
                        "company_id": 1,
                        "employee_id": 200,
                        "due_date": recent_due,
                    },
                ]
            return []

        mock_list.side_effect = fake_list

        nudges = _nudges_onboarding(company_id=1, user_role="hr_manager")
        assert not any(n["id"] == "nudge-onboarding-overdue" for n in nudges)
