"""PDPA Compliance Helpers (T059).

Personal Data Protection Act compliance for the Arbor platform:
- Data minimisation validation
- Consent recording and tracking
- Data retention policy enforcement
- Breach notification templates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ConsentPurpose(str, Enum):
    """Purpose for collecting personal data."""

    ADVISORY_SERVICE = "advisory_service"
    COMPANY_PROFILE = "company_profile"
    ANALYTICS = "analytics"
    NOTIFICATIONS = "notifications"
    MARKETING = "marketing"
    RECRUITMENT = "recruitment"


class DataCategory(str, Enum):
    """Category of personal data collected."""

    COMPANY_INFO = "company_info"  # UEN, company name, sector
    WORKFORCE_DATA = "workforce_data"  # headcounts, salary ranges
    ADVISORY_HISTORY = "advisory_history"  # queries and responses
    USER_CREDENTIALS = "user_credentials"  # email, hashed password
    USAGE_ANALYTICS = "usage_analytics"  # query patterns, feedback


@dataclass
class PdpaConsentRecord:
    """Record of user consent for data collection."""

    user_id: str
    purpose: ConsentPurpose
    granted: bool
    granted_at: datetime = field(default_factory=datetime.now)
    revoked_at: Optional[datetime] = None
    ip_address: str = ""
    consent_version: str = "1.0"


@dataclass
class DataRetentionPolicy:
    """Data retention policy per data category."""

    category: DataCategory
    retention_days: int
    description: str
    deletion_method: str  # "hard_delete", "anonymise", "archive"


# ── Retention policies ──────────────────────────────────────

RETENTION_POLICIES: dict[DataCategory, DataRetentionPolicy] = {
    DataCategory.COMPANY_INFO: DataRetentionPolicy(
        category=DataCategory.COMPANY_INFO,
        retention_days=365 * 3,  # 3 years after account closure
        description="Company registration data retained for 3 years post-closure",
        deletion_method="hard_delete",
    ),
    DataCategory.WORKFORCE_DATA: DataRetentionPolicy(
        category=DataCategory.WORKFORCE_DATA,
        retention_days=365 * 2,  # 2 years
        description="Workforce composition data retained for 2 years",
        deletion_method="anonymise",
    ),
    DataCategory.ADVISORY_HISTORY: DataRetentionPolicy(
        category=DataCategory.ADVISORY_HISTORY,
        retention_days=365,  # 1 year
        description="Advisory session history retained for 1 year",
        deletion_method="anonymise",
    ),
    DataCategory.USER_CREDENTIALS: DataRetentionPolicy(
        category=DataCategory.USER_CREDENTIALS,
        retention_days=30,  # 30 days after account closure
        description="Credentials deleted 30 days after account closure",
        deletion_method="hard_delete",
    ),
    DataCategory.USAGE_ANALYTICS: DataRetentionPolicy(
        category=DataCategory.USAGE_ANALYTICS,
        retention_days=365 * 2,  # 2 years (anonymised)
        description="Usage analytics anonymised and retained for 2 years",
        deletion_method="anonymise",
    ),
}


# ── In-memory stores ────────────────────────────────────────

_consent_records: list[PdpaConsentRecord] = []


# ── Public API ──────────────────────────────────────────────


def check_data_minimisation(
    data_fields: list[str],
    purpose: ConsentPurpose,
) -> list[str]:
    """Check if collected data fields are necessary for the stated purpose.

    Returns list of fields that may be unnecessary (over-collection).
    """
    # Fields necessary per purpose
    necessary_fields: dict[ConsentPurpose, set[str]] = {
        ConsentPurpose.ADVISORY_SERVICE: {
            "company_sector",
            "employee_count",
            "query_text",
        },
        ConsentPurpose.COMPANY_PROFILE: {
            "company_name",
            "uen",
            "sector",
            "employee_count",
            "headcount_local",
            "headcount_foreign",
        },
        ConsentPurpose.ANALYTICS: {
            "query_domain",
            "response_confidence",
            "feedback_rating",
        },
        ConsentPurpose.NOTIFICATIONS: {
            "email",
            "notification_preferences",
        },
        ConsentPurpose.MARKETING: {
            "email",
            "company_name",
        },
        ConsentPurpose.RECRUITMENT: {
            "name",
            "email",
            "phone",
            "resume_url",
            "nationality",
            "citizenship_status",
        },
    }

    needed = necessary_fields.get(purpose, set())
    unnecessary = [f for f in data_fields if f not in needed]
    return unnecessary


def record_consent(
    user_id: str,
    purpose: ConsentPurpose,
    granted: bool,
    ip_address: str = "",
) -> PdpaConsentRecord:
    """Record a consent decision."""
    record = PdpaConsentRecord(
        user_id=user_id,
        purpose=purpose,
        granted=granted,
        ip_address=ip_address,
    )
    _consent_records.append(record)
    return record


def check_retention_compliance(
    category: DataCategory,
    data_created_at: datetime,
) -> bool:
    """Check if data should still be retained per retention policy.

    Returns True if data is within retention period.
    """
    policy = RETENTION_POLICIES.get(category)
    if policy is None:
        return False  # no policy = should not retain

    from datetime import timedelta

    expiry = data_created_at + timedelta(days=policy.retention_days)
    return datetime.now() < expiry


def get_breach_notification_template(
    breach_description: str,
    data_categories_affected: list[DataCategory],
    estimated_affected_users: int,
) -> dict[str, str]:
    """Generate PDPA breach notification template.

    Under PDPA, organisations must notify PDPC within 3 calendar days
    of assessing that a data breach is notifiable.
    """
    categories_str = ", ".join(c.value for c in data_categories_affected)

    return {
        "to": "Personal Data Protection Commission (PDPC)",
        "subject": "Data Breach Notification — Arbor HR Advisory Platform",
        "body": (
            f"Dear PDPC,\n\n"
            f"We are writing to notify of a data breach as required under "
            f"the Personal Data Protection Act 2012.\n\n"
            f"Description: {breach_description}\n\n"
            f"Data categories affected: {categories_str}\n\n"
            f"Estimated number of affected individuals: {estimated_affected_users}\n\n"
            f"Remediation steps: [To be completed]\n\n"
            f"We are taking immediate steps to mitigate the impact and "
            f"prevent recurrence.\n\n"
            f"Contact: [DPO name and contact details]"
        ),
        "internal_note": (
            "PDPA Section 26D: Notify PDPC within 3 calendar days. "
            "Notify affected individuals if breach is likely to result "
            "in significant harm."
        ),
    }
