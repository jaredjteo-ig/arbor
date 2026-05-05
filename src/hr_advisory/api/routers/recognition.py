"""Recognition router — P2-RC obayashi.

Closes the missing leg of Cox lifecycle stage 6 (Reward · Recognition ·
Benefits). Endpoints:

  GET  /recognition                       — list public + my received
  POST /recognition                       — give kudos
  GET  /recognition/feed                  — public feed (last 30d, capped)
  GET  /recognition/received              — kudos received by current user
  GET  /recognition/categories            — enum source of truth for the UI
  GET  /recognition/nominations           — admin tally per period
  POST /recognition/nominate              — submit a peer nomination
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import (
    get_current_user,
    require_role,
)
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CATEGORIES = {
    "above_and_beyond",
    "teamwork",
    "customer",
    "innovation",
    "values",
}

CATEGORY_LABELS = {
    "above_and_beyond": "Above and Beyond",
    "teamwork": "Teamwork",
    "customer": "Customer Focus",
    "innovation": "Innovation",
    "values": "Lives the Values",
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _list_active(model: str, company_id: int) -> list[dict]:
    rows = dataflow_crud.list_records(
        model, {"company_id": company_id}, cache_ttl=0
    )
    return [r for r in rows if not r.get("is_archived")]


@router.get("/categories")
async def list_categories(
    current_user: dict = Depends(get_current_user),
) -> dict:
    return {
        "categories": [
            {"key": k, "label": v} for k, v in CATEGORY_LABELS.items()
        ]
    }


@router.get("")
async def list_recognition(
    scope: str = Query("public", pattern="^(public|received)$"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    rows = _list_active("Recognition", company_id)
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)

    if scope == "public":
        rows = [r for r in rows if r.get("is_public")]
    elif scope == "received":
        # Resolve current user's employee_id, then filter to_employee_id==me.
        user_id = int(current_user.get("sub", 0))
        emp_rows = dataflow_crud.list_records(
            "Employee",
            {"company_id": company_id, "user_id": user_id},
            cache_ttl=0,
        )
        if not emp_rows:
            return {"recognition": [], "count": 0, "scope": scope}
        my_emp_id = emp_rows[0].get("id")
        rows = [r for r in rows if r.get("to_employee_id") == my_emp_id]

    return {
        "recognition": rows[:limit],
        "count": len(rows[:limit]),
        "scope": scope,
    }


@router.get("/feed")
async def feed(
    days: int = Query(30, ge=1, le=180),
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    cutoff = (_now() - timedelta(days=days)).isoformat()
    rows = _list_active("Recognition", company_id)
    rows = [
        r
        for r in rows
        if r.get("is_public") and (r.get("created_at") or "") >= cutoff
    ]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"feed": rows[:50], "count": len(rows[:50]), "days": days}


@router.get("/received")
async def received(current_user: dict = Depends(get_current_user)) -> dict:
    """Same as `?scope=received` for callers that want a dedicated route."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    emp_rows = dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "user_id": user_id},
        cache_ttl=0,
    )
    if not emp_rows:
        return {"recognition": [], "count": 0}
    my_emp_id = emp_rows[0].get("id")
    rows = _list_active("Recognition", company_id)
    rows = [r for r in rows if r.get("to_employee_id") == my_emp_id]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"recognition": rows, "count": len(rows)}


@router.post("")
async def give_recognition(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"recognition_give:{user_id}",
        max_requests=20,
        window_seconds=3600,
        action_name="give recognition",
    )

    body = await request.json()
    to_emp = body.get("to_employee_id")
    msg = (body.get("message") or "").strip()
    category = body.get("category", "above_and_beyond")
    if not to_emp or not msg:
        raise HTTPException(
            status_code=400,
            detail="to_employee_id and message are required.",
        )
    if len(msg) > 1000:
        raise HTTPException(
            status_code=400, detail="message must be <= 1000 characters."
        )
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"category must be one of {sorted(ALLOWED_CATEGORIES)}",
        )

    # Tenant guard: nominee must belong to the same company.
    target = dataflow_crud.list_records(
        "Employee",
        {"id": int(to_emp), "company_id": company_id},
        cache_ttl=0,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Recipient not found.")

    now = _now()
    record = dataflow_crud.create(
        "Recognition",
        {
            "company_id": company_id,
            "from_user_id": user_id,
            "to_employee_id": int(to_emp),
            "category": category,
            "message": msg,
            "is_public": bool(body.get("is_public", True)),
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"recognition": record}


@router.post("/nominate")
async def nominate(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"recognition_nominate:{user_id}",
        max_requests=5,
        window_seconds=86400,
        action_name="peer nomination",
    )

    body = await request.json()
    nominee = body.get("nominee_employee_id")
    period = (body.get("period") or _now().strftime("%Y-%m")).strip()
    rationale = (body.get("rationale") or "").strip()
    category = body.get("category", "above_and_beyond")
    if not nominee or not rationale:
        raise HTTPException(
            status_code=400,
            detail="nominee_employee_id and rationale are required.",
        )
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="invalid category")

    target = dataflow_crud.list_records(
        "Employee",
        {"id": int(nominee), "company_id": company_id},
        cache_ttl=0,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Nominee not found.")

    now = _now()
    record = dataflow_crud.create(
        "PeerNomination",
        {
            "company_id": company_id,
            "nominator_user_id": user_id,
            "nominee_employee_id": int(nominee),
            "period": period,
            "category": category,
            "rationale": rationale,
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"nomination": record}


@router.get("/nominations")
async def list_nominations(
    period: str | None = None,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Admin: tally peer nominations per period."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    rows = _list_active("PeerNomination", company_id)
    if period:
        rows = [r for r in rows if r.get("period") == period]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)

    # Tally by nominee.
    tally: dict[int, int] = {}
    for r in rows:
        eid = r.get("nominee_employee_id")
        if eid is None:
            continue
        tally[eid] = tally.get(eid, 0) + 1

    return {
        "nominations": rows,
        "count": len(rows),
        "tally": [
            {"employee_id": eid, "count": cnt}
            for eid, cnt in sorted(
                tally.items(), key=lambda x: x[1], reverse=True
            )
        ],
    }
