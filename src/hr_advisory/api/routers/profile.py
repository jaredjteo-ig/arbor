"""Company profile endpoints.

Handles company profile CRUD operations, workforce composition
updates, and profile completeness scoring.
Uses DataFlow workflow nodes for all data operations.
"""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import validate_company_access

logger = logging.getLogger(__name__)


def _generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a company name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")

router = APIRouter()


# ---------------------------------------------------------------------------
# Default policy data (Singapore regulatory requirements)
# ---------------------------------------------------------------------------

DEFAULT_POLICIES = [
    {
        "policy_type": "leave",
        "title": "Leave Policy",
        "content": (
            "Annual Leave: Employees are entitled to a minimum of 7 days paid annual leave "
            "in their first year of service, increasing by 1 day per year up to 14 days "
            "(Employment Act s88). Unused annual leave may be carried forward as agreed with "
            "the employer.\n\n"
            "Sick Leave: Employees are entitled to 14 days paid outpatient sick leave and "
            "60 days paid hospitalisation leave per year (Employment Act s89). A medical "
            "certificate from a company-approved doctor is required.\n\n"
            "Maternity Leave: Female employees are entitled to 16 weeks of Government-Paid "
            "Maternity Leave if they have served for at least 3 months (CDCSA).\n\n"
            "Paternity Leave: Male employees are entitled to 4 weeks of Government-Paid "
            "Paternity Leave (effective January 2025)."
        ),
    },
    {
        "policy_type": "fwa",
        "title": "Flexible Work Arrangements",
        "content": (
            "Under the Tripartite Guidelines on Flexible Work Arrangement Requests (TG-FWAR), "
            "effective 1 December 2024, all employees may request FWA from their employer. "
            "Employers must consider requests fairly and respond within 2 months.\n\n"
            "Types of FWA: Flexi-place (work from home), Flexi-time (staggered hours), "
            "Flexi-load (part-time or job sharing)."
        ),
    },
    {
        "policy_type": "handbook",
        "title": "Employee Handbook",
        "content": (
            "This handbook outlines employment terms as required under the Employment Act. "
            "Key Employment Terms (KETs) are provided to every employee within 14 days of "
            "employment (EA s95A).\n\n"
            "Notice Period: As per your employment contract. Statutory minimum: 1 day "
            "(under 26 weeks), 1 week (26 weeks to 2 years), 2 weeks (2-5 years), "
            "4 weeks (5+ years) — Employment Act s10.\n\n"
            "Salary Payment: Salary must be paid within 7 days after the salary period. "
            "Itemised payslips are required (EA s88A)."
        ),
    },
    {
        "policy_type": "safety",
        "title": "Workplace Safety and Health",
        "content": (
            "Under the Workplace Safety and Health Act (WSHA), employers must take "
            "reasonably practicable measures to ensure the safety and health of employees.\n\n"
            "Key obligations: Conduct risk assessments, provide safety training, report "
            "workplace accidents within prescribed timeframes, maintain safety records.\n\n"
            "For workplaces with 50+ employees, a designated WSH Officer is required."
        ),
    },
]


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
    import math

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
        # Guard against NaN/Inf in numeric fields
        if isinstance(value, float) and not math.isfinite(value):
            continue
        if value is not None and value != "" and value != 0:
            filled += 1
    result = round(filled / len(fields_to_check), 2)
    if not math.isfinite(result):
        return 0.0
    return result


def _seed_default_policies(company_id: int) -> None:
    """Create default CompanyPolicy records for a newly created company.

    Only seeds if the company has no existing policies, making this safe
    to call multiple times (idempotent).
    """
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    # Check if policies already exist for this company
    wf = WorkflowBuilder()
    wf.add_node(
        "CompanyPolicyListNode",
        "check",
        {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    existing = _extract_records(results["check"])
    if existing:
        logger.info("Policies already exist for company_id=%s, skipping seed.", company_id)
        return

    # Seed default policies
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for policy in DEFAULT_POLICIES:
        wf = WorkflowBuilder()
        wf.add_node(
            "CompanyPolicyCreateNode",
            "create_policy",
            {
                "company_id": company_id,
                "policy_type": policy["policy_type"],
                "title": policy["title"],
                "content": policy["content"],
                "effective_date": today,
                "is_active": True,
            },
        )
        runtime = LocalRuntime()
        results, _ = runtime.execute(wf.build())
    logger.info("Seeded %d default policies for company_id=%s", len(DEFAULT_POLICIES), company_id)


def _company_to_response(company: dict) -> dict:
    """Convert a DataFlow company record to the API response format.

    Total headcount and pass-type breakdown are computed from actual active
    employee records. Manual headcount fields are kept as fallbacks for the
    workforce composition section (used when employees lack pass_type).
    """
    from hr_advisory.services import dataflow_crud

    company_id = company.get("id")
    # Compute live headcount from active employees
    employees = []
    if company_id:
        try:
            employees = dataflow_crud.list_records(
                "Employee",
                {"company_id": company_id, "is_active": True},
                cache_ttl=0,
            )
        except Exception:
            employees = []

    live_total = len(employees)

    # Count by pass_type from actual employee records
    pass_counts: dict[str, int] = {}
    for emp in employees:
        pt = (emp.get("pass_type") or "").lower()
        if pt:
            pass_counts[pt] = pass_counts.get(pt, 0) + 1

    # Use live counts when available, fall back to manual profile fields
    headcount_local = pass_counts.get("citizen", 0) + pass_counts.get("local", 0)
    headcount_pr = pass_counts.get("pr", 0) + pass_counts.get("permanent_resident", 0)
    headcount_ep = pass_counts.get("ep", 0) + pass_counts.get("employment_pass", 0)
    headcount_sp = pass_counts.get("sp", 0) + pass_counts.get("s_pass", 0)
    headcount_wp = pass_counts.get("wp", 0) + pass_counts.get("work_permit", 0)

    # If no employees have pass_type set, fall back to manual fields
    has_pass_data = sum(pass_counts.values()) > 0
    if not has_pass_data:
        headcount_local = company.get("headcount_local", 0)
        headcount_pr = company.get("headcount_pr", 0)
        headcount_ep = company.get("headcount_ep", 0)
        headcount_sp = company.get("headcount_sp", 0)
        headcount_wp = company.get("headcount_wp", 0)

    return {
        "id": company["id"],
        "name": company.get("name", ""),
        "uen": company.get("uen"),
        "sector": company.get("sector"),
        "headcount_local": headcount_local,
        "headcount_pr": headcount_pr,
        "headcount_ep": headcount_ep,
        "headcount_sp": headcount_sp,
        "headcount_wp": headcount_wp,
        "total_headcount": live_total if live_total > 0 else (
            headcount_local + headcount_pr + headcount_ep + headcount_sp + headcount_wp
        ),
        "has_foreign_workers": (headcount_ep + headcount_sp + headcount_wp) > 0,
        "profile_completeness_score": company.get(
            "profile_completeness_score",
            _compute_completeness(company),
        ),
        "is_active": company.get("is_active", True),
    }


@router.get(
    "/{company_id}",
    dependencies=[Depends(require_role("owner", "hr_manager", "platform_admin"))],
)
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


@router.post("")
async def create_company_profile(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a new company profile."""
    body = await request.json()

    name = body.get("name", "")
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Company name is required")

    def _safe_int(val, default=0):
        """Convert to int safely, guarding against None/NaN/non-numeric."""
        if val is None:
            return default
        try:
            import math

            v = float(val)
            return int(v) if math.isfinite(v) else default
        except (TypeError, ValueError):
            return default

    create_params = {
        "name": name.strip(),
        "slug": _generate_slug(name),
        "uen": body.get("uen"),
        "sector": body.get("sector"),
        "sub_sector": body.get("sub_sector"),
        "headcount_local": _safe_int(body.get("headcount_local")),
        "headcount_pr": _safe_int(body.get("headcount_pr")),
        "headcount_ep": _safe_int(body.get("headcount_ep")),
        "headcount_sp": _safe_int(body.get("headcount_sp")),
        "headcount_wp": _safe_int(body.get("headcount_wp")),
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
                company_id,
                user_id,
                exc,
            )

    # Seed all default data for the newly created company
    if company_id is not None:
        try:
            from hr_advisory.services.company_seeding import seed_company_defaults

            seed_company_defaults(company_id)
        except Exception as exc:
            logger.warning(
                "Created company_id=%s but seeding failed: %s",
                company_id,
                exc,
            )

    return {
        "id": company_id,
        "name": result.get("name", ""),
        "uen": result.get("uen"),
        "sector": result.get("sector"),
        "created": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.put(
    "/{company_id}",
    dependencies=[Depends(require_role("owner", "hr_manager", "platform_admin"))],
)
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
        "slug",
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

    # Auto-regenerate slug when name changes (unless slug was explicitly set)
    if "name" in updates and "slug" not in updates:
        updates["slug"] = _generate_slug(updates["name"])

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


@router.get(
    "/{company_id}/workforce",
    dependencies=[Depends(require_role("owner", "hr_manager", "platform_admin"))],
)
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
