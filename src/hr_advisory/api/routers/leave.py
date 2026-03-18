"""Leave management endpoints.

Handles leave types, applications (apply/approve/reject/withdraw/cancel),
balances, public holidays, leave policies, and team calendar.
"""

import logging
import math
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Input length limits
MAX_TEXT_LENGTH = 2000
MAX_NAME_LENGTH = 200


def _validate_text_length(value: str, field_name: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    """Validate text input to maximum length."""
    if value and len(value) > max_len:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {max_len} characters.",
        )
    return value


# --------------------------------------------------------------------------
# DataFlow helpers (same pattern as payroll.py)
# --------------------------------------------------------------------------


def _dataflow_create(node_type: str, data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]


def _dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000) -> list:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(
        node_type,
        "list",
        {"filter": filter_dict, "limit": limit, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    raw = results["list"]
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    if isinstance(raw, list):
        return raw
    return []


def _dataflow_update(node_type: str, record_id: int, updates: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, "update", {"filter": {"id": record_id}, "fields": updates})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["update"]


def _dataflow_read(node_type: str, record_id: int) -> dict | None:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, "read", {"id": record_id})
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    result = results.get("read", {})
    if result.get("error") or result.get("failed"):
        return None
    return result


def _get_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Resolve the Employee record for a given user_id + company_id."""
    records = _dataflow_list(
        "EmployeeListNode",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


# --------------------------------------------------------------------------
# Business-logic helpers
# --------------------------------------------------------------------------


def _calculate_working_days(
    start_date: str,
    end_date: str,
    start_half: str,
    end_half: str,
    company_id: int,
) -> float:
    """Calculate total leave days excluding weekends and public holidays.

    Half-day support: if start_half or end_half is first_half/second_half,
    that day counts as 0.5.
    """
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)

    if ed < sd:
        return 0.0

    # Fetch public holidays for the date range
    years = set()
    cursor = sd
    while cursor <= ed:
        years.add(cursor.year)
        cursor += timedelta(days=365)
    years.add(ed.year)

    holiday_dates: set[str] = set()
    for yr in years:
        holidays = _dataflow_list(
            "PublicHolidayListNode",
            {"year": yr},
        )
        # Include national (company_id=0) and company-specific holidays
        for h in holidays:
            h_company = h.get("company_id", 0)
            if h_company == 0 or h_company == company_id:
                holiday_dates.add(h.get("date", ""))

    total = 0.0
    current = sd
    while current <= ed:
        # Skip weekends (Saturday=5, Sunday=6)
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        # Skip public holidays
        if current.isoformat() in holiday_dates:
            current += timedelta(days=1)
            continue

        day_value = 1.0
        if current == sd and start_half in ("first_half", "second_half"):
            day_value = 0.5
        if current == ed and end_half in ("first_half", "second_half"):
            day_value = 0.5
        # If start and end are the same day and both are half, still 0.5
        if (
            current == sd == ed
            and start_half in ("first_half", "second_half")
            and end_half in ("first_half", "second_half")
        ):
            day_value = 0.5

        total += day_value
        current += timedelta(days=1)

    return total


def _check_overlapping_applications(
    employee_id: int, start_date: str, end_date: str, exclude_id: int | None = None
) -> bool:
    """Return True if there is an overlapping non-withdrawn/cancelled application."""
    apps = _dataflow_list(
        "LeaveApplicationListNode",
        {"employee_id": employee_id},
    )
    for app in apps:
        if app.get("status") in ("withdrawn", "cancelled", "rejected"):
            continue
        if exclude_id and app.get("id") == exclude_id:
            continue
        app_start = app.get("start_date", "")
        app_end = app.get("end_date", "")
        # Overlap check: NOT (end < app_start OR start > app_end)
        if not (end_date < app_start or start_date > app_end):
            return True
    return False


def _get_or_create_balance(
    employee_id: int, company_id: int, leave_type_code: str, year: int
) -> dict:
    """Get or create a LeaveBalance record for the given employee/type/year.

    T291: Lazy balance creation — looks up LeaveTypeConfig to determine
    proper entitlement, respecting gender and service-month rules.
    """
    balances = _dataflow_list(
        "LeaveBalanceListNode",
        {
            "employee_id": employee_id,
            "leave_type": leave_type_code,
            "year": year,
        },
        limit=1,
    )
    if balances:
        return balances[0]

    # Look up the LeaveTypeConfig for this company + code to get proper entitlement
    entitlement = 0.0
    configs = _dataflow_list(
        "LeaveTypeConfigListNode",
        {"company_id": company_id, "code": leave_type_code},
        limit=1,
    )
    if configs:
        config = configs[0]
        entitlement = _calculate_entitlement_for_employee(config, employee_id, company_id, year)

    return _dataflow_create(
        "LeaveBalanceCreateNode",
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "leave_type": leave_type_code,
            "year": year,
            "entitlement_days": entitlement,
            "used_days": 0.0,
            "pending_days": 0.0,
        },
    )


def _calculate_entitlement_for_employee(
    config: dict, employee_id: int, company_id: int, year: int
) -> float:
    """Calculate leave entitlement for an employee based on LeaveTypeConfig.

    T292: Respects applicable_gender, min_service_months, service-year
    progression for annual leave, and pro-ration for mid-year joiners.
    """
    default_days = config.get("default_days", 0.0)
    applicable_gender = config.get("applicable_gender", "")
    min_service_months = config.get("min_service_months", 0)
    is_pro_ratable = config.get("is_pro_ratable", False)
    code = config.get("code", "")

    # Look up employee details for gender and start_date checks
    employees = _dataflow_list(
        "EmployeeListNode",
        {"id": employee_id, "company_id": company_id},
        limit=1,
    )
    if not employees:
        return default_days

    emp = employees[0]
    emp_gender = emp.get("gender", "").lower()
    start_date_str = emp.get("start_date", "")

    # Gender filter: skip if leave type is gender-restricted and doesn't match
    if applicable_gender and emp_gender and emp_gender != applicable_gender.lower():
        return 0.0

    # Service months check
    if start_date_str and min_service_months > 0:
        try:
            start_dt = date.fromisoformat(start_date_str)
            as_of = date(year, 12, 31)  # entitlement for this year
            months_of_service = (as_of.year - start_dt.year) * 12 + (as_of.month - start_dt.month)
            if months_of_service < min_service_months:
                return 0.0
        except (ValueError, TypeError):
            pass

    # T295: Annual leave service-year progression (EA schedule)
    if code == "annual" and start_date_str:
        try:
            start_dt = date.fromisoformat(start_date_str)
            completed_years = year - start_dt.year
            if date(year, 1, 1) < start_dt:
                completed_years = 0  # haven't completed first year yet
            # EA: 7 days year 1, +1 per year, max 14
            default_days = min(7 + max(0, completed_years - 1), 14)
        except (ValueError, TypeError):
            pass

    # T297: Pro-ration for mid-year joiners
    if is_pro_ratable and start_date_str:
        try:
            start_dt = date.fromisoformat(start_date_str)
            if start_dt.year == year and start_dt.month > 1:
                remaining_months = 12 - start_dt.month + 1
                prorated = default_days * remaining_months / 12
                # Round up to nearest 0.5 (standard SG practice)
                import math

                default_days = math.ceil(prorated * 2) / 2
        except (ValueError, TypeError):
            pass

    return default_days


def ensure_leave_balances(employee_id: int, company_id: int, year: int | None = None) -> list[dict]:
    """Ensure LeaveBalance records exist for all applicable leave types.

    T291: Called when employee views leave or applies for leave.
    Creates missing balances on demand from LeaveTypeConfig.
    Returns all balances for the employee/year.
    """
    if year is None:
        year = date.today().year

    # Get all leave type configs for this company
    configs = _dataflow_list(
        "LeaveTypeConfigListNode",
        {"company_id": company_id},
    )

    balances = []
    for config in configs:
        code = config.get("code", "")
        if not code:
            continue
        balance = _get_or_create_balance(employee_id, company_id, code, year)
        balances.append(balance)

    return balances


# --------------------------------------------------------------------------
# Seed: Singapore statutory leave types
# --------------------------------------------------------------------------

SINGAPORE_STATUTORY_LEAVE_TYPES = [
    {
        "code": "annual",
        "name": "Annual Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 7.0,
        "max_carry_forward": 0.0,
        "is_pro_ratable": True,
        "requires_attachment": False,
        "min_service_months": 3,
        "applicable_gender": "",
    },
    {
        "code": "sick",
        "name": "Outpatient Sick Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 14.0,
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": True,
        "min_service_months": 3,
        "applicable_gender": "",
    },
    {
        "code": "hospitalization",
        "name": "Hospitalisation Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 60.0,
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": True,
        "min_service_months": 3,
        "applicable_gender": "",
    },
    {
        "code": "maternity",
        "name": "Maternity Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 112.0,  # 16 weeks
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": True,
        "min_service_months": 3,
        "applicable_gender": "female",
    },
    {
        "code": "paternity",
        "name": "Paternity Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 28.0,  # 4 weeks (CDCSA amendment effective 1 Jan 2025)
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": True,
        "min_service_months": 3,
        "applicable_gender": "male",
    },
    {
        "code": "childcare",
        "name": "Childcare Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 6.0,
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": False,
        "min_service_months": 3,
        "applicable_gender": "",
    },
    {
        "code": "infant_care",
        "name": "Infant Care Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 6.0,
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": False,
        "min_service_months": 3,
        "applicable_gender": "",
    },
    {
        "code": "adoption",
        "name": "Adoption Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 84.0,  # 12 weeks
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": True,
        "min_service_months": 3,
        "applicable_gender": "female",
    },
    {
        "code": "shared_parental",
        "name": "Shared Parental Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 28.0,  # 4 weeks
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": True,
        "min_service_months": 3,
        "applicable_gender": "male",
    },
    {
        "code": "unpaid_infant_care",
        "name": "Unpaid Infant Care Leave",
        "category": "statutory",
        "is_paid": False,
        "default_days": 6.0,
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": False,
        "min_service_months": 3,
        "applicable_gender": "",
    },
    {
        "code": "ns",
        "name": "NS Reservist Leave",
        "category": "statutory",
        "is_paid": True,
        "default_days": 0.0,  # Duration as called up
        "max_carry_forward": 0.0,
        "is_pro_ratable": False,
        "requires_attachment": True,
        "min_service_months": 0,
        "applicable_gender": "male",
    },
]


def _seed_statutory_leave_types(company_id: int) -> list[dict]:
    """Create all Singapore statutory leave types for a company.

    Skips any leave type whose code already exists for the company.
    Returns the list of created leave type configs.
    """
    existing = _dataflow_list(
        "LeaveTypeConfigListNode",
        {"company_id": company_id},
    )
    existing_codes = {lt.get("code") for lt in existing}

    created = []
    for lt in SINGAPORE_STATUTORY_LEAVE_TYPES:
        if lt["code"] in existing_codes:
            continue
        record = _dataflow_create(
            "LeaveTypeConfigCreateNode",
            {
                "company_id": company_id,
                **lt,
            },
        )
        created.append(record)
    return created


# ==========================================================================
# LEAVE TYPES
# ==========================================================================


# --------------------------------------------------------------------------
# GET /types — List leave types for company
# --------------------------------------------------------------------------


@router.get("/types")
async def list_leave_types(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all configured leave types for the current company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    types = _dataflow_list(
        "LeaveTypeConfigListNode",
        {"company_id": company_id, "is_active": True},
    )
    return {"leave_types": types, "count": len(types)}


# --------------------------------------------------------------------------
# POST /types — Create leave type (admin)
# --------------------------------------------------------------------------


@router.post("/types")
async def create_leave_type(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a new leave type for the company.

    Pass {"seed_statutory": true} to auto-create all Singapore statutory
    leave types instead of a single custom type.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()

    # Seed mode: create all statutory leave types
    if body.get("seed_statutory"):
        created = _seed_statutory_leave_types(company_id)
        return {
            "message": f"Seeded {len(created)} statutory leave type(s).",
            "leave_types": created,
        }

    # Single creation
    name = body.get("name", "").strip()
    code = body.get("code", "").strip()
    if not name or not code:
        raise HTTPException(status_code=400, detail="name and code are required.")

    # Check for duplicate code
    existing = _dataflow_list(
        "LeaveTypeConfigListNode",
        {"company_id": company_id},
    )
    if any(lt.get("code") == code for lt in existing):
        raise HTTPException(status_code=409, detail=f"Leave type code '{code}' already exists.")

    record = _dataflow_create(
        "LeaveTypeConfigCreateNode",
        {
            "company_id": company_id,
            "name": name,
            "code": code,
            "category": body.get("category", "company"),
            "is_paid": body.get("is_paid", True),
            "is_pro_ratable": body.get("is_pro_ratable", True),
            "default_days": body.get("default_days", 0.0),
            "max_carry_forward": body.get("max_carry_forward", 0.0),
            "carry_forward_expiry_months": body.get("carry_forward_expiry_months", 0),
            "requires_attachment": body.get("requires_attachment", False),
            "min_service_months": body.get("min_service_months", 0),
            "applicable_gender": body.get("applicable_gender", ""),
            "is_active": True,
        },
    )
    return {"leave_type": record}


# --------------------------------------------------------------------------
# PATCH /types/{id} — Update leave type (admin)
# --------------------------------------------------------------------------


@router.patch("/types/{leave_type_id}")
async def update_leave_type(
    leave_type_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update an existing leave type configuration."""
    company_id = get_current_company_id(current_user)
    lt = _dataflow_read("LeaveTypeConfigReadNode", leave_type_id)
    if lt is None or lt.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Leave type not found.")

    body = await request.json()
    allowed_fields = {
        "name",
        "is_paid",
        "is_pro_ratable",
        "default_days",
        "max_carry_forward",
        "carry_forward_expiry_months",
        "requires_attachment",
        "min_service_months",
        "applicable_gender",
        "is_active",
        "category",
    }
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    _dataflow_update("LeaveTypeConfigUpdateNode", leave_type_id, updates)
    return {"message": "Leave type updated.", "id": leave_type_id}


# ==========================================================================
# LEAVE APPLICATIONS
# ==========================================================================


# --------------------------------------------------------------------------
# POST /apply — Submit leave application
# --------------------------------------------------------------------------


@router.post("/apply")
async def apply_leave(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit a leave application.

    Validates: sufficient balance, no overlapping applications, and
    auto-calculates total_days excluding weekends and public holidays.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    user_id = int(current_user.get("sub", 0))
    employee = _get_employee_for_user(user_id, company_id)
    if employee is None:
        raise HTTPException(status_code=400, detail="No employee record found.")

    body = await request.json()
    leave_type_id = body.get("leave_type_id")
    start_date = body.get("start_date", "")
    end_date = body.get("end_date", "")
    start_half = body.get("start_half", "full_day")
    end_half = body.get("end_half", "full_day")
    reason = body.get("reason", "")
    _validate_text_length(reason, "reason")

    if not leave_type_id or not start_date or not end_date:
        raise HTTPException(
            status_code=400,
            detail="leave_type_id, start_date, and end_date are required.",
        )

    # Validate dates
    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if ed < sd:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date.")

    # Validate leave type exists and belongs to this company
    lt = _dataflow_read("LeaveTypeConfigReadNode", leave_type_id)
    if lt is None or lt.get("company_id") != company_id or not lt.get("is_active", True):
        raise HTTPException(status_code=404, detail="Leave type not found.")

    leave_type_code = lt.get("code", "")
    employee_id = employee.get("id")

    # Calculate working days
    total_days = _calculate_working_days(start_date, end_date, start_half, end_half, company_id)
    if total_days <= 0:
        raise HTTPException(status_code=400, detail="No working days in the selected range.")

    # Check overlapping applications
    if _check_overlapping_applications(employee_id, start_date, end_date):
        raise HTTPException(status_code=409, detail="Overlapping leave application exists.")

    # Check balance
    year = sd.year
    balance = _get_or_create_balance(employee_id, company_id, leave_type_code, year)
    available = (
        balance.get("entitlement_days", 0.0)
        - balance.get("used_days", 0.0)
        - balance.get("pending_days", 0.0)
    )
    if total_days > available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient leave balance. Available: {available}, Requested: {total_days}.",
        )

    now = datetime.now(timezone.utc).isoformat()

    # Create the application
    application = _dataflow_create(
        "LeaveApplicationCreateNode",
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "leave_type_id": leave_type_id,
            "leave_type_code": leave_type_code,
            "start_date": start_date,
            "end_date": end_date,
            "start_half": start_half,
            "end_half": end_half,
            "total_days": total_days,
            "reason": reason,
            "attachment_path": body.get("attachment_path", ""),
            "status": "pending",
            "applied_at": now,
        },
    )

    # Increase pending days on balance
    _dataflow_update(
        "LeaveBalanceUpdateNode",
        balance["id"],
        {"pending_days": balance.get("pending_days", 0.0) + total_days},
    )

    return {"application": application}


# --------------------------------------------------------------------------
# GET /applications — List leave applications
# --------------------------------------------------------------------------


@router.get("/applications")
async def list_applications(
    status: str = Query(default="", description="Filter by status"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List leave applications.

    Employees see their own applications only.
    Owners and HR managers see all applications for the company.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    role = current_user.get("role", "employee")
    user_id = int(current_user.get("sub", 0))

    if role in ("owner", "hr_manager"):
        filter_dict: dict = {"company_id": company_id}
    else:
        employee = _get_employee_for_user(user_id, company_id)
        if employee is None:
            return {"applications": [], "count": 0}
        filter_dict = {"employee_id": employee.get("id")}

    if status:
        filter_dict["status"] = status

    apps = _dataflow_list("LeaveApplicationListNode", filter_dict)
    apps.sort(key=lambda a: a.get("applied_at", ""), reverse=True)
    return {"applications": apps, "count": len(apps)}


# --------------------------------------------------------------------------
# PATCH /applications/{id}/approve — Approve leave
# --------------------------------------------------------------------------


@router.patch("/applications/{application_id}/approve")
async def approve_application(
    application_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Approve a pending leave application.

    Moves pending_days to used_days on the leave balance.
    """
    company_id = get_current_company_id(current_user)
    app = _dataflow_read("LeaveApplicationReadNode", application_id)
    if app is None or app.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Leave application not found.")

    if app.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending applications can be approved.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    remarks = body.get("remarks", "")

    _dataflow_update(
        "LeaveApplicationUpdateNode",
        application_id,
        {
            "status": "approved",
            "reviewed_by": actor_id,
            "reviewed_at": now,
            "reviewer_remarks": remarks,
        },
    )

    # Update balance: move from pending to used
    total_days = app.get("total_days", 0.0)
    leave_type_code = app.get("leave_type_code", "")
    employee_id = app.get("employee_id")
    year = date.fromisoformat(app.get("start_date", "2026-01-01")).year

    balance = _get_or_create_balance(employee_id, company_id, leave_type_code, year)
    _dataflow_update(
        "LeaveBalanceUpdateNode",
        balance["id"],
        {
            "used_days": balance.get("used_days", 0.0) + total_days,
            "pending_days": max(0.0, balance.get("pending_days", 0.0) - total_days),
        },
    )

    return {"message": "Leave approved.", "id": application_id, "status": "approved"}


# --------------------------------------------------------------------------
# PATCH /applications/{id}/reject — Reject leave
# --------------------------------------------------------------------------


@router.patch("/applications/{application_id}/reject")
async def reject_application(
    application_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reject a pending leave application. Remarks are required."""
    company_id = get_current_company_id(current_user)
    app = _dataflow_read("LeaveApplicationReadNode", application_id)
    if app is None or app.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Leave application not found.")

    if app.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending applications can be rejected.")

    body = await request.json()
    remarks = body.get("remarks", "").strip()
    if not remarks:
        raise HTTPException(status_code=400, detail="Remarks are required when rejecting leave.")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    _dataflow_update(
        "LeaveApplicationUpdateNode",
        application_id,
        {
            "status": "rejected",
            "reviewed_by": actor_id,
            "reviewed_at": now,
            "reviewer_remarks": remarks,
        },
    )

    # Restore pending days
    total_days = app.get("total_days", 0.0)
    leave_type_code = app.get("leave_type_code", "")
    employee_id = app.get("employee_id")
    year = date.fromisoformat(app.get("start_date", "2026-01-01")).year

    balance = _get_or_create_balance(employee_id, company_id, leave_type_code, year)
    _dataflow_update(
        "LeaveBalanceUpdateNode",
        balance["id"],
        {
            "pending_days": max(0.0, balance.get("pending_days", 0.0) - total_days),
        },
    )

    return {"message": "Leave rejected.", "id": application_id, "status": "rejected"}


# --------------------------------------------------------------------------
# PATCH /applications/{id}/withdraw — Employee withdraws own pending
# --------------------------------------------------------------------------


@router.patch("/applications/{application_id}/withdraw")
async def withdraw_application(
    application_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Withdraw a pending leave application. Only the applicant can withdraw."""
    company_id = get_current_company_id(current_user)
    user_id = int(current_user.get("sub", 0))

    app = _dataflow_read("LeaveApplicationReadNode", application_id)
    if app is None or app.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Leave application not found.")

    if app.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending applications can be withdrawn.")

    # Verify ownership
    employee = _get_employee_for_user(user_id, company_id)
    if employee is None or employee.get("id") != app.get("employee_id"):
        raise HTTPException(status_code=403, detail="You can only withdraw your own applications.")

    now = datetime.now(timezone.utc).isoformat()
    _dataflow_update(
        "LeaveApplicationUpdateNode",
        application_id,
        {"status": "withdrawn", "reviewed_at": now},
    )

    # Restore pending days
    total_days = app.get("total_days", 0.0)
    leave_type_code = app.get("leave_type_code", "")
    employee_id = app.get("employee_id")
    year = date.fromisoformat(app.get("start_date", "2026-01-01")).year

    balance = _get_or_create_balance(employee_id, company_id, leave_type_code, year)
    _dataflow_update(
        "LeaveBalanceUpdateNode",
        balance["id"],
        {
            "pending_days": max(0.0, balance.get("pending_days", 0.0) - total_days),
        },
    )

    return {"message": "Leave withdrawn.", "id": application_id, "status": "withdrawn"}


# --------------------------------------------------------------------------
# PATCH /applications/{id}/cancel — Admin cancels approved leave
# --------------------------------------------------------------------------


@router.patch("/applications/{application_id}/cancel")
async def cancel_application(
    application_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Cancel an approved leave application. Restores used_days to the balance."""
    company_id = get_current_company_id(current_user)
    app = _dataflow_read("LeaveApplicationReadNode", application_id)
    if app is None or app.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Leave application not found.")

    if app.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved applications can be cancelled.")

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    remarks = body.get("remarks", "")

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    _dataflow_update(
        "LeaveApplicationUpdateNode",
        application_id,
        {
            "status": "cancelled",
            "reviewed_by": actor_id,
            "reviewed_at": now,
            "reviewer_remarks": remarks,
        },
    )

    # Restore used days to balance
    total_days = app.get("total_days", 0.0)
    leave_type_code = app.get("leave_type_code", "")
    employee_id = app.get("employee_id")
    year = date.fromisoformat(app.get("start_date", "2026-01-01")).year

    balance = _get_or_create_balance(employee_id, company_id, leave_type_code, year)
    _dataflow_update(
        "LeaveBalanceUpdateNode",
        balance["id"],
        {
            "used_days": max(0.0, balance.get("used_days", 0.0) - total_days),
        },
    )

    return {"message": "Leave cancelled.", "id": application_id, "status": "cancelled"}


# ==========================================================================
# LEAVE BALANCES
# ==========================================================================


# --------------------------------------------------------------------------
# GET /balances/{employee_id} — Balance by type for a year
# --------------------------------------------------------------------------


@router.get("/balances/{employee_id}")
async def get_leave_balances(
    employee_id: int,
    year: int = 0,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get leave balances for an employee, broken down by leave type.

    Employees can view their own balance; admins can view any employee's.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    if year == 0:
        year = datetime.now(timezone.utc).year

    # Access control: employees can only view their own
    role = current_user.get("role", "employee")
    user_id = int(current_user.get("sub", 0))
    if role not in ("owner", "hr_manager"):
        employee = _get_employee_for_user(user_id, company_id)
        if employee is None or employee.get("id") != employee_id:
            raise HTTPException(status_code=403, detail="Access denied.")

    # Verify employee belongs to company
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    balances = _dataflow_list(
        "LeaveBalanceListNode",
        {"employee_id": employee_id, "year": year},
    )

    return {"employee_id": employee_id, "year": year, "balances": balances}


# ==========================================================================
# PUBLIC HOLIDAYS
# ==========================================================================


# --------------------------------------------------------------------------
# GET /public-holidays — List holidays
# --------------------------------------------------------------------------


@router.get("/public-holidays")
async def list_public_holidays(
    year: int = 0,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List public holidays for a year. Includes national and company-specific."""
    company_id = get_current_company_id(current_user)
    if year == 0:
        year = datetime.now(timezone.utc).year

    holidays = _dataflow_list("PublicHolidayListNode", {"year": year})

    # Filter to national + company-specific
    visible = [
        h for h in holidays if h.get("company_id", 0) == 0 or h.get("company_id") == company_id
    ]
    visible.sort(key=lambda h: h.get("date", ""))

    return {"year": year, "holidays": visible, "count": len(visible)}


# --------------------------------------------------------------------------
# POST /public-holidays — Create holiday (admin)
# --------------------------------------------------------------------------


@router.post("/public-holidays")
async def create_public_holiday(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a public holiday entry."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    holiday_date = body.get("date", "").strip()

    if not name or not holiday_date:
        raise HTTPException(status_code=400, detail="name and date are required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    try:
        d = date.fromisoformat(holiday_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    record = _dataflow_create(
        "PublicHolidayCreateNode",
        {
            "company_id": company_id,
            "name": name,
            "date": holiday_date,
            "year": d.year,
            "is_gazetted": body.get("is_gazetted", True),
        },
    )
    return {"holiday": record}


# ==========================================================================
# LEAVE POLICIES
# ==========================================================================


# --------------------------------------------------------------------------
# GET /policies — List leave policies
# --------------------------------------------------------------------------


@router.get("/policies")
async def list_leave_policies(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all leave policies for the company."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    policies = _dataflow_list(
        "LeavePolicyListNode",
        {"company_id": company_id, "is_active": True},
    )

    # Enrich with entitlement counts
    enriched = []
    for p in policies:
        entitlements = _dataflow_list(
            "LeavePolicyEntitlementListNode",
            {"policy_id": p.get("id")},
        )
        enriched.append({**p, "entitlement_count": len(entitlements)})

    return {"policies": enriched, "count": len(enriched)}


# --------------------------------------------------------------------------
# POST /policies — Create leave policy
# --------------------------------------------------------------------------


@router.post("/policies")
async def create_leave_policy(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Create a leave policy with optional entitlements.

    Body:
    {
        "name": "Full-time Policy",
        "is_default": true,
        "entitlements": [
            {"leave_type_id": 1, "days": 14, "carry_forward_days": 5},
            ...
        ]
    }
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")

    _validate_text_length(name, "name", MAX_NAME_LENGTH)

    is_default = body.get("is_default", False)

    # If setting as default, unset existing default
    if is_default:
        existing = _dataflow_list(
            "LeavePolicyListNode",
            {"company_id": company_id, "is_default": True},
        )
        for p in existing:
            _dataflow_update("LeavePolicyUpdateNode", p["id"], {"is_default": False})

    policy = _dataflow_create(
        "LeavePolicyCreateNode",
        {
            "company_id": company_id,
            "name": name,
            "is_default": is_default,
            "is_active": True,
        },
    )
    policy_id = policy.get("id")

    # Create entitlements
    entitlements = body.get("entitlements", [])
    created_entitlements = []
    for ent in entitlements:
        lt_id = ent.get("leave_type_id")
        if not lt_id:
            continue
        record = _dataflow_create(
            "LeavePolicyEntitlementCreateNode",
            {
                "policy_id": policy_id,
                "company_id": company_id,
                "leave_type_id": lt_id,
                "days": ent.get("days", 0.0),
                "carry_forward_days": ent.get("carry_forward_days", 0.0),
            },
        )
        created_entitlements.append(record)

    return {
        "policy": policy,
        "entitlements": created_entitlements,
    }


# ==========================================================================
# TEAM CALENDAR
# ==========================================================================


# --------------------------------------------------------------------------
# GET /calendar — Team calendar (who's on leave by month)
# --------------------------------------------------------------------------


@router.get("/calendar")
async def team_calendar(
    year: int = 0,
    month: int = 0,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get team leave calendar data for a given month.

    Returns approved leave applications overlapping the requested month,
    plus public holidays.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    if year == 0:
        year = datetime.now(timezone.utc).year
    if month == 0:
        month = datetime.now(timezone.utc).month

    # Month boundaries
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year, 12, 31)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    month_start_str = month_start.isoformat()
    month_end_str = month_end.isoformat()

    # Fetch approved leave applications for the company
    apps = _dataflow_list(
        "LeaveApplicationListNode",
        {"company_id": company_id, "status": "approved"},
    )

    # Filter to those overlapping the month
    overlapping = []
    for app in apps:
        app_start = app.get("start_date", "")
        app_end = app.get("end_date", "")
        if not app_start or not app_end:
            continue
        if not (app_end < month_start_str or app_start > month_end_str):
            overlapping.append(app)

    # Enrich with employee names
    calendar_entries = []
    for app in overlapping:
        emp_records = _dataflow_list("EmployeeListNode", {"id": app.get("employee_id")}, limit=1)
        emp = emp_records[0] if emp_records else {}
        user = None
        if emp:
            user_records = _dataflow_list("UserListNode", {"id": emp.get("user_id")}, limit=1)
            user = user_records[0] if user_records else None
        calendar_entries.append(
            {
                "application_id": app.get("id"),
                "employee_id": app.get("employee_id"),
                "employee_name": user.get("name", "") if user else "",
                "department": emp.get("department", ""),
                "leave_type_code": app.get("leave_type_code", ""),
                "start_date": app.get("start_date"),
                "end_date": app.get("end_date"),
                "total_days": app.get("total_days"),
            }
        )

    # Public holidays in this month
    holidays = _dataflow_list("PublicHolidayListNode", {"year": year})
    month_holidays = [
        h
        for h in holidays
        if (h.get("company_id", 0) == 0 or h.get("company_id") == company_id)
        and month_start_str <= h.get("date", "") <= month_end_str
    ]

    return {
        "year": year,
        "month": month,
        "leave_entries": calendar_entries,
        "public_holidays": month_holidays,
    }


# ==========================================================================
# LEAVE ENCASHMENT (T344)
# ==========================================================================


@router.post("/encash")
async def leave_encashment(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Convert unused leave to salary for an employee.

    Body: {employee_id, leave_type_code, days, year?, amount_per_day}
    Creates an encashment record and reduces leave balance.
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    employee_id = body.get("employee_id")
    leave_type_code = body.get("leave_type_code", "").strip()
    days = float(body.get("days", 0))
    amount_per_day = float(body.get("amount_per_day", 0))
    year = body.get("year", datetime.now(timezone.utc).year)

    if not math.isfinite(days) or not math.isfinite(amount_per_day):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")

    if not employee_id or not leave_type_code:
        raise HTTPException(
            status_code=400,
            detail="employee_id and leave_type_code are required.",
        )
    if days <= 0 or amount_per_day <= 0:
        raise HTTPException(
            status_code=400,
            detail="days and amount_per_day must be positive.",
        )

    # Verify employee belongs to company
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Check balance
    balance = _get_or_create_balance(employee_id, company_id, leave_type_code, year)
    available = (
        balance.get("entitlement_days", 0.0)
        - balance.get("used_days", 0.0)
        - balance.get("pending_days", 0.0)
    )
    if days > available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: {available}, Requested: {days}.",
        )

    total_amount = round(days * amount_per_day, 2)
    now = datetime.now(timezone.utc).isoformat()
    actor_id = int(current_user.get("sub", 0))

    # Create encashment record
    encashment = _dataflow_create(
        "LeaveEncashmentCreateNode",
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "leave_type_code": leave_type_code,
            "year": year,
            "days": days,
            "amount_per_day": amount_per_day,
            "total_amount": total_amount,
            "approved_by": actor_id,
            "approved_at": now,
        },
    )

    # Deduct from balance (mark as used)
    _dataflow_update(
        "LeaveBalanceUpdateNode",
        balance["id"],
        {"used_days": balance.get("used_days", 0.0) + days},
    )

    return {"encashment": encashment, "balance_remaining": round(available - days, 1)}


# ==========================================================================
# OFF-IN-LIEU (T346)
# ==========================================================================


@router.post("/off-in-lieu")
async def credit_off_in_lieu(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Admin credits off-in-lieu days to an employee's balance.

    Body: {employee_id, days, reason, date_worked}
    """
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    employee_id = body.get("employee_id")
    days = float(body.get("days", 0))
    reason = body.get("reason", "").strip()
    date_worked = body.get("date_worked", "")

    if not math.isfinite(days):
        raise HTTPException(status_code=400, detail="Invalid numeric value.")

    _validate_text_length(reason, "reason")

    if not employee_id or days <= 0:
        raise HTTPException(
            status_code=400,
            detail="employee_id and positive days are required.",
        )

    # Verify employee belongs to company
    emp_records = _dataflow_list("EmployeeListNode", {"id": employee_id}, limit=1)
    if not emp_records or emp_records[0].get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Employee not found.")

    year = datetime.now(timezone.utc).year
    if date_worked:
        try:
            year = date.fromisoformat(date_worked).year
        except ValueError:
            pass

    # Get or create off_in_lieu balance
    balance = _get_or_create_balance(employee_id, company_id, "off_in_lieu", year)

    # Credit by increasing entitlement
    new_entitlement = balance.get("entitlement_days", 0.0) + days
    _dataflow_update(
        "LeaveBalanceUpdateNode",
        balance["id"],
        {"entitlement_days": new_entitlement},
    )

    actor_id = int(current_user.get("sub", 0))
    now = datetime.now(timezone.utc).isoformat()

    # Create an audit record
    record = _dataflow_create(
        "OffInLieuRecordCreateNode",
        {
            "employee_id": employee_id,
            "company_id": company_id,
            "days": days,
            "reason": reason,
            "date_worked": date_worked,
            "credited_by": actor_id,
            "credited_at": now,
        },
    )

    return {
        "off_in_lieu": record,
        "new_entitlement": new_entitlement,
    }


# ==========================================================================
# LEAVE TYPE CONFIG EXTENDED (T343, T345, T347)
# ==========================================================================


@router.get("/type-configs")
async def list_leave_type_configs(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all leave type configs for the company (including inactive)."""
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    configs = _dataflow_list("LeaveTypeConfigListNode", {"company_id": company_id})
    return {"type_configs": configs, "count": len(configs)}


@router.patch("/type-configs/{config_id}")
async def update_leave_type_config(
    config_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Update a leave type config with extended fields.

    Supports all base fields plus: allow_hourly, hours_per_day,
    encashment_enabled, encashment_max_days, unused_handling,
    carry_forward_max_days, carry_forward_expiry_months,
    allow_overflow, entitlement_period.
    """
    company_id = get_current_company_id(current_user)
    config = _dataflow_read("LeaveTypeConfigReadNode", config_id)
    if config is None or config.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Leave type config not found.")

    body = await request.json()
    allowed_fields = {
        # Base fields
        "name", "is_paid", "is_pro_ratable", "default_days",
        "max_carry_forward", "carry_forward_expiry_months",
        "requires_attachment", "min_service_months",
        "applicable_gender", "is_active", "category",
        # Extended fields (T343, T345, T347)
        "allow_hourly", "hours_per_day",
        "encashment_enabled", "encashment_max_days",
        "unused_handling",  # forfeit, carry_forward, encash
        "carry_forward_max_days",
        "allow_overflow",
        "entitlement_period",  # calendar_year, anniversary, custom
    }
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    _dataflow_update("LeaveTypeConfigUpdateNode", config_id, updates)
    updated = _dataflow_read("LeaveTypeConfigReadNode", config_id)
    return {"type_config": updated}
