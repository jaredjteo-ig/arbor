"""Shared memory pool for specialist agent outputs.

Wraps the Kaizen SharedMemoryPool with HR-specific tag validation
and structured storage conventions.

Every insight written by a specialist agent is expected to carry:
  - domain:            str   (e.g. "employment_act")
  - provision_ids:     list  (e.g. [12, 45])
  - confidence:        float (0.0-1.0)
  - risk_tier:         str   ("green" | "amber" | "red")
  - cross_domain_flags: list  (domains that may also be affected)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from kaizen.memory import SharedMemoryPool

logger = logging.getLogger(__name__)

# Required metadata keys for HR specialist outputs
REQUIRED_METADATA_KEYS = frozenset(["domain", "provision_ids", "confidence", "risk_tier"])


class HRSharedMemoryPool:
    """HR-domain wrapper around Kaizen SharedMemoryPool.

    Enforces that every specialist insight carries the metadata
    needed by the ResponseSynthesizerAgent for citation and
    risk-tier aggregation.
    """

    def __init__(self) -> None:
        self._pool = SharedMemoryPool()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_specialist_output(
        self,
        agent_id: str,
        domain: str,
        content: Any,
        provision_ids: Optional[List[int]] = None,
        confidence: float = 0.5,
        risk_tier: str = "green",
        cross_domain_flags: Optional[List[str]] = None,
        extra_tags: Optional[List[str]] = None,
    ) -> None:
        """Write a specialist agent's output to the shared pool.

        Args:
            agent_id: Identifier of the specialist agent.
            domain: Primary domain key (e.g. "cpf").
            content: The advisory content (dict or string).
            provision_ids: List of Provision record IDs referenced.
            confidence: Confidence score 0.0-1.0.
            risk_tier: green | amber | red.
            cross_domain_flags: Other domains that might be affected.
            extra_tags: Additional tags for filtering.
        """
        if risk_tier not in ("green", "amber", "red"):
            raise ValueError(f"risk_tier must be green/amber/red, got {risk_tier}")

        # Serialize content if needed
        if isinstance(content, (dict, list)):
            content_str = json.dumps(content)
        else:
            content_str = str(content)

        tags = [domain]
        if extra_tags:
            tags.extend(extra_tags)

        metadata = {
            "domain": domain,
            "provision_ids": provision_ids or [],
            "confidence": confidence,
            "risk_tier": risk_tier,
            "cross_domain_flags": cross_domain_flags or [],
        }

        self._pool.write_insight(
            {
                "agent_id": agent_id,
                "content": content_str,
                "tags": tags,
                "importance": confidence,
                "segment": "specialist_output",
                "metadata": metadata,
            }
        )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def read_all_specialist_outputs(self) -> List[Dict[str, Any]]:
        """Return all specialist outputs in the pool."""
        return self._pool.read_relevant(segments=["specialist_output"])

    def read_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Return specialist outputs for a specific domain."""
        return self._pool.read_relevant(
            tags=[domain],
            segments=["specialist_output"],
        )

    def get_highest_risk_tier(self) -> str:
        """Return the most severe risk tier across all specialist outputs.

        Severity order: red > amber > green.
        """
        severity = {"green": 0, "amber": 1, "red": 2}
        worst = "green"
        for insight in self.read_all_specialist_outputs():
            tier = insight.get("metadata", {}).get("risk_tier", "green")
            if severity.get(tier, 0) > severity.get(worst, 0):
                worst = tier
        return worst

    # ------------------------------------------------------------------
    # Delegate
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear the pool (useful between sessions)."""
        self._pool.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return pool statistics."""
        return self._pool.get_stats()

    @property
    def inner_pool(self) -> SharedMemoryPool:
        """Access the underlying Kaizen SharedMemoryPool.

        Useful when passing to BaseAgent(shared_memory=...).
        """
        return self._pool
