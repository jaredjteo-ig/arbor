# BYOK API Key Research Findings

## Problem Statement

Arbor currently loads `OPENAI_API_KEY` from `.env` at server startup. This means:

- The project cannot be open-sourced with a working AI advisory — users need to manually configure `.env`
- A single operator (whoever deploys the server) bears the LLM cost for all users
- No multi-tenant AI cost isolation

The goal: let each user provide their own OpenAI API key so Arbor can be fully self-service.

## Finding 1: OpenAI Does NOT Offer OAuth for Third-Party Apps

**OpenAI does not act as an OAuth identity provider.** There is no "Sign in with OpenAI" equivalent to "Sign in with Google." This means Option 2 (log in to OpenAI account) is not feasible.

What OpenAI does offer:

- **Apps SDK**: OAuth flows where ChatGPT is the _client_ and _your_ app is the provider (reverse direction)
- **Admin API**: Manage keys within _your own_ organization only — cannot create keys in user accounts
- **Enterprise SSO**: For logging _into_ OpenAI, not _from_ OpenAI

Community requests for "Login with OpenAI" remain unaddressed.

**Verdict: Option 2 (OpenAI login) is not possible. BYOK (Bring Your Own Key) is the only viable path.**

## Finding 2: BYOK Is the Industry Standard

Every major open-source AI app uses BYOK:

| Product          | Key Storage                | Notes                                                   |
| ---------------- | -------------------------- | ------------------------------------------------------- |
| Cursor IDE       | Server-proxied             | BYOK for standard models                                |
| TypingMind       | Client-only (localStorage) | Pure BYOK, no server storage                            |
| LibreChat        | Encrypted DB               | `OPENAI_API_KEY=user_provided` triggers per-user prompt |
| ChatGPT-Next-Web | Client-only (localStorage) | Privacy-first                                           |
| Lobe Chat        | Settings UI                | Per-user keys via settings                              |
| Open WebUI       | Server env var             | Shared instance key by default                          |
| OpenRouter       | Third-party vault          | Managed BYOK proxy (5% fee)                             |

## Finding 3: OpenAI ToS Position

OpenAI's ToS says "Customers will not buy, sell, or transfer API keys from, to, or with a third party." However:

- This targets key _trading_, not voluntary BYOK usage
- Dozens of major products operate BYOK without enforcement action
- Community consensus: BYOK is practically tolerated
- OpenAI has never provided explicit anti-BYOK guidance despite repeated community requests

## Finding 4: Current Arbor Architecture

The API key flows through a **single global path**:

```
.env → get_settings() [cached] → SpecialistConfig → BaseAgent → WorkflowGenerator → LLMAgentNode → openai.OpenAI(api_key=...)
```

Key characteristics:

- `get_settings()` is `@lru_cache(maxsize=1)` — loaded once, shared across all requests
- Agent configs are created fresh per request but read from the global settings
- No per-request context variable system exists for API keys
- Kaizen's `get_openai_config()` reads directly from `os.getenv("OPENAI_API_KEY")`

There are **3 direct OpenAI usages** outside Kaizen:

1. `kb/embeddings.py` — embedding generation (batch, not per-request)
2. `quality/llm_judge.py` — semantic quality evaluation
3. `quality/mutation_engine.py` — QA rule generation

The embedding pipeline runs during KB setup (not per user request) and should continue using the server-level key.

## Finding 5: Security Best Practices for Key Storage

Three tiers of security:

1. **Client-only** (localStorage): Key never touches server. Best privacy, worst UX (single device).
2. **Encrypted server storage**: AES-256 with KMS-managed keys. Multi-device, but server breach risk.
3. **Per-session memory only**: Key held in RAM, never persisted. Best security, worst UX (re-enter every session).

Critical requirements:

- TLS 1.2+ for all key transmission
- Never log API keys (redact from all logging)
- Fernet encryption (already used for salary data) could be reused
- Provide key rotation and deletion controls

## Finding 6: Multi-Provider Opportunity

While OpenAI is the immediate target, the BYOK architecture should support:

- Anthropic (Claude) — `ANTHROPIC_API_KEY` already in settings
- Ollama (local) — already has auto-detection
- Future: Google Gemini, Mistral, etc.

This aligns with Kaizen's existing multi-provider support.
