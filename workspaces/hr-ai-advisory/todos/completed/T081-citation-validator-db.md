# T081 — Wire Citation Validator to DB-Backed Provision Registry

**Status**: ACTIVE
**Milestone**: 8 — Quality Rubric and Adversarial Testing
**Priority**: MEDIUM
**Estimated Effort**: 3h
**Dependencies**: T064

## What to build

`citation_validator.py` currently validates citations against a hardcoded `_KB_PROVISIONS` dict of approximately 25 entries. This means any provision added through the KB pipeline (T014) is not available to the citation validator. Replace the hardcoded dict with a DataFlow query to the `Provision` model at validation time, so the valid provision set grows automatically as the KB grows.

## Acceptance Criteria

- [ ] `_KB_PROVISIONS` dict replaced with `get_valid_provisions()` function that queries DataFlow
- [ ] `get_valid_provisions()` returns a set of valid provision identifiers from the `Provision` table
- [ ] Caching: results cached for 60 seconds to avoid a DB query on every citation check
- [ ] `validate_citation(citation_text)` uses the live provision set
- [ ] Cache invalidated when KB pipeline adds a new provision (event or short TTL is sufficient)
- [ ] If DB unavailable, falls back to a minimal hardcoded set of core provisions (EA, CPF Act, EFMA, WFA) and logs a warning
- [ ] Integration test: add a new provision to DB, then validate a citation referencing it — returns valid
- [ ] Integration test: DB unavailable — validator falls back gracefully without crashing

## Files

- `src/hr_advisory/trust/citation_validator.py` — replace `_KB_PROVISIONS` with DataFlow query

## Reference

T045 (citation validator implementation), T014 (KB pipeline)

## Definition of Done

- [ ] No hardcoded provision list in citation_validator.py (except fallback set)
- [ ] Cache hit rate > 99% in normal operation
- [ ] New KB provisions available for citation validation within 60 seconds of being added
