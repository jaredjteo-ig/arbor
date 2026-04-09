# Kailash SDK — Upstream Issues from Arbor

Bugs and limitations discovered while building [Arbor](https://github.com/terrene-foundation/arbor) (AI-powered HRIS for Singapore SMEs). These affect any production application built on the Kailash stack.

**Project**: Arbor HR Advisory Platform
**Reporter**: Jared Teo
**Date**: 2026-04-09

---

## P0 — Critical

### 1. Kaizen: Provider config functions have no API key override parameter

**Package**: `kailash-kaizen`
**Functions**: `get_openai_config()`, `get_ollama_config()`, `get_anthropic_config()`
**Filed**: https://github.com/terrene-foundation/kailash-py/issues/12

**Problem**

All three provider config functions read API keys directly from `os.getenv()` with no parameter to override per-request. This completely blocks multi-tenant BYOK (Bring Your Own Key) support — any application where different users or companies bring their own LLM keys cannot use Kaizen natively.

**Reproduction**

```python
from kaizen.config.providers import get_openai_config

# No way to pass a per-request API key
config = get_openai_config()  # Always reads os.getenv("OPENAI_API_KEY")
```

**Expected**

```python
config = get_openai_config(api_key="user-specific-key", base_url="custom-endpoint")
```

**Arbor workaround**

Monkey-patch at module level using `contextvars.ContextVar` to inject per-request keys safely across async task boundaries. See `src/hr_advisory/agents/config.py:47-160`.

**Suggested fix**

1. Add optional `api_key` and `base_url` parameters to `get_openai_config()`, `get_ollama_config()`, `get_anthropic_config()`
2. Update `BaseAgentConfig` to include optional `api_key` and `base_url` fields
3. Thread these parameters through `WorkflowGenerator` → `LLMAgentNode`
4. Fall back to `os.getenv()` when parameters are not provided (backwards-compatible)

---

## P1 — High

### 2. DataFlow: `express_sync.list()` caches results by default with no invalidation after writes

**Package**: `kailash-dataflow`
**Function**: `express_sync.list()`

**Problem**

DataFlow's `express_sync.list()` caches query results by default. After writing to the database (create, update, delete), subsequent reads return stale cached data. There is no automatic cache invalidation after write operations.

**Reproduction**

```python
# Write a record
express_sync.create("OnboardingStep", {"step_id": "s1", "status": "completed"})

# Immediately read — returns stale cached data showing status as "pending"
steps = express_sync.list("OnboardingStep", filters={"user_id": user_id})
```

**Impact in Arbor**

This broke onboarding progress tracking — steps showed "pending" after being marked "completed". The fix required adding `enable_cache=False` to every critical read path: **147 occurrences across 31 files**, including routers, services, KB pipeline, agents, and tests.

**Expected**

Either:

- Write operations automatically invalidate the cache for the affected model
- Cache is off by default for transactional reads
- A clear `invalidate_cache()` API exists

**Suggested fix**

Option A (preferred): Invalidate cache entries for a model after any create/update/delete on that model.
Option B: Change default to `enable_cache=False` and let users opt in for read-heavy queries.
Option C: Provide `express_sync.invalidate("ModelName")` for manual cache busting after writes.

---

## P2 — Medium

### 3. Nexus: No workflow metadata parameter on registration

**Package**: `kailash-nexus`
**Function**: `app.register()`

**Problem**

Nexus workflow registration has no native `metadata` parameter. There is no way to attach structured metadata (version, author, tags, description) to a registered workflow.

**Reproduction**

```python
app = Nexus()
app.register(my_workflow)  # No metadata parameter available
```

**Expected**

```python
app.register(my_workflow, metadata={
    "version": "1.2.0",
    "author": "advisory-team",
    "tags": ["hr", "advisory"],
    "description": "Employment law advisory workflow"
})
```

**Arbor workaround**

Store metadata in a separate dictionary outside the workflow registration.

**Suggested fix**

Add an optional `metadata: dict` parameter to `Nexus.register()`, stored alongside the workflow definition and queryable via the API.

---

### 4. SDK: Transitive dependencies not fully declared

**Package**: `kailash`, `kailash-dataflow`, `kailash-nexus`, `kailash-kaizen`

**Problem**

Several transitive dependencies are not declared in the SDK packages' `pyproject.toml` files. Docker builds from clean environments fail with `ModuleNotFoundError` until these are manually pinned.

**Missing dependencies discovered during Arbor Docker builds**:

- `psutil` (required by Kailash runtime)
- `requests`
- `pandas`
- `numpy`
- `jinja2`
- `aiohttp`
- `websockets`

**Arbor commits**: `33d00b6`, `d9c1568`, `43de1e4`

**Suggested fix**

Audit all packages' `pyproject.toml` dependency declarations. Run a clean `pip install` in an empty venv and verify all imports resolve without error.

---

## P3 — Low

### 5. SDK: `DATABASE_URL` validation rejects special characters in passwords

**Package**: `kailash` (core)

**Problem**

The SDK's database URL validation rejects passwords containing special characters (`@`, `#`, `%`, etc.) that are common in auto-generated database passwords. The password must be URL-encoded before passing to the SDK, but this is not documented.

**Reproduction**

```python
# Fails SDK validation
DATABASE_URL="postgresql://user:p@ss#word@localhost:5432/mydb"

# Works after URL-encoding the password
DATABASE_URL="postgresql://user:p%40ss%23word@localhost:5432/mydb"
```

**Arbor commit**: `d190def`

**Suggested fix**

Either:

- Parse the URL and handle encoding internally before validation
- Document the URL-encoding requirement clearly in DataFlow/connection setup docs

---

### 6. DataFlow: `auto_migrate` event loop conflict in async environments (Resolved)

**Package**: `kailash-dataflow` (versions < 0.10.15)
**Status**: **Fixed in v0.10.15** — `SyncDDLExecutor` bypasses the event loop conflict

**Problem (historical)**

`auto_migrate=True` caused event loop boundary issues in Docker/FastAPI environments. Table creation DDL attempted async operations on a synchronous path, causing deadlocks.

**No action needed** — included for completeness in case of regressions.

---

## Summary

| #   | Issue                              | Package  | Priority | Status                                                                                         |
| --- | ---------------------------------- | -------- | -------- | ---------------------------------------------------------------------------------------------- |
| 1   | API key override missing           | kaizen   | P0       | Filed ([#12](https://github.com/terrene-foundation/kailash-py/issues/12)), workaround in place |
| 2   | Cache not invalidated after writes | dataflow | P1       | Workaround (147 `enable_cache=False`)                                                          |
| 3   | No workflow metadata param         | nexus    | P2       | Workaround (external dict)                                                                     |
| 4   | Transitive deps undeclared         | all      | P2       | Workaround (manual Dockerfile pins)                                                            |
| 5   | DB URL special char rejection      | core     | P3       | Workaround (URL-encode password)                                                               |
| 6   | auto_migrate event loop conflict   | dataflow | —        | Resolved in v0.10.15                                                                           |
