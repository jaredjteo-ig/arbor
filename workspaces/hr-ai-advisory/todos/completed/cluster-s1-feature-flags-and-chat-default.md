# Cluster S1 — Server-side feature flags + default-on chat onboarding

**Tasks:** S1-T2 (server-side feature flags) + S1-T4 (chat-onboarding default-on for new signups, fixes round-13 CRIT-D4).
**Date:** 2026-04-28
**Status:** complete; 14/14 unit tests pass.

## Why

Three round-13 toggles (`arbor.ai-scorecards`, `arbor.tafep-ai`, `arbor.chat-onboarding`) lived in `localStorage`. That meant:

1. New signups never saw chat onboarding — the flag was checked before the user even had a company.
2. There was no audit trail. Owners flipped beta features in their browser only.
3. Toggling a flag on one device did not propagate.

Now the flags live on the company record, are read via a typed React hook, and chat onboarding defaults ON for any user without a company yet.

## What changed

### Backend

1. **`src/hr_advisory/models/company_user.py`** — added `feature_flags: Optional[dict]` to the `Company` model (JSON column, defaults None). DataFlow already supports JSON columns (see `salary_ranges`); no migration script is required for fresh deployments. For an existing prod database, the column will appear as NULL on next read and the router treats NULL as "all flags off" via `_normalise_flags`.
2. **`src/hr_advisory/api/routers/feature_flags.py`** — new router with two endpoints:
   - `GET /companies/me/feature-flags` — any authenticated user. Returns `{company_id, flags, defaulted}`. Always emits the full allow-list with defaults filled in so the frontend has a deterministic shape.
   - `PATCH /companies/me/feature-flags` — `require_role("owner", "platform_admin")`, rate-limited 30/min/user. Body may be a flat `{flag: bool}` map or `{flags: {...}}`. Validates against the allow-list (`ai-scorecards`, `tafep-ai`, `chat-onboarding`) before reading the row, MERGES into the existing dict, and logs an audit line at INFO level.
   - Both endpoints derive `company_id` from the JWT — never from body or path. `validate_company_access` runs as defence in depth.
3. **`src/hr_advisory/api/routers/__init__.py`** — exports `feature_flags_router`.
4. **`src/hr_advisory/api/platform.py`** — registers the router under `/companies` with the `Feature Flags` tag.

### Frontend

5. **`apps/web/src/services/api/feature_flags.ts`** — new typed client. Exports `featureFlagsApi.get()`, `featureFlagsApi.update(partial)`, plus `FEATURE_FLAG_KEYS`, `FeatureFlagKey`, `FeatureFlags`, `DEFAULT_FEATURE_FLAGS`.
6. **`apps/web/src/contexts/AuthContext.tsx`**:
   - Added `featureFlags` and `featureFlagsLoaded` to the auth state.
   - Loads flags after every successful auth event (mount, login, register, refreshUser, loginWithTokens).
   - Exposes `setFeatureFlag(name, value)` (optimistic update + rollback on failure) and `refreshFeatureFlags()`.
   - New hook export: `useFeatureFlag(name)` returns the boolean.
   - On logout, resets `featureFlags` to defaults and `featureFlagsLoaded` to false.
   - **Never** falls back to localStorage. Failing API calls leave the flag at default (false).
7. **`apps/web/src/app/(dashboard)/recruitment/settings/page.tsx`** — `AiScorecardToggle` and `AiScanToggle` now read via `useFeatureFlag(...)` and persist via `setFeatureFlag(...)`. Removed `AI_TOGGLE_KEY` and `AI_SCORECARD_TOGGLE_KEY` constants. Toggles are disabled while `featureFlagsLoaded` is false or while a save is in flight.
8. **`apps/web/src/app/(dashboard)/settings/page.tsx`** — chat-onboarding toggle now backed by `useFeatureFlag("chat-onboarding")` and `setFeatureFlag(...)`. Removed the localStorage state init and writer. Toast wording unchanged.
9. **`apps/web/src/app/(auth)/onboarding/page.tsx` (S1-T4 / CRIT-D4 fix)**:
   - Removed the `localStorage["arbor.chat-onboarding"]` read.
   - New decision tree:
     - `user == null` → wait (render form path safely).
     - `user.company_id == null` → **chat by default** (fresh signup).
     - flags loaded + flag true → chat.
     - flags loaded + flag false → form.
     - flags still loading → form (safe SSR fallback).

### Tests

10. **`tests/unit/test_feature_flags_router.py`** — 14 tests across three classes:
    - `TestGetFlags` (4): default-off, persisted merge, no-company defaulted-marker, 404 on missing record.
    - `TestPatchFlags` (7): merges (doesn't replace), accepts flat map, rejects unknown keys, rejects non-bool values, rejects non-dict body, 403 for hr_manager, 403 for employee.
    - `TestTenantIsolation` (3): both GET and PATCH only ever touch the row whose ID equals the JWT's `company_id`, owner with no company gets 403 not silent write.

## Acceptance criteria

| Criterion                                                                                     | Status                                                                                                      |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| New signup automatically lands in chat onboarding                                             | met — `user.company_id == null` short-circuits to chat                                                      |
| Existing company owner toggling a flag persists across logout, login, and a different browser | met — backed by company record, not localStorage                                                            |
| Cross-tenant: tenant A's owner gets 403/404 trying to read tenant B's flags                   | met structurally — router never accepts a target company id from the wire; covered by `TestTenantIsolation` |

## Test results

- `tests/unit/test_feature_flags_router.py`: **14 passed in 2.52s** (run once per the test-once protocol).
- Full suite **not** run per the brief.

## Operational notes

- The `feature_flags` column is added at the model level. DataFlow auto-migrates JSON columns on dev/sqlite; on the GCP Postgres deployment this MAY require a one-shot `ALTER TABLE companies ADD COLUMN feature_flags JSONB DEFAULT NULL` if DataFlow doesn't pick it up automatically. The router treats NULL as defaults so the system stays functional even if the column is missing.
- Audit logging is currently `logger.info("feature_flags.update user=... company=... changed=... merged=...")`. When the round-12 H16 audit-log table lands, swap that line for an audit-log insert.
- `setFeatureFlag` is optimistic — UI flips first, server confirms, rollback on failure. Toast wording is preserved from the previous localStorage-only flow.
- Other agents are touching `routers/integrations.py`, `routers/recruitment.py`, `seed_demo_data.py`, `NavigationSidebar.tsx`, `LocaleSwitcher.tsx`, and the i18n bundles. None of those were touched here.

## Files changed

- `src/hr_advisory/models/company_user.py` (added `feature_flags` field on Company)
- `src/hr_advisory/api/routers/feature_flags.py` (new)
- `src/hr_advisory/api/routers/__init__.py` (export)
- `src/hr_advisory/api/platform.py` (router import + registration)
- `apps/web/src/services/api/feature_flags.ts` (new)
- `apps/web/src/contexts/AuthContext.tsx` (state + hooks)
- `apps/web/src/app/(dashboard)/recruitment/settings/page.tsx` (two toggles)
- `apps/web/src/app/(dashboard)/settings/page.tsx` (chat-onboarding toggle)
- `apps/web/src/app/(auth)/onboarding/page.tsx` (default-on logic)
- `tests/unit/test_feature_flags_router.py` (new — 14 tests)
