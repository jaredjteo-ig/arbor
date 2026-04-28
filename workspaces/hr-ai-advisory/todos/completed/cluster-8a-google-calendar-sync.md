# T-R055 — Google Calendar Sync for Recruitment Interviews

Status: complete.

## What shipped

End-to-end Google Calendar sync for `InterviewSchedule` rows: scheduling an
interview in Arbor adds a Google Calendar event for the interviewer + candidate;
edits and cancellations propagate; Google webhooks flow back into Arbor.

### Files added

- `src/hr_advisory/integrations/google_calendar/__init__.py`
- `src/hr_advisory/integrations/google_calendar/oauth.py`
  - `get_authorization_url`, `exchange_code`, `get_credentials`, `disconnect`
  - Signed `state` (HMAC-SHA256 over `JWT_SECRET_KEY`) — prevents cross-company
    OAuth callback hijack. 15-minute TTL.
- `src/hr_advisory/integrations/google_calendar/sync.py`
  - `build_event_body`, `create_event`, `update_event`, `delete_event`,
    `fetch_event`, `watch_events`. Best-effort: every Google call is wrapped
    in try/except + logger.warning so a Calendar outage cannot break Arbor.
- `src/hr_advisory/models/google_calendar.py` — new `GoogleCalendarConnection`
  DataFlow model (one row per company, holds tokens + webhook channel).
- `src/hr_advisory/api/routers/integrations_calendar.py` — five endpoints
  under `/integrations/google-calendar/`.
- `tests/unit/test_google_calendar_sync.py` — 16 unit tests (all green).

### Files modified

- `pyproject.toml` — added `google-api-python-client>=2.0.0`,
  `google-auth-oauthlib>=1.0.0`, `google-auth>=2.0.0`.
- `src/hr_advisory/models/__init__.py` — registered `GoogleCalendarConnection`.
- `src/hr_advisory/models/company_user.py` — added `google_event_id: str = ""`
  - index to `InterviewSchedule`.
- `src/hr_advisory/api/routers/__init__.py` and
  `src/hr_advisory/api/platform.py` — registered the new router under
  `/integrations/google-calendar`.
- `src/hr_advisory/api/routers/recruitment.py` — `schedule_interview` calls
  `sync.create_event` after persisting the row and stores the resulting
  `google_event_id` back on the `InterviewSchedule`. `update_interview` either
  patches the event or, if `status == "cancelled"`, deletes it. Both calls are
  wrapped in try/except so Calendar failures never break the interview flow.
- `apps/web/src/services/api/integrations.ts` — new
  `googleCalendarAuthUrl/Status/Disconnect` methods.
- `apps/web/src/app/(dashboard)/recruitment/settings/page.tsx` — new
  "Google Calendar (beta)" card with connected/disconnected pill, Connect
  (opens auth URL in a new tab + listens for `postMessage` to refresh) and
  Disconnect buttons.

### Endpoints

| Method | Path                                       | Purpose                                                 |
| ------ | ------------------------------------------ | ------------------------------------------------------- |
| GET    | `/integrations/google-calendar/auth-url`   | Returns OAuth URL + signed state                        |
| GET    | `/integrations/google-calendar/callback`   | Verifies state, exchanges code, registers webhook       |
| GET    | `/integrations/google-calendar/status`     | `{connected, expires_at, last_synced_at, scope}`        |
| POST   | `/integrations/google-calendar/disconnect` | Revokes + deletes the row                               |
| POST   | `/integrations/google-calendar/webhook`    | Receives Google push notifications (channel-token auth) |

All admin endpoints use `require_role("owner", "hr_manager")` and
`check_rate_limit`. The webhook is authenticated via the channel token we
generated when subscribing (compared with `secrets.compare_digest`).

## Tests

`tests/unit/test_google_calendar_sync.py` — 16 tests, all passing in 1.21s:

- Signed state — round-trip, tampered signature rejected, expired state
  rejected.
- `oauth.exchange_code` — verifies state, persists tokens; rejects malformed
  state.
- `sync.build_event_body` — builds the right summary/start/end/attendees from
  an interview dict (including handling JSON-encoded interviewer lists);
  forwards `status="cancelled"` to Google.
- `sync.create_event/update_event/delete_event` — calls Google with the right
  args, returns `None`/`False` when not connected, swallows Google API errors.
- `schedule_interview` — invokes `sync.create_event` with the right payload
  (candidate email, job title, scheduled time).
- Webhook — rejects bad channel tokens with 401; on a good token, fetches the
  event and patches the matching `InterviewSchedule` row's
  location/scheduled_at/status.

## OAuth setup the user must complete

The integration is wired but inert until the following one-time setup is done
in the user's Google Cloud project. None of these steps require code changes.

1. **Create / select a Google Cloud project**
   `https://console.cloud.google.com/projectcreate`
2. **Enable the Google Calendar API**
   APIs & Services → Library → search "Google Calendar API" → Enable.
3. **Configure the OAuth consent screen**
   APIs & Services → OAuth consent screen
   - User type: External (or Internal if Workspace).
   - App name: "Arbor HR".
   - Scopes: add `https://www.googleapis.com/auth/calendar.events`.
   - Authorised domains: include the domain that hosts Arbor's API (e.g.
     `arbor.example.com`).
4. **Create the OAuth client credentials**
   APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Web application.
   - Authorised redirect URIs:
     - `http://localhost:8001/integrations/google-calendar/callback` (dev)
     - `https://<arbor-host>/integrations/google-calendar/callback` (prod)
       Copy the resulting client ID and client secret.
5. **Set environment variables on the API server**

   ```bash
   export GOOGLE_OAUTH_CLIENT_ID="…apps.googleusercontent.com"
   export GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-…"
   # Public URL of the *API server* — must match the redirect URI you registered.
   export GOOGLE_OAUTH_REDIRECT_URI="https://<arbor-host>/integrations/google-calendar/callback"
   # Public base URL of the API server (used by the webhook subscription).
   export ARBOR_API_URL="https://<arbor-host>"
   # Public base URL of the web app (used in event description back-links).
   export ARBOR_PUBLIC_URL="https://<arbor-web-host>"
   # Optional — defaults to "primary" (the connecting user's main calendar).
   # export GOOGLE_CALENDAR_ID="primary"
   ```

   Add these to `.env` (local), `compose.yaml` (Docker), or the deployment
   target's secret manager. Do **not** commit secrets.

6. **Webhook prerequisite (production only)**
   Google Calendar push notifications require an HTTPS endpoint with a valid
   TLS certificate on a domain you have verified in Google Search Console
   _for the same Cloud project_. Without verification, `events.watch` silently
   returns 401 — connection still works, but updates from the Google side
   won't sync back to Arbor (interview-side writes still flow out).

7. **Run the DB migration**
   The new `GoogleCalendarConnection` model and the new `google_event_id`
   column on `InterviewSchedule` need to be migrated. Use the project's
   standard migration flow (`alembic upgrade head` or DataFlow auto-migrate
   on app start, depending on environment).

## Notes / scope I deliberately did not stray into

- I left `apps/web/src/app/(dashboard)/onboarding/**` untouched (per brief).
- The webhook handler ignores notifications whose channel id we don't know —
  returning 200 so Google stops retrying — and flags the row's
  `last_synced_at` so the next reconciliation can pick up changes.
- `update_interview` clears `google_event_id` once it deletes the event, so a
  later "un-cancel" reschedule will create a fresh event instead of patching a
  tombstone.
