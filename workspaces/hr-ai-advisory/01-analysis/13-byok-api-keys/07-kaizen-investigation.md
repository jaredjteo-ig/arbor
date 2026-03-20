# T399: Kaizen BaseAgent API Key Investigation

## Verdict: UPSTREAM PR REQUIRED + MONKEY-PATCH FOR NOW

## Findings

### 1. BaseAgentConfig has NO api_key field

`packages/kailash-kaizen/src/kaizen/config/config.py:36-50` — BaseAgentConfig stores llm_provider, model, temperature, max_tokens. No api_key.

### 2. WorkflowGenerator does NOT pass api_key to LLMAgentNode

`packages/kailash-kaizen/src/kaizen/core/workflow_generator.py:210-219` — node_config includes provider, model, system_prompt, generation_config. No api_key.

### 3. get_openai_config() reads os.getenv() directly

`packages/kailash-kaizen/src/kaizen/config/providers.py:163-189` — `api_key = os.getenv("OPENAI_API_KEY")`. No parameter override.

### 4. ProviderConfig HAS an api_key field

`providers.py:49` — `api_key: Optional[str] = None`. The field exists but is only populated from env vars.

### 5. get_ollama_config() also reads env

`providers.py` — `base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")`. No parameter override.

## Implementation Strategy

**Monkey-patch in Arbor**: Override `kaizen.config.providers.get_openai_config` and `get_ollama_config` at module level in `agents/config.py` to accept optional api_key/base_url parameters. This is safe because:

- We control both repos (Terrene Foundation)
- The override is additive (falls back to env var if no override)
- It will be removed when the upstream PR lands

**Upstream PR to kailash-kaizen**: Add optional `api_key` and `base_url` parameters to all `get_*_config()` functions. When provided, use them instead of `os.getenv()`. Backward compatible.

## Required Upstream Changes (for PR)

1. `get_openai_config(model=None, api_key=None)` — use override if provided
2. `get_ollama_config(model=None, base_url=None)` — use override if provided
3. `get_anthropic_config(model=None, api_key=None)` — same pattern
4. `BaseAgentConfig` — add optional `api_key` and `base_url` fields
5. `WorkflowGenerator` — thread api_key to LLMAgentNode config
6. `LLMAgentNode` — read api_key from node_config if present, else use provider default
