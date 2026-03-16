---
name: trust-governance
description: "EATP trust lineage and CARE governance reference. Use when working on trust chains, attestations, constraint envelopes, citation validation, or expert review workflows."
---

# Trust & Governance

Three complementary frameworks ensure advisory accuracy and auditability.

## EATP Trust Lineage

Every advisory response carries: GenesisRecord -> AgentAttestations -> TrustChain

### Quick Reference

```python
# Create genesis record (step 4 of safety chain)
genesis = create_genesis_record(
    session_id=session_id,
    query_text=query,
    query_domains=detected_domains,
    company_profile_completeness=0.8,
)

# Create agent attestation
attestation = AgentAttestation(
    agent_id="cpf_specialist",
    agent_role="specialist",
    domain="cpf",
    provisions_retrieved=["cpf_contrib_rates_2026"],
    confidence_score=0.85,
    constraint_envelope_id="cpf_envelope",
)

# Aggregate into trust chain
chain = TrustChain(
    genesis_record=genesis,
    attestations=[attestation],
    chain_confidence=min(a.confidence_score for a in attestations),
)
```

### Chain Confidence Model

- **Weakest-link**: Chain confidence = minimum across all attestations
- Below 0.7 → AMBER risk tier
- Below 0.5 → RED risk tier + human review flag

## Constraint Envelopes

Hard boundaries per specialist agent:

- `allowed_domains` — domains the agent CAN advise on
- `forbidden_domains` — domains the agent MUST NOT touch
- `can_make_legal_determinations` — always False
- `can_modify_kb` — always False

Validated by `validate_constraint_envelope()`. Violations recorded in trust chain.

## Anti-Amnesia

5 constraints re-injected every query turn:

1. KB-only citations (no training data)
2. Stay within constraint envelope
3. Risk tier classification rules
4. Low confidence → recommend human specialist
5. Authorized domain boundaries

File: `src/hr_advisory/trust/eatp_lineage.py`

## CARE Dual Plane

| Trust Plane (Human)         | Execution Plane (AI)   |
| --------------------------- | ---------------------- |
| Content accuracy validation | Response generation    |
| Boundary definition         | Query classification   |
| KB update approval          | Calculator computation |
| Error correction            | Citation validation    |
| Monthly audit               | Rate limiting          |

## Risk Tiering Rules

| Condition                          | Tier      | Action                |
| ---------------------------------- | --------- | --------------------- |
| Informational, high confidence     | GREEN     | Standard disclaimer   |
| Fair employment / foreign manpower | AMBER min | Enhanced disclaimer   |
| Confidence < 0.7                   | AMBER     | Caveat added          |
| Confidence < 0.5                   | RED       | Professional referral |
| Litigation trigger                 | RED       | Mandatory escalation  |
| Response screening fail            | RED       | Safe fallback         |

**Key rule**: Risk tiers ONLY escalate, never downgrade.

## Expert Review (KB Changes)

| Content       | Reviewers | Qualifications | SLA    |
| ------------- | --------- | -------------- | ------ |
| Statutory     | 2         | IHRP + Lawyer  | 24h    |
| Best practice | 1         | IHRP           | 72h    |
| Rate table    | 2         | CPF specialist | 24h    |
| Template      | 1         | Domain expert  | 7 days |

## Learning Pipeline

Feedback → Gap detection → Recommendations → Expert review → KB update

Workflow: `proposed` → `under_review` → `approved` → `implemented`

## Key Files

- `src/hr_advisory/trust/eatp_lineage.py` — Trust chain implementation
- `src/hr_advisory/trust/citation_validator.py` — Citation validation
- `src/hr_advisory/trust/eatp_lineage.py` — Also contains anti-amnesia constraint injection
- `src/hr_advisory/trust/care_governance.py` — CARE framework
- `src/hr_advisory/trust/disclaimers.py` — Disclaimer generation
- `docs/04-trust-governance.md` — Full documentation

## Consult Agent

For trust/governance work: `trust-governance-specialist`
