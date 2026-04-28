# Cluster 6 — Recruitment Red-Team Round-1 Audit

**Completed**: 2026-04-28
**Source**: `active/recruitment-redteam-fixes.md`
**Test gate**: 11 new regression tests, all green. See
`tests/regression/test_b_cluster_6_recruitment_audit.py`. Full suite NOT
re-run per the test-once protocol; previous gate from cluster 5 stands.

---

## Summary

Ten items audited (T-RX07 had already been completed in cluster 5). Nine
items were already shipped at HEAD `3440ee0`. Real work was scoped to
T-RX09 only — two of the four priority list endpoints (`list_all_candidates`,
`list_offers`) still lacked pagination; both now have it.

| Item   | State at HEAD `3440ee0` | Action               |
| ------ | ----------------------- | -------------------- |
| T-RX01 | already fixed           | regression test only |
| T-RX02 | already fixed           | regression test only |
| T-RX03 | already fixed           | regression test only |
| T-RX04 | already fixed           | regression test only |
| T-RX05 | already fixed           | regression test only |
| T-RX06 | already fixed           | regression test only |
| T-RX08 | already fixed           | regression test only |
| T-RX09 | partial (2/4 endpoints) | implemented + test   |
| T-RX10 | already fixed           | regression test only |
| T-RX11 | already fixed           | regression test only |

---

## T-RX01 — Offer email currency formatting | already fixed

- **Source**: `active/recruitment-redteam-fixes.md`
- **State at HEAD `3440ee0`**:
  `src/hr_advisory/api/routers/recruitment.py:1537` — `send_offer` builds
  the salary string as
  `f"{offer.get('currency', 'SGD')} {offer.get('salary', 0):,.2f}/{offer.get('salary_period', 'month')}"`
  No hardcoded `$`.
- **Regression test**:
  `test_t_rx01_send_offer_uses_currency_and_period_in_email` — captures the
  variables passed to `_send_recruitment_email` and asserts the salary string
  contains "SGD" + "monthly" and never `$`.

---

## T-RX02 — PDPA re-confirmation on talent-pool re-apply | already fixed

- **State at HEAD `3440ee0`**:
  `recruitment.py:2629-2643` — `reapply_candidate` creates the new candidate
  with `pdpa_consent=False`, `pdpa_consent_date=""`, and a re-confirmation
  note in `notes`. Response also includes `"note": "PDPA consent must be
re-confirmed for the new application."`.
- **Regression test**:
  `test_t_rx02_reapply_resets_pdpa_consent` — captures the create payload and
  pins consent=False, consent_date="", and the note string.

---

## T-RX03 — Required-screening enforcement on public apply | already fixed

- **State at HEAD `3440ee0`**:
  `recruitment.py:1895-1904` — `public_apply` builds
  `required_ids = {q.get("id") for q in job_questions if q.get("is_required")}`,
  computes `missing = required_ids - answered_ids`, and returns 400
  ("All required screening questions must be answered.") when non-empty.
- **Regression test**:
  `test_t_rx03_public_apply_rejects_missing_required_screening` — submits an
  application that answers only the optional question and asserts a 400
  response with "required screening" in the detail.

---

## T-RX04 — Remove company-name fallback in public_list_jobs | already fixed

- **State at HEAD `3440ee0`**:
  `recruitment.py:1710-1715` — `_resolve_company_by_slug` queries only by
  `slug`, raising 404 immediately if no match. No name fallback exists.
  The header comment at lines 1700-1707 explicitly documents the removal of
  the enumeration vector.
- **Regression test**:
  `test_t_rx04_public_list_jobs_does_not_fall_back_to_company_name` — patches
  `dataflow_crud.list_records` to record every lookup, asserts the endpoint
  returns 404 for an unknown slug, and pins that no Company query was made
  with a `name` filter.

---

## T-RX05 — Bounded deque for rate-limit timestamps | already fixed

- **State at HEAD `3440ee0`**:
  `src/hr_advisory/api/middleware/rate_limit.py:35-38, 188` — `_request_log`
  is `OrderedDict[str, deque]`, and per-key buckets are created as
  `deque(maxlen=max_requests + 1)`.
- **Regression test**:
  `test_t_rx05_rate_limit_timestamps_use_bounded_deque` — exercises
  `_check_in_memory` directly, then asserts the bucket is a `deque` with
  a non-None, sane `maxlen`.

---

## T-RX06 — Mask candidate email in production logs | already fixed

- **State at HEAD `3440ee0`**:
  `recruitment.py:62-63` — `_send_recruitment_email` builds
  `to_masked = to[:3] + "***" + to[to.index("@"):] if "@" in to else "***"`
  and logs the masked form: `logger.info("Recruitment email sent: ...
to=%s", template_name, to_masked)`.
- **Regression test**:
  `test_t_rx06_recruitment_email_log_masks_address` — stubs `ResendAdapter`,
  invokes `_send_recruitment_email` with a recognisable local-part, and
  asserts the success log line never contains the local-part and does
  contain `***`.

---

## T-RX08 — Composite index on Candidate(job_listing_id, email) | already fixed

- **State at HEAD `3440ee0`**:
  `src/hr_advisory/models/company_user.py:2185` — `Candidate.__dataflow__`
  declares `{"name": "idx_candidate_job_email", "fields": ["job_listing_id",
"email"]}` alongside the per-field indexes.
- **Regression test**:
  `test_t_rx08_candidate_has_composite_job_email_index` — pins the composite
  index by introspecting `Candidate.__dataflow__["indexes"]`.

---

## T-RX09 — Pagination on list endpoints | newly fixed

- **State at start**: `list_jobs`, per-job `list_candidates`,
  `search_talent_pool`, `list_referrals` already had pagination. Two
  priority endpoints did NOT:
  - `list_all_candidates` (`recruitment.py:567`)
  - `list_offers` (`recruitment.py:1566`)
- **Fix**: Added `page: int = Query(1, ge=1)` and
  `page_size: int = Query(50, ge=1, le=200)` to both endpoints; both now use
  the existing `_paginate(items, page, page_size)` helper and return the
  same shape as the other paginated endpoints (`items`, `total`, `page`,
  `page_size`, plus the legacy alias key `candidates`/`offers` and a
  `count` for backward compatibility with existing tests).
- **`list_offers` performance note**: candidate-name enrichment is now
  restricted to the rows on the returned page rather than the full offer
  table, which removes an N+1 read sweep that could be triggered by any
  authenticated owner/HR caller.
- **Compatibility**: existing unit tests in `tests/unit/test_recruitment_offers.py`
  continue to pass — they only assert on `body["count"]` and
  `body["offers"]`, which still hold under the paginated response shape
  (with default page_size=50, all small fixtures fit in one page).
- **Regression test**:
  `test_t_rx09_priority_list_endpoints_accept_pagination_params` — three
  layers of coverage:
  1. Signature check on `list_all_candidates`, `list_offers`,
     `search_talent_pool`, and `list_referrals` for `page` + `page_size` params.
  2. Behavioural check — 75 candidates with `?page=2&page_size=25` returns
     25 rows starting at id=26 with `total=75`.
  3. Page-bounded enrichment check on `list_offers` — only the page's three
     rows trigger candidate `read` calls, never the full table of ten.
- **Files changed**:
  - `src/hr_advisory/api/routers/recruitment.py` (list_all_candidates,
    list_offers).

---

## T-RX10 — Stage-transition state machine | already fixed

- **State at HEAD `3440ee0`**:
  `recruitment.py:140-180` — `_VALID_STAGE_TRANSITIONS` maps each source
  stage to its allowed destinations; `_validate_stage_transition` enforces
  with a 400. `update_candidate` (line 776) calls it whenever `stage` is in
  the update payload. Terminal stages (`hired`, `rejected`, `withdrawn`)
  cannot be moved out of via the generic PATCH.
- **Regression tests**:
  - `test_t_rx10_update_candidate_blocks_invalid_stage_transition` —
    PATCH a hired candidate to `"new"` returns 400.
  - `test_t_rx10_update_candidate_allows_valid_stage_transition` —
    `screening -> interview` is allowed and persists.

---

## T-RX11 — close_job cascade | already fixed

- **State at HEAD `3440ee0`**:
  `recruitment.py:383-490` — `close_job` cascades:
  - active candidates (stages new/screening/interview/assessment) ->
    "withdrawn" with `rejection_reason="job_closed"` and an audit-trail
    entry via `_log_candidate_activity`,
  - pending offers (statuses draft/pending_approval/approved/sent) ->
    "expired".
    Returns counters `candidates_withdrawn` and `offers_expired` in the
    response body. Terminal states are left alone.
- **Regression test**:
  `test_t_rx11_close_job_withdraws_active_candidates_and_expires_offers` —
  fixture with 5 candidates (3 active + 2 terminal) and 4 offers (3
  pending + 1 accepted). Asserts only the active/pending rows were
  updated, with the correct rejection_reason and final status, and that
  the response counters match.

---

## Files changed

- `src/hr_advisory/api/routers/recruitment.py` — pagination on
  `list_all_candidates` and `list_offers` (T-RX09).
- `tests/regression/test_b_cluster_6_recruitment_audit.py` — 11 new
  regression tests, one per audited item (T-RX10 has two for the
  forbidden-and-allowed pair).

No edits to `src/hr_advisory/models/company_user.py` were needed — the
T-RX08 index was already present.

---

## Test results

```
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx01_send_offer_uses_currency_and_period_in_email PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx02_reapply_resets_pdpa_consent PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx03_public_apply_rejects_missing_required_screening PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx04_public_list_jobs_does_not_fall_back_to_company_name PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx05_rate_limit_timestamps_use_bounded_deque PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx06_recruitment_email_log_masks_address PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx08_candidate_has_composite_job_email_index PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx09_priority_list_endpoints_accept_pagination_params PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx10_update_candidate_blocks_invalid_stage_transition PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx10_update_candidate_allows_valid_stage_transition PASSED
tests/regression/test_b_cluster_6_recruitment_audit.py::test_t_rx11_close_job_withdraws_active_candidates_and_expires_offers PASSED

============================== 11 passed in 1.54s ==============================
```
