"""Risk-Tiered Disclaimer System (T046).

Three-tier disclaimer framework:
- GREEN: No per-query disclaimer. Source citation is the transparency mechanism.
- AMBER: Light framing based on tripartite guidelines.
- RED: Strong disclosure with professional referral recommendation.

Verification gradient specifies operational depth per tier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VerificationDepth(str, Enum):
    """Verification depth applied to a response based on risk tier."""

    GREEN = "green"
    AMBER = "amber"
    RED = "red"


@dataclass(frozen=True)
class DisclaimerContent:
    """Disclaimer content for a response based on risk tier."""

    risk_tier: str
    show_disclaimer: bool
    disclaimer_text: str
    framing_text: str
    show_professional_referral: bool
    verification_depth: VerificationDepth
    human_review_queued: bool


# ── Platform-level disclaimer ────────────────────────────────

PLATFORM_DISCLAIMER = (
    "Arbor provides HR information and guidance based on publicly available "
    "Singapore employment regulations. This is not legal advice. For critical "
    "decisions involving significant financial exposure or legal proceedings, "
    "we recommend verification by a qualified employment law professional. "
    "Arbor maintains professional indemnity insurance."
)


# ── Per-response disclaimer logic ────────────────────────────


def get_disclaimer(
    risk_tier: str,
    confidence_score: float,
    domains: list[str],
) -> DisclaimerContent:
    """Get the appropriate disclaimer for a response based on risk tier.

    Args:
        risk_tier: "green", "amber", or "red"
        confidence_score: 0.0 to 1.0
        domains: List of regulatory domains involved

    Returns:
        DisclaimerContent with appropriate text and verification depth.
    """
    if risk_tier == "red" or confidence_score < 0.5:
        return DisclaimerContent(
            risk_tier="red",
            show_disclaimer=True,
            disclaimer_text=(
                "This situation involves significant legal or financial implications. "
                "The guidance below is based on current regulations, but given the "
                "complexity, we strongly recommend consulting an employment law "
                "specialist before taking action."
            ),
            framing_text="",
            show_professional_referral=True,
            verification_depth=VerificationDepth.RED,
            human_review_queued=True,
        )

    if risk_tier == "amber":
        domain_text = _domain_framing(domains)
        return DisclaimerContent(
            risk_tier="amber",
            show_disclaimer=True,
            disclaimer_text="",
            framing_text=domain_text,
            show_professional_referral=False,
            verification_depth=VerificationDepth.AMBER,
            human_review_queued=False,
        )

    # GREEN — no disclaimer needed
    return DisclaimerContent(
        risk_tier="green",
        show_disclaimer=False,
        disclaimer_text="",
        framing_text="",
        show_professional_referral=False,
        verification_depth=VerificationDepth.GREEN,
        human_review_queued=False,
    )


def _domain_framing(domains: list[str]) -> str:
    """Generate domain-specific framing text for AMBER tier."""
    framings = {
        "employment_act": "Based on current Employment Act provisions...",
        "cpf": "Based on current CPF contribution rules...",
        "fair_employment": "Based on current tripartite guidelines on fair employment...",
        "foreign_manpower": "Based on current foreign manpower regulations...",
        "tax": "Based on current IRAS guidelines...",
        "wsh": "Based on current workplace safety and health requirements...",
        "compliance": "Based on current regulatory requirements...",
    }

    for domain in domains:
        if domain in framings:
            return framings[domain]

    return "Based on current regulations and guidelines..."


# ── Verification gradient ────────────────────────────────────


@dataclass(frozen=True)
class VerificationResult:
    """Result of applying the verification gradient to a response."""

    depth: VerificationDepth
    citation_validated: bool
    confidence_checked: bool
    cross_domain_validated: bool
    human_review_queued: bool
    checks_passed: list[str]
    checks_failed: list[str]


def apply_verification_gradient(
    risk_tier: str,
    citation_valid: bool,
    confidence_score: float,
    cross_domain_consistent: bool = True,
) -> VerificationResult:
    """Apply the appropriate verification depth for a response.

    GREEN: citation validation only
    AMBER: citation + confidence + cross-domain
    RED: all AMBER + queued for human review
    """
    checks_passed: list[str] = []
    checks_failed: list[str] = []

    # All tiers: citation validation
    if citation_valid:
        checks_passed.append("citation_validation")
    else:
        checks_failed.append("citation_validation")

    if risk_tier == "green":
        return VerificationResult(
            depth=VerificationDepth.GREEN,
            citation_validated=citation_valid,
            confidence_checked=False,
            cross_domain_validated=False,
            human_review_queued=False,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    # AMBER and RED: confidence threshold
    confidence_ok = confidence_score >= 0.6
    if confidence_ok:
        checks_passed.append("confidence_threshold")
    else:
        checks_failed.append("confidence_threshold")

    # AMBER and RED: cross-domain consistency
    if cross_domain_consistent:
        checks_passed.append("cross_domain_consistency")
    else:
        checks_failed.append("cross_domain_consistency")

    if risk_tier == "amber":
        return VerificationResult(
            depth=VerificationDepth.AMBER,
            citation_validated=citation_valid,
            confidence_checked=True,
            cross_domain_validated=True,
            human_review_queued=False,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    # RED: all checks + human review queue
    checks_passed.append("human_review_queued")
    return VerificationResult(
        depth=VerificationDepth.RED,
        citation_validated=citation_valid,
        confidence_checked=True,
        cross_domain_validated=True,
        human_review_queued=True,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
    )
