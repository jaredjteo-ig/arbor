# Authority Documents

This directory contains governance and configuration documents that control how the Arbor platform operates.

## Document Hierarchy

1. **CLAUDE.md** (this directory) -- Preloaded instructions for AI agents working on this codebase. Defines absolute directives, framework preferences, and execution patterns.

2. **Project CLAUDE.md** (`/CLAUDE.md`) -- Root-level instructions auto-loaded every Claude Code session. Contains the full COC five-layer architecture, agent roster, skill index, and workspace commands.

3. **Rules** (`.claude/rules/`) -- Behavioral constraints enforced during development:
   - `communication.md` -- Plain-language communication for non-technical users
   - `agents.md` -- Agent orchestration and review gates
   - `security.md` -- No hardcoded secrets, parameterized queries, input validation
   - `git.md` -- Conventional commits, branch naming, PR requirements
   - `no-stubs.md` -- No placeholders or simulated data in production code
   - `testing.md` -- Three-tier test strategy (unit, integration, E2E)
   - `env-models.md` -- All API keys and model names from `.env`
   - `deployment.md` -- CLI SSO auth, SSL, monitoring, AsyncLocalRuntime in containers
   - `patterns.md` -- Kailash SDK execution patterns

4. **Trust Framework** -- Implemented in `src/hr_advisory/trust/`:
   - EATP trust lineage (genesis records, attestations, trust chains)
   - CARE governance (dual-plane model, expert review workflows)
   - Citation validation against the knowledge base
   - Anti-amnesia constraint re-injection

## How to Use

When making changes to the platform, consult documents in this order:

1. Check the root `CLAUDE.md` for framework-first directives
2. Check the relevant rule file for the type of change
3. Check `docs/01-architecture.md` for system design context
4. Check `docs/03-security.md` for security requirements
