# T066 — Wire Company Context Enrichment Through Full Pipeline

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: HIGH
**Estimated Effort**: 2h
**Dependencies**: T063, T064

## What to build

Company profile data (sector, headcount, foreign worker count, incorporation date) is available but not consistently passed through the pipeline. Fetch company profile once at query start and pass as `company_context` to all specialists and the synthesizer. Specialists use it to tailor advice: sector-specific rules (construction vs. retail), threshold-based guidance (whether WIS applies, whether DRC levy rates apply), headcount-based obligations (is a DPO required for PDPA?).

## Acceptance Criteria

- [ ] Company profile fetched once at pipeline start (not per-agent)
- [ ] `company_context` dict passed to all specialist `advise()` calls
- [ ] `company_context` passed to `ResponseSynthesizerAgent`
- [ ] `BaseDomainSpecialist` system prompt includes company context section when provided
- [ ] Synthesizer uses sector info to filter out inapplicable advice
- [ ] Integration test: query from a construction company receives sector-specific foreign manpower advice (DRC rates, not retail rates)
- [ ] Integration test: query from a 3-person company receives appropriate small-employer advice

## Files

- `src/hr_advisory/api/routers/advisory.py` — fetch company profile once, pass as `company_context`
- `src/hr_advisory/agents/specialists/_base.py` — add `company_context` parameter and prompt injection
- `src/hr_advisory/agents/response_synthesizer.py` — add `company_context` parameter

## Definition of Done

- [ ] Sector-specific advice test passes (construction vs. services)
- [ ] No company context fetched more than once per query
- [ ] Default context (unknown company) handled gracefully
