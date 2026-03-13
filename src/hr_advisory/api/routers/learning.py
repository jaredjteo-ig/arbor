"""Learning Pipeline API endpoints — COC Layer 5.

Exposes the learning pipeline for:
- Submitting user feedback (authenticated users)
- Querying detected KB gaps (authenticated users)
- Viewing/reviewing improvement recommendations
- Generating and viewing monthly reports

Admin endpoints (under /admin/) provide elevated access for:
- KB gap viewing with suggested provisions
- Recommendation listing, review, and application
- Query pattern summaries
- Feedback summaries with category breakdowns
- Latest monthly report access
- Admin-initiated feedback recording
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.trust.learning_pipeline import (
    FeedbackCategory,
    RecommendationStatus,
    apply_recommendation,
    generate_monthly_report,
    get_feedback_summary,
    get_kb_gaps,
    get_monthly_reports,
    get_query_patterns,
    get_recommendations,
    record_feedback,
    review_recommendation,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/feedback")
async def submit_feedback(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit feedback on an advisory response.

    Accepts thumbs-up/thumbs-down with optional categorisation.
    Feeds into the learning pipeline for KB improvement.
    """
    body = await request.json()
    session_id = body.get("session_id", "") or str(uuid.uuid4())
    is_positive = body.get("is_positive", True)
    category_str = body.get("category")
    domains = body.get("domains", [])
    query_snippet = body.get("query_snippet", "")

    category = None
    if category_str:
        try:
            category = FeedbackCategory(category_str)
        except ValueError:
            valid = [c.value for c in FeedbackCategory]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Valid values: {valid}",
            )

    feedback_id = str(uuid.uuid4())
    record = record_feedback(
        feedback_id=feedback_id,
        session_id=session_id,
        is_positive=is_positive,
        category=category,
        domains=domains,
        query_snippet=query_snippet,
    )

    return {
        "feedback_id": record.feedback_id,
        "recorded": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/gaps")
async def list_kb_gaps(
    priority: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List detected knowledge base gaps.

    Optionally filter by priority: critical, high, medium, low.
    """
    valid_priorities = {"critical", "high", "medium", "low"}
    if priority and priority not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority. Valid values: {sorted(valid_priorities)}",
        )

    gaps = get_kb_gaps(priority=priority)
    return {
        "gaps": [
            {
                "gap_id": g.gap_id,
                "domains": g.domains,
                "description": g.description,
                "evidence_query_count": g.evidence_query_count,
                "avg_confidence": g.avg_confidence_when_hit,
                "negative_feedback_count": g.negative_feedback_count,
                "priority": g.priority,
                "detected_at": g.detected_at.isoformat(),
            }
            for g in gaps
        ],
        "total": len(gaps),
    }


@router.get("/recommendations")
async def list_recommendations(
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List improvement recommendations from the learning pipeline."""
    filter_status = None
    if status:
        try:
            filter_status = RecommendationStatus(status)
        except ValueError:
            valid = [s.value for s in RecommendationStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {valid}",
            )

    recs = get_recommendations(status=filter_status)
    return {
        "recommendations": [
            {
                "recommendation_id": r.recommendation_id,
                "type": r.rec_type.value,
                "title": r.title,
                "description": r.description,
                "priority": r.priority,
                "evidence_count": r.evidence_count,
                "affected_domains": r.affected_domains,
                "status": r.status.value,
                "proposed_at": r.proposed_at.isoformat(),
            }
            for r in recs
        ],
        "total": len(recs),
    }


@router.post("/recommendations/{recommendation_id}/review")
async def review_recommendation_endpoint(
    recommendation_id: str,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Review (approve/reject) an improvement recommendation.

    Only admin users can approve or reject recommendations.
    This is the human-on-the-loop gate for learning pipeline changes.
    """
    body = await request.json()
    approved = body.get("approved")
    notes = body.get("notes", "")

    if approved is None:
        raise HTTPException(status_code=400, detail="'approved' field is required (true/false)")

    reviewer = current_user.get("email", current_user.get("id", "unknown"))

    try:
        rec = review_recommendation(
            recommendation_id=recommendation_id,
            approved=approved,
            reviewed_by=reviewer,
            notes=notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "recommendation_id": rec.recommendation_id,
        "status": rec.status.value,
        "reviewed_by": rec.reviewed_by,
        "reviewed_at": rec.reviewed_at.isoformat() if rec.reviewed_at else None,
        "review_notes": rec.review_notes,
    }


@router.get("/reports")
async def list_reports(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List monthly learning pipeline reports.

    Only admin users can view aggregated learning reports.
    """
    reports = get_monthly_reports()
    return {
        "reports": [
            {
                "report_id": r.report_id,
                "period": r.period,
                "total_queries": r.total_queries,
                "total_feedback": r.total_feedback,
                "positive_feedback_rate": round(r.positive_feedback_rate, 3),
                "kb_gaps_count": len(r.kb_gaps_detected),
                "recommendations_count": len(r.recommendations),
                "generated_at": r.generated_at.isoformat(),
            }
            for r in reports
        ],
        "total": len(reports),
    }


@router.post("/reports/generate")
async def generate_report(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate a monthly learning pipeline report.

    Aggregates feedback, KB gaps, routing insights, and recommendations
    into a summary for human expert review.
    """
    body = await request.json()
    period = body.get("period", datetime.now(timezone.utc).strftime("%Y-%m"))
    total_queries = body.get("total_queries", 0)

    report_id = str(uuid.uuid4())
    report = generate_monthly_report(
        report_id=report_id,
        period=period,
        total_queries=total_queries,
    )

    return {
        "report_id": report.report_id,
        "period": report.period,
        "total_queries": report.total_queries,
        "total_feedback": report.total_feedback,
        "positive_feedback_rate": round(report.positive_feedback_rate, 3),
        "kb_gaps_count": len(report.kb_gaps_detected),
        "routing_insights_count": len(report.routing_insights),
        "resolution_patterns_count": report.resolution_patterns_captured,
        "recommendations_count": len(report.recommendations),
        "generated_at": report.generated_at.isoformat(),
    }


# ── Admin endpoints ─────────────────────────────────────────
# All endpoints below require owner or hr_manager role.

_admin_dep = Depends(require_role("owner", "hr_manager"))


@router.get("/admin/gaps", dependencies=[_admin_dep])
async def admin_list_kb_gaps(
    priority: str | None = None,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List detected KB gaps (admin view with suggested provisions).

    Optionally filter by priority: critical, high, medium, low.
    Requires owner or hr_manager role.
    """
    valid_priorities = {"critical", "high", "medium", "low"}
    if priority and priority not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority. Valid values: {sorted(valid_priorities)}",
        )

    gaps = get_kb_gaps(priority=priority)
    return {
        "gaps": [
            {
                "gap_id": g.gap_id,
                "domains": g.domains,
                "description": g.description,
                "evidence_query_count": g.evidence_query_count,
                "avg_confidence": g.avg_confidence_when_hit,
                "negative_feedback_count": g.negative_feedback_count,
                "suggested_provisions": g.suggested_provisions,
                "priority": g.priority,
                "detected_at": g.detected_at.isoformat(),
            }
            for g in gaps
        ],
        "total": len(gaps),
    }


@router.get("/admin/recommendations", dependencies=[_admin_dep])
async def admin_list_recommendations(
    status: str | None = None,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List improvement recommendations (admin view).

    Optionally filter by status: proposed, under_review, approved, rejected, implemented.
    Requires owner or hr_manager role.
    """
    filter_status = None
    if status:
        try:
            filter_status = RecommendationStatus(status)
        except ValueError:
            valid = [s.value for s in RecommendationStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {valid}",
            )

    recs = get_recommendations(status=filter_status)
    return {
        "recommendations": [
            {
                "recommendation_id": r.recommendation_id,
                "type": r.rec_type.value,
                "title": r.title,
                "description": r.description,
                "priority": r.priority,
                "evidence_count": r.evidence_count,
                "affected_domains": r.affected_domains,
                "status": r.status.value,
                "proposed_at": r.proposed_at.isoformat(),
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            }
            for r in recs
        ],
        "total": len(recs),
    }


@router.post("/admin/recommendations/{recommendation_id}/apply", dependencies=[_admin_dep])
async def admin_apply_recommendation(
    recommendation_id: str,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Apply an approved recommendation, marking it as IMPLEMENTED.

    Only recommendations with APPROVED status can be applied.
    This is the human-on-the-loop action gate: an approved change
    is executed and recorded in the trust audit trail.

    Requires owner or hr_manager role.
    """
    body = await request.json()
    notes = body.get("notes", "")
    applied_by = current_user.get("email", current_user.get("id", "unknown"))

    try:
        rec = apply_recommendation(
            recommendation_id=recommendation_id,
            applied_by=applied_by,
            notes=notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Recommendation %s applied by %s",
        recommendation_id,
        applied_by,
    )

    return {
        "recommendation_id": rec.recommendation_id,
        "status": rec.status.value,
        "applied": True,
        "applied_by": applied_by,
        "review_notes": rec.review_notes,
    }


@router.get("/admin/patterns", dependencies=[_admin_dep])
async def admin_list_query_patterns(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List tracked query patterns sorted by frequency.

    Shows which query types are most common, their confidence and
    satisfaction scores, and example queries. Used for understanding
    platform usage and identifying areas for improvement.

    Requires owner or hr_manager role.
    """
    patterns = get_query_patterns()
    return {
        "patterns": [
            {
                "pattern_id": p.pattern_id,
                "description": p.description,
                "domains": p.domains,
                "frequency": p.frequency,
                "avg_confidence": round(p.avg_confidence, 3),
                "avg_satisfaction": round(p.avg_satisfaction, 3),
                "first_seen": p.first_seen.isoformat(),
                "last_seen": p.last_seen.isoformat(),
                "example_queries": p.example_queries,
            }
            for p in patterns
        ],
        "total": len(patterns),
    }


@router.get("/admin/feedback", dependencies=[_admin_dep])
async def admin_feedback_summary(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a summary of all recorded feedback.

    Returns aggregate counts, positive/negative rates, category breakdowns,
    and the most recent feedback records.

    Requires owner or hr_manager role.
    """
    return get_feedback_summary()


@router.get("/admin/report", dependencies=[_admin_dep])
async def admin_latest_report(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the latest monthly learning pipeline report.

    Returns the most recently generated report. Returns an empty
    placeholder if no reports have been generated yet.

    Requires owner or hr_manager role.
    """
    reports = get_monthly_reports()
    if not reports:
        return {
            "report_id": None,
            "period": None,
            "total_queries": 0,
            "total_feedback": 0,
            "positive_feedback_rate": 0.0,
            "kb_gaps_count": 0,
            "routing_insights_count": 0,
            "resolution_patterns_count": 0,
            "recommendations_count": 0,
            "generated_at": None,
            "empty": True,
        }

    report = reports[0]  # Most recent (already sorted by get_monthly_reports)
    return {
        "report_id": report.report_id,
        "period": report.period,
        "total_queries": report.total_queries,
        "total_feedback": report.total_feedback,
        "positive_feedback_rate": round(report.positive_feedback_rate, 3),
        "kb_gaps_count": len(report.kb_gaps_detected),
        "routing_insights_count": len(report.routing_insights),
        "resolution_patterns_count": report.resolution_patterns_captured,
        "recommendations_count": len(report.recommendations),
        "generated_at": report.generated_at.isoformat(),
    }


@router.post("/admin/feedback", dependencies=[_admin_dep])
async def admin_record_feedback(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Record feedback via admin endpoint.

    Accepts the same payload as /feedback but requires admin role.
    Used for administrative feedback recording (e.g., from support tickets).

    Requires owner or hr_manager role.
    """
    body = await request.json()
    session_id = body.get("session_id", "") or str(uuid.uuid4())
    is_positive = body.get("is_positive", True)
    category_str = body.get("category")
    domains = body.get("domains", [])
    query_snippet = body.get("query_snippet", "")

    category = None
    if category_str:
        try:
            category = FeedbackCategory(category_str)
        except ValueError:
            valid = [c.value for c in FeedbackCategory]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Valid values: {valid}",
            )

    feedback_id = str(uuid.uuid4())
    record = record_feedback(
        feedback_id=feedback_id,
        session_id=session_id,
        is_positive=is_positive,
        category=category,
        domains=domains,
        query_snippet=query_snippet,
    )

    logger.info(
        "Admin feedback recorded: %s (positive=%s, category=%s)",
        feedback_id,
        is_positive,
        category_str,
    )

    return {
        "feedback_id": record.feedback_id,
        "recorded": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
