# Plan: Shadow Agent Execution Layer

## Architecture

**Hierarchical Intent → Action**: User message → Intent Classifier (module + action + entities) → Module Executor (API calls) → Response Formatter → User.

The shadow agent uses the **user's own JWT** for all API calls — same permissions, same tenant isolation. No privilege escalation.

## Components

### 1. Intent Classifier (`ShadowIntentClassifier`)

LLM-based agent that receives the user message + current page context and outputs:

```json
{
  "module": "employees",
  "action": "create",
  "entities": { "name": "John", "salary": 5000, "start_date": "2026-03-24" },
  "requires_confirmation": true,
  "confirmation_message": "Create employee John with salary $5,000 starting 24 Mar 2026?"
}
```

Modules: employees, payroll, leave, claims, attendance, shifts, recruitment, projects, inventory, appraisals, reports, compliance, documents, government, accounting, admin, navigation, advisory, calculator.

### 2. Module Tool Registry (`shadow_tools.py`)

Per-module mapping of natural language actions to API calls. Example for `leave`:

```python
LEAVE_TOOLS = {
    "check_balance": {"method": "GET", "path": "/leave/balances/{employee_id}"},
    "apply": {"method": "POST", "path": "/leave/applications", "params": ["leave_type_id", "start_date", "end_date", "reason"]},
    "approve": {"method": "PATCH", "path": "/leave/applications/{id}/approve"},
    "reject": {"method": "PATCH", "path": "/leave/applications/{id}/reject", "params": ["reason"]},
    "list_pending": {"method": "GET", "path": "/leave/applications?status=pending"},
}
```

### 3. Action Executor (`ShadowExecutor`)

Makes HTTP calls to the Arbor API using the user's JWT:

- Reads: execute immediately, return data
- Writes: show confirmation preview first, wait for user approval
- Multi-step: chain calls, show progress for each step
- MCP tools: call via the MCP server endpoints

### 4. Confirmation Manager

For destructive/write actions:

- Format a human-readable preview: "I'll create employee John with salary $5,000. Proceed?"
- Wait for explicit "yes" / "confirm" / approval click
- Only then execute
- Government submissions require double confirmation

### 5. Response Formatter

Translates raw API responses into conversational messages:

- API returns `{"id": 42, "name": "John", "status": "active"}`
- Arbor says: "Done — John has been added as an employee (ID: 42). He's set up and ready to go."

### 6. Shadow API Endpoint

`POST /shadow/execute` — the backend entry point:

```json
// Request
{
  "message": "Onboard John, salary $5000, starts Monday",
  "page_context": "/employees",
  "conversation_id": 123
}

// Response
{
  "type": "confirmation_required",
  "message": "I'll create employee John with salary $5,000 starting 24 Mar 2026. Shall I proceed?",
  "actions": [
    {"step": 1, "description": "Create employee record", "status": "pending"},
    {"step": 2, "description": "Generate Key Employment Terms", "status": "pending"},
    {"step": 3, "description": "Send onboarding email", "status": "pending"}
  ]
}

// After user confirms
{
  "type": "execution_complete",
  "message": "John has been onboarded:\n- Employee record created\n- KET generated\n- Welcome email sent",
  "actions": [
    {"step": 1, "description": "Create employee record", "status": "done", "result_id": 42},
    {"step": 2, "description": "Generate Key Employment Terms", "status": "done"},
    {"step": 3, "description": "Send onboarding email", "status": "done"}
  ],
  "navigation": "/employees/42"
}
```

## Implementation Phases

### Phase 1: Core Backend (M61)

- T451: Intent classifier agent (LLM-based, Kaizen)
- T452: Module tool registry (19 modules, key actions per module)
- T453: Action executor (HTTP client with user JWT forwarding)
- T454: Confirmation manager (preview → approve → execute flow)
- T455: Response formatter (API response → conversational message)
- T456: Shadow execute endpoint (`POST /shadow/execute`)
- T457: Shadow confirm endpoint (`POST /shadow/confirm`)

### Phase 2: Module Coverage (M62)

- T458: Employee module tools (create, update, invite, documents)
- T459: Payroll module tools (run, preview, payslips, adhoc)
- T460: Leave module tools (apply, approve, balance, encash)
- T461: Claims module tools (submit, approve, reimburse)
- T462: Attendance module tools (clock, records, overtime)
- T463: Shifts module tools (roster, publish, swap)
- T464: Recruitment module tools (post, candidates, interviews)
- T465: Documents module tools (generate KET, contracts)
- T466: Government module tools (CPF, IR8A, MOM)
- T467: Navigation module tools (route to any page)
- T468: Reports module tools (generate, export)

### Phase 3: Frontend Integration (M63)

- T469: Wire CommandSurface to POST /shadow/execute
- T470: Confirmation dialog component
- T471: Execution progress indicator (multi-step actions)
- T472: Result display with navigation links
- T473: Action history (what Arbor did for you)

### Phase 4: Proactive Observations (M64)

- T474: Deadline observer (work pass expiry, CPF due, IR8A filing)
- T475: Anomaly observer (unusual attendance, payroll variance)
- T476: Onboarding observer (incomplete employee profiles, missing KET)
- T477: Push observation to shadow widget as proactive alerts

### Phase 5: Testing + Red Team (M65)

- T478: Intent classifier accuracy tests (100+ queries)
- T479: Execution safety tests (confirmation gates enforced)
- T480: Permission boundary tests (can't exceed user's role)
- T481: Adversarial tests (injection via shadow commands)
- T482: Multi-step execution tests (onboarding, payroll workflows)
