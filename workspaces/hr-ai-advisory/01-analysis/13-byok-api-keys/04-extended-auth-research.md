# Extended Authentication Research: Beyond BYOK

## The Core Problem

Most Arbor users will have a ChatGPT account but zero idea what an API key is. Asking them to create an OpenAI Platform account, add a payment method, generate a key, and paste it into Arbor is a massive onboarding stumble. We need zero-friction AI access.

## Key Discovery 1: "Sign in with ChatGPT" Is Coming (But Not Here Yet)

OpenAI is building "Sign in with ChatGPT" — a proper OAuth identity provider for third-party apps. Early previews surfaced through the Codex CLI in May 2025 (Plus users got $5 API credits, Pro got $50 for signing in). TechCrunch reported on it. But as of March 2026, it is NOT publicly available for third-party apps to integrate.

**Watch this closely.** When it launches, it will be the natural choice — everyone has a ChatGPT account.

## Key Discovery 2: ChatGPT Subscription != API Access

ChatGPT Plus ($20/mo) and the OpenAI API are completely separate billing systems. A Plus subscription does NOT include API access. There is NO way to use ChatGPT subscription credits via the API. This kills the "just log into your ChatGPT account" idea for official API calls.

The ONLY exception: OpenAI Codex (included in Plus/Pro) can be accessed via OAuth in third-party tools, but this is limited to code generation use cases and is fragile/undocumented for general use.

## Key Discovery 3: OpenRouter Has Production-Ready OAuth

OpenRouter provides exactly what we need — a proper OAuth PKCE flow where users:

1. Click a button in Arbor ("Connect AI")
2. Get redirected to OpenRouter
3. Sign in (or create a free account)
4. Set a credit limit (even $0.10)
5. Return to Arbor with a provisioned API key

Users pay their own usage. 29 free models available (no payment needed). Paid models (GPT-4o, Claude, Gemini Pro) available for users who add payment.

This is the ONLY production-ready "user-authenticated AI access" OAuth flow available today.

## Key Discovery 4: Google Gemini Free Tier Is Extremely Generous

Google Gemini offers free API access that requires NO credit card:

- All models available (including Gemini 2.0 Flash, Pro)
- 100-1,000 requests per day (free tier)
- 250K tokens per minute
- Only requires a Google account (which almost everyone has)
- API key generation at ai.google.dev takes 30 seconds

This could serve as the **default zero-friction option** — almost everyone has a Google account, and getting a Gemini API key is trivially simple compared to OpenAI.

## Key Discovery 5: Reverse Proxy Solutions Exist But Are Not Production-Viable

Several projects let users authenticate with their ChatGPT account and proxy API calls:

- **openai-oauth** (EvanZhouDev) — localhost proxy using Codex OAuth tokens
- **OpenClaw** — open-source AI router with Codex OAuth support
- **gpt4free** — aggregates free model access

These are fine for developer tools. They are NOT suitable for a production HRIS serving Singapore SMEs because:

- Fragile (depends on undocumented endpoints)
- Against OpenAI ToS for most use cases
- No SLA, could break at any time
- Security risk (proxying through third-party code)

## Key Discovery 6: Anthropic Banned Third-Party Subscription OAuth

In February 2026, Anthropic explicitly banned third-party tools from using Claude subscription OAuth. This is a cautionary tale — OpenAI could do the same for Codex OAuth at any time. Don't build on undocumented OAuth flows.

## Key Discovery 7: Other Free Tiers

| Provider              | Free Tier               | Credit Card? | Quality        |
| --------------------- | ----------------------- | ------------ | -------------- |
| Google Gemini         | 100-1K RPD, all models  | No           | Excellent      |
| Groq                  | Generous, Llama/Mixtral | No           | Good (fast)    |
| Mistral               | 2 RPM, 1B tokens/mo     | No           | Good           |
| DeepSeek              | 5M free tokens          | No           | Good           |
| Cerebras              | Free API key            | No           | Fast inference |
| SambaNova             | Free tier               | No           | Good           |
| Cloudflare Workers AI | 10K neurons/day         | No           | Varies         |

---

## Revised Recommendation: Three-Tier Strategy

### Tier 1: Zero Friction (Default) — Google Gemini Free

**For**: Every user, immediately on signup, no setup required.

How it works:

- Arbor ships with a **server-level Gemini API key** (free tier, no cost to operator)
- Or: guide users through 30-second Gemini key generation (ai.google.dev, just needs Google account)
- Advisory works immediately with Gemini 2.0 Flash (free, good quality)
- Rate limits (100-1K RPD) are sufficient for typical SME advisory usage

Why this is better than requiring an OpenAI key:

- Zero cost to user
- Almost everyone has a Google account
- No credit card required
- Key generation takes 30 seconds vs 5+ minutes for OpenAI

### Tier 2: Better Models — OpenRouter OAuth

**For**: Users who want GPT-4o, Claude, or other premium models.

How it works:

- User clicks "Upgrade AI" or "Connect to OpenRouter" in settings
- OAuth PKCE redirect to OpenRouter
- User signs in, sets credit limit
- Returns with API key
- Arbor uses OpenRouter's OpenAI-compatible API
- User pays per-token for premium models, free models also available

Why OpenRouter:

- Proper OAuth flow (no raw key pasting)
- User controls their spending
- 29 free models included
- Access to GPT-4o, Claude, Gemini Pro, etc.
- OpenAI-compatible API (minimal code changes)

### Tier 3: Power Users — BYOK

**For**: Technical users, enterprises, users with existing API keys.

How it works:

- Paste API key in Settings (OpenAI, Anthropic, or any OpenAI-compatible endpoint)
- Standard BYOK pattern as originally planned
- Encrypted storage, validation, masking

### Tier 0 (Fallback): No AI — HRIS Only

If none of the above are configured, the HRIS works fully. Advisory shows a setup prompt.

---

## Impact on Architecture

The three-tier approach changes the architecture:

### Multi-Provider Support Required

- Current: OpenAI-only in the pipeline
- Needed: OpenAI, Gemini, OpenRouter (OpenAI-compatible), Ollama
- Kaizen already supports multiple providers — this is mainly a config issue

### Key Resolution Chain (Updated)

```
1. Company BYOK key (Tier 3) — if admin has set one
2. Company OpenRouter key (Tier 2) — if user has connected
3. Server Gemini key (Tier 1) — default, free
4. Server .env key (operator override) — for demo/testing
5. Ollama (local) — self-hosted option
6. No LLM — HRIS-only mode
```

### New Frontend Flows

- **Onboarding**: "Your AI advisor is ready" (Gemini free tier works immediately)
- **Settings > AI**: Three options clearly explained in plain language
- **OpenRouter OAuth**: Redirect flow with callback handling

### What This Means for Open-Sourcing

- Ship with Gemini as default — works out of the box with a free Google API key
- OpenRouter OAuth gives a one-click upgrade path
- BYOK for power users
- No `.env` OpenAI key required for basic functionality
