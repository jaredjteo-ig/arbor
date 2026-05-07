"""Engagement-survey router (M2 + M3).

Round-3 product revision: engagement surveys ship in-app only at v1.
Public tokenised endpoints are NOT included; the router exposes
HR-side authoring (templates, cohorts, preview) and employee-side
in-app endpoints.

M2 endpoints (templates + cohorts):
- GET/POST/PATCH/DELETE /templates
- GET/POST/PATCH/DELETE /cohorts
- POST /cohorts/preview

M3 endpoints (launch + responses + trend + manager + actions):
- POST /surveys/launch
- GET  /surveys
- GET  /surveys/{id}
- GET  /surveys/{id}/responses
- POST /surveys/{id}/close
- GET  /surveys/{id}/aggregate
- GET  /surveys/trend
- GET  /surveys/{id}/suggested-actions
- POST /surveys/{id}/actions
- GET  /actions
- PATCH /actions/{id}
- GET  /my-pending
- GET  /my-history
- GET  /my-responses/{id}/render
- POST /my-responses/{id}/submit
- GET  /team/aggregate
- GET  /my-loop-closing
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import (
    get_current_user,
    require_role,
)
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.api.routers._helpers import (
    MAX_NAME_LENGTH,
    MAX_TEXT_LENGTH,
    _validate_text_length,
)
from hr_advisory.services import (
    cohort_resolver,
    dataflow_crud,
    engagement_actions as engagement_actions_svc,
    engagement_library,
    engagement_pseudonym,
    notifications,
    theme_tagger,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Methodology validation (M0 + M2 T21)
_VALID_METHODOLOGIES = {
    "custom",
    "gallup_q12",
    "trust_index",
    "pulse",
    "enps",
}

# Template / cohort PATCH whitelists per round-2 P39 (DataFlow updates use
# whitelists). Reject id, company_id, created_by, created_at.
_TEMPLATE_PATCH_FIELDS = {"name", "description", "sections", "methodology", "is_archived"}
_COHORT_PATCH_FIELDS = {"name", "description", "filter_spec", "is_archived"}

# Round-3 P1 cohort UI restriction (M2 T22). The cohort_resolver still
# supports the full 8-key filter spec, but the create/update handlers
# reject multi-dimension combinators that defer to M8 T91.
_P1_ONLY = True


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ──────────────────────────────────────────────────────────────────────
# Helper — resolve & validate company_id from the JWT
# ──────────────────────────────────────────────────────────────────────


def _resolve_company_id(current_user: dict) -> int:
    """Return the JWT's company_id or raise 400."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    return int(company_id)


def _check_cross_tenant_ad_hoc_ids(
    filter_spec: dict, company_id: int
) -> None:
    """Round-2 M4 / red-team C2: reject ad_hoc_employee_ids that don't
    belong to this company. Used on cohort preview AND launch.
    """
    ids = filter_spec.get("ad_hoc_employee_ids") or []
    if not ids:
        return
    ids_to_check = {int(i) for i in ids}
    owned = dataflow_crud.list_records(
        "Employee", {"company_id": company_id}, cache_ttl=0
    )
    owned_ids = {int(e["id"]) for e in owned if e.get("id")}
    cross_tenant = ids_to_check - owned_ids
    if cross_tenant:
        raise HTTPException(
            status_code=400,
            detail=(
                "ad_hoc_employee_ids contains employee(s) outside "
                "your company."
            ),
        )


def _serialize_filter_spec(filter_spec: Any) -> str:
    """Accept either a dict (frontend send) or already-serialised JSON
    string. Return a normalised JSON string for storage.
    """
    if isinstance(filter_spec, str):
        # Validate by round-tripping through json.loads.
        try:
            parsed = json.loads(filter_spec) if filter_spec else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="filter_spec must be valid JSON.",
            ) from exc
    elif isinstance(filter_spec, dict):
        parsed = filter_spec
    else:
        raise HTTPException(
            status_code=400,
            detail="filter_spec must be an object or JSON string.",
        )

    try:
        cohort_resolver.validate_filter_spec(parsed, p1_only=_P1_ONLY)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return json.dumps(parsed, sort_keys=True)


# ──────────────────────────────────────────────────────────────────────
# Templates (T21)
# ──────────────────────────────────────────────────────────────────────


@router.get("/templates")
async def list_templates(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List engagement-survey templates for the current company.

    Lazy-seeds the P1 library (Q12 + monthly_pulse) on first call.
    """
    company_id = _resolve_company_id(current_user)

    # T16 lazy seed: idempotent — no-op if any template already exists.
    seeded = engagement_library.seed_library_for_company(company_id)
    if seeded:
        logger.info(
            "engagement_library_seeded_on_first_get",
            extra={"company_id": company_id, "seeded": seeded},
        )

    rows = dataflow_crud.list_records(
        "EngagementSurveyTemplate",
        {"company_id": company_id},
        cache_ttl=0,
    )
    rows = [r for r in rows if not r.get("is_archived")]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"templates": rows, "count": len(rows)}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    template = dataflow_crud.read("EngagementSurveyTemplate", template_id)
    if not template or int(template.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Template not found.")
    return {"template": template}


@router.post("/templates")
async def create_template(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new engagement template, optionally cloned from an existing.

    Pass `?clone_from=N` to copy fields from template N (must be in the
    same company).
    """
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"create_engagement_template:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="create engagement template",
    )

    body = await request.json()

    # Clone path
    clone_from = request.query_params.get("clone_from")
    if clone_from:
        try:
            src_id = int(clone_from)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="clone_from must be an integer template id.",
            ) from exc
        src = dataflow_crud.read("EngagementSurveyTemplate", src_id)
        if not src or int(src.get("company_id") or 0) != company_id:
            raise HTTPException(
                status_code=404,
                detail=f"Source template {src_id} not found.",
            )
        body.setdefault("name", f"{src.get('name', '')} (copy)")
        body.setdefault("description", src.get("description", ""))
        body.setdefault("methodology", src.get("methodology", "custom"))
        body.setdefault("sections", src.get("sections", "[]"))

    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")
    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    description = (body.get("description") or "").strip()
    _validate_text_length(description, "description", MAX_TEXT_LENGTH)

    methodology = (body.get("methodology") or "custom").strip()
    if methodology not in _VALID_METHODOLOGIES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"methodology must be one of {sorted(_VALID_METHODOLOGIES)}; "
                f"got {methodology!r}."
            ),
        )

    sections = body.get("sections", "[]")
    if isinstance(sections, list):
        sections = json.dumps(sections)
    elif not isinstance(sections, str):
        raise HTTPException(
            status_code=400,
            detail="sections must be a JSON array or stringified JSON.",
        )

    now = _now()
    record = dataflow_crud.create(
        "EngagementSurveyTemplate",
        {
            "company_id": company_id,
            "name": name,
            "description": description,
            "methodology": methodology,
            "sections": sections,
            "is_archived": False,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"template": record}


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"update_engagement_template:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="update engagement template",
    )

    existing = dataflow_crud.read("EngagementSurveyTemplate", template_id)
    if not existing or int(existing.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Template not found.")

    body = await request.json()
    updates = {k: v for k, v in body.items() if k in _TEMPLATE_PATCH_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    if "methodology" in updates and updates["methodology"] not in _VALID_METHODOLOGIES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"methodology must be one of {sorted(_VALID_METHODOLOGIES)}; "
                f"got {updates['methodology']!r}."
            ),
        )

    if "name" in updates:
        name = (updates["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty.")
        _validate_text_length(name, "name", MAX_NAME_LENGTH)
        updates["name"] = name

    if "sections" in updates and isinstance(updates["sections"], list):
        updates["sections"] = json.dumps(updates["sections"])

    updates["updated_at"] = _now()
    result = dataflow_crud.update(
        "EngagementSurveyTemplate", template_id, updates
    )
    return {"template": result}


@router.delete("/templates/{template_id}")
async def archive_template(
    template_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"archive_engagement_template:{user_id}",
        max_requests=20,
        window_seconds=60,
        action_name="archive engagement template",
    )

    existing = dataflow_crud.read("EngagementSurveyTemplate", template_id)
    if not existing or int(existing.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Template not found.")

    dataflow_crud.update(
        "EngagementSurveyTemplate",
        template_id,
        {"is_archived": True, "updated_at": _now()},
    )
    return {"detail": "Template archived."}


# ──────────────────────────────────────────────────────────────────────
# Cohorts (T22)
# ──────────────────────────────────────────────────────────────────────


@router.get("/cohorts")
async def list_cohorts(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    rows = dataflow_crud.list_records(
        "EngagementCohort", {"company_id": company_id}, cache_ttl=0
    )
    rows = [r for r in rows if not r.get("is_archived")]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"cohorts": rows, "count": len(rows)}


@router.get("/cohorts/{cohort_id}")
async def get_cohort(
    cohort_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    cohort = dataflow_crud.read("EngagementCohort", cohort_id)
    if not cohort or int(cohort.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Cohort not found.")
    return {"cohort": cohort}


@router.post("/cohorts")
async def create_cohort(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a saved cohort.

    P1 UI restriction: filter_spec must use only preset keys
    (`all_active`, `departments`, `tenure_max_days`, `ad_hoc_employee_ids`).
    Multi-dimension combinators defer to M8 T91 full builder.
    """
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"create_engagement_cohort:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="create engagement cohort",
    )

    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")
    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    description = (body.get("description") or "").strip()
    _validate_text_length(description, "description", MAX_TEXT_LENGTH)

    filter_spec_raw = body.get("filter_spec")
    if filter_spec_raw is None:
        raise HTTPException(status_code=400, detail="filter_spec is required.")
    filter_spec = _serialize_filter_spec(filter_spec_raw)

    now = _now()
    record = dataflow_crud.create(
        "EngagementCohort",
        {
            "company_id": company_id,
            "name": name,
            "description": description,
            "filter_spec": filter_spec,
            "is_archived": False,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"cohort": record}


@router.patch("/cohorts/{cohort_id}")
async def update_cohort(
    cohort_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"update_engagement_cohort:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="update engagement cohort",
    )

    existing = dataflow_crud.read("EngagementCohort", cohort_id)
    if not existing or int(existing.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Cohort not found.")

    body = await request.json()
    updates = {k: v for k, v in body.items() if k in _COHORT_PATCH_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    if "filter_spec" in updates:
        updates["filter_spec"] = _serialize_filter_spec(updates["filter_spec"])

    if "name" in updates:
        name = (updates["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty.")
        _validate_text_length(name, "name", MAX_NAME_LENGTH)
        updates["name"] = name

    updates["updated_at"] = _now()
    result = dataflow_crud.update("EngagementCohort", cohort_id, updates)
    return {"cohort": result}


@router.delete("/cohorts/{cohort_id}")
async def archive_cohort(
    cohort_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    existing = dataflow_crud.read("EngagementCohort", cohort_id)
    if not existing or int(existing.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Cohort not found.")
    dataflow_crud.update(
        "EngagementCohort",
        cohort_id,
        {"is_archived": True, "updated_at": _now()},
    )
    return {"detail": "Cohort archived."}


# ──────────────────────────────────────────────────────────────────────
# Cohort preview (T23) + overlap helper (T24)
# ──────────────────────────────────────────────────────────────────────

# Anonymity threshold — round-1 redteam M1.  Hardcoded at v1 per L5.
MIN_COHORT_SIZE = 5

# D1 (red-team Phase 2): manager view shows themes-only at this floor
# instead of suppressing entirely. Themes are pre-aggregated bucket
# names (growth/manager/etc), not individual content — safe at n=3.
# Below this, suppression message stays.
THEMES_ONLY_THRESHOLD = 3

# Sample size returned to the preview UI.
PREVIEW_SAMPLE_NAMES = 8


def find_overlapping_surveys(
    company_id: int,
    employee_ids: list[int],
    *,
    exclude_survey_id: int = 0,
) -> list[dict]:
    """T24 — return active engagement surveys whose response set
    intersects `employee_ids`.

    Used by:
    - `/cohorts/preview` (T23) for the warnings field.
    - M3 launch handler to surface the confirmation modal.

    Returns: list of `{survey_id, name, target_count, overlap_count}`.
    """
    if not employee_ids:
        return []

    open_surveys = dataflow_crud.list_records(
        "EngagementSurvey",
        {"company_id": int(company_id)},
        cache_ttl=0,
    )
    target_ids = set(int(e) for e in employee_ids)
    out: list[dict] = []
    for s in open_surveys:
        if s.get("closed_at"):
            continue  # skip closed surveys
        if int(s.get("id") or 0) == int(exclude_survey_id):
            continue
        responses = dataflow_crud.list_records(
            "EngagementSurveyResponse",
            {"survey_id": int(s["id"])},
            cache_ttl=0,
        )
        # Round-1 C1: voided responses don't count toward overlap.
        overlap = {
            int(r["employee_id"])
            for r in responses
            if r.get("employee_id")
            and not r.get("is_void")
            and int(r["employee_id"]) in target_ids
        }
        if overlap:
            out.append({
                "survey_id": int(s["id"]),
                "name": s.get("name", ""),
                "target_count": int(s.get("target_count") or 0),
                "overlap_count": len(overlap),
            })
    return out


def _resolve_employee_names(
    employee_ids: list[int],
    company_id: int,
    *,
    limit: int = PREVIEW_SAMPLE_NAMES,
) -> list[str]:
    """Resolve up to `limit` employee_ids to human-readable names.

    Names come from `User.name` via `Employee.user_id`; falls back to
    `Employee.designation` when the user has no name set.
    """
    if not employee_ids:
        return []
    sample = sorted(employee_ids)[:limit]
    employees = dataflow_crud.list_records(
        "Employee", {"company_id": company_id}, cache_ttl=0
    )
    emp_by_id = {int(e["id"]): e for e in employees if e.get("id")}
    user_ids = {emp_by_id[i].get("user_id") for i in sample if i in emp_by_id}
    user_ids = {u for u in user_ids if u}
    user_name_by_id: dict[int, str] = {}
    if user_ids:
        users = dataflow_crud.list_records(
            "User", {"company_id": company_id}, cache_ttl=0
        )
        for u in users:
            if int(u.get("id") or 0) in user_ids:
                user_name_by_id[int(u["id"])] = u.get("name", "")

    names: list[str] = []
    for eid in sample:
        emp = emp_by_id.get(eid)
        if not emp:
            continue
        uid = emp.get("user_id")
        name = user_name_by_id.get(int(uid)) if uid else ""
        if not name:
            name = emp.get("designation") or f"Employee {eid}"
        names.append(name)
    return names


@router.post("/cohorts/preview")
async def preview_cohort(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Resolve a `filter_spec` to (matched_count, sample_names, anonymity_safe, warnings).

    Body:
      {
        "filter_spec": {...},
        "anonymity_tier": "pseudonymous"  # optional, drives anonymity_safe gate
      }

    The endpoint takes filter_spec inline (no saved cohort needed) so the
    cohort editor can preview as the user types. Round-1 redteam M3:
    surfaces overlap warnings against active surveys.
    """
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"preview_engagement_cohort:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="preview engagement cohort",
    )

    body = await request.json()
    filter_spec_raw = body.get("filter_spec")
    if filter_spec_raw is None:
        raise HTTPException(status_code=400, detail="filter_spec is required.")

    # Validate (P1-only restriction enforced) and round-trip.
    filter_spec_json = _serialize_filter_spec(filter_spec_raw)
    filter_spec = json.loads(filter_spec_json)

    _check_cross_tenant_ad_hoc_ids(filter_spec, company_id)

    employee_ids = cohort_resolver.resolve_cohort(company_id, filter_spec)
    matched_count = len(employee_ids)

    anonymity_tier = (body.get("anonymity_tier") or "identified").strip()
    is_pseudo_or_anon = anonymity_tier in ("pseudonymous", "anonymous")
    anonymity_safe = not is_pseudo_or_anon or matched_count >= MIN_COHORT_SIZE

    warnings: list[dict] = []
    if is_pseudo_or_anon and not anonymity_safe:
        warnings.append({
            "kind": "anonymity_unsafe",
            "min_cohort_size": MIN_COHORT_SIZE,
            "matched_count": matched_count,
            "message": (
                f"Cohort has {matched_count} matching employee(s). "
                f"Pseudonymous and anonymous tiers require at least "
                f"{MIN_COHORT_SIZE} respondents to preserve anonymity. "
                "Either broaden the cohort or switch tier to identified."
            ),
        })

    overlapping = find_overlapping_surveys(company_id, employee_ids)
    for o in overlapping:
        warnings.append({
            "kind": "overlap_active_survey",
            "survey_id": o["survey_id"],
            "survey_name": o["name"],
            "overlap_count": o["overlap_count"],
            "message": (
                f"{o['overlap_count']} of these employees already have an open "
                f"response in {o['name']!r}. Launching now will give them two "
                "concurrent surveys."
            ),
        })

    sample_names = _resolve_employee_names(employee_ids, company_id)

    return {
        "matched_count": matched_count,
        "sample_names": sample_names,
        "anonymity_safe": anonymity_safe,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════════════
# M3 — Launch + responses + trend + manager + actions
# ══════════════════════════════════════════════════════════════════════

# Per-company launch lock (Z06).
#
# Scope of this lock:
#   - Adequate for single-tenant-per-server deployments (the user's
#     current architecture decision — see workspaces/engagement-survey/
#     02-plans/04-product-revision-round3.md).
#   - Adequate for single-process FastAPI workers (uvicorn --workers 1).
#   - NOT adequate for multi-worker uvicorn deployments — each worker
#     has its own process so this dict isn't shared. Two workers can
#     enter the lock concurrently for the same company.
#
# When/if the deployment moves to multi-worker, replace this with a
# Postgres advisory lock keyed by company_id (round-2 redteam F2.1):
#
#     async with conn.transaction() as tx:
#         await tx.execute("SELECT pg_advisory_xact_lock($1)", company_id)
#         ...  # launch saga
#
# The advisory lock is released on transaction commit/rollback so it
# survives any failure mode in the saga.
_LAUNCH_LOCKS: dict[int, threading.Lock] = {}
_LAUNCH_LOCKS_GUARD = threading.Lock()

# Default consent notice — appended to engagement-survey emails (M8
# reminder send) and surfaced in the in-app form. Tenants can override
# at launch time per S1.
DEFAULT_CONSENT_NOTICE = (
    "Your responses are collected and processed to improve workplace "
    "engagement. Pseudonymous and anonymous tiers strip your "
    "employee_id at submit time. See your company's PDPA notice for "
    "retention and access details."
)
DEFAULT_CONSENT_NOTICE_VERSION = "v1"

# Idempotency window — submits within 24h with the same key replay.
IDEMPOTENCY_REPLAY_WINDOW = timedelta(hours=24)


def _get_launch_lock(company_id: int) -> threading.Lock:
    """Return a per-company lock, creating it on first use (Z06)."""
    with _LAUNCH_LOCKS_GUARD:
        lock = _LAUNCH_LOCKS.get(company_id)
        if lock is None:
            lock = threading.Lock()
            _LAUNCH_LOCKS[company_id] = lock
        return lock


def _parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime, accepting trailing Z and +08:00."""
    if not value:
        raise ValueError("datetime is empty.")
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _to_naive_utc(dt: datetime) -> datetime:
    """Convert any datetime to naive UTC for DB storage."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _resolve_employee_for_user(user_id: int, company_id: int) -> dict | None:
    rows = dataflow_crud.list_records(
        "Employee",
        {"user_id": int(user_id), "company_id": int(company_id)},
        limit=10,
        cache_ttl=0,
    )
    return rows[0] if rows else None


def _tenure_band_for(employee: dict) -> str:
    from datetime import date
    start_str = employee.get("start_date") or ""
    if not start_str:
        return "unknown"
    try:
        start = date.fromisoformat(start_str.split("T")[0])
    except ValueError:
        return "unknown"
    days = (date.today() - start).days
    if days < 365:
        return "0-1y"
    if days < 365 * 3:
        return "1-3y"
    return "3+y"


def _build_response_cohort_attributes(employee: dict) -> str:
    """Z03: snapshot the employee's cohort attributes at submit time.

    Stored on the response so the aggregator can compute by-cohort
    breakdowns for pseudonymous/anonymous responses without joining
    the live Employee table.

    `manager_id_hashed` is included rather than raw manager_id so
    re-identifying via "the only person with manager X" stays harder.
    Hash is non-reversible per-process; stable across queries within
    the same process.
    """
    manager_id = employee.get("reporting_manager_id") or 0
    manager_hash = ""
    if manager_id:
        # Per-process stable hash; only used for cohort grouping.
        manager_hash = hashlib.sha256(
            f"mgr:{int(manager_id)}".encode("utf-8")
        ).hexdigest()[:16]
    return json.dumps({
        "department": employee.get("department", ""),
        "pass_type": employee.get("pass_type", ""),
        "tenure_band": _tenure_band_for(employee),
        "manager_id_hashed": manager_hash,
    }, sort_keys=True)


def _count_submitted_responses(survey_id: int) -> int:
    """Z07 — derive response count on read; no denormalised column."""
    rows = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"survey_id": int(survey_id)},
        limit=5000,
        cache_ttl=0,
    )
    return sum(
        1 for r in rows
        if r.get("submitted_at") and not r.get("is_void")
    )


# ──────────────────────────────────────────────────────────────────────
# T30 — Launch
# ──────────────────────────────────────────────────────────────────────


@router.post("/surveys/launch")
async def launch_survey(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Launch a survey: resolve cohort, snapshot template, fan out responses
    + in-app notifications.

    Body:
      {
        template_id: int,
        cohort_id: int (or 0 with cohort_filter_spec),
        cohort_filter_spec: {...} optional,
        name: str,
        anonymity_tier: identified | pseudonymous | anonymous,
        closes_at: ISO-8601,
        consent_notice_text: str optional,
        force_overlap_acknowledged: bool,
        force_anonymity_acknowledged: bool,
      }
    """
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"launch_engagement_survey:{user_id}",
        max_requests=60,
        window_seconds=3600,
        action_name="launch engagement survey",
    )

    body = await request.json()
    template_id = body.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id is required.")

    template = dataflow_crud.read("EngagementSurveyTemplate", int(template_id))
    if not template or int(template.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Template not found.")

    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")
    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    anonymity_tier = (body.get("anonymity_tier") or "identified").strip()
    if anonymity_tier not in ("identified", "pseudonymous", "anonymous"):
        raise HTTPException(
            status_code=400,
            detail="anonymity_tier must be identified | pseudonymous | anonymous.",
        )

    # Closes_at validation (Z12)
    closes_at_raw = body.get("closes_at")
    if not closes_at_raw:
        raise HTTPException(status_code=400, detail="closes_at is required.")
    try:
        closes_at = _to_naive_utc(_parse_iso_datetime(str(closes_at_raw)))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="closes_at must be a valid ISO-8601 datetime.",
        ) from exc
    now = _now()
    if closes_at <= now + timedelta(hours=1):
        raise HTTPException(
            status_code=400,
            detail="closes_at must be at least 1 hour in the future.",
        )
    if closes_at > now + timedelta(days=90):
        raise HTTPException(
            status_code=400,
            detail="closes_at must be within 90 days.",
        )

    # Resolve cohort.
    cohort_id = int(body.get("cohort_id") or 0)
    cohort_filter_spec_raw = body.get("cohort_filter_spec")
    cohort_filter_spec_json = ""
    if cohort_id:
        cohort = dataflow_crud.read("EngagementCohort", cohort_id)
        if not cohort or int(cohort.get("company_id") or 0) != company_id:
            raise HTTPException(status_code=404, detail="Cohort not found.")
        cohort_filter_spec_json = cohort.get("filter_spec") or "{}"
    elif cohort_filter_spec_raw is not None:
        cohort_filter_spec_json = _serialize_filter_spec(cohort_filter_spec_raw)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either cohort_id or cohort_filter_spec is required.",
        )

    cohort_filter_spec = json.loads(cohort_filter_spec_json)
    # C2 (red-team Phase 3): cross-tenant guard now also applies on
    # launch (was preview-only). Defense-in-depth — preview gates the
    # UI, launch gates the action.
    _check_cross_tenant_ad_hoc_ids(cohort_filter_spec, company_id)
    employee_ids = cohort_resolver.resolve_cohort(company_id, cohort_filter_spec)
    if not employee_ids:
        raise HTTPException(
            status_code=400,
            detail="Cohort matched 0 employees.",
        )

    # Anonymity safety (round-1 M1)
    if (
        anonymity_tier in ("pseudonymous", "anonymous")
        and len(employee_ids) < MIN_COHORT_SIZE
        and not body.get("force_anonymity_acknowledged")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cohort has {len(employee_ids)} employee(s). "
                f"Pseudonymous and anonymous tiers require at least "
                f"{MIN_COHORT_SIZE}. Pass force_anonymity_acknowledged=true "
                "to proceed anyway."
            ),
        )

    # Per-company launch lock (Z06).
    lock = _get_launch_lock(company_id)
    with lock:
        # Re-check overlap inside the lock (TOCTOU-safe).
        overlapping = find_overlapping_surveys(company_id, employee_ids)
        if overlapping and not body.get("force_overlap_acknowledged"):
            return {
                "ok": False,
                "warnings": [
                    {
                        "kind": "overlap_active_survey",
                        "survey_id": o["survey_id"],
                        "survey_name": o["name"],
                        "overlap_count": o["overlap_count"],
                    }
                    for o in overlapping
                ],
                "can_proceed": True,
            }

        # Snapshot template.sections (C3).
        template_sections_snapshot = template.get("sections") or "[]"

        consent_notice_text = (
            (body.get("consent_notice_text") or "").strip()
            or DEFAULT_CONSENT_NOTICE
        )
        consent_notice_version = (
            DEFAULT_CONSENT_NOTICE_VERSION
            + ":"
            + hashlib.sha256(
                consent_notice_text.encode("utf-8")
            ).hexdigest()[:8]
        )

        # Saga A: create survey row.
        survey = dataflow_crud.create(
            "EngagementSurvey",
            {
                "company_id": company_id,
                "template_id": int(template_id),
                "template_sections_snapshot": template_sections_snapshot,
                "cohort_id": cohort_id,
                "cohort_filter_spec": cohort_filter_spec_json,
                "name": name,
                "anonymity_tier": anonymity_tier,
                "schedule_id": int(body.get("schedule_id") or 0),
                "launched_at": now,
                "closes_at": closes_at,
                "closed_at": None,
                "target_count": len(employee_ids),
                "voided_count": 0,
                "consent_notice_version": consent_notice_version,
                "email_delivery_status": "pending",
                "is_archived": False,
                "created_by": user_id,
                "created_at": now,
                "updated_at": now,
            },
        )
        survey_id = int(survey["id"])

        # Saga B: bulk-create responses.
        # Resolve user_ids for notification fanout.
        employees = dataflow_crud.list_records(
            "Employee", {"company_id": company_id}, limit=1000, cache_ttl=0
        )
        emp_by_id = {int(e["id"]): e for e in employees if e.get("id")}

        response_user_pairs: list[tuple[int, int]] = []
        for eid in employee_ids:
            emp = emp_by_id.get(eid)
            if not emp:
                continue
            response = dataflow_crud.create(
                "EngagementSurveyResponse",
                {
                    "company_id": company_id,
                    "survey_id": survey_id,
                    "employee_id": int(eid),
                    "employee_pseudonym": "",
                    "pseudonym_version": 0,
                    "survey_payload": "",
                    "likert_scores": "",
                    "themes": "",
                    "enps_score": None,
                    "response_cohort_attributes": "",
                    "idempotency_key": "",
                    "submitted_at": None,
                    "triggered_at": now,
                    "consent_notice_version": consent_notice_version,
                    "is_void": False,
                    "voided_at": None,
                    "is_archived": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            response_user_pairs.append((int(response["id"]), int(emp["user_id"])))

    # Saga C: fan out in-app notifications (Z10) — outside the lock to
    # not block the launch on slow notification writes.
    # C10 (red-team Phase 3): compute partial-vs-complete state from
    # the actual fanout count and store it on the survey row, so the
    # detail page can surface a "14/28 emails delivered, 14 retrying"
    # banner per the Z09 saga shape.
    notification_count = 0
    try:
        notification_count = notifications.bulk_create_engagement_pending(
            company_id=company_id,
            actor_user_id=user_id,
            survey_name=name,
            closes_at_iso=closes_at.isoformat(),
            response_user_pairs=response_user_pairs,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "engagement_notification_fanout_failed",
            extra={"survey_id": survey_id, "error": str(exc)},
        )

    if notification_count == len(response_user_pairs):
        delivery_status = "complete"
    elif notification_count > 0:
        delivery_status = "partial"
    else:
        delivery_status = "pending"

    try:
        dataflow_crud.update(
            "EngagementSurvey",
            survey_id,
            {"email_delivery_status": delivery_status, "updated_at": _now()},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "engagement_email_delivery_status_set_failed",
            extra={"survey_id": survey_id, "error": str(exc)},
        )

    return {
        "ok": True,
        "survey_id": survey_id,
        "target_count": len(employee_ids),
        "delivery_status": delivery_status,
        "delivered_count": notification_count,
    }


# ──────────────────────────────────────────────────────────────────────
# T32 — Survey list, detail, close
# ──────────────────────────────────────────────────────────────────────


def _enrich_survey(survey: dict) -> dict:
    """Add derived fields: response_count (Z07), response_rate."""
    if not survey:
        return survey
    sid = int(survey.get("id") or 0)
    survey["response_count"] = _count_submitted_responses(sid) if sid else 0
    target = int(survey.get("target_count") or 0)
    survey["response_rate"] = (
        round(survey["response_count"] / target, 3) if target else 0.0
    )
    return survey


@router.get("/surveys")
async def list_surveys(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    rows = dataflow_crud.list_records(
        "EngagementSurvey",
        {"company_id": company_id},
        limit=200,
        cache_ttl=0,
    )
    rows = [r for r in rows if not r.get("is_archived")]
    rows.sort(key=lambda r: r.get("launched_at") or "", reverse=True)
    for r in rows:
        _enrich_survey(r)
    return {"surveys": rows, "count": len(rows)}


@router.get("/surveys/trend")
async def get_trend(
    cohort: str = "all",
    window: int = 6,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """T34 — return the last N closed pulses' average likert + eNPS for
    the given cohort. Backs the hero chart on /engagement.

    `cohort` is one of: `all`, `department:Eng`, `pass_type:LongTerm`,
    `tenure_band:0-1y`, `manager:42`.
    """
    company_id = _resolve_company_id(current_user)
    if window <= 0 or window > 24:
        raise HTTPException(status_code=400, detail="window must be 1-24.")

    surveys = dataflow_crud.list_records(
        "EngagementSurvey",
        {"company_id": company_id},
        limit=200,
        cache_ttl=0,
    )
    closed = [s for s in surveys if s.get("closed_at")]
    closed.sort(key=lambda s: s.get("closed_at") or "")
    closed = closed[-window:]

    points: list[dict] = []
    for s in closed:
        agg = _build_aggregate(int(s["id"]), cohort_filter=cohort)
        points.append({
            "survey_id": int(s["id"]),
            "closed_at": s.get("closed_at"),
            "name": s.get("name"),
            "avg_likert": agg.get("overall_avg_likert"),
            "enps": agg.get("enps_score"),
            "n": agg.get("submitted_count"),
            "is_anonymity_safe": (agg.get("submitted_count") or 0) >= MIN_COHORT_SIZE,
        })
    return {
        "cohort_label": cohort,
        "window": window,
        "points": points,
    }


@router.get("/surveys/{survey_id}")
async def get_survey(
    survey_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    survey = dataflow_crud.read("EngagementSurvey", survey_id)
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Survey not found.")
    # D3 (red-team Phase 2): record HR's view timestamp so the
    # employee-side loop-closing card can differentiate "HR has been
    # notified" (no view yet) from "HR is reviewing" (admin has opened
    # the detail page) from "HR did Y" (action accepted).
    if survey.get("closed_at"):
        try:
            dataflow_crud.update(
                "EngagementSurvey",
                int(survey_id),
                {"last_viewed_by_admin_at": _now()},
            )
            survey["last_viewed_by_admin_at"] = _now().isoformat()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "engagement_survey_view_timestamp_failed",
                extra={"survey_id": survey_id, "error": str(exc)},
            )
    return {"survey": _enrich_survey(survey)}


@router.get("/surveys/{survey_id}/responses")
async def list_responses(
    survey_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List responses with anonymity-tier-aware labelling.

    - identified   → name + email
    - pseudonymous → "Respondent #abc1234"
    - anonymous    → "Anonymous"
    """
    company_id = _resolve_company_id(current_user)
    survey = dataflow_crud.read("EngagementSurvey", survey_id)
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Survey not found.")

    tier = (survey.get("anonymity_tier") or "identified").strip()
    rows = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"survey_id": int(survey_id)},
        limit=5000,
        cache_ttl=0,
    )
    rows = [r for r in rows if not r.get("is_archived")]

    # Resolve names only for identified tier.
    if tier == "identified":
        emp_ids = {int(r["employee_id"]) for r in rows if r.get("employee_id")}
        if emp_ids:
            employees = dataflow_crud.list_records(
                "Employee", {"company_id": company_id}, limit=1000, cache_ttl=0
            )
            emp_by_id = {int(e["id"]): e for e in employees if e.get("id")}
            user_ids = {emp_by_id[i].get("user_id") for i in emp_ids if i in emp_by_id}
            user_ids = {u for u in user_ids if u}
            users = dataflow_crud.list_records(
                "User", {"company_id": company_id}, limit=1000, cache_ttl=0
            )
            user_name_by_id = {int(u["id"]): u for u in users}

            # B5 (red-team): PDPA admin-access log wiring (Z16). HR
            # reading an identified employee's engagement response is
            # PDPA-relevant access — log it.
            from hr_advisory.api.routers.employees import _log_pdpa_access
            actor_id = int(current_user.get("sub") or 0)

            for r in rows:
                eid = r.get("employee_id")
                emp = emp_by_id.get(int(eid)) if eid else None
                u = user_name_by_id.get(int(emp["user_id"])) if emp else None
                if u:
                    r["employee_name"] = u.get("name", "")
                    r["employee_email"] = u.get("email", "")
                    _log_pdpa_access(
                        accessed_by=actor_id,
                        company_id=company_id,
                        data_subject_id=int(eid),
                        categories=["engagement_response"],
                        action="view_admin_response_list",
                    )
    elif tier == "pseudonymous":
        for r in rows:
            pseudo = r.get("employee_pseudonym") or ""
            r["employee_name"] = f"Respondent #{pseudo[:8]}" if pseudo else "Pending"
            r["employee_email"] = ""
    else:  # anonymous
        for r in rows:
            r["employee_name"] = "Anonymous"
            r["employee_email"] = ""

    return {"responses": rows, "count": len(rows), "anonymity_tier": tier}


@router.post("/surveys/{survey_id}/close")
async def close_survey(
    survey_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    survey = dataflow_crud.read("EngagementSurvey", survey_id)
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Survey not found.")
    if survey.get("closed_at"):
        return {"ok": True, "already_closed": True}
    now = _now()
    dataflow_crud.update(
        "EngagementSurvey",
        survey_id,
        {"closed_at": now, "updated_at": now},
    )
    return {"ok": True, "closed_at": now.isoformat()}


# ──────────────────────────────────────────────────────────────────────
# T31 — Employee in-app endpoints
# ──────────────────────────────────────────────────────────────────────


@router.get("/my-pending")
async def my_pending(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List the current user's pending (un-submitted, un-voided) responses
    for surveys that are still open."""
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    employee = _resolve_employee_for_user(user_id, company_id)
    if not employee:
        return {"pending": [], "count": 0}

    # DataFlow express has a multi-key filter bug for EngagementSurveyResponse:
    # `{company_id, employee_id}` returns only 1 row even when many match.
    # Workaround: list by company_id only, then filter in Python.
    rows = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"company_id": company_id},
        limit=2000,
        cache_ttl=0,
    )
    pending = [
        r for r in rows
        if int(r.get("employee_id") or 0) == int(employee["id"])
        and not r.get("submitted_at")
        and not r.get("is_void")
        and not r.get("is_archived")
    ]
    if not pending:
        return {"pending": [], "count": 0}

    surveys = {
        int(s["id"]): s
        for s in dataflow_crud.list_records(
            "EngagementSurvey", {"company_id": company_id}, limit=500, cache_ttl=0
        )
    }
    now = _now()
    out: list[dict] = []
    for r in pending:
        survey = surveys.get(int(r.get("survey_id") or 0))
        if not survey:
            continue
        # Skip surveys that are already closed.
        closes = survey.get("closes_at")
        if closes:
            try:
                closes_dt = (
                    closes if isinstance(closes, datetime)
                    else _parse_iso_datetime(str(closes))
                )
                closes_dt = _to_naive_utc(closes_dt) if isinstance(closes_dt, datetime) else closes_dt
                if isinstance(closes_dt, datetime) and closes_dt <= now:
                    continue
            except ValueError:
                pass
        out.append({
            "response_id": int(r["id"]),
            "survey_id": int(survey["id"]),
            "survey_name": survey.get("name", ""),
            "anonymity_tier": survey.get("anonymity_tier", "identified"),
            "closes_at": survey.get("closes_at"),
        })
    return {"pending": out, "count": len(out)}


@router.get("/my-history")
async def my_history(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submitted history.

    Identified surveys: full record (survey name + submitted_at + themes).
    Pseudonymous surveys: survey name + submitted_at only — themes,
        scores, and per-question content are suppressed because they
        could correlate back to the respondent.
    Anonymous surveys: still hidden — no re-identifiable trail exists.

    Bug #73: pseudonymous tier zeros employee_id at submit, so the
    naive employee_id lookup misses these rows entirely. We resolve them
    by computing this employee's pseudonym for each pseudonymous survey
    and matching on employee_pseudonym. Showing the employee her own
    submission record does not weaken HR-side pseudonymity (HR still
    sees only the pseudonym).
    """
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    employee = _resolve_employee_for_user(user_id, company_id)
    if not employee:
        return {"history": [], "count": 0}
    employee_id = int(employee["id"])

    rows = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"company_id": company_id},
        limit=2000,
        cache_ttl=0,
    )
    surveys = {
        int(s["id"]): s
        for s in dataflow_crud.list_records(
            "EngagementSurvey", {"company_id": company_id}, limit=500, cache_ttl=0
        )
    }

    # Resolve this employee's pseudonym per pseudonymous survey so we can
    # match the zeroed-employee_id rows back to her own submissions.
    pseudonym_lookup: dict[int, str] = {}
    secret: str | None = None
    for survey in surveys.values():
        tier = (survey.get("anonymity_tier") or "identified").strip()
        if tier != "pseudonymous":
            continue
        if secret is None:
            try:
                secret = engagement_pseudonym.get_or_create_company_secret(
                    company_id
                )
            except Exception:  # noqa: BLE001
                break
        pseudonym_lookup[int(survey["id"])] = (
            engagement_pseudonym.compute_pseudonym(
                secret, employee_id, int(survey["id"])
            )
        )

    out = []
    for r in rows:
        if not r.get("submitted_at") or r.get("is_void"):
            continue
        survey_id = int(r.get("survey_id") or 0)
        survey = surveys.get(survey_id)
        if not survey:
            continue
        tier = (survey.get("anonymity_tier") or "identified").strip()

        is_mine = False
        if tier == "identified":
            is_mine = int(r.get("employee_id") or 0) == employee_id
        elif tier == "pseudonymous":
            target_pseudonym = pseudonym_lookup.get(survey_id)
            is_mine = (
                target_pseudonym is not None
                and (r.get("employee_pseudonym") or "") == target_pseudonym
            )
        # Anonymous: skip — no trail.

        if not is_mine:
            continue

        entry = {
            "response_id": int(r["id"]),
            "survey_id": survey_id,
            "survey_name": survey.get("name", ""),
            "anonymity_tier": tier,
            "submitted_at": r.get("submitted_at"),
        }
        # Themes only on identified — themes on pseudonymous responses
        # could correlate the row back to the respondent if combined
        # with side-channel knowledge.
        if tier == "identified":
            entry["themes"] = r.get("themes", "")
        out.append(entry)

    out.sort(key=lambda e: e["submitted_at"] or "", reverse=True)
    return {"history": out, "count": len(out)}


@router.get("/my-responses/{response_id}/render")
async def render_my_response(
    response_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return template_sections_snapshot + parent survey metadata so the
    in-app form can render."""
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))

    response = dataflow_crud.read("EngagementSurveyResponse", response_id)
    if not response or int(response.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Response not found.")
    if response.get("is_void"):
        raise HTTPException(status_code=410, detail="Response is voided.")
    if response.get("submitted_at"):
        raise HTTPException(
            status_code=409,
            detail="Response already submitted.",
        )

    employee = _resolve_employee_for_user(user_id, company_id)
    if not employee or int(employee["id"]) != int(response.get("employee_id") or 0):
        raise HTTPException(status_code=403, detail="Not your response.")

    survey = dataflow_crud.read("EngagementSurvey", int(response["survey_id"]))
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Parent survey not found.")
    if survey.get("closed_at"):
        raise HTTPException(status_code=409, detail="Survey closed.")

    return {
        "response_id": response_id,
        "survey_id": int(survey["id"]),
        "survey_name": survey.get("name", ""),
        "anonymity_tier": survey.get("anonymity_tier", "identified"),
        "consent_notice_version": survey.get("consent_notice_version", ""),
        "template_sections_snapshot": survey.get("template_sections_snapshot", "[]"),
    }


def _check_csrf_or_origin(request: Request) -> None:
    """Z11 + red-team C3 — CSRF/Origin guard for in-app submit.

    Bearer auth is the primary defence. This is belt-and-braces for
    cookie-based sessions and stolen-token replay. Origin/Referer must
    match an entry in `settings.cors_origins`.

    No headers at all → trust Bearer (server-to-server caller).
    Headers present → strict allowlist check.
    """
    origin = request.headers.get("origin") or ""
    referer = request.headers.get("referer") or ""
    if not origin and not referer:
        return  # server-side caller via Bearer.

    # Pull the configured allowlist. Settings is the source of truth
    # for the CORS allowlist used by the Nexus platform; we reuse it
    # here so the engagement endpoints can never drift out of sync.
    from hr_advisory.config.settings import get_settings
    try:
        allowed = set(get_settings().cors_origins_list())
    except Exception:  # noqa: BLE001
        allowed = set()

    # `Origin: null` (sandboxed iframes, file://) always rejected.
    if origin and origin.startswith("null"):
        raise HTTPException(status_code=403, detail="Cross-origin denied.")

    if origin and allowed and origin not in allowed:
        raise HTTPException(status_code=403, detail="Cross-origin denied.")

    # Fallback to Referer if Origin missing — extract scheme://host
    # and compare. Lax — Referer can be omitted by privacy modes.
    if not origin and referer:
        try:
            from urllib.parse import urlparse
            r = urlparse(referer)
            ref_origin = f"{r.scheme}://{r.netloc}" if r.scheme else ""
            if ref_origin and allowed and ref_origin not in allowed:
                raise HTTPException(
                    status_code=403, detail="Cross-origin denied."
                )
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001
            # Malformed Referer — let the request through; Bearer is
            # the primary defence.
            pass


@router.post("/my-responses/{response_id}/submit")
async def submit_my_response(
    response_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """In-app submit handler — covers Z03 (cohort attrs), Z08 (idempotency),
    Z11 (CSRF), Z21 (voided check), anonymity branching."""
    _check_csrf_or_origin(request)

    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))

    response = dataflow_crud.read("EngagementSurveyResponse", response_id)
    if not response or int(response.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Response not found.")
    if response.get("is_void"):
        raise HTTPException(status_code=410, detail="Response is voided.")
    if response.get("submitted_at"):
        # Z08 idempotency: same key returns prior state (200, idempotent).
        idem_in = request.headers.get("idempotency-key") or ""
        prior_idem = response.get("idempotency_key") or ""
        if idem_in and idem_in == prior_idem:
            return {
                "ok": True,
                "idempotent_replay": True,
                "themes": json.loads(response.get("themes") or "[]"),
            }
        raise HTTPException(status_code=409, detail="Already submitted.")

    employee = _resolve_employee_for_user(user_id, company_id)
    if not employee or int(employee["id"]) != int(response.get("employee_id") or 0):
        raise HTTPException(status_code=403, detail="Not your response.")

    survey = dataflow_crud.read("EngagementSurvey", int(response["survey_id"]))
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Parent survey not found.")
    if survey.get("closed_at"):
        raise HTTPException(status_code=409, detail="Survey closed.")

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid request",
        )

    payload_json = json.dumps(body, sort_keys=True)
    if len(payload_json) > 50_000:
        raise HTTPException(status_code=413, detail="Payload too large.")

    # Z08: derive idempotency key if not provided.
    idem_in = (request.headers.get("idempotency-key") or "").strip()
    if not idem_in:
        idem_in = hashlib.sha256(
            f"{response_id}|{payload_json}".encode("utf-8")
        ).hexdigest()

    # Validate against template snapshot — at least one Likert answer.
    sections_raw = survey.get("template_sections_snapshot") or "[]"
    try:
        sections = json.loads(sections_raw)
    except json.JSONDecodeError:
        sections = []
    required_q_ids: list[str] = []
    free_text_keys: list[str] = []
    likert_keys: list[str] = []
    enps_keys: list[str] = []
    multi_keys: list[str] = []
    for section in sections:
        for q in section.get("questions") or []:
            qid = q.get("id")
            if not qid:
                continue
            if q.get("is_required"):
                required_q_ids.append(qid)
            qt = q.get("type")
            if qt in ("likert5",):
                likert_keys.append(qid)
            elif qt == "enps":
                enps_keys.append(qid)
            elif qt in ("short_text", "long_text"):
                free_text_keys.append(qid)
            elif qt == "multi":
                multi_keys.append(qid)

    missing = [q for q in required_q_ids if q not in body]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Invalid request",
        )

    # Compute likert_scores
    likert_scores = {
        k: int(body[k])
        for k in likert_keys
        if k in body and isinstance(body[k], (int, float))
    }
    enps_score = None
    for ek in enps_keys:
        if ek in body and isinstance(body[ek], (int, float)):
            enps_score = int(body[ek])
            break
    themes = theme_tagger.derive_themes(
        body,
        reason_keys=multi_keys,
        free_text_keys=free_text_keys,
    )

    now = _now()
    tier = (survey.get("anonymity_tier") or "identified").strip()
    cohort_attrs_json = _build_response_cohort_attributes(employee)

    updates: dict[str, Any] = {
        "survey_payload": payload_json,
        "likert_scores": json.dumps(likert_scores, sort_keys=True),
        "themes": json.dumps(themes),
        "enps_score": enps_score,
        "response_cohort_attributes": cohort_attrs_json,
        "idempotency_key": idem_in,
        "submitted_at": now,
        "consent_notice_version": survey.get("consent_notice_version", ""),
        "updated_at": now,
    }

    if tier == "identified":
        # Keep employee_id as is.
        updates["employee_pseudonym"] = ""
        updates["pseudonym_version"] = 0
    elif tier == "pseudonymous":
        # Resolve secret + compute pseudonym BEFORE zeroing employee_id.
        version = 1  # active version per Z02
        secret = engagement_pseudonym.get_or_create_company_secret(company_id)
        pseudo = engagement_pseudonym.compute_pseudonym(
            secret, int(employee["id"]), int(survey["id"])
        )
        updates["employee_pseudonym"] = pseudo
        updates["pseudonym_version"] = version
        updates["employee_id"] = 0
    else:  # anonymous
        updates["employee_pseudonym"] = ""
        updates["pseudonym_version"] = 0
        updates["employee_id"] = 0

    dataflow_crud.update("EngagementSurveyResponse", response_id, updates)

    # Resolve any pending notifications pointing at this response.
    # 4d (red-team Phase 3): log on failure rather than swallow silently.
    # The submit itself succeeded; we just couldn't dismiss the badge.
    try:
        notifications.mark_resolved_by_link(
            user_id, f"/my-engagement-surveys/{response_id}/respond"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "engagement_notification_mark_resolved_failed",
            extra={"response_id": response_id, "error": str(exc)},
        )

    return {"ok": True, "idempotent_replay": False, "themes": themes}


# ──────────────────────────────────────────────────────────────────────
# T33 — Aggregate
# ──────────────────────────────────────────────────────────────────────


def _build_aggregate(
    survey_id: int,
    *,
    cohort_filter: str = "all",
) -> dict:
    """T33 — aggregate per-question Likert + theme tally + eNPS.

    `cohort_filter` is one of:
      - "all"
      - "department:<name>"
      - "pass_type:<name>"
      - "tenure_band:<band>"
      - "manager:<id>"

    Anonymity gate: per-question and per-cohort cells with n<5 return
    `is_anonymity_safe=false` and don't expose distributions.
    """
    rows = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"survey_id": int(survey_id)},
        limit=5000,
        cache_ttl=0,
    )
    submitted = [
        r for r in rows
        if r.get("submitted_at") and not r.get("is_void")
    ]
    n_total = len(submitted)
    if n_total == 0:
        return {
            "submitted_count": 0,
            "is_anonymity_safe": False,
            "by_question": [],
            "by_cohort": [],
            "themes_tally": [],
            "enps_score": None,
            "overall_avg_likert": None,
        }

    # Parse helpers
    def _parse_likert(r: dict) -> dict:
        try:
            return json.loads(r.get("likert_scores") or "{}")
        except json.JSONDecodeError:
            return {}

    def _parse_attrs(r: dict) -> dict:
        try:
            return json.loads(r.get("response_cohort_attributes") or "{}")
        except json.JSONDecodeError:
            return {}

    # Apply cohort filter (Z03 frozen attrs, never live join)
    def _filter_match(r: dict) -> bool:
        if cohort_filter == "all":
            return True
        attrs = _parse_attrs(r)
        if cohort_filter.startswith("department:"):
            return attrs.get("department") == cohort_filter.split(":", 1)[1]
        if cohort_filter.startswith("pass_type:"):
            return attrs.get("pass_type") == cohort_filter.split(":", 1)[1]
        if cohort_filter.startswith("tenure_band:"):
            return attrs.get("tenure_band") == cohort_filter.split(":", 1)[1]
        return True

    filtered = [r for r in submitted if _filter_match(r)]
    n_filtered = len(filtered)
    is_safe = n_filtered >= MIN_COHORT_SIZE

    # Overall Likert avg
    all_likerts: list[float] = []
    for r in filtered:
        scores = _parse_likert(r)
        all_likerts.extend(float(v) for v in scores.values() if isinstance(v, (int, float)))
    overall_avg = round(sum(all_likerts) / len(all_likerts), 2) if all_likerts else None

    # Per-question distribution (suppressed if n<5)
    by_q: dict[str, list[float]] = {}
    for r in filtered:
        for k, v in _parse_likert(r).items():
            if isinstance(v, (int, float)):
                by_q.setdefault(k, []).append(float(v))
    by_question = []
    for qid, vals in by_q.items():
        if not is_safe:
            by_question.append({
                "question_id": qid,
                "n": len(vals),
                "is_anonymity_safe": False,
            })
        else:
            avg = round(sum(vals) / len(vals), 2) if vals else None
            distribution = {str(i): vals.count(float(i)) for i in range(1, 6)}
            by_question.append({
                "question_id": qid,
                "n": len(vals),
                "avg": avg,
                "distribution": distribution,
                "is_anonymity_safe": True,
            })

    # Per-cohort breakdown (Z03)
    cohort_buckets: dict[tuple[str, str], list[dict]] = {}
    for r in submitted:
        attrs = _parse_attrs(r)
        for axis_key in ("department", "pass_type", "tenure_band"):
            val = attrs.get(axis_key) or ""
            if val:
                cohort_buckets.setdefault((axis_key, val), []).append(r)
    by_cohort = []
    for (axis_key, val), bucket in cohort_buckets.items():
        likerts: list[float] = []
        themes_tally: dict[str, int] = {}
        for r in bucket:
            for v in _parse_likert(r).values():
                if isinstance(v, (int, float)):
                    likerts.append(float(v))
            try:
                themes = json.loads(r.get("themes") or "[]")
            except json.JSONDecodeError:
                themes = []
            for t in themes:
                themes_tally[t] = themes_tally.get(t, 0) + 1
        n_bucket = len(bucket)
        cell_safe = n_bucket >= MIN_COHORT_SIZE
        by_cohort.append({
            "label": f"{axis_key}:{val}",
            "axis": axis_key,
            "value": val,
            "n": n_bucket,
            "is_anonymity_safe": cell_safe,
            "avg_likert": (
                round(sum(likerts) / len(likerts), 2)
                if likerts and cell_safe
                else None
            ),
            "themes": (
                [
                    {"theme": k, "count": v}
                    for k, v in sorted(
                        themes_tally.items(), key=lambda kv: kv[1], reverse=True
                    )[:5]
                ]
                if cell_safe
                else []
            ),
        })

    # Theme tally across the filtered set
    themes_global: dict[str, int] = {}
    for r in filtered:
        try:
            themes = json.loads(r.get("themes") or "[]")
        except json.JSONDecodeError:
            themes = []
        for t in themes:
            themes_global[t] = themes_global.get(t, 0) + 1
    themes_sorted = sorted(themes_global.items(), key=lambda kv: kv[1], reverse=True)

    # eNPS
    promoter = passive = detractor = 0
    enps_n = 0
    for r in filtered:
        s = r.get("enps_score")
        if s is None:
            continue
        enps_n += 1
        if s >= 9:
            promoter += 1
        elif s >= 7:
            passive += 1
        else:
            detractor += 1
    enps_score = None
    if enps_n >= MIN_COHORT_SIZE:
        enps_score = round((promoter - detractor) * 100 / enps_n, 1)

    return {
        "submitted_count": n_filtered,
        "is_anonymity_safe": is_safe,
        "overall_avg_likert": overall_avg if is_safe else None,
        "by_question": by_question,
        "by_cohort": by_cohort,
        "themes_tally": [{"theme": k, "count": v} for k, v in themes_sorted],
        "enps_score": enps_score,
    }


@router.get("/surveys/{survey_id}/aggregate")
async def get_aggregate(
    survey_id: int,
    cohort: str = "all",
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    survey = dataflow_crud.read("EngagementSurvey", survey_id)
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Survey not found.")
    return _build_aggregate(survey_id, cohort_filter=cohort)


# ──────────────────────────────────────────────────────────────────────
# T35 — Manager view (round-3 pulled from P3)
# ──────────────────────────────────────────────────────────────────────


def _compute_manager_trend(
    *,
    company_id: int,
    scope: set[int],
    manager_id: int,
    max_points: int = 6,
) -> list[dict]:
    """Compute a 6-pulse mini trend for the manager's scope.

    Returns oldest → newest list of points:
      {"survey_id", "survey_name", "closed_at", "n", "avg_likert"}

    Skips pulses where n < MIN_COHORT_SIZE (consistent with the latest-
    pulse anonymity gate). Anonymous-tier surveys are skipped entirely.
    """
    surveys = dataflow_crud.list_records(
        "EngagementSurvey", {"company_id": company_id}, limit=200, cache_ttl=0
    )
    closed = [
        s for s in surveys
        if s.get("closed_at")
        and (s.get("anonymity_tier") or "identified").strip() != "anonymous"
    ]
    closed.sort(key=lambda s: s.get("closed_at") or "", reverse=True)
    closed = closed[:max_points]

    points: list[dict] = []
    for s in closed:
        sid = int(s["id"])
        tier = (s.get("anonymity_tier") or "identified").strip()
        rows = dataflow_crud.list_records(
            "EngagementSurveyResponse",
            {"survey_id": sid},
            limit=5000,
            cache_ttl=0,
        )

        if tier == "pseudonymous":
            try:
                secret = engagement_pseudonym.get_or_create_company_secret(
                    company_id
                )
            except Exception:  # noqa: BLE001
                continue
            scope_pseudonyms = {
                engagement_pseudonym.compute_pseudonym(secret, eid, sid)
                for eid in scope
            }
            mgr_pseudonym = engagement_pseudonym.compute_pseudonym(
                secret, manager_id, sid
            )
            submitted = [
                r for r in rows
                if r.get("submitted_at")
                and not r.get("is_void")
                and (r.get("employee_pseudonym") or "") in scope_pseudonyms
                and (r.get("employee_pseudonym") or "") != mgr_pseudonym
            ]
        else:
            submitted = [
                r for r in rows
                if r.get("submitted_at")
                and not r.get("is_void")
                and int(r.get("employee_id") or 0) in scope
                and int(r.get("employee_id") or 0) != manager_id
            ]

        n = len(submitted)
        if n < MIN_COHORT_SIZE:
            continue

        likerts: list[float] = []
        for r in submitted:
            try:
                scores = json.loads(r.get("likert_scores") or "{}")
                for v in scores.values():
                    if isinstance(v, (int, float)):
                        likerts.append(float(v))
            except json.JSONDecodeError:
                pass
        avg = round(sum(likerts) / len(likerts), 2) if likerts else None
        points.append({
            "survey_id": sid,
            "survey_name": s.get("name", ""),
            "closed_at": s.get("closed_at"),
            "n": n,
            "avg_likert": avg,
        })

    points.reverse()  # oldest → newest for chart consumption
    return points


@router.get("/team/aggregate")
async def get_team_aggregate(
    survey_id: int = 0,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Manager view — aggregate engagement for the manager's reports.

    Auth: any user with at least one direct report (resolved via
    `Employee.reporting_manager_id`). NOT gated by AdminGuard.
    n>=5 enforced with self-exclusion (Z26).
    """
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    employee = _resolve_employee_for_user(user_id, company_id)
    if not employee:
        raise HTTPException(status_code=403, detail="No employee record.")

    employees = dataflow_crud.list_records(
        "Employee", {"company_id": company_id}, limit=1000, cache_ttl=0
    )
    manager_id = int(employee["id"])

    # Direct + indirect reports (recursive 2 levels for P1).
    direct = {
        int(e["id"]) for e in employees
        if int(e.get("reporting_manager_id") or 0) == manager_id
        and e.get("is_active")
    }
    if not direct:
        raise HTTPException(
            status_code=403,
            detail="No direct reports — manager view not available.",
        )
    indirect: set[int] = set()
    for e in employees:
        mgr = int(e.get("reporting_manager_id") or 0)
        if mgr in direct and e.get("is_active"):
            indirect.add(int(e["id"]))
    scope = direct | indirect

    # Resolve target survey (latest closed if not specified).
    if survey_id:
        survey = dataflow_crud.read("EngagementSurvey", survey_id)
        if not survey or int(survey.get("company_id") or 0) != company_id:
            raise HTTPException(status_code=404, detail="Survey not found.")
    else:
        surveys = dataflow_crud.list_records(
            "EngagementSurvey", {"company_id": company_id}, limit=200, cache_ttl=0
        )
        closed = [s for s in surveys if s.get("closed_at")]
        if not closed:
            return {"is_visible": False, "reason": "no_closed_surveys"}
        closed.sort(key=lambda s: s.get("closed_at") or "", reverse=True)
        survey = closed[0]

    survey_id = int(survey["id"])
    survey_tier = (survey.get("anonymity_tier") or "identified").strip()

    # B2 (red-team): for pseudonymous tier, employee_id is zeroed at
    # submit. Filtering by employee_id then misses every submitted row
    # AND silently breaks Z26 self-exclusion (0 != manager_id). Build
    # the scope set in pseudonym-space when tier=pseudonymous, in
    # employee_id-space when tier=identified, and refuse to show for
    # tier=anonymous (no per-respondent identifier to filter on).
    if survey_tier == "anonymous":
        return {
            "is_visible": False,
            "scope_size": len(scope),
            "reason": "anonymity_tier_anonymous",
            "message": (
                "This survey was anonymous. Per-team aggregates are not "
                "available because there's no way to attribute responses "
                "to a team without re-identifying respondents."
            ),
        }

    rows = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"survey_id": survey_id},
        limit=5000,
        cache_ttl=0,
    )

    if survey_tier == "pseudonymous":
        # Resolve the pseudonym for each scope employee + the manager.
        # Pseudonyms are stable per (company, employee, survey) tuple.
        try:
            secret = engagement_pseudonym.get_or_create_company_secret(
                company_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "team_aggregate_pseudonym_secret_failed",
                extra={"company_id": company_id, "error": str(exc)},
            )
            return {
                "is_visible": False,
                "scope_size": len(scope),
                "reason": "secret_unavailable",
                "message": (
                    "Could not resolve the pseudonym secret. "
                    "Engineering should investigate."
                ),
            }
        scope_pseudonyms = {
            engagement_pseudonym.compute_pseudonym(secret, eid, survey_id)
            for eid in scope
        }
        manager_pseudonym = engagement_pseudonym.compute_pseudonym(
            secret, manager_id, survey_id
        )
        submitted = [
            r for r in rows
            if r.get("submitted_at")
            and not r.get("is_void")
            and (r.get("employee_pseudonym") or "") in scope_pseudonyms
            and (r.get("employee_pseudonym") or "") != manager_pseudonym
        ]
    else:
        # identified tier — filter on employee_id directly.
        submitted = [
            r for r in rows
            if r.get("submitted_at")
            and not r.get("is_void")
            and int(r.get("employee_id") or 0) in scope
            and int(r.get("employee_id") or 0) != manager_id
        ]

    n = len(submitted)

    # D1 (red-team Phase 2): SG-SME fit — at 28-employee scale, line
    # managers with 4-7 reports plus 75-85% submission plus self-exclusion
    # rarely reach the n>=5 floor. Suppressing entirely produces a dead
    # page most pulses, which buyers read as "this product wasn't built
    # for me."
    #
    # Three-band response now:
    #   - n < THEMES_ONLY_THRESHOLD (3): suppress entirely.
    #   - THEMES_ONLY_THRESHOLD <= n < MIN_COHORT_SIZE (3 or 4): themes-
    #     only mode. Themes are aggregated bucket names ("growth",
    #     "manager") with no per-respondent content, so PDPA/TAFEP-safe
    #     even at n=3.
    #   - n >= MIN_COHORT_SIZE (5): full aggregate.
    if n < THEMES_ONLY_THRESHOLD:
        return {
            "is_visible": False,
            "scope_size": len(scope),
            "n": n,
            "message": (
                "Your team is too small to see aggregated engagement "
                "data without risk of identifying individual responses. "
                "Roll up to your skip-level manager for visibility."
            ),
        }

    # Aggregate themes (always safe — bucket names, not content).
    themes_tally: dict[str, int] = {}
    for r in submitted:
        try:
            themes = json.loads(r.get("themes") or "[]")
            for t in themes:
                themes_tally[t] = themes_tally.get(t, 0) + 1
        except json.JSONDecodeError:
            pass
    themes_sorted = sorted(
        themes_tally.items(), key=lambda kv: kv[1], reverse=True
    )

    if n < MIN_COHORT_SIZE:
        # n is 3 or 4 — themes-only mode.
        return {
            "is_visible": True,
            "is_limited": True,
            "scope_size": len(scope),
            "n": n,
            "survey_id": survey_id,
            "survey_name": survey.get("name", ""),
            "avg_likert": None,
            "enps_score": None,
            "themes": [
                {"theme": k, "count": v} for k, v in themes_sorted[:10]
            ],
            "message": (
                f"Limited preview: themes only. With {n} response"
                f"{'s' if n != 1 else ''} we don't show individual "
                "scores to protect anonymity. Roll up to your skip-level "
                "manager for the full picture."
            ),
        }

    # n >= MIN_COHORT_SIZE: full aggregate.
    likerts: list[float] = []
    by_q: dict[str, list[float]] = {}
    promoter = detractor = enps_n = 0
    for r in submitted:
        try:
            scores = json.loads(r.get("likert_scores") or "{}")
            for qid, v in scores.items():
                if isinstance(v, (int, float)):
                    likerts.append(float(v))
                    by_q.setdefault(qid, []).append(float(v))
        except json.JSONDecodeError:
            pass
        s = r.get("enps_score")
        if s is not None:
            enps_n += 1
            if s >= 9:
                promoter += 1
            elif s < 7:
                detractor += 1
    avg = round(sum(likerts) / len(likerts), 2) if likerts else None
    enps = (
        round((promoter - detractor) * 100 / enps_n, 1) if enps_n else None
    )

    # Per-question breakdown — let the manager see WHICH dimensions are
    # weakest, not just the aggregate. Question text resolved from the
    # template snapshot frozen on the survey at launch (Z03).
    question_text_lookup: dict[str, str] = {}
    try:
        sections = json.loads(survey.get("template_sections_snapshot") or "[]")
        for sec in sections:
            for q in sec.get("questions", []) or []:
                qid = q.get("id")
                qtext = q.get("text")
                if qid and qtext:
                    question_text_lookup[str(qid)] = str(qtext)
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    by_question = sorted(
        (
            {
                "question_id": qid,
                "question_text": question_text_lookup.get(qid, qid),
                "n": len(vals),
                "avg": round(sum(vals) / len(vals), 2),
            }
            for qid, vals in by_q.items()
            if vals
        ),
        key=lambda r: r["avg"],  # ascending — lowest first surfaces problems
    )

    # 6-pulse mini trend for this manager's scope. Same Z26 self-exclusion,
    # same pseudonym/identified scoping per pulse. Only Likert avg + n
    # per pulse — no per-question, no themes (kept compact). Bounded to
    # the 6 most recent closed surveys for this company.
    trend_points = _compute_manager_trend(
        company_id=company_id,
        scope=scope,
        manager_id=manager_id,
        max_points=6,
    )

    return {
        "is_visible": True,
        "is_limited": False,
        "scope_size": len(scope),
        "n": n,
        "survey_id": survey_id,
        "survey_name": survey.get("name", ""),
        "avg_likert": avg,
        "enps_score": enps,
        "themes": [{"theme": k, "count": v} for k, v in themes_sorted[:10]],
        "by_question": by_question,
        "trend": trend_points,
    }


# ──────────────────────────────────────────────────────────────────────
# T36, T37 — Suggested actions + action endpoints
# ──────────────────────────────────────────────────────────────────────


@router.get("/surveys/{survey_id}/suggested-actions")
async def get_suggested_actions(
    survey_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    survey = dataflow_crud.read("EngagementSurvey", survey_id)
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Survey not found.")
    aggregate = _build_aggregate(survey_id, cohort_filter="all")
    return engagement_actions_svc.suggest_actions_for_lowest_cohort(
        survey_id, aggregate_data=aggregate
    )


@router.post("/surveys/{survey_id}/actions")
async def create_action(
    survey_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create an action (typically accept-from-suggestion). Optional
    one-click create-linked-goal."""
    company_id = _resolve_company_id(current_user)
    user_id = int(current_user.get("sub", 0))
    survey = dataflow_crud.read("EngagementSurvey", survey_id)
    if not survey or int(survey.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Survey not found.")

    body = await request.json()
    suggested_action_text = (body.get("suggested_action_text") or "").strip()
    if not suggested_action_text:
        raise HTTPException(
            status_code=400, detail="suggested_action_text is required."
        )

    cohort_label = (body.get("cohort_label") or "").strip()
    finding_summary = (body.get("finding_summary") or "").strip()
    next_pulse_question = (body.get("next_pulse_question") or "").strip()
    # D4 (red-team Phase 2): explicit theme stored on the action so the
    # loop-closing lookup uses exact-match, not substring scan.
    theme = (body.get("theme") or "").strip().lower()
    create_linked_goal = bool(body.get("create_linked_goal"))

    linked_goal_id = 0
    if create_linked_goal:
        # Use existing Goals module shape from models/company_user.py.
        # Goal fields: company_id, employee_id (required), manager_id,
        # title, description, status, progress_pct, ...
        now = _now()
        goal_title = (
            body.get("goal_title")
            or f"Engagement action: {suggested_action_text[:80]}"
        )
        # Resolve the HR creator's employee_id for ownership; fall
        # back to 0 (company-wide) if the user has no Employee row.
        creator_emp = _resolve_employee_for_user(user_id, company_id)
        owner_emp_id = int(creator_emp["id"]) if creator_emp else 0
        # B7 (red-team): the action endpoint USED to swallow goal-create
        # failures and return success with linked_goal_id=0, leaving the
        # client to discover the missing goal later. Now we surface the
        # failure explicitly — if create_linked_goal=true and the Goal
        # create fails, fail the whole request 502 so the caller can
        # retry without a half-created action.
        try:
            goal = dataflow_crud.create(
                "Goal",
                {
                    "company_id": company_id,
                    "employee_id": owner_emp_id,
                    "manager_id": 0,
                    "period_id": 0,
                    "title": goal_title,
                    "description": (
                        f"Auto-created from engagement survey #{survey_id}. "
                        f"Cohort: {cohort_label or 'all'}. "
                        f"Finding: {finding_summary or 'low engagement'}."
                    ),
                    "metric": "",
                    "target_value": "",
                    "start_date": "",
                    "due_date": "",
                    "status": "draft",
                    "progress_pct": 0,
                    "is_archived": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            linked_goal_id = int(goal.get("id") or 0)
            if linked_goal_id <= 0:
                raise RuntimeError(
                    f"Goal create returned no id: {goal!r}"
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "engagement_action_linked_goal_create_failed",
                extra={
                    "survey_id": survey_id,
                    "cohort_label": cohort_label,
                    "error": str(exc),
                },
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Linked goal could not be created. The action was "
                    "not saved. Retry, or accept without create_linked_goal."
                ),
            ) from exc

    now = _now()
    record = dataflow_crud.create(
        "EngagementAction",
        {
            "company_id": company_id,
            "survey_id": survey_id,
            "cohort_label": cohort_label,
            "finding_summary": finding_summary,
            "suggested_action_text": suggested_action_text,
            "theme": theme,
            "status": (body.get("status") or "accepted").strip(),
            "linked_goal_id": linked_goal_id,
            "next_pulse_question": next_pulse_question,
            "next_pulse_survey_id": 0,
            "resolved_at": None,
            "resolved_score_delta": None,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"action": record}


_ACTION_PATCH_FIELDS = {
    "status",
    "suggested_action_text",
    "linked_goal_id",
    "next_pulse_question",
    "next_pulse_survey_id",
}


@router.patch("/actions/{action_id}")
async def update_action(
    action_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    existing = dataflow_crud.read("EngagementAction", action_id)
    if not existing or int(existing.get("company_id") or 0) != company_id:
        raise HTTPException(status_code=404, detail="Action not found.")
    body = await request.json()
    updates = {k: v for k, v in body.items() if k in _ACTION_PATCH_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")
    if "status" in updates and updates["status"] not in (
        "proposed",
        "accepted",
        "rejected",
        "done",
    ):
        raise HTTPException(status_code=400, detail="Invalid status.")
    now = _now()
    updates["updated_at"] = now
    if updates.get("status") in ("done", "rejected"):
        updates["resolved_at"] = now
    result = dataflow_crud.update("EngagementAction", action_id, updates)
    return {"action": result}


@router.get("/actions")
async def list_actions(
    survey_id: int = 0,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = _resolve_company_id(current_user)
    where: dict[str, Any] = {"company_id": company_id}
    if survey_id:
        where["survey_id"] = int(survey_id)
    rows = dataflow_crud.list_records(
        "EngagementAction", where, limit=500, cache_ttl=0
    )
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"actions": rows, "count": len(rows)}


# ──────────────────────────────────────────────────────────────────────
# T38 — Loop-closing card
# ──────────────────────────────────────────────────────────────────────


@router.get("/my-loop-closing")
async def get_loop_closing(
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = _resolve_company_id(current_user)
    payload = engagement_actions_svc.compute_loop_closing_payload(company_id)
    if payload is None:
        return {"payload": None}
    return {"payload": payload}
