# P4-MG — Line-manager role + team scope (2-week sprint)

**Source audit:** `04-validate/09-redteam-roles-2026-05-12.md` P1-A.

**Problem.** Rajesh Kumar has 7 direct reports in the database
(Marcus, Priya, Nguyen, Ahmad, Sato, Samuel, Chen Wei) but the
product treats him as a regular IC:

- Dashboard is identical to a no-reports employee
- `GET /api/leave/applications` returns 0 (own only, not team)
- No surfaces for team approvals, team appraisals, team engagement
- Every approval funnels through HR Manager

Workable at ~30-person scale, breaks at 500. Obayashi-class buyers
expect line-manager → HR-exception cascade.

**Approach.** Don't add a new role to the auth system — instead
**derive manager scope from `Employee.reporting_manager_id`** so
any employee with ≥ 1 direct report transparently becomes a manager.
This keeps the 3-role system (`owner`, `hr_manager`, `employee`)
intact and avoids cascade migrations.

**Estimate:** 2 weeks (10 dev-days) for FE + BE + tests + seed +
hooks into existing lifecycle dashboard.

**Bundling:** single commit per sub-item, or one bundled "P4-MG
manager role" commit at the end of the sprint. No interlocks with
P4-QW; depends on nothing.

---

## P4-MG-1 — Derive manager scope helper

- **What:** new helper `get_managed_employee_ids(current_user) -> set[int]`
  that returns the set of employee_ids reporting to the current
  user (direct only for v1; transitive can be v2).
- **Where:** `src/hr_advisory/auth/manager_scope.py` (new module).
- **Implementation sketch:**
  ```python
  def get_managed_employee_ids(current_user: dict) -> set[int]:
      """Return employee_ids whose reporting_manager_id is the
      current user's own employee_id. Empty set if current_user
      has no reports."""
      my_emp = list_records("Employee", {"user_id": current_user["id"]}, limit=1)
      if not my_emp: return set()
      my_emp_id = my_emp[0]["id"]
      reports = list_records("Employee", {"reporting_manager_id": my_emp_id})
      return {e["id"] for e in reports}
  ```
- **Acceptance:** unit test pinning Rajesh → {Marcus, Priya, Nguyen,
  Ahmad, Sato, Samuel, Chen Wei} as employee_ids.
- **Test file:** `tests/unit/test_manager_scope.py`.

---

## P4-MG-2 — Team approval endpoints (leave / claims / timesheets)

- **What:** widen the existing list endpoints so a line manager
  sees their team's pending items.
- **Where:**
  - `src/hr_advisory/api/routers/leave.py` — `GET /api/leave/applications`
  - `src/hr_advisory/api/routers/claims.py` — `GET /api/claims`
  - `src/hr_advisory/api/routers/timesheets.py` — `GET /api/timesheets`
- **Logic per endpoint:**
  - If user is `owner` or `hr_manager` → return company-wide (current
    behaviour).
  - Else → return: own records UNION records where
    `employee_id IN get_managed_employee_ids(current_user)`.
- **Approval action:** the existing
  `POST /api/leave/applications/{id}/approve` must allow a line
  manager to approve when `application.employee_id IN
get_managed_employee_ids(current_user)`. Otherwise return 403
  with body "You are not the manager of this employee."
- **Acceptance:**
  - Rajesh (line manager) `GET /api/leave/applications` returns
    own + 7 team members' applications.
  - Marcus (no reports) `GET /api/leave/applications` returns only
    own.
  - Rajesh approving Marcus's leave succeeds.
  - Rajesh approving Lily Phang's leave (not on his team) returns 403.
- **Regression tests:** integration tests in
  `tests/integration/test_manager_team_scope.py` covering:
  - Manager sees team
  - Non-manager sees own only
  - Owner/HR see all
  - Cross-team approve rejected

---

## P4-MG-3 — Team dashboard / /team page

- **What:** new page at `/team` for any user where
  `get_managed_employee_ids` is non-empty. Sidebar shows a "Team"
  entry conditionally.
- **Where:**
  - FE: `apps/web/src/app/(dashboard)/team/page.tsx` (new).
  - Sidebar: `apps/web/src/components/Sidebar.tsx` — conditional
    "Team" link, shown when `useTeamSize() > 0`.
  - BE aggregator: `GET /api/team/dashboard` returns one bundled
    response.
- **Page content (cards in priority order):**
  1. **Pending approvals card** — count of leave + claims + timesheets
     awaiting my decision, with quick-approve buttons.
  2. **On leave today** — names + leave type + return date.
  3. **Upcoming leave (next 14 days)** — for capacity planning.
  4. **Appraisals due** — direct reports with `appraisal.status ==
'pending_manager_review'`.
  5. **Team engagement snapshot** — link to the existing manager
     engagement view (`engagement_surveys.py:2050-2200` already has
     the pattern; extend it).
  6. **Team table** — name / designation / pass type / probation /
     last 1:1 / quick-link to appraisals.
- **Acceptance:**
  - Login as Rajesh → "Team" link visible in sidebar.
  - `/team` shows 7 direct reports with the 6 cards populated.
  - Login as Marcus → no "Team" link; visiting `/team` shows
    "You don't have any direct reports" empty state.
- **Regression test:** Playwright walking the page as Rajesh.

---

## P4-MG-4 — Team appraisal surface

- **What:** widen the appraisals list/detail endpoints so managers
  see their team's appraisals. Add a manager-review action.
- **Where:** `src/hr_advisory/api/routers/appraisals.py`.
- **New endpoints:**
  - `GET /api/appraisals/to-review` — appraisals where
    `subject_employee_id IN managed_ids AND status ==
'pending_manager_review'`.
  - `POST /api/appraisals/{id}/manager-review` — manager submits
    their review; transitions status to `pending_employee_ack` or
    similar.
- **Acceptance:** Rajesh sees Marcus's mid-year review in
  `/appraisals` with a "Submit manager review" CTA.
- **Regression test:** integration spec for the scope filter +
  cross-team rejection.

---

## P4-MG-5 — Team engagement view (manager scope)

- **What:** the engagement-surveys module already has a
  manager-aggregate view (`engagement_surveys.py:2050-2200` with
  HMAC pseudonyms + self-exclusion). Wire it into `/team`.
- **Where:**
  - Existing: `src/hr_advisory/api/routers/engagement_surveys.py::manager_view`.
  - New: link from `/team` dashboard + a `/team/engagement` subroute
    that renders the per-question + 6-pulse trend.
- **Constraint per `engagement-surveys.md` skill:** preserve P50
  (privacy asymmetry — manager can't re-identify their own reports'
  responses) and Z26 (self-exclusion: manager's own responses are
  not in the aggregate they see).
- **Acceptance:** Rajesh sees his team's aggregated engagement
  scores with the 6-pulse trend. Does NOT see his own response
  contributing to the average.
- **Regression test:** reuse the existing `engagement_surveys`
  manager-view test pattern; add a path-routing test from /team.

---

## Cross-cutting for P4-MG bundle

- **D&I check:** team views must not break the <5-bucket anonymity
  collapse rule from P3-5 (pay-equity). If a manager has <5 direct
  reports, the engagement aggregate should refuse to render the
  sub-question breakdown (collapse to "Insufficient data for
  privacy"). Already enforced in `engagement_surveys` — just need to
  preserve when extending.
- **Demo seed:** Rajesh's reports already exist. After P4-MG ships,
  add to seed:
  - 1 pending leave from Marcus (so Rajesh sees a real approval).
  - 1 mid-year appraisal for Priya in `pending_manager_review`.
  - 1 timesheet submission from Sato.
- **Lifecycle dashboard hook:** Strategy lifecycle page (S5/S6/S7)
  should optionally drill into "by manager" when an owner is viewing.
- **Docs:** add a section to
  `.claude/agents/project/arbor-platform-specialist.md` describing
  the manager-scope pattern so future agents reuse it.
