# Brief — Production-Ready Xero Payroll Export

## What we have today (2026-05-08)

Backend code that posts a real Xero ManualJournal end-to-end against
Xero's Demo Company. 31 tests green (17 unit + 11 mocked integration +
3 against real Xero). The internals work: balanced journal lines,
auto-matched account suggestions, status guards, duplicate-export
guard, system-account filtering, Fernet-encrypted token store
(keyed by stable `INTEGRATION_ENCRYPTION_KEY`).

## Where this falls short for real customers

A paying customer cannot connect their own Xero org and export
through the product. The "Connect Xero" button on
`Settings → Integrations` is a stub; the production OAuth round-trip
is unwired; OAuth tokens vanish on backend restart; the wrong
ManualJournals scope is hardcoded in the production adapter (only the
local OAuth helper got fixed); there is no audit trail of what was
posted; there is no way to re-edit account mappings after the first
export; idempotency on the POST is missing, so a network retry would
double-post a journal.

## What the product needs to support

1. A real customer signs up for the Arbor product.
2. They click "Connect Xero" in Settings → Integrations.
3. They are redirected to Xero, choose **their own** Xero org from a
   real picker (multi-org accounts are common — bookkeepers especially),
   click Allow, and land back on Arbor with a persisted connection.
4. They run payroll, click Export to Xero on the run detail page,
   confirm the auto-matched mapping, and see a real journal in their
   Xero with a clear audit-log entry on the Arbor side.
5. If they mis-export, they can void the journal from inside Arbor.
6. If they disconnect Xero from inside Arbor, or revoke from inside
   Xero, the integration cleanly handles either side.
7. Everything survives backend restarts, multi-worker uvicorn, and
   the 30-minute Xero access-token TTL.

## Out of scope for this iteration

- App marketplace listing (separate workstream, downstream of partner
  app review).
- Two-way sync (we only push journals; we do not read invoices/bills).
- Other accounting integrations (QuickBooks, Zoho already have
  adapters — same shape will apply but separate workstream).
