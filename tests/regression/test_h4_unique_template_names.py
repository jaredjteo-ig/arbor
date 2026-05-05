"""H4 regression: onboarding template names must be unique per company.

Origin: round-12 redteam (workspaces/obayashi/04-validate/01-redteam-findings.md).

The bug: prod had three active templates named "HR Technology / SaaS
Onboarding" in one company. The create/update/duplicate endpoints had
no uniqueness check, so admins ended up with ambiguous picks at hire
time. The fix added `_ensure_unique_template_name` and called it from
all three write paths.

These tests pin the contract at the source-code level so the helper
can't be dropped silently from any of the write paths.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ONBOARDING_ROUTER = (
    REPO_ROOT
    / "src"
    / "hr_advisory"
    / "api"
    / "routers"
    / "onboarding.py"
)


def _function_body(name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(ONBOARDING_ROUTER.read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"Function {name!r} not found in onboarding.py")


def _calls_named(node: ast.AST, fn_name: str) -> list[ast.Call]:
    return [
        c
        for c in ast.walk(node)
        if isinstance(c, ast.Call)
        and (
            (isinstance(c.func, ast.Name) and c.func.id == fn_name)
            or (
                isinstance(c.func, ast.Attribute)
                and c.func.attr == fn_name
            )
        )
    ]


@pytest.mark.regression
def test_h4_create_template_enforces_unique_name():
    """`create_template` must call `_ensure_unique_template_name`."""
    fn = _function_body("create_template")
    assert _calls_named(fn, "_ensure_unique_template_name"), (
        "create_template no longer enforces unique names — H4 regression."
    )


@pytest.mark.regression
def test_h4_update_template_enforces_unique_name():
    """`update_template` must call `_ensure_unique_template_name` when name changes."""
    fn = _function_body("update_template")
    assert _calls_named(fn, "_ensure_unique_template_name"), (
        "update_template no longer enforces unique names — H4 regression."
    )


@pytest.mark.regression
def test_h4_duplicate_template_enforces_unique_name():
    """`duplicate_template` must avoid name collisions on the new copy."""
    fn = _function_body("duplicate_template")
    direct = _calls_named(fn, "_ensure_unique_template_name")
    auto_suffix = _calls_named(fn, "_next_available_template_name")
    assert direct or auto_suffix, (
        "duplicate_template no longer dedupes copy names — H4 regression."
    )
