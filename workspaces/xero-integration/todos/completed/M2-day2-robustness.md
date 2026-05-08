# M2 — Day-2 Robustness

After M0 (BLOCKERS) and M1 (finish-the-launch) ship, customers can
use the integration end-to-end. M2 closes the failure modes that
won't show up on day 1 but will hit within the first 30 days of
real usage.

---

## M2-T01 — Void / undo flow (UI + endpoint)

**Problem:** A customer exports a wrong run (wrong period, wrong
mapping, wrong amounts) and their books now have a posted journal
they need to reverse. M1 already added `XeroAdapter.void_journal`
and uses it for force-re-export. But there is no standalone void
flow — a customer can't void without re-exporting.

**Tasks:**

1. New endpoint `POST /payroll/runs/{id}/void-xero-export`:
   - Loads the run, checks `xero_journal_id` is set.
   - Calls `adapter.void_journal`.
   - Clears `xero_journal_id` and `xero_exported_at` on the
     PayrollRun (run is no longer "exported").
   - Writes XeroExportLog with status=VOIDED, actor_id, journal_id.
2. New button on the run detail page: "Void Xero export" (visible
   only when `xero_journal_id` is set, owner role only).
3. Confirm modal explaining what voiding does in Xero (the journal
   appears as VOIDED with original date, not deleted — accountants
   need this paper trail).
4. Tests: integration test for the endpoint, assertion that voiding
   then re-exporting works (force-counter increment).

**Acceptance:** Customer can void a wrongly-exported journal in one
click. The void shows up in their Xero with the original date.

**Files:** `src/hr_advisory/api/routers/payroll.py`,
`apps/web/src/components/payroll/XeroVoidModal.tsx` (new),
`apps/web/src/app/(dashboard)/payroll/[id]/page.tsx`,
`tests/integration/test_xero_payroll_export_api.py`.

---

## M2-T02 — Settings → Integrations → Xero mapping page

**Problem:** The account mapping is only editable inside the export
modal (during a run export). After first export, customer has no
way to revisit/edit it without exporting again.

**Tasks:**

1. New page `/settings/integrations/xero/page.tsx`:
   - Connection status + org name + connected_at.
   - "Switch organisation" button (M0-T01 picker reuse).
   - "Disconnect" button (M1-T07).
   - Account mapping form (reuses `XeroExportModal` mapping UI as
     a `<XeroMappingForm/>` component split out for reuse).
   - "Refresh accounts from Xero" button that bypasses the 24h
     cache (calls `GET /payroll/xero/chart-of-accounts?refresh=true`).
   - Mapping health banner (M1-T06).
2. Add `?refresh=true` query support to chart-of-accounts endpoint
   that passes `force_refresh=True` to the adapter.
3. Test: mapping persists after edit; refresh-button drops cache.

**Acceptance:** Customer can edit the mapping at any time without
running a new payroll. They can refresh the chart when their
accountant changes account names.

**Files:** `apps/web/src/app/(dashboard)/settings/integrations/xero/page.tsx` (new),
`apps/web/src/components/payroll/XeroMappingForm.tsx` (new — extract
from XeroExportModal),
`src/hr_advisory/api/routers/payroll.py`.

---

## M2-T03 — Decimal arithmetic in journal builder

**Problem:** `services/xero_payroll_journal.py` uses `float` for all
arithmetic. For 5-employee runs the balance check holds. For
200-employee runs cross-totals (`gross - bonus`, sum of statutory
contributions) accumulate ULP errors and the `abs(total) > 0.01`
balance check eventually fails on a real run.

**Tasks:**

1. Convert all accumulators to `decimal.Decimal` with
   `getcontext().prec = 28`.
2. Round only at line emission: `Decimal('0.01').quantize(...)`.
3. Convert `payroll_run` dict floats to Decimal at the boundary.
4. Update unit tests with realistic large-N test data: 200
   employees, mixed gross amounts, bonus splits, FWL/SHG. Verify
   balance check holds.
5. Update e2e test journal data accordingly.

**Acceptance:** A 200-employee payroll run produces a balanced
journal that Xero accepts. No more "journal does not balance"
errors on runs that actually balance under correct arithmetic.

**Files:** `src/hr_advisory/services/xero_payroll_journal.py`,
`tests/unit/test_xero_payroll_journal.py`.

---

## M2-T04 — Per-Xero-org rate limiting

**Problem:** `check_rate_limit(f"payroll_xero_export:{company_id}")`
is keyed per Arbor company. Xero limits 60 calls/min and 5,000/day
**per Xero connection** (org). A customer with 3 Arbor companies all
exporting to one Xero org can blow through Xero's daily limit even
though each Arbor company is well under our local limit.

**Tasks:**

1. Resolve the active `xero_tenant_id` before the rate-limit check
   (the IntegrationToken row already has it).
2. Change the rate-limit key from `payroll_xero_export:{company_id}`
   to `xero_org:{xero_tenant_id}`.
3. Adapter-level: read `X-Rate-Limit-Remaining-Daily` and
   `X-Rate-Limit-Remaining-Minute` from the response and warn in
   logs when within 10% of the limit. Surface a typed error before
   hitting 0.
4. Test: simulate two Arbor companies sharing one Xero org, assert
   they share the rate-limit bucket.

**Acceptance:** A customer running multiple Arbor companies into one
Xero org doesn't silent-429 during month-end.

**Files:** `src/hr_advisory/api/routers/payroll.py`,
`src/hr_advisory/mcp_servers/adapters/xero.py`,
`src/hr_advisory/mcp_servers/resilience.py`.

---

## M2-T05 — bonus_total derived from PayslipItem records

**Problem:** The export modal currently has a free-form `bonus_total`
input. User can type anything; no cross-check against actual payslip
items. Wrong number splits the Salary/Bonus expense incorrectly,
silently miscategorising in Xero.

**Tasks:**

1. New helper in `services/xero_payroll_journal.py`:
   `compute_bonus_total(payroll_run_id) -> Decimal` that sums
   PayslipItem rows where `item_type='bonus'` for the run's
   payslips.
2. Modal pre-fills the bonus field with this value. User can
   override but sees a warning if their override differs by more
   than 1% from the computed value.
3. Test: create payslips with 3 bonus items, verify computed total
   matches sum of items.

**Acceptance:** Default bonus_total reflects actual payslip data.
Manual overrides require explicit acknowledgement.

**Files:** `src/hr_advisory/services/xero_payroll_journal.py`,
`src/hr_advisory/api/routers/payroll.py` (new endpoint
`/payroll/runs/{id}/xero-suggested-bonus`),
`apps/web/src/components/payroll/XeroExportModal.tsx`,
`tests/unit/test_xero_payroll_journal.py`.

---

## M2-T06 — Disconnect button + 401-triggered auto-disconnect

(Largely covered by M1-T07 + M1-T09 — verify the UX once both ship
and add the explicit Settings → Integrations → Xero card "Disconnect"
button if not already wired.)

**Tasks:**

1. Confirm the Disconnect button on the integrations card actually
   calls the new disconnect endpoint.
2. Confirm 401 → auto-disconnect path correctly transitions the UI
   from "Connected" to "Disconnected — reconnect."
3. Manual QA on a fresh test account: connect, hit Xero API, expire
   tokens (or wait), attempt export, verify disconnect propagation.

**Acceptance:** Both manual and automatic disconnect paths leave the
UI in a sensible "connect again" state.

**Files:** Same as M1-T07/M1-T09.

---

## M2-T07 — Last-export status badge on run detail

**Problem:** `xero_journal_id` and `xero_exported_at` are visible on
the run detail page only when the modal is open. The page header
should always show the export status if exported.

**Tasks:**

1. Already partly done — the green "Exported · journal X" badge in
   payroll/[id]/page.tsx is rendered when `run.xero_journal_id` is
   set.
2. Surface void status: if a XeroExportLog row exists with
   status=VOIDED and matches the current journal_id, show "Voided
   in Xero" badge instead.
3. Surface failure status: if the most recent export attempt for
   the run was status=FAILED, show "Last export attempt failed —
   review and retry" amber banner.
4. Test: integration test verifying badge text in each state.

**Acceptance:** Run detail page accurately reflects Xero state at a
glance, without needing to open the modal.

**Files:** `apps/web/src/app/(dashboard)/payroll/[id]/page.tsx`,
`apps/web/src/services/api/payroll.ts` (extend run detail with
last_xero_attempt_status field).

---

## M2-T08 — Scope-mismatch detection + reconnect prompt

**Problem:** If we add new scopes in a future Phase (e.g.,
`accounting.contacts.read` for invoice mapping), existing customers'
tokens won't have them. Calling those endpoints returns 403 with no
guidance.

**Tasks:**

1. Document the required scopes per feature in a constants file.
2. At each scope-restricted call site, check
   `IntegrationToken.scopes` first. If required scope is missing,
   return a typed error `{action: "reconnect_for_scope",
missing_scopes: ["accounting.contacts.read"]}`.
3. Frontend translates to "Reconnect Xero to enable invoice mapping"
   with one-click re-OAuth that requests the broader scope set.
4. Test: store a token with limited scopes, call a scope-restricted
   endpoint, verify the typed error.

**Acceptance:** Adding new Xero features in future doesn't silently
break existing customers — they get a clear "reconnect to enable" path.

**Files:** `src/hr_advisory/mcp_servers/adapters/xero.py`,
`src/hr_advisory/api/routers/payroll.py`,
`apps/web/src/components/payroll/XeroExportModal.tsx`.

---

## M2-T09 — Account-code typeahead in mapping UI

**Problem:** The mapping form uses a `<select>` with all chart-of-accounts
items. For a customer with 200+ accounts the dropdown is unwieldy
and people sometimes paste the wrong code from memory. A typeahead
bound to the actual chart prevents number-vs-code mistakes.

**Tasks:**

1. Replace the `<select>` in `XeroMappingForm` (M2-T02) with a
   typeahead component (filterable combobox). Search by code OR name.
2. Show "Code · Name (Type)" in each option for clarity.
3. Validate on submit: rejected if code doesn't match any account
   in the current chart.
4. Test: type partial name, verify filtering; submit invalid code,
   verify rejection.

**Acceptance:** User can find an account quickly; impossible to
submit an unmappable code.

**Files:** `apps/web/src/components/payroll/XeroMappingForm.tsx`.

---

## M2-T10 — Reversal date semantics for void_journal

**Problem:** When `void_journal` is called, the voided journal's
`Date` field — Xero shows it on the original date by default. Some
accountants prefer voids to appear on the void date for visibility.
Decide and document.

**Tasks:**

1. Decide policy. Recommended: keep original date (preserves
   period accuracy; auditors see the void in the period it was
   originally posted to).
2. Document in a customer-facing FAQ: "Voiding a Xero journal
   posts a VOIDED status against the original date, not the void
   date. This keeps your period totals accurate."
3. If alternative date desired, add `void_date` parameter to
   `void_journal` and a "Use today's date" checkbox in the void
   modal.

**Acceptance:** Documented behaviour; consistent with accountant
expectations.

**Files:** Customer FAQ doc (M4),
`src/hr_advisory/mcp_servers/adapters/xero.py`.

---

## M2-T11 — Surface X-Rate-Limit warnings before 429

**Problem:** Xero returns headers like `X-Rate-Limit-Remaining-Daily`
on every response. Today we only react to 429. Surfacing near-limit
warnings lets customers slow down before hitting hard rejection.

**Tasks:**

1. In `XeroAdapter._api_call`, parse the rate-limit headers on every
   response.
2. If remaining < 10% of the limit, emit a structured log warning
   with `event=xero_rate_limit_warn`, `remaining`, `tenant_id`.
3. Optional: surface to the export modal as a yellow banner ("Xero
   rate limit at 90% — large monthly exports may need to be staged.")
4. Cross-cuts with M3 telemetry.

**Acceptance:** Operators get warnings before customers experience
429s.

**Files:** `src/hr_advisory/mcp_servers/adapters/xero.py`,
`src/hr_advisory/mcp_servers/resilience.py`.

---

## M2-T12 — Cross-currency support (gated, customer-pull)

**Problem:** ManualJournal supports `CurrencyRate` and `CurrencyCode`
per journal. Our builder assumes the org's base currency. SG-only
customers are fine; multi-currency customers (rare for SME payroll
but real) will see foreign-currency journals posted at base rate.

**Tasks (NOT a blocker — gate on customer demand):**

1. Add `currency_code` parameter to `build_journal_lines`. Default to
   None (Xero uses base).
2. If non-None, include `CurrencyCode` and `CurrencyRate` (fetched
   from Xero's CurrencyRates endpoint) in the payload.
3. Test against a Demo Company that has multi-currency enabled.
4. UX: only expose if customer's Xero is multi-currency-enabled
   (detected via Organisation endpoint).

**Acceptance:** Multi-currency customers, when they appear, can map
foreign-currency wages correctly.

**Files:** `src/hr_advisory/services/xero_payroll_journal.py`,
`src/hr_advisory/mcp_servers/adapters/xero.py`.
