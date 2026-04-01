"""Statutory floor check service for company policies.

Compares company leave policy text against Singapore Employment Act
statutory minimums using regex-based value extraction. This is a
best-effort extraction — it will never block policy uploads, only
produce warnings.

Statutory references (as at 1 January 2026):
- Annual leave: 7 days minimum for first year of service (EA s.88A)
- Sick leave: 14 days outpatient minimum (EA s.89, after 6 months)
- Hospitalisation leave: 60 days total entitlement (EA s.89, after 6 months)

Company Policy feature — statutory compliance warnings.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Statutory minimums (Singapore Employment Act)
# ---------------------------------------------------------------------------

_STATUTORY_FLOORS: dict[str, dict] = {
    "annual_leave": {
        "statutory_minimum": 7,
        "act_reference": "Employment Act s.88A",
        "description": "annual leave for the first year of service",
    },
    "sick_leave": {
        "statutory_minimum": 14,
        "act_reference": "Employment Act s.89",
        "description": "outpatient sick leave (after 6 months of service)",
    },
    "hospitalisation_leave": {
        "statutory_minimum": 60,
        "act_reference": "Employment Act s.89",
        "description": "hospitalisation leave (after 6 months of service)",
    },
}

# ---------------------------------------------------------------------------
# Regex patterns for extracting numeric values near leave keywords.
#
# Strategy: for each leave type, try multiple patterns from most specific
# to least specific.  The first match wins.  All patterns are
# case-insensitive.
# ---------------------------------------------------------------------------

# Pattern helper: a number (integer) followed by optional whitespace and
# "day(s)" or "working day(s)".
_DAYS_NUM = r"(\d+)\s*(?:working\s*)?days?"

# Annual leave patterns
_ANNUAL_LEAVE_PATTERNS: list[re.Pattern[str]] = [
    # "10 days of annual leave" / "10 days annual leave" / "10 days AL"
    re.compile(
        r"(\d+)\s*(?:working\s*)?days?\s*(?:of\s*)?(?:annual\s*leave|AL)\b",
        re.IGNORECASE,
    ),
    # "annual leave: 10 days" / "annual leave entitlement: 10 days"
    re.compile(
        r"annual\s*leave\s*(?:entitlement)?\s*[:\-]\s*(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE,
    ),
    # "annual leave ... 10 days" (within a reasonable window)
    re.compile(
        r"annual\s*leave\b.{0,40}?(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE | re.DOTALL,
    ),
]

# Sick leave patterns (includes "medical leave" and "outpatient" synonyms)
_SICK_LEAVE_PATTERNS: list[re.Pattern[str]] = [
    # "10 days of sick leave" / "10 days sick leave"
    re.compile(
        r"(\d+)\s*(?:working\s*)?days?\s*(?:of\s*)?(?:(?:outpatient\s*)?sick\s*leave|medical\s*leave)\b",
        re.IGNORECASE,
    ),
    # "sick leave: 10 days"
    re.compile(
        r"(?:outpatient\s*)?(?:sick|medical)\s*leave\s*[:\-]\s*(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE,
    ),
    # "outpatient ... 10 days" (sick leave implied)
    re.compile(
        r"outpatient\b.{0,40}?(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE | re.DOTALL,
    ),
    # "sick leave ... 10 days" (within a reasonable window)
    re.compile(
        r"(?:sick|medical)\s*leave\b.{0,40}?(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE | re.DOTALL,
    ),
]

# Hospitalisation leave patterns
_HOSPITALISATION_LEAVE_PATTERNS: list[re.Pattern[str]] = [
    # "30 days hospitalisation leave"
    re.compile(
        r"(\d+)\s*(?:working\s*)?days?\s*(?:of\s*)?hospitali[sz]ation\s*leave\b",
        re.IGNORECASE,
    ),
    # "hospitalisation leave: 30 days"
    re.compile(
        r"hospitali[sz]ation\s*leave\s*[:\-]\s*(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE,
    ),
    # "hospitalisation leave ... 30 days"
    re.compile(
        r"hospitali[sz]ation\s*leave\b.{0,40}?(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE | re.DOTALL,
    ),
    # "hospitalisation ... 30 days" (leave implied)
    re.compile(
        r"hospitali[sz]ation\b.{0,40}?(\d+)\s*(?:working\s*)?days?",
        re.IGNORECASE | re.DOTALL,
    ),
]

_LEAVE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "annual_leave": _ANNUAL_LEAVE_PATTERNS,
    "sick_leave": _SICK_LEAVE_PATTERNS,
    "hospitalisation_leave": _HOSPITALISATION_LEAVE_PATTERNS,
}


# ---------------------------------------------------------------------------
# Value extraction
# ---------------------------------------------------------------------------


def _extract_days(
    text: str,
    patterns: list[re.Pattern[str]],
) -> int | None:
    """Try each pattern in order and return the first captured integer.

    Returns ``None`` if no pattern matches.
    """
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _compare_value(
    field: str,
    company_value: int | None,
    statutory_minimum: int,
    act_reference: str,
    description: str,
) -> dict:
    """Build a single finding dict comparing company value to statutory floor."""
    if company_value is None:
        return {
            "field": field,
            "company_value": None,
            "statutory_minimum": statutory_minimum,
            "status": "not_detected",
            "message": (
                f"Could not detect a numeric value for {description} in the "
                f"policy text. The statutory minimum under the {act_reference} "
                f"is {statutory_minimum} days. Please verify manually."
            ),
        }

    if company_value < statutory_minimum:
        return {
            "field": field,
            "company_value": company_value,
            "statutory_minimum": statutory_minimum,
            "status": "below_minimum",
            "message": (
                f"Your policy states {company_value} days {description}. "
                f"The statutory minimum under the {act_reference} is "
                f"{statutory_minimum} days for the first year of service."
            ),
        }

    if company_value == statutory_minimum:
        return {
            "field": field,
            "company_value": company_value,
            "statutory_minimum": statutory_minimum,
            "status": "meets_minimum",
            "message": (
                f"Your policy states {company_value} days {description}, "
                f"which meets the statutory minimum under the {act_reference}."
            ),
        }

    # company_value > statutory_minimum
    return {
        "field": field,
        "company_value": company_value,
        "statutory_minimum": statutory_minimum,
        "status": "above_minimum",
        "message": (
            f"Your policy states {company_value} days {description}, "
            f"which exceeds the statutory minimum of {statutory_minimum} "
            f"days under the {act_reference}."
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_policy_against_statutory_floor(
    policy_content: str,
    category: str,
) -> list[dict]:
    """Check a company policy's leave entitlements against statutory minimums.

    For v1, only processes ``category == "leave_absence"``.  For all other
    categories, returns an empty list immediately.

    Args:
        policy_content: The plain-text content of the policy document.
        category: The policy category (e.g. ``"leave_absence"``).

    Returns:
        A list of finding dicts, one per leave type checked.  Each dict
        contains ``field``, ``company_value``, ``statutory_minimum``,
        ``status``, and ``message`` keys.
    """
    if category != "leave_absence":
        return []

    # Defensive: treat None content as empty string
    if policy_content is None:
        policy_content = ""

    findings: list[dict] = []

    for field, floor_info in _STATUTORY_FLOORS.items():
        patterns = _LEAVE_PATTERNS[field]
        company_value = _extract_days(policy_content, patterns)

        finding = _compare_value(
            field=field,
            company_value=company_value,
            statutory_minimum=floor_info["statutory_minimum"],
            act_reference=floor_info["act_reference"],
            description=floor_info["description"],
        )
        findings.append(finding)

        if company_value is not None and finding["status"] == "below_minimum":
            logger.warning(
                "Statutory floor violation detected: field=%s, "
                "company_value=%d, statutory_minimum=%d, category=%s",
                field,
                company_value,
                floor_info["statutory_minimum"],
                category,
            )

    return findings
