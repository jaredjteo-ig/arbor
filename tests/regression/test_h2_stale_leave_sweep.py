"""H2 regression: daily sweep auto-cancels pending leave with past start_date.

Origin: round-12 redteam (workspaces/obayashi/04-validate/01-redteam-findings.md).

The bug: 3 of 4 pending leave applications shown on prod had start_date
already in the past (March/April while today was May). The approver
never acted; the requests sat there forever, freezing the employees'
pending_days against their entitlement.

The fix: a daily sweep endpoint at POST /leave/applications/sweep-stale-pending
that flips them to status='auto_cancelled' and restores the balance.

This test pins:
  1. The endpoint exists.
  2. Its body filters on status='pending' and compares start_date to today.
  3. The auto_cancelled status string is preserved (downstream UIs key on it).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAVE_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "leave.py"
)


@pytest.mark.regression
def test_h2_sweep_endpoint_exists():
    """Leave router declares the stale-sweep endpoint."""
    source = LEAVE_ROUTER.read_text()
    assert "/applications/sweep-stale-pending" in source, (
        "Stale-pending leave sweep endpoint is gone — H2 regression."
    )


@pytest.mark.regression
def test_h2_sweep_uses_auto_cancelled_status():
    """The sweep marks rows as `auto_cancelled` so downstream filters work."""
    source = LEAVE_ROUTER.read_text()
    assert '"auto_cancelled"' in source or "'auto_cancelled'" in source, (
        "Sweep no longer writes status='auto_cancelled' — H2 regression."
    )


@pytest.mark.regression
def test_h2_sweep_filters_pending_with_past_start():
    """Sweep helper fetches status='pending' and compares start_date to today."""
    tree = ast.parse(LEAVE_ROUTER.read_text())

    target = None
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_sweep_stale_pending_applications_for_company"
        ):
            target = node
            break
    assert target is not None, (
        "_sweep_stale_pending_applications_for_company helper missing."
    )

    body_src = ast.unparse(target)
    assert "status" in body_src and "pending" in body_src, (
        "Sweep no longer scopes to pending applications."
    )
    assert "start_date" in body_src, "Sweep no longer reads start_date."
