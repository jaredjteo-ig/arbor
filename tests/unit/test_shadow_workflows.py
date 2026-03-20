"""T482: Multi-step execution tests for the Shadow Agent.

Covers: onboarding workflow, payroll workflow, government submission,
multi-step failure handling, MCP routing, error translation, undo window.
"""

from __future__ import annotations

import sys
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

_kaizen_mods = [
    "kaizen",
    "kaizen.core",
    "kaizen.core.base_agent",
    "kaizen.memory",
    "kaizen.config",
    "kaizen.config.providers",
    "kaizen.signatures",
    "kaizen.core.workflow_generator",
    "kaizen.nodes",
    "kaizen.nodes.ai",
    "kaizen.nodes.ai.llm_agent",
]
for _m in _kaizen_mods:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

from hr_advisory.shadow.executor import ExecutionResult, ExecutionStep, ShadowExecutor
from hr_advisory.shadow.pace import PaceManager, PaceStep
from hr_advisory.shadow.tool_registry import ToolDefinition


class TestMultiStepExecution:
    @pytest.mark.asyncio
    async def test_three_step_onboarding_success(self) -> None:
        steps = [
            ExecutionStep(
                "employees", "create", "POST", "/employees", {"name": "John"}, "Create employee"
            ),
            ExecutionStep(
                "documents", "generate", "POST", "/documents/ket", {"eid": "42"}, "Generate KET"
            ),
            ExecutionStep(
                "employees",
                "invite",
                "POST",
                "/employees/invite",
                {"email": "j@t.com"},
                "Send invite",
            ),
        ]
        executor = ShadowExecutor(base_url="http://test:8000")
        i = 0
        results_data = [
            ExecutionResult(True, 201, {"id": 42}, "", 10.0, "employees", "create", "t"),
            ExecutionResult(True, 200, {"doc_id": 7}, "", 15.0, "documents", "generate", "t"),
            ExecutionResult(True, 200, {"invited": True}, "", 5.0, "employees", "invite", "t"),
        ]

        async def mock_exec(tool, params, jwt):
            nonlocal i
            r = results_data[i]
            i += 1
            return r

        executor.execute = mock_exec  # type: ignore
        results = await executor.execute_multi_step(steps, "jwt")
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_write_failure_stops_at_step_2(self) -> None:
        steps = [
            ExecutionStep("employees", "create", "POST", "/employees", {}, "Create"),
            ExecutionStep("documents", "generate", "POST", "/docs/ket", {}, "KET"),
            ExecutionStep("employees", "invite", "POST", "/invite", {}, "Invite"),
        ]
        executor = ShadowExecutor(base_url="http://test:8000")
        n = 0

        async def mock_exec(tool, params, jwt):
            nonlocal n
            n += 1
            if n == 2:
                return ExecutionResult(
                    False, 500, {}, "Server error", 10.0, "documents", "generate", "t"
                )
            return ExecutionResult(True, 200, {}, "", 5.0, tool.module, tool.action, "t")

        executor.execute = mock_exec  # type: ignore
        results = await executor.execute_multi_step(steps, "jwt")
        assert len(results) == 2
        assert results[1].success is False

    @pytest.mark.asyncio
    async def test_read_failure_continues(self) -> None:
        steps = [
            ExecutionStep("employees", "list", "GET", "/employees", {}, "List"),
            ExecutionStep("employees", "create", "POST", "/employees", {}, "Create"),
        ]
        executor = ShadowExecutor(base_url="http://test:8000")
        n = 0

        async def mock_exec(tool, params, jwt):
            nonlocal n
            n += 1
            if n == 1:
                return ExecutionResult(False, 404, {}, "Not found", 5.0, "employees", "list", "t")
            return ExecutionResult(True, 201, {"id": 1}, "", 10.0, "employees", "create", "t")

        executor.execute = mock_exec  # type: ignore
        results = await executor.execute_multi_step(steps, "jwt")
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True


class TestPACEWorkflows:
    def test_onboarding_preview(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        steps = [
            PaceStep(
                "Create employee", "employees", "create", "POST", "/employees", {"name": "John"}
            ),
            PaceStep("Generate KET", "documents", "generate", "POST", "/documents/ket", {}),
            PaceStep("Send welcome", "employees", "invite", "POST", "/employees/invite", {}),
        ]
        session = mgr.create_session(
            "admin", "employees", "create", "Onboard John", steps, "propose"
        )
        assert session.status == "preview"
        assert len(session.steps) == 3
        assert not session.requires_double_confirm

    def test_government_double_confirm(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        steps = [
            PaceStep("Generate CPF", "government", "cpf_generate", "POST", "/gov/cpf/gen", {}),
            PaceStep("Submit CPF", "government", "cpf_submit", "POST", "/gov/cpf/submit", {}),
        ]
        session = mgr.create_session(
            "admin", "government", "cpf_submit", "Submit CPF", steps, "double_confirm"
        )
        assert session.requires_double_confirm

        s, ready = mgr.confirm_session(session.id)
        assert not ready
        assert s.confirmed_count == 1

        s2, ready2 = mgr.confirm_session(session.id)
        assert ready2
        assert s2.confirmed_count == 2

    def test_single_confirm_for_propose(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        steps = [PaceStep("Run payroll", "payroll", "calculate", "POST", "/payroll/runs", {})]
        session = mgr.create_session(
            "hr", "payroll", "calculate", "March payroll", steps, "propose"
        )
        _, ready = mgr.confirm_session(session.id)
        assert ready

    def test_cancel_blocks_confirm(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        steps = [PaceStep("Delete", "employees", "delete", "DELETE", "/employees/42", {})]
        session = mgr.create_session(
            "admin", "employees", "delete", "Delete #42", steps, "always_propose"
        )
        mgr.cancel_session(session.id)
        _, ready = mgr.confirm_session(session.id)
        assert not ready


class TestMCPRouting:
    @pytest.mark.asyncio
    async def test_is_mcp_routes_to_execute_mcp(self) -> None:
        tool = ToolDefinition(
            "government",
            "cpf_submit",
            "POST",
            "/gov/cpf/submit",
            ["month"],
            "always_propose",
            "Submit CPF",
            is_mcp=True,
        )
        executor = ShadowExecutor(base_url="http://test:8000")
        executor.execute_mcp = AsyncMock(
            return_value=ExecutionResult(  # type: ignore
                True, 200, {"status": "ok"}, "", 100.0, "government", "cpf_submit", "t"
            )
        )
        result = await executor.execute(tool, {"month": "2026-03"}, "jwt")
        executor.execute_mcp.assert_called_once()
        assert result.success

    @pytest.mark.asyncio
    async def test_non_mcp_skips_execute_mcp(self) -> None:
        tool = ToolDefinition(
            "employees",
            "list",
            "GET",
            "/employees",
            [],
            "autonomous",
            "List employees",
            is_mcp=False,
        )
        executor = ShadowExecutor(base_url="http://test:8000")
        executor.execute_mcp = AsyncMock()  # type: ignore
        await executor.execute(tool, {}, "jwt")
        executor.execute_mcp.assert_not_called()


class TestErrorTranslation:
    @pytest.mark.parametrize(
        "status,keyword",
        [
            (401, "log in"),
            (403, "permission"),
            (429, "too many"),
            (500, "server"),
        ],
    )
    def test_error_keywords(self, status: int, keyword: str) -> None:
        from hr_advisory.shadow.executor import _translate_error

        assert keyword in _translate_error(status, {}).lower()

    def test_422_validation(self) -> None:
        from hr_advisory.shadow.executor import _translate_error

        msg = _translate_error(422, {"detail": [{"loc": ["body", "email"], "msg": "required"}]})
        assert "email" in msg.lower()


class TestPathSubstitution:
    def test_single_param(self) -> None:
        from hr_advisory.shadow.executor import _substitute_path_params

        path, rem = _substitute_path_params(
            "/employees/{employee_id}", {"employee_id": "42", "name": "J"}
        )
        assert path == "/employees/42"
        assert "employee_id" not in rem

    def test_multiple_params(self) -> None:
        from hr_advisory.shadow.executor import _substitute_path_params

        path, rem = _substitute_path_params("/co/{cid}/emp/{id}", {"cid": "10", "id": "42"})
        assert path == "/co/10/emp/42"
        assert len(rem) == 0


class TestUndoWindow:
    def test_undoable_within_window(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        steps = [PaceStep("T", "t", "create", "POST", "/t", {})]
        s = mgr.create_session("u1", "t", "create", "T", steps, "propose")
        s.status = "done"
        s._completed_ts = time.monotonic()
        assert s.is_undoable()

    def test_not_undoable_after_window(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        steps = [PaceStep("T", "t", "create", "POST", "/t", {})]
        s = mgr.create_session("u1", "t", "create", "T", steps, "propose")
        s.status = "done"
        s._completed_ts = time.monotonic() - 10
        assert not s.is_undoable()

    def test_not_undoable_if_pending(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        steps = [PaceStep("T", "t", "create", "POST", "/t", {})]
        s = mgr.create_session("u1", "t", "create", "T", steps, "propose")
        assert not s.is_undoable()
