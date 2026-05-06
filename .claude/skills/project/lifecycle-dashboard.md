---
name: lifecycle-dashboard
description: "Cox 8-stage Employee Lifecycle dashboard architecture. Use when adding a new lifecycle stage data source, modifying the aggregator, changing health-pill thresholds, or building a new top-level Strategy hub surface."
---

# Lifecycle Dashboard

The Cox 8-stage Employee Lifecycle is Arbor's organising surface — the
landing page for buyers (`/strategy/lifecycle`). Each lifecycle stage
corresponds to one or more shipped modules; the dashboard's job is to
roll up all stages into a single round-trip with health pills,
KPIs, drill-in detail panels, a D&I tile, and a 14-day activity feed.

## Architecture

```
GET /strategy/lifecycle-dashboard       (single round-trip, owner/hr_manager)
   ├── hero            workforce strategy summary
   ├── stages          { strategy, attract, recruit, onboard, lnd,
   │                     reward, progression, retain }
   │   └── each: { health: green|amber|red, kpi: {...} }
   ├── di_snapshot     gender + pass_type composition + completeness
   └── activity[]      last 14 days, capped at 20 rows, multi-source
```

Every read uses `cache_ttl=0` — the dashboard is the authoritative
counter on the platform. See `security-patterns.md` P22 (live-vs-
snapshot drift) for why.

## Stage → owning module map

| Stage         | Cox name                        | Owning module(s)                                   | Health pill input                                |
| ------------- | ------------------------------- | -------------------------------------------------- | ------------------------------------------------ |
| 1 Strategy    | Strategy                        | Workforce plan + headcount snapshot                | Δ vs target                                      |
| 2 Attract     | Attract                         | JobListing + Candidate + careers page              | applies_30d, sources_30d                         |
| 3 Recruit     | Recruit                         | Candidate kanban + Interview + Offer               | active_jobs, stale (≥14d), candidates            |
| 4 Onboard     | Onboard                         | OnboardingTemplate + Assignment + StepProgress     | avg_completion, overdue                          |
| 5 L&D         | Learning & Development          | TrainingRecord + Certification + Mandatory tracker | avg_hours_per_employee_per_year, has_data        |
| 6 Reward      | Reward · Recognition · Benefits | PayrollRun + Recognition + Claims + Leave          | last_payroll_status, recognitions_30d, headcount |
| 7 Progression | Progression & Performance       | Appraisal + Goal + GoalCheckIn                     | due_total vs completed                           |
| 8 Retain      | Retain · Exit                   | EmploymentEvent + ExitInterview                    | yoy_delta_ppt                                    |

Every health-pill threshold lives in `routers/strategy.py::_pill_*`
helpers and is pinned by parametrized regression tests in
`tests/regression/test_p1_lifecycle_dashboard.py`. Don't move the
thresholds without updating the tests.

## Adding a new stage data source — checklist

When you add a Phase 2/3 module that should feed an existing stage:

1. **Wire the read in `_stages.<stage>`** in `routers/strategy.py`,
   inside the SAME commit that ships the module.
2. **Use `_safe_list("ModelName", filter)`** so the aggregator stays
   resilient if the new model isn't registered yet (see "Phase 2
   resilience" below). It returns `[]` on
   `ValueError: Node X not found`.
3. **Update the stage's KPI dict** with the new field(s). Don't replace
   existing KPI fields — extend them.
4. **Update the stage's health-pill function** if the new signal
   should affect colour. Otherwise keep the pill input unchanged.
5. **Update the frontend StageDetailPanel.tsx** in the same commit:
   - Refresh blurb if it previously said "coming soon" (P27).
   - Add deep-link to the new module's owning page.
   - Surface the new KPI in the panel's `kpis` array.
6. **Update the activity feed**: if the module emits user-visible
   events (kudos posted, exit interview submitted), add a source loop
   to `_activity()` — tenant-scope it (P25), dedup if multi-row per
   parent.
7. **Add a regression test** asserting the new KPI key appears in the
   aggregator response.
8. **Add a demo seed** in `scripts/backfill_demo_<module>.py` so the
   stage card has data on first deploy.

## Phase 2 resilience — `_safe_list`

The aggregator was written before TrainingRecord / Recognition / Goal /
ExitInterview existed. Each Phase 2 model is read via `_safe_list`,
which catches `ValueError` for unregistered models and returns `[]`.
This lets P1 lifecycle dashboard ship without depending on Phase 2
models existing yet. Once Phase 2 ships, the same code path picks up
real data automatically — no aggregator change needed at deploy time.

```python
def _safe_list(model: str, filter_dict: dict) -> list[dict]:
    try:
        return dataflow_crud.list_records(model, filter_dict, cache_ttl=0)
    except ValueError as exc:
        if "not found" in str(exc).lower() or "not registered" in str(exc).lower():
            return []
        raise
```

Don't replace `_safe_list` with bare `list_records` even after Phase 2
ships — it's the resilience seam for any future model that lands later.

## Health-pill thresholds (locked)

| Stage       | green                                           | amber                           | red                             |
| ----------- | ----------------------------------------------- | ------------------------------- | ------------------------------- |
| Strategy    | within 10% of headcount target                  | 10–20% off                      | >20% off OR no plan             |
| Attract     | ≥3 sources active in 30d                        | 1–2 sources                     | 0 applies                       |
| Recruit     | active jobs, no stale, candidates exist         | 1+ stale (≥14d)                 | all stale OR no candidates      |
| Onboard     | avg completion ≥75% AND 0 overdue               | 50–75% OR 1+ overdue            | <50% OR 3+ overdue              |
| L&D         | avg ≥10 hrs/employee/yr                         | 5–10 hrs                        | <5 hrs OR no data               |
| Reward      | payroll on time + ≥1 recognition / employee / Q | late payroll OR low recognition | failed payroll OR 0 recognition |
| Progression | ≥80% of due appraisals completed                | 50–80%                          | <50%                            |
| Retain      | YoY churn flat or down                          | YoY +1–3 ppt                    | YoY +>3 ppt                     |

Codified as `_pill_strategy / _pill_attract / ... / _pill_retain` in
`routers/strategy.py`. Every helper is parametrized-tested in
`tests/regression/test_p1_lifecycle_dashboard.py` — modify the helpers
and the tests in the same commit.

## Activity feed sources

Currently:

- **EmploymentEvent** — `(event_type or "").upper() in ("RESIGNED","TERMINATED","RETRENCHED","RETIRED","HIRED","PROMOTED")`
- **InterviewSchedule** (recruit) — anything in last 14d
- **OnboardingStepProgress** (onboard) — rolled up to one row per
  assignment, scoped via `OnboardingAssignment.company_id` (P25).
- **Appraisal** (progression) — most recent of submitted/signed/updated.
- **Recognition** (reward) — `is_public=True`, last 14d.
- **ExitInterview** (retain) — submitted_at OR triggered_at.

To add a new source:

```python
for r in _safe_list("MyModel", {"company_id": company_id}):
    ts = r.get("created_at") or ""
    if not ts or ts < cutoff:
        continue
    if r.get("is_archived"):
        continue
    feed.append({
        "stage": "owning_stage_key",
        "kind": "MY_KIND",
        "ts": ts,
        "summary": f"...",
    })
```

Always `feed.sort(key=lambda r: r.get("ts") or "", reverse=True)` and
`return feed[:20]` at the end.

**Summary copy MUST be humanized (P35).** Every `summary` string the feed
emits goes straight to a buyer-visible card. Resolve `employee_id`,
`candidate_id`, `assignment_id` to real names BEFORE composing the
string — never inline `employee #N`. Resolve enum values
(`above_and_beyond`, `RESIGNED`) through a `LABEL = {...}` map. Build
the resolution maps once at the top of `_activity()`; do not query
inside the per-row loop. See `security-patterns.md::P35`.

**YoY hero metrics need a last-year baseline in the seed.** Hero
counters that compare to "this time last year" (`churn_yoy_delta`,
`headcount_yoy_delta`) read 0.0 if the seed only writes events for the
current year. Demo backfills MUST seed at least one event ~14 months
ago for every YoY surface. The exit-interview backfill is the canonical
example — see `scripts/backfill_demo_exit_interviews.py` for the
"last-year RESIGNED EmploymentEvent" pattern.

## Strategy depth surfaces (P3)

`/strategy/lifecycle` is the entry. Phase 3 added 3 sibling tabs under
the Strategy hub:

| Path                   | Purpose                                                     |
| ---------------------- | ----------------------------------------------------------- |
| `/strategy/plan`       | Author + publish workforce plan (period, narrative, status) |
| `/strategy/retention`  | Read-only retention risk score per active employee          |
| `/strategy/pay-equity` | By-gender + by-pass-type bucket avg salary, <5 collapsed    |

All four tabs share `StrategyTabs` component (defined inline in each
page). Add a new tab by editing all four files plus `lifecycle/page.tsx`
in lockstep — there's no central tab definition.

## Frontend component map

```
apps/web/src/components/lifecycle/
  StageGrid.tsx           4×2 grid (desktop) / 1-col list (mobile);
                          Lucide icons; health-pill with dot+icon+word.
  StageDetailPanel.tsx    8 stage panels with KPIs + quick-action deep
                          links. Edit blurbs + actions when modules ship.
  HeroBand.tsx            workforce strategy band (Plan disabled = P1)
  DiSnapshotTile.tsx      gender + pass_type composition + completeness
  ActivityFeed.tsx        last 14 days, time-formatted, kind badges
  LifecycleTour.tsx       one-time pop-over; persisted via Company.feature_flags

apps/web/src/services/api/
  strategy.ts             /strategy/lifecycle-dashboard + tour dismiss
  strategy-depth.ts       /strategy/{workforce-plan,skills,succession,
                          retention-risk,pay-equity}
```

## Phase / gate ship discipline

The obayashi initiative shipped in 4 gates (round-12 closure → P1 →
P2 → P3). Lessons:

1. **One bundled commit per gate** — don't trickle-ship across gates.
   Lifecycle UI + backend + seed + tests + docs all land together.
2. **One ship script per gate** — `deploy/ship-<gate>.sh`. Each
   includes pre-flight regression sweep, push, SSH pull + rebuild,
   60s health loop + login retry, schema bootstrap (touch new
   endpoints to autocreate tables), seed run, smoke check.
3. **`docker cp scripts/` before any `docker exec ... python scripts/...`**
   — the backend image bakes only `src/`, not `scripts/`. P32.
4. **Tables auto-create on first endpoint hit** — DataFlow does this
   automatically. So the bootstrap pattern is:

   ```bash
   for path in /strategy/workforce-plan /strategy/skills /strategy/succession; do
       curl -sS -o /dev/null "${PROD_API_BASE}/api${path}" \
         -H "Authorization: Bearer ${ACCESS}" || true
   done
   ```

   Then run the seed script.

5. **Independent guards in seed scripts** — each table's idempotency
   check stands alone (P30). A "any-row-already-exists" exit at the
   top of the script means re-running after a partial change skips
   the new insertion path.

6. **Deploy script smoke check is feature-specific**, not just `/health`.
   Verify the new aggregator KPI key, the new endpoint shape, the new
   page returns 200. Each gate's ship script encodes its own smoke.

## Anti-patterns (don't)

- ❌ Reading `Company.headcount_local` for "current headcount" on a
  dashboard tile — that's a snapshot field, drifts. Use live employees
  with `cache_ttl=0` (P22).
- ❌ Persisting retention scores. They're derived, recompute on every
  call (P34).
- ❌ Reading `event_type` directly without `.upper()` — mixed-case data
  in prod silently drops rows (P29).
- ❌ Pulling raw `OnboardingStepProgress` without joining via
  `OnboardingAssignment.company_id` — that source isn't natively
  tenant-scoped (P25).
- ❌ Letting one stage's blurb claim a module is "coming soon" while
  the module ships in the same commit (P27).
- ❌ Building a new stage card without a regression test pinning its
  KPI keys.
- ❌ Composing activity-feed `summary` strings with raw IDs or
  snake_case enums (`employee #3`, `above_and_beyond`). Resolve through
  the name maps + `LABEL` dict at the top of `_activity()` (P35).
- ❌ Seeding only this-year data when a hero KPI is YoY (`churn_yoy_delta`
  reads 0 if there are no last-year exits). Plant a 14-month-old anchor
  event in the demo backfill.

## Pinned regression tests

| File                                              | Pins                                                                                                      |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `tests/regression/test_p1_lifecycle_dashboard.py` | endpoint exists, response shape, all 8 stages, 28 health-pill cases                                       |
| `tests/regression/test_p2_lnd.py`                 | TrainingRecord/Certification/MandatoryTrainingRequirement models + 8 routes + casefold cert match         |
| `tests/regression/test_p2_rc.py`                  | 5 categories locked, rate limits, 1000-char message cap                                                   |
| `tests/regression/test_p2_go_ex.py`               | Goal status state machine, 0..100 progress bounds, exit token audience, anonymous redaction               |
| `tests/regression/test_p3_strategic_depth.py`     | WorkforcePlan/Skills/Succession models, anonymity threshold, retention not-persisted                      |
| `tests/regression/test_redteam2_findings.py`      | Goals scope on every handler, self-recognition + self-nomination guards                                   |
| `tests/regression/test_redteam2_polish.py`        | Activity-feed humanize (P35), exit-survey preflight semantic-reason (P36), training PATCH whitelist (P39) |

If you change the aggregator shape or threshold, update the relevant
test file in the same commit.

## Cross-references

- `routers/strategy.py` — full aggregator + Phase 3 endpoints
- `routers/training.py` — L&D CRUD + mandatory coverage view
- `routers/recognition.py` — kudos + nominations + feed
- `routers/goals.py` — Goal + GoalCheckIn + scope filter
- `routers/exit_interviews.py` — JWT-tokenised public submit
- `models/company_user.py` — all dataclasses (Phase 2 + Phase 3 added at the end of the file)
- `workspaces/obayashi/02-plans/02-lifecycle-dashboard-spec.md` — the original UI spec
- `workspaces/obayashi/04-validate/01-redteam-findings.md` — round-1 findings
- `workspaces/obayashi/04-validate/02-redteam-findings-round2.md` — round-2 findings + closure
