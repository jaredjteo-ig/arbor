# 05 — Diversity & Inclusion as a Cross-Cutting Layer

The Cox 2019 model's most distinctive feature is that **D&I appears in
every stage's caption**, not as its own ninth segment. The model is
fundamentally about inclusive practice across the full lifecycle.

This doc spec's how D&I metrics surface across every Arbor lifecycle
stage **without** adding new PII fields — every metric below is derivable
from data the platform already collects.

---

## Singapore-specific D&I context

Singapore's D&I framing is different from the UK / US:

- **TAFEP / WFA (Workplace Fairness Act 2024)** — non-discrimination on
  age, gender, race, religion, marital status, family responsibilities,
  disability, mental-health, language. Replaces the older voluntary
  TAFEP guidelines.
- **Foreign manpower diversity** — citizenship status (citizen / PR / EP /
  S Pass / Work Permit) is operationally more salient than race. Quotas
  - levies tied to citizenship class.
- **Gender-balance reporting** — voluntary at SME scale, but increasingly
  expected for larger SMEs and any government-related work.

**Demographic fields already collected on `Employee`:**

| Field                                             | Used for D&I lens                           |
| ------------------------------------------------- | ------------------------------------------- |
| `gender` (male / female / other)                  | Gender pay gap, promotion rate, hiring rate |
| `race` (chinese / malay / indian / other)         | Optional — show only with explicit consent  |
| `nationality` (text)                              | Citizenship-class proxy                     |
| `pass_type` (citizen / pr / ep / sp / wp / other) | Foreign manpower mix                        |
| `immigration_status`                              | Same as pass_type, more granular            |
| `marital_status`                                  | Family-responsibilities lens                |
| `religion`                                        | M39 extension; rarely surfaced              |
| `date_of_birth`                                   | Age cohorts (20s, 30s, 40s, 50+)            |

**Fields NOT collected** (privacy-by-design):

- Disability status
- Sexual orientation / gender identity beyond binary
- Caregiving responsibilities

These are intentionally absent. D&I metrics only use what's already there.

---

## Per-stage D&I view (derivable from existing fields)

### Stage 1 — Strategy

**Metric:** Headcount-target diversity composition.

**Aggregation:** When `WorkforcePlan` lands, the headcount target per
department can carry an optional gender / citizenship target. The
dashboard shows `target_pct` vs `actual_pct` per department.

**Today (no plan model):** Show the overall company composition as a
pie chart — gender, citizenship class, age cohort. One panel.

---

### Stage 2 — Attract

**Metric:** Source diversity of inbound applicants.

**Aggregation:**

```
SELECT source, gender, COUNT(*) FROM candidates
WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY source, gender;
```

**Visual:** Stacked bar — each bar is a source channel, segments are
gender / citizenship. Highlights bias in source mix (e.g., LinkedIn
skews male, referrals skew similar-to-existing).

**Note on race:** Only if employer has opted into race tracking. Default off.

---

### Stage 3 — Recruit

**Metric:** Stage-conversion rate by demographic.

**Aggregation:** For each demographic bucket, what % of `applied`
candidates progressed to `interview`, `offered`, `hired`?

**Visual:** Funnel with paired demographics:

```
Applied:     M ███████  F ████   (100% baseline)
Screening:   M 80%      F 65%
Interview:   M 60%      F 45%
Offered:     M 30%      F 18%   ← drop-off point
Hired:       M 25%      F 15%
```

**Why useful:** surfaces the stage where bias enters. The visual
explicitly shows where the funnel narrows asymmetrically — a manager
with high "offered → male" but low "offered → female" rate gets flagged.

---

### Stage 4 — Onboard

**Metric:** Onboarding completion rate by demographic.

**Aggregation:** `OnboardingAssignment.completion_percentage` averaged
by gender / citizenship / age cohort.

**Visual:** Horizontal bar chart with completion % per demographic. If
one group consistently completes faster / slower, surfaces an
inclusion concern (e.g., language-barrier impact on foreign workers'
onboarding completion).

---

### Stage 5 — Learning & Development

**Metric:** Training hours per employee by demographic.

**Aggregation (when `TrainingRecord` lands):**

```
SELECT gender, AVG(hours) FROM training_records tr
JOIN employees e ON e.id = tr.employee_id
WHERE tr.completed_at > NOW() - INTERVAL '12 months'
GROUP BY gender;
```

**Visual:** Avg training hours / year per demographic. The "all talent
represented and included" Cox principle becomes a measurable thing.

---

### Stage 6 — Reward, Recognition & Benefits

**Metric (most charged):** Pay gap.

**Aggregations:**

| Lens                   | SQL pattern                                                     |
| ---------------------- | --------------------------------------------------------------- |
| Gender pay gap         | `AVG(salary_monthly) GROUP BY gender` — show as ratio + p-value |
| Citizenship pay gap    | `AVG(salary_monthly) GROUP BY pass_type`                        |
| Within-role pay equity | Same role title, pay variance by gender                         |

**Visual:** A dedicated "Pay Equity" tile on the lifecycle dashboard.
Headline number ("Female salaries 8% lower than male, controlling for
role"), then the breakdown table.

**For Recognition (when it lands):** Recognition-events received per
employee, grouped by demographic. Surfaces "do men give kudos to other
men disproportionately?"

---

### Stage 7 — Progression & Performance

**Metric:** Promotion rate by demographic.

**Aggregation:**

```
SELECT gender, COUNT(DISTINCT employee_id) FILTER (WHERE event_type='promoted')
       / COUNT(DISTINCT employee_id) AS promotion_rate
FROM employment_events JOIN employees ON ...
WHERE event_at > NOW() - INTERVAL '12 months'
GROUP BY gender;
```

**Visual:** "Promotions in last 12 months by demographic." Plus
appraisal-score distribution by demographic (so the same appraisal
score should yield comparable promotion rate; bias enters when it
doesn't).

---

### Stage 8 — Retain / Exit

**Metric:** Voluntary churn rate by demographic.

**Aggregation:** `EmploymentEvent.RESIGNED` events per demographic
divided by avg headcount of that demographic.

**Visual:** Churn % by gender, citizenship, age cohort, tenure bucket.
Surfaces "we lose female mid-career engineers at 2× the rate of male."

When `ExitInterview` lands: exit-reason distribution by demographic.

---

## The unified D&I dashboard

A single page (`/dashboard/diversity-inclusion`) aggregates the 8 stage
metrics above into one view. Layout:

```
┌─────────────── Diversity & Inclusion Snapshot ───────────────┐
│                                                                │
│  Company composition         Pay equity                        │
│  ┌────────────────┐          ┌────────────────┐                │
│  │ M 18  F 9      │          │ Gap: -8% (F<M) │                │
│  │ Cit 14  PR 6   │          │ Within-role:   │                │
│  │ EP 5   WP 2    │          │   -3%          │                │
│  └────────────────┘          └────────────────┘                │
│                                                                │
│  Stage funnel by gender                                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Apply  Screen  Interview  Offer  Hire                  │    │
│  │ ████   ███     ██         █      █  Male               │    │
│  │ ███    ██      █          ░      ░  Female            │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
│  Promotion + churn by demographic (last 12 months)             │
│  [bar chart]                                                   │
│                                                                │
│  Demographic-data completeness                                 │
│  Gender 96%  Citizenship 100%  DOB 88%  Race 12%               │
└────────────────────────────────────────────────────────────────┘
```

The "Demographic-data completeness" tile makes data-quality visible.
Companies are nudged to fill gaps so the metrics are reliable.

---

## Privacy + opt-in

- Race-based metrics are **off by default**. Owner explicitly enables
  via Settings → D&I Preferences.
- All metrics aggregate to ≥5 employees per bucket — no
  individual-identifying breakdowns. (e.g., "1 female senior engineer"
  shouldn't show; bucket up to "2 senior engineers" total).
- D&I dashboard view requires `owner` or `hr_manager` role. No
  employee-self view.

---

## Build sequence

| Phase | Scope                                                          | Effort |
| ----- | -------------------------------------------------------------- | ------ |
| 1     | Static composition tile (gender / citizenship / age)           | S      |
| 2     | Source-funnel chart for Recruit stage                          | S      |
| 3     | Pay-gap headline + role-controlled comparison                  | S      |
| 4     | Onboarding-completion-by-demographic chart                     | S      |
| 5     | Promotion + churn by demographic                               | S      |
| 6     | (Once `TrainingRecord` exists) — training hours by demographic | S      |
| 7     | Demographic-completeness scoring widget                        | S      |
| 8     | Race opt-in toggle + privacy guards                            | S      |

Total: ~5 days for the entire D&I dashboard once the underlying
modules (especially L&D + Recognition) are in place. The basic
read-only version using only existing fields can ship in 2 days.
