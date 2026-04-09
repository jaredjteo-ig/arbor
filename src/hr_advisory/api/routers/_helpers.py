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
