# Competitive Analysis: BYOK Patterns

## Value Proposition Assessment

### Why BYOK Matters for Arbor

Arbor's positioning is **free HRIS + AI advisory**. The cost challenge:

- OpenAI GPT-4o: ~$2.50/1M input tokens, ~$10/1M output tokens
- Average advisory query: ~2K input tokens, ~1K output tokens = ~$0.015/query
- Active user doing 10 queries/day = ~$4.50/month
- 100 active users = ~$450/month in LLM costs

BYOK eliminates this cost entirely for the platform operator, making the "free" promise sustainable.

### How Competitors Handle the Cost Problem

| Approach                             | Examples                      | Arbor Fit                                 |
| ------------------------------------ | ----------------------------- | ----------------------------------------- |
| **BYOK (users pay OpenAI directly)** | Cursor, TypingMind, LibreChat | Best fit — aligns with "free" positioning |
| **Subscription covers LLM costs**    | ChatGPT, Perplexity           | Contradicts "free" value prop             |
| **Freemium with LLM quota**          | Copilot (free tier)           | Possible hybrid but adds complexity       |
| **Local LLM only**                   | Open WebUI + Ollama           | Possible fallback but quality gap         |

### Unique Selling Points for Arbor's BYOK

1. **Transparency**: Users see exactly what they're paying for (their own OpenAI usage) — no hidden markups
2. **No vendor lock-in**: Users own their key, can revoke anytime, data stays in Arbor
3. **Quality guarantee**: Using GPT-4o directly (not a fine-tuned smaller model behind a paywall)
4. **Graceful degradation**: HRIS works fully without a key — only AI advisory requires one
5. **Multi-provider**: Users can choose OpenAI, Anthropic, or local Ollama

### Platform Model Evaluation

**Producers**: Arbor (provides HRIS + advisory infrastructure)
**Consumers**: SME owners/HR managers (use HRIS + advisory)
**Partners**: LLM providers (OpenAI, Anthropic — facilitate AI capability)

BYOK makes the LLM provider a true partner in the platform model rather than a cost center. Users transact directly with their chosen provider.

### AAA Framework

- **Automate**: BYOK automates the cost allocation — no billing, no subscriptions, no invoicing
- **Augment**: User decides their own cost-quality tradeoff (GPT-4o vs GPT-4o-mini vs local Ollama)
- **Amplify**: One API key unlocks the full advisory for the entire company — scales expertise access

### Network Effect Considerations

- **Accessibility**: Adding an API key is a one-time setup — low friction after initial entry
- **Engagement**: AI advisory quality directly tied to user's chosen model — they control their experience
- **Personalization**: Future: per-user model preferences, temperature settings, custom instructions
- **Connection**: Multi-provider support connects users to their preferred AI ecosystem
- **Collaboration**: Company-level key sharing option — admin sets key for all employees

## Risk Assessment

### Risk 1: Friction at Onboarding

**Impact**: High — users who don't have an OpenAI key can't use advisory
**Mitigation**:

- HRIS works fully without a key (advisory is the add-on)
- Clear guide: "Get an OpenAI key in 2 minutes" with step-by-step
- Future: trial key from server env for first N queries

### Risk 2: Key Security Liability

**Impact**: Medium — if keys are compromised, Arbor loses trust
**Mitigation**:

- Fernet encryption (proven in salary encryption)
- Clear security documentation
- Key validation on entry (verify with OpenAI API)
- Masked display (show last 4 chars only)

### Risk 3: Support Burden

**Impact**: Low — users may blame Arbor for OpenAI billing/errors
**Mitigation**:

- Clear UI messaging: "This uses your OpenAI account"
- Error translation: show human-readable messages for API errors
- Link to OpenAI's usage dashboard

### Risk 4: OpenAI ToS Ambiguity

**Impact**: Low — BYOK is industry standard, no enforcement precedent
**Mitigation**: None needed currently — monitor for policy changes
