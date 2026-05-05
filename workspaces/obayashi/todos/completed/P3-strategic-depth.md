# Phase 3 — Strategic depth (Gate 4)

**Source plan:** `02-plans/01-phased-roadmap.md` Phase 3 + `02-plans/03-post-redteam-plan.md` Gate 4.
**Estimate:** 20–25 dev-days.
**Order matters:** workforce plan → skills inventory → succession (depends on skills) → retention scoring (depends on EmploymentEvent + skills) → pay-equity dashboard (depends on payroll only).

## Goal

The Strategy hub stops being a coverage dashboard and becomes an
_authoring_ surface. Owners can write the workforce plan, see skills
gaps, identify successors, and act on retention risk before it becomes
churn.

## Critical path

```
P3-1 (WorkforcePlan + UI) → P3-2 (SkillsInventory) → P3-3 (SuccessionPlan)
P3-4 (RetentionRisk) ← parallel-safe with P3-3
P3-5 (PayEquity) ← independent, payroll-only
```

---

## P3-1 — WorkforcePlan model + Strategy hub authoring UI

- **Model fields:** `id`, `company_id`, `period_start`, `period_end`,
  `status` (draft/published/archived), `headcount_targets_json`,
  `skills_priorities_json`, `retention_focus_json`, `narrative`,
  `created_by`, `approved_by`, `approved_at`.
- **UI:** new page `/strategy/plan` — sectioned form (Headcount |
  Skills | Retention | Narrative). Diff against actuals from the
  lifecycle dashboard.
- **Acceptance:** owner can draft a plan, publish it, see it referenced
  on the lifecycle hero header ("FY 2026 H1 plan: published").

## P3-2 — SkillsInventory per employee

- **Model fields:** `id`, `company_id`, `employee_id`, `skill_name`,
  `proficiency` (1–5), `years_experience`, `last_used_date`,
  `verified_by_user_id` (nullable), `notes`.
- **Endpoints:** standard CRUD + `GET /skills/coverage?company_id=N`
  returning skill → headcount-with-skill matrix.
- **UI:** tab on each employee profile page; aggregate matrix on
  `/strategy/skills`.

## P3-3 — SuccessionPlan for critical roles

- **Model fields:** `id`, `company_id`, `role_title`, `incumbent_id`,
  `criticality` (low/med/high), `successors_json` (list of
  `{employee_id, readiness_months, gaps}`), `last_reviewed_at`.
- **UI:** `/strategy/succession` — table of critical roles with the
  current incumbent and a comma-list of successors.
- **Constraint:** depends on P3-2 — successor readiness derives from
  skills inventory deltas.

## P3-4 — Retention-risk derived view (read-only, no new PII)

- **What:** Computed from existing fields — no new PII. Inputs:
  EmploymentEvent history (PROMOTED count, SALARY_REVISION count),
  tenure, leave usage trend, recent appraisal score.
- **Endpoint:** `GET /strategy/retention-risk?employee_id=N` returns
  `{score: 0..100, drivers: [...], recommendation: ...}`.
- **UI tile:** on the lifecycle dashboard's S8 panel — top 5
  at-risk employees with rationale.
- **Constraint:** read-only. No persistent risk scores stored to
  avoid PII drift.

## P3-5 — Pay-equity dashboard

- **What:** computed from existing payroll history. Pay gap by
  gender, pass-type, tenure cohort.
- **Endpoint:** `GET /payroll/pay-equity?period_id=N`.
- **UI:** `/payroll/equity` — summary chart + drill-in by department.
- **Constraint:** never expose individual salaries through this view;
  bucket counts < 5 employees collapse to "—" to prevent re-identification.

---

## Done when

- Average lifecycle coverage rating ≥ 4.5/5.
- Strategy hub demonstrates planning + authoring, not just monitoring.
- This file moves to `todos/completed/P3-strategic-depth.md`.
