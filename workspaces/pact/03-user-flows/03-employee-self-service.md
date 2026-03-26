# User Flow 03: Employee Self-Service

## Sarah Uses Arbor as an Employee

**Persona**: Sarah Lim, 32, warehouse supervisor at Ahmad Logistics. Manages a delivery team (Priya, Wei Ming, Kumar S). Has been at the company 4 years. Not tech-savvy but uses WhatsApp and Grab daily. Got the Arbor invite link in the company WhatsApp group.

**PACT context**: Sarah's position is `D1-R1-D2-R2` (Operations, Warehouse Supervisor). Template: `tmpl_supervisor`. Clearance: RESTRICTED (C1). Her envelope allows: view own records, apply leave, clock in/out, submit claims, view team attendance, approve team leave (as supervisor).

---

## Step 1: First Login

Sarah taps the invite link from WhatsApp. It opens in her phone browser.

**What Sarah sees:**

```
+----------------------------------------------------------+
|  Welcome to Arbor                                         |
|                                                           |
|  Ahmad Logistics Pte Ltd invited you.                     |
|                                                           |
|  Name:      Sarah Lim                                     |
|  Email:     sarah@ahmadlogistics.sg                       |
|  Role:      Warehouse Supervisor — Operations             |
|                                                           |
|  Set your password:                                       |
|  [*************                         ]                 |
|  Confirm:                                                 |
|  [*************                         ]                 |
|                                                           |
|       [Create My Account]                                 |
+----------------------------------------------------------+
```

**What Sarah thinks:** "OK, company thing. Set a password, done."

**What Sarah does:** Sets password, taps "Create My Account."

**What happens behind the scenes:**

- Invitation token consumed (single-use)
- User record activated (role: `employee`)
- Sarah's PactNode confirmed (was created during Ahmad's CSV import)
- Shadow agent begins observation for Sarah's user

---

## Step 2: Employee Dashboard

**What Sarah sees:**

```
+----------------------------------------------------------+
|  Hi Sarah                                 [bell] [menu]   |
|                                                           |
|  YOUR DASHBOARD                                           |
|                                                           |
|  +------------------+  +------------------+               |
|  | Leave Balance    |  | Next Shift       |               |
|  | Annual: 11 days  |  | Tomorrow 8am     |               |
|  | Sick: 14 days    |  | Warehouse B      |               |
|  | [Apply Leave]    |  | [View Schedule]  |               |
|  +------------------+  +------------------+               |
|                                                           |
|  +------------------+  +------------------+               |
|  | Latest Payslip   |  | My Claims        |               |
|  | March 2026       |  | 0 pending        |               |
|  | Net: $3,258      |  | [Submit Claim]   |               |
|  | [View Payslip]   |  |                  |               |
|  +------------------+  +------------------+               |
|                                                           |
|  MY TEAM (3 people)                                       |
|  Priya Devi — Delivery, on duty today                     |
|  Wei Ming — Delivery, on duty today                       |
|  Kumar S — Delivery, on leave (annual)                    |
|                                                           |
|  [Team Attendance]    [Team Schedule]                     |
+----------------------------------------------------------+
```

**What Sarah thinks:** "Ah, I can see my leave and payslip. And my team's status. Useful."

**What Sarah does:** Taps "View Payslip" to check her March pay.

**PACT evaluation (invisible):**

- Sarah views her own payslip: clearance check passes (own_record exception, CONFIDENTIAL data accessible for own records)
- PDPA access logged: Sarah accessed own payslip data
- Gradient zone: AUTO-APPROVED (view own records)
- No notification to anyone

---

## Step 3: Apply for Leave (Auto-Approved)

Sarah wants to take 2 days off next month for a family event.

**What Sarah sees after tapping "Apply Leave":**

```
+----------------------------------------------------------+
|  Apply for Leave                                          |
|                                                           |
|  Leave type:  [Annual Leave          v]                   |
|  From:        [Mon 14 Apr 2026       ]                    |
|  To:          [Tue 15 Apr 2026       ]                    |
|  Duration:    2 days                                      |
|  Reason:      [Family event                     ]         |
|                                                           |
|  Your balance after: 9 days remaining                     |
|                                                           |
|  Team coverage on these dates:                            |
|  Priya — available                                        |
|  Wei Ming — available                                     |
|  Kumar S — available                                      |
|  All 3 team members available. Good coverage.             |
|                                                           |
|       [Submit]     [Cancel]                               |
+----------------------------------------------------------+
```

**What Sarah does:** Taps "Submit."

**PACT evaluation (invisible):**

- Leave request: 2 days annual, within balance, within policy
- Team coverage: all 3 reports available on those dates
- Not during notice period, not during company blackout
- Gradient zone: AUTO-APPROVED (routine, within envelope)
- HR Agent processes immediately

**What Sarah sees:**

```
+----------------------------------------------------------+
|  [checkmark] Leave approved                               |
|                                                           |
|  Annual Leave: Mon 14 Apr — Tue 15 Apr (2 days)          |
|  Remaining balance: 9 days                                |
|                                                           |
|  Ahmad has been notified.                                 |
|                                                           |
|       [Back to Dashboard]                                 |
+----------------------------------------------------------+
```

**What Sarah thinks:** "That was instant. No waiting for Boss to check his phone."

**What Ahmad sees (as a flagged notification, not blocking):**

```
Arbor: Sarah took 2 days leave (14-15 Apr). Full team coverage. Auto-approved.
```

Ahmad glances at it, notes it, moves on. This is the FLAGGED zone — action completed, supervisor notified.

---

## Step 4: Apply for Leave (Escalated to Boss)

Two weeks later. Sarah wants to take 3 days off, but she has submitted her resignation last week. She is in her notice period.

**What Sarah sees after tapping "Apply Leave":**

```
+----------------------------------------------------------+
|  Apply for Leave                                          |
|                                                           |
|  Leave type:  [Annual Leave          v]                   |
|  From:        [Wed 7 May 2026        ]                    |
|  To:          [Fri 9 May 2026        ]                    |
|  Duration:    3 days                                      |
|  Reason:      [Personal matters                 ]         |
|                                                           |
|  Your balance after: 6 days remaining                     |
|                                                           |
|  [!] Note: You are currently in your notice period.       |
|  Leave during notice period needs Ahmad's approval        |
|  and may affect your last working day.                    |
|                                                           |
|       [Submit for Approval]     [Cancel]                  |
+----------------------------------------------------------+
```

**What Sarah thinks:** "Right, I'm serving notice. Makes sense that Boss needs to approve."

**What Sarah does:** Taps "Submit for Approval."

**PACT evaluation (invisible):**

- Leave request: 3 days annual, within balance
- BUT: employee status is "notice_period" (resignation submitted)
- Gradient zone: HELD (notice period leave requires supervisor approval per Employment Act)
- Leave status set to "pending"

**What Sarah sees:**

```
+----------------------------------------------------------+
|  [clock] Leave submitted — waiting for Ahmad's approval   |
|                                                           |
|  Annual Leave: Wed 7 May — Fri 9 May (3 days)            |
|  Status: Pending approval                                 |
|                                                           |
|  Since you're in your notice period, Ahmad needs to       |
|  confirm this leave. You'll be notified once he decides.  |
+----------------------------------------------------------+
```

**What Ahmad sees (HELD action, blocking notification):**

```
+----------------------------------------------------------+
|  Leave Request — Needs Your Approval                      |
|                                                           |
|  Sarah Lim (Warehouse Supervisor)                         |
|  3 days annual leave: Wed 7 May — Fri 9 May              |
|                                                           |
|  [!] Sarah is in her notice period (last day: 20 May)     |
|  Approving this leave will extend her last day to 23 May  |
|  (leave during notice does not count as notice unless      |
|  you agree to waive it).                                  |
|                                                           |
|  [Approve]    [Approve & Waive Notice]    [Decline]       |
+----------------------------------------------------------+
```

The agent is not just routing the leave request — it is providing the Employment Act context that Ahmad needs to make an informed decision.

---

## Step 5: View Payslip (Own Data — RESTRICTED Access)

Sarah taps "Latest Payslip" on her dashboard.

**PACT evaluation (invisible):**

- Target: Payslip model (CONFIDENTIAL clearance required)
- Sarah's clearance: RESTRICTED (C1)
- But: `target_employee_id == requesting_user's employee_id` — own record exception
- Access: ALLOWED (own_record)
- PDPA access logged: Sarah viewed own payslip

**What Sarah sees:**

```
+----------------------------------------------------------+
|  March 2026 Payslip                                       |
|                                                           |
|  EARNINGS                                                 |
|  Basic Salary                          $3,600.00          |
|  Transport Allowance                     $200.00          |
|                                          --------          |
|  Total Gross                           $3,800.00          |
|                                                           |
|  DEDUCTIONS                                               |
|  CPF — Employee (12%)                    $456.00          |
|  SDL (0.25%)                               $9.50          |
|  CDAC                                      $2.00          |
|                                          --------          |
|  Total Deductions                        $467.50          |
|                                                           |
|  NET PAY                               $3,332.50          |
|                                                           |
|  EMPLOYER CONTRIBUTIONS                                   |
|  CPF — Employer (17%)                    $646.00          |
|                                                           |
|  [Download PDF]     [View Previous Months]                |
+----------------------------------------------------------+
```

Sarah views her payslip. No friction. No approval needed. The PACT infrastructure is invisible — clearance was checked, PDPA access was logged, and Sarah experienced it as a simple page load.

---

## Step 6: Attempt to View Another Employee's Salary (BLOCKED)

Sarah is curious about her colleague John's pay. She tries to navigate to his profile. On the employee directory page, she taps John Tan's name.

**What Sarah sees (John's public profile):**

```
+----------------------------------------------------------+
|  John Tan                                                 |
|  Warehouse Supervisor — Operations                        |
|  Reports to: Ahmad                                        |
|  Started: 1 Jun 2021                                      |
|  Email: john@ahmadlogistics.sg                            |
|                                                           |
|  [View Attendance]    [View Schedule]                     |
+----------------------------------------------------------+
```

Sarah can see John's public information (PUBLIC clearance data: name, department, designation, start date). She taps around looking for salary information. There is no salary field visible. She tries typing in the URL bar: `.../employees/john-tan/payslip`.

**PACT evaluation:**

- Target: John Tan's Payslip data (CONFIDENTIAL)
- Sarah's clearance: RESTRICTED (C1)
- Own record? No (John's employee_id != Sarah's employee_id)
- Bridge or KSP? No (Sarah has no cross-department bridge to Finance data)
- Result: BLOCKED

**What Sarah sees:**

```
+----------------------------------------------------------+
|  You don't have access to this page                       |
|                                                           |
|  Salary information is private and can only be viewed     |
|  by the employee themselves or by HR/management.          |
|                                                           |
|  If you need this information for your work, you can      |
|  ask Ahmad to update your access.                         |
|                                                           |
|       [Back to Directory]                                 |
+----------------------------------------------------------+
```

**What Sarah thinks:** "OK, fair enough. That's private."

**What happens behind the scenes:**

- BLOCKED access attempt recorded in PactAuditEvent
- BLOCKED access recorded in ObservationStore (pact_address: D1-R1-D2-R2, target: John Tan payslip, result: blocked)
- PDPA access log: attempted access to CONFIDENTIAL data, DENIED
- No notification to Ahmad (single blocked access is not an anomaly)
- Pattern detector notes this as a data point. If Sarah attempts this 2+ times, it becomes a `blocked_needs_clearance` pattern, and the system will ask Ahmad if Sarah needs access.

**Key design point:** The blocked message is not accusatory. It does not say "ACCESS DENIED" in red. It does not imply Sarah did something wrong. It explains what happened and offers a path forward. This is the UX treatment from PACT-lite section 5.2.

---

## Step 7: Shadow Agent Suggestion (Medical Leave)

Sarah is on her dashboard. The shadow agent nudge service detects that her medical leave balance is low.

**What Sarah sees (nudge at bottom of dashboard):**

```
+----------------------------------------------------------+
|                                                           |
|  [lightbulb] Your medical leave is nearly used up.        |
|  You have 2 days remaining out of 14. Here are your      |
|  options:                                                 |
|                                                           |
|  - If you need medical leave, your sick days are still    |
|    available (separate from outpatient medical leave)     |
|  - After medical leave is exhausted, you can use annual   |
|    leave for medical appointments                         |
|  - Hospitalization leave (60 days) is a separate          |
|    entitlement — it's not affected                        |
|                                                           |
|  [Show me my full leave breakdown]    [Dismiss]           |
+----------------------------------------------------------+
```

**PACT evaluation (invisible):**

- Nudge service accessed Sarah's leave balance: RESTRICTED data, own record exception applies
- Shadow agent generated the nudge based on balance threshold (< 3 days remaining)
- This is an employee-facing nudge — it does not suggest governance changes (those go to owner/hr_manager only)

**What Sarah thinks:** "Oh, I didn't realize I only have 2 days left. Good to know about hospitalization leave being separate."

---

## Step 8: Supervisor View — Team Leave

Sarah is also a supervisor. Her envelope (`tmpl_supervisor`) allows her to view her team's leave balances and attendance, and to approve leave for her direct reports.

**What Sarah sees when she taps "Team Attendance":**

```
+----------------------------------------------------------+
|  My Team — This Week                                      |
|                                                           |
|  +------------------+--+--+--+--+--+                      |
|  |                  |Mo|Tu|We|Th|Fr|                      |
|  +------------------+--+--+--+--+--+                      |
|  | Priya Devi       |OK|OK|OK|OK|OK|                      |
|  | Wei Ming         |OK|OK|MC|OK|OK|                      |
|  | Kumar S          |OK|OK|OK|AL|AL|                      |
|  +------------------+--+--+--+--+--+                      |
|                                                           |
|  AL = Annual Leave, MC = Medical Leave, OK = Present      |
|                                                           |
|  Wei Ming submitted a medical certificate (1 day)         |
|  Kumar S is on approved annual leave (Thu-Fri)            |
|                                                           |
|  [View Full Month]    [Export Attendance]                  |
+----------------------------------------------------------+
```

**PACT evaluation (invisible):**

- Sarah views team attendance: RESTRICTED data for team members
- Sarah's scope: D1-R1-D2-R2 and all children (Priya, Wei Ming, Kumar S)
- Containment check: all three employees are under Sarah in the PACT tree
- Access: ALLOWED (supervisor viewing team data within scope)
- Sarah cannot see John Tan's team attendance — John is a sibling node (D1-R1-D2-R1), not under Sarah

**What Sarah cannot see on this page:**

- Any employee outside her team (Raju, Ali, Faizal, David — they report to John)
- Salary data for her team members
- Medical certificate details (only that a MC was submitted)
- HR notes or disciplinary records for her team

The PACT clearance system ensures Sarah sees exactly what a supervisor needs — team schedule and attendance status — without accidentally exposing data she should not have.

---

## Step 9: Supervisor Leave Approval

Priya applies for leave. Since Priya reports to Sarah, the leave request routes to Sarah first.

**What Sarah sees (push notification):**

```
Arbor: Priya Devi requested 1 day leave (Mon 28 Apr). Needs your OK.
```

Sarah taps the notification.

```
+----------------------------------------------------------+
|  Leave Request                                            |
|                                                           |
|  Priya Devi (Delivery Driver)                             |
|  1 day annual leave: Mon 28 Apr                           |
|                                                           |
|  Her balance: 8 days remaining                            |
|  Team coverage: Wei Ming and Kumar S available            |
|                                                           |
|  [Approve]    [Decline]    [Ask Ahmad]                    |
+----------------------------------------------------------+
```

**PACT evaluation:**

- Sarah's envelope (`tmpl_supervisor`) allows: approve team leave
- Priya reports to Sarah (within scope)
- 1 day, within policy, good coverage
- Gradient zone: AUTO-APPROVED at Sarah's level (she can approve directly)

**What Sarah does:** Taps "Approve."

**What happens behind the scenes:**

- Leave approved by Sarah (supervisor approval)
- Ahmad gets FLAGGED notification: "Priya's 1-day leave approved by Sarah"
- PACE session not required (supervisor has autonomous authority for routine team leave)
- PactAuditEvent: leave approved by D1-R1-D2-R2 (Sarah) for D1-R1-D2-R2-R2 (Priya)

**The "Ask Ahmad" option:** If Sarah is unsure (unusual request, team coverage concern), she can escalate to Ahmad. This is voluntary escalation — the system does not force it, but offers it. This is the human equivalent of a HELD action: Sarah choosing to hold her own decision for her boss.

---

## Step 10: What Sarah Never Sees

The PACT infrastructure is entirely invisible to Sarah. Here is what is running behind every interaction she has:

| Sarah's Action       | PACT Check                                    | Result  | Sarah Experiences              |
| -------------------- | --------------------------------------------- | ------- | ------------------------------ |
| View own dashboard   | Clearance: RESTRICTED, own data               | ALLOWED | Dashboard loads normally       |
| View own payslip     | Clearance: CONFIDENTIAL, own record exception | ALLOWED | Payslip loads normally         |
| View team attendance | Scope: children of D1-R1-D2-R2                | ALLOWED | Team view loads normally       |
| Approve team leave   | Envelope: tmpl_supervisor allows              | ALLOWED | Approve button works           |
| View John's payslip  | Clearance: CONFIDENTIAL, not own, no bridge   | BLOCKED | "You don't have access"        |
| View company payroll | Scope: company-wide, Sarah is team-level      | BLOCKED | Not even visible in navigation |
| Change own salary    | Envelope: tmpl_supervisor, blocked action     | BLOCKED | Not available as an option     |
| Submit CPF           | Envelope: tmpl_supervisor, blocked action     | BLOCKED | Not available as an option     |

Sarah never sees the word "clearance," "envelope," "gradient," or "PACT." She experiences Arbor as a system where she can do her job, see her data, manage her team, and not access things that are not hers. The governance is real but invisible.

---

## Complete Access Matrix for Sarah

| Data Type               | Own       | Team (Priya, Wei Ming, Kumar S) | Other Teams (John's team) | Company-Wide    |
| ----------------------- | --------- | ------------------------------- | ------------------------- | --------------- |
| Name, department, title | Yes       | Yes                             | Yes (directory)           | Yes (directory) |
| Leave balance           | Yes       | Yes                             | No                        | No              |
| Attendance records      | Yes       | Yes                             | No                        | No              |
| Shift schedule          | Yes       | Yes                             | No                        | No              |
| Payslip                 | Yes       | No                              | No                        | No              |
| Salary                  | Yes       | No                              | No                        | No              |
| NRIC/bank details       | Yes (own) | No                              | No                        | No              |
| Performance review      | Yes       | No                              | No                        | No              |
| Medical records         | Yes       | No                              | No                        | No              |
| Claims                  | Yes       | No                              | No                        | No              |
| Company policies        | Yes       | Yes                             | Yes                       | Yes             |
| Public holidays         | Yes       | Yes                             | Yes                       | Yes             |

---

## Failure Points and Mitigations

| Failure                                                   | Likelihood | Impact | Mitigation                                                                                                                                                                |
| --------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sarah forgets password                                    | High       | Low    | Standard password reset flow via email                                                                                                                                    |
| Sarah does not understand why access is blocked           | Medium     | Medium | Block message explains the reason in plain language and suggests next steps                                                                                               |
| Sarah's supervisor leave approval conflicts with HR Agent | Low        | Medium | If HR Agent has already auto-approved at company level, Sarah's approval is redundant (auto-merged). If HR Agent holds, Sarah's approval is necessary-but-not-sufficient. |
| Priya applies for leave when Sarah is on leave herself    | Medium     | Low    | Leave request auto-escalates to Ahmad (next supervisor in PACT tree) if Sarah does not respond within 24 hours                                                            |
| Sarah attempts bulk data download (all team records)      | Low        | Medium | Rate limiting on data access; if >20 records in one session, observation flags it as unusual volume                                                                       |
| Sarah is promoted to manager (role change)                | Medium     | None   | PACT tree recomputed; template envelope upgraded from tmpl_supervisor to tmpl_ops_manager; clearance potentially upgraded by Ahmad's confirmation                         |
