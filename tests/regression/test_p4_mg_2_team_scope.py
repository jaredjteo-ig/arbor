"""P4-MG-2 regression tests — team-scoped approval endpoints.

The leave/claims/timesheets endpoints must widen scope when the
caller is a line-manager (has direct reports). Approve / reject
endpoints must reject cross-team actions with a 403.

Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
finding P1-A.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAVE_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "leave.py"
)


# ---------------------------------------------------------------------------
# Source-level pins — endpoint contract stays right.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg2_leave_router_imports_manager_scope():
    """leave.py must use the manager_scope helper rather than
    re-implementing the reporting_manager_id query."""
    src = LEAVE_ROUTER.read_text()
    assert "from hr_advisory.services import dataflow_crud, manager_scope" in src or (
        "import manager_scope" in src and "manager_scope" in src
    ), "leave.py must import manager_scope for team-scope derivation."


@pytest.mark.regression
def test_mg2_list_applications_widens_for_managers():
    """list_applications must call manager_scope.get_managed_employee_ids
    so a manager's GET returns their team plus self."""
    src = LEAVE_ROUTER.read_text()
    tree = ast.parse(src)
    target = None
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
            and node.name == "list_applications"
        ):
            target = node
            break
    assert target is not None, "list_applications handler missing"
    body = ast.get_source_segment(src, target) or ""
    assert "manager_scope.get_managed_employee_ids" in body, (
        "list_applications must derive team scope from "
        "manager_scope.get_managed_employee_ids."
    )


@pytest.mark.regression
def test_mg2_approve_no_longer_requires_role():
    """approve_application must NOT use require_role('owner','hr_manager')
    — a line manager who is just an `employee` role must be able to
    approve their direct report's leave. The role gate moves into
    the body via `_authorize_review`."""
    src = LEAVE_ROUTER.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
            and node.name in {"approve_application", "reject_application"}
        ):
            func_src = ast.get_source_segment(src, node) or ""
            assert "require_role" not in func_src, (
                f"{node.name} must NOT use require_role — gating moves "
                "into _authorize_review so line managers (employee role "
                "with direct reports) can approve their team's leave."
            )
            assert "_authorize_review" in func_src, (
                f"{node.name} must call _authorize_review for the new "
                "owner/HR/line-manager combined scope."
            )


# ---------------------------------------------------------------------------
# Behavioural tests — _authorize_review guard, exercised directly.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_authorize_review_allows_owner():
    """Owner role passes through with no scope check."""
    from hr_advisory.api.routers.leave import _authorize_review

    current_user = {"sub": "1", "role": "owner", "company_id": 1}
    app = {"id": 100, "employee_id": 99, "company_id": 1}
    with patch(
        "hr_advisory.api.routers.leave._get_employee_for_user",
        return_value=None,  # owner has no Employee row
    ):
        _authorize_review(current_user, app)  # must not raise


@pytest.mark.regression
def test_authorize_review_allows_hr_manager():
    from hr_advisory.api.routers.leave import _authorize_review

    current_user = {"sub": "25", "role": "hr_manager", "company_id": 1}
    app = {"id": 100, "employee_id": 10, "company_id": 1}
    with patch(
        "hr_advisory.api.routers.leave._get_employee_for_user",
        return_value=None,
    ):
        _authorize_review(current_user, app)  # must not raise


@pytest.mark.regression
def test_authorize_review_allows_line_manager_for_their_report():
    """Rajesh (line manager) approves Marcus's leave — must pass."""
    from hr_advisory.api.routers.leave import _authorize_review

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}
    marcus_leave = {"id": 100, "employee_id": 10, "company_id": 1}

    with patch(
        "hr_advisory.api.routers.leave._get_employee_for_user",
        return_value={"id": 3, "user_id": 4},  # Rajesh's Employee row
    ), patch(
        "hr_advisory.services.manager_scope.is_manager_of",
        return_value=True,  # Rajesh manages Marcus
    ):
        _authorize_review(rajesh, marcus_leave)  # must not raise


@pytest.mark.regression
def test_authorize_review_rejects_cross_team_manager():
    """Rajesh (line manager) tries to approve someone NOT on his team
    — must 403 with the team-scope error message."""
    from hr_advisory.api.routers.leave import _authorize_review

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}
    not_my_report_leave = {"id": 200, "employee_id": 99, "company_id": 1}

    with patch(
        "hr_advisory.api.routers.leave._get_employee_for_user",
        return_value={"id": 3, "user_id": 4},
    ), patch(
        "hr_advisory.services.manager_scope.is_manager_of",
        return_value=False,  # Not Rajesh's report
    ):
        with pytest.raises(HTTPException) as exc:
            _authorize_review(rajesh, not_my_report_leave)
    assert exc.value.status_code == 403
    assert "not the manager" in exc.value.detail.lower()


@pytest.mark.regression
def test_authorize_review_rejects_plain_employee():
    """Marcus (no reports) tries to approve someone's leave — 403.
    Pure-IC path: not owner, not HR, not a manager of anyone."""
    from hr_advisory.api.routers.leave import _authorize_review

    marcus = {"sub": "11", "role": "employee", "company_id": 1}
    target = {"id": 50, "employee_id": 6, "company_id": 1}

    with patch(
        "hr_advisory.api.routers.leave._get_employee_for_user",
        return_value={"id": 10, "user_id": 11},
    ), patch(
        "hr_advisory.services.manager_scope.is_manager_of",
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            _authorize_review(marcus, target)
    assert exc.value.status_code == 403


@pytest.mark.regression
def test_authorize_review_blocks_self_approval_even_for_owner():
    """Self-approval is a separation-of-duties violation. Even an
    owner cannot approve their own leave — they must route through
    a co-owner / HR person. SG audit expectation.
    """
    from hr_advisory.api.routers.leave import _authorize_review

    owner = {"sub": "1", "role": "owner", "company_id": 1}
    # Owner's own leave application (their employee_id matches)
    own_app = {"id": 100, "employee_id": 99, "company_id": 1}

    with patch(
        "hr_advisory.api.routers.leave._get_employee_for_user",
        return_value={"id": 99, "user_id": 1},  # owner IS this employee
    ):
        with pytest.raises(HTTPException) as exc:
            _authorize_review(owner, own_app)
    assert exc.value.status_code == 403
    assert "your own" in exc.value.detail.lower()


@pytest.mark.regression
def test_authorize_review_blocks_self_approval_for_line_manager():
    """A line manager who somehow submitted a leave application
    cannot then self-approve it. Self-approval guard fires before
    the manager scope check.
    """
    from hr_advisory.api.routers.leave import _authorize_review

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}
    own_app = {"id": 100, "employee_id": 3, "company_id": 1}

    with patch(
        "hr_advisory.api.routers.leave._get_employee_for_user",
        return_value={"id": 3, "user_id": 4},  # Rajesh IS employee 3
    ):
        with pytest.raises(HTTPException) as exc:
            _authorize_review(rajesh, own_app)
    assert exc.value.status_code == 403
    assert "your own" in exc.value.detail.lower()
