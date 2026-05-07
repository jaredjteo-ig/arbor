# M0 — Foundations (shared primitives)

**Source plan:** `02-plans/01-data-model.md`, `02-plans/02-api-and-routes.md`.

Reusable primitives that other milestones depend on. Build once, share
between exit-interviews and engagement-surveys (and future survey-shaped
modules).

## T01 — Extract token helpers into shared module

- **What:** Move `_make_token` / `_decode_token` from
  `src/hr_advisory/api/routers/exit_interviews.py` into a new shared
  module `src/hr_advisory/api/routers/_survey_tokens.py`. Used by
  exit-interviews now; reserved for future engagement use (e.g.
  alumni-cycle eNPS one year after departure).
- **Why:** P36 codified the public-link preflight pattern; the
  encode/decode primitives belong in one place.
- **Round-3 scope note:** **Engagement v1 is in-app only.** No
  engagement-kind tokens are minted. The `kind` claim still ships
  to enable future use and to harden exit-interview tokens against
  cross-feature replay.
- **Token namespace:** add a `kind` claim — `kind: "exit"` is the
  only minted value at v1. `kind: "engagement"` is reserved.
- **Backwards compatibility:** existing exit-interview tokens already
  in the wild have no `kind`. Treat missing `kind` as `"exit"` (the
  legacy default) for a 30-day grace; after that, reject.
- **Acceptance:** existing exit-interview Playwright walk still works;
  cross-replay (exit token at any engagement endpoint, when those
  ship in alumni-cycle v2+) would return `invalid_or_expired`.
- **Tests:** `tests/regression/test_survey_tokens.py` — new file.

## T02 — Shared survey React components

- **What:** Create `apps/web/src/components/surveys/` with five
  components used by both exit-survey public page, engagement-survey
  public page, and (later) appraisal renderer:
  - `<Likert5 value onChange label />`
  - `<EnpsScale value onChange />` (0-10)
  - `<ChipMultiSelect options selected onToggle />`
  - `<ResponseDetail payload sections />` (round-5 P45 expand-row)
  - `<ScoreBar score />` (round-5/6 reusable)
- **Why:** Three pages already render Likert + chips + free-text. Code
  duplication is a maintenance trap; centralise.
- **Refactor scope:** update existing `/exit-survey/[token]/page.tsx`
  to consume the shared components. Don't change behaviour.
- **Acceptance:** exit-survey live walk still green; visual diff zero.

## T03 — Per-company HMAC secret for pseudonymous mode (C2)

- **What:** Add `Company.engagement_secret: str` (encrypted at rest
  via the existing `encrypt_field` helper) generated on first use.
  Used to compute `employee_pseudonym = HMAC(secret, f"{employee_id}|{survey_id}")`.
- **Why:** C2 from the red-team — pseudonymous mode lets HR see
  cross-survey trends per employee without storing employee_id on
  the response. The HMAC secret lives in `Company`, never travels in
  any API response.
- **Migration:** lazy-generate on first launch of a pseudonymous
  survey; nothing to backfill.
- **Helper:** `src/hr_advisory/services/engagement_pseudonym.py`
  exposing `compute_pseudonym(company_id, employee_id, survey_id)`.
- **Acceptance:** same employee + same survey returns identical
  pseudonym; same employee + different survey returns different
  pseudonym; different employee + same survey returns different
  pseudonym.
- **Tests:** unit test in `tests/regression/test_engagement_pseudonym.py`.

## T04 — Cohort resolver helper

- **What:** `src/hr_advisory/services/cohort_resolver.py` exposing
  `resolve_cohort(company_id, filter_spec) -> list[int]` — takes the
  cohort filter JSON, returns matched `employee_id` list.
- **Filters supported:**
  - `all_active: bool`
  - `departments: list[str]`
  - `designations_like: list[str]` (case-insensitive substring)
  - `pass_types: list[str]`
  - `tenure_min_days: int | None` (computed against `Employee.start_date`)
  - `tenure_max_days: int | None`
  - `manager_ids: list[int]`
  - `ad_hoc_employee_ids: list[int]`
- **Combine semantics:** union (any match keeps the row), then
  intersected with `is_active=True` unless the spec opts out.
- **Returns:** list of unique `employee_id`s, sorted.
- **Performance:** one Employee list_records, in-memory filter — no
  N+1.
- **Acceptance:** filters produce stable result sets; `tenure_min_days`
  computes correctly off `start_date`; tests with seeded demo data
  cover each filter independently.
- **Tests:** `tests/regression/test_cohort_resolver.py`.

## T05 — Generalise `_theme_tags` for engagement responses

- **What:** Move the keyword-sweep theme derivation from
  `exit_interviews.py:79` into `src/hr_advisory/services/theme_tagger.py`.
  Generalise the API:
  ```python
  def derive_themes(payload: dict, *, reason_keys: list[str], free_text_keys: list[str]) -> list[str]
  ```
  Exit-interviews calls it with `reason_keys=["q3_reasons"]`,
  `free_text_keys=["q4_what_worked", "q5_what_to_change", "q6_recommend_why"]`.
  Engagement calls it with the appropriate keys per template.
- **Keyword map:** keep the existing 6-theme map (manager / comp /
  growth / workload / culture / role) as the default, but allow per-call
  override.
- **Acceptance:** existing exit-interview themes don't drift on the
  refactor; engagement responses produce sensible themes from the
  monthly_pulse template.
- **Tests:** `tests/regression/test_theme_tagger.py`.

## T06 — Email queue table

- **What:** Add `EmailDeliveryJob` model OR extend an existing one
  (check `Notification` / `EmailJob` / etc. — investigation task
  before implementation):
  ```python
  @db.model
  class EmailDeliveryJob:
      company_id: int
      to_email: str
      subject: str
      template_id: str           # e.g. "engagement_survey_invite"
      template_vars: str = ""    # JSON
      status: str = "queued"     # queued | sent | failed | retrying
      attempt_count: int = 0
      last_error: str = ""
      sent_at: Optional[datetime] = None
  ```
- **Worker:** `scripts/process_email_jobs.py` runs every minute via
  cron-via-docker-exec (P16). Drains up to 50 queued jobs per tick.
  Exponential backoff on failure (max 5 attempts).
- **Why:** M4 from red-team — launching to 280 employees would time
  out the launch request. Even 28 needs retry on transient failure.
- **Acceptance:** launch endpoint enqueues N rows; worker drains them;
  failed sends retry; status visible to admin via `/api/admin/email-queue`.

## Dependencies

T01 → T02 (frontend) and T01 → engagement public route (M3).
T03 ← T05 (theme tagger doesn't need pseudonym, independent).
T04 ← M3 (launch flow uses it).
T06 ← M3 (launch flow enqueues).

## Acceptance gate for M0

- All five primitives shipped + unit-tested.
- No regression in existing exit-interview live walk.
- New helpers documented with module-level docstrings.
