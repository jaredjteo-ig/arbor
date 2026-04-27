# Recruitment Module: Feature Analysis & Current State Audit

## Current State

The recruitment module has a functional skeleton — backend router (658 lines), database models, and a basic frontend with three tabs (Jobs, Candidates, Interviews) and a Kanban pipeline.

### Working Components

| Component                                            | Status  |
| ---------------------------------------------------- | ------- |
| Job CRUD (create, list, get, update, publish, close) | Working |
| Candidate CRUD (add, list, update, stage change)     | Working |
| Interview scheduling and listing                     | Working |
| Interview feedback submission                        | Working |
| Hire-to-invitation conversion                        | Working |
| Frontend: 3-tab UI, Kanban pipeline, modals          | Working |

### Critical Bugs Found

| Bug                            | Severity | Detail                                                                                                         |
| ------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------- |
| **Offer model missing**        | CRITICAL | Router calls `dataflow_crud.create("Offer", {...})` but no `@db.model class Offer` exists — crashes at runtime |
| **Job title mismatch**         | MAJOR    | Model uses `position_title`, router/frontend use `title` — job titles display as "-"                           |
| **Job status mismatch**        | MAJOR    | Model has `is_published: bool`, router writes `status: "published"/"draft"/"closed"` — status badges broken    |
| **Stage mismatch**             | MAJOR    | Backend sets initial stage to `"applied"`, frontend expects `"new"` — candidates appear in no pipeline column  |
| **Interview field mismatches** | MODERATE | `location_or_link` vs `location`, `interviewer_ids` vs `interviewers`                                          |
| **NRIC not encrypted**         | MODERATE | Candidate model annotates `nric_fin` as encrypted but router never encrypts it                                 |
| **Models not registered**      | CRITICAL | Recruitment models not imported in `__init__.py` — may not appear in DataFlow registry                         |

---

## Feature Priorities

### MUST-HAVE (MVP)

| Feature                                 | Rationale                                                | Existing Infrastructure                                 |
| --------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------- |
| **Resume upload & inline viewing**      | Cannot run recruitment without viewing resumes           | Employee doc upload pattern in `employees.py:2802-2865` |
| **Fix all model-router mismatches**     | Current bugs make the module non-functional              | —                                                       |
| **Create Offer model**                  | Offer creation crashes without it                        | —                                                       |
| **Candidate detail page**               | Full profile with resume, timeline, feedback             | —                                                       |
| **Email notifications**                 | Application received, interview invite, offer, rejection | SES + Resend adapters already built                     |
| **PDPA consent collection**             | Legal requirement for candidate data                     | `PdpaConsentRecord` in `security/pdpa.py`               |
| **Rejection workflow**                  | Reason capture for TAFEP compliance                      | Candidate model has `rejection_reason`                  |
| **Candidate-to-employee data pre-fill** | Core value prop — hire flow must carry all shared fields | Hire endpoint exists but doesn't pre-fill               |
| **Recruitment-to-onboarding handoff**   | Auto-create onboarding assignment on hire                | Onboarding module fully built                           |
| **Hiring manager collaboration**        | Department heads need to review, give feedback, approve  | Approval groups infrastructure exists                   |

### IMPORTANT (Phase 2)

| Feature                           | Rationale                                                      | Existing Infrastructure                               |
| --------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------- |
| **FCF compliance checker**        | Flag MyCareersFuture requirement before hiring foreign workers | FCF rules in `kb/content/foreign_manpower.py:707-800` |
| **TAFEP job ad language scanner** | Flag discriminatory language before publishing                 | TAFEP KB in `kb/content/tafep.py`                     |
| **Pre-screening questionnaires**  | Knockout questions filter unqualified candidates               | New models needed                                     |
| **Screening scorecards**          | Structured evaluation supports fair hiring                     | New models needed                                     |
| **Offer letter PDF generation**   | Professional offer documents                                   | `document.py` PDF generation exists                   |
| **Approval workflows**            | Job posting and offer approvals                                | `approval_groups.py` infrastructure exists            |
| **Candidate data retention**      | PDPA auto-purge after retention period                         | `DataRetentionPolicy` in PDPA module                  |
| **Recruitment analytics**         | Time-to-hire, source effectiveness, pipeline conversion        | Reports router exists                                 |
| **Talent pool**                   | Rejected candidates searchable for future openings             | Extension of candidate model                          |
| **Public careers page**           | Candidates self-apply without HR manual entry                  | New public route needed                               |

### NICE-TO-HAVE (Phase 3)

| Feature                                      | Rationale                             |
| -------------------------------------------- | ------------------------------------- |
| AI-assisted resume screening and ranking     | Differentiator but TAFEP bias risk    |
| Employee referral program                    | Leverage existing employee base       |
| Calendar integration for interviews          | Google Calendar adapter already built |
| Job board integrations (LinkedIn, JobStreet) | Complex APIs, start with "Copy link"  |
| Skills-based keyword matching                | Auto-flag missing qualifications      |
| SkillsFuture qualification matching          | Adapter already exists                |
| Bulk candidate import (CSV + ZIP)            | Agency workflow                       |
| DOCX-to-PDF conversion for resumes           | Server-side conversion                |

---

## New Data Models Required

### Offer

```
company_id, candidate_id, job_listing_id, salary, currency, salary_period,
start_date, position_title, employment_type, probation_months, notice_period_days,
benefits_summary, terms_text, status (draft/pending_approval/approved/sent/accepted/declined/expired),
approved_by, approved_at, sent_at, responded_at, expiry_date, created_by
```

### ScreeningQuestion

```
job_listing_id, company_id, question_text, question_type (text/boolean/multiple_choice),
options (JSON), is_required, is_knockout, sort_order
```

### ScreeningResponse

```
candidate_id, question_id, response_text, response_value
```

### ScorecardTemplate

```
job_listing_id, company_id, criteria_name, criteria_description,
max_score, weight, sort_order
```

### ScorecardEntry

```
candidate_id, scorecard_template_id, reviewer_id, score, comments
```

---

## Risk Register

| Risk                                   | Likelihood | Impact      | Mitigation                                        |
| -------------------------------------- | ---------- | ----------- | ------------------------------------------------- |
| Offer creation crash (model missing)   | CERTAIN    | CRITICAL    | Define Offer model immediately                    |
| Job titles blank (field mismatch)      | CERTAIN    | MAJOR       | Align model ↔ router field names                  |
| PDPA non-compliance (no consent)       | HIGH       | CRITICAL    | Implement consent on candidate creation           |
| TAFEP complaint from discriminatory ad | MEDIUM     | MAJOR       | Implement job ad language scanner                 |
| FCF violation (no MCF posting)         | MEDIUM     | MAJOR       | Implement FCF checker with countdown              |
| Candidate NRIC exposed unencrypted     | MEDIUM     | MAJOR       | Apply encryption or remove from recruitment       |
| No audit trail for hiring decisions    | MEDIUM     | SIGNIFICANT | Log all stage changes with actor/timestamp/reason |

---

## Decision Points

1. **Resume storage**: Local disk (current pattern) vs S3 (adapter built). Recommend local for MVP, S3 as config option.
2. **NRIC during recruitment**: PDPC discourages pre-hire NRIC collection. Recommend removing from candidate model, collect only during onboarding.
3. **AI screening in MVP**: Recommend deferring to Phase 3. Build manual screening first, layer AI with TAFEP guardrails.
4. **FCF enforcement**: Warn with countdown timer, don't hard-block. Advise, don't prevent.
5. **Hiring manager role**: Use department-based access control, not a new role.
