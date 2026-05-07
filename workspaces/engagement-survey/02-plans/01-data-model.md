# Data model

Five new DataFlow models, all in `src/hr_advisory/models/company_user.py`
following existing conventions (snake_case, `__dataflow__` indexes,
soft-delete where appropriate).

## EngagementSurveyTemplate

Authoring-side. Reusable question template; HR can clone the
shipped library entries.

```python
@db.model
class EngagementSurveyTemplate:
    """Question template used to launch one or more engagement surveys.

    sections JSON shape mirrors AppraisalTemplate.sections so the same
    React question-rendering components can serve both modules:

      [
        {
          "title": "Growth & Development",
          "questions": [
            {"id": "q1", "text": "...", "type": "likert5", "is_required": true},
            {"id": "q2", "text": "...", "type": "single", "options": ["...","..."]},
            {"id": "q3", "text": "...", "type": "multi",  "options": ["...","..."]},
            {"id": "q4", "text": "...", "type": "short_text", "max_length": 200},
            {"id": "q5", "text": "...", "type": "long_text",  "max_length": 2000},
            {"id": "q6", "text": "...", "type": "enps"},  # 0-10
          ]
        },
        ...
      ]
    """

    company_id: int
    name: str = ""
    description: str = ""
    methodology: str = "custom"  # custom | gallup_q12 | trust_index | pulse | enps
    sections: str = ""  # JSON
    is_archived: bool = False
    created_by: int = 0

    __dataflow__ = {
        "soft_delete": True,
        "indexes": [
            {"name": "idx_estpl_company", "fields": ["company_id"]},
            {"name": "idx_estpl_methodology", "fields": ["methodology"]},
        ],
    }
```

**Shipped library entries (seeded per company on first use):**

- `gallup_q12_paraphrase` — 12 Likert-5 statements, paraphrased.
- `trust_index_pillars` — 5 sections (Credibility / Respect / Fairness
  / Pride / Camaraderie), 6-8 Likert-5 statements each, plus 2 free
  text.
- `monthly_pulse` — 4 questions: 1 Likert (overall this week), 1 eNPS,
  1 short text "what's getting in your way", 1 multi-select reasons.
- `singapore_sme_quarterly` — 8 Likert + 2 free text, FWA/PDPA/CPF
  context.

## EngagementCohort

Defines who a survey targets. Stored as a filter spec, resolved to
an actual employee list at launch time.

```python
@db.model
class EngagementCohort:
    """Targeting filter for an engagement survey.

    filter_spec JSON:
      {
        "all_active": true,                                 # OR
        "departments": ["Engineering", "Sales"],            # OR
        "designations_like": ["%manager%"],                 # OR
        "pass_types": ["EP", "SP"],                         # OR
        "tenure_min_days": 90,
        "tenure_max_days": null,
        "manager_ids": [12, 14],
        "ad_hoc_employee_ids": [1, 5, 9]                    # union of all above
      }
    """

    company_id: int
    name: str = ""
    description: str = ""
    filter_spec: str = ""  # JSON
    is_archived: bool = False
    created_by: int = 0

    __dataflow__ = {
        "indexes": [{"name": "idx_ecoh_company", "fields": ["company_id"]}],
    }
```

## EngagementSurvey (the launched instance)

One row per "we sent out the H1 2026 pulse to all staff on 7 May".

```python
@db.model
class EngagementSurvey:
    """A launched survey instance — template + cohort + window.

    Snapshots the template's `sections` JSON at launch (red-team C3):
    edits to the template after launch do not corrupt aggregator
    output. Aggregators read `template_sections_snapshot`, never the
    live template.

    `anonymity_tier` is one of:
      - `identified`    — full employee_id stored; admin sees names
      - `pseudonymous`  — employee_id zeroed; pseudonym (HMAC) stored
                          on the response so cross-stage trends still
                          work without de-identifying
      - `anonymous`     — employee_id zeroed; no pseudonym stored
    Default for pulse cadence is `pseudonymous`; default for annual
    Q12-style is `identified`.
    """

    company_id: int
    template_id: int
    template_sections_snapshot: str = ""  # JSON snapshot at launch (C3)
    cohort_id: int = 0           # 0 = ad-hoc; spec stored in cohort_filter_spec
    cohort_filter_spec: str = "" # JSON snapshot at launch (so subsequent cohort edits don't change history)
    name: str = ""               # e.g. "H1 2026 Pulse — All Staff"
    anonymity_tier: str = "identified"  # identified | pseudonymous | anonymous
    schedule_id: int = 0         # 0 = one-off; otherwise links to EngagementSurveySchedule
    launched_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None  # auto-close after this date
    closed_at: Optional[datetime] = None
    response_count: int = 0
    target_count: int = 0
    voided_count: int = 0        # responses voided after termination (C1)
    consent_notice_version: str = ""  # PDPA — exact text shown to respondent (S1)
    is_archived: bool = False
    created_by: int = 0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_esur_company", "fields": ["company_id"]},
            {"name": "idx_esur_template", "fields": ["template_id"]},
            {"name": "idx_esur_schedule", "fields": ["schedule_id"]},
        ],
    }
```

## EngagementSurveyResponse

One row per (survey, employee). Created at launch as `pending`,
filled in on submit. The shape mirrors `ExitInterview` deliberately
so the existing tokenised public-link plumbing works unchanged.

```python
@db.model
class EngagementSurveyResponse:
    """Per-employee response to a launched survey.

    Anonymity behaviour at submit time follows the parent survey's
    `anonymity_tier`:
      - identified   → employee_id remains, employee_pseudonym = ""
      - pseudonymous → employee_id zeroed, employee_pseudonym set to
                       HMAC(company.engagement_secret, employee_id +
                       survey_id). Same employee + same survey = same
                       pseudonym; cross-survey identical pseudonym.
                       Allows trend joins without de-identifying.
      - anonymous    → employee_id zeroed, employee_pseudonym = ""
    """

    company_id: int
    survey_id: int
    employee_id: int = 0      # 0 when not identified
    employee_pseudonym: str = ""  # HMAC, set when anonymity_tier=pseudonymous (C2)
    survey_payload: str = ""  # JSON {q1: "...", q2: 4, q3: ["a","b"], ...}
    likert_scores: str = ""   # JSON {q1: 4, q2: 5, ...} for fast aggregation
    themes: str = ""          # JSON list ["manager", "growth"] derived after submit
    enps_score: Optional[int] = None  # 0-10 if asked, None if not (m1)
    submitted_at: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    consent_notice_version: str = ""  # echoes parent survey at submit (S1)
    is_void: bool = False     # set True if employee terminated mid-window (C1)
    voided_at: Optional[datetime] = None
    is_archived: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_esrsp_company", "fields": ["company_id"]},
            {"name": "idx_esrsp_survey", "fields": ["survey_id"]},
            {"name": "idx_esrsp_employee", "fields": ["employee_id"]},
            {"name": "idx_esrsp_pseudonym", "fields": ["employee_pseudonym"]},
        ],
    }
```

## EngagementSurveySchedule

Recurrence definition for pulse cadences. A daily cron tick consumes it.

```python
@db.model
class EngagementSurveySchedule:
    """Recurrence definition. Cron tick launches new EngagementSurvey
    rows when next_launch_at <= now().
    """

    company_id: int
    template_id: int
    cohort_id: int
    name: str = ""
    cadence: str = "monthly"   # weekly | biweekly | monthly | quarterly
    anonymity_tier: str = "pseudonymous"  # identified | pseudonymous | anonymous
    next_launch_at: Optional[datetime] = None
    last_launched_survey_id: int = 0
    last_skipped_at: Optional[datetime] = None  # M2: cron skipped because prior survey still open
    open_window_days: int = 14
    is_active: bool = True
    created_by: int = 0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_esch_company", "fields": ["company_id"]},
            {"name": "idx_esch_active", "fields": ["is_active"]},
        ],
    }
```

## Relationship diagram

```
                                   EngagementSurveyTemplate
                                            ▲
                                            │ template_id
                                            │
   EngagementCohort ◀── cohort_id ── EngagementSurvey ── schedule_id ──▶ EngagementSurveySchedule
                                            │
                                            │ survey_id
                                            ▼
                                EngagementSurveyResponse ── employee_id ──▶ Employee
                                            │
                                            │ stores
                                            ▼
                              survey_payload + likert_scores + themes
```

## DataFlow + migration concerns

- All five models follow the existing conventions; DataFlow generates
  CRUD nodes automatically.
- The `EngagementSurveyResponse.likert_scores` separate field is a
  denormalised projection of `survey_payload` for fast aggregation
  without parsing JSON server-side. Populate at submit time.
- `tenure_min_days` / `tenure_max_days` in cohort filter is computed
  from `Employee.start_date` at resolution time — no schema change
  needed.
- Cohort `manager_ids` filter uses `Employee.reporting_manager_id`
  (already exists).

## Token shape for public links

Reuse `_make_token` / `_decode_token` from exit_interviews exactly,
with a different prefix:

```python
# In src/hr_advisory/api/routers/engagement_surveys.py
def _make_response_token(response_id: int, company_id: int) -> str:
    payload = {"er": response_id, "co": company_id, "exp": ...}
    return _encode(payload)
```

Frontend public route: `/engagement-survey/[token]/page.tsx` (mirrors
`/exit-survey/[token]/page.tsx`).

## Anonymity invariants

Same shape as ExitInterview — when `is_anonymous` is true on the
`EngagementSurveyResponse`:

- The employee_id is ZEROED on submit (never overwritten with the
  real value).
- Admin views show "Anonymous" instead of the resolved name.
- Cohort aggregation enforces a minimum population size (≥5 by
  default). If a department has 4 employees, anonymous-by-department
  views fall back to "Company-wide aggregate" with a banner.
- Theme analysis aggregates across the entire submitted set, not
  per-employee.

These four invariants need explicit tests; pin them via regression
tests in `tests/regression/test_engagement_anonymity.py`.
