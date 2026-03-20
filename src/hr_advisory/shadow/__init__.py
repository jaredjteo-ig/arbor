# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Shadow Agent execution engine — the intelligence layer for Arbor.

Arbor is NOT a chatbot. It understands intent and EXECUTES actions on the
user's behalf through the PACE loop: Preview, Approve, Confirm, Exit.

Components:
    - intent_classifier: LLM-based intent classification from user messages
    - tool_registry: Maps (module, action) pairs to API call configurations
    - executor: Async HTTP client that executes API calls with user's JWT
    - pace: PACE session manager for write-operation confirmation flow
    - formatter: Response formatter with Arbor identity
"""

from __future__ import annotations

from hr_advisory.shadow.intent_classifier import ShadowIntent, ShadowIntentClassifier
from hr_advisory.shadow.tool_registry import ToolDefinition, ToolRegistry
from hr_advisory.shadow.executor import ExecutionResult, ExecutionStep, ShadowExecutor
from hr_advisory.shadow.pace import PaceManager, PaceSession, PaceStep
from hr_advisory.shadow.formatter import ArborFormatter

__all__ = [
    "ArborFormatter",
    "ExecutionResult",
    "ExecutionStep",
    "PaceManager",
    "PaceSession",
    "PaceStep",
    "ShadowExecutor",
    "ShadowIntent",
    "ShadowIntentClassifier",
    "ToolDefinition",
    "ToolRegistry",
]
