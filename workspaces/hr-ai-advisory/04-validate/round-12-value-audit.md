# Round 12 — Whole-Platform Value Audit

**Date:** 2026-04-28
**Auditor lens:** Skeptical Singapore SME owner-buyer (10–50 staff coffee chain), evaluating Arbor as their first HRIS + advisory platform.
**Method:** Direct API exercise + frontend code/route inspection on `localhost:3000` / `:8000`. (Playwright MCP tools were not available in this environment; the audit therefore drives the live backend and inspects the rendered routes/components as a substitute.)
**Stack health:** Frontend 200, backend 200, postgres + redis healthy. Tier-1 unit tests: 2058 passed (per `.test-results`).

---

## "Would I buy this?" — Bottom Line

**No, not yet — but I see the product underneath, and I would buy it in 4–6 weeks if specific value gaps close.** What works (CPF calculator, shadow agent briefing/nudges with cited provisions, advisory guardrails on adversarial queries) is genuinely impressive and unique against any local HRIS competitor. What is broken (signup blocked by missing migration, every job-detail page 404s, public careers page 500s on slug column, advisory cites zero provisions, scorecard library empty, TAFEP setting stored in localStorage) breaks the demo within the first 90 seconds. A buyer running their own walk-through today would conclude this is a polished prototype, not a production HRIS — and the gap between code quality and demoable substance is the single biggest issue.

---

## Severity Table

| #   | Severity     | Finding                                                                                                                                                       | Module                  | Fix Category                  |
| --- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ----------------------------- |
| 1   | **CRITICAL** | New-account signup returns 500 — `column "token_version" does not exist` on `users`                                                                           | Auth / Onboarding       | DATA (migration)              |
| 2   | **CRITICAL** | Public careers listing returns 500 — `column "slug" does not exist` on `companies`                                                                            | Recruitment / Careers   | DATA (migration)              |
| 3   | **CRITICAL** | `/recruitment/jobs/[id]` redirects to `/recruitment` — no Kanban detail view exists                                                                           | Recruitment             | DESIGN (missing page)         |
| 4   | **CRITICAL** | Every `/recruitment/jobs/{id}` API call returns 404; same for `/candidates/{id}` despite list endpoints showing the records                                   | Recruitment             | DATA (read-by-id broken)      |
| 5   | **CRITICAL** | Auth rate-limit path raises `NameError: logger` on the running backend — login locks out for 60s after 5 attempts and surfaces 500 instead of 429             | Auth                    | DEPLOY (process restart)      |
| 6   | **HIGH**     | Advisory returns `provisions_cited: []` and `confidence_score: 1.0` for a simple leave question. KB is empty (`kb_provisions: 0, kb_acts: 0, kb_domains: 0`). | Advisory                | DATA (KB seeding) + NARRATIVE |
| 7   | **HIGH**     | Mid-complexity advisory question ($5,500 OT on public holiday) returns `degraded: true` + "I'm having trouble processing your question right now."            | Advisory                | NARRATIVE (silent fallback)   |
| 8   | **HIGH**     | `/careers` (no slug) returns 404 — there is no public careers index                                                                                           | Recruitment             | DESIGN (missing route)        |
| 9   | **HIGH**     | Recruitment Settings TAFEP AI toggle stored in `localStorage` only, not server-side — no audit trail, no per-org persistence                                  | Recruitment Settings    | DESIGN                        |
| 10  | **HIGH**     | 5 of 7 seeded jobs have empty `position_title`; `requirements` field is a Python `str(list)` literal (e.g., `"['5+ years...']"`) rendered as-is in API        | Recruitment             | DATA (seed quality)           |
| 11  | **HIGH**     | All 20 candidates have `pdpa_consent: false` — for a Singapore HR product this is a regulatory red flag                                                       | Recruitment             | DATA (seed)                   |
| 12  | **HIGH**     | Compliance dashboard reports all 5 domains as "missing / 0 provisions"; only 5 domains served, the brief specifies 6 (TAFEP missing from API response)        | Compliance              | DATA (KB) + DESIGN            |
| 13  | **HIGH**     | Policies endpoint exposes a tax-receipt PDF mis-classified as a `fair_employment` policy (`title: "Receipt1012046 26012042"`)                                 | Policies / KB ingestion | DATA                          |
| 14  | **MEDIUM**   | 4 of 7 advertised calculators (overtime, retrenchment, notice-period, cost-to-company) have no backend endpoint — all logic is client-side                    | Calculators             | DESIGN (parity)               |
| 15  | **MEDIUM**   | Recruitment landing is one 4,701-line page; user-flows doc explicitly says "each concern gets its own route"                                                  | Recruitment             | DESIGN                        |
| 16  | **MEDIUM**   | Single demo company has 5 duplicate "Senior Software Engineer" jobs with identical descriptions, all unpublished                                              | Recruitment             | DATA (seed)                   |
| 17  | **MEDIUM**   | 15 interviews seeded with empty `interviewer_ids` and empty `location_or_link` — no Zoom link, no interviewer                                                 | Recruitment             | DATA (seed)                   |
| 18  | **MEDIUM**   | Demo Admin (owner) employee record shows `confirmation_status: "on_probation"`, empty department, empty start_date                                            | Employees               | DATA (seed)                   |
| 19  | **MEDIUM**   | Scorecard templates list is empty (Wave 2 just shipped CRUD but no library content) — first-time admin sees a blank page                                      | Recruitment Settings    | DATA (seed)                   |
| 20  | **MEDIUM**   | `employees/{id}` get-by-id strips email/name from response (returns empty strings) while list endpoint returns them — inconsistent contracts                  | Employees               | API contract                  |
| 21  | **MEDIUM**   | Calculator citation ("Employment Act, Part IV") shown but not deep-linked to a KB provision page (no proof chain back to the law text)                        | Calculators             | NARRATIVE                     |
| 22  | **LOW**      | JWT signing key is 25 bytes (warning logged on every login: `InsecureKeyLengthWarning: HMAC key below 32 bytes`)                                              | Auth                    | SECURITY                      |
| 23  | **LOW**      | Source distribution in analytics is suspiciously even (`careers_page:5, jobstreet:5, referral:5, linkedin:5`) — synthetic, not credible                       | Recruitment Analytics   | DATA                          |
| 24  | **LOW**      | Frontend brand reads "Central" but workspace/repo is "Arbor / hr-ai-advisory" — buyers in a generic demo will be confused                                     | Branding                | NARRATIVE                     |
| 25  | **LOW**      | Onboarding wizard silently swallows company-creation errors as "company may already exist"                                                                    | Onboarding              | NARRATIVE (error hiding)      |

---

## Flow-by-Flow Audit

### Flow 1 — Sign-up + Onboarding Wizard

**Repro:**

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","password":"Foo12345!","name":"New User"}'
# {"detail":"Registration failed. Please try again."}
# Backend log: "Database query failed: column 'token_version' of relation 'users' does not exist"
```

**Verdict: VALUE DRAIN.** This is the front door. Today it is bricked. The only way into the platform is the seeded demo account (`demo@central.kailash.ai / CentralDemo2026!`), which I had to discover by reading `scripts/seed_demo_data.py`. A buyer self-registering for a trial cannot complete step 1.

**Onboarding wizard itself is a clean 4-step (Welcome → Company → Snapshot → Ask)**, and routing the user's first advisory question through onboarding is a great trust-building idea — but it is gated behind a sign-up that 500s.

### Flow 2 — HR Advisory Chat

I asked three escalating questions:

| #   | Question                                                         | Result                                                                                                    | Provisions cited | Confidence           | Verdict                                               |
| --- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------- | -------------------- | ----------------------------------------------------- |
| 1   | "How much annual leave for 3 yrs service?"                       | "9 days" (correct under EA s88E)                                                                          | **0**            | **1.0** (suspicious) | Right answer, no proof                                |
| 2   | "Employee earns $5,500, 4h OT on public holiday, what do I owe?" | **"I'm having trouble processing your question right now."** (`degraded: true`, risk_tier `red`)          | 0                | 0.3                  | Demo-killing degraded fallback on a textbook question |
| 3   | "Can I terminate a pregnant employee on probation?"              | "Dismissal related to pregnancy/maternity is wrongful dismissal." + alternative_guidance, `blocked: true` | 0                | 0.0                  | Guardrail works correctly                             |

**Verdict: VALUE DRAIN that masks GENUINE VALUE.** The guardrail logic on adversarial queries is genuinely best-in-class — it refuses, explains why, and offers compliant alternatives. That is a defensible differentiator. But it is buried under two systemic problems:

1. **Provisions citation is empty** on every successful answer. The whole product positioning ("grounded HR advisory with cited legal provisions") evaporates when the JSON shows `"provisions_cited": []`. This is a direct contradiction of the brief's "accuracy is paramount" line and `briefs/02-user-findings.md` ("AI advisory is not utilizing all its available information").
2. **Mid-complexity questions silently degrade.** A non-Part-IV employee asking about OT on a public holiday is exactly the question this product needs to answer. Returning a generic "try again" with `degraded: true` is worse than a "we don't know" — it makes the buyer think the system is unstable.

The KB is empty (`kb_provisions: 0`). Every other layer (guardrails, risk-tier, trust chain telemetry, disclaimers) is solid. **Closing the KB gap is the single highest-impact fix.**

### Flow 3 — Recruitment (Wave 2)

This is the audit's stated focus area. Every step of the user-flows doc breaks somewhere:

| User-flows step              | Reality                                                                                                                                                                                                   |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Click "+ New Job" → publish  | Backend works. Seed has 5 jobs with empty `position_title` and `requirements` rendered as `"['5+ years...']"` (raw Python str of a list).                                                                 |
| Click into a job → Kanban    | **Broken.** `/recruitment/jobs/[id]` redirects to `/recruitment`. The Kanban view promised in the user-flows doc does not exist as a page. The 4,701-line `/recruitment/page.tsx` tries to be everything. |
| Drill into candidate         | **Broken.** `/recruitment/candidates/{id}` returns 404 even though `/candidates` lists 20. Same for `/recruitment/jobs/{id}` (single-record read seems mis-wired against tenant ownership check).         |
| Public careers page          | **Broken.** `/careers` (no slug) returns 404. `/careers/{company-slug}` 200s on the frontend but the API call to `/recruitment/careers/{slug}/jobs` returns 500 (`column "slug" does not exist`).         |
| Apply, schedule, offer, hire | Cannot reach because earlier steps fail. Offers list is empty (0 records). 15 interviews seeded but every one has empty `interviewer_ids` + empty `location_or_link`.                                     |

**Verdict: VALUE DRAIN.** The recruitment module looks like the most ambitious surface, but to a buyer drilling in, almost every detail page is a dead end. The one place the value flow could be strong (the public careers page → apply flow) is broken at the database layer. **Wave 2 is not demo-ready.**

### Flow 4 — Recruitment Settings

**Verdict: NEUTRAL.** Scorecards CRUD endpoints work (`/recruitment/scorecard-templates`) but library is empty — first-time admin sees a "no templates yet" state. The TAFEP AI toggle is stored in `localStorage` (not server) — it is a setting that _appears_ enterprise but isn't. Maintenance sweeps endpoints I tried (`/recruitment/sweeps/data-retention`) returned 404, though the page advertises them.

### Flow 5 — Employees + CSV Import + Leave

29 employees seeded. `is_active: true` for everyone, departments mostly populated, NRIC fields blank (acceptable — PII would never be in a demo). **Demo Admin's own record is in `on_probation` state with an empty start date** — this is the owner's seat, it should be `confirmed`. Single-record `/employees/{id}` strips email/name fields (returns empty strings) — a bug a buyer will hit the moment they open an employee profile.

Leave applications endpoint returns 10 records with proper status flow (approved, applied_at, total_days). `/leave/balances` returns `{"balances": []}` — the headline ("how many days does X have left") cannot be answered.

**Verdict: NEUTRAL** — basic plumbing works; missing balance data and the owner's "on probation" status undermine the "this is your real HR system" narrative.

### Flow 6 — Calculators

**Verdict: PART VALUE ADD, PART NARRATIVE GAP.** CPF calculator returns precise, defensible output (correct 17/20% for SC under-55, OW/AW split, OA/SA/MA allocation). That is buyable. But:

- 4 of 7 advertised calculators (`overtime`, `retrenchment`, `notice-period`, `cost-to-company`) have **no backend endpoint** — all math is client-side TS. The OT calculator constants are correct (`$2,600 cap, 1.5×, 2.0×, 72h cap`) but a buyer cannot trust an "auditable" calculator that runs entirely in the browser with no server-side audit log.
- Citation badges link to "Employment Act, Part IV" as a label string, not a deep-link to a provision page. The "auditable, no AI, just the law" subtitle on the hub is a great line that the calculators do not back up with proof.

### Flow 7 — Compliance Dashboard

`/compliance/status/1` returns:

```json
{"overall_status":"non_compliant",
 "domains":{"employment_act":{"status":"missing","provisions_count":0},
            "cpf":{"status":"missing","provisions_count":0},...}}
```

5 domains shown (the brief specifies 6 — TAFEP is absent from `/compliance/domains`). Every domain is "missing" because the KB is empty. The frontend page uses **hardcoded fixture text** (provisions like `EA s95A KET`) so it looks credible visually, but a buyer asking "how does this stay current?" gets a static answer. **Verdict: VISUAL DEMO that won't survive a probing question.**

### Flow 8 — Settings (LLM Keys / BYOK)

`/companies/1/llm-config` returns `{"config": null, "source": "server_env"}` — clean. The advisory query response surfaces `llm_info: {provider:"gemini", model:"gemini-2.5-flash", is_byok:false}` — transparency about which model answered. This is genuinely good. **Verdict: VALUE ADD.**

---

## Cross-Cutting Issues

### CC-1: Database migration drift (CRITICAL)

Two columns referenced by code don't exist in the database (`users.token_version`, `companies.slug`). Both block primary value flows (signup, public careers). The unit tests pass with mocks; the live DB schema lags. Single highest-impact fix.

### CC-2: KB is empty (HIGH, systemic)

`kb_provisions: 0, kb_acts: 0`. This makes every "grounded" promise (advisory citations, compliance status, calculator deep-links) hollow. The product has the _plumbing_ for grounded advisory and the _guardrails_ to refuse adversarial queries — but no _content_. Until the KB is seeded, the product can't tell its own value story.

### CC-3: Single-record read endpoints are broken across modules (HIGH)

Job detail, candidate detail, employee-by-id (partial). The list endpoints work; the read endpoints don't. This is consistent enough to be a shared `dataflow_crud.read()` bug rather than per-router code.

### CC-4: Seed data quality undermines the credibility of every list view (HIGH)

Empty job titles, str(list)-literals as requirements, all-zero candidate scores, all-false PDPA consent, perfectly-even source distribution, blank interviewer assignments, a tax receipt mis-classified as a fair-employment policy. A buyer will spot this in 30 seconds.

### CC-5: User-flow documents and shipping reality have diverged (MEDIUM)

The user-flows doc says "each concern gets its own route" — recruitment is one 4,701-line file. It says `/careers/jobs/<job-slug>` — the actual route is `/careers/<company-slug>`. It promises a Kanban job-detail page — it redirects to the index. Either update the doc to match what shipped, or build what the doc says.

### CC-6: Branding mismatch (LOW)

Frontend says "Central" (Ricoh demo brand). Workspace says "Arbor / hr-ai-advisory". README/welcome and onboarding need to be reconciled before any prospective buyer demo not aligned to Ricoh.

---

## What a Great Demo Would Look Like (Concrete)

A 12-minute walkthrough that would close a $50–100K SME deal:

1. **(0:00) Sign up live with a real email.** Onboarding wizard collects company profile + first question.
2. **(2:00) First advisory question** answered with **3 cited provisions** linked to the actual EA text, confidence 0.85, disclaimer visible.
3. **(4:00) Compliance dashboard** shows 4 amber gaps with provision references and a "fix this in one click" path (e.g., "Generate KETs for 12 employees missing them" — flowing into the document module).
4. **(6:00) Recruitment**: open jobs page shows 3 published jobs with proper titles. Click one → Kanban with 8 candidates, drag-drop a candidate from Screening → Interview, scheduler modal pre-fills interviewer + Zoom link, candidate emails fire.
5. **(9:00) Public careers page** at `/careers/audit-coffee` shows the 3 jobs with company branding; submit a test application; back in admin, the application appears in the Kanban.
6. **(11:00) Hire flow**: Convert an offered candidate to an employee — payroll record auto-initialised, KET generated with citations, onboarding checklist assigned. Shadow agent surfaces a nudge: "Lily's KET cites old EA provision; refresh?"

Right now, **steps 1, 2, 4, 5, and 6 are partially or fully broken**. Step 3 looks visually credible but has no live data behind it. Step 6 (hire-to-onboard) is the moment that locks in the deal — and it cannot run.

---

## Single Highest-Impact Fix

**Run the missing migrations + seed the KB** (CC-1 + CC-2). One ships the auth + careers value chains in their entirety; the other turns every "grounded advisory" claim from theatre into evidence. Together they unblock a fully working demo for everything except the recruitment Kanban detail page (which is the next priority after that).

Once those two are done, the next 24 hours of work should be:

1. Replace the `/recruitment/jobs/[id]` redirect with a real Kanban page (re-using fragments of the 4,701-line `recruitment/page.tsx`).
2. Fix `dataflow_crud.read("JobListing", id)` and `("Candidate", id)` for tenant-isolated reads.
3. Re-seed candidates with `pdpa_consent: true`, real PDPA dates, and varied source distribution.
4. Move TAFEP toggle from localStorage to a server-persisted org setting.
5. Restart the backend (the `logger` NameError fix per `.test-results` is in source but not loaded in the running process).

That sequence converts the audit from "value drain" to "value chain" in roughly one focused day.
