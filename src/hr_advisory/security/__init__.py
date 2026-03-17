"""Security infrastructure (T059).

Provides:
- PDPA compliance helpers
- Input validation and sanitisation
- Rate limiting configuration
- CORS and CSRF configuration
- Secret management helpers
- OWASP Top 10 compliance checks
- Field-level PII encryption (T191)
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
from hr_advisory.security.encryption import (
    encrypt_field,
    decrypt_field,
    mask_nric,
    mask_bank_account,
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
    "encrypt_field",
    "decrypt_field",
    "mask_nric",
    "mask_bank_account",
]
