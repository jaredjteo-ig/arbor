# Red-team findings — engagement-survey analysis

Reviewer: deep-analyst subagent. Severity rated by demo-credibility +
implementation risk.

## CRITICAL — must fold into plan before /todos

### C1. Cohort drift — pending responses for terminated employees

A response row is created at launch with a fixed `employee_id`. If
that employee resigns during the open window, what happens?

**Decision.** Add `is_void: bool = False` to `EngagementSurveyResponse`.
The existing employee-termination flow (in `employees.py` deactivation
path) gains a sweep:

```python
# In the termination handler, after marking User inactive:
dataflow_crud.list_records("EngagementSurveyResponse", {
    "employee_id": emp_id, "submitted_at": None
})
# → batch update is_void=True
```

Aggregations exclude `is_void=True`. `target_count` recomputes on
read — `target_count - voided_count`. Update `02-plans/01-data-model.md`
in the next revision.

Also: pin `triggered_at` semantics. Set it to `launched_at` on
response creation so the public-link audit-trail is consistent.

### C2. Anonymous mode breaks the killer demo flow

The brief's value proposition is the lifecycle cross-reference: "of
the 3 who resigned, 2 cited growth in their exit interview AND scored
1-2 on Q4 in their last engagement pulse." That join requires the
engagement response → employee_id link.

But anonymous mode (the recommended default for pulse) **zeros
employee_id at submit**. The cross-reference becomes impossible for
anonymous surveys, contradicting market positioning that pushes
anonymity.

**Decision — three-tier anonymity model:**

| Tier           | Stored on response                                                                      | Aggregation                                                     | Cross-stage join    |
| -------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------- |
| `identified`   | full `employee_id`                                                                      | name visible to admin (subject to P33)                          | yes                 |
| `pseudonymous` | `employee_pseudonym = HMAC(company_secret, employee_id+survey_id)` ; employee_id zeroed | name not visible; same employee across surveys = same pseudonym | yes (via pseudonym) |
| `anonymous`    | employee_id zeroed; no pseudonym                                                        | name not visible                                                | no (intentional)    |

**Default for pulse:** `pseudonymous` — admins can correlate trends
without de-identifying. Annual long-form surveys default to
`identified`. True `anonymous` is opt-in for sensitive checks (e.g.
"reporting harassment").

The HMAC secret is per-company, stored encrypted alongside other
company secrets, and never exposed in API responses. The pseudonym is
deterministic per (company, employee, survey) so trend lines work,
but a leaked pseudonym alone reveals nothing about identity.

This is a v1 schema decision — adding pseudonym in v2 means migrating
historical responses (lossy if the secret was generated at v2 launch).

Update brief, methodology, data model, plan, user flows.

### C3. Template edits after launch silently corrupt analytics

`EngagementSurvey` references `template_id`. If Grace later edits
`template.sections` and changes Q4's text from "career growth" to
"team morale", every aggregator that reads via the template gets the
wrong question text → cross-stage analytics ("scored low on growth")
becomes silently false.

**Decision.** `EngagementSurvey` snapshots the template's `sections`
JSON onto a new field `template_sections_snapshot: str` at launch.
Aggregator reads the snapshot, never the live template. Template
edits affect only future launches.

Add `template_id` references for traceability but mark them as the
"original template at launch — sections may have changed since."

## MAJOR — must address in plan, can ship as v1

### M1. Anonymity threshold per-question per-cohort intersection

By-cohort suppression at `n<5` is not enough. A free-text question
answered by only 4 of 28 in a 30-person company is also leaky. The
aggregator must enforce `n_with_response >= 5` PER QUESTION PER COHORT
intersection. Update the aggregate response shape: each question entry
gets `n` and `is_anonymity_safe`; UI suppresses both.

P33 / P34 already cover this conceptually; the API contract just needs
to honour it explicitly per cell.

### M2. Schedule overlap protection

Cron tick must skip launching a new survey if `last_launched_survey_id`
is still open. Either auto-close the prior survey OR skip the tick OR
alert HR. **Pick:** skip + alert. Add `EngagementSurveySchedule.last_skipped_at`
to surface a yellow card on the admin schedule view.

### M3. Survey-overlap detection at launch

`POST /surveys/launch` should scan for open surveys whose cohort
intersects the new launch's cohort. If overlap detected, return a
warning (not a block) — Grace can still launch but sees a confirmation
modal.

### M4. Email fan-out queue

Launching to 28 employees within a single request is fine. Launching
to 280 will time-out the request. Even 28 needs retry-on-failure.

**Decision:** add `EmailDeliveryJob` (existing or new) — launch
endpoint enqueues; a worker drains. For the demo (28 employees) we can
enqueue + drain inline, but the schema must support async drain so
larger customers don't time out.

### M5. Tighten public-submit rate limit

`POST /public/{token}/submit` is currently capped at 10 / hour /
token. Should be: 1 successful submit per token (already enforced via
`already_submitted` check), plus 5 / hour / token for failed-validation
attempts. Prevents payload-enumeration probing.

## SINGAPORE-SPECIFIC

### S1. PDPA consent notice — needs versioning

Add `consent_notice_version: str` on `EngagementSurveyResponse`. Render
the consent string in the public-preflight response so the employee
can see exactly what they're agreeing to. Future versions don't
retroactively change historical consent records.

### S2. Legal review for FWA / TAFEP question prompts

The `singapore_sme_quarterly` shipped template includes prompts about
"fairness", "raising concerns" — these touch TAFEP territory. Before
shipping the template content, run it past an employment-law specialist
(the platform has `sg-employment-law-expert` agent — invoke during
implementation).

## MINOR

### m1. `enps_score: int = -1` sentinel

Switch to `Optional[int] = None`. Modern Python; matches other
nullable fields.

### m2. LLM theme analysis cost ceiling

P13 caps per-tenant per-day. A 200-person customer with 4 free-text
questions = 800 LLM calls per pulse. Add a per-survey batch ceiling:
process the first 50 unique responses, then defer. Cite in P3 plan.

### m3. Confirm `Employee.start_date` exists

Cohort `tenure_min_days` resolver depends on this field. Verified in
`models/company_user.py:441` — exists. Document the dependency in the
plan.

### m4. Use response_id (not survey_id) in employee URLs

`/my-engagement-surveys/[id]/respond` — the `id` should be the
response_id (per-employee), not the survey_id. Otherwise an employee
could probe other employees' response_ids by URL manipulation. Already
implicit in the API spec but make it explicit in the frontend plan.

## Status

C1-C3 fold into the data model + plan revision next pass. M1-M5 are
incorporated as "v1 must include". S1-S2 are pre-launch checklist
items. Minor items roll into implementation.

Plan stays at three phases (P1 / P2 / P3). The C-tier findings shift
schema-related work into P1 (already there); the analytics decisions
strengthen the cross-stage USP without expanding scope.
