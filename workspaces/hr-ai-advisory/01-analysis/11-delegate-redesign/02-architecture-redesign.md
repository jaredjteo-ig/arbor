# Delegate Agent Redesign — Architecture

**Date**: 2026-03-24
**Status**: Analysis Phase — For Review

## Design Principles

1. **The LLM reasons. Tools fetch.** Zero keyword matching, regex, if-else dispatch, or step-by-step activation in agent decision paths.
2. **MCP is the tool surface.** Every platform capability is exposed as an MCP tool. The LLM discovers tools, not a hardcoded list.
3. **Stream everything.** First token appears in <2s. No 30-60s silence.
4. **gpt-5-chat-latest.** The flagship feature uses the flagship model.
5. **PACT governs.** Trust levels come from the governance framework, not frozensets.

## Architecture

```
User Message
    |
    v
+------------------------------------------------------------------+
|  FastAPI SSE Endpoint (/api/delegate/stream)                      |
|                                                                    |
|  1. Auth + tenant isolation (JWT)                                  |
|  2. Input sanitisation + length check                              |
|  3. Safety guardrails (injection/scope — permitted regex)          |
|  4. Budget check                                                   |
|                                                                    |
|  5. Resolve PACT GovernanceContext for this user                   |
|     - Role -> operating envelope (what tools are accessible)       |
|     - Trust tier derived from tool registry, not frozensets         |
|                                                                    |
|  6. Build ArborDelegate (Kaizen BaseAgent)                         |
|     - Model: gpt-5-chat-latest                                     |
|     - MCP servers: 5 Arbor servers (in-process)                    |
|     - REST tools: auto-generated from router registry              |
|     - KB tools: pgvector semantic search                           |
|     - Calculators: deterministic (CPF, leave, salary, quota)       |
|     - Conversation memory: Kaizen BufferMemory                     |
|     - Governance: PACT GovernanceContext (frozen, read-only)        |
|                                                                    |
|  7. agent.stream(message, context) -> SSE token stream             |
|     - Tokens stream to client as they're generated                 |
|     - Tool calls execute between token bursts (invisible to user)  |
|     - PACE confirmation interrupts stream if write detected        |
|                                                                    |
|  8. Post-response: trust chain recording, usage tracking           |
+------------------------------------------------------------------+
```

## The Agent

```python
class ArborDelegate(BaseAgent):
    """Autonomous HR delegate agent.

    The LLM decides what tools to call, in what order, and when it has
    enough information to respond. No keyword routing. No fallback
    templates. No manual ReAct loop.

    Tools are discovered via MCP — the agent sees the FULL platform
    capability surface (644+ tools), not a hardcoded subset.
    """

    class Sig(Signature):
        message: str = InputField(description="User's message")
        page_context: str = InputField(description="Current frontend page")
        company_context: dict = InputField(description="Company profile")
        user_context: dict = InputField(description="User role and name")
        conversation_history: list = InputField(description="Prior turns")

        response: str = OutputField(description="Advisory response or action result")
        actions_taken: list = OutputField(description="Tools called and results")
        risk_tier: str = OutputField(description="green/amber/red")
        confidence: float = OutputField(description="0.0-1.0")
        requires_confirmation: bool = OutputField(description="Whether PACE preview needed")
        confirmation_details: dict = OutputField(description="PACE session if confirmation needed")
```

## MCP Tool Surface

Replace the 6 hardcoded functions with **MCP tool discovery**:

### Option A: In-Process MCP (Recommended)

Register the existing 5 MCP servers + REST endpoints as Kaizen tool objects directly. No subprocess overhead. The tools are already Python functions — wrap them as MCP-compatible tool definitions.

```python
# Instead of:
TOOL_DEFINITIONS = [{"type": "function", "function": {"name": "search_kb", ...}}]

# Do:
delegate = ArborDelegate(
    config=config,
    custom_mcp_servers=[
        {"name": "arbor-hris", "tools": hris_tool_registry},      # 377 REST endpoints
        {"name": "arbor-government", "tools": gov_tools},          # 33 MCP tools
        {"name": "arbor-accounting", "tools": acct_tools},         # 22 MCP tools
        {"name": "arbor-banking", "tools": bank_tools},            # 12 MCP tools
        {"name": "arbor-communications", "tools": comms_tools},    # 22 MCP tools
        {"name": "arbor-regulatory", "tools": reg_tools},          # 8 MCP tools
        {"name": "arbor-kb", "tools": kb_tools},                   # KB search + calculators
    ],
)
```

### Tool Count Management

644+ tools would overwhelm the LLM context. Solution: **progressive tool disclosure**.

1. **Always available** (~20 tools): KB search, calculators, navigation, company context, user context
2. **Page-contextual** (~30-50 tools): Tools relevant to current page (e.g., on /employees page, show employee CRUD tools)
3. **On-demand discovery** (remaining): Agent can call a `discover_tools` meta-tool to search for capabilities by description

This is NOT intent classification — the LLM decides which tools to use. We just manage context window by scoping what's visible.

## KB Search — pgvector Semantic Search

Replace keyword overlap with vector similarity:

```python
# Instead of:
score = sum(1 for w in query_words if w in searchable)  # keyword overlap

# Do:
results = await db.execute(
    "SELECT *, embedding <=> $1 AS distance FROM provisions "
    "WHERE is_active = true ORDER BY distance LIMIT $2",
    [query_embedding, limit]
)
```

pgvector is already installed. Embeddings need to be generated once for all provisions (one-time migration).

## Streaming

```python
@router.post("/stream")
async def delegate_stream(request: Request, ...):
    agent = ArborDelegate(...)

    async def event_generator():
        async for chunk in agent.stream(message=query, ...):
            if chunk.type == "token":
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
            elif chunk.type == "tool_call":
                yield f"data: {json.dumps({'type': 'tool_start', 'name': chunk.tool_name})}\n\n"
            elif chunk.type == "tool_result":
                yield f"data: {json.dumps({'type': 'tool_done', 'name': chunk.tool_name})}\n\n"
            elif chunk.type == "confirmation_required":
                yield f"data: {json.dumps({'type': 'pace', 'session': chunk.session})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## PACE Integration

PACE confirmation is triggered by the **governance layer**, not by if-else checks:

1. Agent decides to call a write tool (e.g., `employees.create`)
2. GovernanceContext checks the tool's trust level from the registry
3. If trust level requires confirmation, the tool call is **intercepted**
4. A PACE session is created and streamed to the client as a `confirmation_required` event
5. Client shows PaceCard — user confirms or cancels
6. On confirmation, the tool executes and results stream back

The agent never sees the PACE logic. It just calls tools. Governance intercepts dangerous ones.

## What Gets Deleted

| File                               | Lines      | Reason                                                                   |
| ---------------------------------- | ---------- | ------------------------------------------------------------------------ |
| `shadow/intent_classifier.py`      | 615        | Replaced by LLM tool selection (the agent IS the classifier)             |
| `shadow/workflow_composer.py`      | 200        | Replaced by LLM multi-step planning                                      |
| `shadow/entity_resolver.py`        | 190        | Replaced by LLM parameter extraction (tool schemas are self-documenting) |
| `shadow/executor.py`               | 563        | Replaced by MCP tool execution                                           |
| `shadow/tool_registry.py`          | 600        | Replaced by MCP server registry                                          |
| `shadow/formatter.py`              | 400        | Replaced by LLM response formatting (streaming renders directly)         |
| `agents/advisory_engine.py`        | 885        | Replaced by ArborDelegate BaseAgent                                      |
| `orchestration/dispatch_router.py` | 120        | Replaced by LLM tool selection                                           |
| **Total removed**                  | **~3,573** |                                                                          |

What stays:

- `shadow/pace.py` — PACE session management (but triggered by governance, not if-else)
- `shadow/observation.py` — behavioral tracking (data pipeline, not agent logic)
- `shadow/memory.py` — preference distillation (data pipeline)
- `shadow/briefing.py` — deterministic dashboard briefing (no LLM, pure DataFlow)
- `shadow/nudges.py` — deterministic nudges (no LLM, pure DataFlow)
- `workflows/guardrails.py` — safety guards (permitted exception to agent-reasoning rule)

## Model Configuration

```env
# .env
OPENAI_PROD_MODEL=gpt-5-chat-latest      # Advisory + delegate (quality)
OPENAI_DEV_MODEL=gpt-5-chat-latest        # Same in dev
# gpt-5-mini reserved for: scope guard, injection detection (speed-critical safety checks)
OPENAI_GUARD_MODEL=gpt-5-mini-2025-08-07
```

## Migration Path

This is not an incremental refactor. It's a replacement:

1. Build `ArborDelegate` as a new module (`src/hr_advisory/delegate/`)
2. Wire MCP tool registry from existing servers + REST endpoints
3. Add pgvector embeddings to KB provisions
4. Add SSE streaming endpoint
5. Update frontend to consume SSE stream
6. Run red team against new implementation
7. When red team passes, delete old shadow/ module

## Success Criteria (from Brief 04)

1. "What notice period must I give?" from any page → cited answer in **<3 seconds** (first token)
2. "Onboard a new employee" → multi-step workflow via PACE (agent plans autonomously)
3. "How many leave days do I have left?" → exact balance (agent calls leave.balance tool)
4. Proactive surfacing of compliance gaps (observation pipeline, not agent logic)
5. Enterprise buyer sees a fundamentally different product

## Open Questions

1. **Kaizen streaming during tool calls** — does `strategy.stream()` resume after tool execution? Need source-level verification.
2. **MCP server lifecycle** — in-process registration vs stdio subprocess. In-process is simpler but ties server lifecycle to the FastAPI process.
3. **Context window management** — 644+ tools at ~100 tokens each = 64K tokens just for tool definitions. Progressive disclosure is required, but how exactly?
4. **Conversation persistence** — Kaizen BufferMemory vs explicit DB-backed history. Current advisory uses in-memory OrderedDict with LRU.
5. **PACT integration maturity** — kailash-pact is at v0.4.0. Is GovernedSupervisor stable enough for production?
