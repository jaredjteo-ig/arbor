"""Unit tests for the risk-tiered disclaimer system.

Tests disclaimer generation for green/amber/red tiers and
verification gradient application.
"""

from __future__ import annotations

from hr_advisory.trust.disclaimers import (
    VerificationDepth,
    apply_verification_gradient,
    get_disclaimer,
)


class TestDisclaimers:
    """Test risk-tiered disclaimer generation."""

    def test_green_no_disclaimer(self) -> None:
        """GREEN tier should not show a per-query disclaimer."""
        result = get_disclaimer("green", 0.9, ["employment_act"])
        assert result.show_disclaimer is False
        assert result.show_professional_referral is False
        assert result.verification_depth == VerificationDepth.GREEN

    def test_amber_shows_framing(self) -> None:
        """AMBER tier should show domain-specific framing text."""
        result = get_disclaimer("amber", 0.8, ["employment_act"])
        assert result.show_disclaimer is True
        assert result.framing_text != ""
        assert result.show_professional_referral is False
        assert result.verification_depth == VerificationDepth.AMBER

    def test_red_shows_full_disclaimer(self) -> None:
        """RED tier should show full disclaimer with professional referral."""
        result = get_disclaimer("red", 0.9, ["employment_act"])
        assert result.show_disclaimer is True
        assert result.disclaimer_text != ""
        assert result.show_professional_referral is True
        assert result.verification_depth == VerificationDepth.RED
        assert result.human_review_queued is True

    def test_low_confidence_forces_red(self) -> None:
        """Confidence below 0.5 should force RED tier regardless of input tier."""
        result = get_disclaimer("green", 0.3, ["employment_act"])
        assert result.risk_tier == "red"
        assert result.show_professional_referral is True
        assert result.human_review_queued is True

    def test_cpf_domain_framing(self) -> None:
        """CPF domain should get CPF-specific framing text."""
        result = get_disclaimer("amber", 0.8, ["cpf"])
        assert "CPF" in result.framing_text

    def test_fair_employment_framing(self) -> None:
        """Fair employment domain should get tripartite-specific framing."""
        result = get_disclaimer("amber", 0.8, ["fair_employment"])
        assert "tripartite" in result.framing_text.lower()


class TestVerificationGradient:
    """Test verification depth application."""

    def test_green_citation_only(self) -> None:
        """GREEN applies citation validation only."""
        result = apply_verification_gradient("green", True, 0.9)
        assert result.depth == VerificationDepth.GREEN
        assert result.citation_validated is True
        assert result.confidence_checked is False
        assert result.cross_domain_validated is False
        assert result.human_review_queued is False

    def test_amber_full_validation(self) -> None:
        """AMBER applies citation + confidence + cross-domain."""
        result = apply_verification_gradient("amber", True, 0.8)
        assert result.depth == VerificationDepth.AMBER
        assert result.citation_validated is True
        assert result.confidence_checked is True
        assert result.cross_domain_validated is True
        assert result.human_review_queued is False

    def test_red_human_review(self) -> None:
        """RED applies all checks + queues human review."""
        result = apply_verification_gradient("red", True, 0.9)
        assert result.depth == VerificationDepth.RED
        assert result.human_review_queued is True

    def test_failed_citation_recorded(self) -> None:
        """Failed citation validation should be in checks_failed."""
        result = apply_verification_gradient("green", False, 0.9)
        assert "citation_validation" in result.checks_failed

    def test_low_confidence_recorded(self) -> None:
        """Confidence below threshold should be in checks_failed."""
        result = apply_verification_gradient("amber", True, 0.3)
        assert "confidence_threshold" in result.checks_failed
