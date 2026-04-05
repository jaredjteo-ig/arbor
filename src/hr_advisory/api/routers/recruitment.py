"""Recruitment management endpoints.

Handles job listings, candidates, interview scheduling,
interviewer feedback, offer generation, and hire conversion.
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

router = APIRouter()

# Input length limits
MAX_TEXT_LENGTH = 2000
MAX_NAME_LENGTH = 200


def _validate_text_length(value: str, field_name: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    """Validate text input to maximum length."""
    if value and len(value) > max_len:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {max_len} characters.",
        )
    return value


def _verify_job_ownership(job_id: int, company_id: int) -> dict:
    """Load a job listing and verify tenant ownership. Raises 404 on failure."""
    job = dataflow_crud.read("JobListing", job_id)
    if not job or job.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    return job


def _verify_candidate_ownership(candidate_id: int, company_id: int) -> dict:
    """Load a candidate and verify tenant ownership. Raises 404 on failure."""
    candidate = dataflow_crud.read("Candidate", candidate_id)
    if not candidate or candidate.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate


# --------------------------------------------------------------------------
# Job listings
# --------------------------------------------------------------------------


@router.get("/jobs")
async def list_jobs(
    status: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all job listings for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status

    jobs = dataflow_crud.list_records("JobListing", filters)
    return {"jobs": jobs, "count": len(jobs)}


@router.post("/jobs")
async def create_job(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new job listing."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Job title is required.")

    _validate_text_length(title, "title", MAX_NAME_LENGTH)
    _validate_text_length(body.get("description", ""), "description")
    _validate_text_length(body.get("notes", ""), "notes")

    job = dataflow_crud.create("JobListing",
        {
            "company_id": company_id,
            "title": title,
            "description": body.get("description", ""),
            "department": body.get("department", ""),
            "location": body.get("location", ""),
            "employment_type": body.get("employment_type", "full_time"),
            "salary_range_min": body.get("salary_range_min"),
            "salary_range_max": body.get("salary_range_max"),
            "requirements": body.get("requirements", []),
            "status": "draft",
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"job": job}


@router.patch("/jobs/{job_id}")
async def update_job(
    job_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a job listing."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_job_ownership(job_id, company_id)

    body = await request.json()
    allowed = {
        "title",
        "description",
        "department",
        "location",
        "employment_type",
        "salary_range_min",
        "salary_range_max",
        "requirements",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("JobListing", job_id, updates)
    return {"job": result}


@router.post("/jobs/{job_id}/publish")
async def publish_job(
    job_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Publish a job listing, making it visible to applicants."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    job = _verify_job_ownership(job_id, company_id)
    if job.get("status") not in ("draft",):
        raise HTTPException(status_code=400, detail="Only draft jobs can be published.")

    result = dataflow_crud.update("JobListing",
        job_id,
        {
            "status": "open",
            "is_published": True,
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"job": result, "detail": "Job published."}


@router.post("/jobs/{job_id}/close")
async def close_job(
    job_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Close a job listing."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    job = _verify_job_ownership(job_id, company_id)
    if job.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Job is already closed.")

    result = dataflow_crud.update("JobListing",
        job_id,
        {
            "status": "closed",
            "closed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"job": result, "detail": "Job closed."}


# --------------------------------------------------------------------------
# Candidates (cross-job)
# --------------------------------------------------------------------------


@router.get("/candidates")
async def list_all_candidates(
    stage: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List ALL candidates across all job listings for the company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if stage:
        filters["stage"] = stage

    candidates = dataflow_crud.list_records("Candidate", filters)
    return {"candidates": candidates, "count": len(candidates)}


# --------------------------------------------------------------------------
# Interviews (cross-candidate)
# --------------------------------------------------------------------------


@router.get("/interviews")
async def list_all_interviews(
    status: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List ALL interviews across all candidates for the company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status

    interviews = dataflow_crud.list_records("InterviewSchedule", filters)
    return {"interviews": interviews, "count": len(interviews)}


# --------------------------------------------------------------------------
# Candidates (per-job)
# --------------------------------------------------------------------------


@router.get("/jobs/{job_id}/candidates")
async def list_candidates(
    job_id: int,
    stage: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List candidates for a job listing."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_job_ownership(job_id, company_id)

    filters: dict = {"job_listing_id": job_id}
    if stage:
        filters["stage"] = stage

    candidates = dataflow_crud.list_records("Candidate", filters)
    return {"candidates": candidates, "count": len(candidates)}


@router.post("/jobs/{job_id}/candidates")
async def add_candidate(
    job_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add a candidate to a job listing (direct or application)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_job_ownership(job_id, company_id)

    body = await request.json()
    name = body.get("name", "").strip()
    email = body.get("email", "").strip()
    if not name or not email:
        raise HTTPException(status_code=400, detail="name and email are required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("notes", ""), "notes")

    # Check for duplicate candidate on same job
    existing = dataflow_crud.list_records("Candidate",
        {"job_listing_id": job_id, "email": email},
        limit=1,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Candidate already exists for this job.")

    candidate = dataflow_crud.create("Candidate",
        {
            "company_id": company_id,
            "job_listing_id": job_id,
            "name": name,
            "email": email,
            "phone": body.get("phone", ""),
            "source": body.get("source", "direct"),
            "resume_url": body.get("resume_url", ""),
            "notes": body.get("notes", ""),
            "stage": "applied",
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"candidate": candidate}


@router.patch("/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update candidate details (stage change, notes, etc.)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_candidate_ownership(candidate_id, company_id)

    body = await request.json()
    allowed = {"name", "email", "phone", "notes", "resume_url", "source"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("Candidate", candidate_id, updates)
    return {"candidate": result}


# --------------------------------------------------------------------------
# Interviews
# --------------------------------------------------------------------------


@router.post("/candidates/{candidate_id}/interviews")
async def schedule_interview(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Schedule an interview for a candidate."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_candidate_ownership(candidate_id, company_id)

    body = await request.json()
    scheduled_at = body.get("scheduled_at", "")
    if not scheduled_at:
        raise HTTPException(status_code=400, detail="scheduled_at is required.")

    interview = dataflow_crud.create("Interview",
        {
            "company_id": company_id,
            "candidate_id": candidate_id,
            "scheduled_at": scheduled_at,
            "duration_minutes": body.get("duration_minutes", 60),
            "interview_type": body.get("interview_type", "in_person"),
            "location": body.get("location", ""),
            "interviewers": body.get("interviewers", []),
            "notes": body.get("notes", ""),
            "status": "scheduled",
            "created_by": int(current_user.get("sub", 0)),
        },
    )

    # Move candidate to interview stage if not already there
    dataflow_crud.update("Candidate",
        candidate_id,
        {"stage": "interview", "updated_at": datetime.now(timezone.utc).isoformat()},
    )

    return {"interview": interview}


@router.get("/candidates/{candidate_id}/interviews")
async def list_interviews(
    candidate_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all interviews for a candidate."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_candidate_ownership(candidate_id, company_id)

    interviews = dataflow_crud.list_records("InterviewSchedule", {"candidate_id": candidate_id})
    return {"interviews": interviews, "count": len(interviews)}


@router.patch("/interviews/{interview_id}")
async def update_interview(
    interview_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an interview (reschedule, change status, etc.)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("Interview", interview_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Interview not found.")

    body = await request.json()
    allowed = {
        "scheduled_at",
        "duration_minutes",
        "interview_type",
        "location",
        "interviewers",
        "notes",
        "status",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("Interview", interview_id, updates)
    return {"interview": result}


# --------------------------------------------------------------------------
# Feedback
# --------------------------------------------------------------------------


@router.post("/interviews/{interview_id}/feedback")
async def add_feedback(
    interview_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Add interviewer feedback for an interview."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("Interview", interview_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Interview not found.")

    body = await request.json()
    rating = body.get("rating")
    if rating is None:
        raise HTTPException(status_code=400, detail="rating is required.")

    feedback = dataflow_crud.create("InterviewFeedback",
        {
            "company_id": company_id,
            "interview_id": interview_id,
            "candidate_id": existing.get("candidate_id"),
            "interviewer_id": int(current_user.get("sub", 0)),
            "rating": rating,
            "strengths": body.get("strengths", ""),
            "weaknesses": body.get("weaknesses", ""),
            "comments": body.get("comments", ""),
            "recommendation": body.get("recommendation", ""),
        },
    )
    return {"feedback": feedback}


@router.get("/candidates/{candidate_id}/feedback")
async def list_candidate_feedback(
    candidate_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all interview feedback for a candidate."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_candidate_ownership(candidate_id, company_id)

    feedback = dataflow_crud.list_records("InterviewFeedback", {"candidate_id": candidate_id})
    return {"feedback": feedback, "count": len(feedback)}


# --------------------------------------------------------------------------
# Offer & hire
# --------------------------------------------------------------------------


@router.post("/candidates/{candidate_id}/offer")
async def generate_offer(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate an offer for a candidate. Changes stage to 'offered'."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    candidate = _verify_candidate_ownership(candidate_id, company_id)

    body = await request.json()
    salary = body.get("salary")
    start_date = body.get("start_date", "")
    if salary is None or not start_date:
        raise HTTPException(status_code=400, detail="salary and start_date are required.")

    salary = float(salary)
    if not math.isfinite(salary):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")

    offer = dataflow_crud.create("Offer",
        {
            "company_id": company_id,
            "candidate_id": candidate_id,
            "job_listing_id": candidate.get("job_listing_id"),
            "salary": salary,
            "start_date": start_date,
            "position_title": body.get("position_title", ""),
            "employment_type": body.get("employment_type", "full_time"),
            "benefits": body.get("benefits", ""),
            "notes": body.get("notes", ""),
            "status": "pending",
            "created_by": int(current_user.get("sub", 0)),
        },
    )

    dataflow_crud.update("Candidate",
        candidate_id,
        {"stage": "offered", "updated_at": datetime.now(timezone.utc).isoformat()},
    )

    return {"offer": offer, "detail": "Offer generated."}


@router.post("/candidates/{candidate_id}/hire")
async def hire_candidate(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Convert a candidate to an employee.

    Creates an invitation for the new hire to join the platform.
    Changes candidate stage to 'hired'.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"hire:{company_id}", max_requests=10, window_seconds=3600, action_name="hiring candidates"
    )

    candidate = _verify_candidate_ownership(candidate_id, company_id)
    if candidate.get("stage") not in ("offered",):
        raise HTTPException(status_code=400, detail="Candidate must be in 'offered' stage to hire.")

    body = await request.json()
    actor_id = int(current_user.get("sub", 0))

    # Create invitation for the new hire
    import secrets

    token = secrets.token_urlsafe(32)
    invitation = dataflow_crud.create("Invitation",
        {
            "company_id": company_id,
            "email": candidate.get("email"),
            "name": candidate.get("name"),
            "role": body.get("role", "employee"),
            "token": token,
            "invited_by": actor_id,
            "status": "pending",
        },
    )

    # Update candidate stage
    dataflow_crud.update("Candidate",
        candidate_id,
        {
            "stage": "hired",
            "hired_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "detail": "Candidate hired. Invitation created.",
        "candidate_id": candidate_id,
    }
