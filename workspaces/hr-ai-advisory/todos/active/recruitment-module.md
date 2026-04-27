# Recruitment Module — Complete Todo List

All tasks required to build the full recruitment module from the current skeleton to production-ready, organized into milestones.

**API Service Layer**: Update `apps/web/src/services/api/recruitment.ts` incrementally with each milestone — add types and methods as endpoints are built, not as a single batch task.

---

## Critical Path Dependencies

```
T-R068 (migration) → T-R001-T-R007 (field fixes) → T-R003/T-R004 (Offer model + registration)
→ T-R063 (seed data update) → T-R062 (demo seed data) → T-R064/T-R067 (tests)
→ T-R056 (multi-page routing) → Milestone 1+ features
```

---

## Milestone 0a: Database Migration & Deployment Setup

These tasks must run BEFORE any code changes deploy. Database schema must match the code that follows.

### T-R068: Database migration script for recruitment model field changes

- **What**: Create migration script to rename/add columns before code deploys
- **Details**:
  - Renames `position_title` → `title` on JobListing
  - Adds `status` column to JobListing (default derived from `is_published`)
  - Renames `location_or_link` → `location` on InterviewSchedule
  - Renames `interviewer_ids` → `interviewers` on InterviewSchedule
  - Handles NRIC data removal from Candidate (T-R006 schema prep)
  - Must run BEFORE T-R001 code changes deploy — running code against the old schema will cause immediate crashes
- **Files**: New migration script in `scripts/` or `src/hr_advisory/scripts/`

### T-R070: Deployment configuration for recruitment module

- **What**: Add environment variables and storage directories for recruitment features
- **Details**:
  - Add `RECRUITMENT_UPLOAD_DIR` to `.env.example`
  - Verify email credentials (`RESEND_API_KEY`) are documented and set on all environments
  - Add CAPTCHA keys placeholder for Phase 3 careers page (e.g., `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET_KEY`)
  - Document required storage directories and permissions (`uploads/recruitment/{company_id}/`)
  - Verify background task runner availability for scheduled checks (offer expiry, feedback reminders)
- **Files**: `.env.example`, deploy docs

---

## Milestone 0: Fix Critical Bugs (Pre-requisite)

The current module is broken in production. These must be fixed before any new work.

### T-R001: Align JobListing model fields with router and frontend

- **What**: Fix field name mismatches between `company_user.py` JobListing model, `recruitment.py` router, and `recruitment.ts` frontend types
- **Details**:
  - Model uses `position_title`, router/frontend use `title` — job titles display as "-"
  - Model has `is_published: bool`, router writes `status: "draft"/"published"/"closed"` — add `status: str = "draft"` field
  - Model uses `salary_range_min/max`, frontend uses `salary_min/max` — align names
  - Model has `organization_id` field that's unused — evaluate removal
  - Also update seed data in `src/hr_advisory/services/company_seeding.py` — `DEFAULT_JOB_LISTINGS` uses `position_title` and `is_published` which must change to match
- **Files**: `src/hr_advisory/models/company_user.py` (JobListing class), `src/hr_advisory/api/routers/recruitment.py`, `apps/web/src/services/api/recruitment.ts`
- **Depends on**: T-R068 (migration must run first)
- **Test**: Create a job via API, verify title and status render correctly in frontend

### T-R002: Fix Candidate stage mismatch

- **What**: Canonicalize the complete stage list across model, router, and frontend
- **Details**: Currently: model has `new/screening/shortlisted/interview/offered/hired/rejected/withdrawn`, frontend `STAGE_STYLES` has `new/screening/interview/assessment/offered/hired/rejected/withdrawn`, frontend `PIPELINE_STAGES` has `new/screening/interview/offered/hired`, backend sets initial to `applied`. Define the authoritative stage progression, remove phantom stages (`shortlisted`, `assessment`, `applied`), and align all three.
- **Files**: `src/hr_advisory/api/routers/recruitment.py` (create_candidate), `apps/web/src/services/api/recruitment.ts` (CandidateStage type), `apps/web/src/app/(dashboard)/recruitment/page.tsx` (STAGE_STYLES, PIPELINE_STAGES)
- **Test**: Add a candidate, verify they appear in the first pipeline column

### T-R003: Create Offer data model

- **What**: Router calls `dataflow_crud.create("Offer", {...})` but no model exists — crashes at runtime
- **Details**: Define `@db.model class Offer` with fields: candidate_id, job_listing_id, company_id, salary, currency (default "SGD"), salary_period (monthly/annual), start_date, position_title, employment_type, probation_months, notice_period_days, benefits_summary, terms_text, status (draft/pending_approval/approved/sent/accepted/declined/expired), approved_by, approved_at, sent_at, responded_at, expiry_date, created_by. Also update the existing `generate_offer` endpoint (router line ~574) to accept and persist all Offer model fields — current endpoint writes a simpler subset that doesn't match the model.
- **Files**: `src/hr_advisory/models/company_user.py`
- **Test**: Create an offer via the API endpoint, verify no crash

### T-R004: Register recruitment models in **init**.py

- **What**: JobListing, Candidate, InterviewSchedule, InterviewFeedback, and the new Offer model are not exported from the models package — may not appear in DataFlow registry
- **Files**: `src/hr_advisory/models/__init__.py`
- **Test**: Import each model from `hr_advisory.models`, verify DataFlow recognizes them

### T-R005: Fix InterviewSchedule field mismatches

- **What**: Model uses `location_or_link` but router writes `location`; model uses `interviewer_ids: str` (JSON array) but router writes `interviewers`
- **Details**: Also align `interview_type` values — model defaults to `in_person`, frontend uses `onsite`. Pick one canonical value and align both.
- **Files**: `src/hr_advisory/models/company_user.py` (InterviewSchedule), `src/hr_advisory/api/routers/recruitment.py`
- **Depends on**: T-R068 (migration must run first)
- **Test**: Schedule an interview, verify location and interviewer data persists

### T-R006: Remove NRIC from Candidate model

- **What**: PDPC discourages NRIC/FIN collection during recruitment (data minimization). Currently has `nric_fin: str` annotated as encrypted but never encrypted
- **Details**: Remove `nric_fin` field from Candidate model. NRIC should only be collected during onboarding after hire decision. Also remove `date_of_birth`, `race`, `gender` if not needed for the application (these can be collected post-hire). Keep `nationality` and `citizenship_status` as these inform work pass requirements.
- **Decision needed**: Which demographic fields to keep vs defer to onboarding
- **Files**: `src/hr_advisory/models/company_user.py` (Candidate class)
- **Depends on**: T-R068 (migration must run first)

### T-R007: Fix job status rendering in frontend

- **What**: Backend publish endpoint sets status to `"published"` but frontend `JOB_STATUS_STYLES` only has `"draft" | "open" | "closed" | "on_hold"` — published jobs get no badge style
- **Details**: Either change backend to use `"open"` when publishing, or add `"published"` to frontend styles. Also move T-R058 scope here: strip unimplemented USP claims from `layout.tsx` immediately (analytics, one-click conversion, structured scorecards don't exist yet). False claims on a live page damage credibility.
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `apps/web/src/app/(dashboard)/recruitment/page.tsx` (JOB_STATUS_STYLES), `apps/web/src/app/(dashboard)/recruitment/layout.tsx`

### T-R060: Fix shadow agent tool registry URLs for recruitment

- **What**: Shadow agent tool registry has URLs that don't match actual router endpoints
- **Details**:
  - `add_candidate` registered as `POST /recruitment/candidates` but actual is `POST /recruitment/jobs/{job_id}/candidates`
  - `schedule_interview` registered as `POST /recruitment/interviews` but actual is `POST /recruitment/candidates/{candidate_id}/interviews`
  - `update_candidate_status` registered as `PATCH /recruitment/candidates/{id}/status` but actual is `PATCH /recruitment/candidates/{candidate_id}` with stage in body
  - Fix all URLs and add shadow tools for new endpoints as milestones complete
- **Files**: `src/hr_advisory/shadow/tool_registry.py`

### T-R062: Seed recruitment demo data

- **What**: Create seed data for candidates, interviews, and feedback for demo purposes
- **Details**: Seed 8-10 candidates across pipeline stages for each demo job listing, at least 2 scheduled interviews with different types, at least 2 feedback entries, and 1 offer. The value audit demo script requires candidates at various stages.
- **Depends on**: T-R001, T-R003, T-R004, T-R063
- **Files**: `src/hr_advisory/services/company_seeding.py`

### T-R063: Update job listing seed data field names

- **What**: Update `DEFAULT_JOB_LISTINGS` in company_seeding.py to use aligned field names after T-R001
- **Details**: Change `position_title` → `title`, `is_published: True` → `status: "published"`, align salary field names
- **Depends on**: T-R001
- **Files**: `src/hr_advisory/services/company_seeding.py`

---

## Milestone 0b: Testing Foundation & Seed Data

### T-R064: Unit tests for recruitment router CRUD operations

- **What**: Test job CRUD, candidate CRUD, interview scheduling, feedback submission, offer creation, hire conversion
- **Details**: Cover tenant isolation (user from company A cannot access company B's candidates), verify field alignment fixes work, test stage transitions
- **Depends on**: T-R001 through T-R007
- **Files**: `tests/unit/test_recruitment.py`

### T-R067: Regression tests for field alignment fixes

- **What**: Verify data roundtrips correctly after model-router alignment
- **Details**: Create job via API → read back → verify title, status, salary fields match. Create candidate → verify stage is correct. Schedule interview → verify location, type, interviewers persist.
- **Depends on**: T-R001 through T-R007
- **Files**: `tests/integration/test_recruitment_fields.py`

---

## Milestone 1: Frontend Architecture + Resume Management

Set up the route structure first so all subsequent milestones build into the right pages rather than accumulating in a single 1100-line page.tsx.

### T-R056: Restructure recruitment into multi-page routing

- **What**: Move from single-page 3-tab layout to proper route-based navigation
- **Details**:
  - `/recruitment` → dashboard
  - `/recruitment/jobs` → job list
  - `/recruitment/jobs/[id]` → job detail + Kanban pipeline
  - `/recruitment/candidates` → global candidate search
  - `/recruitment/candidates/[id]` → candidate profile (full page)
  - `/recruitment/interviews` → calendar view
  - `/recruitment/careers` → careers page admin config
  - Each page is a separate route file under `apps/web/src/app/(dashboard)/recruitment/`
- **Files**: `apps/web/src/app/(dashboard)/recruitment/` (multiple new route files)

### T-R008: Backend resume upload endpoint

- **What**: Create `POST /recruitment/candidates/{candidate_id}/resume` accepting multipart/form-data
- **Details**:
  - Reuse pattern from `employees.py:2802-2865` (10MB limit, PDF/DOCX/JPG/PNG MIME validation)
  - Validate file type via magic bytes (read first bytes), not just Content-Type header which can be spoofed
  - Store with UUID filename in tenant-prefixed directory (`uploads/recruitment/{company_id}/`)
  - `resume_url` stored on Candidate must be an internal reference (UUID), not a publicly accessible path — the download endpoint resolves it
  - Create upload directory with appropriate permissions on first use
  - Update `resume_url` on the Candidate record
  - Validate candidate belongs to the user's company (tenant isolation)
- **Files**: `src/hr_advisory/api/routers/recruitment.py`
- **Test**: Upload a PDF, verify file stored and `resume_url` updated

### T-R009: Backend resume download/serve endpoint

- **What**: Create `GET /recruitment/candidates/{candidate_id}/resume` that serves the file
- **Details**:
  - Verify requesting user has access (same company, appropriate role)
  - Return file with correct Content-Type header
  - Support Content-Disposition for download vs inline viewing
  - Future: S3 presigned URLs when configured (adapter exists at `mcp_servers/adapters/s3_storage.py`)
- **Files**: `src/hr_advisory/api/routers/recruitment.py`

### T-R010: Frontend resume upload in Add Candidate modal

- **What**: Add file input field to the candidate creation form
- **Details**:
  - File picker accepting PDF, DOCX, JPG, PNG (max 10MB)
  - Upload file after candidate record is created (two-step: create candidate, then upload resume)
  - Show upload progress indicator
  - Display file name after successful upload
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`, `apps/web/src/services/api/recruitment.ts`

### T-R011: Frontend inline PDF resume viewer

- **What**: Embed a PDF viewer in the candidate profile panel
- **Details**:
  - Use iframe with PDF URL or PDF.js-based viewer component
  - Default tab when opening candidate profile
  - Download button alongside viewer
  - "Open in new tab" option
  - Graceful fallback for non-PDF files (show download link)
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx` (new component)

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 2: Candidate Detail & Pipeline UX

### T-R012: Candidate profile slide-over panel

- **What**: Full candidate profile view as a slide-over panel from Kanban card click
- **Details**:
  - Panel: 60% width from right side, Kanban visible behind
  - Left column (40%): contact info (email, phone, LinkedIn), application metadata (source, date, job title), screening answers, tags, HR notes
  - Right column (60%): tabbed — Resume (PDF viewer, default), Activity timeline, Interview Feedback, Communications
  - Action bar at top: Reject, Advance to next stage, Schedule Interview, Create Offer
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx` (new CandidateProfile component)

### T-R013: Activity timeline on candidate profile

- **What**: Chronological log of all actions taken on a candidate
- **Details**:
  - Backend: log stage changes, notes added, interviews scheduled, feedback submitted, offers sent with actor + timestamp
  - Frontend: vertical timeline component showing events
  - Auto-generated from existing data (stage changes) + new activity log entries
- **Files**: `src/hr_advisory/api/routers/recruitment.py` (add activity logging), `apps/web/src/app/(dashboard)/recruitment/page.tsx`

### T-R014: Candidate search and filtering

- **What**: Search and filter candidates across all jobs or within a specific job
- **Details**:
  - Backend: add query params to list endpoints — `stage`, `source`, `date_from`, `date_to`, `search` (name/email/phone)
  - Frontend: filter bar above Kanban/table with dropdowns and search input
  - Global candidates page (`/recruitment/candidates`) with cross-job search
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `apps/web/src/app/(dashboard)/recruitment/page.tsx`

### T-R015: Kanban drag-and-drop for stage transitions

- **What**: Allow dragging candidate cards between pipeline columns to change stage
- **Details**:
  - Use a drag-and-drop library (e.g., `@dnd-kit/core` or `react-beautiful-dnd`)
  - On drop: call moveStage API, show optimistic update, revert on failure
  - Confirm significant moves (e.g., moving to Offer triggers offer creation form)
  - Moving backward requires reason
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`, `package.json` (new dependency)

### T-R016: Bulk actions for candidates

- **What**: Select multiple candidates for batch operations
- **Details**:
  - Multi-select via checkboxes on Kanban cards or table rows
  - Toolbar: "N selected: [Move to →] [Reject All] [Tag]"
  - Bulk reject: single reason picker, optional email per candidate
  - Backend: batch endpoints or loop through existing single endpoints
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`, `src/hr_advisory/api/routers/recruitment.py`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 3: Email & Notifications

### T-R017: Recruitment email templates

- **What**: Create email templates for candidate communications
- **Details**:
  - Templates: application received confirmation, interview invitation (with date/time/location), offer letter cover email, rejection notice, feedback reminder (internal)
  - Use existing template engine at `templates/content.py`
  - HTML email templates matching company branding
  - Variables: candidate_name, job_title, company_name, interview_date, etc.
- **Files**: `src/hr_advisory/templates/content.py` (new templates)

### T-R018: Automated email on stage transitions

- **What**: Send emails to candidates when their application stage changes
- **Details**:
  - Connect stage transitions in recruitment router to email sending via SES/Resend adapters
  - Configurable per company: which transitions trigger emails (on/off toggle per stage)
  - Log email delivery in candidate activity timeline
  - Fail gracefully (log error, don't block stage transition)
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `src/hr_advisory/mcp_servers/adapters/resend_email.py`

### T-R019: Interview invitation emails

- **What**: Send structured interview invitation to candidates when interview is scheduled
- **Details**:
  - Include: date, time, duration, format (in-person/video/phone), location or video link, interviewer names, preparation instructions
  - Generate .ics calendar attachment
  - Also notify interviewers with candidate profile link and resume
- **Files**: `src/hr_advisory/api/routers/recruitment.py` (schedule_interview endpoint)

### T-R020: Internal notification for pending feedback

- **What**: Remind interviewers to submit feedback after interviews
- **Details**:
  - 48 hours after interview: email reminder to interviewer
  - 72 hours: alert HR manager that feedback is overdue
  - Use existing notification infrastructure or simple scheduled check
- **Files**: `src/hr_advisory/api/routers/recruitment.py`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 3b: Shadow Agent Integration

### T-R061: Add recruitment-specific shadow agent nudges

- **What**: Create nudge triggers for recruitment-related actions
- **Details**:
  - Nudges for: new applications awaiting review, overdue interview feedback (48h+ after interview), expiring offers (2 days before expiry), candidates stuck in a stage too long (configurable threshold), FCF countdown approaching deadline
- **Depends on**: Milestone 3 (notifications infrastructure)
- **Files**: `src/hr_advisory/shadow/` nudge system

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 4: Hire-to-Employee Conversion

The core value proposition — seamless transition from candidate to employee.

### T-R021: Pre-fill employee data from candidate record on hire

- **What**: When hire endpoint fires, carry all shared fields into the invitation/employee creation
- **Details**:
  - Map Candidate → Employee fields: name, email, phone, nationality, citizenship_status, address
  - Map Offer → Employee fields: designation (from position_title), department, salary (monthly_salary), start_date, employment_type, probation_months, notice_period_days
  - The new employee should log in and see their profile 80% complete
- **Files**: `src/hr_advisory/api/routers/recruitment.py` (hire_candidate endpoint)

### T-R022: Auto-trigger onboarding on hire

- **What**: When candidate is hired, automatically create an OnboardingAssignment
- **Details**:
  - Select onboarding template based on department or company default
  - Pre-fill start date, department, designation from offer data
  - Create invitation with onboarding flag
  - Connect to existing onboarding module at `api/routers/onboarding.py`
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `src/hr_advisory/api/routers/onboarding.py`

### T-R023: Auto-close job and notify pipeline on hire

- **What**: When a candidate is hired, optionally close the job posting and notify remaining candidates
- **Details**:
  - If position filled (configurable): change job status to "filled", remove from careers page
  - Optionally send batch rejection emails to remaining active candidates
  - Log pipeline cleanup in activity timeline
- **Files**: `src/hr_advisory/api/routers/recruitment.py`

### T-R024: Frontend hire conversion review screen

- **What**: UI showing pre-filled employee data before final conversion
- **Details**:
  - Show all data being carried from candidate/offer
  - Highlight remaining fields to complete (NRIC, bank details, emergency contact — to be filled by new hire)
  - Compliance check: flag work permit requirements for non-citizen/PR
  - Onboarding template selector
  - "Create Employee" button
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 5: Rejection & Audit Trail

### T-R025: Structured rejection workflow

- **What**: Dedicated reject endpoint requiring documented reason
- **Details**:
  - Backend: `POST /recruitment/candidates/{id}/reject` with required `reason` (dropdown: not qualified, overqualified, position filled, candidate withdrew, other) and optional `notes`
  - Auto-send rejection email (configurable template)
  - Log rejection with actor, timestamp, reason in activity timeline
  - TAFEP audit trail: rejection reasons are queryable for compliance reviews
- **Files**: `src/hr_advisory/api/routers/recruitment.py`

### T-R026: Audit trail for all stage transitions

- **What**: Log every candidate stage change with who, when, and why
- **Details**:
  - New model or extend candidate activity: `CandidateActivity` (candidate_id, actor_id, action, from_stage, to_stage, reason, details_json, created_at)
  - Log automatically on every stage change in the router
  - Queryable for TAFEP compliance investigations
- **Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/recruitment.py`

### T-R069: Frontend reject action with reason modal

- **What**: When user clicks "Reject" on candidate profile or Kanban card, show modal requiring reason selection
- **Details**: Reason dropdown (not qualified, overqualified, position filled, candidate withdrew, other) + optional notes field. Calls `POST /recruitment/candidates/{id}/reject` from T-R025. Show rejected candidates in a filtered view or grayed-out in pipeline.
- **Depends on**: T-R025 (backend reject endpoint), T-R012 (candidate profile panel)
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 6: Singapore Compliance

### T-R027: PDPA consent collection for candidates

- **What**: Collect and record PDPA consent when candidate data is created
- **Details**:
  - Add `RECRUITMENT` consent purpose to `security/pdpa.py` ConsentPurpose enum
  - On manual candidate creation: auto-record consent (HR enters on behalf, notes source)
  - On careers page application: mandatory consent checkbox with privacy policy link
  - Display consent status (granted/not granted/expired) on candidate profile
  - Track: purpose, timestamp, IP address, consent text version
- **Files**: `src/hr_advisory/security/pdpa.py`, `src/hr_advisory/api/routers/recruitment.py`

### T-R028: FCF compliance checker

- **What**: Alert HR when a job posting may require MyCareersFuture advertising under the Fair Consideration Framework
- **Details**:
  - Check on job creation/publish: if company has 10+ employees AND salary < $22,500/month AND role is for EP/S Pass candidate
  - Show advisory banner: "FCF requires advertising on MyCareersFuture for 14 days before applying for work pass"
  - Track MCF posting date field on JobListing, show countdown timer on job detail page
  - Check exemptions: fewer than 10 employees, salary above threshold, intra-corporate transferees
  - Source: `kb/content/foreign_manpower.py:707-800`
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `src/hr_advisory/models/company_user.py` (add mcf fields to JobListing)

### T-R029: TAFEP job ad language scanner

- **What**: Scan job descriptions for discriminatory language before publishing
- **Details**:
  - Pre-publish check: pattern-match against known problematic phrases
  - Categories: age ("young", "energetic", "fresh graduate only"), gender ("female preferred", "male candidates"), race/language ("Mandarin-speaking" without business justification, "Chinese preferred"), nationality ("Singaporeans only" without justification), marital status, religion
  - Show warning with TAFEP guidance and suggested rephrasing
  - HR can dismiss with justification (logged for audit)
  - Source: `kb/content/tafep.py` fair recruitment provisions
- **Files**: `src/hr_advisory/api/routers/recruitment.py` (new scan function + endpoint)

### T-R030: Candidate data retention policy

- **What**: Auto-manage candidate data lifecycle per PDPA requirements
- **Details**:
  - Configurable retention period per company (default: 24 months after last activity)
  - Scheduled check: flag candidates approaching retention expiry
  - Notify HR before anonymization
  - Anonymization: clear personal data (name, email, phone, resume) but retain statistical data (source, stage reached, dates) for analytics
  - Candidate can request deletion via email (PDPA data access right)
  - Note: DataFlow 2.0 has a built-in retention engine. Use `__dataflow__['retention'] = {'after_days': 730}` on the Candidate model instead of building custom retention logic. Still need PDPA notification workflow before auto-purge.
- **Files**: `src/hr_advisory/security/pdpa.py`, `src/hr_advisory/api/routers/recruitment.py`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 7: Screening & Assessment

### T-R031: Screening question models

- **What**: Create data models for per-job screening questions and candidate responses
- **Details**:
  - `ScreeningQuestion`: job_listing_id, company_id, question_text, question_type (text/boolean/multiple_choice), options (JSON for MC choices), is_required, is_knockout, sort_order
  - `ScreeningResponse`: candidate_id, question_id, response_text, response_value (boolean/numeric for auto-scoring)
- **Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/models/__init__.py`

### T-R032: Screening question CRUD endpoints

- **What**: API endpoints to manage screening questions per job listing
- **Details**:
  - `GET /recruitment/jobs/{id}/questions` — list questions for a job
  - `POST /recruitment/jobs/{id}/questions` — add a question
  - `PATCH /recruitment/questions/{id}` — update a question
  - `DELETE /recruitment/questions/{id}` — remove a question
  - Reorder via PATCH with sort_order
- **Files**: `src/hr_advisory/api/routers/recruitment.py`

### T-R033: Screening questions in job creation UI

- **What**: Add screening question builder to the job creation/edit form
- **Details**:
  - Section below job description: "Screening Questions"
  - Add question button → type picker (text/yes-no/multiple choice)
  - Mark as knockout (auto-flag candidates who answer "wrong")
  - Drag to reorder
  - Preview how candidates will see questions
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`

### T-R034: Screening responses in candidate profile

- **What**: Display candidate's screening answers on their profile
- **Details**:
  - Show in left column of candidate profile panel
  - Knockout answers highlighted in red/warning
  - For boolean/MC questions, show pass/fail indicator
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`

### T-R035: Scorecard template models and CRUD

- **What**: Structured evaluation scorecards per job listing
- **Details**:
  - `ScorecardTemplate`: job_listing_id, company_id, criteria_name, criteria_description, max_score (default 5), weight (default 1.0), sort_order
  - `ScorecardEntry`: candidate_id, scorecard_template_id, reviewer_id, score, comments, created_at
  - CRUD endpoints for templates (tied to job) and entries (tied to candidate + reviewer)
- **Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/recruitment.py`

### T-R036: Scorecard UI in interview feedback form

- **What**: Replace or augment the current freeform feedback with structured scorecard
- **Details**:
  - When submitting feedback, show the job's scorecard criteria with 1-5 star rating per criteria
  - Aggregate scores visible on candidate profile (average per criteria, overall weighted average)
  - Independent scoring: interviewer doesn't see others' scores until after submitting
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 8: Offers & Approvals

### T-R037: Offer creation flow

- **What**: Full offer creation form when advancing candidate to "Offer" stage
- **Details**:
  - Pre-fill from job listing: title, department, salary range
  - HR fills: exact salary, start date, probation period, notice period, benefits summary
  - Show salary range guidance (approved range from job listing)
  - Set offer expiry date (default: 7 days)
  - Save as draft or submit for approval
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`, `src/hr_advisory/api/routers/recruitment.py`

### T-R038: Offer approval workflow

- **What**: Configurable approval chain for offers before sending to candidate
- **Details**:
  - Use existing ApprovalGroup infrastructure at `api/routers/approval_groups.py`
  - Default: hiring manager approves all offers
  - Threshold-based: salary above configurable amount requires additional approver
  - Approver receives notification → reviews candidate profile + feedback + offer terms → Approve/Request Changes/Reject
  - Sequential or parallel approval configurable
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, existing approval infrastructure

### T-R039: Offer letter PDF generation

- **What**: Generate professional offer letter PDF from template
- **Details**:
  - Extend document generation at `api/routers/document.py`
  - Company-configurable offer letter template (set once in settings)
  - Auto-fill: candidate name, job title, salary, start date, probation, notice period, benefits, reporting manager
  - Download PDF or attach to offer email
  - Store generated PDF in candidate documents
- **Files**: `src/hr_advisory/api/routers/document.py`, `src/hr_advisory/api/routers/recruitment.py`

### T-R040: Offer tracking and expiry

- **What**: Track offer status and handle expiry
- **Details**:
  - Statuses: draft → pending_approval → approved → sent → accepted/declined/expired
  - Alert HR 2 days before offer expiry
  - Option to extend expiry date
  - Candidate acceptance updates stage to "hired"
  - Frontend: offer status timeline on candidate profile
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `apps/web/src/app/(dashboard)/recruitment/page.tsx`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 9: Recruitment Dashboard & Analytics

### T-R041: Recruitment dashboard page

- **What**: Landing page for recruitment showing metrics and action items
- **Details**:
  - Metric cards: open positions count, active candidates, interviews this week
  - Action items section (sorted by urgency): new applications awaiting review, overdue feedback, expiring offers, accepted offers ready for conversion
  - Pipeline overview table: all jobs with candidate counts per stage
  - Bottom metrics: avg time-to-hire, offer acceptance rate, top source
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx` (new dashboard view or separate route)

### T-R042: Recruitment analytics endpoints

- **What**: Backend endpoints for recruitment metrics
- **Details**:
  - `GET /recruitment/analytics/summary` — open positions, total candidates, pipeline distribution
  - `GET /recruitment/analytics/time-to-hire` — average days from applied to hired, per job
  - `GET /recruitment/analytics/sources` — candidate source effectiveness (applications, conversions per source)
  - `GET /recruitment/analytics/pipeline` — conversion rates between stages
  - Add recruitment section to existing reports router
- **Files**: `src/hr_advisory/api/routers/recruitment.py` or `src/hr_advisory/api/routers/reports.py`

### T-R043: Interview calendar view

- **What**: Calendar view showing all scheduled interviews across jobs
- **Details**:
  - Week/month view with color-coded interview blocks by type (phone/video/onsite/panel)
  - Filter by: job, interviewer, "my interviews only"
  - Click block → detail panel with candidate link + feedback submission
  - Feedback status indicators (submitted / overdue)
  - List view alternative for mobile
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx` (new InterviewCalendar component)

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 10: Public Careers Page

### T-R044: Backend public job listing endpoints (no auth)

- **What**: Public API endpoints for the careers page — no authentication required
- **Details**:
  - `GET /careers/jobs` — list published jobs (company resolved from subdomain or slug)
  - `GET /careers/jobs/{slug}` — single job detail
  - `POST /careers/jobs/{slug}/apply` — submit application with resume upload
  - Rate limiting and CAPTCHA validation on apply endpoint
  - PDPA consent recording on application submission
- **Files**: `src/hr_advisory/api/routers/recruitment.py` (new public router section)

### T-R045: Public careers page frontend

- **What**: Public-facing page listing open positions
- **Details**:
  - New route: `/careers` (outside dashboard layout, no auth required)
  - Company branding: logo, primary color, tagline (from company settings)
  - Job cards: title, department, location, type, description preview, "Apply Now" CTA
  - Filters: department, location, employment type
  - Mobile-first responsive design
  - SEO-friendly URLs (`/careers/jobs/senior-software-engineer`)
- **Files**: `apps/web/src/app/careers/page.tsx` (new public route)

### T-R046: Application form page

- **What**: Public form for candidates to apply to a job
- **Details**:
  - Fields: name, email, phone, resume upload, LinkedIn URL (optional), cover letter (optional)
  - Screening questions from job configuration
  - PDPA consent checkbox (mandatory) with privacy policy link
  - CAPTCHA (reCAPTCHA or similar)
  - Confirmation page with application ID
  - Confirmation email sent to candidate
- **Files**: `apps/web/src/app/careers/jobs/[slug]/apply/page.tsx`

### T-R047: Careers page admin configuration

- **What**: Settings page for HR to configure the careers page branding
- **Details**:
  - Company logo upload, primary color picker, tagline text
  - About/culture section (rich text)
  - Preview button showing live careers page appearance
  - Custom domain configuration (future)
- **Files**: `apps/web/src/app/(dashboard)/recruitment/careers/page.tsx`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 11: Candidate Self-Service Portal

### T-R048: Candidate application portal

- **What**: Authenticated portal for candidates to track their application status
- **Details**:
  - Magic link authentication (email + OTP, no password)
  - View application status with simplified stages: Under Review → Interview → Decision
  - Visual timeline showing progress
  - Update resume or contact info
  - View messages from company
  - Route: `/applications` (separate from HRIS login)
- **Files**: New route and auth flow for candidates

### T-R049: Online offer acceptance

- **What**: Candidate can accept or decline an offer via a secure link
- **Details**:
  - Secure token-based link sent with offer email
  - Landing page shows offer summary + PDF download
  - Accept/Decline buttons with optional message
  - On accept: update offer status, trigger hire flow
  - On decline: update status, notify HR
- **Files**: New public route, `src/hr_advisory/api/routers/recruitment.py`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 12: Advanced Features

### T-R050: Talent pool (cross-job candidate database)

- **What**: Rejected or previous candidates remain searchable for future openings
- **Details**:
  - Candidates are NOT deleted after rejection — remain in global pool
  - Tags for categorization: "strong-technical", "consider-for-future", "culture-fit"
  - When posting a new job, option to search talent pool for matching candidates
  - Re-apply: move candidate from talent pool to new job's pipeline
- **Files**: `apps/web/src/app/(dashboard)/recruitment/page.tsx`, `src/hr_advisory/api/routers/recruitment.py`

### T-R051: Employee referral program

- **What**: Employees can refer candidates through the platform
- **Details**:
  - Referral submission form accessible to all employees (not just HR)
  - Track: referrer (employee_id), referred candidate, job, status, reward eligibility
  - New model: `Referral` (referrer_id, candidate_id, job_listing_id, company_id, status, reward_amount, paid_at)
  - Dashboard view showing referral pipeline
  - Source tracking: candidates from referrals tagged with referrer name
- **Files**: `src/hr_advisory/models/company_user.py`, `src/hr_advisory/api/routers/recruitment.py`, frontend

### T-R052: Hiring manager filtered view

- **What**: Department heads see a filtered recruitment view for their team's open roles
- **Details**:
  - Department-based access control (not a new role — use employee's department)
  - Hiring managers see: their department's job postings and candidates, pending offer approvals, feedback requests
  - Cannot see: salary bands (configurable), other departments' pipelines
  - Simplified navigation: no careers page config, no analytics
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `apps/web/src/app/(dashboard)/recruitment/page.tsx`

### T-R053: AI job ad compliance checker

- **What**: Use FairEmploymentAgent to review job descriptions for compliance issues
- **Details**:
  - On publish: send job description to FairEmploymentAgent for review
  - Agent checks against TAFEP guidelines (discriminatory language, FCF requirements)
  - Return structured feedback with specific issues and suggested fixes
  - HR can accept suggestions, dismiss with justification, or edit manually
  - Clear disclosure: "AI-assisted review — human decision required"
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `src/hr_advisory/agents/specialists/fair_employment.py`

### T-R054: AI-generated interview scorecards

- **What**: Generate structured interview questions and evaluation criteria from job requirements
- **Details**:
  - Input: job title, description, requirements
  - Output: 4-6 evaluation criteria with descriptions, suggested interview questions per criteria
  - HR can edit/customize before use
  - Creates audit trail of merit-based evaluation
  - Uses platform's BYOK LLM infrastructure
- **Files**: `src/hr_advisory/api/routers/recruitment.py`

### T-R055: Google Calendar integration for interviews

- **What**: Sync interview scheduling with Google Calendar
- **Details**:
  - Use existing adapter at `mcp_servers/adapters/google_calendar.py`
  - Create calendar events when interviews are scheduled
  - Include candidate name, job title, interview type in event
  - Prevent double-booking by checking interviewer availability
  - Generate .ics file for email invitations (works without Google integration)
- **Files**: `src/hr_advisory/api/routers/recruitment.py`, `src/hr_advisory/mcp_servers/adapters/google_calendar.py`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.

---

## Milestone 13: Navigation & Polish

### T-R059: Navigation sidebar update for recruitment sub-pages

- **What**: Add recruitment sub-navigation items to the sidebar
- **Details**:
  - Under "Recruitment" in sidebar: Dashboard, Jobs, Candidates, Interviews, Careers
  - Collapsible section matching existing sidebar patterns (Payroll, Leave, etc.)
  - Badge showing count of pending actions (new applications, overdue feedback)
- **Files**: `apps/web/src/components/shell/NavigationSidebar.tsx`

**Testing**: Update `tests/` with unit/integration tests covering this milestone's new endpoints and UI flows. Update `recruitment.ts` API types and methods for any new endpoints.
