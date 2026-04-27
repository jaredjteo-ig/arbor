"""Company endpoints for the single-tenant deployment.

Wraps the Company DataFlow operations. Each deployment is bound to a
single Company; these endpoints support listing/getting/updating that
company and creating it during onboarding.
"""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import validate_company_access


def _generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a company name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")

logger = logging.getLogger(__name__)

router = APIRouter()


def _execute_node(node_type: str, node_id: str, params: dict) -> dict:
    """Run a single DataFlow workflow node and return the result."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401 -- ensure models are registered

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
        "uen": company.get("uen") or "",
        "sector": company.get("sector") or "",
        "employee_count": total,
        "compliance_score": company.get("compliance_score"),
        "risk_tier": company.get("risk_tier"),
        "last_activity": company.get("last_activity"),
        "created_at": company.get("created_at", ""),
    }


@router.get("")
async def list_companies(
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """List companies visible to the current user.

    Platform admins see all active companies. Regular users see only their own.

    Requires owner, hr_manager, or platform_admin role.
    """
    role = current_user.get("role", "")
    user_company_id = current_user.get("company_id")

    try:
        if role == "platform_admin":
            result = _execute_node(
                "CompanyListNode",
                "list_companies",
                {"filter": {"is_active": True}, "limit": 200},
            )
        elif user_company_id:
            result = _execute_node(
                "CompanyListNode",
                "list_companies",
                {"filter": {"id": user_company_id, "is_active": True}, "limit": 10},
            )
        else:
            return {"companies": [], "count": 0}
    except Exception as exc:
        logger.error("Failed to list companies: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve company list. Please try again later.",
        ) from exc

    records = _extract_records(result)
    companies = [_company_to_response(r) for r in records]

    return {"companies": companies, "count": len(companies)}


@router.post("")
async def create_company(
    request: Request,
    current_user: dict = Depends(require_role("owner", "platform_admin")),
) -> dict:
    """Create a new company.

    Requires owner or platform_admin role.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"create_company:{user_id}", max_requests=30, window_seconds=60, action_name="create company")

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
        "slug": _generate_slug(name),
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
        result = _execute_node("CompanyCreateNode", "create_company", create_params)
    except Exception as exc:
        logger.error("Failed to create company: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to create company. Please try again later.",
        ) from exc

    # Attempt to retrieve the ID of the created record
    company_id = result.get("id")
    if company_id is None:
        try:
            lookup = _execute_node(
                "CompanyListNode",
                "find_created_company",
                {"filter": {"name": name.strip()}, "limit": 1, "enable_cache": False},
            )
            records = _extract_records(lookup)
            if records:
                company_id = records[-1].get("id")
        except Exception:
            company_id = None

    # Associate the creating user with this company
    if company_id is not None:
        user_id = current_user.get("sub") or current_user.get("id")
        if user_id:
            try:
                _execute_node(
                    "UserUpdateNode",
                    "assign_company",
                    {"filter": {"id": int(user_id)}, "fields": {"company_id": company_id}},
                )
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


@router.get("/{company_id}")
async def get_company(
    company_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Get a specific company by ID.

    Requires owner, hr_manager, or platform_admin role.
    """
    validate_company_access(current_user, requested_company_id=company_id)

    try:
        result = _execute_node("CompanyReadNode", "read_company", {"id": company_id})
    except Exception as exc:
        logger.error("Failed to read company id=%s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve company. Please try again later.",
        ) from exc

    if not result or result.get("error") or result.get("failed"):
        raise HTTPException(status_code=404, detail=f"Company with id={company_id} not found")

    return _company_to_response(result)


@router.put("/{company_id}")
async def update_company(
    company_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "platform_admin")),
) -> dict:
    """Update an existing company.

    Requires owner or platform_admin role.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"update_company:{user_id}", max_requests=30, window_seconds=60, action_name="update company")

    validate_company_access(current_user, requested_company_id=company_id)
    body = await request.json()

    if not body:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Verify company exists
    try:
        existing = _execute_node("CompanyReadNode", "read_company_check", {"id": company_id})
    except Exception as exc:
        logger.error("Failed to read company id=%s for update: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to verify company. Please try again later.",
        ) from exc

    if not existing or existing.get("error") or existing.get("failed"):
        raise HTTPException(status_code=404, detail=f"Company with id={company_id} not found")

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
        _execute_node(
            "CompanyUpdateNode",
            "update_company",
            {"filter": {"id": company_id}, "fields": updates},
        )
    except Exception as exc:
        logger.error("Failed to update company id=%s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to update company. Please try again later.",
        ) from exc

    return {
        "id": company_id,
        "updated_fields": list(updates.keys()),
        "updated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
