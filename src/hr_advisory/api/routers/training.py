"""Training (L&D) router — P2-LD obayashi.

Endpoints:
  TrainingRecord CRUD                        /training/records*
  Certification CRUD + expiring filter       /training/certifications*
  MandatoryTrainingRequirement CRUD          /training/mandatory*
  Mandatory-coverage derived view            GET /training/mandatory/coverage

The existing /training/skillsfuture endpoints already live on the
integrations router; this router adds the missing in-house records
that the lifecycle dashboard's L&D stage reads.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _verify_record_ownership(
    model: str, record_id: int, company_id: int
) -> dict:
    rows = dataflow_crud.list_records(
        model, {"id": record_id, "company_id": company_id}, cache_ttl=0
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"{model} not found.")
    return rows[0]


# ---------------------------------------------------------------------------
# Training records
# ---------------------------------------------------------------------------


@router.get("/records")
async def list_training_records(
    employee_id: int | None = None,
    course_type: str | None = None,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict[str, Any] = {"company_id": company_id}
    if employee_id is not None:
        filters["employee_id"] = employee_id
    if course_type:
        filters["course_type"] = course_type

    records = dataflow_crud.list_records(
        "TrainingRecord", filters, cache_ttl=0
    )
    # DataFlow's filter_dict doesn't reliably match Python False → PG false,
    # so post-filter is_archived in Python.
    if not include_archived:
        records = [r for r in records if not r.get("is_archived")]
    return {"records": records, "count": len(records)}


@router.post("/records")
async def create_training_record(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"training_record_create:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="create training record",
    )

    body = await request.json()
    employee_id = body.get("employee_id")
    course_name = (body.get("course_name") or "").strip()
    if not employee_id or not course_name:
        raise HTTPException(
            status_code=400,
            detail="employee_id and course_name are required.",
        )

    now = _now()
    record = dataflow_crud.create(
        "TrainingRecord",
        {
            "company_id": company_id,
            "employee_id": int(employee_id),
            "course_name": course_name,
            "course_provider": (body.get("course_provider") or "").strip(),
            "course_type": body.get("course_type", "internal"),
            "start_date": body.get("start_date") or "",
            "completion_date": body.get("completion_date") or "",
            "hours": float(body.get("hours") or 0.0),
            "cost": float(body.get("cost") or 0.0),
            "funding_source": body.get("funding_source", "employer"),
            "certificate_url": body.get("certificate_url") or "",
            "notes": body.get("notes") or "",
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"record": record}


@router.get("/records/{record_id}")
async def get_training_record(
    record_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    record = _verify_record_ownership("TrainingRecord", record_id, company_id)
    return {"record": record}


@router.patch("/records/{record_id}")
async def update_training_record(
    record_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    _verify_record_ownership("TrainingRecord", record_id, company_id)

    body = await request.json()
    allowed = {
        "course_name",
        "course_provider",
        "course_type",
        "start_date",
        "completion_date",
        "hours",
        "cost",
        "funding_source",
        "certificate_url",
        "notes",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")
    if "hours" in updates:
        updates["hours"] = float(updates["hours"])
    if "cost" in updates:
        updates["cost"] = float(updates["cost"])
    updates["updated_at"] = _now()
    dataflow_crud.update("TrainingRecord", record_id, updates)
    updated = dataflow_crud.read("TrainingRecord", record_id)
    return {"record": updated}


@router.delete("/records/{record_id}")
async def archive_training_record(
    record_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    _verify_record_ownership("TrainingRecord", record_id, company_id)
    dataflow_crud.update(
        "TrainingRecord",
        record_id,
        {"is_archived": True, "updated_at": _now()},
    )
    return {"message": "Training record archived.", "id": record_id}


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


@router.get("/certifications")
async def list_certifications(
    employee_id: int | None = None,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    filters: dict[str, Any] = {"company_id": company_id}
    if employee_id is not None:
        filters["employee_id"] = employee_id

    records = dataflow_crud.list_records(
        "Certification", filters, cache_ttl=0
    )
    if not include_archived:
        records = [r for r in records if not r.get("is_archived")]
    return {"certifications": records, "count": len(records)}


@router.get("/certifications/expiring")
async def list_expiring_certifications(
    within_days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    today = date.today()
    cutoff = (today + timedelta(days=within_days)).isoformat()
    today_iso = today.isoformat()

    all_rows = dataflow_crud.list_records(
        "Certification",
        {"company_id": company_id},
        cache_ttl=0,
    )
    rows = [r for r in all_rows if not r.get("is_archived")]

    expired = []
    expiring = []
    for r in rows:
        exp = (r.get("expires_at") or "").strip()
        if not exp:
            continue
        if exp < today_iso:
            expired.append(r)
        elif exp <= cutoff:
            expiring.append(r)

    return {
        "expired": expired,
        "expiring": expiring,
        "active_total": len(rows),
        "within_days": within_days,
    }


@router.post("/certifications")
async def create_certification(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(
        f"cert_create:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="create certification",
    )

    body = await request.json()
    employee_id = body.get("employee_id")
    cert_name = (body.get("certification_name") or "").strip()
    if not employee_id or not cert_name:
        raise HTTPException(
            status_code=400,
            detail="employee_id and certification_name are required.",
        )

    now = _now()
    record = dataflow_crud.create(
        "Certification",
        {
            "company_id": company_id,
            "employee_id": int(employee_id),
            "certification_name": cert_name,
            "issuing_body": body.get("issuing_body") or "",
            "issued_date": body.get("issued_date") or "",
            "expires_at": body.get("expires_at") or "",
            "cert_number": body.get("cert_number") or "",
            "attachment_url": body.get("attachment_url") or "",
            "notes": body.get("notes") or "",
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"certification": record}


@router.patch("/certifications/{cert_id}")
async def update_certification(
    cert_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    _verify_record_ownership("Certification", cert_id, company_id)

    body = await request.json()
    allowed = {
        "certification_name",
        "issuing_body",
        "issued_date",
        "expires_at",
        "cert_number",
        "attachment_url",
        "notes",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")
    updates["updated_at"] = _now()
    dataflow_crud.update("Certification", cert_id, updates)
    return {"certification": dataflow_crud.read("Certification", cert_id)}


@router.delete("/certifications/{cert_id}")
async def archive_certification(
    cert_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    _verify_record_ownership("Certification", cert_id, company_id)
    dataflow_crud.update(
        "Certification", cert_id, {"is_archived": True, "updated_at": _now()}
    )
    return {"message": "Certification archived.", "id": cert_id}


# ---------------------------------------------------------------------------
# Mandatory training requirements
# ---------------------------------------------------------------------------


@router.get("/mandatory")
async def list_mandatory_requirements(
    current_user: dict = Depends(get_current_user),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    all_rows = dataflow_crud.list_records(
        "MandatoryTrainingRequirement",
        {"company_id": company_id},
        cache_ttl=0,
    )
    rows = [r for r in all_rows if r.get("is_active")]
    return {"requirements": rows, "count": len(rows)}


@router.post("/mandatory")
async def create_mandatory_requirement(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = (body.get("requirement_name") or "").strip()
    cert = (body.get("required_certification_name") or "").strip()
    if not name or not cert:
        raise HTTPException(
            status_code=400,
            detail="requirement_name and required_certification_name are required.",
        )

    now = _now()
    record = dataflow_crud.create(
        "MandatoryTrainingRequirement",
        {
            "company_id": company_id,
            "requirement_name": name,
            "applicable_to": body.get("applicable_to", "all"),
            "required_certification_name": cert,
            "due_within_days_of_hire": int(
                body.get("due_within_days_of_hire") or 90
            ),
            "is_active": True,
            "notes": body.get("notes") or "",
            "created_at": now,
            "updated_at": now,
        },
    )
    return {"requirement": record}


@router.patch("/mandatory/{req_id}")
async def update_mandatory_requirement(
    req_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    company_id = get_current_company_id(current_user)
    _verify_record_ownership(
        "MandatoryTrainingRequirement", req_id, company_id
    )

    body = await request.json()
    allowed = {
        "requirement_name",
        "applicable_to",
        "required_certification_name",
        "due_within_days_of_hire",
        "is_active",
        "notes",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")
    if "due_within_days_of_hire" in updates:
        updates["due_within_days_of_hire"] = int(
            updates["due_within_days_of_hire"]
        )
    updates["updated_at"] = _now()
    dataflow_crud.update("MandatoryTrainingRequirement", req_id, updates)
    return {
        "requirement": dataflow_crud.read(
            "MandatoryTrainingRequirement", req_id
        )
    }


def _employee_matches_rule(emp: dict, applicable_to: str) -> bool:
    """Match an employee against a requirement's applicable_to selector."""
    if applicable_to == "all":
        return True
    if ":" not in applicable_to:
        return False
    field, target = applicable_to.split(":", 1)
    target = target.strip().lower()
    if field == "department":
        return (emp.get("department") or "").strip().lower() == target
    if field == "pass_type":
        return (emp.get("pass_type") or "").strip().lower() == target
    if field == "role":
        return (emp.get("designation") or "").strip().lower() == target
    return False


@router.get("/mandatory/coverage")
async def mandatory_coverage(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """For each requirement, list compliant + non-compliant employees.

    An employee is compliant when they hold an active (non-archived,
    non-expired) certification whose name matches the requirement's
    `required_certification_name`. The match is case-insensitive +
    whitespace-collapsed, same convention as the round-12 H4 helper.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    today_iso = date.today().isoformat()
    all_reqs = dataflow_crud.list_records(
        "MandatoryTrainingRequirement",
        {"company_id": company_id},
        cache_ttl=0,
    )
    requirements = [r for r in all_reqs if r.get("is_active")]
    employees = dataflow_crud.list_records(
        "Employee",
        {"company_id": company_id, "is_active": True},
        cache_ttl=0,
    )
    all_certs = dataflow_crud.list_records(
        "Certification",
        {"company_id": company_id},
        cache_ttl=0,
    )
    certs = [c for c in all_certs if not c.get("is_archived")]

    def _norm(s: str | None) -> str:
        return " ".join((s or "").split()).casefold()

    coverage = []
    total_pairs = 0
    compliant_pairs = 0
    for req in requirements:
        target = _norm(req.get("required_certification_name"))
        applicable_emps = [
            e
            for e in employees
            if _employee_matches_rule(e, req.get("applicable_to", "all"))
        ]
        compliant_emps = []
        non_compliant = []
        for emp in applicable_emps:
            held = [
                c
                for c in certs
                if c.get("employee_id") == emp.get("id")
                and _norm(c.get("certification_name")) == target
                and (
                    not (c.get("expires_at") or "")
                    or (c.get("expires_at") or "") >= today_iso
                )
            ]
            if held:
                compliant_emps.append(emp.get("id"))
            else:
                non_compliant.append(emp.get("id"))
        coverage.append(
            {
                "requirement_id": req.get("id"),
                "requirement_name": req.get("requirement_name"),
                "applicable_to": req.get("applicable_to"),
                "applicable_count": len(applicable_emps),
                "compliant_count": len(compliant_emps),
                "non_compliant_employee_ids": non_compliant,
            }
        )
        total_pairs += len(applicable_emps)
        compliant_pairs += len(compliant_emps)

    rate = compliant_pairs / total_pairs if total_pairs > 0 else 1.0
    return {
        "coverage": coverage,
        "totals": {
            "compliant_pairs": compliant_pairs,
            "total_pairs": total_pairs,
            "rate": round(rate, 2),
        },
    }
