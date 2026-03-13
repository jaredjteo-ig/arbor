# Adversarial Test Run -- Baseline

## Run Configuration

- **Date**: 2026-03-13
- **Sample size**: 8 (1 per category)
- **LLM Provider**: OpenAI
- **LLM Model**: gpt-5-chat-latest
- **Scoring**: AutomatedChecks (deterministic dimensions only)
- **Scoring method**: Overall score = min(all dimension scores) (weakest-link principle)
- **Pass threshold**: 3.0

## Context

This is the first adversarial baseline run across all 8 regulatory categories.
The adversarial scenarios test realistic HR questions that probe edge cases,
common misconceptions, and cross-domain interactions in Singapore employment law.

The scoring uses 4 deterministic dimensions that do not require LLM evaluation:
citation_quality, risk_awareness, response_structure, and disclaimer_presence.

## Pre-Run Fix: Pattern Recognition

The initial baseline attempt (Run 0, pre-fix) showed all 8 scenarios scoring 1.0
because the automated checks only recognised `## Heading` format section headers,
while the LLM consistently produces `**Heading**` (bold text) format. The checks
were widened to recognise both formats. Similarly, disclaimer detection patterns
were expanded to recognise natural language variants.

### Run 0 (Pre-Fix) vs Run 1 (Post-Fix) Comparison

| Dimension           | Run 0 Average | Run 1 Average | Change               |
| ------------------- | ------------- | ------------- | -------------------- |
| citation_quality    | 4.12          | 3.12          | -1.00 (LLM variance) |
| risk_awareness      | 4.75          | 5.00          | +0.25                |
| response_structure  | 1.00          | 4.50          | +3.50 (pattern fix)  |
| disclaimer_presence | 1.50          | 4.25          | +2.75 (pattern fix)  |

## Per-Category Results

| Category         | Score | Scenario ID | Risk Tier | Key Finding                                                        |
| ---------------- | ----- | ----------- | --------- | ------------------------------------------------------------------ |
| employment_act   | 5.0   | EA-01       | amber     | Excellent: all dimensions pass, strong citations                   |
| cpf              | 4.0   | CPF-01      | green     | Good: only citation count slightly low (2 citations)               |
| foreign_manpower | 1.0   | FM-01       | green     | Failed: 0 bracket-format citations found                           |
| fair_employment  | 1.0   | FE-01       | red       | Failed: 0 bracket-format citations found                           |
| tax              | 1.0   | TAX-01      | amber     | Failed: no disclaimer/framing text detected                        |
| wsh              | 1.0   | WSH-01      | red       | Failed: response_structure not detected (colon-after-bold variant) |
| pdpa             | 3.0   | PDPA-01     | amber     | Passed: minimal citations but structured well                      |
| cross_domain     | 4.0   | XD-01       | amber     | Good: strong citations, good structure                             |

## Per-Dimension Averages

| Dimension           | Average | Status                       |
| ------------------- | ------- | ---------------------------- |
| citation_quality    | 3.12    | PASS (but weakest dimension) |
| risk_awareness      | 5.00    | PASS (perfect)               |
| response_structure  | 4.50    | PASS                         |
| disclaimer_presence | 4.25    | PASS                         |

## Overall

- **Average overall score**: 2.50
- **Scenarios passed (>=3.0)**: 4 of 8 (50%)
- **Scenarios failed (<3.0)**: 4 of 8 (50%)
- **Scenarios errored**: 0 of 8 (0% -- infrastructure fully operational)
- **Categories below 3.0**: foreign_manpower, fair_employment, tax, wsh
- **Weakest dimension**: citation_quality (3.12 average)
- **Strongest dimension**: risk_awareness (5.00 -- perfect)
- **Duration**: ~100 seconds for 8 scenarios

## Failing Scenarios (score < 3.0)

### FM-01: Foreign Manpower quota question (score 1.0)

- **Failing dimension**: citation_quality = 1.0
- **Issue**: The specialist produced a well-structured response about DRC limits
  but did not include any bracket-format citations like `[EFMA-conditions]`.
  The response references "Employment of Foreign Manpower Regulations" in prose
  but not in the expected `[provision_id]` format.
- **Root cause**: The Foreign Manpower specialist does not reliably format
  citations with bracket notation.

### FE-01: Discriminatory job ad question (score 1.0)

- **Failing dimension**: citation_quality = 1.0
- **Issue**: Same as FM-01 -- no bracket-format citations despite referencing
  TGFEP and WFL in the prose text.
- **Root cause**: Fair Employment specialist citation formatting.

### TAX-01: Foreign employee tax clearance question (score 1.0)

- **Failing dimension**: disclaimer_presence = 1.0
- **Issue**: The response has good citations and structure but lacks a
  framing disclaimer for the amber risk tier. No "based on current..."
  or "under the..." phrasing matched.
- **Root cause**: Tax specialist does not consistently produce
  tier-appropriate framing text.

### WSH-01: Workplace injury reporting question (score 1.0)

- **Failing dimension**: response_structure = 1.0
- **Issue**: The response used `**Summary:**` (with colon after the bold closing)
  which the pattern matcher does not recognise. This is a minor formatting
  variant that the checks should handle.
- **Root cause**: Edge case in section header pattern matching -- the colon
  after `**Summary:**` prevents the regex from matching.

## Root Cause Analysis

The failures cluster around two issues:

### Issue 1: Citation Format Inconsistency (affects FM-01, FE-01)

Some specialists reference legal provisions in prose ("Under the Employment of
Foreign Manpower Act...") without using the bracket citation format (`[EFMA-conditions]`)
that the automated checks look for. The citation_quality check counts bracket-format
citations in the response text AND provisions from the `cited_provisions` list.
When neither source has data, the score drops to 1.0.

### Issue 2: Formatting Micro-Variants (affects TAX-01, WSH-01)

- TAX-01: No framing text matched despite using regulatory language
- WSH-01: `**Summary:**` (with colon) not matched by `**Summary**` pattern

## Recommendations for Next Iteration

1. **Citation format detection**: Expand the citation quality regex to also match
   parenthetical references like `(EA s.10)`, `(CPFA s.52)`, etc. Many responses
   cite provisions in this format rather than bracket notation.

2. **Section header patterns**: Add colon-after-bold patterns like
   `**Summary:**` and `**Summary: **` to the structure check regex.

3. **Tax specialist disclaimer**: Review the Tax specialist prompt and
   add explicit instructions to include tier-appropriate framing.

4. **Run a category-specific deep test**: Run all 8 scenarios for
   `foreign_manpower` and `fair_employment` to see if the citation
   issue is consistent or intermittent.

5. **Consider parenthetical citation counting**: Many responses cite
   provisions as "(EA s.14)" rather than "[EA-S14]". The automated
   check should recognise both formats.

## Iteration Protocol

1. Run `python scripts/run_adversarial_baseline.py`
2. Identify categories with avg score < 3.0
3. For each failing cluster:
   a. Read the affected specialist's system prompt
   b. Add a Common Mistake entry or Reasoning Scaffold step
   c. Re-run `runner.run_category(category)` to verify improvement
   d. Run `runner.run_full()` to check for regressions
4. Document changes in the next adversarial run report

## Files Changed in T080

- `src/hr_advisory/quality/automated_checks.py` -- Expanded pattern matching:
  - Section headers: now recognises `**Summary**` (bold) in addition to `## Summary`
  - Action steps: added `**Next steps**`, `**What to do now**`, `**Recommended actions**`
  - Disclaimer detection: added `consult...lawyer/specialist`, `professional advice/guidance`,
    `under the...Act/legislation`, `under current...law/framework`, `as of YYYY`
  - Generic disclaimers: added `general guidance`, `informational purposes`,
    `does not constitute legal advice`
- `tests/integration/test_adversarial_baseline.py` -- New integration test suite (8 tests)
- `scripts/run_adversarial_baseline.py` -- Standalone baseline runner script
- `pyproject.toml` -- Registered `slow` and `integration` pytest marks
