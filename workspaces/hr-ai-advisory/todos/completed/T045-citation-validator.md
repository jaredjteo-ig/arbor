# T045 — Citation Validator

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Authority Level and Citation Status Enums**:

- `AuthorityLevel` enum (STATUTORY, TRIPARTITE_GUIDELINE, BEST_PRACTICE) for source weighting
- `CitationStatus` enum (VALID, EXPIRED, NOT_FOUND, SUPERSEDED) for validation outcomes

**Validated Citation Data Model**:

- `ValidatedCitation` frozen dataclass with provision ID, title, authority level, status, verification date, effective/expiry dates, full text, and cross-references
- `CitationValidationResult` with is_valid flag, validated/invalid citation lists, warnings, and valid/invalid count properties

**KB Provision Registry**:

- `_KB_PROVISIONS` in-memory registry with 24 provisions across Employment Act (11), CPF (1), WSH (2), Fair Employment/TGFEP (4), Foreign Manpower (1), WICA (1), PDPA (3), TADM/ECT (1), TAFEP (1), WFA (1)
- Each entry tracks title, authority level, effective date, and last verified date

**Pre-Delivery Guardrail**:

- `validate_citations()` — deterministic check on every response; validates all cited provision IDs against the KB, flags not-found citations as invalid, and generates staleness warnings for provisions last verified more than 90 days ago
- `get_provision_detail()` — returns full provision metadata for the "View Source" UI action

**Addresses**: R2-GAP2 (citation validation), R2-REC2 (source transparency)

## Files

- `src/hr_advisory/trust/citation_validator.py` — citation validation module
