# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Async HTTP executor for the Shadow Agent.

Executes API calls on behalf of the user by forwarding their JWT token.
The executor never escalates privileges — it uses the exact same
permissions the user has in the frontend.

Uses httpx.AsyncClient for async HTTP requests. Base URL defaults to
the local server (http://localhost:8000) or can be configured via
ARBOR_API_BASE_URL environment variable.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ExecutionResult",
    "ExecutionStep",
    "ShadowExecutor",
]


@dataclass
class ExecutionResult:
    """Result of a single API call execution."""

    success: bool
    status_code: int
    data: dict[str, Any]  # parsed JSON response body
    error: str  # human-friendly error message, empty on success
    duration_ms: float  # execution time in milliseconds
    tool_module: str  # which module this call was for
    tool_action: str  # which action this call was for
    timestamp: str  # ISO 8601 timestamp

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON responses."""
        return {
            "success": self.success,
            "status_code": self.status_code,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "tool_module": self.tool_module,
            "tool_action": self.tool_action,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionStep:
    """A single step in a multi-step execution plan."""

    module: str
    action: str
    method: str
    path: str
    params: dict[str, Any]
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON responses."""
        return {
            "module": self.module,
            "action": self.action,
            "method": self.method,
            "path": self.path,
            "params": self.params,
            "description": self.description,
        }


def _get_base_url() -> str:
    """Get the API base URL from environment or default.

    Returns:
        The base URL for API calls (no trailing slash).
    """
    url = os.environ.get("ARBOR_API_BASE_URL", "http://localhost:8000")
    return url.rstrip("/")


def _substitute_path_params(path: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Substitute path parameters like {employee_id} into the URL path.

    Returns:
        (resolved_path, remaining_params) — the path with substitutions
        applied, and the params dict with used keys removed.
    """
    remaining = dict(params)
    placeholders = re.findall(r"\{(\w+)\}", path)
    for placeholder in placeholders:
        if placeholder in remaining:
            value = remaining.pop(placeholder)
            path = path.replace(f"{{{placeholder}}}", str(value))
    return path, remaining


def _translate_error(status_code: int, body: dict[str, Any]) -> str:
    """Translate an HTTP error response into a user-friendly message.

    Args:
        status_code: The HTTP status code.
        body: The parsed JSON response body (may contain "detail").

    Returns:
        A human-friendly error message.
    """
    detail = body.get("detail", "")
    if isinstance(detail, list):
        # FastAPI validation errors come as a list of dicts
        messages = []
        for item in detail:
            if isinstance(item, dict):
                loc = " > ".join(str(l) for l in item.get("loc", []))
                msg = item.get("msg", "")
                messages.append(f"{loc}: {msg}" if loc else msg)
            else:
                messages.append(str(item))
        detail = "; ".join(messages)
    elif not isinstance(detail, str):
        detail = str(detail)

    error_map = {
        400: (
            f"The request was invalid: {detail}"
            if detail
            else "The request was invalid. Please check the parameters."
        ),
        401: "You need to log in again to perform this action.",
        403: "You don't have permission to perform this action.",
        404: detail if detail else "The requested item was not found.",
        409: detail if detail else "This action conflicts with the current state.",
        422: (
            f"Some information is missing or incorrect: {detail}"
            if detail
            else "Some information is missing or incorrect."
        ),
        429: "Too many requests. Please wait a moment and try again.",
        500: "Something went wrong on the server. Please try again later.",
    }

    return error_map.get(
        status_code,
        (
            f"Request failed (status {status_code}): {detail}"
            if detail
            else f"Request failed with status {status_code}."
        ),
    )


class ShadowExecutor:
    """Async HTTP client that executes API calls for the Shadow Agent.

    All calls forward the user's JWT token — the executor never has
    more permissions than the user themselves.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or _get_base_url()

    async def execute(
        self,
        tool: Any,  # ToolDefinition — using Any to avoid circular import at module level
        params: dict[str, Any],
        jwt_token: str,
    ) -> ExecutionResult:
        """Execute a single API call.

        Args:
            tool: The ToolDefinition describing which API to call.
            params: Parameters to send (path params are substituted,
                remaining become query params or JSON body).
            jwt_token: The user's JWT for authorization.

        Returns:
            An ExecutionResult with the response data or error.
        """
        import httpx
        import time

        method = tool.method.upper()
        path, remaining_params = _substitute_path_params(tool.path, params)
        url = f"{self._base_url}{path}"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }

        start_time = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(
                        url,
                        headers=headers,
                        params=remaining_params if remaining_params else None,
                    )
                elif method == "POST":
                    response = await client.post(
                        url,
                        headers=headers,
                        json=remaining_params if remaining_params else {},
                    )
                elif method == "PATCH":
                    response = await client.patch(
                        url,
                        headers=headers,
                        json=remaining_params if remaining_params else {},
                    )
                elif method == "PUT":
                    response = await client.put(
                        url,
                        headers=headers,
                        json=remaining_params if remaining_params else {},
                    )
                elif method == "DELETE":
                    response = await client.delete(
                        url,
                        headers=headers,
                        params=remaining_params if remaining_params else None,
                    )
                else:
                    elapsed = (time.monotonic() - start_time) * 1000
                    return ExecutionResult(
                        success=False,
                        status_code=0,
                        data={},
                        error=f"Unsupported HTTP method: {method}",
                        duration_ms=elapsed,
                        tool_module=tool.module,
                        tool_action=tool.action,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )

            elapsed = (time.monotonic() - start_time) * 1000

            # Parse response body
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text[:1000]}

            if 200 <= response.status_code < 300:
                return ExecutionResult(
                    success=True,
                    status_code=response.status_code,
                    data=body if isinstance(body, dict) else {"result": body},
                    error="",
                    duration_ms=round(elapsed, 2),
                    tool_module=tool.module,
                    tool_action=tool.action,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            else:
                error_msg = _translate_error(
                    response.status_code,
                    body if isinstance(body, dict) else {},
                )
                return ExecutionResult(
                    success=False,
                    status_code=response.status_code,
                    data=body if isinstance(body, dict) else {},
                    error=error_msg,
                    duration_ms=round(elapsed, 2),
                    tool_module=tool.module,
                    tool_action=tool.action,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        except Exception as exc:
            elapsed = (time.monotonic() - start_time) * 1000
            # Translate common httpx exceptions to user-friendly messages
            error_msg = "Could not connect to the server. Please try again."
            exc_type = type(exc).__name__
            if "Timeout" in exc_type:
                error_msg = "The request timed out. Please try again."
            elif "Connect" in exc_type:
                error_msg = "Could not reach the server. Please check your connection."

            logger.error(
                "Shadow executor HTTP error: %s %s — %s: %s",
                method,
                url,
                exc_type,
                exc,
            )

            return ExecutionResult(
                success=False,
                status_code=0,
                data={},
                error=error_msg,
                duration_ms=round(elapsed, 2),
                tool_module=tool.module,
                tool_action=tool.action,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def execute_multi_step(
        self,
        steps: list[ExecutionStep],
        jwt_token: str,
    ) -> list[ExecutionResult]:
        """Execute a sequence of API calls in order.

        Each step runs sequentially. If a step fails and is not a read
        operation, subsequent steps are skipped.

        Args:
            steps: Ordered list of ExecutionSteps to execute.
            jwt_token: The user's JWT for authorization.

        Returns:
            List of ExecutionResults, one per step attempted.
        """
        from hr_advisory.shadow.tool_registry import ToolDefinition

        results: list[ExecutionResult] = []

        for step in steps:
            # Create a lightweight ToolDefinition for the executor
            tool = ToolDefinition(
                module=step.module,
                action=step.action,
                method=step.method,
                path=step.path,
                params=[],
                trust_level="propose",
                description=step.description,
            )

            result = await self.execute(tool, step.params, jwt_token)
            results.append(result)

            # Stop on failure for write operations (reads can continue)
            if not result.success and step.method.upper() != "GET":
                logger.warning(
                    "Multi-step execution stopped at step %d/%d (%s.%s): %s",
                    len(results),
                    len(steps),
                    step.module,
                    step.action,
                    result.error,
                )
                break

        return results
