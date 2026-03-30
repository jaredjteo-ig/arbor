---
type: DISCOVERY
date: 2026-03-30
project: arbor
topic: Red team corrections to engines-vs-primitives analysis
phase: analyze
tags: [architecture, dataflow, nexus, kaizen, red-team]
---

# Red Team Corrections

Claims from 01-analysis.md verified against actual kailash-py source code.

## Corrections

### WRONG: "Agent doesn't support tool calling"

**Evidence**: `Agent.__init__` accepts `tool_access='full'` and `tools=[func1, func2]`.
Agent has 4 tool access levels: `none`, `read_only`, `constrained`, `full`.
Agent accepts plain Python functions as tools (not ToolRegistry schemas).

**Corrected**: Agent supports tool calling via `tool_access` + `tools` params.
Delegate uses `ToolRegistry` with JSON Schema definitions — different tool interface.

**Source**: `kaizen_agents/api/agent.py` — `tool_access`, `tools` params in `__init__`.

### WRONG: "Agent doesn't support streaming"

**Evidence**: `Agent.stream(task)` → `AsyncIterator[str]` — yields plain text tokens.
Also has `Agent.chat(message)` for multi-turn conversations.

**Corrected**: Agent supports streaming (text tokens) and multi-turn chat.
Delegate streaming gives typed events (`TextDelta`, `ToolCallStart`, etc.) — richer.

**Source**: `kaizen_agents/api/agent.py` — `stream()`, `chat()` methods.

### WRONG: "NexusEngine doesn't exist prominently"

**Evidence**: `NexusEngine.builder().preset(Preset.SAAS).build()` is fully functional.
Builder has: `.preset()`, `.bind()`, `.enterprise()`, `.config()`, `.build()`.
Presets: `SAAS`, `API`, `ENTERPRISE`, `DEVELOPMENT`, etc.

**Corrected**: NexusEngine is production-ready with builder + presets.
Arbor should use it instead of `Nexus()` with manual config.

**Source**: `nexus/engine.py` — `NexusEngine`, `NexusEngineBuilder`, `Preset`.

### CONFIRMED: "DataFlowEngine.build() wraps DataFlow() eagerly"

**Evidence**: `DataFlowEngineBuilder.build()` line 205: `DataFlow(database_url=...)`.
The engine constructor is async but internally creates a sync `DataFlow()`.

**Source**: `dataflow/engine.py:205` — `DataFlow(database_url=self._database_url)`.

### CONFIRMED: "DataFlowEngine has no @model decorator"

**Evidence**: `DataFlowEngine` has `register_model(registry, model)` but no `model` property/decorator.
Models still need `@db.model` on the underlying `DataFlow` primitive.

**Source**: `DataFlowEngine` class — `hasattr(DataFlowEngine, 'model')` → `False`.

### CONFIRMED: "COC artifacts don't mention DataFlowEngine"

**Evidence**: `grep -r "DataFlowEngine" .claude/` — zero matches.
`grep -r "NexusEngine" .claude/` — zero matches.
`patterns.md` shows `from kaizen.api import Agent` but no `DataFlowEngine`/`NexusEngine`.

**Source**: `.claude/skills/02-dataflow/SKILL.md`, `.claude/rules/patterns.md` — no engine mentions.

## Updated Architecture Comparison

### Agent vs Delegate — when to use each

| Aspect              | Agent (unified API)       | Delegate (kaizen-agents)        |
| ------------------- | ------------------------- | ------------------------------- |
| **Tool interface**  | Plain Python functions    | ToolRegistry with JSON Schema   |
| **Streaming**       | `stream()` → `str` tokens | `run()` → typed `DelegateEvent` |
| **Multi-turn**      | `chat()` built-in         | Manual conversation injection   |
| **Execution modes** | single, multi, autonomous | Always autonomous               |
| **Budget tracking** | Via config                | Built-in `budget_usd`           |
| **Tool hydration**  | No                        | Yes (progressive disclosure)    |
| **Tool count**      | Works for <30 tools       | Designed for 200+ tools         |

**For Arbor**: Delegate is still the correct choice because:

1. 208 tools need hydration (Agent sends all tools every call)
2. SSE events need typed discrimination (TextDelta vs ToolCallStart)
3. Budget tracking is built into Delegate

**For specialist agents** (if kept): Agent is correct — simple task-based execution with optional tools. The \_KaizenCompatMixin shim is unnecessary; use `Agent.run(task)` directly.

## Updated Recommendations

### DataFlow

- **Keep `DataFlow` primitive** for `@db.model` — no engine equivalent
- **Use `DataFlowEngine`** if adding validation/classification later
- **Upstream fix needed**: kailash-py#171 (lazy connection)

### Nexus

- **Migrate to `NexusEngine.builder().preset(Preset.SAAS).build()`**
- Replaces manual CORS/rate-limit/middleware config
- Low effort, high clarity

### Kaizen

- **Keep `Delegate`** for advisory/shadow (208 tools, SSE streaming)
- **Delete specialist agents** — Delegate handles everything
- If specialists are kept, remove `_KaizenCompatMixin`, use `Agent.run(task)` directly
