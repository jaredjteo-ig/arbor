# 01 — Phased Roadmap

Three phases, each with a demo-able checkpoint. Phase 1 is mostly
**visualisation of existing data** (cheap + high visual impact). Phase 2
**closes the largest module gaps** (L&D, Recognition, Goals, Exit
Interview). Phase 3 is **strategic-depth** (skills inventory, succession,
retention scoring).

After each phase the platform tells a more complete lifecycle story —
each phase is independently shippable and demo-able.

---

## Phase 1 — Wrap existing capability in lifecycle narrative

**Goal:** Buyer demo can walk all 8 stages via the lifecycle dashboard
(card grid, not a wheel graphic) and click through to each underlying
module without hitting a "feature not built" wall.

**Effort:** ~10–12 dev-days (1–2 weeks with parallel agents).

**Demo-able checkpoint:** owner logs in → lands on `/dashboard/lifecycle`
→ sees the 8-stage card grid each with green/amber/red health pill →
clicks "Recruit" → sees stage-detail panel with KPIs → clicks deeper
to the existing `/recruitment` module.

### Phase 1 deliverables

| ID    | Item                                                        | Files                                                         | Effort |
| ----- | ----------------------------------------------------------- | ------------------------------------------------------------- | ------ |
| P1-1  | Lifecycle dashboard page (8-stage card grid + health pills) | `apps/web/src/app/(dashboard)/lifecycle/page.tsx` (new)       | M      |
| P1-2  | `/strategy/lifecycle-dashboard` aggregation endpoint        | `src/hr_advisory/api/routers/strategy.py` (new)               | S      |
| P1-3  | Per-stage health computation                                | Same as P1-2                                                  | S      |
| P1-4  | Stage detail panels (8 inline cards)                        | Same as P1-1                                                  | M      |
| P1-5  | Sidebar nav entry "Lifecycle"                               | `apps/web/src/components/shell/NavigationSidebar.tsx`         | S      |
| P1-6  | D&I snapshot panel (existing-fields-only)                   | `apps/web/src/app/(dashboard)/diversity/page.tsx` (new)       | M      |
| P1-7  | Pay-equity tile (S6-G4)                                     | aggregation in P1-2                                           | S      |
| P1-8  | Source-funnel chart (S3-G2)                                 | aggregation in P1-2                                           | S      |
| P1-9  | Onboarding-completion-by-demographic widget (S4-G4)         | aggregation in P1-2                                           | S      |
| P1-10 | Churn dashboard (S8-G2)                                     | aggregation in P1-2                                           | S      |
| P1-11 | Employer-brand fields on Company (S2-G1)                    | `models/company_user.py`, `routers/profile.py`, settings page | S      |
| P1-12 | Reusable `StageGrid.tsx` component (8-stage card grid)      | `apps/web/src/components/lifecycle/StageGrid.tsx` (new)       | M      |

**Phase 1 ships:**

- Visual lifecycle narrative.
- D&I dashboard from existing fields only.
- Employer-brand polish (Attract).
- 4 new aggregation views (source funnel, onboarding completion, pay
  equity, churn) — all read-only, no schema changes.

**Phase 1 schema changes:**

- 1 ALTER TABLE to add employer-brand fields on `companies`. Nothing else.

---

## Phase 2 — Close the biggest module gaps

**Goal:** L&D, Recognition, Goals, Exit Interview move from absent /
primitive to first-class modules.

**Effort:** ~25–30 dev-days (3–4 weeks with parallel agents).

**Demo-able checkpoint:** Owner can log a training event for an
employee → see it in their L&D ledger → flag a certification with an
expiry → get an automated reminder 30 days before. Manager can give
peer kudos → see them on the recognition wall. Employee can set
quarterly goals → check progress weekly. On RESIGNED event, an exit
interview is auto-scheduled and completed feedback shows up on the
churn dashboard.

### Phase 2 deliverables

#### L&D module (S5-G1, G2, G6) — biggest impact

| ID   | Item                                        | Files                                                     | Effort |
| ---- | ------------------------------------------- | --------------------------------------------------------- | ------ |
| P2-1 | `TrainingRecord` model                      | `models/company_user.py`                                  | S      |
| P2-2 | `Certification` model with expiry           | `models/company_user.py`                                  | S      |
| P2-3 | Training records router (CRUD)              | `routers/training.py` (new)                               | M      |
| P2-4 | `/training` admin page (list, log new)      | `apps/web/src/app/(dashboard)/training/page.tsx`          | M      |
| P2-5 | `/my-training` employee page                | `apps/web/src/app/(dashboard)/my-training/page.tsx` (new) | S      |
| P2-6 | Cert-expiry cron (30/60/90-day reminders)   | `scripts/cert_expiry_reminders.py` (new) + crontab line   | S      |
| P2-7 | Mandatory-training tracker (WSH compliance) | flag on `TrainingRecord`, dashboard widget                | S      |
| P2-8 | L&D KPI on lifecycle dashboard health badge | aggregation in `routers/strategy.py`                      | XS     |

#### Recognition module (S6-G1, G2)

| ID    | Item                                      | Files                                                     | Effort |
| ----- | ----------------------------------------- | --------------------------------------------------------- | ------ |
| P2-9  | `Recognition` model                       | `models/company_user.py`                                  | S      |
| P2-10 | Recognition router (give kudos, list)     | `routers/recognition.py` (new)                            | M      |
| P2-11 | Recognition wall page                     | `apps/web/src/app/(dashboard)/recognition/page.tsx` (new) | M      |
| P2-12 | "Give kudos" widget on employee profile   | `apps/web/src/app/(dashboard)/employees/[id]/page.tsx`    | S      |
| P2-13 | Recognition KPI on lifecycle health badge | aggregation in `routers/strategy.py`                      | XS     |

#### Goals / OKRs (S7-G1)

| ID    | Item                                                 | Files                                                  | Effort |
| ----- | ---------------------------------------------------- | ------------------------------------------------------ | ------ |
| P2-14 | `Goal` model (with parent_goal_id for OKR cascading) | `models/company_user.py`                               | S      |
| P2-15 | Goals router                                         | `routers/goals.py` (new)                               | M      |
| P2-16 | `/goals` admin view                                  | `apps/web/src/app/(dashboard)/goals/page.tsx`          | M      |
| P2-17 | `/my-goals` employee view                            | `apps/web/src/app/(dashboard)/my-goals/page.tsx` (new) | S      |
| P2-18 | Goal progress check-in (manager + employee)          | router endpoint                                        | S      |

#### Exit interview (S8-G1)

| ID    | Item                                        | Files                                                                       | Effort |
| ----- | ------------------------------------------- | --------------------------------------------------------------------------- | ------ |
| P2-19 | `ExitInterview` model                       | `models/company_user.py`                                                    | S      |
| P2-20 | Auto-schedule on RESIGNED event             | `routers/employees.py` exit flow                                            | S      |
| P2-21 | Exit interview form / submit                | `apps/web/src/app/(dashboard)/employees/[id]/exit-interview/page.tsx` (new) | M      |
| P2-22 | Exit reasons aggregation on churn dashboard | aggregation in `routers/strategy.py`                                        | XS     |

#### Onboarding polish (S4-G1, G2)

| ID    | Item                                    | Files                            | Effort |
| ----- | --------------------------------------- | -------------------------------- | ------ |
| P2-23 | Buddy check-in workflow (S4-G1)         | `BuddyCheckin` model + cron + UI | M      |
| P2-24 | 30/60/90-day review auto-create (S4-G2) | hook into hire flow              | S      |

**Phase 2 schema changes** (manageable):

- 5 new tables: `training_records`, `certifications`, `recognition`,
  `goals`, `exit_interviews`, `buddy_checkins`. All additive.

---

## Phase 3 — Strategic depth

**Goal:** workforce strategy becomes a first-class platform artefact.
Skills inventory, succession planning, retention-risk scoring.

**Effort:** ~20–25 dev-days (3 weeks).

**Demo-able checkpoint:** Owner edits the `/strategy` page → sets
quarterly headcount targets per department + identifies 3 critical
roles + their successors → reviews retention-risk-scored employees in a
ranked list. The lifecycle dashboard now shows target-vs-actual
headcount per department.

### Phase 3 deliverables

#### Workforce plan (S1-G2)

| ID   | Item                                              | Files                                                  | Effort |
| ---- | ------------------------------------------------- | ------------------------------------------------------ | ------ |
| P3-1 | `WorkforcePlan` model                             | `models/company_user.py`                               | S      |
| P3-2 | Strategy router                                   | `routers/strategy.py` (extends P1)                     | M      |
| P3-3 | `/strategy` page (edit / approve plan)            | `apps/web/src/app/(dashboard)/strategy/page.tsx` (new) | M      |
| P3-4 | Headcount-target-vs-actual on lifecycle dashboard | aggregation                                            | S      |

#### Skills inventory (S1-G3)

| ID   | Item                                  | Files                                  | Effort |
| ---- | ------------------------------------- | -------------------------------------- | ------ |
| P3-5 | `Employee.skills_json` field          | `models/company_user.py` ALTER         | S      |
| P3-6 | `SkillsCatalogue` (taxonomy)          | new model                              | S      |
| P3-7 | Skills tagging UI on employee profile | `apps/web/.../employees/[id]/page.tsx` | M      |
| P3-8 | Skills coverage per department widget | aggregation                            | S      |

#### Succession planning (S1-G4 / S7-G4)

| ID    | Item                                       | Files                                    | Effort |
| ----- | ------------------------------------------ | ---------------------------------------- | ------ |
| P3-9  | `SuccessionPlan` model                     | `models/company_user.py`                 | S      |
| P3-10 | Succession router                          | `routers/succession.py` (new)            | M      |
| P3-11 | "Critical roles" tagger on Job/Designation | UI + endpoint                            | S      |
| P3-12 | Succession map page                        | `apps/web/.../succession/page.tsx` (new) | M      |

#### Retention-risk scoring (S1-G5 / S8-G3)

| ID    | Item                                                     | Files                           | Effort |
| ----- | -------------------------------------------------------- | ------------------------------- | ------ |
| P3-13 | Retention-risk aggregation endpoint (no model — derived) | `routers/strategy.py` extension | S      |
| P3-14 | Risk-ranked employee list view                           | dashboard widget                | S      |

#### Other gap items folded in

| ID    | Item                                           | Effort |
| ----- | ---------------------------------------------- | ------ |
| P3-15 | PIP workflow (S7-G2)                           | M      |
| P3-16 | 360 feedback (S7-G3)                           | M      |
| P3-17 | Total-rewards statement PDF (S6-G5)            | M      |
| P3-18 | Pay-equity within-role analysis (extends P1-7) | S      |
| P3-19 | Referral programme (S2-G3)                     | M      |
| P3-20 | Talent-pool re-engagement tag (S3-G1)          | S      |
| P3-21 | Alumni tagging (S8-G4)                         | S      |
| P3-22 | Tenure-milestone alerts (S8-G5)                | S      |

---

## Total scope

| Phase     | Effort         | New tables | New routers | New pages |
| --------- | -------------- | ---------- | ----------- | --------- |
| 1         | 10–12 days     | 0          | 1           | 2         |
| 2         | 25–30 days     | 6          | 4           | 6         |
| 3         | 20–25 days     | 4          | 2           | 4         |
| **Total** | **55–67 days** | **10**     | **7**       | **12**    |

At 1.5 dev-days per calendar day with parallel agents that's roughly 8
calendar weeks for the full programme, demo-able after every phase.

---

## What's deliberately deferred or out of scope

- **External ATS integration** (Greenhouse / Workable / etc.) — Arbor's
  recruitment is the ATS for SG SMEs. No need.
- **AI succession-readiness scoring** — phase 3.5 maybe; could ride on
  AdvisoryEngine LLM call but not P0.
- **Employer-brand external campaign tools** (paid LinkedIn job ads,
  glassdoor integration) — partner / future.
- **Performance-review external benchmarks** (industry pay benchmarks) —
  data licensing question.
- **Surveys engine** (engagement, pulse) at full feature parity with
  Culture Amp / Lattice — basic pulse is in P2-23/24, full survey
  engine is a future module.

---

## What this delivers strategically

After Phase 1: **Arbor demos as a full-lifecycle HRIS**, not a
collection of HR features. The 8-stage card grid + per-stage health pills + D&I cross-cutting tile are the headline surfaces.

After Phase 2: **Arbor delivers continuous people operations**, not
just transactions. Recognition + L&D + Goals turn the platform from
"HR system of record" into "HR platform people actually engage with."

After Phase 3: **Arbor becomes a workforce strategy platform**, not
just an operational HRIS. Owners set quarterly plans + monitor execution
against them — the "Strategy" centrepiece of the Cox lifecycle model
becomes a real, editable platform artefact.

---

## What to do next

1. Human review of `briefs/01-` + `01-analysis/01-` through `05-`.
2. Approve / amend / re-prioritise the 12 P0 items in `03-gap-analysis.md`.
3. Approve the 3-phase plan above.
4. `/todos` phase converts this into `todos/active/` files.
5. `/implement` flow ships Phase 1 first (smallest, demo-able first).
