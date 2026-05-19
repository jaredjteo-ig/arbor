"""Red-team P5-PL polish bundle.

Origin: workspaces/obayashi/todos/active/P5-PL-polish-bundle.md
(now completed). Findings O14 + O15 + M6 + M7 + O13.

Most of P5-PL is copy / label / UX state polish that doesn't merit
behavioural tests. The one item with real backend behaviour is P5-PL-3
(leave-type gender filter): GET /leave/types accepts a `for_employee_id`
param and filters out gender-restricted leave types whose
`applicable_gender` doesn't match the named employee's gender.

P5-PL-4 (Approved-state caption) also changes the API contract: GET
/payroll/my-payslips now accepts ?include_approved=true and surfaces a
`pending_approved` list of minimal stubs. Pinned here too.

Source-level pins guard the other items (brand strings, label text,
empty-state copy) so a future refactor can't silently undo them.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HELP = REPO_ROOT / "src" / "hr_advisory/api/routers/help.py"
ANALYTICS_PAGE = (
    REPO_ROOT
    / "apps/web/src/app/(dashboard)/analytics/page.tsx"
)
LEAVE_PAGE = REPO_ROOT / "apps/web/src/app/(dashboard)/my-leave/page.tsx"
PAYSLIPS_PAGE = (
    REPO_ROOT / "apps/web/src/app/(dashboard)/my-payslips/page.tsx"
)
ATTENDANCE_PAGE = (
    REPO_ROOT / "apps/web/src/app/(dashboard)/attendance/page.tsx"
)
LEAVE_ROUTER = REPO_ROOT / "src/hr_advisory/api/routers/leave.py"
PAYROLL_ROUTER = REPO_ROOT / "src/hr_advisory/api/routers/payroll.py"


# ---------------------------------------------------------------------------
# P5-PL-1 — Brand consistency (no user-facing "Arbor" left)
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_pl_1_help_router_uses_central_brand():
    src = HELP.read_text()
    # User-facing strings on the help router are the source of truth
    # for the "Get started with…" landing copy. They must use "Central".
    assert 'title="Get started with Central"' in src, (
        "help.py _GETTING_STARTED must use the Central brand."
    )
    assert "Central is your AI-powered HR compliance assistant" in src
    assert "Central is your everyday HR portal" in src
    # And must not regress to Arbor in user-facing copy.
    assert "Get started with Arbor" not in src
    assert "Arbor is your" not in src


# ---------------------------------------------------------------------------
# P5-PL-2 — Analytics "75% local + PR" label
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_pl_2_analytics_uses_local_plus_pr_label():
    src = ANALYTICS_PAGE.read_text()
    # The compound metric must spell out that the ratio is Local + PR.
    assert "% local + PR" in src, (
        "Analytics top tile must label the compound as 'local + PR' "
        "(the API field local_ratio = local + pr / total)."
    )
    # Hover tooltip explains the math (Local + PR of N).
    assert "subtextTooltip" in src
    assert "Local (" in src and "PR (" in src


# ---------------------------------------------------------------------------
# P5-PL-3 — Leave-type gender filter
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_pl_3_leave_types_endpoint_accepts_for_employee_id():
    """Source pin: list_leave_types signature has the for_employee_id
    param. The behavioural test below exercises the filter."""
    src = LEAVE_ROUTER.read_text()
    assert "for_employee_id: int | None = None" in src
    assert 'applicable_gender' in src
    assert 'emp.get("gender")' in src


@pytest.mark.regression
def test_p5_pl_3_filters_maternity_for_male_employee():
    """Marcus (male) must not see Maternity in the dropdown.
    Grace (female) must not see Paternity / NS Reservist.
    """
    import asyncio
    from hr_advisory.api.routers.leave import list_leave_types

    fake_types = [
        {"code": "annual", "applicable_gender": "", "is_active": True},
        {"code": "maternity", "applicable_gender": "female", "is_active": True},
        {"code": "paternity", "applicable_gender": "male", "is_active": True},
        {"code": "childcare", "applicable_gender": "", "is_active": True},
        {"code": "ns", "applicable_gender": "male", "is_active": True},
    ]

    def run(emp: dict) -> list[str]:
        with (
            patch(
                "hr_advisory.services.dataflow_crud.list_records",
                return_value=fake_types,
            ),
            patch("hr_advisory.services.dataflow_crud.read", return_value=emp),
        ):
            loop = asyncio.new_event_loop()
            try:
                r = loop.run_until_complete(
                    list_leave_types(
                        for_employee_id=emp["id"],
                        current_user={
                            "sub": "10",
                            "company_id": 1,
                            "role": "employee",
                        },
                    )
                )
            finally:
                loop.close()
        return [t["code"] for t in r["leave_types"]]

    marcus = run({"id": 9, "company_id": 1, "gender": "male"})
    grace = run({"id": 25, "company_id": 1, "gender": "female"})

    assert "maternity" not in marcus, (
        "Male employee must not see Maternity in the leave-type list."
    )
    assert "paternity" in marcus
    assert "ns" in marcus
    assert "annual" in marcus
    assert "childcare" in marcus  # universal — always shown

    assert "paternity" not in grace, (
        "Female employee must not see Paternity."
    )
    assert "ns" not in grace
    assert "maternity" in grace
    assert "annual" in grace


@pytest.mark.regression
def test_p5_pl_3_tenant_isolation_404_across_tenants():
    """If the named employee belongs to a different tenant, the endpoint
    MUST 404 — never reveal the employee's existence cross-tenant, and
    never leak the leave-type config to an unrelated tenant."""
    import asyncio
    from fastapi import HTTPException
    from hr_advisory.api.routers.leave import list_leave_types

    other_tenant_emp = {"id": 9, "company_id": 999, "gender": "male"}

    with (
        patch(
            "hr_advisory.services.dataflow_crud.list_records",
            return_value=[],
        ),
        patch(
            "hr_advisory.services.dataflow_crud.read",
            return_value=other_tenant_emp,
        ),
    ):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                list_leave_types(
                    for_employee_id=9,
                    current_user={
                        "sub": "10",
                        "company_id": 1,
                        "role": "owner",
                    },
                )
            )
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError(
                "Cross-tenant for_employee_id lookup must raise 404."
            )
        finally:
            loop.close()


@pytest.mark.regression
def test_p5_pl_3_frontend_passes_employee_id():
    """The /my-leave page must call leaveApi.listTypes(myEmpId) so the
    filter actually applies."""
    src = LEAVE_PAGE.read_text()
    # Pattern: const me = await employeesApi.me().catch(...); ...
    # leaveApi.listTypes(myEmpId)
    assert "leaveApi.listTypes(myEmpId)" in src, (
        "my-leave/page.tsx must pass the current employee id to "
        "leaveApi.listTypes so the backend can apply the gender filter."
    )


# ---------------------------------------------------------------------------
# P5-PL-4 — Approved-but-not-yet-Paid caption
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_pl_4_my_payslips_supports_include_approved():
    """Source pin: GET /my-payslips supports `?include_approved=true`
    and returns a `pending_approved` list of stubs."""
    src = PAYROLL_ROUTER.read_text()
    section_start = src.index("async def get_my_payslips")
    section_end = src.index("async def get_my_payslip_detail", section_start)
    section = src[section_start:section_end]
    assert "include_approved" in section
    assert "pending_approved" in section
    assert "expected_pay_date" in section
    # We must NOT leak the approved payslip body — only stubs.
    # Sanity-check: pending_approved entries don't carry gross / net / cpf.
    assert '"gross"' not in section or "approved" not in section.split('"gross"')[0]


@pytest.mark.regression
def test_p5_pl_4_my_payslips_frontend_renders_caption():
    src = PAYSLIPS_PAGE.read_text()
    assert "pending_approved" in src or "pendingApproved" in src
    assert "Approved" in src
    assert "expected pay date" in src.lower()


# ---------------------------------------------------------------------------
# P5-PL-5 — Attendance empty-state explainer
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_pl_5_attendance_has_stale_clockin_explainer():
    """The MonthlySummary card must render an explainer (not the
    misleading 0h 0m tile) when the only record is a stale clock-in
    with no completed days."""
    src = ATTENDANCE_PAGE.read_text()
    assert "isStaleSingleClockIn" in src
    assert "Last clock-in was" in src
    # The avg-hours tile must show "—" instead of 0h 0m when there are
    # no completed days, to avoid the "this employee never works" read.
    assert 'noCompletedDays ? "—"' in src
