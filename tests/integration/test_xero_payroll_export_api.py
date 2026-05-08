"""Integration tests for the Xero payroll-journal export endpoints.

Hits the live FastAPI app via TestClient with a fresh test company and
patched ``XeroAdapter`` (we don't hit real Xero in CI). Covers:

- GET /payroll/xero/status — connected/mapping flags
- GET /payroll/xero/account-mapping — saved vs auto_match vs empty
- PUT /payroll/xero/account-mapping — upsert
- POST /payroll/runs/{id}/export-xero — happy path, status guards,
  duplicate guard, force re-export, mapping-incomplete guard,
  not-connected guard

Docker must be running: docker compose -f docker-compose.dev.yml up -d
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any
from unittest.mock import patch

import jwt as pyjwt
import pytest
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")
os.environ.setdefault("DATAFLOW_POOL_SIZE", "5")
os.environ.setdefault("DATAFLOW_POOL_MAX_OVERFLOW", "2")

from hr_advisory.config.settings import Settings, get_settings

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
get_settings.cache_clear()

from hr_advisory.api.platform import create_platform
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8099,
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
            "name": f"XeroExportTest {suffix}",
            "uen": f"X{suffix.upper()[:9]}",
            "sector": "Technology",
        },
    )
    company_id = company["id"]

    yield {"company_id": company_id, "suffix": suffix}

    # Best-effort cleanup. Order matters: child rows before parent.
    for model in ("XeroAccountMapping", "PayrollRun"):
        rows = dataflow_crud.list_records(model, {"company_id": company_id}, cache_ttl=0)
        for row in rows:
            try:
                dataflow_crud.delete(model, row["id"])
            except Exception:
                pass
    try:
        dataflow_crud.delete("Company", company_id)
    except Exception:
        pass


def _make_token(
    settings: Settings, user_id: int, role: str, company_id: int
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": f"u{user_id}@xero-test.com",
        "role": role,
        "iat": now,
        "exp": now + 3600,
        "company_id": company_id,
    }
    return pyjwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


@pytest.fixture
def owner_token(settings, test_company) -> str:
    return _make_token(
        settings, user_id=991_001, role="owner",
        company_id=test_company["company_id"],
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def approved_payroll_run(test_company):
    """A balanced, approved PayrollRun ready for export."""
    company_id = test_company["company_id"]
    run = dataflow_crud.create(
        "PayrollRun",
        {
            "company_id": company_id,
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "pay_date": "2026-05-01",
            "status": "approved",
            "payroll_type": "monthly",
            "total_gross": 10000.0,
            "total_net": 8000.0,
            "total_employer_cpf": 1700.0,
            "total_employee_cpf": 2000.0,
            "total_sdl": 25.0,
            "total_fwl": 0.0,
            "total_shg": 0.0,
            "employee_count": 5,
            "created_by": 991_001,
            "approved_by": 991_001,
            "approved_at": "2026-05-01T00:00:00Z",
        },
    )
    yield run
    try:
        dataflow_crud.delete("PayrollRun", run["id"])
    except Exception:
        pass


_FAKE_XERO_CHART = [
    {"Code": "477", "Name": "Wages and Salaries", "Type": "EXPENSE"},
    {"Code": "480", "Name": "Bonus Expense", "Type": "EXPENSE"},
    {"Code": "481", "Name": "CPF - Employer", "Type": "EXPENSE"},
    {"Code": "482", "Name": "SDL Expense", "Type": "EXPENSE"},
    {"Code": "825", "Name": "CPF Payable", "Type": "CURRLIAB"},
    {"Code": "814", "Name": "Net Wages Payable", "Type": "CURRLIAB"},
]


def _full_mapping_payload() -> dict:
    return {
        "salary_expense_code": "477",
        "bonus_expense_code": "480",
        "employer_cpf_expense_code": "481",
        "sdl_expense_code": "482",
        "cpf_payable_code": "825",
        "net_pay_payable_code": "814",
    }


class _FakeXeroAdapter:
    """Stand-in for XeroAdapter — record calls, return canned data."""

    def __init__(self, connected: bool = True):
        self._connected = connected
        self.posted_journals: list[dict[str, Any]] = []
        self.voided_journal_ids: list[str] = []
        self.idempotency_keys: list[str] = []

    def is_connected(self, tenant_id: str) -> bool:
        return self._connected

    async def get_chart_of_accounts(self, tenant_id: str):
        return list(_FAKE_XERO_CHART)

    async def post_payroll_journal(
        self,
        tenant_id: str,
        journal_data: dict,
        xero_tenant_id=None,
        idempotency_key=None,
    ) -> dict:
        self.posted_journals.append(journal_data)
        self.idempotency_keys.append(idempotency_key or "")
        return {
            "journal_id": f"fake-mj-{len(self.posted_journals)}",
            "status": "POSTED",
            "narration": journal_data.get("narration", ""),
            "date": journal_data.get("date", ""),
            "line_count": len(journal_data.get("lines", [])),
            "provider": "xero",
        }

    async def void_journal(
        self, tenant_id: str, journal_id: str, xero_tenant_id=None
    ) -> dict:
        self.voided_journal_ids.append(journal_id)
        return {"journal_id": journal_id, "status": "VOIDED", "provider": "xero"}


@pytest.fixture
def fake_xero():
    """Patch get_xero_adapter to return a fake. Returns the fake instance."""
    fake = _FakeXeroAdapter(connected=True)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        yield fake


# ────────────────────────────────────────────────────────────────────
# /payroll/xero/status
# ────────────────────────────────────────────────────────────────────


def test_status_when_disconnected(client, owner_token):
    fake = _FakeXeroAdapter(connected=False)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        resp = client.get("/payroll/xero/status", headers=_auth(owner_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False


def test_status_when_connected_no_mapping(client, owner_token, fake_xero):
    resp = client.get("/payroll/xero/status", headers=_auth(owner_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["mapping_present"] is False
    assert body["mapping_complete"] is False


# ────────────────────────────────────────────────────────────────────
# /payroll/xero/account-mapping (GET + PUT)
# ────────────────────────────────────────────────────────────────────


def test_get_mapping_returns_auto_match_when_no_saved_mapping(
    client, owner_token, fake_xero
):
    resp = client.get(
        "/payroll/xero/account-mapping", headers=_auth(owner_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "auto_match"
    assert body["mapping"]["salary_expense_code"] == "477"
    assert body["complete"] is True


def test_put_mapping_upserts_and_get_returns_saved(
    client, owner_token, fake_xero
):
    payload = _full_mapping_payload()
    put_resp = client.put(
        "/payroll/xero/account-mapping",
        headers=_auth(owner_token),
        json={"mapping": payload},
    )
    assert put_resp.status_code == 200, put_resp.text
    assert put_resp.json()["complete"] is True

    get_resp = client.get(
        "/payroll/xero/account-mapping", headers=_auth(owner_token)
    )
    body = get_resp.json()
    assert body["source"] == "saved"
    assert body["mapping"] == payload


def test_put_mapping_then_status_reports_complete(
    client, owner_token, fake_xero
):
    client.put(
        "/payroll/xero/account-mapping",
        headers=_auth(owner_token),
        json={"mapping": _full_mapping_payload()},
    )
    resp = client.get("/payroll/xero/status", headers=_auth(owner_token))
    body = resp.json()
    assert body["mapping_present"] is True
    assert body["mapping_complete"] is True


# ────────────────────────────────────────────────────────────────────
# /payroll/runs/{id}/export-xero
# ────────────────────────────────────────────────────────────────────


def test_export_requires_mapping(
    client, owner_token, approved_payroll_run, test_company
):
    # Make sure no mapping exists for this company
    rows = dataflow_crud.list_records(
        "XeroAccountMapping",
        {"company_id": test_company["company_id"]},
        cache_ttl=0,
    )
    for row in rows:
        dataflow_crud.delete("XeroAccountMapping", row["id"])

    fake = _FakeXeroAdapter(connected=True)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        resp = client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={},
        )
    assert resp.status_code == 409
    assert "mapping" in resp.json()["detail"].lower()


def test_export_requires_xero_connected(
    client, owner_token, approved_payroll_run
):
    # Save mapping first so the only failure is "not connected"
    fake_connected = _FakeXeroAdapter(connected=True)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake_connected,
    ):
        client.put(
            "/payroll/xero/account-mapping",
            headers=_auth(owner_token),
            json={"mapping": _full_mapping_payload()},
        )

    fake_disconnected = _FakeXeroAdapter(connected=False)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake_disconnected,
    ):
        resp = client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={},
        )
    assert resp.status_code == 409
    assert "not connected" in resp.json()["detail"].lower()


def test_export_rejects_draft_run(client, owner_token, test_company, fake_xero):
    # Create a DRAFT run — should be rejected
    draft = dataflow_crud.create(
        "PayrollRun",
        {
            "company_id": test_company["company_id"],
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "pay_date": "2026-04-01",
            "status": "draft",
            "payroll_type": "monthly",
            "total_gross": 5000.0,
            "total_net": 4000.0,
            "total_employer_cpf": 850.0,
            "total_employee_cpf": 1000.0,
            "total_sdl": 12.5,
            "total_fwl": 0.0,
            "total_shg": 0.0,
        },
    )
    try:
        resp = client.post(
            f"/payroll/runs/{draft['id']}/export-xero",
            headers=_auth(owner_token),
            json={},
        )
        assert resp.status_code == 400
        assert "approved or paid" in resp.json()["detail"].lower()
    finally:
        dataflow_crud.delete("PayrollRun", draft["id"])


def test_export_happy_path_posts_and_stamps_run(
    client, owner_token, approved_payroll_run
):
    # Save mapping first
    fake = _FakeXeroAdapter(connected=True)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        client.put(
            "/payroll/xero/account-mapping",
            headers=_auth(owner_token),
            json={"mapping": _full_mapping_payload()},
        )

        resp = client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={"bonus_total": 1000.0},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["journal_id"].startswith("fake-mj-")
    assert body["line_count"] == 6
    assert body["exported_at"]

    # Adapter received a balanced journal
    assert len(fake.posted_journals) == 1
    posted = fake.posted_journals[0]
    total = round(sum(line["amount"] for line in posted["lines"]), 2)
    assert total == 0.0

    # PayrollRun was stamped with journal id + timestamp
    refreshed = dataflow_crud.read("PayrollRun", approved_payroll_run["id"])
    assert refreshed["xero_journal_id"] == body["journal_id"]
    assert refreshed["xero_exported_at"]


def test_export_blocks_duplicate_without_force(
    client, owner_token, approved_payroll_run
):
    fake = _FakeXeroAdapter(connected=True)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        client.put(
            "/payroll/xero/account-mapping",
            headers=_auth(owner_token),
            json={"mapping": _full_mapping_payload()},
        )

        first = client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={},
        )
        assert first.status_code == 200

        dup = client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={},
        )

    assert dup.status_code == 409
    assert "already exported" in dup.json()["detail"].lower()
    # Adapter only saw one POST
    assert len(fake.posted_journals) == 1


def test_export_force_overrides_duplicate_guard(
    client, owner_token, approved_payroll_run
):
    fake = _FakeXeroAdapter(connected=True)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        client.put(
            "/payroll/xero/account-mapping",
            headers=_auth(owner_token),
            json={"mapping": _full_mapping_payload()},
        )

        first = client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={},
        )
        first_journal_id = first.json()["journal_id"]
        forced = client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={"force": True},
        )

    assert forced.status_code == 200
    # Both forced and original POST hit Xero
    assert len(fake.posted_journals) == 2
    # Force-re-export voids the prior journal so the customer's books
    # don't end up with two posted journals for the same payroll run.
    assert fake.voided_journal_ids == [first_journal_id]
    # Idempotency keys advance with the force counter so retries dedupe
    # but a forced re-export is genuinely new.
    assert fake.idempotency_keys[0].endswith(":0")
    assert fake.idempotency_keys[1].endswith(":1")


def test_export_writes_audit_log_row_on_success(
    client, owner_token, approved_payroll_run, test_company
):
    """XeroExportLog row written for every successful export."""
    fake = _FakeXeroAdapter(connected=True)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        client.put(
            "/payroll/xero/account-mapping",
            headers=_auth(owner_token),
            json={"mapping": _full_mapping_payload()},
        )
        client.post(
            f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
            headers=_auth(owner_token),
            json={"bonus_total": 250.0},
        )

    rows = dataflow_crud.list_records(
        "XeroExportLog",
        {
            "company_id": test_company["company_id"],
            "payroll_run_id": approved_payroll_run["id"],
        },
        cache_ttl=0,
    )
    assert len(rows) >= 1
    posted_rows = [r for r in rows if r.get("status") == "POSTED"]
    assert posted_rows, f"no POSTED row in {rows}"
    log = posted_rows[-1]
    assert log["journal_id"].startswith("fake-mj-")
    assert log["payload_hash"]
    assert log["bonus_total"] == 250.0
    assert log["forced_reexport"] is False
