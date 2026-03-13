# T078 — Implement Automated Quality Rubric Scoring System

**Status**: ACTIVE
**Milestone**: 8 — Quality Rubric and Adversarial Testing
**Priority**: HIGH
**Estimated Effort**: 5h
**Dependencies**: T076

## What to build

Implement the 8-dimension quality rubric as a Python scoring module. Each dimension is scored 1-5. Automated checks run deterministically; rubric dimensions requiring semantic evaluation use LLM-as-judge. Overall quality score is the minimum across all 8 dimensions (weakest link).

## 8 Dimensions

1. **Legal Accuracy** — provisions cited exist and apply correctly
2. **Contextual Relevance** — advice matches the company's sector/size/situation
3. **Conversational Coherence** — references prior turns correctly, no contradictions
4. **Actionability** — contains concrete next steps the user can take today
5. **Risk Awareness** — risk tier is appropriate for the actual risk level
6. **Citation Quality** — citations are present, correctly formatted, traceable to KB
7. **Language Understanding** — handles Singlish, abbreviations, implicit context
8. **Completeness** — all parts of a multi-part question answered

## Acceptance Criteria

- [ ] `QualityRubric` class in `rubric.py` with `score(query, response, context)` → `RubricResult`
- [ ] `RubricResult` contains: per-dimension scores (1-5), overall_score (min), pass/fail (threshold 3.0), dimension_flags (list of dimensions below 3)
- [ ] Automated checks in `automated_checks.py`:
  - Citation presence check: response contains at least one `[Act s.X]` format citation
  - Risk tier consistency: amber response does not say "no action needed"; red response includes "consult" language
  - Response structure check: contains Summary, What the law says, What you need to do sections (from T076)
  - Disclaimer presence: appropriate disclaimer text present based on risk tier
  - Domain scope check: specialist domains cited match query classification
- [ ] LLM-as-judge for semantic dimensions: Legal Accuracy, Contextual Relevance, Actionability, Completeness
- [ ] Judge prompt uses 5-point scale with explicit criteria per score level
- [ ] Judge model configurable via `.env` — defaults to a fast/cheap model for batch scoring
- [ ] `score_batch(test_cases: list[TestCase])` → `list[RubricResult]` for adversarial suite
- [ ] Integration test: known-good response scores >= 4.0 on all dimensions
- [ ] Integration test: response with no citations scores 1 on Citation Quality

## Files

- `src/hr_advisory/quality/rubric.py` — new file
- `src/hr_advisory/quality/automated_checks.py` — new file
- `src/hr_advisory/quality/__init__.py` — new file

## Reference

11-agent-architecture-analysis.md Section 4 (Quality Rubric)

## Definition of Done

- [ ] All 8 dimensions implemented and testable
- [ ] Automated checks run in < 100ms (no LLM)
- [ ] LLM-as-judge scores available for all semantic dimensions
- [ ] Score batch function usable by T079 adversarial suite
