# M3 — Backend API: launch + responses + trend + manager + actions

**Source plan:** `02-plans/02-api-and-routes.md` §Surveys + §Employee
endpoints, plus `02-plans/04-product-revision-round3.md` (round-3
product revision).

The hot path. Round 3 dropped the public tokenised endpoints (engagement
is in-app only) and pulled manager-view, trend, and the action loop
into P1.

## T30 — `POST /surveys/launch`

- **What:** Resolve the cohort, snapshot the template, create one
  `EngagementSurveyResponse` per employee, fan out **in-app
  notifications**, return `{survey_id, target_count}`.
- **Body:**
  ```json
  {
    "template_id": 7,
    "cohort_id": 3,
    "cohort_filter_spec": null, // OR inline filter (presets/ad-hoc only at P1)
    "name": "H1 2026 Pulse — All Staff",
    "anonymity_tier": "pseudonymous",
    "closes_at": "2026-05-21T23:59:59+08:00",
    "consent_notice_text": "",
    "force_overlap_acknowledged": false,
    "force_anonymity_acknowledged": false
  }
  ```
- **Steps (with Z amendments folded in):**
  1. Validate auth, tenant, role.
  2. Acquire per-`company_id` advisory lock (Z06). Inside lock:
  3. Resolve cohort (T04). Reject if 0 matched.
  4. Anonymity safety (Z07 still applies): if `tier in {pseudonymous, anonymous}` AND `len(employee_ids) < 5`, 400 unless `force_anonymity_acknowledged`.
  5. Overlap check (T24). 409 with `{warnings, can_proceed}` unless `force_overlap_acknowledged`.
  6. Validate `closes_at > launched_at + 1h` AND `closes_at < launched_at + 90d` (Z12).
  7. Snapshot `template.sections` → `survey.template_sections_snapshot` (C3).
  8. Compute `consent_notice_version`.
  9. Saga stage A — create `EngagementSurvey` row. Transaction.
  10. Saga stage B — bulk-create `EngagementSurveyResponse` rows. Transaction.
  11. Saga stage C — fan out **`Notification` rows** (Z10), one per response, `kind="engagement_pending"`, `link="/my-engagement-surveys/{response_id}"`. Post-commit hook.
  12. **No email queue rows** for engagement at P1 (in-app only). Email queue still exists for exit interviews.
  13. Release lock.
  14. Return `{survey_id, target_count}`.
- **Anonymity tier handling:**
  - `identified`: store `employee_id`; no pseudonym computed yet (submit-time, not launch-time).
  - `pseudonymous`: store `employee_id` pre-submit (so we can route the in-app form to the right user); on submit, zero `employee_id` and set `employee_pseudonym`.
  - `anonymous`: store `employee_id` pre-submit; on submit, zero `employee_id` and DO NOT store pseudonym.
- **Rate limit:** 10/hour/company.
- **Acceptance:** launch with all_active cohort creates N responses + N notification rows + 0 email-queue rows; subsequent GET shows the survey in admin list.
- **Tests:** `tests/regression/test_engagement_launch.py` covers cohort 0-match (400), anonymity-unsafe (400 unless forced), overlap (409 unless forced), closes_at out of range (400), parallel launch (Z06: two threads → one survey).

## T31 — Employee in-app endpoints

- **GET `/my-pending`** — list responses for current user where `submitted_at IS NULL` AND parent `closes_at > now()` AND `is_void = False`. Returns name, brief, est duration, closes_at, response_id.
- **GET `/my-history`** — submitted responses, ONLY for surveys with `anonymity_tier == "identified"`. Pseudonymous and anonymous responses are intentionally absent (the user has no re-identifiable trail).
- **GET `/my-responses/{response_id}/render`** — return `template_sections_snapshot` (C3) for the form. Auth via Bearer. Confirms `current_user.id == response.employee_id` (only valid pre-submit, since post-submit the row may have employee_id=0).
- **POST `/my-responses/{response_id}/submit`** — store the response.
  - Idempotency-Key header (Z08), default `sha256(response_id + canonical_payload)`. Replay returns prior response.
  - CSRF (Z11): require `Origin` matches app origin OR CSRF header. Reject 403 cross-origin.
  - Validate payload against snapshot's question schema.
  - Compute `likert_scores`, `themes` (T05, sanitised per Z34), `enps_score`.
  - Populate `response_cohort_attributes` (Z03) BEFORE identity stripping — `{department, pass_type, tenure_band, manager_id_hashed}`.
  - **Anonymity branch:**
    - identified: keep employee_id.
    - pseudonymous: compute pseudonym (T03), set `employee_pseudonym = pseudonym`, zero `employee_id`.
    - anonymous: zero `employee_id`, no pseudonym.
  - Set `submitted_at`, `consent_notice_version`.
  - **Voided check (H10/Z21):** if `is_void=True`, reject 410 voided.
  - Mark related `Notification` row(s) as resolved (so the dashboard card disappears).
  - Return `{ok: true, themes, idempotent_replay: false}`.
- **Submit rate limit:** 1 successful per response (enforced by `submitted_at IS NULL` check), 5 failed-validation per hour per response.
- **PII-clean errors (Z13):** validation errors return generic `{detail: "Invalid request", correlation_id}` with full payload logged server-side.
- **Acceptance:** Lily sees one open pulse on `/my-pending`; submits via in-app; cannot submit twice (idempotent replay); cannot submit for another employee; voided row → 410; cross-origin → 403.
- **Tests:** `tests/regression/test_engagement_my.py` covers the 12-cell voided × tier matrix (Z21 rolled in).

## T32 — Admin response list + close

- **GET `/surveys`** — list launched surveys for the company.
- **GET `/surveys/{id}`** — one survey + summary stats (uses derive-on-read for response count per Z07).
- **GET `/surveys/{id}/responses`** — list responses with anonymity enforcement:
  - identified: name + email visible.
  - pseudonymous: pseudonym shown as "Respondent #abc1234" (first 8 chars of pseudonym hex).
  - anonymous: shown as "Anonymous".
  - **PDPA log (Z16):** `_log_pdpa_access()` for every identified employee_id returned.
- **POST `/surveys/{id}/close`** — sets `closed_at = now()`. Subsequent submissions return 409 closed.
- **Acceptance:** anonymity tiers visibly enforced; close blocks submissions; PDPA log row written.

## T33 — `GET /surveys/{id}/aggregate` with anonymity gate

- Same as the previous T34 spec.
- **Anonymity gates (Z03 + M1 from round-1 redteam):**
  - Per-question and per-cohort: only return distribution if `n >= 5`. Mark suppressed cells as `{is_anonymity_safe: false, n}`.
  - **By-cohort uses `response_cohort_attributes`** (Z03), not a live `Employee` join. Anonymous and pseudonymous tiers join via this snapshot.
- **eNPS computation:** standard (promoters − detractors). Skip if no eNPS question.
- **Theme tally:** aggregate themes; sorted desc.
- **Excludes voided** (C1).
- **Cache:** none. P95 <1s for 500 responses.
- **Acceptance:** aggregator returns Likert distribution + theme tally + eNPS; suppression honoured.
- **Tests:** `tests/regression/test_engagement_aggregate.py`.

## T34 — `GET /surveys/trend` — NEW (round-3, backs the hero chart)

- **Endpoint:** `GET /engagement-surveys/surveys/trend?cohort=engineering&window=6_pulses`
- **What:** returns the last N closed pulses' average score for the
  given cohort, plus the eNPS for each.
- **Body:**
  ```json
  {
    "cohort_label": "Engineering",
    "window": 6,
    "points": [
      {
        "survey_id": 7,
        "closed_at": "2026-04-12",
        "avg_likert": 3.8,
        "enps": 12,
        "n": 8,
        "is_anonymity_safe": true
      },
      {
        "survey_id": 11,
        "closed_at": "2026-05-12",
        "avg_likert": 3.2,
        "enps": -3,
        "n": 8,
        "is_anonymity_safe": true
      }
    ]
  }
  ```
- **Cohort param:** `all` (default), `department:Engineering`, `pass_type:LongTerm`, `tenure_band:0-1y`, `manager:42`.
- **Anonymity gate:** points where `n < 5` return with the value but `is_anonymity_safe=false`; HR can hide or show. Pseudonymous and anonymous tiers use `response_cohort_attributes` (Z03) for the cohort filter.
- **Auth:** `require_role("owner", "hr_manager")`.
- **Acceptance:** with seeded data showing 6 prior pulses for Engineering trending 3.8 → 3.5 → 3.2, the hero chart renders the descending line.
- **Tests:** `tests/regression/test_engagement_trend.py`.

## T35 — `GET /team/aggregate` — NEW (manager view, pulled from P3)

- **Endpoint:** `GET /engagement-surveys/team/aggregate?survey_id=11`
- **Auth:** any authenticated user with at least one direct report (resolved via `Employee.reporting_manager_id`).
- **Scope resolution:**
  1. `manager_employee_id = Employee.from_user(current_user).id`.
  2. Resolve direct + indirect reports recursively (configurable per-company at P2; P1 default = direct + skip-skip).
  3. **Self-exclude (Z26):** filter out the manager's own response from the cohort.
- **Anonymity gate:** `n >= 5` enforced. If `n < 5`, return:
  ```json
  {
    "scope_size": 4,
    "is_visible": false,
    "message": "Your team is too small to see aggregated engagement data without risk of identifying individual responses. Roll up to your skip-level manager for visibility."
  }
  ```
- **When visible:** same shape as `T33 aggregate` but scoped to the manager's team. Returns top themes + Likert distribution + eNPS.
- **PDPA log:** for identified surveys, log the manager's read.
- **Acceptance:** Tanaka (manager of 6) sees aggregate; manager-of-3 sees suppression notice; manager + 5 reports + own response = n=5 visible (self excluded).
- **Tests:** `tests/regression/test_engagement_manager_view.py` covers self-exclusion 3-row matrix from Z26.

## T36 — `GET /surveys/{id}/suggested-actions` — NEW (action loop)

- **What:** Returns 3 AI-suggested actions for the lowest-scoring
  cohort in the survey. Light Kaizen call.
- **Logic:**
  1. Read aggregate (T33). Identify lowest-scoring cohort with `n >= 5`.
  2. Read top theme for that cohort.
  3. Build a Kaizen prompt: "A Singapore SME's {cohort} team scored {score}/5 on engagement, with the top theme being {theme}. Suggest 3 specific, time-bound actions an HR manager could take in the next 30 days."
  4. Sanitise the LLM output through `sanitize_user_text` (Z34).
  5. Cap response at 3 items; truncate at 200 chars each.
- **Cost cap (Z31):** per-survey budget cap, falls back to deterministic 3-suggestion-per-theme template if LLM unavailable or capped.
- **Deterministic fallback templates** (used if LLM fails — D8 from round-3; reviewed by `sg-employment-law-expert` on 2026-05-07, 4 wording tweaks applied for TAFEP / FWA compliance):
  - **growth:** ["Run a skip-level on growth aspirations", "Audit promo cycle clarity", "Launch L&D pilot with a per-head learning budget for the cohort"]
  - **manager:** ["Run 1:1 effectiveness training for managers", "Audit workload balance across team", "Introduce skip-level rotation"]
  - **comp:** ["Benchmark salary against market for affected band", "Audit promo-comp alignment", "Communicate comp philosophy openly"]
  - **workload:** ["Audit on-call rotation and review any flexible-work requests in scope", "Pilot a no-meetings Wednesday", "Run capacity planning workshop with the team"]
  - **culture:** ["Run a team norms and ways-of-working workshop", "Audit recognition cadence", "Introduce peer-recognition channel"]
  - **role:** ["Audit role clarity matrix", "Run a skill-mapping exercise to inform development plans", "Pair employees with mentors outside their reporting line"]
- **Why these specific phrasings** (legal-neutrality rationale):
  - "per-head learning budget for the cohort" avoids the IC/manager differential (TAFEP fair-treatment).
  - "review any flexible-work requests in scope" bakes in the Dec 2024 FWA "reasonably consider" duty.
  - "team norms and ways-of-working" replaces "values workshop" — TAFEP treats values/culture-fit framing as a proxy for age/nationality/religion bias.
  - "to inform development plans" anchors skill-mapping to L&D, not performance assessment, reducing wrongful-dismissal evidentiary risk.
- **Cache:** 24h per survey (suggestions don't change until new responses arrive).
- **Auth:** `require_role("owner", "hr_manager")`.
- **Acceptance:** call returns 3 suggestions in <2s; deterministic
  fallback exercised when LLM disabled.
- **Tests:** `tests/regression/test_engagement_suggested_actions.py`.

## T37 — Action endpoints — NEW (action loop)

- **POST `/surveys/{id}/actions`** — create / accept an action.
  - Body: `{cohort_label, finding_summary, suggested_action_text, status: "accepted", create_linked_goal: bool}`.
  - If `create_linked_goal=true`, call existing Goals module to create a goal owned by `current_user`. Link `linked_goal_id`.
  - Returns the new action row.
- **PATCH `/actions/{id}`** — update an action.
  - Whitelist (P39): `status`, `suggested_action_text`, `linked_goal_id`, `next_pulse_question`, `next_pulse_survey_id`.
- **GET `/actions?survey_id=N`** — list actions for the company, optionally filtered by survey.
- **Auth:** `require_role("owner", "hr_manager")`.
- **Auto-anchoring (D9 from round-3):** when an action is `status=accepted`, if `next_pulse_question` is set, the NEXT launch of the same template will append (or replace) the relevant question with this anchored text. The launch flow checks for accepted actions for that template and folds them in.
- **Resolved score delta:** post-cron, when the next pulse closes, compute the delta (new cohort score − old cohort score) and write to `resolved_score_delta`.
- **Acceptance:** HR creates an action, optionally creates a goal, and after the next pulse closes the delta is computed.
- **Tests:** `tests/regression/test_engagement_actions.py`.

## T38 — `GET /my-loop-closing` — NEW (employee view)

- **What:** Return the loop-closing card payload for the current user's
  company, used on `/my-engagement-surveys`.
- **Body:**
  ```json
  {
    "last_pulse_closed_at": "2026-04-12",
    "top_theme": "growth",
    "action_taken": {
      "headline": "Learning budget pilot launched May 1",
      "linked_goal_label": "Q2: Engineering L&D — every IC has approved budget by end of Q2"
    },
    "next_pulse_anchored_question": "How clear is your career path here?"
  }
  ```
  OR `null` if no pulses have been closed yet.
- **Logic:**
  1. Find latest closed survey for the company.
  2. Compute top theme across responses.
  3. Find any `EngagementAction` with `status="accepted"` AND `cohort_label` matching this user's cohort (or company-wide) for that theme.
  4. Read the linked Goal label if present.
  5. If no accepted action: `action_taken=null`, card shows "HR has seen this — actions in progress."
- **Auth:** any authenticated user.
- **Anonymity:** the payload reveals only the company-wide top theme, never per-employee data. Safe for any user.
- **Acceptance:** Lily lands on `/my-engagement-surveys`, sees the
  card with the seed's "growth" theme + the seeded action.
- **Tests:** `tests/regression/test_engagement_loop_closing.py`.

## Removed in round 3

- ~~Public tokenised endpoints~~ (`/public/{token}/validate`, `/render`, `/submit`). Engagement is in-app only.
- Token render path is now `GET /my-responses/{id}/render` (auth via Bearer).
- Email-queue fan-out for engagement is removed at P1 (the email queue itself stays for exit interviews, and reminder send via email returns at P2 T86).

## Dependencies

- T30 needs T04 (resolver), T05 (theme tagger), T24 (overlap helper), Z06 (lock), Z10 (notification fanout).
- T31 needs T03 (pseudonym), Z03 (cohort attrs), Z08 (idempotency), Z11 (CSRF), Z21 (voided test matrix).
- T33 needs T17 (voided sweep), Z03 (response_cohort_attributes).
- T34 needs T33 + 6 prior pulses in seed (M6 T60 update).
- T35 needs `Employee.reporting_manager_id` recursion + Z26 (self-exclusion).
- T36 needs Kaizen integration + cost cap (Z31) + Z34 sanitisation.
- T37 needs Goals module integration.
- T38 needs T37.

## Acceptance gate for M3

- HR can launch a survey end-to-end via API.
- In-app submit works for all three anonymity tiers.
- Aggregator returns correct gated output.
- **Trend endpoint returns 6-pulse history.**
- **Manager view enforces n≥5 with self-exclusion.**
- **Suggested-actions endpoint returns 3 items (LLM or fallback).**
- **Action endpoints support create + linked-goal + anchor.**
- **Loop-closing endpoint returns valid payload.**
- Pinned by 8 new regression test files.
