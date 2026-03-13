# T087 — Automated Test and Rollback for Instruction Patches (Backend)

**Status**: ACTIVE
**Milestone**: 9 — Human QA Workflow
**Priority**: HIGH
**Estimated Effort**: 5h
**Dependencies**: T083, T078, T079, T086

## What to build

When a patch is proposed (T086), automatically re-run the failing scenarios with the patched prompt to verify the patch works before a human approves it. After human approval and deployment, run a full regression suite and auto-rollback if quality drops. This ensures patches are evidence-backed before approval and safe after deployment.

## PatchRunner

### Pre-Approval Testing (triggered when InstructionPatch moves to `proposed`)

1. Identify the evidence scenarios from `InstructionPatch.evidence_ids`
2. Re-run those specific adversarial scenarios using the patched prompt (patch applied in-memory, not deployed)
3. Score with `QualityRubric`
4. Compare before/after scores
5. If average score improves by >= 0.3 on the target dimension: update patch status to `ready_for_approval`, store scores in `test_results`
6. If scores do not improve or regress: update patch status to `rejected`, store rationale in `test_results`

### Post-Deployment Regression (triggered when admin approves and patch is deployed)

1. Apply patch to the live agent system prompt
2. Run full adversarial suite (64 scenarios)
3. If any category average drops > 0.3 below pre-patch baseline: auto-rollback
4. Rollback: restore previous prompt text, update patch status to `rolled_back`, log reason
5. If no regression: update patch status to `deployed`, store regression test results

## Acceptance Criteria

- [ ] `PatchRunner.test_pre_approval(patch: InstructionPatch)` — runs targeted scenarios, updates patch status
- [ ] `PatchRunner.run_regression(patch: InstructionPatch)` — runs full suite, triggers rollback if needed
- [ ] Prompt is applied in-memory for pre-approval testing (no DB or file change)
- [ ] Prompt is applied to source file or DB-backed prompt store for deployment
- [ ] Rollback restores previous prompt version from `InstructionPatch.old_text`
- [ ] All test run results stored as `TestRunResult` records
- [ ] `POST /admin/qa/patches/{id}/approve` triggers deployment + regression run
- [ ] Admin notified of: test results ready, regression failure, successful deployment
- [ ] Integration test: patch that improves score moves to `ready_for_approval`
- [ ] Integration test: patch that causes regression is rolled back automatically

## Files

- `src/hr_advisory/quality/patch_runner.py` — new file
- `src/hr_advisory/api/routers/qa.py` — wire approve endpoint to trigger deployment + regression
- `src/hr_advisory/quality/rubric.py` — `score_batch()` used by patch runner (from T078)

## Reference

12-human-qa-workflow-design.md Section 3.3 (Automated Verification), Section 4.3 (Rollback)

## Definition of Done

- [ ] Pre-approval testing runs without deploying to production
- [ ] Regression suite runs after every deployment
- [ ] Rollback is automatic and takes < 5 seconds
- [ ] TestRunResult records created for every test run (before, after, regression)
- [ ] Admin cannot deploy a patch still in `proposed` status (must be `ready_for_approval`)
