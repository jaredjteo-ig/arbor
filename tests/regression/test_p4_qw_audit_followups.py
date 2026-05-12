"""P4-QW regression tests — audit follow-up quick wins.

Source audits:
- workspaces/obayashi/04-validate/07-buyer-audit-2026-05-08.md
- workspaces/obayashi/04-validate/08-functional-audit-2026-05-12.md
- workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md

Each test pins one P4-QW finding so it can't regress.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADMIN_GUARD = REPO_ROOT / "apps" / "web" / "src" / "components" / "auth" / "AdminGuard.tsx"
PAYROLL_DETAIL_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "payroll"
    / "[id]"
    / "page.tsx"
)
MY_PAYSLIPS_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "my-payslips"
    / "page.tsx"
)
API_CLIENT = REPO_ROOT / "apps" / "web" / "src" / "services" / "api" / "client.ts"
MY_LEAVE_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "my-leave"
    / "page.tsx"
)
MY_PROFILE_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "my-profile"
    / "page.tsx"
)
MY_DASHBOARD_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "my-dashboard"
    / "page.tsx"
)
CTC_CALC = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "calculators"
    / "elements"
    / "CostToCompanyCalculator.tsx"
)
RESULT_ROW = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "calculators"
    / "elements"
    / "ResultRow.tsx"
)
SEED_SCRIPT = REPO_ROOT / "scripts" / "seed_demo_data.py"


# ---------------------------------------------------------------------------
# P4-QW-1 — Employees who hit an admin page must be redirected, not shown
# a red "Access Denied" panel.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_1_admin_guard_redirects_employees_silently():
    """AdminGuard must redirect employees to /my-dashboard, not show a
    red Access Denied panel.

    The audit (09-redteam-roles P1-B) found that Marcus (employee role)
    hitting /dashboard saw a red "Access Denied — restricted to
    administrators" page. That's the wrong UX — employees navigating to
    a stale URL / bookmark should be silently routed home, not scolded
    with a security warning.
    """
    assert ADMIN_GUARD.exists(), "AdminGuard.tsx file moved or deleted"
    src = ADMIN_GUARD.read_text()

    # The redirect target — silent navigation to the employee's own home.
    assert 'router.replace("/my-dashboard")' in src, (
        "AdminGuard must call router.replace('/my-dashboard') when an "
        "employee hits an admin page (silent redirect, no history pollution)."
    )

    # The old, user-hostile UX must be gone.
    assert "Access Denied" not in src, (
        "AdminGuard must no longer render an 'Access Denied' panel — "
        "employees should be silently redirected away from admin URLs."
    )
    assert "restricted to administrators" not in src, (
        "AdminGuard must no longer surface 'restricted to administrators' "
        "copy. Employees see no error — they're redirected."
    )

    # Must still render nothing while role state is resolving — so admin
    # content doesn't flash before the redirect kicks in.
    assert (
        'user.role === "employee"' in src
    ), "AdminGuard must still check user.role === 'employee' to gate render"


# ---------------------------------------------------------------------------
# P4-QW-9 — Payslip PDF download must be reachable from the UI for both
# the admin run-detail page and the employee self-serve /my-payslips page.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_9_admin_payroll_detail_has_pdf_button():
    """The admin payroll run-detail page must wire a Download PDF button
    in the expanded payslip row.

    Audit 08-functional-audit P1-2: backend endpoint
    POST /payroll/runs/{run_id}/payslips/{payslip_id}/pdf exists but
    no UI button was wired. HR couldn't distribute payslips to
    employees without falling back to manual screenshotting.
    """
    assert PAYROLL_DETAIL_PAGE.exists(), "payroll/[id]/page.tsx moved"
    src = PAYROLL_DETAIL_PAGE.read_text()

    assert "downloadPayslipPdf" in src, (
        "Admin payroll run-detail page must call "
        "payrollApi.downloadPayslipPdf(runId, payslipId) — the existing "
        "API-client method that hits the existing backend endpoint."
    )
    assert "Download payslip PDF" in src, (
        "Admin payroll run-detail page must surface a visible "
        "'Download payslip PDF' button label in the expanded row."
    )


@pytest.mark.regression
def test_p4_qw_9_employee_my_payslips_has_pdf_button():
    """Employees must be able to self-serve their own payslip PDF from
    /my-payslips. (This was already wired pre-audit; the test pins it
    so it can't regress.)"""
    assert MY_PAYSLIPS_PAGE.exists(), "my-payslips/page.tsx moved"
    src = MY_PAYSLIPS_PAGE.read_text()

    assert "downloadMyPayslipPdf" in src, (
        "Employee /my-payslips page must call "
        "payrollApi.downloadMyPayslipPdf(payslipId) for self-serve PDF."
    )


# ---------------------------------------------------------------------------
# P4-QW-2 — Friendly error handling for invalid payroll run IDs.
# The API client must NOT JSON.stringify raw Pydantic validation arrays
# onto the page, and the run-detail page must guard against NaN run IDs
# from a route like /payroll/runs.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_2_api_client_does_not_leak_pydantic_array_to_ui():
    """Pydantic validation errors arrive as `detail: [...]` arrays.
    The API client must render a human-readable summary, not
    `JSON.stringify(body.detail)` onto the screen.

    Bug from 08-functional-audit P1-1: navigating to /payroll/runs
    rendered:
        [{"type":"int_parsing","loc":["path","run_id"],
          "msg":"Input should be a valid integer, unable to parse
          string as an integer","input":"NaN"}]
    """
    src = API_CLIENT.read_text()

    assert "JSON.stringify(body.detail)" not in src, (
        "API client must not render raw Pydantic validation arrays via "
        "JSON.stringify — produce a friendly summary instead."
    )
    assert "Array.isArray(body.detail)" in src, (
        "API client must explicitly handle the array shape of "
        "FastAPI/Pydantic validation errors (detail: [...] )"
    )
    assert "Invalid request" in src, (
        "API client must surface 'Invalid request' as the fallback "
        "user-facing message for validation errors, not raw JSON."
    )


# ---------------------------------------------------------------------------
# P4-QW-3 — Annual leave entitlement must scale by years of service per
# EA Schedule 4. The /employees/me/leave fallback path was hardcoding 7.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_3_ea_schedule_4_scaling_helper():
    """`_ea_annual_leave_days` must implement EA Schedule 4:
    7 days year 1, +1 each subsequent year, capped at 14 from year 8.
    """
    from hr_advisory.api.routers.employees import _ea_annual_leave_days

    # year 2026, employee started Jan of various years
    cases = [
        # (start_date, expected_days_in_2026)
        ("2026-01-01", 7),  # 0 completed years -> 7
        ("2025-01-01", 7),  # 1 completed year  -> 7 (still "year 1")
        ("2024-01-01", 8),  # 2 completed years -> 8
        ("2023-01-01", 9),  # 3 completed years -> 9
        ("2022-01-10", 10),  # 4 completed years -> 10 (Rajesh's actual case)
        ("2021-01-01", 11),  # 5 completed years -> 11
        ("2020-01-01", 12),  # 6 completed years -> 12
        ("2019-01-01", 13),  # 7 completed years -> 13
        ("2018-01-01", 14),  # 8 completed years -> 14 (cap)
        ("2010-01-01", 14),  # 16 completed years -> 14 (still capped)
    ]
    for start, expected in cases:
        actual = _ea_annual_leave_days(start, 2026)
        assert actual == expected, (
            f"EA Schedule 4: employee starting {start} should have {expected} "
            f"days annual in 2026, got {actual}"
        )


@pytest.mark.regression
def test_p4_qw_3_statutory_defaults_scales_when_employee_provided():
    """`_statutory_defaults(employee)` must scale annual leave by service.

    Audit 09-redteam-roles P2-B: Rajesh (joined 2022-01-10, 4+ years
    in 2026) was seeing 7 annual days because the fallback path
    didn't pass employee info into the default builder.
    """
    from hr_advisory.api.routers.employees import _statutory_defaults

    # Rajesh-like profile
    rajesh_like = {"start_date": "2022-01-10"}
    balances = _statutory_defaults(rajesh_like)
    annual = next(b for b in balances if b["leave_type"] == "annual")
    assert annual["entitlement_days"] >= 10.0, (
        "Annual leave for a 4+ year veteran must be ≥ 10 days under EA "
        "Schedule 4. The previous hardcoded fallback returned 7 — "
        f"now returned {annual['entitlement_days']}."
    )
    # Sick + hospitalisation stay flat
    sick = next(b for b in balances if b["leave_type"] == "sick")
    assert sick["entitlement_days"] == 14.0
    hosp = next(b for b in balances if b["leave_type"] == "hospitalization")
    assert hosp["entitlement_days"] == 60.0


@pytest.mark.regression
def test_p4_qw_3_statutory_defaults_no_employee_returns_minimum():
    """When no employee context is provided, fallback returns the
    EA minimum (7 days annual) — preserves prior behaviour for
    admin-viewing-own and pre-employee paths."""
    from hr_advisory.api.routers.employees import _statutory_defaults

    balances = _statutory_defaults()
    annual = next(b for b in balances if b["leave_type"] == "annual")
    assert annual["entitlement_days"] == 7.0, (
        "No-employee fallback must still return the 7-day EA minimum"
    )


# ---------------------------------------------------------------------------
# P4-QW-4 — Hospitalisation leave must not appear additive to sick leave.
# SG rule: 60 days inclusive of the 14 outpatient days.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_4_my_leave_hospitalisation_inclusive_disclaimer():
    """Hospitalisation Leave card on /my-leave must include the
    'inclusive of the 14 outpatient sick days' disclaimer so the
    employee cannot misread 14 + 60 = 74 medical days.
    """
    assert MY_LEAVE_PAGE.exists(), "my-leave/page.tsx moved"
    src = MY_LEAVE_PAGE.read_text()

    assert "Inclusive of the 14 outpatient sick days" in src, (
        "Hospitalisation Leave card on /my-leave must render the "
        "SG-EA-accurate disclaimer that the 60 days are INCLUSIVE of "
        "the 14 outpatient sick days. Without it, employees + HR "
        "miscalculate protected entitlement (audit 09-redteam P2-C)."
    )


# ---------------------------------------------------------------------------
# P4-QW-5 — NRIC mask must display the server-masked value verbatim
# (preserves leading citizenship-band character).
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_5_my_profile_uses_server_masked_nric():
    """My Profile must render `profile.nric_fin` as-is (the server's
    correct 9-char SG mask), not reconstruct `****{last4}` which
    drops the leading citizenship-band letter and produces 8 chars.
    """
    src = MY_PROFILE_PAGE.read_text()

    # Must NOT reconstruct from last4 (the old buggy approach).
    assert "`****${profile.nric_fin_last4}`" not in src, (
        "My Profile must not rebuild `****{last4}` — use the server-"
        "masked nric_fin verbatim. The reconstructed value drops the "
        "leading citizenship-band char and produces a malformed NRIC."
    )


# ---------------------------------------------------------------------------
# P4-QW-6 — Stale empty-template onboarding cards must not render.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_6_dashboard_hides_empty_onboarding():
    """My Dashboard must skip the onboarding card when the template
    has zero steps (legacy assignments to long-tenured employees)."""
    src = MY_DASHBOARD_PAGE.read_text()

    assert "totalSteps === 0" in src, (
        "My Dashboard OnboardingProgressCard must return null when "
        "totalSteps is 0 (audit P4-QW-6). Otherwise legacy employees "
        "see a confusing '0 of 0 steps completed' card."
    )


# ---------------------------------------------------------------------------
# P4-QW-7 — Demo seed must produce ≥1 work-pass expiring within 90 days.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_7_seed_uses_relative_work_pass_expiry():
    """Demo seed must compute work_pass_expiry from date.today()
    rather than hardcoding dates that drift past expiry as time
    passes. Otherwise the 'Work Pass Expiring Soon' filter looks
    broken in demos.
    """
    src = SEED_SCRIPT.read_text()

    assert "date.today() + timedelta(days=45)" in src, (
        "At least one foreign worker must have work_pass_expiry = "
        "today+45 so the filter always has a near-term entry."
    )
    assert "date.today() + timedelta(days=75)" in src, (
        "A second foreign worker should expire later (today+75) so "
        "the filter shows a graduated set in demos."
    )


# ---------------------------------------------------------------------------
# P4-QW-8 — WICA $0 in Cost-to-Company must have a tooltip explaining
# the $2,600 / manual-worker threshold.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_8_wica_row_has_threshold_tooltip():
    """The WICA row in Cost-to-Company must expose a tooltip that
    explains why $0 can be correct, so buyers in construction
    (manual workforce) don't read it as a gap."""
    src = CTC_CALC.read_text()

    assert "tooltip=" in src and "WICA" in src, (
        "WICA row must pass a tooltip prop (audit P4-QW-8)."
    )
    assert "$2,600" in src or "≤$2,600" in src or "2,600" in src, (
        "WICA tooltip must mention the $2,600 monthly threshold "
        "that defines mandatory coverage."
    )


@pytest.mark.regression
def test_p4_qw_8_result_row_accepts_tooltip_prop():
    """The shared ResultRow primitive must accept a `tooltip` prop
    so every calculator row can disambiguate a legitimate $0."""
    src = RESULT_ROW.read_text()

    assert "tooltip" in src, (
        "ResultRow must accept a tooltip prop for disambiguating "
        "$0 entries across the 7 SG HR calculators."
    )


# ---------------------------------------------------------------------------
# P4-QW-2 (continued) — Pydantic validation array must not surface raw
# on the payroll detail page.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_qw_2_payroll_detail_page_guards_invalid_run_id():
    """Hitting /payroll/runs lands on /payroll/[id] with id='runs', which
    makes Number(id) = NaN. The page must detect this before fetching
    and render a friendly 'Payroll run not found' panel.
    """
    src = PAYROLL_DETAIL_PAGE.read_text()

    assert "Number.isFinite(runId)" in src, (
        "Payroll run-detail page must validate runId is finite before "
        "calling the API. Number(id) returns NaN when id is non-numeric "
        "(e.g. when someone navigates to /payroll/runs by mistake)."
    )
    assert "Payroll run not found" in src, (
        "Payroll run-detail page must render a friendly "
        "'Payroll run not found' panel for invalid runIds, not the raw "
        "API error or a generic crash."
    )
