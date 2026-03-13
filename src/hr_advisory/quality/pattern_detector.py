"""Pattern detection for QA evaluation failures.

Clusters QA evaluation failures by (affected_agent, failure_category).
When a cluster reaches 3+ instances and no existing open patch covers the
group, it emits the cluster for mutation by MutationEngine.

Usage:
    detector = PatternDetector(evaluations=_evaluations, patches=_patches)
    clusters = detector.run()
    # Each cluster is a dict with keys:
    #   affected_agent, failure_category, count, evidence_ids, correction_texts
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from hr_advisory.models.qa import PatchStatus

logger = logging.getLogger(__name__)

# Minimum number of matching evaluations required to form a cluster
CLUSTER_THRESHOLD = 3

# Patch statuses that indicate an open/in-progress patch (should block new clusters)
OPEN_PATCH_STATUSES = frozenset(
    [
        PatchStatus.PROPOSED,
        PatchStatus.TESTING,
        PatchStatus.READY_FOR_APPROVAL,
        PatchStatus.APPROVED,
    ]
)


class PatternDetector:
    """Detects recurring QA failure patterns from evaluation data.

    Scans in-memory evaluation stores for clusters of failures grouped by
    (affected_agent, failure_category). Only evaluations with
    has_material_correction=True are considered.

    Args:
        evaluations: Dict mapping evaluation ID to evaluation dict.
        patches: Dict mapping patch ID to patch dict.
    """

    def __init__(
        self,
        evaluations: Dict[int, Dict[str, Any]],
        patches: Dict[int, Dict[str, Any]],
    ) -> None:
        if evaluations is None:
            raise ValueError("evaluations must not be None -- pass an empty dict instead")
        if patches is None:
            raise ValueError("patches must not be None -- pass an empty dict instead")
        self._evaluations = evaluations
        self._patches = patches

    def run(self) -> List[Dict[str, Any]]:
        """Detect failure clusters ready for mutation.

        Returns:
            List of cluster dicts, each containing:
                - affected_agent: str
                - failure_category: str
                - count: int (number of matching evaluations)
                - evidence_ids: list[int] (evaluation IDs in the cluster)
                - correction_texts: list[str] (correction texts from evaluations)
        """
        # Step 1: Group evaluations by (affected_agent, failure_category)
        groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

        for eval_id, evaluation in self._evaluations.items():
            if not evaluation.get("has_material_correction", False):
                continue

            agent = evaluation.get("affected_agent")
            category = evaluation.get("failure_category")

            if not agent or not category:
                logger.debug(
                    "Skipping evaluation %s: missing affected_agent or failure_category",
                    eval_id,
                )
                continue

            groups[(agent, category)].append(evaluation)

        # Step 2: Filter groups that meet the threshold
        clusters: List[Dict[str, Any]] = []

        for (agent, category), evals in groups.items():
            if len(evals) < CLUSTER_THRESHOLD:
                continue

            # Step 3: Check if an open patch already covers this group
            if self._has_open_patch(agent, category):
                logger.info(
                    "Skipping cluster (%s, %s) -- an open patch already exists",
                    agent,
                    category,
                )
                continue

            evidence_ids = [e["id"] for e in evals]
            correction_texts = [
                e.get("correction_text", "") for e in evals if e.get("correction_text")
            ]

            cluster = {
                "affected_agent": agent,
                "failure_category": category,
                "count": len(evals),
                "evidence_ids": evidence_ids,
                "correction_texts": correction_texts,
            }

            logger.info(
                "Detected failure cluster: agent=%s, category=%s, count=%d",
                agent,
                category,
                len(evals),
            )
            clusters.append(cluster)

        return clusters

    def _has_open_patch(self, agent: str, category: str) -> bool:
        """Check if an open/in-progress patch exists for this (agent, category).

        A patch is considered 'open' if its status is one of:
        proposed, testing, ready_for_approval, or approved.

        Deployed, rejected, and rolled_back patches do NOT block new clusters.

        Args:
            agent: The target agent identifier.
            category: The failure category.

        Returns:
            True if an open patch exists for this group.
        """
        for patch in self._patches.values():
            if (
                patch.get("target_agent") == agent
                and patch.get("failure_category") == category
                and patch.get("status") in OPEN_PATCH_STATUSES
            ):
                return True
        return False
