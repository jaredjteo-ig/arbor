# M60: Foundation — PACT Models, Feature Flag, Org Templates

**Milestone**: M60
**Priority**: CRITICAL — all other milestones depend on this
**Scope**: Backend
**Estimated effort**: 3-4 days

This milestone establishes the data structures that everything else builds on.
No governance engine code — only schema, config, and flags. Following the
build-now boundary defined in gap resolution C3.

---

### T400: PactNode and PactEnvelope DataFlow models

**Scope**: backend
**Depends**: nothing
**Files**:

- `src/hr_advisory/models/pact.py` (new file)

**Description**: Create the core PACT persistence models using DataFlow.

`PactNode`:

- `id`: Integer primary key
- `company_id`: FK to Company
- `address`: String — D/T/R address string (e.g. `D1-R1-D2-R1`)
- `node_type`: String — `division`, `team`, `role`
- `label`: String — human-readable (e.g. "Operations", "Warehouse Supervisor")
- `parent_address`: String nullable — parent's address string
- `employee_id`: Integer nullable FK to Employee (if role is filled by a human)
- `agent_role_id`: String nullable — agent role key (e.g. `agent_hr_manager`) if agent-filled
- `fill_type`: String — `human`, `agent`, `shadow_augmented`, `vacant`
- `template_id`: String — envelope template key (e.g. `tmpl_hr_manager`)
- `is_inferred`: Boolean default True — False once owner confirms the tree
- `is_active`: Boolean default True
- `created_at`, `updated_at`

`PactEnvelope`:

- `id`: Integer primary key
- `company_id`: FK to Company
- `node_id`: FK to PactNode (nullable — some envelopes are templates, not node-specific)
- `template_id`: String — which template this was derived from
- `financial_max_per_action`: Integer nullable — None = unlimited
- `financial_daily_cumulative`: Integer nullable
- `financial_monthly_cumulative`: Integer nullable
- `financial_flagging_threshold`: Integer nullable
- `operational_allowed_actions`: JSON array of strings
- `operational_blocked_actions`: JSON array of strings
- `operational_rate_limit`: String nullable (e.g. `100/hour`)
- `operational_scope`: String (e.g. `company_wide`, `own_department`, `own_team`, `own_records_only`)
- `data_access_max_classification`: String — `public`, `restricted`, `confidential`, `secret`
- `data_access_pii_handling`: String
- `temporal_operating_hours`: String (e.g. `Mon-Sat 07:00-22:00 SGT` or `24/7`)
- `temporal_max_task_duration`: String nullable
- `communication_internal`: Boolean default True
- `communication_external`: Boolean default False
- `communication_external_channels`: JSON array nullable
- `communication_review_required_triggers`: JSON array nullable
- `is_active`: Boolean default True
- `created_at`, `updated_at`

`PactAuditEvent`:

- `id`: Integer primary key
- `company_id`: FK to Company
- `event_type`: String — `tree_confirmed`, `envelope_widened`, `envelope_tightened`, `agent_activated`, `agent_deactivated`, `gradient_shifted`, `held_action_resolved`, `emergency_bypass`
- `actor_user_id`: FK to User (who caused this event)
- `target_node_address`: String nullable
- `target_agent_role`: String nullable
- `event_data`: JSON — full context of what changed
- `created_at`

`PactSuggestion`:

- `id`: Integer primary key
- `company_id`: FK to Company
- `suggestion_type`: String — `envelope_widening`, `structural_change`, `agent_activation`, `anomaly_flag`
- `title`: String — plain-language title shown to boss
- `description`: String — plain-language explanation
- `proposed_change`: JSON — what would change if accepted
- `confidence_score`: Float — 0.0 to 1.0
- `evidence_summary`: String — why this is being suggested
- `status`: String — `pending`, `accepted`, `dismissed`
- `reviewed_by`: FK to User nullable
- `reviewed_at`: DateTime nullable
- `created_at`

**Acceptance criteria**:

- [ ] All four models registered with DataFlow
- [ ] `pip install -e .` and all imports succeed
- [ ] `pytest tests/unit/test_pact_models.py` passes (basic CRUD for each model)
- [ ] No circular imports with existing models

---

### T401: HeldAction DataFlow model

**Scope**: backend
**Depends**: T400
**Files**:

- `src/hr_advisory/models/pact.py` (extend)

**Description**: The HeldAction model is the core data structure for the
notification pipeline. When an agent would take an action that falls in the
HELD zone of the gradient, it creates a HeldAction record and stops. The boss
reviews it and approves or rejects.

`HeldAction`:

- `id`: Integer primary key
- `company_id`: FK to Company
- `agent_role`: String — which agent generated this (e.g. `agent_hr_manager`)
- `action_type`: String — what action was being attempted (e.g. `approve_leave`, `process_payroll_run`)
- `action_display`: String — plain-language description for the boss (e.g. "Sarah Lim wants 3 days leave next week")
- `action_context`: String — why the agent is asking (e.g. "Priya and Wei Ming are already off that week")
- `action_options`: JSON array — list of option objects `{key, label, description}` shown to the boss
- `action_data`: JSON — full machine-readable context (leave application ID, etc.)
- `gradient_zone`: String — `flagged` or `held`
- `urgency`: String — `routine`, `urgent`, `deadline`
- `status`: String — `pending`, `approved`, `rejected`, `expired`, `auto_resolved`
- `resolution_option`: String nullable — which option the boss chose
- `resolution_note`: String nullable
- `resolved_by`: FK to User nullable
- `resolved_at`: DateTime nullable
- `escalation_level`: Integer default 0 — increments as reminders are sent
- `expires_at`: DateTime nullable — if set, auto-resolves when passed
- `notify_at`: DateTime — when to send first notification
- `created_at`, `updated_at`

Also add `LeaveApplicationStatus.PENDING_RESCHEDULE = "pending_reschedule"` to the
existing `LeaveApplicationStatus` class in `company_user.py`.

**Acceptance criteria**:

- [ ] `HeldAction` model registered and usable
- [ ] `pending_reschedule` leave status added
- [ ] Unit tests for held action creation and status transitions
- [ ] JSON field validation: `action_options` must be a list of objects with `key` and `label`

---

### T402: `pact_enabled` company feature flag

**Scope**: backend
**Depends**: T400
**Files**:

- `src/hr_advisory/models/company_user.py` (modify Company model)

**Description**: Add `pact_enabled: Boolean default False` to the Company model.
When False, all PACT models exist but are ignored — the existing 4-role RBAC
works exactly as today. When True, the PACT envelope check runs AFTER the RBAC
check (additive, never replacing).

Also add `pact_activated_at: DateTime nullable` and
`pact_template_id: String nullable` (which org template was selected:
`micro`, `small`, `medium`).

**Acceptance criteria**:

- [ ] Company model has `pact_enabled`, `pact_activated_at`, `pact_template_id`
- [ ] Existing tests still pass (flag defaults to False, no behavior change)
- [ ] Migration-safe: `pact_enabled=False` for all existing companies

---

### T403: Org template config — Python dataclasses

**Scope**: backend (config, not engine)
**Depends**: nothing
**Files**:

- `src/hr_advisory/pact/templates/__init__.py` (new package)
- `src/hr_advisory/pact/templates/org_templates.py` (new file)

**Description**: Implement the three SME org templates from domain config spec
Section 1 as Python dataclasses. These are static configuration — not engine code.

```python
@dataclass(frozen=True)
class OrgRole:
    address_suffix: str  # e.g. "R2"
    label: str           # e.g. "HR Manager"
    fill_type: str       # "human", "agent", "shadow_augmented", "vacant"
    template_id: str     # e.g. "tmpl_hr_manager"
    agent_role_id: Optional[str]  # e.g. "agent_hr_manager"

@dataclass(frozen=True)
class OrgDivision:
    address_suffix: str  # e.g. "D1"
    label: str
    roles: list[OrgRole]
    sub_divisions: list["OrgDivision"]

@dataclass(frozen=True)
class OrgTemplate:
    id: str              # "micro", "small", "medium"
    name: str
    employee_range: tuple[int, int]
    tree: OrgDivision
    agent_fillable_roles: list[str]  # list of agent_role_id
    human_roles: list[str]
    shadow_augmented_designations: list[str]
```

Implement `MICRO_TEMPLATE`, `SMALL_TEMPLATE`, `MEDIUM_TEMPLATE` matching
exactly the structures in domain config spec Sections 1.1, 1.2, 1.3.

Implement `select_org_template(employee_count: int) -> OrgTemplate` matching
Section 1.4.

**Acceptance criteria**:

- [ ] Three templates defined as frozen dataclasses
- [ ] `select_org_template(5)` returns MICRO, `(15)` returns SMALL, `(30)` returns MEDIUM
- [ ] Unit tests for template selection
- [ ] Templates are importable from `hr_advisory.pact.templates`

---

### T404: Agent role definitions config

**Scope**: backend (config)
**Depends**: nothing
**Files**:

- `src/hr_advisory/pact/agents/__init__.py` (new package)
- `src/hr_advisory/pact/agents/roles.py` (new file)

**Description**: Implement the 12 agent role definitions from domain config spec
Section 2 as Python dataclasses. Config only — no execution logic.

```python
@dataclass(frozen=True)
class AgentRoleDefinition:
    id: str                           # e.g. "agent_hr_manager"
    title: str
    description: str
    activation_stage: str             # "day_1", "week_1", "week_2", "month_1", "month_2", "month_3"
    llm_usage: str                    # "zero", "optional", "required"
    capabilities: list[str]
    tools: list[str]
    data_access_max_clearance: str
    allowed_models: dict[str, str]    # model_name -> "read" | "read/write"
    excluded_models: list[str]
    envelope_defaults: dict           # mirrors the YAML envelope spec
```

Define all 12 agents: `AGENT_HR_MANAGER`, `AGENT_PAYROLL`, `AGENT_LEAVE_ADMIN`,
`AGENT_ATTENDANCE`, `AGENT_CLAIMS`, `AGENT_COMPLIANCE`, `AGENT_RECRUITMENT`,
`AGENT_ONBOARDING`, `AGENT_ADVISORY`, `AGENT_REPORTS`, `AGENT_DOCUMENTS`,
`AGENT_SHADOW`.

Define `AGENT_REGISTRY: dict[str, AgentRoleDefinition]` keyed by id.

Also define the user-facing composition from gap resolution H1:

```python
USER_FACING_AGENTS = {
    "arbor_hr": ["agent_hr_manager", "agent_leave_admin", "agent_attendance", "agent_onboarding", "agent_documents", "agent_shadow"],
    "arbor_payroll": ["agent_payroll", "agent_claims", "agent_reports"],
    "arbor_compliance": ["agent_compliance", "agent_advisory", "agent_recruitment"],
}
```

**Acceptance criteria**:

- [ ] All 12 agent role definitions implemented
- [ ] `AGENT_REGISTRY["agent_payroll"].llm_usage == "zero"` (deterministic)
- [ ] `AGENT_REGISTRY["agent_advisory"].activation_stage == "day_1"`
- [ ] `USER_FACING_AGENTS` defines the 3 user-facing composites
- [ ] Unit tests for registry lookup and composition

---

### T405: Envelope template definitions config

**Scope**: backend (config)
**Depends**: T403, T404
**Files**:

- `src/hr_advisory/pact/templates/envelope_templates.py` (new file)

**Description**: Implement the 12 envelope templates from domain config spec
Section 4 as Python dataclasses. Reconciled per gap resolution H3: agent
envelopes (Section 2) are authoritative; role templates (Section 4) are
user-friendly presentation layer. Both must produce the same effective
permissions.

```python
@dataclass(frozen=True)
class EnvelopeTemplate:
    id: str                                # e.g. "tmpl_owner"
    matches_designations: list[str]        # designation keywords for auto-assignment
    matches_user_roles: list[str]          # UserRole values
    financial_max_per_action: Optional[int]   # None = unlimited
    financial_daily_cumulative: Optional[int]
    financial_monthly_cumulative: Optional[int]
    financial_flagging_threshold: Optional[int]
    operational_allowed: list[str]
    operational_blocked: list[str]
    operational_scope: str
    data_max_classification: str
    data_pii_handling: str
    temporal_operating_hours: str
    temporal_max_task_duration: Optional[str]
    communication_internal: bool
    communication_external: bool
    communication_external_channels: list[str]
    communication_review_triggers: list[str]
```

Define all 12 templates: `tmpl_owner`, `tmpl_hr_manager`, `tmpl_hr_exec`,
`tmpl_finance_manager`, `tmpl_payroll_officer`, `tmpl_ops_manager`,
`tmpl_supervisor`, `tmpl_sales_manager`, `tmpl_it_manager`,
`tmpl_employee_office`, `tmpl_employee_field`, `tmpl_employee_self`.

Also add `tmpl_consultant` (gap resolution M1): cross-company read scope,
`tmpl_hr_exec` functional level, `data_max_classification: restricted`.

Define `TEMPLATE_REGISTRY: dict[str, EnvelopeTemplate]`.

Define `match_template_for_designation(designation: str, user_role: str) -> EnvelopeTemplate`
that iterates templates, checks keyword matches (case-insensitive), falls back to
`tmpl_employee_office` if no match.

**Acceptance criteria**:

- [ ] All 13 templates defined (12 + tmpl_consultant)
- [ ] `match_template_for_designation("Warehouse Supervisor", "employee")` returns `tmpl_supervisor`
- [ ] `match_template_for_designation("Director", "owner")` returns `tmpl_owner`
- [ ] Unrecognized designations fall back to `tmpl_employee_office`
- [ ] Unit tests for designation matching covering all 13 templates

---

### T406: HR data classification registry

**Scope**: backend (config)
**Depends**: nothing
**Files**:

- `src/hr_advisory/pact/clearance/__init__.py` (new package)
- `src/hr_advisory/pact/clearance/registry.py` (new file)

**Description**: Implement the complete model clearance registry from domain
config spec Section 3 as Python dicts.

```python
MODEL_CLEARANCE_REGISTRY: dict[str, str]  # model_name -> "public" | "restricted" | "confidential" | "secret"
EMPLOYEE_FIELD_CLEARANCE: dict[str, str]  # field_name -> clearance level
```

Copy all entries from Section 3.2 and 3.3 of the spec exactly. This registry is
the single source of truth for PACT knowledge clearance enforcement when the
engine ships.

Also implement helpers:

- `get_model_clearance(model_name: str) -> str` — returns clearance, defaults to `restricted` if not found
- `get_field_clearance(field_name: str) -> str` — returns field clearance from `EMPLOYEE_FIELD_CLEARANCE`, defaults to `confidential`
- `can_access_model(role_max_clearance: str, model_name: str) -> bool` — clearance level comparison

**Acceptance criteria**:

- [ ] Registry contains all 77+ models from the spec
- [ ] `get_model_clearance("Employee") == "confidential"`
- [ ] `get_model_clearance("Company") == "public"`
- [ ] `get_field_clearance("nric_fin") == "confidential"`
- [ ] `get_field_clearance("department") == "public"`
- [ ] `can_access_model("restricted", "Employee") == False`
- [ ] `can_access_model("confidential", "Employee") == True`
- [ ] Unit tests for all clearance checks

---

### T407: Gradient calibration tables

**Scope**: backend (config)
**Depends**: nothing
**Files**:

- `src/hr_advisory/pact/gradient/__init__.py` (new package)
- `src/hr_advisory/pact/gradient/calibration.py` (new file)

**Description**: Implement the verification gradient tables from domain config
spec Section 5 as Python data structures.

```python
@dataclass(frozen=True)
class GradientRule:
    module: str          # "leave", "payroll", "attendance", "claims", "employee", "compliance", "recruitment"
    action: str          # the action being evaluated
    conditions: dict     # key-value conditions (e.g. {"days": "<=2", "balance_sufficient": True})
    zone: str            # "auto_approved", "flagged", "held", "blocked"
    reason: str          # human-readable explanation

GRADIENT_RULES: list[GradientRule]
```

Encode all rows from Section 5.1 through 5.7 (Leave, Payroll, Attendance,
Claims, Employee Management, Compliance, Recruitment modules).

Note: this is configuration only. The evaluation engine (`pact.GradientEngine`)
ships with PACT core. These tables are what Arbor feeds into that engine.

Also implement a simple local evaluator for testing purposes:
`evaluate_gradient_local(module: str, action: str, context: dict) -> str`
that evaluates rules in order, returning the first matching zone. This is used
only in acceptance tests and never in production (production uses the PACT core
engine).

**Acceptance criteria**:

- [ ] All tables from Section 5 encoded (minimum 40 rules)
- [ ] `evaluate_gradient_local("leave", "approve_leave", {"days": 2, "balance_sufficient": True}) == "auto_approved"`
- [ ] `evaluate_gradient_local("payroll", "approve_payroll_run", {}) == "held"`
- [ ] `evaluate_gradient_local("payroll", "modify_cpf_rates", {}) == "blocked"`
- [ ] `evaluate_gradient_local("leave", "delete_leave_record", {}) == "blocked"`
- [ ] Unit tests for 20+ gradient scenarios

---

### T408: Bridge definitions config

**Scope**: backend (config)
**Depends**: T404
**Files**:

- `src/hr_advisory/pact/bridges/__init__.py` (new package)
- `src/hr_advisory/pact/bridges/definitions.py` (new file)

**Description**: Implement the 7 bridge definitions from domain config spec
Section 6 as Python dataclasses.

```python
@dataclass(frozen=True)
class DataFlowSpec:
    model: str
    fields: list[str]     # ["*"] means all accessible fields
    classification_ceiling: str
    purpose: str

@dataclass(frozen=True)
class BridgeDefinition:
    id: str               # e.g. "bridge_leave_payroll"
    from_role: str        # agent_role_id
    to_role: str          # agent_role_id or "*"
    direction: str        # "one_way", "bidirectional"
    scope: str
    regulation: str       # which SG law enables/requires this bridge
    data_flows: list[DataFlowSpec]
    operational_scope: list[str]
    financial_authority: bool  # always False for agent bridges
    is_active: bool       # can be enabled/disabled per company
```

Define all 7 bridges: `bridge_leave_payroll`, `bridge_attendance_payroll`,
`bridge_claims_payroll`, `bridge_recruitment_onboarding`,
`bridge_onboarding_payroll`, `bridge_compliance_audit`,
`bridge_shadow_observation`.

Define `BRIDGE_REGISTRY: dict[str, BridgeDefinition]`.

**Acceptance criteria**:

- [ ] All 7 bridges defined
- [ ] `BRIDGE_REGISTRY["bridge_leave_payroll"].direction == "one_way"`
- [ ] `BRIDGE_REGISTRY["bridge_compliance_audit"].to_role == "*"`
- [ ] `BRIDGE_REGISTRY["bridge_shadow_observation"].financial_authority == False`
- [ ] Unit tests for bridge registry lookup

---

### T409: Singapore regulatory mapping config

**Scope**: backend (config)
**Depends**: nothing
**Files**:

- `src/hr_advisory/pact/regulatory/__init__.py` (new package)
- `src/hr_advisory/pact/regulatory/sg_mappings.py` (new file)

**Description**: Implement the Singapore regulatory mappings from domain config
spec Section 7 as Python dataclasses.

```python
@dataclass(frozen=True)
class RegMapping:
    regulation_id: str    # e.g. "EA", "CPF", "EFMA", "PDPA", "WSH", "WICA"
    full_name: str
    last_amended: str
    affected_agents: list[str]
    enforcement: str
    operating_envelope_constraints: list[str]
    gradient_constraints: list[str]
    data_access_constraints: list[str]
```

Define all 6 mappings: `EA_MAPPING`, `CPF_MAPPING`, `EFMA_MAPPING`,
`PDPA_MAPPING`, `WSH_MAPPING`, `WICA_MAPPING`.

Define `REGULATORY_REGISTRY: dict[str, RegMapping]`.

**Acceptance criteria**:

- [ ] All 6 regulatory mappings defined
- [ ] `REGULATORY_REGISTRY["CPF"].enforcement` contains "deterministic"
- [ ] `REGULATORY_REGISTRY["PDPA"].affected_agents == ["all"]`
- [ ] Unit tests for registry lookup

---

### T410: D/T/R auto-inference algorithm

**Scope**: backend
**Depends**: T403, T405
**Files**:

- `src/hr_advisory/pact/inference/__init__.py` (new package)
- `src/hr_advisory/pact/inference/tree_builder.py` (new file)

**Description**: Implement the `build_pact_tree(company_id: int)` function
from document `02-auto-inference-algorithms.md`. This is the "invisible magic"
of onboarding — given employee data, produces a D/T/R tree with template
assignments.

Algorithm:

1. Load all active employees for `company_id` (name, department, designation,
   reporting_manager_id, start_date)
2. Group by department to discover D nodes
3. Infer T (team) nodes when a department has >3 employees with the same
   reporting_manager (sub-teams)
4. Create R nodes for each employee role based on reporting structure
5. Assign `template_id` via `match_template_for_designation()`
6. Assign `fill_type` based on template (owner = human, field staff = human,
   hr_manager may be human or create agent slot)
7. Create agent-fillable vacant slots for roles not filled by humans
   (e.g. if no one has `hr_manager` designation, create a vacant
   D1-R1-R2 slot for the HR Manager Agent)
8. Persist `PactNode` records (setting `is_inferred=True`)
9. Return tree structure as nested dict for display

Edge cases to handle:

- No "Reports To" data: flat tree, all employees under boss
- Designation not matching any template: use `tmpl_employee_field` for
  Operations departments, `tmpl_employee_office` for Admin
- Multiple bosses (designations matching `tmpl_owner`): use first-registered
  or highest seniority (by start_date)
- Employee is their own manager (data error): ignore the loop, use department head

**Acceptance criteria**:

- [ ] Ahmad Logistics test case: 11 employees produce the exact tree from user flow 01 Step 4b
- [ ] Flat-data fallback: 5 employees with no departments → single department, all under boss
- [ ] Agent vacant slots created for micro template: HR Manager, Payroll Officer, Compliance Monitor
- [ ] `PactNode` records persisted with `is_inferred=True`
- [ ] Idempotent: running twice does not create duplicate nodes
- [ ] Unit tests for Ahmad Logistics scenario
- [ ] Unit tests for flat data scenario
- [ ] Unit tests for missing reporting lines scenario

---

### T411: Agent service accounts and RBAC mapping

**Scope**: backend
**Depends**: T400, T402
**Files**:

- `src/hr_advisory/models/company_user.py` (modify User model)
- `src/hr_advisory/pact/agents/service_accounts.py` (new file)

**Description**: Agent-filled roles need a service account `User` record so
they can call the same API endpoints as human users, subject to the same auth
middleware. Per gap resolution C1 Phase 3: agents get `UserRole.HR_MANAGER`
(the broadest existing role that covers most agent operations), and PACT
envelope constrains within that.

Add to User model:

- `is_agent_service_account: Boolean default False`
- `agent_role_id: String nullable` — which agent this service account represents
- `pact_node_id: Integer nullable` — FK to PactNode

Create `create_agent_service_account(company_id: int, agent_role_id: str, pact_node_id: int) -> User`
that creates a User record with:

- `name`: f"Arbor {AgentRoleDefinition.title}"
- `email`: f"agent.{agent_role_id}.{company_id}@arbor.internal"
- `role`: `UserRole.HR_MANAGER` (base RBAC role)
- `is_agent_service_account`: True
- `agent_role_id`: the given agent role id
- A secure random password (agents authenticate via service token, not password)

Create `get_or_create_service_account(company_id: int, agent_role_id: str) -> User`.

**Acceptance criteria**:

- [ ] `is_agent_service_account`, `agent_role_id`, `pact_node_id` fields on User model
- [ ] `create_agent_service_account` produces a valid User record
- [ ] Service account emails are unique per company+agent combination
- [ ] Existing auth middleware does not break for non-agent users
- [ ] Unit tests for service account creation and retrieval

---

### T412: `pact_enabled` API endpoint and onboarding trigger

**Scope**: backend
**Depends**: T402, T410, T411
**Files**:

- `src/hr_advisory/api/routers/pact.py` (new file — PACT management endpoints)

**Description**: Create the `/api/pact/` router with initial endpoints for
enabling PACT and triggering the tree build.

Endpoints:

- `POST /api/pact/enable` — set `pact_enabled=True` on the company, run
  `build_pact_tree(company_id)`, create service accounts for all agent roles
  defined in the org template. Owner only.
- `GET /api/pact/tree` — return the current D/T/R tree for the company as
  a nested JSON structure. Owner and hr_manager.
- `POST /api/pact/tree/confirm` — set all inferred nodes to `is_inferred=False`.
  Owner only.
- `GET /api/pact/status` — return `{enabled: bool, template: str, nodes: int, agents: int, confirmed: bool}`.

**Acceptance criteria**:

- [ ] `POST /api/pact/enable` returns 200 with the generated tree
- [ ] `GET /api/pact/tree` returns a navigable nested structure
- [ ] `POST /api/pact/tree/confirm` flips `is_inferred` flags
- [ ] Tree is auto-generated from existing employee data (no extra input needed)
- [ ] Calling `enable` twice is idempotent
- [ ] Integration test: register company, add employees, enable PACT, verify tree
