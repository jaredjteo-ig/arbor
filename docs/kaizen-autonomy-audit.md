# Kaizen Autonomy Audit: Findings from Arbor Advisory Engine

**Date**: 2026-03-21
**Context**: Arbor's HR advisory pipeline was rebuilt from a rigid 13-step Kaizen agent pipeline to an autonomous LLM function-calling engine. This document captures the architectural lessons and capability gaps discovered in Kaizen during the process.

## Background

Arbor's advisory system originally used the Kaizen agent framework:

- `QueryAnalyzerAgent` (Chain-of-Thought classification)
- `DispatchRouter` (deterministic domain routing)
- 8 specialist agents (EmploymentActAgent, CPFAgent, etc.)
- `ComplianceGate` (cross-specialist validation)
- `ResponseSynthesizer` (merges specialist outputs)

This pipeline had a **60-70% degradation rate** — most queries fell through to hardcoded template responses. The keyword-based routing was brittle, calculators returned stubs, and multi-turn context was lost.

The replacement: a single `AdvisoryEngine` class (~660 lines) using OpenAI's native function calling with 6 tools. Result: **0% degradation, 100% of queries get real answers.**

## The Autonomy Question

During the rebuild, we audited Kaizen's capabilities against a clear autonomy taxonomy:

| Level | Name          | Description                                                                | Kaizen Support              |
| ----- | ------------- | -------------------------------------------------------------------------- | --------------------------- |
| 0     | Reactive      | Single-shot response                                                       | Yes (SimpleQA, CoT)         |
| 1     | Tool-Using    | Loop with tool calling                                                     | Yes (ReAct, RAGResearch)    |
| 2     | Coordinated   | Multiple agents in fixed topology                                          | Partial (Supervisor-Worker) |
| 3     | Self-Directed | Agent decides its own strategy, spawns sub-agents, restructures mid-flight | **Not implemented**         |

**Arbor needed Level 3. Kaizen provides Level 1-2.**

## Capability Gap Analysis

### 1. Supervisor-Worker: Static, Not Dynamic

**What exists**: `SupervisorWorkerPattern` accepts a pre-defined list of workers at construction. A2A semantic matching selects the best worker for a task.

**What's missing**: The worker list is fixed at init. The supervisor cannot:

- Instantiate a new worker type it has never seen
- Modify the worker list during execution
- Split a task into sub-tasks and assign each to different workers concurrently

**What's needed**: An `AgentFactory` pattern — the supervisor receives a factory/registry rather than a list, and can request agents by capability description.

### 2. AgentRegistry: Discovery Without Spawning

**What exists**: `AgentRegistry` provides O(1) capability-based discovery and health monitoring. `OrchestrationRuntime` provides semantic routing for 10-100 agents.

**What's missing**: Discovery exists, but spawning does not. `find_agents_by_capability()` returns already-registered agents. There is no mechanism for an agent to say "I need a capability that nobody currently provides — please create one."

**What's needed**: An `AgentFactory` that can create agents from capability descriptions or signature templates at runtime.

### 3. SharedMemoryPool: Flat, Not Hierarchical

**What exists**: Tag-based writes with importance scoring. Agent-filtered reads with `exclude_own=True`.

**What's missing**: No structured communication channels, no scoped contexts. An agent writes "insights" and another reads them by tag. This is insufficient for:

- Structured delegation (agent A assigns a task to agent B and waits for the result)
- Hierarchical context (parent context scoped and inherited by children)
- Conversation threading (concurrent sub-tasks needing isolated contexts)

**What's needed**: A `ScopedContext` system — parent agents create scoped contexts that inherit relevant parent context but isolate the sub-task's working memory.

### 4. A2A Protocol: Selection, Not Communication

**What exists**: Capability cards with semantic matching (0.0-1.0 scores). Integrated with Router, Supervisor-Worker, Ensemble patterns.

**What's missing**: A2A is used for **selection**, not **communication**. There is no mechanism for agents to send messages to each other, negotiate, or coordinate mid-flight. Delegation is done by the pattern (`supervisor.run(worker)`), not by the agents themselves.

**What's needed**: An inter-agent message passing layer. Agents should be able to `delegate_to(agent_id, task, context)` and receive results asynchronously.

### 5. Planning Agents: Single-Agent, Not Compositional

**What exists**: `PlanningAgent` (plan-then-execute), `PEVAgent` (plan-execute-verify with refinement), `Tree-of-Thoughts` (N-path exploration).

**What's missing**: These are **single-agent reasoning patterns**, not multi-agent coordination. The PlanningAgent plans for itself — it does not plan which agents to use, how to decompose work across agents, or when to restructure.

**What's needed**: An `AgentPlanner` that operates at the composition level — given a task, produces a plan of which agents to invoke, in what order, with what inputs. Can dynamically adjust when sub-tasks fail.

### 6. Budget Controls: Well-Suited (Minor Gap)

**What exists**: `BudgetTracker` with two-phase reserve/record in integer microdollars. `PostureBudgetIntegration` linking budget thresholds to EATP posture transitions. `BudgetInterruptHandler` for automatic shutdown.

**What's missing**: No built-in mechanism for parent agents to allocate sub-budgets to children.

**What's needed**: A `BudgetAllocation` pattern — small wrapper, not a fundamental gap.

## Documentation Issues

### Conflation of "Autonomous" with "Loop-Based"

The Kaizen documentation uses "autonomous" to mean three different things:

1. **Tool autonomy**: "Can call tools without per-call human approval" (`kaizen-tool-calling.md`)
2. **Execution autonomy**: "Runs in a loop until done" (`kaizen-specialist.md` line 183: "Autonomous Agents (3): ReActAgent...")
3. **Strategic autonomy**: "Decides its own approach to solving a problem" (NOT IMPLEMENTED)

Only definition 3 is what most people mean by "autonomous agent." The documentation does not distinguish these.

**Recommendation**: Add a clear autonomy taxonomy (Levels 0-3 above) to the documentation.

### Pipelines Described as "Multi-Agent Coordination"

`kaizen-orchestration.md` line 1: "Multi-Agent Coordination" — but the patterns shown are fixed-topology execution graphs. Sequential, Parallel, and Router pipelines are not coordination — agents don't negotiate or adjust behavior. Replace with "Multi-Agent Composition."

### "Autonomy Infrastructure" is Execution Infrastructure

`SKILL.md` lines 272-313 lists 6 subsystems (Hooks, Checkpoints, Interrupts, Memory, Planning, Meta-Controller) as "Autonomy Infrastructure." These are excellent execution infrastructure but do not provide autonomy. They provide the plumbing that an autonomous agent would use.

**Recommendation**: Rename to "Execution Infrastructure" and add a note that Level 3 autonomy requires additional composition capabilities built on top.

## Arbor's Solution: What We Built Instead

Since Kaizen lacked Level 3 autonomy, we bypassed the agent framework entirely and used OpenAI's native function calling:

```python
class AdvisoryEngine:
    """Single LLM with 6 tools. The LLM decides what to call."""

    def run(self, query, conversation_history, company_context):
        messages = [system_prompt] + history + [user_query]

        for round in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=model, messages=messages, tools=TOOL_DEFINITIONS
            )
            if response.has_tool_calls:
                # Execute tools, append results, continue
                for tool_call in response.tool_calls:
                    result = execute_tool(tool_call)
                    messages.append(tool_result)
            else:
                return response.content  # Done
```

### Tools Defined

1. `search_kb(query, domain?)` — Search legal provisions
2. `calculate_cpf(wage, age_band, bonus?)` — CPF contributions
3. `calculate_leave(years_of_service, leave_type)` — Leave entitlements
4. `calculate_salary(salary, calculation_type, ...)` — Salary proration/OT
5. `calculate_quota_levy(sector, headcount_local, ...)` — Foreign worker quotas
6. `get_company_context(company_id)` — Company profile

### Performance Comparison

| Metric               | Old (Kaizen Pipeline)       | New (Autonomous Engine)                 |
| -------------------- | --------------------------- | --------------------------------------- |
| Degradation rate     | 60-70%                      | 0%                                      |
| CPF calculation      | Stub message                | Exact: $1,275 + $1,500 = $2,775         |
| Maternity leave      | Annual leave template       | Cites Part IX EA + CDCSA, 8 vs 16 weeks |
| Multi-domain queries | Misrouted to single domain  | Covers both EA + EFMA naturally         |
| Multi-turn context   | Lost on degradation         | Native message array — always retained  |
| Token tracking       | Estimation heuristic        | Real counts from API                    |
| Code size            | ~1200 lines + 5 agent files | ~660 lines, 1 file                      |
| Avg response time    | 3-14s (when not degraded)   | 4-17s (always answers)                  |

## Recommendations for Kaizen

### Short-Term (v1.x)

1. **Define the autonomy taxonomy** in documentation — stop calling ReAct "autonomous"
2. **Add `AgentFactory`** — create agents from capability descriptions at runtime
3. **Add `ScopedContext`** — hierarchical context for parent-child agent delegation
4. **Add sub-budget allocation** to `BudgetTracker`

### Medium-Term (v2.x)

5. **Add inter-agent message passing** — structured delegation beyond A2A selection
6. **Add `AgentPlanner`** — meta-planning over agent composition
7. **Make Supervisor-Worker dynamic** — mutable worker list, runtime spawning

### Long-Term

8. **Native function-calling integration** — let Kaizen agents use the LLM's built-in tool calling instead of the custom ReAct loop, which is slower and less reliable
9. **Provider-agnostic tool calling** — abstract over OpenAI/Anthropic/Gemini function calling APIs

## Files

| File                                          | Purpose                                |
| --------------------------------------------- | -------------------------------------- |
| `src/hr_advisory/agents/advisory_engine.py`   | The autonomous engine implementation   |
| `src/hr_advisory/api/routers/advisory.py`     | Integration into safety chain          |
| `src/hr_advisory/agents/memory/short_term.py` | `load_as_messages()` for native format |
| This document                                 | Audit findings and recommendations     |
