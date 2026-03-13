# T043 — Singlish and Natural Language Robustness

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Singlish HR Phrase Mappings**:

- 16 common Singlish phrases with standard English meanings and example contexts
- Covers: "resign already", "need pay or not", "can forfeit", "never take", "how to calculate", "got include", "confirm plus chop", "kena", "cannot anyhow", "last time", "still can", "bo bian", "abit sian", "paiseh", "jialat", "buay tahan"

**Suggested Questions in Singlish**:

- 10 natural Singapore English example queries for display in the advisory chat
- e.g. "My staff resign already, need pay notice period or not?"

**LLM System Prompt Addition**:

- `SINGLISH_SYSTEM_PROMPT` providing detailed guidance for LLMs on:
  - Understanding Singlish naturally without asking users to rephrase
  - Common Singlish grammar patterns in HR contexts
  - Code-switching between English and Chinese/Malay terms
  - Instructions to respond in clear standard English while being warm
  - Explicit "do NOT" rules: don't correct Singlish, don't ask for rephrasing

**Helper Functions**:

- `get_singlish_context()` — returns the system prompt addition
- `get_suggested_questions()` — returns suggested Singlish queries

## Files

- `src/hr_advisory/workflows/singlish.py` — Singlish handling module
