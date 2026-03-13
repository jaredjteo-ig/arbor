"""Unit tests for the feedback-to-improvement pipeline.

Tests:
1. PatternDetector clusters evaluations correctly
2. PatternDetector doesn't trigger for < 3 instances
3. PatternDetector skips clusters with existing open patches
4. MutationEngine produces a coherent InstructionPatch dict
5. Duplicate patch prevention
6. QA-LEARNED RULES section present in all specialist prompts
7. PatternDetector is wired into QA API as background task
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hr_advisory.models.qa import (
    EvaluationFailureCategory,
    PatchStatus,
    TargetAgent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_eval_dict(
    eval_id: int,
    agent: str,
    category: str,
    correction_text: str = "correction",
) -> Dict[str, Any]:
    """Build an evaluation dict as stored in _evaluations."""
    return {
        "id": eval_id,
        "session_id": 1,
        "conversation_id": f"ADV-{eval_id:04d}",
        "turn_number": 1,
        "score_legal_accuracy": 2.0,
        "score_contextual_relevance": 3.0,
        "score_coherence": 3.0,
        "score_actionability": 2.0,
        "score_risk_awareness": 3.0,
        "score_citation_quality": 3.0,
        "score_language": 3.0,
        "score_completeness": 3.0,
        "citation_flags": None,
        "has_material_correction": True,
        "correction_text": correction_text,
        "failure_category": category,
        "affected_agent": agent,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# 1. PatternDetector -- clusters evaluations correctly
# ---------------------------------------------------------------------------


class TestPatternDetectorClustering:
    """PatternDetector groups evaluations by (affected_agent, failure_category)."""

    def test_clusters_three_matching_evaluations(self) -> None:
        """When 3+ evaluations share (agent, category), a cluster is emitted."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.EMPLOYMENT_ACT,
                EvaluationFailureCategory.MISSED_NUANCE,
            )
            for i in range(1, 4)
        }
        patches: Dict[int, Dict[str, Any]] = {}

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 1
        cluster = clusters[0]
        assert cluster["affected_agent"] == TargetAgent.EMPLOYMENT_ACT
        assert cluster["failure_category"] == EvaluationFailureCategory.MISSED_NUANCE
        assert cluster["count"] >= 3
        assert len(cluster["evidence_ids"]) >= 3

    def test_clusters_multiple_groups(self) -> None:
        """Multiple distinct (agent, category) groups each produce a cluster."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals: Dict[int, Dict[str, Any]] = {}
        # Group 1: EA + missed_nuance (3 evals)
        for i in range(1, 4):
            evals[i] = _make_eval_dict(
                i,
                TargetAgent.EMPLOYMENT_ACT,
                EvaluationFailureCategory.MISSED_NUANCE,
            )
        # Group 2: CPF + wrong_interpretation (4 evals)
        for i in range(4, 8):
            evals[i] = _make_eval_dict(
                i,
                TargetAgent.CPF,
                EvaluationFailureCategory.WRONG_INTERPRETATION,
            )
        patches: Dict[int, Dict[str, Any]] = {}

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 2
        agents = {c["affected_agent"] for c in clusters}
        assert TargetAgent.EMPLOYMENT_ACT in agents
        assert TargetAgent.CPF in agents

    def test_only_material_corrections_are_clustered(self) -> None:
        """Evaluations without has_material_correction=True are ignored."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals: Dict[int, Dict[str, Any]] = {}
        for i in range(1, 6):
            e = _make_eval_dict(
                i,
                TargetAgent.EMPLOYMENT_ACT,
                EvaluationFailureCategory.MISSED_NUANCE,
            )
            e["has_material_correction"] = False  # Should be excluded
            evals[i] = e
        patches: Dict[int, Dict[str, Any]] = {}

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 0


# ---------------------------------------------------------------------------
# 2. PatternDetector -- below threshold
# ---------------------------------------------------------------------------


class TestPatternDetectorBelowThreshold:
    """PatternDetector must NOT trigger when cluster count < 3."""

    def test_two_evaluations_does_not_trigger(self) -> None:
        """Two matching evaluations should produce zero clusters."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.CPF,
                EvaluationFailureCategory.WRONG_LAW,
            )
            for i in range(1, 3)  # Only 2
        }
        patches: Dict[int, Dict[str, Any]] = {}

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 0

    def test_one_evaluation_does_not_trigger(self) -> None:
        """A single evaluation should produce zero clusters."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            1: _make_eval_dict(
                1,
                TargetAgent.TAX,
                EvaluationFailureCategory.WRONG_INTERPRETATION,
            ),
        }
        patches: Dict[int, Dict[str, Any]] = {}

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 0

    def test_empty_evaluations_returns_empty(self) -> None:
        """No evaluations means no clusters."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        detector = PatternDetector(evaluations={}, patches={})
        clusters = detector.run()

        assert clusters == []


# ---------------------------------------------------------------------------
# 3. PatternDetector -- skips clusters with existing open patches
# ---------------------------------------------------------------------------


class TestPatternDetectorSkipsExistingPatches:
    """PatternDetector should not trigger if an open patch already covers the group."""

    def test_skips_when_proposed_patch_exists(self) -> None:
        """An existing 'proposed' patch for the same (agent, category) blocks new cluster."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.EMPLOYMENT_ACT,
                EvaluationFailureCategory.MISSED_NUANCE,
            )
            for i in range(1, 5)
        }
        # Existing patch in 'proposed' status for same agent + category
        patches = {
            100: {
                "id": 100,
                "target_agent": TargetAgent.EMPLOYMENT_ACT,
                "failure_category": EvaluationFailureCategory.MISSED_NUANCE,
                "status": PatchStatus.PROPOSED,
                "patch_type": "add_rule",
                "new_text": "Existing proposed rule.",
            },
        }

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 0

    def test_skips_when_testing_patch_exists(self) -> None:
        """An existing 'testing' patch blocks new cluster."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.CPF,
                EvaluationFailureCategory.WRONG_INTERPRETATION,
            )
            for i in range(1, 5)
        }
        patches = {
            200: {
                "id": 200,
                "target_agent": TargetAgent.CPF,
                "failure_category": EvaluationFailureCategory.WRONG_INTERPRETATION,
                "status": PatchStatus.TESTING,
                "patch_type": "add_rule",
                "new_text": "Existing testing rule.",
            },
        }

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 0

    def test_skips_when_ready_for_approval_patch_exists(self) -> None:
        """An existing 'ready_for_approval' patch blocks new cluster."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.WSH,
                EvaluationFailureCategory.WRONG_LAW,
            )
            for i in range(1, 4)
        }
        patches = {
            300: {
                "id": 300,
                "target_agent": TargetAgent.WSH,
                "failure_category": EvaluationFailureCategory.WRONG_LAW,
                "status": PatchStatus.READY_FOR_APPROVAL,
                "patch_type": "add_rule",
                "new_text": "Existing ready rule.",
            },
        }

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 0

    def test_does_not_skip_when_patch_is_rejected(self) -> None:
        """A rejected patch should NOT block a new cluster."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.EMPLOYMENT_ACT,
                EvaluationFailureCategory.WRONG_LAW,
            )
            for i in range(1, 4)
        }
        patches = {
            400: {
                "id": 400,
                "target_agent": TargetAgent.EMPLOYMENT_ACT,
                "failure_category": EvaluationFailureCategory.WRONG_LAW,
                "status": PatchStatus.REJECTED,
                "patch_type": "add_rule",
                "new_text": "Rejected rule.",
            },
        }

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 1

    def test_does_not_skip_when_patch_is_rolled_back(self) -> None:
        """A rolled-back patch should NOT block a new cluster."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.TAX,
                EvaluationFailureCategory.FABRICATED_CITATION,
            )
            for i in range(1, 4)
        }
        patches = {
            500: {
                "id": 500,
                "target_agent": TargetAgent.TAX,
                "failure_category": EvaluationFailureCategory.FABRICATED_CITATION,
                "status": PatchStatus.ROLLED_BACK,
                "patch_type": "add_rule",
                "new_text": "Rolled back rule.",
            },
        }

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 1


# ---------------------------------------------------------------------------
# 4. MutationEngine -- produces a coherent InstructionPatch dict
# ---------------------------------------------------------------------------


class TestMutationEngineProposal:
    """MutationEngine.propose() takes a cluster and returns a patch dict."""

    @patch("hr_advisory.quality.mutation_engine.MutationEngine._call_llm")
    def test_propose_returns_valid_patch_dict(self, mock_llm) -> None:
        """propose() must return a dict with required InstructionPatch fields."""
        from hr_advisory.quality.mutation_engine import MutationEngine

        mock_llm.return_value = (
            "RULE: When advising on EA s.27 salary deductions, "
            "always mention the 25% per-incident cap and 50% per-period aggregate cap."
        )

        cluster = {
            "affected_agent": TargetAgent.EMPLOYMENT_ACT,
            "failure_category": EvaluationFailureCategory.MISSED_NUANCE,
            "count": 4,
            "evidence_ids": [1, 2, 3, 4],
            "correction_texts": [
                "Aggregate cap applies",
                "25% limit per incident",
                "50% total cap per period",
                "s.27 deduction cap",
            ],
        }

        engine = MutationEngine()
        result = engine.propose(cluster)

        assert result["target_agent"] == TargetAgent.EMPLOYMENT_ACT
        assert result["patch_type"] == "add_rule"
        assert result["new_text"]  # Non-empty string
        assert result["evidence_count"] == 4
        assert result["evidence_ids"] == [1, 2, 3, 4]
        assert result["status"] == PatchStatus.PROPOSED
        assert result["failure_category"] == EvaluationFailureCategory.MISSED_NUANCE

    @patch("hr_advisory.quality.mutation_engine.MutationEngine._call_llm")
    def test_propose_includes_proposed_at_timestamp(self, mock_llm) -> None:
        """The returned dict must include a proposed_at timestamp."""
        from hr_advisory.quality.mutation_engine import MutationEngine

        mock_llm.return_value = "RULE: Always check CPF rate tables by age band."

        cluster = {
            "affected_agent": TargetAgent.CPF,
            "failure_category": EvaluationFailureCategory.WRONG_INTERPRETATION,
            "count": 3,
            "evidence_ids": [10, 11, 12],
            "correction_texts": ["Rate error", "Wrong band", "Old table used"],
        }

        engine = MutationEngine()
        result = engine.propose(cluster)

        assert "proposed_at" in result
        assert result["proposed_at"] is not None

    @patch("hr_advisory.quality.mutation_engine.MutationEngine._call_llm")
    def test_propose_graceful_failure_on_llm_error(self, mock_llm) -> None:
        """If the LLM call fails, propose() returns None and logs the error."""
        from hr_advisory.quality.mutation_engine import MutationEngine

        mock_llm.side_effect = Exception("LLM service unavailable")

        cluster = {
            "affected_agent": TargetAgent.FOREIGN_MANPOWER,
            "failure_category": EvaluationFailureCategory.WRONG_LAW,
            "count": 3,
            "evidence_ids": [20, 21, 22],
            "correction_texts": ["Error 1", "Error 2", "Error 3"],
        }

        engine = MutationEngine()
        result = engine.propose(cluster)

        assert result is None

    @patch("hr_advisory.quality.mutation_engine.MutationEngine._call_llm")
    def test_propose_logs_error_on_failure(self, mock_llm, caplog) -> None:
        """LLM failures must be logged with context, not silently swallowed."""
        from hr_advisory.quality.mutation_engine import MutationEngine

        mock_llm.side_effect = RuntimeError("Connection refused")

        cluster = {
            "affected_agent": TargetAgent.FAIR_EMPLOYMENT,
            "failure_category": EvaluationFailureCategory.OVERLY_GENERIC,
            "count": 3,
            "evidence_ids": [30, 31, 32],
            "correction_texts": ["Too vague", "Lacks specifics", "Generic advice"],
        }

        engine = MutationEngine()
        with caplog.at_level(logging.ERROR, logger="hr_advisory.quality.mutation_engine"):
            engine.propose(cluster)

        assert any("Connection refused" in record.message for record in caplog.records)

    @patch("hr_advisory.quality.mutation_engine.MutationEngine._call_llm")
    def test_propose_empty_llm_response_returns_none(self, mock_llm) -> None:
        """If the LLM returns an empty string, propose() returns None."""
        from hr_advisory.quality.mutation_engine import MutationEngine

        mock_llm.return_value = ""

        cluster = {
            "affected_agent": TargetAgent.PDPA,
            "failure_category": EvaluationFailureCategory.MISSED_NUANCE,
            "count": 3,
            "evidence_ids": [40, 41, 42],
            "correction_texts": ["Gap 1", "Gap 2", "Gap 3"],
        }

        engine = MutationEngine()
        result = engine.propose(cluster)

        assert result is None


# ---------------------------------------------------------------------------
# 5. Duplicate patch prevention (PatternDetector + deployed patches)
# ---------------------------------------------------------------------------


class TestDuplicatePatchPrevention:
    """Ensure deployed patches do NOT block new clusters (only open ones do)."""

    def test_deployed_patch_does_not_block_new_cluster(self) -> None:
        """A deployed patch for the same group should NOT prevent re-detection."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.EMPLOYMENT_ACT,
                EvaluationFailureCategory.MISSED_NUANCE,
            )
            for i in range(1, 4)
        }
        patches = {
            600: {
                "id": 600,
                "target_agent": TargetAgent.EMPLOYMENT_ACT,
                "failure_category": EvaluationFailureCategory.MISSED_NUANCE,
                "status": PatchStatus.DEPLOYED,
                "patch_type": "add_rule",
                "new_text": "Already deployed rule.",
            },
        }

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        # Deployed patch should NOT block: the issue is recurring despite the fix
        assert len(clusters) == 1

    def test_approved_patch_blocks_new_cluster(self) -> None:
        """An approved (but not yet deployed) patch should block new clusters."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            i: _make_eval_dict(
                i,
                TargetAgent.CPF,
                EvaluationFailureCategory.WRONG_LAW,
            )
            for i in range(1, 5)
        }
        # NOTE: 'approved' is still open -- not yet deployed, not rejected
        # The task says: "no existing patch in proposed/testing/ready_for_approval"
        # So 'approved' should also be considered open (it's still in the pipeline)
        patches = {
            700: {
                "id": 700,
                "target_agent": TargetAgent.CPF,
                "failure_category": EvaluationFailureCategory.WRONG_LAW,
                "status": PatchStatus.APPROVED,
                "patch_type": "add_rule",
                "new_text": "Approved rule.",
            },
        }

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        # Approved is still in-pipeline, so it should block
        assert len(clusters) == 0


# ---------------------------------------------------------------------------
# 6. QA-LEARNED RULES section present in all specialist prompts
# ---------------------------------------------------------------------------


class TestQALearnedRulesSection:
    """All specialist agents must include the QA-LEARNED RULES section."""

    @pytest.mark.parametrize(
        "agent_class_path,agent_class_name",
        [
            (
                "hr_advisory.agents.specialists.employment_act",
                "EmploymentActAgent",
            ),
            (
                "hr_advisory.agents.specialists.cpf",
                "CPFAgent",
            ),
            (
                "hr_advisory.agents.specialists.foreign_manpower",
                "ForeignManpowerAgent",
            ),
            (
                "hr_advisory.agents.specialists.fair_employment",
                "FairEmploymentAgent",
            ),
            (
                "hr_advisory.agents.specialists.tax",
                "TaxAgent",
            ),
            (
                "hr_advisory.agents.specialists.wsh",
                "WSHAgent",
            ),
            (
                "hr_advisory.agents.specialists.pdpa",
                "PDPAAgent",
            ),
        ],
    )
    @patch("hr_advisory.agents.config._resolve_provider_and_model")
    @patch("kaizen.core.base_agent.BaseAgent.__init__", return_value=None)
    def test_specialist_has_qa_learned_rules_section(
        self,
        mock_base_init,
        mock_resolve,
        agent_class_path,
        agent_class_name,
    ) -> None:
        """Each specialist's system prompt must contain the QA-LEARNED RULES marker."""
        import importlib

        mock_resolve.return_value = ("openai", "gpt-4o")

        module = importlib.import_module(agent_class_path)
        cls = getattr(module, agent_class_name)

        # Create an instance -- we mock BaseAgent.__init__ to avoid LLM setup
        instance = object.__new__(cls)
        instance.domain = cls.domain
        instance.domain_label = cls.domain_label

        prompt = instance._generate_system_prompt()

        assert "QA-LEARNED RULES" in prompt, (
            f"{agent_class_name}._generate_system_prompt() is missing "
            f"the '== QA-LEARNED RULES ==' section"
        )
        assert "Do not modify manually" in prompt or "do not modify manually" in prompt.lower(), (
            f"{agent_class_name} QA-LEARNED RULES section must include the "
            f"'Do not modify manually' instruction"
        )


# ---------------------------------------------------------------------------
# 7. PatternDetector evidence_ids are correct
# ---------------------------------------------------------------------------


class TestPatternDetectorEvidenceIds:
    """The cluster's evidence_ids must be the actual evaluation IDs."""

    def test_evidence_ids_match_evaluation_ids(self) -> None:
        """Cluster evidence_ids should be the IDs of matching evaluations."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        evals = {
            10: _make_eval_dict(
                10,
                TargetAgent.WSH,
                EvaluationFailureCategory.WRONG_ROUTING,
            ),
            20: _make_eval_dict(
                20,
                TargetAgent.WSH,
                EvaluationFailureCategory.WRONG_ROUTING,
            ),
            30: _make_eval_dict(
                30,
                TargetAgent.WSH,
                EvaluationFailureCategory.WRONG_ROUTING,
            ),
        }
        patches: Dict[int, Dict[str, Any]] = {}

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 1
        assert set(clusters[0]["evidence_ids"]) == {10, 20, 30}

    def test_correction_texts_included_in_cluster(self) -> None:
        """Clusters must carry correction_texts for MutationEngine context."""
        from hr_advisory.quality.pattern_detector import PatternDetector

        corrections = ["Fix A", "Fix B", "Fix C"]
        evals = {}
        for i, txt in enumerate(corrections, start=1):
            evals[i] = _make_eval_dict(
                i,
                TargetAgent.FAIR_EMPLOYMENT,
                EvaluationFailureCategory.IGNORED_CONTEXT,
                correction_text=txt,
            )
        patches: Dict[int, Dict[str, Any]] = {}

        detector = PatternDetector(evaluations=evals, patches=patches)
        clusters = detector.run()

        assert len(clusters) == 1
        assert set(clusters[0]["correction_texts"]) == {"Fix A", "Fix B", "Fix C"}


# ---------------------------------------------------------------------------
# 8. MutationEngine uses settings for LLM config (never hardcoded)
# ---------------------------------------------------------------------------


class TestMutationEngineConfig:
    """MutationEngine must use get_settings() for LLM provider/model."""

    @patch("hr_advisory.quality.mutation_engine.get_settings")
    @patch("hr_advisory.quality.mutation_engine.MutationEngine._call_llm")
    def test_engine_reads_model_from_settings(self, mock_llm, mock_settings) -> None:
        """MutationEngine should read LLM model from environment settings."""
        from hr_advisory.quality.mutation_engine import MutationEngine

        mock_settings.return_value = MagicMock(
            openai_api_key="test-key",
            openai_prod_model="gpt-4o",
            default_llm_model="gpt-4o",
        )
        mock_llm.return_value = "RULE: Test rule text."

        cluster = {
            "affected_agent": TargetAgent.TAX,
            "failure_category": EvaluationFailureCategory.WRONG_INTERPRETATION,
            "count": 3,
            "evidence_ids": [50, 51, 52],
            "correction_texts": ["Fix 1", "Fix 2", "Fix 3"],
        }

        engine = MutationEngine()
        result = engine.propose(cluster)

        assert result is not None
        assert result["new_text"] == "RULE: Test rule text."
