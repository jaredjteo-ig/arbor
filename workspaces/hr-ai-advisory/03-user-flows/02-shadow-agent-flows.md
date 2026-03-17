# Shadow Agent User Flows

## Flow 1: First-Time User with Shadow Agent

### Trigger

User signs up and completes onboarding. This is their first session with the shadow agent.

### Steps

1. **Dashboard loads with shadow widget**
   - Bottom-right: subtle 36px breathing circle (the shadow widget)
   - Tooltip on hover: "Ask AITE anything (Ctrl+Shift+A)"
   - No margin yet (first session — margin appears after the agent has observations to show)
   - Dashboard shows Getting Started steps as before

2. **User clicks shadow widget**
   - Command surface opens: centered floating bar, top third of screen, dimmed backdrop
   - Placeholder text: "Ask anything about Singapore HR, or tell me what to do..."
   - Below: suggested commands based on onboarding data:
     - "What compliance gaps does my company have?"
     - "Calculate CPF for my employees"
     - "Show me the employment contracts I need"
   - Recent commands: empty (first session)

3. **User types "What notice period must I give?"**
   - Stream of thought: "Searching knowledge base... Found EA s.10..."
   - Result renders inline in the overlay:
     - Structured answer with notice periods by length of service
     - Source citation pills: [Employment Act s.10] [EA Part II]
     - "Ask follow-up" input appears below
   - User presses Escape — overlay dismisses, back to dashboard

4. **User clicks "Compliance check" in Getting Started**
   - Navigates to /compliance as normal
   - Shadow widget pulses briefly (attention state) — the agent has something contextual
   - If user clicks widget: "Based on your company profile (25 employees, Technology sector), here are the regulations that apply to you. Want me to run a quick assessment?"

### Exit

User has experienced the shadow agent as a command surface (not a chatbot) and seen it provide contextual awareness.

---

## Flow 2: Admin Daily Workflow

### Trigger

Returning admin user opens AITE on a Monday morning.

### Steps

1. **Dashboard loads**
   - Shadow widget breathing (ambient state)
   - Right margin appears (48px collapsed) — agent has observations from previous sessions
   - Context dots visible: 2 dots
     - Dot 1 tooltip: "CPF submission deadline in 5 days"
     - Dot 2 tooltip: "2 employees approaching probation end date"
   - Dashboard briefing card (inline annotation, Layer C):
     - "Good morning. 2 compliance items need attention. CPF deadline March 22."

2. **User expands margin (clicks it or Ctrl+Shift+A)**
   - 320px card stack appears:
     - **Top card**: "CPF submission due March 22. Your last calculation was February. Want me to calculate March contributions for all employees?"
     - **Action card**: [Calculate March CPF] [Remind me Thursday] [Dismiss]
     - **Memory thread**: "You typically review compliance on Mondays" (learned pattern, editable)

3. **User clicks "Calculate March CPF"**
   - Action plan card appears: "I'll calculate CPF for 25 employees using current salary data and 2026 rates. Results will include employer + employee breakdown."
   - [Do it] [Adjust] [Cancel]
   - User clicks "Do it"
   - Stream of thought: "Calculating... 25 employees processed"
   - Result card: summary table with total employer/employee contributions
   - [Download CSV] [View details] [Pin to margin]

4. **User navigates to Compliance page**
   - Inline annotations appear on checklist items (Layer C):
     - Next to "KET issued": warning icon + "3 new employees since last KET review"
     - Next to "FWA policy": check icon + "Policy document generated on March 5"
   - Shadow widget ambient (no attention needed here)

### Exit

Admin has handled Monday compliance tasks with shadow agent assistance, without opening a chat drawer once.

---

## Flow 3: Employee Self-Service

### Trigger

Employee (invited by admin) logs into their AITE account.

### Steps

1. **Employee dashboard loads**
   - Simplified navigation: My Dashboard, My Leave, My Terms, Policies, Ask AITE
   - No admin pages (Compliance, Calculators, Documents, Clients, Analytics, Emergency)
   - Shadow widget present (same breathing circle)
   - Dashboard shows:
     - Employment summary card: role, start date, department
     - Leave balance card: annual leave used/remaining, sick leave used/remaining
     - Next payslip date
     - Recent company announcements (if any)

2. **Employee clicks shadow widget**
   - Command surface opens with employee-relevant suggestions:
     - "How many leave days do I have left?"
     - "What's my notice period?"
     - "Can I request flexible work arrangements?"
     - "Show me the company leave policy"

3. **Employee types "Can I take 3 days leave next week?"**
   - Agent checks leave balance: "You have 11 days annual leave remaining. 3 days next week is available."
   - Action card: "Apply for annual leave: March 24-26"
   - [Submit request] [Change dates] [Cancel]
   - User clicks "Submit request" → leave request sent to manager for approval

4. **Employee asks "What's my CPF contribution this month?"**
   - Agent looks up employee's salary and age band
   - Result: "Based on your salary of $4,500 (age 28, Singapore Citizen): Employer contributes $765 (17%), Employee contributes $900 (20%). Your OA receives $1,002, SA $333, MA $330."
   - Source: [CPF Act — Contribution Rates 2026]

### Exit

Employee got answers to their HR questions and submitted a leave request without ever contacting HR.

---

## Flow 4: Command Surface Power User

### Trigger

Experienced admin user who has been using AITE for weeks. Shadow agent has learned their patterns.

### Steps

1. **User opens command surface (Ctrl+Shift+A)**
   - Recent commands populated:
     - "Calculate CPF for all employees"
     - "Check compliance status"
     - "Generate KET for new hire"
   - Suggestions based on learned patterns:
     - "It's Monday — run your weekly compliance check?" (learned: user checks compliance on Mondays)
     - "New employee Sarah joined last week — KET document needed"

2. **User types "Onboard Sarah Chen, developer, $6,000"**
   - Agent creates a multi-step action plan:

     ```
     Onboard Sarah Chen — Developer — $6,000/month

     Step 1: Create employee record
     Step 2: Generate Key Employment Terms document
     Step 3: Calculate CPF contributions (employer: $1,020, employee: $1,200)
     Step 4: Add to company headcount
     Step 5: Send welcome email with login credentials

     [Start onboarding] [Adjust details] [Cancel]
     ```

   - User clicks "Start onboarding"
   - Stream of thought shows each step completing
   - Result: "Sarah Chen onboarded. KET document ready for download. CPF registration reminder set for next business day."

3. **User types "Who hasn't submitted their timesheets?"**
   - Agent: "3 employees have not submitted timesheets for March: [Employee A], [Employee B], [Employee C]. Want me to send a reminder?"
   - [Send reminder to all 3] [Select which] [Cancel]

4. **User types "Take me to emergency guides"**
   - Command surface dismisses, navigates to /emergency
   - No further interaction needed

### Exit

Power user completes multiple admin tasks through natural language commands without navigating through forms.

---

## Flow 5: Enterprise Admin Inviting Employees

### Trigger

Admin has set up the company and wants to bring employees onto the platform.

### Steps

1. **Admin navigates to Employees page (new)**
   - Shows employee list (currently empty for new companies)
   - "Invite employees" button prominent
   - Shadow widget pulses: agent has a suggestion

2. **Admin clicks shadow widget or Invite button**
   - If via widget: "You have 25 employees in your company profile but none on the platform yet. Want to invite them?"
   - Invitation form:
     - Bulk invite via CSV upload (name, email, role, department, salary, start date)
     - Or individual invite (name, email)
   - Role assignment: "employee" (default) or "hr_manager"

3. **Admin uploads CSV with 25 employees**
   - Agent validates: "25 employees parsed. 2 have missing email addresses. 1 has a salary below minimum wage ($1,600). Want to proceed with the 22 valid entries?"
   - [Invite 22] [Fix errors first] [Cancel]

4. **Invitations sent**
   - Email sent to each employee with registration link
   - Admin sees invitation status: sent, accepted, expired
   - Shadow margin dot: "12 of 22 employees have registered so far"

5. **Admin checks employee compliance**
   - Shadow inline annotation on Compliance page: "15 employees need KET documents. Want me to generate them in bulk?"
   - [Generate 15 KETs] → bulk document generation with employee-specific terms

### Exit

Admin has onboarded employees with AI assistance, generated compliance documents in bulk.

---

## Flow 6: Shadow Agent Proactive Alert

### Trigger

A regulatory change occurs (e.g., CPF rate update), or a compliance deadline approaches.

### Steps

1. **User opens AITE on any page**
   - Shadow widget shows attention state: gentle ripple every 5 seconds
   - Right margin has a new context dot with a distinct colour (amber for attention)

2. **User hovers on the attention dot**
   - Tooltip: "CPF OW ceiling increases to $8,500 from January 2027. Affects 8 of your employees."

3. **User expands margin**
   - Top card: detailed alert
     - "The CPF ordinary wage ceiling will increase from $8,000 to $8,500 effective 1 January 2027. This affects 8 of your 25 employees who earn above the current ceiling. Estimated additional employer CPF cost: $340/month."
     - Source: [CPF Act Amendment 2026]
   - Action cards:
     - [Calculate impact for all employees]
     - [Show affected employees]
     - [Dismiss — I'll handle this later]

4. **User clicks "Calculate impact"**
   - Results show per-employee CPF increase
   - [Download report] [Add to next board meeting agenda] [Dismiss]

### Exit

User was proactively informed of a regulatory change that affects their company, with quantified impact and actionable next steps — without asking.
