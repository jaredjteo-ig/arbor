# User Flow 05: Shadow-to-Agent Graduation

## Month 2-6: Ah Mei's Shadow Agent Graduates to Full Agent

**Persona**: Mei Ling (Ah Mei), 38, Admin Manager at Ahmad Logistics. Does HR, admin, and finance as side duties. Has been using Arbor since Day 1 — she was the first person Ahmad told about it. She handles leave approvals, attendance tracking, employee questions, and payroll prep. She is the de facto HR person but her title is "Admin Manager."

**PACT context**: Ah Mei's position is `D1-R1-D1-R1` (Admin Department, Admin Manager). Template: `tmpl_hr_manager`. Clearance: CONFIDENTIAL (C2). Her envelope allows leave management, attendance, claims, employee record management, view payroll. It does NOT allow: approve payroll, submit CPF, change statutory rates, terminate employees.

**Key insight**: Ah Mei has a shadow agent watching her work patterns. The shadow agent is not doing the work — Ah Mei is. But the shadow agent is learning what Ah Mei's work looks like so it can eventually do that work instead of her. This is the graduation path: observe -> suggest -> partially automate -> fully automate.

---

## Phase 1: Observation (Month 1-2)

### What Ah Mei Does Every Day

The shadow agent silently records Ah Mei's daily work patterns:

```
WEEKLY PATTERN (observed over 8 weeks):

Monday:
  08:30 — Login, check attendance dashboard
  08:45 — Process any leave requests from the weekend (1-3 requests)
  09:00 — Check employee messages (usually 1-2 HR questions)
  09:30 — Answer HR questions by looking up policies
  10:00 — Regular work (admin, not HR)

Tuesday-Thursday:
  08:30 — Login, check attendance
  09:00 — Process leave requests if any (0-2 per day)
  Sporadic — Answer employee questions
  Otherwise — Regular admin work

Friday:
  08:30 — Check attendance
  09:00 — Compile weekly attendance summary for Ahmad
  10:00 — Process any pending claims (2-5 per week)
  14:00 — Print/file employee documents

25th of month:
  08:30 — Pull salary data for all employees
  09:00 — Help Ahmad with payroll calculation (since Month 1,
           this is now "review the Payroll Agent's output")
  10:00 — Generate payslips (now automated)
  11:00 — File payslips
```

### What the Shadow Agent Records

```
ObservationStore entries for Ah Mei (30-day summary):

Module: leave
  approve_leave: 22 actions
  avg_time_to_approve: 4 minutes
  rejection_rate: 0%
  pattern: approves within balance, within policy, no questions asked

Module: attendance
  view_attendance: 46 actions (daily check)
  flag_absence: 3 actions (flagged unreported absences to Ahmad)

Module: employees
  view_employee: 31 actions
  update_employee: 5 actions (address changes, bank updates)

Module: claims
  approve_claim: 8 actions
  avg_claim_amount: $67
  rejection_rate: 0% (all within policy)

Module: advisory
  ask_question: 6 actions
  questions about: leave entitlements (3), CPF rates (2), notice period (1)

Module: payroll
  view_payroll: 4 actions
  (payroll approval goes through Ahmad, not Ah Mei)
```

### Shadow Agent's Internal Assessment

After 8 weeks of observation, the PactInferenceEngine produces this analysis:

```
User: Mei Ling (D1-R1-D1-R1)
Observation window: 56 days
Total actions: 126

PATTERNS DETECTED:

1. LEAVE APPROVAL — Confidence: 0.95
   Pattern: Ah Mei approves ALL leave requests that are within
   balance and within policy. Zero rejections in 8 weeks.
   Average time from request to approval: 4 minutes.
   She does not exercise judgment — she checks two things
   (balance OK? policy OK?) and approves.

   ASSESSMENT: This is a mechanical task. An agent can do
   exactly what Ah Mei does with 100% accuracy.

2. ATTENDANCE MONITORING — Confidence: 0.88
   Pattern: Ah Mei checks attendance every morning at ~08:30.
   She looks for: unreported absences (no MC, no leave,
   didn't clock in). When she finds one, she messages the
   employee first, then flags to Ahmad if no response.

   ASSESSMENT: This is pattern-based monitoring with a
   two-step escalation. An agent can replicate this.

3. CLAIMS PROCESSING — Confidence: 0.82
   Pattern: Ah Mei approves all claims under $200 that have
   receipts attached. She has never rejected a claim.

   ASSESSMENT: Rule-based approval. Agent can do this.

4. HR QUESTIONS — Confidence: 0.70
   Pattern: Ah Mei looks up policy documents and leave
   entitlements to answer employee questions. She sometimes
   asks the advisory agent for SG employment law guidance.

   ASSESSMENT: The advisory engine already handles this.
   Ah Mei is acting as a human proxy for an existing agent
   capability.

5. PAYROLL SUPPORT — Confidence: 0.60
   Pattern: Ah Mei reviews payroll output but does not approve.
   Her involvement is reading + confirming, not deciding.

   ASSESSMENT: Low-value intermediate step. Ahmad reviews
   anyway. But confidence too low to suggest removal.
```

---

## Phase 2: First Suggestion to Boss (Week 8)

The shadow agent surfaces its first suggestion to Ahmad (not to Ah Mei — governance suggestions go to the owner).

### What Ahmad Sees in His Morning Briefing

```
+----------------------------------------------------------+
|  Good morning, Ahmad                     Mon 12 May 2026  |
|                                                           |
|  SUGGESTION                                               |
|                                                           |
|  Ah Mei approves every leave request that follows your    |
|  company policy — she's approved 22 this month without    |
|  declining any. Each one takes her about 4 minutes to     |
|  check balance and approve.                               |
|                                                           |
|  The HR Agent can do the same thing: check the balance,   |
|  check the policy, and approve automatically. Ah Mei      |
|  would get a notification instead of an approval task.    |
|                                                           |
|  This would free up about 90 minutes of Ah Mei's time    |
|  per month.                                               |
|                                                           |
|  What changes:                                            |
|  BEFORE: Employee applies -> Ah Mei reviews -> approves   |
|  AFTER:  Employee applies -> Agent approves automatically |
|          Ah Mei gets a notification (can override)        |
|                                                           |
|  Unusual requests (during notice period, low coverage,    |
|  5+ consecutive days) still come to you for approval.     |
|                                                           |
|  [Let the Agent Handle Leave]   [Tell Me More]   [No]    |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Ah Mei approves everything anyway. Makes sense to automate it. She can still see what's happening."

**What Ahmad does:** Taps "Let the Agent Handle Leave."

### What Happens Behind the Scenes

- HR Agent's envelope updated: `operational.allowed_action_types += "approve_routine_leave"`
- Gradient config: routine leave (within balance, within policy, good coverage) moves from HELD to AUTO-APPROVED
- Non-routine leave (notice period, low coverage, 5+ days, near balance exhaustion) remains HELD for Ahmad
- Ah Mei's own envelope unchanged — she can still approve leave manually if she wants to override
- EATP delegation record: Ahmad delegates routine leave approval from Ah Mei to HR Agent
- PactSuggestion marked as "accepted"
- Notification sent to Ah Mei: "Ahmad has set up automatic approval for routine leave requests. You'll get a notification for each one, and you can still override if needed."

### What Ah Mei Sees

```
+----------------------------------------------------------+
|  [info] Update to your workflow                           |
|                                                           |
|  Ahmad has set up automatic leave approvals for routine   |
|  requests (within policy, good team coverage).            |
|                                                           |
|  What this means for you:                                 |
|  - You'll get a notification when leave is auto-approved  |
|  - You can override any decision if something looks wrong |
|  - Unusual requests still come to you or Ahmad            |
|                                                           |
|  This frees up your mornings — no more manually checking  |
|  each leave request.                                      |
|                                                           |
|       [OK, got it]    [I have questions]                  |
+----------------------------------------------------------+
```

**What Ah Mei thinks:** "Finally. I was just rubber-stamping those anyway."

---

## Phase 3: Second Suggestion — Claims (Week 12)

Four weeks after leave was automated. The shadow agent has continued observing Ah Mei's remaining work patterns.

### What Ahmad Sees

```
+----------------------------------------------------------+
|  SUGGESTION                                               |
|                                                           |
|  Since we automated leave approvals, Ah Mei's routine     |
|  HR work has dropped by about 90 minutes per month.       |
|                                                           |
|  The next biggest routine task: claims processing.        |
|  Ah Mei approves all claims under $200 that have          |
|  receipts. She's approved 32 claims in 4 months           |
|  without rejecting any.                                   |
|                                                           |
|  Want the agent to auto-approve small claims too?         |
|                                                           |
|  What changes:                                            |
|  BEFORE: Employee submits claim -> Ah Mei checks receipt  |
|          -> approves                                      |
|  AFTER:  Employee submits claim -> Agent checks receipt   |
|          is attached -> auto-approves if under $200       |
|          Ah Mei gets notification. Claims above $200      |
|          still need manual review.                        |
|                                                           |
|  [Auto-Approve Small Claims]   [Tell Me More]   [No]     |
+----------------------------------------------------------+
```

Ahmad approves. Another chunk of Ah Mei's HR work transfers to the agent.

---

## Phase 4: Third Suggestion — Attendance (Week 16)

### What Ahmad Sees

```
+----------------------------------------------------------+
|  SUGGESTION                                               |
|                                                           |
|  Ah Mei checks attendance every morning and flags          |
|  employees who didn't clock in and don't have leave.      |
|  She does this 5 days a week, spending about 15 minutes   |
|  each time.                                               |
|                                                           |
|  The agent can do this automatically:                     |
|  1. Check attendance at 9:00 AM daily                     |
|  2. If someone didn't clock in and has no leave:          |
|     - Send them a message: "Are you coming in today?"     |
|     - If no response by 10:00 AM, flag to Ah Mei         |
|  3. Weekly attendance summary sent to you on Friday       |
|                                                           |
|  This matches exactly what Ah Mei does today.             |
|                                                           |
|  [Automate Attendance Checks]   [Tell Me More]   [No]    |
+----------------------------------------------------------+
```

Ahmad approves. Attendance monitoring moves to the agent.

---

## Phase 5: The Transition Moment (Month 5)

At this point, the shadow agent has observed that most of Ah Mei's HR duties have been automated:

| HR Task               | Before                          | Now                                   | Time Saved     |
| --------------------- | ------------------------------- | ------------------------------------- | -------------- |
| Leave approvals       | Ah Mei reviews each one         | Agent auto-approves routine           | ~90 min/month  |
| Claims processing     | Ah Mei checks receipt, approves | Agent auto-approves under $200        | ~45 min/month  |
| Attendance monitoring | Ah Mei checks every morning     | Agent checks, escalates exceptions    | ~75 min/month  |
| HR questions          | Ah Mei looks up policies        | Advisory engine answers directly      | ~60 min/month  |
| Payroll prep          | Ah Mei reviews with Ahmad       | Payroll Agent handles, Ahmad approves | ~120 min/month |

**Total time saved: approximately 6.5 hours per month** — nearly a full work day.

### What Ahmad Sees in Month 5 Briefing

```
+----------------------------------------------------------+
|  INSIGHT                                                  |
|                                                           |
|  Over the past 5 months, the HR Agent has taken over      |
|  most of Ah Mei's routine HR work:                        |
|                                                           |
|  - Leave approvals: 100% automated (48 this month)        |
|  - Claims: Small claims automated (12 this month)         |
|  - Attendance: Daily checks automated                     |
|  - Payroll: Handled by Payroll Agent                      |
|                                                           |
|  Ah Mei's remaining HR tasks:                             |
|  - Handling unusual situations (2-3 per month)            |
|  - Employee onboarding (when you hire)                    |
|  - Overriding agent decisions when needed (rare)          |
|                                                           |
|  Ah Mei now spends about 95% of her time on admin and     |
|  finance work instead of HR.                              |
|                                                           |
|  This is just an observation — no action needed.          |
|  Everything is working well.                              |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "So the agent is basically doing the HR Manager job now. Ah Mei can focus on the stuff I actually hired her for."

This is NOT a suggestion to fire Ah Mei. This is a statement of fact: the HR Manager role in Ahmad's PACT tree is now effectively agent-filled. Ah Mei's human role has shifted from "person who does HR" to "person who oversees the agent that does HR and handles exceptions."

---

## Phase 6: Full Graduation (Month 6)

The shadow agent makes one final structural observation.

### What Ahmad Sees

```
+----------------------------------------------------------+
|  OBSERVATION                                              |
|                                                           |
|  Your team structure shows Ah Mei as Admin Manager        |
|  responsible for HR. But in practice, the HR Agent now    |
|  handles the daily HR work, and Ah Mei steps in only      |
|  for exceptions.                                          |
|                                                           |
|  Your actual structure looks like:                        |
|                                                           |
|         [Ahmad]                                           |
|        Director                                           |
|        /     \                                            |
|   [Admin]    [Operations]                                 |
|      |          ...                                       |
|   [Ah Mei]                                               |
|   Admin & Finance                                        |
|      |                                                    |
|   [HR Agent]     <-- doing the daily HR work              |
|   handles leave, claims, attendance                       |
|                                                           |
|  Ah Mei is effectively supervising the HR Agent.          |
|  Want me to update the team structure to reflect this?    |
|                                                           |
|  What changes:                                            |
|  - HR Agent becomes a formal role in the team chart       |
|  - Ah Mei appears as its supervisor (she can override)    |
|  - Ahmad remains the final authority for big decisions    |
|                                                           |
|  This is just a label change — it reflects what's         |
|  already happening. No permissions change.                |
|                                                           |
|  [Update Structure]   [No, Leave As-Is]                   |
+----------------------------------------------------------+
```

**What Ahmad does:** Taps "Update Structure."

### Updated PACT Tree

```
BOD (vacant)
D1 (Ahmad Logistics Pte Ltd)
  D1-R1 (Ahmad — Director) [tmpl_owner]
    D1-R1-D1 (Admin & Finance)
      D1-R1-D1-R1 (Ah Mei — Admin & Finance Manager) [tmpl_hr_manager]
        D1-R1-D1-R1-R2 (Siti Aminah — Admin Assistant) [tmpl_employee_office]
        D1-R1-D1-R1-D1 (HR Operations)
          D1-R1-D1-R1-D1-R1 (HR Agent) [agent-filled, tmpl_hr_exec]
    D1-R1-D2 (Operations)
      ... (unchanged)
    D1-R1-D3 (Finance)
      D1-R1-D3-R1 (Payroll Agent) [agent-filled, tmpl_payroll_officer]
```

The HR Agent now has a formal position in the tree, under Ah Mei's supervision. Ah Mei can override any agent decision. Ahmad can override Ah Mei. The hierarchy is:

```
Ahmad (authority: everything)
  -> Ah Mei (authority: override agent, handle exceptions)
    -> HR Agent (authority: routine HR within envelope)
```

This is the graduation: the shadow agent observed Ah Mei's work, suggested automation piece by piece, and over 6 months the "HR Manager" role transitioned from human-filled to agent-filled with human oversight.

---

## What Ah Mei Experiences Over 6 Months

| Month | Ah Mei's HR Workload                                      | Agent's Role                 | Ah Mei's Experience                             |
| ----- | --------------------------------------------------------- | ---------------------------- | ----------------------------------------------- |
| 1     | Full (leave, attendance, claims, questions, payroll prep) | Observing silently           | "This Arbor thing is watching. Whatever."       |
| 2     | Full minus leave (leave auto-approved)                    | Leave automation             | "Nice, I don't have to check leave anymore"     |
| 3     | Full minus leave and small claims                         | Claims automation            | "More time for actual admin work"               |
| 4     | Full minus leave, claims, and attendance                  | Attendance automation        | "Mornings are free now"                         |
| 5     | Exceptions only (2-3 per month)                           | Handling 95% of routine HR   | "I barely do HR anymore"                        |
| 6     | Supervises agent, handles exceptions                      | Formal HR Agent role in tree | "I'm the person the agent asks when it's stuck" |

### What Ah Mei NEVER Experiences

- Being told she is being "replaced"
- Losing access to anything she had before
- Having her role diminished
- Being forced to accept automation she does not want

At every step, Ahmad made the decision. Ah Mei was notified but never asked to approve her own obsolescence. The agent did not compete with Ah Mei — it took over the mechanical parts of her work that she was already rubber-stamping.

---

## The Trust Mechanics

### Why This Worked

1. **Observation before suggestion.** The shadow agent watched for 8 weeks before making its first suggestion. It had overwhelming evidence (22 approvals, zero rejections, 4-minute average) before it said anything.

2. **Smallest possible step first.** The first automation was leave approval — the most routine, lowest-risk task. Not payroll. Not compliance. Not terminations.

3. **Boss decides, not the agent.** Every automation step was Ahmad's decision. The shadow agent suggested; Ahmad approved. The PACT principle: agents suggest, humans authorize.

4. **Ah Mei was informed, not consulted.** This might seem harsh, but it reflects reality: the employer decides how work is organized. Ah Mei was told what changed and given override capability. She was not asked to approve a change that benefits the company.

5. **Reversible at every step.** "You can take back this access anytime." Every automation can be reverted. Ah Mei can override any individual decision. Ahmad can turn off the entire agent.

6. **Progressive, not revolutionary.** Six months. Five small steps. Each step was a minor quality-of-life improvement, not a dramatic reorganization. By the time the "HR Manager role is agent-filled" observation was made, it was just acknowledging reality.

### PACT Invariants Maintained

| Invariant              | How It's Maintained                                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Monotonic tightening   | HR Agent's envelope is always tighter than Ah Mei's (Ah Mei can override agent)                                                       |
| Clearance independence | HR Agent has CONFIDENTIAL clearance for employee data, same as Ah Mei. Clearance did not change — only operational authority changed. |
| Grammar constraint     | Every node in the tree is valid D/T/R. The agent node follows the same structural rules as a human node.                              |
| Human-on-the-loop      | Ahmad approves every governance change. Ah Mei can override every operational decision.                                               |
| EATP audit trail       | Every graduation step has a delegation record. Every agent action has an audit anchor.                                                |

---

## Failure Points and Mitigations

| Failure                                                | Likelihood | Impact | Mitigation                                                                                                                                                                              |
| ------------------------------------------------------ | ---------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ah Mei resents the automation                          | Medium     | Medium | Framing matters. She is freed from drudge work, not replaced. Her override capability is real. Her admin/finance work remains hers.                                                     |
| Agent makes a mistake Ah Mei would not have            | Low        | Medium | Ah Mei gets notifications for all agent decisions. She can override within 24 hours. Mistakes are caught by the same person who was doing the job.                                      |
| Ahmad approves automation too quickly                  | Low        | Low    | Confidence threshold of 0.70 means the pattern must be strong. The agent does not suggest automation after 2 occurrences — it waits for a statistically significant pattern.            |
| Ah Mei leaves the company                              | Low        | High   | The HR Agent is already handling the work. Ah Mei's departure does not create a coverage gap. New hire (if any) steps into the supervisor role.                                         |
| Agent's observations are wrong (misidentified pattern) | Low        | Medium | Ah Mei's override capability catches the first error. The pattern is re-evaluated. False positives in observation do not lead to automation — the suggestion requires Ahmad's approval. |
| Employee trust erodes ("a robot handles my leave now") | Medium     | Low    | Employees experience faster service. Leave approved in seconds instead of hours. The UX is the same — they apply, it gets approved. They do not need to know who (or what) approved it. |
