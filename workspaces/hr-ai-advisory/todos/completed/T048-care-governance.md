# T048 — CARE Governance

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Governance Enums**:

- `ReviewerQualification` enum (IHRP_CERTIFIED, EMPLOYMENT_LAWYER, CPF_SPECIALIST, TAX_SPECIALIST, WSH_SPECIALIST, DOMAIN_EXPERT)
- `ContentType` enum (STATUTORY, BEST_PRACTICE, RATE_TABLE, TEMPLATE)
- `ReviewSLA` enum (CRITICAL/24h, STANDARD/72h, LOW/7 days)

**Review Data Models**:

- `ReviewRequirement` dataclass defining minimum reviewers, required qualifications, and SLA per content type
- `ExpertReview` dataclass recording individual review decisions with qualification, approval status, and comments
- `GovernanceRecord` dataclass tracking full governance lifecycle with `meets_requirements` property that checks both reviewer count and qualification coverage

**Review Requirements by Content Type**:

- STATUTORY: 2 reviewers (IHRP_CERTIFIED + EMPLOYMENT_LAWYER), 24h SLA
- BEST_PRACTICE: 1 reviewer (IHRP_CERTIFIED), 72h SLA
- RATE_TABLE: 2 reviewers (CPF_SPECIALIST), 24h SLA
- TEMPLATE: 1 reviewer (DOMAIN_EXPERT), 7-day SLA

**Dual Plane Model**:

- `TRUST_PLANE` — human accountability layer defining responsibilities (content accuracy validation, boundary definition, escalation rule governance, KB update approval, error correction verification, monthly accuracy audit) and required operators (IHRP practitioners, employment lawyers, domain specialists)
- `EXECUTION_PLANE` — AI-scaled delivery layer defining responsibilities (response generation, query routing, calculator computation, document generation, citation validation, guardrails) and hard constraints (cannot modify KB, cannot make legal determinations, must cite from KB only, must respect constraint envelopes, must flag low-confidence responses)

**Addresses**: R2-GAP5 (CARE governance framework)

## Files

- `src/hr_advisory/trust/care_governance.py` — CARE governance module
