# T063 — Replace OrchestratorAgent with Deterministic DispatchRouter

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: HIGH
**Estimated Effort**: 3h

## What to build

The `OrchestratorAgent` makes an unnecessary LLM call to re-decide routing that `QueryAnalyzerAgent` already determined. Replace it with a deterministic `DispatchRouter` class that reads `QueryAnalysisResult` and deterministically selects specialists and dispatch mode.

## Acceptance Criteria

- [ ] `DispatchRouter` class created — no LLM calls, pure Python logic
- [ ] Maps domain strings to specialist instances (employment_act, cpf, foreign_manpower, fair_employment, tax, wsh, pdpa)
- [ ] Selects dispatch mode: parallel (independent domains), sequential (dependent), router (single domain)
- [ ] Falls back to sequential for unknown domain combinations
- [ ] Advisory router pipeline updated to instantiate `DispatchRouter` instead of `OrchestratorAgent`
- [ ] `OrchestratorAgent` retained but no longer in the hot path (kept for reference)
- [ ] Integration test: multi-domain query routed correctly without LLM call at dispatch stage

## Files

- `src/hr_advisory/agents/orchestration/dispatch_router.py` — new file
- `src/hr_advisory/api/routers/advisory.py` — swap orchestrator for dispatch router

## Reference

11-agent-architecture-analysis.md Section 2.1 Change 1

## Definition of Done

- [ ] No `OrchestratorAgent` in the live advisory pipeline
- [ ] `DispatchRouter` unit-tested with all domain combinations
- [ ] Latency improvement verified (1 fewer LLM call per query, approx 1-3s faster)
