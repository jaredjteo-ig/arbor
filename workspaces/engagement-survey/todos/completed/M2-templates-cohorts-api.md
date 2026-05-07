# M2 — Backend API: templates + cohorts

**Source plan:** `02-plans/02-api-and-routes.md` §Templates and §Cohorts.

CRUD scaffolding for the authoring side. No employee-facing flow
yet — that's M3.

## T20 — Router scaffolding

- **What:** Create `src/hr_advisory/api/routers/engagement_surveys.py`
  with the FastAPI `router` instance and standard imports (auth,
  rate_limit, tenant_isolation, dataflow_crud, \_helpers).
- **Register** in `src/hr_advisory/api/main.py` (or wherever routers
  are mounted) under prefix `/engagement-surveys`, with the `engagement`
  tag for OpenAPI grouping.
- **Acceptance:** `GET /engagement-surveys/templates` returns 401
  (auth required) when called without a Bearer header.

## T21 — Templates CRUD

- **Endpoints:**
  - `GET /templates` — list with seed-on-empty (T16)
  - `GET /templates/{id}`
  - `POST /templates` — create or clone (clone uses `?clone_from=N`)
  - `PATCH /templates/{id}` — whitelist fields (P39): `name`,
    `description`, `sections`, `methodology`, `is_archived`. Reject
    `id`, `company_id`, `created_by`, `created_at`.
  - `DELETE /templates/{id}` — soft-delete (sets `is_archived=True`).
- **Auth:** all `require_role("owner", "hr_manager")`.
- **Tenant:** all `validate_company_access(current_user, ...)`.
- **Validation:**
  - `name` 1..200 chars; reject empty.
  - `sections` must be valid JSON; warn (don't reject) if no questions.
  - `methodology` in the validated enum (T10).
- **Acceptance:** CRUD-roundtrip works for owner + hr_manager;
  employees get 403; cross-tenant read returns 404 (not 403).
- **Tests:** `tests/regression/test_engagement_templates.py`.

## T22 — Cohorts CRUD (P1 scope: presets + ad-hoc only)

- **Endpoints:**
  - `GET /cohorts` — returns saved cohorts. Includes 3 system-seeded
    presets:
    - `all_active_staff` (filter_spec: `{all_active: true}`)
    - `by_department` (preset, requires department selection by HR)
    - `new_joiners_under_90d` (filter_spec: `{tenure_max_days: 90}`)
  - `POST /cohorts` — create custom cohort with **preset + optional ad-hoc list** at P1. Full filter UI (full pass_type/tenure/manager/dept combinator) defers to M8 T91.
  - `PATCH /cohorts/{id}` — whitelist `name`, `description`, `filter_spec`, `is_archived`.
  - `DELETE /cohorts/{id}` — soft-delete.
- **Auth + tenant:** same as templates.
- **P1 filter_spec accepted at create-time:**
  - `{all_active: true}` (preset)
  - `{departments: [...]}` (preset, single dimension)
  - `{tenure_max_days: 90, all_active: true}` (preset)
  - `{ad_hoc_employee_ids: [...]}` (ad-hoc)
  - Combinations of preset + ad_hoc list (e.g. department + extra individual employees)
- **filter_spec validation:** call shared validator from `cohort_resolver.py` (T04). Reject unknown keys, multi-dimension combinators rejected at P1 with message "Multi-dimension cohort builder ships at v2."
- **Round-3 rationale:** SMEs of 28 produce mostly n<5 suppressed cells in any deep slice. Three presets + ad-hoc covers ~95% of pulse cohorts. Full UI ships at M8 T91 after P1 lands.
- **Acceptance:** valid preset accepted; deep-slice (multi-dimension) rejected with semantic message at P1; presets resolve correctly via T04.
- **Tests:** `tests/regression/test_engagement_cohorts.py`.

## T23 — Cohort preview endpoint

- **Endpoint:** `POST /cohorts/preview`
- **Body:** `{filter_spec: {...}, anonymity_tier: "pseudonymous"}` —
  preview takes filter_spec inline (doesn't require a saved cohort).
- **Z04/M5 cross-tenant guard:** every employee_id resolved is asserted `Employee.company_id == current_user.company_id`; reject 400 if any cross-tenant id present (defends against a malicious or buggy admin sending another tenant's employee_id list).
- **Response:**
  ```json
  {
    "matched_count": 22,
    "sample_names": ["Lily Phang", "Chen Wei", "..."], // first 8 names
    "anonymity_safe": true, // matched_count >= 5
    "warnings": [] // e.g. "Cohort intersects an open survey for these employees"
  }
  ```
- **Implementation:** call `resolve_cohort()` (T04), enrich with names
  via `_resolve_employee_names()`, compute anonymity flag, scan for
  overlap with active surveys (M3 helper).
- **Rate limit:** 30 req/minute (interactive endpoint).
- **Anonymity threshold:** parameterise as `min_cohort_size = 5`
  (constant), not a magic number.
- **Acceptance:** filter for "Engineering" returns 8 employees with
  names; filter for "Management" (2 employees) returns
  `anonymity_safe=false` and a warning naming the threshold.
- **Tests:** unit tests in `tests/regression/test_engagement_cohorts.py`
  with seeded demo data.

## T24 — Survey-overlap warning helper (M3 from red-team)

- **What:** Helper `find_overlapping_surveys(company_id, employee_ids,
*, exclude_survey_id=0) -> list[dict]` that returns active surveys
  whose response set intersects `employee_ids` and which are not
  closed.
- **Returns:** list of `{survey_id, name, target_count, overlap_count}`.
- **Used by:** preview (T23) for the warnings field; launch (M3) to
  show the confirmation modal.
- **Acceptance:** when no active survey, returns `[]`; when active
  survey has 22 of the 28 in this cohort, returns one entry with
  `overlap_count=22`.
- **Tests:** as part of `test_engagement_cohorts.py`.

## Dependencies

T20 → T21, T22, T23, T24 (all need router scaffolding).
T22, T23 → T04 (cohort resolver).
T23 → T24 (overlap helper).

## Acceptance gate for M2

- Templates and cohorts CRUD live with full whitelist + role
  enforcement.
- Cohort preview returns matched count + anonymity flag + warnings.
- All tests green; no regressions in existing exit-interview /
  appraisal endpoints.
