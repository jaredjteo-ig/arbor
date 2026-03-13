"""Short-term (per-session) conversation memory.

Stores recent queries, responses, and extracted entities so the
orchestration pipeline can maintain context across turns within a
single advisory session.

Backed by Kaizen BufferMemory with a configurable turn window.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from kaizen.memory import BufferMemory

logger = logging.getLogger(__name__)

DEFAULT_MAX_TURNS = 20


class ShortTermMemory:
    """Window-based conversation memory for a single advisory session.

    Each turn stores:
      - query:    str   (the user's question)
      - response: str   (the synthesized answer)
      - entities: dict  (entities extracted by QueryAnalyzer)
      - domains:  list  (domains identified for this turn)
      - risk_tier: str  (risk tier for this turn)
      - timestamp: str  (ISO 8601)
    """

    def __init__(self, max_turns: int = DEFAULT_MAX_TURNS) -> None:
        self._buffer = BufferMemory(max_turns=max_turns)
        self.max_turns = max_turns

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def save_turn(
        self,
        session_id: str,
        query: str,
        response: str,
        entities: Optional[Dict[str, Any]] = None,
        domains: Optional[List[str]] = None,
        risk_tier: str = "green",
    ) -> None:
        """Persist one query-response turn."""
        turn = {
            "user": query,
            "agent": response,
            "entities": entities or {},
            "domains": domains or [],
            "risk_tier": risk_tier,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._buffer.save_turn(session_id, turn)

    def load_context(self, session_id: str) -> Dict[str, Any]:
        """Load conversation context for the session.

        Returns:
            {
                "turns": [...],
                "turn_count": int,
                "recent_entities": dict,   # merged entities from last 3 turns
                "recent_domains": list,    # unique domains from last 3 turns
            }
        """
        raw = self._buffer.load_context(session_id)
        turns = raw.get("turns", [])

        # Merge entities from last 3 turns for quick context
        recent = turns[-3:] if len(turns) >= 3 else turns
        merged_entities: Dict[str, Any] = {}
        recent_domains: List[str] = []
        for t in recent:
            merged_entities.update(t.get("entities", {}))
            recent_domains.extend(t.get("domains", []))

        return {
            "turns": turns,
            "turn_count": len(turns),
            "recent_entities": merged_entities,
            "recent_domains": sorted(set(recent_domains)),
        }

    def clear(self, session_id: str) -> None:
        """Erase all turns for the given session."""
        self._buffer.clear(session_id)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def get_last_query(self, session_id: str) -> Optional[str]:
        """Return the most recent user query, or None."""
        ctx = self.load_context(session_id)
        turns = ctx.get("turns", [])
        if turns:
            return turns[-1].get("user")
        return None

    def get_turn_count(self, session_id: str) -> int:
        """Return the number of stored turns."""
        return self.load_context(session_id).get("turn_count", 0)
