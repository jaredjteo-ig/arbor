"""Security infrastructure (T059).

Provides:
- PDPA compliance helpers
- Input validation and sanitisation
- Rate limiting configuration
- CORS and CSRF configuration
- Secret management helpers
- OWASP Top 10 compliance checks
"""

from hr_advisory.security.pdpa import (
    PdpaConsentRecord,
    DataRetentionPolicy,
    check_data_minimisation,
    record_consent,
    check_retention_compliance,
    get_breach_notification_template,
)
from hr_advisory.security.validation import (
    sanitise_input,
    validate_email,
    validate_uen,
    validate_query_length,
    RateLimitConfig,
    RATE_LIMITS,
)

__all__ = [
    "PdpaConsentRecord",
    "DataRetentionPolicy",
    "check_data_minimisation",
    "record_consent",
    "check_retention_compliance",
    "get_breach_notification_template",
    "sanitise_input",
    "validate_email",
    "validate_uen",
    "validate_query_length",
    "RateLimitConfig",
    "RATE_LIMITS",
]
