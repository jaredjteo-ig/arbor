# 02 — Current State Mapping

For each of the 8 lifecycle stages: what's already in the codebase
(modules / models / endpoints / pages), and a 1–5 coverage rating.

**Rating scale:**

- ⭐ (1) — essentially absent
- ⭐⭐ (2) — primitive plumbing exists but no usable workflow
- ⭐⭐⭐ (3) — core functionality, gaps in polish or analytics
- ⭐⭐⭐⭐ (4) — production-ready, minor gaps
- ⭐⭐⭐⭐⭐ (5) — buyer-grade, near-complete

---

## Stage 1 — Strategy ⭐⭐ (2/5)

**Coverage:** primitive. The DATA exists; no workforce-strategy SURFACE.

| Layer   | What exists                                                                               |
| ------- | ----------------------------------------------------------------------------------------- |
| Models  | `Company.headcount_local/_pr/_ep/_sp/_wp` (snapshot only — set on signup, not maintained) |
| Models  | `Employee` (active count derivable)                                                       |
| Models  | `EmploymentEvent` (HIRED/PROMOTED/RESIGNED/TERMINATED — full event log)                   |
| Routers | None dedicated to strategy. `/profile` returns the static headcount fields.               |
| Pages   | No "Strategy" or "Workforce Plan" page in `apps/web/src/app/(dashboard)/`                 |

**Gaps:**

- No `WorkforcePlan` model (period-based headcount target vs. actual)
- No `SkillsInventory` per employee
- No `SuccessionPlan` model for critical roles
- No retention-risk scoring derived view
- The lifecycle dashboard itself (an 8-stage organising surface — NOT a wheel graphic; the Cox image is reference only)

---

## Stage 2 — Attract ⭐⭐⭐ (3/5)

**Coverage:** core public-facing API exists; employer-brand surface is thin.

| Layer   | What exists                                                                               |
| ------- | ----------------------------------------------------------------------------------------- |
| Models  | `JobListing` (with `unique_slug`, `published_at`, `application_form_config`)              |
| Routers | `GET /recruitment/careers/{company_slug}/jobs` (public, no auth)                          |
| Routers | `GET /recruitment/careers/{company_slug}/jobs/{job_slug}` (public detail)                 |
| Routers | `POST /recruitment/careers/{company_slug}/jobs/{job_slug}/apply` (public apply with PDPA) |
| Routers | TAFEP `Check Compliance` LLM scan on each job ad                                          |
| Pages   | `/careers/[slug]/page.tsx` exists in apps/web — public careers page renders               |
| Pages   | Job detail + apply form public-facing                                                     |

**Gaps:**

- `Company` has no employer-brand fields (`mission`, `tagline`,
  `benefits_summary`, `culture_pillars`, `team_photos_url`, `glassdoor_url`)
- No source-ROI dashboard ("which channel produces the best hires")
- No referral program tracking (employees who refer hires)
- No employer-brand metrics (page views, time-on-page, conversion)

---

## Stage 3 — Recruit ⭐⭐⭐⭐⭐ (5/5)

**Coverage:** strongest stage. Buyer-grade.

| Layer   | What exists                                                                                                                                                                  |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Models  | `JobListing`, `Candidate`, `InterviewSchedule`, `Offer`, `ScorecardEntry`, `ScorecardTemplate`, `JobScreeningQuestion`, `InterviewFeedback`, `CandidateActivity`             |
| Routers | 56 endpoints in `recruitment.py` (jobs CRUD, candidates CRUD with stage state machine, interviews with display_type+is_overdue, AI scorecards with quota cap, offers, hires) |
| Polish  | TAFEP screening, AI scorecard with bias hardening (S3-T3), schedule_interview idempotency window (S3-T6), default-template race lock (S3-T7)                                 |
| Pages   | `/recruitment/{dashboard,jobs,candidates,interviews,settings}`                                                                                                               |
| Pages   | Drag-and-drop kanban for stages (verified live today)                                                                                                                        |

**Gaps (small):**

- Talent pool / "good fit for future role" tag on rejected candidates
- Stage conversion analytics by demographic source
- Referral program tracking

---

## Stage 4 — Onboard ⭐⭐⭐⭐ (4/5)

**Coverage:** strong. Multiple recent rounds of hardening.

| Layer   | What exists                                                                                                                                                                               |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Models  | `OnboardingTemplate`, `OnboardingModule`, `OnboardingStep` (with `is_active`), `OnboardingAssignment` (with `last_reminder_sent_at`), `OnboardingStepProgress`, `PreboardingTaskInstance` |
| Routers | 41 endpoints in `onboarding.py` — templates, modules, steps, assignments, complete-step, reminders cron, preboarding tasks                                                                |
| Cron    | Daily 09:00 SGT reminder cron (S4-T4) wired in production                                                                                                                                 |
| Pages   | `/onboarding/templates/[id]` (admin builder with drag-drop)                                                                                                                               |
| Pages   | `/my-onboarding` (employee self-service view)                                                                                                                                             |

**Gaps:**

- No buddy-programme workflow (the column exists, no surface uses it)
- No 30/60/90-day review cadence (would need to use Appraisal or new model)
- No new-hire pulse survey
- No onboarding-completion analytics surfaced ("avg time-to-complete by
  template, by department")

---

## Stage 5 — Learning & Development ⭐⭐ (2/5)

**Coverage:** weakest stage on the platform. SkillsFuture lookup only.

| Layer   | What exists                                                             |
| ------- | ----------------------------------------------------------------------- |
| Models  | None dedicated to L&D                                                   |
| Routers | `GET /integrations/skillsfuture/courses` (catalogue lookup)             |
| Routers | `GET /integrations/skillsfuture/courses/{id}/grant-check` (eligibility) |
| Pages   | `/training/skillsfuture` (single page, just lists courses)              |

**Gaps (large):**

- No `TrainingRecord` model — no record of who took what training
- No `Certification` model — first-aid, professional, expiring certs
- No internal learning catalogue
- No learning-plan-per-employee surface
- No L&D budget tracking (per team / per employee)
- No mandatory-training tracker (e.g. WSH compliance training)
- No training-hours-by-demographic D&I metric

This is the biggest gap and the highest-leverage build for the
"lifecycle narrative" sell.

---

## Stage 6 — Reward, Recognition & Benefits ⭐⭐⭐⭐ (4/5)

**Coverage:** Reward + Benefits = strong. Recognition = absent.

| Sub-stage                               | Coverage                                                                                                                |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Reward (payroll, salary, bonuses)**   | ⭐⭐⭐⭐⭐ — `SalaryComponent`, full payroll engine, payslips, CPF, IR8A, IR21, GIRO, bonus runs, off-cycle adjustments |
| **Benefits (leave, claims)**            | ⭐⭐⭐⭐⭐ — 10+ statutory leave types + custom, claims with categories/groups/co-payment/BIK                           |
| **Recognition (peer, manager, social)** | ⭐ — entirely absent                                                                                                    |

**Models present:** `SalaryComponent`, `PayrollRun`, `Payslip`,
`PayslipItem`, `LeaveType`, `LeaveApplication`, `LeaveBalance`,
`Claim`, `ClaimCategory`, `ClaimItem`, `ClaimAuditEntry`

**Models absent for Recognition:**

- `Kudos` / `Recognition` / `PeerNomination`
- `EmployeeOfTheMonth`
- `RecognitionAward` (linked to a small bonus payment)

**Other gaps:**

- No pay-equity dashboard (gender / citizenship pay gap)
- No total-rewards statement (a year-end "here's everything you got: salary
  - leave + claims + benefits + bonus" PDF)

---

## Stage 7 — Progression & Performance ⭐⭐⭐ (3/5)

**Coverage:** appraisals work, but no goals/360/PIP/succession.

| Layer   | What exists                                                                    |
| ------- | ------------------------------------------------------------------------------ |
| Models  | `AppraisalTemplate`, `AppraisalPeriod`, `Appraisal`                            |
| Routers | 5 endpoints in `appraisals.py` — template CRUD, period CRUD, reviews, sign-off |
| Models  | `EmploymentEvent.PROMOTED` event-log + `SALARY_REVISION`                       |
| Pages   | `/appraisals` (admin + employee views)                                         |

**Gaps (significant):**

- No `Goal` / `OKR` model — no goal-tracking, no progress check-ins
- No `PIP` (Performance Improvement Plan) model — could ride on Appraisal
  but is conceptually distinct
- No 360-feedback mechanism (peer / direct-report / cross-functional input)
- No `SuccessionPlan` model — who's next-in-line for which role
- No `Competency` model — what does each role require, what does each person
  have

---

## Stage 8 — Retain / Exit ⭐⭐⭐ (3/5)

**Coverage:** exit mechanics work; retention analytics are absent.

| Layer   | What exists                                                                            |
| ------- | -------------------------------------------------------------------------------------- |
| Models  | `EmploymentEvent.RESIGNED/TERMINATED/RETRENCHED`                                       |
| Models  | `Employee.notice_period_days`, `end_date`, `confirmation_status`, `probation_end_date` |
| Models  | `OffboardingChecklist` (if it exists — need to verify)                                 |
| Routers | Final-pay calc in payroll runs                                                         |
| Routers | IR21 tax-clearance generation                                                          |
| Pages   | Employee termination flow on `/employees/[id]`                                         |

**Gaps:**

- No `ExitInterview` model + workflow + analytics
- No churn dashboard (voluntary vs. involuntary, tenure bucket, department)
- No retention-risk scoring per employee
- No alumni / boomerang tagging
- No anniversary / tenure-milestone alerts
- No "stay interviews" (proactive retention conversations) workflow

---

## Coverage summary table

| Stage | Cox name              | Arbor coverage   | Largest gap                              |
| ----- | --------------------- | ---------------- | ---------------------------------------- |
| 1     | Strategy              | ⭐⭐ (2/5)       | No surface at all — data exists, no page |
| 2     | Attract               | ⭐⭐⭐ (3/5)     | Employer-brand fields on Company         |
| 3     | Recruit               | ⭐⭐⭐⭐⭐ (5/5) | Talent pool re-engagement                |
| 4     | Onboard               | ⭐⭐⭐⭐ (4/5)   | Buddy programme + 30/60/90-day           |
| 5     | L&D                   | ⭐⭐ (2/5)       | **Entire L&D module — biggest gap**      |
| 6     | Reward/Recog/Benefits | ⭐⭐⭐⭐ (4/5)   | **Recognition — entirely absent**        |
| 7     | Progression/Perf      | ⭐⭐⭐ (3/5)     | Goals + PIP + succession + 360           |
| 8     | Retain/Exit           | ⭐⭐⭐ (3/5)     | Exit interviews + churn dashboard        |

**Average coverage:** 3.25/5

**Strongest stages (4+):** Recruit, Onboard, Reward & Benefits.
**Weakest stages (≤2):** Strategy, L&D.
**Highest visibility-to-effort ratio for next build:** the Strategy
hub (8-stage card-grid lifecycle dashboard) + Recognition module + L&D foundations.
