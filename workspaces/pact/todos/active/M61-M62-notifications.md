# M61-M62: Held-Action Pipeline — #1 Priority

**Milestone**: M61 (notification pipeline) + M62 (approval UX)
**Priority**: CRITICAL — identified as "make-or-break" in value proposition critique
**Scope**: both
**Estimated effort**: 4-5 days

Without this, the boss never learns about held actions unless they open the app.
The critique is explicit: "If held actions depend on the boss opening the app,
they will be ignored." This is the UX linchpin of the entire PACT vision.

---

### T413: Extend push_service.py with held-action notification types

**Scope**: backend
**Depends**: T401
**Files**:

- `src/hr_advisory/notifications/push_service.py` (modify)

**Description**: Add three new notification types to `NotificationType` enum:

```python
HELD_ACTION = "held_action"           # "Sarah Lim wants 3 days leave — your input needed"
DAILY_DIGEST = "daily_digest"         # "3 actions need your review today"
ESCALATION = "escalation"             # "Held action pending 48 hours — Sarah is still waiting"
AGENT_SUGGESTION = "agent_suggestion" # "The HR Agent has an idea that could save time"
```

Add `send_held_action_notification(held_action_id: int, company_id: int) -> bool`
that:

1. Loads the HeldAction from DataFlow
2. Loads the company owner's User record (or hr_manager if relevant)
3. Sends push notification with:
   - title: plain-language action display
   - body: action context + first option label
   - data: `{held_action_id, action_type, urgency}`
4. Returns True on success, False on failure (never raises)

Add `send_daily_digest(company_id: int) -> bool` that:

1. Counts pending HeldAction records for the company
2. If count > 0: sends "You have N items needing your review today"
3. If count == 0: skips (no notification)

Add `send_escalation(held_action_id: int) -> bool` that:

1. Increments `held_action.escalation_level`
2. Sends escalation notification: "Sarah's leave request has been waiting
   for 2 days. She needs an answer."

**Acceptance criteria**:

- [ ] Three new NotificationType values added
- [ ] `send_held_action_notification` sends FCM push in production, logs in dev
- [ ] `send_daily_digest` only sends when there are pending actions
- [ ] `send_escalation` increments escalation_level before sending
- [ ] All functions return bool (never raise)
- [ ] Unit tests with mocked FCM client

---

### T414: Held-action notification scheduler

**Scope**: backend
**Depends**: T413
**Files**:

- `src/hr_advisory/pact/notifications/__init__.py` (new package)
- `src/hr_advisory/pact/notifications/scheduler.py` (new file)

**Description**: Background task that drives the held-action notification
pipeline. Runs periodically (every 15 minutes via existing task queue or
APScheduler).

`process_held_action_notifications()`:

1. Find all `HeldAction` records with `status=pending` and `notify_at <= now()`
2. For each:
   - If `escalation_level == 0`: send initial notification (T413)
   - If `escalation_level == 1` and age > 48 hours: send escalation
   - If `escalation_level == 2` and age > 5 days: send final escalation
     with stronger language
   - If expired (`expires_at < now()`): auto-resolve as `expired`

`process_daily_digest(hour: int = 8)`:

1. At 08:00 SGT daily: send digest to each company with pending actions
2. Groups multiple held actions into one digest notification

`batch_vs_immediate_rules(held_action: HeldAction) -> str`:

- Returns `immediate` if `urgency == "urgent"` or `urgency == "deadline"`
- Returns `batched` if `urgency == "routine"`
- Batched actions are included in the daily digest, not sent immediately

Channel priority config per company (stored in Company model or a settings table):
`notification_channel_priority: JSON default ["push", "email", "whatsapp"]`

**Acceptance criteria**:

- [ ] `process_held_action_notifications` correctly escalates after 48h and 5d
- [ ] Daily digest runs at 08:00 SGT
- [ ] Urgent actions (payroll deadline, work pass expiry) sent immediately
- [ ] Routine actions (leave approval, small claim) batched in digest
- [ ] `expires_at` auto-resolution works
- [ ] Unit tests for each scheduling scenario
- [ ] Integration test: create held action, advance time, verify notifications sent

---

### T415: Email channel for held actions

**Scope**: backend
**Depends**: T413
**Files**:

- `src/hr_advisory/pact/notifications/email_channel.py` (new file)
- `src/hr_advisory/templates/email/held_action.html` (new file)
- `src/hr_advisory/templates/email/daily_digest.html` (new file)

**Description**: Email fallback when push notification is not delivered or
the user has no FCM token registered.

`send_held_action_email(held_action_id: int) -> bool`:

- Subject: "Action needed: {held_action.action_display}"
- Body: plain-language context, list of options as buttons linking to
  `GET /pact/held-actions/{id}/resolve?option={key}&token={email_token}`
  (one-click approval from email)
- Email token: single-use HMAC-signed token that pre-authenticates the action
  (same pattern as the invitation flow in the existing codebase)

`send_daily_digest_email(company_id: int, pending_count: int) -> bool`:

- Subject: "Arbor: {N} items need your review"
- Body: list of pending held actions with direct links

**Acceptance criteria**:

- [ ] Email HTML template renders correctly with all variables
- [ ] One-click approval link verifies HMAC token before executing resolution
- [ ] Email token is single-use (invalidated after use)
- [ ] Email sent when push notification FCM token is missing
- [ ] Unit tests for token generation and verification
- [ ] Integration test: receive email, click approve link, held action resolved

---

### T416: Held-action API endpoints

**Scope**: backend
**Depends**: T401, T414
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)

**Description**: REST endpoints for the held-action review flow.

Endpoints:

- `GET /api/pact/held-actions` — list all pending held actions for the company.
  Filter by `status`, `agent_role`, `urgency`. Owner and hr_manager.
- `GET /api/pact/held-actions/{id}` — get single held action with full context.
- `POST /api/pact/held-actions/{id}/resolve` — resolve a held action.
  Body: `{option: str, note: str nullable}`. Sets `status`, `resolution_option`,
  `resolution_note`, `resolved_by`, `resolved_at`. Creates PactAuditEvent.
- `GET /api/pact/held-actions/summary` — counts by status and urgency for
  dashboard badge display.

Validation: only the company owner or hr_manager can resolve held actions.
Only pending held actions can be resolved (not expired/auto_resolved).

**Acceptance criteria**:

- [ ] List endpoint returns held actions ordered by urgency then created_at
- [ ] Resolve endpoint validates option key is one of `held_action.action_options[*].key`
- [ ] PactAuditEvent created on each resolution
- [ ] Summary endpoint returns `{pending: N, urgent: N, expired: N}`
- [ ] Employees cannot access held actions (403)
- [ ] Integration tests for full resolve flow

---

### T417: WhatsApp channel for held actions

**Scope**: backend
**Depends**: T413
**Files**:

- `src/hr_advisory/pact/notifications/whatsapp_channel.py` (new file)

**Description**: Wire the existing WhatsApp MCP adapter to held actions.
The WhatsApp integration is identified as a critical channel (SG bosses live
on WhatsApp). The `arbor-communications` MCP server and WhatsApp adapter
already exist at `src/hr_advisory/mcp_servers/adapters/whatsapp.py` — this
task wires them to the notification pipeline.

`send_held_action_whatsapp(held_action_id: int, phone_number: str) -> bool`:

1. Format message:

   ```
   Arbor HR: {action_display}

   {action_context}

   Reply with the number to respond:
   1. {option_1_label}
   2. {option_2_label}
   3. {option_3_label}

   Or open the app: arbor.terrene.dev/held-actions/{id}
   ```

2. Send via the WhatsApp MCP adapter
3. Register an expected reply in a `WhatsAppReplyExpectation` table keyed by
   `{phone_number}:{held_action_id}` with 24-hour TTL

`handle_whatsapp_reply(phone_number: str, message_body: str) -> bool`:

1. Look up pending `WhatsAppReplyExpectation` for the phone number
2. Parse option number (1, 2, 3) from message body
3. Resolve the held action with the selected option
4. Reply: "Done. {option_label} for {action_display}."

`WhatsAppReplyExpectation` DataFlow model:

- `phone_number`, `held_action_id`, `option_map: JSON`, `expires_at`, `fulfilled: bool`

WhatsApp opt-in: only send if the company has `whatsapp_notifications_enabled=True`
and the user's phone number is on file (User.phone field).

**Acceptance criteria**:

- [ ] `send_held_action_whatsapp` formats message correctly with numbered options
- [ ] Reply "1" resolves the held action with option 1
- [ ] `WhatsAppReplyExpectation` expires after 24 hours
- [ ] Phone number not on file: skip WhatsApp, use email fallback
- [ ] `whatsapp_notifications_enabled` company setting checked first
- [ ] Unit tests for message formatting and reply parsing
- [ ] Integration test: send message, reply "1", verify held action resolved

---

### T418: Notification channel preferences API

**Scope**: backend
**Depends**: T413, T415, T417
**Files**:

- `src/hr_advisory/api/routers/pact.py` (extend)
- `src/hr_advisory/models/company_user.py` (extend Company model)

**Description**: Company-level and user-level notification channel settings.

Add to Company model:

- `notification_channel_priority: JSON default ["push", "email", "whatsapp"]`
- `whatsapp_notifications_enabled: Boolean default False`
- `digest_hour_sgt: Integer default 8` — hour of day for daily digest (0-23)

Endpoints:

- `GET /api/pact/notification-settings` — get current settings
- `PATCH /api/pact/notification-settings` — update settings. Owner only.

**Acceptance criteria**:

- [ ] Default channel priority is `["push", "email", "whatsapp"]`
- [ ] WhatsApp defaults to disabled (opt-in)
- [ ] Digest hour is configurable
- [ ] Settings update is owner-only
- [ ] Integration test: change digest hour, verify digest triggers at new time

---

### T419: Held-action review page (frontend)

**Scope**: frontend
**Depends**: T416
**Files**:

- `apps/web/app/(dashboard)/held-actions/page.tsx` (new)
- `apps/web/app/(dashboard)/held-actions/[id]/page.tsx` (new)
- `apps/web/components/pact/HeldActionCard.tsx` (new)
- `apps/web/components/pact/HeldActionBadge.tsx` (new)

**Description**: The core held-action review UX from user flow 01 Step 8.

`HeldActionCard` displays:

- Agent icon + "Needs Your Input" header
- Employee name and request summary
- "Why I'm asking you" — plain-language context
- Option buttons (Approve Anyway / Suggest Different Dates / Decline, etc.)
- Elapsed time since request

`/held-actions` page:

- List of all pending held actions, ordered by urgency
- Group: urgent (deadline/time-sensitive) at top, then routine
- Badge count in sidebar nav (uses `/api/pact/held-actions/summary`)
- Empty state: "All caught up. No pending items."

`/held-actions/{id}` page:

- Full detail view of a single held action
- All options as large tap-friendly buttons
- Option note field (optional free text)
- "View history" link to audit trail

`HeldActionBadge`:

- Red badge showing count of pending actions
- Displayed in sidebar nav and on dashboard card
- Uses TanStack Query with 60-second refetch interval

**Acceptance criteria**:

- [ ] Badge shows correct count from summary endpoint
- [ ] Tapping an option calls `POST /api/pact/held-actions/{id}/resolve`
- [ ] After resolution, card disappears from list (optimistic update)
- [ ] Urgent items shown first
- [ ] Empty state displayed when no pending actions
- [ ] Mobile-first: buttons are 44px touch targets minimum
- [ ] Playwright test: resolve a held action from the UI

---

### T420: "Suggest Different Dates" leave flow

**Scope**: both
**Depends**: T416, T419
**Files**:

- `src/hr_advisory/api/routers/leave.py` (extend)
- `apps/web/components/pact/SuggestDatesDialog.tsx` (new)

**Description**: The "Suggest Different Dates" option from user flow 01 Step 8
and as specified in gap resolution M5. When the boss chooses this option on a
leave held action, they see alternative weeks with full team coverage and can
send a counter-proposal to the employee.

Backend:

- `GET /api/leave/{id}/suggest-dates` — for a leave application, returns
  3 alternative date ranges with the same duration, where team coverage
  is full. Algorithm: look at the 4 weeks after the original request dates,
  check attendance/leave for all employees in the same team, rank by coverage.
- `POST /api/leave/{id}/suggest-dates` — body: `{suggested_start, suggested_end, note}`.
  Sets leave application `status = pending_reschedule`. Creates notification for
  the employee with the suggested dates and optional note.

New leave status: `pending_reschedule` (added in T401). Employee can:

- Accept: creates new leave application with suggested dates, cancels original
- Decline: leaves original application pending (routes back to boss)
- Propose different dates: updates application with new dates

Frontend `SuggestDatesDialog`:

- Shows within HeldActionCard when option "suggest_dates" is selected
- Lists 3 alternative date ranges with coverage indicator (e.g. "Full team available")
- Custom date range input as alternative
- Optional note field
- "Send to Employee" button

**Acceptance criteria**:

- [ ] `GET /api/leave/{id}/suggest-dates` returns 3 alternatives
- [ ] Alternatives have full team coverage (no existing leave conflicts)
- [ ] Employee receives in-app notification and email when dates are suggested
- [ ] `pending_reschedule` status flow: employee accepts → original cancelled, new created
- [ ] Employee declines → original back to pending for boss
- [ ] UI test: boss selects dates, employee accepts, both leave records updated correctly

---

### T421: Dashboard held-actions widget

**Scope**: frontend
**Depends**: T419
**Files**:

- `apps/web/app/(dashboard)/page.tsx` (modify)
- `apps/web/components/pact/DashboardHeldActions.tsx` (new)

**Description**: The dashboard "Pending for you" section from user flows 01
and 06, showing held actions inline on the main dashboard.

`DashboardHeldActions` component:

- Fetches pending held actions (limit 3, ordered by urgency)
- Renders each as a compact action card with inline approve/decline buttons
- "See all {N}" link when there are more than 3
- Disappears (no empty state) when count is 0

Dashboard main page update:

- Replace any existing "pending approvals" placeholder with `DashboardHeldActions`
- Show count in the "TODAY'S HIGHLIGHTS" section: "N actions need your approval"

**Acceptance criteria**:

- [ ] Dashboard shows up to 3 held actions inline
- [ ] Approving from the dashboard resolves the held action
- [ ] Count reflects real pending count from API
- [ ] "See all" navigates to `/held-actions`
- [ ] Component uses TanStack Query with 60-second refresh

---

### T422: Morning briefing integration with held actions

**Scope**: backend
**Depends**: T414, T401
**Files**:

- `src/hr_advisory/shadow/briefing.py` (modify)

**Description**: The existing briefing service generates daily summaries.
Extend it to include held-action counts and summaries from the PACT layer.

Modify `generate_morning_briefing(company_id: int, user_id: int) -> BriefingContent`:

- Add a `pending_actions` section: count and first 2 held action displays
- Include urgency-based sorting: urgent items mentioned first
- If count == 0: "All caught up. No pending items."
- If count >= 3: "You have {N} items that need your review."

This makes the briefing the proactive pull channel while T414 handles push.

**Acceptance criteria**:

- [ ] Briefing includes held-action count when pact_enabled
- [ ] Urgent held actions surfaced first in briefing
- [ ] Briefing shows "All caught up" when no pending actions
- [ ] Existing briefing tests still pass
- [ ] Unit test: company with 3 pending held actions generates correct briefing
