# User Flow 02: Payroll Agent Activation

## Month 1: Ahmad Activates the Payroll Agent

**Persona**: Ahmad, same logistics boss from Flow 01. Has been using Arbor for 4 weeks. HR Agent handles leave and attendance. Ahmad still calculates payroll manually on the 25th of each month using a spreadsheet, then transfers via internet banking.

**Trigger**: It is 24 March. Ahmad is about to do payroll. Arbor knows this because the shadow agent has observed Ahmad's pattern: he logs in, views employee records, and then disappears for 3 hours (the time he spends on his spreadsheet).

---

## Step 1: The Suggestion

Ahmad opens Arbor on the morning of the 24th. His daily briefing contains an unusual item.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Good morning, Ahmad                     Mon 24 Mar 2026  |
|                                                           |
|  YOUR COMPANY TODAY                                       |
|                                                           |
|  Team: 12 employees, all active                           |
|  Leave: 2 on leave today (Raju — MC, Siti — annual)      |
|  HR Agent: 14 actions this week, 0 issues                 |
|                                                           |
|  ──────────────────────────────────────────                |
|                                                           |
|  SUGGESTION                                               |
|                                                           |
|  Payroll is due tomorrow. Last month you spent about      |
|  3 hours calculating salaries, CPF, and generating        |
|  payslips.                                                |
|                                                           |
|  Arbor can calculate payroll for you. It handles:         |
|  - Base salary + allowances for all 12 employees          |
|  - CPF contributions (employee + employer)                |
|  - SDL, SHG fund deductions                               |
|  - Unpaid leave deductions (auto-pulled from leave data)  |
|  - Overtime (from attendance records)                      |
|  - Generate payslips for everyone                         |
|                                                           |
|  Want to try it this month? You'll review everything      |
|  before anything is finalized.                            |
|                                                           |
|  [Try Payroll Agent]   [Not This Month]                   |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "3 hours, yeah, that's about right. If I can review everything before it's final, what's the harm in trying?"

**What Ahmad does:** Taps "Try Payroll Agent."

---

## Step 2: Payroll Agent Capabilities

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Payroll Agent                                            |
|                                                           |
|  WHAT IT DOES                                             |
|                                                           |
|  [checkmark] Calculate monthly salary for each employee   |
|  [checkmark] Compute CPF (employee + employer portions)   |
|  [checkmark] Apply SDL (Skills Development Levy)          |
|  [checkmark] Route SHG fund by race (CDAC/MBMF/SINDA/ECF)|
|  [checkmark] Deduct unpaid leave (pulled from leave data) |
|  [checkmark] Add overtime pay (from attendance records)   |
|  [checkmark] Generate individual payslips (PDF)           |
|  [checkmark] Prepare CPF e-Submission file                |
|  [checkmark] Prepare bank GIRO file for salary transfer   |
|                                                           |
|  WHAT IT DOES NOT DO                                      |
|                                                           |
|  [lock] Submit anything to CPF Board — you do that        |
|  [lock] Transfer money to any bank account — you do that  |
|  [lock] Submit tax filings to IRAS — you do that          |
|  [lock] Change anyone's salary — only you can do that     |
|  [lock] Approve the payroll run — you review and confirm  |
|                                                           |
|  In short: the agent does all the math. You press the     |
|  final "go" button. Nothing leaves your company without   |
|  your approval.                                           |
|                                                           |
|  [Activate Payroll Agent]     [Cancel]                    |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "So it does the calculation part and I still do the bank transfer and CPF submission myself. That's the hard part done for me."

**What Ahmad does:** Taps "Activate Payroll Agent."

**What happens behind the scenes:**

- New PactNode created in the PACT tree under Finance (auto-created D node):

```
D1-R1 (Ahmad)
  D1-R1-D1 (Admin)
    ...
  D1-R1-D2 (Operations)
    ...
  D1-R1-D3 (Finance)            <-- auto-created
    D1-R1-D3-R1 (Payroll Agent) <-- agent-filled role
```

- Payroll Agent assigned template `tmpl_payroll_officer` with modifications:
  - Financial: calculate payroll (unlimited — it is computation, not spending)
  - Operational: generate payslips, prepare CPF file, prepare GIRO file, pull leave/attendance data
  - Blocked: approve payroll run (HELD for Ahmad), submit CPF (HELD), change salary (BLOCKED), bank transfers (BLOCKED)
  - Data Access: CONFIDENTIAL (needs salary data, bank details for GIRO file)
  - Communication: internal only (no external submissions)
  - Temporal: payroll processing window (20th-28th of each month)
- Verification gradient:
  - Auto-approved: calculate individual employee pay, generate payslip PDF
  - Flagged: payroll variance >5% from previous month (something changed)
  - Held: approve final payroll run, generate CPF submission file, generate GIRO file
  - Blocked: modify salary, submit to CPF Board, submit to IRAS
- EATP delegation record: Ahmad delegates payroll computation to Payroll Agent

Ahmad does not see any of this.

---

## Step 3: First Payroll Run — Agent Calculates

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Payroll Agent is preparing March payroll...              |
|                                                           |
|  [progress bar: ████████████████░░░░ 80%]                 |
|                                                           |
|  Step 1: Pulled salary data for 12 employees     [done]   |
|  Step 2: Calculated CPF contributions             [done]   |
|  Step 3: Applied SDL and SHG deductions           [done]   |
|  Step 4: Checked leave records for deductions     [done]   |
|  Step 5: Checked attendance for overtime           [now]   |
|  Step 6: Generating payslips                    [pending]  |
|  Step 7: Preparing summary for your review      [pending]  |
|                                                           |
+----------------------------------------------------------+
```

30 seconds later:

```
+----------------------------------------------------------+
|  March Payroll — Ready for Your Review                    |
|                                                           |
|  SUMMARY                                                  |
|  Total gross: $38,400                                     |
|  Total CPF (employee): $4,608                             |
|  Total CPF (employer): $6,528                             |
|  Total SDL: $96                                           |
|  Total SHG: $24                                           |
|  Total net pay: $33,168                                   |
|                                                           |
|  EMPLOYEES                                                |
|  +------+----------------+---------+--------+---------+   |
|  | #    | Name           | Gross   | CPF(E) | Net Pay |   |
|  +------+----------------+---------+--------+---------+   |
|  | 1    | Mei Ling       | $4,200  | $504   | $3,598  |   |
|  | 2    | John Tan       | $3,800  | $456   | $3,258  |   |
|  | 3    | Sarah Lim      | $3,800  | $456   | $3,258  |   |
|  | 4    | Raju Kumar     | $2,400  | $288   | $2,064  |   |
|  | 5    | Ali bin Osman  | $2,400  | $288   | $2,064  |   |
|  | 6    | Priya Devi     | $2,600  | $312   | $2,240  |   |
|  | 7    | Wei Ming       | $2,600  | $312   | $2,240  |   |
|  | 8    | Faizal         | $2,200  | $264   | $1,896  |   |
|  | 9    | David Lee      | $2,800  | $336   | $2,408  |   |
|  | 10   | Siti Aminah    | $2,200  | $264   | $1,896  |   |
|  | 11   | Kumar S        | $2,400  | $288   | $2,064  |   |
|  +------+----------------+---------+--------+---------+   |
|                                                           |
|  NOTES                                                    |
|  - Raju had 1 day MC (no deduction — paid medical leave)  |
|  - Siti had 3 days annual leave (no deduction)            |
|  - John worked 4 hours overtime ($57.69 added)            |
|  - No foreign worker levy this month (all citizens/PRs)   |
|                                                           |
|  [flag] Net pay is $1,240 lower than February.            |
|  Reason: David Lee's salary was adjusted from $3,000 to   |
|  $2,800 last month.                                       |
|                                                           |
|  Tap any employee to see their detailed payslip.          |
|                                                           |
|  [Approve Payroll]   [Make Changes]   [Cancel Run]        |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Oh right, I reduced David's pay because he moved from the forklift role. The numbers look right. Let me check one payslip to be sure."

**What Ahmad does:** Taps on "John Tan" to see the detailed payslip.

---

## Step 4: Detailed Payslip Review

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  March 2026 Payslip — John Tan                           |
|                                                           |
|  EARNINGS                                                 |
|  Basic Salary                          $3,600.00          |
|  Transport Allowance                     $200.00          |
|  Overtime (4 hrs x $14.42/hr)             $57.69          |
|                                          --------          |
|  Total Gross                           $3,857.69          |
|                                                           |
|  DEDUCTIONS                                               |
|  CPF — Employee (12%)                    $456.00          |
|  SDL (0.25%)                               $9.50          |
|  CDAC (Chinese)                            $2.00          |
|                                          --------          |
|  Total Deductions                        $467.50          |
|                                                           |
|  NET PAY                               $3,390.19          |
|                                                           |
|  EMPLOYER CONTRIBUTIONS                                   |
|  CPF — Employer (17%)                    $646.00          |
|                                                           |
|  [Download PDF]     [Back to Summary]                     |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "That's exactly what I'd have calculated. The overtime rate is right — $3,600 / 26 days / 8 hours x 1.5 = $25.96... wait, no. Let me check."

Ahmad pauses. The OT calculation looks off. He taps "Make Changes" on the summary.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  What would you like to change?                           |
|                                                           |
|  [ ] An employee's salary is wrong                        |
|  [o] A calculation doesn't look right                     |
|  [ ] I need to add a bonus or deduction                   |
|  [ ] An employee should not be in this run                |
|                                                           |
|  Tell me what's wrong:                                    |
|  [John's OT rate seems low. Shouldn't it be      ]       |
|  [based on basic salary $3,600?                   ]       |
|                                                           |
|       [Submit]                                            |
+----------------------------------------------------------+
```

**Agent responds in-line:**

```
+----------------------------------------------------------+
|  You're right to check. Here's how the OT was calculated: |
|                                                           |
|  John's OT rate:                                          |
|  $3,600 (basic) / 26 days / 8 hours = $17.31/hour        |
|  OT rate: $17.31 x 1.5 = $25.96/hour                     |
|  But John's basic is capped at OW ceiling $8,000          |
|  (not relevant here — his basic is below ceiling).        |
|                                                           |
|  Wait — I see the issue. The calculation on the payslip   |
|  shows $14.42/hr. Let me recheck...                       |
|                                                           |
|  Correction: I was incorrectly using gross ($3,857.69)    |
|  instead of basic ($3,600) for the hourly rate base.      |
|  Recalculating:                                           |
|                                                           |
|  Correct: $3,600 / 26 / 8 x 1.5 = $25.96/hr             |
|  4 hours x $25.96 = $103.85 (was $57.69)                 |
|  Difference: +$46.16                                      |
|                                                           |
|  [Apply Correction]    [Recalculate All]                  |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Good thing I checked. But the system caught my question and recalculated. Next month it'll get it right."

**What Ahmad does:** Taps "Apply Correction." The payroll run recalculates with the corrected OT rate. Ahmad reviews the updated summary and taps "Approve Payroll."

**What happens behind the scenes:**

- Payroll run correction recorded in PactAuditEvent
- The correction feeds back into the payroll engine's OT calculation (this is a real bug being fixed, not just an envelope issue)
- PACE session: Approve Payroll is a HELD action. Ahmad's approval is the PACE Approve step.
- Payroll status: draft -> approved
- EATP audit anchor: payroll run approved by owner, with correction history
- Observation recorded: Ahmad reviewed the payroll in detail, found an error, corrected it. This tells the system that Ahmad is a careful payroll reviewer who reads line items.

---

## Step 5: Post-Approval — Generating Files

**What Ahmad sees after approval:**

```
+----------------------------------------------------------+
|  [checkmark] March Payroll Approved                       |
|                                                           |
|  Next steps (you handle these):                           |
|                                                           |
|  1. Download bank GIRO file                               |
|     Upload this to your bank's internet banking           |
|     to transfer salaries.                                 |
|     [Download GIRO File]                                  |
|                                                           |
|  2. Download CPF submission file                          |
|     Upload this to the CPF e-Submit portal to             |
|     submit employer and employee contributions.           |
|     [Download CPF File]                                   |
|                                                           |
|  3. Payslips have been generated                          |
|     Employees can view their payslips in Arbor.           |
|     [Preview All Payslips]  [Download All as PDF]         |
|                                                           |
|  Reminder: CPF contributions are due by the 14th of       |
|  next month (14 April 2026).                              |
|                                                           |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Three clicks and I'm done. Download GIRO, upload to DBS. Download CPF, upload to CPF portal. Used to take me 3 hours."

**What Ahmad does:** Downloads both files, notes the CPF deadline.

**Key design point:** The agent prepared the files but did NOT submit them. The GIRO file goes to Ahmad's bank. The CPF file goes to the CPF Board portal. These are external submissions — HELD for boss under the Payroll Agent's envelope (communication: internal only; external submissions blocked). Ahmad does the final mile himself.

---

## Step 6: Month 2 — Second Payroll Run

One month later. Ahmad has not done the spreadsheet. He opens Arbor on the 24th.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Good morning, Ahmad                     Thu 24 Apr 2026  |
|                                                           |
|  PAYROLL                                                  |
|                                                           |
|  April payroll is ready for your review.                  |
|                                                           |
|  Total: $38,560 (up $160 from March — John's OT was      |
|  higher this month: 6 hours instead of 4)                 |
|                                                           |
|  No anomalies detected. All calculations use the          |
|  corrected OT formula from last month.                    |
|                                                           |
|  [Review & Approve]                                       |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "It remembered the OT fix. Let me just check the total."

**What Ahmad does:** Taps "Review & Approve." Scans the summary. Everything matches his expectations. Taps "Approve Payroll" without checking individual payslips this time.

**What PACT observes:**

- March: Ahmad reviewed in detail, checked individual payslips, found an error, took 25 minutes
- April: Ahmad reviewed the summary only, approved in 3 minutes
- Pattern emerging: Ahmad is developing trust in the calculations

---

## Step 7: Month 3 — Third Payroll Run

May payroll. Ahmad opens Arbor on the 24th.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Good morning, Ahmad                     Mon 24 May 2026  |
|                                                           |
|  PAYROLL                                                  |
|                                                           |
|  May payroll is ready for your review.                    |
|  Total: $39,200 (+$640 from April)                        |
|                                                           |
|  Changes from last month:                                 |
|  - Wei Ming's salary increased from $2,600 to $2,800     |
|    (the raise you approved on 15 May)                     |
|  - Raju had 2 days unpaid leave (-$184.62 deducted)      |
|                                                           |
|  [Review & Approve]                                       |
|                                                           |
|  ──────────────────────────────────────────                |
|                                                           |
|  SUGGESTION                                               |
|                                                           |
|  You've approved payroll 3 months in a row, and it's      |
|  been accurate each time. Want me to prepare payroll      |
|  automatically each month? You'd still review a summary   |
|  before it's finalized — but I won't wait for you to      |
|  start the calculation.                                   |
|                                                           |
|  BEFORE: I wait for you to start payroll, then calculate  |
|  AFTER:  I calculate on the 24th, send you the summary    |
|          to approve. If anything looks wrong, you fix it   |
|          before approving. Nothing changes without your OK.|
|                                                           |
|  [Yes, prepare automatically]    [No, I'll start it]      |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "It's been right 3 months in a row. I just scan the summary anyway. Sure, let it prepare automatically."

**What Ahmad does:** Taps "Yes, prepare automatically." Then reviews the May payroll and taps "Approve."

---

## Step 8: The Gradient Shift

What Ahmad just agreed to is a gradient shift in PACT terms:

| Action                    | Before                                   | After                                             |
| ------------------------- | ---------------------------------------- | ------------------------------------------------- |
| Calculate payroll         | HELD (agent waits for Ahmad to initiate) | AUTO-APPROVED (agent initiates on the 24th)       |
| Generate payslips         | HELD (waits for payroll approval)        | FLAGGED (generated automatically, Ahmad notified) |
| Approve final payroll run | HELD (Ahmad must approve)                | HELD (unchanged — Ahmad still approves)           |
| Generate CPF/GIRO files   | HELD (waits for payroll approval)        | HELD (unchanged — generated only after approval)  |
| Submit to CPF Board       | BLOCKED (Ahmad does manually)            | BLOCKED (unchanged)                               |

The critical constraint — approval of the final payroll run — remains HELD. Ahmad still reviews and approves the numbers. The gradient shift only affects the preparation, not the decision.

**What happens behind the scenes:**

- Payroll Agent's envelope updated: `operational.allowed_action_types += "initiate_payroll_calculation"`
- Gradient config updated: payroll calculation moved from "held" to "auto"
- Gradient config updated: payslip generation moved from "held" to "flagged"
- EATP delegation record: Ahmad delegates payroll initiation to Payroll Agent
- PactAuditEvent: gradient shift, approved by owner

---

## Step 9: Month 4 Onwards — Automatic Preparation

From June onwards, on the 24th of each month:

1. Payroll Agent automatically calculates all salaries (auto-approved)
2. Payroll Agent generates draft payslips (flagged — Ahmad gets notification)
3. Ahmad receives a morning briefing item: "June payroll is ready: $39,400. No anomalies. [Review & Approve]"
4. Ahmad reviews the summary, taps approve (2 minutes)
5. GIRO and CPF files generated (held — Ahmad downloads them)
6. Ahmad uploads to bank and CPF portal (manual — outside Arbor)

**Time comparison:**

- Before Arbor: 3 hours per month (spreadsheet calculation + manual payslips)
- Month 1 with agent: 25 minutes (detailed review, found error)
- Month 2 with agent: 3 minutes (summary review)
- Month 4+ with agent: 2 minutes (approve from briefing notification)

---

## Step 10: Future Possibility — CPF Auto-Submit (Not Now)

At month 6, the shadow agent might suggest:

```
"You've been downloading the CPF file and uploading it manually for
6 months. Arbor can submit directly to CPF Board through the MCP
integration. Want to try it?

This requires: connecting your CPF Board account (CorpPass login).
You'd still approve the submission before it goes through."
```

This is the MCP integration layer (arbor-government server). If Ahmad accepts, the Payroll Agent's envelope would be widened to include external communication to `cpf_portal` — currently BLOCKED, would move to HELD (Ahmad approves, agent submits).

This is a future capability. The user flow documents its possibility but does not assume it is activated.

---

## Trust Progression Summary

| Month      | Ahmad's Involvement        | Agent Autonomy                             | Trust Level                           |
| ---------- | -------------------------- | ------------------------------------------ | ------------------------------------- |
| 0 (before) | Does everything            | None                                       | N/A                                   |
| 1          | Reviews every line item    | Calculate on demand, wait for approval     | Low — "Let me check your work"        |
| 2          | Reviews summary only       | Calculate on demand, wait for approval     | Growing — "I'll glance at it"         |
| 3          | Approves from summary      | Calculate automatically, wait for approval | Medium — "I trust your math"          |
| 4+         | Approves from notification | Calculate and prep automatically           | High — "Just show me the total"       |
| 6+ (maybe) | Approves submission        | Full cycle including CPF submission        | Very high — "Handle it, I'll confirm" |

At no point does the agent transfer money or submit to government without Ahmad's explicit approval. The gradient shifts only affect preparation and calculation — the authority boundary (approve/submit) never moves unless Ahmad explicitly agrees.

---

## Failure Points and Mitigations

| Failure                                              | Likelihood | Impact | Mitigation                                                                                   |
| ---------------------------------------------------- | ---------- | ------ | -------------------------------------------------------------------------------------------- |
| Payroll calculation error (wrong OT, wrong CPF rate) | Medium     | High   | First 3 months are HELD for detailed review; errors caught early, corrections fed back       |
| Ahmad approves without reviewing                     | Low        | High   | Agent highlights variances (>5% change) as flags; cannot silence variance flags              |
| Salary data not entered for new employee             | Medium     | Medium | Agent detects missing salary at calculation time, holds payroll until resolved               |
| CPF rate change (government updates rates)           | Annual     | High   | Agent pulls from statutory rate tables updated by Terrene Foundation; flags if rates changed |
| Month-end timing (24th falls on weekend)             | Monthly    | Low    | Agent adjusts to previous business day; configurable in company settings                     |
| Bank GIRO file format changes                        | Rare       | High   | File format is standardized by ABS; agent uses current format from template library          |
