"""Abuse prevention and guardrails for the advisory platform.

Provides:
- Query screening for attempts to circumvent employment law
- Mandatory escalation criteria
- Content filtering for TAFEP compliance
- Rate limiting helpers
- Logging of flagged queries for review
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ScreeningResult(str, Enum):
    """Result of query screening."""

    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    ESCALATE = "escalate"


class EscalationReason(str, Enum):
    """Reason for mandatory escalation to human specialist."""

    ACTIVE_LITIGATION = "active_litigation"
    CRIMINAL_LIABILITY = "criminal_liability"
    LOW_CONFIDENCE = "low_confidence"
    CIRCUMVENTION_ATTEMPT = "circumvention_attempt"
    DISCRIMINATION_ALLEGATION = "discrimination_allegation"
    MULTI_JURISDICTION = "multi_jurisdiction"


@dataclass(frozen=True)
class ScreeningOutput:
    """Output from the query screening pipeline."""

    result: ScreeningResult
    reason: str
    matched_patterns: list[str]
    escalation_reason: Optional[EscalationReason] = None
    alternative_guidance: str = ""


@dataclass
class FlaggedQuery:
    """A query flagged for admin review."""

    id: str
    query: str
    screening_result: ScreeningResult
    reason: str
    user_id: Optional[str]
    timestamp: datetime
    reviewed: bool = False
    reviewer_notes: str = ""


# ── Pattern definitions ──────────────────────────────────────

# Patterns that indicate attempts to circumvent employment law
_CIRCUMVENTION_PATTERNS: list[tuple[str, str]] = [
    (
        r"(?i)avoid\s+(paying?\s+)?cpf",
        "Attempting to avoid CPF contributions is illegal under the CPF Act.",
    ),
    (
        r"(?i)(under.?pay|pay\s+less\s+than|below)\s+(pwm|progressive\s+wage)",
        "Paying below the Progressive Wage Model minimum is a violation of the Employment Act.",
    ),
    (
        r"(?i)illegal\s+deduct(ion)?s?\s+(from\s+)?salary",
        "Unauthorized salary deductions violate the Employment Act s27.",
    ),
    (
        r"(?i)(not\s+pay|skip|avoid)\s+(overtime|ot\s+pay)",
        "Failure to pay overtime to eligible employees violates EA Part IV.",
    ),
    (
        r"(?i)(fake|forge|falsify)\s+(employment|contract|payslip|ket|record)",
        "Falsifying employment records is a criminal offence.",
    ),
    (
        r"(?i)(hire|employ)\s+(illegal|undocumented|without\s+permit)",
        "Employing foreign workers without valid work passes violates EFMA.",
    ),
    (
        r"(?i)avoid\s+(providing?\s+)?(ket|payslip|key\s+employment\s+terms)",
        "Failing to issue KETs or payslips violates EA s95A and s88A.",
    ),
    (
        r"(?i)(terminate|fire|dismiss).{0,30}(pregnan|maternity|paternity)",
        "Dismissal related to pregnancy/maternity is wrongful dismissal.",
    ),
    (
        r"(?i)(force|make)\s+(employee|staff|worker)\s+(to\s+)?(resign|quit)",
        "Constructive dismissal is treated as wrongful dismissal.",
    ),
    (
        r"(?i)(classify|treat)\s+as\s+(freelancer|contractor).{0,30}(avoid|escape)",
        "Misclassifying employees as contractors to avoid obligations violates employment law.",
    ),
]

# Patterns requiring mandatory escalation
_ESCALATION_PATTERNS: list[tuple[str, EscalationReason, str]] = [
    (
        r"(?i)(lawsuit|litigation|su(ed|ing)|court\s+case|legal\s+proceedings|tadm\s+claim|wrongful\s+dismissal|unfair\s+dismissal|mediation\s+claim|ect\s+claim)",
        EscalationReason.ACTIVE_LITIGATION,
        "This query involves active or potential litigation. Please consult an employment law specialist.",
    ),
    (
        r"(?i)(criminal|police\s+report|investigation|fraud|embezzlement)",
        EscalationReason.CRIMINAL_LIABILITY,
        "This query involves potential criminal liability. Please consult a legal professional immediately.",
    ),
    (
        r"(?i)(discriminat(e|ion)|harass(ment)?|racial|sexual\s+harassment)",
        EscalationReason.DISCRIMINATION_ALLEGATION,
        "Discrimination and harassment cases require careful handling. We recommend consulting a specialist.",
    ),
    (
        r"(?i)(cross.?border|overseas|foreign\s+jurisdiction|international\s+employment)",
        EscalationReason.MULTI_JURISDICTION,
        "Multi-jurisdiction employment matters require specialist legal advice.",
    ),
]

# Content filter patterns (ensure responses don't contain discriminatory advice)
_CONTENT_FILTER_PATTERNS: list[tuple[str, str]] = [
    (
        r"(?i)(hire|prefer|only\s+accept)\s+(chinese|malay|indian|caucasian|male|female)",
        "Response contains discriminatory hiring advice that violates TAFEP guidelines.",
    ),
    (
        r"(?i)(age\s+limit|too\s+old|retire\s+age|force\s+retire)",
        "Response may contain age-discriminatory advice.",
    ),
    (
        r"(?i)(don'?t\s+hire|reject)\s+(pregnan|disable|handicap)",
        "Response contains discriminatory guidance violating the Workplace Fairness Act.",
    ),
]

# ── In-memory store for flagged queries ──────────────────────

_flagged_queries: list[FlaggedQuery] = []


# ── Screening functions ──────────────────────────────────────


def screen_query(query: str, user_id: Optional[str] = None) -> ScreeningOutput:
    """Screen a user query for circumvention attempts and mandatory escalation triggers.

    Returns a ScreeningOutput indicating whether to PASS, WARN, BLOCK, or ESCALATE.
    """
    matched_patterns: list[str] = []

    # Check escalation patterns first (higher priority)
    for pattern, reason, message in _ESCALATION_PATTERNS:
        if re.search(pattern, query):
            matched_patterns.append(pattern)
            output = ScreeningOutput(
                result=ScreeningResult.ESCALATE,
                reason=message,
                matched_patterns=matched_patterns,
                escalation_reason=reason,
            )
            _log_flagged_query(query, output, user_id)
            return output

    # Check circumvention patterns
    for pattern, message in _CIRCUMVENTION_PATTERNS:
        if re.search(pattern, query):
            matched_patterns.append(pattern)
            output = ScreeningOutput(
                result=ScreeningResult.BLOCK,
                reason=message,
                matched_patterns=matched_patterns,
                alternative_guidance=(
                    "Instead of seeking ways to circumvent employment regulations, "
                    "we can help you understand your obligations and find compliant "
                    "approaches that work for your business."
                ),
            )
            _log_flagged_query(query, output, user_id)
            return output

    return ScreeningOutput(
        result=ScreeningResult.PASS,
        reason="Query passed screening.",
        matched_patterns=[],
    )


def screen_response(response_text: str) -> ScreeningOutput:
    """Screen an AI-generated response for discriminatory or non-compliant content."""
    matched_patterns: list[str] = []

    for pattern, _message in _CONTENT_FILTER_PATTERNS:
        if re.search(pattern, response_text):
            matched_patterns.append(pattern)

    if matched_patterns:
        return ScreeningOutput(
            result=ScreeningResult.BLOCK,
            reason="Response contains content that may violate fair employment guidelines.",
            matched_patterns=matched_patterns,
        )

    return ScreeningOutput(
        result=ScreeningResult.PASS,
        reason="Response passed content filter.",
        matched_patterns=[],
    )


def check_confidence_escalation(confidence_score: float) -> Optional[ScreeningOutput]:
    """Check if low confidence requires mandatory escalation."""
    if confidence_score < 0.5:
        return ScreeningOutput(
            result=ScreeningResult.ESCALATE,
            reason=(
                "The AI confidence for this query is below the threshold. "
                "For accuracy, please consult an employment law specialist."
            ),
            matched_patterns=[],
            escalation_reason=EscalationReason.LOW_CONFIDENCE,
        )
    return None


# ── Flagging and review ──────────────────────────────────────


def _log_flagged_query(
    query: str,
    output: ScreeningOutput,
    user_id: Optional[str],
) -> None:
    """Log a flagged query for admin review."""
    import hashlib

    query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]
    _flagged_queries.append(
        FlaggedQuery(
            id=f"flag-{query_hash}",
            query=query,
            screening_result=output.result,
            reason=output.reason,
            user_id=user_id,
            timestamp=datetime.now(),
        )
    )


def get_flagged_queries(reviewed: Optional[bool] = None) -> list[FlaggedQuery]:
    """Get flagged queries, optionally filtered by review status."""
    if reviewed is None:
        return list(_flagged_queries)
    return [q for q in _flagged_queries if q.reviewed == reviewed]


def review_flagged_query(query_id: str, notes: str = "") -> Optional[FlaggedQuery]:
    """Mark a flagged query as reviewed."""
    for q in _flagged_queries:
        if q.id == query_id:
            q.reviewed = True
            q.reviewer_notes = notes
            return q
    return None


# ── Rate limiting helpers ────────────────────────────────────

# Simple in-memory rate limiter (production: Redis)
_request_counts: dict[str, list[datetime]] = {}
_WINDOW_SECONDS = 60
_MAX_REQUESTS_PER_WINDOW = 30


def check_rate_limit(user_id: str) -> bool:
    """Check if a user has exceeded the rate limit.

    Returns True if the request should be ALLOWED, False if rate-limited.
    """
    now = datetime.now()
    if user_id not in _request_counts:
        _request_counts[user_id] = []

    # Clean old entries
    _request_counts[user_id] = [
        t for t in _request_counts[user_id] if (now - t).total_seconds() < _WINDOW_SECONDS
    ]

    if len(_request_counts[user_id]) >= _MAX_REQUESTS_PER_WINDOW:
        return False

    _request_counts[user_id].append(now)
    return True
