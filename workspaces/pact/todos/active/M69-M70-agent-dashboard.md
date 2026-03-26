# M69-M70: Agent Workforce Dashboard

**Milestone**: M69 (workforce view + agent detail), M70 (permissions + cost savings + override)
**Priority**: MEDIUM-HIGH — required for boss to understand and trust the agent workforce
**Scope**: frontend (mostly), backend (permissions API)
**Estimated effort**: 5-6 days

Per user flow 06 (agent-workforce-dashboard), at Month 6 the boss sees an
org chart with human and robot icons. They can inspect what each agent does,
adjust its permissions, see cost savings, and trigger emergency override.
This is the transparency layer that builds long-term trust.

Gap H4 (UI-to-PACT field mapping): the permissions adjustment screen must
translate PACT envelope dimensions into plain-language toggles that a
non-technical boss can understand.

---

## M69: Workforce View and Agent Detail

### T451: Agent workforce overview page

**Scope**: frontend
**Depends**: T423, T439
**Files**:

- `apps/web/app/(dashboard)/arbor-agents/page.tsx` (modify — was stub in T445)
- `apps/web/components/pact/WorkforceOrgChart.tsx` (new)
- `apps/web/components/pact/AgentListItem.tsx` (new)

**Description**: The "Your AI HR Team" dashboard showing both human employees
and active agents in an org chart view. Per user flow 06 Step 2.

`WorkforceOrgChart`:

- Renders the same org chart as `GET /api/employees/org-chart` (T439)
- Employees shown as circular avatars (photo or initials)
- Agent service accounts shown with a distinct robot icon badge
  (`is_agent=True` flag from T439)
- Clicking an agent node opens `AgentDetailPanel` (T452)
- Clicking an employee node opens existing employee detail
- Show reliability percentage on agent node (derived from action history: T456)

`AgentListItem`:

- Compact list representation for when org chart is too large
- Agent name + icon, current status (active/paused/inactive),
  actions today, reliability percentage
- Toggle to active/paused inline (calls `POST /api/pact/agents/{id}/pause`)

`/arbor-agents` page updates:

- Remove stub content from T445
- Add tab bar: "Org Chart" / "Agent List"
- Org Chart tab: `WorkforceOrgChart`
- Agent List tab: list of `AgentListItem` for all configured agents
- `TrustLadder` component from T445 retained at top

**Acceptance criteria**:

- [ ] Agents appear with robot badge in org chart
- [ ] Employees appear as regular avatars
- [ ] Clicking agent opens detail panel
- [ ] Agent list shows status and reliability
- [ ] Inline pause toggle calls correct API endpoint
- [ ] Tab switching works on mobile

---

### T452: Agent detail panel / page

**Scope**: frontend
**Depends**: T456, T423
**Files**:

- `apps/web/components/pact/AgentDetailPanel.tsx` (new)
- `apps/web/app/(dashboard)/arbor-agents/[agentId]/page.tsx` (new)

**Description**: Full detail view for a single agent. Per user flow 06 Step 3.
Uses plain language throughout — no PACT vocabulary.

Layout sections:

1. **Header**: Agent name + icon, status badge (Active / Paused), activate/
   pause button, "Adjust permissions" link (to T453)

2. **What it does** — plain-language capability list:
   - `arbor_hr`: "Approves routine leave requests", "Monitors attendance",
     "Answers HR policy questions", "Guides new employee onboarding"
   - `arbor_payroll`: "Prepares monthly payroll for your review",
     "Tracks CPF submission deadlines", "Processes expense claims"
   - `arbor_compliance`: "Monitors work pass expiry dates",
     "Tracks government filing deadlines", "Alerts on regulatory changes"

3. **What it cannot do** — hard limits in plain language:
   - "Cannot terminate employees"
   - "Cannot change salaries"
   - "Cannot access bank accounts directly" (bridges require your approval)
   - "Cannot send documents externally without your review"

4. **Recent activity** — last 10 actions from `GET /api/pact/agents/{id}/actions`
   - Each action: timestamp, description, outcome (completed/held/escalated)

5. **Reliability score** — circular progress showing percentage of actions
   completed without escalation. "Arbor HR resolved 94% of tasks this month."

6. **Held actions** — count of currently pending held actions for this agent.
   "1 item needs your input" → links to `/held-actions?agent={id}`

Data source: `GET /api/pact/agents/{id}/detail` (T456)

**Acceptance criteria**:

- [ ] All 4 sections rendered for each of 3 agents
- [ ] "What it cannot do" list is always shown (not conditional)
- [ ] Recent activity shows last 10 actions with timestamps
- [ ] Reliability score matches calculation from T456
- [ ] Held actions count badge links to filtered held-actions list
- [ ] "Adjust permissions" link navigates to T453

---

### T453: Permissions adjustment screen

**Scope**: frontend
**Depends**: T454, T455
**Files**:

- `apps/web/app/(dashboard)/arbor-agents/[agentId]/permissions/page.tsx` (new)
- `apps/web/components/pact/PermissionsToggle.tsx` (new)
- `apps/web/components/pact/PermissionsSection.tsx` (new)

**Description**: The permissions adjustment screen from user flow 06 Step 4.
This is the resolution for gap H4 (UI-to-PACT field mapping). Each toggle
maps to a PACT envelope dimension change — but the boss sees plain-language
descriptions, not envelope syntax.

UI-to-PACT mapping (from gap resolution H4 and spec Section 4):

**Financial controls** (maps to `OperationalConstraints.financial_limit`):

- "Handle leave requests up to {N} days" → toggle + number input
- "Process expense claims up to ${N}" → toggle + number input
- "Prepare payroll without approval" → toggle (maps to bridge_payroll_ledger)

**Escalation controls** (maps to gradient zones):

- "Always ask me before approving overtime" → toggle
- "Always ask me before hiring decisions" → toggle (always ON, not removable)
- "Ask me if a claim seems unusual" → toggle

**Data access controls** (maps to `DataAccessConstraints.clearance_level`):

- "Can view employee salaries" → toggle
- "Can view bank account details" → toggle (off by default)
- "Can see medical certificate content" → toggle

**Communication controls** (maps to `CommunicationConstraints`):

- "Can reply to employee questions on my behalf" → toggle
- "Can send documents to MOM directly" → toggle (bridge_mom_ecitizen)
- "Can submit CPF on my behalf" → toggle (bridge_cpf_ezpay)

Each toggle: shows current state, description of what enabling/disabling
means, risk level badge (LOW/MEDIUM — no HIGH toggles exposed in UI,
HIGH changes require contacting support).

`PermissionsToggle`: single toggle with label, description, risk badge.
`PermissionsSection`: grouped section with header and list of toggles.

On toggle change → calls `PATCH /api/pact/agents/{id}/permissions` (T455).

**Acceptance criteria**:

- [ ] All toggles shown with plain-language descriptions
- [ ] Financial limits show number inputs when enabled
- [ ] "Always ask me before hiring decisions" is always ON and disabled
      (cannot be turned off in UI)
- [ ] Each toggle change calls permissions PATCH endpoint
- [ ] Risk badge shown for each toggle
- [ ] Mobile-friendly: toggles are tappable at 44px minimum

---

## M70: Cost Savings and Emergency Override

### T454: Agent permissions read API

**Scope**: backend
**Depends**: T405, T423
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)

**Description**: Read the current effective permissions for an agent in a
company, translated to the UI-friendly format (not raw PACT envelope syntax).

`GET /api/pact/agents/{agent_id}/permissions`:

- Returns `{sections: [{name, toggles: [{key, label, enabled, risk_level}]}]}`
- Maps envelope template values to boolean toggles
- Falls back to template defaults if no company-specific overrides
- Owner only

`CompanyAgentPermissions` DataFlow model:

- `company_id`, `agent_id`, `overrides: JSON`
- JSON stores delta from template defaults: `{financial_limit: 5000, can_view_salary: false}`
- Created on first permission edit; read-only until then (use template defaults)

**Acceptance criteria**:

- [ ] Returns default template values for a company that has never edited permissions
- [ ] Returns company overrides merged over defaults after editing
- [ ] All UI toggle keys from T453 are present in response
- [ ] Owner-only access enforced
- [ ] Unit test: merge template defaults with company overrides

---

### T455: Agent permissions write API

**Scope**: backend
**Depends**: T454
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)

**Description**: Update agent permissions. Writes to `CompanyAgentPermissions`
overrides. Creates a `PactAuditEvent` for each change.

`PATCH /api/pact/agents/{agent_id}/permissions`:

- Body: `{key: str, value: bool | int}`
- Validates: key must be in known toggle set
- Validates: cannot disable "always_ask_hiring" (hard constraint)
- Validates: financial limit must be > 0 and <= 100000
- Creates `PactAuditEvent` with `{agent_id, key, old_value, new_value, changed_by, changed_at}`
- Returns updated full permissions object (same shape as GET)

`GET /api/pact/agents/{agent_id}/permissions/history`:

- Returns `PactAuditEvent` records for permissions changes
- Last 50 changes, ordered most recent first
- Owner only

**Acceptance criteria**:

- [ ] PATCH updates the specific key in company overrides
- [ ] Attempting to disable "always_ask_hiring" returns 422
- [ ] Financial limit < 1 returns 422
- [ ] PactAuditEvent created for every change
- [ ] Permissions history returns chronological audit trail
- [ ] Integration test: change permission, verify audit event created

---

### T456: Agent activity and reliability API

**Scope**: backend
**Depends**: T423, T416
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)
- `src/hr_advisory/pact/analytics.py` (new)

**Description**: Track and expose agent action history and reliability metrics.

`AgentActionLog` DataFlow model:

- `company_id`, `agent_id`, `action_type`, `action_description` (plain text),
  `outcome` (completed/held/escalated/failed), `held_action_id nullable`,
  `created_at`

Record to `AgentActionLog` when:

- An agent completes an auto-approved action (T424, T425, T427, T429, T433, T434)
- A held action is created (link `held_action_id`)
- A held action is resolved (update outcome to `completed`)

`analytics.py`:

`calculate_reliability(company_id: int, agent_id: str, days: int = 30) -> float`:

- `reliability = (completed_without_escalation / total_actions) * 100`
- Returns 100.0 if no actions yet (new agent is considered reliable)

`GET /api/pact/agents/{agent_id}/actions`:

- Returns last 20 `AgentActionLog` records for the company + agent
- Includes `action_description`, `outcome`, `created_at`, `held_action_id`
- Owner only

`GET /api/pact/agents/{agent_id}/detail`:

- Aggregates: `{agent_id, status, reliability_30d, actions_today, held_count, recent_actions}`
- `held_count` = pending held actions linked to this agent
- Owner only

**Acceptance criteria**:

- [ ] AgentActionLog record created for every agent action (auto + held)
- [ ] `calculate_reliability` returns 100.0 for new agent (no actions)
- [ ] `calculate_reliability` returns correct percentage after mixed outcomes
- [ ] Actions endpoint returns 20 most recent actions
- [ ] Detail endpoint aggregates reliability, actions today, held count
- [ ] Unit test: 10 completed + 2 escalated = 83.3% reliability

---

### T457: Cost savings summary

**Scope**: both
**Depends**: T456
**Files**:

- `src/hr_advisory/pact/analytics.py` (extend)
- `src/hr_advisory/api/routers/pact.py` (extend)
- `apps/web/components/pact/CostSavingsSummary.tsx` (new)
- `apps/web/app/(dashboard)/arbor-agents/page.tsx` (modify)

**Description**: Per user flow 06 Step 5 and per the value critique, the
comparison must be "time saved" not "vs competitor pricing."

Backend `calculate_cost_savings(company_id: int) -> dict`:

- Hours saved: each completed agent action assigned a baseline time estimate
  - leave approval: 8 minutes
  - payroll preparation: 4 hours per run
  - compliance check: 15 minutes per item
  - onboarding task: 20 minutes per task
- Monthly hours saved = sum of baseline times for completed actions in last 30 days
- Dollar value: `hours_saved * 50` (SGD $50/hour default, configurable)
- Returns `{hours_saved_month: float, dollar_value_month: float, actions_count: int}`

`GET /api/pact/cost-savings`:

- Returns `calculate_cost_savings` result
- Owner only

`CostSavingsSummary` component:

- Three metric cards: "Hours saved this month", "Equivalent value", "Tasks completed"
- Tagline: "Arbor handled {N} tasks this month, saving you approximately
  {H} hours ({$V} in HR time)."
- Time range selector: this month / last 3 months / all time

**Acceptance criteria**:

- [ ] Hours saved calculated from AgentActionLog baseline times
- [ ] Dollar value = hours \* $50
- [ ] Returns zero for company with no agent actions (not null)
- [ ] Cost savings widget shown on arbor-agents page
- [ ] Time range selector changes API call parameters
- [ ] Unit test: 5 leave approvals + 1 payroll run = correct hours

---

### T458: Emergency override (pause all agents)

**Scope**: both
**Depends**: T423
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)
- `apps/web/components/pact/EmergencyOverrideDialog.tsx` (new)
- `apps/web/app/(dashboard)/arbor-agents/page.tsx` (modify)

**Description**: Per user flow 06 Step 6. The boss can pause all agents
immediately. This is a trust safety valve — the boss must always feel in control.

Backend `POST /api/pact/agents/pause-all`:

- Sets `agent_activation.status = paused` for ALL active agents in the company
- Creates `PactAuditEvent` with reason: `emergency_pause_all`
- Creates a held action of type `agent_pause_confirmation` with:
  - action_display: "All Arbor agents paused"
  - action_context: "You paused all agents. Pending tasks have been held."
  - options: [{key: "resume", label: "Resume agents"}, {key: "keep_paused", label: "Keep paused"}]
- Returns `{paused_agents: [list of agent_ids]}`

`POST /api/pact/agents/resume-all`:

- Resumes all paused agents
- Clears pause-confirmation held action
- Owner only

`EmergencyOverrideDialog`:

- Triggered by "Pause everything" button on `/arbor-agents` page
- Confirmation step: "This will pause all agents. Any pending tasks will
  require your manual review. Continue?"
- Two large buttons: "Yes, pause agents" / "Cancel"
- After pause: shows "Agents paused. You can resume anytime."
- Calls `POST /api/pact/agents/pause-all`

**Acceptance criteria**:

- [ ] Pause-all sets all active agents to paused status
- [ ] PactAuditEvent created with emergency_pause_all reason
- [ ] Confirmation dialog shown before pause (no accidental tap)
- [ ] "Pause everything" button always visible on /arbor-agents page
- [ ] Resume-all reactivates all paused agents
- [ ] Integration test: pause all, verify all agents status=paused

---

### T459: Agent status push notification to boss

**Scope**: backend
**Depends**: T413, T456
**Files**:

- `src/hr_advisory/notifications/push_service.py` (extend)
- `src/hr_advisory/pact/notifications/scheduler.py` (extend)

**Description**: When an agent completes a significant batch of tasks (end of
day summary) or encounters an unexpected escalation rate, notify the boss.

`send_agent_daily_summary(company_id: int, agent_id: str) -> bool`:

- Called at 18:00 SGT for each company with active agents
- Only sends if agent completed >= 3 actions today
- Notification:
  - title: "Arbor HR handled {N} tasks today"
  - body: "All routine. {M} items waiting for your review." (or "All done.")
  - data: `{type: "agent_summary", agent_id}`
- Uses `AGENT_SUGGESTION` notification type from T413

`send_high_escalation_alert(company_id: int, agent_id: str, escalation_rate: float)`:

- Triggered when escalation_rate > 50% in last 7 days (agent struggling)
- Notification: "Arbor HR escalated more items than usual this week.
  You may want to review its permissions."
- Fires at most once per 7 days per agent

**Acceptance criteria**:

- [ ] Daily summary sent at 18:00 SGT when >= 3 actions completed
- [ ] No summary sent on days with 0-2 actions
- [ ] High escalation alert fires when escalation rate > 50%
- [ ] High escalation alert fires at most once per 7 days
- [ ] Unit test: scheduler at 18:00 triggers summary for correct companies
