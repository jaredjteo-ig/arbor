# Plan: BYOK API Keys + Budget-Capped Default

## Decision

Keep the server's OpenAI key as default (gpt-5-mini, $5/month cap per company). Let users bring their own key for unlimited usage on gpt-5-chat-latest. Support Ollama for local/DGX deployments.

No OpenRouter OAuth. No Gemini. Simple, direct.

| Mode                     | Model                   | Cost             | Limit                |
| ------------------------ | ----------------------- | ---------------- | -------------------- |
| **Default** (server key) | `gpt-5-mini-2025-08-07` | Free to user     | $5/month per company |
| **BYOK** (user's key)    | `gpt-5-chat-latest`     | User pays OpenAI | Unlimited            |
| **Ollama** (local/DGX)   | User's chosen model     | Free             | Unlimited            |
| **No AI** (fallback)     | —                       | Free             | HRIS only            |

## Why This Works

- **$5/month on gpt-5-mini = ~500 typical queries** (~23/working day). Generous enough for real use.
- BYOK unlocks the premium model (gpt-5-chat-latest) with no limits.
- Ollama with DGX collaboration gives a free high-performance option for institutional users.
- HRIS works fully without any AI — advisory is the add-on.

## Scope

### In Scope

- BYOK: admin enters OpenAI API key, encrypted, stored per-company
- Budget tracking: per-company token cost accumulation, $5/month cap on default key
- Ollama configuration: custom endpoint URL (for DGX or local Ollama)
- Model selection: gpt-5-mini (default), gpt-5-chat-latest (BYOK), custom (Ollama)
- Frontend: settings page for key entry, Ollama endpoint, usage display
- Graceful degradation at every level

### Out of Scope (Future)

- Per-user keys (start with company-level)
- Multi-provider BYOK (Anthropic, Gemini — architecture supports it, UI deferred)
- Full usage analytics dashboard
- OpenRouter OAuth
- Adjustable budget caps (fixed $5 for now)

## Architecture

### Provider Resolution Chain

```
1. Company BYOK key → gpt-5-chat-latest (unlimited)
2. Company Ollama endpoint → user's chosen model (unlimited)
3. Server OpenAI key (.env) → gpt-5-mini ($5/month cap)
4. Server Ollama (auto-detected) → local model
5. No LLM → HRIS-only mode
```

### Key Storage Model

```
CompanyLLMConfig:
  company_id      FK to Company (unique with provider)
  provider        "openai" | "ollama" | "custom"
  encrypted_key   Fernet-encrypted API key (LLM_KEY_ENCRYPTION_KEY)
  model_pref      model name (nullable — defaults to gpt-5-chat-latest for OpenAI)
  base_url        custom endpoint URL (required for Ollama, nullable for OpenAI)
  status          "active" | "invalid" | "revoked"
  updated_by      user_id of admin who last changed
  created_at, updated_at
```

### Budget Tracking Model

```
CompanyLLMUsage:
  company_id      FK to Company
  month           date (first of month, e.g. 2026-04-01)
  query_count     integer
  input_tokens    integer
  output_tokens   integer
  estimated_cost  float (USD, calculated from token counts + model pricing)
  updated_at
```

Unique constraint on (company_id, month). Upsert on each query.

### Budget Enforcement

```
On each advisory request (before LLM call):
  1. Fetch CompanyLLMUsage for current month
  2. If company has BYOK key → skip budget check, use their key
  3. If using server key → check estimated_cost < $5.00
     - Under budget: proceed
     - At 80% ($4.00): proceed + include warning in response
     - At 100% ($5.00): block with friendly message

After LLM call:
  4. Count actual tokens (from OpenAI response usage field)
  5. Calculate cost: (input_tokens * $0.25/1M) + (output_tokens * $2.00/1M)
  6. Upsert CompanyLLMUsage: increment tokens and cost
```

Monthly reset: automatic — new month = new row.

### Ollama / DGX Configuration

```
Admin enters in Settings:
  - Endpoint URL: e.g. http://dgx.institution.edu:11434
  - Model name: e.g. llama3.1:70b
  - (No API key needed for Ollama)

Backend stores as CompanyLLMConfig:
  provider = "ollama"
  base_url = "http://dgx.institution.edu:11434"
  model_pref = "llama3.1:70b"
  encrypted_key = NULL (no key for Ollama)
```

Kaizen already has Ollama provider support — just needs the base_url to be configurable instead of defaulting to localhost.

### Changes by Layer

**Layer 1: Database** (new)

- `CompanyLLMConfig` DataFlow model
- `CompanyLLMUsage` DataFlow model

**Layer 2: Backend — New Endpoints**

- `POST /companies/{id}/llm-config` — Save BYOK key or Ollama config (admin only)
- `GET /companies/{id}/llm-config` — Get config with masked key (admin only)
- `DELETE /companies/{id}/llm-config` — Remove config
- `POST /companies/{id}/llm-config/validate` — Test key/endpoint
- `GET /companies/{id}/llm-usage` — Get current month usage + remaining budget

**Layer 3: Backend — Pipeline Modifications**

- Refactor `has_llm_available()` — check company config before server env
- Refactor `_resolve_provider_and_model()` — accept per-request overrides
- Create `LLMKeyContext` dataclass: api_key, provider, model, base_url, is_byok
- Thread through `_run_llm_advisory()` and all agent configs
- Apply to BOTH `/query` AND `/stream` endpoints
- After LLM call: extract token counts from response, update CompanyLLMUsage
- Before LLM call: check budget if using server key

**Layer 4: Backend — Encryption**

- `LLM_KEY_ENCRYPTION_KEY` env var (separate from salary encryption)
- No plaintext fallback

**Layer 5: Kaizen Framework** (upstream if needed)

- Investigate `BaseAgent.run()` to confirm where API key is consumed
- If needed: `get_openai_config()` accepts optional api_key + base_url
- Ollama provider: accept configurable base_url

**Layer 6: Frontend**

- Settings > AI Configuration with two clear options:
  1. "Use your own OpenAI key" — key input, validation
  2. "Connect to a local AI service" — Ollama endpoint + model
- Usage display: "X queries this month, $Y.YY of $5.00 used"
- Budget warning in advisory chat when approaching limit
- "Upgrade" prompt when budget exceeded

## Implementation Order

### Phase 0: Investigation

1. Read Kaizen `BaseAgent.run()` — where is API key consumed?
2. Can Ollama base_url be overridden per-request?
3. Decision gate: upstream PR needed or not?

### Phase 1: Pipeline Refactor (backend)

4. Refactor global state in `agents/config.py`
5. Create `LLMKeyContext` dataclass
6. Thread through advisory pipeline (both `/query` and `/stream`)
7. Verify with existing .env key (no behavior change)

### Phase 2: Storage + Budget (backend)

8. `CompanyLLMConfig` model + encryption
9. `CompanyLLMUsage` model + token counting
10. CRUD endpoints for LLM config
11. Key validation endpoint
12. Budget check + enforcement logic

### Phase 3: Ollama Support (backend)

13. Configurable Ollama endpoint (not just localhost)
14. Ollama model selection
15. Health check for Ollama endpoint

### Phase 4: Frontend

16. Settings page: BYOK + Ollama config
17. Usage display + budget indicator
18. Budget warning/exceeded states in advisory chat
19. Onboarding: show AI status on first advisory visit

### Phase 5: Polish

20. Error message normalization
21. Stale key detection (mark invalid after 401)
22. Update `.env.example` with gpt-5-mini as documented default
23. Remove OPENAI_API_KEY as a hard requirement

## Security Checklist

- [ ] `LLM_KEY_ENCRYPTION_KEY` separate from salary encryption
- [ ] No plaintext fallback in any environment
- [ ] Key never logged
- [ ] Key validated with minimal completion call before storage
- [ ] Key masked in all API responses (last 4 chars)
- [ ] Key hard-deleted on removal
- [ ] Admin-only access to config endpoints
- [ ] Key decrypted in memory per-request, cleared after use
- [ ] Error messages normalized (no OpenAI error text passthrough)
- [ ] `updated_by` audit trail on config changes
- [ ] Ollama endpoint validated (health check) before saving
- [ ] Budget tracking uses actual token counts from API response (not estimates)
