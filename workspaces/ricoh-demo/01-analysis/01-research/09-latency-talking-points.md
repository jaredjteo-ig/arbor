# Response Latency — Talking Points During Demo

When the first advisory query takes 5-8 seconds to begin streaming, use these talking points to fill the pause and turn the wait into a feature explanation.

## As tokens begin streaming:

"Watch what's happening here. The system isn't just querying a language model — it's running a 13-step pipeline:

1. First it validates your question is about HR — blocking off-topic queries
2. Then it checks for prompt injection attempts
3. It searches the structured knowledge base for relevant legal provisions
4. It retrieves your company profile for context
5. The AI synthesizes a response grounded in what it found
6. Citations are validated against the actual knowledge base
7. A risk tier is assigned — green for factual, amber for guidance, red for high-stakes
8. Finally, every response gets a trust lineage record — an audit trail you can verify

That's why the first response takes a few seconds. It's not slow — it's thorough."

## If the response is faster than expected:

"The system caches knowledge base lookups and maintains conversation context, so follow-up questions in the same conversation are significantly faster."

## Pre-warming protocol:

10 minutes before demo: Open the advisory chat and ask a simple question like "What is the minimum annual leave in Singapore?" This warms:

- The Gemini API connection pool
- The KB embedding search index
- The conversation memory store
