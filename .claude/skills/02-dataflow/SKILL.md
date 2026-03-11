---
name: dataflow
description: "Kailash DataFlow - zero-config database framework with automatic model-to-node generation. Use when asking about 'database operations', 'DataFlow', 'database models', 'CRUD operations', 'bulk operations', 'database queries', 'database migrations', 'multi-tenancy', 'multi-instance', 'database transactions', 'PostgreSQL', 'MySQL', 'SQLite', 'MongoDB', 'pgvector', 'vector search', 'document database', 'RAG', 'semantic search', 'existing database', 'database performance', 'database deployment', 'database testing', or 'TDD with databases'. DataFlow is NOT an ORM - it generates 11 workflow nodes per SQL model, 8 nodes for MongoDB, and 3 nodes for vector operations."
---

# Kailash DataFlow

Zero-config database framework that generates workflow nodes from model definitions.

## Overview

DataFlow is NOT an ORM. It generates **11 workflow nodes per model** that handle CRUD, bulk, count, and upsert operations through the workflow engine.

## Quick Start

```python
from kailash_dataflow import DataFlow, db

# Connect to database
df = DataFlow("sqlite:///myapp.db")

# Define a model
@db.model
class User:
    name: str
    email: str
    age: int = 0

# Register model nodes
df.register_model(User)

# Use in workflow
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

workflow = WorkflowBuilder()
workflow.add_node("CreateUser", "create", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30,
})
runtime = LocalRuntime()
results, run_id = runtime.execute(workflow.build())
```

## Reference Documentation

### Core Skills

- **[dataflow-quickstart](dataflow-quickstart.md)** - Setup, connection, model registration
- **[dataflow-models](dataflow-models.md)** - Model definition with `@db.model`

## Key Concepts

### Model-to-Node Generation

Each model generates 11 node types:

| Node Type              | Operation        | Example for `User`        |
| ---------------------- | ---------------- | ------------------------- |
| `Create{Model}`        | Insert one       | `CreateUser`              |
| `Read{Model}`          | Read one by ID   | `ReadUser`                |
| `Update{Model}`        | Update by filter | `UpdateUser`              |
| `Delete{Model}`        | Delete by filter | `DeleteUser`              |
| `List{Model}`          | Query with filter| `ListUser`                |
| `Count{Model}`         | Count records    | `CountUser`               |
| `BulkCreate{Model}`    | Insert many      | `BulkCreateUser`          |
| `BulkUpdate{Model}`    | Update many      | `BulkUpdateUser`          |
| `BulkDelete{Model}`    | Delete many      | `BulkDeleteUser`          |
| `Upsert{Model}`        | Insert or update | `UpsertUser`              |
| `Aggregate{Model}`     | Aggregate query  | `AggregateUser`           |

### DataFlow Is NOT an ORM

- No lazy loading, no relationships, no unit of work
- Each node = one SQL query (explicit, predictable)
- Models define schema, not object behavior
- Generated nodes wrap parameterized SQL

### Deployment Pattern

```python
from kailash_dataflow import DataFlow, db
from kailash_nexus import Nexus

@db.model
class Product:
    name: str
    price: float
    category: str

df = DataFlow("postgresql://localhost/shop")
df.register_model(Product)

# Deploy with Nexus
app = Nexus()
app.register_dataflow(df)
app.serve(port=3000)
```

## Install

```bash
pip install kailash-dataflow
```

## Related Skills

- **[01-core-sdk](../01-core-sdk/SKILL.md)** - Core workflow patterns
- **[03-nexus](../03-nexus/SKILL.md)** - API deployment
- **[04-kaizen](../04-kaizen/SKILL.md)** - AI agents

## Support

For DataFlow help, invoke:

- `dataflow-specialist` - Model design, queries, optimization
- `pattern-expert` - Workflow patterns with DataFlow
