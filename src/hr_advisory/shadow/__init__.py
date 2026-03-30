# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Shadow Agent support modules — PACE, formatting, execution.

The primary intelligence layer is now the kaizen-agents Delegate
(see hr_advisory.delegate). These modules provide:

    - tool_registry: Maps (module, action) pairs to API call configurations
    - executor: Async HTTP client that executes API calls with user's JWT
    - pace: PACE session manager for write-operation confirmation flow
    - formatter: Response formatter with Arbor identity
    - briefing: Daily briefing generation
    - nudges: Contextual nudge suggestions
    - observation: User session behavior tracking
    - memory: Observation distillation into persistent preferences
"""

from __future__ import annotations

from hr_advisory.shadow.tool_registry import ToolDefinition, ToolRegistry
from hr_advisory.shadow.executor import ExecutionResult, ExecutionStep, ShadowExecutor
from hr_advisory.shadow.pace import PaceManager, PaceSession, PaceStep
from hr_advisory.shadow.formatter import ArborFormatter
from hr_advisory.shadow.briefing import generate_briefing
from hr_advisory.shadow.nudges import get_nudges
from hr_advisory.shadow.observation import ObservationStore, get_observation_store
from hr_advisory.shadow.memory import MemoryStore, UserMemory, get_memory_store

__all__ = [
    "ArborFormatter",
    "ExecutionResult",
    "ExecutionStep",
    "MemoryStore",
    "ObservationStore",
    "PaceManager",
    "PaceSession",
    "PaceStep",
    "ShadowExecutor",
    "ToolDefinition",
    "ToolRegistry",
    "UserMemory",
    "generate_briefing",
    "get_memory_store",
    "get_nudges",
    "get_observation_store",
]
