# T010B — Kaizen Agent Architecture: Action Agents

## Status: COMPLETED

## What Was Built

2 action agents (Tier 3):

| Agent                   | Purpose                                                   |
| ----------------------- | --------------------------------------------------------- |
| DocumentGenerationAgent | Templates, contracts, policies via Core SDK workflows     |
| CalculatorAgent         | Deterministic dispatcher to Core SDK calculator workflows |

## Verification

Covered by test_specialist_agents.py (61 passed, 3 skipped)

## Files

- `src/hr_advisory/agents/actions/document_gen.py`
- `src/hr_advisory/agents/actions/calculator.py`
- `src/hr_advisory/agents/actions/__init__.py`
