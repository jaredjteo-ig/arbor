# Red-team comprehensive walk — 2026-05-19

**HEAD at capture:** `4912ec8` (local) / `13c0569` (prod live).
**Method:** Live Playwright walk through prod (`http://136.110.51.61`) as all four roles. Click every nav item, every button, exercise every workflow end-to-end. Console + network monitored throughout. Followed by codebase audit.
**Tester perspective:** Skeptical SG-SME HR buyer who has never seen this product before. No insider knowledge.

**Test accounts:**

- Demo Admin (owner): `demo@central.kailash.ai` / `CentralDemo2026!`
- Grace Koh (HR manager): `grace.koh@central-solutions.sg` / `Employee2026!`
- Rajesh Kumar (employee with 7 reports — derived line manager): `rajesh.kumar@central-solutions.sg` / `Employee2026!`
- Marcus Tan (IC, on probation, in Rajesh's team): `marcus.tan@central-solutions.sg` / `Employee2026!`

---

## Findings legend

- **🔴 BLOCKER** — page crashes, key flow broken, demo would die here
- **🟠 HIGH** — works but produces wrong / missing data, looks broken
- **🟡 MEDIUM** — works but UX gap, polish, value-flow break
- **🟢 LOW** — minor cosmetic or future improvement
- **✅ HOLD** — checked, no defect

---

## Headline

Platform mechanics work end-to-end. RBAC boundaries hold (P49 + P55
derived-manager pattern verified live). The **flagship AI advisory**
returns answers without rendered citation chips — landing page
promises "source-cited answers" but the API response carries
`domains: ["general"]` with no provisions array — that's a buyer
trust hit. CPF answer also recites the **2025-era OW-ceiling
roadmap** ("scheduled to progressively increase to $8,000 by 2026")
even though today is May 2026 and the ceiling is already $8,000 —
the model's training cutoff is leaking through stale KB content.
**Three workflow gaps** would erode demo credibility:
probation-auto-transition is dead, onboarding completion progress
is stuck at 0% across the seed, and the HR-Manager role still sees
platform-admin surfaces (KB Management, Audit, QA Sessions) even
though those endpoints 404 her.

---

## Round 1 — Owner (Demo Admin) walk

Routes visited as owner (every nav item):

| Route                     | Status | Notable                                                                                                                                                                                                         |
| ------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/` (landing)             | ✅     | clean; 1× /api/auth/me 401 expected for anon                                                                                                                                                                    |
| `/login`                  | ✅     | clean                                                                                                                                                                                                           |
| `/dashboard`              | ✅     | quick-actions + HR mgmt cards + compliance + pending actions                                                                                                                                                    |
| `/strategy/lifecycle`     | ✅     | 8 stages render; tour dialog dismissible; click-through to KPI drill-in works                                                                                                                                   |
| `/advisory`               | 🟠     | answer arrives but **no rendered citations**; history shows orphaned "(earlier reply unavailable)" entries (resolved on refresh — but visible on first paint)                                                   |
| `/compliance`             | ✅     | 67 provisions, 6 domains, 7 findings after run with check                                                                                                                                                       |
| `/calculators`            | ✅     | landing                                                                                                                                                                                                         |
| `/calculators/cpf`        | ✅     | $4500 / age 35 / Citizen → $765 + $900 = $1665 (correct 17%/20% 2026 rates); $1039 OA / $277 SA / $349 MA matches CPF First Schedule                                                                            |
| `/employees`              | ✅     | 28 rows render; Directory / Onboarding / Invitations tabs work                                                                                                                                                  |
| `/employees → Onboarding` | 🟠     | 5 assignments, 1 marked **Completed at 0% progress** (Lily Phang)                                                                                                                                               |
| `/payroll`                | 🟡     | 3 runs render; out-of-order banner correct; identical gross across 3 months ($162,050) reads as fake seed                                                                                                       |
| `/leave`                  | ✅     | 12 applications; rejected / auto-cancelled / approved states all present                                                                                                                                        |
| `/claims`                 | ✅     | 3 pending, 6 total; itemized line entries with amounts                                                                                                                                                          |
| `/attendance`             | 🟡     | "Today" lists 2 absent warehouse staff; "Monthly Summary" 1/1 day present, "0h 0m" with "Late" status on single record — low-quality seed                                                                       |
| `/shifts`                 | 🟡     | **completely empty** — no templates, no shifts, "No templates yet" empty state                                                                                                                                  |
| `/policies`               | 🟡     | 0 active / 0 draft / 0 archived — yet 3 policies do exist via API (Workplace Safety, Employee Handbook, FWA) — list endpoint mismatch                                                                           |
| `/appraisals`             | ✅     | 1 template ("Annual Performance Review"); Templates/Periods/My Appraisals tabs                                                                                                                                  |
| `/goals`                  | 🟠     | **Duplicate "Q2 Engineering L&D" goal card** rendered twice in Active tab                                                                                                                                       |
| `/recognition`            | ✅     | Public feed 8 kudos; Received by me tab                                                                                                                                                                         |
| `/exit-interviews`        | 🟡     | 2 entries — but **Rajesh Kumar's exit interview shows up while he's still actively managing 7 reports**. Either seed is wrong or workflow doesn't mark him as exited.                                           |
| `/engagement`             | ✅     | 6-pulse trend, 7 surveys H2026; per-dept filter works                                                                                                                                                           |
| `/projects`               | ✅     | 2 active projects ($80K, $50K)                                                                                                                                                                                  |
| `/inventory`              | ✅     | 5 items, all Available                                                                                                                                                                                          |
| `/recruitment`            | 🟠     | 22 candidates: 13 New + 2 Screening + 6 Interview + **0 Offered + 0 Hired** — pipeline stalled in seed                                                                                                          |
| `/approvals`              | 🟡     | Only Timesheet + Inventory tabs; no Leave/Claims roll-up                                                                                                                                                        |
| `/reports`                | 🟠     | Headcount-by-dept sums to **29** (8+6+6+4+3+2) but Employees list / Lifecycle show **28**. Inconsistent. Leave-utilisation / payroll-trend cards say "Run a report to see data" despite 3 payroll runs existing |
| `/analytics`              | 🟠     | Top stat says "**75% local**" but Pass-Type bar shows Local 19/28 = 67.9%. The 75% is Local+PR; label misleading                                                                                                |
| `/emergency`              | ✅     | 6 emergency scenario guides render (TADM, WICA, MOM, etc.)                                                                                                                                                      |
| `/training/records`       | ✅     | 4 training records, tabs for Certifications/Mandatory/SkillsFuture                                                                                                                                              |
| `/admin`                  | ✅     | KB / regulatory / feedback / audit / QA tabs; numbers consistent (67 provisions, 6 acts, 1 query, 0 feedback)                                                                                                   |
| `/settings/integrations`  | 🟡     | All 14 integrations show "Not Connected" (0/3 acct, 0/3 bank, 0/1 gov, 0/5 comms, 0/2 cal) — buyer demo gap                                                                                                     |
| `/settings`               | ✅     | A11y (Normal / Large / XL), theme, language (EN/中/MS/த), AI memory, observation log                                                                                                                            |
| `/help`                   | 🟡     | **Brand mix: subtitle says "Get started with Arbor"** but product is branded Central everywhere else                                                                                                            |
| `/documents`              | ✅     | 12 templates with provision links and EA citations                                                                                                                                                              |

### Owner findings

**🟠-O1 — Advisory has no rendered citations.** Landing page promises "Source-cited answers from 6 regulatory domains" with example chips like "EA Part II" / "Section 10". Live response for "How do I calculate CPF contributions?" comes back as plain prose with no chips. API `/api/advisory/history/{id}` returns:

```json
"domains": ["general"], "risk_tier": "green", "confidence_score": 1
```

No `citations` / `provisions` array. The CPF question matched **`general`** domain, not `cpf` — KB retrieval routing is wrong.

**🟠-O2 — Stale OW-ceiling answer.** CPF answer: "_The OW ceiling is currently $6,000 but is scheduled to progressively increase to $8,000 by 2026._" Today is 2026-05-19. The ceiling **is** $8,000. The deterministic calculator (`/calculators/cpf`) uses the correct 2026 rates ($1665 total for $4500/age 35/Citizen) but the LLM advisory is reciting the pre-2026 roadmap. Either:

- KB chunk for CPF is from the 2024–2025 era and not re-embedded, OR
- LLM is filling from training data, ignoring KB.

Buyer who knows SG payroll will catch this in <60s and the platform's "answers grounded in Singapore employment law" claim will be the first thing they distrust.

**🟠-O3 — Advisory history shows "(earlier reply unavailable)".** On first navigation to `/advisory`, history sidebar showed 3 entries; 2 of them had the placeholder "(earlier reply unavailable)" under the question. On full refresh `/api/advisory/conversations` returned only 1 entry. The frontend is rendering stale client-side state or an orphaned conversation list. Buyer sees "_something we asked is lost_".

**🟠-O4 — Goals: duplicate card.** "Q2 Engineering L&D — every IC has approved budget by end of Q2" renders twice in Active tab. Either the seed inserted two rows, or the React key collision is causing double render. Counter says `Active(6)` but I count 7 cards visible. Pure data bug or render bug — verify via `/api/goals` returns 6 unique rows.

**🟠-O5 — Headcount inconsistency 28 vs 29.** `/reports` department breakdown adds to 29 (8 Eng + 6 Ops + 6 Sales + 4 Fin + 3 HR + 2 Mgmt). `/employees` and `/strategy/lifecycle` both say 28. Reports counts Demo Admin (`user.id = 1`) separately because the lifecycle excludes a soft-deleted/system row. Single source of truth missing.

**🟠-O6 — Onboarding "Completed at 0%"** (Lily Phang). Completed status with 0% progress is contradictory. Either completion auto-trips to 100% when status changes, or the seed wrote conflicting fields. Buyer who clicks into Lily's record will lose trust.

**🟠-O7 — Recruitment pipeline stalled.** 22 active candidates, 0 offers, 0 hires. The Lifecycle "Recruit / Action / 2 jobs · 2 stale" surfaces the gap, but the seeded narrative doesn't show recruitment ever closing. Buyer will ask "_does the offer/hire flow work?_"

**🟠-O8 — Probation auto-transition broken** (cross-cuts Owner / IC views). Marcus Tan: `start_date: 2026-01-06`, `probation_months: 3`, expected probation end ~2026-04-06. Today 2026-05-19. His `confirmation_status` is still `on_probation` and `probation_end_date` is `""`. The system has no job that flips probation → confirmed when the period elapses, and HR never gets a "Marcus's probation ends today — confirm?" nudge. Seed-wide check: Jason Ng also shows `On Probation` in Employees list — likely same issue.

**🟡-O9 — Payroll seed is too symmetric.** Apr 2026 Paid + Mar 2026 Draft + Feb 2026 Approved all show **identical gross $162,050** and **identical net $138,656**. Realistic monthly payroll varies (joiners/leavers, bonuses, overtime, sick days). Same issue P52 caught for engagement seed — demo-realism via probability-weighted draws applies here too.

**🟡-O10 — Out-of-order banner is informational only.** Banner says "Resolve the earlier run before processing newer ones". No inline button to delete/void the Mar 2026 Draft, no link to the draft. User has to scroll down, find the row, click into it.

**🟡-O11 — Shifts is empty.** Active feature on the platform with backend (`/api/shifts/schedule` 200) but no seed templates or assignments. Demo for a buyer who runs shift-based operations (Obayashi's SG entity has site workers; Jennifer's coffee chain has baristas) is a hole.

**🟡-O12 — Compliance action items don't open Policies.** Compliance check produces 7 findings including "No formal grievance handling process" + "No FWA policy in place" + "No itemised payslip system". Action Items list at bottom: "Establish grievance handling process / Draft FWA policy". Clicking these doesn't open `/policies` pre-filtered to "grievance" or "FWA" template. The value chain `gap-detected → fix-now` is broken at the handoff.

**🟡-O13 — Attendance "Monthly Summary" reads as broken.** "1/1 Days Present, 1 Late Day, 0 Absent, 0h 0m Avg Hours/Day" with a single record "2026-05-06 05:52 pm clock in, --:-- clock out, 0h 0m, Late". Demo Admin has clocked in once (and never clocked out) in 13 days. The card says "0h 0m avg" — strictly correct but reads as "this employee never works".

**🟡-O14 — Brand inconsistency Central vs Arbor.** Product is branded "Central — HR Advisory" in `<title>`, sidebar, login, dashboard. But `/help` page subtitle: "_Get started with Arbor_" + "_Arbor is your AI-powered HR compliance assistant_". The floating shadow agent button reads "Ask Central (Ctrl+Shift+A)" but the engineering-side product name is still Arbor. Demo viewer will notice.

**🟡-O15 — Analytics "75% local" label.** Top stat reads `28 / 75% local` but the breakdown shows 19 Local (68%), 2 PR (7%), 3 SP, 2 EP, 2 WP. The 75% is **Local + PR** (which both count as Singapore citizens-or-PRs for MOM purposes). Label should read "75% local + PR" or "75% Singaporean / PR" to avoid confusion.

**🟡-O16 — Rajesh exit interview present while active manager.** `/exit-interviews` shows Rajesh Kumar's submitted interview (Retirement theme, 30 Apr 2026), yet `/team` dashboard treats him as currently active manager of 7 reports. If exit-interview submission isn't meant to terminate someone, the workflow needs labeling; if it is, the offboarding pipeline is incomplete.

**🟡-O17 — Approvals page narrow scope.** Subtitle: "_Review and action pending timesheet entries and inventory requests_". Leave + claims + appraisal approvals live on their own pages. A unified Pending Actions inbox would aggregate.

**🟢-O18 — Settings observation paths inconsistent.** "OBSERVED PATTERNS" lists "/dashboard 2 visits" alongside friendly labels like "Advisory 1 visit" and "Calculators 1 visit". Inconsistent — should be one or the other.

---

## Round 2 — Grace Koh (HR Manager) walk

**🟠-H1 — HR Manager sees full platform-admin surface in sidebar.** Grace's left nav includes all 30 owner-level items (Admin, Integrations, Reports, Analytics, Settings, etc.). Direct page access succeeds:

- `/admin` → 200, full UI renders (KB Management, Audit, QA Sessions, QA Metrics)
- `/settings/integrations` → 200, can see/click Connect for every integration

However the underlying admin API endpoints **return 404** to HR Manager:

```
/api/admin/regulatory_updates → 404
/api/admin/feedback → 404
/api/admin/audit_logs → 404
/api/admin/qa_sessions → 404
```

So the data is gated, but the **frontend surfaces are not gated**. A
buyer in their first hour testing as their HR Manager will:

1. Click `/admin` → see "Admin & Operations" with full tab strip
2. Click any tab → see metric tiles populated (because the _summary_
   endpoint they share isn't gated, e.g., `/api/admin/overview` shows
   the same KB stats as for owner)
3. Then they'll wonder why some actions silently fail

**Verdict:** HR-level role should not render the Admin sidebar item
at all (move it under owner-only). At minimum the route guard should
redirect HR to `/dashboard` like it does for IC.

**✅-H2 — HR has PII access** (as expected). `/api/employees/1` returns `nric_fin`, `bank_account_number`, `salary_monthly` — required for payroll/tax work. Backed by `hr_manager` role check.

**✅-H3 — HR-bounded views work.** `/api/leave/applications` returns all 12, `/api/claims` returns all 6, `/api/employees` returns 28. No tenant leak (all `company_id: 1`).

**🟡-H4 — Grace's `team_size = 0`.** She's an HR Manager not a line manager (no one reports to her in `Employee.reporting_manager_id`). Correct per P55. But dashboard does not differentiate "0 because you have no direct reports" vs "0 because everyone is OK today". A clarifying caption would help.

---

## Round 3 — Rajesh Kumar (line-manager, 7 reports) walk

**✅-R1 — P55 derived-manager scope works live.**

```json
{ "team_size": 7, "team_members": [Ahmad, Chen Wei, Marcus, Nguyen, Priya, Samuel, Sato Yuki] }
```

All 7 are confirmed Engineering reports — derived from `reporting_manager_id = 3` (Rajesh's employee id).

**✅-R2 — Team page narrows correctly.** `/team` renders 7-member directory with minimal fields (name, email, designation, dept, confirmation_status). Pending Approvals card: 1 claim, 1 appraisal — both correctly counted from Rajesh's scope.

**✅-R3 — PII boundary holds.** `/api/employees/26` (Marcus, Rajesh's direct report) → **403**. Confirms that even within scope, full PII profile requires `hr_manager`+ role; manager only gets the slim `/team/members` projection.

**✅-R4 — Out-of-scope blocked.**

```
/api/employees/1 (Tanaka, not in his team)        → 403
/api/employees      (full list)                   → 403
/api/payroll/runs                                 → 403
/api/recruitment/candidates                       → 403
/api/recruitment/jobs                             → 403
/api/inventory/items                              → 403
/api/exit-interviews                              → 403
```

**🟡-R5 — Engagement view shows lowest-question copy.** "Latest pulse: H2026 Pulse — Mar 2026 / Lowest: 'I have had opportunities at work to learn and grow.' (2.6)". Good per-question depth for managers. But the **engagement card on Rajesh's team page references the Mar 2026 pulse** even though there's an Apr 2026 pulse listed at owner level (`23/28 (82%) — Open`). Either Rajesh's team hasn't responded to Apr yet, or the per-team aggregate is one cycle behind. A "based on cycle Mar 2026 (Apr 2026 still open)" caption would clarify.

**🟢-R6 — Frontend manager-detection still has the residual flash** noted in `2026-05-07` session (`P4-QW` follow-up): /me lacks `has_reports`, so the manager UI shows a brief loading state before backend confirms scope. Not a defect, just deferred.

---

## Round 4 — Marcus Tan (IC, on probation) walk

**✅-M1 — IC nav is correctly scoped.** 13 items, all `/my-*` plus Advisory / Settings / Help. No Admin, no Payroll-mgmt, no Team. Direct `/admin`, `/payroll` → redirected back to `/my-dashboard`.

**✅-M2 — PII view of self is safely masked.** `/api/employees/me` returns `nric_fin: "S****115N"`, `bank_account_number: "********79-4"`, `work_pass_number: "****"`. Last-4 visible. Date of birth + home address are visible (his own, acceptable).

**✅-M3 — Cross-employee blocked.**

```
/api/employees/26 (his own profile, by id)        → 403
/api/employees/4  (his manager Rajesh)            → 403
/api/employees/1                                  → 403
/api/employees    (list)                          → 403
/api/payroll/runs                                 → 403
/api/recruitment/candidates                       → 403
/api/inventory/items                              → 403
```

**✅-M4 — Scoped data correctly filtered.** `/api/leave/applications` returns 2 rows for Marcus (his own + one in his manager's scope of which he's the subject). `/api/claims` returns 2 rows similarly. `/api/training/records` 200 — verified only his own. P56 (action-vs-analytics scope asymmetry) holds.

**🟠-M5 — Probation auto-transition broken** (also flagged in O8).

```
start_date         : 2026-01-06
probation_months   : 3
probation_end_date : ""   (empty!)
confirmation_status: "on_probation"   (should be "confirmed" by now)
today              : 2026-05-19
```

There's no scheduled job that flips probation → confirmed when 3
months elapse, and HR has no nudge surface. Marcus is in this
limbo state — should have triggered an HR action ~6 weeks ago. Two
fixes:

- Compute `probation_end_date` deterministically (start_date +
  probation_months) on employee create, store and surface it.
- Cron job (daily) that sets `confirmation_status = "confirmed"`
  on probation_end_date pass, and emits an HR notification +
  Compliance-check finding if it isn't actioned.

**🟡-M6 — Apply for Leave modal exposes every leave type to every gender.** Marcus (male) sees "Maternity Leave" in the combobox. Backend should reject, but UI clutter implies it's possible. Should filter by gender + tenure (e.g., Maternity is female-only; Childcare requires marital status married + child; FWA is universal).

**🟡-M7 — My Payslips shows only Apr 2026** despite Feb 2026 payroll being "Approved". Plausible policy ("only Paid runs are visible to employee"), but no copy explaining. A "Approved (pay date 7 Mar 2026)" line would set expectation.

**🟡-M8 — My Engagement copy is excellent** ("Last pulse, your team raised growth. HR did: launch L&D pilot. Linked to: Q2 Engineering L&D — every IC has approved budget by end of Q2."). Closes the loop per the P50–P53 patterns. ✅ No defect — flagged because it's the strongest value-flow page on the platform and the rest of the IC pages should mirror this telling-the-story pattern.

---

## Cross-cutting / systemic findings

**🟠-X1 — Headcount source of truth missing.** Reports says 29, Employees says 28, Lifecycle says 28. Either:

- Demo Admin (`user_id: 1`) is sometimes counted (Reports), sometimes not (Employees / Lifecycle), OR
- A `is_active=False` row is included in one query and not in others.

Fix: pick one — typically "employees where `is_active=True` AND `start_date <= today` AND (end_date IS NULL OR end_date >= today)" — and route every headcount card through the same function.

**🟠-X2 — Advisory KB routing too broad.** `/api/advisory/history/...` shows `domains: ["general"]` for a CPF question. The domain classifier upstream of the ReAct loop is matching everything as `general`. This bypasses the per-domain KB retrieval pattern (CPF KB has 8 provisions including the OW ceiling 2026 increase) and the LLM falls back on training data — hence the stale OW-ceiling answer. Fix at the classifier, not the model.

\*\*🟡-X3 — Two visible /api/auth/me 401s on login flow are landing-page-anon expected — but they polluted the console for first-time visitors. Move that probe behind a localStorage check.

**🟢-X4 — Notifications inbox count rendered as a small "2" badge** on multiple pages. The badge increments across navigation (sidebar pre-render reads from somewhere, then the freshly-loaded page renders its own count). Slight flicker, not a defect.

---

## Codebase audit — confirmed root causes + adjacent gaps

Spawned three parallel specialist audits after the live walk
(arbor-platform-specialist, advisory-safety-chain-specialist,
arbor-web-specialist) plus a security-reviewer sweep. Confirmed
findings below with file:line.

### C1 — Probation auto-transition is structurally absent

**Diagnosis:** `grep -rn 'APScheduler|BackgroundScheduler|celery|on_event'` against `src/hr_advisory/` returns zero hits. There is no `jobs/` directory, no scheduler, no FastAPI startup task. Probation state is purely event-driven by manual HR action.

Evidence:

- `src/hr_advisory/api/routers/employees.py:3178` `GET /employees/probation/due` — read-only listing of employees within 30d of `probation_end_date`. No writer.
- `src/hr_advisory/api/routers/employees.py:3238` `POST /employees/{id}/confirm` — flips `confirmation_status="confirmed"` but requires manual HR call.
- `src/hr_advisory/api/routers/employees.py:3261` `POST /{id}/extend-probation` — only path that writes `probation_end_date`.
- **Employee create path never computes `probation_end_date = start_date + relativedelta(months=probation_months)`.** Hence Marcus's empty string.

**Fix proposal:**

1. On employee create/update (employees.py ~line 308), compute and store `probation_end_date` deterministically.
2. Add APScheduler in `platform.py` startup that runs daily, flips `on_probation → confirmed` where `probation_end_date <= today`, writes an `EmploymentEvent` AND an `AuditLogEntry` for the chain.

Adjacent gap: extended probation relies on the same missing tick.

### C2 — Headcount split across 4 independent queries

| Surface                       | File:line                                                 | Filter                       |
| ----------------------------- | --------------------------------------------------------- | ---------------------------- |
| /reports dept breakdown (29)  | `reports.py:63`                                           | `is_active=True` only        |
| /strategy/lifecycle hero (28) | `strategy.py:175` via `_employees_for_company` `:155-163` | `is_active=True` + cache_ttl |
| /employees list (28)          | `employees.py` list endpoint                              | default `is_active=True`     |
| /analytics (28)               | `analytics/engine.py`                                     | independent DataFlow query   |

**Diagnosis:** No shared helper. The +1 in `/reports` is almost certainly a row with `is_active=True` AND `confirmation_status="terminated"` — the termination path at `employees.py:3485` may write only one of the two fields.

**Fix:** Create `services/headcount.py::get_active_employee_count(company_id, as_of_date=None)` defining "active" as `is_active=True AND (end_date IS NULL OR end_date > as_of_date) AND confirmation_status != 'terminated'`. Replace all four call sites. Audit termination path to ensure both writes are atomic.

### C3 — Advisory has no input-side domain classifier

**Diagnosis:** `advisory_engine.py:1066-1104` (`_extract_domains_from_tools`) assigns domains AFTER the LLM emits `search_kb(domain=...)` calls. **There is no pre-retrieval domain classifier.** The "Step 6: Domain Detection" advertised in the system prompt (line 326) does not exist as code. When the LLM answers from parametric memory (as it did for the CPF question), no `search_kb` is called, domains falls back to `["general"]`, and retrieval is effectively "no-domain → rank all → top-k". The stale OW-ceiling answer leaked from the model's pre-2026 training data.

**Fix:**

1. Add deterministic keyword/regex domain detector (cpf, sdl, ow ceiling, ordinary wages, AW, employer rate → `cpf`; itemised payslip, KET, EA s95A → `employment_act`; etc.)
2. Pre-seed retrieval with detected domains BEFORE the LLM turn.
3. Use `tool_choice={"type":"function","function":{"name":"search_kb"}}` for the first iteration to force at least one KB call.
4. Re-rank top-k restricted to detected domains.

### C4 — Citation array silently dropped

**Diagnosis:** Citations ARE plumbed when present (`advisory_engine.py:1104, :950-951`), but they're derived **only from observed `search_kb` tool calls**. When the LLM answers without invoking `search_kb`, `_extract_citations` returns `[]`. The history serializer at `advisory.py:166-167` correctly omits `provisions_cited` when empty. Result: the field never appears, exactly the prod symptom.

**Fix:** Same as C3 — force `search_kb` on every advisory turn, OR reject responses with `len(citations) == 0` unless the question is non-statutory (set domain="non_statutory" explicitly).

### C5 — Onboarding "Completed at 0%" is structural

**Diagnosis:** `onboarding.py:323-353` (`_update_assignment_status`) — when `total == 0` (template has no role-matching steps), writes `completion_percentage: 0.0` but does NOT set status. **`status` and `completion_percentage` are stored independently on `OnboardingAssignment`**, so a seed script writing both fields directly to DataFlow (or a status-only update in a separate code path) can produce inconsistent state.

**Fix:** Add a `__post_init__`-style invariant — reject `status="completed"` writes unless `completion_percentage >= 100.0 AND total > 0`. Better: add a DB-level CHECK constraint, or derive `status` from `completion_percentage` (single source of truth).

### C6 — Goal duplicate render — backend likely

**Diagnosis:** `apps/web/src/app/(dashboard)/goals/page.tsx:89-101` — `grouped` is built by pushing every API row into `map[g.status]`. No client-side dedupe. Counter `items.length` on line 303 would match render count, so if user sees 6+7 mismatch, the backend `goalsApi.list()` is returning either a duplicate row (same id) OR two rows with different ids but identical content (e.g., cartesian against a goal_checkins JOIN missing DISTINCT).

**Fix:**

1. Frontend defense-in-depth: dedupe by `g.id` in `fetchAll` (line 73): `setGoals(Array.from(new Map(g.goals.map(x => [x.id, x])).values()))`.
2. Backend (`/api/goals` handler): add `DISTINCT` or fix the cartesian join.

### C7 — RBAC sidebar leak (HR sees admin nav)

**Diagnosis:** `apps/web/src/components/shell/NavigationSidebar.tsx:473` — only branches on `role === "employee"`:

```ts
const isEmployee = user?.role === "employee";
const bottomNavItems = isEmployee
  ? employeeBottomNavItems
  : adminBottomNavItems;
```

Any non-employee role (hr_manager, owner, anything else) gets the full `adminBottomNavItems` (lines 285-321), including `nav.admin → /admin` (303-307) and `nav.integrations → /settings/integrations` (309-313). **No per-item role predicate anywhere in the file.** Backend protects routes; frontend leaks the surface.

**Fix:** Add `requiredRole?: "owner" | "owner|hr_manager"` to `NavItem`. Gate Admin / Integrations to `owner` only. Gate Approvals / Reports / Analytics to `owner|hr_manager`. Filter in render: `coreNavItems.filter(canSee(user.role))`. Per P49, use a permission predicate, not a role proxy.

### C8 — Leave-type modal shows all types regardless of gender

**Diagnosis:** `apps/web/src/app/(dashboard)/my-leave/page.tsx:259` fetches `leaveApi.listTypes()` and renders every type unfiltered at line 542-546. No gender/marital filter. Employee gender from `/api/employees/me` is never read.

**Fix:** Backend `/api/leave/types` should accept `employee_id` and filter by `Employee.gender` (maternity → female, paternity → male, childcare → has children). Frontend passes current user's `employee_id`. Defense-in-depth: also filter in `ApplyLeaveModal` based on `useAuth().user.gender`. Per the no-naive-fallback rule, fix at the API contract, not just the dropdown.

### C9 — Advisory orphan history is a frontend rewrite

**Diagnosis:** `apps/web/src/app/(dashboard)/advisory/page.tsx:43-48` — frontend `cleanPreview` substitution rewrites any conversation whose stored `last_message` preview contains the legacy guardrail string `"I'm having trouble processing your question"` into the placeholder `"(earlier reply unavailable)"`. The orphan rows are real persisted conversations whose assistant turn was the legacy guardrail-fallback (a transient screening or 5xx response stored to DB). The 3→1 discrepancy after refresh is a separate stale-state issue: `handleConversationStart` calls `refreshConversations()` but error paths leave React Query holding pre-delete rows.

**Fix:** Server-side purge or hide. Either `DELETE WHERE text LIKE 'I''m having trouble%'` or backend marks such turns `hidden=true` so the sidebar omits them entirely. Also invalidate the conversations query after every mutation/SSE-error, not only on stream success.

### C10 — Security: audit-log gaps on payroll + employee mutations

**🔴 GAP — `payroll.py:475-502` `approve_payroll_run`, `:510-597` `mark_payroll_paid`, `:605-623` `cancel_payroll_run`** — NONE call `record_event()` or any `_audit_*` helper. These are the highest-financial-impact actions in the system (writing `status: approved`, `status: paid` cascading to every payslip + approved claim for the period). Per P58 they must dual-write to `AuditLogEntry`. Also no `check_rate_limit`.

**🔴 GAP — `employees.py:2401-2559` `update_employee` (PATCH `/employees/{id}`)** — writes `confirmation_status`, `probation_end_date`, `is_active`, `salary_monthly`, `reporting_manager_id` via a 38-field allow-list with NO `record_event()` call. EmploymentEvent rows are mutable; the immutable chain is missing. Mass-mutation endpoint with zero chain coverage.

**🟡 PARTIAL — `recruitment.py:284-332` `_log_candidate_activity`** — dual-writes correctly, but the action-key derivation is lossy: `action.lower().replace(" ", "_").replace("changed_to_", "stage_")` can collide on different actions, weakening chain analytics.

**🟡 PARTIAL — HR Manager can self-mutate `confirmation_status` on their own row** via `PATCH /employees/{their_own_id}` — there is no `caller != target` check for sensitive fields in `update_employee`. Combined with the missing audit log, an HR manager can quietly self-confirm.

**Fix:**

1. Add `_audit_payroll(run_id, company_id, action, actor_id, details)` modeled on `_audit_claim` and call from approve/mark-paid/cancel + add `check_rate_limit`.
2. Add `_audit_employee(employee_id, company_id, action, actor_id, fields_changed)` and call from `update_employee` whenever sensitive fields change.
3. In `update_employee`, refuse self-mutation of `confirmation_status` / `salary_monthly` / `is_active` / `reporting_manager_id` where `target.user_id == current_user.sub`.
4. In `recruitment._log_candidate_activity`, preserve original action verb instead of collapsing.

### What still holds ✅ (security)

- `leave.py:83-87`, `claims.py:59-63`, `attendance.py:663-667` — self-approval blocks present (P57).
- `employees.py:1977-2004` — `EMPLOYEE_SELF_SERVICE_FIELDS` whitelist excludes `confirmation_status` / `probation_end_date` / `salary_monthly` / `reporting_manager_id` from `PUT /employees/me`.
- `recruitment.py:345, 724, 758` — uses `Depends(require_role("owner", "hr_manager"))` (DI), 403 enforced before handler runs.

---

## What held — security ✅

(complements the existing 11/12 round-2 findings)

- ✅ Owner JWT decoded to `{ sub: "1", email: ... }` — no internal
  flags or claims leaked.
- ✅ HR has full PII; line-manager and IC do not.
- ✅ Manager scope derives from `reporting_manager_id` not from a
  role string (P55 verified live).
- ✅ Direct-id employee fetch is 403 even within scope (P56
  action-vs-analytics asymmetry verified).
- ✅ `/admin` route guards: IC redirected to `/my-dashboard`; HR
  route allowed but backend admin endpoints 404. (Mixed result —
  see H1 for UI gap.)
- ✅ `/api/auth/login` rejects empty/wrong credentials with 422 / 401. Trying SQL-injection on email returns 422 (Pydantic).
- ✅ No admin / payroll PII visible to Rajesh or Marcus.

---

## Recommended fix order

| Priority | Finding                                    | Effort | Why                                                             |
| -------- | ------------------------------------------ | ------ | --------------------------------------------------------------- |
| P1       | O2 / X2 — Advisory KB domain routing       | 4h     | Flagship feature returns stale answers; classifier fix          |
| P1       | M5 / O8 — Probation auto-transition        | 3h     | Real HR workflow; affects 2+ seeded employees; cron + nudge     |
| P1       | H1 — HR Manager sees admin nav             | 30m    | RBAC trust signal; sidebar filter by role                       |
| P2       | O1 / C4 — Advisory citations missing       | 3h     | Landing page promise; emit citations in response model          |
| P2       | X1 — Headcount source of truth             | 2h     | Inconsistent numbers across pages = "platform isn't accurate"   |
| P2       | O3 — Advisory orphan history entries       | 1h     | Either fix the stale client cache or hide entries with no reply |
| P2       | O4 — Goal duplicate render                 | 1h     | Buyer screenshot risk                                           |
| P2       | O6 — Onboarding "Completed at 0%"          | 1h     | Derive completion or sync seed                                  |
| P3       | O12 — Compliance → Policies hand-off       | 2h     | Closes the gap-detect → fix-now loop                            |
| P3       | O9 — Payroll seed realism (probabilistic)  | 2h     | Apply P52 to payroll seed too                                   |
| P3       | O11 — Shifts empty                         | 3h     | Seed 1 week of warehouse shifts                                 |
| P3       | O14 — Brand consistency (Central vs Arbor) | 1h     | Replace "Arbor" in Help copy                                    |
| P4       | O15 — Analytics "75% local" label          | 15m    | Label fix                                                       |
| P4       | M6 — Apply-leave filter by gender          | 1h     | UI clutter                                                      |
| P4       | O13 — Attendance empty-state copy          | 30m    | "1 record" reads as "broken"                                    |
| P4       | O18 — Settings observation labels          | 15m    | Cosmetic                                                        |
| P5       | M7 — My Payslips "Approved" copy           | 15m    | Set expectation                                                 |
| P5       | R5 — Engagement card cycle caption         | 15m    | Clarify                                                         |
| P5       | O5 — Reports run-empty cards               | 30m    | "Run a report" CTA when data exists is misleading               |

**Total P1+P2 = ~17h.** Worth shipping before next Obayashi /
Jennifer demo. The flagship feature reliability + RBAC visual gate
are the credibility-defining issues.

---

## New P0/P1 from codebase audit (security + audit-log)

These are not visible in the live walk but emerged from the parallel
codebase audit. They're security-grade and need to ship before next
prod deploy.

| Priority | Finding                                                               | Effort | Why                                                                                                            |
| -------- | --------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| **P0**   | C10 — Payroll approve/mark-paid/cancel have NO audit log              | 2h     | Highest-financial-impact actions; P58 immutable-chain violation; ISO 27001 + PDPA s24 fail                     |
| **P0**   | C10 — `update_employee` PATCH writes salary/status without audit      | 2h     | 38-field mass-mutation endpoint with zero immutable trail; insider-threat exposure                             |
| **P0**   | C10 — HR Manager can self-mutate `confirmation_status` on own row     | 30m    | Privilege escalation: `update_employee` lacks `caller != target` check on sensitive fields                     |
| **P1**   | C10 — Payroll endpoints lack `check_rate_limit`                       | 30m    | Bulk approve/cancel abuse surface — round-12 already added rate limit on HR-decision endpoints, payroll missed |
| **P2**   | C10 — `recruitment._log_candidate_activity` lossy action-key collapse | 1h     | Audit-chain analytics weakened by collisions in event_type                                                     |

**Cross-reference to existing patterns:** these gaps re-violate
patterns P58 (hash-chained audit log alongside mutable record) and
P57 (self-approval block on every role). The pattern catalogue is
in `.claude/skills/project/security-patterns.md`.

---

## Summary

**Live walk:** 4 roles × ~30 routes each. RBAC mostly holds (P55,
P56, P57 verified live). The flagship advisory is unreliable for
buyer demos until citations + KB routing are fixed. Probation
auto-transition is structurally absent. HR Manager sees admin nav
items she has no business clicking. Goal renders a duplicate.
Onboarding can show "Completed at 0%". Headcount disagrees with
itself across 4 pages.

**Codebase audit:** Confirms the live findings have specific
root-cause file:line locations (above). Adds three P0 security gaps
on payroll + employee mutations missing immutable audit trail, and
an HR-Manager self-mutation escalation. Adjacent gaps surfaced
across recruitment audit-chain integrity and the missing
deterministic compute-and-store of `probation_end_date`.

**Total P0+P1+P2 = ~22h** (5h P0 security + 17h P1+P2 demo-readiness).
P0s are pre-deploy blockers. P1+P2 are pre-demo blockers.

After fixes ship: run a fourth red-team round to verify all 10
codebase findings (C1-C10) are closed, and verify the orphan
advisory conversation rows are purged from prod DB.
