# Xero Integration — Deployment Runbook

End-to-end procedure for deploying the Xero payroll-export feature
to production at 136.110.51.61. Read top-to-bottom; do not skip
sections. The whole runbook should take ~20 minutes the first time;
subsequent deploys (after migrations are applied once) are ~5 minutes.

Cross-references:

- Code-side outstanding work: `workspaces/xero-integration/todos/active/`
- Retention policy: `workspaces/xero-integration/02-plans/02-data-retention.md`

---

## 0. Pre-flight checklist

Before you touch the prod host, confirm:

1. The branch you're deploying contains M0 + M1 commits. Quick check:
   ```
   git log --oneline | head -5
   ```
   You should see `feat(xero): close M0 pre-launch blockers …` and
   the M1 commits.
2. Local tests are green for the Xero suite:
   ```
   pytest tests/unit/test_xero_*.py \
          tests/integration/test_xero_*.py \
          tests/regression/test_xero_*.py \
          --timeout=60 -q
   ```
3. You have a Xero **production** developer app set up (separate
   from the dev sandbox app you used for the e2e test). The dev app
   can stay for ongoing local testing.
4. You have the production app's Client ID and Client Secret to hand.
5. The production redirect URI is registered in the Xero app:
   `<XERO_OAUTH_REDIRECT_BASE_URL>/integrations/xero/oauth/callback`
   (e.g. `http://136.110.51.61/integrations/xero/oauth/callback`).

---

## 1. Prepare production environment variables

Generate a production Fernet key (do this on your laptop, paste into
the prod env once — never commit):

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then add four variables to the production environment. **Strongly
prefer GCP Secret Manager** over baking into `docker-compose.yml`,
but if you're using compose env-files, ensure the file is gitignored
and chmod 600.

```
INTEGRATION_ENCRYPTION_KEY=<the Fernet key you just generated>
XERO_CLIENT_ID=<production app client id>
XERO_CLIENT_SECRET=<production app client secret>
XERO_OAUTH_REDIRECT_BASE_URL=http://136.110.51.61
```

**Important about INTEGRATION_ENCRYPTION_KEY:** once a customer has
connected, this key encrypts their tokens at rest. Rotating it
**will invalidate every stored token** — every customer would need
to reconnect. Treat it as a stable long-term secret. Document its
location in your secret-management system.

---

## 2. SSH into production and pull the new code

```
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61
cd /path/to/arbor
git fetch origin
git checkout main && git pull
```

---

## 3. Apply database migrations

All four migrations are idempotent — safe to re-run on a host that
already has them. Run in order:

```
python scripts/migrate_xero_payroll_export.py
python scripts/migrate_integration_tokens.py
python scripts/migrate_xero_export_log.py
python scripts/migrate_xero_force_counter.py
```

Expected output for a fresh deploy:

- `migrate_xero_payroll_export.py`: adds `xero_journal_id` and
  `xero_exported_at` to `payroll_runs`, creates
  `xero_account_mappings`.
- `migrate_integration_tokens.py`: creates `integration_tokens`.
- `migrate_xero_export_log.py`: creates `xero_export_logs`.
- `migrate_xero_force_counter.py`: adds `xero_force_counter` to
  `payroll_runs`.

If any of these say "already exists — skipping", you've already
applied them — that's fine.

---

## 4. Restart the backend with the new code + env

```
docker compose -f deploy/docker-compose.prod.yml up -d --build api
```

Wait ~30 seconds for the container to come up.

---

## 5. Smoke tests (do not skip)

### 5a. Backend health

```
curl -s http://136.110.51.61/health
```

Should return `{"status":"healthy", ...}`. If not, check
`docker logs <api-container>` for startup errors.

### 5b. Xero status endpoint

Sign into the live web app at http://136.110.51.61, get a JWT for
an owner role, then:

```
TOKEN=<your jwt>
curl -s -H "Authorization: Bearer $TOKEN" \
     http://136.110.51.61/payroll/xero/status
```

Should return `{"connected": false, "mapping_present": false,
"mapping_complete": false}` for any company that hasn't connected.

### 5c. OAuth start endpoint

```
curl -s -H "Authorization: Bearer $TOKEN" \
     http://136.110.51.61/integrations/xero/oauth/start
```

Should return `{"redirect_url": "https://login.xero.com/identity/...
&client_id=<XERO_CLIENT_ID>&redirect_uri=http://136.110.51.61/...&state=..."}`.

If `redirect_url` is empty or you get a 500 with "XERO_CLIENT_ID
not configured", the env vars from step 1 didn't propagate — check
the container env: `docker exec <api> env | grep XERO`.

### 5d. End-to-end (manual)

1. In a browser, sign in as an owner-role user.
2. Settings → Integrations → click **Connect Xero**.
3. You should land on Xero's consent screen. Authorize.
4. You should land back at `/settings/integrations?xero=connected`
   with a green "Xero connected" toast.
5. If you authorized multiple Xero orgs, you'll first see the
   `/settings/integrations/xero/pick-org` page — pick one.
6. Approve a payroll run, click **Export to Xero**, save the
   auto-matched mapping, click **Post to Xero**.
7. Verify in your Xero org: Reports → Journal Report → look for the
   new ManualJournal with the narration "Payroll <period>".

---

## 6. Set up the recurring jobs

Two cron entries to add to your prod crontab:

```
# Xero: keep refresh tokens warm (daily at 02:00 SGT)
0 2 * * * cd /path/to/arbor && python scripts/keep_xero_tokens_warm.py >> /var/log/xero-keepalive.log 2>&1

# Xero: PDPA-redact disconnected token material (monthly, 1st at 03:00 SGT)
0 3 1 * * cd /path/to/arbor && python scripts/redact_old_xero_tokens.py >> /var/log/xero-redact.log 2>&1
```

Verify with `crontab -l`. Watch the first run of the keepalive job
the day after deploy: `tail -100 /var/log/xero-keepalive.log`.

---

## 7. Rollback plan

If something goes wrong post-deploy and a customer has already
connected:

**Code rollback (safe — tokens persist):**

```
git checkout <previous commit>
docker compose -f deploy/docker-compose.prod.yml up -d --build api
```

The migrations are additive (no DROPs), so older code will still
work — it just won't reference the new columns/tables. Customer
connections stay live.

**Token rollback (only if INTEGRATION_ENCRYPTION_KEY changed):**

If you accidentally rotated `INTEGRATION_ENCRYPTION_KEY`, every
stored token becomes un-decryptable. The fix:

1. Restore the original key.
2. If irretrievable, customers must reconnect — there's no recovery
   path. Communicate proactively rather than letting them hit a
   silent failure.

**Migration rollback (last resort):**

The migrations don't include DOWN scripts. If you need to drop the
new tables/columns:

```sql
DROP TABLE IF EXISTS xero_export_logs CASCADE;
DROP TABLE IF EXISTS integration_tokens CASCADE;
DROP TABLE IF EXISTS xero_account_mappings CASCADE;
ALTER TABLE payroll_runs
  DROP COLUMN IF EXISTS xero_journal_id,
  DROP COLUMN IF EXISTS xero_exported_at,
  DROP COLUMN IF EXISTS xero_force_counter;
```

Only do this if the feature is being permanently removed — running
this on a live system loses all customer Xero connections and audit
history.

---

## 7b. Alerting thresholds (M3-T02)

Pipe the structured `xero event=...` log lines (M3-T01) into your
alerting tool (Slack, PagerDuty, whatever the project uses) with
the following thresholds. The `xero_log_event` helper logs at
WARNING when `outcome=failure` so a simple severity filter is
enough.

| Signal                                            | Threshold        | Action                                                      |
| ------------------------------------------------- | ---------------- | ----------------------------------------------------------- |
| `event=refresh_invalid_grant` count               | any              | Slack: customer must reconnect — do not page.               |
| `event=api_401_auto_disconnect` count             | any              | Slack: same as above.                                       |
| `event=post_payroll_journal outcome=failure` rate | > 10% per hour   | Page on-call — likely Xero outage or scope regression.      |
| `event=*` HTTP 429 (rate-limit)                   | any in last hour | Slack: a customer is hitting Xero's per-org cap.            |
| `event=test_connection outcome=failure` rate      | > 50% in 5 min   | Page — Xero side likely down.                               |
| `event=export_run` zero successes in 24h          | n/a              | Daily check, not paging — confirms the integration is live. |

The `GET /payroll/xero/operations-summary` endpoint exposes a
rolling-24h breakdown per company (`by_status`, `success_rate`,
`last_failure`). Wire your dashboard to this.

---

## 8. Post-deploy monitoring (first 24h)

Tail logs and grep for Xero-specific structured events:

```
docker logs -f <api-container> 2>&1 | grep -E "xero|Xero"
```

Specifically watch for:

- `Xero rate limit exceeded` — increase awareness of customer usage
  patterns.
- `Refresh token returned invalid_grant` — if any, the keepalive
  cron is the fix; verify it ran.
- `XeroAccountInvalid` — customer's mapping has stale codes; their
  next export attempt will surface the new 409 error with
  `mapping_url`.
- 502 from `post_payroll_journal` paths — investigate Xero-side
  errors via the `XeroExportLog` row's `error_message` field.

After 24 hours of clean logs and at least one successful customer
export, the deploy is considered stable.

---

## 9. Future deploys

Once the migrations and env vars are in place, future deploys are:

```
ssh ... → cd /path/to/arbor → git pull → docker compose up -d --build api
```

Re-run migrations only if a new `scripts/migrate_xero_*.py` lands
in the new commit.
