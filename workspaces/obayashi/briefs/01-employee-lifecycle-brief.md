# Brief 01 — Emphasising the Employee Lifecycle on the Platform

**Date:** 2026-05-05
**Workspace:** obayashi
**Source artefact:** Steven AJ Cox 2019 — 8-stage Employee Lifecycle wheel
**Author:** Jared (product owner)

---

## Want

Surface and emphasise the **Employee Lifecycle** as a first-class organising
principle for the Arbor HR platform. The reference model has 8 stages around a
central `Strategy` hub:

| #   | Stage                              | Cox 2019 description                                            |
| --- | ---------------------------------- | --------------------------------------------------------------- |
| 1   | **Strategy** (centre)              | Strategic workforce plan designed to deliver corporate strategy |
| 2   | **Attract**                        | Being an appealing inclusive employer                           |
| 3   | **Recruit**                        | Enabling all talent to successfully apply                       |
| 4   | **Onboard**                        | Ensuring all talent is understood and all staff trained         |
| 5   | **Learning & Development**         | All talent represented and included                             |
| 6   | **Reward, Recognition & Benefits** | All talent's needs catered for                                  |
| 7   | **Progression & Performance**      | All talent performance management consistent                    |
| 8   | **Retain / Exit**                  | Talent that wants to stay. Learn from & manage exits.           |

The reference model has a strong **diversity & inclusion (D&I)** undertone in
every stage — every stage's caption emphasises bias-free, inclusive practice.

## Why this matters

Today the platform has **isolated modules** (Recruitment, Onboarding, Payroll,
Leave, Claims, Attendance, Appraisals, etc.) that each work well in isolation
but are **not unified by a lifecycle narrative**. A buyer or HR practitioner
walking the dashboard sees a list of features, not a story of "how this
platform supports our people from attract → exit."

The lifecycle model gives:

- **A buyer-facing narrative** — "we cover the full lifecycle, here's the wheel"
- **Practitioner navigation** — quick jump from any stage to its tools
- **Gap analysis** — visibly highlights stages we under-serve (e.g. Attract,
  Reward & Recognition, Progression)
- **Strategic plumbing** — connects each stage back to a central workforce
  strategy (currently absent as an explicit surface)

## What success looks like

**The wheel image is reference material only — not a UI artefact.** The 8
stages become a structural / navigational taxonomy in the product. No
literal wheel graphic gets drawn.

1. **A lifecycle-organised dashboard surface** (top-nav or owner / HR
   default landing) that presents the 8 stages as a clean horizontal /
   vertical layout — cards, tabs, or a stepper — each with stage-level
   health metrics and deep-links into the relevant modules. Layout is a
   product-design call, NOT a Cox-wheel reproduction.
2. **Per-stage health scoring** — for each of the 8 stages, derive a status
   from existing data (e.g. Recruit health = candidates active vs stale jobs;
   Onboard health = avg completion %; Retain health = churn % YoY).
3. **Strategy hub** — a new page that captures the company's workforce
   strategy (headcount targets, skills gaps, succession plans) and shows how
   each lifecycle stage contributes.
4. **Identify and close gaps** — explicit roadmap of which lifecycle stages
   are under-served by current modules and what to build/integrate.
5. **D&I lens** — every stage surfaces the equivalent of "inclusive practice"
   indicators (e.g. Recruit shows source diversity; L&D shows participation by
   demographic; Reward shows pay equity gap).

## Constraints

- **Cannot break existing modules.** Lifecycle is a NEW lens, not a
  replacement.
- **Reuse existing data wherever possible.** Don't add new schemas without
  clear value.
- **D&I metrics must be derivable from already-collected fields**
  (gender, race, citizenship_status, etc. on `Employee`) — no new PII fields.
- **Single-tenant single-worker prod** — same operational constraints we've
  worked under all session.

## Out of scope (explicitly defer)

- Full HRIS integration with external ATS / payroll systems.
- AI-driven succession planning / headcount forecasting (could be a v2).
- Public-facing employer-brand pages (Attract stage external surface) — phase 2.

## Inputs to the analyse phase

- This brief.
- The 8-stage diagram itself (above).
- The current Arbor module + model inventory (will be enumerated in
  `01-analysis/02-current-state-mapping.md`).
- The `arbor-platform-specialist` agent's router/model maps.

## Deliverables expected from `/analyze`

1. **`01-analysis/01-lifecycle-decoded.md`** — interpretation of the model in
   Singapore-SME / Arbor context. Each of 8 stages: what it means, what HR
   activities it implies, what data points support it.
2. **`01-analysis/02-current-state-mapping.md`** — for each stage, what
   modules / models / endpoints / pages CURRENTLY exist. Coverage rating
   (1–5) per stage.
3. **`01-analysis/03-gap-analysis.md`** — what's missing per stage and how
   critical each gap is for the buyer story vs. operational use.
4. **`01-analysis/04-strategy-hub-concept.md`** — sketch of the central
   "Strategy" surface that ties the lifecycle together.
5. **`01-analysis/05-di-cross-cutting.md`** — how D&I metrics surface across
   every stage, derived from existing fields.
6. **`02-plans/01-phased-roadmap.md`** — concrete phased plan: phase 1
   (visualise existing capability), phase 2 (close highest-leverage gaps),
   phase 3 (advanced analytics).
7. **`02-plans/02-lifecycle-dashboard-spec.md`** — UI spec for the lifecycle
   dashboard (the wheel + stage detail panels).

After human review of 02-plans, the work converts to `todos/active/` under
the standard COC `/implement` flow.
