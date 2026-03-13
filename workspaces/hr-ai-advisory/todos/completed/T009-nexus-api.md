# T009 — Nexus Multi-Channel API Setup

## Status: COMPLETED

## What Was Built

Full Nexus API gateway with 8 router groups, session management, SSE streaming, and multi-channel handlers.

### API Endpoints (8 routers)

| Router     | Endpoints                                              | Purpose                      |
| ---------- | ------------------------------------------------------ | ---------------------------- |
| advisory   | POST /query, POST /stream (SSE), GET /history/{id}     | Advisory query and streaming |
| calculator | POST /cpf, /leave, /salary                             | HR calculators               |
| compliance | POST /check, GET /status/{id}, POST /gap-analysis      | Compliance checking          |
| document   | GET /templates, GET /templates/{id}, POST /generate    | Document generation          |
| profile    | GET/{id}, POST/, PUT/{id}, GET/{id}/workforce          | Company profiles             |
| kb         | GET /acts, /domains, GET /provisions/{id}, POST /query | Knowledge base               |
| auth       | POST /register, /login, /refresh, GET /me              | Authentication               |
| search     | POST /semantic, POST /fulltext                         | Search (pgvector + filters)  |

### Infrastructure

- **Platform** (`platform.py`) — Nexus with `auto_discovery=False`, CORS, rate limiting (100 req/min)
- **Session** (`session.py`) — InMemorySessionStore (dev) / RedisSessionStore (prod) with company context, conversation history, risk escalation tracking
- **SSE Streaming** — `/advisory/stream` with start/token/complete events
- **Multi-channel handlers** — 3 workflows available on API + CLI + MCP simultaneously
- **Server** (`server.py`) — Configurable entrypoint

## Verification

27 tests passing:

- Health checks (3), CORS (2), Advisory (3), Calculator (2), Compliance (1)
- Document (2), Profile (2), KB (2), Auth (2), Search (2)
- Session CRUD (4), Multi-channel handlers (2)

## Files

- `src/hr_advisory/api/platform.py`, `session.py`, `server.py`, `__init__.py`
- `src/hr_advisory/api/routers/` — 8 router files + barrel export
- `src/hr_advisory/config/settings.py` (updated with api_host, api_port, cors_origins)
- `tests/integration/test_nexus_api.py`
