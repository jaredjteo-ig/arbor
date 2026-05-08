# Implementation Roadmap — Xero Production Readiness

Two phases. Phase 1 is the minimum that lets a real paying customer
connect their own Xero org and export safely. Phase 2 closes the
remaining SOFT blockers so the feature does not break on day-2 edge
cases.

The single most important thing is that **Phase 0 starts on day 0**:
submit the Xero partner-program app review, because Xero's review
gate is wall-clock days-to-weeks. Everything else can be parallel.

---

## Phase 0 — Calendar gate (start now, ~5 min of work)

**P0.1 Submit Xero partner-program app review**
Form: https://developer.xero.com/partner/sign-up
Submit the production app config (production redirect URI, name,
logo, privacy policy URL). Until this is approved, the app is capped
at 25 connections and anyone connecting sees a "this app is not yet
approved" warning. Approval typically takes 1-3 weeks.

---

## Phase 1 — Minimum viable production (1-2 days work, blocking)

Sequence matters: nothing later in the list works until earlier items
are in place.

### P1.1 — `INTEGRATION_ENCRYPTION_KEY` in production env (~30 min)

- Generate a stable Fernet key (`Fernet.generate_key().decode()`).
- Add to deployed environment (GCP secret manager, or env var on the
  prod compose file at 136.110.51.61).
- **Without this, Phase 1.3 cannot persist tokens that survive
  restart.** This is the cheapest item but the prerequisite for all
  token persistence.

### P1.2 — Fix production scopes in `XeroAdapter.get_authorization_url` (~15 min)

- Replace the legacy broad scope set (line 116-124 of `adapters/xero.py`)
  with `["openid", "offline_access", "accounting.manualjournals",
"accounting.settings.read"]`.
- Already proven against real Xero in the e2e test.
- Drop `profile`, `email`, `accounting.reports.read`,
  `accounting.transactions` — none are used.

### P1.3 — `XeroOAuthConnection` table + adapter switch (~3 hours)

Schema (one DataFlow `@db.model`):

```
@db.model
class XeroOAuthConnection:
    company_id: int                        # Arbor company
    xero_tenant_id: str = ""               # Xero org id (chosen at connect)
    xero_tenant_name: str = ""             # Display
    access_token_encrypted: str = ""       # Fernet(INTEGRATION_ENCRYPTION_KEY)
    refresh_token_encrypted: str = ""
    expires_at: str = ""                   # ISO timestamp
    scopes: str = ""                       # space-separated
    connected_at: str = ""
    connected_by: int = 0
    disconnected_at: str = ""              # soft-delete
```

Then write a thin DB-backed `TokenStore` that the adapter consumes.
Replace the in-memory singleton's `get_token_manager()` with the new
store behind the same interface (`store_token`, `get_valid_token`,
`refresh_if_expired`, `is_connected`). Tests survive without changes.

Retires: **H2, H4 (partial), S1, S8 (with cache invalidation on
disconnect)**.

### P1.4 — Production OAuth start + callback endpoints (~2 hours)

Two new endpoints, both in `api/routers/integrations.py`:

`GET /integrations/xero/oauth/start`

- `require_role("owner")`
- Generate `state = HMAC(INTEGRATION_ENCRYPTION_KEY,
f"{company_id}:{user_id}:{nonce}")`, persist nonce in a short-TTL
  cache or use signed token; returning the redirect URL only after
  bound to session.
- Build auth URL via `XeroAdapter.get_authorization_url` with the
  fixed scopes (P1.2) and a redirect URI of
  `<live-app-url>/integrations/xero/oauth/callback`.
- Return `{redirect_url}` to frontend; frontend `window.location =
redirect_url`.

`GET /integrations/xero/oauth/callback`

- Validates the `state` HMAC against the user's session — abort on
  mismatch (H7 fix).
- Calls `XeroAdapter.handle_oauth_callback(company_id, code,
redirect_uri)`.
- Calls `_get_xero_tenant_id` to fetch Xero connections.
- If `len(connections) == 1`: persist the row.
- If `len(connections) > 1`: redirect to a `/settings/integrations/xero/pick-org`
  page with the connection list, ask user to choose, persist on
  selection.
- Final redirect: `/settings/integrations?xero=connected`.

Retires: **H1, H3, H7, H4 (full)**.

### P1.5 — `XeroExportLog` audit table (~1 hour)

```
@db.model
class XeroExportLog:
    company_id: int
    payroll_run_id: int
    journal_id: str = ""               # Xero ManualJournalID
    posted_at: str = ""
    actor_id: int = 0                  # who clicked Export
    line_count: int = 0
    payload_hash: str = ""             # SHA256 of journal_data — proves what was sent
    status: str = ""                   # POSTED / VOIDED / FAILED
    error_message: str = ""            # populated on FAILED
```

Write on every POST (success and failure). The `payload_hash` lets us
prove later exactly what was sent without storing PII-laden payloads.

Retires: **S3**.

### P1.6 — Idempotency-Key on POST ManualJournals (~30 min)

Xero accepts `Idempotency-Key` header on POST. Use:
`f"{company_id}:{payroll_run_id}:{force_counter}"` where
`force_counter` increments on each `force=true` re-export. Adapter-level
change in `_api_call`. Retires **S4**.

### P1.7 — Server-side `force=true` enforcement (~15 min)

The export endpoint already checks `xero_journal_id` server-side, but
voiding the prior journal before posting a replacement is missing.
Either:

- Block `force=true` until P2.1 (void flow) lands, or
- Hold a pre-flight void call here — call adapter `void_journal(prior_id)`
  before posting the new one, atomically.

Retires: **S5**.

---

## Phase 2 — Day-2 robustness (3-4 days, can ship after Phase 1)

### P2.1 — Void / undo flow (~3 hours)

- Adapter method `void_journal(tenant_id, journal_id)` that PUTs to
  `ManualJournals/{id}` with `Status: VOIDED`.
- Endpoint `POST /payroll/runs/{run_id}/void-xero-export`.
- Modal button "Void this Xero journal" when `xero_journal_id` is set.
- Audit log entry on void.

Retires: **S6**.

### P2.2 — Account mapping settings page (~2 hours)

- New page `/settings/integrations/xero` that loads the saved mapping,
  lets user re-pick from current chart of accounts, and saves via
  the existing `PUT /payroll/xero/account-mapping`.
- Cache invalidation: when a customer reopens this page, force-refresh
  the chart of accounts (drop the 24h cache for that tenant).

Retires: **S7, S8**.

### P2.3 — Decimal arithmetic in journal builder (~1 hour)

- Convert all accumulators in `xero_payroll_journal.py` from `float`
  to `Decimal` (`getcontext().prec = 28`).
- Round only at line emit (`Decimal.quantize(Decimal('0.01'))`).
- Update unit tests to use `Decimal` test data and verify large-N
  payroll runs balance.

Retires: **S9**.

### P2.4 — Per-Xero-org rate limiting (~1 hour)

- Move the rate limit key from `f"payroll_xero_export:{company_id}"` to
  `f"xero_org:{xero_tenant_id}"` for export endpoint.
- Adapter-level rate limit also keyed by `xero_tenant_id`, not Arbor
  `tenant_id`. Helper exists (`check_rate_limit`) — change the keys.

Retires: **S2**.

### P2.5 — `bonus_total` derived from payslip items (~1 hour)

- Replace the modal's free-form `bonus_total` field with a server-side
  default: sum of `PayslipItem.amount` where `item_type == "bonus"`.
- Show the auto-calculated value, allow override but warn on mismatch.

Retires: **S10**.

### P2.6 — Disconnect button + revocation handling (~2 hours)

- Settings → Integrations → Xero "Disconnect" button.
- On click: PUT `XeroOAuthConnection.disconnected_at`, drop tokens
  from the DB row.
- Adapter `is_connected` checks `disconnected_at == ""`.
- 401 from Xero in any call → mark `disconnected_at` automatically (S12).

Retires: **P1, S12**.

### P2.7 — Last-export status badge on run detail (~30 min)

Already partly there — surface `xero_journal_id` and `xero_exported_at`
on the run detail page even when the modal is closed. Trivial.

Retires: **P2**.

---

## Effort estimate

| Phase | Work      | Calendar                     |
| ----- | --------- | ---------------------------- |
| P0    | 5 min     | 1-3 weeks of waiting on Xero |
| P1    | ~8 hours  | 1-2 working days             |
| P2    | ~10 hours | 2-3 working days             |

After P0 (review submitted) + P1 (production-safe), the feature is
ready for the first paying customer. P2 should follow within the
first week of go-live to avoid customer-facing regressions.

## What we are NOT doing in this plan

- App marketplace listing (separate workstream, downstream of P0).
- QuickBooks / Zoho equivalents — same architecture will apply, but
  ship Xero alone first.
- Two-way sync — we only push journals; reading invoices/bills from
  Xero is a different feature.
- Saga-based retry orchestration for export failures (the existing
  `mcp_servers/saga.py` could be wired in, but P1.5 audit log + P1.6
  idempotency cover the failure modes that matter for first paying
  customer).
