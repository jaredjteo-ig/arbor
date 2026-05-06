"""Round-2 redteam regression tests.

Pins the fixes for findings raised in
`workspaces/obayashi/04-validate/02-redteam-findings-round2.md`.

  H1 — goals scope filter on get/patch/checkin (not just list)
  M2 — block self-recognition + self-nomination
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOALS_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "goals.py"
RECO_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "recognition.py"
)


def _function_body(path: Path, name: str) -> ast.AST:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"Function {name!r} not found in {path}")


@pytest.mark.regression
def test_h1_goals_scope_helper_exists():
    """`_verify_goal_in_scope` helper must exist and enforce scope."""
    src = GOALS_ROUTER.read_text()
    assert "_verify_goal_in_scope" in src, (
        "Goals scope helper missing — H1 redteam regression."
    )


@pytest.mark.regression
@pytest.mark.parametrize(
    "handler",
    ["get_goal", "update_goal", "list_checkins", "add_checkin"],
)
def test_h1_goals_handlers_use_scope_check(handler: str):
    """Every per-goal handler must call _verify_goal_in_scope, NOT
    _verify_goal directly. Calling _verify_goal alone allows any
    employee to read/write any goal in their company by ID guess."""
    fn = _function_body(GOALS_ROUTER, handler)
    body_src = ast.unparse(fn)
    assert "_verify_goal_in_scope" in body_src, (
        f"{handler} no longer enforces scope — H1 regression. "
        f"Use _verify_goal_in_scope, not _verify_goal."
    )


@pytest.mark.regression
def test_m2_self_recognition_blocked():
    """give_recognition must reject when the recipient is the giver."""
    fn = _function_body(RECO_ROUTER, "give_recognition")
    body_src = ast.unparse(fn)
    assert (
        'target[0].get("user_id") == user_id' in body_src
        or "target[0].get('user_id') == user_id" in body_src
    ), (
        "Self-recognition guard removed — M2 regression. Users could "
        "spam the kudos feed with self-pats."
    )


@pytest.mark.regression
def test_m2_self_nomination_blocked():
    """nominate must reject when the nominee is the nominator."""
    fn = _function_body(RECO_ROUTER, "nominate")
    body_src = ast.unparse(fn)
    assert (
        'target[0].get("user_id") == user_id' in body_src
        or "target[0].get('user_id') == user_id" in body_src
    ), (
        "Self-nomination guard removed — M2 regression. Tally rankings "
        "would be gameable."
    )
