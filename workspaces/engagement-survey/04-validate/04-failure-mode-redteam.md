# 04 — Failure-Mode + Concurrency + Systemic Red-Team

Round-2 deep-analyst review of the engagement-survey feature implementation
(M0–M6). Targets the 11 specific failure-mode classes flagged in the brief
plus systemic issues uncovered while reading the code paths.

Findings tagged `[H]` / `[M]` / `[L]` per round-2 convention. Each finding
names the failure scenario, the offending code path, and a concrete fix.

---

## 1. DataFlow caching workaround in `services/dataflow_crud.py`

### F1.1 — `_list_records_direct_sql` builds SQL by f-string with table + column names — column names from `filter_dict` are NOT validated `[H]`

**Scenario:** `_list_records_direct_sql` interpolates filter keys (column
names) directly into the WHERE clause via f-string:

```python
clauses.append(f"{k} IS NULL")
clauses.append(f"{k} = %s")
```

`k` comes from `filter_dict`. Every call site I audited passes a literal
dict (`{"company_id": ...}`) so this is currently safe in practice — but
there is **no defence** against a future caller that lets user input flow
into a filter key. This is a latent SQL-injection vector waiting for a
"refactor that helped".

**Code path:** `services/dataflow_crud.py:144-150`.

**Fix:** Add an identifier whitelist in `_list_records_direct_sql`:

```python
_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
for k in filter_dict.keys():
    if not _IDENT_RE.match(k):
        raise ValueError(f"Invalid filter column name: {k!r}")
```

This mirrors `infrastructure-sql.md` Rule 1 (`_validate_identifier`) and
is required for the same reason. The table name from `_model_to_table()`
should likewise be re-validated even though it's derived (defence in depth
— a future override could be malicious).

### F1.2 — Table-name pluralisation will silently break for non-conforming models `[H]`

**Scenario:** `_model_to_table()` applies a heuristic snake_case + simple
plural rule. Models that DataFlow names differently (because the
`@db.model` decorator computed a different table name, or because of
acronyms / odd suffixes) silently route to the wrong (or non-existent)
table. The exception is swallowed at line 167-177 and an empty list is
returned — caller cannot distinguish "no rows" from "table doesn't
exist".

Concrete risks in this codebase:

| Model          | Heuristic produces | DataFlow actual | Status       |
| -------------- | ------------------ | --------------- | ------------ |
| `Company`      | `companys`         | `companies`     | **MISMATCH** |
| `Goal`         | `goals`            | `goals`         | OK           |
| `Notification` | `notifications`    | `notifications` | OK           |
| `Employee`     | `employees`        | `employees`     | OK           |

The `y → ies` rule in line 115-116 specifically tests `endswith("y")`
and excludes vowel-y endings. `Company` ends in `y`, the preceding char
is `n` (consonant), so the heuristic produces `companies`. **OK on
inspection** — but this only works because of an English orthography
coincidence. Any model whose name ends in odd patterns (`Status`,
`Address`, `Box`, `Quiz`, `Person → people`, `Mouse → mice`) will fall
off. `_TABLE_NAME_OVERRIDES` is empty.

**Fix (must do):**

1. Populate `_TABLE_NAME_OVERRIDES` for every model that uses
   `_list_records_direct_sql`. List them out (currently:
   `EngagementSurveyResponse`, `EngagementSurvey`, `Notification`,
   `Employee`, `Company`, `Goal`).
2. Replace the silent `except Exception → return []` (line 167-177)
   with: log error AND raise. Caller business logic depends on
   distinguishing "no rows" from "broken table mapping". This is
   especially severe for the launch overlap check (`F2.2` below) where
   "no overlap rows" means "go ahead, launch the survey".

**Defence in depth:** at startup, run an assertion loop that calls
`_model_to_table()` for every registered model and verifies the table
exists in `pg_tables`. Fail fast at boot, not at first user request.

### F1.3 — Connection-pool exhaustion via psycopg2 sync connections `[M]`

**Scenario:** Every `_list_records_direct_sql` call opens a fresh
`psycopg2.connect(DATABASE_URL)`, executes one query, closes. These
connections are **separate from DataFlow's asyncpg pool** — they count
against `Postgres.max_connections=100` directly, on top of DataFlow's
`pool_size=70 + max_overflow=35`.

Worst case: a launch fan-out for a 1000-employee company calls
`_list_records_direct_sql` for `bulk_create_engagement_pending`'s
post-write verification (each cohort_resolver call, each notification
fanout) — under load this can trip `FATAL: too many connections`.

**Code path:** `services/dataflow_crud.py:138-180`.

**Fix:** Use a small dedicated psycopg2 pool (e.g.
`psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10)`) created
once at module import. Acquire / release per call. Caps the blast
radius regardless of caller volume.

### F1.4 — `cache_ttl=0` path silently degrades on connection failure `[M]`

**Scenario:** Lines 167-177 catch ANY exception and return `[]`. The
`/my-pending` endpoint, the manager aggregate, and the launch overlap
check all rely on this list being authoritative. Returning `[]` on
DB unavailability means:

- `/my-pending` shows "you have no surveys" when DB is down.
- The launch overlap check decides "no overlap, launch".
- The cohort resolver returns an empty cohort, then a survey launches
  with zero responses (fan-out is empty).

**Fix:** Catch only the narrow set of expected exceptions (connection
errors → re-raise as a typed `DataAccessError`; programming errors like
table-not-found → also re-raise). Don't paper over them with `[]`.

---

## 2. Per-company launch lock (Z06)

### F2.1 — `threading.Lock` does not protect across uvicorn workers `[H]` _(known limitation, but undocumented)_

**Scenario:** `_LAUNCH_LOCKS: dict[int, threading.Lock]` is in-process
state. Production runs typically use multiple uvicorn / gunicorn
workers (`--workers 4`). The lock is per-process — workers race against
each other for the overlap check.

**Code path:** Per the brief, this is in
`services/engagement_surveys.py` (location confirmed in handler-side
service), and known.

**Fix (one of):**

1. Document explicitly in `deploy/deployment-config.md` that this app
   MUST run with `--workers 1` until DB-backed locking ships.
2. Replace with a Postgres advisory lock keyed by company_id:
   ```sql
   SELECT pg_try_advisory_xact_lock(hashtext('engagement_launch_'||$1))
   ```
   Held for the duration of the transaction. Cross-worker safe.
3. Add a DB-level partial unique constraint on
   `engagement_surveys (company_id, status='open')` to enforce "at most
   one open survey per company" at the schema level — defence in depth
   against any racing worker that bypasses the lock.

Recommend (2) + (3) together. (1) alone is fragile — operators forget.

### F2.2 — Overlap check inside the lock still runs through cached path unless `cache_ttl=0` is explicit `[H]`

**Scenario:** The lock guarantees one launch at a time _per process_,
but if the overlap check uses DataFlow's cached list and a previous
process's launch was just-committed-but-not-yet-cache-invalidated, the
fresh launch sees no overlap and proceeds.

**Verification:** Audit the launch handler to confirm it reads the
overlap check via `dataflow_crud.list_records(..., cache_ttl=0)`.
Otherwise the lock is solving a problem that's already happened (DB
race), not a problem that's still happening (cache staleness).

**Fix:** Add a regression test that:

1. Launches survey A (commits).
2. Within the same worker process, immediately calls the overlap check.
3. Asserts the overlap check sees survey A.

Without `cache_ttl=0` this test fails — which is the bug.

### F2.3 — `_LAUNCH_LOCKS` dict grows without bound `[L]`

**Scenario:** One entry per company_id, never evicted. Acceptable for
single-tenant Arbor demo. Not acceptable for multi-tenant where
company_id space can grow to millions.

**Fix:** Cap with an `OrderedDict`-based LRU, default 10000, per
`infrastructure-sql.md` Rule 7. Or replace with the Postgres advisory
lock above (no in-memory state needed).

---

## 3. Saga rollback at launch (Z09)

### F3.1 — `bulk_create_engagement_pending` partial-fanout state is invisible to the user `[M]`

**Scenario:** `notifications.py:111-145` catches per-row exceptions,
logs a warning, increments `created` only on success. Returns
`(created, target)`. **But the launch handler must record this on the
survey row** so HR can see "fanned out 870 of 1000 — 130 failed".
Currently `email_delivery_status` is hardcoded to `"pending"` /
`"complete"` — there is no `"partial"` state.

**Code path:** `services/notifications.py:111-145`; consumer is the
launch handler.

**Fix:** Extend the field to `"pending" | "complete" | "partial"`. Set
`partial` when `created < target`. Surface on the survey detail page
with an "Resend failed" button. This is a real ops requirement —
launches will hit transient errors.

### F3.2 — No retry on transient notification failures `[M]`

**Scenario:** A connection blip during fan-out skips notifications
permanently. Per `seeding.md` Rule 4, transient failures should retry
with exponential backoff. `bulk_create_engagement_pending` does not
retry.

**Fix:** Wrap each `create_notification` in a tiny retry helper (max 3
attempts, 0.5/1.5/4.5s backoff, capped at 30s). The same helper
already exists in `seed_demo_data.py` per the rules — extract to
`services/retry.py` for reuse.

### F3.3 — No saga rollback if the response-row bulk insert fails midway `[H]`

**Scenario:** Launch handler creates Survey row → bulk-creates response
rows → fans out notifications. If the response-row insert fails halfway
(50 of 1000 inserted, then a constraint violation), the Survey row is
already committed and the user sees a half-launched survey with 50
respondents and 950 missing.

**Fix (one of):**

1. Wrap Survey-create + response-row-bulk-create in a single
   transaction (preferred — atomic). Notifications fan out **after**
   commit.
2. If single-transaction is infeasible due to ORM constraints, add a
   compensating action: on response-row bulk-create failure, set the
   Survey row to `is_archived=True, launched_at=NULL` and emit a
   warning telemetry event. Retry from a clean slate.

Currently neither is in place — this is a real partial-failure hole.

---

## 4. Idempotency on submit (Z08)

### F4.1 — No DB UNIQUE constraint on `idempotency_key` — TOCTOU race `[H]`

**Scenario:** Two parallel POSTs from the same client (browser sent
twice due to a slow network — frontend retried) both pass the
"idempotency check" because neither has stored the row yet:

```
T0 — req A reads: no submitted row exists → proceeds to write.
T0 — req B reads: no submitted row exists → proceeds to write.
T1 — req A writes submitted row.
T2 — req B writes submitted row.
Result: TWO submitted rows for same response.
```

The index alone (no UNIQUE) does not prevent the second insert.

**Code path:** `submit_my_response` in the engagement_surveys router
(per the brief). DB schema for `engagement_survey_responses`.

**Fix:**

1. Add a partial UNIQUE constraint:
   ```sql
   CREATE UNIQUE INDEX uq_engagement_response_idem
   ON engagement_survey_responses (company_id, idempotency_key)
   WHERE idempotency_key <> '';
   ```
2. Catch `psycopg2.errors.UniqueViolation` in the handler and treat it
   as the same-key-replay case → return the existing row.

This is a **must-fix** before launching to a real customer. The current
shape is the textbook double-submit bug.

### F4.2 — `idempotency_key` is empty string for many response rows `[L]`

**Scenario:** The seed script writes `''` for `idempotency_key` on
every seeded row. The submit handler check needs to differentiate
"never had a key" from "matched key". Right now the handler probably
checks `idempotency_key == provided_key` — if both are `''`, this is
true and it returns the wrong row.

**Fix:** Treat `idempotency_key == ''` as "no key" — never match on
empty. Combine with the partial UNIQUE above.

---

## 5. Cohort resolver edge cases

### F5.1 — Employees with `start_date == ""` are silently excluded by tenure filter `[M]`

**Scenario:** `cohort_resolver.py:155-159` (`_tenure_days`) returns
`None` if `start_date` is unparseable. Line 270-271 then `continue`s
in the tenure filter — these employees never match.

For HR running a "new hires (last 90 days)" pulse, an employee with
a missing `start_date` is exactly the population they want to flag —
but the filter silently drops them.

**Fix:** Add an audit log warning at filter time:

```python
if td is None:
    logger.warning("cohort_skip_unparseable_start_date",
                   extra={"employee_id": e["id"], "company_id": company_id})
```

Plus a UI bubble: "3 employees in the cohort have no start_date and
were excluded — fix their profiles or set tenure_min_days=0".

### F5.2 — `departments=["Eng"]` against all-null department field returns empty cohort silently `[M]`

**Scenario:** Per the brief — yes, returns empty set, and the launch
handler would happily launch a survey with target_count=0.

**Code path:** `cohort_resolver.py:213-218`; consumer is the launch
handler.

**Fix:** In the launch handler, after `resolve_cohort` returns, assert
`len(cohort) > 0`. If 0, return HTTP 400 with a meaningful error
("Cohort matches no employees — refine the filter"). Currently the
launch silently produces a useless empty survey.

### F5.3 — Re-hires keep original `start_date` → tenure filter mis-classifies them `[L]`

**Scenario:** Documented in line 152 — re-hires keep their original
hire date. A re-hire who was rehired 3 months ago but originally
started 5 years ago will tenure-filter as a 5-year employee, not a
new hire. Acceptable per the M-finding, but is a known inaccuracy.

**Fix:** Future schema extension to add `latest_rehire_date`. Not P1.
Document in the cohort UI tooltip: "Tenure is measured from the
employee's _first_ hire date".

### F5.4 — Resolver re-runs full company employee scan on every call `[L]`

**Scenario:** Trend endpoint over 24 historical surveys × cohort
resolution per survey = 24 full-company employee scans. Cache the
employee list per request (not module-level — staleness risks).

**Fix:** Move the resolver inside a per-request cache decorator (e.g.
`functools.lru_cache` on a tuple key, or pass the employee list in
explicitly so the caller controls the lifetime). Required for the
performance fix in `F6.1`.

---

## 6. Trend endpoint `/surveys/trend`

### F6.1 — N×M aggregate calls with no caching → p95 budget blown `[H]`

**Scenario:** 24 historical surveys × full aggregate scan (which itself
lists all responses for that survey). Each aggregate call goes through
`cache_ttl=0` direct SQL (per `dataflow_crud.list_records` defaults for
correctness paths). With ~200 responses per survey × 24 surveys = 4800
row reads, plus 24 employee-list scans for cohort resolution if the
trend filters by cohort.

p95 budget was <800ms — easy to blow past on a real customer with 24+
historical pulses.

**Code path:** `engagement_surveys.py:990-1030` per the brief.

**Fix:**

1. Materialise per-survey aggregates into an `engagement_aggregates`
   table on survey close (the closing transition is the natural
   trigger). Trend reads from this table — O(N) row reads, no scans.
2. Until that table ships: short-circuit the trend endpoint to return
   only the **last 6 surveys** (matching the seed) and document the
   budget. 24 is aspirational.
3. Add `EXPLAIN ANALYZE` to logs for trend-endpoint requests in dev so
   regressions are visible.

This is the hardest one to defer — the demo won't fall over with 6
surveys, but a real customer with 24 monthly pulses will.

### F6.2 — `cohort` filter "manager:42" not supported by `_build_aggregate` `[H]`

**Scenario:** Brief flagged this. The trend endpoint accepts a cohort
parameter, but `_build_aggregate` filters only by department,
pass_type, tenure_band — the `manager:42` syntax silently no-ops.
Manager dashboard's "trend for my team" line graph silently shows
the company-wide trend, not the manager's team trend.

**Fix:** Either:

1. Add manager_id_hashed dimension to `_build_aggregate`'s filter set.
   Required for the manager dashboard claim.
2. OR document at the API level that `manager:` is unsupported for
   trend, and remove the UI element until (1) ships.

Recommend (1) — the manager view is a marquee feature.

### F6.3 — Trend across surveys with different cohorts is misleading `[M]`

**Scenario:** Survey 1 polled "all_active". Survey 2 polled "Eng
only". Trend joining them gives "company score 3.7 → Eng score 3.2"
which looks like an 0.5-point drop but is actually a cohort change.

**Fix:** Trend endpoint must filter to surveys with **comparable
cohort_filter_spec** (or at least surface the cohort difference in
the response). Add a `cohort_warning` flag to each trend point.

---

## 7. Manager view self-exclusion (Z26) — **CRITICAL**

### F7.1 — Self-exclusion broken for pseudonymous tier (`employee_id=0` after submit) `[H]`

**Scenario:** Confirmed against the seed script
(`backfill_demo_engagement_surveys.py:362`):

```python
# Pseudonymous-tier insert sets employee_id=0:
"VALUES (%s, %s, 0, %s, 1, ...)"
#              ^—— employee_id zeroed at submit
```

Self-exclusion in the manager-view aggregate filters by
`employee_id != manager_id` on submitted rows. **For pseudonymous
surveys, every submitted row has `employee_id=0`** — so:

- If the manager's own response is in the aggregate, the filter does
  NOT exclude it (0 ≠ manager_id is true; row is INCLUDED).
- The "self-exclusion" claim is silently false.

**This is a real bug**, exactly as the brief flagged.

**Code path:** Self-exclusion logic in
`engagement_surveys.py` (manager team aggregate handler) +
`backfill_demo_engagement_surveys.py:362,497`.

**Fix:** For pseudonymous tier, self-exclusion must use the manager's
**pseudonym** rather than employee_id. Concretely:

```python
manager_pseudonym = compute_pseudonym(secret, manager_employee_id, survey_id)
rows = [r for r in rows if r.get("employee_pseudonym") != manager_pseudonym]
```

This requires the manager-view handler to:

1. Resolve the manager's `employee_id`.
2. Compute the pseudonym for each survey under view (since pseudonym
   is per-survey).
3. Exclude rows matching that pseudonym.

For anonymous tier, self-exclusion is **fundamentally impossible**
(no link from row to identity). The UI must document: "Anonymous
tier surveys cannot exclude your own response — your response is
included in the team average." Show this banner on the manager view.

**Plus:** add a regression test:

```python
def test_manager_self_exclusion_pseudonymous():
    # Manager submits response, then views team aggregate.
    # Aggregate's count must equal (team_size - 1), not team_size.
```

### F7.2 — Direct + indirect reports resolved 2 levels deep only `[M]`

**Scenario:** Per the brief — orgs with 3+ levels of management chain
will have skip-level reports invisible to the senior manager.

**Fix:** Replace fixed-depth recursion with a CTE:

```sql
WITH RECURSIVE reports AS (
  SELECT id FROM employees WHERE reporting_manager_id = $1
  UNION
  SELECT e.id FROM employees e
    JOIN reports r ON e.reporting_manager_id = r.id
)
SELECT id FROM reports;
```

Add a depth limit (e.g. 10) as a safety net against cycles.

### F7.3 — Manager view k-anonymity gate must apply per-tier `[M]`

**Scenario:** Aggregate gates with `n>=5` for pseudonymous (per
docs/round-1). For identified tier, the gate may differ. For anonymous
tier, the gate should be stricter (n>=10?).

**Fix:** Move the threshold into the survey row's
`anonymity_tier` → `min_aggregate_n` mapping. Currently looks
hardcoded.

---

## 8. Theme tagger sanitisation

### F8.1 — HTML-escape interaction with keyword sweep `[L]`

**Scenario:** `sanitise_input` HTML-escapes — `&` becomes `&amp;`. The
default keyword map in `theme_tagger.py:31-38` does not contain `&`,
`<`, `>`, `"`, `'`. After escape:

| Input         | Escaped                | Lowercase           | Matches?                   |
| ------------- | ---------------------- | ------------------- | -------------------------- |
| `<system>`    | `&lt;system&gt;`       | `&lt;system&gt;`    | YES (`system` substring)   |
| `R&D burnout` | `r&amp;d burnout`      | `r&amp;d burnout`   | YES (`burnout` substring)  |
| `"workload"`  | `&quot;workload&quot;` | `&quot;workload...` | YES (`workload` substring) |

Keyword matches via `kw in text_blob` — substring matching, not
boundary-aware. The escapes don't break the matches. **Low
risk in practice** because:

- No keyword in the default map starts with `&`, `<`, `>`, `"`, `'`.
- All examples above still produce the intended theme tag.

**But**: a future keyword map that includes (e.g.) `q&a` would break
because `q&a → q&amp;a`. Document the constraint in the keyword_map
docstring: "keywords must contain only chars that survive HTML escape".

**Fix (low priority):** add a regression test pinning the current
behaviour, and a docstring constraint on `derive_themes` that custom
keyword maps must avoid `& < > " '`.

### F8.2 — Reason-tag path BYPASSES sanitisation `[M]`

**Scenario:** Lines 71-77 take `reason_keys` values "at face value" —
no `sanitise_input` call. If the frontend lets users author free-form
reason tags (e.g. "Other (please specify)"), an attacker can inject:

```python
payload = {"q3_reasons": ["<script>alert(1)</script>"]}
themes = derive_themes(payload)
# Returns ['<script>alert(1)</script>'] — stored, then rendered in
# the manager dashboard.
```

**Fix:** Apply `sanitise_input` to reason tags too, before adding to
the set. Reason tags are user-controlled in many UIs.

### F8.3 — `text_blob.lower()` after sanitisation can cause keyword-pollution `[L]`

**Scenario:** Free-text scan concatenates all parts with `" "` then
lowercases. A keyword that spans a boundary (e.g. `pay` matched
across `... salary | rise ...` → no match) is fine. But a keyword
like `it` would match in any word containing those letters
(`commit`, `it`, `bit`).

**Fix:** Add word-boundary regex for keywords that are short common
substrings. The default map is OK (all keywords are 3+ chars and
specific) but the contract for custom maps should be documented.

---

## 9. Termination sweep — **CRITICAL**

### F9.1 — Pseudonymous-submitted responses NOT swept (employee_id zeroed at submit) `[H]`

**Scenario:** Confirmed real bug. `void_pending_engagement_responses`
(`engagement_termination.py:47-51`) filters by:

```python
rows = dataflow_crud.list_records(
    "EngagementSurveyResponse",
    {"employee_id": int(employee_id)},
    cache_ttl=0,
)
```

Per the seed script (`backfill_demo_engagement_surveys.py:362,497`),
**pseudonymous-tier responses are written with `employee_id=0`** at
submit time. The termination sweep filters by `employee_id=<term_id>`
— it never finds the pseudonymous-submitted rows.

But also — per Z04 — the sweep voids only `submitted_at IS NULL` rows.
So in practice:

1. Pending pseudonymous responses (`submitted_at IS NULL`) — these
   _do_ still have `employee_id` set (per seed line 437 they're
   written with employee_id intact). **Sweep correctly voids them.**
2. Submitted pseudonymous responses (`submitted_at IS NOT NULL`,
   `employee_id=0`) — Z04 says _don't void these anyway_. **Sweep
   correctly skips them, not because of the filter mismatch, but
   because Z04 wants them kept.**

**So the bug is _latent_, not active.** The sweep happens to do the
right thing because of two compensating defects. But:

- If Z04 ever changes (e.g. new policy: void submitted-but-anonymised
  responses on termination), the sweep breaks silently.
- If the pending-row identity-stripping happens at any point earlier
  than submit (e.g. a future "draft autosave" feature), the sweep
  misses pending pseudonymous rows.
- The current behaviour is not pinned by a regression test.

**Fix:**

1. Add an explicit comment in `engagement_termination.py` that the
   sweep relies on `employee_id` being present on PENDING rows of all
   tiers, and is intentionally blind to submitted-pseudonymous rows
   (per Z04). Cite Z04.
2. Add a regression test that exercises the boundary:
   ```python
   def test_sweep_pending_pseudonymous():
       # Pending pseudonymous response → employee_id intact → swept.
       # Submitted pseudonymous response → employee_id=0 → NOT swept (Z04).
   ```
3. If the design ever inverts (sweep submitted rows too): add a
   second filter pass via `survey_id + cohort_attrs` lookup, since
   `employee_id` is unavailable.

This is a "documented latent bug" — flag prominently for the next
schema change.

### F9.2 — Anonymous-tier sweep gap `[M]`

**Scenario:** Anonymous tier has `employee_id=0` from launch, not just
from submit. The sweep cannot find any anonymous-tier responses for
the terminated employee at all (pending or submitted). Per round-3
design, anonymous responses can't be tied to identity — but pending
anonymous responses _do_ have a target employee_id at launch time
(otherwise the response can't be assigned to a respondent for fan-out).

**Verification:** check whether anonymous-tier response rows zero
employee_id at insert (launch) or at submit. If at launch — the
termination sweep cannot void anonymous-tier pending responses at
all. The terminated employee can still submit if they have the link
saved.

**Fix:** Anonymous-tier pending rows must keep employee_id until
submit (then zero it). Sweep then works for pending rows. Document
loudly.

### F9.3 — Sweep `surveys_affected` count drifts on partial failure `[L]`

**Scenario:** `engagement_termination.py:84-106` computes
`new_count = old + sum(...)` but the sum counts _all pending rows
including failed-update ones_. If 5 voids succeed and 2 fail, the
voided_count gets +7 but only 5 actually voided.

**Fix:** Track the per-survey successful void count locally, sum that
when bumping voided_count.

---

## 10. Demo seed script edge cases — **CRITICAL**

### F10.1 — Idempotency check fires only at `>= 6` — runs twice between 1 and 5 `[H]`

**Scenario:** `backfill_demo_engagement_surveys.py:170-177`:

```python
if existing >= 6:
    logger.info(...)
    return
```

If a previous run inserted partial data (e.g. 3 surveys, then crashed),
re-running creates 6 more for a total of 9. Trend hero shows 9
mismatched pulses. The "demo refresh" seeding rule
(`seeding.md` Rule 1 — idempotency) is violated.

**Fix:** Either:

1. Make the check `existing >= 1 → already seeded, skipping`. Force
   operators to truncate before re-seeding.
2. Make the seed actually idempotent: query for existing engagement
   surveys with a known marker (e.g. `name LIKE 'H% Pulse — %'`) and
   skip inserts that match.

Recommend (2). Add a marker column or a deterministic name pattern
that the seed checks before inserting.

### F10.2 — Plaintext-hex pseudonym secret stored when service path expects ciphertext `[H]` _(works by accident)_

**Scenario:** Confirmed against `engagement_pseudonym.py` and
`security/encryption.py`.

`backfill_demo_engagement_surveys.py:215-220` stores
`secrets.token_hex(32)` directly as the value of
`engagement_secret_v1`. The service path reads via
`get_or_create_company_secret` → `decrypt_field(encrypted)`.

**Why it works in practice (accidental alignment):**

`security/encryption.py:40-51`:

```python
def decrypt_field(value: str) -> str:
    if not value: return value
    f = _get_fernet()
    if f is None: return value         # ← no key configured
    try: return f.decrypt(value.encode()).decode()
    except Exception: return value     # ← decrypt failure returns input
```

So a plaintext-hex value either:

- Returns as-is when `SALARY_ENCRYPTION_KEY` is unset (dev mode).
- Returns as-is when Fernet decrypt raises (because hex isn't valid
  ciphertext).

**But** — if someone fixes `decrypt_field` to fail-loudly (good
security practice — `eatp.md` says fail-closed), the seed-script's
plaintext secret immediately breaks every pseudonym verification. The
seeded pulse data will produce one set of pseudonyms; the running
service computes a different set; the trend join fails silently.

**Fix:** Seed script must call `encrypt_field(new_secret)` before the
UPDATE — same path as the service. Drop the comment that says "for the
seed we store hex-plaintext to keep the demo simple". The plaintext
stand-in is a footgun.

```python
from hr_advisory.security.encryption import encrypt_field
secret_v1 = secrets.token_hex(32)
encrypted = encrypt_field(secret_v1)
cur.execute(
    "UPDATE companies SET engagement_secret_v1 = %s, ... WHERE id = %s",
    (encrypted, company_id),
)
```

### F10.3 — Year-formatting bug for early pulses `[L]`

**Scenario:** Line 281:

```python
pulse_name = f"H{(2026 if i >= 4 else 2025) - 0} Pulse — {launched.strftime('%b %Y')}"
```

Two issues:

1. `(year) - 0` is a no-op. Looks like a typo.
2. Year-vs-half mapping is hardcoded — pulses 0-3 get "H2025", pulses
   4-5 get "H2026". For the actual `launched` date (which was
   `now - timedelta(days=...)` and could span multiple half-years)
   the H-label may not match the date.

**Fix:** Compute H-label from the `launched` date itself:

```python
half = "H1" if launched.month <= 6 else "H2"
pulse_name = f"{half} {launched.year} Pulse — {launched.strftime('%b %Y')}"
```

### F10.4 — Resigned employees still in `active_employees` if their event was logged but `is_active` not flipped `[M]`

**Scenario:** Lines 195 (`active_employees = [e for e in employees if e["is_active"]]`)
and 264-272 (resigned IDs from `employment_events`). The seed
intersects them but uses `e["is_active"]` for the loop bound. If
the demo seed produces an employment_events row but doesn't flip
`is_active=False` on the employee row, the resigned employees end up
in `active_employees` AND in `resigned_ids`. They get LOW
growth-question scores and get included in the engineering trend.

This is desired in the demo (resigners drag the trend down) but is
_incorrect modelling_ — terminated employees shouldn't have current
pulse responses. A real customer running the seed in their tenant
would see resigned employees with submitted responses (anomaly).

**Fix:** Either:

1. Flip `is_active=False` for the resigned employees as part of the
   seed (matching real production termination flow).
2. Use a different mechanism for the trend dip (e.g. low-scoring
   active employees who _will_ resign next quarter, not currently-
   resigned employees).

Recommend (1) — matches production semantics.

### F10.5 — Non-deterministic open-pulse "skip" probability `[L]`

**Scenario:** Lines 450-472:

```python
if rng.random() > 0.78:
    # Skip — they haven't submitted yet
```

`rng` is seeded (`RNG_SEED = 20260507`) so each run is deterministic.
Good. But the fixed seed means every customer's demo data has the
same skip pattern — fine for demo, awkward if any test depends on
"about 78% submission rate" because it's actually whatever the seed
produced.

**Fix:** Add a regression test that pins the actual submission count
the fixed seed produces, so any `RNG_SEED` change is caught.

---

## 11. Pre-existing failures

### F11.1 — Field-name drifts: `OnboardingModule.idx_onbmodule_order` etc. — likely more `[M]`

**Scenario:** The brief flags two field-name corrections:

- `OnboardingModule.idx_onbmodule_order: "order"` → `"sort_order"`
- `OnboardingStep.idx_onbstep_order: "order"` → `"sort_order"`

If two were drifted, there are likely more. `intermediate-reviewer`
would expect a systematic audit:

**Fix:** Run a one-time audit script:

```python
# For every model with index_field references, assert the referenced
# column exists in the model's __dict__ and the migration's column list.
```

Output: list of all (model, declared*field, actual_column) mismatches.
Fix all of them in one pass. A grep for `idx*`field declarations
plus a`model_to_dict_keys` cross-check is enough.

### F11.2 — Model ↔ schema drift not caught at startup `[M]`

**Scenario:** The two columns added (`interview_schedules.google_event_id`,
`onboarding_steps.is_active`) were detected only at runtime when a query
referenced the missing column. Without a startup-time consistency
check, future drifts wait for a user-triggered failure.

**Fix:** Add a `scripts/validate_schema_alignment.py` that:

1. Loads every DataFlow model.
2. Inspects expected columns from the model fields.
3. Queries `information_schema.columns` for each table.
4. Asserts no missing columns AND no extra columns (or warns on extras).

Run as part of CI startup smoke test. Failing fast at deploy time is
much cheaper than a 3am page from a missing-column error.

### F11.3 — Migration files not regenerated to match the new field names `[L]`

**Scenario:** The brief implies the field-name fixes were made on the
model side. If the alembic migration was generated against the OLD
field name, the migration history is now inconsistent with the model.
Fresh DB bootstraps could fail.

**Fix:** Verify by running `alembic upgrade head` on a fresh empty
database, then asserting model→schema alignment via F11.2's script.

---

## Systemic findings (uncovered while reading)

### S1 — `dataflow_crud.list_records` silently returns `[]` on ANY error `[H]`

Same root cause as F1.4 but worth its own header. **Every caller of
`list_records` with `cache_ttl=0`** is exposed to the silent-failure
mode. Find all callers and audit which ones treat `[]` as
authoritative ("no rows, proceed") vs. which would prefer to surface
the error.

The pattern of `try / except Exception → return []` for a function
that's called from auth-critical paths is a **systemic anti-pattern**
across this codebase. Per `no-stubs.md` Rule 3:

> Production code SHOULD NOT silently swallow errors

This applies here. Fix at the helper level — every consumer benefits.

### S2 — No `cache_ttl=0` is the default — implicit footgun `[M]`

**Scenario:** Default value is `cache_ttl=None`, which means "use
DataFlow's cache". Correctness paths must remember to pass
`cache_ttl=0`. Easy to forget on a future addition (e.g. a new
endpoint added by another developer who copy-pastes from a non-
correctness path).

**Fix:** Flip the default to `cache_ttl=0` (correctness over
performance). Add a separate `list_records_cached(...)` helper for the
performance path. Force-explicit caching, default-safe.

### S3 — `_TABLE_NAME_OVERRIDES` dict is empty in production code `[M]`

Per F1.2 — this is a placeholder waiting to bite. Either populate it
with every model used by `_list_records_direct_sql`, or remove the
mechanism entirely in favour of asking DataFlow for the table name
directly:

```python
def _model_to_table(model_name: str) -> str:
    from hr_advisory.models.database import db
    model = db.get_model(model_name)
    return model.__table__.name  # or however DataFlow exposes it
```

### S4 — No global SQL-injection regression test `[L]`

**Scenario:** Per F1.1, future filter dicts could carry user input.
Add a regression test that asserts every public endpoint that
ultimately calls `_list_records_direct_sql` rejects input keys
containing `;`, `--`, `/*`, or whitespace.

---

## Totals + recommendation

| Severity  | Count  |
| --------- | ------ |
| H         | 13     |
| M         | 14     |
| L         | 9      |
| **Total** | **36** |

### H findings (must-fix before customer launch)

1. F1.1 — SQL identifier validation in direct-SQL path
2. F1.2 — Table-name pluralisation gap + silent-empty on table miss
3. F2.1 — Multi-worker lock gap (advisory lock or `--workers 1`)
4. F2.2 — Lock + cache freshness must be tested together
5. F3.3 — Saga rollback for response-row bulk-insert failure
6. F4.1 — UNIQUE constraint on idempotency_key
7. F6.1 — Trend endpoint p95 budget (materialise aggregates)
8. F6.2 — Manager cohort filter unsupported
9. F7.1 — **Manager self-exclusion broken for pseudonymous tier**
10. F9.1 — **Termination sweep: pseudonymous filter mismatch (latent)**
11. F10.1 — Seed script idempotency boundary
12. F10.2 — Seed script secret encryption mismatch
13. S1 — Silent-empty error path in `list_records`

### Recommendation

**Block the M0–M6 sign-off** until the H findings are resolved or
explicitly waived with mitigations. The pseudonymous-tier defects
(F7.1 and F9.1) directly invalidate two of the three round-1 anonymity
invariants — they are the marquee feature of the product, and the
current implementation silently fails to deliver them. The manager
view in particular ships a false promise to users.

The seed-script issues (F10.1, F10.2) will not block the demo (they
work by accident) but will block any customer running their own seed
or tier-2 pseudonym rotation.

Suggested fix order:

1. **F7.1 + F9.1** — anonymity invariants. Add tests first to pin
   the broken behaviour, then fix.
2. **F4.1 + F1.1 + F1.2** — data-integrity / injection foundations.
3. **F3.3 + F2.1 + F2.2** — concurrency / partial-failure paths.
4. **F6.1 + F6.2** — trend endpoint performance + manager filter.
5. **F10.1 + F10.2** — seed script alignment with service path.
6. **S1** — silent-empty error handling pass across the codebase.

Allow ~3-4 days of focused work for items 1-5; item 6 is a sweep
that benefits every future feature on this platform.
