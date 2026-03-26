"""Shared memory pool for specialist agent outputs.

Wraps the Kaizen SharedMemory with HR-specific tag validation
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


logger = logging.getLogger(__name__)

# Required metadata keys for HR specialist outputs
REQUIRED_METADATA_KEYS = frozenset(["domain", "provision_ids", "confidence", "risk_tier"])


class HRSharedMemoryPool:
    """HR-domain wrapper around Kaizen SharedMemory.

    Enforces that every specialist insight carries the metadata
    needed by the ResponseSynthesizerAgent for citation and
    risk-tier aggregation.
    """

    def __init__(self) -> None:
        self._insights: list[dict[str, Any]] = []

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
        """Write a specialist agent's output to the shared pool."""
        if risk_tier not in ("green", "amber", "red"):
            raise ValueError(f"risk_tier must be green/amber/red, got {risk_tier}")

        if isinstance(content, (dict, list)):
            content_str = json.dumps(content)
        else:
            content_str = str(content)

        metadata = {
            "domain": domain,
            "provision_ids": provision_ids or [],
            "confidence": confidence,
            "risk_tier": risk_tier,
            "cross_domain_flags": cross_domain_flags or [],
        }

        insight = {
            "agent_id": agent_id,
            "content": content_str,
            "metadata": metadata,
        }
        self._insights.append(insight)

        logger.debug("Stored specialist output: %s/%s", agent_id, domain)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def read_all_specialist_outputs(self) -> List[Dict[str, Any]]:
        """Return all specialist outputs in the pool."""
        return list(self._insights)

    def read_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Return specialist outputs for a specific domain."""
        return [i for i in self._insights if i.get("metadata", {}).get("domain") == domain]

    def get_highest_risk_tier(self) -> str:
        """Return the most severe risk tier across all specialist outputs."""
        severity = {"green": 0, "amber": 1, "red": 2}
        worst = "green"
        for insight in self._insights:
            tier = insight.get("metadata", {}).get("risk_tier", "green")
            if severity.get(tier, 0) > severity.get(worst, 0):
                worst = tier
        return worst

    # ------------------------------------------------------------------
    # Delegate
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear the pool."""
        self._insights.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return pool statistics."""
        domains = set()
        agents = set()
        for i in self._insights:
            domains.add(i.get("metadata", {}).get("domain", ""))
            agents.add(i.get("agent_id", ""))
        return {
            "insight_count": len(self._insights),
            "domain_count": len(domains),
            "agent_count": len(agents),
        }

    @property
    def inner_pool(self) -> "HRSharedMemoryPool":
        """Access the pool (self-reference for backward compat)."""
        return self
