"""Admin and operations API router.

Covers regulatory update management (T040), admin dashboard data (T041),
and operational monitoring. All endpoints require owner or hr_manager role.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from hr_advisory.api.middleware.auth_middleware import require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.workflows.regulatory_updates import (
    AffectedProvision,
    RegulatoryUpdate,
    UpdateStatus,
    UpdateUrgency,
    approve_update,
    create_update,
    get_stale_provisions,
    get_staleness_summary,
    get_update,
    list_updates,
    publish_update,
    record_review,
    reject_update,
    submit_for_review,
)

_admin_dep = Depends(require_role("owner", "hr_manager"))

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Request/Response models ──────────────────────────────────


class AffectedProvisionRequest(BaseModel):
    provision_id: str
    current_text: str
    new_text: str
    change_type: str


class CreateUpdateRequest(BaseModel):
    id: str
    title: str
    description: str
    source: str
    source_url: str = ""
    urgency: str
    affected_provisions: list[AffectedProvisionRequest]
    effective_date: str  # ISO date
    domains_affected: list[str] = []
    alert_message: str = ""
    impact_summary: str = ""


class ReviewRequest(BaseModel):
    reviewer: str
    notes: str = ""


class RecordReviewRequest(BaseModel):
    provision_id: str
    reviewer: str
    next_review_date: str  # ISO date


class UpdateResponse(BaseModel):
    id: str
    title: str
    description: str
    source: str
    urgency: str
    status: str
    effective_date: str
    created_at: str
    reviewed_by: str | None = None
    published_at: str | None = None
    domains_affected: list[str] = []
    alert_message: str = ""
    impact_summary: str = ""
    affected_provisions_count: int = 0


def _to_response(update: RegulatoryUpdate) -> UpdateResponse:
    return UpdateResponse(
        id=update.id,
        title=update.title,
        description=update.description,
        source=update.source,
        urgency=update.urgency.value,
        status=update.status.value,
        effective_date=update.effective_date.isoformat(),
        created_at=update.created_at.isoformat(),
        reviewed_by=update.reviewed_by,
        published_at=update.published_at.isoformat() if update.published_at else None,
        domains_affected=update.domains_affected,
        alert_message=update.alert_message,
        impact_summary=update.impact_summary,
        affected_provisions_count=len(update.affected_provisions),
    )


# ── Regulatory Update CRUD ───────────────────────────────────


@router.post("/updates", response_model=UpdateResponse, dependencies=[_admin_dep])
async def create_regulatory_update(req: CreateUpdateRequest, current_user: dict = Depends(require_role("owner", "hr_manager"))) -> UpdateResponse:
    """Create a new regulatory update in draft status."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_update:{user_id}", max_requests=30, window_seconds=60, action_name="create regulatory update")
    provisions = [
        AffectedProvision(
            provision_id=p.provision_id,
            current_text=p.current_text,
            new_text=p.new_text,
            change_type=p.change_type,
        )
        for p in req.affected_provisions
    ]
    update = create_update(
        RegulatoryUpdate(
            id=req.id,
            title=req.title,
            description=req.description,
            source=req.source,
            source_url=req.source_url,
            urgency=UpdateUrgency(req.urgency),
            status=UpdateStatus.DRAFT,
            affected_provisions=provisions,
            effective_date=date.fromisoformat(req.effective_date),
            created_at=datetime.now(),
            created_by="admin",
            domains_affected=req.domains_affected,
            alert_message=req.alert_message,
            impact_summary=req.impact_summary,
        )
    )
    return _to_response(update)


@router.get("/updates", response_model=list[UpdateResponse], dependencies=[_admin_dep])
async def list_regulatory_updates(status: str | None = None) -> list[UpdateResponse]:
    """List regulatory updates, optionally filtered by status."""
    filter_status = UpdateStatus(status) if status else None
    updates = list_updates(filter_status)
    return [_to_response(u) for u in updates]


@router.get("/updates/{update_id}", response_model=UpdateResponse, dependencies=[_admin_dep])
async def get_regulatory_update(update_id: str) -> UpdateResponse:
    """Get a specific regulatory update."""
    update = get_update(update_id)
    if update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    return _to_response(update)


@router.post(
    "/updates/{update_id}/submit", response_model=UpdateResponse, dependencies=[_admin_dep]
)
async def submit_update_for_review(update_id: str, current_user: dict = Depends(require_role("owner", "hr_manager"))) -> UpdateResponse:
    """Submit a draft update for review."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"submit_update:{user_id}", max_requests=30, window_seconds=60, action_name="submit update for review")
    try:
        update = submit_for_review(update_id)
    except ValueError as e:
        logger.error("Failed to submit update %s for review: %s", update_id, e)
        raise HTTPException(
            status_code=400, detail="Unable to submit this update for review."
        ) from e
    return _to_response(update)


@router.post(
    "/updates/{update_id}/approve", response_model=UpdateResponse, dependencies=[_admin_dep]
)
async def approve_regulatory_update(
    update_id: str,
    req: ReviewRequest,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> UpdateResponse:
    """Approve a reviewed update (human-in-the-loop gate)."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"approve_update:{user_id}", max_requests=30, window_seconds=60, action_name="approve regulatory update")
    try:
        update = approve_update(update_id, req.reviewer, req.notes)
    except ValueError as e:
        logger.error("Failed to approve update %s: %s", update_id, e)
        raise HTTPException(
            status_code=400, detail="Unable to approve this update."
        ) from e
    return _to_response(update)


@router.post(
    "/updates/{update_id}/reject", response_model=UpdateResponse, dependencies=[_admin_dep]
)
async def reject_regulatory_update(
    update_id: str,
    req: ReviewRequest,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> UpdateResponse:
    """Reject a reviewed update."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"reject_update:{user_id}", max_requests=30, window_seconds=60, action_name="reject regulatory update")
    try:
        update = reject_update(update_id, req.reviewer, req.notes)
    except ValueError as e:
        logger.error("Failed to reject update %s: %s", update_id, e)
        raise HTTPException(
            status_code=400, detail="Unable to reject this update."
        ) from e
    return _to_response(update)


@router.post(
    "/updates/{update_id}/publish", response_model=UpdateResponse, dependencies=[_admin_dep]
)
async def publish_regulatory_update(update_id: str, current_user: dict = Depends(require_role("owner", "hr_manager"))) -> UpdateResponse:
    """Publish an approved update — updates KB, generates alerts, and sends email notifications."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"publish_update:{user_id}", max_requests=30, window_seconds=60, action_name="publish regulatory update")
    try:
        update = publish_update(update_id)
    except ValueError as e:
        logger.error("Failed to publish update %s: %s", update_id, e)
        raise HTTPException(
            status_code=400, detail="Unable to publish this update."
        ) from e

    # Send email notifications to subscribed users (non-blocking)
    try:
        from hr_advisory.api.routers.alerts import notify_users_of_alert

        await notify_users_of_alert(
            alert_title=update.title,
            alert_description=update.description,
            source=update.source,
            effective_date=update.effective_date.isoformat() if update.effective_date else "",
            domains=", ".join(update.domains_affected) if update.domains_affected else "",
        )
    except Exception as exc:
        logger.warning("Alert email notification failed (non-blocking): %s", exc)

    # Send Web Push notifications to subscribed browsers (non-blocking)
    try:
        from hr_advisory.notifications.web_push import send_push_to_all_companies

        domains_text = (
            ", ".join(update.domains_affected) if update.domains_affected else ""
        )
        push_body = update.description
        if domains_text:
            push_body = f"[{domains_text}] {push_body}"

        send_push_to_all_companies(
            title=f"Regulatory Update: {update.title}",
            body=push_body[:200],  # Truncate for notification display
            url="/alerts",
            data={"update_id": update.id},
        )
    except Exception as exc:
        logger.warning("Web Push notification failed (non-blocking): %s", exc)

    return _to_response(update)


# ── Staleness tracking ───────────────────────────────────────


@router.get("/staleness/summary", dependencies=[_admin_dep])
async def staleness_summary() -> dict[str, int]:
    """Get a summary of provision staleness status."""
    return get_staleness_summary()


@router.get("/staleness/stale", dependencies=[_admin_dep])
async def stale_provisions() -> list[dict]:
    """Get provisions past their review date."""
    records = get_stale_provisions()
    return [
        {
            "provision_id": r.provision_id,
            "last_reviewed": r.last_reviewed.isoformat(),
            "next_review_date": r.next_review_date.isoformat(),
            "reviewer": r.reviewer,
        }
        for r in records
    ]


@router.post("/staleness/review", dependencies=[_admin_dep])
async def record_provision_review(req: RecordReviewRequest, current_user: dict = Depends(require_role("owner", "hr_manager"))) -> dict:
    """Record that a provision has been reviewed."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"record_review:{user_id}", max_requests=30, window_seconds=60, action_name="record provision review")
    record = record_review(
        provision_id=req.provision_id,
        reviewer=req.reviewer,
        next_review_date=date.fromisoformat(req.next_review_date),
    )
    return {
        "provision_id": record.provision_id,
        "last_reviewed": record.last_reviewed.isoformat(),
        "next_review_date": record.next_review_date.isoformat(),
        "reviewer": record.reviewer,
    }


# ── User role management ────────────────────────────────────


class RoleUpdateRequest(BaseModel):
    role: str


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_role("owner"))])
async def update_user_role(user_id: int, req: RoleUpdateRequest, current_user: dict = Depends(require_role("owner"))) -> dict:
    """Update a user's role. Only owners can change roles.

    Valid roles: owner, hr_manager, employee.
    """
    rl_user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"update_user_role:{rl_user_id}", max_requests=30, window_seconds=60, action_name="update user role")
    valid_roles = {"owner", "hr_manager", "employee"}
    if req.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{req.role}'. Must be one of: {', '.join(sorted(valid_roles))}.",
        )

    from hr_advisory.services import dataflow_crud

    user = dataflow_crud.read("User", user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    dataflow_crud.update("User", user_id, {"role": req.role})

    return {
        "message": f"User {user_id} role updated to '{req.role}'.",
        "user_id": user_id,
        "role": req.role,
    }


# ── Platform metrics (T041) ──────────────────────────────────


@router.get("/metrics", dependencies=[_admin_dep])
async def platform_metrics() -> dict:
    """Platform metrics for the admin dashboard.

    Pulls live data from the knowledge base, regulatory update store,
    and learning pipeline.
    """
    from hr_advisory.kb.admin import get_kb_stats
    from hr_advisory.trust.learning_pipeline import (
        _feedback_records,
        _query_patterns,
        _recommendations,
        get_kb_gaps,
    )

    # KB statistics (live from DataFlow)
    try:
        kb_stats = get_kb_stats()
    except Exception:
        kb_stats = {}

    # Learning pipeline statistics
    total_queries = sum(p.frequency for p in _query_patterns.values())
    patterns_with_confidence = [p for p in _query_patterns.values() if p.avg_confidence > 0]
    avg_confidence = (
        sum(p.avg_confidence for p in patterns_with_confidence) / len(patterns_with_confidence)
        if patterns_with_confidence
        else 0.0
    )

    # Risk distribution from query patterns
    risk_counts = {"green": 0, "amber": 0, "red": 0}
    for pattern in _query_patterns.values():
        tier = pattern.pattern_id.split(":")[-1] if ":" in pattern.pattern_id else "green"
        if tier in risk_counts:
            risk_counts[tier] += pattern.frequency

    return {
        "queries_tracked": total_queries,
        "avg_confidence": round(avg_confidence, 3),
        "risk_distribution": risk_counts,
        "kb_provisions": kb_stats.get("provisions", 0),
        "kb_acts": kb_stats.get("acts", 0),
        "kb_domains": kb_stats.get("domains", 0),
        "kb_gaps": len(get_kb_gaps()),
        "feedback_count": len(_feedback_records),
        "pending_recommendations": len(
            [r for r in _recommendations.values() if r.status.value == "proposed"]
        ),
        "pending_updates": len(list_updates(UpdateStatus.IN_REVIEW)),
        "published_updates": len(list_updates(UpdateStatus.PUBLISHED)),
    }
