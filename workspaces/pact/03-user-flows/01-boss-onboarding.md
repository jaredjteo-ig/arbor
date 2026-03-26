# User Flow 01: Boss Onboarding

## Ahmad Registers and Deploys His First Agent

**Persona**: Ahmad, 45, owns a logistics SME in Tuas. 12 employees (1 admin, 2 supervisors, 9 warehouse/delivery staff). Does HR himself on spreadsheets. Heard about Arbor from a hawker center conversation with another boss.

**Entry point**: `arbor.terrene.dev` on his phone during lunch break.

**Goal**: Get his HR off spreadsheets. Does not know what an "agent" is. Does not care about governance. Wants something that works.

---

## Step 1: Landing Page

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  [Arbor logo]                              [Sign Up Free] |
|                                                           |
|   Your AI HR Department                                   |
|   for Singapore SMEs                                      |
|                                                           |
|   Payroll. Leave. Compliance. Handled.                    |
|                                                           |
|   Join 200+ Singapore SMEs who replaced their             |
|   HR spreadsheets with Arbor.                             |
|                                                           |
|        [Get Started - It's Free]                          |
|                                                           |
|   "I used to spend every Saturday doing payroll.          |
|    Now Arbor does it in 5 minutes." - Jenny, F&B owner    |
|                                                           |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Free? OK, let me try."

**What Ahmad does:** Taps "Get Started."

**What PACT does:** Nothing yet.

---

## Step 2: Registration

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Create Your Account                                      |
|                                                           |
|  Your name:      [Ahmad bin Hassan              ]         |
|  Email:          [ahmad@ahmadlogistics.sg        ]         |
|  Password:       [*************                 ]         |
|  Mobile:         [+65 9XXX XXXX                 ]         |
|                                                           |
|        [Create Account]                                   |
|                                                           |
|  Already have an account? Sign in                         |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Simple enough. Same as everything else."

**What Ahmad does:** Fills in details, taps "Create Account."

**What happens behind the scenes:**

- User record created (role: `owner`)
- Email verification sent (single-use token, 7-day expiry)
- No company yet. No PACT yet.

---

## Step 3: Company Setup (3 questions)

Ahmad verifies his email and lands on the company setup screen. This is intentionally short. Three questions, not a form.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Let's set up your company                                |
|                                                           |
|  Company name:                                            |
|  [Ahmad Logistics Pte Ltd                    ]            |
|                                                           |
|  UEN (optional):                                          |
|  [201912345D                                 ]            |
|  (We use this for CPF and IRAS filing later)              |
|                                                           |
|  How many employees do you have?                          |
|                                                           |
|    ( ) Just me                                            |
|    (o) 2-10                                               |
|    ( ) 11-25                                              |
|    ( ) 26-50                                              |
|    ( ) More than 50                                       |
|                                                           |
|        [Set Up Company]                                   |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "UEN? OK, I'll put it in. 12 employees, that's 11-25."

**What Ahmad does:** Fills in name, UEN, selects "11-25", taps "Set Up Company."

**What happens behind the scenes:**

- Company record created
- `seed_company_defaults(company_id)` runs:
  - 11 statutory leave types (annual, sick, maternity, paternity, childcare, etc.)
  - 6 claim categories (transport, medical, meals, etc.)
  - Attendance settings (default 44-hour work week)
  - Default policies (PDPA, leave, claims)
  - Pay items, pay schemes, cost centres
- Ahmad's User linked to Company (role: `owner`)
- Ahmad's Employee record created (department: "Management", designation: "Director")
- PACT-lite tree initialized: just BOD (vacant) + D1 (Company) + D1-R1 (Ahmad, Director)
- Template envelope `tmpl_owner` assigned to Ahmad's role

Ahmad sees none of this. The page transitions smoothly.

---

## Step 4: Add Your Team

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  [checkmark] Company created!                             |
|                                                           |
|  Now let's add your team. You can:                        |
|                                                           |
|  +-------------------+    +-------------------+           |
|  |  Upload a File    |    |  Add One by One   |           |
|  |                   |    |                   |           |
|  |  CSV or Excel     |    |  Enter details    |           |
|  |  with employee    |    |  for each person  |           |
|  |  details          |    |                   |           |
|  +-------------------+    +-------------------+           |
|                                                           |
|  Or skip this for now — you can add people anytime.       |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "I have a spreadsheet with everyone's details. Let me upload that."

**What Ahmad does:** Taps "Upload a File."

### Step 4a: CSV Upload

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Upload Employee List                                     |
|                                                           |
|  Drop your file here or [Browse]                          |
|                                                           |
|  Your file should have these columns:                     |
|  Name, Email, Department, Job Title, Start Date           |
|                                                           |
|  Optional columns (can add later):                        |
|  NRIC, Phone, Salary, Bank Account                        |
|                                                           |
|  [Download sample CSV]                                    |
+----------------------------------------------------------+
```

Ahmad uploads `staff_list.xlsx` with 11 rows:

```
Name              Department    Job Title           Start Date    Reports To
Mei Ling (Ah Mei) Admin         Admin Manager       2020-03-15    Ahmad
John Tan          Operations    Warehouse Supv      2021-06-01    Ahmad
Sarah Lim         Operations    Warehouse Supv      2022-01-10    Ahmad
Raju Kumar        Operations    Warehouse Worker    2023-04-01    John Tan
Ali bin Osman     Operations    Warehouse Worker    2023-06-15    John Tan
Priya Devi        Operations    Delivery Driver     2022-09-01    Sarah Lim
Wei Ming          Operations    Delivery Driver     2023-11-01    Sarah Lim
Faizal            Operations    Warehouse Worker    2024-01-15    John Tan
David Lee         Operations    Forklift Operator   2024-03-01    John Tan
Siti Aminah       Admin         Admin Assistant     2024-06-01    Mei Ling
Kumar S           Operations    Delivery Driver     2024-08-01    Sarah Lim
```

### Step 4b: Import Preview

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  I found 11 employees in your file                        |
|                                                           |
|  [checkmark] Mei Ling — Admin Manager (Admin)             |
|  [checkmark] John Tan — Warehouse Supervisor (Operations) |
|  [checkmark] Sarah Lim — Warehouse Supervisor (Operations)|
|  [checkmark] Raju Kumar — Warehouse Worker (Operations)   |
|  [checkmark] Ali bin Osman — Warehouse Worker (Operations)|
|  [checkmark] Priya Devi — Delivery Driver (Operations)    |
|  [checkmark] Wei Ming — Delivery Driver (Operations)      |
|  [checkmark] Faizal — Warehouse Worker (Operations)       |
|  [checkmark] David Lee — Forklift Operator (Operations)   |
|  [checkmark] Siti Aminah — Admin Assistant (Admin)        |
|  [checkmark] Kumar S — Delivery Driver (Operations)       |
|                                                           |
|  2 departments found: Admin (2 people), Operations (9)    |
|  Reporting lines detected from "Reports To" column        |
|                                                           |
|       [Import All]    [Review One by One]                 |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Looks right. 11 people, two departments."

**What Ahmad does:** Taps "Import All."

**What happens behind the scenes:**

- 11 Employee records created with department, designation, reporting_manager_id
- User records created for each (role: `employee`, invitation pending)
- PACT `build_pact_tree(company_id)` runs:

```
BOD (vacant)
D1 (Ahmad Logistics Pte Ltd)
  D1-R1 (Ahmad — Director) [tmpl_owner]
    D1-R1-D1 (Admin)
      D1-R1-D1-R1 (Mei Ling — Admin Manager) [tmpl_hr_manager]
        D1-R1-D1-R1-R2 (Siti Aminah — Admin Assistant) [tmpl_employee_office]
    D1-R1-D2 (Operations)
      D1-R1-D2-R1 (John Tan — Warehouse Supervisor) [tmpl_supervisor]
        D1-R1-D2-R1-R2 (Raju Kumar — Worker) [tmpl_employee_field]
        D1-R1-D2-R1-R3 (Ali bin Osman — Worker) [tmpl_employee_field]
        D1-R1-D2-R1-R4 (Faizal — Worker) [tmpl_employee_field]
        D1-R1-D2-R1-R5 (David Lee — Forklift Operator) [tmpl_employee_field]
      D1-R1-D2-R2 (Sarah Lim — Warehouse Supervisor) [tmpl_supervisor]
        D1-R1-D2-R2-R2 (Priya Devi — Driver) [tmpl_employee_field]
        D1-R1-D2-R2-R3 (Wei Ming — Driver) [tmpl_employee_field]
        D1-R1-D2-R2-R4 (Kumar S — Driver) [tmpl_employee_field]
```

- Template envelopes assigned by designation matching
- Clearances auto-granted: Ahmad gets CONFIDENTIAL, Mei Ling gets CONFIDENTIAL (hr_manager role), everyone else gets RESTRICTED
- Verification gradient active with template defaults
- Shadow agent observation begins (silent)

Ahmad sees none of the PACT computation.

---

## Step 5: Your Team Structure

This is the "aha" moment. Ahmad sees his company for the first time as a visual structure.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Your team is set up!                                     |
|                                                           |
|  Here's how your company looks:                           |
|                                                           |
|                    [Ahmad]                                 |
|                   Director                                |
|                   /       \                               |
|           [Admin]          [Operations]                   |
|              |              /          \                   |
|         [Mei Ling]    [John Tan]    [Sarah Lim]          |
|        Admin Mgr     Warehouse Supv  Warehouse Supv      |
|            |           / | | \          / | \             |
|       [Siti]      [Raju][Ali]       [Priya][Wei]         |
|                   [Faizal][David]   [Kumar S]            |
|                                                           |
|  2 departments, 3 team leads, 11 team members             |
|                                                           |
|  Does this look right?                                    |
|                                                           |
|  [Yes, looks good]    [I need to make changes]            |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Huh, that's my company. That's right, John and Sarah each have their own teams. Mei Ling has Siti under her."

**What Ahmad does:** Taps "Yes, looks good."

**What happens behind the scenes:**

- PactNode records marked `is_inferred: False` (owner-confirmed)
- PactAuditEvent recorded: tree confirmed by owner
- EATP delegation record created (organization structure snapshot)

**What Ahmad thinks next:** "OK, so what does this thing actually do for me?"

---

## Step 6: First Agent Offer

This is the critical moment. Ahmad has a team structure. He has no one doing HR. Arbor knows this because there is no employee with an HR-specific designation in a company that selected "11-25" employees. This is the moment Arbor offers to fill the gap.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  One more thing                                           |
|                                                           |
|  Right now, nobody in your company is dedicated to HR.    |
|  Mei Ling handles admin, and you probably handle the      |
|  rest yourself — leave approvals, payroll, compliance.    |
|                                                           |
|  Arbor can take over routine HR tasks for you:            |
|                                                           |
|  +------------------------------------------------------+ |
|  |  HR Agent                                   [Start]  | |
|  |                                                      | |
|  |  What it handles:                                    | |
|  |  - Approve routine leave requests automatically      | |
|  |  - Track attendance and flag issues                  | |
|  |  - Answer employee HR questions (policies,           | |
|  |    leave balances, payslips)                         | |
|  |  - Send you a morning summary of what's happening    | |
|  |                                                      | |
|  |  What it does NOT do (you stay in control):          | |
|  |  - Any financial decisions (payroll, bonuses)        | |
|  |  - Hiring or firing anyone                           | |
|  |  - Contacting government agencies                    | |
|  |  - Anything unusual — it asks you first              | |
|  +------------------------------------------------------+ |
|                                                           |
|  This is like hiring a reliable HR assistant who          |
|  handles the routine stuff and checks with you on         |
|  anything important.                                      |
|                                                           |
|  You can change what it's allowed to do at any time.      |
|                                                           |
|       [Start HR Agent]       [Maybe Later]                |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "So it does the boring stuff and asks me when it's not sure? OK, that sounds like what I need."

**What Ahmad does:** Taps "Start HR Agent."

**What happens behind the scenes:**

- The "HR Agent" is not a new entity. It is the existing shadow agent with Mei Ling's template envelope (`tmpl_hr_manager`) assigned to the HR Agent role in the PACT tree
- A new PactNode is created: `D1-R1-D1-R1-T2` (People Operations Team) with an agent-filled R node underneath
- The agent's envelope:
  - Financial: approve claims up to $500
  - Operational: manage leave, manage attendance, answer HR questions, generate reports
  - Data Access: CONFIDENTIAL for employee records (with PDPA logging)
  - Communication: internal only (no government submissions)
  - Temporal: business hours, with emergency escalation 24/7
- Verification gradient set to conservative defaults:
  - Auto-approved: view own data, check leave balance, clock in/out
  - Flagged: leave during peak periods, claims above monthly average
  - Held: anything the agent is unsure about, anything near envelope boundary
  - Blocked: payroll, terminations, government submissions, salary changes
- EATP delegation record created: Ahmad (D1-R1) delegates HR operations to the HR Agent

Ahmad does not see any of this. He sees:

```
+----------------------------------------------------------+
|  [checkmark] HR Agent is active                           |
|                                                           |
|  It will start by watching how things work for a few      |
|  days, then gradually take over routine tasks.            |
|                                                           |
|  Tomorrow morning, you'll get your first daily summary.   |
|                                                           |
|  In the meantime, invite your team to Arbor so they       |
|  can apply for leave and check their schedules:           |
|                                                           |
|       [Invite Team by Email]                              |
|       [Share Invite Link]                                 |
|       [Go to Dashboard]                                   |
+----------------------------------------------------------+
```

**What Ahmad does:** Taps "Share Invite Link" (easier than typing 11 emails), copies the link, drops it in the company WhatsApp group.

---

## Step 7: First Morning Briefing (Next Day)

Ahmad opens Arbor the next morning. The shadow agent's briefing service has assembled his first daily summary.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Good morning, Ahmad                     Tue 22 Mar 2026  |
|                                                           |
|  YOUR COMPANY TODAY                                       |
|                                                           |
|  Team: 8 of 11 have joined Arbor                         |
|  (Raju, Faizal, Kumar S haven't accepted their invite)   |
|                                                           |
|  Pending for you:                                         |
|  - 0 leave requests                                       |
|  - 0 claims                                               |
|                                                           |
|  HR Agent status:                                         |
|  Observing — learning how your team works. I'll start     |
|  handling routine tasks after a few days.                  |
|                                                           |
|  TIP: Employees can now apply for leave, check their      |
|  balances, and view company policies through Arbor.       |
|                                                           |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "OK, three people haven't joined yet. I'll remind them."

**What Ahmad does:** Forwards the invite link to Raju, Faizal, and Kumar S directly on WhatsApp.

---

## Step 8: First Held Action (Day 5)

Five days in. Sarah has submitted a leave request through Arbor. The HR Agent evaluates it.

**Agent's internal evaluation:**

- Sarah requests 3 days off (Wednesday to Friday next week)
- Sarah has 14 days annual leave remaining
- 3 days is within policy
- BUT: checking attendance patterns, next week has 2 other people already on leave from Sarah's team
- HR Agent assessment: this could cause understaffing during a busy period
- Gradient evaluation: HELD (near boundary — team coverage concern)

Ahmad gets a push notification on his phone:

```
Arbor: Sarah Lim wants 3 days leave next week. I need your input.
```

Ahmad taps the notification.

**What Ahmad sees:**

```
+----------------------------------------------------------+
|  Leave Request — Needs Your Input                         |
|                                                           |
|  Sarah Lim (Warehouse Supervisor)                         |
|  Requesting: Wed 27 Mar — Fri 29 Mar (3 days annual)     |
|                                                           |
|  Her balance: 14 days remaining (plenty)                  |
|                                                           |
|  Why I'm asking you:                                      |
|  Priya and Wei Ming are already off that week.            |
|  If Sarah is also away, her delivery team will have       |
|  only Kumar S available for 3 days.                       |
|                                                           |
|  Options:                                                 |
|                                                           |
|  [Approve Anyway]  [Suggest Different Dates]  [Decline]   |
|                                                           |
|  If you approve, I'll notify Sarah immediately.           |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "Oh, I didn't realize Priya and Wei Ming are off too. That's only one driver for three days. Better check with Sarah."

**What Ahmad does:** Taps "Suggest Different Dates."

**What Ahmad sees next:**

```
+----------------------------------------------------------+
|  Suggest alternative dates for Sarah                      |
|                                                           |
|  The following weeks have better coverage:                 |
|                                                           |
|  [o] Mon 31 Mar — Wed 2 Apr (full team available)        |
|  [ ] Mon 7 Apr — Wed 9 Apr (full team available)         |
|  [ ] Other dates: [________________]                      |
|                                                           |
|  Add a note (optional):                                   |
|  [Too many people off that week. Can you shift    ]       |
|  [to the following week?                          ]       |
|                                                           |
|       [Send to Sarah]     [Cancel]                        |
+----------------------------------------------------------+
```

Ahmad picks the first option, adds the note, taps "Send to Sarah."

**What happens behind the scenes:**

- Leave application status set to "pending_reschedule"
- Sarah gets notification: "Ahmad suggested alternative dates for your leave. Mon 31 Mar - Wed 2 Apr. Note: Too many people off that week."
- PACT observation recorded: held action, boss responded with alternative dates
- PactAuditEvent: leave hold resolved with alternative suggestion
- This is the first data point in the "how does Ahmad handle leave decisions" pattern

**What builds trust:** Ahmad saw that the agent caught something he would have missed (team overlap). The agent did not make the decision for him. It showed him the information and let him decide. The next time the agent flags something, Ahmad will take it more seriously.

---

## Step 9: Agent Learns the Pattern (Week 2-4)

Over the next three weeks, 8 more leave requests come in:

| Request | Employee | Days              | Team Coverage      | Agent Decision     | Ahmad's Response                   |
| ------- | -------- | ----------------- | ------------------ | ------------------ | ---------------------------------- |
| #2      | Raju     | 1 day (MC)        | Full coverage      | Auto-approved      | (not involved)                     |
| #3      | Ali      | 2 days            | Full coverage      | Auto-approved      | (not involved)                     |
| #4      | David    | 1 day             | Full coverage      | Auto-approved      | (not involved)                     |
| #5      | Siti     | 3 days            | Mei Ling available | Auto-approved      | (not involved)                     |
| #6      | Priya    | 2 days            | Kumar S covering   | Flagged (marginal) | Notification: "Approved, just FYI" |
| #7      | Wei Ming | 1 day (emergency) | Low coverage       | Held               | Ahmad approves in 2 minutes        |
| #8      | Faizal   | 5 days            | OK coverage        | Flagged (5+ days)  | Notification: "Approved, noted"    |
| #9      | Sarah    | 3 days            | Full coverage      | Auto-approved      | (not involved)                     |

**What Ahmad sees in his Week 3 morning briefing:**

```
+----------------------------------------------------------+
|  HR Agent Update                                          |
|                                                           |
|  This month: 9 leave requests processed                   |
|  - 5 auto-approved (routine, good coverage)               |
|  - 2 flagged for your attention (you noted them)          |
|  - 1 held for your decision (you approved)                |
|  - 1 rescheduled (your suggestion)                        |
|                                                           |
|  The team seems to have a good leave pattern. Most        |
|  requests are straightforward.                            |
+----------------------------------------------------------+
```

**What Ahmad thinks:** "It handled 5 on its own and only bugged me 3 times. That's pretty good."

**What PACT has learned:**

- Ahmad approves leave quickly when coverage is fine (pattern: rubber-stamp)
- Ahmad intervenes when multiple people from the same team overlap (pattern: coverage-conscious)
- Ahmad does not reject leave requests; he suggests alternatives
- Confidence score for "auto-approve leave with full coverage": 0.88
- Confidence score for "flag leave with marginal coverage": 0.82

This data feeds into the shadow agent's suggestion engine. The agent is building a model of Ahmad's judgment. It will use this to suggest envelope refinements in Month 2.

---

## What Built Trust at Each Step

| Step           | Trust Signal                            | Why It Matters                 |
| -------------- | --------------------------------------- | ------------------------------ |
| Registration   | Simple, fast, no credit card            | "This isn't trying to trap me" |
| Team import    | Recognized my spreadsheet format        | "It understands how I work"    |
| Org chart      | Showed me my company correctly          | "It knows my team"             |
| Agent offer    | Clear list of can/cannot                | "I know what I'm getting"      |
| First hold     | Caught the team overlap I'd have missed | "This is actually useful"      |
| Auto-approvals | Handled the obvious ones silently       | "It's not wasting my time"     |
| Weekly summary | Showed me what it did and why           | "I know what's happening"      |

---

## Failure Points and Mitigations

| Failure                                            | Likelihood | Impact | Mitigation                                                                                |
| -------------------------------------------------- | ---------- | ------ | ----------------------------------------------------------------------------------------- |
| CSV has messy data (no departments, no job titles) | High       | Medium | Parser falls back to flat structure; shadow agent suggests departments later              |
| Ahmad does not tap "Start HR Agent"                | Medium     | Low    | Agent still runs in observation mode; offers again in 7 days                              |
| Ahmad ignores the first held action for days       | Medium     | Medium | Escalating notifications: day 1 nudge, day 3 reminder, day 5 "Sarah is still waiting"     |
| Employee data has wrong reporting lines            | Medium     | Low    | Tree still valid; shadow agent detects actual reporting patterns and suggests corrections |
| Ahmad's phone does not get push notifications      | Low        | Medium | Morning briefing email fallback; in-app badge count visible on next login                 |
| Ahmad adds employees manually later (not bulk)     | Medium     | None   | PACT tree recomputes on every employee add; envelopes assigned incrementally              |
