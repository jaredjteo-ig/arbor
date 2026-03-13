# T064 — Wire KB Retrieval into Specialist Dispatch Path

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: CRITICAL (highest priority change in entire codebase)
**Estimated Effort**: 4h
**Dependencies**: T063

## What to build

Specialists currently advise from LLM training data because `search_provisions()` is never called before dispatching them. Before calling each specialist, query the KB for relevant provisions in that specialist's domain and pass them as `relevant_provisions` to `specialist.advise()`. Without this change, the knowledge base serves no purpose in live queries.

## Acceptance Criteria

- [ ] `search_provisions(query, domain)` called for each specialist domain before dispatch
- [ ] Results passed as `relevant_provisions: list[Provision]` in the specialist `advise()` call
- [ ] `BaseDomainSpecialist.advise()` signature updated to accept `relevant_provisions`
- [ ] Each specialist's system prompt includes retrieved provision text in a `## Relevant Provisions` section
- [ ] If `search_provisions()` returns empty, specialist logs a warning and continues (does not error)
- [ ] Integration test: query about notice periods retrieves EA provisions and they appear in specialist context
- [ ] Integration test: response cites a provision that was in the retrieved set (not hallucinated)

## Files

- `src/hr_advisory/api/routers/advisory.py` — add `search_provisions()` call before each specialist dispatch
- `src/hr_advisory/agents/specialists/_base.py` — add `relevant_provisions` parameter to `advise()`
- All specialist files — update `advise()` to inject provisions into system prompt

## Reference

11-agent-architecture-analysis.md Section 2.1 Change 2

## Definition of Done

- [ ] KB provisions appear in specialist context for every domain query
- [ ] No specialist response that cites a provision not in the KB or retrieved set
- [ ] Fallback handling tested (empty KB results, KB unavailable)
