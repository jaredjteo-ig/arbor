# P5-DM — Demo seed realism

**Source:** `04-validate/13-redteam-comprehensive-2026-05-19.md`
findings O9 (payroll) + O11 (shifts).

**State:** Live walk turned up two zero-content / unrealistic-content
demo surfaces. A buyer in their first 5 minutes notices the gaps and
loses trust before the value chain finishes loading.

**Recommended bundling:** ship as one commit. Both touch
`scripts/seed_demo_data.py` and need a wipe-before-reseed on prod
(per `.claude/rules/seeding.md` rule 10).

---

## P5-DM-1 — Payroll seed realism (P52 distribution)

- **Symptom:** Three payroll runs (Feb Approved, Mar Draft, Apr Paid)
  all show identical totals: gross $162,050, net $138,656. A buyer
  who knows payroll varies month-to-month (joiners, leavers, OT,
  bonuses, sick days) reads it as fake the moment they spot the
  repeated number.
- **Where:** `scripts/seed_demo_data.py` — payroll section. Currently
  invokes `payroll/calculate` once per month against the same active
  employee set, producing identical outputs.
- **Fix:** apply pattern P52 (probability-weighted demo distributions
  per `.claude/rules/seeding.md` rule 9) to monthly variation:
  - Add a probability of 1 OT day per warehouse employee per month
    (focal 30-50%, adjacent 5-15%, background 1-3%).
  - Add a sick-day distribution: 10-20% chance per employee per month.
  - Add a 1-time discretionary bonus per month: 1-2 random employees.
  - Vary headcount across the 3 months by toggling `is_active` /
    `start_date` for 2-3 employees so Feb has 27, Mar has 28, Apr 29.
- **Acceptance:**
  - Three months show distinct gross/net values, max delta ≥ $4,000.
  - At least one month shows OT in the payslip itemisation.
  - Demo Admin's payroll dashboard view doesn't repeat the same number.
- **Regression test:** `tests/regression/test_p5_dm_payroll_variance.py`
  — assert seeded run totals differ pairwise (no two identical).
- **Wipe-before-reseed SQL** (rule 10):
  ```sql
  DELETE FROM payslip_items WHERE company_id=:cid;
  DELETE FROM payslips WHERE company_id=:cid;
  DELETE FROM payroll_runs WHERE company_id=:cid;
  ```
  Run inside backend container before re-seed.

---

## P5-DM-2 — Shifts seed (1 week of warehouse rota)

- **Symptom:** `/shifts` is completely empty for Demo Admin — no
  templates, no scheduled shifts. Landing page promises "Visual shift
  allocation with availability checking, leave integration, and labour
  law compliance" but the buyer sees `"No templates yet. Create one to
  start scheduling."`
- **Where:** `scripts/seed_demo_data.py` — add a new `shifts` section
  to the section registry. New section, modeled on `recognition` /
  `onboarding` sections.
- **Fix:** seed three shift templates + one published week:
  - Templates: Morning (08:00-16:00), Afternoon (14:00-22:00), Night
    (22:00-06:00).
  - Assignments: 5 warehouse staff (Ravi, Lim Ah Kow, Muhammad Rizwan,
    Siti Aminah, Ruth/another) rotated across the current week.
  - 2 leave overlaps (already-approved leave for Ravi Mon-Tue) so the
    "leave-integrated availability" feature has something to surface.
  - Status: Published (not draft).
- **Acceptance:**
  - `/shifts` for Demo Admin shows 3 templates + a populated week grid.
  - Lifecycle dashboard's Reward stage doesn't change (shifts don't
    cross to reward).
  - Marcus (IC) can see his own shift in `/my-attendance` if he were
    on a warehouse team — N/A for him (engineer), but a warehouse
    test account would.
- **Regression test:** none required — purely seed data; covered by
  buyer-walk smoke (next red-team round).
- **Wipe-before-reseed SQL:**
  ```sql
  DELETE FROM shift_assignments WHERE company_id=:cid;
  DELETE FROM shift_templates WHERE company_id=:cid;
  ```

---

## Effort + dependencies

- Total: 2-3 hours
- No code dependencies (seed-only changes)
- DEPLOY: run wipe SQL inside backend container, then
  `python scripts/seed_demo_data.py --section payroll --section shifts`.
- Validation: live walk of `/payroll` and `/shifts` as Demo Admin
  post-deploy.
