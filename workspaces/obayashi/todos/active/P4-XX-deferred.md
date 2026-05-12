# P4-XX — Explicitly deferred

This file documents items intentionally NOT being actioned in the
P4 audit-followup wave. Each has an owner-locked decision attached.

Listed here so they don't get forgotten — and so the next session's
red-team doesn't surface them again as "missing".

---

## P4-XX-1 — HTTPS + custom domain (procurement)

- **Source:** `04-validate/07-buyer-audit-2026-05-08.md` P1.
- **Status:** DEFERRED — waiting on owner to procure a domain.
- **Why deferred:** procurement, not engineering. Caddyfile already
  in `deploy/` is configured to auto-provision Let's Encrypt — once
  a domain points at `136.110.51.61`, HTTPS comes up automatically.
- **Blocks:**
  - **P4-XX-2** (Xero production deploy) — Xero refuses
    non-localhost HTTP redirect URIs.
  - Enterprise procurement conversations (Obayashi IT will reject
    HTTP on day one).
- **Unblocks when:** owner registers a domain and updates DNS A
  record to `136.110.51.61`.
- **Then-do:** restart `arbor-caddy`, verify cert provisioning, add
  the HTTPS callback URL to Xero developer-portal app config.

---

## P4-XX-2 — Xero production deploy

- **Source:** `workspaces/xero-integration/.session-notes`,
  `04-validate/09-redteam-roles-2026-05-12.md` P0-A.
- **Status:** DEFERRED — owner-locked. Per current-session
  instruction: "xero cannot be done right now... leave it first".
- **Two distinct things this means:**
  1. **DON'T run the deferred Xero migrations on prod.**
     Consequence: `dataflow_crud.update("PayrollRun", ...)` continues
     to crash on prod because the model code references columns
     (`xero_journal_id`, `xero_exported_at`, `xero_force_counter`)
     that don't exist in the prod DB. This affects:
     - `approve_payroll_run` → 500
     - `mark_paid` → 500
     - `cancel` → 500
     - Any future Xero export → 500
  2. **DON'T flip on the Xero feature flag / set env vars.** Even
     if the migrations were run, the Xero feature would stay
     dormant unless `XERO_CLIENT_ID` / `XERO_CLIENT_SECRET` /
     `INTEGRATION_ENCRYPTION_KEY` / `XERO_OAUTH_REDIRECT_BASE_URL`
     are set in `.env.prod`.
- **Mitigation while deferred:** the live site's payroll Approve /
  Mark Paid / Cancel buttons are currently broken on prod. If/when
  the user wants those working again, three options exist
  (documented in earlier conversation):
  - **A.** Run the schema migrations anyway (additive, Xero stays
    off). 10 min.
  - **B.** Revert the Xero model fields from `PayrollRun`
    (rollback of M0..M4 model alignment).
  - **C.** Conditional field exclusion in DataFlow UPDATE.
- **Unblocks when:** owner says "ok ship Xero". At that point,
  follow `deploy/xero-deployment-runbook.md` — 4 env vars + 5
  migrations + restart.
- **Scope on unblock:** every Xero item already coded under M0..M4
  becomes immediately live. Plus the Xero roadmap items from the
  prior conversation (auto-export, alerts, reconciliation,
  tracking categories) can start ticket-ising.

---

## P4-XX-3 — Multi-currency + multi-entity (group structure)

- **Source:** Xero roadmap §11 (prior conversation).
- **Status:** DEFERRED — strategic, not blocking any current
  customer.
- **Why deferred:** SGD-only payroll is sufficient for SG-only SMEs.
  Multi-currency is real architectural work (functional vs
  presentation currency, FX rate sourcing, multi-tenant Xero
  connection per legal entity).
- **Unblocks when:** first prospect explicitly asks for it (signal:
  enterprise prospect with subsidiaries in JP / US / AU).

---

## P4-XX-4 — QBO + Zoho + MYOB + Tally adapters

- **Source:** Xero roadmap §6 + §14 (prior conversation).
- **Status:** DEFERRED — wait for customer demand.
- **Why deferred:** patterns are codified in
  `.claude/skills/project/third-party-integration-patterns.md` —
  each is a ~1-2 week build when triggered. Don't pre-build.
- **Unblocks when:**
  - QBO — first US / AU pre-Xero prospect asks
  - Zoho — first SG Zoho-bookkeeping SME prospect asks
  - Tally — first SG firm with Indian back-office asks
  - MYOB — first AU prospect asks

---

## P4-XX-5 — Xero Payroll API direct integration

- **Source:** Xero roadmap §12.
- **Status:** DEFERRED — wait for customer demand.
- **Why deferred:** current Xero integration pushes a GL summary
  journal — sufficient for the 90% of Xero-accounting customers
  who don't use Xero Payroll. Direct Payroll-API integration is
  several months of work and only valuable for prospects who
  already run payroll in Xero (smaller segment).
- **Unblocks when:** 3+ named prospects request it.

---

## Status legend

- **DEFERRED** — explicitly chosen not to action; documented reason.
- Once a deferred item unblocks, move it from this file to a new
  `P4-X-*-active.md` and update `000-master.md`.
