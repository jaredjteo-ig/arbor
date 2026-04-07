"""Build onboarding context for advisory chat injection.

When an employee has an active onboarding assignment, this module fetches
the template content (modules, steps, policies, benefits, contacts, etc.)
and formats it as a text block that the advisory engine can use to answer
company-specific onboarding questions.

The context is cached per employee with a 10-minute TTL since onboarding
content changes infrequently.
"""

from __future__ import annotations

import json
import logging
import time
from collections import OrderedDict
from typing import Any

from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache: employee_id -> (text, expiry_timestamp)
# Bounded to prevent OOM in long-running processes.
# ---------------------------------------------------------------------------

_MAX_CACHE_ENTRIES = 2000
_CACHE_TTL_SECONDS = 600  # 10 minutes
_cache: OrderedDict[tuple[int, int], tuple[str, float]] = OrderedDict()


def _cache_get(employee_id: int, company_id: int) -> str | None:
    """Return cached onboarding context if still valid, else None."""
    key = (employee_id, company_id)
    entry = _cache.get(key)
    if entry is None:
        return None
    text, expiry = entry
    if time.monotonic() > expiry:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return text


def _cache_set(employee_id: int, company_id: int, text: str) -> None:
    """Store onboarding context in cache with TTL."""
    key = (employee_id, company_id)
    _cache[key] = (text, time.monotonic() + _CACHE_TTL_SECONDS)
    _cache.move_to_end(key)
    while len(_cache) > _MAX_CACHE_ENTRIES:
        _cache.popitem(last=False)


def invalidate_cache(employee_id: int | None = None, company_id: int | None = None) -> None:
    """Invalidate cached onboarding context.

    If both employee_id and company_id are provided, only that entry is removed.
    If only employee_id, removes all entries for that employee.
    Otherwise the entire cache is cleared.
    """
    if employee_id is not None and company_id is not None:
        _cache.pop((employee_id, company_id), None)
    elif employee_id is not None:
        keys_to_remove = [k for k in _cache if k[0] == employee_id]
        for k in keys_to_remove:
            _cache.pop(k, None)
    else:
        _cache.clear()


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def get_onboarding_context(
    user_id: int,
    company_id: int,
) -> str:
    """Fetch onboarding context for an employee if they have an active assignment.

    Returns a formatted text block suitable for injection into the advisory
    system prompt. Returns an empty string if the employee has no active
    onboarding.

    Args:
        user_id: The authenticated user's ID.
        company_id: The company ID for tenant isolation.

    Returns:
        A text block describing the employee's onboarding content, or "".
    """
    # Find the employee record for this user
    try:
        employees = dataflow_crud.list_records(
            "Employee",
            {"user_id": user_id, "company_id": company_id},
            limit=1,
        )
    except Exception:
        logger.debug("Could not look up employee for user_id=%s", user_id)
        return ""

    if not employees:
        return ""

    employee = employees[0]
    employee_id = employee.get("id")
    if employee_id is None:
        return ""

    # Check cache first
    cached = _cache_get(employee_id, company_id)
    if cached is not None:
        return cached

    # Look for an active onboarding assignment
    try:
        assignments = dataflow_crud.list_records(
            "OnboardingAssignment",
            {"employee_id": employee_id, "company_id": company_id, "status": "in_progress"},
            limit=1,
        )
    except Exception:
        logger.debug("Could not look up onboarding assignment for employee_id=%s", employee_id)
        return ""

    if not assignments:
        # Cache the negative result too (avoids repeated DB lookups)
        _cache_set(employee_id, company_id, "")
        return ""

    assignment = assignments[0]
    template_id = assignment.get("template_id")
    if template_id is None:
        _cache_set(employee_id, company_id, "")
        return ""

    # Build the context
    context = _build_onboarding_text(assignment, template_id, company_id, employee)
    _cache_set(employee_id, company_id, context)
    return context


def _build_onboarding_text(
    assignment: dict[str, Any],
    template_id: int,
    company_id: int,
    employee: dict[str, Any],
) -> str:
    """Assemble onboarding content into a readable text block for the LLM."""
    sections: list[str] = []

    # -- Template info --
    template = dataflow_crud.read("OnboardingTemplate", template_id)
    if template and template.get("company_id") != company_id:
        template = None  # tenant isolation: template must belong to same company
    template_name = template.get("name", "Onboarding") if template else "Onboarding"
    sections.append(
        f"EMPLOYEE ONBOARDING PROGRAM: {template_name}\n"
        f"Employee: {employee.get('name', 'Unknown')}\n"
        f"Status: {assignment.get('status', 'in_progress')}\n"
        f"Progress: {assignment.get('completion_percentage', 0):.0f}%"
    )

    # -- Buddy info --
    buddy_id = assignment.get("buddy_employee_id")
    if buddy_id:
        buddy = dataflow_crud.read("Employee", buddy_id)
        if buddy and buddy.get("company_id") == company_id:
            buddy_info = f"Onboarding buddy: {buddy.get('name', 'A colleague')}"
            if buddy.get("designation"):
                buddy_info += f" — {buddy['designation']}"
            if buddy.get("department"):
                buddy_info += f", {buddy['department']}"
            sections.append(buddy_info)

    # -- Modules and steps --
    try:
        modules = dataflow_crud.list_records(
            "OnboardingModule",
            {"template_id": template_id, "company_id": company_id},
            limit=100,
        )
    except Exception:
        modules = []

    if modules:
        # Sort by sort_order
        modules.sort(key=lambda m: m.get("sort_order", 0))

        module_section = "ONBOARDING MODULES:"
        for mod in modules:
            mod_id = mod.get("id")
            mod_name = mod.get("name", "Untitled")
            mod_desc = mod.get("description", "")
            mod_phase = mod.get("phase", "")
            mandatory = "Required" if mod.get("is_mandatory") else "Optional"

            module_section += f"\n\n--- {mod_name} ({mod_phase}) [{mandatory}] ---"
            if mod_desc:
                module_section += f"\n{mod_desc}"

            # Fetch steps for this module
            if mod_id is not None:
                try:
                    steps = dataflow_crud.list_records(
                        "OnboardingStep",
                        {"module_id": mod_id},
                        limit=50,
                    )
                except Exception:
                    steps = []

                if steps:
                    steps.sort(key=lambda s: s.get("sort_order", 0))
                    for step in steps:
                        step_title = step.get("title", "Untitled")
                        step_body = step.get("body_content", "")
                        step_type = step.get("step_type", "content")

                        module_section += f"\n  - {step_title}"
                        if step_type == "checklist" and step.get("checklist_items"):
                            try:
                                items = json.loads(step["checklist_items"])
                                if isinstance(items, list):
                                    for item in items:
                                        if isinstance(item, str):
                                            module_section += f"\n    [ ] {item}"
                                        elif isinstance(item, dict):
                                            module_section += f"\n    [ ] {item.get('label', item.get('text', str(item)))}"
                            except (json.JSONDecodeError, TypeError):
                                pass
                        if step_body:
                            # Truncate very long body content to keep context manageable
                            body_preview = step_body[:800]
                            if len(step_body) > 800:
                                body_preview += "..."
                            module_section += f"\n    {body_preview}"

        sections.append(module_section)

    # -- Due date --
    due_date = assignment.get("due_date")
    if due_date:
        sections.append(f"Onboarding due date: {due_date}")

    # Assemble final context block
    if not any(s for s in sections if "ONBOARDING MODULES:" in s):
        # No real content to inject
        return ""

    return "\n\n".join(sections)
