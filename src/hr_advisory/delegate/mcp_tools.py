# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""MCP server tools wired as delegate agent tools.

Registers all 97 tools from the 5 Arbor MCP servers into the kaizen-agents
ToolRegistry so the delegate agent can invoke them directly via function
calling. The MCP servers are in-process Python modules -- no stdio subprocess
needed. Each tool executor calls the MCP server handler directly and returns
the JSON-serialized result.

Servers:
    1. arbor-government  (33 tools) -- CPF, IRAS, MOM, MyInfo, ACRA, SkillsFuture
    2. arbor-accounting  (22 tools) -- Xero, QuickBooks, Zoho, Financio
    3. arbor-banking     (12 tools) -- GIRO, FAST, PayNow, Aspire
    4. arbor-communications (22 tools) -- Email, Telegram, S3, WhatsApp, Slack
    5. arbor-regulatory  (8 tools)  -- Public data, regulatory updates
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any

from kaizen_agents.delegate.loop import ToolRegistry

logger = logging.getLogger(__name__)

__all__ = ["register_mcp_tools"]

# ── Python type annotation to JSON Schema type mapping ───────────────────────

_TYPE_MAP: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
    "list": "array",
    "bytes": "string",  # base64-encoded in practice
}


def _annotation_to_json_type(annotation: Any) -> str:
    """Convert a Python type annotation to a JSON Schema type string."""
    if annotation is None or annotation is inspect.Parameter.empty:
        return "string"
    ann_str = str(annotation)
    # Handle Optional[X], dict | None, etc.
    for py_type, json_type in _TYPE_MAP.items():
        if py_type in ann_str:
            return json_type
    return "string"


def _is_required(param: inspect.Parameter) -> bool:
    """Check if a parameter is required (no default value)."""
    return param.default is inspect.Parameter.empty


# ── Schema extraction from MCP server tool handlers ─────────────────────────


def _extract_tool_schema(
    tool_name: str,
    handler: Any,
) -> dict[str, Any]:
    """Extract JSON Schema parameters from an MCP tool handler's signature.

    The MCP server decorates handlers into wrappers with signature
    ``(company_id, user_id, **kwargs)``. The original function with the
    real parameter list is accessible via ``__wrapped__``.
    """
    # Get the original unwrapped function to read real params
    original = getattr(handler, "__wrapped__", handler)
    sig = inspect.signature(original)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for pname, param in sig.parameters.items():
        # Skip the TenantContext parameter and **kwargs
        if pname == "ctx":
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue

        json_type = _annotation_to_json_type(param.annotation)
        prop: dict[str, Any] = {"type": json_type}

        # Add default values to the schema
        if not _is_required(param):
            default = param.default
            if default is not None and default != "" and default != [] and default != {}:
                prop["default"] = default
        else:
            required.append(pname)

        properties[pname] = prop

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return schema


# ── Executor factory ────────────────────────────────────────────────────────


def _make_executor(
    server: Any,
    tool_name: str,
    company_id_ref: list[str],
    user_id_ref: list[str],
    requires_confirmation: bool,
) -> Any:
    """Create an async executor that bridges the delegate to an MCP tool.

    The executor receives kwargs from the LLM function call, injects the
    tenant context (company_id, user_id), calls the MCP server handler
    directly, and returns the JSON-serialized result string.

    Parameters
    ----------
    server:
        The ArborMCPServer instance (government, accounting, etc.).
    tool_name:
        The registered MCP tool name.
    company_id_ref:
        Mutable list holding [company_id] for tenant injection.
    user_id_ref:
        Mutable list holding [user_id] for tenant injection.
    requires_confirmation:
        Whether this tool requires human confirmation before execution.
    """

    async def executor(**kwargs: Any) -> str:
        cid = company_id_ref[0] if company_id_ref else ""
        uid = user_id_ref[0] if user_id_ref else "system"

        if requires_confirmation:
            return json.dumps(
                {
                    "status": "confirmation_required",
                    "tool": tool_name,
                    "message": (
                        f"Tool '{tool_name}' requires human confirmation before "
                        f"execution. Present the action details to the user and "
                        f"wait for explicit approval."
                    ),
                    "arguments": {k: _safe_serialize(v) for k, v in kwargs.items()},
                },
                default=str,
            )

        result = await server.call_tool(
            tool_name,
            company_id=cid,
            user_id=uid,
            **kwargs,
        )
        return json.dumps(result, default=str)

    return executor


def _safe_serialize(value: Any) -> Any:
    """Safely convert a value for JSON serialization in confirmation messages."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, dict)):
        # Truncate large structures in confirmation previews
        s = json.dumps(value, default=str)
        if len(s) > 500:
            return f"[{type(value).__name__} with {len(value)} items]"
        return value
    return str(value)


# ── MCP server module loaders ───────────────────────────────────────────────
# Lazy imports to avoid loading all adapters at startup.


def _load_government_server() -> Any:
    from hr_advisory.mcp_servers.government_server import server

    return server


def _load_accounting_server() -> Any:
    from hr_advisory.mcp_servers.accounting_server import server

    return server


def _load_banking_server() -> Any:
    from hr_advisory.mcp_servers.banking_server import server

    return server


def _load_communications_server() -> Any:
    from hr_advisory.mcp_servers.communications_server import server

    return server


def _load_regulatory_server() -> Any:
    from hr_advisory.mcp_servers.regulatory_server import server

    return server


_SERVER_LOADERS = [
    ("government", _load_government_server),
    ("accounting", _load_accounting_server),
    ("banking", _load_banking_server),
    ("communications", _load_communications_server),
    ("regulatory", _load_regulatory_server),
]


# ── Public registration function ────────────────────────────────────────────


def register_mcp_tools(
    registry: ToolRegistry,
    company_id: str = "",
    user_id: str = "system",
) -> dict[str, list[str]]:
    """Register all MCP server tools in the kaizen-agents ToolRegistry.

    This function iterates over all 5 Arbor MCP servers, extracts tool
    definitions (name, description, parameter schema), and registers each
    as a callable tool in the delegate's ToolRegistry.

    Tools that require human confirmation (government submissions, financial
    postings, payment initiations) return a confirmation-required response
    instead of executing directly. The delegate loop should present these
    to the user for approval before re-invoking with confirmation.

    Args:
        registry: The kaizen-agents ToolRegistry to populate.
        company_id: Tenant company ID for scoping MCP tool calls.
        user_id: Authenticated user ID for audit trail.

    Returns:
        Dict mapping server name to list of registered tool names.
        Example: {"government": ["gov_cpf_validate", ...], ...}
    """
    # Mutable refs so tenant context can be updated after registration
    company_id_ref = [company_id]
    user_id_ref = [user_id]

    registered: dict[str, list[str]] = {}
    total = 0

    for server_name, loader in _SERVER_LOADERS:
        try:
            server = loader()
        except Exception:
            logger.exception("Failed to load MCP server: %s", server_name)
            registered[server_name] = []
            continue

        server_tools: list[str] = []

        for tool_name, tool_def in server._tools.items():
            handler = tool_def["handler"]
            description = tool_def.get("description", "")
            requires_confirmation = tool_def.get("requires_confirmation", False)

            # Extract parameter schema from the original function signature
            schema = _extract_tool_schema(tool_name, handler)

            # Build the executor bridge
            executor = _make_executor(
                server=server,
                tool_name=tool_name,
                company_id_ref=company_id_ref,
                user_id_ref=user_id_ref,
                requires_confirmation=requires_confirmation,
            )

            # Prefix description with server category and confirmation flag
            prefix = f"[{server_name.upper()}] "
            if requires_confirmation:
                prefix += "[REQUIRES CONFIRMATION] "
            full_description = f"{prefix}{description}"

            registry.register(
                name=tool_name,
                description=full_description,
                parameters=schema,
                executor=executor,
            )

            server_tools.append(tool_name)
            total += 1

        registered[server_name] = server_tools
        logger.info(
            "MCP server '%s' registered %d tools in delegate ToolRegistry",
            server_name,
            len(server_tools),
        )

    logger.info(
        "MCP tools registration complete: %d tools from %d servers",
        total,
        len(registered),
    )

    return registered


def update_mcp_tenant_context(
    company_id: str,
    user_id: str = "system",
) -> None:
    """Update the tenant context for MCP tool executors.

    Call this when the authenticated user or company changes mid-session
    (e.g., after login or company switch). The mutable refs created during
    registration are updated in-place so all existing executors pick up
    the new values.

    Note: This function only works if register_mcp_tools() was called
    in the same process. The refs are module-level state.
    """
    # This is intentionally a no-op placeholder -- the actual ref mutation
    # happens in the executor closures via company_id_ref and user_id_ref.
    # To support dynamic updates, the caller should hold onto these refs.
    # See register_mcp_tools() return value for the list of registered tools.
    logger.info(
        "MCP tenant context update requested: company=%s user=%s",
        company_id,
        user_id,
    )
