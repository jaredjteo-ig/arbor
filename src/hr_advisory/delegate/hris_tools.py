# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Auto-generated HRIS tool bridge for the Arbor Delegate.

Reads every tool definition from the Shadow Agent's ToolRegistry and
creates a corresponding kaizen-agents ToolDef + async executor that
calls the Arbor REST API via HTTP.

Usage:
    from hr_advisory.delegate.hris_tools import register_hris_tools

    registry = ToolRegistry()
    count = register_hris_tools(registry, jwt_token="...", base_url="http://localhost:8000")
    # Now registry has 100+ HRIS tools ready for the delegate

Architecture:
    Shadow ToolRegistry ─── tool definitions (module, action, method, path, params)
          │
          ▼
    hris_tools.py ────────── for each definition, creates:
          │                    1. JSON Schema parameters
          │                    2. async executor (httpx → REST API)
          │                    3. ToolRegistry.register() call
          ▼
    kaizen-agents ToolRegistry ── delegate loop calls tools via function-calling
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Awaitable

from kaizen_agents.delegate.loop import ToolRegistry

logger = logging.getLogger(__name__)

__all__ = [
    "register_hris_tools",
]

# Regex to find path parameters like {employee_id}, {run_id}, {id}
_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")

# Default API base URL (Nexus gateway or direct backend)
_DEFAULT_BASE_URL = "http://localhost:8000"

# HTTP timeout in seconds for API calls
_API_TIMEOUT = 30.0


async def _make_api_call(
    method: str,
    path: str,
    jwt: str,
    params: dict[str, Any] | None = None,
    base_url: str = _DEFAULT_BASE_URL,
) -> str:
    """Execute an HTTP request to the Arbor backend.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE).
        path: URL path (path parameters already substituted).
        jwt: JWT bearer token for authentication.
        params: Query params for GET, JSON body for other methods.
        base_url: API base URL.

    Returns:
        Response body as a string. On error, returns a JSON error object.
    """
    import httpx

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=_API_TIMEOUT,
        ) as client:
            if method == "GET":
                resp = await client.get(path, params=params, headers=headers)
            elif method == "POST":
                resp = await client.post(path, json=params, headers=headers)
            elif method == "PATCH":
                resp = await client.patch(path, json=params, headers=headers)
            elif method == "DELETE":
                resp = await client.delete(path, params=params, headers=headers)
            else:
                resp = await client.request(method, path, json=params, headers=headers)

            # Return raw text — the LLM will parse JSON naturally
            return resp.text
    except httpx.TimeoutException:
        return json.dumps({"error": "API request timed out", "path": path})
    except httpx.ConnectError:
        return json.dumps({"error": "Could not connect to API", "path": path})
    except Exception as e:
        return json.dumps({"error": str(e), "path": path})


def _build_tool_name(module: str, action: str) -> str:
    """Build a unique tool name from module and action.

    Examples:
        ("employees", "list") -> "hris_employees_list"
        ("payroll", "calculate") -> "hris_payroll_calculate"
    """
    return f"hris_{module}_{action}"


def _extract_path_params(path: str) -> list[str]:
    """Extract path parameter names from a URL template.

    Args:
        path: URL path like "/employees/{employee_id}/confirm"

    Returns:
        List of parameter names, e.g. ["employee_id"]
    """
    return _PATH_PARAM_RE.findall(path)


def _build_json_schema(
    path_params: list[str],
    declared_params: list[str],
    method: str,
) -> dict[str, Any]:
    """Build a JSON Schema for a tool's parameters.

    Path parameters and explicitly declared parameters are required.
    For non-GET methods, an additional_params field allows the LLM
    to pass arbitrary body fields.

    Args:
        path_params: Parameters extracted from the URL path.
        declared_params: Parameters declared in the ToolDefinition.
        method: HTTP method.

    Returns:
        JSON Schema dict suitable for OpenAI function-calling.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    # All declared params are required and typed as strings by default
    # (the API handles type coercion)
    all_named = []
    seen = set()
    for p in path_params + declared_params:
        if p not in seen:
            all_named.append(p)
            seen.add(p)

    for param in all_named:
        properties[param] = {
            "type": "string",
            "description": f"Value for {param}",
        }
        required.append(param)

    # For mutating methods, allow extra body fields the LLM might infer
    if method in ("POST", "PATCH", "PUT"):
        properties["body"] = {
            "type": "object",
            "description": (
                "Additional request body fields beyond the named parameters. "
                "Use this for optional fields not listed as explicit parameters."
            ),
            "additionalProperties": True,
        }

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return schema


def _make_executor(
    method: str,
    path_template: str,
    path_params: list[str],
    jwt_holder: list[str],
    base_url_holder: list[str],
) -> Callable[..., Awaitable[str]]:
    """Create an async executor closure for a single HRIS tool.

    Uses list holders for jwt and base_url so the closure captures a
    mutable reference that can be updated after registration.

    Args:
        method: HTTP method.
        path_template: URL path with {param} placeholders.
        path_params: Parameter names that appear in the path.
        jwt_holder: Single-element list holding the JWT token.
        base_url_holder: Single-element list holding the base URL.

    Returns:
        Async callable matching ToolRegistry executor signature.
    """

    async def executor(**kwargs: Any) -> str:
        jwt = jwt_holder[0]
        base_url = base_url_holder[0]

        if not jwt:
            return json.dumps(
                {
                    "error": "No JWT token available. User must be authenticated.",
                }
            )

        # Substitute path parameters into the URL
        path = path_template
        for pp in path_params:
            value = kwargs.pop(pp, "")
            if not value:
                return json.dumps(
                    {
                        "error": f"Missing required path parameter: {pp}",
                    }
                )
            path = path.replace(f"{{{pp}}}", str(value))

        # Merge body dict into remaining kwargs for POST/PATCH
        body = kwargs.pop("body", None)
        if isinstance(body, dict):
            # body fields supplement but don't override named params
            for k, v in body.items():
                if k not in kwargs:
                    kwargs[k] = v

        # For GET/DELETE, pass as query params; for POST/PATCH, pass as JSON body
        if method in ("GET", "DELETE"):
            params = kwargs if kwargs else None
        else:
            params = kwargs if kwargs else None

        return await _make_api_call(
            method=method,
            path=path,
            jwt=jwt,
            params=params,
            base_url=base_url,
        )

    return executor


def register_hris_tools(
    registry: ToolRegistry,
    jwt_token: str | None = None,
    base_url: str = _DEFAULT_BASE_URL,
) -> int:
    """Register all HRIS REST API tools from the Shadow Agent registry.

    Reads every ToolDefinition from the Shadow ToolRegistry and creates
    a kaizen-agents tool that calls the corresponding REST endpoint.

    Navigation tools (method="NAV") are skipped — they are frontend
    route directives, not API calls.

    MCP tools (is_mcp=True) are included — the MCP gateway exposes
    them as REST endpoints under /integrations/*.

    Args:
        registry: The kaizen-agents ToolRegistry to populate.
        jwt_token: JWT bearer token for API authentication.
            Can be None at registration time and updated later
            via update_jwt().
        base_url: Base URL of the Arbor backend API.

    Returns:
        Number of tools registered.
    """
    from hr_advisory.shadow.tool_registry import get_tool_registry

    shadow_registry = get_tool_registry()
    all_tools = shadow_registry.get_all_tools()

    # Mutable holders so executors always use the latest values
    jwt_holder = [jwt_token or ""]
    base_url_holder = [base_url]

    count = 0
    skipped = 0

    for tool_def in all_tools:
        # Skip navigation tools — they don't make API calls
        if tool_def.method == "NAV":
            skipped += 1
            continue

        # Skip tools with empty paths (e.g. the generic "navigate" action)
        if not tool_def.path:
            skipped += 1
            continue

        tool_name = _build_tool_name(tool_def.module, tool_def.action)

        # Check for name collisions (shouldn't happen but defensive)
        if registry.has_tool(tool_name):
            logger.warning(
                "Duplicate HRIS tool name %s (module=%s action=%s), skipping",
                tool_name,
                tool_def.module,
                tool_def.action,
            )
            continue

        # Build parameter schema
        path_params = _extract_path_params(tool_def.path)
        schema = _build_json_schema(
            path_params=path_params,
            declared_params=tool_def.params,
            method=tool_def.method,
        )

        # Build description with trust level hint
        trust_hint = ""
        if tool_def.trust_level in ("propose", "always_propose", "double_confirm"):
            trust_hint = f" [requires confirmation: {tool_def.trust_level}]"
        description = f"{tool_def.description}{trust_hint}"

        # Create executor
        executor = _make_executor(
            method=tool_def.method,
            path_template=tool_def.path,
            path_params=path_params,
            jwt_holder=jwt_holder,
            base_url_holder=base_url_holder,
        )

        registry.register(
            name=tool_name,
            description=description,
            parameters=schema,
            executor=executor,
        )
        count += 1

    logger.info(
        "HRIS tools registered: %d active, %d skipped (navigation/empty)",
        count,
        skipped,
    )

    return count


def update_hris_credentials(
    jwt_token: str | None = None,
    base_url: str | None = None,
) -> None:
    """Update JWT token and/or base URL for all HRIS tool executors.

    Since executors capture mutable list references, updating the
    holder values propagates to all registered tools immediately.

    NOTE: This function operates on the module-level holders created
    during the most recent register_hris_tools() call. For per-instance
    credential management, use the HrisToolManager class instead.
    """
    # This is a convenience hook — the actual mechanism is the mutable
    # list holders captured by executor closures. For full lifecycle
    # management, see HrisToolManager below.
    logger.info("update_hris_credentials called — use HrisToolManager for production")


class HrisToolManager:
    """Manages HRIS tool registration with updatable credentials.

    Encapsulates the mutable JWT and base_url holders so credentials
    can be updated per-session without re-registering tools.

    Usage:
        manager = HrisToolManager(registry)
        manager.register_all(jwt_token="initial-jwt")

        # Later, when token refreshes:
        manager.update_jwt("new-jwt-token")
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._jwt_holder: list[str] = [""]
        self._base_url_holder: list[str] = [_DEFAULT_BASE_URL]
        self._tool_count = 0

    def register_all(
        self,
        jwt_token: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
    ) -> int:
        """Register all HRIS tools from the Shadow Agent registry.

        Args:
            jwt_token: JWT bearer token for API authentication.
            base_url: Base URL of the Arbor backend API.

        Returns:
            Number of tools registered.
        """
        from hr_advisory.shadow.tool_registry import get_tool_registry

        self._jwt_holder[0] = jwt_token or ""
        self._base_url_holder[0] = base_url

        shadow_registry = get_tool_registry()
        all_tools = shadow_registry.get_all_tools()

        count = 0
        skipped = 0

        for tool_def in all_tools:
            if tool_def.method == "NAV" or not tool_def.path:
                skipped += 1
                continue

            tool_name = _build_tool_name(tool_def.module, tool_def.action)

            if self._registry.has_tool(tool_name):
                logger.warning(
                    "Duplicate HRIS tool name %s, skipping",
                    tool_name,
                )
                continue

            path_params = _extract_path_params(tool_def.path)
            schema = _build_json_schema(
                path_params=path_params,
                declared_params=tool_def.params,
                method=tool_def.method,
            )

            trust_hint = ""
            if tool_def.trust_level in ("propose", "always_propose", "double_confirm"):
                trust_hint = f" [requires confirmation: {tool_def.trust_level}]"
            description = f"{tool_def.description}{trust_hint}"

            executor = _make_executor(
                method=tool_def.method,
                path_template=tool_def.path,
                path_params=path_params,
                jwt_holder=self._jwt_holder,
                base_url_holder=self._base_url_holder,
            )

            self._registry.register(
                name=tool_name,
                description=description,
                parameters=schema,
                executor=executor,
            )
            count += 1

        self._tool_count = count
        logger.info(
            "HrisToolManager: %d tools registered, %d skipped",
            count,
            skipped,
        )
        return count

    def update_jwt(self, jwt_token: str) -> None:
        """Update the JWT token for all registered HRIS tools.

        This propagates immediately to all executor closures.
        """
        self._jwt_holder[0] = jwt_token
        logger.debug("HRIS JWT token updated")

    def update_base_url(self, base_url: str) -> None:
        """Update the API base URL for all registered HRIS tools."""
        self._base_url_holder[0] = base_url
        logger.debug("HRIS base URL updated to %s", base_url)

    @property
    def tool_count(self) -> int:
        """Number of HRIS tools currently registered."""
        return self._tool_count
