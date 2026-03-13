"""DataFlow models for the regulatory knowledge base.

These models store Singapore employment legislation, tripartite guidelines,
and HR best practices in a structured, queryable format with vector
embeddings for semantic search.
"""

from datetime import datetime
from typing import Optional

from hr_advisory.models.database import db
from hr_advisory.models.enums import (
    AuthorityLevel,
    ApplicabilityRuleType,
    CrossReferenceType,
)


@db.model
class Act:
    """A legislative act, regulation, or guideline document.

    Examples: Employment Act 1968, CPF Act, Tripartite Guidelines on FWA.
    """

    title: str
    short_name: str
    authority_type: str = AuthorityLevel.STATUTE.value
    issuing_body: str = ""
    current_version_date: Optional[datetime] = None
    official_url: Optional[str] = None
    is_active: bool = True


@db.model
class Domain:
    """HR knowledge domain for organising provisions.

    Supports hierarchy via parent_domain_id (self-referential).
    Examples: Compensation & Benefits > CPF > Contribution Rates.
    """

    name: str
    description: Optional[str] = None
    parent_domain_id: Optional[int] = None
    sort_order: int = 0


@db.model
class Provision:
    """A specific section, clause, or guideline provision.

    The core knowledge unit — stores formal text, plain-language summary,
    interpretation notes, and an embedding vector for semantic search.
    """

    source_act_id: int
    section: str
    title: str
    formal_text: str
    plain_summary: str = ""
    interpretation_notes: Optional[str] = None
    effective_date: Optional[datetime] = None
    superseded_date: Optional[datetime] = None
    superseded_by_id: Optional[int] = None
    authority_level: str = AuthorityLevel.STATUTE.value
    domain_id: Optional[int] = None
    next_review_date: Optional[datetime] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None

    __dataflow__ = {
        "soft_delete": True,
        "indexes": [
            {"name": "idx_provision_act", "fields": ["source_act_id"]},
            {"name": "idx_provision_domain", "fields": ["domain_id"]},
            {"name": "idx_provision_authority", "fields": ["authority_level"]},
            {"name": "idx_provision_active", "fields": ["is_active"]},
        ],
    }


@db.model
class ApplicabilityRule:
    """Conditions under which a provision applies.

    Examples: "Applies when headcount >= 5", "Applies to S-Pass holders",
    "Applies to companies in F&B sector".
    """

    provision_id: int
    rule_type: str = ApplicabilityRuleType.HEADCOUNT.value
    criteria_type: str = ""
    criteria_value: Optional[dict] = None
    notes: Optional[str] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_applicability_provision", "fields": ["provision_id"]},
            {"name": "idx_applicability_type", "fields": ["rule_type"]},
        ],
    }


@db.model
class CrossReference:
    """Relationship between two provisions.

    Captures how provisions interact: amendments, supplements,
    contradictions, implementations.
    """

    source_provision_id: int
    target_provision_id: int
    relationship_type: str = CrossReferenceType.RELATED.value
    notes: Optional[str] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_xref_source", "fields": ["source_provision_id"]},
            {"name": "idx_xref_target", "fields": ["target_provision_id"]},
        ],
    }


@db.model
class PracticalExample:
    """Worked example showing how a provision applies in practice.

    Includes scenario description, calculation details (JSON),
    and the outcome — used to give SMEs concrete guidance.
    """

    provision_id: int
    scenario: str
    calculation: Optional[dict] = None
    outcome: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_example_provision", "fields": ["provision_id"]},
        ],
    }


@db.model
class RateTable:
    """Numerical rates that change over time.

    Examples: CPF contribution rates, levy rates, salary thresholds.
    Soft-deleted so historical rates are preserved.
    """

    table_type: str
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    criteria: Optional[dict] = None
    rate_value: str = ""
    source_url: Optional[str] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None

    __dataflow__ = {
        "soft_delete": True,
        "indexes": [
            {"name": "idx_rate_type", "fields": ["table_type"]},
            {"name": "idx_rate_effective", "fields": ["effective_date"]},
            {"name": "idx_rate_active", "fields": ["is_active"]},
        ],
    }
