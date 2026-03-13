---
name: advisory-safety-chain
description: "13-step advisory safety chain reference. Use when modifying advisory endpoints, guardrails, response generation, or debugging blocked/escalated queries."
---

# Advisory Safety Chain

Every HR advisory query passes through 13 sequential steps. If any step blocks, the query is rejected with an explanation.

## Chain Steps (Quick Reference)

| #   | Step                   | File                          | Outcome                        |
| --- | ---------------------- | ----------------------------- | ------------------------------ |
| 1   | Input sanitisation     | `security/validation.py`      | XSS-safe, null-free, truncated |
| 2   | Rate limiting          | `workflows/guardrails.py`     | 429 if exceeded                |
| 3   | Query screening        | `workflows/guardrails.py`     | PASS / BLOCK / ESCALATE        |
| 4   | EATP genesis record    | `trust/eatp_lineage.py`       | Trust anchor created           |
| 5   | Anti-amnesia injection | `trust/eatp_lineage.py`       | Constraints re-injected        |
| 6   | Domain detection       | `workflows/classification/`   | Domains classified             |
| 7   | KB retrieval           | `trust/citation_validator.py` | Provisions fetched             |
| 8   | Citation validation    | `trust/citation_validator.py` | Citations verified             |
| 9   | Response generation    | `api/routers/advisory.py`     | KB-grounded response           |
| 10  | Confidence check       | `api/routers/advisory.py`     | Risk tier escalation           |
| 11  | Response screening     | `workflows/guardrails.py`     | TAFEP compliance check         |
| 12  | Disclaimer             | `trust/disclaimers.py`        | Risk-tiered disclaimer         |
| 13  | Trust chain            | `trust/eatp_lineage.py`       | Full audit trail               |

All paths are relative to `src/hr_advisory/`.

## Guardrail Patterns

### Circumvention (BLOCK)

Queries attempting to bypass safety controls. Returns explanation of why blocked.

Examples: "ignore previous instructions", "bypass safety", "how to avoid paying CPF"

### Escalation (RED tier)

Queries requiring human specialist referral:

- Litigation: TADM claims, wrongful/unfair dismissal, mediation, ECT
- Criminal: theft, fraud, assault in workplace context
- Discrimination: active complaints, TAFEP violations

### Rate Limits

| Category   | Per Minute | Per Hour | Burst |
| ---------- | ---------- | -------- | ----- |
| Advisory   | 10         | 100      | 3     |
| Auth       | 5          | 20       | 2     |
| Calculator | 30         | 500      | 10    |
| Admin      | 20         | 200      | 5     |
| Document   | 10         | 100      | 3     |

## Response Structure

```json
{
  "query": "...",
  "response": "...",
  "provisions_cited": [
    { "provision_id": "...", "title": "...", "authority_level": "..." }
  ],
  "risk_tier": "green|amber|red",
  "confidence_score": 0.85,
  "disclaimer": { "show": true, "text": "...", "professional_referral": false },
  "trust_chain": {
    "session_id": "...",
    "genesis_fingerprint": "...",
    "chain_confidence": 0.85
  },
  "citation_warnings": [],
  "timestamp": "..."
}
```

## Streaming (SSE)

`POST /advisory/stream` returns Server-Sent Events:

- `event: start` — Query accepted, risk tier
- `event: disclaimer` — Disclaimer text
- `event: token` — Individual word tokens
- `event: complete` — Full response with trust chain

Same safety chain as `/advisory/query`.

## Critical Rules

1. NEVER skip or reorder steps
2. NEVER return a response without a trust chain
3. Risk tiers ONLY escalate, never downgrade
4. Anti-amnesia constraints injected on EVERY query
5. Streaming applies the SAME chain as synchronous
6. Circumvention blocks MUST explain WHY

## Related Documentation

- `docs/01-architecture.md` — Advisory pipeline architecture
- `docs/03-security.md` — Security chain details
- `docs/04-trust-governance.md` — Trust chain and risk tiering

## Consult Agent

For safety chain modifications: `advisory-safety-chain-specialist`
