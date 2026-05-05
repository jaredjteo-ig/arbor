# 01 — Employee Lifecycle Decoded for Singapore SME / Arbor Context

**Source:** Steven AJ Cox 2019 — 8-stage Employee Lifecycle (reference
diagram only; the wheel graphic is NOT reproduced as a UI element)
**Reframing:** What each stage actually means for a 20–200 person Singapore
SME using Arbor (vs. a multinational HR-tech buyer's lens).

The Cox model is a useful skeleton but it was drawn for a UK-style large
corporate with strong D&I governance. Singapore SMEs have different real
constraints: TAFEP-level fair-employment compliance, MOM-driven foreign
manpower restrictions, statutory leave/CPF, and a much smaller pool of HR
practitioners (often one HR generalist for the whole company). The decode
below is grounded in that operational reality.

---

## Stage 1 — Strategy (centre)

**Cox:** "Strategic workforce plan designed to deliver corporate strategy."

**SG-SME translation:**
The "workforce strategy" for an SME is rarely a board-deck exercise. It's
more often three concrete questions the owner / HR head answers quarterly:

1. **Headcount plan** — how many people do we need, in which roles, by when,
   to hit revenue/operations targets? (Anchored against MOM quota / levy
   ceilings if foreign workers are in scope.)
2. **Skills gap** — what capabilities are we short on (SkillsFuture
   investments, certifications, leadership readiness)?
3. **Retention risk** — who's flight-risk? What's the resignation
   probability on critical roles? Where do we need succession?

**Data points already collected on Arbor today:**

- `Company.headcount_local` / `_pr` / `_ep` / `_sp` / `_wp`
- `Employee.designation` + `department` + `start_date` + `is_active`
- `EmploymentEvent` (HIRED, PROMOTED, RESIGNED, TERMINATED, RETRENCHED)
- Headcount math by `EmploymentEvent` aggregation per period
- `CompanyPolicy` for leave/work-arrangements but no documented "workforce
  strategy" anywhere

**Missing for full Strategy stage:**

- A persisted **headcount plan** vs. actual (no model for this today)
- A **skills inventory** per employee (no model — `Employee` has
  `designation` but no skills array)
- A **succession map** for critical roles (no model)
- Retention risk score per employee (could be derived; not surfaced)

**HR activities this stage drives:**

- Quarterly headcount review
- SkillsFuture credit allocation & ROI tracking
- "Critical role" tagging + succession planning
- Workforce dashboard the CEO actually opens once a quarter

---

## Stage 2 — Attract

**Cox:** "Being an appealing inclusive employer."

**SG-SME translation:**
For a 50-person SME, "Attract" is mostly: a public careers page, employer
branding (Glassdoor / LinkedIn presence), and word-of-mouth from current
employees. Sophisticated employer-brand campaigns are out of scope. What
matters operationally:

1. A **public-facing careers page** that lists open jobs with a
   one-click-apply form
2. **Source diversity tracking** — where do quality candidates come from?
   Today Arbor captures `Candidate.source` (linkedin, jobstreet, referral,
   direct, careers_page, etc.).
3. **TAFEP-compliant job ads** — no biased language, age-neutral, etc. —
   Arbor's `Check Compliance` button on job listings already addresses this.

**Currently in Arbor:**

- `GET /recruitment/careers/{company_slug}/jobs` — public listing
- `GET /recruitment/careers/{company_slug}/jobs/{job_slug}` — public detail
- `POST /recruitment/careers/{company_slug}/jobs/{job_slug}/apply` — public apply
- `Check Compliance` button on each job listing (TAFEP screening via LLM)
- `Candidate.source` enum tracks where applicants came from

**Missing:**

- A public **company careers page** (`/careers/{company_slug}`) actually
  rendered as a frontend page (the API exists; not sure the public route is
  rendered for prospective candidates).
- **Employer brand assets** (logo, mission, benefits summary) attached to
  Company — `Company` model has `name`, `uen`, `sector`, `headcount_*`, but
  no `mission`, `tagline`, `benefits_summary`, `culture_pillars`.
- **Source ROI metrics** — a dashboard showing which source produces the
  most hires / highest retention.

---

## Stage 3 — Recruit

**Cox:** "Enabling all talent to successfully apply."

**SG-SME translation:**
This is the operational heart of `routers/recruitment.py`. For an SME, the
end-to-end recruitment story is: post a job → receive applications →
screen → interview → hire → trigger onboarding. Already well-covered.

**Currently in Arbor (very strong):**

- `JobListing` + `Candidate` + `InterviewSchedule` + `Offer` + `ScorecardEntry`
  - `ScorecardTemplate` + `JobScreeningQuestion` + `InterviewFeedback`
- 56 endpoints in `recruitment.py` covering: listings, public-apply,
  candidates CRUD with stage state-machine, interviews (now with display_type
  - is_overdue per today's polish), AI scorecards (with quota cap), offers,
    hires, screening questions, compliance scan
- TAFEP compliance scan, AI scorecard generation, panel interviews
- Auto-assign onboarding on hire (saga-protected per S2-T2)

**Gaps:**

- **Talent pool** — rejected/withdrawn candidates aren't tagged for "good fit
  for future role". The `Candidate.stage` includes `rejected` and `withdrawn`
  but there's no "future re-engagement" pool.
- **Diversity dashboard for Recruit** — % candidates by source × stage
  conversion rate; where in the funnel does diversity drop off? Not surfaced
  today.

---

## Stage 4 — Onboard

**Cox:** "Ensuring all talent is understood and all staff trained."

**SG-SME translation:**
For SG SMEs the onboarding load is concrete: KETs (Key Employment Terms)
issued, CPF enrolment, work pass linkage if foreign worker, equipment
provisioning, first-week training. The "talent understood" part includes
profile setup (NRIC/FIN, bank, emergency contact, tax info).

**Currently in Arbor (very strong, recently hardened):**

- `OnboardingTemplate` + `OnboardingModule` + `OnboardingStep` (with
  `is_active` for soft-delete per S3-T5) + `OnboardingAssignment` (with
  `last_reminder_sent_at` for S4-T4 cron debounce) + `OnboardingStepProgress`
- 41 endpoints in `onboarding.py` — templates, assign, complete steps,
  preboarding tasks (5 tasks × 4 trigger points), reminders cron
- Full Excel template import
- Drag-and-drop step reorder (per S4-T5 today)

**Gaps:**

- **Buddy programme tracking** — `OnboardingAssignment.buddy_employee_id`
  exists but nothing surfaces it as a workflow ("schedule weekly buddy
  check-in for first 90 days"). Just a column.
- **30/60/90-day review cadence** — no first-class concept; would need to
  ride on `Appraisal` model.
- **Pulse / sentiment surveys during onboarding** — no model.

---

## Stage 5 — Learning & Development

**Cox:** "All talent represented and included."

**SG-SME translation:**
For SG SMEs this is dominated by **SkillsFuture credits**, internal training
ledger, and ad-hoc mentoring. Arbor has a SkillsFuture integration but
**no internal L&D record-keeping module**. This is the largest under-served
stage on the platform.

**Currently in Arbor (thin):**

- `GET /integrations/skillsfuture/courses` — discover SkillsFuture courses
- `GET /integrations/skillsfuture/courses/{course_id}/grant-check` —
  eligibility check
- Frontend page at `/training/skillsfuture`
- That's it. No internal "training record", no certification tracking, no
  learning plan per employee.

**Gaps (large):**

- **No `TrainingRecord` model** — record of who took what training, when,
  cost, outcome.
- **No `Certification` model** — first-aid certs, professional certs that
  expire, etc. (Highly relevant for WSH compliance.)
- **No learning plan per employee** — can't say "Sarah's plan for FY26: X, Y,
  Z courses, Y mentor sessions."
- **No L&D budget tracking** — per-team or per-employee L&D budget consumed.
- **No learning catalogue** — internal courses, mandatory learning,
  optional growth tracks.

---

## Stage 6 — Reward, Recognition & Benefits

**Cox:** "All talent's needs catered for."

**SG-SME translation:**
Reward is **payroll + bonuses** (monetary). Benefits are **leave / claims /
group insurance / wellness perks** (non-monetary or in-kind). Recognition is
**peer kudos / employee-of-the-month / spot bonuses** — soft, social.

The first two are well-covered. **Recognition is virtually absent.**

**Currently in Arbor (strong on Reward & Benefits):**

- Payroll engine (zero-LLM, deterministic) — payslips, CPF, IR8A, IR21,
  GIRO bank files
- `SalaryComponent` model — base, allowances, deductions, bonuses,
  recurring + one-off
- Leave (10+ statutory + custom leave types, balances, encashment, off-in-lieu)
- Claims (categories, groups, co-payment, submission, approval, BIK)
- `BenefitInKind` partially covered via claims

**Currently absent on Recognition:**

- No `Kudos` / `Recognition` / `PeerNomination` model
- No "employee of the month / quarter" workflow
- No public recognition wall / feed
- No spot-bonus tooling integrated with payroll

**Gaps (medium):**

- A **Recognition module** would be a cheap-to-build, high-visibility
  product win — peer kudos, manager nominations, periodic "employee of
  the month" with a feed-style recognition wall.
- **Pay equity dashboard** — male/female pay gap, citizenship pay gap, etc.
  All data exists (`Employee.gender`, `nationality`, `salary_monthly`); not
  surfaced.

---

## Stage 7 — Progression & Performance

**Cox:** "All talent performance management consistent."

**SG-SME translation:**
For SG SMEs this is **annual / semi-annual appraisals**, **goal tracking**,
**promotion workflow**, **succession planning**, and **PIP** (performance
improvement plans). Arbor has appraisals.

**Currently in Arbor (medium):**

- `AppraisalTemplate` + `AppraisalPeriod` + `Appraisal` models
- 5 endpoints in `appraisals.py` for templates / periods / reviews / sign-off
- `EmploymentEvent.PROMOTED` records promotion events
- `EmploymentEvent.SALARY_REVISION` records salary changes

**Gaps (significant):**

- **No goal-tracking model** (OKR / SMART goals). Appraisal is point-in-time;
  ongoing goals + progress tracking is absent.
- **No PIP workflow** — can be built on top of Appraisal, but the explicit
  "this employee is on a 90-day PIP, here are milestones" flow is missing.
- **No 360 feedback** — peer / direct-report / cross-functional input on
  appraisals.
- **No succession map** — who is next-in-line for which roles?
- **No competency model** — what does "Senior Software Engineer at this
  company" actually require?

---

## Stage 8 — Retain / Exit

**Cox:** "Talent that wants to stay. Learn from & manage exits."

**SG-SME translation:**
Two halves:

1. **Retain:** churn-risk dashboard, retention programmes (e.g. anniversary
   bonuses), tenure milestones.
2. **Exit:** resignation workflow (notice period, handover checklist,
   final-pay calc, IR21 for foreign workers, exit interview).

**Currently in Arbor (medium-strong):**

- `EmploymentEvent.RESIGNED` / `TERMINATED` / `RETRENCHED` for event log
- `Employee.notice_period_days` + `end_date` fields
- Final-pay calc (payroll handles exit-month payroll specifically)
- IR21 generation for foreign-worker tax-clearance
- Probation confirmation workflow (`confirmation_status`,
  `probation_end_date`)

**Gaps (medium):**

- **No exit interview workflow** — no `ExitInterview` model, no template, no
  comparative analytics ("top 5 reasons people are leaving").
- **No churn dashboard** — voluntary vs. involuntary, by department, by
  tenure-bucket. The data exists in `EmploymentEvent`; no aggregation page.
- **No retention-risk scoring** — could derive from time-since-promotion,
  appraisal score, days-since-pay-rise, leave usage patterns.
- **No alumni / boomerang tracking** — terminated employees stay
  `is_active=False`, but no "we'd hire them again" tag or alumni
  re-engagement workflow.

---

## Cross-cutting: D&I lens (Cox 2019 emphasis)

The Cox model places D&I as a **transverse concern** at every stage, not its
own stage. The captions in the original Cox diagram each include an inclusion
clause. For Arbor that translates to:

| Stage       | D&I metric (derivable from existing fields)        |
| ----------- | -------------------------------------------------- |
| Strategy    | Headcount plan diversity targets vs. actual        |
| Attract     | Source-of-applicant diversity (`Candidate.source`) |
| Recruit     | Stage conversion by gender / nationality           |
| Onboard     | Onboarding completion % by demographic             |
| L&D         | Training hours by demographic                      |
| Reward      | Pay gap by gender, citizenship, race               |
| Progression | Promotion rate by demographic                      |
| Retain/Exit | Voluntary churn by demographic                     |

All of these are derivable from already-collected fields on `Employee`.
None require new PII.

---

## Strategic implication

The Cox lifecycle is a useful **organising lens**, not a replacement
architecture. Arbor already has stages 3 (Recruit), 4 (Onboard), and 6
(Reward & Benefits) at strong coverage. Stages 5 (L&D) and 7 (Progression
beyond appraisal) and the Strategy hub itself are the largest gaps.

The buyer-facing value is: **wrap what we already have in a lifecycle
narrative**, then close the gaps in priority order. See
`02-current-state-mapping.md` for the per-stage coverage rating.
