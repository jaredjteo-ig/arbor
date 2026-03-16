# T096 — Fix Authority Level Mapping

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T045, T064, T081

## What to build

The current `mapAuthority` function in SystemMessage derives the authority level from the relevance score (e.g., score >= 0.8 maps to "statutory"). This is factually incorrect: relevance is a retrieval metric measuring how well a provision matches the query, not an inherent property of the provision's legal standing. Authority (statutory, regulatory, advisory) is a fixed attribute of each source. Fix the mapping to use the actual `provision_type` field from the KB response. If the backend does not currently include `provision_type` in the advisory API response, add it.

## Acceptance Criteria

### Frontend Fix

- [ ] `mapAuthority` function removed or replaced — no authority mapping based on relevance score
- [ ] Authority level is read directly from the `provision_type` (or equivalent) field on the citation object
- [ ] Authority levels correctly displayed: statutory, regulatory, advisory — matching the actual source type in the KB
- [ ] No regression in the visual display of authority badges

### Backend Fix (if needed)

- [ ] Advisory API response includes `provision_type` on each citation returned
- [ ] `provision_type` is populated from the KB record, not inferred from any score
- [ ] If the field name differs in the DB model, normalise it to `provision_type` in the API response schema

### Validation

- [ ] Employment Act provisions display "Statutory" authority
- [ ] MOM administrative circulars display "Regulatory" or "Administrative" authority
- [ ] TAFEP guidelines display "Advisory" authority
- [ ] CPF Board regulations display the correct authority level per provision type

## Files

- `apps/web/src/components/advisory/SystemMessage.tsx` — remove score-based mapAuthority, read provision_type from citation
- `src/hr_advisory/api/routers/advisory.py` — include provision_type in citation response objects
- `src/hr_advisory/models/knowledge_base.py` — confirm provision_type field exists with correct values

## Definition of Done

- [ ] No relevance score used for authority level determination anywhere in the codebase
- [ ] Authority level displayed correctly for all four major source types (Employment Act, CPF, MOM circular, TAFEP)
- [ ] Backend API includes provision_type in citation objects
- [ ] Integration test confirms authority level in response matches KB record provision_type
