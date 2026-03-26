# Kaizen Autonomous Agent Capabilities: Technical Research for Arbor Delegate Redesign

**Date**: 2026-03-24
**Purpose**: Research findings to support replacing the manual advisory_engine.py with a proper Kaizen autonomous agent.
**Scope**: BaseAgent API, MCP integration, streaming, tool calling, GovernedSupervisor, Pipeline.router()

---

## 1. Current State: advisory_engine.py

The current engine at `src/hr_advisory/agents/advisory_engine.py` is a **manual ReAct loop** using raw OpenAI client calls:

- **885 lines**, hand-rolled for-loop with `MAX_TOOL_ROUNDS = 10`
- **6 hardcoded OpenAI function tool definitions** (search_kb, calculate_cpf, calculate_leave, calculate_salary, calculate_quota_levy, get_company_context)
- **Direct `openai.OpenAI()` client construction** with manual message accumulation
- **No streaming** -- blocks until full response is ready
- **No budget tracking** -- no cost awareness, no token limits
- **No governance** -- no trust tiers, no PACE enforcement
- **Keyword-based KB search fallback** using stopword removal and word overlap scoring
- **Manual confidence/risk extraction** via regex on response tail

### What works well (preserve in redesign)

- The system prompt is excellent: role-specific, confidence-ladder, boundary-aware
- Tool definitions are well-structured with clear descriptions
- KB search with Python content fallback is a solid pattern
- Citation extraction from KB results
- Synthesis steering after 5+ search_kb calls (prevents infinite tool loops)

### What must change

- Raw OpenAI loop must become a Kaizen autonomous agent
- 6 hardcoded tools must become MCP-discovered tools
- No streaming must become SSE token streaming
- No governance must become PACE-level trust enforcement
- No cost tracking must become BudgetTracker integration

---

## 2. Kaizen BaseAgent -- Autonomous Agent API

### Creating an Autonomous Agent

BaseAgent is the foundation. Three components: config dataclass, Signature, and the agent class.

```python
from kaizen.core.base_agent import BaseAgent
from kaizen.signatures import Signature, InputField, OutputField
from dataclasses import dataclass

@dataclass
class AdvisoryConfig:
    llm_provider: str = "openai"
    model: str = "gpt-5-chat-latest"
    temperature: float = 0.7
    max_tokens: int = 4000
    use_async_llm: bool = True  # Required for FastAPI

class AdvisorySignature(Signature):
    # Inputs
    query: str = InputField(description="User's HR/employment law question")
    conversation_history: str = InputField(description="Prior conversation turns as JSON", default="[]")
    company_context: str = InputField(description="Company profile JSON for personalisation", default="{}")
    user_context: str = InputField(description="User role and name for tone adjustment", default="{}")

    # Outputs
    response_text: str = OutputField(description="Comprehensive advisory response in markdown")
    confidence: float = OutputField(description="Confidence score 0.0-1.0")
    risk_tier: str = OutputField(description="Risk level: green, amber, or red")
    citations: str = OutputField(description="JSON array of legal provisions cited")

class AdvisoryAgent(BaseAgent):
    def __init__(self, config: AdvisoryConfig):
        super().__init__(
            config=config,
            signature=AdvisorySignature(),
            tools="all"  # Enable MCP tool discovery
        )

    async def advise(self, query: str, **kwargs) -> dict:
        result = await self.run_async(query=query, **kwargs)
        return result
```

### Key API Surface

| Method                                    | Purpose                      | When to use               |
| ----------------------------------------- | ---------------------------- | ------------------------- |
| `self.run(...)`                           | Sync execution (wraps async) | CLI, scripts, notebooks   |
| `await self.run_async(...)`               | Native async execution       | FastAPI, high-throughput  |
| `await self.execute_tool(name, params)`   | Execute a single tool        | Explicit tool calls       |
| `await self.discover_tools()`             | List available tools         | Tool introspection        |
| `await self.execute_tool_chain([...])`    | Sequential tool execution    | Multi-step data gathering |
| `self.extract_str(result, key, default)`  | Safe result extraction       | Output parsing            |
| `self.extract_list(result, key, default)` | Safe list extraction         | Output parsing            |
| `self.write_to_memory(content, tags)`     | Persist to memory            | Session continuity        |

### Execution Strategies

- **AsyncSingleShotStrategy** (default for interactive agents): Single LLM call, automatic async execution, 2-3x faster than sync.
- **MultiCycleStrategy** (default for autonomous agents): Multiple LLM calls with tool execution between cycles. Used by ReActAgent, CodeGenerationAgent, RAGResearchAgent, SelfReflectionAgent.

The advisory agent needs **MultiCycleStrategy** since it requires multiple tool-calling rounds (search KB, calculate, synthesize).

### Agent Classification

The advisory agent is an **Autonomous Agent** -- it needs multi-cycle execution with tool calling. This puts it in the same category as ReActAgent and RAGResearchAgent. Autonomous agents:

- Use MultiCycleStrategy by default
- Have MCP tool discovery enabled by default (`mcp_enabled=True`)
- Support `tools="all"` for builtin MCP tools plus custom MCP servers
- ALL reasoning happens in the LLM -- tools are dumb data endpoints

### ReActAgent Pattern

Kaizen provides `ReActAgent` which implements the Reason-Act-Observe loop natively:

```python
from kaizen.agents import ReActAgent

agent = ReActAgent(
    config=config,
    tools="all"  # Enable all MCP tools
)

# Agent autonomously:
# 1. Reasons about the task
# 2. Calls appropriate tools
# 3. Observes results
# 4. Iterates until objective is met
result = agent.solve("Calculate CPF for a $5000 salary employee aged 30")
```

This is conceptually what advisory_engine.py does manually. The ReActAgent handles the loop, tool dispatch, and termination detection natively.

### Async Execution in FastAPI

```python
from fastapi import FastAPI
app = FastAPI()

agent = AdvisoryAgent(AdvisoryConfig())

@app.post("/api/advisory/ask")
async def ask(request: AskRequest):
    result = await agent.run_async(
        query=request.message,
        conversation_history=json.dumps(request.history),
        company_context=json.dumps(request.company_context or {}),
        user_context=json.dumps(request.user_context or {}),
    )
    return {"response": result["response_text"]}
```

---

## 3. Kaizen + MCP -- Tool Discovery from 5 MCP Servers

### Architecture

Kaizen agents discover tools through MCP (Model Context Protocol). Instead of hardcoding 6 function definitions, the agent connects to MCP servers and discovers tools at runtime.

### Connecting Multiple MCP Servers

```python
mcp_servers = [
    {
        "name": "arbor-government",
        "command": "python",
        "args": ["-m", "hr_advisory.mcp_servers.government_server"],
        "transport": "stdio"
    },
    {
        "name": "arbor-accounting",
        "command": "python",
        "args": ["-m", "hr_advisory.mcp_servers.accounting_server"],
        "transport": "stdio"
    },
    {
        "name": "arbor-banking",
        "command": "python",
        "args": ["-m", "hr_advisory.mcp_servers.banking_server"],
        "transport": "stdio"
    },
    {
        "name": "arbor-communications",
        "command": "python",
        "args": ["-m", "hr_advisory.mcp_servers.communications_server"],
        "transport": "stdio"
    },
    {
        "name": "arbor-regulatory",
        "command": "python",
        "args": ["-m", "hr_advisory.mcp_servers.regulatory_server"],
        "transport": "stdio"
    },
]

agent = AdvisoryAgent(
    config=config,
    tools="all",
    custom_mcp_servers=mcp_servers  # Discover tools from all 5 servers
)
```

### Tool Discovery at Runtime

```python
# Agent discovers all available tools from connected MCP servers
tools = await agent.discover_tools()
# Returns tool definitions with name, description, parameters, danger_level

# Filter by category
gov_tools = await agent.discover_tools(category="government")
```

### Managing 100+ Tools Without Context Overflow

The Arbor platform has 120+ REST endpoints and 38 MCP connectors. Strategies to prevent context overflow:

1. **CatalogMCPServer for pre-filtering**: Use the Kaizen Catalog Server to register agents and their tool schemas. The catalog provides `catalog_search` to find relevant tools by capability, reducing the set presented to the LLM.

2. **MCP session wiring**: `discover_mcp_resources()`, `read_mcp_resource()`, `discover_mcp_prompts()`, `get_mcp_prompt()` are wired on agent sessions. The agent discovers available tools but the LLM only sees tool descriptions in its context, not full schemas.

3. **Tool categories with danger levels**: Tools are tagged by category (file, http, government, accounting, etc.) and danger level (SAFE, LOW, MEDIUM, HIGH, CRITICAL). The agent can selectively load categories.

4. **Practical approach for advisory**: The advisory agent only needs ~20-30 tools at most (KB search, 7 calculators, company context, a few government lookups). The 5 MCP servers should expose curated tool sets, not all 120 endpoints. The `tool_selector.py` module already handles this curation.

### CatalogMCPServer Pattern

```python
from kaizen.mcp.catalog_server.server import CatalogMCPServer

# Start the catalog server (11 tools for agent discovery/deploy/governance)
server = CatalogMCPServer()

# Register advisory agent with catalog
server.handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "deploy_agent",
        "arguments": {
            "manifest_toml": """
[agent]
manifest_version = "1.0"
name = "arbor-advisory"
module = "hr_advisory.agents.advisory_agent"
class_name = "AdvisoryAgent"
capabilities = ["hr_advisory", "employment_law", "cpf_calculation", "leave_calculation"]

[governance]
risk_level = "medium"
suggested_posture = "supervised"
budget_microdollars = 5000000
"""
        }
    }
})
```

### MCP vs Hardcoded Tools -- Migration Path

| Current (advisory_engine.py)              | Kaizen + MCP                                               |
| ----------------------------------------- | ---------------------------------------------------------- |
| `TOOL_DEFINITIONS` list of 6 dicts        | MCP servers expose tools; agent discovers at runtime       |
| `_execute_tool_call()` with if-elif chain | `agent.execute_tool(name, params)` -- MCP handles dispatch |
| OpenAI function calling format            | MCP tool format (auto-converted by Kaizen)                 |
| 6 tools                                   | 20-30 curated tools from 5 MCP servers                     |
| Manual JSON schema                        | MCP servers declare schemas                                |

---

## 4. Kaizen Streaming

### Current API

Streaming is supported through the strategy layer:

```python
class StreamingAgent(BaseAgent):
    async def stream_response(self, question: str):
        async for token in self.strategy.stream(
            self.signature,
            {"question": question},
            self.config
        ):
            yield token
```

### FastAPI SSE Integration

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.post("/api/advisory/stream")
async def stream_advisory(request: AskRequest):
    agent = get_advisory_agent()  # Singleton

    async def event_stream():
        async for token in agent.strategy.stream(
            agent.signature,
            {
                "query": request.message,
                "conversation_history": json.dumps(request.history),
                "company_context": json.dumps(request.company_context or {}),
            },
            agent.config,
        ):
            # SSE format
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

### Streaming with Control Protocol

For richer bidirectional communication (progress reporting, approval requests):

```python
from kaizen.core.autonomy.control import ControlProtocol
from kaizen.core.autonomy.control.transports import HTTPTransport

# HTTP transport supports SSE natively
transport = HTTPTransport(host="0.0.0.0", port=8000)
await transport.start_server()

protocol = ControlProtocol(transport)
agent = AdvisoryAgent(config, control_protocol=protocol)

# Agent can now:
# - Stream tokens via SSE
# - Report progress: await self.report_progress("Searching KB...", 25.0)
# - Ask clarification: await self.ask_user_question("Which domain?", ["CPF", "Leave", "All"])
```

### Streaming Limitations and Considerations

1. **Strategy.stream()** is the core method. It yields tokens as they arrive from the LLM provider.
2. **Tool-calling rounds** interrupt the stream. When the agent calls a tool mid-response, the stream pauses, the tool executes, and streaming resumes. The client needs to handle this: tokens flow, then a tool_call event, then tool results, then more tokens.
3. **Multi-cycle agents** (ReActAgent, which the advisory agent would be) stream within each cycle but have gaps between cycles for tool execution.
4. **The streaming skill is minimal** (4 lines of actual content). Implementation may require inspecting `kaizen/strategies/` source for the full streaming API, particularly for multi-cycle strategies.

### Practical Pattern for Advisory

The advisory agent's streaming path would be:

```
Client connects SSE
  -> Agent receives query
  -> Agent reasons (stream thought tokens)
  -> Agent decides to call search_kb
  -> SSE sends: {"type": "tool_call", "tool": "search_kb", "status": "executing"}
  -> Tool executes
  -> SSE sends: {"type": "tool_result", "tool": "search_kb", "status": "complete"}
  -> Agent reasons about results (stream more tokens)
  -> Agent decides to call calculate_cpf
  -> SSE sends: {"type": "tool_call", ...}
  -> ...
  -> Agent produces final answer (stream response tokens)
  -> SSE sends: {"type": "done", "confidence": 0.92, "risk": "green"}
```

---

## 5. Kaizen Tool Calling

### How Kaizen Differs from Raw OpenAI Function Calling

| Feature           | Raw OpenAI (current)                    | Kaizen Tool Calling                            |
| ----------------- | --------------------------------------- | ---------------------------------------------- |
| Tool definitions  | Manual JSON schema dicts                | MCP auto-discovery or Tool objects             |
| Tool dispatch     | if-elif chain in `_execute_tool_call()` | `agent.execute_tool()` -- framework dispatches |
| Error handling    | Manual try/except per tool              | Built-in with danger-level awareness           |
| Approval workflow | None                                    | SAFE/LOW/MEDIUM/HIGH/CRITICAL levels           |
| Tool chaining     | Manual message accumulation             | `agent.execute_tool_chain([...])`              |
| Cost tracking     | Manual token counting                   | Automatic `_cost`, `_tokens` in result         |
| Budget limits     | None                                    | BudgetTracker + PostureBudgetIntegration       |
| Tool discovery    | Static list                             | Runtime MCP discovery                          |

### Danger Level Approval Workflow

```
SAFE (read-only)     -> Auto-approved (search_kb, get_company_context)
LOW (minor changes)  -> Auto-approved (calculate_cpf, calculate_leave)
MEDIUM (significant) -> Auto-approved in dev, requires approval in prod
HIGH (risky)         -> Always requires approval
CRITICAL (destructive) -> Manual-only approval
```

For the advisory agent, all tools are SAFE or LOW since they are read-only calculations and lookups.

### Custom Tool Registration

For tools that are not MCP-served (e.g., the KB search with Python content fallback):

```python
from kaizen.tools import Tool, ToolParameter

search_kb_tool = Tool(
    name="search_kb",
    description="Search Singapore employment law knowledge base",
    function=_search_kb_with_fallback,  # The existing function
    parameters=[
        ToolParameter(name="query", type="string", description="Search query", required=True),
        ToolParameter(name="domain", type="string", description="Domain filter", required=False),
    ],
    category="knowledge",
    danger_level="SAFE",
)
```

### Tool Chaining

```python
# Sequential tool execution with result passing
results = await agent.execute_tool_chain([
    {"tool_name": "search_kb", "params": {"query": "CPF rates 2026"}},
    {"tool_name": "calculate_cpf", "params": {"monthly_wage": 5000}},
])
# results[0] = KB search results
# results[1] = CPF calculation results
```

### Automatic Tool Selection

Kaizen's autonomous agents (ReActAgent, RAGResearchAgent) use the LLM to select tools. The LLM sees all available tool descriptions and autonomously decides:

1. Which tool to call
2. What arguments to pass
3. When it has enough information to stop
4. How to synthesize results into a response

This is exactly what advisory_engine.py does manually with the for-loop. Kaizen handles it natively.

---

## 6. GovernedSupervisor -- PACT-Governed Agent Orchestration

### Package: kaizen-agents (v0.1.0)

`GovernedSupervisor` is the PACT-governed orchestration layer built on top of kailash-kaizen SDK. It provides progressive disclosure across 3 layers.

### Layer 1: Simple (Minimal Config)

```python
from kaizen_agents.supervisor import GovernedSupervisor

supervisor = GovernedSupervisor(
    model="gpt-5-chat-latest",
    budget_usd=5.0,  # $5 per session cap
)
result = await supervisor.run("Calculate CPF for an employee earning $5000/month")
```

### Layer 2: Configured (PACE-Level Trust)

```python
supervisor = GovernedSupervisor(
    model="gpt-5-chat-latest",
    budget_usd=5.0,
    tools=["search_kb", "calculate_cpf", "calculate_leave", "calculate_salary",
           "calculate_quota_levy", "get_company_context"],
    data_clearance="restricted",          # PACE trust level mapping
    warning_threshold=0.70,               # Budget warning at 70%
    max_children=10,                       # Max concurrent sub-agents
    max_depth=5,                           # Max delegation depth
    policy_source="arbor-platform",        # D/T/R authority
)
```

### Layer 3: Full Governance (9 Subsystems)

```python
# Read-only governance state queries
trail = supervisor.audit.to_list()                  # EATP hash chain audit trail
snap = supervisor.budget.get_snapshot("root")        # Budget status
chain = supervisor.accountability.trace("agent-1")   # D/T/R chain
events = supervisor.cascade.get_events()             # Envelope tightening events
warnings = supervisor.dereliction.get_stats()        # Insufficient tightening
bypasses = supervisor.bypass_manager.get_active()    # Emergency overrides
orphans = supervisor.vacancy.get_orphans()           # Orphaned agents
classes = supervisor.clearance.get_classifications() # Data classification
classified = supervisor.classifier.classify("data")  # Classification assignment
```

### Mapping PACE Levels to GovernedSupervisor

PACE (the Arbor trust framework) has 4 levels: Proactive, Active, Controlled, Emergency. These map to GovernedSupervisor's clearance and budget configuration:

| PACE Level | Clearance    | Budget Cap   | Tools                | Behavior                           |
| ---------- | ------------ | ------------ | -------------------- | ---------------------------------- |
| Proactive  | PUBLIC       | $0.50/query  | All SAFE tools       | Full autonomy, low stakes          |
| Active     | INTERNAL     | $2.00/query  | All SAFE + LOW tools | Autonomous with monitoring         |
| Controlled | RESTRICTED   | $5.00/query  | Curated tool subset  | Human approval for certain actions |
| Emergency  | CONFIDENTIAL | $10.00/query | Minimal tools        | Human-in-the-loop for everything   |

### Anti-Self-Modification

Agents receive governance through `_ReadOnlyView` proxies. They cannot modify their own envelopes:

```python
# Agent sees read-only views -- mutation raises AttributeError
supervisor.budget.allocate(...)  # AttributeError!
supervisor.cascade.tighten_envelope(...)  # AttributeError!
```

### Budget Tracking Integration

```python
from kailash.trust.constraints.budget_tracker import BudgetTracker, usd_to_microdollars
from kailash.trust.postures import PostureStateMachine, TrustPosture
from kaizen.governance.posture_budget import PostureBudgetIntegration

tracker = BudgetTracker(allocated_microdollars=usd_to_microdollars(5.0))
state_machine = PostureStateMachine()
state_machine.register_agent("advisory-agent", TrustPosture.DELEGATED)

integration = PostureBudgetIntegration(
    budget_tracker=tracker,
    state_machine=state_machine,
    agent_id="advisory-agent",
    thresholds={"warning": 0.70, "downgrade": 0.90, "emergency": 1.0},
)
# At 70% spend: WARNING logged
# At 90% spend: posture -> SUPERVISED (reduced autonomy)
# At 100% spend: posture -> PSEUDO_AGENT (emergency, human required)
```

### Seven Governance Modules

| Module                | Purpose                     | Advisory Use                        |
| --------------------- | --------------------------- | ----------------------------------- |
| AccountabilityTracker | D/T/R addressing            | Map advisory agent in org tree      |
| BudgetTracker         | Cost enforcement            | Per-query and monthly caps          |
| CascadeManager        | Envelope tightening         | Restrict tools when budget low      |
| ClearanceEnforcer     | Data classification (C0-C4) | PII/salary data classification      |
| DerelictionDetector   | Insufficient governance     | Alert on over-permissive delegation |
| BypassManager         | Emergency overrides         | Admin override for urgent queries   |
| VacancyManager        | Orphan detection            | Handle agent failure gracefully     |

---

## 7. Pipeline.router() -- LLM-Based Routing

### Current State

Pipeline.router() uses A2A (Agent-to-Agent) semantic capability matching to route tasks to the most appropriate agent, replacing keyword-based or dispatch-table routing.

```python
from kaizen.orchestration.pipeline import Pipeline

# Create specialized agents
kb_agent = KBSearchAgent(config)
cpf_agent = CPFCalculatorAgent(config)
leave_agent = LeaveCalculatorAgent(config)
salary_agent = SalaryCalculatorAgent(config)
general_agent = GeneralAdvisoryAgent(config)

# LLM-based routing -- no if-else, no keyword matching
router = Pipeline.router(
    agents=[kb_agent, cpf_agent, leave_agent, salary_agent, general_agent],
    routing_strategy="semantic"  # A2A-based routing
)

# The LLM examines A2A capability cards and reasons about best match
result = router.run(query="How much CPF should I pay for a $5000 salary?")
# Routes to cpf_agent automatically
```

### How It Works

1. Each agent has an A2A capability card (auto-generated from its Signature and config via `to_a2a_card()`)
2. The router LLM receives the query and all agent capability cards
3. The LLM reasons about which agent(s) best match the query
4. Selected agent(s) execute the task
5. Results are returned (or synthesized if ensemble mode)

### Applicability to Advisory Redesign

For the advisory use case, Pipeline.router() is **less relevant** than GovernedSupervisor because:

1. The advisory agent is a single autonomous agent that calls tools, not a multi-agent system that routes to specialists
2. The "routing" happens at the tool level (which tool to call), not the agent level
3. The LLM already handles tool selection natively through the ReAct loop

Where Pipeline.router() would be useful:

- If the platform evolves to have separate specialist agents (payroll specialist, leave specialist, recruitment specialist) and needs to route queries to the right one
- If the shadow agent system dispatches tasks across multiple domain agents

### Other Pipeline Patterns

| Pattern           | Use Case                    | Advisory Relevance                     |
| ----------------- | --------------------------- | -------------------------------------- |
| Router            | Route to specialist agents  | Future: multi-agent advisory           |
| Ensemble          | Multi-perspective synthesis | Future: cross-domain queries           |
| Supervisor-Worker | Hierarchical coordination   | Future: complex multi-step advisory    |
| Sequential        | Linear agent chain          | Current: search -> calculate -> advise |
| Parallel          | Concurrent execution        | Current: parallel KB + calculator      |

---

## 8. L3 Autonomy Model

### Five Primitives

| Primitive                         | Module                | Purpose                                                   |
| --------------------------------- | --------------------- | --------------------------------------------------------- |
| EnvelopeTracker/Splitter/Enforcer | `kaizen.l3.envelope`  | Continuous budget tracking, non-bypassable enforcement    |
| ScopedContext                     | `kaizen.l3.context`   | Hierarchical context with projection-based access control |
| MessageRouter/Channel             | `kaizen.l3.messaging` | Typed inter-agent messaging                               |
| AgentFactory/Registry             | `kaizen.l3.factory`   | Runtime agent spawning with lifecycle tracking            |
| PlanValidator/Executor            | `kaizen.l3.plan`      | DAG task graphs with gradient-driven failure handling     |

### Key Design Principle

All L3 primitives are **deterministic** -- no LLM calls. The orchestration layer (kaizen-agents `GovernedSupervisor`) decides WHAT to do; the SDK validates and enforces.

### EnvelopeTracker for Advisory Budget

```python
from kaizen.l3.envelope import EnvelopeTracker, PlanGradient, CostEntry

tracker = EnvelopeTracker(
    envelope={"financial_limit": 5.0, "action_limit": 50},  # $5, 50 tool calls max
    gradient=PlanGradient(
        budget_flag_threshold=0.70,   # Warn at 70%
        budget_hold_threshold=0.95,   # Hold at 95%
    ),
)

# After each LLM call or tool execution
verdict = await tracker.record_consumption(
    CostEntry(action="llm_call", dimension="financial", cost=0.05, agent_instance_id="advisory-1")
)
# verdict.zone: AUTO_APPROVED | FLAGGED | HELD | BLOCKED
```

### Gradient Zones (enforcement levels)

| Zone          | Range          | Advisory Behavior                              |
| ------------- | -------------- | ---------------------------------------------- |
| AUTO_APPROVED | 0-70% budget   | Full autonomy, no restrictions                 |
| FLAGGED       | 70-95% budget  | Continue but log for review, shorter responses |
| HELD          | 95-100% budget | Suspend, require human intervention            |
| BLOCKED       | >100% budget   | Reject all actions                             |

### L3Runtime (Convenience Integration)

```python
from kaizen.l3 import L3Runtime, AgentSpec

runtime = L3Runtime(root_envelope={"financial_limit": 100.0})

# Spawn advisory agent with full integration
spec = AgentSpec(agent_type="advisory", capabilities=["hr_law", "calculation"])
instance = await runtime.spawn_agent(spec, parent_id="root")

# Create plan executor with enforcer integration
executor = runtime.create_plan_executor(node_callback=my_callback)
```

---

## 9. BYOK (Bring Your Own Key) Support

The advisory agent serves multi-tenant users who may bring their own API keys:

```python
from kaizen.core.config import BaseAgentConfig

# Tenant-specific config
config = BaseAgentConfig(
    llm_provider="openai",
    model="gpt-5-chat-latest",
    api_key="sk-tenant-123",        # Per-request override
    base_url="https://proxy.example.com/v1",  # Optional proxy
)

agent = AdvisoryAgent(config=config)
result = await agent.run_async(query="...")
```

Key security features:

- Credentials flow through CredentialStore (never in serializable config)
- BYOKClientCache with SHA-256 hashed keys, TTL 300s, max 128 entries
- Error sanitization strips API key patterns from exceptions
- Empty/whitespace api_key raises ConfigurationError
- base_url validated against SSRF (cloud metadata endpoints blocked)

---

## 10. Implementation Recommendations

### Architecture

```
FastAPI Endpoint (/api/advisory/stream)
  |
  v
AdvisoryAgent (BaseAgent + MultiCycleStrategy)
  |-- MCP: arbor-government (8 tools)
  |-- MCP: arbor-accounting (7 tools)
  |-- MCP: arbor-banking (5 tools)
  |-- MCP: arbor-communications (6 tools)
  |-- MCP: arbor-regulatory (9 tools)
  |-- Custom: search_kb (Python content fallback)
  |-- Custom: get_company_context (DataFlow query)
  |
  v
GovernedSupervisor (Layer 2)
  |-- BudgetTracker ($5/query, $150/month cap)
  |-- ClearanceEnforcer (RESTRICTED for salary/PII data)
  |-- AuditTrail (EATP hash chain)
  |-- PostureBudgetIntegration (PACE level transitions)
  |
  v
SSE Token Stream -> Client
```

### Migration Steps

1. **Create AdvisoryAgent** extending BaseAgent with AdvisorySignature
2. **Convert 6 hardcoded tools** to Tool objects or MCP server tools
3. **Wire MCP servers** via `custom_mcp_servers` parameter
4. **Add streaming** via strategy.stream() and SSE endpoint
5. **Wrap in GovernedSupervisor** (Layer 2) with budget + clearance
6. **Wire PostureBudgetIntegration** for PACE level enforcement
7. **Add BYOK support** via BaseAgentConfig api_key override
8. **Preserve system prompt** (it's good -- just move it to the Signature's prompt template)
9. **Preserve synthesis steering** (5+ search_kb cap) as a tool-level guardrail

### What to Keep from advisory_engine.py

- `_build_system_prompt()` -- move to Signature system prompt
- `_search_kb_with_fallback()` -- register as custom Tool with SAFE danger level
- `_extract_citations()` -- post-processing on result
- `_parse_confidence_and_risk()` -- move to OutputField definitions in Signature
- Anti-amnesia constraints injection -- move to Signature system prompt
- Security footer injection -- move to Signature system prompt

### What to Remove

- `TOOL_DEFINITIONS` list -- replaced by MCP discovery
- `_execute_tool_call()` if-elif chain -- replaced by framework dispatch
- `MAX_TOOL_ROUNDS` for-loop -- replaced by MultiCycleStrategy
- Manual `openai.OpenAI()` client construction -- replaced by Kaizen provider
- Manual token counting -- replaced by built-in `_tokens`, `_cost`
- Manual message accumulation -- replaced by strategy internals

### Open Questions

1. **Streaming + tool calls**: The streaming skill documentation is minimal (4 lines). Need to verify how `strategy.stream()` handles multi-cycle execution with tool calls interleaved. May need to inspect `kaizen/strategies/` source.

2. **MCP server lifecycle**: The 5 arbor MCP servers currently run as in-process modules. With Kaizen MCP integration, they would run as stdio subprocesses. Need to decide: (a) keep them in-process and register as custom Tools, or (b) launch as MCP stdio servers. Option (a) is simpler and avoids subprocess overhead.

3. **GovernedSupervisor availability**: `kaizen-agents` is v0.1.0 and requires `kailash-kaizen>=2.1.0`. Need to verify these versions are available/installable in the Arbor deployment environment.

4. **KB search fallback**: The Python content module fallback (`_search_python_kb`) is important for when DataFlow DB is empty. This needs to be preserved as a custom tool, not an MCP-discovered one, since it's a local function.

5. **Conversation memory**: advisory_engine.py receives `conversation_history` as a parameter. Kaizen provides BufferMemory with `session_id` for automatic memory management. Need to decide whether to use Kaizen's memory system or continue passing history explicitly (explicit is simpler for the API contract).

---

## References

### Skills Read

- `kaizen-baseagent-quick.md` -- BaseAgent API, config, execution
- `kaizen-tool-calling.md` -- Tool registration, MCP integration, danger levels
- `kaizen-streaming.md` -- Strategy.stream() for token streaming
- `kaizen-catalog-server.md` -- CatalogMCPServer with 11 tools
- `kaizen-agents-governance.md` -- GovernedSupervisor, 7 modules
- `kaizen-agents-security.md` -- Anti-self-modification, NaN defense
- `kaizen-control-protocol.md` -- Bidirectional communication, 4 transports
- `kaizen-l3-overview.md` -- L3 primitives, L3Runtime, EATP events
- `kaizen-l3-envelope.md` -- EnvelopeTracker, gradient zones
- `kaizen-react-pattern.md` -- ReAct Reason+Act+Observe
- `kaizen-multi-agent-setup.md` -- SharedMemoryPool coordination
- `kaizen-budget-tracking.md` -- BudgetTracker, PostureBudgetIntegration
- `kaizen-composition.md` -- DAG validation, schema compatibility
- `kaizen-cost-tracking.md` -- Per-invocation cost tracking
- `kaizen-byok-patterns.md` -- Per-request API key overrides
- `kaizen-agent-execution.md` -- run(), run_async(), strategies
- `kaizen-supervisor-worker.md` -- Supervisor-worker pattern
- `SKILL.md` -- Full Kaizen skill index

### Source Files Read

- `src/hr_advisory/agents/advisory_engine.py` -- Current engine (885 lines)
