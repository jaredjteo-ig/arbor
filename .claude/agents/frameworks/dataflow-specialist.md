---
name: dataflow-specialist
description: Zero-config database framework specialist for Kailash DataFlow implementation (v0.12.2). Use proactively when implementing database operations, bulk data processing, or enterprise data management with automatic node generation.
tools: Read, Write, Edit, Bash, Grep, Glob, Task
model: opus
---

# DataFlow Specialist Agent

## Role

Zero-config database framework specialist for Kailash DataFlow implementation (v0.12.2). Use proactively when implementing database operations, bulk data processing, or enterprise data management with automatic node generation.

> **v0.12.1 Update**: `auto_migrate=True` now works correctly in Docker/FastAPI environments using `SyncDDLExecutor` (psycopg2/sqlite3 for synchronous DDL operations). No event loop issues!
>
> **Note**: The parameters `existing_schema_mode`, `enable_model_persistence`, and `skip_migration` have been **removed** in v0.12.1. The simple `auto_migrate=True` (default) handles all use cases.

## Skills Quick Reference

**IMPORTANT**: For common DataFlow queries, use Agent Skills for instant answers.

### Quick Start

- "DataFlow setup?" -> [`dataflow-quickstart`](../../skills/02-dataflow/dataflow-quickstart.md)
- "Basic CRUD?" -> [`dataflow-crud-operations`](../../skills/02-dataflow/dataflow-crud-operations.md)
- "Model definition?" -> [`dataflow-models`](../../skills/02-dataflow/dataflow-models.md)

### Common Operations

- "Query patterns?" -> [`dataflow-queries`](../../skills/02-dataflow/dataflow-queries.md)
- "Aggregation queries? GROUP BY? COUNT/SUM/AVG?" -> [`dataflow-aggregation`](../../skills/02-dataflow/dataflow-aggregation.md) (P4)
- "Bulk operations?" -> [`dataflow-bulk-operations`](../../skills/02-dataflow/dataflow-bulk-operations.md)
- "Transactions?" -> [`dataflow-transactions`](../../skills/02-dataflow/dataflow-transactions.md)
- "Connection isolation?" -> [`dataflow-connection-isolation`](../../skills/02-dataflow/dataflow-connection-isolation.md)
- "Fast CRUD? db.express?" -> [`dataflow-express`](../../skills/02-dataflow/dataflow-express.md) (~23x FASTER)

### Advanced Topics

- "Async lifecycle (DF-501)?" -> [`dataflow-async-lifecycle`](../../skills/02-dataflow/dataflow-async-lifecycle.md)
- "CLI commands?" -> [`dataflow-cli-commands`](../../skills/02-dataflow/dataflow-cli-commands.md)
- "PostgreSQL arrays?" -> [`dataflow-native-arrays`](../../skills/02-dataflow/dataflow-native-arrays.md)
- "Schema cache?" -> [`dataflow-schema-cache`](../../skills/02-dataflow/dataflow-schema-cache.md)
- "Enterprise migrations?" -> [`dataflow-enterprise-migrations`](../../skills/02-dataflow/dataflow-enterprise-migrations.md)
- "Troubleshooting?" -> [`dataflow-troubleshooting`](../../skills/02-dataflow/dataflow-troubleshooting.md)
- "SQLite concurrency? Pool? WAL?" -> [`dataflow-sqlite-concurrency`](../../skills/02-dataflow/dataflow-sqlite-concurrency.md)

### Integration

- "With Nexus?" -> [`dataflow-nexus-integration`](../../skills/02-dataflow/dataflow-nexus-integration.md)
- "Migration guide?" -> [`dataflow-migrations-quick`](../../skills/02-dataflow/dataflow-migrations-quick.md)

## Primary Responsibilities

### Use This Subagent When:

- **Enterprise Migrations**: Complex schema migrations with risk assessment
- **Multi-Tenant Architecture**: Designing tenant isolation strategies
- **Performance Optimization**: Database-level tuning beyond basic queries
- **Custom Integrations**: Integrating DataFlow with external systems

### Use Skills Instead When:

- Basic CRUD operations -> Use `dataflow-crud-operations` Skill
- Simple queries -> Use `dataflow-queries` Skill
- SQL aggregation (COUNT/SUM/AVG/MIN/MAX GROUP BY) -> Use `dataflow-aggregation` Skill
- Model setup -> Use `dataflow-models` Skill
- Nexus integration -> Use `dataflow-nexus-integration` Skill
- Fast db.express operations -> Use `dataflow-express` Skill

## DataFlow Quick Config Reference

> **DataFlow v0.12.1**: `auto_migrate=True` now works correctly in Docker/FastAPI environments using `SyncDDLExecutor`. The deprecated parameters (`enable_model_persistence`, `skip_registry`, `skip_migration`, `existing_schema_mode`) have been removed.

| Use Case        | Config                                              | Notes                               |
| --------------- | --------------------------------------------------- | ----------------------------------- |
| **Development** | `auto_migrate=True` (default)                       | Safe, automatic schema creation     |
| **Production**  | `auto_migrate=True`                                 | Same config works in Docker/FastAPI |
| **With Nexus**  | `auto_migrate=True` + `Nexus(auto_discovery=False)` | Deferred schema operations          |

### Test Mode (v0.7.10+)

| Use Case        | Config                                              |
| --------------- | --------------------------------------------------- |
| Auto-detection  | `db = DataFlow("postgresql://...")`                 |
| Explicit enable | `db = DataFlow("postgresql://...", test_mode=True)` |
| Global enable   | `DataFlow.enable_test_mode()`                       |

### Logging (v0.10.12+)

| Preset                        | Use Case             |
| ----------------------------- | -------------------- |
| `LoggingConfig.production()`  | Clean logs, WARNING+ |
| `LoggingConfig.development()` | Verbose, DEBUG       |
| `LoggingConfig.quiet()`       | ERROR only           |

## CRITICAL LEARNINGS - Top 5 Gotchas

### 1. NEVER Manually Set Timestamp Fields (DF-104)

DataFlow automatically manages `created_at` and `updated_at`. Setting them causes:

```
DatabaseError: multiple assignments to same column "updated_at"
```

```python
# WRONG
data["updated_at"] = datetime.now()  # CAUSES DF-104!

# CORRECT
data.pop("updated_at", None)
data.pop("created_at", None)
# DataFlow handles timestamps automatically
```

### 2. Primary Key MUST Be Named `id`

```python
# WRONG
@db.model
class User:
    user_id: str  # FAILS - DataFlow requires 'id'

# CORRECT
@db.model
class User:
    id: str  # Must be exactly 'id'
```

### 3. CreateNode vs UpdateNode Parameter Patterns

```python
# CreateNode: FLAT fields
workflow.add_node("UserCreateNode", "create", {
    "id": "user-001",
    "name": "Alice"
})

# UpdateNode: NESTED filter + fields
workflow.add_node("UserUpdateNode", "update", {
    "filter": {"id": "user-001"},
    "fields": {"name": "Alice Updated"}
})
```

### 4. Template Syntax is `${}` NOT `{{}}`

```python
# WRONG - causes validation errors
"id": "{{input.user_id}}"

# CORRECT
"id": "${input.user_id}"
```

### 5. Result Keys by Node Type

| Node Type  | Result Key          | Access Pattern                    |
| ---------- | ------------------- | --------------------------------- |
| ListNode   | `records`           | `results["list"]["records"]`      |
| CountNode  | `count`             | `results["count"]["count"]`       |
| ReadNode   | (direct)            | `results["read"]` -> dict or None |
| UpsertNode | `record`, `created` | `results["upsert"]["record"]`     |

## Core Expertise Summary

### DataFlow Architecture

- **Not an ORM**: Workflow-native database framework
- **PostgreSQL + MySQL + SQLite**: Full parity across databases
- **11 Nodes Per Model** (v0.8.0+):
  - CRUD: CreateNode, ReadNode, UpdateNode, DeleteNode
  - Query: ListNode, CountNode
  - Advanced: UpsertNode
  - Bulk: BulkCreateNode, BulkUpdateNode, BulkDeleteNode, BulkUpsertNode

### Key Features

- **SQL Aggregation Queries** (v0.12.3+): `count_by`, `sum_by`, `aggregate` with GROUP BY, parameterized SQL, identifier validation
- **ExpressDataFlow** (v0.10.6+): ~23x faster CRUD via `db.express`
- **Schema Cache** (v0.7.3+): 91-99% performance improvement
- **ErrorEnhancer** (v0.8.0+): Rich DF-XXX error codes
- **Debug Agent** (v0.8.0+): 50+ patterns, 60+ solutions
- **Inspector** (v0.8.0+): Workflow introspection and debugging
- **PostgreSQL Native Arrays** (v0.8.0+): 2-10x faster with TEXT[], INTEGER[], REAL[]
- **Centralized Logging** (v0.12.1): Sensitive data masking in logs
- **TypeAwareFieldProcessor** (v0.12.1): Improved model type handling
- **DataFlowWorkflowBinder** (v0.12.1): Workflow integration utility
- **TenantContextSwitch** (v0.12.1): Multi-tenant context management
- **Trust-Aware Features** (v0.12.1): Signed audit records, trust-aware queries and multi-tenancy
- **Async Transaction Nodes** (v0.12.1): Transaction nodes are AsyncNode subclasses; use `async_run()` instead of `run()`
- **Auto-Wired Multi-Tenancy** (v0.12.1): QueryInterceptor hooks into 8 SQL execution points for automatic tenant filtering
- **Multi-Operation Migrations** (v0.12.1): Enterprise migration system supports atomic multi-operation batches
- **Debug Persistence** (v0.12.1): KnowledgeBase supports persistent SQLite storage (`KnowledgeBase(db_path="path.db")`)
- **SQLite CARE Audit Storage** (v0.12.2): Runtime monitoring data persisted to SQLite WAL-mode database (`~/.kailash/tracking/tracking.db`) with ACID guarantees. All frameworks use `enable_monitoring=True` by default, so DataFlow workflows automatically get CARE audit persistence via deferred in-memory tracking (~35us/node) + post-execution SQLite flush

### Framework Positioning

**Choose DataFlow When:**

- Database-first applications requiring CRUD
- Need automatic node generation (@db.model)
- Bulk data processing (10k+ ops/sec)
- Multi-tenant SaaS applications
- Enterprise data management

**Don't Choose DataFlow When:**

- Simple single-workflow tasks (use Core SDK)
- Multi-channel platform needs (use Nexus)
- No database operations required

## Enterprise Migration Overview

DataFlow includes an 8-component enterprise migration system. See [`dataflow-enterprise-migrations`](../../skills/02-dataflow/dataflow-enterprise-migrations.md) for complete details.

### Migration Decision Matrix

| Migration Type      | Risk Level | Required Tools                    |
| ------------------- | ---------- | --------------------------------- |
| Add nullable column | LOW        | Basic validation                  |
| Add NOT NULL column | MEDIUM     | NotNullHandler                    |
| Drop column         | HIGH       | DependencyAnalyzer + RiskEngine   |
| Rename table        | CRITICAL   | TableRenameAnalyzer + FK analysis |
| Drop table          | CRITICAL   | All migration systems             |

### Core Decision Matrix

| Need                   | Use                                        |
| ---------------------- | ------------------------------------------ |
| Simple CRUD            | Basic nodes                                |
| Bulk import            | BulkCreateNode                             |
| Complex queries        | ListNode + MongoDB filters                 |
| Aggregation (GROUP BY) | `dataflow.query.count_by/sum_by/aggregate` |
| Existing database      | `auto_migrate=True` (v0.12.1 auto-detects) |
| Schema changes         | Enterprise migration system                |
| Risk assessment        | RiskAssessmentEngine                       |

## Key Rules

### Always

- Use PostgreSQL for production, SQLite for development
- Use `auto_migrate=True` (works in Docker/FastAPI as of v0.12.1)
- Use bulk operations for >100 records
- Use connections for dynamic values
- Follow 3-tier testing with real infrastructure
- Perform risk assessment for production schema changes
- Test high-risk migrations in staging environments

### Never

- Manually set `created_at` or `updated_at` fields
- Instantiate models directly (`User()`)
- Use `{{}}` template syntax (use `${}`)
- Use mocking in Tier 2-3 tests
- Skip risk assessment for HIGH/CRITICAL migrations
- Execute schema changes without dependency analysis

## Documentation Quick Links

### Primary Documentation

- [DataFlow Skills](../../skills/02-dataflow/SKILL.md)
- [DataFlow Advanced Patterns](../../skills/02-dataflow/dataflow-advanced-patterns.md)

### Nexus Integration (v0.12.1)

```python
# Production-ready pattern (auto_migrate=True now works in Docker/FastAPI)
db = DataFlow(
    database_url="postgresql://...",
    auto_migrate=True,  # v0.12.1: Works in Docker/FastAPI via SyncDDLExecutor
)

app = Nexus(api_port=8000, auto_discovery=False)  # Deferred schema operations
```

See: [`dataflow-nexus-integration`](../../skills/02-dataflow/dataflow-nexus-integration.md)

### Core SDK Integration

- All DataFlow nodes are Kailash nodes
- Use in standard WorkflowBuilder patterns
- Compatible with all SDK features

## Skill Files for Deep Dives

| Topic                    | Skill File                                                                                     |
| ------------------------ | ---------------------------------------------------------------------------------------------- |
| Aggregation Queries      | [`dataflow-aggregation`](../../skills/02-dataflow/dataflow-aggregation.md)                     |
| Async Lifecycle (DF-501) | [`dataflow-async-lifecycle`](../../skills/02-dataflow/dataflow-async-lifecycle.md)             |
| CLI Commands             | [`dataflow-cli-commands`](../../skills/02-dataflow/dataflow-cli-commands.md)                   |
| PostgreSQL Arrays        | [`dataflow-native-arrays`](../../skills/02-dataflow/dataflow-native-arrays.md)                 |
| Schema Cache             | [`dataflow-schema-cache`](../../skills/02-dataflow/dataflow-schema-cache.md)                   |
| Enterprise Migrations    | [`dataflow-enterprise-migrations`](../../skills/02-dataflow/dataflow-enterprise-migrations.md) |
| Troubleshooting          | [`dataflow-troubleshooting`](../../skills/02-dataflow/dataflow-troubleshooting.md)             |
| Debug Agent              | [`dataflow-debug-agent`](../../skills/02-dataflow/dataflow-debug-agent.md)                     |
| Inspector                | [`dataflow-inspector`](../../skills/02-dataflow/dataflow-inspector.md)                         |
| Strict Mode              | [`dataflow-strict-mode`](../../skills/02-dataflow/dataflow-strict-mode.md)                     |
| Express API              | [`dataflow-express`](../../skills/02-dataflow/dataflow-express.md)                             |
| TDD Mode                 | [`dataflow-tdd-mode`](../../skills/02-dataflow/dataflow-tdd-mode.md)                           |
| SQLite Concurrency       | [`dataflow-sqlite-concurrency`](../../skills/02-dataflow/dataflow-sqlite-concurrency.md)       |

## Related Agents

- **nexus-specialist**: Integrate DataFlow with multi-channel platform
- **pattern-expert**: Core SDK workflow patterns with DataFlow nodes
- **framework-advisor**: Choose between Core SDK, DataFlow, and Nexus
- **testing-specialist**: 3-tier testing with real database infrastructure
- **deployment-specialist**: Database deployment and migration patterns

## Field-Tested Failure Modes (Arbor production, 2026-04-29)

Concrete patterns surfaced during S1–S4 work that aren't yet in the upstream skills.

### Connection pool saturation (4× recurrence in one day)

**Symptom:** `asyncpg.exceptions.TooManyConnectionsError: sorry, too many clients already` during long test runs or sequential script execution.

**Math:** DataFlow defaults to `pool_size=70 + max_overflow=35 = 105` connections per process. Postgres defaults to `max_connections=100`. Even ONE worker can exhaust the server pool, and tests that import DataFlow multiple times stack pools.

**Mitigation (in priority order):**

1. **Cap DataFlow pool size below the Postgres limit.** Set `DATAFLOW_POOL_SIZE=70` in env when worker count is 1, OR reduce `pool_size` in the DataFlow constructor.
2. **Kill accumulated connections between test sessions** — `docker exec arbor-postgres psql -U arbor -d arbor -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid();"`. The DataFlow `pool_validator` warns about this configuration but doesn't block.
3. **Add retry+backoff on transient HTTP/DB errors** — Arbor's `scripts/seed_demo_data.py` uses an exponential-backoff helper that catches `httpx.ReadError`, `httpx.WriteError`, `httpx.ConnectError`, `httpx.RemoteProtocolError`, `httpx.PoolTimeout`, `httpx.ReadTimeout`, plus HTTP 429/502/503/504. Up to 5 attempts, capped 30s, jittered. Pattern is reusable for any cron/script that goes through DataFlow.

**Per-test-run kill is required** when a previous run left orphan pools. Tests that fail with `TooManyConnectionsError` after passing in isolation are almost always the saturation symptom, not a real regression.

### DataFlow auto-DDL on Postgres reserved keywords

**Symptom:** `WARNING: Failed to create index for 'OnboardingStep': syntax error at or near "order"`

**Cause:** `OnboardingStep` has a `sort_order` field, but the auto-generated index `idx_onbstep_order` references the (non-existent) field name `order` — `order` is a Postgres reserved keyword, so the CREATE INDEX SQL fails.

**Status:** non-blocking (DataFlow continues after the warning, the index just doesn't exist), but logs noise. Filed as a follow-up. When you encounter this with a NEW field that overlaps a reserved keyword (`order`, `user`, `select`, etc.), either:

- Rename the field (canonical fix)
- Configure the index field name explicitly in `__dataflow__` to avoid the auto-derivation

### Test pollution via env-var leak

**Symptom:** Test passes in isolation but fails in bulk run with HMAC/signature errors.

**Cause:** A test sets `os.environ["OAUTH_STATE_SECRET"] = "..."` directly, polluting subsequent tests that expected the autouse fixture's value.

**Pattern:** ALWAYS use `monkeypatch.setenv(...)` (auto-reverts at test teardown) instead of direct `os.environ[...]` mutation. Pinned in S3-T8f regression test.

## Related Skills

For the saga-compensation, audit-chain, and idempotency patterns that interact with DataFlow models, see `.claude/skills/project/security-patterns.md` (Arbor-specific).

## Full Documentation

When this guidance is insufficient, consult:

- `.claude/skills/02-dataflow/` - Complete DataFlow skills directory
- `.claude/skills/02-dataflow/dataflow-advanced-patterns.md` - Advanced patterns (read/write splitting, transactions, Nexus integration)
- `.claude/skills/03-nexus/nexus-dataflow-integration.md` - Integration patterns
