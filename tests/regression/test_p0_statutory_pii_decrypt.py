"""P0 regressions from 2026-05-12 functional audit.

Three independent bugs discovered while walking the live site as an HR manager,
all of which would break the first real payroll cycle for a customer:

  P0-1. CPF e-Submit file shipped NRICs as Fernet ciphertext. mycpf.gov.sg
        would reject the upload. Root cause: `generate_cpf_esubmit` reads
        `emp.nric_fin` directly without decrypting.

  P0-2. Bank GIRO file shipped account numbers as Fernet ciphertext. Bank
        would reject the file. Same root cause in `generate_bank_giro`.

  P0-3. Admin run-detail endpoint returned payslips without a `payslip_id`
        alias, so the frontend issued `GET /payslips/undefined` on every
        expand. No payslip line items were reachable. The same bug had
        previously been fixed for `/my-payslips` (see comment in
        `get_my_payslips`) but the same fix was never applied to
        `get_payroll_run`.

  P0-4. Discovered during P0-1/2/3 deploy verification: DataFlow
        `express_sync.read("PayrollRun", id)` returns None for every
        PayrollRun row while `express_sync.list("PayrollRun", filter={"id": id})`
        returns the same row correctly. This blocks 19 payroll endpoints
        (every one that calls `dataflow_crud.read("PayrollRun", ...)`),
        including the CPF e-Submit + Bank GIRO POSTs fixed in P0-1/2.
        Defensive fix: `dataflow_crud.read` falls back to a filtered
        list when express_sync.read returns None.

Origin: workspaces/obayashi/04-validate/08-functional-audit-2026-05-12.md
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STATUTORY = REPO_ROOT / "src" / "hr_advisory" / "services" / "statutory_files.py"
PAYROLL_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "payroll.py"


# ---------------------------------------------------------------------------
# P0-1 + P0-2 — functional regression: ciphertext must not appear in output
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p0_1_cpf_esubmit_decrypts_nric():
    """CPF e-Submit must emit plaintext NRIC, not Fernet ciphertext."""
    from cryptography.fernet import Fernet

    # Ensure encryption is active for this test.
    key = Fernet.generate_key()
    os.environ["SALARY_ENCRYPTION_KEY"] = key.decode()

    # Bust the lru_cache so the fixture key is picked up.
    from hr_advisory.security import encryption as enc_mod

    enc_mod._get_fernet.cache_clear()

    plaintext_nric = "S1234567D"
    encrypted_nric = Fernet(key).encrypt(plaintext_nric.encode()).decode()
    assert encrypted_nric.startswith("gAAAAA"), "encrypted token should start with Fernet prefix"

    from hr_advisory.services.statutory_files import generate_cpf_esubmit

    csv_content = generate_cpf_esubmit(
        payroll_run={"period_start": "2026-04-01", "employer_cpf_account": "T12345678A"},
        payslips=[
            {
                "employee_id": 1,
                "cpf_ow_used": 5000.0,
                "cpf_aw_used": 0.0,
                "employer_cpf": 850.0,
                "employee_cpf": 1000.0,
            }
        ],
        employees=[
            {"id": 1, "nric_fin": encrypted_nric, "user_id": 1, "name": "Alice"}
        ],
    )

    assert plaintext_nric in csv_content, (
        "decrypted NRIC must appear in CPF e-Submit file"
    )
    assert "gAAAAA" not in csv_content, (
        "Fernet ciphertext must NOT leak into CPF e-Submit file"
    )


@pytest.mark.regression
def test_p0_2_bank_giro_decrypts_account_number():
    """Bank GIRO must emit plaintext account number, not Fernet ciphertext."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    os.environ["SALARY_ENCRYPTION_KEY"] = key.decode()

    from hr_advisory.security import encryption as enc_mod

    enc_mod._get_fernet.cache_clear()

    plaintext_account = "408-525800-8"
    encrypted_account = Fernet(key).encrypt(plaintext_account.encode()).decode()
    assert encrypted_account.startswith("gAAAAA")

    from hr_advisory.services.statutory_files import generate_bank_giro

    giro_content = generate_bank_giro(
        payroll_run={"pay_date": "2026-04-30", "id": 4, "company_id": 1},
        payslips=[{"employee_id": 1, "net_salary": 8391.00}],
        employees=[
            {
                "id": 1,
                "bank_code": "7339",
                "bank_account_number": encrypted_account,
                "user_id": 1,
                "name": "Alice",
            }
        ],
        bank_format="generic",
    )

    assert plaintext_account in giro_content, (
        "decrypted account number must appear in Bank GIRO file"
    )
    assert "gAAAAA" not in giro_content, (
        "Fernet ciphertext must NOT leak into Bank GIRO file"
    )


@pytest.mark.regression
def test_p0_2_bank_giro_dbs_format_decrypts_account_number():
    """DBS fixed-width GIRO must also emit plaintext, not ciphertext."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    os.environ["SALARY_ENCRYPTION_KEY"] = key.decode()

    from hr_advisory.security import encryption as enc_mod

    enc_mod._get_fernet.cache_clear()

    plaintext_account = "012345678"
    encrypted_account = Fernet(key).encrypt(plaintext_account.encode()).decode()

    from hr_advisory.services.statutory_files import generate_bank_giro

    giro_content = generate_bank_giro(
        payroll_run={"pay_date": "2026-04-30", "id": 4, "company_id": 1},
        payslips=[{"employee_id": 1, "net_salary": 1000.00}],
        employees=[
            {
                "id": 1,
                "bank_code": "7171",
                "bank_account_number": encrypted_account,
                "user_id": 1,
                "name": "Alice",
            }
        ],
        bank_format="dbs",
    )

    assert plaintext_account in giro_content, (
        "DBS GIRO must contain plaintext account number"
    )
    assert "gAAAAA" not in giro_content, (
        "Fernet ciphertext must NOT leak into DBS GIRO file"
    )


# ---------------------------------------------------------------------------
# P0-3 — source-level regression: admin run-detail must alias `payslip_id`
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p0_3_admin_run_detail_aliases_payslip_id():
    """Admin /payroll/runs/{id} must alias the primary key as `payslip_id`.

    The frontend reads `payslip.payslip_id` to build the detail URL
    `/payslips/{id}`. The DataFlow row exposes `id`, not `payslip_id`. Without
    the alias the frontend issues `GET /payslips/undefined` and every payslip
    expand shows "No payslip items available".
    """
    src = PAYROLL_ROUTER.read_text()
    tree = ast.parse(src)

    target_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_payroll_run":
            target_func = node
            break

    assert target_func is not None, "get_payroll_run handler missing"

    func_src = ast.get_source_segment(src, target_func) or ""
    assert '"payslip_id": ps.get("id")' in func_src, (
        "get_payroll_run must alias `payslip_id` so the frontend can "
        "navigate to /payslips/{id}. Without this alias, the React "
        "PayslipRow component calls /payslips/undefined."
    )


# ---------------------------------------------------------------------------
# P0-4 — dataflow_crud.read must fall back to list when express_sync.read fails
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p0_4_read_falls_back_to_list_when_express_read_returns_none():
    """`dataflow_crud.read` must retry via `express_sync.list` on None.

    DataFlow's express_sync.read returns None for some models (observed:
    PayrollRun in prod after a container rebuild). The list-with-id-filter
    operation returns the same row in the same shape. The fallback keeps
    the 19 `read("PayrollRun", ...)` call sites in `routers/payroll.py`
    functional regardless of which DataFlow node path is healthy.
    """
    from hr_advisory.services import dataflow_crud

    class FakeExpressSync:
        def __init__(self):
            self.read_calls = []
            self.list_calls = []

        def read(self, model, record_id):
            self.read_calls.append((model, record_id))
            return None  # simulate the prod failure

        def list(self, model, filter=None):
            self.list_calls.append((model, filter))
            if filter == {"id": 4}:
                return [{"id": 4, "company_id": 1, "status": "paid"}]
            return []

    class FakeDb:
        def __init__(self):
            self.express_sync = FakeExpressSync()

    fake_db = FakeDb()

    # Patch the lazy db loader to return our fake.
    original = dataflow_crud._get_db
    dataflow_crud._get_db = lambda: fake_db
    try:
        result = dataflow_crud.read("PayrollRun", 4)
    finally:
        dataflow_crud._get_db = original

    assert result is not None, "fallback must yield the row when read returns None"
    assert result["id"] == 4
    assert result["status"] == "paid"
    # Both paths exercised — read tried first, then the list fallback.
    assert len(fake_db.express_sync.read_calls) == 1
    assert fake_db.express_sync.list_calls == [("PayrollRun", {"id": 4})]


@pytest.mark.regression
def test_p0_4_read_returns_none_when_list_also_empty():
    """If both express_sync.read and the list fallback return nothing, read returns None."""
    from hr_advisory.services import dataflow_crud

    class FakeExpressSync:
        def read(self, model, record_id):
            return None

        def list(self, model, filter=None):
            return []

    class FakeDb:
        def __init__(self):
            self.express_sync = FakeExpressSync()

    original = dataflow_crud._get_db
    dataflow_crud._get_db = lambda: FakeDb()
    try:
        result = dataflow_crud.read("PayrollRun", 999)
    finally:
        dataflow_crud._get_db = original

    assert result is None
