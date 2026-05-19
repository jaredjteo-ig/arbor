# P5-PL — Polish bundle (5 small items)

**Source:** `04-validate/13-redteam-comprehensive-2026-05-19.md`
findings O14, O15, M6, M7, O13.

**State:** Five standalone polish items each under 1 hour. None
gate any other work. Ship as a single combined commit for tidiness,
or individually.

---

## P5-PL-1 — Brand consistency: Central vs Arbor (O14)

- **Symptom:** Product is branded `Central — HR Advisory` everywhere
  except `/help`, whose subtitle reads `"Get started with Arbor"` +
  `"Arbor is your AI-powered HR compliance assistant"`. Buyer notices
  the brand mix on the help page.
- **Where:** `apps/web/src/app/(dashboard)/help/page.tsx` — search
  for the literal strings `"Arbor"`, `"with Arbor"`.
- **Fix:** replace every user-facing `"Arbor"` reference with
  `"Central"`. Keep `"Arbor"` only in internal-facing strings (toast
  IDs, dev console messages, telemetry tags) — those are engineering
  scaffolding, not buyer-facing.
- **Acceptance:**
  - `/help` page contains zero occurrences of the word "Arbor".
  - Grep `apps/web/src/app -name "*.tsx"` for `Arbor` returns only
    internal/scaffolding hits.
- **Regression test:**
  `tests/regression/test_p5_pl_no_arbor_in_user_copy.py` — source-pin
  that user-facing copy doesn't contain "Arbor".
- **Effort:** 15 min.

---

## P5-PL-2 — Analytics "75% local" label fix (O15)

- **Symptom:** `/analytics` top tile reads `28 / 75% local`. But the
  pass-type breakdown shows Local = 19 (67.9%). The 75% is actually
  Local + PR (21/28). Label is misleading — a buyer would call it
  out as inaccurate.
- **Where:** `apps/web/src/app/(dashboard)/analytics/page.tsx` —
  the workforce composition tile.
- **Fix:** label "75% local + PR" or "75% Singaporean / PR" (the
  composite that matters for MOM/CPF purposes). Surface the
  breakdown ratio with a tooltip: "Local (19) + PR (2) = 21 of 28".
- **Acceptance:**
  - Tile text reads "75% local + PR" (or equivalent compound label).
  - Hover tooltip explains the math.
- **Regression test:** none — pure copy fix.
- **Effort:** 15 min.

---

## P5-PL-3 — Apply-leave modal gender filter (M6)

- **Symptom:** Marcus (male) opens the Apply for Leave modal and
  sees "Maternity Leave" in the dropdown. Backend rejects on submit,
  but the UI clutter is wrong.
- **Where:**
  - Backend: `/api/leave/types` in `src/hr_advisory/api/routers/
    leave.py` — accept `employee_id` query param and filter by
    `Employee.gender` / `Employee.marital_status` / dependents.
  - Frontend: `apps/web/src/app/(dashboard)/my-leave/page.tsx:259`
    — pass `employee_id` when listing types.
- **Fix:** backend filters per the leave-type-eligibility map:
  - `maternity` → female only.
  - `paternity` → male only.
  - `childcare` / `infant_care` / `extended_childcare` → requires
    at least 1 dependent under 7 / under 2.
  - `adoption` → either gender, requires dependent flag.
  - `shared_parental` → male only, with eligible spouse.
  - `ns_reservist` → male only.
  - All others (annual, sick, hospitalisation, unpaid) → universal.
- **Acceptance:**
  - Marcus's modal does NOT show: Maternity, Childcare, Infant Care,
    Adoption.
  - Marcus's modal DOES show: Annual, Sick, Hospitalisation,
    Paternity (if dependent), NS Reservist, Unpaid.
  - Female test user (e.g., Grace Koh) sees Maternity / Childcare
    where eligible.
- **Regression test:**
  `tests/regression/test_p5_pl_leave_type_gender_filter.py` —
  hit `/api/leave/types?employee_id=<marcus_id>` and assert the
  returned list excludes maternity.
- **Effort:** 1 hour (backend filter map + frontend pass-through).

---

## P5-PL-4 — My Payslips "Approved" status caption (M7)

- **Symptom:** Marcus's `/my-payslips` shows only Apr 2026 (Paid)
  even though Feb 2026 is Approved. No copy explains why approved
  payslips aren't visible. Plausible policy ("only Paid runs are
  visible") but the buyer can't tell.
- **Where:** `apps/web/src/app/(dashboard)/my-payslips/page.tsx`.
- **Fix:** add an info banner: "Approved payslips become visible
  here once your employer marks the run as paid. Your Feb 2026
  payslip is currently Approved (expected pay date: 7 Mar 2026)."
  Source the awaiting-payment data from `/api/payroll/my-payslips?
  include_approved=true`.
- **Acceptance:**
  - Marcus's `/my-payslips` shows the Paid Apr payslip + an info
    card for Approved Feb run with expected pay date.
  - Helps him understand "where's my payslip?" without an HR ping.
- **Regression test:** none — copy + minor API field addition.
- **Effort:** 30 min.

---

## P5-PL-5 — Attendance empty-state copy (O13)

- **Symptom:** `/attendance` for Demo Admin shows "1/1 Days Present,
  1 Late Day, 0h 0m Avg Hours/Day" — strictly correct (single
  record, no clock-out) but reads as "this employee never works".
- **Where:** `apps/web/src/app/(dashboard)/attendance/page.tsx` —
  Monthly Summary card.
- **Fix:** when there's exactly 1 record AND clock_out is null AND
  the date is older than 24 h, render an explainer: "Last clock-in
  was N days ago without a clock-out. Avg hours can't be computed
  until at least one full day is recorded." Hide the "0h 0m" tile.
- **Acceptance:**
  - Demo Admin's `/attendance` does NOT show the misleading "0h 0m".
  - Empty state has friendly explainer.
- **Regression test:** none — copy fix.
- **Effort:** 30 min.

---

## Total effort + sequencing

- 15 + 15 + 60 + 30 + 30 = 2.5 hours.
- All five can ship in a single commit (`P5-PL polish bundle`).
- No dependencies on the other P5 items.
- No prod deploy ordering — frontend-only changes plus one API
  filter (P5-PL-3).
