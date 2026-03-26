# Delegate Agent Redesign — Current State Audit

**Date**: 2026-03-24
**Status**: Analysis Phase

## The Problem

The Arbor delegate agent (formerly "shadow agent") is architecturally broken. It scores **34% on functional testing** and **42% on autonomous capability**. The root causes are structural, not incremental:

1. **6 hardcoded OpenAI function tools** when the platform has **644+ tools** across 5 MCP servers, 31 REST routers, and 170 registry entries
2. **gpt-5-mini** instead of gpt-5-chat-latest — the budget model for the flagship feature
3. **37 agent-reasoning rule violations** — keyword matching, regex classification, if-else dispatch, manual workflow loops
4. **No MCP integration** — Kailash has a full MCP framework, 5 MCP servers are built, but none are wired to the LLM
5. **No streaming** — 30-60s wall of silence before response appears
6. **Manual ReAct loop** — hand-rolled `for round in range(10)` instead of Kaizen autonomous agent patterns

## Capability Surface (644+ tools, 6 exposed)

| Surface                  | Tools    | Exposed to LLM                  | Coverage |
| ------------------------ | -------- | ------------------------------- | -------- |
| MCP Servers (5)          | 97       | 0                               | 0%       |
| REST API (31 routers)    | 377      | 0                               | 0%       |
| Shadow Tool Registry     | 170      | 0 (used for HTTP dispatch only) | 0%       |
| Hardcoded Function Tools | 6        | 6                               | 100%     |
| **Total**                | **644+** | **6**                           | **<1%**  |

The 6 tools: search_kb, calculate_cpf, calculate_leave, calculate_salary, calculate_quota_levy, get_company_context.

Missing: ALL employee CRUD, ALL leave management, ALL payroll operations, ALL attendance, ALL claims, ALL recruitment, ALL documents, ALL government filings, ALL accounting integrations, ALL communication channels.

## Agent-Reasoning Rule Violations (37 total)

| Severity    | Count | Key Offenders                                                                                      |
| ----------- | ----- | -------------------------------------------------------------------------------------------------- |
| CRITICAL    | 3     | `_classify_rule_based()` (158 lines of keyword matching), `_detect_attachment()` (60 lines)        |
| MAJOR       | 4     | Trust-level frozensets, tool dispatch if-elif, workflow composer hardcoded routing, DispatchRouter |
| SIGNIFICANT | 8     | Domain mapping dicts, HTTP method dispatch, page-to-nudge dispatch, observation heuristics         |
| MINOR       | 7     | Output formatters, calculator dispatch (permitted as tool plumbing)                                |
| PERMITTED   | ~38   | Guardrails safety patterns (explicitly allowed)                                                    |

### The Three Worst Offenders

**1. `intent_classifier.py:_classify_rule_based()` (lines 457-615)**
158 lines of `if any(kw in msg_lower for kw in [...])` that activates whenever the LLM returns None. Covers only 8/19 modules. The other 11 modules dump into advisory as a catchall. This is why intent classification fails 43%.

**2. `advisory_engine.py:_execute_tool_call()` (lines 490-569)**
Six-branch if-elif chain dispatching tool calls. Should be a registry. More importantly, should be MCP tool execution, not hardcoded functions.

**3. `advisory_engine.py:run()` (lines 631-788)**
Manual `for round_num in range(MAX_TOOL_ROUNDS)` ReAct loop with hand-rolled message management, steering nudges ("synthesize now" injected at round 5+), and manual token counting. This is what Kaizen BaseAgent does automatically.

## Red Team Findings (Live Production Tests)

### Advisory Engine (20 queries): 3.8/5

**Strengths**: Zero hallucination, correct citations, good Singlish handling, proper guardrail blocking.

**Failures**:

- 33s avg latency, 72s max (gpt-5-mini doing 2-5 tool rounds)
- Calculator tools bypassed (LLM computes inline)
- 30-50% irrelevant citations (keyword search, not semantic)
- Pregnancy termination guardrail legally inaccurate (flat refusal vs nuanced EA s.84(4))
- CPF minimization too helpful (teaches optimization without s.58 fraud warning)
- Confidence always 0.95 (gpt-5-mini doesn't self-calibrate)

### Shadow Agent (24 tests): 24/70 (34%)

**Critical failures**:

- Company association broken (new users locked out)
- Intent classification fails 43% (LLM returns None → keyword fallback covers 8/19 modules)
- Stored XSS in action history
- Entity resolution broken (`{employee_id}` literal in URL)
- Zero context awareness in rule-based fallback
- Trust level system unreachable (intents misclassified)

## What Must Change

The delegate agent needs to be **rebuilt from scratch** using:

1. **Kaizen autonomous agent** (not manual ReAct loop) — BaseAgent with proper tool calling, streaming, budget tracking
2. **MCP tool discovery** — all 644+ tools exposed via MCP, not 6 hardcoded functions
3. **gpt-5-chat-latest** — the capable model, not the budget model
4. **Token streaming** — SSE from first token, not 30-60s silence
5. **Zero keyword/regex/if-else classification** — LLM reasons about everything; tools are dumb data endpoints
6. **PACT governance** — trust levels from the tool registry, not frozenset membership tests
