# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Arbor Delegate — autonomous HR assistant powered by kaizen-agents.

The Delegate is the Layer 3 entrypoint for Arbor, built on the
kaizen-agents AgentLoop (Layer 2 engine). It replaces the manual
advisory_engine.py ReAct loop with the SDK's native autonomous
tool-calling loop.

Architecture:
    Layer 1: PRIMITIVES (kailash-kaizen) — signatures, tool protocol
    Layer 2: ENGINE (kaizen-agents: AgentLoop) — while-loop + streaming
    Layer 3: ENTRYPOINT (this module) — Arbor tools + system prompt + SSE

Usage:
    from hr_advisory.delegate import create_delegate, stream_response

    loop = create_delegate(api_key="...", company_context={...})
    async for chunk in loop.run_turn("What is the CPF rate for age 30?"):
        yield chunk  # stream to client
"""

from hr_advisory.delegate.arbor_loop import DelegateConfig, create_delegate, stream_delegate
from hr_advisory.delegate.tools import register_arbor_tools, ToolHydrator

__all__ = [
    "DelegateConfig",
    "ToolHydrator",
    "create_delegate",
    "register_arbor_tools",
    "stream_delegate",
]
