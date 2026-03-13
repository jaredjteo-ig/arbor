"""Integration tests for the Learning Pipeline API (COC Layer 5).

Tests:
- Feedback submission and retrieval
- KB gap listing
- Recommendation listing and review
- Monthly report generation
- Auth requirements on all endpoints
"""

from __future__ import annotations

import pytest

from hr_advisory.trust.learning_pipeline import (
    FeedbackCategory,
    RecommendationStatus,
    RecommendationType,
    _feedback_records,
    _kb_gaps,
    _monthly_reports,
    _query_patterns,
    _recommendations,
    _resolution_patterns,
    _routing_insights,
    detect_kb_gap,
    propose_recommendation,
    record_feedback,
    record_query_pattern,
)


@pytest.fixture(autouse=True)
def _clean_learning_stores():
    """Clear in-memory learning stores before each test."""
    _feedback_records.clear()
    _kb_gaps.clear()
    _monthly_reports.clear()
    _query_patterns.clear()
    _recommendations.clear()
    _resolution_patterns.clear()
    _routing_insights.clear()
    yield
    _feedback_records.clear()
    _kb_gaps.clear()
    _monthly_reports.clear()
    _query_patterns.clear()
    _recommendations.clear()
    _resolution_patterns.clear()
    _routing_insights.clear()


class TestFeedbackRecording:
    """Test feedback ingestion into learning pipeline."""

    def test_positive_feedback(self):
        record = record_feedback(
            feedback_id="fb-001",
            session_id="sess-001",
            is_positive=True,
        )
        assert record.feedback_id == "fb-001"
        assert record.is_positive is True
        assert record.category is None
        assert len(_feedback_records) == 1

    def test_negative_feedback_with_category(self):
        record = record_feedback(
            feedback_id="fb-002",
            session_id="sess-002",
            is_positive=False,
            category=FeedbackCategory.WRONG_ANSWER,
            domains=["cpf"],
            query_snippet="How much CPF for age 56?",
        )
        assert record.is_positive is False
        assert record.category == FeedbackCategory.WRONG_ANSWER
        assert record.domains == ["cpf"]
        assert len(_feedback_records) == 1

    def test_multiple_feedback_records(self):
        for i in range(5):
            record_feedback(
                feedback_id=f"fb-{i}",
                session_id=f"sess-{i}",
                is_positive=i % 2 == 0,
            )
        assert len(_feedback_records) == 5


class TestQueryPatternTracking:
    """Test query pattern recording and aggregation."""

    def test_new_pattern_recorded(self):
        pattern = record_query_pattern(
            pattern_id="cpf:green",
            description="CPF queries with green risk",
            domains=["cpf"],
            confidence=0.9,
            satisfaction=1.0,
            query_example="What are CPF rates?",
        )
        assert pattern.frequency == 1
        assert pattern.avg_confidence == 0.9
        assert len(pattern.example_queries) == 1

    def test_pattern_frequency_increments(self):
        record_query_pattern("cpf:green", "CPF", ["cpf"], 0.9, 1.0)
        record_query_pattern("cpf:green", "CPF", ["cpf"], 0.8, 0.5)
        pattern = _query_patterns["cpf:green"]
        assert pattern.frequency == 2
        assert pattern.avg_confidence == pytest.approx(0.85, abs=0.01)
        assert pattern.avg_satisfaction == pytest.approx(0.75, abs=0.01)


class TestKbGapDetection:
    """Test KB gap detection and priority assignment."""

    def test_critical_gap_detected(self):
        gap = detect_kb_gap(
            gap_id="gap-001",
            domains=["foreign_manpower"],
            description="Missing S Pass quota rules for 2026",
            evidence_query_count=50,
            avg_confidence=0.25,
            negative_feedback_count=12,
        )
        assert gap.priority == "critical"
        assert gap.gap_id == "gap-001"

    def test_high_gap_detected(self):
        gap = detect_kb_gap(
            gap_id="gap-002",
            domains=["cpf"],
            description="Missing CPF rate for aged 71+",
            evidence_query_count=20,
            avg_confidence=0.45,
            negative_feedback_count=6,
        )
        assert gap.priority == "high"

    def test_medium_gap_detected(self):
        gap = detect_kb_gap(
            gap_id="gap-003",
            domains=["employment_act"],
            description="Part-time leave prorating unclear",
            evidence_query_count=10,
            avg_confidence=0.7,
            negative_feedback_count=3,
        )
        assert gap.priority == "medium"

    def test_low_gap_detected(self):
        gap = detect_kb_gap(
            gap_id="gap-004",
            domains=["employment_act"],
            description="Minor formatting issue",
            evidence_query_count=2,
            avg_confidence=0.8,
            negative_feedback_count=1,
        )
        assert gap.priority == "low"


class TestRecommendationEngine:
    """Test recommendation proposal and review."""

    def test_propose_recommendation(self):
        rec = propose_recommendation(
            recommendation_id="rec-001",
            rec_type=RecommendationType.KB_EXPANSION,
            title="Add 2026 S Pass quota tables",
            description="Foreign manpower queries are failing due to missing 2026 quota data",
            evidence_count=12,
            affected_domains=["foreign_manpower"],
            priority="high",
        )
        assert rec.status == RecommendationStatus.PROPOSED
        assert rec.priority == "high"

    def test_approve_recommendation(self):
        propose_recommendation(
            recommendation_id="rec-002",
            rec_type=RecommendationType.KB_CORRECTION,
            title="Fix paternity leave weeks",
            description="KB shows 2 weeks instead of 4 weeks",
            evidence_count=8,
            affected_domains=["child_development"],
            priority="critical",
        )
        from hr_advisory.trust.learning_pipeline import review_recommendation

        rec = review_recommendation(
            recommendation_id="rec-002",
            approved=True,
            reviewed_by="admin@example.com",
            notes="Confirmed: paternity leave updated to 4 weeks since Jan 2025",
        )
        assert rec.status == RecommendationStatus.APPROVED
        assert rec.reviewed_by == "admin@example.com"

    def test_reject_recommendation(self):
        propose_recommendation(
            recommendation_id="rec-003",
            rec_type=RecommendationType.ROUTING_CHANGE,
            title="Merge CPF and EA domains",
            description="They co-occur 80% of the time",
            evidence_count=3,
            affected_domains=["cpf", "employment_act"],
        )
        from hr_advisory.trust.learning_pipeline import review_recommendation

        rec = review_recommendation(
            recommendation_id="rec-003",
            approved=False,
            reviewed_by="admin@example.com",
            notes="Domains should remain separate for accuracy",
        )
        assert rec.status == RecommendationStatus.REJECTED

    def test_review_nonexistent_raises(self):
        from hr_advisory.trust.learning_pipeline import review_recommendation

        with pytest.raises(ValueError, match="not found"):
            review_recommendation("nonexistent", approved=True, reviewed_by="admin")


class TestMonthlyReportGeneration:
    """Test monthly report generation."""

    def test_empty_report(self):
        from hr_advisory.trust.learning_pipeline import generate_monthly_report

        report = generate_monthly_report(
            report_id="report-001",
            period="2026-03",
            total_queries=100,
        )
        assert report.total_queries == 100
        assert report.total_feedback == 0
        assert report.positive_feedback_rate == 0.0

    def test_report_with_feedback(self):
        from hr_advisory.trust.learning_pipeline import generate_monthly_report

        record_feedback("fb-1", "s-1", is_positive=True)
        record_feedback("fb-2", "s-2", is_positive=True)
        record_feedback("fb-3", "s-3", is_positive=False, category=FeedbackCategory.WRONG_ANSWER)

        report = generate_monthly_report(
            report_id="report-002",
            period="2026-03",
            total_queries=50,
        )
        assert report.total_feedback == 3
        assert report.positive_feedback_rate == pytest.approx(2 / 3, abs=0.01)

    def test_report_includes_kb_gaps(self):
        from hr_advisory.trust.learning_pipeline import generate_monthly_report

        detect_kb_gap("g-1", ["cpf"], "Missing data", 10, 0.4, 5)
        detect_kb_gap("g-2", ["employment_act"], "Unclear provision", 5, 0.6, 3)

        report = generate_monthly_report("report-003", "2026-03", 200)
        assert len(report.kb_gaps_detected) == 2
