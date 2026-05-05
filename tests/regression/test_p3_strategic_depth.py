"""P3 regression: strategic depth — workforce plan, skills, succession,
retention risk, pay equity.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "strategy.py"
)
MODELS_FILE = (
    REPO_ROOT / "src" / "hr_advisory" / "models" / "company_user.py"
)


@pytest.mark.regression
def test_p3_models_exist():
    src = MODELS_FILE.read_text()
    for cls in (
        "class WorkforcePlan:",
        "class SkillsInventoryEntry:",
        "class SuccessionPlan:",
    ):
        assert cls in src, f"Missing P3 model: {cls}"


@pytest.mark.regression
def test_p3_endpoints_present():
    src = STRATEGY_ROUTER.read_text()
    for marker in (
        '"/workforce-plan"',
        '"/skills"',
        '"/skills/coverage"',
        '"/succession"',
        '"/retention-risk"',
        '"/pay-equity"',
    ):
        assert marker in src, f"Missing P3 endpoint: {marker}"


@pytest.mark.regression
def test_p3_pay_equity_anonymity_threshold():
    """Pay-equity must collapse buckets with fewer than 5 employees."""
    src = STRATEGY_ROUTER.read_text()
    assert "len(vals) < 5" in src, (
        "Pay-equity anonymity threshold dropped — could re-identify "
        "individuals when buckets are sparse."
    )
    assert '"—"' in src, "Pay-equity collapse marker '—' removed."


@pytest.mark.regression
def test_p3_retention_not_persisted():
    """Retention-risk endpoint must not write to a persistent store.

    Per spec, the score is recomputed on every call (no PII drift).
    """
    tree = ast.parse(STRATEGY_ROUTER.read_text())
    fn = next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == "retention_risk"
        ),
        None,
    )
    assert fn is not None, "retention_risk handler missing."
    body = ast.unparse(fn)
    forbidden = (
        "dataflow_crud.create",
        "dataflow_crud.update",
        "dataflow_crud.delete",
    )
    for f in forbidden:
        assert f not in body, (
            f"retention_risk now persists via {f} — violates the "
            "no-persistence rule for the derived view."
        )


@pytest.mark.regression
def test_p3_skills_proficiency_bounds():
    src = STRATEGY_ROUTER.read_text()
    assert "proficiency < 1 or proficiency > 5" in src, (
        "Skills proficiency bounds removed — could allow nonsense values."
    )
