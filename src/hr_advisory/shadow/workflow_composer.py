# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Workflow composer for the Shadow Agent.

Expands high-level intents into multi-step PACE sessions. For example,
"create employee" becomes a 3-step onboarding workflow: create employee,
generate KET, send invite email.

Returns None for single-step intents that don't need expansion.
"""

from __future__ import annotations

import logging
from typing import Any

from hr_advisory.shadow.pace import PaceStep
from hr_advisory.shadow.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

__all__ = [
    "compose_workflow",
]


def compose_workflow(
    module: str,
    action: str,
    entities: dict[str, Any],
    registry: ToolRegistry,
) -> list[PaceStep] | None:
    """Expand a high-level intent into a multi-step PACE workflow.

    Known multi-step workflows:
    - ("employees", "create") -> [create employee, generate KET, send invite]
    - ("employees", "import") -> [preview import, execute import]

    Args:
        module: The target module (e.g. "employees").
        action: The target action (e.g. "create", "import").
        entities: The extracted entities from the intent classifier.
        registry: The tool registry to look up tool definitions.

    Returns:
        A list of PaceStep objects for multi-step workflows, or None
        if the intent is a single-step operation (caller should use
        the default single-step behavior).
    """
    # Look up known multi-step workflows
    if module == "employees" and action == "create":
        return _expand_onboarding(entities, registry)

    if module == "employees" and action == "import":
        return _expand_import(entities, registry)

    # No expansion — caller uses single-step default
    return None


def _expand_onboarding(
    entities: dict[str, Any],
    registry: ToolRegistry,
) -> list[PaceStep]:
    """Expand employee creation into a 3-step onboarding workflow.

    Steps:
    1. Create employee (via invite endpoint)
    2. Generate Key Employment Terms (KET) document
    3. Send invite email

    Args:
        entities: The extracted entities (e.g. name, email).
        registry: The tool registry to look up tool definitions.

    Returns:
        A list of 3 PaceStep objects.
    """
    steps: list[PaceStep] = []

    # Step 1: Create employee
    create_tool = registry.resolve_tool("employees", "create")
    if create_tool is not None:
        steps.append(
            PaceStep(
                description=create_tool.description,
                tool_module=create_tool.module,
                tool_action=create_tool.action,
                method=create_tool.method,
                path=create_tool.path,
                params=dict(entities),
            )
        )
    else:
        logger.error("Onboarding workflow: 'employees.create' tool not found in registry")
        steps.append(
            PaceStep(
                description="Invite a new employee to the company",
                tool_module="employees",
                tool_action="create",
                method="POST",
                path="/employees/invite",
                params=dict(entities),
            )
        )

    # Step 2: Generate KET document
    ket_tool = registry.resolve_tool("documents", "generate")
    if ket_tool is not None:
        steps.append(
            PaceStep(
                description="Generate Key Employment Terms (KET) document",
                tool_module=ket_tool.module,
                tool_action=ket_tool.action,
                method=ket_tool.method,
                path=ket_tool.path,
                params={"template_id": "ket"},
            )
        )
    else:
        logger.error("Onboarding workflow: 'documents.generate' tool not found in registry")
        steps.append(
            PaceStep(
                description="Generate Key Employment Terms (KET) document",
                tool_module="documents",
                tool_action="generate",
                method="POST",
                path="/document/generate",
                params={"template_id": "ket"},
            )
        )

    # Step 3: Send invite email
    # Re-use the create tool's path for the invite step since invite IS the create action
    invite_email = entities.get("email", "")
    steps.append(
        PaceStep(
            description="Send welcome email to the new employee",
            tool_module="employees",
            tool_action="invite",
            method="POST",
            path="/employees/invite",
            params={"email": invite_email} if invite_email else {},
        )
    )

    logger.info("Onboarding workflow expanded: %d steps", len(steps))
    return steps


def _expand_import(
    entities: dict[str, Any],
    registry: ToolRegistry,
) -> list[PaceStep]:
    """Expand employee import into a 2-step preview-then-execute workflow.

    Steps:
    1. Preview import (validate CSV/Excel data)
    2. Execute import (create employees from validated data)

    Args:
        entities: The extracted entities (e.g. format, file reference).
        registry: The tool registry to look up tool definitions.

    Returns:
        A list of 2 PaceStep objects.
    """
    steps: list[PaceStep] = []

    # Step 1: Preview import
    import_tool = registry.resolve_tool("employees", "import")
    if import_tool is not None:
        steps.append(
            PaceStep(
                description="Preview bulk employee import — validate data before committing",
                tool_module=import_tool.module,
                tool_action=import_tool.action,
                method=import_tool.method,
                path=import_tool.path,
                params=dict(entities),
            )
        )
    else:
        logger.error("Import workflow: 'employees.import' tool not found in registry")
        steps.append(
            PaceStep(
                description="Preview bulk employee import — validate data before committing",
                tool_module="employees",
                tool_action="import",
                method="POST",
                path="/employees/import/preview",
                params=dict(entities),
            )
        )

    # Step 2: Execute import
    steps.append(
        PaceStep(
            description="Execute bulk employee import — create employee records",
            tool_module="employees",
            tool_action="import_execute",
            method="POST",
            path="/employees/import/execute",
            params=dict(entities),
        )
    )

    logger.info("Import workflow expanded: %d steps", len(steps))
    return steps
