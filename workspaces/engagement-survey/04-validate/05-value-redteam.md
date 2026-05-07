# Value Red-Team — Engagement Survey (Round-3)

**Persona:** Jennifer Liu / a Singapore SME owner running a 28-employee company. She has already evaluated Lattice, Officevibe, CultureAmp Skills Coach, and a local SG vendor.

**Method:** Read every file the buyer pitch claims delivers value, plus the seed and the trend/team/action endpoints. Cross-checked promises in `04-product-revision-round3.md` against the seeded narrative and the rendered UI behaviour.

## 1. Headline verdict

**Conditional sign — but not yet.** The skeleton is genuinely better than 3 of the 4 tools she's seen at this price point: trend hero, accept-and-create-goal, and the loop-closing card are real product instincts and they are wired through end-to-end. The L&D pilot story (3.8 → 3.2 over six pulses, action accepted, linked goal #X, next-pulse anchored question) is the killer demo and it actually works in seeded data.

But there are three demo-day blockers that, in a live pitch, would surface as "wait, is this real?" moments. None are fundamental — all are 1-2 hour fixes. **At 28 employees, two of the six promises (Manager view, By-cohort breakdown) will say "n<5, suppressed" most of the time, which a buyer will read as "this product wasn't built for me."**

## 2. Per-promise scorecard

| #   | Promise                                 | Verdict                           |
| --- | --------------------------------------- | --------------------------------- |
| 1   | Trend hero (not snapshot)               | **DELIVER**                       |
| 2   | Action loop (1-click create-goal)       | **PARTIAL**                       |
| 3   | Manager view in P1                      | **MISS for 28-emp SME**           |
| 4   | Loop-closing card with sincere fallback | **DELIVER** (with one trust risk) |
| 5   | Three-tier anonymity                    | **DELIVER**                       |
| 6   | TAFEP/FWA-aware suggested actions       | **PARTIAL**                       |

### Promise 2 — Action loop. PARTIAL.

The product pitch says "one-click 'create goal' wiring the finding to the existing Goals module." The actual flow is 5 decisions (open modal, edit text, type next-pulse question, decide on goal toggle, click Accept).

**Worse: the modal does not show the goal title preview before submission.** Whatever HR types as the action becomes the goal title prefixed with `Engagement:`. The seeded goal title is a beautifully written "Q2 Engineering L&D — every IC has approved budget by end of Q2" but the live demo flow produces "Engagement: Launch L&D pilot with a per-head learning budget for the cohort." **Demo and live produce different-looking outputs** — exactly what a CFO will spot.

**Fix priority (1-2 hours):** add a "Goal title" input field to the modal, defaulting to a more concise format.

### Promise 3 — Manager view. MISS for 28-employee SME.

Tanaka (a 6-report manager) needs all 6 of his reports to have submitted to clear the n>=5 gate after self-exclusion. With 78% submission rate, that's 4.68 — below threshold most of the time. **On a 28-person SME, most line managers will see the suppression message most of the time.**

**Mitigation paths, in order of preference:**

1. Show themes-only to managers when n=3 or 4 (PDPA-defensible since themes don't identify individuals).
2. Lower MIN_COHORT_SIZE to 3 for manager view ONLY (with banner). Requires legal review.
3. Reframe the manager view as a quarterly rollup, not a weekly habit.
4. Bundle teams: suggest "skip-level rollup" automatically when team < 5.

### Promise 4 — Loop-closing card. DELIVER (with trust risk).

The card itself is the strongest piece of UX copy in the feature. Lily on her phone reads "Last pulse, your team raised growth. HR did: Launch L&D pilot with a per-head learning budget for the cohort. → Linked to: Q2 Engineering L&D" and feels heard.

**The risk: the fallback when no action exists.** "HR has seen this — actions in progress" can structurally lie. The card shows whenever there's a closed pulse with a top theme, regardless of whether HR has actually opened the dashboard. **Fix:** track an HR "viewed" timestamp and only flip to "in progress" once an HR user has opened the survey detail page.

**Also:** `compute_loop_closing_payload` picks an action by **substring match** of the theme inside `finding_summary` or `suggested_action_text`. Brittle. On the seed it works because the strings match. In production it will silently fail to surface valid actions.

### Promise 6 — TAFEP/FWA suggested actions. PARTIAL.

The 18 strings are TAFEP-neutral but **abstract**. "Audit promo cycle clarity" — what does HR actually DO Monday morning?

**The legal-review constraint is real.** The fix is to ship richer LLM-driven actions at P3 — and in P1 to lower expectations. **Change the panel header from "Suggested actions:" to "Discussion starters:"** — 1-word copy change converts an over-promise into an honest one.

## 3. Demo-day gotchas

- **G1**: "By cohort" tab on a 28-employee company is mostly suppressed. Walk Eng + Ops only in demo.
- **G2**: Trend hero "All staff" view is flat-ish — Sales offsets Eng's decline. Auto-default the dropdown to lowest-scoring cohort.
- **G3**: "Accept" modal creates a verbose goal title (`Engagement: Launch L&D pilot with...`) — looks ugly compared to seeded goal.
- **G4**: Manager view 403 for Grace (admin with no reports). Show preview/sample state instead of error.
- **G5**: Loop-closing card on Lily stays anchored on last closed pulse until the open pulse closes. Demo-er must explain.
- **G6**: eNPS without context. Add tooltip "Above 30 is excellent, 0-30 healthy, below 0 needs attention."

## 4. Single biggest risk

**The manager view doesn't work for SG SMEs at 28-employee scale, and the round-3 plan promises it as a P1 differentiator.**

Without one of the mitigations listed above, the manager-view promise is a rope-a-dope: prominent in the pitch deck, dead in the actual product. A skeptical buyer running through the manager view with a real team size (4-7 reports, 75-85% response rate) and getting the friendly suppression will register: "this product was designed for 200-employee teams and the SME experience is bolted on."

## 5. Single biggest strength

**The L&D pilot story in the seed is a complete, verifiable transformation narrative.**

1. `/engagement` → trend chart shows Engineering descending 3.8 → 3.2 over six pulses
2. Click latest closed pulse → action panel shows "Engineering scored 2.1 on growth"
3. Already-accepted card shows "Launch L&D pilot" → linked to Goal #X with 25% progress
4. Anchored next-pulse question
5. Open `/my-engagement-surveys` as Lily → loop-closing card mirrors the same story
6. Cross-stage panel (P2) ties resignations back to growth

**Six surfaces, one story, all wired through real records.** No other pulse-survey vendor at this price point can show this. The product instinct in round-3 was the right call. The execution has gaps but the spine is right.
