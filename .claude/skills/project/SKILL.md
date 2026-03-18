---
name: arbor-hr-advisory
description: "Arbor HR Advisory Platform skills — Singapore employment law advisory, safety chain, trust governance, calculators, KB pipeline. Use when working on any Arbor-specific feature."
---

# Arbor HR Advisory Platform Skills

Project-specific knowledge for the AI-powered HR advisory platform serving Singapore SMEs.

## Skill Files

| File                         | Domain                    | When to Use                                                                                             |
| ---------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------- |
| `sg-employment-law.md`       | Singapore employment law  | KB content, provision accuracy, regulatory domains                                                      |
| `advisory-safety-chain.md`   | 13-step safety chain      | Advisory query pipeline, guardrails, response generation                                                |
| `platform-architecture.md`   | Platform structure        | Router setup, middleware, auth, Nexus integration                                                       |
| `trust-governance.md`        | EATP/CARE/learning        | Trust chains, citation validation, expert review                                                        |
| `calculators.md`             | HR calculators            | CPF, leave, salary, quota, overtime calculations                                                        |
| `kb-management.md`           | Knowledge base pipeline   | Content loading, search, regulatory updates                                                             |
| `auth-security.md`           | Authentication & security | JWT tokens, tenant isolation, rate limiting, PDPA                                                       |
| `document-generation.md`     | Document templates        | Template CRUD, generation, preview, download, history                                                   |
| `company-user-management.md` | Company & user profiles   | Company onboarding, user CRUD, roles, workforce data                                                    |
| `hris-engine.md`             | Full HRIS engine          | Payroll (pay items, schemes, adhoc, simulation, variance), leave (encashment, off-in-lieu, hourly), claims (groups, co-payment, BIK), attendance (lateness brackets, today dashboard), shifts (hourly rates, multipliers, publish), appraisals (templates, periods, reviews, sign-off), projects (assignments, timesheets, allocations, costs), inventory (locations, categories, items, lifecycle state machine, requests), recruitment (job listings, candidates, interviews, hiring), reports (11 types with charts), approval workflows, rate limiting, demo seed data |
| `mcp-integrations.md`        | MCP integration layer     | 5 MCP servers, 38 connectors, circuit breakers, idempotency, sagas, PII filter, webhooks, tool selector |

## Quick Reference

### Project Structure

```
src/hr_advisory/
  api/routers/      23+ FastAPI routers (advisory, payroll, leave, claims, attendance, shifts, employees,
                    appraisals, projects, inventory, recruitment, reports, approval_groups, integrations...)
  agents/           Kaizen agents (orchestrator, specialists)
  models/           60+ DataFlow models (company, user, KB, payroll, leave, claims, attendance, shifts,
                    appraisals, projects, inventory, recruitment, approval groups)
  services/         Payroll calculator, statutory files, encryption, demo seed data
  workflows/        Core SDK workflows (calculators, guardrails)
  trust/            EATP lineage, CARE governance, citations
  kb/               Knowledge base content and pipeline
  security/         Input validation, PDPA, rate limiting (sliding window), PII encryption
  templates/        Document templates (KETs, contracts)
  config/           Settings from environment variables
  mcp_servers/      5 MCP servers, 38 adapters, resilience infra (circuit breakers, sagas, idempotency)
```

### Six Regulatory Domains

1. Employment Act (EA) — wages, hours, overtime, leave, termination
2. CPF — contributions, ceilings, age bands, citizenship
3. Foreign Manpower (EFMA) — work passes, quotas, levies
4. Fair Employment (TAFEP/WFA) — anti-discrimination, fair hiring
5. Workplace Safety (WSH) — employer duties, incident reporting
6. Tax (IRAS) — employer obligations, IR8A/IR21, BIK

### Critical Patterns

```python
# Kailash execution — ALWAYS this direction
runtime = LocalRuntime()
results, run_id = runtime.execute(workflow.build())

# Auth dependency — ALL protected endpoints
current_user: dict = Depends(get_current_user)

# Tenant isolation — ALL company-scoped data
validate_company_access(current_user, requested_company_id=company_id)

# Role check — admin endpoints
require_role(current_user, "owner", "hr_manager")
```

## Related Documentation

- `docs/01-architecture.md` — Full system architecture
- `docs/02-api-reference.md` — Complete API reference
- `docs/03-security.md` — Security architecture
- `docs/04-trust-governance.md` — Trust and governance framework
- `docs/05-testing.md` — Test strategy and coverage
- `docs/00-authority/CLAUDE.md` — Agent preloaded instructions

## Related Agents

- `sg-employment-law-expert` — Singapore employment law domain
- `advisory-safety-chain-specialist` — 13-step safety chain
- `arbor-platform-specialist` — Platform architecture
- `trust-governance-specialist` — EATP/CARE governance
- `hr-calculator-specialist` — Calculator implementations
- `kb-pipeline-specialist` — KB content and pipeline
- `arbor-web-specialist` — Web frontend (Next.js/React)
- `arbor-mobile-specialist` — Mobile frontend (Flutter)
