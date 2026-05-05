"""Recruitment management endpoints.

Handles job listings, candidates, interview scheduling,
interviewer feedback, offer generation, hire conversion,
resume upload/download, and automated recruitment emails.
"""

import json
import logging
import math
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import FileResponse

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.integrations.google_calendar import sync as gcal_sync
from hr_advisory.mcp_servers.adapters.resend_email import ResendAdapter
from hr_advisory.services import dataflow_crud
from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

logger = logging.getLogger(__name__)

router = APIRouter()


# Roles that may be assigned via the candidate→hire flow. Owners and platform
# admins are intentionally excluded — those positions are not filled through
# recruitment. Anything outside this set is rejected at hire time and again
# defensively when the new hire accepts their invitation (auth.py).
HIRABLE_ROLES: frozenset[str] = frozenset({"employee", "hr_manager"})


# S3-T4: per-company AI-scorecard quota. Counted per calendar month. The
# soft cap surfaces a warning in the response so the customer sees the
# upgrade tier; the hard cap returns 429 to protect platform cost.
SCORECARD_SOFT_CAP: int = int(os.environ.get("SCORECARD_SOFT_CAP", "50"))
SCORECARD_HARD_CAP: int = int(os.environ.get("SCORECARD_HARD_CAP", "500"))


def _scorecard_quota_check(company_id: int) -> tuple[datetime, int, str]:
    """Return (month_start, count_so_far, state) for the company's scorecard
    quota in the current calendar month.

    state is one of:
      - "ok": below soft cap
      - "soft_warning": ≥ soft cap, < hard cap (caller continues, response
        gets a `quota_warning` field)
      - "exhausted": ≥ hard cap (caller raises 429)

    Counts use ScorecardEntry rows tagged is_ai_generated=True. Older
    deployments without the is_ai_generated column degrade gracefully —
    the count returns 0 (best-effort), which is the safe behaviour:
    customers without the AI column are pre-feature-flag and shouldn't
    be billed against the cap.
    """
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    try:
        rows = dataflow_crud.list_records(
            "ScorecardEntry",
            {"company_id": company_id, "is_ai_generated": True},
            limit=10000,
        )
    except Exception as exc:  # noqa: BLE001 — schema may lack is_ai_generated
        logger.debug(
            "Scorecard quota count fell back to 0 (schema missing AI column): %s",
            type(exc).__name__,
        )
        return month_start, 0, "ok"

    count = 0
    for row in rows:
        created = row.get("created_at")
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                continue
        if not isinstance(created, datetime):
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created >= month_start:
            count += 1

    if count >= SCORECARD_HARD_CAP:
        return month_start, count, "exhausted"
    if count >= SCORECARD_SOFT_CAP:
        return month_start, count, "soft_warning"
    return month_start, count, "ok"


# --------------------------------------------------------------------------
# Recruitment email helper (T-R018)
# --------------------------------------------------------------------------


async def _send_recruitment_email(
    to: str,
    template_name: str,
    variables: dict,
) -> bool:
    """Send a recruitment email. Returns True on success, False on failure.

    Never raises — email delivery must not block recruitment operations.
    """
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.debug("RESEND_API_KEY not configured — skipping recruitment email")
        return False

    try:
        template = RECRUITMENT_TEMPLATES.get(template_name)
        if not template:
            logger.warning("Unknown recruitment email template: %s", template_name)
            return False

        from html import escape as html_escape
        safe_vars = {k: html_escape(str(v)) for k, v in variables.items()}
        subject = template["subject"].format(**variables)  # Subject is plain text, no escaping
        html = template["html"].format(**safe_vars)

        adapter = ResendAdapter(api_key=api_key)
        await adapter.send_email(to=to, subject=subject, html_body=html)
        to_masked = to[:3] + "***" + to[to.index("@"):] if "@" in to else "***"
        logger.info("Recruitment email sent: template=%s, to=%s", template_name, to_masked)
        return True
    except Exception as exc:
        logger.warning("Failed to send recruitment email: %s", exc)
        return False

# Upload directory for recruitment resumes
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.getcwd(), "uploads", "documents"))
RECRUITMENT_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "recruitment")

# Resume upload constraints
MAX_RESUME_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}

# Magic byte signatures for file type verification
_MAGIC_BYTES = {
    "application/pdf": (b"%PDF", 4),
    "image/jpeg": (b"\xff\xd8\xff", 3),
    "image/png": (b"\x89PNG", 4),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04", 4),
    "application/msword": (b"\xd0\xcf\x11\xe0", 4),
}

# Extension to MIME type mapping for download responses
_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# Input length limits
MAX_TEXT_LENGTH = 2000
MAX_NAME_LENGTH = 200

# Email format regex for input validation
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


from hr_advisory.api.routers._helpers import _validate_text_length  # noqa: E402


# --------------------------------------------------------------------------
# DataFlow helpers
# --------------------------------------------------------------------------


def _verify_job_ownership(job_id: int, company_id: int) -> dict:
    """Load a job listing and verify tenant ownership. Raises 404 on failure.

    Uses list_records + filter rather than dataflow_crud.read() because
    the underlying express_sync.read() returns None for valid integer-PK
    rows on PostgreSQL — a DataFlow-layer bug that historically caused
    every recruitment endpoint depending on this helper to 404. The
    list_records path is consistent with the rest of recruitment.py.
    """
    rows = dataflow_crud.list_records(
        "JobListing", {"id": job_id, "company_id": company_id}
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    return rows[0]


def _verify_candidate_ownership(candidate_id: int, company_id: int) -> dict:
    """Load a candidate and verify tenant ownership. Raises 404 on failure.

    Same workaround as _verify_job_ownership — list_records sidesteps
    the broken dataflow_crud.read().
    """
    rows = dataflow_crud.list_records(
        "Candidate", {"id": candidate_id, "company_id": company_id}
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return rows[0]


# T-RX10: Allowed candidate stage transitions.
# Each key lists the destination stages that are valid from the source stage.
# "hired", "rejected" and "withdrawn" are terminal.
_VALID_STAGE_TRANSITIONS: dict[str, set[str]] = {
    "new": {"new", "screening", "rejected", "withdrawn"},
    "screening": {"screening", "interview", "rejected", "withdrawn"},
    "interview": {"interview", "assessment", "offered", "rejected", "withdrawn"},
    "assessment": {"assessment", "offered", "rejected", "withdrawn"},
    "offered": {"offered", "hired", "rejected", "withdrawn"},
    "hired": {"hired"},
    "rejected": {"rejected"},
    "withdrawn": {"withdrawn"},
}


def _validate_stage_transition(old: str, new: str) -> None:
    """Reject invalid candidate-stage transitions with a 400.

    A no-op transition (old == new) is always allowed. Unknown old stages
    fall through to a permissive check so legacy records aren't bricked.
    """
    if not new:
        return
    if old == new:
        return
    allowed = _VALID_STAGE_TRANSITIONS.get(old)
    if allowed is None:
        # Unknown source stage — log and allow so we don't break legacy data.
        logger.warning("Unknown source stage %r for transition validation", old)
        return
    if new not in allowed:
        terminal = old in {"hired", "rejected", "withdrawn"}
        if terminal:
            detail = (
                f"Cannot move candidate from terminal stage '{old}'. "
                f"Re-apply via the talent pool to start a new pipeline."
            )
        else:
            allowed_str = ", ".join(sorted(allowed - {old}))
            detail = (
                f"Invalid stage transition '{old}' -> '{new}'. "
                f"Allowed next stages: {allowed_str}."
            )
        raise HTTPException(status_code=400, detail=detail)


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int]:
    """Slice a list for pagination. Returns (page_items, total)."""
    total = len(items)
    offset = (page - 1) * page_size
    return items[offset : offset + page_size], total


def _log_candidate_activity(candidate_id: int, action: str, actor_id: int, details: str = "") -> None:
    """Append an activity entry to the candidate's notes for audit trail.

    T-R026: Each entry is timestamped and prepended to existing notes so the
    most recent activity appears first.

    S2-T5: also append to the immutable hash-chained audit log so a
    candidate-record rewrite (e.g., a buggy admin tool that overwrites
    `notes`) is independently detectable. Failure to write the chain
    entry is logged but does not block the mutable update.
    """
    candidate = dataflow_crud.read("Candidate", candidate_id)
    if not candidate:
        return
    existing_notes = candidate.get("notes", "")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"[{timestamp}] {action}"
    if details:
        entry += f" — {details}"
    new_notes = f"{entry}\n{existing_notes}" if existing_notes else entry
    dataflow_crud.update("Candidate", candidate_id, {"notes": new_notes})

    # S2-T5: dual-write to the immutable audit log
    try:
        from hr_advisory.services import audit_log as _audit_log

        company_id = candidate.get("company_id")
        if company_id:
            event_key = (
                "candidate."
                + action.lower().replace(" ", "_").replace("changed_to_", "stage_")
            )
            _audit_log.record_event(
                company_id=int(company_id),
                actor_id=int(actor_id) if actor_id else 0,
                event_type=event_key,
                payload={
                    "candidate_id": candidate_id,
                    "action": action,
                    "details": details,
                },
            )
    except Exception as exc:
        logger.warning(
            "AuditLogEntry append failed for candidate %s action=%s: %s",
            candidate_id,
            action,
            exc,
        )


# --------------------------------------------------------------------------
# Job listings
# --------------------------------------------------------------------------


@router.get("/jobs")
async def list_jobs(
    status: str | None = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all job listings for the current company.

    T-RX09: paginated. ``items`` contains the current page only. Each row
    is enriched with `candidate_count` (live count of candidates assigned
    to that job) so the dashboard doesn't have to issue N+1 lookups.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status

    jobs = dataflow_crud.list_records("JobListing", filters)

    # Bulk-fetch candidates once per company, group by job_listing_id.
    # Single query beats per-job lookups on the dashboard.
    try:
        all_candidates = dataflow_crud.list_records(
            "Candidate", {"company_id": company_id}
        )
        count_by_job: dict[int, int] = {}
        for cand in all_candidates:
            jid = cand.get("job_listing_id")
            if jid:
                count_by_job[jid] = count_by_job.get(jid, 0) + 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("Job candidate-count enrichment failed: %s", exc)
        count_by_job = {}

    enriched_jobs = []
    for job in jobs:
        out = dict(job)
        out["candidate_count"] = count_by_job.get(job.get("id"), 0)
        enriched_jobs.append(out)

    page_items, total = _paginate(enriched_jobs, page, page_size)
    return {
        "jobs": page_items,
        "items": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


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

    salary_min = body.get("salary_range_min")
    salary_max = body.get("salary_range_max")
    if salary_min is not None:
        salary_min = float(salary_min)
        if not math.isfinite(salary_min) or salary_min < 0:
            raise HTTPException(status_code=400, detail="Invalid salary_range_min: must be a finite non-negative number.")
    if salary_max is not None:
        salary_max = float(salary_max)
        if not math.isfinite(salary_max) or salary_max < 0:
            raise HTTPException(status_code=400, detail="Invalid salary_range_max: must be a finite non-negative number.")
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise HTTPException(status_code=400, detail="salary_range_min cannot exceed salary_range_max.")

    job = dataflow_crud.create(
        "JobListing",
        {
            "company_id": company_id,
            "title": title,
            "description": body.get("description", ""),
            "department": body.get("department", ""),
            "location": body.get("location", ""),
            "employment_type": body.get("employment_type", "full_time"),
            "salary_range_min": salary_min,
            "salary_range_max": salary_max,
            "requirements": body.get("requirements", ""),
            "status": "draft",
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"job": job}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a single job listing by ID."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    job = _verify_job_ownership(job_id, company_id)
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

    # H5: Validate salary fields with math.isfinite() to prevent NaN/Inf bypass
    if "salary_range_min" in updates:
        val = float(updates["salary_range_min"])
        if not math.isfinite(val) or val < 0:
            raise HTTPException(status_code=400, detail="Invalid salary_range_min: must be a finite non-negative number.")
        updates["salary_range_min"] = val
    if "salary_range_max" in updates:
        val = float(updates["salary_range_max"])
        if not math.isfinite(val) or val < 0:
            raise HTTPException(status_code=400, detail="Invalid salary_range_max: must be a finite non-negative number.")
        updates["salary_range_max"] = val
    if "salary_range_min" in updates and "salary_range_max" in updates:
        if updates["salary_range_min"] > updates["salary_range_max"]:
            raise HTTPException(status_code=400, detail="salary_range_min cannot exceed salary_range_max.")

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

    result = dataflow_crud.update(
        "JobListing",
        job_id,
        {
            "status": "open",
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"job": result, "detail": "Job published."}


@router.post("/jobs/{job_id}/close")
async def close_job(
    job_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Close a job listing.

    T-RX11: cascading effects on close
      - Active candidates (stage in new/screening/interview/assessment) are
        moved to "withdrawn" with rejection_reason="job_closed".
      - Pending offers (status in draft/pending_approval/approved/sent) are
        marked "expired".
      - One audit-trail entry per affected candidate is appended.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    job = _verify_job_ownership(job_id, company_id)
    if job.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Job is already closed.")

    actor_id = int(current_user.get("sub", 0))
    now_iso = datetime.now(timezone.utc).isoformat()

    result = dataflow_crud.update(
        "JobListing",
        job_id,
        {
            "status": "closed",
            "closed_at": now_iso,
        },
    )

    # ---- Cascade: active candidates -> withdrawn ------------------
    active_stages = {"new", "screening", "interview", "assessment"}
    candidates_withdrawn = 0
    try:
        candidates = dataflow_crud.list_records(
            "Candidate",
            {"job_listing_id": job_id, "company_id": company_id},
        )
        for cand in candidates:
            stage = cand.get("stage", "")
            if stage not in active_stages:
                continue
            cand_id = cand.get("id")
            if cand_id is None:
                continue
            try:
                dataflow_crud.update(
                    "Candidate",
                    cand_id,
                    {
                        "stage": "withdrawn",
                        "rejection_reason": "job_closed",
                        "updated_at": now_iso,
                    },
                )
                _log_candidate_activity(
                    cand_id,
                    "Withdrawn (job closed)",
                    actor_id,
                    "Job listing was closed; candidate auto-withdrawn.",
                )
                candidates_withdrawn += 1
            except Exception:
                logger.warning(
                    "Failed to withdraw candidate %s on job close", cand_id,
                    exc_info=True,
                )
    except Exception:
        logger.warning("Failed to list candidates for job close cascade", exc_info=True)

    # ---- Cascade: pending offers -> expired ------------------------
    pending_offer_statuses = {"draft", "pending_approval", "approved", "sent"}
    offers_expired = 0
    try:
        offers = dataflow_crud.list_records(
            "Offer",
            {"job_listing_id": job_id, "company_id": company_id},
        )
        for offer in offers:
            if offer.get("status") not in pending_offer_statuses:
                continue
            offer_id = offer.get("id")
            if offer_id is None:
                continue
            try:
                dataflow_crud.update(
                    "Offer",
                    offer_id,
                    {"status": "expired"},
                )
                offers_expired += 1
            except Exception:
                logger.warning(
                    "Failed to expire offer %s on job close", offer_id,
                    exc_info=True,
                )
    except Exception:
        logger.warning("Failed to list offers for job close cascade", exc_info=True)

    return {
        "job": result,
        "detail": "Job closed.",
        "candidates_withdrawn": candidates_withdrawn,
        "offers_expired": offers_expired,
    }


# --------------------------------------------------------------------------
# TAFEP Compliance Scan (T-R029)
# --------------------------------------------------------------------------


@router.post("/jobs/{job_id}/scan")
async def scan_job_listing(
    job_id: int,
    ai_check: bool = Query(False, description="Enable LLM second-pass scan (T-R053)"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Scan a job listing description for TAFEP compliance issues.

    Checks both the description and requirements fields for language that may
    violate TAFEP's fair employment guidelines. When ``ai_check`` is true,
    additionally runs an LLM second-pass scan for subtler phrases.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    job = _verify_job_ownership(job_id, company_id)

    from hr_advisory.services.tafep_scanner import scan_job_description, scan_with_ai

    # Rule-based scan (always runs)
    desc_findings = scan_job_description(job.get("description", ""))
    req_findings = scan_job_description(job.get("requirements", ""))

    all_findings = [
        {**f, "field": "description", "source": f.get("source", "rule")}
        for f in desc_findings
    ] + [
        {**f, "field": "requirements", "source": f.get("source", "rule")}
        for f in req_findings
    ]

    response: dict = {
        "job_id": job_id,
        "findings": all_findings,
        "count": len(all_findings),
        "compliant": len(all_findings) == 0,
    }

    # T-R053: optional AI pass — fail-open if anything goes wrong.
    if ai_check:
        ai_unavailable = False
        ai_reason = ""
        for field in ("description", "requirements"):
            field_text = job.get(field, "")
            if not field_text:
                continue
            ai_result = scan_with_ai(field_text)
            if ai_result.get("ai_unavailable"):
                ai_unavailable = True
                ai_reason = ai_result.get("reason", "")
                continue
            for f in ai_result.get("findings", []):
                all_findings.append({**f, "field": field, "source": "ai"})
        response["findings"] = all_findings
        response["count"] = len(all_findings)
        response["compliant"] = len(all_findings) == 0
        if ai_unavailable:
            response["ai_unavailable"] = True
            response["ai_reason"] = ai_reason

    return response


# --------------------------------------------------------------------------
# Candidates (cross-job)
# --------------------------------------------------------------------------


@router.get("/candidates")
async def list_all_candidates(
    stage: str | None = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List ALL candidates across all job listings for the company.

    T-RX09: paginated. Returns at most ``page_size`` rows per call so a
    company with thousands of candidates cannot exhaust server memory.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if stage:
        filters["stage"] = stage

    candidates = dataflow_crud.list_records("Candidate", filters)
    page_items, total = _paginate(candidates, page, page_size)
    return {
        "candidates": page_items,
        "items": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# --------------------------------------------------------------------------
# Interviews (cross-candidate)
# --------------------------------------------------------------------------


@router.get("/interviews")
async def list_all_interviews(
    status: str | None = Query(None),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List ALL interviews across all candidates for the company.

    Enriches each row with `candidate_name` and `interviewer_names`
    so the frontend doesn't have to issue N+1 lookups (and doesn't
    fall back to rendering raw IDs like "#1" / "#undefined").
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status

    interviews = dataflow_crud.list_records("InterviewSchedule", filters)

    # Bulk-fetch the related candidates so we can join names without N+1.
    # Use list_records (matches the rest of recruitment.py) — the per-id
    # read() variant returned None for valid ids in local testing.
    candidate_ids = {iv.get("candidate_id") for iv in interviews if iv.get("candidate_id")}
    candidate_map: dict[int, str] = {}
    if candidate_ids:
        try:
            cand_rows = dataflow_crud.list_records(
                "Candidate", {"company_id": company_id}
            )
            for cand in cand_rows:
                cid = cand.get("id")
                if cid in candidate_ids:
                    candidate_map[cid] = cand.get("name", "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Candidate name enrichment failed: %s", exc)

    # Resolve interviewer names. The `interviewers` field is a JSON-encoded
    # list of either employee IDs (preferred) or free-text names. Look up
    # employee names when given IDs; pass strings through as-is.
    enriched: list[dict] = []
    for iv in interviews:
        out = dict(iv)
        out["candidate_name"] = candidate_map.get(iv.get("candidate_id", 0), "")

        names: list[str] = []
        raw_interviewers = iv.get("interviewers", "")
        if raw_interviewers:
            try:
                parsed = (
                    json.loads(raw_interviewers)
                    if isinstance(raw_interviewers, str)
                    else raw_interviewers
                )
                if isinstance(parsed, list):
                    # Bulk-fetch all employees + users once for the company,
                    # then join in-memory to avoid N+1 reads.
                    if "_emp_user_map" not in locals():
                        try:
                            emp_rows = dataflow_crud.list_records(
                                "Employee", {"company_id": company_id}
                            )
                            user_rows = dataflow_crud.list_records(
                                "User", {"company_id": company_id}
                            )
                            user_by_id = {u.get("id"): u for u in user_rows}
                            _emp_user_map: dict[int, str] = {}
                            for e in emp_rows:
                                eid = e.get("id")
                                if eid is None:
                                    continue
                                user = user_by_id.get(e.get("user_id"))
                                if user and user.get("name"):
                                    _emp_user_map[eid] = user["name"]
                                else:
                                    _emp_user_map[eid] = e.get("designation") or f"Employee #{eid}"
                        except Exception:  # noqa: BLE001
                            _emp_user_map = {}
                    for entry in parsed:
                        if isinstance(entry, int) or (
                            isinstance(entry, str) and entry.isdigit()
                        ):
                            eid = int(entry)
                            if eid in _emp_user_map:
                                names.append(_emp_user_map[eid])
                            else:
                                names.append(f"Employee #{eid}")
                        elif isinstance(entry, str) and entry.strip():
                            names.append(entry.strip())
                        elif isinstance(entry, dict):
                            n = entry.get("name") or entry.get("email")
                            if n:
                                names.append(str(n))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        out["interviewer_names"] = names

        # Humanize the type for direct display: "in_person" → "In Person".
        # Frontends shouldn't have to maintain their own enum→label map.
        raw_type = str(iv.get("interview_type", "") or "")
        out["display_type"] = (
            raw_type.replace("_", " ").title() if raw_type else ""
        )

        # Derive is_overdue: any non-terminal interview whose scheduled_at
        # is more than 24h in the past. UI renders an "Overdue" badge.
        # Terminal statuses (completed, cancelled, no_show) never overdue.
        out["is_overdue"] = False
        if iv.get("status") in ("scheduled", "rescheduled"):
            scheduled_str = iv.get("scheduled_at", "") or ""
            if scheduled_str:
                try:
                    scheduled_dt = datetime.fromisoformat(
                        str(scheduled_str).replace("Z", "+00:00")
                    )
                    now_dt = datetime.now(timezone.utc)
                    if scheduled_dt.tzinfo is None:
                        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                    if (now_dt - scheduled_dt).total_seconds() > 24 * 3600:
                        out["is_overdue"] = True
                except (ValueError, TypeError):
                    pass

        enriched.append(out)

    return {"interviews": enriched, "count": len(enriched)}


# --------------------------------------------------------------------------
# Candidates (per-job)
# --------------------------------------------------------------------------


@router.get("/jobs/{job_id}/candidates")
async def list_candidates(
    job_id: int,
    stage: str | None = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List candidates for a job listing (T-RX09: paginated)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_job_ownership(job_id, company_id)

    filters: dict = {"job_listing_id": job_id}
    if stage:
        filters["stage"] = stage

    candidates = dataflow_crud.list_records("Candidate", filters)
    page_items, total = _paginate(candidates, page, page_size)
    return {
        "candidates": page_items,
        "items": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


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

    job = _verify_job_ownership(job_id, company_id)

    body = await request.json()
    name = body.get("name", "").strip()
    email = body.get("email", "").strip()
    if not name or not email:
        raise HTTPException(status_code=400, detail="name and email are required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(body.get("notes", ""), "notes")

    # Validate email format
    if email and not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format.")

    # Check for duplicate candidate on same job
    existing = dataflow_crud.list_records(
        "Candidate",
        {"job_listing_id": job_id, "email": email},
        limit=1,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Candidate already exists for this job.")

    # T-R027: PDPA consent fields
    pdpa_consent = bool(body.get("pdpa_consent", False))
    pdpa_consent_date = ""
    if pdpa_consent:
        pdpa_consent_date = datetime.now(timezone.utc).isoformat()

    candidate = dataflow_crud.create(
        "Candidate",
        {
            "company_id": company_id,
            "job_listing_id": job_id,
            "name": name,
            "email": email,
            "phone": body.get("phone", ""),
            "source": body.get("source", "direct"),
            "resume_url": body.get("resume_url", ""),
            "notes": body.get("notes", ""),
            "stage": "new",
            "pdpa_consent": pdpa_consent,
            "pdpa_consent_date": pdpa_consent_date,
            "created_by": int(current_user.get("sub", 0)),
        },
    )

    # T-R027: Record PDPA consent for recruitment if granted
    if pdpa_consent:
        try:
            from hr_advisory.security.pdpa import ConsentPurpose, record_consent

            record_consent(
                user_id=str(candidate.get("id", "")),
                purpose=ConsentPurpose.RECRUITMENT,
                granted=True,
                ip_address="",
            )
            logger.info(
                "PDPA recruitment consent recorded for candidate_id=%s",
                candidate.get("id"),
            )
        except Exception as exc:
            logger.warning("Failed to record PDPA consent: %s", exc)

    # T-R018: Send application received email (non-blocking)
    if email:
        company = dataflow_crud.read("Company", company_id)
        company_name = company.get("name", "") if company else ""
        await _send_recruitment_email(
            to=email,
            template_name="application_received",
            variables={
                "candidate_name": name or "Applicant",
                "job_title": job.get("title", ""),
                "company_name": company_name,
            },
        )

    return {"candidate": candidate}


@router.get("/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get a single candidate by ID."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    candidate = _verify_candidate_ownership(candidate_id, company_id)
    return {"candidate": candidate}


@router.patch("/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update candidate details (stage change, notes, etc.).

    Stage transitions are validated against a directed state machine
    (see _VALID_STAGE_TRANSITIONS). Invalid moves return 400.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    candidate = _verify_candidate_ownership(candidate_id, company_id)

    body = await request.json()
    allowed = {"name", "email", "phone", "notes", "resume_url", "source", "stage"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # T-RX10: validate stage transition before persisting.
    if "stage" in updates:
        _validate_stage_transition(
            candidate.get("stage", "new"),
            str(updates["stage"]),
        )

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = dataflow_crud.update("Candidate", candidate_id, updates)

    # T-R026: Log stage transitions for audit trail
    if "stage" in body:
        actor_id = int(current_user.get("sub", 0))
        _log_candidate_activity(candidate_id, f"Stage changed to {body['stage']}", actor_id)

    return {"candidate": result}


# --------------------------------------------------------------------------
# Structured rejection (T-R025)
# --------------------------------------------------------------------------


@router.post("/candidates/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reject a candidate with a documented reason."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    candidate = _verify_candidate_ownership(candidate_id, company_id)

    if candidate.get("stage") == "hired":
        raise HTTPException(status_code=400, detail="Cannot reject a hired candidate.")

    body = await request.json()
    reason = body.get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required.")

    _validate_text_length(reason, "reason", MAX_TEXT_LENGTH)
    notes = body.get("notes", "").strip()
    _validate_text_length(notes, "notes", MAX_TEXT_LENGTH)

    updates: dict = {
        "stage": "rejected",
        "rejection_reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if notes:
        updates["notes"] = notes

    result = dataflow_crud.update("Candidate", candidate_id, updates)

    # T-R026: Log rejection in audit trail
    actor_id = int(current_user.get("sub", 0))
    _log_candidate_activity(candidate_id, "Rejected", actor_id, reason)

    # Send rejection email
    candidate_email = candidate.get("email", "")
    if candidate_email and body.get("send_email", True):
        job = dataflow_crud.read("JobListing", candidate.get("job_listing_id"))
        company = dataflow_crud.read("Company", company_id)
        await _send_recruitment_email(
            to=candidate_email,
            template_name="rejection_notice",
            variables={
                "candidate_name": candidate.get("name", ""),
                "job_title": job.get("title", "") if job else "",
                "company_name": company.get("name", "") if company else "",
            },
        )

    logger.info("Candidate rejected: id=%s, reason=%s", candidate_id, reason)
    return {"candidate": result, "message": "Candidate rejected."}


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

    # S3-T6: idempotency guard — double-clicking "Schedule Interview" used to
    # create two InterviewSchedule rows AND two Google Calendar events. Look
    # for an existing row created within the last 30 seconds for this same
    # (candidate_id, scheduled_at, company_id) and return it instead. The
    # 30-second window is wider than any plausible network round-trip but
    # narrow enough that two genuinely intentional rapid-fire schedules
    # (with different times) are not collapsed.
    existing_rows = dataflow_crud.list_records(
        "InterviewSchedule",
        {
            "candidate_id": candidate_id,
            "company_id": company_id,
            "scheduled_at": scheduled_at,
        },
    )
    if existing_rows:
        now_dt = datetime.now(timezone.utc)
        for row in existing_rows:
            created_iso = row.get("created_at") or ""
            if not created_iso:
                continue
            try:
                # DataFlow returns created_at as ISO string OR datetime; normalize
                if isinstance(created_iso, datetime):
                    created_dt = created_iso
                else:
                    created_dt = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                if (now_dt - created_dt).total_seconds() < 30:
                    logger.info(
                        "schedule_interview idempotent return: candidate_id=%s "
                        "scheduled_at=%s existing_row=%s age_s=%.1f",
                        candidate_id,
                        scheduled_at,
                        row.get("id"),
                        (now_dt - created_dt).total_seconds(),
                    )
                    return {
                        "interview": row,
                        "detail": "Existing interview returned (idempotent within 30s window).",
                    }
            except (ValueError, TypeError):
                # If we cannot parse the timestamp, fall through to create
                continue

    interview = dataflow_crud.create(
        "InterviewSchedule",
        {
            "company_id": company_id,
            "candidate_id": candidate_id,
            "scheduled_at": scheduled_at,
            "duration_minutes": body.get("duration_minutes", 60),
            "interview_type": body.get("interview_type", "onsite"),
            "location": body.get("location", ""),
            "interviewers": json.dumps(body.get("interviewers", [])) if isinstance(body.get("interviewers"), list) else body.get("interviewers", "[]"),
            "notes": body.get("notes", ""),
            "status": "scheduled",
            "created_by": int(current_user.get("sub", 0)),
        },
    )

    # T-R019: Load candidate for stage check and email
    candidate = _verify_candidate_ownership(candidate_id, company_id)

    # Move candidate to interview stage only if at an earlier stage.
    # T-RX10: walk through the state machine ("new" -> "screening" -> "interview")
    # so audit trail and transition rules stay consistent.
    STAGE_ORDER = {"new": 0, "screening": 1, "interview": 2, "assessment": 3, "offered": 4, "hired": 5, "rejected": 6, "withdrawn": 7}
    current_stage = candidate.get("stage", "new")
    if STAGE_ORDER.get(current_stage, 0) < STAGE_ORDER.get("interview", 2):
        path: list[str] = []
        if current_stage == "new":
            path = ["screening", "interview"]
        elif current_stage == "screening":
            path = ["interview"]
        for next_stage in path:
            dataflow_crud.update(
                "Candidate",
                candidate_id,
                {
                    "stage": next_stage,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    # T-R019: Send interview invitation email to candidate
    candidate_email = candidate.get("email", "")
    if candidate_email:
        job = dataflow_crud.read("JobListing", candidate.get("job_listing_id"))
        company = dataflow_crud.read("Company", company_id)
        await _send_recruitment_email(
            to=candidate_email,
            template_name="interview_invitation",
            variables={
                "candidate_name": candidate.get("name", ""),
                "job_title": job.get("title", "") if job else "",
                "company_name": company.get("name", "") if company else "",
                "interview_date": body.get("scheduled_at", "")[:10],
                "interview_time": body.get("scheduled_at", "")[11:16] if len(body.get("scheduled_at", "")) > 11 else "",
                "duration": str(body.get("duration_minutes", 60)),
                "interview_format": body.get("interview_type", "onsite"),
                "location_or_link": body.get("location", ""),
                "interviewer_names": "The hiring team",
            },
        )

    # T-R055: best-effort Google Calendar sync.  Failures must never block
    # the interview workflow — log and continue.
    try:
        job = dataflow_crud.read("JobListing", candidate.get("job_listing_id"))
        sync_payload = {
            "id": interview.get("id"),
            "scheduled_at": interview.get("scheduled_at", ""),
            "duration_minutes": interview.get("duration_minutes", 60),
            "location": interview.get("location", ""),
            "interviewers": body.get("interviewers", []),
            "candidate_email": candidate.get("email", ""),
            "candidate_name": candidate.get("name", ""),
            "job_title": (job or {}).get("title", "") if job else "",
            "notes": interview.get("notes", ""),
            "status": interview.get("status", "scheduled"),
        }
        google_event_id = gcal_sync.create_event(company_id, sync_payload)
        if google_event_id and interview.get("id"):
            dataflow_crud.update(
                "InterviewSchedule",
                interview["id"],
                {"google_event_id": google_event_id},
            )
            interview["google_event_id"] = google_event_id
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google Calendar sync failed for interview %s: %s",
            interview.get("id"),
            exc,
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

    # Use list_records — dataflow_crud.read returns None for valid integer
    # PKs on PostgreSQL (DataFlow-layer bug). See _verify_job_ownership.
    rows = dataflow_crud.list_records(
        "InterviewSchedule", {"id": interview_id, "company_id": company_id}
    )
    existing = rows[0] if rows else None
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
    result = dataflow_crud.update("InterviewSchedule", interview_id, updates)

    # T-R055: keep Google Calendar in sync.  Cancellations delete the event;
    # any other change patches the event.  Best-effort — never blocks.
    google_event_id = (existing.get("google_event_id") or "") or ((result or {}).get("google_event_id") or "")
    try:
        if google_event_id:
            new_status = updates.get("status", existing.get("status"))
            if new_status == "cancelled":
                gcal_sync.delete_event(company_id, google_event_id)
                # Detach from the Arbor row so a future reschedule creates a new event.
                dataflow_crud.update(
                    "InterviewSchedule",
                    interview_id,
                    {"google_event_id": ""},
                )
            else:
                # Build the same payload shape sync.create_event expects.
                candidate = dataflow_crud.read("Candidate", existing.get("candidate_id")) or {}
                job = dataflow_crud.read("JobListing", candidate.get("job_listing_id")) or {}
                merged = {**existing, **updates}
                sync_payload = {
                    "id": interview_id,
                    "scheduled_at": merged.get("scheduled_at", ""),
                    "duration_minutes": merged.get("duration_minutes", 60),
                    "location": merged.get("location", ""),
                    "interviewers": merged.get("interviewers", "[]"),
                    "candidate_email": candidate.get("email", ""),
                    "candidate_name": candidate.get("name", ""),
                    "job_title": job.get("title", ""),
                    "notes": merged.get("notes", ""),
                    "status": merged.get("status", "scheduled"),
                }
                gcal_sync.update_event(company_id, google_event_id, sync_payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google Calendar sync failed for interview update %s: %s",
            interview_id,
            exc,
        )

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

    existing = dataflow_crud.read("InterviewSchedule", interview_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Interview not found.")

    body = await request.json()
    rating = body.get("rating")
    if rating is None:
        raise HTTPException(status_code=400, detail="rating is required.")

    feedback = dataflow_crud.create(
        "InterviewFeedback",
        {
            "company_id": company_id,
            "interview_id": interview_id,
            "candidate_id": existing.get("candidate_id"),
            "interviewer_id": int(current_user.get("sub", 0)),
            "overall_rating": rating,
            "strengths": body.get("strengths", ""),
            "weaknesses": body.get("weaknesses", ""),
            "notes": body.get("comments", body.get("notes", "")),
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

    # T-RX10: must reach "offered" via a valid transition. The candidate
    # must currently be at "interview" or "assessment" (or already at
    # "offered" — handled as a no-op stage move below).
    _validate_stage_transition(candidate.get("stage", "new"), "offered")

    body = await request.json()
    salary = body.get("salary")
    start_date = body.get("start_date", "")
    if salary is None or not start_date:
        raise HTTPException(status_code=400, detail="salary and start_date are required.")

    salary = float(salary)
    if not math.isfinite(salary):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")

    offer = dataflow_crud.create(
        "Offer",
        {
            "company_id": company_id,
            "candidate_id": candidate_id,
            "job_listing_id": candidate.get("job_listing_id"),
            "salary": salary,
            "currency": body.get("currency", "SGD"),
            "salary_period": body.get("salary_period", "monthly"),
            "start_date": start_date,
            "position_title": body.get("position_title", ""),
            "employment_type": body.get("employment_type", "full_time"),
            "probation_months": body.get("probation_months", 6),
            "notice_period_days": body.get("notice_period_days", 30),
            "benefits_summary": body.get("benefits_summary", ""),
            "terms_text": body.get("terms_text", ""),
            "expiry_date": body.get("expiry_date", ""),
            "notes": body.get("notes", ""),
            "status": "draft",
            "created_by": int(current_user.get("sub", 0)),
        },
    )

    dataflow_crud.update(
        "Candidate",
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

    # S2-T1: privilege-escalation guard. The body's role must be one of the
    # explicitly hirable roles. Owner/platform_admin escalations are rejected
    # here and again at invitation acceptance (auth.py) as defense-in-depth.
    requested_role = body.get("role", "employee")
    if requested_role not in HIRABLE_ROLES:
        logger.warning(
            "Hire role rejected: actor=%s candidate=%s requested_role=%s",
            actor_id,
            candidate_id,
            requested_role,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid role '{requested_role}' for hire. "
                f"Must be one of: {', '.join(sorted(HIRABLE_ROLES))}."
            ),
        )

    # T-R021: Fetch the latest offer for salary pre-fill
    offers = dataflow_crud.list_records("Offer", {"candidate_id": candidate_id, "company_id": company_id})
    latest_offer = offers[0] if offers else {}

    # T-R021: Resolve department and designation from body, job listing, or offer
    job = dataflow_crud.read("JobListing", candidate.get("job_listing_id"))
    department = body.get("department") or (job.get("department", "") if job else "")
    designation = body.get("designation") or (job.get("title", "") if job else "")

    # Create invitation for the new hire
    # Invitation model fields: company_id, inviter_id, email, role, token, expires_at,
    # accepted_at, is_active, department, designation
    import secrets

    token = secrets.token_urlsafe(32)
    invitation = dataflow_crud.create(
        "Invitation",
        {
            "company_id": company_id,
            "email": candidate.get("email"),
            "name": candidate.get("name"),
            "phone": candidate.get("phone", ""),
            "department": department,
            "designation": designation,
            "salary": latest_offer.get("salary"),
            "role": requested_role,
            "token": token,
            "inviter_id": actor_id,
            "is_active": True,
        },
    )

    # Update candidate stage
    dataflow_crud.update(
        "Candidate",
        candidate_id,
        {
            "stage": "hired",
            "hired_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # T-R026: Log hire in audit trail
    _log_candidate_activity(candidate_id, "Hired", actor_id)

    # T-R023: Log hired count for auto-close tracking
    job_id = candidate.get("job_listing_id")
    if job_id:
        all_candidates = dataflow_crud.list_records("Candidate", {"job_listing_id": job_id, "company_id": company_id})
        hired_count = sum(1 for c in all_candidates if c.get("stage") == "hired")
        logger.info("Job %s has %d hired candidates", job_id, hired_count)

    # T-R022: OnboardingAssignment is created when the new hire accepts their
    # invitation (auth.py:_register_employee_via_invitation calls
    # auto_assign_default_onboarding once the Employee row actually exists).
    # We do NOT create one here — doing so before invitation acceptance would
    # produce a dangling row with employee_id=0.
    return {
        "detail": "Candidate hired. Invitation created — onboarding will be assigned on acceptance.",
        "candidate_id": candidate_id,
    }


# --------------------------------------------------------------------------
# Resume upload & download
# --------------------------------------------------------------------------


def _validate_magic_bytes(content: bytes, content_type: str) -> bool:
    """Verify file content matches declared MIME type via magic byte signatures.

    Returns True if magic bytes match, False otherwise.
    """
    if content_type not in _MAGIC_BYTES:
        # No magic bytes check available for this type — reject as unsafe
        return False
    expected_prefix, prefix_len = _MAGIC_BYTES[content_type]
    if len(content) < prefix_len:
        return False
    return content[:prefix_len] == expected_prefix


@router.post("/candidates/{candidate_id}/resume")
async def upload_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Upload a resume file for a candidate.

    Validates file size (10MB), MIME type, file extension, and magic bytes.
    Stores the file with a UUID-based filename under uploads/recruitment/{company_id}/.
    Updates the candidate's resume_url field with the stored filename.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"resume_upload:{company_id}",
        max_requests=30,
        window_seconds=3600,
        action_name="uploading resumes",
    )

    _verify_candidate_ownership(candidate_id, company_id)

    # Read file content with size guard
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_RESUME_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit.")

    # MIME type validation
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_RESUME_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Use PDF, DOC, DOCX, JPG, or PNG.",
        )

    # Extension validation (defence in depth — don't trust content_type alone)
    original_filename = file.filename or "resume"
    file_ext = os.path.splitext(original_filename)[1].lower()
    if file_ext not in ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_ext}' not allowed. Use PDF, DOC, DOCX, JPG, or PNG.",
        )

    # Magic byte validation — verify actual file content matches declared type
    if not _validate_magic_bytes(content, content_type):
        raise HTTPException(
            status_code=400,
            detail="File content does not match declared type. Magic bytes verification failed.",
        )

    # Save file with UUID-based name under company subdirectory
    company_upload_dir = os.path.join(RECRUITMENT_UPLOAD_DIR, str(company_id))
    os.makedirs(company_upload_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(company_upload_dir, stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Update candidate's resume_url with the UUID filename
    dataflow_crud.update(
        "Candidate",
        candidate_id,
        {"resume_url": stored_name, "updated_at": datetime.now(timezone.utc).isoformat()},
    )

    logger.info(
        "Resume uploaded: candidate_id=%s, file=%s, size=%d, company_id=%s",
        candidate_id,
        stored_name,
        len(content),
        company_id,
    )

    return {"message": "Resume uploaded.", "resume_url": stored_name}


@router.get("/candidates/{candidate_id}/resume")
async def download_resume(
    candidate_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> FileResponse:
    """Download/serve the resume file for a candidate.

    Resolves the stored UUID filename from the candidate's resume_url field,
    verifies the file exists on disk, and returns it with the correct MIME type
    and Content-Disposition header.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    candidate = _verify_candidate_ownership(candidate_id, company_id)

    resume_url = candidate.get("resume_url", "")
    if not resume_url:
        raise HTTPException(status_code=404, detail="No resume on file for this candidate.")

    # Prevent path traversal — reject any resume_url containing path separators or ..
    if "/" in resume_url or "\\" in resume_url or ".." in resume_url or "\x00" in resume_url:
        raise HTTPException(status_code=400, detail="Invalid resume reference.")

    file_path = os.path.join(RECRUITMENT_UPLOAD_DIR, str(company_id), resume_url)
    # Double-check resolved path stays within expected directory
    expected_dir = os.path.realpath(os.path.join(RECRUITMENT_UPLOAD_DIR, str(company_id)))
    if not os.path.realpath(file_path).startswith(expected_dir + os.sep) and os.path.realpath(file_path) != expected_dir:
        raise HTTPException(status_code=400, detail="Invalid resume reference.")

    if not os.path.isfile(file_path):
        logger.error(
            "Resume file not found on disk: candidate_id=%s, path=%s",
            candidate_id,
            file_path,
        )
        raise HTTPException(status_code=404, detail="Resume file not found on disk.")

    # Determine media type from extension
    file_ext = os.path.splitext(resume_url)[1].lower()
    media_type = _EXT_TO_MIME.get(file_ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=\"{resume_url}\""},
    )


# --------------------------------------------------------------------------
# Screening Questions (T-R031, T-R032)
# --------------------------------------------------------------------------


@router.get("/jobs/{job_id}/questions")
async def list_screening_questions(
    job_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List screening questions for a job listing, sorted by sort_order."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_job_ownership(job_id, company_id)

    questions = dataflow_crud.list_records(
        "ScreeningQuestion",
        {"job_listing_id": job_id, "company_id": company_id},
    )
    questions.sort(key=lambda q: q.get("sort_order", 0))
    return {"questions": questions, "count": len(questions)}


@router.post("/jobs/{job_id}/questions")
async def create_screening_question(
    job_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a screening question for a job listing."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_job_ownership(job_id, company_id)

    body = await request.json()
    question_text = body.get("question_text", "").strip()
    if not question_text:
        raise HTTPException(status_code=400, detail="Question text is required.")

    _validate_text_length(question_text, "question_text")

    q = dataflow_crud.create(
        "ScreeningQuestion",
        {
            "job_listing_id": job_id,
            "company_id": company_id,
            "question_text": question_text,
            "question_type": body.get("question_type", "text"),
            "options": body.get("options", ""),
            "is_required": body.get("is_required", False),
            "is_knockout": body.get("is_knockout", False),
            "sort_order": body.get("sort_order", 0),
        },
    )
    return {"question": q}


@router.patch("/questions/{question_id}")
async def update_screening_question(
    question_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a screening question."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    q = dataflow_crud.read("ScreeningQuestion", question_id)
    if not q or q.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Question not found.")

    body = await request.json()
    allowed = {
        "question_text",
        "question_type",
        "options",
        "is_required",
        "is_knockout",
        "sort_order",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = dataflow_crud.update("ScreeningQuestion", question_id, updates)
    return {"question": result}


@router.delete("/questions/{question_id}")
async def delete_screening_question(
    question_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete a screening question."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    q = dataflow_crud.read("ScreeningQuestion", question_id)
    if not q or q.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Question not found.")

    dataflow_crud.delete("ScreeningQuestion", question_id)
    return {"message": "Question deleted."}


# --------------------------------------------------------------------------
# M8: Offers & Approvals (T-R038, T-R040)
# --------------------------------------------------------------------------


@router.post("/offers/{offer_id}/approve")
async def approve_offer(
    offer_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Approve a pending offer."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    offer = dataflow_crud.read("Offer", offer_id)
    if not offer or offer.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Offer not found.")

    if offer.get("status") not in ("draft", "pending_approval"):
        raise HTTPException(
            status_code=400,
            detail=f"Offer cannot be approved from status '{offer.get('status')}'.",
        )

    user_id = int(current_user.get("sub", 0))
    result = dataflow_crud.update(
        "Offer",
        offer_id,
        {
            "status": "approved",
            "approved_by": user_id,
            "approved_at": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )
    return {"offer": result, "message": "Offer approved."}


@router.post("/offers/{offer_id}/send")
async def send_offer(
    offer_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Send an approved offer to the candidate."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    offer = dataflow_crud.read("Offer", offer_id)
    if not offer or offer.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Offer not found.")

    if offer.get("status") not in ("draft", "approved"):
        raise HTTPException(
            status_code=400,
            detail=f"Offer cannot be sent from status '{offer.get('status')}'.",
        )

    # Get candidate and send email
    candidate = dataflow_crud.read("Candidate", offer.get("candidate_id"))
    if candidate and candidate.get("email"):
        company = dataflow_crud.read("Company", company_id)
        await _send_recruitment_email(
            to=candidate["email"],
            template_name="offer_sent",
            variables={
                "candidate_name": candidate.get("name", ""),
                "position_title": offer.get("position_title", ""),
                "company_name": company.get("name", "") if company else "",
                "salary": f"{offer.get('currency', 'SGD')} {offer.get('salary', 0):,.2f}/{offer.get('salary_period', 'month')}",
                "start_date": offer.get("start_date", ""),
                "expiry_date": offer.get("expiry_date", "TBD"),
            },
        )

    result = dataflow_crud.update(
        "Offer",
        offer_id,
        {
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )

    # Update candidate stage to offered
    if offer.get("candidate_id"):
        dataflow_crud.update(
            "Candidate",
            offer["candidate_id"],
            {
                "stage": "offered",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {"offer": result, "message": "Offer sent to candidate."}


@router.get("/offers")
async def list_offers(
    status: str | None = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all offers for the company.

    T-RX09: paginated. Candidate-name enrichment is restricted to the page
    being returned to avoid an N+1 read across the entire offer table.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict = {"company_id": company_id}
    if status:
        filters["status"] = status

    offers = dataflow_crud.list_records("Offer", filters)
    page_items, total = _paginate(offers, page, page_size)

    # Enrich the page with candidate names (only the rows we'll return)
    for offer in page_items:
        cand = dataflow_crud.read("Candidate", offer.get("candidate_id"))
        offer["candidate_name"] = cand.get("name", "") if cand else ""

    return {
        "offers": page_items,
        "items": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/offers/{offer_id}/respond")
async def respond_to_offer(
    offer_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Accept or decline an offer."""
    company_id = get_current_company_id(current_user)

    offer = dataflow_crud.read("Offer", offer_id)
    if not offer or offer.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Offer not found.")

    if offer.get("status") != "sent":
        raise HTTPException(
            status_code=400,
            detail="Offer is not in a respondable state.",
        )

    body = await request.json()
    response = body.get("response", "").strip().lower()
    if response not in ("accepted", "declined"):
        raise HTTPException(
            status_code=400,
            detail="Response must be 'accepted' or 'declined'.",
        )

    result = dataflow_crud.update(
        "Offer",
        offer_id,
        {
            "status": response,
            "responded_at": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )

    return {"offer": result, "message": f"Offer {response}."}


# --------------------------------------------------------------------------
# M9: Recruitment Analytics (T-R042)
# --------------------------------------------------------------------------


@router.get("/analytics/summary")
async def recruitment_summary(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get recruitment summary metrics."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    jobs = dataflow_crud.list_records("JobListing", {"company_id": company_id})
    candidates = dataflow_crud.list_records("Candidate", {"company_id": company_id})
    interviews = dataflow_crud.list_records(
        "InterviewSchedule", {"company_id": company_id}
    )

    open_jobs = sum(1 for j in jobs if j.get("status") == "open")
    total_candidates = len(candidates)

    # Pipeline distribution
    pipeline: dict[str, int] = {}
    for c in candidates:
        stage = c.get("stage", "new")
        pipeline[stage] = pipeline.get(stage, 0) + 1

    # Interviews this week
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    interviews_this_week = sum(
        1
        for i in interviews
        if i.get("scheduled_at", "") >= week_start.isoformat()[:10]
        and i.get("status") == "scheduled"
    )

    # Source distribution
    sources: dict[str, int] = {}
    for c in candidates:
        src = c.get("source", "direct")
        sources[src] = sources.get(src, 0) + 1

    # Offers
    offers = dataflow_crud.list_records("Offer", {"company_id": company_id})
    total_offers = len(offers)
    accepted_offers = sum(1 for o in offers if o.get("status") == "accepted")
    offer_acceptance_rate = (
        round(accepted_offers / total_offers * 100, 1)
        if total_offers > 0
        else 0
    )

    return {
        "open_jobs": open_jobs,
        "total_jobs": len(jobs),
        "total_candidates": total_candidates,
        "pipeline": pipeline,
        "interviews_this_week": interviews_this_week,
        "sources": sources,
        "total_offers": total_offers,
        "accepted_offers": accepted_offers,
        "offer_acceptance_rate": offer_acceptance_rate,
    }


# --------------------------------------------------------------------------
# M10: Public Careers Page (no auth) — T-R044
#
# All public endpoints scope by {company_slug} in the URL path. This:
#   1. Naturally enforces tenant isolation — a job from Company B cannot be
#      addressed via Company A's careers URL.
#   2. Removes the company-name enumeration vector (no name fallback).
#   3. Matches the frontend's URL shape (/careers/{slug}/jobs/{jobSlug}).
# --------------------------------------------------------------------------


def _resolve_company_by_slug(company_slug: str) -> dict:
    """Resolve a company by its public slug. 404 if unknown."""
    companies = dataflow_crud.list_records("Company", {"slug": company_slug})
    if not companies:
        raise HTTPException(status_code=404, detail="Company not found.")
    return companies[0]


def _resolve_public_job(company_id: int, job_slug: str) -> dict:
    """Resolve an open job by its slug within a given company. 404 otherwise.

    The slug is matched against `unique_slug` first; falls back to numeric id
    for backward compatibility with older URLs.
    """
    jobs = dataflow_crud.list_records(
        "JobListing", {"company_id": company_id, "unique_slug": job_slug}
    )
    job = jobs[0] if jobs else None
    if not job and job_slug.isdigit():
        # Backward-compat: allow numeric id lookup, but still tenant-scoped.
        candidate = dataflow_crud.read("JobListing", int(job_slug))
        if candidate and candidate.get("company_id") == company_id:
            job = candidate
    if not job or job.get("status") != "open":
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _public_job_summary(job: dict) -> dict:
    """Strip internal fields from a JobListing row for public display."""
    return {
        "id": job.get("id"),
        "slug": job.get("unique_slug", "") or str(job.get("id", "")),
        "title": job.get("title", ""),
        "department": job.get("department", ""),
        "location": job.get("location", ""),
        "employment_type": job.get("employment_type", ""),
        "description": job.get("description", ""),
        "requirements": job.get("requirements", ""),
        "posted_date": job.get("published_at", ""),
    }


@router.get("/careers/{company_slug}/jobs")
async def public_list_jobs(company_slug: str) -> dict:
    """Public endpoint: list published jobs for a company's careers page."""
    company = _resolve_company_by_slug(company_slug)
    company_id = company.get("id")

    jobs = dataflow_crud.list_records(
        "JobListing", {"company_id": company_id, "status": "open"}
    )

    return {
        "company_name": company.get("name", ""),
        "company_slug": company_slug,
        "jobs": [_public_job_summary(j) for j in jobs],
        "count": len(jobs),
    }


@router.get("/careers/{company_slug}/jobs/{job_slug}")
async def public_get_job(company_slug: str, job_slug: str) -> dict:
    """Public endpoint: get a single published job listing scoped to a company."""
    company = _resolve_company_by_slug(company_slug)
    company_id = company.get("id")
    job = _resolve_public_job(company_id, job_slug)

    questions = dataflow_crud.list_records(
        "ScreeningQuestion",
        {"job_listing_id": job.get("id"), "company_id": company_id},
    )
    questions.sort(key=lambda q: q.get("sort_order", 0))

    return {
        "job": _public_job_summary(job),
        "company_name": company.get("name", ""),
        "screening_questions": [
            {
                "id": q.get("id"),
                "question_text": q.get("question_text", ""),
                "question_type": q.get("question_type", "text"),
                "options": q.get("options", ""),
                "is_required": q.get("is_required", False),
            }
            for q in questions
        ],
    }


@router.post("/careers/{company_slug}/jobs/{job_slug}/apply")
async def public_apply(
    company_slug: str,
    job_slug: str,
    request: Request,
) -> dict:
    """Public endpoint: submit a job application — tenant-scoped via URL."""
    # Rate-limit FIRST (T-RX security review C3) — before any DB work, so we
    # can't be used as a (job, email) presence oracle by enumeration timing.
    client_host = request.client.host if request.client else "unknown"
    check_rate_limit(
        f"apply:{client_host}",
        max_requests=10,
        window_seconds=3600,
        action_name="job applications",
    )

    company = _resolve_company_by_slug(company_slug)
    company_id = company.get("id")
    job = _resolve_public_job(company_id, job_slug)
    job_id = job.get("id")

    body = await request.json()
    name = body.get("name", "").strip()
    email = body.get("email", "").strip()

    if not name or not email:
        raise HTTPException(
            status_code=400, detail="Name and email are required."
        )

    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    _validate_text_length(email, "email", MAX_NAME_LENGTH)
    # H1 / H2: bound the cover-letter and demographic fields to prevent
    # unauthenticated DB inflation.
    _validate_text_length(body.get("cover_letter", ""), "cover_letter", MAX_TEXT_LENGTH)
    _validate_text_length(body.get("nationality", ""), "nationality", 100)
    _validate_text_length(body.get("citizenship_status", ""), "citizenship_status", 100)
    _validate_text_length(body.get("phone", ""), "phone", 50)

    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format.")

    # Check PDPA consent
    if not body.get("pdpa_consent", False):
        raise HTTPException(
            status_code=400,
            detail="PDPA consent is required to submit your application.",
        )

    # Duplicate-application: return identical "received" body on duplicate so
    # the response shape doesn't betray an existing application for this email.
    existing = dataflow_crud.list_records(
        "Candidate",
        {
            "job_listing_id": job_id,
            "email": email,
            "company_id": company_id,
        },
    )
    if existing:
        existing_id = existing[0].get("id")
        return {
            "message": "Application received. We will be in touch.",
            "reference_number": f"APP-{existing_id}" if existing_id else "APP-PENDING",
            "application_id": existing_id,
        }

    candidate = dataflow_crud.create(
        "Candidate",
        {
            "company_id": company_id,
            "job_listing_id": job_id,
            "name": name,
            "email": email,
            "phone": body.get("phone", ""),
            "source": "careers_page",
            "stage": "new",
            "nationality": body.get("nationality", ""),
            "citizenship_status": body.get("citizenship_status", ""),
            "pdpa_consent": True,
            "pdpa_consent_date": datetime.now(timezone.utc).isoformat(),
            "notes": body.get("cover_letter", ""),
        },
    )

    # M6: Save screening responses — validate question_ids belong to this job
    responses = body.get("screening_responses", [])
    # Load screening questions for validation
    job_questions = dataflow_crud.list_records("ScreeningQuestion", {
        "job_listing_id": job_id,
        "company_id": company_id,
    })
    valid_question_ids = {q.get("id") for q in job_questions}

    # Enforce required questions
    required_ids = {q.get("id") for q in job_questions if q.get("is_required")}
    if required_ids:
        answered_ids = {r.get("question_id") for r in responses if r.get("question_id")}
        missing = required_ids - answered_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail="All required screening questions must be answered.",
            )

    for resp in responses:
        question_id = resp.get("question_id")
        if question_id and question_id in valid_question_ids:
            dataflow_crud.create(
                "ScreeningResponse",
                {
                    "candidate_id": candidate.get("id"),
                    "question_id": question_id,
                    "company_id": company_id,
                    "response_text": resp.get("response_text", ""),
                    "response_value": resp.get("response_value", ""),
                },
            )

    # Send confirmation email
    await _send_recruitment_email(
        to=email,
        template_name="application_received",
        variables={
            "candidate_name": name,
            "job_title": job.get("title", ""),
            "company_name": company.get("name", ""),
        },
    )

    candidate_id = candidate.get("id")
    logger.info(
        "Public application received: job=%s, candidate=%s",
        job_id,
        candidate_id,
    )
    return {
        "message": "Application submitted successfully.",
        "reference_number": f"APP-{candidate_id}" if candidate_id else "APP-PENDING",
        "application_id": candidate_id,
    }


# --------------------------------------------------------------------------
# M11: Candidate Application Status (T-R048)
# --------------------------------------------------------------------------


_STAGE_LABELS = {
    "new": "Under Review",
    "screening": "Under Review",
    "interview": "Interview Stage",
    "assessment": "Assessment Stage",
    "offered": "Offer Extended",
    "hired": "Hired",
    "rejected": "Application Closed",
    "withdrawn": "Withdrawn",
}


def _coarse_month(timestamp_value) -> str:
    """Coarsen a timestamp to YYYY-MM. Avoids exposing precise applied_date."""
    if not timestamp_value:
        return ""
    if isinstance(timestamp_value, datetime):
        return timestamp_value.strftime("%Y-%m")
    if isinstance(timestamp_value, str):
        return timestamp_value[:7] if len(timestamp_value) >= 7 else ""
    return ""


@router.get("/careers/{company_slug}/application-status")
async def public_application_status(
    company_slug: str,
    request: Request,
    email: str = Query(...),
    job_slug: str = Query(...),
) -> dict:
    """Public endpoint: check application status, scoped to a company.

    Returns the same response shape whether or not the application exists,
    so the endpoint cannot be used as an email/job presence oracle.
    """
    # Rate limit by IP to prevent enumeration sweeps
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(
        f"status_check:{client_ip}",
        max_requests=20,
        window_seconds=3600,
        action_name="application status checks",
    )

    generic_response = {
        "status": "Under Review",
        "applied_month": "",
    }

    # Resolve company; for unknown slugs, return the generic response (no
    # 404 oracle) — but still validate input shape.
    companies = dataflow_crud.list_records("Company", {"slug": company_slug})
    if not companies:
        return generic_response
    company_id = companies[0].get("id")

    # Resolve job by slug within this company
    jobs = dataflow_crud.list_records(
        "JobListing", {"company_id": company_id, "unique_slug": job_slug}
    )
    if not jobs and job_slug.isdigit():
        candidate_job = dataflow_crud.read("JobListing", int(job_slug))
        if candidate_job and candidate_job.get("company_id") == company_id:
            jobs = [candidate_job]
    if not jobs:
        return generic_response
    job_id = jobs[0].get("id")

    candidates = dataflow_crud.list_records(
        "Candidate",
        {"email": email, "job_listing_id": job_id, "company_id": company_id},
    )
    if not candidates:
        return generic_response

    candidate = candidates[0]
    return {
        "status": _STAGE_LABELS.get(
            candidate.get("stage", "new"), "Under Review"
        ),
        "applied_month": _coarse_month(candidate.get("created_at", "")),
    }


# --------------------------------------------------------------------------
# M12: Overdue Feedback Reminders (T-R020)
# --------------------------------------------------------------------------


@router.get("/feedback/overdue")
async def list_overdue_feedback(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List interviews with overdue feedback (T-RX09: paginated).

    An interview is overdue when it is in status 'completed', the scheduled
    time is more than 48h ago, and no feedback record exists yet.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    interviews = dataflow_crud.list_records("InterviewSchedule", {
        "company_id": company_id,
        "status": "completed",
    })

    now = datetime.now(timezone.utc)
    overdue = []
    for interview in interviews:
        # Check if feedback exists for this interview
        feedback = dataflow_crud.list_records("InterviewFeedback", {
            "interview_id": interview.get("id"),
            "company_id": company_id,
        })
        if not feedback:
            # Check if interview was > 48h ago
            scheduled = interview.get("scheduled_at", "")
            if scheduled:
                try:
                    interview_dt = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
                    if interview_dt.tzinfo:
                        interview_dt = interview_dt.replace(tzinfo=None)
                    if (now.replace(tzinfo=None) - interview_dt).total_seconds() > 48 * 3600:
                        candidate = dataflow_crud.read("Candidate", interview.get("candidate_id"))
                        overdue.append({
                            "interview_id": interview.get("id"),
                            "candidate_id": interview.get("candidate_id"),
                            "candidate_name": candidate.get("name", "") if candidate else "",
                            "scheduled_at": scheduled,
                            "interview_type": interview.get("interview_type", ""),
                            "hours_overdue": round((now.replace(tzinfo=None) - interview_dt).total_seconds() / 3600),
                        })
                except (ValueError, TypeError):
                    logger.warning(
                        "Invalid scheduled_at value for interview %s: %s",
                        interview.get("id"),
                        scheduled,
                    )

    page_items, total = _paginate(overdue, page, page_size)
    return {
        "overdue": page_items,
        "items": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/feedback/remind")
async def send_feedback_reminders(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Send reminder emails to interviewers with overdue feedback."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    interviews = dataflow_crud.list_records("InterviewSchedule", {
        "company_id": company_id,
        "status": "completed",
    })

    now = datetime.now(timezone.utc)
    sent_count = 0
    for interview in interviews:
        feedback = dataflow_crud.list_records("InterviewFeedback", {
            "interview_id": interview.get("id"),
            "company_id": company_id,
        })
        if not feedback:
            scheduled = interview.get("scheduled_at", "")
            if scheduled:
                try:
                    interview_dt = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
                    if interview_dt.tzinfo:
                        interview_dt = interview_dt.replace(tzinfo=None)
                    if (now.replace(tzinfo=None) - interview_dt).total_seconds() > 48 * 3600:
                        candidate = dataflow_crud.read("Candidate", interview.get("candidate_id"))
                        candidate_name = candidate.get("name", "") if candidate else "Unknown"
                        logger.info(
                            "Feedback reminder: interview=%s, candidate=%s",
                            interview.get("id"),
                            candidate_name,
                        )
                        sent_count += 1
                except (ValueError, TypeError):
                    logger.warning(
                        "Invalid scheduled_at value for interview %s: %s",
                        interview.get("id"),
                        scheduled,
                    )

    return {"reminders_sent": sent_count, "message": f"Sent {sent_count} feedback reminders."}


@router.post("/run-data-retention-sweep")
async def run_data_retention_sweep(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """T-R030: PDPA pre-purge notice sweep (cron-callable, admin-only).

    Finds candidates that:
      - were created more than 700 days ago, AND
      - are not in the "hired" stage, AND
      - have not yet received a pre-purge notice (pdpa_purge_warned_at is null)

    For each, sends one ``data_retention_warning`` email and stamps
    ``pdpa_purge_warned_at``. The actual purge happens at 730 days via the
    DataFlow retention sweeper.

    Suggested: daily at 03:00 SGT via external cron hitting
    ``POST /recruitment/run-data-retention-sweep`` with an admin token.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    check_rate_limit(
        f"retention_sweep:{company_id}",
        max_requests=2,
        window_seconds=3600,
        action_name="data retention sweep",
    )

    candidates = dataflow_crud.list_records(
        "Candidate", {"company_id": company_id},
    )
    company = dataflow_crud.read("Company", company_id) or {}
    company_name = company.get("name", "")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=700)
    purge_at = now + timedelta(days=30)
    notified = 0
    eligible = 0

    for cand in candidates:
        if cand.get("stage") == "hired":
            continue
        if cand.get("pdpa_purge_warned_at"):
            continue
        created_at_raw = cand.get("created_at", "")
        created_dt: datetime | None = None
        if isinstance(created_at_raw, datetime):
            created_dt = created_at_raw
        elif isinstance(created_at_raw, str) and created_at_raw:
            try:
                created_dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                created_dt = None
        if created_dt is None:
            continue
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        if created_dt > cutoff:
            continue

        eligible += 1
        cand_email = cand.get("email", "")
        cand_id = cand.get("id")
        if not cand_email or cand_id is None:
            continue

        job_title = ""
        if cand.get("job_listing_id"):
            try:
                job = dataflow_crud.read("JobListing", cand["job_listing_id"])
                if job:
                    job_title = job.get("title", "")
            except Exception:
                logger.debug("Job lookup failed for retention sweep", exc_info=True)

        try:
            sent = await _send_recruitment_email(
                to=cand_email,
                template_name="data_retention_warning",
                variables={
                    "candidate_name": cand.get("name", "Applicant"),
                    "company_name": company_name,
                    "job_title": job_title,
                    "applied_date": (
                        created_dt.date().isoformat() if created_dt else ""
                    ),
                    "purge_date": purge_at.date().isoformat(),
                },
            )
            # Only stamp when the email actually went out. If the mail
            # provider is misconfigured we want to retry next sweep — not
            # silently mark the candidate "warned" and then auto-purge them
            # 30 days later without ever notifying them.
            if sent:
                dataflow_crud.update(
                    "Candidate", cand_id,
                    {"pdpa_purge_warned_at": now},
                )
                notified += 1
            else:
                logger.warning(
                    "Retention sweep: email send failed for candidate %s — not stamping warned_at",
                    cand_id,
                )
        except Exception:
            logger.warning(
                "Retention sweep failed for candidate %s", cand_id, exc_info=True,
            )

    logger.info(
        "Retention sweep: company_id=%s, eligible=%d, notified=%d",
        company_id, eligible, notified,
    )
    return {
        "eligible_candidates": eligible,
        "notified": notified,
        "message": f"Sent {notified} PDPA retention notice(s) for {eligible} eligible candidate(s).",
    }


@router.post("/feedback/run-overdue-reminder-sweep")
async def run_overdue_reminder_sweep(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """T-R020: cron-callable sweep that fires feedback reminders.

    Suggested: daily at 09:00 SGT via external cron hitting
    ``POST /recruitment/feedback/run-overdue-reminder-sweep`` with an
    admin token. Rate-limited so accidental loops don't flood interviewers.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    # Bound to once-per-15min per company so a misconfigured cron job can't
    # blast interviewers with duplicate reminders.
    check_rate_limit(
        f"feedback_sweep:{company_id}",
        max_requests=4,
        window_seconds=3600,
        action_name="feedback reminder sweep",
    )

    # Reuse the listing logic to find overdue items.
    overdue_resp = await list_overdue_feedback(
        page=1, page_size=200, current_user=current_user,
    )
    overdue_items = overdue_resp.get("items", overdue_resp.get("overdue", []))

    if not overdue_items:
        return {
            "reminders_sent": 0,
            "overdue_count": 0,
            "message": "No overdue feedback to remind on.",
        }

    # Reuse the per-company reminder helper to actually fire the emails.
    reminder_resp = await send_feedback_reminders(current_user=current_user)
    sent = int(reminder_resp.get("reminders_sent", 0))

    logger.info(
        "Overdue feedback sweep: company_id=%s, overdue=%d, sent=%d",
        company_id, len(overdue_items), sent,
    )
    return {
        "reminders_sent": sent,
        "overdue_count": len(overdue_items),
        "message": f"Sweep complete. Sent {sent} reminder(s) for {len(overdue_items)} overdue interview(s).",
    }


# --------------------------------------------------------------------------
# M13: FCF Compliance Checker (T-R028)
# --------------------------------------------------------------------------


@router.get("/jobs/{job_id}/fcf-check")
async def check_fcf_compliance(
    job_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Check FCF (Fair Consideration Framework) compliance for a job listing.

    Under FCF, employers with 10+ employees must advertise on MyCareersFuture
    for 14 days before applying for an EP or S Pass, unless exempt.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    job = _verify_job_ownership(job_id, company_id)

    # Count employees
    employees = dataflow_crud.list_records("Employee", {"company_id": company_id})
    employee_count = len(employees)

    # Get salary range
    salary_max = job.get("salary_range_max", 0) or 0

    # FCF exemptions
    exempt = False
    exemption_reason = ""

    if employee_count < 10:
        exempt = True
        exemption_reason = "Company has fewer than 10 employees"
    elif salary_max >= 22500:
        exempt = True
        exemption_reason = "Salary exceeds $22,500/month (exempt from FCF advertising)"

    # Check MCF posting status
    mcf_posted_date = job.get("mcf_posted_date", "")
    days_since_posting = 0
    mcf_requirement_met = False

    if mcf_posted_date:
        try:
            posted_dt = datetime.fromisoformat(mcf_posted_date)
            days_since_posting = (
                datetime.now(timezone.utc).replace(tzinfo=None) - posted_dt.replace(tzinfo=None)
            ).days
            mcf_requirement_met = days_since_posting >= 14
        except (ValueError, TypeError):
            logger.warning(
                "Invalid mcf_posted_date for job %s: %s", job_id, mcf_posted_date
            )

    return {
        "job_id": job_id,
        "employee_count": employee_count,
        "salary_max": salary_max,
        "fcf_exempt": exempt,
        "exemption_reason": exemption_reason,
        "mcf_posted": bool(mcf_posted_date),
        "mcf_posted_date": mcf_posted_date,
        "days_since_posting": days_since_posting,
        "mcf_requirement_met": mcf_requirement_met or exempt,
        "advisory": (
            "No FCF advertising required — exempt." if exempt
            else "MyCareersFuture advertising completed." if mcf_requirement_met
            else f"FCF requires 14 days on MyCareersFuture before EP/S Pass application. "
                 f"{'Post not yet submitted.' if not mcf_posted_date else f'{14 - days_since_posting} days remaining.'}"
        ),
    }


@router.post("/jobs/{job_id}/mcf-posted")
async def record_mcf_posting(
    job_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Record that a job has been posted on MyCareersFuture."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    _verify_job_ownership(job_id, company_id)

    result = dataflow_crud.update("JobListing", job_id, {
        "mcf_posted_date": datetime.now(timezone.utc).isoformat(),
    })
    return {"job": result, "message": "MCF posting date recorded."}


# --------------------------------------------------------------------------
# M14: Offer Letter PDF Generation (T-R039)
# --------------------------------------------------------------------------


@router.get("/offers/{offer_id}/letter")
async def generate_offer_letter(
    offer_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> FileResponse:
    """Generate an offer letter PDF for a given offer."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    offer = dataflow_crud.read("Offer", offer_id)
    if not offer or offer.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Offer not found.")

    candidate = dataflow_crud.read("Candidate", offer.get("candidate_id"))
    company = dataflow_crud.read("Company", company_id)

    candidate_name = candidate.get("name", "Candidate") if candidate else "Candidate"
    company_name = company.get("name", "Company") if company else "Company"

    # Generate PDF using reportlab (already installed for payslip generation)
    import tempfile

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=A4,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "OfferTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=20
    )
    body_style = ParagraphStyle(
        "OfferBody", parent=styles["Normal"], fontSize=11, leading=16, spaceAfter=12
    )

    story = []
    story.append(Paragraph(company_name, title_style))
    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(f"Date: {datetime.now().strftime('%d %B %Y')}", body_style)
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Dear {candidate_name},", body_style))
    story.append(Spacer(1, 0.1 * inch))

    position_title = offer.get("position_title", "")
    story.append(
        Paragraph(
            f"We are pleased to offer you the position of <b>{position_title}</b> "
            f"at {company_name}. We were impressed with your qualifications and believe you will be "
            f"a valuable addition to our team.",
            body_style,
        )
    )

    employment_type = offer.get("employment_type", "Full-time").replace("_", " ").title()
    currency = offer.get("currency", "SGD")
    salary = offer.get("salary", 0)
    start_date = offer.get("start_date", "TBD")
    probation_months = offer.get("probation_months", 6)
    notice_period_days = offer.get("notice_period_days", 30)

    story.append(
        Paragraph(
            f"<b>Position:</b> {position_title}<br/>"
            f"<b>Employment Type:</b> {employment_type}<br/>"
            f"<b>Monthly Salary:</b> {currency} {salary:,.2f}<br/>"
            f"<b>Start Date:</b> {start_date}<br/>"
            f"<b>Probation Period:</b> {probation_months} months<br/>"
            f"<b>Notice Period:</b> {notice_period_days} days",
            body_style,
        )
    )

    benefits_summary = offer.get("benefits_summary", "")
    if benefits_summary:
        story.append(
            Paragraph(f"<b>Benefits:</b> {benefits_summary}", body_style)
        )

    story.append(Spacer(1, 0.2 * inch))
    expiry_date = offer.get("expiry_date", "further notice") or "further notice"
    story.append(
        Paragraph(
            "Please confirm your acceptance of this offer by signing and returning this letter. "
            f"This offer is valid until {expiry_date}.",
            body_style,
        )
    )

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Yours sincerely,", body_style))
    story.append(Paragraph(company_name, body_style))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("_________________________", body_style))
    story.append(Paragraph(f"Accepted by: {candidate_name}", body_style))
    story.append(Paragraph("Date: _____________", body_style))

    doc.build(story)

    # H3: Sanitize filename — strip all characters except alphanumeric, underscore, hyphen
    safe_filename = re.sub(r"[^a-zA-Z0-9_-]", "", candidate_name.replace(" ", "-").lower())[:50]
    if not safe_filename:
        safe_filename = "offer-letter"

    # H4: Schedule temp file cleanup via BackgroundTasks
    def _cleanup_temp_file(path: str) -> None:
        try:
            os.unlink(path)
        except OSError:
            pass

    background_tasks.add_task(_cleanup_temp_file, tmp.name)

    return FileResponse(
        tmp.name,
        media_type="application/pdf",
        filename=f"offer-letter-{safe_filename}.pdf",
    )


# --------------------------------------------------------------------------
# M12: Talent Pool (T-R050)
# --------------------------------------------------------------------------


@router.get("/talent-pool")
async def search_talent_pool(
    query: str = Query("", description="Search by name or email"),
    stage: str = Query("", description="Filter by stage"),
    source: str = Query("", description="Filter by source"),
    tag: str = Query("", description="Filter by tag in notes"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Search the talent pool — all candidates across all jobs (T-RX09: paginated)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    candidates = dataflow_crud.list_records("Candidate", {"company_id": company_id})

    # Apply filters
    if query:
        q = query.lower()
        candidates = [
            c for c in candidates
            if q in c.get("name", "").lower() or q in c.get("email", "").lower()
        ]
    if stage:
        candidates = [c for c in candidates if c.get("stage") == stage]
    if source:
        candidates = [c for c in candidates if c.get("source") == source]
    if tag:
        t = tag.lower()
        candidates = [c for c in candidates if t in c.get("notes", "").lower()]

    page_items, total = _paginate(candidates, page, page_size)

    # Enrich the page with job title (only the rows we'll return)
    for c in page_items:
        job = dataflow_crud.read("JobListing", c.get("job_listing_id"))
        c["job_title"] = job.get("title", "") if job else ""

    return {
        "candidates": page_items,
        "items": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/candidates/{candidate_id}/reapply")
async def reapply_candidate(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Move a talent pool candidate to a new job's pipeline."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    candidate = _verify_candidate_ownership(candidate_id, company_id)

    body = await request.json()
    new_job_id = body.get("job_listing_id")
    if not new_job_id:
        raise HTTPException(status_code=400, detail="job_listing_id is required.")

    _verify_job_ownership(new_job_id, company_id)

    # T-RX02: Re-applying from the talent pool ALWAYS requires fresh PDPA consent.
    # The new candidate record starts with consent unset and a clear note.
    new_candidate = dataflow_crud.create("Candidate", {
        "company_id": company_id,
        "job_listing_id": new_job_id,
        "name": candidate.get("name", ""),
        "email": candidate.get("email", ""),
        "phone": candidate.get("phone", ""),
        "source": "talent_pool",
        "stage": "new",
        "nationality": candidate.get("nationality", ""),
        "citizenship_status": candidate.get("citizenship_status", ""),
        "resume_url": candidate.get("resume_url", ""),
        "pdpa_consent": False,
        "pdpa_consent_date": "",
        "notes": f"Re-applied from talent pool (original candidate #{candidate_id}). PDPA consent must be re-confirmed.",
    })

    return {
        "candidate": new_candidate,
        "message": "Candidate added to new job pipeline. PDPA consent must be re-confirmed.",
        "note": "PDPA consent must be re-confirmed for the new application.",
    }


# --------------------------------------------------------------------------
# M12: Employee Referrals (T-R051)
# --------------------------------------------------------------------------


@router.post("/referrals")
async def create_referral(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit an employee referral. Available to all authenticated users."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))

    body = await request.json()
    job_id = body.get("job_listing_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="job_listing_id is required.")

    _verify_job_ownership(job_id, company_id)

    candidate_name = body.get("candidate_name", "").strip()
    candidate_email = body.get("candidate_email", "").strip()
    if not candidate_name or not candidate_email:
        raise HTTPException(status_code=400, detail="Candidate name and email are required.")

    _validate_text_length(candidate_name, "candidate_name", MAX_NAME_LENGTH)

    # Find the employee record for the referrer
    employees = dataflow_crud.list_records("Employee", {"user_id": user_id, "company_id": company_id})
    employee = employees[0] if employees else None
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found for current user.")

    referral = dataflow_crud.create("Referral", {
        "company_id": company_id,
        "referrer_employee_id": employee.get("id"),
        "job_listing_id": job_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "candidate_phone": body.get("candidate_phone", ""),
        "status": "pending",
        "notes": body.get("notes", ""),
    })

    logger.info(
        "Referral submitted: referrer=%s, candidate=%s, job=%s",
        employee.get("id"),
        candidate_name,
        job_id,
    )
    return {"referral": referral, "message": "Referral submitted."}


@router.get("/referrals")
async def list_referrals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List referrals. HR sees all; employees see their own (T-RX09: paginated)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")

    if role in ("owner", "hr_manager"):
        referrals = dataflow_crud.list_records("Referral", {"company_id": company_id})
    else:
        user_id = int(current_user.get("sub", 0))
        employees = dataflow_crud.list_records("Employee", {"user_id": user_id, "company_id": company_id})
        employee = employees[0] if employees else None
        if not employee:
            return {
                "referrals": [], "items": [], "count": 0,
                "total": 0, "page": page, "page_size": page_size,
            }
        referrals = dataflow_crud.list_records("Referral", {
            "company_id": company_id,
            "referrer_employee_id": employee.get("id"),
        })

    page_items, total = _paginate(referrals, page, page_size)

    # Enrich the page with job title
    for r in page_items:
        job = dataflow_crud.read("JobListing", r.get("job_listing_id"))
        r["job_title"] = job.get("title", "") if job else ""

    return {
        "referrals": page_items,
        "items": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# --------------------------------------------------------------------------
# M12: Hiring Manager Filtered View (T-R052)
# --------------------------------------------------------------------------


@router.get("/my-department/candidates")
async def list_department_candidates(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List candidates for jobs in the current user's department."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employees = dataflow_crud.list_records("Employee", {"user_id": user_id, "company_id": company_id})
    employee = employees[0] if employees else None
    if not employee:
        return {"candidates": [], "count": 0}

    department = employee.get("department", "")
    if not department:
        return {"candidates": [], "count": 0, "message": "No department assigned."}

    # Find jobs in this department
    jobs = dataflow_crud.list_records("JobListing", {"company_id": company_id, "department": department})
    job_ids = {j.get("id") for j in jobs}

    # Find candidates for those jobs
    all_candidates = dataflow_crud.list_records("Candidate", {"company_id": company_id})
    dept_candidates = [c for c in all_candidates if c.get("job_listing_id") in job_ids]

    # Enrich with job title
    for c in dept_candidates:
        job = dataflow_crud.read("JobListing", c.get("job_listing_id"))
        c["job_title"] = job.get("title", "") if job else ""

    return {
        "department": department,
        "candidates": dept_candidates,
        "count": len(dept_candidates),
    }


# --------------------------------------------------------------------------
# T-R035: Interview Scorecards (templates + entries)
# --------------------------------------------------------------------------


def _validate_scorecard_criteria(criteria: list) -> str:
    """Validate that criteria is a list of {name, weight} and weights sum ~1.0.

    Returns the JSON string to persist. Raises 400 on invalid input.
    """
    if not isinstance(criteria, list) or not criteria:
        raise HTTPException(
            status_code=400, detail="criteria must be a non-empty list.",
        )

    cleaned: list[dict] = []
    total_weight = 0.0
    for idx, item in enumerate(criteria):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=400,
                detail=f"criteria[{idx}] must be an object with 'name' and 'weight'.",
            )
        name = str(item.get("name", "")).strip()
        if not name:
            raise HTTPException(
                status_code=400, detail=f"criteria[{idx}].name is required.",
            )
        try:
            weight = float(item.get("weight", 0))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"criteria[{idx}].weight must be numeric.",
            ) from exc
        if not math.isfinite(weight) or weight < 0 or weight > 1:
            raise HTTPException(
                status_code=400,
                detail=f"criteria[{idx}].weight must be a finite number in [0, 1].",
            )
        cleaned.append({"name": name, "weight": weight})
        total_weight += weight

    if abs(total_weight - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Criteria weights must sum to 1.0 (got {total_weight:.3f}).",
        )

    return json.dumps(cleaned)


@router.get("/scorecard-templates")
async def list_scorecard_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all scorecard templates for the company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    templates = dataflow_crud.list_records(
        "ScorecardTemplate", {"company_id": company_id},
    )
    page_items, total = _paginate(templates, page, page_size)
    return {
        "items": page_items,
        "templates": page_items,
        "count": len(page_items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/scorecard-templates")
async def create_scorecard_template(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new scorecard template (admin-only)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")
    _validate_text_length(name, "name", MAX_NAME_LENGTH)
    description = str(body.get("description", ""))
    _validate_text_length(description, "description")

    criteria_json = _validate_scorecard_criteria(body.get("criteria", []))

    template = dataflow_crud.create(
        "ScorecardTemplate",
        {
            "company_id": company_id,
            "name": name,
            "description": description,
            "criteria": criteria_json,
            "created_by": int(current_user.get("sub", 0)),
            "is_active": bool(body.get("is_active", True)),
        },
    )
    return {"template": template}


@router.patch("/scorecard-templates/{template_id}")
async def update_scorecard_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a scorecard template (admin-only)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("ScorecardTemplate", template_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Scorecard template not found.")

    body = await request.json()
    updates: dict = {}
    if "name" in body:
        name = str(body["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty.")
        _validate_text_length(name, "name", MAX_NAME_LENGTH)
        updates["name"] = name
    if "description" in body:
        description = str(body["description"])
        _validate_text_length(description, "description")
        updates["description"] = description
    if "criteria" in body:
        updates["criteria"] = _validate_scorecard_criteria(body["criteria"])
    if "is_active" in body:
        updates["is_active"] = bool(body["is_active"])

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    result = dataflow_crud.update("ScorecardTemplate", template_id, updates)
    return {"template": result}


@router.delete("/scorecard-templates/{template_id}")
async def delete_scorecard_template(
    template_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Delete (archive) a scorecard template (admin-only)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    existing = dataflow_crud.read("ScorecardTemplate", template_id)
    if not existing or existing.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Scorecard template not found.")

    dataflow_crud.delete("ScorecardTemplate", template_id)
    return {"message": "Scorecard template deleted."}


def _compute_scorecard_total(criteria_json: str, scores: dict) -> float:
    """Weighted average of 1..5 scores against the template's criteria."""
    try:
        criteria = json.loads(criteria_json) if criteria_json else []
    except (TypeError, ValueError):
        criteria = []
    total = 0.0
    weight_sum = 0.0
    for c in criteria:
        name = c.get("name", "")
        weight = float(c.get("weight", 0) or 0)
        score = scores.get(name)
        if score is None:
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score_f) or score_f < 1 or score_f > 5:
            continue
        total += score_f * weight
        weight_sum += weight
    if weight_sum <= 0:
        return 0.0
    # If only some criteria scored, scale the partial result up to the
    # full weight so partial scorecards are still comparable.
    return round(total / weight_sum, 2)


@router.get("/interview-feedback/{feedback_id}/scorecards")
async def list_scorecard_entries(
    feedback_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List scorecard entries linked to a specific interview feedback record."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    feedback = dataflow_crud.read("InterviewFeedback", feedback_id)
    if not feedback or feedback.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Interview feedback not found.")

    entries = dataflow_crud.list_records(
        "ScorecardEntry",
        {"interview_feedback_id": feedback_id, "company_id": company_id},
    )
    return {"entries": entries, "count": len(entries)}


@router.post("/interview-feedback/{feedback_id}/scorecards")
async def create_scorecard_entry(
    feedback_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a scorecard entry against an interview feedback record."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    feedback = dataflow_crud.read("InterviewFeedback", feedback_id)
    if not feedback or feedback.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Interview feedback not found.")

    body = await request.json()
    template_id = body.get("template_id")
    if template_id is None:
        raise HTTPException(status_code=400, detail="template_id is required.")

    template = dataflow_crud.read("ScorecardTemplate", template_id)
    if not template or template.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Scorecard template not found.")

    raw_scores = body.get("scores", {})
    if not isinstance(raw_scores, dict):
        raise HTTPException(
            status_code=400, detail="scores must be an object of name->1..5.",
        )

    # Validate scores
    for k, v in raw_scores.items():
        try:
            score_f = float(v)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"scores['{k}'] must be a number between 1 and 5.",
            ) from exc
        if not math.isfinite(score_f) or score_f < 1 or score_f > 5:
            raise HTTPException(
                status_code=400,
                detail=f"scores['{k}'] must be between 1 and 5.",
            )

    notes = str(body.get("notes", ""))
    _validate_text_length(notes, "notes")

    total = _compute_scorecard_total(template.get("criteria", ""), raw_scores)

    entry = dataflow_crud.create(
        "ScorecardEntry",
        {
            "company_id": company_id,
            "interview_feedback_id": feedback_id,
            "template_id": int(template_id),
            "scores": json.dumps(raw_scores),
            "notes": notes,
            "total_score": total,
            "created_by": int(current_user.get("sub", 0)),
        },
    )
    return {"entry": entry, "total_score": total}


# --------------------------------------------------------------------------
# T-R054: AI candidate scorecard generation (Kaizen)
# --------------------------------------------------------------------------


@router.get("/scorecard/quota")
async def scorecard_quota(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Return the current month's AI-scorecard quota state for the company.

    Settings page renders this as "27 / 50 used (resets 2026-05-01)".
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    month_start, used, state = _scorecard_quota_check(company_id)
    # Reset is the start of next month
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    return {
        "used": used,
        "soft_cap": SCORECARD_SOFT_CAP,
        "hard_cap": SCORECARD_HARD_CAP,
        "state": state,
        "month_start": month_start.date().isoformat(),
        "resets_on": next_month.date().isoformat(),
    }


@router.post("/candidates/{candidate_id}/scorecard/generate")
async def generate_ai_scorecard(
    candidate_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Generate an AI-authored scorecard for a candidate (T-R054).

    Loads the candidate, the job listing, the requested scorecard
    template, and any interview feedback collected so far, then runs the
    Kaizen ScorecardAgent. The structured scorecard is returned to the
    caller and persisted as a ScorecardEntry row when the schema is
    available — falling back to a transient generation_id if not.

    LLM calls are expensive: rate-limited to 10 requests / minute / user.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"generate_scorecard:{user_id}",
        max_requests=10,
        window_seconds=60,
    )

    # S3-T4: per-company monthly scorecard quota. Without this gate a 5-user
    # company can sustain 3,000 scorecards/hour (50/min × 60min) and burn
    # ~$720/day on GPT-4o. Soft cap = 50/month free, hard cap = 500/month.
    # The 500 hard cap protects the platform; the 50 soft cap surfaces a
    # warning in the response so the customer sees pricing tiers.
    quota_now, quota_used, quota_state = _scorecard_quota_check(company_id)
    if quota_state == "exhausted":
        raise HTTPException(
            status_code=429,
            detail=(
                f"Monthly AI-scorecard limit reached ({quota_used}/{SCORECARD_HARD_CAP}). "
                f"Resets on the 1st of next month. Contact sales to upgrade."
            ),
        )

    candidate = _verify_candidate_ownership(candidate_id, company_id)

    body = await request.json()
    template_id = body.get("template_id")
    if template_id is None:
        raise HTTPException(status_code=400, detail="template_id is required.")
    try:
        template_id = int(template_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="template_id must be an integer.",
        ) from exc

    template = dataflow_crud.read("ScorecardTemplate", template_id)
    if not template or template.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Scorecard template not found.")

    # Job listing — required so the agent can compare against requirements.
    job_id = candidate.get("job_listing_id")
    job = (
        dataflow_crud.read("JobListing", job_id) if job_id is not None else None
    )
    if not job or job.get("company_id") != company_id:
        raise HTTPException(
            status_code=404,
            detail="Job listing for this candidate was not found.",
        )

    # Interview feedback — optional, scoped by tenant.
    feedback_rows = dataflow_crud.list_records(
        "InterviewFeedback", {"candidate_id": candidate_id},
    )
    feedback_rows = [
        f for f in feedback_rows if f.get("company_id") == company_id
    ]

    # Build sanitised inputs for the agent (no protected attributes).
    candidate_payload = {
        "id": candidate.get("id"),
        "name": candidate.get("name", ""),
        "email": candidate.get("email", ""),
        "current_role": candidate.get("current_role", ""),
        "experience_summary": candidate.get("experience_summary", "")
        or candidate.get("notes", ""),
        "skills": candidate.get("skills", []),
        "education": candidate.get("education", ""),
        "resume_excerpt": candidate.get("resume_excerpt", ""),
        "source": candidate.get("source", ""),
        "stage": candidate.get("stage", ""),
    }
    job_payload = {
        "id": job.get("id"),
        "title": job.get("title", ""),
        "department": job.get("department", ""),
        "employment_type": job.get("employment_type", ""),
        "description": job.get("description", ""),
        "requirements": job.get("requirements", ""),
    }
    template_payload = {
        "id": template.get("id"),
        "name": template.get("name", ""),
        "description": template.get("description", ""),
        "criteria": template.get("criteria", "[]"),
    }
    feedback_payload = [
        {
            "id": f.get("id"),
            "interview_id": f.get("interview_id"),
            "overall_rating": f.get("overall_rating"),
            "strengths": f.get("strengths", ""),
            "weaknesses": f.get("weaknesses", ""),
            "notes": f.get("notes", ""),
            "recommendation": f.get("recommendation", ""),
        }
        for f in feedback_rows
    ]

    # Lazy-import the agent so the recruitment router stays importable
    # even if the kaizen extras are missing from the dev environment.
    try:
        from hr_advisory.agents.scorecard_agent import (
            ScorecardAgent,
            ScorecardAgentConfig,
        )
    except ImportError as exc:
        logger.error("ScorecardAgent unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="AI scorecard service is not available on this deployment.",
        ) from exc

    try:
        agent = ScorecardAgent(config=ScorecardAgentConfig())
        result = agent.generate(
            candidate_profile=candidate_payload,
            job_listing=job_payload,
            scorecard_template=template_payload,
            interview_feedback=feedback_payload,
        )
    except Exception as exc:
        logger.error(
            "ScorecardAgent failed for candidate %s, template %s: %s",
            candidate_id,
            template_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="AI scorecard generation failed. Please try again or score manually.",
        ) from exc

    scorecard = result.get("scorecard", {})
    degraded = bool(result.get("degraded", False))

    # Persist as a ScorecardEntry row keyed against this candidate so the
    # AI-authored scorecard is reviewable alongside human ones. Falls back
    # to a transient generation_id when the schema isn't deployed yet.
    competency_ratings = scorecard.get("competency_ratings", {}) or {}
    notes_blob = json.dumps(
        {
            "ai_generated": True,
            "overall_fit": scorecard.get("overall_fit"),
            "recommended_decision": scorecard.get("recommended_decision"),
            "narrative": scorecard.get("narrative", ""),
            "strengths": scorecard.get("strengths", []),
            "concerns": scorecard.get("concerns", []),
            "degraded": degraded,
        },
    )
    generation_id = f"ai-scorecard-{candidate_id}-{uuid.uuid4().hex[:12]}"
    # S3-T8b: narrow the catch — only schema-mismatch errors should be
    # silently skipped (the AI columns may not yet exist on older
    # deployments). Real DB failures (connection timeout, deadlock, etc.)
    # MUST surface so we don't lose scorecards quietly. Postgres returns
    # `column ... does not exist` (psycopg2 ProgrammingError, code 42703);
    # SQLite returns OperationalError with "no such column".
    persisted_entry: dict | None = None
    try:
        persisted_entry = dataflow_crud.create(
            "ScorecardEntry",
            {
                "company_id": company_id,
                "candidate_id": candidate_id,
                "interview_feedback_id": None,
                "template_id": template_id,
                "scores": json.dumps(competency_ratings),
                "notes": notes_blob[:MAX_TEXT_LENGTH] if notes_blob else "",
                "total_score": float(scorecard.get("overall_fit", 0.0) or 0.0),
                "created_by": user_id,
                "generation_id": generation_id,
                "is_ai_generated": True,
            },
        )
    except Exception as exc:  # noqa: BLE001
        # Treat ONLY schema-mismatch as the no-op case.
        msg = str(exc).lower()
        is_schema_mismatch = (
            "no such column" in msg
            or "does not exist" in msg
            or "undefinedcolumn" in msg
            or "unknown column" in msg
        )
        if is_schema_mismatch:
            logger.info(
                "ScorecardEntry persistence skipped (schema lacks AI columns): %s",
                type(exc).__name__,
            )
            persisted_entry = None
        else:
            # Real DB failure — log loudly, but still don't take down the
            # whole scorecard generation. The scorecard is already
            # returned to the caller; persistence is best-effort but the
            # error is now visible in alerts.
            logger.error(
                "ScorecardEntry persistence FAILED (non-schema): %s — %s",
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            persisted_entry = None

    _log_candidate_activity(
        candidate_id,
        f"AI scorecard generated (template_id={template_id}, "
        f"decision={scorecard.get('recommended_decision', 'unknown')})",
        user_id,
    )

    response = {
        "scorecard": scorecard,
        "generation_id": generation_id,
        "degraded": degraded,
        "persisted_entry_id": (persisted_entry or {}).get("id"),
    }
    # S3-T4: surface quota state so the UI can show usage / upgrade nudge.
    response["quota"] = {
        "used": quota_used + 1,  # this generation counts against the cap
        "soft_cap": SCORECARD_SOFT_CAP,
        "hard_cap": SCORECARD_HARD_CAP,
        "state": quota_state,
    }
    if quota_state == "soft_warning":
        response["quota_warning"] = (
            f"You've used {quota_used + 1} of your {SCORECARD_SOFT_CAP} free "
            f"AI scorecards this month. Hard cap is {SCORECARD_HARD_CAP}. "
            f"Contact sales for the next tier."
        )
    return response
