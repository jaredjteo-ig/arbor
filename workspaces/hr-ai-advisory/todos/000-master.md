# HR AI Advisory — Master Todo Index

**Project**: HR AI Advisory Platform (Singapore SME HR compliance)
**Last Updated**: 2026-03-14
**Total Tasks**: 108 across 12 milestones
**Status**: T001-T088 complete. T089-T108 active (UX audit findings — Milestones 10-12).

---

## How to Read This Index

- T001-T062 are **done** — completion records are in `completed/`
- T063-T088 are **done** — completion records are in `completed/`
- T089-T108 are **active** — detailed files are in `active/`
- Implement M10 first (first impressions) — M11 and M12 can proceed in parallel after M10

---

## Milestone 1: Foundation ✓

**Goal**: Infrastructure, design system, authentication, data models, and API layer in place and tested.

**Milestone file**: `active/M01-foundation.md`

| Task ID | Task Name                                             | Status | Dependencies     |
| ------- | ----------------------------------------------------- | ------ | ---------------- |
| T001    | Project scaffolding and repository structure          | done   | —                |
| T002    | Design system — shared tokens and i18n infrastructure | done   | T001             |
| T003    | Design system — base components (React)               | done   | T002             |
| T004    | Design system — base components (Flutter)             | done   | T002             |
| T005    | App shell and navigation (React)                      | done   | T003             |
| T006    | App shell and navigation (Flutter)                    | done   | T004             |
| T007    | DataFlow models — regulatory knowledge base           | done   | T001             |
| T008    | DataFlow models — company and user                    | done   | T001             |
| T009    | Nexus multi-channel API setup                         | done   | T007, T008       |
| T010    | Kaizen agent architecture — orchestration and memory  | done   | T007, T009       |
| T010A   | Kaizen agent architecture — domain specialists        | done   | T010             |
| T010B   | Kaizen agent architecture — action agents             | done   | T010A            |
| T011    | Core SDK — employee classification workflow           | done   | T007, T009       |
| T012    | Authentication and authorization                      | done   | T005, T006, T009 |
| T013    | API service layer (React + Flutter)                   | done   | T009, T012       |

---

## Milestone 2: Knowledge Base and Agent Team ✓

**Goal**: Company profile setup works. Users can ask any HR question and get accurate, cited answers. Basic templates downloadable. CPF calculator works.

**Milestone file**: `active/M02-knowledge-and-agents.md`

| Task ID | Task Name                                                                    | Status | Dependencies                        |
| ------- | ---------------------------------------------------------------------------- | ------ | ----------------------------------- |
| T014    | Knowledge base content pipeline and tooling                                  | done   | T007, T010                          |
| T015    | Knowledge base population — Employment Act (priority domain 1)               | done   | T014                                |
| T016    | Knowledge base population — CPF (priority domain 2)                          | done   | T014                                |
| T017    | Knowledge base population — Foreign Manpower (priority domain 3)             | done   | T014                                |
| T018    | Knowledge base population — TAFEP and Workplace Fairness (priority domain 4) | done   | T014                                |
| T019    | Knowledge base population — Tax, WSH, and remaining domains                  | done   | T014                                |
| T020    | Core SDK — CPF contribution calculator workflow                              | done   | T016, T011                          |
| T021    | Core SDK — foreign worker quota/levy calculator workflow                     | done   | T017, T011                          |
| T022    | Core SDK — leave entitlement calculator workflow                             | done   | T015, T011                          |
| T023    | Agent team integration testing                                               | done   | T010B, T015, T016, T017, T018, T019 |
| T024    | Onboarding flow (React web)                                                  | done   | T005, T012, T013, T010              |
| T025    | Onboarding flow (Flutter mobile)                                             | done   | T006, T012, T013, T010              |
| T026    | Advisory chat interface (React web)                                          | done   | T024, T009, T023                    |
| T027    | Advisory chat interface (Flutter mobile)                                     | done   | T025, T009, T023                    |
| T028    | Essential templates — Phase 1 bundle                                         | done   | T015, T034                          |

---

## Milestone 3: Full Advisory Platform ✓

**Goal**: Full advisory experience — all calculators, document generation, compliance health check, emergency flow, consultant multi-client support, regulatory alerts. Admin team can manage KB updates.

**Milestone file**: `active/M03-advisory-platform.md`

| Task ID | Task Name                                                | Status | Dependencies                 |
| ------- | -------------------------------------------------------- | ------ | ---------------------------- |
| T029    | Dashboard — returning user (React web)                   | done   | T026                         |
| T030    | Dashboard — returning user (Flutter mobile)              | done   | T027                         |
| T031    | Calculator hub and all calculators (React + Flutter)     | done   | T020, T021, T022, T029, T030 |
| T032    | Document template library (React web)                    | done   | T028, T029                   |
| T033    | Document template library (Flutter mobile)               | done   | T028, T030                   |
| T034    | Document generation engine and flow                      | done   | T009, T010B, T028            |
| T035    | Compliance health check (React + Flutter)                | done   | T023, T029, T030             |
| T036    | Emergency/urgent flow (React + Flutter)                  | done   | T023, T029, T030             |
| T037    | Multi-client support — consultant view (React + Flutter) | done   | T008, T029, T030             |
| T038    | Regulatory alerts system (React + Flutter)               | done   | T029, T030                   |
| T039    | Company profile and user settings (React + Flutter)      | done   | T008, T029, T030             |
| T040    | Regulatory change management pipeline                    | done   | T014, T041                   |
| T041    | Admin and operations interface                           | done   | T009, T007, T008             |
| T042    | Abuse prevention and guardrails                          | done   | T010B, T009                  |
| T043    | Singlish and natural language robustness                 | done   | T023, T026, T027             |

---

## Milestone 4: Trust, Governance and CARE/EATP ✓

**Goal**: Every piece of advice shows its source, authority level, and confidence. Full EATP audit trail. Transparent error correction. Platform learns and improves.

**Milestone file**: `active/M04-trust-and-governance.md`

| Task ID | Task Name                                         | Status | Dependencies                       |
| ------- | ------------------------------------------------- | ------ | ---------------------------------- |
| T044    | EATP trust lineage implementation                 | done   | T010B, T007, T008                  |
| T045    | Source citation and authority level system        | done   | T044, T026, T027                   |
| T046    | Risk-tiered disclaimer system                     | done   | T044, T045                         |
| T047    | Error correction and transparency process         | done   | T041, T007, T008                   |
| T048    | CARE framework governance integration             | done   | T044, T040, T046                   |
| T049    | Advisory accuracy testing framework               | done   | T044, T045, T041                   |
| T050    | Platform learning and feedback loop (COC Layer 5) | done   | T049, T040, T041                   |
| T051    | Sector-specific playbooks                         | done   | T015, T016, T017, T018, T019, T023 |
| T052    | Growth-stage triggers                             | done   | T039, T038                         |

---

## Milestone 5: Scale, Polish and Deployment ✓

**Goal**: Production-ready platform with HRIS integrations, analytics, offline mobile, push notifications, comprehensive E2E testing, security hardening, and deployment infrastructure. Ready for PSG listing.

**Milestone file**: `active/M05-scale-and-deploy.md`

| Task ID | Task Name                                     | Status | Dependencies                 |
| ------- | --------------------------------------------- | ------ | ---------------------------- |
| T053    | HRIS integration — API adapters               | done   | T008, T009                   |
| T054    | Analytics dashboard                           | done   | T029, T030, T037             |
| T055    | Offline capabilities (Flutter)                | done   | T027, T033                   |
| T056    | Push notifications (Flutter + backend)        | done   | T038, T027                   |
| T057    | Performance optimization                      | done   | T023, T035, T031             |
| T058    | Comprehensive E2E testing                     | done   | T035, T036, T037, T043, T049 |
| T059    | Security review and hardening                 | done   | T042, T044, T008             |
| T060    | Deployment configuration                      | done   | T059, T058                   |
| T061    | PSG listing preparation                       | done   | T060                         |
| T062    | Market sizing reconciliation and go-to-market | done   | T060                         |

---

---

## Milestone 6: Advisory Pipeline Architecture ✓

**Goal**: Fix the core advisory engine — KB retrieval wired, deterministic routing, conversation context propagated, trust layer live, proper error signalling. Without this milestone, the KB exists but does not influence advice.

| Task ID | Task Name                                                        | Status | Dependencies     |
| ------- | ---------------------------------------------------------------- | ------ | ---------------- |
| T063    | Replace OrchestratorAgent with deterministic DispatchRouter      | done   | —                |
| T064    | Wire KB retrieval into specialist dispatch path (CRITICAL)       | done   | T063             |
| T065    | Wire conversation history through full pipeline                  | done   | T063, T064       |
| T066    | Wire company context enrichment through full pipeline            | done   | T063, T064       |
| T067    | Wire ComplianceAgent as mandatory post-specialist quality gate   | done   | T063, T064       |
| T068    | Create PDPAAgent specialist                                      | done   | T063, T064       |
| T069    | Wire anti-amnesia injection and EATP trust lineage into pipeline | done   | T063, T064, T065 |
| T070    | Fix error handling to escalate uncertainty instead of suppress   | done   | T063             |

---

## Milestone 7: Specialist Prompt Optimization ✓

**Goal**: Each agent reasons with expert-grade scaffolding. Common mistakes are explicitly guarded against. Responses are structured and actionable.

| Task ID | Task Name                                                                  | Status | Dependencies |
| ------- | -------------------------------------------------------------------------- | ------ | ------------ |
| T071    | Enhance QueryAnalyzer with intent detection and few-shot examples          | done   | T063         |
| T072    | Add reasoning scaffolding to EmploymentActAgent                            | done   | T064         |
| T073    | Add reasoning scaffolding to CPFAgent                                      | done   | T064         |
| T074    | Add reasoning scaffolding to ForeignManpowerAgent                          | done   | T064         |
| T075    | Add reasoning scaffolding to FairEmployment, Tax, and WSH agents           | done   | T064         |
| T076    | Enhance ResponseSynthesizer with structured output and conflict resolution | done   | T067, T070   |
| T077    | Add QueryClarifier pre-classification stage                                | done   | T071         |

---

## Milestone 8: Quality Rubric and Adversarial Testing ✓

**Goal**: Every response is measurable. 64 adversarial scenarios pass. KB gaps filled. Citation validation live.

| Task ID | Task Name                                                 | Status | Dependencies          |
| ------- | --------------------------------------------------------- | ------ | --------------------- |
| T078    | Implement automated quality rubric scoring system         | done   | T076                  |
| T079    | Expand adversarial test suite to 64+ scenarios            | done   | T078                  |
| T080    | Run adversarial scenarios and iterate prompt improvements | done   | T072-T076, T078, T079 |
| T081    | Wire citation validator to DB-backed provision registry   | done   | T064                  |
| T082    | Add missing KB content for adversarial scenario gaps      | done   | T064, T079            |

---

## Milestone 9: Human QA Workflow ✓

**Goal**: Continuous improvement loop. Reviewers score conversations. Patterns detected. Patches proposed, tested, and deployed with automated regression guard.

| Task ID | Task Name                                                     | Status | Dependencies           |
| ------- | ------------------------------------------------------------- | ------ | ---------------------- |
| T083    | QA data models and API endpoints                              | done   | T078                   |
| T084    | QA Sessions tab in Admin page (frontend)                      | done   | T083                   |
| T085    | Conversation browser and evaluation form (frontend)           | done   | T083, T084             |
| T086    | Feedback-to-improvement pipeline (backend)                    | done   | T083, T078             |
| T087    | Automated test and rollback for instruction patches (backend) | done   | T083, T078, T079, T086 |
| T088    | QA metrics dashboard (frontend)                               | done   | T083, T084, T085, T087 |

---

## Milestone 10: Demo-Ready First Impressions (ACTIVE)

**Goal**: A new user lands on AITE and immediately sees value — not emptiness. Fix the greeting, redesign the empty dashboard state, wire the post-signup onboarding flow, add value proposition to auth pages, remove hardcoded data, and restructure navigation.

| Task ID | Task Name                                      | Status | Priority | Dependencies     |
| ------- | ---------------------------------------------- | ------ | -------- | ---------------- |
| T089    | Fix broken greeting and dashboard empty state  | active | HIGH     | T029             |
| T090    | Wire onboarding flow to post-signup            | active | HIGH     | T024, T089       |
| T091    | Split-screen auth pages with value proposition | active | HIGH     | T012             |
| T092    | Remove hardcoded data and seed demo state      | active | HIGH     | T029, T038, T089 |
| T093    | Reduce and group sidebar navigation            | active | MEDIUM   | T005, T039       |

---

## Milestone 11: AI Trust and Safety (ACTIVE)

**Goal**: The AI advisory interface earns user trust through transparency, verifiability, and proper safety patterns. Citations are clickable, authority is accurate, confidence is meaningful, and escalation actually works.

| Task ID | Task Name                                      | Status | Priority | Dependencies     |
| ------- | ---------------------------------------------- | ------ | -------- | ---------------- |
| T094    | Add legal disclaimer to advisory page          | active | HIGH     | T026, T046       |
| T095    | Make citations clickable with provision viewer | active | HIGH     | T045, T064, T081 |
| T096    | Fix authority level mapping                    | active | HIGH     | T045, T064, T081 |
| T097    | Add markdown rendering for AI responses        | active | HIGH     | T026, T076       |
| T098    | Add stop-generation button and reasoning trace | active | MEDIUM   | T026, T065       |
| T099    | Implement escalation flow                      | active | HIGH     | T036, T046, T070 |
| T100    | Fix confidence display and add caveats         | active | HIGH     | T046, T076, T096 |
| T101    | Wire conversation history loading              | active | HIGH     | T026, T065       |

---

## Milestone 12: Enterprise Polish (ACTIVE)

**Goal**: Professional-grade quality that an HR Director would present to their C-suite. Typography consistency, accessibility compliance, expandable chat input, search, audit trail, contextual AI entry points, and resilient error handling.

| Task ID | Task Name                                   | Status | Priority | Dependencies           |
| ------- | ------------------------------------------- | ------ | -------- | ---------------------- |
| T102    | Enforce typography scale from design tokens | active | MEDIUM   | T002, T003             |
| T103    | Fix accessibility issues                    | active | HIGH     | T003, T036             |
| T104    | Upgrade chat input to expandable textarea   | active | MEDIUM   | T026, T093             |
| T105    | Add page transitions and search results     | active | LOW      | T005, T093             |
| T106    | Add user query audit trail                  | active | MEDIUM   | T026, T065, T044       |
| T107    | Contextual AI entry points                  | active | MEDIUM   | T035, T031, T036, T026 |
| T108    | Error handling and resilience               | active | HIGH     | T026, T098             |

---

## Red Team Findings Addressed

All 14 red team findings have been addressed:

| Finding | Description                     | Addressed In              |
| ------- | ------------------------------- | ------------------------- |
| R2-GAP1 | Anti-amnesia mechanism          | T044 (EATP lineage)       |
| R2-GAP2 | KB search in citation system    | T045 (citation validator) |
| R2-GAP3 | Verification gradient depth     | T046 (disclaimers)        |
| R2-GAP4 | COC Layer 5 learning            | T050 (learning pipeline)  |
| R2-GAP5 | Expert validation workflow      | T048 (CARE governance)    |
| R2-GAP6 | Genesis record trust anchor     | T044 (EATP lineage)       |
| R2-REC2 | Citation pre-delivery guardrail | T045 (citation validator) |
| R2-REC3 | Constraint envelope testing     | T044 (EATP lineage)       |
| M1      | Open platform + associations    | T062 (go-to-market)       |
| M3      | Employment Hero monitoring      | T062 (go-to-market)       |
| S6      | Market sizing reconciliation    | T062 (go-to-market)       |

---

## Summary

### Completed (T001-T088)

- **88/88 tasks complete** across 9 milestones
- Full-stack implementation: Python backend + React web + Flutter mobile
- 6 regulatory domains covered with 33+ provisions in KB
- 3 deterministic calculators (CPF, leave, quota/levy)
- Trust infrastructure: EATP lineage, citations, disclaimers, error correction
- CARE governance: human-on-the-loop, dual plane model, expert validation
- Production deployment: Docker, PostgreSQL+pgvector, Redis, SSE streaming
- Security: PDPA compliance, input validation, rate limiting, security headers
- Advisory pipeline: 14-step safety chain with SSE streaming, deterministic routing, KB retrieval
- Quality system: 64-scenario adversarial suite, automated rubric, human QA workflow
- Persistent AI advisory panel: site-wide side panel accessible from every dashboard page

### Active (T089-T108) — UX Audit Findings

- **20 tasks active** across 3 new milestones (M10-M12)
- M10 (5 tasks): First impressions — greeting, empty state, onboarding routing, auth pages, nav restructure
- M11 (8 tasks): AI trust — disclaimers, clickable citations, authority fix, markdown, stop button, escalation, confidence, history
- M12 (7 tasks): Enterprise polish — typography, accessibility, textarea, search, audit trail, contextual AI, error handling
- Recommended implementation order: M10 in full first, then M11 and M12 in parallel
