# M1 — Data model + migrations

**Source plan:** `02-plans/01-data-model.md` (incl. red-team revisions
for C1, C2, C3, S1, M2).

Five new DataFlow models in `src/hr_advisory/models/company_user.py`.
Built after M0 because the model definitions reference T03 (HMAC) and
T04 (cohort filter spec).

## T10 — `EngagementSurveyTemplate`

- **What:** Add the model exactly as in `02-plans/01-data-model.md`
  §EngagementSurveyTemplate. Fields: company_id, name, description,
  methodology, sections (JSON), is_archived, created_by + soft_delete.
- **Methodology enum:** validate `methodology in {custom, gallup_q12,
trust_index, pulse, enps}` at handler level (DataFlow doesn't
  enforce enums).
- **Section JSON shape:** mirror `AppraisalTemplate.sections`
  exactly. Document the schema in the model docstring.
- **Acceptance:** model imports cleanly; DataFlow nodes register;
  empty-list query returns `[]` for a fresh company.

## T11 — `EngagementCohort`

- **What:** Model with company_id, name, description, filter_spec
  (JSON), is_archived, created_by.
- **filter_spec validation:** at handler level — reject unknown keys,
  enforce types, validate `tenure_min_days >= 0`, `tenure_max_days
  > = tenure_min_days`.
- **Acceptance:** model imports; CRUD-roundtrip via DataFlow.

## T12 — `EngagementSurvey`

- **What:** Model with red-team additions:
  - `template_sections_snapshot: str` (C3) — JSON snapshot at launch
  - `anonymity_tier: str = "identified"` (C2) — one of identified /
    pseudonymous / anonymous, validated at handler
  - `voided_count: int = 0` (C1)
  - `consent_notice_version: str = ""` (S1)
  - all baseline fields per plan
- **Acceptance:** model imports; `template_sections_snapshot` is set
  at launch (M3 task) and never updated thereafter.

## T13 — `EngagementSurveyResponse`

- **What:** Model with red-team additions:
  - `employee_pseudonym: str = ""` (C2) — populated when parent
    survey's anonymity_tier is `pseudonymous`
  - `is_void: bool = False` + `voided_at: Optional[datetime]` (C1)
  - `consent_notice_version: str = ""` (S1, echoed from parent at submit)
  - `enps_score: Optional[int] = None` (m1, was sentinel int=-1)
  - all baseline fields per plan
- **Indexes:** add `idx_esrsp_pseudonym` for pseudonym-keyed trend
  joins.
- **Acceptance:** model imports; pseudonym index present; no
  collision with the employee_id index.

## T14 — `EngagementSurveySchedule`

- **What:** Model with red-team additions:
  - `last_skipped_at: Optional[datetime]` (M2) — when cron tick
    skipped a launch because the prior survey was still open
  - `anonymity_tier: str = "pseudonymous"` (default for pulse cadence)
  - all baseline fields per plan
- **Acceptance:** model imports; cron tick task (M9) reads/writes
  `last_skipped_at`.

## T15 — Migration

- **What:** Run `alembic revision --autogenerate -m "engagement
surveys"` (or DataFlow's equivalent) to produce the migration. Six
  CREATE TABLE statements + indexes (5 originals plus
  `EngagementAction` from T17a).
- **Add `Company.engagement_secret`** (T03) in the same migration —
  encrypted text column. Default null; lazy-generated on first use.
- **Test on staging DB first:** confirm migrations reversible and
  idempotent.
- **Rollback test (Z05):** apply migration → seed 5 rows across all
  6 tables → `alembic downgrade -1` → assert clean uninstall (no
  orphan indexes, no orphan FK constraints).
- **Acceptance:** DB schema matches model definitions; rollback
  produces clean uninstall; no impact on existing tables.

## T16 — Seed shipped library entries on first GET (P1 scope)

- **What:** When `GET /engagement-surveys/templates` returns empty
  for a company, seed two library entries (round-3 trim):
  1. **`gallup_q12_paraphrase`** — 12 Likert-5 questions, paraphrased
     (per `01-research/01-methodology-landscape.md`). Marked
     `methodology=gallup_q12`. Default anonymity = identified.
     Default cadence: quarterly. (Owner decision: keep Q12 quarterly,
     no micro-pulse variant.)
  2. **`monthly_pulse`** — 4 questions: Likert "feeling about work",
     eNPS 0-10, free-text "what's getting in your way", multi-select
     reasons. `methodology=pulse`. Default anonymity = pseudonymous.
- **Trust Index + Singapore SME templates:** **moved to M8 T82 / T83**
  (P2). They need `sg-employment-law-expert` review before ship and
  P1 ships without them.
- **Implementation:** seed function called inside the GET handler;
  idempotent (skip if any template exists); writes via
  dataflow_crud.create.
- **Acceptance:** new company → first GET returns 2 templates (P1
  scope); second GET returns the same set; templates owned by the
  calling company.

## T17a — `EngagementAction` model (round-3, action loop)

- **What:** Add new model in `src/hr_advisory/models/company_user.py`
  to wire the action loop:
  ```python
  @db.model
  class EngagementAction:
      company_id: int
      survey_id: int
      cohort_label: str = ""
      finding_summary: str = ""
      suggested_action_text: str = ""
      status: str = "proposed"          # proposed | accepted | rejected | done
      linked_goal_id: int = 0           # links to Goals module if HR opts in
      next_pulse_question: str = ""     # text to anchor in next pulse
      next_pulse_survey_id: int = 0     # the next pulse this measures against
      created_by: int
      created_at: datetime
      resolved_at: Optional[datetime]
      resolved_score_delta: Optional[float]
  ```
- **Why:** the action loop is the round-3 product addition. Without
  this model, surveys are theatre — measure pain without relieving it.
- **Indexes:** `idx_engagement_action_survey_id`,
  `idx_engagement_action_status`, `idx_engagement_action_linked_goal`.
- **Acceptance:** model imports; CRUD via DataFlow nodes; can link to
  Goals module via `linked_goal_id`.

## T17 — Termination sweep (C1)

- **What:** When an employee is deactivated (existing termination
  flow in `employees.py`), find pending `EngagementSurveyResponse`
  rows for that employee and set `is_void = True`, `voided_at = now()`.
  Bump parent survey's `voided_count`.
- **Why:** C1 — open responses for terminated employees should not
  count in aggregations and should not be reachable via tokenised
  link.
- **Public link behaviour:** preflight returns `{ok: false, reason:
"voided"}` (new semantic state, mirrors P36).
- **Acceptance:** termination flow tests assert pending engagement
  responses get voided; aggregator excludes voided rows; preflight
  returns the correct semantic state.

## Dependencies

T15 (migration) blocks all of M2 / M3 / M4 — backend can't write
without the schema.

T16 depends on T10 (template model exists).

T17 depends on T13 + the existing termination handler.

## Acceptance gate for M1

- Five new tables in DB; migration reversible.
- Backend can `dataflow_crud.create` for every model.
- New company gets shipped library on first GET.
- Termination flow sweeps engagement responses.
- All model unit tests green.
