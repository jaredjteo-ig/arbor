"""Regression tests for round-13 H — Google Calendar disconnect routing.

Bug: clicking "Disconnect" on the Google Calendar settings card returned
a fake-success response without actually revoking tokens. Root cause:
the generic ``POST /integrations/{provider}/disconnect`` route in
``routers/integrations.py`` is registered BEFORE the dedicated T-R055
``POST /integrations/google-calendar/disconnect`` route in
``routers/integrations_calendar.py``. FastAPI matches routes in
registration order, so the generic catch-all wins for the
``google-calendar`` provider.

Fix: the generic handler now refuses to handle providers that have a
dedicated disconnect route (currently just ``google-calendar``) by
returning a 404 telling the caller to use the dedicated path. Because
both routes share the same path-with-different-prefix shape, FastAPI
falls through to the dedicated route and the actual revoke + delete
logic runs.

These tests pin three invariants:

1. ``POST /integrations/google-calendar/disconnect`` invokes the
   T-R055 handler (returns ``{"disconnected": bool}``), and the stored
   ``GoogleCalendarConnection`` row is deleted as a side-effect.
2. The generic ``/{provider}/disconnect`` handler still works for
   other providers (e.g. ``xero``) — the fix is scoped to the
   shadowed providers, not a global block.
3. If a developer accidentally hits the generic path for
   ``google-calendar`` (e.g. via direct curl), they get a 404 with a
   pointer to the dedicated route — never a silent fake-success.

These tests are permanent regression guards. NEVER delete them.
"""

from __future__ import annotations

import os
import time
import uuid

import jwt as pyjwt
import pytest
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")

from hr_advisory.config.settings import Settings, get_settings  # noqa: E402

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
get_settings.cache_clear()

from hr_advisory.api.platform import create_platform  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8097,
        cors_origins="http://localhost:3000",
        jwt_secret_key=_TEST_JWT_SECRET,
        jwt_algorithm="HS256",
        jwt_expiry_minutes=60,
    )


@pytest.fixture(scope="module")
def platform(settings):
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    return TestClient(platform._gateway.app)


def _make_token(settings: Settings, user_id: int, company_id: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": f"disconnect_routing_{uuid.uuid4().hex[:8]}@example.com",
        "role": "owner",
        "company_id": company_id,
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture()
def owner_token(settings) -> str:
    return _make_token(settings, user_id=99001, company_id=42)


@pytest.fixture()
def auth_headers(owner_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {owner_token}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeDataflow:
    """In-memory stand-in for ``hr_advisory.services.dataflow_crud``.

    Stores ``GoogleCalendarConnection`` rows keyed by ``id`` so the T-R055
    handler can find + delete them. Other models are no-ops.
    """

    def __init__(self) -> None:
        self.rows: dict[int, dict] = {}
        self.deletes: list[tuple[str, int]] = []
        self._next_id = 1

    def reset(self) -> None:
        self.rows.clear()
        self.deletes.clear()
        self._next_id = 1

    def seed_connection(self, company_id: int) -> int:
        rec_id = self._next_id
        self._next_id += 1
        self.rows[rec_id] = {
            "id": rec_id,
            "company_id": company_id,
            "status": "connected",
            "refresh_token": "",  # empty so disconnect() skips the network call
            "access_token": "",
            "scope": "https://www.googleapis.com/auth/calendar.events",
        }
        return rec_id

    def list_records(self, model: str, filters: dict, limit: int = 100):
        if model != "GoogleCalendarConnection":
            return []
        cid = int(filters.get("company_id", -1)) if filters else -1
        return [r for r in self.rows.values() if r["company_id"] == cid][:limit]

    def delete(self, model: str, record_id):
        self.deletes.append((model, int(record_id)))
        if model == "GoogleCalendarConnection":
            self.rows.pop(int(record_id), None)
        return True

    def update(self, *args, **kwargs):  # pragma: no cover - unused here
        return True

    def create(self, *args, **kwargs):  # pragma: no cover - unused here
        return {"id": 0}


@pytest.fixture()
def fake_dataflow(monkeypatch) -> _FakeDataflow:
    """Patch the dataflow_crud module the oauth helpers import lazily.

    ``oauth._load_connection`` and ``oauth.disconnect`` both do
    ``from hr_advisory.services import dataflow_crud`` *inside* the
    function body, so we patch the attributes on the module object.
    """
    fake = _FakeDataflow()
    from hr_advisory.services import dataflow_crud as real

    monkeypatch.setattr(real, "list_records", fake.list_records)
    monkeypatch.setattr(real, "delete", fake.delete)
    monkeypatch.setattr(real, "update", fake.update)
    monkeypatch.setattr(real, "create", fake.create)
    return fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_google_calendar_disconnect_invokes_dedicated_handler(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_dataflow: _FakeDataflow,
):
    """The dedicated route MUST run, not the generic ``/{provider}/disconnect``.

    Distinguishing markers:
      * Dedicated handler returns ``{"disconnected": bool}``.
      * Generic handler returns ``{"message": "...", "provider": "..."}``.

    The dedicated handler also deletes the ``GoogleCalendarConnection``
    row through ``dataflow_crud.delete``; the generic handler does not.
    """
    # Seed a connection for company 42 (matches the JWT in owner_token).
    rec_id = fake_dataflow.seed_connection(company_id=42)
    assert rec_id in fake_dataflow.rows

    response = client.post(
        "/integrations/google-calendar/disconnect",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    # Shape MUST match the T-R055 handler, not the generic one.
    assert "disconnected" in body, (
        "Expected dedicated-handler response shape {'disconnected': bool}; "
        f"got {body!r}. The generic /{'{provider}'}/disconnect route is "
        "shadowing /integrations/google-calendar/disconnect again."
    )
    assert isinstance(body["disconnected"], bool)
    assert body["disconnected"] is True

    # Generic handler keys MUST NOT appear.
    assert "message" not in body
    # 'provider' is included by the generic handler with a string value;
    # the dedicated handler omits it. Either absent or not the generic
    # placeholder is acceptable.
    assert body.get("provider") != "google-calendar" or "message" in body or len(body) == 1

    # The connection row MUST be deleted as a side-effect of the
    # dedicated handler's ``oauth.disconnect`` call.
    assert ("GoogleCalendarConnection", rec_id) in fake_dataflow.deletes, (
        "Dedicated disconnect handler should have deleted the "
        "GoogleCalendarConnection row, but no delete was recorded."
    )
    assert rec_id not in fake_dataflow.rows


@pytest.mark.regression
def test_generic_disconnect_still_works_for_other_providers(
    client: TestClient,
    auth_headers: dict[str, str],
):
    """The fix MUST NOT break disconnect for providers that legitimately
    use the generic catch-all (Xero, Microsoft Graph, etc.). Calling
    the generic route for ``xero`` should still hit the original handler
    and return its ``{"message": ..., "provider": ...}`` shape."""
    response = client.post(
        "/integrations/xero/disconnect",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    # Generic-handler shape.
    assert "message" in body
    assert body.get("provider") == "xero"


@pytest.mark.regression
def test_generic_disconnect_refuses_google_calendar_directly(
    client: TestClient,
    auth_headers: dict[str, str],
):
    """If a caller bypasses route precedence and somehow hits the generic
    handler with provider='google-calendar' (e.g. router order regression),
    we MUST NOT silently fake-succeed. Return 404 with a pointer to the
    dedicated route so the failure is loud.

    This is a belt-and-braces test: in normal operation FastAPI's route
    precedence sends ``/integrations/google-calendar/disconnect`` to the
    dedicated router (verified in the first test). This guard fires only
    if both prefixes ever overlap and the generic handler runs anyway.

    Verification strategy: the generic handler is reachable as the
    ``disconnect_provider_post`` function on its router; calling the
    function directly is the only way to bypass FastAPI's matcher. We
    simulate that here.
    """
    from fastapi import HTTPException

    from hr_advisory.api.routers.integrations import disconnect_provider_post

    fake_user = {"sub": "99001", "role": "owner", "company_id": 42, "id": "99001"}

    import asyncio

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            disconnect_provider_post(
                provider="google-calendar",
                current_user=fake_user,
            )
        )

    assert exc_info.value.status_code == 404
    detail = str(exc_info.value.detail)
    assert "google-calendar" in detail
    assert "/integrations/google-calendar/disconnect" in detail
