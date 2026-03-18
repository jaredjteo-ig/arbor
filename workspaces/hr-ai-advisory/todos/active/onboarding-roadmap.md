# Onboarding Completion & Feature Enhancements Roadmap — T278-T398

**Scope**: 121 tasks across 21 milestones. Completes employee lifecycle AND delivers comprehensive HRIS modules — zero deferred.
**Baseline**: T001-T277 complete. Advisory, HRIS engine, MCP integrations all live.
**User Decisions**:

1. Single company creation endpoint (no duplication)
2. Self-registration collects personal data; post-registration admin enters HR-sensitive data
3. Leave rollover default Jan 1 (pro-rated), company-configurable
4. Employee profile must be comprehensive and industry-leading
5. No deferment except email delivery and social proof

---

## M36: Backend Hardening & Data Integrity

Fix critical bugs and data integrity issues identified by red team. Everything else depends on these.

### T278: Consolidate Company Creation to Single Endpoint

**Problem**: Two endpoints create companies — `POST /clients/` (used by frontend, seeds nothing) and `POST /profile/` (seeds only policies). This causes seeding divergence.

**Backend:**

- Consolidate into `POST /clients/` as the single company creation endpoint
- Move policy seeding from `profile.py:_seed_default_policies()` into the clients handler
- Remove or redirect `POST /profile/` company creation (keep profile update)
- Ensure `clientsApi.create()` in frontend continues working unchanged
- Update any references/tests that use the profile path

**Files**: `src/hr_advisory/api/routers/clients.py`, `src/hr_advisory/api/routers/profile.py`
**Red Team**: C2

### T279: Fix Paternity Leave Seed — 14 → 28 Days

**Problem**: `_seed_statutory_leave_types` seeds paternity leave at 14 days. CDCSA amendment effective Jan 1, 2025 doubled it to 28 days (4 weeks). Our own KB (`templates/content.py:133`) has the correct value.

**Backend:**

- Change paternity leave `entitlement_days` from `14.0` to `28.0` in `leave.py:283`
- Verify all other leave type entitlements match current legislation
- Add code comment citing CDCSA amendment date

**Files**: `src/hr_advisory/api/routers/leave.py`
**Red Team**: Value auditor critical finding

### T280: Invitation Rollback on User Creation Failure

**Problem**: `register-employee` marks invitation accepted BEFORE creating user. If user creation fails (DB timeout, etc.), invitation is permanently burned. Employee locked out.

**Backend:**

- Wrap user creation in try/except block (auth.py ~line 485-501)
- On failure: revert invitation (`accepted_at=""`, `is_active=True`)
- Re-raise the original HTTP error
- Add test: simulate user creation failure, verify invitation is reusable

**Files**: `src/hr_advisory/api/routers/auth.py`
**Red Team**: C1

### T281: Duplicate Invitation Guard

**Problem**: No check for existing active invitation or existing user when inviting. Admin clicking twice creates orphan records.

**Backend:**

- Before creating new invitation, check for:
  1. Active, unexpired invitation for same email + company → deactivate old, create new
  2. Existing user with that email already in the company → return 409 Conflict
- Return clear error messages for each case

**Files**: `src/hr_advisory/api/routers/employees.py`
**Red Team**: M2

### T282: Company Name in validate_invitation Response

**Problem**: `GET /employees/invite/{token}` returns `company_id` (integer), not company name. Frontend needs to show "You've been invited to join [Company Name]".

**Backend:**

- Look up company record by `company_id` in the validate handler
- Add `company_name` to response: `{"valid": True, "email": ..., "role": ..., "company_id": ..., "company_name": ...}`
- This endpoint is public (no auth required) — only expose name, not sensitive company data

**Files**: `src/hr_advisory/api/routers/employees.py`
**Red Team**: M1

### T283: Invitation Lifecycle Management

**Problem**: No way to cancel, revoke, resend, or list invitations.

**Backend:**

- `DELETE /employees/invite/{invitation_id}` — revoke (set is_active=False)
- `POST /employees/invite/{invitation_id}/resend` — deactivate old token, generate new one with fresh 7-day expiry
- `GET /employees/invitations` — list pending invitations for company (with status: pending/accepted/expired/revoked)
- Require owner/hr_manager role for all

**Files**: `src/hr_advisory/api/routers/employees.py`

### T284: Return Invite Token in API Response

**Problem**: Token NOT returned in invite response (security comment says intentional). Without it, admin has no way to share the link.

**Backend:**

- Modify `POST /employees/invite` to return `{"message": ..., "invite_url": "{FRONTEND_URL}/signup?token={token}", "invitation_id": ...}`
- Remove the security comment — document that token is single-use, email-locked, 7-day expiry
- Add audit log entry when token is generated (who invited, for which email, when)
- Add rate limiting: max 50 invitations per company per hour

**Files**: `src/hr_advisory/api/routers/employees.py`
**Red Team**: ADR-1, S1

### T285: CSV Import Returns Invite Tokens

**Problem**: CSV import creates invitations but returns only counts, not tokens.

**Backend:**

- Modify CSV import response to include list of `{"email": ..., "invite_url": ...}` for each created invitation
- Maintain backward compatibility with counts

**Files**: `src/hr_advisory/api/routers/employees.py` (~line 1810-1842)
**Red Team**: S3

---

## M37: Default Data Seeding

When a company is created, all HRIS modules must be immediately usable.

### T286: Unified seed_company_defaults Function

**Backend:**

- Create `seed_company_defaults(company_id: int)` function in a shared module (e.g., `src/hr_advisory/services/company_seeding.py`)
- Calls in sequence: seed_policies → seed_leave_types → seed_claim_categories → seed_attendance_settings → seed_public_holidays
- Each sub-seed is idempotent (checks for existing before creating)
- Wire into `POST /clients/` handler after company + user association
- Wrap in try/except — seeding failures should log but not fail company creation

**Files**: New `src/hr_advisory/services/company_seeding.py`, `src/hr_advisory/api/routers/clients.py`

### T287: Seed Statutory Leave Types on Company Creation

**Backend:**

- Move `_seed_statutory_leave_types()` from leave.py into `company_seeding.py`
- Call from `seed_company_defaults()`
- All 11 types: Annual (7), Sick (14), Hospitalisation (60), Maternity (112), Paternity (28), Childcare (6), Infant Care (6), Adoption (84), Shared Parental (28), Unpaid Infant Care (6), NS Reservist (0)
- Include: Compassionate (3, non-statutory but culturally expected), Marriage (1, non-statutory)
- Mark non-statutory types with `is_statutory: False` so companies know they can adjust

**Files**: `src/hr_advisory/services/company_seeding.py`, `src/hr_advisory/api/routers/leave.py`

### T288: Seed Default Claim Categories on Company Creation

**Backend:**

- Create `_seed_default_claim_categories(company_id)` in `company_seeding.py`
- Default categories:
  - Transport ($200/month cap)
  - Meals ($150/month cap)
  - Medical ($500/month cap, requires receipt)
  - Office Supplies ($100/month cap, requires receipt)
  - Entertainment ($200/month cap, requires receipt)
  - Training & Development ($500/month cap, requires receipt)
- Each with sensible defaults for monthly_limit and requires_receipt

**Files**: `src/hr_advisory/services/company_seeding.py`

### T289: Seed Attendance Settings on Company Creation

**Backend:**

- Create `_seed_attendance_settings(company_id)` in `company_seeding.py`
- Persist the existing inline defaults to DB: work_start=09:00, work_end=18:00, grace=15min, OT_threshold=30min, require_gps=False, require_photo=False
- Verify AttendanceSettings DataFlow model supports this

**Files**: `src/hr_advisory/services/company_seeding.py`

### T290: Seed Public Holidays on Company Creation

**Backend:**

- Create `_seed_public_holidays(company_id, year)` in `company_seeding.py`
- Primary: fetch from data.gov.sg API (existing adapter in `data_gov_sg.py`)
- Fallback: hardcoded 2026 Singapore gazetted holidays (11 holidays):
  - New Year's Day (Jan 1), Chinese New Year (Jan 29-30), Hari Raya Puasa (Mar 30), Good Friday (Apr 3), Labour Day (May 1), Vesak Day (May 12), Hari Raya Haji (Jun 7), National Day (Aug 9), Deepavali (Oct 20), Christmas (Dec 25)
- Store as PublicHoliday records with `company_id=0` (national) and `is_gazetted=True`
- Include substitute holidays for weekend-falling holidays

**Files**: `src/hr_advisory/services/company_seeding.py`

---

## M38: Leave Entitlement Engine

Make leave balances accurate, gender-aware, service-aware, and self-renewing.

### T291: Lazy LeaveBalance Creation from LeaveTypeConfig

**Problem**: Only 2 of 11 leave types get balance records on registration. Nine types have zero balance.

**Backend:**

- When employee views leave balances or applies for leave, check if LeaveBalance exists for each LeaveTypeConfig
- If not: auto-create based on LeaveTypeConfig, respecting `applicable_gender` and `min_service_months`
- Helper: `ensure_leave_balances(employee_id, company_id)` — call from leave list endpoint and leave application endpoint
- Returns all balances, creating missing ones on demand

**Files**: `src/hr_advisory/api/routers/leave.py`
**Red Team**: M3

### T292: Gender-Aware and Service-Month-Aware Balance Creation

**Backend:**

- When creating LeaveBalance, check:
  - `applicable_gender`: skip maternity for male, skip paternity for female
  - `min_service_months`: if employee has < required months, set entitlement to 0 with note "Available after X months"
- Sick leave progressive: 3 months=5 days, 4=8, 5=11, 6+=14 (per EA)
- Use `employee.start_date` and `employee.gender` to determine eligibility

**Files**: `src/hr_advisory/api/routers/leave.py`
**Red Team**: M4

### T293: Register-Employee Uses LeaveTypeConfig

**Problem**: auth.py hardcodes Annual=7, Sick=14. Should use seeded LeaveTypeConfig.

**Backend:**

- Remove hardcoded leave balance creation from `register-employee` (auth.py ~line 554-587)
- Instead: call `ensure_leave_balances(employee_id, company_id)` after employee creation
- This ensures balances match the company's configured types, not hardcoded values
- Depends on T287 (leave types seeded on company creation)

**Files**: `src/hr_advisory/api/routers/auth.py`

### T294: Leave Year Rollover

**Backend:**

- Add `leave_year_start` field to Company model (default: "01-01", format "MM-DD")
- Create `rollover_leave_balances(company_id, year)` service function:
  - For each employee in company, for each leave type:
  - Calculate new year's entitlement (based on service years for annual leave)
  - Handle carry-forward: configurable per leave type (default: no carry-forward for annual, zero for all others)
  - Pro-rate for mid-year joiners (entitlement × remaining_months / 12)
- Expose via `POST /leave/rollover` (admin action) — not automatic cron for MVP
- Admin can trigger at year start, system shows "rollover pending" indicator

**Files**: `src/hr_advisory/api/routers/leave.py`, `src/hr_advisory/models/company_user.py`

### T295: Annual Leave Service-Year Progression

**Backend:**

- Implement EA schedule: Year 1=7 days, Year 2=8, Year 3=9, ... Year 8+=14
- `calculate_annual_leave_entitlement(start_date, as_of_date)` — already exists in `calculator.py:47-51`
- Wire into rollover function and lazy balance creation
- When calculating: use `employee.start_date` to determine completed years of service

**Files**: `src/hr_advisory/api/routers/leave.py`, `src/hr_advisory/services/leave_engine.py`

### T296: Hospitalisation Inclusive of Sick Leave

**Problem**: Employee seeing "14 sick + 60 hospitalisation" thinks they have 74 days. Actual entitlement is 60 days inclusive of outpatient.

**Backend:**

- Add `inclusive_of` field to LeaveTypeConfig: `hospitalisation.inclusive_of = "sick"`
- When displaying balances: annotate hospitalisation with "(inclusive of outpatient sick leave)"
- When approving hospitalisation leave: deduct from combined pool, not separate
- Update My Leave frontend to show the relationship clearly

**Files**: `src/hr_advisory/api/routers/leave.py`, `src/hr_advisory/models/company_user.py`

### T297: Pro-Rated Leave for Mid-Year Joiners

**Backend:**

- When employee joins mid-year, calculate: `entitlement × (remaining_months / 12)`
- Round up to nearest 0.5 day (standard SG practice)
- Apply during initial balance creation and year rollover
- Store `is_prorated: bool` and `prorated_from_date` on LeaveBalance for audit

**Files**: `src/hr_advisory/api/routers/leave.py`

---

## M39: Employee Profile — Comprehensive Fields

Employee profiles must be comprehensive, covering all standard HRIS fields and adding advanced features.

### T298: Employee Model Extensions

Add missing fields for comprehensive employee profiles.

**Backend — Add to Employee model:**

- Personal: `religion` (enum: buddhist/christian/hindu/islam/sikh/taoist/none/other — affects SHG), `phone` (string), `alias` (string, display name), `photo_url` (string), `nationality` (string, separate from immigration_status)
- Employment: `salary_type` (enum: monthly/daily/hourly), `hourly_rate` (float, for hourly workers), `daily_rate` (float, for daily-rated), `payment_method` (enum: giro/fast/cheque/cash), `payment_frequency` (enum: monthly/bi_weekly/weekly), `overtime_eligible` (bool, default True for Part IV EA employees), `working_hours_type` (enum: fixed/shift/flexible)
- Bank: `branch_code` (string)
- Tax: `iras_auto_inclusion` (bool, default True), `tax_reference` (string)
- Tags: `tags` (JSON array of strings, for admin grouping)

**Migration**: DataFlow schema update for new columns

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/employees.py`

### T299: Emergency Contact Model & API

**Backend:**

- Create `EmergencyContact` DataFlow model:
  - employee_id, company_id, name, phone, relationship (enum: spouse/parent/sibling/child/friend/other), is_primary (bool)
- API endpoints:
  - `GET /employees/{id}/emergency-contacts`
  - `POST /employees/{id}/emergency-contacts`
  - `PUT /employees/{id}/emergency-contacts/{contact_id}`
  - `DELETE /employees/{id}/emergency-contacts/{contact_id}`
- Allow employee self-service (own contacts only)
- PDPA audit on access

**Files**: `src/hr_advisory/models/company_user.py`, new router or extend `employees.py`

### T300: Family Members Model & API

**Problem**: Leave eligibility (maternity, paternity, childcare) requires child details. Need to track spouse and children.

**Backend:**

- Create `FamilyMember` DataFlow model:
  - employee_id, company_id, name, relationship (spouse/child/parent), date_of_birth, gender, nric_fin (encrypted), citizenship_status
- API endpoints (same pattern as emergency contacts)
- Used by: childcare leave eligibility (child under 7), paternity (child is citizen), maternity (child is citizen)
- Validate leave applications against family member records
- PDPA audit on access

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/employees.py`

### T301: Employee Document Management

**Backend:**

- Create `EmployeeDocument` DataFlow model:
  - employee_id, company_id, document_type (enum: nric/work_pass/contract/cert/medical/other), file_name, file_url, uploaded_by, upload_date, expiry_date, notification_days_before (int, default 30), notes
- API endpoints:
  - `GET /employees/{id}/documents`
  - `POST /employees/{id}/documents` (file upload)
  - `PUT /employees/{id}/documents/{doc_id}` (update metadata)
  - `DELETE /employees/{id}/documents/{doc_id}`
- Document expiry tracking: query for documents expiring within N days
- `GET /documents/expiring?days=30` — admin view of all expiring documents across company
- Advanced: expiry alerts on any document type, not just work passes

**Files**: `src/hr_advisory/models/company_user.py`, new router `src/hr_advisory/api/routers/documents.py`

### T302: Employee Notes & Memos

**Backend:**

- Create `EmployeeNote` DataFlow model:
  - employee_id, company_id, note_type (enum: general/performance/disciplinary/confidential), content (text), created_by (user_id), is_confidential (bool)
- API endpoints:
  - `GET /employees/{id}/notes` (filtered by user permission — confidential only for owner/hr_manager)
  - `POST /employees/{id}/notes`
  - `PUT /employees/{id}/notes/{note_id}` (only by creator)
  - `DELETE /employees/{id}/notes/{note_id}` (only by creator or owner)
- Employee cannot see notes about themselves (admin-only feature)
- PDPA audit for confidential notes

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/employees.py`

### T303: Custom Fields

**Problem**: Most HRIS platforms have fixed schemas. Arbor should let admins define their own fields.

**Backend:**

- Create `CustomFieldDefinition` DataFlow model:
  - company_id, field_name, field_label, field_type (enum: text/number/date/dropdown/checkbox), dropdown_options (JSON array), is_required (bool), display_order (int), applies_to (enum: employee/leave/claim)
- Create `CustomFieldValue` DataFlow model:
  - entity_type (employee/leave/claim), entity_id, field_definition_id, value (JSON — supports any type)
- API endpoints:
  - `GET /settings/custom-fields` — list definitions
  - `POST /settings/custom-fields` — create definition
  - `PUT /settings/custom-fields/{id}` — update definition
  - `DELETE /settings/custom-fields/{id}` — delete (only if no values exist)
  - Custom field values managed via entity endpoints (e.g., `PUT /employees/{id}` includes `custom_fields`)

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/settings.py`

### T304: Employee Timeline / Activity Log

**Problem**: No unified timeline of changes to employee records. Advanced feature.

**Backend:**

- Create `EmployeeEvent` DataFlow model:
  - employee_id, company_id, event_type (enum: created/profile_updated/salary_changed/promoted/department_changed/probation_confirmed/leave_approved/terminated/document_uploaded/note_added), description (text), changed_by (user_id), old_value (JSON), new_value (JSON), event_date
- Auto-log on: employee creation, profile updates (capture diff), salary changes, status changes, leave approval/rejection
- API: `GET /employees/{id}/timeline?limit=50&offset=0`
- Salary changes always logged with old → new for audit

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/employees.py`

### T305: Structured Singapore Address

**Problem**: Current model has single `residential_address` string. Most platforms use freetext. We can do better.

**Backend:**

- Add structured address fields to Employee: `address_block` (string), `address_street` (string), `address_unit` (string, e.g. "#05-123"), `address_building` (string), `address_postal_code` (string, 6-digit SG postal)
- Keep `residential_address` as computed/display field (concatenated)
- Validate postal code format (6 digits)
- Future: OneMap API integration for address verification

**Files**: `src/hr_advisory/models/company_user.py`

### T306: Work Pass Lifecycle Management

**Problem**: Basic platforms only have expiry reminders. We should have full lifecycle tracking.

**Backend:**

- Create `WorkPassEvent` DataFlow model:
  - employee_id, company_id, event_type (enum: applied/approved/renewed/cancelled/expired), pass_type, pass_number, effective_date, expiry_date, notes
- Auto-create event when work_pass_expiry is set or changed on Employee
- `GET /employees/work-pass-expiring?days=90` — list employees with passes expiring within N days
- `GET /employees/{id}/work-pass-history` — full pass history
- Alert integration: surface in dashboard pending actions when passes expire within 90/60/30 days

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/employees.py`

### T307: Skills & Certifications Tracking

**Backend:**

- Create `EmployeeSkill` DataFlow model:
  - employee_id, company_id, skill_name, proficiency_level (enum: basic/intermediate/advanced/expert), certification_name (optional), certification_number, certified_date, expiry_date, issuing_body
- API: CRUD on `/employees/{id}/skills`
- `GET /skills/expiring?days=90` — certifications expiring (e.g., food safety, WSH, first aid)
- `GET /skills/search?skill=first_aid` — find employees with specific skills
- Advanced: searchable skills matrix across company

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/employees.py`

### T308: Digital Onboarding Checklist

**Problem**: Traditional onboarding is just data entry. We should have task-based checklists.

**Backend:**

- Create `OnboardingTemplate` DataFlow model:
  - company_id, template_name, items (JSON array of {title, description, assigned_to: "employee"/"hr"/"it"/"manager", category: "documents"/"it_setup"/"orientation"/"policies"})
- Create `OnboardingChecklist` DataFlow model:
  - employee_id, company_id, template_id, items (JSON array with completion status), overall_status (enum: not_started/in_progress/completed), due_date
- Default template items:
  1. Submit NRIC/FIN copy (employee)
  2. Submit bank account details (employee)
  3. Sign employment contract (employee)
  4. Set up workstation (IT)
  5. Create email account (IT)
  6. Complete orientation (HR)
  7. Acknowledge company policies (employee)
  8. Emergency contact details (employee)
- API: CRUD on `/onboarding/templates`, `/employees/{id}/onboarding`
- Auto-create checklist when employee is invited

**Files**: `src/hr_advisory/models/company_user.py`, new `src/hr_advisory/api/routers/onboarding.py`

---

## M40: Employee Registration Flow

Two-phase registration: employee provides personal data, admin completes HR-sensitive data.

### T309: Self-Registration — Personal Data Collection

**Problem**: Current register-employee creates minimal employee record (user_id, company_id, employment_type, start_date). Employee has no way to fill in their profile.

**Backend:**

- Extend `POST /auth/register-employee` to accept optional personal fields:
  - name, date_of_birth, gender, race, nationality, religion, phone, nric_fin, residential address fields, bank details, emergency contacts
- Fields provided at registration are saved immediately
- Fields not provided remain empty (to be filled later via profile edit)

**Frontend (My Profile):**

- After first login, employee sees "Complete Your Profile" prompt on /my-dashboard
- Profile completion page with sections:
  1. Personal Information (name, DOB, gender, race, nationality, religion, phone, photo)
  2. Identity (NRIC/FIN — with PDPA notice)
  3. Address (structured SG address fields)
  4. Banking (bank name, account, branch code — with PDPA notice)
  5. Emergency Contacts (add 1-2 contacts)
- Progress indicator showing completion percentage
- Required vs optional fields clearly marked

**Files**: `src/hr_advisory/api/routers/auth.py`, `apps/web/src/app/(dashboard)/my-profile/page.tsx`

### T310: Post-Registration — Admin HR Data Entry

**Problem**: HR-sensitive fields (salary, department, designation) should be entered by admin, not employee.

**Backend:**

- Ensure `PUT /employees/{id}` accepts all HR-sensitive fields:
  - salary_monthly, salary_type, payment_method, payment_frequency
  - department, designation, employment_type, working_hours_type
  - probation_months, probation_end_date, overtime_eligible
  - reporting_manager_id, leave_policy_id
  - notice_period_days, tags
- Only owner/hr_manager can update these fields
- Employee can update own personal fields (name, phone, address, bank, emergency contacts) but NOT salary/department/designation

**Frontend (Admin Employee Edit):**

- Admin employee detail page: tabbed interface
  - Tab 1: Personal (read-only view of employee-provided data)
  - Tab 2: Employment (admin editable: department, designation, type, schedule, reporting manager)
  - Tab 3: Compensation (admin editable: salary, payment method, overtime eligibility)
  - Tab 4: Statutory (admin editable: CPF/SHG settings, tax, work pass details)
  - Tab 5: Documents (upload/manage)
  - Tab 6: Timeline (auto-generated activity log)
  - Tab 7: Notes (admin only)
- "Profile Incomplete" badge on employees missing critical payroll fields (salary, DOB, NRIC, bank)

**Files**: `src/hr_advisory/api/routers/employees.py`, `apps/web/src/app/(dashboard)/employees/[id]/page.tsx`

---

## M41: Employee Invite Acceptance (Frontend)

### T311: Signup Page — Invite Token Detection & Validation

**Frontend:**

- On `/signup`, read `token` from URL search params
- If token present: call `GET /employees/invite/{token}` to validate
- Loading state: skeleton while validating
- On valid: switch to invite mode (T312)
- On invalid/expired/used: show appropriate error (T314)

**Files**: `apps/web/src/app/(auth)/signup/page.tsx`, `apps/web/src/services/api/employees.ts`

### T312: Invite Acceptance UI

**Frontend:**

- When invite is valid, show:
  - Banner: "You've been invited to join [Company Name] as [Role]"
  - Email field: pre-filled from invitation, read-only
  - Name field: editable
  - Password + confirm password fields
  - Submit button: "Accept Invitation & Create Account"
- On submit: call `POST /auth/register-employee` with `{name, email, password, invitation_token}`
- On success: store JWT tokens in auth context, redirect to `/my-dashboard`

**Files**: `apps/web/src/app/(auth)/signup/page.tsx`

### T313: Hide Google SSO in Invite Mode

**Problem**: If employee clicks "Sign up with Google" during invite flow, the invitation token is not consumed. Google OAuth goes through a different registration path.

**Frontend:**

- When `token` param is present, hide the Google SSO button
- Show only the standard email/password form
- Add note: "Please use email registration to accept your invitation"

**Files**: `apps/web/src/app/(auth)/signup/page.tsx`

### T314: Invite Error States

**Frontend:**

- Invalid token: "This invitation link is not valid. Please contact your employer for a new link."
- Expired token: "This invitation has expired (links are valid for 7 days). Ask your employer to send a new invitation."
- Already used: "This invitation has already been accepted. If this was you, log in to access your account." + link to /login
- Network error: "Unable to verify invitation. Please try again."
- All error states include a "Sign up as a new user instead" link

**Files**: `apps/web/src/app/(auth)/signup/page.tsx`

### T315: Admin Employees Page — Invite Link & Pending Table

**Frontend:**

- After successful invite, show modal with:
  - "Invitation created!" message
  - Copyable invite link (with copy-to-clipboard button)
  - "Share this link with [email] via WhatsApp, email, or any channel"
- New section on employees page: "Pending Invitations" table
  - Columns: Email, Role, Sent By, Sent Date, Expires, Status, Actions
  - Actions: Copy Link, Resend, Revoke
  - Status: Pending (green), Expired (red), Accepted (grey), Revoked (grey)

**Files**: `apps/web/src/app/(dashboard)/employees/page.tsx`

---

## M42: Employee Profile Pages (Frontend)

### T316: Employee Self-Service Profile Page

**Frontend:**

- New page: `/my-profile`
- Sections (editable by employee):
  1. Photo upload + basic info (name, alias, DOB, gender)
  2. Contact (phone, email — email read-only)
  3. Identity (NRIC/FIN with PDPA consent notice, masked display: \*\*\*\*1234)
  4. Address (structured SG fields: block, street, unit, building, postal)
  5. Banking (bank name, account number masked, branch code — with PDPA notice)
  6. Emergency Contacts (add/edit/remove, max 3)
  7. Family Members (add/edit/remove — for leave eligibility)
- Profile completion progress bar
- "Required for payroll" indicators on critical fields (NRIC, bank, DOB)
- Save per-section (not whole-form submit)
- PDPA notice: "Your personal data is encrypted and accessed only for HR/payroll purposes"

**Files**: `apps/web/src/app/(dashboard)/my-profile/page.tsx`

### T317: Admin Employee Detail Page

**Frontend:**

- `/employees/[id]` — comprehensive employee view for admin
- Tabbed interface:
  1. **Overview**: Photo, name, department, designation, status badge, key metrics (tenure, leave balance summary, last payroll)
  2. **Personal**: All personal data (read view of what employee entered)
  3. **Employment**: Department, designation, type, schedule, reporting manager, probation status, confirmation
  4. **Compensation**: Salary breakdown, payment method, CPF rates, SHG, overtime settings, salary history chart
  5. **Statutory**: Immigration status, work pass details, IRAS settings, FWL category
  6. **Leave**: Leave balances per type, recent applications, calendar view
  7. **Documents**: Upload/manage documents with expiry indicators
  8. **Timeline**: Auto-generated event log with filters
  9. **Notes**: Admin-only notes with confidentiality toggle
  10. **Onboarding**: Checklist status (if still in progress)
  11. **Custom Fields**: Company-defined custom fields
  12. **Skills**: Certifications and skills with expiry tracking
- Action buttons: Edit Employment, Edit Compensation, Run Payroll, Generate Payslip, Terminate

**Files**: `apps/web/src/app/(dashboard)/employees/[id]/page.tsx`

### T318: Admin Employee Edit Forms

**Frontend:**

- Edit modals/forms for each admin-editable section:
  - Employment edit: department, designation, employment_type, working_hours_type, reporting_manager (dropdown of employees), overtime_eligible, tags
  - Compensation edit: salary_monthly, salary_type, payment_method, payment_frequency (salary changes auto-logged in timeline)
  - Statutory edit: immigration_status, work_pass details, IRAS settings
  - Probation: confirm/extend with notes
  - Terminate: end_date, reason, final salary calculation trigger
- Salary change confirmation: "Changing salary from $X to $Y. This will be logged."
- All changes recorded in EmployeeEvent timeline

**Files**: `apps/web/src/app/(dashboard)/employees/[id]/` (edit components)

### T319: Emergency Contacts & Family Members UI

**Frontend:**

- Reusable contact card component (name, phone, relationship, primary badge)
- Add/edit/remove with inline forms
- Family members: additional fields (DOB, gender, citizenship — for leave eligibility)
- "Why do we need this?" tooltips explaining leave eligibility requirements

**Files**: `apps/web/src/components/employees/`

### T320: Employee Documents UI

**Frontend:**

- Document list with type icons, upload date, expiry indicators
- Upload modal: file picker, document type dropdown, optional expiry date, notification toggle
- Expiry badges: green (>90 days), yellow (30-90 days), red (<30 days), expired
- Bulk upload support
- Download/preview documents
- Admin dashboard widget: "Documents expiring soon" (across all employees)

**Files**: `apps/web/src/app/(dashboard)/employees/[id]/documents/`, `apps/web/src/components/employees/`

### T321: Employee Timeline View

**Frontend:**

- Chronological event list with filters (all, profile, salary, leave, status)
- Each event shows: date, event type icon, description, changed by, old→new values
- Salary change events highlighted with amount difference
- Status change events (hired → probation → confirmed → resigned) shown as milestones
- Infinite scroll or paginated

**Files**: `apps/web/src/components/employees/EmployeeTimeline.tsx`

### T322: Work Pass Expiry Alerts & Calendar

**Frontend:**

- Dashboard widget: "Work Passes Expiring" card
  - Shows employees with passes expiring within 90 days
  - Color-coded: red (<30 days), yellow (30-60), green (60-90)
- Employees page: filter by "work pass expiring soon"
- Calendar view integration: work pass expiry dates on company calendar
- Notification preferences in settings

**Files**: `apps/web/src/components/dashboard/`, `apps/web/src/app/(dashboard)/employees/page.tsx`

---

## M43: Public Landing Page

### T323: Root Landing Page with ManagementShowcase

**Frontend:**

- Create `apps/web/src/app/page.tsx` (public route, no auth required)
- Use ManagementShowcase component with modifications:
  - Hero CTA: "Get Started Free" → links to `/signup` (NOT CompanySetupModal)
  - Bottom CTA: "Start Free" → links to `/signup`
- Add navigation header: Arbor logo, feature links (anchor to sections), Login button, "Get Started Free" button
- Ensure root layout does NOT wrap this page in ProtectedRoute
- Mobile responsive

**Files**: `apps/web/src/app/page.tsx`, `apps/web/src/components/management/ManagementShowcase.tsx`

### T324: Update ValuePropositionPanel for HRIS Positioning

**Problem**: Auth pages' left panel shows "AI-Powered HR Compliance" (advisory). Should reflect full HRIS.

**Frontend:**

- Update tagline: "Your Complete HR Platform for Singapore"
- Update features:
  1. "Free Payroll & CPF" — Run payroll, generate CPF files, create payslips — all free
  2. "AI Compliance Advisor" — Answers grounded in Singapore employment law with source citations
  3. "Full HR Suite" — Leave, claims, attendance, shifts, employee management — everything in one place
- Update trust signal: "Trusted by Singapore SMEs. Backed by ASME."

**Files**: `apps/web/src/app/(auth)/elements/ValuePropositionPanel.tsx`

### T325: Sidebar Navigation — Employee View

**Frontend:**

- Ensure employee role sees correct sidebar:
  - My Dashboard
  - My Profile (NEW)
  - My Leave
  - My Claims
  - My Payslips
  - My Attendance
  - Advisory (ask HR questions)
  - Help
- Admin (owner/hr_manager) continues to see full management sidebar
- My Profile link in sidebar for all roles

**Files**: `apps/web/src/components/shell/NavigationSidebar.tsx`

---

## M44: End-to-End Verification

### T326: E2E — Company Creation Seeds All Default Data

**Test:**

1. Register new user → create company via CompanySetupModal
2. Verify: 13 leave types seeded (11 statutory + compassionate + marriage)
3. Verify: 6 claim categories seeded
4. Verify: attendance settings persisted
5. Verify: public holidays loaded (11+ for 2026)
6. Verify: 4 company policies seeded
7. Verify: paternity leave = 28 days

### T327: E2E — Admin Invites Employee → Employee Registers

**Test:**

1. Admin navigates to /employees, clicks invite
2. Enters employee email and role
3. Gets copyable invite link
4. Employee opens link → /signup?token=...
5. Sees company name and role
6. Fills name, password
7. Submits → auto-logged in → lands on /my-dashboard
8. Admin sees employee in roster

### T328: E2E — Leave Balances Respect Gender & Service Months

**Test:**

1. Register male employee → verify no maternity/adoption balance
2. Register female employee → verify no paternity/shared parental balance
3. New employee (< 3 months service) → verify sick leave = 0 or noted as "not yet eligible"
4. Verify annual leave = 7 (first year)

### T329: E2E — Duplicate Invite Handling

**Test:**

1. Admin invites same email twice → old invite deactivated, new one created
2. Admin invites email of existing user in company → 409 error with clear message

### T330: E2E — Invalid/Expired Token Error States

**Test:**

1. Visit /signup?token=INVALID → error message shown
2. Visit /signup?token=EXPIRED → expiry message shown
3. Visit /signup?token=ALREADY_USED → "already accepted" + login link

### T331: E2E — Registration Failure Does Not Burn Invitation

**Test:**

1. Create invitation
2. Simulate registration failure (e.g., duplicate email)
3. Verify invitation is still active and can be used again

### T332: E2E — Full Payroll Run for New Employee

**Test:**

1. Admin creates company → invites employee
2. Employee registers → admin fills in: salary ($5000), DOB, NRIC, bank, race (Chinese)
3. Admin runs payroll for current month
4. Verify: CPF employee + employer (correct age band), SDL ($11.25 cap), CDAC (Chinese SHG)
5. Generate payslip → verify itemised breakdown
6. Employee views payslip on /my-payslips

### T333: E2E — Employee Self-Service Profile

**Test:**

1. Employee logs in → /my-dashboard shows "Complete Your Profile" prompt
2. Employee navigates to /my-profile
3. Fills: DOB, gender, NRIC, address, bank details, emergency contact
4. Saves each section
5. Profile completion shows 100%
6. Admin sees updated profile on /employees/[id]

### T334: E2E — Employee Self-Service Leave & Claims

**Test:**

1. Employee views /my-leave → sees balances for applicable leave types
2. Employee applies for annual leave → pending status
3. Admin approves → employee sees approved
4. Employee submits expense claim on /my-claims
5. Admin approves → claim marked approved

### T335: E2E — Public Landing Page

**Test:**

1. Visit root URL (not logged in) → ManagementShowcase visible
2. Click "Get Started Free" → navigates to /signup
3. Login/Sign Up buttons in header work
4. Page is mobile responsive

---

## M45: Payroll Enhancements

Implement comprehensive payroll features: pay items, pay schemes, adhoc payroll, variance reports, payslip settings.

### T336: Pay Item System

**Problem**: A full pay item system (custom allowances, deductions, bonuses) with OW/AW classification and IR8A codes is needed. We have no equivalent.

**Backend:**

- Create `PayItem` DataFlow model:
  - company_id, name, category (enum: salary/overtime/allowance/deduction/reimbursement/bonus/commission), cpf_type (enum: ow/aw/exempt), ir8a_code (string), unit_type (enum: fixed_amount/hours/days), default_amount (float), is_recurring (bool), is_taxable (bool), is_cpf_applicable (bool), display_on_shift (bool), allow_adhoc_request (bool), allow_project_costing (bool), is_archived (bool)
- API: CRUD on `/payroll/pay-items`
- Seed common SG pay items: Monthly Salary (OW), Overtime (OW), Transport Allowance (OW), Meal Allowance (OW), 13th Month Bonus (AW), Performance Bonus (AW), Commission (AW), AWS (AW)

**Frontend:**

- Pay items settings page under /settings/payroll
- Add/edit pay items with OW/AW classification guide

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/payroll.py`

### T337: Pay Scheme Templates

**Problem**: Reusable pay scheme templates (monthly/daily/hourly with OT rates, holiday groups) are needed. We have salary_type on Employee but no templates.

**Backend:**

- Create `PayScheme` DataFlow model:
  - company_id, name, pay_type (monthly/daily/hourly), currency (default SGD), base_amount (float), has_overtime (bool), ot_base_hourly_rate (float), ot_rate_normal (float, default 1.5), ot_rate_rest_day (float, default 2.0), ot_rate_holiday (float, default 2.0), ot_recording_method (enum: after_working_hours/after_fixed_hours), ot_threshold_weekly (float), ot_threshold_monthly (float), work_hours_type (enum: fixed_days/fixed_timing/shift/flexible), holiday_group_id (int), prorate_by_attendance (bool), recurring_pay_items (JSON array of {pay_item_id, amount})
- API: CRUD on `/payroll/pay-schemes`
- Employee can be assigned a pay_scheme_id

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/payroll.py`

### T338: Adhoc/Off-Cycle Payroll

**Problem**: Adhoc payroll runs (off-cycle payments for bonuses, final salary, etc.) are needed. We only support monthly runs.

**Backend:**

- Add `payroll_type` field to PayrollRun model: enum (monthly/adhoc/final_salary/bonus)
- Allow creating adhoc payroll for selected employees with custom date range
- Custom pay items per adhoc run
- Final salary calculation: pro-rated salary + leave encashment + outstanding claims - deductions

**Files**: `src/hr_advisory/api/routers/payroll.py`

### T339: Payroll Variance Report

**Problem**: Month-over-month payroll comparison is needed. We have no variance reporting.

**Backend:**

- `GET /payroll/variance?month1=2026-02&month2=2026-03` — compare two payroll runs
- Return per-employee: gross change, CPF change, net change, new/departed employees
- Flag significant variances (>10% change)

**Frontend:**

- Variance report page under /payroll/reports
- Table with employee rows, amount columns, variance highlights
- Export to Excel

**Files**: `src/hr_advisory/api/routers/payroll.py`, `apps/web/src/app/(dashboard)/payroll/reports/`

### T340: Payslip Settings & Features

**Problem**: Extensive payslip configuration is needed. Our payslips are basic.

**Backend:**

- Create `PayslipSettings` DataFlow model (per company):
  - show_employee_address (bool), show_paid_days (bool), show_leave_balance (bool), show_payslip_id (bool), combine_pay_items_by_type (bool), password_protect_pdf (bool), password_format (enum: nric_last4/custom), enable_payslip_module (bool), enable_payday_countdown (bool)
- Apply settings when generating payslips
- Scheduled publish: allow setting future publish date
- Payslip PDF generation with company letterhead/logo

**Files**: `src/hr_advisory/api/routers/payroll.py`, `src/hr_advisory/models/company_user.py`

### T341: CPF Enhanced Settings

**Problem**: Per-employee CPF control (include/exclude/full employer), AMCS, PMBS, Community Chest is needed. We auto-calculate but don't support overrides.

**Backend:**

- Add to Employee model: `cpf_status` (enum: include/exclude/full_employer), `amcs_enabled` (bool), `pmbs_enabled` (bool), `community_chest_amount` (float, 0 = opted out), `shg_override_amount` (float, optional fixed override)
- Payroll engine: respect cpf_status when calculating. Full employer = employer pays both shares. Exclude = no CPF at all.
- Add AMCS/PMBS/Community Chest as separate line items on payslip

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/engines/payroll_engine.py`

### T342: Payroll Pay Items Per Employee

**Problem**: Admin needs to add/edit/remove pay items per employee during payroll generation. Our payroll is one-shot calculation.

**Backend:**

- Add `PayrollLineItem` DataFlow model:
  - payroll_run_id, employee_id, pay_item_id, description, amount, unit_type, units, cpf_type, is_manual_override (bool)
- During payroll generation: auto-populate from pay scheme + recurring items
- Allow admin to edit/add/delete line items before confirming
- Save as draft → admin reviews → confirm → calculate statutory → finalize

**Frontend:**

- Payroll review screen: per-employee expandable rows with editable pay items
- Add pay item button, delete button, amount editing
- Statutory calculations update in real-time on confirm

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/payroll.py`

---

## M46: Leave Enhancements

### T343: Hourly/Time-Based Leave (Time Off)

**Backend:**

- Add `allow_hourly` flag to LeaveTypeConfig
- Add `hours_per_day` to LeaveTypeConfig (default 8)
- LeaveApplication: support `duration_type` (enum: full_day/half_day/hours), `hours` (float)
- Convert hours to days for balance deduction: hours / hours_per_day
- Create "Time Off" leave type in seed: hourly, no balance limit

**Files**: `src/hr_advisory/api/routers/leave.py`, `src/hr_advisory/models/company_user.py`

### T344: Leave Encashment

**Backend:**

- Add `encashment_enabled` (bool) and `encashment_max_days` (float) to LeaveTypeConfig
- `POST /leave/encash` endpoint: convert unused leave days to salary
- Calculation: daily_rate × encashed_days → creates a PayrollLineItem (AW type)
- Track encashment in LeaveBalance history

**Files**: `src/hr_advisory/api/routers/leave.py`

### T345: Carry-Forward with Expiry

**Backend:**

- Add to LeaveTypeConfig: `unused_handling` (enum: forfeit/encash/carry_forward), `carry_forward_max_days` (float), `carry_forward_expiry_months` (int, e.g., 3 = expires Mar 31)
- During year rollover: move unused days to carry-forward pool with expiry date
- When carry-forward expires: auto-forfeit and log event
- LeaveBalance: add `carried_forward_days` and `carry_forward_expiry` fields

**Files**: `src/hr_advisory/api/routers/leave.py`, `src/hr_advisory/models/company_user.py`

### T346: Off-in-Lieu for Public Holidays

**Backend:**

- When employee works on a public holiday (detected via attendance), auto-generate off-in-lieu credit
- Create "Off-in-Lieu" leave type (non-statutory, no annual entitlement, earned by working holidays)
- `POST /leave/off-in-lieu` — admin credits days to employee
- Balance tracking: earned, used, remaining

**Files**: `src/hr_advisory/api/routers/leave.py`

### T347: Leave Overflow & Earned Leave Distribution

**Backend:**

- Add `allow_overflow` (bool) to LeaveTypeConfig — allow applications exceeding current balance within yearly entitlement
- Add `entitlement_period` (enum: all_at_once/monthly/quarterly/biannual) — distribute entitlement over the year
- Monthly: 7 days annual / 12 = ~0.58 days earned per month
- Track earned vs available vs used

**Files**: `src/hr_advisory/api/routers/leave.py`

### T348: Leave Settings & Features (Frontend)

**Frontend:**

- Leave type configuration page (admin): all standard settings per leave type
- Leave calendar view: visibility scoped (company/department/self)
- Leave application: support half-day (AM/PM) and hourly options
- Proof upload (medical certificate for sick leave)
- Reason field (required/optional per leave type)
- Manager leave creation (create leave for subordinates)

**Files**: `apps/web/src/app/(dashboard)/leave/`

---

## M47: Claims Enhancements

### T349: Claims Co-Payment & Limits

**Backend:**

- Add to ClaimCategory: `co_payment_percentage` (float), `co_payment_fixed` (float), `limit_per_claim` (float), `limit_per_day` (float), `limit_per_week` (float), `limit_per_year` (float), `limit_per_financial_year` (float), `prorate_limits` (bool), `probationer_excluded` (bool), `backdated_months_limit` (int), `remark_required` (bool), `max_attachments` (int, default 5)
- Calculate reimbursement: claim_amount - co_payment
- Validate against all applicable limits before approval
- Pro-rate limits for mid-year joiners

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/claims.py`

### T350: Group Claims / Flexi-Benefits

**Backend:**

- Create `ClaimGroup` DataFlow model:
  - employee_id, company_id, name (e.g., "March Business Trip"), status (draft/submitted/approved/partially_approved), total_amount
- Claims can belong to a group (optional `claim_group_id` on Claim)
- Approve/deny individual claims within a group
- "Approve All" batch operation
- Flexi-benefits: company defines annual benefit pool, employee claims against it across categories

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/claims.py`

### T351: Benefits in Kind (BIK)

**Backend:**

- Add `is_benefit_in_kind` (bool) to ClaimCategory
- BIK claims: reimbursement amount is subject to CPF and IRAS deductions
- Auto-include BIK on IR8A Appendix 8A
- Track BIK totals per employee per year

**Files**: `src/hr_advisory/api/routers/claims.py`, `src/hr_advisory/engines/payroll_engine.py`

### T352: Claims Payroll Integration & Cut-Off

**Backend:**

- Add `claims_cutoff_day` (int, 1-31) to company payroll settings
- During payroll generation: auto-include approved claims before cut-off date
- Claims approved after cut-off: roll to next month's payroll
- Payout type per category: always_payout / never_payout / allow_no_payout

**Files**: `src/hr_advisory/api/routers/payroll.py`, `src/hr_advisory/api/routers/claims.py`

### T353: Claims Frontend Enhancements

**Frontend:**

- Multi-file upload (up to 5 attachments per claim)
- Claim group creation and management
- Foreign currency support with exchange rate
- Claims report generation (Excel/PDF with receipts)
- Claims dashboard: pending approvals, monthly spend, category breakdown
- Cut-off date indicator on claims page

**Files**: `apps/web/src/app/(dashboard)/claims/`

---

## M48: Attendance Enhancements

### T354: Lateness & Early Departure Settings

**Backend:**

- Create `LatenessSettings` DataFlow model (per company):
  - enable_lateness_deduction (bool), display_lateness (bool), grace_period_minutes (int), deduction_brackets (JSON: [{from_min: 0, to_min: 15, amount: 0}, {from_min: 16, to_min: 30, amount: 10}, ...])
- Create `EarlyDepartureSettings` model (same pattern)
- During payroll: auto-calculate lateness/early departure deductions from attendance logs
- Attendance records flagged with late/early status

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/attendance.py`

### T355: Attendance Advanced Settings

**Backend:**

- Add to AttendanceSettings: `allow_multiple_clock_per_day` (bool), `auto_clock_out_hours` (float), `min_interval_minutes` (int, prevent double-clock), `max_daily_hours` (float), `max_log_duration_hours` (float), `clock_out_rounding` (enum: off/up/down), `clock_out_rounding_interval` (int, 5/10/15/30/60 min), `mandatory_approval_before_payroll` (bool), `allow_employee_self_edit` (bool)
- Implement auto clock-out: if employee hasn't clocked out after X hours, auto-insert clock-out
- Implement clock-out rounding
- Multiple clock-in/out pairs per day

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/attendance.py`

### T356: Attendance Views & Audit

**Backend:**

- `GET /attendance/today` — real-time view: who's clocked in, who's late, who's absent
- `GET /attendance/summary?from=2026-03-01&to=2026-03-31` — aggregated hours per employee
- `GET /attendance/audit` — change audit trail (who edited what, when)
- Attendance adjustment remarks (required when admin edits a log)

**Frontend:**

- Attendance Today page: live status cards
- Attendance Summary: monthly view with totals
- Attendance log editing with mandatory remarks
- Filter by: employee, department, date range, status, approval state

**Files**: `src/hr_advisory/api/routers/attendance.py`, `apps/web/src/app/(dashboard)/attendance/`

---

## M49: Shift Enhancements

### T357: Shift Hourly Rates & Multipliers

**Backend:**

- Create `ShiftHourlyRate` DataFlow model: company_id, name, branch_id (optional), hourly_rate (float), overtime_amount (float)
- Create `ShiftMultiplier` model: company_id, name, branch_id (optional), multiplier_value (float)
- Add to ShiftTemplate: `break_type` (paid/unpaid), `break_start` / `break_end` or `break_duration`, `pay_item_id`, `instructions`, `work_type`
- OT rate configuration: per shift template, multiple rate tiers (normal/rest_day/holiday), time-of-day activation

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/shifts.py`

### T358: Shift Publishing & Planning

**Backend:**

- Shift statuses: draft → planned → published
- Publish shifts: notify assigned employees
- Recurring shifts: create repeating schedule (weekly/monthly)
- Shift pay items: additional pay items per shift (e.g., night allowance)
- Shift attendance linking: map attendance logs to specific shifts

**Frontend:**

- Weekly calendar view for shift planning
- Drag-and-drop shift assignment
- Publish button with employee notification
- Shift pay breakdown view

**Files**: `src/hr_advisory/api/routers/shifts.py`, `apps/web/src/app/(dashboard)/shifts/`

---

## M50: Appraisal Module (NEW)

### T359: Appraisal Models & API

**Backend:**

- Create `AppraisalTemplate` DataFlow model:
  - company_id, name, sections (JSON: [{title, weight, questions: [{text, type: text/rating/dropdown, filled_by: employee/reviewer, options: [...]}]}]), enable_weightage (bool), require_employee_signoff (bool), is_archived (bool)
- Create `AppraisalPeriod` model:
  - company_id, template_id, name (e.g., "2026 Annual Review"), start_date, end_date, status (draft/active/closed)
- Create `Appraisal` model:
  - period_id, employee_id, reviewer_id, template_id, company_id, status (pending/in_progress/submitted/signed_off), responses (JSON), scores (JSON), overall_score (float), reviewer_comments, employee_comments, submitted_at, signed_off_at
- API:
  - Templates: CRUD on `/appraisals/templates`
  - Periods: CRUD on `/appraisals/periods`
  - Individual: `GET/PUT /appraisals/{id}`, `POST /appraisals/{id}/submit`, `POST /appraisals/{id}/sign-off`
  - Launch period: `POST /appraisals/periods/{id}/launch` — creates Appraisal records for all employees
- Support: ad-hoc appraisal (single employee, e.g., probation confirmation) and period appraisal (batch)

**Files**: `src/hr_advisory/models/company_user.py`, new `src/hr_advisory/api/routers/appraisals.py`

### T360: Appraisal Frontend

**Frontend:**

- Template builder: drag-and-drop sections, question types, weightage
- Period management: create period, assign template, launch, monitor progress
- Employee view: fill assigned sections, submit, sign off
- Reviewer view: fill reviewer sections, view employee responses
- Admin view: track completion, view all scores, export to Excel
- Results dashboard: score distribution, department comparison

**Files**: `apps/web/src/app/(dashboard)/appraisals/`

---

## M51: Organization Structure & Admin Settings

### T361: Multi-Organization / Branch Structure

**Backend:**

- Create `Organization` DataFlow model: company_id, parent_org_id (nullable for root), name, code
- Create `Branch` DataFlow model: company_id, name, address, postal_code, geofence_radius_meters (default 100), latitude, longitude, is_archived (bool)
- Employee: add `organization_id`, `branch_id` fields
- Allow payroll per organization
- Reports filterable by org/branch

**Files**: `src/hr_advisory/models/company_user.py`

### T362: Approval Groups

**Backend:**

- Create `ApprovalGroup` DataFlow model:
  - company_id, name, type (enum: no_rules/one_tier/two_tier), rules (JSON: [{category: "leave:annual"/claim:transport"/attendance, approvers: [{type: "employee"/"group", id: int}], tier: 1/2}])
- Apply to: leave applications, claims, attendance logs
- One-tier: single approver or group approves
- Two-tier: first approver → then second approver
- Auto-route applications based on employee's approval group

**Files**: `src/hr_advisory/models/company_user.py`, new `src/hr_advisory/api/routers/approval_groups.py`

### T363: Admin Permissions (Granular)

**Backend:**

- Create `AdminPermission` DataFlow model:
  - user_id, company_id, permissions (JSON: {employees: {view: bool, create: bool, edit: bool, delete: bool}, payroll: {view, generate, publish, edit}, leave: {view, approve, create}, claims: {view, approve}, attendance: {view, approve, edit}, shifts: {view, create, publish}, appraisals: {view, create, private: bool}, reports: {view, export}, settings: {view, edit}})
- Enforce permissions on all API endpoints
- Owner role: full access (not configurable)
- HR Manager: configurable per module
- Preset permission templates (e.g., "Payroll Admin", "Leave Manager", "Read-Only")

**Files**: `src/hr_advisory/api/middleware/`, `src/hr_advisory/models/company_user.py`

### T364: Company Settings & Calendar

**Backend:**

- Extend Company model: `logo_url`, `letterhead_url`, `business_address`, `cpf_submission_number`, `financial_year_start` (MM-DD), `default_currency` (default SGD)
- Create `HolidayGroup` DataFlow model: company_id, name, holidays (JSON array of {date, name, is_gazetted})
- Multiple holiday groups: different employees can have different holiday calendars
- Calendar settings: per event type visibility (company/dept/subordinates/self) for birthday, leave, work pass expiry, etc.
- Employee directory settings: enable/disable, search scope, show email/phone

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/settings.py`

### T365: Settings & Admin Frontend

**Frontend:**

- Company settings page: logo upload, business details, financial year
- Organization structure: tree view with add/edit/archive
- Branches: map view with geofence radius
- Approval groups: visual flow builder
- Admin accounts: permission matrix with presets
- Holiday groups: calendar editor with import-by-country
- Employee directory settings: toggles
- Calendar visibility settings: per-event-type matrix

**Files**: `apps/web/src/app/(dashboard)/settings/`

---

## M52: Reports Module (22 Reports)

### T366: Payroll Reports

**Backend:**

- Monthly payroll summary (PDF/Excel): grouped by org/dept
- CPF report: monthly CPF breakdown per employee
- Banks report: payroll by banking institution
- Salary YTD report: year-to-date per employee per month
- Payroll variance: month-over-month comparison (reuse T339)
- Cost centres report: payroll by cost centre with statutory breakdowns

**Frontend:**

- Reports hub page: /payroll/reports
- Filter by: month, org, dept, employee
- Preview in-app, download as Excel/PDF

**Files**: `src/hr_advisory/api/routers/reports.py`, `apps/web/src/app/(dashboard)/payroll/reports/`

### T367: Leave, Claims, Attendance & Employee Reports

**Backend:**

- Leave report: all applications with filters (date, type, status, employee)
- Leave balance report: per-type breakdown with additions/deductions
- Claims report: with receipt summary, paid/unpaid filter
- Claims PDF: summary with receipt attachments
- Attendance report: working hours per employee for custom period
- Shift attendance report: shift breakdown with OT per day
- Employee report: all personal details with pay scheme, CPF, SHG

**Frontend:**

- Extend reports hub with tabs: Payroll, Leave, Claims, Attendance, Employees
- Consistent filter/export pattern across all reports

**Files**: `src/hr_advisory/api/routers/reports.py`, `apps/web/src/app/(dashboard)/reports/`

---

## M53: Employee Lifecycle & Cost Centres

### T368: Offboarding Flow

**Backend:**

- `POST /employees/{id}/terminate` — set termination date, reason, notes
- Auto-calculate: final salary (pro-rated), leave encashment, outstanding claims, notice period pay/deduction
- Status transitions: active → terminating (future date) → resigned (past date)
- Cancel offboarding: `POST /employees/{id}/cancel-termination`
- Re-onboarding: `POST /employees/{id}/re-onboard` — reactivate with new start date, preserve history
- Resignation document upload
- IR21 generation for foreign employees on cessation

**Frontend:**

- Termination modal: date picker, reason dropdown, notes, document upload
- Final salary preview before confirming
- Terminated employees: filtered view with re-onboard option

**Files**: `src/hr_advisory/api/routers/employees.py`, `apps/web/src/app/(dashboard)/employees/`

### T369: Salary Adjustments & Career History

**Backend:**

- `POST /employees/{id}/salary-adjustment` — new_amount, effective_date, reason (promotion/annual_review/correction), adjustment_type (fixed/percentage/decrement)
- Bulk salary adjustment: `POST /employees/bulk-salary-adjustment` — apply to multiple employees
- Auto-log in EmployeeEvent timeline
- Career history: track all position/dept/salary changes (immutable once payroll generated)
- `GET /employees/{id}/career-history` — full history

**Frontend:**

- Salary adjustment modal with current → new comparison
- Bulk adjustment page: select employees, set percentage/fixed increase
- Career history timeline on employee detail page

**Files**: `src/hr_advisory/api/routers/employees.py`

### T370: Cost Centres

**Backend:**

- Create `CostCentre` DataFlow model: company_id, name, code, is_active (bool)
- Employee: add `cost_centre_id`
- Claims: add optional `cost_centre_id` (pre-filled from employee, overridable)
- Reports: filter by cost centre (payroll, claims, employee)
- API: CRUD on `/settings/cost-centres`

**Frontend:**

- Cost centres management page
- Cost centre selection in employee edit and claims
- Reports filtered by cost centre

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/settings.py`

---

## M54: AI-Powered Advantages

Advanced features powered by our AI capabilities.

### T371: Payroll Simulation/Preview

**Problem**: Most platforms have no payroll preview. Admin must generate → review → delete if wrong. We can do better.

**Backend:**

- `POST /payroll/simulate` — run full payroll calculation without saving
- Returns same output as real payroll but with `is_simulation: true`
- Shows per-employee breakdown: gross, CPF, SDL, SHG, net, variance from last month
- "What-if" mode: simulate salary changes, new hires, terminations

**Frontend:**

- Simulation page: run preview, review results, then "Generate for Real" button
- Variance highlighting against previous month

**Files**: `src/hr_advisory/api/routers/payroll.py`

### T372: Org Chart Visualization

**Problem**: Most platforms lack org chart visualization. We can build one using reporting_manager_id.

**Frontend:**

- `/employees/org-chart` — interactive org chart
- Generated from reporting_manager_id relationships
- Click node → employee detail card
- Drag-and-drop to reassign reporting lines
- Department color coding
- Search and highlight

**Files**: `apps/web/src/app/(dashboard)/employees/org-chart/`

### T373: AI-Powered Compliance Alerts in HRIS

**Backend:**

- Shadow agent monitors HRIS data and surfaces compliance risks:
  - Work passes expiring within 90 days
  - Probation periods ending (auto-confirmation needed)
  - Annual leave not taken (EA requires employers to ensure leave is used)
  - CPF rates incorrect for age band (DOB-based verification)
  - Overtime exceeds EA Part IV limits (72 hours/month)
  - Missing statutory documents (NRIC, work pass copy)
- Daily compliance scan → surfaces alerts on admin dashboard
- Each alert: description, severity, recommended action, "Fix Now" button

**Files**: `src/hr_advisory/engines/compliance_scanner.py`

### T374: Employee Self-Service Salary History

**Problem**: Most platforms don't let employees view salary history. We can provide transparency.

**Frontend:**

- `/my-profile/salary-history` — employee sees their salary progression
- Chart: salary over time
- Table: effective date, amount, reason (promotion/review/etc.)
- Only shows data the employee role is permitted to see (configurable)

**Files**: `apps/web/src/app/(dashboard)/my-profile/`

### T375: Workflow Automation for Approvals

**Problem**: Most platforms have fixed approval flows (max 2 tiers). We can be flexible.

**Backend:**

- Add conditional routing: auto-approve leaves < 1 day, require 2-tier for > 5 days
- Auto-escalation: if approver doesn't act within X days, escalate to next tier
- Notification on approval/rejection
- Delegation: approver can delegate to another user while on leave

**Files**: `src/hr_advisory/api/routers/approval_groups.py`

---

## M55: E2E — Feature Verification

### T376: E2E — Pay Items & Pay Schemes

**Test:**

1. Create pay items (OW allowance, AW bonus)
2. Create pay scheme template with OT rates
3. Assign scheme to employee
4. Run payroll → verify pay items appear on payslip with correct OW/AW classification

### T377: E2E — Adhoc Payroll & Final Salary

**Test:**

1. Create adhoc payroll for bonus payment
2. Terminate employee → generate final salary payroll
3. Verify: pro-rated salary + leave encashment + outstanding claims - deductions

### T378: E2E — Leave Encashment & Carry-Forward

**Test:**

1. Set annual leave to carry-forward (max 5 days, expires in 3 months)
2. End of year: employee has 10 unused days
3. Rollover: 5 carried forward, 5 forfeited
4. March 31: carried days expire
5. Encash remaining if encashment enabled

### T379: E2E — Claims Co-Payment & Group Claims

**Test:**

1. Create claim category with 20% co-payment
2. Employee submits $100 claim → reimbursement = $80
3. Create group claim with 3 sub-claims
4. Admin approves 2, denies 1 → partial approval
5. Approved amount auto-included in payroll

### T380: E2E — Attendance Lateness & Deductions

**Test:**

1. Configure lateness deduction brackets
2. Employee clocks in 20 min late
3. Payroll shows deduction based on bracket

### T381: E2E — Appraisal Flow

**Test:**

1. Admin creates template with weighted sections
2. Launch period for company
3. Employee fills sections → submits
4. Reviewer fills sections → submits
5. Employee signs off
6. Admin exports scores to Excel

### T382: E2E — Org Structure & Permissions

**Test:**

1. Create sub-organization with departments
2. Create branch with geofence
3. Create approval group with 2 tiers
4. Create admin with limited permissions → verify access restricted

### T383: E2E — Offboarding & Re-Onboarding

**Test:**

1. Terminate employee with future date → status = terminating
2. Generate final salary with leave encashment
3. After termination date → status = resigned
4. Re-onboard → new start date, history preserved

### T384: E2E — Payroll Simulation

**Test:**

1. Run payroll simulation → verify no data persisted
2. Compare simulation with actual payroll → numbers match
3. Simulate with salary change → shows difference

### T385: E2E — Full Feature Coverage

**Comprehensive test:**

1. Create company → verify all seeds
2. Create org structure (2 orgs, 3 depts, 2 branches)
3. Create pay schemes (monthly, hourly, daily)
4. Invite and register 3 employees (citizen, PR, foreigner)
5. Assign pay schemes, departments, branches
6. Run payroll → verify CPF/SDL/SHG/FWL per employee type
7. Leave management: apply, approve, encash, rollover
8. Claims: single + group, with co-payment, payroll integration
9. Attendance: clock in/out, lateness deduction
10. Appraisal: create template, launch period, complete flow
11. Reports: generate all 7 report types
12. Offboard one employee → final salary → re-onboard

---

## Summary — Module Coverage

| Module                                       | Implementation  | Gap Status    |
| -------------------------------------------- | --------------- | ------------- |
| Payroll (16 settings, pay items, schemes)    | T336-T342       | COVERED       |
| Leave (17 per-type settings, hourly, encash) | T343-T348       | COVERED       |
| Claims (18 fields, co-pay, group, BIK)       | T349-T353       | COVERED       |
| Attendance (21 settings, lateness, audit)    | T354-T356       | COVERED       |
| Shift/Rostering (13 template fields, rates)  | T357-T358       | COVERED       |
| Appraisal (templates, scoring, 360)          | T359-T360       | COVERED (NEW) |
| Reports (22 reports)                         | T366-T367       | COVERED       |
| Settings/Admin (permissions, org, calendar)  | T361-T365       | COVERED       |
| Employee Lifecycle (onboard, offboard)       | T368-T369       | COVERED       |
| Cost Centres                                 | T370            | COVERED       |
| Employee Self-Service                        | T316-T322, T374 | COVERED       |
| Project Costing                              | T386-T389       | COVERED       |
| Inventory                                    | T390-T392       | COVERED       |
| ATS                                          | T393-T395       | COVERED       |

**AI-Powered Advantages:**

- AI compliance alerts (T373)
- Payroll simulation/preview (T371)
- Org chart visualization (T372)
- Employee salary history (self-service) (T374)
- Workflow automation with auto-escalation (T375)
- Custom fields (T303)
- Skills & certifications tracking (T307)
- Digital onboarding checklist (T308)
- PDPA audit trail (existing)
- Salary encryption (existing)
- AI advisory (existing)
- Shadow agent (existing)

---

## M56: Project Costing Module

Comprehensive project costing with budget tracking and profitability analysis.

### T386: Project Models & Core API

**Backend:**

- Create `Project` DataFlow model:
  - company_id, name (max 30 chars), description, start_date, end_date (nullable for ongoing), branch_id (optional), auto_assign_new_employees (bool), is_archived (bool), budget_amount (float, optional)
- Create `ProjectAssignment` model:
  - project_id, employee_id, company_id, assignment_type (enum: timesheet/attendance/allocation), role_id (optional), is_active (bool)
- Create `ProjectRole` model:
  - company_id, name, hourly_rate (float), remarks, is_archived (bool)
- Create `ProjectOverhead` model:
  - project_id, company_id, type (enum: project_based/employee_based), name, description, months (JSON array), amount_per_month (float), remarks
- API: CRUD on `/projects`, `/projects/{id}/assignments`, `/projects/roles`, `/projects/{id}/overheads`
- Bulk assign/unassign employees to projects
- Auto-assign new employees if project flag is set

**Files**: `src/hr_advisory/models/company_user.py`, new `src/hr_advisory/api/routers/projects.py`

### T387: Timesheets

**Backend:**

- Extend existing `TimesheetApproval` stub model with full fields
- Create `TimesheetEntry` DataFlow model:
  - employee_id, company_id, project_id, date, hours (float), minutes (int), rate_type (enum: normal/overtime/holiday), billable (bool), notes, created_by (enum: admin/manager/employee)
- API:
  - `POST /timesheets/entries` — create entry (admin, manager, or employee self-service)
  - `GET /timesheets?employee_id=&month=&project_id=` — list entries
  - `PUT /timesheets/entries/{id}` — edit entry
  - `DELETE /timesheets/entries/{id}` — delete entry
  - `POST /timesheets/import-attendance?month=` — import from attendance logs
- Employee self-service: `/my-timesheets` page

**Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/projects.py`

### T388: Project Allocations

**Backend:**

- Create `ProjectAllocation` DataFlow model:
  - employee_id, company_id, month (YYYY-MM), allocation_type (enum: percentage/nominal/equal), base_amount_type (enum: salary/custom), custom_base_amount (float, optional), allocations (JSON: [{project_id, percentage_or_amount}]), remarks
- Base salary calculation: gross + pay items + employer CPF + SDL (excluding items marked `exclude_from_project_costing`)
- Add `exclude_from_project_costing` (bool) to PayItem model (T336)
- API: CRUD on `/projects/allocations`

**Files**: `src/hr_advisory/api/routers/projects.py`

### T389: Project Calculations & Reports

**Backend:**

- `POST /projects/calculate?month=&year=&project_ids=` — generate cost calculations
  - Aggregate: timesheet costs (hours × role hourly rate), attendance costs (imported hours × rate), allocation costs (salary × percentage), overheads
  - Status: unapproved → approved (irreversible)
- `POST /projects/{calc_id}/approve` — approve calculation
- `GET /projects/report?month=&year=` — Excel report with filters (org/dept/employee/project)
- **Advanced**: budget vs actual comparison, project profitability (revenue - cost), variance alerts

**Frontend:**

- Projects list page: `/projects` with grid view
- Project detail: assignments, timesheets, allocations, overheads, calculations
- Employee timesheet self-service: `/my-timesheets`
- Project costing report: filterable, exportable
- **Advanced**: project profitability dashboard, budget burn-down chart

**Files**: `src/hr_advisory/api/routers/projects.py`, `apps/web/src/app/(dashboard)/projects/`

---

## M57: Inventory / Asset Management Module

Comprehensive inventory management with both quantity-based tracking AND individual asset tracking, serial numbers, depreciation, and return workflows.

### T390: Inventory Models & Core API

**Backend:**

- Create `InventoryLocation` DataFlow model:
  - company_id, name, organization_scope (enum: all/specific), organization_id (optional)
- Create `InventoryCategory` DataFlow model:
  - company_id, name, location_id, tracking_mode (enum: quantity/individual), permitted_issuers (JSON: {positions: [int], employees: [int]}), permitted_requesters (JSON: same), require_acknowledgment (bool)
- Create `InventoryItem` DataFlow model:
  - category_id, company_id, location_id, name, quantity (int, for quantity mode), serial_number (string, for individual mode — advanced feature), purchase_date (date — advanced feature), purchase_price (float — advanced feature), warranty_expiry (date — advanced feature), condition (enum: new/good/fair/damaged/disposed — advanced feature), status (enum: available/reserved/issued/pending_acknowledgment/returned/disposed), assigned_to_employee_id (optional), assigned_at (datetime), notes, photo_url (string — advanced feature)
- API: CRUD on `/inventory/locations`, `/inventory/categories`, `/inventory/items`

**Files**: `src/hr_advisory/models/company_user.py`, new `src/hr_advisory/api/routers/inventory.py`

### T391: Inventory Workflows

**Backend:**

- `POST /inventory/items/{id}/reserve` — reserve for employee (pre-allocation)
- `POST /inventory/items/{id}/issue` — issue to employee (with timestamp)
- `POST /inventory/items/{id}/acknowledge` — employee acknowledges receipt
- `POST /inventory/items/{id}/return` — return to inventory (full return workflow)
- `POST /inventory/items/{id}/dispose` — mark as disposed
- `POST /inventory/requests` — employee requests an item
- `PUT /inventory/requests/{id}/approve` — admin approves (reserve or issue)
- `PUT /inventory/requests/{id}/deny` — admin denies with reason
- Create `InventoryMovement` audit log model:
  - item_id, company_id, action (enum: created/reserved/issued/acknowledged/returned/disposed/transferred), from_employee_id, to_employee_id, performed_by, notes, timestamp
- `GET /inventory/items/{id}/history` — movement audit trail

**Files**: `src/hr_advisory/api/routers/inventory.py`

### T392: Inventory Frontend

**Frontend:**

- Inventory dashboard: `/inventory` — location → category → items drill-down
- Item detail: status badge, assignment history, photo, serial number, warranty indicator
- Issue/reserve/return modals
- Employee view: `/my-inventory` — items assigned to me, request new items, acknowledge receipts
- Request management: admin view of pending requests with approve/deny
- Expiry alerts: items with warranty expiring (dashboard widget)
- **Advanced**: asset depreciation report (purchase price, age, estimated current value), condition tracking, item photos

**Files**: `apps/web/src/app/(dashboard)/inventory/`, `apps/web/src/app/(dashboard)/my-inventory/`

---

## M58: ATS / Recruitment Module

Full-featured ATS with interview scheduling, scoring, offer letters, career page, and AI screening.

### T393: ATS Models & Core API

**Backend:**

- Create `JobListing` DataFlow model:
  - company_id, organization_id, department_id, position_title, employment_type (enum: full_time/part_time/contract/internship), location, description (rich text), requirements (rich text), salary_range_min (float, optional), salary_range_max (float, optional), is_published (bool), unique_slug (auto-generated), application_form_config (JSON: custom fields, mandatory flags), created_by, published_at, closed_at
- Create `Candidate` DataFlow model:
  - company_id, job_listing_id, name, email, phone, nric_fin (encrypted), gender, dob, race, nationality, citizenship_status, address, resume_url, cover_letter_url, application_data (JSON: answers to custom questions), source (enum: direct/linkedin/indeed/jobstreet/referral/other), stage (enum: new/screening/shortlisted/interview/offered/hired/rejected/withdrawn), overall_score (float, optional — advanced feature), rejection_reason, pdpa_consent (bool — advanced feature), pdpa_consent_date, notes
- Create `InterviewSchedule` DataFlow model (advanced feature):
  - candidate_id, company_id, interview_type (enum: phone/video/in_person/panel), scheduled_at (datetime), duration_minutes (int), location_or_link, interviewer_ids (JSON array), status (enum: scheduled/completed/cancelled/no_show), notes
- Create `InterviewFeedback` DataFlow model (advanced feature):
  - interview_id, candidate_id, interviewer_id, company_id, scores (JSON: [{criteria, score_1_to_5}]), recommendation (enum: strong_hire/hire/maybe/no_hire/strong_no_hire), comments, submitted_at
- Create `OfferLetter` DataFlow model (advanced feature):
  - candidate_id, company_id, position_title, salary, start_date, benefits_summary, template_id, status (enum: draft/sent/accepted/declined/expired), sent_at, responded_at
- API:
  - Job listings: CRUD on `/recruitment/jobs`
  - `GET /recruitment/jobs/{slug}/apply` — public application form
  - `POST /recruitment/jobs/{slug}/apply` — submit application (public, no auth)
  - Candidates: CRUD on `/recruitment/candidates`
  - `PUT /recruitment/candidates/{id}/stage` — move through pipeline
  - `POST /recruitment/candidates/{id}/onboard` — convert to employee (pre-fills from candidate data)
  - Interviews: CRUD on `/recruitment/interviews`
  - Feedback: CRUD on `/recruitment/feedback`
  - Offers: CRUD on `/recruitment/offers`

**Files**: `src/hr_advisory/models/company_user.py`, new `src/hr_advisory/api/routers/recruitment.py`

### T394: ATS Frontend

**Frontend:**

- Job listings page: `/recruitment/jobs` — list, create, edit, publish/unpublish
- Public application page: `/careers/{slug}` — no auth required, PDPA consent, resume upload
- **Career page** (advanced feature): `/careers` — public page listing all open positions with company branding
- Candidate pipeline: `/recruitment/candidates` — kanban board with drag-and-drop between stages
- Candidate detail: application data, interview schedule, feedback scores, timeline
- Interview scheduling: calendar view, send invite (ICS file), interviewer assignment
- Feedback form: scoring criteria, recommendation, comments
- Offer management: create from template, track status
- Recruitment reports: time-to-hire, pipeline conversion rates, source effectiveness
- **AI screening** (advanced feature): shadow agent scores candidates against job requirements

**Files**: `apps/web/src/app/(dashboard)/recruitment/`, `apps/web/src/app/careers/`

### T395: ATS → Employee Onboarding Bridge

**Backend:**

- When candidate reaches "Hired" stage and admin clicks "Onboard":
  - Create invitation using candidate's email
  - Pre-fill Employee record from candidate data (name, email, phone, NRIC, DOB, gender, race, nationality, address, bank details)
  - Link candidate record to employee record for audit trail
  - Mark candidate as "onboarded"
- `GET /recruitment/candidates/{id}/onboard-preview` — show which fields will pre-fill
- Preserve candidate's interview feedback and scores in employee timeline

**Files**: `src/hr_advisory/api/routers/recruitment.py`, `src/hr_advisory/api/routers/employees.py`

---

## M59: E2E — Project Costing, Inventory & ATS Verification

### T396: E2E — Project Costing Full Flow

**Test:**

1. Create project with budget, assign 3 employees (one per assignment type)
2. Timesheet employee: log 40 hours on project
3. Attendance employee: import attendance logs
4. Allocation employee: allocate 50% salary to project
5. Add project overhead (project-based and employee-based)
6. Generate payroll → generate project calculations
7. Approve calculations → generate report
8. Verify: budget vs actual comparison shows correctly

### T397: E2E — Inventory Full Flow

**Test:**

1. Create location → category (individual tracking mode) → 3 items with serial numbers
2. Reserve item for new employee
3. Issue reserved item → employee acknowledges
4. Employee requests another item → admin approves → issues
5. Employee returns item → status back to available
6. Dispose damaged item → removed from available pool
7. Verify: movement audit trail shows all transitions

### T398: E2E — ATS Full Flow

**Test:**

1. Create job listing → publish → verify public URL works
2. Submit application via public form (with PDPA consent)
3. Move candidate: new → screening → shortlisted
4. Schedule interview → interviewer submits feedback with scores
5. Move to offered → create offer letter
6. Move to hired → click "Onboard"
7. Verify: employee created with pre-filled data from candidate
8. Verify: candidate record linked to employee

---

## Updated Summary — Full Module Coverage

| Module                | Implementation  | Gap Status        |
| --------------------- | --------------- | ----------------- |
| Payroll               | T336-T342       | COVERED           |
| Leave                 | T343-T348       | COVERED           |
| Claims                | T349-T353       | COVERED           |
| Attendance            | T354-T356       | COVERED           |
| Shift/Rostering       | T357-T358       | COVERED           |
| Appraisal             | T359-T360       | COVERED           |
| Reports               | T366-T367       | COVERED           |
| Settings/Admin        | T361-T365       | COVERED           |
| Employee Lifecycle    | T368-T369       | COVERED           |
| Cost Centres          | T370            | COVERED           |
| Employee Self-Service | T316-T322, T374 | COVERED           |
| **Project Costing**   | **T386-T389**   | **COVERED (NEW)** |
| **Inventory**         | **T390-T392**   | **COVERED (NEW)** |
| **ATS**               | **T393-T395**   | **COVERED (NEW)** |

**Total: 121 tasks (T278-T398) across 21 milestones. Zero deferred modules.**
