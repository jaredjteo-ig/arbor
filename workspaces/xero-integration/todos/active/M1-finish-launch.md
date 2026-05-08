# M1 — Finish-The-Launch

Closes the loop on Phase 1: actual production deployment, frontend
wiring of the Connect button, refresh-token resilience, PDPA
compliance for token handling, and the operational gaps that turn
the integration from "works on day 1" into "still works after
month-end and after a customer disconnects."

---

## M1-T01 — User actions: Xero partner program + production secrets

**Owner: Jared, not code.** These are wall-clock blockers, not
implementation work.

**Tasks:**

1. Submit Xero partner-program app review at
   https://developer.xero.com/partner/sign-up. Include:
   - App name, description, support URL, privacy policy URL.
   - Production redirect URI.
   - Logo (256×256 PNG).
   - Demo video or screenshot of the export flow.
     Approval is calendar-gated (1-3 weeks). Until approved you're
     capped at 25 connections and OAuth shows an "unverified" warning.
2. Generate and set production env vars on the GCP host (136.110.51.61):
   ```
   INTEGRATION_ENCRYPTION_KEY=<Fernet.generate_key().decode()>
   XERO_CLIENT_ID=<production app credentials>
   XERO_CLIENT_SECRET=<production app credentials>
   XERO_OAUTH_REDIRECT_BASE_URL=http://136.110.51.61
       (or final domain — must match Xero app whitelist exactly)
   ```
   Add to `docker-compose.yml` env section, not `.env` directly.
3. Register `<XERO_OAUTH_REDIRECT_BASE_URL>/integrations/xero/oauth/callback`
   in the Xero app's Configuration → Redirect URIs list.
4. Run migrations on prod DB:
   ```
   python scripts/migrate_xero_payroll_export.py
   python scripts/migrate_integration_tokens.py
   python scripts/migrate_xero_export_log.py
   python scripts/migrate_xero_force_counter.py
   ```
   All four are idempotent — safe to re-run.

**Acceptance:** OAuth round-trip completes against prod from a real
browser at the deployed URL.

---

## M1-T02 — Frontend: wire "Connect Xero" button to real OAuth

**Problem:** Settings → Integrations "Connect" button still hits the
stub `/{provider}/connect` endpoint at `integrations.py:1095`. The
new endpoint is `/integrations/xero/oauth/start`. Currently the
real button is dead.

**Tasks:**

1. Add `xeroOauthStart()` to `apps/web/src/services/api/integrations.ts`
   that calls GET `/integrations/xero/oauth/start` and returns
   `{redirect_url}`.
2. In `apps/web/src/app/(dashboard)/settings/integrations/page.tsx`,
   when the user clicks "Connect" on the Xero card, call the new
   API method and `window.location = response.redirect_url`.
3. Detect query params on settings page mount:
   - `?xero=connected` → toast.success("Connected to Xero — <org name>"),
     refetch integration status.
   - `?xero_error=<reason>` → toast.error with translated message.
4. After successful connect, the card should show: "Connected to
   <org name> · <connected_at>" and a "Disconnect" button.
5. Test: click Connect → real-Xero round-trip → land back on settings
   with green badge and org name.

**Acceptance:** End-to-end manual test on the dev environment with
the user's own Xero Demo Company shows the full flow working from
the Settings page.

**Files:** `apps/web/src/services/api/integrations.ts`,
`apps/web/src/app/(dashboard)/settings/integrations/page.tsx`,
`apps/web/src/hooks/api/useIntegrations.ts` (extend with
useXeroOauthStart mutation).

---

## M1-T03 — Refresh-token expiry: re-auth UX

**Problem:** Xero refresh tokens expire after 60 days of disuse.
After day 60, every API call returns 400 `invalid_grant`. The
current code logs and returns None, surfacing as a generic 401 to
the user. They have no idea they need to reconnect.

**Tasks:**

1. In `XeroAdapter._refresh_token`, detect `invalid_grant`
   response and:
   - Mark the IntegrationToken row's `disconnected_at` (auto-disconnect).
   - Raise a typed exception `XeroReauthRequired` with a user-facing
     message.
2. The export endpoint catches `XeroReauthRequired` and returns 401
   with `{detail, action: "reconnect", reconnect_url:
"/settings/integrations?reconnect=xero"}`.
3. Frontend modal renders a "Reconnect Xero" button when the export
   endpoint returns this error, deep-linking back to Connect.
4. Test: stub `/identity/connect/token` to return `invalid_grant`,
   call export, verify 401 with reconnect_url.

**Acceptance:** A customer whose refresh token expired sees "Your
Xero connection expired — Reconnect" in the export modal, not a
generic 401.

**Files:** `src/hr_advisory/mcp_servers/adapters/xero.py`,
`src/hr_advisory/api/routers/payroll.py`,
`apps/web/src/components/payroll/XeroExportModal.tsx`,
`tests/integration/test_xero_payroll_export_api.py`.

---

## M1-T04 — Refresh-keepalive cron

**Problem:** Customers who run payroll once a month have their
refresh token go idle for 30 days at a time. Two missed months and
they're at the 60-day cliff. Most accounting integrations preempt
this with a cron that pings each connection every 7-14 days.

**Tasks:**

1. New script `scripts/keep_xero_tokens_warm.py`:
   - Read all `IntegrationToken` rows where `provider='xero'`,
     `disconnected_at=''`, `expires_at` within next 7 days.
   - For each: call `XeroAdapter._refresh_token` to rotate the
     access token (which extends the refresh token's idle window).
   - Log success/failure counts.
2. Add to deployment cron (daily at 02:00 SGT). Document in
   `deploy/deployment-config.md`.
3. On failure (not invalid_grant), retry next day; on
   invalid_grant, mark disconnected and email the customer.
4. Test: integration test that creates a near-expiry token, runs
   the script, asserts the row's `expires_at` extended.

**Acceptance:** Tokens within 7 days of expiry get refreshed
automatically. Customer never hits the 60-day cliff during normal
usage.

**Files:** `scripts/keep_xero_tokens_warm.py` (new),
`deploy/deployment-config.md`,
`tests/integration/test_keep_xero_tokens_warm.py` (new).

---

## M1-T05 — CoA cache invalidation on archive/rename detection

**Problem:** `_coa_cache` has 24h TTL with no invalidation. A
customer renames a Xero account at 09:00, exports payroll at 09:30,
and our cache hands back the stale code. Xero rejects with 400
account-not-found. Customer is confused; the cache won't refresh
for another 23.5h.

**Tasks:**

1. On any 400 response from `post_payroll_journal` whose body
   contains `"is not a valid code for this document"` or
   `"AccountID could not be found"`, invalidate the CoA cache for
   that tenant and surface a typed error.
2. The export endpoint catches the typed error and returns 409 with
   `{detail: "Account code <X> no longer exists in your Xero. Update
your account mapping.", offending_code: "<X>",
mapping_url: "/settings/integrations/xero"}`.
3. Test: mock Xero to return the validation error, assert cache
   invalidated, response payload contains offending_code and
   mapping_url.

**Acceptance:** Renaming an account in Xero between exports surfaces
a clear "update your mapping" message linked to the mapping page,
not a generic 400.

**Files:** `src/hr_advisory/mcp_servers/adapters/xero.py`,
`src/hr_advisory/api/routers/payroll.py`.

---

## M1-T06 — Archived-account mapping banner

**Problem:** Xero accounts can be archived (Status=ARCHIVED). Our
auto-matcher filters by ACTIVE but mapped codes don't get
re-validated when the chart changes. A code that was active at
mapping time may now be archived; export will fail at POST time
rather than warning beforehand.

**Tasks:**

1. New endpoint `GET /payroll/xero/mapping-health` that:
   - Loads the saved XeroAccountMapping.
   - Fetches the current chart of accounts.
   - For each mapped code, checks Status. Returns
     `{archived: ["482", "825"], renamed: [], missing: []}`.
2. Settings → Integrations → Xero mapping page (M2-T02) shows a
   warning banner when this endpoint returns non-empty arrays.
3. The export modal shows the same banner + blocks export if any
   mapped code is archived/missing.
4. Test: mock CoA where one mapped code is ARCHIVED, hit the health
   endpoint, assert it appears in `archived`.

**Acceptance:** Mapping health is visible to the customer before
they hit export. They get a chance to fix mappings instead of
discovering it via a failed export.

**Files:** `src/hr_advisory/api/routers/payroll.py`,
`apps/web/src/components/payroll/XeroExportModal.tsx`,
`apps/web/src/app/(dashboard)/settings/integrations/xero/page.tsx` (new — see M2-T02).

---

## M1-T07 — PDPA-compliant disconnect (hard-delete + Xero revoke)

**Problem:** OAuth tokens are personal data under SG PDPA. On
disconnect we currently soft-delete (set `disconnected_at`). PDPA
retention principles require deletion when the purpose has ended.
Also: we don't revoke at Xero's side, so the customer's Xero org
list still shows our app even after they "disconnect" in Arbor.

**Tasks:**

1. New endpoint `POST /integrations/xero/disconnect`:
   - Calls Xero `DELETE /connections/{xero_tenant_id}` to revoke at
     source.
   - Hard-deletes the IntegrationToken row (DELETE FROM
     integration_tokens WHERE tenant_id=$1 AND provider='xero').
   - Drops in-memory cache entry.
2. Disconnect button on Settings → Integrations → Xero card calls
   this endpoint.
3. Cascade: company offboarding flow (when a Company row is deleted)
   must also disconnect all integrations. Add to existing offboarding
   path.
4. Audit log: write a XeroExportLog-style row capturing the
   disconnect event (provider, tenant_id, actor_id, when) — even
   though we're hard-deleting the token, the event of disconnection
   is itself audit-worthy.
5. Test: connect, disconnect, verify (a) IntegrationToken row gone,
   (b) Xero `/connections` no longer includes our app.

**Acceptance:** Disconnect from Arbor's UI removes the connection on
both sides — Arbor's DB and Xero's authorized-apps list.

**Files:** `src/hr_advisory/api/routers/integrations.py`,
`src/hr_advisory/mcp_servers/adapters/xero.py` (new
`disconnect_at_source` method),
`src/hr_advisory/mcp_servers/auth/token_store.py` (new
`hard_delete` method),
`tests/integration/test_xero_disconnect.py` (new).

---

## M1-T08 — Production deployment runbook

**Tasks:**

1. Document in `deploy/xero-deployment-runbook.md`:
   - Prerequisites: M1-T01 user actions complete.
   - Migration order (the four scripts).
   - Smoke-test plan post-deploy (curl the `/integrations/xero/status`
     endpoint, attempt OAuth, verify token persists across restart).
   - Rollback plan: if migration partially fails, how to revert.
   - Monitoring checklist: tail logs for first 24h after deploy.
2. Add to `deploy/deployment-config.md` index.
3. Dry-run the runbook on the dev environment one full time before
   running on prod.

**Acceptance:** Another engineer (or future-you) can deploy Xero
end-to-end by reading the runbook, with no calls back to current-you.

**Files:** `deploy/xero-deployment-runbook.md` (new),
`deploy/deployment-config.md`.

---

## M1-T09 — Xero-side disconnection detection (webhook or 401)

**Problem:** A user revokes Arbor's access from inside their Xero
account (Settings → Connected apps → Disconnect). Our DB still
shows the connection as active. We only learn on the next API call
when Xero returns 401.

**Tasks:**

1. Subscribe to Xero's connection-removed webhook (if available —
   verify in Xero docs). Set up `/integrations/xero/webhook` endpoint
   with HMAC signature validation. Mark `disconnected_at` on receipt.
2. As a fallback (and for completeness), in `XeroAdapter._api_call`,
   when a 401 surfaces and refresh fails:
   - Mark the IntegrationToken row's `disconnected_at`.
   - Return `XeroReauthRequired` (already added in M1-T03) so the
     UX is consistent.
3. Settings → Integrations card detects `disconnected_at` set and
   shows "Connection lost — reconnect" rather than "Connected."
4. Test: stub Xero to return 401, attempt export, verify
   `disconnected_at` set and reconnect prompt shown.

**Acceptance:** Customer revoking from Xero side surfaces in the
Arbor UI within minutes (webhook) or on next export attempt (401
fallback) — never silently broken.

**Files:** `src/hr_advisory/api/routers/integrations.py`,
`src/hr_advisory/mcp_servers/adapters/xero.py`,
`tests/integration/test_xero_webhook.py` (new).

---

## M1-T10 — Audit log retention policy

**Problem:** XeroExportLog rows are append-only and never deleted.
Per SG IRAS requirements, payroll/accounting records must be kept
for 7 years (Income Tax Act). Per PDPA, retention beyond that
requires justification.

**Tasks:**

1. Document the retention policy in
   `workspaces/xero-integration/02-plans/02-data-retention.md`:
   - XeroExportLog: 7 years from `posted_at`.
   - IntegrationToken disconnected rows: redacted access/refresh
     tokens after 90 days, full delete after 7 years.
2. New script `scripts/redact_old_xero_tokens.py` runs monthly:
   - For IntegrationToken rows where `disconnected_at` > 90 days
     ago, set access_token_encrypted=" " and
     refresh_token_encrypted=" " (preserves audit row, deletes
     personal data).
3. Cross-reference with sg-employment-law-expert agent on the exact
   IRAS retention requirements.
4. Add to deploy cron schedule.

**Acceptance:** Documented retention policy in workspace; redaction
cron in place; legal-team-style approval traceable.

**Files:** `workspaces/xero-integration/02-plans/02-data-retention.md`
(new), `scripts/redact_old_xero_tokens.py` (new),
`deploy/deployment-config.md`.
