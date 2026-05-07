# Code-Quality Red Team Review — Engagement Survey M0-M6

**Reviewer**: intermediate-reviewer
**Scope**: All M0-M6 changes for the engagement-survey feature

## Summary

Overall the engagement-survey implementation is high-quality, production-ready code. Anonymity invariants are enforced at every layer, security is taken seriously (HMAC pseudonyms, sanitisation before keyword sweep, CSRF guard, idempotency), and the round-1/2/3 redteam findings have been folded back into the code. Test coverage is broad and independent.

## Top 5 fixes before P1 ship

1. **CRITICAL: Direct-SQL list bypass in `dataflow_crud.py:_list_records_direct_sql` is SQL-injection-vulnerable on identifier path** — table name comes from `_model_to_table()`, but if an unsafe model*name is passed (or the override map mis-edited), the f-string `f"SELECT * FROM {table}"` interpolates without validation. Filter clauses likewise interpolate `k` from dict keys: `f"{k} = %s"`. Per `rules/infrastructure-sql.md` Rule 1, validate identifiers via `_validate_identifier()` regex `^[a-zA-Z*][a-zA-Z0-9_]\*$` before interpolation. ~10 LOC fix.

2. **HIGH: `engagement_termination.py` double-counts in voided_count under partial failure** (`engagement_termination.py:94-96`). If 3 of 5 voids succeed, the survey's `voided_count` is still incremented by 5. Fix: track `successfully_voided_by_survey: dict[int, int]` and use that for the bump.

3. **HIGH: Frontend `Stat` component is duplicated 3 times with different styling contracts** — `engagement/page.tsx`, `engagement/team/page.tsx`, `engagement/surveys/[id]/page.tsx`. Two accept `value: string` only; one accepts `value: React.ReactNode`. Three different visual contracts. Extract to `components/engagement/Stat.tsx` with explicit `variant` prop.

4. **HIGH: Silent partial-failure in `create_action` linked-goal path** (`engagement_surveys.py:1992-1996`) returns `linked_goal_id=0` to the client with no indication the goal creation failed. Per `rules/no-stubs.md` Rule 3, error-hiding pattern. Either propagate `goal_create_failed: True` field, or fail-loud with 500 + rollback.

5. **MEDIUM: 1700-line `engagement_surveys.py` should be split** along three logical seams: templates+cohorts CRUD, launch+lifecycle+aggregate, employee+actions. Comprehension limit hit. Three separate routers under same `/engagement-surveys` prefix.

## Detailed findings

### Concern 1: `engagement_surveys.py` size + structure (MEDIUM)

File is ~2089 lines after M3. Recommended split:

- `engagement_templates_cohorts.py` (M2): templates CRUD + cohort CRUD + preview, ~480 lines
- `engagement_surveys_admin.py` (M3 admin): launch + list/detail/close + aggregate + trend + actions, ~700 lines
- `engagement_employee.py` (M3 employee): my-pending, my-history, render, submit, my-loop-closing, team/aggregate, ~500 lines

Shared helpers (`_resolve_company_id`, `_serialize_filter_spec`, `_resolve_employee_for_user`, `_build_response_cohort_attributes`, `MIN_COHORT_SIZE`, `find_overlapping_surveys`, `_build_aggregate`) move to `services.engagement_helpers`.

### Concern 2: Backend type-safety (LOW with HIGH on one path)

Most handlers do NOT have an `isinstance(body, dict)` guard. If a client sends `[]` or `null`, the `.get()` call throws `AttributeError` and FastAPI returns a 500. **Recommendation**: hoist a `_get_json_body(request) -> dict` helper at the top of every POST/PATCH handler.

`submit_my_response:1453-1458` returns generic `"Invalid request"` on validation failure — log the actual reason for ops, return clearer 400 to caller.

### Concern 3: Comment quality

- **GOOD**: `_build_response_cohort_attributes:765-775` — explains why manager_id_hashed instead of raw manager_id. Exemplary "WHY" commentary.
- **GOOD**: Z06 launch lock comment at line 689-694 — explains threading.Lock + future Postgres advisory lock direction.
- **GOLD STANDARD**: `dataflow_crud.py:67-74` DataFlow caching comment.
- **HIGH severity**: Line 1190 — "Round-2 H12 / Z16 — PDPA admin-access log hook. (Stub: existing \_log_pdpa_access wiring in Arbor; call it here when present in the platform.)" — TODO disguised as comment. Identified-tier responses do NOT get logged when admins view them. Compliance gap.

### Concern 4: Error handling (HIGH for three patterns)

#### 4a. `create_action` linked-goal silent failure (HIGH)

`engagement_surveys.py:1966-1996`: try/except wraps Goal creation, on failure sets `linked_goal_id=0` and returns success. User thinks goal was created. Violates `rules/no-stubs.md` Rule 3. **Fix**: return `goal_create_failed: True` OR rollback the action with `dataflow_crud.delete("EngagementAction", record["id"])`.

#### 4b. `engagement_termination.void_pending_engagement_responses` double-count (HIGH)

`engagement_termination.py:84-101`: if 3 of 5 voids succeed, the parent survey's `voided_count` still bumps by 5. **Fix**: track `successfully_voided_by_survey` dict.

#### 4c. `notifications.bulk_create_engagement_pending` partial failure (LOW — acceptable)

Docstring explicitly says partial fanout is acceptable. But `email_delivery_status` is currently never set to "partial" — feature gap, not a bug.

#### 4d. `engagement_surveys.py:1559-1566` notification mark-resolved silent swallow (LOW)

Bare `except: pass` with no logging. Change to `except Exception as exc: logger.warning(...)` to match the pattern used elsewhere.

### Concern 5: Naming consistency (LOW — clean)

Models, services, fields all snake_case + Engagement\* prefix consistent. `voided_count` (counter) vs `voided_at` (timestamp) is intentional. No issues.

**Minor**: `engagement_termination.py` returns `{"voided": N}` but model field is `voided_count`. Rename dict key to `"voided_count"` to match.

### Concern 6: Test quality

#### `test_engagement_pseudonym.py` — GOOD

9 tests, no shared state, specific assertions, defensive (charset test).

#### `test_engagement_surveys_api.py` — GOOD with caveat

Module-scoped fixture creates 7 employees + cleans up. Tenant isolation tested. **State leak risk**: tests within the module create templates/cohorts on shared company without cleanup — count-dependent assertions could break if order changes.

#### `test_engagement_surveys_m3.py` — GOOD with HIGH issue

**HIGH — STATE LEAK**: `test_submit_voided_response_returns_410:597-626` calls `pytest.skip("Already submitted in earlier test")` if no pending response found. Test order matters. Skip is invisible in CI unless someone checks the report. **Fix**: each test should launch its own fresh survey rather than relying on the shared fixture.

**MEDIUM — Fixture redundancy**: `settings_for(user)` helper at line 688 reconstructs Settings instead of using the fixture. If anyone changes the fixture's defaults, helper goes out of sync.

### Concern 7: Frontend type-safety (LOW)

#### `myHistory` return type wrong (LOW)

Returns `PendingResponse[]` but Python returns `{response_id, survey_id, survey_name, submitted_at, themes}` — different shape. Define separate `HistoryResponse` interface.

#### `EngagementSurvey.schedule_id` non-optional (LOW)

Mark as `schedule_id?: number` for safety on round-trips.

#### `submitMyResponse` cannot send custom Idempotency-Key (LOW)

Server-derived sha256 fallback works. File as follow-up to extend `apiClient.post`.

### Concern 8: Frontend duplication — Stat component (HIGH)

Three definitions across three files with three different visual contracts. Extract to `components/engagement/Stat.tsx`:

```tsx
export function Stat({
  label, value, variant = "plain",
}: {
  label: string;
  value: React.ReactNode;
  variant?: "plain" | "card";
}) { ... }
```

Replace 3 call sites. ~20 minutes, removes ~30 lines duplication.

### Concern 9: Hardcoded values (LOW)

Production code: clean. Constants properly extracted (`MIN_COHORT_SIZE`, `PREVIEW_SAMPLE_NAMES`, `IDEMPOTENCY_REPLAY_WINDOW`).

Seed script: narrative-driven values appropriate for demo. No fix needed.

**LOW**: line 281 — `f"H{(2026 if i >= 4 else 2025) - 0} Pulse..."` — the `- 0` is a no-op. Strip.

**LOW**: `submit_my_response:1461-1462` hardcodes `50_000` payload size limit. Add `MAX_SUBMIT_PAYLOAD_BYTES = 50_000` constant.

### Concern 10: CSS / design-system color leak (MEDIUM)

`rose-*` Tailwind classes hardcoded throughout engagement frontend, while other colors use design tokens (`var(--color-gray-XXX)`). Either:

- (a) Add `--color-rose-XX` variables to globals.css
- (b) Comment that engagement intentionally uses Tailwind's rose palette as module accent

Without one, future contributors will mix tokens inconsistently.

## Additional CRITICAL findings (not in original scope)

### `_LAUNCH_LOCKS` unbounded growth (LOW for current single-tenant deployment)

`engagement_surveys.py:693-718`. Per `rules/trust-plane-security.md` Rule 4 (Bounded Collections), use `OrderedDict` with `maxsize`. 1-line fix. Single-tenant per Postgres so practical impact is zero today.

### `_check_csrf_or_origin` is too lenient (LOW)

`engagement_surveys.py:1391-1410`: rejects only `Origin: null`, doesn't reject `Origin: https://attacker.com`. Mitigated by Bearer auth — attacker with valid JWT can submit anyway, attacker without JWT blocked at auth layer. Belt-and-braces. Still worth fixing — read `settings.cors_origins` and assert `origin in cors_origins`.

### Manager-view recursion depth-2 only (LOW — intentional)

`engagement_surveys.py:1804-1820` only walks 2 levels. Comment says "(recursive 2 levels for P1)". When scope is capped, response should include `scope_capped_at_levels: 2` so frontend can surface "Showing direct + indirect reports only".
