# PACT-lite: Invisible Governance for Singapore SMEs

## Design Specification v0.1

**Status**: Working Draft
**Date**: 2026-03-21
**Context**: Arbor HRIS Platform (Terrene Foundation)
**Prerequisite**: PACT Core Specification v0.1

---

## 1. Design Philosophy

### The Problem

PACT is architecturally sound but operationally hostile to its primary audience. A 10-person Singapore SME has a Boss, Ah Mei (who does HR, admin, and finance), and 8 staff. They will never:

- Configure a D/T/R tree
- Define five-dimensional operating envelopes
- Classify 77 DataFlow models by clearance level
- Set verification gradient thresholds per dimension
- Establish knowledge share policies between organizational units

But their platform should still be governed by PACT. Every action should flow through accountable delegation chains. Every data access should respect clearance boundaries. Every unusual action should trigger calibrated human oversight. The governance should be real, not theater.

### The Solution: Infer, Generate, Evolve

PACT-lite does not simplify PACT. It does not drop features. It does not make governance optional. Instead, it makes PACT invisible by:

1. **Inferring** the D/T/R structure from data the company already provides (departments, job titles, reporting lines)
2. **Generating** sensible operating envelopes from template libraries matched to Singapore job roles
3. **Auto-classifying** all data models using PDPA categories that Arbor already enforces
4. **Evolving** the governance posture through shadow agent observation and owner-confirmed suggestions

The human's burden is zero configuration. Their contribution is judgment -- confirming or rejecting the shadow agent's governance suggestions as they arrive naturally over time.

### Design Constraints

- **No new screens at onboarding.** PACT-lite must not add a single step to the existing company registration flow.
- **No governance vocabulary exposed.** Users never see "D/T/R", "operating envelope", "clearance level", or "verification gradient." They see team structures, permissions, and approval flows.
- **Progressive disclosure only.** Governance features surface through shadow agent suggestions, not configuration panels.
- **Fail-safe defaults.** When the system cannot infer a governance decision, it defaults to the more restrictive option. Restrictive defaults that are loosened by observation are safer than permissive defaults that are tightened after an incident.
- **Full PACT compliance.** Every PACT invariant (monotonic tightening, grammar constraint, clearance independence) is enforced. The simplification is in the input method, not the enforcement model.

---

## 2. Auto-Inference of D/T/R

### 2.1 The Data Already Exists

Arbor's Employee model already captures the three inputs needed for D/T/R inference:

```
Employee.department       -> D (Department) inference
Employee.designation      -> R (Role) inference
Employee.reporting_manager_id -> Hierarchy inference
```

The `Organization` model provides sub-organizational units. The `Branch` model provides physical locations. The `ApprovalGroup` model provides approval chain data. All of these map to D/T/R structures.

### 2.2 The Inference Algorithm

**Phase 1: Department Discovery (D nodes)**

When employees are added with department values, the system groups them:

```
Input:
  Employee(name="Boss", department="Management", designation="Director", reporting_manager_id=None)
  Employee(name="Ah Mei", department="Admin", designation="HR Manager", reporting_manager_id=boss_id)
  Employee(name="John", department="Operations", designation="Supervisor", reporting_manager_id=boss_id)
  Employee(name="Sarah", department="Operations", designation="Worker", reporting_manager_id=john_id)
  ... (6 more workers)

Phase 1 output: Unique departments -> {Management, Admin, Operations}
Each becomes a D node.
```

**Phase 2: Hierarchy Inference (R nodes)**

For each department, find the reporting chain:

```
For department "Operations":
  - John reports to Boss (Boss is outside Operations)
  - Sarah reports to John
  -> John is the department head (R1 for Operations)
  -> Sarah is a member (R2 under John)

For department "Admin":
  - Ah Mei reports to Boss
  -> Ah Mei is the department head (R1 for Admin)

For department "Management":
  - Boss has no reporting_manager_id
  -> Boss is the organization head
```

**Phase 3: Tree Assembly**

```
BOD (auto-created, vacant -- the Boss is not a board member in an SME)
D1 (Company)
  D1-R1 (Boss -- Managing Director)
    D1-R1-D1 (Admin)
      D1-R1-D1-R1 (Ah Mei -- HR Manager)
    D1-R1-D2 (Operations)
      D1-R1-D2-R1 (John -- Supervisor)
        D1-R1-D2-R1-R2 (Sarah -- Worker)
        D1-R1-D2-R1-R3 (Worker 2)
        ...
```

### 2.3 Handling Ambiguity

**No reporting_manager_id set:**

- If only one employee exists in a department, they become the head (R1)
- If multiple employees exist with no reporting lines, the system picks the one with the highest-seniority designation (Director > Manager > Supervisor > Officer > Executive > Staff) and marks it as "inferred -- please confirm"
- If designations are identical or absent, ALL employees are placed as flat R nodes under the department head, and the head is left vacant with a shadow agent suggestion to the owner: "Your Operations team has 5 people but no one is marked as supervisor. Want to set John as the team lead?"

**Flat structures (everyone reports to Boss):**

- This is valid. It produces:
  ```
  D1-R1 (Boss)
    D1-R1-R2 (Ah Mei)
    D1-R1-R3 (John)
    D1-R1-R4 (Sarah)
    ...
  ```
- The shadow agent will eventually suggest departmentalization: "You have 10 people all reporting directly to you. Would you like me to group them into teams based on their job functions?"

**Single department (or no departments):**

- The entire company is one D node. All employees are R nodes under the owner. This is PACT-valid (single D with head R and member Rs).
- The system works fine in this mode. Governance is flat but present.

**Cross-functional roles (Ah Mei does HR + Finance + Admin):**

- Ah Mei gets one primary R position in her declared department
- Her actual access pattern (which the shadow agent observes) determines bridge suggestions
- Week 4 suggestion: "Ah Mei has been accessing payroll data regularly but she's in the Admin department. Should I give her formal access to Finance data?"

### 2.4 When D/T/R is Generated

The D/T/R tree is computed:

1. **At company creation** -- from seed data (departments seeded by `company_seeding.py`)
2. **When employees are added** -- each new employee triggers a tree recomputation
3. **When reporting lines change** -- `reporting_manager_id` update triggers recomputation
4. **When departments are modified** -- department name change, merge, or split
5. **On shadow agent suggestion acceptance** -- owner confirms a structural change

The tree is materialized in a `PactNode` table (see File 2 for schema) and recomputed idempotently. Old addresses are preserved in `address_history` for audit.

---

## 3. Template Envelopes from Job Roles

### 3.1 The Template Library

Singapore SMEs use a small set of well-known job functions. PACT-lite ships with 12 template envelopes that cover approximately 90% of roles:

| Template ID            | Role Pattern                 | Matches Designations                                           |
| ---------------------- | ---------------------------- | -------------------------------------------------------------- |
| `tmpl_owner`           | Company Owner / Director     | Director, Managing Director, CEO, Owner, Founder               |
| `tmpl_hr_manager`      | HR Manager / People Lead     | HR Manager, HR Director, People Manager, Admin Manager         |
| `tmpl_hr_exec`         | HR Executive / Officer       | HR Executive, HR Officer, HR Admin, Admin Executive            |
| `tmpl_finance_manager` | Finance Manager / Controller | Finance Manager, CFO, Financial Controller, Accounts Manager   |
| `tmpl_payroll_officer` | Payroll Officer              | Payroll Officer, Payroll Executive, Payroll Admin              |
| `tmpl_ops_manager`     | Operations Manager           | Operations Manager, COO, Production Manager, Warehouse Manager |
| `tmpl_supervisor`      | Team Lead / Supervisor       | Supervisor, Team Lead, Senior [role], Shift Supervisor         |
| `tmpl_sales_manager`   | Sales / BD Manager           | Sales Manager, Business Development Manager, Account Manager   |
| `tmpl_it_manager`      | IT Manager / Tech Lead       | IT Manager, Tech Lead, Systems Administrator                   |
| `tmpl_employee_office` | Office Employee              | Executive, Officer, Coordinator, Assistant, Clerk              |
| `tmpl_employee_field`  | Field / Operations Staff     | Technician, Driver, Worker, Operator, Installer                |
| `tmpl_employee_self`   | Self-Service Only            | Intern, Trainee, Part-Timer, Temp Staff                        |

### 3.2 Template Envelope Details

Each template defines all five PACT dimensions. Here are three representative templates:

**tmpl_owner (Company Owner)**

```yaml
financial:
  max_per_action: unlimited
  daily_cumulative: unlimited
  monthly_cumulative: unlimited
  approval_threshold: null # Owner approves themselves
  flagging_threshold: 10000 # Flag for audit trail
operational:
  allowed_action_types: [all]
  blocked_action_types: [delete_audit_records]
  rate_limit: 1000/hour
  scope_restriction: [company_wide]
data_access:
  max_classification: confidential # SECRET requires explicit upgrade
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

**tmpl_hr_manager (Ah Mei)**

```yaml
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

**tmpl_employee_self (Regular Employee)**

```yaml
financial:
  max_per_action: 0 # Cannot initiate financial actions
  approval_threshold: 0
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
  max_classification: restricted # Own data only
  allowed_scopes:
    - own_employee_record
    - own_leave_balance
    - own_payslips
    - own_attendance
    - own_claims
    - company_policies
    - public_holidays
  excluded_scopes: [other_employee_data, payroll_runs, management_reports]
  pii_handling: own_data_only
temporal:
  operating_hours: "Mon-Sat 07:00-22:00 SGT"
  max_task_duration: 1h
communication:
  internal_channels: [self_service_portal]
  external_allowed: false
```

### 3.3 Template Matching Algorithm

When an employee is added, the system matches their designation to a template:

```
1. Normalize designation: lowercase, strip whitespace, remove "senior/junior/lead" prefixes
2. Exact match against template keyword lists
3. Fuzzy match (Levenshtein distance <= 2) against template keywords
4. If role=owner in User model -> tmpl_owner (override)
5. If role=hr_manager in User model -> tmpl_hr_manager (override)
6. If no match -> tmpl_employee_office (safe default)
```

The matched template becomes the Role Envelope for that position. It is automatically tighter than the parent's envelope (monotonic tightening is validated at write time).

### 3.4 Learning from Usage (Shadow Agent Observation)

Template envelopes are starting points. The shadow agent observes actual usage and suggests refinements:

**Envelope too tight:**

```
Shadow agent observes: Ah Mei has tried to approve payroll 4 times this month.
                       Each time it was held ("This needs your OK -- payroll approval
                       requires the company owner").
                       Each time Boss approved within 5 minutes.

Shadow agent suggests to Boss: "Ah Mei regularly processes payroll approval, and
                                you've approved her requests every time. Would you
                                like to let her approve payroll runs directly?"

If Boss says yes -> tmpl_hr_manager.operational.allowed_action_types += approve_payroll_run
```

**Envelope too loose:**

```
Shadow agent observes: A new employee accessed the employee directory 47 times in
                       one day, downloading every employee's profile.

Shadow agent flags to Ah Mei: "New employee Raj viewed 47 employee profiles today.
                               This is unusual. Want me to limit directory access
                               to his own team?"
```

---

## 4. Default Knowledge Clearance

### 4.1 PDPA to PACT Clearance Mapping

Singapore's Personal Data Protection Act already classifies personal data. Arbor already enforces PDPA access logging via `PdpaAccessLog`. The mapping to PACT clearance levels (using EATP naming convention) is natural:

| PDPA Category                  | PACT Level        | Rationale                                            |
| ------------------------------ | ----------------- | ---------------------------------------------------- |
| Public business information    | PUBLIC (C0)       | Company name, org chart, policies, public holidays   |
| Personal data (non-sensitive)  | RESTRICTED (C1)   | Names, departments, leave balances, attendance       |
| Personal data (PDPA-protected) | CONFIDENTIAL (C2) | Salary, NRIC, bank details, performance reviews      |
| Sensitive personal data        | SECRET (C3)       | Medical records, disability status, criminal records |
| N/A for SME                    | TOP_SECRET (C4)   | Not used -- reserved for enterprises                 |

### 4.2 Auto-Classification of All 77 DataFlow Models

Every model in `company_user.py` receives a default classification. The classification is assigned at the model level, not the record level (individual records can be upgraded but not downgraded from the model default).

**PUBLIC (C0) -- Day-to-day operations, visible to all company members:**

| Model                  | Justification                                   |
| ---------------------- | ----------------------------------------------- |
| Company                | Company profile is organizational knowledge     |
| CompanyPolicy          | Policies should be accessible to all employees  |
| PublicHoliday          | Public information                              |
| Organization           | Org structure is public within the company      |
| Branch                 | Location information is operational             |
| HolidayGroup           | Calendar information                            |
| LeaveTypeConfig        | Leave rules are policy, not private data        |
| ShiftTemplate          | Shift definitions are operational               |
| ClaimCategory          | Claim rules are policy                          |
| AppraisalTemplate      | Template structure (not filled responses)       |
| AppraisalPeriod        | Period dates are organizational                 |
| CostCentre             | Cost centres are organizational                 |
| Project                | Project names and dates are operational         |
| ProjectRole            | Role definitions are organizational             |
| JobListing             | Published job listings are intentionally public |
| Template               | Document templates are operational              |
| ContentUpdate          | Regulatory updates are informational            |
| InventoryLocation      | Location data is operational                    |
| InventoryCategory      | Category definitions are operational            |
| PayItem                | Pay item definitions (not amounts) are policy   |
| PayScheme              | Scheme structures (not individual amounts)      |
| LatenessSettings       | Policy settings                                 |
| EarlyDepartureSettings | Policy settings                                 |
| AttendanceSettings     | Policy settings                                 |
| ShiftHourlyRate        | Rate definitions (operational)                  |
| ShiftMultiplier        | Multiplier definitions (operational)            |
| PayslipSettings        | Display settings                                |
| ApprovalGroup          | Approval structure is organizational            |

**RESTRICTED (C1) -- Accessible to the employee (own) + manager (team) + HR:**

| Model                           | Justification                               |
| ------------------------------- | ------------------------------------------- |
| User                            | User accounts contain email and preferences |
| Conversation                    | Advisory conversation threads               |
| AdvisorySession                 | Advisory Q&A content                        |
| LeaveApplication                | Leave details are personal                  |
| LeaveBalance                    | Balance data is personal                    |
| LeavePolicy                     | Policy assignments reveal groupings         |
| LeavePolicyEntitlement          | Entitlement details                         |
| AttendanceRecord                | Daily attendance is personal                |
| TimesheetApproval               | Timesheet data is personal                  |
| ShiftAssignment                 | Individual schedule is personal             |
| ShiftPublish                    | Publication audit trail                     |
| Claim                           | Claim submissions are personal              |
| ClaimItem                       | Individual claim items                      |
| ClaimGroup                      | Grouped claims                              |
| ClaimAuditEntry                 | Claim workflow audit                        |
| EmployeeSkill                   | Skills and certifications                   |
| EmployeeEvent                   | Timeline of changes                         |
| EmployeeNote (non-confidential) | General performance notes                   |
| EmploymentEvent                 | Career events                               |
| CustomFieldValue                | Custom data values                          |
| CustomFieldDefinition           | Field definitions                           |
| ProjectAssignment               | Who is on which project                     |
| ProjectAllocation               | Salary allocation percentages               |
| ProjectOverhead                 | Project cost data                           |
| TimesheetEntry                  | Project time entries                        |
| InventoryItem                   | Item assignments are personal               |
| InventoryMovement               | Movement audit trail                        |
| InventoryRequest                | Personal requests                           |
| Appraisal                       | Individual appraisal content                |
| Candidate                       | Candidate personal data                     |
| InterviewSchedule               | Interview details                           |
| InterviewFeedback               | Feedback content                            |
| Invitation                      | Invitation tokens                           |
| CompanyLLMConfig                | Company AI configuration                    |
| CompanyLLMUsage                 | Usage metrics                               |
| UserLLMConfig                   | Personal AI configuration                   |
| AdminPermission                 | Permission assignments                      |

**CONFIDENTIAL (C2) -- Requires HR or Finance role, PDPA-logged:**

| Model                           | Justification                          |
| ------------------------------- | -------------------------------------- |
| Employee (salary fields)        | Salary is PDPA-protected personal data |
| Employee (NRIC fields)          | NRIC is PDPA-protected                 |
| Employee (bank fields)          | Banking details are PDPA-protected     |
| SalaryComponent                 | Salary breakdown is financial PII      |
| Payslip                         | Individual pay details                 |
| PayslipItem                     | Pay line items                         |
| PayrollRun                      | Aggregate payroll data                 |
| PayrollLineItem                 | Individual payroll entries             |
| CpfYtdRecord                    | Statutory contribution records         |
| TaxFiling                       | Tax filing data                        |
| EmployeeNote (confidential)     | Flagged as confidential by creator     |
| EmployeeDocument (confidential) | Flagged as confidential                |
| PdpaAccessLog                   | Access audit trail itself is sensitive |
| EmergencyContact                | Family contact information             |
| FamilyMember                    | Family member PII (NRIC, DOB)          |

**SECRET (C3) -- Not auto-assigned. Reserved for explicit upgrade:**

No model defaults to SECRET. This level is reserved for:

- Medical certificates with diagnosis details
- Disability accommodation records
- Criminal background check results
- Pending termination records (before announcement)
- Whistleblower reports

SECRET classification is applied to individual records, not model defaults, when an authorized user (owner or HR manager with clearance) explicitly marks a record.

### 4.3 Default Posture: Restrictive with Automatic Loosening

The default is **restrictive**: every user starts at RESTRICTED clearance (C1) with access only to PUBLIC data and their own RESTRICTED records.

Clearance upgrades happen automatically based on role template:

| User Role  | Auto-Granted Clearance | Justification                                 |
| ---------- | ---------------------- | --------------------------------------------- |
| owner      | CONFIDENTIAL (C2)      | Needs full visibility into company finances   |
| hr_manager | CONFIDENTIAL (C2)      | Needs access to employee PII for HR functions |
| consultant | RESTRICTED (C1)        | Advisory access, not operational              |
| employee   | RESTRICTED (C1)        | Own records only                              |

This means Ah Mei (hr_manager) can access salary data from day one without any manual clearance setup. The template envelope already scopes her access correctly. PACT enforcement is invisible because the defaults match what she needs.

---

## 5. The Verification Gradient as UX

### 5.1 Human-Readable Gradient

PACT's four zones map to natural UX patterns:

| PACT Zone     | UX Treatment                            | User Sees                                          |
| ------------- | --------------------------------------- | -------------------------------------------------- |
| Auto-approved | Action completes immediately            | Nothing special -- it just works                   |
| Flagged       | Action completes + notification appears | Blue info badge: "Heads up: [description]"         |
| Held          | Action pauses, approval request sent    | Yellow prompt: "This needs [name]'s OK"            |
| Blocked       | Action denied with explanation          | Red message: "This isn't allowed because [reason]" |

### 5.2 UX Copy for Each Zone

**Auto-approved (invisible):**
No UI element. The action just completes. The audit trail records it silently.

**Flagged (gentle notification):**

```
"Heads up -- Sarah is applying for leave during the December peak period.
This has been approved automatically per your leave policy, but you might
want to check team coverage."
```

```
"John approved a $480 claim today. This is within policy limits but higher
than his usual monthly claims ($180 average)."
```

**Held (approval required):**

```
"Ah Mei wants to run payroll for March ($47,200 total).
This needs your approval before it goes through.
[Approve] [Review Details] [Decline]"
```

```
"Sarah submitted a termination letter for review. This needs
HR Manager approval before it can be sent.
[Review & Approve] [Request Changes] [Decline]"
```

**Blocked (not permitted):**

```
"You can't access salary records for other employees.
If you need this for your work, ask your manager to
update your permissions."
```

```
"CPF submissions can only be done by the company owner
or designated finance officer. Ask Boss to submit this,
or ask them to give you submission access."
```

### 5.3 Gradient Defaults by Template

Each template envelope includes default gradient thresholds. These are not exposed as configuration -- they are built into the template:

**tmpl_owner:**

- Almost everything is auto-approved (owner has widest envelope)
- Flagged: unusually large transactions (>$10,000), bulk operations (>10 records)
- Held: government submissions (double-confirm in PACE), delete operations
- Blocked: delete audit records (no one can do this)

**tmpl_hr_manager:**

- Auto-approved: leave management, attendance, standard employee operations
- Flagged: accessing salary data outside normal patterns, modifying another manager's team
- Held: payroll approval, termination workflows, statutory submissions
- Blocked: modifying statutory rates, accessing medical records without justification

**tmpl_employee_self:**

- Auto-approved: view own records, apply leave, clock in/out, submit claims
- Flagged: applying for >5 consecutive days leave, claims above monthly average
- Held: nothing (employees don't have authority that requires holding)
- Blocked: accessing other employees' data, any admin function, any financial approval

### 5.4 Integration with PACE

The PACE loop (Preview, Approve, Confirm, Exit) already implements held actions. PACT-lite extends PACE:

- **Autonomous** PACE actions that fall within the auto-approved zone execute immediately (as today)
- **Propose** PACE actions that fall within the flagged zone execute after single confirmation + notification
- **Always_propose** PACE actions that fall within the held zone require the approval of the role's supervisor (not just the user themselves)
- **Double_confirm** PACE actions (government submissions) require both the user and their supervisor

The existing `trust_level` field in `ShadowIntent` and `PaceSession` maps directly:

| PACE trust_level | PACT gradient zone | PACT-lite behavior                                      |
| ---------------- | ------------------ | ------------------------------------------------------- |
| autonomous       | auto-approved      | Execute, log silently                                   |
| propose          | flagged            | Execute after user confirms, notify supervisor          |
| always_propose   | held               | Execute after user confirms + supervisor approves       |
| double_confirm   | held (elevated)    | Execute after user confirms twice + supervisor approves |

---

## 6. Shadow Agent as PACT Operator

### 6.1 The Core Loop: Observe, Infer, Suggest, Confirm, Enforce

The shadow agent becomes the primary mechanism through which PACT governance evolves:

```
                    +------------------+
                    |   User Actions   |
                    +--------+---------+
                             |
                    +--------v---------+
                    |    OBSERVE       |  ObservationStore records every action
                    |  (passive, silent)|  with module, action, target, timestamp
                    +--------+---------+
                             |
                    +--------v---------+
                    |    INFER         |  PactInferenceEngine compares observed
                    |  (compute, silent)|  behavior against current D/T/R + envelopes
                    +--------+---------+
                             |
                    +--------v---------+
                    |    SUGGEST       |  Shadow agent surfaces governance suggestions
                    |  (proactive)     |  to owner/admin via nudges or briefing
                    +--------+---------+
                             |
                    +--------v---------+
                    |    CONFIRM       |  Owner/admin approves, modifies, or
                    |  (human judgment)|  dismisses the suggestion
                    +--------+---------+
                             |
                    +--------v---------+
                    |    ENFORCE       |  PACT tree updated, envelopes modified,
                    |  (automatic)     |  EATP records created for audit
                    +--------+---------+
```

### 6.2 What the Shadow Agent Observes

The existing `ObservationStore` tracks page views and clicks. PACT-lite extends observation to track:

1. **Action patterns**: Which modules does each user interact with? How frequently? What time of day?
2. **Access patterns**: Which data does each user access? Do they access data outside their department?
3. **Approval patterns**: Who approves what? How quickly? Are approvals rubber-stamped or reviewed?
4. **Boundary events**: Which actions are held or blocked? How does the human respond? Do they approve or deny?
5. **Cross-department interactions**: Does the Admin person regularly access Operations data? Does the Supervisor access Finance reports?

### 6.3 Suggestion Types

The shadow agent produces five categories of PACT governance suggestions:

**Category 1: Structural Suggestions (D/T/R changes)**

```
"You now have 5 employees in Operations and 3 in Sales. Want me to create
separate team structures for each? This helps with approval routing and
data access."

"Ah Mei has been the only person handling HR, Finance, and Admin.
As you grow, you might want to separate these into distinct teams.
For now, I've noted that she has cross-functional access."
```

**Category 2: Envelope Refinement (widening or tightening)**

```
"Ah Mei has tried to approve payroll 4 times this month and you've
approved every time. Want to give her direct payroll approval access?"

"New hire Raj has been downloading the full employee directory daily.
This is unusual -- most employees access the directory 2-3 times per
week. Want me to flag this behavior going forward?"
```

**Category 3: Clearance Adjustments**

```
"Sarah in Operations needs to view project cost reports for her
supervisor role, but she currently can't access financial data.
Want to give her read-only access to project budgets?"

"John's medical certificate was uploaded with diagnosis details visible.
I've automatically classified this as restricted. Only you and Ah Mei
can access it."
```

**Category 4: Approval Flow Optimization**

```
"Leave approvals under 3 days are always approved within 5 minutes.
Want me to auto-approve leave requests under 3 days and just
notify you?"

"Claims under $50 are always approved. Want to set those to
auto-approve so your team doesn't have to wait?"
```

**Category 5: Compliance Alerts**

```
"Ah Mei accessed 12 employees' NRIC data today without the usual
payroll or CPF context. This is tracked in the PDPA log.
No action needed if this was for a legitimate purpose."

"Your Operations team has been working overtime consistently.
Singapore law requires overtime records to be kept for 2 years.
I'm making sure all records are preserved."
```

---

## 7. Progressive Disclosure Timeline

### Day 1: Invisible PACT

**What happens:**

- Company registers, adds departments and employees
- `seed_company_defaults()` runs (policies, leave types, claim categories)
- PACT-lite auto-generates D/T/R tree from employee data
- Template envelopes assigned based on designations
- Knowledge clearance auto-classified for all models
- Verification gradient active with template defaults

**What the user sees:**

- Normal Arbor onboarding
- Everything works as before
- No mention of governance, envelopes, or clearance

**What PACT is doing silently:**

- Every action logged with PACT address context
- Every data access checked against clearance (but all pass because templates match needs)
- Shadow agent begins building observation profiles

### Week 1-2: Observation Phase

**What happens:**

- Shadow agent accumulates behavioral data across all users
- Observation patterns begin to stabilize (Ah Mei's workflow becomes clear)
- No suggestions yet -- minimum 7 days of observation before first suggestion

**What the user sees:**

- Morning briefings (already exist) -- unchanged
- Nudges (already exist) -- unchanged
- Possibly a very gentle first suggestion if a clear pattern emerges

### Week 2-4: First Suggestions

**What the shadow agent suggests:**

```
Morning briefing item:
"I've noticed your team has settled into a routine. Here are some
things I can set up to make approvals faster:

- Auto-approve leave requests under 2 days (you've approved all
  12 of these this month within minutes)
- Let Ah Mei process payroll directly (you've approved her payroll
  runs 3 months in a row)

[Set these up] [Tell me more] [Not now]"
```

**If the owner selects "Set these up":**

- Leave auto-approval threshold created in the verification gradient
- Ah Mei's envelope widened to include payroll approval
- EATP records created for both changes
- Shadow agent confirms: "Done. Ah Mei can now approve payroll directly, and short leave requests will be auto-approved. I'll let you know if anything unusual comes up."

**If the owner selects "Not now":**

- Suggestion is dismissed
- Shadow agent will re-suggest in 2 weeks if the pattern persists
- After 3 dismissals, the shadow agent stops suggesting this specific change

### Month 2-3: Structural Suggestions

**What the shadow agent suggests:**

```
"Your company has grown to 15 people across 4 departments.
I've been tracking how work flows between teams:

- HR handles leave for everyone (as expected)
- Operations team needs attendance data from Admin
- Sales team submits expenses that Finance reviews

Want me to set up formal data sharing between these teams?
This means:
- Operations can see their team's attendance (already happening informally)
- Finance gets automatic access to Sales expense claims
- HR retains access to all employee data company-wide

[Set up team connections] [Show me what changes] [Not now]"
```

### Month 4-6: Full PACT Running

By this point, the shadow agent has:

- Confirmed or created 3-5 structural suggestions
- Refined 5-10 envelope parameters based on observed behavior
- Established 2-4 cross-department bridges
- Set up 3-6 auto-approval thresholds
- Maintained full EATP audit trail for every change

The company now has a fully governed PACT structure that was configured entirely through observation and confirmation, with zero manual setup.

### 6 Months+: Ongoing Refinement

The shadow agent continues to:

- Monitor for new patterns (new employees, changed workflows)
- Flag anomalies against established baselines
- Suggest governance updates when the company grows or restructures
- Maintain compliance alerts for Singapore regulatory requirements

---

## 8. Data Model Changes

### 8.1 New Models (added to company_user.py)

```python
@db.model
class PactNode:
    """D/T/R node in the PACT organizational tree."""
    company_id: int
    node_type: str = ""  # "D" / "T" / "R" / "BOD"
    name: str = ""
    address: str = ""  # Positional address e.g. "D1-R1-D2-R1"
    parent_address: str = ""
    employee_id: Optional[int] = None  # For R nodes: which employee occupies this role
    is_vacant: bool = False
    is_primary_head: bool = False  # True for the mandatory head R of a D/T
    is_inferred: bool = True  # True if auto-generated, False if human-confirmed
    address_history: Optional[dict] = None  # Previous addresses for audit
    source: str = "auto"  # "auto" / "shadow_suggestion" / "manual"

@db.model
class PactEnvelope:
    """Operating envelope for a role (R node)."""
    company_id: int
    role_address: str = ""  # PACT address of the R node
    template_id: str = ""  # Which template was used as base
    financial: Optional[dict] = None  # Five-dimension envelope as JSON
    operational: Optional[dict] = None
    temporal: Optional[dict] = None
    data_access: Optional[dict] = None
    communication: Optional[dict] = None
    gradient_config: Optional[dict] = None  # Verification gradient thresholds
    defined_by_address: str = ""  # PACT address of the defining role
    is_inferred: bool = True
    source: str = "template"  # "template" / "shadow_suggestion" / "manual"

@db.model
class PactClearance:
    """Knowledge clearance for a role."""
    company_id: int
    role_address: str = ""
    max_clearance: str = "restricted"  # public/restricted/confidential/secret/top_secret
    compartments: Optional[dict] = None  # JSON array of compartment names
    granted_by_address: str = ""
    is_auto_granted: bool = True  # True if derived from template

@db.model
class PactSuggestion:
    """Shadow agent PACT governance suggestion."""
    company_id: int
    suggestion_type: str = ""  # structural/envelope/clearance/approval/compliance
    title: str = ""
    description: str = ""
    evidence: Optional[dict] = None  # Observation data supporting this suggestion
    proposed_changes: Optional[dict] = None  # What would change if accepted
    status: str = "pending"  # pending/accepted/dismissed/expired
    target_address: str = ""  # Which PACT node this affects
    suggested_at: str = ""
    resolved_at: str = ""
    resolved_by: Optional[int] = None
    dismiss_count: int = 0  # How many times similar suggestions were dismissed

@db.model
class PactAuditEvent:
    """Audit trail for PACT governance actions."""
    company_id: int
    event_type: str = ""  # tree_compiled/envelope_created/clearance_granted/suggestion_accepted/etc
    actor_address: str = ""  # Who triggered this
    target_address: str = ""  # What was affected
    details: Optional[dict] = None  # Full change details
    eatp_record_id: str = ""  # Link to EATP trust record
```

### 8.2 Model Classification Registry

A static registry maps each model to its default PACT clearance level (using EATP naming: public/restricted/confidential/secret/top_secret):

```python
MODEL_CLEARANCE_REGISTRY: dict[str, str] = {
    "Company": "public",
    "CompanyPolicy": "public",
    "PublicHoliday": "public",
    # ... (all 77 models mapped as per Section 4.2)
    "Employee": "confidential",  # Model-level; individual fields may vary
    "Payslip": "confidential",
    "FamilyMember": "confidential",
}
```

---

## 9. Integration Points

### 9.1 Company Seeding (`company_seeding.py`)

Add to `seed_company_defaults()`:

```python
("pact_tree", _seed_pact_tree),
("pact_envelopes", _seed_pact_envelopes),
("pact_clearances", _seed_pact_clearances),
```

The PACT seeding happens after employees are seeded. It reads the existing employee data and generates the initial D/T/R tree, template envelopes, and clearance assignments.

### 9.2 Auth Middleware (`auth_middleware.py`)

Add PACT context to the auth payload:

```python
# After JWT validation, look up the user's PACT address
pact_address = get_user_pact_address(user_id, company_id)
payload["pact_address"] = pact_address
payload["pact_clearance"] = get_effective_clearance(pact_address)
```

### 9.3 Shadow Agent Observation (`observation.py`)

Extend `record_observation()` to include PACT context:

```python
entry["pact_address"] = user_pact_address
entry["target_model"] = model_name  # Which DataFlow model was accessed
entry["target_clearance"] = model_clearance  # Clearance level of accessed data
entry["envelope_check"] = "auto" / "flagged" / "held" / "blocked"
```

### 9.4 PACE Integration (`pace.py`)

Extend `PaceSession` to include envelope validation:

```python
# Before executing a PACE session, validate against the user's effective envelope
effective_envelope = compute_effective_envelope(user_pact_address)
for step in session.steps:
    gradient_zone = evaluate_gradient(step, effective_envelope)
    if gradient_zone == "blocked":
        step.status = "blocked"
        step.block_reason = "Outside your current permissions"
    elif gradient_zone == "held":
        step.requires_supervisor_approval = True
        step.supervisor_address = get_parent_role_address(user_pact_address)
```

### 9.5 Briefing Service (`briefing.py`)

Add PACT governance items to the morning briefing:

```python
def _pact_governance_items(company_id: int, user_pact_address: str) -> list[dict]:
    """Surface pending PACT suggestions and governance alerts."""
    suggestions = get_pending_suggestions(company_id, user_pact_address)
    return [format_suggestion_as_briefing_item(s) for s in suggestions]
```

### 9.6 Nudge Service (`nudges.py`)

Add PACT-specific nudges:

```python
def _nudges_pact(company_id: int, user_pact_address: str) -> list[dict]:
    """PACT governance nudges."""
    # E.g., "3 employees don't have reporting managers set"
    # E.g., "Ah Mei's access patterns suggest she needs Finance access"
    ...
```

---

## 10. Success Criteria

### Measurable Outcomes

| Metric                              | Target                   | Measurement                                          |
| ----------------------------------- | ------------------------ | ---------------------------------------------------- |
| PACT setup time for new company     | 0 seconds (automatic)    | No additional onboarding steps                       |
| Time to first governance suggestion | 7-14 days                | Shadow agent observation window                      |
| Owner interaction with governance   | <5 minutes/month         | Confirmation clicks only                             |
| Suggestion acceptance rate          | >70% after 3 months      | Suggestions are well-targeted                        |
| False block rate                    | <2% of all actions       | Restrictive defaults are not operationally crippling |
| Audit trail completeness            | 100% of governed actions | Every action has PACT address + clearance context    |
| PACT invariant violations           | 0                        | Monotonic tightening never violated                  |

### Qualitative Outcomes

- Boss never hears the word "envelope" or "clearance"
- Ah Mei can do her job from day one without permission requests
- New employees can only see their own data without any configuration
- Government submissions require double approval without anyone configuring it
- Six months in, the company has a real governance structure that emerged organically

---

## 11. Risk Register

| Risk                                         | Likelihood | Impact | Mitigation                                                            |
| -------------------------------------------- | ---------- | ------ | --------------------------------------------------------------------- |
| Template mismatch (wrong envelope for job)   | Medium     | Medium | Shadow agent detects within 1 week; suggest correction                |
| Owner ignores all suggestions                | Medium     | Low    | Defaults are safe; governance works without suggestions               |
| D/T/R inference produces wrong hierarchy     | Medium     | Low    | Shadow agent suggests corrections; any structure is better than none  |
| Restrictive defaults block legitimate work   | Low        | High   | Monitor false-block rate; shadow agent suggests loosening within days |
| Clearance auto-classification too permissive | Low        | High   | Default is restrictive; PDPA logging catches violations               |
| Performance impact of envelope checks        | Low        | Medium | Envelope checks are in-memory; clearance is cached per session        |
| User confusion about held/blocked actions    | Medium     | Medium | UX copy is natural language; no technical terms exposed               |
