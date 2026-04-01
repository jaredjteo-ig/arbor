"""Unified company default data seeding.

Called after company creation to ensure all HRIS modules are immediately
usable.  Each sub-seed is idempotent — safe to call multiple times.
"""

import json
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
        ("cost_centres", _seed_demo_cost_centres),
        ("pay_items", _seed_demo_pay_items),
        ("projects", _seed_demo_projects),
        ("project_roles", _seed_demo_project_roles),
        ("inventory", _seed_demo_inventory),
        ("appraisal_template", _seed_demo_appraisal_template),
        ("job_listings", _seed_demo_job_listings),
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
        "category": "leave_absence",
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
        "category": "employment_terms",
        "title": "Flexible Work Arrangements",
        "content": (
            "Per Tripartite Guidelines on FWA Requests (TG-FWAR), effective "
            "1 Dec 2024, all employees may submit formal FWA requests. "
            "Employers must consider and respond within 2 months."
        ),
    },
    {
        "policy_type": "handbook",
        "category": "general_hr",
        "title": "Employee Handbook",
        "content": (
            "Key Employment Terms (KETs) must be provided within 14 days of "
            "employment start per EA s95. Notice period per contract or EA "
            "default. Salary payment within 7 days of end of salary period."
        ),
    },
    {
        "policy_type": "wsh",
        "category": "workplace_safety",
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
                "category": policy.get("category", ""),
                "title": policy["title"],
                "content": policy["content"],
                "effective_date": today,
                "is_active": True,
                "version_number": 1,
                "file_type": "text",
                "status": "active",
                "extraction_status": "",
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


# ---------------------------------------------------------------------------
# Cost centre seeding
# ---------------------------------------------------------------------------

DEFAULT_COST_CENTRES = [
    {"name": "Engineering", "code": "ENG"},
    {"name": "Operations", "code": "OPS"},
    {"name": "Sales & Marketing", "code": "SMK"},
]


def _seed_demo_cost_centres(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "CostCentreListNode",
            "check_cost_centres",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "cost centres already exist"}

    count = 0
    for cc in DEFAULT_COST_CENTRES:
        _execute_node(
            "CostCentreCreateNode",
            "create_cost_centre",
            {"company_id": company_id, "is_active": True, **cc},
        )
        count += 1
    return {"created": count}


# ---------------------------------------------------------------------------
# Pay item seeding
# ---------------------------------------------------------------------------

DEFAULT_PAY_ITEMS = [
    {
        "name": "Monthly Salary",
        "category": "salary",
        "cpf_type": "ow",
        "is_recurring": True,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
    {
        "name": "Overtime",
        "category": "overtime",
        "cpf_type": "ow",
        "is_recurring": False,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
    {
        "name": "Transport Allowance",
        "category": "allowance",
        "cpf_type": "ow",
        "is_recurring": True,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
    {
        "name": "Meal Allowance",
        "category": "allowance",
        "cpf_type": "ow",
        "is_recurring": True,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
    {
        "name": "13th Month Bonus",
        "category": "bonus",
        "cpf_type": "aw",
        "is_recurring": False,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
    {
        "name": "Performance Bonus",
        "category": "bonus",
        "cpf_type": "aw",
        "is_recurring": False,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
    {
        "name": "Commission",
        "category": "commission",
        "cpf_type": "aw",
        "is_recurring": False,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
    {
        "name": "AWS",
        "category": "bonus",
        "cpf_type": "aw",
        "is_recurring": False,
        "is_taxable": True,
        "is_cpf_applicable": True,
    },
]


def _seed_demo_pay_items(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "PayItemListNode",
            "check_pay_items",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "pay items already exist"}

    count = 0
    for item in DEFAULT_PAY_ITEMS:
        _execute_node(
            "PayItemCreateNode",
            "create_pay_item",
            {"company_id": company_id, **item},
        )
        count += 1
    return {"created": count}


# ---------------------------------------------------------------------------
# Project seeding
# ---------------------------------------------------------------------------

DEFAULT_PROJECTS = [
    {
        "name": "Website Redesign",
        "description": "Complete redesign of the company website with modern UI/UX",
        "budget_amount": 50000.0,
        "start_date": "2026-01-15",
        "end_date": "2026-06-30",
    },
    {
        "name": "Mobile App Development",
        "description": "Build a cross-platform mobile application for customers",
        "budget_amount": 80000.0,
        "start_date": "2026-02-01",
        "end_date": "",
    },
]


def _seed_demo_projects(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "ProjectListNode",
            "check_projects",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "projects already exist"}

    count = 0
    for proj in DEFAULT_PROJECTS:
        _execute_node(
            "ProjectCreateNode",
            "create_project",
            {"company_id": company_id, **proj},
        )
        count += 1
    return {"created": count}


# ---------------------------------------------------------------------------
# Project role seeding
# ---------------------------------------------------------------------------

DEFAULT_PROJECT_ROLES = [
    {"name": "Developer", "hourly_rate": 75.0},
    {"name": "Designer", "hourly_rate": 65.0},
    {"name": "Project Manager", "hourly_rate": 85.0},
]


def _seed_demo_project_roles(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "ProjectRoleListNode",
            "check_project_roles",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "project roles already exist"}

    count = 0
    for role in DEFAULT_PROJECT_ROLES:
        _execute_node(
            "ProjectRoleCreateNode",
            "create_project_role",
            {"company_id": company_id, **role},
        )
        count += 1
    return {"created": count}


# ---------------------------------------------------------------------------
# Inventory seeding (location + categories + items)
# ---------------------------------------------------------------------------


def _seed_demo_inventory(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "InventoryLocationListNode",
            "check_inv_locations",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "inventory already exists"}

    # 1. Create location
    loc_result = _execute_node(
        "InventoryLocationCreateNode",
        "create_location",
        {"company_id": company_id, "name": "Main Office", "organization_scope": "all"},
    )
    location_id = loc_result["id"]

    # 2. Create categories
    it_cat_result = _execute_node(
        "InventoryCategoryCreateNode",
        "create_it_category",
        {
            "company_id": company_id,
            "location_id": location_id,
            "name": "IT Equipment",
            "tracking_mode": "quantity",
            "require_acknowledgment": True,
        },
    )
    it_cat_id = it_cat_result["id"]

    office_cat_result = _execute_node(
        "InventoryCategoryCreateNode",
        "create_office_category",
        {
            "company_id": company_id,
            "location_id": location_id,
            "name": "Office Supplies",
            "tracking_mode": "quantity",
            "require_acknowledgment": True,
        },
    )
    office_cat_id = office_cat_result["id"]

    # 3. Create items
    items = [
        {
            "category_id": it_cat_id,
            "name": 'MacBook Pro 14"',
            "quantity": 1,
            "serial_number": "ABC123",
            "purchase_price": 3299.0,
            "condition": "new",
            "status": "available",
        },
        {
            "category_id": it_cat_id,
            "name": 'MacBook Pro 14"',
            "quantity": 1,
            "serial_number": "ABC124",
            "purchase_price": 3299.0,
            "condition": "new",
            "status": "available",
        },
        {
            "category_id": it_cat_id,
            "name": 'Dell Monitor 27"',
            "quantity": 1,
            "serial_number": "MON001",
            "purchase_price": 599.0,
            "condition": "new",
            "status": "available",
        },
        {
            "category_id": office_cat_id,
            "name": "Wireless Mouse",
            "quantity": 10,
            "purchase_price": 45.0,
            "condition": "new",
            "status": "available",
        },
        {
            "category_id": office_cat_id,
            "name": "USB-C Hub",
            "quantity": 5,
            "purchase_price": 89.0,
            "condition": "new",
            "status": "available",
        },
    ]

    count = 0
    for item in items:
        _execute_node(
            "InventoryItemCreateNode",
            "create_inv_item",
            {"company_id": company_id, "location_id": location_id, **item},
        )
        count += 1

    return {"created": {"locations": 1, "categories": 2, "items": count}}


# ---------------------------------------------------------------------------
# Appraisal template seeding
# ---------------------------------------------------------------------------

DEFAULT_APPRAISAL_SECTIONS = [
    {
        "title": "Goal Achievement",
        "weight": 40,
        "questions": [
            {
                "text": "How well did the employee meet their annual goals?",
                "type": "rating",
                "filled_by": "reviewer",
            },
            {
                "text": "Describe your key achievements this year",
                "type": "text",
                "filled_by": "employee",
            },
        ],
    },
    {
        "title": "Core Competencies",
        "weight": 30,
        "questions": [
            {
                "text": "Communication and teamwork",
                "type": "rating",
                "filled_by": "reviewer",
            },
            {
                "text": "Problem solving and initiative",
                "type": "rating",
                "filled_by": "reviewer",
            },
        ],
    },
    {
        "title": "Growth & Development",
        "weight": 30,
        "questions": [
            {
                "text": "What skills would you like to develop?",
                "type": "text",
                "filled_by": "employee",
            },
            {
                "text": "Recommended training or development areas",
                "type": "text",
                "filled_by": "reviewer",
            },
        ],
    },
]


def _seed_demo_appraisal_template(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "AppraisalTemplateListNode",
            "check_appraisal_templates",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "appraisal templates already exist"}

    _execute_node(
        "AppraisalTemplateCreateNode",
        "create_appraisal_template",
        {
            "company_id": company_id,
            "name": "Annual Performance Review",
            "sections": json.dumps(DEFAULT_APPRAISAL_SECTIONS),
            "enable_weightage": True,
            "require_employee_signoff": True,
        },
    )
    return {"created": 1}


# ---------------------------------------------------------------------------
# Job listing seeding
# ---------------------------------------------------------------------------

DEFAULT_JOB_LISTINGS = [
    {
        "position_title": "Senior Software Engineer",
        "employment_type": "full_time",
        "department": "Tech",
        "description": (
            "We are looking for an experienced software engineer to join our "
            "engineering team. You will design, build, and maintain scalable "
            "backend services and APIs."
        ),
        "requirements": (
            "5+ years of software development experience. "
            "Proficiency in Python or TypeScript. "
            "Experience with cloud services (AWS/GCP). "
            "Strong problem-solving skills."
        ),
        "salary_range_min": 7000.0,
        "salary_range_max": 10000.0,
        "is_published": True,
    },
    {
        "position_title": "HR Executive",
        "employment_type": "full_time",
        "department": "HR",
        "description": (
            "Join our HR team to manage the full employee lifecycle — from "
            "recruitment and onboarding to payroll administration and employee "
            "relations."
        ),
        "requirements": (
            "2+ years of HR generalist experience. "
            "Familiarity with Singapore Employment Act and MOM regulations. "
            "Strong communication and organisational skills."
        ),
        "salary_range_min": 4000.0,
        "salary_range_max": 5500.0,
        "is_published": True,
    },
]


def _seed_demo_job_listings(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "JobListingListNode",
            "check_job_listings",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "job listings already exist"}

    count = 0
    for listing in DEFAULT_JOB_LISTINGS:
        _execute_node(
            "JobListingCreateNode",
            "create_job_listing",
            {"company_id": company_id, **listing},
        )
        count += 1
    return {"created": count}
