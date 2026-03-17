"""Integration tests for the deterministic regulatory change classifier.

Tests:
- CPF rate change classified as relevant, domain=CPF/payroll, urgency=high
- Unrelated government news classified as not relevant
- Employment Act amendment classified as relevant, domain=general_employment
- Urgency levels (critical for immediate effect, medium for upcoming, low for info)
- Summary generation
- Action items generation
- Affected module mapping
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.adapters.regulatory_classifier import (
    ClassificationInput,
    ClassificationResult,
    Domain,
    RegulatoryChangeClassifier,
    Urgency,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def classifier() -> RegulatoryChangeClassifier:
    return RegulatoryChangeClassifier()


def _make_input(
    title: str,
    description: str = "",
    source: str = "change_detection",
    url: str = "https://example.gov.sg/change",
) -> ClassificationInput:
    return ClassificationInput(
        title=title,
        description=description,
        source=source,
        url=url,
    )


# ---------------------------------------------------------------------------
# CPF-related Changes
# ---------------------------------------------------------------------------


class TestCPFClassification:
    """CPF-related regulatory changes."""

    def test_cpf_rate_change_is_relevant(self, classifier):
        result = classifier.classify(
            _make_input("CPF OW ceiling increase to $8,500 effective Jan 2027")
        )
        assert result.is_relevant is True

    def test_cpf_rate_change_domain_includes_cpf(self, classifier):
        result = classifier.classify(
            _make_input("CPF contribution rate increase for senior workers")
        )
        assert Domain.CPF in result.domains

    def test_cpf_change_urgency_is_high(self, classifier):
        result = classifier.classify(
            _make_input(
                "CPF rate increase effective from 1 January 2027",
                description="The new CPF contribution rates will take effect for wages earned from 1 January 2027.",
            )
        )
        assert result.urgency in (Urgency.HIGH, Urgency.CRITICAL)

    def test_cpf_ceiling_change_affects_payroll(self, classifier):
        result = classifier.classify(_make_input("Ordinary Wage ceiling revised upward to $8,500"))
        affected = result.affected_modules
        assert any("payroll" in m for m in affected) or any("cpf" in m for m in affected)

    def test_cpf_ow_ceiling_confidence_above_threshold(self, classifier):
        result = classifier.classify(_make_input("CPF ordinary wage ceiling increase announced"))
        assert result.confidence >= 0.2


# ---------------------------------------------------------------------------
# Unrelated News
# ---------------------------------------------------------------------------


class TestIrrelevantClassification:
    """News that is not related to HR/employment."""

    def test_unrelated_gov_news_not_relevant(self, classifier):
        result = classifier.classify(
            _make_input(
                "Singapore launches new MRT line extension",
                description="The Thomson-East Coast Line extension will open in Q3 2026.",
                source="telegram",
            )
        )
        assert result.is_relevant is False

    def test_unrelated_news_has_empty_domains(self, classifier):
        result = classifier.classify(_make_input("New HDB BTO launches in Tengah and Jurong East"))
        assert len(result.domains) == 0

    def test_unrelated_news_urgency_is_low(self, classifier):
        result = classifier.classify(
            _make_input("Budget 2026: MediSave top-ups for eligible residents")
        )
        # MediSave triggers CPF domain, but this is a standalone test for
        # genuinely unrelated news
        result_unrelated = classifier.classify(
            _make_input("NEA announces new park connector trail in Punggol")
        )
        assert result_unrelated.urgency == Urgency.LOW


# ---------------------------------------------------------------------------
# Employment Act
# ---------------------------------------------------------------------------


class TestEmploymentActClassification:
    """Employment Act amendment classification."""

    def test_employment_act_amendment_is_relevant(self, classifier):
        result = classifier.classify(
            _make_input(
                "Employment Act amendment gazetted",
                description="Amendments to the Employment Act 1968 have been gazetted today.",
            )
        )
        assert result.is_relevant is True

    def test_employment_act_domain(self, classifier):
        result = classifier.classify(
            _make_input("Employment Act amendment bill passed in parliament")
        )
        assert Domain.GENERAL_EMPLOYMENT in result.domains

    def test_gazetted_triggers_high_urgency(self, classifier):
        result = classifier.classify(
            _make_input(
                "Employment Claims Act amendment gazetted",
                description="The amendment has been gazetted and will take effect next month.",
            )
        )
        assert result.urgency in (Urgency.HIGH, Urgency.CRITICAL)


# ---------------------------------------------------------------------------
# Urgency Levels
# ---------------------------------------------------------------------------


class TestUrgencyLevels:
    """Verify urgency classification for different signal phrases."""

    def test_effective_immediately_is_critical(self, classifier):
        result = classifier.classify(
            _make_input(
                "Emergency amendment: CPF rates effective immediately",
                description="The rates take effect with immediate effect.",
            )
        )
        assert result.urgency == Urgency.CRITICAL

    def test_consultation_paper_is_low(self, classifier):
        result = classifier.classify(
            _make_input(
                "MOM releases consultation paper on fair employment",
                description="Public consultation on proposed tripartite guidelines.",
            )
        )
        assert result.urgency == Urgency.LOW

    def test_proposed_amendment_is_medium(self, classifier):
        result = classifier.classify(
            _make_input(
                "Proposed amendment to retirement age thresholds",
                description="MOM proposes to raise the re-employment age. Will take effect from 2028.",
            )
        )
        assert result.urgency == Urgency.MEDIUM

    def test_rate_increase_is_high(self, classifier):
        result = classifier.classify(
            _make_input("Foreign worker levy rate increase for S Pass holders")
        )
        assert result.urgency == Urgency.HIGH


# ---------------------------------------------------------------------------
# Multi-domain Classification
# ---------------------------------------------------------------------------


class TestMultiDomain:
    """Changes that affect multiple domains."""

    def test_cpf_and_payroll_overlap(self, classifier):
        result = classifier.classify(
            _make_input("CPF contribution rate change affects payroll calculations")
        )
        assert len(result.domains) >= 2
        # Should have both CPF and payroll
        domain_values = {d.value for d in result.domains}
        assert "cpf" in domain_values

    def test_leave_and_employment(self, classifier):
        result = classifier.classify(
            _make_input(
                "Employment Act amendment: new paternity leave entitlements",
                description="Paternity leave increased under the Employment Act.",
            )
        )
        domain_values = {d.value for d in result.domains}
        assert "leave" in domain_values

    def test_foreign_workers_domain(self, classifier):
        result = classifier.classify(_make_input("EFMA amendment: new S Pass qualifying salary"))
        assert Domain.FOREIGN_WORKERS in result.domains


# ---------------------------------------------------------------------------
# Summary Generation
# ---------------------------------------------------------------------------


class TestSummaryGeneration:
    """Verify plain-language summary is generated."""

    def test_relevant_change_summary_contains_title(self, classifier):
        inp = _make_input("CPF ceiling revised to $8,500")
        result = classifier.classify(inp)
        assert "CPF ceiling revised" in result.summary

    def test_relevant_change_summary_contains_urgency_phrase(self, classifier):
        result = classifier.classify(_make_input("CPF rate increase gazetted"))
        # Summary should mention urgency-related phrasing
        assert any(
            phrase in result.summary.lower()
            for phrase in ["action", "review", "attention", "informational"]
        )

    def test_irrelevant_change_summary_says_not_directly_affect(self, classifier):
        result = classifier.classify(_make_input("New MRT line extension opens"))
        assert "does not appear to directly affect" in result.summary

    def test_summary_mentions_source(self, classifier):
        result = classifier.classify(
            _make_input(
                "CPF rates updated",
                source="sso_rss",
            )
        )
        assert "Singapore Statutes Online" in result.summary


# ---------------------------------------------------------------------------
# Action Items
# ---------------------------------------------------------------------------


class TestActionItems:
    """Verify action items are generated based on domains and urgency."""

    def test_cpf_change_has_rate_verification_action(self, classifier):
        result = classifier.classify(
            _make_input("CPF contribution rates revised", source="change_detection")
        )
        action_text = " ".join(result.action_items).lower()
        assert "cpf" in action_text

    def test_high_urgency_has_review_action(self, classifier):
        result = classifier.classify(_make_input("CPF rate increase gazetted"))
        assert any("Review the regulatory change" in item for item in result.action_items)

    def test_high_urgency_has_admin_record_action(self, classifier):
        result = classifier.classify(_make_input("Employment Act amendment gazetted"))
        assert any("regulatory update record" in item for item in result.action_items)

    def test_leave_domain_has_calendar_action(self, classifier):
        result = classifier.classify(_make_input("Public holiday calendar updated for 2027"))
        action_text = " ".join(result.action_items).lower()
        assert "leave" in action_text or "holiday" in action_text


# ---------------------------------------------------------------------------
# Affected Modules
# ---------------------------------------------------------------------------


class TestAffectedModules:
    """Verify domain-to-module mapping."""

    def test_cpf_domain_maps_to_payroll_calculator(self, classifier):
        result = classifier.classify(_make_input("CPF rates updated for 2027"))
        assert (
            "payroll_calculator" in result.affected_modules
            or "cpf_engine" in result.affected_modules
        )

    def test_tax_domain_maps_to_statutory_files(self, classifier):
        result = classifier.classify(_make_input("IRAS IR8A filing deadline changed for YA2027"))
        assert "statutory_files" in result.affected_modules

    def test_modules_are_sorted(self, classifier):
        result = classifier.classify(_make_input("CPF rate and payroll changes"))
        assert result.affected_modules == sorted(result.affected_modules)


# ---------------------------------------------------------------------------
# Classification Stats
# ---------------------------------------------------------------------------


class TestClassificationStats:
    """Verify stats tracking works correctly."""

    def test_stats_count_increases(self, classifier):
        assert classifier.get_classification_stats()["total_classified"] == 0

        classifier.classify(_make_input("CPF rates changed"))
        classifier.classify(_make_input("New park opens"))

        stats = classifier.get_classification_stats()
        assert stats["total_classified"] == 2

    def test_stats_relevant_count(self, classifier):
        classifier.classify(_make_input("CPF contribution rate increase"))
        classifier.classify(_make_input("New MRT line extension"))

        stats = classifier.get_classification_stats()
        assert stats["relevant"] >= 1

    def test_recent_classifications_returns_dicts(self, classifier):
        classifier.classify(_make_input("CPF rates changed"))
        recent = classifier.get_recent_classifications(limit=10)
        assert isinstance(recent, list)
        assert len(recent) == 1
        assert "is_relevant" in recent[0]
        assert "urgency" in recent[0]


# ---------------------------------------------------------------------------
# ClassificationResult serialization
# ---------------------------------------------------------------------------


class TestResultSerialization:
    """Verify to_dict produces complete serializable output."""

    def test_to_dict_contains_all_fields(self, classifier):
        result = classifier.classify(_make_input("CPF rates revised"))
        d = result.to_dict()
        expected_keys = {
            "is_relevant",
            "confidence",
            "domains",
            "urgency",
            "summary",
            "action_items",
            "affected_modules",
            "source",
            "title",
            "url",
            "classified_at",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_domains_are_string_values(self, classifier):
        result = classifier.classify(_make_input("CPF rates revised"))
        d = result.to_dict()
        for domain in d["domains"]:
            assert isinstance(domain, str)

    def test_urgency_is_string_value(self, classifier):
        result = classifier.classify(_make_input("CPF rates revised"))
        d = result.to_dict()
        assert isinstance(d["urgency"], str)
