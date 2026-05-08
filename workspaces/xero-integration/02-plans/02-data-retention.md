# Data Retention — Xero Integration

How long Arbor keeps the Xero-related records it stores, and what
redaction/deletion happens when. Driven by Singapore PDPA (purpose
limitation, data minimization) and IRAS record-keeping requirements
(7 years for tax-relevant business records).

---

## XeroExportLog (audit trail)

**What it stores:** one row per export attempt (POSTED / FAILED /
VOIDED) — payroll_run_id, journal_id, actor_id, posted_at,
payload_hash, line_count, bonus_total, forced_reexport, error_message
on failure.

**No PII** in the row itself — payload_hash is SHA-256 of the journal
JSON, not the JSON. Accountant queries are answered via the hash plus
the Arbor-side payroll run record.

**Retention:** 7 years from `posted_at`. Required by IRAS for
business records related to wages, statutory contributions, and tax
filings (Income Tax Act, Employment Act §95).

**Deletion:** annual job (deferred — not in M1) deletes rows older
than 7 years. Until then rows accumulate without an upper bound, but
volumes are tiny (one per export attempt per company) so storage
cost is negligible.

---

## IntegrationToken (OAuth credentials)

**What it stores:** Fernet-encrypted access_token + refresh_token,
xero_tenant_id, scopes, connected_by user_id, connected_at,
disconnected_at.

**Active rows (`disconnected_at = ''`)** — kept while the connection
is live. Tokens are personal data under PDPA: associated with the
authorising user's Xero session.

**Disconnected rows (`disconnected_at != ''`)** — soft-deleted on
revoke. Two retention phases:

| Age since disconnect | What                                                                                                                                      |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 0–90 days            | Full row retained (in case of dispute or restoration)                                                                                     |
| 90+ days             | `access_token_encrypted` and `refresh_token_encrypted` redacted to empty strings; metadata (xero_tenant_id, connected_by, dates) retained |
| 7 years              | Row hard-deleted entirely                                                                                                                 |

**M1-T07 hard-delete on customer-initiated disconnect.** When a user
clicks Disconnect, the active row is hard-deleted (not soft-deleted)
because the purpose has ended and PDPA's data-minimization principle
applies. Audit history of the disconnect event lives separately in
the export log + Arbor's general audit log, so the row deletion
doesn't lose accountability.

The 90-day-redact policy applies to rows that became disconnected via
_revoke-from-Xero-side_ paths (`_api_call` 401 → auto-disconnect,
`_refresh_token` invalid_grant) where we still want a short window
of full-row retention for support/dispute resolution.

---

## XeroAccountMapping

**What it stores:** the six bucket → Xero account-code mappings per
company. Last-updated-by user id and timestamp.

**No PII.** Account codes are accountant-set strings.

**Retention:** kept while the company exists. Deleted on company
offboarding (cascade from Company deletion).

---

## Migration / redaction script

`scripts/redact_old_xero_tokens.py` (monthly cron):

```python
SELECT id FROM integration_tokens
WHERE disconnected_at != ''
  AND disconnected_at < (NOW() - INTERVAL '90 days')::TEXT
  AND (access_token_encrypted != '' OR refresh_token_encrypted != '')
```

For each → `UPDATE … SET access_token_encrypted = '',
refresh_token_encrypted = ''`.

The 7-year hard-delete is a separate, deferred job — Xero
integration is too new for any rows to be eligible yet.

---

## Void / reversal date semantics (M2-T10)

When a customer voids an exported journal via the run detail page,
the adapter PUTs `Status: VOIDED` against the original ManualJournal
ID and **does not change the JournalDate**. Implications:

- The void appears in the customer's Xero on the **original posting
  date**, not the void date. This preserves period accuracy — the
  expense and the reversal both belong to the period the payroll
  was actually for.
- Auditors and accountants see a clean trail: a POSTED journal on
  date X, then a VOIDED status update on the same id. Drilldown
  shows when the void happened (Xero tracks `UpdatedDateUTC`
  internally) but the ledger date stays put.
- Arbor mirrors this on its side: `XeroExportLog` records two rows
  for the run — POSTED with `posted_at = original`, then VOIDED
  with `posted_at = now`. The journal_id is identical on both rows
  so the pair is queryable as a unit.

We chose this over a "post a counter-journal on today's date"
approach because:

1. SG accountants generally prefer same-period reversals for
   period-close cleanliness.
2. Counter-journals would double the row count in Xero's journal
   report, making month-end reconciliation harder.
3. Re-exporting after a void uses a fresh idempotency key (the
   force counter increments) so the new journal is genuinely a new
   entry, not a duplicate dedupe.

If a customer needs the void to land on the void date specifically
(rare; usually for next-FY corrections), they can manually add a
counter-journal in Xero — Arbor doesn't currently expose that.

---

## Disconnect verification (M2-T06)

The end-to-end disconnect path is exercised in two places:

1. **Settings → Integrations card** — when a user clicks the
   Disconnect button (and the integration card detects `xero`,
   special-cases the new endpoint), the page reloads and the card
   flips to Disconnected.
2. **Settings → Integrations → Xero** dedicated page — full
   disconnect flow with confirmation prompt, hard-delete + Xero-side
   revoke, page reload to flip status.

A 401 on any subsequent `/api.xro/2.0/*` call also auto-disconnects
locally (covered by `_api_call`'s 401 path → `revoke_token` +
`XeroReauthRequired`). Smoke-test scenarios:

- **User-initiated disconnect**: confirm dialog → POST → IntegrationToken
  row hard-deleted → settings card flips → Xero "Connected apps"
  no longer lists Arbor.
- **Xero-side revocation**: customer revokes from inside Xero →
  next API call returns 401 → adapter auto-disconnects → next page
  load shows "Connect Xero" instead of "Connected".
- **Refresh-token expiry**: `_refresh_token` returns `invalid_grant`
  → adapter auto-disconnects → next page load shows reconnect prompt.

These paths share the same `revoke_token` / `hard_delete` helpers,
so once one passes the others should too.

---

## What we do NOT store

- The plaintext payroll journal JSON sent to Xero (we hash it).
- Xero account names/descriptions beyond what the chart-of-accounts
  cache holds (24h TTL, in-memory only).
- Xero webhook payloads (none received yet — when M1-T09 lands, we
  will store webhook events for ≤30 days for replay).

---

## Audit/compliance pointers

- PDPA principles applied: purpose limitation (token kept only while
  needed), data minimization (90-day redaction once disconnected),
  retention limit (7-year cap).
- IRAS Income Tax Act §67 (record-keeping period — 5 years; we use 7
  for safety).
- Cross-reference: `.claude/rules/security.md` (no PII in logs),
  `.claude/rules/seeding.md` (production-data safety).
