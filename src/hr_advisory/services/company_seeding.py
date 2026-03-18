"""Unified company default data seeding.

Called after company creation to ensure all HRIS modules are immediately
usable.  Each sub-seed is idempotent — safe to call multiple times.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DataFlow helpers (same pattern used across the codebase)
# ---------------------------------------------------------------------------


def _execute_node(node_type: str, node_id: str, params: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder
    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, node_id, params)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results[node_id]


def _extract_records(result) -> list[dict]:
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def seed_company_defaults(company_id: int) -> dict:
    """Seed all default data for a newly created company.

    Returns a summary of what was seeded.  Individual failures are logged
    but do NOT block company creation.
    """
    summary: dict = {}

    for name, fn in [
        ("policies", _seed_policies),
        ("leave_types", _seed_leave_types),
        ("claim_categories", _seed_claim_categories),
        ("attendance_settings", _seed_attendance_settings),
    ]:
        try:
            summary[name] = fn(company_id)
        except Exception as exc:
            logger.warning("Seeding %s failed for company_id=%s: %s", name, company_id, exc)
            summary[name] = {"error": str(exc)}

    logger.info("Company seeding complete for company_id=%s: %s", company_id, summary)
    return summary


# ---------------------------------------------------------------------------
# Policy seeding (moved from profile.py)
# ---------------------------------------------------------------------------

DEFAULT_POLICIES = [
    {
        "policy_type": "leave",
        "title": "Leave Policy",
        "content": (
            "Annual leave entitlement per Employment Act s88: minimum 7 days "
            "for first year, increasing by 1 day per year up to 14 days. "
            "Sick leave: 14 days outpatient, 60 days hospitalisation "
            "(inclusive). Maternity: 16 weeks (CDCSA). Paternity: 4 weeks "
            "(CDCSA, effective 1 Jan 2025). Childcare: 6 days."
        ),
    },
    {
        "policy_type": "fwa",
        "title": "Flexible Work Arrangements",
        "content": (
            "Per Tripartite Guidelines on FWA Requests (TG-FWAR), effective "
            "1 Dec 2024, all employees may submit formal FWA requests. "
            "Employers must consider and respond within 2 months."
        ),
    },
    {
        "policy_type": "handbook",
        "title": "Employee Handbook",
        "content": (
            "Key Employment Terms (KETs) must be provided within 14 days of "
            "employment start per EA s95. Notice period per contract or EA "
            "default. Salary payment within 7 days of end of salary period."
        ),
    },
    {
        "policy_type": "wsh",
        "title": "Workplace Safety and Health",
        "content": (
            "Per Workplace Safety and Health Act (WSHA), employers must take "
            "reasonably practicable measures to ensure safety. Workplaces with "
            "50+ employees must appoint a safety officer."
        ),
    },
]


def _seed_policies(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "CompanyPolicyListNode",
            "check_policies",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "policies already exist"}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0
    for policy in DEFAULT_POLICIES:
        _execute_node(
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
        count += 1
    return {"created": count}


# ---------------------------------------------------------------------------
# Leave type seeding (delegates to existing function in leave.py)
# ---------------------------------------------------------------------------


def _seed_leave_types(company_id: int) -> dict:
    from hr_advisory.api.routers.leave import _seed_statutory_leave_types

    created = _seed_statutory_leave_types(company_id)
    return {"created": len(created)}


# ---------------------------------------------------------------------------
# Claim category seeding
# ---------------------------------------------------------------------------

DEFAULT_CLAIM_CATEGORIES = [
    {"name": "Transport", "monthly_limit": 200.0, "per_claim_limit": 0, "requires_receipt": False},
    {"name": "Meals", "monthly_limit": 150.0, "per_claim_limit": 0, "requires_receipt": False},
    {"name": "Medical", "monthly_limit": 500.0, "per_claim_limit": 0, "requires_receipt": True},
    {
        "name": "Office Supplies",
        "monthly_limit": 100.0,
        "per_claim_limit": 0,
        "requires_receipt": True,
    },
    {
        "name": "Entertainment",
        "monthly_limit": 200.0,
        "per_claim_limit": 0,
        "requires_receipt": True,
    },
    {
        "name": "Training & Development",
        "monthly_limit": 500.0,
        "per_claim_limit": 0,
        "requires_receipt": True,
    },
]


def _seed_claim_categories(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "ClaimCategoryListNode",
            "check_categories",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "claim categories already exist"}

    count = 0
    for cat in DEFAULT_CLAIM_CATEGORIES:
        _execute_node(
            "ClaimCategoryCreateNode",
            "create_category",
            {"company_id": company_id, "is_active": True, **cat},
        )
        count += 1
    return {"created": count}


# ---------------------------------------------------------------------------
# Attendance settings seeding
# ---------------------------------------------------------------------------


def _seed_attendance_settings(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "AttendanceSettingsListNode",
            "check_settings",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "attendance settings already exist"}

    _execute_node(
        "AttendanceSettingsCreateNode",
        "create_settings",
        {
            "company_id": company_id,
            "work_start_time": "09:00",
            "work_end_time": "18:00",
            "grace_period_minutes": 15,
            "overtime_threshold_minutes": 30,
            "require_gps": False,
            "require_photo": False,
        },
    )
    return {"created": 1}
