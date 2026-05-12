# Red-team — role-based user flows, 2026-05-12

Scope: walk through every Central role end-to-end on the live site
(http://136.110.51.61) and identify functional, security, UX, and
permission gaps. Roles covered:

| Role             | Test user           | Notes                                 |
| ---------------- | ------------------- | ------------------------------------- |
| **owner**        | Demo Admin (id=1)   | top of the hierarchy                  |
| **hr_manager**   | Grace Koh (id=25)   | mostly covered in 08-functional-audit |
| **line-manager** | Rajesh Kumar (id=4) | `employee` role + 7 direct reports    |
| **employee**     | Marcus Tan (id=10)  | regular IC, no reports                |

Method: API probes for security boundaries, UI walk-through via
Playwright for each role's daily journeys. Cross-role checks for
data isolation.

---

## P0 — Production blockers

### P0-A. `approve_payroll_run` crashes with 500 on every prod run

**Affects**: owner

`POST /payroll/runs/{id}/approve` (the Draft → Approved transition,
owner-only) returns 500 _Internal Server Error_.

Backend stack trace:

```
kailash.sdk_exceptions.NodeExecutionError:
Database query failed: column "xero_journal_id" does not exist
```

The Xero integration M0..M4 work added `xero_journal_id`,
`xero_exported_at`, `xero_force_counter` to the `PayrollRun` model
(see `models/company_user.py:740-770`), and DataFlow now generates
UPDATE statements that reference those columns. **The matching
migrations (`scripts/migrate_xero_payroll_export.py`,
`migrate_xero_force_counter.py`) were never run on prod because
the Xero deployment was deferred until HTTPS is in place** — see
`workspaces/xero-integration/.session-notes`.

**Effect**: every transition on a payroll run (`approve`, `mark_paid`,
`cancel`, the Xero export itself) crashes. The "Out-of-order payroll
detected" banner on the live site can't be resolved because the Mar
2026 draft cannot be approved.

**Fix**: run the deferred Xero migrations on prod. They are idempotent
column-add migrations — no schema risk.

```bash
ssh ... "docker exec arbor-backend python scripts/migrate_xero_payroll_export.py"
ssh ... "docker exec arbor-backend python scripts/migrate_xero_force_counter.py"
ssh ... "docker exec arbor-backend python scripts/migrate_xero_export_log.py"
ssh ... "docker exec arbor-backend python scripts/migrate_xero_mapping_history.py"
ssh ... "docker exec arbor-backend python scripts/migrate_integration_tokens.py"
```

---

## P1 — Major workflow gaps

### P1-A. Line-manager role does not exist as a workflow

**Affects**: line-manager (Rajesh + 6 others with direct reports)

Rajesh has **7 direct reports** in the database
(Marcus, Priya, Nguyen, Ahmad, Sato, Samuel, Chen Wei) but the
product behaves as if he's a regular IC:

- **Dashboard**: identical to a no-direct-reports employee. No
  "pending team approvals", no "team on leave today", no
  "appraisals to review", no team engagement panel.
- **Leave approvals**: `GET /api/leave/applications` returns 0
  results for Rajesh — he cannot see his direct reports'
  applications. There is no manager-approval surface in the UI.
- **Manager-specific endpoints don't exist**:
  - `/api/employees/my-reports` → 403
  - `/api/employees/team` → 403
  - `/api/approvals/pending` → 404
  - `/api/appraisals/to-review` → 422
  - `/api/engagement/manager-view` → 404

The system currently funnels every approval through HR Manager
(Grace). That's workable for ~30-person SMEs. For Obayashi (500
employees) — where the buyer expectation is line-manager →
HR-exception cascade — this is a structural gap.

**What's needed**:

- Add a `manager` role _or_ derive manager scope from
  `Employee.reporting_manager_id`
- Manager dashboard with pending approvals (leave / claims /
  timesheets) for their reports
- Scope `/api/leave/applications`, `/api/claims`, `/api/timesheets`
  to return their team when accessed by a line manager
- Team page (org chart from their root, leave coverage, appraisals,
  engagement scores per-direct-report)

### P1-B. Employee post-login lands on Access Denied

**Affects**: employee, line-manager

After login, employees are routed to `/dashboard` (owner/HR-only) and
see a red "Access Denied — restricted to administrators" page before
the auth-aware sidebar redirects them. The sidebar already renders
"My Dashboard / My Leave / My Payslips" links — it knows the role.

**Fix**: role-aware redirect in the login flow. Owner/HR → `/dashboard`,
Employee → `/my-dashboard`. ~5 lines.

---

## P2 — UX & data integrity

### P2-A. NRIC mask shows only 4 hidden characters

**Affects**: employee (in My Profile)

SG NRIC is 9 characters (`S1234567A`). The mask should be
`S****567A` (5 hidden, format-revealing). The live site shows
`****115N` — 4 hidden chars + last 4. Hides the leading letter
(C/S/T/G/M/F indicator of citizenship band) and the wrong total
character count. Per the project's own `mask_nric` helper which
DOES do `nric[0] + "*"*(len-5) + nric[-4:]` — so the underlying
fn is correct, the display value is just being passed the
already-masked or differently-masked version.

The PDPA copy beneath ("Your NRIC/FIN is encrypted at rest…") is
good — but the mask format misleads on the document length.

### P2-B. "Per Employment Act" entitlements aren't EA-correct for tenure

**Affects**: employee, line-manager

Leave entitlements are labelled **"Per Employment Act"** but the
numbers don't scale with years of service.

- Rajesh: 4+ years service (joined 10 Jan 2022), shows 7 annual.
  SG EA Schedule 4 at 4 years = 10 days. So either:
  - Company has a flat 7-day policy (legal, very common) — in
    which case the label should say "Per company policy", not
    "Per Employment Act".
  - The entitlement engine isn't applying the year-of-service
    bumps — in which case Rajesh is being short-changed by 3 days.

**Fix**: either implement the scaling table (7 → 8 → 9 ... → 14)
or relabel the dashboard copy to be honest about the source.

### P2-C. Hospitalisation framed as additive to Sick Leave

**Affects**: employee

Dashboard shows three separate buckets:

- Annual Leave: 7
- Sick Leave: 14
- Hospitalisation: 60

Implies an employee has 14 + 60 = 74 medical days. The actual SG
rule is **60 days hospitalisation includes the 14 outpatient
sick days** — they are not additive. The framing risks confusing
employees about their protected entitlement and could create
disputes with HR.

**Fix**: present as a single medical-leave block with sub-rows:
"Outpatient (14) + Hospitalisation up to 60 total". Or add a
disclaimer line.

### P2-D. Stale onboarding template assigned to 4-year veteran

**Affects**: line-manager (Rajesh) — likely all old employees

Rajesh joined Jan 2022, has "HR Technology / SaaS Onboarding"
template assigned to him with "0 of 0 steps completed" rendered
on his dashboard. Either:

- Seed data error (the seed assigned current templates to legacy
  employees retroactively)
- Or template assignment leaked from a different lifecycle.

**Effect**: irritating UX clutter on the dashboard of established
employees. Suggests "you have unfinished onboarding" when there's
nothing to do.

**Fix**: hide the onboarding card when assigned_at < hire_date or
when steps_total == 0.

### P2-E. Single-payslip view shows only Apr

**Affects**: employee, line-manager

`/my-payslips` shows only the April 2026 paid run. Earlier runs
(Mar 2026 Draft, Feb 2026 Approved) are correctly hidden because
they aren't Paid yet. This is correct behaviour — but combined
with P0-A (can't approve drafts), employees who joined in early
months will see fewer payslips than expected.

Not a bug, but a cascading consequence of P0-A.

---

## Security boundaries — what holds

Cross-role API probes from Marcus (regular employee):

| Endpoint                                         | Response | Verdict |
| ------------------------------------------------ | -------- | ------- |
| `GET /api/payroll/runs/4` (admin)                | 403      | ✅      |
| `POST /api/payroll/runs/4/cpf-file`              | 403      | ✅      |
| `GET /api/payroll/runs/4/payslips/{113,114,115}` | 403      | ✅      |
| `GET /api/admin/users`                           | 404      | ✅      |
| `GET /api/employees`                             | 403      | ✅      |
| `GET /api/employees/{4,25}` (others)             | 403      | ✅      |
| `POST /api/leave/applications/1/approve`         | 405      | ✅      |
| `POST /api/compliance/check`                     | 403      | ✅      |

Cross-tenant probe from owner: `GET /api/companies/2` (foreign
company) → 404. Good — no enumeration / data leak.

**No PII leakage detected** across the 11 cross-role probes. Earlier
P0 PII concerns (encrypted NRIC blobs in CPF e-Submit file) are
already fixed and verified live in commit `f1a8394`.

---

## What works well — credibility wins

- **Employee self-service catalogue** is complete and SG-shaped:
  My Leave / Claims / Payslips / Attendance / Timesheets /
  Inventory / Engagement / Onboarding / Profile / Advisory.
  All 11 leave types in the apply dropdown (incl. Maternity,
  Paternity, Childcare, Adoption, Shared Parental, NS Reservist).
- **PDPA copy** is on every screen with sensitive data — "Your
  data is encrypted and accessed only for HR and payroll purposes"
  on profile; "Your NRIC/FIN is encrypted at rest…" on identity.
- **Bank account masking**: `********61-7` (last 4 + dash format
  preserved). Better than the NRIC mask above.
- **Half-day leave** checkboxes on both start and end of the
  application — handles SG common practice without forcing two
  separate applications.
- **Quick Actions** on owner dashboard: Ask a question / Run a
  calculation / Generate a document / Compliance check — exactly
  the four owner mental-model verbs.
- **The big stuff verified earlier**: payroll math, CPF/GIRO
  decrypt fix shipped, advisory citations, compliance domain
  coverage, Cost-to-Company math.

---

## Punch list — sorted by Obayashi blocker risk

| #     | Item                                                               | Effort  | Blocks pilot?                      |
| ----- | ------------------------------------------------------------------ | ------- | ---------------------------------- |
| **1** | **Run deferred Xero migrations on prod** (fixes P0-A)              | 10 min  | **YES**                            |
| **2** | **Manager role / scope / dashboard** (P1-A)                        | 2 weeks | **YES** at 500-person scale        |
| 3     | Role-aware post-login redirect (P1-B)                              | 30 min  | Demo-killer; not enterprise-killer |
| 4     | Relabel "Per Employment Act" or implement EA tenure scaling (P2-B) | 1 day   | Compliance risk                    |
| 5     | Fix hospitalisation-vs-sick-leave additive UX (P2-C)               | 1 hr    | Employee dispute risk              |
| 6     | Fix NRIC mask format (P2-A)                                        | 15 min  | Cosmetic                           |
| 7     | Hide stale onboarding cards on legacy employees (P2-D)             | 1 hr    | Cosmetic                           |

Items 1 + 2 are the only true blockers for Obayashi. Item 1 is a
10-minute migration; item 2 is real product work (~2 weeks for a
proper line-manager surface).

---

## Recommended next sprint

1. **Today**: Run the 5 deferred Xero migrations on prod. Verify
   `approve_payroll_run` and `mark_paid` work. Without this, every
   payroll-state-transition on the live site is broken.
2. **Day 1**: Role-aware redirect (#3) + relabel leave copy (#4 + 5).
   30 min of polish, removes 3 confusing things from buyer demos.
3. **Weeks 1-2**: Manager role + manager scope. Concrete deliverables:
   - `manager` derived role for any employee with direct reports
   - `/team` page with: pending approvals, on-leave-today, appraisals-due
   - Scope filter on `/api/leave/applications`, `/api/claims`,
     `/api/appraisals` to include `WHERE employee.reporting_manager_id = me`
   - Manager-of-team engagement view (already exists for `engagement_surveys`
     — extend the pattern)
4. **Week 3**: WICA tooltip + work-pass-expiring seed (carried over
   from 07-buyer-audit).

After this sprint, the product can credibly handle a 500-person
construction firm's daily operations.
