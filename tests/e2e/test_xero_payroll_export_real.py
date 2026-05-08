"""Tier-3 e2e test that posts a real ManualJournal to Xero.

Skipped unless ``XERO_E2E_*`` env vars are populated by running
``scripts/xero_oauth_setup.py`` first. Targets Xero's Demo Company
(sandbox), which auto-resets every 28 days, so we don't bother
voiding the journal afterward.

What this verifies that the mocked integration tests cannot:
- The OAuth token actually authenticates against api.xero.com.
- ``XeroAdapter.get_chart_of_accounts`` returns the
  ``{Code, Name, Type, Status}`` shape our auto-matcher expects.
- A balanced ManualJournal payload is accepted by Xero (status,
  date format, account codes, line amounts all valid).
- ``post_payroll_journal`` returns a real ``ManualJournalID``.
- The PayrollRun row gets stamped with that id end-to-end through
  the FastAPI endpoint.

Run::

    XERO_E2E_TENANT_ID=... XERO_E2E_ACCESS_TOKEN=... \\
    XERO_E2E_REFRESH_TOKEN=... \\
    pytest tests/e2e/test_xero_payroll_export_real.py -v
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Optional

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

from hr_advisory.api.platform import create_platform
from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter
from hr_advisory.mcp_servers.auth.token_store import get_token_manager
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)


_REQUIRED_ENV = (
    "XERO_E2E_TENANT_ID",
    "XERO_E2E_ACCESS_TOKEN",
    "XERO_E2E_REFRESH_TOKEN",
    "XERO_CLIENT_ID",
    "XERO_CLIENT_SECRET",
)


def _e2e_creds_present() -> bool:
    return all(os.environ.get(var, "").strip() for var in _REQUIRED_ENV)


pytestmark = pytest.mark.skipif(
    not _e2e_creds_present(),
    reason=(
        "Xero e2e credentials missing. Run scripts/xero_oauth_setup.py "
        "and add XERO_E2E_TENANT_ID/ACCESS_TOKEN/REFRESH_TOKEN to .env "
        "(plus XERO_CLIENT_ID/SECRET for token refresh)."
    ),
)


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────


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


@pytest.fixture(scope="module")
def test_company():
    suffix = uuid.uuid4().hex[:8]
    company = dataflow_crud.create(
        "Company",
        {
            "name": f"XeroE2E {suffix}",
            "uen": f"E{suffix.upper()[:9]}",
            "sector": "Technology",
        },
    )
    company_id = company["id"]

    yield {"company_id": company_id, "suffix": suffix}

    for model in ("XeroAccountMapping", "PayrollRun"):
        rows = dataflow_crud.list_records(
            model, {"company_id": company_id}, cache_ttl=0
        )
        for row in rows:
            try:
                dataflow_crud.delete(model, row["id"])
            except Exception:
                pass
    try:
        dataflow_crud.delete("Company", company_id)
    except Exception:
        pass


@pytest.fixture(scope="module", autouse=True)
def bootstrap_xero_token(test_company):
    """Inject the captured Xero tokens into the in-memory token store.

    The token store keys by ``(tenant_id, provider)``; we use the local
    Arbor company_id as tenant_id so XeroAdapter.is_connected() returns
    True for our test company.
    """
    company_id = str(test_company["company_id"])
    manager = get_token_manager()
    manager.store_token(
        company_id,
        "xero",
        {
            "access_token": os.environ["XERO_E2E_ACCESS_TOKEN"],
            "refresh_token": os.environ["XERO_E2E_REFRESH_TOKEN"],
            "expires_in": 1800,  # 30 minutes; refresh kicks in if stale
            "scope": "accounting.transactions accounting.settings.read",
        },
    )
    yield


@pytest.fixture(scope="module")
def owner_token(settings, test_company) -> str:
    now = int(time.time())
    payload = {
        "sub": "991_777",
        "email": "owner@xero-e2e.test",
        "role": "owner",
        "iat": now,
        "exp": now + 3600,
        "company_id": test_company["company_id"],
    }
    return pyjwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


@pytest.fixture
def approved_payroll_run(test_company):
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
            "total_gross": 5000.0,
            "total_net": 4000.0,
            "total_employer_cpf": 850.0,
            "total_employee_cpf": 1000.0,
            "total_sdl": 12.5,
            "total_fwl": 0.0,
            "total_shg": 0.0,
            "employee_count": 1,
            "created_by": 991_777,
            "approved_by": 991_777,
            "approved_at": "2026-05-01T00:00:00Z",
        },
    )
    yield run
    try:
        dataflow_crud.delete("PayrollRun", run["id"])
    except Exception:
        pass


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────


def test_status_reports_connected_against_real_xero(client, owner_token):
    resp = client.get("/payroll/xero/status", headers=_auth(owner_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True, (
        "is_connected() should be True after token bootstrap."
    )


def test_chart_of_accounts_returns_real_xero_shape(client, owner_token):
    resp = client.get(
        "/payroll/xero/chart-of-accounts", headers=_auth(owner_token)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    accounts = body["accounts"]
    assert len(accounts) > 0, "Xero Demo Company should have accounts."

    # The auto-matcher relies on Code, Name, Type. Confirm at least one
    # account has the canonical shape.
    sample = accounts[0]
    assert "Code" in sample and "Name" in sample, (
        f"Unexpected Xero account shape: {sample}"
    )


def _select_codes_for_e2e(accounts: list[dict]) -> dict[str, str]:
    """Pick six real Xero account codes for the e2e mapping.

    Strategy: find any expense and any current-liability account in the
    Demo Company and reuse them across buckets. Xero accepts the same
    code on multiple lines as long as the journal balances, which is
    what we want for a sandbox smoke test.
    """
    expense = next(
        (a for a in accounts if a.get("Type") in ("EXPENSE", "OVERHEADS", "DIRECTCOSTS")
         and a.get("Status", "ACTIVE") == "ACTIVE"
         and not a.get("SystemAccount")),
        None,
    )
    liability = next(
        (a for a in accounts if a.get("Type") in ("CURRLIAB", "LIABILITY")
         and a.get("Status", "ACTIVE") == "ACTIVE"
         and not a.get("SystemAccount")),
        None,
    )
    assert expense and liability, (
        f"Demo Company missing expense/liability accounts. Got: "
        f"{[(a.get('Code'), a.get('Type')) for a in accounts[:8]]}"
    )

    return {
        "salary_expense_code": expense["Code"],
        "bonus_expense_code": expense["Code"],
        "employer_cpf_expense_code": expense["Code"],
        "sdl_expense_code": expense["Code"],
        "cpf_payable_code": liability["Code"],
        "net_pay_payable_code": liability["Code"],
    }


def test_full_export_round_trip_against_real_xero(
    client, owner_token, approved_payroll_run
):
    # 1. Fetch real chart of accounts
    chart_resp = client.get(
        "/payroll/xero/chart-of-accounts", headers=_auth(owner_token)
    )
    assert chart_resp.status_code == 200
    accounts = chart_resp.json()["accounts"]

    # 2. Pick valid codes from the Demo Company
    mapping = _select_codes_for_e2e(accounts)

    # 3. Save mapping
    put_resp = client.put(
        "/payroll/xero/account-mapping",
        headers=_auth(owner_token),
        json={"mapping": mapping},
    )
    assert put_resp.status_code == 200, put_resp.text
    assert put_resp.json()["complete"] is True

    # 4. Export the run — this hits api.xero.com/api.xro/2.0/ManualJournals
    export_resp = client.post(
        f"/payroll/runs/{approved_payroll_run['id']}/export-xero",
        headers=_auth(owner_token),
        json={},
    )
    assert export_resp.status_code == 200, export_resp.text
    body = export_resp.json()

    # 5. Verify Xero accepted the journal and returned a real id
    journal_id: Optional[str] = body.get("journal_id")
    assert journal_id, f"Xero did not return a journal id: {body}"
    # Xero ManualJournalIDs are GUIDs.
    assert len(journal_id) >= 30, (
        f"journal_id doesn't look like a Xero GUID: {journal_id!r}"
    )
    assert body["status"] in ("POSTED", "DRAFT"), body
    assert body["line_count"] >= 2

    # 6. The PayrollRun row was stamped end-to-end
    refreshed = dataflow_crud.read("PayrollRun", approved_payroll_run["id"])
    assert refreshed["xero_journal_id"] == journal_id
    assert refreshed["xero_exported_at"]

    logger.info(
        "Successfully posted real Xero ManualJournal: id=%s, lines=%d",
        journal_id,
        body["line_count"],
    )
