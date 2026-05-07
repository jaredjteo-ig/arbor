# User flow — Grace launches the H1 2026 pulse

**Actor:** Grace Koh, HR Manager at Central Solutions Pte Ltd.
**Trigger:** Quarterly engagement check-in is due. The CEO asked for
a pulse before the next leadership offsite in two weeks.
**Goal:** Send a 5-question pulse to all 28 active staff, anonymous,
closes in 14 days.

## Step 1 — open Engagement

| What Grace sees / does                                 | What the system does                                 |
| ------------------------------------------------------ | ---------------------------------------------------- |
| Clicks "Engagement" in the sidebar (Management group)  | Renders `/engagement` overview, calls aggregator API |
| Hero: "No active surveys yet. Last pulse: never."      | Empty-state copy explains pulse vs annual            |
| Sees four shipped templates listed under Templates tab | Backend seeded library on first GET                  |
| Sees a primary "Launch survey" button                  |                                                      |

**Value moment:** the empty state tells Grace what to do next. The
shipped library means she doesn't have to compose 12 questions from
scratch.

## Step 2 — launch wizard, pick template

| What Grace sees / does                              | What the system does     |
| --------------------------------------------------- | ------------------------ |
| Clicks "Launch survey" → wizard step 1 of 3         | Modal opens              |
| Sees four templates with a "method" badge each      | GET /templates           |
| Hovers "Monthly pulse" — preview shows 4 questions  | Lazy-loads sections JSON |
| Clicks "Monthly pulse" → highlighted; clicks "Next" |                          |

**Value moment:** the methodology badge ("pulse", "gallup_q12") tells
her what she's picking without opening the questions.

## Step 3 — wizard, pick cohort

| What Grace sees / does                                                           | What the system does                                                 |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Sees no saved cohorts; uses the inline filter builder                            | Cohort list empty                                                    |
| Toggles "All active staff"                                                       | Live preview fires `POST /cohorts/preview` with `{all_active: true}` |
| Preview shows: 28 matched · sample names · "Anonymous reporting safe (n=28 ≥ 5)" | Cohort resolver returns matched_count + sample + anonymity_safe flag |
| Clicks "Next"                                                                    |                                                                      |

**Value moment:** the preview surfaces the anonymity threshold up
front. Grace sees green and proceeds; if she'd picked "Engineering"
(8 people) she'd still be safe; if "Management" (2), she'd see a
warning before launching.

## Step 4 — wizard, configure + launch

| What Grace sees / does                                                        | What the system does                                                                                                                |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Names it "H1 2026 Pulse — All Staff"                                          |                                                                                                                                     |
| Toggles "Anonymous"                                                           | sets `is_anonymous=true`                                                                                                            |
| Sets close date to "+14 days"                                                 |                                                                                                                                     |
| Picks recurrence "monthly" (P2 feature, hidden in P1)                         | (P1: defaults to one-off)                                                                                                           |
| Clicks "Launch"                                                               | Backend resolves cohort to 28 employee_ids, creates 28 EngagementSurveyResponse rows in pending, mints 28 tokens, queues 28 emails. |
| Sees toast "Survey launched. 28 emails queued; 28 in-app notifications sent." | Returns `{survey_id: 5, target_count: 28}`                                                                                          |
| Lands on `/engagement/surveys/5` — response count 0 / 28                      | Detail page                                                                                                                         |

**Value moment:** it took ~90 seconds. The whole launch was three
clicks (template, cohort, launch) plus a name.

## Step 5 — monitor

Two days in. Grace clicks back into Engagement → Surveys tab → her
pulse card shows 21 / 28 responded (75%). She clicks "Send reminder"
(P2 feature) — backend re-emails the 7 non-responders.

Five days in, 25 / 28. She moves on.

## Step 6 — review aggregate

Day 14, survey auto-closed.

| What Grace sees / does                                                                        | What the system does                                                   |
| --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Clicks the closed pulse → /engagement/surveys/5                                               | GET /aggregate                                                         |
| Aggregated tab shows: 25 responses, average Likert 3.8, eNPS +18                              | Aggregator returns by_question + by_cohort + enps                      |
| Hero question: "I have what I need to do my best work" — 60% strongly agree, 8% disagree      | Distribution bars per question, shipped from `<ScoreBar>` family       |
| Free text Q4 (what's getting in your way) shows themes: workload (5), growth (4), manager (3) | `_theme_tags` aggregated across responses                              |
| Switches to By cohort → Engineering 3.2, Sales 4.4, Operations 4.0                            | Per-cohort aggregation with anonymity-safe gate                        |
| Tries to expand Management cohort — sees suppression banner ("n=2, suppressed for anonymity") | Backend returns `is_anonymity_safe: false` row; UI renders a red strip |

**Value moment:** the cohort breakdown points at Engineering as the
hot spot in two clicks. No spreadsheet, no manual aggregation.

## Step 7 — cross-stage (the demo killer flow, P3)

Grace opens Lifecycle → Retain stage → "Engagement leading-indicator"
panel:

> 3 employees resigned this quarter (Rajesh, Marcus, Priya).
> 2 of them scored below 3 on Q4 (career growth) in their last
> engagement pulse before resigning. Both also cited "growth" in
> their exit interview. Pattern correlation: 67% of low-engagement
> Engineering employees cite growth on exit.

She clicks the panel → drills into one resigned employee's timeline:
their Likert trajectory, exit interview themes, last appraisal score
— all in one view.

**Value moment:** this is the only thing in the demo that no other
SaaS product on the market can do natively. It traces back to the
data-model decision to keep `likert_scores` denormalised and indexed
by employee_id.

## Failure modes Grace might hit (and how the system responds)

| Failure                                                | System response                                                                                                                   |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Cohort filter matches 0 employees                      | Preview shows "0 matched. Adjust filter or select a different cohort." Launch button disabled.                                    |
| Cohort matches 1-4 employees + anonymous toggled       | Preview shows "n=3, anonymous reporting unsafe." Launch button warns inline; Grace can override only if she un-toggles anonymous. |
| Email service down                                     | Backend launches survey but logs queued-but-undelivered emails; Grace sees a yellow banner "21/28 emails delivered, 7 retrying."  |
| Two surveys sent to the same employee in the same week | The second launch shows a "Survey overlap" warning at the preview step. Override allowed but logged.                              |
| Launching while another pulse is still open            | Detail page shows both as active; HR sees an info badge.                                                                          |
