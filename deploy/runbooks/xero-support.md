# Xero Integration — Support Runbook

For Tier-1 support handling customer-reported Xero issues. Steps
assume access to the production DB (read-only is enough for
diagnostics) and the prod logs.

Cross-reference: `deploy/xero-deployment-runbook.md` for ops + alert
thresholds. `workspaces/xero-integration/02-plans/02-data-retention.md`
for retention/PDPA policy.

---

## "My export failed"

### Step 1 — find the failure row

```sql
SELECT id, payroll_run_id, status, error_message, posted_at, actor_id
FROM xero_export_logs
WHERE company_id = :company_id
ORDER BY posted_at DESC
LIMIT 10;
```

The most recent FAILED row's `error_message` tells you which class
of error.

### Step 2 — match the error class to the fix

| `error_message` contains               | What it means                                  | What to do                                                                                                                         |
| -------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `account_invalid:` followed by code(s) | A mapped account was archived/renamed in Xero  | Tell customer: "Settings → Integrations → Xero → click 'Refresh accounts'. Check the mapping page banner shows green, then retry." |
| `reauth_required`                      | Refresh token expired (60-day idle) or revoked | Tell customer: "Click 'Reconnect Xero' on the modal — your token expired."                                                         |
| `rate_limit:`                          | Hit Xero's 60/min or 5000/day cap              | Wait the retry-after window. Look for spike pattern (one customer? one Xero org?).                                                 |
| `void_failed:`                         | Force-re-export couldn't void prior journal    | Customer's prior journal may have already been voided in Xero. Have them check and use force=true again, or void manually.         |
| Anything else                          | Generic Xero 4xx/5xx                           | Grep prod logs for the same `posted_at` to find the structured `xero event=...` line.                                              |

### Step 3 — grep the structured logs

Every export attempt logs `xero event=export_run` (success) or
`event=post_payroll_journal outcome=failure` (adapter-level failure)
with stable field names:

```
grep "company_id=$CID" /var/log/api.log | grep "xero event="
```

Pull the `xero_status`, `error`, `latency_ms`, `journal_id` fields
from the offending line.

---

## "I'm not connected" (but I was yesterday)

### Likely causes (in order)

1. **Refresh token expired** (60 days idle) — adapter auto-disconnected
   them on the most recent attempt.
2. **They revoked from Xero side** — adapter auto-disconnected on the
   first 401.
3. **Backend restart with stale `INTEGRATION_ENCRYPTION_KEY`** — every
   token becomes un-decryptable.

### Diagnose

```sql
SELECT id, disconnected_at, expires_at, scopes
FROM integration_tokens
WHERE tenant_id = :company_id::TEXT AND provider = 'xero'
ORDER BY id DESC LIMIT 5;
```

- `disconnected_at != ''` → soft-deleted, customer reconnect needed.
- `disconnected_at == ''` and `expires_at < now` → access token
  expired but refresh token should work; tell them to retry once.
- No row at all → never connected (or hard-deleted on disconnect).

For (3), check the keepalive cron logs at
`/var/log/xero-keepalive.log` — sudden burst of "invalid token" /
"InvalidToken" entries across customers means the encryption key
changed.

---

## "I posted a journal twice"

### Diagnose

```sql
SELECT id, journal_id, status, posted_at, actor_id, forced_reexport
FROM xero_export_logs
WHERE payroll_run_id = :run_id
ORDER BY posted_at;
```

Two POSTED rows with different `journal_id` for the same `payroll_run_id`
indicates the void-on-force flow worked but the prior journal is
still posted in Xero.

### Walkthrough

1. Confirm in customer's Xero (`Reports → Journal Report`) which
   journals are present.
2. If both exist as POSTED in Xero: void one manually from Xero's UI
   on the duplicate's date. Tell the customer.
3. If one exists as VOIDED, our books are already correct — explain
   it's the audit trail of the corrected operation.

### Why this should not happen

- M0-T02 advisory lock prevents concurrent same-run POSTs.
- M1-T06 idempotency-key dedupes network retries at Xero's side
  (24h window).
- M2-T01 force-re-export voids the prior journal before posting.

If duplicates appear, M0-T02's lock or the idempotency-key path
likely regressed — open a P1 issue.

---

## "How do I manually reset a customer's Xero connection?"

### As a hard reset (rare — only when the customer is locked out)

```sql
-- Soft-delete the active token row so the customer sees "Connect Xero".
UPDATE integration_tokens
SET disconnected_at = NOW()::TEXT
WHERE tenant_id = :company_id::TEXT
  AND provider = 'xero'
  AND disconnected_at = '';
```

Tell them to reconnect. The 90-day token redaction job will clean
up the row eventually; no PII risk in the meantime because tokens
are Fernet-encrypted at rest.

**Don't hard-delete unless they explicitly ask** — the soft-delete
preserves audit history.

---

## Standard reply templates

### Account-mapping update needed

> Hi <name> — your last Xero export hit account code <CODE>, which
> looks like it's been archived or renamed in Xero. To fix:
>
> 1. Go to Settings → Integrations → Xero in Arbor.
> 2. Click "Refresh accounts" (top right of the mapping section).
> 3. Update any banner-flagged mappings.
> 4. Retry the export.
>
> Let me know if it still fails after that.

### Reconnect needed

> Hi <name> — your Xero connection expired (Xero invalidates tokens
> after 60 days of disuse). It looks like you had a gap in payroll
> exports that triggered the timeout. To fix:
>
> 1. Settings → Integrations → click "Connect Xero".
> 2. Pick the same Xero organisation when prompted.
> 3. Retry the export.
>
> Your prior data and account mapping are preserved.

### Concurrent click protection

> The 409 you saw is our safety net — it kicks in when two clicks
> land within milliseconds of each other to prevent posting the same
> journal twice. Just wait a few seconds and retry the single
> remaining click; the export should go through.

---

## Escalation

If none of the above fits, escalate to engineering with:

- Company id
- Payroll run id
- Most recent `xero_export_logs` rows (full row, raw)
- Most recent `xero event=...` log lines (24h window grep)
- Customer's reported timestamp
