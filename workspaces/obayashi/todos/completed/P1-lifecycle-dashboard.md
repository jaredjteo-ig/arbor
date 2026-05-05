# Phase 1 — Lifecycle Dashboard (Gate 2) ✅ COMPLETED 2026-05-05

All 12 deliverables shipped (P1-1..P1-12). Single bundled commit. Page
live at `/strategy/lifecycle`. 36 P1 regression tests + 3 Playwright
E2E tests pin the contract. README updated.

**Evidence:**

| ID                 | Artefact                                                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| P1-1 aggregator    | `src/hr_advisory/api/routers/strategy.py::lifecycle_dashboard` returns hero + 8 stages + di_snapshot + activity in one round-trip |
| P1-2 page          | `apps/web/src/app/(dashboard)/strategy/lifecycle/page.tsx`                                                                        |
| P1-3 detail panels | `components/lifecycle/StageDetailPanel.tsx` — 8 panels with KPIs + quick-action deep links                                        |
| P1-4 health pills  | 8 `_pill_*` helpers + 28 parametrized regression tests                                                                            |
| P1-5 D&I tile      | `components/lifecycle/DiSnapshotTile.tsx` — gender + pass_type composition + 4-field completeness                                 |
| P1-6 activity feed | `components/lifecycle/ActivityFeed.tsx` — last 14 days                                                                            |
| P1-7 ALTER TABLE   | `scripts/migrate_company_employer_brand.py` — 6 employer-brand columns; `Company` dataclass updated                               |
| P1-8 sidebar       | `Lifecycle` entry above `Dashboard` in `NavigationSidebar.tsx`                                                                    |
| P1-9 tour          | `LifecycleTour.tsx` + `POST /strategy/lifecycle-tour/dismiss`                                                                     |
| P1-10 regression   | `tests/regression/test_p1_lifecycle_dashboard.py` — 36 tests                                                                      |
| P1-11 E2E          | `apps/web/tests/e2e-live/10-lifecycle-walk.spec.ts` — 3 tests                                                                     |
| P1-12 docs         | README "Strategy Hub" section                                                                                                     |

**Original brief:**

**Source plans:** `02-plans/02-lifecycle-dashboard-spec.md` (UI spec), `02-plans/03-post-redteam-plan.md` Gate 2.
**Estimate:** 10–12 dev-days.
**Owner-locked decisions:** Ship all 12 together (no feature flag). Single-threaded. Card grid — NOT a wheel graphic.

## Goal

A buyer (Jennifer Liu / Ricoh stakeholders) lands on `/strategy/lifecycle`
and walks Strategy → Attract → Recruit → Onboard → L&D → Reward →
Progression → Retain on a single page, with live coverage data per stage,
drill-in detail panels, and a D&I lens.

## Critical path

```
P1-7 (ALTER TABLE) → P1-1 (aggregator endpoint) → P1-2 (page) → P1-3..6 (detail panels, D&I, activity)
P1-8 (sidebar) ← any time
P1-9 (tour) → after P1-2 lands
P1-10 (regression) + P1-11 (E2E) ← after FE+BE merge
P1-12 (docs) ← last
```

---

## P1-1 — Lifecycle dashboard aggregator endpoint

- **What:** `GET /strategy/lifecycle-dashboard` — single endpoint that
  returns hero counters + per-stage coverage + D&I snapshot + activity
  feed in one payload.
- **Source data (live, no new tables needed):** Employee, EmploymentEvent,
  JobListing, Candidate, OnboardingAssignment, AppraisalPeriod, Claim,
  PayrollRun, LeaveApplication, Recognition (P2-RC, until then mocked
  to 0), TrainingRecord (P2-LD, mocked to 0).
- **Response shape:** see `02-plans/02-lifecycle-dashboard-spec.md`
  "API endpoint shape" section. Must include `health_pill` per stage
  with green/amber/red threshold per the spec.
- **Constraints:** all reads use `cache_ttl=0` for headcount aggregations
  to match the dashboard tile (round-12 NEW-3 lesson). All money/time
  fields use deterministic formatters.
- **Acceptance:** endpoint returns 200 with the documented shape;
  each of the 8 stages is present even if its coverage is 0.

## P1-2 — `/strategy/lifecycle` Next.js page (4×2 card grid)

- **What:** New page at `apps/web/src/app/(dashboard)/strategy/lifecycle/page.tsx`.
- **Layout per spec:** 4×2 card grid on desktop (≥1024px), horizontal
  stepper on tablet (640–1023px), vertical list on mobile (<640px).
- **Each stage card shows:** stage number + name, health-pill, 1-line
  summary, primary metric (live count), "Open stage" CTA.
- **Constraints:** no wheel graphic; no SVG geometry. Pure Tailwind grid.

## P1-3 — Per-stage detail panels

- **What:** Drill-in modal/panel per stage. Source spec details the
  content map (Strategy → headcount plan progress; Attract → published
  jobs + applicants this month; Recruit → kanban summary; Onboard →
  active assignments + completion %; L&D → records this quarter;
  Reward → last paid run + claims this month; Progression → in-flight
  appraisals + goals; Retain → resignations YTD + exit interview status).
- **Acceptance:** every stage opens; every metric in the panel matches
  the equivalent value on the existing dedicated page (e.g., L&D panel
  records count = `/training/records` list count).

## P1-4 — Health-pill thresholds + colour-coding

- **What:** Implement the health-pill component used inside each card.
  Thresholds locked per spec: green ≥ 4/5, amber 3, red ≤ 2 (with the
  underlying coverage rating coming from the aggregator endpoint).
- **Acceptance:** the round-12 baseline (avg 3.25/5) renders as 3 amber
  - 2 red + 3 green, matching `01-analysis/02-current-state-mapping.md`.

## P1-5 — D&I tile (transverse, derivable from existing fields)

- **What:** Single tile underneath the grid summarising per-stage D&I
  exposures: gender, citizenship, age cohort, tenure. No new PII fields.
- **Source:** existing Employee fields (gender, race, nationality,
  pass_type, dob, start_date) computed live.
- **Constraints:** race opt-in only. Anything missing/unset → "Not
  reported" rather than imputed.

## P1-6 — Activity feed (last 14 days)

- **What:** Right rail (or below D&I on mobile) listing recent
  EmploymentEvent rows — HIRED, PROMOTED, RESIGNED, etc.
- **Acceptance:** newest first, capped at 20, "View all" link drops
  to a future `/strategy/activity` route (Gate 3).

## P1-7 — ALTER TABLE: Company employer-brand fields

- **What:** Migration script `scripts/migrate_company_employer_brand.py`
  adding columns to `companies`:
  - `mission TEXT NOT NULL DEFAULT ''`
  - `tagline TEXT NOT NULL DEFAULT ''`
  - `benefits_summary TEXT NOT NULL DEFAULT ''`
  - `culture_pillars TEXT NOT NULL DEFAULT ''` (JSON array as text)
  - `team_photos_url TEXT NOT NULL DEFAULT ''`
  - `glassdoor_url TEXT NOT NULL DEFAULT ''`
- **Constraints:** idempotent (column-exists check before each ALTER).
  Same pattern as `migrate_employee_tracks_attendance.py`.
- **Plus:** add the corresponding fields to the `Company` dataclass in
  `src/hr_advisory/models/company_user.py`.
- **Acceptance:** migration runs cleanly twice; new fields reachable
  via `/profile` GET/PATCH.

## P1-8 — Sidebar entry: "Strategy" above Dashboard

- **What:** Add a top-level `Strategy` entry to
  `apps/web/src/components/shell/NavigationSidebar.tsx` linking to
  `/strategy/lifecycle`. It sits _above_ Dashboard.
- **Constraints:** additive; do not relabel Dashboard.

## P1-9 — First-time admin onboarding tour pop-over

- **What:** Light dismissible pop-over for first-time landing on
  `/strategy/lifecycle`. 3 bullets: "this is your lifecycle map",
  "click any stage to drill in", "amber/red flags need action".
- **Persisted via:** existing `feature_flags` map on Company (set
  `seen_lifecycle_tour` once dismissed).

## P1-10 — Regression tests

- **Tests:**
  - `tests/regression/test_p1_lifecycle_aggregator_shape.py` — every
    stage present, every health-pill value valid.
  - `tests/regression/test_p1_lifecycle_thresholds.py` — at the round-12
    baseline state, the response yields the documented pill colours.
- **Style:** follow round-12 pattern — AST inspection where useful;
  full integration test for the endpoint with a real PG.

## P1-11 — Playwright E2E walking all 8 stages

- **What:** `apps/web/tests/e2e/lifecycle-walk.spec.ts` walks the page,
  opens every stage panel, asserts content presence per stage, walks
  the D&I tile and activity feed.
- **Constraints:** runs against local dev (`http://localhost:3000`),
  re-uses the existing Playwright login fixture.

## P1-12 — README + docs update with screenshot

- **What:** Add a `Strategy hub` section to README + `docs/00-authority/`.
  One screenshot of the card grid. One paragraph explaining the
  health-pill thresholds.
- **Constraints:** no commercial coupling per `rules/independence.md`.

---

## Done when

- All 12 deliverables green and shipped in a single bundled commit.
- A new redteam-style Playwright walk passes the page.
- This file moves to `todos/completed/P1-lifecycle-dashboard.md`.
- Lifecycle coverage rating in `01-analysis/02-current-state-mapping.md`
  is recomputed and committed (Strategy goes from 2/5 → 4/5).
