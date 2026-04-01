# Ricoh Thailand Demo — Showcase Roadmap

**Objective**: Showcase Arbor as a production-grade HR copilot to Ricoh Thailand. Demo the Singapore product to demonstrate what's possible.
**Analysis**: `01-analysis/16-ricoh-demo/` (4 documents)
**Scope**: Demo prep only — no Thailand localization at this stage.

---

## M66: Demo Infrastructure & Data (IMMEDIATE)

### T483: Deploy Latest Code to Production

**File**: `deploy/ship.sh`
**What**: 5 commits since last deploy (2026-03-20) include SSE event type prefix fixes, KB search fallback to Python content modules, and citation validation improvements. Run `./deploy/ship.sh` to pick these up on arbor.terrene.foundation.

**Verification**:

- `curl -s https://arbor.terrene.foundation/api/health` returns all workflows healthy
- Frontend loads at https://arbor.terrene.foundation
- Shadow endpoint returns 401 (auth required, not 404)

### T484: Create Demo Account & Company

**What**: Register a demo user and create a company with a realistic Singapore profile:

1. Register demo user (e.g., `demo@arbor.terrene.foundation`)
2. Create company (e.g., "Sakura Trading Pte Ltd")
3. Configure: sector=Services, headcount=45, breakdown: 30 local, 5 PR, 5 EP, 3 SP, 2 WP
4. This triggers `seed_company_defaults()` — verify leave types, claim categories, attendance settings, holidays are populated

### T485: Demo Data Seed Script

**File**: `scripts/seed_demo_data.py` (new)
**What**: A single reusable script that creates the entire demo dataset:

```bash
python scripts/seed_demo_data.py --company "Sakura Trading" --employees 30
```

Creates:

- 25-30 employees with varied profiles (citizens, PRs, EP/SP/WP holders; mix of roles, salary bands $2,500-$12,000)
- 2-3 employees with upcoming work pass expiry (compliance alerts)
- 1-2 employees on probation
- 3 months payroll history (Jan-Mar 2026) with CPF, SDL, FWL breakdowns
- 8-10 leave applications (approved, pending, rejected; annual, sick, maternity)
- 5-6 expense claims in various states
- Attendance records for current month with 2-3 overtime cases
- 1 active recruitment pipeline with 4-5 candidates
- Idempotent (can re-run safely)

### T486: Set Demo Budget & API Configuration

**What**: Configure the demo company for unlimited demo queries:

1. Set company LLM budget to $50/month (via CompanyLLMConfig or direct DB update)
2. Verify OpenAI API key on server is valid and has credits
3. Prepare a backup BYOK key (test it works)
4. Test one advisory query end-to-end to confirm streaming works

### T487: Pre-Test Demo Advisory Questions

**What**: Test all 5 scripted advisory questions:

1. "What is the minimum notice period for terminating an employee who has worked for 3 years?"
2. "What are the CPF contribution rates for a 35-year-old Singapore citizen earning $5,000?"
3. "An employee was injured at work. What are my obligations as an employer?"
4. "An employee claims they were wrongfully dismissed after refusing overtime. What should I do?"
5. "I'm hiring a foreign worker for the first time. What do I need to know?"

Verify: proper citations, risk tiers, streaming, reasonable response time (<8 seconds first token).

### T488: Verify Conversation Persistence

**What**: The advisory may persist conversations to DB (via `_rehydrate_conversation`). Verify:

1. Create a conversation with 2-3 messages
2. Restart the backend container
3. Check if the conversation loads correctly
4. If conversations survive restart: demo prep conversations can be pre-created
5. If not: accept starting fresh during demo (fine — shows real flow)

---

## M67: UX Demo Polish

### T489: Date Picker Components

**File**: `apps/web/src/components/design-system/DatePicker.tsx` (new)
**What**: Replace plain text date inputs (YYYY-MM-DD) with proper date picker:

- Calendar popover with month/year navigation
- Supports date ranges for leave applications
- Apply across: leave applications, employee forms, payroll period, claims

### T490: Employee Search Picker

**File**: `apps/web/src/components/design-system/EmployeeSearch.tsx` (new)
**What**: Searchable employee dropdown to replace raw ID inputs:

- Type-ahead search by name
- Shows employee name, department, role in dropdown
- Returns employee_id for API calls
- Apply across: leave (approving for), payroll, attendance, shifts, claims

### T491: Reports Charts

**File**: `apps/web/src/app/(dashboard)/reports/` (modify)
**What**: Add visual charts to the reports module:

- Headcount by department (bar chart)
- Payroll cost trend (line chart, 3-6 months)
- Leave utilization (stacked bar)
- Foreign worker ratio (pie chart)
- Use a lightweight chart library (recharts or chart.js)

### T492: Dashboard Enhancement for Demo

**File**: `apps/web/src/app/(dashboard)/dashboard/page.tsx` (modify)
**What**: Ensure the dashboard shows rich data when a company has seed data:

- Headcount summary card with breakdown
- Pending approvals count (leave, claims, timesheets)
- Upcoming deadlines (work pass expiry, CPF filing)
- Compliance status with meaningful data
- Shadow agent briefing card populated

### T493: Fix Clients Page Dead End

**File**: `apps/web/src/app/(dashboard)/clients/page.tsx`
**What**: The "View" button on client rows navigates nowhere. Either:

- Implement a client detail page
- Or remove the Clients nav item entirely (not relevant to the core demo story)

---

## M68: Demo Narrative & Materials

### T494: Demo Script Document

**File**: `workspaces/hr-ai-advisory/01-analysis/16-ricoh-demo/05-demo-script.md` (new)
**What**: Detailed presenter script with:

- Exact words to say at each point (45-minute flow from analysis)
- Screen navigation instructions (which URL, what to type)
- Timing cues per act
- Fallback plans if something fails
- Thai equivalents for Singapore terms (translate for audience: "CPF is like Thailand's Social Security Fund")

### T495: ChatGPT vs Arbor Comparison

**What**: Prepare a side-by-side comparison for the opening act:

1. Ask ChatGPT a Singapore employment law question
2. Ask Arbor the same question
3. Screenshot both responses
4. Highlight: Arbor has citations, risk tier, structured KB retrieval. ChatGPT has generic text, may be wrong.

### T496: Multi-Jurisdiction Architecture Diagram

**File**: `docs/diagrams/` or slide
**What**: Visual diagram showing that the architecture is jurisdiction-pluggable:

- Pluggable KB layer (show SG as "filled in", TH/MY/VN/ID as "ready to load")
- Configurable specialist agents per jurisdiction
- Modular calculator layer
- Universal HRIS core (payroll, leave, attendance = same everywhere)
- EATP trust lineage (universal)

This is for the "Thailand story" portion of the demo — showing the ARCHITECTURE, not the content.

### T497: Record Backup Demo Video

**What**: Record a 5-minute screen capture of the demo's key moments as fallback:

1. Advisory streaming with citations and risk tier
2. Calculator running with exact CPF numbers
3. Dashboard with real data
4. Shadow agent margin indicators

### T498: Leave-Behind Materials

**What**: After the demo, Ricoh executives need something to circulate internally:

1. One-page PDF: "Arbor HR Copilot — Capability Brief"
2. Architecture diagram showing multi-jurisdiction potential
3. Key differentiators (trust lineage, safety chain, deterministic calculators)

---

## M69: Demo Resilience

### T499: Response Latency Pre-warming

**What**: First advisory query after a cold start takes 5-8 seconds. Mitigate:

1. Send a throwaway query 10 minutes before demo starts
2. Prepare talking points for the pause: "Watch how it searches the knowledge base, identifies the relevant provisions, then synthesizes a response..."

### T500: Production Smoke Test Script

**File**: `scripts/demo_smoke_test.py` (new)
**What**: Run this morning-of-demo to verify everything works:

- Health endpoint → 200
- Auth flow (login with demo account) → token
- Advisory query (quick test) → streaming response
- Calculator endpoint → result
- Shadow context endpoint → data
- Frontend → 200

### T501: AITE Branding Remnant Sweep

**What**: Verify all user-visible surfaces say "Arbor" not "AITE":

- Web app title, nav, tagline
- Mobile app package name (`sg.aite.hr_advisory_mobile` → `sg.arbor.hr`)
- Any remaining screenshots or assets
- Deploy if any changes made

---

## ~~M70: Shadow Agent Execution~~ — ALREADY COMPLETE

Red team audit confirmed the shadow agent execution layer is fully implemented:

- Backend: `/execute`, `/confirm`, `/cancel`, `/undo` endpoints all exist in `shadow.py`
- Frontend: `CommandSurface.tsx` already wired to `/shadow/execute`, `PaceCard.tsx` handles PACE flow
- Backend modules: `intent_classifier.py`, `tool_registry.py`, `executor.py`, `pace.py`, `formatter.py`, `workflow_composer.py` all exist

**No new work needed.** Include shadow agent execution in the demo script as an existing feature.

---

## M70: Test Suite Cleanup

### T502: Fix Pre-existing Test Failures

**What**: The 115 pre-existing test failures are in learning, QA, invitation, and feedback modules (test ordering, state pollution). Fix:

1. Diagnose root cause per module (shared state, missing setUp/tearDown)
2. Fix test isolation
3. Target: 0 failures in full pytest run
4. Not a demo blocker, but important for credibility and code health

---

## Summary

| Milestone | Todos     | Description                | Priority  |
| --------- | --------- | -------------------------- | --------- |
| M66       | T483-T488 | Demo infrastructure & data | IMMEDIATE |
| M67       | T489-T493 | UX demo polish             | HIGH      |
| M68       | T494-T498 | Demo narrative & materials | HIGH      |
| M69       | T499-T501 | Demo resilience & branding | MEDIUM    |
| M70       | T502      | Test suite cleanup         | LOW       |

**Total: 20 todos (T483-T502) across 5 milestones**

**Shadow agent execution is ALREADY COMPLETE** — no new work needed. Include in demo as existing feature.

**Critical path**: M66 (deploy + seed data) → M67 (UX polish) → M68 (demo materials)

**Parallel tracks**: M69 (resilience) + M70 (tests) run independently.

**What was removed** (not needed for showcase-only demo):

- All Thailand KB, calculators, specialist agents, guardrails, emergency responses
- Multi-jurisdiction architecture changes
- Thai i18n localization
- Thai data models and statutory filing formats
- Shadow agent execution (already built — confirmed by red team audit)

Thailand adaptation can be proposed as a follow-up if Ricoh shows interest.
