"""B3 regression: claim total_amount must be the SUM of items, not the last item.

Origin: round-12 redteam (workspaces/obayashi/04-validate/01-redteam-findings.md).

The bug: `_recalculate_claim_total` called `dataflow_crud.list_records`
without `cache_ttl=0`, so the list cache returned a stale view that
missed just-inserted items. After multiple item adds the resulting
`total_amount` matched the most recent item rather than the sum.

The fix: pass `cache_ttl=0` so the recalculation always reads the
authoritative DB state. This test pins the contract at the source code
level so the cache flag can't be removed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAIMS_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "claims.py"
)


@pytest.mark.regression
def test_b3_recalc_bypasses_list_cache():
    """`_recalculate_claim_total` must call list_records with cache_ttl=0."""
    tree = ast.parse(CLAIMS_ROUTER.read_text())

    target = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "_recalculate_claim_total"
        ):
            target = node
            break
    assert target is not None, "_recalculate_claim_total not found"

    list_calls = [
        c
        for c in ast.walk(target)
        if isinstance(c, ast.Call)
        and isinstance(c.func, ast.Attribute)
        and c.func.attr == "list_records"
    ]
    assert list_calls, "_recalculate_claim_total no longer calls list_records"

    cache_kwargs = []
    for call in list_calls:
        for kw in call.keywords:
            if kw.arg == "cache_ttl":
                cache_kwargs.append(kw)

    assert cache_kwargs, (
        "list_records call inside _recalculate_claim_total is missing "
        "cache_ttl=0; without it the recalc reads a stale list cache and "
        "total_amount drifts to the last-inserted item only."
    )
    for kw in cache_kwargs:
        assert (
            isinstance(kw.value, ast.Constant) and kw.value.value == 0
        ), "cache_ttl must be exactly 0 to bypass the cache"
