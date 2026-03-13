# T077 — Add QueryClarifier Pre-Classification Stage

**Status**: ACTIVE
**Milestone**: 7 — Specialist Prompt Optimization
**Priority**: MEDIUM
**Estimated Effort**: 3h
**Dependencies**: T071

## What to build

Some queries are genuinely ambiguous and cannot be correctly classified without more information. Add a lightweight `QueryClarifier` agent that runs before `QueryAnalyzerAgent` when the query is ambiguous. It asks a single targeted clarifying question and waits for the user's response before classification proceeds. Key examples: "my staff wants to leave" (resign? take leave?), "can I deduct this from their pay?" (which deduction type?), "what are the rules for part-timers?" (which obligation — CPF, EA, leave?). The clarifier must only fire when genuinely ambiguous — not on every query.

## Acceptance Criteria

- [ ] `QueryClarifier` class created with `needs_clarification()` and `generate_question()` methods
- [ ] `needs_clarification()` returns `True` only for ambiguous queries — uses lightweight LLM call (max_tokens=256, temperature=0.0)
- [ ] When clarification needed: advisory pipeline returns a `type="clarification_needed"` response containing only the clarifying question — no specialist advice
- [ ] Frontend handles `type="clarification_needed"` response: displays question, captures user answer, resubmits as follow-up with original query context
- [ ] When clarification received (follow-up turn with original + answer): `QueryClarifier` bypassed, `QueryAnalyzer` proceeds with enriched context
- [ ] Ambiguity heuristics: queries under 8 words with no domain keyword, queries using pronouns without antecedents, queries with multiple possible intents at equal probability
- [ ] `needs_clarification()` must NOT fire on: clear domain queries, questions with salary/leave amounts, company-specific questions
- [ ] Integration test: "my staff wants to leave" triggers clarification question about resignation vs leave
- [ ] Integration test: "can I dismiss someone for misconduct?" does NOT trigger clarification (clear intent)

## Files

- `src/hr_advisory/agents/query_clarifier.py` — new file
- `src/hr_advisory/api/routers/advisory.py` — add clarifier as first pipeline stage
- `apps/web/src/` — handle `clarification_needed` response type in chat interface

## Reference

11-agent-architecture-analysis.md Section 2.1 Change 3

## Definition of Done

- [ ] Clarifier precision > 95% (does not ask unnecessary questions)
- [ ] Clarifier recall > 90% (catches genuinely ambiguous queries)
- [ ] Round-trip works: question → user answers → correct routing
- [ ] No added latency on clear queries (clarifier adds < 500ms only when ambiguous)
