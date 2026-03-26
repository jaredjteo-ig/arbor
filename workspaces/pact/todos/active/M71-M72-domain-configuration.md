# M71-M72: Domain Configuration and Label Mapping

**Milestone**: M71 (clearance registry + regulatory mappings in UI), M72 (LLM usage matrix + bridge UI)
**Priority**: MEDIUM — required for ops transparency and consultant access
**Scope**: both
**Estimated effort**: 4-5 days

This milestone exposes domain configuration to appropriate users:

- Gap H4: UI-to-PACT field mapping table (partially addressed in T453; this
  milestone makes the registry visible to power users and consultants)
- Gap M4: LLM usage matrix per agent (which actions use LLM vs deterministic)
- Consultant role: `tmpl_consultant` envelope template — consultants get
  advisory access but cannot approve actions
- Clearance registry exposure: superuser/support can inspect what data
  each agent can access

---

## M71: Clearance Registry and Regulatory Mapping UI

### T460: Clearance registry read endpoint

**Scope**: backend
**Depends**: T406
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)

**Description**: Expose the data classification registry from T406 as a
read-only API endpoint. Used by the permissions UI and by consultants who
need to understand what data agents can access.

`GET /api/pact/clearance-registry`:

- Returns `{models: [{name, clearance_level, description}], fields: [{model, field, clearance_level}]}`
- No authentication beyond owner (consultants can also read — they need to
  understand data access)
- Field clearance only returned for PUBLIC and RESTRICTED entries
  (CONFIDENTIAL and SECRET field names are masked: `"[confidential field]"`)
- Sorted: PUBLIC first, then RESTRICTED, then CONFIDENTIAL, then SECRET

`GET /api/pact/clearance-registry/agent/{agent_id}`:

- Returns the effective data access for a specific agent
- Derived from the agent's envelope template `DataAccessConstraints.clearance_level`
- Shows: `{agent_id, can_access: [{model, fields}], cannot_access: [{model, reason}]}`

**Acceptance criteria**:

- [ ] Returns all models and their clearance levels
- [ ] CONFIDENTIAL/SECRET field names masked in response
- [ ] Agent-specific view shows correct access based on envelope template
- [ ] Owner and hr_manager and consultant can read (employee gets 403)
- [ ] Unit test: arbor_hr agent can access RESTRICTED but not CONFIDENTIAL

---

### T461: Data access transparency page

**Scope**: frontend
**Depends**: T460
**Files**:

- `apps/web/app/(dashboard)/arbor-agents/[agentId]/data-access/page.tsx` (new)
- `apps/web/components/pact/DataAccessMatrix.tsx` (new)

**Description**: Plain-language explanation of what data each agent can see.
Per the value critique, the boss must understand and trust what the agent
accesses — opacity destroys trust.

`DataAccessMatrix`:

- Table: data category | what agent can see | what agent cannot see
- Data categories mapped from clearance levels (plain language):
  - PUBLIC → "Company policies and org chart"
  - RESTRICTED → "Employee details, leave records, attendance"
  - CONFIDENTIAL → "Salary and compensation" (shown with lock icon)
  - SECRET → "Bank account details" (shown with lock icon + "never")
- For each row: green check for accessible, red X for not accessible,
  lock icon for permanently restricted

Linked from:

- `AgentDetailPanel` (T452) "What data can it see?" link
- Permissions page (T453) footer link

**Acceptance criteria**:

- [ ] All 4 clearance levels shown with plain labels
- [ ] Lock icons on CONFIDENTIAL and SECRET rows
- [ ] Green/red indicators match actual clearance levels from API
- [ ] Page loads within 1 second (static-ish data)
- [ ] Works for all 3 agents (different clearance levels)

---

### T462: Singapore regulatory mapping display

**Scope**: frontend
**Depends**: T409
**Files**:

- `apps/web/app/(dashboard)/arbor-agents/compliance-coverage/page.tsx` (new)
- `apps/web/components/pact/RegulatoryCoverageTable.tsx` (new)

**Description**: Show which Singapore regulations each agent covers. Linked
from the Compliance Agent detail page. Answers: "Which laws does Arbor
monitor for me?"

`RegulatoryCoverageTable`:

- Table: regulation | what Arbor monitors | what is NOT automated (requires human)
- Rows from T409 config: EA, CPF Act, EFMA, PDPA, WSH, WICA
- Per regulation:
  - "Monitors": comma-list of items (e.g. "Leave entitlements, notice period")
  - "Not automated": items that require human judgment or are not in scope
    (e.g. "Employment contract negotiations", "Retrenchment exercises")
- Footer: "Last updated: [date from regulatory mapping version tag]"

`GET /api/pact/regulatory-coverage`:

- Returns regulatory mapping data from T409 config file
- No auth required (public information — no company-specific data)

**Acceptance criteria**:

- [ ] All 6 Singapore regulations shown
- [ ] Each row has "monitors" and "not automated" columns
- [ ] Page accessible without login (publicly viewable marketing-grade info)
- [ ] Linked from Compliance Agent detail page

---

### T463: Consultant access — tmpl_consultant envelope activation

**Scope**: backend
**Depends**: T405, T411
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)
- `src/hr_advisory/api/routers/companies.py` (extend)

**Description**: Consultants have the `UserRole.CONSULTANT` role in the existing
RBAC system. When PACT is enabled, they should be assigned the `tmpl_consultant`
envelope which gives them read-only access to RESTRICTED data (employee details,
leave, payroll summaries) but no action-taking ability.

Per the gap resolution C1 build-now boundary: create the model and activation
logic. The PACT engine's envelope intersection happens in pact-core.

`POST /api/companies/{id}/consultants/{user_id}/enable-pact`:

- Sets a `ConsultantPactEnrollment` record:
  - `company_id`, `user_id`, `envelope_template_key: tmpl_consultant`,
    `enrolled_at`, `enrolled_by`
- Validates: user must have CONSULTANT role in the company
- Creates `PactAuditEvent` for enrollment
- Owner only

`DELETE /api/companies/{id}/consultants/{user_id}/pact`:

- Removes `ConsultantPactEnrollment`
- Creates `PactAuditEvent` for removal

`GET /api/pact/my-enrollment`:

- For consultants: returns their enrollment status and effective permissions
- For owners: returns full company enrollment summary

**Acceptance criteria**:

- [ ] Enrolling a consultant creates ConsultantPactEnrollment record
- [ ] Non-consultant user returns 422 on enrollment
- [ ] Audit event created on enrollment and removal
- [ ] Consultant can read `GET /api/pact/my-enrollment`
- [ ] Owner gets company-wide summary from same endpoint

---

## M72: LLM Usage Matrix and Bridge Management UI

### T464: LLM usage matrix — which actions are LLM vs deterministic

**Scope**: backend + frontend
**Depends**: T424, T425, T426, T429, T433
**Files**:

- `src/hr_advisory/pact/llm_matrix.py` (new)
- `apps/web/components/pact/LlmUsageMatrix.tsx` (new)

**Description**: Gap M4 asks: which agent actions use LLM and which are
deterministic? The payroll engine is ALWAYS deterministic (zero LLM — per
project memory). Some HR and compliance actions use LLM for reasoning.

`llm_matrix.py`:

```python
LLM_USAGE_MATRIX = {
    "arbor_hr": {
        "leave_approval": {
            "method": "deterministic",
            "description": "Policy rules engine. No AI reasoning.",
            "llm_used": False,
        },
        "attendance_monitoring": {
            "method": "deterministic",
            "description": "Threshold comparison against configured rules.",
            "llm_used": False,
        },
        "policy_qa": {
            "method": "llm",
            "description": "LLM with KB retrieval (advisory safety chain).",
            "llm_used": True,
            "model_tier": "standard",
        },
        "onboarding_guidance": {
            "method": "hybrid",
            "description": "Checklist is deterministic; welcome message is LLM.",
            "llm_used": True,
            "model_tier": "standard",
        },
    },
    "arbor_payroll": {
        "payroll_preparation": {
            "method": "deterministic",
            "description": "Pure arithmetic. Zero LLM. Auditable calculations.",
            "llm_used": False,
        },
        "cpf_submission": {
            "method": "deterministic",
            "description": "CPF API integration. No LLM involved.",
            "llm_used": False,
        },
        "variance_explanation": {
            "method": "llm",
            "description": "LLM generates plain-language payslip summary.",
            "llm_used": True,
            "model_tier": "standard",
        },
    },
    "arbor_compliance": {
        "work_pass_monitoring": {
            "method": "deterministic",
            "description": "Date arithmetic against expiry dates.",
            "llm_used": False,
        },
        "filing_deadlines": {
            "method": "deterministic",
            "description": "Calendar rules for statutory filing dates.",
            "llm_used": False,
        },
        "regulatory_update_analysis": {
            "method": "llm",
            "description": "LLM classifies impact of MOM/IRAS regulatory updates.",
            "llm_used": True,
            "model_tier": "standard",
        },
    },
}
```

`GET /api/pact/llm-usage`:

- Returns matrix grouped by agent
- No authentication required (transparency-first)

`LlmUsageMatrix` component:

- Table: action | method | description
- "Deterministic" rows shown with gear icon (no LLM)
- "LLM" rows shown with brain icon
- "Hybrid" rows shown with both icons
- Tagline: "Your payroll is always calculated by deterministic rules — no AI
  guesswork."

Linked from: agent detail pages (T452) and FAQ/trust pages.

**Acceptance criteria**:

- [ ] Matrix covers all actions for all 3 agents
- [ ] Payroll preparation is marked deterministic in matrix
- [ ] Policy Q&A is marked LLM
- [ ] Frontend renders all rows with correct icons
- [ ] `GET /api/pact/llm-usage` returns complete matrix
- [ ] Unit test: matrix contains expected keys for all agents

---

### T465: Bridge activation and management UI

**Scope**: frontend
**Depends**: T430
**Files**:

- `apps/web/app/(dashboard)/arbor-agents/[agentId]/bridges/page.tsx` (new)
- `apps/web/components/pact/BridgeCard.tsx` (new)
- `apps/web/components/pact/BridgeActivationDialog.tsx` (new)

**Description**: Per the spec Section 6 and T430, bridges connect agents to
external systems (CPF EZPay, MOM eCitizen, payroll ledger, leave calendar,
email/WhatsApp). The boss must explicitly activate each bridge. This page
manages bridge connections per agent.

`BridgeCard`:

- Name (plain: "CPF Submission" not "bridge_cpf_ezpay"), status badge
  (Connected / Not Connected), description, activate/disconnect button
- Shows: "What this connection allows" and "What approvals are still required"

`BridgeActivationDialog`:

- Two-step: (1) explain what the bridge does + show what agent can do with it,
  (2) confirmation with "I authorize Arbor to..." consent text
- On confirm: calls `POST /api/pact/bridges/{bridge_id}/activate` (T430)

Bridge list per agent:

- `arbor_hr`: HR calendar (leave calendar sync), communication bridge (email/WhatsApp to employees)
- `arbor_payroll`: Payroll ledger (accounting system write), CPF EZPay, banking bridge (read-only bank reconciliation)
- `arbor_compliance`: MOM eCitizen, IRAS myTax Portal, communication bridge (regulatory filing emails)

**Acceptance criteria**:

- [ ] Bridge list shown per agent with status
- [ ] Activate requires 2-step confirmation
- [ ] Disconnect shows "Are you sure?" confirmation
- [ ] Bridge description uses plain language (no technical terms)
- [ ] "What approvals are still required" shown even after bridge activated
- [ ] Integration test: activate bridge, verify CompanyBridge record created

---

### T466: Org template selection and upgrade path

**Scope**: both
**Depends**: T403, T450
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)
- `apps/web/app/(dashboard)/settings/org-template/page.tsx` (new)

**Description**: Companies can see which org template they are on
(`micro_sme`, `small_sme`, `medium_sme`) and request an upgrade. The template
determines default envelope limits and which agents are available.

`GET /api/pact/org-template`:

- Returns `{current_template, template_name, description, agent_slots, envelope_limits}`
- `agent_slots`: how many agents this template allows (micro=1, small=2, medium=3)
- `envelope_limits`: human-readable summary of key limits (financial, operational)

`POST /api/pact/org-template/upgrade`:

- Upgrades from `micro_sme` to `small_sme`, or `small_sme` to `medium_sme`
- Validates: employee count must be within new template's range
- Creates `PactAuditEvent` for template change
- Owner only

Frontend `/settings/org-template`:

- Shows current template with description
- Shows "Upgrade available" card if eligible
- Template comparison table: features per template
- "Upgrade template" button → `POST /api/pact/org-template/upgrade`

**Acceptance criteria**:

- [ ] `GET` returns correct template for company's employee count
- [ ] Upgrade from micro to small succeeds for 5-15 employee company
- [ ] Upgrade to medium fails for company with <= 15 employees (422)
- [ ] Audit event created on upgrade
- [ ] Frontend shows comparison table with agent slots highlighted
- [ ] Unit test: micro → small → medium upgrade path
