# Recruitment Module: User Flows & Information Architecture

## Design Context

In Singapore SMEs (10-200 employees), the HR Manager is often one person handling payroll, leave, compliance, AND recruitment. They are not a dedicated recruiter. Every screen must respect that — no jargon, no enterprise complexity, every common action completable in under 3 clicks.

---

## Navigation Structure

```
RECRUITMENT (sidebar section)
  ├── Dashboard      (landing — "what needs my attention")
  ├── Jobs           (manage job postings)
  │   ├── /jobs              → job list
  │   ├── /jobs/new          → create/edit job
  │   ├── /jobs/:id          → job detail + Kanban pipeline
  │   └── /jobs/:id/settings → pipeline stages, hiring team
  ├── Candidates     (global candidate pool, searchable)
  │   ├── /candidates        → search & filter all candidates
  │   └── /candidates/:id    → full candidate profile
  ├── Interviews     (calendar view)
  │   └── /interviews/:id    → interview detail + feedback
  └── Careers Page   (public page configuration)
```

Each concern gets its own route — enables bookmarking, browser back/forward, and parallel tabs.

### Role-Based Visibility

| Navigation Item       | HR Manager | Hiring Manager   | Interviewer   | Candidate |
| --------------------- | ---------- | ---------------- | ------------- | --------- |
| Dashboard             | Full       | Dept only        | Hidden        | Hidden    |
| Jobs                  | Full CRUD  | Dept (read only) | Hidden        | Hidden    |
| Candidates            | Full       | Dept only        | Assigned only | Hidden    |
| Interviews            | Full       | Dept only        | Assigned only | Hidden    |
| Careers Config        | Full       | Hidden           | Hidden        | Hidden    |
| Careers Page (public) | Hidden     | Hidden           | Hidden        | Full      |

---

## Core User Flows

### Flow 1: Post a Job

**Who**: HR Manager | **Frequency**: 2-5x/month | **Goal**: Idea to published in < 10 minutes

1. Click "+ New Job" (persistent CTA on Jobs page)
2. **Single-page form** (not a wizard — 5-8 fields don't need steps):
   - Basics: title, department, location, employment type
   - Compensation: salary range (visible only to hiring team)
   - Description & requirements (rich text)
   - Hiring team: select hiring manager + interviewers from employees
   - Pipeline stages (defaults pre-filled, customizable)
   - Screening questions (optional, 3-5 knockout questions)
3. Preview — shows exactly what candidates will see on careers page
4. **Compliance gate**: system scans description for TAFEP issues before publishing
   - "This says 'young and energetic' — age-related language may attract a TAFEP complaint"
   - One-click fix or dismiss with justification
5. Publish → job appears on careers page, shareable link generated

**Key design decision**: Save Draft is always available. Auto-save every 30 seconds. HR managers get interrupted constantly.

### Flow 2: Receive & Screen Applications

**Who**: HR Manager | **Frequency**: Daily during active hiring | **Goal**: Triage new applications quickly

1. Dashboard shows "12 new applications across 3 jobs"
2. Click into a job → **Kanban view** (primary view, not table)
   ```
   [Applied 8]  [Screening 5]  [Interview 3]  [Offer 1]  [Hired 0]
   ```
3. Each card shows: name, time since applied, source badge, quick-match indicator
4. Click card → **slide-over panel** (60% width) with:
   - Left: contact info, screening answers, notes
   - Right: inline PDF resume viewer (default tab), activity timeline, feedback
5. Quick actions from card: Move to next stage, Reject, View Profile
6. **Drag and drop** between columns to advance candidates
7. **Bulk actions**: select multiple → "5 selected: [Move to Screening] [Reject All]"
8. Rejection requires reason (dropdown) → auto-sends configurable rejection email

**Key design decision**: Kanban is primary, table is secondary (toggle in top-right). A table shows data; a Kanban shows workflow state.

### Flow 3: Interview Pipeline

**Who**: HR Manager (schedules), Interviewer (conducts + feedback), Hiring Manager (reviews)

1. Advance candidate to "Interview" stage
2. **Schedule modal**: round type, interviewers (multi-select from employees), date/time, format (in-person/video/phone/panel), location/link
3. Notifications sent:
   - Candidate: date, time, location, interviewer names, prep instructions
   - Interviewers: date, time, candidate profile link, resume, job description
4. **Interviewer view** (minimal): "My Interviews" — upcoming interviews, candidate profiles, feedback form
5. **Structured feedback form**:
   - Overall recommendation: Strong Yes / Yes / Neutral / No / Strong No
   - Rating per criteria (1-5 stars): Technical Skills, Communication, Problem Solving, Culture Fit
   - Text fields: Strengths, Concerns, Private Notes (hiring team only)
6. Feedback aggregated on candidate profile: average rating, consensus indicator
7. **Feedback reminders**: 48h after interview if not submitted, HR alerted at 72h
8. Decision: schedule another round, move to offer, or reject

**Key design decision**: Interviewers don't see each other's feedback until they submit their own (prevents anchoring bias).

### Flow 4: Make an Offer

**Who**: HR Manager (creates), Hiring Manager (approves), Candidate (responds)

1. Move candidate to "Offer" stage → offer creation form
2. Form pre-filled from job listing: title, department, salary range
3. HR fills: exact salary, start date, probation period, notice period, benefits
4. **Approval workflow**: system shows required approvers based on rules
   - Hiring manager always approves
   - Salary above threshold → additional approver (configurable)
5. Approvers notified → review candidate profile + feedback + proposed offer → Approve/Request Changes/Reject
6. Approved → HR clicks "Send Offer"
   - PDF offer letter generated from company template
   - Email sent to candidate with PDF attachment + online accept/decline link
7. Candidate responds:
   - Accept → triggers Flow 5 (Hire)
   - Decline → HR notified, option for counter-offer or backup candidate
   - No response by expiry → HR alerted 2 days before, option to extend

### Flow 5: Hire (Candidate → Employee)

**Who**: HR Manager | **Goal**: Zero re-entry of data

1. Candidate accepts offer → dashboard shows "Ready for conversion"
2. **Conversion review screen**:
   - Pre-filled from offer + application: name, email, phone, job title, department, reports-to, start date, salary, probation period
   - Remaining fields to complete: NRIC/FIN, DOB, citizenship, bank account, emergency contact
   - Compliance check: flags work permit requirements for non-citizen/PR
   - Onboarding toggle: select template, auto-assign
3. Click "Create Employee" →
   - Employee record created in Employees module
   - Payroll record initialized (salary, CPF ready)
   - Onboarding checklist assigned
   - Application marked "Hired"
4. **Auto-cleanup**:
   - Other candidates in pipeline notified (configurable rejection emails)
   - Job posting status → "Filled" (removed from careers page)
   - Recruitment metrics updated

### Flow 6: Candidate Self-Service

**Who**: External candidate | **Goal**: Apply easily, know where they stand

1. **Careers page** (`/careers`): public, no login, company-branded
   - List of open positions with filters (department, type, location)
   - Job detail page with description, requirements, benefits
2. **Application form** (one page, not multi-step):
   - Name, email, phone, resume upload, LinkedIn (optional)
   - Screening questions (from job config)
   - PDPA consent checkbox (mandatory) with privacy policy link
3. Confirmation: "Thank you! We'll review your application."
   - Confirmation email with application ID + portal link
4. **Application portal** (magic link auth, no password):
   - Status: Under Review → Interview → Decision (abstracted stages)
   - Timeline showing progress
   - Update resume/contact info
   - View messages from company

---

## Key Views

### Recruitment Dashboard

Purpose: "What needs my attention right now?" in 5 seconds.

```
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ OPEN JOBS    5   │  │ ACTIVE           │  │ INTERVIEWS       │
│ 2 need attention │  │ CANDIDATES  47   │  │ THIS WEEK    8   │
│                  │  │ 12 new this week │  │ 3 need feedback  │
└─────────────────┘  └──────────────────┘  └──────────────────┘

NEEDS YOUR ACTION
├─ 12 new applications awaiting review          [Review Now]
├─ 3 interviews completed, feedback not submitted [Send Reminder]
├─ 1 offer expiring in 2 days                   [View Offer]
└─ 1 offer accepted — ready for conversion      [Convert to Employee]

PIPELINE OVERVIEW
Job                     Applied  Screen  Interview  Offer  Hired
Sr Software Engineer       8       5        3        1      0
Marketing Manager         12       3        1        0      0
Finance Analyst            4       2        0        0      0

METRICS (last 30 days)
Avg Time to Hire: 28 days  |  Offer Acceptance: 75%
Avg Time in Stage: 4.2 days|  Top Source: Careers Page (62%)
```

### Job Detail Page (Kanban)

- Full Kanban board with drag-and-drop
- Cards show: name, applied date, source badge, status indicator, quick rating
- Click card → slide-over candidate profile
- View toggle: Kanban / Table
- Filters: source, date range, search
- Bulk actions via multi-select

### Candidate Profile

- Left (40%): contact, application info, screening answers, tags, HR notes, offer history
- Right (60%): tabbed — Resume (PDF viewer, default), Activity timeline, Feedback, Communications
- Action bar: Reject, Advance, Schedule Interview, Create Offer

### Interview Calendar

- Week/month view with color-coded interview blocks
- Filter by: job, interviewer, "my interviews only"
- Click block → detail panel with candidate link + quick actions
- Feedback status indicators on blocks (submitted / overdue)

### Careers Page (Public)

- Clean minimal design — logo, culture blurb, job cards, footer
- Mobile-first (candidates apply from phones)
- Company branding configurable in admin settings
- SEO-friendly URLs (`/careers/jobs/senior-software-engineer`)

---

## Responsive Design

| Breakpoint           | Layout                                                                          |
| -------------------- | ------------------------------------------------------------------------------- |
| Desktop (>1280px)    | Full sidebar + 5 Kanban columns visible                                         |
| Laptop (1024-1280px) | Collapsed sidebar, 4 columns                                                    |
| Tablet (768-1024px)  | Hidden sidebar, 3 columns, horizontal scroll                                    |
| Mobile (<768px)      | Single column, swipe between stages, explicit action buttons (no drag-and-drop) |

---

## Pipeline Stage Colors (Consistent Across All Views)

| Stage     | Color  | Hex     |
| --------- | ------ | ------- |
| Applied   | Gray   | #6B7280 |
| Screening | Blue   | #3B82F6 |
| Interview | Purple | #8B5CF6 |
| Offer     | Amber  | #F59E0B |
| Hired     | Green  | #10B981 |
| Rejected  | Red    | #EF4444 |

Urgency indicators: red left-border (overdue >48h), amber left-border (expiring <48h), blue "NEW" badge (<24h).

---

## Permissions Model

| Action                | HR Manager            | Hiring Mgr      | Interviewer | Candidate   |
| --------------------- | --------------------- | --------------- | ----------- | ----------- |
| Create/edit/close job | Yes                   | Request (draft) | No          | No          |
| View candidates       | All                   | Dept only       | Assigned    | Own profile |
| Move candidates       | Yes                   | Dept only       | No          | No          |
| Schedule interviews   | Yes                   | Dept only       | No          | No          |
| Submit feedback       | Yes                   | Yes             | Assigned    | No          |
| Create offer          | Yes                   | No              | No          | No          |
| Approve offer         | Yes (below threshold) | Yes (dept)      | No          | No          |
| Accept/decline offer  | No                    | No              | No          | Yes         |
| Convert to employee   | Yes                   | No              | No          | No          |
| View salary info      | Yes                   | Configurable    | No          | No          |
