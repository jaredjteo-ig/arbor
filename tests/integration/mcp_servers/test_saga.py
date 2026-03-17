"""Integration tests for SagaOrchestrator (multi-step MCP tool orchestration).

Tests:
- Start a saga with named steps
- Advance through steps with start_step / complete_step
- Fail at step N and resume from step N
- Cancel an in-progress saga
- Saga templates match expected step definitions
- Serialization via to_dict()
- Context sharing between steps
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.saga import (
    SAGA_TEMPLATES,
    SagaExecution,
    SagaOrchestrator,
    SagaStatus,
    SagaStep,
    StepStatus,
)

from .conftest import TENANT_A, TENANT_B


# ---------------------------------------------------------------------------
# Start saga
# ---------------------------------------------------------------------------


class TestStartSaga:
    """Creating and starting a new saga."""

    def test_start_creates_saga_in_progress(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(
            tenant_id=TENANT_A,
            saga_type="submit_cpf",
            step_names=["validate", "generate", "submit"],
        )
        assert saga.status == SagaStatus.IN_PROGRESS
        assert saga.tenant_id == TENANT_A
        assert saga.saga_type == "submit_cpf"
        assert saga.total_steps == 3
        assert saga.completed_steps == 0
        assert saga.current_step_index == 0

    def test_start_creates_pending_steps(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(
            tenant_id=TENANT_A,
            saga_type="submit_cpf",
            step_names=["validate", "generate", "submit"],
        )
        for step in saga.steps:
            assert step.status == StepStatus.PENDING
            assert step.started_at is None

    def test_start_with_context(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(
            tenant_id=TENANT_A,
            saga_type="submit_cpf",
            step_names=["validate", "submit"],
            context={"payroll_run_id": "run_123", "month": "2026-03"},
        )
        assert saga.context["payroll_run_id"] == "run_123"
        assert saga.context["month"] == "2026-03"

    def test_current_step_points_to_first(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(
            tenant_id=TENANT_A,
            saga_type="submit_cpf",
            step_names=["validate", "submit"],
        )
        assert saga.current_step is not None
        assert saga.current_step.name == "validate"

    def test_start_assigns_unique_id(self, orchestrator: SagaOrchestrator):
        s1 = orchestrator.start_saga(TENANT_A, "submit_cpf", ["a", "b"])
        s2 = orchestrator.start_saga(TENANT_A, "submit_cpf", ["a", "b"])
        assert s1.id != s2.id

    def test_start_sets_started_at(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "submit_cpf", ["a"])
        assert saga.started_at is not None
        assert saga.completed_at is None


# ---------------------------------------------------------------------------
# Step advancement
# ---------------------------------------------------------------------------


class TestStepAdvancement:
    """Advancing through saga steps."""

    def test_start_step_marks_in_progress(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["step_1", "step_2"])
        step = orchestrator.start_step(saga.id)
        assert step.status == StepStatus.IN_PROGRESS
        assert step.started_at is not None
        assert step.name == "step_1"

    def test_complete_step_marks_completed(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["step_1", "step_2"])
        orchestrator.start_step(saga.id)
        next_step = orchestrator.complete_step(saga.id, {"validated": True})

        assert saga.steps[0].status == StepStatus.COMPLETED
        assert saga.steps[0].result_summary == {"validated": True}
        assert saga.steps[0].completed_at is not None
        assert next_step is not None
        assert next_step.name == "step_2"

    def test_complete_final_step_finishes_saga(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["only_step"])
        orchestrator.start_step(saga.id)
        result = orchestrator.complete_step(saga.id, {"done": True})

        assert result is None  # No more steps
        assert saga.status == SagaStatus.COMPLETED
        assert saga.completed_at is not None

    def test_completed_steps_count_increments(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1", "s2", "s3"])
        assert saga.completed_steps == 0

        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)
        assert saga.completed_steps == 1

        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)
        assert saga.completed_steps == 2

    def test_current_step_index_advances(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1", "s2", "s3"])
        assert saga.current_step_index == 0

        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)
        assert saga.current_step_index == 1
        assert saga.current_step.name == "s2"

    def test_start_step_on_completed_saga_raises(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["only_step"])
        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)

        with pytest.raises(ValueError, match="No more steps"):
            orchestrator.start_step(saga.id)


# ---------------------------------------------------------------------------
# Failure and recovery
# ---------------------------------------------------------------------------


class TestFailureAndRecovery:
    """Failing at step N and resuming from step N."""

    def test_fail_step_marks_saga_failed(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1", "s2", "s3"])
        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)
        orchestrator.start_step(saga.id)
        orchestrator.fail_step(saga.id, "CPF Board API timeout")

        assert saga.status == SagaStatus.FAILED
        assert saga.error_detail == "CPF Board API timeout"
        assert saga.steps[1].status == StepStatus.FAILED
        assert saga.steps[1].error == "CPF Board API timeout"
        assert saga.current_step_index == 1  # Still points to failed step

    def test_resume_from_failed_step(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1", "s2", "s3"])
        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)
        orchestrator.start_step(saga.id)
        orchestrator.fail_step(saga.id, "timeout")

        resumed = orchestrator.resume_saga(saga.id)
        assert resumed.status == SagaStatus.IN_PROGRESS
        assert resumed.error_detail is None
        assert resumed.current_step.name == "s2"
        assert resumed.current_step.status == StepStatus.PENDING

    def test_resume_non_failed_saga_raises(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1"])
        with pytest.raises(ValueError, match="not failed"):
            orchestrator.resume_saga(saga.id)

    def test_resume_and_complete_remaining_steps(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1", "s2", "s3"])

        # Complete step 1
        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)

        # Fail step 2
        orchestrator.start_step(saga.id)
        orchestrator.fail_step(saga.id, "error")

        # Resume and complete step 2
        orchestrator.resume_saga(saga.id)
        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id, {"retried": True})

        # Complete step 3
        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id)

        assert saga.status == SagaStatus.COMPLETED
        assert saga.completed_steps == 3


# ---------------------------------------------------------------------------
# Cancel saga
# ---------------------------------------------------------------------------


class TestCancelSaga:
    """Cancelling an in-progress saga."""

    def test_cancel_in_progress_saga(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1", "s2"])
        orchestrator.cancel_saga(saga.id)
        assert saga.status == SagaStatus.CANCELLED
        assert saga.completed_at is not None

    def test_cancel_failed_saga(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1"])
        orchestrator.start_step(saga.id)
        orchestrator.fail_step(saga.id, "error")
        orchestrator.cancel_saga(saga.id)
        assert saga.status == SagaStatus.CANCELLED

    def test_cancel_unknown_saga_raises(self, orchestrator: SagaOrchestrator):
        with pytest.raises(ValueError, match="Unknown saga"):
            orchestrator.cancel_saga("nonexistent-id")


# ---------------------------------------------------------------------------
# Awaiting approval
# ---------------------------------------------------------------------------


class TestAwaitingApproval:
    """Saga paused for human confirmation."""

    def test_set_awaiting_approval(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["confirm", "submit"])
        orchestrator.set_awaiting_approval(saga.id)
        assert saga.status == SagaStatus.AWAITING_APPROVAL


# ---------------------------------------------------------------------------
# Context sharing
# ---------------------------------------------------------------------------


class TestContextSharing:
    """Shared context between saga steps."""

    def test_update_context(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1", "s2"])
        orchestrator.update_context(saga.id, employees=47, total_cpf=38450.00)
        assert saga.context["employees"] == 47
        assert saga.context["total_cpf"] == 38450.00

    def test_update_context_preserves_existing(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(
            TENANT_A,
            "test",
            ["s1"],
            context={"month": "2026-03"},
        )
        orchestrator.update_context(saga.id, total=1000)
        assert saga.context["month"] == "2026-03"
        assert saga.context["total"] == 1000


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSagaSerialization:
    """to_dict() for API responses."""

    def test_saga_to_dict(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "submit_cpf", ["validate", "submit"])
        d = saga.to_dict()
        assert d["id"] == saga.id
        assert d["tenant_id"] == TENANT_A
        assert d["saga_type"] == "submit_cpf"
        assert d["status"] == "in_progress"
        assert d["total_steps"] == 2
        assert d["completed_steps"] == 0
        assert len(d["steps"]) == 2
        assert d["steps"][0]["name"] == "validate"
        assert d["steps"][0]["status"] == "pending"

    def test_step_to_dict(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1"])
        orchestrator.start_step(saga.id)
        orchestrator.complete_step(saga.id, {"count": 5})
        d = saga.steps[0].to_dict()
        assert d["name"] == "s1"
        assert d["status"] == "completed"
        assert d["result_summary"] == {"count": 5}
        assert d["started_at"] is not None
        assert d["completed_at"] is not None


# ---------------------------------------------------------------------------
# Listing and retrieval
# ---------------------------------------------------------------------------


class TestListSagas:
    """Listing and filtering sagas."""

    def test_get_saga_by_id(self, orchestrator: SagaOrchestrator):
        saga = orchestrator.start_saga(TENANT_A, "test", ["s1"])
        fetched = orchestrator.get_saga(saga.id)
        assert fetched is not None
        assert fetched.id == saga.id

    def test_get_unknown_saga_returns_none(self, orchestrator: SagaOrchestrator):
        assert orchestrator.get_saga("nonexistent") is None

    def test_list_all_sagas(self, orchestrator: SagaOrchestrator):
        orchestrator.start_saga(TENANT_A, "test_a", ["s1"])
        orchestrator.start_saga(TENANT_B, "test_b", ["s1"])
        sagas = orchestrator.list_sagas()
        assert len(sagas) == 2

    def test_list_by_tenant(self, orchestrator: SagaOrchestrator):
        orchestrator.start_saga(TENANT_A, "test_a", ["s1"])
        orchestrator.start_saga(TENANT_B, "test_b", ["s1"])
        sagas = orchestrator.list_sagas(tenant_id=TENANT_A)
        assert len(sagas) == 1
        assert sagas[0].tenant_id == TENANT_A

    def test_list_by_status(self, orchestrator: SagaOrchestrator):
        s1 = orchestrator.start_saga(TENANT_A, "test_a", ["s1"])
        orchestrator.start_saga(TENANT_A, "test_b", ["s1"])
        orchestrator.start_step(s1.id)
        orchestrator.fail_step(s1.id, "err")

        failed = orchestrator.list_sagas(status=SagaStatus.FAILED)
        assert len(failed) == 1
        in_progress = orchestrator.list_sagas(status=SagaStatus.IN_PROGRESS)
        assert len(in_progress) == 1

    def test_list_limit(self, orchestrator: SagaOrchestrator):
        for i in range(5):
            orchestrator.start_saga(TENANT_A, f"test_{i}", ["s1"])
        sagas = orchestrator.list_sagas(limit=3)
        assert len(sagas) == 3


# ---------------------------------------------------------------------------
# Saga templates
# ---------------------------------------------------------------------------


class TestSagaTemplates:
    """Pre-defined saga templates have correct step names."""

    def test_submit_cpf_template(self):
        steps = SAGA_TEMPLATES["submit_cpf"]
        assert steps[0] == "validate_readiness"
        assert "submit_to_cpf" in steps
        assert "verify_acknowledgement" in steps
        assert len(steps) == 5

    def test_file_ir8a_template(self):
        steps = SAGA_TEMPLATES["file_ir8a"]
        assert "generate_ir8a_data" in steps
        assert "submit_to_iras" in steps

    def test_file_ir21_template(self):
        steps = SAGA_TEMPLATES["file_ir21"]
        assert "generate_ir21_data" in steps
        assert "submit_to_iras" in steps

    def test_post_payroll_to_accounting_template(self):
        steps = SAGA_TEMPLATES["post_payroll_to_accounting"]
        assert "fetch_chart_of_accounts" in steps
        assert "post_journal" in steps

    def test_bulk_salary_payment_template(self):
        steps = SAGA_TEMPLATES["bulk_salary_payment"]
        assert "generate_payment_file" in steps
        assert "verify_payment_status" in steps

    def test_send_payslips_template(self):
        steps = SAGA_TEMPLATES["send_payslips"]
        assert "generate_payslips" in steps
        assert "send_emails" in steps
        assert "verify_delivery" in steps

    def test_import_from_hris_template(self):
        steps = SAGA_TEMPLATES["import_from_hris"]
        assert "fetch_employees" in steps
        assert "create_records" in steps

    def test_myinfo_onboarding_template(self):
        steps = SAGA_TEMPLATES["myinfo_onboarding"]
        assert "initiate_consent" in steps
        assert "fetch_myinfo_data" in steps
        assert "create_employee" in steps

    def test_all_templates_have_confirm_action(self):
        """Most templates include a human confirmation step."""
        templates_with_confirm = [
            "submit_cpf",
            "file_ir8a",
            "file_ir21",
            "post_payroll_to_accounting",
            "bulk_salary_payment",
        ]
        for template_name in templates_with_confirm:
            steps = SAGA_TEMPLATES[template_name]
            assert (
                "confirm_action" in steps
            ), f"Template '{template_name}' is missing 'confirm_action' step"
