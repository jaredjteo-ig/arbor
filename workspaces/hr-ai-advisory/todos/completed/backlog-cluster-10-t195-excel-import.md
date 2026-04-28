# T195 — Onboarding Excel Template Import

**Status:** Complete (audit + regression tests added)
**Completed at HEAD:** `3440ee0`
**Endpoint:** `POST /onboarding/templates/import`

## Audit result

The endpoint and the parser both already existed at HEAD `3440ee0`:

- **Router:** `src/hr_advisory/api/routers/onboarding.py:804-1605` (~800 lines)
- **Parser:** `src/hr_advisory/services/onboarding_parser.py` (589 lines)
- **Dependency:** `openpyxl>=3.1.0` already declared in `pyproject.toml:58`

This task therefore became an audit + regression-test task, not a build task.
No production code was changed.

## Sheets wired

All 12 sheets are parsed and persisted by the existing implementation:

| Sheet | Name                   | Result                                                                                                                                                                    |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Company Profile        | Enriches `OnboardingTemplate.description` with mission/vision/values                                                                                                      |
| 2     | Org Structure          | Creates a "Department Overview" content step in the orientation module                                                                                                    |
| 3     | Onboarding Modules     | Creates `OnboardingModule` records (REQUIRED — minimum viable)                                                                                                            |
| 4     | Step Content           | Creates `OnboardingStep` records (REQUIRED — minimum viable)                                                                                                              |
| 5     | Role Configuration     | Sets `OnboardingModule.role_filter` and appends role/buddy/goal metadata to template description                                                                          |
| 6     | IT Provisioning        | Creates `PreboardingTaskInstance` records with `owner_role="it"`                                                                                                          |
| 7     | Policies & Compliance  | Matches against existing `CompanyPolicy` (by title); creates `OnboardingStep` of type `policy_acknowledgment` (linked) or `content` (unlinked) inside a compliance module |
| 8     | Benefits Overview      | Creates content steps inside a "Benefits Overview" module                                                                                                                 |
| 9     | Probation & Goals      | Creates 30/60/90-day checklist steps inside a "Probation & Goals" module                                                                                                  |
| 10    | Comms & Channels       | Creates a "Communication Channels" content step in the orientation module                                                                                                 |
| 11    | Key Contacts           | Creates a "Key Contacts" content step in the orientation module                                                                                                           |
| 12    | Pre-boarding Checklist | Creates `PreboardingTaskInstance` records (HR/manager/IT/office_manager)                                                                                                  |

Nothing is deferred to T213 from a coverage perspective — the implementation
already maps every sheet. T213 (richer policy linking, deadline parsing,
EmployeeMilestone seeding, etc.) remains future work as scoped in
`onboarding-phase-b-d.md`.

## Tests added

`tests/unit/test_onboarding_import.py` (4 cases, all green):

1. **`test_minimum_viable_import_creates_template_modules_and_steps`** — only
   sheets 3 + 4 present. Verifies template, modules, and steps are created
   and linked correctly.
2. **`test_step_with_unknown_module_recovers_with_warning`** — a step with
   `module_name` that doesn't match any module is reattached to the first
   module rather than aborting the import. Verifies the partial-import
   recovery path.
3. **`test_tenant_isolation_uses_auth_company_id_not_workbook_company`** —
   uploads a workbook whose Sheet 1 declares a _different_ company name. The
   created records' `company_id` must come from the auth context (`42`), not
   from the workbook contents.
4. **`test_rejects_non_xlsx_file_extension`** — non-`.xlsx` uploads return
   HTTP 400 and create no records.

Tests build a real .xlsx in memory with `openpyxl`, mock `dataflow_crud` with
an in-memory fake (preserves create/read/list/update semantics including the
filter dict), and exercise the FastAPI endpoint via `TestClient` with
`require_role("owner", "hr_manager")` satisfied through dependency override
of `get_current_user`.

Run command (test-once protocol — only this file):

```bash
.venv/bin/python -m pytest tests/unit/test_onboarding_import.py -v
# 4 passed in ~2.8s
```

## Notes / discrepancies vs. the brief

- **File size cap:** the brief specified 5 MB, but the existing endpoint uses
  10 MB (`MAX_FILE_SIZE = 10 * 1024 * 1024` at `routers/onboarding.py:49`,
  matching the parser's own 10 MB cap at `onboarding_parser.py:21`). I did
  NOT change this — reducing it is a behavioural change that should land as
  a deliberate decision rather than a side-effect of T195. Flag for review.
- **Rate limit:** existing endpoint already calls
  `check_rate_limit(f"onboarding_upload:{company_id}", max_requests=10, window_seconds=300, ...)`.
- **Role check:** existing endpoint already enforces
  `require_role("owner", "hr_manager")`.
- **Tenant isolation:** confirmed by both code inspection (every `create()`
  call uses `company_id` from `get_current_company_id(current_user)`) and by
  the regression test above.
- **`openpyxl` install in dev venv:** the package is declared in
  `pyproject.toml` but was missing from `.venv/`. Installed via
  `pip install 'openpyxl>=3.1.0'` to run the tests. No code change was
  required.

## Files touched

- `tests/unit/test_onboarding_import.py` (new — 4 tests)
- `workspaces/hr-ai-advisory/todos/completed/backlog-cluster-10-t195-excel-import.md` (this file)

## Files NOT touched (as audit was clean)

- `src/hr_advisory/api/routers/onboarding.py`
- `src/hr_advisory/services/onboarding_parser.py`
- `pyproject.toml`
