# Product Brief — Ricoh Thailand Demo

## Product

Arbor deployed as a standalone commercial product demo for Ricoh Thailand — a Japanese MNC subsidiary with 500-2,000 employees (sales, service engineers, back-office). The demo showcases Arbor's AI-powered HR advisory platform using Singapore employment law as proof of architecture, framed as the governance framework that will power Thailand. The goal is a paid proof-of-concept engagement, not a purchase order.

## Objectives

- Deploy a clean, production-grade Arbor instance independent of the Terrene Foundation instance
- Switch LLM provider from OpenAI to Google Gemini API
- Demonstrate the platform's governance architecture (EATP trust lineage, 13-step safety chain, risk tiers) in terms that resonate with Japanese corporate culture (ringi, horenso, TQM)
- Show the full HRIS + AI advisory integration using Singapore content as proof
- Frame the Thailand adaptation as Phase 2 (content swap, not platform rebuild)
- Secure a commissioned proof-of-concept: 3 Thai regulatory domains, validated by Thai legal counsel

## Tech Stack

- Backend: Kailash Core SDK + DataFlow + Nexus (Python/FastAPI)
- Frontend: Next.js 16 + React + Tailwind v4 (web), Flutter (mobile)
- Database: PostgreSQL 14+ with pgvector
- AI: Google Gemini API (switching from OpenAI), Kailash Kaizen agents
- Infrastructure: GCP (new project, asia-southeast1), Docker Compose, Caddy auto-HTTPS
- Cache: Redis

## Constraints

- Singapore HR content is acceptable for demo — this is an architecture/governance showcase
- Must switch from OpenAI to Gemini API (user requirement)
- Must deploy to a separate instance (not arbor.terrene.foundation)
- Demo company seed data should feel appropriate for the audience (not Sakura Trading)
- MULTI_JURISDICTION guardrail will reject Thai-specific questions — only ask Singapore questions live
- $5/month default LLM budget must be increased for demo company
- In-memory conversation storage means server restart clears chat history
- Friday 2026-03-28 is the CCO meeting — narrative must be ready

## Users

- **Primary audience: Ricoh Thailand CCO** — Japanese corporate decision-maker evaluating AI governance for HR compliance
- **Secondary audience: Ricoh Thailand HR team** — Thai HR professionals who would use the platform daily
- **Demo operator: Jared** — Running the live demo and presenting the narrative
- **Internal champion (post-demo): Ricoh Thailand HR manager or IT manager** — Builds the ringisho for internal approval

## Key Demo Narrative

Lead with governance, not technology. The story:

1. "AI is already in your HR department — your employees are asking ChatGPT about Thai labour law right now. Uncontrolled."
2. "We built governance for AI HR compliance. Singapore proves it works."
3. "EATP is digital ringi. The safety chain is TQM for AI."
4. "The architecture is jurisdiction-pluggable. Thailand is an adaptation, not a rebuild."
5. "Commission a focused proof-of-concept: 3 Thai regulatory domains, 4-6 weeks."

## References

- Prior analysis migrated from `workspaces/hr-ai-advisory/01-analysis/16-ricoh-demo/` (11 documents)
- CCO narrative document: `01-analysis/01-research/10-ricoh-thailand-proposal-analysis.md`
- Redeployment analysis: `01-analysis/01-research/11-redeployment-analysis.md`
