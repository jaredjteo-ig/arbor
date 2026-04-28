# Session 4 — Architectural debt + polish (~25 hr)

**Goal:** the codebase stops accumulating technical debt that future sessions trip over. Splits the two oversized routers; closes the deferred polish items (full i18n coverage, daily cron, drag-and-drop); adds the test infrastructure that round-12 #10 identified.

**Source findings:** `04-validate/round-13-code-review.md` Top 3 + remaining "future work" notes from clusters 9, 11/12, 14.

**Test gate:** 2380 (post-S3) baseline. This session is high-risk-of-regression; convergence requires zero new failures.

---

## S4-T1: recruitment.py architectural split [r13 code-review]

- **What:** `recruitment.py` is 3,382 lines after T-R054 + T-R055. Hard to navigate, hard to review, every red-team round flags it.
- **Approach:** split into 4 sibling modules at the same import path; export the same `router` object from a thin orchestrator. Zero behaviour change — pure refactor.
- **Files:**
  - `src/hr_advisory/api/routers/recruitment/__init__.py` — assembles the master router from sub-routers.
  - `src/hr_advisory/api/routers/recruitment/jobs.py` — listings, public apply, careers.
  - `src/hr_advisory/api/routers/recruitment/candidates.py` — CRUD, stage transitions, hire.
  - `src/hr_advisory/api/routers/recruitment/interviews.py` — schedule, update, feedback, calendar hooks (T-R055).
  - `src/hr_advisory/api/routers/recruitment/offers.py` — generate, send, accept.
  - `src/hr_advisory/api/routers/recruitment/scorecards.py` — T-R054 endpoint.
  - `src/hr_advisory/api/routers/recruitment/_helpers.py` — shared private functions.
- **Acceptance:**
  - Every route reachable at the same path as before.
  - Full unit + regression suite passes unchanged.
  - Import statement migrations: every other file's `from hr_advisory.api.routers.recruitment import ...` keeps working via the `__init__` re-export.
- **Risk:** **HIGH.** Big diff with no behaviour change is the riskiest kind — if a single route gets dropped during the move, the corresponding test will fail loudly, but a stale import in some unrelated path could be silent. Mitigation: run the full suite after every sub-module move.

## S4-T2: onboarding.py architectural split [r13 code-review]

- **What:** `onboarding.py` is 4,060 lines.
- **Approach:** same as S4-T1.
- **Sub-modules:**
  - `templates.py` — template + module + step CRUD, Excel import.
  - `assignments.py` — assign, list, my-progress, step completion, document upload.
  - `preboarding.py` — preboarding tasks + reminders.
  - `surveys.py` — pulse surveys + analytics + milestones.
  - `_helpers.py` — shared.
- **Acceptance:** identical to S4-T1.
- **Risk:** HIGH. Same pattern as S4-T1.

## S4-T3: i18n full coverage [round-9 polish]

- **What:** cluster 9 shipped the i18n scaffold but only 2 surfaces (navbar + my-payslips) use `t()`. The other 30+ pages are English-only.
- **Files:**
  - Roughly 30 `apps/web/src/app/(dashboard)/*/page.tsx` files: replace hardcoded strings with `t()` calls.
  - `apps/web/src/lib/i18n/{en,zh-CN,ms-MY,ta-SG}.json` — add ~500 new translation keys.
- **Approach:** ship in batches of 5 pages per agent invocation. Each page: identify all user-visible strings, add to en.json with stable keys (`page.section.label`), translate to zh-CN/ms-MY/ta-SG using the same idiomatic Singapore-HR vocabulary cluster 9 established.
- **Acceptance:**
  - At least the 10 highest-traffic pages (dashboard, advisory, my-leave, my-claims, my-attendance, my-onboarding, employees, recruitment landing, settings, compliance) fully translated.
  - Manual test: switch locale → spot-check each page renders no English fallbacks.
- **Risk:** low. Mechanical work but voluminous. Can be split across multiple agents in parallel.

## S4-T4: Daily cron for overdue reminders [r13 polish]

- **What:** `POST /onboarding/reminders/send-overdue` exists but has no scheduler. Customer admins have to remember to hit it manually.
- **Files:**
  - Use the existing Kailash task queue infrastructure (`KAILASH_DATABASE_URL` task queue) OR a small `celery-beat` config.
  - New `src/hr_advisory/scheduled/onboarding_reminders.py` — daily 09:00 SGT job iterates all companies with active assignments and triggers the existing endpoint.
  - Persist `last_reminded_at` on `OnboardingStepProgress` so the daily job doesn't double-send within 24h.
- **Acceptance:**
  - Cron runs once per day; `last_reminded_at` debounces.
  - Manual integration test on the local stack.
- **Risk:** med — requires deciding on scheduler infra (task queue vs cron container vs systemd timer).

## S4-T5: Drag-and-drop reorder on template builder [r13 polish]

- **What:** cluster 11 shipped numeric `sort_order` input. Native UX is drag-and-drop.
- **Files:**
  - `apps/web/src/app/(dashboard)/onboarding/templates/[id]/page.tsx` — wrap module / step lists in `react-beautiful-dnd` (or `@dnd-kit/sortable`). On drop, call existing reorder endpoints.
- **Acceptance:** drag a module up/down, drop, persist; page reload shows the new order.
- **Risk:** low.

## S4-T6: CLI/MCP smoke test [round-12 #10]

- **What:** the multi-channel handlers in `platform.py` were silently broken once (the `_lookup_provisions` ImportError) until cluster 0 surfaced it. A smoke test would have caught it the same day.
- **Files:**
  - `tests/integration/test_cli_mcp_handlers.py` (new) — invoke each `app.handler(...)` registered in `platform._register_handlers` with a minimal payload. Assert the response is a dict (not an exception) and includes the documented keys.
- **Acceptance:** all 3 handlers (`advisory_query`, `compliance_check`, `search_kb`) return well-formed responses; test runs in CI.
- **Risk:** low.

## S4-T7: tz boundary integration test for shadow/briefing [r13 medium]

- **What:** T215 fixed datetime tz-mismatch in `routers/onboarding.py` but `shadow/briefing.py` (T208) reads onboarding rows and renders briefing — and is never tested with tz-aware data.
- **Files:**
  - `tests/integration/test_briefing_tz_boundary.py` — seed an OnboardingAssignment with `due_date` in tz-aware ISO; call the briefing endpoint; assert no tz error and the due-date renders correctly.
- **Risk:** low.

---

## Implementation order

This session is the riskiest — splits and broad i18n coverage both touch a LOT of files. Recommended sequence:

**Phase 1 (parallel, low risk):**

- Agent A: S4-T6 + S4-T7 (small test additions; isolated)
- Agent B: S4-T5 (drag-drop; touches one file)

**Phase 2 (parallel, high risk — needs full convergence after each):**

- Agent C: S4-T1 (recruitment.py split)
- Agent D: S4-T2 (onboarding.py split)
- After both: full pytest run; if any failure → revert that split, file as deferred.

**Phase 3 (sequential, medium risk):**

- S4-T3 i18n full coverage (multiple parallel agents, 5 pages each).
- S4-T4 daily cron (depends on infra decision).

## Acceptance for the session

- 2380 → ≥2400 tests passing.
- recruitment.py + onboarding.py both under 1,200 lines per sub-module.
- i18n: 10 highest-traffic pages fully translated × 4 locales.
- Daily cron triggers in dev stack.
- CLI/MCP smoke test in CI.

## Notes on risk

- S4-T1 + S4-T2 are the highest-risk items in the entire 4-session plan. If either causes a regression that takes more than an hour to fix, **revert the split, ship the rest, defer the split to its own focused session**.
- I18n work is voluminous but mechanically safe. Worst case: a translation is awkward and gets revised later.
