# Cluster 3 — Backlog Perf + UX (B12, B13, B15)

**Completed**: 2026-04-28
**Source**: `active/backlog-red-team-findings.md`
**Test gate**: 2095 passed, 3 pre-existing failures (carried, not regressions). See `.test-results`.

---

## Summary

Three perf/UX backlog items from round 11. **B12 and B13 were already fully
fixed at HEAD `3440ee0`**; only one real gap remained for B15 (approvals page
tab strip). New regression tests pin all three so they cannot silently regress.

---

## TODO-B12 — Fix N+1 query in employee list ✅ already fixed

- **Priority**: Medium
- **Source**: Round 11, Q-H1
- **File**: `src/hr_advisory/api/routers/employees.py:286-295`
- **State at HEAD `3440ee0`**: `_bulk_find_users` does a single
  `dataflow_crud.list_records("User", filter_dict)` then filters by an
  `id_set` in memory. Comment in source: "one query per user ID (N+1 elimination)".
- **Regression test**: `test_b12_bulk_find_users_is_single_query` — patches
  `list_records` and `read`, runs a 5-user batch, asserts list_records is
  called once and read is called zero times.

---

## TODO-B13 — Add pagination to list endpoints ✅ already fixed

- **Priority**: Medium
- **Source**: Round 11, M-10
- **State at HEAD `3440ee0`**: All three priority endpoints already paginated:
  - `GET /employees` (`employees.py:1757`) — `page` + `page_size` (default 50,
    max 200), returns `{employees, count, company_id, page, page_size, total, pages}`
  - `GET /leave/applications` (`leave.py:781`) — same pattern
  - `GET /payroll/runs` (`payroll.py:371`) — same pattern (analogous to /payroll/payslips
    which is also paginated)
- **Note**: 21 occurrences of `limit: 10000` exist elsewhere (mostly in `shadow.py`)
  but those are internal calls — adding pagination there is a future task, not
  the round 11 finding.
- **Regression test**: `test_b13_priority_endpoints_declare_pagination` (parametrized
  × 3) — inspects each function's signature and source.

---

## TODO-B15 — Responsive breakpoints for 8 employee-facing pages ✅ fixed

- **Priority**: Medium
- **Source**: Round 11, M-3
- **State at start of cluster**: All 8 pages had the basics in place
  (`max-w-Nxl mx-auto`, tables wrapped in `overflow-x-auto`). One genuine gap
  was the approvals page's tab strip and action button group.
- **Fix**: `apps/web/src/app/(dashboard)/approvals/page.tsx`:
  - Tab strip: `flex gap-1 border-b` → `flex gap-1 border-b ... overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0` so tabs scroll horizontally on <640px.
  - Action button group above the timesheet table: `flex gap-2` → `flex flex-wrap gap-2` so buttons wrap to a second line instead of overflowing.
- **Other 7 pages** (claims, attendance, appraisals, shifts, my-claims,
  my-attendance, my-timesheets, my-payslips): audited, already mobile-functional
  at 375px. Tables wrapped, headers short, modals viewport-bounded.
- **Recruitment** is explicitly out of B15 scope — its 4,701-line single-page
  architecture is tracked under the recruitment-module deferred items
  (recruitment.py + recruitment/page.tsx architectural split).
- **Regression test**: `test_b15_approvals_tabs_have_overflow_handling` — pins
  the `overflow-x-auto` class on the approvals tab strip so it can't silently
  drop out in a future refactor.

### Files changed

- `apps/web/src/app/(dashboard)/approvals/page.tsx`
- `tests/regression/test_b_cluster_3_perf.py` (new)
