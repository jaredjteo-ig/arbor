"""Enum definitions for HR Advisory models.

DataFlow stores enums as TEXT. These Python enums provide
type safety in application code; use .value when passing
to DataFlow nodes.
"""

from enum import Enum


class AuthorityLevel(str, Enum):
    """How binding a provision is — determines risk tier defaults."""

    STATUTE = "statute"
    SUBSIDIARY = "subsidiary"
    TRIPARTITE_GUIDELINE = "tripartite_guideline"
    ADVISORY = "advisory"
    BEST_PRACTICE = "best_practice"


class RiskTier(str, Enum):
    """Advisory response risk classification."""

    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class ApplicabilityRuleType(str, Enum):
    """Types of applicability conditions."""

    HEADCOUNT = "headcount"
    SECTOR = "sector"
    WORKER_TYPE = "worker_type"
    SALARY_THRESHOLD = "salary_threshold"
    COMPANY_TYPE = "company_type"
    EFFECTIVE_DATE = "effective_date"


class CrossReferenceType(str, Enum):
    """How two provisions relate to each other."""

    AMENDS = "amends"
    SUPPLEMENTS = "supplements"
    CONTRADICTS = "contradicts"
    IMPLEMENTS = "implements"
    SUPERSEDES = "supersedes"
    RELATED = "related"
