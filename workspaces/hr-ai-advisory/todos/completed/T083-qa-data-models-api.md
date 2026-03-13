# T083 — QA Data Models and API Endpoints

**Status**: ACTIVE
**Milestone**: 9 — Human QA Workflow
**Priority**: HIGH
**Estimated Effort**: 5h
**Dependencies**: T078

## What to build

Create the backend data layer and API surface for the human QA review workflow. This includes DataFlow models for QA sessions and evaluations, instruction patch tracking, and test run results. Also includes the REST endpoints the frontend (T084, T085) and automation (T086, T087) will consume.

## DataFlow Models

### QASession

- `id`, `reviewer_id` (FK to User), `created_at`, `completed_at`
- `date_range_start`, `date_range_end` (filter on conversation dates)
- `filters` (JSON: risk_tier, domain, flagged_only, confidence_min, confidence_max, sampling_strategy)
- `status` (active, completed)
- `summary` (JSON: count_evaluated, avg_overall_score, per_dimension_averages, failure_category_counts)

### QAEvaluation

- `id`, `session_id` (FK to QASession), `conversation_id`, `turn_number`
- `score_legal_accuracy`, `score_contextual_relevance`, `score_coherence`, `score_actionability`
- `score_risk_awareness`, `score_citation_quality`, `score_language`, `score_completeness`
- `citation_flags` (JSON: list of {citation, status: correct/incorrect/missing})
- `has_material_correction` (bool), `correction_text` (text, nullable)
- `failure_category` (enum: legal_error, missing_citation, wrong_risk_tier, incomplete_answer, hallucination, coherence_failure, other)
- `affected_agent` (enum: query_analyzer, employment_act, cpf, foreign_manpower, fair_employment, tax, wsh, pdpa, compliance, synthesizer)
- `created_at`

### InstructionPatch

- `id`, `target_agent` (same enum as affected_agent), `patch_type` (add_rule, modify_rule, add_example, update_threshold)
- `old_text` (nullable — the text being replaced), `new_text` (the proposed addition/change)
- `evidence_count` (number of QA evaluations that motivated this patch)
- `evidence_ids` (JSON: list of QAEvaluation ids)
- `test_results` (JSON: before/after scores per scenario)
- `status` (proposed, testing, ready_for_approval, approved, deployed, rejected, rolled_back)
- `proposed_at`, `approved_at`, `deployed_at`, `approved_by` (FK to User)

### TestRunResult

- `id`, `patch_id` (FK to InstructionPatch), `run_type` (pre_patch, post_patch, regression)
- `scenarios_run` (int), `scenarios_passed` (int), `scenarios_failed` (int)
- `avg_score_before`, `avg_score_after`, `score_delta`
- `failing_scenario_ids` (JSON), `run_at`

## API Endpoints

- `POST /admin/qa/sessions` — create new QA session with filters
- `GET /admin/qa/sessions` — list sessions (active first, then completed)
- `GET /admin/qa/sessions/{id}` — get session detail with summary scores
- `GET /admin/qa/sessions/{id}/conversations` — list conversations matching session filters
- `POST /admin/qa/evaluations` — submit evaluation for a conversation turn
- `GET /admin/qa/evaluations` — list evaluations (filterable by session, agent, category)
- `GET /admin/qa/patches` — list patches (filterable by status, agent)
- `POST /admin/qa/patches/{id}/approve` — approve a patch for deployment
- `POST /admin/qa/patches/{id}/reject` — reject a patch with reason

## Acceptance Criteria

- [ ] All 4 DataFlow models created and migrated
- [ ] All 9 API endpoints implemented with input validation
- [ ] Only admin users can access `/admin/qa/` endpoints (use existing auth from T012)
- [ ] `GET /admin/qa/sessions/{id}/conversations` applies session filters (date range, risk tier, etc.)
- [ ] Integration test: full QA session lifecycle (create → evaluate → list)
- [ ] Integration test: patch approval flow (propose → approve → status updated)

## Files

- `src/hr_advisory/models/qa.py` — DataFlow models
- `src/hr_advisory/api/routers/qa.py` — new router
- `src/hr_advisory/api/main.py` — register qa router

## Reference

12-human-qa-workflow-design.md Sections 7, 8

## Definition of Done

- [ ] All models created with correct field types and FK relationships
- [ ] All 9 endpoints return correct status codes and response shapes
- [ ] Admin-only access enforced (non-admin request returns 403)
