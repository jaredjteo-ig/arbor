# BYOK API Keys — Authority Document

## Overview

Arbor provides a three-tier AI access model:

| Mode                        | Model                   | Cost               | Limit                                     |
| --------------------------- | ----------------------- | ------------------ | ----------------------------------------- |
| **Default** (server key)    | `gpt-5-mini-2025-08-07` | Free to user       | $5/month per company (adjustable $1-$100) |
| **BYOK** (user's key)       | `gpt-5-chat-latest`     | User pays provider | Unlimited                                 |
| **Ollama** (local/DGX)      | User's chosen model     | Free               | Unlimited                                 |
| **Per-user key** (optional) | User's choice           | User pays          | Unlimited                                 |

## Architecture

### Provider Resolution Chain

```
1. User's personal key (UserLLMConfig) → unlimited
2. Company's BYOK key (CompanyLLMConfig) → unlimited
3. Company's Ollama endpoint → unlimited
4. Server .env key → budget-capped
5. Local Ollama auto-detect → unlimited
6. No LLM → HRIS-only mode
```

### Key Files

| File                                         | Purpose                                                 |
| -------------------------------------------- | ------------------------------------------------------- |
| `src/hr_advisory/agents/llm_context.py`      | `LLMKeyContext` — per-request key/provider/model bundle |
| `src/hr_advisory/agents/config.py`           | Provider resolution, Kaizen monkey-patch for BYOK       |
| `src/hr_advisory/security/llm_encryption.py` | Dedicated Fernet encryption (`LLM_KEY_ENCRYPTION_KEY`)  |
| `src/hr_advisory/services/llm_config.py`     | Config CRUD + `build_llm_context()`                     |
| `src/hr_advisory/services/llm_budget.py`     | Budget enforcement + token pricing                      |
| `src/hr_advisory/services/llm_errors.py`     | Error normalization (never leak provider errors)        |
| `src/hr_advisory/services/llm_metrics.py`    | Structured observability logging                        |
| `src/hr_advisory/services/ollama_health.py`  | Ollama endpoint health checks                           |
| `src/hr_advisory/services/audit_log.py`      | PDPA audit events                                       |
| `src/hr_advisory/api/routers/llm_config.py`  | 8 API endpoints (company + user)                        |
| `src/hr_advisory/cli/rotate_llm_keys.py`     | Encryption key rotation CLI                             |
| `src/hr_advisory/models/company_user.py`     | CompanyLLMConfig, CompanyLLMUsage, UserLLMConfig models |

### API Endpoints

**Company-level** (admin-only, prefix `/companies/{id}`):

- `POST /llm-config` — Save BYOK key or Ollama endpoint
- `GET /llm-config` — Get config (masked key)
- `DELETE /llm-config` — Remove config
- `POST /llm-config/validate` — Test key/endpoint before saving
- `GET /llm-usage` — Current month usage + budget
- `PUT /llm-budget` — Adjust monthly budget ($1-$100)

**User-level** (self-service, prefix `/users`):

- `POST /me/llm-config` — Save personal API key
- `GET /me/llm-config` — Get personal config
- `DELETE /me/llm-config` — Remove personal config

## Security

- **Encryption**: Dedicated `LLM_KEY_ENCRYPTION_KEY` (Fernet), separate from salary encryption
- **Key masking**: API keys never returned in responses; masked as `***stored***`
- **Frozen context**: `LLMKeyContext` is `frozen=True` — immutable after construction
- **Memory cleanup**: `clear_key()` drops reference in `finally` block
- **SSRF protection**: Cloud metadata endpoints blocked (169.254.169.254, etc.)
- **NaN/Inf protection**: All numeric paths validated with `math.isfinite()`
- **Audit trail**: Every key lifecycle event logged via `log_audit_event()`
- **Key rotation**: CLI tool with decrypt-verify-reencrypt cycle

## Budget Enforcement

- Default: $5/month per company (~500 queries with gpt-5-mini)
- Check before LLM call, record after completion
- 80% warning threshold, 100% block
- Soft cap: in-flight queries complete, next query blocked
- BYOK/Ollama users bypass budget entirely
- Monthly reset: new month = new row in CompanyLLMUsage

## Kaizen Integration

Kaizen's `get_openai_config()` reads `os.getenv("OPENAI_API_KEY")` with no parameter override. A monkey-patch in `agents/config.py` uses `contextvars.ContextVar` + `copy_context().run()` to inject per-request keys safely across thread boundaries. Upstream PR: https://github.com/terrene-foundation/kailash-py/issues/12

## Frontend

Settings page at `/settings/ai` with:

- Current status (provider, model, budget bar)
- BYOK form (provider dropdown, key input, validation)
- Ollama form (endpoint URL, model name)
- Budget display and adjustment
