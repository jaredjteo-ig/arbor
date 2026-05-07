# User flow — Lily completes the H1 2026 pulse

**Actor:** Lily Phang, Account Manager (Sales).
**Trigger:** She receives an email "Central Solutions: 2-minute pulse
check-in (closes 21 May)" while waiting for a meeting to start.
**Goal:** Complete the survey on her phone before the meeting.

## Path A — tokenised email link (likely path)

### Step 1 — open the email

| What Lily sees / does                                                        | What the system does                             |
| ---------------------------------------------------------------------------- | ------------------------------------------------ |
| Subject: "Central Solutions: 2-minute pulse check-in (closes 21 May)"        |                                                  |
| Body: "Hi Lily, your responses are anonymous. Tap below to share your view." | Email rendered with org branding + tokenised URL |
| Taps "Open survey" link → opens `/engagement-survey/<token>` on her phone    | Public route mounts                              |

### Step 2 — preflight + render

| What Lily sees / does                                                | What the system does                                                 |
| -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Brief loading state (under 1 second)                                 | Page mounts; calls `GET /public/{token}/validate`                    |
| Page header: "H1 2026 Pulse · Anonymous · 4 questions · ~90 seconds" | Validate returns `{ok: true, is_anonymous: true, triggered_at: ...}` |
| First question rendered (1 Likert)                                   | Page calls `GET /public/{token}/render` to fetch sections JSON       |

**Value moment:** the time-estimate ("~90 seconds") sets expectations
honestly. Anonymous tag visible up-front so Lily knows what she can say.

### Step 3 — answer the questions

| What Lily sees / does                                                       | What the system does                          |
| --------------------------------------------------------------------------- | --------------------------------------------- |
| Q1 (Likert): "How are you feeling about work this week?" — taps 4           | Local state                                   |
| Q2 (eNPS 0-10): "Would you recommend this team?" — taps 8                   | Local state                                   |
| Q3 (long text): "What's getting in your way right now?" — types 2 sentences | Auto-grows; max 2000 chars                    |
| Q4 (multi-select): pain points "workload" + "growth"                        | Chips toggle                                  |
| Submit button enables when required q's filled                              | Same gating logic as appraisals (round-7 P43) |

**Value moment:** mobile-friendly inputs, no scrolling juggling. The
Submit button label is honest ("Submit anonymous response") so Lily
knows what's about to happen.

### Step 4 — submit

| What Lily sees / does                                                                                                                                  | What the system does                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Taps Submit                                                                                                                                            | `POST /public/{token}/submit` with `{q1: 4, q2: 8, q3: "...", q4: ["workload", "growth"]}`                                                                    |
| Page transitions to "Thank you" view                                                                                                                   | Backend stores survey_payload, computes likert_scores `{q1: 4}`, derives themes `["workload", "growth"]`, zeroes employee_id (anonymous), stamps submitted_at |
| "Thank you" copy: "Your responses are anonymous and will help us improve. Aggregated themes are shared with leadership; individual responses are not." | Reassurance + transparency                                                                                                                                    |
| Cannot resubmit — token now reads "already submitted"                                                                                                  | If she taps the original email again, preflight returns `reason: "already_submitted"`                                                                         |

**Value moment:** the thank-you copy reinforces the anonymity contract.
Lily closes the tab confident her response counted.

## Path B — in-app

Same flow but landed via `/my-engagement-surveys` after Lily logs in
to do something else. The pending card on `/my-dashboard` ("1 pulse
open · closes in 3 days") prompts her.

| What Lily sees / does                                            | What the system does                                                                                                                      |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Lands on dashboard, sees pulse card                              | `/my-dashboard` calls `GET /engagement-surveys/my-pending`                                                                                |
| Clicks "Start" → routes to `/my-engagement-surveys/[id]/respond` |                                                                                                                                           |
| Same form as path A                                              | In-app variant uses Bearer auth instead of token; backend still creates the same response row, marks employee_id=0 if survey is anonymous |
| Submits                                                          | `POST /my-responses/{id}/submit`                                                                                                          |

**Equivalence:** path A and path B converge on the same DB row. The
only difference is which authn method is used.

## Failure modes Lily might hit

| Failure                                                 | System response                                                                                              |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Token expired (HR auto-closed the survey)               | Preflight `reason: "closed"` → "This survey has closed. Thanks for your time."                               |
| Token tampered with                                     | Preflight `reason: "invalid_or_expired"` → friendly amber empty state                                        |
| Resumed mid-way (closed tab, reopened)                  | Form is stateless — re-fills empty; she retypes. Acceptable for 90-sec survey.                               |
| Missed required question, taps Submit                   | Inline validation; submit disabled until filled. No silent-disabled.                                         |
| Network drops during submit                             | Frontend retries once with exponential backoff; if still failing, "Could not submit. Refresh and try again." |
| Tries to submit an anonymous survey via the in-app path | Backend ignores the authenticated user's identity; sets employee_id=0 anyway.                                |

## Anonymity contract — what Lily can verify

These commitments must be true and visible:

1. The "Anonymous" badge is shown on the page header and email subject.
2. The thank-you copy explicitly states "individual responses are not
   shared with leadership."
3. If she views the same survey on the admin side (impossible for
   employees, but verifiable in a security review), her individual
   response is rendered as "Anonymous", not her name.
4. She cannot identify herself by what she wrote — there's no name
   field, no "submitted by" line, no IP-correlation surfaced in the UI.

These four invariants form the regression test
`tests/regression/test_engagement_anonymity.py` referenced in the
data-model plan.

## Time budget

- Open email → form rendered: ≤2s
- Form interaction: ≤90s for a 4-question pulse
- Submit → thank you: ≤1s

If actual measurements blow these budgets in P1, the demo loses
credibility. Track in the Playwright walk script.
