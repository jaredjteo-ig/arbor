# T223 — Chat-style Company Onboarding (Cluster 7b)

**Status:** Implemented (beta, opt-in via Settings)
**Branch / HEAD baseline:** `3440ee0`
**Date completed:** 2026-04-28

## Summary

Added a conversational alternative to the existing form-based company
onboarding. Users can opt in via Settings -> Experimental Features ->
"Chat onboarding" (default off). When enabled, the auth onboarding
page renders a chat surface where the Arbor agent collects the
company name, industry sector, headcount range, and foreign-worker
presence one field at a time, then creates the company profile via
the existing `/profile` endpoint.

The form-based path (`CompanySetupModal`, `CompanyProfileStep`) is
left fully intact for users who don't opt in.

## Files Touched

### Backend

- `src/hr_advisory/api/routers/shadow.py`
  Added a deterministic, LLM-free state-machine endpoint:
  - `POST /shadow/onboarding/chat` — kicks off / advances the flow.
  - Helpers: `_chat_onboarding_match_sector`,
    `_chat_onboarding_match_headcount`, `_chat_onboarding_match_yes_no`,
    `_chat_onboarding_prompt`.
  - States: `name -> sector -> headcount -> foreign_workers -> confirm -> done`.
  - Stateless: the frontend echoes the accumulated `fields` dict on
    each turn so no PACE session / cooldown / undo machinery is required.
  - Reuses `check_rate_limit` (per-user) and `get_current_user` auth.
  - Caps answers at 200 chars; strips control chars from name input.

### Frontend

- `apps/web/src/components/onboarding/ChatOnboarding.tsx` (new)
  - Uses `ChatBubble` + `ChatInput` from the design system.
  - Suggestion chips per step (industries, headcount ranges, yes/no).
  - Animated dots while waiting; "Creating your company..." while
    finalising.
  - On `done`, calls `profileApi.create()` and `refreshUser()`, then
    fires `onComplete`.
  - Inline error banner for transport-level failures, soft system
    bubbles for clarification when the backend returns `error`.

- `apps/web/src/components/onboarding/index.ts`
  Re-exports `ChatOnboarding` and `ChatOnboardingResult`.

- `apps/web/src/services/api/shadow.ts`
  Added `shadowApi.onboardingChat(step, answer, fields)`.

- `apps/web/src/app/(auth)/onboarding/page.tsx`
  Reads `localStorage["arbor.chat-onboarding"]` and renders
  `ChatOnboarding` instead of the four-step form when the flag is on.
  On completion the user is routed to `/my-dashboard` (we skip the
  rich Compliance Snapshot here because the chat flow does not collect
  the detailed local/PR/EP/SP/WP breakdown that snapshot needs — see
  "Not in scope" below).

- `apps/web/src/app/(dashboard)/settings/page.tsx`
  Added an "Experimental Features (Beta)" `AppCard` with a
  `ToggleSwitch` for chat onboarding. Persists to `localStorage`
  under the key `arbor.chat-onboarding`. Shows a toast confirming
  the change.

### Tests

- `tests/unit/test_chat_onboarding.py` (new)
  78 unit tests covering:
  - Sector matching (canonical, alias, substring, unknown, empty).
  - Headcount matching (range strings, raw numbers, edge cases).
  - Yes/No matching (positive/negative variants, ambiguous returns
    None, prefix phrases).
  - Prompt generation (Arbor prefix, name interpolation, summary
    rendering, foreign_workers true/false).
  - State-machine integrity (steps tuple shape, every step has a prompt).

  All 78 tests pass via `.venv/bin/python -m pytest
tests/unit/test_chat_onboarding.py` (1.21s).

## Not In Scope

These were intentionally deferred to keep the patch minimal and
avoid blast radius on the form path:

- **No LLM judgement on answers.** The state machine uses keyword /
  alias / regex matching. We do not call the intent classifier
  (gpt-5-mini) for chat onboarding — it is conversational UI sugar
  over the same fields the form collects, not a free-form interview.
- **No PACE preview / cooldown / undo.** Onboarding creates the very
  first company the user owns, so a "Are you sure?" gate would feel
  redundant. The `confirm` step inside the chat is the equivalent
  approval gate.
- **No detailed headcount breakdown.** The form path collects
  local / PR / EP / S Pass / WP counts; chat collects only a single
  range bucket. As a result, the chat path skips the Compliance
  Snapshot step (which requires the breakdown) and routes straight
  to the dashboard. The compliance snapshot remains accessible via
  the dashboard cards. Future work could extend the chat state
  machine with a "tell me about your workforce mix" step.
- **No CompanySetupModal changes.** The dashboard modal continues to
  use the form. Switching it to chat is a separate piece of work
  (and not requested in T223).
- **No i18n strings added.** Cluster 9 owns translation work; all
  prompts ship in English for now.
- **No backend persistence of conversation transcript.** The
  endpoint is stateless and does not write to the observation store
  or memory store. If we later want to reconstruct the conversation
  for support / analytics, we'd persist (user_id, step, answer) on
  each turn.

## Manual Verification Plan

(For QA when the cluster is integrated.)

1. Sign up as a new user. Onboarding should show the standard
   four-step form.
2. Log in, go to Settings -> Experimental Features, toggle "Chat
   onboarding" on. Confirm toast appears.
3. Sign out, sign up as a different user. Onboarding should show
   the chat surface ("Set up with Arbor — beta").
4. Walk through the chat: type "Acme Pte Ltd" -> click "Technology"
   chip -> type "30" (matches 26-50) -> click "No" -> click "Yes".
   Should see "Creating your company..." then the dashboard.
5. Verify a company profile was created via `GET /profile/{id}`.
6. Toggle the flag back off; confirm subsequent signups see the
   form again.

## Test Results

- New tests: `tests/unit/test_chat_onboarding.py` -- 78 / 78 passing.
- No existing tests modified.
- Followed the test-once protocol; did not run the full suite.
