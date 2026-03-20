# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Shadow Agent workflow composer.

Covers: multi-step workflow expansion, single-step passthrough,
onboarding workflow, import workflow.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

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


from hr_advisory.shadow.pace import PaceStep
from hr_advisory.shadow.tool_registry import ToolRegistry, get_tool_registry
from hr_advisory.shadow.workflow_composer import compose_workflow


class TestComposeWorkflow:
    """Workflow composer must expand multi-step intents into PaceStep lists."""

    def setup_method(self) -> None:
        self.registry = get_tool_registry()

    def test_onboarding_expands_to_three_steps(self) -> None:
        """Employee create should expand to: create + generate KET + send invite."""
        steps = compose_workflow(
            module="employees",
            action="create",
            entities={"name": "John", "email": "john@example.com"},
            registry=self.registry,
        )
        assert steps is not None
        assert len(steps) == 3

    def test_onboarding_step_types(self) -> None:
        """Onboarding steps must be PaceStep instances with correct modules."""
        steps = compose_workflow(
            module="employees",
            action="create",
            entities={"name": "John"},
            registry=self.registry,
        )
        assert steps is not None
        assert all(isinstance(s, PaceStep) for s in steps)

        # Step 1: create employee
        assert steps[0].tool_module == "employees"
        assert steps[0].tool_action == "create"
        assert steps[0].method == "POST"

        # Step 2: generate KET
        assert steps[1].tool_module == "documents"
        assert steps[1].tool_action == "generate"

        # Step 3: send invite email
        assert steps[2].tool_module == "employees"

    def test_onboarding_carries_entities_to_first_step(self) -> None:
        """The first onboarding step should receive the original entities."""
        steps = compose_workflow(
            module="employees",
            action="create",
            entities={"name": "Jane", "email": "jane@example.com"},
            registry=self.registry,
        )
        assert steps is not None
        assert (
            steps[0].params.get("name") == "Jane"
            or steps[0].params.get("email") == "jane@example.com"
        )

    def test_import_expands_to_two_steps(self) -> None:
        """Employee import should expand to: preview + execute."""
        steps = compose_workflow(
            module="employees",
            action="import",
            entities={"format": "csv"},
            registry=self.registry,
        )
        assert steps is not None
        assert len(steps) == 2

    def test_payroll_calculate_returns_none(self) -> None:
        """Payroll calculate is single-step — no expansion needed."""
        steps = compose_workflow(
            module="payroll",
            action="calculate",
            entities={"month": "March"},
            registry=self.registry,
        )
        assert steps is None

    def test_unknown_module_returns_none(self) -> None:
        """Unknown module/action combos should return None (single-step default)."""
        steps = compose_workflow(
            module="claims",
            action="create",
            entities={},
            registry=self.registry,
        )
        assert steps is None

    def test_leave_apply_returns_none(self) -> None:
        """Leave apply is single-step — no expansion needed."""
        steps = compose_workflow(
            module="leave",
            action="apply",
            entities={"type": "annual"},
            registry=self.registry,
        )
        assert steps is None

    def test_onboarding_steps_have_descriptions(self) -> None:
        """Each expanded step must have a non-empty description."""
        steps = compose_workflow(
            module="employees",
            action="create",
            entities={"name": "Test"},
            registry=self.registry,
        )
        assert steps is not None
        for step in steps:
            assert step.description, f"Step {step.tool_action} has no description"

    def test_onboarding_steps_have_valid_paths(self) -> None:
        """Each expanded step must have a non-empty path."""
        steps = compose_workflow(
            module="employees",
            action="create",
            entities={"name": "Test"},
            registry=self.registry,
        )
        assert steps is not None
        for step in steps:
            assert step.path, f"Step {step.tool_action} has no path"

    def test_import_steps_have_correct_modules(self) -> None:
        """Import steps must be in the employees module."""
        steps = compose_workflow(
            module="employees",
            action="import",
            entities={},
            registry=self.registry,
        )
        assert steps is not None
        assert steps[0].tool_module == "employees"
        assert steps[0].tool_action == "import"  # preview step
