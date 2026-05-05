# 000 — Master todo list

**Workspace:** obayashi (Cox 8-stage Employee Lifecycle initiative).
**Source plans:** `02-plans/01-phased-roadmap.md`, `02-plans/02-lifecycle-dashboard-spec.md`, `02-plans/03-post-redteam-plan.md`.
**Owner-locked decisions:**

- B1 deferred (will be toggled by owner separately).
- Single bundled commit per gate.
- Phase 1 ships all 12 deliverables together.
- Phase 2: L&D first, then Recognition → Goals → Exit Interview.
- Single-threaded execution.
- Deploy is scripted end-to-end.

---

## Gate 1 — Round-12 redteam closure deploy ✅ COMPLETED 2026-05-05

Shipped at `e837f7d`. Smoke probes 200; backfills applied; H2 sweep
auto-cancelled 3 stale pending leaves on prod. See
`todos/completed/G1-deploy-redteam-round-12.md` for full evidence and
the 5 deploy-script issues encountered + fixed in passing.

| ID   | Title                                       | Status                        |
| ---- | ------------------------------------------- | ----------------------------- |
| G1-1 | Run deploy/ship-redteam-round-12.sh on prod | completed                     |
| G1-2 | B1 LLM toggle (owner)                       | open — owner-side .env change |

---

## Gate 2 — Phase 1: Lifecycle dashboard (12 deliverables) ✅ COMPLETED 2026-05-05

All 12 deliverables shipped together as bundled commit. Page live at
`/strategy/lifecycle` with 8 stage cards, detail panels, D&I tile, and
activity feed. 36 P1 regression tests pin the health-pill thresholds.
See `todos/completed/P1-lifecycle-dashboard.md` for full evidence.

| ID    | Title                                            | Status |
| ----- | ------------------------------------------------ | ------ |
| P1-1  | Lifecycle dashboard aggregator endpoint          | active |
| P1-2  | /strategy/lifecycle Next.js page (4×2 card grid) | active |
| P1-3  | Per-stage detail panels                          | active |
| P1-4  | Health-pill thresholds + colour-coding           | active |
| P1-5  | D&I tile (transverse)                            | active |
| P1-6  | Activity feed (last 14 days)                     | active |
| P1-7  | ALTER TABLE: Company employer-brand fields       | active |
| P1-8  | Sidebar entry: "Strategy" above Dashboard        | active |
| P1-9  | First-time admin onboarding tour pop-over        | active |
| P1-10 | Regression tests: aggregator shape + thresholds  | active |
| P1-11 | Playwright E2E: walk all 8 stages                | active |
| P1-12 | README + docs update with screenshot             | active |

---

## Gate 3 — Phase 2: Module gaps (L&D first, then all)

L&D is the biggest gap (2/5 → 4/5 target). Then Recognition → Goals →
Exit. Each block must include FE + BE + tests + demo seed + a one-line
hook into the Gate 2 lifecycle dashboard so Strategy reflects coverage.

Estimate 25–30 dev-days. Done when avg coverage ≥ 4/5.

### L&D foundations ✅ COMPLETED 2026-05-05

| ID      | Title                                            | Status    |
| ------- | ------------------------------------------------ | --------- |
| P2-LD-1 | TrainingRecord model + CRUD endpoints            | completed |
| P2-LD-2 | Certification model with expiry tracking         | completed |
| P2-LD-3 | MandatoryTrainingRequirement model               | completed |
| P2-LD-4 | /training/records page (admin + employee views)  | completed |
| P2-LD-5 | /training/certifications page with expiry alerts | completed |
| P2-LD-6 | Mandatory-training tracker page                  | completed |
| P2-LD-7 | Demo seed: 3 records, 2 certs, 1 expiring soon   | completed |
| P2-LD-8 | Lifecycle dashboard S5 pill reads live data      | completed |
| P2-LD-9 | Regression tests pinning router + helpers        | completed |

### Recognition

| ID      | Title                                         | Status |
| ------- | --------------------------------------------- | ------ |
| P2-RC-1 | Recognition model + PeerNomination model      | active |
| P2-RC-2 | POST/GET /recognition endpoints               | active |
| P2-RC-3 | /recognition page (give kudos, see history)   | active |
| P2-RC-4 | Dashboard widget: this-month recognition feed | active |
| P2-RC-5 | Demo seed: 6 kudos across 4 employees         | active |
| P2-RC-6 | Lifecycle-dashboard hook (S6 sub-stage)       | active |
| P2-RC-7 | Regression + E2E tests                        | active |

### Goals / OKR

| ID      | Title                                              | Status |
| ------- | -------------------------------------------------- | ------ |
| P2-GO-1 | Goal + GoalCheckIn models                          | active |
| P2-GO-2 | Goal CRUD + check-in endpoints                     | active |
| P2-GO-3 | /goals page (employee + manager views)             | active |
| P2-GO-4 | Goal progress tile on appraisals page              | active |
| P2-GO-5 | Demo seed: 3 employees × 2 goals each, 4 check-ins | active |
| P2-GO-6 | Lifecycle-dashboard hook (S7 enrichment)           | active |
| P2-GO-7 | Regression + E2E tests                             | active |

### Exit interview

| ID      | Title                                              | Status |
| ------- | -------------------------------------------------- | ------ |
| P2-EX-1 | ExitInterview model                                | active |
| P2-EX-2 | Workflow: triggered on termination, sent to leaver | active |
| P2-EX-3 | Admin view: aggregated themes + sentiment          | active |
| P2-EX-4 | Demo seed: 2 completed exit interviews             | active |
| P2-EX-5 | Lifecycle-dashboard hook (S8 churn analytics)      | active |
| P2-EX-6 | Regression + E2E tests                             | active |

---

## Gate 4 — Phase 3: Strategic depth

Lower urgency. Models depend on each other (workforce plan → skills →
succession). Estimate 20–25 dev-days.

| ID   | Title                                                  | Status |
| ---- | ------------------------------------------------------ | ------ |
| P3-1 | WorkforcePlan model + Strategy hub authoring UI        | active |
| P3-2 | SkillsInventory per employee                           | active |
| P3-3 | SuccessionPlan for critical roles                      | active |
| P3-4 | Retention-risk derived view (read-only, no new PII)    | active |
| P3-5 | Pay-equity dashboard (gender / pass-type from payroll) | active |

---

## Cross-cutting (not gated)

| ID  | Title                                                       | Status |
| --- | ----------------------------------------------------------- | ------ |
| X-1 | Fix React missing-key warning in ClaimsList (NEW-2)         | active |
| X-2 | Triage 45 pre-existing test failures (out-of-scope cleanup) | active |
| X-3 | Codify round-12 patterns into security-patterns.md          | active |

---

## Status legend

- **active** — sitting in `todos/active/<id>-<slug>.md` waiting for `/implement`
- **completed** — moved to `todos/completed/<id>-<slug>.md` after evidence
- **blocked** — waiting on owner decision (annotated in the body)
