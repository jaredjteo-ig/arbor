"""MCP Server Registry — central registry for all integration servers.

Provides discovery and management of all 5 MCP servers. The shadow agent
uses this to discover available tools. The admin API uses this for
health monitoring and configuration.

T204: MCP Server Scaffold + Registry
"""

from __future__ import annotations

import logging
from typing import Optional

from hr_advisory.mcp_servers.base import AiteMCPServer

logger = logging.getLogger(__name__)

# Lazy-initialized server instances
_servers: dict[str, AiteMCPServer] = {}
_initialized = False


def _create_servers() -> dict[str, AiteMCPServer]:
    """Create and configure all MCP server instances.

    Imports are deferred to avoid circular dependencies and to allow
    each server module to register its tools at import time.
    """
    servers = {}

    try:
        from hr_advisory.mcp_servers.regulatory_server import server as regulatory

        servers["aite-regulatory"] = regulatory
    except ImportError:
        logger.warning("aite-regulatory server not available")

    try:
        from hr_advisory.mcp_servers.government_server import server as government

        servers["aite-government"] = government
    except ImportError:
        logger.warning("aite-government server not available")

    try:
        from hr_advisory.mcp_servers.accounting_server import server as accounting

        servers["aite-accounting"] = accounting
    except ImportError:
        logger.warning("aite-accounting server not available")

    try:
        from hr_advisory.mcp_servers.banking_server import server as banking

        servers["aite-banking"] = banking
    except ImportError:
        logger.warning("aite-banking server not available")

    try:
        from hr_advisory.mcp_servers.communications_server import server as comms

        servers["aite-communications"] = comms
    except ImportError:
        logger.warning("aite-communications server not available")

    logger.info("MCP registry initialized: %d servers", len(servers))
    return servers


def get_all_servers() -> dict[str, AiteMCPServer]:
    """Get all registered MCP servers."""
    global _servers, _initialized
    if not _initialized:
        _servers = _create_servers()
        _initialized = True
    return _servers


def get_server(name: str) -> Optional[AiteMCPServer]:
    """Get a specific MCP server by name."""
    return get_all_servers().get(name)


def list_all_tools() -> list[dict]:
    """List all tools across all servers (for shadow agent discovery)."""
    tools = []
    for server_name, server in get_all_servers().items():
        for tool in server.list_tools():
            tools.append(
                {
                    "server": server_name,
                    "name": tool["name"],
                    "description": tool["description"],
                }
            )
    return tools


def list_all_resources() -> list[dict]:
    """List all resources across all servers."""
    resources = []
    for server_name, server in get_all_servers().items():
        for resource in server.list_resources():
            resources.append(
                {
                    "server": server_name,
                    **resource,
                }
            )
    return resources


def get_all_health() -> dict:
    """Get health status of all servers."""
    return {name: server.get_health() for name, server in get_all_servers().items()}


async def call_tool(tool_name: str, **kwargs) -> dict:
    """Route a tool call to the correct server.

    Searches all servers for the named tool and invokes it.
    This is the primary entry point for the shadow agent.
    """
    for server in get_all_servers().values():
        if tool_name in server._tools:
            return await server.call_tool(tool_name, **kwargs)

    return {
        "status": "error",
        "message": f"Tool '{tool_name}' not found in any MCP server",
        "available_servers": list(get_all_servers().keys()),
    }
