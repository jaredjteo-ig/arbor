"""Unified company default data seeding.

Called after company creation to ensure all HRIS modules are immediately
usable.  Each sub-seed is idempotent — safe to call multiple times.
"""

import json
import logging
from datetime import datetime, timezone

from hr_advisory.services import dataflow_crud

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
        ("public_holidays", _seed_public_holidays),
        ("claim_categories", _seed_claim_categories),
        ("attendance_settings", _seed_attendance_settings),
        ("cost_centres", _seed_demo_cost_centres),
        ("pay_items", _seed_demo_pay_items),
        ("projects", _seed_demo_projects),
        ("project_roles", _seed_demo_project_roles),
        ("inventory", _seed_demo_inventory),
        ("appraisal_template", _seed_demo_appraisal_template),
        ("job_listings", _seed_demo_job_listings),
        ("onboarding_template", _seed_onboarding_template),
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
# Public holiday seeding (Singapore 2026 gazetted holidays from MOM)
# ---------------------------------------------------------------------------

SG_PUBLIC_HOLIDAYS_2026 = [
    {"name": "New Year's Day", "date": "2026-01-01"},
    {"name": "Chinese New Year", "date": "2026-02-17"},
    {"name": "Chinese New Year (2nd day)", "date": "2026-02-18"},
    {"name": "Hari Raya Puasa", "date": "2026-03-20"},
    {"name": "Good Friday", "date": "2026-04-03"},
    {"name": "Labour Day", "date": "2026-05-01"},
    {"name": "Vesak Day", "date": "2026-05-12"},
    {"name": "Hari Raya Haji", "date": "2026-06-27"},
    {"name": "National Day", "date": "2026-08-09"},
    {"name": "Deepavali", "date": "2026-10-18"},
    {"name": "Christmas Day", "date": "2026-12-25"},
]


def _seed_public_holidays(company_id: int) -> dict:
    existing = _extract_records(
        _execute_node(
            "PublicHolidayListNode",
            "check_public_holidays",
            {"filter": {"company_id": company_id}, "limit": 1, "enable_cache": False},
        )
    )
    if existing:
        return {"skipped": True, "reason": "public holidays already exist"}

    count = 0
    for holiday in SG_PUBLIC_HOLIDAYS_2026:
        _execute_node(
            "PublicHolidayCreateNode",
            "create_public_holiday",
            {
                "company_id": company_id,
                "name": holiday["name"],
                "date": holiday["date"],
                "year": 2026,
                "is_gazetted": True,
            },
        )
        count += 1
    return {"created": count}


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


# ---------------------------------------------------------------------------
# Onboarding template seeding — Singapore Standard Onboarding
# ---------------------------------------------------------------------------

SG_ONBOARDING_MODULES = [
    {
        "name": "Company Orientation",
        "phase": "orientation",
        "sort_order": 0,
        "is_mandatory": False,
        "estimated_duration_minutes": 30,
        "steps": [
            {
                "title": "Welcome to the Team",
                "sort_order": 0,
                "step_type": "content",
                "body_content": (
                    "Welcome! This onboarding guide will help you get started. "
                    "Complete each section at your own pace."
                ),
            },
            {
                "title": "Meet Your Team",
                "sort_order": 1,
                "step_type": "content",
                "body_content": (
                    "Your department and team structure. Your manager will "
                    "introduce you to your colleagues in your first week."
                ),
            },
            {
                "title": "Office & IT Setup",
                "sort_order": 2,
                "step_type": "checklist",
                "checklist_items": json.dumps([
                    "Received laptop/workstation",
                    "Email account set up",
                    "Slack/Teams access",
                    "Building access card",
                    "Parking/transport arranged",
                ]),
            },
        ],
    },
    {
        "name": "Employment Documentation",
        "phase": "compliance",
        "sort_order": 1,
        "is_mandatory": True,
        "estimated_duration_minutes": 20,
        "steps": [
            {
                "title": "Employment Contract",
                "sort_order": 0,
                "step_type": "policy_acknowledgment",
                "body_content": "",
                # policy_id is resolved at seed time if a matching policy exists
                "_link_policy_type": "handbook",
            },
            {
                "title": "NRIC/FIN Copy",
                "sort_order": 1,
                "step_type": "document_upload",
                "body_content": (
                    "Upload a copy of your NRIC (Singapore Citizens/PRs) or "
                    "FIN (Foreign employees) for payroll and CPF registration."
                ),
            },
            {
                "title": "Bank Account Details",
                "sort_order": 2,
                "step_type": "form",
                "body_content": (
                    "Provide your bank details for salary payment. Your bank "
                    "account number will be encrypted at rest."
                ),
            },
            {
                "title": "Emergency Contact",
                "sort_order": 3,
                "step_type": "form",
                "body_content": (
                    "Provide at least one emergency contact person."
                ),
            },
        ],
    },
    {
        "name": "Singapore Compliance",
        "phase": "compliance",
        "sort_order": 2,
        "is_mandatory": True,
        "estimated_duration_minutes": 15,
        "steps": [
            {
                "title": "CPF Contributions",
                "sort_order": 0,
                "step_type": "content",
                "body_content": (
                    "Central Provident Fund (CPF) is mandatory for Singapore "
                    "Citizens and Permanent Residents. Your employer contributes "
                    "[employer rate]% and [employee rate]% is deducted from your "
                    "salary. EP/S Pass/WP holders are exempt."
                ),
            },
            {
                "title": "PDPA Consent",
                "sort_order": 1,
                "step_type": "policy_acknowledgment",
                "body_content": (
                    "Under the Personal Data Protection Act (PDPA), we collect "
                    "and process your personal data for employment purposes."
                ),
            },
            {
                "title": "Workplace Safety",
                "sort_order": 2,
                "step_type": "content",
                "body_content": (
                    "Under the Workplace Safety and Health Act, all employees "
                    "must be aware of workplace safety procedures. Report any "
                    "hazards to your supervisor immediately."
                ),
            },
        ],
    },
    {
        "name": "Leave & Benefits",
        "phase": "benefits",
        "sort_order": 3,
        "is_mandatory": False,
        "estimated_duration_minutes": 10,
        "steps": [
            {
                "title": "Leave Entitlements",
                "sort_order": 0,
                "step_type": "content",
                "body_content": (
                    "Singapore Employment Act provides minimum annual leave of "
                    "7 days (first year), increasing by 1 day per year up to "
                    "14 days. Sick leave: 14 days outpatient, 60 days "
                    "hospitalisation."
                ),
            },
            {
                "title": "Benefits Overview",
                "sort_order": 1,
                "step_type": "content",
                "body_content": (
                    "Review your compensation package including CPF "
                    "contributions, medical benefits, and any additional "
                    "allowances."
                ),
            },
        ],
    },
    {
        "name": "Probation & Goals",
        "phase": "probation",
        "sort_order": 4,
        "is_mandatory": False,
        "estimated_duration_minutes": 10,
        "steps": [
            {
                "title": "Probation Period",
                "sort_order": 0,
                "step_type": "content",
                "body_content": (
                    "Your probation period is [X] months. During this time, "
                    "your manager will conduct regular check-ins to support "
                    "your transition."
                ),
            },
            {
                "title": "30-60-90 Day Goals",
                "sort_order": 1,
                "step_type": "checklist",
                "checklist_items": json.dumps([
                    "Week 1: Complete all onboarding modules",
                    "Month 1: Meet all key stakeholders",
                    "Month 2: Take ownership of first project",
                    "Month 3: Operate independently in your role",
                ]),
            },
        ],
    },
]


def _seed_onboarding_template(company_id: int) -> dict:
    """Seed the Singapore Standard Onboarding template with modules and steps.

    Idempotent — checks for existing onboarding templates before creating.
    Uses dataflow_crud (express_sync) for all creates.
    """
    existing = dataflow_crud.list_records(
        "OnboardingTemplate",
        {"company_id": company_id},
        limit=1,
    )
    if existing:
        return {"skipped": True, "reason": "onboarding templates already exist"}

    now = datetime.now(timezone.utc).isoformat()

    # Resolve policy IDs for policy_acknowledgment steps (best-effort)
    policy_id_cache: dict[str, int | None] = {}
    policies = dataflow_crud.list_records(
        "CompanyPolicy",
        {"company_id": company_id},
    )
    for policy in policies:
        ptype = policy.get("policy_type", "")
        if ptype and ptype not in policy_id_cache:
            policy_id_cache[ptype] = policy.get("id")

    # 1. Create template
    template = dataflow_crud.create(
        "OnboardingTemplate",
        {
            "company_id": company_id,
            "name": "Singapore Standard Onboarding",
            "description": "Default onboarding template for Singapore-based employees.",
            "is_default": True,
            "version": 1,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    template_id = template["id"]

    # 2. Create modules and steps
    modules_created = 0
    steps_created = 0

    for module_def in SG_ONBOARDING_MODULES:
        step_defs = module_def.pop("steps", [])

        module = dataflow_crud.create(
            "OnboardingModule",
            {
                "template_id": template_id,
                "company_id": company_id,
                "name": module_def["name"],
                "description": "",
                "phase": module_def["phase"],
                "sort_order": module_def["sort_order"],
                "estimated_duration_minutes": module_def.get("estimated_duration_minutes", 0),
                "is_mandatory": module_def.get("is_mandatory", True),
                "is_role_specific": False,
                "role_filter": "",
            },
        )
        module_id = module["id"]
        modules_created += 1

        for step_def in step_defs:
            # Resolve policy_id for policy_acknowledgment steps
            policy_id = None
            link_policy_type = step_def.pop("_link_policy_type", None)
            if link_policy_type:
                policy_id = policy_id_cache.get(link_policy_type)

            dataflow_crud.create(
                "OnboardingStep",
                {
                    "module_id": module_id,
                    "title": step_def["title"],
                    "description": "",
                    "sort_order": step_def["sort_order"],
                    "step_type": step_def["step_type"],
                    "body_content": step_def.get("body_content", ""),
                    "checklist_items": step_def.get("checklist_items", ""),
                    "media_url": "",
                    "requires_completion": True,
                    "policy_id": policy_id,
                    "requires_previous_completion": False,
                },
            )
            steps_created += 1

        # Restore steps back so the constant is not mutated
        module_def["steps"] = step_defs

    logger.info(
        "Seeded onboarding template for company_id=%s: template_id=%s, modules=%s, steps=%s",
        company_id,
        template_id,
        modules_created,
        steps_created,
    )
    return {"created": {"template": 1, "modules": modules_created, "steps": steps_created}}
