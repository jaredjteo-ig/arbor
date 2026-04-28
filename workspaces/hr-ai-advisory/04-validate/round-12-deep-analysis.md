# Round 12 — Deep Failure-Mode and Edge-Case Analysis

**Generated:** 2026-04-28
**Scope:** Code-and-architecture audit only. No browser/runtime probing.
**Sources read:** `.session-notes`, `.test-results`, recruitment-redteam-round1.md,
recruitment-redteam-fixes.md, recruitment-module.md, onboarding-feature.md,
plus the implementation files referenced inline below.

**Severity scale:** CRITICAL (production data loss / security) > HIGH
(integrity / availability) > MEDIUM (correctness drift) > LOW (polish).

---

## 1. Failure Points (Production Reliability)

### 1.1 Rate Limiter — In-Memory, Per-Process [HIGH]

**File:** `src/hr_advisory/api/middleware/rate_limit.py`

The `_request_log` `OrderedDict` lives in process memory. With `n` backend
processes (uvicorn workers, multiple containers, blue/green), each holds its
own counter. Effective limit on the `apply:{ip}` bucket becomes `n × 10/hr`,
not 10/hr. This is the same gap RX07 documented; T-RX05 (bounded deque) does
not change it.

Concrete impact:

- Public `/careers/.../apply` with one container is 10/hr. With production
  scale-out (two containers planned for the GCP deploy), it's 20/hr.
- Auth bucket (`auth:{ip}` at 5/min in `auth.py`) has the same dilution.
- Hire bucket (`hire:{company_id}` at 10/hr) — same.

Recovery on restart wipes everything: an attacker can force a rolling restart
or just wait out the next deploy window.

**Mitigation:** Implement T-RX07 (Redis-backed rate limit with `INCR + EXPIRE`)
before the next public surface goes live. Until then, halve the limits in
`platform.py` to compensate for the worst-case `n=2`.

---

### 1.2 LLM Degradation Path [MEDIUM]

**File:** `src/hr_advisory/agents/advisory_engine.py:963-980`

When OpenAI/Gemini is down or the API key is invalid, the outermost `except
Exception` returns:

```
{"response_text": "I'm having trouble processing your question right now...",
 "risk_tier": "amber", "confidence": 0.3, "domains": [], "citations": [],
 "degraded": True}
```

This is correct fail-closed behaviour for the user-facing message, but the
trust chain in `advisory.py:556-568` still records an attestation with
`reasoning_summary="Autonomous engine: domains=[], tools=[]"` and persists a
GenesisRecord with empty `query_domains`. So an audit later cannot
distinguish "LLM was down" from "LLM answered with no tools". The `degraded`
flag is in the response but not in the attestation.

**Mitigation:** Add `degraded: bool` to `AgentAttestation` and propagate.
Include the LLM provider/model and the exception class name (not message —
PII risk) in the attestation when `degraded=True`.

---

### 1.3 DB Pool / asyncpg "different loop" Errors [HIGH — already partly addressed]

The test logs flagged event-loop binding issues. Read of `advisory.py:482`
shows the engine being run via `loop = asyncio.get_event_loop()` and
`loop.run_in_executor(None, ...)`. The engine itself uses a sync `OpenAI`
client inside the executor — fine. But `_fetch_company_profile()` uses
`LocalRuntime().execute(...)` which is sync and fine in the request handler,
not fine if ever called from a background task that owns its own loop.

The `auto_assign_default_onboarding(...)` call inside `register_employee`
(`auth.py:599`) and `ensure_leave_balances(...)` (`auth.py:587`) are called
synchronously inside an async endpoint. If either internally uses
`AsyncLocalRuntime` or asyncpg pools, the "different loop" error returns.

**Mitigation:** Audit `ensure_leave_balances`, `auto_assign_default_onboarding`
and confirm both use sync `LocalRuntime`. Add a regression test that hits
`/auth/register-employee` against a real Postgres DB, not the unit mock, to
catch this path.

---

### 1.4 Resume Upload — Cleanup Story [MEDIUM]

**File:** `src/hr_advisory/api/routers/recruitment.py:1232-1300`

Files land at `uploads/recruitment/{company_id}/{uuid}.{ext}`. There is no
deletion path on:

- Candidate deletion (no DELETE endpoint exists yet — but if added, files
  orphan).
- Re-upload (a candidate uploading a second resume creates a new UUID file
  and overwrites only `resume_url` in the DB; the previous file orphans).
- PDPA purge (`pdpa_purge_warned_at` field exists in `Candidate`; no purge
  job has been wired to delete files).
- Company deletion / tenant offboarding.

These accumulate forever. At 10MB max × thousands of candidates/year × N
years this is bounded but ungoverned. Bigger PDPA risk: a candidate can
exercise their right of erasure, and the file persists.

**Mitigation:** (a) On `update_candidate` resume re-upload, delete the
previous file. (b) Add a daily janitor job that deletes files whose
`Candidate.resume_url` no longer references them. (c) Wire PDPA purge to
delete files in the same transaction as candidate deletion.

---

### 1.5 Resend Email — Fail-Silent [HIGH for compliance]

**File:** `src/hr_advisory/api/routers/recruitment.py:35-67`

`_send_recruitment_email` swallows every exception and returns `False`.
Caller never checks the return value. If Resend is down or
`RESEND_API_KEY` is unset, the candidate is moved to `interview` /
`offered` / `hired` stage but never receives the email — they will not show
up.

For the hire path, the candidate is moved to `hired`, an Invitation is
created with a token, and the welcome email is supposed to deliver the
token. If Resend fails, the token only exists in the DB and the candidate
cannot self-register.

**Mitigation:** Add a `RecruitmentEmailQueue` table (or reuse an existing
queue), persist failed sends with retry counter, and surface "email failed"
banners in the recruitment UI for HR to manually resend or copy the
invitation link. Alternatively, return a `email_status: "queued|failed"`
field in the API responses so the frontend can warn.

---

### 1.6 Pdf Generation Temp Files [LOW — addressed]

Round-1 H4 noted reportlab PDF temp files were never cleaned up; now wired
via `BackgroundTask`. No new finding.

---

## 2. State Integrity (Invariant Violations)

### 2.1 Hire → Onboarding Transition [HIGH]

**Files:** `recruitment.py:1123-1210` and `auth.py:594-616`

The flow:

1. Recruiter clicks Hire → `Candidate.stage="hired"`, `Invitation` row
   created, candidate email sent (best-effort).
2. Candidate clicks email link → `/auth/register-employee` validates
   invitation, creates User, creates Employee, creates LeaveBalance, calls
   `auto_assign_default_onboarding`.

Failure modes that break the invariant "hired => onboarding eventually
exists":

- **Email never delivered (1.5)** — candidate never registers, no
  Onboarding row, but `Candidate.stage="hired"`. Recruitment dashboard
  shows them as hired forever.
- **Invitation expires** (`expires_at`) — same outcome. The hire endpoint
  does not currently set `expires_at` on the invitation row
  (recruitment.py:1164-1179 is missing it). If the model defaults to NULL,
  the expiry check at `auth.py:454-462` skips silently. If the model
  defaults to "now", the candidate cannot register at all.
- **`auto_assign_default_onboarding` raises** — caught at `auth.py:611`
  with `logger.warning`. User and Employee exist; no Onboarding. The
  company sees a hired employee with no onboarding tasks.
- **`ensure_leave_balances` raises** — same pattern at `auth.py:589-592`.
  Employee exists with no leave balances.

The TOCTOU rollback at `auth.py:476-486` reverts the invitation if user
creation fails, but does not roll back if Employee creation, leave
balances, or onboarding assignment fail. Result: User exists but is
unusable from HR's perspective.

**Mitigation:** Wrap User + Employee + LeaveBalance + OnboardingAssignment
in a single DB transaction. If any step fails, roll the whole thing back
and re-activate the invitation. The current "warning + continue" pattern
leaves orphaned half-states.

---

### 2.2 Compliance Cache vs Policy Updates [MEDIUM]

**Files:** `compliance.py:33-51` (cache) and `policies.py:326-450` (creates).

`policies.create_policy` and `policies.upload_policy` do not call
`invalidate_compliance_cache(company_id)` after writing. The cache hook
exists (`compliance.invalidate_compliance_cache`) but is never imported
anywhere in `policies.py` — verified by `grep invalidate_compliance_cache`
in this directory. So:

- HR uploads a new "Leave Policy" at 09:00.
- A user runs a compliance check at 09:01 — cached result from 09:00 is
  returned, says "missing leave policy".
- Up to 5 minutes of stale "non-compliant" warnings.

For a 5-minute TTL on a single-tenant SaaS this is mild; for a demo where
the buyer adds a policy and runs compliance immediately to "see the green
light", it is observable and confidence-eroding.

**Mitigation:** Import and call `invalidate_compliance_cache(company_id)`
in `policies.create_policy`, `policies.update_policy`, `policies.delete_policy`,
and `policies.upload_policy`. Also call it from `kb_router` if the KB is
ever updated mid-session (KB content changes invalidate every company's
cache — call with `company_id=None` and clear the whole dict).

---

### 2.3 Trust Chain — Persistence Is Optional [MEDIUM, "proof debt"]

**Files:** `trust/eatp_lineage.py:277-334` and `advisory.py:556-568`.

The `_persist_trust_chain` is wrapped in a broad `try/except Exception` that
logs a warning. The `advisory_query` endpoint never calls
`finalize_trust_chain`. `create_trust_chain` only writes to the
`_trust_cache` `OrderedDict` (in-memory, evicts at 10000). On process
restart, every in-flight chain is lost.

The chain is returned to the client as `trust_chain` in the response, but
nothing on the server retains it for audit. So the "EATP-traceable" claim
on the marketing page has no audit trail unless the
`TrustLineageRecordCreateNode` happens to succeed AND we add a
`finalize_trust_chain(...)` call.

**Mitigation:** (a) Call `finalize_trust_chain(session_id, user_id,
company_id)` at the end of `advisory_query` and the streaming variant.
(b) Treat `_persist_trust_chain` failures as a counter-incrementing event
(metrics) so we know when audit data is being lost. (c) Reflect the
persistence outcome back in the response (`trust_chain.persisted: bool`)
so the frontend can warn during demos.

---

### 2.4 Monotonic Risk-Tier Escalation [LOW — guardrail present]

`advisory.py:179-183` defines `_escalate_risk_tier` enforcing the
monotonic invariant (green → amber → red, never down), but I see only
direct assignments to `risk_tier` in the rest of the file (`risk_tier =
"red"` at lines 526, 537). The helper is defined but unused. Not a current
defect — but a footgun: a future contributor will assume tier escalation is
enforced, and downgrade unintentionally.

**Mitigation:** Either (a) delete `_escalate_risk_tier` if direct
assignment is the convention, or (b) replace every `risk_tier = X` with
`risk_tier = _escalate_risk_tier(risk_tier, X)`.

---

## 3. Scope / Tenancy (Single-Tenant Collapse Audit)

### 3.1 Cross-Tenant Filter Coverage

`tenant_isolation.get_current_company_id` is called in every recruitment,
onboarding, and policies endpoint I sampled. The pattern
`_verify_*_ownership(id, company_id)` is consistent. Public endpoints scope
by URL slug (`recruitment.py:1717-1742`) which is the right defence.

Spot-checks:

- `recruitment.list_jobs` — filters by `company_id` ✓
- `recruitment.public_get_job` — scoped via `_resolve_public_job` ✓
- `recruitment.update_interview` — checks ownership at line 977-979 ✓
- `policies.get_policy` — checks `company_id` mismatch at line 304 ✓
- `onboarding.*` — sampled, every endpoint loads `company_id` first ✓

### 3.2 JWT Scope Claim Validation [MEDIUM]

**File:** `tenant_isolation.py:43-92`

`validate_company_access` is called in `advisory.py:291` and
`advisory.py:707`. It is NOT called in most recruitment/policies/onboarding
endpoints — they rely on `get_current_company_id(current_user)` and then
match the loaded record's `company_id` against the JWT's `company_id`.

This is fine because the resource lookup uses the JWT-derived `company_id`
as the filter key, so a user from company A trying to read job 42 (which
belongs to company B) will get a 404 — the join `(job_id=42 AND
company_id=A)` returns empty.

**One gap:** The hire endpoint (`recruitment.py:1124`) takes
`candidate_id` from the URL path and looks it up via
`_verify_candidate_ownership`, but the request body's `role` field is
trusted (`recruitment.py:1174`). A user could request `role:
"platform_admin"` for the new hire. The Invitation accepts arbitrary
strings; `_register_employee_via_invitation` reads the role straight from
the invitation (`auth.py:481`) and passes it to `_create_user`. There's no
allow-list.

**Severity:** HIGH if `platform_admin` is a real privilege escalation; the
escalated user becomes a platform admin in the new company on first login.

**Mitigation:** In `recruitment.hire_candidate`, validate `role ∈ {"employee",
"hr_manager"}`. Block "owner" and "platform_admin" from the recruitment
hire path. Owners are seeded at company creation; platform admins are
out-of-band.

### 3.3 `_conversation_owners` LRU [LOW]

**File:** `advisory.py:127-148`

Conversation ownership is recorded at first POST and bounded at 10000
entries with LRU. If a user's conversation gets evicted (busy server, lots
of users), the next message from that user will silently re-set ownership
without verifying the prior owner. This is a small tenancy hole — at
extreme scale, conversation-level isolation can drift. With the current
single-buyer demo it is theoretical.

---

## 4. Three Fault Lines (COC Framework)

### 4.1 Anti-Amnesia — Where Knowledge Is Captured vs Lost [MEDIUM]

Captured well:

- KB provisions in `hr_advisory/kb/content/*.py` modules (Python
  source-of-truth for employment law). Versioned in git.
- `ANTI_AMNESIA_RULES` re-injected into every system prompt
  (`eatp_lineage.py:236-261`).
- Round 1 red-team findings → `recruitment-redteam-round1.md` and
  fix-tracking todo.
- Recruitment Wave 2 architectural decisions → in commit messages
  (9429c81 → 49feeb1).
- Test maintenance debt resolution → `.test-results`.

Lost or at risk:

- `_register_handlers` (CLI/MCP) was broken silently for "unknown
  duration" (per the brief). No regression test was added in the same
  session. I confirmed the import is now fixed (`platform.py:240`) but
  there is no automated test that exercises the CLI/MCP handlers, so it
  can break again.
- Old Kaizen pipeline modules (`agents/orchestration/`,
  `agents/specialists/`) are kept "for reference" but are dead code. New
  contributors will ask "is this used?" — the docstring says no, but
  there is no integration test that fails when they get re-imported by
  accident. Already happened once (`platform.py` had an import the test
  suite didn't catch).
- Provider priority swap (openai → gemini in `llm_context.py:90-114`)
  is documented in `.test-results` but not in any user-facing changelog
  or README. Existing customers with OPENAI_API_KEY still set would not
  notice unless they look at billing.

**Mitigation:**

- Add a CLI-channel smoke test in `tests/integration/test_cli_handlers.py`
  that invokes `advisory_query_handler` and `compliance_check_handler`
  directly. Catches the next silent breakage.
- Add a top-level ARCHITECTURE-DECISIONS.md (or a section in CLAUDE.md)
  capturing: "AdvisoryEngine replaced the Kaizen pipeline on commit
  4b3d4c6. The orchestration/ and specialists/ modules are kept as
  scaffolding for the synthesizer fallback but are not wired into the
  active path."
- Add a CHANGELOG.md entry for the provider-priority change.

### 4.2 Premature Certainty — Where the System Claims Authority [HIGH]

The advisory engine's confidence ladder (`advisory_engine.py:364-372`) is
an instruction in the system prompt, not a hard constraint. The model can
still hallucinate citations. The downstream guard (`citation_validator`
called at `advisory.py:540-547`) only validates _existing_ citation IDs
against the KB; it cannot detect a fabricated section number that happens
to look real.

`_search_python_kb` (`advisory_engine.py:431-551`) does keyword-overlap
scoring with a stop-word list. It returns "best-effort matches" with no
floor on score quality. If the engine searches for "non-existent topic
xyz", it gets back the top-5 unrelated provisions. The LLM then has 5
provisions in context and may cite them, conflating "I have provisions in
context" with "those provisions actually answer the question".

The `[CONFIDENCE: X.XX]` marker in the response is self-reported. There is
no calibration check that compares stated confidence to actual citation
density or KB coverage.

**Specific risks the system currently claims more authority than it has:**

1. "TAFEP-compliant" — the TAFEP scan in recruitment is regex-based
   (`recruitment.py` calls a TAFEP scanner). Unicode homoglyphs bypass it
   (round 1 LOW finding). Marketing should say "TAFEP-aligned screening"
   not "TAFEP-compliant".
2. "MOM-aligned" — KB content is hand-curated. There is no scheduled
   refresh or last-updated date on each provision. A user asking about
   2026 EP threshold gets the answer from whatever was in the KB at the
   most recent commit. `kb_currency_status: {d: "2026-03-01"}` in
   `advisory.py:509` is hardcoded.
3. "Trust chain recorded" — see §2.3 above. Persistence is best-effort;
   the user-facing claim is unconditional.

**Mitigation:**

- Add a minimum-score threshold to `_search_python_kb` (drop matches with
  score 0). If no matches reach threshold, return an empty list rather
  than the top-5 weak matches.
- Replace hardcoded `kb_currency_status` with an actual lookup against
  `LegalAct.last_updated` or equivalent.
- Soften marketing copy to "TAFEP-aligned" / "MOM-aligned KB" rather than
  "compliant" / "verified".
- Add a calibration test: sample 50 advisory responses with stated
  confidence, manually score actual correctness, plot the calibration
  curve. If overconfident, scale down all confidence outputs.

### 4.3 Proof Debt — Claims Without Audit Trail [MEDIUM]

Inventory of claims that need an audit trail and where they currently
stand:

| Claim                             | Audit trail today                     | Gap                                               |
| --------------------------------- | ------------------------------------- | ------------------------------------------------- |
| "TAFEP scan run before publish"   | Frontend toggles a flag; no DB record | Add `JobListing.tafep_scan_result` JSON           |
| "Compliance check passed"         | Cached for 5min, not persisted        | Add `ComplianceCheckResult` table, write each run |
| "Statutory floor warnings shown"  | Returned in response, not persisted   | Persist warnings on policy row                    |
| "Trust chain attestations"        | Best-effort, in-memory cache primary  | See §2.3                                          |
| "Rate limit enforced"             | In-memory, no log of 429s             | Log every 429 to a metrics counter                |
| "Candidate consented to PDPA"     | `pdpa_consent: true` + date stamp ✓   | OK — but no IP/user-agent capture                 |
| "Policy acknowledged by employee" | `PolicyAcknowledgment` row ✓          | OK                                                |
| "Onboarding step completed"       | `OnboardingStepProgress` row ✓        | OK                                                |
| "Hire decision was authorised"    | Activity note in `Candidate.notes`    | Notes are mutable; need immutable audit log       |

**Mitigation:** Add an immutable `AuditLog` table for hire, terminate,
policy publish, compliance check, advisory query (with hash, not body).
Write once, never update. Index by `(company_id, action, ts)`.

---

## 5. Architectural Debt

### 5.1 Old Kaizen Pipeline — Keep, Refactor, or Delete?

**Files:** `agents/orchestration/` and `agents/specialists/`.

Recommendation: **Delete.** Rationale:

- `orchestration/__init__.py` exports only `ResponseSynthesizerAgent` and
  describes the rest as "kept for reference but NOT used".
- The synthesizer is the only consumer; if there is no fallback path that
  uses it (verify by `grep ResponseSynthesizerAgent` across the codebase
  — likely zero callers outside its own module), it too is dead.
- Specialists are 7 files (`employment_act.py`, `cpf.py`, etc.) with
  domain prompts. The KB content modules already serve that purpose.
- Dead code that "looks alive" is the worst kind: contributors will read
  it, modify it, and assume it runs.
- We already paid the cost once (`platform.py` ImportError, `.test-results`
  notes 11 obsolete pipeline-wiring tests had to be deleted).

If keeping for the synthesizer fallback: extract just
`ResponseSynthesizerAgent` into `agents/synthesizer.py` and delete
everything else. Remove the directory.

If the synthesizer is actually dead too: delete both directories and
~2000 lines of dead code in one PR. Add a regression test that imports
`hr_advisory.api.platform` to confirm no further dead-code dependencies.

### 5.2 LLM Provider Priority [LOW — documentation]

The change from openai-first to gemini-first is now in
`llm_context.from_server_env`. It's not in any user-facing doc. Customers
with both keys set will silently bill Gemini instead of OpenAI. Add a
CHANGELOG.md or a per-company "Active provider: gemini" indicator in the
Settings page.

### 5.3 Other Silent Breakages (Like `_register_handlers`) [HIGH for hygiene]

The pattern that broke `_register_handlers` was: a module imported by name
at startup, the import succeeded, the symbol was wrong. Same pattern
exists in any place that uses lazy/runtime imports inside functions.
Audit list:

- `advisory_engine.py:417` — `from hr_advisory.kb.admin import
search_provisions` inside `_search_kb_with_fallback`. If renamed,
  failure is a tool-call error, not startup.
- `advisory.py:399, 597, 671` — inline imports of `onboarding_context`,
  `alerts._alerts_store`. Same pattern.
- `auth.py:597, 437` — inline imports of `auto_assign_default_onboarding`,
  `_find_invitation_by_token`.

Each of these is a silent breakage waiting to happen. Tests cover the
happy path; they do not cover "rename a function and see what breaks".

**Mitigation:** Add a `tests/import_smoke.py` that imports every router
module and every handler module at the top level and asserts no
ImportError. Run as part of the unit suite. Catches the
`platform.py`-style breakage at test time, not deploy time.

---

## Risk Register (consolidated, severity-tagged)

| #   | Finding                                                    | Severity | File                                           |
| --- | ---------------------------------------------------------- | -------- | ---------------------------------------------- |
| 1   | Role allow-list missing in recruitment.hire_candidate      | CRITICAL | `recruitment.py:1174`                          |
| 2   | Hire→onboard transition not transactional                  | HIGH     | `auth.py:483-616`                              |
| 3   | Resend email failure leaves recruitment state inconsistent | HIGH     | `recruitment.py:35-67`                         |
| 4   | Compliance cache not invalidated on policy CRUD            | MEDIUM   | `policies.py` (multiple), `compliance.py:49`   |
| 5   | Trust chain persistence is best-effort, never finalized    | MEDIUM   | `advisory.py:514`, `eatp_lineage.py:353-361`   |
| 6   | In-memory rate limiter dilutes with multi-process          | HIGH     | `rate_limit.py`                                |
| 7   | Resume files orphan on re-upload, deletion, PDPA purge     | MEDIUM   | `recruitment.py:1232-1300`                     |
| 8   | LLM degradation flag not in trust attestation              | MEDIUM   | `advisory_engine.py:963-980`                   |
| 9   | Old Kaizen pipeline modules are dead code                  | MEDIUM   | `agents/orchestration/`, `agents/specialists/` |
| 10  | No CLI/MCP integration test for handlers                   | HIGH     | `platform.py:212-303`                          |
| 11  | KB Python fallback returns weak matches with no threshold  | MEDIUM   | `advisory_engine.py:541-551`                   |
| 12  | `kb_currency_status` is hardcoded                          | MEDIUM   | `advisory.py:509`                              |
| 13  | `_escalate_risk_tier` defined but unused                   | LOW      | `advisory.py:179-183`                          |
| 14  | Inline lazy imports across routers — silent rename risk    | MEDIUM   | multiple                                       |
| 15  | No immutable audit log for hire/terminate/publish          | MEDIUM   | (system-wide)                                  |
| 16  | Provider priority change undocumented for users            | LOW      | (no CHANGELOG)                                 |

---

## Top 5 Things To Fix Before Next Deploy

1. **Role allow-list in `recruitment.hire_candidate`** (#1) — block
   `role ∈ {"platform_admin", "owner"}` from being passed via the hire
   request body. Currently a privilege-escalation path. 10-minute fix,
   regression test in `tests/regression/test_hire_role_allowlist.py`.

2. **Transactional hire→onboarding** (#2) — wrap User + Employee +
   LeaveBalance + OnboardingAssignment in a single DB transaction in
   `auth.register-employee`. Roll back invitation activation if any
   step fails. Without this, every email-delivery hiccup leaves orphan
   half-employees.

3. **Compliance cache invalidation on policy writes** (#4) — one-line
   import + four call sites in `policies.py`. Without this, demos run
   immediately after policy upload show stale "non-compliant". This is
   the single highest demo-confidence-erosion item.

4. **Persist trust chains and reflect persistence in response** (#5) —
   call `finalize_trust_chain(...)` at end of `advisory_query` and
   `advisory_stream`. Add `trust_chain.persisted: bool`. Without this,
   the "EATP-traceable" value claim has no audit trail.

5. **CLI/MCP smoke test** (#10) plus **import-smoke test** (#14) — add
   `tests/integration/test_cli_handlers.py` and a top-level
   `tests/test_imports.py` that imports every router. The
   `_register_handlers` outage was silent; the next one will be too
   without these guards.

Total effort: ~half a day. All five reduce specific failure modes seen or
inferred this session and are pre-conditions for trustworthy production
operation under real load.
