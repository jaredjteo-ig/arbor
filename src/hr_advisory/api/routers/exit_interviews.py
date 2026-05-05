"""Exit interview router — P2-EX obayashi.

Auto-creates an ExitInterview row when an EmploymentEvent of type
RESIGNED/TERMINATED/RETRENCHED is written. Sends a tokenized survey
link to the leaver. Admin views aggregated themes per period.

Endpoints:
  POST /exit-interviews/trigger             — manual trigger (admin)
  GET  /exit-interviews                     — admin list
  GET  /exit-interviews/{id}                — admin detail
  POST /exit-interviews/{token}/submit      — public submit via token
  GET  /exit-interviews/themes              — derived theme tally
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import (
    get_current_user,
    require_role,
)
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.config.settings import get_settings
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)
router = APIRouter()

EXIT_TOKEN_AUD = "arbor.exit-interview"
EXIT_TOKEN_EXPIRY_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _settings():
    return get_settings()


def _make_token(interview_id: int, company_id: int) -> str:
    s = _settings()
    payload = {
        "iss": "arbor",
        "aud": EXIT_TOKEN_AUD,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(
            datetime.now(timezone.utc).timestamp()
            + EXIT_TOKEN_EXPIRY_DAYS * 86400
        ),
        "ei": interview_id,
        "co": company_id,
    }
    return jwt.encode(payload, s.jwt_secret_key, algorithm="HS256")


def _decode_token(token: str) -> dict:
    s = _settings()
    try:
        return jwt.decode(
            token,
            s.jwt_secret_key,
            algorithms=["HS256"],
            audience=EXIT_TOKEN_AUD,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc


def _theme_tags(payload: dict) -> list[str]:
    """Lightweight, deterministic theme derivation.

    Uses the multi-pick reasons (Q3) as the primary tag source plus a
    keyword sweep over the free-text answers. No LLM call by default —
    keeps cost predictable and is enough to drive the Themes view.
    """
    tags: set[str] = set()
    reasons = payload.get("q3_reasons") or []
    if isinstance(reasons, list):
        for r in reasons:
            tags.add(str(r).strip().lower())

    text_blob = " ".join(
        str(payload.get(k) or "")
        for k in ("q4_what_worked", "q5_what_to_change", "q6_recommend_why")
    ).lower()
    keyword_map = {
        "manager": ["manager", "boss", "supervisor"],
        "comp": ["pay", "salary", "compensation", "bonus"],
        "growth": ["growth", "promotion", "career"],
        "workload": ["workload", "burnout", "overworked"],
        "culture": ["culture", "environment"],
        "role": ["role", "scope", "fit"],
    }
    for theme, kws in keyword_map.items():
        if any(k in text_blob for k in kws):
            tags.add(theme)

    return sorted(tags)


@router.post("/trigger")
async def trigger_interview(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Admin: manually create an exit interview for an employee.

    The auto-trigger path lives in the employees router termination flow
    (when ExitInterview model is registered). This endpoint exists so
    admins can backfill or re-send.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    employee_id = body.get("employee_id")
    is_anonymous = bool(body.get("is_anonymous", False))
    if not employee_id:
        raise HTTPException(
            status_code=400, detail="employee_id is required."
        )

    target = dataflow_crud.list_records(
        "Employee",
        {"id": int(employee_id), "company_id": company_id},
        cache_ttl=0,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Employee not found.")

    now = _now()
    record = dataflow_crud.create(
        "ExitInterview",
        {
            "company_id": company_id,
            "employee_id": int(employee_id),
            "triggered_at": now,
            "triggered_by_event_id": int(body.get("event_id") or 0),
            "survey_payload": "",
            "themes": "",
            "is_anonymous": is_anonymous,
            "submitted_at": None,
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    token = _make_token(record["id"], company_id)
    return {"interview": record, "submit_token": token}


@router.get("")
async def list_interviews(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    rows = dataflow_crud.list_records(
        "ExitInterview", {"company_id": company_id}, cache_ttl=0
    )
    rows = [r for r in rows if not r.get("is_archived")]
    rows.sort(key=lambda r: r.get("triggered_at") or "", reverse=True)

    # Anonymous-mode redaction.
    redacted = []
    for r in rows:
        if r.get("is_anonymous"):
            r2 = dict(r)
            r2["employee_id"] = 0
            redacted.append(r2)
        else:
            redacted.append(r)
    return {"interviews": redacted, "count": len(redacted)}


@router.get("/themes")
async def list_themes(
    since: str | None = None,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    rows = dataflow_crud.list_records(
        "ExitInterview", {"company_id": company_id}, cache_ttl=0
    )
    submitted = [r for r in rows if r.get("submitted_at")]
    if since:
        submitted = [r for r in submitted if (r.get("submitted_at") or "") >= since]

    tally: dict[str, int] = {}
    for r in submitted:
        themes_raw = r.get("themes") or ""
        try:
            themes = json.loads(themes_raw) if themes_raw else []
        except json.JSONDecodeError:
            themes = []
        for t in themes:
            tally[t] = tally.get(t, 0) + 1

    response_rate = (
        len(submitted) / len(rows) if rows else 0.0
    )
    return {
        "tally": [
            {"theme": k, "count": v}
            for k, v in sorted(
                tally.items(), key=lambda x: x[1], reverse=True
            )
        ],
        "submitted_count": len(submitted),
        "total_triggered": len(rows),
        "response_rate": round(response_rate, 2),
    }


@router.get("/{interview_id}")
async def get_interview(
    interview_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    rows = dataflow_crud.list_records(
        "ExitInterview",
        {"id": interview_id, "company_id": company_id},
        cache_ttl=0,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Interview not found.")
    interview = rows[0]
    if interview.get("is_anonymous"):
        interview = dict(interview)
        interview["employee_id"] = 0
    return {"interview": interview}


@router.post("/{token}/submit")
async def submit_interview(token: str, request: Request) -> dict:
    """Public — leaver submits via tokenized link (no auth)."""
    decoded = _decode_token(token)
    interview_id = int(decoded.get("ei", 0))
    company_id = int(decoded.get("co", 0))

    rows = dataflow_crud.list_records(
        "ExitInterview",
        {"id": interview_id, "company_id": company_id},
        cache_ttl=0,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Interview not found.")
    interview = rows[0]
    if interview.get("submitted_at"):
        raise HTTPException(
            status_code=409, detail="This interview was already submitted."
        )

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object.")

    survey_json = json.dumps(body)
    if len(survey_json) > 20000:
        raise HTTPException(
            status_code=413, detail="Submission too large."
        )
    themes = _theme_tags(body)

    now = _now()
    dataflow_crud.update(
        "ExitInterview",
        interview_id,
        {
            "survey_payload": survey_json,
            "themes": json.dumps(themes),
            "submitted_at": now,
            "updated_at": now,
        },
    )
    return {"ok": True, "themes": themes}
