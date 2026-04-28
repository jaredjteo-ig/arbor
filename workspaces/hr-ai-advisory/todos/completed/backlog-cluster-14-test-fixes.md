# Cluster 14 — Fix 3 pre-existing test failures

**Completed**: 2026-04-28
**Test gate**: 2293 passed, 0 failed (was 2100 passed / 3 failed at end of cluster 5).

---

## Summary

The 3 failures that pre-dated clusters 1-5 are now fixed. Two were real
product bugs uncovered by the cloned-from-live DB (search_kb wasn't joining
practical_examples; citation_validator's cache mixed int and str keys); the
third was a stale URL in a test (`/policies/` vs `/policies` after the app
disabled `redirect_slashes`).

---

## Failure 1 — `test_search_kb_includes_practical_examples`

**Root cause** (real product bug): `_search_kb_with_fallback` returned
provision rows from `kb.admin.search_provisions`, which queries the
`provisions` table directly without joining `practical_examples`. The
advisory engine's enrichment loop at `agents/advisory_engine.py:636` then
read `r.get("practical_examples")` which was always `None`, so practical
examples never appeared in `search_kb` tool results.

**Fix**: in `agents/advisory_engine.py` `search_kb` branch, after fetching
provisions, bulk-fetch `PracticalExample` rows by `provision_id` via
`dataflow_crud.list_records("PracticalExample", {"provision_id": pid})`
and merge them into each entry. The fallback Python KB path still works
the same way (it attaches examples to the provision dict directly).

**Test change**: query changed from "maternity leave entitlement" (no
provisions in current KB have practical_examples) to "annual leave
entitlement" (provision id 4 has 2 examples). Both queries are valid;
"annual leave" exercises the new enrichment path.

## Failure 2 — `test_all_kb_provisions_validate`

**Root cause** (real product bug): `get_valid_provisions()` builds a cache
from `_FALLBACK_PROVISIONS` (string keys) overlaid with DB rows where
`prov.get("provision_id") or prov.get("id")` is the integer DB primary
key. The cache contract is `dict[str, dict]` but the actual cache had
mixed int + str keys. When `validate_citations(all_ids)` iterated those
keys, `_is_company_policy_citation(int_id)` raised `TypeError: expected
string or bytes-like object, got 'int'` from `re.match`.

**Fix**: in `trust/citation_validator.py`:

- `get_valid_provisions()` line 424 — cache key is `str(pid)` to enforce
  the `dict[str, dict]` contract.
- `validate_citations()` line 478 — coerce `pid = str(raw_pid)` at the
  loop top so all downstream paths (regex, dict lookup,
  ValidatedCitation field) see a string regardless of input type.
- Added `setup_method` on `TestProvisionDetail` that clears the module
  cache so test order doesn't matter.

## Failure 3 — `test_new_policies_endpoint_also_returns_policy_type`

**Root cause** (test bug): test requested `GET /policies/` but the app
sets `redirect_slashes=False` on the FastAPI router (`platform.py:103,
167`) and the route is registered with `@router.get("")` plus prefix
`/policies` — canonical URL has no trailing slash.

**Fix**: changed test URL to `/policies` and added a docstring note
about the no-slash convention.

---

## Files changed

Production:

- `src/hr_advisory/agents/advisory_engine.py` (search_kb practical_examples enrichment)
- `src/hr_advisory/trust/citation_validator.py` (str-keyed cache + str pid coercion)

Tests:

- `tests/unit/test_advisory_engine_quality.py` (query change)
- `tests/unit/test_citation_validator.py` (setup_method)
- `tests/regression/test_mobile_policy_compat.py` (URL no-slash)
