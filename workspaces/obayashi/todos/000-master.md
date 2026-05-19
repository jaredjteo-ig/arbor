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

### Recognition ✅ COMPLETED 2026-05-05

All 7 deliverables shipped under `feat(obayashi-p2-rest)` (`9243cc7`).

| ID      | Title                                         | Status    |
| ------- | --------------------------------------------- | --------- |
| P2-RC-1 | Recognition + PeerNomination models           | completed |
| P2-RC-2 | /recognition endpoints (7 routes)             | completed |
| P2-RC-3 | /recognition page (give/feed/received)        | completed |
| P2-RC-4 | Lifecycle dashboard S6 reads recognition data | completed |
| P2-RC-5 | Demo seed: 6 kudos + 2 nominations            | completed |
| P2-RC-6 | Lifecycle hook (S6 sub-stage)                 | completed |
| P2-RC-7 | Regression tests (5)                          | completed |

### Goals / OKR ✅ COMPLETED 2026-05-05

| ID      | Title                                        | Status    |
| ------- | -------------------------------------------- | --------- |
| P2-GO-1 | Goal + GoalCheckIn models                    | completed |
| P2-GO-2 | Goal CRUD + check-in endpoints               | completed |
| P2-GO-3 | /goals page (status kanban + check-in)       | completed |
| P2-GO-4 | Goal progress tile (via lifecycle dashboard) | completed |
| P2-GO-5 | Demo seed: 6 goals + 4 check-ins             | completed |
| P2-GO-6 | Lifecycle hook (S7 enrichment)               | completed |
| P2-GO-7 | Regression tests                             | completed |

### Exit interview ✅ COMPLETED 2026-05-05

| ID      | Title                                              | Status    |
| ------- | -------------------------------------------------- | --------- |
| P2-EX-1 | ExitInterview model                                | completed |
| P2-EX-2 | Workflow: trigger + tokenised /exit-survey/[token] | completed |
| P2-EX-3 | Admin view: list + aggregated themes               | completed |
| P2-EX-4 | Demo seed: 2 exit interviews (1 anon, 1 named)     | completed |
| P2-EX-5 | Lifecycle hook (S8 churn analytics)                | completed |
| P2-EX-6 | Regression tests                                   | completed |

---

## Gate 4 — Phase 3: Strategic depth ✅ COMPLETED 2026-05-05

Shipped under `feat(obayashi-p3+x)` (`7bb9dd2`). Strategy hub becomes
an authoring surface — workforce plan + skills + succession + retention
risk + pay equity all live at /strategy/\*.

| ID   | Title                                               | Status    |
| ---- | --------------------------------------------------- | --------- |
| P3-1 | WorkforcePlan model + /strategy/plan authoring UI   | completed |
| P3-2 | SkillsInventory per employee + coverage matrix      | completed |
| P3-3 | SuccessionPlan for critical roles                   | completed |
| P3-4 | Retention-risk derived view (read-only, no new PII) | completed |
| P3-5 | Pay-equity dashboard (<5-bucket anonymity collapse) | completed |

---

## Cross-cutting (not gated)

| ID  | Title                                               | Status                                                                                                    |
| --- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| X-1 | Fix React missing-key warning in ClaimsList (NEW-2) | completed (Fragment-keyed in `7bb9dd2`)                                                                   |
| X-2 | Triage 45 pre-existing test failures                | completed — 46 → 0 across 5 batches (`cf84255`, `5ddbc67`, `d662798`, `4990852`, `a63e02a`); 2503 passing |
| X-3 | Codify round-12 patterns into security-patterns.md  | completed (P18..P22 in `7bb9dd2`)                                                                         |

---

## Gate 5 — Phase 4: Audit follow-ups (May 2026)

Source audits (this session):

- `04-validate/07-buyer-audit-2026-05-08.md` — buyer/marketing lens
- `04-validate/08-functional-audit-2026-05-12.md` — daily-ops lens (3
  P0 PII/payslip bugs already shipped in commits `f1a8394` + `e9d5ffc`)
- `04-validate/09-redteam-roles-2026-05-12.md` — role-based lens

Three actionable bundles + one deferred parking lot. P4-QW unblocks
nothing else; P4-MG is real product work; P4-LP is marketing surface;
P4-XX collects intentionally-deferred items (Xero, HTTPS, multi-currency).

### P4-QW — Quick wins (1 day total) ✅ COMPLETED 2026-05-12

All 10 items shipped under the P4-QW bundle. 14 new regression tests
in `tests/regression/test_p4_qw_audit_followups.py` pin every change.

| ID       | Title                                              | Status                                           |
| -------- | -------------------------------------------------- | ------------------------------------------------ |
| P4-QW-1  | Role-aware post-login redirect                     | completed — AdminGuard silently redirects        |
| P4-QW-2  | Friendly 404 for /payroll/runs + invalid run IDs   | completed — Pydantic array no longer JSON-leaked |
| P4-QW-3  | EA Schedule 4 leave scaling                        | completed — `_ea_annual_leave_days(start, year)` |
| P4-QW-4  | Fix hospitalisation-vs-sick-leave additive framing | completed — "inclusive of" disclaimer added      |
| P4-QW-5  | Fix NRIC mask shape on My Profile                  | completed — server mask used verbatim            |
| P4-QW-6  | Hide stale onboarding card on legacy employees     | completed — empty-template cards hidden          |
| P4-QW-7  | Seed ≥1 work-pass-expiring employee                | completed — relative dates (+45d, +75d)          |
| P4-QW-8  | WICA tooltip in Cost-to-Company calculator         | completed — ResultRow accepts `tooltip` prop     |
| P4-QW-9  | Payslip PDF download button on run-detail          | completed — wired to existing BE endpoint        |
| P4-QW-10 | Compliance page inner-scroll trap                  | completed — no-fix needed (audit methodology)    |

File: `todos/completed/P4-QW-quick-wins.md`.

### P4-MG — Line-manager role + team scope (2-week sprint) ✅ COMPLETED 2026-05-13

| ID      | Title                                            | Status                                                                             |
| ------- | ------------------------------------------------ | ---------------------------------------------------------------------------------- |
| P4-MG-1 | Derive manager scope helper                      | completed — `services/manager_scope.py` + 17 unit tests                            |
| P4-MG-2 | Team approval endpoints (leave/claims/timesheet) | completed — verified live (Rajesh sees team, cross-team approve 403)               |
| P4-MG-3 | /team dashboard + sidebar entry                  | completed — `/team` live; Rajesh sees 7 reports + 4 cards + roster                 |
| P4-MG-4 | Team appraisal surface                           | completed — `/to-review` + `/manager-review` live; /team shows count               |
| P4-MG-5 | Team engagement view (manager scope)             | completed — /team card + /team/engagement detail; Q12 weakest-first with n≥5 floor |

File: `todos/active/P4-MG-manager-role.md`.

### P4-LP — Landing page & procurement surface (1 day) ✅ COMPLETED 2026-05-13

All 3 items shipped. 6 new regression tests in
`tests/regression/test_p4_lp_landing.py`. Landing app builds clean
(`next build` → 5 static pages including /pricing).

| ID      | Title                              | Status                                              |
| ------- | ---------------------------------- | --------------------------------------------------- |
| P4-LP-1 | Book-a-demo CTA + form             | completed — hero + /contact?intent=demo wired       |
| P4-LP-2 | Trust strip above the fold         | completed — 5 truthful signals, no unaudited claims |
| P4-LP-3 | Pricing transparency (tiers + CTA) | completed — /pricing with 3 tiers + FAQ + sales CTA |

File: `todos/completed/P4-LP-landing-page.md`.

### P4-XX — Explicitly deferred (owner-locked)

| ID      | Title                               | Status   |
| ------- | ----------------------------------- | -------- |
| P4-XX-1 | HTTPS + custom domain               | deferred |
| P4-XX-2 | Xero production deploy + migrations | deferred |
| P4-XX-3 | Multi-currency + multi-entity       | deferred |
| P4-XX-4 | QBO / Zoho / MYOB / Tally adapters  | deferred |
| P4-XX-5 | Xero Payroll API direct integration | deferred |

File: `todos/active/P4-XX-deferred.md`. Each item has unblock criteria.

---

## Gate 5 — Red-team round 3 (P0 security + P1 demo-credibility)

Source: `04-validate/13-redteam-comprehensive-2026-05-19.md` —
Playwright walk across 4 roles (owner / HR / line-mgr / IC) plus
codebase audit. 3 P0 + 4 P1 + 2 P2 already shipped LOCAL as
`P5-RT3`; 9 further items split into 4 active bundles below.

### P5-RT3 — Round-3 fixes ✅ COMPLETED 2026-05-19 (LOCAL)

3 P0 + 4 P1 + 2 P2 items shipped LOCAL + 1 pre-existing B11
failure resolved. 558 / 0 tests, 51 new regression tests across
6 files. TS clean. Prod deploy pending session-end.

| ID        | Title                                           | Status                                                                      |
| --------- | ----------------------------------------------- | --------------------------------------------------------------------------- |
| P5-RT3-PR | Payroll audit-log + rate-limit                  | completed — \_audit_payroll + check_rate_limit on approve/mark-paid/cancel  |
| P5-RT3-EM | Employee update audit-log + self-mutation guard | completed — \_audit_employee + \_SELF_MUTATION_BLOCKED_FIELDS + 4 endpoints |
| P5-RT3-IN | Integrations rate-limit (pre-existing B11)      | completed — xero_disconnect + xero_pick_org now call check_rate_limit       |
| P5-RT3-PB | Probation auto-transition (date + scheduler)    | completed — services/probation.py + daily tick in platform.py               |
| P5-RT3-AD | Advisory KB pre-classifier + force grounding    | completed — services/advisory_domain_classifier.py + engine pre-seed        |
| P5-RT3-RB | HR sidebar RBAC gate                            | completed — SidebarRole + canSeeNavItem; /admin + /integrations owner-only  |
| P5-RT3-HC | Headcount source-of-truth helper                | completed — services/headcount.py + 4 call sites wired                      |
| P5-RT3-GD | Goals duplicate render dedupe                   | completed — frontend dedupe by goal.id                                      |
| P5-RT3-ON | Onboarding "Completed at 0%" invariant          | completed — self-healing in \_enrich_assignment                             |

File: `todos/completed/P5-RT3-redteam-round3-fixes.md`.

### P5-PL — Polish bundle ✅ COMPLETED 2026-05-19 (LOCAL)

5 small items shipped together. 9 new regression tests in
`tests/regression/test_p5_pl_polish_bundle.py`. 567 / 0 tests, TS clean.

| ID      | Title                                      | Status                                                           |
| ------- | ------------------------------------------ | ---------------------------------------------------------------- |
| P5-PL-1 | Brand consistency Central vs Arbor         | completed — help.py + 5 dashboard pages updated                  |
| P5-PL-2 | Analytics "75% local + PR" label + tooltip | completed — analytics page card now shows compound label         |
| P5-PL-3 | Leave-type gender filter (BE + FE)         | completed — /leave/types accepts for_employee_id, filters gender |
| P5-PL-4 | My Payslips Approved-state caption         | completed — /my-payslips?include_approved=true + Clock banner    |
| P5-PL-5 | Attendance empty-state explainer           | completed — Monthly Summary self-heals stale single clock-in     |

File: `todos/completed/P5-PL-polish-bundle.md`.

### P5-AD — Advisory legacy-fallback cleanup ✅ COMPLETED 2026-05-19 (LOCAL)

Backend persistence filter + idempotent prod purge script + frontend
hide-orphans. 11 new regression tests in
`tests/regression/test_p5_ad_advisory_legacy_filter.py`. 578 / 0 tests,
TS clean. Prod DB purge must run at deploy time via
`scripts/maintenance/purge_legacy_advisory.py` (ADMIN_PASSWORD required).

| ID      | Title                                      | Status                                                                                   |
| ------- | ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| P5-AD-1 | Backend filter (short_term) + purge script | completed — `_is_legacy_fallback_reply` blocks persistence + idempotent purge script     |
| P5-AD-2 | Conversations-list cache invalidation      | completed — hook filters legacy rows; ChatContainer.onStreamError → refreshConversations |

File: `todos/completed/P5-AD-advisory-history-cleanup.md`.

### P5-VL — Value-flow handoffs ✅ COMPLETED 2026-05-19 (LOCAL)

Compliance Action Items now navigate. `/policies?template=<slug>`
auto-opens the Add Policy modal pre-populated. 10 new regression
tests in `tests/regression/test_p5_vl_value_flow_handoffs.py`. 588 / 0
tests, TS clean. Closes the gap-detect → fix-now value chain.

| ID      | Title                                               | Status                                                                                 |
| ------- | --------------------------------------------------- | -------------------------------------------------------------------------------------- |
| P5-VL-1 | Compliance Action Items render as navigable CTAs    | completed — `_FINDING_CTAS` + frontend `FINDING_CTA_MAP` + render-as-link block        |
| P5-VL-2 | /policies?template=<slug> opens modal pre-populated | completed — `/document/templates/by-slug/{slug}` + PolicyCreateModal initialDraft prop |

File: `todos/completed/P5-VL-value-flow-handoffs.md`.

### P5-DU — Demo seed via UI walkthrough ✅ COMPLETED 2026-05-19 (LOCAL)

Playwright-MCP driven pilot of seed flows + post-deploy verification.
Validates that UI-driven seeding (vs. SQL-direct) doubles as an
end-to-end smoke test, and surfaces bugs the SQL approach can't.
Seven sections piloted; six pass, one blocked by upstream Xero
deferral.

| Section         | Result     | Evidence                                                                                                                                    |
| --------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| auth-smoke      | ✅ passes  | Grace nav dropped 60 → 56 items post-deploy (Admin/Integrations gone) — P5-RT3 sidebar fix verified live                                    |
| payroll         | 🔴 blocked | P4-XX-2 Xero schema gap. **New finding**: `calculate` is also affected, not just `approve/mark-paid/cancel`                                 |
| shifts          | ✅ passes  | "Morning Shift 08:00-16:00 (8h)" template created via UI                                                                                    |
| leave-apply     | ✅ passes  | Marcus modal shows 9 leave types (no Maternity/Adoption) — P5-PL-3 verified. End-to-end: apply → owner approve → AuditLogEntry id=6 written |
| claim-submit    | ✅ passes  | Marcus creates claim id=11 → submit → owner approve. 3 hash-chained audit entries (created/submitted/approved)                              |
| attendance      | ✅ passes  | Lim Ah Kow clock-in (status=late) + clock-out, tracks_attendance gate working                                                               |
| onboarding-walk | ✅ passes  | **P5-RT3-ON self-heal verified live**: Lily Phang's "Completed at 0%" entry demoted to draft on read                                        |

File: `todos/completed/P5-DU-ui-seed-walkthrough.md`.

### P5 — Remaining red-team round-3 follow-ups

One bundle still waiting for `/implement`.

| ID    | Title                                | Effort | Source-finding ids                            |
| ----- | ------------------------------------ | ------ | --------------------------------------------- |
| P5-DM | Demo seed realism (payroll + shifts) | 2-3h   | O9, O11 (kept as fallback to P5-DU's UI path) |

File: `todos/active/P5-DM-demo-seed-realism.md`.

---

## Status legend

- **active** — sitting in `todos/active/<id>-<slug>.md` waiting for `/implement`
- **completed** — moved to `todos/completed/<id>-<slug>.md` after evidence
- **blocked** — waiting on owner decision (annotated in the body)
