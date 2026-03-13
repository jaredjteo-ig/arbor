"""Input Validation and Security Hardening (T059).

Provides:
- Input sanitisation (XSS prevention)
- Email and UEN format validation
- Query length limits
- Rate limiting configuration
- CORS and security headers configuration
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting configuration per endpoint category."""

    category: str
    requests_per_minute: int
    requests_per_hour: int
    burst_limit: int


# ── Rate limit configurations ───────────────────────────────

RATE_LIMITS: dict[str, RateLimitConfig] = {
    "advisory": RateLimitConfig(
        category="advisory",
        requests_per_minute=10,
        requests_per_hour=100,
        burst_limit=3,
    ),
    "calculator": RateLimitConfig(
        category="calculator",
        requests_per_minute=30,
        requests_per_hour=500,
        burst_limit=10,
    ),
    "auth": RateLimitConfig(
        category="auth",
        requests_per_minute=5,
        requests_per_hour=20,
        burst_limit=2,
    ),
    "admin": RateLimitConfig(
        category="admin",
        requests_per_minute=20,
        requests_per_hour=200,
        burst_limit=5,
    ),
    "document": RateLimitConfig(
        category="document",
        requests_per_minute=10,
        requests_per_hour=100,
        burst_limit=3,
    ),
}

# ── CORS configuration ──────────────────────────────────────

CORS_CONFIG = {
    "allow_origins": [
        "http://localhost:3000",  # React dev
        "http://localhost:5173",  # Vite dev
    ],
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "X-Request-ID"],
    "allow_credentials": True,
    "max_age": 3600,
}

# ── Security headers ────────────────────────────────────────

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",  # Modern browsers use CSP instead
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


# ── Input validation ─────────────────────────────────────────

# Maximum query length (characters)
MAX_QUERY_LENGTH = 2000
MIN_QUERY_LENGTH = 3

# UEN format: 8-10 characters, alphanumeric, ending with a letter
_UEN_PATTERN = re.compile(r"^[0-9A-Za-z]{8,10}[A-Za-z]$")

# Email format (simplified but sufficient)
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def sanitise_input(text: str) -> str:
    """Sanitise user input to prevent XSS and injection.

    - HTML-escapes special characters
    - Strips null bytes
    - Limits to MAX_QUERY_LENGTH
    """
    # Remove null bytes
    cleaned = text.replace("\x00", "")
    # HTML escape
    cleaned = html.escape(cleaned, quote=True)
    # Truncate
    return cleaned[:MAX_QUERY_LENGTH]


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email format.

    Returns (is_valid, error_message).
    """
    if not email:
        return False, "Email is required"
    if len(email) > 254:
        return False, "Email address is too long"
    if not _EMAIL_PATTERN.match(email):
        return False, "Invalid email format"
    return True, ""


def validate_uen(uen: str) -> tuple[bool, str]:
    """Validate Singapore UEN format.

    Returns (is_valid, error_message).
    """
    if not uen:
        return False, "UEN is required"
    cleaned = uen.strip().upper()
    if not _UEN_PATTERN.match(cleaned):
        return (
            False,
            "Invalid UEN format (expected 9-10 alphanumeric characters ending with a letter)",
        )
    return True, ""


def validate_query_length(query: str) -> tuple[bool, str]:
    """Validate advisory query length.

    Returns (is_valid, error_message).
    """
    if len(query) < MIN_QUERY_LENGTH:
        return False, f"Query must be at least {MIN_QUERY_LENGTH} characters"
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query must not exceed {MAX_QUERY_LENGTH} characters"
    return True, ""
