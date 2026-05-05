"""H3 regression: payroll cannot be paid out of chronological order.

Origin: round-12 redteam (workspaces/obayashi/04-validate/01-redteam-findings.md).

The bug: prod showed an April run as Paid while March was still Draft,
and the dashboard's "Next Pay Date" pointed at a March pay date that
had already passed. This is a sequencing bug — pay-out-of-order
breaks CPF/IR8A reconciliation and confuses the next-pay-date heuristic.

Two fixes:
  - Backend `mark_payroll_paid` now refuses to flip a run to paid
    when an earlier-period run is still draft/approved.
  - Frontend `nextPayDate` only considers drafts whose pay_date is
    today or later (not stale past-dated drafts).

This test pins the backend guard at the source level. The frontend
guard is covered by Playwright in /redteam.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYROLL_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "payroll.py"
)


@pytest.mark.regression
def test_h3_mark_paid_blocks_out_of_order_runs():
    """`mark_payroll_paid` must refuse to pay later when earlier is unpaid."""
    tree = ast.parse(PAYROLL_ROUTER.read_text())

    target = None
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "mark_payroll_paid"
        ):
            target = node
            break
    assert target is not None, "mark_payroll_paid not found"

    body_src = ast.unparse(target)
    # Confirm the chronological-ordering guard exists. We look for the
    # 409 status, the period_end comparison, and the earlier-pending
    # filter — together they describe the guard uniquely enough that an
    # accidental removal will fail this test.
    assert "409" in body_src, "Out-of-order guard no longer raises 409."
    assert "period_end" in body_src, (
        "Out-of-order guard no longer reads period_end."
    )
    assert (
        "draft" in body_src and "approved" in body_src
    ), "Out-of-order guard no longer scopes to draft/approved siblings."
