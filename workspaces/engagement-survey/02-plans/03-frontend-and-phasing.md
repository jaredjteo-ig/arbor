# Frontend pages + phasing

## Frontend pages — admin (HR)

All under `apps/web/src/app/(dashboard)/engagement/`. Sidebar entry
"Engagement" is added between "Goals" and "Recognition" in the
Management group, gated to owner / hr_manager via the existing
sidebar role logic.

### `/engagement` (overview)

Top-level dashboard for HR.

- Hero band: latest pulse score, response rate, eNPS.
- Trend chart: last 6 pulses or last 12 months — Likert average over
  time.
- Open surveys card: surveys with `closed_at == null`, response %.
- Recent themes: aggregated theme tally across the last 90 days of
  responses.
- Cross-stage panel (v2): "of the 3 employees who resigned this
  quarter, 2 cited 'growth' in their exit interview AND scored 1-2 on
  Q4 (career growth) in the last engagement pulse before resigning".

Tabs:

| Tab       | What it shows                                     |
| --------- | ------------------------------------------------- |
| Surveys   | List of launched surveys; click → detail page     |
| Templates | Library + custom; click → editor                  |
| Cohorts   | Saved cohorts + create new                        |
| Schedules | Active recurring schedules; pause/resume controls |

### `/engagement/templates/[id]` (template editor)

- Sections rail (left) with reorderable sections.
- Per-section: title + question list with type icons.
- Question editor inline: text, type, options (for single/multi),
  required flag, max_length (for text).
- Methodology dropdown at the top with shipped library options
  (clones into a new template).
- "Preview" button opens a read-only modal rendering exactly what
  the employee will see.

### `/engagement/surveys/[id]` (survey detail)

- Header: name, template, cohort summary, launched_at, closes_at,
  response %.
- Tabs:
  - **Aggregated** — per-question Likert distribution bars + theme
    chips for free-text questions + eNPS card.
  - **By cohort** — same metrics broken down by department / pass
    type / tenure band; suppress rows where `n < 5`.
  - **Responses** — list of individual rows (anonymized to "Anonymous"
    when survey is anonymous; otherwise employee names per round-3
    enrichment patterns). Click expands to show full payload —
    reuse the exit-interview detail-card pattern.
- Action buttons: "Send reminder" (re-emails non-responders), "Close
  survey", "Export CSV/PDF".

### `/engagement/launch` (launch wizard)

Three-step modal/wizard:

1. **Pick template** — list of library + custom templates with
   "(method: gallup_q12)" badges.
2. **Pick cohort** — saved cohorts OR build inline with the same
   filter controls as the cohorts editor. Live preview shows
   matched count + anonymity safety status.
3. **Configure** — name, anonymous toggle, closes_at, schedule
   recurrence (off / weekly / biweekly / monthly / quarterly).

Submit calls `POST /engagement-surveys/surveys/launch`.

## Frontend pages — employee

### `/my-engagement-surveys`

- Header: "Engagement check-ins" with brief copy explaining what
  these are and that responses are anonymous (when applicable).
- Pending list: cards with survey name, ~time-to-complete, deadline,
  "Start" button.
- History list (collapsed by default): past submissions when survey
  was non-anonymous.
- After clicking Start, route to `/my-engagement-surveys/[id]/respond`
  — the same in-app form the public tokenised page renders.

### `/my-dashboard` enhancement

Add a "Pending check-ins" card under "Leave balance" / "Company
policies" when the user has at least one pending engagement-survey
response. One-line summary: "1 pulse open · closes in 3 days".

### Public route — `/engagement-survey/[token]/page.tsx`

Mirror `/exit-survey/[token]/page.tsx`:

- Mount-time preflight via `GET /public/{token}/validate`.
- Render same semantic empty states (invalid / not_found /
  already_submitted / closed).
- Render the question form via `GET /public/{token}/render`.
- Submit via `POST /public/{token}/submit`.

## Component reuse

| Component                         | Origin                        | Usage in engagement                          |
| --------------------------------- | ----------------------------- | -------------------------------------------- |
| `<Likert5 value onChange label/>` | New, shared to exit-interview | Q1/Q2 of exit + every Likert q on engagement |
| `<ChipMultiSelect options/>`      | New, shared                   | Q3 reasons in exit + multi q in engagement   |
| `<ResponseDetail payload/>`       | Generalised from exit         | Both modules; round-5 P45 enrichment pattern |
| `<ScoreBar score/>`               | Round-5 (exit + appraisal)    | Per-criterion bars on aggregate views        |
| `<ThemeChips themes/>`            | New, shared                   | Theme tally cells on aggregate               |
| Tokenised public page shell       | exit-survey/[token]/page.tsx  | Copy + parameterise on token-prefix          |

Move these into `apps/web/src/components/surveys/` so both modules
import from one place.

## Phasing

### P1 — minimum shippable demo (ETA: 2 sessions)

**Backend.** Five new models, full template CRUD, cohort CRUD, launch
endpoint, public token endpoints (validate / render / submit), employee
in-app endpoints (my-pending / submit), aggregate endpoint with Likert
distribution + theme tally + eNPS. Seed Q12 paraphrase + monthly pulse
templates on first GET.

**Frontend.** `/engagement` overview, `/engagement/launch` wizard,
`/engagement/surveys/[id]` detail, `/my-engagement-surveys` employee
page, `/engagement-survey/[token]` public page. Sidebar entry.

**Defer:** schedules + cron, Trust Index template, manager-level
views, exports, cross-stage analytics tile.

### P2 — recurring + Trust Index + exports (ETA: 1 session)

- Schedule + recurrence cron tick.
- Trust Index pillars template + Singapore SME quarterly template.
- CSV / PDF export of aggregate.
- Reminder send-button.

### P3 — cross-stage analytics + manager view (ETA: 1 session)

- Cross-stage tile on lifecycle dashboard ("of the X who resigned, Y
  showed engagement signals N days prior").
- Manager-level view: each manager sees aggregate for their direct
  reports if `n >= 5`. Otherwise "Roll up to your skip-level for
  visibility."
- LLM theme analysis swap-in for `_theme_tags` (gated by P13 cost cap).
- eNPS as a lifecycle dashboard hero metric.
- Slack / Teams delivery channel.

## Demo storyboard (the value-flow show)

Order of clicks for a buyer demo:

1. Grace clicks **Engagement** → sees the overview with last pulse
   score 3.8/5, response rate 82%, eNPS +18. Trend chart shows
   Engineering scores trending down 3 months.
2. Click into the latest pulse survey → switch to **By cohort** tab
   → Engineering's average is 3.2 (red), Sales is 4.4 (green).
3. Click into Engineering's expanded view → most-common theme is
   "growth" (5 of 8 mentioned).
4. Switch to **Lifecycle** in the sidebar → Reward stage shows
   matching trend; Retain stage shows the "of the 3 who resigned this
   quarter, 2 cited growth" panel.
5. Open one of the resigned employees' exit interview → growth
   theme matches.

This is the single value flow the whole feature is built to deliver.
Every architectural choice traces back to it.

## Quality gates per phase

- P1 lands when: Grace can launch a Q12-style survey to all 28
  employees in ≤3 minutes, Lily completes it in ≤90 seconds, the
  aggregate page populates within 30 seconds of submit, and the
  Playwright walkthrough exercises the full HR + employee path.
- P2 lands when: schedule cron has launched at least one pulse
  automatically end-to-end on staging, CSV export validates against
  Excel/Sheets, reminder email is delivered.
- P3 lands when: the cross-stage panel demonstrates a real
  correlation in the seeded demo data and the manager view enforces
  the n≥5 anonymity rule.

## Test discipline

For every endpoint listed in `02-api-and-routes.md`:

- Tier 1 unit test in `tests/regression/test_engagement_*.py` for
  each contract (anonymity invariants, tokenised submit, cohort
  resolver edge cases).
- Tier 3 Playwright walk for each user flow before declaring P1
  complete (Grace launches → Lily completes → Grace reviews).

Reuse the live-Playwright redteam method that closed rounds 3-7
(per the codified `enrichment-and-detail-patterns.md` audit
protocol).
