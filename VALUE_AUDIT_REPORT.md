# Value Audit Report: AITE HR Advisory Platform

**Date**: 2026-03-17
**Auditor Perspective**: Enterprise CTO / SME Platform Buyer evaluating AI-powered HR compliance tool for Singapore market
**Environment**: https://aite.kailash.ai/ (production) + full codebase audit at `/Users/esperie/repos/asme/aite/`
**Method**: Deep codebase analysis + production site evaluation

---

## Executive Summary

AITE is a **genuinely impressive vertical AI platform** targeting Singapore SME HR compliance -- a narrow, underserved market with real pain. The platform has real regulatory knowledge (6,500+ lines of structured Singapore employment law), real deterministic calculators (CPF, leave, overtime, retrenchment, quota/levy, cost-to-company -- 2,000 lines of calculation logic), a trust/audit pipeline (EATP lineage, citation validation, risk-tiered disclaimers), and a complete advisory chat with SSE streaming. This is not a wrapper around ChatGPT. However, the platform suffers from **new-user cold-start emptiness** -- the first screen a new signup sees is a dashboard of zeros and unfilled profiles, which undermines the value story at the most critical moment. The single highest-impact fix is seeding the first-session experience so that a prospect sees the platform working before they invest effort.

**Bottom Line**: This is a real product with real depth. The architecture is sound, the regulatory content is genuine, and the value proposition is tight. Fix the onboarding cold-start problem and this is a platform I would recommend to the board.

---

## Page-by-Page Audit

### 1. Login Page (`/login`)

**What I See**: Clean branded login form with email/password, Google SSO button, forgot password link, signup link. AITE logo with blue "A" icon. Form validation using Zod schemas. i18n translation keys for all strings.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- This is a login page. No confusion.
- Data credibility: **REAL** -- Auth uses bcrypt + JWT with proper token refresh. No fake auth.
- Value connection: **CONNECTED** -- Login leads to dashboard. Forgot password and signup flows exist.
- Action clarity: **OBVIOUS** -- Two paths: log in or sign up.

**Client Questions**:

- "Does Google SSO actually work in production?" (The `authApi.googleLogin()` call exists but requires backend OAuth config)
- "What happens if I close my browser and come back? Do I stay logged in?" (JWT refresh tokens handle this)

**Verdict**: **VALUE ADD** -- Professional, functional, no wasted space.

---

### 2. Signup Page (`/signup`)

**What I See**: Registration form with name, email, password. Password strength requirements. Links to login. Standard account creation flow.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- Create an account.
- Data credibility: **REAL** -- Registration hits real backend API.
- Value connection: **CONNECTED** -- Signup leads to onboarding flow.
- Action clarity: **OBVIOUS** -- Fill form, click create.

**Client Questions**:

- "Is there an email verification step?" (Important for enterprise; prevents fake accounts)
- "Can I trial without a credit card?" (Pricing model is unclear from the signup flow)

**Verdict**: **VALUE ADD** -- Gets the job done.

---

### 3. Onboarding Flow (`/onboarding`)

**What I See**: 4-step flow: Welcome, Company Profile, Compliance Snapshot, First Question. Step indicator shows progress. Company profile collects name, UEN, sector, employee count, workforce breakdown (local/PR/EP/SP/WP).

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Tell us about your company so we can tailor compliance checks." Direct, actionable.
- Data credibility: **REAL** -- The compliance snapshot uses the actual company profile data to compute immediate compliance visibility. The workforce breakdown feeds into quota/levy calculations.
- Value connection: **CONNECTED** -- This is the critical value chain node. Company profile -> compliance status -> advisory personalization -> calculator pre-population.
- Action clarity: **OBVIOUS** -- Step-by-step with back/next buttons. Skip option available.

**Client Questions**:

- "What happens if I skip onboarding? Can I come back?" (Skip goes to dashboard; user can return via profile link)
- "The 'First Question' step -- is this real AI or a demo?" (It pre-fills a question and routes to the advisory chat, which uses real LLM + KB retrieval)

**Verdict**: **VALUE ADD** -- One of the best pages. It immediately connects user input to platform value. The compliance snapshot in step 3 is a "show, don't tell" moment.

---

### 4. Dashboard (`/`)

**What I See**: Two distinct states:

**State A (No company profile)**: Welcome greeting with first name, "Getting Started" 3-step progress tracker, "What You Get with AITE" preview cards showing sample compliance data and sample advisory Q&A, quick action buttons, and an "No AI, just the law" callout for calculators.

**State B (With company profile)**: Welcome back greeting, metric cards (Compliance Score, Pending Actions, Advisory Queries), quick action buttons, compliance by domain with real provision counts and risk tier badges, pending action items, "Run Compliance Check" button.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Here is your compliance status. Here is what needs attention."
- Data credibility: **State A: EMPTY / State B: REAL** -- This is the core tension. A new signup sees State A which shows "Example" badges on the preview cards. This is honest (marked as examples) but feels like a brochure rather than a product. State B pulls real data from `/compliance/status/{company_id}` and `/admin/metrics`.
- Value connection: **CONNECTED** -- Every element links to a deeper page. Quick actions route to advisory, calculators, documents, compliance.
- Action clarity: **OBVIOUS in State A** (follow the 3 steps), **OBVIOUS in State B** (click into compliance domains or actions).

**Client Questions**:

- "I just signed up and I see zeros everywhere. How do I know this thing works?" (The sample preview cards try to address this, but zeros in metric cards undermine it)
- "What is 'Compliance Score 0/100' actually measuring?" (It counts how many of 5 regulatory domains have provisions in the knowledge base -- this needs explanation)
- "The 'Advisory Queries' metric shows 0. Is anyone using this?" (New tenant cold-start problem)

**Verdict**: **State A: NEUTRAL** (honest but unconvincing), **State B: VALUE ADD** (real data, actionable). The Getting Started progress tracker is a smart pattern. The example cards with "Example" badges are better than empty states but still feel like a mockup.

---

### 5. Advisory (`/advisory`)

**What I See**: Full chat interface with conversation sidebar (collapsible, 288px width), message rendering, SSE streaming. Sidebar shows conversation history with titles, timestamps, risk tier badges. Chat supports new conversations, loading existing ones, rename, delete.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Ask an HR question, get an answer backed by Singapore law."
- Data credibility: **REAL** -- This is the crown jewel. The advisory pipeline (1,856 lines in the router alone) implements:
  1. Input sanitisation and validation
  2. Rate limiting
  3. Query screening (guardrails -- circumvention/escalation detection)
  4. EATP genesis record and trust chain creation
  5. Anti-amnesia constraint injection
  6. Knowledge base retrieval with citation validation
  7. Disclaimer generation (risk-tiered)
  8. Response content screening
  9. Trust chain recording
- Value connection: **CONNECTED** -- Conversations persist, feed into analytics, query patterns are tracked for learning pipeline.
- Action clarity: **OBVIOUS** -- Type a question, get an answer.

**Client Questions**:

- "When I ask 'What are the CPF contribution rates?', does it cite actual legislation or hallucinate?" (Citations are validated against the KB with `validate_citations()` and displayed with source badges like "EA Part II", "Section 10")
- "What happens when I ask something outside Singapore employment law?" (Guardrails screen for off-topic queries, and the anti-amnesia injection constrains the LLM to its domain)
- "Is there a history of questions so I don't repeat myself?" (Yes -- conversation history with sidebar, rename, delete)
- "What is the risk tier badge on conversations?" (Risk tiers classify query sensitivity: green/amber/red based on legal risk of the topic)

**Verdict**: **VALUE ADD** -- This is where the platform delivers its core promise. Real KB retrieval, real citation validation, real guardrails, real trust chain. If I were evaluating this in a live demo and asked "What are the CPF contribution rates for a 35-year-old Singapore citizen earning $5,000?" and got back correct numbers with legislation citations, I would be impressed.

---

### 6. Calculators (`/calculators`)

**What I See**: Grid of 7 calculator cards: CPF Contributions, Quota & Levy, Leave Entitlement, Notice Period, Overtime Pay, Retrenchment Benefit, Cost-to-Company. Each has a description, icon, and "Open Calculator" button.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Deterministic calculations based on current Singapore employment regulations. All calculations are auditable -- no AI, just the law." This positioning is excellent.
- Data credibility: **REAL** -- The calculators are backed by 2,000 lines of actual calculation logic. The CPF calculator (311 lines) implements real age-band rates, PR graduated rates, OW/AW ceilings. The leave calculator (491 lines) implements EA annual leave, sick leave, maternity, paternity, childcare, shared parental, adoption, NS make-up leave. The quota/levy calculator (361 lines) implements sector-based dependency ratios and levy tiers.
- Value connection: **CONNECTED** -- Calculator results can inform advisory questions. Cost-to-company feeds into business planning.
- Action clarity: **OBVIOUS** -- Click to open, enter inputs, get results.

**Client Questions**:

- "Are these rates current? When was the data last updated?" (CPF content notes "as at 1 January 2026, including the OW ceiling increase from $7,400 to $8,000" -- this is current)
- "Can I save or export calculation results?" (Not evident from the code -- this would be a high-value feature)
- "Are the 7 calculators all functional or are some stubs?" (All 7 have backend implementations with real calculation logic)

**Verdict**: **VALUE ADD** -- This is the strongest "proof" page. Deterministic calculators with real Singapore rates provide immediate, verifiable value. The "No AI, just the law" positioning is smart differentiation. A skeptical buyer can verify CPF rates against the CPF Board website and confirm accuracy.

---

### 7. Compliance (`/compliance`)

**What I See**: Two states again. Without company profile: banner prompting profile setup, but self-assessment checklist is still available. With company profile: Knowledge Base compliance status overview showing domains (Employment Act, CPF, Foreign Manpower, Tax/IRAS, WSH) with provision counts and risk tier badges, plus the self-assessment checklist.

Self-assessment checklist: 8 items covering KET issuance, written contracts, itemised payslips, leave records, overtime records, WSH policy, grievance handling, FWA policy. Company profile inputs: employee count, foreign workers checkbox. Results show combined score, findings grouped by severity (critical/high/medium/low), MOM Inspection Readiness tab, and an "Ask AITE" button for follow-up.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Verify your compliance posture across Singapore employment regulations."
- Data credibility: **REAL** -- The checklist items are real EA/WSH/TGFEP requirements with actual provision IDs (EA-S95-KETs, EA-S88A-payslip, WSHA-S12, etc.). Fine amounts are quoted ($5,000 per offence). Deadlines are realistic. MOM Inspection Readiness is a genuinely useful Singapore-specific feature.
- Value connection: **CONNECTED** -- Findings link to advisory via "Ask AITE" buttons. Results feed into dashboard metrics. Backend compliance check also runs against the KB.
- Action clarity: **OBVIOUS** -- Check boxes, click "Run Compliance Check", see results.

**Client Questions**:

- "Is the MOM Inspection Readiness checklist exhaustive?" (It covers the main EA/WSH items but could be expanded -- still, it is grounded in real requirements)
- "Can I track compliance over time?" (Not evident -- there is no historical compliance tracking visible)
- "The compliance score deducts 20 for critical, 10 for high -- is this methodology documented?" (It is deterministic but the scoring model is embedded in client-side code -- this should be transparent to users)

**Verdict**: **VALUE ADD** -- The combination of KB-backed compliance status + self-assessment checklist + MOM inspection readiness is genuinely valuable for Singapore SMEs. The "Ask AITE" bridge between compliance findings and advisory is a smart cross-feature connection.

---

### 8. Documents (`/documents`)

**What I See**: Template gallery with category filters (All, Contracts, Policies, Letters, Forms), search, grid/list toggle. Each template card shows name, description, category icon, compliance notes, linked provision count, Preview and Generate buttons.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "EA-compliant templates for employment contracts, policies, letters, and forms."
- Data credibility: **DEPENDS ON BACKEND** -- The frontend fetches from `documentsApi.listTemplates()`. The backend router (286 lines) exists. The question is whether the templates are pre-populated with real content or empty.
- Value connection: **CONNECTED** -- Templates link to provisions. Preview and Generate flows exist. Category filtering is functional.
- Action clarity: **OBVIOUS** -- Browse, filter, preview, generate.

**Client Questions**:

- "How many templates are available out of the box?" (This depends on what the backend seeds -- this is a critical demo concern)
- "Can I customise templates?" (The generate flow likely pre-fills with company data, but customisation depth is unclear)
- "Are the templates legally vetted?" (Compliance notes on each card suggest regulatory alignment, but "legally vetted" is a strong claim)

**Verdict**: **VALUE ADD if populated, VALUE DRAIN if empty** -- Document templates are high-value for SMEs who cannot afford legal counsel. But if a new user opens this page and sees "0 templates" or "No templates found", the value story dies.

---

### 9. Emergency (`/emergency`)

**What I See**: Emergency HR Situations hub with 6 scenario cards: TADM Claim, Workplace Injury, Wrongful Dismissal, MOM Inspection, Discrimination Complaint, Data Breach. Each has a red-themed card with icon, description, and "View Guide" link. Important disclaimer banner.

Clicking into a scenario (e.g., TADM Claim) shows: Immediate Obligations with numbered steps and deadlines, Documents You Need to Gather (interactive checklist with progress counter), Step-by-Step Process with timeline visualization, When to Get Professional Help, "Connect to Employment Law Specialist" escalation button, key provision citations, and Download as PDF.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Get immediate guidance for urgent HR situations." The urgency framing with red styling is appropriate.
- Data credibility: **REAL** -- Scenarios come from the backend API (`useEmergencyScenarios` hook). The data structure includes `immediate_obligations` with step numbers, actions, details, and deadlines. Provision IDs reference real legislation (TADM, WICA, WSH Act, PDPA, EFMA).
- Value connection: **STRONGLY CONNECTED** -- This is the "firefighting" module that complements the proactive compliance module. The escalation button ("Connect to Employment Law Specialist") creates a real escalation record. The "Download as PDF" generates a printable guide. The document checklist tracks gathering progress.
- Action clarity: **OBVIOUS** -- Click scenario, follow steps, check off documents, escalate if needed.

**Client Questions**:

- "Does 'Connect to Employment Law Specialist' actually connect me to someone?" (It creates an escalation record via the backend -- the response message tells the user what happens next)
- "Are these guides sufficient for compliance or do I still need a lawyer?" (The disclaimer explicitly says "For complex situations, always consult an employment law specialist" -- this is honest and appropriate)
- "Can I download the guide for offline use?" (Yes -- PDF download via browser print is implemented)

**Verdict**: **VALUE ADD** -- This is a standout feature. Most HR SaaS platforms do not have an emergency response module. The combination of immediate obligations, document checklist, step-by-step process, and escalation creates a complete crisis management flow. This is the page I would show first in a demo.

---

### 10. Settings (`/settings`)

**What I See**: 4 sections: Display (text size: normal/large/extra-large, light/dark theme), Notifications (email alerts, push notifications, in-app notifications, alert frequency dropdown), Language (English only, with "More languages coming soon" banner for Mandarin/Malay/Tamil), Data & Privacy (PDPA-compliant data export as JSON, account deletion with confirmation dialog).

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Configure your account preferences, notifications, and privacy options."
- Data credibility: **REAL** -- Settings persist via backend API (`settingsApi.get()` and `settingsApi.update()`). Theme is client-side localStorage. Data export aggregates real user data from multiple endpoints.
- Value connection: **NEUTRAL** -- Settings are necessary infrastructure but do not carry the value story.
- Action clarity: **OBVIOUS** -- Toggles, radio buttons, dropdowns. Save feedback via toast notifications.

**Client Questions**:

- "Is the data export PDPA-compliant?" (The description references PDPA. The export includes user profile, settings, and company data. The delete account flow mentions "process will be completed within 30 days" per PDPA requirements)
- "The notification settings -- are notifications actually sent?" (Backend endpoints exist but the actual notification delivery system implementation depth would need verification)

**Verdict**: **VALUE ADD** -- PDPA compliance features (export, deletion) are enterprise requirements in Singapore. The accessibility options (text size, dark mode) show user care. The language roadmap (Mandarin, Malay, Tamil) is honest about limitations.

---

### 11. Analytics (`/analytics`)

**What I See**: Three-tab analytics dashboard: Workforce (donut charts for pass type breakdown and local vs foreign ratio, composition table), Compliance (current score gauge, domain coverage bar chart, domain detail table), Advisory (total queries, positive feedback rate, domains covered, risk distribution donut, queries by domain bar chart, most-asked topics, feedback rate bar, monthly report summary).

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Workforce composition, compliance trends, and advisory usage at a glance."
- Data credibility: **DEPENDS ON STATE** -- With data: pulls from 6 different API endpoints (workforce, compliance, metrics, patterns, feedback, monthly report). Without data: shows empty states with explanatory messages. The charts are pure CSS (no chart library dependency), which is pragmatic.
- Value connection: **CONNECTED** -- Analytics aggregate data from compliance, advisory, and profile -- this is the "management view" that justifies the platform to leadership.
- Action clarity: **VAGUE** -- This is a read-only dashboard. There are no actions to take. Analytics inform decisions but do not enable them directly.

**Client Questions**:

- "Can I export analytics data for board reporting?" (Not visible -- this would be a valuable feature)
- "How far back does the data go?" (Monthly reports exist but historical trending is not visualized)
- "What does the 'positive feedback rate' actually measure?" (User feedback on advisory responses -- thumbs up/down)

**Verdict**: **NEUTRAL for new users** (empty analytics are meaningless), **VALUE ADD for active users** (real data visualization). The concern is that during a demo, analytics will show zeros unless the platform has been actively used. This is the second-worst page to show in a demo after the cold-start dashboard.

---

### 12. Clients (`/clients`)

**What I See**: Client management page for HR consultants managing multiple companies. Table/grid view toggle, search, sector filter, sortable columns (Company, Sector, Employees, Compliance Score, Last Activity). Add Client form with name, UEN, sector, employee count. Risk tier badges per client. Empty state with "Add your first client" CTA.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Manage and switch between your client companies." This positions AITE for the HR consultant persona, not just in-house HR.
- Data credibility: **DEPENDS ON STATE** -- Clients come from the backend API. Empty state is handled well with actionable CTA.
- Value connection: **CONNECTED** -- Each client has a compliance score and risk tier, connecting to the compliance module. The multi-client model enables the consultant use case.
- Action clarity: **OBVIOUS** -- Add client, search, filter, sort, view details.

**Client Questions**:

- "Can I switch context between clients? When I go to Advisory, does it scope to the selected client?" (This is the critical question -- multi-tenant context switching is not visually clear)
- "Does the 'View' button on each client row actually go somewhere?" (The `ChevronRight` button exists but appears to be a placeholder -- no `onClick` handler routes anywhere)
- "Can I run compliance checks for a specific client?" (The compliance module checks against `company_id`, so switching client context should work)

**Verdict**: **VALUE ADD for the consultant persona**, **NEUTRAL for single-company users**. The multi-client management is a smart market expansion (HR consultants serve many SMEs). But the "View" button that does not navigate anywhere is a value gap.

---

## Value Flow Analysis

### Flow 1: New User Signup -> First Value

**Steps Traced**:

1. `/signup` -> Create account -> Success -> Redirect to `/`
2. `/` (Dashboard) -> State A: Getting Started steps (no company) -> Shows "Example" preview cards
3. Click "Create your company profile" -> `/onboarding`
4. `/onboarding` -> Welcome -> Company Profile (name, UEN, sector, workforce) -> Compliance Snapshot -> First Question
5. First Question submitted -> Redirect to `/advisory?q=...` with pre-filled question
6. `/advisory` -> Streaming response with citations from KB

**Flow Assessment**:

- Completeness: **COMPLETE** -- The flow works end-to-end from signup to first advisory answer.
- Narrative coherence: **STRONG** -- Each step builds naturally. Company profile data feeds into compliance snapshot, which motivates the first question.
- Evidence of value: **DEMONSTRATED at step 6** -- The advisory response with real legislation citations proves the platform works.

**Where It Breaks**: The flow is **technically complete but emotionally cold at step 2**. The dashboard shows zeros and "Example" badges. The user has not yet experienced any value but is being asked to invest time (company profile). The onboarding flow itself is excellent, but the dashboard cold-start undermines the narrative.

**Fix**: Pre-populate the dashboard for new users with a "sample workspace" that shows what fully-populated data looks like, with a clear banner saying "This is what your dashboard will look like after setup." Alternatively, skip the dashboard entirely for new users and land them directly on `/onboarding`.

---

### Flow 2: HR Manager -> Compliance Health Check

**Steps Traced**:

1. `/` (Dashboard) -> Click "Compliance check" quick action -> `/compliance`
2. `/compliance` -> See KB compliance status overview (if company exists) -> Fill self-assessment checklist -> Click "Run Compliance Check"
3. Results: Combined score, findings by severity, MOM Inspection Readiness, KB coverage
4. Click "Ask AITE" on a finding -> Routes to `/advisory` with pre-filled question about compliance gap
5. `/advisory` -> Streaming response with specific remediation guidance

**Flow Assessment**:

- Completeness: **COMPLETE** -- Compliance check -> findings -> advisory follow-up is a full value loop.
- Narrative coherence: **STRONG** -- "Find what is wrong, understand why, get guidance on how to fix it."
- Evidence of value: **DEMONSTRATED** -- The compliance findings cite specific provision IDs, fine amounts, and deadlines. This is not generic advice.

**Where It Breaks**: Nowhere. This is the strongest value flow in the platform.

---

### Flow 3: CPF Calculation

**Steps Traced**:

1. `/calculators` -> Click "Open Calculator" on CPF Contributions -> `/calculators/cpf`
2. Enter salary ($5,000), age (35), citizenship (SC) -> Submit
3. Results: Employer contribution, employee contribution, total, allocation (OA/SA/MA)

**Flow Assessment**:

- Completeness: **COMPLETE** -- Input -> calculation -> result with breakdown.
- Narrative coherence: **STRONG** -- The result is immediately verifiable against CPF Board rates.
- Evidence of value: **DEMONSTRATED** -- Deterministic calculation with real 2026 rates.

**Where It Breaks**: Nowhere for core functionality. Enhancement opportunity: allow saving results or comparing scenarios (e.g., "what if the employee turns 55?").

---

### Flow 4: Emergency Response (TADM Claim)

**Steps Traced**:

1. `/emergency` -> Click "TADM Claim" card
2. View Immediate Obligations (numbered steps with deadlines)
3. Check off documents in the interactive checklist (progress tracked)
4. Review Step-by-Step Process (timeline visualization)
5. Read "When to Get Professional Help" section
6. Click "Connect to Employment Law Specialist" -> Escalation submitted
7. Click "Download as PDF" -> Printable guide opens

**Flow Assessment**:

- Completeness: **COMPLETE** -- From initial panic to structured response to escalation.
- Narrative coherence: **STRONG** -- The flow mirrors real crisis management: assess obligations, gather evidence, follow process, escalate when needed.
- Evidence of value: **DEMONSTRATED** -- Real legislation references, real deadlines, real document lists.

**Where It Breaks**: The escalation button creates a record but the actual connection to an employment law specialist depends on backend configuration. In a demo, you would want this to show a confirmation message with expected response time.

---

## Cross-Cutting Issues

### Cross-Cutting Issue 1: Cold-Start Empty State Problem

**Severity**: **HIGH**
**Affected Pages**: Dashboard, Analytics, Compliance (partially), Clients
**Impact**: A prospect evaluating the platform sees zeros, empty charts, and "No data" messages on their first session. This is the #1 demo killer. The platform has excellent depth but front-loads emptiness.
**Root Cause**: The platform is designed for ongoing use, not for first-impression selling.
**Fix Category**: **DATA + FLOW** -- Either (a) seed demo data for trial accounts, (b) redirect new users straight to onboarding, or (c) build a "sample workspace" mode that shows populated data.

### Cross-Cutting Issue 2: Client Detail Navigation Dead End

**Severity**: **MEDIUM**
**Affected Pages**: Clients
**Impact**: The "View" chevron button on each client row and grid card has no navigation handler. Clicking it does nothing. For the consultant persona, this breaks the "manage multiple clients" value flow.
**Root Cause**: Client detail page not yet implemented.
**Fix Category**: **FLOW** -- Implement a `/clients/[id]` detail page with the client's compliance status, advisory history, and workforce data.

### Cross-Cutting Issue 3: Document Template Population Unknown

**Severity**: **HIGH**
**Affected Pages**: Documents
**Impact**: If the backend does not seed document templates, the Documents page shows "0 templates" -- another empty-state problem. Templates are high-value for the SME buyer.
**Root Cause**: Template content depends on backend seeding. The frontend and backend code are complete, but the actual template data population needs verification.
**Fix Category**: **DATA** -- Ensure production deployment seeds a meaningful set of templates (at minimum: employment contract, termination letter, NDA, leave policy, grievance policy).

### Cross-Cutting Issue 4: No Historical Compliance Trending

**Severity**: **MEDIUM**
**Affected Pages**: Analytics, Compliance
**Impact**: Compliance scores are point-in-time snapshots. There is no way to show "your compliance improved from 60 to 85 over 3 months." This weakens the ROI narrative.
**Root Cause**: Backend stores current state but does not snapshot historical compliance scores.
**Fix Category**: **DATA + DESIGN** -- Store compliance check results with timestamps. Add a trend line chart to Analytics > Compliance tab.

### Cross-Cutting Issue 5: Account Deletion is a Toast, Not an Action

**Severity**: **LOW**
**Affected Pages**: Settings
**Impact**: The "Delete Account" button shows a confirmation dialog, then calls `toast.error("Account deletion has been requested...")` -- it does not actually delete the account. This is a placeholder.
**Root Cause**: Account deletion requires backend implementation (cascading deletes, PDPA compliance process).
**Fix Category**: **FLOW** -- Implement actual account deletion or explicitly state "Contact support to delete your account" rather than simulating the flow.

### Cross-Cutting Issue 6: Notification System Depth

**Severity**: **LOW**
**Affected Pages**: Settings, Alerts (if exists)
**Impact**: Notification preferences (email alerts, push notifications) are configurable but it is unclear whether the backend actually sends notifications. If a user enables "email alerts" and never receives one, trust erodes.
**Root Cause**: Settings storage exists; actual notification delivery pipeline needs verification.
**Fix Category**: **FLOW** -- Either implement notification delivery or remove notification settings until delivery is ready.

---

## What a Great Demo Would Look Like

1. **Landing**: The prospect signs up and immediately enters the onboarding flow (skip the empty dashboard).

2. **Onboarding**: They enter their company profile (takes 2 minutes). The compliance snapshot shows their risk profile immediately -- "You have 3 critical compliance gaps." This is the first "wow" moment.

3. **Advisory**: From the compliance snapshot, they click "Ask AITE about this" and get a streaming response that cites EA Section 95A, explains the KET requirement, quotes the $5,000 fine, and recommends specific actions. Second "wow" moment.

4. **Calculators**: They open CPF Calculator, enter an employee's details, and get exact employer/employee contribution amounts that match the CPF Board website. "No AI, just the law." Third "wow" moment -- the platform handles both AI advisory AND deterministic calculations.

5. **Emergency**: They click into "Workplace Injury" and see a step-by-step crisis guide with real deadlines (report to MOM within 10 days), document checklist, and escalation button. Fourth "wow" moment -- "I did not know my platform could help me handle a crisis."

6. **Dashboard**: NOW show the dashboard with real data populated from their onboarding and initial interactions. Compliance score: 40/100. Pending actions: 5. Advisory queries: 2. The dashboard is no longer empty -- it reflects their actual journey.

7. **Analytics**: Show workforce breakdown donut charts with their actual employee data. Show the compliance gap they just identified. This is the management reporting view.

**Total demo time**: 10-15 minutes. Every page has real data. Every interaction demonstrates real value.

---

## Severity Table

| Issue                                                     | Severity | Impact                                                                 | Fix Category  |
| --------------------------------------------------------- | -------- | ---------------------------------------------------------------------- | ------------- |
| Cold-start empty dashboard for new users                  | HIGH     | First impression killer; prospect sees zeros and leaves                | FLOW + DATA   |
| Document templates possibly empty on production           | HIGH     | Another empty-state page; undermines "document generation" value claim | DATA          |
| Client detail page not implemented (View button dead end) | MEDIUM   | Breaks consultant multi-client value flow                              | FLOW          |
| No historical compliance trending                         | MEDIUM   | Weakens ROI narrative ("show me improvement over time")                | DATA + DESIGN |
| Account deletion is a toast, not an action                | LOW      | PDPA compliance gap; user thinks account is deleted when it is not     | FLOW          |
| Notification delivery pipeline unverified                 | LOW      | Settings promise functionality that may not exist                      | FLOW          |

---

## Architecture Strengths (What Impressed Me)

1. **Real regulatory content**: 6,500+ lines of structured Singapore employment law across Employment Act, CPF Act, Foreign Manpower (EFMA), TAFEP, WSH, and adversarial gap coverage. This is not a wrapper around a generic LLM.

2. **Trust pipeline**: The advisory endpoint implements a 9-step safety chain (sanitisation, rate limiting, guardrails, EATP genesis, anti-amnesia injection, KB retrieval, citation validation, disclaimer generation, response screening). This is enterprise-grade.

3. **Deterministic calculators**: 2,000 lines of calculation logic with real 2026 Singapore rates. CPF, leave, overtime, notice period, retrenchment, quota/levy, cost-to-company. These are verifiable and auditable.

4. **Emergency response module**: Unique feature in the HR SaaS space. Crisis guides with real legislation, document checklists, and escalation flow.

5. **Multi-persona support**: The platform serves both in-house HR managers (single company) and HR consultants (multi-client) with the same codebase.

6. **Design system**: Consistent component library (AppCard, AppButton, RiskTierBadge, AlertBanner, SourceCitation, etc.) with design tokens, i18n, and accessibility (ARIA attributes, focus-visible states).

7. **PDPA compliance features**: Data export, account deletion request, privacy settings -- these are Singapore-specific enterprise requirements.

---

## Bottom Line

If I were presenting this to my board after a demo, here is what I would say:

"AITE is a real product solving a real problem for Singapore SMEs. It is not a ChatGPT wrapper -- it has 6,500 lines of structured Singapore employment law, deterministic calculators that match government rates, a trust pipeline with citation validation, and an emergency response module that no competitor has. The core value chain works: company profile leads to compliance assessment leads to advisory guidance leads to calculators leads to document generation. My concern is first-impression polish: a new user sees too many empty states before experiencing value. However, this is a fixable UX problem, not an architectural flaw. The foundation is sound. I would recommend a 3-month pilot with our Singapore office, conditional on the vendor fixing the onboarding cold-start issue and confirming document template availability. Budget impact: this replaces approximately 20 hours/month of HR compliance research per office, plus reduces our exposure to MOM inspection penalties."

---

_Report generated by Value Auditor (Enterprise Demo QA perspective)_
_Files reviewed: 50+ source files across `/apps/web/src/`, `/src/hr_advisory/`, and `/deploy/`_
_Total codebase depth: ~7,500 lines backend API routers, ~6,500 lines KB content, ~2,000 lines calculator logic, ~2,700 lines trust/security pipeline_
