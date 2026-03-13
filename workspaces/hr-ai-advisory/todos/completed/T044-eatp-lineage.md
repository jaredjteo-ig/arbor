# T044 — EATP Trust Lineage

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Trust Level and Agent Role Enums**:

- `TrustLevel` enum (VERIFIED, STANDARD, LIMITED) for session trust anchoring
- `AgentRole` enum (USER, ORCHESTRATOR, SPECIALIST, SYNTHESIZER, VALIDATOR) for tracking agent contributions

**Constraint Envelope System**:

- `ConstraintEnvelope` dataclass defining hard boundaries per agent (allowed/forbidden domains, legal determination flag, KB modification flag)
- 8 predefined envelopes: employment_act_specialist, cpf_specialist, foreign_manpower_specialist, fair_employment_specialist, tax_specialist, wsh_specialist, compliance_specialist, orchestrator
- `validate_constraint_envelope()` deterministic boundary check returning violation descriptions when an agent responds outside its authorized domains

**Trust Chain Tracking**:

- `AgentAttestation` dataclass capturing per-agent contribution (domain, provisions retrieved, reasoning summary, confidence score, constraint violations)
- `GenesisRecord` dataclass as session trust anchor (user verification level, company profile completeness, KB currency status, agent version hashes, SHA-256 fingerprint)
- `TrustChain` dataclass aggregating genesis + attestations with chain confidence (minimum across attestations), provisions cited, human review status, and `to_dict()` serialization

**Anti-Amnesia Mechanism**:

- `ANTI_AMNESIA_RULES` — 4 critical constraints re-injected every agent turn to prevent drift from KB citations to parametric memory
- `get_anti_amnesia_injection()` — builds per-agent constraint block including domain-specific boundaries from the constraint envelope

**In-Memory Trust Store**:

- `create_trust_chain()` and `get_trust_chain()` for session-scoped trust chain management
- Production path: PostgresTrustStore via DataFlow

**Addresses**: R2-GAP6 (trust lineage), R2-GAP1 (constraint envelopes), R2-REC3 (anti-amnesia)

## Files

- `src/hr_advisory/trust/eatp_lineage.py` — EATP trust lineage module
