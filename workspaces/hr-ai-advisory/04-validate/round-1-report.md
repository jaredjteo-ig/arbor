# Red Team Round 1 — Validation Report

**Date**: 2026-03-12
**Agents deployed**: 6 (security-reviewer, gold-standards-validator, testing-specialist, coc-expert, value-auditor, deep-analyst)

---

## Summary

4 of 6 agents completed (value-auditor and deep-analyst were interrupted by context limit). Key findings:

- **4 CRITICAL security issues** — all fixed in Round 1
- **1 CRITICAL integration gap** — advisory pipeline was not wired to safety chain — fixed
- **Testing gaps** — E2E test imports broken — fixed
- **Calculator endpoints** — using placeholder math instead of real calculators — fixed

## Findings and Fixes

### CRITICAL — Security (all fixed)

| ID  | Finding                                                                                    | Fix                                                                                                                   |
| --- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| C1  | JWT secret defaults to `"change-this-in-production"` with no production guard              | Added `RuntimeError` in `get_settings()` that blocks startup if production uses default secret                        |
| C2  | Admin endpoints completely unauthenticated                                                 | Added `require_role("owner", "hr_manager")` dependency to all 11 admin endpoints                                      |
| C3  | All API endpoints (advisory, calculator, compliance, document, search, KB) unauthenticated | Added `get_current_user` dependency to all protected endpoints. Template listings and KB reference data remain public |
| C4  | CORS allows wildcard headers (`*`)                                                         | Changed to explicit allowlist: `["Authorization", "Content-Type", "X-Request-ID"]`                                    |

### CRITICAL — Integration (fixed)

| ID  | Finding                                                                                                                                                  | Fix                                                                                                                                                                                                                                                                                               |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I1  | Advisory `/query` endpoint returns hardcoded placeholder — does not invoke guardrails, EATP, citations, disclaimers, anti-amnesia, or response screening | Rewrote advisory router with full 12-step safety chain: sanitise → rate limit → screen query → EATP genesis → anti-amnesia injection → domain detection → KB lookup → citation validation → response generation → confidence escalation → response screening → disclaimer + trust chain recording |
| I2  | Calculator endpoints use placeholder math (e.g., `salary * 0.17`) instead of real calculator implementations                                             | Wired CPF endpoint to `calculate_cpf_contributions()` with full `CPFInput` mapping. Wired leave endpoint to `calculate_leave_entitlement()` with full `LeaveInput` mapping                                                                                                                        |
| I3  | Security headers (HSTS, CSP, X-Frame-Options, etc.) defined in `validation.py` but never applied to HTTP responses                                       | Added FastAPI middleware in `platform.py` that injects all `SECURITY_HEADERS` into every response                                                                                                                                                                                                 |
| I4  | Admin router not registered in platform                                                                                                                  | Added `admin_router` to `_register_routers()`                                                                                                                                                                                                                                                     |
| I5  | Multi-channel handler returns placeholder without guardrails                                                                                             | Added query screening to `advisory_query_handler`                                                                                                                                                                                                                                                 |

### HIGH — Testing (fixed)

| ID  | Finding                                                                     | Fix                                                                                                                                                |
| --- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | E2E calculator tests import from `hr_advisory.calculators.cpf` (wrong path) | Fixed to import from `hr_advisory.workflows.calculators.cpf_calculator` with correct class names (`CPFInput`, `calculate_cpf_contributions`, etc.) |

### Remaining items for Round 2

- 29 modules still lack unit tests (Tier 1)
- Guardrails, trust chain, and citation validator need dedicated unit tests
- Admin metrics endpoint returns hardcoded fake numbers
- KB endpoints return placeholder data (pending DataFlow wiring)
- Server-side token revocation not implemented (logout is client-side only)

---

## Files Modified

| File                                        | Change                                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| `src/hr_advisory/config/settings.py`        | Production JWT guard                                                    |
| `src/hr_advisory/api/routers/admin.py`      | Auth on all endpoints                                                   |
| `src/hr_advisory/api/routers/advisory.py`   | Full safety chain integration                                           |
| `src/hr_advisory/api/routers/calculator.py` | Real calculator wiring + auth                                           |
| `src/hr_advisory/api/routers/compliance.py` | Auth added                                                              |
| `src/hr_advisory/api/routers/document.py`   | Auth on write endpoints                                                 |
| `src/hr_advisory/api/routers/search.py`     | Auth added                                                              |
| `src/hr_advisory/api/routers/kb.py`         | Auth on protected endpoints                                             |
| `src/hr_advisory/api/routers/profile.py`    | Auth verified                                                           |
| `src/hr_advisory/api/platform.py`           | Security headers middleware, CORS fix, admin router, handler guardrails |
| `tests/e2e/test_calculator_flows.py`        | Fixed imports to correct module paths                                   |
