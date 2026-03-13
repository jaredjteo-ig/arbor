# T023 — Agent Team Integration Testing

## Status: COMPLETED

## What Was Built

### CalculatorAgent Enhancement (`src/hr_advisory/agents/actions/calculator.py`)

- Added `quota_levy` calculator type that delegates to the pure `calculate_quota_levy()` function
- CalculatorAgent now supports 4 calculator types: cpf, leave, salary, quota_levy

### Integration Test Suite (`tests/integration/test_agent_team_integration.py`)

Comprehensive agent team integration tests covering:

1. **Calculator dispatch** (6 tests): quota_levy type supported, services/manufacturing scenarios, levy projections, infeasible warnings, headroom
2. **Multi-specialist pool coordination** (3 tests): 3 specialists write → compliance reads, cross-domain flags preserved, provision IDs aggregated
3. **Multi-turn context** (3 tests): 10-turn conversation maintains history, 12-turn window evicts oldest, multi-session isolation
4. **Risk-tier escalation** (5 tests): green stays green, amber escalates, red overrides amber, empty pool defaults green, low confidence doesn't suppress risk
5. **Concurrent sessions** (2 tests): 10 isolated sessions, ThreadPoolExecutor concurrent writes
6. **Trust lineage** (3 tests): metadata fields (agent_id, provision_ids, confidence, risk_tier), pipeline trust chain, multi-domain lineage aggregation
7. **Calculator-pure function integration** (3 tests): CPF matches, quota_levy matches pure function, all 4 types accessible
8. **Long-term company tracking** (2 tests): frequent topic detection, advisory history ordering
9. **LLM-dependent Singlish queries** (5 tests, skip without API key): 5 real Singlish HR queries route correctly
10. **LLM-dependent cross-domain routing** (2 tests, skip without API key): retrenchment multi-domain, foreign hire routing
11. **LLM-dependent full pipeline** (1 test, skip without API key): end-to-end with calculator integration

## Verification

27 deterministic tests passed + 8 LLM-dependent tests (skip without API key)
61 existing specialist tests still pass (no regressions)

## Files

- `src/hr_advisory/agents/actions/calculator.py` (modified)
- `tests/integration/test_agent_team_integration.py` (new)
