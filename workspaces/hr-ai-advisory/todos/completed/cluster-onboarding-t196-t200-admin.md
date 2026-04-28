# Cluster: Onboarding T196–T200 (admin)

Status: complete (2026-04-28)

## Scope

T196 — Auto-assign default onboarding on employee registration
T197 — Employees page: Directory + Onboarding tabs
T198 — Admin onboarding templates list page
T199 — Per-template builder page (modules + steps CRUD)
T200 — "Assign template" entry point on the Onboarding tab

## What changed

### T196 — Auto-assign default onboarding (already wired)

Verified that `register-employee` already calls `auto_assign_default_onboarding(employee_id, company_id)` in
`src/hr_advisory/api/routers/auth.py:597`. The helper at
`src/hr_advisory/api/routers/onboarding.py:319` does the full job:

- Looks up `OnboardingTemplate` rows for `company_id` with `is_default=True` and `is_active=True`.
- Bails out if none exist or if the employee already has an active assignment.
- Creates the `OnboardingAssignment` with `status="in_progress"`.
- Walks all modules via `_get_all_steps_for_template(template_id, employee=...)`, which already filters
  modules by `is_role_specific` + `role_filter` against the employee's designation.
- Creates an `OnboardingStepProgress` row per step (status `pending`).
- Copies template-level `PreboardingTaskInstance` rows (those with `employee_id=0`) into
  per-employee instances and computes `deadline_date = start_date + relative_days` parsed from
  the `notes` field. (The `PreboardingTaskInstance` model has no dedicated `deadline_relative_days`
  field — the parse-from-notes approach matches the existing schema.)
- Auto-creates 30/60/90-day `OnboardingMilestone` rows.

No code change was needed for T196; the path already exists and is exercised by
`tests/unit/test_recruitment_regression.py`.

### T197 — Employees Directory + Onboarding tabs (already wired)

The page at `apps/web/src/app/(dashboard)/employees/page.tsx` already renders three tabs
(`Directory`, `Onboarding`, `Invitations`) with a shared toolbar and URL `?tab=` syncing.
The Onboarding tab calls `GET /onboarding/assignments` and shows analytics, search, status
filter, and per-employee expansion (preboarding tasks, IT provisioning, milestones, surveys).

Updated only to add the T200 button — see below.

### T198 — Admin templates list page (NEW)

`apps/web/src/app/(dashboard)/onboarding/page.tsx`

A new admin route, gated by `<AdminGuard>`. Behaviour:

- Lists all templates for the current company via `GET /onboarding/templates`.
- Sorted: default first, then alphabetical.
- Per-row actions: Edit (links to the builder), Duplicate, Set default, Archive.
- Header "Create template" button opens an inline modal that hits `POST /onboarding/templates`
  and routes the user straight into the new template's builder.

### T199 — Template builder page (NEW)

`apps/web/src/app/(dashboard)/onboarding/templates/[id]/page.tsx`

Loads `GET /onboarding/templates/{id}` (which returns the template with modules and steps inlined),
shows a back-link to `/onboarding`, and supports the full CRUD:

- Edit template metadata (name, description, default flag) → `PUT /onboarding/templates/{id}`.
- Add module → `POST /onboarding/templates/{id}/modules` with name, description, phase
  (orientation / compliance / benefits / probation / custom), `sort_order`, `estimated_duration_minutes`,
  `is_mandatory`, `is_role_specific`, and `role_filter` (validated as JSON array).
- Edit / delete module → `PUT|DELETE /onboarding/modules/{id}`.
- Add step → `POST /onboarding/modules/{id}/steps` with title, description, step_type
  (content / checklist / document_upload / policy_acknowledgment / form / approval),
  `body_content`, `sort_order`, `requires_completion`, `requires_previous_completion`, `policy_id`.
- Edit / delete step → `PUT|DELETE /onboarding/steps/{id}`.

Per the brief, drag-to-reorder was deferred — instead the modal exposes a numeric `sort_order`
input (lower numbers appear first), which is exactly how the backend stores it. The reorder
endpoints (`PATCH /onboarding/templates/{id}/reorder` and `PATCH /onboarding/modules/{id}/reorder-steps`)
are still available for a future drag-and-drop pass.

### T200 — "Assign template" from Onboarding tab (wired in the existing page)

`apps/web/src/app/(dashboard)/employees/page.tsx`

- Added an `onAssignClick` prop on `OnboardingTab` and a "Assign template" primary button next to
  Export CSV.
- Added a small in-page `AssignFromOnboardingTabModal` that picks an active employee (search by
  name / email / department / designation) and chains into the existing `AssignTemplateModal`
  (which handles template selection, due date, and optional buddy via `POST /onboarding/assign`).

The previous "Onboard" button on each row of the Directory tab is preserved — both flows now
funnel into the same `AssignTemplateModal`.

### API client extensions

`apps/web/src/services/api/onboarding.ts`

- New types: `OnboardingModuleWithSteps`, `OnboardingTemplateDetail`.
- New admin methods that match the actual backend response envelopes:
  `getTemplateAdmin`, `createTemplateAdmin`, `updateTemplateAdmin`,
  `addModuleAdmin`, `updateModuleAdmin`, `deleteModuleAdmin`,
  `addStepAdmin`, `updateStepAdmin`, `deleteStepAdmin`.
- The existing client methods (used by `TemplateBuilder.tsx`, which I was not allowed to touch)
  were left untouched; I added `sort_order` and `requires_previous_completion` as optional fields
  on the existing types so both old and new code compile.

## Files changed

- NEW `apps/web/src/app/(dashboard)/onboarding/page.tsx` — admin template list (T198).
- NEW `apps/web/src/app/(dashboard)/onboarding/templates/[id]/page.tsx` — template builder (T199).
- MOD `apps/web/src/services/api/onboarding.ts` — new admin client methods + nested-detail types.
- MOD `apps/web/src/app/(dashboard)/employees/page.tsx` — Onboarding-tab "Assign template" button
  - employee picker modal (T200). T197 tabs were already in place.

Files NOT touched (per constraints):

- `src/hr_advisory/models/company_user.py`
- `src/hr_advisory/api/routers/onboarding.py`
- `src/hr_advisory/api/routers/recruitment.py`
- `src/hr_advisory/api/routers/employees.py`
- `apps/web/src/components/onboarding/TemplateBuilder.tsx`
- `apps/web/src/components/onboarding/AssignTemplateModal.tsx`
- `src/hr_advisory/api/routers/auth.py` (T196 hook already present)

## Tests

Per the test-once protocol, no full suite run was triggered. The auto-assign hook is already
exercised by `tests/unit/test_recruitment_regression.py`. No new tests were added for this
cluster (it's UI-heavy + backend was unchanged).

## Known limitations / follow-ups

- Reorder of modules / steps is currently a numeric `sort_order` input. The reorder endpoints
  exist; a drag-and-drop pass can wire `PATCH /onboarding/templates/{id}/reorder` and
  `PATCH /onboarding/modules/{id}/reorder-steps` later.
- The pre-existing `getTemplate` and `createTemplate` types in `onboarding.ts` don't match
  the actual backend envelope shape; the legacy `TemplateBuilder.tsx` UI may show "no modules"
  on every template. The new pages bypass it via the new `*Admin` methods.
