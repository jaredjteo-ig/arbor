"""Regression: M0-T02 — concurrent Xero export must not produce duplicates.

Two clicks within milliseconds on the same payroll run previously
raced on the read-then-write of ``xero_force_counter``: both reads
saw counter=0, both writes set counter=1 at counter=0 idempotency-key,
both POSTs fired at Xero. Depending on whether Xero's
Idempotency-Key dedupe arrived first, the customer's books could
end up with two posted journals.

Fix: Postgres advisory lock around the export body. Concurrent
attempt on the same run gets ``pg_try_advisory_lock = false`` and
surfaces as 409.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
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

from hr_advisory.api.platform import create_platform
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8094,
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
            "name": f"XeroConcurrentTest {suffix}",
            "uen": f"C{suffix.upper()[:9]}",
            "sector": "Technology",
        },
    )
    company_id = company["id"]
    yield {"company_id": company_id, "suffix": suffix}

    for model in ("XeroAccountMapping", "PayrollRun", "XeroExportLog"):
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


@pytest.fixture
def owner_token(settings, test_company) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": "994_001",
            "email": "owner@concurrent-test.com",
            "role": "owner",
            "iat": now,
            "exp": now + 3600,
            "company_id": test_company["company_id"],
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@pytest.fixture
def approved_run(test_company):
    run = dataflow_crud.create(
        "PayrollRun",
        {
            "company_id": test_company["company_id"],
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
            "approved_by": 994_001,
        },
    )
    yield run
    try:
        dataflow_crud.delete("PayrollRun", run["id"])
    except Exception:
        pass


_CHART = [
    {"Code": "477", "Name": "Wages and Salaries", "Type": "EXPENSE"},
    {"Code": "480", "Name": "Bonus Expense", "Type": "EXPENSE"},
    {"Code": "481", "Name": "CPF - Employer", "Type": "EXPENSE"},
    {"Code": "482", "Name": "SDL Expense", "Type": "EXPENSE"},
    {"Code": "825", "Name": "CPF Payable", "Type": "CURRLIAB"},
    {"Code": "814", "Name": "Net Wages Payable", "Type": "CURRLIAB"},
]


_MAPPING = {
    "salary_expense_code": "477",
    "bonus_expense_code": "480",
    "employer_cpf_expense_code": "481",
    "sdl_expense_code": "482",
    "cpf_payable_code": "825",
    "net_pay_payable_code": "814",
}


class _SlowFakeAdapter:
    """Fake Xero adapter that sleeps in post_payroll_journal so we can
    arrange a real overlap between two concurrent requests."""

    def __init__(self, post_delay: float = 0.5):
        self._connected = True
        self._post_delay = post_delay
        self.posted_journals: list[dict[str, Any]] = []
        self.lock = asyncio.Lock()

    def is_connected(self, tenant_id: str) -> bool:
        return self._connected

    async def get_chart_of_accounts(self, tenant_id: str):
        return list(_CHART)

    async def post_payroll_journal(
        self,
        tenant_id: str,
        journal_data: dict,
        xero_tenant_id=None,
        idempotency_key=None,
    ):
        # Hold long enough that two concurrent requests genuinely
        # overlap inside the export body.
        await asyncio.sleep(self._post_delay)
        async with self.lock:
            self.posted_journals.append(
                {
                    "journal_data": journal_data,
                    "idempotency_key": idempotency_key,
                }
            )
            n = len(self.posted_journals)
        return {
            "journal_id": f"fake-mj-{n}",
            "status": "POSTED",
            "narration": journal_data.get("narration", ""),
            "date": journal_data.get("date", ""),
            "line_count": len(journal_data.get("lines", [])),
            "provider": "xero",
        }

    async def void_journal(self, tenant_id, journal_id, xero_tenant_id=None):
        return {"journal_id": journal_id, "status": "VOIDED", "provider": "xero"}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.regression
def test_concurrent_export_attempts_serialize_to_one_post(
    client, owner_token, approved_run, test_company
):
    """Two simultaneous POSTs to /payroll/runs/{id}/export-xero must
    result in exactly ONE journal at Xero. The losing call returns
    409 (advisory lock not acquired) without retrying.
    """
    fake = _SlowFakeAdapter(post_delay=0.4)
    with patch(
        "hr_advisory.mcp_servers.adapters.xero.get_xero_adapter",
        return_value=fake,
    ):
        # Save mapping
        client.put(
            "/payroll/xero/account-mapping",
            headers=_auth(owner_token),
            json={"mapping": _MAPPING},
        )

        # Fire two concurrent POSTs. TestClient is sync so we use
        # threads — the underlying app handles them concurrently.
        import concurrent.futures

        def _post():
            return client.post(
                f"/payroll/runs/{approved_run['id']}/export-xero",
                headers=_auth(owner_token),
                json={},
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_post)
            f2 = pool.submit(_post)
            r1 = f1.result(timeout=10)
            r2 = f2.result(timeout=10)

    statuses = sorted([r1.status_code, r2.status_code])
    # Exactly one success + exactly one conflict
    assert statuses == [200, 409], (
        f"expected one 200 + one 409, got {statuses}: "
        f"{r1.text!r} | {r2.text!r}"
    )
    # Adapter only saw one POST attempt — the loser bailed before
    # talking to Xero.
    assert len(fake.posted_journals) == 1

    # The audit log has exactly one POSTED row.
    rows = dataflow_crud.list_records(
        "XeroExportLog",
        {
            "company_id": test_company["company_id"],
            "payroll_run_id": approved_run["id"],
        },
        cache_ttl=0,
    )
    posted = [r for r in rows if r.get("status") == "POSTED"]
    assert len(posted) == 1, (
        f"expected exactly one POSTED audit row, got {len(posted)}: {rows}"
    )
