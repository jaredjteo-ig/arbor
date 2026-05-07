# Engagement-survey todo red-team — round 2

Reviewer: deep-analyst subagent.
Scope: every todo file in `workspaces/engagement-survey/todos/active/`,
the source plans in `02-plans/`, the user flows in `03-user-flows/`,
the round-1 redteam in `04-validate/00-redteam-findings.md`.

> **Note on file enumeration.** This environment has no directory-list
> tool; only `Read` against absolute paths. M0-foundations,
> M1-data-model, M2-admin-template-cohort, and X-cross-cutting were
> read directly. M3-M10 file _names_ could not be confirmed — the
> exact-path attempts (~50 plausible kebab-case combinations) all
> returned `File does not exist`. Findings against M3-M10 are inferred
> from cross-references in the X file, the plan documents, and the
> task-number ranges (T01-T06=M0, T10-T17=M1, T20-T24=M2 → M3+ owns
> T30+, M6 owns T61, M9 owns T90/T93). Any finding labelled
> `[INFERRED-MILESTONE]` should be checked against the actual file by
> the human reviewer; if the milestone already covers it, drop the
> finding.

## Headline counts

- **H (high — would block ship): 14**
- **M (medium — would cause rework): 23**
- **L (low — nice to have): 11**
- **Total: 48**

## H findings

### [H1] No backend route to actually deliver the killer cross-stage panel

**What's missing.** The brief and `03-user-flows/01-grace-launches-pulse.md`
Step 7 promise the demo's value-flow: "of the 3 who resigned this
quarter, 2 cited growth in their exit interview AND scored 1-2 on Q4
in the last engagement pulse before resigning." `02-plans/02-api-and-routes.md`
mentions a "lifecycle dashboard hook" but no concrete endpoint shape,
no controller, no aggregation SQL/DataFlow node, no `entry_type` for
the activity feed beyond a single example object.

**Why it matters.** This IS the demo. If M9/M10 lands without a
specific endpoint like `GET /strategy/lifecycle/engagement-resignation-correlation`
returning a tested JSON shape, the demo storyboard step 4 collapses to
"trust me there's a panel." Round-1 C2 flagged the data-model
implication (pseudonymous tier preserves the join); the join logic
itself is unbuilt.

**Suggested fix.** Add to **M9 (cross-stage / manager view)** a
T-task like:

- T9X-correlation-endpoint: define payload shape `{window_days, resigned_count, low_engagement_resigned_count, pseudonym_join_strategy, sample_employees: [{name OR pseudonym, exit_themes, last_engagement_likert, days_between_pulse_and_resignation}]}`.
- Implement the join (`EmploymentEvent` RESIGNED in last 90 days → join `EngagementSurveyResponse` by `employee_id` for identified, by `employee_pseudonym` for pseudonymous).
- Acceptance: against seeded data, returns >=2 correlated rows; n<5 cohorts return suppressed bucket.

### [H2] Anonymity invariant #4 is unenforceable as written — `n < 5` is per-cohort but aggregator can't compute it without first reading employee_id

**What's missing.** X2 invariant #4 says "Aggregator never returns a
per-question OR per-cohort cell with `n < 5` AND `is_anonymity_safe == true`."
For `pseudonymous` and `anonymous` tiers, `employee_id` is zeroed at
submit. There's no department/manager attribute on the response row,
so the aggregator cannot compute per-cohort `n` without joining back
to `Employee` — but the join requires identity, which we just stripped.

**Why it matters.** Either (a) we silently denormalise department onto
the response (leaks identity at the row level — single-Eng-resp pair

- free-text gives identity away), or (b) the by-cohort tab shows only
  `identified` surveys, contradicting the plan's "Engineering 3.2 vs Sales
  4.4" demo-storyboard moment which uses an anonymous pulse.

**Suggested fix.** Add to **M1 (data model)** a new field
`response_cohort_attributes: str` (JSON, populated at submit time from
the employee's then-current department/pass_type/tenure_band/manager_id
**before** identity stripping). Aggregator reads this. Document that
it's a frozen snapshot — termination/transfer doesn't rewrite.
Add tests pinning that `response_cohort_attributes` is set on every
response regardless of tier and that the aggregator computes `by_cohort`
from it, never from a live `Employee` join. Update X2 invariant #4 to
reference this field.

### [H3] Concurrent same-cohort launches by two admins have no per-tenant lock

**What's missing.** Co-admins Grace and Bob each click "Launch" within
the same minute on the same template+cohort. Each thread:

1. resolves cohort → 28 employee_ids
2. creates 28 EngagementSurveyResponse rows
3. mints 28 tokens
4. enqueues 28 emails

The user explicitly asked: does the overlap check actually catch this?
Answer from the todos as written: **no.** T24 (`find_overlapping_surveys`)
is a _helper_ and the launch wizard surfaces it as a _warning_ (M3 from
round-1). There is no per-(company_id, cohort_id) lock at the launch
endpoint to serialise concurrent launches. Grace and Bob both pass the
warning, both proceed, and now the same employees get two response
rows + two emails for "the same" survey.

**Why it matters.** Pattern P-per-tenant-locks (security-patterns.md)
exists exactly for this. Skipping it leaves users double-emailed at
launch and the response_count counter racing on parallel submits
(also untreated — see [H4]).

**Suggested fix.** Add to **M3 (launch flow)**:

- T3X-launch-lock: acquire per-`company_id` advisory lock (or
  `threading.Lock` keyed by company_id) for the duration of the launch
  transaction. Inside the lock, re-run the overlap check against
  freshly-read open surveys (TOCTOU-safe).
- Acceptance: parallel-launch test (`pytest -n 2`) with two threads
  hitting the same cohort produces exactly one survey row, not two.

### [H4] `response_count` counter increments are not atomic

**What's missing.** The schema defines `EngagementSurvey.response_count`
as a denormalised counter. Public-submit and in-app-submit both bump
it. With 28 employees on a closing day, multiple submits land in the
same second. There's no `UPDATE ... SET response_count = response_count + 1`
or transactional CAS in any todo file I read. Today's typical
DataFlow `update_record({"response_count": current+1})` is a TOCTOU
read-modify-write.

**Why it matters.** "Response rate 25/28" on the detail page becomes
"22/28" or "27/28" intermittently. The Lifecycle activity feed depends
on it. The auto-close guard (M9 P3) "all employees responded" depends
on it. Demo-credibility-killer.

**Suggested fix.** Add to **M3 or M4 (submit flow)**:

- T-submit-counter: use an atomic SQL increment (`UPDATE survey SET
response_count = response_count + 1 WHERE id = ?`) inside the same
  transaction as the response insert. OR derive `response_count` on
  read (`SELECT count(*) FROM responses WHERE survey_id=? AND submitted_at IS NOT NULL`)
  and drop the denormalised counter — fewer integrity headaches.
- Acceptance: parallel-submit test with 10 threads = exactly 10 final
  response_count, never 9 or 11.

### [H5] No idempotency key on the public submit endpoint

**What's missing.** Round-1 M5 tightened rate limits on
`POST /public/{token}/submit` to 5/hr/token but didn't add an
idempotency key. Mobile carrier retries (network drops in Lily's
flow Step 4 says "retries once with exponential backoff") will fire
two submits if the first 200 OK didn't reach the phone. Result: two
EngagementSurveyResponse rows for the same employee, double-counting
the cohort, double-bumping response_count.

**Why it matters.** Pattern P-idempotency in security-patterns.md
exists for this. Without it: aggregations are wrong by 1-3% for any
survey with mobile respondents on flaky networks (every demo).

**Suggested fix.** Add to **M3 or M4 (public submit)**:

- T-submit-idempotency: accept `Idempotency-Key` header (or derive
  from `token + sha256(payload)`); if a successful submit exists for
  this key in the last 24h, return the prior response unchanged
  (200 OK, body `{ok: true, idempotent_replay: true}`).
- Acceptance: identical submit twice → one row; different payload
  same token → reject with `already_submitted`.

### [H6] Email partial-failure rollback path is undefined

**What's missing.** Round-1 M4 added an `EmailDeliveryJob` queue (T06)
but no compensating action when launch succeeds and email enqueue
fails halfway through (29 employees, 14 emails enqueued, then queue
dies). The user's question lists this exactly: "if launch fails
halfway through (some response rows created, email queue partially
populated), can we recover?" Answer from the todos: no rollback shape.

**Why it matters.** Saga-compensation (P1, security-patterns.md) is
the canonical pattern. Without it, Grace launches a survey, sees
"toast: 28 emails queued" because the response rows wrote, but only
14 got tokens, the other 14 are unreachable forever (no in-app
notification yet, see [M-x]).

**Suggested fix.** Add to **M3 (launch flow)**:

- T-launch-saga: structure launch as: (1) create survey row,
  (2) bulk-create response rows, (3) bulk-enqueue emails — each in
  its own try/except with reverse-order compensation (delete
  responses, soft-delete survey, log the failure). OR: make
  email-enqueue a post-commit hook with at-least-once delivery — if
  any email fails, mark survey `email_delivery_status: partial` and
  expose a "Retry queue" admin button.
- Acceptance: kill the email queue mid-launch → survey detail page
  shows "14/28 emails delivered, 14 retrying" banner (already in user
  flow Step 4 failure modes!) backed by a real status field.

### [H7] In-app notification path is asserted in user flow but missing from any todo

**What's missing.** `03-user-flows/01-grace-launches-pulse.md` Step 4
toast says "28 emails queued; **28 in-app notifications sent**." But
no todo file (M0-M2 read; M3+ inferred) lists creating a `Notification`
row, or hooking the existing `Notification` model, for engagement
launches. X7 Q3 even asks "Does the existing Notification model already
cover what T06's EmailDeliveryJob needs?" — investigation, not
implementation.

**Why it matters.** Lily's Path B (`/my-dashboard` "1 pulse open · closes
in 3 days") depends on a Notification row existing. Without it the
employee never sees the pending card. Toast lies to Grace.

**Suggested fix.** Add to **M3 (launch flow)** OR **M5 (employee
self-service)**:

- T-notification-fanout: on launch, create a `Notification` row per
  response (`kind="engagement_pending"`, `link="/my-engagement-surveys/{response_id}"`).
- Frontend `/my-dashboard` reads the existing notification feed; pending
  card derived from there.
- Acceptance: after launch, `GET /notifications/me` includes one row
  per recipient.

### [H8] Token-kind grace period (T01) has no expiry-enforcement task

**What's missing.** T01 says "treat missing `kind` as `'exit'` for a
30-day grace; after that, reject." X5 lists the calendar but no
T-task tags the cleanup. There is no follow-up todo, no GitHub issue,
no test assertion that fails if the legacy fallback is still in code
on day 31. The X5 "Cleanup: remove the legacy fallback in code" line
is the only thing marking it.

**Why it matters.** Forgotten grace periods become permanent legacy
exposure. A token from May 2026 could be replayed against the
engagement endpoint in May 2027.

**Suggested fix.** Add to **M0 or M10 (codify)**:

- T-token-grace-cleanup: write the cleanup as a _failing_ test
  guarded by a date check (`if datetime.utcnow() > T01_lands_at + 30d:
assert "kind" in token`). When the test starts failing, the human
  knows to delete the fallback. Wire into CI.
- Acceptance: test passes today; fails 31 days after T01 lands until
  the legacy fallback is removed.

### [H9] CSRF on in-app submit endpoint not specified

**What's missing.** `POST /engagement-surveys/my-responses/{id}/submit`
takes auth via Bearer (per plan). FastAPI Bearer endpoints are
typically CSRF-immune _if_ the cookie isn't being sent. But the rest
of the platform uses the cookie session (per round-7 codify and
auth-security.md). The in-app submit therefore needs the existing
CSRF protection or a documented exemption. No todo addresses it.

**Why it matters.** A malicious page in another tab could `fetch()`
the submit endpoint with the user's cookie and forge a response.
Especially nasty on identified surveys.

**Suggested fix.** Add to **M5 (employee self-service)** OR **X1
checklist**:

- T-csrf-in-app: assert `Origin`/`Referer` matches the configured app
  origin OR require a CSRF token header. Document the choice.
- Acceptance: cross-origin POST with valid bearer is rejected 403.

### [H10] No test pins the "voided employee can't submit" path

**What's missing.** T17 (termination sweep) sets `is_void=True` on
pending response rows. The public preflight is supposed to return
`{ok: false, reason: "voided"}` (T17 acceptance). But:

- No test asserts the in-app `/my-responses/{id}/submit` path also
  rejects with 410 for `is_void=True` rows.
- No test asserts the employee's `/my-pending` list excludes voided
  rows.
- The dispatcher could happily process a submit on a voided row,
  silently restoring the employee's data into the survey.

**Why it matters.** Round-1 C1 was _the_ critical anonymity-invariant
breach — terminated employees still seeing surveys leaks both
identity (they show on the response list) and data (they shouldn't be
counted). The remediation needs a test pinning every entry path, not
just the public one.

**Suggested fix.** Add to **M6 (regression tests)** in T61's pin:

- Test matrix: `(public-submit, in-app-submit) × (is_void=True,
is_void=False) × (anonymity_tier ∈ {identified, pseudonymous,
anonymous})` = 12 cells. Voided rows return 410 in every cell.
- `/my-pending` excludes voided rows. `/aggregate` excludes voided.

### [H11] Pseudonym secret rotation is undefined — leak == permanent compromise

**What's missing.** T03 introduces `Company.engagement_secret` for
HMAC. There's no rotation path. If the secret leaks (insider
extraction, DB backup compromise), every historical pseudonym is
permanently re-identifiable for as long as the response data exists,
because the same (secret, employee_id, survey_id) tuple is
reproducible by the attacker.

**Why it matters.** PDPA + S1 consent versioning rely on pseudonym
acting as a one-way curtain. Without rotation, "we promised
pseudonymity" becomes "we promised pseudonymity until our DB leaks."
This is a privacy-review-readiness blocker.

**Suggested fix.** Add to **M1 (data model)** OR **M0 (foundations)**:

- T-pseudonym-rotation: model `Company.engagement_secret` as a
  versioned field (`engagement_secret_v1`, `engagement_secret_v2`,
  etc.) with `engagement_secret_active_version: int`. Responses store
  `pseudonym_version` so verification still works. Document a rotation
  runbook (rotate every N months OR on incident).
- Acceptance: rotation procedure produces NEW pseudonyms for the same
  (employee, survey) post-rotation; pre-rotation pseudonyms remain
  valid and readable for trend analysis up to the rotation point.

### [H12] PDPA admin-access audit logging is checklist-only, not a task

**What's missing.** X1 lists "PDPA `consent_notice_version` recorded
on every response" and X4 says "Audit trail: PDPA-relevant access
(admin reading non-anonymous responses) flows through the existing
`_log_pdpa_access()` helper." But there's no T-task wiring
`_log_pdpa_access()` into:

- `GET /engagement-surveys/surveys/{id}/responses` (admin reads)
- `GET /engagement-surveys/surveys/{id}/export` (admin downloads)
- The detail-row expand path

**Why it matters.** PDPA s23 requires recording who accessed
identified PII. Round-1 didn't catch this because the round-1 review
was scoped to data-model. Privacy-review-readiness fails.

**Suggested fix.** Add to **M3 or M9**:

- T-pdpa-access-log: every endpoint returning a non-zero `employee_id`
  on a response calls `_log_pdpa_access(actor_id=current_user.id,
subject_employee_id=row.employee_id, purpose="engagement_admin_read")`.
- Acceptance: regression test asserts a row in PdpaAccessLog after
  every such read.

### [H13] Manager-view leakage when a manager has 4 reports + their own response sits in the cohort

**What's missing.** X7 Q4 _answers_ this but the answer ("the
manager's own response should NOT count toward the n>=5 threshold")
is never realised as a task. There is no T-task in M9 (manager view)
that reads the manager's user_id, excludes their own response from
the count, and then reapplies the n>=5 gate.

**Why it matters.** Without the task, default behaviour is "count all
responses where reporting_manager_id == this_manager_id" which
_includes_ the manager themselves if they responded as part of the
cohort. A manager with 5 reports + their own response = n=6 visible;
exclude self = n=5 visible (still safe); exclude self for 4 reports +
self = n=4 (must suppress, but right now it shows n=5 i.e. leaky).

**Suggested fix.** Add to **M9 (manager view)**:

- T9X-self-exclusion: manager-view aggregator filters out
  `employee_id == current_manager_employee_id` (and the equivalent
  pseudonym) before computing `n`. Then re-evaluates `n >= 5`.
- Acceptance: test with manager + 4 reports = "Roll up to skip-level"
  banner. Manager + 5 reports + self = "n=5" view. Manager + 5
  reports without self response = "n=5" view.

### [H14] Demo-coherence: seed script is named in X6 but no T-task creates the engagement seed entries

**What's missing.** X6 lists 4 invariants the seed must produce:
3 RESIGNED in last 90 days, 2 cite growth, all 3 have low engagement
on growth questions, pseudonyms link engagement → employment events.
None of M0-M2 (read) own seed work; M10 (codify) is "capture
knowledge". The plan refers to `scripts/seed_demo_data.py --section
demo-refresh` (memory file `feedback_seed_script.md`) but no engagement
section is added.

**Why it matters.** Without seeded engagement data, the killer demo
flow is empty — the cross-stage panel says "no resigned employees in
window" or "no engagement responses available." This is a demo-day
catastrophe.

**Suggested fix.** Add to **M9 (cross-stage / manager view)** OR
create new **M-seed**:

- T-seed-engagement: extend `scripts/seed_demo_data.py` with two
  new sections: `engagement-templates` (seeds Q12 + pulse if not
  present) and `engagement-history` (creates 2 closed pulses +
  responses linked by pseudonym to the 3 RESIGNED employees, with
  Q4-growth Likert in 1-2 range for the 2 who cited growth).
- Acceptance: run `seed_demo_data.py --section demo-refresh` →
  cross-stage panel returns ≥2 correlated rows.

## M findings

### [M1] Acceptance criterion "DataFlow nodes register" (T10/T11/T12/T13/T14) is too vague

T10's acceptance "model imports cleanly; DataFlow nodes register;
empty-list query returns `[]` for a fresh company" doesn't specify
_which_ nodes (CRUD = 4 of them) and doesn't pin idempotency or
soft-delete semantics. A `pytest -k test_engagement_template_model`
checking only `from hr_advisory.models.company_user import
EngagementSurveyTemplate` passes a model with broken indexes.

**Fix:** Each model task should list: "EngagementXyzCreateNode",
"...UpdateNode", "...ReadNode", "...DeleteNode" all callable; index
migration produced; soft-delete update sets `is_archived=True` not
hard-delete. Test that a `delete` call leaves the row visible in raw
SQL but invisible to `list_records`.

### [M2] T16 "shipped library" seed has no consent_notice_version baked in

T16 seeds 4 templates but doesn't define what `consent_notice_version`
those launches default to. S1 says responses echo the parent
survey's notice version, but the template itself doesn't carry one.
The result: templates seeded today, when launched in 6 months, mint
an empty consent string.

**Fix:** Add `default_consent_notice_version: str` and
`default_consent_notice_text: str` to `EngagementSurveyTemplate`.
Library entries ship with a v1 PDPA notice. Launch uses
`survey.consent_notice_version = template.default_consent_notice_version`
unless overridden.

### [M3] T05 theme tagger has no prompt-injection sanitisation

T05 generalises `_theme_tags`. Free-text answers feed `derive_themes`.
Round-3+ codified prompt-injection sanitization (security-patterns
P-injection). Engagement free-text questions (longer, more frequent)
are a bigger surface than exit interviews.

**Fix:** Acceptance must say `derive_themes()` runs all free-text
through `sanitize_user_text()` before keyword match (and before any
LLM swap-in in P3). Test: payload with `</system> ignore previous`
produces `themes` not `["compromised"]`.

### [M4] T23 cohort preview leaks names cross-tenant if `validate_company_access` is forgotten

T23 returns `sample_names` (8 names). The endpoint requires
`hr_admin` role, but if the request body's `filter_spec` references
`manager_ids` that span companies (theoretically) or
`ad_hoc_employee_ids` from another tenant, the resolver could return
those employees' names. T22's tenant validation uses URL `{id}` —
preview takes inline filter_spec.

**Fix:** T23 acceptance must say "every employee_id resolved is
asserted `Employee.company_id == current_user.company_id`; reject
with 400 if any cross-tenant id present."

### [M5] T23 sample names is a privacy regression on small cohorts

`sample_names` returns 8 names. For a cohort of 4 (Management),
returning all 4 names + the warning "anonymity unsafe" tells the HR
admin exactly who the survey would target. Fine for HR. But: the
preview endpoint is `hr_admin` so it's fine for _now_. If a manager
view is added in M9 that uses the same preview endpoint with a
narrower scope, the sample list re-leaks identity. Document the
boundary.

**Fix:** Mark T23 as `hr_admin only — never expose to manager-view`,
and split the preview endpoint into `hr_admin` + `manager` variants
in M9 with the manager variant returning only the count.

### [M6] T22 PATCH whitelist doesn't include `description`

The plan says `name`, `description`, `filter_spec`, `is_archived`.
T22's text body matches. But it would be very easy to forget
`description` in code given the field naming. Acceptance test must
assert `PATCH {description: "new"}` succeeds and persists.

### [M7] No task ensures `closes_at` is in the future at launch

The launch endpoint takes `closes_at`. There's no validation that
`closes_at > launched_at`. A launch with `closes_at` in the past
auto-closes immediately on first cron tick, gives Grace a confusing
"closed" state, and emails go out for a survey that's already gone.

**Fix:** Add to **M3 (launch)** validation: `closes_at >
launched_at + 1 hour` (1h floor to prevent fat-finger). Reject with 400.

### [M8] No task addresses `closes_at` timezone — SGT vs UTC mismatch

User flows say "closes in 14 days" in Grace's view. Backend stores
UTC. If the wizard sends `2026-05-21T23:59:59` without timezone, the
backend may interpret as UTC and close 8 hours early in SGT. Round-7
P41 already codified SGT-conversion patterns.

**Fix:** Add **frontend M7 (launch wizard)** task: send `closes_at`
as ISO-8601 with explicit `+08:00` offset OR convert in the API
layer. Test: closes_at displayed as "21 May 23:59 SGT" matches DB
`2026-05-21T15:59:59Z`.

### [M9] Cohort filter `manager_ids` matches recursively or only direct?

T04 says `manager_ids: list[int]` — Filter by reporting_manager_id.
But the user flow (Step 7) talks about a manager seeing "direct +
indirect reports". For cohort targeting, is `manager_ids: [12]` ==
"reports of 12 only" or "reports of 12 and reports-of-reports"?
Ambiguous. If a CTO is in `manager_ids`, do all of engineering
get the survey or only their 3 direct reports?

**Fix:** Add T04 acceptance criterion: explicit semantic — direct
only by default; provide `manager_ids_recursive: list[int]` as a
separate key for the recursive case. Test both.

### [M10] T04 cohort resolver doesn't handle terminated employees that re-activate

T04 union-then-intersect with `is_active=True`. Edge case: an
employee terminated last month, reactivated yesterday, with
`tenure_min_days: 90` set. Their tenure is computed off
`Employee.start_date` (original hire) — they pass the filter even
though they've effectively been gone. Specification ambiguity, not
necessarily a bug, but it should be a documented decision.

**Fix:** Add T04 acceptance: "tenure is computed off latest
re-hire `start_date`, not original. Document and test."

### [M11] T17 termination sweep doesn't define behaviour for already-submitted responses

T17 says "find pending EngagementSurveyResponse rows for that
employee and set `is_void = True`." What about already-submitted
responses (submitted_at != None)? Are they:
(a) left as-is and counted in the aggregate (the response is real,
they answered while employed),
(b) voided too (employee no longer wants it counted),
(c) flagged but counted (audit trail)?

Plan implies (a) but T17's text reads as "all pending" only.
Ambiguity in critical path.

**Fix:** T17 explicit: "submitted responses are NOT voided.
Termination void only affects rows with `submitted_at IS NULL`. Add
test pinning the boundary."

### [M12] No frontend task ensures the public route is mobile-responsive

`03-user-flows/02-lily-completes-pulse.md` Step 1 says "on her phone".
The frontend phasing doc says `apps/web/src/components/surveys/`
shared components but no acceptance criterion mentions mobile
viewport (320px-414px) testing. The Likert5/EnpsScale tap targets
must be >=44pt; ChipMultiSelect must wrap; long_text auto-grows on
mobile keyboard.

**Fix:** Add to **M4 (public submission frontend)** acceptance: "tested
at 375x667 (iPhone SE) viewport in Playwright; all tap targets >=44pt;
no horizontal scroll; submit button reachable above keyboard."

### [M13] No accessibility task — screen-reader and keyboard-only

The public form must be keyboard-navigable and screen-reader-friendly.
PDPA + reasonable accessibility expectations. No todo addresses ARIA
labels on Likert5 (`role="radiogroup"`), EnpsScale (`role="radiogroup"
aria-label="Net promoter score 0 to 10"`), focus trapping in modals,
Skip-to-content links.

**Fix:** Add to **M4** task: "axe-core scan returns zero serious
violations on `/engagement-survey/[token]` and
`/my-engagement-surveys/[id]/respond`. Add to Playwright suite."

### [M14] No i18n consideration

The plan mentions Singapore SMEs (FWA/PDPA/CPF) but ships English
copy only. Even within the demo target (28 employees), Mandarin and
Bahasa Melayu speakers are realistic. The brief doesn't explicitly
demand i18n but the templates ship English-only.

**Fix:** Add to **M10 (codify)** OR explicit deferral: document "v1
ships English-only; template `sections` JSON shape supports
`text_translations: {en: "...", zh: "...", ms: "..."}` for v2." Even
if not implemented, reserve the schema field so v2 doesn't migrate.

### [M15] No PII-leakage check on error messages

If the public submit fails (e.g. JSON malformed), what does the API
return? "500 Internal Server Error" with stack? "400 Invalid payload"
with `payload[employee_id]` in the message? FastAPI's default
validation error includes input snippets. For pseudonymous responses,
even a `validation error: employee_id must be int, got 'lily@central.io'`
leaks the email.

**Fix:** Add to **X1 / M3-M5 acceptance**: "FastAPI validation errors
on public endpoints return generic `{detail: 'Invalid request'}`
without echoing input fields. Test with malformed payload — confirm
response excludes input values."

### [M16] No CORS configuration for the public route

`/engagement-survey/[token]` will be opened from email clients
(mailto), Slack previews, and corporate proxies. CORS preflight
behavior on `POST /public/{token}/submit` is undefined. If the
frontend at app.example.com submits to api.example.com, CORS rules
apply. Production deployment notes say "GCP at 136.110.51.61" — same
host probably, but document.

**Fix:** Add to **X1 checklist**: "CORS allowed origins explicit;
public endpoints document credentials: omit (tokens are url-bound,
no cookie). Test preflight returns 204 with correct headers."

### [M17] No rate limit on `GET /public/{token}/render`

The plan limits `submit` to 5/hr/token but `render` is unmetered.
An attacker who has any one valid token can hammer `/render` to
DOS the backend (returns sections JSON each time, larger payload
than validate). Same for `/validate` — listed in plan as the
preflight, no rate limit specified.

**Fix:** Add to **M3 (public endpoints)**: "30 req/min/token on
`/render`; 60 req/min/IP on `/validate`."

### [M18] CSV export sanitisation not pinned to a task

X1 checklist mentions `sanitizeCsvCell()` but no T-task creates the
export endpoint with the call wired in. CSV-injection (`=cmd|...`)
on a free-text answer like `=HYPERLINK("...")` lands in HR's
spreadsheet on download.

**Fix:** Add to **M9 (P2 exports)** task: "every cell in CSV passes
through `sanitizeCsvCell()` (per rules/security.md). Test: payload
`=cmd|/c calc.exe` exports as `'=cmd|/c calc.exe`."

### [M19] PDF export has no template / styling task

The plan says "CSV / PDF" export but no task lists what the PDF
contains, who renders it (server-side wkhtmltopdf vs client jsPDF),
or whether it sanitises the same way as CSV. Likely a follow-on
ticket but undefined.

**Fix:** Either drop PDF from v1 or add a concrete task: "server-side
PDF via existing wkhtmltopdf path; same anonymity-suppression rules
as the on-screen aggregate; embed company logo from existing brand
asset."

### [M20] T15 migration doesn't address rollback safety on a populated DB

T15 says "test on staging DB first; confirm migrations are reversible."
But DataFlow + Alembic on a populated DB may not actually drop tables
cleanly if responses already exist. Reversibility is asserted not
tested. M0/M1 are the foundation — if rollback breaks at M3, we're
stuck.

**Fix:** Add to T15: "rollback test: apply migration, insert 5 rows
across all 5 tables, run `alembic downgrade -1`, assert clean uninstall
with no orphaned indexes / FK constraints."

### [M21] Schedule cadence "anchored to launch date" (X7 Q5) has month-end edge case

X7 Q5 decides "anchored to launch date." A schedule launched on Jan
31 tries to fire Feb 31, which doesn't exist. Last-day-of-month
semantics undefined.

**Fix:** Add to **M9 (schedules)** acceptance: "if `next_launch_at`
target day exceeds month length, clamp to last day of month. Test:
schedule anchored to Jan 31 fires Feb 28 (or 29 on leap year), Mar 31,
Apr 30."

### [M22] Auto-close cron doesn't check `closes_at` reliably

There's an auto-close on `closes_at` (model says `auto-close after
this date`) but no T-task creates the close-cron. Schedule cron is
mentioned (M9) but a separate "close expired surveys" cron isn't
named. The plan says "Day 14, survey auto-closed" in the user flow.

**Fix:** Add to **M9 (schedules + cron)**: "T-close-cron: daily tick
at 02:30 SGT scans surveys with `closes_at < now AND closed_at IS NULL`,
sets `closed_at = now`, fires a close webhook (notifies HR via
notification feed). Idempotent (re-running is no-op)."

### [M23] No task pins frontend route for "already-submitted" empty state

The plan and user flow describe the `already_submitted` semantic state
but no frontend task lists the copy/icon/CTA. P1 has only `/launch`

- `/surveys/[id]` + `/my-engagement-surveys` + public route — the
  public route's empty states are inferred from the exit-survey
  template but the engagement-specific copy ("Thanks — your pulse
  response was received on May 8 at 9:14 SGT") isn't authored.

**Fix:** Add to **M4 (public submission frontend)** acceptance: "five
empty states authored with copy, screenshot-tested: invalid_or_expired,
not_found, already_submitted, closed, voided (the new state from C1)."

## L findings

### [L1] T01 token grace period: no observability metric

X4 doesn't mention a counter for `legacy_token_kind_assumed_total`.
Operations-blind on whether legacy tokens are still in use.

**Fix:** Add to **X4**: counter incremented every time the legacy
fallback fires; alert if non-zero on day 31.

### [L2] T02 `<ScoreBar>` listed as new but flagged as "round-5/6 reusable"

Inconsistency in the file: T02 says "shared, ... round-5/6 reusable".
If it already exists, the task should say "move existing".

**Fix:** Clarify whether T02 creates or relocates; if relocates, list
the source path.

### [L3] T16 library seeds run on every empty GET — race risk

If two HR admins open `/engagement` for the first time within the
same second, both fire `GET /templates`, both see empty, both seed.
Idempotent (T16 says "skip if any exists"), but the second insert
window opens before the first commits.

**Fix:** Wrap seed in advisory lock per company; idempotency-friendly
upsert. Pattern P-per-tenant-locks.

### [L4] T22 cohort PATCH that changes `filter_spec` after cohort is referenced by an open survey

The survey snapshots `cohort_filter_spec` at launch (good — round-1
C3 pattern). But editing the cohort while a survey is open changes
nothing for the survey but may surprise admins. Consider a yellow
banner: "This cohort has 1 active survey; edits won't affect it."

**Fix:** Add T22 acceptance: "PATCH a cohort with active surveys
returns 200 + warning body field; UI surfaces it."

### [L5] T23 anonymity threshold magic number `min_cohort_size = 5`

T23 names it correctly as a constant, but no task lifts it to a
company-level setting. Some Singapore SMEs might want stricter
(n>=10). Foundation-independence aside, leaving it hardcoded is fine
for v1 but documentation should mention the lift-point.

**Fix:** Comment in T23: "v1 hardcoded `MIN_COHORT_SIZE = 5`; v2 may
lift to `Company.min_cohort_size` setting."

### [L6] T17 termination flow: race with submit-in-progress

If Lily clicks Submit at 10:00:01 and HR terminates her at 10:00:02,
the sweep marks her response `is_void=True` but her submit is
mid-flight and writes `submitted_at`. Final state: voided + submitted.
Aggregator excludes voided → her response disappears.

**Fix:** Add note: "if submit lands within 5 minutes of termination,
flag for HR review rather than auto-voiding silently. Audit-log the
race."

### [L7] No accessibility audit on aggregate page color-only encoding

Aggregate distribution bars use red (Eng 3.2) / green (Sales 4.4) per
plan. Color-blindness compliance: add icons or text labels. Round-7
P40+ patterns may already cover this — verify.

**Fix:** Add to **M8 (aggregate frontend)**: "all color-coded
distribution bars also expose textual label (e.g. 'low'/'high') for
screen-reader and color-blind users."

### [L8] X3 performance budget for cohort preview is 500ms p95 — but no test

The budget is documented in the X file but no T-task adds a perf
gate. CI doesn't fail on regressions.

**Fix:** Add to **M2 or M6**: smoke perf test asserting cohort
preview returns in <500ms with seeded 100-employee company.

### [L9] No task lists the OpenAPI tag/group for swagger UX

T20 says `engagement` tag — fine. But the existing swagger UI groups
exit-interviews + appraisals + engagement under "HR" probably. No
task pins how the engagement endpoints appear. Minor UX for the API
client builder team.

**Fix:** Document in T20: "swagger group `engagement-surveys` with
description sentence; appears alphabetically after `exit-interviews`."

### [L10] T03 lazy-generation of pseudonym secret — no concurrent first-use guard

If two pulses launch in the same minute on a fresh company, both try
to generate the secret. Pattern P-per-tenant-locks.

**Fix:** Note in T03: "lazy-generation guarded by per-company lock OR
check-then-set with retry on integrity-error. Test concurrent first
launch."

### [L11] X8 `/appraisals` AdminGuard issue — verify, don't just assert

X8 says "Engagement has the same shape — make sure `/engagement`
AdminGuard does NOT prevent the employee `/my-engagement-surveys`
flow. They live in different routes, so this is structural; verify."
"Verify" is not a task.

**Fix:** Add explicit T-task in **M5 (employee self-service)**:
"Playwright smoke as Lily (employee role) — confirm `/engagement`
returns 403 (or sidebar hidden) AND `/my-engagement-surveys` returns 200. Pin the boundary."

## Cross-reference audit (what each finding implicates)

- **M0** (T01-T06): impacted by H8, L1, L2, L10
- **M1** (T10-T17): impacted by H2, H10, H11, M1, M2, M10, M11, M20
- **M2** (T20-T24): impacted by M3, M4, M5, M6, L3, L4, L5
- **M3 (inferred)**: impacted by H3, H4, H5, H6, H7, H9, M7, M8, M15, M16, M17
- **M4 (inferred)**: impacted by H4, M12, M13, M23
- **M5 (inferred)**: impacted by H7, H9, L11
- **M6 (inferred)**: impacted by H10
- **M8 (inferred)**: impacted by L7
- **M9 (inferred)**: impacted by H1, H13, H14, M5, M18, M19, M21, M22
- **M10 (codify)**: impacted by H8, M14
- **X-cross-cutting**: impacted by H8, M14, M15, M16, L1, L8

## Decision points (questions for stakeholder)

1. **H1 endpoint shape:** confirm the cross-stage correlation endpoint
   path and payload. The data model supports it, but no contract is
   yet pinned.
2. **H2 vs cohort denormalisation:** acceptable to snapshot
   department/manager onto each response at submit (vs joining live
   Employee table)? This is the only way to make `by_cohort`
   aggregation work for non-identified surveys.
3. **H4 atomic counter vs derived count:** denormalised
   `response_count` with atomic SQL increment, or kill the column and
   compute on read? The latter is simpler, the former is faster on
   surveys with hundreds of responses.
4. **H6 saga shape:** survey saga is "create response rows" + "enqueue
   emails" — should email failure roll back response rows, or surface
   a partial-delivery state for HR to retry? Lily-flow Step 4 implies
   the partial-delivery state.
5. **H11 rotation cadence:** when do we rotate `engagement_secret`?
   Annual? On staffing change? On incident only?
6. **M14 i18n scope for v1:** strict English-only is fine, but should
   we reserve `text_translations` JSON shape now or migrate later?
7. **M19 PDF export:** ship in v1 or defer to v2 (CSV-only at v1)?

## Status

H findings are ship-blockers in the literal sense — every one of
them either (a) breaks the killer demo flow, (b) leaks identity, or
(c) loses data. They should fold into the next todo revision before
`/implement` starts.

M findings cause rework if discovered post-implementation but don't
block ship if caught during M3/M4/M9 review.

L findings are nice-to-haves but should be tracked as follow-ups.

The plan as it stands is solid on data model and admin authoring
(M0-M2). It's thinnest on:

- Concurrency safety (H3, H4, H5, L3, L6, L10) — five findings
- The cross-stage demo flow (H1, H14) — two findings, one is the
  USP.
- Accessibility / mobile / i18n (M12-M14) — privacy-review-readiness
  exposure.

Recommendation: address all H before `/implement`; address H+M+L for
M9 specifically before the demo dress-rehearsal.
