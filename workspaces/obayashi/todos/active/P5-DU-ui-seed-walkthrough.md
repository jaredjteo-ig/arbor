# P5-DU — Demo seed via UI walkthrough (Playwright-driven)

**Source:** `04-validate/13-redteam-comprehensive-2026-05-19.md`
findings O9 (payroll seed too symmetric) + O11 (shifts empty).

**Supersedes:** `P5-DM-demo-seed-realism.md` — the SQL approach.
Keep the SQL fallback documented; P5-DU is the preferred path.

**Why UI-driven seeding:** the SQL approach (write into `payroll_runs`,
`shift_assignments` directly) is fast but loses two things:

1. **Confidence the user flow actually works** — the live walk on
   2026-05-19 found multiple UX gaps (leave-types modal showed
   Maternity to males, onboarding "Completed at 0%", missing
   advisory citations) that a click-the-UI seed would have
   surfaced months earlier.
2. **Authentic timestamps + audit chain** — SQL inserts skip the
   audit-log dual-write, rate-limit checks, validation, and the
   downstream side-effects (claim status flip on payroll-paid,
   trust-chain entries, employment-event rows). The buyer's
   "show me how this works" demo runs through the exact same
   paths the seed data was created with.

The walkthrough doubles as a **post-deploy smoke test**. Run it
once after every prod deploy and you have evidence every flagship
flow worked end-to-end on the live URL.

---

## Approach

Add a `scripts/seed/ui_walkthrough.py` Playwright script (sync API
via `playwright.sync_api`). Driven by `.env` for the prod URL +
credentials. Sections mirror `seed_demo_data.py`'s `--section`
contract so operators can run subsets:

```
python scripts/seed/ui_walkthrough.py \
  --base-url http://136.110.51.61 \
  --section payroll --section shifts \
  [--dry-run] [--headed]
```

Reads `ADMIN_PASSWORD` / `EMPLOYEE_PASSWORD` from env (per
`.claude/rules/seeding.md`).

### Sections

| Section           | Role        | What it does                                                                                                              |
| ----------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------- |
| `auth-smoke`      | all 4 roles | Login + assert role-correct dashboard renders + sidebar shape                                                             |
| `payroll`         | Owner       | Calculate Feb 2026 → Approve → Mark Paid. Repeat for Mar (Draft only). Apr already exists. Variance comes from real seed. |
| `shifts`          | HR          | Manage Templates → create 3 templates (Morning / Afternoon / Night). Assign Shift → publish week.                         |
| `leave-apply`     | Marcus      | `/my-leave` Apply for Leave → submit Annual 2 days. Owner approves via `/leave`.                                          |
| `claim-submit`    | Marcus      | `/my-claims` New Claim → add 2 items → submit. Owner approves via `/claims`.                                              |
| `attendance`      | Lim Ah Kow  | `/my-attendance` Clock In → Clock Out (simulated 8h). Confirms attendance flow + monthly summary.                         |
| `onboarding-walk` | Marcus      | `/my-onboarding` → click through every checklist item → assignment flips to Completed at 100%.                            |

Each section is an isolated function. A failure in one section
prints the screenshot path + stack and continues to the next
(per `.claude/rules/seeding.md` rule 1).

---

## Acceptance

- `python scripts/seed/ui_walkthrough.py --section auth-smoke` passes
  on prod, asserting each of 4 roles lands on the right dashboard.
- After `--section payroll`, owner-view `/payroll` shows 3 runs with
  **distinct** gross totals (the variance comes from real seed +
  approve/mark-paid timing, NOT from probabilistic distribution).
- After `--section shifts`, owner-view `/shifts` shows 3 templates
  - a populated current-week grid.
- After `--section leave-apply` + `--section claim-submit`, the
  `pending_approvals` count on owner dashboard increments before
  the owner-side approve step, then decrements after.
- A failure mid-section captures `playwright-mcp/error-<section>.png`
  - the URL the test was on + the last DOM snapshot.

---

## Failure modes to expect (and what they tell us)

| Failure                                                    | Diagnosis                                                                                                                                        |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Apply for Leave` modal shows Maternity to Marcus          | already fixed in P5-PL-3; this seed verifies the fix held on prod                                                                                |
| Approve button on `/leave` returns 403 for owner           | RBAC regression — Cross-check against P5-RT3-EM                                                                                                  |
| "Calculate Payroll" hangs without completing               | LLM-free deterministic path — should be < 5s; if >30s the payroll_calculator service degraded                                                    |
| Shift template create returns 500                          | Backend hasn't seeded shift_templates schema, OR ShiftTemplateCreateNode signature changed                                                       |
| Onboarding checklist clicks don't flip status to Completed | The P5-RT3-ON self-heal demoted the row — but the underlying create flow may be wrong; investigate                                               |
| Selector by label fails (button changed)                   | Frontend changed copy; update the script. Acceptable churn.                                                                                      |
| Playwright + DataFlow contention                           | If the script and the daily probation tick collide, the tick might flip on_probation → confirmed while we're reading. Disable via env if needed. |

---

## Out of scope (deferred)

- Statutory file generation (CPF e-Submit / IR8A / GIRO PDF) — these
  cross to integration endpoints that need real bank/IRAS sandbox
  credentials. Keep in `seed_demo_data.py` direct calls.
- Recruitment full pipeline (candidate sourcing → interview → offer)
  — too many moving parts; cover separately.
- Document generation (employment contract PDF) — already exercised
  by P5-VL-2 modal prefill in production; no need to drive in seed.

---

## Effort

- 2-3 hours scaffolding (Playwright sync setup, section runner,
  screenshot + error capture).
- 30-45 min per section × 7 sections = ~5 hours full implementation.
- Bonus: every section is a regression test for free.

Total: ~7-8 hours OR ~3 hours if we ship just 3-4 priority sections
(auth-smoke + payroll + shifts + onboarding-walk).

---

## Run order when implementing

1. Scaffold `scripts/seed/ui_walkthrough.py` with section registry
   - auth-smoke section only. Verify Playwright sync API + login
     works against `http://136.110.51.61`.
2. Add `payroll` section. Validate variance happens.
3. Add `shifts` section. Validate template creation succeeds.
4. Add `leave-apply` + `claim-submit` (these double as P5-RT3-EM
   audit-log smoke tests).
5. Add `attendance` + `onboarding-walk` last (lowest demo value).

If any section reveals a missing UI flow or a backend bug, FIX it
inline — that's the win of this approach over SQL inserts.

---

## Hybrid fallback

If Playwright proves too brittle on a particular section, fall back
to the SQL path documented in `P5-DM-demo-seed-realism.md` for THAT
section only. The UI script and the SQL script are designed to
coexist; both write through the same eventual data model.

---

## Pilot results — 2026-05-19 (Playwright MCP, against prod)

Approach validated. Three sections probed:

| Section      | Result                       | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `auth-smoke` | ✅ passes                    | Owner + Grace login + landing assertion + sidebar shape. Confirmed Grace still sees Admin/Integrations on prod commit 13c0569 (P5-RT3 sidebar fix not yet deployed) — script catches the regression once it ships.                                                                                                                                                                                                                                                                      |
| `payroll`    | 🔴 blocked by P4-XX-2 (Xero) | `POST /payroll/calculate` returns 500 on prod. Backend log: `dataflow_crud.create("PayrollRun", ...)` fails because the deferred Xero migrations haven't run — the model code references `xero_journal_id` / `xero_exported_at` / `xero_force_counter` columns absent in the prod schema. Earlier session notes only listed approve / mark-paid / cancel as affected; **calculate is also broken**. New finding the SQL-seed approach would never surface. Unblocks when P4-XX-2 ships. |
| `shifts`     | ✅ passes                    | Clicked Manage Templates → form opens → filled Template Name + Start/End Time → Create Template. New "Morning Shift 08:00–16:00 (8h)" row appeared. ShiftTemplate creation flow is healthy end-to-end on prod.                                                                                                                                                                                                                                                                          |

### What the pilot proved

1. **Playwright MCP is sufficient for the live walk** (no Python
   Playwright install needed for the pilot phase). Direct UI driving
   works against prod with the existing JWT login flow.
2. **The approach surfaces real bugs the SQL approach misses.** The
   payroll/calculate 500 was unknown — it's not on the P4-XX-2
   deferred list. We now know calculate is also affected and can
   list it as a fourth payroll endpoint blocked by the Xero
   schema gap.
3. **Per-section isolation works.** Payroll failed but shifts
   succeeded immediately after — exactly the failure-isolation
   the section design promised.

### Open question: package installation

Pilot used Playwright MCP (Claude Code tool). A reusable
`scripts/seed/ui_walkthrough.py` for CI / post-deploy operator use
needs `pip install playwright && playwright install chromium`
(~200MB). Defer this until at least one operator (other than Claude)
needs to run the script — until then the MCP path is enough.

### Next moves

- Unblock payroll section when P4-XX-2 unblocks (or apply the
  conditional-field-exclusion mitigation from `P4-XX-deferred.md`).
- Continue MCP-driven pilots of `leave-apply` + `claim-submit` +
  `onboarding-walk` to validate the remaining sections work before
  scaffolding the reusable script.
- If all sections pass, decide: ship as Python Playwright script,
  OR codify the Playwright MCP recipe into a runnable Claude
  command.
