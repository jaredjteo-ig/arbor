# Shadow Agent Execution Layer — Architecture Analysis

## The Gap

Arbor today: **observes** (context API) → **advises** (13-step safety chain) → **navigates** (action-registry with 5 types)

Arbor should: **observes** → **understands intent** → **executes on behalf** → **reports results**

The user says "onboard John with $5000 salary starting Monday" and Arbor creates the employee, generates the KET, sets up payroll, and sends the welcome email. Not "here's how to onboard an employee."

## Capability Surface

| Layer           | Count | Examples                                    |
| --------------- | ----- | ------------------------------------------- |
| API endpoints   | 363   | Create employee, run payroll, approve leave |
| MCP tools       | 99    | Submit CPF, generate GIRO, send email       |
| Frontend routes | 33    | Navigate to /payroll, /leave, /employees    |
| Kaizen agents   | 10    | Query analysis, domain specialists          |

## Architecture Decision: Hierarchical Intent → Action

An LLM cannot handle 462 tools in a single context. Instead:

```
User: "Onboard John, salary $5000, starts Monday"
  │
  ▼
┌──────────────────────────────┐
│  Intent Classifier (LLM)     │  → Module: employees
│  "What module + action?"     │  → Action: create
│                              │  → Entities: {name: John, salary: 5000, start: Monday}
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Module Executor             │  → Calls POST /employees with extracted params
│  (per-module tool registry)  │  → Then calls POST /documents/ket for KET
│                              │  → Then calls MCP send_onboarding_invite
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Response Formatter          │  → "Done. John has been onboarded:
│                              │     - Employee record created
│                              │     - KET generated
│                              │     - Welcome email sent
│                              │     - Start date: Monday"
└──────────────────────────────┘
```

### Why Hierarchical (not flat tool list)

- **462 tools in one prompt** = LLM confusion, high token cost, slow
- **Hierarchical routing** = classify into ~15 modules first (cheap), then give the module-specific executor only its ~20-30 tools (focused, accurate)
- Same pattern as the existing advisory pipeline (QueryAnalyzer → DispatchRouter → Specialists)

## Module Registry

| Module      | API endpoints | MCP tools      | Key actions                                      |
| ----------- | ------------- | -------------- | ------------------------------------------------ |
| employees   | 50            | 2 (MyInfo)     | Create, update, invite, documents, custom fields |
| payroll     | 36            | 12 (banking)   | Run payroll, generate payslips, GIRO, adhoc pay  |
| leave       | 19            | 2 (email)      | Apply, approve, reject, check balance, encash    |
| claims      | 18            | 2 (email)      | Submit, approve, reimburse                       |
| attendance  | 18            | 0              | Clock in/out, view records, overtime             |
| shifts      | 17            | 0              | Create roster, publish, swap                     |
| recruitment | 17            | 3 (email)      | Post job, add candidate, schedule interview      |
| projects    | 22            | 0              | Create project, log time, allocate               |
| inventory   | 17            | 0              | Track items, request, transfer                   |
| appraisals  | 13            | 2 (email)      | Launch cycle, submit review, sign off            |
| reports     | 11            | 0              | Generate report, export                          |
| compliance  | 4             | 8 (regulatory) | Check compliance, audit                          |
| documents   | 6             | 4 (storage)    | Generate KET, contract, policy                   |
| government  | 0             | 33             | CPF submit, IR8A, MOM OED                        |
| accounting  | 0             | 22             | Xero/QB journal, export                          |
| admin       | 11            | 0              | User management, settings                        |
| navigation  | 33 routes     | 0              | "Take me to payroll"                             |
| advisory    | 6             | 0              | "What's the rule for..." (existing)              |
| calculator  | 3             | 0              | "Calculate CPF for..." (existing)                |

## Execution Modes

### 1. Direct Action (single API call)

"What's Sarah's leave balance?" → GET /leave/balances?employee_id=sarah_id → "Sarah has 12 days remaining"

### 2. Multi-Step Action (chained calls)

"Onboard John" → POST /employees → POST /documents/ket → POST /email/onboarding → "Done"

### 3. Confirmation-Required Action (destructive/irreversible)

"Run payroll for March" → Arbor shows preview → User confirms → POST /payroll/run → "Payroll processed"

### 4. Navigation Action (frontend routing)

"Where do I manage shifts?" → Navigate to /shifts

### 5. Advisory Action (existing pipeline)

"What's the notice period for termination?" → Existing advisory pipeline → Cited response

## Trust Envelope

Arbor operates within the **same permissions as the user**. It uses the user's JWT token for all API calls. If the user is an employee (not admin), Arbor can only access employee-level endpoints. This is enforced by the existing auth + tenant isolation middleware — no new trust model needed.

### Confirmation Gates

| Action Type          | Confirmation   | Example                          |
| -------------------- | -------------- | -------------------------------- |
| Read data            | No             | "What's Sarah's leave balance?"  |
| Navigate             | No             | "Take me to payroll"             |
| Create record        | Yes (preview)  | "Add a new employee John"        |
| Update record        | Yes (preview)  | "Change Sarah's salary to $6000" |
| Delete record        | Yes (explicit) | "Remove the draft payroll run"   |
| Submit to government | Yes (double)   | "Submit CPF for March"           |
| Send communication   | Yes (preview)  | "Send payslips to all employees" |
| Financial action     | Yes (explicit) | "Process GIRO payment"           |

## What Needs Building

1. **Intent Classifier Agent** — LLM-based: classifies user message into (module, action, entities)
2. **Module Tool Registry** — Maps each module to its callable API endpoints + MCP tools
3. **Action Executor** — Makes the API calls using the user's auth token
4. **Confirmation Manager** — Shows preview for destructive actions, waits for approval
5. **Response Formatter** — Translates API responses into user-friendly messages
6. **Command Surface Integration** — Wire the executor into the existing CommandSurface frontend
7. **Shadow API Endpoint** — New `POST /shadow/execute` endpoint

## What Already Exists (Reuse)

- **CommandSurface.tsx** — Frontend input already exists
- **action-registry.ts** — Has 5 action types, needs extension to "execute"
- **ShadowWidget.tsx** — Persistent UI entry point
- **Auth middleware** — JWT token for API calls
- **MCP servers** — All 99 tools already implemented
- **API endpoints** — All 363 endpoints already exist
- **Kaizen BaseAgent** — Tool calling + shared memory
