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
    - entity_resolver: Maps LLM-extracted entities to API parameter names
    - workflow_composer: Expands intents into multi-step PACE workflows
    - observation: User session behavior tracking and intent inference
    - memory: Observation distillation into persistent preferences
"""

from __future__ import annotations

from hr_advisory.shadow.intent_classifier import ShadowIntent, ShadowIntentClassifier
from hr_advisory.shadow.tool_registry import ToolDefinition, ToolRegistry
from hr_advisory.shadow.executor import ExecutionResult, ExecutionStep, ShadowExecutor
from hr_advisory.shadow.pace import PaceManager, PaceSession, PaceStep
from hr_advisory.shadow.formatter import ArborFormatter
from hr_advisory.shadow.entity_resolver import detect_missing_required, resolve_entities
from hr_advisory.shadow.workflow_composer import compose_workflow
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
    "ShadowIntent",
    "ShadowIntentClassifier",
    "ToolDefinition",
    "ToolRegistry",
    "UserMemory",
    "compose_workflow",
    "detect_missing_required",
    "generate_briefing",
    "get_memory_store",
    "get_nudges",
    "get_observation_store",
    "resolve_entities",
]
