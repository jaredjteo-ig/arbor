# Round 13 — Value Audit (Final Batch + Clusters 1-14)

**Date:** 2026-04-28
**Auditor lens:** 30-employee Singapore F&B SME owner-buyer who was told a "major update" just shipped.
**Method:** Direct API exercise on live (`http://136.110.51.61/api`) and local (`http://localhost:8000`) backends, source-of-truth inspection on the FE pages and step renderers.
**Stack health:** live frontend 200, live API auth-able as `demo@central.kailash.ai`. Local backend running but **demonstrably stale** (started before the round-13 final batch was committed).

---

## "Would I buy this?" — Bottom Line

**No, and worse than round 12 — the demo would now actively mislead me.** Round 12's blockers (signup 500, careers 500, candidate detail 404) have been fixed and the platform's substance has clearly grown — onboarding templates, AI scorecards, calendar sync, i18n scaffolding, DOCX export, chat onboarding all have real backend code. But **the running deployment doesn't have most of it**: the live API returns 404 for `/integrations/google-calendar/status`, `/integrations/google-calendar/auth-url`, `/recruitment/candidates/{id}/scorecard/generate`, `/onboarding/reminders/send-overdue`, `/shadow/onboarding/chat`, and the `/document/download/{id}?format=docx` path is rejected with `422 "format must be 'pdf'"`. Eight of the twelve features on the audit list are either inaccessible to a buyer right now, demonstrably fake (i18n scaffold doesn't translate the navbar), or wired to localStorage instead of the database. **The single highest-impact fix is a deploy** — without it, this round's demo will trip in the first 30 seconds when the salesperson clicks "Connect Google Calendar" and the toast reads "Make sure GOOGLE_OAUTH_CLIENT_ID is set."

---

## Severity Table

| #   | Severity     | Finding                                                                                                                                                                                                                                                                                                                | Module               | Fix Category               |
| --- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------------- |
| 1   | **CRITICAL** | Live deployment is stale: 6+ round-13 endpoints return 404 even though source has them (`gcal/status`, `gcal/auth-url`, `scorecard/generate`, `onboarding/reminders`, `shadow/onboarding/chat`)                                                                                                                        | Deploy / DevOps      | DEPLOY                     |
| 2   | **CRITICAL** | DOCX download rejected on live: `GET /document/download/{id}?format=docx` returns `422 "format must be 'pdf'"` — every B01 demo crashes here                                                                                                                                                                           | Documents            | DEPLOY                     |
| 3   | **CRITICAL** | i18n scaffold does NOT translate the dashboard sidebar — `NavigationSidebar.tsx` uses hardcoded English `label:` strings, not `t()` calls. 95% of the navbar stays in English when the user picks 中 / MS / த                                                                                                          | i18n                 | DESIGN (incomplete wiring) |
| 4   | **CRITICAL** | Chat onboarding (T223) is gated behind a `localStorage["arbor.chat-onboarding"]` toggle that the user has to set BEFORE signing up. New accounts always see the form-based flow. The feature is unreachable without prior insider knowledge.                                                                           | Onboarding (auth)    | DESIGN                     |
| 5   | **HIGH**     | AI scorecards toggle (T-R054) stored only in `localStorage["arbor.ai-scorecards"]` — same anti-pattern as round-12 TAFEP. No audit trail, no per-org persistence, no per-user RBAC                                                                                                                                     | Recruitment / AI     | DESIGN                     |
| 6   | **HIGH**     | Onboarding template detail returns `modules: None, steps: None` for the second seeded template (id=4 "HR Technology / SaaS Onboarding" imported from test.xlsx). A user clicking into it sees an empty builder                                                                                                         | Onboarding admin     | DATA (seed) / DESIGN       |
| 7   | **HIGH**     | Default Onboarding template (id=2) has DUPLICATE "Probation Period" modules (modules 8 and 9) — module 9 is empty (0 steps). Confusing for any admin reviewing the template                                                                                                                                            | Onboarding admin     | DATA (seed)                |
| 8   | **HIGH**     | All 5 seeded onboarding assignments are stuck at `0% complete` with `0 completed_steps / 13 total_steps`. The "demonstrated value" of the onboarding feature is zero — buyer sees activity began weeks ago and went nowhere                                                                                            | Onboarding employee  | DATA (seed)                |
| 9   | **HIGH**     | Probation leave warning (T209) silently does nothing on the seeded data: Demo Admin (employee 29) IS `on_probation` but has no active onboarding assignment, so the gate-condition `has_active onboarding` is false. Warning never fires in the demo path                                                              | Leave                | NARRATIVE (data)           |
| 10  | **HIGH**     | New user signup creates an account with `company_id: null`, but there is no working onboarding handoff — `/shadow/onboarding/chat` 404s and the form-based flow exists at `(auth)/onboarding`, but the new user lands at `/my-dashboard` not at onboarding. Signup → company-creation gap reopens                      | Auth / Onboarding    | DEPLOY + NARRATIVE         |
| 11  | **HIGH**     | Scorecard template library is EMPTY (0 templates) — same as round 12. AI Scorecard agent has nothing to score against in a demo and the picker on the candidate detail page is empty                                                                                                                                   | Recruitment Settings | DATA (seed)                |
| 12  | **HIGH**     | Pre-boarding tasks endpoint returns `{tasks: [], total: 0}` for every employee. T205 PreboardingChecklist will render an empty state for every "HR viewing employee onboarding" demo                                                                                                                                   | Onboarding HR        | DATA (seed)                |
| 13  | **HIGH**     | Pre-boarding view design: HR opens `/my-onboarding?employee_id=N` and the page calls `getMyProgress()` (which ignores the param) — so HR sees THEIR OWN onboarding (none) plus the employee's pre-boarding checklist. The two halves of the page belong to different people                                            | Onboarding HR        | DESIGN                     |
| 14  | **HIGH**     | Generic `/integrations/{provider}/disconnect` swallows `disconnect google-calendar` requests with `{"status":"disconnected","provider":"google-calendar"}` — the response is technically valid but it didn't disconnect Google Calendar (the new T-R055 router isn't running). Feature looks like it works but doesn't | Integrations         | DESIGN (route shadowing)   |
| 15  | **HIGH**     | Shadow briefing on live does NOT include T208 onboarding insights — `quick_stats` has only `active_employees, pending_leave_requests, payroll_status`. The "X new hires onboarding (Y% complete on average)" line is in source but not in the running response                                                         | Shadow Agent         | DEPLOY                     |
| 16  | **MEDIUM**   | Translation quality: ZH "入职流程" (onboarding process) and "审批" (approvals) are correct but mainland-leaning; idiomatic Singapore Mandarin would more often use "新人引导" or just leave English. Acceptable, not idiomatic                                                                                         | i18n                 | NARRATIVE                  |
| 17  | **MEDIUM**   | Translation quality: MS "Penyertaan Pekerja" (literally "employee inclusion") for Onboarding is awkward — Singapore Bahasa would more naturally say "Pengenalan Pekerja Baharu" or stay in English. Tells a SG SME owner this was machine-translated                                                                   | i18n                 | NARRATIVE                  |
| 18  | **MEDIUM**   | Connect Google Calendar UX failure mode is technical: clicking Connect when env vars aren't set produces toast "Could not start Google Calendar connection. Make sure GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are set." — leaks OAuth-developer language to a SME owner                                  | Integrations / UX    | NARRATIVE                  |
| 19  | **MEDIUM**   | Demo Admin (id=1, employee_id=29) still has `confirmation_status: "on_probation"`, no department, no start_date — same data quality issue from round 12                                                                                                                                                                | Employees / Seed     | DATA (seed)                |
| 20  | **MEDIUM**   | Recruitment candidates still all show `pdpa_consent: false` — same regulatory red flag from round 12                                                                                                                                                                                                                   | Recruitment / Seed   | DATA (seed)                |
| 21  | **MEDIUM**   | Round-13 work is fully **uncommitted** (HEAD = 3440ee0 from before the new code, working tree dirty per `.test-results`) — no production change set actually shipped. Both local AND live are running the previous commit's code                                                                                       | DevOps               | DEPLOY                     |
| 22  | **LOW**      | Approvals page uses `overflow-x-auto` on the tabs container — viewport at 375px will scroll, but the tabs row is the only horizontally scrollable element on the page. No scroll affordance (no shadow / chevron). User has to discover it by accident                                                                 | Approvals UI         | DESIGN                     |
| 23  | **LOW**      | Quota what-if calculator file (`QuotaLevyCalculator.tsx`) exists but the audit could not exercise the side-by-side comparison via API only; FE-only verification still pending Playwright run                                                                                                                          | Calculators          | TEST GAP                   |
| 24  | **LOW**      | Locale switcher exists in settings (`LocaleSwitcher.tsx` line 890) — visible to a buyer but switching it changes only the labels that DO use `t()` (auth strings, payslips strings, group labels). Most pages don't translate, see Issue 3                                                                             | i18n                 | DESIGN                     |

---

## Per-Feature Verdict

### 1. AI Candidate Scorecards (T-R054)

- **Source code**: clean, well-designed (system prompt has bias guardrails: "Never reference protected attributes (race, religion, age, family status, gender)", decision constrained to `{proceed, reject, further_interview}`, scoring clamped 1-5, evidence-anchored).
- **Reality on live and local**: `POST /recruitment/candidates/{id}/scorecard/generate` returns `404 Not Found`. The endpoint is in the source file at line 3187 but the running backends were started before the change was added.
- **Toggle anti-pattern**: gated by `localStorage["arbor.ai-scorecards"]` — buyer's IT will ask "where's the audit log of when AI scoring was enabled?" and the answer is "in the user's browser cache".
- **No template library**: `GET /recruitment/scorecard-templates` returns `{templates:[], count:0}`. Even if the endpoint worked, the AI has nothing to score against.
- **Verdict: VALUE DRAIN.** Demo is a 404 + empty picker.

### 2. Google Calendar Sync (T-R055)

- **Source code**: comprehensive (OAuth with HMAC-signed state, auto-refresh, webhook channel-token compare via `secrets.compare_digest`, create/update/delete event hooks wired into `schedule_interview` and `update_interview`).
- **Reality on live**: every new T-R055 endpoint returns 404. The OLD generic `POST /integrations/{provider}/disconnect` route shadows the new disconnect endpoint and returns a fake-success response (`{"status":"disconnected","provider":"google-calendar"}`) without actually doing anything. **A buyer would think it works** — that is worse than a clean 404.
- **Verdict: VALUE DRAIN that masks itself.** The most demo-blocking feature in the round.

### 3. Chat Onboarding (T223)

- **Source code**: real chat surface (`ChatOnboarding.tsx`), backend state machine at `POST /shadow/onboarding/chat`, sensible suggestion chips for each step.
- **Reality**: the auth/onboarding page checks `localStorage["arbor.chat-onboarding"]` BEFORE the user has signed up (line 37) — for any new account, this key is null, and the form-based flow renders. The chat is unreachable for new buyers. Even if you DID flip the toggle, `/shadow/onboarding/chat` 404s on live.
- **Verdict: VALUE DRAIN.** Dead code from a buyer's perspective.

### 4. Onboarding Admin (T198/T199)

- **Template list (`/onboarding`)**: the API works (`GET /onboarding/templates` returns 4 templates). One of those templates is junk: id=4 is the "test.xlsx" import with a description that contains role-config blobs ("Role: Software Engineer | Buddy: Senior Engineer | Goals: 30: Complete onboarding..."). Looks unprofessional in the list.
- **Template detail (`/onboarding/templates/[id]`)**: works for the default Central template (id=2 → 4 modules / 13 steps, real Singapore EA content), but the imported template 4 returns `modules: None, steps: None`. Click into it and the builder is empty.
- **Default template has duplicate "Probation Period" modules** (8 + 9) where module 9 is empty.
- **Numeric `sort_order` reorder, no drag-and-drop**: a non-technical HR person CAN edit a step but reordering means typing "1, 2, 3" in a number field. Not "easy for a non-technical HR person to build".
- **Verdict: NEUTRAL with rough edges.** Substance is there, demo polish isn't.

### 5. Employee Onboarding (T201-T207)

- All 5 seeded assignments are stuck at `0/13 steps complete`. Status is "in_progress" but nothing has progressed since 7 April. Buyer asks "so does anyone actually use this?" and the answer is visibly "no".
- 6 step renderers exist (`ContentStep`, `ChecklistStep`, `DocumentUploadStep`, `PolicyAcknowledgmentStep`, `FormStep`, `ApprovalStep`) — file structure is solid.
- **`/onboarding/reminders/send-overdue` 404s on live** — T207 reminder emails are unreachable.
- **Verdict: NEUTRAL.** UI is there, evidence of value isn't.

### 6. Pre-boarding Checklist (T205)

- `GET /onboarding/preboarding/{employee_id}` returns `{tasks:[], total:0}` for every employee tested. The component has nothing to render.
- The HR/owner override path (`/my-onboarding?employee_id=N`) is logically broken: the page calls `getMyProgress()` for the LOGGED-IN USER, ignores `?employee_id`, and renders the pre-boarding checklist for that employee on top. Two unrelated people on one screen.
- **Verdict: VALUE DRAIN.** Even if the data were there, the screen confuses two identities.

### 7. Onboarding Insights in Shadow Briefing (T208)

- **Source code adds the insights** (`briefing.py:458 _onboarding_insights`) including "X new hires onboarding (Y% complete on average)" and overdue alerts.
- **Live response does NOT include them**: the briefing JSON I got back has only `pending_leave, draft_payroll, pending_leave_requests, payroll_status, active_employees`. Onboarding insights are missing — confirms the deploy gap.
- **Verdict: VALUE DRAIN.** Source good, deploy bad.

### 8. Probation Leave Warning (T209)

- The warning logic is correct (`leave.py:777`) — it requires BOTH `confirmation_status == "on_probation"` AND an active onboarding assignment.
- Tested with Demo Admin (employee 29, on_probation) and got NO warning back — because Demo Admin has no active onboarding. The seed data does NOT exercise the warning path. A demo of T209 will silently do nothing.
- **Verdict: NEUTRAL (logic correct) but no demo evidence.**

### 9. i18n Locale Switcher (B17)

- **4 locales × 173 keys each** is a respectable scaffold.
- **The dashboard sidebar IS NOT TRANSLATED.** `NavigationSidebar.tsx` uses hardcoded English strings (`label: "Dashboard"`, `label: "Onboarding"`, etc., lines 56-237). Only the two group headers (`t("nav.group_tools")`, `t("nav.group_management")`) call `t()`.
- **Page-level translation is selective**: my-payslips uses `t()` everywhere, but most pages (recruitment, employees, leave, etc.) are still English-only.
- **Translation quality**: ZH is OK; MS "Penyertaan Pekerja" is awkward; TA looks correct but I am not a native reader.
- **Verdict: VALUE DRAIN.** A buyer who flips to Mandarin sees an English navbar, English page contents, with a Mandarin "Settings" page header. This is worse than not shipping the feature.

### 10. DOCX Export (B01)

- **Source code is real** (`document.py:216 _generate_document_docx`, full Word generation with python-docx).
- **Live API rejects DOCX** with `422 "format must be 'pdf'"`. Same stale-deploy story.
- **Verdict: VALUE DRAIN.** Demo button click → 422 error.

### 11. Approvals Page Tabs (B15)

- Tab container has `overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0` — at 375px wide the tabs scroll horizontally without breaking layout.
- No scroll affordance (gradient/chevron) so users may not realize there's more.
- **Verdict: NEUTRAL.** Functional, mediocre discoverability.

### 12. Quota What-If Calculator (B07)

- File `QuotaLevyCalculator.tsx` exists. API-only audit could not exercise the side-by-side render. Recommend Playwright follow-up.
- **Verdict: TEST GAP.**

---

## Cross-Cutting Issues

### 1. The Stale Deploy Is The Story (CRITICAL, blocking everything)

`workspaces/hr-ai-advisory/.test-results` declares `HEAD = 3440ee0 (working tree dirty)`. `git log --oneline` confirms the latest commit IS `3440ee0` (`docs(deploy): canonical local + production deploy procedures`). All round-13 production code (`scorecard_agent.py`, `integrations/google_calendar/*`, `integrations_calendar.py`, T207 reminders, T208 briefing insights, T209 probation warning, DOCX support, T223 chat router) is **uncommitted and undeployed**. `pytest` ran against the dirty tree but the running backends were started from the previous commit. This converts every audit finding into a deploy story rather than a feature story. Until you commit + ship, the buyer literally cannot see most of round 13.

### 2. localStorage as Org-Level Configuration

Three round-13 toggles live in browser localStorage: `arbor.ai-scorecards`, `arbor.chat-onboarding`, and the round-12 `arbor.tafep-ai`. None are reflected in any backend audit log. From a SG enterprise-buyer lens, this is a "not enterprise-ready" smell. CTOs ask: "If our compliance officer needs to know who turned on AI scoring, where's the audit trail?"

### 3. Seed-Data Decay Across Three Rounds

Round 6 found: empty TAFEP, broken candidate detail. Round 12 found: empty scorecards library, empty interviews, scorecard library empty, all candidates `pdpa_consent: false`, Demo Admin still on probation, junk policy ("Receipt1012046 26012042"). Round 13 finds: still all the round 12 issues + new ones (template 4 modules None, default template duplicated probation module, all onboarding assignments at 0% progress, scorecard library still empty, preboarding still empty). The seed pipeline is not catching up to the feature surface. **The product features faster than the demo data, so every shipped feature looks lifeless.**

### 4. Source Of Truth Drift Between Toggles And Backend

The localStorage toggles are read by individual pages but no single component knows the platform's "feature flag state". A buyer asks "what's enabled for my org?" and there is no answer. This compounds with the i18n half-translation problem: the user's experience is mosaic, not uniform.

---

## Top 5 Demo Blockers

1. **Live deployment is missing 6+ round-13 endpoints (404 on `gcal/status`, `gcal/auth-url`, `scorecard/generate`, `onboarding/reminders`, `shadow/onboarding/chat`).** First click on "Connect Google Calendar" or "Generate AI Scorecard" or DOCX download fails. Demo dies in the first 30 seconds. **Fix: commit working tree + redeploy.**
2. **DOCX download on live returns 422 "format must be 'pdf'".** B01 demo path crashes immediately. Same root cause as #1.
3. **i18n switch shows an English sidebar.** Switching locale in settings is the most visible "international SME-ready" demo move. The navbar staying English makes it look broken even though the rest works. **Fix: replace hardcoded labels with `t("nav.…")` keys (already in en.json/zh-CN.json/ms-MY.json/ta-SG.json).**
4. **Chat onboarding (T223) is unreachable for new buyers** — the localStorage toggle has to be flipped before signup, so any first-time buyer sees the form flow. Sales pitch "we onboard you in chat" lands as "we don't". **Fix: server-side feature flag, default-on for new accounts during the rollout.**
5. **Every onboarding assignment is at 0%.** Buyer drilling into the onboarding module sees five new hires, all "in_progress", none of whom have completed a single step in three weeks. **Fix: seed two assignments at 100%, two at ~60%, one preboarding-only — gives the screen a visible activity gradient.**

---

## What A Compelling Demo Would Look Like

A buyer hits `/recruitment/settings`, clicks "Connect Google Calendar", grants OAuth in a popup, and sees the status pill flip to **Connected** with a real `expires_at` timestamp. They schedule an interview from the candidate detail page; the interviewer's Google Calendar gains a real event. They flip the AI Scorecard toggle (server-stored, with an audit-log line on the company), pick a "Engineering — Senior Backend" scorecard template (seeded), and the AI returns a real 1-5 rating per criterion with no protected-attribute references and a clear `further_interview` recommendation. They navigate to `/onboarding`, see two assignments at 100% (with the smiling employee names), one at 65%, one preboarding-only — and the dashboard's shadow briefing card reads "5 new hires onboarding (54% complete on average)". They flip the locale to Mandarin and the entire navbar transitions to 仪表板 / 入职流程 / 招聘. They generate a Warning Letter and download both PDF and DOCX. None of this requires new code — it requires deploy + seed + i18n wire-up.
