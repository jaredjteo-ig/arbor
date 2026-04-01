# Ricoh Thailand Demo — Complete Roadmap

**Objective**: Deploy Arbor as a standalone commercial demo on a new instance with Gemini API, showcase to Ricoh Thailand CCO on Friday 2026-03-28.
**Workspace**: `workspaces/ricoh-demo/`
**Analysis**: `01-analysis/01-research/` (11 documents)
**Constraint**: Singapore content is acceptable — this is an architecture/governance showcase.

---

## M1: Gemini API Migration

The platform already has multi-provider infrastructure (`VALID_PROVIDERS` includes `"gemini"`, UI dropdown lists it, streaming is provider-agnostic). The work is rewriting 5 files with direct OpenAI SDK calls.

**Decision required before starting**: LiteLLM abstraction (recommended, 1-2 days) vs Direct Gemini SDK (3-5 days) vs OpenAI-compatible endpoint (1 day, risky). See `01-analysis/01-research/11-redeployment-analysis.md` section 1.3 for trade-offs.

### T001: Investigate Kaizen framework Gemini support

**What**: Before choosing the migration approach, verify if Kailash Kaizen supports Gemini natively.

**Files to check**:

- `src/hr_advisory/agents/config.py:82-138` — monkey-patches `kaizen.config.providers.get_openai_config()`
- Kaizen framework documentation / source for provider support

**Outcome**: Determines if we need LiteLLM as bridge or can use Kaizen's native provider system.

### T002: Add LiteLLM dependency and provider abstraction

**What**: Install LiteLLM and create a thin wrapper that all LLM calls route through. This makes the Gemini switch a config change rather than a rewrite.

**Files**:

- `pyproject.toml:51` — Add `litellm` dependency alongside (not replacing) `openai`
- New file: `src/hr_advisory/agents/llm_provider.py` — Central LLM call function that wraps LiteLLM
- `src/hr_advisory/config/settings.py:32-35` — Add Gemini model defaults

**Skip if**: Decision is to use Direct Gemini SDK or OpenAI-compatible endpoint instead.

### T003: Migrate advisory engine function calling to Gemini

**What**: The advisory engine has 214 lines of OpenAI tool definitions (lines 28-242) and OpenAI-specific response parsing (lines 609-673) including `choice.message.tool_calls`, `finish_reason == "tool_calls"`, `tool_call.function.name`.

**File**: `src/hr_advisory/agents/advisory_engine.py`
**Lines**: 28-242 (tool definitions), 609-673 (response parsing)

**If using LiteLLM**: Change the `client.chat.completions.create()` call to `litellm.completion()` with `model="gemini/gemini-2.0-flash"`. LiteLLM auto-translates the function calling schema. Test all 7 calculator tool invocations.

**If using Direct Gemini SDK**: Must transpile all `TOOL_DEFINITIONS` from OpenAI format to Gemini `FunctionDeclaration` format. Different request AND response schema. Much more work.

**Verification**: Ask "What are the CPF contribution rates for a 35-year-old Singapore citizen earning $5,000?" — must trigger `calculate_cpf` tool call and return exact numbers.

### T004: Migrate intent classifier to Gemini

**File**: `src/hr_advisory/shadow/intent_classifier.py:331-354`
**What**: Replace `openai.OpenAI()` + `client.chat.completions.create()` with Gemini-compatible call. Uses JSON response mode for structured output.

**Verification**: Shadow agent intent classification still works (test via shadow endpoint).

### T005: Migrate guardrails scope classification to Gemini

**File**: `src/hr_advisory/workflows/guardrails.py:495-511`
**What**: Replace `openai.OpenAI()` + `client.chat.completions.create()` with Gemini-compatible call. Simple classification call (no function calling).

**Verification**: Query scope classification still routes correctly. Test with both in-scope and out-of-scope queries.

### T006: Migrate response synthesizer fallback to Gemini

**File**: `src/hr_advisory/agents/orchestration/response_synthesizer.py:169-198`
**What**: Replace `OpenAI()` + `client.chat.completions.create()` with Gemini-compatible call. This is the direct LLM fallback path.

**Verification**: Advisory responses still generate when the primary path falls through to direct synthesis.

### T007: Switch embedding model and vector dimensions

**Files**:

- `src/hr_advisory/kb/embeddings.py:77-84` — Change from `text-embedding-3-small` (OpenAI, 1536-dim) to Gemini `text-embedding-004` (768-dim)
- `src/hr_advisory/models/vector_setup.py:11` — Change `VECTOR_DIMENSIONS = 1536` to `768`

**Note**: Since this is a fresh database deploy, no migration needed — just set the right dimension before first KB load. All provisions will be embedded fresh with Gemini's model.

**Verification**: KB semantic search still returns relevant provisions. Test with 5 scripted queries.

### T008: Update env var defaults and config

**Files**:

- `.env.example:14-17` — Change `OPENAI_API_KEY`/`OPENAI_PROD_MODEL` to `GEMINI_API_KEY` and Gemini model names
- `deploy/.env.prod.example:17-19` — Same changes
- `src/hr_advisory/config/settings.py:32-35` — Change default models from `gpt-4o`/`gpt-4o-mini` to Gemini equivalents
- `src/hr_advisory/agents/llm_context.py:42` — Change default provider from `"openai"` to `"gemini"`

### T009: Update Kaizen config monkey-patch for Gemini

**File**: `src/hr_advisory/agents/config.py:82-138`
**What**: The current code patches `kaizen.config.providers.get_openai_config()` to intercept API keys. Update this to work with Gemini provider, or replace with LiteLLM bridge if Kaizen doesn't support Gemini natively.

**Depends on**: T001 (investigation outcome)

### T010: End-to-end Gemini integration test

**What**: Run the full advisory flow on Gemini from start to finish:

1. Advisory query with simple factual answer (notice period) — test basic completion
2. Advisory query triggering calculator tool call (CPF rates) — test function calling
3. Advisory query triggering RED risk tier (wrongful dismissal) — test safety chain
4. KB semantic search — test embedding quality
5. Shadow agent intent classification — test JSON mode

**Pass criteria**: All 5 scenarios produce correct, cited responses comparable to OpenAI quality. Response time under 10 seconds for first token.

---

## M2: Infrastructure & Deployment

New GCP instance separate from arbor.terrene.foundation.

### T011: Provision new GCP project and instance

**What**: Create a new GCP project for the Ricoh demo deployment:

1. Create GCP project (e.g., `arbor-demo` or similar)
2. Provision a GCE instance in `asia-southeast1` (e2-medium, Container-Optimized OS)
3. Reserve a static external IP
4. Set up firewall rules (80, 443)
5. SSH access configured

### T012: Register domain and configure DNS

**What**: Set up a demo domain (e.g., `demo.arbor.sg` or `arbor-demo.terrene.dev` or similar — Jared to decide).

1. Register/configure domain
2. Point DNS A record to the new static IP
3. Caddy will auto-provision SSL via Let's Encrypt

### T013: Update deployment config for new instance

**Files**:

- `deploy/Caddyfile:1` — Change `arbor.terrene.foundation` to new domain
- `deploy/docker-compose.prod.yml:36,39,58,62` — Update CORS origins and API URLs to new domain
- `deploy/deployment-config.md:7-60` — Update GCP project, instance name, IP, account
- `deploy/ship.sh:14-16` — Update `PROJECT`, `ZONE`, `INSTANCE` variables
- `deploy/.env.prod.example:35` — Update Google OAuth redirect URI
- `deploy/.env.prod.example:40` — Update CORS origin

### T014: Create production .env file for new instance

**What**: Create the actual `.env.prod` for the new instance (NOT committed to git):

- `DATABASE_URL` — New PostgreSQL credentials
- `REDIS_URL` — New Redis URL
- `GEMINI_API_KEY` — Google Gemini API key
- `JWT_SECRET_KEY` — Generate new production-grade secret
- `GOOGLE_OAUTH_CLIENT_ID` / `SECRET` — If using Google OAuth for demo
- `FROM_EMAIL` — Updated email domain
- `CORS_ORIGINS` — New domain
- `APP_ENV=production`
- `DEBUG=false`
- `LLM_BUDGET_USD=50` — Override default $5

### T015: Deploy and verify health

**What**: Deploy the application to the new instance:

1. Run `deploy/ship.sh` (after T013 updates)
2. Verify health: `curl -s https://<new-domain>/api/health`
3. Verify SSL certificate
4. Verify frontend loads
5. Verify CORS (frontend can call backend)

### T016: Initialize fresh database and load KB

**What**: On the new instance:

1. DataFlow auto-creates all 72 tables on first start
2. Load KB content (Acts, Domains, Provisions from `kb/content/*.py` modules)
3. Generate vector embeddings using Gemini embedding model
4. Verify KB semantic search returns relevant results

**Depends on**: T007 (embedding model switch), T015 (deployment)

---

## M3: Branding & Data Cleanup

### T017: Fix AITE branding remnants

**Files**:

- `apps/mobile/lib/core/config/app_config.dart:10` — Change comment "AITE backend API" to "Arbor backend API"
- `apps/web/tests/e2e/helpers/auth.helper.ts:85` — Update comment "aite_app on port 8099"
- `tests/e2e/test_live_api_all_flows.py:17` — Remove hardcoded path `/Users/esperie/repos/asme/aite/src`
- Mobile package name: `sg.aite.hr_advisory_mobile` → `sg.arbor.hr` (if mobile demo needed)

### T018: Update metadata descriptions

**Files**:

- `apps/web/src/app/layout.tsx:13-14` — Change description from "Singapore SMEs" to something broader (e.g., "AI-powered HR advisory platform with employment law compliance")
- `apps/mobile/pubspec.yaml:1-2` — Same
- `pyproject.toml:6-10` — Update description and author email

### T019: Update email domains

**Files**:

- `src/hr_advisory/config/settings.py:51,120` — Change `noreply@arbor.sg` to new email
- `src/hr_advisory/mcp_servers/adapters/resend_email.py:254` — Update sender
- `src/hr_advisory/mcp_servers/adapters/ses_email.py:50,60` — Update `notifications@arbor.sg` and SES region
- `apps/web/src/app/(dashboard)/help/page.tsx:334` — Update `mailto:support@arbor.sg`

### T020: Create demo seed script for Ricoh audience

**File**: `scripts/seed_demo_data.py` (modify)
**What**: Update the seed script to create a demo company appropriate for the Ricoh Thailand audience:

1. Make company name configurable via CLI args (default: something neutral, not "Sakura Trading")
2. Employee profiles with a mix that resonates with the audience (include some Japanese names for the expat angle)
3. Include diversity of roles: management, engineers, sales, service, back-office
4. Include varied work pass types (citizens, PRs, EP/SP holders)
5. Include 3 months payroll history, leave applications, claims, attendance records
6. Include 1-2 employees with upcoming work pass expiry (shows compliance alerts)
7. Idempotent — can re-run safely

```bash
python scripts/seed_demo_data.py --api-url https://<new-domain> --company "Demo Corp" --employees 25
```

### T021: Set demo company LLM budget

**What**: After seed script runs, set the demo company's LLM budget to $50+ via:

- Admin panel (if accessible), or
- Direct DB update: `UPDATE company_llm_config SET monthly_budget_usd = 50 WHERE company_id = <id>`
- Or set `LLM_BUDGET_USD=50` in env (if global override exists)

---

## M4: UX Demo Polish

### T022: Date picker component

**File**: `apps/web/src/components/design-system/DatePicker.tsx` (exists but may need updates)
**What**: Replace plain text date inputs (YYYY-MM-DD) with proper date picker:

- Calendar popover with month/year navigation
- Date range support for leave applications
- Apply across: leave applications, employee forms, payroll period selection, claims

### T023: Employee search picker

**File**: `apps/web/src/components/design-system/EmployeeSearch.tsx` (new or existing)
**What**: Searchable employee dropdown to replace raw ID inputs:

- Type-ahead search by name
- Shows employee name, department, role in dropdown
- Returns employee_id for API calls
- Apply across: leave (approving for), payroll, attendance, shifts, claims

### T024: Reports charts

**File**: `apps/web/src/app/(dashboard)/reports/page.tsx`
**What**: Add visual charts to the reports module:

- Headcount by department (bar chart)
- Payroll cost trend (line chart, 3-6 months)
- Leave utilization (stacked bar)
- Foreign worker ratio (pie chart)
- Use recharts or similar lightweight chart library

### T025: Dashboard enhancement for demo data

**File**: `apps/web/src/app/(dashboard)/dashboard/page.tsx`
**What**: Ensure dashboard shows rich data when company has seed data:

- Headcount summary card with breakdown
- Pending approvals count (leave, claims, timesheets)
- Upcoming deadlines (work pass expiry, CPF filing)
- Compliance status with meaningful data
- Shadow agent briefing card populated

### T026: Fix Clients page dead end

**File**: `apps/web/src/app/(dashboard)/clients/page.tsx`
**What**: The "View" button on client rows navigates nowhere. Either:

- Implement a client detail page, or
- Remove the Clients nav item entirely (not relevant to demo story — recommended)

---

## M5: Demo Data & Testing

### T027: Pre-test 5 scripted advisory questions

**What**: After deployment, test all 5 scripted demo questions:

1. "What is the minimum notice period for terminating an employee who has worked for 3 years?"
   - Expected: EA Section 10, 2 weeks, AMBER risk tier
2. "What are the CPF contribution rates for a 35-year-old Singapore citizen earning $5,000?"
   - Expected: Triggers `calculate_cpf` tool, exact rates, GREEN risk tier
3. "An employee was injured at work. What are my obligations as an employer?"
   - Expected: Cross-references WSH Act and WICA, multi-domain
4. "An employee claims they were wrongfully dismissed after refusing overtime. What should I do?"
   - Expected: RED risk tier, professional referral, "stop all adverse action"
5. "I'm hiring a foreign worker for the first time. What do I need to know?"
   - Expected: Triggers `calculate_quota_levy`, references EFMA

**Pass criteria**: Proper citations, correct risk tiers, streaming works, response time <8 seconds first token.

### T028: Production smoke test script

**File**: `scripts/demo_smoke_test.py` (modify for new domain)
**What**: Morning-of-demo automated verification:

- Health endpoint → 200
- Auth flow (login with demo account) → JWT token
- Advisory query → streaming response with citations
- Calculator endpoint → correct result
- Shadow context endpoint → data returned
- Frontend → 200

### T029: Verify conversation persistence

**What**: Test if conversations survive a server restart:

1. Create a conversation with 2-3 messages
2. Restart the backend container
3. Check if the conversation loads correctly
4. Document the result — affects demo prep strategy

### T030: Response latency measurement

**What**: Time all 5 scripted queries to set expectations:

- First query (cold start): expected 5-8 seconds
- Subsequent queries: expected 3-5 seconds
- Document Gemini latency vs OpenAI baseline (if available)
- Prepare talking points for any pause: "Watch how it searches the knowledge base..."

---

## M6: Demo Materials & Narrative

Most materials already exist from the analysis phase. Finalize and print-ready.

### T031: Finalize CCO narrative document

**File**: `01-analysis/01-research/10-ricoh-thailand-proposal-analysis.md`
**What**: The narrative is written. Review and finalize Part 6 (Friday Talking Points) for the actual meeting:

- Confirm the 15-minute narrative flow works when spoken aloud
- Adjust any talking points based on new information about Ricoh Thailand
- Ensure the "Ask" is clear: paid proof-of-concept, 3 Thai domains, 4-6 weeks

### T032: Finalize leave-behind brief for ringisho circulation

**File**: `01-analysis/01-research/08-leave-behind-brief.md`
**What**: This becomes the attachment the internal champion uses to build the ringisho. Review and finalize:

- Structure as near-ready ringisho attachment (problem, solution, governance, risk, cost, timeline, next steps)
- Remove any Terrene Foundation internal references
- Ensure pricing section aligns with what Jared wants to propose
- Export as PDF for handoff

### T033: Prepare ChatGPT vs Arbor comparison screenshots

**What**: The comparison document exists (`06-chatgpt-comparison.md`). Create actual visual assets:

1. Ask ChatGPT the wrongful dismissal question, screenshot the response
2. Ask Arbor the same question on the demo instance, screenshot the response
3. Create a side-by-side comparison image or slide
4. This is the opening "wow" moment of the demo

### T034: Create multi-jurisdiction architecture diagram

**What**: Visual diagram for the "Thailand story" portion (already drafted in `07-architecture-diagram.md`):

- Pluggable KB layer: SG filled, TH/MY/VN/ID as "ready to load"
- Configurable specialist agents per jurisdiction
- Modular calculator layer
- Universal HRIS core
- Universal EATP trust lineage
- Export as image or slide

### T035: Record backup demo video

**What**: 5-minute screen capture of key demo moments as fallback:

1. Advisory streaming with citations and risk tier
2. Calculator running with exact CPF numbers
3. Dashboard with real data
4. Shadow agent margin indicators
5. RED-tier response with professional referral

---

## M7: Demo Resilience

### T036: Demo day pre-warming protocol

**What**: 30 minutes before the demo:

1. Send a throwaway advisory query to warm up the system
2. Verify all 5 scripted questions still work
3. Check LLM budget hasn't been exhausted
4. Clear any test conversations that look unprofessional
5. Open all demo URLs in browser tabs

### T037: Fallback plan document

**What**: Written plan for common demo failures:

| Failure                | Fallback                                          |
| ---------------------- | ------------------------------------------------- |
| Backend down           | Show backup video (T035)                          |
| Advisory returns error | Switch to pre-recorded screenshots                |
| Slow response (>15s)   | Talk through the safety chain steps while waiting |
| LLM budget exhausted   | Use BYOK key or show pre-recorded                 |
| Frontend 500           | Switch to mobile app or API-direct demo           |
| Internet down          | Use backup video on local machine                 |

### T038: Prepare BYOK backup key

**What**: Have a second Gemini API key ready (different project/billing) in case the primary key has issues. Test it works before demo day.

---

## M8: Post-Demo — Thailand Proof-of-Concept

These tasks activate only if Ricoh agrees to a PoC engagement.

### T039: Build minimal Thai KB (10-20 provisions)

**File**: New `src/hr_advisory/kb/content/thai_labour.py`
**What**: Even before formal PoC, having 10-20 Thai provisions loaded transforms the demo from "imagine" to "look, we started." Key provisions:

- Severance pay (LPA Section 118): 30-400 days by tenure
- Annual leave minimum (LPA Section 30): 6 days after 1 year
- Overtime rates (LPA Sections 61/63): 1.5x normal, 3x holiday
- Notice period (LPA Section 17): at least one pay cycle
- Working hours (LPA Section 23): 8 hours/day, 48 hours/week
- Maternity leave (LPA Section 41): 98 days
- Sick leave (LPA Section 32): 30 working days/year
- Social Security contributions: 5%/5%, capped THB 750 each

### T040: Build Thai Social Security Fund calculator

**File**: New `src/hr_advisory/workflows/calculators/ssf_calculator.py`
**What**: Simplest Thai calculator — proves the architecture works for Thailand:

- Employer: 5% of wages capped at THB 15,000/month = max THB 750
- Employee: same
- Handle temporary rate reductions (government announces quarterly)

### T041: Build Thai PIT withholding calculator

**File**: New `src/hr_advisory/workflows/calculators/thai_pit_calculator.py`
**What**: Thai personal income tax using annualization method:

- Progressive brackets: 0% (up to 150K) → 5% → 10% → 15% → 20% → 25% → 30% → 35%
- Monthly withholding = (projected annual tax) / 12
- Handle deductions (personal 60K, spouse 60K, children 30K, social security, etc.)

### T042: Build Thai severance calculator

**File**: New `src/hr_advisory/workflows/calculators/thai_severance_calculator.py`
**What**: LPA Section 118 severance scale:

- 120 days but <1 year: 30 days
- 1-3 years: 90 days
- 3-6 years: 180 days
- 6-10 years: 240 days
- 10-20 years: 300 days
- 20+ years: 400 days

### T043: Build Thai specialist agents (3 priority domains)

**What**: Configure 3 Thai specialist agents for the PoC:

1. **Labour Protection specialist** — Thai LPA equivalent of EA specialist
2. **Social Security specialist** — Thai SSF equivalent of CPF specialist
3. **Tax specialist** — Thai Revenue Code equivalent of IRAS specialist

Each needs: domain prompt, system instructions, KB content reference.

### T044: Thai guardrail patterns

**File**: `src/hr_advisory/workflows/guardrails.py`
**What**: Add Thai-specific circumvention detection:

- "Avoid paying social security contributions" → illegal under SSA
- "Pay below minimum wage" → violation of LPA
- "Hire foreign worker without permit" → violation of Working of Aliens Act

### T045: Engage Thai legal counsel for KB validation

**What**: Partner with a Thai law firm to validate the KB content:

- Recommended: Chandler MHM (Japanese-Thai firm — natural fit for Ricoh)
- Alternative: Baker McKenzie Bangkok, Tilleke & Gibbins
- Scope: Review 3 domain KB modules for accuracy, currency, completeness
- Budget: estimate THB 50,000-150,000 for review

---

## M9: Post-Demo — Multi-Jurisdiction Architecture

Long-term platform evolution. Only if Ricoh engagement proceeds AND multi-country is on the table.

### T046: Add jurisdiction field to Company model

**File**: `src/hr_advisory/models/company_user.py`
**What**: Add `jurisdiction: str = "SG"` field to Company model. This is the foundation for multi-jurisdiction support.

- Update all downstream code that assumes Singapore
- Add jurisdiction to company creation API
- Add jurisdiction to onboarding flow
- Route specialist agents based on jurisdiction

### T047: Parameterize calculators by jurisdiction

**What**: Refactor calculators to load rates from config/DB rather than hardcoded constants:

- CPF calculator → jurisdiction-aware social security calculator
- Overtime calculator → jurisdiction-aware overtime calculator
- Leave calculator → jurisdiction-aware leave calculator
- Cost-to-company → jurisdiction-aware breakdown

### T048: Jurisdiction-aware domain routing

**What**: Specialist agent dispatcher routes to correct domain agents based on company jurisdiction:

- SG company → EA, CPF, EFMA, TAFEP, WSH, IRAS specialists
- TH company → LPA, SSF, Revenue Code, Foreign Employment, Labour Relations, OSH specialists

### T049: Bilingual advisory (Thai + English)

**What**: Advisory engine responds in the appropriate language:

- Detect query language
- Respond in same language
- Legal citations always include Thai Act name + section number
- Support Buddhist Era dates (Thai legislation uses B.E.)

### T050: Thai statutory filing formats

**What**: Generate Thai-specific compliance files:

- Social Security Fund monthly filing (SSO format)
- PIT withholding return (PND 1 monthly, PND 1 Kor annual)
- Replaces Singapore's CPF e-Submit and IR8A generation

### T051: Full Thai calculator suite

**What**: Complete the remaining Thai calculators beyond the PoC set:

- Overtime calculator (1.5x weekday, 2x holiday, 3x holiday OT)
- Leave entitlement tracker (7 leave types with different rules)
- Work permit 4:1 ratio monitor
- Notice period calculator

### T052: ASEAN expansion framework

**What**: If Ricoh wants Vietnam, Indonesia, Philippines — document the framework:

- KB content template per jurisdiction
- Specialist agent configuration template
- Calculator implementation guide
- Estimated effort per jurisdiction: 2-4 weeks each (leveraging proven architecture)

---

## Summary

| Milestone | Todos     | Description                   | Priority      | Effort Est. |
| --------- | --------- | ----------------------------- | ------------- | ----------- |
| **M1**    | T001-T010 | Gemini API migration          | **CRITICAL**  | 2-4 days    |
| **M2**    | T011-T016 | Infrastructure & deployment   | **CRITICAL**  | 1-2 days    |
| **M3**    | T017-T021 | Branding & data cleanup       | **HIGH**      | 3-4 hours   |
| **M4**    | T022-T026 | UX demo polish                | **HIGH**      | 2-3 days    |
| **M5**    | T027-T030 | Demo data & testing           | **HIGH**      | 4-6 hours   |
| **M6**    | T031-T035 | Demo materials & narrative    | **MEDIUM**    | 1 day       |
| **M7**    | T036-T038 | Demo resilience               | **MEDIUM**    | 2-3 hours   |
| **M8**    | T039-T045 | Post-demo: Thailand PoC       | **POST-DEMO** | 3-4 weeks   |
| **M9**    | T046-T052 | Post-demo: Multi-jurisdiction | **POST-DEMO** | 2-3 months  |

**Total: 52 todos across 9 milestones**

### Critical Path (must complete before demo)

```
T001 (Kaizen investigation)
  → T002 (LiteLLM abstraction)
    → T003-T006 (migrate 4 LLM calls)
      → T007 (embedding switch)
        → T010 (e2e Gemini test)

T011-T012 (GCP + domain) — parallel with M1
  → T013-T014 (deployment config + env)
    → T015 (deploy)
      → T016 (DB + KB load)
        → T020 (seed data)
          → T021 (budget)
            → T027 (pre-test questions)

T017-T019 (branding cleanup) — parallel with above
T022-T026 (UX polish) — parallel with above
T031-T035 (demo materials) — parallel with above
```

### Parallel Tracks

- **Track A**: Gemini migration (M1) — backend focused
- **Track B**: Infrastructure (M2) — DevOps focused
- **Track C**: UX polish (M4) — frontend focused
- **Track D**: Materials (M6) — narrative focused

Tracks A-D can run concurrently. M3 (branding) and M5 (testing) are sequential after A+B converge. M7 (resilience) is demo-day prep.

### What's Explicitly Excluded from Demo Scope

- Thai KB content (Singapore is acceptable for demo)
- Thai calculators, specialists, guardrails
- Multi-jurisdiction architecture changes
- Thai i18n localization
- Thai data models and statutory filing formats
- Mobile app demo (web only for CCO meeting)
- Test suite cleanup (not visible in demo)

These are captured in M8-M9 as post-demo work.
