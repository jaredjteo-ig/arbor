# T069 — Wire Anti-Amnesia Injection and EATP Trust Lineage into Live Pipeline

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: HIGH
**Estimated Effort**: 4h
**Dependencies**: T063, T064, T065

## What to build

`get_anti_amnesia_injection()` and the EATP trust chain infrastructure exist (T044) but are never invoked during live queries. Wire them into the pipeline: inject anti-amnesia rules into every specialist's system prompt, create a `GenesisRecord` per query session, create an `AgentAttestation` per agent call, validate each agent's output against its constraint envelope, and pass the completed `TrustChain` to the response synthesizer for inclusion in the response metadata.

## Acceptance Criteria

- [ ] `get_anti_amnesia_injection()` called for each specialist and injected into system prompt
- [ ] `create_trust_chain()` called at pipeline start with session context
- [ ] `GenesisRecord` created per query with: user trust level, company profile completeness flag, KB currency status
- [ ] `AgentAttestation` created per specialist call with: domain, provisions retrieved, confidence score
- [ ] `validate_constraint_envelope()` called on each specialist output; violations logged and flagged in response
- [ ] Completed `TrustChain` attached to advisory response as `trust_metadata`
- [ ] Integration test: trust chain returned in response contains attestations from all specialists called
- [ ] Integration test: constraint violation (specialist advising outside its domain) is flagged in chain

## Files

- `src/hr_advisory/api/routers/advisory.py` — add trust chain creation, per-agent attestation, constraint validation
- `src/hr_advisory/agents/specialists/_base.py` — inject anti-amnesia into system prompt construction
- `src/hr_advisory/trust/eatp_lineage.py` — verify all public functions work as expected (read-only review)

## Reference

T044 (EATP lineage already built), 11-agent-architecture-analysis.md Section 1.3

## Definition of Done

- [ ] Every live advisory response includes `trust_metadata` with chain confidence score
- [ ] Anti-amnesia rules present in every specialist system prompt
- [ ] Constraint envelope validation active for all specialists
- [ ] No increase in response latency beyond 100ms for trust wiring overhead
