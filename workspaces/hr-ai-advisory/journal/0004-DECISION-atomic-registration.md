---
type: DECISION
date: 2026-03-31
created_at: 2026-03-31T17:30:00+08:00
author: co-authored
session_id: arbor-session-10
session_turn: 25
project: arbor
topic: Atomic registration — user + company in one API call
phase: implement
tags: [registration, auth, company-creation, onboarding]
---

# Atomic Registration: User + Company Created Together

## Decision

Registration now accepts `company_name` and atomically creates both a User and Company in a single `/auth/register` call. The JWT returned immediately includes `company_id`, so the frontend can redirect straight to `/dashboard`.

## Alternatives Considered

1. **Keep two-step flow** (register → manual company creation on /onboarding) — Rejected. Users who close the browser after step 1 are stuck in limbo with no company. The onboarding page assumes company creation succeeds but has no guarantee.

2. **Force onboarding before dashboard access** — Rejected. Adds friction and creates the same limbo state if interrupted.

3. **Create company server-side with default name** — Rejected. User should name their own company.

## Implementation

- `AuthService.register_user()` gains `company_name` parameter
- New `_create_company_for_registration()` private method handles company + seeding
- Company creation is try/except wrapped — if it fails, user is still created (graceful degradation)
- Frontend signup form adds "Company name" field (required)
- Frontend redirects to `/dashboard` instead of `/onboarding`
- 5 unit tests cover: happy path, backward compat, existing company_id, failure resilience, empty string

## For Discussion

1. The company_name field is now required on the signup form. If we later add Google OAuth signup, how does company creation work when there's no form?
2. If company creation fails silently (try/except), the user lands on /dashboard with no company — same limbo state. Should we retry or force the user to create one?
3. The old /onboarding page still exists. Should it be removed, or repurposed for profile completion?
