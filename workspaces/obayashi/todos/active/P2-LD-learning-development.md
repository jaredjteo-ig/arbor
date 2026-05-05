# Phase 2 (L&D first) — Learning & Development foundations

**Source plan:** `02-plans/03-post-redteam-plan.md` Gate 3 — L&D foundations.
**Estimate:** 8–10 dev-days.
**Why first in Phase 2:** L&D is the largest gap in the lifecycle (2/5
coverage today; SkillsFuture lookup only). Closes the "Cox stage 5 is
empty" objection that buyers see immediately on the lifecycle dashboard.

## Goal

Lifecycle stage 5 (L&D) coverage moves from 2/5 to 4/5. Buyers see real
training records, certification expiry alerts, and a mandatory-training
tracker — not just a SkillsFuture course list.

## Critical path

```
P2-LD-1 (TrainingRecord) → P2-LD-4 (records page)
P2-LD-2 (Certification) → P2-LD-5 (certs page + expiry alerts)
P2-LD-3 (MandatoryTrainingRequirement) → P2-LD-6 (tracker tile)
P2-LD-7 (demo seed) → after backend lands
P2-LD-8 (lifecycle hook) → after FE lands
P2-LD-9 (tests) → continuous, locked-down at end
```

---

## P2-LD-1 — TrainingRecord model + CRUD endpoints

- **Model fields:** `id`, `company_id`, `employee_id`, `course_name`,
  `course_provider`, `course_type` (internal/external/skillsfuture),
  `start_date`, `completion_date` (nullable), `hours`, `cost`,
  `funding_source` (self/employer/skillsfuture_credit),
  `certificate_url`, `notes`, `created_at`, `updated_at`.
- **Endpoints:** `POST /training/records`, `GET /training/records`
  (paginated, filterable by employee/course_type), `GET /training/records/{id}`,
  `PATCH /training/records/{id}`, `DELETE /training/records/{id}` (soft
  via `is_archived`).
- **Constraints:** all writes go through `dataflow_crud`. List reads
  cap at 10000. Use `cache_ttl=0` only on aggregations the lifecycle
  dashboard reads.

## P2-LD-2 — Certification model with expiry tracking

- **Model fields:** `id`, `company_id`, `employee_id`, `certification_name`,
  `issuing_body`, `issued_date`, `expires_at` (nullable for
  non-expiring), `cert_number`, `attachment_url`, `notes`.
- **Endpoint:** standard CRUD plus `GET /training/certifications/expiring?within_days=N`.
- **Constraints:** alert thresholds (30 / 7 / expired) fed by the
  alerts engine — see `src/hr_advisory/api/routers/alerts.py` for the
  established pattern.

## P2-LD-3 — MandatoryTrainingRequirement model

- **What:** lets owners define "every employee in dept X must hold
  cert Y by date Z". Used by WSH compliance + sector-specific demands.
- **Fields:** `id`, `company_id`, `requirement_name`, `applicable_to`
  (department / pass_type / role match), `required_certification_id`
  (FK), `due_within_days_of_hire`, `is_active`.
- **Endpoint:** standard CRUD; plus a derived
  `GET /training/mandatory/coverage` returning per-employee compliance.

## P2-LD-4 — `/training/records` page (admin + employee views)

- **What:** Replace the current bare SkillsFuture lookup page with a
  proper records workflow.
- **Admin tabs:** All Records | Per Employee | Per Course Type.
  Add/Edit/Archive per row.
- **Employee view:** "My Training" — read-only of their own rows + a
  CTA to request a new course (creates a draft record).

## P2-LD-5 — `/training/certifications` page with expiry alerts

- **What:** Sortable table by `expires_at`. Three top-tile counters:
  Expired, Expiring in 30 days, Active.
- **Each row:** employee name, certification, issue date, expiry,
  status pill, "Renew" CTA (creates a new cert row pre-filled).

## P2-LD-6 — Mandatory-training tracker dashboard tile

- **What:** New tile on `/dashboard` and on the lifecycle dashboard's
  L&D detail panel.
- **Shows:** "X of Y employees compliant with mandatory training" plus
  the names of non-compliant employees.

## P2-LD-7 — Demo seed: 3 training records, 2 certs, 1 expiring soon

- **What:** Add a `seed_l_and_d` section to `scripts/seed_demo_data.py`
  per the seed-script rules. Idempotent. Uses `lookup-company` first.
- **Records:** 3 (mix of internal, external, SkillsFuture).
- **Certs:** 2 (one expiring in 21 days for the dashboard tile demo,
  one safely active).

## P2-LD-8 — Lifecycle-dashboard hook (S5 health-pill data)

- **What:** Wire the L&D coverage value into the Gate 2 aggregator so
  S5's health-pill turns from red to green once enough records exist.
- **Threshold:** ≥ 1 mandatory-training requirement met + ≥ 3
  TrainingRecord rows in the last 12 months.

## P2-LD-9 — Regression + E2E tests

- **Regression:** model schema test, expiring-certs filter test,
  mandatory-coverage derived view test.
- **E2E:** Playwright walks the records page, certs page, and verifies
  the lifecycle S5 pill flipped to amber/green after seeding.

---

## Done when

- All 9 deliverables green; lifecycle dashboard S5 pill is no longer red.
- Demo walkthrough convincingly answers "what about training?" without
  the buyer having to ask follow-ups.
- This file moves to `todos/completed/P2-LD-learning-development.md`.
