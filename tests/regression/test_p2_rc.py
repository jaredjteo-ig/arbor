"""P2-RC regression: Recognition module presence + contracts."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RECO_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "recognition.py"
)
MODELS_FILE = (
    REPO_ROOT / "src" / "hr_advisory" / "models" / "company_user.py"
)


@pytest.mark.regression
def test_p2_rc_models_exist():
    src = MODELS_FILE.read_text()
    for cls in ("class Recognition:", "class PeerNomination:"):
        assert cls in src, f"Missing P2-RC model: {cls}"


@pytest.mark.regression
def test_p2_rc_router_endpoints():
    src = RECO_ROUTER.read_text()
    for marker in (
        '"/categories"',
        '"/feed"',
        '"/received"',
        '"/nominate"',
        '"/nominations"',
    ):
        assert marker in src, f"Missing recognition endpoint: {marker}"


@pytest.mark.regression
def test_p2_rc_categories_locked():
    """The 5 recognition categories must be the canonical set."""
    src = RECO_ROUTER.read_text()
    for cat in (
        '"above_and_beyond"',
        '"teamwork"',
        '"customer"',
        '"innovation"',
        '"values"',
    ):
        assert cat in src, f"Recognition category {cat} dropped."


@pytest.mark.regression
def test_p2_rc_rate_limits():
    """Both give and nominate must rate-limit."""
    src = RECO_ROUTER.read_text()
    assert (
        "recognition_give:" in src
    ), "Recognition give endpoint dropped its rate limit."
    assert (
        "recognition_nominate:" in src
    ), "Peer nomination dropped its rate limit (per rules/security.md)."


@pytest.mark.regression
def test_p2_rc_message_length_cap():
    """1000-char cap on recognition messages must remain enforced."""
    src = RECO_ROUTER.read_text()
    assert "1000" in src, "Recognition message length cap removed."
