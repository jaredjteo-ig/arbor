# Arbor PACT Agent Workforce — Implementation Plan

**Date**: 2026-03-21
**Status**: Approved after analysis red team convergence
**Depends on**: PACT core library (`pip install pact`) for engine; all domain config is built now.

---

## Build Principle

Following Astra's pattern: **build domain configuration now, engine integration later.**

Everything Arbor builds is configuration, models, notifications, UI, and acceptance tests. The governance engine (D/T/R address computation, envelope intersection, clearance algorithm, gradient evaluation, EATP records) comes from the PACT core library when it ships.

Nothing we build will be thrown away. It all becomes the HRIS domain layer of the PACT agent workforce platform.

---

## Phase Overview

| Phase                     | Milestones | What                                                        | Priority | Depends On |
| ------------------------- | ---------- | ----------------------------------------------------------- | -------- | ---------- |
| **1. Foundation**         | M60-M62    | PACT models, feature flag, org templates, auto-generation   | CRITICAL | Nothing    |
| **2. Held Actions**       | M63-M65    | HeldAction model, notification pipeline, approval UX        | CRITICAL | M60        |
| **3. Agent Workforce**    | M66-M68    | 3 user-facing agents, service accounts, envelope config     | HIGH     | M60, M63   |
| **4. Progressive Deploy** | M69-M70    | Morning briefings, agent offers, trust ladder               | HIGH     | M66        |
| **5. Dashboard**          | M71-M72    | Workforce view, permissions adjustment, cost savings        | HIGH     | M66        |
| **6. Domain Config**      | M73-M74    | Clearance registry, regulatory mappings, bridge definitions | MEDIUM   | M60        |
| **7. Acceptance Tests**   | M75        | Agent role-filling scenarios                                | MEDIUM   | M66, M73   |
| **8. Pricing & Landing**  | M76        | Free tier, paywall, updated landing page                    | MEDIUM   | M71        |

---

## Phase 1: Foundation (M60-M62)

**Goal**: PACT models exist in the database. Companies can have org trees auto-generated from employee data. Feature flag controls PACT activation.

**Models**:

- `PactNode` (type: D/T/R, name, parent_id, company_id, occupant_type: human/agent/shadow/vacant, occupant_id)
- `PactEnvelope` (node_id, financial_limit, operational_actions JSON, data_clearance, communication_scope, temporal_window)
- `HeldAction` (agent_role, action_type, details JSON, company_id, status, reviewer_id)
- Company gets `pact_enabled: bool` field

**Auto-generation**: When employees are added, build D/T/R tree from department + designation + reporting_manager_id. Use the micro/small/medium templates from `05-domain-configuration-spec.md`.

**Key files**: `src/hr_advisory/pact/` (new package), `src/hr_advisory/models/company_user.py` (new models)

---

## Phase 2: Held-Action Pipeline (M63-M65)

**Goal**: When an agent action hits the HELD zone, the boss gets notified and can approve/reject.

**Pipeline**: Agent action → gradient check → HELD → create HeldAction → trigger notifications → boss reviews → approve/reject → agent proceeds/stops.

**Notifications**: In-app SSE badge, push notification, WhatsApp (via existing MCP communication server), email. Channel priority configurable per company.

**Key files**: `src/hr_advisory/pact/held_actions.py`, `src/hr_advisory/api/routers/pact.py`, `apps/web/src/app/(dashboard)/held-actions/`

---

## Phase 3: Agent Workforce (M66-M68)

**Goal**: 3 user-facing agents (Arbor HR, Arbor Payroll, Arbor Compliance) can be activated per company. Each runs as a service account with RBAC role + PACT envelope.

**3 agents**:

1. **Arbor HR** — leave approval, attendance tracking, onboarding, employee queries
2. **Arbor Payroll** — CPF calculation, payslip generation, statutory filing prep, claims review
3. **Arbor Compliance** — regulatory monitoring, filing deadline alerts, compliance checks, advisory

**Service accounts**: Each agent gets a User record with role `hr_manager` (existing RBAC). PACT envelope constrains within that role. The agent acts via the shadow agent execution infrastructure (existing executor, tool registry, PACE).

**Envelope config**: 12 envelope templates from `05-domain-configuration-spec.md`. Applied when agent is activated.

---

## Phase 4: Progressive Deployment (M69-M70)

**Goal**: Arbor proactively offers agent capabilities based on observation and usage patterns.

**Morning briefings**: At 8am SGT, send boss a summary: leave balances, pending actions, compliance alerts, upcoming deadlines. This is the 24-hour aha moment.

**Agent offers**: After 7+ days of shadow observation, suggest agent activation: "You've been approving routine leave manually. Want Arbor HR to handle that?"

**Trust ladder**: Track agent reliability (actions taken, errors, human overrides). Display as a simple trust score in dashboard.

---

## Phase 5: Agent Dashboard (M71-M72)

**Goal**: Boss sees and manages the agent workforce from a single dashboard.

**Org chart**: Visual tree showing human/agent/shadow for each role.
**Agent detail**: Actions today, held actions pending, envelope summary, reliability score.
**Permissions**: Adjust envelope in plain language ("Allow claims up to $1000").
**Cost savings**: "Equivalent HR work this month: ~$8,000 saved."

---

## Phase 6: Domain Configuration (M73-M74)

**Goal**: All 77+ DataFlow models classified. Singapore regulatory mappings defined. Bridges specified.

**This is pure configuration** — Python dataclasses and YAML. No engine code.

**Files**: `src/hr_advisory/pact/config/clearance_registry.py`, `regulatory_mappings.py`, `bridge_definitions.py`, `envelope_templates.py`, `gradient_calibration.py`

---

## Phase 7: Acceptance Tests (M75)

**Goal**: Tests that prove the agent workforce works correctly when PACT core is integrated.

**Pattern**: Tests assert against the future `pact` API. They will fail until PACT core ships (expected, documented). When PACT core ships and Arbor integrates it, these tests should pass without modification.

---

## Phase 8: Pricing & Landing (M76)

**Goal**: Free tier active. Paywall gates agent activation. Landing page reflects "AI HR Department" positioning.

---

## Success Metrics

| Metric                                   | Target                | Measured By                            |
| ---------------------------------------- | --------------------- | -------------------------------------- |
| First agent activated within 14 days     | >50% of signups       | PactNode with occupant_type=agent      |
| Boss reviews held action within 24 hours | >80% of held actions  | HeldAction.reviewed_at - created_at    |
| Morning briefing open rate               | >60%                  | Notification delivery + click tracking |
| Agent reliability (0 errors/month)       | >95% of companies     | Trust score calculation                |
| Cost savings displayed                   | >$5K/month equivalent | Dashboard calculation                  |
