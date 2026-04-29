# Session 2 — Round-12 correctness carryovers (~10 hr)

**Goal:** close the 5 round-12 findings that round-13 also flagged as still-open. After this the platform stops failing security/correctness reviews on paper, regardless of demo polish.

**Source findings:** `04-validate/round-12-deep-analysis.md` items 1, 2, 4, 5, 15.

**Test gate:** 2340 baseline; each task adds at least one regression test.

---

## S2-T1: Hire-role allow-list [round-12 CRITICAL]

- **What:** `recruitment.hire_candidate` (recruitment.py:1174) reads `body.get("role", "employee")` and passes it straight to `Invitation.role`, which `auth.py:481` reads back into `_create_user`. No allow-list. An hr_manager can hire a candidate as `platform_admin` and that candidate becomes a platform admin on first login.
- **Files:**
  - `src/hr_advisory/api/routers/recruitment.py` — at hire time, validate `role` against an explicit allow-list `{"employee", "hr_manager"}`. Reject `owner`, `platform_admin`, anything else.
  - Defense-in-depth: also validate at the auth.py invitation-acceptance side so even a malformed Invitation row can't escalate.
- **Acceptance:**
  - POST `/recruitment/candidates/{id}/hire` with `role: "platform_admin"` returns 400 not 200.
  - Regression test exercises the bypass attempt and asserts the resulting User has `role="employee"` (not platform_admin).
- **Risk:** low. ~30 lines.

## S2-T2: Hire → onboarding transactional [round-12 HIGH]

- **What:** the hire flow creates a User → Employee → OnboardingAssignment chain. Today, a failure midway leaves orphan half-states (User exists with no Employee, or Employee with no OnboardingAssignment). The auto-assign task already exists; it just isn't transactional with the user-create.
- **Files:**
  - `src/hr_advisory/api/routers/auth.py` register-employee path — wrap the User-create + Employee-create + auto-assign-onboarding in a single DataFlow transaction (or saga with explicit compensation).
  - If full transaction is too risky, use a saga: on auto-assign failure, mark the Employee as `onboarding_pending=True` so a sweep job can retry.
- **Acceptance:**
  - Inject a forced failure in `auto_assign_default_onboarding` → no orphan rows; the User-create rolls back too.
  - Regression test: real Postgres, mocked auto-assign that raises → assert no User/Employee row was created.
- **Risk:** med — DataFlow's transaction semantics across multiple models need verification first.

## S2-T3: Compliance cache invalidation on policy writes [round-12 HIGH]

- **What:** `routers/compliance.py:_compliance_cache` has a 5-minute TTL. When `routers/policies.py` creates/updates/deletes a policy that affects compliance domain coverage, the cache stays stale for up to 5 minutes — `/compliance/status` returns out-of-date data.
- **Files:**
  - `src/hr_advisory/api/routers/compliance.py` — expose `invalidate_compliance_cache(company_id: int) -> None`.
  - `src/hr_advisory/api/routers/policies.py` — call it on every write (create / update / delete / upload).
  - Regression test: write a policy → next compliance/status call uses fresh data not the cached stale value.
- **Risk:** low. Tight blast radius.

## S2-T4: `finalize_trust_chain` integration [round-12 HIGH]

- **What:** `agents/advisory_engine.py` builds a trust chain via `create_trust_chain(genesis)` and adds attestations as the engine runs, but `finalize_trust_chain(...)` is never called. The chain stays unsealed in memory; we have proof debt — the audit trail isn't actually persisted at the end of the advisory query.
- **Files:**
  - `src/hr_advisory/agents/advisory_engine.py` — at the end of `run(...)`, call `finalize_trust_chain(trust_chain)` and persist the result.
  - `src/hr_advisory/api/routers/advisory.py` — same for the streaming path; finalize at end of stream.
  - Surface `trust_chain.persisted: bool` in the response.
- **Acceptance:**
  - Every `/advisory/query` response includes `trust_chain.persisted: True` and a `trust_chain_id` for retrieval.
  - Regression test: post a query, retrieve the persisted trust chain by id, verify the genesis + attestation count.
- **Risk:** med. Need to verify `finalize_trust_chain` semantics + DB schema for persistence.

## S2-T5: Immutable audit log [round-12 HIGH]

- **What:** several action logs (recruitment activity, onboarding step completion, compliance status changes) write to mutable rows. A bad actor (or a buggy admin tool) could delete or rewrite an audit entry. PDPA compliance + future security-review readiness both want an append-only audit log.
- **Files:**
  - `src/hr_advisory/models/audit.py` (new) — `AuditLogEntry` DataFlow model with hash-chaining: each row's `prev_hash` = hash of the previous row; current row's `hash` is computed deterministically from its content + prev_hash.
  - `src/hr_advisory/services/audit_log.py` (new) — `record_event(company_id, actor_id, event_type, payload)`. Async-safe, batched flush.
  - Touchpoints: every `_log_candidate_activity`, `_audit_claim`, scorecard generate, calendar connect/disconnect, hire, onboarding step completion → also write to the immutable log.
  - `tests/regression/test_audit_log_chain_integrity.py` — verify hashes chain correctly; tampering with row N invalidates the rest.
- **Acceptance:**
  - All security-relevant actions write to the audit log.
  - Tamper test: modify a row in the DB → chain verifier reports the break.
- **Risk:** med. Needs careful DB design + hash-chain correctness.

---

## Implementation order

Sub-agents in parallel:

- Agent A: S2-T1 + S2-T3 (small, isolated; both touch routers but different files)
- Agent B: S2-T2 (transaction semantics — needs full focus)
- Agent C: S2-T4 (trust chain — own module)
- Agent D: S2-T5 (immutable log — biggest greenfield)

After convergence: pytest full suite, commit per agent's work, single push.

## Acceptance for the session

- 2340 → ≥2360 tests passing.
- 5 new regression tests (one per task).
- Round-12 master report's "still open" section drops to 0.
- Single commit `fix(security): close round-12 carryovers — role allow-list + transactional hire + cache + trust chain + audit log`.
