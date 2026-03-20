# Cost Analysis: Advisory Pipeline with Real Models

## Models

| Context              | Model                   | Input/1M | Output/1M |
| -------------------- | ----------------------- | -------- | --------- |
| Default (server key) | `gpt-5-mini-2025-08-07` | $0.25    | $2.00     |
| BYOK users           | `gpt-5-chat-latest`     | $1.25    | $10.00    |
| Ollama (DGX)         | Local model             | Free     | Free      |

## Per-Query Token Breakdown

A single advisory query triggers 4-6 LLM calls:

1. **QueryAnalyzer**: ~1.8K-3.5K tokens (system prompt ~1.5K + query + context)
2. **Specialist(s)**: ~10K-15K tokens each (system prompt 7-9.5K + KB provisions + context)
3. **ComplianceAgent** (optional, ~30%): ~3K-8K tokens
4. **ResponseSynthesizer**: ~7K-15K tokens (system prompt 3.9K + all specialist outputs)

### Typical Scenarios

| Scenario                         | Input Tokens | Output Tokens | Total |
| -------------------------------- | ------------ | ------------- | ----- |
| Simple (1 domain, no compliance) | ~18K         | ~1.5K         | 19.5K |
| Typical (1 domain + compliance)  | ~25K         | ~2K           | 27K   |
| Multi-domain                     | ~35K         | ~3K           | 38K   |
| Heavy (multi-domain + history)   | ~45K         | ~4K           | 49K   |

## $5/Month Budget on gpt-5-mini (Default)

| Scenario     | Cost/Query | Queries for $5 | Per Working Day (22 days) |
| ------------ | ---------- | -------------- | ------------------------- |
| Simple       | $0.007     | ~700           | ~32/day                   |
| Typical      | $0.010     | ~500           | ~23/day                   |
| Multi-domain | $0.015     | ~330           | ~15/day                   |
| Heavy        | $0.019     | ~260           | ~12/day                   |

**Verdict: $5/month on gpt-5-mini is very generous.** Even heavy users get 12+ queries/day.

## BYOK on gpt-5-chat-latest

| Scenario | Cost/Query | Queries for $5 | Per Working Day |
| -------- | ---------- | -------------- | --------------- |
| Simple   | $0.033     | ~150           | ~7/day          |
| Typical  | $0.051     | ~100           | ~5/day          |
| Heavy    | $0.096     | ~50            | ~2/day          |

BYOK users get the premium model. Still reasonable at ~5 queries/day for typical use.

## Ollama / DGX (Free)

No token cost. Throughput depends on the model and hardware:

- DGX with Llama 3.1 70B: fast inference, comparable quality to gpt-5-mini for factual tasks
- Local Ollama: varies by model and GPU

## Budget Tracking Implementation

Track per-company spending:

- Count input + output tokens per request
- Multiply by model pricing
- Accumulate daily/monthly
- Alert at 80% of $5 cap
- Block at 100% with friendly message: "You've used your free AI allowance this month. Add your own API key for unlimited access, or wait until next month."

Monthly reset: 1st of each month, UTC.

## Cost Optimization Opportunities (Future)

1. **Cached input pricing**: gpt-5-mini offers 90% discount on cached inputs ($0.025/1M). System prompts are identical across requests — if OpenAI caches them, cost drops ~30%.
2. **Compress system prompts**: 7-9.5K tokens per specialist is heavy. Could reduce 30-40%.
3. **Reduce KB provisions**: top_k=10 → top_k=5 saves ~1K tokens per specialist.
4. **Skip compliance gate for simple queries**: saves 3-8K tokens on ~70% of queries.
