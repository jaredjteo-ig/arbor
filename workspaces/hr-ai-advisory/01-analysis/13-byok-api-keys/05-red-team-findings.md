# Red Team Findings

## Critical Issues (Must Fix)

### C1: Global State Blocks Per-Request Key Resolution

- `get_settings()` is `@lru_cache(maxsize=1)` — API key baked in at first call
- `_resolved_provider` and `_resolved_model` are module-level globals in `agents/config.py`
- Once resolved on first request, ALL subsequent requests use that provider
- **Fix**: Restructure resolution to accept per-request overrides; don't cache provider/model globally

### C2: Use Separate Encryption Key

- Plan proposed reusing `SALARY_ENCRYPTION_KEY` for API keys — single point of compromise
- The codebase already uses separate keys: `INTEGRATION_ENCRYPTION_KEY` in `token_store.py`
- **Fix**: Use dedicated `LLM_KEY_ENCRYPTION_KEY`, block startup without it in production

### C3: `has_llm_available()` Short-Circuits Before Company Key Check

- This function checks server env key and Ollama — returns False if neither exists
- Called BEFORE company key resolution in `_run_llm_advisory()`
- In pure BYOK deployment, pipeline never reaches company key
- **Fix**: Refactor to accept optional company_id or move check after key resolution

## Major Issues (Should Fix)

### M1: Both `/query` AND `/stream` Endpoints Need BYOK

- `/stream` at `advisory.py:1439` duplicates the entire safety chain
- Plan only mentions `/query` — both need identical key resolution

### M2: Add Basic Usage Tracking at Launch

- Without per-company query counting, admins get surprise OpenAI bills
- Minimal: `company_llm_usage` counter (company_id, date, query_count)
- Expose on admin settings page

### M3: Key Validation Should Use Actual Completion, Not GET /models

- `GET /models` succeeds even with $0 balance
- Use minimal completion call (`max_tokens=1`) to verify billing works
- Cost: < $0.001 per validation

### M4: Investigate Kaizen BaseAgent Before Implementing

- Critical unknown: does `BaseAgent.run()` read config.api_key or re-resolve from os.getenv?
- If it re-resolves, parameter threading alone won't work — upstream change is blocking
- **Must read Kaizen source before committing to implementation plan**

## Significant Issues

### S1: Multi-Admin Key Audit Trail

- Add `updated_by` to CompanyLLMConfig model
- Log key changes to audit trail

### S2: Stale Key Detection

- After 401 from OpenAI, mark config as `status=invalid`
- Skip API calls until key is updated (don't keep hitting a dead key)

### S3: Normalize Error Messages

- Don't pass through OpenAI's error text (leaks key validity info)
- Map to generic categories: `key_invalid`, `quota_exceeded`, `service_unavailable`

### S4: Handle Memory Cleanup for Decrypted Keys

- Python GC doesn't zero memory — decrypted keys persist in heap
- Follow trust-plane pattern: explicitly overwrite key variable after use

## Noted (Low Priority)

- N1: Quality tools (`llm_judge.py`, `mutation_engine.py`) need graceful handling when no server key
- N2: Embedding pipeline should log clearly when no server key available
- N3: Document Fernet key rotation procedure for encrypted API keys
- N4: Consider `BYOK_ENABLED` deployment flag for self-hosted single-company setups
