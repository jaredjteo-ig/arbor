# Functional audit — daily HR operations, 2026-05-12

Different lens from yesterday's marketing/trust audit. The question
here is: **can an HR team at a 500-person SG firm actually do their
work in this tool today?**

Logged in as Grace Koh (HR Manager). Tested the operational
functions a payroll/HR ops team performs every day or month.

---

## P0 — Hard functional blockers

These break the actual statutory job, not just the demo.

### P0-1. CPF e-Submit file has encrypted NRICs

Button `CPF e-Submit File` on payroll detail downloads
`cpf-esubmit-2026-04-01.csv`. Structure is correct (HEADER /
DETAIL × 29 / TRAILER), totals match the dashboard tile
(`19639.00 + 23290.00 = 42929.00`).

But 27 of 29 DETAIL rows show the NRIC field as a
Fernet-encrypted blob:

```
DETAIL,gAAAAABp8PG0TF200_a1gv61RHwEuW8X...==,Tanaka Hiroshi,8000,...
DETAIL,gAAAAABp8PG10De_MRoXUPvKLcyvD1VFTW...==,Lim Mei Ling,8000,...
...
DETAIL,T3135534G,Lily Phang,5200,...     ← only this row decrypted
```

**Effect**: mycpf.gov.sg would reject this file outright. The HR
team cannot meet the monthly CPF deadline using this product.

**Root cause**:
`src/hr_advisory/services/statutory_files.py` reads
`emp.get("nric_fin", "")` directly. The PII column is encrypted at
storage and the export code is missing the decrypt step.

**Fix**: single-line — call `decrypt_pii(employee.nric_fin)` (or the
project's helper) before serialising. Same module also handles IR8A,
IR21, AIS — verify those too.

### P0-2. Bank GIRO file has encrypted account numbers

Same shape, same root cause:

```
EMPLOYEE_NAME,BANK_CODE,ACCOUNT_NUMBER,AMOUNT,REFERENCE
Tanaka Hiroshi,7232,gAAAAABp8PG09NbpC...,12000.00,SALARY-4-2026-04-30
Lim Mei Ling,7232,gAAAAABp8PG1wrbyX...,8391.00,SALARY-4-2026-04-30
...
Lily Phang,7339,408-525800-8,4355.00,SALARY-4-2026-04-30  ← decrypted
```

Bank codes are correct (7232=OCBC, 7375=HSBC, 7171=DBS, 7339=UOB)
and amounts match payslip totals. But the bank rejects on the
encrypted account number.

**Effect**: payroll cannot be paid out via GIRO. HR has to fall
back to manual transfer.

**Fix**: same line as P0-1, applied to `bank_account_number`.

### P0-3. Payslip detail is completely broken

Every payslip row on the run-detail page is clickable. Expanding
ANY row calls:

```
GET /api/payroll/runs/4/payslips/undefined
```

— the frontend never reads the payslip's primary key. So every
payslip shows "No payslip items available" and there is no PDF
download button.

**Effect**:

- HR cannot drill into a single payslip to verify line items
- HR cannot download a payslip PDF for the employee
- The IR8A / AIS workflow that depends on per-payslip drill-down
  is unreachable from the UI

**Fix**: frontend bug — the click handler is reading the wrong
field name (`payslipId` vs `id`, or similar). 1-line fix.

---

## P1 — Major operational gaps

### P1-1. /payroll/runs route leaks raw FastAPI JSON

Direct nav to `http://136.110.51.61/payroll/runs` renders:

```
[{"type":"int_parsing","loc":["path","run_id"],
 "msg":"Input should be a valid integer, unable to parse string as an integer",
 "input":"NaN"}]
```

Two issues:

- The route should not exist (the list is at `/payroll`, detail
  at `/payroll/{id}`). Either redirect `/payroll/runs` → `/payroll`
  or 404 it.
- Even on a real bad `run_id`, the response should be a friendly
  404 page, not raw FastAPI validation JSON.

**Effect**: any customer who bookmarks, pastes a stale link, or
hits an invalid id sees a debug-mode error page in prod.

### P1-2. No way to generate payslip PDF from the UI

Even with P0-3 fixed, there's no visible PDF button on the
run-detail page. The agent doc (`sg-payroll-expert.md`) mentions
`POST /payroll/runs/{id}/payslips/{id}/pdf` exists in the backend,
but the frontend hasn't wired a button.

**Effect**: monthly payslip distribution to employees is manual
work — HR has to send screenshots or build their own template.

---

## What works correctly

These are the operational verbs that DO work today:

| Function                                           | Status                               | Evidence                                                                         |
| -------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------- |
| Payroll list with status (Paid / Draft / Approved) | ✅                                   | 3 runs visible, lifecycle states correct                                         |
| Out-of-order detection                             | ✅                                   | Banner explains exactly what's wrong and why                                     |
| CPF/Bank file generation (mechanically)            | ⚠️ structure correct, content broken | See P0-1 / P0-2                                                                  |
| Run summary totals (Gross/Net/CPF/SDL/FWL/SHG)     | ✅                                   | All 7 dimensions, math correct                                                   |
| Foreign-worker $0 CPF handling                     | ✅                                   | Tanaka/Nguyen/Ahmad/Sato all $0 ✓                                                |
| Cost-to-Company calculator math                    | ✅                                   | $5K SG citizen → $5,861.25 exact                                                 |
| AI advisory with citations                         | ✅                                   | EA-S10 → 2 weeks notice, clickable pill                                          |
| Compliance health check                            | ✅                                   | 6 SG domains, cited statutes, 83% score                                          |
| **Leave approve flow**                             | ✅                                   | Pending 2→1, On Leave Today 1→2, table status flips to Approved — all consistent |
| Employee directory + work-pass filter              | ⚠️ filter wires, no data             | Filter mechanically correct, demo seed has no expiring passes                    |
| Onboarding templates (Excel)                       | ✅                                   | 3 templates, SG default, KPI strip                                               |
| Nudge tray (KET / OT / FWL / CPF deadlines)        | ✅                                   | Surfaces correctly on every page                                                 |

---

## Punch list — sorted by Obayashi blocker risk

| #     | Item                                                               | Effort     | Production-blocking?                              |
| ----- | ------------------------------------------------------------------ | ---------- | ------------------------------------------------- |
| **1** | **CPF e-Submit + Bank GIRO decrypt-on-export**                     | **1-2 hr** | **YES (P0)**                                      |
| **2** | **Payslip expand wires correct payslip_id**                        | **1 hr**   | **YES (P0)**                                      |
| **3** | **Payslip PDF button + endpoint wire-up**                          | **1 day**  | **YES (P0 — required for monthly payroll cycle)** |
| 4     | Friendly 404 + redirect `/payroll/runs` → `/payroll`               | 30 min     | P1                                                |
| 5     | Seed an expiring-work-pass employee                                | 15 min     | Demo-only                                         |
| 6     | Audit other statutory files (IR8A, IR21, AIS) for same decrypt gap | 1 hr       | Discover-then-fix                                 |

**Items 1, 2, 3 are mandatory before any customer runs payroll on
this product.** Until they're fixed, the dashboard math is correct
but the monthly artefacts the customer actually needs (CPF e-Submit
upload, bank GIRO file, individual payslip PDFs) are unusable.

After those three, ~half a day of work, you'd have a real
production payroll cycle.

---

## Bottom line

The **payroll engine is right** — math is correct, foreign-worker
rules are right, totals reconcile across screens. But the **output
layer** that delivers statutory artefacts and employee payslips is
broken in three independent places, all of which would surface in
the first real payroll run.

These are FE-wiring + 1-line BE decrypt issues, not engine bugs.
A single focused day fixes them.
