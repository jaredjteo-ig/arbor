"""Unit tests for PatchRunner -- automated test and rollback for instruction patches.

Tests:
1. test_pre_approval_improving_patch_becomes_ready -- improving scores -> ready_for_approval
2. test_pre_approval_non_improving_patch_rejected -- no improvement -> rejected
3. test_regression_no_drop_deploys -- no category drops -> deployed
4. test_regression_with_drop_rolls_back -- category drops > 0.3 -> auto-rollback
5. test_rollback_restores_old_text -- source file restored after rollback
6. test_inject_patch_in_memory_cleanup -- in-memory injection cleaned up
7. test_approve_requires_ready_for_approval -- API rejects approve for "proposed" status
8. test_test_run_result_structure -- returned dict matches PatchTestResult fields
"""

from __future__ import annotations

import inspect
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from hr_advisory.models.qa import (
    PatchStatus,
    TargetAgent,
    TestRunType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_patch_dict(
    *,
    patch_id: int = 1,
    target_agent: str = TargetAgent.EMPLOYMENT_ACT,
    new_text: str = "RULE: Always cite EA s.27 for salary deduction caps.",
    evidence_ids: list | None = None,
    status: str = PatchStatus.PROPOSED,
) -> Dict[str, Any]:
    """Build a patch dict matching MutationEngine output."""
    return {
        "id": patch_id,
        "target_agent": target_agent,
        "patch_type": "add_rule",
        "old_text": None,
        "new_text": new_text,
        "evidence_count": 3,
        "evidence_ids": evidence_ids or [1, 2, 3],
        "failure_category": "missed_critical_nuance",
        "test_results": None,
        "status": status,
        "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
        "approved_at": None,
        "deployed_at": None,
        "approved_by": None,
    }


def _make_scenario_result(
    scenario_id: str,
    category: str,
    overall_score: float,
    passed: bool = True,
) -> MagicMock:
    """Build a mock ScenarioResult-like object."""
    result = MagicMock()
    result.scenario_id = scenario_id
    result.category = category
    result.overall_score = overall_score
    result.passed = passed
    result.scores = {
        "citation_quality": overall_score,
        "risk_awareness": overall_score,
    }
    result.error = None
    return result


def _make_run_summary(
    per_category_avg: Dict[str, float],
    avg_overall_score: float = 4.0,
    scenarios_run: int = 64,
) -> MagicMock:
    """Build a mock RunSummary."""
    summary = MagicMock()
    summary.per_category_avg = per_category_avg
    summary.avg_overall_score = avg_overall_score
    summary.scenarios_run = scenarios_run
    summary.total_scenarios = scenarios_run
    summary.scenarios_passed = scenarios_run
    summary.scenarios_failed = 0
    summary.scenarios_errored = 0
    return summary


# ---------------------------------------------------------------------------
# 1. Pre-approval: improving patch becomes ready_for_approval
# ---------------------------------------------------------------------------


class TestPreApprovalImprovingPatch:
    """When pre-approval testing shows score improvement >= 0.3, patch moves to ready_for_approval."""

    @patch("hr_advisory.quality.patch_runner.AdversarialRunner")
    def test_pre_approval_improving_patch_becomes_ready(self, MockRunner) -> None:
        """An improving patch should move to ready_for_approval status."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict(evidence_ids=[1, 2, 3])

        # First run (baseline, without patch): avg score 3.0
        baseline_summary = _make_run_summary(
            per_category_avg={"employment_act": 3.0},
            avg_overall_score=3.0,
            scenarios_run=3,
        )
        # Second run (with patch injected): avg score 3.5 (improvement of 0.5 >= 0.3)
        patched_summary = _make_run_summary(
            per_category_avg={"employment_act": 3.5},
            avg_overall_score=3.5,
            scenarios_run=3,
        )

        runner_instance = MockRunner.return_value
        runner_instance._run_scenarios.side_effect = [baseline_summary, patched_summary]

        pr = PatchRunner()
        result = pr.test_pre_approval(patch_dict)

        assert result["run_type"] == TestRunType.PRE_PATCH
        assert result["status_recommendation"] == PatchStatus.READY_FOR_APPROVAL
        assert result["score_delta"] >= 0.3


# ---------------------------------------------------------------------------
# 2. Pre-approval: non-improving patch rejected
# ---------------------------------------------------------------------------


class TestPreApprovalNonImprovingPatch:
    """When pre-approval testing shows no improvement, patch is rejected."""

    @patch("hr_advisory.quality.patch_runner.AdversarialRunner")
    def test_pre_approval_non_improving_patch_rejected(self, MockRunner) -> None:
        """A patch that does not improve scores should be rejected."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict()

        # Both runs return same score -- no improvement
        baseline_summary = _make_run_summary(
            per_category_avg={"employment_act": 3.0},
            avg_overall_score=3.0,
            scenarios_run=3,
        )
        patched_summary = _make_run_summary(
            per_category_avg={"employment_act": 3.1},
            avg_overall_score=3.1,
            scenarios_run=3,
        )

        runner_instance = MockRunner.return_value
        runner_instance._run_scenarios.side_effect = [baseline_summary, patched_summary]

        pr = PatchRunner()
        result = pr.test_pre_approval(patch_dict)

        assert result["run_type"] == TestRunType.PRE_PATCH
        assert result["status_recommendation"] == PatchStatus.REJECTED
        assert result["score_delta"] < 0.3
        assert "rationale" in result


# ---------------------------------------------------------------------------
# 3. Regression: no category drop -> deployed
# ---------------------------------------------------------------------------


class TestRegressionNoDropDeploys:
    """Post-deployment regression with no category drops results in 'deployed' status."""

    @patch("hr_advisory.quality.patch_runner.PatchRunner._apply_patch_to_source")
    @patch("hr_advisory.quality.patch_runner.AdversarialRunner")
    def test_regression_no_drop_deploys(self, MockRunner, mock_apply) -> None:
        """When no category avg drops > 0.3 below baseline, patch is deployed."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict(status=PatchStatus.APPROVED)
        mock_apply.return_value = "old prompt text"

        # Baseline before patch
        baseline_summary = _make_run_summary(
            per_category_avg={
                "employment_act": 4.0,
                "cpf": 3.8,
                "foreign_manpower": 3.5,
                "fair_employment": 4.0,
                "tax": 3.9,
                "wsh": 3.7,
                "pdpa": 4.0,
                "cross_domain": 3.6,
            },
            avg_overall_score=3.8,
        )
        # Post-patch regression -- stable scores, minor improvements
        regression_summary = _make_run_summary(
            per_category_avg={
                "employment_act": 4.2,
                "cpf": 3.7,
                "foreign_manpower": 3.6,
                "fair_employment": 4.0,
                "tax": 3.9,
                "wsh": 3.7,
                "pdpa": 4.1,
                "cross_domain": 3.5,
            },
            avg_overall_score=3.8,
        )

        runner_instance = MockRunner.return_value
        runner_instance.run_full.side_effect = [baseline_summary, regression_summary]

        pr = PatchRunner()
        result = pr.run_regression(patch_dict)

        assert result["run_type"] == TestRunType.REGRESSION
        assert result["status_recommendation"] == PatchStatus.DEPLOYED
        assert result.get("rolled_back") is not True


# ---------------------------------------------------------------------------
# 4. Regression: category drop -> auto-rollback
# ---------------------------------------------------------------------------


class TestRegressionWithDropRollsBack:
    """Post-deployment regression with a category drop > 0.3 triggers auto-rollback."""

    @patch("hr_advisory.quality.patch_runner.PatchRunner._rollback_patch")
    @patch("hr_advisory.quality.patch_runner.PatchRunner._apply_patch_to_source")
    @patch("hr_advisory.quality.patch_runner.AdversarialRunner")
    def test_regression_with_drop_rolls_back(self, MockRunner, mock_apply, mock_rollback) -> None:
        """When a category avg drops > 0.3 below baseline, patch is rolled back."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict(status=PatchStatus.APPROVED)
        old_text = "old prompt text before patch"
        mock_apply.return_value = old_text

        # Baseline
        baseline_summary = _make_run_summary(
            per_category_avg={
                "employment_act": 4.0,
                "cpf": 4.0,
                "foreign_manpower": 3.5,
                "fair_employment": 4.0,
                "tax": 3.9,
                "wsh": 3.7,
                "pdpa": 4.0,
                "cross_domain": 3.6,
            },
            avg_overall_score=3.8,
        )
        # Post-patch regression -- cpf dropped significantly (4.0 -> 3.2 = -0.8)
        regression_summary = _make_run_summary(
            per_category_avg={
                "employment_act": 4.2,
                "cpf": 3.2,  # dropped 0.8 from 4.0
                "foreign_manpower": 3.5,
                "fair_employment": 4.0,
                "tax": 3.9,
                "wsh": 3.7,
                "pdpa": 4.0,
                "cross_domain": 3.6,
            },
            avg_overall_score=3.7,
        )

        runner_instance = MockRunner.return_value
        runner_instance.run_full.side_effect = [baseline_summary, regression_summary]

        pr = PatchRunner()
        result = pr.run_regression(patch_dict)

        assert result["run_type"] == TestRunType.REGRESSION
        assert result["status_recommendation"] == PatchStatus.ROLLED_BACK
        assert result["rolled_back"] is True
        # Rollback must have been called with agent and old text
        mock_rollback.assert_called_once_with(patch_dict["target_agent"], old_text)


# ---------------------------------------------------------------------------
# 5. Rollback restores old text in source file
# ---------------------------------------------------------------------------


class TestRollbackRestoresOldText:
    """Verify that _rollback_patch restores the agent's source file to its previous state."""

    def test_rollback_restores_old_text(self, tmp_path) -> None:
        """After rollback, the source file should contain the old text exactly."""
        from hr_advisory.quality.patch_runner import PatchRunner

        # Create a temp file simulating a specialist source
        original_content = (
            "def _generate_system_prompt(self) -> str:\n"
            "    return (\n"
            '        "You are a Singapore Employment Act specialist.\\n"\n'
            '        "== QA-LEARNED RULES ==\\n"\n'
            '        "(Rules added by the QA feedback pipeline. Do not modify manually.)\\n"\n'
            "    )\n"
        )
        source_file = tmp_path / "employment_act.py"
        source_file.write_text(original_content)

        # Modify the file (simulating a patch being applied)
        modified_content = original_content.replace(
            '"(Rules added by the QA feedback pipeline. Do not modify manually.)\\n"',
            '"(Rules added by the QA feedback pipeline. Do not modify manually.)\\n"\n'
            '        "- RULE: Always cite EA s.27 for salary deduction caps.\\n"',
        )
        source_file.write_text(modified_content)
        assert source_file.read_text() != original_content

        # Now rollback
        pr = PatchRunner()
        pr._rollback_patch(
            agent_name=TargetAgent.EMPLOYMENT_ACT,
            old_text=original_content,
            _source_path=str(source_file),
        )

        # The file should be restored to the original content
        assert source_file.read_text() == original_content


# ---------------------------------------------------------------------------
# 6. In-memory patch injection is cleaned up
# ---------------------------------------------------------------------------


class TestInjectPatchInMemoryCleanup:
    """Verify that _inject_patch_in_memory properly cleans up after use."""

    @patch("hr_advisory.quality.patch_runner.PatchRunner._resolve_agent_class")
    def test_inject_patch_in_memory_cleanup(self, mock_resolve) -> None:
        """After the context manager exits, the agent's prompt should be restored."""
        from hr_advisory.quality.patch_runner import PatchRunner

        # Create a mock agent class with a _generate_system_prompt method
        original_prompt = (
            "You are a specialist.\n"
            "== QA-LEARNED RULES ==\n"
            "(Rules added by the QA feedback pipeline. Do not modify manually.)\n"
        )

        mock_agent_cls = MagicMock()
        mock_agent_instance = MagicMock()
        mock_agent_instance._generate_system_prompt = MagicMock(return_value=original_prompt)
        mock_resolve.return_value = mock_agent_cls

        original_method = mock_agent_cls._generate_system_prompt

        pr = PatchRunner()
        cleanup = pr._inject_patch_in_memory(
            agent_name=TargetAgent.EMPLOYMENT_ACT,
            patch_text="RULE: New rule for testing.",
        )

        # After injection, the prompt method should be replaced
        assert mock_agent_cls._generate_system_prompt != original_method

        # Call cleanup to restore
        cleanup()

        # After cleanup, the original method is restored
        assert mock_agent_cls._generate_system_prompt == original_method


# ---------------------------------------------------------------------------
# 7. Approve requires ready_for_approval status
# ---------------------------------------------------------------------------


class TestApproveRequiresReadyForApproval:
    """API should reject approve for patches still in 'proposed' status."""

    def test_approve_requires_ready_for_approval(self) -> None:
        """POST /patches/{id}/approve should return 400 for 'proposed' patches."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from hr_advisory.api.middleware.auth_middleware import get_current_user
        from hr_advisory.api.routers.qa import _patches, router

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: {
            "sub": 10,
            "email": "admin@example.com",
            "role": "owner",
            "company_id": 1,
            "id": "admin-10",
        }

        # Clear and set up a patch in "proposed" status
        _patches.clear()
        _patches[1] = _make_patch_dict(patch_id=1, status=PatchStatus.PROPOSED)

        client = TestClient(app)
        resp = client.post("/admin/qa/patches/1/approve")

        # Should reject because patch is still "proposed" (not "ready_for_approval")
        assert resp.status_code == 400
        assert "ready_for_approval" in resp.json()["detail"].lower()

        # Cleanup
        _patches.clear()
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 8. PatchTestResult structure matches model fields
# ---------------------------------------------------------------------------


class TestPatchTestResultStructure:
    """Verify that PatchRunner returns dicts matching PatchTestResult fields."""

    @patch("hr_advisory.quality.patch_runner.AdversarialRunner")
    def test_test_run_result_structure(self, MockRunner) -> None:
        """The dict returned by test_pre_approval must have all PatchTestResult fields."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict()

        # Set up improving scores so we get a full result back
        baseline_summary = _make_run_summary(
            per_category_avg={"employment_act": 3.0},
            avg_overall_score=3.0,
            scenarios_run=3,
        )
        patched_summary = _make_run_summary(
            per_category_avg={"employment_act": 4.0},
            avg_overall_score=4.0,
            scenarios_run=3,
        )

        runner_instance = MockRunner.return_value
        runner_instance._run_scenarios.side_effect = [baseline_summary, patched_summary]

        pr = PatchRunner()
        result = pr.test_pre_approval(patch_dict)

        # Verify all PatchTestResult-equivalent fields are present
        required_fields = [
            "run_type",
            "scenarios_run",
            "scenarios_passed",
            "scenarios_failed",
            "avg_score_before",
            "avg_score_after",
            "score_delta",
            "status_recommendation",
        ]
        for field_name in required_fields:
            assert field_name in result, (
                f"Missing field '{field_name}' in test run result. "
                f"Got keys: {sorted(result.keys())}"
            )

        # Validate types
        assert isinstance(result["run_type"], str)
        assert isinstance(result["scenarios_run"], int)
        assert isinstance(result["avg_score_before"], float)
        assert isinstance(result["avg_score_after"], float)
        assert isinstance(result["score_delta"], float)


# ---------------------------------------------------------------------------
# 9. Additional: PatchRunner raises clear errors for invalid inputs
# ---------------------------------------------------------------------------


class TestPatchRunnerValidation:
    """PatchRunner should raise explicit errors, not use silent defaults."""

    def test_pre_approval_raises_on_missing_evidence_ids(self) -> None:
        """Patches without evidence_ids should raise a clear ValueError."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict()
        patch_dict["evidence_ids"] = []

        pr = PatchRunner()
        with pytest.raises(ValueError, match="evidence_ids"):
            pr.test_pre_approval(patch_dict)

    def test_pre_approval_raises_on_missing_target_agent(self) -> None:
        """Patches without target_agent should raise a clear ValueError."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict()
        patch_dict["target_agent"] = ""

        pr = PatchRunner()
        with pytest.raises(ValueError, match="target_agent"):
            pr.test_pre_approval(patch_dict)

    def test_pre_approval_raises_on_missing_new_text(self) -> None:
        """Patches without new_text should raise a clear ValueError."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict()
        patch_dict["new_text"] = ""

        pr = PatchRunner()
        with pytest.raises(ValueError, match="new_text"):
            pr.test_pre_approval(patch_dict)

    def test_regression_raises_on_non_approved_patch(self) -> None:
        """run_regression should raise if patch is not in approved status."""
        from hr_advisory.quality.patch_runner import PatchRunner

        patch_dict = _make_patch_dict(status=PatchStatus.PROPOSED)

        pr = PatchRunner()
        with pytest.raises(ValueError, match="approved"):
            pr.run_regression(patch_dict)
