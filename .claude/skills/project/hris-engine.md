# HRIS Engine Skill

Full HRIS operations: payroll, leave, claims, attendance, shifts, employee lifecycle.

## Module Map

| Module      | Router                           | Models                                                                                                          | Service                                                         | Frontend                                        |
| ----------- | -------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------- |
| Payroll     | `api/routers/payroll.py`         | PayrollRun, Payslip, PayslipItem, PayslipLineItem, CpfYtdRecord, TaxFiling, PayItem, PayScheme, PayslipSettings | `services/payroll_calculator.py`, `services/statutory_files.py` | `/payroll`, `/payroll/[id]`, `/my-payslips`     |
| Leave       | `api/routers/leave.py`           | LeaveTypeConfig, LeaveApplication, PublicHoliday, LeavePolicy, LeavePolicyEntitlement, LeaveEncashment          | —                                                               | `/leave`                                        |
| Claims      | `api/routers/claims.py`          | ClaimCategory, ClaimGroup, Claim, ClaimItem, ClaimAuditEntry                                                    | —                                                               | `/claims`                                       |
| Attendance  | `api/routers/attendance.py`      | AttendanceSettings, AttendanceRecord, TimesheetApproval                                                         | —                                                               | `/attendance`                                   |
| Shifts      | `api/routers/shifts.py`          | ShiftTemplate, ShiftAssignment, ShiftPublish                                                                    | —                                                               | `/shifts`                                       |
| Employee    | `api/routers/employees.py`       | Employee (30+ fields), SalaryComponent, EmergencyContact, EmploymentEvent, EmployeeDocument, PdpaAccessLog      | —                                                               | `/employees`, `/employees/[id]`                 |
| Appraisals  | `api/routers/appraisals.py`      | AppraisalTemplate, AppraisalPeriod, AppraisalReview                                                             | —                                                               | `/appraisals`, `/my-appraisals`                 |
| Projects    | `api/routers/projects.py`        | Project, ProjectAssignment, ProjectTimesheet, ProjectAllocation                                                 | —                                                               | `/projects`, `/projects/[id]`, `/my-timesheets` |
| Inventory   | `api/routers/inventory.py`       | InventoryLocation, InventoryCategory, InventoryItem, InventoryRequest, InventoryMovement                        | —                                                               | `/inventory`, `/inventory/requests`             |
| Recruitment | `api/routers/recruitment.py`     | JobListing, Candidate, Interview, InterviewFeedback                                                             | —                                                               | `/recruitment`, `/recruitment/[id]`             |
| Reports     | `api/routers/reports.py`         | — (aggregation queries, no dedicated models)                                                                    | —                                                               | `/reports`                                      |
| Approvals   | `api/routers/approval_groups.py` | ApprovalGroup, ApprovalGroupMember                                                                              | —                                                               | `/settings/approval-groups`                     |
| Onboarding  | `api/routers/onboarding.py`      | OnboardingTemplate, OnboardingModule, OnboardingStep, OnboardingAssignment, OnboardingStepProgress, PreboardingTaskInstance | `services/onboarding_parser.py`                    | `/employees` (Onboarding tab), `/my-onboarding` |

## CRUD Pattern — dataflow_crud (Mandatory)

All routers use `dataflow_crud` for single-record operations (~23x faster than WorkflowBuilder):

```python
from hr_advisory.services import dataflow_crud

# Create
record = dataflow_crud.create("PayrollRun", {"company_id": 1, "period_start": "2026-04-01"})

# Read
record = dataflow_crud.read("PayrollRun", run_id)  # Returns None if not found

# List with filter
records = dataflow_crud.list_records("PayrollRun", {"company_id": 1, "status": "draft"})

# Update
dataflow_crud.update("PayrollRun", run_id, {"status": "approved"})

# Delete
dataflow_crud.delete("PayrollRun", run_id)
```

## Router Endpoint Template

Every endpoint follows: auth → tenant → validate → execute → respond.

```python
@router.post("/endpoint")
async def handler(request: Request, current_user: dict = Depends(require_role("owner", "hr_manager"))) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    # ... validate inputs (NaN check, length check)
    # ... execute business logic
    # ... return result
```

## Status Machines

| Entity            | States                                                             | Key Transition Rules                                                          |
| ----------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| PayrollRun        | draft → approved → paid (+ cancelled)                              | Approve: owner only. Cancel approved: owner only.                             |
| LeaveApplication  | pending → approved/rejected/withdrawn/cancelled                    | Approve deducts balance. Cancel restores balance. Remarks required on reject. |
| Claim             | draft → submitted → pending_approval → approved/rejected → paid    | Audit entry on every transition. Paid only via payroll mark-paid.             |
| TimesheetApproval | pending → approved/rejected                                        | Approved OT feeds into payroll.                                               |
| ShiftAssignment   | scheduled → confirmed → completed/cancelled/no_show                | No-show: no pay for that shift.                                               |
| InventoryItem     | available → reserved → issued → acknowledged → returned → disposed | Full lifecycle. reserved/issued require employee_id. Movement audit trail.    |
| InventoryRequest  | pending → approved → issued → acknowledged / rejected              | Approval queue. Issued triggers item state change.                            |
| AppraisalReview   | draft → submitted → reviewed → signed_off                          | Employee submits self-assessment, reviewer scores, sign-off locks.            |
| JobListing        | draft → published → closed                                         | Published listings visible to candidates. Close when position filled.         |
| Candidate         | new → screening → interview → offered → hired / rejected           | Hired triggers employee creation. Each stage can reject.                      |
| ProjectTimesheet  | draft → submitted → approved → rejected                            | Employee submits, manager approves. Approved hours feed cost calculations.    |

## Security Checklist (Every New Endpoint)

1. Auth decorator present (`Depends(get_current_user)` or `require_role`)
2. Company_id from JWT, never from request body
3. Ownership check after every record read (`record.company_id == company_id`)
4. Role-appropriate access (employees see own, admins see company)
5. Input validation (required fields, types, `math.isfinite()` on amounts, length limits)
6. Generic error messages (log details server-side, never `str(exc)` to client)
7. Status transition guard (verify current state before allowing change)
8. PDPA audit logging for encrypted fields (NRIC, bank, salary, work pass)
9. Balance coupling (leave/claims status changes must update balances atomically)

## PII Encryption

```python
from hr_advisory.security.encryption import encrypt_field, decrypt_field, mask_nric, mask_bank_account

# On write: encrypt before storing
updates["nric_fin"] = encrypt_field(nric_value)
updates["nric_fin_last4"] = nric_value[-4:]  # Derive BEFORE encrypting

# On read: decrypt for internal use, mask for display
full_nric = decrypt_field(emp.get("nric_fin", ""))
display_nric = mask_nric(full_nric)  # S****567D

# PDPA audit: log every access
_log_pdpa_access(accessed_by=user_id, company_id=company_id,
                 data_subject_id=emp_id, categories=["nric", "salary"], action="view")
```

## Cross-Module Integration

Payroll pulls from leave, attendance, claims, and projects during calculation:

```
POST /payroll/calculate
  ├── For each employee:
  │   ├── Fetch unpaid leave → leave_deduction_days
  │   ├── Fetch approved timesheet → overtime_hours
  │   ├── Fetch approved claims → approved_claims_total
  │   ├── Fetch approved project timesheets → project_hours (cost allocation)
  │   ├── Fetch pay items (OW/AW) → structured earnings/deductions
  │   └── calculate_employee_payslip(emp, components, period, ...)
  └── On mark-paid: update claims with paid_in_payroll_run_id
```

Recruitment → Employee conversion:

```
POST /recruitment/candidates/{id}/hire
  ├── Validate candidate status == "offered"
  ├── Create Employee record from candidate data
  ├── Transition candidate status → "hired"
  └── Close job listing if all positions filled
```

Inventory approval workflow:

```
POST /inventory/requests
  ├── Employee creates request → status: pending
  ├── Approval group member approves → status: approved
  ├── Admin issues item → item status: issued, request status: issued
  └── Employee acknowledges receipt → item status: acknowledged
```

## Statutory Files

| File         | Format                     | Generator                     |
| ------------ | -------------------------- | ----------------------------- |
| CPF e-Submit | CSV: HEADER/DETAIL/TRAILER | `generate_cpf_esubmit()`      |
| Bank GIRO    | CSV or DBS fixed-width     | `generate_bank_giro(format=)` |
| IR8A         | JSON data structure        | `generate_ir8a_data()`        |
| IR21         | JSON data structure        | `generate_ir21_data()`        |
| Payslip      | HTML (EA s88A compliant)   | `generate_payslip_html()`     |

## Payroll Enhancements

### Pay Items

Pay items define structured earnings and deductions with statutory classification:

- **OW (Ordinary Wages)** vs **AW (Additional Wages)** classification — affects CPF ceiling calculations
- **IR8A codes** — each pay item maps to an IR8A field for year-end tax filing
- Types: `earning`, `deduction`, `employer_contribution`
- Statutory items (CPF, SDL, FWL, SHG) are system-managed and cannot be deleted

### Pay Schemes

Group employees into pay schemes (e.g., "Executive", "Operations") that define which pay items apply and their default amounts. Assigned via `pay_scheme_id` on Employee model.

### Adhoc / Off-Cycle Payroll

Separate payroll runs outside the regular monthly cycle for bonuses, back-pay, or termination pay. Uses same calculation engine but with `run_type: "adhoc"`.

### Payroll Line Items

Granular breakdown of each payslip by pay item. Each `PayslipLineItem` links to a `PayItem` and carries: amount, quantity, rate, OW/AW classification.

### Payslip Settings

Company-level configuration: payslip template, display fields, company logo, statutory disclaimer text.

### Variance Reports

Compare two payroll periods side-by-side. Flags employees with significant changes (>10% by default) in gross, net, or CPF.

### Payroll Simulation

Dry-run calculation without creating a PayrollRun. Returns projected payslips for what-if analysis (salary changes, new hires).

## Leave Enhancements

### Hourly Leave

`LeaveTypeConfig.unit` can be `"days"` or `"hours"`. Hourly leave deducts from balance in hours. Display and balance tracking adapts to unit.

### Encashment

`POST /leave/encashment` converts unused leave balance to cash payment. Creates a `LeaveEncashment` record and feeds into payroll as an earning line item. Requires approval.

### Carry-Forward with Expiry

`LeaveTypeConfig.carry_forward_days` and `carry_forward_expiry_months` control how many days carry over and when they expire. `ensure_leave_balances()` applies carry-forward on new period creation.

### Off-in-Lieu

Compensatory leave earned for working on rest days or public holidays. Created via attendance/shift module, appears as a special leave type with auto-credited balance.

### Earned Leave Distribution

For leave types that accrue (e.g., annual leave), `earned_leave_distribution` controls monthly vs quarterly vs annual accrual. Pro-rated for mid-year joiners.

## Claims Enhancements

### Co-Payment

`ClaimCategory.copayment_pct` — employer pays X%, employee absorbs remainder. Applied automatically during claim calculation.

### Claim Groups

`ClaimGroup` aggregates categories with a shared annual limit. E.g., "Medical Group" with $2,000 cap covering outpatient + dental + specialist.

### Benefits-in-Kind (BIK)

Claim categories flagged `is_bik: true` are reported on IR8A as taxable benefits. Payroll integration pulls BIK totals for tax filing.

### Payroll Integration with Cut-Off

Claims approved before the payroll cut-off date are included in that month's payroll run. `claims_cutoff_day` in company settings (default: 25th).

## Attendance Enhancements

### Lateness / Early Departure Brackets

Configurable deduction brackets in `AttendanceSettings`:

```
lateness_brackets: [
  {"minutes": 15, "deduction": 0},       # grace period
  {"minutes": 30, "deduction": 0.25},     # quarter-day deduction
  {"minutes": 60, "deduction": 0.5},      # half-day deduction
]
```

### Auto Clock-Out

`auto_clockout_hours` in settings — if employee has not clocked out after N hours, system auto-closes the record. Prevents overnight orphan records.

### Today Dashboard

`GET /attendance/today` — real-time view of who is clocked in, who is late, who is absent. Used by the attendance dashboard frontend component.

### Attendance Summary

`GET /attendance/summary?period=YYYY-MM` — monthly summary per employee: total hours, late count, early departure count, overtime hours, absence count.

## Shift Enhancements

### Hourly Rates

`ShiftTemplate.hourly_rate` — base rate for the shift. Overrides employee's default rate when assigned to this shift.

### Multipliers

`ShiftTemplate.rate_multiplier` — e.g., 1.5x for night shifts, 2.0x for public holidays. Applied to hourly rate for payroll cost calculations.

### Break Types

`ShiftTemplate.break_type` — `"paid"` or `"unpaid"`. Unpaid breaks deducted from total shift hours for payroll.

### Publish Workflow

Shifts go through a publish cycle: draft → published. `POST /shifts/publish` publishes a week's roster. Published shifts notify assigned employees. Changes after publish require re-publish.

## Appraisals Module

### Template Builder

`AppraisalTemplate` defines the review structure: sections (e.g., "Goals", "Competencies", "Values"), rating scales (1-5 or custom), weight per section, self-assessment toggle.

### Periods

`AppraisalPeriod` defines review cycles (annual, mid-year, probation). Links to a template. Has `launch_date` and `due_date`.

### Launch and Review Workflow

```
Admin creates period → launches → employees receive self-assessment
  → Employee submits self-assessment (status: submitted)
  → Reviewer adds scores and comments (status: reviewed)
  → Sign-off by both parties (status: signed_off)
```

### Endpoints

- `POST /appraisals/templates` — CRUD for templates (admin)
- `POST /appraisals/periods` — CRUD for periods (admin)
- `POST /appraisals/periods/{id}/launch` — Launch a period (admin)
- `GET /appraisals/my-reviews` — Employee's own reviews
- `PUT /appraisals/reviews/{id}` — Submit/update review (employee or reviewer)
- `POST /appraisals/reviews/{id}/sign-off` — Final sign-off

## Projects Module

### Project CRUD

Projects with: name, code, client, start/end dates, budget, status (active/completed/archived). Budget tracked in dollars with variance alerts.

### Role-Based Hourly Rates

`ProjectAssignment` links employees to projects with a role and hourly rate. Different employees can have different rates on the same project.

### Timesheets (Employee Self-Service)

Employees log hours via `POST /projects/timesheets`. Each entry: project_id, date, hours, description, billable flag. Submitted for manager approval.

### Allocations

`ProjectAllocation` — planned hours per employee per week/month. Used for capacity planning and utilization reports.

### Overhead Costs

Projects can have non-labor costs (materials, licenses, travel) tracked as overhead line items.

### Cost Calculations with Budget Variance

```
Total project cost = Σ(approved_hours × hourly_rate) + overhead_costs
Budget variance = budget - total_cost
Utilization = actual_hours / allocated_hours × 100
```

`GET /projects/{id}/costs` returns breakdown by employee, by month, with budget variance percentage.

## Inventory Module

### Location → Category → Item Hierarchy

- `InventoryLocation` — physical locations (office, warehouse, branch)
- `InventoryCategory` — item types (laptops, furniture, access cards)
- `InventoryItem` — individual tracked items with serial number, purchase date, value

### Lifecycle State Machine

```
available → reserved → issued → acknowledged → returned → available
                                     ↓
                                  disposed
```

Each transition creates an `InventoryMovement` audit record with: item_id, from_status, to_status, employee_id, timestamp, notes.

### Employee Requests with Approval

Employees request items via `POST /inventory/requests`. Requests enter the approval queue (uses ApprovalGroup routing). Approved requests are fulfilled by admin issuing the item.

### Movement Audit Trail

Every status change on an inventory item is recorded in `InventoryMovement`. Full chain of custody from purchase to disposal.

## Recruitment Module

### Job Listings

`JobListing` with: title, department, description, requirements, salary range, employment type, location, status (draft/published/closed). Published listings are visible for candidate applications.

### Candidate Pipeline

```
new → screening → interview → offered → hired
                                  ↓
                              rejected (from any stage)
```

Each stage transition is logged. Candidates carry: name, email, phone, resume_url, source, current_salary, expected_salary, notes.

### Interview Scheduling

`Interview` records: candidate_id, interviewer_id (employee), scheduled_at, type (phone/video/onsite), status, location/meeting_link.

### Feedback

`InterviewFeedback` per interviewer: rating (1-5), strengths, concerns, recommendation (hire/no_hire/maybe), notes. Aggregated for hiring decision.

### Hire-to-Employee Conversion

`POST /recruitment/candidates/{id}/hire` creates an Employee record from candidate data (name, email, phone, department, position, start date, salary). Candidate status transitions to "hired".

## Reports Module

### 11 Report Types

| Report             | Endpoint                       | Data Source                    | Chart Type           |
| ------------------ | ------------------------------ | ------------------------------ | -------------------- |
| Payroll Summary    | `GET /reports/payroll-summary` | PayrollRun + Payslip           | BarChart             |
| CPF Contributions  | `GET /reports/cpf`             | PayslipItem (CPF lines)        | BarChart             |
| Bank Summary       | `GET /reports/banks`           | Payslip (by bank)              | DonutChart           |
| YTD Earnings       | `GET /reports/ytd`             | CpfYtdRecord                   | TrendLine            |
| Payroll Variance   | `GET /reports/variance`        | Two PayrollRun periods         | BarChart             |
| Leave Balance      | `GET /reports/leave`           | LeaveBalance                   | BarChart             |
| Claims Summary     | `GET /reports/claims`          | Claim (by category/status)     | DonutChart           |
| Attendance Summary | `GET /reports/attendance`      | AttendanceRecord               | TrendLine            |
| Employee Directory | `GET /reports/employees`       | Employee (headcount, turnover) | BarChart             |
| Project Costs      | `GET /reports/projects`        | ProjectTimesheet + costs       | BarChart + TrendLine |
| Recruitment Funnel | `GET /reports/recruitment`     | Candidate pipeline stages      | BarChart             |

### Chart Components

- `BarChart` — grouped or stacked, horizontal or vertical
- `DonutChart` — percentage breakdowns with center label
- `TrendLine` — time-series with data points

All charts use the `SimpleChart` component family in the frontend (`components/charts/`).

## Approval Workflows

### Approval Groups

`ApprovalGroup` defines who can approve what. Members are employees with approval authority. Groups are assigned to modules (timesheets, inventory requests, leave, claims).

### Timesheet Approval Queue

`GET /projects/timesheets/pending` — managers see submitted timesheets awaiting approval. `PUT /projects/timesheets/{id}/approve` or `/reject`.

### Inventory Request Approval Queue

`GET /inventory/requests/pending` — approval group members see pending requests. `PUT /inventory/requests/{id}/approve` or `/reject`.

## Rate Limiting

In-memory sliding window rate limiter applied as middleware:

- **Per-company key**: `company:{company_id}` — prevents any single company from overwhelming the system
- **Per-user key**: `user:{user_id}` — prevents individual abuse
- Configurable window size and max requests via environment variables
- Returns `429 Too Many Requests` with `Retry-After` header
- Advisory and auth endpoints have stricter limits than CRUD endpoints

## Frontend Components

### EmployeePicker

Reusable employee selection component used across modules (project assignments, shift assignments, appraisal reviewers, inventory requests). Supports search, multi-select, and department filtering.

### SimpleChart Components

`BarChart`, `DonutChart`, `TrendLine` — lightweight chart components used by the reports module. Accept standardized data format: `{ labels: string[], datasets: { label, data, color }[] }`.

## Demo Seed Data

`services/demo_seed.py` creates realistic demo data across all modules: employees with varied profiles, payroll runs with line items, leave applications, claims, attendance records, shift rosters, appraisal periods with reviews, projects with timesheets, inventory items, job listings with candidates, and approval groups.

## Payroll Reports & Exports (Added 2026-04-06)

| Endpoint                                           | Method | Purpose                                                                     |
| -------------------------------------------------- | ------ | --------------------------------------------------------------------------- |
| `/payroll/reports/cpf-reconciliation?year=&month=` | GET    | Per-employee CPF vs YTD record comparison, flags >$0.01 discrepancies       |
| `/payroll/tax/ir8a-csv`                            | POST   | IRAS AIS CSV (ID/Name/Type/NRIC/DOB/Commencement/Cessation/Gross/Bonus/CPF) |
| `/payroll/tax/appendix-8a/{employee_id}?year=`     | GET    | Benefits-in-kind: housing, car, utilities, club, education, insurance       |
| `/payroll/export?start_date=&end_date=`            | GET    | Full payslip CSV with all statutory columns                                 |
| `/payroll/runs/{id}/payslips/{id}/pdf`             | POST   | Admin payslip PDF download (reportlab, EA s88A)                             |
| `/payroll/my-payslips/{id}/pdf`                    | GET    | Employee self-service payslip PDF                                           |

All exports use `_sanitize_filename()`. All require `owner`/`hr_manager` (except employee self-service PDF).

## Parallel Payroll Runs

Compare Arbor against external HRIS:

- `POST /payroll/parallel/upload` — flexible CSV column matching (BOM-aware, comma/dollar stripping)
- `POST /payroll/parallel/compare` — match by ID or name, tolerances: gross=exact, net/CPF=$1
- Bounded storage: `OrderedDict` max 10, LRU eviction. NaN rejected via `math.isfinite()`.

## Exit Processing

`POST /employees/{employee_id}/exit` with settlement calculation:

1. Pro-rated salary (calendar day method)
2. Leave encashment (unused annual × monthly/26)
3. Notice period payment/deduction (shortfall days × daily rate)
4. Retrenchment benefit (sector-aware calculator)

Creates EmploymentEvent, sets employee inactive. Frontend: lifecycle tab on employee detail page with employment timeline, status card, confirm/extend/exit actions.

## Performance Testing

`tests/performance/test_payroll_performance.py` — 8 tests with deterministic seed (42):

- 200 employees (60% citizen, 20% PR, 10% EP, 10% SP/WP), salaries $2.5k-$15k
- Timing: <30s total, <150ms per employee
- Correctness: CPF non-zero for citizens/PRs, zero for foreigners, SDL in $2-$11.25, FWL only for WP/SP

## Onboarding System (Added 2026-04-07)

### Architecture
- 6 models: OnboardingTemplate (versioned), OnboardingModule (phase-based, role-filterable), OnboardingStep (6 types), OnboardingAssignment (with completion %), OnboardingStepProgress (per-step tracking), PreboardingTaskInstance (pre-Day-1 tasks)
- 28 API endpoints in `api/routers/onboarding.py` covering template CRUD, module/step management, assignment (single + bulk), employee self-service, HR approval, pre-boarding
- Excel parser: `services/onboarding_parser.py` reads 12-sheet LIA template format

### Step Types
- **content**: body text, "Mark as Read"
- **checklist**: JSON items, all must be checked
- **document_upload**: file upload (PDF/JPG/PNG/DOCX, 10MB, UUID filenames, magic-byte validation)
- **policy_acknowledgment**: links to CompanyPolicy, creates PolicyAcknowledgment record
- **form**: structured data collection (bank details, emergency contacts)
- **approval**: HR/manager must approve via `POST /steps/{id}/approve`

### SG Default Template
Seeded via `company_seeding.py` — "Singapore Standard Onboarding" with 5 modules:
1. Company Orientation (welcome, team, IT checklist)
2. Employment Documentation (contract ack, NRIC upload, bank details, emergency contact)
3. Singapore Compliance (CPF info, PDPA consent, WSH awareness)
4. Leave & Benefits (EA entitlements, package overview)
5. Probation & Goals (timeline, 30-60-90 checklist)

### Frontend
- Admin: Employees page Onboarding tab with template builder (create/edit/duplicate/import), assignment tracking with progress bars, "Onboard" button per employee in Directory
- Employee: `/my-onboarding` page with module cards, step-by-step completion, progress card on `/my-dashboard`, nav badge

## Related Docs

- `docs/01-architecture.md` — System architecture with HRIS modules
- `docs/02-api-reference.md` — Complete API reference (all modules)
- `docs/03-security.md` — Security architecture
