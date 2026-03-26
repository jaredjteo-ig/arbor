# M63-M65: Agent Workforce — 3 User-Facing Agents

**Milestone**: M63 (Arbor HR Agent), M64 (Arbor Payroll Agent), M65 (Arbor Compliance Agent)
**Priority**: HIGH — core product differentiation
**Scope**: both
**Estimated effort**: 7-9 days

Three user-facing agents, each composed of internal capability modules.
Per gap resolution H1: 12 internal capabilities, 3 user-facing agents.
Build-now boundary: agent activation logic, service account wiring, envelope
application. The gradient enforcement engine waits for PACT core.

---

## M63: Arbor HR Agent

### T423: HR Agent activation endpoint

**Scope**: backend
**Depends**: T411, T412
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)

**Description**: Endpoint to activate a user-facing agent for a company.

`POST /api/pact/agents/{agent_id}/activate`:

- `agent_id` is the user-facing key: `arbor_hr`, `arbor_payroll`, `arbor_compliance`
- Validates `pact_enabled=True` for the company
- Creates service accounts for all internal agents in the composite
- Creates PactNode records for each agent role
- Creates default PactEnvelope for each node (from template defaults)
- Marks each node with `fill_type=agent`
- Creates PactAuditEvent: `agent_activated`
- Returns the agent detail including node addresses, capabilities, and initial envelope

`POST /api/pact/agents/{agent_id}/deactivate`:

- Marks all composite agent nodes as `fill_type=vacant`
- Routes all pending held actions to `auto_resolved` (or to owner)
- Creates PactAuditEvent: `agent_deactivated`

`GET /api/pact/agents` — list all agents for the company with their status
(inactive / active / needs_attention).

`GET /api/pact/agents/{agent_id}` — get agent detail: status, actions this
month, current capabilities, held actions count.

**Acceptance criteria**:

- [ ] Activating `arbor_hr` creates 6 internal agent nodes (hr_manager, leave_admin, attendance, onboarding, documents, shadow)
- [ ] Deactivating reverts nodes to vacant, routes held actions to owner
- [ ] Cannot activate same agent twice (idempotent)
- [ ] Only owner can activate/deactivate
- [ ] PactAuditEvent created for each activation/deactivation
- [ ] Integration test: activate arbor_hr, verify 6 service accounts exist

---

### T424: HR Agent — leave auto-approval logic

**Scope**: backend
**Depends**: T423, T407
**Files**:

- `src/hr_advisory/pact/agents/hr_agent.py` (new file)

**Description**: The core behavioral logic for the HR Agent's leave approval
capability. This is the internal implementation that respects the gradient
calibration tables (T407) and creates HeldAction records (T401) when needed.

`evaluate_leave_application(leave_application_id: int, company_id: int) -> LeaveDecision`:

- Loads the leave application
- Loads the employee's leave balance (calls existing leave service)
- Checks team coverage (how many others in the same department/team are on leave
  the same days — uses existing attendance/leave queries)
- Checks special conditions: notice period, probation, peak period, leave type
- Evaluates against gradient calibration tables (T407 `evaluate_gradient_local`)
- Returns `LeaveDecision(zone, reason, should_auto_approve, action_display, action_context, options)`

`process_leave_application(leave_application_id: int, company_id: int) -> str`:

- Calls `evaluate_leave_application`
- If zone is `auto_approved`: approves leave directly (calls existing leave approval)
- If zone is `flagged`: approves leave AND creates a notification (not a held action)
- If zone is `held`: creates HeldAction record, does NOT approve leave
- If zone is `blocked`: rejects leave directly with regulatory reason
- Returns the zone string

The HR Agent should be triggered when a new LeaveApplication is created and
`pact_enabled=True` for the company. Wire this in the leave creation flow
in `leave.py` router (add a post-creation hook).

**Acceptance criteria**:

- [ ] 2-day annual leave, sufficient balance, no overlap → auto_approved
- [ ] Leave during notice period → held
- [ ] Leave with >50% team overlap → held
- [ ] Leave with no balance → blocked
- [ ] `flagged` zone: leave approved + notification sent, no held action
- [ ] PACT disabled: agent not invoked, existing manual flow unchanged
- [ ] Unit tests for each gradient zone scenario (min 8 test cases)
- [ ] Integration test: apply for leave, verify auto-approval for routine case

---

### T425: HR Agent — attendance monitoring

**Scope**: backend
**Depends**: T423
**Files**:

- `src/hr_advisory/pact/agents/hr_agent.py` (extend)

**Description**: The attendance monitoring capability: daily absence detection,
lateness pattern detection, and overtime tracking.

`check_daily_attendance(company_id: int) -> list[AttendanceAlert]`:

- Runs once per day (add to scheduler in T414)
- For each active employee: check if they clocked in today
- Employees who haven't clocked in by 10:00 AM and have no approved leave:
  create a `HeldAction` with `urgency=routine`, `action_type=unreported_absence`
- Returns list of alerts generated

`detect_lateness_pattern(employee_id: int, company_id: int) -> Optional[PactSuggestion]`:

- Look at last 30 days of attendance
- If employee was late >3 times: generate a PactSuggestion for the boss
  ("Raju has been late 4 times this month. Want to talk to him?")
- Returns suggestion or None if below threshold

**Acceptance criteria**:

- [ ] Absent employee without leave generates held action at 10:00 AM
- [ ] Employee with approved leave does not generate absent alert
- [ ] 4 lateness events in 30 days generates PactSuggestion
- [ ] 2 lateness events does not generate suggestion
- [ ] Unit tests for detection logic

---

### T426: HR Agent — policy Q&A routing

**Scope**: backend
**Depends**: T423
**Files**:

- `src/hr_advisory/pact/agents/hr_agent.py` (extend)

**Description**: The HR Agent should intercept employee questions about HR
policies and route them to the existing advisory pipeline, but within the
agent's data clearance (RESTRICTED — no salary data).

`route_hr_question(question: str, employee_id: int, company_id: int) -> str`:

- Called when an employee asks a question via the shadow agent
- Checks if the question is HR-related (leave balance, policy, attendance)
- If yes: routes to advisory pipeline with company context but WITHOUT
  individual PII (the HR Agent is RESTRICTED clearance)
- If no: passes through to the general advisory pipeline
- Returns the response

This leverages the existing advisory infrastructure (intent classifier,
workflow composer, advisory router) with a restricted context envelope.

**Acceptance criteria**:

- [ ] "How many sick leave days do I have?" → answered using leave balance data
- [ ] "What's the company's overtime policy?" → answered using company policy
- [ ] "What's Sarah's salary?" → blocked (clearance violation)
- [ ] Existing advisory pipeline tests still pass
- [ ] Unit test: policy question routed correctly

---

### T427: HR Agent — onboarding checklist automation

**Scope**: backend
**Depends**: T423
**Files**:

- `src/hr_advisory/pact/agents/hr_agent.py` (extend)

**Description**: When a new employee is created (invitation sent), the
Onboarding Agent capability automatically:

1. Creates an onboarding task checklist (DataFlow model or uses existing EmployeeEvent)
2. Sends a welcome email to the new employee
3. Generates initial leave balances (calls existing `ensure_leave_balances()`)
4. Creates reminders for the boss if the employee hasn't completed onboarding
   tasks within 7 days

`initiate_onboarding(employee_id: int, company_id: int)`:

- Generates 8-item standard onboarding checklist:
  - Personal details form sent
  - NRIC/FIN received
  - Bank account received
  - Emergency contact received
  - Employment contract signed
  - Leave balances created
  - System access granted
  - Welcome package sent
- Stores checklist as EmployeeEvent records tagged with `event_type=onboarding_task`
- Sends welcome email with self-service onboarding form link
- Creates leave balances via `ensure_leave_balances()`

`check_onboarding_progress(employee_id: int) -> OnboardingStatus`:

- Returns completion percentage and list of incomplete tasks
- If overdue items exist (>7 days): creates PactSuggestion for boss

Wire `initiate_onboarding` to be called when a new employee record is created
and `pact_enabled=True`.

**Acceptance criteria**:

- [ ] New employee creation triggers onboarding checklist
- [ ] Welcome email sent with onboarding form link
- [ ] Leave balances created via `ensure_leave_balances()`
- [ ] 8-item checklist created as EmployeeEvent records
- [ ] Overdue items (7+ days) generate PactSuggestion
- [ ] PACT disabled: no automatic onboarding (existing manual flow)
- [ ] Integration test: create employee, verify welcome email and leave balances

---

### T428: HR Agent frontend — offer screen (onboarding step 6)

**Scope**: frontend
**Depends**: T423
**Files**:

- `apps/web/components/pact/AgentOfferCard.tsx` (new)
- `apps/web/app/(onboarding)/setup/page.tsx` (modify)

**Description**: The "First Agent Offer" screen from user flow 01 Step 6.
Shown during company onboarding after the team is imported and org chart
confirmed.

`AgentOfferCard` component:

- Agent name: "HR Agent"
- "What it handles" section: bulleted list of plain-language capabilities
- "What it does NOT do" section: bulleted list of constraints
- "Start HR Agent" CTA button + "Maybe Later" link
- Calls `POST /api/pact/agents/arbor_hr/activate` on confirmation

Onboarding flow integration:

- After user confirms org chart (`POST /api/pact/tree/confirm`), redirect to
  the agent offer screen
- If user skips: show the offer again in the next morning briefing (T422)

**Acceptance criteria**:

- [ ] Offer screen shown after org chart confirmation
- [ ] "Start HR Agent" calls activation endpoint and shows success state
- [ ] "Maybe Later" skips without activating
- [ ] Offer re-shown in morning briefing if skipped
- [ ] Mobile-first layout

---

## M64: Arbor Payroll Agent

### T429: Payroll Agent activation and payroll calculation trigger

**Scope**: backend
**Depends**: T423, T407
**Files**:

- `src/hr_advisory/pact/agents/payroll_agent.py` (new file)

**Description**: The Payroll Agent wraps the existing deterministic payroll
engine (already built in M16-M27) with PACT governance. Key principle: the
engine does the arithmetic (zero LLM), PACT handles the authority (who can
approve and submit).

`process_payroll_run_pact(payroll_run_id: int, company_id: int) -> PayrollDecision`:

- Called when a payroll run is initiated
- Evaluates gradient for `calculate_payroll` (should be auto_approved)
- If `payroll_run.variance_percentage > 5%`: creates a `flagged` notification
  (variance flag cannot be silenced — from payroll gradient table)
- When boss approves run: evaluates gradient for `approve_payroll_run` → HELD
  for boss
- When boss approves: generates payslips, generates CPF file, generates GIRO file
- `submit_cpf_to_board` → HELD (separate action, double-confirm required)

`schedule_monthly_payroll(company_id: int)`:

- After 3 months of successful runs, offer "prepare automatically" (T437)
- If accepted: create a scheduled task to run `initiate_payroll_calculation`
  on the 24th of each month
- Grace period: if payroll agent is not yet activated, remind boss to activate

Wire payroll calculation to be triggered automatically on the 24th of each
month if `payroll_auto_prepare=True` on the company.

Add `payroll_auto_prepare: Boolean default False` to Company model.

**Acceptance criteria**:

- [ ] Manual payroll calculation → auto_approved (gradient)
- [ ] Variance >5% → flagged notification
- [ ] `approve_payroll_run` → held (boss confirmation required)
- [ ] `submit_cpf` → separate held action
- [ ] Auto-prepare on 24th if `payroll_auto_prepare=True`
- [ ] Payroll engine calculations unchanged (zero LLM, deterministic)
- [ ] Integration test: initiate payroll, verify held action created for approval

---

### T430: Bridge activation — leave/attendance/claims to payroll

**Scope**: backend
**Depends**: T429, T408
**Files**:

- `src/hr_advisory/pact/bridges/bridge_service.py` (new file)

**Description**: When the Payroll Agent is activated, activate the 3 data bridges
that feed payroll calculations (leave deductions, overtime hours, claim
reimbursements). These bridges already exist in the domain config (T408); this
task implements the activation logic and the data fetch functions.

`activate_bridge(bridge_id: str, company_id: int)`:

- Marks the bridge as active in a `CompanyBridge` junction model
- Creates PactAuditEvent: `bridge_activated`

`get_leave_data_for_payroll(company_id: int, period_start: date, period_end: date)`:

- Fetches approved leave applications for the period
- Returns only the fields specified in `bridge_leave_payroll.data_flows`
- Validates classification ceiling (restricted — no salary data)

`get_attendance_data_for_payroll(company_id: int, period_start: date, period_end: date)`:

- Fetches overtime hours from attendance records
- Returns only the fields in `bridge_attendance_payroll.data_flows`

`get_claims_data_for_payroll(company_id: int, period_start: date, period_end: date)`:

- Fetches approved claims for reimbursement inclusion
- Returns only the fields in `bridge_claims_payroll.data_flows`

The existing payroll engine already calls these queries; this task wraps them
in bridge-aware functions that respect classification constraints.

`CompanyBridge` DataFlow model:

- `company_id`, `bridge_id`, `is_active: bool`, `activated_at`, `activated_by`

**Acceptance criteria**:

- [ ] Activating Payroll Agent also activates the 3 payroll bridges
- [ ] Bridge data fetch functions return only allowed fields
- [ ] `CompanyBridge` records persisted
- [ ] Deactivating Payroll Agent deactivates its bridges
- [ ] Integration test: payroll run uses bridge data for leave deductions

---

### T431: Payroll Agent offer screen and activation UX

**Scope**: frontend
**Depends**: T429
**Files**:

- `apps/web/app/(dashboard)/payroll/page.tsx` (modify)
- `apps/web/components/pact/PayrollAgentOffer.tsx` (new)
- `apps/web/components/pact/PayrollProgressStepper.tsx` (new)

**Description**: The Payroll Agent activation UX from user flow 02 Steps 1-3.
Shown in the morning briefing when payroll month-end approaches and the agent
has not been activated.

`PayrollAgentOffer` component:

- Triggered by morning briefing suggestion ("Payroll is due tomorrow. Arbor
  can calculate payroll for you.")
- Shows capabilities checkmark list (from T429 agent definition)
- Shows "does NOT do" lock list
- "Try Payroll Agent" CTA
- "Not This Month" dismiss button

`PayrollProgressStepper` component:

- Shows on the payroll run page when Payroll Agent calculates
- Steps: "Pulled salary data", "Calculated CPF", "Applied SDL/SHG",
  "Checked leave deductions", "Checked overtime", "Generated payslips",
  "Ready for review"
- Progress bar animation
- Each step shows [done] / [now] / [pending] status

**Acceptance criteria**:

- [ ] Offer shown in morning briefing section when payroll month-end
- [ ] Activation calls `POST /api/pact/agents/arbor_payroll/activate`
- [ ] Progress stepper animates through calculation steps
- [ ] "Not This Month" dismisses for current month only (re-shown next month)

---

### T432: Payroll review and approval page updates

**Scope**: frontend
**Depends**: T431, T416
**Files**:

- `apps/web/app/(dashboard)/payroll/[id]/review/page.tsx` (new)

**Description**: The payroll review screen from user flow 02 Step 3, showing
the agent-calculated payroll summary before boss approval.

Page layout:

- SUMMARY section: total gross, CPF (employee), CPF (employer), SDL, SHG, net pay
- EMPLOYEES section: table with name, gross, CPF employee, net pay columns
- NOTES section: changes from last month, flagged items (variance)
- Action buttons: [Approve Payroll] [Make Changes] [Cancel Run]
- Tap employee name → shows detailed payslip (existing payslip page)

"Make Changes" flow:

- Radio options: "salary is wrong", "calculation looks wrong", "add bonus/deduction",
  "exclude an employee"
- Free text field for description
- Submit → creates a HeldAction for the boss-agent correction conversation
  (or routes to the relevant edit screen)

Variance flag display:

- If payroll has a flagged variance: show orange banner with explanation
  "Net pay is $1,240 lower than February. Reason: David Lee's salary was adjusted."

**Acceptance criteria**:

- [ ] Summary totals match payroll run data
- [ ] Variance flag shown when run has flagged items
- [ ] [Approve Payroll] creates a held action for final approval
- [ ] Employee row tap shows existing payslip detail page
- [ ] "Make Changes" shows contextual options

---

## M65: Arbor Compliance Agent

### T433: Compliance Agent — work pass expiry monitoring

**Scope**: backend
**Depends**: T423
**Files**:

- `src/hr_advisory/pact/agents/compliance_agent.py` (new file)

**Description**: Work pass expiry is a high-impact compliance issue for
Singapore SMEs with foreign workers (EPF, S-Pass, WP). The Compliance Agent
monitors expiry dates and creates escalating held actions.

`check_work_pass_expiries(company_id: int) -> list[WorkPassAlert]`:

- Loads all active employees with `work_pass_expiry` date set
- 60 days before expiry: create PactSuggestion (informational)
- 30 days before expiry: create HeldAction with urgency=urgent
  "John's S Pass expires in 30 days. Action needed now."
- 7 days before expiry: create HeldAction with urgency=deadline
  "URGENT: John's S Pass expires in 7 days. Stop work assignment immediately."
- On expiry: create blocked alert — work assignment should be prevented

Run this check daily as part of the notification scheduler (T414).

`check_outstanding_work_passes(company_id: int) -> list[Employee]`:

- Returns employees who should have work passes (non-citizen/non-PR) but
  have no `work_pass_number` or `work_pass_expiry` on file
- Generates PactSuggestion: "Raj may need a work pass. Want me to check?"

**Acceptance criteria**:

- [ ] 60-day expiry: PactSuggestion created
- [ ] 30-day expiry: urgent HeldAction created
- [ ] 7-day expiry: deadline HeldAction created
- [ ] Already expired: compliance flag on employee profile
- [ ] Employees without pass data generate a suggestion
- [ ] Check runs daily without duplicate alerts (idempotent)
- [ ] Unit tests for all expiry scenarios

---

### T434: Compliance Agent — filing deadline tracker

**Scope**: backend
**Depends**: T433
**Files**:

- `src/hr_advisory/pact/agents/compliance_agent.py` (extend)

**Description**: Track statutory filing deadlines and remind the boss
before they become urgent.

`get_filing_deadlines(company_id: int, year: int) -> list[FilingDeadline]`:

- Returns all filing deadlines for the company's fiscal year:
  - CPF monthly submission (14th of each month)
  - IR8A annual filing (1 March of following year)
  - NS makeup pay (within 3 months of NS duty)
  - GST quarterly/monthly (if company is GST-registered)
- `FilingDeadline(name, due_date, description, advance_notice_days)`

`check_approaching_deadlines(company_id: int) -> list[HeldAction]`:

- 14 days before: create informational held action (routine urgency)
- 5 days before: create urgent held action
- Day of: create deadline held action

Run daily as part of scheduler.

**Acceptance criteria**:

- [ ] CPF deadline for each month is tracked
- [ ] IR8A annual deadline is tracked
- [ ] 14-day advance notice creates routine held action
- [ ] 5-day notice creates urgent held action
- [ ] Duplicate alerts prevented (one alert per deadline per notification level)
- [ ] Integration test: company with employees, verify CPF deadlines appear

---

### T435: Compliance Agent — regulatory update monitoring

**Scope**: backend
**Depends**: T433
**Files**:

- `src/hr_advisory/pact/agents/compliance_agent.py` (extend)

**Description**: Monitor the knowledge base for regulatory updates and surface
action-required changes to the boss. The knowledge base pipeline already receives
regulatory updates via the `arbor-regulatory` MCP server; this task wires them
to the compliance agent.

`monitor_regulatory_updates(company_id: int) -> list[ComplianceAlert]`:

- Queries ContentUpdate records created in the last 30 days
- Filters for updates tagged with `requires_action=True`
- For each action-required update:
  - 14+ days to deadline: PactSuggestion ("CPF rate changed. New rates applied
    automatically to your payroll.")
  - <14 days to deadline: HeldAction (urgent)
  - CPF rate changes: auto-update the payroll engine's rate tables AND create
    a flagged notification ("I've updated your CPF rates for January 2027.")

`apply_cpf_rate_change(effective_date: date)`:

- When CPF board publishes new rates (January and September each year):
  detects the change in the knowledge base
- Auto-updates the CPF rate tables used by the payroll engine
- Creates PactSuggestion for the boss: "CPF rates updated for {date}.
  Your next payroll run will use the new rates."

This is the "compliance aha moment" from the value proposition critique:
"Your agents handled something you didn't even know needed handling."

**Acceptance criteria**:

- [ ] ContentUpdate with `requires_action=True` triggers compliance alert
- [ ] CPF rate change: auto-applied to payroll tables + notification sent
- [ ] Informational regulatory changes: PactSuggestion (not HeldAction)
- [ ] Action-required updates with deadline: HeldAction
- [ ] Unit test: new CPF rate detected, payroll tables updated, notification created

---

### T436: Compliance Agent offer and dashboard

**Scope**: frontend
**Depends**: T433, T434
**Files**:

- `apps/web/app/(dashboard)/compliance/page.tsx` (modify)
- `apps/web/components/pact/ComplianceAgentDashboard.tsx` (new)
- `apps/web/components/pact/ComplianceTimeline.tsx` (new)

**Description**: The compliance monitoring UI surfaces filing deadlines, work
pass expiries, and regulatory alerts in one place.

`ComplianceAgentDashboard`:

- Filing deadlines section: next 3 upcoming deadlines with days-remaining
- Work pass expiries: employees with passes expiring in 90 days
- Regulatory alerts: active alerts from ContentUpdate monitoring
- "All clear" state when no active issues

`ComplianceTimeline`:

- Visual timeline showing upcoming deadlines (next 6 months)
- Color-coded: green (>30 days), orange (14-30 days), red (<14 days)
- Each deadline links to the relevant held action (if created)

Compliance nav item in sidebar: badge count for active compliance issues.

**Acceptance criteria**:

- [ ] Filing deadlines shown with days-remaining countdown
- [ ] Work pass expiries listed with employee name and urgency
- [ ] Timeline visualization for next 6 months of deadlines
- [ ] Badge count in sidebar for active compliance issues
- [ ] Clicking a deadline item navigates to the held action
