# M60: Production Hardening & SDK Alignment

**Context**: M01-M59 and M61-M65 are complete. The Delegate engine has replaced all specialist agents. This milestone closes the remaining gaps identified in the post-migration audit before the next feature push.

**Scope**: Dead code removal, test fixes, deployment hygiene, SDK alignment.

---

## T500: Delete PatchRunner (dead code)

**Files**: `src/hr_advisory/quality/patch_runner.py` (540 lines), related test files
**What**: PatchRunner targets specialist agent system prompts that no longer exist. `_AGENT_MODULE_MAP` is empty — every call raises ValueError. The adversarial runner it imports is independent and stays.

- Delete `patch_runner.py`
- Delete any test files that only test PatchRunner
- Remove imports of PatchRunner from `__init__.py` or other modules
- Verify `adversarial_runner.py` and `qa` models still work independently

**Why**: 540 lines of dead code that always raises ValueError. Violates zero-tolerance rule (known broken code must be fixed or deleted).

---

## T501: Delete HRIS API provider stub

**Files**: `src/hr_advisory/integrations/hris_adapters.py`
**What**: `_sync_api_provider()` raises `NotImplementedError` — a stub. CSV import works and is the active path.

- Remove the `_sync_api_provider` function
- Remove `_PROVIDER_ADAPTERS` dict entries that point to it
- Keep the CSV import path fully functional
- Update any router that exposes API sync to return a clear "CSV import only" response instead of raising

**Why**: No-stubs rule. The function exists to raise an error — just remove it and keep the working CSV path.

---

## T502: Fix tool count docstring

**File**: `src/hr_advisory/delegate/tools.py`
**What**: Module docstring claims "600+ HRIS CRUD endpoints" but only 207 tools are registered (6 always-active + ~201 discoverable). Update the docstring to reflect reality.

---

## T503: Investigate and fix integration test failures

**What**: 37 integration tests fail. Determine which are PostgreSQL-infrastructure issues vs actual code bugs.

- Run `pytest tests/integration/ -q --timeout=30 2>&1 | tail -50` to see failure summary
- Categorize: infrastructure (needs Postgres) vs code bugs
- Fix any code bugs found
- Mark infrastructure-only tests with `@pytest.mark.requires_postgres` or similar skip marker so CI can run clean

---

## T504: Production deploy env template

**File**: `deploy/.env.production.template` (new)
**What**: Create a deployment env template documenting all required variables. Currently credentials live in flat files at `/opt/arbor/` with no documentation.

- List all required env vars (DATABASE_URL, REDIS_URL, JWT_SECRET, SALARY_ENCRYPTION_KEY, OPENAI_API_KEY, etc.)
- Add comments explaining each
- Reference the flat-file credential locations
- Update `deploy/docker-compose.prod.yml` if it doesn't source these correctly

---

## T505: Close kailash-py#171

**What**: DataFlow import-time connection issue is fixed in 1.3.0. Close the GitHub issue.

- `gh issue close 171 --repo terrene-foundation/kailash-py --comment "Fixed in kailash-dataflow 1.3.0 (lazy connection). Verified in Arbor."`

---

## T506: Commit SDK version pin updates

**What**: pyproject.toml has been updated this session (kailash>=2.3.4, dataflow>=1.4.0, kaizen>=2.3.3, nexus>=1.6.1). COC artifacts synced to v1.2.0. Commit these changes.

---

## T507: Red team — Delegate advisory quality

**What**: Verify the Delegate engine produces correct, cited, safe advisory responses across the 6 regulatory domains.

- Test 10 queries across: Employment Act, CPF, Foreign Manpower (EFMA), Fair Employment (TAFEP), Workplace Safety (WSH), Tax (IRAS)
- Verify citations are present and accurate
- Verify guardrails block out-of-scope queries
- Verify safety chain runs (disclaimer, risk tier, trust chain)
- Compare quality to the advisory-quality brief benchmarks

---

## T508: Red team — Security & tenant isolation

**What**: Verify security boundaries hold under the Delegate architecture.

- Test tenant isolation (company A can't see company B's data)
- Test auth bypass attempts on advisory and shadow endpoints
- Test prompt injection defense (system prompt extraction, role-play jailbreaks)
- Test rate limiting enforcement
- Test NaN/Inf injection on calculator inputs
- Verify no secrets in API responses or logs

---

## T509: Red team — Production deployment verification

**What**: Verify the Docker image builds, the compose stack works, and production is stable.

- `docker build -f deploy/Dockerfile.backend -t arbor-backend:test .`
- Verify health endpoint responds
- Verify advisory streaming works end-to-end
- Check for resource leaks (connection pools, memory)
