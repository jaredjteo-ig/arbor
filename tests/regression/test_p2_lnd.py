"""P2-LD regression: Learning & Development module presence + contracts.

Pins the L&D module shape so future refactors can't silently strip the
training records / certifications / mandatory-training surface.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "training.py"
)
MODELS_FILE = (
    REPO_ROOT / "src" / "hr_advisory" / "models" / "company_user.py"
)


@pytest.mark.regression
def test_p2_ld_models_exist():
    source = MODELS_FILE.read_text()
    for cls in (
        "class TrainingRecord:",
        "class Certification:",
        "class MandatoryTrainingRequirement:",
    ):
        assert cls in source, f"Missing P2-LD model: {cls.strip(':')}"


@pytest.mark.regression
def test_p2_ld_router_endpoints():
    source = TRAINING_ROUTER.read_text()
    for path in (
        '"/records"',
        '"/records/{record_id}"',
        '"/certifications"',
        '"/certifications/expiring"',
        '"/certifications/{cert_id}"',
        '"/mandatory"',
        '"/mandatory/{req_id}"',
        '"/mandatory/coverage"',
    ):
        assert path in source, f"Missing P2-LD route: {path}"


@pytest.mark.regression
def test_p2_ld_coverage_helper_exists():
    """The mandatory-coverage derived view must use a casefold + whitespace
    normalised match so 'first aid certificate' matches 'First Aid Certificate'."""
    source = TRAINING_ROUTER.read_text()
    assert "_norm" in source and "casefold()" in source, (
        "Mandatory-coverage helper must casefold + whitespace-normalize "
        "certification name matches."
    )


@pytest.mark.regression
def test_p2_ld_employee_rule_matcher():
    """`_employee_matches_rule` must support all/department/pass_type/role."""
    tree = ast.parse(TRAINING_ROUTER.read_text())
    fn = next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "_employee_matches_rule"
        ),
        None,
    )
    assert fn is not None, "_employee_matches_rule helper missing."
    body = ast.unparse(fn)
    for kind in ("department", "pass_type", "role", "all"):
        assert kind in body, (
            f"_employee_matches_rule no longer handles selector {kind!r}"
        )
