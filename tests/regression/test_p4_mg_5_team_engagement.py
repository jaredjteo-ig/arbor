"""P4-MG-5 regression tests — team engagement view.

The /engagement-surveys/team/aggregate endpoint already exists with
the n ≥ 5 floor, Z26 self-exclusion, and tier-aware pseudonym
resolution. P4-MG-5 wires it onto /team:

- FE service exposes engagementApi.teamAggregate()
- useTeamEngagement() hook
- Team engagement card on /team (hidden when n < 5 or tier=anonymous)
- /team/engagement detail page with full breakdown

This file pins those surfaces. The underlying BE behaviour is
already tested in tests/regression/test_redteam* files and is not
re-tested here.

Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
finding P1-A. P4-MG-5 in P4-MG-manager-role.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGAGEMENT_API = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "services"
    / "api"
    / "engagement.ts"
)
USE_TEAM_HOOK = (
    REPO_ROOT / "apps" / "web" / "src" / "hooks" / "api" / "useTeam.ts"
)
TEAM_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "team"
    / "page.tsx"
)
TEAM_ENGAGEMENT_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "team"
    / "engagement"
    / "page.tsx"
)
ENGAGEMENT_ROUTER = (
    REPO_ROOT
    / "src"
    / "hr_advisory"
    / "api"
    / "routers"
    / "engagement_surveys.py"
)


# ---------------------------------------------------------------------------
# BE already exists — verify the endpoint we wire to is still mounted.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg5_team_aggregate_endpoint_still_exists():
    """The /team/aggregate manager view must still be on the router.
    If a future refactor moves or renames it, MG-5's wiring breaks."""
    src = ENGAGEMENT_ROUTER.read_text()
    assert '@router.get("/team/aggregate")' in src, (
        "engagement_surveys.py must continue to expose /team/aggregate "
        "— P4-MG-5 wires onto it."
    )


@pytest.mark.regression
def test_mg5_team_aggregate_enforces_anonymity_floor():
    """Pin the n ≥ 5 floor + Z26 self-exclusion guards. Future
    refactors must NOT loosen these — they protect direct reports
    from manager re-identification (P50)."""
    src = ENGAGEMENT_ROUTER.read_text()
    assert "MIN_COHORT_SIZE" in src, (
        "Manager view must guard against n < MIN_COHORT_SIZE."
    )
    # Self-exclusion is enforced when building the scope filter
    assert "manager_id" in src and "reporting_manager_id" in src
    # Anonymous-tier surveys must NEVER yield a team aggregate
    assert 'survey_tier == "anonymous"' in src, (
        "Anonymous-tier surveys must refuse team aggregation."
    )


# ---------------------------------------------------------------------------
# FE service + hook surface.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg5_frontend_service_exposes_team_aggregate():
    src = ENGAGEMENT_API.read_text()
    assert "teamAggregate" in src, (
        "engagementApi must expose teamAggregate() (P4-MG-5)."
    )
    assert "/engagement-surveys/team/aggregate" in src, (
        "engagementApi.teamAggregate must hit the existing "
        "/engagement-surveys/team/aggregate endpoint."
    )
    # Discriminated union typing
    assert "TeamEngagementVisible" in src
    assert "TeamEngagementHidden" in src


@pytest.mark.regression
def test_mg5_use_team_engagement_hook_exists():
    src = USE_TEAM_HOOK.read_text()
    assert "useTeamEngagement" in src, (
        "useTeamEngagement hook must exist in useTeam.ts."
    )
    assert "engagementApi.teamAggregate" in src, (
        "useTeamEngagement must call engagementApi.teamAggregate."
    )


# ---------------------------------------------------------------------------
# /team page — engagement card.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg5_team_page_renders_engagement_card():
    src = TEAM_PAGE.read_text()
    assert "useTeamEngagement" in src, (
        "/team page must call useTeamEngagement to render the "
        "engagement card."
    )
    assert "Team engagement" in src, (
        "/team page must include a Team engagement card."
    )
    # Privacy floor surfaced in the FE — n badge + explanation
    assert "n = " in src or "n =" in src, (
        "The card must show the response count n so managers "
        "understand the anonymity threshold."
    )
    # Deep link to the detail page
    assert "/team/engagement" in src


@pytest.mark.regression
def test_mg5_team_page_handles_hidden_state():
    """The card must render the 'not yet available' state when the
    aggregate is hidden (n < 5 / anonymous tier / no closed surveys)
    rather than crashing or showing fake numbers."""
    src = TEAM_PAGE.read_text()
    # Discriminated-union check — `is_visible: false` branch must
    # be handled explicitly.
    assert "is_visible" in src
    assert "Aggregates require at least 5 responses" in src or (
        "5 responses" in src
    ), "Hidden card must explain the anonymity floor to the manager."


# ---------------------------------------------------------------------------
# /team/engagement detail page.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg5_team_engagement_detail_page_exists():
    assert TEAM_ENGAGEMENT_PAGE.exists(), (
        "/team/engagement detail page must exist at "
        "apps/web/src/app/(dashboard)/team/engagement/page.tsx"
    )


@pytest.mark.regression
def test_mg5_detail_page_renders_full_breakdown():
    src = TEAM_ENGAGEMENT_PAGE.read_text()
    # The four sections promised by the original todo
    for marker in [
        "Team engagement",  # title
        "by_question",  # weakest-first table data
        "themes",  # theme tags
        "trend",  # 6-pulse trend table
    ]:
        assert marker in src, (
            f"Detail page must reference '{marker}' to render the "
            "full breakdown (avg + by-question + themes + 6-pulse trend)."
        )


@pytest.mark.regression
def test_mg5_detail_page_explains_privacy_model():
    """Detail page must explicitly state the P50 privacy guarantee
    (manager sees distributions, not responses) — this is the
    differentiator vs unsafe team-engagement tools."""
    src = TEAM_ENGAGEMENT_PAGE.read_text()
    # Look for the language pattern, not exact words
    assert "individual responses" in src.lower() or "distributions only" in src.lower(), (
        "Detail page must state the privacy model so managers "
        "understand they see distributions only."
    )
    assert "5 responses" in src or "n ≥ 5" in src or "n >= 5" in src, (
        "Detail page must surface the n ≥ 5 floor explanation."
    )


@pytest.mark.regression
def test_mg5_detail_page_back_link_to_team():
    """The detail page must link back to /team — important for
    nav structure since /team/engagement isn't in the sidebar."""
    src = TEAM_ENGAGEMENT_PAGE.read_text()
    assert 'href="/team"' in src, (
        "/team/engagement must include a 'Back to team' link."
    )
