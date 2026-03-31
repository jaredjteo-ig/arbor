---
type: DISCOVERY
date: 2026-03-31
created_at: 2026-03-31T17:35:00+08:00
author: agent
session_id: arbor-session-10
session_turn: 30
project: arbor
topic: CSRF middleware was the root cause of 37 integration test failures
phase: implement
tags: [testing, csrf, nexus, integration-tests]
---

# CSRF Middleware Blocked All POST TestClient Requests

## Discovery

37 integration tests were returning 403 "CSRF validation failed" instead of expected status codes. Root cause: the NexusEngine SAAS preset adds CSRF middleware that validates the `Origin` header on POST/PUT/DELETE/PATCH. Starlette's `TestClient` does not send an `Origin` header (it's not a browser). With `cors_origins="http://localhost:3000"`, the middleware sets `allow_missing_origin=False`, rejecting all non-browser requests.

## Fix

Set `cors_origins="*"` in test settings fixtures only. When origins include `"*"`, the CSRF middleware sets `allow_missing_origin=True`, allowing non-browser clients (TestClient, curl, CI runners) to make requests.

## Impact

- 37 previously failing tests now pass
- Production CSRF protection is unchanged
- The fix is confined to 4 test files

## For Discussion

1. If the SAAS preset changes CSRF behavior in a future Nexus release, these tests could break again. Should we add a dedicated `NexusEngine.builder().preset(Preset.TEST)` that disables CSRF entirely?
2. The 335 remaining skipped tests all need PostgreSQL. If we set up CI with Postgres, would any of them also hit CSRF issues, or is the `cors_origins="*"` fix already applied to those files?
