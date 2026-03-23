"""Seed realistic employee data for Acme Pte Ltd."""

import os
import sys

# Load .env before anything else
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from hr_advisory.services.auth_service import AuthService

auth = AuthService()

COMPANY_ID = 1
EMPLOYEES = [
    {
        "name": "Ahmad bin Ibrahim",
        "email": "ahmad@acme.sg",
        "department": "Engineering",
        "employment_type": "full_time",
        "nationality": "SC",
        "salary": 6500,
        "start_date": "2023-06-15",
    },
    {
        "name": "Priya Nair",
        "email": "priya@acme.sg",
        "department": "Engineering",
        "employment_type": "full_time",
        "nationality": "PR",
        "salary": 7200,
        "start_date": "2022-01-10",
    },
    {
        "name": "Chen Wei Lin",
        "email": "weilin@acme.sg",
        "department": "Operations",
        "employment_type": "full_time",
        "nationality": "SC",
        "salary": 4800,
        "start_date": "2024-03-01",
    },
    {
        "name": "Sarah Lim",
        "email": "sarah.lim@acme.sg",
        "department": "HR",
        "employment_type": "full_time",
        "nationality": "SC",
        "salary": 5500,
        "start_date": "2023-09-01",
    },
    {
        "name": "Raj Kumar",
        "email": "raj@acme.sg",
        "department": "Sales",
        "employment_type": "full_time",
        "nationality": "EP",
        "salary": 8000,
        "start_date": "2024-07-01",
    },
    {
        "name": "Mei Ling Tan",
        "email": "meiling@acme.sg",
        "department": "Finance",
        "employment_type": "part_time",
        "nationality": "SC",
        "salary": 3200,
        "start_date": "2025-01-15",
    },
]


def seed():
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder
    import hr_advisory.models  # noqa: F401

    runtime = LocalRuntime()
    created = 0

    for emp in EMPLOYEES:
        existing = auth._find_user_by_email(emp["email"])
        if existing:
            print(f"  SKIP {emp['name']} — already exists")
            continue

        # Create user
        pw_hash = auth.hash_password("Employee123!")
        user = auth._create_user(
            email=emp["email"],
            name=emp["name"],
            password_hash=pw_hash,
            company_id=COMPANY_ID,
            role="employee",
        )
        user_id = user["id"]

        # Create employee record
        wf = WorkflowBuilder()
        wf.add_node(
            "EmployeeCreateNode",
            "create_emp",
            {
                "user_id": user_id,
                "company_id": COMPANY_ID,
                "department": emp["department"],
                "employment_type": emp["employment_type"],
                "nationality": emp.get("nationality", "SC"),
                "start_date": emp["start_date"],
                "is_active": True,
            },
        )
        results, _ = runtime.execute(wf.build())
        emp_result = results["create_emp"]

        # Get employee ID
        emp_id = emp_result.get("id")
        if emp_id is None:
            wf2 = WorkflowBuilder()
            wf2.add_node(
                "EmployeeListNode",
                "find",
                {
                    "filter": {"user_id": user_id, "company_id": COMPANY_ID},
                    "limit": 1,
                    "enable_cache": False,
                },
            )
            r2, _ = runtime.execute(wf2.build())
            recs = r2["find"].get("records", []) if isinstance(r2["find"], dict) else []
            emp_id = recs[0]["id"] if recs else None

        if emp_id:
            # Create salary component
            wf3 = WorkflowBuilder()
            wf3.add_node(
                "SalaryComponentCreateNode",
                "sal",
                {
                    "employee_id": emp_id,
                    "company_id": COMPANY_ID,
                    "component_type": "basic",
                    "name": "Basic Salary",
                    "amount": emp["salary"],
                    "is_active": True,
                },
            )
            runtime.execute(wf3.build())

            # Create leave balances
            try:
                from hr_advisory.api.routers.leave import ensure_leave_balances

                ensure_leave_balances(emp_id, COMPANY_ID)
            except Exception as e:
                print(f"  WARN leave: {e}")

        created += 1
        print(
            f"  OK {emp['name']} — user={user_id}, emp={emp_id}, ${emp['salary']}/mo, {emp['department']}"
        )

    print(f"\nDone: {created} employees created for company {COMPANY_ID}")


if __name__ == "__main__":
    seed()
