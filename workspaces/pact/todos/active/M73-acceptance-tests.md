# M73: Acceptance Tests — PACT Core Integration

**Milestone**: M73 (acceptance tests for PACT core engine integration)
**Priority**: HIGH — these tests define the contract with the pact-core library
**Scope**: backend
**Estimated effort**: 3-4 days

Per gap resolution C3, Arbor builds acceptance tests now. These tests assert
against the future `pact` library API. Every test is marked `pytest.mark.skip`
with the reason `"[BLOCKED: pact-core] — engine not yet available"`.

When `pip install pact` ships, remove the `@pytest.mark.skip` decorators and
run the suite. All tests must pass against the real engine with zero changes
to test code.

File structure:

```
tests/pact/
├── conftest.py                    (fixtures)
├── test_gradient_evaluation.py   (T467)
├── test_clearance_engine.py      (T468)
├── test_held_action_pipeline.py  (T469)
├── test_envelope_intersection.py (T470)
├── test_bridge_integration.py    (T471)
├── test_progressive_activation.py (T472)
└── test_sg_regulatory_mappings.py (T473)
```

---

### T467: Gradient evaluation acceptance tests

**Scope**: backend
**Depends**: T407 (gradient calibration config)
**Files**:

- `tests/pact/test_gradient_evaluation.py` (new)
- `tests/pact/conftest.py` (new)

**Description**: Tests that assert the PACT gradient engine correctly zones
agent actions for each of Arbor's 7 calibrated modules.

`conftest.py` fixtures:

```python
@pytest.fixture
def micro_sme_context():
    """Company context: micro SME, pact_enabled, arbor_hr active."""
    return {
        "company_id": 999,
        "agent_role": "hr_manager",
        "org_template": "micro_sme",
        "pact_enabled": True,
    }

@pytest.fixture
def gradient_engine():
    """[BLOCKED: pact-core] — replace with: from pact import GradientEngine"""
    pytest.skip("[BLOCKED: pact-core]")
```

Test scenarios (all `@pytest.mark.skip("[BLOCKED: pact-core]")`):

**Leave module**:

- `test_leave_approve_within_limit_is_auto_approved`: 2-day leave, 10 employees, no overlap → AUTO_APPROVED
- `test_leave_approve_with_team_overlap_is_held`: 2-day leave during period when 50% of team already on leave → HELD
- `test_leave_approve_during_notice_period_is_held`: Employee on notice, applying for leave → HELD
- `test_leave_approve_beyond_balance_is_blocked`: Applying for more days than balance → BLOCKED
- `test_mass_leave_application_is_flagged`: 4 employees in 5-person company all applying same week → FLAGGED

**Payroll module**:

- `test_routine_payroll_run_is_auto_approved`: No changes from last month → AUTO_APPROVED
- `test_payroll_with_variance_over_20pct_is_held`: One employee's pay differs by >20% from last month → HELD
- `test_payroll_with_terminated_employee_is_flagged`: Run includes employee terminated this month → FLAGGED
- `test_payroll_with_missing_cpf_is_blocked`: Payroll run when CPF credentials not configured → BLOCKED

**Claims module**:

- `test_small_claim_within_policy_is_auto_approved`: Medical claim ≤ $100 with receipt → AUTO_APPROVED
- `test_large_claim_over_limit_is_held`: Claim > $500 → HELD
- `test_claim_with_no_receipt_is_flagged`: Medical claim without supporting document → FLAGGED

**Attendance module**:

- `test_routine_attendance_pattern_is_auto_approved`: Employee 2 minutes late, first time this month → AUTO_APPROVED
- `test_repeated_lateness_is_flagged`: Employee late >3 times this week → FLAGGED

**Acceptance criteria**:

- [ ] All tests present and marked `pytest.mark.skip("[BLOCKED: pact-core]")`
- [ ] Skip marker includes exact string `[BLOCKED: pact-core]`
- [ ] Each test calls `gradient_engine.evaluate(action, context)` — no custom logic
- [ ] Each test asserts against `Verdict` enum values from pact library
- [ ] conftest.py fixtures compile without importing pact (skip inside fixture)
- [ ] Running `pytest tests/pact/ -v` shows correct skip messages, no errors

---

### T468: Clearance engine acceptance tests

**Scope**: backend
**Depends**: T406 (clearance registry)
**Files**:

- `tests/pact/test_clearance_engine.py` (new)

**Description**: Tests for the PACT clearance engine — does a given agent role
have access to a given data resource at the requested clearance level?

Test scenarios:

**Agent role access**:

- `test_hr_agent_can_access_restricted_data`: `hr_manager` role accessing
  `Employee.job_title` (RESTRICTED) → PERMITTED
- `test_hr_agent_cannot_access_confidential_data`: `hr_manager` role accessing
  `Employee.base_salary` (CONFIDENTIAL) → DENIED
- `test_employee_self_service_can_access_own_public_data`: `employee` role
  accessing own `Employee.name` (PUBLIC) → PERMITTED
- `test_employee_cannot_access_other_employee_salary`: `employee` role accessing
  another employee's `Employee.base_salary` → DENIED
- `test_payroll_agent_can_access_confidential_salary`: `payroll_agent` role
  accessing `Employee.base_salary` (CONFIDENTIAL) → PERMITTED (payroll
  envelope grants CONFIDENTIAL access)
- `test_payroll_agent_cannot_access_secret_bank_data`: `payroll_agent` role
  accessing `Employee.bank_account_number` (SECRET) → DENIED (requires bridge)
- `test_consultant_can_access_restricted_not_confidential`: `consultant` role
  with tmpl_consultant → RESTRICTED permitted, CONFIDENTIAL denied

**Bridge-mediated access**:

- `test_bridge_grants_secret_access_to_payroll_agent`: When `bridge_cpf_ezpay`
  is active for company, payroll agent can access CPF number → PERMITTED
- `test_bridge_access_denied_without_bridge_active`: Same access attempt when
  bridge is NOT active → DENIED

**Acceptance criteria**:

- [ ] All 9 tests present and marked `pytest.mark.skip("[BLOCKED: pact-core]")`
- [ ] Tests use `clearance_engine.can_access(role, resource, level, context)` API
- [ ] No test implements custom clearance logic
- [ ] Registry fixtures loaded from `pact/hr_data_classification.py` (T406)
- [ ] Tests compile without pact library installed

---

### T469: Held-action pipeline acceptance tests

**Scope**: backend
**Depends**: T401, T413, T414, T416
**Files**:

- `tests/pact/test_held_action_pipeline.py` (new)

**Description**: End-to-end tests for the held-action pipeline from action
evaluation through notification through resolution.

Note: most of these tests do NOT require pact-core. The pipeline tests test
Arbor's own code (HeldAction model, notifications, API). Only the gradient
evaluation portion is blocked.

Test scenarios:

**Pipeline integration** (NOT blocked — test Arbor code):

- `test_held_action_created_when_gradient_returns_held`: Mock gradient engine
  to return HELD → verify HeldAction record created with correct fields
- `test_held_action_sends_push_notification`: After HeldAction created → verify
  push_service called with HELD_ACTION notification type
- `test_held_action_resolve_sets_status`: Call `POST /api/pact/held-actions/{id}/resolve`
  → status = approved, resolved_by = user_id, resolved_at set
- `test_resolve_creates_audit_event`: Resolve a held action → PactAuditEvent created
- `test_invalid_option_key_rejected`: Resolve with option key not in action_options → 422
- `test_employee_cannot_resolve_held_action`: Employee user calls resolve → 403
- `test_expired_held_action_cannot_be_resolved`: HeldAction with status=expired → 422
- `test_daily_digest_skips_zero_pending`: Company with 0 pending actions → no push sent
- `test_escalation_increments_level`: Call `send_escalation` → escalation_level + 1

**Gradient integration** (BLOCKED — require pact-core):

- `test_held_action_pipeline_full_flow`: From leave application with overlap →
  gradient HELD → HeldAction created → notification sent → boss resolves →
  leave application updated

**Acceptance criteria**:

- [ ] Non-blocked tests are NOT skipped (run with real Arbor code + mocks)
- [ ] Blocked tests are skipped with `[BLOCKED: pact-core]`
- [ ] `test_held_action_created_when_gradient_returns_held` passes now
      (with gradient engine mocked)
- [ ] `test_resolve_creates_audit_event` passes now
- [ ] Integration test uses real DataFlow models (not in-memory stubs)

---

### T470: Envelope intersection acceptance tests

**Scope**: backend
**Depends**: T405 (envelope templates)
**Files**:

- `tests/pact/test_envelope_intersection.py` (new)

**Description**: Tests that PACT envelope intersection (monotonic tightening)
works correctly. All blocked — requires pact-core `EnvelopeEngine`.

Test scenarios (all `@pytest.mark.skip("[BLOCKED: pact-core]")`):

- `test_company_envelope_tightens_template`: tmpl_micro_sme has financial_limit=5000;
  company overrides to 3000 → effective limit = 3000 (min wins)
- `test_envelope_cannot_widen_beyond_template`: Template has financial_limit=5000;
  company override sets 10000 → effective limit = 5000 (cannot widen)
- `test_nested_envelope_intersection`: org → company → agent envelopes all intersected;
  most restrictive dimension from each level applies
- `test_consultant_envelope_restricts_actions`: tmpl_consultant intersected with
  company envelope → consultant cannot approve actions (action_approval=False in
  tmpl_consultant overrides any company setting)
- `test_pact_enabled_false_skips_envelope`: Company with pact_enabled=False →
  envelope intersection not applied, RBAC-only check used

**Acceptance criteria**:

- [ ] All 5 tests present and marked `pytest.mark.skip("[BLOCKED: pact-core]")`
- [ ] Tests load actual envelope template YAML from T405 config files
- [ ] Tests call `envelope_engine.intersect([t1, t2, t3])` API
- [ ] Tests assert on resulting `OperationalConstraints.financial_limit` values

---

### T471: Bridge integration acceptance tests

**Scope**: backend
**Depends**: T430, T408
**Files**:

- `tests/pact/test_bridge_integration.py` (new)

**Description**: Tests for bridge activation, action gating, and external
system integration.

Test scenarios (mixed blocked/not-blocked):

**Not blocked (Arbor code)**:

- `test_activate_bridge_creates_company_bridge_record`: Call
  `POST /api/pact/bridges/bridge_cpf_ezpay/activate` → CompanyBridge record created
- `test_bridge_requires_owner_to_activate`: Non-owner cannot activate bridge → 403
- `test_deactivate_bridge_sets_status_inactive`: Deactivate bridge → status=inactive
- `test_deactivated_bridge_blocks_dependent_action`: CompanyBridge inactive + agent
  tries to use bridge → action held (mock gradient to return BLOCKED for missing bridge)

**Blocked (pact-core)**:

- `test_active_bridge_unlocks_secret_data_access`: When bridge_cpf_ezpay active,
  pact ClearanceEngine grants access to CPF numbers → `[BLOCKED: pact-core]`
- `test_bridge_audit_trail_in_eatp`: Every bridge-mediated action creates EATP
  record → `[BLOCKED: pact-core]`

**Acceptance criteria**:

- [ ] Non-blocked tests pass without pact-core
- [ ] Blocked tests skip with correct message
- [ ] `test_activate_bridge_creates_company_bridge_record` passes now
- [ ] Integration test uses real DataFlow models

---

### T472: Progressive activation acceptance tests

**Scope**: backend
**Depends**: T423, T442, T448
**Files**:

- `tests/pact/test_progressive_activation.py` (new)

**Description**: Tests for the progressive trust ladder — observation, suggestion,
activation, and trust building over time.

All NOT blocked (test Arbor's own code — not pact-core):

- `test_observation_backfill_on_pact_enable`: Enable PACT for company with
  existing leave approvals → observations created, suggestion generated
- `test_suggestion_created_after_threshold`: Record 3 leave_approved_manually
  events → PactSuggestion created for arbor_hr
- `test_suggestion_not_duplicated`: Record 5 leave events when suggestion already
  exists → still only 1 active suggestion
- `test_accept_suggestion_activates_agent`: Accept suggestion via API →
  agent.status = active
- `test_dismiss_suggestion_prevents_immediate_resurface`: Dismiss suggestion →
  check_suggestion_triggers skips dismissed suggestions for 7 days
- `test_agent_action_creates_log_entry`: HR agent auto-approves leave →
  AgentActionLog record created
- `test_reliability_100pct_for_new_agent`: New agent with 0 actions →
  reliability = 100.0
- `test_reliability_decreases_with_escalations`: 8 completed + 2 escalated →
  reliability = 80.0
- `test_cost_savings_calculation`: 5 leave approvals (8min each) + 1 payroll
  run (4h) → hours_saved = 4.67, dollar_value = 233.33

**Acceptance criteria**:

- [ ] All 9 tests pass without pact-core (fully testable with Arbor code)
- [ ] Each test uses real DataFlow models (not mocks for model operations)
- [ ] Tests are isolated (no shared state between test runs)
- [ ] `test_reliability_decreases_with_escalations` asserts within 0.01 tolerance

---

### T473: Singapore regulatory mapping acceptance tests

**Scope**: backend
**Depends**: T409
**Files**:

- `tests/pact/test_sg_regulatory_mappings.py` (new)

**Description**: Tests that the Singapore regulatory config is complete,
internally consistent, and maps correctly to PACT concepts.

Not blocked — tests Arbor config code, not pact-core:

- `test_all_six_regulations_present`: EA, CPF Act, EFMA, PDPA, WSH, WICA
  all in `SG_REGULATORY_MAPPINGS`
- `test_each_regulation_has_required_fields`: Every regulation entry has:
  `agency`, `applicable_modules`, `held_action_triggers`, `auto_approved_items`
- `test_ea_leave_trigger_is_held_for_notice_period`: EA mapping has
  `"leave_during_notice_period"` in `held_action_triggers`
- `test_cpf_act_payroll_is_auto_approved`: CPF Act mapping has payroll preparation
  in `auto_approved_items` (deterministic payroll engine is compliant)
- `test_pdpa_triggers_held_for_external_data_share`: PDPA mapping has any
  external data sharing action in `held_action_triggers`
- `test_wsh_incident_reporting_is_held`: WSH mapping requires human review for
  incident reporting → `held_action_triggers`
- `test_all_bridges_in_mappings_have_corresponding_bridge_definition`: Every
  bridge referenced in regulatory mappings exists in bridge definitions config (T408)
- `test_regulatory_coverage_endpoint_returns_all_regulations`: Call
  `GET /api/pact/regulatory-coverage` → all 6 regulations present

**Acceptance criteria**:

- [ ] All 8 tests pass without pact-core
- [ ] Tests import config from `hr_advisory/pact/config/sg_regulatory_mappings.py`
- [ ] Tests do NOT hardcode expected values — read from config
      (tests that config is internally consistent, not that specific values are present)
- [ ] Running full suite: `pytest tests/pact/ -v` shows 8 passed, N skipped, 0 failed
