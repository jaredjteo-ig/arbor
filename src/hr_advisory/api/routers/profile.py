"""Company profile endpoints.

Handles company profile CRUD operations, workforce composition
updates, and profile completeness scoring.
Uses DataFlow workflow nodes for all data operations.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.tenant_isolation import validate_company_access

logger = logging.getLogger(__name__)

router = APIRouter()


def _execute_node(node_type: str, node_id: str, params: dict) -> dict:
    """Run a single DataFlow workflow node and return the result."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401 — ensure models are registered

    wf = WorkflowBuilder()
    wf.add_node(node_type, node_id, params)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results[node_id]


def _extract_records(result) -> list[dict]:
    """Extract the record list from a DataFlow ListNode result."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


def _compute_completeness(company: dict) -> float:
    """Compute profile completeness score based on filled fields."""
    fields_to_check = [
        "name",
        "uen",
        "sector",
        "headcount_local",
        "headcount_pr",
        "headcount_ep",
        "headcount_sp",
        "headcount_wp",
    ]
    filled = 0
    for field in fields_to_check:
        value = company.get(field)
        if value is not None and value != "" and value != 0:
            filled += 1
    return round(filled / len(fields_to_check), 2)


def _company_to_response(company: dict) -> dict:
    """Convert a DataFlow company record to the API response format."""
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
        "uen": company.get("uen"),
        "sector": company.get("sector"),
        "headcount_local": company.get("headcount_local", 0),
        "headcount_pr": company.get("headcount_pr", 0),
        "headcount_ep": company.get("headcount_ep", 0),
        "headcount_sp": company.get("headcount_sp", 0),
        "headcount_wp": company.get("headcount_wp", 0),
        "total_headcount": total,
        "profile_completeness_score": company.get(
            "profile_completeness_score",
            _compute_completeness(company),
        ),
        "is_active": company.get("is_active", True),
    }


@router.get("/{company_id}")
async def get_company_profile(
    company_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the full company profile including workforce composition."""
    validate_company_access(current_user, requested_company_id=company_id)
    try:
        result = _execute_node("CompanyReadNode", "read", {"id": company_id})
    except Exception as exc:
        logger.error("Failed to read company id=%s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve company profile. Please try again later.",
        ) from exc

    if not result or result.get("error") or result.get("failed"):
        raise HTTPException(status_code=404, detail=f"Company with id={company_id} not found")

    return _company_to_response(result)


@router.post("/")
async def create_company_profile(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a new company profile."""
    body = await request.json()

    name = body.get("name", "")
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Company name is required")

    create_params = {
        "name": name.strip(),
        "uen": body.get("uen"),
        "sector": body.get("sector"),
        "sub_sector": body.get("sub_sector"),
        "headcount_local": body.get("headcount_local", 0),
        "headcount_pr": body.get("headcount_pr", 0),
        "headcount_ep": body.get("headcount_ep", 0),
        "headcount_sp": body.get("headcount_sp", 0),
        "headcount_wp": body.get("headcount_wp", 0),
        "is_active": True,
    }

    # Compute completeness before save
    create_params["profile_completeness_score"] = _compute_completeness(create_params)

    try:
        result = _execute_node("CompanyCreateNode", "create", create_params)
    except Exception as exc:
        logger.error("Failed to create company: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to create company profile. Please try again later.",
        ) from exc

    # DataFlow CreateNode doesn't return the auto-generated id.
    # Fetch the created record by name+UEN to get the id.
    company_id = result.get("id")
    if company_id is None:
        try:
            lookup = _execute_node(
                "CompanyListNode",
                "find_created",
                {"filter": {"name": name.strip()}, "limit": 1, "enable_cache": False},
            )
            records = _extract_records(lookup)
            if records:
                company_id = records[-1].get("id")
        except Exception:
            company_id = None

    # Link the newly created company to the current user if not already linked
    user_id = current_user.get("sub")
    if company_id is not None and user_id is not None:
        try:
            _execute_node(
                "UserUpdateNode",
                "link_company",
                {"filter": {"id": int(user_id)}, "fields": {"company_id": company_id}},
            )
            logger.info("Linked company_id=%s to user_id=%s", company_id, user_id)
        except Exception as exc:
            logger.warning(
                "Created company_id=%s but failed to link to user_id=%s: %s",
                company_id, user_id, exc,
            )

    return {
        "id": company_id,
        "name": result.get("name", ""),
        "uen": result.get("uen"),
        "sector": result.get("sector"),
        "created": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.put("/{company_id}")
async def update_company_profile(
    company_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update an existing company profile."""
    validate_company_access(current_user, requested_company_id=company_id)
    body = await request.json()

    if not body:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Verify company exists first
    try:
        existing = _execute_node("CompanyReadNode", "read_check", {"id": company_id})
    except Exception as exc:
        logger.error("Failed to read company id=%s for update: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to verify company. Please try again later.",
        ) from exc

    if not existing or existing.get("error") or existing.get("failed"):
        raise HTTPException(status_code=404, detail=f"Company with id={company_id} not found")

    # Only allow updating known fields
    allowed_fields = {
        "name",
        "uen",
        "sector",
        "sub_sector",
        "headcount_local",
        "headcount_pr",
        "headcount_ep",
        "headcount_sp",
        "headcount_wp",
        "salary_ranges",
        "is_active",
    }
    updates = {k: v for k, v in body.items() if k in allowed_fields}

    if not updates:
        raise HTTPException(
            status_code=400,
            detail=f"No valid fields to update. Allowed: {sorted(allowed_fields)}",
        )

    # Recompute completeness with merged data
    merged = {**existing, **updates}
    updates["profile_completeness_score"] = _compute_completeness(merged)

    try:
        _execute_node(
            "CompanyUpdateNode",
            "update",
            {"filter": {"id": company_id}, "fields": updates},
        )
    except Exception as exc:
        logger.error("Failed to update company id=%s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to update company profile. Please try again later.",
        ) from exc

    return {
        "id": company_id,
        "updated_fields": list(updates.keys()),
        "updated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{company_id}/workforce")
async def get_workforce_composition(
    company_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get detailed workforce composition breakdown."""
    validate_company_access(current_user, requested_company_id=company_id)
    try:
        result = _execute_node("CompanyReadNode", "read", {"id": company_id})
    except Exception as exc:
        logger.error("Failed to read company id=%s for workforce: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve workforce composition. Please try again later.",
        ) from exc

    if not result or result.get("error") or result.get("failed"):
        raise HTTPException(status_code=404, detail=f"Company with id={company_id} not found")

    local = result.get("headcount_local", 0)
    pr = result.get("headcount_pr", 0)
    ep = result.get("headcount_ep", 0)
    sp = result.get("headcount_sp", 0)
    wp = result.get("headcount_wp", 0)
    total = local + pr + ep + sp + wp
    local_total = local + pr
    local_ratio = round(local_total / total, 2) if total > 0 else 0.0

    return {
        "company_id": company_id,
        "workforce": {
            "local": local,
            "pr": pr,
            "ep": ep,
            "sp": sp,
            "wp": wp,
        },
        "total": total,
        "local_ratio": local_ratio,
    }
