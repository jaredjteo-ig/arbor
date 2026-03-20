# Shadow Agent Architecture

Authority document for the Arbor Shadow Agent intelligence layer.

## Overview

The shadow agent is Arbor's intelligence layer. It is NOT a chatbot. It understands user intent, executes HR actions through a trust-based confirmation loop (PACE), drives the UI, learns user patterns, and provides proactive context.

## 5-Layer Architecture

| Layer      | Purpose                                        | LLM Required | Key Modules                       |
| ---------- | ---------------------------------------------- | ------------ | --------------------------------- |
| Ambient    | Always-present context, briefings, annotations | No           | briefing, nudges, context router  |
| Action     | Execute on behalf of user (100+ tools)         | Yes (intent) | classifier, executor, PACE, tools |
| Navigation | Drive UI to correct page                       | Yes (intent) | classifier, tool registry (nav)   |
| Memory     | Learn user patterns, distill themed summaries  | No           | observation, memory               |
| Proactive  | Act before asked: deadlines, anomalies         | No           | briefing, nudges                  |

## Execution Pipeline

```
User message
  -> Scope guard (block out-of-scope, detect injection)
  -> Intent classifier (LLM with rule-based fallback)
     -> Returns: module, action, entities, trust_level, attachment_intent
  -> Entity resolver (name mapping + date resolution)
  -> Tool registry lookup (module, action -> ToolDefinition)
  -> Workflow composer (expand multi-step if applicable)
  -> Trust level routing:
     autonomous    -> Executor runs immediately, returns result
     propose       -> Create PACE session, return preview
     always_propose -> Create PACE session with 5s cooldown
     double_confirm -> Create PACE session with 2-step gate
```

## Trust Model

4-tier monotonic trust system. Trust can only escalate, never downgrade.

| Tier           | Actions                                    | UX Behavior                     |
| -------------- | ------------------------------------------ | ------------------------------- |
| autonomous     | list, get, view, search, navigate, balance | Execute immediately             |
| propose        | create, update, approve, submit, apply     | Preview + single confirm        |
| always_propose | delete, terminate, cancel, mark_paid       | Preview + 5s cooldown + confirm |
| double_confirm | cpf_submit, ir8a_submit, giro, journals    | Preview + 2-step approval       |

## PACE Session Lifecycle

```
preview -> [cooldown if always_propose/double_confirm]
        -> awaiting_double_confirm [if double_confirm, after 1st confirm]
        -> executing -> done (with 8s undo window) / failed
        \-> cancelled (at any point before executing)
```

### Safeguards

- Sessions expire after 10 minutes (TTL)
- Max 10,000 sessions with LRU eviction
- Session ownership verified (user_id match)
- Cooldown uses monotonic clock (prevents clock skew bypass)
- Undo window is 8 seconds from completion

## Tool Registry

100+ tools across 21 modules. Each tool is a frozen dataclass:

```python
ToolDefinition(module, action, method, path, params, trust_level, description, is_mcp)
```

MCP tools route to 5 servers: arbor-government, arbor-accounting, arbor-banking, arbor-communications, arbor-regulatory.

## Security Architecture

| Control               | Implementation                                        |
| --------------------- | ----------------------------------------------------- |
| Privilege containment | JWT forwarded as-is, never escalated                  |
| Path traversal        | Regex validation on all path parameters               |
| SSRF prevention       | Path param validation + no user-controlled URLs       |
| Tenant isolation      | PACE session user_id == current user                  |
| Injection detection   | Scope guard with adversarial pattern matching         |
| MCP isolation         | Only company_id/user_id passed, never raw tokens      |
| Bounded memory        | All stores: maxlen=10,000, LRU eviction               |
| Connection reuse      | Shared httpx.AsyncClient (30s timeout, 100 max conns) |

## API Surface

13 endpoints under `/shadow/` prefix. All require authentication.

### Execution: execute, confirm, confirm/stream, cancel, undo, history

### Ambient: context, briefing, nudges, observe, memory, distill

### Upload: upload (with intent routing)

## Frontend Components

9 React components in `apps/web/src/components/shadow-agent/`:

- ShadowAgentContext (context + hooks)
- CommandSurface (Cmd+K command bar)
- PaceCard (PACE confirmation flow)
- ArborOverlay (floating widget)
- ArborResult (result display + undo)
- ArborHistory (action history)
- ShadowMargin (inline compliance annotations)
- ShadowBriefingCard (morning briefing)
- InlineAnnotation (regulatory badges)

## Identity

- Prefix: "Arbor: " on all responses
- Color: Teal (#0D6E4F)
- Icon: Leaf
- Voice: Professional, clear, action-oriented

## Test Coverage

465 tests across 10 files covering: intent classification, PACE flow, entity resolution, memory distillation, observation tracking, workflow composition, trust enforcement, adversarial inputs, multi-step execution, and error handling. 3 red team rounds, 25 findings, all resolved.

## Production Upgrade Path

| Component      | Dev (Current)   | Production            |
| -------------- | --------------- | --------------------- |
| PACE sessions  | In-memory dict  | Redis                 |
| Observation    | In-memory deque | Redis or PostgreSQL   |
| Memory         | In-memory dict  | PostgreSQL            |
| Action history | In-memory dict  | PostgreSQL (DataFlow) |
| Rate limiting  | In-memory       | Redis                 |
