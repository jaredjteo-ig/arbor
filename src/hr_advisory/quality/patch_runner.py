"""PatchRunner -- automated test and rollback for instruction patches.

NOTE: The specialist agents have been replaced by the Delegate engine.
PatchRunner's mechanism of patching individual specialist system prompts
no longer works. The evaluation and pattern detection pipeline still
functions, but patch testing/deployment will raise ValueError until
PatchRunner is redesigned to target the Delegate's system prompt or
tool descriptions.

Usage:
    runner = PatchRunner()
    result = runner.test_pre_approval(patch_dict)  # raises ValueError
    result = runner.run_regression(patch_dict)      # raises ValueError
"""

from __future__ import annotations

import importlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from hr_advisory.models.qa import PatchStatus, TestRunType
from hr_advisory.quality.adversarial_runner import (
    ADVERSARIAL_SCENARIOS,
    AdversarialRunner,
    RunSummary,
)

logger = logging.getLogger(__name__)

# Minimum score improvement required for pre-approval
MIN_IMPROVEMENT_THRESHOLD = 0.3

# Maximum category score drop allowed during regression before rollback
MAX_REGRESSION_DROP = 0.3

# Map from agent identifiers to their module paths and class names.
# The specialist agents have been replaced by the Delegate engine.
# This map is empty — PatchRunner will raise ValueError for any target_agent.
_AGENT_MODULE_MAP: Dict[str, tuple[str, str]] = {}


class PatchRunner:
    """Tests instruction patches before/after deployment.

    Pre-approval testing is IN-MEMORY only -- does not modify source files.
    Post-deployment regression modifies the actual specialist source file
    (QA-LEARNED RULES section) and rolls back automatically on regression.
    """

    def test_pre_approval(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-approval testing: run evidence scenarios with patched prompt in-memory.

        1. Validate patch dict
        2. Get evidence scenario IDs from patch["evidence_ids"]
        3. Find matching scenarios from ADVERSARIAL_SCENARIOS
        4. Run baseline (without patch)
        5. Inject patch in-memory and re-run
        6. Compare before/after scores
        7. If avg score improves >= 0.3: recommend ready_for_approval
        8. If no improvement: recommend rejected

        Args:
            patch: Dict with InstructionPatch fields from MutationEngine.

        Returns:
            PatchTestResult dict with run_type, scores, delta, status recommendation.

        Raises:
            ValueError: If patch is missing required fields.
        """
        self._validate_patch(patch)

        evidence_ids = patch["evidence_ids"]
        target_agent = patch["target_agent"]
        new_text = patch["new_text"]

        # Find matching scenarios from ADVERSARIAL_SCENARIOS by evidence_ids
        # Evidence IDs map to scenario indices; we select scenarios that match
        scenarios = self._find_evidence_scenarios(evidence_ids)

        if not scenarios:
            logger.warning(
                "No matching adversarial scenarios found for evidence_ids=%s. "
                "Using first scenario from each category as fallback.",
                evidence_ids,
            )
            scenarios = self._get_fallback_scenarios(len(evidence_ids))

        # Step 1: Run baseline (without patch)
        runner = AdversarialRunner()
        baseline_summary = runner._run_scenarios(scenarios)

        # Step 2: Inject patch in-memory and re-run
        cleanup = self._inject_patch_in_memory(target_agent, new_text)
        try:
            patched_runner = AdversarialRunner()
            patched_summary = patched_runner._run_scenarios(scenarios)
        finally:
            cleanup()

        # Step 3: Compare scores
        score_before = baseline_summary.avg_overall_score
        score_after = patched_summary.avg_overall_score
        score_delta = score_after - score_before

        if score_delta >= MIN_IMPROVEMENT_THRESHOLD:
            status_recommendation = PatchStatus.READY_FOR_APPROVAL
            logger.info(
                "Pre-approval test PASSED for agent=%s: delta=%.2f (%.2f -> %.2f)",
                target_agent,
                score_delta,
                score_before,
                score_after,
            )
        else:
            status_recommendation = PatchStatus.REJECTED
            logger.info(
                "Pre-approval test FAILED for agent=%s: delta=%.2f (%.2f -> %.2f), "
                "below threshold %.2f",
                target_agent,
                score_delta,
                score_before,
                score_after,
                MIN_IMPROVEMENT_THRESHOLD,
            )

        result: Dict[str, Any] = {
            "run_type": TestRunType.PRE_PATCH,
            "scenarios_run": baseline_summary.scenarios_run,
            "scenarios_passed": patched_summary.scenarios_passed,
            "scenarios_failed": patched_summary.scenarios_failed,
            "avg_score_before": float(score_before),
            "avg_score_after": float(score_after),
            "score_delta": float(score_delta),
            "status_recommendation": status_recommendation,
            "run_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        if status_recommendation == PatchStatus.REJECTED:
            result["rationale"] = (
                f"Score improvement of {score_delta:.2f} is below the required "
                f"threshold of {MIN_IMPROVEMENT_THRESHOLD:.2f}. "
                f"Before: {score_before:.2f}, After: {score_after:.2f}."
            )

        return result

    def run_regression(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Post-deployment regression: run full 64-scenario suite.

        1. Validate patch is in approved status
        2. Run full baseline (before applying patch)
        3. Apply patch to source file
        4. Run full regression suite
        5. If any category avg drops > 0.3 below baseline: auto-rollback
        6. If no regression: recommend deployed

        Args:
            patch: Dict with InstructionPatch fields.

        Returns:
            PatchTestResult dict with run_type, scores, delta, rollback info.

        Raises:
            ValueError: If patch is not in approved status.
        """
        if patch.get("status") != PatchStatus.APPROVED:
            raise ValueError(
                f"run_regression requires patch in 'approved' status, "
                f"got '{patch.get('status')}'. Only approved patches can be "
                f"regression-tested for deployment."
            )

        target_agent = patch["target_agent"]
        new_text = patch["new_text"]

        # Step 1: Run full baseline
        baseline_runner = AdversarialRunner()
        baseline_summary = baseline_runner.run_full()

        # Step 2: Apply patch to source
        old_text = self._apply_patch_to_source(target_agent, new_text)

        # Step 3: Run regression suite
        try:
            regression_runner = AdversarialRunner()
            regression_summary = regression_runner.run_full()
        except Exception as exc:
            # On any failure during regression, rollback immediately
            logger.error(
                "Regression suite failed for agent=%s, rolling back: %s",
                target_agent,
                exc,
                exc_info=True,
            )
            self._rollback_patch(target_agent, old_text)
            return {
                "run_type": TestRunType.REGRESSION,
                "scenarios_run": 0,
                "scenarios_passed": 0,
                "scenarios_failed": 0,
                "avg_score_before": baseline_summary.avg_overall_score,
                "avg_score_after": 0.0,
                "score_delta": 0.0,
                "status_recommendation": PatchStatus.ROLLED_BACK,
                "rolled_back": True,
                "rollback_reason": f"Regression suite error: {exc}",
                "run_at": datetime.now(tz=timezone.utc).isoformat(),
            }

        # Step 4: Check for category regressions
        regressed_categories = self._check_category_regression(baseline_summary, regression_summary)

        score_before = baseline_summary.avg_overall_score
        score_after = regression_summary.avg_overall_score
        score_delta = score_after - score_before

        if regressed_categories:
            # Auto-rollback
            logger.warning(
                "Regression detected in categories %s for agent=%s, rolling back. " "Drops: %s",
                list(regressed_categories.keys()),
                target_agent,
                regressed_categories,
            )
            self._rollback_patch(target_agent, old_text)

            return {
                "run_type": TestRunType.REGRESSION,
                "scenarios_run": regression_summary.scenarios_run,
                "scenarios_passed": regression_summary.scenarios_passed,
                "scenarios_failed": regression_summary.scenarios_failed,
                "avg_score_before": float(score_before),
                "avg_score_after": float(score_after),
                "score_delta": float(score_delta),
                "status_recommendation": PatchStatus.ROLLED_BACK,
                "rolled_back": True,
                "regressed_categories": regressed_categories,
                "rollback_reason": (
                    f"Categories regressed beyond threshold: " f"{regressed_categories}"
                ),
                "run_at": datetime.now(tz=timezone.utc).isoformat(),
            }

        # No regression: deployed
        logger.info(
            "Regression test PASSED for agent=%s: delta=%.2f (%.2f -> %.2f)",
            target_agent,
            score_delta,
            score_before,
            score_after,
        )

        return {
            "run_type": TestRunType.REGRESSION,
            "scenarios_run": regression_summary.scenarios_run,
            "scenarios_passed": regression_summary.scenarios_passed,
            "scenarios_failed": regression_summary.scenarios_failed,
            "avg_score_before": float(score_before),
            "avg_score_after": float(score_after),
            "score_delta": float(score_delta),
            "status_recommendation": PatchStatus.DEPLOYED,
            "rolled_back": False,
            "run_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _validate_patch(self, patch: Dict[str, Any]) -> None:
        """Validate that a patch dict has all required fields.

        Raises:
            ValueError: With a clear message identifying the missing field.
        """
        if not patch.get("target_agent"):
            raise ValueError(
                "patch must contain 'target_agent' -- cannot test a patch "
                "without knowing which agent to target"
            )
        if not patch.get("new_text"):
            raise ValueError(
                "patch must contain 'new_text' -- cannot test a patch "
                "without the rule text to inject"
            )
        if not patch.get("evidence_ids"):
            raise ValueError(
                "patch must contain non-empty 'evidence_ids' -- cannot run "
                "pre-approval testing without knowing which scenarios to test"
            )

    def _find_evidence_scenarios(self, evidence_ids: list) -> list[Dict[str, Any]]:
        """Find adversarial scenarios matching evidence IDs.

        Evidence IDs from evaluations are mapped to scenario IDs by using
        the scenario index within each category. This is a best-effort
        mapping since evidence_ids come from QA evaluations, not directly
        from adversarial scenarios.

        Returns a flat list of scenario dicts from ADVERSARIAL_SCENARIOS.
        """
        all_scenarios = []
        for category, items in ADVERSARIAL_SCENARIOS.items():
            all_scenarios.extend(items)

        # Try to find scenarios by index (evidence IDs are evaluation IDs,
        # we use modular indexing into the scenario list)
        matched = []
        for eid in evidence_ids:
            idx = (eid - 1) % len(all_scenarios)
            matched.append(all_scenarios[idx])

        return matched

    def _get_fallback_scenarios(self, count: int) -> list[Dict[str, Any]]:
        """Get fallback scenarios if evidence mapping fails.

        Returns one scenario per category, up to the requested count.
        """
        scenarios = []
        for category, items in ADVERSARIAL_SCENARIOS.items():
            if items:
                scenarios.append(items[0])
            if len(scenarios) >= count:
                break
        return scenarios

    def _inject_patch_in_memory(self, agent_name: str, patch_text: str) -> callable:
        """Temporarily inject patch text into an agent's system prompt in-memory.

        Replaces the agent class's _generate_system_prompt method with a
        wrapper that appends the patch text to the QA-LEARNED RULES section.

        Args:
            agent_name: The target agent identifier (e.g. "employment_act_specialist").
            patch_text: The rule text to inject.

        Returns:
            A cleanup function that restores the original prompt method.
        """
        agent_cls = self._resolve_agent_class(agent_name)
        original_method = agent_cls._generate_system_prompt

        def patched_prompt(self_agent):
            original_prompt = original_method(self_agent)
            # Append the patch text after the QA-LEARNED RULES section
            if "QA-LEARNED RULES" in original_prompt:
                return original_prompt + f"- {patch_text}\n"
            else:
                return original_prompt + (
                    "\n== QA-LEARNED RULES ==\n"
                    "(Rules added by the QA feedback pipeline. "
                    "Do not modify manually.)\n"
                    f"- {patch_text}\n"
                )

        agent_cls._generate_system_prompt = patched_prompt

        def cleanup():
            agent_cls._generate_system_prompt = original_method

        return cleanup

    def _resolve_agent_class(self, agent_name: str):
        """Resolve an agent name to its class.

        Args:
            agent_name: The agent identifier (e.g. "employment_act_specialist").

        Returns:
            The agent class.

        Raises:
            ValueError: If the agent name is not recognized.
        """
        if agent_name not in _AGENT_MODULE_MAP:
            raise ValueError(
                f"Unknown agent '{agent_name}'. Known agents: "
                f"{sorted(_AGENT_MODULE_MAP.keys())}"
            )

        module_path, class_name = _AGENT_MODULE_MAP[agent_name]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def _apply_patch_to_source(self, agent_name: str, patch_text: str) -> str:
        """Append patch text to agent's QA-LEARNED RULES section in source file.

        Args:
            agent_name: The target agent identifier.
            patch_text: The rule text to append.

        Returns:
            The old file content (for rollback).

        Raises:
            ValueError: If the agent name is not recognized.
            FileNotFoundError: If the agent source file cannot be found.
        """
        source_path = self._get_agent_source_path(agent_name)

        with open(source_path, "r") as f:
            old_content = f.read()

        # Find the QA-LEARNED RULES section and append the patch text
        marker = "(Rules added by the QA feedback pipeline. Do not modify manually.)"
        if marker not in old_content:
            raise ValueError(
                f"Agent source file {source_path} does not contain the "
                f"QA-LEARNED RULES marker. Cannot apply patch."
            )

        # Find the line with the marker and the closing quote/paren after it
        # We append the new rule line after the marker line
        lines = old_content.split("\n")
        new_lines = []
        inserted = False

        for line in lines:
            new_lines.append(line)
            if not inserted and marker in line:
                # Detect the indentation and quote style from this line
                stripped = line.lstrip()
                indent = line[: len(line) - len(stripped)]
                # Add the new rule line with matching indentation
                new_lines.append(f'{indent}"- {patch_text}\\n"')
                inserted = True

        if not inserted:
            raise ValueError(
                f"Failed to insert patch text into {source_path}. "
                f"QA-LEARNED RULES marker was found but insertion failed."
            )

        new_content = "\n".join(new_lines)

        with open(source_path, "w") as f:
            f.write(new_content)

        logger.info(
            "Applied patch to source file %s for agent=%s",
            source_path,
            agent_name,
        )

        return old_content

    def _rollback_patch(
        self,
        agent_name: str,
        old_text: str,
        _source_path: Optional[str] = None,
    ) -> None:
        """Restore previous prompt text by writing old_text back to source file.

        Args:
            agent_name: The target agent identifier.
            old_text: The previous file content to restore.
            _source_path: Override source path (used in tests with tmp_path).
        """
        if _source_path is not None:
            source_path = _source_path
        else:
            source_path = self._get_agent_source_path(agent_name)

        with open(source_path, "w") as f:
            f.write(old_text)

        logger.info(
            "Rolled back patch for agent=%s, restored source file %s",
            agent_name,
            source_path,
        )

    def _get_agent_source_path(self, agent_name: str) -> str:
        """Get the filesystem path of the agent's source file.

        Args:
            agent_name: The agent identifier.

        Returns:
            Absolute path to the agent's .py source file.

        Raises:
            ValueError: If the agent name is not recognized.
        """
        if agent_name not in _AGENT_MODULE_MAP:
            raise ValueError(
                f"Unknown agent '{agent_name}'. Known agents: "
                f"{sorted(_AGENT_MODULE_MAP.keys())}"
            )

        module_path, _ = _AGENT_MODULE_MAP[agent_name]
        module = importlib.import_module(module_path)
        source_file = module.__file__

        if source_file is None:
            raise FileNotFoundError(
                f"Cannot determine source file for agent '{agent_name}' "
                f"(module {module_path}). The module may be a namespace package."
            )

        return source_file

    def _check_category_regression(
        self,
        baseline: RunSummary,
        regression: RunSummary,
    ) -> Dict[str, float]:
        """Check if any category average dropped more than the threshold.

        Args:
            baseline: RunSummary from the baseline run.
            regression: RunSummary from the post-patch regression run.

        Returns:
            Dict mapping category names to their drop amounts (only categories
            that dropped more than MAX_REGRESSION_DROP).
        """
        regressed: Dict[str, float] = {}

        for category, baseline_avg in baseline.per_category_avg.items():
            regression_avg = regression.per_category_avg.get(category, 0.0)
            drop = baseline_avg - regression_avg

            if drop > MAX_REGRESSION_DROP:
                regressed[category] = round(drop, 3)
                logger.warning(
                    "Category '%s' regressed: %.2f -> %.2f (drop=%.2f, " "threshold=%.2f)",
                    category,
                    baseline_avg,
                    regression_avg,
                    drop,
                    MAX_REGRESSION_DROP,
                )

        return regressed
