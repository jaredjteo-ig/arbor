"""Integration tests for AiteMCPServer base class.

Tests:
- Tool registration and invocation
- Tenant isolation (audit log filtered by company_id)
- Audit logging (entries created with correct fields, no PII leakage)
- Health endpoint
- Resource registration
- Error standardization on tool failure
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.base import AiteMCPServer, TenantContext, ToolInvocationRecord

from .conftest import TENANT_A, TENANT_B, USER_A, USER_B


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Tool registration via the @server.tool decorator."""

    def test_registered_tools_appear_in_list(self, mcp_server: AiteMCPServer):
        tools = mcp_server.list_tools()
        names = [t["name"] for t in tools]
        assert "test_echo" in names
        assert "test_fail" in names
        assert "test_confirm" in names

    def test_tool_description_preserved(self, mcp_server: AiteMCPServer):
        tools = {t["name"]: t for t in mcp_server.list_tools()}
        assert tools["test_echo"]["description"] == "Echo input back"
        assert tools["test_confirm"]["description"] == "Requires confirmation"

    def test_requires_confirmation_flag_stored(self, mcp_server: AiteMCPServer):
        tool_meta = mcp_server._tools["test_confirm"]
        assert tool_meta["requires_confirmation"] is True
        assert mcp_server._tools["test_echo"]["requires_confirmation"] is False

    def test_unknown_tool_returns_error(self, mcp_server: AiteMCPServer):
        """Calling an unregistered tool returns a structured error, not an exception."""

    async def test_unknown_tool_returns_error_dict(self, mcp_server: AiteMCPServer):
        result = await mcp_server.call_tool("nonexistent_tool", company_id=TENANT_A)
        assert result["status"] == "error"
        assert "Unknown tool" in result["message"]


# ---------------------------------------------------------------------------
# Tool invocation
# ---------------------------------------------------------------------------


class TestToolInvocation:
    """Tool invocation through call_tool() and the wrapped handler."""

    async def test_successful_invocation_returns_result(self, mcp_server: AiteMCPServer):
        result = await mcp_server.call_tool(
            "test_echo", company_id=TENANT_A, user_id=USER_A, message="ping"
        )
        assert result == {"echo": "ping", "company_id": TENANT_A}

    async def test_default_user_id_is_system(self, mcp_server: AiteMCPServer):
        """When user_id is not provided, it defaults to 'system'."""
        await mcp_server.call_tool("test_echo", company_id=TENANT_A)
        record = mcp_server._audit_log[-1]
        assert record.user_id == "system"

    async def test_failing_tool_returns_error_dict(self, mcp_server: AiteMCPServer):
        result = await mcp_server.call_tool("test_fail", company_id=TENANT_A, user_id=USER_A)
        assert result["status"] == "error"
        assert result["error"] == "RuntimeError"
        assert "deliberate failure" in result["message"]
        assert result["tool"] == "test_fail"

    async def test_tool_receives_tenant_context(self, mcp_server: AiteMCPServer):
        """The tool handler receives a TenantContext with the correct company_id."""
        result = await mcp_server.call_tool(
            "test_echo", company_id=TENANT_B, user_id=USER_B, message="ctx_test"
        )
        assert result["company_id"] == TENANT_B


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


class TestAuditLogging:
    """Audit trail created for every tool invocation."""

    async def test_successful_call_creates_audit_entry(self, mcp_server: AiteMCPServer):
        await mcp_server.call_tool("test_echo", company_id=TENANT_A, user_id=USER_A)
        log = mcp_server.get_audit_log()
        assert len(log) >= 1
        entry = log[0]
        assert entry["tool_name"] == "test_echo"
        assert entry["company_id"] == TENANT_A
        assert entry["user_id"] == USER_A
        assert entry["status"] == "success"
        assert entry["duration_ms"] >= 0
        assert entry["error_type"] is None

    async def test_failed_call_creates_audit_entry_with_error(self, mcp_server: AiteMCPServer):
        await mcp_server.call_tool("test_fail", company_id=TENANT_A, user_id=USER_A)
        log = mcp_server.get_audit_log()
        entry = log[0]
        assert entry["status"] == "error"
        assert entry["error_type"] == "RuntimeError"

    async def test_audit_log_filtered_by_company(self, mcp_server: AiteMCPServer):
        """Audit log can be filtered by company_id -- tenant isolation."""
        await mcp_server.call_tool("test_echo", company_id=TENANT_A, user_id=USER_A)
        await mcp_server.call_tool("test_echo", company_id=TENANT_B, user_id=USER_B)

        log_a = mcp_server.get_audit_log(company_id=TENANT_A)
        log_b = mcp_server.get_audit_log(company_id=TENANT_B)

        assert all(e["company_id"] == TENANT_A for e in log_a)
        assert all(e["company_id"] == TENANT_B for e in log_b)

    async def test_audit_log_limit(self, mcp_server: AiteMCPServer):
        for _ in range(5):
            await mcp_server.call_tool("test_echo", company_id=TENANT_A, user_id=USER_A)
        log = mcp_server.get_audit_log(limit=3)
        assert len(log) == 3

    async def test_audit_log_sorted_newest_first(self, mcp_server: AiteMCPServer):
        await mcp_server.call_tool(
            "test_echo", company_id=TENANT_A, user_id=USER_A, message="first"
        )
        await mcp_server.call_tool(
            "test_echo", company_id=TENANT_A, user_id=USER_A, message="second"
        )
        log = mcp_server.get_audit_log()
        assert log[0]["timestamp"] >= log[1]["timestamp"]

    async def test_audit_entries_do_not_contain_request_payload(self, mcp_server: AiteMCPServer):
        """Audit entries must not leak tool arguments (potential PII)."""
        await mcp_server.call_tool(
            "test_echo", company_id=TENANT_A, user_id=USER_A, message="secret_salary_5000"
        )
        log = mcp_server.get_audit_log()
        entry = log[0]
        serialized = str(entry)
        assert "secret_salary_5000" not in serialized

    async def test_audit_entry_has_unique_id(self, mcp_server: AiteMCPServer):
        await mcp_server.call_tool("test_echo", company_id=TENANT_A, user_id=USER_A)
        await mcp_server.call_tool("test_echo", company_id=TENANT_A, user_id=USER_A)
        log = mcp_server.get_audit_log()
        ids = [e["id"] for e in log]
        assert len(ids) == len(set(ids)), "Audit entry IDs must be unique"


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Server health status."""

    def test_health_includes_server_name(self, mcp_server: AiteMCPServer):
        health = mcp_server.get_health()
        assert health["server"] == "aite-test-server"

    def test_health_includes_version(self, mcp_server: AiteMCPServer):
        health = mcp_server.get_health()
        assert health["version"] == "0.0.1"

    def test_health_reports_tool_count(self, mcp_server: AiteMCPServer):
        health = mcp_server.get_health()
        assert health["tools_registered"] == 3

    async def test_health_tracks_total_invocations(self, mcp_server: AiteMCPServer):
        assert mcp_server.get_health()["total_invocations"] == 0
        await mcp_server.call_tool("test_echo", company_id=TENANT_A)
        assert mcp_server.get_health()["total_invocations"] == 1
        await mcp_server.call_tool("test_fail", company_id=TENANT_A)
        assert mcp_server.get_health()["total_invocations"] == 2

    def test_health_includes_timestamp(self, mcp_server: AiteMCPServer):
        health = mcp_server.get_health()
        assert "timestamp" in health
        assert "T" in health["timestamp"]  # ISO 8601 format


# ---------------------------------------------------------------------------
# Resource registration
# ---------------------------------------------------------------------------


class TestResourceRegistration:
    """MCP resource registration and retrieval."""

    def test_register_and_list_resource(self):
        server = AiteMCPServer(name="res-test")

        @server.resource("aite://status", name="Status", description="Server status")
        def status_resource():
            return {"status": "ok"}

        resources = server.list_resources()
        assert len(resources) == 1
        assert resources[0]["uri"] == "aite://status"
        assert resources[0]["name"] == "Status"

    def test_get_resource_by_uri(self):
        server = AiteMCPServer(name="res-test")

        @server.resource("aite://version")
        def version_resource():
            return {"version": "1.0.0"}

        result = server.get_resource("aite://version")
        assert result == {"version": "1.0.0"}

    def test_get_unknown_resource_returns_none(self):
        server = AiteMCPServer(name="res-test")
        assert server.get_resource("aite://nonexistent") is None
