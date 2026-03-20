# Architecture Assessment: BYOK Integration Points

## Current LLM Call Chain

```
HTTP Request (POST /advisory/query)
  → get_current_user() [JWT auth]
  → validate_company_access()
  → 13-step safety chain
  → _async_run_llm_advisory() [thread pool]
    → _run_llm_advisory()
      → QueryAnalyzerAgent(shared_memory)    ← config reads global settings
      → DispatchRouter()                      ← deterministic, no LLM
      → SpecialistAgent(shared_memory)        ← config reads global settings
      → ComplianceAgent(shared_memory)        ← config reads global settings
      → ResponseSynthesizerAgent(shared_memory) ← config reads global settings
        → BaseAgent.run()
          → WorkflowGenerator.generate()
            → LLMAgentNode._execute()
              → get_openai_config()           ← reads os.getenv("OPENAI_API_KEY")
              → openai.OpenAI(api_key=...)    ← ACTUAL API CALL
```

## Injection Points (Ranked by Elegance)

### Option A: Config-Level Override (Recommended)

Modify the agent config resolution to accept an optional `api_key` parameter that takes precedence over the environment variable.

**Touch points**:

1. `agents/config.py` — Add `api_key` field to all config dataclasses, pass through resolution
2. `advisory.py:_run_llm_advisory()` — Accept `api_key` param, pass to config constructors
3. `advisory.py:advisory_query()` — Retrieve user's API key, pass to pipeline

**Pros**: Clean, minimal changes, works with existing Kaizen pattern
**Cons**: Requires Kaizen's `get_openai_config()` to also accept override

### Option B: Context Variable (Python contextvars)

Use Python's `contextvars` to set a request-scoped API key that Kaizen reads.

**Touch points**:

1. Create `_openai_api_key_var = contextvars.ContextVar("openai_api_key")`
2. Set in FastAPI middleware or dependency
3. Kaizen's `get_openai_config()` checks contextvar first, then env

**Pros**: No parameter threading through call chain
**Cons**: Implicit coupling, harder to test, may not work across thread pool boundary (ThreadPoolExecutor doesn't propagate contextvars by default)

### Option C: Environment Variable Per-Request (Temporary Override)

Temporarily set `os.environ["OPENAI_API_KEY"]` per request.

**Pros**: Zero code changes to Kaizen
**Cons**: Race condition nightmare in concurrent requests. **NOT viable.**

## Recommended Approach: Option A with Fallback Chain

```
User's stored key (DB, encrypted)
  → falls back to → Server .env key (operator-provided)
    → falls back to → Ollama (local, free)
      → falls back to → No LLM available (deterministic-only mode)
```

This preserves backward compatibility: if a user hasn't set a key, the server's key is used (or Ollama, or no LLM).

## What Needs to Change

### Backend (Arbor)

1. **New model**: `UserLLMConfig` — stores encrypted API key per user
2. **New endpoints**: CRUD for user API keys (save, delete, validate)
3. **Config threading**: Pass user's key through the advisory pipeline
4. **Agent config override**: All 6 config dataclasses accept optional `api_key`
5. **Encryption**: Reuse existing Fernet pattern from salary encryption

### Kaizen Framework (Upstream)

6. **`get_openai_config()` override**: Accept optional `api_key` parameter
7. **`LLMAgentNode`**: Accept `api_key` from config rather than always reading env

**Important**: Changes 6-7 are in the Kailash SDK, not Arbor. Two options:

- **Monkey-patch**: Override `get_openai_config` at Arbor level (quick, dirty)
- **Upstream PR**: Add `api_key` parameter to Kaizen's provider config (clean, slower)

Given this is a Terrene Foundation project with control over both repos, the upstream PR is the right path.

### Frontend (Web)

8. **Settings page**: API key input form with validation
9. **Onboarding prompt**: First-time "enter your API key to enable AI advisory"
10. **Status indicator**: Show whether AI advisory is available or key-needed

### What Stays the Same

- Embedding pipeline (`kb/embeddings.py`) — batch operation, uses server key
- Quality tools (`llm_judge.py`, `mutation_engine.py`) — internal QA, uses server key
- KB search — deterministic DataFlow queries, no LLM
- 13-step safety chain — mostly deterministic, LLM is one step
- All non-advisory endpoints — pure HRIS, no LLM

## Security Considerations

1. **Encryption at rest**: Fernet (AES-128-CBC + HMAC-SHA256), key from `SALARY_ENCRYPTION_KEY` env var
2. **Never log keys**: Redact from all logging pipelines
3. **Validate before storing**: Hit OpenAI's models endpoint to verify key works
4. **Key masking in UI**: Only show last 4 chars after initial entry
5. **Deletion**: Hard-delete encrypted key from DB, not soft-delete
6. **No key in JWT/cookies**: Key lives in DB only, retrieved server-side per request
7. **Rate limiting**: Existing per-user rate limiter still applies
8. **PDPA**: API keys are credentials, not PII — no PDPA audit log needed (but encrypt anyway)
