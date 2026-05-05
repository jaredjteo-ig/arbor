# Arbor

<p align="center">
  <img src="https://img.shields.io/badge/platform-Kailash%20SDK-7C3AED.svg" alt="Kailash SDK">
  <img src="https://img.shields.io/badge/architecture-COC%205--Layer-blue.svg" alt="COC 5-Layer">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="Apache 2.0">
</p>

<p align="center">
  <strong>AI-powered HR advisory and workforce management for Singapore</strong><br>
  Built on <a href="https://github.com/terrene-foundation/kailash-py">Kailash SDK</a> with the <a href="https://github.com/terrene-foundation/kailash-coc-claude-py">COC methodology</a> for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a>.
</p>

---

## What is Arbor?

Arbor is a complete, open-source HRIS (Human Resource Information System) with an AI-powered employment law advisory engine. It is designed for Singapore SMEs and provides:

- **Free Payroll & CPF** -- Run payroll, generate CPF e-Submit files, create payslips
- **AI Compliance Advisor** -- Answers grounded in Singapore employment law with source citations
- **Full HR Suite** -- Leave, claims, attendance, shifts, employee management, document generation
- **MCP Integration Layer** -- 38 connectors across 5 MCP servers for government, accounting, banking, communications, and regulatory systems

### Tech Stack

| Layer                 | Technology                                             |
| --------------------- | ------------------------------------------------------ |
| **Backend**           | Python, Kailash SDK (Core + DataFlow + Nexus + Kaizen) |
| **Frontend (Web)**    | Next.js 16, React, Tailwind v4, TanStack Query         |
| **Frontend (Mobile)** | Flutter, Riverpod 3, GoRouter                          |
| **Database**          | PostgreSQL 16 + pgvector, Redis                        |
| **AI**                | OpenAI / Ollama (configurable via `.env`)              |
| **Auth**              | JWT + bcrypt, Google OAuth                             |

---

## Quick Start

```bash
# Clone
git clone https://github.com/terrene-foundation/arbor.git
cd arbor

# Configure
cp .env.example .env   # Edit with your API keys and DB credentials

# Backend
pip install -e ".[dev]"
python -m hr_advisory.api.main

# Frontend (Web)
cd apps/web && npm install && npm run dev
```

---

## Architecture

```
apps/
  web/               Next.js frontend (React)
  mobile/            Flutter frontend (iOS/Android/Desktop)

src/hr_advisory/
  api/               Nexus-powered REST API (FastAPI)
    routers/         13 route modules (auth, employees, payroll, leave, claims, ...)
    middleware/      Auth, tenant isolation, CORS
  agents/            Kaizen AI agents (advisory, compliance, PDPA)
  calculators/       Deterministic payroll calculators (CPF, leave, OT, cost-to-company)
  kb/                Knowledge base pipeline (employment law, CPF, TAFEP, EFMA)
  models/            DataFlow models (PostgreSQL + pgvector)
  mcp_servers/       5 MCP servers with 38 connectors
  security/          Encryption, PDPA audit logging
  services/          Business logic (company seeding, leave engine)
  templates/         Document generation (payslips, contracts, IR8A)
  trust/             EATP trust lineage, disclaimers

deploy/              Docker, Caddy, staging/production pipeline
docs/                Architecture, trust governance, authority docs
tests/               3-tier testing (unit, integration, E2E)
```

---

## Modules

### Strategy Hub — Cox 8-stage Employee Lifecycle (`/strategy/lifecycle`)

- Single page that walks Strategy → Attract → Recruit → Onboard → Learning → Reward → Progression → Retain
- Health-pill per stage (Healthy / Attention / Action) with thresholds defined in `routers/strategy.py`
- Hero band: headcount actual vs target, open roles, churn YTD vs YoY
- Stage detail panels with KPIs + quick-action deep links into each module
- D&I cross-cutting tile (gender / pass-type composition + completeness metrics)
- Cross-stage activity feed (last 14 days)

### HRIS Engine (Deterministic -- Zero LLM)

- **Payroll** -- Gross-to-net with CPF, SDL, FWL, SHG. Statutory file generation (CPF e-Submit, IR8A, IR21)
- **Leave** -- 13 leave types, gender-aware, service-year progression, pro-ration, carry-forward
- **Claims** -- 6 categories, receipt validation, monthly caps, approval workflow
- **Attendance** -- Clock in/out, GPS/photo, overtime calculation, grace periods
- **Shifts** -- Schedule management, shift rates, roster planning
- **Employee Lifecycle** -- Onboarding, probation, confirmation, termination, work pass tracking

### AI Advisory Engine

- **13-step safety chain** -- Query analysis, KB retrieval, compliance gate, response synthesis, citation validation
- **6 domain specialists** -- Employment Act, CPF, Foreign Manpower, TAFEP, WSH, Tax/IRAS
- **Knowledge base** -- 8 regulatory domains with provision-level granularity
- **Trust lineage** -- EATP attestation on every advisory response

### MCP Integration Layer

- **arbor-government** -- MOM, IRAS, CPF Board, data.gov.sg, SkillsFuture
- **arbor-accounting** -- Xero, QuickBooks, Financio, and SG HRIS platforms
- **arbor-banking** -- PayNow, GIRO, Wise, Aspire
- **arbor-communications** -- Email (SES/Resend), Slack, Teams, WhatsApp, Telegram
- **arbor-regulatory** -- MOM RSS, regulatory change detection, compliance monitoring

---

## Development with COC

This project uses [Cognitive Orchestration for Codegen (COC)](https://github.com/terrene-foundation/kailash-coc-claude-py) -- a five-layer architecture for Claude Code that replaces unstructured vibe coding with institutionally aware AI code generation.

```
Your Natural Language Request
         |
  1. Intent       30 Agents          Who should handle this?
         |
  2. Context      28 Skills          What does the AI need to know?
         |
  3. Guardrails   9 Rules + 9 Hooks  What must the AI never do?
         |
  4. Instructions CLAUDE.md + 20 Cmds What should the AI prioritize?
         |
  5. Learning     Observe -> Evolve  How does the system improve?
         |
  Production-Ready Code
```

### Workspace Commands

| Command      | Phase | Purpose                                         |
| ------------ | ----- | ----------------------------------------------- |
| `/start`     | --    | New user orientation; explains the workflow     |
| `/analyze`   | 01    | Research and validate the project idea          |
| `/todos`     | 02    | Create project roadmap; stops for your approval |
| `/implement` | 03    | Build the project one task at a time            |
| `/redteam`   | 04    | Test everything from a real user's perspective  |
| `/codify`    | 05    | Capture knowledge for future sessions           |
| `/deploy`    | --    | Get the project live                            |
| `/ws`        | --    | Check project status anytime                    |

---

## License

Apache License, Version 2.0. See [LICENSE](LICENSE).

<p align="center">
  <a href="docs/00-authority/README.md">Authority Docs</a> |
  <a href="https://github.com/terrene-foundation/kailash-py">Kailash SDK</a> |
  <a href="https://github.com/terrene-foundation/kailash-coc-claude-py">COC Framework</a>
</p>
