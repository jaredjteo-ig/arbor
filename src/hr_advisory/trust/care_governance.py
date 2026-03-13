"""CARE Framework Governance Integration (T048).

Implements CARE principles:
- Human-on-the-Loop: humans validate all KB updates
- Dual Plane Model: Trust Plane (human) vs Execution Plane (AI)
- Expert validation workflow with SLAs and reviewer qualifications
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ReviewerQualification(str, Enum):
    """Required qualification level for reviewers."""

    IHRP_CERTIFIED = "ihrp_certified"
    EMPLOYMENT_LAWYER = "employment_lawyer"
    CPF_SPECIALIST = "cpf_specialist"
    TAX_SPECIALIST = "tax_specialist"
    WSH_SPECIALIST = "wsh_specialist"
    DOMAIN_EXPERT = "domain_expert"


class ContentType(str, Enum):
    """Type of content being reviewed."""

    STATUTORY = "statutory"
    BEST_PRACTICE = "best_practice"
    RATE_TABLE = "rate_table"
    TEMPLATE = "template"


class ReviewSLA(str, Enum):
    """Review SLA based on urgency."""

    CRITICAL = "24_hours"
    STANDARD = "72_hours"
    LOW = "7_days"


@dataclass
class ReviewRequirement:
    """Defines what's needed to approve a content change."""

    content_type: ContentType
    min_reviewers: int
    required_qualifications: list[ReviewerQualification]
    sla: ReviewSLA


@dataclass
class ExpertReview:
    """Record of an expert review."""

    review_id: str
    content_id: str
    reviewer_id: str
    reviewer_qualification: ReviewerQualification
    approved: bool
    comments: str
    reviewed_at: datetime = field(default_factory=datetime.now)


@dataclass
class GovernanceRecord:
    """Complete governance record for a content change."""

    content_id: str
    content_type: ContentType
    requirement: ReviewRequirement
    reviews: list[ExpertReview] = field(default_factory=list)
    is_approved: bool = False
    approved_at: Optional[datetime] = None

    @property
    def review_count(self) -> int:
        return len(self.reviews)

    @property
    def approval_count(self) -> int:
        return sum(1 for r in self.reviews if r.approved)

    @property
    def meets_requirements(self) -> bool:
        """Check if the governance requirements are met."""
        if self.approval_count < self.requirement.min_reviewers:
            return False
        # Check that required qualifications are covered
        reviewer_quals = {r.reviewer_qualification for r in self.reviews if r.approved}
        for req_qual in self.requirement.required_qualifications:
            if req_qual not in reviewer_quals:
                return False
        return True


# ── Review requirements by content type ──────────────────────

REVIEW_REQUIREMENTS: dict[ContentType, ReviewRequirement] = {
    ContentType.STATUTORY: ReviewRequirement(
        content_type=ContentType.STATUTORY,
        min_reviewers=2,
        required_qualifications=[
            ReviewerQualification.IHRP_CERTIFIED,
            ReviewerQualification.EMPLOYMENT_LAWYER,
        ],
        sla=ReviewSLA.CRITICAL,
    ),
    ContentType.BEST_PRACTICE: ReviewRequirement(
        content_type=ContentType.BEST_PRACTICE,
        min_reviewers=1,
        required_qualifications=[ReviewerQualification.IHRP_CERTIFIED],
        sla=ReviewSLA.STANDARD,
    ),
    ContentType.RATE_TABLE: ReviewRequirement(
        content_type=ContentType.RATE_TABLE,
        min_reviewers=2,
        required_qualifications=[ReviewerQualification.CPF_SPECIALIST],
        sla=ReviewSLA.CRITICAL,
    ),
    ContentType.TEMPLATE: ReviewRequirement(
        content_type=ContentType.TEMPLATE,
        min_reviewers=1,
        required_qualifications=[ReviewerQualification.DOMAIN_EXPERT],
        sla=ReviewSLA.LOW,
    ),
}


def get_review_requirement(content_type: ContentType) -> ReviewRequirement:
    """Get the review requirement for a content type."""
    return REVIEW_REQUIREMENTS[content_type]


# ── Dual Plane Model ─────────────────────────────────────────

TRUST_PLANE = {
    "description": "Human accountability layer",
    "responsibilities": [
        "Content accuracy validation",
        "Boundary definition for agents",
        "Escalation rule governance",
        "KB update approval",
        "Error correction verification",
        "Monthly accuracy audit",
    ],
    "operators": [
        "IHRP-certified practitioners",
        "Employment lawyers",
        "Domain specialists (CPF, tax, WSH)",
    ],
}

EXECUTION_PLANE = {
    "description": "AI-scaled delivery layer",
    "responsibilities": [
        "Advisory response generation",
        "Query classification and routing",
        "Calculator computation",
        "Document generation",
        "Citation validation",
        "Rate limiting and guardrails",
    ],
    "constraints": [
        "Cannot modify KB content",
        "Cannot make legal determinations",
        "Must cite from KB only",
        "Must respect constraint envelopes",
        "Must flag low-confidence responses",
    ],
}
