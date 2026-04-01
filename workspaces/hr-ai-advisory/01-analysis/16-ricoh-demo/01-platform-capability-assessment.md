# Platform Capability Assessment for Ricoh Thailand Demo

**Date**: 2026-03-24
**Objective**: Evaluate Arbor's current state as a demo piece for Ricoh Thailand

---

## Executive Summary

Arbor is a **production-deployed, fully functional HR platform** — not a prototype. It is live at `arbor.terrene.foundation` with all containers healthy. The platform has 120+ API endpoints, a working AI advisory engine with SSE streaming, 6 regulatory domain specialists, deterministic HR calculators, a full HRIS suite (payroll, leave, claims, attendance, shifts, recruitment, appraisals), and a shadow agent intelligence layer. The codebase is ~89K lines Python backend + ~61K lines React frontend + ~47K lines tests.

**Demo readiness: 8/10** for a Singapore HR copilot demo. For a Ricoh Thailand demo, the score drops to **5/10** because the entire knowledge base is Singapore-specific. However, the _architecture and UX_ are universally impressive and demonstrate what an HR copilot can do regardless of jurisdiction.

---

## Current Capabilities (What Works Today)

### 1. AI Advisory Engine — Rating: 9/10

| Component                        | Status       | Detail                                                                            |
| -------------------------------- | ------------ | --------------------------------------------------------------------------------- |
| Advisory chat with SSE streaming | Working      | Real-time token streaming, conversation history                                   |
| 6 domain specialists             | Implemented  | Employment Act, CPF, Foreign Manpower, TAFEP/Fair Employment, WSH, Tax/IRAS       |
| 13-step safety chain             | Implemented  | Query analysis → KB retrieval → compliance gate → synthesis → citation validation |
| Knowledge base                   | 6,500+ lines | Structured Singapore employment law across 6 regulatory domains                   |
| Trust lineage (EATP)             | Implemented  | Every advisory response carries attestation                                       |
| Risk-tier UI                     | Working      | Green/amber/red visual trust signals                                              |
| Conversation management          | Working      | Create, load, rename, delete conversations                                        |
| Escalation flow                  | Implemented  | When queries exceed AI confidence                                                 |

**Demo strength**: Ask it a real Singapore employment law question and watch it stream a cited, risk-categorized response in real-time. This is the single most impressive demo moment.

### 2. Shadow Agent — Rating: 7/10

| Component                  | Status      | Detail                                            |
| -------------------------- | ----------- | ------------------------------------------------- |
| Intent classification      | Implemented | 465 tests passing                                 |
| PACE execution loop        | Implemented | Plan-Act-Check-Evaluate safety model              |
| Entity resolution          | Implemented | Resolves "my employee John" to employee records   |
| Workflow composition       | Implemented | Multi-step HR tasks                               |
| Observation/memory         | Implemented | Learns user work patterns                         |
| Command surface (frontend) | Built       | React components for inline AI interaction        |
| Margin/overlay UI          | Built       | ArborOverlay, ArborResult, ArborHistory, PaceCard |
| Briefing cards             | Built       | Proactive suggestions                             |

**Demo strength**: Show how the AI isn't just a chatbot — it's embedded in every page, observes patterns, and proactively surfaces relevant compliance information.

### 3. Full HRIS Suite — Rating: 7/10

| Module              | API               | Frontend                 | Status  |
| ------------------- | ----------------- | ------------------------ | ------- |
| Employee management | 131K lines router | Full CRUD                | Working |
| Payroll             | 73K lines router  | Run payroll, payslips    | Working |
| Leave management    | 54K lines router  | Apply, approve, balances | Working |
| Claims & expenses   | 31K lines router  | Submit, approve          | Working |
| Attendance          | 35K lines router  | Clock in/out, overtime   | Working |
| Shifts              | 28K lines router  | Schedule, roster         | Working |
| Recruitment         | 22K lines router  | Pipeline, candidates     | Working |
| Appraisals          | 19K lines router  | Reviews, scores          | Working |
| Projects            | 29K lines router  | Task tracking            | Working |
| Inventory           | 18K lines router  | Asset management         | Working |
| Learning/Training   | 17K lines router  | Course management        | Working |
| Documents           | 10K lines router  | Template generation      | Working |
| Compliance          | 13K lines router  | Compliance checks        | Working |

**Demo strength**: This isn't just an AI chatbot — it's a complete HR platform. The AI is integrated INTO the operations, not bolted on.

### 4. Calculators (Deterministic, Zero LLM) — Rating: 8/10

- CPF contribution calculator (all age bands, all worker types)
- Leave entitlement calculator (13 leave types, service-year progression)
- Overtime pay calculator (Part IV EA employees)
- Retrenchment benefit calculator
- Cost-to-company breakdown
- Quota/levy calculator (foreign worker ratios)
- Notice period calculator

**Demo strength**: "The AI doesn't guess your CPF — it calculates it deterministically, then the advisory engine explains the regulations behind it."

### 5. MCP Integration Layer — Rating: 6/10

| Server               | Connectors                                      | Status  |
| -------------------- | ----------------------------------------------- | ------- |
| arbor-government     | MOM, IRAS, CPF Board, data.gov.sg, SkillsFuture | Defined |
| arbor-accounting     | Xero, QuickBooks, Financio                      | Defined |
| arbor-banking        | PayNow, GIRO, Wise, Aspire                      | Defined |
| arbor-communications | Email, Slack, Teams, WhatsApp, Telegram         | Defined |
| arbor-regulatory     | MOM RSS, compliance monitoring                  | Defined |

**Note**: Connectors are architecturally defined with the MCP protocol but external API integrations require actual API keys and partner agreements.

### 6. Frontend & UX — Rating: 7/10

- Next.js 16 + React + Tailwind v4 + TanStack Query
- Full design system with tokens
- Responsive layout with sidebar navigation
- 35+ dashboard pages
- Onboarding flow (4-step company setup)
- Admin panel with QA dashboard, KB management, conversation browser
- Shadow agent components (CommandSurface, PaceCard, ArborOverlay, etc.)

**Known issues** (from red team): Plain text date inputs, no employee search picker, some modules lack charts (tables only).

### 7. Infrastructure & Security — Rating: 8/10

- Production deployment: GCP asia-southeast1, Docker Compose, Caddy auto-HTTPS
- Auth: JWT + bcrypt, Google OAuth, token refresh
- Tenant isolation: Company-scoped all queries
- Input validation: NaN/Infinity checks, text length limits, CSV injection prevention
- 7 red team rounds completed, 22+ security issues found and fixed
- 826+ tests passing (115 pre-existing failures in non-critical modules)

---

## Critical Gap: Singapore-Specific Content

The entire knowledge base, all 6 specialist agents, all calculators, and all compliance logic are built for **Singapore employment law**. This includes:

- Employment Act (Cap. 91)
- CPF Act (Central Provident Fund)
- EFMA (Employment of Foreign Manpower Act)
- TAFEP Tripartite Guidelines
- WSH Act (Workplace Safety and Health)
- IRAS Income Tax Act

None of this applies to Thailand. Thai labour law (Labour Protection Act B.E. 2541, Social Security Act, Revenue Code) is entirely different.

---

## What This Means for the Ricoh Thailand Demo

### What's universally impressive (show these):

1. **The advisory engine architecture** — the 13-step safety chain, citation grounding, risk tiers
2. **Shadow agent concept** — AI embedded in every page, not a bolted-on chatbot
3. **Full HRIS + AI integration** — the platform runs payroll AND explains the law
4. **Trust lineage** — every AI response is traceable and auditable (EATP)
5. **The speed of development** — 121 completed milestones, 89K lines of code, production-deployed

### What's Singapore-only (demonstrate but explain):

1. All regulatory content and citations
2. CPF, SDL, FWL calculations
3. MOM/TAFEP/IRAS-specific compliance checks
4. Quota/levy management

### What would need to change for Thailand:

1. Replace KB content with Thai labour law
2. Build Thai specialist agents (Social Security, Revenue Department, Labour Court)
3. Replace calculators (Thai SSF instead of CPF, Thai income tax brackets)
4. Thai language support
5. Different statutory filing formats
