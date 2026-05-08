# Third-Party Integration Patterns

The reference playbook for moving any third-party integration (Xero,
QuickBooks, Zoho, future accounting/HR/banking SaaS) from "adapter
exists but unwired" to "production-ready, customer-safe." Codified
from the Xero payroll-export workstream — see
`workspaces/xero-integration/todos/completed/` for the source
milestones (M0..M4) this skill distils.

This skill answers: **"I'm wiring up a new accounting/HR third-party
integration — what must I get right, and what gets silently wrong if
I don't?"**

> **How to read this skill.** Treat the patterns as _reference shapes_
> derived from the Xero workstream, not drop-in code. Re-derive
> against the current codebase before copying — symbol names cited
> here (`_xero_export_lock`, `_extract_offending_codes`,
> `xero_oauth_callback`, etc.) are correct as of M0..M4 codification,
> but if `grep` fails, search for the _behaviour_ described before
> assuming it's missing. Provider-specific details (rate limits,
> refresh-token windows, idempotency mechanisms, OAuth multi-org
> shape) **vary between Xero, QBO, and Zoho** — flagged inline
> below; verify against the relevant provider's current docs at
> integration time.

## When to use

- Adding any new OAuth-based third-party integration to Arbor.
- Hardening an existing adapter that passes mocked tests but has
  never seen a real customer.
- Reviewing an integration PR for production-readiness gaps.
- Diagnosing a Xero/QBO/Zoho production incident.

## The hardening hierarchy

Each pattern below has a category — **HARD** / **SILENT** /
**OPERATIONAL** — that ranks the cost of getting it wrong:

| Category    | Cost of skipping                                                   |
| ----------- | ------------------------------------------------------------------ |
| HARD        | Feature literally cannot work for a real customer                  |
| SILENT      | Works once, breaks invisibly — wrong data in wrong place, no error |
| OPERATIONAL | Works correctly but undiagnosable / unrecoverable on incident      |

Skip a HARD item and the customer reports it. Skip a SILENT item and
nobody notices for weeks; the customer's accountant finds it during
audit.

---

## 1. Multi-org OAuth picker — SILENT data leak

**The bug:** A Xero or Zoho OAuth connection can grant access to
**multiple organisations** the authorising user can see. Bookkeepers
commonly have 5+. A naive `connections[0]` pick silently routes one
customer's payroll into another customer's books — no error, just
wrong data in the wrong tenant.

**Per-provider OAuth shape (verify at integration time):**

- **Xero**: post-consent `/connections` endpoint returns the full
  list. The picker is a separate page after the callback.
- **QBO**: realm is chosen _during_ consent — the user picks the
  company on Intuit's screen. The callback returns one `realmId` and
  there is no post-hoc multi-realm picker. The fix below is
  Xero-shaped and does **not** apply to QBO; for QBO, validate the
  returned `realmId` against the authorising user's expectations and
  surface it on the settings page.
- **Zoho**: post-consent `/organizations` endpoint returns the list;
  picker pattern applies similarly to Xero. Verify against current
  Zoho Books docs.

**The fix (Xero / Zoho-shape, post-consent picker):**

1. After token exchange, call the provider's connections /
   organizations endpoint to list **all** org/tenant IDs.
2. If exactly one → persist directly.
3. If more than one → stash the list under an HMAC-signed nonce in
   a short-TTL store, redirect to a picker page.
4. Picker submits the chosen ID; server validates the chosen ID was
   in the original authorised list before persisting.
5. Provide a "Switch organisation" link on the integration settings
   page that re-runs the picker without full re-OAuth.

**Reference implementation:**

- `src/hr_advisory/api/routers/integrations.py` — see
  `xero_oauth_callback`, `xero_pending_orgs`, `xero_pick_org`.
- `src/hr_advisory/mcp_servers/adapters/xero.py::list_xero_connections`.
- `apps/web/src/app/(dashboard)/settings/integrations/xero/pick-org/page.tsx`.

---

## 2. HMAC-signed OAuth state — HARD security gap

**The bug:** Without a signed and session-bound `state` parameter,
an attacker can stitch their own connection onto another customer's
account via CSRF on the callback URL.

**The fix:**

1. `state = json({c: company_id, u: user_id, n: nonce, t: now}) +
"." + hmac_sha256(payload, key)` where `key` is bytes derived
   from `INTEGRATION_ENCRYPTION_KEY`.
2. Verify HMAC on callback using `hmac.compare_digest` (constant-
   time; never use `==`).
3. Enforce TTL (10 minutes is a sensible default for _our_ flow —
   long enough for the consent round-trip, short enough that a
   leaked state token is stale; not provider-mandated).
4. **Key reuse note.** The Xero implementation uses the same
   `INTEGRATION_ENCRYPTION_KEY` env var as the source of secret
   material for both Fernet (token-at-rest) and HMAC-SHA256 (state
   signing). They use the secret in different ways — Fernet
   instantiates a key object, HMAC takes raw bytes via
   `hmac.new(key.encode(), ...)`. **Do not feed the raw Fernet key
   bytes into the Fernet primitive twice; do not derive HMAC from
   the Fernet token format.** If you need stronger separation,
   derive sub-keys via HKDF.
5. **Do not rotate `INTEGRATION_ENCRYPTION_KEY` on a schedule.**
   Rotation invalidates every customer's stored token (Fernet
   decryption fails) and forces a global re-OAuth. Treat the value
   as a stable long-term secret. Rotate only on confirmed key
   compromise, and plan the rotation as a customer-impacting event.

**Reference:** `xero_oauth_start` and `xero_oauth_callback` in
`api/routers/integrations.py`. Unit test for HMAC round-trip in
`tests/unit/test_xero_oauth_state.py`.

---

## 3. Persisted token store — HARD restart safety

**The bug:** An in-memory token store loses every customer's
connection on backend restart. Every deploy = "Reconnect" prompts
for everyone. With multi-worker uvicorn, refreshes done by worker
A are invisible to worker B (intermittent 401s after 30 minutes).

**The fix:**

1. `IntegrationToken` `@db.model` with: `tenant_id`,
   `provider`, encrypted `access_token`/`refresh_token`,
   `expires_at`, `scopes`, provider-specific extras
   (`xero_tenant_id`, `qbo_realm_id`, etc.), `connected_by`,
   `connected_at`, `disconnected_at` (soft-delete column).
2. Fernet-encrypted at rest using `INTEGRATION_ENCRYPTION_KEY`.
3. Write-through cache in `ExternalTokenManager`: in-process dict
   for hot-path reads, DB read on cache miss, DB write on
   store/refresh, cache invalidation on revoke.
4. `is_connected()` returns True whenever a refresh_token exists
   (even if access_token is stale) — flipping to "disconnected"
   every 30 minutes is wrong UX.
5. Soft-delete (`disconnected_at`) preserves audit history;
   hard-delete only on user-initiated PDPA disconnect.

**Reference:** `IntegrationToken` in `models/company_user.py`,
`ExternalTokenManager` in `mcp_servers/auth/token_store.py`,
migration `scripts/migrate_integration_tokens.py`.

---

## 4. Refresh-token cliff handling — SILENT then HARD

**The bug:** Most OAuth providers expire refresh tokens after some
idle window (Xero: 60 days). A customer who runs payroll once a
month hits the cliff after two missed months. The next API call
returns `invalid_grant`; without explicit handling it surfaces as
a generic 401 with no guidance.

**The fix:**

1. `XxxReauthRequired` typed exception. `_refresh_token` detects
   `invalid_grant`, hard-disconnects the local token row, raises
   the exception.
2. `_api_call` 401 path triggers the same auto-disconnect — covers
   the case where the user revoked from the provider's side.
3. Calling endpoint catches the exception, returns structured 401:
   `{message, action: "reconnect", reconnect_url:
"/settings/integrations?reconnect=xero"}`. Frontend renders a
   "Reconnect" CTA, not a generic auth error.
4. **Daily keepalive cron** rotates tokens within 7 days of expiry
   so most customers never reach the cliff in normal use. Catches
   `XxxReauthRequired` so a single bad token doesn't crash the
   batch.

**Reference:** `XeroReauthRequired` and the `_refresh_token` /
`_api_call` paths in `adapters/xero.py`. Cron at
`scripts/keep_xero_tokens_warm.py`.

---

## 5. Concurrent-export TOCTOU advisory lock — SILENT duplicate

**The bug:** Two clicks within milliseconds (or two browser tabs)
race on the read-then-write of any "version counter" used in
idempotency keys. Both reads see counter=0, both writes happen. If
the upstream's idempotency dedupe arrives first, you get two
identical writes; if not, two POSTs. Either way: **silent duplicate
journals in the customer's books**.

**The fix:**

1. Wrap the write endpoint body in a Postgres advisory lock keyed on
   a deterministic `(class_id, object_id)` derived from
   `(company_id, run_id)`.
2. `pg_try_advisory_lock` (non-blocking) — second concurrent call
   gets `False` → return 409 immediately.
3. Implement as a context manager that holds a fresh psycopg2
   connection for the lock duration; release in `__exit__`.
4. Per `rules/infrastructure-sql.md` Rule 2 — multi-statement
   operations that must be atomic require explicit transactions
   anyway.
5. Pair with a regression test that fires concurrent POSTs (thread
   pool of 2) and asserts: exactly one 200 + one 409, exactly one
   upstream POST attempt, exactly one POSTED audit row.

**Reference:** `_xero_export_lock` context manager in
`api/routers/payroll.py`. Regression test at
`tests/regression/test_xero_concurrent_export.py`.

---

## 6. Idempotency-Key + force counter — SILENT duplicate

**The bug:** A network blip between Arbor and the upstream causes a
client retry. Without an Idempotency-Key, the second attempt is a
fresh write — duplicate journal in the customer's books.

**The fix:**

1. Send a stable per-operation idempotency token via the upstream's
   supported mechanism. **Verify per provider — there is no
   universal standard:**
   - **Xero**: `Idempotency-Key` HTTP header. Documented dedupe
     window applies (verify current docs before relying on a
     specific number); short retries within a few hours are the
     usual safety target.
   - **QuickBooks Online**: uses `RequestId` (a query parameter,
     not a header) on POST. Different shape — do not strip
     `Idempotency-Key` onto QBO endpoints expecting it to work.
   - **Zoho Books**: at last check did not honour
     `Idempotency-Key`; verify, and if absent, lean on the
     advisory lock (#5) plus a uniqueness check (e.g. existing
     journal id on the run row) to dedupe.
   - **Stripe-style APIs** (banking, payments): `Idempotency-Key`
     header with a documented 24h window.
2. The token format Arbor uses for Xero is
   `provider:{company}:{run}:{counter}`. The pattern (stable
   per-attempt token, increments only on intentional re-tries)
   generalises; the header name does not.
3. Counter increments only on explicit `force=true` re-export, so
   accidental retries dedupe but intentional re-exports are
   genuinely new.
4. Pair with the advisory lock from #5 so the read-then-bump of the
   counter is atomic.
5. **Force-re-export must void the prior journal first.** Without
   it, `force=true` leaves two POSTED journals for the same period
   in the customer's books — reconciliation hell. This is itself a
   reusable pattern (any "republish" flow needs prior-revoke).

**Reference:** `_api_call` `idempotency_key` parameter in
`adapters/xero.py`; `next_force_counter` + `void_journal` call
in the export endpoint.

---

## 7. PDPA-compliant disconnect — HARD compliance

**The bug:** Soft-delete-forever violates PDPA's purpose-limitation
principle. Also: not revoking at the upstream means the customer's
"Connected apps" list still shows Arbor after they disconnect on
our side — confusing and bad-faith.

**The fix:**

1. `POST /integrations/{provider}/disconnect` does both:
   - `DELETE /connections/{id}` at the upstream to revoke source.
   - Hard-delete the active `IntegrationToken` row locally.
2. Best-effort on the upstream: if the revoke fails (network /
   already-revoked), proceed with local delete and log the upstream
   error. Customer's intent is honoured locally either way.
3. Disconnected rows older than 90 days have their encrypted token
   columns redacted (separate cron); full row dropped at 7 years
   (IRAS retention requirement for tax records).
4. Cascade on company offboarding: deleting a Company must
   disconnect all its integrations.

**Reference:** `xero_disconnect` endpoint in
`api/routers/integrations.py`; `revoke_at_source` in
`adapters/xero.py`; `hard_delete` in
`mcp_servers/auth/token_store.py`; redaction cron at
`scripts/redact_old_xero_tokens.py`.

---

## 8. Audit log with payload hash — OPERATIONAL

**The bug:** When a customer's accountant asks "who posted journal
X on date Y?", you have no answer without forensic reconstruction.

**The fix:**

1. Append-only `XxxExportLog` `@db.model` with: `company_id`,
   `payroll_run_id` (or whatever the per-export reference is),
   `journal_id` (upstream's ID), `posted_at`, `actor_id`
   (Arbor user), `payload_hash` (SHA-256 of the JSON sent),
   `status` (POSTED / FAILED / VOIDED), `error_message` on
   FAILED, plus operation-specific fields (`bonus_total`,
   `forced_reexport`).
2. Write on **every** code path — success, failure, void — best
   effort; never raise into the request path.
3. `payload_hash` lets you prove what was sent without storing
   PII-laden line text. The hash is the audit-grade identity of
   the operation.
4. Retention: 7 years (Income Tax Act for SG businesses; verify
   per jurisdiction).

**Reference:** `XeroExportLog` model + `_write_audit` helper in
`api/routers/payroll.py`. Migration
`scripts/migrate_xero_export_log.py`.

---

## 9. Scope evolution + reconnect-for-scope — OPERATIONAL

**The bug:** When a future feature needs a new OAuth scope (e.g.
adding `accounting.contacts.read` for invoice mapping), existing
customers' tokens won't have it. Calls 403 with no guidance.

**The fix:**

1. Define required scopes per feature in a constants dict
   (`XERO_SCOPE_REQUIREMENTS = {"post_payroll_journal":
{"accounting.manualjournals"}, ...}`).
2. `assert_xero_scopes(stored_scopes, feature)` raises typed
   `XeroScopeMissing` if any required scope is absent.
3. Endpoint catches and returns structured 403 with
   `{action: "reconnect_for_scope", missing_scopes,
reconnect_url}`. Frontend deep-links a re-OAuth that requests
   the broader scope set.
4. Don't auto-disconnect on scope mismatch — the existing scopes
   may still cover the existing flows. Only the new feature is
   blocked.

**Reference:** `XERO_SCOPE_REQUIREMENTS`, `assert_xero_scopes`,
`XeroScopeMissing` in `adapters/xero.py`.

---

## 10. Mapping health — chart-of-accounts staleness — SILENT

**The bug:** A customer's accountant archives or renames a Xero
account. Our cached chart-of-accounts is stale. The customer's
saved mapping points to a code that no longer exists. Next export
fails with a generic 400.

**The fix:**

1. Catch the upstream's "account code is not valid" / "account ID
   not found" 400 in the adapter's POST path. Surface as typed
   `XxxAccountInvalid` carrying the offending codes (extract via
   regex from the upstream error message).
2. Adapter invalidates the chart-of-accounts cache on this error.
3. Endpoint catches and returns 409 with `{offending_codes,
mapping_url}`. UI deep-links the customer to the mapping page.
4. **Proactive health check**: `GET /payroll/xero/mapping-health`
   compares saved mapping codes against the current chart and
   returns `{archived, missing, system_managed, ok}`. Settings
   page shows a banner before the next export attempt fails.
5. `?refresh=true` query param on chart-of-accounts bypasses the
   24h cache for the "I just changed something in Xero" flow.

**Reference:** `XeroAccountInvalid` + `_extract_offending_codes`
in `adapters/xero.py`; `get_xero_mapping_health` endpoint in
`api/routers/payroll.py`.

---

## 11. Decimal arithmetic at the boundary — SILENT correctness

**The bug:** Float arithmetic accumulates ULP errors on large-N
sums. For a 5-employee payroll the balance check holds; for 200+
employees the `abs(total) > 0.01` check fails on inputs that
balance algebraically.

**The fix:**

1. All accumulators in the journal-builder service use
   `decimal.Decimal` with `getcontext().prec = 28`.
2. Convert at the boundary: `Decimal(str(value))` from float —
   the str() round-trip avoids IEEE-754 representation artefacts.
3. Round at line emission: `value.quantize(Decimal('0.01'),
rounding=ROUND_HALF_UP)`. Half-up is the SG accountant
   convention; banker's rounding is wrong.
4. Convert back to float at the API boundary (the upstream's HTTP
   client expects floats).

**Reference:** `_to_decimal`, `_quantize` in
`services/xero_payroll_journal.py`.

---

## 12. Bulk operations with skip-not-abort — OPERATIONAL

**The bug:** Customer onboarding wants to backfill 6 months of
payroll into Xero. Either: (a) they click Export per run for an
hour, or (b) a naive bulk endpoint aborts the batch on the first
failure.

**The fix:**

1. `POST /payroll/runs/bulk-export-xero` accepts `{run_ids: []}`.
   **Cap the batch size** (24 runs) — bounds rate-limit blast radius
   and request duration.
2. **Series, not parallel** — respects the upstream's per-org rate
   limit (60/min for Xero). One run at a time, no concurrency
   inside the request.
3. Per-run advisory lock acquisition with **skip-on-conflict**: if
   another export is in progress for the same run, append a 409
   result to the batch and continue with the next run.
4. Per-run try/except: failures yield `{run_id, ok: false,
status_code, error}` results. Never abort the batch.
5. Batch endpoint has its own rate limit (4/hour per company)
   independent of the per-run rate limit.

**Reference:** `bulk_export_runs_to_xero` endpoint in
`api/routers/payroll.py`.

---

## 13. Date-field timezone alignment — SILENT mis-period

**The bug:** Accounting providers interpret journal/transaction date
fields in the **organisation's** local timezone, not UTC. A
`datetime.now(timezone.utc).strftime("%Y-%m-%d")` fallback near
month-end posts to the wrong period for any org outside UTC.
Singapore is UTC+8 — exports between 16:00–24:00 UTC on the last day
of the month land in the next month's books.

**The fix:**

1. Require an explicit business-meaningful date field
   (`pay_date`, `posting_date`, etc.) on the source record. Reject
   the request with 400 if empty — do not fall back to "now".
2. Pass the date through as-is (`YYYY-MM-DD`); let the upstream
   apply its own timezone interpretation.
3. Cover with a unit test that an empty date field returns 400
   before any upstream call is made.

**Reference:** `pay_date` validation in the export endpoint;
`services/xero_payroll_journal.py` uses `pay_date` as the journal
date and falls back only to `period_end`, never to `now()`.

---

## 14. Mapping change history — OPERATIONAL audit recoverability

**The bug:** When a customer's accountant asks "why did Salary
Expense move from 477 to 478 between April and May exports?", you
have no answer without forensic reconstruction. Saved-mapping
overwrites lose the transition.

**The fix:**

1. Append-only `XxxAccountMappingHistory` `@db.model` with
   `company_id`, `field_name`, `previous_code`, `new_code`,
   `changed_by`, `changed_at`. One row per changed field per save.
2. The PUT mapping endpoint diffs the existing row against the new
   payload and writes one history row per changed field. First-time
   saves write no history (no previous to diff against).
3. Surface the most-recent-100 entries on the mapping settings
   page so customers see their own history. Best-effort write —
   never raise into the request path.

**Reference:** `XeroAccountMappingHistory` in
`models/company_user.py`; diff loop in `put_xero_account_mapping`;
migration `scripts/migrate_xero_mapping_history.py`.

---

## Cross-cutting: pattern caveats from red-team review

These warnings apply across multiple patterns. Add to the relevant
pattern's mental checklist:

- **Multi-worker cache invalidation (pattern #3 + #10).** Per-process
  in-memory caches diverge across uvicorn workers. A revoke or
  CoA-invalidate event hit by worker A leaves worker B serving
  stale state until natural eviction. Mitigate with: short TTL,
  pub/sub invalidation (Redis, NOTIFY/LISTEN), or DB-read on every
  state-sensitive call. The Xero token store is currently
  best-effort: revokes hit the DB, but workers may serve a stale
  cached token for up to one cache-entry lifetime.
- **Advisory-lock keyspace (pattern #5).** Postgres advisory locks
  share a global namespace across the entire database. Pick a
  stable `class_id` constant unique to each locking subsystem (Xero
  export uses `0x7E70_E000`); two subsystems sharing the same
  `class_id` could mutually block. Use a fresh psycopg2 connection
  per lock acquisition — do not pool, the lock is bound to the
  session.
- **Frontend double-click pairs with #5/#6.** Disable the submit
  button on `mutation.isPending` so a UI double-click can't
  generate two requests; the server-side advisory lock + idempotency
  key are the second belt for network-retry / multi-tab cases.

---

## Cross-cutting: structured logging

Every integration emits structured log lines via a
`provider_log_event(event, **fields)` helper. The format is
`provider event=name k1=v1 k2=v2 ...` — easy to grep, easy for
log aggregators to parse. Standard fields: `event`, `outcome`
(`success` / `failure`), `tenant_id`, `provider_tenant_id`,
`company_id`, `run_id`, `journal_id`, `latency_ms`,
`error`. `outcome=failure` logs at WARNING so alerting can
filter on severity.

**Reference:** `xero_log_event` in `adapters/xero.py`; alerting
thresholds documented in `deploy/xero-deployment-runbook.md` §7b.

---

## The Phase 0 / M0..M4 milestone framework

When wiring up a new integration, mirror the milestone structure
that worked for Xero:

| Milestone   | Scope                                                               | Items         |
| ----------- | ------------------------------------------------------------------- | ------------- |
| **Phase 0** | User actions: app credentials, partner program                      | calendar-only |
| **M0**      | Pre-launch BLOCKERS — silent-data-leak class                        | 6             |
| **M1**      | Finish-the-launch — frontend wiring + restart safety + PDPA         | 9-10          |
| **M2**      | Day-2 robustness — void/undo, mapping page, decimal, scope checks   | 12            |
| **M3**      | Polish + Ops — structured logs, alerts, audit history, bulk         | 7             |
| **M4**      | Customer-facing — help guide, support runbook, marketplace, privacy | 4             |

Total: ~38-40 items per integration. The first integration takes
~5 sessions. Subsequent ones using this skill as a checklist take
~2-3.

**Reference workspace structure:** `workspaces/xero-integration/`
contains `briefs/`, `01-analysis/01-gap-inventory.md`,
`02-plans/01-implementation-roadmap.md`,
`02-plans/02-data-retention.md`,
`02-plans/03-privacy-tos-deltas.md`, `todos/active/` →
`todos/completed/`, `.test-results`. Copy this shape for
QuickBooks / Zoho when prioritised.

---

## Provider-specific differences worth knowing

> **All cells are reference values from the M0..M4 codification —
> verify against current provider docs at integration time.** API
> limits, refresh-expiry windows, and OAuth flow shapes change.

| Provider | Daily limit (verify)     | Refresh expiry (verify) | Tenant unit                      | Multi-tenant OAuth flow                | Idempotency mechanism (verify)                               |
| -------- | ------------------------ | ----------------------- | -------------------------------- | -------------------------------------- | ------------------------------------------------------------ |
| Xero     | ~5,000/day, ~60/min      | ~60 days idle           | Org (`tenantId`)                 | Post-consent `/connections` picker     | `Idempotency-Key` HTTP header                                |
| QBO      | ~500/min, ~10 concurrent | per-app config          | Realm (`realmId`)                | Realm chosen at consent (single-realm) | `RequestId` query parameter, not header                      |
| Zoho     | ~2,500/day per org       | per-app config          | Organization (`organization_id`) | Post-consent `/organizations` picker   | None standard — rely on advisory lock + run-state uniqueness |

App-marketplace certification (Xero, QBO) is gated on customer
evidence — typically 3+ active connections — not bureaucratic
review. Apply only after the integration has shipped and is in use.

**See also:**

- `mcp-integrations.md` — connector inventory + MCP server architecture.
- `deploy/xero-deployment-runbook.md` — production deploy checklist (alerting thresholds, env vars, migrations, rollback).
- `deploy/runbooks/xero-support.md` — Tier-1 support runbook (diagnostic SQL, error-class table, reply templates).
- `workspaces/xero-integration/02-plans/02-data-retention.md` — retention/redaction policy.
- `workspaces/xero-integration/02-plans/03-privacy-tos-deltas.md` — privacy-policy + ToS copy ready for legal.

---

## Quick-reference patterns table

| Pattern               | Skip risk            | Code sentinel                     |
| --------------------- | -------------------- | --------------------------------- |
| Multi-org picker      | SILENT data leak     | `connections[0]` (Xero/Zoho)      |
| HMAC state            | HARD CSRF gap        | unsigned `state`                  |
| Persisted token store | HARD restart loss    | `self._store: dict`               |
| Refresh-token cliff   | SILENT then HARD     | no `XxxReauthRequired`            |
| Advisory lock         | SILENT duplicates    | read-then-write counter           |
| Idempotency token     | SILENT duplicates    | retry without per-op token        |
| PDPA disconnect       | HARD compliance      | soft-delete forever               |
| Audit log + hash      | OPERATIONAL          | logging.info() only               |
| Scope evolution       | OPERATIONAL          | hardcoded scopes only             |
| Mapping health        | SILENT 400s          | `coa_cache` no invalidation       |
| Decimal boundary      | SILENT large-N drift | `round(float, 2)`                 |
| Bulk skip-not-abort   | OPERATIONAL          | first-failure aborts batch        |
| Date timezone         | SILENT mis-period    | `datetime.now(utc)` fallback      |
| Mapping history       | OPERATIONAL          | mapping overwrite, no diff log    |
| Multi-worker cache    | SILENT staleness     | per-process dict, no invalidation |

If you see any of the right-column sentinels in a PR, the
left-column pattern is missing.
