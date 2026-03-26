# Value Audit Report: Arbor HR Advisory Platform

**Date**: 2026-03-21
**Auditor Perspective**: Enterprise CTO evaluating AI-powered HR compliance tool for Singapore SME market. Testers are actively using this system.
**Environment**: https://arbor.terrene.foundation (production, GCE asia-southeast1-b)
**Method**: Live API probing + full codebase analysis + prior audit comparison (March 17)
**Prior Audit**: VALUE_AUDIT_REPORT.md (2026-03-17, on old domain aite.kailash.ai)

---

## Executive Summary

Arbor is a vertically focused AI advisory platform for Singapore employment law with genuine depth: a 13-step safety pipeline, 6 regulatory domains, deterministic CPF/payroll calculators, citation-validated responses with risk tiers, EATP trust chains, and a multi-agent specialist architecture. The codebase is impressively complete -- 60+ DataFlow models, 120+ API endpoints, 40+ frontend pages, 465+ tests.

**However, the platform is currently UNUSABLE for testers.** User registration returns HTTP 500 (Internal Server Error), which means no new tester can create an account, log in, or reach any authenticated feature. Every other evaluation point (advisory chat, calculators, compliance checks, shadow agent) is locked behind authentication that cannot be obtained. This is a showstopper.

**Single highest-impact fix**: Diagnose and repair the user registration endpoint. Until this is fixed, the entire platform is a landing page.

---

## Phase 1: Landing Page (`/`)

### What I See

The landing page loads successfully (HTTP 200). It renders a professional single-page marketing site with:

- Navigation header: Arbor logo, Features/Compliance/Advisory anchor links, Login and "Get Started Free" CTAs
- Feature showcase: ManagementShowcase component listing 10+ HR modules (Payroll, Leave, Claims, Attendance, Shifts, Employees, Documents, Compliance, Reports, Appraisals) with capability bullet points
- Compliance preview section: 6-domain compliance checklist (EA, CPF, EFMA, WSH, TAFEP, Tax/IRAS) with sample coverage status
- Advisory preview section: sample Q&A with source citation pills (EA Part II, Section 10)
- Bottom CTA: "Free for all Singapore SMEs. Set up in under a minute. No credit card required."
- Footer: "Arbor by Terrene Foundation"

### Value Assessment

- **Purpose clarity**: CLEAR -- Within 5 seconds, I know this is an HR management + compliance advisory platform for Singapore SMEs. The value proposition ("stay ahead of Singapore regulations") is specific and believable.
- **Data credibility**: MIXED -- The compliance preview is explicitly labeled "Example" (honest), and the advisory preview shows a truncated sample answer with citation pills. This is appropriate for a marketing page. However, the feature modules list "available" status for 10+ modules -- a tester expects ALL of these to work once they sign up.
- **Value connection**: CONNECTED -- Multiple CTAs point to /signup and /login. Anchor links work within the page.
- **Action clarity**: OBVIOUS -- "Get Started Free" is prominent and repeated. Login for returning users is visible.

### Client Questions

1. "The landing page promises 10+ HR modules. Are all of them actually functional, or are some coming soon?"
2. "You say 'set up in under a minute' -- is company setup actually that fast?"
3. "What does 'free for all Singapore SMEs' mean? Is there a usage cap?"

### Verdict: VALUE ADD

The landing page is well-constructed and tells a clear story. The "free for Singapore SMEs" positioning is strong for the target market. The feature list is ambitious -- the key question is whether the platform delivers once someone signs up.

---

## Phase 2: Registration (`/signup`) -- CRITICAL FAILURE

### What I See

Navigating to /signup renders a clean registration form with:

- Name, email, password, confirm password fields
- Zod validation (min 8 chars for password, email format)
- Google SSO button
- "Already have an account? Login" link
- Invitation token flow for employee onboarding (via URL parameter)

### What Actually Happens

**Registration returns HTTP 500 (Internal Server Error).**

Tested via API:

```
POST /api/auth/register
{"name":"Test User","email":"valueaudit2026@gmail.com","password":"SecurePass123!"}

Response: 500 Internal Server Error
```

Tested multiple times with different email addresses and passwords. The response is consistently "Internal Server Error" -- not the application's custom error message ("Registration failed. Please try again."), which means the error occurs before the endpoint's exception handler can catch it, or the exception message does not match the expected pattern.

**Root cause analysis** (from code):

- The registration endpoint calls `AuthService.register_user()` which calls `_create_user()` which executes a DataFlow `UserCreateNode` workflow against PostgreSQL
- Login returns 401 (correct rejection for invalid credentials), meaning the database READ path works
- The 500 likely indicates a database WRITE failure -- possible causes: connection pool exhaustion under writes, migration not applied (missing column/table), disk full, or a DataFlow node error

**Impact**: No new tester can create an account. The entire platform beyond the landing page is inaccessible.

### Value Assessment

- **Purpose clarity**: CLEAR -- It's a signup form.
- **Data credibility**: N/A -- Cannot assess because registration fails.
- **Value connection**: BROKEN -- The signup form is a dead end. The CTA promise ("Get Started Free") is a lie right now.
- **Action clarity**: OBVIOUS (the form) but BROKEN (the result).

### Client Questions

1. "I clicked 'Get Started Free' and got an error. Is this product actually live?"
2. "How do I get an account to test this?"
3. "If registration has been broken, how long has it been broken? Are your existing testers affected?"

### Verdict: CRITICAL VALUE DRAIN

This is a P0 production incident. The primary conversion funnel (landing page -> signup -> dashboard) is completely broken. Every tester who arrives at the platform right now bounces at this step.

---

## Phase 3: Login (`/login`) -- Accessible but Gate-locked

### What I See

The login form renders correctly with email/password fields, Google SSO button, forgot password link, and signup link. The endpoint correctly returns 401 for invalid credentials (not 500), which confirms the read path to the database is operational.

### Value Assessment

- **Purpose clarity**: CLEAR
- **Data credibility**: REAL -- Auth rejection works correctly.
- **Value connection**: ISOLATED -- Without registration working, existing users can log in but new testers cannot.
- **Action clarity**: OBVIOUS

### Verdict: NEUTRAL (functional but unreachable for new testers)

---

## Phase 4: API Health Check

### What I See

```
GET /api/health
{"status":"healthy","server_type":"enterprise_workflow_server",
 "workflows":{"advisory_query":"healthy","compliance_check":"healthy","search_kb":"healthy"},
 "mcp_servers":{}}
```

The API reports itself as healthy. All three core workflow subsystems (advisory, compliance, KB search) report healthy. MCP servers show empty (expected -- MCP integration is for external connectors).

### Value Assessment

The health check is misleading. It reports "healthy" while user registration (a core workflow) is returning 500. The health check does not test write operations to the database, which is the actual failure point.

### Client Questions

1. "Your health check says 'healthy' but registration is broken. What does 'healthy' actually mean?"
2. "Do you have monitoring that would catch this kind of failure?"

### Verdict: NEUTRAL (exists but does not catch the actual production issue)

---

## Phase 5: Advisory System (Code Analysis -- Cannot Test Live)

Since registration is broken, I cannot test the advisory system through the UI. However, the codebase reveals the full pipeline:

### What the Code Shows

The advisory system is the most impressive part of the codebase. The `/api/advisory/query` and `/api/advisory/stream` endpoints implement a 13-step safety chain:

1. **Input sanitization** -- HTML/script stripping, length validation
2. **Rate limiting** -- Per-user token bucket
3. **Scope screening** -- Detects off-topic queries and redirects politely
4. **Prompt injection detection** -- Pattern matching for injection attempts
5. **Query screening** -- Circumvention and escalation detection
6. **Conversation memory** -- Multi-turn context via ShortTermMemory (LRU bounded at 10,000 conversations)
7. **Company profile fetch** -- Personalizes responses based on company sector, headcount, workforce composition
8. **BYOK LLM context** -- Supports customer-provided API keys with budget tracking
9. **Budget enforcement** -- Monthly $5 free tier with BYOK upgrade path
10. **EATP trust chain** -- Full genesis record, agent attestations, constraint envelope validation
11. **Multi-agent specialist pipeline**: QueryAnalyzer -> DispatchRouter -> Domain Specialists (Employment Act, CPF, Foreign Manpower, Fair Employment, PDPA, Tax, WSH) -> ComplianceAgent -> ResponseSynthesizer
12. **Citation validation** -- Provisions are looked up from the KB and validated before being cited
13. **Response screening** -- Output content safety check

The template fallback system is also substantial -- 1,100+ lines of domain-specific response context covering every major employment law topic with specific statutory references.

### What Would Happen If a Tester Used It

Based on the code:

- Asking "How many days of annual leave am I entitled to?" would:
  - Detect domain: `employment_act`
  - Look up provisions: EA-PART-X-annual-leave, EA-S89-sick-leave, etc.
  - Run through the EmploymentActAgent specialist
  - Return a response citing Part X of the Employment Act with risk tier "green"
  - Show citation pills like [EA Part X] [Statutory] that are clickable
  - Display a confidence score and appropriate disclaimer

- Follow-up "What if I've only worked 3 months?" would:
  - Load the conversation history from ShortTermMemory
  - Pass it to the specialists for context-aware response
  - Correctly note the 3-month qualifying period for annual leave

### Concerning Issues (From Code)

1. **Conversation persistence**: All conversations are stored in Python `OrderedDict` in memory. A server restart wipes ALL conversation history. This was flagged as an "open gap" in the project memory. For testers using the system right now, any backend deployment or restart erases their history.

2. **LLM timeout**: 60-second timeout on the LLM pipeline, with template fallback if it times out. The fallback is high quality but not AI-generated -- testers might notice a quality difference.

3. **Budget tracking is estimated**: Token counts are estimated based on word count multipliers, not actual usage. The comment says "Actual token counts require upstream Kaizen changes (issue #12)."

### Verdict: VALUE ADD (architecturally excellent, but cannot be verified live)

---

## Phase 6: Calculators (Code Analysis -- Cannot Test Live)

### What the Code Shows

7 calculators exist with backend endpoints:

- **CPF Calculator**: Server-side calculation with full age band tiers, PR graduated rates, OW ceiling ($8,000), all citizenship statuses
- **Leave Calculator**: Statutory entitlement by leave type with pro-ration
- **Overtime Calculator**: EA Part IV compliant with $4,500 cap
- **Notice Period Calculator**: Statutory minimums by service length
- **Retrenchment Calculator**: Benefit estimation
- **Cost-to-Company Calculator**: Total employment cost including employer CPF, SDL, FWL, SHG
- **Quota/Levy Calculator**: Foreign worker DRC and levy by sector

The CPF calculator front end correctly calls the backend API (not client-side calculation), shows inline annotations for OW ceiling capping and PR graduated rates, and includes 2026 rate references.

### What Would Happen If a Tester Used It

For a $5,000/month salary, age 30, Singapore Citizen:

- Employer CPF: $850 (17%)
- Employee CPF: $1,000 (20%)
- Total CPF: $1,850 (37%)
- OA/SA/MA allocation breakdown
- Notes about OW ceiling and rate year

This is deterministic -- zero LLM, pure arithmetic. High reliability, high value.

### Verdict: VALUE ADD (strong utility, high accuracy, but inaccessible)

---

## Phase 7: Compliance System (Code Analysis -- Cannot Test Live)

### What the Code Shows

The compliance page offers:

- Status dashboard showing 5 regulatory domains with coverage status (covered/sparse/missing)
- "Run Compliance Check" button that executes a backend check
- Client-side inspection readiness checklist
- Findings with severity levels (critical/high/medium/low), recommendations, and deadlines
- Source citations with authority levels
- "Ask Arbor" integration for domain-specific questions

### Verdict: VALUE ADD (good design, cannot verify live)

---

## Phase 8: Shadow Agent (Code Analysis)

### What the Code Shows

The shadow agent consists of:

- **ShadowWidget**: A 36px floating button (bottom-right) with breathing animation and Ctrl+Shift+A shortcut
- **CommandSurface**: A slide-up command palette for quick queries, calculations, and navigation
- **ShadowBriefingCard**: Time-aware greeting on the dashboard with contextual action suggestions
- **InlineAnnotation**: Contextual annotations on calculator results and compliance findings
- **ShadowMargin**: A right-side margin for page-level insights
- **ArborOverlay/ArborResult/ArborHistory**: Full result display with citation support

The shadow agent can dispatch to calculators directly (CPF, leave, overtime calculations from the command surface), navigate to pages, and answer quick questions via the advisory API.

### Concerning Issues

1. **Observation pipeline not wired**: The project memory notes "observation pipeline not wired (client -> server)" -- the shadow agent cannot observe user actions on pages and proactively surface relevant guidance
2. **InlineAnnotation not rendered on pages**: Also noted as an "open gap" -- inline annotations exist as components but are not consistently surfaced across pages
3. **Undo is guidance-only**: The shadow agent cannot actually undo actions, only advise

### Verdict: NEUTRAL (impressive architecture but the "shadow" aspect -- proactive, observational intelligence -- is not yet functional)

---

## Value Flow Analysis

### Flow 1: New Tester -> Get Value

**Steps Traced**:

1. Landing page (/) -> Clear CTA -> Click "Get Started Free"
2. Signup (/signup) -> Fill form -> Click "Create Account"
3. **BROKEN** -> HTTP 500 Internal Server Error
4. Dashboard (/dashboard) -> **UNREACHABLE**
5. Advisory (/advisory) -> **UNREACHABLE**

**Flow Assessment**:

- Completeness: BROKEN AT STEP 2
- Narrative coherence: STRONG (the promise is clear and compelling)
- Evidence of value: ABSENT (no tester can see any authenticated feature)

**Where It Breaks**: The database write path for user creation fails silently.

### Flow 2: Existing User -> Advisory Value (Hypothetical)

**Steps Traced** (from code analysis):

1. Login -> Dashboard with briefing card, compliance metrics, quick actions
2. Click "Ask a question" -> Advisory page
3. Type question -> SSE stream begins with phased thinking indicator
4. Response renders with risk tier badge, confidence score, citation pills
5. Click citation -> ProvisionViewer modal with formal text, plain summary, practical examples
6. Follow-up question -> Context carries over via ShortTermMemory

**Flow Assessment**:

- Completeness: COMPLETE (in code)
- Narrative coherence: STRONG -- each step builds on the last
- Evidence of value: THEORETICAL (cannot demonstrate live)

### Flow 3: Dashboard -> Compliance -> Remediation

**Steps Traced** (from code analysis):

1. Dashboard shows compliance score, pending actions by domain
2. Click "View details" -> Compliance page with domain breakdown
3. "Run Compliance Check" -> Backend generates findings with severity
4. Findings show recommendations and deadlines
5. "Ask Arbor" button on findings -> Pre-fills advisory with domain question

**Flow Assessment**:

- Completeness: COMPLETE (in code)
- Narrative coherence: STRONG
- Evidence of value: THEORETICAL

---

## Cross-Cutting Issues

### Issue 1: Registration Broken (HTTP 500)

**Severity**: CRITICAL
**Affected Pages**: /signup, and transitively ALL authenticated pages
**Impact**: No new tester can use the platform. The entire demo funnel is broken.
**Root Cause**: Database write failure in `AuthService._create_user()` via DataFlow `UserCreateNode`. The read path (login check) works, so the database connection exists but write operations fail. Possible causes: migration not applied, disk full, connection pool exhaustion on writes, or a DataFlow node configuration error.
**Fix Category**: INFRASTRUCTURE

### Issue 2: Conversation Persistence (In-Memory Only)

**Severity**: HIGH
**Affected Pages**: /advisory, conversation history
**Impact**: Every server restart erases all conversation history. Testers lose their conversation threads without warning. In a deployment cycle (which happened today per git log), all history is wiped.
**Root Cause**: `_conversation_memory`, `_conversation_titles`, and `_conversation_owners` are Python `OrderedDict` instances in module scope -- pure in-memory, no persistence layer.
**Fix Category**: DATA (needs database-backed conversation store)

### Issue 3: Health Check Does Not Detect Registration Failure

**Severity**: HIGH
**Affected Pages**: /api/health (monitoring)
**Impact**: The health check reports "healthy" while a critical user flow is broken. This means the team has no automated alert for this failure.
**Root Cause**: Health check only verifies advisory_query, compliance_check, and search_kb workflows. It does not test auth/registration write path.
**Fix Category**: INFRASTRUCTURE (add write-path health check)

### Issue 4: Shadow Agent Observation Pipeline Not Wired

**Severity**: MEDIUM
**Affected Pages**: All pages (shadow agent is global)
**Impact**: The shadow agent cannot observe what the user is doing on a page and proactively surface relevant information. It is currently reactive-only (user must explicitly invoke it). The "shadow" metaphor loses its meaning.
**Root Cause**: Client-to-server observation events are not implemented.
**Fix Category**: FEATURE

### Issue 5: Token Usage Estimation (Not Actual)

**Severity**: MEDIUM
**Affected Pages**: Advisory (budget tracking)
**Impact**: Budget tracking is based on word-count estimation with multipliers, not actual token counts. For BYOK users this is irrelevant (they pay their provider directly). For free-tier users, inaccurate estimation could prematurely exhaust their $5/month budget or allow overuse.
**Root Cause**: Kailash Kaizen does not expose token counts from agent runs (referenced as issue #12).
**Fix Category**: DATA (upstream dependency)

### Issue 6: Google SSO Configuration

**Severity**: LOW
**Affected Pages**: /signup, /login
**Impact**: The Google SSO button exists on both pages but the OAuth exchange endpoint returns "Failed to exchange Google authorization code." If testers try Google SSO, they get an error.
**Root Cause**: Likely missing or misconfigured Google OAuth client credentials on the server.
**Fix Category**: INFRASTRUCTURE

---

## What a Great Demo Would Look Like

### For a Tester Arriving Right Now

1. **Landing page**: (Already good) -- Clear value proposition, Singapore SME focus, feature overview.

2. **Instant signup**: Click "Get Started Free", fill 3 fields, account created in under 10 seconds. Redirect to dashboard.

3. **Guided first experience**: Dashboard greets by name with a time-aware briefing ("Good afternoon, [Name]"). Three getting-started steps are visible. The first step ("Create your company profile") opens a modal with sector selection and basic info.

4. **Immediate value -- even without company setup**: The advisory chat is accessible immediately. The tester types "How many days of annual leave do my employees get?" and within 3 seconds sees a streaming response citing Part X of the Employment Act, with clickable citation pills showing formal text and plain-language summaries.

5. **Calculator proof point**: The tester clicks "Run a calculation" -> CPF Calculator -> enters $5,000 salary, age 30 -> sees exact breakdown: $850 employer, $1,000 employee, OA/SA/MA split. Zero ambiguity, zero AI hallucination.

6. **Compliance check**: After setting up company profile, the tester runs a compliance check and sees their coverage across 6 domains with specific findings and remediation steps.

7. **Shadow agent "aha moment"**: While viewing payroll, the shadow widget pulses to indicate "I noticed you haven't set up CPF submission. Here's what you need to know." The proactive, contextual intelligence demonstrates the "shadow" concept.

### What Is Missing Right Now

- Step 2 is broken (registration 500)
- Steps 3-6 cannot be reached by new testers
- Step 7 (proactive shadow) is not yet wired

---

## Severity Table

| #   | Issue                                    | Severity     | Impact                                   | Fix Category    | Estimated Effort              |
| --- | ---------------------------------------- | ------------ | ---------------------------------------- | --------------- | ----------------------------- |
| 1   | Registration returns 500                 | **CRITICAL** | Platform unusable for new testers        | Infrastructure  | 1-2 hours (diagnose + fix)    |
| 2   | Conversation history in-memory only      | HIGH         | History lost on every deploy/restart     | Data            | 4-8 hours (DB-backed store)   |
| 3   | Health check misses registration failure | HIGH         | No automated detection of current outage | Infrastructure  | 1 hour                        |
| 4   | Shadow agent observation not wired       | MEDIUM       | "Shadow" concept not demonstrated        | Feature         | 8-16 hours                    |
| 5   | Token usage estimation vs actual         | MEDIUM       | Budget tracking inaccurate               | Data (upstream) | Blocked on Kaizen issue #12   |
| 6   | Google SSO not configured                | LOW          | SSO button is a dead end                 | Infrastructure  | 1 hour (if credentials exist) |

---

## Comparison with Prior Audit (March 17)

The March 17 audit (on the old aite.kailash.ai domain) rated the platform positively and identified the "cold-start emptiness" as the top issue. Since then:

**Improvements made**:

- Shadow agent fully implemented (M61-M65: 12 backend modules, 13 API endpoints, 9 frontend components)
- Proactive token refresh to prevent silent 401 failures
- LLM timeout (60s) with KB fallback
- Bounded conversation stores (10K LRU eviction)
- Domain renamed from AITE to Arbor with new domain

**New regression**:

- Registration endpoint is now broken (was not broken on March 17)
- This is worse than the cold-start emptiness -- at least the March 17 platform let testers sign up

**Still open from March 17**:

- Conversation persistence (still in-memory)
- Shadow observation pipeline (still not wired)

---

## Bottom Line

Arbor is a deeply impressive vertical AI platform. The advisory safety chain (13 steps, multi-agent pipeline, citation validation, trust chains) is beyond what most enterprise AI products ship. The deterministic calculators are production-ready. The regulatory knowledge base covers 6 Singapore domains with statutory precision. The architecture supports BYOK API keys, budget enforcement, and tenant isolation.

But none of that matters right now because testers cannot create accounts.

The platform is one database fix away from being demonstrably excellent. The registration 500 is likely a trivial infrastructure issue (migration, disk, connection config) that masks an otherwise complete and well-built product. Fix registration, add a write-path health check so this never happens undetected again, and then tackle conversation persistence. The shadow agent observation pipeline and token estimation are polish items that can follow.

If I were advising the board: this product has real depth and genuine regulatory expertise. It is not a ChatGPT wrapper. But I would not recommend it to any tester until the registration is confirmed working, because the first impression right now is "it's broken."

**Priority actions, in order**:

1. SSH into arbor-prod, check backend logs for the registration 500 root cause, fix it
2. Add a registration write-path check to /api/health
3. Test the full signup->advisory->calculator flow end-to-end on production
4. Only then notify testers that the platform is ready
