# P4-QW — Audit quick wins (1 day total)

**Source audits:**

- `04-validate/07-buyer-audit-2026-05-08.md` — buyer/marketing lens
- `04-validate/08-functional-audit-2026-05-12.md` — daily-ops lens
- `04-validate/09-redteam-roles-2026-05-12.md` — role-based lens

**State:** 8 standalone polish items, each <2 hr. Land any time. None
of these gate the manager-role work (P4-MG) or the marketing-surface
work (P4-LP).

**Recommended bundling:** single commit per item, or one combined
"P4-QW polish bundle" commit. No interlocks between items.

---

## P4-QW-1 — Role-aware post-login redirect

- **Source:** `09-redteam-roles` P1-B.
- **Symptom:** Marcus (employee) logs in → routed to `/dashboard` →
  red "Access Denied — restricted to administrators" page. Sidebar
  correctly renders employee links. Login flow is role-blind.
- **Where:** post-login redirect logic. Likely in
  `apps/web/src/app/login/page.tsx` (or `useAuth` hook).
- **Fix:** branch on `user.role`:
  - `owner` | `hr_manager` → `/dashboard`
  - `employee` → `/my-dashboard`
- **Acceptance:**
  - Logging in as `marcus.tan@central-solutions.sg` lands on
    `/my-dashboard` directly with no Access Denied flash.
  - Logging in as `grace.koh@central-solutions.sg` still lands on
    `/dashboard`.
  - Logging in as `demo@central.kailash.ai` still lands on `/dashboard`.
- **Regression test:** Playwright spec — login as employee + assert URL
  is `/my-dashboard` and no "Access Denied" text on first paint.

---

## P4-QW-2 — Friendly 404 for /payroll/runs and invalid run IDs

- **Source:** `08-functional-audit` P1-1.
- **Symptom:** direct nav to `http://136.110.51.61/payroll/runs` (no
  id) renders raw FastAPI Pydantic validation JSON:
  ```
  [{"type":"int_parsing","loc":["path","run_id"],"msg":"Input should
  be a valid integer, unable to parse string as an integer","input":"NaN"}]
  ```
  Same shape on any invalid id (typo, stale link, bookmarks).
- **Where:** Next.js dynamic route `apps/web/src/app/(dashboard)/payroll/[id]/page.tsx`
  - the error boundary that surfaces 4xx bodies.
- **Fix:**
  - Either redirect `/payroll/runs` → `/payroll`, OR add a static
    Next.js page at that path that renders "Pick a run".
  - For `/payroll/{badid}` — catch the 422/404 and render a friendly
    "Payroll run not found — back to list" page, not the raw JSON.
- **Acceptance:**
  - GET `/payroll/runs` → 200 with the runs list, not raw FastAPI JSON.
  - GET `/payroll/999999` → friendly 404 page, not raw JSON.
- **Regression test:** Playwright — visit both URLs as Grace, assert
  no "int_parsing" or "loc" strings on page.

---

## P4-QW-3 — Honest leave-entitlement labelling

- **Source:** `09-redteam-roles` P2-B.
- **Symptom:** dashboard says "Per Employment Act" on the Annual
  Leave card but the numbers don't scale with years of service.
  Rajesh has 4 years service, shows 7 annual; SG EA Schedule 4 at
  4 years is 10 days.
- **Decision required:** is the 7-day allocation **company policy**
  (legal — many SG SMEs do flat) or **EA scaling not implemented**?
- **Fix — Path A (relabel):** if it's company policy, change copy on
  the Annual Leave card from "Per Employment Act" → "Per company
  policy" (or "Per your employment contract"). Add a tooltip:
  "Your company offers a flat allocation. The Employment Act minimum
  is 7 days at year 1 scaling to 14 at year 8."
- **Fix — Path B (implement scaling):** implement EA Schedule 4 table
  (year 1: 7 / year 2: 8 / ... / year 8+: 14) in the entitlement
  computation. Add a unit test pinning the table.
- **Where:** Likely `src/hr_advisory/services/leave_calculator.py` or
  similar; dashboard component in
  `apps/web/src/app/(dashboard)/my-dashboard/page.tsx`.
- **Acceptance:**
  - If Path A: dashboard copy reads "Per company policy" with tooltip.
  - If Path B: Rajesh (4 yrs) sees 10 annual; Marcus (5 months) sees
    7 annual; new hire <3 months sees prorated.
- **Regression test:** either a Playwright copy check (Path A) or a
  pytest table-driven test on the entitlement table (Path B).

---

## P4-QW-4 — Fix hospitalisation-vs-sick-leave framing

- **Source:** `09-redteam-roles` P2-C, also `07-buyer-audit`.
- **Symptom:** dashboard shows Sick Leave 14 and Hospitalisation
  Leave 60 as separate buckets, implying 74 days protected. SG rule
  is 60 inclusive of 14 — they are NOT additive.
- **Fix options (pick one):**
  - **A:** Merge into one "Medical Leave" card with two sub-rows
    "Outpatient (14)" + "Total inclusive of hospitalisation (60)".
  - **B:** Keep two cards but add a disclaimer below
    Hospitalisation: "Inclusive of the 14 outpatient days above
    — not additional."
- **Where:** dashboard component for the leave-balance card. Same file
  as P4-QW-3.
- **Acceptance:** visually impossible to read "I have 74 medical days"
  off the dashboard.
- **Regression test:** Playwright — assert the disclaimer text is
  present on the medical card.

---

## P4-QW-5 — Fix NRIC mask shape

- **Source:** `09-redteam-roles` P2-A.
- **Symptom:** My Profile shows NRIC as `****115N` (4 hidden + 4
  visible = 8 chars). SG NRIC is 9 chars (`S1234567A`). Correct
  mask: `S****567A` (1 + 5 stars + 4 visible). The underlying
  helper `mask_nric` in `src/hr_advisory/security/encryption.py`
  already produces the correct shape — something upstream is either
  passing pre-masked data or stripping the first char.
- **Where:**
  - Helper: `src/hr_advisory/security/encryption.py::mask_nric` (correct).
  - Suspect: the `/employees/me` response. Earlier probe shows
    `nric_fin: "T****803C"` from the API for Rajesh — that's actually
    correct (T + 4 stars + 4 visible = 9 chars). So the bug may be
    Marcus-specific or rendering-side.
- **Investigation step before coding:** dump Marcus's `/employees/me`
  response, see what the API returns. If API is right, fix is in the
  React component.
- **Acceptance:** all employees' My Profile shows a 9-char NRIC mask
  with the first character (citizenship-band letter) preserved.
- **Regression test:** pytest table-driven `mask_nric` already exists;
  add a snapshot test on the profile component.

---

## P4-QW-6 — Hide stale onboarding card on legacy employees

- **Source:** `09-redteam-roles` P2-D.
- **Symptom:** Rajesh joined Jan 2022; his dashboard shows "0 of 0
  steps completed" onboarding card with template
  "HR Technology / SaaS Onboarding" — assigned retroactively by a
  seed.
- **Where:** dashboard onboarding-card component.
- **Fix:** hide the card when EITHER:
  - `assigned_at < hire_date - 30 days` (template assigned far after
    the employee joined; almost certainly seed noise), OR
  - `steps_total == 0` (template was never populated), OR
  - `assignment.status == 'completed'`
- **Acceptance:** Rajesh's `/my-dashboard` shows no onboarding card.
  Marcus (Jan 2026 hire) still sees his card if uncompleted.
- **Regression test:** Playwright — login as Rajesh, assert no
  "Onboarding Progress" panel.

---

## P4-QW-7 — Seed at least one work-pass-expiring employee

- **Source:** `07-buyer-audit` P2.
- **Symptom:** "Work Pass Expiring Soon" filter chip on
  `/employees` works mechanically — chip activates, "Clear filter"
  appears, table re-renders with empty state. But none of the 4
  foreign workers (Tanaka, Sato, Ahmad, Nguyen) have a pass
  expiring within the window. The marquee SG differentiator
  doesn't LIGHT UP for a buyer.
- **Where:** `scripts/seed_demo_data.py` — section that seeds
  foreign-worker passes.
- **Fix:** for at least 1 employee with a foreign pass, set
  `work_pass_expiry` to a date 30-60 days from `today`. Document
  in the seed which employee is the "expiring soon" demo case.
  Use the wipe-and-reseed approach in `seeding.md` rule 10.
- **Acceptance:**
  - After re-seed, `/employees` with the filter active shows ≥ 1
    employee.
  - The employee detail page shows a yellow/red badge on the work-pass
    expiry field.
- **Regression test:** pytest — seed and assert at least 1 expiring
  employee.

---

## P4-QW-8 — WICA tooltip in Cost-to-Company calculator

- **Source:** `07-buyer-audit` P2 + `08-functional-audit` (CTC math
  test).
- **Symptom:** Cost-to-Company for SG citizen at $5K services shows
  WICA $0.00 with no explanation. WICA is mandatory only for
  manual workers and non-manual <$2,600/mo — a $5K services citizen
  doesn't trigger the threshold. The $0 reads as a gap for buyers
  in construction (manual workforce).
- **Where:** Cost-to-Company calculator page in
  `apps/web/src/app/(dashboard)/calculators/cost-to-company/page.tsx`.
- **Fix:** inline tooltip next to the WICA row: "WICA is mandatory
  for manual workers and non-manual employees earning <$2,600/month.
  Your inputs don't trigger the threshold." Apply to all 7
  calculator pages where a row reads $0 with caveat.
- **Acceptance:** WICA $0 row has an info-icon with the explanation.
- **Regression test:** Playwright — assert tooltip text is reachable
  via keyboard focus on the WICA row.

---

## P4-QW-9 — Payslip PDF download button on run-detail

- **Source:** `08-functional-audit` P1-2.
- **Symptom:** payslip line-item drill-down works (after P0-3 fix
  shipped in `f1a8394`), but there's no UI button to generate a
  PDF for an individual employee's payslip. The backend endpoint
  `POST /payroll/runs/{run_id}/payslips/{payslip_id}/pdf` already
  exists per `agents/project/sg-payroll-expert.md` — just not
  wired to a button.
- **Where:**
  - BE endpoint already exists in
    `src/hr_advisory/api/routers/payroll.py` (search for
    `/runs/{run_id}/payslips/{payslip_id}/pdf`).
  - FE: `apps/web/src/app/(dashboard)/payroll/[id]/page.tsx`
    `PayslipRow` component — add a "Download PDF" button in the
    expanded detail section.
- **Fix:**
  - Add `downloadPayslipPdf(runId, payslipId)` to
    `apps/web/src/services/api/payroll.ts`.
  - Add a "Download payslip PDF" button in the expanded payslip row
    next to the Statutory Contributions block.
  - Also surface on the employee `/my-payslips/{id}` detail page —
    employees should be able to self-serve their own PDF (verify
    the employee-scoped endpoint `GET /my-payslips/{id}/pdf` exists
    and is wired).
- **Acceptance:**
  - HR Manager on April 2026 run → expand Lim Mei Ling → click
    "Download PDF" → PDF downloads with employee name, period,
    earnings/deductions, employer contributions, and the EA s88A
    footer.
  - Employee on `/my-payslips/{id}` → can self-download own PDF.
  - Employee cannot download another employee's PDF (verify 403).
- **Regression test:**
  - Integration test: admin downloads → 200 + content-type
    `application/pdf` + `Content-Disposition` header with employee
    name.
  - Security test: employee tries to download a colleague's PDF
    → 403.

---

## P4-QW-10 — Fix Compliance page scroll behaviour

- **Source:** `07-buyer-audit` P3.
- **Symptom:** the `/compliance` page didn't respond to
  `window.scrollTo` during the buyer audit — looks like an inner
  scroll container is trapping the user. On a standard 1080p
  laptop, parts of the checklist may be unreachable.
- **Where:** `apps/web/src/app/(dashboard)/compliance/page.tsx` —
  search for `overflow:auto`, `overflow:hidden`, or fixed-height
  panel containers that swallow scroll.
- **Fix:** remove the inner scroll trap. Let the page scroll
  naturally. If the checklist is long, render the full list and
  let `<main>` handle scroll like every other dashboard page.
- **Acceptance:**
  - On a 1280×720 viewport, the bottom of the compliance checklist
    is reachable by normal mouse-wheel / trackpad scroll.
  - The "Ask Central about this" CTAs on every checklist item are
    clickable without trapping focus.
- **Regression test:** Playwright at 1280×720 — scroll to bottom of
  the page and assert the last checklist item is in viewport.
