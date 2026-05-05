# 03 — Gap Analysis

For each gap identified in `02-current-state-mapping.md`: severity (impact ×
probability of buyer/user noticing), effort (S/M/L/XL), strategic priority
(P0..P3), and a recommended treatment.

**Severity rubric (1–5):**

- 5 = blocks a buyer demo or pilot ("the product is missing this whole stage")
- 4 = a real customer asks about it within first month
- 3 = visible during exploration but workaroundable
- 2 = noticed by power users only
- 1 = polish

**Effort rubric:**

- S = <1 day (1 file or one schema add)
- M = 2–5 days
- L = 1–2 weeks (multiple new models + routers + UI)
- XL = >2 weeks (new module class)

**Priority:**

- P0 = ship before any pilot demo
- P1 = ship in next pilot iteration
- P2 = ship after first paying customer
- P3 = backlog / nice-to-have

---

## Stage 1 — Strategy gaps

| ID    | Gap                                                                | Severity | Effort | Priority | Treatment                                                                                                                                                                         |
| ----- | ------------------------------------------------------------------ | -------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1-G1 | No lifecycle dashboard / surface                                   | 5        | M      | **P0**   | New `/dashboard/lifecycle` page with an 8-stage card grid + per-stage health pills (NOT a wheel graphic — Cox image is reference only). Pure read aggregation over existing data. |
| S1-G2 | No `WorkforcePlan` model (period-based headcount target vs actual) | 4        | M      | P1       | New `WorkforcePlan` model + 1 router + 1 page. Headcount target by department by quarter.                                                                                         |
| S1-G3 | No skills inventory per employee                                   | 3        | M      | P2       | Add `Employee.skills_json` (text[] or JSON), simple skills tagger UI on profile.                                                                                                  |
| S1-G4 | No succession plan for critical roles                              | 3        | M      | P2       | New `SuccessionPlan` model (role, primary_successor, backup_successor, readiness_score).                                                                                          |
| S1-G5 | No retention-risk scoring                                          | 3        | S      | P2       | Pure derivation — no model. Score = f(time_since_promotion, appraisal_avg, leave_pattern, tenure). One endpoint.                                                                  |

---

## Stage 2 — Attract gaps

| ID    | Gap                                              | Severity | Effort | Priority | Treatment                                                                                                                                            |
| ----- | ------------------------------------------------ | -------- | ------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| S2-G1 | `Company` lacks employer-brand fields            | 4        | S      | **P0**   | ALTER TABLE: `mission`, `tagline`, `benefits_summary`, `culture_pillars`, `team_photos_url`, `glassdoor_url`, `linkedin_url`. Settings page surface. |
| S2-G2 | No source-ROI dashboard                          | 3        | S      | P1       | Aggregate over `Candidate.source` × `Candidate.stage` already in DB. One endpoint, one chart.                                                        |
| S2-G3 | No referral programme                            | 3        | M      | P2       | New `ReferralProgram` + `Referral` models. Bonus payout linked to payroll.                                                                           |
| S2-G4 | Public careers page lacks employer-brand content | 3        | S      | P1       | Once S2-G1 lands, render those fields on `/careers/[slug]`.                                                                                          |

---

## Stage 3 — Recruit gaps (smallest gap-set)

| ID    | Gap                                                                    | Severity | Effort | Priority | Treatment                                                                                    |
| ----- | ---------------------------------------------------------------------- | -------- | ------ | -------- | -------------------------------------------------------------------------------------------- |
| S3-G1 | Rejected/withdrawn candidates not flagged for re-engagement            | 2        | S      | P2       | Add `Candidate.talent_pool_tag: str` (good_fit_future / not_a_fit / boomerang). UI checkbox. |
| S3-G2 | No diversity-funnel analytics (stage conversion by demographic source) | 3        | S      | P1       | Pure aggregation over existing fields. New endpoint + chart.                                 |

---

## Stage 4 — Onboard gaps

| ID    | Gap                                          | Severity | Effort | Priority | Treatment                                                                                                                 |
| ----- | -------------------------------------------- | -------- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| S4-G1 | Buddy programme has a column but no workflow | 3        | M      | P1       | New `BuddyCheckin` model (assignment_id, week_n, completed). Cron prompt to buddies weekly for first 90 days.             |
| S4-G2 | No 30/60/90-day review cadence               | 3        | M      | P1       | Auto-create `Appraisal` rows at +30d, +60d, +90d on hire — reuse existing Appraisal model.                                |
| S4-G3 | No new-hire pulse survey                     | 2        | M      | P2       | New `PulseSurvey` model (ride existing `appraisal` infrastructure).                                                       |
| S4-G4 | Onboarding completion analytics not surfaced | 3        | S      | P1       | Read aggregation of `OnboardingAssignment.completion_percentage` by template / department. Chart on Onboarding dashboard. |

---

## Stage 5 — Learning & Development gaps (largest)

This is the under-served stage. Investing here gives the biggest narrative
boost.

| ID    | Gap                                            | Severity | Effort | Priority | Treatment                                                                                                                                             |
| ----- | ---------------------------------------------- | -------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| S5-G1 | No `TrainingRecord` model                      | **5**    | M      | **P0**   | New `TrainingRecord` (employee_id, course_name, provider, type [internal/external/skillsfuture], status, hours, cost, completed_at, certificate_url). |
| S5-G2 | No `Certification` model with expiry           | 4        | M      | **P0**   | New `Certification` (employee_id, name, issuer, issued_date, expiry_date, document_url). Daily cron flags expiring certs.                             |
| S5-G3 | No internal learning catalogue                 | 3        | M      | P1       | New `LearningCourse` model + admin CRUD. Companies define their internal learning offerings.                                                          |
| S5-G4 | No per-employee learning plan                  | 3        | M      | P1       | New `LearningPlan` (employee_id, year, course_ids[], target_hours). Integrates with goals (Stage 7).                                                  |
| S5-G5 | No L&D budget tracking                         | 3        | M      | P1       | Add `Department.lnd_budget_annual` + `Employee.lnd_budget_annual`. Aggregation over `TrainingRecord.cost`.                                            |
| S5-G6 | No mandatory-training tracker (WSH compliance) | 4        | M      | **P0**   | A type-of `TrainingRecord` flagged `is_mandatory=True`. WSH-flagged employees auto-assigned.                                                          |
| S5-G7 | No training-hours-by-demographic D&I metric    | 2        | S      | P2       | Aggregation over `TrainingRecord` × `Employee` demographic fields.                                                                                    |

---

## Stage 6 — Reward, Recognition & Benefits gaps

| ID    | Gap                                           | Severity | Effort | Priority | Treatment                                                                                                                                          |
| ----- | --------------------------------------------- | -------- | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| S6-G1 | **Recognition entirely absent**               | 4        | M      | **P0**   | New `Recognition` model (from_user, to_employee, type [kudos/peer-nominate/manager-callout], message, public_visible). Recognition-wall feed page. |
| S6-G2 | No employee-of-the-month workflow             | 3        | M      | P1       | Built on top of S6-G1. Voting / nomination model + monthly cron.                                                                                   |
| S6-G3 | No spot-bonus tooling integrated with payroll | 3        | M      | P2       | Recognition can trigger a one-off `SalaryComponent` row on next payroll.                                                                           |
| S6-G4 | No pay-equity dashboard                       | 4        | S      | **P0**   | Pure aggregation — gender pay gap, citizenship pay gap, role-vs-pay-band. All data exists.                                                         |
| S6-G5 | No total-rewards statement (year-end PDF)     | 3        | M      | P2       | Year-end PDF: salary + bonuses + leave value + claims + employer CPF + benefits. Reuses payroll engine.                                            |

---

## Stage 7 — Progression & Performance gaps

| ID    | Gap                                            | Severity | Effort | Priority | Treatment                                                                                                |
| ----- | ---------------------------------------------- | -------- | ------ | -------- | -------------------------------------------------------------------------------------------------------- |
| S7-G1 | No `Goal` / `OKR` model                        | 4        | M      | **P0**   | New `Goal` (employee_id, period, title, description, key_results, status, progress_pct, parent_goal_id). |
| S7-G2 | No PIP (Performance Improvement Plan) workflow | 3        | M      | P1       | New `PerformanceImprovementPlan` (employee_id, manager_id, start, end, milestones, outcome).             |
| S7-G3 | No 360 feedback                                | 3        | M      | P1       | Extend Appraisal — `AppraisalReviewer` model (peer / direct-report / manager / cross-functional).        |
| S7-G4 | No `SuccessionPlan` model (also S1-G4)         | 3        | M      | P2       | See S1-G4.                                                                                               |
| S7-G5 | No `Competency` model                          | 2        | M      | P2       | Optional. Companies map roles → competencies → assessments.                                              |

---

## Stage 8 — Retain / Exit gaps

| ID    | Gap                                    | Severity | Effort | Priority | Treatment                                                                                                                                                   |
| ----- | -------------------------------------- | -------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S8-G1 | No exit-interview workflow             | 4        | M      | **P0**   | New `ExitInterview` model (employee_id, scheduled_at, completed_at, reason_primary, reason_secondary, would_return, feedback). Triggered on RESIGNED event. |
| S8-G2 | No churn dashboard                     | 4        | S      | **P0**   | Pure aggregation over `EmploymentEvent`. Voluntary vs involuntary, by department, by tenure bucket, last 12 months trend.                                   |
| S8-G3 | No retention-risk scoring (also S1-G5) | 3        | S      | P1       | See S1-G5.                                                                                                                                                  |
| S8-G4 | No alumni / boomerang tag              | 2        | S      | P2       | `Employee.alumni_status: str` (rehire_eligible / not / boomerang).                                                                                          |
| S8-G5 | No tenure-milestone alerts             | 2        | S      | P2       | Cron daily — flag employees hitting 1y, 5y, 10y. Trigger Recognition (S6-G1).                                                                               |
| S8-G6 | No "stay interview" workflow           | 2        | S      | P3       | Optional — proactive retention conversations. Same model as Exit interview, different trigger.                                                              |

---

## Cross-cutting D&I gaps

| ID    | Gap                                                | Severity | Effort | Priority | Treatment                                                                                      |
| ----- | -------------------------------------------------- | -------- | ------ | -------- | ---------------------------------------------------------------------------------------------- |
| DI-G1 | No D&I dashboard summarising the per-stage metrics | 4        | S      | **P0**   | One page that aggregates the 8 D&I metrics already derivable from existing data.               |
| DI-G2 | Demographic completeness scoring                   | 2        | S      | P2       | What % of employees have gender / nationality / DOB filled? Drives the D&I metric reliability. |

---

## Top 12 priority items (P0)

In effort + severity-sorted order — these are the items to ship first
to make the lifecycle narrative real:

1. **S1-G1** — Lifecycle dashboard surface (M, sev 5) — the
   8-stage organising principle the buyer's diagram demands, rendered
   as a card grid (not a wheel graphic)
2. **S2-G1** — Employer-brand fields on Company (S, sev 4)
3. **S5-G1** — `TrainingRecord` model + CRUD (M, sev 5)
4. **S5-G2** — `Certification` model with expiry tracking (M, sev 4)
5. **S5-G6** — Mandatory-training tracker (M, sev 4)
6. **S6-G1** — Recognition module (M, sev 4) — the absent half of
   "Reward, Recognition & Benefits"
7. **S6-G4** — Pay-equity dashboard (S, sev 4)
8. **S7-G1** — Goals / OKR model (M, sev 4)
9. **S8-G1** — Exit-interview workflow (M, sev 4)
10. **S8-G2** — Churn dashboard (S, sev 4)
11. **DI-G1** — D&I dashboard (S, sev 4)
12. **S4-G4** — Onboarding completion analytics (S, sev 3) — fast win

Roughly 6 weeks of focused work for the P0 set if done sequentially,
2–3 weeks if parallelised across multiple agents per session.

The phased plan (`02-plans/01-phased-roadmap.md`) bundles these into
shippable increments with clear "demo-able" checkpoints.
