# BYOK API Keys + Budget-Capped Default — Todo Roadmap

**Milestone**: M60 (BYOK)
**Plan**: `02-plans/03-byok-api-keys-plan.md`
**Analysis**: `01-analysis/13-byok-api-keys/`
**User Flows**: `03-user-flows/04-byok-api-key-flows.md`

---

## M60-P0: Investigation (Must Complete First)

### T399: Investigate Kaizen BaseAgent API key consumption path

**Priority**: BLOCKER — determines entire implementation approach
**Files to read** (in kailash-kaizen, NOT this repo):

- `packages/kailash-kaizen/src/kaizen/core/base_agent.py` — `BaseAgent.run()`, `to_workflow()`, `WorkflowGenerator`
- `packages/kailash-kaizen/src/kaizen/config/providers.py` — `get_openai_config()`, `get_ollama_config()`
- `packages/kailash-kaizen/src/kaizen/nodes/ai/llm_agent.py` — `LLMAgentNode._execute()`

**Questions to answer**:

1. Does `BaseAgent.run()` read `api_key` from the config object or re-resolve from `os.getenv("OPENAI_API_KEY")`?
2. Does `get_openai_config()` accept an optional `api_key` parameter?
3. Does `get_ollama_config()` accept a custom `base_url` parameter?
4. Can `ProviderConfig` carry a per-request api_key through the workflow execution?

**Decision gate**:

- If config object fields are passed through → proceed with parameter threading (no upstream PR needed)
- If `os.getenv` is called at execution time → file upstream PR to kailash-kaizen first, BLOCK until merged

**Deliverable**: Decision document in `01-analysis/13-byok-api-keys/07-kaizen-investigation.md`

---

## M60-P1: Pipeline Refactor (Backend)

### T400: Create LLMKeyContext dataclass

**File**: `src/hr_advisory/agents/llm_context.py` (new)
**What**:

- Dataclass: `api_key`, `provider` ("openai"|"ollama"|"custom"), `model`, `base_url`, `is_byok` (bool)
- Factory method: `from_company_config(config: CompanyLLMConfig)` → decrypts key, builds context
- Factory method: `from_server_env()` → reads .env settings, builds context
- Factory method: `for_ollama(base_url, model)` → builds Ollama context
- `to_dict()` and `__repr__` that mask the API key

**Security**: `api_key` field must NOT appear in `__repr__`, logs, or serialization. Mask to last 4 chars.

### T401: Refactor global state in agents/config.py

**File**: `src/hr_advisory/agents/config.py`
**What**:

- Remove module-level `_resolved_provider` and `_resolved_model` globals
- Change `_resolve_provider_and_model()` to accept optional `LLMKeyContext` parameter
- If context provided → use its provider/model/api_key
- If no context → fall back to current behavior (read from settings/env)
- Update `has_llm_available()` to accept optional `company_id` parameter
  - If company_id given → check CompanyLLMConfig first
  - Then check server env key
  - Then check Ollama
- All 7 config dataclasses (`QueryAnalyzerConfig`, `QueryClarifierConfig`, `OrchestratorConfig`, `ResponseSynthesizerConfig`, `SpecialistConfig`, `ComplianceConfig`, `DocumentGenerationConfig`) gain optional `api_key` and `base_url` fields
- `__post_init__` uses explicit values if set, falls back to resolution only when empty

**Red team C1, C3**: This directly addresses the global state and has_llm_available short-circuit issues.

### T402: Thread LLMKeyContext through advisory /query pipeline

**File**: `src/hr_advisory/api/routers/advisory.py`
**What**:

- In `advisory_query()` (line ~355): after auth + company validation, resolve `LLMKeyContext`:
  1. Check CompanyLLMConfig for company_id → build context from it
  2. Else build context from server env
- Pass context to `_async_run_llm_advisory()`
- In `_run_llm_advisory()` (line ~961): accept `llm_context: LLMKeyContext` parameter
- Pass context fields to every agent config constructor:
  - `QueryAnalyzerAgent(config=QueryAnalyzerConfig(llm_provider=ctx.provider, model=ctx.model, ...))`
  - Same for all specialists, compliance, synthesizer
- After LLM call: extract token usage from response, pass to budget tracking (T409)

**Red team M1 (partial)**: This covers /query. T403 covers /stream.

### T403: Thread LLMKeyContext through advisory /stream pipeline

**File**: `src/hr_advisory/api/routers/advisory.py`
**What**:

- Same as T402 but for `advisory_stream()` (line ~1439)
- Identical key resolution logic
- Identical context threading through agent configs
- Must handle streaming response token counting (may need post-stream accumulation)

**Red team M1**: Both endpoints now covered.

### T404: Verify backward compatibility — no behavior change with .env key

**What**:

- Run existing advisory tests with current .env configuration
- Confirm: when no CompanyLLMConfig exists, behavior is identical to pre-refactor
- Confirm: `_resolve_provider_and_model()` without context returns same result as before
- Confirm: existing Ollama auto-detection still works

**Acceptance**: All existing advisory tests pass. No .env changes needed.

---

## M60-P2: Storage + Budget (Backend)

### T405: Add CompanyLLMConfig DataFlow model

**File**: `src/hr_advisory/models/company_user.py` (add to existing models)
**What**:

```
CompanyLLMConfig:
  id              auto PK
  company_id      FK to Company
  provider        string ("openai"|"ollama"|"custom")
  encrypted_key   text (nullable — NULL for Ollama)
  model_pref      string (nullable — defaults per provider)
  base_url        string (nullable — required for Ollama)
  status          string ("active"|"invalid"|"revoked"), default "active"
  updated_by      integer (user_id)
  is_active       boolean, default True
  created_at, updated_at
```

- Unique constraint on (company_id, provider, is_active=True)
- Soft delete via is_active flag

### T406: Add CompanyLLMUsage DataFlow model

**File**: `src/hr_advisory/models/company_user.py` (add to existing models)
**What**:

```
CompanyLLMUsage:
  id              auto PK
  company_id      FK to Company
  month           date (first of month)
  query_count     integer, default 0
  input_tokens    integer, default 0
  output_tokens   integer, default 0
  estimated_cost  float, default 0.0 (USD)
  updated_at
```

- Unique constraint on (company_id, month)
- Upsert pattern: increment on each query

### T407: Create LLM key encryption service

**File**: `src/hr_advisory/security/llm_encryption.py` (new)
**What**:

- Dedicated Fernet encryption using `LLM_KEY_ENCRYPTION_KEY` env var
- `encrypt_api_key(plaintext: str) -> str` — returns base64-encoded ciphertext
- `decrypt_api_key(ciphertext: str) -> str` — returns plaintext
- NO plaintext fallback (unlike salary encryption dev mode)
- Raise `ConfigurationError` if env var not set in production
- Dev mode: allow a deterministic fallback key derived from `JWT_SECRET_KEY` (with warning log)

**Red team C2**: Separate from salary encryption key.

### T408: Add CRUD endpoints for LLM config

**File**: `src/hr_advisory/api/routers/company.py` (add to existing company router)
**What**:

- `POST /companies/{id}/llm-config` — Save BYOK key or Ollama config
  - Admin-only (role check)
  - Tenant isolation (company_id matches user's company)
  - Encrypt API key before storage
  - Set `updated_by` to current user
  - Validate key/endpoint before saving (call T411)
- `GET /companies/{id}/llm-config` — Get config with masked key
  - Admin-only
  - Return: provider, status, model_pref, base_url, masked key (last 4 chars), updated_by, updated_at
  - NEVER return the full encrypted or decrypted key
- `DELETE /companies/{id}/llm-config` — Remove config
  - Admin-only
  - Hard-delete the encrypted key column (set to NULL), set is_active=False
  - PDPA audit log entry for the deletion
- `GET /companies/{id}/llm-usage` — Get current month usage
  - Admin-only
  - Return: query_count, input_tokens, output_tokens, estimated_cost, budget_limit ($5.00), budget_remaining

**Red team S1**: `updated_by` audit trail included.

### T409: Budget tracking + enforcement logic

**File**: `src/hr_advisory/services/llm_budget.py` (new)
**What**:

- `check_budget(company_id: int) -> BudgetCheckResult`
  - Fetch CompanyLLMUsage for current month
  - Return: `allowed` (bool), `remaining_usd` (float), `warning` (bool if >80%), `used_usd`, `query_count`
  - Monthly cap: $5.00 (hardcoded constant `DEFAULT_MONTHLY_BUDGET_USD = 5.00`)
- `record_usage(company_id: int, input_tokens: int, output_tokens: int, model: str)`
  - Calculate cost from token counts and model pricing:
    - gpt-5-mini: ($0.25 _ input / 1M) + ($2.00 _ output / 1M)
    - gpt-5-chat-latest: ($1.25 _ input / 1M) + ($10.00 _ output / 1M)
  - Upsert CompanyLLMUsage: increment query_count, tokens, estimated_cost
- Model pricing table as a dict constant (easy to update)
- Budget check happens BEFORE LLM call in the advisory pipeline
- Usage recording happens AFTER LLM call (using actual token counts from OpenAI response `usage` field)

### T410: Integrate budget check into advisory pipeline

**File**: `src/hr_advisory/api/routers/advisory.py`
**What**:

- In `advisory_query()` and `advisory_stream()`, after resolving LLMKeyContext:
  - If `ctx.is_byok` → skip budget check
  - If using server key → call `check_budget(company_id)`
    - If `not allowed` → return 429 with `budget_exceeded` response (no LLM call)
    - If `warning` → set flag, include budget warning in final response
- After LLM call completes:
  - Extract `usage.prompt_tokens` and `usage.completion_tokens` from OpenAI response
  - Call `record_usage(company_id, prompt_tokens, completion_tokens, model)`
- Include `budget_info` in response JSON when using server key:
  ```json
  {
    "budget_info": {
      "used": 2.34,
      "limit": 5.0,
      "queries_this_month": 234,
      "warning": false
    }
  }
  ```

### T411: Key/endpoint validation endpoint

**File**: `src/hr_advisory/api/routers/company.py`
**What**:

- `POST /companies/{id}/llm-config/validate`
  - Admin-only
  - Accept: `{ provider, api_key?, base_url?, model? }`
  - For OpenAI: make minimal completion call (`max_tokens=1`, simple prompt) to verify key works AND billing is active
  - For Ollama: hit `{base_url}/api/tags`, verify model exists in the list
  - Return: `{ valid: bool, error?: string, provider_info?: { models: [...] } }`
  - Rate limit: max 5 validation attempts per minute per company (prevent brute-force)

**Red team M3**: Uses actual completion, not just GET /models.

---

## M60-P3: Ollama/DGX Support (Backend)

### T412: Configurable Ollama endpoint per company

**File**: `src/hr_advisory/agents/config.py`, `src/hr_advisory/agents/llm_context.py`
**What**:

- When `LLMKeyContext.provider == "ollama"`:
  - Use `LLMKeyContext.base_url` instead of server default `OLLAMA_BASE_URL`
  - Use `LLMKeyContext.model` instead of auto-detected model
- Verify Kaizen's Ollama provider supports custom base_url (from T399 investigation)
- If not: add `base_url` parameter to the Ollama config path in Kaizen (upstream)

### T413: Ollama health check service

**File**: `src/hr_advisory/services/ollama_health.py` (new)
**What**:

- `check_ollama_health(base_url: str, model: str | None = None) -> OllamaHealthResult`
  - Hit `{base_url}/api/tags` with 5-second timeout
  - Return: `reachable` (bool), `models` (list), `model_available` (bool if specific model requested)
- Used by: T411 (validation endpoint), T412 (runtime fallback check)

---

## M60-P4: Frontend

### T414: AI Configuration settings page

**File**: `apps/web/src/app/(dashboard)/settings/ai/page.tsx` (new)
**What**:

- New settings sub-page at `/settings/ai`
- Add "AI Configuration" link in settings navigation (existing `settings/page.tsx` sidebar)
- Three sections:
  1. **Current Status**: show active provider, model, usage this month, budget bar
  2. **Use Your Own OpenAI Key**: form with masked key input, validate button, save/delete
  3. **Connect to Local AI (Ollama)**: form with endpoint URL + model name, test connection button
- Admin-only page (redirect non-admins)
- Uses TanStack Query for API calls
- Design: match existing settings page patterns (AppCard, AppButton, ToggleSwitch)

### T415: API service layer for LLM config

**File**: `apps/web/src/services/api/llm-config.ts` (new)
**What**:

- `getLLMConfig(companyId)` → GET /companies/{id}/llm-config
- `saveLLMConfig(companyId, data)` → POST /companies/{id}/llm-config
- `deleteLLMConfig(companyId)` → DELETE /companies/{id}/llm-config
- `validateLLMConfig(companyId, data)` → POST /companies/{id}/llm-config/validate
- `getLLMUsage(companyId)` → GET /companies/{id}/llm-usage

### T416: Budget indicator in advisory chat

**File**: `apps/web/src/app/(dashboard)/advisory/page.tsx` (modify existing)
**What**:

- After each response, if `budget_info` is present in the response:
  - Show usage bar: "12 of ~500 free queries this month"
  - If `warning`: show amber banner "Free AI allowance almost used up"
- If response indicates `budget_exceeded`:
  - Show friendly message (see user flow 5)
  - Admin: "Go to Settings" button
  - Employee: "Ask your admin" message
- If response indicates `llm_available: false`:
  - Show setup prompt (see user flow 1)

### T417: Add AI settings link to settings navigation

**File**: `apps/web/src/app/(dashboard)/settings/page.tsx` (modify)
**What**:

- Add "AI Configuration" card/link in the settings page
- Icon: `Brain` (already imported from lucide-react)
- Only visible to admins
- Badge showing current status: "Free tier" / "Custom key" / "Ollama"

---

## M60-P5: Polish + Security

### T418: Error message normalization for LLM provider errors

**File**: `src/hr_advisory/services/llm_errors.py` (new)
**What**:

- `normalize_llm_error(error: Exception, provider: str) -> LLMErrorResult`
- Map OpenAI errors to categories:
  - 401 → `key_invalid` ("Your API key is no longer valid")
  - 429 → `rate_limited` ("The AI service is busy, try again in a moment")
  - 402/insufficient_quota → `quota_exceeded` ("Your OpenAI account needs more credits")
  - 500/503 → `service_unavailable` ("The AI service is temporarily down")
  - Timeout → `timeout` ("The request took too long")
- Map Ollama errors:
  - Connection refused → `endpoint_unreachable` ("Cannot reach the AI service")
  - Model not found → `model_unavailable` ("The selected model is not available")
- NEVER pass through raw OpenAI/Ollama error text to the frontend

**Red team S3**: Normalized error messages.

### T419: Stale key detection + auto-invalidation

**File**: `src/hr_advisory/api/routers/advisory.py`, `src/hr_advisory/services/llm_budget.py`
**What**:

- When an LLM call returns 401 (key invalid):
  - Mark CompanyLLMConfig `status = "invalid"`
  - Fall back to server key for current request (if budget allows)
  - Include `key_status: "invalid"` in response so frontend can prompt update
- When admin saves a new key:
  - Reset status to "active"
- On GET /llm-config: include status in response so settings page shows warning

**Red team S2**: Stale key detection.

### T420: Decrypted key memory cleanup

**File**: `src/hr_advisory/agents/llm_context.py`
**What**:

- After LLM call completes (in `_run_llm_advisory`), explicitly clear the decrypted key:
  ```python
  if llm_context and llm_context.api_key:
      # Overwrite the string reference (best effort in CPython)
      llm_context = None
  ```
- Add context manager pattern: `with llm_context.decrypted() as key:` that clears on exit
- Follow trust-plane security rule (MUST NOT 4: Leave Private Key Material in Memory)

**Red team S4**: Memory cleanup for decrypted keys.

### T421: Update .env.example with new config

**File**: `.env.example`
**What**:

- Update `OPENAI_PROD_MODEL` comment to show `gpt-5-mini-2025-08-07` as the default
- Add `LLM_KEY_ENCRYPTION_KEY` entry (commented, with instruction to generate)
- Add `OLLAMA_BASE_URL` entry (commented, showing default `http://localhost:11434`)
- Add `OLLAMA_MODEL` entry (commented)
- Update the header comment to explain the BYOK model
- Remove any suggestion that `OPENAI_API_KEY` is required (make clear it's for server-level default)

### T422: Update deploy/.env.prod.example

**File**: `deploy/.env.prod.example`
**What**:

- Add `LLM_KEY_ENCRYPTION_KEY=CHANGE_ME` (required in production)
- Update model references to gpt-5-mini
- Add Ollama config section (commented)

### T423: Graceful handling when no server key and no BYOK

**Files**:

- `src/hr_advisory/kb/embeddings.py` — log clearly when no OPENAI_API_KEY, don't crash
- `src/hr_advisory/quality/llm_judge.py` — skip gracefully when no key available
- `src/hr_advisory/quality/mutation_engine.py` — skip gracefully when no key available
- Advisory pipeline: return structured `llm_available: false` response

**Red team N1, N2**: Quality tools handle missing server key gracefully.

---

## M60-P6: Testing

### T424: Unit tests for LLMKeyContext

**File**: `tests/unit/test_llm_context.py` (new)
**What**:

- Test `from_company_config()` correctly decrypts and builds context
- Test `from_server_env()` reads settings correctly
- Test `for_ollama()` builds Ollama context
- Test `__repr__` masks API key
- Test `to_dict()` masks API key

### T425: Unit tests for budget tracking

**File**: `tests/unit/test_llm_budget.py` (new)
**What**:

- Test `check_budget()`: under limit, at warning (80%), at limit (100%), over limit
- Test `record_usage()`: correct cost calculation for gpt-5-mini and gpt-5-chat-latest
- Test monthly reset: new month creates new row
- Test model pricing table accuracy

### T426: Unit tests for LLM key encryption

**File**: `tests/unit/test_llm_encryption.py` (new)
**What**:

- Test encrypt/decrypt roundtrip
- Test different keys produce different ciphertext
- Test decryption with wrong key fails
- Test missing env var raises ConfigurationError

### T427: Integration tests for LLM config endpoints

**File**: `tests/integration/test_llm_config_endpoints.py` (new)
**What**:

- Test POST /llm-config: save OpenAI key, verify encrypted in DB
- Test POST /llm-config: save Ollama endpoint, verify stored
- Test GET /llm-config: returns masked key, never full key
- Test DELETE /llm-config: key hard-deleted from DB
- Test GET /llm-usage: returns budget info
- Test admin-only access (non-admin gets 403)
- Test tenant isolation (can't access other company's config)
- Test validation endpoint with mock OpenAI/Ollama

### T428: Integration test for budget enforcement

**File**: `tests/integration/test_budget_enforcement.py` (new)
**What**:

- Test advisory query increments usage counters
- Test advisory blocked when budget exceeded
- Test BYOK queries skip budget check
- Test budget warning at 80%
- Test monthly reset behavior

### T429: Integration test for provider resolution chain

**File**: `tests/integration/test_provider_resolution.py` (new)
**What**:

- Test: company with BYOK → uses BYOK key
- Test: company with Ollama → uses Ollama endpoint
- Test: company with nothing → uses server key
- Test: no server key + no BYOK → returns llm_available=false
- Test: BYOK key invalid → falls back to server key
- Test: Ollama endpoint down → falls back to server key

---

## M60-P7: Gap Fills (From Red Team)

### T430: Database migration for new models

**Files**: migration scripts (Alembic or raw SQL)
**What**:

- Generate and apply migrations for CompanyLLMConfig and CompanyLLMUsage tables
- DataFlow model definition does NOT auto-create tables in PostgreSQL
- Must run before any CRUD endpoint is usable
- Include rollback migration

**Depends on**: T405, T406

### T431: Tenant isolation + admin permission enforcement on BYOK endpoints

**File**: `src/hr_advisory/api/routers/company.py`
**What**:

- All BYOK endpoints (T408) MUST enforce:
  - `company_id` matches authenticated user's company (tenant isolation)
  - User has admin role (role check)
  - Input validation: `math.isfinite()` on all numeric fields per trust-plane rules
  - NaN/Inf guard on budget cost values
- Reuse existing `validate_company_access()` and `require_admin()` patterns from other routers

**Red team G2, G12, G19 (partial)**: Tenant isolation + permissions + NaN validation.

### T432: Atomic budget deduction (transaction-safe)

**File**: `src/hr_advisory/services/llm_budget.py`
**What**:

- Budget check + deduction MUST be atomic to prevent TOCTOU race
- Two employees hitting /query simultaneously could both read "$4.95 remaining" and both proceed
- Use DataFlow upsert with `estimated_cost + $cost <= $5.00` as a WHERE condition
- If upsert affects 0 rows → budget exceeded (fail-closed)
- This replaces the naive "read then write" pattern in T409

**Red team G19**: Concurrent request budget race condition.

### T433: Runtime provider failover chain

**File**: `src/hr_advisory/api/routers/advisory.py`
**What**:

- When BYOK key fails at runtime (401, 403, quota exceeded):
  1. Mark key as invalid (T419)
  2. Attempt fallback to server key (if budget allows)
  3. If fallback succeeds: include `"provider_fallback": true` in response
  4. If fallback also fails: return structured error
- When Ollama endpoint times out:
  1. Attempt fallback to server key
  2. Same fallback indication in response
- NEVER silently switch providers without telling the user

**Red team G15**: Runtime failover.

### T434: PDPA audit logging for key lifecycle events

**File**: `src/hr_advisory/api/routers/company.py`
**What**:

- Log to PdpaAccessLog (existing pattern) for:
  - Key created (who, when, provider)
  - Key viewed (masked, who, when)
  - Key deleted (who, when)
  - Key decrypted for advisory use (company_id, timestamp — NOT the key itself)
  - Key status changed (active → invalid, who/what triggered)
- Reuse existing `log_pdpa_access()` helper

**Red team G4**: Audit logging for sensitive credential operations.

### T435: Token pricing lookup table

**File**: `src/hr_advisory/services/llm_budget.py`
**What**:

- Dict constant mapping model → (input_cost_per_million, output_cost_per_million):
  ```python
  MODEL_PRICING = {
      "gpt-5-mini-2025-08-07": (0.25, 2.00),
      "gpt-5-mini": (0.25, 2.00),
      "gpt-5-chat-latest": (1.25, 10.00),
  }
  ```
- Fallback: if model not in table, use gpt-5-mini pricing (conservative)
- Ollama models: cost = 0 (always)
- Easy to update when OpenAI changes pricing

**Red team G9**: Pricing table dependency for budget tracking.

### T436: Streaming budget enforcement

**File**: `src/hr_advisory/api/routers/advisory.py`
**What**:

- For /stream endpoint: budget is checked BEFORE the stream starts (same as /query)
- Token counting happens AFTER stream completes (accumulate from SSE chunks or from final usage)
- If a single streaming response overshoots the remaining budget, allow it to complete (don't cut mid-stream) but record the overage
- The $5 cap is a soft cap — a single query can push slightly over, but the NEXT query will be blocked
- This is simpler than mid-stream termination and avoids broken responses

**Red team G17, G38**: Streaming-specific budget handling. Pragmatic approach — soft cap, don't cut mid-stream.

### T437: DGX scoping note

**Note**: DGX support is delivered via Ollama compatibility. NVIDIA DGX systems run Ollama-compatible endpoints (or can be configured to). The Ollama endpoint URL + model name pattern covers DGX without additional DGX-specific tasks. If the institution's DGX uses a non-Ollama API, that's a future "custom" provider task.

**Red team G11, G40**: Explicitly scoped — DGX = Ollama-compatible endpoint.

---

## Summary

| Phase | Todos     | Description                    |
| ----- | --------- | ------------------------------ |
| P0    | T399      | Kaizen investigation (BLOCKER) |
| P1    | T400-T404 | Pipeline refactor              |
| P2    | T405-T411 | Storage + budget               |
| P3    | T412-T413 | Ollama/DGX support             |
| P4    | T414-T417 | Frontend                       |
| P5    | T418-T423 | Polish + security              |
| P6    | T424-T429 | Testing                        |
| P7    | T430-T437 | Gap fills from red team        |

**Total: 39 todos (T399-T437)**
**Dependencies**: T399 is a BLOCKER. P1 depends on T399. P2 depends on P1. P3 depends on P1. P4 depends on P2. P5-P7 can partially run in parallel with P4. T430 (migration) must complete before any P2 endpoint is usable. T431 (tenant isolation) must be part of T408 implementation. T432 (atomic budget) must be part of T409 implementation.

**Red team gaps addressed**: G1 (migration → T430), G2/G12 (tenant+perm → T431), G4 (audit → T434), G9 (pricing → T435), G11 (DGX → T437), G15 (failover → T433), G17 (streaming → T436), G19 (race condition → T432). Feature flag (G5) deferred — the refactor is backward-compatible by design (no company config = use server key = same as today). Rate limiting on validation (G3) folded into T411 (already specified).

---

## M60-P8: Previously Deferred — Now In Scope

### T438: Encryption key rotation support

**File**: `src/hr_advisory/security/llm_encryption.py`, new management command
**What**:

- `rotate_encryption_key(old_key: str, new_key: str)` function
- Reads all CompanyLLMConfig rows with encrypted_key != NULL
- Decrypts each with old key, re-encrypts with new key, writes back
- Atomic per-row (transaction per update)
- CLI command: `python -m hr_advisory.cli rotate-llm-keys --old-key ENV --new-key ENV`
- Logs rotation events to PDPA audit trail (T434)
- Verifies decrypt works with new key before committing

### T439: BYOK observability — metrics and alerts

**Files**: `src/hr_advisory/services/llm_metrics.py` (new), advisory.py modifications
**What**:

- Structured logging for every LLM call:
  - `llm.call` event: company_id, provider, model, input_tokens, output_tokens, cost_usd, duration_ms, is_byok
  - `llm.budget.warning` event: company_id, used_usd, limit_usd
  - `llm.budget.exceeded` event: company_id
  - `llm.key.invalid` event: company_id, provider
  - `llm.fallback` event: company_id, from_provider, to_provider
- Metrics counters (for Prometheus/StatsD if connected):
  - `llm_requests_total` (labels: provider, model, is_byok)
  - `llm_tokens_total` (labels: direction=input/output, model)
  - `llm_cost_usd_total` (labels: model, is_byok)
  - `llm_budget_exceeded_total`
  - `llm_key_invalid_total`
- Use existing structlog pattern from the codebase

### T440: Multi-provider BYOK (Anthropic, Gemini, DeepSeek, Mistral)

**Files**: `src/hr_advisory/agents/llm_context.py`, `src/hr_advisory/agents/config.py`, config endpoints
**What**:

- Extend `CompanyLLMConfig.provider` enum: "openai" | "anthropic" | "gemini" | "deepseek" | "mistral" | "ollama" | "custom"
- Extend `LLMKeyContext` to carry provider-specific config
- Extend `_resolve_provider_and_model()` to handle each provider
- Extend validation endpoint (T411) to test each provider's API
- Extend pricing table (T435) with per-provider pricing
- Frontend: provider dropdown in BYOK form (T414)
- Each provider maps to a Kaizen provider config (Kaizen already supports openai, anthropic, ollama)
- For providers Kaizen doesn't support natively: use OpenAI-compatible endpoint with custom base_url (DeepSeek, Mistral support this)

### T441: Adjustable budget caps

**Files**: `src/hr_advisory/services/llm_budget.py`, company router, frontend
**What**:

- Add `monthly_budget_usd` field to Company model (default 5.00)
- Admin can adjust in Settings > AI Configuration
- `POST /companies/{id}/llm-budget` — Set budget (admin only)
- `GET /companies/{id}/llm-budget` — Get budget config
- Budget enforcement reads from company config, not hardcoded $5
- Frontend: budget adjustment slider/input in AI settings page
- Minimum: $1.00, Maximum: $100.00 (prevent accidental $10,000 bills)
- PDPA audit log for budget changes

### T442: Per-user API keys (optional override)

**Files**: new model, new endpoints, frontend
**What**:

- New model `UserLLMConfig` — same schema as CompanyLLMConfig but with user_id
- Resolution chain becomes:
  1. User's BYOK key (if set)
  2. Company's BYOK key (if set)
  3. Company's Ollama endpoint (if set)
  4. Server key (budget-capped)
  5. Server Ollama
  6. No LLM
- New endpoints under `/users/me/llm-config` (self-service, no admin needed)
- Frontend: "Personal AI Key" section in user profile settings
- Per-user keys skip company budget (user pays their own)
- Per-user keys inherit company Ollama config if no personal key

### T443: Tests for P8 features

**Files**: new test files
**What**:

- `tests/unit/test_key_rotation.py` — rotation roundtrip, partial failure recovery
- `tests/unit/test_llm_metrics.py` — metric emission verification
- `tests/integration/test_multi_provider.py` — each provider validates and routes correctly
- `tests/integration/test_adjustable_budget.py` — custom budget limits enforced
- `tests/integration/test_per_user_keys.py` — user key takes precedence over company key

---

## Summary

| Phase | Todos     | Description                        |
| ----- | --------- | ---------------------------------- |
| P0    | T399      | Kaizen investigation (BLOCKER)     |
| P1    | T400-T404 | Pipeline refactor                  |
| P2    | T405-T411 | Storage + budget                   |
| P3    | T412-T413 | Ollama/DGX support                 |
| P4    | T414-T417 | Frontend                           |
| P5    | T418-T423 | Polish + security                  |
| P6    | T424-T429 | Testing                            |
| P7    | T430-T437 | Gap fills from red team            |
| P8    | T438-T443 | Previously deferred — now in scope |

**Total: 45 todos (T399-T443)**
**Dependencies**: T399 is a BLOCKER. P1→P2→P3→P4 sequential. P5-P8 can partially parallelize after P2. T430 (migration) before any endpoint. T440 (multi-provider) extends T401/T408/T411/T414.
