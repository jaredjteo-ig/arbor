# M0 — Pre-Launch BLOCKERS

These must be closed before any paying customer is allowed to connect
their real Xero org. Each is a "silent miscategorisation" or
"silent data leak" risk that will not be detected post-hoc.

---

## M0-T01 — Org picker in OAuth callback (multi-org safety)

**Problem:** The current `/integrations/xero/oauth/callback` calls
`_get_xero_tenant_id` which picks `connections[0]`. Bookkeepers and
accounting firms regularly connect 5+ Xero orgs. Picking the first
one silently routes one customer's payroll journal into another
customer's books — a financial data leak between tenants the user
manages.

**Tasks:**

1. Modify `XeroAdapter.handle_oauth_callback` (or move logic into the
   callback endpoint) to return the full `connections` list rather
   than just the first tenant id.
2. When `len(connections) > 1`:
   - Persist the OAuth tokens with `xero_tenant_id=""` (un-bound).
   - Stash the connections list in a short-TTL store (Redis or
     `_pending_org_picks` dict keyed by `(company_id, nonce)`) and
     redirect to `/settings/integrations/xero/pick-org?token=<nonce>`.
   - On that page, the user sees a list of org names + types and
     clicks one. Submission persists `xero_tenant_id` and
     `xero_tenant_name` on the `IntegrationToken` row.
3. When `len(connections) == 1`: skip the picker, persist directly,
   redirect to `/settings/integrations?xero=connected` (today's path).
4. Add a "Switch Xero organization" link on Settings → Integrations →
   Xero that re-runs the picker without full re-OAuth (re-fetch
   `/connections` with the current access token).
5. Tests: integration test for both single-org and multi-org callback
   paths, with a fake `_get_xero_tenant_id` returning 1 vs 3 orgs.

**Acceptance:** Connecting a Xero account that has multiple orgs
shows a picker; picking org B persists org B; subsequent exports
post to org B; no journal ever lands in org A.

**Files:** `src/hr_advisory/api/routers/integrations.py`,
`src/hr_advisory/mcp_servers/adapters/xero.py`,
`apps/web/src/app/(dashboard)/settings/integrations/xero/pick-org/page.tsx` (new),
`tests/integration/test_xero_oauth_callback.py` (new).

---

## M0-T02 — Concurrent-export TOCTOU race

**Problem:** Two users in the same Arbor company click "Export to
Xero" within the same millisecond. The export endpoint reads
`xero_force_counter`, derives the Idempotency-Key, then writes the
new counter. Both reads happen before either write, both POSTs use
counter 0, Xero may dedupe (returning the first response twice) or
may post twice depending on edge timing. The audit log shows two
POSTED rows with the same journal_id; the customer's books may have
either one or two posted journals. Silent duplicates that aren't
detectable post-hoc.

**Tasks:**

1. Wrap the `/payroll/runs/{id}/export-xero` body in an explicit
   Postgres transaction with `SELECT … FOR UPDATE` on the PayrollRun
   row before computing the idempotency key.
2. Or use a Postgres advisory lock keyed on `(company_id, run_id)`:
   `SELECT pg_try_advisory_xact_lock(hashtext('xero-export'),
hashtext($1))`. Return 409 if lock not acquired (= "another
   export in progress").
3. Per `rules/infrastructure-sql.md` Rule 2 — multi-statement
   operations that must be atomic require a transaction.
4. Regression test that simulates two concurrent POSTs (asyncio
   gather of two TestClient calls) and asserts: exactly one
   `POSTED` audit row, exactly one Xero POST attempt, the second
   request returns 409 or waits.

**Acceptance:** Concurrent double-click cannot produce two Xero
journals. Concurrent attempt returns deterministic conflict error.

**Files:** `src/hr_advisory/api/routers/payroll.py`,
`tests/regression/test_xero_concurrent_export.py` (new).

---

## M0-T03 — Singapore GST-correct TaxType + LineAmountTypes

**Problem:** Today the journal builder sends no `TaxType` and no
`LineAmountTypes`. Xero defaults vary, but for SG GST-registered
companies (>S$1M turnover, IRAS GST F5 quarterly returns) salary
journals MUST be marked `BASEXCLUDED` (out-of-scope) and the journal
LineAmountTypes set to `NoTax`. Silent default → customer's GST F5
return is wrong → IRAS issue. They will blame Arbor.

**Tasks:**

1. Update `services/xero_payroll_journal.py::build_journal_lines` to
   set `tax_type="BASEXCLUDED"` on every line.
2. Update `XeroAdapter.post_payroll_journal` payload to include
   `LineAmountTypes: "NoTax"` at the journal level.
3. Add unit test that asserts every emitted line has
   `TaxType=BASEXCLUDED` and the payload sent to the adapter has
   `LineAmountTypes=NoTax`.
4. Document in the export modal: "Lines posted as BAS Excluded
   (out-of-scope for GST). Adjust in Xero if your accounting policy
   differs."

**Acceptance:** A real journal posted via the e2e test against Xero
Demo Company has `TaxType=BASEXCLUDED` on every line. Verified by
fetching the posted ManualJournal back via GET `/ManualJournals/{id}`.

**Files:** `src/hr_advisory/services/xero_payroll_journal.py`,
`src/hr_advisory/mcp_servers/adapters/xero.py`,
`tests/unit/test_xero_payroll_journal.py`,
`tests/e2e/test_xero_payroll_export_real.py`,
`apps/web/src/components/payroll/XeroExportModal.tsx`.

---

## M0-T04 — JournalDate uses org-local timezone, not UTC

**Problem:** `build_journal_lines` uses
`datetime.now(timezone.utc).strftime("%Y-%m-%d")` for the date
fallback. Xero interprets JournalDate in the **org's** timezone
(usually Singapore for our customers, Pacific for AU customers,
etc.). A SG payroll run with `pay_date=2026-04-30` posted at 23:00
SGT (15:00 UTC) is fine, but if the date is missing and we fallback
to `datetime.now(utc)` near month-end, we may post to the wrong
period.

**Tasks:**

1. Always require `pay_date` on the PayrollRun — fail-fast on
   `period_end` fallback (today's behaviour). Error message: "Pay
   date required for Xero export."
2. Add validation in the export endpoint: reject if `pay_date == ""`.
3. Test: run with empty `pay_date` returns 400 with clear error.
4. Document: "Pay date must be set on the payroll run before export."

**Acceptance:** Exporting a run with empty `pay_date` returns 400
with a clear error before any Xero call is made.

**Files:** `src/hr_advisory/api/routers/payroll.py`,
`src/hr_advisory/services/xero_payroll_journal.py`,
`tests/integration/test_xero_payroll_export_api.py`.

---

## M0-T05 — Frontend disables Export button while pending

**Problem:** The user clicks Export, the browser request hangs while
the backend POSTs to Xero, the user clicks Export again. Without
`disabled` on the button, two POSTs go to the backend. M0-T02 fixes
the backend race; this prevents the UX issue from creating two
audit-log entries (one of which gets 409'd).

**Tasks:**

1. In `XeroExportModal.handleExport`, the button already disables on
   `exportRun.isPending` — verify this is wired correctly.
2. Audit `payroll/[id]/page.tsx` "Export to Xero" link — make sure
   it can't open multiple modals (debounce open).
3. Add an integration smoke test: click Export twice rapidly, assert
   only one network request fires.
4. Visual feedback during pending: "Posting to Xero…" with spinner
   (already implemented — verify).

**Acceptance:** Double-click on Export results in exactly one
backend POST. UI shows pending state for the full Xero round-trip.

**Files:** `apps/web/src/components/payroll/XeroExportModal.tsx`,
`apps/web/src/app/(dashboard)/payroll/[id]/page.tsx`,
`apps/web/tests/e2e/xero-export-doubleclick.spec.ts` (new).

---

## M0-T06 — E2E coverage for failure modes

**Problem:** 3 e2e tests pass against Demo Company, all happy-path.
None exercise: multi-org callback, refresh-token failure, archived
account on mapping, concurrent export. These are the failure modes
that ship in production and break first.

**Tasks:**

1. Multi-org callback test: mock `/connections` to return 3 orgs,
   verify redirect to picker page rather than direct success.
2. Refresh-token-failure test: store an expired access token + an
   intentionally-bad refresh token, attempt export, verify 401
   surfaced as "Reconnect Xero" UX rather than generic 500.
3. Archived-account test: mock chart of accounts where one mapped
   code returns Status=ARCHIVED, attempt export, verify the banner
   shows on mapping page and the export 400s with named code.
4. Concurrent export test: see M0-T02 regression test.
5. Multi-org-picker happy path: mock picker selection, persist,
   subsequent export uses the chosen org.

**Acceptance:** All 5 new tests green. CI gates on them.

**Files:** `tests/e2e/test_xero_payroll_export_real.py` (extend),
`tests/regression/test_xero_concurrent_export.py` (new),
new tests in `tests/integration/`.
