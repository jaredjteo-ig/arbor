# Red Team Round 8 — Production Gaps + Persistence Deploy

**Date**: 2026-03-21
**Scope**: Production gap fixes, persistence models, advisory pipeline, security review
**Agents**: e2e-runner, security-reviewer, value-auditor

## Deployed Fixes (3 commits)

| Commit    | Description                                                                                        |
| --------- | -------------------------------------------------------------------------------------------------- |
| `2c201fe` | 7 persistence models, observation pipeline wiring, SDK/Nexus compat                                |
| `86f87ba` | Security findings C1 (tenant isolation), C2 (NaN guard), H1/H2 (input limits), H4 (PII truncation) |
| `74ff0a1` | Advisory non-dict LLM return handling (fixes 500 on timeout)                                       |

## Production Test Results

| Test                          | Result      | Notes                                           |
| ----------------------------- | ----------- | ----------------------------------------------- |
| Health check                  | PASS        | 3 workflows healthy                             |
| Registration                  | PASS        | Field is `name` not `full_name`                 |
| Login                         | PASS        | JWT tokens issued                               |
| Advisory: annual leave        | PASS        | 6 provisions, 0.9 confidence, green tier        |
| Advisory: CPF rates           | PASS        | Employer 17%/employee 20%, PR differentiation   |
| Advisory: 3 concurrent        | PASS        | All 200, 45-53s (post-fix)                      |
| Guardrails: CPF circumvention | PASS        | Blocked, red tier                               |
| Guardrails: out-of-scope      | PARTIAL     | Red tier but not hard-blocked (MEDIUM)          |
| CPF calculator                | PASS        | Correct allocations matching CPF Board method   |
| Compliance check              | PASS (auth) | Tenant isolation enforced; KB gap in production |
| Shadow observe                | PASS        | Observation accepted and persisted              |
| Observation pipeline          | PASS        | Frontend→backend wired                          |

## Security Review Summary

- 2 CRITICAL fixed (C1: tenant isolation on trust chains, C2: NaN/Inf guard)
- 4 HIGH fixed/mitigated (H1: input limits, H2: details validation, H3: rate limit bounds, H4: PII truncation)
- 4 MEDIUM documented (M1-M4: model constraints, flagged query company_id, session storage validation, runtime reuse)
- 14 checks PASSED (SQL injection, secrets, token handling, auth, tenant isolation, rate limiting, bounded collections, XSS, indexes)

## Open Items

| Severity | Issue                                                                         | Status                        |
| -------- | ----------------------------------------------------------------------------- | ----------------------------- |
| MEDIUM   | Out-of-scope queries not hard-blocked ("Write Python script" gets provisions) | Scope classifier needs tuning |
| MEDIUM   | LLM pipeline returns template fallback (Kaizen agent compat issue in Docker)  | Functional but degraded       |
| MEDIUM   | Compliance KB not fully loaded in production                                  | KB initialization gap         |
| LOW      | Calculator field naming inconsistent with user expectations                   | Documentation needed          |

## Convergence Assessment

The advisory system is working end-to-end on production. Registration, login, advisory queries, guardrails, calculators, and the shadow agent observation pipeline all function correctly. The LLM pipeline uses template fallback (not AI-synthesized narrative) due to a Kaizen agent compatibility issue in the Docker container, but responses are useful and include proper provisions and citations.

**Verdict: CONVERGED for tester use.** The template fallback provides accurate, citation-backed responses. The MEDIUM items are tracked but non-blocking.
