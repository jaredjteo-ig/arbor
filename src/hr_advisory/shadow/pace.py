# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""PACE session manager for the Shadow Agent.

PACE = Preview, Approve, Confirm, Exit

For write operations, the Shadow Agent doesn't execute immediately.
Instead, it creates a PACE session that shows the user what will
happen (Preview), waits for their approval (Approve), executes
the action (Confirm), and returns the result (Exit).

Sessions are stored in memory with TTL-based cleanup. Production
deployment should use Redis for persistence across restarts.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "PaceManager",
    "PaceSession",
    "PaceStep",
]

# Maximum sessions in memory and TTL
_MAX_SESSIONS = 10000
_SESSION_TTL_SECONDS = 600  # 10 minutes — pending sessions expire after this


@dataclass
class PaceStep:
    """A single step in a PACE execution plan."""

    description: str
    tool_module: str
    tool_action: str
    method: str
    path: str
    params: dict[str, Any]
    status: str = "pending"  # pending, executing, done, failed, cancelled

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON responses."""
        return {
            "description": self.description,
            "tool_module": self.tool_module,
            "tool_action": self.tool_action,
            "method": self.method,
            "path": self.path,
            "params": self.params,
            "status": self.status,
        }


@dataclass
class PaceSession:
    """A PACE session containing one or more execution steps."""

    id: str
    user_id: str
    intent_module: str
    intent_action: str
    confirmation_message: str
    steps: list[PaceStep]
    status: str = "preview"  # preview, executing, done, failed, cancelled
    created_at: str = ""
    completed_at: str | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    _created_ts: float = 0.0  # monotonic time for TTL tracking

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self._created_ts == 0.0:
            self._created_ts = time.monotonic()

    def is_expired(self) -> bool:
        """Check if this session has exceeded the TTL."""
        if self.status in ("done", "failed", "cancelled"):
            return False  # Completed sessions don't expire (they're cleaned up differently)
        return (time.monotonic() - self._created_ts) > _SESSION_TTL_SECONDS

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "intent_module": self.intent_module,
            "intent_action": self.intent_action,
            "confirmation_message": self.confirmation_message,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "results": self.results,
        }


class PaceManager:
    """Manages PACE sessions for write-operation confirmation flow.

    In-memory storage with LRU eviction and TTL cleanup.
    Production: swap to Redis-backed store.
    """

    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._sessions: OrderedDict[str, PaceSession] = OrderedDict()
        self._max_sessions = max_sessions

    def create_session(
        self,
        user_id: str,
        intent_module: str,
        intent_action: str,
        confirmation_message: str,
        steps: list[PaceStep],
    ) -> PaceSession:
        """Create a new PACE session in preview state.

        Args:
            user_id: The ID of the user who initiated the action.
            intent_module: The classified module (e.g. "leave").
            intent_action: The classified action (e.g. "apply").
            confirmation_message: Human-readable description of what will happen.
            steps: The execution steps that will be performed on confirmation.

        Returns:
            The newly created PaceSession.
        """
        # Evict expired sessions first
        self._cleanup_expired()

        # Evict oldest if at capacity
        while len(self._sessions) >= self._max_sessions:
            evicted_id, _ = self._sessions.popitem(last=False)
            logger.debug("PACE session evicted (LRU): %s", evicted_id)

        session_id = str(uuid.uuid4())
        session = PaceSession(
            id=session_id,
            user_id=user_id,
            intent_module=intent_module,
            intent_action=intent_action,
            confirmation_message=confirmation_message,
            steps=steps,
        )
        self._sessions[session_id] = session

        logger.info(
            "PACE session created: %s (%s.%s, %d steps)",
            session_id,
            intent_module,
            intent_action,
            len(steps),
        )
        return session

    def get_session(self, session_id: str) -> PaceSession | None:
        """Get a session by ID.

        Returns None if not found or expired.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired():
            logger.debug("PACE session expired: %s", session_id)
            self._sessions.pop(session_id, None)
            return None
        return session

    def get_user_sessions(self, user_id: str, status: str | None = None) -> list[PaceSession]:
        """Get all sessions for a user, optionally filtered by status.

        Args:
            user_id: The user ID to filter by.
            status: Optional status filter (e.g. "preview", "done").

        Returns:
            List of matching PaceSession objects.
        """
        self._cleanup_expired()
        sessions = []
        for session in self._sessions.values():
            if session.user_id != user_id:
                continue
            if status is not None and session.status != status:
                continue
            sessions.append(session)
        return sessions

    async def execute_session(
        self,
        session_id: str,
        jwt_token: str,
    ) -> PaceSession | None:
        """Execute a pending PACE session.

        Runs all steps sequentially. Stops on first failure for write
        operations. Updates step and session statuses as it goes.

        Args:
            session_id: The session to execute.
            jwt_token: The user's JWT for authorization.

        Returns:
            The updated PaceSession, or None if not found/expired.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        if session.status != "preview":
            logger.warning(
                "Cannot execute PACE session %s — status is '%s', expected 'preview'",
                session_id,
                session.status,
            )
            return session

        from hr_advisory.shadow.executor import ShadowExecutor
        from hr_advisory.shadow.tool_registry import ToolDefinition

        executor = ShadowExecutor()
        session.status = "executing"

        all_succeeded = True
        for step in session.steps:
            step.status = "executing"

            tool = ToolDefinition(
                module=step.tool_module,
                action=step.tool_action,
                method=step.method,
                path=step.path,
                params=[],
                trust_level="propose",
                description=step.description,
            )

            result = await executor.execute(tool, step.params, jwt_token)
            session.results.append(result.to_dict())

            if result.success:
                step.status = "done"
            else:
                step.status = "failed"
                all_succeeded = False
                # Stop execution on write failure
                if step.method.upper() != "GET":
                    # Mark remaining steps as cancelled
                    idx = session.steps.index(step)
                    for remaining_step in session.steps[idx + 1 :]:
                        remaining_step.status = "cancelled"
                    break

        session.status = "done" if all_succeeded else "failed"
        session.completed_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "PACE session %s completed: status=%s, %d/%d steps succeeded",
            session_id,
            session.status,
            sum(1 for s in session.steps if s.status == "done"),
            len(session.steps),
        )
        return session

    def cancel_session(self, session_id: str) -> bool:
        """Cancel a pending PACE session.

        Args:
            session_id: The session to cancel.

        Returns:
            True if the session was found and cancelled, False otherwise.
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        if session.status != "preview":
            logger.warning(
                "Cannot cancel PACE session %s — status is '%s'",
                session_id,
                session.status,
            )
            return False

        session.status = "cancelled"
        session.completed_at = datetime.now(timezone.utc).isoformat()
        for step in session.steps:
            if step.status == "pending":
                step.status = "cancelled"

        logger.info("PACE session cancelled: %s", session_id)
        return True

    def _cleanup_expired(self) -> None:
        """Remove expired sessions from the store."""
        expired_ids = [sid for sid, session in self._sessions.items() if session.is_expired()]
        for sid in expired_ids:
            self._sessions.pop(sid, None)
        if expired_ids:
            logger.debug("Cleaned up %d expired PACE sessions", len(expired_ids))


# Module-level singleton
_manager: PaceManager | None = None


def get_pace_manager() -> PaceManager:
    """Get or create the shared PaceManager singleton."""
    global _manager
    if _manager is None:
        _manager = PaceManager()
    return _manager
