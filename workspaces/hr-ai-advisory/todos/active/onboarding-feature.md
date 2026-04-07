# Employee Onboarding Feature — Todo List

**Feature**: Structured employee onboarding with Excel template import, module/step tracking, and progress dashboards for both HR staff and employees.

**Reference**: `workspaces/ricoh-demo/LIA_Onboarding_Templates.xlsx` (12-sheet template)

---

## M22: Onboarding Data Models & API (Backend)

### T193: Onboarding data models

Create DataFlow models in `src/hr_advisory/models/company_user.py`:

- **OnboardingTemplate** — company_id, name, description, is_default, version (int, auto-increment on edit), created_by, created_at
- **OnboardingModule** — template_id, company_id, name, description, phase (orientation/compliance/benefits/probation/custom), order, estimated_duration_minutes, is_mandatory, is_role_specific, role_filter (JSON array of designations/departments, null = all roles)
- **OnboardingStep** — module_id, title, description, order, step_type (content/checklist/document_upload/policy_acknowledgment/form/approval), body_content, checklist_items (JSON), media_url, requires_completion, policy_id (optional FK to CompanyPolicy for acknowledgment steps), requires_previous_completion (bool, default false)
- **OnboardingAssignment** — employee_id, template_id, template_version (int, snapshot at assignment time), company_id, assigned_by, assigned_at, due_date, status (in_progress/completed/overdue), completed_at, completion_percentage
- **OnboardingStepProgress** — assignment_id, step_id, employee_id, status (pending/in_progress/completed/skipped), completed_at, completed_by (int, nullable — for approval steps), document_url, form_data (JSON, nullable — for form steps), notes, acknowledged_at
- **PreboardingTaskInstance** — company_id, template_id, employee_id, task_name, owner_role (hr/manager/it/office_manager), trigger, deadline_date (absolute, calculated from employee start_date), status (pending/done), completed_at, completed_by, notes

Add indexes on company_id, employee_id, status, template_id.

Dependencies: None
Files: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/models/__init__.py`

---

### T194: Onboarding API endpoints

Create `src/hr_advisory/api/routers/onboarding.py` with endpoints:

**Template & Module Management (admin):**
- `GET /onboarding/templates` — list templates for company
- `POST /onboarding/templates` — create template
- `GET /onboarding/templates/{id}` — get template with modules and steps
- `PUT /onboarding/templates/{id}` — update template
- `DELETE /onboarding/templates/{id}` — archive template
- `POST /onboarding/templates/{id}/modules` — add module to template
- `PUT /onboarding/modules/{id}` — update module
- `DELETE /onboarding/modules/{id}` — remove module
- `POST /onboarding/modules/{id}/steps` — add step to module
- `PUT /onboarding/steps/{id}` — update step
- `DELETE /onboarding/steps/{id}` — remove step

**Assignment & Tracking (admin):**
- `POST /onboarding/assign` — assign template to employee (auto on invite acceptance optional)
- `GET /onboarding/assignments` — list all assignments (filterable by status)
- `GET /onboarding/assignments/{id}` — get assignment with progress
- `GET /employees/{id}/onboarding` — get employee's onboarding progress

**Employee Self-Service:**
- `GET /onboarding/my-progress` — get current user's onboarding assignment + step statuses
- `POST /onboarding/steps/{step_id}/complete` — mark step as completed
- `POST /onboarding/steps/{step_id}/upload` — upload document for a step
- `POST /onboarding/steps/{step_id}/acknowledge` — acknowledge policy step

**Pre-boarding:**
- `GET /onboarding/preboarding/{employee_id}` — pre-boarding checklist for upcoming hire
- `PATCH /onboarding/preboarding/{task_id}` — mark pre-boarding task done

All endpoints: `dataflow_crud`, tenant isolation, role-based access.
Register in `platform.py`.

Dependencies: T193
Files: `src/hr_advisory/api/routers/onboarding.py`, `src/hr_advisory/api/platform.py`

---

### T195: Excel template import endpoint

Add `POST /onboarding/import` endpoint that:

1. Accepts .xlsx file upload (openpyxl)
2. Parses all 12 sheets from the LIA template format:
   - Sheet 1 (Company Profile) → update Company model fields
   - Sheet 2 (Org Structure) → informational, store in template metadata
   - Sheet 3 (Onboarding Modules) → create OnboardingModule records
   - Sheet 4 (Step Content) → create OnboardingStep records linked to modules
   - Sheet 5 (Role Configuration) → create role-specific module assignments
   - Sheet 6 (IT Provisioning) → create PreboardingTask records (owner=IT)
   - Sheet 7 (Policies & Compliance) → link to existing CompanyPolicy acknowledgment
   - Sheet 8 (Benefits Overview) → create content steps in Benefits module
   - Sheet 9 (Probation & Goals) → update company probation settings + create goal steps
   - Sheet 10 (Comms & Channels) → create informational step in Orientation module
   - Sheet 11 (Key Contacts) → store as step content + buddy assignment metadata
   - Sheet 12 (Pre-boarding Checklist) → create PreboardingTask records
3. Creates an OnboardingTemplate with all modules/steps
4. Returns import summary (modules created, steps created, warnings)
5. Handles partial imports gracefully (skip invalid rows with warnings)

Validation: required columns per sheet, data types, max lengths.
Add `openpyxl>=3.1.0` to pyproject.toml if not present.

Dependencies: T193, T194
Files: `src/hr_advisory/api/routers/onboarding.py`, `src/hr_advisory/services/onboarding_parser.py`

---

### T196: Auto-assign onboarding on employee registration

When an employee accepts an invitation and registers:

1. Check if company has a default OnboardingTemplate
2. If yes, create an OnboardingAssignment for the employee
3. Create OnboardingStepProgress records (status=pending) for each step
4. If role-specific modules exist (from Sheet 5), filter by employee's designation/role
5. If the template has PreboardingTasks, create tracking records

Modify `POST /auth/register-employee` or the invitation acceptance flow.

Dependencies: T193, T194
Files: `src/hr_advisory/api/routers/auth.py` or `employees.py`

---

## M23: Onboarding Frontend — Admin (React)

### T197: Employees page — separate Directory and Onboarding tabs

Restructure `/apps/web/src/app/(dashboard)/employees/page.tsx`:

- Add tab navigation: **Directory** | **Onboarding** | **Invitations**
- Directory tab: current employee roster (search, filters, status badges)
- Onboarding tab: list of employees currently onboarding with:
  - Employee name, start date, assigned template
  - Progress bar (% complete)
  - Status badge (in_progress/completed/overdue)
  - Days since start
  - Click to expand → see module/step breakdown
- Invitations tab: current pending invitations section

Dependencies: T194
Files: `apps/web/src/app/(dashboard)/employees/page.tsx`

---

### T198: Onboarding template builder page

Create `/apps/web/src/app/(dashboard)/employees/onboarding/page.tsx`:

- List existing templates with module count, step count, assigned employee count
- "Create Template" button → opens builder
- "Import from Excel" button → file upload that calls POST /onboarding/import
- Template builder:
  - Template name and description
  - Add/reorder modules (drag or arrows)
  - Per module: add/reorder steps with type selection (content, checklist, document upload, policy acknowledgment)
  - Step editor: title, body content (rich text), checklist items, required flag
  - Set as default template toggle
  - Save/publish

Dependencies: T194, T195
Files: `apps/web/src/app/(dashboard)/employees/onboarding/page.tsx`, `apps/web/src/services/api/onboarding.ts`

---

### T199: Onboarding API service (frontend)

Create `/apps/web/src/services/api/onboarding.ts`:

Types: OnboardingTemplate, OnboardingModule, OnboardingStep, OnboardingAssignment, OnboardingStepProgress, PreboardingTask, ImportResult

Methods:
- `listTemplates()`, `getTemplate(id)`, `createTemplate(data)`, `updateTemplate(id, data)`
- `addModule(templateId, data)`, `updateModule(id, data)`, `deleteModule(id)`
- `addStep(moduleId, data)`, `updateStep(id, data)`, `deleteStep(id)`
- `importTemplate(file)` — FormData upload
- `assignTemplate(employeeId, templateId)`
- `listAssignments(filters)`, `getAssignment(id)`
- `getEmployeeOnboarding(employeeId)`
- `getMyProgress()` — self-service
- `completeStep(stepId)`, `uploadStepDocument(stepId, file)`, `acknowledgeStep(stepId)`

Export from `services/api/index.ts`.

Dependencies: T194
Files: `apps/web/src/services/api/onboarding.ts`, `apps/web/src/services/api/index.ts`

---

### T200: Admin onboarding detail view

When admin clicks an employee's onboarding from the Onboarding tab:

- Show employee info card (name, role, department, start date)
- Module-by-module progress with expand/collapse:
  - Module name, phase, estimated duration
  - Steps within module: title, type icon, status badge (pending/completed/skipped)
  - Completion timestamp for done steps
  - Document download link for upload steps
- Overall progress bar + percentage
- Actions: reassign template, mark steps as skipped, add notes
- Pre-boarding checklist section (for HR: what to prepare before Day 1)

Dependencies: T197, T199
Files: `apps/web/src/app/(dashboard)/employees/page.tsx` (or sub-component)

---

## M24: Onboarding Frontend — Employee Self-Service

### T201: My Onboarding page

Create `/apps/web/src/app/(dashboard)/my-onboarding/page.tsx`:

- Overall progress card: "X of Y steps completed" with progress bar
- Module cards in order, each showing:
  - Module name, phase badge, estimated duration
  - Steps as a checklist:
    - Content steps: "Read" button → shows body content in modal, then mark as read
    - Checklist steps: interactive checkboxes, all must be checked to complete
    - Document upload steps: file picker + upload button, shows uploaded file name
    - Policy acknowledgment: link to policy + "I acknowledge" button
    - Approval steps: "Pending manager approval" status
  - Module completion badge when all steps done
- Celebration state when 100% complete

Dependencies: T199
Files: `apps/web/src/app/(dashboard)/my-onboarding/page.tsx`

---

### T202: Add My Onboarding to employee navigation

Add "My Onboarding" nav item to the employee sidebar in NavigationSidebar.tsx:
- Show only when employee has an active onboarding assignment
- Badge with "X remaining" count
- Position after "My Dashboard" and before "My Profile"

Also add onboarding progress card to `/my-dashboard`:
- "Complete Your Onboarding" card with progress bar and "Continue" button
- Show only when onboarding is in progress (not completed)

Dependencies: T201, T199
Files: `apps/web/src/components/shell/NavigationSidebar.tsx`, `apps/web/src/app/(dashboard)/my-dashboard/page.tsx`

---

### T203: Onboarding step completion modals

Create reusable modal components for each step type:

- **ContentStepModal**: shows heading, body content (markdown/HTML), optional media, "Mark as Read" button
- **ChecklistStepModal**: shows checklist items as interactive checkboxes, "Complete" enabled when all checked
- **DocumentUploadModal**: file picker, upload progress, preview of uploaded file, "Submit" button
- **PolicyAckModal**: loads policy content (from existing policies system), "I have read and acknowledge" checkbox + submit

All modals call the onboarding API to update step progress.

Dependencies: T199, T201
Files: `apps/web/src/components/onboarding/` (new directory for these components)

---

## M25: Integration & Polish

### T204: Seed default onboarding template on company creation

When a new company is created, seed a basic Singapore onboarding template:

**Module 1: Welcome & Orientation** (3 steps)
- Welcome message (content)
- Company overview (content)
- Organisation structure (content)

**Module 2: Employment Documents** (4 steps)
- Employment contract review (document upload)
- NRIC/FIN copy (document upload)
- Bank account details (form — links to employee profile)
- Emergency contact form (form — links to employee profile)

**Module 3: Policies & Compliance** (3 steps)
- Employee handbook (policy acknowledgment — links to existing policies)
- Leave policy (policy acknowledgment)
- Code of conduct (policy acknowledgment)

**Module 4: Probation & Goals** (2 steps)
- Probation timeline (content — uses company's probation_months)
- 30-60-90 day goals (checklist)

Add to `src/hr_advisory/services/company_seeding.py`.

Dependencies: T193, T194
Files: `src/hr_advisory/services/company_seeding.py`

---

### T205: Onboarding notifications and nudges

Integrate onboarding with existing systems:

1. **Shadow agent nudges** (`shadow/nudges.py`): "Employee X has 3 overdue onboarding steps" for HR managers
2. **Shadow briefing** (`shadow/briefing.py`): include onboarding stats in morning briefing (X employees onboarding, Y overdue)
3. **Employee nudges**: "You have 5 onboarding steps remaining — complete by [date]"
4. **Alert on completion**: notify HR when an employee completes 100% onboarding

Dependencies: T194, T201
Files: `src/hr_advisory/shadow/nudges.py`, `src/hr_advisory/shadow/briefing.py`

---

### T206: Pre-boarding checklist for HR

When an employee is invited but hasn't started yet, show a pre-boarding checklist on the Onboarding tab:

- Tasks from PreboardingTask model (Sheet 12 of Excel)
- Timeline: "Day -14: Send offer letter", "Day -7: Send welcome email", etc.
- Owner assignment (HR, Manager, IT)
- Checkbox completion tracking
- Auto-calculated deadlines based on employee start date

Dependencies: T194, T197
Files: `apps/web/src/app/(dashboard)/employees/page.tsx`

---

### T207: Onboarding reporting

Add onboarding metrics to the reports page:

- Average onboarding completion time
- Completion rate by module
- Overdue step count by department
- Employee onboarding status breakdown (in_progress/completed/overdue)

Dependencies: T194
Files: `src/hr_advisory/api/routers/reports.py`, `apps/web/src/app/(dashboard)/reports/page.tsx`

---

### T208: Red team onboarding feature

Full red team validation:
- Test Excel import with valid/invalid/partial data
- Test employee self-service flow end-to-end
- Test role-based access (employee sees only their onboarding, admin sees all)
- Test auto-assignment on registration
- Test progress calculation accuracy
- Verify policy acknowledgment integrates with existing system
- Security: document upload validation, tenant isolation on all endpoints

Dependencies: T193-T207
Files: Validation artifacts in `workspaces/hr-ai-advisory/04-validate/`

---

### T209: Deploy onboarding feature

Deploy to production:
- Build and deploy backend + frontend
- Verify health
- Test with demo accounts (create template, assign to employee, complete steps)

Dependencies: T208

---

### T210: Onboarding parser unit tests

Write comprehensive unit tests for `onboarding_parser.py`:

- Valid template with all 12 sheets
- Missing optional sheets (graceful skip)
- Invalid data types in cells (numbers as strings, empty required fields)
- Duplicate module names
- Empty sheets
- Oversized file (>10MB rejection)
- Non-xlsx file rejection
- Formula/macro sanitisation

Dependencies: T195
Files: `tests/unit/test_onboarding_parser.py`

---

### T211: Template clone and bulk assign endpoints

Add:
- `POST /onboarding/templates/{id}/duplicate` — clone template with all modules/steps, new name
- `POST /onboarding/assign-bulk` — assign template to multiple employee IDs at once
- `DELETE /onboarding/assignments/{id}` — cancel/revoke an assignment
- `PATCH /onboarding/templates/{id}/reorder` — batch reorder modules (accepts ordered ID list)
- `PATCH /onboarding/modules/{id}/reorder-steps` — batch reorder steps within module

Dependencies: T194
Files: `src/hr_advisory/api/routers/onboarding.py`

---

## Summary

| Milestone | Tasks | Scope |
|-----------|-------|-------|
| M22: Backend | T193-T196, T210-T211 | Models, API (30+ endpoints), Excel import, auto-assign, tests |
| M23: Admin Frontend | T197-T200 | Tabs restructure, template builder, import UI, detail view |
| M24: Employee Frontend | T201-T203 | My Onboarding page, nav integration, step modals |
| M25: Integration | T204-T209 | Default seeding, notifications, pre-boarding, reports, red team, deploy |

**Total: 19 tasks (T193-T211)**

---

## Red Team Review Notes (addressed)

- Model gaps fixed: added template versioning, role_filter on modules, policy_id on steps, completed_by on progress, form_data for form steps, PreboardingTaskInstance (not just template)
- API gaps fixed: added clone, bulk assign, cancel assignment, reorder endpoints (T211)
- Security: Excel upload must include file size limit (10MB), MIME validation, zip bomb protection. Document uploads must follow existing patterns (UUID filenames, type validation). Tenant isolation verified through assignment → template → company_id chain.
- Edge cases: template_version snapshot on assignment prevents mid-onboarding drift. requires_previous_completion flag enables sequential enforcement. Multiple assignments per employee supported (show latest active).
- Parser unit tests added as T210.
