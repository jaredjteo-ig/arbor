---
type: DECISION
date: 2026-03-30
project: arbor
topic: Delete pre-Delegate specialist and orchestration agents
phase: implement
tags: [cleanup, delegate, agents, dead-code]
---

# Delete 14 Pre-Delegate Agent Files (8,657 lines)

## Decision

Remove 8 specialist agents (compliance, cpf, employment_act, fair_employment, foreign_manpower, pdpa, tax, wsh) and 6 orchestration agents (dispatch_router, orchestrator, query_analyzer, query_clarifier, response_synthesizer, kb_retriever) along with dead config classes, signatures, and test files.

## Alternatives Considered

1. **Keep as reference** — rejected; the Delegate engine is the active path and these files create confusion about which code is live
2. **Gradual removal** — rejected; all 14 files are uniformly dead (zero imports from active code paths)

## Rationale

The Delegate engine (kaizen-agents) handles all advisory domains via 208+ tools with a TAOD loop. The specialist agents were a Kaizen BaseAgent + Signature pattern that predated the Delegate. Red team verified zero active references. 4 parallel agents confirmed convergence.

## Consequences

- PatchRunner is structurally broken (no agents to patch) — needs redesign for Delegate
- QA evaluation pipeline still works; only patch testing/deployment is affected
- `_base.py` and `DocumentGenerationAgent` preserved (still used as tool backends)
