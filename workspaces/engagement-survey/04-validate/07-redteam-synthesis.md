# Master Red-Team Synthesis — Engagement Survey M0-M6

Four red-team passes ran in parallel:

1. `03-security-redteam.md` — security-reviewer: 7 H + 8 M + 7 L + 10 INFO
2. `04-failure-mode-redteam.md` — deep-analyst: 13 H + 14 M + 9 L = 36 findings
3. `05-value-redteam.md` — value-auditor: 6-promise scorecard + 6 demo-day gotchas
4. `06-code-quality-redteam.md` — intermediate-reviewer: 1 CRITICAL + 4 HIGH + medium pile

**Total cross-rated findings: 1 CRITICAL + ~24 HIGH + ~30 MEDIUM + ~20 LOW.**

The same root causes were independently surfaced by multiple agents — those are the ones that ship-block.

## Convergent ship-blockers (multiple agents flagged)

These are the items where two or more red-team passes independently arrived at the same finding. They block P1 ship.

### B1 [CRITICAL] — Direct-SQL identifier interpolation in `dataflow_crud._list_records_direct_sql`

**Flagged by:** security (H1), failure-mode (F1.1), code-quality (#1 top fix)

`f"SELECT * FROM {table}"` and `f"{k} = %s"` interpolate `table` (from `_model_to_table()`) and `k` (filter dict keys) directly into SQL without identifier validation. No live exploit today (callers pass class-name literals), but per `rules/infrastructure-sql.md` Rule 1 this MUST validate via `^[a-zA-Z_][a-zA-Z0-9_]*$` regex. ~10 LOC fix.

**File:** `src/hr_advisory/services/dataflow_crud.py:122-180`.

### B2 [HIGH] — Manager view self-exclusion broken for pseudonymous tier

**Flagged by:** failure-mode (F7.1), value-audit (Promise 3 partial)

Filter `employee_id != manager_id` never excludes the manager when `employee_id=0` (pseudonymous post-submit). Round-1 anonymity invariant violated. Self-exclusion must use **pseudonym** computed from manager's (company, employee_id, survey_id) tuple. Anonymous tier needs a UI banner acknowledging self-exclusion is impossible.

**File:** `src/hr_advisory/api/routers/engagement_surveys.py:1804-1875`.

### B3 [HIGH] — Termination sweep gap for pseudonymous

**Flagged by:** failure-mode (F9.1)

`engagement_termination.py:47-51` filters by `{"employee_id": int(employee_id)}` — pseudonymous-submitted rows have `employee_id=0`, never matched. Today masked by Z04 ("don't void submitted") but any future policy change exposes the bug. Add backup `survey_id + cohort_attrs` lookup AND pin the boundary with a regression test.

**File:** `src/hr_advisory/services/engagement_termination.py:46-58`.

### B4 [HIGH] — Seed-script plaintext secret vs service ciphertext

**Flagged by:** security (M2), failure-mode (F10.2)

`backfill_demo_engagement_surveys.py:215-220` stores `secrets.token_hex(32)` as plaintext into `Company.engagement_secret_v1`. The service path calls `decrypt_field()` and only "works" because `decrypt_field` swallows Fernet failures and returns input as-is (a separate fail-closed violation). The moment anyone fixes `decrypt_field` to fail-loudly, every seeded pseudonym mismatches the runtime-computed one and trend joins silently fail.

**Fix:** seed must call `encrypt_field()` before storing.

**Files:** `scripts/backfill_demo_engagement_surveys.py:215`, `src/hr_advisory/security/encryption.py:50` (related: `decrypt_field` swallows failures).

### B5 [HIGH] — PDPA admin-access logging stubbed

**Flagged by:** security (H3), code-quality (#4 / Concern 3)

`engagement_surveys.py:1190` is a TODO disguised as a comment. Round-2 H12 / Z16 explicitly required wiring `_log_pdpa_access()` for every endpoint exposing identified `employee_id`. The helper exists in `employees.py:729-760` and just needs to be called.

**Affected endpoints:** `GET /surveys/{id}/responses` (admin reads), CSV export (P2), expand-detail.

### B6 [HIGH] — voided_count double-counts under partial failure

**Flagged by:** code-quality (Concern 4b)

`engagement_termination.py:84-101`: if 3 of 5 individual void updates fail, the survey's `voided_count` still bumps by 5 (the original `pending` length, not the success count). Track `successfully_voided_by_survey: dict[int, int]`.

### B7 [HIGH] — `create_action` linked-goal silent failure

**Flagged by:** code-quality (Concern 4a)

`engagement_surveys.py:1992-1996`: try/except returns success with `linked_goal_id=0` on goal-create failure. Client thinks goal was created, sees 0 in response, no error indicator. Violates `rules/no-stubs.md` Rule 3.

**Fix:** propagate `goal_create_failed: True` OR rollback the action with `dataflow_crud.delete("EngagementAction", id)`.

## Demo-day blockers (value-auditor)

Distinct from code defects but ship-blocking for P1 demo:

### D1 — Manager view doesn't work for SG SMEs at 28-employee scale

**This is the single biggest product-fit risk.** With 6-report manager + 78% submission + n>=5 self-exclusion gate, the suppression message fires ~60% of the time. A buyer running through manager view with a real team gets the friendly "your team is too small" message and registers "this product wasn't built for me."

**Mitigation paths (decision required):**

1. Show themes-only when n=3 or 4 (PDPA-defensible)
2. Lower MIN_COHORT_SIZE to 3 for manager view (legal review needed)
3. Reframe as quarterly rollup, not weekly habit
4. Auto-bundle small teams ("skip-level rollup")

### D2 — Action accept modal creates verbose goal title

Demo seed shows beautiful goal: "Q2 Engineering L&D — every IC has approved budget by end of Q2". Live demo flow produces "Engagement: Launch L&D pilot with a per-head learning budget for the cohort." **Demo and live diverge** — exactly what a CFO will spot.

**Fix:** add a "Goal title" input field to the modal with a suggested concise default.

### D3 — Loop-closing fallback can structurally lie

"HR has seen this — actions in progress" shows whenever any closed pulse has a top theme, regardless of whether HR has actually opened the dashboard. **Fix:** track HR `viewed_at` on the survey; only flip to "in progress" once HR has opened the detail page.

### D4 — Loop-closing card uses substring match for action lookup

`compute_loop_closing_payload` finds an action by substring of theme inside `finding_summary` or `suggested_action_text`. Brittle. Works on seed because strings match; in production silently fails to surface valid actions. **Fix:** match on `cohort_label` + indexed theme list, not free-text substring.

## Cross-cutting findings

### C1 [HIGH] — Frontend `Stat` component duplicated 3x

**Flagged by:** code-quality (#3 top fix). 30 minutes to extract; removes ~30 LOC.

### C2 [HIGH] — Cross-tenant `ad_hoc_employee_ids` guard missing on launch

**Flagged by:** security (H4). Preview has the check; launch does not. Single-tenant per server (per recent decision) makes this defense-in-depth, but still worth wiring.

### C3 [HIGH] — CSRF guard too permissive

**Flagged by:** security (H2). Only rejects `Origin: null`. Should compare against `settings.cors_origins`. Mitigated by Bearer auth; belt-and-braces.

### C4 [HIGH] — Idempotency dead code path on already-submitted

**Flagged by:** security (H5). When client supplies an Idempotency-Key on a submit that's already submitted, the comparison against the stored key always fails (the stored key was server-derived). Fix: server stores the supplied key when given one.

### C5 [HIGH] — `engagement_surveys.py` is 1700+ lines

**Flagged by:** code-quality (#5 / Concern 1). Split into 3 routers along M2 / M3-admin / M3-employee seams. Maintainability not correctness.

### C6 [MEDIUM] — Trend endpoint scans 24 surveys × full aggregate

**Flagged by:** failure-mode (F6.1). Will blow p95<800ms budget on production data. Cache or materialise.

### C7 [MEDIUM] — Trend endpoint doesn't support `manager:42` cohort syntax

**Flagged by:** failure-mode (F6.2). Manager dashboard's "team trend" silently shows company trend instead. Add manager-axis to `_build_aggregate`.

### C8 [MEDIUM] — Test state leak: `test_submit_voided_response_returns_410` skips silently if order changes

**Flagged by:** code-quality (Concern 6). Each test should launch its own fresh survey. Skip is invisible in CI.

### C9 [MEDIUM] — `rose-*` colors hardcoded; rest use design tokens

**Flagged by:** code-quality (Concern 10). Add `--color-rose-XX` to globals.css OR document the intentional brand-accent choice.

### C10 [MEDIUM] — `email_delivery_status` never set to "partial"

**Flagged by:** code-quality (Concern 4c). Field exists for Z09 saga shape but launch handler never computes partial state. Feature gap.

## Recommended fix order

### Phase 1: Critical correctness (must fix before any deploy)

| #   | Item                                            | Owner   | LOC |
| --- | ----------------------------------------------- | ------- | --- |
| 1   | B1 — SQL identifier validation in dataflow_crud | backend | ~10 |
| 2   | B2 — Manager view self-exclusion via pseudonym  | backend | ~30 |
| 3   | B3 — Termination sweep + regression test        | backend | ~40 |
| 4   | B4 — Seed-script encrypt_field on secret        | scripts | ~5  |
| 5   | B5 — PDPA log wiring                            | backend | ~20 |
| 6   | B6 — voided_count partial-failure fix           | backend | ~15 |
| 7   | B7 — create_action linked-goal explicit failure | backend | ~10 |

**Estimated: 1 day backend.**

### Phase 2: Demo readiness (must fix before P1 ship demo)

| #   | Item                                                  | Owner              | LOC    |
| --- | ----------------------------------------------------- | ------------------ | ------ |
| 8   | D1 — Manager view SME-fit (decision + implementation) | product + backend  | varies |
| 9   | D2 — Goal title input on accept modal                 | frontend           | ~30    |
| 10  | D3 — HR viewed_at + loop-closing copy                 | backend + frontend | ~50    |
| 11  | D4 — Loop-closing match on cohort_label not substring | backend            | ~20    |

**Estimated: 1-2 days depending on D1 path chosen.**

### Phase 3: Hardening (can ship P1 first, follow-up)

C1 (Stat extraction), C2 (cross-tenant guard on launch), C3 (CSRF allowlist), C4 (idempotency-key storage), C5 (router split), C6 (trend caching), C7 (manager cohort), C8 (test state leak), C9 (color tokens), C10 (email_delivery_status).

**Estimated: 2-3 days.**

## What's actually shippable today

P1 backend is functionally complete with the right architecture, sound anonymity invariants, and good test coverage **except** for the convergent ship-blockers above. The value spine (trend → action → linked goal → loop-closing) is real and demo-able with the seeded data.

**Verdict:** Don't ship M7 (P1 production deploy) until Phase 1 is in. Phase 2 is needed for a credible demo. Phase 3 is shippable as M10 polish.

The instinct in round-3 (action loop, manager view, trend hero, in-app only) was the right call. Execution is mostly there. The 7 convergent ship-blockers are concrete and total ~1 day of backend work.

## Cross-reference

- `03-security-redteam.md` — full security findings + remediation code
- `04-failure-mode-redteam.md` — full failure-mode findings + concurrency analysis
- `05-value-redteam.md` — buyer perspective + per-promise scorecard
- `06-code-quality-redteam.md` — code quality + maintainability findings
- `02-todo-redteam-findings.md` — round-2 plan-level findings (closed in Z amendments)
- `00-redteam-findings.md` — round-1 plan-level findings (closed in Z + round-3 product revision)
