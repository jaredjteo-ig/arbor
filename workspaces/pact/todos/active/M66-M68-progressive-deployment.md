# M66-M68: Progressive Deployment — Trust Ladder UX

**Milestone**: M66 (24-hour aha moment), M67 (agent offer flow), M68 (observation pipeline wiring)
**Priority**: HIGH — converts free users to paid; addresses value proposition critique
**Scope**: both
**Estimated effort**: 5-7 days

The value proposition critique (08) is explicit: the 24-hour aha moment must be
the morning briefing on Day 1, not agent activation. The trust ladder is:
Day 1 advisory + org chart + briefing → Day 3-7 first agent offer → Day 14
first agent activation. This milestone wires the observation pipeline (currently
un-wired per project memory) to feed the suggestion engine.

---

## M66: 24-Hour Aha Moment

### T437: Company setup wizard — step-by-step onboarding

**Scope**: frontend
**Depends**: T402
**Files**:

- `apps/web/app/(onboarding)/setup/page.tsx` (new)
- `apps/web/app/(onboarding)/setup/steps/CompanyProfileStep.tsx` (new)
- `apps/web/app/(onboarding)/setup/steps/EmployeeImportStep.tsx` (new)
- `apps/web/app/(onboarding)/setup/steps/OrgChartConfirmStep.tsx` (new)
- `apps/web/app/(onboarding)/setup/steps/FirstAdvisoryStep.tsx` (new)
- `apps/web/components/setup/SetupProgress.tsx` (new)

**Description**: Multi-step onboarding wizard that delivers the 24-hour aha
moment. Shown to owner on first login after company creation. Steps match
user flow 01 Steps 1-7.

Steps:

1. **Company profile** — industry, headcount, incorporation date. Selects
   org template (`micro_sme`, `small_sme`, `medium_sme`) from T403.
   Stores `company.org_template_key` on save.

2. **Import employees** — choice: "Upload a file (CSV/Excel)" or "Add one by one."
   Both paths converge at org chart confirmation.

3. **Org chart confirmation** — auto-generated org chart from employee data.
   Boss can drag-and-drop to fix reporting lines. One-tap confirm.

4. **First advisory** — pre-loaded question: "Are my employment contracts
   compliant with Singapore employment law?" Triggers the advisory pipeline
   and shows the answer inline. This is the "it actually knows the law" moment.

5. **Setup complete** — summary screen: "Arbor is watching. You'll receive
   your first morning briefing tomorrow at 8am." CTA: "Go to dashboard."

`SetupProgress`: horizontal step indicator showing current step and check marks.

Redirect logic: if `company.setup_completed=True`, skip wizard and go to
dashboard. Set `setup_completed=True` on step 5 completion.

**Acceptance criteria**:

- [ ] Wizard shows on first login when `setup_completed=False`
- [ ] Company profile step updates `org_template_key` via `PATCH /api/companies/{id}`
- [ ] Import step links to CSV import flow (T438)
- [ ] Org chart confirmation calls `POST /api/employees/bulk-update-managers`
- [ ] Advisory step fires real advisory pipeline, shows answer with citations
- [ ] Step 5 sets `setup_completed=True` via `PATCH /api/companies/{id}`
- [ ] Returning to wizard after completion redirects to dashboard immediately
- [ ] Mobile-first layout, progress indicator visible on all steps

---

### T438: CSV/Excel employee import backend

**Scope**: backend
**Depends**: T400
**Files**:

- `src/hr_advisory/api/routers/employees.py` (extend)
- `src/hr_advisory/services/employee_import.py` (new)

**Description**: Bulk employee import from CSV or Excel. Used in setup wizard
step 2 and as a standalone import function from the employee list page.

`POST /api/employees/import`:

- Accepts `multipart/form-data` with `file` field
- Supports `.csv` and `.xlsx` formats (openpyxl for xlsx)
- Column mapping: `name`, `email`, `job_title`, `department`, `manager_email`,
  `employment_type`, `start_date` (all optional except `name` and `email`)
- Returns `{imported: N, skipped: N, errors: [{row, reason}]}`
- Creates employees with `status=active`; skips rows with duplicate email
- Max 500 rows per import (returns 400 if exceeded)

`GET /api/employees/import/template`:

- Returns CSV template with correct column headers
- Includes 2 example rows showing correct format

`employee_import.py`:

- `parse_csv(file_bytes: bytes) -> list[dict]`
- `parse_xlsx(file_bytes: bytes) -> list[dict]`
- `validate_row(row: dict, company_id: int) -> tuple[bool, str]` — checks
  required fields, email format, no duplicate in company
- `import_employees(rows: list[dict], company_id: int) -> ImportResult`

**Acceptance criteria**:

- [ ] CSV with 10 employees imports correctly
- [ ] XLSX with 10 employees imports correctly
- [ ] Duplicate email within same company is skipped (not errored)
- [ ] Row with missing name returns error with row number
- [ ] Import > 500 rows returns 400 with clear message
- [ ] Template download returns valid CSV with correct headers
- [ ] Unit tests: parse_csv, parse_xlsx, validate_row, import_employees
- [ ] Integration test: upload CSV, verify employees created

---

### T439: Org chart bulk-update managers endpoint

**Scope**: backend
**Depends**: T438
**Files**:

- `src/hr_advisory/api/routers/employees.py` (extend)

**Description**: After CSV import, the setup wizard shows an org chart where the
boss can fix reporting lines. This endpoint persists the adjusted tree.

`POST /api/employees/bulk-update-managers`:

- Body: `{updates: [{employee_id: int, manager_id: int | null}]}`
- Updates `employee.manager_id` for each entry
- Max 200 updates per call
- Owner or hr_manager only
- Returns `{updated: N}`

`GET /api/employees/org-chart`:

- Returns org tree as nested JSON: `{id, name, job_title, manager_id, children: [...]}`
- Builds from all active employees in the company
- Sorted: alphabetically within each level
- Includes `is_agent: bool` flag (True for agent service accounts from T411)

**Acceptance criteria**:

- [ ] Bulk-update endpoint accepts up to 200 updates atomically
- [ ] Org-chart endpoint returns valid nested tree for a 10-person company
- [ ] Agent service accounts appear with `is_agent=True` in org chart
- [ ] Employee without manager appears at root level
- [ ] Unit test: build org tree from flat employee list

---

### T440: Morning briefing proactive value enhancements

**Scope**: backend
**Depends**: T422, T433
**Files**:

- `src/hr_advisory/shadow/briefing.py` (modify)

**Description**: The morning briefing is the 24-hour aha moment per gap
resolution C4. On Day 1 it should already surface something useful — the
company has been seeded with demo data that makes the briefing non-empty.

Extend `generate_morning_briefing(company_id: int, user_id: int)`:

1. **Work pass expiry** — list employees with work pass expiring in next
   60 days (using compliance agent detection from T433). Format:
   "Work pass for {name} expires in {N} days."

2. **Leave balance alerts** — employees with less than 3 days annual leave
   remaining. Format: "{N} employees have low annual leave balance."

3. **Probation endings** — employees completing probation in next 14 days.
   Format: "{name} completes probation on {date}. Review performance?"

4. **Pending held actions** — count from T422 (already implemented). Urgent
   items mentioned first.

5. **Payroll deadline** (if `payroll_auto_prepare=False`) — "CPF submission
   for {month} is due in {N} days."

Format as a structured `BriefingContent` dict with sections. Each section
is optional — skip silently if no items. If ALL sections are empty, the
briefing generates: "All clear today. No urgent items."

**Acceptance criteria**:

- [ ] Briefing includes work pass expiry section when expiries exist
- [ ] Briefing includes leave balance alerts when low-balance employees exist
- [ ] Briefing includes probation endings for next 14 days
- [ ] All-clear message when no items in any section
- [ ] Existing briefing tests still pass
- [ ] Unit test: company with 5 different alert types generates correct sections

---

### T441: Briefing push notification — morning delivery

**Scope**: backend
**Depends**: T414, T440
**Files**:

- `src/hr_advisory/pact/notifications/scheduler.py` (extend)

**Description**: Extend the notification scheduler from T414 to include the
morning briefing push notification.

In `process_daily_digest(hour: int = 8)`:

1. For each company where the current SGT hour matches `company.digest_hour_sgt`:
   - Generate briefing via `generate_morning_briefing(company_id, owner_user_id)`
   - If briefing has any non-empty sections: send push notification
     - title: "Good morning, {owner_first_name}"
     - body: first two briefing items as comma-separated summary
     - data: `{type: "morning_briefing", company_id}`
   - Log: "Briefing sent to company {company_id}"

This makes the push notification the daily trigger that brings the boss
into the app (proactive pull model).

**Acceptance criteria**:

- [ ] Briefing push sent at configured `digest_hour_sgt` for each company
- [ ] Push body contains first two briefing items
- [ ] No push sent when briefing is all-clear
- [ ] Unit test: scheduler at 08:00 triggers briefing push for correct companies

---

## M67: Agent Offer Flow

### T442: Observation-based suggestion generator

**Scope**: backend
**Depends**: T411, T424
**Files**:

- `src/hr_advisory/shadow/observation.py` (extend)
- `src/hr_advisory/pact/suggestions.py` (new)

**Description**: The shadow agent observes boss behavior and generates agent
activation suggestions when patterns are detected. Per gap resolution C4
and user flow 01 Steps 3-7, the suggestion appears after 3-7 days of use,
not immediately.

In `observation.py`, add observation event tracking:

`record_observation(company_id: int, event_type: str, data: dict)`:

- Persists to `PactSuggestion.observation_log` (JSON array, append-only)
- Event types: `leave_approved_manually`, `payroll_run_completed`,
  `advisory_question_asked`, `compliance_item_viewed`
- Max 1,000 events per company (sliding window, drop oldest)

In `suggestions.py`:

`check_suggestion_triggers(company_id: int) -> list[PactSuggestion]`:

- Analyzes observation log for patterns
- Creates `PactSuggestion` records when thresholds are met:
  - `leave_approved_manually` >= 3 events → suggest `arbor_hr` activation
  - `payroll_run_completed` >= 1 event → suggest `arbor_payroll` activation
  - `compliance_item_viewed` >= 2 events → suggest `arbor_compliance` activation
- Does NOT create duplicate suggestions (checks for existing active suggestions)
- Returns list of newly created suggestions

`PactSuggestion` model (defined in T400):

- `company_id`, `agent_id` (e.g. `arbor_hr`), `trigger_event` (what caused it),
  `status` (`active`, `accepted`, `dismissed`), `created_at`, `dismissed_at`

**Acceptance criteria**:

- [ ] `record_observation` persists event to observation log
- [ ] `check_suggestion_triggers` creates suggestion after 3 leave approvals
- [ ] No duplicate suggestions for same company + agent combination
- [ ] Suggestion not created if agent is already active
- [ ] Unit tests: threshold logic for all 3 agents

---

### T443: Agent offer API endpoints

**Scope**: backend
**Depends**: T442
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)

**Description**: Endpoints for reading and acting on agent activation suggestions.

`GET /api/pact/suggestions`:

- Returns active `PactSuggestion` records for the company
- Includes `agent_id`, `trigger_event`, `created_at`
- Owner only

`POST /api/pact/suggestions/{id}/accept`:

- Sets `suggestion.status = accepted`
- Triggers agent activation (delegates to `activate_agent` from T423)
- Returns `{agent_id, activated: true}`

`POST /api/pact/suggestions/{id}/dismiss`:

- Sets `suggestion.status = dismissed`, `dismissed_at = now()`
- Returns `{dismissed: true}`

`GET /api/pact/suggestions/history`:

- Returns all suggestions (accepted + dismissed) for audit trail
- Owner only

**Acceptance criteria**:

- [ ] List endpoint only returns active suggestions
- [ ] Accept endpoint activates agent and marks suggestion as accepted
- [ ] Dismiss endpoint marks suggestion as dismissed with timestamp
- [ ] History endpoint includes both accepted and dismissed
- [ ] Employees get 403 on all suggestion endpoints

---

### T444: Agent offer card — frontend component

**Scope**: frontend
**Depends**: T443, T428, T431
**Files**:

- `apps/web/components/pact/AgentSuggestionBanner.tsx` (new)
- `apps/web/app/(dashboard)/page.tsx` (modify)

**Description**: The moment the boss sees the first agent offer.
Per user flow 01 Step 6 and per the value critique: language must NOT
use "PACT" or "gradient" — describe outcomes only.

`AgentSuggestionBanner`:

- Shown on dashboard when `GET /api/pact/suggestions` returns active suggestions
- Displays the FIRST active suggestion only (one offer at a time)
- Layout: agent avatar + offer text + "Tell me more" / "Not now" buttons
- Offer text by agent:
  - `arbor_hr`: "You've approved {N} leave requests this week. Want Arbor HR
    to handle routine approvals for you?"
  - `arbor_payroll`: "Payroll took {N} minutes last month. Want Arbor Payroll
    to prepare it automatically next month?"
  - `arbor_compliance`: "You have {N} compliance items due this quarter.
    Want Arbor Compliance to track them for you?"
- "Tell me more" → opens `AgentOfferCard` (T428 / T431 / T436 full detail page)
- "Not now" → calls `POST /api/pact/suggestions/{id}/dismiss`
  Then hides the banner. Does NOT disable future offers.
- Dismissal lasts 7 days (client-side — re-fetch after 7 days)

**Acceptance criteria**:

- [ ] Banner appears on dashboard when active suggestion exists
- [ ] Offer text uses dynamic N count (not hardcoded)
- [ ] "Not now" dismisses via API and hides banner
- [ ] "Tell me more" navigates to agent offer detail page
- [ ] Only one suggestion shown at a time (first in list)
- [ ] Banner absent when no active suggestions

---

### T445: Trust ladder progress indicator

**Scope**: frontend
**Depends**: T402, T423, T443
**Files**:

- `apps/web/components/pact/TrustLadder.tsx` (new)
- `apps/web/app/(dashboard)/arbor-agents/page.tsx` (new, stub page)

**Description**: Visual indicator of the boss's position on the agent trust
ladder. Shown on the "Arbor Agents" section of the dashboard and on a
dedicated page. Does NOT use PACT vocabulary — shows outcomes.

`TrustLadder` component:

- 5-step progress visualization (not a numbered list, but a milestone bar):
  1. "Arbor is watching" (complete on Day 1 — org chart confirmed)
  2. "First useful insight" (complete after first morning briefing delivered)
  3. "First agent offer" (complete when first suggestion is created)
  4. "First agent active" (complete when any agent is activated)
  5. "Your AI HR team" (complete when all 3 agents active)
- Each step has: icon, label, completion check mark
- Current step is highlighted
- Clicking a completed step shows timestamp ("Completed {date}")
- Clicking a future step shows "What happens here" tooltip

Data source: derive from `GET /api/pact/status` (T412) + suggestions list.

`/arbor-agents` page (stub):

- Shows `TrustLadder` at top
- Below: active agents list (empty if none active yet)
- "Learn about Arbor's agents" accordion with plain-language descriptions

**Acceptance criteria**:

- [ ] Steps 1-2 complete by Day 1 after setup wizard
- [ ] Step 3 completes when first suggestion created
- [ ] Step 4 completes when first agent activated via API
- [ ] Step 5 completes when all 3 agents active
- [ ] Timestamps shown on completed steps
- [ ] "What happens here" tooltip on future steps

---

## M68: Observation Pipeline Wiring

### T446: Client-side observation event emission

**Scope**: frontend
**Depends**: T442
**Files**:

- `apps/web/lib/observations.ts` (new)
- `apps/web/app/(dashboard)/leave/page.tsx` (modify)
- `apps/web/app/(dashboard)/payroll/page.tsx` (modify)
- `apps/web/app/(dashboard)/compliance/page.tsx` (modify)

**Description**: Wire client-side observation events to the backend. Per
project memory, the observation pipeline is currently un-wired (client side
sends nothing to server). This is the fix.

`observations.ts`:

```ts
export async function recordObservation(
  eventType: string,
  data?: Record<string, unknown>,
): Promise<void>;
```

- `POST /api/pact/observations` with `{event_type, data}`
- Fire-and-forget: catches errors silently (observation failure MUST NOT
  break the user workflow)
- Called after successful user actions, not before

Events to wire:

- Leave approve/reject → `leave_approved_manually` with `{leave_id}`
- Payroll run completed (after boss approves payroll summary) →
  `payroll_run_completed` with `{payroll_run_id}`
- Compliance item viewed (>5 seconds on page) → `compliance_item_viewed`
- Advisory question asked → `advisory_question_asked` (already fires in
  shadow agent? — verify and wire if not)

**Acceptance criteria**:

- [ ] `recordObservation` POST fires after leave approve action
- [ ] `recordObservation` POST fires after payroll run approval
- [ ] `recordObservation` POST fires after 5s on compliance page
- [ ] Observation failure does not interrupt user workflow (try/catch)
- [ ] Unit test: `recordObservation` calls correct endpoint with correct body

---

### T447: Observation API endpoint

**Scope**: backend
**Depends**: T442
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)

**Description**: Backend endpoint that receives client-side observations.

`POST /api/pact/observations`:

- Body: `{event_type: str, data: dict nullable}`
- Calls `record_observation(company_id, event_type, data)` from T442
- Then calls `check_suggestion_triggers(company_id)` — creates suggestions
  if thresholds newly met
- Returns `{recorded: true}` always (no error details exposed)
- Owner or hr_manager only

Rate limiting: max 60 observation events per company per hour to prevent
abuse. Uses existing in-memory rate limiter.

**Acceptance criteria**:

- [ ] POST records observation in database
- [ ] POST triggers suggestion check after recording
- [ ] Returns 200 even if observation fails internally (fail-open for UX)
- [ ] Rate limit: 61st event in 1 hour returns 429
- [ ] Unit test: recording 3 leave observations triggers HR suggestion

---

### T448: Observation backfill from existing action logs

**Scope**: backend
**Depends**: T447
**Files**:

- `src/hr_advisory/pact/suggestions.py` (extend)

**Description**: New companies that already have data should not have to wait
for fresh observations. On company PACT enablement, backfill observations from
existing leave/payroll/compliance records.

`backfill_observations(company_id: int) -> int`:

- Called once when `pact_enabled` is set to True (in T412 endpoint)
- Counts: approved leave applications in last 90 days → emit synthetic
  `leave_approved_manually` events (up to 10, to not over-inflate)
- Counts: completed payroll runs in last 6 months → emit synthetic
  `payroll_run_completed` events (up to 3)
- Counts: compliance reports viewed (from audit log if available) → emit
  synthetic `compliance_item_viewed` events (up to 5)
- Does NOT overwrite existing observations
- Returns total number of synthetic events created

This means that on Day 1 after enabling PACT, the boss may already see an
agent suggestion if they have a history of manual leave approvals.

**Acceptance criteria**:

- [ ] Backfill called automatically on PACT enablement
- [ ] Company with 10 past leave approvals gets immediate HR agent suggestion
- [ ] Backfill is idempotent (calling twice does not double-count)
- [ ] Backfill capped at limits (10 leave, 3 payroll, 5 compliance events)
- [ ] Unit test: backfill generates correct suggestion for company with history

---

### T449: Shadow agent suggestion integration

**Scope**: backend
**Depends**: T442, T448
**Files**:

- `src/hr_advisory/shadow/nudges.py` (extend)

**Description**: The shadow agent's nudge system should surface PACT suggestions
alongside regular nudges. This connects the two systems.

Extend `generate_nudges(company_id: int, user_id: int) -> list[Nudge]`:

- Include PACT suggestions (from T442) as nudge items when:
  - Suggestion `status == active`
  - Suggestion created more than 24 hours ago (don't spam on Day 1)
- Format as a nudge:
  - `type: "agent_offer"`
  - `title: "Arbor HR can save you time"`
  - `body`: same offer text as `AgentSuggestionBanner` (T444)
  - `action_url: "/arbor-agents/{agent_id}/offer"`
- Deduplication: if suggestion already shown as banner (T444), skip in nudges
  (client-side: suppress nudge if suggestion banner is visible)

**Acceptance criteria**:

- [ ] PACT suggestion appears as nudge item after 24-hour delay
- [ ] Nudge not generated if agent already active
- [ ] Nudge not generated if suggestion dismissed within last 7 days
- [ ] Existing nudge tests still pass
- [ ] Unit test: company with active suggestion generates nudge after 24h

---

### T450: Setup completion tracking + PACT auto-enable for new companies

**Scope**: backend
**Depends**: T402, T437
**Files**:

- `src/hr_advisory/api/routers/companies.py` (extend)
- `src/hr_advisory/models/company_user.py` (extend Company model)

**Description**: Track setup wizard completion and auto-enable PACT for
new companies that complete onboarding.

Add to Company model:

- `setup_completed: Boolean default False`
- `setup_completed_at: DateTime nullable`
- `first_briefing_sent: Boolean default False`

`PATCH /api/companies/{id}` extensions:

- Allow updating `setup_completed` (owner only)
- On `setup_completed=True`: set `pact_enabled=True` automatically
  (new companies always start with PACT — existing companies need explicit
  opt-in via T412)
- On `setup_completed=True`: call `backfill_observations(company_id)` (T448)
- On `setup_completed=True`: schedule `generate_morning_briefing` for next
  08:00 SGT

**Acceptance criteria**:

- [ ] `setup_completed=True` auto-enables PACT for new companies
- [ ] `setup_completed=True` triggers observation backfill
- [ ] `setup_completed_at` timestamp recorded
- [ ] Existing companies (pre-PACT) are NOT auto-enabled (setup_completed stays False)
- [ ] Unit test: completing setup enables pact and triggers backfill
