# Core User Flows

## Flow 1: First-Time User Onboarding

### Trigger

User visits the platform for the first time (web or mobile).

### Steps

1. **Welcome screen**
   - "Get expert HR guidance for your Singapore business"
   - Sign up with email or Google/Singpass (if applicable)

2. **Company profile setup** (progressive, ~2 minutes)
   - "What sector is your business in?" → Dropdown (F&B, Construction, Manufacturing, Services, Tech, Healthcare, Professional Services, Retail, Logistics, Other)
   - "How many employees do you have?" → Number input
   - "How many are Singapore Citizens or PRs?" → Number input
   - "Do you employ foreign workers?" → Yes/No
     - If yes: "How many EP holders? S Pass? Work Permit?" → Number inputs
   - "What's the approximate salary range of your employees?" → Range selector

3. **Instant compliance snapshot**
   - Based on profile, show 3-5 immediate insights:
     - "Based on your sector and headcount, here's what applies to you"
     - Flag any obvious gaps (e.g., "You have 30 employees but no documented grievance procedure — this is a tripartite standard")
     - Show upcoming thresholds (e.g., "At 50 employees, you'll need a designated Workplace Safety Officer")

4. **First question prompt**
   - "What HR question is on your mind today? Ask in your own words."
   - Show sample questions for their sector

### Exit

User is in the advisory interface with profile set up and first question answered.

---

## Flow 2: Advisory Q&A (Core Loop)

### Trigger

User types or speaks an HR question.

### Steps

1. **Question received**
   - Natural language input (text or voice)
   - System classifies: domain, sub-topic, risk level, complexity

2. **Context applied**
   - Company profile filters applicable regulations
   - Employee classification determined if question is about a specific employee type

3. **Response generated** (structured format)

   **For GREEN (factual) questions** — e.g., "How many days of annual leave must I give?"

   ```
   [Answer in plain language]

   For your company:
   - Employees in their 1st year: 7 days
   - Employees in their 3rd year: 9 days
   - Employees in their 8th year+: 14 days

   Source: Employment Act, Section 88A

   [Download: Annual Leave Policy Template]
   ```

   **For AMBER (guidance) questions** — e.g., "Should I offer dental benefits?"

   ```
   [Contextual recommendation based on sector benchmarks]

   Based on current guidelines:
   - [What the tripartite guidelines say]
   - [What's common in your sector]
   - [Cost implications for your company size]

   Source: Tripartite Guidelines on [relevant guideline]
   Note: This reflects current best practices. Your specific situation
   may warrant professional consultation for implementation.
   ```

   **For RED (high-stakes) questions** — e.g., "An employee filed a TADM claim"

   ```
   Here's what you need to know about the TADM process:

   [Step-by-step process overview]
   [Your immediate obligations and deadlines]
   [Documents you should gather]

   Source: Employment Claims Act, Sections [X-Y]

   ⚠️ This is a formal dispute process with legal implications.
   While this overview covers the standard process, the specifics
   of your case matter. Consider consulting an employment lawyer,
   especially if the claim amount is significant.

   [Connect to an employment law specialist]
   ```

4. **Follow-up options**
   - "Ask a follow-up question"
   - "Download related template"
   - "Run a calculation" (if applicable)
   - "See related topics"

### Exit

User has an actionable answer with sources and next steps.

---

## Flow 3: Foreign Worker Quota/Levy Calculator

### Trigger

User asks about hiring a foreign worker, or navigates to the calculator tool.

### Steps

1. **Current workforce input** (pre-filled from profile, editable)
   - Singapore Citizens: [number]
   - Permanent Residents: [number]
   - EP holders: [number]
   - S Pass holders: [number]
   - Work Permit holders: [number]

2. **Scenario input**
   - "What type of worker do you want to hire?" → EP / S Pass / Work Permit
   - "How many?" → Number

3. **Calculation result**

   ```
   Current Status:
   - Your sector: Services
   - DRC (Dependency Ratio Ceiling): 35%
   - Current ratio: 28% (within limit)
   - S Pass sub-quota: 12% (within 15% limit)

   After hiring 1 additional S Pass holder:
   - New ratio: 31% ✅ Within limit
   - New S Pass ratio: 14% ✅ Within limit
   - Monthly levy for this worker: $650 (Tier 2)
   - Total monthly levy impact: $650

   ⚠️ Note: You're approaching your S Pass sub-quota (14% of 15%).
   The next S Pass hire would bring you to the ceiling.

   Source: MOM Foreign Worker Levy rates (effective 1 Jan 2026)
   ```

4. **What-if scenarios**
   - "What if I hire a WP instead of S Pass?"
   - "What if I hire 2 more locals first?"
   - "Show me the levy impact for all my current foreign workers"

### Exit

User understands their quota position and levy cost before making a hiring decision.

---

## Flow 4: Document Generation

### Trigger

User requests a template or document.

### Steps

1. **Template selection**
   - From advisory context: "You mentioned you need an employment contract — let me generate one for you"
   - From template library: Browse categories (Contracts, Policies, Letters, Forms, Checklists)

2. **Context gathering** (for the specific document)
   - Employment contract example:
     - "Is this for a full-time or part-time employee?"
     - "What's their monthly salary?" (determines EA Part IV applicability)
     - "Are they local, PR, or foreign worker?"
     - "What's the job title and key responsibilities?"
     - "Probation period? (Common: 3 or 6 months)"
     - "Any specific allowances or benefits?"

3. **Document generated**
   - Preview in-app
   - Highlighted sections: "These clauses are required by the Employment Act" vs "These are recommended best practice" vs "These are customized to your input"
   - Compliance notes: "This contract includes all Key Employment Terms required under the Employment Act since April 2016"

4. **Download options**
   - PDF (ready to print and sign)
   - Word/DOCX (editable)
   - Save to account for future reference

### Exit

User has a compliant, contextual document ready to use.

---

## Flow 5: Compliance Health Check

### Trigger

User requests a compliance scan, or system suggests one during onboarding.

### Steps

1. **Profile verification**
   - Confirm company details are current
   - Any changes since last check?

2. **Scan runs** (based on profile)
   - Checks company profile against all applicable regulatory requirements
   - Identifies: what's required, what's likely in place, what's potentially missing

3. **Results presented** (prioritized by risk)

   ```
   Compliance Health Check Results

   🔴 HIGH PRIORITY (Act now)
   1. No documented Key Employment Terms provided to employees
      - Required since April 2016 for all EA-covered employees
      - Risk: MOM enforcement, up to $300 per employee
      - [Fix it: Generate KET templates for all employee types]

   2. WICA insurance may not cover all eligible employees
      - Required for all manual workers and employees earning ≤$2,100/month
      - Risk: Employer personally liable for work injury compensation
      - [Review: Which employees need coverage]

   🟡 MEDIUM PRIORITY (Address this quarter)
   3. No FWA request process documented
      - Required since December 2024 under TG-FWAR
      - Risk: TAFEP investigation if employee complaints arise
      - [Fix it: Generate FWA policy and process template]

   🟢 GOOD PRACTICE (When you have time)
   4. No formal grievance handling procedure
      - Recommended under Tripartite Standard on Grievance Handling
      - Not statutory but expected by TAFEP
      - [Create: Grievance procedure template]
   ```

4. **Action plan**
   - Prioritized checklist of items to address
   - Each item links to the relevant advisory topic and template
   - Track progress over time

### Exit

User has a clear picture of their compliance status and a prioritized action plan.

---

## Flow 6: Regulatory Change Alert

### Trigger

A regulation changes that affects the user's company profile.

### Steps

1. **Alert delivered** (push notification + in-app + email)

   ```
   📋 Regulatory Update Affecting Your Business

   What changed: CPF contribution rates for employees aged 55-60
   will increase from 1 January 2027

   How it affects you: You have 3 employees in this age band.
   Your monthly CPF cost will increase by approximately $XXX.

   What you need to do:
   1. Update your payroll system with new rates (by December 2026)
   2. Budget for the increased employer contribution
   3. No action needed from your employees

   Source: CPF Board announcement, [date]
   Effective: 1 January 2027

   [See detailed breakdown] [Update my budget calculator]
   ```

2. **Detailed view** (if user clicks through)
   - Full explanation of the change
   - Exact impact on user's company (calculated from profile)
   - Comparison: current rates vs. new rates for each affected employee category
   - Timeline: when to prepare, when it takes effect

### Exit

User understands how the change affects them and what to do about it.

---

## Flow 7: Mobile Quick Access

### Trigger

User opens mobile app (Flutter).

### Steps

1. **Dashboard** (optimized for quick glances)
   - Any new regulatory alerts? → Badge count
   - Quick actions: Ask a question, Run a calculation, Generate a document
   - Recent conversations and documents

2. **Voice input**
   - Tap microphone, ask question in natural language
   - Especially useful for on-the-go SME owners

3. **Quick calculators** (one-tap access)
   - CPF calculator
   - Quota calculator
   - Leave entitlement calculator
   - Notice period calculator

4. **Offline access** (for critical references)
   - Downloaded templates available offline
   - Key reference tables (CPF rates, levy rates, leave entitlements) cached locally

### Exit

User gets quick answers without navigating complex menus.

---

## Flow Summary Matrix

| Flow                    | Persona A (Owner, 5-20) | Persona B (Scaling, 20-100) | Persona C (Solo HR) | Persona D (Consultant) |
| ----------------------- | ----------------------- | --------------------------- | ------------------- | ---------------------- |
| Onboarding              | Primary entry           | Primary entry               | Primary entry       | Primary entry          |
| Advisory Q&A            | Daily use               | Weekly use                  | Daily use           | Daily use              |
| Quota/Levy Calculator   | Occasional              | Frequent                    | Frequent            | Per-client             |
| Document Generation     | Monthly                 | Weekly                      | Weekly              | Daily                  |
| Compliance Health Check | Quarterly               | Monthly                     | Monthly             | Per-client             |
| Regulatory Alerts       | As needed               | As needed                   | As needed           | As needed              |
| Mobile Quick Access     | Primary device          | Secondary                   | Secondary           | On-the-go              |
