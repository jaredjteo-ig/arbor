---
name: platform-architecture
description: "AITE platform architecture patterns. Use when adding endpoints, modifying middleware, or understanding component connections."
---

# Platform Architecture

## Entry Point

`src/hr_advisory/api/platform.py` — `create_platform(settings)` creates the Nexus instance.

## Router Registration

```python
from hr_advisory.api.routers import auth, advisory, calculator, compliance, document, kb, profile, search, learning, admin

# In create_platform():
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(advisory.router, prefix="/advisory", tags=["advisory"])
# ... etc
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

## Critical Rules

- ALWAYS use `runtime.execute(workflow.build())` — never the reverse
- ALL protected endpoints MUST use `Depends(get_current_user)`
- ALL company-scoped endpoints MUST call `validate_company_access()`
- Admin endpoints MUST use `require_role("owner", "hr_manager")`
- `JWT_SECRET_KEY` MUST NOT be the default value in production
- NEVER use `LocalRuntime` in containers — use `AsyncLocalRuntime`
- NEVER hardcode model names — read from `.env`

## Related Documentation

- `docs/01-architecture.md` — Full system architecture
- `docs/02-api-reference.md` — Complete API reference
- `docs/03-security.md` — Security architecture

## Consult Agent

For platform architecture: `aite-platform-specialist`
