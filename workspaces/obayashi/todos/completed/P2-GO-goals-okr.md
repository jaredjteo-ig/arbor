# Phase 2 — Goals / OKR

**Source plan:** `02-plans/03-post-redteam-plan.md` Gate 3 — Goals/OKR.
**Estimate:** 5–6 dev-days.
**Why third in Phase 2:** appraisals work today (3/5) but cycle-time
goal tracking is the missing piece. With Goals, Progression stage moves
from 3/5 → 4/5.

## Goal

Employees + managers can set goals, log check-ins, see progress on the
appraisals page. Lifecycle stage 7 (Progression/Performance) gets a
real interim-cycle data source instead of the once-per-year appraisal
snapshot.

## Critical path

```
P2-GO-1 (models) → P2-GO-2 (endpoints) → P2-GO-3 (page)
P2-GO-4 (appraisals tile) → after endpoints
P2-GO-5 (seed) → after endpoints
P2-GO-6 (lifecycle hook) → last
P2-GO-7 (tests) → continuous
```

---

## P2-GO-1 — Goal + GoalCheckIn models

- **Goal fields:** `id`, `company_id`, `employee_id`, `manager_id`
  (FK), `period_id` (FK to AppraisalPeriod, optional), `title`,
  `description`, `metric` (free text — the OKR's KR), `target_value`,
  `start_date`, `due_date`, `status` (draft/active/at_risk/done/cancelled),
  `progress_pct`, `created_at`, `updated_at`.
- **GoalCheckIn fields:** `id`, `goal_id`, `actor_user_id`,
  `progress_pct` (0–100), `note`, `created_at`.

## P2-GO-2 — Goal CRUD + check-in endpoints

- **Endpoints:**
  - `POST /goals` — owner/hr_manager/employee can create their own.
  - `GET /goals?employee_id=N` — admin scope, manager scope (their
    reports), self scope.
  - `PATCH /goals/{id}` — status, progress, fields.
  - `POST /goals/{id}/checkins` — append a check-in.
  - `GET /goals/{id}/checkins` — full history.
- **Constraints:** status-transition state machine — draft → active →
  (at_risk ↔ active) → done | cancelled. Manual `done` requires a
  final check-in with progress = 100.

## P2-GO-3 — `/goals` page (employee + manager views)

- **Employee view:** "My Goals" — kanban-by-status, in-line check-in
  form on each card.
- **Manager view:** "Team Goals" — flat table of direct reports, sortable
  by status / due date / progress.

## P2-GO-4 — Goal progress tile on appraisals page

- **What:** When opening an Appraisal, show a Goals panel listing the
  employee's active goals + most recent check-ins. Read-only view —
  edits go to `/goals`.

## P2-GO-5 — Demo seed: 3 employees × 2 goals each, 4 check-ins

- **Section:** `seed_goals` in seed_demo_data.py.
- **Mix:** 2 active, 2 at_risk, 1 done, 1 draft. 4 check-ins spread
  across the 6 goals to demo the timeline.

## P2-GO-6 — Lifecycle-dashboard hook (S7 enrichment)

- **What:** Aggregator returns `active_goals_count` +
  `at_risk_goals_count` for S7 detail panel.
- **Health-pill:** stays green if every employee in
  `H1 2026 Performance Review` period has ≥ 1 active goal.

## P2-GO-7 — Regression + E2E tests

- **Regression:** status-transition state machine; `progress_pct`
  bounds; manager-scope filter (no leakage of other teams).
- **E2E:** create goal, add check-in, mark done.

---

## Done when

- Lifecycle dashboard S7 panel shows live goal counts.
- Manager can demo "set goal → check in mid-cycle → close" in <2 min.
- This file moves to `todos/completed/P2-GO-goals-okr.md`.
