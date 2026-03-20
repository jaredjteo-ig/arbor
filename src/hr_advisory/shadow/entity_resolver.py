# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Entity resolver for the Shadow Agent.

Maps LLM-extracted entity names to API parameter names using per-module
mappings, and resolves relative date expressions (e.g. "Monday", "tomorrow",
"next week") into YYYY-MM-DD format.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "detect_missing_required",
    "resolve_entities",
]

# ── Per-module entity name mappings ──────────────────────────
# Maps informal entity names (as extracted by the LLM) to the
# actual API parameter names expected by each module's endpoints.

_MODULE_MAPPINGS: dict[str, dict[str, str]] = {
    "employees": {
        "name": "full_name",
        "salary": "basic_salary",
        "start": "date_of_joining",
        "start_date": "date_of_joining",
        "department": "department_name",
        "role": "designation",
    },
    "leave": {
        "type": "leave_type_id",
        "days": "duration",
        "reason": "remarks",
    },
    "payroll": {
        "month": "pay_period",
    },
    "attendance": {},
}

# ── Day-of-week lookup ───────────────────────────────────────

_DAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Regex to match ISO date format (YYYY-MM-DD)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _resolve_date(value: Any) -> Any:
    """Resolve relative date expressions to YYYY-MM-DD strings.

    Handles:
    - "today" -> today's date
    - "tomorrow" -> tomorrow's date
    - "next week" -> next Monday
    - Day names ("Monday", "Friday") -> next occurrence of that day
    - "next Monday", "next Friday" -> next occurrence of that day
    - ISO dates (YYYY-MM-DD) -> pass through unchanged
    - Non-string values -> pass through unchanged

    Args:
        value: The value to resolve. Only strings are processed.

    Returns:
        The resolved value. Dates are returned as YYYY-MM-DD strings.
        Non-date strings and non-string values pass through unchanged.
    """
    if not isinstance(value, str):
        return value

    normalized = value.strip().lower()

    # ISO date pass-through
    if _ISO_DATE_RE.match(normalized):
        return value

    today = date.today()

    # Simple relative dates
    if normalized == "today":
        return today.isoformat()

    if normalized == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    if normalized == "next week":
        # Next Monday
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        return (today + timedelta(days=days_until_monday)).isoformat()

    # "next <day>" pattern
    next_day_match = re.match(r"^next\s+(\w+)$", normalized)
    if next_day_match:
        day_name = next_day_match.group(1)
        if day_name in _DAY_NAMES:
            target_weekday = _DAY_NAMES[day_name]
            days_ahead = (target_weekday - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).isoformat()

    # Bare day name (e.g. "Monday", "Friday")
    if normalized in _DAY_NAMES:
        target_weekday = _DAY_NAMES[normalized]
        days_ahead = (target_weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat()

    # Not a recognized date expression — pass through
    return value


def resolve_entities(
    module: str,
    action: str,
    entities: dict[str, Any],
    tool_params: list[str],
) -> tuple[dict[str, Any], list[str]]:
    """Map extracted entity names to API parameter names and resolve dates.

    Uses per-module mappings to translate informal entity names (e.g. "name")
    to the actual API parameter names (e.g. "full_name"). Also resolves
    relative date expressions in entity values.

    Args:
        module: The target module (e.g. "employees", "leave").
        action: The target action (e.g. "create", "apply").
        entities: The raw entities extracted by the intent classifier.
        tool_params: The list of parameter names expected by the tool.

    Returns:
        (resolved_params, warnings) tuple. resolved_params is a dict of
        API-ready parameters. warnings is a list of strings describing
        entities that could not be mapped to any known parameter.
    """
    mappings = _MODULE_MAPPINGS.get(module, {})
    resolved: dict[str, Any] = {}
    warnings: list[str] = []
    tool_params_set = set(tool_params)

    for key, value in entities.items():
        # Resolve relative dates in values
        resolved_value = _resolve_date(value)

        # Try mapping the entity name
        if key in mappings:
            mapped_name = mappings[key]
            resolved[mapped_name] = resolved_value
            logger.debug(
                "Entity mapped: %s.%s — %r -> %r",
                module,
                action,
                key,
                mapped_name,
            )
        elif key in tool_params_set:
            # Entity name already matches a tool param — pass through
            resolved[key] = resolved_value
        else:
            # Check if the mapped name from any module mapping matches a tool param
            # If not, it's an unmappable entity
            warnings.append(
                f"Entity '{key}' could not be mapped to a known parameter for "
                f"{module}.{action}. Available params: {', '.join(tool_params) if tool_params else 'none'}"
            )
            logger.warning(
                "Unmappable entity for %s.%s: %r (value=%r)",
                module,
                action,
                key,
                resolved_value,
            )

    return resolved, warnings


def detect_missing_required(
    tool_params: list[str],
    resolved: dict[str, Any],
) -> list[str]:
    """Check which required parameters are still missing after entity resolution.

    Args:
        tool_params: The list of required parameter names from the tool definition.
        resolved: The resolved parameters after entity mapping.

    Returns:
        A list of parameter names that are required but not present
        in the resolved dict.
    """
    missing: list[str] = []
    for param in tool_params:
        if param not in resolved:
            missing.append(param)
    return missing
