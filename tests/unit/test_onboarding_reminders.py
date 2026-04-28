"""Unit tests for the T207 onboarding overdue-reminder endpoint.

Covers ``POST /onboarding/reminders/send-overdue``:

1. RBAC — only owner/hr_manager can hit the endpoint; employees get 403.
2. Happy path — overdue pending steps trigger an email per affected
   employee, completed/cancelled assignments are skipped, and assignments
   without due dates are ignored.
3. No RESEND_API_KEY — the endpoint short-circuits cleanly with a sentinel
   summary instead of erroring.
4. Rate limiting — the 5/hour/company guard kicks in on the 6th call.

Tests fully mock ``dataflow_crud`` and the Resend adapter; no DB or HTTP
I/O is performed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.rate_limit import reset_rate_limit_state
from hr_advisory.api.routers.onboarding import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _fake_owner() -> dict:
    return {
        "sub": "10",
        "email": "owner@example.com",
        "role": "owner",
        "company_id": 42,
    }


def _fake_employee() -> dict:
    return {
        "sub": "11",
        "email": "alice@example.com",
        "role": "employee",
        "company_id": 42,
    }


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/onboarding")
    return app


@pytest.fixture()
def owner_client():
    reset_rate_limit_state()
    app = _make_app()
    app.dependency_overrides[get_current_user] = _fake_owner
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def employee_client():
    reset_rate_limit_state()
    app = _make_app()
    app.dependency_overrides[get_current_user] = _fake_employee
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_employee_role_is_forbidden(employee_client, monkeypatch):
    """Employees must not be able to trigger company-wide reminders."""
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    response = employee_client.post("/onboarding/reminders/send-overdue")
    assert response.status_code == 403


def test_no_api_key_short_circuits(owner_client, monkeypatch):
    """When RESEND_API_KEY is unset, the endpoint succeeds but skips delivery."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    with patch(
        "hr_advisory.api.routers.onboarding.dataflow_crud"
    ) as mock_crud:
        mock_crud.list_records.return_value = []
        mock_crud.read.return_value = {"name": "Acme Co"}

        response = owner_client.post("/onboarding/reminders/send-overdue")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company_id"] == 42
    assert body["summary"]["emails_sent"] == 0
    # Sentinel: -1 means email transport unavailable
    assert body["summary"]["skipped"] == -1


def test_overdue_assignments_trigger_email(owner_client, monkeypatch):
    """Pending steps on past-due assignments should generate exactly one
    reminder email per affected employee."""
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    overdue_assignment = {
        "id": 100,
        "company_id": 42,
        "employee_id": 7,
        "template_id": 5,
        "status": "in_progress",
        "due_date": yesterday,
    }
    fresh_assignment = {
        "id": 101,
        "company_id": 42,
        "employee_id": 8,
        "template_id": 5,
        "status": "in_progress",
        "due_date": tomorrow,  # not overdue — must be skipped
    }
    completed_assignment = {
        "id": 102,
        "company_id": 42,
        "employee_id": 9,
        "template_id": 5,
        "status": "completed",
        "due_date": yesterday,  # overdue but completed — must be skipped
    }
    no_due_date_assignment = {
        "id": 103,
        "company_id": 42,
        "employee_id": 10,
        "template_id": 5,
        "status": "in_progress",
        "due_date": None,
    }

    pending_step_progress = [
        {"id": 200, "assignment_id": 100, "step_id": 50, "status": "pending"},
        {"id": 201, "assignment_id": 100, "step_id": 51, "status": "pending"},
    ]

    def _list_records(model, _filters=None, **_kwargs):
        if model == "OnboardingAssignment":
            return [
                overdue_assignment,
                fresh_assignment,
                completed_assignment,
                no_due_date_assignment,
            ]
        if model == "OnboardingStepProgress":
            return pending_step_progress
        return []

    def _read(model, record_id):
        if model == "Company":
            return {"name": "Acme Co"}
        if model == "Employee" and record_id == 7:
            return {"id": 7, "user_id": 70, "company_id": 42}
        if model == "User" and record_id == 70:
            return {"id": 70, "email": "alice@example.com", "name": "Alice"}
        if model == "OnboardingTemplate" and record_id == 5:
            return {"id": 5, "name": "New Hire Onboarding"}
        if model == "OnboardingStep":
            return {"id": record_id, "title": f"Step {record_id}"}
        return None

    mock_adapter = MagicMock()
    mock_adapter.send_email = AsyncMock(return_value={"id": "msg_1", "status": "sent"})

    with (
        patch("hr_advisory.api.routers.onboarding.dataflow_crud") as mock_crud,
        patch(
            "hr_advisory.mcp_servers.adapters.resend_email.ResendAdapter",
            return_value=mock_adapter,
        ),
    ):
        mock_crud.list_records.side_effect = _list_records
        mock_crud.read.side_effect = _read

        response = owner_client.post("/onboarding/reminders/send-overdue")

    assert response.status_code == 200, response.text
    body = response.json()
    summary = body["summary"]
    assert summary["assignments_scanned"] == 4
    assert summary["overdue_assignments"] == 1
    assert summary["emails_sent"] == 1
    assert summary["employees_notified"] == 1

    mock_adapter.send_email.assert_awaited_once()
    call_kwargs = mock_adapter.send_email.await_args.kwargs
    assert call_kwargs["to"] == "alice@example.com"
    assert "New Hire Onboarding" in call_kwargs["subject"]


def test_rate_limit_blocks_after_five_calls(owner_client, monkeypatch):
    """The 5/hour cap MUST kick in on the 6th call within the window."""
    monkeypatch.setenv("RESEND_API_KEY", "test-key")

    with (
        patch("hr_advisory.api.routers.onboarding.dataflow_crud") as mock_crud,
        patch(
            "hr_advisory.mcp_servers.adapters.resend_email.ResendAdapter"
        ) as mock_adapter_cls,
    ):
        mock_crud.list_records.return_value = []
        mock_crud.read.return_value = {"name": "Acme Co"}
        mock_adapter_cls.return_value = MagicMock(
            send_email=AsyncMock(return_value={"id": "x", "status": "sent"})
        )

        for _ in range(5):
            ok = owner_client.post("/onboarding/reminders/send-overdue")
            assert ok.status_code == 200, ok.text

        blocked = owner_client.post("/onboarding/reminders/send-overdue")
        assert blocked.status_code == 429
