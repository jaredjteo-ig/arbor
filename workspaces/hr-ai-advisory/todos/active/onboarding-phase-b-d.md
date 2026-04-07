# Onboarding Completion — Full Todo List

**Reference**: `01-analysis/01-research/onboarding-gap-analysis.md`, LIA PRD, 12-sheet Excel template
**Scope**: Complete the onboarding feature from 40% → 100% of PRD coverage

---

## Phase A: Foundation Fix (Blocks Everything)

### T212: Fix seed script + re-seed all demo data

Fix the 7 CRITICAL issues in `scripts/seed_demo_data.py` (already rewritten, needs deploy + test):

- Timeout 120s, try/finally token safety, invite token extraction
- Employee profile enrichment: PATCH each employee with DOB, gender, race, nationality, NRIC, banking, address, phone, salary_monthly
- Payroll: wrapped in try/except, continues on failure
- Attendance: today only
- Role promotions: use new PATCH /admin/users/{id}/role endpoint

Deploy the seed fixes (health endpoint, role endpoint, delete invitation) and re-run the seed script. Verify:

- All 28 employees have complete profiles (department, DOB, gender, race, salary, banking)
- Grace Koh promoted to hr_manager
- Payroll runs for at least 1 month
- Leave balances populated
- At least some claims and attendance records exist

Files: `scripts/seed_demo_data.py`, `src/hr_advisory/api/platform.py`, `src/hr_advisory/api/routers/admin.py`, `src/hr_advisory/api/routers/employees.py`

---

### T213: Wire remaining 10 Excel sheets into import endpoint

Currently the import endpoint (`POST /onboarding/templates/import`) only uses Sheets 3+4 (modules/steps). The other 10 sheets are parsed but discarded.

Wire each sheet's data into the system:

**Sheet 1 (Company Profile)**: Store as template metadata (description field) — company name, mission, vision, values. Don't overwrite Company model.

**Sheet 2 (Org Structure)**: Create content step in Orientation module with department overview.

**Sheet 5 (Role Configuration)**: Store `role_filter` on modules that have `is_role_specific=true`. Store buddy assignment info in template metadata. Create role-specific modules from "Additional Modules" column.

**Sheet 6 (IT Provisioning)**: Create `PreboardingTaskInstance` template records (not per-employee yet — those are created on assignment). Store as pre-boarding tasks with `owner_role="it"`.

**Sheet 7 (Policies & Compliance)**: For each policy, look up matching `CompanyPolicy` by name/category. If found, create a `policy_acknowledgment` step linked to that policy. If not found, create a `content` step with the policy description.

**Sheet 8 (Benefits Overview)**: Create content steps in a "Benefits" module with benefit details.

**Sheet 9 (Probation & Goals)**: Store probation config (review schedule, goal templates) as template metadata. Create checklist steps for 30/60/90 goals.

**Sheet 10 (Comms & Channels)**: Create a content step in Orientation module listing communication tools and meeting cadences.

**Sheet 11 (Key Contacts)**: Store contacts as template metadata for buddy assignment. Create a content step listing key contacts.

**Sheet 12 (Pre-boarding Checklist)**: Create `PreboardingTaskInstance` template records with task_name, owner_role, trigger, deadline_relative_days.

Files: `src/hr_advisory/api/routers/onboarding.py` (import endpoint), `src/hr_advisory/services/onboarding_parser.py`

---

### T214: Auto-create pre-boarding tasks on assignment

When `POST /onboarding/assign` is called:

1. Look up PreboardingTaskInstance template records for the template
2. For each, create a per-employee instance with:
   - `deadline_date` calculated from employee's `start_date` + `deadline_relative_days`
   - `status = "pending"`
   - `employee_id` from the assignment

Also: if no template pre-boarding tasks exist, create default SG ones:

- Day -14: Send offer letter (HR)
- Day -10: Collect documents (HR)
- Day -7: Send welcome email (HR)
- Day -5: Set up workspace (Operations)
- Day -1: Verify access + equipment (IT)

Files: `src/hr_advisory/api/routers/onboarding.py`

---

### T215: Deploy + verify onboarding end-to-end

Deploy all fixes. Test the full flow on production:

1. Login as owner → go to Onboarding tab
2. Upload the filled Central Solutions Excel template
3. Verify: template created with all modules/steps from all sheets
4. Go to Directory tab → click "Onboard" on an employee
5. Select template, set due date → assign
6. Login as that employee → see My Onboarding page
7. Complete a content step (mark as read)
8. Complete a checklist step (check all items)
9. Upload a document step
10. Acknowledge a policy step
11. Verify progress bar updates
12. Login as owner → verify progress shows on Onboarding tab

Files: verification only, no code changes

---

## Phase B: Core Gaps (High Value)

### T216: Pre-boarding task UI for HR

Create a pre-boarding section in the admin onboarding view:

- When an employee has onboarding assigned but hasn't started (or is in first week):
  - Show pre-boarding checklist: task name, owner role, deadline, status
  - Checkbox to mark each task done
  - Color-coded: green (done), amber (due soon), red (overdue)
  - Timeline view: "Day -14", "Day -7", "Day -1" relative to start date

- Also show pre-boarding summary on the employee detail page

Files: `apps/web/src/app/(dashboard)/employees/page.tsx`, `apps/web/src/services/api/onboarding.ts`

---

### T217: Admin onboarding filters + export

Add filtering to the Onboarding tab assignment list:

- Filter by status: in_progress / completed / overdue / all
- Filter by department (from employee data)
- Filter by template
- Search by employee name
- Date range filter (assigned_at)

Add CSV export button:

- `GET /onboarding/assignments/export?status=&department=` returns CSV
- Columns: Employee, Department, Template, Assigned Date, Due Date, Status, Completion %, Days Since Start

Backend: add export endpoint to onboarding router
Frontend: add filter dropdowns + export button to OnboardingTab

Files: `src/hr_advisory/api/routers/onboarding.py`, `apps/web/src/app/(dashboard)/employees/page.tsx`

---

### T218: Buddy assignment from Sheet 11

When onboarding is assigned to an employee:

1. Look up buddy info from template metadata (parsed from Sheet 11)
2. Match buddy by role/department/availability
3. Store buddy assignment on the OnboardingAssignment record (add `buddy_employee_id` field)
4. Show buddy info on the employee's My Onboarding page: name, role, photo, email
5. Show buddy assignment on the admin onboarding detail view

Also: add buddy info to the welcome content step (Sheet 1 orientation module).

Files: `src/hr_advisory/models/company_user.py` (add field), `src/hr_advisory/api/routers/onboarding.py`, `apps/web/src/app/(dashboard)/my-onboarding/page.tsx`

---

## Phase C: Differentiators

### T219: Pulse survey model + endpoints

Create pulse survey system:

**Models** (in `company_user.py`):

- `PulseSurvey` — company_id, employee_id, assignment_id, survey_type (day_30/day_60), sent_at, completed_at, status
- `PulseSurveyResponse` — survey_id, question_number, question_text, score (1-5), comment

**Endpoints** (new router or add to onboarding router):

- `POST /onboarding/surveys/trigger` — admin manually triggers survey for employee
- `GET /onboarding/surveys` — list all surveys with scores
- `GET /onboarding/my-surveys` — employee sees pending surveys
- `POST /onboarding/surveys/{id}/respond` — employee submits responses
- `GET /onboarding/surveys/{id}/results` — admin sees individual results

**Default 5 questions** (NPS-style, 1-5 scale):

1. "I understand my role and responsibilities clearly" (Role Clarity)
2. "I feel welcomed and included by my team" (Team Belonging)
3. "My manager has been supportive during my onboarding" (Manager Support)
4. "I have the tools and resources I need to do my job" (Resource Availability)
5. "Overall, how would you rate your onboarding experience?" (Overall)

**Disengagement flag**: if average score < 3.5, flag and alert HR

Files: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/onboarding.py`

---

### T220: Pulse survey frontend

**Employee view** (`/my-onboarding` or `/my-surveys`):

- Card showing "Day 30 Check-in" or "Day 60 Check-in"
- 5 questions with 1-5 star/emoji rating
- Optional comment per question
- Submit button

**Admin view** (Onboarding tab):

- Survey completion status per employee
- Average score with color coding (green >4, amber 3.5-4, red <3.5)
- Drill into individual responses
- Disengagement alert banner for low scores

Files: `apps/web/src/app/(dashboard)/my-onboarding/page.tsx`, `apps/web/src/app/(dashboard)/employees/page.tsx`, `apps/web/src/services/api/onboarding.ts`

---

### T221: Milestone tracker (30/60/90 reviews)

**Backend**:

- `OnboardingMilestone` model — assignment_id, milestone_type (day_30/day_60/day_90), scheduled_date, status (pending/completed), completed_at, notes, reviewed_by
- Auto-create milestones when assignment is created (calculate dates from start_date)
- `GET /onboarding/milestones/{assignment_id}` — list milestones
- `PATCH /onboarding/milestones/{id}` — mark completed, add notes

**Frontend**:

- Employee My Onboarding: show upcoming milestones with countdown
- Admin: milestone timeline on assignment detail, "Complete Review" button with notes field

Uses Sheet 9 data for review schedule and goal templates.

Files: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/onboarding.py`, frontend pages

---

### T222: Onboarding analytics dashboard

Add onboarding metrics to `/reports` or create `/analytics/onboarding`:

- **Completion rate**: % of employees who completed onboarding by due date
- **Average time to complete**: days from assignment to 100%
- **Completion by department**: bar chart
- **Completion by module**: which modules take longest / have lowest completion
- **Overdue count**: current overdue assignments
- **Survey scores**: average pulse survey scores (if T219 built)

Backend: `GET /onboarding/analytics` endpoint aggregating from assignments
Frontend: cards + charts on the reports or analytics page

Files: `src/hr_advisory/api/routers/onboarding.py`, `apps/web/src/app/(dashboard)/reports/page.tsx`

---

## Phase D: Advanced

### T223: Conversational onboarding (chat-guided)

Integrate onboarding content into the advisory chat system:

1. When a new hire asks questions in Advisory, check if they have active onboarding
2. If yes, inject their onboarding template content (from Sheets 1-12) as context
3. The advisory can answer company-specific questions: "What's the leave policy?", "Who's my buddy?", "What should I do on Day 1?"
4. Proactive: when employee visits Advisory during onboarding, show suggested questions based on their current module

This uses the existing RAG infrastructure — the parsed sheet data becomes part of the knowledge base for that employee's company.

Files: `src/hr_advisory/api/routers/advisory.py`, `src/hr_advisory/agents/advisory_engine.py`

---

### T224: IT provisioning workflow

Use Sheet 6 data to create an IT provisioning system:

- `ITProvisioningTask` model — employee_id, tool_name, category, owner, sla_days, status, requested_at, completed_at
- Auto-create tasks when employee is assigned onboarding (based on their role + Sheet 6 mapping)
- Admin view: IT tab showing pending provisioning tasks by employee
- Status tracking: pending → in_progress → completed
- SLA alerting: flag tasks past their SLA deadline

Files: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/onboarding.py`, frontend

---

### T225: Role-specific onboarding paths

Use Sheet 5 data to auto-select modules by employee role:

- When assigning onboarding, check employee's designation/department
- Match against `role_filter` on modules (JSON array of designations)
- Only assign matching modules + universal modules (role_filter is empty)
- Additional modules from Sheet 5 "Additional Modules" column auto-added
- 30-60-90 goals from Sheet 5 auto-populated in Probation module

Files: `src/hr_advisory/api/routers/onboarding.py` (assign endpoint)

---

### T226: Auto-assign onboarding on employee registration

When an employee accepts an invitation and registers (T196 from original plan):

1. Check if company has a default OnboardingTemplate
2. If yes, auto-create OnboardingAssignment
3. Create step progress records for all applicable steps
4. Create pre-boarding task instances
5. Employee lands on My Onboarding page after first login

Files: `src/hr_advisory/api/routers/auth.py`

---

### T227: Red team + deploy complete onboarding

Full red team of the complete onboarding system:

- Upload template → verify all 12 sheets consumed
- Assign → verify pre-boarding tasks created, buddy assigned, milestones scheduled
- Employee completes all steps → verify 100% completion
- Pulse surveys at Day 30/60
- Admin views: filters, export, analytics, milestone tracking
- Security: tenant isolation, file uploads, role access

Deploy and verify on production.

Files: validation + deployment

---

## Summary

| Phase              | Tasks     | Scope                                                               |
| ------------------ | --------- | ------------------------------------------------------------------- |
| A: Foundation      | T212-T215 | Seed fix, wire 10 sheets, pre-boarding auto-create, deploy+verify   |
| B: Core            | T216-T218 | Pre-boarding UI, admin filters+export, buddy assignment             |
| C: Differentiators | T219-T222 | Pulse surveys, milestone tracker, analytics                         |
| D: Advanced        | T223-T227 | Chat onboarding, IT provisioning, role paths, auto-assign, red team |

**Total: 16 tasks (T212-T227)**
