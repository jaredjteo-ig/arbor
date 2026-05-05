# 02 — Lifecycle Dashboard UI Spec

The visual centrepiece of the lifecycle initiative. **The Cox wheel is
reference material only — it does NOT get reproduced as a UI element.**
This spec describes a clean, card-based layout that uses the 8 stages as
an organising structure without any literal wheel graphic.

---

## Page structure

```
/dashboard/lifecycle
├── Hero band (workforce strategy summary — 1 row)
├── 8-stage layout (cards in a grid OR horizontal stepper)
├── Stage detail panel (slides in below when a stage card clicked)
├── D&I cross-cutting tile (compact summary + link to /diversity)
└── Recent activity feed (last 7 days, cross-stage)
```

Width: full main-area width (`max-w-7xl mx-auto`). Mobile: cards stack
vertically.

Auth: `Depends(require_role("owner", "hr_manager"))` — same gate as the
existing dashboard.

---

## Hero band (unchanged from previous spec)

```
┌────────────────────────────────────────────────────────────────────┐
│  Workforce Strategy                          [Edit Plan ▸]         │
│  ────────────────────────────────────────────────────────────────  │
│  Q2 FY2026  •  Plan status: Active  •  Last reviewed: 12 Apr       │
│                                                                     │
│  Headcount    Open roles    Critical roles    Churn YTD             │
│   28 / 32       3 jobs         2 at risk         4%                 │
│   ⚠ -4         (1 stale)      (Eng Mgr,         ▼ -1pt YoY          │
│                                Sales Lead)                          │
└────────────────────────────────────────────────────────────────────┘
```

In Phase 1 (no `WorkforcePlan` yet), Hero shows actual headcount only,
"Edit Plan" is disabled with tooltip "Coming in next release."

---

## The 8-stage layout (cards, not a wheel)

### Layout option A — 4×2 card grid (recommended for desktop)

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ 1 Strategy  │ 2 Attract   │ 3 Recruit   │ 4 Onboard   │
│ ●●● healthy │ ●●● healthy │ ●●  attn    │ ●●● healthy │
│ ┌─────┐     │             │ 2 stale     │ 87% on      │
│ │ icon│     │ 3 sources   │ jobs        │ track       │
│ └─────┘     │ active      │             │             │
│ View ▸      │ View ▸      │ View ▸      │ View ▸      │
├─────────────┼─────────────┼─────────────┼─────────────┤
│ 5 L&D       │ 6 Reward    │ 7 Progress  │ 8 Retain    │
│ ●   action  │ ●●● healthy │ ●●  attn    │ ●●● healthy │
│ Data        │ Payroll on  │ 5 reviews   │ Churn -1pt  │
│ missing     │ time        │ due         │ YoY         │
│ View ▸      │ View ▸      │ View ▸      │ View ▸      │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

Each card has:

- **Stage number + name** (Cox numbering preserved as a learning
  artefact: 1 Strategy, 2 Attract, ...)
- **Health pill** — coloured dot + word (healthy / attn / action). NOT a
  rainbow wheel slice. Standard design-system status pill.
- **Headline KPI** (1 line)
- **"View ▸" link** — opens the stage detail panel below OR navigates
  to the underlying module
- **Icon** in the top-left for visual scanning (Lucide: Lightbulb,
  Magnet, UserPlus, Briefcase, GraduationCap, Award, TrendingUp,
  DoorOpen)

### Layout option B — horizontal stepper (compact / mobile)

```
1 Strategy ▸ 2 Attract ▸ 3 Recruit ▸ 4 Onboard ▸ 5 L&D ▸ 6 Reward ▸ 7 Progress ▸ 8 Retain
   ●●●           ●●●         ●●          ●●●        ●         ●●●         ●●          ●●●
```

A stepper line where each "step" is the stage with its health dot.
Click a step → stage detail panel below.

### Layout option C — vertical list (mobile default)

```
┌──────────────────────────────────────────┐
│ 1 ● Strategy                  [edit]    │
│   Headcount delta: -4                    │
├──────────────────────────────────────────┤
│ 2 ● Attract            ✓ healthy        │
│   3 sources active in last 30d           │
├──────────────────────────────────────────┤
│ 3 ⚠ Recruit                 [view]      │
│   2 stale jobs                           │
├──────────────────────────────────────────┤
│ 4 ✓ Onboard                 [view]      │
│   Avg completion 87%                     │
└──────────────────────────────────────────┘
```

### Recommended approach

**Default to Option A (4×2 card grid)** at ≥1024px. **Collapse to
Option C (vertical list)** at <1024px. **Skip Option B** (stepper)
unless a future redesign wants a more compact at-a-glance bar.

Critically: **none of these three options reproduces the literal Cox
wheel.** They use the 8-stage taxonomy as content organisation, not
as a graphical artefact.

---

## Stage detail panel (per stage)

Below the 8-stage grid. 8 distinct panel layouts (one per stage). Same
content as previously specced — only the entry visual (the wheel)
changed; the per-stage detail panel content is unchanged.

### Stage 3 — Recruit detail panel (example)

```
┌───────────── Recruit ──────────────────────── [Open Recruitment ▸] ┐
│                                                                     │
│  Active jobs: 3        Active candidates: 8        Time to hire: 24d│
│                                                                     │
│  Pipeline                                                           │
│  ───────────                                                        │
│  New ████████ 14    Screening ██ 1    Interview █████ 5             │
│  Assessment 0       Offered 0         Hired 0  (last 30d)          │
│                                                                     │
│  D&I lens — funnel by gender                                        │
│  Apply  Screen  Interview  Offer  Hire                              │
│  M ███   ███     ██         █      █                                │
│  F ██    ██      ░          ░      ░    (drop-off at Interview)    │
│                                                                     │
│  Quick actions                                                      │
│  [Review pending interviews]  [View pipeline]  [Add candidate]      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

Each stage panel contains:

1. **Headline KPIs** (3–4 numbers)
2. **Stage-specific visualisation** (pipeline / funnel / progress
   bars)
3. **D&I lens** for that stage (one chart)
4. **Quick actions** (3–5 deep links into the existing module)

### All 8 stage detail panels (specifications)

| Stage         | Headline KPIs                                                  | Visualisation                                  | D&I lens                       | Quick actions                                  |
| ------------- | -------------------------------------------------------------- | ---------------------------------------------- | ------------------------------ | ---------------------------------------------- |
| 1 Strategy    | Headcount delta, Skills coverage, Open roles                   | Headcount-target-vs-actual bar chart           | Composition pie                | Edit Plan, View Departments                    |
| 2 Attract     | Public-page views (when tracked), Source mix, Apply conversion | Source-mix donut                               | Source diversity bar           | View public careers page, Edit employer brand  |
| 3 Recruit     | Active jobs, Candidates in pipeline, Time-to-hire              | Pipeline kanban summary                        | Funnel by gender               | Review interviews, View candidates, New job    |
| 4 Onboard     | Active assignments, Avg completion %, Overdue count            | Completion progress bars per active assignment | Completion-by-demographic bars | View templates, Onboarding tasks               |
| 5 L&D         | Trainings YTD, Hours per employee, Cert expiries (30d)         | Training hours timeline                        | Training hours by gender       | Log training, View ledger, Browse SkillsFuture |
| 6 Reward      | Last payroll status, Recognition events (30d), Pay-equity gap  | Recognition feed (last 5)                      | Pay gap headline               | Run payroll, Give kudos, View pay equity       |
| 7 Progression | Goals progress, Appraisals due, Promotions YTD                 | Goal-progress thermometer per dept             | Promotion rate by demographic  | View appraisals, Edit goals                    |
| 8 Retain/Exit | Churn YTD, Voluntary vs involuntary, Retention risks           | Churn over last 12 months line chart           | Churn by tenure bucket         | Review at-risk employees, Exit interviews      |

---

## D&I cross-cutting tile

A compact 280px-tall card below the stage detail panel:

```
┌───── Diversity & Inclusion Snapshot ───────── [Full report ▸] ┐
│                                                                │
│  Composition                Pay equity                         │
│  M 64% F 32% Other 4%       -8% female (within-role: -3%)      │
│  Citizens 50% PR 21% EP 14% [Investigate ▸]                    │
│                                                                │
│  Funnel drop-off:  Interview → Offer  (M 50% F 30%)            │
│  Recent promotions: 3 male, 1 female, 1 PR, 0 WP               │
│                                                                │
│  Demographic data completeness:                                │
│  Gender 96% ✓  Citizenship 100% ✓  DOB 88% ⚠  Race 12% (off)  │
└────────────────────────────────────────────────────────────────┘
```

Links to the full `/dashboard/diversity-inclusion` page.

---

## Recent activity feed

Right column on desktop, below D&I tile on mobile. Last 7 days of
cross-stage activity.

```
┌────────────── Recent activity (7d) ──────────┐
│ 📅 2 hours ago                                 │
│   Interview scheduled: Aisha Binte Rahman      │
│   (recruit)                                    │
│ 🎉 6 hours ago                                 │
│   Recognition: "Great work on the X launch"    │
│   from Lily → Joel  (reward)                   │
│ 📈 1 day ago                                   │
│   Q1 appraisal completed: Pradeep Reddy        │
│   (progression)                                │
│ 📥 2 days ago                                  │
│   Eunice Wee onboarding 50% complete           │
│   (onboard)                                    │
│ 🎓 3 days ago                                  │
│   Training logged: WSH supervisor course       │
│   (l&d)                                        │
└────────────────────────────────────────────────┘
```

Sourced from a single union query across `EmploymentEvent`,
`InterviewSchedule`, `OnboardingStepProgress`, `Recognition`, `Goal`,
`TrainingRecord`, `Appraisal`, `ExitInterview`. Limit 20 most-recent.

---

## API endpoint shape

`GET /strategy/lifecycle-dashboard` returns one consolidated payload:

```json
{
  "hero": {
    "headcount_actual": 28,
    "headcount_target": 32,
    "open_jobs": 3,
    "stale_jobs": 1,
    "critical_roles_at_risk": 2,
    "churn_ytd_pct": 4.0,
    "churn_yoy_delta": -1.0
  },
  "stages": {
    "strategy":   { "health": "amber", "kpi": { "delta": -4 } },
    "attract":    { "health": "green", "kpi": { "applies_30d": 12 } },
    "recruit":    { "health": "amber", "kpi": { "active_jobs": 3, "stale": 1 } },
    "onboard":    { "health": "green", "kpi": { "avg_completion": 0.87 } },
    "lnd":        { "health": "amber", "kpi": { "data_missing": true } },
    "reward":     { "health": "green", "kpi": { "last_payroll": "ok" } },
    "progression":{ "health": "amber", "kpi": { "due_reviews": 5 } },
    "retain":     { "health": "green", "kpi": { "churn_ytd": 0.04 } }
  },
  "di_snapshot": { ... },
  "activity": [ ... ]
}
```

One round-trip. No N+1. All aggregations server-side.

---

## Health pill thresholds

| Stage       | Green when...                                          | Amber when...                   | Red when...                     |
| ----------- | ------------------------------------------------------ | ------------------------------- | ------------------------------- |
| Strategy    | Headcount within 10% of target                         | 10–20% off                      | >20% off OR no plan             |
| Attract     | ≥3 sources active in last 30d                          | 1–2 sources                     | 0 applies last 30d              |
| Recruit     | All open jobs have <14d-old candidate touch            | 1+ stale (≥14d)                 | All jobs stale OR no candidates |
| Onboard     | Avg completion ≥75% AND 0 overdue                      | Avg 50–75% OR 1+ overdue        | Avg <50% OR 3+ overdue          |
| L&D         | Avg ≥10 hours/employee/year                            | 5–10 hours                      | <5 hours OR no data             |
| Reward      | Last payroll on time + ≥1 recognition/employee/quarter | Late payroll OR low recognition | Failed payroll OR 0 recognition |
| Progression | ≥80% of due appraisals completed                       | 50–80%                          | <50%                            |
| Retain      | YoY churn flat or down                                 | YoY +1–3 ppt                    | YoY +>3 ppt                     |

These thresholds are codified in `routers/strategy.py` and pinned by
regression tests.

---

## Empty states

Brand-new company:

- 8-stage card grid still renders, all cards show grey "no data yet"
  state with a "Get started: <action>" CTA.
- Hero band shows "Welcome — add your first employees to populate this
  view."

The lifecycle dashboard becomes the **landing screen** for empty-state
users — guides them through the platform structure without showing a
visual gimmick.

---

## Performance budget

- Single endpoint p95 < 300ms on 200 employees + 10,000 events.
- All aggregations are simple `GROUP BY` on indexed columns. No joins
  beyond `Employee × EmploymentEvent`.
- 30-second server-side cache per company_id. Invalidate-on-write
  deferred to v2 if hit rate is low.

---

## Accessibility

- Each stage card is a `<button>` (or `<a>` if it's a hard nav). Focus
  ring visible. Enter / Space activates.
- Health colour: NEVER colour-only — paired with icon (✓, ⚠, ⛔) +
  text word ("healthy" / "attn" / "action").
- Tab order: card 1 → card 2 → ... → card 8 → D&I tile → Activity feed.
- `prefers-reduced-motion` disables any pulse animation on red cards.

---

## Phase 1 ship checklist

- [ ] 8-stage card-grid layout component (`apps/web/src/components/lifecycle/StageGrid.tsx`)
- [ ] Each card click → scroll to + load stage detail panel
- [ ] All 8 stage detail panels render with KPIs from existing data
- [ ] D&I cross-cutting tile uses existing fields only
- [ ] Activity feed unions across the 8 stage tables that exist today
- [ ] Empty-state renders cleanly for brand-new companies
- [ ] Mobile collapses to vertical list (Option C)
- [ ] Accessibility: keyboard nav + screen-reader labels
- [ ] One Playwright test: open dashboard → click each stage card → verify
      detail panel renders the expected KPI label
- [ ] Sidebar nav "Lifecycle" entry in `NavigationSidebar.tsx`

After Phase 1 ships, the buyer demo walks the 8 stages via the card
grid + detail panels — the lifecycle narrative is real, the wheel
graphic stays in the pitch deck only.
