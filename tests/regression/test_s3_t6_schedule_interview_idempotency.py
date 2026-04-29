"""Regression: S3-T6 — schedule_interview idempotency.

Pre-S3-T6, double-clicking "Schedule Interview" created TWO
InterviewSchedule rows AND triggered two Google Calendar event creates.
The fix adds a 30-second window dedup on
`(candidate_id, scheduled_at, company_id)`.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.rate_limit import reset_rate_limit_state
from hr_advisory.api.routers.recruitment import router as recruitment_router


def _fake_owner() -> dict:
    return {"sub": "10", "email": "owner@example.com", "role": "owner", "company_id": 1}


@pytest.fixture()
def owner_client() -> TestClient:
    reset_rate_limit_state()
    app = FastAPI()
    app.include_router(recruitment_router, prefix="/recruitment")
    app.dependency_overrides[get_current_user] = _fake_owner
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        reset_rate_limit_state()


@pytest.mark.regression
def test_s3_t6_idempotency_guard_in_handler_source():
    """Source-level guard — the handler must check for an existing
    InterviewSchedule row created within 30 seconds before inserting a
    new one. Without this, two rapid POSTs both pass through to create.
    """
    from hr_advisory.api.routers import recruitment as recruitment_module

    src = inspect.getsource(recruitment_module.schedule_interview)
    # Idempotency guard markers
    assert "list_records" in src
    assert '"InterviewSchedule"' in src
    # The 30-second window check
    assert "30" in src
    # Must reference both candidate_id and scheduled_at in the dedup query
    assert "candidate_id" in src
    assert "scheduled_at" in src


@pytest.mark.regression
def test_s3_t6_duplicate_post_returns_existing_row(owner_client):
    """Two rapid POSTs with identical (candidate_id, scheduled_at) — the
    second MUST return the existing row, not create a new one.
    """
    candidate = {
        "id": 5,
        "company_id": 1,
        "job_listing_id": 1,
        "name": "Alice Tan",
        "email": "alice@example.com",
        "stage": "interview",
    }
    scheduled_at = "2026-05-15T10:00:00+00:00"
    create_calls: list[tuple[str, dict]] = []

    # The "existing row" returned by list_records on the SECOND call.
    # Created 5 seconds ago — well inside the 30s window.
    existing_row = {
        "id": 99,
        "company_id": 1,
        "candidate_id": 5,
        "scheduled_at": scheduled_at,
        "duration_minutes": 60,
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    list_call_count = {"n": 0}

    def _list_records(model: str, filters: dict):
        if model == "InterviewSchedule":
            list_call_count["n"] += 1
            # First call returns empty (so the create proceeds);
            # second call returns the existing row.
            if list_call_count["n"] == 1:
                return []
            return [existing_row]
        return []

    def _read(model: str, record_id: int):
        if model == "Candidate":
            return candidate
        if model == "JobListing":
            return {"id": 1, "title": "SWE", "department": "Engineering"}
        if model == "Company":
            return {"id": 1, "name": "Acme"}
        return None

    def _create(model: str, fields: dict):
        create_calls.append((model, fields))
        return {**fields, "id": existing_row["id"]}

    with patch("hr_advisory.api.routers.recruitment.dataflow_crud") as mock_crud, \
         patch("hr_advisory.api.routers.recruitment.gcal_sync"), \
         patch("hr_advisory.api.routers.recruitment._send_recruitment_email"), \
         patch("hr_advisory.api.routers.recruitment._verify_candidate_ownership", return_value=candidate):
        mock_crud.list_records.side_effect = _list_records
        mock_crud.read.side_effect = _read
        mock_crud.create.side_effect = _create
        mock_crud.update.return_value = candidate

        # First POST — list returns empty, so create proceeds
        resp1 = owner_client.post(
            "/recruitment/candidates/5/interviews",
            json={"scheduled_at": scheduled_at},
        )
        # Second POST — list returns the existing row created 5s ago
        resp2 = owner_client.post(
            "/recruitment/candidates/5/interviews",
            json={"scheduled_at": scheduled_at},
        )

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    # Only one create should have happened (first POST). The second hit
    # the dedup window and returned the existing row.
    interview_creates = [c for c in create_calls if c[0] == "InterviewSchedule"]
    assert len(interview_creates) == 1, (
        f"Second POST must NOT create a new row — got {len(interview_creates)} "
        f"InterviewSchedule creates."
    )
    # Second response must include "idempotent" signal in the detail
    assert "idempotent" in resp2.json().get("detail", "").lower()
