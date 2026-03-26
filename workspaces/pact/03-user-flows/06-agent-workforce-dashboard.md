# User Flow 06: Agent Workforce Dashboard

## Boss Views and Manages the Agent Workforce

**Persona**: Ahmad, same logistics boss. Month 6. Arbor has been running for half a year. He has 3 agents active: HR Agent (under Ah Mei), Payroll Agent (under Ahmad directly), and the Compliance Agent (monitoring work permits and regulatory deadlines). Ahmad checks Arbor once a day, usually in the morning while drinking kopi at the kopitiam before heading to the warehouse.

**PACT context**: Ahmad is `D1-R1` (Director). He has visibility into the entire PACT tree. His clearance is CONFIDENTIAL (C2). He can view all agent envelopes, all held actions, all audit events. He is the root authority.

---

## Step 1: Opening the Dashboard

Ahmad opens Arbor on his phone. He is on the main screen.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Good morning, Ahmad                     Sat 20 Sep 2026  |
|                                                           |
|  YOUR COMPANY                                             |
|                                                           |
|  12 employees    3 agents    0 issues                     |
|                                                           |
|  TODAY'S HIGHLIGHTS                                       |
|  - 2 employees on leave (Priya — annual, Siti — MC)      |
|  - 1 action needs your approval (payroll, see below)     |
|  - September payroll ready for review ($39,800)           |
|                                                           |
|  [Review Payroll]                                         |
|                                                           |
|  ──────────────────────────────────────────                |
|                                                           |
|  AGENT PERFORMANCE THIS MONTH                             |
|                                                           |
|  [shield] HR Agent         87 actions   0 errors          |
|  [calc]   Payroll Agent     1 run       0 errors          |
|  [doc]    Compliance Agent  4 alerts    0 missed          |
|                                                           |
|  [View My Team]                                           |
+----------------------------------------------------------+
```

**What Ahmad does:** Taps "View My Team."

---

## Step 2: The Team View — Humans and Agents Together

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  My Team                                [list] [chart]    |
|                                                           |
|  ┌──────────────────────────────────────────────┐         |
|  │                 [Ahmad]                       │         |
|  │                Director                       │         |
|  │                                               │         |
|  │        ┌──────────┼──────────┐               │         |
|  │        v          v          v               │         |
|  │    [Admin]    [Operations]  [Finance]        │         |
|  │                                               │         |
|  │  [Ah Mei]     [John]  [Sarah]  [Payroll     │         |
|  │  Admin Mgr   Supv     Supv     Agent]       │         |
|  │     |         |   |    |  |   |  [robot]    │         |
|  │  [Siti]  [HR  |   |    |  |   |             │         |
|  │  [robot] Agent]   |    |  |   |             │         |
|  │          [robot]  |    |  |   |             │         |
|  │                   |    |  |   |             │         |
|  │         Raju Ali  | Priya |   |             │         |
|  │         Faizal    | Wei   |   |             │         |
|  │         David     | Kumar |   |             │         |
|  └──────────────────────────────────────────────┘         |
|                                                           |
|  Legend:                                                   |
|  [person icon] = Human     [robot icon] = Agent           |
|  [green dot] = Active      [yellow dot] = Needs attention |
|  [grey dot] = Off/inactive                                |
|                                                           |
|  12 humans   3 agents   0 vacant roles                    |
+----------------------------------------------------------+
```

The org chart uses simple visual indicators. Human nodes are standard person icons. Agent nodes have a distinct robot/gear icon. Color dots show status at a glance.

**What Ahmad thinks:** "There's my team. Three agents — one under Ah Mei, one under Finance, one... where's the Compliance Agent?"

The Compliance Agent does not appear as a separate node because it is a capability of the HR Agent (compliance monitoring is part of the HR Agent's envelope). The dashboard shows it as a separate line item in performance metrics because it is a distinct function, but in the PACT tree it shares the HR Agent's position.

**What Ahmad does:** Taps on the HR Agent node.

---

## Step 3: Agent Detail View — HR Agent

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  HR Agent                              [green: Active]    |
|  Reports to: Ah Mei (Admin Manager)                       |
|  Active since: 22 March 2026 (6 months)                   |
|                                                           |
|  ── TODAY ────────────────────────────────────────         |
|                                                           |
|  Actions today: 5                                         |
|  [check] Auto-approved Sarah's 1-day leave (8:15 AM)     |
|  [check] Auto-approved Raju's MC (8:30 AM)               |
|  [check] Answered Wei Ming's question about OT rate       |
|  [check] Flagged Kumar S absence (no MC, no leave)        |
|  [clock] Pending: Ahmad's payroll approval                |
|                                                           |
|  ── THIS MONTH ───────────────────────────────────         |
|                                                           |
|  Leave approvals:        18 auto-approved                 |
|                           3 flagged (you were notified)   |
|                           1 held (you approved)           |
|                           0 errors                        |
|                                                           |
|  Claims processed:       7 auto-approved (<$200)          |
|                           2 held (>$200, you approved)    |
|                           0 errors                        |
|                                                           |
|  Attendance:             22 daily checks completed        |
|                           3 absences flagged              |
|                           0 missed checks                 |
|                                                           |
|  HR questions answered:  6                                |
|  Compliance alerts:      1 (Ali's WP renewal, 45 days)   |
|                                                           |
|  ── HELD ACTIONS (1) ─────────────────────────────         |
|                                                           |
|  [yellow] September payroll ready for your review         |
|           Total: $39,800. No anomalies detected.          |
|           [Review & Approve]                              |
|                                                           |
|  ── WHAT THIS AGENT CAN DO ───────────────────────         |
|                                                           |
|  [check] Approve routine leave (within policy)            |
|  [check] Approve small claims (under $200)                |
|  [check] Monitor daily attendance                         |
|  [check] Answer HR policy questions                       |
|  [check] Track work permit expiry dates                   |
|  [check] Send internal notifications                      |
|                                                           |
|  [lock] Cannot approve payroll (you review)               |
|  [lock] Cannot submit to CPF/MOM/IRAS (you submit)       |
|  [lock] Cannot terminate employees                        |
|  [lock] Cannot change salaries                            |
|  [lock] Cannot access medical records                     |
|                                                           |
|  ── RELIABILITY ──────────────────────────────────         |
|                                                           |
|  6 months active                                          |
|  437 total actions                                        |
|  0 errors                                                 |
|  2 overrides by Ah Mei (both were correct — edge cases    |
|    the agent flagged for human judgment)                  |
|  Accuracy: 99.5% (2 out of 437 needed human correction)  |
|                                                           |
|  [Adjust Permissions]    [View Full History]              |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "437 actions, zero errors. Two overrides by Ah Mei, both were edge cases. This is working."

---

## Step 4: Reviewing a Held Action

Ahmad sees the held payroll item. He taps "Review & Approve."

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  September Payroll — Ready for Approval                   |
|                                                           |
|  Total gross: $39,800                                     |
|  Total net:   $34,150                                     |
|  CPF (employee): $4,776                                   |
|  CPF (employer): $6,766                                   |
|                                                           |
|  Changes from last month:                                 |
|  [info] Kumar S salary increased $2,400 -> $2,600         |
|         (the raise you approved on 5 Sep)                 |
|  [info] New employee: Jenny Tan added mid-month           |
|         (pro-rated salary: $1,800 for 15 days)            |
|                                                           |
|  No anomalies. All calculations verified against          |
|  previous month with expected variances.                  |
|                                                           |
|  [Approve]   [View Details]   [Reject]                    |
+----------------------------------------------------------+
```

**What Ahmad does:** Scans the changes (salary raise and new employee — both expected), taps "Approve."

**Time spent:** 45 seconds.

**What happens behind the scenes:**

- PACE session: payroll approval (HELD action resolved)
- Payroll status: draft -> approved
- GIRO and CPF files generated (HELD — Ahmad downloads separately)
- PactAuditEvent: payroll approved by D1-R1 (Ahmad)
- EATP audit anchor: September payroll run approved

---

## Step 5: Adjusting Agent Permissions

Ahmad has been thinking: claims under $200 are auto-approved, but his team has started submitting more transport claims since fuel prices went up. The average claim is now $180. He wants to raise the auto-approval threshold.

**What Ahmad does:** From the HR Agent detail view, taps "Adjust Permissions."

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  HR Agent — Permissions                                   |
|                                                           |
|  These are the rules for what the HR Agent can do          |
|  on its own versus what needs your approval.              |
|                                                           |
|  LEAVE APPROVALS                                          |
|  [check] Auto-approve routine leave               [edit] |
|  [check] Flag leave during peak periods            [edit] |
|  [lock]  Hold leave during notice period                  |
|                                                           |
|  CLAIMS                                                   |
|  Auto-approve claims up to: [$200       ]          [edit] |
|  Claims above this amount need your approval.             |
|                                                           |
|  ATTENDANCE                                               |
|  [check] Daily attendance check at 9:00 AM         [edit] |
|  [check] Message absent employees                  [edit] |
|  [check] Flag unreported absences to Ah Mei        [edit] |
|                                                           |
|  FINANCIAL LIMITS                                         |
|  Max approval per action: $500                     [edit] |
|  Daily cumulative limit:  $2,000                   [edit] |
|                                                           |
|  THINGS ONLY YOU CAN DO (cannot be changed here)          |
|  [lock] Payroll approval                                  |
|  [lock] Government submissions                            |
|  [lock] Employee termination                              |
|  [lock] Salary changes                                    |
|                                                           |
|  [Save Changes]    [Reset to Defaults]    [Cancel]        |
+----------------------------------------------------------+
```

**What Ahmad does:** Taps the claims threshold field, changes $200 to $500.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Confirm change                                           |
|                                                           |
|  You're increasing the claims auto-approval limit:        |
|                                                           |
|  BEFORE: Claims under $200 auto-approved                  |
|  AFTER:  Claims under $500 auto-approved                  |
|                                                           |
|  This means the agent will approve claims up to $500      |
|  without asking you first. You'll still get a             |
|  notification for each one.                               |
|                                                           |
|  Claims above $500 will still need your approval.         |
|                                                           |
|  [Confirm]    [Cancel]                                    |
+----------------------------------------------------------+
```

**What Ahmad does:** Taps "Confirm."

**What happens behind the scenes:**

- PactEnvelope updated: financial.approval_threshold changed from 200 to 500
- Verification gradient updated: claims $200-$500 moved from HELD to AUTO-APPROVED (with FLAGGED notification to Ahmad)
- Monotonic tightening validated: $500 is still within the owner's unlimited threshold
- EATP delegation record: Ahmad widens HR Agent's financial authority
- PactAuditEvent: envelope widened by owner

**Key design point:** The "Things Only You Can Do" section shows hard constraints that cannot be loosened from this screen. These are the BLOCKED actions in the agent's envelope. Ahmad cannot accidentally give the agent payroll approval authority from this simple settings screen. If Ahmad wants to change these, he would need to go through a different, more deliberate flow (which the system would hold for double-confirmation).

---

## Step 6: Trust Score and Cost Savings

Ahmad scrolls down on the dashboard.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  AGENT WORKFORCE — 6-MONTH SUMMARY                       |
|                                                           |
|  ── RELIABILITY ──────────────────────────────────         |
|                                                           |
|  HR Agent                                                 |
|  [========================================] 99.5%         |
|  437 actions, 0 errors, 2 human overrides                 |
|  Active: 6 months                                         |
|                                                           |
|  Payroll Agent                                            |
|  [========================================] 100%          |
|  6 payroll runs, 0 errors, 1 correction (Month 1)        |
|  Active: 5 months                                         |
|                                                           |
|  Compliance Agent                                         |
|  [========================================] 100%          |
|  8 alerts, 0 missed deadlines                             |
|  Active: 4 months                                         |
|                                                           |
|  ── WHAT THE AGENTS HANDLED ─────────────────────          |
|                                                           |
|  This month alone:                                        |
|  - 22 leave approvals                                     |
|  - 9 claims processed                                     |
|  - 22 daily attendance checks                             |
|  - 6 HR questions answered                                |
|  - 1 payroll run ($39,800)                                |
|  - 1 compliance alert (Ali's WP renewal)                  |
|                                                           |
|  ── TIME SAVED ───────────────────────────────────         |
|                                                           |
|  Your time saved this month:         ~8 hours             |
|  Ah Mei's time saved this month:     ~6.5 hours           |
|  Total time saved (6 months):        ~87 hours            |
|                                                           |
|  ── ESTIMATED VALUE ──────────────────────────────         |
|                                                           |
|  A part-time HR admin costs approximately $2,000/month    |
|  in Singapore (20 hours/week at $25/hour).                |
|                                                           |
|  Your agents handled the equivalent of ~14.5 hours        |
|  of HR work this month, worth approximately $1,450.       |
|                                                           |
|  6-month total: approximately $8,700 in equivalent        |
|  HR admin work handled by agents.                         |
|                                                           |
|  This is not a billing comparison — Arbor is open-source. |
|  It shows what you would spend if you hired someone       |
|  to do this work instead.                                 |
|                                                           |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "I would've needed a part-time HR person by now. Instead, the agents handle it. And Ah Mei gets to focus on finance."

**Key design point:** The cost savings number is carefully framed. It is not "Arbor saved you $8,700" (implying a billing comparison). It is "this is what you would have spent on equivalent human labor." Arbor is open-source under Terrene Foundation. The value proposition is productivity, not software pricing.

---

## Step 7: Handling an Anomaly on the Dashboard

One day, the dashboard shows a yellow indicator.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  My Team                                                  |
|                                                           |
|  12 employees    3 agents    1 issue                      |
|                                                           |
|  [!] HR Agent flagged an unusual pattern:                 |
|                                                           |
|  New employee Raj accessed 31 employee profiles           |
|  in the directory today. Most employees access            |
|  2-3 profiles per week.                                   |
|                                                           |
|  This was logged automatically. No data was exposed       |
|  (Raj can only see names and departments, not salary      |
|  or personal information).                                |
|                                                           |
|  [Noted — No Action]   [Restrict Directory Access]        |
|  [Talk to Raj]                                            |
+----------------------------------------------------------+
```

**PACT evaluation:**

- Pattern detected: `anomalous_volume` (31 accesses vs ~3 baseline)
- Data accessed: Employee directory (PUBLIC clearance — names, departments, titles)
- No confidential data was exposed (Raj's clearance is RESTRICTED, directory is PUBLIC)
- But the volume is unusual and the shadow agent flags it per the observation pattern

**What Ahmad does:** Taps "Noted — No Action." He knows Raj is new and probably just learning who everyone is.

**What happens behind the scenes:**

- PactSuggestion dismissed (anomalous_volume for Raj)
- If this pattern continues (Raj downloads 30+ profiles weekly), the system will re-alert with higher confidence
- If Raj's behavior normalizes, no further alerts

---

## Step 8: Dashboard Over Time — What Changes

### Month 1 Dashboard

```
1 agent (HR Agent, observing)
"HR Agent is learning how your team works."
No reliability data yet.
```

### Month 3 Dashboard

```
2 agents (HR Agent active, Payroll Agent active)
HR Agent: 89 actions, 100% accuracy
Payroll Agent: 1 run, 1 correction
Time saved: ~25 hours total
```

### Month 6 Dashboard

```
3 agents (HR, Payroll, Compliance — all active)
HR Agent: 437 actions, 99.5% accuracy
Payroll Agent: 6 runs, 100% accuracy
Compliance: 8 alerts, 0 missed
Time saved: ~87 hours total
Value: ~$8,700 equivalent HR admin work
```

### Month 12 Dashboard (Projected)

```
3-4 agents
HR Agent: ~900 actions, accuracy tracking
Payroll Agent: 12 runs
Compliance: 15+ alerts tracked
Time saved: ~180 hours total
New: possibly Recruitment Agent if Ahmad starts hiring more
Shadow agent suggests: "You've been hiring 1-2 people per
quarter. Want an agent to help with job postings and
candidate screening?"
```

---

## Step 9: What the Dashboard Does NOT Show

The dashboard is designed for a boss who checks for 2 minutes over kopi. It deliberately omits:

| Hidden Detail                  | Why It's Hidden          | Where to Find It                                        |
| ------------------------------ | ------------------------ | ------------------------------------------------------- |
| PACT addresses (D1-R1-D2-R1)   | Technical jargon         | Diagnostics panel (owner-only)                          |
| Envelope YAML/JSON             | Configuration complexity | "Adjust Permissions" screen (simplified)                |
| Clearance levels (C0-C4)       | Academic terminology     | Shown as "can see/cannot see" in permissions            |
| EATP record IDs                | Audit infrastructure     | Audit trail page (owner-only, for MOM/IRAS requests)    |
| Gradient zone names            | PACT vocabulary          | Shown as "auto/needs approval/blocked"                  |
| Template IDs (tmpl_hr_manager) | Internal implementation  | Never exposed to users                                  |
| Confidence scores (0.88)       | Statistical language     | Shown as "the agent is confident about this" or omitted |
| Observation store entries      | Surveillance feeling     | Summarized as "X actions this month"                    |

Every PACT concept is translated into a plain-language equivalent before it reaches the screen. The governance is real and enforced. The vocabulary is human and accessible.

---

## Step 10: Emergency Override

Ahmad receives an urgent call. An employee had a workplace accident. He needs to override the HR Agent's normal process and take immediate action.

**What Ahmad does:** Opens Arbor, goes to the employee's profile, taps "Emergency Action."

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Emergency Action — David Lee                             |
|                                                           |
|  [!] This bypasses normal approval flows.                 |
|  All actions will be logged and require a reason.         |
|                                                           |
|  What happened?                                           |
|  [Workplace injury - fell from forklift            ]      |
|                                                           |
|  Immediate actions:                                       |
|  [check] Mark David as on medical leave (effective now)   |
|  [check] Notify Ah Mei and John (David's supervisor)      |
|  [check] Generate WSH incident report form                |
|  [check] Check David's insurance coverage                 |
|  [ ] Contact next-of-kin (optional)                       |
|                                                           |
|  [Execute Emergency Actions]                              |
+----------------------------------------------------------+
```

**PACT evaluation:**

- Emergency override: Ahmad is the owner (D1-R1). He has maximum authority.
- Override bypasses normal gradient (actions that would normally be flagged or held execute immediately)
- EATP audit anchor: emergency bypass, with justification and expiry
- All actions fully logged — the audit trail is MORE complete during an emergency, not less

**What Ahmad does:** Checks all items except next-of-kin (he will call David's wife himself), enters the reason, taps "Execute Emergency Actions."

**What happens immediately:**

- David marked as on medical leave
- Ah Mei receives notification: "David Lee — workplace injury. On medical leave effective now."
- John receives notification: "David Lee — workplace injury. Please reassign his tasks."
- WSH incident report form generated (pre-filled with David's employment details, date/time, Ahmad's description)
- David's insurance coverage summary pulled from employee records
- PactAuditEvent: emergency actions executed by owner, bypass justification recorded
- Compliance Agent flags: "WSH incident report must be submitted to MOM within 10 days"

The dashboard returns to normal, but the compliance tracker now shows:

```
[!] WSH incident report due by 30 September
    Employee: David Lee
    [Complete & Submit Report]
```

---

## Failure Points and Mitigations

| Failure                                                            | Likelihood | Impact | Mitigation                                                                                                                                                                       |
| ------------------------------------------------------------------ | ---------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ahmad never opens the dashboard                                    | Medium     | Low    | Morning briefing pushes key metrics. Dashboard is a pull interface, briefing is push.                                                                                            |
| Dashboard data is stale (agent processed actions since last check) | Medium     | None   | Dashboard shows real-time data. "Actions today" updates live.                                                                                                                    |
| Cost savings estimate is misleading                                | Low        | Medium | Estimate is clearly labeled as "equivalent HR admin work" not "money saved." Based on MOM published median wages.                                                                |
| Ahmad changes a permission that breaks something                   | Low        | Medium | Monotonic tightening prevents unsafe widening. Hard constraints (payroll, government) cannot be changed from the simple settings screen. Confirmation dialog shows exact impact. |
| Agent performance degrades without Ahmad noticing                  | Low        | High   | Monthly reliability email sent even if Ahmad does not open the dashboard. Reliability drop below 95% triggers a dedicated alert.                                                 |
| Ahmad wants to remove an agent                                     | Low        | None   | "Adjust Permissions" screen includes "Deactivate Agent" at the bottom. Deactivation routes all agent tasks back to the human (Ah Mei or Ahmad). Reversible.                      |
