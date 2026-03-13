# T010 — Kaizen Agent Architecture: Orchestration and Memory

## Status: COMPLETED

## What Was Built

### Orchestration Agents (Tier 1)

| Agent                    | Pattern           | Purpose                                                                               |
| ------------------------ | ----------------- | ------------------------------------------------------------------------------------- |
| QueryAnalyzerAgent       | Chain-of-Thought  | Classifies queries by domain, extracts entities, assigns risk tier, routes            |
| OrchestratorAgent        | Supervisor-Worker | Produces dispatch plans (parallel/sequential/router) for specialists                  |
| ResponseSynthesizerAgent | Synthesis         | Combines specialist outputs into plain-language answer with citations and disclaimers |

### Memory Infrastructure

| Component          | Scope       | Purpose                                                                                     |
| ------------------ | ----------- | ------------------------------------------------------------------------------------------- |
| HRSharedMemoryPool | Per-query   | Tagged specialist output storage (domain, provisions, confidence, risk, cross-domain flags) |
| ShortTermMemory    | Per-session | Conversation context across turns with configurable window                                  |
| LongTermMemory     | Per-company | Topic frequency tracking, company context, advisory history                                 |

### Supporting

- **Signatures** — 3 Kaizen Signature classes with **intent** and **guidelines**
- **Config** — Model/API key resolution from Settings/environment
- **Pipeline factory** — `create_orchestration_pipeline()` wires all agents with shared memory

## Verification

22 passed, 6 skipped (no API key):

- SharedMemoryPool (6), ShortTermMemory (5), LongTermMemory (6)
- Agent instantiation + pipeline wiring (5)
- LLM-dependent tests skip gracefully without OPENAI_API_KEY

## Files

- `src/hr_advisory/agents/orchestration/` — query_analyzer.py, orchestrator.py, response_synthesizer.py
- `src/hr_advisory/agents/memory/` — shared_pool.py, short_term.py, long_term.py
- `src/hr_advisory/agents/signatures.py`, `config.py`, `__init__.py`
- `tests/integration/test_agent_orchestration.py`
