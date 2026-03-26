# User Flow 04: Compliance Crisis

## Month 4: Foreign Worker Permit Expiry

**Persona**: Ahmad, same logistics boss. Arbor has been running for 4 months. HR Agent handles leave and attendance. Payroll Agent handles monthly payroll. Ahmad's daily involvement is down to ~5 minutes per day (reviewing morning briefing, approving held actions).

**The crisis**: Raju Kumar is a Work Permit holder from India. His work permit expires on 15 April 2026. Ahmad has not thought about this because he has 11 other things on his mind.

**PACT context**: The Compliance Agent monitors statutory deadlines as part of the HR Agent's envelope. It has access to Employee records (CONFIDENTIAL) including work_pass_number and work_pass_expiry. External communication to MOM (Ministry of Manpower) is HELD for boss — the agent cannot submit anything to government without Ahmad's approval.

---

## Step 1: Detection (Day 0 — 30 Days Before Expiry)

**What the Compliance Agent detects:**

```
Internal evaluation:
- Employee: Raju Kumar (D1-R1-D2-R1-R2)
- Work permit: WP-1234567
- Expiry: 15 April 2026
- Today: 16 March 2026
- Days remaining: 30
- Threshold: 45-day warning (missed), 30-day warning (triggered now)
- Status: URGENT — 30 days is the minimum recommended lead time
  for WP renewal applications
```

The agent checks its envelope:

- Operational: monitoring work pass expiry — AUTO-APPROVED (passive monitoring)
- Communication to MOM: HELD for boss (external regulatory submission)
- Data access: Employee.work_pass_expiry — CONFIDENTIAL, agent has access via HR role

**Why 30 days matters:** MOM work permit renewal processing takes 1-3 weeks. Starting at 30 days gives just enough time, but no margin for delays. The ideal window is 45-60 days.

---

## Step 2: First Notification to Boss

Ahmad receives a push notification at 8:15 AM:

```
Arbor: Raju Kumar's work permit expires in 30 days (15 April).
Action needed to keep him working legally.
```

Ahmad taps the notification.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  [!] Work Permit Expiring — Action Needed                 |
|                                                           |
|  Employee: Raju Kumar                                     |
|  Position: Warehouse Worker (Operations)                  |
|  Work Permit: WP-1234567                                  |
|  Expiry: 15 April 2026 (30 days from now)                 |
|                                                           |
|  WHAT HAPPENS IF NOT RENEWED                              |
|                                                           |
|  After 15 April, Raju cannot legally work in Singapore.   |
|  Employing a worker with an expired permit is an offence  |
|  under the Employment of Foreign Manpower Act (EFMA):     |
|  - Fine up to $30,000                                     |
|  - Imprisonment up to 12 months                           |
|  - Debarment from hiring foreign workers                  |
|                                                           |
|  WHAT I'VE PREPARED                                       |
|                                                           |
|  I've drafted the renewal application with the            |
|  information I have on file:                              |
|                                                           |
|  - Raju's personal details (from employee record)         |
|  - Your company UEN and WP quota status                   |
|  - Employment details (salary, start date, job scope)     |
|                                                           |
|  [!] Some information may need updating:                  |
|  - Raju's passport expiry (not on file)                   |
|  - Current residential address                            |
|  - Medical examination status                             |
|                                                           |
|  NEXT STEPS                                               |
|                                                           |
|  1. Review the draft application                          |
|  2. Fill in the missing information                       |
|  3. Approve — I'll prepare the submission package         |
|  4. You submit via MOM EPOL/WPOL portal                   |
|                                                           |
|  [Review Application]    [Remind Me Tomorrow]             |
|  [I'll Handle This Myself]                                |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Oh no, I completely forgot about Raju's permit. 30 days is tight. Let me look at what it prepared."

**What Ahmad does:** Taps "Review Application."

---

## Step 3: Application Review

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Work Permit Renewal — Draft Application                  |
|                                                           |
|  EMPLOYER INFORMATION                                     |
|  Company: Ahmad Logistics Pte Ltd                         |
|  UEN: 201912345D                                          |
|  WP Quota: 7 of 10 used (3 remaining)                    |
|  Sector: Logistics & Transport                            |
|                                                           |
|  WORKER INFORMATION                                       |
|  Name: Raju Kumar                                         |
|  FIN: G1234567N                                           |
|  Nationality: Indian                                      |
|  Date of Birth: 15 Jun 1990                               |
|  Current WP: WP-1234567 (expires 15 Apr 2026)            |
|                                                           |
|  EMPLOYMENT DETAILS                                       |
|  Job title: Warehouse Worker                              |
|  Monthly salary: $2,400                                   |
|  Start date: 1 Apr 2023                                   |
|                                                           |
|  MISSING INFORMATION                                      |
|  [!] Passport number: [_________________]                 |
|  [!] Passport expiry:  [_________________]                |
|  [!] Current address:  [_________________]                |
|  [!] Last medical exam: [_________________]               |
|      (required within 6 months of renewal)                |
|                                                           |
|  ESTIMATED COSTS                                          |
|  WP levy: $300/month (current rate for WP holder)         |
|  Security bond: $5,000 (non-Malaysian worker)             |
|  Medical exam: ~$50-80 (if needed)                        |
|                                                           |
|  [Save & Complete Later]    [Submit for Preparation]      |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "I need to ask Raju for his passport details and check when his last medical was. Let me save this and come back."

**What Ahmad does:** Taps "Save & Complete Later."

**What happens behind the scenes:**

- Draft application saved (status: "incomplete")
- PactAuditEvent: compliance action acknowledged by owner, pending completion
- Agent schedules follow-up reminders
- EATP audit anchor: work permit renewal initiated, owner reviewing

---

## Step 4: Follow-Up Reminder (Day 3)

Ahmad has not completed the application. Three days later:

**What Ahmad sees in his morning briefing:**

```
+----------------------------------------------------------+
|  Good morning, Ahmad                     Thu 19 Mar 2026  |
|                                                           |
|  [!] URGENT — Raju's work permit                          |
|                                                           |
|  The renewal application still needs passport details     |
|  and medical exam status. 27 days remaining.              |
|                                                           |
|  Processing typically takes 1-3 weeks, so the             |
|  application needs to be submitted within the             |
|  next 2 weeks to be safe.                                 |
|                                                           |
|  [Complete Application]    [Ask Raju Directly]            |
+----------------------------------------------------------+
```

**What Ahmad does:** Taps "Ask Raju Directly."

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Send a message to Raju about his renewal?                |
|                                                           |
|  I can send Raju a notification through Arbor asking      |
|  him to update his passport details and medical exam      |
|  status. He'll be able to fill in the information         |
|  himself through his Arbor profile.                       |
|                                                           |
|  Draft message:                                           |
|                                                           |
|  "Hi Raju, we need to renew your work permit before       |
|   15 April. Please update your passport number,           |
|   passport expiry date, current address, and last         |
|   medical exam date in your Arbor profile. If you         |
|   need a medical exam, please let Ahmad know."            |
|                                                           |
|  [Send to Raju]    [Edit Message]    [Cancel]             |
+----------------------------------------------------------+
```

**PACT evaluation:**

- Communication: internal message to Raju — AUTO-APPROVED (internal channel)
- The agent drafted the message but Ahmad approves sending it (this is a PACE "propose" action — Ahmad confirms before it goes)

**What Ahmad does:** Taps "Send to Raju."

**What Raju sees (Arbor notification):**

```
+----------------------------------------------------------+
|  Action needed: Work permit renewal                       |
|                                                           |
|  Your work permit expires on 15 April 2026.               |
|  Please update these details in your profile:             |
|                                                           |
|  - Passport number                                        |
|  - Passport expiry date                                   |
|  - Current address                                        |
|  - Last medical exam date                                 |
|                                                           |
|  [Update My Profile]                                      |
+----------------------------------------------------------+
```

Raju updates his profile. The compliance agent detects the profile update and auto-fills the draft application.

---

## Step 5: Application Complete (Day 5)

Raju has filled in his details. The agent notifies Ahmad.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  [checkmark] Raju's renewal application is complete       |
|                                                           |
|  All required information has been filled in:             |
|  - Passport: M1234567 (expires Dec 2028)                  |
|  - Address: Blk 123 Tuas South Ave 2 #05-678             |
|  - Last medical: 15 Sep 2025 (valid — within 6 months)   |
|                                                           |
|  The application package is ready:                        |
|  1. Renewal form (pre-filled)                             |
|  2. Supporting documents checklist                        |
|  3. Levy payment reminder                                 |
|                                                           |
|  You need to submit this through MOM's WPOL portal        |
|  using your CorpPass login.                               |
|                                                           |
|  [Download Application Package]                           |
|  [Show Me How to Submit]                                  |
+----------------------------------------------------------+
```

**PACT evaluation:**

- Generating the application package: AUTO-APPROVED (internal document generation)
- Submitting to MOM: HELD for boss (external regulatory submission, BLOCKED in agent's envelope)
- The agent cannot submit. It prepares. Ahmad submits.

**What Ahmad does:** Taps "Download Application Package." Then taps "Show Me How to Submit."

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  How to Submit Raju's Work Permit Renewal                 |
|                                                           |
|  Step 1: Go to mom.gov.sg/eservices                       |
|  Step 2: Log in with CorpPass                             |
|  Step 3: Select "Work Permit Renewal"                     |
|  Step 4: Upload the application package I prepared        |
|  Step 5: Pay the renewal fee ($35)                        |
|  Step 6: Save the acknowledgement number                  |
|                                                           |
|  After you submit, enter the acknowledgement number       |
|  here so I can track the processing status:               |
|                                                           |
|  MOM Acknowledgement: [_________________]                 |
|                                                           |
|  [I've Submitted]     [I'll Do It Later]                  |
+----------------------------------------------------------+
```

**What Ahmad does:** Opens a new tab, goes to MOM portal, logs in with CorpPass, submits the renewal, gets the acknowledgement number, comes back to Arbor, enters it.

---

## Step 6: Tracking (Day 5-25)

The agent now monitors the renewal status.

**What Ahmad sees in subsequent morning briefings:**

Day 7:

```
Raju's WP renewal: Submitted (Day 2 of processing). Typically takes 1-3 weeks.
```

Day 14:

```
Raju's WP renewal: Processing (Day 9). No issues flagged by MOM.
23 days remaining on current permit.
```

Day 21:

```
Raju's WP renewal: Approved! New permit valid until 14 April 2028.
Collection details will be sent to your email.
```

If the renewal had NOT been approved by day 21:

```
+----------------------------------------------------------+
|  [!] Raju's WP renewal — Still processing                 |
|                                                           |
|  It's been 16 days since submission. Processing is        |
|  taking longer than usual. The current permit expires      |
|  in 9 days.                                               |
|                                                           |
|  Options:                                                 |
|  - Call MOM hotline: 6438 5122 (quote ref: WP-R-2026...)  |
|  - Visit MOM Services Centre at Riverwalk                  |
|  - Raju can continue working while the renewal is          |
|    being processed (he has a valid renewal application)    |
|                                                           |
|  [Set Reminder to Call Tomorrow]                          |
+----------------------------------------------------------+
```

---

## Step 7: Escalation Pattern (If Boss Ignores)

What if Ahmad never taps "Review Application" and ignores every notification?

**Day 0 (30 days before expiry):** Standard notification — appears in briefing and as push notification. Priority: medium.

**Day 3 (27 days):** Follow-up in briefing. Priority: elevated. Tone: informational.

```
"Raju's work permit renewal — you haven't reviewed the draft
application yet. 27 days remaining."
```

**Day 7 (23 days):** Nudge on every page Ahmad visits. Priority: high. Tone: urgency.

```
"Raju's work permit expires in 23 days. The renewal application
needs your attention. Processing takes 1-3 weeks, so time is
getting tight."
```

**Day 14 (16 days):** Daily dedicated notification. Priority: critical. Tone: consequences stated.

```
+----------------------------------------------------------+
|  [!!] CRITICAL — Raju's Work Permit                       |
|                                                           |
|  16 days until expiry. MOM processing takes up to         |
|  3 weeks. If you submit today, the permit may expire      |
|  before the renewal is processed.                         |
|                                                           |
|  If Raju's permit expires:                                |
|  - He cannot work (you must send him home or he waits)    |
|  - Employing an expired-permit worker: up to $30,000      |
|    fine and 12 months imprisonment                        |
|  - Your company may be debarred from hiring foreign       |
|    workers                                                |
|                                                           |
|  [Complete Application NOW]                               |
+----------------------------------------------------------+
```

**Day 21 (9 days):** Emergency escalation. The agent sends an email to Ahmad's registered email address (not just in-app notification).

```
Subject: URGENT — Raju Kumar's work permit expires in 9 days

Ahmad,

Raju's work permit (WP-1234567) expires on 15 April 2026.
This is 9 days away. I've been reminding you since 16 March.

If the permit expires without a renewal application:
- Raju cannot legally work
- You may face fines up to $30,000

The renewal application is ready in Arbor. It takes 5 minutes
to review and submit through MOM's portal.

Please log in to Arbor to complete this: [link]

— Arbor Compliance Agent
```

**PACT evaluation for email:**

- Communication: email to Ahmad (internal, to the company owner) — AUTO-APPROVED
- The agent does NOT email MOM directly (external regulatory — BLOCKED)
- The agent does NOT email Raju about the risk (that is Ahmad's decision)

**Day 28 (2 days):** Final warning. Daily reminders with countdown.

```
"Raju's permit expires in 2 DAYS. If you cannot complete the
renewal, you should plan for Raju's last working day to avoid
legal risk."
```

**Day 30+ (expired):** If the permit expires without renewal:

```
+----------------------------------------------------------+
|  [!!!] EXPIRED — Raju's Work Permit                       |
|                                                           |
|  Raju Kumar's work permit expired on 15 April 2026.       |
|                                                           |
|  IMMEDIATE ACTIONS REQUIRED:                              |
|                                                           |
|  1. Raju CANNOT work today. Do not assign him to any      |
|     shift or task until his permit is renewed.            |
|                                                           |
|  2. If Raju has already been assigned to today's shift,   |
|     you need to reassign his tasks to another worker.     |
|                                                           |
|  3. To renew an expired permit, you must:                 |
|     - Apply through MOM within 30 days of expiry          |
|     - Pay a late renewal fee                              |
|     - Raju may need to leave Singapore and re-enter       |
|                                                           |
|  I've removed Raju from all future shift schedules        |
|  until his permit status is resolved.                     |
|                                                           |
|  [Start Emergency Renewal]    [Contact MOM Hotline]       |
+----------------------------------------------------------+
```

**PACT evaluation for removing Raju from shifts:**

- Operational: modifying shift assignments — within HR Agent's envelope
- Gradient: FLAGGED (unusual action — agent explains why)
- Ahmad is notified but the agent acts because this is a legal compliance requirement, not a judgment call. Continuing to schedule an expired-permit worker is an offence.

**Key design point:** The agent escalates in urgency but never in authority. It cannot submit the renewal itself. It cannot contact MOM. It can only prepare, remind, and eventually remove the worker from active schedules to prevent legal violation. The authority boundary (external government submission) never moves without Ahmad's explicit decision.

---

## Step 8: EATP Audit Trail

Every step of this compliance workflow creates an immutable audit record:

| Day | Event                        | EATP Record Type | Content                            |
| --- | ---------------------------- | ---------------- | ---------------------------------- |
| 0   | Agent detects WP expiry      | Audit Anchor     | Detection event, 30-day threshold  |
| 0   | Ahmad notified               | Audit Anchor     | Notification sent, timestamp       |
| 3   | Ahmad reminded (no action)   | Audit Anchor     | Reminder sent, no response         |
| 5   | Raju updates profile         | Audit Anchor     | Employee self-service data update  |
| 5   | Application package prepared | Audit Anchor     | Document generated                 |
| 5   | Ahmad downloads package      | Audit Anchor     | Owner retrieves documents          |
| 5   | Ahmad submits to MOM         | Audit Anchor     | Owner confirms external submission |
| 21  | MOM approves renewal         | Audit Anchor     | Renewal confirmed                  |

If an MOM inspector asks "When did you apply for renewal? Who prepared it? When were you notified?" — every answer is in the EATP chain, cryptographically signed and tamper-evident.

---

## Step 9: Multi-Worker Scenario

Ahmad has 3 foreign workers (Raju, Ali, Faizal). The compliance agent tracks all permits.

**What Ahmad sees on the compliance dashboard:**

```
+----------------------------------------------------------+
|  Foreign Worker Compliance                                |
|                                                           |
|  +---+------------------+--------+------------+---------+ |
|  | # | Worker           | Permit | Expiry     | Status  | |
|  +---+------------------+--------+------------+---------+ |
|  | 1 | Raju Kumar       | WP     | 15 Apr 26  | [!] 30d | |
|  | 2 | Ali bin Osman    | WP     | 22 Aug 26  | OK 159d | |
|  | 3 | Faizal           | WP     | 10 Nov 26  | OK 239d | |
|  +---+------------------+--------+------------+---------+ |
|                                                           |
|  Monthly levy summary:                                    |
|  3 WP holders x $300/month = $900/month                   |
|  (included in payroll as employer cost)                    |
|                                                           |
|  Upcoming:                                                |
|  - Raju: Renewal needed NOW (30 days)                     |
|  - Ali: Renewal notification in ~3 months                 |
|  - Faizal: Renewal notification in ~6 months              |
+----------------------------------------------------------+
```

The agent creates a rolling compliance calendar. Each permit is tracked with its own escalation timeline. Ahmad does not need to remember any dates — the system tracks them all.

---

## Failure Points and Mitigations

| Failure                                       | Likelihood | Impact   | Mitigation                                                                                                                                                                                                       |
| --------------------------------------------- | ---------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ahmad ignores all notifications until expiry  | Medium     | Critical | Escalation ladder: nudge -> dedicated notification -> email -> shift removal. Cannot prevent Ahmad from ignoring, but can prevent the company from committing an offence (removing worker from active schedule). |
| Employee record missing work_pass_expiry date | Medium     | High     | On employee import, if immigration_status is "work_permit" or "s_pass" but work_pass_expiry is blank, agent creates a held action: "Raju is a WP holder but has no permit expiry on file. Please add this."      |
| MOM changes renewal process or portal         | Rare       | Medium   | Agent provides guidance links to MOM website. Specific portal steps are marked as "verify current process on mom.gov.sg" rather than guaranteed instructions.                                                    |
| Renewal rejected by MOM                       | Low        | Critical | Agent helps Ahmad understand rejection reasons and prepare an appeal or alternative (repatriation planning). This is a held action — agent provides options, Ahmad decides.                                      |
| Multiple permits expiring in the same month   | Low        | High     | Agent staggers notifications and tracks each independently. Combined dashboard shows all pending actions.                                                                                                        |
| Ahmad's CorpPass expired or unavailable       | Low        | High     | Agent cannot detect this (CorpPass is external). If Ahmad reports submission failure, agent suggests CorpPass renewal steps and provides MOM hotline as fallback.                                                |
