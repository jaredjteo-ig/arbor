# Cluster 2 — Backlog Security (B08, B09, B11)

**Completed**: 2026-04-28
**Source**: `active/backlog-red-team-findings.md`
**Test gate**: 2090 passed, 3 pre-existing failures (carried from cluster 1, not regressions). See `.test-results`.

---

## Summary

Three security backlog items from round 11. Two were already fixed at HEAD;
B11 (rate limiting on 13 routers) needed real work — 20 endpoints across
claims/appraisals/projects gained `check_rate_limit` calls. Coverage now
fully closed across all 11 in-scope routers (12th, `reports.py`, is read-only).

---

## TODO-B08 — Sanitize error messages in API responses ✅ already fixed

- **Priority**: Medium
- **Source**: Round 11, S-H2
- **Originally listed files**: `integrations.py`, `admin.py`, `llm_config.py`, `settings.py`
- **State at HEAD `3440ee0`**: All four files already use sanitized error messages.
  The remaining `str(exc)` sites in `auth.py`, `learning.py`, `calculator.py`
  catch `ValueError`/`KeyError` raised by validation services — those messages
  are intentionally user-facing ("Email is required", "Password must be at least
  8 characters") and not infrastructure leaks.
- **No regression test added** because the remaining `str(exc)` sites are
  intentional; an over-aggressive pin would block legitimate validation errors.

---

## TODO-B09 — Rate limit Google OAuth exchange endpoint ✅ already fixed

- **Priority**: Medium
- **Source**: Round 11, M-5
- **File**: `src/hr_advisory/api/routers/auth.py:672`
- **State at HEAD `3440ee0`**: `google_exchange` calls `_check_auth_rate_limit(request)`
  before any other logic. IP-keyed, 5 requests / 60s window — same protection as
  `/auth/login`, `/auth/register`, `/auth/refresh`. No work needed.

---

## TODO-B11 — Add rate limiting to 13 routers missing it ✅ fixed

- **Priority**: Medium
- **Source**: Round 11, M-8
- **State at start of cluster**: 12 of 13 listed routers had `check_rate_limit`
  imported and partially wired; 20 specific endpoints across claims, appraisals,
  and projects still lacked the call. (`reports.py` is read-only; the round 11
  list included `clients` which has since been retired.)
- **Fix**: Added `check_rate_limit(f"<action>:{user_id}", max_requests=N, ...)`
  to 20 endpoints. Caps tuned by op: 30/min routine, 60/min for state-transition
  burst (approve/reject), 20/min for destructive (archive/delete) + uploads.
- **Webhook endpoint** (`integrations.receive_webhook`) intentionally uses
  `_check_webhook_rate(client_ip)` instead — webhooks have no user_id; IP-based
  is the correct mechanism.
- **Regression test**: `tests/regression/test_b11_rate_limit_coverage.py` —
  12 tests, AST-scans every covered router's write endpoints and asserts a
  rate-limit call is present.

### Per-router count (post-fix)

| Router       | Writes | Rate-limited | Notes                   |
| ------------ | ------ | ------------ | ----------------------- |
| claims       | 11     | 11           | added 6                 |
| appraisals   | 9      | 9            | added 4                 |
| shifts       | 10     | 10           | already complete        |
| projects     | 18     | 18           | added 10                |
| banking      | 1      | 1            | already complete        |
| alerts       | 2      | 2            | already complete        |
| calculator   | 3      | 3            | already complete        |
| compliance   | 2      | 2            | already complete        |
| admin        | 7      | 7            | already complete        |
| integrations | 14     | 14           | webhook uses IP limiter |
| kb           | 1      | 1            | already complete        |

### Files changed

- `src/hr_advisory/api/routers/claims.py`
- `src/hr_advisory/api/routers/appraisals.py`
- `src/hr_advisory/api/routers/projects.py`
- `tests/regression/test_b11_rate_limit_coverage.py` (new)

### Note on production-readiness

The underlying `check_rate_limit` is in-memory per-process. In a multi-worker
or multi-container deploy, each process has its own counters — so the effective
cap is N × the configured cap with N workers. T-RX07 (Redis-backed rate
limiter) is the proper fix for that and remains tracked separately.
