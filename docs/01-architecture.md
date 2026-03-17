# System Architecture

## Overview

AITE is built on the Kailash SDK ecosystem -- four frameworks that handle orchestration, data, API delivery, and AI agents respectively. The platform provides HR advisory services for Singapore SMEs across six regulatory domains.

## Kailash SDK Ecosystem

| Framework    | Role                            | Key Usage in AITE                                   |
| ------------ | ------------------------------- | --------------------------------------------------- |
| **Core SDK** | Workflow orchestration          | Calculators, classification, guardrails, compliance |
| **DataFlow** | Zero-config database operations | Company/user models, KB models, auto-generated CRUD |
| **Nexus**    | Multi-channel API gateway       | FastAPI routers, CLI handlers, MCP handlers         |
| **Kaizen**   | AI agent framework              | Orchestrator, specialist agents, shared memory      |

All frameworks build on Core SDK. DataFlow provides auto-generated workflow nodes (e.g., `CompanyCreateNode`, `ProvisionListNode`) from model definitions. Nexus wraps FastAPI and adds multi-channel delivery. Kaizen provides `BaseAgent` with signatures, memory pools, and LLM integration.

## Application Layers

```
Client (Web / CLI / MCP)
       |
  Nexus Gateway
  (CORS, security headers, rate limiting)
       |
  FastAPI Routers              Nexus Handlers
  (REST API endpoints)         (multi-channel: API + CLI + MCP)
       |                              |
  Auth Middleware               Shared Logic
  (JWT, tenant isolation)       (advisory, compliance, search)
       |
  Business Logic
  |- Advisory safety chain (13 steps)
  |- Calculators (CPF, leave, cost-to-company, quota/levy)
  |- Payroll engine (gross-to-net, CPF, SDL, FWL, SHG)
  |- Leave management (types, application, approval, calendar)
  |- Claims & expenses (submission, approval, payroll integration)
  |- Attendance (clock in/out, GPS, lateness, overtime)
  |- Shift scheduling (templates, assignments, availability, hours)
  |- Statutory file generation (CPF e-Submit, IR8A, IR21, bank GIRO, payslips)
  |- Compliance checker
  |- Document generator
  |- Learning pipeline
       |
  Trust Layer
  |- EATP lineage (GenesisRecord -> AgentAttestation -> TrustChain)
  |- CARE governance (dual-plane, expert review)
  |- Citation validation
  |- Anti-amnesia constraints
       |
  Data Layer
  |- DataFlow models -> PostgreSQL
  |- Knowledge base (6 domains, provisions, cross-references)
  |- pgvector for semantic search (keyword-density fallback)
  |- Redis for sessions and token blocklist
```

## Agent Architecture

The advisory system uses a supervisor-worker pattern built on Kaizen:

```
User Query
    |
QueryAnalyzerAgent      -- Classifies domains, complexity, risk
    |
OrchestratorAgent       -- Plans specialist dispatch (parallel/sequential/router)
    |
SpecialistAgents        -- Domain-specific (EA, CPF, EFMA, TAFEP, WSH, Tax)
    |
ResponseSynthesizer     -- Merges specialist outputs into a response
```

Each specialist has a **constraint envelope** that defines its allowed and forbidden domains. The orchestrator dispatches at most three specialists per query. Agents share context via `SharedMemoryPool`.

### Specialist Agents

| Agent                         | Domain           | Constraint                                     |
| ----------------------------- | ---------------- | ---------------------------------------------- |
| `employment_act_specialist`   | Employment Act   | Cannot advise on tax, CPF, or foreign manpower |
| `cpf_specialist`              | CPF              | Cannot advise on EA, EFMA, or tax              |
| `foreign_manpower_specialist` | Foreign Manpower | Cannot advise on EA, CPF, or tax               |
| `fair_employment_specialist`  | Fair Employment  | Cannot advise on tax or CPF                    |
| `tax_specialist`              | Tax / IRAS       | Cannot advise on EA or EFMA                    |
| `wsh_specialist`              | Workplace Safety | Cannot advise on tax or CPF                    |
| `compliance_specialist`       | Cross-domain     | Cannot make legal determinations               |

## Knowledge Base

The KB stores Singapore employment legislation and guidelines as structured provisions loaded via DataFlow:

| Domain           | Source Legislation                           |
| ---------------- | -------------------------------------------- |
| Employment Act   | Employment Act 1968 (Cap 91)                 |
| CPF              | Central Provident Fund Act (Cap 36)          |
| Foreign Manpower | Employment of Foreign Manpower Act (Cap 91A) |
| Fair Employment  | TAFEP Guidelines, Workplace Fairness Act     |
| Workplace Safety | WSH Act (Cap 354A), WICA                     |
| Tax              | Income Tax Act, IRAS guidelines              |

Each provision includes: formal text, plain-language summary, section reference, authority level, linked cross-references, applicability rules, and practical examples. Provisions are queried via DataFlow nodes (`ProvisionListNode`, `ProvisionReadNode`, `CrossReferenceListNode`).

## Calculators

All calculators are implemented as Kailash Core SDK workflows:

| Calculator       | Purpose                                                                      |
| ---------------- | ---------------------------------------------------------------------------- |
| CPF Calculator   | 2026 contribution rates by age band and citizenship                          |
| Leave Calculator | Statutory leave entitlements (annual, sick, maternity, paternity, childcare) |
| Cost-to-Company  | Full employer cost including CPF, SDL, levies                                |
| Quota/Levy       | Foreign worker quota and levy by sector                                      |
| Overtime         | Overtime pay calculation per Part IV of Employment Act                       |
| Notice Period    | Statutory notice period by tenure                                            |
| Retrenchment     | Retrenchment benefit estimation                                              |

## Multi-Channel Access

Nexus handlers expose core functionality across three channels simultaneously:

| Handler            | Description                    | Channels      |
| ------------------ | ------------------------------ | ------------- |
| `advisory_query`   | Submit an HR advisory question | API, CLI, MCP |
| `compliance_check` | Run a compliance check         | API, CLI, MCP |
| `search_kb`        | Search the knowledge base      | API, CLI, MCP |

Handlers apply the same safety chain as their REST counterparts (sanitisation, screening, domain detection, citation validation).

## LLM Configuration

The platform auto-detects the available LLM provider from environment variables:

1. **OpenAI** -- Set `OPENAI_API_KEY` and optionally `OPENAI_PROD_MODEL` / `OPENAI_DEV_MODEL`
2. **Ollama** -- Set `OLLAMA_MODEL` (e.g., `qwen2.5:32b-instruct-q8_0`) and `OLLAMA_BASE_URL`

The `DEFAULT_LLM_MODEL` environment variable sets the fallback model. All model names come from `.env` -- never hardcoded.

## Data Flow

```
                      PostgreSQL
                      /        \
          DataFlow Nodes       pgvector
         (CRUD operations)     (semantic search)
              |
         Kailash Runtime
         (LocalRuntime / AsyncLocalRuntime)
              |
         WorkflowBuilder
         (nodes + connections)
```

DataFlow auto-generates CRUD nodes from model definitions in `src/hr_advisory/models/`. These nodes are used directly in routers via `WorkflowBuilder` -- no manual SQL or ORM code needed.
