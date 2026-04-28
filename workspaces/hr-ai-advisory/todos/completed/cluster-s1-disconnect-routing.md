# Cluster S1-T5 — Google Calendar Disconnect Routing Fix

**Source:** session-1-demo-readiness.md (Round-13 H — value-auditor walkthrough)
**Status:** complete
**Date:** 2026-04-28

## Problem

Clicking "Disconnect" on the Google Calendar settings card returned a fake-success
response without actually revoking OAuth tokens at Google or deleting the stored
`GoogleCalendarConnection` row.

**Root cause:** route shadowing. FastAPI matches routes in registration order. The
generic `integrations` router (mounted at `/integrations`) declares a catch-all
`POST /{provider}/disconnect` and was registered BEFORE the dedicated T-R055
`integrations_calendar` router (mounted at `/integrations/google-calendar`). Every
request to `POST /integrations/google-calendar/disconnect` was therefore handled
by the generic handler with `provider="google-calendar"`, which only does an
in-memory store removal — never touching `oauth.disconnect()`, never revoking
tokens at Google, never deleting the persisted row.

## Fix

Two-layer defence:

1. **Structural (Option B):** in `src/hr_advisory/api/platform.py`, register
   `integrations_calendar_router` BEFORE `integrations_router`. FastAPI now
   matches the dedicated `/integrations/google-calendar/disconnect` route first.
2. **Defence-in-depth (Option A):** in `src/hr_advisory/api/routers/integrations.py`,
   the generic `disconnect_provider_post` handler now refuses requests where
   `provider == "google-calendar"` with a 404 telling the caller to use the
   dedicated route. This catches accidental future regressions in router
   registration order — instead of silently fake-succeeding again, the failure
   is loud.

## Files Touched

- `src/hr_advisory/api/platform.py` — re-ordered router registration; added
  comment explaining why the order is load-bearing.
- `src/hr_advisory/api/routers/integrations.py` — added a small allowlist
  (`_DEDICATED_DISCONNECT_PROVIDERS = {"google-calendar"}`) that returns 404
  before any in-memory store mutation runs.
- `tests/regression/test_round13_disconnect_routing.py` — new permanent
  regression suite (3 tests).

NOT touched (per scope): `routers/integrations_calendar.py` (T-R055 handler is
correct), recruitment / onboarding / auth routers, frontend.

## Verification

`tests/regression/test_round13_disconnect_routing.py` — 3 tests, all pass:

1. `test_google_calendar_disconnect_invokes_dedicated_handler` — `POST
/integrations/google-calendar/disconnect` returns the T-R055 shape
   (`{"disconnected": True}`), and the seeded `GoogleCalendarConnection` row
   is deleted via `dataflow_crud.delete`.
2. `test_generic_disconnect_still_works_for_other_providers` — `POST
/integrations/xero/disconnect` still hits the generic handler and returns
   the `{"message": ..., "provider": "xero"}` shape.
3. `test_generic_disconnect_refuses_google_calendar_directly` — direct
   invocation of the generic function with `provider="google-calendar"`
   raises `HTTPException(404)` with the dedicated-route pointer in the
   detail.

Test run (isolation):

```
============================= test session starts ==============================
tests/regression/test_round13_disconnect_routing.py::test_google_calendar_disconnect_invokes_dedicated_handler PASSED
tests/regression/test_round13_disconnect_routing.py::test_generic_disconnect_still_works_for_other_providers PASSED
tests/regression/test_round13_disconnect_routing.py::test_generic_disconnect_refuses_google_calendar_directly PASSED
======================== 3 passed, 3 warnings in 3.06s =========================
```

## Notes

- Initial attempt with Option A alone (the 404 guard) was insufficient because
  FastAPI's route matcher does not fall through from one router to another after
  the prefix matches; once the generic router accepts the path it owns the
  response. Test #1 caught this and forced the structural reorder.
- The 404 guard is retained as defence-in-depth: if a future change accidentally
  re-orders routers, the failure surfaces immediately instead of regressing into
  another fake-success.
