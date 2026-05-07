# API endpoints + route map

New router: `src/hr_advisory/api/routers/engagement_surveys.py`.
Registered in the platform's main FastAPI app with prefix
`/engagement-surveys`.

All admin endpoints go through `require_role("owner", "hr_manager")`.
Employee endpoints use `get_current_user`. Public submission endpoints
are tokenised (no auth header required, token IS the auth).

## Templates

| Method | Path                                 | Purpose                                     | Auth     |
| ------ | ------------------------------------ | ------------------------------------------- | -------- |
| GET    | `/engagement-surveys/templates`      | List templates (incl. shipped library)      | hr_admin |
| GET    | `/engagement-surveys/templates/{id}` | Read one template with sections JSON        | hr_admin |
| POST   | `/engagement-surveys/templates`      | Create new (or clone shipped library entry) | hr_admin |
| PATCH  | `/engagement-surveys/templates/{id}` | Update name/sections; bumps `updated_at`    | hr_admin |
| DELETE | `/engagement-surveys/templates/{id}` | Soft-delete (sets `is_archived`)            | hr_admin |

**On first GET:** if the company has no templates, seed the four
shipped library entries (Q12 paraphrase, Trust Index pillars, monthly
pulse, Singapore SME quarterly) into the company's template list.

## Cohorts

| Method | Path                                  | Purpose                                                                        | Auth     |
| ------ | ------------------------------------- | ------------------------------------------------------------------------------ | -------- |
| GET    | `/engagement-surveys/cohorts`         | List cohorts                                                                   | hr_admin |
| POST   | `/engagement-surveys/cohorts`         | Create cohort with filter spec                                                 | hr_admin |
| PATCH  | `/engagement-surveys/cohorts/{id}`    | Update                                                                         | hr_admin |
| DELETE | `/engagement-surveys/cohorts/{id}`    | Soft-delete                                                                    | hr_admin |
| POST   | `/engagement-surveys/cohorts/preview` | **Resolve filter to employee count + sample names; check anonymity threshold** | hr_admin |

The preview endpoint returns:

```json
{
  "matched_count": 22,
  "sample_names": ["Lily Phang", "Chen Wei", "Tanaka Hiroshi", "..."],
  "anonymity_safe": true,
  "warnings": []
}
```

If `matched_count < 5`, `anonymity_safe = false` and warnings include
"Cohort is too small for anonymous reporting; aggregated views may
be re-identifiable. Use identified mode or merge with another cohort."

## Surveys (instances)

| Method | Path                                         | Purpose                                                       | Auth     |
| ------ | -------------------------------------------- | ------------------------------------------------------------- | -------- |
| GET    | `/engagement-surveys/surveys`                | List launched surveys (with response counts)                  | hr_admin |
| GET    | `/engagement-surveys/surveys/{id}`           | Read one with full response stats                             | hr_admin |
| POST   | `/engagement-surveys/surveys/launch`         | Launch (resolves cohort, creates response rows, sends emails) | hr_admin |
| POST   | `/engagement-surveys/surveys/{id}/close`     | Manually close (rejects further submissions)                  | hr_admin |
| POST   | `/engagement-surveys/surveys/{id}/remind`    | Re-send reminder to non-responders                            | hr_admin |
| GET    | `/engagement-surveys/surveys/{id}/responses` | List responses (anonymized if `is_anonymous`)                 | hr_admin |
| GET    | `/engagement-surveys/surveys/{id}/aggregate` | Aggregated Likert distribution + theme tally + eNPS           | hr_admin |
| GET    | `/engagement-surveys/surveys/{id}/export`    | CSV / PDF                                                     | hr_admin |

**Launch payload:**

```json
{
  "template_id": 7,
  "cohort_id": 3, // OR cohort_filter_spec inline
  "cohort_filter_spec": null,
  "name": "H1 2026 Pulse — All Staff",
  "is_anonymous": true,
  "closes_at": "2026-05-21T23:59:59"
}
```

Launch endpoint:

1. Resolves cohort filter to a list of employee_ids.
2. Creates one `EngagementSurveyResponse` per employee, status pending.
3. Sends a tokenised link to each employee's email (reuse the
   exit-interview email pattern).
4. Returns `{survey_id, target_count}`.

## Schedules

| Method | Path                                        | Purpose                | Auth     |
| ------ | ------------------------------------------- | ---------------------- | -------- |
| GET    | `/engagement-surveys/schedules`             | List schedules         | hr_admin |
| POST   | `/engagement-surveys/schedules`             | Create schedule        | hr_admin |
| PATCH  | `/engagement-surveys/schedules/{id}`        | Update cadence/cohort  | hr_admin |
| POST   | `/engagement-surveys/schedules/{id}/pause`  | Pause without deleting | hr_admin |
| POST   | `/engagement-surveys/schedules/{id}/resume` | Resume                 | hr_admin |
| DELETE | `/engagement-surveys/schedules/{id}`        | Archive                | hr_admin |

A new cron entry `engagement_pulse_tick.sh` runs daily at 02:00 SGT,
reads active schedules where `next_launch_at <= now()`, calls the
launch endpoint internally, and bumps `next_launch_at` per cadence.

Reuse the cron-via-docker-exec pattern (security-patterns P16).

## Employee endpoints

| Method | Path                                           | Purpose                                              | Auth     |
| ------ | ---------------------------------------------- | ---------------------------------------------------- | -------- |
| GET    | `/engagement-surveys/my-pending`               | List my open surveys (status=pending, closes_at>now) | employee |
| GET    | `/engagement-surveys/my-history`               | Past submissions (for non-anonymous surveys)         | employee |
| POST   | `/engagement-surveys/my-responses/{id}/submit` | Submit my response (in-app, requires auth)           | employee |

## Public tokenised endpoints

| Method | Path                                          | Purpose                                           | Auth |
| ------ | --------------------------------------------- | ------------------------------------------------- | ---- |
| GET    | `/engagement-surveys/public/{token}/validate` | Preflight (mirror exit-interview semantic states) | none |
| GET    | `/engagement-surveys/public/{token}/render`   | Return template sections + survey metadata        | none |
| POST   | `/engagement-surveys/public/{token}/submit`   | Submit response payload                           | none |

The `validate` endpoint follows P36 — return semantic reasons:
`{ok: true|false, reason: "invalid_or_expired" | "not_found" | "already_submitted" | "closed", is_anonymous: bool, triggered_at: ISO}`.

## Aggregation endpoint shape

`GET /engagement-surveys/surveys/{id}/aggregate` returns:

```json
{
  "survey_id": 5,
  "name": "H1 2026 Pulse",
  "response_count": 22,
  "target_count": 28,
  "response_rate": 0.79,
  "is_anonymous": true,
  "by_question": {
    "q1": {
      "type": "likert5",
      "text": "I know what is expected of me at work.",
      "distribution": { "1": 0, "2": 1, "3": 4, "4": 11, "5": 6 },
      "average": 4.0,
      "n": 22
    },
    "q2": {
      /* ... */
    },
    "q4_what_to_change": {
      "type": "long_text",
      "text": "...",
      "themes": [
        { "theme": "manager", "count": 5 },
        { "theme": "workload", "count": 3 },
        { "theme": "growth", "count": 8 }
      ],
      "n_with_response": 14
    }
  },
  "enps": {
    "promoters": 8,
    "passives": 10,
    "detractors": 4,
    "score": 18.2,
    "n": 22
  },
  "by_cohort": [
    {
      "department": "Engineering",
      "n": 8,
      "average_likert": 3.6,
      "is_anonymity_safe": true // n >= 5
    },
    {
      "department": "Management",
      "n": 2,
      "average_likert": null,
      "is_anonymity_safe": false // n < 5; suppressed
    }
  ]
}
```

## Lifecycle dashboard hook

`/strategy/lifecycle` aggregator gains a new derivation:

- For Reward stage: `engagement_score = avg(latest pulse Likert).
- For Retain stage: cross-check engagement score < 3.0 against
  EmploymentEvent RESIGNED in the next 90 days → "leading-indicator
  hit-rate" panel.

Lifecycle activity feed gains entries:

```json
{
  "stage": "reward",
  "kind": "ENGAGEMENT",
  "ts": "...",
  "summary": "Engagement pulse submitted: Lily Phang",
  "entity_type": "engagement_survey",
  "entity_id": 3
}
```

P46 click-through pattern carries through unchanged.

## Backwards-compat / namespace concerns

- Route prefix `/engagement-surveys/` chosen to avoid colliding with
  the existing `/exit-interviews/` (parallel sibling).
- The existing `_make_token` / `_decode_token` are duplicated into
  the engagement router unless we refactor them into a shared
  `surveys/_token.py` first. Recommend extracting on the v1 commit
  to keep both modules consistent.

## Rate limits

- `POST /engagement-surveys/surveys/launch` — 10 / hour / company
  (same shape as `appraisals.launch_period`).
- `POST /engagement-surveys/public/{token}/submit` — 10 / hour / token
  (per-token, same shape as exit-interview submit).
- `GET /engagement-surveys/cohorts/preview` — 30 / minute (interactive
  endpoint).
