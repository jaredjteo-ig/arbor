# Arbor Full HRIS Roadmap — Single Run

**Scope**: 63 tasks (T141-T203) across 12 milestones. Covers all 83 features from the parity matrix.
**Approach**: One continuous implementation run. No phasing. Build → integrate → harden.
**Baseline**: T001-T140 complete. Advisory engine, calculators, shadow agent, compliance, employee basics, web + mobile frontends all live.

---

## M16: Employee Data Foundation

Everything else depends on richer employee records. Extend the existing Employee model and add supporting models.

### T141: Employee Profile Extensions

Add missing fields to the Employee model that payroll, statutory filing, and employee management all depend on.

**Backend:**

- Add fields to Employee model: `date_of_birth` (date), `nric_fin` (encrypted string), `nric_fin_last4` (string, for display), `gender` (enum: male/female), `marital_status` (enum), `race` (enum: chinese/malay/indian/eurasian/other — needed for Self-Help Group fund routing)
- Add fields: `work_pass_number` (encrypted string), `work_pass_type` (enum: ep/sp/wp/s_pass/ltvp/dp), `work_pass_expiry` (date), `immigration_status` (enum: citizen/pr_year1/pr_year2/pr_year3_plus/foreigner), `immigration_effective_date` (date)
- Add fields: `bank_name` (string), `bank_account_number` (encrypted string), `bank_account_last4` (string), `bank_code` (string — DBS/UOB/OCBC/Maybank/CIMB/HSBC)
- Add fields: `residential_address` (text), `postal_code` (string)
- Add PDPA encryption for sensitive fields using Fernet symmetric encryption (NRIC, bank account, work pass number) — store encrypted, decrypt on read with audit log
- Run DataFlow migration to add columns

**API:**

- Extend PUT `/employees/{id}` to accept new fields
- Extend GET `/employees/{id}` to return new fields (mask NRIC/bank to last 4 digits unless admin)
- Add PDPA access logging: every read of encrypted fields logs who accessed what and when

**Web:**

- Extend employee detail/edit form with new field sections: Personal Details, Immigration & Pass, Banking Details
- Mask sensitive fields by default with "reveal" toggle (admin only)
- Add field-level validation (NRIC format: S/T/F/G + 7 digits + letter, bank code from known list)

**Mobile:**

- Mirror web employee form extensions
- Use flutter_secure_storage for any locally cached sensitive data

**Evidence:**

- [ ] Employee model has all new fields with proper types
- [ ] NRIC, bank account, work pass encrypted at rest
- [ ] API masks sensitive fields for non-admin users
- [ ] PDPA access audit log captures every sensitive field read
- [ ] Web + mobile forms render and validate all fields
- [ ] DataFlow migration runs without errors

---

### T142: Salary Components Model

Replace the single `salary_monthly` field with a structured salary components model that supports allowances, deductions, and variable pay.

**Backend:**

- Create `SalaryComponent` model: `id`, `employee_id` (FK), `component_type` (enum: basic_salary/fixed_allowance/variable_allowance/fixed_deduction/variable_deduction/commission/bonus), `name` (string — e.g. "Transport Allowance", "Union Dues"), `amount` (decimal), `frequency` (enum: monthly/weekly/daily/one_time/per_payroll_run), `is_taxable` (bool), `is_cpf_applicable` (bool — whether subject to CPF OW), `effective_from` (date), `effective_to` (date, nullable), `is_active` (bool)
- Seed common component templates: transport allowance, meal allowance, housing allowance, phone allowance, loan repayment, union dues, insurance deduction, per diem
- Add computed property on Employee: `total_monthly_gross` = sum of active components where frequency=monthly
- Keep existing `salary_monthly` as the canonical basic salary; components are additions/deductions on top
- DataFlow migration for new model

**API:**

- CRUD endpoints for salary components: POST/GET/PUT/DELETE under `/employees/{id}/salary-components`
- GET `/employees/{id}/salary-summary` — returns basic salary + all active components with totals (gross, taxable amount, CPF-applicable amount)
- Validation: at least one basic_salary component must exist; component amounts must be positive for allowances, positive for deductions (stored as absolute values, applied as deductions in payroll)

**Web:**

- Salary components tab on employee detail page
- Add/edit/remove component forms with type, name, amount, frequency, taxable toggle, CPF toggle
- Summary card showing gross breakdown

**Mobile:**

- Employee self-service: view own salary components (read-only, amounts masked by default)

**Evidence:**

- [ ] SalaryComponent model created with all fields
- [ ] CRUD API endpoints working
- [ ] Employee gross calculation aggregates components correctly
- [ ] Web UI shows component management
- [ ] Mobile shows read-only view for employees

---

### T143: Emergency Contacts and Next-of-Kin

**Backend:**

- Create `EmergencyContact` model: `id`, `employee_id` (FK), `name` (string), `relationship` (string), `phone_primary` (string), `phone_secondary` (string, nullable), `email` (string, nullable), `is_next_of_kin` (bool), `priority` (int — 1 = primary contact)
- Allow up to 3 emergency contacts per employee
- DataFlow migration

**API:**

- CRUD endpoints under `/employees/{id}/emergency-contacts`
- Validation: at least one emergency contact required before employee record is "complete"

**Web + Mobile:**

- Emergency contacts section on employee profile
- Add/edit/remove contacts
- "Profile completeness" indicator on employee list (flags missing contacts, bank details, NRIC, etc.)

**Evidence:**

- [ ] EmergencyContact model and API working
- [ ] Web + mobile forms for contact management
- [ ] Profile completeness indicator shows missing data

---

### T144: Employment History

Track job changes, salary revisions, and role transitions within the company.

**Backend:**

- Create `EmploymentEvent` model: `id`, `employee_id` (FK), `event_type` (enum: hired/promoted/transferred/salary_revision/confirmed/resigned/terminated/retrenched/contract_renewed), `event_date` (date), `description` (text), `old_value` (JSON — e.g. {"designation": "Developer", "salary": 5000}), `new_value` (JSON — e.g. {"designation": "Senior Developer", "salary": 6500}), `effective_date` (date), `approved_by` (FK to User, nullable), `notes` (text, nullable)
- Auto-generate events when: salary components change, designation changes, department changes, employment status changes
- DataFlow migration

**API:**

- GET `/employees/{id}/history` — chronological event timeline
- POST `/employees/{id}/history` — manual event entry (for backdating historical records)

**Web:**

- Employment history timeline on employee detail page (vertical timeline, most recent first)
- Event cards showing what changed, when, and who approved

**Mobile:**

- Employee self-service: view own employment history timeline

**Evidence:**

- [ ] EmploymentEvent model and API working
- [ ] Auto-generated events on salary/designation/status changes
- [ ] Timeline UI renders on web and mobile

---

### T145: Employee Document Storage

Store employment-related documents (contracts, certifications, letters, etc.).

**Backend:**

- Create `EmployeeDocument` model: `id`, `employee_id` (FK), `document_type` (enum: contract/offer_letter/ket/certification/warning_letter/termination_letter/nric_copy/work_pass_copy/medical_cert/other), `file_name` (string), `file_path` (string — S3 or local storage path), `file_size` (int), `mime_type` (string), `uploaded_by` (FK to User), `uploaded_at` (datetime), `description` (text, nullable), `is_confidential` (bool)
- File storage: local filesystem in development (`/uploads/documents/`), S3 in production
- Max file size: 10MB per file, accepted types: PDF, JPG, PNG, DOCX
- DataFlow migration

**API:**

- POST `/employees/{id}/documents` — upload document (multipart form)
- GET `/employees/{id}/documents` — list documents
- GET `/employees/{id}/documents/{doc_id}/download` — download file
- DELETE `/employees/{id}/documents/{doc_id}` — soft delete
- Access control: admin sees all; employee sees own non-confidential documents

**Web:**

- Documents tab on employee detail page
- Upload with drag-and-drop, document type selector
- Document list with download/delete actions
- Confidential badge on restricted documents

**Mobile:**

- Document list view with download capability
- Upload from camera or file picker

**Evidence:**

- [ ] EmployeeDocument model and file storage working
- [ ] Upload/download/delete API endpoints
- [ ] Web drag-and-drop upload
- [ ] Mobile upload and download
- [ ] Access control enforced (employee sees own, admin sees all)

---

### T146: Bulk CSV Employee Import

Import employees from CSV (critical for onboarding companies migrating from other systems).

**Backend:**

- CSV parser accepting columns: name, email, designation, department, employment_type, nationality, pass_type, salary_monthly, date_of_birth, nric_fin, bank_name, bank_account_number, start_date, work_pass_number, work_pass_expiry
- Validation: required fields (name, email, salary), email format, salary > 0, no duplicate emails, NRIC format (if provided)
- Two-stage process: (1) parse + validate → return preview with errors flagged, (2) confirm → create employee records
- Generate invitation emails for all imported employees
- Return import summary: created count, skipped count, error details

**API:**

- POST `/employees/import/preview` — upload CSV, return parsed preview with validation results
- POST `/employees/import/confirm` — execute the import after user reviews preview

**Web:**

- Import wizard: (1) upload CSV, (2) column mapping preview (auto-detect), (3) validation results with error highlighting, (4) confirm import
- Download sample CSV template

**Mobile:**

- Not needed on mobile (admin-only workflow, better on desktop)

**Evidence:**

- [ ] CSV parser handles all column types with validation
- [ ] Preview stage shows errors without creating records
- [ ] Confirm stage creates employees and sends invitations
- [ ] Sample CSV template downloadable
- [ ] Import wizard UI on web

---

## M17: Payroll Engine Core

The payroll engine calculates pay for all employees in a company for a given period. Uses the existing calculators (CPF, SDL, FWL) but wraps them in a payroll run workflow.

### T147: PayrollRun, Payslip, PayslipItem Models

Core data models for payroll processing.

**Backend:**

- Create `PayrollRun` model: `id`, `company_id` (FK), `period_start` (date), `period_end` (date), `pay_date` (date), `status` (enum: draft/calculating/review/approved/paid/cancelled), `payroll_type` (enum: monthly/bonus/back_pay/final), `total_gross` (decimal), `total_net` (decimal), `total_employer_cpf` (decimal), `total_employee_cpf` (decimal), `total_sdl` (decimal), `total_fwl` (decimal), `total_shg` (decimal — Self-Help Group), `employee_count` (int), `created_by` (FK to User), `approved_by` (FK to User, nullable), `approved_at` (datetime, nullable), `notes` (text, nullable)
- Create `Payslip` model: `id`, `payroll_run_id` (FK), `employee_id` (FK), `period_start` (date), `period_end` (date), `basic_salary` (decimal), `gross_salary` (decimal), `net_salary` (decimal), `employer_cpf` (decimal), `employee_cpf` (decimal), `sdl` (decimal), `fwl` (decimal), `shg_fund` (string, nullable — CDAC/MBMF/SINDA/ECF), `shg_amount` (decimal), `cpf_ow_used` (decimal — OW amount used for this month), `cpf_aw_used` (decimal), `status` (enum: draft/confirmed/paid)
- Create `PayslipItem` model: `id`, `payslip_id` (FK), `item_type` (enum: basic_salary/allowance/deduction/overtime/bonus/commission/back_pay/no_pay_leave_deduction/employer_cpf/employee_cpf/sdl/fwl/shg), `name` (string), `amount` (decimal), `is_taxable` (bool), `is_cpf_applicable` (bool), `notes` (string, nullable)
- DataFlow migrations for all three models
- Index: payroll_run by (company_id, period_start), payslip by (employee_id, period_start)

**Evidence:**

- [ ] All three models created with proper fields and relationships
- [ ] DataFlow migrations run successfully
- [ ] Models support multi-tenancy (company_id scoping)

---

### T148: Gross-to-Net Payroll Calculation Workflow

The core payroll calculation that processes all employees for a pay period.

**Backend:**

- Create `PayrollCalculationService` (pure Python service, not Kailash workflow — payroll is too critical for LLM involvement):
  1. Fetch all active employees for the company
  2. For each employee:
     a. Calculate basic salary (monthly, or pro-rated for partial months)
     b. Sum all active salary components (allowances, deductions)
     c. Calculate OT pay if attendance records exist
     d. Calculate commission if applicable
     e. Apply no-pay leave deductions if any
     f. **Gross = basic + allowances + OT + commission + bonus - no-pay deductions**
     g. Call CPF calculator (existing) with gross OW, employee age, citizenship/PR status, YTD OW used
     h. Calculate SDL (existing calculator)
     i. Calculate FWL if foreign worker (existing calculator)
     j. Calculate SHG fund based on race + income band
     k. **Net = Gross - Employee CPF - SHG - voluntary deductions**
     l. Create PayslipItems for every line
     m. Create Payslip with totals
  3. Create PayrollRun with aggregated totals
  4. Return PayrollRun in "draft" status for review

- All calculations deterministic — zero LLM involvement
- Rounding: all amounts to 2 decimal places, CPF rounded to nearest dollar per CPF Board rules
- Handle edge cases: employees with $0 salary (unpaid leave), negative net (flag as error, do not process)

**API:**

- POST `/payroll/calculate` — body: `{period_start, period_end, pay_date, payroll_type}` → returns PayrollRun with all Payslips in draft
- POST `/payroll/{run_id}/approve` — move from review → approved
- POST `/payroll/{run_id}/mark-paid` — move from approved → paid
- GET `/payroll/runs` — list all payroll runs for company
- GET `/payroll/runs/{run_id}` — get run with all payslips
- GET `/payroll/runs/{run_id}/payslips/{payslip_id}` — single payslip with all items

**Evidence:**

- [ ] Payroll calculation produces correct gross, CPF, SDL, FWL, SHG, net for test employees
- [ ] PayrollRun status transitions work (draft → review → approved → paid)
- [ ] Edge cases handled: partial month, $0 salary, foreign workers
- [ ] All API endpoints return correct data

---

### T149: CPF YTD Tracking and Ceiling Management

CPF has annual ceilings: OW ceiling ($6,800/month as of 2026), AW ceiling ($102,000 - total OW subject to CPF). Must track YTD to avoid over-contribution.

**Backend:**

- Create `CpfYtdRecord` model: `id`, `employee_id` (FK), `year` (int), `month` (int), `ow_subject_to_cpf` (decimal — OW used this month, capped at ceiling), `aw_subject_to_cpf` (decimal), `ytd_ow_total` (decimal — running total), `ytd_aw_total` (decimal), `employer_cpf` (decimal), `employee_cpf` (decimal), `payslip_id` (FK)
- Modify payroll calculation to:
  1. Look up YTD OW total for the employee
  2. Cap current month OW at monthly ceiling ($6,800 as of 2026 — load from rate table, not hardcoded)
  3. Track AW ceiling ($102,000 - YTD OW) for bonus runs
  4. Create CpfYtdRecord after each payroll run
- Handle mid-year PR status changes: if employee becomes PR mid-year, graduated rates apply from the effective date; prior months are not recalculated

**API:**

- GET `/payroll/cpf-ytd/{employee_id}?year=2026` — return YTD CPF breakdown by month

**Evidence:**

- [ ] Monthly OW correctly capped at ceiling
- [ ] AW ceiling correctly calculated for bonus runs
- [ ] YTD record created for every payslip
- [ ] PR status change mid-year applies correct graduated rates

---

### T150: Self-Help Group Funds (CDAC/MBMF/SINDA/ECF)

Singapore citizens contribute to community self-help groups based on race and income.

**Backend:**

- Add SHG fund calculation to payroll service:
  - CDAC (Chinese Development Assistance Council): Chinese race, tiered by monthly wage ($0.50-$1.50-$2.50 etc.)
  - MBMF (Mosque Building & Mendaki Fund): Malay race, tiered by monthly wage
  - SINDA (Singapore Indian Development Association): Indian race, tiered by monthly wage
  - ECF (Eurasian Community Fund): Eurasian race, tiered by monthly wage
- Rate tables: create SHG rate table entries in RateTable model (type: shg_cdac, shg_mbmf, shg_sinda, shg_ecf) with income bands and contribution amounts
- Determination: based on Employee.race + Employee.nationality (citizens only, not PR or foreigners) + monthly total wages
- Add to payslip as a deduction line item

**API:**

- No new endpoints needed — integrated into payroll calculation

**Evidence:**

- [ ] SHG rate tables seeded with current 2026 rates
- [ ] Correct fund selected based on employee race
- [ ] Citizens only (PR and foreigners exempt)
- [ ] Correct tier selected based on monthly wage
- [ ] Shows as line item on payslip

---

### T151: Pay Variations — Proration, Back-pay, Bonus, Commission, No-pay Leave

Handle all the non-standard pay scenarios.

**Backend — Proration:**

- Mid-month hire: salary prorated from start date to end of month. Formula: `monthly_salary * (calendar_days_worked / calendar_days_in_month)` — use calendar day method (most common in SG)
- Mid-month resignation: salary prorated from start of month to last working day
- Detect proration automatically from Employee.start_date and Employee.end_date vs payroll period

**Backend — Back-pay:**

- When salary components are backdated (effective_from in the past), calculate difference for affected months
- Create adjustment payslip items with type=back_pay and reference to original period
- Can be included in regular payroll run or separate back-pay run

**Backend — Bonus / AWS / 13th Month:**

- Support bonus payroll runs (payroll_type=bonus)
- Bonus subject to CPF AW ceiling (not OW ceiling)
- AWS (Annual Wage Supplement / 13th month): typically 1 month basic salary; prorated for <12 months service
- Create PayslipItems with type=bonus, name specifying "AWS" or "Performance Bonus" etc.

**Backend — Commission:**

- Commission from salary components (type=commission, frequency=monthly or per_payroll_run)
- Included in gross salary, subject to CPF (if is_cpf_applicable=true)

**Backend — No-pay Leave Deduction:**

- When leave records with type=unpaid exist for the payroll period, deduct from salary
- Formula: `monthly_salary / working_days_in_month * unpaid_leave_days`
- Create PayslipItem with type=no_pay_leave_deduction

**Evidence:**

- [ ] Mid-month hire proration calculates correctly
- [ ] Mid-month resignation proration calculates correctly
- [ ] Bonus run uses AW ceiling correctly
- [ ] AWS prorated for partial year employees
- [ ] Commission included in gross
- [ ] No-pay leave deduction calculated from leave records

---

### T152: Payroll Dashboard (Web)

The admin interface for running and managing payroll.

**Web:**

- New page: `/payroll` — Payroll dashboard
  - Top: action card "Run Payroll" with period selector (month/year) and pay date picker
  - Below: list of past payroll runs with status badges (draft/review/approved/paid)
  - Each run card shows: period, employee count, total gross, total net, status, actions
- Payroll run detail page: `/payroll/{run_id}`
  - Summary cards: total gross, total CPF (employer + employee), total SDL, total FWL, total SHG, total net
  - Employee payslip list table: name, basic salary, gross, deductions, net, status
  - Click employee → payslip detail with all line items
  - Actions: Approve (moves draft → approved), Mark Paid, Cancel, Download Summary
- Add "Payroll" to sidebar navigation (admin only, between Employees and Compliance)

**Evidence:**

- [ ] Payroll page accessible from sidebar
- [ ] Can initiate a payroll run and see results
- [ ] Payroll run detail shows all payslips with correct totals
- [ ] Status transitions (approve, mark paid) work from UI
- [ ] Past payroll runs listed with filter/sort

---

### T153: Payroll Mobile Screens

**Mobile:**

- Admin: Payroll run list (read-only summary — full management on web)
- Admin: Payroll run detail with employee list
- Employee: "My Payslips" screen (already partially exists — wire to real payroll data)
  - List of payslips by period
  - Payslip detail with all line items
  - Download PDF button

**Evidence:**

- [ ] Admin can view payroll runs on mobile
- [ ] Employees can view own payslips with full itemization
- [ ] PDF download works on mobile

---

### T154: Employee Payslip View

Self-service payslip access for employees on web.

**Web:**

- Update `/my-leave` area or add `/my-payslips` page
  - List of payslips (most recent first)
  - Payslip detail view: employer name, employee name, period, all items grouped by type (earnings, deductions, employer contributions), gross, net
  - Download PDF button
  - "This payslip is computer-generated" footer
- Employee can only see own payslips; admin can see all

**API:**

- GET `/payroll/my-payslips` — employee's own payslips across all runs
- GET `/payroll/my-payslips/{payslip_id}` — single payslip detail

**Evidence:**

- [ ] Employee can view own payslip list
- [ ] Payslip detail shows all line items correctly grouped
- [ ] Admin can view any employee's payslips
- [ ] Access control enforced (employee sees only own)

---

## M18: Payslips, Bank Files & Reports

### T155: EA s88A Compliant Payslip Generation

Generate itemised payslips that meet Employment Act Section 88A requirements.

**Backend:**

- Payslip must include (per EA s88A + MOM guidelines):
  1. Employer name and address
  2. Employee name and NRIC/FIN (masked)
  3. Date of payment
  4. Basic salary for the period
  5. Start and end date of salary period
  6. Allowances paid (itemised: transport, meal, etc.)
  7. Any additional payments (OT, bonus, commission — with period and calculation basis for OT)
  8. Deductions (itemised: employee CPF, SHG fund, loan repayments, etc.)
  9. Overtime hours, pay rate, and total OT pay (if applicable)
  10. Net salary paid
  11. Employer CPF contribution (for reference)
  12. Mode of payment
- Create `PayslipGenerator` service that formats payslip data into the required structure
- Generate both JSON (for rendering) and PDF

**PDF Generation:**

- Use reportlab or weasyprint for PDF creation
- Template: clean layout with company logo (if uploaded), header with company/employee info, itemised table, footer with disclaimers
- A4 format, printable

**API:**

- GET `/payroll/payslips/{payslip_id}/pdf` — returns PDF file
- POST `/payroll/runs/{run_id}/generate-payslips` — batch generate all PDFs for a run

**Evidence:**

- [ ] Payslip contains all EA s88A required fields
- [ ] PDF renders cleanly on A4
- [ ] Batch generation works for all employees in a run
- [ ] OT section includes hours, rate, and calculation basis

---

### T156: Payslip Email Delivery

**Backend:**

- Add email delivery to payslip workflow
- After payroll run is marked "paid", option to email payslips to all employees
- Email template: subject "Your payslip for [Month Year]", body with basic summary (gross, net, pay date), PDF attachment
- Use existing SendGrid integration
- Track delivery status: `payslip_emailed_at` field on Payslip model
- Batch send with rate limiting (avoid SendGrid throttling)

**API:**

- POST `/payroll/runs/{run_id}/email-payslips` — send payslips to all employees in the run
- GET `/payroll/runs/{run_id}/email-status` — delivery status per employee

**Web:**

- "Email Payslips" button on payroll run detail page (only when status=paid)
- Delivery status indicators (sent/failed/pending)

**Evidence:**

- [ ] Payslip emails sent with PDF attachment
- [ ] Email template includes basic salary summary
- [ ] Batch sending with rate limiting works
- [ ] Delivery status tracked and visible in UI

---

### T157: Bank GIRO File Generation

Generate bank payment files in the formats required by Singapore banks.

**Backend:**

- Create `BankFileGenerator` service supporting formats:
  - DBS GIRO (NETS format): fixed-width text file with header, detail, trailer records
  - UOB GIRO: CSV format with specific column layout
  - OCBC GIRO: fixed-width format
  - Generic GIRO: CSV format that works with most banks
- File content: employee name, bank code, account number, payment amount (net salary), reference (payroll period)
- Include PayNow reference for banks that support PayNow business payments
- Validation: all employees in the run must have bank details, flag any missing

**API:**

- POST `/payroll/runs/{run_id}/bank-file?format=dbs` — generate bank file for the run
- Returns downloadable file

**Web:**

- "Generate Bank File" button on payroll run detail page (when status=approved or paid)
- Bank format selector dropdown
- Warning if any employees have missing bank details

**Evidence:**

- [ ] DBS GIRO file format matches bank specification
- [ ] UOB and OCBC formats generate correctly
- [ ] Missing bank details flagged before generation
- [ ] File downloads from UI

---

### T158: Payroll Reports

Generate standard payroll reports.

**Backend:**

- Create report generators:
  1. **Payroll Summary Report**: per-run summary with totals by department, by employment type; gross, CPF (employer + employee), SDL, FWL, SHG, net
  2. **YTD Report**: per-employee cumulative totals for the year; gross earnings, CPF contributions, tax-relevant totals; useful for IR8A preparation
  3. **Payment Reconciliation Report**: per-run bank payment reconciliation; employee name, bank, account, amount paid, payment reference
- Output formats: JSON (for UI rendering) + CSV (for download) + PDF (for printing)

**API:**

- GET `/payroll/reports/summary?run_id={id}` — payroll summary
- GET `/payroll/reports/ytd?year=2026` — YTD report for all employees
- GET `/payroll/reports/reconciliation?run_id={id}` — payment reconciliation
- All endpoints accept `?format=json|csv|pdf` query parameter

**Web:**

- Reports tab on payroll page
- Report selector with date range/period filters
- Preview in browser + download buttons (CSV, PDF)

**Evidence:**

- [ ] Summary report aggregates correctly by department and type
- [ ] YTD report matches sum of individual payslips
- [ ] Reconciliation report matches bank file amounts
- [ ] CSV and PDF downloads work

---

## M19: Tax & Statutory File Generation

### T159: CPF e-Submit File Generation

Generate the CPF contribution file in the format required by CPF Board's e-Submit portal.

**Backend:**

- CPF Board e-Submit file format (CSV):
  - Header: employer CPF account number, payment year/month, number of employees
  - Detail rows: employee NRIC/FIN, employee name, OW subject to CPF, AW subject to CPF, employer CPF, employee CPF, total CPF
  - Amounts in dollars and cents (2 decimal places)
- Source data from PayrollRun for the month
- Validation: all employees must have NRIC/FIN; CPF amounts must match sum of employer + employee contributions
- CPF submission reference number tracking: add `cpf_submission_ref` to PayrollRun

**API:**

- POST `/payroll/runs/{run_id}/cpf-file` — generate CPF e-Submit file
- Returns downloadable CSV file

**Web:**

- "Generate CPF File" button on payroll run detail page
- Pre-generation validation check (missing NRICs, amount mismatches)
- Download button for generated file
- Checkbox to mark "CPF submitted" with date

**Evidence:**

- [ ] File format matches CPF Board e-Submit specification
- [ ] Amounts match payroll calculation
- [ ] Missing NRIC flagged before generation
- [ ] Submission status tracked

---

### T160: IR8A Tax Filing Auto-Generation

Generate IR8A data for annual IRAS tax filing.

**Backend:**

- IR8A requires per-employee annual tax data:
  - Employment income (basic salary, bonus, director fees)
  - Benefits in kind (Appendix 8A — separate task)
  - Employer CPF contributions
  - Exempt income, pension
  - Employee voluntary CPF contributions
  - Gains from stock options (Appendix 8B — deferred)
- Source: aggregate all PayslipItems for the tax year (1 Jan - 31 Dec)
- Create `TaxFiling` model: `id`, `company_id` (FK), `employee_id` (FK), `tax_year` (int), `filing_type` (enum: ir8a/appendix_8a/ir21), `data` (JSON — the filing data), `status` (enum: draft/submitted), `submitted_date` (date, nullable)
- Generate IR8A in IRAS AIS format (XML) for potential future direct submission
- Also generate human-readable PDF for employee reference

**API:**

- POST `/payroll/tax/generate-ir8a?year=2026` — generate IR8A for all employees
- GET `/payroll/tax/ir8a/{employee_id}?year=2026` — get individual IR8A data
- GET `/payroll/tax/ir8a/{employee_id}/pdf?year=2026` — download IR8A PDF

**Web:**

- Tax filing section on payroll page
- "Generate IR8A" button with year selector
- Per-employee IR8A preview and PDF download
- Bulk download all IR8A PDFs as ZIP

**Evidence:**

- [ ] IR8A data aggregates correctly from payslips
- [ ] All required IRAS fields populated
- [ ] PDF format matches IR8A form layout
- [ ] Bulk generation and download works

---

### T161: Appendix 8A (Benefits in Kind)

Generate Appendix 8A for employees who receive non-cash benefits.

**Backend:**

- Appendix 8A covers: housing, car, utilities, furniture, entertainment, leave passage, education, insurance, club membership, other benefits
- Create `BenefitInKind` model: `id`, `employee_id` (FK), `benefit_type` (enum matching IRAS categories), `description` (string), `annual_value` (decimal), `tax_year` (int)
- Include in IR8A generation: sum of all benefits in kind for the year
- Generate Appendix 8A form data in IRAS format

**API:**

- CRUD endpoints for benefits in kind under `/employees/{id}/benefits-in-kind`
- Include in IR8A tax filing generation

**Web:**

- Benefits in kind management on employee detail page
- Auto-included in IR8A generation

**Evidence:**

- [ ] BenefitInKind model and CRUD working
- [ ] Benefits aggregated correctly in IR8A
- [ ] Appendix 8A form data generated

---

### T162: IR21 (Departing Foreign Employees)

Generate IR21 tax clearance data for foreign employees leaving the company.

**Backend:**

- IR21 required for: EP/SP/WP holders who cease employment or are leaving Singapore
- Must be filed at least 1 month before employee's last day (MOM/IRAS requirement)
- IR21 data: same income fields as IR8A but for partial year + outstanding income + bonus provisions
- Create workflow: when a foreign employee's end_date is set, auto-flag for IR21 processing
- Must withhold all monies due until IRAS clearance received

**API:**

- POST `/payroll/tax/generate-ir21/{employee_id}` — generate IR21 for departing foreign employee
- GET `/payroll/tax/ir21/{employee_id}/pdf` — download IR21 PDF

**Web:**

- IR21 section in tax filing page
- Auto-alert when foreign employee end_date is set
- IR21 form preview and PDF download
- Status tracking (pending, filed, cleared)

**Evidence:**

- [ ] IR21 generates correctly for departing foreign employees
- [ ] Auto-flag on end_date trigger
- [ ] PDF matches IR21 form layout
- [ ] Status tracking works

---

## M20: Leave Management System

Extend the existing leave calculator and balance tracking into a full leave management workflow.

### T163: Leave Type Configuration

**Backend:**

- Create `LeaveType` model: `id`, `company_id` (FK), `name` (string), `code` (string — e.g. "AL", "SL", "ML"), `category` (enum: statutory/company/custom), `is_paid` (bool), `is_pro_ratable` (bool), `default_days` (decimal — supports half days), `max_carry_forward` (decimal), `carry_forward_expiry_months` (int, nullable), `requires_attachment` (bool — e.g. MC for sick leave), `min_service_months` (int — eligibility), `applicable_gender` (enum: all/male/female, nullable), `is_active` (bool)
- Seed statutory leave types on company creation:
  - Annual Leave (7 days Y1, +1/year, max 14 — from existing calculator)
  - Sick Leave (14 days outpatient after 6 months)
  - Hospitalisation Leave (60 days inclusive of sick leave)
  - Maternity Leave (16 weeks GPML — female only)
  - Paternity Leave (4 weeks GPPL — male only)
  - Childcare Leave (6 days if child <7)
  - Extended Childcare Leave (2 days if child 7-12)
  - Shared Parental Leave (4 weeks)
  - Adoption Leave (12 weeks)
  - NS Leave (make-up pay — male citizens/PR only)
  - Unpaid Leave (0 days default, no limit)
  - Compassionate Leave (company discretion, default 3 days)
  - Marriage Leave (company discretion, default 3 days)
  - Study/Exam Leave (company discretion, default 0)
  - Off-in-Lieu / TOIL (accrued from overtime)

**API:**

- CRUD for leave types: GET/POST/PUT/DELETE `/leave/types`
- Company can customize days, carry-forward rules, and add custom types

**Web:**

- Leave settings page (admin): manage leave types, configure days and rules
- Read-only view for employees

**Evidence:**

- [ ] All statutory leave types seeded on company creation
- [ ] Custom leave types can be created
- [ ] Days, carry-forward, eligibility rules configurable
- [ ] API CRUD works

---

### T164: Leave Application and Approval Workflow

**Backend:**

- Create `LeaveApplication` model: `id`, `employee_id` (FK), `leave_type_id` (FK), `start_date` (date), `end_date` (date), `start_half` (enum: full_day/first_half/second_half), `end_half` (enum: full_day/first_half/second_half), `total_days` (decimal — calculated), `reason` (text), `attachment_path` (string, nullable — for MC), `status` (enum: pending/approved/rejected/cancelled/withdrawn), `applied_at` (datetime), `reviewed_by` (FK to User, nullable), `reviewed_at` (datetime, nullable), `reviewer_remarks` (text, nullable)
- Auto-calculate total_days: count business days between start and end, subtract weekends and public holidays, apply half-day rules
- Validation:
  - Sufficient leave balance
  - No overlapping applications
  - Minimum notice period (configurable per leave type)
  - Attachment required for sick leave > 1 day
  - Maternity/paternity: check eligibility conditions
- State machine: pending → approved/rejected; pending → withdrawn (by employee); approved → cancelled (by admin, with balance restoration)
- On approval: deduct from LeaveBalance
- On cancellation/withdrawal: restore balance

**API:**

- POST `/leave/apply` — submit application
- GET `/leave/applications` — list (employee: own; manager: team; admin: all)
- PATCH `/leave/applications/{id}/approve` — approve with optional remarks
- PATCH `/leave/applications/{id}/reject` — reject with required remarks
- PATCH `/leave/applications/{id}/withdraw` — employee withdraws own pending application
- PATCH `/leave/applications/{id}/cancel` — admin cancels approved leave

**Evidence:**

- [ ] Leave application calculates total days correctly (excluding weekends, holidays)
- [ ] Half-day applications work
- [ ] Balance validation prevents over-application
- [ ] Status transitions work correctly
- [ ] Balance deducted on approval, restored on cancellation

---

### T165: Multi-Level Approval and Manager Assignment

**Backend:**

- Add `reporting_manager_id` (FK to Employee, nullable) to Employee model — for approval routing
- Approval routing: application goes to the employee's reporting manager; if no manager, goes to company admin
- Multi-level: optionally configure approval chain (e.g., team lead → department head → HR) via `ApprovalChain` model: `id`, `company_id`, `level` (int), `approver_role` (enum) or `approver_id` (FK), `leave_day_threshold` (decimal — e.g., >5 days needs second approval)
- Notifications: email the approver when a new application arrives; email the employee when approved/rejected

**API:**

- PUT `/employees/{id}/reporting-manager` — set reporting manager
- CRUD for approval chains: `/leave/approval-chains`

**Web:**

- Reporting manager selector on employee profile
- Approval chain configuration in leave settings
- Pending approvals badge in sidebar for managers

**Evidence:**

- [ ] Applications route to correct approver
- [ ] Multi-level approval triggers when threshold met
- [ ] Email notifications sent to approvers and employees
- [ ] Pending approvals count visible for managers

---

### T166: Leave Rules — Carry-Forward, Encashment, Proration

**Backend — Carry-Forward:**

- At year end (or configurable date), calculate unused leave
- Carry forward up to `max_carry_forward` days from LeaveType
- Carried-forward days expire after `carry_forward_expiry_months` if set
- Create `LeaveCarryForward` record: employee, year, leave_type, days_carried, expiry_date

**Backend — Encashment:**

- Convert unused leave days to cash at daily rate: `monthly_salary / working_days_per_month`
- Create encashment request with approval workflow
- On approval, create PayslipItem in next payroll run

**Backend — Proration:**

- Mid-year joiners: prorate annual leave based on months remaining
- Formula: `annual_entitlement * (remaining_months / 12)`, rounded to nearest 0.5 day
- Use existing leave calculator logic

**API:**

- POST `/leave/year-end-process?year=2026` — process carry-forward for all employees
- POST `/leave/encashment` — request encashment
- GET `/leave/balances/{employee_id}?year=2026` — balance with carry-forward and used breakdown

**Evidence:**

- [ ] Carry-forward calculates correctly
- [ ] Expiry enforcement works
- [ ] Encashment creates payroll item
- [ ] Proration matches existing calculator results

---

### T167: Leave Calendar and Public Holidays

**Web:**

- Team leave calendar: `/leave/calendar`
  - Monthly calendar view showing who is on leave
  - Colour-coded by leave type
  - Public holidays marked
  - Filter by department, leave type
  - Click date to see details
- Employee can see team members' leave (names only, not leave type details — privacy)

**Backend — Public Holidays:**

- Create `PublicHoliday` model: `id`, `name` (string), `date` (date), `year` (int), `is_gazetted` (bool)
- Seed Singapore gazetted holidays for 2026 and 2027:
  - New Year's Day, Chinese New Year (2 days), Good Friday, Hari Raya Puasa, Labour Day, Vesak Day, Hari Raya Haji, National Day, Deepavali, Christmas Day
- Public holidays excluded from leave day calculation
- Admin can add company-specific holidays (e.g., company anniversary)

**API:**

- CRUD for public holidays: `/leave/public-holidays`
- GET `/leave/calendar?month=3&year=2026&department=engineering` — calendar data

**Mobile:**

- Calendar view (month view, simplified — list format)
- Public holiday list

**Evidence:**

- [ ] Calendar shows team leave accurately
- [ ] Public holidays seeded and excluded from leave calculations
- [ ] Custom holidays supported
- [ ] Department filter works

---

### T168: Leave Policy by Employee Group

**Backend:**

- Create `LeavePolicy` model: `id`, `company_id`, `name` (string — e.g. "Full-time Policy", "Part-time Policy", "Management Policy"), `is_default` (bool)
- Create `LeavePolicyEntitlement` model: `id`, `policy_id` (FK), `leave_type_id` (FK), `days` (decimal), `carry_forward_days` (decimal)
- Add `leave_policy_id` (FK) to Employee model — defaults to company default policy
- When calculating leave balance, use policy entitlement instead of leave type defaults
- This allows: management gets 21 days annual leave, staff gets 14, part-time gets 7

**API:**

- CRUD for leave policies: `/leave/policies`
- Assign policy to employee: PATCH `/employees/{id}` with `leave_policy_id`

**Web:**

- Leave policy management page (admin)
- Policy assignment on employee profile
- Policy comparison view

**Evidence:**

- [ ] Different policies give different entitlements
- [ ] Default policy applied to new employees
- [ ] Policy override works per employee

---

### T169: Leave Pages (Web)

**Web:**

- `/leave` — Leave hub for admin:
  - Pending approvals list (with approve/reject actions)
  - Team leave summary (on leave today, upcoming)
  - Quick stats: total pending, approved this month, rejected
- `/leave/apply` — Employee leave application form:
  - Leave type selector, date range picker, half-day toggles, reason, attachment upload
  - Real-time balance check (shows remaining days as user selects dates)
  - Conflict warning (overlapping leave, blackout dates)
- `/leave/my-leave` — Employee view:
  - Leave balance cards by type (used/remaining/pending)
  - Application history with status
  - Cancel/withdraw pending applications
- `/leave/settings` — Admin leave configuration (types, policies, approval chains)
- Add "Leave" to sidebar navigation

**Evidence:**

- [ ] All leave pages accessible
- [ ] Application form with real-time balance check
- [ ] Approval workflow from pending list
- [ ] Employee self-service balance and history view

---

### T170: Leave Mobile Screens

**Mobile:**

- Leave balance summary (card view)
- Apply for leave (form with date picker, type selector)
- My applications list with status
- Manager: approval list with approve/reject actions
- Leave calendar (month view, simplified)

**Evidence:**

- [ ] All leave flows work on mobile
- [ ] Apply and approve work end-to-end
- [ ] Balance displays correctly

---

## M21: Claims & Expenses

### T171: Claims Models and API

**Backend:**

- Create `ClaimCategory` model: `id`, `company_id`, `name` (string — "Transport", "Meals", "Medical", "Accommodation", "Office Supplies", "Other"), `monthly_limit` (decimal, nullable), `per_claim_limit` (decimal, nullable), `requires_receipt` (bool, default true), `is_active` (bool)
- Create `Claim` model: `id`, `employee_id` (FK), `claim_month` (date — the month this claim is for), `status` (enum: draft/submitted/pending_approval/approved/rejected/paid/cancelled), `total_amount` (decimal), `submitted_at` (datetime), `reviewed_by` (FK, nullable), `reviewed_at` (datetime, nullable), `reviewer_remarks` (text, nullable), `paid_in_payroll_run_id` (FK, nullable)
- Create `ClaimItem` model: `id`, `claim_id` (FK), `category_id` (FK), `description` (string), `amount` (decimal), `receipt_date` (date), `receipt_paths` (JSON array — up to 5 file paths), `notes` (text, nullable)
- Seed default claim categories on company creation
- DataFlow migrations

**API:**

- CRUD for claim categories: `/claims/categories`
- POST `/claims` — create claim (draft)
- PATCH `/claims/{id}/submit` — submit for approval
- PATCH `/claims/{id}/approve` — approve
- PATCH `/claims/{id}/reject` — reject
- GET `/claims` — list (employee: own; manager: team pending; admin: all)
- GET `/claims/{id}` — detail with items
- CRUD for claim items: `/claims/{id}/items`
- POST `/claims/{id}/items/{item_id}/receipts` — upload receipt (multipart, up to 5 per item)
- Validation: total amount within limits, receipts required if category requires them

**Evidence:**

- [ ] All models created
- [ ] CRUD and status transitions work
- [ ] Receipt upload stores files correctly
- [ ] Limit validation enforced
- [ ] Claim routing to correct approver

---

### T172: Claims Approval, Audit Trail, and Payroll Integration

**Backend — Approval:**

- Same approval routing as leave (reporting manager → admin)
- Multi-level approval if total amount exceeds threshold (configurable)
- Email notifications on submission and approval/rejection

**Backend — Audit Trail:**

- Create `ClaimAuditEntry` model: `id`, `claim_id` (FK), `action` (enum: created/submitted/approved/rejected/cancelled/paid), `actor_id` (FK to User), `timestamp` (datetime), `details` (JSON)
- Auto-log every status change

**Backend — Payroll Integration:**

- Approved claims for a month are included in the payroll run
- Create PayslipItems with type=claim_reimbursement for each approved claim
- Mark claim as `paid` and link to `paid_in_payroll_run_id`
- Claims reimbursement is not subject to CPF (not salary/wage)

**API:**

- GET `/claims/{id}/audit-trail` — full history
- GET `/payroll/claims-pending?month=2026-03` — claims ready for payroll inclusion

**Evidence:**

- [ ] Approval workflow routes correctly
- [ ] Audit trail captures all state changes
- [ ] Approved claims appear in payroll calculation
- [ ] Claims marked as paid after payroll run

---

### T173: Claims Pages (Web + Mobile)

**Web:**

- `/claims` — Claims hub:
  - Employee: submit new claim, view own claims with status
  - Manager: pending claims for approval with approve/reject
  - Admin: all claims, category management, limit configuration
- Claim form: add items with category, amount, description, date; upload receipts per item (drag-and-drop, up to 5)
- Claim detail: itemised view with receipt thumbnails, audit trail, status timeline

**Mobile:**

- Submit claim with camera receipt capture
- View own claims with status
- Manager: approve/reject from mobile
- Receipt photo upload from camera or gallery

**Add "Claims" to sidebar navigation**

**Evidence:**

- [ ] Claim submission with receipt upload works (web + mobile)
- [ ] Manager approval works (web + mobile)
- [ ] Receipt thumbnails display
- [ ] Camera capture works on mobile

---

## M22: Attendance & Time Tracking

### T174: Attendance Models and API

**Backend:**

- Create `AttendanceRecord` model: `id`, `employee_id` (FK), `date` (date), `clock_in` (datetime, nullable), `clock_out` (datetime, nullable), `clock_in_location` (JSON: {lat, lng, address}, nullable), `clock_out_location` (JSON, nullable), `clock_in_photo` (string — file path, nullable), `clock_out_photo` (string, nullable), `status` (enum: present/absent/late/half_day/on_leave/holiday), `work_hours` (decimal — calculated), `overtime_hours` (decimal — calculated), `remarks` (text, nullable), `is_manual` (bool — true if admin-created, false if clocked)
- Create `AttendanceSettings` model: `id`, `company_id`, `work_start_time` (time — e.g. 09:00), `work_end_time` (time — e.g. 18:00), `grace_period_minutes` (int — late threshold, e.g. 15), `overtime_threshold_minutes` (int — e.g. 30 min after work_end), `require_gps` (bool), `require_photo` (bool), `allowed_locations` (JSON array — [{name, lat, lng, radius_meters}])
- DataFlow migrations

**API:**

- POST `/attendance/clock-in` — body: `{location?, photo?}` — creates record with clock_in time
- POST `/attendance/clock-out` — body: `{location?, photo?}` — updates record with clock_out time
- GET `/attendance/today` — current employee's today record
- GET `/attendance/records?employee_id=&month=&year=` — list records
- GET `/attendance/summary?employee_id=&month=&year=` — monthly summary (present/absent/late days, total hours, OT hours)
- PATCH `/attendance/{id}` — admin correction
- GET/PUT `/attendance/settings` — company attendance settings

**Evidence:**

- [ ] Clock in/out creates/updates records
- [ ] Work hours calculated from clock times
- [ ] Overtime detected from threshold
- [ ] Late status applied based on grace period
- [ ] GPS location captured if enabled

---

### T175: Clock In/Out with GPS and Photo

**Web:**

- Attendance widget on employee dashboard: large "Clock In" / "Clock Out" button
- Current status display (clocked in since HH:MM, or not clocked in)
- GPS capture (browser geolocation API) — show current location on mini map
- Photo capture (webcam via getUserMedia) — take selfie on clock-in/out
- Location validation: if `allowed_locations` configured, warn if outside allowed radius

**Mobile:**

- Prominent clock in/out button on employee home screen
- GPS from device location services
- Camera for photo proof
- Offline support: queue clock-in/out if offline, sync when back online
- Location accuracy indicator

**Evidence:**

- [ ] Clock in/out works on web with GPS + photo
- [ ] Clock in/out works on mobile with GPS + photo
- [ ] Location validation warns when outside allowed area
- [ ] Offline clock-in queues and syncs

---

### T176: Lateness Tracking and Overtime Auto-Calculation

**Backend:**

- On clock-in: if time > work_start_time + grace_period → mark as late
- Lateness minutes = clock_in_time - work_start_time
- On clock-out: if time > work_end_time + overtime_threshold → calculate OT hours
- OT hours = clock_out_time - work_end_time (rounded to nearest 0.5 hour)
- Part IV EA employees: OT rate = 1.5x hourly rate (use existing OT calculator)
- Non-Part IV employees: no statutory OT, but track hours for reporting
- Monthly summary auto-generates: total late count, total OT hours, OT pay estimate

**API:**

- GET `/attendance/lateness?month=&year=` — lateness report
- GET `/attendance/overtime?month=&year=` — overtime report with pay estimates

**Evidence:**

- [ ] Late status correctly determined
- [ ] OT hours calculated from clock-out time
- [ ] Part IV OT pay calculation matches existing calculator
- [ ] Monthly summary aggregates correctly

---

### T177: Timesheet Approval and Attendance Summary

**Backend:**

- Create `TimesheetApproval` model: `id`, `employee_id`, `month` (date), `status` (enum: pending/approved/rejected), `total_work_hours` (decimal), `total_ot_hours` (decimal), `submitted_at` (datetime), `approved_by` (FK), `approved_at` (datetime)
- At month end, employee (or system) submits timesheet for approval
- Manager reviews attendance records + OT hours → approve/reject
- Approved timesheets feed OT hours into payroll

**API:**

- POST `/attendance/timesheet/submit?month=2026-03` — submit for approval
- PATCH `/attendance/timesheet/{id}/approve` — approve
- PATCH `/attendance/timesheet/{id}/reject` — reject
- GET `/attendance/timesheets` — list (employee: own; manager: team)

**Evidence:**

- [ ] Timesheet submission aggregates month's records
- [ ] Manager can approve/reject
- [ ] Approved OT hours available for payroll calculation

---

### T178: Attendance Pages (Web + Mobile)

**Web:**

- `/attendance` — Attendance hub (admin):
  - Today's attendance: who's in, who's late, who's absent
  - Colour-coded status indicators (green=on time, amber=late, red=absent, blue=on leave)
  - Monthly calendar view per employee
  - Attendance summary report with filters
  - Timesheet approval queue
- Employee attendance widget on dashboard (clock in/out)
- Multi-location selector (if company has multiple offices)

**Mobile:**

- Clock in/out (primary action)
- My attendance history
- Manager: team attendance today

**Add "Attendance" to sidebar navigation**

**Evidence:**

- [ ] Today's attendance view shows all employees
- [ ] Colour-coded status indicators work
- [ ] Calendar view renders per-employee attendance
- [ ] Clock in/out on web and mobile

---

## M23: Shift Scheduling

### T179: Shift Models and API

**Backend:**

- Create `ShiftTemplate` model: `id`, `company_id`, `name` (string — "Morning", "Afternoon", "Night", "Split"), `start_time` (time), `end_time` (time), `break_minutes` (int), `work_hours` (decimal — calculated), `colour` (string — hex colour for calendar display), `is_active` (bool)
- Create `ShiftAssignment` model: `id`, `employee_id` (FK), `shift_template_id` (FK), `date` (date), `status` (enum: scheduled/confirmed/completed/cancelled/no_show), `actual_start` (datetime, nullable), `actual_end` (datetime, nullable), `notes` (text, nullable)
- Create `ShiftPublish` model: `id`, `company_id`, `week_start` (date), `published_at` (datetime), `published_by` (FK to User) — tracks when schedules are published
- DataFlow migrations
- Index: shift_assignment by (employee_id, date), (company_id, date)

**API:**

- CRUD for shift templates: `/shifts/templates`
- CRUD for shift assignments: `/shifts/assignments`
- POST `/shifts/publish?week_start=2026-03-16` — publish schedule for the week
- GET `/shifts/schedule?week_start=&department=` — weekly schedule grid
- GET `/shifts/my-schedule?week_start=` — employee's own schedule
- GET `/shifts/availability?date=` — who's available (not on leave, not already assigned)

**Evidence:**

- [ ] Shift templates and assignments created
- [ ] Schedule publishing works
- [ ] Availability check excludes on-leave employees

---

### T180: Shift Calendar UI

**Web:**

- `/shifts` — Shift scheduling page:
  - Weekly grid view: rows = employees, columns = days (Mon-Sun)
  - Each cell shows shift template (colour-coded) or empty
  - Drag-and-drop: drag shift template onto employee+day cell to assign
  - Right-click cell: edit, delete, swap with another employee
  - Availability overlay: grey out cells where employee is on leave
  - Hours counter per employee per week (flag if exceeding 44 hours — EA limit)
  - "Publish" button: notify all affected employees of their schedule
  - Filter by department
- Shift template management (admin settings)

**Mobile:**

- Employee: "My Schedule" — weekly list view with shift times
- Push notification when new schedule published
- Admin: read-only schedule view (editing on web only)

**Add "Shifts" to sidebar navigation**

**Evidence:**

- [ ] Drag-and-drop shift assignment works
- [ ] Leave-integrated availability greys out unavailable cells
- [ ] Hours per employee per week tracked
- [ ] Labour law warning when >44 hours
- [ ] Schedule publishing sends notifications

---

### T181: Shift-Payroll Integration

**Backend:**

- For shift-based employees (part-time, hourly), calculate pay from shift hours:
  - Daily rate = monthly salary / working days per month (or hourly rate if hourly employee)
  - Total pay = sum of shift work_hours \* rate
  - Overtime: hours beyond 8/day or 44/week at 1.5x (Part IV EA employees)
- In payroll calculation:
  - If employee has shift assignments for the period, use shift hours instead of flat monthly salary
  - Create PayslipItems: regular_hours_pay + overtime_pay
- Handle no-show: shift with status=no_show → deduction or no pay for that shift

**Evidence:**

- [ ] Shift-based pay calculated from actual hours
- [ ] Overtime from shifts uses correct thresholds
- [ ] No-show handling works
- [ ] Payslip items reflect shift-based calculation

---

## M24: Employee Lifecycle

### T182: Org Chart

**Backend:**

- Org chart derived from Employee.reporting_manager_id relationships
- API: GET `/employees/org-chart` — returns hierarchical tree structure
- Handle: employees with no manager (top level), circular references (prevent in validation)

**Web:**

- `/employees/org-chart` — Interactive org chart page
  - Tree/hierarchy visualization (top-down)
  - Each node: employee name, designation, department, photo (placeholder if none)
  - Click node: navigate to employee detail
  - Zoom and pan for large organizations
  - Use a lightweight library (e.g., react-organizational-chart or d3-org-chart)

**Evidence:**

- [ ] Org chart renders from reporting manager hierarchy
- [ ] Interactive (click, zoom, pan)
- [ ] Handles missing managers gracefully

---

### T183: Confirmation Workflow

Track probation periods and manage confirmation decisions.

**Backend:**

- Add to Employee model: `probation_months` (int, default 3 or 6), `probation_end_date` (date — calculated from start_date + probation_months), `confirmation_status` (enum: on_probation/confirmed/extended/terminated)
- Create `ConfirmationAction` model: `id`, `employee_id`, `action` (enum: confirm/extend/terminate), `action_date` (date), `new_probation_end` (date, nullable — for extensions), `remarks` (text), `actioned_by` (FK to User)
- Auto-alert: 2 weeks before probation_end_date, send notification to reporting manager and admin
- On confirmation: update status, create EmploymentEvent
- On extension: update probation_end_date, create EmploymentEvent
- On termination: trigger exit process

**API:**

- GET `/employees/probation/due` — employees approaching probation end
- POST `/employees/{id}/confirm` — confirm employee
- POST `/employees/{id}/extend-probation` — extend with new end date
- POST `/employees/{id}/terminate-probation` — terminate

**Web:**

- Probation dashboard widget on admin dashboard (due this month count)
- Probation action form on employee detail
- Confirmation history on employment timeline

**Evidence:**

- [ ] Probation end date calculated correctly
- [ ] Alerts sent 2 weeks before end date
- [ ] Confirm/extend/terminate actions work
- [ ] Employment history updated on action

---

### T184: Exit and Offboarding

**Backend:**

- Create `ExitChecklist` model: `id`, `employee_id`, `checklist_type` (enum: resignation/termination/retrenchment/contract_end), `items` (JSON array of {task, completed, completed_by, completed_at}), `initiated_date` (date), `last_working_day` (date), `status` (enum: in_progress/completed)
- Default checklist items by type:
  - All: return company property, deactivate system access, final salary calculation, update CPF cessation, archive employee documents
  - Resignation: accept resignation letter, serve notice period, handover plan, exit interview
  - Termination: termination letter, termination meeting, severance if applicable
  - Retrenchment: retrenchment notification to MOM, retrenchment benefit calculation, re-employment assistance
  - Foreign workers: IR21 filing, cancel/transfer work pass, IPA cancellation
- Final salary calculation: use existing calculators + pro-rated salary + unused leave encashment + retrenchment benefit (if applicable)
- On exit completion: set employee status to inactive, set end_date

**API:**

- POST `/employees/{id}/initiate-exit` — body: {type, last_working_day} → create checklist
- PATCH `/employees/{id}/exit-checklist/{item_index}/complete` — mark item done
- GET `/employees/{id}/exit-checklist` — get checklist status
- POST `/employees/{id}/final-salary` — calculate final salary

**Web:**

- Exit wizard on employee detail page: select exit type → set last working day → checklist generated
- Checklist view with progress bar, item toggles
- Final salary breakdown display
- "Complete Exit" button when all items done

**Evidence:**

- [ ] Exit checklist generated by type
- [ ] Foreign worker items include IR21 and pass cancellation
- [ ] Final salary calculated correctly
- [ ] Employee set to inactive on completion

---

### T185: Employee Lifecycle Pages

**Web:**

- Enhanced `/employees` page:
  - Status filters: active, on probation, on notice, inactive
  - Profile completeness column (percentage based on filled fields)
  - Quick actions: confirm, initiate exit
- Enhanced employee detail page:
  - Tabs: Profile, Salary, Leave, Documents, History, Exit (if applicable)
  - Profile completeness indicator at top
  - Employment timeline sidebar
- `/employees/org-chart` (from T182)

**Mobile:**

- Enhanced employee list with status indicators
- Employee detail with profile, documents, history tabs

**Evidence:**

- [ ] Employee list shows status filters and completeness
- [ ] Employee detail has all tabs
- [ ] Mobile employee views updated

---

## M25: Cross-Module Integration

### T186: Payroll-Leave Integration

Connect leave records to payroll calculations.

**Backend:**

- During payroll calculation, for each employee:
  1. Query approved leave applications for the payroll period
  2. Unpaid leave: calculate deduction = (monthly_salary / working_days) \* unpaid_leave_days
  3. Sick leave beyond entitlement: treated as unpaid leave
  4. Leave encashment (if approved): add as earnings item
- PayslipItems created: no_pay_leave_deduction (with day count and rate), leave_encashment (if applicable)
- Validation: warn if leave records are incomplete (pending approvals during payroll period)

**Evidence:**

- [ ] Unpaid leave deducted in payroll correctly
- [ ] Leave encashment added as earnings
- [ ] Warning for pending leave during payroll period

---

### T187: Payroll-Attendance Integration

Connect attendance/timesheet data to payroll.

**Backend:**

- During payroll calculation, for each employee:
  1. If approved timesheet exists for the period:
     a. Use total OT hours from timesheet
     b. Calculate OT pay = OT hours _ hourly_rate _ 1.5 (Part IV employees)
     c. Create PayslipItem with type=overtime, amount=OT pay, notes="X hours at Y rate"
  2. If shift-based employee:
     a. Calculate pay from shift hours (T181)
     b. Deduct no-show shifts
- For monthly salaried employees without timesheet, OT is only included if timesheet is submitted and approved

**Evidence:**

- [ ] OT hours from timesheet flow into payslip
- [ ] Shift-based pay calculated correctly
- [ ] Only approved timesheets included

---

### T188: Payroll-Claims Integration

Include approved claims in payroll as reimbursements.

**Backend:**

- During payroll calculation:
  1. Query approved claims for the payroll month
  2. For each approved claim: create PayslipItem with type=claim_reimbursement, amount=claim total, is_taxable=false, is_cpf_applicable=false
  3. Mark claims as paid and link to payroll run
- Claims reimbursement shown separately on payslip (not part of salary/wages, not subject to CPF/tax)

**Evidence:**

- [ ] Approved claims included in payroll
- [ ] Reimbursement not subject to CPF
- [ ] Claims marked as paid after payroll

---

## M26: Shadow Agent HRIS Integration

### T189: Shadow Agent Payroll and Leave Commands

Extend the shadow agent command surface to handle HRIS operations.

**Backend:**

- Add shadow commands:
  - "Run payroll" → navigate to payroll page, pre-fill current month
  - "Show payslip for [employee]" → display payslip detail
  - "My payslip" (employee) → show latest payslip
  - "Apply for leave" → open leave application form
  - "Check my leave balance" → display balance summary
  - "Who's on leave today?" → show today's leave list
  - "Submit my timesheet" → navigate to timesheet submission
- Shadow context enrichment:
  - Dashboard page: payroll status (last run date, next due), pending leave approvals count, employee probation due dates
  - Employee page: compliance completeness (missing NRIC, bank details), leave balance summary
  - Payroll page: missing data warnings (employees without bank details)

**Web:**

- Add HRIS commands to command surface action registry
- Add HRIS annotations to shadow margin on relevant pages
- Shadow briefing card includes payroll/leave/claims status

**Evidence:**

- [ ] HRIS commands work from command surface
- [ ] Shadow margin shows HRIS context on relevant pages
- [ ] Dashboard briefing includes HRIS status

---

### T190: Shadow Agent Claims and Attendance Commands

**Backend:**

- Add shadow commands:
  - "Submit a claim" → open claims form
  - "My claims this month" → display claims summary
  - "Clock in/out" → trigger attendance
  - "My attendance this month" → show summary
  - "Who's late today?" (admin) → show lateness report
  - "Show shift schedule" → navigate to shift page
  - "Upcoming deadlines" → CPF submission date, IR8A deadline, etc.

**Evidence:**

- [ ] Claims and attendance commands work
- [ ] Deadline reminders surface in shadow context

---

## M27: Hardening & Production

### T191: Salary Encryption at Rest

**Backend:**

- Implement Fernet symmetric encryption for all salary-related fields:
  - Employee: salary_monthly (already encrypted via T141 for NRIC/bank, extend to salary)
  - SalaryComponent: amount
  - Payslip: basic_salary, gross_salary, net_salary, employer_cpf, employee_cpf
  - PayslipItem: amount
- Encryption key from environment variable `SALARY_ENCRYPTION_KEY`
- Decrypt only on read, with PDPA audit logging
- Ensure payroll calculations work with encrypted fields (decrypt for calculation, re-encrypt for storage)
- Database stores encrypted values; all decryption happens in application layer

**Evidence:**

- [ ] Salary fields encrypted at rest in database
- [ ] Decryption works for payroll calculations
- [ ] PDPA audit logs capture every salary field access
- [ ] Encryption key rotatable without data loss

---

### T192: PDPA Audit Trail for Sensitive Data

**Backend:**

- Create `PdpaAccessLog` model: `id`, `accessed_by` (FK to User), `accessed_at` (datetime), `data_subject_id` (FK to Employee), `data_category` (enum: nric/bank_account/salary/work_pass/medical), `action` (enum: view/export/modify), `ip_address` (string), `justification` (string, nullable)
- Auto-log on every access to encrypted fields (via model property getters)
- Admin can view PDPA access logs
- Retention: 5 years (PDPA requirement)

**API:**

- GET `/admin/pdpa-logs?employee_id=&category=&date_from=&date_to=` — admin only

**Web:**

- PDPA access log page in admin console
- Filter by employee, category, date range, user

**Evidence:**

- [ ] Every sensitive field access logged
- [ ] Admin can view and filter logs
- [ ] Log entries include who, what, when, and IP

---

### T193: Payroll Accuracy Test Suite

**Backend:**

- Create comprehensive test suite validating payroll calculations against known CPF Board rate tables:
  - Test all age bands (below 55, 55-60, 60-65, above 65)
  - Test all citizenship types (SC, PR Y1, PR Y2, PR Y3+, foreigner)
  - Test OW ceiling capping (salary > $6,800)
  - Test AW ceiling for bonus runs
  - Test SHG fund selection by race
  - Test SDL calculation (0.25% of gross, min $2, max $11.25)
  - Test FWL by sector and tier
  - Test proration (mid-month hire/resignation)
  - Test no-pay leave deduction
  - Test back-pay calculation
- Test data: create 20 reference employees covering all edge cases
- Expected results: hand-calculated or verified against CPF Board online calculator
- Run as part of CI — payroll tests must pass before any payroll code change is deployed

**Evidence:**

- [ ] 50+ test cases covering all payroll scenarios
- [ ] All tests pass against current 2026 rate tables
- [ ] Tests run in CI pipeline
- [ ] Edge cases covered (zero salary, ceiling boundary, PR status change)

---

### T194: Performance Testing

**Backend:**

- Performance benchmark: run payroll for 200 employees in <30 seconds
- Test scenarios:
  - 200 employees, monthly payroll with all components
  - 50 employees with complex salary structures (10+ components each)
  - Concurrent payroll calculation + leave application + attendance clock-in
- Optimize: batch database reads (not N+1), bulk insert payslip records
- Memory profiling: ensure no memory leaks in payroll calculation loop

**Evidence:**

- [ ] 200-employee payroll completes in <30 seconds
- [ ] No N+1 query patterns
- [ ] Memory usage stable during large payroll runs
- [ ] Concurrent operations don't deadlock

---

### T195: Data Export and Parallel Run Support

**Backend — Export:**

- Export all company data as CSV/Excel:
  - Employee list with all fields
  - Payroll history (all payslip items)
  - Leave balances and applications
  - Claims
  - Attendance records
- ZIP archive download with one CSV per data type

**Backend — Parallel Run:**

- "Comparison mode": user runs payroll on Arbor and enters their current system's numbers
- Create `ParallelRunComparison` model: employee_id, period, arbor_gross, arbor_net, arbor_cpf, external_gross, external_net, external_cpf, variance_amount, variance_percentage
- Report: show variances per employee, flag discrepancies > $1

**API:**

- POST `/data/export` — generate full export ZIP
- POST `/payroll/parallel-run/import` — upload external payroll data CSV
- GET `/payroll/parallel-run/comparison?period=` — get comparison report

**Web:**

- Data export button in admin settings
- Parallel run page in payroll section

**Evidence:**

- [ ] Full data export generates correctly
- [ ] Parallel run comparison highlights discrepancies
- [ ] Variance report useful for migration validation

---

### T196: Payroll Web UI Polish

**Web:**

- Ensure all payroll pages follow design system
- Payroll run wizard: step 1 (select period) → step 2 (review employee list) → step 3 (calculation results) → step 4 (approve)
- Responsive design for tablet use
- Empty states for first-time payroll users
- Help tooltips on complex fields (OW ceiling explanation, CPF rates)
- Error states: clear messaging when payroll can't be run (missing employee data, etc.)

**Evidence:**

- [ ] Payroll wizard flows smoothly
- [ ] Responsive on tablet
- [ ] Helpful empty states and tooltips
- [ ] Error messages in plain language

---

### T197: Leave and Claims Web UI Polish

**Web:**

- Leave application: date picker shows leave balance depletion in real-time
- Leave calendar: smooth month navigation, responsive
- Claims form: receipt upload with preview thumbnails, amount auto-sum
- Approval lists: batch approve/reject multiple items
- All forms have proper validation messages

**Evidence:**

- [ ] Real-time balance depletion on leave form
- [ ] Receipt thumbnails display
- [ ] Batch approval works
- [ ] Validation messages helpful

---

### T198: Attendance and Shifts Web UI Polish

**Web:**

- Clock in/out: large, clear button; visual feedback on success
- Attendance dashboard: colour coding consistent (green/amber/red)
- Shift calendar: smooth drag-and-drop with snap-to-cell
- Schedule publish: confirmation dialog with affected employee count
- Multi-location: location selector dropdown

**Evidence:**

- [ ] Clock in/out provides clear feedback
- [ ] Colour coding consistent
- [ ] Drag-and-drop smooth
- [ ] Multi-location works

---

### T199: Mobile HRIS Screens Polish

**Mobile:**

- Ensure all HRIS screens work on mobile:
  - Payslip view (readable formatting)
  - Leave apply and approve
  - Claims submit with camera
  - Clock in/out (primary action)
  - Shift schedule (weekly list view)
- Push notifications for: payslip ready, leave approved/rejected, shift published, claim status change
- Offline support for clock in/out

**Evidence:**

- [ ] All HRIS screens render correctly on mobile
- [ ] Push notifications fire for key events
- [ ] Offline clock in/out works

---

### T200: Sidebar Navigation Update

**Web:**

- Update sidebar to include all new sections:
  - Dashboard
  - Advisory
  - **Payroll** (new)
  - **Leave** (new)
  - **Claims** (new)
  - **Attendance** (new)
  - **Shifts** (new — admin only)
  - Employees
  - Compliance
  - Documents
  - Calculators
  - Emergency
  - Alerts
  - Analytics
  - Admin (admin only)
- Employee sidebar (role-restricted): Dashboard, Ask Arbor, My Payslips, My Leave, My Claims, My Attendance, My Schedule, Policies
- Collapse secondary items into groups if sidebar gets too long

**Evidence:**

- [ ] All navigation items present
- [ ] Role-based visibility enforced
- [ ] Employee sees restricted sidebar
- [ ] Mobile navigation drawer updated

---

### T201: API Route Registration

**Backend:**

- Create new API routers: payroll.py, leave.py, claims.py, attendance.py, shifts.py
- Register all new routes in Nexus app
- Add OpenAPI documentation for all new endpoints
- Add authentication middleware to all new routes
- Add tenant isolation to all new routes
- Rate limiting on write endpoints

**Evidence:**

- [ ] All new routes registered and accessible
- [ ] Auth required on all routes
- [ ] Tenant isolation verified (company A can't see company B's data)
- [ ] Rate limiting active

---

### T202: Database Seed Data for Testing

**Backend:**

- Create seed script that generates realistic test data:
  - 1 company with 25 employees (mix of SC, PR, EP, SP, WP)
  - Salary components for all employees
  - 3 months of payroll history
  - Leave balances and 10 leave applications (various statuses)
  - 5 claims with receipts
  - 2 weeks of attendance records
  - 1 week of shift schedule
- Use for development, demo, and testing

**Evidence:**

- [ ] Seed script runs without errors
- [ ] All HRIS features have realistic data to display
- [ ] Demo account accessible for stakeholder review

---

### T203: Production Deployment

**Backend + Frontend:**

- Run full test suite (all tiers)
- Update Docker images for backend + web
- Database migrations for all new models
- Seed SHG rate tables, public holidays, default leave types in production
- Verify all new API routes accessible through load balancer
- Update mobile app builds (iOS + Android)
- Smoke test: run a full payroll cycle on staging environment
- Monitor error rates for 24 hours post-deployment

**Evidence:**

- [ ] All tests pass
- [ ] Database migrations applied successfully
- [ ] All new features accessible in production
- [ ] Mobile app updated
- [ ] No elevated error rates post-deployment
- [ ] Payroll smoke test passes on staging

---

## Summary

| Milestone                     | Tasks        | Scope                                                                                  |
| ----------------------------- | ------------ | -------------------------------------------------------------------------------------- |
| M16: Employee Data Foundation | T141-T146    | Profile extensions, salary components, contacts, history, documents, CSV import        |
| M17: Payroll Engine Core      | T147-T154    | Models, calculation, CPF YTD, SHG, pay variations, dashboard, mobile, employee payslip |
| M18: Payslips & Reports       | T155-T158    | EA s88A payslips, PDF, email, bank GIRO files, reports                                 |
| M19: Tax & Statutory Files    | T159-T162    | CPF e-Submit, IR8A, Appendix 8A, IR21                                                  |
| M20: Leave Management         | T163-T170    | Leave types, application, approval, rules, calendar, policies, pages                   |
| M21: Claims & Expenses        | T171-T173    | Models, submission, approval, audit, payroll integration, pages                        |
| M22: Attendance & Time        | T174-T178    | Models, clock in/out, GPS, lateness, OT, timesheet, pages                              |
| M23: Shift Scheduling         | T179-T181    | Models, calendar, drag-drop, availability, payroll integration                         |
| M24: Employee Lifecycle       | T182-T185    | Org chart, confirmation, exit/offboarding, lifecycle pages                             |
| M25: Cross-Module Integration | T186-T188    | Payroll ↔ leave, attendance, claims                                                    |
| M26: Shadow Agent HRIS        | T189-T190    | HRIS commands, context enrichment                                                      |
| M27: Hardening & Production   | T191-T203    | Encryption, PDPA, testing, performance, export, UI polish, deployment                  |
| **Total**                     | **63 tasks** | **83 features from parity matrix + supporting infrastructure**                         |
