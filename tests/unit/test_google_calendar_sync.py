"""Unit tests for the Google Calendar integration (T-R055).

All Google API calls are mocked.  These tests cover:

1. Signed state — round-trips and rejects spoofed/expired states.
2. ``oauth.exchange_code`` — verifies state, persists tokens.
3. ``sync.build_event_body`` — builds the right payload from an interview dict.
4. ``sync.create_event`` / ``update_event`` / ``delete_event`` — call Google
   with the right arguments and tolerate failures gracefully.
5. ``schedule_interview`` — invokes the sync layer.
6. The webhook — rejects bad channel tokens before patching the row.
"""

from __future__ import annotations

import importlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_oauth_state_secret(monkeypatch):
    """Round-13 H2: production code refuses to sign OAuth state with the
    default placeholder. Tests need a real secret in the env.

    Tests that explicitly verify the fail-fast path (e.g.
    `test_default_secret_rejected`) override this with their own
    monkeypatch."""
    monkeypatch.setenv(
        "OAUTH_STATE_SECRET",
        "test-oauth-state-secret-32-chars-min-12345",
    )


# ---------------------------------------------------------------------------
# Signed state
# ---------------------------------------------------------------------------


class TestSignedState:
    def test_roundtrip(self):
        from hr_advisory.integrations.google_calendar import oauth

        signed = oauth.build_signed_state(42, 7)
        assert oauth.verify_signed_state(signed) == (42, 7)

    def test_tampered_payload_rejected(self):
        from hr_advisory.integrations.google_calendar import oauth

        signed = oauth.build_signed_state(42, 7)
        head, sig = signed.split(".", 1)
        # Flip the last char of the signature so HMAC mismatches.
        flipped = head + "." + sig[:-1] + ("A" if sig[-1] != "A" else "B")
        with pytest.raises(oauth.OAuthStateError):
            oauth.verify_signed_state(flipped)

    def test_expired_state_rejected(self):
        from hr_advisory.integrations.google_calendar import oauth

        # Build a state that was issued 30 minutes ago.
        old_time = time.time() - (30 * 60)
        signed = oauth.build_signed_state(7, 99, now=old_time)
        with pytest.raises(oauth.OAuthStateError):
            oauth.verify_signed_state(signed)

    def test_default_secret_rejected(self, monkeypatch):
        """Round-13 H2: must fail-fast when OAUTH_STATE_SECRET / JWT_SECRET_KEY
        is unset or set to a known-default placeholder."""
        from hr_advisory.integrations.google_calendar import oauth

        monkeypatch.delenv("OAUTH_STATE_SECRET", raising=False)
        monkeypatch.setenv("JWT_SECRET_KEY", "change-this-in-production")
        with pytest.raises(RuntimeError, match="non-default"):
            oauth.build_signed_state(42, 7)


# ---------------------------------------------------------------------------
# OAuth exchange_code (state binding to user_id — round-13 CRIT-S3)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# OAuth exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    def test_exchange_code_persists_tokens(self):
        from hr_advisory.integrations.google_calendar import oauth

        signed = oauth.build_signed_state(99, 5)

        # Fake credentials object returned by the Flow.
        fake_creds = MagicMock()
        fake_creds.token = "ACCESS-TOKEN"
        fake_creds.refresh_token = "REFRESH-TOKEN"
        fake_creds.scopes = [oauth.GOOGLE_CALENDAR_SCOPE]
        fake_creds.token_uri = "https://oauth2.googleapis.com/token"
        fake_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        fake_flow = MagicMock()
        fake_flow.credentials = fake_creds

        persisted: dict[str, Any] = {}

        def fake_persist(record):
            persisted.update(record)
            persisted.setdefault("id", 1)
            return persisted

        with patch.dict(
            "os.environ",
            {
                "GOOGLE_OAUTH_CLIENT_ID": "client",
                "GOOGLE_OAUTH_CLIENT_SECRET": "secret",
            },
            clear=False,
        ), patch.object(oauth, "_build_flow", return_value=fake_flow), patch.object(
            oauth, "_persist_connection", side_effect=fake_persist
        ):
            result = oauth.exchange_code(
                "AUTH-CODE", signed, expected_user_id=5
            )

        # The Flow had its code exchanged.
        fake_flow.fetch_token.assert_called_once_with(code="AUTH-CODE")
        # The persisted record carries the right fields.
        assert result["company_id"] == 99
        assert result["access_token"] == "ACCESS-TOKEN"
        assert result["refresh_token"] == "REFRESH-TOKEN"
        assert oauth.GOOGLE_CALENDAR_SCOPE in result["scope"]
        # The user that completed the callback is recorded as connected_by.
        assert result["connected_by"] == 5

    def test_exchange_code_rejects_bad_state(self):
        from hr_advisory.integrations.google_calendar import oauth

        with pytest.raises(oauth.OAuthStateError):
            oauth.exchange_code(
                "AUTH-CODE", "not.a.valid.state", expected_user_id=1
            )

    def test_exchange_code_rejects_user_mismatch(self):
        """Round-13 CRIT-S3: state issued for user 5 cannot be redeemed
        by a callback authenticated as user 6, even within the same
        company. This blocks the cross-user OAuth-state-stealing chain."""
        from hr_advisory.integrations.google_calendar import oauth

        signed = oauth.build_signed_state(99, 5)
        with pytest.raises(oauth.OAuthStateError, match="different user"):
            oauth.exchange_code(
                "AUTH-CODE", signed, expected_user_id=6
            )


# ---------------------------------------------------------------------------
# sync.build_event_body
# ---------------------------------------------------------------------------


class TestBuildEventBody:
    def test_payload_shape(self):
        from hr_advisory.integrations.google_calendar import sync

        body = sync.build_event_body(
            {
                "id": 17,
                "scheduled_at": "2026-05-12T10:30:00+00:00",
                "duration_minutes": 45,
                "location": "Singapore office",
                "interviewers": ["alice@acme.io", {"email": "bob@acme.io"}],
                "candidate_email": "carol@example.com",
                "candidate_name": "Carol Lee",
                "job_title": "Senior Engineer",
                "notes": "Bring portfolio.",
            }
        )

        assert body["summary"] == "Interview: Carol Lee for Senior Engineer"
        assert body["location"] == "Singapore office"
        assert body["start"]["dateTime"].startswith("2026-05-12T10:30")
        # 10:30 + 45min = 11:15
        assert "11:15" in body["end"]["dateTime"]
        emails = sorted(a["email"] for a in body["attendees"])
        assert emails == ["alice@acme.io", "bob@acme.io", "carol@example.com"]
        assert "View in Arbor" in body["description"]
        assert "/recruitment/interviews/17" in body["description"]

    def test_cancelled_status_passed_through(self):
        from hr_advisory.integrations.google_calendar import sync

        body = sync.build_event_body(
            {
                "id": 1,
                "scheduled_at": "2026-05-12T10:30:00+00:00",
                "duration_minutes": 60,
                "interviewers": [],
                "candidate_email": "a@b.com",
                "candidate_name": "A",
                "job_title": "B",
                "status": "cancelled",
            }
        )
        assert body["status"] == "cancelled"

    def test_interviewers_can_be_json_string(self):
        # The DataFlow row stores ``interviewers`` as a JSON-encoded string.
        from hr_advisory.integrations.google_calendar import sync

        body = sync.build_event_body(
            {
                "id": 1,
                "scheduled_at": "2026-05-12T10:30:00+00:00",
                "duration_minutes": 60,
                "interviewers": json.dumps(["x@y.io"]),
                "candidate_email": "c@d.io",
                "candidate_name": "C",
                "job_title": "D",
            }
        )
        emails = sorted(a["email"] for a in body["attendees"])
        assert emails == ["c@d.io", "x@y.io"]


# ---------------------------------------------------------------------------
# sync.create_event / update_event / delete_event
# ---------------------------------------------------------------------------


def _fake_calendar_service(returned_event_id: str = "EVT-1") -> MagicMock:
    """Build a fake ``googleapiclient`` service supporting the endpoints we use."""

    service = MagicMock()
    insert_chain = service.events.return_value.insert.return_value
    insert_chain.execute.return_value = {"id": returned_event_id}
    patch_chain = service.events.return_value.patch.return_value
    patch_chain.execute.return_value = {"id": returned_event_id}
    delete_chain = service.events.return_value.delete.return_value
    delete_chain.execute.return_value = None
    get_chain = service.events.return_value.get.return_value
    get_chain.execute.return_value = {
        "id": returned_event_id,
        "status": "confirmed",
        "location": "Updated location",
        "start": {"dateTime": "2026-05-12T11:00:00+00:00"},
    }
    return service


class TestSyncEventOperations:
    def test_create_event_calls_google_with_built_payload(self):
        from hr_advisory.integrations.google_calendar import sync

        service = _fake_calendar_service("EVT-100")
        with patch.object(sync, "_build_service", return_value=service):
            event_id = sync.create_event(
                company_id=1,
                interview={
                    "id": 5,
                    "scheduled_at": "2026-05-12T10:00:00+00:00",
                    "duration_minutes": 60,
                    "interviewers": ["i@x.io"],
                    "candidate_email": "c@x.io",
                    "candidate_name": "Cand",
                    "job_title": "Eng",
                    "location": "HQ",
                },
            )
        assert event_id == "EVT-100"
        # Verify the body passed to insert
        insert_call = service.events.return_value.insert.call_args
        body = insert_call.kwargs["body"]
        assert body["summary"] == "Interview: Cand for Eng"
        assert body["location"] == "HQ"

    def test_create_event_returns_none_when_not_connected(self):
        from hr_advisory.integrations.google_calendar import sync

        with patch.object(sync, "_build_service", return_value=None):
            result = sync.create_event(
                company_id=1,
                interview={
                    "id": 5,
                    "scheduled_at": "2026-05-12T10:00:00+00:00",
                    "duration_minutes": 60,
                    "interviewers": [],
                    "candidate_email": "c@x.io",
                    "candidate_name": "C",
                    "job_title": "E",
                },
            )
        assert result is None

    def test_create_event_swallows_google_errors(self):
        from hr_advisory.integrations.google_calendar import sync

        service = _fake_calendar_service()
        # Make insert blow up
        service.events.return_value.insert.return_value.execute.side_effect = (
            RuntimeError("boom")
        )
        with patch.object(sync, "_build_service", return_value=service):
            result = sync.create_event(
                company_id=1,
                interview={
                    "id": 5,
                    "scheduled_at": "2026-05-12T10:00:00+00:00",
                    "duration_minutes": 60,
                    "interviewers": [],
                    "candidate_email": "c@x.io",
                    "candidate_name": "C",
                    "job_title": "E",
                },
            )
        assert result is None  # Best-effort: never raise.

    def test_update_event_patches_existing_event(self):
        from hr_advisory.integrations.google_calendar import sync

        service = _fake_calendar_service("EVT-7")
        with patch.object(sync, "_build_service", return_value=service):
            result = sync.update_event(
                company_id=1,
                google_event_id="EVT-7",
                interview={
                    "id": 5,
                    "scheduled_at": "2026-05-12T11:00:00+00:00",
                    "duration_minutes": 90,
                    "interviewers": [],
                    "candidate_email": "c@x.io",
                    "candidate_name": "C",
                    "job_title": "E",
                    "location": "Online",
                },
            )
        assert result == "EVT-7"
        patch_call = service.events.return_value.patch.call_args
        assert patch_call.kwargs["eventId"] == "EVT-7"
        assert patch_call.kwargs["body"]["location"] == "Online"

    def test_delete_event_calls_google(self):
        from hr_advisory.integrations.google_calendar import sync

        service = _fake_calendar_service("EVT-1")
        with patch.object(sync, "_build_service", return_value=service):
            ok = sync.delete_event(company_id=1, google_event_id="EVT-1")
        assert ok is True
        delete_call = service.events.return_value.delete.call_args
        assert delete_call.kwargs["eventId"] == "EVT-1"


# ---------------------------------------------------------------------------
# schedule_interview hook calls sync.create_event
# ---------------------------------------------------------------------------


class TestScheduleInterviewHook:
    @pytest.mark.asyncio
    async def test_schedule_interview_invokes_sync_create_event(self):
        from hr_advisory.api.routers import recruitment

        # Patch dataflow_crud and sync.
        captured: dict[str, Any] = {}

        def fake_create(model_name, data):
            if model_name == "InterviewSchedule":
                captured["interview"] = {**data, "id": 123}
                return captured["interview"]
            return {**data, "id": 1}

        def fake_read(model_name, record_id):
            if model_name == "Candidate":
                return {
                    "id": record_id,
                    "company_id": 1,
                    "name": "Carol",
                    "email": "carol@example.com",
                    "stage": "screening",
                    "job_listing_id": 7,
                }
            if model_name == "JobListing":
                return {"id": record_id, "title": "Senior Engineer"}
            if model_name == "Company":
                return {"id": record_id, "name": "Acme"}
            return None

        def fake_update(*args, **kwargs):
            return {}

        def fake_list(model_name, filters, limit=10000):
            return [{"id": 999, "candidate_id": filters.get("candidate_id"), "company_id": 1}]

        verify_returned = {
            "id": 1,
            "company_id": 1,
            "name": "Carol",
            "email": "carol@example.com",
            "stage": "screening",
            "job_listing_id": 7,
        }

        sync_calls: list[tuple] = []

        def fake_create_event(company_id, payload):
            sync_calls.append((company_id, payload))
            return "GCAL-EVT-42"

        # Build a dummy request
        class FakeRequest:
            async def json(self):
                return {
                    "scheduled_at": "2026-05-12T10:00:00+00:00",
                    "duration_minutes": 60,
                    "interview_type": "video",
                    "location": "Online",
                    "interviewers": ["alice@x.io"],
                    "notes": "",
                }

        with patch.object(recruitment.dataflow_crud, "create", side_effect=fake_create), patch.object(
            recruitment.dataflow_crud, "read", side_effect=fake_read
        ), patch.object(recruitment.dataflow_crud, "update", side_effect=fake_update), patch.object(
            recruitment.dataflow_crud, "list_records", side_effect=fake_list
        ), patch.object(recruitment, "_verify_candidate_ownership", return_value=verify_returned), patch.object(
            recruitment, "get_current_company_id", return_value=1
        ), patch.object(
            recruitment.gcal_sync, "create_event", side_effect=fake_create_event
        ), patch.object(
            recruitment, "_send_recruitment_email", return_value=False
        ):
            result = await recruitment.schedule_interview(
                candidate_id=1,
                request=FakeRequest(),
                current_user={"sub": 5, "company_id": 1, "role": "owner"},
            )

        assert result["interview"]["id"] == 123
        assert sync_calls, "sync.create_event was not called"
        company_id, payload = sync_calls[0]
        assert company_id == 1
        assert payload["candidate_email"] == "carol@example.com"
        assert payload["job_title"] == "Senior Engineer"
        assert payload["scheduled_at"] == "2026-05-12T10:00:00+00:00"


# ---------------------------------------------------------------------------
# Webhook channel-token validation
# ---------------------------------------------------------------------------


class TestWebhookAuth:
    @pytest.mark.asyncio
    async def test_webhook_rejects_bad_channel_token(self):
        from fastapi import HTTPException

        from hr_advisory.api.routers import integrations_calendar

        # The stored connection expects token ``GOOD-TOKEN``; the webhook
        # arrives with ``BAD-TOKEN`` so we expect an HTTP 401.
        def fake_list(model_name, filters, limit=10000):
            if model_name == "GoogleCalendarConnection":
                return [
                    {
                        "id": 1,
                        "company_id": 1,
                        "channel_id": filters.get("channel_id"),
                        "channel_token": "GOOD-TOKEN",
                    }
                ]
            return []

        class FakeRequest:
            def __init__(self, headers):
                self.headers = headers

            async def body(self):
                return b"{}"

        request = FakeRequest(
            headers={
                "X-Goog-Channel-ID": "chan-1",
                "X-Goog-Channel-Token": "BAD-TOKEN",
                "X-Goog-Resource-State": "exists",
                "X-Goog-Resource-ID": "res-1",
            }
        )

        with patch.object(
            integrations_calendar.dataflow_crud, "list_records", side_effect=fake_list
        ):
            with pytest.raises(HTTPException) as exc:
                await integrations_calendar.google_calendar_webhook(request)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_webhook_patches_interview_when_token_matches(self):
        from hr_advisory.api.routers import integrations_calendar

        updates: list[tuple] = []

        def fake_list(model_name, filters, limit=10000):
            if model_name == "GoogleCalendarConnection":
                return [
                    {
                        "id": 1,
                        "company_id": 1,
                        "channel_id": filters.get("channel_id"),
                        "channel_token": "GOOD-TOKEN",
                    }
                ]
            if model_name == "InterviewSchedule":
                return [
                    {
                        "id": 50,
                        "company_id": 1,
                        "google_event_id": filters.get("google_event_id"),
                        "scheduled_at": "2026-05-12T10:00:00+00:00",
                        "location": "Old",
                        "status": "scheduled",
                    }
                ]
            return []

        def fake_update(model_name, rec_id, data):
            updates.append((model_name, rec_id, data))
            return data

        def fake_fetch_event(company_id, google_event_id):
            return {
                "id": google_event_id,
                "status": "confirmed",
                "location": "New location",
                "start": {"dateTime": "2026-05-12T11:00:00+00:00"},
            }

        class FakeRequest:
            def __init__(self):
                self.headers = {
                    "X-Goog-Channel-ID": "chan-1",
                    "X-Goog-Channel-Token": "GOOD-TOKEN",
                    "X-Goog-Resource-State": "exists",
                    "X-Goog-Resource-ID": "res-1",
                }

            async def body(self):
                return json.dumps({"id": "EVT-50"}).encode("utf-8")

        with patch.object(
            integrations_calendar.dataflow_crud, "list_records", side_effect=fake_list
        ), patch.object(
            integrations_calendar.dataflow_crud, "update", side_effect=fake_update
        ), patch.object(
            integrations_calendar.sync, "fetch_event", side_effect=fake_fetch_event
        ):
            response = await integrations_calendar.google_calendar_webhook(FakeRequest())

        # Webhook returned 200 + the interview was patched with the new fields.
        assert response.status_code == 200
        interview_updates = [u for u in updates if u[0] == "InterviewSchedule"]
        assert interview_updates, "expected an InterviewSchedule update"
        _, rec_id, data = interview_updates[0]
        assert rec_id == 50
        assert data.get("location") == "New location"
        assert data.get("scheduled_at") == "2026-05-12T11:00:00+00:00"
