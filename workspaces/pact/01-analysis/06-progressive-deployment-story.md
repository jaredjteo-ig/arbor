# Progressive Deployment Story: From Registration to Full AI HR Department

**Date**: 2026-03-21
**Status**: Working Draft
**Context**: The user journey from a boss registering on Arbor to having a fully governed AI HR department running autonomously

---

## The Guiding Principle

Arbor earns trust the way a good employee does: by showing up, doing the basics well, asking before acting on anything important, and gradually taking on more responsibility as the boss sees consistent competence. PACT makes this safe because every expansion of agent authority is governed, auditable, and reversible.

---

## Day 1: Registration and Invisible Setup

### What the Boss Does

1. Signs up on Arbor
2. Creates company profile (name, UEN, sector)
3. Adds employees (name, email, department, designation, reporting manager)

This is a 15-minute process. No governance questions. No configuration panels. No mention of agents, envelopes, or organizational trees.

### What the Boss Sees

A clean dashboard showing:

- Company overview (headcount, departments)
- Employee directory
- Quick actions: "Add employee," "View policies," "Ask a question"
- A welcome message: "I'm setting up your HR system. You can start asking employment law questions right away."

### What Happens Behind the Scenes

**PACT tree auto-generated:**

```
Input: Boss (Owner, Management), Ah Mei (HR Manager, Admin),
       John (Supervisor, Operations), 7 staff (Operations)

Output:
BOD (vacant)
D1 (Company)
  D1-R1 (Boss — Director)          [HUMAN]
    D1-R1-D1 (Admin)
      D1-R1-D1-R1 (Ah Mei — HR Manager)  [HUMAN + SHADOW]
    D1-R1-D2 (Operations)
      D1-R1-D2-R1 (John — Supervisor)    [HUMAN + SHADOW]
        D1-R1-D2-R1-R2..R8 (Staff)       [HUMAN — self-service]
```

**Template envelopes assigned:**

- Boss: tmpl_owner
- Ah Mei: tmpl_hr_manager
- John: tmpl_supervisor
- Staff: tmpl_employee_field (Operations) or tmpl_employee_office

**Knowledge clearance auto-classified:**

- All 77+ models get default PACT clearance levels
- Boss: CONFIDENTIAL access
- Ah Mei: CONFIDENTIAL access (HR Manager template)
- John: RESTRICTED access (Supervisor template)
- Staff: RESTRICTED access (own records only)

**Agent roles created but dormant:**

- HR Manager Agent (D1-R1-R2): dormant — Ah Mei fills this as human
- Payroll Agent (D1-R1-R3): dormant — will activate at Month 1
- Compliance Agent (D1-R1-R4): dormant — will activate at Month 2
- Advisory Agent: ACTIVE from day 1 (existing system)
- Shadow Agent: ACTIVE from day 1 (existing system)
- Leave Administrator Agent: ACTIVE from day 1 (tracking only, not approving)

**Verification gradient active with defaults:**

- Routine self-service actions: auto-approved
- Government submissions: held for boss
- Delete operations: blocked

**Shadow agent begins silent observation.**

### What the Boss Experiences

Everything just works. The employee directory shows everyone. Leave policies are pre-configured with Singapore defaults (14 days annual, 14 days sick, 60 days hospitalization, 28 days paternity). The advisory system answers employment law questions. Nothing mentions governance.

---

## Week 1: Advisory and Leave Tracking

### What Becomes Active

| Agent               | Status                 | What It Does                                                |
| ------------------- | ---------------------- | ----------------------------------------------------------- |
| Advisory Agent      | Active                 | Answers employment law questions, runs calculators          |
| Shadow Agent        | Active                 | Observes user behavior, begins building baselines           |
| Leave Administrator | Active (tracking only) | Tracks leave balances, calculates accruals, enforces policy |

### What the Boss Sees

**Monday morning — first briefing:**

```
Good morning!

Here's your company at a glance:
- 10 employees across 2 departments
- No leave applications this week
- No upcoming filing deadlines

Quick tip: Your employees can apply for leave directly
through the app. You'll get a notification to approve.
```

**When an employee applies for leave:**

```
Sarah applied for 2 days of annual leave (March 25-26).
She has 12 days remaining.
No team overlap issues.
[Approve] [Decline]
```

The boss taps "Approve." This is the existing workflow — no agent involvement yet. The Leave Administrator Agent is tracking balances and checking policy in the background, but all approval goes to the boss (or Ah Mei, if she has hr_manager role).

**When Ah Mei asks a question:**

```
Ah Mei: "What's the paternity leave entitlement now?"

Advisory Agent: "Under the CDCSA (amended 1 Jan 2025), paternity leave
is 28 calendar days (4 weeks). This applies to:
- Singapore citizen fathers
- Child is a Singapore citizen
- Father must have served employer for 3+ continuous months

The first 14 days are employer-funded. The remaining 14 days are
government-funded (capped at $2,500/week including CPF).

Your company's leave policy already includes 28 days of paternity leave."
```

### What the Shadow Agent Records

Silently, for every user:

- Which pages they visit (employee directory, leave, attendance)
- Which actions they take (approve leave, view payslip, check balance)
- How long approvals take (boss approves Sarah's leave in 2 minutes)
- Cross-department access patterns (Ah Mei views Operations team's attendance)
- Time-of-day patterns (boss checks dashboard at 8:30 AM, Ah Mei processes leave at 10 AM)

No suggestions yet. Minimum 7 days of observation before the first suggestion.

### Agent Envelope in Effect

The Leave Administrator Agent is active but constrained:

```
Current envelope (Week 1):
  Can do: Track balances, calculate accruals, check team overlap, flag anomalies
  Cannot do: Approve leave, reject leave, encash leave, modify policy
  Gradient: All approvals route to boss/Ah Mei
```

---

## Week 2: First Agent Activation Prompt

### What Changes

The shadow agent has accumulated 7 days of observation. It has seen:

- 4 leave applications, all approved by boss within 5 minutes
- 3 of 4 were routine (1-2 days, annual leave, balance sufficient)
- Ah Mei checks attendance daily at 10 AM
- Boss checks the dashboard at 8:30 AM

### What the Boss Sees

**Morning briefing (Day 8):**

```
Good morning!

Your week at a glance:
- 4 leave applications processed (all approved)
- 10 employees, 0 on leave today
- CPF filing reminder: March submission due by 14th April

I can help with some of the routine work. Want me to handle
leave approvals for short requests (1-2 days) that are within
policy? I'll notify you each time, and you can override any
decision.

[Yes, handle short leave] [Tell me more] [Not yet]
```

**If the boss taps "Tell me more":**

```
Here's what would change:

BEFORE (current):
  Every leave request waits for you or Ah Mei to approve.

AFTER:
  Leave requests under 2 days, with sufficient balance,
  and no team overlap → approved automatically.
  You get a notification: "Sarah's 1-day leave approved."

  Everything else still comes to you:
  - Leave 3+ days → you approve
  - Notice period leave → you approve
  - Multiple team members same days → you approve

This is reversible anytime from Settings.

[Yes, handle short leave] [Not yet]
```

**If the boss taps "Yes, handle short leave":**

```
Done. Short leave requests (1-2 days, within policy, no overlap)
will now be approved automatically. I'll notify you each time.

You can change this anytime in Settings > Agent Permissions.
```

### What Changes in PACT

- Leave Administrator Agent's envelope widens: `approve_leave` added to `allowed_actions` with gradient constraint `auto_approved_up_to: 2_days`
- EATP Delegation Record created: Boss delegated leave approval authority (<=2 days) to Leave Administrator Agent
- PactAuditEvent logged: suggestion accepted, change applied
- Gradient updated: leave <=2 days moves from "held" to "auto-approved with notification"

### Agent Envelope After Activation

```
Updated envelope (Week 2):
  Can do: Track balances, calculate accruals, approve leave <=2 days (within policy, no overlap)
  Cannot do: Approve leave >2 days, reject leave, encash leave, modify policy
  Gradient: Leave <=2 days = auto-approved + notification
            Leave 3-5 days = flagged (approved by Ah Mei)
            Leave >5 days = held (boss approval)
```

---

## Week 3-4: HR Manager Agent Becomes Useful

### What the Boss Sees

Employees start using self-service. The HR Manager Agent (if Ah Mei doesn't exist) or Ah Mei's shadow agent handles increasing volume:

**Nudge to boss (Day 14):**

```
Your team has been using the leave system well — 8 applications
processed this week, 6 auto-approved, 2 by Ah Mei.

Here are two more things I can handle:
1. Answer employee questions about company policies
   (like "How many sick leave days do I have?")
2. Send attendance reminders to employees who forget to clock in

[Set up both] [Tell me more] [Not now]
```

**First compliance alert (Day 18):**

```
Heads up: John's work pass expires in 45 days (May 5).
You'll need to renew it before then or he can't work legally.

Steps:
1. Apply for renewal on MOM's EP Online
2. Allow 4-6 weeks processing time
3. Start now to avoid risk

[Show me the steps] [Noted]
```

### What the Shadow Agent Learns

By Week 3, the shadow agent has established baselines for every user:

**Boss baseline:**

- Checks dashboard at 8:30 AM
- Approves leave within 3 minutes (fast-approve pattern)
- Reviews payroll-related items more carefully (10+ minutes)
- Never accesses individual salary records (delegates to Ah Mei)

**Ah Mei baseline:**

- Processes leave at 10 AM
- Checks attendance daily
- Accesses 3-5 employee records per day
- Attempts payroll-related tasks but gets "held" (needs boss approval)

**Pattern detected:** Ah Mei tries to view payroll data 3 times per week but her clearance is correct (she can view). She tries to initiate payroll processing but it's held for boss. Boss approves within 5 minutes every time.

---

## Month 1: Payroll Agent Activation

### The Trigger

The boss receives a morning briefing that includes:

```
It's month-end soon. Here's what I can help with for payroll:

Right now: You or Ah Mei calculate payroll manually.
With the Payroll Agent: I calculate payroll automatically using your
employees' salary data, CPF rates, overtime, and leave deductions.

Here's what the agent can and cannot do:

CAN do:
- Calculate gross and net salary for all employees
- Apply CPF contributions (correct 2026 rates, rounded to nearest dollar)
- Deduct for unpaid leave and lateness
- Include approved overtime and claim reimbursements
- Generate payslips in PDF format

CANNOT do:
- Approve the payroll run (you must confirm)
- Submit to CPF Board (you must confirm)
- Change anyone's salary
- Access medical records

Want me to prepare March payroll? You'll review everything before
it's finalized.

[Yes, prepare payroll] [Show me a sample first] [Not yet]
```

**If boss taps "Show me a sample first":**

The Payroll Agent calculates a sample payroll run and presents it:

```
March 2026 Payroll Preview (DRAFT — not finalized):

Total employees: 10
Gross salary total: $38,500.00
Employee CPF total: $7,700.00
Employer CPF total: $6,545.00
SDL total: $96.25
SHG total: varies by employee
Net payout total: $30,800.00

Changes from last month:
- Sarah's OT: 8 hours ($192.00)
- No unpaid leave deductions this month
- 2 new claim reimbursements ($340.00 total)

[Looks right — prepare full run] [Something seems off] [Not now]
```

### What Changes in PACT

When the boss activates the Payroll Agent:

- Payroll Agent envelope activates with all constraints from Section 2.2 of the domain config
- Bridge from Leave-to-Payroll activates (unpaid leave deductions flow automatically)
- Bridge from Attendance-to-Payroll activates (overtime hours flow automatically)
- Bridge from Claims-to-Payroll activates (approved reimbursements flow automatically)
- EATP records created for all bridge activations

### The Monthly Payroll Flow

```
Day 25 of month:
  Payroll Agent: "March payroll is ready for review.
                  Total: $38,500 gross, $30,800 net.
                  3 changes from last month (shown below).
                  [Review & Approve] [See Details]"

Boss taps [Review & Approve]:
  Payroll Agent: "Payroll approved. Generating payslips now.
                  10 payslips will be ready in 2 minutes.

                  CPF e-Submit file is also ready.
                  This needs a separate confirmation to submit.
                  [Submit CPF now] [I'll submit later]"

Boss taps [Submit CPF now]:
  System: "Confirm CPF submission for March 2026?
           Total employee CPF: $7,700.00
           Total employer CPF: $6,545.00
           This will be submitted to CPF Board.
           [Confirm submission] [Cancel]"

Boss taps [Confirm submission]:
  Agent: "CPF submission confirmed. File generated for upload.
          Reminder: Upload to CPF e-Submit portal by 14th April."
```

### Agent Envelope at Month 1

```
Active agents:
  Advisory Agent          — active since Day 1
  Shadow Agent            — active since Day 1
  Leave Administrator     — tracking + auto-approve <=2 days since Week 2
  HR Manager Agent        — answering policy questions since Week 3
  Attendance Agent        — tracking clock-in/out since Week 3
  Payroll Agent           — calculating payroll since Month 1
  Document Agent          — generating payslips since Month 1

Still dormant:
  Claims Agent            — activates Month 1 (next suggestion)
  Compliance Agent        — activates Month 2
  Recruitment Agent       — activates Month 3
  Onboarding Agent        — activates Month 2
  Reports Agent           — activates Month 2
```

---

## Month 2: Compliance and Onboarding Agents

### What the Boss Sees

**Morning briefing (Day 30):**

```
Good morning!

Monthly summary:
- 12 leave applications (10 auto-approved, 2 you reviewed)
- March payroll processed ($38,500 gross)
- CPF submitted on time
- 0 compliance issues

New capabilities available:

1. COMPLIANCE MONITORING
   I can track filing deadlines, CPF rate changes, work pass
   expiries, and employment law updates — and alert you before
   anything is due.

2. EMPLOYEE ONBOARDING
   When you hire someone new, I can collect their documents,
   set up their system access, create their leave balances,
   and walk them through orientation.

[Activate both] [Just compliance] [Just onboarding] [Not now]
```

### Compliance Agent in Action

Once activated, the Compliance Agent begins continuous monitoring:

**Week 5 alert:**

```
Filing reminder: IR8A preparation should start in October.
You have 10 employees — all need IR8A forms for YA2027.
I'll start preparing the data in September.
[Noted]
```

**Week 6 alert:**

```
Regulatory update: MOM has updated the Fair Consideration
Framework guidelines for EP applications. Key change:
job ads on MyCareersFuture must now run for 28 days
(was 14 days) before EP applications.

This affects your company if you hire foreign workers on EP.
[Show me the details] [Noted]
```

**Week 7 alert:**

```
Work pass expiry: John's S-Pass expires in 30 days (May 5).
Status: NOT YET RENEWED

You need to:
1. Apply on MOM EP Online (allow 4-6 weeks)
2. URGENT: Start today to avoid expired pass

[Show renewal steps] [I've already started] [Remind me in 3 days]
```

### Onboarding Agent in Action

The boss hires a new employee:

```
Boss: "I want to add a new employee — Mary, starting April 1"

Onboarding Agent: "I'll set up Mary's onboarding. Here's what I need:

Personal details:
- Full name: Mary [need surname]
- NRIC/FIN: [will collect from Mary directly]
- Date of birth: [will collect from Mary directly]

Employment details:
- Department: [which department?]
- Designation: [what's her job title?]
- Salary: [needs your input — I cannot set this]
- Employment type: Full-time / Part-time / Contract?

[Fill in now] [Send Mary an onboarding form]"
```

If boss taps "Send Mary an onboarding form":

```
Onboarding Agent: "I'll email Mary an onboarding form to collect her:
- Personal details (NRIC, DOB, address, bank details)
- Emergency contact
- Tax reference number

Her data will be encrypted and only accessible to you and Ah Mei.
She'll also get a welcome guide explaining company policies.

[Send the form] [Let me review it first]"
```

---

## Month 3: Claims and Recruitment

### Claims Agent Activation

```
Morning briefing insight:
"Your team submitted 15 expense claims this month. All were under
$100 and all were approved. Want me to auto-approve small claims
(under $50) so your team doesn't have to wait?

Claims $50-$200: I'll approve and notify you
Claims over $200: Still needs your approval

[Set up auto-claims] [Tell me more] [Not now]"
```

### Recruitment Agent Activation

```
"I noticed you've been growing — 2 new hires in the last 2 months.
If you're looking to hire more, I can help with:

- Draft job listings (you review before publishing)
- Track applicants in a pipeline
- Schedule interviews
- Generate offer letters (you approve before sending)

Want to try it for your next hire?

[Yes, let's set it up] [Not yet]"
```

---

## Month 4-5: Envelope Refinement Through Observation

### What the Shadow Agent Has Learned

After 4 months of observation, the shadow agent has high-confidence patterns:

**Pattern: Ah Mei should have payroll approval authority**

```
Evidence: Ah Mei has initiated payroll runs 4 months in a row.
Boss approved every time within 3 minutes.
Confidence: 0.95

Suggestion (Month 4 briefing):
"Ah Mei has processed payroll for 4 months straight, and you've
approved every run within minutes. Want to give her direct payroll
approval authority?

She still cannot:
- Submit CPF (only you can do that)
- Modify salary rates
- Access tax filing data

[Give Ah Mei payroll approval] [No, I want to keep reviewing] [Not now]"
```

**Pattern: Auto-approve leave up to 5 days**

```
Evidence: All leave requests 3-5 days have been approved.
No rejections in 4 months.
Confidence: 0.90

Suggestion (Month 4 briefing):
"Every leave request up to 5 days has been approved this year.
Want to extend auto-approval from 2 days to 5 days?

You'll still review:
- Leave during notice period
- Leave when >50% of team is already off
- Leave for more than 5 days

[Extend to 5 days] [Keep at 2 days] [Not now]"
```

**Pattern: Operations team needs formal structure**

```
Evidence: Company now has 12 employees (2 new hires).
Operations has 8 people, no formal sub-teams.
Confidence: 0.85

Suggestion (Month 5 briefing):
"Your Operations team has grown to 8 people. John is supervising
everyone directly. Want me to suggest a team structure?

Proposed:
- Team A (Installation): John supervises 3 technicians
- Team B (Maintenance): New Supervisor supervises 4 workers

This means:
- John approves Team A's leave and attendance
- New Supervisor approves Team B's leave and attendance
- You only see escalations

[Set up teams] [Show me the details] [Not now]"
```

---

## Month 6: Full AI HR Department

### Current State

By month 6, with consistent boss engagement, the following agents are active:

| Agent               | Active Since                                  | Current Envelope                                            |
| ------------------- | --------------------------------------------- | ----------------------------------------------------------- |
| Advisory Agent      | Day 1                                         | Full employment law Q&A                                     |
| Shadow Agent        | Day 1                                         | Observing all, suggesting governance changes                |
| Leave Administrator | Week 1 (tracking), Week 2 (approval <=5 days) | Auto-approve routine leave, flag unusual patterns           |
| HR Manager Agent    | Week 3                                        | Policy Q&A, attendance tracking, onboarding support         |
| Attendance Agent    | Week 3                                        | Clock-in tracking, overtime calculation, lateness detection |
| Payroll Agent       | Month 1                                       | Full payroll calculation, payslip generation, CPF prep      |
| Document Agent      | Month 1                                       | Payslips, contracts, letters                                |
| Claims Agent        | Month 3                                       | Auto-approve <$50, route larger claims                      |
| Compliance Agent    | Month 2                                       | Deadline tracking, regulatory monitoring, work pass alerts  |
| Recruitment Agent   | Month 3                                       | Job listings, candidate tracking, offer drafts              |
| Onboarding Agent    | Month 2                                       | Document collection, system setup, welcome sequence         |
| Reports Agent       | Month 2                                       | Headcount, turnover, cost analysis                          |

### What the Boss's Day Looks Like

**8:30 AM — Morning briefing (2 minutes):**

```
Good morning!

Today:
- 2 employees on leave (Sarah, Tom)
- 1 leave request awaiting your review (6-day annual leave — John)
- Compliance: All clear, next CPF deadline April 14
- Payroll: March payslips distributed yesterday, 0 queries

This week:
- 1 new starter (Mary) — onboarding 80% complete, awaiting bank details
- 1 interview scheduled (Thursday, 2 PM — Warehouse Assistant role)

Action needed:
- Review John's 6-day leave request [Review]
- Mary hasn't submitted bank details — reminder sent [Noted]
```

**Boss reviews John's leave (30 seconds):**

```
John requested 6 days annual leave (April 14-21).
Balance: 8 days remaining
Team coverage: Team A has 2/3 staff available
No overlap with other leave

Recommendation: Approve
[Approve] [Decline] [Ask John for details]
```

**Boss taps Approve. Done for the day.**

**Total boss time on HR this week: approximately 15 minutes.**

Compare to Month 0: 5-10 hours per week on leave approvals, payroll, compliance checking, and employee queries.

### PACT Governance State

```
Active PACT structure:
  12 roles in D/T/R tree
  6 agent-filled roles
  4 human roles (Boss, Ah Mei, John, new Supervisor)
  2 shadow-augmented humans (Ah Mei, John)

  7 bridges active (Leave→Payroll, Attendance→Payroll, Claims→Payroll,
                     Recruitment→Onboarding, Onboarding→Payroll,
                     Compliance→All, Shadow→All)

  23 EATP Delegation Records (envelope changes + bridge activations)
  ~15,000 PACT audit events (action logging over 6 months)

  5 envelope widenings accepted by boss
  2 structural changes accepted
  1 suggestion dismissed (boss prefers to review all overtime)
```

---

## The "Boss Never Engages" Scenario

### What Happens If the Boss Ignores Everything

Boss registers, adds employees, never reads briefings, dismisses all suggestions.

**Month 6 state without engagement:**

| Feature        | Without Boss Engagement                    | With Boss Engagement                                |
| -------------- | ------------------------------------------ | --------------------------------------------------- |
| D/T/R tree     | Auto-generated, functional                 | Confirmed and refined                               |
| Leave tracking | Active, balances accurate                  | Active + auto-approval for routine                  |
| Leave approval | All go to boss/Ah Mei (manual)             | Routine auto-approved, boss reviews edge cases only |
| Payroll        | Boss must calculate manually               | Agent calculates, boss confirms                     |
| CPF filing     | Boss must do everything                    | Agent prepares, boss confirms                       |
| Compliance     | Alerts in unread briefings                 | Proactive alerts, tracked deadlines                 |
| Onboarding     | Manual process                             | Guided checklist, automated document collection     |
| Governance     | Template defaults (safe but not optimized) | Refined by observation (efficient and tailored)     |

**Key point**: The system is functional but not efficient. The boss still does all approvals manually. The agents are dormant except for tracking and advisory. Governance is present (template envelopes, clearance enforcement) but not optimized.

**When the boss finally engages:**

```
"Welcome back! I've been tracking your company for 6 months.
Here are 5 things that can save you 4+ hours per week:

1. Auto-approve routine leave (you've approved 48 out of 48)
2. Let me calculate payroll (you've been doing it in Excel)
3. Auto-approve small claims (you've approved all 30 under $100)
4. Set up compliance alerts (2 deadlines were almost missed)
5. Give Ah Mei payroll access (she asks you every month)

[Set up all 5] [Review one at a time] [Not now]"
```

The "Set up all 5" button applies the top suggestions in one batch, with a confirmation screen showing exactly what changes. Six months of accumulated observation makes the suggestions highly confident and immediately valuable.

---

## Progressive Trust Ladder Summary

| Stage            | Time      | Trust Level       | Agent Capability                    | Boss Effort         |
| ---------------- | --------- | ----------------- | ----------------------------------- | ------------------- |
| Registration     | Day 1     | Zero trust        | Record-keeping only                 | 15 min setup        |
| Observation      | Week 1    | Transparency      | Advisory Q&A, leave tracking        | Normal work         |
| First delegation | Week 2    | Low-stakes trust  | Auto-approve 1-2 day leave          | 1 min confirmation  |
| Operational      | Month 1   | Growing trust     | Payroll calculation, attendance     | Review + confirm    |
| Expanded         | Month 2-3 | Established trust | Compliance, onboarding, claims      | Review edge cases   |
| Refined          | Month 4-5 | Earned trust      | Wider envelopes, structural changes | Approve suggestions |
| Full             | Month 6   | Verified trust    | Full AI HR department               | 15 min/week         |

At every stage, the boss can:

- **Reverse** any delegation (revoke agent authority)
- **Tighten** any envelope (restrict what agents can do)
- **Review** any action (full audit trail available)
- **Override** any decision (human always has final say)

PACT governance ensures that agent authority only expands when the boss explicitly confirms it, and every expansion is recorded in a tamper-evident audit trail.
