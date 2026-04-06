"""Client management endpoints for the consultant view.

Wraps the company profile DataFlow operations to provide a
multi-tenant client list. Consultants can manage multiple client
companies through these endpoints.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import validate_company_access
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

router = APIRouter()


def _company_to_client(company: dict) -> dict:
    """Convert a DataFlow company record to the client API response format."""
    total = (
        company.get("headcount_local", 0)
        + company.get("headcount_pr", 0)
        + company.get("headcount_ep", 0)
        + company.get("headcount_sp", 0)
        + company.get("headcount_wp", 0)
    )
    return {
        "id": company["id"],
        "name": company.get("name", ""),
        "uen": company.get("uen") or "",
        "sector": company.get("sector") or "",
        "employee_count": total,
        "compliance_score": company.get("compliance_score"),
        "risk_tier": company.get("risk_tier"),
        "last_activity": company.get("last_activity"),
        "created_at": company.get("created_at", ""),
    }


@router.get("/")
async def list_clients(
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin", "consultant")),
) -> dict:
    """List all client companies visible to the current user.

    Platform admins and consultants see all active companies.
    Regular users see only their own company.
    """
    role = current_user.get("role", "")
    user_company_id = current_user.get("company_id")

    try:
        if role in ("platform_admin", "consultant"):
            records = dataflow_crud.list_records("Company", {"is_active": True}, limit=200)
        elif user_company_id:
            records = dataflow_crud.list_records(
                "Company", {"id": user_company_id, "is_active": True}, limit=10
            )
        else:
            return {"clients": [], "total": 0}
    except Exception as exc:
        logger.error("Failed to list clients: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve client list. Please try again later.",
        ) from exc

    clients = [_company_to_client(r) for r in records]

    return {"clients": clients, "total": len(clients)}


@router.post("/")
async def create_client(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Create a new client company."""
    body = await request.json()

    # Accept both "name" and "company_name" for compatibility
    name = body.get("name", "") or body.get("company_name", "")
    if not name or not name.strip():
        raise HTTPException(
            status_code=400, detail="Company name is required (use 'name' or 'company_name' field)"
        )

    uen = (
        body.get("uen", "") or ""
    ).strip()  # Optional — users may not have UEN during initial setup

    employee_count = body.get("employee_count", 0) or body.get("estimated_headcount", 0)
    sector = body.get("sector", "")

    create_params = {
        "name": name.strip(),
        "uen": uen.strip(),
        "sector": sector,
        "headcount_local": employee_count,
        "headcount_pr": 0,
        "headcount_ep": 0,
        "headcount_sp": 0,
        "headcount_wp": 0,
        "is_active": True,
        "profile_completeness_score": 0.0,
    }

    try:
        result = dataflow_crud.create("Company", create_params)
    except Exception as exc:
        logger.error("Failed to create client: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to create client company. Please try again later.",
        ) from exc

    # Attempt to retrieve the ID of the created record
    company_id = result.get("id")
    if company_id is None:
        try:
            records = dataflow_crud.list_records("Company", {"name": name.strip()}, limit=1)
            if records:
                company_id = records[-1].get("id")
        except Exception:
            company_id = None

    # Associate the creating user with this company
    if company_id is not None:
        user_id = current_user.get("sub") or current_user.get("id")
        if user_id:
            try:
                dataflow_crud.update("User", int(user_id), {"company_id": company_id})
                logger.info("Assigned user %s to company %s", user_id, company_id)
            except Exception as exc:
                logger.warning(
                    "Failed to assign user %s to company %s: %s", user_id, company_id, exc
                )

    # Seed all default data for the new company
    seed_summary = {}
    if company_id is not None:
        try:
            from hr_advisory.services.company_seeding import seed_company_defaults

            seed_summary = seed_company_defaults(company_id)
        except Exception as exc:
            logger.warning("Company %s created but seeding failed: %s", company_id, exc)

    return {
        "id": company_id,
        "name": name.strip(),
        "uen": uen.strip(),
        "sector": sector,
        "employee_count": employee_count,
        "compliance_score": None,
        "risk_tier": None,
        "last_activity": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed_summary": seed_summary,
    }


@router.get("/{client_id}")
async def get_client(
    client_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin", "consultant")),
) -> dict:
    """Get a specific client company by ID."""
    validate_company_access(current_user, requested_company_id=client_id)

    try:
        result = dataflow_crud.read("Company", client_id)
    except Exception as exc:
        logger.error("Failed to read client id=%s: %s", client_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve client. Please try again later.",
        ) from exc

    if not result:
        raise HTTPException(status_code=404, detail=f"Client with id={client_id} not found")

    return _company_to_client(result)


@router.put("/{client_id}")
async def update_client(
    client_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Update an existing client company."""
    validate_company_access(current_user, requested_company_id=client_id)
    body = await request.json()

    if not body:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Verify client exists
    try:
        existing = dataflow_crud.read("Company", client_id)
    except Exception as exc:
        logger.error("Failed to read client id=%s for update: %s", client_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to verify client. Please try again later.",
        ) from exc

    if not existing:
        raise HTTPException(status_code=404, detail=f"Client with id={client_id} not found")

    # Map frontend fields to DataFlow fields
    allowed_fields = {"name", "uen", "sector", "employee_count", "is_active"}
    updates: dict = {}
    for key, value in body.items():
        if key in allowed_fields:
            if key == "employee_count":
                updates["headcount_local"] = value
            else:
                updates[key] = value

    if not updates:
        raise HTTPException(
            status_code=400,
            detail=f"No valid fields to update. Allowed: {sorted(allowed_fields)}",
        )

    try:
        dataflow_crud.update("Company", client_id, updates)
    except Exception as exc:
        logger.error("Failed to update client id=%s: %s", client_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to update client. Please try again later.",
        ) from exc

    return {
        "id": client_id,
        "updated_fields": list(updates.keys()),
        "updated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
