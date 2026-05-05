# 04 — Strategy Hub Concept

The "Strategy" core in the Cox wheel is the most under-served stage in
Arbor today. This doc sketches what the Strategy hub should look like as
a first-class platform surface — both as a **buyer-facing narrative** and a
**practitioner-usable workforce-planning tool**.

---

## The "narrative" half — Lifecycle Dashboard

The page is the single entry point to the whole lifecycle story.
**The Cox wheel image is reference material only — it is NOT
reproduced as a UI element.** The 8-stage taxonomy organises the page
content (cards, health pills, detail panels) without any literal
wheel graphic. Full UI spec in `02-plans/02-lifecycle-dashboard-spec.md`.

### URL + entry points

- New top-level page: `/dashboard/lifecycle`
- Add a "Lifecycle" link in the sidebar (or fold it into the existing
  `/dashboard` as a top section)
- Buyer-pitch entry: link from marketing / homepage
- Owner / HR-manager-only (uses `require_role`)

### Layout (above-the-fold)

```
┌─────────────────────────────────────────────────────────────┐
│  Workforce Strategy                              [Edit Plan]│
│  ─────────────────────────────────────────────────────────  │
│  Headcount: 28 / 32 target   Skills coverage: 73% (-2 pts)  │
│  Open roles: 3   Critical roles at risk: 2   Churn YTD: 4%  │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Employee Lifecycle (8 stages)                               │
│  ┌──────────┬──────────┬──────────┬──────────┐               │
│  │ 1 Strat. │ 2 Attract│ 3 Recruit│ 4 Onboard│               │
│  │ ●● amber │ ●●● green│ ●● amber │ ●●● green│               │
│  ├──────────┼──────────┼──────────┼──────────┤               │
│  │ 5 L&D    │ 6 Reward │ 7 Progr. │ 8 Retain │               │
│  │ ● red    │ ●●● green│ ●● amber │ ●●● green│               │
│  └──────────┴──────────┴──────────┴──────────┘               │
│  4×2 card grid. Each card has stage number, name, health     │
│  pill (green/amber/red), 1-line headline KPI, "View ▸" link. │
└──────────────────────────────────────────────────────────────┘

[Click any card → opens that stage's detail panel below]
```

The wheel from the Cox reference is a **conceptual diagram**, not a
product surface. The cards convey the same 8-stage taxonomy in a clean
grid layout that scales to mobile (vertical list) without recreating
the polar geometry.

### Per-card "health pill" — derived from existing data

| Stage       | Health metric                                                                                  | Source                                                   |
| ----------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Strategy    | % of headcount targets met (when `WorkforcePlan` lands)                                        | `WorkforcePlan.headcount_target` vs `Employee.is_active` |
| Attract     | Conversion of public-applies to candidates last 30d                                            | `Candidate.created_at` filtered by source=careers_page   |
| Recruit     | Active jobs with >0 candidates AND latest candidate-touch <14d                                 | `JobListing.status='open'` + `Candidate.updated_at`      |
| Onboard     | % of `OnboardingAssignment` not overdue, plus avg completion %                                 | `OnboardingAssignment.status` + `completion_percentage`  |
| L&D         | % employees with at least 1 training in last 12 months (once `TrainingRecord` exists)          | `TrainingRecord` aggregations                            |
| Reward      | Last payroll closed on time + recognition events / employee / month (once `Recognition` lands) | `PayrollRun.status` + `Recognition` count                |
| Progression | % of due appraisals completed in current period                                                | `Appraisal.status` filtered by `AppraisalPeriod` window  |
| Retain/Exit | Voluntary churn last 12 months vs prior 12 months                                              | `EmploymentEvent.RESIGNED` aggregations                  |

Each pill is computed by a single SQL aggregation. No new schema
required until the stage's underlying model is built.

### Stage detail panel (shown when a card is clicked)

When the user clicks the "Recruit" card, the lower half of the page
expands to show:

- **Headline metric** (e.g., "8 active candidates across 2 open roles")
- **3 stage-specific KPIs** (e.g., time-to-hire, source-mix, stage
  conversion)
- **D&I lens panel** — applicable diversity metric for that stage
  (e.g., "Source diversity: 4 channels, top 2 produce 60% of hires")
- **Quick actions** — context-aware links to the underlying module
  (e.g., "Review pending interviews", "View candidate pipeline")

This is the practitioner-usable bit. Clicking deeper takes the user to
the existing recruitment / onboarding / etc. modules — the lifecycle
dashboard is a **navigation hub**, not a duplicate of the modules.

---

## The "operational" half — Workforce Plan

This is the persisted **strategy artefact** every quarter the owner /
HR head updates.

### New model: `WorkforcePlan`

```python
@db.model
class WorkforcePlan:
    """Quarterly workforce strategy snapshot.

    One row per company per quarter. Captures headcount targets, skills
    priorities, and retention focus. Drives the Strategy hub's headline
    metrics.
    """
    company_id: int
    period_start: datetime  # quarter start
    period_end: datetime
    status: str = "draft"  # draft / active / closed

    # Headcount targets per department (JSON: {"Engineering": 12, "Sales": 5})
    headcount_targets_json: str = ""

    # Top 3 skills the company is investing in this quarter
    skills_priorities_json: str = ""  # JSON list of {skill, target_employees}

    # Critical roles at risk (JSON: [{role: "Eng Manager", risk: "high"}])
    retention_focus_json: str = ""

    # Free-text strategic narrative (what's the workforce story this quarter?)
    narrative: str = ""

    created_by: int = 0
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
```

### New endpoints

- `GET /strategy/current` — returns the active plan for the current quarter
- `POST /strategy/plan` — owner creates / updates the draft plan
- `POST /strategy/plan/{id}/approve` — finalize the plan (status → active)
- `GET /strategy/lifecycle-dashboard` — the per-stage health aggregation
- `GET /strategy/diversity-snapshot` — the D&I cross-cutting view

### New page: `/strategy`

Edit the workforce plan. Form fields for headcount targets per department,
skills priorities (autocomplete from a `SkillsCatalogue`), retention-focus
selector. Free-text narrative field. Save / approve buttons.

---

## Why this works as a buyer narrative

**Story arc the platform now tells:**

1. **Strategy** (centre) — "We help you set the workforce plan."
2. **Attract** — "Your careers page reflects who you are as an employer."
3. **Recruit** — "AI-screened candidates, TAFEP-compliant, full pipeline."
4. **Onboard** — "Auto-assigned templates, preboarding, daily reminders."
5. **L&D** — "SkillsFuture catalogue + internal training records + cert
   expiry alerts."
6. **Reward** — "Singapore-spec payroll + leave + claims + recognition
   wall."
7. **Progression** — "Appraisals + goals + 30/60/90-day reviews."
8. **Retain / Exit** — "Churn analytics, exit interviews, alumni tags."

A buyer can now navigate the full "people story" of their company, not
a feature list.

---

## Design principles

1. **No literal wheel graphic.** The Cox image is reference material;
   the product UI uses a clean card grid (or a vertical list on
   mobile). Stage taxonomy stays; geometry doesn't.
2. **Lifecycle is navigation, not duplication.** Clicking a stage card
   takes the user to the existing module. Don't rebuild Recruit views
   inside the Strategy hub.
3. **Health pills derive from already-collected data.** No new
   instrumentation in Phase 1. New schema only when a stage's source
   doesn't exist yet (L&D, Recognition, Goals).
4. **D&I is a transverse layer, not a separate stage.** Per-stage
   metrics surface their D&I view inline — no separate "Diversity"
   tab that gets ignored.
5. **Strategy is editable, not just read-only.** The owner / HR head
   actively maintains the workforce plan; the platform doesn't just
   tell them their numbers.
6. **Mobile-friendly.** Card grid stacks to a vertical list at <1024px;
   each stage panel is independently scrollable.

---

## Phased build plan for Strategy hub itself

| Phase | Scope                                                                                 | Effort |
| ----- | ------------------------------------------------------------------------------------- | ------ |
| 1     | Lifecycle dashboard rendering the 8-stage card grid + health pills from existing data | M (5d) |
| 2     | `WorkforcePlan` model + edit page                                                     | M (5d) |
| 3     | D&I cross-cutting panel (read aggregations only)                                      | S (2d) |
| 4     | Skills catalogue + per-employee skills tagging                                        | M (5d) |
| 5     | Retention-risk scoring (derived)                                                      | S (2d) |
| 6     | Succession-plan model + critical-role tagging                                         | M (5d) |

Phases 1–3 are the **demo-able** Strategy hub. Phases 4–6 are the
strategic-depth follow-on.
