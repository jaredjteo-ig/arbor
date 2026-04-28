"""Cluster 3 regression tests: B12 (N+1 fix), B13 (pagination).

B15 (responsive breakpoints) is a UX assertion that needs browser tooling —
covered by /redteam Playwright runs, not unit tests.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.regression
def test_b12_bulk_find_users_is_single_query() -> None:
    """B12: `_bulk_find_users` must NOT do one DB read per user_id.

    The original bug: `_bulk_find_users` looped over user_ids and called
    `dataflow_crud.read("User", uid)` per user — 200 employees = 200 queries.
    The fix: one `list_records("User", {"company_id": ...})` call, then
    in-memory dict lookup.

    This test patches `list_records` and asserts it's called at most once
    for a batch of N user_ids.
    """
    from hr_advisory.api.routers import employees as employees_router

    bulk_find = employees_router._bulk_find_users
    user_ids = [10, 20, 30, 40, 50]
    fake_users = [
        {"id": 10, "name": "A", "email": "a@x"},
        {"id": 20, "name": "B", "email": "b@x"},
        {"id": 99, "name": "Z", "email": "z@x"},  # extra row, must be filtered out
    ]

    with patch.object(
        employees_router.dataflow_crud, "list_records", return_value=fake_users
    ) as mock_list, patch.object(
        employees_router.dataflow_crud, "read"
    ) as mock_read:
        result = bulk_find(user_ids, company_id=1)

    assert mock_list.call_count == 1, (
        "B12 regression: _bulk_find_users must call list_records exactly once "
        f"(got {mock_list.call_count})"
    )
    assert mock_read.call_count == 0, (
        "B12 regression: _bulk_find_users must not call dataflow_crud.read at all "
        f"(got {mock_read.call_count} read calls — that is the N+1 pattern)"
    )
    assert set(result.keys()) == {10, 20}, (
        "Result must only contain users whose ids are in the requested batch"
    )


@pytest.mark.regression
@pytest.mark.parametrize(
    "module_name,function_name",
    [
        ("hr_advisory.api.routers.employees", "list_employees"),
        ("hr_advisory.api.routers.leave", "list_applications"),
        ("hr_advisory.api.routers.payroll", "list_payroll_runs"),
    ],
)
def test_b13_priority_endpoints_declare_pagination(module_name: str, function_name: str) -> None:
    """B13: priority list endpoints must accept page/page_size and return total.

    Inspects the function signature for `page` and `page_size` parameters
    and the source for `total` and `pages` keys in the response dict.
    """
    import importlib

    module = importlib.import_module(module_name)
    func = getattr(module, function_name)
    sig = inspect.signature(func)
    params = sig.parameters

    assert "page" in params, f"{function_name} must accept a `page` query parameter"
    assert "page_size" in params, f"{function_name} must accept a `page_size` query parameter"

    source = inspect.getsource(func)
    assert '"total"' in source, (
        f"{function_name} response must include 'total' (count of all matching records)"
    )
    assert '"pages"' in source, (
        f"{function_name} response must include 'pages' (count of pages)"
    )


@pytest.mark.regression
def test_b15_approvals_tabs_have_overflow_handling() -> None:
    """B15: the approvals tab strip must not overflow horizontally on mobile.

    Pin the fix: the `<div>` wrapping the TABS.map should have
    `overflow-x-auto` so the tabs scroll on narrow screens instead of
    pushing the layout wider than the viewport.
    """
    page = REPO_ROOT / "apps/web/src/app/(dashboard)/approvals/page.tsx"
    text = page.read_text(encoding="utf-8")
    # The tab container line should mention overflow-x-auto.
    assert "border-b border-[var(--color-gray-200)] overflow-x-auto" in text, (
        "approvals tabs are missing overflow-x-auto — they will push past 375px on mobile"
    )
