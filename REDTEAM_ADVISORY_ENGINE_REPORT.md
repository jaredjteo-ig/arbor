# Red Team Report: Autonomous Advisory Engine

**Date**: 2026-03-21
**Auditor Perspective**: Enterprise CTO evaluating AI HR advisory platform
**Environment**: https://arbor.terrene.foundation
**Method**: Automated API testing + Playwright browser screenshots + source code analysis
**Engine Under Test**: Autonomous LLM with function calling (gpt-5-chat-latest)
**Previous Engine**: 13-step Kaizen agent pipeline (gpt-5-mini)

## Executive Summary

**THE ADVISORY ENGINE IS COMPLETELY DOWN IN PRODUCTION.** Every advisory query returns HTTP 500. The root cause is two Python NameErrors introduced when the old 13-step pipeline was replaced with the new autonomous engine: (1) `citation_result` is referenced but never assigned -- the old pipeline called `validate_citations()` but the new code path skipped it; (2) `_est_input_tokens`/`_est_output_tokens` were renamed to `_real_input_tokens`/`_real_output_tokens` but the old variable names were left in a downstream `log_llm_call()` invocation.

Only the scope-check guardrail works (out-of-scope queries like "what is the weather" get blocked before reaching the broken code path). All 10 substantive advisory tests failed with 500 errors. The fix is a 3-line code change.

**Severity: CRITICAL -- Production outage. Zero advisory queries can succeed.**

## Root Cause Analysis

### Bug 1: `citation_result` NameError (CRITICAL)

**File**: `src/hr_advisory/api/routers/advisory.py`, lines 785 and 2236

The old pipeline had a step that called `validate_citations()` to produce `citation_result`. When the pipeline was replaced with the autonomous engine (Step 4 now calls `AdvisoryEngine.run()`), the citation validation step was removed, but `citation_result.warnings` is still referenced in the response construction at line 785 (regular endpoint) and line 2236 (streaming endpoint).

```python
# Line 785 -- REFERENCES UNDEFINED VARIABLE
"citation_warnings": citation_result.warnings,  # NameError!
```

**Impact**: Every advisory query that passes the guardrails (scope check, injection check, rate limit) hits this NameError and returns 500.

### Bug 2: `_est_input_tokens` / `_est_output_tokens` NameError (HIGH)

**File**: `src/hr_advisory/api/routers/advisory.py`, lines 772-773

The token tracking variables were renamed from `_est_input_tokens`/`_est_output_tokens` to `_real_input_tokens`/`_real_output_tokens` (to reflect that the autonomous engine provides actual token counts, not estimates), but the old names were left in the `log_llm_call()` invocation.

```python
# Lines 772-773 -- OLD NAMES, UNDEFINED
input_tokens=_est_input_tokens,   # NameError!
output_tokens=_est_output_tokens,  # NameError!
```

**Impact**: Would cause a second NameError for non-BYOK users with a company_id, but Bug 1 prevents execution from reaching this point.

### Fix Applied

Three changes in `src/hr_advisory/api/routers/advisory.py`:

1. **Import** `CitationValidationResult` alongside `validate_citations`
2. **Add citation validation step** (Step 9b) before the response is constructed, in both regular and streaming endpoints
3. **Fix variable names** from `_est_input_tokens`/`_est_output_tokens` to `_real_input_tokens`/`_real_output_tokens`

Total diff: 23 lines added, 5 lines removed. Pure bug fix, no behavioral changes.

## Test Results (Pre-Fix)

Ran 11 test scenarios with 74 quality checks against production. **12/74 passed (16%).**

### OLD vs NEW Comparison Table

| Test Case                      | OLD System (Kaizen Pipeline)                                   | NEW System (Autonomous Engine)                                | Verdict    |
| ------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------- | ---------- |
| EP Hiring Obligations          | Misrouted to Employment Act domain. Generic template response. | HTTP 500 -- engine crashes before generating any response     | **BROKEN** |
| Maternity Leave                | Returned annual leave template instead of maternity leave.     | HTTP 500                                                      | **BROKEN** |
| CPF Calculation                | Returned "Routing to CalculatorAgent" stub. No actual numbers. | HTTP 500                                                      | **BROKEN** |
| S Pass Quota                   | No calculator integration. Generic EFMA text.                  | HTTP 500                                                      | **BROKEN** |
| Multi-Turn Context             | Follow-ups lost domain context. Each turn was independent.     | HTTP 500 on all 3 turns                                       | **BROKEN** |
| Multi-Domain: EP + Termination | Routed to single domain only.                                  | HTTP 500                                                      | **BROKEN** |
| Multi-Domain: CPF + Leave      | Could not handle compound queries.                             | HTTP 500                                                      | **BROKEN** |
| Adversarial CPF                | Keyword router confused by adversarial phrasing.               | HTTP 500                                                      | **BROKEN** |
| Emergency WSH                  | No emergency routing. Standard response latency.               | HTTP 500                                                      | **BROKEN** |
| PDPA NRIC                      | No PDPA domain coverage.                                       | HTTP 500                                                      | **BROKEN** |
| Out of Scope (Weather)         | Basic keyword scope check -- worked.                           | Scope check still works (200). Blocked before hitting engine. | **PASS**   |

### What Works

1. **Landing page**: Professional, clear value proposition, feature list, CTA
2. **Authentication**: Registration, login, JWT tokens all functional
3. **UI/UX**: Advisory chat interface is well-designed with suggested queries, conversation history sidebar, proper input
4. **Scope guardrails**: Out-of-scope queries are correctly blocked before reaching the engine
5. **Injection detection**: Prompt injection screening works (pre-engine step)
6. **Rate limiting**: Rate limit check works (pre-engine step)

### What Is Broken

1. **ALL advisory queries**: 100% failure rate on any HR question
2. **Streaming endpoint**: Same bug exists -- `citation_result` undefined
3. **LLM usage logging**: `_est_input_tokens` undefined (secondary bug)

## Architecture Assessment (Code Review)

The autonomous engine architecture (`advisory_engine.py`) is well-designed:

- **6 tools** with proper OpenAI function-calling schema: `search_kb`, `calculate_cpf`, `calculate_leave`, `calculate_salary`, `calculate_quota_levy`, `get_company_context`
- **Loop with MAX_TOOL_ROUNDS=10** to prevent runaway tool-calling
- **Proper error handling** with degraded mode fallback
- **Token tracking** across tool-calling rounds
- **Confidence/risk extraction** from LLM responses
- **Citation extraction** from KB search results

The safety chain wrapping the engine is comprehensive:

- Input sanitization, query length validation
- Rate limiting (per-user)
- Scope screening (is this an HR question?)
- Prompt injection detection
- Query content screening (circumvention, escalation)
- EATP trust chain creation
- Confidence escalation checks
- Response content screening
- Risk-tiered disclaimers
- Citation validation (now fixed)
- Constraint envelope validation
- Learning pipeline recording
- Conversation memory persistence
- Budget tracking (BYOK awareness)

**The architecture is solid. The failure was a simple integration error -- the new engine was wired in but the downstream steps still referenced variables from the old pipeline.**

## Response Times (Pre-Fix)

Even though all queries returned 500, the timing reveals how far execution got:

| Query                  | Time        | Analysis                                                           |
| ---------------------- | ----------- | ------------------------------------------------------------------ |
| Out of scope (weather) | 0.6s        | Blocked by scope check (fast path, no LLM call)                    |
| CPF calculation        | 3.4s        | LLM called, tool calls executed, then crashed at citation_result   |
| EP hiring              | 13.7s       | LLM called search_kb (multiple rounds), crashed at citation_result |
| Maternity leave        | 12.7s       | Similar -- LLM + KB search, then crash                             |
| Multi-turn (3 queries) | 14.3s total | Each turn crashed independently                                    |

These times suggest the LLM and tools ARE working -- the engine successfully calls tools and gets responses, but the post-processing crashes.

## Cross-Cutting Issues

### Issue 1: No Company for New Users

**Severity**: HIGH

New users register without a `company_id` (it's null). The advisory endpoint handles this gracefully (falls back to server LLM defaults), but the company creation endpoint (`POST /profile/`) returned 500 during testing. Users without a company cannot get personalized advice (no sector, headcount, or compliance context).

### Issue 2: No Integration Tests for the New Pipeline

**Severity**: HIGH

The NameError would have been caught by any integration test that exercises the full advisory flow (query -> engine -> trust chain -> response). The 3050 unit tests pass, but none test the advisory response construction with the new engine.

### Issue 3: Streaming Endpoint Has Same Bug

**Severity**: CRITICAL (same as Bug 1)

The streaming endpoint (`POST /advisory/stream`) at line 2236 has the identical `citation_result` NameError. Both endpoints are fixed in the same patch.

## Recommended Actions

### Immediate (Deploy Now)

1. **Deploy the fix** in `src/hr_advisory/api/routers/advisory.py` -- the 3-change patch that adds `citation_result` assignment and fixes the variable names
2. **Verify** by running the red-team test script (`tests/redteam_advisory_engine.py`) against production after deploy

### Short-Term (This Sprint)

3. **Add integration test** that exercises the full `/advisory/query` endpoint with a real or mocked LLM response, verifying the response structure includes `citation_warnings`
4. **Fix company creation** -- investigate why `POST /profile/` returns 500 for new users
5. **Re-run the full red-team test suite** after deploy to generate the comparison table showing OLD vs NEW improvements

### Medium-Term

6. **Add smoke test to deploy pipeline** -- `ship.sh` should hit `/advisory/query` with a test query and verify 200 before declaring deploy successful
7. **Add Python linting rule** to detect undefined variable references (pyflakes or ruff would have caught both NameErrors)

## Bottom Line

The autonomous advisory engine is architecturally superior to the old 13-step pipeline -- it uses real LLM function calling instead of keyword routing, it can handle multi-domain and multi-turn queries natively, and it has proper tool integration for calculators and KB search. However, it was deployed to production with a trivial integration bug that makes it return 500 on every query. The fix is 3 lines. After deploying the fix, the full test suite needs to be re-run to validate that the new engine actually delivers on its architectural promise.

From a CTO perspective: **the engineering quality is high but the deployment process has a critical gap -- no integration smoke test. A $500K platform cannot ship a total feature outage. Fix the bug, add the smoke test, then re-evaluate.**
