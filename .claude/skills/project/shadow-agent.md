# Shadow Agent Skill

Arbor's intelligence layer: intent classification, PACE execution loop, tool registry, trust tiers, entity resolution, workflow composition, observation/memory, ambient context.

## Module Map

| Module            | Backend                              | Frontend                                                | Tests                              |
| ----------------- | ------------------------------------ | ------------------------------------------------------- | ---------------------------------- |
| Intent Classifier | `shadow/intent_classifier.py`        | —                                                       | `test_shadow_intent.py`            |
| Tool Registry     | `shadow/tool_registry.py`            | —                                                       | `test_shadow_engine.py`            |
| Executor          | `shadow/executor.py`                 | —                                                       | `test_shadow_workflows.py`         |
| PACE Manager      | `shadow/pace.py`                     | `shadow-agent/PaceCard.tsx`                             | `test_shadow_pace.py`              |
| Formatter         | `shadow/formatter.py`                | `shadow-agent/ArborResult.tsx`                          | `test_shadow_engine.py`            |
| Entity Resolver   | `shadow/entity_resolver.py`          | —                                                       | `test_shadow_entity_resolver.py`   |
| Workflow Composer | `shadow/workflow_composer.py`        | —                                                       | `test_shadow_workflow_composer.py` |
| Observation       | `shadow/observation.py`              | —                                                       | `test_shadow_observation.py`       |
| Memory            | `shadow/memory.py`                   | —                                                       | `test_shadow_memory.py`            |
| Briefing          | `shadow/briefing.py`                 | `shadow-agent/ShadowBriefingCard.tsx`                   | —                                  |
| Nudges            | `shadow/nudges.py`                   | —                                                       | —                                  |
| Scope Guard       | `shadow/guardrails.py`               | —                                                       | `test_shadow_adversarial.py`       |
| Permissions       | (trust levels in tool_registry+pace) | —                                                       | `test_shadow_permissions.py`       |
| API Router        | `api/routers/shadow.py`              | `services/api/shadow.ts`                                | `test_shadow_engine.py`            |
| Command Surface   | —                                    | `shadow-agent/CommandSurface.tsx`                       | —                                  |
| Overlay/History   | —                                    | `shadow-agent/ArborOverlay.tsx`, `ArborHistory.tsx`     | —                                  |
| Annotations       | —                                    | `shadow-agent/ShadowMargin.tsx`, `InlineAnnotation.tsx` | —                                  |

All backend paths relative to `src/hr_advisory/`. All frontend paths relative to `apps/web/src/components/`. All test paths relative to `tests/unit/`.

## PACE Loop (Preview -> Approve -> Confirm -> Execute)

The PACE loop governs all write operations. Read operations bypass PACE entirely.

### Session States

```
preview -> awaiting_double_confirm (if double_confirm) -> executing -> done/failed
        \-> cancelled
```

### Trust Level Decision Tree

```
Is action in _AUTONOMOUS_ACTIONS?           -> autonomous (no PACE)
Is action in _DOUBLE_CONFIRM_ACTIONS?       -> double_confirm (2-step gate)
Is module in _DOUBLE_CONFIRM_MODULES?       -> double_confirm
Is action in _ALWAYS_PROPOSE_ACTIONS?       -> always_propose (5s cooldown)
Otherwise                                   -> propose (single confirm)
```

### Cooldown and Undo

- **Cooldown**: 5 seconds for `always_propose` and `double_confirm` — server-side monotonic timer prevents clock skew
- **Undo window**: 8 seconds after completion
- **Undoable actions**: leave.apply (withdraw), claims.create/submit (withdraw), attendance.clock_in/clock_out (reverse)

### PaceSession Dataclass

```python
@dataclass
class PaceSession:
    id: str                    # UUID
    user_id: str               # Owner (tenant isolation)
    intent_module: str         # e.g., "leave"
    intent_action: str         # e.g., "apply"
    confirmation_message: str  # Human-readable preview
    steps: list[PaceStep]      # Execution steps
    trust_level: str           # autonomous|propose|always_propose|double_confirm
    status: str                # preview|awaiting_double_confirm|executing|done|failed|cancelled
    results: list              # Step execution results
    confirmed_count: int       # 0, 1, or 2 (for double confirm)
    created_at: float          # monotonic timestamp
```

## Tool Registry Pattern

Tools are registered as frozen dataclasses mapping (module, action) to API endpoints:

```python
@dataclass(frozen=True)
class ToolDefinition:
    module: str          # e.g., "employees"
    action: str          # e.g., "list"
    method: str          # GET, POST, PATCH, PUT, DELETE
    path: str            # e.g., "/employees" or "/employees/{employee_id}"
    params: list[str]    # Required parameter names
    trust_level: str     # autonomous|propose|always_propose|double_confirm
    description: str     # Human-readable description
    is_mcp: bool         # True for MCP tools (government, accounting, banking)
```

### Adding a New Tool

1. Add `ToolDefinition` to `_register_core_tools()` in `tool_registry.py`
2. Set correct trust level (reads=autonomous, writes=propose, deletes=always_propose, gov/financial=double_confirm)
3. Add intent patterns to `intent_classifier.py` (both LLM prompt and rule-based fallback)
4. Add entity mappings to `entity_resolver.py` if the module has non-obvious param names
5. Add tests to `test_shadow_engine.py`

### Tool Coverage (100+ tools across 21 modules)

- **employees** (11): list, get, create, update, delete, search, invite, import, documents, self_update, directory
- **payroll** (13): list, get, calculate, approve, cancel, mark_paid, simulate, variance, pay_items, schemes, adhoc, settings, reports
- **leave** (12): list, get, apply, approve, reject, withdraw, cancel, balance, encashment, oil, types, calendar
- **attendance** (11): list, clock_in, clock_out, today, summary, settings, approve_timesheet, lateness, auto_clockout, delete, export
- **claims** (7): list, get, create, submit, approve, reject, categories
- **navigation** (33+): navigate to any frontend route
- **government** (5 MCP): cpf_submit, ir8a_submit, ir21_generate, work_pass_check, levy_check
- **accounting** (3 MCP): post_payroll_journal, post_claims_journal, reconcile
- Plus: recruitment, projects, inventory, appraisals, admin, documents, reports, calculator, settings, shifts, compliance, search, advisory

## Intent Classification

### LLM Classification (Primary)

- Model: gpt-5-mini (configurable via env)
- Temperature: 0, max_tokens: 512
- Prompt includes 19 module descriptions with available actions
- Attachment detection (bulk_import, document_upload, receipt_upload, payroll_import)
- Async via `asyncio.to_thread()` to avoid blocking the event loop

### Rule-Based Fallback

100+ keyword patterns covering common commands:

- "list employees", "show staff" -> employees.list
- "apply leave", "take day off" -> leave.apply
- "clock in", "punch in" -> attendance.clock_in
- "run payroll", "calculate salary" -> payroll.calculate
- Default: routes to advisory pipeline (not an error)

### Attachment Detection

3-tier specificity: payroll keywords > receipt keywords > document keywords > bulk import keywords > generic.

## Entity Resolution

Maps LLM-extracted entity names to API parameter names:

```python
# Module-specific mappings
employees: name -> full_name, salary -> basic_salary, start -> date_of_joining, department -> department_name, role -> designation
leave: type -> leave_type_id, days -> duration, reason -> remarks
payroll: month -> pay_period
```

### Date Resolution

- "today" -> today's ISO date
- "tomorrow" -> tomorrow's ISO date
- "next week" -> next Monday
- "next Monday/Friday/etc." -> next occurrence of that weekday
- ISO dates (YYYY-MM-DD) -> pass through

## Workflow Composition

Expands single intents into multi-step PACE workflows:

### Employee Onboarding (employees.create -> 3 steps)

1. Create employee (POST /employees/invite)
2. Generate KET document (POST /document/generate, template_id=ket)
3. Send invite email (POST /employees/invite with email)

### Employee Import (employees.import -> 2 steps)

1. Preview import (POST /employees/import/preview)
2. Execute import (POST /employees/import/execute)

Single-step intents bypass the composer (returns None).

## Observation and Memory

### Observation Store

- Records: page views, clicks, form submissions
- In-memory bounded deque (max 10,000 per user with LRU eviction)
- `infer_intent()` detects behavioral patterns and suggests nudges

### Memory Store

- Distills observations into themed summaries
- UserMemory: themes[], patterns[], preferences{}, last_distilled
- NOT chat logs — behavioral intelligence
- In-memory bounded dict (max 10,000 users with LRU eviction)

## Ambient Context

### Briefing Engine (Deterministic, No LLM)

- Pending actions (leave approvals, claim approvals, payroll runs, shift assignments)
- Upcoming deadlines (CPF 14th, IR8A 1 Mar, foreign worker levy, etc.)
- Attention needed (compliance gaps, missing documents, expiring work passes)
- Quick stats (active employees, pending requests, payroll status)

### Nudges Engine (Deterministic, No LLM)

- Types: deadline, anomaly, completion, regulatory
- Max 3 per request, sorted by urgency
- Page-aware: different nudges per page context

## Executor Security

### Path Parameter Validation

```python
_PATH_PARAM_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
# Rejects: "../", "/", null bytes, special characters
# Prevents: SSRF, directory traversal, path injection
```

### JWT Forwarding

- User's exact JWT forwarded in Authorization header
- Never escalates privileges
- MCP tools receive only company_id/user_id (extracted from JWT, not raw token)

### Error Translation

All HTTP errors translated to user-friendly messages. Never expose stack traces or internal details.

### Connection Pooling

- Shared httpx.AsyncClient singleton (lazy initialization)
- 30s timeout, 100 max connections, 20 keepalive connections

## Frontend Integration

### CommandSurface

- Keyboard shortcut: Cmd+K / Ctrl+K
- Suggested commands by role (admin vs employee)
- File upload support for attachment intents
- Result rendering: text, navigation, calculator, advisory, PACE

### PaceCard States

- preview: Show steps + confirm/cancel buttons
- cooldown: 5s countdown with disabled confirm button
- double_confirm: Amber warning + second confirmation required
- executing: Step-by-step progress with spinner
- done: Success message + undo link (if undoable)
- failed: Error message + retry button

### ArborOverlay

- Floating button to open command surface
- Badge with pending action count
- Context-aware suggestion preview

### ArborResult

- Renders different result types (text, navigation, calculation, error)
- Advisory results with risk tier badge + citations

### ArborHistory

- List of recent commands with timestamps
- Success/failure indicators
- Undo buttons for undoable actions within window

## API Endpoints (13 total)

| Method | Path                   | Purpose                         | Auth |
| ------ | ---------------------- | ------------------------------- | ---- |
| POST   | /shadow/execute        | Main command entry point        | Yes  |
| POST   | /shadow/confirm        | Confirm PACE session            | Yes  |
| POST   | /shadow/confirm/stream | Confirm with SSE streaming      | Yes  |
| POST   | /shadow/cancel         | Cancel PACE session             | Yes  |
| POST   | /shadow/undo           | Undo recent action              | Yes  |
| GET    | /shadow/history        | User action history             | Yes  |
| GET    | /shadow/context        | Page compliance context         | Yes  |
| GET    | /shadow/briefing       | Morning briefing                | Yes  |
| GET    | /shadow/nudges         | Page nudges                     | Yes  |
| POST   | /shadow/observe        | Record observation              | Yes  |
| GET    | /shadow/memory         | Get user memory                 | Yes  |
| POST   | /shadow/distill        | Trigger memory distillation     | Yes  |
| POST   | /shadow/upload         | File upload with intent routing | Yes  |

## Production Upgrade Path

Current state is in-memory for dev. Production requires:

- PACE sessions -> Redis
- Observation store -> Redis or PostgreSQL
- Memory store -> PostgreSQL
- Action history -> PostgreSQL (DataFlow model)
- Rate limiting -> Redis (already has upgrade path)
- Audit logging -> dedicated audit table

## Constants

```python
_SESSION_TTL_SECONDS = 600      # 10 minutes
_UNDO_WINDOW_SECONDS = 8        # Undo window after completion
_COOLDOWN_SECONDS = 5           # Cooldown for dangerous actions
_MAX_SESSIONS = 10000           # LRU eviction threshold
_MAX_HISTORY_PER_USER = 100     # Action history per user
_MAX_HISTORY_USERS = 10000      # Users with history
_MAX_OBSERVATIONS = 10000       # Per-user observation limit
_MAX_MEMORY_USERS = 10000       # Users with memory
```

## HRIS Integration (Added 2026-04-06)

### Context Sources

`_build_compliance_context(company_id)` queries 8 sources: company profile, employees, policies, KET documents, payroll runs, leave configs, shift templates, content updates. Returns real compliance data. Leave context adds pending count + upcoming team leave (7 days).

### Observation Personalisation

`_generate_suggestions_from_observations()` in nudges.py: 30-day window, frequency-based mapping:

- Payroll views -> "Next payroll due in X days"
- Leave views -> "X pending leave approvals"
- Employee views -> "X probation employees ending this month"
- Compliance views -> "Compliance score X%"

### HRIS Tools

- `payroll.validate` (autonomous) -> 4 checks: employee coverage, CPF rates, zero-salary, variance >20%
- `leave.team_balances` (autonomous) -> aggregated balances, low-balance alerts, pending count
- Both require `owner`/`hr_manager` role

### CPF Briefing

`_cpf_validation()`: deadline reminder (14th within 14 days), month-over-month variance >10% flagged with explanation.

### Attention Widget

- `useShadowNudges` hook: 60s polling, session-scoped seen tracking
- ShadowWidget: pulsing red badge, `shadow-nudge-pulse` animation, accessible aria-label
- `prefers-reduced-motion` respected

## Related Docs

- `docs/00-authority/08-shadow-agent.md` — Architecture authority doc
- `workspaces/hr-ai-advisory/01-analysis/15-shadow-agent-execution/` — Analysis artifacts
- `workspaces/hr-ai-advisory/02-plans/05-shadow-execution-plan.md` — Implementation plan

## Related Agents

- `shadow-agent-specialist` — Primary agent for all shadow agent work
- `arbor-platform-specialist` — Platform integration (router registration)
- `arbor-web-specialist` — Frontend components integration
- `advisory-safety-chain-specialist` — Advisory routing from shadow agent
