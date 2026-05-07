# Product brief — Employee Engagement Surveys

**Date**: 2026-05-07
**Source**: User-submitted ask after the round-7 redteam closure of obayashi.

## What the user asked for (verbatim)

> An employee engagement survey is a tool used to measure employees'
> dedication, motivation, sense of purpose, and enthusiasm for their
> work and organization. These surveys help leaders identify strengths,
> uncover areas for improvement, and inform strategies to enhance
> productivity and retention. Key focus areas often include leadership,
> team dynamics, professional growth, and alignment with company goals.
>
> Common methodologies: **Gallup Q12** (12 standardised questions),
> **Trust Index™ Survey** (Great Place to Work — credibility, respect,
> fairness, pride, camaraderie), **Pulse Surveys** (short, frequent
> check-ins).
>
> Sample questions: "I know what is expected of me at work." / "I have
> the materials and equipment I need to do my work right." / "At work,
> my opinions seem to count." / "I have a best friend at work." / "What
> is one thing your manager does that has a positive impact on you?"
>
> Per Gallup's 2026 report, only 20% of the global workforce felt
> engaged in 2025.
>
> **For this demo**: HR creates questions (template or freeform), sends
> to all staff or subsections, drafts the questionnaire, collects
> responses, generates reports for management. Cross-reference with
> exit interviews / appraisals / goals data for lifecycle insight.

## Core capabilities (HR-perspective)

1. Build a survey template — pick from a library (Gallup Q12 paraphrase,
   Pulse, custom) or compose from scratch.
2. Define question types — Likert 1-5, single-select, multi-select,
   short text, long text.
3. Target a cohort — all staff, by department, by role, by tenure band,
   by manager, ad-hoc selection.
4. Configure delivery — anonymous vs identified, schedule (one-off /
   weekly pulse / monthly / quarterly), open window.
5. Send via the platform — in-app notification + tokenised public link
   for those without active sessions.
6. Track participation — % response, days since launch, reminder cadence.
7. Read aggregated results — Likert distribution, theme tally on
   free-text, heat-map per criterion / per cohort.
8. Drill into individual responses (when not anonymous) — same
   expand-row pattern as exit interviews.
9. Export — CSV / PDF report for management distribution.
10. Cross-stage view — engagement themes alongside exit-interview
    themes and retention-risk drivers in the lifecycle dashboard.

## Core capabilities (Employee-perspective)

1. See pending surveys on `/my-dashboard` (badge count + card).
2. Click into `/my-engagement-surveys` and complete in-app.
3. Receive a tokenised email/Slack link as a fallback.
4. Submit; see a "thank you" confirmation; cannot edit after submit.
5. View own past submissions (when not anonymous) — basic dignity.

## Out of scope for v1

- Real-time sentiment dashboards (overkill for SME use case)
- ML-driven theme clustering (the existing keyword sweep + LLM theme
  derivation is sufficient for v1)
- 360 reviews (different problem; lives under appraisals)
- Slack / Teams integration (defer to v2)
- Per-cohort tokenized links with embedded user_id (privacy concern in
  small companies — handle in cohort-targeting logic)

## Why this matters

- Singapore SMEs largely run engagement surveys via Google Forms with
  no integration. The platform already collects exit interviews,
  appraisals, goals, retention risk — engagement is the missing piece
  in the lifecycle view.
- Methodology credibility (Gallup Q12 paraphrase, Trust Index pillars,
  Pulse cadence) is the difference between "form-builder" and
  "engagement intelligence platform".
- Cross-stage analysis is a unique differentiator: the platform can
  correlate "low engagement on growth" → "appraisal score declining"
  → "retention risk" → "exit interview cited growth" without HR
  manually piecing it together.

## Success criteria

- Grace can launch a Gallup-Q12-style survey to all 28 employees in
  ≤3 minutes.
- Lily can complete a 5-question pulse in ≤90 seconds on her phone.
- Aggregated themes appear on the engagement dashboard within 30s of
  the last response.
- The lifecycle dashboard reward stage tile shows an engagement score
  derived from latest pulse Likert average.
- Cross-reference with exit interviews shows: "of the 3 employees who
  resigned this quarter, 2 cited 'growth' in their exit interview AND
  scored 1-2 on Q4 (career growth) in the last engagement pulse before
  resigning". This is the value-flow demo.
