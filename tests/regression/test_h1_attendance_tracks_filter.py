"""H1 regression: Attendance dashboard filters by Employee.tracks_attendance.

Origin: round-12 redteam (workspaces/obayashi/04-validate/01-redteam-findings.md).

The bug: every active employee appeared on the daily Attendance page,
including salaried desk staff who have no clock-in workflow. They all
showed as "Absent" — visible noise that made the page look broken.

The fix: a per-employee `tracks_attendance` flag (default false) plus
a filter inside `today_dashboard` so only opted-in employees appear.

This test pins the filter at the source-code level so the flag can't
be quietly removed from the Employee fetch.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ATTENDANCE_ROUTER = (
    REPO_ROOT
    / "src"
    / "hr_advisory" / "api" / "routers" / "attendance.py"
)
EMPLOYEE_MODEL = (
    REPO_ROOT
    / "src"
    / "hr_advisory" / "models" / "company_user.py"
)


@pytest.mark.regression
def test_h1_employee_model_has_tracks_attendance_field():
    """Employee dataclass must declare a `tracks_attendance` field."""
    source = EMPLOYEE_MODEL.read_text()
    assert "tracks_attendance" in source, (
        "Employee.tracks_attendance was removed — H1 regression."
    )


@pytest.mark.regression
def test_h1_today_dashboard_filters_by_tracks_attendance():
    """`today_dashboard` must filter the employee fetch on tracks_attendance."""
    tree = ast.parse(ATTENDANCE_ROUTER.read_text())

    target = None
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "today_dashboard"
        ):
            target = node
            break
    assert target is not None, "today_dashboard not found"

    # Find the list_records("Employee", {...}) call and inspect its dict.
    found = False
    for call in ast.walk(target):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "list_records"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value == "Employee"
        ):
            continue

        if len(call.args) < 2 or not isinstance(call.args[1], ast.Dict):
            continue

        keys = {
            k.value
            for k in call.args[1].keys
            if isinstance(k, ast.Constant)
        }
        if "tracks_attendance" in keys:
            found = True
            break

    assert found, (
        "today_dashboard no longer filters Employee by tracks_attendance — "
        "the salaried-desk-staff filter has regressed."
    )
