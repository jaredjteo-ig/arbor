"""Calculator endpoints for HR computations.

Handles CPF contribution calculations, leave entitlement calculations,
salary structure breakdowns, and other HR-related computations.
"""

import logging
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.workflows.calculators.cost_to_company_calculator import (
    CostToCompanyInput,
    calculate_cost_to_company,
)
from hr_advisory.workflows.calculators.cpf_calculator import CPFInput, calculate_cpf_contributions
from hr_advisory.workflows.calculators.leave_calculator import (
    LeaveInput,
    calculate_leave_entitlement,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/cpf")
async def calculate_cpf(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Calculate CPF contributions for an employee.

    Accepts salary details and employee profile to compute
    employer and employee CPF contribution amounts.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"calculate_cpf:{user_id}", max_requests=30, window_seconds=60, action_name="calculate CPF")

    body = await request.json()

    # --- Validate required fields upfront instead of silently defaulting to zero ---
    missing = []
    if "gross_salary" not in body and "monthly_ow" not in body:
        missing.append("gross_salary (monthly gross salary)")
    if "employee_age" not in body and "age" not in body:
        missing.append("employee_age (employee's age)")
    if "citizenship_status" not in body:
        missing.append("citizenship_status ('SC', 'PR', or 'foreigner')")
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    # Accept both field-name conventions: frontend names and canonical names
    gross_salary = body.get("gross_salary", body.get("monthly_ow", 0))
    employee_age = body.get("employee_age", body.get("age", 30))
    citizenship_raw = body.get("citizenship_status", "SC")
    pr_year = body.get("pr_year", None)
    monthly_aw = body.get("monthly_aw", 0.0)
    ytd_ow = body.get("ytd_ow", 0.0)
    ytd_aw = body.get("ytd_aw", 0.0)

    # Normalize citizenship_status — frontend sends lowercase ("sc", "pr", "ep")
    # but CPFInput expects uppercase ("SC", "PR", "foreigner")
    CITIZENSHIP_MAP = {
        "sc": "SC",
        "pr": "PR",
        "ep": "foreigner",
        "foreigner": "foreigner",
        # Accept uppercase as-is
        "SC": "SC",
        "PR": "PR",
    }
    citizenship_status = CITIZENSHIP_MAP.get(citizenship_raw)
    if citizenship_status is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid citizenship_status '{citizenship_raw}'. "
                "Accepted values: 'SC', 'PR', 'foreigner' (or lowercase 'sc', 'pr', 'ep')."
            ),
        )

    # Validate numeric inputs
    try:
        gross_salary = float(gross_salary)
        employee_age = int(employee_age)
        monthly_aw = float(monthly_aw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid numeric value: {exc}",
        ) from exc

    if gross_salary <= 0:
        raise HTTPException(
            status_code=422,
            detail="gross_salary must be a positive number.",
        )
    if employee_age <= 0:
        raise HTTPException(
            status_code=422,
            detail="employee_age must be a positive integer.",
        )

    # PR employees must provide pr_year
    if citizenship_status == "PR" and pr_year is None:
        raise HTTPException(
            status_code=422,
            detail="pr_year is required for Permanent Resident employees (1, 2, or 3+).",
        )

    try:
        cpf_input = CPFInput(
            citizenship_status=citizenship_status,
            age=employee_age,
            monthly_ow=gross_salary,
            monthly_aw=monthly_aw,
            pr_year=pr_year,
            ytd_ow=ytd_ow,
            ytd_aw=ytd_aw,
        )
        result = calculate_cpf_contributions(cpf_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        **asdict(result),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/leave")
async def calculate_leave(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Calculate leave entitlements based on employment details.

    Computes annual leave, sick leave, maternity/paternity leave
    based on tenure, employment type, and applicable legislation.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"calculate_leave:{user_id}", max_requests=30, window_seconds=60, action_name="calculate leave")

    body = await request.json()
    years_of_service = body.get("years_of_service", 1)
    employment_type = body.get("employment_type", "full_time")
    leave_type = body.get("leave_type", "annual_leave")
    citizenship_status = body.get("citizenship_status", "SC")
    number_of_children = body.get("number_of_children", 0)
    child_ages = body.get("child_ages", [])
    child_citizenship = body.get("child_citizenship", "")
    child_order = body.get("child_order", 1)

    try:
        leave_input = LeaveInput(
            years_of_service=years_of_service,
            employment_type=employment_type,
            leave_type=leave_type,
            citizenship_status=citizenship_status,
            number_of_children=number_of_children,
            child_ages=child_ages,
            child_citizenship=child_citizenship,
            child_order=child_order,
        )
        result = calculate_leave_entitlement(leave_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        **asdict(result),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/salary")
async def calculate_salary(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Break down a salary structure into components.

    Uses real CPF calculator and cost-to-company calculator for accurate
    computation based on age, citizenship, and pass type.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"calculate_salary:{user_id}", max_requests=30, window_seconds=60, action_name="calculate salary")

    body = await request.json()
    gross_salary = body.get("gross_salary", 0)
    age = body.get("employee_age", 30)
    citizenship = body.get("citizenship_status", "sc").lower()
    pr_year = body.get("pr_year", 3)
    pass_type = body.get("pass_type", "")
    sector = body.get("sector", "services")

    try:
        # Get accurate CPF breakdown
        cpf_citizenship = "SC" if citizenship == "sc" else citizenship.upper()
        cpf_result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status=cpf_citizenship,
                age=age,
                monthly_ow=gross_salary,
                pr_year=pr_year,
            )
        )

        # Get full cost-to-company breakdown
        ctc_result = calculate_cost_to_company(
            CostToCompanyInput(
                monthly_salary=gross_salary,
                citizenship=citizenship,
                age=age,
                pr_year=pr_year,
                pass_type=pass_type,
                sector=sector,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "gross_salary": gross_salary,
        "cpf_employee_deduction": cpf_result.employee_contribution,
        "estimated_net_pay": round(gross_salary - cpf_result.employee_contribution, 2),
        "cpf_employer_contribution": cpf_result.employer_contribution,
        "total_cost_to_employer": ctc_result.total_monthly_cost,
        "total_annual_cost": ctc_result.total_annual_cost,
        "breakdown": ctc_result.breakdown,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
