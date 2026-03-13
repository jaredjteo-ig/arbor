# T086 — Feedback-to-Improvement Pipeline (Backend)

**Status**: ACTIVE
**Milestone**: 9 — Human QA Workflow
**Priority**: HIGH
**Estimated Effort**: 6h
**Dependencies**: T083, T078

## What to build

Implement the backend pipeline that converts QA evaluation data into `InstructionPatch` candidates. Two components: a pattern detector that identifies recurring failure clusters, and a mutation engine that proposes specific text changes to agent system prompts based on the evidence. Human approval is required before any patch deploys (T087 handles the automated test and deploy path).

## PatternDetector

Runs after each QA evaluation is submitted. Clusters failures by `failure_category` and `affected_agent`. When a cluster reaches 3+ instances, it triggers `MutationEngine`.

Logic:

- Query QAEvaluations where `has_material_correction = True` grouped by (affected_agent, failure_category)
- If count >= 3 for any group AND no existing patch in `proposed/testing/ready_for_approval` status covers this group: trigger mutation
- Tag which evaluations are the evidence set

## MutationEngine

Takes a cluster of evaluations and proposes an `InstructionPatch`:

- Reads the current system prompt for `target_agent` (from source file or DB cache)
- Sends LLM call: "Given these QA evaluations [corrections], propose a specific addition to the QA-LEARNED RULES section of this agent's system prompt"
- Mutation scope enforcement: LLM is constrained to modify only the `## QA-LEARNED RULES` section — a designated section that must be added to all agent system prompts
- Output: `InstructionPatch` record with `new_text` set to the proposed addition
- `patch_type` is always `add_rule` unless the correction explicitly identifies an existing wrong rule

## Acceptance Criteria

- [ ] `PatternDetector.run()` method: queries evaluations, identifies clusters, returns list of clusters ready for mutation
- [ ] `PatternDetector` called as a background task after each evaluation submission (async, not blocking the API response)
- [ ] `MutationEngine.propose(cluster: EvaluationCluster)` → `InstructionPatch` record created in DB with status `proposed`
- [ ] `## QA-LEARNED RULES` section added to all 8 specialist agent system prompts as designated mutation zone
- [ ] Mutation scope enforced: LLM prompt instructs "add a rule to the QA-LEARNED RULES section only — do not modify any other section"
- [ ] Duplicate patch prevention: if an open patch already exists for the same (agent, category), do not create another
- [ ] Admin notification: when a new patch is in `proposed` status, add an entry to the admin notification queue (existing system from T041)
- [ ] Integration test: 3 evaluations submitted for the same agent/category → patch created
- [ ] Integration test: duplicate patch not created if one is already open

## Files

- `src/hr_advisory/quality/pattern_detector.py` — new file
- `src/hr_advisory/quality/mutation_engine.py` — new file
- `src/hr_advisory/agents/specialists/_base.py` — add `## QA-LEARNED RULES` section to prompt template
- All specialist system prompts — add empty `## QA-LEARNED RULES` section

## Reference

12-human-qa-workflow-design.md Section 3 (Feedback-to-Improvement Pipeline), Section 4 (Instruction Fine-Tuning)

## Definition of Done

- [ ] PatternDetector clusters evaluations correctly
- [ ] MutationEngine produces coherent, specific rule additions (not vague instructions)
- [ ] QA-LEARNED RULES section present in all specialist prompts
- [ ] No mutation modifies any section outside QA-LEARNED RULES
- [ ] Admin notified of new patches requiring approval
