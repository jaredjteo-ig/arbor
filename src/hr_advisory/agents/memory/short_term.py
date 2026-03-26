"""Short-term (per-session) conversation memory.

Stores recent queries, responses, and extracted entities so the
orchestration pipeline can maintain context across turns within a
single advisory session.

Backed by Kaizen BufferMemory for hot context, with database persistence
via ConversationThread/ConversationMessage DataFlow models.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_TURNS = 20


class _TurnBuffer:
    """Simple windowed turn buffer (replaces old Kaizen BufferMemory)."""

    def __init__(self, max_turns: int = DEFAULT_MAX_TURNS) -> None:
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
        self._max_turns = max_turns

    def save_turn(self, session_id: str, turn: Dict[str, Any]) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(turn)
        if len(self._sessions[session_id]) > self._max_turns:
            self._sessions[session_id] = self._sessions[session_id][-self._max_turns :]

    def get_turns(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._sessions.get(session_id, []))

    def get_turn_count(self, session_id: str) -> int:
        return len(self._sessions.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear_all(self) -> None:
        self._sessions.clear()


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
        self._buffer = _TurnBuffer(max_turns=max_turns)
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
        provisions_cited: Optional[List[Dict[str, Any]]] = None,
        confidence_score: Optional[float] = None,
        user_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> None:
        """Persist one query-response turn (in-memory + database)."""
        turn: Dict[str, Any] = {
            "user": query,
            "agent": response,
            "entities": entities or {},
            "domains": domains or [],
            "risk_tier": risk_tier,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if provisions_cited:
            turn["provisions_cited"] = provisions_cited
        if confidence_score is not None:
            import math

            if not math.isfinite(confidence_score):
                confidence_score = 0.0
            turn["confidence_score"] = confidence_score
        self._buffer.save_turn(session_id, turn)

        # Persist to database (best-effort)
        self._persist_turn(
            session_id=session_id,
            query=query,
            response=response,
            entities=entities,
            domains=domains,
            risk_tier=risk_tier,
            provisions_cited=provisions_cited,
            confidence_score=confidence_score,
            user_id=user_id,
            company_id=company_id,
        )

    def _persist_turn(
        self,
        session_id: str,
        query: str,
        response: str,
        entities: Optional[Dict[str, Any]],
        domains: Optional[List[str]],
        risk_tier: str,
        provisions_cited: Optional[List[Dict[str, Any]]],
        confidence_score: Optional[float],
        user_id: Optional[int],
        company_id: Optional[int],
    ) -> None:
        """Persist conversation turn to database (best-effort)."""
        try:
            from kailash import LocalRuntime, WorkflowBuilder

            # Ensure thread exists (upsert by session_id)
            thread_id = self._ensure_thread(
                session_id, user_id or 0, company_id or 0, subject=query[:60]
            )
            if not thread_id:
                return

            # Save user message
            wf = WorkflowBuilder()
            wf.add_node(
                "ConversationMessageCreateNode",
                "save_user_msg",
                {
                    "thread_id": thread_id,
                    "sender": "user",
                    "text": query[:4000],
                    "entities": json.dumps(entities or {}),
                    "domains": json.dumps(domains or []),
                    "risk_tier": risk_tier,
                },
            )
            runtime = LocalRuntime()
            runtime.execute(wf.build())

            # Save agent message
            wf2 = WorkflowBuilder()
            wf2.add_node(
                "ConversationMessageCreateNode",
                "save_agent_msg",
                {
                    "thread_id": thread_id,
                    "sender": "agent",
                    "text": response[:8000],
                    "entities": json.dumps(entities or {}),
                    "domains": json.dumps(domains or []),
                    "risk_tier": risk_tier,
                    "confidence_score": confidence_score,
                    "provisions_cited": json.dumps(provisions_cited or []),
                },
            )
            runtime.execute(wf2.build())
        except Exception as exc:
            logger.warning("Failed to persist conversation turn: %s", exc)

    def _ensure_thread(
        self, session_id: str, user_id: int, company_id: int, subject: str = ""
    ) -> Optional[int]:
        """Get or create a conversation thread for the session_id."""
        try:
            from kailash import LocalRuntime, WorkflowBuilder

            # Try to find existing thread
            wf = WorkflowBuilder()
            wf.add_node(
                "ConversationThreadListNode",
                "find_thread",
                {
                    "filter": {"session_id": session_id},
                    "limit": 1,
                    "enable_cache": False,
                },
            )
            runtime = LocalRuntime()
            results, _ = runtime.execute(wf.build())
            records = results.get("find_thread", {})
            if isinstance(records, dict):
                items = records.get("records", [])
            else:
                items = records if isinstance(records, list) else []

            if items:
                return items[0].get("id")

            # Create new thread
            wf2 = WorkflowBuilder()
            wf2.add_node(
                "ConversationThreadCreateNode",
                "create_thread",
                {
                    "user_id": user_id,
                    "company_id": company_id,
                    "session_id": session_id,
                    "subject": subject,
                },
            )
            results2, _ = runtime.execute(wf2.build())
            created = results2.get("create_thread", {})
            return created.get("id")
        except Exception as exc:
            logger.warning("Failed to ensure conversation thread: %s", exc)
            return None

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
        turns = self._buffer.get_turns(session_id)

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

    def load_as_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Load conversation as OpenAI message-format list.

        Returns:
            [{role: "user", content: "..."}, {role: "assistant", content: "..."}, ...]
        """
        ctx = self.load_context(session_id)
        messages: List[Dict[str, str]] = []
        for turn in ctx.get("turns", []):
            user_content = turn.get("user", "")
            if user_content:
                messages.append({"role": "user", "content": user_content})
            agent_content = turn.get("agent", "")
            if agent_content:
                messages.append({"role": "assistant", "content": agent_content})
        return messages
