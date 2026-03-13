"""DataFlow models for the HR AI Advisory platform."""

from hr_advisory.models.database import db
from hr_advisory.models.enums import (
    AuthorityLevel,
    RiskTier,
    ApplicabilityRuleType,
    CrossReferenceType,
)
from hr_advisory.models.knowledge_base import (
    Act,
    Domain,
    Provision,
    ApplicabilityRule,
    CrossReference,
    PracticalExample,
    RateTable,
)
from hr_advisory.models.company_user import (
    Company,
    User,
    Conversation,
    AdvisorySession,
    ContentUpdate,
    Template,
    UserRole,
    ContentUpdateStatus,
    ContentUrgency,
)
from hr_advisory.models.qa import (
    QASession,
    QAEvaluation,
    InstructionPatch,
    PatchTestResult,
    SessionStatus,
    EvaluationFailureCategory,
    TargetAgent,
    PatchStatus,
    TestRunType,
)

__all__ = [
    "db",
    # Enums
    "AuthorityLevel",
    "RiskTier",
    "ApplicabilityRuleType",
    "CrossReferenceType",
    "UserRole",
    "ContentUpdateStatus",
    "ContentUrgency",
    "SessionStatus",
    "EvaluationFailureCategory",
    "TargetAgent",
    "PatchStatus",
    "TestRunType",
    # Knowledge base
    "Act",
    "Domain",
    "Provision",
    "ApplicabilityRule",
    "CrossReference",
    "PracticalExample",
    "RateTable",
    # Company & user
    "Company",
    "User",
    "Conversation",
    "AdvisorySession",
    "ContentUpdate",
    "Template",
    # QA workflow
    "QASession",
    "QAEvaluation",
    "InstructionPatch",
    "PatchTestResult",
]
