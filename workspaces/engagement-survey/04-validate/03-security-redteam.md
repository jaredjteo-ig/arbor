# Engagement Survey — Round-1 Security Red Team

Date: 2026-05-07
Reviewer: security-reviewer (Claude)
Scope: M0–M6 of `/engagement-survey`. Backend router + helpers + services + models +
seed scripts; frontend typed surface only (UI-side rendering not deeply audited
because React auto-escapes are sufficient for the discovered text-injection paths).

Single-tenant deployment per the user's recent decision: cross-tenant findings are
defense-in-depth, not primary exploits. Authenticated-admin-as-attacker is the
operative threat model for HR-only endpoints; authenticated-employee-as-attacker
for `/my-*` endpoints.

---

## CRITICAL (must fix before commit)

None. The high-impact paths the user flagged (SQL injection in
`_list_records_direct_sql`, pseudonym-secret leakage, anonymity-tier branching,
tenant isolation, idempotency replay) are all currently safe given the model
names that callers actually pass and given the seed-script context. See HIGH for
items that are one refactor away from CRITICAL and should be hardened now.

---

## HIGH (should fix before merge)

### H1 — `_list_records_direct_sql` filter-key SQL injection (latent)

**File**: `src/hr_advisory/services/dataflow_crud.py:122–166`

The user explicitly flagged the `f"SELECT * FROM {table}"` line. The `table`
value comes from `_model_to_table(model_name)`, and current callers pass
hardcoded model-name string literals — so the table interpolation is safe today.
But the **filter-key** interpolation a few lines down is the larger latent risk:

```python
for k, v in filter_dict.items():
    if v is None:
        clauses.append(f"{k} IS NULL")
    else:
        clauses.append(f"{k} = %s")
        params.append(v)
```

Filter keys (`k`) are interpolated into the SQL with no validation. The values
(`v`) are correctly parameterised, but a caller that constructs `filter_dict`
from user input (e.g. via a query-string passthrough or a generic search
endpoint) would inject SQL through the key. Today, every call site I audited
passes literal string keys (`"company_id"`, `"survey_id"`, `"id"`, `"user_id"`,
etc.), so the live exploit path is closed. The risk is that the next engineer
who adds a `?filter=foo:bar` style endpoint will hand `filter_dict` to this
function and ship an injection.

The same applies to `model_name`: today every caller passes a literal CamelCase
model class name, but a future caller that passes `request.query_params["model"]`
through to `list_records(model_name=...)` would inject via the table
interpolation.

**Suggested fix**:

```python
import re
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

def _validate_identifier(name: str, what: str) -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL {what}: {name!r}")
    return name

def _list_records_direct_sql(...):
    table = _validate_identifier(_model_to_table(model_name), "table name")
    ...
    for k, v in filter_dict.items():
        _validate_identifier(k, "filter key")
        ...
```

Add this even though no current caller is exploitable — it costs ~5 LOC and
removes the entire class of injection.

This also satisfies `.claude/rules/infrastructure-sql.md` MUST Rule 1 ("Validate
SQL Identifiers with `_validate_identifier()`").

---

### H2 — CSRF guard is permissive; does not match configured origin

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1391–1410` (`_check_csrf_or_origin`)

Round-2 H9/Z11 was supposed to lock the in-app submit handler to the configured
app origin. The current implementation only rejects `Origin: null`:

```python
if origin and origin.startswith("null"):
    raise HTTPException(status_code=403, detail="Cross-origin denied.")
```

Any browser with `Origin: https://evil.example.com` passes this guard. Bearer
auth is the primary defence and works against pure CSRF (a third-party page
can't read a Bearer token from cookies it doesn't control), but the platform
docstring says "the rest of the platform sometimes runs cookie-based session"
— in that case a real CSRF is possible.

Even with Bearer-only, there's a useful defence the current code is missing:
on a cross-origin POST to `/my-responses/{id}/submit` from a malicious page,
the browser sends the JWT only if the user pasted it into the malicious page
or the malicious page can read it from your localStorage via XSS. Tightening
to a same-origin / configured-origin check costs ~10 LOC and makes the next
exploit chain harder.

**Suggested fix**:

```python
from urllib.parse import urlparse
from hr_advisory.config.settings import get_settings

def _check_csrf_or_origin(request: Request) -> None:
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    if not origin and not referer:
        return  # server-side caller via Bearer
    settings = get_settings()
    allowed = {o.rstrip("/") for o in (settings.cors_origins or [])}
    candidate = origin.rstrip("/") or (
        f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
        if referer else ""
    )
    if candidate and candidate not in allowed:
        raise HTTPException(status_code=403, detail="Cross-origin denied.")
```

Per `.claude/rules/security.md` Output-Encoding rule and the task brief's
explicit ask in concern #3.

---

### H3 — PDPA admin-access logging not actually wired

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1188–1190`

The `list_responses` handler has the comment

```python
# Round-2 H12 / Z16 — PDPA admin-access log hook.
# (Stub: existing _log_pdpa_access wiring in Arbor;
# call it here when present in the platform.)
```

…but doesn't call anything. The `_log_pdpa_access` helper **does** exist at
`src/hr_advisory/api/routers/employees.py:729–760` — it's just not imported
or invoked here. Identified-tier surveys leak employee_name + employee_email
to admins on every call to `GET /surveys/{id}/responses` with no audit trail.

This violates Round-2 H12 / Z16 explicitly (the brief's concern #4).

**Suggested fix**: extract `_log_pdpa_access` (and `_create_pdpa_log` /
`_list_pdpa_logs`) into a shared module, e.g.
`src/hr_advisory/services/pdpa_audit.py`, then call from the engagement-surveys
list_responses handler:

```python
from hr_advisory.services.pdpa_audit import log_pdpa_access

if tier == "identified":
    ...
    for r in rows:
        ...
        if u:
            r["employee_name"] = u.get("name", "")
            r["employee_email"] = u.get("email", "")
            log_pdpa_access(
                accessed_by=int(current_user.get("sub", 0)),
                company_id=company_id,
                data_subject_id=int(emp["id"]),
                categories=["engagement_response_pii"],
                action="engagement_responses_list",
                ip_address=request.client.host if request.client else "",
            )
```

The brief mentions this is a single-tenant deployment, so PDPA-trail loss is
the actual harm rather than a cross-tenant attack.

---

### H4 — Cohort preview cross-tenant guard is correct, but launch path skips it

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:621–638` (preview)
vs `:903` (launch).

`preview_cohort` correctly guards `ad_hoc_employee_ids` against IDs outside the
caller's company:

```python
cross_tenant = ids_to_check - owned_ids
if cross_tenant:
    raise HTTPException(...)
```

`launch_survey` does NOT — it just calls `cohort_resolver.resolve_cohort(...)`
which silently filters foreign IDs out (cohort_resolver.py:298–301 checks
`emp_by_id.get(int(emp_id))`).

The silent filter means cross-tenant launch attempts never raise; on
single-tenant this isn't exploitable. But the inconsistency violates the
explicit guard the round-2 work added. Promote the preview-side check to a
shared helper and call it from both endpoints.

**Suggested fix**:

```python
def _validate_ad_hoc_ids(filter_spec: dict, company_id: int) -> None:
    ids = filter_spec.get("ad_hoc_employee_ids")
    if not ids:
        return
    owned = dataflow_crud.list_records(
        "Employee", {"company_id": company_id}, cache_ttl=0
    )
    owned_ids = {int(e["id"]) for e in owned if e.get("id")}
    cross_tenant = set(int(i) for i in ids) - owned_ids
    if cross_tenant:
        raise HTTPException(
            status_code=400,
            detail="ad_hoc_employee_ids contains employee(s) outside your company.",
        )
```

Call from both `preview_cohort` and `launch_survey` (the latter on the inline
`cohort_filter_spec` path AND, defensively, after loading a saved cohort, in
case the cohort was authored before the validation existed).

---

### H5 — Idempotency-key fallback skipped when client sends empty string

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1465–1469`

```python
idem_in = (request.headers.get("idempotency-key") or "").strip()
if not idem_in:
    idem_in = hashlib.sha256(...).hexdigest()
```

This is actually correct for the empty-string case (`"".strip() or "..."`
falls back). But there are two adjacent holes:

1. **Whitespace-only keys**: a client sending `Idempotency-Key:    ` (whitespace)
   becomes `""` after strip and hits the fallback. Fine.
2. **Single-char keys**: a client sending `Idempotency-Key: x` is accepted as-is.
   This is a denial-of-resubmit risk: an attacker who can read a victim's idem
   key could replay it; conversely, a malicious browser extension could submit
   `x` to lock out the user's honest submit. Not a privilege boundary, more a
   robustness issue.
3. **Already-submitted retry path**: lines 1431–1441 — if `submitted_at` is set
   and `idem_in == prior_idem`, a 200 is returned. But `idem_in` here is
   `request.headers.get("idempotency-key") or ""` — **not** stripped, **not**
   the sha256 fallback. An attacker can never collide their idem key with the
   stored one because the storage path uses the strip + fallback derivation.
   So this check is dead code in practice.

**Suggested fix**: a small refactor that consolidates the derivation:

```python
def _derive_idempotency_key(request: Request, response_id: int, payload_json: str) -> str:
    raw = (request.headers.get("idempotency-key") or "").strip()
    if len(raw) >= 16:  # accept supplied key only if it looks intentional
        return raw
    return hashlib.sha256(f"{response_id}|{payload_json}".encode()).hexdigest()
```

Then use the same function in both the already-submitted check and the storage
path. This makes the replay path actually testable.

---

### H6 — `create_action` does not validate `status` field

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:2007`

```python
"status": (body.get("status") or "accepted").strip(),
```

`update_action` (line 2044) validates against
`{"proposed", "accepted", "rejected", "done"}`, but `create_action` accepts
any string. An HR user can create actions with `status="custom_label"`. The
loop-closing card filter is `status="accepted"`, so attacker-supplied labels
just don't show up — but the next engineer who adds a status-aware feature
will trip on the missing whitelist.

**Suggested fix**: same whitelist as update:

```python
status = (body.get("status") or "accepted").strip()
if status not in ("proposed", "accepted", "rejected", "done"):
    raise HTTPException(status_code=400, detail="Invalid status.")
```

---

### H7 — `create_action`: no length cap on user-supplied text fields

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1941–1949, 2003–2009`

`suggested_action_text`, `cohort_label`, `finding_summary`, `next_pulse_question`,
and `goal_title` are accepted with `.strip()` but no length validation. An HR
admin can paste a 10MB string into `suggested_action_text`; the loop-closing
endpoint then ships that 10MB string in every employee's `/my-loop-closing`
response.

The Notification table imposes a 200/1000-char cap on its title/body
(`notifications.py:80–82`), but the engagement_actions table has no cap — and
its rows feed both HR and employee views.

**Suggested fix**:

```python
from hr_advisory.api.routers._helpers import MAX_NAME_LENGTH, MAX_TEXT_LENGTH, _validate_text_length

_validate_text_length(suggested_action_text, "suggested_action_text", MAX_TEXT_LENGTH)
_validate_text_length(cohort_label, "cohort_label", MAX_NAME_LENGTH)
_validate_text_length(finding_summary, "finding_summary", MAX_TEXT_LENGTH)
_validate_text_length(next_pulse_question, "next_pulse_question", MAX_TEXT_LENGTH)

goal_title = (body.get("goal_title") or f"Engagement action: {suggested_action_text[:80]}").strip()
_validate_text_length(goal_title, "goal_title", MAX_NAME_LENGTH)
```

Same for `update_action` patch fields — the whitelist allows
`suggested_action_text` and `next_pulse_question` updates with no length check.

---

## MEDIUM (fix in next iteration)

### M1 — `Goal` created with HR's own employee_id; access control inconsistent

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1962–1991`

`create_action` with `create_linked_goal=true` creates a Goal with
`employee_id = creator_emp.id` (the HR creator's own employee record). The
brief's concern #8 asks two questions:

1. **Could this leak HR's identity into a cohort-level context?** Slightly. The
   loop-closing card payload reads
   `linked_goal_label = goal.get("title", "")` — so an employee viewing their
   loop-closing card sees the goal title that points at HR's personal goal
   list. Title is HR-supplied, so they could write something like "HR's growth
   plan for Engineering" — fine — or accidentally leave the
   default `"Engagement action: <truncated suggested text>"`. No employee_id
   leakage in the response, but the Goal **row** is owned by HR's
   employee_id, which means in HR's `/goals` list it shows up as one of HR's
   personal goals. That's likely surprising UX, not a security defect.

2. **Does Goal access control verify the requesting user can read goals
   belonging to HR's employee_id?** The Goals router wasn't part of this
   audit but the model has `company_id` + `employee_id` + `manager_id`
   columns. If the Goals router scopes by `company_id` only, every employee
   in the company could read HR's auto-created action goals — they'd see
   the title and description (which contains
   `f"Auto-created from engagement survey #{survey_id}. Cohort:
{cohort_label or 'all'}. Finding: {finding_summary or 'low engagement'}."`
   — a low-key cohort-finding leak). Worth confirming.

**Suggested fix**:

- Set `manager_id = user_id` and `employee_id = 0` for engagement-action goals
  so they're identified as company-level rather than personal. OR
- Add a `source: "engagement_action"` field on Goal and filter those out of
  /goals/me listings. OR (simplest)
- Don't auto-create a Goal at all; just store `linked_goal_id=0` and let HR
  open the action and manually link it.

The third option matches the round-3 product intent best — the action loop is
about HR ownership, not making "engagement" personal goals on HR's profile.

---

### M2 — `engagement_secret` plaintext fallback in seed script vs encrypted in service path

**File**: `scripts/backfill_demo_engagement_surveys.py:204–222`

```python
secret_v1 = secrets.token_hex(32)
cur.execute(
    "UPDATE companies SET engagement_secret_v1 = %s, "
    "engagement_secret_active_version = 1 WHERE id = %s",
    (secret_v1, company_id),
)
```

The seed stores **plaintext** hex in `companies.engagement_secret_v1`. The
service path (`engagement_pseudonym.get_or_create_company_secret`) stores
**Fernet-encrypted** ciphertext.

Decrypt path (`security/encryption.py:40–51`):

```python
def decrypt_field(value: str) -> str:
    ...
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        # Value might not be encrypted (migration scenario) — return as-is
        return value
```

The bare `except` "value might not be encrypted" branch silently returns the
input. So both paths "work" — but with three concerning side-effects:

1. The plaintext seed secret is computed by the seed script AND stored as
   plaintext. If the seed runs on production demo data and the demo company is
   later used by real users, the company's pseudonym secret has a much weaker
   storage guarantee than other companies' secrets.
2. `decrypt_field`'s fallback masks legitimate decryption failures (e.g. a
   `SALARY_ENCRYPTION_KEY` rotation that wasn't migrated). Anyone who later
   tries to debug "why are pseudonyms wrong after we rotated the encryption
   key" will hit this silent path.
3. Once the seed has stamped plaintext, subsequent `update` calls from the
   service won't re-encrypt (the existing value is non-empty, so the service's
   lazy-generation path doesn't fire). The plaintext stays plaintext for the
   life of the demo company.

**Brief's concern #2 sub-questions**:

- Is the plaintext secret ever exposed in API responses? **No** — `Company` is
  not exposed via any read API I found. The dashboard reads via `/auth/me`
  which surfaces a small allow-listed shape. Confirm by grepping for
  `engagement_secret` in `*.py` (only the model, the service, and the seed
  reference it).
- Is the seed-script's plaintext-storage acceptable? **No, not for production
  demo data.** Acceptable for ephemeral local dev only. The fix is two lines:
  call `encrypt_field` from the seed (after importing the same module the
  service uses) so the seed and service stay symmetric.
- Does logging ever leak the secret? **No** — the
  `engagement_secret_decrypt_failed` and `engagement_secret_generated` log
  events both omit the secret value. Good.

**Suggested fix** (in the seed script):

```python
from hr_advisory.security.encryption import encrypt_field

secret_v1_plain = secrets.token_hex(32)
secret_v1_stored = encrypt_field(secret_v1_plain)
cur.execute(
    "UPDATE companies SET engagement_secret_v1 = %s, "
    "engagement_secret_active_version = 1 WHERE id = %s",
    (secret_v1_stored, company_id),
)
# Use secret_v1_plain locally for the _hmac_pseudonym calls;
# the service path will decrypt secret_v1_stored on read.
```

Also: tighten `decrypt_field`'s silent fallback. Logging at WARNING when
decryption fails (instead of silent pass-through) catches the encryption-key
rotation case at the cost of being slightly noisy in dev with no key set.

---

### M3 — Cohort preview leaks tenant employee names without rate-limit

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:586–682`

`preview_cohort` returns up to 8 employee names per call. It's rate-limited at
30/min/user. An attacker with HR credentials in a single-tenant deployment can
enumerate the entire active employee roster by varying `filter_spec` (e.g.
sweeping `departments=["Engineering"]`, `["Sales"]`, etc.) at 30 calls/minute —
that's 240 names/minute. Not exploitable for cross-tenant data, but a single
compromised HR account can dump the whole employee directory by name in
seconds.

The bigger issue is that 30/min for a leakage-shaped endpoint is generous. The
analogous endpoints (`hr-calculator-specialist` says calculators are
30/min/500/hr) are appropriate for compute, less so for PII enumeration.

**Suggested fix**: drop preview to 10/min/100/hr OR move name resolution off
the preview endpoint — preview returns count + anonymity_safe + warnings only,
and a separate `/cohorts/preview/sample` endpoint with stricter rate limit
returns names.

---

### M4 — Manager view doesn't audit-log access to subordinates' aggregated data

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1782–1903`

`get_team_aggregate` returns themes + Likert avg + eNPS for the manager's
direct + indirect reports, gated on n>=5 with self-exclusion. The aggregate is
anonymity-safe, BUT for small teams just above the threshold (n=5–8 reports), a
malicious manager who knows the cohort attributes can correlate aggregated
themes with specific employees they manage.

There's no audit log of who pulled the team aggregate, when, or for which
survey. Round-2 H12/Z16's PDPA logging hook (already noted in H3) should also
fire here.

**Suggested fix**: log a category like `engagement_team_aggregate_view` when
`is_visible=True`. data_subject_id=0 (the aggregate isn't tied to one subject
but to the manager's subtree).

---

### M5 — Submit handler returns generic 400 message; could leak validation state

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1499–1504`

```python
missing = [q for q in required_q_ids if q not in body]
if missing:
    raise HTTPException(
        status_code=400,
        detail="Invalid request",
    )
```

The detail string is generic ("Invalid request") — this is correct for not
leaking template structure to attackers. But there are inconsistent error
messages elsewhere in the same handler:

- Line 1457: `"Invalid request"` (good)
- Line 1462: `"Payload too large."` (acceptable — attacker can already infer
  the 50KB limit)
- Line 1503: `"Invalid request"` (good)
- But line 1441: `"Already submitted."` — leaks state to a non-owner. Combined
  with the line 1444 `"Not your response."` 403, an attacker enumerating
  response_ids learns the difference between "exists, submitted by someone
  else" (409 → "Already submitted") vs "exists but not yours" (403 → "Not
  your response") vs "doesn't exist" (404).

This is response-ID enumeration via timing/status difference. Single-tenant
threat model makes this low-priority but worth tightening.

**Suggested fix**: collapse 403 + 409 + 404 into a single `404 "Not found"` for
non-owners; the legitimate owner of an already-submitted response should
already know it's submitted (their own UI shows it) so the 409 path isn't
needed at the API boundary.

---

### M6 — Race condition: `notifications.bulk_create_engagement_pending` runs outside the launch lock

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1026–1040`

The launch lock (`_LAUNCH_LOCKS`) is released before the notification fanout
(intentional, per Z10 saga shape). The fanout's `try/except` swallows all
exceptions and only logs a warning. In single-process Uvicorn this is fine,
but with multiple workers it means:

- Worker A acquires the lock, creates survey + responses, releases the lock,
  then crashes (OOM, SIGTERM, segfault) before fanning out notifications.
- Worker B never sees the lock contention because it's already released.
- The user gets a 500 (or hung connection); responses exist; no notifications
  exist.
- Re-running the launch creates a duplicate survey because the lock-protected
  overlap check doesn't see the existing partial-launch as "active" until
  responses exist with `submitted_at IS NOT NULL` (the
  `find_overlapping_surveys` filter is "responses with employee_id ≠ 0 and not
  voided" — see line 527–533 — which matches the partial state).

This isn't an exploit, but it's an availability bug that won't show until the
first crash mid-launch.

**Suggested fix**: keep notification fanout inside the lock. The slow-down
(maybe 5–10 seconds for 200 notifications) is acceptable since launches are
rare; alternatively, write a `survey.email_delivery_status="partial"` column
when fanout fails so the UI surfaces the half-state.

---

### M7 — Theme tagger doesn't sanitise multi-pick reasons (`reason_keys`)

**File**: `src/hr_advisory/services/theme_tagger.py:71–77`

```python
for key in reason_keys:
    reasons = payload.get(key) or []
    if isinstance(reasons, list):
        for r in reasons:
            if r is None:
                continue
            tags.add(str(r).strip().lower())
```

The free-text path correctly calls `sanitise_input` (line 89). The reasons
path does not. So a multi-pick payload like `q3_reasons:
["<script>alert(1)</script>"]` ends up stored verbatim in
`response.themes` JSON, then surfaced in:

- HR's `/surveys/{id}/aggregate` → `themes_tally`
- Manager view's `themes` array
- Loop-closing card's `top_theme`

React's auto-escape catches the obvious script tag at render time, but other
rendering paths (e.g. an admin CSV export, an LLM prompt that interpolates
the tag) wouldn't. Also worth noting: the multi-pick input is
template-defined (Q12 ships closed options like "manager", "comp", "growth"),
so a benign client always sends safe values. But the API doesn't enforce
that the values come from `q.options`; submit validation in
`submit_my_response` doesn't cross-check multi-key values against the
template's `q.options` list either.

**Suggested fix**: sanitise the reason values too:

```python
for r in reasons:
    if r is None:
        continue
    cleaned = sanitise_input(str(r).strip().lower())
    if cleaned:
        tags.add(cleaned)
```

And consider validating multi-pick answers against the question's options at
submit time (currently line 1496–1497 just accepts whatever the client sends).

---

### M8 — `_count_submitted_responses` is O(N) called O(N) times in `list_surveys`

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:1067–1082, 1054–1064`

Every survey in the list calls `_count_submitted_responses(sid)`, which fetches
up to 5000 responses and counts in Python. For a company with 100 historical
surveys × 200 responses each, that's 20,000 rows pulled per list page. The
front-end calls this on `/engagement` which becomes the engagement
hero. There's no rate limit on `list_surveys`.

This is a DoS amplification vector: a single GET pulls O(surveys × responses)
rows. An authenticated attacker (any HR admin) can hit `/surveys` repeatedly
to saturate the backend pool.

**Suggested fix**: aggregate counts in one query rather than N. With direct
SQL it's a single `SELECT survey_id, COUNT(*) FROM
engagement_survey_responses WHERE survey_id = ANY(...) AND submitted_at IS
NOT NULL AND is_void = false GROUP BY survey_id`. Or add the rate limit to
match cohort preview's 30/min.

---

## LOW (consider fixing)

### L1 — `consent_notice_version` truncated hash collision space (8 hex chars = 32 bits)

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:953–959`

```python
consent_notice_version = (
    DEFAULT_CONSENT_NOTICE_VERSION
    + ":"
    + hashlib.sha256(consent_notice_text.encode("utf-8")).hexdigest()[:8]
)
```

8 hex chars = 4.3 billion possibilities. PDPA audit defends against "this
employee saw consent notice X" — if the hash collides for two distinct
notices, the audit log links a response to the wrong notice text. Birthday
bound is ~65k notices before a 50% collision risk. For a single tenant this
is fine forever; defense-in-depth says use 16 chars.

**Suggested fix**: bump to `[:16]` (~10^19 possibilities, no collision risk).

---

### L2 — `compute_pseudonym` validates but doesn't constant-time the secret

**File**: `src/hr_advisory/services/engagement_pseudonym.py:74–81`

```python
try:
    secret_bytes = bytes.fromhex(secret_hex)
except ValueError as exc:
    raise ValueError("secret_hex must be valid hex.") from exc
```

The error message reveals "valid hex" vs "any other failure" — but the secret
is never compared, only used as the HMAC key. No timing side channel here.
Note for completeness: the surrounding code uses `hmac.new(secret_bytes,
message, hashlib.sha256).hexdigest()` correctly. ✓

If pseudonym verification is added later (e.g. "is this stored pseudonym
valid for this employee?"), the comparison MUST use `hmac.compare_digest()`
per `.claude/rules/trust-plane-security.md` MUST NOT Rule 1.

---

### L3 — JWT `make_token` allows arbitrary `kind` from caller

**File**: `src/hr_advisory/api/routers/_survey_tokens.py:53–79`

```python
def make_token(record_id, company_id, *, kind=EXIT_TOKEN_KIND, ...):
```

The `kind` parameter is keyword-only with a sane default, but no allow-list.
A future caller could pass `kind="admin"` or `kind="../etc"` and produce a
token that — if `decode_token` is later called with that exact kind — would
verify. Today no live code path mints anything but `"exit"`, so unexploitable.

**Suggested fix**: maintain a `_VALID_KINDS = {"exit", "engagement"}` and
assert `kind in _VALID_KINDS` at mint time.

---

### L4 — `_resolve_employee_for_user` returns `rows[0]` without checking length consistency

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:738–745`

```python
def _resolve_employee_for_user(user_id, company_id):
    rows = dataflow_crud.list_records(
        "Employee",
        {"user_id": int(user_id), "company_id": int(company_id)},
        limit=10,
        cache_ttl=0,
    )
    return rows[0] if rows else None
```

If a User somehow has two Employee rows in the same company (data bug), this
silently picks the lowest-ID one. The submit handler then matches "Not your
response" or "your response" against the wrong record. Defense-in-depth: log
a warning if `len(rows) > 1`.

---

### L5 — `_build_response_cohort_attributes` per-process hash for manager_id

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:765–789`

```python
manager_hash = hashlib.sha256(
    f"mgr:{int(manager_id)}".encode("utf-8")
).hexdigest()[:16]
```

`hashlib.sha256` is not "per-process stable" as the docstring claims — it's
deterministic across all processes. The hash output is identical given the
same input. The comment is wrong but the intent (stable for trend grouping,
not random) is achieved.

The minor concern: `f"mgr:{N}"` with sha256 truncated to 16 chars is
essentially a (slow) lookup table — anyone who knows the
`manager_hash` and the company's manager_id space can brute-force the
mapping in milliseconds (just hash every manager_id from 1 to 10,000). So the
hash provides zero re-identification protection beyond cosmetic.

**Suggested fix**: use HMAC keyed by the engagement secret:

```python
import hmac as hmac_mod
secret = engagement_pseudonym.get_or_create_company_secret(company_id)
manager_hash = hmac_mod.new(
    bytes.fromhex(secret),
    f"mgr:{int(manager_id)}".encode("utf-8"),
    hashlib.sha256,
).hexdigest()[:16]
```

This makes brute-force infeasible without the secret. Fix the docstring to
match.

---

### L6 — `find_overlapping_surveys` is O(surveys × responses) per launch

**File**: `src/hr_advisory/api/routers/engagement_surveys.py:491–541`

For each open survey, fetches all its responses. For 50 historical surveys
this is 50 separate `list_records` calls. Today fine; future scale concern.
Single SQL query with `JOIN` would replace this. Rate-limited via the launch
endpoint (60/hr/user) so DoS surface is bounded.

---

### L7 — Notification "metadata_json" stored unvalidated

**File**: `src/hr_advisory/services/notifications.py:87`

```python
"metadata_json": json.dumps(metadata) if metadata else "",
```

If `metadata` contains non-serialisable values, `json.dumps` raises and the
notification creation fails. The fanout's `try/except` swallows it and the
employee gets no notification. Single-tenant concern; today the only callers
pass `{"response_id": int}` which is fine.

---

## INFO (non-issues confirmed safe)

### I1 — `submit_my_response` anonymity-tier branching is correct

Per the brief's concern #6: I traced lines 1539–1556 and confirm:

- `identified` → `employee_id` unchanged, `pseudonym=""`, `version=0`. ✓
- `pseudonymous` → `employee_id=0` AND `pseudonym=hmac(...)` AND `version=1`. ✓
  Note: secret is resolved BEFORE zeroing employee_id (line 1546 vs 1552). ✓
- `anonymous` → `employee_id=0`, `pseudonym=""`, `version=0`. ✓

The order is correct in all three branches. No tier writes both `employee_id`
and a pseudonym in a way that would re-identify.

### I2 — Tenant isolation: every endpoint reads `company_id` from JWT and filters

Per concern #5: I checked every handler in `engagement_surveys.py`. All of them:

- Resolve `company_id` via `_resolve_company_id(current_user)` (raises 400 if
  the JWT has no company).
- Filter list endpoints by `{"company_id": company_id}`.
- Verify single-record reads via `int(record.get("company_id") or 0) !=
company_id` → 404 (not 403, to avoid leaking existence).

Specific spot-checks:

- `get_template`, `get_cohort`, `get_survey`: filter on read. ✓
- `update_template`, `update_cohort`, `update_action`: read existing first +
  filter. ✓
- `create_action`: reads parent survey first + filter. ✓
- `list_responses`: reads parent survey first + filter. ✓
- `get_aggregate`, `get_suggested_actions`: reads parent survey first +
  filter. ✓
- `render_my_response`, `submit_my_response`: filter on response company_id
  AND verify employee owns the response (line 1372/1444). ✓
- `my_pending`, `my_history`: filter responses by company_id, then by
  employee_id from `_resolve_employee_for_user`. ✓
- `get_team_aggregate`: scope is `manager.direct + indirect` from
  `Employee.list_records({"company_id": company_id})`. ✓
- `get_loop_closing` → `compute_loop_closing_payload(company_id)`: scoped. ✓

The `find_overlapping_surveys` helper (line 491) takes `company_id` as
argument and filters; never called with anyone else's company_id.

### I3 — Seed script SQL is parameterised throughout

Per concern #10: every `cur.execute(...)` in
`scripts/backfill_demo_engagement_surveys.py` uses `%s` placeholders + a
params tuple. No f-string interpolation of user-controlled values. The two
f-strings on line 281 (`pulse_name`) and 387 (`open_name`) interpolate
script-controlled values (timestamps + offsets) into a Python string before
binding it as a parameter — not into the SQL itself. Safe.

### I4 — Pseudonym determinism preserves trend continuity

`compute_pseudonym(secret, employee_id, survey_id)` is keyed by survey_id
specifically — so the same employee gets a different pseudonym in each
survey. This is the right anonymity property: cross-survey trend joins
require the secret + employee_id, which only the company holds. An attacker
with raw response rows but not the secret can't link two pseudonyms to the
same employee.

### I5 — `void_pending_engagement_responses` correctly filters submitted responses

Per the brief, Z04 says "only responses with `submitted_at IS NULL` are
voided". `engagement_termination.py:55–59`:

```python
pending = [
    r for r in rows
    if r.get("submitted_at") is None
    and not r.get("is_void")
]
```

✓ Submitted responses stay in the aggregate.

### I6 — `Notification.mark_resolved` verifies user_id ownership

`notifications.py:166–198` correctly checks `int(row.get("user_id")) ==
int(user_id)` before resolving. An attacker can't resolve another user's
notifications.

### I7 — Rate limits: per-user identifiers, not per-IP

All `check_rate_limit` calls use `user_id` as the namespace
(`f"action:{user_id}"`). A single attacker with a botnet can't bypass by
rotating IPs. ✓

### I8 — Submit handler caps payload at 50KB

Line 1462: `if len(payload_json) > 50_000` — appropriate cap. The 5x-larger
cap on exit interviews (20KB) is per-handler. Engagement's 50KB allows a
larger free-text answer; reasonable.

### I9 — Trust-plane / EATP patterns not applicable

The trust-plane / EATP patterns in `.claude/rules/trust-plane-security.md`
apply only to `packages/trust-plane/**` and `packages/eatp/**`. None of the
engagement-survey code is under those paths.

### I10 — `decrypt_field` silent-fallback caveat

Already covered in M2. The behaviour is intentional ("migration scenario")
but is the kind of "silent fallback" called out in
`.claude/rules/zero-tolerance.md` ABSOLUTE RULE 3. Not introduced by this
work, but flagged because the engagement secret depends on this path.

---

## Totals

| Severity | Count |
| -------- | ----- |
| CRITICAL | 0     |
| HIGH     | 7     |
| MEDIUM   | 8     |
| LOW      | 7     |
| INFO     | 10    |

## Pre-merge recommendation

The brief's CRITICAL-flagged paths (SQL injection in `_list_records_direct_sql`
filter keys, pseudonym secret leakage, tenant isolation, anonymity-tier
branching, idempotency replay) are all currently safe given how callers use
them. None of them are CRITICAL by exploitability today.

The two findings that should land before this ships to anyone outside dev:

1. **H1** — add `_validate_identifier` to `_list_records_direct_sql`. ~5 LOC.
   This isn't theoretical — it converts a class of injection from
   "depends-on-caller-discipline" to "structurally impossible".

2. **H3** — wire `_log_pdpa_access` into `list_responses`. The PDPA audit
   trail is regulatory, not nice-to-have. ~10 LOC if you keep it inline,
   ~30 if you extract a shared module (recommended).

H2 (CSRF guard tightening) is also worth doing now because it's the kind of
finding that becomes painful to fix later when the JWT-vs-cookie path
diverges further.

The remaining HIGH (H4–H7) are quality issues — defense-in-depth and input
validation. Land them in the next iteration.

The MEDIUM and LOW items are tracked for next iteration. M1 (Goal access
control inconsistency) deserves a 5-min sanity check on the Goals router
before this merges, just to confirm the cohort-finding leak isn't already
live.
