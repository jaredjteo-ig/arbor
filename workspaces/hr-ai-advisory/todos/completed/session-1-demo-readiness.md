# Session 1 — Demo readiness (~6 hr)

**Goal:** the live demo at `http://136.110.51.61/` runs clean for the first 5–10 minutes. The buyer reaches their first hard question without hitting a screen where the product visibly fails to do what we just said it does.

**Source findings:** `04-validate/round-13-master.md` CRIT-D3, CRIT-D4 + cross-cutting "stale demo" issues + value-auditor "what 'great' looks like" target.

**Test gate:** 2340 unit + regression passing baseline; final session run must keep this number or grow it.

---

## S1-T1: Wire `t()` into NavigationSidebar [CRIT-D3]

- **What:** locale switcher exists + 4 bundles complete (173 keys × 4 locales) but the sidebar's `label:` props are hardcoded English strings, so switching to Mandarin/Malay/Tamil leaves the entire navbar untranslated.
- **Files:**
  - `apps/web/src/components/shell/NavigationSidebar.tsx` — replace each `label: "Dashboard"` etc. with `t("nav.dashboard", { defaultValue: "Dashboard" })` (or read from a key map).
- **Acceptance:**
  - Switch locale in Settings → navbar items render in the chosen language within one render frame.
  - Existing English remains identical when locale = `en`.
  - All 4 locales tested manually for visual breakage (long labels overflowing, etc.).
- **Risk:** low — pure label substitution, keys already exist.

## S1-T2: Server-side feature flags [r13 cross-cutting]

- **What:** three round-13 feature toggles live in `localStorage` (`arbor.ai-scorecards`, `arbor.tafep-ai`, `arbor.chat-onboarding`). No backend audit trail. New users / fresh browsers never see them on regardless of org config.
- **Files:**
  - `src/hr_advisory/models/company_user.py` — add `Company.feature_flags: dict` (JSON column) OR new `CompanyFeatureFlag` model. Pick whichever requires no destructive migration.
  - `src/hr_advisory/api/routers/company.py` (or a new `feature_flags.py`) — `GET /companies/me/feature-flags`, `PATCH /companies/me/feature-flags` (owner-only).
  - `apps/web/src/contexts/AuthContext.tsx` — load flags on login, expose `useFeatureFlag(name: string)` hook.
  - `apps/web/src/app/(dashboard)/recruitment/settings/page.tsx` — replace `localStorage` reads with `useFeatureFlag("ai-scorecards")` etc., write via the new API.
  - `apps/web/src/app/(dashboard)/settings/page.tsx` — same treatment for `chat-onboarding` toggle.
- **Acceptance:**
  - Toggle flips in DB on PATCH; survives logout/login.
  - Client falls back to `false` when the API call fails (no cached localStorage as the source of truth).
  - All 3 toggles use the new infrastructure.
- **Risk:** low. Add 1 regression test asserting AuthContext reads flags from API not localStorage.

## S1-T3: Refresh seed data [r13 cross-cutting]

- **What:** every audit since round 6 flags the same lifeless artefacts. Demo Admin still on probation, all candidates `pdpa_consent: false`, scorecard library empty, all 5 onboarding assignments at 0%.
- **Files:**
  - `scripts/seed_demo_data.py` — extend with:
    - Fix Demo Admin: `confirmation_status="confirmed"`, populate `department`, `start_date` ≥ 6 months ago.
    - 20 candidates → set `pdpa_consent=True`, `pdpa_consent_date=<recent>`, vary `source` (careers_page, jobstreet, referral, linkedin) by 30/30/20/20 split (not 25 even).
    - 3-5 scorecard templates: "Engineering — Senior", "Sales — Account Exec", "F&B — Operations", "HR — Specialist", "Customer Support".
    - 4-6 preboarding tasks per default template (Day -14 send offer, Day -10 collect documents, Day -7 welcome email, Day -5 workspace setup, Day -1 IT verify access).
    - Vary onboarding-assignment progress: 1 at 100%, 1 at 65%, 1 at 30%, 1 preboarding-only, 1 just-assigned.
- **Acceptance:**
  - `python scripts/seed_demo_data.py --reset` runs end-to-end on a fresh local DB.
  - Live demo at `136.110.51.61/recruitment` shows non-empty scorecard library + varied candidate sources + PDPA-consenting candidates.
  - Live demo at `136.110.51.61/onboarding` shows assignments at varied %, not all-zero.
- **Risk:** low. Wrap each new section in try/except so a partial seed doesn't abort.

## S1-T4: Default-on chat onboarding for new accounts [CRIT-D4]

- **What:** chat onboarding is gated by `localStorage["arbor.chat-onboarding"]` checked BEFORE signup. New users always see the form because their browser hasn't visited Settings yet.
- **Files:**
  - `apps/web/src/app/(auth)/onboarding/page.tsx` — instead of localStorage gate, default to `true` for users with no company yet (i.e., on the signup completion path). Keep the Settings toggle so existing users can opt out.
- **Acceptance:**
  - Fresh signup hits the chat path automatically.
  - Existing users (have a company) see the form unless they explicitly toggled chat on in Settings.
  - Settings toggle (now backed by feature flags from S1-T2) overrides both defaults.
- **Risk:** low. Coordinate with S1-T2 — the flag now lives server-side.

## S1-T5: Fix disconnect endpoint shadowing [r13 H — value-auditor]

- **What:** generic `/integrations/{provider}/disconnect` route in `routers/integrations.py` shadows the new T-R055 `/integrations/google-calendar/disconnect` and returns a fake-success response. So clicking "Disconnect" in the UI looks like it worked but Google tokens stay live.
- **Files:**
  - `src/hr_advisory/api/routers/integrations.py` — add an explicit reject for `provider == "google-calendar"` so the request falls through to the dedicated router (or move the generic disconnect to a path that doesn't shadow specific providers).
- **Acceptance:**
  - `POST /integrations/google-calendar/disconnect` reaches the T-R055 handler (verified via response shape: includes `disconnected: bool` not the generic-disconnect response).
  - Regression test: assert Google Calendar disconnect actually deletes the `GoogleCalendarConnection` row.
- **Risk:** low.

---

## Implementation order (parallel-where-safe)

Sub-agents in parallel:

1. Agent A: S1-T1 (frontend only, NavigationSidebar)
2. Agent B: S1-T2 (full-stack — backend model + endpoints + frontend hook)
3. Agent C: S1-T3 (backend script only)
4. Agent D: S1-T5 (backend only — touches `routers/integrations.py`)

Then sequentially:

- S1-T4 (depends on S1-T2's feature flag infrastructure)

Final: pytest, deploy, smoke-test live, commit + push.

## Acceptance for the session

- 2340 → ≥2350 tests passing (each task adds 1+ regression test).
- `git log` shows one focused commit per task or one combined commit per the user's preference.
- Live `136.110.51.61` demo: locale switcher translates navbar; toggles persist across browsers / sessions / users; seed data shows variety not zeros; new signup goes to chat by default; Calendar disconnect actually disconnects.
