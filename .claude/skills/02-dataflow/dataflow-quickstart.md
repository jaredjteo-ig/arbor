---
name: dataflow-quickstart
description: "Get started with Kailash DataFlow zero-config database framework. Use when asking 'DataFlow tutorial', 'DataFlow quick start', '@db.model', 'DataFlow setup', 'database framework', or 'how to use DataFlow'."
---

# DataFlow Quickstart

Get started with Kailash DataFlow in 5 minutes.

## Install

```bash
pip install kailash-dataflow
```

## Step 1: Connect to Database

```python
from kailash_dataflow import DataFlow

# SQLite (zero-config, great for development)
df = DataFlow("sqlite:///myapp.db")

# PostgreSQL
df = DataFlow("postgresql://user:password@localhost:5432/myapp")

# MySQL
df = DataFlow("mysql://user:password@localhost:3306/myapp")
```

## Step 2: Define Models

```python
from kailash_dataflow import db

@db.model
class User:
    name: str
    email: str
    age: int = 0
    active: bool = True

@db.model
class Post:
    title: str
    body: str
    author_id: int
    published: bool = False
```

## Step 3: Register Models

```python
df.register_model(User)
df.register_model(Post)
```

This generates 11 workflow nodes per model (CreateUser, ReadUser, UpdateUser, DeleteUser, ListUser, CountUser, BulkCreateUser, etc.).

## Step 4: Use in Workflows

```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

workflow = WorkflowBuilder()

# Create a user
workflow.add_node("CreateUser", "new_user", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30,
})

# List active users
workflow.add_node("ListUser", "active_users", {
    "filter": {"active": True},
    "limit": 10,
})

runtime = LocalRuntime()
results, run_id = runtime.execute(workflow.build())

print(results["new_user"])       # Created user record
print(results["active_users"])   # List of active users
```

## Filtering

```python
from kailash_dataflow import F

# Filter operators
workflow.add_node("ListUser", "filtered", {
    "filter": F.eq("active", True) & F.gte("age", 18),
    "order_by": "name",
    "limit": 50,
})
```

## Update and Delete

```python
# Update by filter
workflow.add_node("UpdateUser", "deactivate", {
    "filter": {"id": 1},
    "fields": {"active": False},
})

# Delete by filter
workflow.add_node("DeleteUser", "cleanup", {
    "filter": {"active": False},
})
```

## Bulk Operations

```python
# Bulk create
workflow.add_node("BulkCreateUser", "batch_insert", {
    "records": [
        {"name": "Bob", "email": "bob@example.com"},
        {"name": "Carol", "email": "carol@example.com"},
    ],
})
```

## Deploy with Nexus

```python
from kailash_dataflow import DataFlow, db
from kailash_nexus import Nexus

@db.model
class Product:
    name: str
    price: float

df = DataFlow("sqlite:///shop.db")
df.register_model(Product)

app = Nexus()
app.register_dataflow(df)
app.serve(port=3000)
```

## Key Rules

1. **Never set `created_at` or `updated_at`** -- auto-managed by DataFlow
2. **Create uses flat params** -- `{"name": "Alice", "email": "..."}`
3. **Update uses filter + fields** -- `{"filter": {"id": 1}, "fields": {"name": "Bob"}}`
4. **Primary key is always `id`** -- cannot customize
5. **DataFlow is NOT an ORM** -- each node = one SQL query

## Related Skills

- **[dataflow-models](dataflow-models.md)** - Model definition details
- **[01-core-sdk](../01-core-sdk/SKILL.md)** - Workflow patterns

<!-- Trigger Keywords: DataFlow quickstart, DataFlow tutorial, DataFlow setup, @db.model, database framework, get started DataFlow -->
