# T080 — Run Adversarial Scenarios and Iterate Prompt Improvements

**Status**: ACTIVE
**Milestone**: 8 — Quality Rubric and Adversarial Testing
**Priority**: HIGH
**Estimated Effort**: 8h (iterative)
**Dependencies**: T072, T073, T074, T075, T076, T078, T079

## What to build

Execute the full 64-scenario adversarial test suite against the improved pipeline (after Milestone 6 and 7 tasks). Score each response using the quality rubric. Identify the lowest-scoring dimensions and scenarios. Iterate: adjust prompts → re-run failing scenarios → verify improvement without regression. Document results.

## Acceptance Criteria

- [ ] First full run completed and scores recorded in `workspaces/hr-ai-advisory/04-validate/adversarial-run-01.md`
- [ ] Baseline scores documented: per-category average, per-dimension average, overall minimum
- [ ] Failing scenarios (score < 3.0) identified and grouped by: affected agent, failure dimension, failure category
- [ ] At least one prompt iteration cycle completed for the lowest-scoring category
- [ ] Re-run after iteration shows improvement in failing scenarios
- [ ] Regression check: previously passing scenarios still pass after iteration
- [ ] Final run achieves: overall_score >= 3.5 average across all 64 scenarios
- [ ] Target: no category with average score < 3.0
- [ ] Results documented in `workspaces/hr-ai-advisory/04-validate/adversarial-run-final.md`

## Iteration Protocol

For each failing scenario cluster:

1. Identify the affected agent's system prompt section
2. Add or refine a Common Mistake entry or Reasoning Scaffold step
3. Re-run the failing scenarios (targeted, not full suite)
4. If improvement confirmed, run full suite to check regression
5. Document change and evidence

## Files (output — documentation)

- `workspaces/hr-ai-advisory/04-validate/adversarial-run-01.md` — baseline results
- `workspaces/hr-ai-advisory/04-validate/adversarial-run-final.md` — post-iteration results
- `workspaces/hr-ai-advisory/04-validate/prompt-changes-log.md` — what was changed and why

## Definition of Done

- [ ] All 64 scenarios executed at least twice (baseline + post-iteration)
- [ ] Average overall score >= 3.5
- [ ] No category average below 3.0
- [ ] Prompt changes documented with before/after score evidence
