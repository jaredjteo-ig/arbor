# API Reference

Base URL: `http://localhost:8000` (development)

All authenticated endpoints require `Authorization: Bearer <token>` header. Tokens are obtained via `/auth/login` or `/auth/register`.

---

## Authentication (`/auth`)

### POST /auth/register

Register a new user account.

**Body**: `{ "email": "...", "password": "...", "name": "...", "company_id": null }`

**Response**: User details + `access_token` + `refresh_token`

| Status | Meaning                  |
| ------ | ------------------------ |
| 200    | Success                  |
| 400    | Validation error         |
| 409    | Email already registered |
| 429    | Rate limited             |

### POST /auth/login

Authenticate with email and password.

**Body**: `{ "email": "...", "password": "..." }`

**Response**: User details + `access_token` + `refresh_token`

| Status | Meaning             |
| ------ | ------------------- |
| 200    | Success             |
| 401    | Invalid credentials |
| 429    | Rate limited        |

### POST /auth/refresh

Exchange a refresh token for a new access token.

**Body**: `{ "refresh_token": "..." }`

**Response**: `{ "access_token": "..." }`

### GET /auth/me

Get the current authenticated user's profile. Requires auth.

### POST /auth/logout

Logout and revoke the current access token. The token's JTI is added to the server-side blocklist so it cannot be reused. Requires auth.

### POST /auth/password-reset-request

Request a password reset. Always returns 200 to prevent email enumeration.

**Body**: `{ "email": "..." }`

### POST /auth/password-reset

Reset password using a valid reset token.

**Body**: `{ "token": "...", "new_password": "..." }`

---

## Advisory (`/advisory`)

### POST /advisory/query

Submit an HR advisory question. Applies the full 13-step safety chain:

1. Input sanitisation
2. Rate limiting
3. Query screening (guardrails -- circumvention/escalation detection)
4. EATP genesis record creation
5. Anti-amnesia constraint injection
6. Domain detection
7. Knowledge base retrieval
8. Citation validation
9. Response generation
10. Confidence escalation check
11. Response content screening
12. Risk-tiered disclaimer
13. Trust chain recording + learning pipeline

**Body**: `{ "query": "...", "company_id": null, "conversation_id": null }`

**Response**:

```json
{
  "query": "...",
  "response": "...",
  "provisions_cited": [
    { "provision_id": "...", "title": "...", "authority_level": "...", "status": "..." }
  ],
  "risk_tier": "green|amber|red",
  "confidence_score": 0.85,
  "disclaimer": { "show": true, "text": "...", "framing": "...", "professional_referral": false },
  "trust_chain": { "session_id": "...", "genesis_fingerprint": "...", "chain_confidence": 0.85, ... },
  "citation_warnings": [],
  "timestamp": "..."
}
```

Requires auth. Rate limited: 10/min, 100/hour.

### POST /advisory/stream

Stream an advisory response word-by-word via Server-Sent Events (SSE). Same safety chain as `/advisory/query`.

**SSE Event Types**:

- `start` -- Query accepted, includes risk tier
- `disclaimer` -- Disclaimer text (if applicable)
- `token` -- Individual word tokens
- `complete` -- Full response with citations and trust chain

Requires auth.

### GET /advisory/history/{conversation_id}

Retrieve conversation history for a given conversation. Requires auth.

---

## Calculator (`/calculator`)

### POST /calculator/cpf

Calculate CPF contributions for an employee.

**Body**:

```json
{
  "gross_salary": 5000,
  "employee_age": 30,
  "citizenship_status": "SC",
  "pr_year": null,
  "monthly_aw": 0,
  "ytd_ow": 0,
  "ytd_aw": 0
}
```

**Response**: Employer contribution, employee contribution, total, OW/AW ceiling handling, rate breakdown.

Requires auth.

### POST /calculator/leave

Calculate leave entitlements based on employment details.

**Body**:

```json
{
  "years_of_service": 3,
  "employment_type": "full_time",
  "leave_type": "annual_leave",
  "citizenship_status": "SC",
  "number_of_children": 0,
  "child_ages": [],
  "child_citizenship": "",
  "child_order": 1
}
```

**Supported leave types**: `annual_leave`, `sick_leave`, `maternity_leave`, `paternity_leave`, `childcare_leave`, `shared_parental_leave`

Requires auth.

### POST /calculator/salary

Break down a salary structure into components (CPF, SDL, levies, net pay, total cost).

**Body**:

```json
{
  "gross_salary": 5000,
  "employee_age": 30,
  "citizenship_status": "sc",
  "pr_year": 3,
  "pass_type": "",
  "sector": "services"
}
```

Requires auth.

---

## Compliance (`/compliance`)

### POST /compliance/check

Run a compliance check across regulatory domains by querying the knowledge base for provision coverage.

**Body**: `{ "company_id": 1, "domains": ["employment_act", "cpf", "foreign_manpower"] }`

**Response**: Per-domain findings, overall status (`compliant` / `review_needed` / `non_compliant`), risk tier, remediation recommendations.

Requires auth.

### GET /compliance/status/{company_id}

Get the latest compliance status with per-domain coverage breakdown.

Requires auth + company access.

### POST /compliance/gap-analysis

Detailed gap analysis comparing KB coverage to requirements. Returns severity classification and remediation recommendations per domain.

**Body**: `{ "company_id": 1, "domains": null }`

Requires auth.

---

## Document (`/document`)

### GET /document/templates

List available document templates. Optional `?category=` filter.

### GET /document/templates/{template_id}

Get a specific template including content and linked provisions.

### POST /document/preview

Preview a document with partial field values. Returns unfilled placeholders for UI highlighting.

**Body**: `{ "template_id": 1, "fields": { "company_name": "Acme" } }`

Requires auth.

### POST /document/generate

Generate a customised document from a template. Returns a `document_id` for download.

**Body**: `{ "template_id": 1, "company_id": 1, "fields": { ... } }`

Requires auth.

### GET /document/download/{document_id}

Download a generated document as plain text. Requires auth.

### GET /document/history

List previously generated documents. Optional `?company_id=` filter. Requires auth.

---

## Knowledge Base (`/kb`)

### GET /kb/acts

List all legislative acts in the knowledge base. No auth required.

### GET /kb/domains

List all HR knowledge domains. No auth required.

### GET /kb/provisions/{provision_id}

Get a specific provision with cross-references, applicability rules, and practical examples. Requires auth.

### POST /kb/query

Query provisions by domain, act, or keyword.

**Body**: `{ "domain_id": null, "act_id": null, "keyword": "overtime", "limit": 50 }`

Requires auth.

---

## Search (`/search`)

### POST /search/semantic

Semantic search with relevance scoring. Ranks results by match location (title > summary > formal text).

**Body**: `{ "query": "annual leave entitlement", "top_k": 10, "domain_id": null, "threshold": 0.7 }`

Requires auth.

### POST /search/fulltext

Full-text search with domain, act, authority level, and date filters. Supports pagination.

**Body**:

```json
{
  "query": "notice period",
  "domain_id": null,
  "act_id": null,
  "authority_level": null,
  "effective_after": null,
  "effective_before": null,
  "page": 1,
  "page_size": 20
}
```

Requires auth.

---

## Company Profile (`/profile`)

### GET /profile/{company_id}

Get the full company profile including workforce composition and completeness score. Requires auth + company access.

### POST /profile/

Create a new company profile.

**Body**: `{ "name": "...", "uen": "...", "sector": "...", "headcount_local": 10, ... }`

Requires auth.

### PUT /profile/{company_id}

Update an existing company profile. Requires auth + company access.

### GET /profile/{company_id}/workforce

Get detailed workforce composition breakdown (local, PR, EP, SP, WP) with local ratio. Requires auth + company access.

---

## Learning Pipeline (`/learning`)

### POST /learning/feedback

Submit feedback on an advisory response (thumbs up/down with optional category).

**Body**: `{ "session_id": "...", "is_positive": true, "category": "accuracy", "domains": [...], "query_snippet": "..." }`

**Categories**: `accuracy`, `completeness`, `clarity`, `relevance`, `timeliness`

Requires auth.

### GET /learning/gaps

List detected knowledge base gaps. Optional `?priority=` filter (`critical`, `high`, `medium`, `low`). Requires auth.

### GET /learning/recommendations

List improvement recommendations from the learning pipeline. Optional `?status=` filter. Requires auth.

### POST /learning/recommendations/{recommendation_id}/review

Approve or reject a recommendation (human-on-the-loop gate). Requires `owner` or `hr_manager` role.

**Body**: `{ "approved": true, "notes": "..." }`

### GET /learning/reports

List monthly learning pipeline reports. Requires `owner` or `hr_manager` role.

### POST /learning/reports/generate

Generate a monthly report aggregating feedback, KB gaps, and recommendations. Requires `owner` or `hr_manager` role.

### Admin Learning Endpoints

All require `owner` or `hr_manager` role:

- `GET /learning/admin/gaps` -- KB gaps with suggested provisions
- `GET /learning/admin/recommendations` -- Full recommendation details
- `POST /learning/admin/recommendations/{id}/apply` -- Apply an approved recommendation
- `GET /learning/admin/patterns` -- Query pattern tracking (frequency, confidence, satisfaction)
- `GET /learning/admin/feedback` -- Feedback summary with category breakdowns
- `GET /learning/admin/report` -- Latest monthly report
- `POST /learning/admin/feedback` -- Admin feedback recording

---

## Admin (`/admin`)

All admin endpoints require `owner` or `hr_manager` role.

### Regulatory Updates

- `POST /admin/updates` -- Create a regulatory update (draft status)
- `GET /admin/updates` -- List updates, optional `?status=` filter
- `GET /admin/updates/{update_id}` -- Get a specific update
- `POST /admin/updates/{update_id}/submit` -- Submit for review
- `POST /admin/updates/{update_id}/approve` -- Approve (human-in-the-loop gate)
- `POST /admin/updates/{update_id}/reject` -- Reject
- `POST /admin/updates/{update_id}/publish` -- Publish (updates KB, generates alerts)

**Update lifecycle**: `draft` -> `in_review` -> `approved` -> `published` (or `rejected`)

### Staleness Tracking

- `GET /admin/staleness/summary` -- Provision staleness status counts
- `GET /admin/staleness/stale` -- Provisions past their review date
- `POST /admin/staleness/review` -- Record that a provision has been reviewed

### Platform Metrics

- `GET /admin/metrics` -- Dashboard data: queries tracked, avg confidence, risk distribution, KB stats, feedback count, pending recommendations, pending/published updates

---

## Payroll (`/payroll`)

### POST /payroll/calculate
Run payroll for all active employees. Creates PayrollRun in draft status with Payslips and PayslipItems. Integrates leave deductions, overtime from timesheets, and approved claims. Requires `owner` or `hr_manager`.

**Body**: `{ "period_start": "2026-03-01", "period_end": "2026-03-31", "pay_date": "2026-03-28", "payroll_type": "monthly" }`

### GET /payroll/runs
List all payroll runs for the company. Requires `owner` or `hr_manager`.

### GET /payroll/runs/{id}
Get payroll run detail with all payslips. Requires `owner` or `hr_manager`.

### POST /payroll/runs/{id}/approve
Approve a draft payroll run. Requires `owner` only.

### POST /payroll/runs/{id}/mark-paid
Mark approved run as paid. Marks all claims as paid. Requires `owner` or `hr_manager`.

### POST /payroll/runs/{id}/cancel
Cancel a non-paid run. Approved runs require `owner` role.

### GET /payroll/my-payslips
Employee's own payslips (confirmed/paid only). Any authenticated user.

### POST /payroll/runs/{id}/cpf-file
Generate CPF e-Submit CSV file for download.

### POST /payroll/runs/{id}/bank-file
Generate bank GIRO file. `?format=generic|dbs|uob|ocbc`

### POST /payroll/tax/generate-ir8a
Generate IR8A data for all employees. `?year=2026`

### POST /payroll/tax/generate-ir21/{employee_id}
Generate IR21 for departing foreign employee.

---

## Leave (`/leave`)

### GET /leave/types
List leave types for company.

### POST /leave/apply
Submit leave application. Auto-validates balance and overlap. Any authenticated user.

**Body**: `{ "leave_type_id": 1, "start_date": "2026-03-24", "end_date": "2026-03-26", "start_half": "full_day", "end_half": "full_day", "reason": "..." }`

### GET /leave/applications
List applications. Employee sees own; admin sees all. `?status=` filter.

### PATCH /leave/applications/{id}/approve
Approve leave. Deducts from balance. Requires manager/admin.

### PATCH /leave/applications/{id}/reject
Reject with required remarks.

### GET /leave/balances/{employee_id}
Leave balance by type for a year. `?year=2026`

### GET /leave/calendar
Team calendar data by month. `?month=3&year=2026`

---

## Claims (`/claims`)

### POST /claims
Create draft claim. Any authenticated user.

### GET /claims
List claims. Employee sees own; admin sees all. `?status=` filter.

### PATCH /claims/{id}/submit
Submit for approval.

### PATCH /claims/{id}/approve
Approve claim. Requires admin.

### POST /claims/{id}/items
Add item to draft claim. Validates category limits.

### POST /claims/{id}/items/{item_id}/receipts
Upload receipt (multipart form, max 10MB, PDF/JPG/PNG).

---

## Attendance (`/attendance`)

### POST /attendance/clock-in
Clock in with optional GPS location. Any authenticated user.

### POST /attendance/clock-out
Clock out. Auto-calculates work hours and overtime.

### GET /attendance/today
Current employee's today record.

### GET /attendance/records
List records. `?employee_id=&month=&year=` filters.

### GET /attendance/summary
Monthly summary: present/absent/late counts, total hours.

### POST /attendance/timesheet/submit
Submit monthly timesheet for approval.

---

## Shifts (`/shifts`)

### GET /shifts/templates
List shift templates. Requires admin.

### GET /shifts/schedule
Weekly schedule grid. `?week_start=2026-03-16&department=engineering`

### POST /shifts/assignments
Create shift assignment. Requires admin.

### POST /shifts/publish
Publish schedule for a week. Creates audit record.

### GET /shifts/my-schedule
Employee's own schedule. `?week_start=`

### GET /shifts/hours
Hours per employee per week. Warns if >44h (EA limit).
