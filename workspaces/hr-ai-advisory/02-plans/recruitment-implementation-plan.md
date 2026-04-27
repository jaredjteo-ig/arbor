# Recruitment Module: Implementation Plan

## Overview

Build out the recruitment module from its current skeleton into a production-ready feature that crosses the "good enough to not buy a separate ATS" threshold, with Singapore-specific compliance as the long-term differentiator.

**Core value proposition**: When you hire someone in Arbor, every system updates automatically — payroll, onboarding, compliance, leave entitlements. No standalone ATS can match this.

---

## Phase 0: Fix Critical Bugs (Pre-requisite)

These must be fixed before any new features — the current module is broken in production.

### 0.1 Model-Router Field Alignment

- `position_title` → `title` (or vice versa) across JobListing model and router
- `is_published: bool` → add `status: str` field to JobListing model
- `location_or_link` → `location` in InterviewSchedule
- `interviewer_ids` → align with router's `interviewers` field
- Backend initial stage `"applied"` → `"new"` to match frontend pipeline

### 0.2 Create Missing Offer Model

- Define `@db.model class Offer` in `company_user.py`
- Fields: candidate_id, job_listing_id, company_id, salary, currency, salary_period, start_date, position_title, employment_type, probation_months, notice_period_days, benefits_summary, terms_text, status, approved_by, approved_at, sent_at, responded_at, expiry_date, created_by

### 0.3 Register Recruitment Models

- Add JobListing, Candidate, InterviewSchedule, InterviewFeedback, Offer to `models/__init__.py`

### 0.4 NRIC Encryption or Removal

- PDPC discourages NRIC collection during recruitment
- Recommendation: remove `nric_fin` from Candidate model, collect during onboarding only

---

## Phase 1: Core Pipeline (Enables Daily Use)

The goal: an HR manager can post a job, receive applications with resumes, track candidates through a pipeline, and manage the process from one screen.

### 1.1 Resume Upload & Viewing

- **Backend**: `POST /recruitment/candidates/{id}/resume` — multipart/form-data upload
  - Reuse pattern from `employees.py:2802-2865` (10MB limit, PDF/DOCX/JPG/PNG)
  - Store with UUID filename in tenant-prefixed directory
  - `GET /recruitment/candidates/{id}/resume` — serve file with access control
- **Frontend**: File input in Add Candidate modal, "View Resume" button on candidate card
  - Inline PDF viewer (iframe or PDF.js) in candidate profile panel

### 1.2 Candidate Detail Page

- Slide-over panel (60% width) from Kanban card click
- Left column (40%): contact info, application metadata, screening answers, notes
- Right column (60%): tabbed — Resume (PDF viewer), Activity timeline, Interview Feedback, Communications
- Resume tab as default view

### 1.3 Email Notifications for Candidates

- Connect to existing SES/Resend email adapters
- Templates: application received, interview invitation, offer sent, rejection notice
- Configurable per company (on/off per notification type)
- Automated on stage transitions (configurable)

### 1.4 Candidate-to-Employee Data Pre-fill

- When hire endpoint fires, carry all shared fields into the employee/invitation record:
  - name, email, phone, date_of_birth, nationality, citizenship_status, gender, race, address
- Employee logs in and sees profile 80% complete

### 1.5 Recruitment-to-Onboarding Handoff

- On hire: auto-create OnboardingAssignment with department-specific template
- Pre-fill start date, department, designation from offer data
- Connect to existing onboarding module

### 1.6 Rejection Workflow

- Dedicated reject endpoint requiring reason (dropdown + optional free text)
- Auto-send configurable rejection email
- Log rejection reason for TAFEP audit trail

### 1.7 Candidate Search & Filtering

- Filter by: stage, source, date applied, job listing, rating
- Search by: name, email, phone
- Both Kanban and table view support filters

---

## Phase 2: Singapore Compliance & Screening

The goal: Arbor does things no standalone ATS can — compliance guardrails specific to Singapore employment law.

### 2.1 PDPA Consent Collection

- Add `RECRUITMENT` consent purpose to PDPA module
- Collect consent on candidate creation (manual entry) or application submission (careers page)
- Record: purpose, timestamp, IP address, consent text version
- Display consent status on candidate profile

### 2.2 FCF Compliance Checker

- On job creation: if company has 10+ employees AND salary < $22,500/month, show advisory
- "Fair Consideration Framework requires advertising on MyCareersFuture for 14 days before applying for EP/S Pass"
- Track MCF posting date and 14-day countdown on job detail page
- Source: `kb/content/foreign_manpower.py:707-800`

### 2.3 TAFEP Job Ad Language Scanner

- Pre-publish check: scan job description for discriminatory language patterns
- Flag: age-related ("young", "energetic"), gender ("female preferred"), race/language ("Mandarin-speaking" without justification), nationality, marital status, religion
- Show warning with TAFEP guidance and suggested rephrasing
- Source: `kb/content/tafep.py` fair recruitment provisions

### 2.4 Pre-Screening Questionnaires

- New models: ScreeningQuestion, ScreeningResponse
- Per-job configurable questions (text/boolean/multiple-choice)
- Knockout questions auto-flag unqualified candidates
- Answers visible on candidate profile

### 2.5 Screening Scorecards

- New models: ScorecardTemplate, ScorecardEntry
- Per-job evaluation criteria with weights
- Independent reviewer scoring (prevents anchoring bias)
- Aggregate scores visible on candidate profile

### 2.6 Offer Letter PDF Generation

- Extend document generation engine (`document.py`)
- Company-configurable offer letter template
- Auto-fill from offer data (name, title, salary, start date, benefits)
- Download PDF or send via email

### 2.7 Approval Workflows

- Job posting approval: require hiring manager sign-off before publishing
- Offer approval: threshold-based (e.g., salary > $X requires director approval)
- Use existing ApprovalGroup infrastructure

### 2.8 Candidate Data Retention

- Configurable retention period (default: 2 years after last activity)
- Auto-notify HR before anonymization
- Candidate can request deletion via application portal (PDPA right)

### 2.9 Recruitment Analytics

- Dashboard metrics: open positions, pipeline by stage, time-to-hire, source effectiveness, offer acceptance rate
- Reports: diversity metrics (aggregated), cost-per-hire, pipeline conversion rates
- Add to existing reports router

### 2.10 Talent Pool

- Rejected candidates remain searchable for future openings
- Tags for categorization ("strong-technical", "consider-for-future")
- When new job posted, search previous candidates

---

## Phase 3: Differentiation

### 3.1 Public Careers Page

- Public route (`/careers`) — no auth required to view or apply
- Company branding (logo, colors, tagline) configurable by HR
- SEO-friendly URLs (`/careers/jobs/senior-software-engineer`)
- Application form: name, email, phone, resume upload, screening questions, PDPA consent
- CAPTCHA for bot prevention
- Mobile-first (candidates apply from phones)

### 3.2 Candidate Application Portal

- Post-submission: email + magic link authentication (no password)
- Status tracking: simplified stages (Under Review → Interview → Decision)
- Update resume/contact info
- View and respond to communications

### 3.3 Employee Referral Program

- Employees can refer candidates through the platform
- Track referral source, status, reward eligibility
- Dashboard showing referral pipeline

### 3.4 AI-Powered Compliance Screening

- Job ad compliance checker using FairEmploymentAgent (not resume screening)
- AI-generated structured interview questions from job requirements
- Resume-to-requirements matching with TAFEP guardrails
- Clear disclosure that AI is advisory, human makes final decisions

### 3.5 Calendar Integration

- Connect interview scheduling to Google Calendar (adapter exists)
- .ics file generation for email invitations
- Prevent double-booking

### 3.6 Hiring Manager Filtered View

- Department-based access control (not a new role)
- Hiring managers see: their department's candidates, pending approvals, feedback requests
- Cannot see: salary bands (configurable), other departments' pipelines

---

## Architecture Notes

### Storage Strategy

- MVP: local disk (matches employee document pattern)
- Production: S3 with presigned URLs (adapter already built)
- Configurable via environment variable

### Cross-Module Data Flows

```
Recruitment → Employees   (candidate data pre-fills employee record)
Recruitment → Payroll     (offer salary feeds into first payrun)
Recruitment → Onboarding  (hire triggers onboarding assignment)
Recruitment → Documents   (offer letter stored in employee docs)
Recruitment → Compliance  (FCF status in company compliance checks)
```

### Files to Modify

- `src/hr_advisory/models/company_user.py` — new models, fix field names
- `src/hr_advisory/models/__init__.py` — register models
- `src/hr_advisory/api/routers/recruitment.py` — major expansion
- `src/hr_advisory/api/routers/onboarding.py` — hire handoff
- `src/hr_advisory/api/routers/reports.py` — recruitment reports
- `src/hr_advisory/security/pdpa.py` — RECRUITMENT consent purpose
- `src/hr_advisory/templates/content.py` — email templates
- `apps/web/src/services/api/recruitment.ts` — frontend API expansion
- `apps/web/src/app/(dashboard)/recruitment/page.tsx` — full UI rebuild
