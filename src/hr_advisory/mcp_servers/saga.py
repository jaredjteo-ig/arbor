"""Saga state machine for multi-step MCP tool orchestrations.

Provides recoverable multi-step workflow execution. Each step is
logged to persistent state so the shadow agent can resume from
failure points.

T209: Saga State Machine (Red Team C4)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SagaStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SagaStep:
    """A single step in a saga execution."""

    name: str
    status: StepStatus = StepStatus.PENDING
    result_summary: Optional[dict] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "result_summary": self.result_summary,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class SagaExecution:
    """A multi-step saga execution record."""

    id: str
    tenant_id: str
    saga_type: str  # e.g., "submit_cpf", "post_payroll_to_xero"
    status: SagaStatus = SagaStatus.PENDING
    steps: list[SagaStep] = field(default_factory=list)
    current_step_index: int = 0
    context: dict = field(default_factory=dict)  # Shared data between steps
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_detail: Optional[str] = None

    @property
    def current_step(self) -> Optional[SagaStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "saga_type": self.saga_type,
            "status": self.status.value,
            "current_step": self.current_step_index,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_detail": self.error_detail,
        }


class SagaOrchestrator:
    """Manages saga lifecycle — creation, advancement, failure, and recovery.

    Usage::

        orchestrator = get_saga_orchestrator()

        # Start a new saga
        saga = orchestrator.start_saga(
            tenant_id="company_123",
            saga_type="submit_cpf",
            step_names=["validate", "generate", "confirm", "submit", "verify"],
        )

        # Advance through steps
        orchestrator.start_step(saga.id)
        result = await do_validation()
        orchestrator.complete_step(saga.id, {"employees": 47, "total": 38450})

        orchestrator.start_step(saga.id)
        file = await generate_cpf_file()
        orchestrator.complete_step(saga.id, {"file_size": 12340})

        # If a step fails
        orchestrator.fail_step(saga.id, "CPF Board API timeout")
        # The saga can be resumed later from this step

        # Resume from failure
        saga = orchestrator.get_saga(saga.id)
        # current_step_index points to the failed step — retry it
    """

    def __init__(self):
        self._sagas: dict[str, SagaExecution] = {}

    def start_saga(
        self,
        tenant_id: str,
        saga_type: str,
        step_names: list[str],
        context: Optional[dict] = None,
    ) -> SagaExecution:
        """Create and start a new saga."""
        saga = SagaExecution(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            saga_type=saga_type,
            status=SagaStatus.IN_PROGRESS,
            steps=[SagaStep(name=name) for name in step_names],
            context=context or {},
        )
        self._sagas[saga.id] = saga
        logger.info(
            "Started saga %s (%s) for %s with %d steps",
            saga.id,
            saga_type,
            tenant_id,
            len(step_names),
        )
        return saga

    def start_step(self, saga_id: str) -> SagaStep:
        """Mark the current step as in-progress."""
        saga = self._get_saga(saga_id)
        step = saga.current_step
        if step is None:
            raise ValueError(f"No more steps in saga {saga_id}")
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now(timezone.utc)
        return step

    def complete_step(
        self,
        saga_id: str,
        result_summary: Optional[dict] = None,
    ) -> Optional[SagaStep]:
        """Complete the current step and advance to next.

        Returns the next step, or None if saga is complete.
        """
        saga = self._get_saga(saga_id)
        step = saga.current_step
        if step is None:
            raise ValueError(f"No active step in saga {saga_id}")

        step.status = StepStatus.COMPLETED
        step.result_summary = result_summary
        step.completed_at = datetime.now(timezone.utc)

        saga.current_step_index += 1

        if saga.current_step_index >= saga.total_steps:
            saga.status = SagaStatus.COMPLETED
            saga.completed_at = datetime.now(timezone.utc)
            logger.info("Saga %s COMPLETED", saga_id)
            return None

        logger.info(
            "Saga %s step %d/%d completed, advancing to '%s'",
            saga_id,
            saga.current_step_index,
            saga.total_steps,
            saga.steps[saga.current_step_index].name,
        )
        return saga.steps[saga.current_step_index]

    def fail_step(self, saga_id: str, error: str) -> None:
        """Mark the current step as failed. Saga can be resumed later."""
        saga = self._get_saga(saga_id)
        step = saga.current_step
        if step:
            step.status = StepStatus.FAILED
            step.error = error
            step.completed_at = datetime.now(timezone.utc)
        saga.status = SagaStatus.FAILED
        saga.error_detail = error
        logger.warning(
            "Saga %s FAILED at step '%s': %s", saga_id, step.name if step else "?", error
        )

    def set_awaiting_approval(self, saga_id: str) -> None:
        """Mark saga as waiting for human approval."""
        saga = self._get_saga(saga_id)
        saga.status = SagaStatus.AWAITING_APPROVAL

    def resume_saga(self, saga_id: str) -> SagaExecution:
        """Resume a failed saga from the failed step.

        Resets the failed step to pending so it can be retried.
        """
        saga = self._get_saga(saga_id)
        if saga.status != SagaStatus.FAILED:
            raise ValueError(f"Saga {saga_id} is not failed (status: {saga.status.value})")

        step = saga.current_step
        if step:
            step.status = StepStatus.PENDING
            step.error = None
            step.completed_at = None
        saga.status = SagaStatus.IN_PROGRESS
        saga.error_detail = None
        logger.info("Saga %s resumed at step '%s'", saga_id, step.name if step else "?")
        return saga

    def cancel_saga(self, saga_id: str) -> None:
        """Cancel an in-progress or failed saga."""
        saga = self._get_saga(saga_id)
        saga.status = SagaStatus.CANCELLED
        saga.completed_at = datetime.now(timezone.utc)
        logger.info("Saga %s CANCELLED", saga_id)

    def update_context(self, saga_id: str, **kwargs: Any) -> None:
        """Update the shared context for a saga."""
        saga = self._get_saga(saga_id)
        saga.context.update(kwargs)

    def get_saga(self, saga_id: str) -> Optional[SagaExecution]:
        """Get a saga by ID."""
        return self._sagas.get(saga_id)

    def list_sagas(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[SagaStatus] = None,
        limit: int = 50,
    ) -> list[SagaExecution]:
        """List sagas with optional filters."""
        sagas = list(self._sagas.values())
        if tenant_id:
            sagas = [s for s in sagas if s.tenant_id == tenant_id]
        if status:
            sagas = [s for s in sagas if s.status == status]
        sagas.sort(key=lambda s: s.started_at, reverse=True)
        return sagas[:limit]

    def _get_saga(self, saga_id: str) -> SagaExecution:
        saga = self._sagas.get(saga_id)
        if saga is None:
            raise ValueError(f"Unknown saga: {saga_id}")
        return saga


# Pre-defined saga templates
SAGA_TEMPLATES: dict[str, list[str]] = {
    "submit_cpf": [
        "validate_readiness",
        "generate_file",
        "confirm_action",
        "submit_to_cpf",
        "verify_acknowledgement",
    ],
    "file_ir8a": [
        "generate_ir8a_data",
        "preview_for_admin",
        "confirm_action",
        "submit_to_iras",
        "verify_acknowledgement",
    ],
    "file_ir21": [
        "generate_ir21_data",
        "confirm_action",
        "submit_to_iras",
        "verify_acknowledgement",
    ],
    "post_payroll_to_accounting": [
        "fetch_chart_of_accounts",
        "map_accounts",
        "generate_journal",
        "confirm_action",
        "post_journal",
    ],
    "bulk_salary_payment": [
        "generate_payment_file",
        "confirm_action",
        "initiate_payment",
        "verify_payment_status",
    ],
    "send_payslips": [
        "generate_payslips",
        "confirm_recipients",
        "send_emails",
        "send_notifications",
        "verify_delivery",
    ],
    "import_from_hris": [
        "fetch_employees",
        "preview_mapping",
        "confirm_import",
        "create_records",
        "verify_import",
    ],
    "myinfo_onboarding": [
        "initiate_consent",
        "fetch_myinfo_data",
        "map_to_employee",
        "confirm_data",
        "create_employee",
    ],
}


# Singleton
_orchestrator: Optional[SagaOrchestrator] = None


def get_saga_orchestrator() -> SagaOrchestrator:
    """Get or create the global saga orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SagaOrchestrator()
    return _orchestrator
