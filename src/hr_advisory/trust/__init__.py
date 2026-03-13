"""Trust, governance, and transparency infrastructure.

Modules:
- eatp_lineage: EATP trust chain tracking (T044)
- citation_validator: Pre-delivery citation validation (T045)
- disclaimers: Risk-tiered disclaimer system (T046)
- error_correction: Error correction and transparency (T047)
"""

from hr_advisory.trust.citation_validator import (
    validate_citations,
    get_provision_detail,
    get_valid_provisions,
    CitationValidationResult,
    ValidatedCitation,
    AuthorityLevel,
    CitationStatus,
)
from hr_advisory.trust.disclaimers import (
    get_disclaimer,
    apply_verification_gradient,
    PLATFORM_DISCLAIMER,
    DisclaimerContent,
    VerificationResult,
)
from hr_advisory.trust.eatp_lineage import (
    create_trust_chain,
    get_trust_chain,
    get_anti_amnesia_injection,
    get_constraint_envelope,
    validate_constraint_envelope,
    GenesisRecord,
    TrustChain,
    AgentAttestation,
    ConstraintEnvelope,
    TrustLevel,
    AgentRole,
)
from hr_advisory.trust.error_correction import (
    report_error,
    apply_correction,
    verify_correction,
    get_correction_log,
    get_error_records,
    ErrorRecord,
    ErrorSource,
    CorrectionStatus,
)

__all__ = [
    # EATP lineage
    "create_trust_chain",
    "get_trust_chain",
    "get_anti_amnesia_injection",
    "get_constraint_envelope",
    "validate_constraint_envelope",
    "GenesisRecord",
    "TrustChain",
    "AgentAttestation",
    "ConstraintEnvelope",
    "TrustLevel",
    "AgentRole",
    # Citation validation
    "validate_citations",
    "get_provision_detail",
    "get_valid_provisions",
    "CitationValidationResult",
    "ValidatedCitation",
    "AuthorityLevel",
    "CitationStatus",
    # Disclaimers
    "get_disclaimer",
    "apply_verification_gradient",
    "PLATFORM_DISCLAIMER",
    "DisclaimerContent",
    "VerificationResult",
    # Error correction
    "report_error",
    "apply_correction",
    "verify_correction",
    "get_correction_log",
    "get_error_records",
    "ErrorRecord",
    "ErrorSource",
    "CorrectionStatus",
]
