# P5-VL — Value-flow handoffs

**Source:** `04-validate/13-redteam-comprehensive-2026-05-19.md`
finding O12.

**State:** The compliance check identifies 7 findings (KET, payslip,
leave records, OT records, WSH policy, grievance process, FWA policy)
and renders an "Action Items" list at the bottom. Each item is the
right next step — but clicking it doesn't take the user anywhere.
The gap-detect → fix-now value chain is broken at the handoff,
which is exactly the moment the buyer expects the platform to
prove its value.

---

## P5-VL-1 — Compliance Action Items link into Policies/Documents

- **Symptom:** `/compliance` "Action Items" list shows items like
  `"Set up itemised payslip system"`, `"Establish grievance handling
  process"`, `"Draft FWA policy"`. Clicking any item is a no-op —
  static text.
- **Where:**
  - Frontend list rendering: `apps/web/src/app/(dashboard)/
    compliance/page.tsx` (the Action Items section).
  - Backend findings model: `src/hr_advisory/api/routers/
    compliance.py` — each finding has a `provision_id` /
    `recommended_action` field but no target route.
- **Fix:** add a `cta` object to each finding shape on the backend,
  containing `{ label: str, href: str, kind: "policy_template" |
  "document_template" | "settings" | "external" }`. Map each known
  finding to the right target:
  - `"No KET issued"` → `/documents?template=ket`
  - `"No itemised payslip system"` → `/settings/payroll`
  - `"No leave records maintained"` → `/leave/policies`
  - `"No OT records maintained"` → `/settings/attendance`
  - `"No WSH policy"` → `/policies?category=workplace_safety`
  - `"No grievance handling process"` → `/policies?category=fair_employment`
  - `"No FWA policy"` → `/policies?category=fair_employment&template=fwa`
  Frontend renders each item as a button that navigates to the href.
- **Acceptance:**
  - Each of the 7 currently-rendered Action Items has a visible CTA
    chip / arrow.
  - Clicking "Draft FWA policy" lands on `/policies?category=
    fair_employment&template=fwa` with the FWA template already
    selected and ready to publish.
  - The buyer's complete-the-value-loop journey:
    compliance check → click action → arrive at policy/template
    → publish → re-run compliance check → score improves.
- **Regression tests:**
  - `tests/regression/test_p5_vl_compliance_cta_map.py` — pin that
    each known finding ID maps to a non-empty `cta.href`.
  - Playwright E2E in next red-team round: click each of 7 items,
    assert landing URL.

---

## P5-VL-2 — Auto-create policy drafts from compliance click

- **Symptom:** even after wiring P5-VL-1, the buyer arriving at
  `/policies?category=fair_employment&template=fwa` sees an empty
  list and a "Add Policy" button. One more step of friction.
- **Where:** `apps/web/src/app/(dashboard)/policies/page.tsx`.
- **Fix:** when arriving via `?template=<id>` query param, open the
  Add Policy modal pre-populated with the template content (from
  `/api/documents/templates`). Modal title: "Publish [template
  name]". Submit creates the policy in draft state.
- **Acceptance:**
  - URL `/policies?category=fair_employment&template=fwa` opens a
    draft policy modal with FWA template pre-filled.
  - Submit → policy appears in Draft tab.
  - Re-run compliance check → "No FWA policy" finding goes away
    (because there's now an active policy in the relevant category).
- **Regression test:** Playwright E2E in next red-team round.

---

## Effort + dependencies

- Total: 3 hours (P5-VL-1: 2h backend + frontend; P5-VL-2: 1h).
- Depends on `/api/documents/templates` already existing (verified —
  12 templates from live walk).
- Recommended order: ship P5-VL-1 first (the click-to-navigate),
  validate by buyer walk, then P5-VL-2 (auto-populate).
