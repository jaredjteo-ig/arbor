# Red-team round 2 — wider lens, 2026-05-13

The earlier round (`11-redteam-p4-mg-sprint-2026-05-13.md`) probed
the narrow security/privacy contract of the P4-MG sprint. This
round goes wider — looks for issues those probes didn't cover:

- **PII leakage** via the new endpoints — does a manager get
  payroll-grade access through `/team/*`?
- **Audit-trail completeness** — are approval/reject/review
  actions written to the immutable hash-chained audit log?
- **Rate-limit coverage** on the new + widened endpoints.
- **Edge cases**: forged IDs, SQL injection, invalid JWT,
  malformed params, double-approve idempotency, nonexistent
  subpaths.

HEAD at capture: `e44f9be`. Prod live on `e44f9be`. Active
todos: only `P4-XX-deferred.md` remains.

---

## What held ✅

### PII surface (no leak)

`/api/team/members` and `/api/team/dashboard.team_members` return
11 minimal fields each — `id, user_id, name, email, department,
designation, employment_type, pass_type, confirmation_status,
start_date, is_active`. **None of**:

- `nric_fin`, `bank_account_number`, `salary_monthly`,
  `date_of_birth`, `residential_address`

leak into the manager's view. Rajesh as Marcus's direct line
manager **CANNOT** fetch Marcus's full record via
`GET /api/employees/{id}` — that's still 403, payroll-grade PII
stays gated to owner/HR. Correct separation.

### Edge cases (6 probes)

| Probe                                           | Result                                                                                                 |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `GET /team/aggregate?survey_id=999999` (forged) | 404 `"Survey not found."` ✓                                                                            |
| `?survey_id=1' OR '1'='1` (SQL injection)       | 422 (Pydantic int validation rejects) ✓                                                                |
| Invalid JWT                                     | 401 `"Invalid or expired token"` ✓                                                                     |
| Malformed bool param                            | 422 with Pydantic validation detail (BE raw; FE apiClient wraps as friendly summary per P4-QW-2 fix) ✓ |
| `GET /api/team/internal-helper` (nonexistent)   | 404 ✓                                                                                                  |
| Double-approve already-approved leave           | **400 `"Only pending applications can be approved."`** — idempotency-via-status-guard ✓                |

No crashes, no info-leak via error messages, no enumerable
distinction between "doesn't exist" and "you can't see it"
beyond what's appropriate.

---

## 🔴 P1 finding — Missing immutable audit log on HR-decision endpoints

**Symptom**: `leave/approve`, `leave/reject`, `timesheet/approve`,
`timesheet/reject`, and the new `appraisals/manager-review` write
`reviewed_by` + `reviewed_at` (and sometimes `reviewer_remarks`)
directly onto the entity record. **No corresponding write to the
immutable hash-chained audit log.**

**Evidence**:

```
$ grep '_audit' src/hr_advisory/api/routers/leave.py
# no audit-log calls in approve_application / reject_application
$ grep '_audit' src/hr_advisory/api/routers/attendance.py
# no audit-log calls in approve_timesheet / reject_timesheet
$ grep '_audit' src/hr_advisory/api/routers/appraisals.py
# no audit-log calls in manager_review_appraisal

$ grep '_audit_claim' src/hr_advisory/api/routers/claims.py
  _audit_claim(claim_id, company_id, "approved", actor_id)
  _audit_claim(claim_id, company_id, "rejected", actor_id, ...)
# claims does it right
```

**Why it matters**:

- The `reviewed_by` field on the record is **mutable** —
  `dataflow_crud.update()` can overwrite it. A compromised manager
  could later UPDATE the record to look like HR approved (or vice
  versa).
- SG enterprise buyers (Obayashi, banks, listed cos) ask for
  immutable HR-decision audit. PDPA Section 24 + ISO 27001 +
  Big-4 audit expectations all want an append-only trail.
- The mechanism already exists in this codebase (claims uses
  the hash-chained `AuditLogEntry` via `_audit_claim`). Pattern
  is a copy-paste away.

**Pre-existing vs MG-introduced**:

- Leave + timesheet approve/reject: pre-existing gap.
  `feat(scope): team-scoped approval endpoints (P4-MG-2)` inherited
  but didn't introduce.
- `appraisals/manager-review`: **introduced by P4-MG-4** — the
  endpoint is new and ships without audit-log calls.

**Recommended fix** (~1 hr, single bundled commit):

1. Add `_audit_leave()` helper in `routers/leave.py` modelled on
   `_audit_claim()`. Call it on approve / reject / withdraw / cancel.
2. Add `_audit_timesheet()` helper in `routers/attendance.py`.
   Call it on approve / reject.
3. Add `_audit_appraisal()` helper in `routers/appraisals.py`.
   Call it on submit / manager-review / sign-off.
4. Regression test: assert that `approve_application` + the other
   six endpoints write to `AuditLogEntry` with `entity_type`,
   `entity_id`, `action`, `actor_id`, and a SHA-256 hash chain.

---

## 🟡 P2 finding — Rate-limit coverage on new + inherited endpoints

| Endpoint                                      | Rate-limited?            |
| --------------------------------------------- | ------------------------ |
| `leave/apply`                                 | ✓ 20/60s                 |
| `leave/approve`, `leave/reject`               | ✗                        |
| `claims/approve`, `claims/reject`             | ✓ 60/60s                 |
| `timesheet/approve`, `timesheet/reject`       | ✗                        |
| `appraisals/submit`                           | ✓ 30/60s                 |
| `appraisals/manager-review`                   | ✓ 30/60s (added by MG-4) |
| `appraisals/to-review`                        | ✗                        |
| `team/dashboard`, `team/size`, `team/members` | ✗                        |

**This is what `test_b11_rate_limit_coverage[integrations]` has
been flagging since 2026-05-12** — the pre-existing single fail
that carries across every test run. Static analysis of the router
write-endpoint set vs `check_rate_limit` callers fails on those
gaps.

**Why it matters**: a leaked JWT (or even a non-leaked one from
a hostile manager) could brute-force-approve 1000 fake leave
applications in under a minute. The downstream balance update
would compound the damage.

**Recommended fix**: add `check_rate_limit` on each of the seven
write endpoints listed above. Use the same shape claims/approve
already uses (60/60s scoped to actor_id). Read-only `team/*`
endpoints can stay unrated (or get 120/60s if buyer asks).

Both findings touch the same files. **A single bundled commit
"audit-log + rate-limit on HR-decision endpoints" closes both.**

---

## What I deliberately didn't re-test

Per the test-once protocol, didn't re-run:

- The 61 P4-MG sprint regression tests (verified in round-1
  red-team — see `.test-results`)
- The 18 narrow security probes from round-1 (covered there)
- The wider regression suite from 2026-05-12 (3865 pass +
  159 pre-existing fails in unrelated modules)

This round produced no new regression tests — runtime probes
confirmed source pins are calibrated correctly, and the P1/P2
findings need the fixes themselves to write tests against.

---

## Sign-off

- **security-reviewer lens.** PII holds. Edge cases graceful.
  **One actionable security finding** (P1 audit log) — pre-existing
  for 4 of 5 affected endpoints, MG-introduced for the 5th
  (`appraisals/manager-review`). Worth fixing before the next
  enterprise pilot conversation.
- **value-auditor lens.** No buyer-facing gaps surfaced in this
  round. The /team page tells the right story (verified visually
  in round-1).
- **testing-specialist lens.** 61/61 sprint tests pass per
  `.test-results`. No re-execution of pre-existing suite.

**Recommendation**: bundle the P1 + P2 fixes into a single
focused commit before declaring P4 wave fully done. Estimate
1.5 hours total — well-bounded, no architecture changes, single
test file.

If deferred, mark in P4-XX-deferred.md with explicit unblock
trigger so the next session sees it.
