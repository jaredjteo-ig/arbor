# T065 — Wire Conversation History Through Full Pipeline

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T063, T064

## What to build

`QueryAnalyzerAgent` accepts `conversation_history` but specialists and `ResponseSynthesizerAgent` do not. Add `conversation_history` to all specialist and synthesizer signatures, and pass formatted history from `ShortTermMemory` through every pipeline stage. This enables multi-turn coherence: pronoun resolution ("what about him?"), follow-up elaboration ("tell me more about the notice period"), and continuity across a session.

## Acceptance Criteria

- [ ] `ShortTermMemory.get_formatted_history()` called at the start of each pipeline execution
- [ ] Formatted history passed to `QueryAnalyzerAgent` (already done — verify)
- [ ] Formatted history passed to each specialist via `advise()` signature
- [ ] Formatted history passed to `ResponseSynthesizerAgent`
- [ ] Each specialist uses history in prompt to resolve references (e.g., "this employee" refers to entity mentioned 2 turns ago)
- [ ] Synthesizer uses history to avoid repeating information already given
- [ ] Integration test: two-turn conversation where second query uses pronoun referencing first query entity — correct resolution

## Files

- `src/hr_advisory/agents/specialists/_base.py` — add `conversation_history` to `advise()`
- `src/hr_advisory/agents/specialists/signatures.py` — update Kaizen signatures
- `src/hr_advisory/agents/response_synthesizer.py` — add `conversation_history` parameter
- `src/hr_advisory/api/routers/advisory.py` — pass history from ShortTermMemory through pipeline

## Definition of Done

- [ ] All pipeline stages receive conversation history
- [ ] Pronoun resolution test passes (second turn references first turn entity correctly)
- [ ] "Tell me more" follow-up test passes (no repetition, elaborates from previous point)
