# M4 — Frontend: HR pages (round-3 revised)

**Source plan:** `02-plans/03-frontend-and-phasing.md` §Frontend pages — admin, plus `02-plans/04-product-revision-round3.md`.

Round 3 added: **trend-chart hero**, **manager-view tab**, **action panel** on detail page. Trimmed: cohort UI to **3 presets + ad-hoc** (full builder defers to M8 T91).

All pages under `apps/web/src/app/(dashboard)/engagement/`. Uses shared survey components from M0 T02. Sidebar entry "Engagement" gated by role per `role-aware-ux.md` (P46).

## T40 — Sidebar entry + route gating

- **What:** Add "Engagement" link in `NavigationSidebar.tsx` under the Management group, between "Goals" and "Recognition". Use `MessageSquareDot` icon.
- **Role-gating:** sidebar already filters by role; add the entry under the admin-only block per `role-aware-ux.md`.
- **AdminGuard:** wrap every `engagement/**` page in `<AdminGuard>` to deny employees at the route level.
  - **Exception:** `/engagement/team` (manager view, T44) is gated by "has at least one direct report", NOT admin role. Lily can't access it; Tanaka (manager but not admin) can.
- **API service layer:** `apps/web/src/services/api/engagement.ts` with typed methods for every endpoint in M2 + M3.
- **Acceptance:** Grace sees "Engagement" in sidebar; Lily does not; Lily hitting `/engagement` directly gets the AdminGuard "Access Denied"; Tanaka (non-admin manager) can hit `/engagement/team` but not `/engagement` overview.

## T41 — `/engagement` overview page (with trend hero)

- **Hero band (round-3 redesigned):**
  - **Primary element:** 6-pulse trend line chart, calling `GET /surveys/trend?cohort=all&window=6_pulses`. X-axis = closed_at dates; Y-axis = avg_likert. Secondary line for eNPS overlaid.
  - **Cohort dropdown:** above the chart — `All staff | Department: Eng / Sales / ... | Custom...`. Reloads chart with new cohort param.
  - **Inset stats:** small numbers below the chart — "Latest pulse: 3.2 / 5 · 22 of 28 responded · eNPS +18 · 6-pulse trend: ↓ 0.6". Latest-pulse is no longer the dominant element.
  - **Empty state:** if no closed pulses yet, hero shows "Trend appears after your first pulse closes" with a CTA "Launch your first pulse".
- **Tabs:**
  - Surveys (default)
  - Templates
  - Cohorts
  - Schedules (P2)
- **Empty state below tabs:** "Launch your first engagement survey" CTA → opens wizard. Copy: "Pulse surveys take 90 seconds for employees and surface engagement signals long before they show up in exits."
- **Acceptance:** Grace lands and immediately sees the trend chart with seeded 6 pulses showing the descending Engineering line. Switching cohorts reloads the chart in <500ms.

## T42 — Templates tab + editor

- **What:** Library list (cards: name, methodology badge, question count). Each card has: View, Clone, Edit (only for company-owned custom templates).
- **Editor route:** `/engagement/templates/[id]` — sections rail (left) reorderable, per-section question list, inline question editor.
- **Question types (P1):** Likert-5, Single-select, Multi-select, Short text, Long text, eNPS (0-10).
- **Methodology badge:** `gallup_q12` (purple), `pulse` (blue), `trust_index` (gold — P2), `custom` (grey).
- **Preview button:** opens read-only modal rendering the form the way an employee will see it.
- **Save:** PATCH /templates/{id}.
- **Acceptance:** Grace creates a custom template, adds 5 questions; preview matches what Lily will see in-app.

## T43 — Cohorts tab + editor (P1: presets + ad-hoc)

- **What:** Cohort list (name, matched count, last_used_at). Editor modal for selecting from **3 presets + optional ad-hoc list**.
- **P1 UI controls:**
  - Radio: pick a preset — `All active staff` / `By department` (with department multi-select if chosen) / `New joiners (under 90 days)`.
  - "Add specific employees" search-multiselect (always available; combines with preset).
- **Preview panel:** on every change, debounced fire to `/cohorts/preview` and render `matched_count`, sample names (first 8), anonymity safety chip, overlap warnings.
- **Full filter UI deferred to M8 T91:** Note in the page footer "Need more filters? Coming in v2."
- **Save:** POST /cohorts (create) or PATCH /cohorts/{id} (update).
- **Acceptance:** filter changes update preview within 500ms; anonymity-unsafe state shows red chip with explanation; Grace can build "Engineering only" via department preset.

## T44 — Manager view (`/engagement/team`) — NEW (round-3, pulled from P3)

- **What:** New page for any user with at least one direct report. Aggregates engagement data for the manager's reports.
- **Auth:** non-admin allowed if `has_direct_reports`. AdminGuard does NOT wrap this route.
- **Calls:** `GET /team/aggregate?survey_id={latest_closed_id}` — returns aggregate scoped to manager's reports with n≥5 gate + self-exclusion (Z26).
- **Page layout:**
  - **Header:** "Your team's engagement" with manager's report count + window selector.
  - **If `n < 5`:** info panel — "Your team is too small to see aggregated engagement data without risk of identifying individual responses. Roll up to your skip-level manager for visibility."
  - **If `n >= 5`:** trend mini-chart + per-question Likert distribution + theme cloud + eNPS card. Reuses `<ScoreBar>` family.
- **No drill-down to individual responses:** managers see only aggregates. Drill-down is HR-only on `/engagement/surveys/{id}`.
- **Acceptance:** Tanaka (manager of 6) sees aggregate; manager-of-3 sees suppression notice; manager-of-5-with-own-response sees n=5 visible (self excluded — Z26).

## T45 — Launch wizard

- **What:** Three-step modal at `/engagement/launch`.
- **Step 1 — pick template.** Same library list as Templates tab, "Use this template" button. Selecting clones-and-uses (creates new survey with chosen template_id).
- **Step 2 — pick cohort.** Pick a saved cohort (table) OR build inline using P1 UI (preset + ad-hoc, same as T43). Live preview.
- **Step 3 — configure.**
  - Name input (default: `<template name> — <today's date>`).
  - Anonymity tier radio: Identified / Pseudonymous / Anonymous, with one-line explainers.
  - **Default = match methodology:** pulse → pseudonymous; gallup_q12 → identified.
  - Closes_at date picker (default: today + 14 days, with explicit `+08:00` SGT offset per Z12).
  - Recurrence dropdown (P2): Off / Weekly / Biweekly / Monthly / Quarterly. P1 hard-codes Off.
  - Consent notice preview (read-only) — show PDPA copy that will be appended to the email.
- **Submit:** POST /surveys/launch. On 409 overlap, show confirm dialog with overlap details; on confirm, retry with `force_overlap_acknowledged=true`.
- **Acceptance:** Grace launches a Q12 to all 28 employees in ≤3 minutes (per brief).

## T46 — `/engagement/surveys/[id]` detail page (with action panel)

- **Header:** name, template, cohort summary, launched_at, closes_at, response %.
- **Tabs:**
  - **Aggregated** — calls /aggregate; renders per-question Likert distribution (`<ScoreBar>`), free-text theme chips, eNPS card.
  - **By cohort** — table by department / pass_type / tenure_band (uses `response_cohort_attributes` from Z03). Suppressed cells show "n=2 (suppressed)".
  - **Responses** — list of rows. Anonymity tier dictates label: name (identified) / pseudonym slug (pseudonymous) / "Anonymous". Click expands → reuse `<ResponseDetail>` from M0 T02.
- **Action panel (round-3 NEW, bottom of page):**
  - **Calls:** `GET /surveys/{id}/suggested-actions` for the lowest-scoring cohort with `n >= 5`.
  - **Renders 3 suggested actions** as cards: action text + cohort label + theme chip.
  - **Buttons per card:** "Accept" (POSTs to `/surveys/{id}/actions` with `status=accepted`), "Reject" (POSTs `status=rejected`), "Edit & Accept" (opens modal to edit suggested_action_text before accepting).
  - **One-click create-goal:** Accept opens a small modal "Track this as a Goal? [Yes / No]". Yes → calls Goals module's create-goal API with finding_summary as the goal title; links `linked_goal_id`.
  - **Already-accepted section:** below the suggestions, lists accepted actions with their linked goal label and `next_pulse_anchored_question` for context.
  - **Empty state:** if no cohort has `n >= 5` (e.g. small company with all-anonymous tier), action panel shows "Action suggestions need at least 5 responses in a cohort. They'll appear once your team grows."
- **Action buttons (existing):**
  - Send reminder (P2; otherwise grey "Coming soon").
  - Close survey (POST /surveys/{id}/close, with confirm).
  - Export CSV / PDF (P2).
- **Acceptance:** Grace clicks into the closed pulse, sees per-question distribution, switches to By cohort, sees Engineering 3.2 (red), scrolls to action panel, sees 3 suggestions for Engineering on growth theme, accepts one + creates a goal, sees it appear in `linked_goal_label` immediately.

## T47 — `/engagement/launch` route wiring

- Tiny task: route the wizard from a button on `/engagement` overview. Modal stack on top of overview.

## Dependencies

- T40 → T41, T44 (route wiring).
- T42 → T45 (wizard reuses template list).
- T43 → T45 (wizard reuses cohort UI).
- T44 → M3 T35 (manager-view endpoint).
- T45 → T46 (after launch, redirect to detail page).
- T46 → M3 T36 (suggested-actions) + T37 (action endpoints).
- All → M0 T02 (shared survey components).
- All → M2 / M3 backend service layer in T40.

## Acceptance gate for M4

- All 7 HR pages render without console errors.
- **Trend hero chart renders 6 pulses with cohort filter.**
- Launch wizard end-to-end: pick template → pick cohort → configure → submit → land on detail page.
- Detail page renders aggregate within 1 second of survey close.
- **Action panel surfaces 3 suggested actions; accept-and-create-goal flow works end-to-end.**
- **Manager view (`/engagement/team`) enforces n≥5 and self-exclusion.**
- Sidebar gating works (Grace sees admin pages, Tanaka sees /engagement/team only, Lily sees nothing).
- Local typecheck (`cd apps/web && npx tsc --noEmit`) clean.
