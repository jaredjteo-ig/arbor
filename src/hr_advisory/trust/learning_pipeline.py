"""Platform Learning and Feedback Loop — COC Layer 5 (T050).

Implements the learning pipeline that makes institutional knowledge
compound over time:

- Usage pattern analysis: query patterns, routing decisions, confidence
- KB gap detection: low-confidence patterns → KB expansion priorities
- Agent routing optimization: frequent domain co-occurrences
- Resolution pattern capture: successful cross-domain resolutions
- Feedback-to-action pipeline: categorised thumbs-down → KB improvement
- Periodic recommendations: monthly summary for human expert review

All evolved changes go through human review (CARE Human-on-the-Loop).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Feedback taxonomy ────────────────────────────────────────


class FeedbackCategory(str, Enum):
    """Category assigned to negative feedback."""

    WRONG_ANSWER = "wrong_answer"
    OUTDATED_INFO = "outdated_info"
    UNCLEAR_EXPLANATION = "unclear_explanation"
    MISSING_TOPIC = "missing_topic"
    IRRELEVANT_RESPONSE = "irrelevant_response"
    TOO_GENERIC = "too_generic"


class RecommendationType(str, Enum):
    """Type of improvement recommendation."""

    KB_EXPANSION = "kb_expansion"
    KB_CORRECTION = "kb_correction"
    PROMPT_REFINEMENT = "prompt_refinement"
    ROUTING_CHANGE = "routing_change"
    NEW_SCENARIO = "new_scenario"


class RecommendationStatus(str, Enum):
    """Status of a recommendation in the review pipeline."""

    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


# ── Data models ──────────────────────────────────────────────


@dataclass
class QueryPattern:
    """A detected pattern in user queries."""

    pattern_id: str
    description: str
    domains: list[str]
    frequency: int  # total occurrences
    avg_confidence: float
    avg_satisfaction: float  # 0.0 = all negative, 1.0 = all positive
    first_seen: datetime
    last_seen: datetime
    example_queries: list[str] = field(default_factory=list)


@dataclass
class KbGap:
    """A detected gap in the knowledge base."""

    gap_id: str
    domains: list[str]
    description: str
    evidence_query_count: int
    avg_confidence_when_hit: float
    negative_feedback_count: int
    suggested_provisions: list[str] = field(default_factory=list)
    priority: str = "medium"  # critical, high, medium, low
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingInsight:
    """An insight about agent routing patterns."""

    domain_pair: tuple[str, str]
    co_occurrence_count: int
    avg_resolution_confidence: float
    suggested_action: str  # e.g., "pre-route to both", "merge domains"


@dataclass
class ResolutionPattern:
    """A successful resolution pattern for cross-domain queries."""

    pattern_id: str
    query_type: str
    domains_involved: list[str]
    agent_sequence: list[str]
    key_provisions: list[str]
    resolution_summary: str
    success_count: int
    avg_confidence: float
    captured_at: datetime = field(default_factory=datetime.now)


@dataclass
class FeedbackRecord:
    """Processed feedback record with categorisation."""

    feedback_id: str
    session_id: str
    is_positive: bool
    category: Optional[FeedbackCategory] = None
    domains: list[str] = field(default_factory=list)
    query_snippet: str = ""
    recorded_at: datetime = field(default_factory=datetime.now)


@dataclass
class ImprovementRecommendation:
    """A recommendation for platform improvement."""

    recommendation_id: str
    rec_type: RecommendationType
    title: str
    description: str
    priority: str  # critical, high, medium, low
    evidence_count: int  # number of feedback/queries supporting this
    affected_domains: list[str]
    status: RecommendationStatus = RecommendationStatus.PROPOSED
    proposed_at: datetime = field(default_factory=datetime.now)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: str = ""


@dataclass
class MonthlyReport:
    """Monthly learning pipeline summary for human review."""

    report_id: str
    period: str  # e.g., "2026-03"
    total_queries: int
    total_feedback: int
    positive_feedback_rate: float
    kb_gaps_detected: list[KbGap]
    routing_insights: list[RoutingInsight]
    resolution_patterns_captured: int
    recommendations: list[ImprovementRecommendation]
    generated_at: datetime = field(default_factory=datetime.now)


# ── In-memory stores ─────────────────────────────────────────
# In production, backed by DataFlow models + PostgreSQL.

_query_patterns: dict[str, QueryPattern] = {}
_kb_gaps: dict[str, KbGap] = {}
_routing_insights: list[RoutingInsight] = []
_resolution_patterns: dict[str, ResolutionPattern] = {}
_feedback_records: list[FeedbackRecord] = []
_recommendations: dict[str, ImprovementRecommendation] = {}
_monthly_reports: list[MonthlyReport] = []


# ── Feedback ingestion ───────────────────────────────────────


def record_feedback(
    feedback_id: str,
    session_id: str,
    is_positive: bool,
    category: Optional[FeedbackCategory] = None,
    domains: Optional[list[str]] = None,
    query_snippet: str = "",
) -> FeedbackRecord:
    """Record user feedback for learning pipeline processing."""
    record = FeedbackRecord(
        feedback_id=feedback_id,
        session_id=session_id,
        is_positive=is_positive,
        category=category,
        domains=domains or [],
        query_snippet=query_snippet,
    )
    _feedback_records.append(record)
    return record


# ── Query pattern tracking ───────────────────────────────────


def record_query_pattern(
    pattern_id: str,
    description: str,
    domains: list[str],
    confidence: float,
    satisfaction: float,
    query_example: str = "",
) -> QueryPattern:
    """Record or update a query pattern observation."""
    existing = _query_patterns.get(pattern_id)
    if existing is not None:
        # Update running averages
        n = existing.frequency
        existing.avg_confidence = (existing.avg_confidence * n + confidence) / (n + 1)
        existing.avg_satisfaction = (existing.avg_satisfaction * n + satisfaction) / (n + 1)
        existing.frequency = n + 1
        existing.last_seen = datetime.now()
        if query_example and len(existing.example_queries) < 5:
            existing.example_queries.append(query_example)
        return existing

    pattern = QueryPattern(
        pattern_id=pattern_id,
        description=description,
        domains=domains,
        frequency=1,
        avg_confidence=confidence,
        avg_satisfaction=satisfaction,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        example_queries=[query_example] if query_example else [],
    )
    _query_patterns[pattern_id] = pattern
    return pattern


# ── KB gap detection ─────────────────────────────────────────


def detect_kb_gap(
    gap_id: str,
    domains: list[str],
    description: str,
    evidence_query_count: int,
    avg_confidence: float,
    negative_feedback_count: int,
    suggested_provisions: Optional[list[str]] = None,
) -> KbGap:
    """Register a detected knowledge base gap."""
    # Auto-assign priority based on evidence strength
    if negative_feedback_count >= 10 or avg_confidence < 0.3:
        priority = "critical"
    elif negative_feedback_count >= 5 or avg_confidence < 0.5:
        priority = "high"
    elif negative_feedback_count >= 2:
        priority = "medium"
    else:
        priority = "low"

    gap = KbGap(
        gap_id=gap_id,
        domains=domains,
        description=description,
        evidence_query_count=evidence_query_count,
        avg_confidence_when_hit=avg_confidence,
        negative_feedback_count=negative_feedback_count,
        suggested_provisions=suggested_provisions or [],
        priority=priority,
    )
    _kb_gaps[gap_id] = gap
    return gap


def get_kb_gaps(priority: Optional[str] = None) -> list[KbGap]:
    """Get detected KB gaps, optionally filtered by priority."""
    gaps = list(_kb_gaps.values())
    if priority is not None:
        gaps = [g for g in gaps if g.priority == priority]
    return sorted(gaps, key=lambda g: g.negative_feedback_count, reverse=True)


# ── Routing optimization ────────────────────────────────────


def record_routing_insight(
    domain_pair: tuple[str, str],
    co_occurrence_count: int,
    avg_resolution_confidence: float,
    suggested_action: str,
) -> RoutingInsight:
    """Record a routing optimisation insight."""
    insight = RoutingInsight(
        domain_pair=domain_pair,
        co_occurrence_count=co_occurrence_count,
        avg_resolution_confidence=avg_resolution_confidence,
        suggested_action=suggested_action,
    )
    _routing_insights.append(insight)
    return insight


# ── Resolution pattern capture ───────────────────────────────


def capture_resolution_pattern(
    pattern_id: str,
    query_type: str,
    domains_involved: list[str],
    agent_sequence: list[str],
    key_provisions: list[str],
    resolution_summary: str,
    confidence: float,
) -> ResolutionPattern:
    """Capture a successful resolution pattern for future reference."""
    existing = _resolution_patterns.get(pattern_id)
    if existing is not None:
        existing.success_count += 1
        n = existing.success_count
        existing.avg_confidence = (existing.avg_confidence * (n - 1) + confidence) / n
        return existing

    pattern = ResolutionPattern(
        pattern_id=pattern_id,
        query_type=query_type,
        domains_involved=domains_involved,
        agent_sequence=agent_sequence,
        key_provisions=key_provisions,
        resolution_summary=resolution_summary,
        success_count=1,
        avg_confidence=confidence,
    )
    _resolution_patterns[pattern_id] = pattern
    return pattern


# ── Recommendation engine ────────────────────────────────────


def propose_recommendation(
    recommendation_id: str,
    rec_type: RecommendationType,
    title: str,
    description: str,
    evidence_count: int,
    affected_domains: list[str],
    priority: str = "medium",
) -> ImprovementRecommendation:
    """Propose a platform improvement recommendation."""
    rec = ImprovementRecommendation(
        recommendation_id=recommendation_id,
        rec_type=rec_type,
        title=title,
        description=description,
        priority=priority,
        evidence_count=evidence_count,
        affected_domains=affected_domains,
    )
    _recommendations[recommendation_id] = rec
    return rec


def review_recommendation(
    recommendation_id: str,
    approved: bool,
    reviewed_by: str,
    notes: str = "",
) -> ImprovementRecommendation:
    """Record human expert review of a recommendation."""
    rec = _recommendations.get(recommendation_id)
    if rec is None:
        raise ValueError(f"Recommendation {recommendation_id} not found")
    rec.status = RecommendationStatus.APPROVED if approved else RecommendationStatus.REJECTED
    rec.reviewed_by = reviewed_by
    rec.reviewed_at = datetime.now()
    rec.review_notes = notes
    return rec


def get_recommendations(
    status: Optional[RecommendationStatus] = None,
) -> list[ImprovementRecommendation]:
    """Get recommendations, optionally filtered by status."""
    recs = list(_recommendations.values())
    if status is not None:
        recs = [r for r in recs if r.status == status]
    return sorted(recs, key=lambda r: r.proposed_at, reverse=True)


def apply_recommendation(
    recommendation_id: str,
    applied_by: str,
    notes: str = "",
) -> ImprovementRecommendation:
    """Apply an approved recommendation, marking it as IMPLEMENTED.

    Only recommendations with APPROVED status can be applied.
    Raises ValueError if the recommendation does not exist,
    is not in APPROVED status, or is already IMPLEMENTED.
    """
    rec = _recommendations.get(recommendation_id)
    if rec is None:
        raise KeyError(f"Recommendation {recommendation_id} not found")
    if rec.status == RecommendationStatus.IMPLEMENTED:
        raise ValueError(f"Recommendation {recommendation_id} is already implemented")
    if rec.status != RecommendationStatus.APPROVED:
        raise ValueError(
            f"Recommendation {recommendation_id} must be approved before it can be applied "
            f"(current status: {rec.status.value})"
        )
    rec.status = RecommendationStatus.IMPLEMENTED
    rec.review_notes = (
        f"{rec.review_notes}\n[Applied by {applied_by}] {notes}".strip()
        if notes
        else f"{rec.review_notes}\n[Applied by {applied_by}]".strip()
    )
    return rec


# ── Query pattern retrieval ──────────────────────────────────


def get_query_patterns() -> list[QueryPattern]:
    """Get all tracked query patterns, sorted by frequency descending."""
    return sorted(_query_patterns.values(), key=lambda p: p.frequency, reverse=True)


# ── Feedback retrieval ───────────────────────────────────────


def get_feedback_summary() -> dict:
    """Get a summary of all recorded feedback.

    Returns a dict with:
    - total_feedback: total count
    - positive_count: number of positive feedback records
    - negative_count: number of negative feedback records
    - positive_rate: ratio of positive feedback (0.0 to 1.0)
    - category_breakdown: dict of category -> count for negative feedback
    - recent: list of the 50 most recent feedback records (serialised)
    """
    total = len(_feedback_records)
    positive = sum(1 for f in _feedback_records if f.is_positive)
    negative = total - positive

    category_breakdown: dict[str, int] = {}
    for f in _feedback_records:
        if not f.is_positive and f.category is not None:
            cat = f.category.value
            category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

    recent = [
        {
            "feedback_id": f.feedback_id,
            "session_id": f.session_id,
            "is_positive": f.is_positive,
            "category": f.category.value if f.category else None,
            "domains": f.domains,
            "query_snippet": f.query_snippet,
            "recorded_at": f.recorded_at.isoformat(),
        }
        for f in reversed(_feedback_records[-50:])
    ]

    return {
        "total_feedback": total,
        "positive_count": positive,
        "negative_count": negative,
        "positive_rate": positive / total if total > 0 else 0.0,
        "category_breakdown": category_breakdown,
        "recent": recent,
    }


# ── Monthly report generation ────────────────────────────────


def generate_monthly_report(
    report_id: str,
    period: str,
    total_queries: int,
) -> MonthlyReport:
    """Generate the monthly learning pipeline summary.

    In production, this aggregates from DataFlow queries across
    AdvisorySession, UserFeedback, and trust store tables.
    """
    positive_count = sum(1 for f in _feedback_records if f.is_positive)
    total_feedback = len(_feedback_records)
    positive_rate = positive_count / total_feedback if total_feedback > 0 else 0.0

    report = MonthlyReport(
        report_id=report_id,
        period=period,
        total_queries=total_queries,
        total_feedback=total_feedback,
        positive_feedback_rate=positive_rate,
        kb_gaps_detected=get_kb_gaps(),
        routing_insights=list(_routing_insights),
        resolution_patterns_captured=len(_resolution_patterns),
        recommendations=get_recommendations(status=RecommendationStatus.PROPOSED),
    )
    _monthly_reports.append(report)
    return report


def get_monthly_reports() -> list[MonthlyReport]:
    """Get all monthly reports, most recent first."""
    return list(reversed(_monthly_reports))
