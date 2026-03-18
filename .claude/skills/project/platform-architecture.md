---
name: platform-architecture
description: "Arbor platform architecture patterns. Use when adding endpoints, modifying middleware, or understanding component connections."
---

# Platform Architecture

## Entry Point

`src/hr_advisory/api/platform.py` — `create_platform(settings)` creates the Nexus instance.

## Router Registration

```python
from hr_advisory.api.routers import (
    auth, advisory, calculator, compliance, document, kb, profile, search,
    learning, admin, payroll, leave, claims, attendance, shifts, employees,
    appraisals, projects, inventory, recruitment, reports, approval_groups,
    integrations,
)

# In create_platform():
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(advisory.router, prefix="/advisory", tags=["advisory"])
# ... core routers ...
app.include_router(appraisals.router, prefix="/appraisals", tags=["appraisals"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(recruitment.router, prefix="/recruitment", tags=["recruitment"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(approval_groups.router, prefix="/approval-groups", tags=["approval-groups"])
```

## Auth Pattern

```python
from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.tenant_isolation import validate_company_access

# Protected endpoint
@router.get("/resource")
async def get_resource(current_user: dict = Depends(get_current_user)):
    ...

# Company-scoped endpoint
@router.get("/company/{company_id}/data")
async def get_data(company_id: int, current_user: dict = Depends(get_current_user)):
    validate_company_access(current_user, requested_company_id=company_id)
    ...

# Admin endpoint
@router.post("/admin/action")
async def admin_action(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "owner", "hr_manager")
    ...
```

## Token Lifecycle

```
Register/Login → access_token + refresh_token
    |
    ├── Access token (60 min default, configurable)
    │   └── Contains: sub, email, role, company_id, jti, exp
    │
    ├── Refresh token (7 days)
    │   └── Contains: sub, type="refresh", jti, exp
    │
    └── Logout → both JTIs added to blocklist
        └── Blocklist: InMemoryBlocklist (dev) / RedisBlocklist (prod)
```

## DataFlow Usage

```python
from kailash.runtime import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder

# Query pattern
wf = WorkflowBuilder()
wf.add_node("ProvisionListNode", "find", {"filter": {"domain_id": 1}, "limit": 50})
runtime = LocalRuntime()
results, _ = runtime.execute(wf.build())
provisions = results["find"]["records"]

# Create pattern
wf = WorkflowBuilder()
wf.add_node("CompanyCreateNode", "create", {"name": "Acme", "uen": "202400099Z"})
runtime = LocalRuntime()
results, _ = runtime.execute(wf.build())
```

## Environment Variables (Key)

| Variable             | Purpose           | Default                                       |
| -------------------- | ----------------- | --------------------------------------------- |
| `JWT_SECRET_KEY`     | Token signing     | dev-only default (blocked in prod)            |
| `JWT_EXPIRY_MINUTES` | Access token TTL  | 60                                            |
| `CORS_ORIGINS`       | Allowed origins   | `http://localhost:3000,http://localhost:5173` |
| `OPENAI_API_KEY`     | OpenAI LLM access | None                                          |
| `OLLAMA_MODEL`       | Ollama model name | None                                          |
| `EMBEDDING_MODEL`    | Embedding model   | `text-embedding-3-small`                      |
| `REDIS_URL`          | Redis connection  | None (uses in-memory fallback)                |

## Multi-Channel Handlers

```python
@app.handler("advisory_query")
def advisory_query_handler(query: str, company_id: int = None):
    # Same logic as REST /advisory/query
    # Available via API, CLI, and MCP channels
    ...
```

## Frontend API Layer

The web frontend (`apps/web/`) uses two client patterns:

| Client | File | Pattern | Auth |
|--------|------|---------|------|
| `apiClient` | `services/api/client.ts` | REST (GET/POST/PUT/DELETE) | Auto 401/403 retry with token refresh |
| `createSSEStream` | `services/api/sse.ts` | SSE streaming (POST) | Auto 401 retry with token refresh |

JWT tokens stored in `localStorage` (`access_token`, `refresh_token`). Singleton refresh promise prevents concurrent refresh requests.

## Conversation Management Endpoints

| Method | Path | Purpose | Tenant Isolation |
|--------|------|---------|------------------|
| GET | `/advisory/conversations` | List user's conversations | Filtered by ownership |
| GET | `/advisory/conversations/{id}/history` | Conversation history | Ownership verified |
| DELETE | `/advisory/conversations/{id}` | Delete conversation | Ownership verified |
| PATCH | `/advisory/conversations/{id}` | Rename conversation | Ownership verified |

Non-owned conversations return 404 (prevents enumeration).

## Critical Rules

- ALWAYS use `runtime.execute(workflow.build())` — never the reverse
- ALL protected endpoints MUST use `Depends(get_current_user)`
- ALL company-scoped endpoints MUST call `validate_company_access()`
- Admin endpoints MUST use `require_role("owner", "hr_manager")`
- `JWT_SECRET_KEY` MUST NOT be the default value in production
- NEVER use `LocalRuntime` in containers — use `AsyncLocalRuntime`
- NEVER hardcode model names — read from `.env`

## Rate Limiting Middleware

In-memory sliding window rate limiter applied before auth middleware:

- Per-company and per-user keys
- Configurable via `RATE_LIMIT_WINDOW_SECONDS` and `RATE_LIMIT_MAX_REQUESTS` env vars
- Returns 429 with `Retry-After` header on breach
- Advisory and auth endpoints have stricter limits

## Related Documentation

- `docs/01-architecture.md` — Full system architecture
- `docs/02-api-reference.md` — Complete API reference (120+ endpoints)
- `docs/03-security.md` — Security architecture

## Consult Agent

For platform architecture: `arbor-platform-specialist`
