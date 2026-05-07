# M6 — Demo seed + regression tests (round-3 revised)

**Source plan:** `02-plans/03-frontend-and-phasing.md` §Test discipline, plus `02-plans/04-product-revision-round3.md`.

Round-3 changes: drop public-token tests (engagement is in-app only), add trend-chart seed (6 prior pulses), add action-loop seed (one accepted action with linked goal), add manager-view tests (self-exclusion 3-row matrix).

Make the demo data reach into the killer flow — without seed data showing the cross-stage correlation AND the closed action loop, the buyer demo falls flat.

## T60 — `backfill_demo_engagement_surveys.py` (round-3 expanded)

- **What:** New script under `scripts/`. Idempotent (presence-check on first survey row).
- **What it seeds (round-3 expanded for trend hero + action loop):**
  1. Two engagement-survey templates per company (Q12 paraphrase, monthly_pulse) — shipped library, idempotent seed.
  2. **Six prior closed pulses** spanning the last 6 months (one per month) for trend-hero rendering. Anonymity_tier=pseudonymous, all 28 employees responded each time. Engineering trends 3.8 → 3.7 → 3.5 → 3.3 → 3.2 → 3.2 (the demo's "engagement collapse" signal). Sales trends roughly flat at 4.3-4.5. Fixed RNG seed.
  3. **One open pulse** from 7 days ago (closes in 7 more days), anonymity_tier=pseudonymous, 22/28 responses. Lily Phang has NOT yet responded.
  4. **Critical for cross-stage flow (P2):** the 3 employees who resigned this quarter (per existing exit-interview backfill — Rajesh Kumar + 2 others) have low Likert in the recent pulses. Their pseudonyms (HMAC) map to the same hash as their `EmploymentEvent RESIGNED` rows.
  5. **Action loop seed (round-3 NEW):** one `EngagementAction` row already accepted — `cohort_label="Engineering"`, `finding_summary="Q4 growth scored 2.1/5 — the lowest of all questions"`, `suggested_action_text="Launch L&D pilot with budget per IC"`, `status="accepted"`, `linked_goal_id=<seeded goal in Goals module>`, `next_pulse_question="How clear is your career path here?"`. This drives the loop-closing card on Lily's `/my-engagement-surveys` AND the "already-accepted" section of the action panel.
  6. **Linked goal seeded** in existing Goals module: title "Q2: Engineering L&D — every IC has approved budget by end of Q2", owner = Grace.
  7. Two scheduled pulses — one monthly recurring (paused), one quarterly active.
- **Theme distribution:** seeded responses cite "growth", "manager", "workload" in proportions matching exit-interview themes.
- **Acceptance:** running on fresh demo DB produces:
  - **Trend hero** renders 6 pulses with the descending Engineering line.
  - Engagement overview shows "Latest 3.2 / 5 · 22 of 28 · eNPS +18 · 6-pulse trend ↓".
  - **Action panel** on detail page shows the seeded "L&D pilot" action under "Already accepted".
  - **Loop-closing card** on Lily's `/my-engagement-surveys` shows "Last pulse, your team raised growth → Learning budget pilot launched May 1".
  - **Cross-stage panel (P2)** demonstrates that of 3 resigned employees, 2 scored low on growth.

## T61 — Anonymity invariants regression suite

- **What:** `tests/regression/test_engagement_anonymity.py` covers
  the four invariants from `03-user-flows/02-lily-completes-pulse.md`
  §Anonymity contract:
  1. The Anonymous / Pseudonymous / Identified badge is set
     correctly on the survey + every response.
  2. Submit on an `anonymous` survey zeroes employee_id; submit on
     `pseudonymous` zeroes employee_id and sets pseudonym; submit
     on `identified` keeps employee_id.
  3. Admin response list returns "Anonymous" / pseudonym slug /
     name appropriately.
  4. Aggregator suppresses cells where `n < 5`.
- **Test data:** use a fixture that creates 3 surveys (one per
  tier), 6 responses each, asserts the schema.
- **Acceptance:** all four invariants hold; pinned tests fail loudly
  if the anonymity logic regresses.

## T62 — In-app submit + rate-limit tests (round-3: replaces tokenised submit tests)

- **What:** `tests/regression/test_engagement_in_app_submit.py` pins:
  - Valid Bearer + valid payload → 200.
  - Reused response_id (already submitted) → 409 already_submitted.
  - Idempotency-Key replay (Z08) → 200 with `idempotent_replay: true`, single row.
  - Voided employee (Z21 12-cell matrix subset) → 410 voided across all three anonymity tiers.
  - Closed window → 409 closed.
  - Bad payload (missing required q) → 400 with PII-clean error envelope (Z13).
  - 6 invalid attempts on one response → 429 rate-limited.
  - Cross-origin POST → 403 CSRF (Z11).
  - Cross-user attempt (employee A using their bearer to submit response B's URL) → 403.
- **Removed (round-3):** ~~tokenised public submit tests~~ — engagement has no public route.

## T63 — Cohort resolver + preview tests

- Already covered in M2 T22-T24. List here for traceability.

## T64 — Aggregator anonymity-gate tests

- Already covered in M3 T34. List here for traceability.

## T65 — End-to-end Playwright walks (round-3 expanded)

- **What:** New Playwright spec `tests/e2e/test_engagement_grace_lily.spec.ts` exercising:
  1. Login as Grace.
  2. Open `/engagement`. **Trend hero renders 6 pulses (seeded).**
  3. Open launch wizard, pick monthly_pulse, pick All Active cohort, anonymity_tier=pseudonymous, set name + closes_at, submit.
  4. Land on detail page; response count=0/28 immediately after launch.
  5. Logout. Login as Lily. Check `/my-dashboard` shows pending card. Click Open.
  6. On `/my-engagement-surveys`, **loop-closing card shows seeded "growth → L&D pilot" action**.
  7. Click Start on the new pulse.
  8. Fill in Likert + eNPS + free text + chips. Submit (in-app only).
  9. See thank-you. `/my-engagement-surveys` shows pending=0.
  10. Logout. Login as Grace. Refresh detail page; response count=1/28.
  11. Aggregator shows 1 response visible on Aggregated tab.
  12. **Action panel walk:** scroll to action panel, see suggestions for the lowest-scoring cohort, accept one, create-goal modal opens, accept → linked goal appears in "Already accepted" section.
  13. **Manager-view walk:** logout, login as Tanaka (manager of Engineering). Open `/engagement/team`. See aggregate (n=6, no suppression notice). Logout.
- **Time budgets to assert:**
  - Login + page loads within 5s each.
  - Lily's form fill: scripted with realistic delays; total interaction <90s.

## T66 — Action-loop regression tests (round-3 NEW)

- **What:** `tests/regression/test_engagement_actions.py` covers:
  - HR creates an action with `create_linked_goal=true` → action row exists with `linked_goal_id != 0`; goal row exists in Goals module with the matching title.
  - Action lifecycle: proposed → accepted → resolved with score delta after next pulse closes.
  - Auto-anchoring: an accepted action's `next_pulse_question` is folded into the next pulse of the same template.
  - Manager-view self-exclusion 3-row matrix (Z26): manager+4 reports = suppression; manager+5+self = n=5 visible self-excluded; manager+5 no-self = n=5 visible.
  - Suggested-actions deterministic fallback (M3 T36) when LLM disabled or budget cap trips.

## T66b — Regression test of loop-closing endpoint

- **What:** `GET /my-loop-closing` returns expected payload for
  Lily after seed runs (top_theme="growth", action_taken not null).
- **Edge case:** company with no closed pulses returns null
  payload (card hidden).

## Dependencies

T60 ← T16 (templates seeded first); ← M3 launch endpoint.
T61, T62, T64, T66 ← M3 (endpoints exist).
T65 ← M4 + M5 (frontends shipped).

## Acceptance gate for M6

- Demo seed reproducibly populates 6-pulse trend, the action-loop seed, and (for P2) the cross-stage correlation.
- All anonymity invariants pinned.
- In-app submit reuse / voided / closed all return correct semantic codes.
- Action-loop tests cover create-goal + auto-anchoring + manager self-exclusion.
- Loop-closing endpoint returns expected payload after seed.
- One end-to-end Playwright walk green covering: Grace launch + Lily submit + action panel accept-and-create-goal + manager-view aggregate.
