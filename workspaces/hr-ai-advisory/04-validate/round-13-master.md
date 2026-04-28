# Round 13 Master Report — Aggregate of 4 Red-Team Agents

**Generated:** 2026-04-28
**HEAD:** `3440ee0` (working tree dirty — round-13 production work uncommitted)
**Test posture:** 2326 unit + regression passing, 0 failed.
**Sub-reports:**

- `04-validate/round-13-security-audit.md` (security-reviewer)
- `04-validate/round-13-value-audit.md` (value-auditor)
- `04-validate/round-13-deep-analysis.md` (deep-analyst)
- `04-validate/round-13-code-review.md` (intermediate-reviewer)

---

## Executive verdict

**The platform is technically stronger than round 12, but the live demo is now WORSE than round 12 because the round-13 work is uncommitted and undeployed.** Eight of twelve audited features 404 on production. The single highest-leverage action is **commit + deploy**, not new code.

After commit + deploy, **3 unique CRITICALs and ~12 HIGHs remain that BLOCK production-grade shipping** — most concentrated in the new Google Calendar OAuth flow and the multi-channel CLI/MCP handler that round-12 also flagged.

---

## Severity matrix

| Severity | Source-code findings (commit-time) | Live/demo findings (deploy-time) |
| -------- | ---------------------------------- | -------------------------------- |
| CRITICAL | 3                                  | 4                                |
| HIGH     | 14                                 | 11                               |
| MEDIUM   | 22                                 | 5                                |
| LOW      | 9                                  | 4                                |

Source vs deploy split matters because the deploy-time issues unblock with a single `docker compose up -d` after a commit.

---

## CRITICAL

### Source-code CRITICALs (BLOCK before commit)

#### CRIT-S1 — Multi-channel handler tenant leak [deep-analyst]

**File:** `src/hr_advisory/api/platform.py:236, 296`
**Title:** `advisory_query_handler` AND `compliance_check_handler` still accept `company_id: int = 0` as a body parameter with no validation against the caller's session.
**Background:** This is C1 from round-12 RESURFACING. Cluster 0 rewired `advisory_query_handler` to use `AdvisoryEngine` but kept the `company_id` parameter and passed it straight through. CLI/MCP callers can ask the LLM to dump any company's data. HTTP routes are safe because they go through `Depends(get_current_user)`; these handlers don't.
**Single-tenant deploy contains the blast radius today**, but becomes a data-exposure incident the moment a second customer onboards.
**Fix:** Drop the `company_id` body parameter and read it from the trusted-channel auth context (CLI SSO, MCP transport auth). Or: assert single-tenant explicitly and document that as an invariant.

#### CRIT-S2 — Webhook URL attacker-influenced [security-reviewer C1]

**File:** `src/hr_advisory/integrations/google_calendar/sync.py` (`watch_events`) + env `ARBOR_API_URL`
**Title:** The webhook URL registered with Google for push notifications is built from `ARBOR_API_URL` environment variable with no scheme or allowlist validation.
**Exploit:** If an attacker can influence `ARBOR_API_URL` (env-var injection in a misconfigured deploy, or a supply-chain attack on a config module), Google sends future webhook payloads to a URL the attacker chose. Tokens stored in our DB are still ours, but interview-update notifications are intercepted.
**Fix:** Validate `ARBOR_API_URL` against `^https://[a-zA-Z0-9.-]+\.terrene\.foundation/?$` (or whatever the prod hostname is) at startup. Reject startup if mismatch.

#### CRIT-S3 — OAuth callback unauthenticated + no CSRF on auth-url [security-reviewer C2]

**File:** `src/hr_advisory/api/routers/integrations_calendar.py:callback`
**Title:** The OAuth callback endpoint has no auth requirement; combined with no CSRF protection on `/auth-url`, an attacker can bind their own Google tokens to a victim company.
**Exploit chain:**

1. Attacker hits `GET /integrations/google-calendar/auth-url` (no CSRF token required → tricks the victim into clicking a link, gets the signed state for victim's `company_id`).
2. Attacker substitutes their OWN Google account in the consent screen.
3. Google redirects back to `/callback?code=<attacker_code>&state=<victim_state>`.
4. Callback exchanges code → gets attacker's tokens → persists them into victim's `GoogleCalendarConnection`.
5. Victim's interviews now sync to the attacker's calendar, with attendees including real candidate emails.
   **Fix:** Bind state to user identity (include user_id in HMAC payload, verify on callback). Require `Depends(get_current_user)` on `/callback` AND match user_id from cookie/session against state's user_id.

### Live/demo CRITICALs (block ship; unblock with commit + deploy + small fixes)

#### CRIT-D1 — Stale deploy hides round-13 work [value-auditor]

8+ endpoints 404 on live: `/integrations/google-calendar/*`, `/recruitment/candidates/{id}/scorecard/generate`, `/onboarding/reminders/send-overdue`, `/shadow/onboarding/chat`. Working tree is dirty; production is at `3440ee0` from before round 13.
**Fix:** commit + push + deploy. Single action unlocks 8 findings.

#### CRIT-D2 — DOCX export 422 on live [value-auditor]

Live API returns `422 "format must be 'pdf'"` for `format=docx`. The B01 work is in source but not deployed.
**Fix:** part of CRIT-D1.

#### CRIT-D3 — i18n sidebar still English [value-auditor]

`apps/web/src/components/shell/NavigationSidebar.tsx` uses hardcoded `label: "Dashboard"` strings, NOT `t()` keys. Switching to Mandarin/Malay/Tamil leaves the entire navbar in English.
**Fix:** ~30 lines wiring `t("nav.dashboard")` etc. The keys already exist in all 4 locale bundles. (Cluster 9 agent claimed this was wired; it's not.)

#### CRIT-D4 — Chat onboarding unreachable for new accounts [value-auditor]

Beta toggle is `localStorage["arbor.chat-onboarding"]` and is checked BEFORE signup. New users always see the form flow because they haven't visited Settings yet.
**Fix:** swap to a server-side feature flag, or default the flag ON for new accounts during rollout.

---

## HIGH (deduplicated across agents)

### Calendar OAuth (T-R055) — 7 of these

| ID  | Title                                                                                                           | File                               | Source(s)                                                                         |
| --- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------- |
| H1  | OAuth tokens stored plaintext in `GoogleCalendarConnection` despite docstring claim                             | `models/google_calendar.py:21-22`  | deep-analyst, security-reviewer H3                                                |
| H2  | OAuth state HMAC reuses `JWT_SECRET_KEY` with fallback `"change-this-in-production"`                            | `oauth.py:63`                      | code-review BLOCK, security H2                                                    |
| H3  | Webhook handler doesn't verify `X-Goog-Resource-ID` against stored `channel_resource_id` (replay vector)        | `integrations_calendar.py`         | security-reviewer H4                                                              |
| H4  | Webhook patch path never reached — Google push notifications have empty bodies; handler reads body for event ID | `integrations_calendar.py:webhook` | deep-analyst (T-R055 is one-way Arbor→Google only despite agent claim of two-way) |
| H5  | `logger.exception()` on OAuth code-exchange failure can serialize the OAuth `code` via traceback locals         | `oauth.py`                         | security-reviewer H7                                                              |
| H6  | OAuth refresh log message can leak the refresh token                                                            | `oauth.py:316-322`                 | deep-analyst (also security H5)                                                   |
| H7  | `channel_expiration` set but never honoured — webhooks silently die after 7 days                                | `sync.py`                          | deep-analyst                                                                      |

### AI Scorecards (T-R054) — 3

| ID  | Title                                                                                                             | File                 | Source               |
| --- | ----------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------- |
| H8  | Candidate `notes`/`resume_excerpt`/`experience_summary` flow into LLM prompt with no `screen_injection()` applied | `scorecard_agent.py` | security-reviewer H6 |
| H9  | Bias prevention is soft-prompt only — no name/email stripping, no name-swap test                                  | endpoint + agent     | deep-analyst         |
| H10 | No per-company cost cap (10/min/user × 5 users = 3000/hr; ~$720/day GPT-4o burn)                                  | endpoint             | deep-analyst         |

### Onboarding — 1

| ID  | Title                                                            | File                              | Source       |
| --- | ---------------------------------------------------------------- | --------------------------------- | ------------ |
| H11 | Step delete orphans `OnboardingStepProgress` rows mid-assignment | `routers/onboarding.py` step CRUD | deep-analyst |

### Round-12 carryovers untouched — 5

| ID  | Title                                                                                                  | File                                                                          | Source                                                   |
| --- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- | -------------------------------------------------------- |
| H12 | Hire-role allow-list missing — `hr_manager` can hire candidate as `platform_admin` (round-12 CRITICAL) | `routers/recruitment.py:1174`                                                 | deep-analyst (cross-reference round-12 deep-analysis.md) |
| H13 | Hire→onboarding non-transactional — orphan half-states on subsystem failure                            | `routers/recruitment.py:hire_candidate` + `routers/auth.py:register-employee` | round-12 deep-analyst                                    |
| H14 | Compliance cache not invalidated on policy writes                                                      | `routers/policies.py` + `routers/compliance.py`                               | round-12 deep-analyst                                    |
| H15 | Trust chain `finalize_trust_chain(...)` never called                                                   | `agents/advisory_engine.py` + `routers/advisory.py`                           | round-12 deep-analyst                                    |
| H16 | Immutable audit log missing                                                                            | platform-wide                                                                 | round-12 deep-analyst                                    |

### Source code quality — 3 BLOCKs

| ID  | Title                                                                                                   | File                     | Source               |
| --- | ------------------------------------------------------------------------------------------------------- | ------------------------ | -------------------- |
| H17 | Bare `except Exception: pass` in `onboarding.py:2914` (request.client) and `:3001` (await request.json) | onboarding.py            | code-review BLOCK    |
| H18 | Bare `except Exception: pass` in `integrations_calendar.py:285`                                         | integrations_calendar.py | code-review BLOCK    |
| H19 | `httpx.post` (sync) inside async OAuth `disconnect()` — blocks event loop                               | `oauth.py:disconnect`    | security-reviewer M2 |

### Live/demo HIGHs (unblocked by commit + deploy + small fixes)

- AI scorecards toggle in localStorage (no audit trail)
- Onboarding template 4 returns `modules:None`
- Default template has duplicate "Probation Period" modules
- All 5 in-progress assignments stuck at 0% — onboarding module looks lifeless on first click
- Probation warning never fires on seeded data (Demo Admin has no active onboarding)
- Signup→onboarding gap reopens (new users land at `/my-dashboard` with `company_id:null`)
- Scorecard template library still empty
- Preboarding tasks still empty
- T205 HR-view shows two unrelated identities on one screen
- Generic `/integrations/{provider}/disconnect` shadows the new T-R055 disconnect with a fake-success response
- Shadow briefing on live missing T208 onboarding insights

---

## MEDIUM (notable, deduplicated)

| Title                                                                                                                                                      | Source               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| Redis `INCR + EXPIRE NX` race + silent fallback to in-memory means rate-limit semantics differ between paths and can double-burst at window boundaries     | security-reviewer H1 |
| Redis 30-second backoff dilutes public-endpoint limits during a flap                                                                                       | deep-analyst         |
| In-memory rate-limit fallback collapses under IPv6 spray (50K key cap)                                                                                     | deep-analyst         |
| Webhook reads body without `Content-Length` cap                                                                                                            | security-reviewer M1 |
| Scorecard endpoint has no length caps on candidate fields before LLM call                                                                                  | security-reviewer M3 |
| `/onboarding/analytics` is O(templates × modules × steps × assignments) — no rate limit                                                                    | security-reviewer M4 |
| `/shadow/onboarding/chat` doesn't reject already-companied users                                                                                           | security-reviewer M5 |
| `verify_signed_state` doesn't bind to user identity                                                                                                        | security-reviewer M6 |
| `schedule_interview` has no idempotency on `(candidate_id, scheduled_at)` — duplicate Google events                                                        | deep-analyst         |
| Two-`is_default=True`-templates race in `create_template`/`update_template`                                                                                | deep-analyst         |
| `ScorecardEntry` persistence catches all exceptions, hiding real DB failures                                                                               | deep-analyst         |
| T215 datetime fix is consistent within `routers/onboarding.py`, but `shadow/briefing.py` (T208) is a likely tz-aware/naive boundary that no test exercises | deep-analyst         |
| Reminder email HTML escape only handles `<>` — missing `&"'`                                                                                               | security-reviewer M8 |
| Scorecard audit log message uses LLM-derived `decision` (whitelisted but defense-in-depth weak)                                                            | security-reviewer M7 |

---

## LOW (notable)

- OAuth `error` query param interpolated unescaped into callback HTML (reflected XSS, low because attacker controls only the response they get)
- postMessage uses `'*'` target origin
- `_redirect_uri()` localhost fallback in production
- Redis URL not validated against `redis://`/`rediss://` scheme allowlist
- Approvals tabs scroll without affordance
- Singapore branding inconsistencies persist
- MS translation "Penyertaan Pekerja" awkward; ZH translations mainland-leaning
- OAuth error message leaks dev jargon ("Make sure GOOGLE_OAUTH_CLIENT_ID is set")

---

## Three Fault Lines (COC framework, deep-analyst)

- **Anti-amnesia:** the `replace(tzinfo=None)` pattern is not codified in `.claude/rules/`. Webhook one-way limitation undocumented. Multi-channel handler `company_id` issue has no ADR. Chat onboarding's keyword matching has no documented update path.
- **Premature certainty:** 7 marketing/UX claims exceed actual capability — AI scorecards return ratings with no confidence interval; chat onboarding has hardcoded keyword matching but presents like an LLM; "two-way Calendar sync" claimed but only Arbor→Google is wired.
- **Proof debt:** `_log_candidate_activity` writes the AI-scorecard activity log entry BEFORE persistence is confirmed. Webhook's `last_synced_at` is updated on unknown-event hits. Round-12 #15 (immutable audit log) becomes more urgent.

---

## Cross-cutting issues (value-auditor)

1. **The stale deploy IS the story.** Every audit finding becomes a deploy story rather than a feature story. **Highest-leverage fix: commit + redeploy.**
2. **localStorage as org-level config.** 3 round-13 feature toggles live in browser cache. No backend audit trail. CTO smell test fails.
3. **Seed-data decay across 3 rounds.** Round 6, 12, 13 all flagged: empty TAFEP/scorecards/preboarding, all candidates `pdpa_consent:false`, Demo Admin still on probation. Features ship faster than demo data.
4. **Source-of-truth drift.** Toggles, i18n keys, and backend state are not reconcilable. A buyer asking "what's enabled for my org?" has no answer.

---

## Top 7 fix-before-next-deploy (prioritized)

1. **Commit + redeploy** [CRIT-D1] — single action unlocks ~8 findings.
2. **Wire `t()` into `NavigationSidebar.tsx`** [CRIT-D3] — 30 lines, keys already exist.
3. **Drop `company_id` body param from `_register_handlers`** [CRIT-S1] OR assert single-tenant. Add CLI/MCP smoke test.
4. **Bind OAuth state to user_id + auth `/callback`** [CRIT-S3] — prevents calendar token-binding hijack.
5. **Validate `ARBOR_API_URL` at startup** [CRIT-S2] — single startup check.
6. **Replace OAuth `JWT_SECRET_KEY` fallback with fail-fast** [H2] + use a dedicated `OAUTH_STATE_SECRET` env var with domain separation.
7. **Encrypt OAuth tokens at rest** [H1] — `cryptography.fernet` on the two columns + migration.

After 1–7, round 14 should flip to "Yes, I would buy this."

### Secondary cluster (also worth doing this batch)

8. Fix `apps/web/src/app/(auth)/onboarding/page.tsx` so chat onboarding is reachable from signup [CRIT-D4].
9. Strip candidate name/email before passing to scorecard LLM + add `screen_injection()` [H8, H9].
10. Add per-company cost cap on scorecard endpoint [H10].
11. Onboarding step soft-delete (set `is_active=False`) [H11].
12. Tighten the 3 bare `except Exception: pass` sites [H17, H18].
13. Round-12 hire-role allow-list [H12].

### Tertiary (defer to next cluster)

- Architectural split (recruitment.py 3,382 lines, onboarding.py 4,060 lines) — flagged again by code-review.
- Replace 3 localStorage toggles with server-side feature flags + audit trail.
- Seed-data refresh: 2 assignments at 100%, 1 at 65%, 1 preboarding-only; 3-5 scorecard templates; 4-6 preboarding tasks per role.
- Compliance cache invalidation on policy writes [H14].
- Trust chain `finalize_trust_chain` integration [H15].
- Immutable audit log [H16].
- Hire→onboarding transactionality [H13].

---

## What's WORKING (don't lose this)

- Code quality of new features is high — Kaizen agent has bias guardrails, bounded decision set, evidence anchoring.
- Calendar OAuth state HMAC implementation itself is correct (15-min TTL, nonce, `hmac.compare_digest`); the issues are around it (secret reuse, missing user-binding, unauthenticated callback).
- T-RX07 Redis rate limiter is bounded, fails loudly with backoff, has good defense in depth.
- Onboarding tenant isolation is correct on every endpoint reviewed.
- All Google API calls are mocked in tests.
- Real Postgres in integration tier per `rules/testing.md`.
- All 4 i18n locale bundles are complete (173 keys × 4 locales) — only the wiring on NavigationSidebar is broken.
- DOCX generation code is real (python-docx, full Word output) — only deploy stands between code and demo.
- Round-12's hard blockers are all FIXED (signup, careers, candidate-detail).

---

## Next step

If the goal is "ship round 13", the convergence path is:

1. Apply fixes 1–7 above (~6 hours of focused work).
2. Re-run pytest + verify zero regressions.
3. Run a fresh round-14 audit.
4. Then commit + deploy + smoke-test live.

If the goal is "decide whether to ship round 13", the verdict from this round is **NO — the OAuth flow has 2 unfixed CRITICALs and the live demo is currently misleading**. Either fix and re-audit, or hold the round for a follow-up.
