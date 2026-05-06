"""Shared helper functions for routers.

These functions are duplicated across 8+ routers. Import from here
instead of redefining locally.
"""

from fastapi import HTTPException

from hr_advisory.services import dataflow_crud

# Input length limits (shared defaults)
MAX_TEXT_LENGTH = 2000
MAX_NAME_LENGTH = 200


def _validate_text_length(value: str, field_name: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    """Validate text input does not exceed maximum length.

    Raises HTTPException 400 if the value is too long.
    Returns the value unchanged on success.
    """
    if value and len(value) > max_len:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {max_len} characters.",
        )
    return value


def _find_employee_for_user(user_id: int, company_id: int) -> dict | None:
    """Look up the Employee record for a given user_id and company_id.

    Returns the employee dict or None if not found.
    """
    records = dataflow_crud.list_records(
        "Employee",
        {"user_id": user_id, "company_id": company_id},
        limit=1,
    )
    return records[0] if records else None


def _resolve_employee_names(
    employee_ids: set[int], company_id: int
) -> dict[int, str]:
    """Bulk-resolve employee_id → User.name for the given employee IDs.

    Employee has no name column; the canonical display name lives on the
    linked User row. Returns a dict keyed by employee_id, missing entries
    map to "" so callers can fall back gracefully.
    """
    if not employee_ids:
        return {}
    employees = dataflow_crud.list_records(
        "Employee", {"company_id": company_id}
    )
    uid_to_eids: dict[int, list[int]] = {}
    for emp in employees:
        eid = emp.get("id")
        if eid not in employee_ids:
            continue
        uid = emp.get("user_id")
        if uid:
            uid_to_eids.setdefault(uid, []).append(eid)
    if not uid_to_eids:
        return {}
    name_map: dict[int, str] = {}
    users = dataflow_crud.list_records("User", {"company_id": company_id})
    for user in users:
        uid = user.get("id")
        if uid in uid_to_eids:
            name = user.get("name", "")
            for eid in uid_to_eids[uid]:
                name_map[eid] = name
    return name_map


def _resolve_user_names(
    user_ids: set[int], company_id: int
) -> dict[int, str]:
    """Bulk-resolve user_id → User.name for the given user IDs.

    Used for actor / created_by / approved_by columns whose value is a
    raw User.id (not an Employee.id). Returns "" for missing entries.
    """
    if not user_ids:
        return {}
    users = dataflow_crud.list_records("User", {"company_id": company_id})
    return {
        u.get("id"): u.get("name", "")
        for u in users
        if u.get("id") in user_ids
    }
