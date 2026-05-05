# 03 — Post-redteam plan

**Date:** 2026-05-05
**Inputs:**

- `01-analysis/03-gap-analysis.md` — 30+ gaps, top-12 P0
- `02-plans/01-phased-roadmap.md` — 3-phase ~55–67 dev-day roadmap
- `02-plans/02-lifecycle-dashboard-spec.md` — implementer-ready UI spec
- `04-validate/01-redteam-findings.md` — 18 findings (B1/B2/B3 + 4H + 8M + 5L)
- This session's element-level lap — 4 additional findings

This plan turns all of the above into a single ordered execution path. It
is structured as **gates** rather than dates: each gate has a clear
"done" criterion and unblocks the next.

---

## Where we are right now

**Code state on this branch (uncommitted):**

- 17 of 18 redteam findings fixed: B2 + B3 + H1–H4 + M1–M8 + L1–L5.
- 3 of 4 lap findings fixed: NEW-2 (left as cosmetic console-only), NEW-3
  (analytics live computation), NEW-4 (humanized status).
- 1 deferred: **B1** — switch `DEFAULT_LLM_MODEL` off Gemini free tier.
  Owner-side action; ~1 minute to apply.

**New artefacts on disk:**

- 6 backfill / migration scripts (`scripts/backfill_*.py` + 1 ALTER).
- 5 regression tests under `tests/regression/`.
- 1 pre-existing test fix in `tests/unit/test_recruitment_advanced.py`
  (`TestReapplyCandidate` — was stubbing wrong `dataflow_crud` method).

**Local validation:**

- Full unit + regression sweep: 45 pre-existing failures (unrelated test
  drift), **0 new regressions**.
- Playwright full-prod walk: every route 200, every CTA fires, every
  redteam fix visibly resolved on the live local DB.

---

## Gate 0 — Owner-side decisions before deploy

Two decisions block the deploy. Both are 1-minute changes.

| Decision                   | Action                                                                                                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **B1 LLM provider**        | Set `DEFAULT_LLM_MODEL` to `gpt-4o-mini` or `claude-3-5-haiku-latest` in `deploy/.env.prod`. Keys already configured. Smoke-test the advisory chat after restart.         |
| **Bundle vs split commit** | Decide whether to ship the 17+3 fixes as one bundled commit or split B-fixes / H-fixes / M+L fixes. Recommendation: one bundled commit per the local-first deploy memory. |

**Done when:** B1 env var set; commit shape decided.

---

## Gate 1 — Production deploy of the redteam closure

**Sequence (irreversible actions are flagged):**

1. **Snapshot** the local `.test-results` artefact into the workspace.
2. **Commit** all branch changes with a `fix(redteam-round-12)` prefix.
   Conventional-commit body lists: 17 findings fixed, 3 lap findings,
   6 backfills, 5 regression tests.
3. **CI green check** — full matrix on the PR.
4. **Bundle deploy** to `136.110.51.61`:
   - Pull the merged commit on the VM.
   - Run **all 6 backfill / migration scripts on prod**, in this order
     (order matters because the H1 column add precedes the H1 frontend
     filter, and the M5/M7 demo seeds expect the M4 cleanup to have
     happened first):
     1. `scripts/backfill_employee_pass_type.py` (M1)
     2. `scripts/migrate_employee_tracks_attendance.py` (H1 column)
     3. `scripts/backfill_claim_totals.py` (B3)
     4. `scripts/backfill_onboarding_templates.py` (H4)
     5. `scripts/backfill_empty_payroll_drafts.py` (M4)
     6. `scripts/backfill_demo_appraisals.py` (M5)
     7. `scripts/backfill_demo_interview_variety.py` (M7)
   - Restart docker stack.
   - Hit `POST /leave/applications/sweep-stale-pending` once via the API
     (H2). This can be done as the admin from the live site rather than
     by SSH.
5. **Smoke-walk the live site** with Playwright using the same
   route-and-CTA pass that we ran locally. Report any divergence.

**Done when:** every redteam finding (except B1, which the owner toggles
when ready) is verifiably resolved on `136.110.51.61` and the smoke walk
passes.

> **Risk note:** the H1 migration adds a non-null column with a default,
> so no row rewrite stalls. The B3 backfill is a single SQL UPDATE.
> The H4 backfill soft-archives only — never deletes. The M4 cleanup
> deletes `payroll_runs` rows where `gross_pay = 0` across all attached
> payslips, so it cannot remove a real run. Each script is idempotent.

---

## Gate 2 — Phase 1 of the lifecycle roadmap (visualization)

The bug-fix wave is closed. Next deliverable is the buyer-narrative
upgrade: **render the 8-stage Cox lifecycle as a coverage dashboard** so
sales can walk Strategy → Exit on a single page.

**Source spec:** `02-plans/02-lifecycle-dashboard-spec.md` (no wheel
graphic — 4×2 card grid desktop, vertical list mobile).

**Phase 1 deliverables (P1-1 through P1-12 in `01-analysis/03-gap-analysis.md`):**

1. `GET /strategy/lifecycle-dashboard` aggregator endpoint — returns
   hero counters + per-stage coverage + D&I snapshot + activity feed
   from data that already exists.
2. `/strategy/lifecycle` Next.js page rendering the card grid.
3. Stage detail panels (drill-in for each of the 8 stages).
4. Health-pill thresholds per the spec (green ≥ 4/5, amber 3, red ≤ 2).
5. D&I tile (transverse, derived from existing demographic fields).
6. Activity feed (last 14 days of `EmploymentEvent`).
7. **Single ALTER TABLE**: add `Company` employer-brand fields
   (`mission`, `tagline`, `benefits_summary`, `culture_pillars`,
   `team_photos_url`, `glassdoor_url`).
8. Update sidebar to surface a "Strategy" entry above "Dashboard"
   (replaces nothing — additive).
9. Onboarding tour pop-over for first-time admin landing on the page.
10. 2 regression tests (aggregator shape + health-pill thresholds).
11. 1 Playwright E2E test walking the 8 stages.
12. README + docs update with screenshot.

**Estimate:** 10–12 dev-days as scoped in the existing roadmap.

**Done when:** an enterprise buyer (Jennifer Liu / Ricoh stakeholders)
can land on `/strategy/lifecycle`, see all 8 stages with live coverage
data, drill into any stage, and the page reads as the entry point of the
platform rather than the dashboard.

---

## Gate 3 — Phase 2 (closing the largest-gap modules)

These are the modules the redteam + gap analysis flagged as **structurally
absent**, not just rough:

| Module                              | Why it matters                                                                                                                                                         | Models added                                                      |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **L&D foundations** (S5-G1, G2, G6) | Lifecycle stage 5 is the weakest — currently a SkillsFuture lookup only. Buyers expect at minimum: training records, certification expiry, mandatory-training tracker. | `TrainingRecord`, `Certification`, `MandatoryTrainingRequirement` |
| **Recognition** (S6-G1)             | Reward/Recognition/Benefits is one stage; without recognition the segment reads as half-implemented.                                                                   | `Recognition`, `PeerNomination`                                   |
| **Goals / OKR** (S7-G1)             | Performance stage is appraisals-only today. Goals close the in-cycle gap.                                                                                              | `Goal`, `GoalCheckIn`                                             |
| **Exit interview workflow** (S8-G1) | Exit mechanics work but no analytics. Exit interview model unblocks churn analysis.                                                                                    | `ExitInterview`                                                   |

**Estimate:** 25–30 dev-days. **Note:** each new module needs the same
treatment as recruitment got in round-12 — frontend, backend, regression
tests, demo seed, and a one-line lifecycle-dashboard hook so the
Strategy page reflects the new coverage.

**Done when:** average lifecycle coverage rating moves from 3.25/5 to
≥4/5 (per the rubric in `01-analysis/02-current-state-mapping.md`).

---

## Gate 4 — Phase 3 (strategic depth)

Higher-leverage but lower-urgency. Implementing in this order respects
data dependencies (workforce plan refers to skills inventory; succession
refers to skills + retention scoring):

1. `WorkforcePlan` model + Strategy hub authoring UI.
2. `SkillsInventory` per employee.
3. `SuccessionPlan` for critical roles.
4. Retention-risk scoring derived view (read-only — no new PII).
5. Pay-equity dashboard (gender / pass-type pay gap from existing
   payroll data).

**Estimate:** 20–25 dev-days.

**Done when:** the Strategy hub stops being a coverage view and becomes
an authoring surface — owners can write the plan, not just read it.

---

## Cross-cutting items (not gated)

These are continuously useful and don't block the gates above:

- **NEW-2** React "missing key prop" warning in `ClaimsList` — fix when
  next touching that file. Cosmetic only.
- **NEW-1** Playwright/AppInput synthetic-event handling — investigate
  if/when test-runner work resumes. Real-keyboard tests pass.
- **45 pre-existing test failures** unrelated to redteam fixes —
  triage as a separate cleanup task. Not blocking ship.
- **Codify** session-level institutional knowledge into
  `.claude/skills/project/security-patterns.md` after Phase 1 ships
  (round-12 gave us 4–5 new patterns: the cache-bypass-on-recalc rule,
  the defensive-route-guard pattern, the chronological-ordering guard,
  the unique-name helper pattern, the rolling-window UI default).

---

## Open questions for the owner

1. **B1 model choice** — `gpt-4o-mini` (cheap, fast, lower fidelity) or
   `claude-3-5-haiku-latest` (slightly higher fidelity, comparable cost
   on Anthropic)? Recommendation: claude-3-5-haiku for the demo, then
   benchmark against gpt-4o-mini on cost/quality before pilot.
2. **Phase 1 scope sequencing** — ship the 12 deliverables together, or
   release behind a feature flag and roll out per buyer-segment?
3. **Phase 2 module priority** — L&D first or Recognition first? L&D
   has the bigger gap; Recognition has the smaller LOC but bigger
   employee-experience signal for the demo.
4. **Resource plan** — is this all single-threaded (Jared) or do we
   parallelize the L&D and Recognition tracks?

---

## What this plan does NOT cover

- Any commercial coupling, pricing, or partnership work — out of scope
  per `rules/independence.md`.
- Ricoh-specific or TCA-specific tailoring — that lives in
  `workspaces/tca-pitch/`.
- Mobile (Flutter) parity work — separate workspace.
