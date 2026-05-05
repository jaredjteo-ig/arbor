"""Regression test for T214 — pre-boarding tasks auto-created on assignment.

Covers two paths:

1. ``auto_assign_default_onboarding`` (used by the invitation-accept flow)
   creates per-employee ``PreboardingTaskInstance`` rows from the template-
   level rows (employee_id == 0) with ``deadline_date`` computed as
   ``employee.start_date + relative_days`` parsed from the task notes.

2. ``POST /onboarding/assign`` (manual HR assignment) follows the same
   path — template-level rows are copied to per-employee instances and the
   deadline is computed.

Bug:
    Previously the assignment endpoint did not copy template pre-boarding
    rows. New hires landed without their offer-letter / IT-setup tasks.

Fix:
    Both code paths copy template-level rows into per-employee instances
    and parse "X days before" / "X days relative" from the notes column to
    set the ``deadline_date``.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")
# DataFlow defaults pool_size=70 + max_overflow=35 (105 connections per worker),
# which exceeds Postgres max_connections=100 on a fresh local DB.
os.environ.setdefault("DATAFLOW_POOL_SIZE", "5")
os.environ.setdefault("DATAFLOW_POOL_MAX_OVERFLOW", "2")


@pytest.mark.regression
@pytest.mark.integration
def test_t214_auto_assign_creates_preboarding_tasks_with_deadline():
    """auto_assign_default_onboarding copies template tasks + calculates deadlines."""
    from hr_advisory.api.routers.onboarding import auto_assign_default_onboarding
    from hr_advisory.services import dataflow_crud
    from hr_advisory.services.auth_service import AuthService

    auth = AuthService()
    suffix = uuid.uuid4().hex[:8]

    company = dataflow_crud.create(
        "Company",
        {
            "name": f"PreboardingT214 {suffix}",
            "uen": f"P{suffix.upper()[:9]}",
            "sector": "Technology",
        },
    )
    company_id = company["id"]

    user = auth._create_user(
        email=f"emp_t214_{suffix}@example.com",
        name="Emp T214",
        password_hash=auth.hash_password("RegT214!Pass"),
        company_id=company_id,
        role="employee",
    )
    user_id = user["id"]

    start_date = (date.today() + timedelta(days=14)).isoformat()
    employee = dataflow_crud.create(
        "Employee",
        {
            "user_id": user_id,
            "company_id": company_id,
            "employment_type": "full_time",
            "start_date": start_date,
            "is_active": True,
            "designation": "Software Engineer",
            "confirmation_status": "on_probation",
        },
    )
    employee_id = employee["id"]

    # ── Default template + template-level pre-boarding tasks ────────────
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    template = dataflow_crud.create(
        "OnboardingTemplate",
        {
            "company_id": company_id,
            "name": f"Default T214 {suffix}",
            "description": "Default template",
            "is_default": True,
            "version": 1,
            "is_active": True,
            "created_by": 0,
            "created_at": now_naive,
            "updated_at": now_naive,
        },
    )
    template_id = template["id"]

    # Template-level tasks (employee_id == 0). Notes contain the relative-
    # days hint that the auto-assign code parses.
    pb_tasks = []
    for task_name, owner_role, rel_days in [
        ("Send offer letter", "hr", -14),
        ("Set up workstation", "it", -1),
        ("Send welcome email", "hr", -7),
    ]:
        rec = dataflow_crud.create(
            "PreboardingTaskInstance",
            {
                "company_id": company_id,
                "template_id": template_id,
                "employee_id": 0,
                "task_name": task_name,
                "owner_role": owner_role,
                "trigger": "Offer accepted",
                "status": "pending",
                "notes": f"Created {rel_days} days before start",
            },
        )
        pb_tasks.append(rec["id"])

    # ── Trigger the auto-assign code path ───────────────────────────────
    assignment = auto_assign_default_onboarding(
        employee_id=employee_id,
        company_id=company_id,
    )
    assert assignment is not None
    assignment_id = assignment.get("id")

    # ── Verify per-employee tasks were created with computed deadlines ──
    emp_tasks = dataflow_crud.list_records(
        "PreboardingTaskInstance",
        {"employee_id": employee_id, "template_id": template_id},
        cache_ttl=0,
    )
    assert len(emp_tasks) == 3, (
        f"Expected 3 per-employee pre-boarding tasks, got {len(emp_tasks)}"
    )

    task_by_name = {t["task_name"]: t for t in emp_tasks}
    assert set(task_by_name) == {"Send offer letter", "Set up workstation", "Send welcome email"}

    start_dt = datetime.fromisoformat(start_date)
    # Each task's deadline_date should be start_date + relative_days.
    for task_name, rel_days in [
        ("Send offer letter", -14),
        ("Set up workstation", -1),
        ("Send welcome email", -7),
    ]:
        task = task_by_name[task_name]
        assert task["status"] == "pending"
        assert task["deadline_date"], f"{task_name} missing deadline_date"
        deadline = datetime.fromisoformat(task["deadline_date"])
        expected = start_dt + timedelta(days=rel_days)
        # Allow for different date precision (date-only vs datetime).
        assert deadline.date() == expected.date(), (
            f"{task_name}: expected deadline {expected.date()}, got {deadline.date()}"
        )

    # ── Cleanup ─────────────────────────────────────────────────────────
    for t in emp_tasks:
        try:
            dataflow_crud.delete("PreboardingTaskInstance", t["id"])
        except Exception:
            pass
    for tid in pb_tasks:
        try:
            dataflow_crud.delete("PreboardingTaskInstance", tid)
        except Exception:
            pass
    # Step progress + assignment cleanup
    try:
        progress = dataflow_crud.list_records(
            "OnboardingStepProgress",
            {"assignment_id": assignment_id},
            cache_ttl=0,
        )
        for p in progress:
            try:
                dataflow_crud.delete("OnboardingStepProgress", p["id"])
            except Exception:
                pass
    except Exception:
        pass
    try:
        milestones = dataflow_crud.list_records(
            "OnboardingMilestone",
            {"assignment_id": assignment_id},
            cache_ttl=0,
        )
        for m in milestones:
            try:
                dataflow_crud.delete("OnboardingMilestone", m["id"])
            except Exception:
                pass
    except Exception:
        pass
    try:
        dataflow_crud.delete("OnboardingAssignment", assignment_id)
    except Exception:
        pass
    try:
        dataflow_crud.delete("OnboardingTemplate", template_id)
    except Exception:
        pass
    try:
        dataflow_crud.delete("Employee", employee_id)
    except Exception:
        pass
    try:
        dataflow_crud.delete("User", user_id)
    except Exception:
        pass
    try:
        dataflow_crud.delete("Company", company_id)
    except Exception:
        pass
