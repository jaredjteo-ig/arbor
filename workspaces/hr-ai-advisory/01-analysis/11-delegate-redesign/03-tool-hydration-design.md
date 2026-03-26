# Tool Search/Hydration Layer — Implementation Design

**Date**: 2026-03-24
**Context**: Filed as [kailash-py#76](https://github.com/terrene-foundation/kailash-py/issues/76). This is a Kaizen engine feature, but Arbor can prototype it immediately.

## The Problem

The Delegate's `ToolRegistry.get_openai_tools()` returns ALL registered tool schemas on every LLM call. With Arbor's 644+ tools, that's ~64K tokens of tool definitions — exceeding most model context budgets and drowning signal in noise.

Anthropic solved this with `defer_loading` at their API layer. But that's provider-specific. Kaizen needs the same capability at the engine layer, working with OpenAI, Anthropic, Ollama, or any provider.

## Design: ToolHydrator

A thin layer between `ToolRegistry` and the LLM call that manages which tool schemas are "active" (sent to the LLM) vs "deferred" (stored but not sent).

```
                    ToolRegistry (644 tools)
                           |
                     ToolHydrator
                    /              \
           Active Set              Deferred Set
        (~15 tools)              (~629 tools)
        - search_tools            - employees.create
        - search_kb               - payroll.calculate
        - calculators             - leave.apply
        - navigation              - ... (624 more)
        - company_context
                                  Indexed by:
                                  - name (exact match)
                                  - description (BM25)
                                  - tags/categories
```

### Core API

```python
class ToolHydrator:
    """Manages active vs deferred tool schemas for context-efficient LLM calls."""

    def __init__(self, registry: ToolRegistry, always_active: list[str] | None = None):
        self._registry = registry
        self._always_active = set(always_active or [])
        self._hydrated: set[str] = set()  # Tools activated this turn
        self._index: dict[str, list[str]] = {}  # keyword -> tool names

    def get_active_tools(self) -> list[dict]:
        """Return tool schemas for the active set only.

        Includes: always-active tools + search_tools meta-tool + hydrated tools.
        """
        active_names = self._always_active | self._hydrated | {"search_tools"}
        return [
            tool.to_openai_format()
            for name, tool in self._registry._tools.items()
            if name in active_names
        ] + [self._search_tool_schema()]

    def hydrate(self, tool_names: list[str]) -> list[dict]:
        """Activate deferred tools by name. Returns their schemas."""
        schemas = []
        for name in tool_names:
            if self._registry.has_tool(name):
                self._hydrated.add(name)
                schemas.append(self._registry._tools[name].to_openai_format())
        return schemas

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search deferred tools by description. Returns name + description pairs."""
        # BM25-style scoring over tool names and descriptions
        ...

    def reset_hydration(self) -> None:
        """Clear hydrated tools (call between user turns)."""
        self._hydrated.clear()
```

### Integration Point: Delegate Loop

Two changes to `loop.py`:

```python
# 1. Replace get_openai_tools() with get_active_tools()
async def _stream_completion(self) -> StreamResult:
    tools = self._hydrator.get_active_tools()  # was: self._tools.get_openai_tools()
    ...

# 2. Handle search_tools results by hydrating
async def _execute_tool_calls(self, tool_calls):
    for call in tool_calls:
        name = call["function"]["name"]
        args = json.loads(call["function"]["arguments"])

        if name == "search_tools":
            # Search returns tool names; hydrate them into active set
            matches = self._hydrator.search(args["query"], args.get("limit", 5))
            result = json.dumps(matches)
            # The matched tool schemas are now in get_active_tools()
            # for the next LLM round
        else:
            result = await self._tools.execute(name, args)

        self._conversation.add_tool_result(call["id"], name, result)
```

### The search_tools Meta-Tool

```python
def _search_tool_schema(self) -> dict:
    return {
        "type": "function",
        "function": {
            "name": "search_tools",
            "description": (
                "Search for available platform tools by what you want to do. "
                "Returns tool names and descriptions. After finding the right "
                "tool, you can call it directly on the next turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Describe what you want to do, e.g. "
                            "'create a new employee', 'apply for leave', "
                            "'submit CPF contributions'"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    }
```

### Search Implementation (BM25 over name+description)

```python
import re
from collections import Counter

def _build_index(self) -> None:
    """Build inverted index over tool names and descriptions."""
    for name, tool in self._registry._tools.items():
        tokens = self._tokenize(f"{name} {tool.description}")
        for token in tokens:
            self._index.setdefault(token, []).append(name)

def search(self, query: str, limit: int = 5) -> list[dict]:
    """BM25-style search over tool registry."""
    query_tokens = self._tokenize(query)
    scores: Counter = Counter()

    for token in query_tokens:
        for name in self._index.get(token, []):
            scores[name] += 1  # Simple term frequency

    results = []
    for name, score in scores.most_common(limit):
        tool = self._registry._tools[name]
        results.append({
            "name": name,
            "description": tool.description,
            "score": score,
        })
        # Auto-hydrate the top results
        self._hydrated.add(name)

    return results

@staticmethod
def _tokenize(text: str) -> list[str]:
    """Simple word tokenization with stopword removal."""
    words = re.findall(r'\w+', text.lower())
    stops = {'the', 'a', 'an', 'is', 'are', 'for', 'to', 'in', 'of', 'and', 'or', 'with'}
    return [w for w in words if w not in stops and len(w) > 2]
```

## For Arbor: Always-Active Tools

```python
ALWAYS_ACTIVE = [
    # KB and advisory
    "search_kb",
    "calculate_cpf",
    "calculate_leave",
    "calculate_salary",
    "calculate_quota_levy",
    "get_company_context",
    # Navigation
    "navigate_to",
    # Observation (non-LLM data pipeline)
    "record_observation",
    # The meta-tool itself is auto-included
]
```

Everything else (employee CRUD, payroll, leave management, attendance, claims, shifts, recruitment, inventory, appraisals, projects, documents, government filings, accounting, banking, communications) is deferred and discoverable via `search_tools`.

## Token Budget

| Approach                              | Tokens per request |
| ------------------------------------- | ------------------ |
| All 644 tools                         | ~64,000            |
| Always-active (10) + search_tools (1) | ~1,100             |
| After hydration (10 + 5 discovered)   | ~2,600             |
| **Savings**                           | **96%**            |

## Implementation Location

**Immediate (Arbor)**: Implement `ToolHydrator` in `src/hr_advisory/delegate/hydrator.py` as a prototype.

**Upstream (Kaizen)**: Once validated, move to `kaizen-agents/delegate/hydrator.py` as a standard engine feature. File: [kailash-py#76](https://github.com/terrene-foundation/kailash-py/issues/76).

## Open Questions

1. **Should hydrated tools persist across user turns or reset?** Reset is safer (each turn starts clean) but means repeated searches for multi-step operations. Keep for now, reset between conversations.

2. **Should search auto-hydrate or require explicit hydration?** Auto-hydrate (search results are immediately available as callable tools) is simpler and matches how Anthropic's tool search works.

3. **Embedding-based search vs BM25?** BM25 is simpler and has no dependencies. Embeddings are better for semantic queries ("how do I hire someone" → `employees.create`). Start with BM25, upgrade to embeddings when pgvector is available in the engine context.
