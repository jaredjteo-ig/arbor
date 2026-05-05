"""P2-GO + P2-EX regression: Goals + Exit Interview module presence."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOALS_ROUTER = REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "goals.py"
EXIT_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "exit_interviews.py"
)
MODELS_FILE = (
    REPO_ROOT / "src" / "hr_advisory" / "models" / "company_user.py"
)


@pytest.mark.regression
def test_p2_go_models_exist():
    src = MODELS_FILE.read_text()
    for cls in ("class Goal:", "class GoalCheckIn:"):
        assert cls in src, f"Missing P2-GO model: {cls}"


@pytest.mark.regression
def test_p2_ex_models_exist():
    src = MODELS_FILE.read_text()
    assert "class ExitInterview:" in src, "Missing P2-EX model: ExitInterview"


@pytest.mark.regression
def test_p2_go_status_state_machine():
    """The status state machine must enforce monotonic forward transitions."""
    src = GOALS_ROUTER.read_text()
    assert "VALID_STATUS_TRANSITIONS" in src, (
        "Goal status state machine table missing."
    )
    for status in ("draft", "active", "at_risk", "done", "cancelled"):
        assert f'"{status}"' in src, f"Status {status!r} no longer in goal router."


@pytest.mark.regression
def test_p2_go_progress_bounds():
    """progress_pct must be bounded 0..100."""
    src = GOALS_ROUTER.read_text()
    assert "pct < 0 or pct > 100" in src, (
        "progress_pct bounds removed — could allow negative or >100 progress."
    )


@pytest.mark.regression
def test_p2_ex_token_audience():
    """Exit interview tokens must be scoped to a unique audience."""
    src = EXIT_ROUTER.read_text()
    assert 'EXIT_TOKEN_AUD = "arbor.exit-interview"' in src, (
        "Exit token audience constant missing or renamed — could allow "
        "cross-feature token reuse."
    )


@pytest.mark.regression
def test_p2_ex_anonymous_redaction():
    """Admin GET must redact employee_id when is_anonymous=True."""
    tree = ast.parse(EXIT_ROUTER.read_text())
    fn = next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == "list_interviews"
        ),
        None,
    )
    assert fn is not None, "list_interviews handler missing."
    body_src = ast.unparse(fn)
    assert "is_anonymous" in body_src, (
        "list_interviews no longer redacts anonymous rows."
    )
    assert '"employee_id"] = 0' in body_src or "employee_id'] = 0" in body_src, (
        "list_interviews no longer zeroes employee_id on anonymous rows."
    )


@pytest.mark.regression
def test_p2_ex_theme_keyword_keys():
    """Theme derivation must cover the canonical bucket set."""
    src = EXIT_ROUTER.read_text()
    for theme in ("manager", "comp", "growth", "workload", "culture", "role"):
        assert f'"{theme}"' in src, f"Exit theme bucket {theme!r} dropped."
