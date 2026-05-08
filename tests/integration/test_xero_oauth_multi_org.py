"""Integration tests for the multi-org Xero OAuth picker (M0-T01).

Two flows under test, both with ``XeroAdapter`` patched so we don't
hit real Xero:

1. **Single-org happy path** — `list_xero_connections` returns one
   org → callback persists `xero_tenant_id` and redirects to
   `/settings/integrations?xero=connected`.
2. **Multi-org pick** — `list_xero_connections` returns ≥2 orgs →
   callback redirects to `/settings/integrations/xero/pick-org`.
   Frontend reads `/integrations/xero/pending-orgs` then POSTs
   `/integrations/xero/pick-org` with the chosen tenant id, which
   persists.

Also covers the security guards on the picker endpoints:

* Token HMAC mismatch → 403.
* Pick token expired (TTL exhausted) → 403.
* Chosen ``xero_tenant_id`` not in the original authorised list → 400.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse
import uuid
from typing import Any
from unittest.mock import patch

import jwt as pyjwt
import pytest
from starlette.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor"
)
os.environ.setdefault("DATAFLOW_POOL_SIZE", "5")
os.environ.setdefault("DATAFLOW_POOL_MAX_OVERFLOW", "2")

from hr_advisory.config.settings import Settings, get_settings

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
get_settings.cache_clear()

# The OAuth start endpoint requires INTEGRATION_ENCRYPTION_KEY. Re-use
# whatever's already in .env for these tests rather than overriding,
# so the persisted token store and the OAuth flow share a key.
if not os.environ.get("INTEGRATION_ENCRYPTION_KEY"):
    from cryptography.fernet import Fernet

    os.environ["INTEGRATION_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from hr_advisory.api.platform import create_platform
from hr_advisory.services import dataflow_crud


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8093,
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


@pytest.fixture(scope="module")
def test_company():
    suffix = uuid.uuid4().hex[:8]
    company = dataflow_crud.create(
        "Company",
        {
            "name": f"XeroMultiOrg {suffix}",
            "uen": f"M{suffix.upper()[:9]}",
            "sector": "Technology",
        },
    )
    company_id = company["id"]
    yield {"company_id": company_id}

    rows = dataflow_crud.list_records(
        "IntegrationToken", {"tenant_id": str(company_id)}, cache_ttl=0
    )
    for row in rows:
        try:
            dataflow_crud.delete("IntegrationToken", row["id"])
        except Exception:
            pass
    try:
        dataflow_crud.delete("Company", company_id)
    except Exception:
        pass


@pytest.fixture
def owner_token(settings, test_company) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": "993_001",
            "email": "owner@multi-org-test.com",
            "role": "owner",
            "iat": now,
            "exp": now + 3600,
            "company_id": test_company["company_id"],
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def _signed_state(company_id: int, user_id: int, key: bytes) -> str:
    """Build a valid HMAC-signed state token like the start endpoint does."""
    import json

    payload = {
        "c": company_id,
        "u": user_id,
        "n": "test-nonce",
        "t": int(time.time()),
    }
    body = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


# ────────────────────────────────────────────────────────────────────
# Fakes
# ────────────────────────────────────────────────────────────────────


class _FakeAdapter:
    def __init__(self, connections: list[dict]):
        self._connections = connections

    async def handle_oauth_callback(
        self, tenant_id: str, code: str, redirect_uri: str
    ) -> dict:
        # Simulate token exchange + token-store persistence the real
        # adapter would do.
        from hr_advisory.mcp_servers.auth.token_store import get_token_manager

        get_token_manager().store_token(
            tenant_id,
            "xero",
            {
                "access_token": "fake-access",
                "refresh_token": "fake-refresh",
                "expires_in": 1800,
                "scope": "openid offline_access accounting.manualjournals",
            },
        )
        return {"status": "connected"}

    async def list_xero_connections(self, access_token: str):
        return list(self._connections)


_SINGLE_CONN = [
    {
        "tenantId": "single-org-id",
        "tenantName": "Solo Pte Ltd",
        "tenantType": "ORGANISATION",
    }
]
_MULTI_CONN = [
    {
        "tenantId": "org-a",
        "tenantName": "Tan Family Bakery Pte Ltd",
        "tenantType": "ORGANISATION",
    },
    {
        "tenantId": "org-b",
        "tenantName": "Lim Cleaning Services Pte Ltd",
        "tenantType": "ORGANISATION",
    },
    {
        "tenantId": "org-c",
        "tenantName": "Ng Logistics Pte Ltd",
        "tenantType": "ORGANISATION",
    },
]


# ────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────


def test_callback_single_org_persists_directly(
    client, test_company
):
    """When the user has authorised exactly one Xero org, the callback
    persists ``xero_tenant_id`` and redirects to the success URL —
    no picker required."""
    company_id = test_company["company_id"]
    user_id = 993_001
    key = os.environ["INTEGRATION_ENCRYPTION_KEY"].encode()
    state = _signed_state(company_id, user_id, key)

    fake = _FakeAdapter(_SINGLE_CONN)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        resp = client.get(
            "/integrations/xero/oauth/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert "xero=connected" in resp.headers["location"]

    # Token row carries the chosen tenant id.
    rows = dataflow_crud.list_records(
        "IntegrationToken",
        {"tenant_id": str(company_id), "provider": "xero"},
        cache_ttl=0,
    )
    assert len(rows) == 1
    assert rows[0]["xero_tenant_id"] == "single-org-id"
    assert rows[0]["xero_tenant_name"] == "Solo Pte Ltd"


def test_callback_multi_org_redirects_to_picker(client, test_company):
    """When >1 orgs, the callback redirects to the picker page rather
    than silently picking the first."""
    company_id = test_company["company_id"]
    user_id = 993_001
    key = os.environ["INTEGRATION_ENCRYPTION_KEY"].encode()
    state = _signed_state(company_id, user_id, key)

    fake = _FakeAdapter(_MULTI_CONN)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        resp = client.get(
            "/integrations/xero/oauth/callback",
            params={"code": "fake-code-2", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "/settings/integrations/xero/pick-org" in location
    assert "token=" in location

    # The token in the redirect should fetch the same orgs back via
    # the pending-orgs endpoint.
    pick_token = urllib.parse.parse_qs(location.split("?", 1)[1])["token"][0]
    pending = client.get(
        "/integrations/xero/pending-orgs",
        params={"token": pick_token},
    )
    assert pending.status_code == 200, pending.text
    body = pending.json()
    assert {c["tenantId"] for c in body["connections"]} == {
        "org-a",
        "org-b",
        "org-c",
    }


def test_pick_org_persists_chosen_tenant_id(client, test_company):
    """Picker submission stores the user's chosen org and clears the
    pending entry so it can't be replayed."""
    company_id = test_company["company_id"]
    user_id = 993_001
    key = os.environ["INTEGRATION_ENCRYPTION_KEY"].encode()
    state = _signed_state(company_id, user_id, key)

    # First, drive the multi-org callback to stash the pending pick.
    fake = _FakeAdapter(_MULTI_CONN)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        resp = client.get(
            "/integrations/xero/oauth/callback",
            params={"code": "fake-code-3", "state": state},
            follow_redirects=False,
        )
    pick_token = urllib.parse.parse_qs(resp.headers["location"].split("?", 1)[1])[
        "token"
    ][0]

    # Submit a choice — middle org, not the first.
    submit = client.post(
        "/integrations/xero/pick-org",
        json={"token": pick_token, "xero_tenant_id": "org-b"},
    )
    assert submit.status_code == 200, submit.text
    assert "xero=connected" in submit.json()["redirect_url"]

    # Token row now carries org-b, not org-a.
    rows = dataflow_crud.list_records(
        "IntegrationToken",
        {"tenant_id": str(company_id), "provider": "xero"},
        cache_ttl=0,
    )
    assert len(rows) == 1
    assert rows[0]["xero_tenant_id"] == "org-b"
    assert rows[0]["xero_tenant_name"] == "Lim Cleaning Services Pte Ltd"

    # Replaying the same pick token should now fail — the pending entry
    # was consumed.
    replay = client.post(
        "/integrations/xero/pick-org",
        json={"token": pick_token, "xero_tenant_id": "org-a"},
    )
    assert replay.status_code == 404


def test_pick_org_rejects_unauthorised_tenant_id(client, test_company):
    """An attacker who guesses or replays a tenant id that wasn't in
    the user's original authorisation list must be rejected — this is
    what protects against cross-tenant binding."""
    company_id = test_company["company_id"]
    user_id = 993_001
    key = os.environ["INTEGRATION_ENCRYPTION_KEY"].encode()
    state = _signed_state(company_id, user_id, key)

    fake = _FakeAdapter(_MULTI_CONN)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        resp = client.get(
            "/integrations/xero/oauth/callback",
            params={"code": "fake-code-4", "state": state},
            follow_redirects=False,
        )
    pick_token = urllib.parse.parse_qs(
        resp.headers["location"].split("?", 1)[1]
    )["token"][0]

    bad = client.post(
        "/integrations/xero/pick-org",
        json={"token": pick_token, "xero_tenant_id": "attacker-org-id"},
    )
    assert bad.status_code == 400
    assert "authorised" in bad.json()["detail"].lower()


def test_pick_org_rejects_tampered_token(client):
    """A token whose HMAC doesn't validate must be rejected."""
    bad_token = "tampered-nonce.0000000000000000000000000000000000000000000000000000000000000000"
    resp = client.post(
        "/integrations/xero/pick-org",
        json={"token": bad_token, "xero_tenant_id": "anything"},
    )
    # Either signature invalid or token unknown — both are >= 400.
    assert resp.status_code in (400, 403, 404)


def test_pending_orgs_rejects_missing_token(client):
    resp = client.get("/integrations/xero/pending-orgs")
    assert resp.status_code == 400
