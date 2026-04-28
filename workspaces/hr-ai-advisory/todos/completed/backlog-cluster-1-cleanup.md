# Cluster 1 — Backlog Quick Wins (B10, B14, B18, B19, B20, B22)

**Completed**: 2026-04-28
**Source**: `active/backlog-red-team-findings.md`
**Test gate**: 2078 passed, 3 pre-existing failures (verified not regressions). See `.test-results`.

---

## Summary

Six MEDIUM/LOW backlog items from round 11. Three were already fixed in prior commits;
three required real work. New regression tests added in `tests/regression/test_b_cluster_cleanup.py`.

---

## TODO-B10 — Fix saga tenant isolation type mismatch ✅ already fixed

- **Priority**: Medium
- **Source**: Round 11, M-6
- **Original concern**: `saga.tenant_id` is str, `company_id` is int — comparison always fails
- **File**: `src/hr_advisory/api/routers/integrations.py:284`
- **Resolution**: Verified at HEAD `3440ee0`: `if str(saga.tenant_id) != str(company_id): raise HTTPException(...)`. Both sides coerced to `str`. No change needed.

---

## TODO-B14 — Fix dataflow_crud.count() double query ✅ already fixed

- **Priority**: Low
- **Source**: Round 11, M-9
- **File**: `src/hr_advisory/services/dataflow_crud.py:93-102`
- **Resolution**: Verified — `count()` does `len(list_records(...))`, a single query. The
  original "double query" pattern is gone. The remaining inefficiency (fetches all rows
  to count) is its own future task; not a regression of the original concern.
- **Regression test**: `test_b14_count_is_single_query` patches `list_records` and asserts
  one call.

---

## TODO-B18 — Replace datetime.utcnow() with datetime.now(timezone.utc) ✅ fixed

- **Priority**: Low
- **Source**: Round 11, M-7
- **Original target**: `src/hr_advisory/api/routers/onboarding.py` (28 occurrences)
- **State at start of cluster**: `onboarding.py` already clean. Two stragglers found in
  `agents/memory/short_term.py:63` and `agents/memory/long_term.py:91`.
- **Fix**: Both files updated to import `timezone` and use `datetime.now(timezone.utc)`.
- **Regression test**: `test_b18_no_datetime_utcnow_in_app_code` scans all of
  `src/hr_advisory/api/routers/` and `src/hr_advisory/agents/memory/` for any remaining
  occurrences.

---

## TODO-B19 — Extract duplicate helper functions to shared module ✅ fixed

- **Priority**: Low
- **Source**: Round 11, L-5
- **State at start of cluster**: `_helpers.py` existed with both helpers, but five
  routers still had local copies.
- **Fix**: Removed five local definitions and replaced with imports from
  `hr_advisory.api.routers._helpers`:
  - `recruitment.py` — `_validate_text_length`
  - `shifts.py`, `attendance.py`, `claims.py`, `policies.py` — `_find_employee_for_user`
- **Verification**: `from hr_advisory.api.routers import recruitment, shifts, attendance, claims, policies` succeeds without error.
- **Regression test**: `test_b19_helpers_imported_not_redefined` greps every router for
  `^def _validate_text_length` and `^def _find_employee_for_user`, asserting only
  `_helpers.py` defines them.

---

## TODO-B20 — Use UUID4 for document IDs ✅ already fixed

- **Priority**: Low
- **Source**: Round 11, L-6
- **File**: `src/hr_advisory/api/routers/document.py:406`
- **Resolution**: Verified `document_id = f"doc_{uuid.uuid4()}"`. Predictable hash is gone.
- **Regression test**: `test_b20_document_id_uses_uuid4` greps the canonical pattern and
  parses a sample id as UUID4.

---

## TODO-B22 — Fix silent error swallowing in dashboard/reports ✅ fixed

- **Priority**: Low
- **Source**: Round 11, L-3
- **State at start of cluster**: 2 silent `.catch(() => {})` blocks remained:
  1. `apps/web/src/app/(dashboard)/compliance/page.tsx:444` — auto-populate from company profile
  2. `apps/web/src/components/shell/AppShell.tsx:39` — unread alert count
- **Fix**: Both replaced with `console.warn(...)` — preserves the graceful fallback
  (manual entry / 0 count) but adds observability.
- **Why not toast**: Both are background fetches whose failure does not block the user.
  A blocking toast would be over-noisy. The console warning is sufficient for diagnosis
  while keeping the UX silent on transient failures.
