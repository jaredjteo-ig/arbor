---
name: dataflow-models
description: "Define DataFlow models with @db.model decorator. Use when creating DataFlow models, defining database schemas, model setup, @db.model, table definitions, or field types."
---

# DataFlow Model Definition

Define database models using the `@db.model` decorator. Each model generates 11 workflow node types.

## Quick Start

```python
from kailash_dataflow import db

@db.model
class User:
    name: str
    email: str
    age: int = 0
    active: bool = True
```

This generates: `CreateUser`, `ReadUser`, `UpdateUser`, `DeleteUser`, `ListUser`, `CountUser`, `BulkCreateUser`, `BulkUpdateUser`, `BulkDeleteUser`, `UpsertUser`, `AggregateUser`.

## Field Types

```python
from kailash_dataflow import db

@db.model
class Product:
    # String fields
    name: str                    # Required text field
    description: str = ""       # Optional with default

    # Numeric fields
    price: float                # Required float
    quantity: int = 0           # Integer with default

    # Boolean
    active: bool = True

    # Timestamps (auto-managed)
    # created_at and updated_at are automatically added
```

### Available Field Types

| Python Type | SQL Type         | Notes                      |
| ----------- | ---------------- | -------------------------- |
| `str`       | TEXT / VARCHAR    | String data                |
| `int`       | INTEGER / BIGINT | Whole numbers              |
| `float`     | REAL / DOUBLE    | Floating point             |
| `bool`      | BOOLEAN          | True/False                 |

## Model Conventions

### Auto-Managed Fields

Every model automatically gets:

- `id` -- Primary key (auto-increment integer)
- `created_at` -- Set on insert (never manually set)
- `updated_at` -- Updated on every modification (never manually set)

```python
# WRONG: Never set timestamps manually
workflow.add_node("CreateUser", "create", {
    "name": "Alice",
    "created_at": "2024-01-01",  # BAD -- auto-managed
})

# CORRECT: Let DataFlow manage timestamps
workflow.add_node("CreateUser", "create", {
    "name": "Alice",
    "email": "alice@example.com",
})
```

### Create Uses Flat Parameters

```python
# CreateUser takes field values directly
workflow.add_node("CreateUser", "create", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30,
})
```

### Update Uses Filter + Fields

```python
# UpdateUser requires filter and fields
workflow.add_node("UpdateUser", "update", {
    "filter": {"id": 1},
    "fields": {"name": "Bob", "age": 31},
})
```

### Primary Key Must Be Named `id`

DataFlow models always use `id` as the primary key name. Custom primary key names are not supported.

### Soft Delete

When enabled, delete marks records with `deleted_at` instead of removing them. Note: soft delete only affects DELETE operations, NOT queries -- you must filter deleted records yourself.

```python
@db.model(soft_delete=True)
class AuditRecord:
    action: str
    details: str
```

## Filtering with F

```python
from kailash_dataflow import F

# Build filter conditions
workflow.add_node("ListUser", "active_users", {
    "filter": F.eq("active", True) & F.gte("age", 18),
    "order_by": "name",
    "limit": 100,
})

# Available filter operators
F.eq("field", value)      # Equal
F.neq("field", value)     # Not equal
F.gt("field", value)      # Greater than
F.gte("field", value)     # Greater than or equal
F.lt("field", value)      # Less than
F.lte("field", value)     # Less than or equal
F.like("field", "%pattern%")  # LIKE pattern
F.in_("field", [1, 2, 3])    # IN list

# Combine with & (AND) and | (OR)
filter = F.eq("active", True) & (F.gt("age", 18) | F.eq("role", "admin"))
```

## Multi-Tenancy

```python
from kailash_dataflow import db, with_tenant

@db.model(multi_tenant=True)
class Document:
    title: str
    content: str

# Use with tenant context
with with_tenant("tenant_123"):
    # All queries automatically filtered by tenant
    workflow.add_node("ListDocument", "docs", {})
```

## Complete Example

```python
from kailash_dataflow import DataFlow, db, F
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

# Define models
@db.model
class Task:
    title: str
    description: str = ""
    status: str = "pending"
    priority: int = 0

# Connect and register
df = DataFlow("sqlite:///tasks.db")
df.register_model(Task)

# Build workflow
workflow = WorkflowBuilder()
workflow.add_node("CreateTask", "new_task", {
    "title": "Build API",
    "description": "Implement REST endpoints",
    "priority": 1,
})
workflow.add_node("ListTask", "pending_tasks", {
    "filter": F.eq("status", "pending"),
    "order_by": "-priority",
    "limit": 10,
})

runtime = LocalRuntime()
results, run_id = runtime.execute(workflow.build())
print(results["pending_tasks"])
```

<!-- Trigger Keywords: DataFlow model, @db.model, field types, model definition, database schema, table definition, field type -->
