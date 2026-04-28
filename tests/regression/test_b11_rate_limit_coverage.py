"""B11 regression: every router write endpoint must have rate limiting.

The original finding (round 11, M-8) was that 13 routers had write endpoints
(POST/PATCH/PUT/DELETE) with no `check_rate_limit` call, leaving them open
to abuse. This test pins the coverage so a new endpoint can't slip through
without a rate limit.

Mechanism: parse each router file with the AST, find every function decorated
with @router.{post,put,patch,delete}, and assert at least one rate-limit call
appears in the function body. Webhooks are exempted because they use
`_check_webhook_rate` (IP-based) instead of the user-tied `check_rate_limit`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTERS_DIR = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers"

# Routers covered by the B11 brief. (`reports.py` is read-only — no writes.
# `clients.py` was retired in the single-tenant collapse.)
COVERED_ROUTERS = {
    "claims",
    "appraisals",
    "shifts",
    "projects",
    "banking",
    "alerts",
    "calculator",
    "compliance",
    "admin",
    "integrations",
    "kb",
}

WRITE_DECORATORS = {"post", "put", "patch", "delete"}

# Endpoints exempted from the user-tied check_rate_limit pattern:
# - inbound webhooks: rate-limited by client IP via _check_webhook_rate.
EXEMPTIONS = {
    ("integrations", "receive_webhook"),
}

# Helper-rate-limit callables (any of these counts as protected).
RATE_LIMIT_CALLEES = {"check_rate_limit", "_check_webhook_rate", "_check_auth_rate_limit"}


def _is_router_write_decorator(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if not isinstance(func.value, ast.Name):
        return False
    return func.value.id == "router" and func.attr in WRITE_DECORATORS


def _function_calls_rate_limit(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name) and callee.id in RATE_LIMIT_CALLEES:
                return True
            if isinstance(callee, ast.Attribute) and callee.attr in RATE_LIMIT_CALLEES:
                return True
    return False


def _collect_unprotected(router_name: str) -> list[str]:
    path = ROUTERS_DIR / f"{router_name}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if (router_name, node.name) in EXEMPTIONS:
            continue
        has_write_decorator = any(_is_router_write_decorator(d) for d in node.decorator_list)
        if not has_write_decorator:
            continue
        if not _function_calls_rate_limit(node):
            offenders.append(f"{router_name}.{node.name}:line{node.lineno}")
    return offenders


@pytest.mark.regression
@pytest.mark.parametrize("router_name", sorted(COVERED_ROUTERS))
def test_b11_router_write_endpoints_have_rate_limit(router_name: str) -> None:
    """Each write endpoint in the covered routers must call a rate-limit helper."""
    unprotected = _collect_unprotected(router_name)
    assert not unprotected, (
        f"{router_name}.py has unprotected write endpoints: {unprotected}. "
        "Every @router.{post,put,patch,delete} handler must call "
        f"one of {sorted(RATE_LIMIT_CALLEES)}."
    )


@pytest.mark.regression
def test_b11_reports_router_has_no_writes() -> None:
    """reports.py was excluded from B11 because it is read-only.

    Pin that assumption: if anyone adds a POST/PATCH/DELETE to reports.py,
    this test trips and they must add it to COVERED_ROUTERS above.
    """
    path = ROUTERS_DIR / "reports.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    writes: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(_is_router_write_decorator(d) for d in node.decorator_list):
                writes.append(f"{node.name}:line{node.lineno}")
    assert not writes, (
        "reports.py now has write endpoints — add 'reports' to COVERED_ROUTERS "
        f"in this test and rate-limit those writes: {writes}"
    )
