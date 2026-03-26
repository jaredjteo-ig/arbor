# Red Team Analysis: PACT Package Gaps, Contradictions, and Missing Pieces

**Date**: 2026-03-21
**Analyst**: deep-analyst (red team mode)
**Scope**: All PACT analysis documents (04-08), user flows (01, 02, 06), brief (02), Astra reference (04)
**Complexity Score**: 27/30 (Complex) -- Governance: 9, Legal: 9, Strategic: 9

---

## Executive Summary

The PACT analysis package is thorough on vision and domain configuration but has seven structural gaps that would block or delay implementation. The most critical: there is no migration path from Arbor's existing 4-role flat RBAC to the 12-envelope PACT model, the held-action notification pipeline (identified as "make-or-break" in 08) is absent from user flows, and the pricing contradiction between 04 and 08 is unresolved. Additionally, the documents oscillate between Astra's "build config, import engine later" pattern and assuming PACT engine capabilities that do not exist, creating ambiguity about what developers should build now.

---

## 1. CRITICAL Gaps (Block Implementation)

### C1. No Migration Path from Existing RBAC to PACT Envelopes

**Source**: 05-domain-configuration-spec.md (Section 2, all 12 agents), existing codebase (`src/hr_advisory/models/company_user.py` lines 20-24)

**The gap**: Arbor today has 4 roles: `owner`, `hr_manager`, `consultant`, `employee`. Every endpoint checks `require_role(["owner", "hr_manager"])` or similar. The PACT vision requires 12 envelope templates with 5-dimensional constraints, per-field data classification, and a verification gradient engine that intercepts every action.

There is zero code bridging these two worlds. The analysis documents describe the target state (envelope YAML, gradient tables, clearance registries) but never address:

- How existing endpoints transition from `require_role()` to envelope evaluation
- Whether the 4 existing roles map to specific templates (owner -> tmpl_owner, hr_manager -> tmpl_hr_manager, employee -> tmpl_employee_office, consultant -> ???)
- What happens during the transition period when some endpoints are envelope-governed and others are RBAC-governed
- Whether existing data (120+ endpoints, 77+ models) needs a migration to add clearance metadata

**Why it blocks**: A developer picking up 05 would not know whether to modify `auth_middleware.py` to check envelopes, create a new middleware layer, or build an adapter between RBAC and PACT. Without this, implementation cannot start.

**How to close**: Write a `10-migration-strategy.md` document that specifies:

1. Phase 1: RBAC remains, envelope config stored but not enforced (shadow mode)
2. Phase 2: Envelope checks run in parallel with RBAC, log mismatches
3. Phase 3: Envelope enforcement replaces RBAC for specific endpoints
4. The exact mapping of existing roles to PACT templates
5. The middleware architecture (new `pact_middleware.py` that wraps or replaces `auth_middleware.py`)

---

### C2. Held-Action Notification Pipeline Is Undefined

**Source**: 08-value-proposition-critique.md (Section 5: "The held action UX is the make-or-break feature and it is under-designed"), 03-user-flows/01-boss-onboarding.md (Step 8: push notification shown but not specified)

**The gap**: File 08 explicitly identifies four channels (morning briefing, nudges, shadow chat, push notification) and concludes that push notifications and WhatsApp are "not optional." The user flows in 01 and 02 show push notifications in their wireframes (e.g., "Arbor: Sarah Lim wants 3 days leave next week. I need your input.") But there is no specification for:

- What triggers a push notification vs. an in-app nudge vs. an email
- The notification payload schema for held actions (distinct from the existing `NotificationType` enum which covers only regulatory/compliance alerts)
- Escalation logic (day 1 nudge, day 3 reminder, day 5 "Sarah is still waiting" -- mentioned in 01's failure table but not specified)
- Batch vs. immediate delivery rules
- WhatsApp integration flow (the MCP adapter exists at `src/hr_advisory/mcp_servers/adapters/whatsapp.py` but is not connected to held actions)

The existing push service (`src/hr_advisory/notifications/push_service.py`) handles 5 notification types: `REGULATORY_UPDATE`, `DEADLINE_REMINDER`, `COMPLIANCE_ALERT`, `CORRECTION_NOTICE`, `SYSTEM_ANNOUNCEMENT`. None of these is `HELD_ACTION` or `APPROVAL_REQUEST`. The entire held-action concept has no code representation.

**Why it blocks**: The user flows depend on push notifications for held actions. Without them, the boss never learns about pending approvals unless they open the app. File 08 states this clearly: "If held actions depend on the boss opening the app, they will be ignored."

**How to close**: Add a `held-action-notification-spec.md` to user flows or plans that defines:

1. New notification types: `HELD_ACTION_APPROVAL`, `HELD_ACTION_REMINDER`, `HELD_ACTION_ESCALATION`
2. Trigger rules: which gradient zones generate which notification type
3. Escalation timeline with configurable intervals
4. Channel priority: push first, email fallback, WhatsApp opt-in
5. Batch digest rules for low-urgency held actions

---

### C3. No "Build Now" vs. "Build When Engine Ships" Boundary

**Source**: 05-domain-configuration-spec.md (header: "When PACT core ships, Arbor feeds its configuration"), 04-strategic-repositioning.md (Section 9.2: "All three platforms consume the same PACT core engine (when built by the care/pact team)"), Astra reference 04-what-we-build-now.md

**The gap**: Astra's document is explicit and clean about what to build now: "Everything we build is configuration and domain knowledge -- not governance engine code." It then lists a phased build order (A through G) with clear deliverables, all of which are data structures and configuration files.

Arbor's 05 follows this pattern in principle but breaks it in practice. The acceptance tests in Section 8 reference `gradient_engine.evaluate()`, `access_engine.can_access()`, and `bridge_engine.can_cross()` -- none of which exist. The user flows (01, 02, 06) describe real-time envelope enforcement, gradient evaluation, and observation recording as if they are buildable now.

This creates confusion: should a developer implement `gradient_engine.evaluate()` as a stub that reads the YAML config? Or wait for the PACT core team? Or build a minimal local enforcement layer?

Astra's document answers this clearly: "Nothing we build will be thrown away. It all becomes the domain layer." Arbor's documents do not draw this line.

**Why it blocks**: Without a clear "build now" list, developers will either build too much (reimplementing what the PACT core team should provide) or too little (only writing YAML that cannot be tested or demonstrated).

**How to close**: Add a section to 05 (or create a separate document) that mirrors Astra's format:

| What                               | Build Now?     | Deliverable                                      | Notes                                         |
| ---------------------------------- | -------------- | ------------------------------------------------ | --------------------------------------------- |
| Org templates (Section 1)          | Yes            | Python dataclass + YAML                          | Config only                                   |
| Agent role definitions (Section 2) | Yes            | YAML capability specs                            | Config only                                   |
| Data classification (Section 3)    | Yes            | Python dict                                      | Config only                                   |
| Envelope templates (Section 4)     | Yes            | YAML + dataclass                                 | Config only                                   |
| Gradient calibration (Section 5)   | Yes (tables)   | Python dict                                      | Config only; enforcement requires PACT core   |
| Bridge definitions (Section 6)     | Yes            | YAML + dataclass                                 | Config only                                   |
| Regulatory mapping (Section 7)     | Yes            | Python dict                                      | Config only                                   |
| Acceptance tests (Section 8)       | Yes (as specs) | `pytest.mark.skip` until engine ships            | Executable specifications                     |
| `gradient_engine.evaluate()`       | NO             | Wait for PACT core                               | Engine code                                   |
| `access_engine.can_access()`       | NO             | Wait for PACT core                               | Engine code                                   |
| `build_pact_tree()`                | PARTIAL        | Build the inference algorithm; enforcement waits | Tree builder is config; enforcement is engine |

---

### C4. The "Aha in 24 Hours" Finding Is Not Reflected in User Flows

**Source**: 08-value-proposition-critique.md (Section 6: "The aha moment must happen in the first session"), 06-progressive-deployment-story.md (Week 1-2 before any agent action), 01-boss-onboarding.md (Step 6-7: agent activates but then says "It will start by watching for a few days")

**The gap**: File 08 lays out a specific aha sequence: register, add employees, see org chart, agent explains capabilities, next morning the agent has already handled a leave request. The critique says: "That sequence -- setup to first autonomous action in 24 hours -- is the aha moment."

But the user flows contradict this. Flow 01, Step 6 says the agent "will start by watching how things work for a few days." Step 7 (next day morning briefing) shows: "HR Agent status: Observing -- learning how your team works. I'll start handling routine tasks after a few days."

This is the exact slow-trust pattern that File 08 criticized as taking too long. The user flows were likely written before or in parallel with the critique, and the critique's findings were not backported.

**Why it blocks**: If the user flows are the implementation spec, developers will build the slow-trust model. The critique says this model loses customers. The two documents give contradictory direction on the single most important UX decision.

**How to close**: Revise Flow 01 to incorporate the 24-hour aha moment. Specifically:

1. After Step 6 (agent activation), the agent should immediately handle any pending self-service actions (leave balance queries, policy questions) instead of "observing"
2. Step 7 (morning briefing) should show at least one action the agent took autonomously, even if it is low-stakes (e.g., "Ahmad's 1-day MC was auto-approved per your company's medical leave policy")
3. The observation period before suggestions can remain, but the agent should perform read-only and auto-approvable actions from day 1

---

## 2. HIGH Gaps (Cause Confusion or Significant Risk)

### H1. Agent Role Count Inconsistency Between Documents

**Source**: 05-domain-configuration-spec.md (Section 2: 12 agent roles), 02-agent-workforce-vision.md (brief), 04-strategic-repositioning.md (Section 2.2: "HR Manager, Payroll Officer, Leave Administrator, Attendance Tracker, Claims Processor, and Compliance Monitor" -- 6 roles), 01-boss-onboarding.md (Step 6: offers a single "HR Agent")

**The gap**: The documents cannot agree on how many agents exist and how they are presented to the user:

- 05 defines 12 distinct agent roles (HR Manager, Payroll, Leave Admin, Attendance, Claims, Compliance, Recruitment, Onboarding, Advisory, Reports, Document, Shadow)
- 04 mentions 6 agent roles in Section 2.2
- The brief (02) mentions "12 HRIS agent role definitions"
- User flow 01 presents a single "HR Agent" to the boss
- User flow 06 shows 3 agents at month 6 (HR Agent, Payroll Agent, Compliance Agent)

The user flow 01 approach (single "HR Agent" that encompasses leave, attendance, claims, HR questions) is fundamentally different from 05's approach (12 separate agents with separate envelopes). If the HR Agent is actually a composite of Leave Admin + Attendance + Claims + HR Manager, then what are its envelope constraints? It cannot have the Leave Admin's RESTRICTED clearance AND the Claims Agent's $200 financial authority in a single envelope without a composition model.

**Why it causes confusion**: A developer implementing Flow 01's "HR Agent" would build one agent with one envelope. A developer implementing 05's spec would build 12 separate agents. These are architecturally different. The user-facing simplification (one "HR Agent") needs a formal mapping to the 12 internal agents.

**How to close**: Add a "User-Facing Agent Mapping" section to 05 that specifies:

- User sees: "HR Agent" -- internally this is Leave Admin + Attendance + Claims + HR Manager composite
- User sees: "Payroll Agent" -- internally this is Payroll Agent + Document Agent composite (for payslip generation)
- User sees: "Compliance Agent" -- internally this is Compliance Agent + Advisory Agent composite
- Define how composite envelopes work (union of capabilities? intersection of constraints? most restrictive clearance?)

---

### H2. Pricing Contradiction Between Market Sizing and Value Critique

**Source**: 04-strategic-repositioning.md (Section 4: TAM $670M at $200/month), 08-value-proposition-critique.md (Section 4: "$200/month is the most expensive option by a factor of 2-3x"; Section 10: "Introduce tiered pricing -- $50/month for basic HRIS, $200/month for AI HR department")

**The gap**: File 04 calculates TAM as 280K x $200 x 12 = $670M, and SOM Year 1 at 500 companies x $200 x 12 = $1.2M. File 08 then demolishes the $200 price point: HReasily is $2/employee, Talenox has a free tier, and at $200/month for a 5-person company the cost is $40/employee -- "Talenox's free tier wins on pure arithmetic."

File 08 suggests tiered pricing ($50 basic + $200 AI) and three other alternatives (free tier, usage-based, value-story). But 04's entire market sizing and financial model assumes flat $200. Neither document reconciles this.

More importantly, the user flows in 01 show a landing page that says "It's Free" (`[Get Started - It's Free]`) and "Join 200+ Singapore SMEs who replaced their HR spreadsheets with Arbor." This implies a free tier exists. But no document defines what is free vs. paid.

**Why it causes confusion**: Product, marketing, and engineering decisions depend on the pricing model. If there is a free tier, the architecture needs usage limits, upgrade prompts, and feature gating. If it is flat $200, the onboarding flow should not say "It's Free." The market sizing numbers in 04 cannot be used for investor conversations if the pricing is wrong.

**How to close**: Create a pricing decision document that resolves:

1. Is there a free tier? If so, what is included?
2. What is the paid tier pricing? Flat or per-employee?
3. Recompute market sizing with the chosen model
4. Update Flow 01's landing page copy to match the pricing decision
5. Specify what features are gated (agent capabilities? number of agents? LLM usage?)

---

### H3. Envelope Templates Do Not Match Between Agents and Roles

**Source**: 05-domain-configuration-spec.md (Section 2.1: HR Manager Agent envelope has `financial.max_per_action: 0`), 05-domain-configuration-spec.md (Section 4.2: tmpl_hr_manager has `financial.max_per_action: 500`)

**The gap**: There are TWO sets of envelope definitions in 05, and they conflict:

1. **Agent role definitions** (Section 2, 12 agents): Each agent has an `envelope:` block defining its constraints. Example: HR Manager Agent has `financial.max_per_action: 0`.

2. **Envelope templates** (Section 4, 12 templates): Each template defines constraints for a human or agent in that role. Example: `tmpl_hr_manager` has `financial.max_per_action: 500`.

When Ah Mei (human) fills the HR Manager role, she gets `tmpl_hr_manager` with $500 financial authority. When the HR Manager Agent fills the same role, it gets the agent envelope with $0 financial authority. This makes sense conceptually (agents are more restricted than humans in the same role) but the document never explains this relationship. A developer would not know which envelope applies or whether they stack.

Additional conflicts:

- Agent HR Manager has `data_access.max_clearance: restricted`, but `tmpl_hr_manager` has `data_access.max_classification: confidential`. Does the agent HR Manager see confidential data or not?
- Agent Payroll has `temporal.operating_hours: 24/7`, but `tmpl_payroll_officer` has `temporal.operating_hours: Mon-Fri 09:00-18:00`. Which applies when the agent fills the payroll officer role?

**Why it causes confusion**: The two envelope systems create ambiguity about which constraints apply in which context. This is a governance design issue, not just a documentation issue -- the wrong answer could give an agent too much or too little authority.

**How to close**: Add a "Template vs. Agent Envelope" section to 05 that specifies:

1. Human in role: template applies directly
2. Agent in role: template is the ceiling; agent envelope is a further restriction within the template
3. Resolution rule: for each dimension, take the MORE restrictive of (template, agent envelope)
4. Explicitly reconcile the conflicts listed above

---

### H4. PACT Vocabulary Leaks Into User Flows

**Source**: 08-value-proposition-critique.md (Section 9: "If the boss ever sees the word 'envelope' or 'clearance' or 'gradient,' the product has failed at its own design constraint"), 01-boss-onboarding.md, 02-payroll-agent-activation.md, 06-agent-workforce-dashboard.md

**The gap**: File 08 insists on zero PACT vocabulary in user-facing materials. Flow 06 does an excellent job of this (Section 9 explicitly lists what is hidden). But the user flows are inconsistent:

Vocabulary leaks found:

- Flow 01, Step 6 behind-the-scenes: mentions "EATP Delegation Record" and "PactAuditEvent" in text that is framed as developer notes but mixed with user-facing wireframes. The document format does not clearly separate "what the user sees" from "what happens behind the scenes."
- Flow 02, Step 8: "What Ahmad just agreed to is a gradient shift in PACT terms" -- this is an explanatory note, but the heading says "The Gradient Shift" which could be confused with user-facing text.
- Flow 06, Step 5: "Monotonic tightening validated" appears in behind-the-scenes text. While this is technically not user-facing, a developer implementing this screen might accidentally expose the term.

More importantly, the "Adjust Permissions" screen in Flow 06 Step 5 shows a simplified interface but does not define the mapping from simplified labels to PACT concepts. When Ahmad changes "Auto-approve claims up to: [$200]" to $500, which PACT field changes? Is it `financial.approval_threshold`? `financial.max_per_action`? `financial.flagging_threshold`? The envelope templates in 05 use different field names than the user-facing labels.

**Why it causes confusion**: Frontend developers need an explicit mapping from UI labels to PACT field names. Without it, the "Adjust Permissions" screen cannot be implemented correctly.

**How to close**: Create a "UI Label to PACT Field Mapping" reference table covering every user-adjustable setting shown in the flows. Example:

| UI Label                    | PACT Field                              | Agent        | Notes                          |
| --------------------------- | --------------------------------------- | ------------ | ------------------------------ |
| "Auto-approve claims up to" | `envelope.financial.flagging_threshold` | agent_claims | Below this: auto. Above: held. |
| "Max approval per action"   | `envelope.financial.max_per_action`     | agent_claims | Hard ceiling                   |
| "Daily cumulative limit"    | `envelope.financial.daily_cumulative`   | agent_claims | Resets at midnight SGT         |

---

### H5. Shadow Agent Observation Pipeline Is Still Not Wired

**Source**: 08-value-proposition-critique.md (Section 6: "Observation pipeline is not wired"), VALUE_AUDIT_REPORT_2026-03-21.md (Issue 4), 06-progressive-deployment-story.md (relies on shadow agent pattern detection throughout)

**The gap**: The entire progressive trust model depends on the shadow agent observing user actions and building behavioral baselines. The progressive deployment story (06) references these observations at every stage:

- Week 1: "Shadow agent begins silent observation"
- Week 2: "The shadow agent has accumulated 7 days of observation"
- Month 4-5: "the shadow agent has high-confidence patterns" with specific confidence scores

But the project memory and the VALUE_AUDIT_REPORT both confirm: "observation pipeline not wired (client -> server)." The shadow agent's `observation.py` exists but the client-to-server pipeline (user actions on pages being sent to the observation store) is not connected.

This is not a PACT-specific gap -- it is a pre-existing platform gap. But the entire PACT progressive trust model is built on top of it. Without observation data, there are no patterns. Without patterns, there are no suggestions. Without suggestions, envelope widening never happens. The progressive deployment story collapses to "boss manually configures everything" -- which is the opposite of the vision.

**Why it causes confusion**: The user flows read as if observation is working. A product manager approving these flows would assume the feature exists. It does not. Every timeline in the progressive deployment story is fictional without this infrastructure.

**How to close**:

1. Flag the observation pipeline as a prerequisite for PACT user flows (not a parallel workstream)
2. Define the minimum observation events needed: page visits, action types, approval latency, data access patterns
3. Estimate implementation effort (the VALUE_AUDIT_REPORT estimates 8-16 hours)
4. Update the progressive deployment story to note which stages require observation and which can work without it (e.g., template assignment works without observation; suggestion generation does not)

---

### H6. No Specification for the D/T/R Auto-Inference Algorithm

**Source**: 05-domain-configuration-spec.md (Section 1.4: template selection algorithm), 01-boss-onboarding.md (Step 4b: "PACT `build_pact_tree(company_id)` runs"), 05 Section 1 references "02-auto-inference-algorithms.md"

**The gap**: The domain config spec references a document `02-auto-inference-algorithms.md` in Section 1.4 ("The D/T/R inference algorithm (02-auto-inference-algorithms.md) customizes it based on actual employee data"). This document does not exist in the analysis directory.

The user flow (01, Step 4b) shows the expected output of `build_pact_tree()` -- a complete D/T/R tree with departments, teams, and reporting lines inferred from CSV data. But the algorithm for this inference is not specified:

- How are departments detected? From the "Department" column? What if it is missing?
- How are team boundaries inferred? From reporting lines? What if there are 8 people reporting to one manager -- does it create sub-teams?
- How is the template selected per person? By designation matching against `tmpl_*.matches.designations`? What happens when a designation does not match any template (e.g., "Office Cleaner")?
- What happens when the CSV has no "Reports To" column? Does the tree flatten?
- How are D (Division), T (Team), and R (Role) nodes distinguished? The current Employee model has `department` and `reporting_manager_id` but no concept of teams as distinct from departments.

**Why it causes confusion**: The org tree auto-generation is the first "invisible magic" the user experiences. If it is wrong (e.g., all 12 employees in one flat department), the org chart in Flow 01 Step 5 will be unimpressive. The inference algorithm is load-bearing for the entire onboarding experience.

**How to close**: Write the referenced `02-auto-inference-algorithms.md` with:

1. Input: employee list with (name, department, designation, reporting_manager_id)
2. Algorithm: how to detect D, T, and R nodes
3. Fallback: what happens when data is incomplete
4. Template matching: exact algorithm for designation -> template assignment, including the fallback template for unmatched designations (presumably `tmpl_employee_office`)
5. Test cases: the Ahmad Logistics example from Flow 01 as a worked example

---

## 3. MEDIUM Gaps (Improvements)

### M1. No "Consultant" Role in PACT Templates

**Source**: 05-domain-configuration-spec.md (Section 4: 12 envelope templates), existing codebase (UserRole includes `CONSULTANT`)

**The gap**: The existing Arbor RBAC has 4 roles: owner, hr_manager, consultant, employee. The PACT envelope templates define 12 templates, none of which is for a consultant. File 07 (platform model) discusses consultants and accountants as channel partners who manage multiple SME clients. But there is no template for their access level.

A consultant managing 50 client companies needs cross-company access (view multiple companies), restricted per-company (cannot see all data in any one company), and a specific functional scope (payroll processing, compliance reports). This does not map to any of the 12 templates.

**How to close**: Add `tmpl_consultant` and `tmpl_accountant` templates to 05, or specify that consultants use `tmpl_hr_manager` with cross-company scope restrictions.

---

### M2. Compliance Agent as Separate Agent vs. HR Agent Capability

**Source**: 05-domain-configuration-spec.md (Section 2.6: Compliance Agent is separate with id `agent_compliance`), 06-agent-workforce-dashboard.md (Step 2: "The Compliance Agent does not appear as a separate node because it is a capability of the HR Agent")

**The gap**: The domain config defines Compliance Agent as a standalone agent with its own envelope, tools, and activation stage (month_2). But user flow 06 says it "shares the HR Agent's position" in the PACT tree and only appears separately in performance metrics. These are contradictory architectures.

If compliance is part of the HR Agent, then the HR Agent's envelope must include compliance capabilities (regulatory monitoring, filing deadline tracking, work pass alerts). But the HR Agent's envelope in Section 2.1 does not include these capabilities. If compliance is separate, it needs its own node in the tree, which contradicts Flow 06.

**How to close**: Decide whether compliance is a distinct agent or a capability bundle within the HR Agent, and reconcile the affected documents. The cleaner architecture is probably a distinct agent that the user flow presents as part of the "HR Agent" composite (see H1).

---

### M3. The "12 Employees" Data Mismatch in User Flows

**Source**: 01-boss-onboarding.md (persona: "12 employees", CSV has 11 rows, Step 4b preview says "I found 11 employees"), 02-payroll-agent-activation.md (Step 1: "salary data for 12 employees", payroll summary shows 11 employees in the table)

**The gap**: Ahmad has "12 employees" (from persona description) but the CSV upload shows 11 employees (Ahmad himself is already in the system as employee #12, so 11 + Ahmad = 12 total). This is probably intentional but:

- Flow 02 Step 3 says "Pulled salary data for 12 employees" but the payslip table shows 11 rows (no entry for Ahmad). This is correct if Ahmad does not receive a payslip from himself, but it should be stated.
- The payroll summary shows "Total gross: $38,400" for 11 employees in Flow 02, but Flow 06 shows "$39,800" for September with "12 employees." Was an employee added between these flows? Jenny Tan is mentioned in Flow 06 Step 4 as a "new employee" -- but the headcount should then be 13, not 12.

**How to close**: Normalize the employee count and payroll totals across all three user flows. Create a canonical employee roster for Ahmad Logistics that all flows reference.

---

### M4. LLM Cost Model Not Reconciled with Agent Architecture

**Source**: 04-strategic-repositioning.md (Section 10, Decision Point 3: "Which agent roles require LLM and which are purely deterministic?"), 08-value-proposition-critique.md (Section 2: "500 queries per month is tight"), 05-domain-configuration-spec.md (Section 2.9: Advisory Agent uses LLM; all others unspecified)

**The gap**: The BYOK decision (project memory) sets a $5/month default LLM cap. The domain config spec defines 12 agents but only explicitly states which ones use LLM for the Advisory Agent ("LLM usage: ZERO" for Payroll, unspecified for the other 10).

Agents that likely require LLM:

- Advisory Agent (confirmed)
- Shadow Agent (intent classification, pattern detection, suggestion generation)
- Compliance Agent (regulatory interpretation, "monitor regulatory updates")
- Recruitment Agent (candidate screening, "check fair consideration framework")
- HR Manager Agent (answer HR policy questions -- unless this is rule-based)
- Onboarding Agent (generate welcome materials -- unless templated)

If 6 of 12 agents use LLM, the $5/month cap is woefully insufficient. The shadow agent alone uses LLM for intent classification on every user interaction.

**How to close**: Add an "LLM Usage Matrix" to the domain config that specifies for each agent: deterministic (zero LLM), LLM-optional (can fall back to rules), or LLM-required. Then recompute the cost model per agent and per company size.

---

### M5. No Specification for the "Suggest Alternative Dates" Flow

**Source**: 01-boss-onboarding.md (Step 8: "Suggest Different Dates" option), 08-value-proposition-critique.md (Section 10: "The suggest alternative dates flow -- not implemented")

**The gap**: Flow 01 shows a polished "Suggest Alternative Dates" interface that finds weeks with better team coverage and lets Ahmad send a counter-proposal to Sarah. This requires:

- Team schedule awareness (query attendance/leave for all employees in Sarah's team for multiple weeks)
- Date optimization (find the nearest dates with full coverage)
- Status management (new leave application status: `pending_reschedule`)
- Employee notification and response flow

File 08 lists this as "not implemented." The Leave module endpoints (`src/hr_advisory/api/routers/leave.py`) have no `pending_reschedule` status or date suggestion logic.

**How to close**: Either simplify the flow (replace "Suggest Different Dates" with a free-text message to the employee) or specify the date suggestion algorithm and add `pending_reschedule` to the leave state machine.

---

### M6. Data Export and Retention Not Addressed

**Source**: 08-value-proposition-critique.md (Section 8: "Data export -- Not mentioned in any document"), 04-strategic-repositioning.md (Section 7.5: "No vendor lock-in")

**The gap**: The strategic positioning promises "no vendor lock-in" and "data and governance structure are portable." File 08 flags that no export endpoint exists. The generic export MCP adapter exists (`src/hr_advisory/mcp_servers/adapters/generic_export.py`) but this is an MCP tool, not a user-facing bulk export feature.

For an open-source Foundation project, data portability is not just a feature -- it is a principle. The Foundation's independence rules require that users can leave at any time.

**How to close**: Add data export to the implementation roadmap. Minimum: CSV export for all major modules (employees, payroll history, leave records, attendance, claims). PACT tree export (JSON) for governance portability.

---

### M7. The "Free" Landing Page vs. Undefined Pricing

**Source**: 01-boss-onboarding.md (Step 1: landing page says "Get Started - It's Free" and "Sign Up Free"), all other documents reference $200/month pricing

**The gap**: The landing page wireframe prominently features "Free" as the entry point. But no document defines:

- What is free?
- Is there a trial period?
- When does payment start?
- What happens when the trial ends?

This is not just a marketing question. It affects:

- Database schema (subscription model, billing fields)
- Feature gating logic
- Agent activation limits (can free users activate all 12 agents?)
- LLM usage caps

**How to close**: Resolve as part of the pricing decision (see H2). If the landing page says "Free," there must be a free tier. Define what it includes.

---

### M8. No Error or Unhappy Path Specifications

**Source**: All user flows (01, 02, 06)

**The gap**: The user flows show the happy path beautifully. Flow 01 has a failure table (Section "Failure Points and Mitigations"), which is good. But the flows themselves never show what Ahmad sees when things go wrong:

- What if the CSV upload fails (wrong format, missing columns)?
- What if the payroll calculation has an error (not the OT correction scenario, but a system error)?
- What if the push notification fails to deliver and Ahmad misses a held action for 7 days?
- What if Ahmad rejects a shadow agent suggestion -- what is the UI?
- What if Ahmad wants to undo an agent's auto-approved action?

File 08 specifically flags undo as a problem: "The PACE undo window is 8 seconds. For a boss who checks once a day, an 8-second undo window is meaningless." No flow addresses the reversal UX.

**How to close**: Add at least one unhappy-path variant to each user flow. Specifically: CSV import failure, payroll error, missed held action, and undo/reversal.

---

## 4. Cross-Reference Audit

### Documents Checked for Consistency

| Document                             | Internally Consistent               | Consistent with Others                         | Issues     |
| ------------------------------------ | ----------------------------------- | ---------------------------------------------- | ---------- |
| 04-strategic-repositioning.md        | Yes                                 | Pricing conflicts with 08                      | H2         |
| 05-domain-configuration-spec.md      | Envelope conflicts (H3)             | Agent count conflicts with flows (H1)          | H1, H3, H6 |
| 06-progressive-deployment-story.md   | Yes                                 | Assumes observation pipeline exists (H5)       | H5, C4     |
| 07-platform-model-analysis.md        | Yes                                 | Pricing assumes $200 flat (H2)                 | H2         |
| 08-value-proposition-critique.md     | Yes                                 | Findings not reflected in flows (C4)           | C4         |
| 01-boss-onboarding.md                | Employee count inconsistency (M3)   | PACT vocab leaks (H4), "Free" undefined (M7)   | H4, M3, M7 |
| 02-payroll-agent-activation.md       | Employee count mismatch (M3)        | Consistent with 05 envelope definitions        | M3         |
| 06-agent-workforce-dashboard.md      | Compliance Agent contradiction (M2) | Consistent with progressive trust model        | M2         |
| 02-agent-workforce-vision.md (brief) | Yes                                 | Consistent with 04 and 05                      | None       |
| Astra 04-what-we-build-now.md        | Exemplary                           | Arbor does not follow its pattern cleanly (C3) | C3         |

### Key Cross-Document Conflicts

1. **Agent count**: 05 says 12, 04 says 6, Flow 01 presents 1, Flow 06 shows 3. All of these can be reconciled but the reconciliation is not documented (H1).

2. **Envelope values**: Agent envelopes in Section 2 vs. role templates in Section 4 of 05 give different values for the same role (H3).

3. **Timeline**: 08 says "aha in 24 hours," flows say "observing for a few days" (C4).

4. **Pricing**: 04 says $200 flat, 08 says tiered, Flow 01 says "Free" (H2, M7).

5. **Compliance Agent architecture**: 05 says standalone agent, Flow 06 says part of HR Agent (M2).

---

## 5. Decision Points Requiring Resolution

Before implementation can proceed, these decisions need stakeholder input:

1. **What can Arbor build without PACT core?** Define the explicit "build now" list following Astra's pattern. (C3)

2. **How does the RBAC-to-PACT migration work?** Define the phased approach. (C1)

3. **What is the pricing model?** Free tier? Flat $200? Tiered? Per-employee? This affects architecture. (H2, M7)

4. **Is the aha moment 24 hours or 2 weeks?** The flows and the critique disagree. Resolve this and update the affected flows. (C4)

5. **How are 12 internal agents presented as 3-4 user-facing agents?** Define the composition model. (H1)

6. **Which envelope applies when an agent fills a human role?** Template ceiling with agent restrictions, or agent envelope overrides template? (H3)

7. **Is the observation pipeline a prerequisite or a parallel workstream?** The progressive trust model depends on it. (H5)

---

## 6. Risk Register

| #   | Risk                                  | Severity | Likelihood | Impact                             | Mitigation                             |
| --- | ------------------------------------- | -------- | ---------- | ---------------------------------- | -------------------------------------- |
| C1  | No RBAC-to-PACT migration path        | CRITICAL | Certain    | Blocks all implementation          | Write migration strategy document      |
| C2  | Held-action notifications undefined   | CRITICAL | Certain    | Boss never sees pending approvals  | Spec the notification pipeline         |
| C3  | Build-now boundary unclear            | CRITICAL | High       | Developers build wrong things      | Mirror Astra's build-order table       |
| C4  | 24hr aha not in flows                 | CRITICAL | High       | Slow onboarding loses customers    | Revise Flow 01                         |
| H1  | Agent count inconsistency             | HIGH     | Certain    | Architecture confusion             | Define composition model               |
| H2  | Pricing unresolved                    | HIGH     | Certain    | Market sizing invalid              | Pricing decision document              |
| H3  | Envelope conflicts                    | HIGH     | Certain    | Wrong access control               | Reconcile agent vs. template envelopes |
| H4  | PACT vocabulary in flows              | HIGH     | Medium     | Frontend exposes jargon            | UI-to-PACT field mapping table         |
| H5  | Observation pipeline unwired          | HIGH     | Certain    | Progressive trust impossible       | Flag as prerequisite                   |
| H6  | Auto-inference algorithm missing      | HIGH     | Certain    | Onboarding org chart fails         | Write the algorithm spec               |
| M1  | No consultant template                | MEDIUM   | High       | Channel partner access broken      | Add tmpl_consultant                    |
| M2  | Compliance Agent architecture unclear | MEDIUM   | High       | Duplicate or missing functionality | Decide standalone vs. composite        |
| M3  | Employee count mismatch               | MEDIUM   | Certain    | Flows look inconsistent            | Normalize canonical roster             |
| M4  | LLM cost model incomplete             | MEDIUM   | High       | Costs exceed revenue               | LLM usage matrix per agent             |
| M5  | Suggest-dates flow unspecified        | MEDIUM   | Medium     | Feature cannot be built            | Simplify or specify algorithm          |
| M6  | No data export                        | MEDIUM   | Certain    | Violates Foundation principles     | Add to implementation roadmap          |
| M7  | "Free" landing page undefined         | MEDIUM   | Certain    | Marketing-architecture mismatch    | Resolve with pricing decision          |
| M8  | No unhappy-path flows                 | MEDIUM   | Certain    | Error UX not designed              | Add failure variants to flows          |

---

## 7. Summary of Required Actions

### Immediate (Before Implementation Starts)

1. **Write migration strategy** (C1) -- RBAC to PACT phased approach
2. **Write held-action notification spec** (C2) -- The make-or-break feature
3. **Create build-now vs. build-later table** (C3) -- Follow Astra's pattern exactly
4. **Revise Flow 01** for 24-hour aha moment (C4) -- Agent acts on day 1, not after observation period

### Before First Sprint

5. **Define agent composition model** (H1) -- How 12 internal agents map to 3-4 user-facing agents
6. **Resolve pricing** (H2, M7) -- Affects database schema, feature gating, and market positioning
7. **Reconcile envelope conflicts** (H3) -- Template vs. agent envelope resolution rules
8. **Write auto-inference algorithm** (H6) -- The `02-auto-inference-algorithms.md` that 05 references

### During Implementation

9. **Wire observation pipeline** (H5) -- Prerequisite for progressive trust
10. **Create UI-to-PACT mapping** (H4) -- Prerequisite for frontend development
11. **Add unhappy-path flows** (M8) -- Error UX for key scenarios
12. **Add data export** (M6) -- Foundation principle compliance
