# Round-3 product revision

**Date:** 2026-05-07.
**Trigger:** owner reviewed the milestones + Z amendments and asked
for a recommendations pass weighing employee (Lily) vs HR (Grace)
flows. Six recommendations surfaced; five accepted, one rejected.

This document supersedes the relevant sections of
`03-frontend-and-phasing.md` and the original `M3` / `M5` / `M8` / `M9`
shapes. The milestone files have been revised in-place to match.

## Decisions

### Accepted

1. **Drop public tokenised path for engagement.** Every engagement
   recipient is a current authenticated employee — the dual
   public+in-app surface adds CSRF, idempotency, rate-limit, render +
   validate endpoints, and a second failure-mode tree for marginal
   value. Engagement is **in-app only**. Public tokens stay for exit
   interviews where the recipient may have lost SSO.

2. **Manager view ships in P1.** Originally P3. Action happens at the
   manager layer; HR aggregates are board-meeting cadence. Make the
   weekly habit available first.

3. **Action loop in P1.** When HR clicks into a low-scoring cohort, the
   detail page surfaces (a) AI-suggested actions (3 templated
   suggestions), (b) one-click "create goal" wiring the finding to
   the existing Goals module, (c) auto-anchored same-question for
   the next pulse so improvement is measurable.

4. **Trend hero, not snapshot hero.** `/engagement` overview leads
   with a 6-pulse line chart per cohort, not the latest pulse's bar
   numbers. Single-pulse view is a screenshot; trend view is the
   insight that earns Grace's attention.

5. **Trim cohort builder to 3 presets + ad-hoc in P1.** All staff /
   department / new joiners <90d covers ~95% of SME pulse cohorts.
   Full filter UI (full pass_type/tenure/manager/ad-hoc combiner)
   defers to P2 if anyone asks. SMEs of 28 produce mostly n<5
   suppressed cells in any case.

6. **Cross-stage correlation moves P3 → P2.** Still ships before P3
   close, but earlier in the sequence. This rebalances P2 so it has
   demo-credible value (cross-stage panel is the USP), and frees P3
   to focus on LLM theme analysis + Slack + cross-tenant.

### Rejected

7. **~~1-question micro-pulse as monthly default.~~** Owner chose to
   keep Q12 quarterly as the cadence. No micro-pulse template ships.
   The `monthly_pulse` template stays at 4 questions (per the M1 T16
   library).

## New phasing

### P1 (M0-M7) — minimum shippable HR + employee + manager flow

| Module                         | Was P1? | Now P1? | Notes                                                                          |
| ------------------------------ | ------- | ------- | ------------------------------------------------------------------------------ |
| Token kind isolation (T01)     | Yes     | Yes     | Still shipped (exit interviews need it). Engagement does not consume.          |
| Shared survey components (T02) | Yes     | Yes     | Used by exit + engagement in-app.                                              |
| HMAC pseudonym (T03)           | Yes     | Yes     | Unchanged.                                                                     |
| Cohort resolver (T04)          | Yes     | Yes     | Unchanged.                                                                     |
| Theme tagger (T05)             | Yes     | Yes     | Deterministic. LLM swap-in deferred to P3.                                     |
| Email queue (T06)              | Yes     | Yes     | Used by both exit + engagement. In-app notifications also added (Z10).         |
| 5 DataFlow models (M1)         | Yes     | Yes     | Plus new `EngagementAction` model. Trust Index + SG SME templates moved to P2. |
| Templates CRUD (M2)            | Yes     | Yes     | Unchanged.                                                                     |
| Cohort presets + ad-hoc (M2)   | Yes     | Yes     | **Trimmed.** Full builder moved to P2.                                         |
| Launch + in-app submit (M3)    | Partial | Yes     | **Public endpoints dropped.** In-app only.                                     |
| Trend endpoint (NEW)           | No      | Yes     | `GET /surveys/trend?cohort=X&window=6_pulses` — backs the hero chart.          |
| Manager-view endpoint (NEW)    | No      | Yes     | Was P3. Pulled into P1.                                                        |
| Action endpoints (NEW)         | No      | Yes     | `GET /surveys/{id}/suggested-actions`, `POST /surveys/{id}/actions`.           |
| HR pages (M4)                  | Yes     | Yes     | Trend hero added. Manager-view tab added. Action panel on detail page.         |
| Employee pages (M5)            | Yes     | Yes     | Public route dropped. Loop-closing card added.                                 |
| Demo seed + tests (M6)         | Yes     | Yes     | Test matrix updated for in-app only.                                           |
| P1 ship (M7)                   | Yes     | Yes     | Bigger acceptance gate.                                                        |

### P2 (M8) — recurring + cross-stage + full cohort builder + exports

| Module                                | Was P2? | Now P2? | Notes                                             |
| ------------------------------------- | ------- | ------- | ------------------------------------------------- |
| Cron tick + schedules (T80, T81)      | Yes     | Yes     | Unchanged.                                        |
| Trust Index template (T82)            | Yes     | Yes     | Unchanged.                                        |
| Singapore SME template (T83)          | Yes     | Yes     | Unchanged.                                        |
| CSV export (T84)                      | Yes     | Yes     | Unchanged.                                        |
| PDF export (T85)                      | Yes     | Yes     | Unchanged.                                        |
| Reminder send (T86)                   | Yes     | Yes     | Unchanged.                                        |
| **Cross-stage correlation** (was T90) | **No**  | **Yes** | Pulled in from P3. The USP demo flow ships at P2. |
| **Lifecycle leading-indicator panel** | **No**  | **Yes** | Pulled in from P3.                                |
| **Lifecycle activity-feed entries**   | **No**  | **Yes** | Pulled in from P3.                                |
| **Full cohort builder UI**            | **No**  | **Yes** | The 5-dimension filter UI deferred from P1.       |
| **eNPS hero on lifecycle dashboard**  | **No**  | **Yes** | Pulled in from P3.                                |

### P3 (M9) — AI + integrations + cross-tenant

| Module                         | Was P3? | Now P3? | Notes                                                           |
| ------------------------------ | ------- | ------- | --------------------------------------------------------------- |
| LLM theme analysis (T94)       | Yes     | Yes     | Unchanged. Cost cap (P13).                                      |
| Slack / Teams delivery (T96)   | Yes     | Yes     | Unchanged.                                                      |
| Cross-tenant comparison (T107) | Yes     | Yes     | Unchanged. Anonymised median benchmark across opted-in tenants. |
| ~~Cross-stage correlation~~    | Yes     | **No**  | Moved to P2.                                                    |
| ~~Manager view~~               | Yes     | **No**  | Moved to P1.                                                    |
| ~~eNPS hero~~                  | Yes     | **No**  | Moved to P2.                                                    |

## What changed in the data model

### NEW: `EngagementAction` model

Lives in `src/hr_advisory/models/company_user.py`. Wires the action
loop.

```python
@db.model
class EngagementAction:
    company_id: int
    survey_id: int                  # parent survey the action came from
    cohort_label: str = ""          # e.g. "Engineering" or empty for company-wide
    finding_summary: str = ""       # one-liner what the survey showed
    suggested_action_text: str = "" # AI-suggested or HR-typed
    status: str = "proposed"        # proposed | accepted | rejected | done
    linked_goal_id: int = 0         # if HR clicked "create goal", points at Goals module
    next_pulse_question: str = ""   # text of the question to anchor in the next pulse
    next_pulse_survey_id: int = 0   # the next pulse this action will be measured against
    created_by: int
    created_at: datetime
    resolved_at: Optional[datetime]
    resolved_score_delta: Optional[float] # if next pulse showed +/- improvement
```

This model is the spine of the action loop. It:

1. Captures the finding (cohort + summary).
2. Records the chosen action.
3. Links to a Goal in the existing Goals module if HR opts in.
4. Pre-anchors the question to re-ask in the next pulse.
5. Records the resolved score delta after the next pulse closes — so
   demos can say "engineering went from 3.2 → 3.7 after the L&D
   intervention."

### NEW: `loop_closing_card_payload` shape

For `/my-engagement-surveys` employee view. Backed by an aggregator
that reads:

- The most recent closed survey for the company.
- Its top theme (e.g. "growth").
- Any `EngagementAction` with `status=accepted` AND `linked_goal_id != 0`
  for that theme.
- The action's chosen `suggested_action_text` (if Grace personalised
  it) or fallback "HR is reviewing this signal."

Returned shape:

```json
{
  "last_pulse_closed_at": "2026-04-12",
  "top_theme": "growth",
  "action_taken": {
    "headline": "Learning budget pilot launched May 1",
    "linked_goal_label": "Q2: Engineering L&D — every IC has approved budget by end of Q2"
  },
  "next_pulse_anchored_question": "How clear is your career path here?"
}
```

If no `accepted` action exists for the top theme: `action_taken` is
null and the card shows "HR has seen this — actions in progress."
Trust-preserving even when no action has been taken yet.

## What changed in the API

### Removed

- ~~`GET /engagement-surveys/public/{token}/validate`~~
- ~~`GET /engagement-surveys/public/{token}/render`~~
- ~~`POST /engagement-surveys/public/{token}/submit`~~

These are deleted from the M3 spec. Exit interview tokens still use
the equivalent endpoints under `/exit-survey/...`. The token kind
isolation work (T01, Z01) still ships — engagement just never
issues an `engagement`-kind token.

**Token kind change:** the `kind` claim in `_make_token` accepts
`"exit"` only at v1. The `"engagement"` kind is reserved for future
use (e.g. ex-employees being surveyed during alumni follow-up).

### Added

| Endpoint                                                 | Purpose                                                   |
| -------------------------------------------------------- | --------------------------------------------------------- |
| `GET /engagement-surveys/surveys/trend`                  | Returns 6-pulse trend for a cohort. Backs the hero chart. |
| `GET /engagement-surveys/team/aggregate`                 | Manager-view aggregate. Pulled in from P3.                |
| `GET /engagement-surveys/surveys/{id}/suggested-actions` | AI-suggested actions for a survey. Light Kaizen call.     |
| `POST /engagement-surveys/surveys/{id}/actions`          | Create / accept an action.                                |
| `PATCH /engagement-surveys/actions/{id}`                 | Update an action (link goal, change status).              |
| `GET /engagement-surveys/actions`                        | List actions for the company. Used in the action panel.   |
| `GET /engagement-surveys/my-loop-closing`                | Loop-closing card payload for employee dashboard.         |

### Unchanged

All admin and template / cohort endpoints.

## What changed in the frontend

### `/engagement` (HR overview)

**Before:** hero band with latest pulse score + response rate + eNPS.
**After:** hero band with **6-pulse trend chart** as the dominant
element; latest-pulse score is a small inset stat. Trend chart shows
overall + dropdown to filter by cohort.

### `/engagement/surveys/[id]` (HR detail)

**Before:** three tabs (Aggregated, By cohort, Responses) + close +
export buttons.
**After:** the same three tabs **plus** an **Action panel** at the
bottom of the page that:

- Lists 3 AI-suggested actions for the lowest-scoring cohort.
- Each action has "Accept" / "Reject" buttons.
- Accepting an action lets HR optionally one-click create a Goal
  (uses existing Goals module modal).
- Shows already-accepted actions for context.

### `/engagement/team` (NEW — manager view)

Pulled in from P3. Visible to any user with at least one direct
report. Aggregates engagement data for the manager's reports with
n≥5 gate. Self-exclusion enforced (Z26).

### `/my-engagement-surveys` (employee view)

**Before:** pending check-ins + history (identified-only).
**After:** **loop-closing card at top** showing "Last pulse you said
X. Action taken: Y." then pending check-ins, then history. The
loop-closing card is the trust-builder.

### `/my-engagement-surveys/[response_id]/respond` (employee form)

**Before:** in-app form + parallel public route via tokenised email.
**After:** in-app form **only** — no public route. Anonymity badge
copy revised:

- Identified: "Your name will be visible to HR."
- Pseudonymous: "Your name is hidden. Your responses across surveys
  can be tracked as a trend, but never traced back to you. Free-text
  comments may still be readable to HR — keep them general if you
  want full privacy."
- Anonymous: "Your name is hidden. No trend tracking. Free-text
  comments may still be readable to HR — keep them general if you
  want full privacy."

### `/my-dashboard` pending card

Unchanged from M5 T52.

### Removed

- ~~`/engagement-survey/[token]` public page~~ — never built. Saved
  effort: ~3 days frontend + ~3 days backend + the entire Z11/Z14/Z15
  CSRF/CORS/rate-limit thread.

## Token kind isolation revisited

T01 still ships because exit interviews need it. The 30-day grace
window described in Z01 still applies. The change: the `engagement`
kind is reserved and never minted in v1, so cross-replay attacks
between exit ↔ engagement become impossible by construction.

If a future feature wants to mail tokenised engagement surveys to
ex-employees (alumni cycle, NPS one year after departure), the
`engagement` kind is ready.

## Net scope delta

**Removed (vs original P1):**

- 3 public endpoints (validate/render/submit) — backend
- 1 public route page — frontend
- Z08 idempotency on public submit (engagement) — partially still
  needed for in-app submit but simpler
- Z11 CSRF on in-app — still needed (no scope change)
- Z14 rate limits on `/render`/`/validate` — gone
- Z15 CORS for public route — gone
- Z17 mobile-responsive public form — gone (in-app form still
  responsive but uses existing app shell)
- Z19 public empty-state copy — gone

**Added (vs original P1):**

- `EngagementAction` model + 5 new endpoints
- Manager-view endpoint + page (pulled from P3)
- Trend endpoint + chart hero (pulled forward)
- Loop-closing card endpoint + employee UI element
- Action panel on HR detail page
- Suggested-actions Kaizen integration (light — 3-template prompt)

**Estimated net P1 effort:** roughly equivalent. Action loop adds
roughly what the public route subtracts.

## Acceptance gate revision

P1 ship (M7 T74) acceptance criteria add:

- Trend hero renders with 6 pulses of seeded data.
- Manager view enforces n≥5 with self-exclusion.
- Action panel shows 3 suggested actions for the lowest-scoring cohort.
- One-click create-goal from action panel produces a goal in the
  existing Goals module.
- Loop-closing card on `/my-engagement-surveys` shows the seed's
  last-pulse theme + a sample action.
- ~~Public route end-to-end~~ — removed from acceptance.

## Open decisions still pending

(carried from Z30, plus new):

- **D8 (NEW):** AI-suggested-actions prompt template. Use light
  Kaizen with deterministic fallback (3 hardcoded suggestions per
  theme) if LLM call fails or budget cap trips. Confirm pattern.
- **D9 (NEW):** Action lifecycle — automatic re-ask or manual
  re-ask of the anchored question? Default: automatic for the next
  pulse only; if the action's `next_pulse_survey_id` is set, the
  next launched survey of that template auto-includes the question.
- **D10 (NEW):** Action visibility to managers vs HR-only.
  Default: HR creates actions, but assigned-manager (if linked goal
  has an owner) sees it on their team page.
