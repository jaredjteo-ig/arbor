# Cluster: Onboarding T201-T207 — Employee Self-Service UI

**Status**: Complete
**Owner**: Cluster (parallel agent)
**Date**: 2026-04-28

## Summary

Implements the employee-facing onboarding self-service experience: a
modular `/my-onboarding` page that fetches `GET /onboarding/my-progress`,
renders module-grouped step lists with type-specific renderers, and
exposes an admin pre-boarding view plus an HR-triggered overdue-step
reminder endpoint.

## Tasks delivered

### T201 — `/my-onboarding` page

- Path: `apps/web/src/app/(dashboard)/my-onboarding/page.tsx`
- Header: clipboard icon, page title (i18n), template name, due-date
  inline (`Due by 12 May 2026`).
- Calls `onboardingApi.getMyProgress()`. Handles three states:
  unauthenticated/no-assignment (EmptyState), error (retry button),
  success (module list). 404s collapse to no-assignment messaging.
- Module-grouped step list. Each module is collapsible, shows phase
  badge (Orientation / Compliance / Benefits / Probation / Custom),
  per-module mini progress bar, and step-count summary.
- Each step row shows status badge (pending / in_progress / completed
  / skipped) and dispatches the right CTA via the new step components.

### T202 — Step type renderers

Six new components under `apps/web/src/components/onboarding/steps/`:

- `ContentStep.tsx` — renders `body_content` as `whitespace-pre-wrap`
  (deliberately not `dangerouslySetInnerHTML`); "Mark as Read" button
  calls `completeStep`.
- `ChecklistStep.tsx` — parses `checklist_items` (JSON or
  newline-separated text), per-item checkboxes, "Complete" button
  enabled only when every item is checked.
- `DocumentUploadStep.tsx` — file picker with `accept=".pdf,.jpg,..."`,
  client-side 10 MB guard mirroring backend, calls
  `uploadStepDocument`. Once completed, displays the uploaded
  filename.
- `PolicyAcknowledgmentStep.tsx` — fetches the linked `CompanyPolicy`
  via `policiesApi.get(policy_id)`, displays title + category, links
  to `/policies/{id}` in a new tab, requires "I acknowledge" checkbox
  before submit. Calls `acknowledgeStep`.
- `FormStep.tsx` — parses a JSON form schema from `body_content` (or
  any future dedicated `form_schema` field), supports text / email /
  tel / number / textarea / select fields with required-field
  validation, submits `form_data` via `POST /onboarding/steps/{id}/
complete`.
- `ApprovalStep.tsx` — read-only, "Awaiting approval from {{approver}}"
  with approver name fallback to "HR". Switches to "Approved <date>"
  when status is completed.

Plus `steps/index.ts` barrel export.

### T203 — Mark as completed

- Each step renderer calls the appropriate API method
  (`completeStep` / `uploadStepDocument` / `acknowledgeStep` / form
  submit). The page passes a `fetchProgress` callback so successful
  completions reload the assignment, refreshing the step status,
  module progress bar, and overall percent.

### T204 — ProgressBar component

- Path: `apps/web/src/components/onboarding/ProgressBar.tsx`
- Linear bar showing % complete; clamps and rounds the input value;
  proper `role="progressbar"` with aria-valuenow / valuemin / valuemax
  for accessibility.
- When passed a `modules` array, hover/focus reveals a tooltip with
  per-module breakdown (`Module Name  3/5 (60%)`).
- Used on the my-onboarding page above the module list.

### T205 — Pre-boarding checklist for upcoming hires

- Path: `apps/web/src/components/onboarding/PreboardingChecklist.tsx`
- Calls `GET /onboarding/preboarding/{employee_id}` and
  `PATCH /onboarding/preboarding/{task_id}`.
- Renders pending tasks with owner role label (HR / Manager / IT /
  Office Manager), deadline, and overdue badge. "Mark done" updates
  the task and refreshes the list.
- Surfaced on the my-onboarding page when an HR/owner user passes
  `?employee_id=N` in the URL — gated client-side on the auth role
  _and_ enforced server-side by the existing `require_role`
  decorator.

### T206 — Side nav entry

- Verified: "My Onboarding" was already wired into
  `employeeCoreNavItems` in
  `apps/web/src/components/shell/NavigationSidebar.tsx` (label key
  `nav.my-onboarding`, route `/my-onboarding`, ClipboardCheck icon).
  No change required.

### T207 — Overdue-step reminder endpoint

- Appended to `src/hr_advisory/api/routers/onboarding.py`:
  - `_build_overdue_reminder_email()` — HTML body builder, escapes
    user content.
  - `_send_overdue_reminders_for_company()` — scans
    `OnboardingAssignment` rows for the company, skips completed /
    cancelled / no-due-date / not-yet-overdue, finds pending
    `OnboardingStepProgress`, resolves employee + user + email +
    template, dispatches via `ResendAdapter.send_email`. Caps the
    digest at 25 step titles. Failures inside the loop are logged
    but do not abort.
  - `POST /onboarding/reminders/send-overdue` — owner/hr_manager
    only, rate-limited at **5 calls per hour per company** so a
    misbehaving cron or repeated clicks cannot spam employees. No
    DB-backed last-reminded-at marker yet — easy follow-up if real
    cron triggers it daily.
  - When `RESEND_API_KEY` is unset, returns a clean summary with
    `skipped: -1` (sentinel) instead of erroring.
- API client: `onboardingApi.sendOverdueReminders()` added in
  `apps/web/src/services/api/onboarding.ts`.
- Optional test: `tests/unit/test_onboarding_reminders.py` covers
  RBAC (employee gets 403), no-API-key short circuit, the happy
  path filtering (overdue / fresh / completed / no-due-date), and
  the rate-limit guard. Tests fully mock `dataflow_crud` and the
  Resend adapter — no DB or HTTP I/O. (Not run per the cluster's
  test-once protocol.)

## Files touched

### New

- `apps/web/src/components/onboarding/steps/ContentStep.tsx`
- `apps/web/src/components/onboarding/steps/ChecklistStep.tsx`
- `apps/web/src/components/onboarding/steps/DocumentUploadStep.tsx`
- `apps/web/src/components/onboarding/steps/PolicyAcknowledgmentStep.tsx`
- `apps/web/src/components/onboarding/steps/FormStep.tsx`
- `apps/web/src/components/onboarding/steps/ApprovalStep.tsx`
- `apps/web/src/components/onboarding/steps/index.ts`
- `apps/web/src/components/onboarding/ProgressBar.tsx`
- `apps/web/src/components/onboarding/PreboardingChecklist.tsx`
- `tests/unit/test_onboarding_reminders.py`

### Modified

- `apps/web/src/app/(dashboard)/my-onboarding/page.tsx`
  (refactored to delegate step rendering to step components and to
  use ProgressBar + the admin pre-boarding section)
- `apps/web/src/services/api/onboarding.ts`
  (added `sendOverdueReminders()`)
- `src/hr_advisory/api/routers/onboarding.py`
  (appended T207 endpoint + helpers)

### Untouched

- `apps/web/src/components/shell/NavigationSidebar.tsx`
  (T206 already wired; no edit needed)
- `routers/auth.py`, `routers/employees.py`, `routers/recruitment.py`,
  `models/company_user.py`, `(dashboard)/employees/page.tsx`,
  `(dashboard)/onboarding/**` — all left alone per the brief.

## Testing notes

- Per cluster instructions, the suite was NOT run. Optional
  T207 tests are designed to run in isolation:
  `pytest tests/unit/test_onboarding_reminders.py`.
- All new user-visible strings use `react-i18next`'s `t()` with
  English `defaultValue` fallbacks. Non-English bundles were not
  updated (cluster 9 owns translation keys).

## Follow-ups (out of scope here)

- Persist `last_reminded_at` on `OnboardingStepProgress` so the
  reminder endpoint can debounce per-step (e.g. send once per 48h
  per step) when a real cron runs daily.
- Wire a small "Send overdue reminders" button into the admin
  onboarding dashboard (cluster owns that page).
- Translate user-visible strings into the non-English bundles.
