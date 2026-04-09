# Backlog: Red Team Findings (Rounds 9-11)

Items already fixed are marked ~~strikethrough~~. Remaining items are organized by priority.

---

## Milestone 1: Document Generation (CRITICAL)

### TODO-B01: PDF/DOCX document generation

- **Priority**: Critical
- **Source**: Round 11, F-C1
- **Current state**: `src/hr_advisory/api/routers/document.py` generates plain text only. Frontend downloads as `.txt`.
- **Required**: Generate employment contracts, KET documents, HR templates as PDF and DOCX
- **Approach**: The payroll router already has PDF generation (payslip PDFs at line 651+). Reuse that pattern with `reportlab` for PDF. For DOCX, use `python-docx` (already installed).
- **Files**: `src/hr_advisory/api/routers/document.py`, `apps/web/src/app/(dashboard)/documents/[id]/generate/page.tsx`
- **Acceptance**: User can download a generated employment contract as a formatted PDF with company letterhead

### TODO-B02: Document preview page renders formatted content

- **Priority**: High
- **Source**: Round 11, F-C1 (related)
- **Files**: `apps/web/src/app/(dashboard)/documents/[id]/preview/page.tsx`
- **Acceptance**: Preview shows the document with proper formatting, sections, and company branding before download

---

## Milestone 2: Onboarding Enhancement (CRITICAL)

### TODO-B03: Instant compliance snapshot in company onboarding

- **Priority**: Critical
- **Source**: Round 11, F-C2
- **Current state**: CompanySetupModal goes Welcome -> Form -> Success -> dashboard reload. No insight step.
- **Required**: Add a "Compliance Snapshot" step between Form and Success that shows 3-5 immediate insights based on sector, headcount, and workforce composition
- **Approach**: The `/onboarding` page already has a `ComplianceSnapshotStep` component that generates client-side insights. Port this logic into the CompanySetupModal as step 3.
- **Files**: `apps/web/src/components/company/CompanySetupModal.tsx`, `apps/web/src/components/onboarding/ComplianceSnapshotStep.tsx`
- **Acceptance**: After entering company details, user sees "Based on your profile, here are 4 things you need to know" before the success screen

### TODO-B04: CompanySetupModal uses correct API endpoint

- **Priority**: Medium
- **Source**: Round 11, M-4
- **Current state**: Dashboard's CompanySetupModal calls `clientsApi.create()` with `as any` type assertion
- **Required**: Use `profileApi.create()` to create a company profile, matching the profile page
- **Files**: `apps/web/src/components/company/CompanySetupModal.tsx`

---

## Milestone 3: Notifications & Alerts (HIGH)

### TODO-B05: Wire regulatory alert email delivery

- **Priority**: High
- **Source**: Round 11, F-H2
- **Current state**: Push service exists (`src/hr_advisory/notifications/push_service.py`), Resend email adapter exists (`src/hr_advisory/mcp_servers/adapters/resend_email.py`), but neither is called when alerts are published
- **Required**: When a regulatory alert is published, send email notifications to users who have email alerts enabled
- **Files**: `src/hr_advisory/api/routers/alerts.py`, `src/hr_advisory/notifications/push_service.py`
- **Acceptance**: Publishing a regulatory alert triggers email delivery to subscribed users

### TODO-B06: Wire regulatory alert push notifications

- **Priority**: Medium
- **Source**: Round 11, F-H2 (related)
- **Required**: Browser push notifications for urgent compliance alerts
- **Files**: Frontend service worker, `src/hr_advisory/notifications/push_service.py`

---

## Milestone 4: Calculator Enhancements (HIGH)

### TODO-B07: Quota calculator what-if scenarios

- **Priority**: High
- **Source**: Round 11, M-11
- **Current state**: Single-shot calculation only
- **Required**: Add "What if I hire..." section below results: dropdown for pass type (EP/SP/WP), number input, recalculate button. Show side-by-side comparison of current vs proposed.
- **Files**: `apps/web/src/app/(dashboard)/calculators/elements/QuotaLevyCalculator.tsx`
- **Acceptance**: User can compare "current state" vs "if I hire 1 more S Pass" in a single view

---

## Milestone 5: Security Hardening (MEDIUM)

### TODO-B08: Sanitize error messages in API responses

- **Priority**: Medium
- **Source**: Round 11, S-H2
- **Current state**: `str(exc)` exposed in HTTPException details in `integrations.py`, `admin.py`, `llm_config.py`
- **Required**: Replace infrastructure error messages with generic text, log originals server-side
- **Files**: `src/hr_advisory/api/routers/integrations.py`, `admin.py`, `llm_config.py`, `settings.py`

### TODO-B09: Add rate limiting to Google OAuth exchange

- **Priority**: Medium
- **Source**: Round 11, M-5
- **Files**: `src/hr_advisory/api/routers/auth.py` (google_exchange endpoint)

### TODO-B10: Fix saga tenant isolation type mismatch

- **Priority**: Medium
- **Source**: Round 11, M-6
- **Current state**: `saga.tenant_id` is str, `company_id` is int — comparison always fails
- **Files**: `src/hr_advisory/api/routers/integrations.py:271`

### TODO-B11: Add rate limiting to 13 routers missing it

- **Priority**: Medium
- **Source**: Round 11, M-8
- **Routers**: claims, appraisals, shifts, projects, banking, alerts, calculator, compliance, reports, admin, integrations, clients, kb
- **Required**: Add `check_rate_limit` to POST/PATCH/DELETE endpoints

---

## Milestone 6: Performance (MEDIUM)

### TODO-B12: Fix N+1 query in employee list

- **Priority**: Medium
- **Source**: Round 11, Q-H1
- **Current state**: `_bulk_find_users` makes one DB query per user. 200 employees = 200 queries.
- **Required**: Single `list_records("User", {"company_id": company_id})` call with in-memory map
- **Files**: `src/hr_advisory/api/routers/employees.py:295-305`

### TODO-B13: Add pagination to list endpoints

- **Priority**: Medium
- **Source**: Round 11, M-10
- **Current state**: 21 occurrences of `limit: 10000` as de facto unlimited
- **Required**: Implement `page`/`page_size` query parameters. Priority: GET /employees, GET /leave/applications, GET /payroll/payslips
- **Files**: Multiple routers

### TODO-B14: Fix dataflow_crud.count() double query

- **Priority**: Low
- **Source**: Round 11, M-9
- **Files**: `src/hr_advisory/services/dataflow_crud.py:93-102`

---

## Milestone 7: Frontend Polish (MEDIUM)

### TODO-B15: Add responsive breakpoints to 8 pages

- **Priority**: Medium
- **Source**: Round 11, M-3
- **Pages**: appraisals, shifts, recruitment, approvals, my-claims, my-attendance, my-timesheets, my-payslips
- **Required**: Add sm:/md:/lg: Tailwind breakpoints for mobile-friendly layouts
- **Acceptance**: All employee-facing pages usable on mobile (375px width)

### TODO-B16: Implement turnover analysis report

- **Priority**: Low
- **Source**: Round 11, L-1
- **Current state**: "Coming Soon" badge visible in reports page
- **Files**: `apps/web/src/app/(dashboard)/reports/page.tsx`, backend endpoint needed

### TODO-B17: Add multilingual support (Mandarin, Malay, Tamil)

- **Priority**: Low
- **Source**: Round 11, L-2
- **Current state**: "More languages coming soon" banner in settings
- **Required**: i18n translations for core UI elements

---

## Milestone 8: Code Quality (LOW)

### TODO-B18: Replace datetime.utcnow() with datetime.now(timezone.utc)

- **Priority**: Low
- **Source**: Round 11, M-7
- **Current state**: 28 occurrences in onboarding.py
- **Files**: `src/hr_advisory/api/routers/onboarding.py`

### TODO-B19: Extract duplicate helper functions to shared module

- **Priority**: Low
- **Source**: Round 11, L-5
- **Current state**: `_validate_text_length`, `_find_employee_for_user` duplicated across 8 routers
- **Required**: Create `src/hr_advisory/api/routers/_helpers.py`

### TODO-B20: Use UUID4 for document IDs instead of predictable hash

- **Priority**: Low
- **Source**: Round 11, L-6
- **Files**: `src/hr_advisory/api/routers/document.py`

### TODO-B21: Synchronize headcount between Company Profile and actual employees

- **Priority**: Low
- **Source**: Round 11, L-4
- **Required**: Either auto-compute profile headcount from employee records, or show a warning when they diverge

### TODO-B22: Fix silent error swallowing in dashboard/reports

- **Priority**: Low
- **Source**: Round 11, L-3
- **Current state**: `.catch(() => {})` hides API failures
- **Required**: Show user-friendly error states when data fails to load

---

## Already Fixed (this session)

- ~~S-C1: Password change token_version bump~~ (fixed in round 11 deploy)
- ~~S-C2: Cross-tenant alert leak~~ (fixed in round 11 deploy)
- ~~S-H1: Unbounded in-memory stores~~ (fixed in round 11 deploy)
- ~~Q-H2: Missing isfinite() checks~~ (fixed in round 11 deploy)
- ~~U-H1: Orphan pages navigation~~ (fixed in round 11 deploy)
- ~~U-H2: Dashboard headcount field~~ (fixed in round 11 deploy)
- ~~M-1: Notification bell count~~ (fixed in round 11 deploy)
- ~~M-2: UEN edit contradiction~~ (fixed in round 11 deploy)
- ~~F-H1: S Pass sub-quota~~ (fixed in round 11 deploy)
- All security fixes from rounds 9-10 (PII encryption, RBAC, token versioning, etc.)
