# M5 — Frontend: employee pages (round-3 revised)

**Source plan:** `02-plans/03-frontend-and-phasing.md` §Frontend pages — employee, plus `02-plans/04-product-revision-round3.md`.

Round 3 dropped the public tokenised page entirely (engagement is
in-app only) and added the **loop-closing card** at the top of
`/my-engagement-surveys` to show employees what came of their last
response.

## T50 — `/my-engagement-surveys` page (with loop-closing card)

- **Sidebar:** add "My Engagement" link to the employee sidebar
  (under My Inventory, before Advisory). Visible to all authenticated
  users; backend gates content.
- **Page sections (top to bottom):**
  1. **Loop-closing card** (NEW round-3) — calls `/my-loop-closing`. Shape:
     - Headline: "Last pulse, your team raised **{top_theme}**."
     - Action body: "{action_taken.headline}" — e.g. "Learning budget pilot launched May 1." If `action_taken=null`: "HR has seen this — actions in progress."
     - Linked goal: small chip "→ {linked_goal_label}" with link to `/goals/{id}`.
     - Next-pulse anchor: "Next pulse will ask: {next_pulse_anchored_question}" — sets expectation for what's coming.
     - **Conditional render:** hide if `last_pulse_closed_at` is null (no pulses yet).
  2. **Pending check-ins** (cards) — calls `/my-pending`. Each card shows: survey name, ~time-to-complete, deadline, "Start" button.
  3. **History** (collapsed accordion below) — calls `/my-history`. Lists past submissions ONLY for identified-tier surveys (per T31). Each row links to a read-only view of the submitted payload.
- **Empty states:**
  - Pending empty: "No pending check-ins. We'll let you know when your team has a new pulse."
  - History empty: "Your past responses appear here for surveys where your responses were identified. Anonymous and pseudonymous responses do not show up in your history."
- **Acceptance:** Lily lands on the page, sees the loop-closing card showing the seeded "growth → L&D pilot" action, and one pending pulse below it. Clicking Start navigates to the form.

## T51 — `/my-engagement-surveys/[response_id]/respond` form

- **What:** In-app form. The ONLY engagement-survey form path at v1
  (no public tokenised route).
- **Routing:** path key is `response_id`, NOT `survey_id` (per m4 from
  round-1 — prevents URL-based probing of other employees' responses).
- **Render:** GET `/my-responses/{response_id}/render` to fetch
  `template_sections_snapshot`; render with shared survey components
  (M0 T02).
- **Submit:** POST `/my-responses/{response_id}/submit`. CSRF header
  - `Idempotency-Key` set (Z11, Z08). On success, mark related
    notification resolved.
- **Anonymity badge** (round-3 revised copy):
  - **Identified:** "Your name will be visible to HR." Yellow chip.
  - **Pseudonymous:** "Your name is hidden. Your responses across surveys can be tracked as a trend, but never traced back to you. Free-text comments may still be readable to HR — keep them general if you want full privacy." Blue chip.
  - **Anonymous:** "Your name is hidden. No trend tracking. Free-text comments may still be readable to HR — keep them general if you want full privacy." Green chip.
- **Time estimate:** computed from question count (Likert q × 5s + text q × 20s + multi q × 8s, ceiling to nearest 30s).
- **Submit progression:** disabled-with-help-text gating (P43); shows "Fill in question 3 to submit" inline while incomplete.
- **Acceptance:** Lily completes a 4-question pulse in ≤90s; submit redirects to `/my-engagement-surveys` with green toast; loop-closing card visible during the next pulse cycle.

## T52 — `/my-dashboard` pending-surveys card

- **What:** Add a card to the employee dashboard showing pending engagement surveys.
- **Conditional render:** only when `my-pending` returns ≥1 entry.
- **Card content:** "X pending check-in(s) · closes in N days" with "Open" button → navigates to `/my-engagement-surveys`.
- **Notification badge:** the dashboard alerts/unread-count fetch (per round-7 P46) reads engagement notifications via the existing `Notification` feed; the badge increments per pending engagement row.
- **Acceptance:** Lily's dashboard shows the card; clicking opens the list. Badge count matches `len(my-pending)`.

## T53 — Removed in round 3

The original public route `/engagement-survey/[token]` is **dropped**.
Engagement is in-app only. Exit interviews keep their public route at
`/exit-survey/[token]` unchanged.

## T54 — Shared survey components (T02 deliverable)

Already enumerated in M0 T02. Listed here to remind that M5 cannot
ship without it.

## T55 — Translation strings

- **What:** Engagement survey UI uses ~12 user-visible strings. Add to i18n catalog (`apps/web/src/lib/i18n/`) for English / Mandarin / Malay / Tamil.
- **Strings to localise:**
  - "Engagement", "Pending check-ins"
  - The three anonymity-badge copies (revised round-3 above)
  - "Your name will be visible", "Submit response", "Thank you"
  - "Last pulse, your team raised X" (loop-closing card)
  - "HR has seen this — actions in progress" (loop-closing fallback)
  - "Next pulse will ask:" (loop-closing card)
  - "1 pulse open · closes in N days"
  - Empty-state copies
- **Defer to v2 if tight:** Mandarin/Malay/Tamil ship as English-fallback for P1.
- **Acceptance:** strings present in all 4 catalogs; switching language updates them; no hardcoded English.

## T56 — Lily route boundary smoke (Z20)

- **What:** Playwright smoke as Lily — confirm `/engagement` returns 403 (or sidebar hidden) AND `/my-engagement-surveys` returns 200.
- **Acceptance:** test pinned; engagement leakage to employees caught in CI.

## T57 — Accessibility scan (Z18)

- **What:** axe-core scan returns zero serious violations on `/my-engagement-surveys` and the in-app form. Likert5 = `role="radiogroup"`. EnpsScale = `role="radiogroup" aria-label="Net promoter score 0 to 10"`. Loop-closing card has appropriate landmark.
- **Acceptance:** axe-core in Playwright suite returns 0 serious.

## Dependencies

- T50 → T51 (Start button routes to form).
- T50 → T38 (loop-closing endpoint).
- T51 → M0 T02 (shared components).
- T51 → T31 (in-app submit).
- T52 → T50 (card links to list page).
- T56, T57 → all of M5.

## Acceptance gate for M5

- Employee lands on `/my-engagement-surveys`, sees loop-closing card showing what came of last pulse.
- Employee can complete a survey via in-app path in ≤90s.
- Empty states friendly (not error-flavoured).
- Anonymity badge with revised copy visible at every step.
- Local typecheck clean.
- Lily route boundary smoke green.
- axe-core scan zero serious violations.
