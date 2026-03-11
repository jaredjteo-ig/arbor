---
skill: nexus-quickstart
description: Zero-config Nexus setup and basic workflow registration. Start here for all Nexus applications.
priority: CRITICAL
tags: [nexus, quickstart, zero-config, setup]
---

# Nexus Quickstart

Get started with Kailash Nexus for multi-channel deployment.

## Install

```bash
pip install kailash-nexus
```

## Quick Start

```python
from kailash_nexus import Nexus
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

# Create Nexus app
app = Nexus()

# Register a workflow handler
@app.route("/greet")
def greet(name: str = "World"):
    workflow = WorkflowBuilder()
    workflow.add_node("TextTransformNode", "greeting", {
        "template": f"Hello, {name}!",
    })
    runtime = LocalRuntime()
    results, run_id = runtime.execute(workflow.build())
    return results["greeting"]

# Start server
app.serve(port=3000)
```

## Handler Registration

```python
from kailash_nexus import Nexus

app = Nexus()

# Simple function handler
@app.route("/echo")
def echo(message: str):
    return {"echo": message}

# With method specification
@app.route("/users", methods=["POST"])
def create_user(name: str, email: str):
    # Create user logic
    return {"user": {"name": name, "email": email}}

# With workflow execution
@app.route("/process")
def process(data: str):
    workflow = WorkflowBuilder()
    workflow.add_node("JSONTransformNode", "transform", {
        "expression": "@.value",
    })
    runtime = LocalRuntime()
    results, run_id = runtime.execute(workflow.build(), {"data": data})
    return results["transform"]
```

## Middleware

```python
from kailash_nexus import Nexus

app = Nexus()

# CORS
app.add_middleware("cors", {
    "origins": ["http://localhost:3000"],
    "methods": ["GET", "POST"],
})

# Rate limiting
app.add_middleware("rate_limit", {
    "max_requests": 100,
    "window_seconds": 60,
})

# Authentication
app.add_middleware("auth", {
    "type": "jwt",
    "secret": "your-jwt-secret",
})
```

## Presets

```python
from kailash_nexus import Nexus

# Lightweight -- minimal middleware
app = Nexus(preset="lightweight")

# Standard -- CORS + rate limiting + logging
app = Nexus(preset="standard")

# Enterprise -- full middleware stack
app = Nexus(preset="enterprise")
```

## With DataFlow

```python
from kailash_nexus import Nexus
from kailash_dataflow import DataFlow, db

@db.model
class Task:
    title: str
    done: bool = False

df = DataFlow("sqlite:///tasks.db")
df.register_model(Task)

app = Nexus()
app.register_dataflow(df)
app.serve(port=3000)
# Auto-generates CRUD endpoints for Task
```

## Custom Port

```python
app = Nexus()
app.serve(port=8080)  # Default is 3000
```

## Related Skills

- **[01-core-sdk](../01-core-sdk/SKILL.md)** - Workflow creation
- **[02-dataflow](../02-dataflow/SKILL.md)** - Database integration
- **[04-kaizen](../04-kaizen/SKILL.md)** - AI agent integration

<!-- Trigger Keywords: nexus quickstart, nexus setup, nexus server, nexus API, nexus deployment -->
