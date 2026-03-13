"""DataFlow models for companies, users, conversations, and advisory sessions.

These models handle the transactional side of the platform: who is asking,
what company context they're in, what conversations they've had, and
what advisory responses were generated.
"""

from datetime import datetime
from typing import Optional

from hr_advisory.models.database import db
from hr_advisory.models.enums import RiskTier


# ---------------------------------------------------------------------------
# Enums (string-based for DataFlow compatibility)
# ---------------------------------------------------------------------------


class UserRole:
    OWNER = "owner"
    HR_MANAGER = "hr_manager"
    CONSULTANT = "consultant"


class ContentUpdateStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentUrgency:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@db.model
class Company:
    """A Singapore SME company profile.

    Stores workforce composition used for provision applicability filtering.
    Multi-tenant enabled for consultant access to multiple clients.
    """

    name: str
    uen: Optional[str] = None
    sector: Optional[str] = None
    sub_sector: Optional[str] = None
    headcount_local: int = 0
    headcount_pr: int = 0
    headcount_ep: int = 0
    headcount_sp: int = 0
    headcount_wp: int = 0
    salary_ranges: Optional[dict] = None
    profile_completeness_score: float = 0.0
    is_active: bool = True

    __dataflow__ = {
        "multi_tenant": True,
        "indexes": [
            {"name": "idx_company_uen", "fields": ["uen"]},
            {"name": "idx_company_sector", "fields": ["sector"]},
        ],
    }


@db.model
class User:
    """A platform user linked to a company.

    Stores preferences (text size, notifications, language) as JSON.
    """

    email: str
    name: str
    company_id: Optional[int] = None
    role: str = UserRole.OWNER
    preferences: Optional[dict] = None
    password_hash: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_user_email", "fields": ["email"]},
            {"name": "idx_user_company", "fields": ["company_id"]},
        ],
    }


@db.model
class Conversation:
    """A conversation thread grouping related advisory sessions.

    Each conversation belongs to a user+company context and may
    contain multiple back-and-forth advisory exchanges.
    """

    user_id: int
    company_id: Optional[int] = None
    title: str = ""
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_conversation_user", "fields": ["user_id"]},
            {"name": "idx_conversation_company", "fields": ["company_id"]},
        ],
    }


@db.model
class AdvisorySession:
    """A single query-response exchange within a conversation.

    Stores the full audit trail: which provisions were cited,
    which agents were involved, confidence score, risk tier,
    trust lineage (EATP), and genesis record (COC).
    """

    conversation_id: int
    user_id: int
    company_id: Optional[int] = None
    query_text: str
    response_text: str = ""
    provisions_cited: Optional[dict] = None
    agents_involved: Optional[dict] = None
    confidence_score: float = 0.0
    risk_tier: str = RiskTier.GREEN.value
    trust_lineage: Optional[dict] = None
    genesis_record: Optional[dict] = None
    feedback_rating: Optional[str] = None
    feedback_text: Optional[str] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_session_conversation", "fields": ["conversation_id"]},
            {"name": "idx_session_user", "fields": ["user_id"]},
            {"name": "idx_session_company", "fields": ["company_id"]},
            {"name": "idx_session_risk_tier", "fields": ["risk_tier"]},
        ],
    }


@db.model
class ContentUpdate:
    """Tracks regulatory content changes (e.g. new MOM circular, CPF rate change).

    Used to alert companies about changes affecting them and to
    trigger knowledge base updates.
    """

    source_url: Optional[str] = None
    change_summary: str = ""
    affected_domains: Optional[dict] = None
    urgency: str = ContentUrgency.MEDIUM
    status: str = ContentUpdateStatus.DRAFT
    author_id: Optional[int] = None
    published_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_content_update_status", "fields": ["status"]},
            {"name": "idx_content_update_urgency", "fields": ["urgency"]},
        ],
    }


@db.model
class Template:
    """Reusable document templates linked to provisions.

    Examples: Employment contract template, FWA request form,
    performance review template.
    """

    name: str
    template_type: str = ""
    content: str = ""
    template_version: int = 1
    linked_provision_ids: Optional[dict] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_template_type", "fields": ["template_type"]},
        ],
    }
