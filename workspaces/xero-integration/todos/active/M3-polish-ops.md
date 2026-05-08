# M3 — Polish + Operational Maturity

Non-blocking but high-leverage. Most of these are not customer-facing
features but force-multipliers when something goes wrong in
production.

---

## M3-T01 — Structured logging for Xero events

**Problem:** Today we have `logger.info("Posted...")`-style logs.
Operators can't grep cleanly for "all failed exports last week."

**Tasks:**

1. Add a `xero_log_event(event, **fields)` helper in adapter that
   emits structured JSON with stable field names:
   `event`, `outcome` (success/failure), `xero_status`, `tenant_id`,
   `xero_tenant_id`, `company_id`, `run_id`, `journal_id`, `latency_ms`.
2. Replace existing `logger.info/.warning` with structured calls at:
   - OAuth start/callback
   - Token refresh (success and failure)
   - chart-of-accounts fetch
   - post_payroll_journal (success and each failure type)
   - void_journal
3. Document log schema in `deploy/xero-deployment-runbook.md`.

**Acceptance:** `grep '"event":"xero_export"' logs.json | jq` is
useful out of the box.

**Files:** `src/hr_advisory/mcp_servers/adapters/xero.py`,
`src/hr_advisory/api/routers/payroll.py`,
`src/hr_advisory/api/routers/integrations.py`.

---

## M3-T02 — Operational alerting

**Problem:** Customers will hit failures we don't see until they
email support.

**Tasks:**

1. Define alert thresholds:
   - Refresh failure rate > 5% per hour → page.
   - Export 4xx rate > 10% per hour → page.
   - Any 429 (rate limit) hit → warn (Slack).
   - Any 502 from Xero (Xero side outage) → warn.
2. Wire into existing alerting (Slack channel, email, whatever the
   project already uses). Reuse `notifications.py` if applicable.
3. Document escalation in the runbook.
4. Add a "Xero status" summary endpoint for the admin dashboard
   showing rolling 24h success rate per company.

**Acceptance:** A Xero outage or scope misconfiguration surfaces in
ops chat within 5 minutes, not via customer email next morning.

**Files:** `src/hr_advisory/services/notifications.py`,
`src/hr_advisory/api/routers/admin.py` (new admin endpoint),
`deploy/xero-deployment-runbook.md`.

---

## M3-T03 — Mapping change history

**Problem:** When a customer's mapping changes (because they re-saved
it), we have no record of the previous mapping. If their accountant
asks "why did salary expense move from 477 to 478 between April and
May exports?", we can't answer.

**Tasks:**

1. New model `XeroAccountMappingHistory` (append-only):
   - company_id, mapping_field, previous_code, new_code,
     changed_by, changed_at.
2. On every `PUT /payroll/xero/account-mapping`, diff the old and
   new mapping; write history rows for changed fields.
3. Show change history on the mapping settings page (M2-T02): "On
   2026-04-15, Jared changed Salary Expense from 477 to 478."

**Acceptance:** Mapping history is queryable. Future audit
questions can be answered without forensic reconstruction.

**Files:** `src/hr_advisory/models/company_user.py`,
`scripts/migrate_xero_mapping_history.py` (new),
`src/hr_advisory/api/routers/payroll.py`,
`apps/web/src/app/(dashboard)/settings/integrations/xero/page.tsx`.

---

## M3-T04 — Bulk-export historical runs

**Problem:** A customer onboarding mid-year will have several
already-paid runs they want in Xero retroactively. Today they have
to click Export per run.

**Tasks:**

1. New endpoint `POST /payroll/runs/bulk-export-xero` accepts
   `{run_ids: [int]}` and processes them in series (Xero's daily
   rate-limit makes parallel risky).
2. UI: multi-select checkboxes on the runs list page; "Export N to
   Xero" action surfaces a per-run progress modal.
3. Each run still goes through the same idempotency-key + audit log
   path. Failures are surfaced per-run, not aborting the batch.

**Acceptance:** Onboarding customers can backfill 6 months of
journals in one operation.

**Files:** `src/hr_advisory/api/routers/payroll.py`,
`apps/web/src/app/(dashboard)/payroll/page.tsx`,
`apps/web/src/components/payroll/BulkXeroExportModal.tsx` (new).

---

## M3-T05 — "Test Xero connection" button

**Problem:** When a customer suspects something is wrong with their
connection, the only diagnostic is "try to export." A dedicated test
button gives a fast green/red signal.

**Tasks:**

1. New endpoint `GET /integrations/xero/test`:
   - Calls Xero `/connections` (cheapest auth-validating call).
   - Returns `{success: bool, latency_ms: int, tenant_name, scopes,
details: ...}`.
2. Button on Settings → Integrations → Xero card: "Test connection."
3. Reuses the existing TestConnectionResponse pattern in
   integrations.ts.

**Acceptance:** Diagnostic feedback in <1 second without committing
any customer data.

**Files:** `src/hr_advisory/api/routers/integrations.py`,
`apps/web/src/app/(dashboard)/settings/integrations/page.tsx`.

---

## M3-T06 — Per-route telemetry on the export modal

**Problem:** Today we have no insight into how customers use the
modal. Are they always changing the mapping? Always using
default bonus? Always force-re-exporting?

**Tasks:**

1. Emit frontend analytics events at key modal interactions:
   - mapping_loaded, mapping_changed, mapping_saved
   - bonus_field_edited, bonus_default_kept
   - export_attempted, export_success, export_failure
   - force_reexport_used
2. Wire into existing analytics if the project has one; otherwise
   structured backend logs.

**Acceptance:** Product can answer "how many customers actually
change their mapping after auto-match?" with data.

**Files:** `apps/web/src/components/payroll/XeroExportModal.tsx`,
backend log emission if needed.

---

## M3-T07 — Apply same hardening to QuickBooks + Zoho adapters

**Cross-reference, NOT in this milestone — separate workstream.**

The same pattern (persisted IntegrationToken, real OAuth round-trip,
audit log, idempotency-key, void support) applies to the existing
QuickBooks and Zoho adapters. Treat as a separate workstream
prioritised by customer demand.

**Tasks (when prioritised):**

1. Audit `mcp_servers/adapters/quickbooks.py` and
   `mcp_servers/adapters/zoho.py` against the M0+M1 checklist.
2. Reuse the IntegrationToken table and ExternalTokenManager — the
   shape is provider-agnostic.
3. Endpoints follow the `/integrations/<provider>/oauth/start` and
   `/oauth/callback` pattern.
4. Audit log: extend XeroExportLog into a generic
   AccountingExportLog with a `provider` column, OR create
   per-provider tables (decide based on volume).

**Acceptance:** Equivalent shape for QBO and Zoho when their
customers materialize.

**Files:** Multiple, when prioritized.
