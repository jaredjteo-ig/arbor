---
type: DISCOVERY
date: 2026-03-30
project: arbor
topic: Engines vs Primitives — Why Arbor uses low-level APIs
phase: analyze
tags: [architecture, dataflow, nexus, kaizen, engines, primitives, coc-gap]
---

# Engines vs Primitives: Analysis

## Question 1: Are the engines feature-complete and usable?

### DataFlowEngine

| Aspect                  | Status                          | Details                                                                                       |
| ----------------------- | ------------------------------- | --------------------------------------------------------------------------------------------- |
| **Builder pattern**     | Available                       | `DataFlowEngine.builder(url).build()` — async                                                 |
| **Validation layer**    | Available                       | Field-level validators (`@field_validator`)                                                   |
| **Data classification** | Available                       | PII/internal/public classification                                                            |
| **Query monitoring**    | Available                       | Slow query detection                                                                          |
| **@db.model decorator** | Delegates to DataFlow primitive | Same eager connection issue                                                                   |
| **Import-time fix**     | **Partial**                     | `build()` is async (can't run at import), but still wraps `DataFlow()` which connects eagerly |
| **Cross-SDK parity**    | Good                            | Matches kailash-rs `DataFlowEngine::builder().build()`                                        |

**Gap**: `DataFlowEngine.build()` still calls `DataFlow(url)` internally, which connects eagerly. The engine doesn't solve the import-time issue — it just wraps the problem. The `@db.model` decorator still needs the underlying `DataFlow` instance.

**Verdict**: 70/100 — feature-complete for enterprise features (validation, classification) but doesn't fix the core problem (eager connection). Migration adds value for validation/classification but doesn't solve the test isolation issue.

### NexusEngine / Nexus Builder

| Aspect                   | Status    | Details                                           |
| ------------------------ | --------- | ------------------------------------------------- |
| **Builder pattern**      | Available | `Nexus()` with presets                            |
| **Presets**              | Available | `Preset.SAAS`, `Preset.API`, etc.                 |
| **Handler pattern**      | Available | `@app.handler()` decorator                        |
| **FastAPI sub-app**      | Available | Nexus creates FastAPI, can be mounted or extended |
| **Middleware**           | Available | Auth, CORS, security headers via plugins          |
| **DataFlow integration** | Available | `auto_discovery=False` for DataFlow               |

**How Arbor uses Nexus today** (platform.py): Arbor creates a `Nexus()` instance, gets the `FastAPI` app from it, then mounts 23+ routers manually. This is essentially using Nexus as a FastAPI factory with CORS/session middleware.

**Gap**: Arbor doesn't use Nexus handlers (`@app.handler`). It manually registers FastAPI routers because the HRIS modules predate Nexus. The engine pattern would work for new services but migrating 120+ existing endpoints to handlers is high effort, low reward.

**Verdict**: 85/100 — Nexus is production-ready. Arbor already uses it correctly for what it needs (platform factory). No migration needed.

### Kaizen: Agent vs BaseAgent vs Delegate

| Layer  | Class                 | Purpose                         | Tool calling       | Streaming        |
| ------ | --------------------- | ------------------------------- | ------------------ | ---------------- |
| **L1** | `BaseAgent`           | Legacy signature-based agents   | No                 | No               |
| **L2** | `Agent` (unified API) | Task-based execution            | Via tools list     | No               |
| **L3** | `Delegate`            | Autonomous tool-calling loop    | Yes (ToolRegistry) | Yes (SSE events) |
| **L3** | `AgentLoop`           | Core loop (Delegate wraps this) | Yes                | Yes              |

**How Arbor uses Kaizen today**:

- **Specialists** (8 agents): Subclass `Agent` via `_KaizenCompatMixin` — use `run_sync(task)` to get text responses. No tool calling. These are the old orchestration pipeline agents (pre-Delegate).
- **Advisory/Shadow**: Uses `Delegate` with 208 tools — the live production path.

**Gap**: The 8 specialist agents inherit from `Agent` but use a shim (`_KaizenCompatMixin.run()`) that converts kwargs → task string → `run_sync()` → parse JSON. This is because:

1. `Agent.run(task)` is task-string-based, not kwargs-based
2. The specialists were designed for `BaseAgent.run(**kwargs)` which returned structured dicts
3. The unified `Agent` API doesn't have a kwargs→structured-output mode

**Correct architecture**:

- Specialists should be deleted entirely — the Delegate handles all advisory via tools
- If specialists are kept for the old orchestration pipeline, they should use `Agent.run(task)` directly with proper prompts, not the kwargs shim

**Verdict**: 60/100 — The Agent API is production-ready but the specialist agents are architectural debt from the pre-Delegate era. The Delegate is the correct layer for all Arbor's AI use cases.

---

## Question 2: Why primitives instead of engines?

### Root Cause: COC Artifact Deficiency

**The COC artifacts systematically guide toward primitives, not engines.**

| Framework    | COC Skill Index (SKILL.md)                              | COC Quickstart         | COC Rules (patterns.md)  | Verdict                             |
| ------------ | ------------------------------------------------------- | ---------------------- | ------------------------ | ----------------------------------- |
| **DataFlow** | `DataFlow` only — zero mention of `DataFlowEngine`      | `DataFlow(url)`        | `DataFlow` patterns only | **Engines invisible**               |
| **Nexus**    | `Nexus()` only — no `NexusEngine` or builder mention    | `Nexus()`              | `Nexus` basic only       | **Engine exists but not prominent** |
| **Kaizen**   | `BaseAgent` as primary, `Agent` in separate design docs | `BaseAgent` quickstart | `Agent` in patterns.md   | **Split brain — two APIs**          |

### Specific COC Gaps

1. **DataFlow SKILL.md** — 40+ skill files, none mention `DataFlowEngine`. The quickstart shows `DataFlow("sqlite:///app.db")` as the entry point. A developer following COC will never discover the engine.

2. **Nexus SKILL.md** — Shows `Nexus()` constructor. The Preset system and builder pattern exist in the SDK but aren't in the skills. The `nexus-quickstart.md` uses the primitive.

3. **Kaizen SKILL.md** — Lists `BaseAgent` as the primary class with 12+ skill files about it. The unified `Agent` API exists in 3 separate design documents (`UNIFIED_AGENT_*.md`) but these are design specs, not usage guides. The skill index doesn't link to them prominently.

4. **patterns.md** — Line 151 correctly shows `from kaizen.api import Agent` but this is in the Kaizen section only. No `DataFlowEngine` or `NexusEngine` patterns anywhere.

5. **Framework specialist agents** — `dataflow-specialist.md`, `nexus-specialist.md`, `kaizen-specialist.md` — these agents are the primary guidance mechanism. If they don't know about engines, Claude Code won't recommend them.

### The Fault Line

This is a **COC Layer 2 (Patterns) failure** — institutional knowledge about the engine APIs exists in the SDK source code but was never codified into the COC artifacts. The pattern-matching that guides Claude Code toward the right API is missing for the engine layer.

The fix is upstream: update the COC template skills and agent definitions to:

1. Default to engines, not primitives
2. Show primitives as the "advanced/custom" path
3. Add decision trees: "Use DataFlowEngine unless you need X"

---

## Recommendations

### Immediate (Arbor)

1. **Keep current architecture** — Arbor works. The Delegate (L3) is the correct layer. Nexus is used appropriately. DataFlow primitive is fine for the current model count.

2. **Delete specialist agents** — They're dead code from the pre-Delegate era. The Delegate + 208 tools handles everything they did. This removes the `Agent` compatibility shim entirely.

3. **Don't migrate DataFlow to DataFlowEngine** — The engine adds validation/classification which Arbor doesn't use yet. The eager connection issue exists in both. Low ROI.

### Upstream (COC Template)

1. **Update all SKILL.md indexes** to lead with engines
2. **Update quickstart files** to show engine builder patterns
3. **Update framework specialist agents** to recommend engines by default
4. **Add decision tree skill**: "When to use Engine vs Primitive"
5. **Update patterns.md** with engine patterns for all 3 frameworks

### Upstream (SDK)

1. **kailash-py#171** — Lazy connection for DataFlow (blocks test isolation)
2. **Agent unified API** — Add structured output mode (kwargs → dict) so specialists don't need shims
