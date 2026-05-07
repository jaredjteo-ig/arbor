# What we already have — reuse map

The platform has substantial infrastructure that maps directly onto
"survey + targeted delivery + tokenised submission + theme tally +
lifecycle integration". Building Engagement Surveys as a brand-new
silo would be wasteful; this doc lists every existing piece and how
it should be reused vs extended vs left alone.

## Direct conceptual analogue: ExitInterview

The existing exit-interview module is, structurally, an
employee-facing engagement survey with a different trigger
(termination) and a single recipient. Reusable patterns:

| Concern                    | ExitInterview today                                      | Reuse for engagement                           |
| -------------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| Tokenised public link      | `_make_token` / `_decode_token` (JWT, expiry)            | Same helpers, different audience               |
| Anonymous mode             | `is_anonymous` bool zeroes `employee_id` in admin views  | Same — but per-survey not per-instance         |
| Survey JSON payload        | `survey_payload: str` (JSON-as-text)                     | Same shape, broader question schema            |
| Theme derivation           | `_theme_tags()` — Q3 reasons + keyword sweep over Q4/5/6 | Generalize: tags from any tagged question      |
| Submit preflight           | `GET /exit-interviews/public/{token}/validate`           | Same — anti-pattern P36 already codified       |
| Expand-row response detail | Per-row chevron → ResponseDetail card (P45 enrichment)   | Same component family                          |
| Backfill seed              | `backfill_demo_exit_interviews.py`                       | New `backfill_demo_engagement_surveys.py`      |
| Lifecycle dashboard hook   | "retain" stage activity feed entry                       | New "reward" stage tile or shared "engagement" |

**The implication.** The Engagement Survey module should be **a
sibling of ExitInterview, not a replacement and not a generalisation**.
Both submit a tokenised JSON payload. They have different trigger
events (engagement = scheduled cohort launch; exit = termination
event), different cardinality (multiple engagement responses per
employee per year vs one exit interview), and different audience
scopes (engagement = active employees; exit = leavers). Trying to
collapse them into one model would over-couple them.

But: extract the shared primitives into a small `surveys` package or
helper module so the second use of the pattern doesn't copy-paste.

## Question-template reuse with Appraisals

The `AppraisalTemplate` model already has:

```python
sections: str = ""  # JSON: [{title, weight, questions: [{text, type, filled_by, options}]}]
```

This is exactly the shape we need for engagement-survey templates.
Three options:

1. **Reuse the type signature** — define a shared `SurveyTemplate`
   model with the same `sections` JSON shape; `AppraisalTemplate`
   could (eventually) be deprecated in favour of it. Big refactor.
2. **Copy the shape, separate model** — new `EngagementSurveyTemplate`
   with the same `sections` field. Ships fast, mild duplication.
3. **Share question-rendering frontend code** — same Likert /
   multi-select / textarea components, even if backend models differ.

**Recommendation:** option 2 + 3. New `EngagementSurveyTemplate` model
mirroring the JSON shape; the React components for rendering each
question type live in `apps/web/src/components/surveys/` and are used
by both modules.

## Cohort targeting — does this exist?

Partially. The platform has:

- `Employee.department` / `Employee.designation` — for filtering
- `OnboardingAssignment` with `template_id + employee_id_list` —
  similar concept of "assign template to a set of employees"
- `AppraisalPeriod` `launch` endpoint — creates an `Appraisal` per
  active employee at launch time

The Appraisal launch flow is the closest analogue: HR launches a
period, the backend fans out an `Appraisal` row per active employee.
For engagement surveys we want the same fan-out, plus cohort filters
beyond `is_active`.

**What we need to build.**

- A `Cohort` definition: name + filter spec (department, designation,
  pass_type, tenure_band, manager_id, ad-hoc employee_ids).
- A launch endpoint that resolves the cohort to a list of employees
  AT THE LAUNCH TIME and creates one `EngagementSurveyResponse` row
  per employee (in `pending` status).

## Schedule + recurrence — does this exist?

No. The platform has cron entries for `refresh_calendar_watches.sh`
and `send_overdue_reminders.sh`, but no in-app schedule definition.
We need:

- `EngagementSurveySchedule` model: template_id + cohort + cadence +
  next_launch_at + is_active.
- A daily cron tick that finds schedules due, launches them, and
  updates `next_launch_at`.

Reuse the `cron via docker exec` pattern (P16 in security-patterns).

## Notification + delivery

Today the platform has:

- Email infrastructure for invitations, password resets, exit
  interview links
- In-app `/notifications` (per the alerts model) — admin-only currently
- Activity feed on lifecycle dashboard

For engagement surveys, employees need to know they have a survey
waiting. Three channels:

1. **Email with tokenised link** (reuse exit-interview pattern)
2. **In-app card on `/my-dashboard`** (new — shows pending surveys)
3. **Sidebar badge** on `My Dashboard` (small UI; defer to v2 if
   tight on time)

For v1 ship 1 + 2.

## Theme analysis

The exit-interview `_theme_tags` does a deterministic Q3-reasons +
keyword sweep over free-text. It works but it's crude. For engagement
surveys we want theme analysis across a population of responses
("3 of 28 employees mentioned 'manager'; 5 mentioned 'workload'").

Two paths:

- **v1 (ship now):** generalize `_theme_tags` to accept a list of
  responses + a tag list, return per-tag count. No LLM.
- **v2:** LLM-driven sentiment + theme clustering using the existing
  advisory engine (Gemini 2.5 Flash). Run on a batch of submitted
  responses; store derived themes per submission. The existing
  budget-cap (P13) still applies.

## Lifecycle dashboard integration

Currently the lifecycle dashboard has 8 stage cards: Strategy,
Attract, Recruit, Onboard, Learning, Reward, Progression, Retain.
Engagement signals fit naturally under **Reward** (today this shows
kudos count + payroll OK status).

**Proposed addition.** Reward stage gets a new metric: "Engagement
score (last pulse)" — average of the latest pulse's Likert questions,
expressed as 0-100. Click-through to `/engagement` admin view.

The activity feed already shows `Kudos for X` and `Exit interview
submitted: Y`. Add `Engagement pulse submitted: Y` (round-3 click-through
pattern P46 — entity_type=engagement_survey, entity_id=response.id,
href=/engagement).

## Cross-stage analysis (the demo's killer flow)

The brief's success criterion calls out the cross-reference value:

> "of the 3 employees who resigned this quarter, 2 cited 'growth' in
> their exit interview AND scored 1-2 on Q4 (career growth) in the
> last engagement pulse before resigning"

Building this requires:

- An aggregation endpoint that joins `EmploymentEvent` (RESIGNED) +
  `ExitInterview.themes` + `EngagementSurveyResponse.scores`.
- A "lifecycle insight" card on the lifecycle dashboard.

This is a v2 deliverable but the v1 data model MUST not block it —
specifically, `EngagementSurveyResponse` MUST persist the Likert score
per question (not just an aggregate) and MUST be queryable by
employee_id + period.

## What we're NOT building

- A general form builder (out of scope; we want survey-shaped, not
  arbitrary forms).
- 360-degree review surveys (lives under appraisals).
- Survey-as-a-service for non-employees (customers, applicants — that's
  a different product surface).
- Real-time live polling during meetings.

## Summary of what to build vs reuse

| Component                        | Build new          | Reuse                                                 |
| -------------------------------- | ------------------ | ----------------------------------------------------- |
| Survey template + questions JSON | New model          | Copy `AppraisalTemplate.sections` shape               |
| Tokenised public link            | —                  | `_make_token` / `_decode_token` helpers               |
| Anonymous mode                   | —                  | `is_anonymous` pattern from ExitInterview             |
| Cohort definition + resolver     | New                | —                                                     |
| Schedule + recurrence            | New                | Cron-via-docker-exec pattern (P16)                    |
| Per-employee response row        | New                | One-per-employee fan-out from launch endpoint pattern |
| In-app delivery                  | New page           | Existing AppShell + ProtectedRoute                    |
| Email delivery                   | —                  | Existing email service                                |
| Theme tally                      | Extend             | `_theme_tags` from ExitInterview                      |
| Response detail expand UI        | —                  | P45 enrichment-and-detail pattern                     |
| Lifecycle dashboard tile         | New tile in Reward | `_activity` feed + `entity_type` pattern              |
| Cross-stage analytics            | v2                 | —                                                     |
