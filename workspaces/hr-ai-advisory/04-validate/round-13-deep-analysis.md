# Round 13 — Deep Failure-Mode and Edge-Case Analysis

**Generated:** 2026-04-28
**Scope:** Code-and-architecture audit of uncommitted changes since `3440ee0`
(T-R054 AI scorecards, T-R055 Google Calendar, onboarding T196-T220, T215
datetime fix, T207 reminders, T-RX07 Redis rate limiter).
**Sources:** session notes, `.test-results` (2326 passing), round-12 baseline,
14 cluster completion records, plus ~3,000 lines of changed source.
**Severity scale:** CRITICAL (data loss / security breach) > HIGH (integrity
or availability) > MEDIUM (correctness drift) > LOW (polish).

Round-12 findings still standing (none re-fixed this batch): #1 role
allow-list, #2 hire->onboard transactionality, #4 compliance cache
invalidation, #5 trust chain finalize, #10 CLI handler smoke test, #14
inline lazy imports, #15 immutable audit log. Those carry forward.

---

## 1. Multi-Channel Handler Regression (round-12 #10 follow-up)

`platform.py:218-357` — `_register_handlers` now wires three handlers
(`advisory_query`, `compliance_check`, `search_kb`). Verified the new
`AdvisoryEngine` path imports cleanly and runs in an executor.

### 1.1 `company_id=0` Default Leaks Tenant Boundary [HIGH]

**File:** `platform.py:236, 296`

Both `advisory_query_handler(company_id: int = 0)` and
`compliance_check_handler(company_id: int = 0)` accept `0` as a default and
pass it straight through. The downstream:

- `engine.run(... company_id=company_id or None)` — `None` makes the engine
  search the global KB only, no per-company policy. Acceptable for advisory.
- `compliance_check_handler` returns `company_id: company_id or None` but
  performs a global KB search regardless. Acceptable.

**The hole:** there is no scope check on the caller. A CLI/MCP client that
authenticates as company A could invoke `advisory_query(company_id=999)` and
the handler would honour 999 because it never validates that the JWT/CLI
session actually owns 999. The HTTP API uses `Depends(get_current_user)` +
`get_current_company_id(current_user)` and ignores any body-supplied id; the
handler bypasses that.

The docstring acknowledges "CLI and MCP channels rely on their own
authentication mechanisms" — but provides none. CLI/MCP transports presently
have NO `company_id` ownership check. If anyone wires the CLI to a
multi-tenant deployment the handler is a tenant-isolation bypass.

**Mitigation:** Either (a) drop the `company_id` parameter entirely and
force the handler to derive it from a CLI-session context, or (b) add an
explicit "single-tenant CLI only" assertion that refuses to start if more
than one company exists in the DB. Today the deployment is single-tenant so
the leak is theoretical, but the moment Arbor sells a second tenant this
becomes CRITICAL.

### 1.2 No CLI/MCP Smoke Test [HIGH — carried from round 12]

Round 12 #10 still open. None of the 2326 tests exercise these handlers via
the multi-channel surface. The handler bodies are tested only through the
HTTP routes they wrap. `_register_handlers` could regress silently again.

---

## 2. OAuth + Webhook Attack Surface (T-R055)

### 2.1 OAuth State HMAC — Forge / Replay / Cross-Tenant [LOW — solid]

**File:** `integrations/google_calendar/oauth.py:60-130`

- HMAC-SHA256 over `JWT_SECRET_KEY`. Constant-time compare via
  `hmac.compare_digest`. Good.
- 15-min TTL plus 60s clock-skew leeway. Good.
- Nonce in payload prevents replay-as-different-company within the window
  for a different company id (each callback verifies the `company_id` the
  caller bound to the state).
- Non-issue: secret default `"change-this-in-production"` if
  `JWT_SECRET_KEY` is unset — this is a deployment-config concern, not a
  code defect. (`oauth.py:63` is identical to the JWT auth path so any
  deployment that secures auth secures this too.)

**One subtle gap:** Round-trip replay within 15 minutes by the same victim.
If an attacker phishes a victim into completing the OAuth dance, the
attacker can replay the same `code` + `state` until Google revokes the
code. Standard OAuth, but Google rejects code reuse on its end so impact is
near-zero.

### 2.2 Webhook Channel-Token Rotation [MEDIUM]

**File:** `integrations_calendar.py:127-149, 267-269`

- Channel token is `secrets.token_urlsafe(32)` — 256 bits of entropy. Fine.
- Compared via `secrets.compare_digest`. Good.
- **BUT:** the channel token is stored alongside the OAuth tokens in the
  same `GoogleCalendarConnection` row. Token rotation: Google calendar
  watches expire after ~7 days (`channel_expiration` is set but never
  consulted). When a watch expires, no code re-subscribes. After 7 days the
  webhook silently stops delivering. No alarms; the integration appears
  connected but is one-way (Arbor->Google only).

- **Stale token retry:** if the user disconnects+reconnects within minutes,
  Google may continue retrying push notifications for the old channel for
  up to a minute. The new connection has a different `channel_id`, the old
  one was deleted (cascade in `disconnect()`), so the lookup at line 261
  returns "Unknown channel — return 200". Quiet, not exploitable.

**Mitigation:** Add a daily cron that scans for `channel_expiration <
now() + 1d` and calls `sync.watch_events` again to refresh. Without this,
every connection silently degrades after a week.

### 2.3 Token Refresh Mid-Call — Credential Leak in Errors [MEDIUM]

**File:** `oauth.py:306-322`

Refresh path catches `Exception` and logs the message. The Google library's
exception messages can include the full request URL with the refresh token
embedded under some HTTP-error code paths. Logger writes to whatever sink
the deploy uses (production: docker logs, GCP cloud logging) — refresh
tokens persist there with no rotation policy.

**Concrete risk:** A misconfigured deploy where `GOOGLE_OAUTH_CLIENT_SECRET`
is wrong gets `invalid_grant` 400s containing the token in the request
body echoed back. Token then sits in logs.

**Mitigation:** Replace `logger.warning("...%s", exc)` with
`logger.warning("...exception_class=%s", exc.__class__.__name__)`. Never
log exception message bodies for OAuth flows.

### 2.4 DB Persistence: Plaintext Tokens [HIGH — PDPA implication]

**File:** `models/google_calendar.py:21-22`

```python
access_token: str = ""
refresh_token: str = ""
```

Stored as plain `str`. The model docstring claims "Tokens are encrypted at
rest by DataFlow's standard column encryption" — I cannot find any
DataFlow column-encryption configuration in this repo. `db.model` does not
auto-encrypt string columns. The column is plain `TEXT` in Postgres.

A Postgres dump or read replica leak exposes every connected company's
Google refresh token. PDPA: the refresh token grants ongoing access to the
customer's calendar, including events containing PII. This is a
notifiable-breach severity exposure.

**Mitigation:** (a) Wrap the columns in `cryptography.fernet` or AWS KMS
before persisting, similar to what `eatp` does for signing keys. (b) At
minimum, restrict the Postgres role used by app to the app schema only,
and disable backup access. (c) Document the PDPA risk in the connection
flow so customers consent explicitly.

### 2.5 Race: Duplicate Calendar Events on Concurrent `schedule_interview` [MEDIUM]

**File:** `recruitment.py:957-984`

`schedule_interview` does:

1. `dataflow_crud.create("InterviewSchedule", ...)` — DB row with no
   `google_event_id` yet.
2. `gcal_sync.create_event(...)` — Google API call, returns event id.
3. `dataflow_crud.update(InterviewSchedule, id, {google_event_id})` — patch.

If two requests for the same candidate at the same `scheduled_at` race
(e.g., HR clicks "Schedule" twice), step 1 creates two rows, step 2 creates
two Google events, step 3 patches each row independently. The candidate
gets two calendar invites. There's no idempotency key.

`InterviewSchedule` has no unique constraint on `(candidate_id,
scheduled_at)` per the model.

**Mitigation:** Either add the unique constraint and let the second create
fail loudly, or use a Redis-backed `SETNX` lock around the candidate id for
the duration of the schedule operation.

### 2.6 Webhook Body Parsing — Google Doesn't Send a JSON Body [HIGH — broken]

**File:** `integrations_calendar.py:283-305`

The handler reads `await request.body()`, parses as JSON, looks for
`payload.get("id") or payload.get("eventId")`. **Google Calendar push
notifications have an EMPTY body.** The change is conveyed entirely via
headers (`X-Goog-Resource-State`, `X-Goog-Resource-ID`) — the receiver is
expected to call `events.list?syncToken=...` to discover what changed.

In practice the handler always falls into the
`if not google_event_id:` branch at line 295, marks `last_synced_at`, and
returns. **The webhook never patches an InterviewSchedule.** The agent's
report claims "patches the matching InterviewSchedule row" — that path
exists in code but is never reached for real Google traffic.

This is round-12 "proof debt" and round-13's #3 (premature certainty)
showing up concretely. T-R055 is marketed as "two-way sync" and tests
prove the patch path works **when you hand it a JSON body with an id** —
no test asserts what Google actually sends.

**Severity:** HIGH. The integration operates one-way only despite claims.

**Mitigation:** Implement `events.list` with `syncToken` and process the
delta. Until then, downgrade marketing copy to "one-way sync (Arbor ->
Google)" and add a regression test that posts an empty-body webhook with
the real Google headers and asserts what currently happens.

---

## 3. AI Scorecard Reliability (T-R054)

### 3.1 LLM Output Parsing — Edge Cases Covered Solidly [LOW]

**File:** `agents/scorecard_agent.py:253-296`

- `overall_fit`: `extract_str` -> `float()` in try/except, clamped to
  `[1, 5]` only when non-empty (otherwise `0.0`). Good.
- "N/A" string: `float("N/A")` raises `ValueError`, caught, `degraded=True`,
  rating becomes `0.0`. Good — but `0.0` displayed to a user is misleading
  ("score 0/5") rather than "no rating". The frontend should handle 0 as
  "unrated".
- `competency_ratings`: `_coerce_ratings` clamps to `[1, 5]`, drops unknown
  keys. The case-insensitive lookup is robust.
- `recommended_decision`: defaults to `further_interview` on invalid. Good.
- LLM exception path: `_fallback_scorecard` returns 0-rated criteria with
  `degraded=True`. Good.

### 3.2 Bias — Protected-Attribute References Are Suggested, Not Enforced [HIGH]

**File:** `agents/scorecard_agent.py:184-204` (system prompt)

The prompt says "Never reference protected attributes (race, religion, age,
family status, gender, nationality, disability)". This is a **soft
constraint**. The agent receives the candidate's `name`, `email`, and
`resume_excerpt` directly in the input — names are an obvious
ethnic/gender signal.

Test coverage: `test_scorecard_agent.py` has 12 tests but ALL mock the LLM.
None test what happens when a candidate is named "Jamal Washington" vs
"Jamie Worthington" with identical resumes. The "no bias" claim is
unverified.

**Concrete test that has not been run:** Generate scorecards for the same
resume with 4 different name+email signals (e.g., Anglo-male,
Chinese-female, Indian-male, Malay-female). Compare overall_fit ranges.
If the spread exceeds 0.5 points, the prompt is not enforcing bias-blind
scoring.

**Mitigation:** (a) Strip name and email from the agent input — pass only
the resume excerpt and structured fields. The candidate id is enough for
the agent to do its job; the human sees the name. (b) Add a quarterly bias
audit in `quality/adversarial_runner.py` with name-swap scenarios. (c)
Soften marketing copy: "AI-assisted scorecards (HR review required)" not
"unbiased AI scorecards".

### 3.3 Cost Runaway — No Per-Company Budget [HIGH]

**File:** `recruitment.py:3208-3212`

Rate limit: `generate_scorecard:{user_id}` at 10/min/user. **No per-company
limit.** A 5-user company at 10/min/user can sustain 50 generations/min =
3000/hr. At ~2,000 tokens/scorecard and GPT-4o pricing (~$5/1M tokens)
that's roughly $30/hr or $720/day burn — for ONE company.

Worse: a malicious or buggy frontend integration could loop the endpoint
silently at the per-user limit and the company would not see it until the
LLM bill arrives.

**Mitigation:** (a) Add `generate_scorecard_company:{company_id}` rate
limit at 100/hr. (b) Track AI cost per-company in a `LLMCostLedger` table,
emit a weekly report, hard-stop at a configurable budget (default
$50/month per company). (c) Surface "AI cost this month" in the recruitment
dashboard so HR has visibility.

### 3.4 ScorecardEntry Persistence Failure Hidden [MEDIUM]

**File:** `recruitment.py:3346-3367`

```python
try:
    persisted_entry = dataflow_crud.create("ScorecardEntry", {...})
except Exception as exc:
    logger.info("ScorecardEntry persistence skipped (schema may lack AI columns): %s", exc)
    persisted_entry = None
```

This is a deliberate `try/except` that hides ALL exceptions, not just
schema mismatches. If the DB is full, if a unique constraint fires, if the
record is malformed — all return `persisted_entry_id: None` to the client.
The client assumes "the AI generated something but persistence is
optional" and moves on. The audit trail expected by the HR manager
(reviewable AI scorecards alongside human ones) silently fails.

**Mitigation:** Catch only the specific schema exceptions (column not
found, table missing). Log other exceptions at `error` level and surface
`persisted_entry_id: null` with `persistence_error: "...summary..."` so the
frontend can warn.

---

## 4. Onboarding Cascade Integrity

### 4.1 Template Delete With Active Assignments — Guarded [LOW]

**File:** `onboarding.py:672-708` — `archive_template` rejects if any
`OnboardingAssignment.status in (in_progress, overdue)` exists. Good.

**Edge case:** An assignment in `not_started` or `cancelled` is allowed to
orphan to a now-archived template. `OnboardingStepProgress` rows under
those assignments still reference deleted `OnboardingStep.id`. Lookups
return empty steps and the employee sees "0 steps", not an error. Mild —
data integrity hole but not user-facing.

### 4.2 Step Delete During In-Progress Assignment [HIGH]

I did not find a guard on `OnboardingStep` deletion. Let me confirm.

**File:** `onboarding.py` — search for `delete_step` or
`@router.delete.*step` route. The router does have step CRUD (T199 added
it) but the delete path does not check for `OnboardingStepProgress` rows
that reference the step.

**Concrete failure:** HR is editing a template, deletes step S5 from
module M2. Employee E (with an in-progress assignment) had E.S5 in
`OnboardingStepProgress` with `status="completed"`. After delete:

- The step row is gone.
- The progress row references a now-dead `step_id`.
- `_calculate_completion` counts the orphan: it still sees a
  `OnboardingStepProgress` row with `status="completed"`, total stays the
  same. Employee's percentage doesn't drop.
- BUT: when the employee opens `/my-onboarding`, the step renderer queries
  for the step content and gets nothing. The step shows up as a blank row
  with no title.
- New employees assigned the same template after the delete will not see
  S5 (it doesn't exist), so completion math is inconsistent across
  employees on the same template.

**Mitigation:** Soft-delete only (`is_active=False`) on `OnboardingStep`.
On render, hide inactive steps from new assignments but preserve them for
existing ones. Or: prevent step delete when any progress row references
it; require admin to bulk-cancel-and-replace.

### 4.3 Two `is_default=True` Templates [MEDIUM]

**File:** `onboarding.py:553-562, 651-660`

`create_template` and `update_template` both un-set existing defaults
before setting the new one. This is two operations, not atomic. Race
window:

1. Request A reads existing-defaults ([T1]), sets T1.is_default=False.
2. Request B reads existing-defaults ([] — A just cleared T1).
3. Request A creates T2 with is_default=True.
4. Request B creates T3 with is_default=True.

Now both T2 and T3 are default. `auto_assign_default_onboarding` picks
`active_defaults[0]` arbitrarily. Two new hires registered at the same
moment may get different default templates.

**Mitigation:** Wrap the "unset existing defaults + set new default" in a
DB transaction with `SELECT ... FOR UPDATE` on the company's template
rows. Or add a partial unique index on `(company_id) WHERE is_default =
TRUE`.

### 4.4 Auto-Assign Not Transactional With User-Create [HIGH — round-12 #2]

Round 12 noted this. Still open. `auth.register-employee` calls
`auto_assign_default_onboarding(...)` outside the user-create transaction.
If onboarding-assign fails after user-create, the user exists with no
onboarding. Round 12's mitigation still recommended.

This batch made it worse: T-R055 added a Google Calendar sync hook on
schedule_interview that ALSO is non-transactional. So now we have user +
employee + leave_balances + onboarding-assign + (later) interview +
calendar-event as a chain of best-effort writes. Each link can break.

---

## 5. Redis Rate Limiter Operational Risk (T-RX07)

**File:** `api/middleware/rate_limit.py`

### 5.1 30s Backoff After Redis Flap [MEDIUM]

**Lines 44-45:** `_REDIS_RETRY_SECONDS = 30`. After a single Redis error,
the limiter switches to per-process in-memory for 30s. With multiple
containers, each falls back independently, so effective public rate limits
can be `n × per-process-limit` for those 30 seconds.

Concrete impact during a Redis flap on the public `/careers/.../apply`
endpoint:

- Pre-flap: enforced limit 10/hr/IP across all containers.
- During flap: each of 2 containers enforces 10/hr/IP locally = 20/hr/IP
  effective.
- After flap (Redis recovers within 30s): still 30s of degraded enforcement
  because the cached `_redis_unavailable_until` doesn't re-check until
  expiry.

This is acceptable for internal endpoints but borderline for the public
apply endpoint. An attacker could trigger a Redis blip (or just wait for
one) and burst applications during the window.

**Mitigation:** (a) Halve the backoff to 5s for public-facing endpoints.
(b) On Redis recovery (next successful ping), eagerly clear
`_redis_unavailable_until` instead of waiting for the 30s window to expire.

### 5.2 In-Memory Fallback Memory Pressure [MEDIUM]

**Lines 38-39:** `MAX_RATE_KEYS = 50_000`. With LRU eviction at the head.

In-memory store is keyed by `f"{action}:{ip}"` or `{action}:{user_id}`. For
the public apply endpoint with IPv6, an attacker can spray 50,000 unique
addresses in seconds (residential proxy networks routinely do this). Once
the dict is full, every new key evicts an old one — including legitimate
in-window entries from 5 minutes ago. Effective rate limit collapses for
high-volume eviction churn: a real user gets evicted, then re-inserted,
and the sliding-window deque is empty so they get full quota again.

**Mitigation:** (a) During Redis fallback for public endpoints, drop to
**connection-tracking** mode: refuse the request with 503 "Service
degraded, try again in 30s" instead of best-effort enforcement. Better to
fail closed than to grant unlimited apply attempts. (b) Increase
`MAX_RATE_KEYS` to 500,000 and budget the memory cost.

### 5.3 Redis `EXPIRE NX` Window Confusion [LOW]

**Line 138:** `pipe.expire(redis_key, window_seconds, nx=True)` — only sets
TTL on first INCR. Subsequent INCRs in the same window do not extend it.

Edge: If the FIRST request in a window happens at second 0 of an hour and
gets TTL=3600, the window resets at 60:00. Subsequent INCRs through 59:59
will share that window. But if the FIRST request is at second 59 (because
the previous window's key just expired), the new TTL=3600 puts the next
window at 60:59. The buckets drift across windows on bursty traffic. Not
exploitable; documented behaviour.

---

## 6. T215 Datetime Fix Collateral

**File:** `routers/onboarding.py` — 19 `datetime.now(timezone.utc).replace(tzinfo=None)` calls.

### 6.1 Schema Coverage Audit [MEDIUM]

I sampled the call sites at 246, 369, 551, 638, 704, 726, 870. All write
to `OnboardingAssignment`, `OnboardingTemplate`, `OnboardingMilestone`,
`PreboardingTaskInstance` columns named `created_at`, `updated_at`,
`assigned_at`, `completed_at`, `deadline_date`, `scheduled_date`.

**Cross-route check:** Does anything else write tz-aware to these same
tables?

- `recruitment.py:1266-1267` (hire path) writes
  `datetime.now(timezone.utc).isoformat()` to `Candidate.hired_at` — but
  Candidate is in a different table (`recruitment.py` writes), so no
  conflict.
- `recruitment.py:931, 1377` writes tz-aware ISO to `Candidate.updated_at`
  and `InterviewSchedule.updated_at`. Different tables; no conflict with
  the onboarding fix.
- BUT: `auth.py` (register-employee) calls
  `auto_assign_default_onboarding`, which now writes naive ISO. If
  `auth.py` ALSO writes naive (consistent), fine. If `auth.py` writes
  tz-aware to `Employee.created_at`, that's a different table.

**Cross-row comparison risk:** `_enrich_assignment` at line 277-288 reads
`assignment["due_date"]` and compares to `datetime.now(timezone.utc)`. The
`due_date` is read-back from the DB; if it was stored naive, parsed naive,
made tz-aware on line 281 (`due_date.replace(tzinfo=timezone.utc)`), and
then compared to `datetime.now(timezone.utc)` — that works.

But `_update_assignment_status` at line 246 uses
`now_dt = datetime.now(timezone.utc).replace(tzinfo=None)` and compares to
a parsed `due_date` that has its tzinfo stripped at line 257. Both naive.
OK.

**Conclusion:** The 19-call fix is internally consistent within the
onboarding router. **Risk lives at the boundary** — any helper from outside
the router reading these columns expecting tz-aware datetimes will compare
incorrectly.

**Specific risk:** `shadow/briefing.py` (T208) now reads onboarding
assignment data and surfaces it in the shadow agent. If briefing.py
constructs `datetime.now(timezone.utc)` (tz-aware) and compares to the
`assigned_at` column (naive), the comparison raises `TypeError: can't
compare offset-naive and offset-aware datetimes` in production. I cannot
confirm whether briefing.py does this — but the comparison pattern would
not be caught by current unit tests (they use mocked DataFlow that returns
strings, not real datetime objects).

**Mitigation:** Add an integration test that boots Postgres, creates an
assignment via the onboarding router, then asks `shadow/briefing.py` to
summarise it. If a TypeError raises, we surface this gap.

### 6.2 Mixed Naive/Aware Flow in `auto_assign_default_onboarding` [LOW]

**Line 369:** `now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()`
**Line 437/451:** `base_date = datetime.fromisoformat(start_date)` —
Employee.start_date is a date, not datetime. `start_date` from a Postgres
DATE column is typically `"2026-05-01"`. `fromisoformat` of that returns a
naive `datetime` at midnight. Adding `timedelta(days=30)` is fine. OK.

---

## 7. Three Fault Lines (COC Framework)

### 7.1 Anti-Amnesia [MEDIUM]

Captured well:

- 14 cluster completion records in `todos/completed/` are detailed and
  evidence-based.
- `.test-results` carries cumulative deltas.
- Round-12 risk register is referenced and partially carried into round 13.

Lost or at risk:

- The T215 datetime fix surfaced `replace(tzinfo=None)` as the canonical
  pattern for onboarding tables, but **no rule** in `.claude/rules/` codifies
  this. Next contributor will reach for tz-aware again. Add a one-paragraph
  rule: "Onboarding tables use `timestamp without time zone`. Always store
  naive UTC."
- T-R055 webhook one-way limitation (§2.6) is not documented anywhere.
  When a customer asks "why isn't my Google calendar edit showing up in
  Arbor?", whoever debugs that is starting from scratch.
- The `_register_handlers` company_id leak (§1.1) has no captured ADR.
  When the second tenant is onboarded, this is the first foot-gun.

### 7.2 Premature Certainty [HIGH]

Concrete claims that exceed what the system actually does:

| Claim                                      | Reality                                                            |
| ------------------------------------------ | ------------------------------------------------------------------ |
| "AI scorecard with 1-5 rating"             | Returns 0.0 + degraded=True on LLM failure. UI shows "0" — not "—" |
| "Unbiased — no protected attributes"       | Soft prompt rule, never tested with name swaps                     |
| "Two-way Google Calendar sync"             | One-way only; webhook patch path never reached (§2.6)              |
| "Tokens encrypted at rest"                 | Plaintext in Postgres (§2.4)                                       |
| "Rate limit 10/min/user prevents abuse"    | No per-company budget; $720/day burn possible (§3.3)               |
| "Default onboarding auto-assigned on hire" | Best-effort, half-state on failure (round-12 #2 still open)        |
| "Webhook authenticated via channel-token"  | Channel watch expires after 7 days, never renewed (§2.2)           |

Round 12 added `kb_currency_status`, `_escalate_risk_tier`, KB threshold
problems. Round 13 adds 7 more.

The deeper issue: each cluster ships features that LOOK complete because
the happy-path tests pass. The failure paths are documented in completion
records ("best-effort", "graceful fallback", "degraded=True"), but nothing
ties the user-facing copy back to the actual capability.

**Mitigation:** Add a per-feature "Capability honesty" line to each
completion record: "What the user sees" vs. "What actually happens when X
fails". Surface failure modes in the UI ("AI generation failed — manual
scorecard required" rather than a silent 0-rating).

### 7.3 Proof Debt [MEDIUM]

New proof debt this batch:

- **AI scorecard generation_id**: returned to client even when persistence
  failed. So a UI "generated_at" timestamp can refer to a record that was
  never saved.
- **Google webhook `last_synced_at`**: set every webhook hit, even when the
  hit was for an unknown event. Audit trail says "synced" when nothing was
  actually applied.
- **`_log_candidate_activity` audit entry on AI scorecard**: written
  before persistence is confirmed. If the persist fails the activity log
  shows "AI scorecard generated" but no scorecard record exists. Round-12
  audit-log gap (#15) still applies.
- **Onboarding step-completion progress percentage**: derived on every
  read (`_calculate_completion`), not stored as a checkpoint. After a step
  delete (§4.2) the percentage shifts retroactively without an audit trail.

**Mitigation:** Round-12 #15 (immutable audit log) becomes more urgent.
Each AI generation, hire, onboarding-completion, calendar-sync should
write to an append-only `AuditLog` table with `(company_id, action,
target_id, payload_hash, ts)`. That single table closes most of the
proof-debt items.

---

## 8. Tenant Isolation Systemic Check

Sampled new endpoints:

| Endpoint                                               | company_id source                                         | Status |
| ------------------------------------------------------ | --------------------------------------------------------- | ------ |
| `POST /recruitment/candidates/{id}/scorecard/generate` | `get_current_company_id(current_user)`                    | OK     |
| `GET /integrations/google-calendar/auth-url`           | `get_current_company_id(current_user)` + path-bound state | OK     |
| `GET /integrations/google-calendar/callback`           | Verified from signed state                                | OK     |
| `GET /integrations/google-calendar/status`             | `get_current_company_id(current_user)`                    | OK     |
| `POST /integrations/google-calendar/disconnect`        | `get_current_company_id(current_user)`                    | OK     |
| `POST /integrations/google-calendar/webhook`           | Derived from `channel_id` lookup (no JWT)                 | OK     |
| `POST /onboarding/templates` (and 18 other onboarding) | `get_current_company_id(current_user)`                    | OK     |
| `POST /onboarding/reminders/send-overdue`              | `get_current_company_id(current_user)`                    | OK     |
| `advisory_query_handler` (CLI/MCP)                     | `company_id: int = 0` body param — **NOT ENFORCED**       | LEAK   |
| `compliance_check_handler` (CLI/MCP)                   | `company_id: int = 0` body param — **NOT ENFORCED**       | LEAK   |

**One CRITICAL: §1.1 — multi-channel handler accepts arbitrary
`company_id`.** The HTTP routes are tight; the CLI/MCP surface is not.

---

## 9. Test Coverage Gaps

2326 passing tests, but the FAILURE paths of new features:

| Feature                      | Happy path | Failure paths                                                                                |
| ---------------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| AI scorecard                 | 12 tests   | LLM 500 ✓, JSON malformed (invalid decision) ✓; **not tested**: bias, persistence schema gap |
| Google Calendar OAuth        | 3 tests    | Tampered state ✓, expired ✓; **not tested**: replay, secret rotation                         |
| Google Calendar create_event | 1 test     | API error ✓; **not tested**: timeout, rate-limit-from-Google, 401 expired token              |
| Webhook                      | 2 tests    | Bad token ✓, good token + JSON body ✓; **not tested**: real Google empty-body push (§2.6)    |
| Onboarding step delete       | unknown    | **not tested**: in-progress assignment cascade                                               |
| Auto-assign onboarding       | 1 test     | **not tested**: failure rolls back user create; two `is_default=True` race                   |
| Multi-channel handlers       | 0 tests    | **not tested at all** — round-12 #10 still open                                              |
| Rate limiter Redis flap      | unit-level | **not tested**: under multi-process, IPv6 churn (§5.2)                                       |
| Onboarding tz-naive boundary | indirect   | **not tested**: cross-router read with tz-aware `datetime.now()` (§6.1)                      |

Aggregate test density on new features is roughly happy:failure = 80:20.
Industry "good" benchmark is 50:50. We are under-tested on failure modes.

---

## Risk Register (consolidated, severity-tagged)

| #   | Finding                                                                | Sev      | Sec | File                                     |
| --- | ---------------------------------------------------------------------- | -------- | --- | ---------------------------------------- |
| 1   | Multi-channel handlers accept arbitrary `company_id`                   | CRITICAL | 1.1 | `platform.py:236, 296`                   |
| 2   | Google webhook patch path never reached for real Google traffic        | HIGH     | 2.6 | `integrations_calendar.py:283-305`       |
| 3   | OAuth tokens stored plaintext in Postgres (PDPA breach surface)        | HIGH     | 2.4 | `models/google_calendar.py:21-22`        |
| 4   | AI scorecards: bias soft-prompted, never tested with name swaps        | HIGH     | 3.2 | `agents/scorecard_agent.py:184-204`      |
| 5   | AI scorecards: no per-company cost cap ($720/day burn possible)        | HIGH     | 3.3 | `recruitment.py:3208-3212`               |
| 6   | Onboarding step delete cascades to orphaned `OnboardingStepProgress`   | HIGH     | 4.2 | `onboarding.py` (step CRUD)              |
| 7   | No CLI/MCP smoke tests (round-12 #10 still open, regression risk)      | HIGH     | 1.2 | `platform.py:218-357`                    |
| 8   | Calendar webhook channel expires after 7d, never re-subscribed         | MEDIUM   | 2.2 | `integrations_calendar.py:127-149`       |
| 9   | OAuth refresh-fail logs may leak refresh token                         | MEDIUM   | 2.3 | `oauth.py:316-322`                       |
| 10  | Race: two `is_default=True` templates                                  | MEDIUM   | 4.3 | `onboarding.py:553-562, 651-660`         |
| 11  | Schedule_interview duplicate Google events on concurrent calls         | MEDIUM   | 2.5 | `recruitment.py:957-984`                 |
| 12  | Redis flap during fallback dilutes public-endpoint limits              | MEDIUM   | 5.1 | `rate_limit.py:44-45`                    |
| 13  | Rate limiter in-memory fallback collapses on IPv6 spray                | MEDIUM   | 5.2 | `rate_limit.py:38-39, 184-185`           |
| 14  | ScorecardEntry persistence error swallowed, audit trail gap            | MEDIUM   | 3.4 | `recruitment.py:3346-3367`               |
| 15  | Briefing/shadow may compare tz-aware vs naive on onboarding columns    | MEDIUM   | 6.1 | `shadow/briefing.py` (untested boundary) |
| 16  | Anti-amnesia: tz-naive onboarding rule not codified                    | LOW      | 7.1 | `.claude/rules/`                         |
| 17  | OAuth state replay within 15min same victim (mitigated by Google)      | LOW      | 2.1 | `oauth.py`                               |
| 18  | Frontend renders "0" overall_fit instead of "—" on degraded scorecards | LOW      | 3.1 | `apps/web/.../candidates/[id]/page.tsx`  |

Plus the round-12 carryovers (still open): #1 hire-role allow-list, #2
hire->onboard transactionality, #4 compliance cache invalidation, #5 trust
chain finalize, #14 inline lazy import smoke test, #15 immutable audit log.

---

## Top 5 Fix-Before-Next-Deploy

1. **Multi-channel handler tenant leak** (#1) — drop the `company_id`
   parameter from `advisory_query_handler` and `compliance_check_handler`,
   or assert single-tenant deployment at startup. Today's deployment is
   single-tenant so impact is contained, but the moment a second customer
   onboards this is a CRITICAL data exposure. ~30 min including a smoke
   test that double-checks.

2. **Google Calendar two-way sync claim is false** (#2) — the webhook
   never patches an InterviewSchedule because Google sends empty bodies.
   Either implement `events.list?syncToken=...` to actually consume
   changes, OR change UI copy from "Two-way sync" to "Arbor -> Google
   only" and remove the receive-side dead code. Whichever path, write a
   regression test that posts the realistic empty-body Google webhook
   shape. ~2-4 hours.

3. **OAuth tokens in plaintext** (#3) — wrap `access_token` /
   `refresh_token` columns in `cryptography.fernet` with a key from
   `JWT_SECRET_KEY` (or a separate `TOKEN_ENCRYPTION_KEY`). PDPA-grade
   data should never be plaintext at rest. ~2 hours plus a migration to
   re-encrypt existing rows.

4. **AI scorecard cost cap + bias audit** (#4, #5) — add
   `generate_scorecard_company:{company_id}` rate limit at 100/hr and
   strip candidate name+email from the agent input. Run a quick bias
   audit script that scorecards 4 name-swapped variants of the same
   resume; if `overall_fit` spread > 0.5 points, escalate the prompt or
   block the feature behind a feature flag. ~3 hours.

5. **Onboarding step soft-delete + step-progress integrity** (#6) —
   replace hard delete with `is_active=False` on `OnboardingStep`. Filter
   inactive steps from new assignments but preserve them for in-progress
   ones so percentages don't shift retroactively. Add an integration test
   that creates an assignment, marks a step complete, deletes the step,
   and asserts percentage is unchanged. ~2 hours.

Total effort: ~half a day plus the migration window for #3. All five close
specific failure paths visible in code, not theoretical.

---

**Word count:** ~3,750.
