# Xero Integration — Outstanding Work Index

Phase 1 (real OAuth + persisted tokens + audit log + idempotency +
void-on-force) shipped in commits `2ec4461` and `2d3d1f3`. The work
below is everything **still outstanding** for production-readiness,
organized by milestone.

Each milestone file lists tasks with `Problem`, `Tasks`,
`Acceptance`, and the affected `Files`. Read them top-to-bottom in
that file; cross-milestone you can pick a different sequence based
on customer demand.

---

## Status quo (already shipped)

| Surface                                                             | State   |
| ------------------------------------------------------------------- | ------- |
| Backend: persisted IntegrationToken table                           | shipped |
| Backend: real /integrations/xero/oauth/start + /oauth/callback      | shipped |
| Backend: HMAC-signed state, 10-min TTL                              | shipped |
| Backend: XeroExportLog audit table + writes on every attempt        | shipped |
| Backend: Idempotency-Key on POST ManualJournals                     | shipped |
| Backend: void_journal adapter method + force-re-export voids prior  | shipped |
| Backend: granular accounting.manualjournals scope                   | shipped |
| Backend: refresh callback registered at adapter init                | shipped |
| Tests: 37 green (22 unit + 12 integration mocked + 3 e2e real Xero) | shipped |

---

## Milestones

### M0 — Pre-launch BLOCKERS

**File:** [M0-blockers.md](M0-blockers.md). Six items. Don't ship
to a paying customer without these.

| ID     | Title                                        | Why blocker                                                        |
| ------ | -------------------------------------------- | ------------------------------------------------------------------ |
| M0-T01 | Org picker in OAuth callback                 | Multi-org users get journals in wrong tenant — financial data leak |
| M0-T02 | Concurrent-export TOCTOU race                | Double-click → silent duplicate journals                           |
| M0-T03 | SG GST-correct TaxType (BASEXCLUDED)         | Customer's IRAS GST F5 wrong if not set                            |
| M0-T04 | JournalDate uses pay_date (not utc fallback) | Edge-of-month exports post to wrong period                         |
| M0-T05 | Frontend disable Export while pending        | Double-click safety                                                |
| M0-T06 | E2E coverage for failure modes               | 3 happy-path tests aren't enough for prod                          |

### M1 — Finish-the-launch

**File:** [M1-finish-launch.md](M1-finish-launch.md). Ten items.
Closes the loop: deployment, frontend wiring, refresh expiry, PDPA.

| ID     | Title                                                   |
| ------ | ------------------------------------------------------- |
| M1-T01 | User actions: Xero partner program + production secrets |
| M1-T02 | Frontend: wire "Connect Xero" button to real OAuth      |
| M1-T03 | Refresh-token expiry: re-auth UX                        |
| M1-T04 | Refresh-keepalive cron                                  |
| M1-T05 | CoA cache invalidation on archive/rename                |
| M1-T06 | Archived-account mapping banner                         |
| M1-T07 | PDPA-compliant disconnect (hard-delete + Xero revoke)   |
| M1-T08 | Production deployment runbook                           |
| M1-T09 | Xero-side disconnection detection                       |
| M1-T10 | Audit log retention policy                              |

### M2 — Day-2 robustness

**File:** [M2-day2-robustness.md](M2-day2-robustness.md). Twelve
items. Failure modes that won't show on day 1 but will hit within
30 days of real usage.

| ID     | Title                                                |
| ------ | ---------------------------------------------------- |
| M2-T01 | Void / undo flow (UI + endpoint)                     |
| M2-T02 | Settings → Integrations → Xero mapping page          |
| M2-T03 | Decimal arithmetic in journal builder                |
| M2-T04 | Per-Xero-org rate limiting                           |
| M2-T05 | bonus_total derived from PayslipItem records         |
| M2-T06 | Disconnect button + 401 auto-disconnect (UX confirm) |
| M2-T07 | Last-export status badge on run detail               |
| M2-T08 | Scope-mismatch detection + reconnect prompt          |
| M2-T09 | Account-code typeahead in mapping UI                 |
| M2-T10 | Reversal date semantics for void_journal             |
| M2-T11 | Surface X-Rate-Limit warnings before 429             |
| M2-T12 | Cross-currency support (gated, customer-pull)        |

### M3 — Polish + ops

**File:** [M3-polish-ops.md](M3-polish-ops.md). Seven items.
Force-multipliers when something goes wrong.

| ID     | Title                                                           |
| ------ | --------------------------------------------------------------- |
| M3-T01 | Structured logging for Xero events                              |
| M3-T02 | Operational alerting                                            |
| M3-T03 | Mapping change history                                          |
| M3-T04 | Bulk-export historical runs                                     |
| M3-T05 | "Test Xero connection" button                                   |
| M3-T06 | Per-route telemetry on the export modal                         |
| M3-T07 | Apply same hardening to QuickBooks + Zoho (separate workstream) |

### M4 — Docs + listings

**File:** [M4-docs-listings.md](M4-docs-listings.md). Four items.
Sales/support multipliers.

| ID     | Title                             |
| ------ | --------------------------------- |
| M4-T01 | Customer-facing user guide        |
| M4-T02 | Internal support runbook          |
| M4-T03 | Xero App Marketplace listing prep |
| M4-T04 | Privacy policy + ToS updates      |

---

## Recommended order

1. **M1-T01** (Jared submits partner-program + sets prod secrets) — calendar gate
2. **M0-T01..T06** (BLOCKERS — code work, ~1-2 days)
3. **M1-T02** (frontend Connect button — half a day, end-to-end smoke)
4. **M1-T05, M1-T06** (CoA cache + archive banner — paired)
5. **M1-T07, M1-T09** (disconnect + 401 detection — paired)
6. **M1-T03, M1-T04** (refresh expiry — paired)
7. **M1-T08** (deployment runbook + dry run)
8. **M1-T10** (retention policy doc)
9. **M2-T01..T12** in any reasonable order; M2-T02 (mapping page)
   unblocks several others.
10. **M3** as backlog when M2 ships.
11. **M4** alongside M2 — docs catch up to features.

---

## Total scope

- M0 BLOCKERS: 6 items, ~1-2 days
- M1 finish-launch: 10 items, ~3-4 days (some Jared-only)
- M2 day-2: 12 items, ~4-5 days
- M3 polish/ops: 7 items, ~3-4 days
- M4 docs/listings: 4 items, ~1-2 days

**Critical path to first paying customer: M1-T01 (calendar) +
M0 (code) + M1-T02 + M1-T07 + M1-T08.** Everything else can ship
incrementally post-launch with minimal customer impact.
