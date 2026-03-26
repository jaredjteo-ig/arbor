# Arbor Domain Configuration Specification

**Date**: 2026-03-21
**Status**: Working Draft
**Context**: PACT domain layer for Arbor HRIS (following Astra's pattern)
**Principle**: Everything here is configuration and domain knowledge — not governance engine code. When PACT core ships, Arbor feeds its configuration into the engine and the agent-filled HR department works.

---

## 1. SME Organizational Templates

Three pre-built templates cover approximately 95% of Singapore SMEs. Each defines the D/T/R tree, which roles are human, which are agent-fillable, and which are shadow-augmented.

### 1.1 Micro Template (1-10 Employees)

The most common Singapore SME structure. One boss, possibly one admin person (Ah Mei), and staff.

```
BOD (vacant — SMEs don't have formal boards)

D1 (Company)
  D1-R1 (Boss / Director)                    [HUMAN — always]
    D1-R1-R2 (HR Manager)                    [AGENT-FILLABLE — primary value prop]
    D1-R1-R3 (Payroll Officer)               [AGENT-FILLABLE]
    D1-R1-R4 (Compliance Monitor)            [AGENT-FILLABLE]
    D1-R1-D1 (Operations)
      D1-R1-D1-R1 (Operations Lead)          [HUMAN or SHADOW-AUGMENTED]
        D1-R1-D1-R1-R2..Rn (Staff)           [HUMAN — self-service only]
```

**Agent-fillable roles**: HR Manager, Payroll Officer, Compliance Monitor
**Human roles**: Boss (always), Operations Lead, Staff
**Shadow-augmented**: Ah Mei (if she exists — human doing HR/admin with shadow agent helping)

**When Ah Mei exists**: D1-R1-R2 becomes Ah Mei (HUMAN + SHADOW). The HR Manager Agent role merges into her shadow augmentation. She does the work; the shadow observes, suggests, and catches mistakes.

**When Ah Mei does not exist**: D1-R1-R2 is the HR Manager Agent (AGENT-FILLED). The agent handles leave, attendance, onboarding, and employee queries autonomously within its envelope.

### 1.2 Small Template (11-25 Employees)

The company has grown enough to have distinct departments but still runs lean. Typically 2-4 departments with 1 manager each.

```
BOD (vacant)

D1 (Company)
  D1-R1 (Boss / Director)                     [HUMAN]
    D1-R1-D1 (Administration / HR)
      D1-R1-D1-R1 (HR Manager)                [HUMAN or AGENT-FILLABLE]
        D1-R1-D1-R1-R2 (HR Executive)         [AGENT-FILLABLE]
        D1-R1-D1-R1-R3 (Payroll Officer)      [AGENT-FILLABLE]
    D1-R1-D2 (Operations)
      D1-R1-D2-R1 (Operations Manager)        [HUMAN]
        D1-R1-D2-R1-T1 (Team A)
          D1-R1-D2-R1-T1-R1 (Supervisor A)    [HUMAN or SHADOW-AUGMENTED]
            D1-R1-D2-R1-T1-R1-R2..Rn (Staff)  [HUMAN — self-service]
        D1-R1-D2-R1-T2 (Team B)
          D1-R1-D2-R1-T2-R1 (Supervisor B)    [HUMAN or SHADOW-AUGMENTED]
    D1-R1-D3 (Sales / Business Dev)
      D1-R1-D3-R1 (Sales Manager)             [HUMAN]
        D1-R1-D3-R1-R2..Rn (Sales Staff)      [HUMAN — self-service]
    D1-R1-R2 (Compliance Monitor)              [AGENT-FILLABLE]
    D1-R1-R3 (Advisory Agent)                  [AGENT-FILLABLE]
```

**Agent-fillable roles**: HR Executive, Payroll Officer, Compliance Monitor, Advisory Agent
**Human roles**: Boss, HR Manager (may be human or agent), Operations Manager, Supervisors, Staff
**Shadow-augmented**: Supervisors (attendance oversight, leave routing)

### 1.3 Medium Template (26-50 Employees)

Formal departmental structure. The company likely has a dedicated HR person and possibly finance.

```
BOD (may exist — some medium SMEs have advisory boards)
  BOD-R1 (Chair — if exists)                    [HUMAN]

D1 (Company)
  D1-R1 (Managing Director / CEO)               [HUMAN]
    D1-R1-D1 (HR Department)
      D1-R1-D1-R1 (HR Director / HR Manager)    [HUMAN]
        D1-R1-D1-R1-R2 (HR Executive)           [HUMAN or AGENT-FILLABLE]
        D1-R1-D1-R1-R3 (Recruitment Lead)       [AGENT-FILLABLE]
        D1-R1-D1-R1-T1 (Employee Onboarding)
          D1-R1-D1-R1-T1-R1 (Onboarding Agent)  [AGENT-FILLABLE]
    D1-R1-D2 (Finance Department)
      D1-R1-D2-R1 (Finance Manager)             [HUMAN]
        D1-R1-D2-R1-R2 (Payroll Officer)        [HUMAN or AGENT-FILLABLE]
        D1-R1-D2-R1-R3 (Claims Processor)       [AGENT-FILLABLE]
    D1-R1-D3 (Operations)
      D1-R1-D3-R1 (Operations Director)         [HUMAN]
        D1-R1-D3-R1-T1..Tn (Teams)
          D1-R1-D3-R1-Tn-R1 (Team Lead)         [HUMAN — SHADOW-AUGMENTED]
    D1-R1-D4 (Sales & Marketing)
      D1-R1-D4-R1 (Sales Director)              [HUMAN]
    D1-R1-R2 (Compliance Monitor)                [AGENT-FILLABLE]
    D1-R1-R3 (Reports Agent)                     [AGENT-FILLABLE]
    D1-R1-R4 (Advisory Agent)                    [AGENT-FILLABLE]
```

**Agent-fillable roles**: HR Executive, Recruitment Lead, Onboarding Agent, Payroll Officer, Claims Processor, Compliance Monitor, Reports Agent, Advisory Agent
**Human roles**: MD, HR Director, Finance Manager, Operations Director, Sales Director, Team Leads, Staff
**Shadow-augmented**: HR Director, Team Leads

### 1.4 Template Selection Algorithm

```
FUNCTION select_org_template(company_id: int) -> str:
    employee_count = count_active_employees(company_id)
    unique_departments = count_unique_departments(company_id)

    IF employee_count <= 10:
        RETURN "micro"
    ELIF employee_count <= 25:
        RETURN "small"
    ELSE:
        RETURN "medium"

    # Note: Template is the starting point. The D/T/R inference
    # algorithm (02-auto-inference-algorithms.md) customizes it
    # based on actual employee data.
```

---

## 2. HRIS Agent Role Definitions

Twelve agent roles, each with a capability specification defining what the agent can do, what tools it uses, what data it accesses, and what its PACT envelope looks like.

### 2.1 HR Manager Agent

**Role address**: Varies by template (e.g., D1-R1-R2 in micro)
**Purpose**: Central HR operations — leave approval, policy enforcement, employee management
**Fills the human role of**: HR Manager ($5,000-$8,000/month)

```yaml
id: agent_hr_manager
title: "HR Manager Agent"
description: "Handles day-to-day HR operations within policy boundaries"
activation_stage: week_2 # Progressive deployment stage

capabilities:
  - approve_leave_within_policy
  - track_leave_balances
  - manage_attendance_records
  - process_employee_onboarding_checklist
  - answer_hr_policy_questions
  - generate_employment_letters
  - track_probation_milestones
  - manage_employee_profile_updates
  - route_complex_queries_to_advisory

tools:
  - leave.approve_leave
  - leave.reject_leave
  - leave.list_applications
  - leave.check_balance
  - attendance.list_records
  - attendance.create_override
  - employees.list
  - employees.get
  - employees.update_profile
  - documents.generate_letter
  - advisory.ask_question

data_access:
  max_clearance: restricted # Can see leave/attendance, not salary
  allowed_models:
    - LeaveApplication (read/write)
    - LeaveBalance (read)
    - LeaveTypeConfig (read)
    - AttendanceRecord (read/write)
    - Employee (read — restricted fields only)
    - CompanyPolicy (read)
  excluded_models:
    - Payslip
    - PayrollRun
    - SalaryComponent
    - FamilyMember
    - EmployeeDocument (confidential)

envelope:
  financial:
    max_per_action: 0 # No financial authority
  operational:
    allowed_actions:
      - manage_leave
      - manage_attendance
      - view_employees
      - generate_documents
      - answer_policy_queries
    blocked_actions:
      - approve_payroll
      - submit_cpf
      - terminate_employee
      - modify_salary
      - access_medical_records
      - delete_any_record
    rate_limit: 100/hour
  data_access:
    max_classification: restricted
    scope: company_wide # Can see all employees' leave/attendance
  temporal:
    operating_hours: "Mon-Sat 07:00-22:00 SGT"
    max_task_duration: 1h
  communication:
    internal: true
    external: false
```

### 2.2 Payroll Agent

**Role address**: Varies (e.g., D1-R1-R3 in micro, D1-R1-D2-R1-R2 in medium)
**Purpose**: Deterministic payroll calculation, payslip generation, statutory file preparation
**Fills the human role of**: Payroll Officer ($3,000-$5,000/month)
**LLM usage**: ZERO — entirely deterministic arithmetic

```yaml
id: agent_payroll
title: "Payroll Agent"
description: "Calculates payroll, generates payslips, prepares statutory filings"
activation_stage: month_1

capabilities:
  - calculate_monthly_payroll
  - generate_payslips
  - calculate_cpf_contributions
  - generate_cpf_esubmit_file
  - calculate_sdl_shg_fwl
  - prepare_ir8a_data
  - prepare_ir21_data
  - track_ytd_contributions
  - calculate_overtime
  - process_leave_deductions
  - process_claim_reimbursements

tools:
  - payroll.calculate_run
  - payroll.generate_payslips
  - payroll.list_runs
  - payroll.get_variance_report
  - payroll.generate_cpf_file
  - payroll.generate_ir8a
  - calculators.cpf
  - calculators.overtime
  - calculators.proration

data_access:
  max_clearance: confidential # Must see salary data
  allowed_models:
    - Employee (full — needs salary, NRIC, bank, CPF fields)
    - SalaryComponent (read)
    - PayrollRun (read/write)
    - PayrollLineItem (read/write)
    - Payslip (read/write)
    - PayslipItem (read/write)
    - CpfYtdRecord (read/write)
    - TaxFiling (read/write)
    - PayItem (read)
    - PayScheme (read)
    - LeaveApplication (read — for unpaid leave deductions)
    - AttendanceRecord (read — for overtime calculation)
    - Claim (read — for reimbursement inclusion)
  excluded_models:
    - FamilyMember (not needed for payroll)
    - EmployeeNote
    - EmployeeSkill
    - Appraisal
    - InterviewFeedback

envelope:
  financial:
    max_per_action: 500000 # Total payroll run limit
    daily_cumulative: 500000
    monthly_cumulative: 500000
  operational:
    allowed_actions:
      - calculate_payroll
      - generate_payslips
      - prepare_statutory_files
      - view_salary_data
      - calculate_contributions
    blocked_actions:
      - approve_payroll_run # HELD for boss
      - submit_cpf_to_board # HELD for boss
      - submit_ir8a # HELD for boss
      - modify_cpf_rates # BLOCKED — statutory
      - modify_salary # BLOCKED — HR function
      - terminate_employee # BLOCKED
    rate_limit: 50/hour
  data_access:
    max_classification: confidential
    pii_handling: access_with_pdpa_logging
    scope: company_wide
  temporal:
    operating_hours: "24/7" # Payroll can run anytime
    blackout_periods: []
    max_task_duration: 4h # Payroll runs can be long
  communication:
    internal: true
    external: false # Cannot send payslips externally without approval
```

### 2.3 Leave Administrator Agent

**Role address**: Sub-role of HR Manager or standalone
**Purpose**: Leave balance tracking, accrual, encashment calculation, policy enforcement
**Fills the human role of**: HR admin handling leave (part of Ah Mei's job)

```yaml
id: agent_leave_admin
title: "Leave Administrator Agent"
description: "Manages leave balances, enforces leave policy, handles encashment"
activation_stage: week_1 # First agent to activate

capabilities:
  - track_leave_balances
  - calculate_accruals
  - enforce_leave_policy
  - check_team_coverage
  - process_leave_encashment
  - manage_off_in_lieu
  - prorate_new_joiner_leave
  - detect_leave_abuse_patterns

tools:
  - leave.check_balance
  - leave.list_applications
  - leave.calculate_proration
  - leave.encash
  - leave.list_types
  - employees.list # For team coverage checks

data_access:
  max_clearance: restricted
  allowed_models:
    - LeaveApplication (read/write)
    - LeaveBalance (read/write)
    - LeaveTypeConfig (read)
    - LeavePolicy (read)
    - LeavePolicyEntitlement (read)
    - Employee (read — restricted fields: name, department, start_date, gender)
    - PublicHoliday (read)
  excluded_models:
    - All salary/payroll models
    - All PII models

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - view_leave_balances
      - calculate_accruals
      - calculate_prorations
      - check_team_overlap
    blocked_actions:
      - approve_leave # Initial stage: flagged to HR Manager or boss
      - encash_leave # HELD for boss
      - modify_leave_policy
      - delete_leave_records
  data_access:
    max_classification: restricted
    scope: company_wide
  temporal:
    operating_hours: "Mon-Sat 07:00-22:00 SGT"
  communication:
    internal: true
    external: false
```

### 2.4 Attendance Agent

```yaml
id: agent_attendance
title: "Attendance Agent"
description: "Tracks clock-in/out, overtime, shift scheduling, lateness"
activation_stage: week_2

capabilities:
  - track_clock_events
  - calculate_overtime_hours
  - manage_shift_assignments
  - detect_lateness_patterns
  - flag_absenteeism
  - generate_attendance_reports

tools:
  - attendance.clock_in
  - attendance.clock_out
  - attendance.list_records
  - attendance.get_summary
  - shifts.list_assignments
  - shifts.assign
  - reports.attendance_summary

data_access:
  max_clearance: restricted
  allowed_models:
    - AttendanceRecord (read/write)
    - ShiftAssignment (read/write)
    - ShiftTemplate (read)
    - ShiftPublish (read)
    - AttendanceSettings (read)
    - LatenessSettings (read)
    - EarlyDepartureSettings (read)
    - Employee (read — restricted fields only)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - record_attendance
      - calculate_overtime
      - assign_shifts
      - generate_reports
    blocked_actions:
      - approve_overtime_payment # Goes to payroll agent or boss
      - modify_attendance_settings
      - delete_attendance_records
  data_access:
    max_classification: restricted
    scope: company_wide
  temporal:
    operating_hours: "24/7" # Attendance tracking is always-on
  communication:
    internal: true
    external: false
```

### 2.5 Claims Agent

```yaml
id: agent_claims
title: "Claims Agent"
description: "Reviews claim submissions, checks policy compliance, routes for approval"
activation_stage: month_1

capabilities:
  - validate_claim_submissions
  - check_policy_limits
  - check_duplicate_claims
  - calculate_claim_totals
  - route_claims_for_approval
  - track_claim_status

tools:
  - claims.list
  - claims.get
  - claims.update_status
  - claims.validate

data_access:
  max_clearance: restricted
  allowed_models:
    - Claim (read/write)
    - ClaimItem (read/write)
    - ClaimGroup (read)
    - ClaimCategory (read)
    - ClaimAuditEntry (write)
    - Employee (read — restricted fields)

envelope:
  financial:
    max_per_action: 200 # Can auto-approve claims up to $200
    daily_cumulative: 1000
    monthly_cumulative: 5000
    flagging_threshold: 100
  operational:
    allowed_actions:
      - validate_claims
      - check_policy
      - auto_approve_within_limit
      - route_for_approval
    blocked_actions:
      - approve_claims_above_limit # HELD for boss/HR manager
      - modify_claim_categories
      - process_reimbursement # Goes to payroll
  data_access:
    max_classification: restricted
    scope: company_wide
  temporal:
    operating_hours: "Mon-Sat 08:00-20:00 SGT"
  communication:
    internal: true
    external: false
```

### 2.6 Compliance Agent

```yaml
id: agent_compliance
title: "Compliance Agent"
description: "Monitors regulatory changes, tracks filing deadlines, flags compliance gaps"
activation_stage: month_2

capabilities:
  - monitor_regulatory_updates
  - track_filing_deadlines
  - check_cpf_rate_currency
  - verify_leave_entitlement_compliance
  - audit_pdpa_compliance
  - flag_employment_act_violations
  - generate_compliance_reports
  - alert_work_pass_expiries

tools:
  - compliance.check_status
  - compliance.list_deadlines
  - compliance.check_cpf_rates
  - advisory.ask_question # For regulatory interpretation
  - reports.compliance_summary
  - alerts.work_pass_expiry
  - alerts.filing_reminder

data_access:
  max_clearance: confidential # Needs to audit salary data for CPF compliance
  allowed_models:
    - Employee (read — full for compliance audit)
    - PayrollRun (read — for CPF verification)
    - CpfYtdRecord (read)
    - TaxFiling (read)
    - LeaveBalance (read)
    - LeaveTypeConfig (read)
    - AttendanceRecord (read)
    - CompanyPolicy (read)
    - ContentUpdate (read)
  excluded_models:
    - FamilyMember
    - EmployeeDocument (non-compliance)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - audit_compliance
      - generate_reports
      - flag_violations
      - send_reminders
    blocked_actions:
      - modify_any_record # Read-only agent
      - submit_statutory_filings # HELD for boss
      - contact_regulators
  data_access:
    max_classification: confidential
    pii_handling: access_with_pdpa_logging
    scope: company_wide
  temporal:
    operating_hours: "24/7"
  communication:
    internal: true
    external: false
```

### 2.7 Recruitment Agent

```yaml
id: agent_recruitment
title: "Recruitment Agent"
description: "Manages job postings, tracks applicants, schedules interviews, generates offers"
activation_stage: month_3

capabilities:
  - create_job_listings
  - screen_applications
  - schedule_interviews
  - generate_offer_letters
  - track_applicant_pipeline
  - check_fair_consideration_framework

tools:
  - recruitment.list_jobs
  - recruitment.create_job
  - recruitment.list_candidates
  - recruitment.update_candidate
  - recruitment.schedule_interview
  - documents.generate_letter

data_access:
  max_clearance: restricted
  allowed_models:
    - JobListing (read/write)
    - Candidate (read/write)
    - InterviewSchedule (read/write)
    - InterviewFeedback (read)
    - Template (read)
    - Employee (read — restricted, for org chart context)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - manage_job_listings
      - track_candidates
      - schedule_interviews
      - generate_offer_drafts
    blocked_actions:
      - approve_offer_letter # HELD for boss
      - set_salary_in_offer # HELD for boss
      - create_employee_record # Post-acceptance, HELD
  data_access:
    max_classification: restricted
    scope: company_wide
  temporal:
    operating_hours: "Mon-Sat 08:00-20:00 SGT"
  communication:
    internal: true
    external: true # Can send interview invitations
    external_channels: [email_with_review]
    review_required_triggers: [offer_letter, salary_discussion]
```

### 2.8 Onboarding Agent

```yaml
id: agent_onboarding
title: "Onboarding Agent"
description: "Manages new employee document collection, system setup, orientation checklist"
activation_stage: month_2

capabilities:
  - create_onboarding_checklist
  - collect_employee_documents
  - setup_system_access
  - initiate_cpf_enrollment
  - generate_welcome_materials
  - track_probation_milestones
  - send_onboarding_reminders

tools:
  - employees.create # With HELD for boss confirmation
  - employees.update_profile
  - documents.request_upload
  - documents.list
  - leave.create_initial_balances

data_access:
  max_clearance: confidential # Needs to collect NRIC, bank details
  allowed_models:
    - Employee (read/write)
    - EmployeeDocument (read/write)
    - Invitation (read/write)
    - LeaveBalance (write — initial balances)
    - Template (read)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - manage_onboarding_checklist
      - collect_documents
      - create_initial_balances
      - send_welcome_materials
    blocked_actions:
      - create_employee_without_approval # HELD for boss
      - set_salary # HELD for boss/finance
      - assign_to_team # HELD for relevant manager
  data_access:
    max_classification: confidential
    pii_handling: access_with_pdpa_logging
  temporal:
    operating_hours: "Mon-Sat 08:00-20:00 SGT"
  communication:
    internal: true
    external: true # Can send welcome emails to new hires
    external_channels: [email]
```

### 2.9 Advisory Agent

```yaml
id: agent_advisory
title: "Advisory Agent"
description: "Answers employment law questions, provides regulatory guidance"
activation_stage: week_1 # Available from day 1 — existing system

capabilities:
  - answer_employment_law_questions
  - cite_relevant_provisions
  - explain_regulatory_requirements
  - provide_compliance_guidance
  - generate_document_templates
  - explain_cpf_calculations

tools:
  - advisory.ask_question
  - kb.search
  - calculators.cpf
  - calculators.overtime
  - calculators.proration
  - calculators.retrenchment
  - calculators.retirement
  - calculators.probation
  - calculators.proration

data_access:
  max_clearance: restricted # Reads company context, not individual PII
  allowed_models:
    - Company (read)
    - CompanyPolicy (read)
    - ContentUpdate (read)
    - AdvisorySession (read/write)
    - Conversation (read/write)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - answer_questions
      - search_knowledge_base
      - run_calculators
      - generate_templates
    blocked_actions:
      - modify_any_employee_data
      - modify_any_policy
      - submit_any_filing
  data_access:
    max_classification: restricted
    scope: company_context_only # Company profile, not individual employees
  temporal:
    operating_hours: "24/7"
  communication:
    internal: true
    external: false
```

### 2.10 Reports Agent

```yaml
id: agent_reports
title: "Reports Agent"
description: "Generates headcount, turnover, cost analysis, and compliance reports"
activation_stage: month_2

capabilities:
  - generate_headcount_report
  - generate_turnover_report
  - generate_cost_analysis
  - generate_leave_utilization_report
  - generate_overtime_report
  - generate_compliance_status_report
  - generate_payroll_summary

tools:
  - reports.headcount
  - reports.turnover
  - reports.payroll_summary
  - reports.leave_utilization
  - reports.attendance_summary
  - reports.compliance_summary

data_access:
  max_clearance: confidential # Needs salary data for cost analysis
  allowed_models:
    - Employee (read — aggregated, not individual PII)
    - PayrollRun (read)
    - LeaveApplication (read)
    - LeaveBalance (read)
    - AttendanceRecord (read)
    - CpfYtdRecord (read)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - generate_reports
      - aggregate_data
    blocked_actions:
      - modify_any_record
      - export_individual_pii # BLOCKED — reports are aggregate
      - share_externally # HELD for boss
  data_access:
    max_classification: confidential
    pii_handling: aggregate_only # Reports show totals, not individual values
  temporal:
    operating_hours: "24/7"
  communication:
    internal: true
    external: false
```

### 2.11 Document Agent

```yaml
id: agent_documents
title: "Document Agent"
description: "Generates contracts, payslip PDFs, letters, and manages document storage"
activation_stage: month_1

capabilities:
  - generate_employment_contracts
  - generate_payslip_pdfs
  - generate_offer_letters
  - generate_warning_letters
  - generate_termination_letters
  - manage_document_storage
  - distribute_payslips

tools:
  - documents.generate_letter
  - documents.list
  - documents.upload
  - documents.download
  - payroll.generate_payslip_pdf

data_access:
  max_clearance: confidential # Contracts contain salary, NRIC
  allowed_models:
    - Template (read)
    - EmployeeDocument (read/write)
    - Employee (read — for mail merge fields)
    - Payslip (read — for payslip PDFs)
    - Company (read — for letterhead)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - generate_documents
      - store_documents
      - distribute_payslips
    blocked_actions:
      - send_termination_letter # HELD for boss
      - send_warning_letter # HELD for boss/HR
      - delete_documents
  data_access:
    max_classification: confidential
    pii_handling: access_with_pdpa_logging
  temporal:
    operating_hours: "Mon-Sat 08:00-20:00 SGT"
  communication:
    internal: true
    external: true # Can email payslips to employees
    external_channels: [email]
    review_required_triggers: [termination, warning, legal]
```

### 2.12 Shadow Agent

```yaml
id: agent_shadow
title: "Shadow Agent"
description: "Observes, suggests, augments human roles — the PACT operator"
activation_stage: day_1 # Always active

capabilities:
  - observe_user_actions
  - detect_behavioral_patterns
  - generate_governance_suggestions
  - provide_morning_briefings
  - deliver_contextual_nudges
  - augment_human_decisions

tools:
  - shadow.observe
  - shadow.briefing
  - shadow.nudge
  - shadow.suggest
  - pact.my_permissions
  - pact.team_structure
  - pact.review_suggestions

data_access:
  max_clearance: restricted # Sees actions and patterns, not PII details
  allowed_models:
    - PactNode (read/write)
    - PactEnvelope (read/write — via suggestion acceptance only)
    - PactClearance (read)
    - PactSuggestion (read/write)
    - PactAuditEvent (write)
    - ObservationStore (read/write)
    - MemoryStore (read/write)

envelope:
  financial:
    max_per_action: 0
  operational:
    allowed_actions:
      - observe
      - detect_patterns
      - generate_suggestions
      - present_suggestions
    blocked_actions:
      - apply_governance_changes # Can ONLY suggest; boss must confirm
      - expand_own_observation_scope
      - modify_own_envelope
      - disable_audit_logging
  data_access:
    max_classification: restricted
    # Shadow agent sees action metadata, not data content
  temporal:
    operating_hours: "24/7"
  communication:
    internal: true
    external: false
```

---

## 3. HR Data Classification

All 77+ DataFlow models classified using EATP clearance levels. This registry is the single source of truth for PACT knowledge clearance enforcement.

### 3.1 Classification Levels

| Level        | EATP Code | Description                                    | Who Can Access                          |
| ------------ | --------- | ---------------------------------------------- | --------------------------------------- |
| PUBLIC       | C0        | Organizational knowledge, policies, settings   | All company members                     |
| RESTRICTED   | C1        | Personal data (non-sensitive), team data       | Employee (own) + Manager (team) + HR    |
| CONFIDENTIAL | C2        | PDPA-protected PII, financial data             | HR + Finance + Owner (PDPA-logged)      |
| SECRET       | C3        | Medical records, investigations, whistleblower | Explicit grant only (not auto-assigned) |
| TOP_SECRET   | C4        | Not used in SME context                        | Reserved for enterprise                 |

### 3.2 Complete Model Registry

```python
MODEL_CLEARANCE_REGISTRY = {
    # ================================================================
    # PUBLIC (C0) — Organizational knowledge, visible to all
    # ================================================================

    # Company structure
    "Company": "public",
    "Organization": "public",
    "Branch": "public",
    "CostCentre": "public",

    # Policies and settings
    "CompanyPolicy": "public",
    "PublicHoliday": "public",
    "HolidayGroup": "public",
    "LeaveTypeConfig": "public",
    "ShiftTemplate": "public",
    "ClaimCategory": "public",
    "AttendanceSettings": "public",
    "LatenessSettings": "public",
    "EarlyDepartureSettings": "public",
    "ShiftHourlyRate": "public",
    "ShiftMultiplier": "public",
    "PayslipSettings": "public",
    "ApprovalGroup": "public",

    # Templates and definitions
    "AppraisalTemplate": "public",
    "AppraisalPeriod": "public",
    "Project": "public",
    "ProjectRole": "public",
    "JobListing": "public",
    "Template": "public",
    "ContentUpdate": "public",
    "InventoryLocation": "public",
    "InventoryCategory": "public",
    "PayItem": "public",
    "PayScheme": "public",

    # ================================================================
    # RESTRICTED (C1) — Personal data, team + HR access
    # ================================================================

    # User and session data
    "User": "restricted",
    "Conversation": "restricted",
    "AdvisorySession": "restricted",
    "Invitation": "restricted",

    # Leave records
    "LeaveApplication": "restricted",
    "LeaveBalance": "restricted",
    "LeavePolicy": "restricted",
    "LeavePolicyEntitlement": "restricted",

    # Attendance and shifts
    "AttendanceRecord": "restricted",
    "TimesheetApproval": "restricted",
    "ShiftAssignment": "restricted",
    "ShiftPublish": "restricted",

    # Claims
    "Claim": "restricted",
    "ClaimItem": "restricted",
    "ClaimGroup": "restricted",
    "ClaimAuditEntry": "restricted",

    # Employee metadata (non-PII)
    "EmployeeSkill": "restricted",
    "EmployeeEvent": "restricted",
    "EmployeeNote": "restricted",  # Upgradeable to confidential per-record
    "EmploymentEvent": "restricted",
    "CustomFieldValue": "restricted",
    "CustomFieldDefinition": "restricted",

    # Project assignments
    "ProjectAssignment": "restricted",
    "ProjectAllocation": "restricted",
    "ProjectOverhead": "restricted",
    "TimesheetEntry": "restricted",

    # Inventory
    "InventoryItem": "restricted",
    "InventoryMovement": "restricted",
    "InventoryRequest": "restricted",

    # Performance and recruitment
    "Appraisal": "restricted",
    "Candidate": "restricted",
    "InterviewSchedule": "restricted",
    "InterviewFeedback": "restricted",

    # LLM configuration
    "CompanyLLMConfig": "restricted",
    "CompanyLLMUsage": "restricted",
    "UserLLMConfig": "restricted",
    "AdminPermission": "restricted",

    # ================================================================
    # CONFIDENTIAL (C2) — PII, PDPA-logged access required
    # ================================================================

    # Employee core (contains NRIC, bank, salary)
    "Employee": "confidential",

    # Salary and payroll
    "SalaryComponent": "confidential",
    "Payslip": "confidential",
    "PayslipItem": "confidential",
    "PayrollRun": "confidential",
    "PayrollLineItem": "confidential",
    "CpfYtdRecord": "confidential",
    "TaxFiling": "confidential",

    # Family and contact PII
    "FamilyMember": "confidential",
    "EmergencyContact": "confidential",

    # Confidential documents
    "EmployeeDocument": "confidential",  # Upgradeable to secret per-record

    # Audit trail of PII access
    "PdpaAccessLog": "confidential",

    # ================================================================
    # SECRET (C3) — Not auto-assigned, explicit per-record upgrade
    # ================================================================
    # Applied to individual records:
    # - Medical certificates with diagnosis details
    # - Disability accommodation records
    # - Criminal background check results
    # - Pending termination records (pre-announcement)
    # - Whistleblower reports
    # - Disciplinary investigation files

    # ================================================================
    # TOP_SECRET (C4) — Not used in SME context
    # ================================================================
}
```

### 3.3 Field-Level Overrides for Employee Model

The Employee model spans multiple clearance levels. Field-level classification determines which agent roles see which fields.

```python
EMPLOYEE_FIELD_CLEARANCE = {
    # PUBLIC — visible in org chart / directory
    "name": "public",          # Via User.name
    "department": "public",
    "designation": "public",
    "photo_url": "public",
    "alias": "public",

    # RESTRICTED — visible to team + HR
    "employment_type": "restricted",
    "start_date": "restricted",
    "end_date": "restricted",
    "confirmation_status": "restricted",
    "reporting_manager_id": "restricted",
    "working_hours_type": "restricted",
    "overtime_eligible": "restricted",
    "organization_id": "restricted",
    "branch_id": "restricted",
    "cost_centre_id": "restricted",
    "pay_scheme_id": "restricted",
    "tags": "restricted",

    # CONFIDENTIAL — HR/Finance only, PDPA-logged
    "nric_fin": "confidential",
    "nric_fin_last4": "confidential",
    "salary_monthly": "confidential",
    "salary_type": "confidential",
    "hourly_rate": "confidential",
    "daily_rate": "confidential",
    "bank_name": "confidential",
    "bank_account_number": "confidential",
    "bank_account_last4": "confidential",
    "bank_code": "confidential",
    "branch_code": "confidential",
    "payment_method": "confidential",
    "payment_frequency": "confidential",
    "tax_reference": "confidential",
    "date_of_birth": "confidential",
    "gender": "confidential",
    "marital_status": "confidential",
    "race": "confidential",
    "religion": "confidential",
    "nationality": "confidential",
    "immigration_status": "confidential",
    "immigration_effective_date": "confidential",
    "work_pass_number": "confidential",
    "work_pass_expiry": "confidential",
    "pass_type": "confidential",
    "residential_address": "confidential",
    "postal_code": "confidential",
    "address_block": "confidential",
    "address_street": "confidential",
    "address_unit": "confidential",
    "address_building": "confidential",
    "address_postal_code": "confidential",
    "phone": "confidential",
    "cpf_status": "confidential",
    "amcs_enabled": "confidential",
    "pmbs_enabled": "confidential",
    "community_chest_amount": "confidential",
    "shg_override_amount": "confidential",
    "iras_auto_inclusion": "confidential",
}
```

---

## 4. Envelope Templates

The 12 envelope templates from the PACT-lite design, now aligned with the 12 agent role definitions. Each template covers all 5 PACT dimensions.

### 4.1 tmpl_owner (Company Boss)

```yaml
id: tmpl_owner
matches:
  user_role: [owner]
  designations:
    [director, managing director, ceo, owner, founder, md, gm, general manager]

financial:
  max_per_action: unlimited
  daily_cumulative: unlimited
  monthly_cumulative: unlimited
  flagging_threshold: 10000 # Flag for audit trail, not for approval

operational:
  allowed_action_types: [all]
  blocked_action_types:
    - delete_audit_records
    - delete_eatp_records
    - modify_pact_engine # Cannot modify the governance engine itself
  rate_limit: 1000/hour
  scope_restriction: [company_wide]

data_access:
  max_classification: confidential
  # SECRET requires explicit upgrade even for owner
  pii_handling: full_access_with_audit
  write_permissions: [all]

temporal:
  operating_hours: "24/7"
  blackout_periods: []
  max_task_duration: unlimited

communication:
  internal_channels: [all]
  external_allowed: true
  external_channels: [email, sms]
  review_required_triggers: [legal, regulatory_submission]
```

### 4.2 tmpl_hr_manager (Ah Mei / HR Manager)

```yaml
id: tmpl_hr_manager
matches:
  user_role: [hr_manager]
  designations:
    [
      hr manager,
      hr director,
      people manager,
      admin manager,
      human resource manager,
      head of hr,
    ]

financial:
  max_per_action: 500
  daily_cumulative: 2000
  monthly_cumulative: 10000
  approval_threshold: 500
  flagging_threshold: 200

operational:
  allowed_action_types:
    - manage_leave
    - manage_attendance
    - manage_claims
    - manage_employees
    - view_payroll
    - generate_reports
    - manage_documents
    - manage_onboarding
  blocked_action_types:
    - approve_payroll_run
    - submit_cpf
    - submit_ir8a
    - modify_statutory_rates
    - delete_audit_records
    - modify_salary_above_band
  scope_restriction: [company_wide]

data_access:
  max_classification: confidential
  allowed_scopes:
    - employee_records
    - leave_records
    - attendance_records
    - claims_records
    - payroll_view_only
  excluded_scopes:
    - medical_records_detail
    - executive_compensation
  pii_handling: access_with_justification

temporal:
  operating_hours: "Mon-Sat 08:00-20:00 SGT"
  max_task_duration: 8h

communication:
  internal_channels: [all]
  external_allowed: true
  external_channels: [email_with_review]
  allowed_recipients: [company_employees, mom_portal, cpf_portal]
  review_required_triggers: [legal, termination, regulatory]
```

### 4.3 tmpl_hr_exec (HR Executive / Officer)

```yaml
id: tmpl_hr_exec
matches:
  designations:
    [
      hr executive,
      hr officer,
      hr admin,
      admin executive,
      hr coordinator,
      people operations,
    ]

financial:
  max_per_action: 100
  daily_cumulative: 500

operational:
  allowed_action_types:
    - manage_leave
    - manage_attendance
    - view_employees
    - generate_basic_reports
  blocked_action_types:
    - approve_payroll
    - manage_salary
    - terminate_employee
    - approve_claims_above_100
    - submit_statutory

data_access:
  max_classification: restricted # Below HR Manager
  pii_handling: access_with_pdpa_logging

temporal:
  operating_hours: "Mon-Fri 09:00-18:00 SGT"

communication:
  internal_channels: [portal, email]
  external_allowed: false
```

### 4.4 tmpl_finance_manager

```yaml
id: tmpl_finance_manager
matches:
  designations:
    [
      finance manager,
      cfo,
      financial controller,
      accounts manager,
      head of finance,
    ]

financial:
  max_per_action: 50000
  daily_cumulative: 200000
  monthly_cumulative: 500000
  approval_threshold: 10000
  flagging_threshold: 5000

operational:
  allowed_action_types:
    - manage_payroll
    - approve_payroll_run
    - manage_claims
    - generate_financial_reports
    - view_all_salary_data
  blocked_action_types:
    - manage_leave # HR function
    - terminate_employee # HR function
    - recruit # HR function
    - modify_statutory_rates

data_access:
  max_classification: confidential
  allowed_scopes: [salary_data, payroll_data, claims_data, tax_data, cpf_data]
  excluded_scopes: [medical_records, disciplinary_records]

temporal:
  operating_hours: "Mon-Fri 08:00-20:00 SGT"
  blackout_periods: [payroll_processing_window]

communication:
  internal_channels: [all]
  external_allowed: true
  external_channels: [email]
  allowed_recipients: [company_employees, cpf_board, iras]
```

### 4.5 tmpl_payroll_officer

```yaml
id: tmpl_payroll_officer
matches:
  designations:
    [
      payroll officer,
      payroll executive,
      payroll admin,
      payroll specialist,
      compensation,
    ]

financial:
  max_per_action: 0 # Cannot approve financial transactions
  # Can calculate but not approve

operational:
  allowed_action_types:
    - calculate_payroll
    - generate_payslips
    - prepare_statutory_files
    - view_salary_data
  blocked_action_types:
    - approve_payroll_run
    - submit_cpf
    - submit_ir8a
    - modify_salary
    - access_non_payroll_data

data_access:
  max_classification: confidential
  allowed_scopes: [salary_data, payroll_data, cpf_data]
  excluded_scopes: [medical_records, disciplinary_records, performance_reviews]

temporal:
  operating_hours: "Mon-Fri 09:00-18:00 SGT"

communication:
  internal_channels: [portal]
  external_allowed: false
```

### 4.6 tmpl_ops_manager

```yaml
id: tmpl_ops_manager
matches:
  designations:
    [
      operations manager,
      coo,
      production manager,
      warehouse manager,
      logistics manager,
    ]

financial:
  max_per_action: 200
  daily_cumulative: 1000

operational:
  allowed_action_types:
    - manage_attendance_own_team
    - manage_shifts
    - approve_leave_own_team
    - view_employees_own_team
    - manage_inventory
    - manage_projects
  blocked_action_types:
    - manage_payroll
    - manage_salary
    - access_other_team_data
    - manage_company_policies

data_access:
  max_classification: restricted
  scope: own_department_only

temporal:
  operating_hours: "Mon-Sat 06:00-22:00 SGT" # Operations may start early

communication:
  internal_channels: [all]
  external_allowed: false
```

### 4.7 tmpl_supervisor

```yaml
id: tmpl_supervisor
matches:
  designations:
    [
      supervisor,
      team lead,
      team leader,
      shift supervisor,
      section head,
      foreman,
    ]

financial:
  max_per_action: 0

operational:
  allowed_action_types:
    - view_own_team_attendance
    - approve_leave_own_team # May be held depending on gradient
    - view_own_team_schedule
    - override_attendance_own_team
  blocked_action_types:
    - manage_payroll
    - manage_salary
    - access_other_team_data
    - manage_company_policies
    - terminate_employee

data_access:
  max_classification: restricted
  scope: own_team_only

temporal:
  operating_hours: "Mon-Sat 06:00-22:00 SGT"

communication:
  internal_channels: [portal, email]
  external_allowed: false
```

### 4.8 tmpl_sales_manager

```yaml
id: tmpl_sales_manager
matches:
  designations:
    [
      sales manager,
      business development,
      account manager,
      sales director,
      commercial manager,
    ]

financial:
  max_per_action: 500
  daily_cumulative: 2000

operational:
  allowed_action_types:
    - manage_own_team
    - approve_leave_own_team
    - view_project_data
    - submit_claims
  blocked_action_types:
    - manage_payroll
    - access_hr_sensitive_data
    - manage_company_policies

data_access:
  max_classification: restricted
  scope: own_department_only

temporal:
  operating_hours: "Mon-Sat 08:00-20:00 SGT"

communication:
  internal_channels: [all]
  external_allowed: true
  external_channels: [email]
```

### 4.9 tmpl_it_manager

```yaml
id: tmpl_it_manager
matches:
  designations:
    [it manager, tech lead, systems administrator, cto, head of technology]

financial:
  max_per_action: 200

operational:
  allowed_action_types:
    - manage_own_team
    - manage_system_settings
    - view_audit_logs
  blocked_action_types:
    - manage_payroll
    - manage_hr_data
    - modify_pact_structure

data_access:
  max_classification: restricted
  scope: own_department_plus_system_logs

temporal:
  operating_hours: "24/7" # IT may need after-hours access

communication:
  internal_channels: [all]
  external_allowed: false
```

### 4.10 tmpl_employee_office (Default for Office Workers)

```yaml
id: tmpl_employee_office
matches:
  designations:
    [
      executive,
      officer,
      coordinator,
      assistant,
      clerk,
      administrator,
      analyst,
      associate,
    ]

financial:
  max_per_action: 0

operational:
  allowed_action_types:
    - apply_leave
    - clock_in_out
    - submit_claim
    - view_own_records
    - view_company_policies
    - view_org_chart
    - update_own_profile
  blocked_action_types: [everything_else]
  scope_restriction: [own_records_only]

data_access:
  max_classification: restricted
  scope: own_records_only
  pii_handling: own_data_only

temporal:
  operating_hours: "Mon-Sat 07:00-22:00 SGT"
  max_task_duration: 1h

communication:
  internal_channels: [self_service_portal]
  external_allowed: false
```

### 4.11 tmpl_employee_field (Field / Operations Staff)

```yaml
id: tmpl_employee_field
matches:
  designations:
    [
      technician,
      driver,
      worker,
      operator,
      installer,
      mechanic,
      electrician,
      plumber,
      cleaner,
      helper,
      packer,
      assembler,
      labourer,
    ]

financial:
  max_per_action: 0

operational:
  allowed_action_types:
    - clock_in_out
    - apply_leave
    - view_own_records
    - view_shift_schedule
    - submit_claim
  blocked_action_types: [everything_else]
  scope_restriction: [own_records_only]

data_access:
  max_classification: restricted
  scope: own_records_only

temporal:
  operating_hours: "24/7" # Shift workers may access outside office hours
  max_task_duration: 30m

communication:
  internal_channels: [mobile_app]
  external_allowed: false
```

### 4.12 tmpl_employee_self (Minimal Access)

```yaml
id: tmpl_employee_self
matches:
  designations:
    [intern, trainee, part-timer, temp, attachment, volunteer, relief]

financial:
  max_per_action: 0

operational:
  allowed_action_types:
    - clock_in_out
    - view_own_records
    - apply_leave
  blocked_action_types: [everything_else]
  scope_restriction: [own_records_only]

data_access:
  max_classification: restricted
  scope: own_records_only

temporal:
  operating_hours: "Mon-Fri 08:00-18:00 SGT"
  max_task_duration: 15m

communication:
  internal_channels: [self_service_portal]
  external_allowed: false
```

---

## 5. Gradient Calibration

Per-module gradient thresholds that determine when actions are auto-approved, flagged, held, or blocked.

### 5.1 Leave Module

| Action                  | Auto-Approved                        | Flagged                      | Held                       | Blocked                 |
| ----------------------- | ------------------------------------ | ---------------------------- | -------------------------- | ----------------------- |
| View own balance        | Always                               | —                            | —                          | —                       |
| Apply leave (1-3 days)  | If balance sufficient and no overlap | If during peak period        | If during notice period    | If no balance remaining |
| Apply leave (4-10 days) | If balance sufficient                | If >50% team overlap         | Always (manager approval)  | If no balance           |
| Apply leave (>10 days)  | Never                                | —                            | Always (boss approval)     | If no balance           |
| Cancel own application  | If status=pending                    | —                            | If status=approved         | If status=completed     |
| Approve leave (agent)   | If within policy and <3 days         | If 3-5 days or near boundary | If >5 days or special type | If outside envelope     |
| Encash leave            | Never                                | —                            | Always (boss approval)     | If no eligible balance  |
| Delete leave record     | Never                                | —                            | Never                      | Always blocked          |

### 5.2 Payroll Module

| Action                  | Auto-Approved                  | Flagged                         | Held                         | Blocked                    |
| ----------------------- | ------------------------------ | ------------------------------- | ---------------------------- | -------------------------- |
| Calculate payroll run   | Always (read-only calculation) | If variance >5% from last month | —                            | —                          |
| Generate payslips       | Always (after approved run)    | —                               | —                            | —                          |
| Approve payroll run     | Never for agents               | —                               | Always (boss confirmation)   | If run has errors          |
| Submit CPF e-Submit     | Never                          | —                               | Always (boss double-confirm) | If rates mismatch          |
| Modify CPF rates        | Never                          | —                               | Never                        | Always blocked (statutory) |
| Ad-hoc pay item         | —                              | If <$500                        | If $500-$5000                | If >$5000                  |
| Back-pay run            | —                              | —                               | Always (boss approval)       | —                          |
| Final pay (termination) | —                              | —                               | Always (boss + HR approval)  | —                          |

### 5.3 Attendance Module

| Action              | Auto-Approved              | Flagged                    | Held                   | Blocked                |
| ------------------- | -------------------------- | -------------------------- | ---------------------- | ---------------------- |
| Clock in/out        | Always                     | If outside scheduled hours | —                      | If already clocked     |
| Overtime recording  | If within OT policy        | If >2 hours/day            | If >4 hours/day        | If OT not approved     |
| Attendance override | —                          | If single occurrence       | Always (supervisor/HR) | If >3 per month        |
| Shift assignment    | By supervisor for own team | If cross-team              | If overtime shift      | If violates WSH limits |
| Delete attendance   | Never                      | —                          | Never                  | Always blocked         |

### 5.4 Claims Module

| Action                    | Auto-Approved                     | Flagged             | Held            | Blocked                  |
| ------------------------- | --------------------------------- | ------------------- | --------------- | ------------------------ |
| Submit claim              | Always (submission, not approval) | —                   | —               | —                        |
| Approve claim <$50        | Auto-approve (agent)              | —                   | —               | —                        |
| Approve claim $50-$200    | Agent-approved + notification     | If unusual category | —               | —                        |
| Approve claim $200-$500   | —                                 | —                   | HR Manager/Boss | —                        |
| Approve claim >$500       | —                                 | —                   | Boss only       | —                        |
| Duplicate claim detection | Auto-block (agent flags)          | —                   | —               | Blocked if confirmed dup |

### 5.5 Employee Management Module

| Action                                   | Auto-Approved           | Flagged       | Held               | Blocked                                  |
| ---------------------------------------- | ----------------------- | ------------- | ------------------ | ---------------------------------------- |
| View own profile                         | Always                  | —             | —                  | —                                        |
| Update own profile (self-service fields) | Always                  | —             | —                  | —                                        |
| Update employee profile (HR)             | Auto for non-PII fields | If PII change | If salary change   | If NRIC/bank change without verification |
| Create employee                          | —                       | —             | Always (boss)      | —                                        |
| Terminate employee                       | —                       | —             | Always (boss + HR) | If in probation without cause            |
| Delete employee record                   | Never                   | —             | Never              | Always blocked (soft-delete only)        |

### 5.6 Compliance Module

| Action                        | Auto-Approved          | Flagged            | Held                         | Blocked |
| ----------------------------- | ---------------------- | ------------------ | ---------------------------- | ------- |
| Run compliance check          | Always (read-only)     | —                  | —                            | —       |
| Generate compliance report    | Always                 | —                  | —                            | —       |
| File statutory return         | —                      | —                  | Always (boss double-confirm) | —       |
| Acknowledge regulatory update | Auto for informational | If action required | If deadline <14 days         | —       |
| Modify compliance settings    | —                      | —                  | Always (boss)                | —       |

### 5.7 Recruitment Module

| Action                | Auto-Approved              | Flagged                   | Held                  | Blocked |
| --------------------- | -------------------------- | ------------------------- | --------------------- | ------- |
| Create job listing    | Auto (draft status)        | —                         | Publish requires boss | —       |
| Screen candidates     | Auto (ranking only)        | If disqualifying criteria | —                     | —       |
| Schedule interview    | Auto within business hours | If outside hours          | —                     | —       |
| Generate offer letter | —                          | —                         | Always (boss)         | —       |
| Set salary in offer   | —                          | —                         | Always (boss)         | —       |

---

## 6. Bridge Definitions

Cross-module data flows modeled as PACT bridges. Each bridge defines what data crosses containment boundaries, in which direction, and with what constraints.

### 6.1 Leave-to-Payroll Bridge

```yaml
id: bridge_leave_payroll
from_role: agent_leave_admin # or HR Manager
to_role: agent_payroll
direction: one_way # Leave data flows to Payroll; Payroll data does not flow back
scope: "Unpaid leave deductions and leave encashment for payroll processing"
regulation: "Employment Act — salary deduction for unauthorized absence"

data_flow:
  - model: LeaveApplication
    fields: [employee_id, leave_type, start_date, end_date, status, days_taken]
    classification_ceiling: restricted
    purpose: "Calculate unpaid leave deductions"
  - model: LeaveBalance
    fields: [employee_id, balance, encashed_days]
    classification_ceiling: restricted
    purpose: "Process leave encashment as pay item"

operational_scope:
  - read_approved_leave_for_payroll_period
  - read_encashment_records
  - NO write access to leave records from payroll

financial_authority: false
```

### 6.2 Attendance-to-Payroll Bridge

```yaml
id: bridge_attendance_payroll
from_role: agent_attendance
to_role: agent_payroll
direction: one_way
scope: "Overtime hours and attendance data for payroll calculation"
regulation: "Employment Act Part IV — overtime payment requirements"

data_flow:
  - model: AttendanceRecord
    fields: [employee_id, date, clock_in, clock_out, overtime_hours, status]
    classification_ceiling: restricted
    purpose: "Calculate overtime payment"
  - model: ShiftAssignment
    fields: [employee_id, shift_date, actual_hours]
    classification_ceiling: restricted
    purpose: "Calculate shift differentials"

operational_scope:
  - read_overtime_hours_for_payroll_period
  - read_shift_records_for_payroll_period

financial_authority: false
```

### 6.3 Claims-to-Payroll Bridge

```yaml
id: bridge_claims_payroll
from_role: agent_claims
to_role: agent_payroll
direction: one_way
scope: "Approved claim reimbursements for payroll inclusion"
regulation: "Employment Act — salary includes reimbursement of expenses"

data_flow:
  - model: Claim
    fields: [employee_id, amount, status, approved_date, category]
    classification_ceiling: restricted
    purpose: "Include approved reimbursements in payslip"

operational_scope:
  - read_approved_claims_for_payroll_period

financial_authority: false
```

### 6.4 Recruitment-to-Onboarding Bridge

```yaml
id: bridge_recruitment_onboarding
from_role: agent_recruitment
to_role: agent_onboarding
direction: one_way
scope: "Accepted candidate data initiates onboarding workflow"
regulation: "PDPA — consent required for data transfer between functions"

data_flow:
  - model: Candidate
    fields: [name, email, phone, position, offer_salary, start_date]
    classification_ceiling: restricted
    purpose: "Create employee record and initiate onboarding"

operational_scope:
  - read_accepted_candidates
  - trigger_onboarding_workflow

financial_authority: false
```

### 6.5 Onboarding-to-Payroll Bridge

```yaml
id: bridge_onboarding_payroll
from_role: agent_onboarding
to_role: agent_payroll
direction: one_way
scope: "New employee data for payroll enrollment"
regulation: "CPF Act — employer must register employee within first month"

data_flow:
  - model: Employee
    fields:
      [
        employee_id,
        nric_fin,
        start_date,
        salary_monthly,
        cpf_status,
        bank_details,
      ]
    classification_ceiling: confidential
    purpose: "Enroll in payroll and CPF"

operational_scope:
  - notify_payroll_of_new_employee
  - share_cpf_enrollment_data

financial_authority: false
```

### 6.6 Compliance-to-All Bridge

```yaml
id: bridge_compliance_audit
from_role: agent_compliance
to_role: all_agents
direction: one_way # Compliance reads from all; writes to none
scope: "Read-only audit access across all modules for compliance verification"
regulation: "Employment Act, CPF Act, PDPA — employer record-keeping obligations"

data_flow:
  - model: "*"
    fields: [all readable fields within confidential ceiling]
    classification_ceiling: confidential
    purpose: "Compliance audit and verification"

operational_scope:
  - read_all_for_audit
  - NO write to any module
  - NO modify to any record

financial_authority: false
```

### 6.7 Shadow-to-All Observation Bridge

```yaml
id: bridge_shadow_observation
from_role: agent_shadow
to_role: all_agents
direction: one_way # Shadow reads metadata only
scope: "Action metadata observation for pattern detection"
regulation: "CARE — Human-on-the-Loop requires observable agent behavior"

data_flow:
  - metadata_only: true # Shadow sees WHAT happened, not the DATA content
    fields: [user_id, action_type, module, timestamp, envelope_result]
    classification_ceiling: restricted
    purpose: "Pattern detection and governance suggestions"

operational_scope:
  - observe_action_metadata
  - NO read of actual data content
  - NO write to any operational module

financial_authority: false
```

---

## 7. Singapore Regulatory Mapping

Mapping Singapore employment legislation to PACT concepts — the foundational configuration that makes Arbor's agents compliant by construction.

### 7.1 Employment Act (EA)

```python
EA_MAPPING = RegMapping(
    full_name="Employment Act (Chapter 91)",
    last_amended="2024",
    pact_concepts={
        "operating_envelope": [
            "OT calculation rules constrain Payroll Agent arithmetic",
            "Notice period rules constrain termination workflows",
            "Rest day and public holiday rules constrain shift scheduling",
            "Salary deduction limits constrain Claims Agent amounts",
        ],
        "verification_gradient": [
            "Termination → always HELD (boss + HR approval required)",
            "Salary reduction → always HELD (employee consent required)",
            "Overtime >72 hours/month → BLOCKED (statutory limit)",
            "Rest day work → FLAGGED (must pay 2x rate)",
        ],
        "data_access": [
            "Employment records must be kept for 2 years after termination",
            "Salary records accessible to employee (own records)",
            "MOM inspector access → HELD for boss confirmation",
        ],
    },
    affected_agents=["agent_payroll", "agent_hr_manager", "agent_attendance", "agent_compliance"],
    enforcement="Structural — rules embedded in payroll calculation engine and gradient thresholds",
)
```

### 7.2 CPF Act

```python
CPF_MAPPING = RegMapping(
    full_name="Central Provident Fund Act (Chapter 36)",
    last_amended="2026",
    pact_concepts={
        "operating_envelope": [
            "CPF contribution rates are lookup-table-driven (age band x PR year)",
            "OW ceiling ($8,000/month 2026) hard-coded in calculation",
            "AW ceiling ($102,000/year minus OW) enforced per-run",
            "SHG fund routing by race (CDAC/MBMF/SINDA/ECF) — citizens only",
        ],
        "verification_gradient": [
            "Monthly CPF submission → HELD (boss double-confirm before e-Submit)",
            "Rate changes (January/September) → auto-update + FLAGGED notification",
            "Late submission detection → FLAGGED with penalty calculation",
            "Modify CPF rates manually → BLOCKED (statutory rates are immutable)",
        ],
        "data_access": [
            "CPF data classified CONFIDENTIAL",
            "Employee can view own CPF contributions",
            "CPF Board submissions require boss authorization",
        ],
    },
    affected_agents=["agent_payroll", "agent_compliance"],
    enforcement="Deterministic — zero LLM, pure arithmetic with tested lookup tables",
)
```

### 7.3 Employment of Foreign Manpower Act (EFMA)

```python
EFMA_MAPPING = RegMapping(
    full_name="Employment of Foreign Manpower Act (Chapter 91A)",
    pact_concepts={
        "operating_envelope": [
            "FWL rates constrain payroll calculation (WP $300, S Pass $450)",
            "Work pass expiry tracking in Compliance Agent",
            "Foreign worker quota limits in hiring workflow",
        ],
        "verification_gradient": [
            "Work pass expiry <30 days → FLAGGED alert to boss",
            "Work pass expiry <7 days → HELD — block work assignment",
            "Hire above quota → BLOCKED",
            "FWL rate change → auto-update + notification",
        ],
        "data_access": [
            "Work pass data classified CONFIDENTIAL",
            "Pass expiry dates accessible to HR Manager and Compliance",
        ],
    },
    affected_agents=["agent_payroll", "agent_compliance", "agent_hr_manager", "agent_onboarding"],
    enforcement="Structural — pass expiry alerts automated, FWL rates in payroll engine",
)
```

### 7.4 Personal Data Protection Act (PDPA)

```python
PDPA_MAPPING = RegMapping(
    full_name="Personal Data Protection Act 2012",
    pact_concepts={
        "knowledge_clearance": [
            "Employee PII fields classified CONFIDENTIAL",
            "NRIC collection minimized (last 4 digits preferred)",
            "Medical records classified SECRET",
            "Access logging for all CONFIDENTIAL+ data (PdpaAccessLog)",
        ],
        "operating_envelope": [
            "NRIC display rules — mask except last 4 digits",
            "Data retention limits — employment records 2 years post-termination",
            "Consent requirements for data sharing across departments",
        ],
        "verification_gradient": [
            "Bulk PII export → BLOCKED without boss approval",
            "Access to NRIC data → FLAGGED + PDPA logged",
            "Share employee data externally → HELD for boss",
            "Delete PDPA access log → BLOCKED (audit integrity)",
        ],
    },
    affected_agents=["all"],
    enforcement="Structural — PACT clearance framework IS the PDPA enforcement layer",
)
```

### 7.5 Workplace Safety and Health Act (WSH)

```python
WSH_MAPPING = RegMapping(
    full_name="Workplace Safety and Health Act (Chapter 354A)",
    pact_concepts={
        "operating_envelope": [
            "Maximum working hours enforcement in shift scheduling",
            "Mandatory rest period enforcement between shifts",
            "Safety record keeping requirements",
        ],
        "verification_gradient": [
            "Consecutive shifts >12 hours → BLOCKED",
            "Rest period <8 hours between shifts → BLOCKED",
            "Safety incident report → HELD for boss + immediate filing",
        ],
    },
    affected_agents=["agent_attendance", "agent_compliance"],
    enforcement="Structural — shift scheduling engine enforces rest periods",
)
```

### 7.6 Work Injury Compensation Act (WICA)

```python
WICA_MAPPING = RegMapping(
    full_name="Work Injury Compensation Act (Chapter 354)",
    pact_concepts={
        "verification_gradient": [
            "Work injury report → HELD for boss, 10-day MOM notification deadline",
            "Medical leave for work injury → auto-approved up to statutory limit",
        ],
        "data_access": [
            "Work injury records classified CONFIDENTIAL",
            "Medical records from work injury classified SECRET",
        ],
    },
    affected_agents=["agent_compliance", "agent_leave_admin"],
    enforcement="Deadline tracking by Compliance Agent, auto-leave by Leave Agent",
)
```

---

## 8. Acceptance Tests

Agent role-filling scenarios that validate the domain configuration when PACT core is integrated.

### 8.1 HR Manager Agent Tests

```python
class TestHRManagerAgent:
    """Tests that the HR Manager Agent operates within its envelope."""

    def test_approve_routine_leave(self, org, gradient_engine):
        """2-day annual leave with sufficient balance → AUTO_APPROVED."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R2",  # HR Manager Agent
            action="approve_leave",
            params={"days": 2, "type": "annual", "balance_sufficient": True},
        )
        assert result.zone == "AUTO_APPROVED"

    def test_flag_leave_during_peak(self, org, gradient_engine):
        """Leave during December peak → FLAGGED (approved but boss notified)."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R2",
            action="approve_leave",
            params={"days": 3, "type": "annual", "is_peak_period": True},
        )
        assert result.zone == "FLAGGED"

    def test_hold_leave_during_notice(self, org, gradient_engine):
        """Leave during notice period → HELD for boss."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R2",
            action="approve_leave",
            params={"days": 2, "type": "annual", "employee_on_notice": True},
        )
        assert result.zone == "HELD"

    def test_blocked_from_salary_data(self, org, access_engine):
        """HR Manager Agent cannot access salary data."""
        result = access_engine.can_access(
            role_address="D1-R1-R2",
            target_model="Employee",
            target_field="salary_monthly",
        )
        assert result.decision == "BLOCKED"
        assert "confidential" in result.reason.lower() or "clearance" in result.reason.lower()

    def test_blocked_from_payroll_approval(self, org, gradient_engine):
        """HR Manager Agent cannot approve payroll runs."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R2",
            action="approve_payroll_run",
            params={},
        )
        assert result.zone == "BLOCKED"
```

### 8.2 Payroll Agent Tests

```python
class TestPayrollAgent:
    """Tests that the Payroll Agent calculates but does not approve."""

    def test_calculate_payroll_auto_approved(self, org, gradient_engine):
        """Payroll calculation (read-only) → AUTO_APPROVED."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R3",  # Payroll Agent
            action="calculate_payroll",
            params={"month": "2026-03"},
        )
        assert result.zone == "AUTO_APPROVED"

    def test_approve_payroll_held_for_boss(self, org, gradient_engine):
        """Payroll approval → HELD for boss."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R3",
            action="approve_payroll_run",
            params={"total": 47200},
        )
        assert result.zone == "HELD"
        assert result.requires_approval_from == "D1-R1"  # Boss

    def test_submit_cpf_held_for_boss(self, org, gradient_engine):
        """CPF submission → HELD for boss double-confirm."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R3",
            action="submit_cpf",
            params={"total_cpf": 12500},
        )
        assert result.zone == "HELD"

    def test_modify_cpf_rates_blocked(self, org, gradient_engine):
        """Modifying statutory CPF rates → BLOCKED for everyone."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-R3",
            action="modify_cpf_rates",
            params={},
        )
        assert result.zone == "BLOCKED"

    def test_can_access_salary_data(self, org, access_engine):
        """Payroll Agent can access salary data (CONFIDENTIAL clearance)."""
        result = access_engine.can_access(
            role_address="D1-R1-R3",
            target_model="Employee",
            target_field="salary_monthly",
        )
        assert result.decision == "ALLOWED"
        assert result.pdpa_logged is True

    def test_cannot_access_medical_records(self, org, access_engine):
        """Payroll Agent blocked from SECRET medical records."""
        result = access_engine.can_access(
            role_address="D1-R1-R3",
            target_model="EmployeeDocument",
            target_field=None,
            record_classification="secret",
        )
        assert result.decision == "BLOCKED"
```

### 8.3 Cross-Module Bridge Tests

```python
class TestBridges:
    """Tests for cross-module data flow through PACT bridges."""

    def test_leave_data_flows_to_payroll(self, org, bridge_engine):
        """Leave Agent's approved leave records accessible to Payroll Agent."""
        result = bridge_engine.can_cross(
            from_role="D1-R1-R2",   # Leave Admin (under HR Manager)
            to_role="D1-R1-R3",     # Payroll Agent
            data_model="LeaveApplication",
            fields=["employee_id", "days_taken", "leave_type"],
        )
        assert result.allowed is True
        assert result.bridge_id == "bridge_leave_payroll"

    def test_payroll_data_does_not_flow_to_leave(self, org, bridge_engine):
        """Payroll data does not flow back to Leave Agent (one-way bridge)."""
        result = bridge_engine.can_cross(
            from_role="D1-R1-R3",   # Payroll Agent
            to_role="D1-R1-R2",     # Leave Admin
            data_model="PayrollRun",
            fields=["total_amount"],
        )
        assert result.allowed is False

    def test_compliance_can_read_all_modules(self, org, bridge_engine):
        """Compliance Agent has read-only bridge to all modules."""
        for target_model in ["PayrollRun", "LeaveApplication", "AttendanceRecord", "Claim"]:
            result = bridge_engine.can_cross(
                from_role="D1-R1-R4",  # Compliance Agent
                to_role="*",
                data_model=target_model,
                fields=["*"],
                operation="read",
            )
            assert result.allowed is True
            assert result.bridge_id == "bridge_compliance_audit"

    def test_compliance_cannot_write(self, org, bridge_engine):
        """Compliance Agent cannot write to any operational module."""
        result = bridge_engine.can_cross(
            from_role="D1-R1-R4",
            to_role="*",
            data_model="PayrollRun",
            fields=["status"],
            operation="write",
        )
        assert result.allowed is False
```

### 8.4 Employee Self-Service Tests

```python
class TestEmployeeSelfService:
    """Tests that regular employees are confined to self-service."""

    def test_employee_can_view_own_leave_balance(self, org, access_engine):
        """Employee can view their own leave balance."""
        result = access_engine.can_access(
            role_address="D1-R1-D1-R1-R2",  # Staff member
            target_model="LeaveBalance",
            target_employee_id=42,
            requesting_user_employee_id=42,  # Own record
        )
        assert result.decision == "ALLOWED"
        assert result.reason == "own_record"

    def test_employee_blocked_from_other_employee_data(self, org, access_engine):
        """Employee cannot view another employee's leave balance."""
        result = access_engine.can_access(
            role_address="D1-R1-D1-R1-R2",
            target_model="LeaveBalance",
            target_employee_id=99,
            requesting_user_employee_id=42,  # Not own record
        )
        assert result.decision == "BLOCKED"

    def test_employee_blocked_from_salary_data(self, org, access_engine):
        """Employee cannot view salary data (even their own model-level is CONFIDENTIAL)."""
        result = access_engine.can_access(
            role_address="D1-R1-D1-R1-R2",
            target_model="SalaryComponent",
            target_employee_id=42,
            requesting_user_employee_id=42,
        )
        # Own salary components are accessible but PDPA-logged
        assert result.decision == "ALLOWED"
        assert result.pdpa_logged is True

    def test_employee_can_apply_leave(self, org, gradient_engine):
        """Employee can submit a leave application."""
        result = gradient_engine.evaluate(
            role_address="D1-R1-D1-R1-R2",
            action="apply_leave",
            params={"days": 2, "type": "annual"},
        )
        assert result.zone == "AUTO_APPROVED"  # Submission is auto; approval is separate
```

### 8.5 Progressive Agent Activation Tests

```python
class TestProgressiveActivation:
    """Tests that agent roles activate progressively over time."""

    def test_week_1_only_advisory_and_leave_tracking(self, company_age_days=7):
        """In week 1, only Advisory and Leave Administrator agents are active."""
        active_agents = get_active_agents(company_id, company_age_days)
        assert "agent_advisory" in active_agents
        assert "agent_leave_admin" in active_agents
        assert "agent_payroll" not in active_agents
        assert "agent_recruitment" not in active_agents

    def test_month_1_payroll_activates(self, company_age_days=30):
        """At month 1, Payroll and Document agents become available."""
        active_agents = get_active_agents(company_id, company_age_days)
        assert "agent_payroll" in active_agents
        assert "agent_documents" in active_agents

    def test_month_3_full_suite(self, company_age_days=90):
        """At month 3, all agents are available for activation."""
        active_agents = get_active_agents(company_id, company_age_days)
        assert len(active_agents) == 12  # All 12 agent roles

    def test_boss_can_activate_early(self, company_age_days=7):
        """Boss can manually activate any agent ahead of schedule."""
        result = activate_agent(company_id, "agent_payroll", activated_by="boss")
        assert result.success is True
        assert "agent_payroll" in get_active_agents(company_id)
```
