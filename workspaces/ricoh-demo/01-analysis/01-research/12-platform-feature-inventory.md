# Central HR Platform — Complete Feature Inventory

**For**: Client presentation / slide deck material
**Date**: 2026-03-26
**Platform**: central.kailash.ai

---

## Platform at a Glance

| Metric                        | Value                                 |
| ----------------------------- | ------------------------------------- |
| Backend codebase              | ~89,000 lines Python                  |
| Frontend (web)                | ~61,000 lines React/Next.js           |
| Frontend (mobile)             | ~47,000 lines Flutter                 |
| Test suite                    | ~47,000 lines, 826+ tests             |
| API endpoints                 | 120+                                  |
| Data models                   | 72                                    |
| Dashboard pages               | 48                                    |
| HRIS modules                  | 22                                    |
| Calculators                   | 7 (deterministic, zero AI)            |
| KB provisions                 | 89+ structured legal provisions       |
| Regulatory domains            | 6                                     |
| Safety chain steps            | 13 (every advisory query, every time) |
| Red team rounds               | 7 completed                           |
| Security issues found & fixed | 22+                                   |

---

## The Three Layers

Central operates on three layers. The bottom two work with zero AI. The top layer is where the intelligence lives.

### Layer 1: Complete HRIS (No AI Required)

A full-service HR platform — payroll, leave, attendance, claims, recruitment, appraisals, and more. Every feature listed below works without any AI or LLM key. Pure operational HR.

### Layer 2: Deterministic Compliance (No AI Required)

Statutory calculators, knowledge base, compliance checking, and trust infrastructure. Every number is computed from published statutory tables — the AI never does math.

### Layer 3: AI Intelligence (LLM Required)

The advisory engine, shadow agent, and semantic search. This is what makes Central different from every other HRIS — employment law advisory with citations, risk tiers, and a cryptographic audit trail.

---

## Layer 1: Full HRIS Suite — 22 Modules

Every module has: backend API, database persistence, web dashboard, and role-based access.

### Core HR

| Module                  | What It Does                           | Key Features                                                                                                                                                                                                                               |
| ----------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Employee Management** | Complete employee lifecycle            | Invite, onboard, profiles, salary components, emergency contacts, employment history, documents, org chart, CSV bulk import, probation tracking, family members, skills, custom fields                                                     |
| **Payroll**             | Gross-to-net with statutory deductions | Calculate runs, CPF/SDL/FWL breakdowns, approve/pay workflow, payslips, payslip PDF, email payslips, CPF e-Submit file generation, bank GIRO file, IR8A/IR21 tax filing, pay items, pay schemes, variance reports, ad-hoc runs, simulation |
| **Leave Management**    | Apply-approve workflow with balances   | Leave types, applications, approve/reject, balances auto-calculated by service years, public holidays, policies, calendar view, encashment, off-in-lieu, prorated for mid-year joiners                                                     |
| **Claims & Expenses**   | Submit-approve with receipts           | Categories, create/submit, receipt upload, manager approval, audit trail, claim groups, payroll-ready integration                                                                                                                          |
| **Attendance**          | Clock in/out with overtime             | Clock in/out, daily records, summary view, edit/correct, timesheet submit/approve, lateness tracking, early departure, overtime calculation, dashboard                                                                                     |
| **Shift Scheduling**    | Roster management                      | Shift templates, schedule creation, assignments, publish, employee availability, hours tracking, hourly rates, shift multipliers                                                                                                           |

### Talent & Performance

| Module                  | What It Does                     | Key Features                                                                                                                              |
| ----------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Recruitment**         | Hiring pipeline                  | Job listings, publish/close, candidate tracking, interview scheduling, feedback collection, offer management, hire-to-employee conversion |
| **Appraisals**          | Performance reviews              | Templates, review periods, launch cycles, self-assessment, manager review, scoring, submit/sign-off workflow                              |
| **Projects & Costing**  | Project-based workforce tracking | Project CRUD, team assignments, role-based rates, overhead allocation, timesheet entries, cost calculation, project reports               |
| **Learning & Training** | Training management              | Course management, SkillsFuture integration, training records                                                                             |

### Operations

| Module                 | What It Does                       | Key Features                                                                                                                                                     |
| ---------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Inventory / Assets** | Company asset tracking             | Locations, categories, items, reserve/issue/return/dispose workflow, employee acknowledgment, request-approval flow, full history                                |
| **Documents**          | Template-based document generation | Contract templates, offer letters, KET (Key Employment Terms), generate from template, preview, download                                                         |
| **Compliance**         | Regulatory health check            | Evaluates HR practices against employment law, category-by-category scoring, recommendations                                                                     |
| **Reports**            | Analytics with charts              | Payroll summary, YTD reports, leave utilization, claims analysis, attendance patterns, headcount by department — all with visual charts (bar, donut, trend line) |

### Platform

| Module                | What It Does                 | Key Features                                                                              |
| --------------------- | ---------------------------- | ----------------------------------------------------------------------------------------- |
| **Company Profile**   | Organization setup           | Profile, workforce composition, sector, headcount breakdown, completeness scoring         |
| **Policies**          | Company policy management    | Leave policy, flexible work arrangements, employee handbook, workplace safety — versioned |
| **Approval Groups**   | Multi-level approvals        | Configurable approval chains for leave, claims, timesheets                                |
| **Alerts**            | Regulatory updates           | Published regulatory change notifications with read/dismissed tracking                    |
| **Emergency HR**      | Crisis response guides       | Structured step-by-step guides for workplace emergencies with deadlines and checklists    |
| **Client Management** | Multi-tenant for consultants | Client company list with compliance scoring, risk tiers                                   |
| **Help Centre**       | Self-service support         | FAQ articles, getting-started guide                                                       |
| **Settings**          | User preferences             | Notifications, display, language, password, data import/export                            |

---

## Layer 2: Deterministic Compliance — Zero AI

### 7 Statutory Calculators

Every calculator uses published statutory tables. The AI is never involved in computation. Numbers are exact, auditable, and reproducible.

| Calculator                | What It Computes                                | Key Details                                                                            |
| ------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------- |
| **CPF Contributions**     | Employer + employee CPF with OA/SA/MA breakdown | All age bands, all citizenship tiers (SC, PR Year 1-3+), OW ceiling, AW ceiling        |
| **Leave Entitlement**     | Statutory leave by service years                | 13 leave types, annual progression (7→14 days), sick leave tiers, maternity, childcare |
| **Overtime Pay**          | OT rates by scenario                            | 1.5x weekday, 2x rest day, 2x public holiday, 3x holiday OT. Part IV salary ceiling    |
| **Notice Period**         | Required notice by tenure                       | 4-tier scale from Employment Act Section 10                                            |
| **Retrenchment Benefits** | Severance computation                           | Based on years of service and last drawn salary                                        |
| **Quota & Levy**          | Foreign worker ratios and costs                 | Dependency Ratio Ceiling by sector, levy rates by pass type (EP/SP/WP)                 |
| **Cost to Company**       | Full employment cost breakdown                  | Base salary + employer CPF + SDL + levy + benefits = total cost                        |

**Available on**: Web dashboard + mobile app (mobile runs calculations natively on-device)

### Knowledge Base

| Metric                | Value                                                                             |
| --------------------- | --------------------------------------------------------------------------------- |
| Structured provisions | 89+                                                                               |
| Regulatory domains    | 6 (Employment Act, CPF, Foreign Manpower, Fair Employment, Workplace Safety, Tax) |
| Content format        | Formal legal text + plain-language summary + interpretation notes                 |
| Cross-references      | Provision-to-provision relationships mapped                                       |
| Practical examples    | Worked scenarios with calculations                                                |
| Rate tables           | Historical and current rates with effective dates                                 |
| Search                | Semantic (AI-powered) + keyword fallback                                          |

---

## Layer 3: AI Intelligence

### Advisory Engine

The core differentiator. Ask a question about employment law in natural language — get a cited, risk-classified, safety-checked response.

| Capability                | Detail                                                                                                                     |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Natural language Q&A**  | Ask anything about employment law — "What are the CPF rates for a 35-year-old earning $5,000?"                             |
| **Real-time streaming**   | Server-Sent Events (SSE) — watch the response build in real time                                                           |
| **Legal citations**       | Every claim traced to a specific Act, Section, subsection                                                                  |
| **Risk classification**   | 3-tier system: GREEN (routine), AMBER (sensitive), RED (consult a lawyer)                                                  |
| **Tool invocation**       | AI decides when to call calculators — "What are the CPF rates?" triggers the deterministic CPF calculator, not an AI guess |
| **Conversation memory**   | Multi-turn conversations with context preservation                                                                         |
| **Professional referral** | RED-tier queries include explicit "stop and consult a lawyer" guidance with contact numbers                                |
| **Disclaimers**           | Risk-appropriate disclaimers calibrated to query sensitivity                                                               |

### 13-Step Safety Chain

Every advisory query passes through 13 safety checks. No exceptions.

| Step | What It Does                                                       | AI? |
| ---- | ------------------------------------------------------------------ | --- |
| 1    | Input sanitization (XSS, injection)                                | No  |
| 2    | Rate limiting (per-user, per-company)                              | No  |
| 3    | Prompt injection screening (8+ patterns)                           | No  |
| 4    | Circumvention detection (10+ patterns — "how to avoid paying CPF") | No  |
| 5    | Scope screening (is this an HR question?)                          | Yes |
| 6    | Budget check (monthly spending cap)                                | No  |
| 7    | Trust genesis record (EATP audit trail starts)                     | No  |
| 8    | LLM context resolution (which provider, which key)                 | No  |
| 9    | **Advisory engine** (the main AI response with tool calling)       | Yes |
| 10   | Citation validation (do cited provisions actually exist?)          | No  |
| 11   | Risk-tier classification                                           | No  |
| 12   | Response screening (TAFEP compliance check)                        | No  |
| 13   | Trust chain recording (EATP audit trail completed)                 | No  |

**11 of 13 steps are deterministic.** The AI handles interpretation and synthesis. Everything else is guardrails.

### Trust Lineage (EATP)

Every AI response carries a cryptographic audit trail.

| Record                    | What It Proves                                                                              |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| **Genesis Record**        | What was asked, when, by whom, system state at time of query                                |
| **Agent Attestations**    | Which specialist agents contributed, what sources they consulted, confidence level          |
| **Constraint Envelope**   | What the AI was allowed to do — explicit boundaries on scope, authority, data access        |
| **Verification Gradient** | Monotonic escalation: auto-approved → flagged → held → blocked (can only go up, never down) |
| **Audit Anchor**          | Tamper-evident hash chain — proves the record hasn't been altered                           |

**Why this matters for Japanese MNCs**: This is digital ringi. Every AI decision has the same traceability that Japanese corporate governance expects from internal approval processes.

### Shadow Agent

AI embedded in every page — not a chatbot in a sidebar.

| Component                   | What It Does                                                                        | AI? |
| --------------------------- | ----------------------------------------------------------------------------------- | --- |
| **Contextual intelligence** | Knows which page you're on, what data you're looking at                             | No  |
| **Intent classification**   | Understands natural language commands ("approve John's leave")                      | Yes |
| **PACE safety model**       | Preview → Approve → Confirm → Exit — AI never acts without human approval           | No  |
| **Entity resolution**       | Resolves "John" to the right employee record                                        | No  |
| **Workflow composition**    | Breaks multi-step commands into individual API calls                                | No  |
| **Proactive briefing**      | Morning briefing cards with pending actions, expiring permits, compliance deadlines | No  |
| **Contextual nudges**       | Page-aware suggestions ("3 leave requests pending approval")                        | No  |
| **Behavioral observation**  | Learns usage patterns over time                                                     | No  |

**9 of 10 shadow agent components are deterministic.** Only intent classification uses AI.

---

## Multi-Provider AI Support

Central supports multiple AI providers. Companies choose their own.

| Provider          | Status                   | Use Case                                    |
| ----------------- | ------------------------ | ------------------------------------------- |
| **Google Gemini** | Primary (server default) | Advisory, embeddings, intent classification |
| **OpenAI**        | Fallback                 | Same capabilities, alternative provider     |
| **Anthropic**     | BYOK supported           | Company-configured                          |
| **DeepSeek**      | BYOK supported           | Cost-effective alternative                  |
| **Mistral**       | BYOK supported           | European data residency                     |
| **Ollama**        | Supported                | On-premise / air-gapped deployment          |
| **Custom**        | Supported                | Any OpenAI-compatible endpoint              |

Users configure their preferred provider in **Settings > AI Configuration**. BYOK keys are encrypted at rest and bypass the server's default budget cap.

---

## Security & Compliance

| Capability             | Detail                                                            |
| ---------------------- | ----------------------------------------------------------------- |
| **Authentication**     | JWT + bcrypt + Google OAuth SSO                                   |
| **Tenant isolation**   | Every query scoped to company_id — enforced at API layer          |
| **Field encryption**   | NRIC, bank accounts encrypted at rest with masking for display    |
| **LLM key encryption** | BYOK API keys encrypted with Fernet before database storage       |
| **PDPA compliance**    | Access logging, consent tracking, data minimization               |
| **Rate limiting**      | Per-IP auth limits, per-user advisory limits                      |
| **Input validation**   | NaN/Infinity checks, text length limits, CSV injection prevention |
| **Audit trail**        | LLM key events, PDPA access, admin actions — all logged           |
| **Security testing**   | 7 red team rounds, 22+ security issues found and fixed            |

---

## Mobile App (Flutter)

Full-featured companion app with native performance.

| Feature                | Detail                                           |
| ---------------------- | ------------------------------------------------ |
| **Advisory chat**      | SSE streaming with citations and risk tiers      |
| **7 calculators**      | Native Dart — runs on-device, no API call needed |
| **Compliance checker** | Category-by-category regulatory health           |
| **Documents**          | Template browsing and generation                 |
| **Emergency HR**       | Crisis response guides                           |
| **Alerts**             | Regulatory update notifications                  |
| **Analytics**          | Dashboard metrics                                |
| **Auth**               | Login, signup, forgot password                   |
| **Onboarding**         | Guided first-run experience                      |

---

## Integration Architecture (MCP)

35+ integration adapters with production-grade infrastructure (circuit breakers, retry logic, idempotency, PII filtering, audit logging). Adapters are architecturally ready — activation requires partner API credentials.

| Category           | Adapters                                                                 | Status                 |
| ------------------ | ------------------------------------------------------------------------ | ---------------------- |
| **Government**     | MOM, IRAS, CPF Board, ACRA, MyInfo (Singpass), SkillsFuture, data.gov.sg | Architecture ready     |
| **Accounting**     | Xero, QuickBooks, Financio, Zoho Books                                   | OAuth 2.0 flows built  |
| **Banking**        | PayNow, GIRO, Wise, Aspire                                               | API structures defined |
| **Communications** | Slack, Telegram, WhatsApp, Microsoft Teams, Email (Resend/SES), SMS      | Webhook handlers built |
| **HRIS Sync**      | Talenox, HREasily                                                        | Export/import defined  |
| **Storage**        | AWS S3                                                                   | Functional             |

---

## What This Means for Your Organization

### Without AI (free, unlimited)

You get a complete HRIS that replaces paid platforms ($4-10/employee/month):

- Payroll with statutory deductions
- Leave management with auto-calculated balances
- Attendance, shifts, claims, recruitment, appraisals
- 7 deterministic calculators
- Compliance checking against employment law
- Document generation from templates
- Full web + mobile experience

### With AI (the intelligence layer)

You get everything above, plus:

- Employment law advisory with cited legal provisions
- Risk-aware responses that know when to say "consult a lawyer"
- Cryptographic audit trail on every AI response (EATP trust lineage)
- AI embedded in every page (shadow agent) — proactive compliance alerts
- 13-step safety chain on every query
- Semantic knowledge base search across 6 regulatory domains

### The Governance Difference

| Capability            | Generic AI (ChatGPT)                      | Central                                               |
| --------------------- | ----------------------------------------- | ----------------------------------------------------- |
| Legal citations       | None                                      | Specific Act, Section, subsection                     |
| Risk awareness        | None — same confident tone for everything | 3-tier system (GREEN / AMBER / RED)                   |
| Calculations          | AI guesses numbers                        | Deterministic calculators (zero AI, exact arithmetic) |
| Professional referral | Generic "seek advice"                     | Specific contacts with phone numbers                  |
| Audit trail           | None                                      | EATP cryptographic trust lineage                      |
| Safety chain          | None                                      | 13 checks, every query, every time                    |
| Knows its limits      | Never                                     | RED tier = "stop, call a lawyer"                      |

---

## Pricing

| Tier                 | What's Included                                             | Price                       |
| -------------------- | ----------------------------------------------------------- | --------------------------- |
| **Full platform**    | Complete HRIS + AI advisory + support SLA                   | USD 8-15 / employee / month |
| **AI advisory only** | Advisory engine alongside existing HRIS                     | USD 3-5 / employee / month  |
| **Proof-of-concept** | 3 regulatory domains, 4-6 weeks, validated by legal counsel | Fixed fee engagement        |

All pricing includes ongoing regulatory updates, knowledge base maintenance, and technical support.

---

## Technical Architecture

```
┌─────────────────────────────────────────────────┐
│                  Clients                         │
│         Web (Next.js) + Mobile (Flutter)         │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              Caddy (Auto-HTTPS)                  │
│         /api/* → Backend | /* → Frontend         │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│           FastAPI Backend (Python)                │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ HRIS     │  │ Advisory │  │ Shadow Agent  │  │
│  │ Engine   │  │ Engine   │  │ Intelligence  │  │
│  │ (22 mod) │  │ (6 spec) │  │ (10 comp)    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
│       │             │               │            │
│  ┌────▼─────────────▼───────────────▼────────┐  │
│  │         Trust & Safety Layer               │  │
│  │  13-step chain │ EATP │ Guardrails │ PACE  │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────┐  ┌─────────┐  ┌──────────────┐  │
│  │ PostgreSQL │  │  Redis  │  │ LLM Provider │  │
│  │ + pgvector │  │ (cache) │  │ (Gemini/OAI) │  │
│  └────────────┘  └─────────┘  └──────────────┘  │
└──────────────────────────────────────────────────┘
```

**Built on**: Kailash SDK (Terrene Foundation, Apache 2.0)
**Deployment**: Docker Compose, AWS/GCP, auto-HTTPS via Caddy
**Database**: PostgreSQL 16 + pgvector for semantic search
**Cache**: Redis 7
