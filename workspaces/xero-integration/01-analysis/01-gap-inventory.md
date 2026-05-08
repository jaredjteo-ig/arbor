# Gap Inventory — From Working E2E to First Paying Customer

Verdict from deep-analyst: my initial gap list (14 items) was
correct on substance, but 4 items belong in a harder category than I
had them, and there are **8 additional gaps** I missed — three of
which would result in real money landing in the wrong GL account
silently. This document consolidates everything in one place.

Categories:

- **HARD** — feature literally cannot work for a real customer.
- **SOFT** — works on first try, breaks on edge cases, restart, or
  multi-worker prod.
- **Polish** — would be nice; not required for first paying customer.

---

## HARD blockers

| #   | Gap                                                                                                                                                           | Why it blocks                                                                                                                                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| H1  | `/{provider}/connect` is a stub (`integrations.py` line 1095)                                                                                                 | Customer has no way to begin a real Xero OAuth round-trip. `redirect_url: ""` is returned.                                                                                                                                       |
| H2  | `ExternalTokenManager` is in-memory only (`token_store.py` line 102)                                                                                          | Backend restart drops every customer's OAuth tokens. Every deploy = "Reconnect Xero" prompts for everyone.                                                                                                                       |
| H3  | OAuth-callback endpoint does not exist                                                                                                                        | Even if H1 generated the auth URL, there's no `/oauth/callback/xero` to receive Xero's redirect, validate state, exchange code → tokens, and persist.                                                                            |
| H4  | `xero_tenant_id` not persisted                                                                                                                                | Multi-org customers (bookkeepers running 5+ companies) always export to the first connected org. Cannot be fixed by the per-process cache I added in `_resolve_xero_tenant_id` — multi-worker uvicorn diverges between requests. |
| H5  | Production `XeroAdapter.get_authorization_url` (line 116-124) still requests `accounting.transactions`, `accounting.reports.read`, `accounting.settings.read` | Apps registered after 2 March 2026 reject these. New customer signups post-cutoff will see the same `invalid_scope` error I hit. Only the OAuth setup script was fixed.                                                          |
| H6  | `INTEGRATION_ENCRYPTION_KEY` only set in dev `.env`                                                                                                           | Production token-manager will fall back to ephemeral keys, making any persisted tokens un-decryptable on next restart.                                                                                                           |
| H7  | OAuth `state` parameter is unsigned and unbound to user session                                                                                               | An attacker can stitch their Xero connection onto another customer's Arbor account via a CSRF-style attack on the callback URL. Audit-log integrity dies the moment this is exploitable.                                         |
| H8  | No production Xero app credentials                                                                                                                            | Currently using a dev sandbox app (capped users, demo-only). Production app needs Xero partner-program review — Xero takes days to weeks. **This is a calendar gate; start it today.**                                           |
| H9  | Production callback URL not registered in Xero app whitelist                                                                                                  | Tied to H8 — the live deployment domain (`central.kailash.ai` or whatever) must be on Xero's redirect URI list.                                                                                                                  |

---

## SOFT blockers

| #   | Gap                                                  | Failure mode                                                                                                                                                                                                                                    |
| --- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | Multi-worker uvicorn + in-memory token cache         | Refresh-token rotation done by worker A invisible to worker B → intermittent 401s ~30 minutes after each connect. Persistence (H2) fixes both.                                                                                                  |
| S2  | Rate-limiting per Arbor tenant, not per Xero org     | Customer running 3 Arbor companies into one Xero org will silently 429 during month-end. Xero limits 60 calls/min and 5,000/day **per Xero connection**, not per consumer.                                                                      |
| S3  | No `XeroExportLog` audit trail                       | SG SME compliance can't answer "who posted journal X on date Y?" Hard for accountant queries; necessary for IRAS posture if anything ever needs to be reconstructed.                                                                            |
| S4  | No `Idempotency-Key` header on POST `ManualJournals` | Network blip during POST → retry → **journal posted twice** in customer's books. Debits and credits doubled. Use `(company_id, payroll_run_id, force_counter)` as the key.                                                                      |
| S5  | `force=true` server-side bypass                      | Frontend modal blocks re-export by default, but a direct API call with `{"force": true}` skips the existing journal id and posts again. Should require explicit confirmation + ideally void the prior journal.                                  |
| S6  | No void/undo flow                                    | Customer posts a wrong journal → support email. Xero supports `Status: VOIDED` via PUT — wire it as the reverse of force-re-export.                                                                                                             |
| S7  | Mapping has no edit UI outside the export modal      | When the customer's accountant renames a Xero account, the saved code goes stale → next export silently miscategorises or 400s. Need `Settings → Integrations → Xero → Account mapping`.                                                        |
| S8  | `_coa_cache` 24h TTL with no invalidation            | Same vector as S7, shorter horizon. Cache is keyed by Arbor tenant, not Xero org id. Invalidate on disconnect/reconnect.                                                                                                                        |
| S9  | `float` arithmetic in journal builder                | For 5-employee runs balance holds. For 200-employee runs cross-totals (`gross - bonus`, `employer + employee + sdl + fwl + shg`) accumulate ULP errors and the `abs(total) > 0.01` balance check fails. Use `Decimal`, round only at line-emit. |
| S10 | `bonus_total` is a free-form modal input             | User can type any number; no cross-check against payslip line items. Splits Salary/Bonus expense incorrectly without any guardrail. Should be derived from `PayslipItem` records of type `bonus`.                                               |
| S11 | Auto-matcher patterns are substring matches          | `"cpf"` matches any account name containing it — including a customer's custom `"CPF reimbursement clearing"`. Currently safe because the modal forces user confirmation. Must never be applied silently.                                       |
| S12 | No webhook for Xero-side disconnection               | If user revokes Arbor's access from inside Xero, we only learn on next 401. Graceful but the "Connected" badge is stale until then.                                                                                                             |

---

## Polish

| #   | Gap                                                                                 |
| --- | ----------------------------------------------------------------------------------- |
| P1  | Disconnect / switch-org UI on Settings → Integrations                               |
| P2  | "Last exported to Xero on …" badge on the run detail page even when modal is closed |
| P3  | Telemetry: export success rate, retry counts, scope errors                          |
| P4  | Account-mapping change history (who edited which mapping when)                      |
| P5  | Bulk-export multiple historical runs (currently one click per run)                  |

---

## Architectural concerns flagged

1. **The token-manager singleton is the most concentrated risk.** Every
   Xero/CPF/future integration depends on `get_token_manager()`.
   Replacing in-memory with DataFlow-backed storage retires H2, S1,
   most of H6, and partially H4 in one focused workstream.
2. **First-connection-wins tenant resolution is structurally wrong**,
   not just a caching bug. Persist the chosen `xero_tenant_id` at
   OAuth-callback time, with an org picker shown when `len(connections)
   > 1`.
3. **Auto-match must remain advisory only.** Today the modal forces
   user confirmation before save. Any future code path that bypasses
   the modal (e.g. a "set up Xero with one click" flow) reintroduces
   silent miscategorisation risk.
4. **`force=true` re-export without voiding** leaves the customer's
   Xero with two posted journals for the same payroll run.
   Reconciliation hell. Block until the void flow is built.
