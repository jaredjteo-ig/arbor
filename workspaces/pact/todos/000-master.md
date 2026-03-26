# PACT Agent Workforce — Master Todo List

**Workspace**: pact
**Tasks**: T400–T480
**Status**: ACTIVE (all todos pending)
**Last updated**: 2026-03-21

Continues from the Arbor platform (M01-M59, T001-T398, all complete).
This roadmap covers the full PACT Agent Workforce vision as specified in
`briefs/02-agent-workforce-vision.md` and the analysis in `01-analysis/`.

Build-now boundary (gap resolution C3): Arbor builds config, models,
notifications, and acceptance tests. The gradient engine, clearance
algorithm, and EATP records wait for `pip install pact` (marked [BLOCKED]).

---

## Priority Order

1. **M61-M62** (CRITICAL) — held-action pipeline is the "make-or-break" UX
2. **M60** (CRITICAL) — foundation models required by everything else
3. **M63-M65** (HIGH) — three user-facing agents (core product)
4. **M74** (HIGH) — pricing/free tier (product cannot acquire users without it)
5. **M66-M68** (HIGH) — progressive deployment + observation pipeline
6. **M69-M70** (MEDIUM-HIGH) — agent dashboard (retention + trust)
7. **M73** (HIGH) — acceptance tests define PACT core contract
8. **M71-M72** (MEDIUM) — domain config + label mapping

---

## M60: Foundation Models and Config

**File**: `todos/active/M60-foundation.md`
**Estimated effort**: 3-4 days
**Priority**: CRITICAL

- [ ] T400: PactNode, PactEnvelope, PactAuditEvent, PactSuggestion DataFlow models
- [ ] T401: HeldAction DataFlow model + pending_reschedule leave status
- [ ] T402: pact_enabled company feature flag + pact_settings JSON
- [ ] T403: Org template config — 3 SME templates as frozen dataclasses
- [ ] T404: Agent role definitions config — 12 internal + USER_FACING_AGENTS map
- [ ] T405: Envelope template definitions — 13 templates including tmpl_consultant
- [ ] T406: HR data classification registry — MODEL_CLEARANCE_REGISTRY, EMPLOYEE_FIELD_CLEARANCE
- [ ] T407: Gradient calibration tables + local evaluator stub for tests
- [ ] T408: Bridge definitions config — 7 bridges
- [ ] T409: Singapore regulatory mapping config — 6 regulations
- [ ] T410: D/T/R auto-inference algorithm — build_pact_tree
- [ ] T411: Agent service accounts + User model is_agent / agent_role fields
- [ ] T412: PACT API router — /api/pact/enable, /api/pact/tree, /api/pact/status

---

## M61-M62: Held-Action Pipeline (CRITICAL)

**File**: `todos/active/M61-M62-notifications.md`
**Estimated effort**: 4-5 days
**Priority**: CRITICAL — identified as "make-or-break" in value proposition critique

- [ ] T413: Extend push_service.py — HELD_ACTION, DAILY_DIGEST, ESCALATION, AGENT_SUGGESTION types
- [ ] T414: Held-action notification scheduler — escalation at 48h/5d, digest at 08:00 SGT
- [ ] T415: Email channel — one-click approval HMAC tokens, HTML templates
- [ ] T416: Held-action API endpoints — list, get, resolve, summary
- [ ] T417: WhatsApp channel — wire MCP adapter, WhatsAppReplyExpectation model
- [ ] T418: Notification channel preferences API — Company model extensions
- [ ] T419: Held-action review page frontend — HeldActionCard, HeldActionBadge, /held-actions pages
- [ ] T420: "Suggest Different Dates" leave flow — backend algorithm + SuggestDatesDialog
- [ ] T421: Dashboard held-actions widget — DashboardHeldActions component
- [ ] T422: Morning briefing integration with held actions

---

## M63-M65: Agent Workforce — 3 User-Facing Agents

**File**: `todos/active/M63-M65-agent-workforce.md`
**Estimated effort**: 7-9 days
**Priority**: HIGH

### M63: Arbor HR Agent

- [ ] T423: HR Agent activation/deactivation/listing endpoints
- [ ] T424: HR Agent leave auto-approval logic — evaluate_leave_application
- [ ] T425: HR Agent attendance monitoring — check_daily_attendance, detect_lateness_pattern
- [ ] T426: HR Agent policy Q&A routing — RESTRICTED clearance, blocks salary questions
- [ ] T427: HR Agent onboarding checklist automation — initiate_onboarding, 8-item checklist
- [ ] T428: HR Agent offer screen frontend — AgentOfferCard, onboarding step 6

### M64: Arbor Payroll Agent

- [ ] T429: Payroll Agent activation + payroll_auto_prepare feature + monthly scheduling
- [ ] T430: Bridge activation service — CompanyBridge model, 3 payroll bridges
- [ ] T431: Payroll Agent offer screen + PayrollProgressStepper frontend
- [ ] T432: Payroll review and approval page

### M65: Arbor Compliance Agent

- [ ] T433: Compliance Agent work pass expiry monitoring — 60/30/7 day escalation
- [ ] T434: Compliance Agent filing deadline tracker — CPF monthly, IR8A annual
- [ ] T435: Compliance Agent regulatory update monitoring + CPF rate auto-apply
- [ ] T436: Compliance Agent frontend dashboard + ComplianceTimeline component

---

## M66-M68: Progressive Deployment

**File**: `todos/active/M66-M68-progressive-deployment.md`
**Estimated effort**: 5-7 days
**Priority**: HIGH

### M66: 24-Hour Aha Moment

- [ ] T437: Company setup wizard — 4-step onboarding
- [ ] T438: CSV/Excel employee import backend
- [ ] T439: Org chart bulk-update managers endpoint + org-chart GET
- [ ] T440: Morning briefing proactive value enhancements — work pass, probation, leave balance
- [ ] T441: Briefing push notification — morning delivery at digest_hour_sgt

### M67: Agent Offer Flow

- [ ] T442: Observation-based suggestion generator — threshold detection, PactSuggestion model
- [ ] T443: Agent offer API endpoints — list, accept, dismiss, history
- [ ] T444: Agent offer card — AgentSuggestionBanner frontend component
- [ ] T445: Trust ladder progress indicator — TrustLadder component, /arbor-agents page stub

### M68: Observation Pipeline Wiring

- [ ] T446: Client-side observation event emission — observations.ts, wire leave/payroll/compliance pages
- [ ] T447: Observation API endpoint — POST /api/pact/observations
- [ ] T448: Observation backfill from existing action logs — run on PACT enablement
- [ ] T449: Shadow agent suggestion integration — nudges.py PACT suggestion items
- [ ] T450: Setup completion tracking + PACT auto-enable for new companies

---

## M69-M70: Agent Workforce Dashboard

**File**: `todos/active/M69-M70-agent-dashboard.md`
**Estimated effort**: 5-6 days
**Priority**: MEDIUM-HIGH

### M69: Workforce View and Agent Detail

- [ ] T451: Agent workforce overview page — WorkforceOrgChart with robot badges
- [ ] T452: Agent detail panel — capabilities, activity, reliability score
- [ ] T453: Permissions adjustment screen — UI-to-PACT field mapping (gap H4)

### M70: Cost Savings and Emergency Override

- [ ] T454: Agent permissions read API — CompanyAgentPermissions model
- [ ] T455: Agent permissions write API — PATCH + history endpoint
- [ ] T456: Agent activity and reliability API — AgentActionLog model, analytics
- [ ] T457: Cost savings summary — hours saved, dollar value, CostSavingsSummary component
- [ ] T458: Emergency override — pause-all/resume-all API + EmergencyOverrideDialog
- [ ] T459: Agent status push notification — daily summary at 18:00 SGT, escalation alert

---

## M71-M72: Domain Configuration and Label Mapping

**File**: `todos/active/M71-M72-domain-configuration.md`
**Estimated effort**: 4-5 days
**Priority**: MEDIUM

### M71: Clearance Registry and Regulatory Mapping UI

- [ ] T460: Clearance registry read endpoint — model list + agent-specific view
- [ ] T461: Data access transparency page — DataAccessMatrix component
- [ ] T462: Singapore regulatory mapping display — RegulatoryCoverageTable
- [ ] T463: Consultant access — tmpl_consultant envelope activation

### M72: LLM Usage Matrix and Bridge Management

- [ ] T464: LLM usage matrix — which actions use LLM vs deterministic (gap M4)
- [ ] T465: Bridge activation and management UI — BridgeCard, BridgeActivationDialog
- [ ] T466: Org template selection and upgrade path — /settings/org-template page

---

## M73: Acceptance Tests — PACT Core Integration

**File**: `todos/active/M73-acceptance-tests.md`
**Estimated effort**: 3-4 days
**Priority**: HIGH — defines the PACT core API contract

- [ ] T467: Gradient evaluation acceptance tests — 13 scenarios across leave/payroll/claims/attendance [mostly BLOCKED]
- [ ] T468: Clearance engine acceptance tests — 9 scenarios including bridge-mediated access [BLOCKED]
- [ ] T469: Held-action pipeline acceptance tests — 9 non-blocked + 1 blocked scenario
- [ ] T470: Envelope intersection acceptance tests — 5 scenarios [BLOCKED]
- [ ] T471: Bridge integration acceptance tests — 4 not blocked + 2 blocked scenarios
- [ ] T472: Progressive activation acceptance tests — 9 scenarios, all NOT blocked
- [ ] T473: Singapore regulatory mapping acceptance tests — 8 scenarios, all NOT blocked

---

## M74: Pricing, Onboarding, and Data Governance

**File**: `todos/active/M74-pricing-onboarding.md`
**Estimated effort**: 4-5 days
**Priority**: HIGH

- [ ] T474: Subscription tier model — TIER_DEFINITIONS, check_tier, require_tier
- [ ] T475: Feature gating enforcement in API endpoints — 402 responses
- [ ] T476: Tier upgrade API and billing settings page — PricingCards, UpgradeBanner
- [ ] T477: Employee count enforcement — tier limits on create + import
- [ ] T478: Data export — PDPA portability, JSON/CSV, scoped exports
- [ ] T479: Data retention policy and deletion — anonymization, account deletion
- [ ] T480: Landing page — free tier definition, /pricing page

---

## Task Count Summary

| Milestone | Tasks          | Scope   | Blocked by pact-core            |
| --------- | -------------- | ------- | ------------------------------- |
| M60       | T400–T412 (13) | backend | T410 partially                  |
| M61-M62   | T413–T422 (10) | both    | none                            |
| M63-M65   | T423–T436 (14) | both    | none (gradient mocked)          |
| M66-M68   | T437–T450 (14) | both    | none                            |
| M69-M70   | T451–T459 (9)  | both    | none                            |
| M71-M72   | T460–T466 (7)  | both    | none                            |
| M73       | T467–T473 (7)  | backend | T467, T468, T470, parts of T471 |
| M74       | T474–T480 (7)  | both    | none                            |
| **Total** | **81 tasks**   |         | **~15 tasks fully blocked**     |

---

## Dependency Graph (Critical Path)

```
T400 (models) → T401 (HeldAction) → T413 (push types) → T414 (scheduler)
                                  → T416 (API) → T419 (frontend)
T402 (feature flag) → T412 (PACT router) → T423 (agent activation)
T403 (org templates) → T437 (setup wizard) → T450 (auto-enable)
T404 (agent roles) → T424-T427 (HR agent logic)
T405 (envelopes) → T454 (permissions API) → T453 (permissions UI)
T406 (clearance) → T460 (clearance API) → T461 (data access page)
T408 (bridges) → T430 (bridge activation) → T465 (bridge UI)
T409 (regulatory) → T433-T435 (compliance monitoring) → T462 (regulatory UI)
T411 (service accounts) → T423 (agent activation) → T456 (action log)
T442 (suggestions) → T443 (offer API) → T444 (offer banner) → T445 (trust ladder)
T446 (observation events) → T447 (observation API) → T448 (backfill)
T474 (tiers) → T475 (gates) → T476 (billing UI)
```

---

## PACT Core Dependency Register

The following tasks are waiting for `pip install pact`. When the library ships,
remove `pytest.mark.skip("[BLOCKED: pact-core]")` from each test.

| Task           | Blocked Component                                              |
| -------------- | -------------------------------------------------------------- |
| T407           | Local gradient evaluator (stub only — real evaluation blocked) |
| T410           | D/T/R auto-inference (partial — address building blocked)      |
| T467           | GradientEngine.evaluate()                                      |
| T468           | ClearanceEngine.can_access()                                   |
| T470           | EnvelopeEngine.intersect()                                     |
| T471 (partial) | ClearanceEngine bridge-mediated access, EatpBridge             |
| T469 (1 test)  | Full E2E pipeline through gradient evaluation                  |

All other tasks are buildable now without pact-core.
