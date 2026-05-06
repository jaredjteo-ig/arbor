# Round-3 Redteam — Raw-ID Leakage Audit

**Date**: 2026-05-06
**Scope**: every dashboard / list / detail / modal in the web app
**Trigger**: User flagged "Employee #6" / "Employee #5" in the My Appraisals tab.
We already fixed `/appraisals/my` — but the same bug class lives across many other surfaces. This round audits the rest.

## Verification accounts (live: http://136.110.51.61/)

- **Grace Koh** (HR manager) — `grace.koh@central-solutions.sg` / `Employee2026!`
- **Lily Phang** (employee) — `lily.phang@central-solutions.sg` / `Employee2026!`

## Findings (static scan, before live verification)

### A. HARD `#${id}` fallback (frontend renders raw ID when name is missing)

| #   | File                     | Line                   | Field                                              | Backend route returns name?                              |
| --- | ------------------------ | ---------------------- | -------------------------------------------------- | -------------------------------------------------------- |
| A1  | `appraisals/page.tsx`    | 910                    | `Employee #${a.employee_id}`                       | ✅ now (just patched) — fallback redundant               |
| A2  | `approvals/page.tsx`     | 378                    | `Employee #${entry.employee_id}` (recent activity) | ❌ no enrichment                                         |
| A3  | `approvals/page.tsx`     | 579                    | `Employee #${req.employee_id}` (pending requests)  | ❌ no enrichment                                         |
| A4  | `policies/[id]/page.tsx` | 607                    | `Employee #${emp.employee_id}` (employees list)    | ❌ no enrichment                                         |
| A5  | `recruitment/page.tsx`   | 3119, 4572, 4610, 4657 | `Candidate #${iv.candidate_id}` × 4                | ✅ enriched in `_enrich_interviews` — fallback redundant |
| A6  | `shifts/page.tsx`        | 308                    | `Emp #${a.employee_id}`                            | ❌ no enrichment                                         |
| A7  | `employees/page.tsx`     | 2383                   | `Employee #${assignment.employee_id}` (probation)  | ❌ no enrichment                                         |
| A8  | `projects/[id]/page.tsx` | 433                    | `#${a.employee_id}` (allocations)                  | ❌ no enrichment                                         |
| A9  | `projects/[id]/page.tsx` | 498                    | `#${ts.employee_id}` (timesheets)                  | ❌ no enrichment                                         |

### B. NO FALLBACK — always renders raw ID (worst case)

| #   | File                      | Line | Pattern                                               |
| --- | ------------------------- | ---- | ----------------------------------------------------- |
| B1  | `policies/[id]/page.tsx`  | 655  | `Employee #{ack.employee_id}` — no `\|\|`, always raw |
| B2  | `employees/[id]/page.tsx` | 3336 | `Created by #{note.created_by}` — exposes raw user_id |

### C. Renders integer as visible text (no `#` prefix but still a leak)

| #   | File               | Line | Pattern                                                              |
| --- | ------------------ | ---- | -------------------------------------------------------------------- |
| C1  | `payroll/page.tsx` | 686  | `{comp.employee_name \|\| comp.employee_id}` — falls back to integer |
| C2  | `payroll/page.tsx` | 737  | `{u.employee_name \|\| u.employee_id}` — falls back to integer       |

### D. Helper-function based (RISK: depends on employees list being populated)

| #   | File                               | Line | Pattern                         |
| --- | ---------------------------------- | ---- | ------------------------------- |
| D1  | `attendance/page.tsx`              | 479  | `employeeName(emp.employee_id)` |
| D2  | `exit-interviews/page.tsx`         | 258  | `employeeName(iv.employee_id)`  |
| D3  | `goals/page.tsx`                   | 272  | `employeeName(g.employee_id)`   |
| D4  | `training/records/page.tsx`        | 376  | `employeeName(r.employee_id)`   |
| D5  | `training/certifications/page.tsx` | 368  | `employeeName(c.employee_id)`   |

These rely on a local `employeeName()` helper plus `useEmployees()` hook. If the employees endpoint is empty or the user lacks permission, fallback rendering kicks in. To verify in Playwright.

### E. Audit-log / patch-history surfaces

| #   | File                                   | Line     | Pattern                                                                                             |
| --- | -------------------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| E1  | `admin/elements/PatchHistoryTable.tsx` | 224, 267 | `{patch.approved_by ?? "Unknown"}` — depends on whether `approved_by` is a name string or a user_id |

## Backend enrichment status (cross-checked against `src/hr_advisory/api/routers/`)

- ✅ Already enriched: `recruitment.py` (interviews, candidates, offers), `onboarding.py` (assignments), `leave.py` (applications), `appraisals.py` (just fixed), `strategy.py` (activity feed — round-2 fix)
- ❌ Not enriched (must add): `approvals.py`, `policies.py`, `projects.py`, `shifts.py`, `employees.py` (probation assignments path), `payroll.py`, employee `notes` endpoint

## Plan

1. **Live walk** as Grace + Lily — confirm which leaks are user-visible vs theoretical
2. **Backend patches** — extend the `_enrich_*` pattern (mirror leave.py / appraisals.py) for the 7 ❌ routers
3. **Frontend cleanup** — replace `#${id}` fallbacks with the now-enriched `*_name`, including B1 and B2 hardcoded leaks and C1/C2 integer fallbacks
4. **Regression pins** — add round-3 tests
5. **Re-verify live**

## Test-results pre-state

- `tests/regression/test_redteam2_polish.py` — 6/6 green (3 new pins added in round-3a covering appraisals fixes already)
- Touched-area tests (`-k appraisal or strategy or activity`): 25/25 green

## Live walk results (Playwright on prod 5ba30cd)

### As Grace Koh (HR manager)

| Page                                                | Result                                                                                                                                                                          |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/approvals` (Timesheet + Inventory)                | **Empty** — both tabs say "No pending …". Leak path not reachable.                                                                                                              |
| `/employees` (Directory + Onboarding)               | **Clean** — onboarding shows "Tanaka Hiroshi", "Lim Mei Ling", "Lily Phang" etc. Backend `_enrich_assignments` works.                                                           |
| `/shifts`                                           | **Empty** — no shifts/templates in the seeded week. Leak path not reachable.                                                                                                    |
| `/policies/3` (Employee Handbook → Acknowledgments) | 🔴 **CONFIRMED LIVE LEAK** — 28 rows showing `Employee #29` … `Employee #1`, all with `-` for email. **Screenshot**: `r3-leak-policies-acknowledgments.png`.                    |
| `/projects/1` and `/projects/2` (all tabs)          | **Empty** — both projects have 0 team members; no allocations / timesheets. Leak path not reachable.                                                                            |
| `/payroll/4` (Apr 2026 detail)                      | **Clean** — every row shows the real name (Tanaka Hiroshi, Lim Mei Ling, etc.). Integer-fallback never triggered.                                                               |
| `/recruitment?tab=interviews`                       | **Clean** — candidate names + interviewer panels resolve correctly via `_enrich_interviews`.                                                                                    |
| `/employees/2/Notes` (Lim Mei Ling)                 | **Empty** — no notes seeded. Leak path not reachable.                                                                                                                           |
| `/admin` Overview                                   | **Clean** — only metrics, no per-record IDs visible. (Did not drill into Patch History — out of scope today.)                                                                   |
| `/appraisals` → My Appraisals                       | 🔴 **PRE-DEPLOY LEAK** — shows `Employee #6 / #5 / #4` (matches the user's original screenshots; will close on this deploy because backend `/my` enrichment is staged locally). |
| `/exit-interviews`                                  | **Clean** — Rajesh Kumar resolves; "Anonymous" row is intentional. Subtitle still says "tokenised" (will close on this deploy).                                                 |
| `/goals`                                            | **Clean** — all goals show real owner names (Chen Wei, Tanaka Hiroshi, Rajesh Kumar).                                                                                           |
| `/training/records`                                 | **Clean** — Chen Wei / Rajesh Kumar / Tanaka Hiroshi resolve correctly.                                                                                                         |
| `/attendance`                                       | **Empty** in the demo — no records this month.                                                                                                                                  |

### As Lily Phang (employee)

| Page             | Result                                                                                                                                                                              |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/my-dashboard`  | **Clean** — "Welcome, Lily" + leave balances + 3 policy cards; no IDs.                                                                                                              |
| `/my-onboarding` | **Empty** — "No onboarding tasks assigned".                                                                                                                                         |
| `/my-leave`      | **Empty** — no applications submitted.                                                                                                                                              |
| `/my-payslips`   | **Clean** — April 2026 payslip card with Gross/Net only.                                                                                                                            |
| `/my-timesheets` | **Empty** — no entries.                                                                                                                                                             |
| `/appraisals`    | ⚠️ **AdminGuard blocks her completely** — but the page advertises a "My Appraisals" tab for employees. This is a separate bug (not in scope of this round) — flagged for follow-up. |

## Root-cause classification

After the live walk, the leaks split cleanly into three buckets:

1. **Confirmed user-visible leak** — `policies/[id]/Acknowledgments` (B1 + the no-fallback hardcoded `#` literal). Backend `policies.py` does not enrich; frontend has zero fallback. Both layers must be fixed.
2. **Pre-deploy leak that this turn already patches locally** — appraisals My Appraisals (A1). Closes on deploy.
3. **Defensive-only** — backend endpoints whose code paths look unsafe but whose seeded data never lights them up: approvals, projects, shifts, employee notes, payroll integer fallback. Will fix proactively because real customer data **will** trigger them; otherwise we ship the same bug class again the moment users add records.

## Round-3 scope (revised based on live results)

**Must close (live leak):**

- Backend: enrich `policies.py` acknowledged + not_acknowledged with `employee_name` + `email`
- Frontend: `policies/[id]/page.tsx` line 655 — replace hardcoded `Employee #{ack.employee_id}` with `ack.employee_name || "—"` and surface `ack.email`

**Defensive sweeps (theoretical → real once data lands):**

- Backend: `_enrich_*` helper for approvals (recent activity + pending), projects (allocations + timesheets), shifts (assignments), employee notes (`created_by → User.name`)
- Frontend: drop integer-only fallback in `payroll/page.tsx:686/737`; replace `Employee #${id}` / `Candidate #${id}` / `#${id}` literals with `name || "—"` everywhere (no information value in showing an int to an HR user)

**Permission bug (out of round-3 scope, file follow-up):**

- `appraisals/page.tsx` `AdminGuard` blocks employees from viewing their own appraisals via the My Appraisals tab.

## Closure status (post-fix)

### Code changes shipped this round

| Layer    | File                        | Change                                                                                                                                                                                                                              |
| -------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ----- |
| Backend  | `_helpers.py`               | Added shared `_resolve_employee_names` (Employee.user_id → User.name) and `_resolve_user_names` helpers                                                                                                                             |
| Backend  | `policies.py`               | `list_acknowledgments` now resolves `full_name` + `email` for both `acknowledged` and `not_acknowledged` lists via the User row (Employee has no name/email column — previous code shipped blank fields)                            |
| Backend  | `projects.py`               | `list_assignments` and `list_timesheet_entries` now return `employee_name` (timesheets also return `project_name`)                                                                                                                  |
| Backend  | `shifts.py`                 | `/schedule` now returns a flat `assignments` array (the web app expected this; backend was returning only the grid → contract bug + leak fix in one) — every assignment carries `employee_name`, `template_name`, `template_colour` |
| Backend  | `inventory.py`              | `list_item_requests` returns `employee_name` for the Approvals → Inventory Requests tab                                                                                                                                             |
| Backend  | `employees.py`              | `list_employee_notes_endpoint` returns `created_by_name` so the timeline never says "Created by #N"                                                                                                                                 |
| Frontend | `policies/[id]/page.tsx`    | Acknowledged table: dropped hardcoded `Employee #{ack.employee_id}`, added Email column, shape now uses `ack.full_name`. Pending table: fallback simplified to `"—"`                                                                |
| Frontend | `appraisals/page.tsx`       | Fallback simplified to `"—"`                                                                                                                                                                                                        |
| Frontend | `approvals/page.tsx`        | Both employee + project fallbacks simplified to `"—"`                                                                                                                                                                               |
| Frontend | `shifts/page.tsx`           | `Emp #N` → `"—"`                                                                                                                                                                                                                    |
| Frontend | `employees/page.tsx`        | Onboarding row + template fallbacks simplified                                                                                                                                                                                      |
| Frontend | `projects/[id]/page.tsx`    | Allocations + timesheets fallbacks simplified                                                                                                                                                                                       |
| Frontend | `payroll/page.tsx`          | Dropped raw-integer fallback (was rendering `comp.employee_id` as visible text)                                                                                                                                                     |
| Frontend | `recruitment/page.tsx`      | Four `#${candidate_id}` literal fallbacks → `"—"`                                                                                                                                                                                   |
| Frontend | `my-timesheets/page.tsx`    | `Project #N` → `"—"`                                                                                                                                                                                                                |
| Frontend | `employees/[id]/page.tsx`   | Notes timeline: `Created by #{created_by}` → `Created by {created_by_name                                                                                                                                                           |     | "—"}` |
| Frontend | `services/api/employees.ts` | `EmployeeNote` interface gains `created_by_name?: string`                                                                                                                                                                           |

### Test coverage added this round

`tests/regression/test_redteam3_id_leak.py` — **7 new pins**, all green:

1. `test_policy_acknowledgments_resolve_names_and_emails` — pins the live leak
2. `test_project_assignments_resolve_employee_name`
3. `test_project_timesheets_resolve_employee_and_project_name`
4. `test_shifts_schedule_returns_flat_assignments_with_names` (also pins the contract: `assignments` key must exist)
5. `test_inventory_requests_resolve_employee_name`
6. `test_employee_notes_resolve_created_by_name`
7. `test_resolve_employee_names_handles_missing_user` — pins the helper's crash-safety on orphaned `Employee.user_id`

### Test results

- Round-2 + round-3 regression suites combined: **13/13 PASSED** (2.36 s)
- Touched-area unit tests (`-k appraisal or strategy or activity or projects or shifts or inventory or employee or notes`, excluding pre-existing flake): **281 PASSED**
- Frontend `tsc --noEmit`: **clean** (no errors)

### Pre-existing failures (NOT introduced this round, confirmed via `git stash`)

These exist on a stashed clean HEAD — same set fails identically. Connection-pool teardown across event-loops, classic asyncpg/pytest-asyncio interplay. Tracked as a separate follow-up:

- `tests/integration/test_policies_api.py` — 25 tests fail with bare 404 on `/policies/?status=active`. Same on stashed HEAD. Likely a router-mount or trailing-slash redirect issue specific to the integration test client.
- `tests/integration/test_onboarding_e2e.py`, `tests/integration/test_onboarding_flow.py` — 4 tests, async-pool teardown
- `tests/adversarial/test_cpf.py`, `test_cross_domain.py`, `test_employment_act.py`, `test_tax.py`, `test_wsh.py` — 7 scattered failures, same async-loop pattern

**These are infrastructure flakes, not leaks.** They predate this round and are unaffected by the leak fixes. Recommend a dedicated infrastructure round to stabilise the test pool teardown.

### Live re-verification

Pending — requires deploy of this branch to `136.110.51.61`. The bundled deploy will close:

1. Policies acks live leak (28 rows × `Employee #N` → real names + emails)
2. Appraisals My Appraisals leak (Employee #6/#5/#4 → Lily Phang / Aisha Rahman / etc.)
3. Exit-interviews "tokenised" jargon → plain language
4. Defensive enrichments (kick in the moment a user creates a project assignment, shift, inventory request, or employee note)
