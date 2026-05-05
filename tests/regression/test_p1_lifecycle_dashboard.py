"""P1 regression: Lifecycle dashboard aggregator + health-pill thresholds.

Origin: Phase 1 obayashi (`workspaces/obayashi/02-plans/02-lifecycle-dashboard-spec.md`).

Pins three contracts at the source-code level so future refactors don't
silently break the buyer-facing surface:

  1. The aggregator endpoint `/strategy/lifecycle-dashboard` exists.
  2. The health-pill threshold functions are present and stable.
  3. Each pill function returns one of {green, amber, red} for representative
     inputs that match the spec.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "strategy.py"
)


@pytest.mark.regression
def test_p1_lifecycle_endpoint_registered():
    """`/strategy/lifecycle-dashboard` route must be declared on the router."""
    source = STRATEGY_ROUTER.read_text()
    assert "@router.get(\"/lifecycle-dashboard\")" in source, (
        "Lifecycle aggregator endpoint missing — P1-1 regression."
    )
    assert "lifecycle_dashboard" in source, (
        "lifecycle_dashboard handler renamed — Strategy router wiring broken."
    )


@pytest.mark.regression
def test_p1_health_pill_helpers_exist():
    """All 8 stage health-pill helpers must be present in strategy.py."""
    tree = ast.parse(STRATEGY_ROUTER.read_text())
    funcs = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef)
    }
    expected = {
        "_pill_strategy",
        "_pill_attract",
        "_pill_recruit",
        "_pill_onboard",
        "_pill_lnd",
        "_pill_reward",
        "_pill_progression",
        "_pill_retain",
    }
    missing = expected - funcs
    assert not missing, f"Missing pill helpers: {missing}"


def _pill_module():
    return importlib.import_module(
        "hr_advisory.api.routers.strategy"
    )


@pytest.mark.regression
@pytest.mark.parametrize(
    "actual,target,expected",
    [
        (28, 28, "green"),     # 0% delta
        (27, 30, "green"),     # 10% delta
        (24, 30, "amber"),     # 20% delta
        (20, 30, "red"),       # >20% delta
        (0, 0, "amber"),       # No plan set
    ],
)
def test_p1_pill_strategy_thresholds(actual, target, expected):
    pill = _pill_module()._pill_strategy(actual, target)
    assert pill == expected, f"_pill_strategy({actual},{target}) = {pill!r}"


@pytest.mark.regression
@pytest.mark.parametrize(
    "applies,sources,expected",
    [
        (0, 0, "red"),
        (0, 1, "red"),     # No applies still red even with sources
        (5, 1, "amber"),
        (5, 2, "amber"),
        (5, 3, "green"),
        (50, 5, "green"),
    ],
)
def test_p1_pill_attract_thresholds(applies, sources, expected):
    pill = _pill_module()._pill_attract(applies, sources)
    assert pill == expected


@pytest.mark.regression
@pytest.mark.parametrize(
    "active,stale,candidates,expected",
    [
        (0, 0, 0, "amber"),     # No open jobs
        (3, 0, 5, "green"),     # All fresh, candidates exist
        (3, 1, 5, "amber"),     # 1 stale → amber
        (3, 3, 5, "red"),       # All stale → red
        (3, 0, 0, "red"),       # No candidates → red
    ],
)
def test_p1_pill_recruit_thresholds(active, stale, candidates, expected):
    pill = _pill_module()._pill_recruit(active, stale, candidates)
    assert pill == expected


@pytest.mark.regression
@pytest.mark.parametrize(
    "avg_completion,overdue,expected",
    [
        (0.85, 0, "green"),
        (0.60, 0, "amber"),
        (0.85, 1, "amber"),
        (0.40, 0, "red"),
        (0.85, 3, "red"),
    ],
)
def test_p1_pill_onboard_thresholds(avg_completion, overdue, expected):
    pill = _pill_module()._pill_onboard(avg_completion, overdue)
    assert pill == expected


@pytest.mark.regression
@pytest.mark.parametrize(
    "avg_hours,has_data,expected",
    [
        (12.0, True, "green"),
        (7.0, True, "amber"),
        (3.0, True, "red"),
        (0.0, False, "red"),
    ],
)
def test_p1_pill_lnd_thresholds(avg_hours, has_data, expected):
    pill = _pill_module()._pill_lnd(avg_hours, has_data)
    assert pill == expected


@pytest.mark.regression
@pytest.mark.parametrize(
    "due_total,due_completed,expected",
    [
        (0, 0, "amber"),     # No reviews due → amber
        (10, 9, "green"),
        (10, 6, "amber"),
        (10, 3, "red"),
    ],
)
def test_p1_pill_progression_thresholds(due_total, due_completed, expected):
    pill = _pill_module()._pill_progression(due_total, due_completed)
    assert pill == expected


@pytest.mark.regression
@pytest.mark.parametrize(
    "yoy_delta,expected",
    [
        (-1.0, "green"),
        (0.5, "green"),
        (1.5, "amber"),
        (4.0, "red"),
    ],
)
def test_p1_pill_retain_thresholds(yoy_delta, expected):
    pill = _pill_module()._pill_retain(yoy_delta)
    assert pill == expected


@pytest.mark.regression
def test_p1_lifecycle_response_shape():
    """The aggregator response must include hero + stages + di_snapshot + activity."""
    source = STRATEGY_ROUTER.read_text()
    for key in ("hero", "stages", "di_snapshot", "activity"):
        assert f'"{key}"' in source, (
            f"Lifecycle aggregator no longer returns {key!r}."
        )

    for stage in (
        "strategy",
        "attract",
        "recruit",
        "onboard",
        "lnd",
        "reward",
        "progression",
        "retain",
    ):
        assert f'"{stage}"' in source, (
            f"Stage {stage!r} no longer present in the aggregator output."
        )
