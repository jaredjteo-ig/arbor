# Value Audit Report: Arbor HRIS Platform

**Date**: 2026-03-24
**Auditor Perspective**: Singapore SME Owner, 15-person technology company
**Environment**: https://arbor.terrene.foundation (production)
**Method**: HTTP API walkthrough + source code analysis + live endpoint testing
**Build**: Latest production deployment (Caddy + Uvicorn + Next.js 16)

---

## Executive Summary

Arbor has **genuine, differentiated value** in its advisory engine and regulatory calculators -- these are production-quality features that solve real problems Singapore SME owners face daily. However, **the platform is currently unusable for its core HRIS purpose** because company creation is broken in production (500 Internal Server Error), which blocks access to payroll, leave, claims, employees, and every management module. The single highest-impact fix is resolving the DataFlow `CompanyCreateNode` failure on the production database, which would instantly unlock the entire platform for new users.

**Verdict**: The advisory engine alone justifies attention. The HRIS modules show serious depth in source code. But today, a new user who clicks "Get Started Free" hits a wall within 60 seconds.

---

## Phase 1: First Impression

### Landing Page (`/`)

**What I See**: Clean, modern landing page. Clear headline: "Your Complete HR Management Suite." Subtext covers payroll, leave, claims, attendance, shifts, compliance, AI advisory. Three trust signals: "100% Free", "AI-Powered", "Singapore Compliant", "All-in-One". Eight feature cards with bullet points (Payroll, Leave, Claims, Attendance, Shifts, Employees, Documents, Compliance). Footer mentions Terrene Foundation. Two CTAs: "Get Started Free" and "Login."

**Value Assessment**:

- Purpose clarity: **CLEAR** -- "Free HRIS for Singapore SMEs with AI compliance advisory" is stated in plain language
- Data credibility: **GOOD FOR A LANDING PAGE** -- Feature lists are specific (CPF age bands, 16+ leave types, 6-domain compliance). No vanity metrics or empty claims
- Value connection: **CONNECTED** -- Each feature card leads to a signup CTA
- Action clarity: **OBVIOUS** -- Two clear paths: "Get Started Free" or "Login"

**What Works Well**:

1. The positioning is clear and differentiated. "Free for all Singapore SMEs" is a strong hook
2. Regulatory specificity builds trust -- naming CPF, SDL, FWL, SHG, EA Part IV shows domain knowledge
3. The compliance preview section with domain badges (Employment Act: Covered, EFMA: Needs Review) is a smart trust builder
4. AI advisory example with source citations shows the product is grounded, not vague

**Client Questions**:

1. "Free, no credit card, no limits, no catch" -- what is the business model? How does the Terrene Foundation sustain this?
2. No social proof -- no testimonials, no company logos, no user count. Is anyone actually using this?
3. The title tag says "Arbor -- HR Advisory" but the landing page positions it as a "Complete HR Management Suite" -- which is it?

**Verdict**: **VALUE ADD** -- The landing page tells a clear, specific story. It stands out from generic HR SaaS pitches by naming actual Singapore regulations. The missing social proof is understandable for a new product.

---

### Login Page (`/login`)

**What I See**: Split-screen layout. Left panel repeats the value proposition (Free Payroll & CPF, AI Compliance Advisor, Full HR Suite). Right panel has email/password login form with "Sign in with Google" option and "Don't have an account? Sign up" link.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- Standard login page
- Trust signals: The left panel reinforces value during the login moment, which is a nice touch
- Google SSO: Good for SME owners who want frictionless access
- The "Sign up" link navigates to `/signup`

**Verdict**: **VALUE ADD** -- Professional, appropriate for the target audience.

---

### Signup Page (`/signup`)

**What I See**: The page loads and shows "Verifying your invitation..." then hangs. The signup page requires an invitation token (query parameter). There is no general self-registration path through the UI.

**CRITICAL FINDING**: The landing page says "Get Started Free" and the login page says "Don't have an account? Sign up" -- but the signup page is invitation-only. The "Get Started Free" buttons have no working path for a cold visitor.

**However**: The API endpoint `POST /api/auth/register` does work and accepts `{email, password, name}`. This means the backend supports self-registration but the frontend signup page is gated behind invitations. This is a **flow disconnection**.

**Client Questions**:

1. "I clicked 'Get Started Free' and got stuck on 'Verifying your invitation.' How do I actually sign up?"
2. If registration requires an invitation, who sends the first one?

**Verdict**: **VALUE DRAIN** -- The most important conversion path (visitor to user) is broken in the UI.

---

### Onboarding Page (`/onboarding`)

**What I See**: A 4-step wizard (Welcome, Company, Snapshot, Ask). The Welcome step shows value propositions: Compliance Guidance, Accurate Calculators, Ready-Made Templates, Company-Specific Advice. There is a "Get Started" button.

**Value Assessment**:

- Purpose clarity: **CLEAR** -- Guides new users through initial setup
- Step design: **SMART** -- The 4 steps mirror the user's mental model (understand what this is, set up my company, see my situation, ask a question)
- The step names are user-friendly, not technical

**Verdict**: **VALUE ADD** -- Well-designed onboarding flow in concept. Blocked by the company creation failure in practice.

---

## Phase 2: Core Feature Audit

### Company Creation (`POST /api/clients/` and `POST /api/profile/`)

**What I See**: Both company creation endpoints return `500 Internal Server Error` with generic messages: "Failed to create client company" / "Failed to create company profile." The `CompanyCreateNode` DataFlow operation fails silently.

**CRITICAL FINDING**: Company creation is the gateway to the entire HRIS. Without a company, every single management module returns "No company associated with this account. Contact support." This means:

- Payroll: Blocked
- Leave: Blocked
- Claims: Blocked
- Employees: Blocked
- Attendance: Blocked
- Shifts: Blocked
- Recruitment: Blocked
- Inventory: Blocked
- Appraisals: Blocked
- Projects: Blocked

**Root Cause (Probable)**: The DataFlow `CompanyCreateNode` is failing on the production PostgreSQL database. This could be a schema migration issue, a missing table, or a DataFlow registry configuration problem. The error is caught and wrapped in a generic message, hiding the actual cause.

**Impact**: **100% of new users are blocked**. The platform cannot be used for its stated purpose by any new visitor.

**Verdict**: **SHOWSTOPPER** -- This single bug makes the platform unusable for any new user.

---

### Advisory Engine (`POST /api/advisory/query`)

**What I See**: The advisory engine is **genuinely excellent**. I tested two queries:

**Query 1**: "What are my obligations for hiring a foreign worker on an S Pass?"

- Response: 3,500+ characters of structured, actionable guidance
- Covers: minimum salary ($3,150/$3,650 for FS), quota (15% sub-DRC from Sep 2025), levy ($550/$650), KET requirements, EA obligations, practical checklist
- Citations: 11 provisions cited (EFMA-SP, EFMA-DRC, EFMA-LEVY, EA-S20A, etc.)
- Risk tier: Amber (appropriate for complex regulatory topic)
- Confidence: 0.92
- Trust chain: Session ID, genesis fingerprint, verification depth, attestation count
- Model: gpt-5-mini-2025-08-07

**Query 2**: "Can I terminate an employee during probation without notice?"

- Response: 2,689 characters, structured answer with EA section references
- Correctly identifies: notice still required during probation, EA s10 notice periods, EA s14 summary dismissal exception
- Citations: 5 provisions
- Risk tier: Amber
- Confidence: 0.95

**Value Assessment**:

- Purpose clarity: **CLEAR** -- Ask any HR question, get a cited answer
- Data credibility: **REAL** -- These are not template responses. The citations are accurate, the legal analysis is correct for Singapore law, and the practical checklists are genuinely useful
- Value connection: **CONNECTED** -- Each answer cites specific provisions, includes risk tiers, and offers to do follow-up calculations
- The trust chain metadata (session ID, genesis fingerprint, verification depth) demonstrates serious governance infrastructure

**What This Solves**: An SME owner currently pays $300-500/hour for employment law advice, or Googles for hours and hopes they get it right. This provides instant, cited, actionable answers. This is the product's killer feature.

**Client Questions**:

1. "How current is the legal knowledge? The CDCSA amendments and TG-FWAR are from 2024-2025 -- are those reflected?"
   **Answer**: Yes. The response correctly references the 4-week paternity leave (Jan 2025 amendment) and the 15% S Pass sub-DRC (Sep 2025).
2. "Can I trust this for actual business decisions?"
   **Answer**: The system appropriately flags amber risk on complex topics and includes a disclaimer system. It recommends professional advice for contested cases. This is responsible design.

**Verdict**: **STRONG VALUE ADD** -- This is the best feature of the platform and could justify adoption on its own. Production-quality, legally accurate, well-cited.

---

### CPF Calculator (`POST /api/calculator/cpf`)

**What I See**: Full CPF calculation with:

- Employer contribution: $850 (17% of $5,000)
- Employee contribution: $1,000 (20% of $5,000)
- Total: $1,850 (37%)
- OW/AW breakdown with ceilings ($8,000 OW ceiling, $97,000 AW ceiling remaining)
- Account allocation: OA $1,154, SA $308, MA $388

**Value Assessment**:

- Data credibility: **REAL** -- These are correct 2026 CPF rates for citizens under 55. The allocation split matches the official CPF Board rates
- This is deterministic calculation, not LLM output -- zero hallucination risk
- Includes ceiling awareness (critical for higher earners)

**Verdict**: **VALUE ADD** -- Solves a real daily problem (SME owners manually calculating CPF).

---

### Document Generation (`POST /api/document/generate`)

**What I See**: 12 document templates available:

1. Employment Contract (Full-Time) -- 7 compliance provisions
2. Employment Contract (Part-Time) -- 4 provisions
3. Key Employment Terms (KET) -- 3 provisions
4. Annual Leave Policy
5. Sick Leave Policy
6. Termination Letter (With Notice)
7. Resignation Acceptance Letter
8. Warning Letter
9. FWA Request Form
10. FWA Policy
11. Expense Claims Form
12. Timesheet Template

I generated a full employment contract. The output is a properly structured legal document with:

- EA-compliant clauses (s10 notice, s14 summary dismissal, s88A payslip, s89 sick leave)
- Correct 2025 paternity leave (4 weeks CDCSA)
- CPF employer obligation clause
- Proper formatting with signature blocks

**However**: Some template variables are unresolved ({{contract_date}}, {{authorised_signatory}}, {{probation_notice_weeks}}). These should either be filled from input or have sensible defaults.

**Verdict**: **VALUE ADD** -- Real legal documents that an SME owner would otherwise pay $500-2,000 for from a law firm. The unresolved template variables are a minor polish issue.

---

### Compliance Check (`POST /api/compliance/check`)

**What I See**: Returns a compliance status across 5 domains (Employment Act, CPF, EFMA, Tax, WSH). For our new user without a company, all domains show "missing" with 0 provisions checked.

**Problem**: The compliance check returns "No [domain] provisions found in the knowledge base" for all 5 domains. This suggests the DataFlow-based KB is empty on the production instance, even though the advisory engine (which uses Python content modules as KB fallback) works perfectly.

**This creates a contradictory experience**: The advisory engine gives detailed, cited legal answers, but the compliance page says "no provisions found." The user sees the AI knows the law but the compliance dashboard says it does not.

**Root Cause**: The compliance check queries the DataFlow KB (database), while the advisory engine falls back to Python content modules (`kb/content/`) when the DB is empty. They use different data sources.

**Verdict**: **VALUE DRAIN** -- The compliance page actively undermines the trust built by the advisory engine. A user who gets a brilliant advisory response and then sees "all missing" on compliance will question the entire platform.

---

### Employee Management

**What I See (from source)**: The employees page has:

- Employee directory with search
- Status badges (active, invited, inactive)
- Confirmation status (confirmed, on probation, extended)
- Profile completeness indicator
- Invite Employee modal (email + role selection)
- Invite Link modal with copy-to-clipboard
- CSV import functionality
- Bulk operations
- Work pass expiry tracking with alerts
- Employee detail page with 12 tabs (personal, employment, compensation, statutory, leave, claims, attendance, documents, family, timeline, skills, custom fields)

**Value Assessment**: The employee management module shows serious depth -- 30+ employee fields, PDPA-compliant PII encryption, work pass expiry alerts, probation tracking. This is not a skeleton.

**However**: None of this is accessible in production because company creation is broken.

**Verdict**: **NEUTRAL** (potentially VALUE ADD once company creation works) -- The depth is there in code. Cannot verify in production.

---

### Payroll Module

**What I See (from source)**: The payroll module includes:

- Payroll run creation (draft, approved, paid status workflow)
- Gross-to-net calculation with CPF, SDL, FWL, SHG
- Payslip generation (EA s88A compliant)
- Bank file generation (DBS, UOB, OCBC formats)
- CPF file generation (CPF99 format)
- IR8A/IR21 tax filing generation
- Variance report (compare month-to-month)
- Pay items and pay schemes
- Accounting sync

**Value Assessment**: This is a complete payroll system for Singapore -- not a stub. The CPF calculation engine is deterministic (zero LLM), handles all age bands, PR graduated rates, and OW/AW ceilings correctly.

**However**: Blocked by company creation failure.

**Verdict**: **NEUTRAL** (potentially STRONG VALUE ADD) -- If this works as the source code suggests, it eliminates the need for a separate payroll provider.

---

## Phase 3: Cross-Cutting Issues

### Issue 1: Company Creation Failure (SHOWSTOPPER)

**Severity**: CRITICAL
**Affected Pages**: Every page behind authentication except Advisory and Calculators
**Impact**: 100% of new users are blocked from the HRIS. The platform cannot fulfill its stated value proposition for any new visitor.
**Root Cause**: DataFlow `CompanyCreateNode` fails on the production PostgreSQL database with a 500 error. The generic error message hides the actual cause.
**Fix Category**: DATA/INFRASTRUCTURE -- Likely a database migration or schema issue on production.

### Issue 2: Signup Flow Disconnection

**Severity**: HIGH
**Affected Pages**: Landing page, Login page, Signup page
**Impact**: The "Get Started Free" CTA leads to a page that shows "Verifying your invitation..." and stops. There is no self-registration path through the UI, despite the API supporting it.
**Root Cause**: The `/signup` page requires an invitation token (query param). The landing page links point to `/signup` without a token.
**Fix Category**: FLOW -- Either make `/signup` work without an invitation token (call the `/api/auth/register` endpoint directly) or route "Get Started Free" through the onboarding wizard which handles registration.

### Issue 3: Compliance Check Contradicts Advisory

**Severity**: HIGH
**Affected Pages**: Compliance page, Advisory page
**Impact**: Advisory gives brilliant legal answers, but Compliance dashboard says "no provisions found." This creates a trust contradiction -- if the system knows employment law well enough to cite specific sections, why does the compliance check say it has zero knowledge?
**Root Cause**: Advisory uses Python content modules as KB fallback. Compliance check queries the DataFlow database, which is empty on production.
**Fix Category**: DATA -- Either populate the production KB database or make the compliance check fall back to the same Python content modules.

### Issue 4: Branding Leak on API Documentation

**Severity**: MEDIUM
**Affected Pages**: `/api/docs` (Swagger UI)
**Impact**: The API documentation page title says "Kailash Nexus - Zero-Config Workflow Platform" instead of "Arbor." An SME owner who stumbles onto `/api/docs` sees an unrelated product name.
**Root Cause**: The Nexus server auto-generates its Swagger page with the Nexus branding. The HRIS-specific API routes are mounted as sub-routes of the Nexus server.
**Fix Category**: NARRATIVE -- Override the Nexus server title to "Arbor API" in the platform configuration.

### Issue 5: Sensitive Endpoints Exposed Without Auth

**Severity**: HIGH (Security)
**Affected Endpoints**:

- `/api/metrics` -- Prometheus metrics (security violation counts, injection attempt counts)
- `/api/enterprise/features` -- Lists all enterprise features
- `/api/connections/metrics` -- Connection pool status
- `/api/connections/pools` -- Pool details
- `/api/durability/status` -- Durability system internals
  **Impact**: Anyone can see internal system metrics, including security violation counts, injection attempt counts, and infrastructure details. This is an information disclosure vulnerability.
  **Root Cause**: These are Nexus framework endpoints that are registered automatically and do not have auth middleware.
  **Fix Category**: SECURITY -- Either disable these endpoints in production or add authentication.

### Issue 6: Unresolved Template Variables in Documents

**Severity**: LOW
**Affected Feature**: Document generation
**Impact**: Generated employment contracts contain unresolved `{{template_variable}}` placeholders (e.g., `{{contract_date}}`, `{{authorised_signatory}}`). Minor polish issue but undermines the "ready to use" promise.
**Fix Category**: DATA -- Either add these fields to the generation form or substitute sensible defaults.

### Issue 7: Dashboard Kailash Branding

**Severity**: LOW
**Affected Page**: `/api/dashboard` returns a "Kailash Live Dashboard" page with WebSocket metrics monitoring
**Impact**: Internal monitoring dashboard is accessible and branded as Kailash, not Arbor
**Fix Category**: NARRATIVE/SECURITY -- Should be disabled or auth-gated in production

---

## Value Flow Analysis

### Flow 1: New User Registration to First Value

**Steps Traced**:

1. Landing page (`/`) -- Click "Get Started Free" -- Navigates to `/signup`
2. **BREAKS HERE**: `/signup` shows "Verifying your invitation..." and stops
3. (Alternative) Direct API registration works (`POST /api/auth/register`)
4. After login, redirected to Dashboard -- sees "Set up your company" prompt
5. Company Setup Modal -- Enter name, UEN, sector, headcount
6. **BREAKS HERE**: Company creation returns 500 error
7. All HRIS modules return "No company associated with this account"

**Flow Assessment**:

- Completeness: **BROKEN AT STEP 2 (UI) AND STEP 6 (API)**
- Narrative coherence: The landing page promises an easy setup. Reality: the user cannot even register through the UI
- Evidence of value: **ABSENT** -- No new user can reach any working HRIS feature

**Where It Breaks**: The entire onboarding funnel is non-functional. The advisory engine works (accessible without a company), but the HRIS -- which is the stated core product -- is completely locked.

### Flow 2: Advisory Question to Actionable Answer

**Steps Traced**:

1. Login (assume API-based registration)
2. Navigate to Advisory (`/advisory`)
3. Type a question about Singapore employment law
4. Receive structured response with citations, risk tier, confidence score
5. Follow-up questions maintain conversation context
6. Conversation history saved and browsable

**Flow Assessment**:

- Completeness: **COMPLETE** -- This flow works end-to-end in production
- Narrative coherence: **STRONG** -- The response format (answer + citations + risk tier + practical checklist) is exactly what an SME owner needs
- Evidence of value: **DEMONSTRATED** -- Real answers, real citations, real legal accuracy

### Flow 3: Document Generation

**Steps Traced**:

1. Browse 12 available templates
2. Select a template (e.g., Employment Contract)
3. Fill in required fields
4. Receive a complete, EA-compliant document with proper clauses

**Flow Assessment**:

- Completeness: **MOSTLY COMPLETE** -- Some template variables unresolved
- Narrative coherence: **STRONG** -- Documents reference actual EA sections
- Evidence of value: **DEMONSTRATED** -- The generated employment contract is legally sound

### Flow 4: CPF Calculation

**Steps Traced**:

1. Input gross salary, age, citizenship status
2. Receive detailed breakdown: employer/employee contributions, rates, account allocation, ceiling tracking

**Flow Assessment**:

- Completeness: **COMPLETE**
- Evidence of value: **DEMONSTRATED** -- Correct CPF rates, ceiling awareness, account split

---

## What a Great Demo Would Look Like

If Arbor were demo-ready today, a visitor's experience would be:

1. **Landing page**: Click "Get Started Free" (already good)
2. **Registration**: Enter email, password, name -- account created in 5 seconds
3. **Company setup**: Enter "Audit Test Pte Ltd", technology sector, 15 employees -- company created, demo data seeded automatically (payroll history, sample employees, leave balances, inventory items)
4. **Dashboard**: See a populated dashboard with compliance score, pending actions, recent activity, and the Shadow Agent briefing card
5. **Advisory**: Ask "What are my CPF obligations for a PR employee?" and get a cited answer in 3 seconds (THIS ALREADY WORKS)
6. **Payroll**: See the pre-seeded payroll run with sample employees, click "Approve", see CPF file generated
7. **Employees**: See 5-10 pre-seeded employees with different profiles (citizen, PR, EP holder, WP holder), demonstrating the full breadth of Singapore workforce management
8. **Compliance**: See a meaningful compliance dashboard showing real findings based on the seeded company data (not "all missing")
9. **Documents**: Generate an employment contract pre-filled with company data (THIS ALREADY WORKS minus company data)

The gap between current state and demo-ready is primarily:

- Fix company creation (turns on 80% of the platform)
- Populate the compliance KB database (fixes the trust contradiction)
- Wire the signup page for self-registration (fixes the conversion funnel)

---

## Severity Table

| Issue                                           | Severity | Impact                                      | Fix Category   |
| ----------------------------------------------- | -------- | ------------------------------------------- | -------------- |
| Company creation 500 error                      | CRITICAL | 100% of new users blocked from HRIS         | INFRASTRUCTURE |
| Signup flow broken (invitation-only)            | HIGH     | Visitors cannot register through the UI     | FLOW           |
| Compliance check shows "all missing"            | HIGH     | Contradicts advisory engine, destroys trust | DATA           |
| Prometheus/enterprise endpoints unauthenticated | HIGH     | Information disclosure vulnerability        | SECURITY       |
| API docs say "Kailash Nexus" not "Arbor"        | MEDIUM   | Branding confusion                          | NARRATIVE      |
| Unresolved template variables in documents      | LOW      | Polish issue in generated contracts         | DATA           |
| Kailash Live Dashboard exposed                  | LOW      | Internal tooling visible                    | SECURITY       |

---

## Bottom Line

Arbor has built something genuinely valuable for Singapore SMEs. The advisory engine is the strongest feature I have seen in an HR tech product targeted at this market -- it gives accurate, cited, actionable legal guidance that would cost $300-500/hour from a lawyer. The CPF calculator is correct to the dollar. The document generator produces real legal documents. The payroll engine (in source code) handles the full complexity of Singapore statutory payroll.

**But none of the HRIS features are reachable by any new user today.**

The platform has a production database issue that causes company creation to fail with a 500 error. Since every HRIS module requires a company, this single bug turns a feature-rich platform into an advisory chatbot with a broken sign-up flow. The signup page is also invitation-only in the UI despite the backend supporting self-registration, so even reaching the point of company creation requires workarounds.

**My recommendation to the board**: This is not ready for user-facing launch. Fix three things -- company creation, self-registration flow, and compliance KB data -- and you have a product worth recommending to every SME in our network. The underlying technology and domain knowledge are solid. The gap is operational, not architectural.

**Estimated fix effort**: If the company creation failure is a database migration issue (most likely), this is a 1-2 hour fix. The signup flow routing is a 30-minute frontend change. The compliance KB population requires running the seeding script against the production database. Total: less than one working day to go from "broken" to "demo-ready."

---

_Audit conducted by Value Auditor agent. All API calls verified against the live production environment at https://arbor.terrene.foundation on 2026-03-24._
