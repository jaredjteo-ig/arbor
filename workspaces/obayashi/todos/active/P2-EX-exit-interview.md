# Phase 2 — Exit interview workflow

**Source plan:** `02-plans/03-post-redteam-plan.md` Gate 3 — Exit interview.
**Estimate:** 4–5 dev-days.
**Why fourth in Phase 2:** exit mechanics work (terminate flow + IR21
generation), but no analytics. Exit interview model unlocks churn
storytelling for stage 8.

## Goal

When an employee is terminated, an exit interview is generated and sent
to them. Admins see aggregated themes per quarter. Lifecycle stage 8
moves from 3/5 → 4/5 with real exit data.

## Critical path

```
P2-EX-1 (model) → P2-EX-2 (workflow trigger) → P2-EX-3 (admin view)
P2-EX-4 (seed) → after model
P2-EX-5 (lifecycle hook) → last
P2-EX-6 (tests) → continuous
```

---

## P2-EX-1 — ExitInterview model

- **Fields:** `id`, `company_id`, `employee_id`, `triggered_at`,
  `triggered_by_event_id` (FK to EmploymentEvent, RESIGNED/TERMINATED/
  RETRENCHED), `submitted_at` (nullable), `survey_payload` (JSON text:
  Likert ratings + free-text fields), `themes` (JSON text: derived
  tags after submission), `is_anonymous` (boolean), `created_at`,
  `updated_at`.
- **Survey fields (locked at v1):**
  - Q1 Likert: "How would you rate your overall experience?"
  - Q2 Likert: "How fairly were you treated?"
  - Q3 Multi-pick: "Reasons for leaving" (chips: comp, growth,
    manager, role, location, family, retirement, other).
  - Q4 Free text: "What worked well?"
  - Q5 Free text: "What would you change?"
  - Q6 Free text: "Would you recommend Central as an employer? (yes/no/why)"

## P2-EX-2 — Workflow: triggered on termination, sent to leaver

- **What:** When an EmploymentEvent of type RESIGNED/TERMINATED/
  RETRENCHED is written, automatically create an ExitInterview row
  and email the leaver a tokenized link to the survey.
- **Survey link:** signed JWT with 30-day expiry, scoped to that
  ExitInterview row. Anonymous mode strips employee_id from any join
  the admin sees.
- **Endpoints:**
  - `POST /exit-interviews/{token}/submit` (no auth, token-validated).
  - `GET /exit-interviews` admin scope, paginated.
  - `GET /exit-interviews/themes?since=YYYY-MM` — derived theme tally.

## P2-EX-3 — Admin view: aggregated themes + sentiment

- **Page:** `/exit-interviews` (admin/hr_manager only).
- **Tabs:** All Interviews | Themes (last 12 months).
- **Themes derivation:** simple keyword tally over the multi-pick
  reasons + light sentiment heuristic on the free text. No LLM call
  by default — guards budget. Optional LLM enrichment behind a feature
  flag.

## P2-EX-4 — Demo seed: 2 completed exit interviews

- **Section:** `seed_exit_interviews` in seed_demo_data.py. Idempotent.
- **Two interviews:** one anonymous (negative sentiment, manager-related
  themes), one named (positive sentiment, retirement reason).

## P2-EX-5 — Lifecycle-dashboard hook (S8 churn analytics)

- **What:** Aggregator returns `exits_last_90d` +
  `exit_response_rate` + `top_theme_last_quarter` for S8 panel.
- **Health-pill:** S8 amber if response rate < 50%; green if ≥ 70%
  AND no negative theme dominates.

## P2-EX-6 — Regression + E2E tests

- **Regression:** token-validation logic; anonymous-mode redaction
  on admin GET; theme derivation determinism on the seeded data.
- **E2E:** Playwright walks the leaver flow with a seeded token,
  submits, then admin views the new row.

---

## Done when

- Lifecycle S8 panel surfaces exit data; demo can answer "what about
  retention insights?" with real charts.
- Avg lifecycle coverage moves from 3.25/5 baseline to ≥ 4/5.
- This file moves to `todos/completed/P2-EX-exit-interview.md`.
