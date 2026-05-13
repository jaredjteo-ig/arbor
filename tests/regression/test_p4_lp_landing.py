"""P4-LP regression tests — landing page bundle (May 2026).

Source: workspaces/obayashi/04-validate/07-buyer-audit-2026-05-08.md
Each test pins one P4-LP element so it can't regress.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LANDING_PAGE = REPO_ROOT / "apps" / "landing" / "src" / "app" / "page.tsx"
CONTACT_PAGE = (
    REPO_ROOT / "apps" / "landing" / "src" / "app" / "contact" / "page.tsx"
)
PRICING_PAGE = (
    REPO_ROOT / "apps" / "landing" / "src" / "app" / "pricing" / "page.tsx"
)


# ---------------------------------------------------------------------------
# P4-LP-1 — Book-a-demo is the primary CTA on the landing page and the
# contact form is intent-aware (?intent=demo, ?tier=X).
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_lp_1_landing_has_book_a_demo_cta():
    """The landing page must surface 'Book a demo' as the primary CTA."""
    assert LANDING_PAGE.exists(), "landing page.tsx moved"
    src = LANDING_PAGE.read_text()

    assert "Book a demo" in src, (
        "Landing page must have a 'Book a demo' CTA (P4-LP-1)."
    )
    assert "/contact?intent=demo" in src, (
        "The CTA must route to /contact?intent=demo so the form can "
        "show the demo-specific copy + tag the lead as an inbound demo."
    )


@pytest.mark.regression
def test_p4_lp_1_contact_form_is_intent_aware():
    """The /contact form must adapt its copy based on ?intent / ?tier
    query params and emit an `intent` hidden field so sales can route."""
    src = CONTACT_PAGE.read_text()

    # Intent-aware copy switch
    assert 'intent === "demo"' in src, (
        "/contact must branch on intent=demo to show demo copy."
    )
    assert "Book a demo" in src, (
        "/contact?intent=demo must show 'Book a demo' as the heading."
    )

    # Tier routing
    assert "tier" in src, "/contact must accept a `tier` query param."
    assert "Talk to sales" in src, (
        "/contact?tier=X must show 'Talk to sales' heading variant."
    )

    # Hidden intent field on the form (so Netlify captures it)
    assert 'name="intent"' in src, (
        "The contact form must include a hidden `intent` field so the "
        "inbound source (demo / pricing tier / general) is captured."
    )


# ---------------------------------------------------------------------------
# P4-LP-2 — Trust strip with 5 truthful trust signals above the fold.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_lp_2_trust_strip_signals_present():
    """Trust strip must render the five truthful signals."""
    src = LANDING_PAGE.read_text()

    required_signals = [
        "PDPA-compliant",
        "Singapore-hosted",
        "Statutory files",
        "No AI in payroll math",
        "Cited advisory",
    ]
    for signal in required_signals:
        assert signal in src, (
            f"Trust strip must include '{signal}' (audit P4-LP-2). "
            "Every claim must be true today — no ISO 27001/SOC 2 "
            "language unless audited."
        )


@pytest.mark.regression
def test_p4_lp_2_no_unaudited_compliance_claims():
    """Trust strip must NOT claim ISO 27001 or SOC 2 (not audited).

    Audit P4-LP-2 hardline: don't ship trust-signal copy that isn't
    backed by an actual certificate. A pre-emptive guard keeps future
    edits honest.
    """
    src = LANDING_PAGE.read_text()
    forbidden = ["ISO 27001", "ISO27001", "SOC 2", "SOC2"]
    for claim in forbidden:
        assert claim not in src, (
            f"Landing page must not claim '{claim}' until the audit "
            "report is in hand and dated."
        )


# ---------------------------------------------------------------------------
# P4-LP-3 — Pricing page with 3 tiers + tier-aware sales CTA.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p4_lp_3_pricing_page_exists_with_three_tiers():
    """/pricing must exist with Starter / Growth / Enterprise tiers."""
    assert PRICING_PAGE.exists(), (
        "apps/landing/src/app/pricing/page.tsx must exist (P4-LP-3)."
    )
    src = PRICING_PAGE.read_text()

    for tier in ["Starter", "Growth", "Enterprise"]:
        assert tier in src, f"Pricing page must include the {tier} tier."

    # The CTA is rendered via a template literal `/contact?tier=${tier.id}`,
    # and the TIERS array carries the matching ids. Verify both.
    assert "/contact?tier=${tier.id}" in src, (
        "Pricing page must build /contact?tier=<id> links per tier so "
        "the contact form pre-fills the right copy + intent."
    )
    for tier_id in ["starter", "growth", "enterprise"]:
        assert f'"{tier_id}"' in src, (
            f"TIERS array must include id '{tier_id}' so the tier-aware "
            "CTA resolves on /contact?tier=<id>."
        )


@pytest.mark.regression
def test_p4_lp_3_pricing_nav_link_on_landing():
    """The landing nav must surface a Pricing link."""
    src = LANDING_PAGE.read_text()
    assert 'href="/pricing"' in src, (
        "Landing nav must link to /pricing (desktop + mobile) so "
        "users can discover plans from any page (P4-LP-3)."
    )
