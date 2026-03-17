# AITE Agent Instructions

Preloaded context for AI agents working on the AITE HR Advisory Platform.

## What This Project Is

AITE is an AI-powered HR advisory platform for Singapore SMEs. It provides source-cited guidance on employment regulations across six domains: Employment Act, CPF, Foreign Manpower (EFMA), Fair Employment (TAFEP/WFA), Workplace Safety and Health, and Tax/IRAS.

## Technology Stack

- **Runtime**: Python 3.11+
- **Frameworks**: Kailash SDK ecosystem (Core SDK, DataFlow, Nexus, Kaizen)
- **API Gateway**: Nexus (wraps FastAPI + uvicorn)
- **Database**: PostgreSQL via DataFlow (auto-generated CRUD nodes)
- **Cache/Sessions**: Redis
- **Auth**: JWT with JTI + server-side blocklist (PyJWT + passlib[bcrypt])
- **LLM**: Auto-detects OpenAI or Ollama (qwen2.5 instruct models)
- **Vector Search**: pgvector (with keyword-density fallback)

## Key Directories

```
src/hr_advisory/
  api/              Nexus platform, FastAPI routers, middleware
  agents/           Kaizen agents (orchestrator, specialists, memory)
  models/           DataFlow models (company, user, knowledge base)
  workflows/        Kailash Core SDK workflows (calculators, guardrails, classification)
  trust/            EATP lineage, CARE governance, citation validation
  kb/               Knowledge base content and pipeline
  security/         Input validation, PDPA, rate limiting
  templates/        Document templates (KETs, contracts, policies)
  config/           Settings from environment variables
  mcp_servers/      5 MCP servers, 38 adapters, resilience infrastructure

tests/
  unit/             Fast isolated tests (no DB, no network)
  integration/      DataFlow + KB + agent tests (real Kailash runtime)
  e2e/              Full API scenario tests
```

## Framework-First Rule

Before writing code from scratch, check whether the Kailash frameworks handle it:

- Database operations -> DataFlow (auto-generated nodes)
- API endpoints -> Nexus (routers + multi-channel handlers)
- AI agents -> Kaizen (BaseAgent, signatures, shared memory)
- Workflows -> Core SDK (WorkflowBuilder, LocalRuntime)

## Execution Pattern

```python
# ALWAYS:
runtime = LocalRuntime()
results, run_id = runtime.execute(workflow.build())

# NEVER:
workflow.execute(runtime)  # Wrong direction

# In containers:
runtime = AsyncLocalRuntime()
results, run_id = await runtime.execute_workflow_async(workflow.build(), inputs={})
```

## Environment Variables

All API keys and model names come from `.env`. Never hardcode model strings. See `.env.example` for the full list.

## MCP Integration Layer

### Architecture

- 5 MCP servers: aite-government, aite-accounting, aite-banking, aite-communications, aite-regulatory
- 38 connectors covering SG government APIs, accounting, banking, communications, regulatory monitoring
- Shadow agent discovers tools via registry and calls them through natural language objectives

### Key Modules

- `src/hr_advisory/mcp_servers/base.py` -- AiteMCPServer base class
- `src/hr_advisory/mcp_servers/registry.py` -- Server discovery
- `src/hr_advisory/mcp_servers/resilience.py` -- Circuit breakers (25 pre-configured)
- `src/hr_advisory/mcp_servers/idempotency.py` -- Submission ledger (prevents double-submit)
- `src/hr_advisory/mcp_servers/saga.py` -- Multi-step workflow state machine
- `src/hr_advisory/mcp_servers/pii_filter.py` -- PII stripping for PDPA compliance
- `src/hr_advisory/mcp_servers/confirm_action.py` -- Human approval gates
- `src/hr_advisory/api/routers/integrations.py` -- API endpoints (13 endpoint groups)

### Critical Rules

- Government submissions MUST use idempotency ledger
- OAuth tokens MUST be encrypted at rest (Fernet)
- Webhooks MUST verify signatures when signing secret is configured
- MyInfo state parameter is REQUIRED (not optional)
- Circuit breaker reset requires admin role
- Tool names in tool_selector.py MUST match actual @server.tool() registrations
