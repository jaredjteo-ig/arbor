"""Cluster 6 regression: recruitment red-team round-1 backlog (T-RX01..T-RX11).

T-RX07 (Redis-backed rate limiter) is covered by `test_b_cluster_5_redis_rate_limit.py`.
The other 10 items are pinned here so a future change cannot silently regress them.

Status at HEAD `3440ee0` (audited 2026-04-28):
  * T-RX01 — offer email uses currency + salary_period            (already fixed)
  * T-RX02 — talent-pool re-apply forces fresh PDPA consent       (already fixed)
  * T-RX03 — public_apply enforces required screening questions   (already fixed)
  * T-RX04 — public_list_jobs is slug-only (no name fallback)     (already fixed)
  * T-RX05 — rate-limit timestamps stored in bounded deque        (already fixed)
  * T-RX06 — candidate email masked in production logs            (already fixed)
  * T-RX08 — composite index on Candidate(job_listing_id, email)  (already fixed)
  * T-RX09 — pagination on list endpoints                         (newly fixed in this cluster
                                                                    for list_all_candidates and
                                                                    list_offers; the others were
                                                                    already paginated)
  * T-RX10 — stage-transition state machine on update_candidate   (already fixed)
  * T-RX11 — close_job cascades to candidates + offers            (already fixed)
"""

from __future__ import annotations

import inspect
import logging
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.rate_limit import reset_rate_limit_state
from hr_advisory.api.routers.recruitment import router as recruitment_router


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _fake_owner() -> dict:
    return {
        "sub": "10",
        "email": "owner@example.com",
        "role": "owner",
        "company_id": 1,
    }


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(recruitment_router, prefix="/recruitment")
    return app


@pytest.fixture()
def owner_client() -> TestClient:
    reset_rate_limit_state()
    app = _make_app()
    app.dependency_overrides[get_current_user] = _fake_owner
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        reset_rate_limit_state()


@pytest.fixture()
def public_client() -> TestClient:
    reset_rate_limit_state()
    app = _make_app()
    client = TestClient(app)
    try:
        yield client
    finally:
        reset_rate_limit_state()


def _candidate(**overrides) -> dict:
    base = {
        "id": 5,
        "company_id": 1,
        "job_listing_id": 1,
        "name": "Alice Tan",
        "email": "alice@example.com",
        "phone": "+6591234567",
        "stage": "interview",
        "source": "direct",
        "nationality": "Singapore",
        "citizenship_status": "citizen",
        "resume_url": "",
        "pdpa_consent": True,
        "pdpa_consent_date": "2026-01-01T00:00:00+00:00",
        "notes": "",
    }
    base.update(overrides)
    return base


def _offer(**overrides) -> dict:
    base = {
        "id": 1,
        "company_id": 1,
        "candidate_id": 5,
        "job_listing_id": 1,
        "salary": 7500.0,
        "currency": "SGD",
        "salary_period": "monthly",
        "start_date": "2026-06-01",
        "position_title": "Software Engineer",
        "employment_type": "full_time",
        "status": "approved",
        "expiry_date": "2026-05-15",
        "created_by": 10,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# T-RX01: Offer-sent email uses currency + period (no hardcoded "$")
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx01_send_offer_uses_currency_and_period_in_email(owner_client) -> None:
    """The salary string passed to `_send_recruitment_email` must include the
    currency code and salary period, NOT a hardcoded `$`.
    """
    captured: dict = {}

    async def _capture_email(*, to: str, template_name: str, variables: dict) -> bool:
        captured["to"] = to
        captured["template"] = template_name
        captured["variables"] = variables
        return True

    company = {"id": 1, "name": "Acme Pte Ltd"}
    offer = _offer(currency="SGD", salary=7500.0, salary_period="monthly")
    candidate = _candidate(email="alice@example.com")

    def _read(model: str, record_id: int):
        if model == "Offer":
            return offer
        if model == "Candidate":
            return candidate
        if model == "Company":
            return company
        return None

    with patch(
        "hr_advisory.api.routers.recruitment._send_recruitment_email",
        new=_capture_email,
    ), patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.read.side_effect = _read
        mock_crud.update.return_value = {**offer, "status": "sent"}

        resp = owner_client.post("/recruitment/offers/1/send")

    assert resp.status_code == 200, resp.text
    salary_var = captured["variables"]["salary"]
    assert "$" not in salary_var, (
        f"Offer email salary still uses hardcoded $: {salary_var!r}"
    )
    assert "SGD" in salary_var
    assert "7,500.00" in salary_var
    assert "monthly" in salary_var


# ---------------------------------------------------------------------------
# T-RX02: Re-apply from talent pool forces fresh PDPA consent
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx02_reapply_resets_pdpa_consent(owner_client) -> None:
    """`reapply_candidate` must create the new candidate record with
    `pdpa_consent=False`, an empty consent date, and a re-confirmation note."""
    source_candidate = _candidate(
        id=42,
        company_id=1,
        pdpa_consent=True,
        pdpa_consent_date="2024-01-01T00:00:00+00:00",
    )
    new_job = {"id": 99, "company_id": 1, "title": "Backend Engineer"}

    captured_create: dict = {}

    def _read(model: str, record_id: int):
        if model == "Candidate" and record_id == 42:
            return source_candidate
        if model == "JobListing" and record_id == 99:
            return new_job
        return None

    def _create(model: str, payload: dict) -> dict:
        captured_create["model"] = model
        captured_create["payload"] = payload
        return {"id": 100, **payload}

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.read.side_effect = _read
        mock_crud.create.side_effect = _create

        resp = owner_client.post(
            "/recruitment/candidates/42/reapply",
            json={"job_listing_id": 99},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["note"] == "PDPA consent must be re-confirmed for the new application."

    payload = captured_create["payload"]
    assert payload["pdpa_consent"] is False, (
        "Re-applied candidate must NOT inherit prior PDPA consent"
    )
    assert payload["pdpa_consent_date"] == "", (
        "Re-applied candidate must NOT inherit prior PDPA consent_date"
    )
    assert "PDPA consent must be re-confirmed" in payload["notes"]


# ---------------------------------------------------------------------------
# T-RX03: Required screening questions enforced on public apply
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx03_public_apply_rejects_missing_required_screening(public_client) -> None:
    """`public_apply` must return 400 when a required screening question is
    not answered. Optional questions are still accepted with no answer."""
    company = {"id": 1, "name": "Acme", "slug": "acme"}
    job = {
        "id": 7,
        "company_id": 1,
        "unique_slug": "backend-eng",
        "status": "open",
        "title": "Backend Engineer",
    }
    questions = [
        {
            "id": 11,
            "company_id": 1,
            "job_listing_id": 7,
            "question_text": "Years of Python?",
            "question_type": "text",
            "is_required": True,
            "sort_order": 1,
        },
        {
            "id": 12,
            "company_id": 1,
            "job_listing_id": 7,
            "question_text": "Preferred timezone?",
            "question_type": "text",
            "is_required": False,
            "sort_order": 2,
        },
    ]

    def _list_records(model: str, filters: dict):
        if model == "Company":
            return [company]
        if model == "JobListing":
            return [job]
        if model == "ScreeningQuestion":
            return questions
        if model == "Candidate":
            return []
        return []

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.list_records.side_effect = _list_records
        mock_crud.create.return_value = {"id": 500}

        resp = public_client.post(
            "/recruitment/careers/acme/jobs/backend-eng/apply",
            json={
                "name": "Bob",
                "email": "bob@example.com",
                "pdpa_consent": True,
                "screening_responses": [
                    # Only the optional question answered — required Q-11 missing.
                    {"question_id": 12, "response_text": "SGT"},
                ],
            },
        )

    assert resp.status_code == 400, resp.text
    assert "required screening" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# T-RX04: Public list-jobs is slug-only (no company-name fallback)
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx04_public_list_jobs_does_not_fall_back_to_company_name(public_client) -> None:
    """If no company has the given slug, the public endpoint must 404 — it
    must NOT try a name lookup, which would enable enumeration."""
    list_calls: list = []

    def _list_records(model: str, filters: dict):
        list_calls.append({"model": model, "filters": dict(filters)})
        return []  # Always empty — no slug match, no name fallback should be tried.

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.list_records.side_effect = _list_records

        resp = public_client.get("/recruitment/careers/acme-corp/jobs")

    assert resp.status_code == 404
    company_lookups = [c for c in list_calls if c["model"] == "Company"]
    assert company_lookups, "Endpoint should at minimum query Company by slug"
    for c in company_lookups:
        # Only slug should ever be the lookup key — never name.
        assert "name" not in c["filters"], (
            f"public_list_jobs reintroduced name fallback: {c['filters']!r}"
        )
        assert "slug" in c["filters"], (
            f"public_list_jobs must query by slug: {c['filters']!r}"
        )


# ---------------------------------------------------------------------------
# T-RX05: Rate-limit timestamps live in a bounded deque
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx05_rate_limit_timestamps_use_bounded_deque() -> None:
    """The per-key timestamp store must be a `collections.deque` with a
    `maxlen` so a request burst can't grow the list unboundedly."""
    from collections import deque

    from hr_advisory.api.middleware import rate_limit as rl

    rl.reset_rate_limit_state()
    try:
        # Force the in-memory branch by exercising it directly.
        rl._check_in_memory(  # type: ignore[attr-defined]
            "test:key",
            max_requests=3,
            window_seconds=60,
            action_name="t-rx05 regression",
        )
        bucket = rl._request_log["test:key"]  # type: ignore[attr-defined]
        assert isinstance(bucket, deque), (
            f"Expected bounded deque for rate-limit timestamps, got {type(bucket)!r}"
        )
        assert bucket.maxlen is not None, (
            "Deque must have a maxlen — unbounded buckets re-introduce the bug"
        )
        assert bucket.maxlen <= 1024, (
            f"Deque maxlen={bucket.maxlen} is suspiciously large"
        )
    finally:
        rl.reset_rate_limit_state()


# ---------------------------------------------------------------------------
# T-RX06: Candidate email masked in production logs
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx06_recruitment_email_log_masks_address(monkeypatch, caplog) -> None:
    """`_send_recruitment_email` must log a masked form of the recipient
    address, never the full email — emails are PII under PDPA."""
    import asyncio
    import os

    from hr_advisory.api.routers import recruitment as rec

    monkeypatch.setenv("RESEND_API_KEY", "test-key-not-real")

    class _StubAdapter:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def send_email(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(rec, "ResendAdapter", _StubAdapter)

    caplog.set_level(logging.INFO, logger=rec.logger.name)
    asyncio.run(
        rec._send_recruitment_email(
            to="alice.private@confidential-domain.example",
            template_name="application_received",
            variables={
                "candidate_name": "Alice",
                "job_title": "Engineer",
                "company_name": "Acme",
            },
        )
    )

    success_records = [
        r for r in caplog.records if r.message.startswith("Recruitment email sent")
    ]
    assert success_records, "Expected the success log line"
    msg = success_records[0].getMessage()
    assert "alice.private" not in msg, (
        f"Full email leaked into logs: {msg!r}"
    )
    assert "***" in msg, f"Mask marker missing from log line: {msg!r}"
    # Domain may be retained for ops debugging — that is still PDPA-acceptable.
    assert "@confidential-domain.example" in msg


# ---------------------------------------------------------------------------
# T-RX08: Composite index on Candidate(job_listing_id, email)
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx08_candidate_has_composite_job_email_index() -> None:
    """The Candidate model must declare a composite index on
    (job_listing_id, email) so duplicate-application checks are O(log n)."""
    from hr_advisory.models.company_user import Candidate

    indexes = Candidate.__dataflow__["indexes"]
    composite = [
        idx for idx in indexes
        if idx.get("fields") == ["job_listing_id", "email"]
    ]
    assert composite, (
        "Composite index (job_listing_id, email) missing from Candidate.__dataflow__"
    )


# ---------------------------------------------------------------------------
# T-RX09: Pagination on priority list endpoints
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx09_priority_list_endpoints_accept_pagination_params(owner_client) -> None:
    """`list_all_candidates`, `list_offers`, `search_talent_pool`, and
    `list_referrals` must all expose `page` and `page_size` query params and
    return both a `total` count and a sliced page."""
    from hr_advisory.api.routers import recruitment as rec

    # 1. Signature check — page/page_size are part of the public contract.
    for fn_name in (
        "list_all_candidates",
        "list_offers",
        "search_talent_pool",
        "list_referrals",
    ):
        fn = getattr(rec, fn_name)
        sig = inspect.signature(fn)
        assert "page" in sig.parameters, (
            f"{fn_name} missing `page` query param — pagination regressed"
        )
        assert "page_size" in sig.parameters, (
            f"{fn_name} missing `page_size` query param — pagination regressed"
        )

    # 2. Behavioural check — when 75 records exist, page_size=25 returns 25
    #    items and total=75. This pins the slicing logic, not just the params.
    candidates = [_candidate(id=i, email=f"c{i}@x.example") for i in range(1, 76)]

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.list_records.return_value = candidates

        resp = owner_client.get(
            "/recruitment/candidates", params={"page": 2, "page_size": 25}
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 75
    assert body["page"] == 2
    assert body["page_size"] == 25
    assert len(body["candidates"]) == 25
    # Page 2 of 25 starts at offset 25 -> id=26.
    assert body["candidates"][0]["id"] == 26

    # 3. list_offers also paginates and only enriches the returned page (so
    #    it can't be turned into a candidate-table sweep).
    offers = [_offer(id=i, candidate_id=i) for i in range(1, 11)]
    candidate_reads: list = []

    def _read(model: str, record_id: int):
        if model == "Candidate":
            candidate_reads.append(record_id)
            return _candidate(id=record_id, name=f"Cand {record_id}")
        return None

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.list_records.return_value = offers
        mock_crud.read.side_effect = _read

        resp = owner_client.get(
            "/recruitment/offers", params={"page": 1, "page_size": 3}
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 10
    assert len(body["offers"]) == 3
    # Enrichment must be limited to the page (3 reads), not the full table (10).
    assert len(candidate_reads) == 3, (
        f"list_offers enriched off-page rows: {candidate_reads!r}"
    )


# ---------------------------------------------------------------------------
# T-RX10: Stage-transition state machine on update_candidate
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx10_update_candidate_blocks_invalid_stage_transition(owner_client) -> None:
    """A hired candidate cannot be reverted to "new" via the generic PATCH —
    `update_candidate` must reject the move with a 400."""
    candidate = _candidate(id=5, stage="hired")

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.read.return_value = candidate

        resp = owner_client.patch(
            "/recruitment/candidates/5",
            json={"stage": "new"},
        )

    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"].lower()
    assert "hired" in detail or "transition" in detail or "terminal" in detail


@pytest.mark.regression
def test_t_rx10_update_candidate_allows_valid_stage_transition(owner_client) -> None:
    """The state machine must still let HR move a candidate forward through
    valid stages (e.g. screening -> interview)."""
    candidate = _candidate(id=5, stage="screening")
    updated = _candidate(id=5, stage="interview")

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.read.return_value = candidate
        mock_crud.update.return_value = updated

        resp = owner_client.patch(
            "/recruitment/candidates/5",
            json={"stage": "interview"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["candidate"]["stage"] == "interview"


# ---------------------------------------------------------------------------
# T-RX11: close_job cascades to candidates + pending offers
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_t_rx11_close_job_withdraws_active_candidates_and_expires_offers(owner_client) -> None:
    """Closing a job must:
       1. Move every candidate in an active stage to "withdrawn" with
          rejection_reason="job_closed".
       2. Expire every offer in a pending status (draft/pending_approval/
          approved/sent).
       Terminal candidate stages (hired/rejected/withdrawn) and final offer
       statuses (accepted/declined/expired) must be left untouched."""
    job = {"id": 7, "company_id": 1, "status": "open", "title": "BE"}
    candidates = [
        _candidate(id=101, stage="new"),
        _candidate(id=102, stage="screening"),
        _candidate(id=103, stage="hired"),  # terminal — must NOT change
        _candidate(id=104, stage="rejected"),  # terminal — must NOT change
        _candidate(id=105, stage="interview"),
    ]
    offers = [
        _offer(id=201, status="draft"),
        _offer(id=202, status="approved"),
        _offer(id=203, status="accepted"),  # terminal — must NOT change
        _offer(id=204, status="sent"),
    ]

    updates: list = []

    def _list_records(model: str, filters: dict):
        if model == "Candidate":
            return candidates
        if model == "Offer":
            return offers
        return []

    def _read(model: str, record_id: int):
        if model == "JobListing" and record_id == 7:
            return job
        if model == "Candidate":
            for c in candidates:
                if c["id"] == record_id:
                    return c
            return None
        return None

    def _update(model: str, record_id: int, payload: dict) -> dict:
        updates.append({"model": model, "id": record_id, "payload": payload})
        return {"id": record_id, **payload}

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud:
        mock_crud.list_records.side_effect = _list_records
        mock_crud.read.side_effect = _read
        mock_crud.update.side_effect = _update

        resp = owner_client.post("/recruitment/jobs/7/close")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["candidates_withdrawn"] == 3, body
    assert body["offers_expired"] == 3, body

    # Candidate updates: only ids 101, 102, 105 should have moved to withdrawn.
    cand_updates = [u for u in updates if u["model"] == "Candidate"]
    withdrawn_ids = {
        u["id"] for u in cand_updates
        if u["payload"].get("stage") == "withdrawn"
    }
    assert withdrawn_ids == {101, 102, 105}, withdrawn_ids
    for u in cand_updates:
        if u["payload"].get("stage") == "withdrawn":
            assert u["payload"]["rejection_reason"] == "job_closed"

    # Offer updates: only ids 201, 202, 204 should have moved to expired.
    offer_updates = [u for u in updates if u["model"] == "Offer"]
    expired_ids = {
        u["id"] for u in offer_updates
        if u["payload"].get("status") == "expired"
    }
    assert expired_ids == {201, 202, 204}, expired_ids
