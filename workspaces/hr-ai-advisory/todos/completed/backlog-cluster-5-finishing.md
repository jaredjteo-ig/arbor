# Cluster 5 — Backlog Finishing + Onboarding Foundation

**Completed**: 2026-04-28
**Sources**: `active/backlog-red-team-findings.md`, `active/recruitment-redteam-fixes.md`, `active/onboarding-feature.md`
**Test gate**: 2100 passed, 3 pre-existing failures (carried, not regressions). See `.test-results`.

---

## Summary

Five items audited; one needed real work. The other four were already shipped
at HEAD `3440ee0`. Real work: T-RX07 Redis-backed rate limiter (deep-analyst's
HIGH finding from round 12 — fixes the multi-worker quota dilution).

---

## TODO-B16 — Implement turnover analysis report ✅ already fixed

- **Priority**: Low
- **Source**: Round 11, L-1
- **State at HEAD `3440ee0`**:
  - Backend: `routers/reports.py:31` — `GET /reports/turnover` returns
    monthly hires/terminations, headcount, turnover rate, per-domain breakdowns,
    and an overall rate.
  - Frontend: `apps/web/src/app/(dashboard)/reports/page.tsx` already imports
    `TurnoverReportResponse`, has the report card metadata (line 56-58), wires
    `reportsApi.turnover` (line 370), and renders a full `TurnoverReportViewer`
    (line 580+).

---

## TODO-B21 — Synchronize headcount between profile and employees ✅ already fixed

- **Priority**: Low
- **Source**: Round 11, L-4
- **State at HEAD `3440ee0`**: `routers/profile.py:261` returns
  `live_total if live_total > 0 else profile_total` for the headcount field.
  This is the auto-compute approach the brief proposed — the live count from
  the actual Employee table is preferred, with the stored profile value as a
  fallback for new companies that haven't onboarded employees yet.

---

## T193 — Onboarding data models ✅ already fixed

- **Source**: `active/onboarding-feature.md`
- **State at HEAD `3440ee0`**: All six models exist in
  `src/hr_advisory/models/company_user.py:2678-2799`:
  - `OnboardingTemplate` (line 2678)
  - `OnboardingModule` (line 2700)
  - `OnboardingStep` (line 2724)
  - `OnboardingAssignment` (line 2748)
  - `OnboardingStepProgress` (line 2774)
  - `PreboardingTaskInstance` (line 2799)

---

## T194 — Onboarding API endpoints ✅ already fixed

- **Source**: `active/onboarding-feature.md`
- **State at HEAD `3440ee0`**: `src/hr_advisory/api/routers/onboarding.py` has
  3,820 lines and 40 endpoints across template/module/step CRUD, assignment,
  employee self-service, and pre-boarding flows.

---

## T-RX07 — Redis-backed rate limiter ✅ fixed

- **Source**: `active/recruitment-redteam-fixes.md`
- **Severity**: MEDIUM (security — affects public endpoint protection in
  production multi-worker deployments). Also flagged as HIGH by deep-analyst
  in round-12 deep-analysis.
- **State at start**: `middleware/rate_limit.py` was in-memory only. In a
  multi-worker / multi-container deploy, each process counted independently,
  so the effective cap was N × the configured cap.
- **Fix**: Rewrote the limiter to use Redis as the primary backend with
  graceful in-memory fallback.
  - **Redis path**: `INCR rate:<key>` + `EXPIRE rate:<key> <window> NX` in
    a single pipeline. The `NX` flag means TTL is set only on the first
    increment — subsequent increments don't reset the window. Fixed-window
    semantics; standard production approach.
  - **Fallback**: If `REDIS_URL` is unset, the package isn't installed, the
    initial PING fails, or any operation later raises a Redis error, the
    limiter falls back to the existing in-memory deque-bounded sliding
    window. The fallback is logged loudly (per zero-tolerance rule —
    failures must never silently disable rate limiting).
  - **Backoff**: 30-second window after a failure before retrying Redis.
    Prevents pounding on a dead server.
  - **`reset_rate_limit_state()`** exposed for tests.
- **Compatibility**: All existing call sites (12 routers) work unchanged —
  same `check_rate_limit(identifier, max_requests, window_seconds, action_name)`
  signature. The only test-suite change is updating
  `tests/unit/test_rate_limit.py`'s autouse fixture to point `REDIS_URL`
  at a closed port (forces the in-memory branch the existing tests target).
- **Regression tests**: `tests/regression/test_b_cluster_5_redis_rate_limit.py`
  - `test_t_rx07_redis_backend_enforces_limit_and_persists_count`
  - `test_t_rx07_falls_back_to_in_memory_when_redis_unreachable`
  - `test_t_rx07_backs_off_after_failure`

### Note on `guardrails.check_rate_limit`

A separate `check_rate_limit` lives in `hr_advisory.workflows.guardrails`
(used by `auth.py` and recruitment `public_apply`). It's still in-memory.
Migrating it to share the same Redis backend is a small follow-up; this
cluster scoped to the primary middleware limiter as the brief specified.

### Files changed

- `src/hr_advisory/api/middleware/rate_limit.py`
- `tests/unit/test_rate_limit.py`
- `tests/regression/test_b_cluster_5_redis_rate_limit.py` (new)
