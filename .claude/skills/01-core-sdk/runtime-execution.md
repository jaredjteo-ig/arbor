---
name: runtime-execution
description: "Execute workflows with LocalRuntime or AsyncLocalRuntime, with parameter overrides and configuration options. Use when asking 'execute workflow', 'runtime.execute', 'LocalRuntime', 'AsyncLocalRuntime', 'run workflow', 'execution options', 'runtime parameters', 'content-aware detection', or 'workflow execution'."
---

# Runtime Execution

Configuration and execution patterns for the Kailash Runtime.

## Usage

`/runtime-execution` -- Reference for LocalRuntime, execute(), and reading results

## The Runtime

```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

# Build a workflow
workflow = WorkflowBuilder()
workflow.add_node("LogNode", "logger", {"message": "Hello"})

# Create runtime (reuse across executions)
runtime = LocalRuntime()

# Execute workflow
results, run_id = runtime.execute(workflow.build())
# results: dict of {node_id: {output_key: value}}
# run_id: unique execution identifier (str)
```

## Execution Result

The `runtime.execute()` method returns a tuple of `(results, run_id)`:

```python
results, run_id = runtime.execute(workflow.build(), inputs)

# results -- Per-node output maps: {node_id: {output_key: value}} (dict)
# run_id  -- Unique identifier for this execution run (str)
```

## Accessing Results

```python
results, run_id = runtime.execute(workflow.build(), {"text": "hello"})

# Check the unique run ID
print(f"Run: {run_id}")

# Access output from a specific node by ID
node_output = results.get("my_transform_node")
if node_output:
    value = node_output.get("result")
    print(f"Result: {value}")

# Pattern: get or raise
output = results.get("final_node")
if output is None:
    raise KeyError("node 'final_node' not in results")

# Pattern: get string value with default
text = results.get("text_node", {}).get("text", "default")

# Iterate all node results
for node_id, outputs in results.items():
    print(f"Node '{node_id}': {len(outputs)} outputs")
    for key, val in outputs.items():
        print(f"  {key}: {val}")
```

## Execution Model (Level-Based Parallelism)

```
Workflow DAG:
  A -> B -> D
  A -> C -> D

Level 0: [A]        -- runs first (no dependencies)
Level 1: [B, C]     -- runs in parallel (both depend only on A)
Level 2: [D]        -- runs last (depends on B and C)
```

The Runtime pre-computes execution levels at `workflow.build()` time and runs nodes at the same level concurrently.

## Passing Inputs to Workflows

```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

workflow = WorkflowBuilder()
workflow.add_node("TextTransformNode", "upper", {"operation": "uppercase"})

runtime = LocalRuntime()

# Pass inputs as a dict
results, run_id = runtime.execute(workflow.build(), {
    "text": "hello world",
    "count": 10,
    "enabled": True,
    "config": {"timeout": 30},
})
```

## Async Execution

```python
from kailash.runtime import AsyncLocalRuntime
import asyncio

async def run_workflow():
    workflow = WorkflowBuilder()
    workflow.add_node("LogNode", "logger", {})

    runtime = AsyncLocalRuntime()
    results, run_id = await runtime.execute(workflow.build(), {"data": "hello"})
    return results

asyncio.run(run_workflow())
```

## Common Patterns

### Re-using Runtime for Multiple Executions

```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

runtime = LocalRuntime()

workflow = WorkflowBuilder()
workflow.add_node("LogNode", "logger", {})
built = workflow.build()

# Execute multiple times with different inputs
for i in range(10):
    results, run_id = runtime.execute(built, {"id": i})
    print(f"Run {run_id}")
```

### Error Handling

```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

workflow = WorkflowBuilder()
workflow.add_node("HTTPRequestNode", "api", {
    "url": "https://api.example.com/data",
    "method": "GET",
})

runtime = LocalRuntime()

try:
    results, run_id = runtime.execute(workflow.build())
    output = results["api"]
    print(f"Response: {output}")
except Exception as e:
    print(f"Workflow execution failed: {e}")
```

## Testing with Runtime

```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime import LocalRuntime

def test_workflow_produces_correct_output():
    workflow = WorkflowBuilder()
    workflow.add_node("TextTransformNode", "upper", {
        "operation": "uppercase",
    })

    runtime = LocalRuntime()
    results, run_id = runtime.execute(workflow.build(), {"text": "hello"})

    output = results["upper"]
    assert output.get("result") == "HELLO"
```

## Verify

```bash
pip install kailash
python -c "from kailash.runtime import LocalRuntime; print('OK')"
```

<!-- Trigger Keywords: execute workflow, runtime, LocalRuntime, AsyncLocalRuntime, run workflow, execution, workflow execution -->
