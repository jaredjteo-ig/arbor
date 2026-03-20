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
_UNDO_WINDOW_SECONDS = 8  # seconds after completion where undo is allowed
_COOLDOWN_SECONDS = 5  # server-side cooldown for always_propose/double_confirm


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
    trust_level: str = "propose"  # propose, always_propose, double_confirm
    status: str = "preview"  # preview, awaiting_double_confirm, executing, done, failed, cancelled
    created_at: str = ""
    completed_at: str | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    confirmed_count: int = 0  # how many times user has confirmed (double_confirm needs 2)
    _created_ts: float = 0.0  # monotonic time for TTL tracking
    _completed_ts: float = 0.0  # monotonic time for undo window tracking

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

    def is_undoable(self) -> bool:
        """Check if this session is within the undo window (8 seconds after completion)."""
        if self.status != "done" or self._completed_ts == 0.0:
            return False
        return (time.monotonic() - self._completed_ts) <= _UNDO_WINDOW_SECONDS

    @property
    def requires_double_confirm(self) -> bool:
        """Whether this session requires a two-step approval gate."""
        return self.trust_level == "double_confirm"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "intent_module": self.intent_module,
            "intent_action": self.intent_action,
            "confirmation_message": self.confirmation_message,
            "steps": [s.to_dict() for s in self.steps],
            "trust_level": self.trust_level,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "results": self.results,
            "confirmed_count": self.confirmed_count,
            "requires_double_confirm": self.requires_double_confirm,
            "is_undoable": self.is_undoable(),
        }


class PaceManager:
    """Manages PACE sessions for write-operation confirmation flow.

    In-memory storage with LRU eviction and TTL cleanup.
    Production: swap to Redis-backed store.
    """

    def __init__(
        self,
        max_sessions: int = _MAX_SESSIONS,
        cooldown_seconds: float = _COOLDOWN_SECONDS,
    ) -> None:
        self._sessions: OrderedDict[str, PaceSession] = OrderedDict()
        self._max_sessions = max_sessions
        self._cooldown_seconds = cooldown_seconds

    def create_session(
        self,
        user_id: str,
        intent_module: str,
        intent_action: str,
        confirmation_message: str,
        steps: list[PaceStep],
        trust_level: str = "propose",
    ) -> PaceSession:
        """Create a new PACE session in preview state.

        Args:
            user_id: The ID of the user who initiated the action.
            intent_module: The classified module (e.g. "leave").
            intent_action: The classified action (e.g. "apply").
            confirmation_message: Human-readable description of what will happen.
            steps: The execution steps that will be performed on confirmation.
            trust_level: Trust classification — "propose", "always_propose",
                or "double_confirm". Double-confirm requires two approvals.

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
            trust_level=trust_level,
        )
        self._sessions[session_id] = session

        logger.info(
            "PACE session created: %s (%s.%s, %d steps, trust=%s)",
            session_id,
            intent_module,
            intent_action,
            len(steps),
            trust_level,
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

    def confirm_session(self, session_id: str) -> tuple[PaceSession | None, bool]:
        """Record a confirmation for a PACE session.

        For double_confirm sessions, the first confirmation transitions
        from 'preview' to 'awaiting_double_confirm'. The second confirmation
        transitions to execution.

        For single-confirm sessions (propose, always_propose), one
        confirmation is sufficient.

        Args:
            session_id: The session to confirm.

        Returns:
            (session, ready_to_execute) — the session and whether it's
            ready for execution (True) or still awaiting more confirmations.
        """
        session = self.get_session(session_id)
        if session is None:
            return None, False

        # Server-side cooldown for dangerous actions
        if session.trust_level in ("always_propose", "double_confirm"):
            elapsed = time.monotonic() - session._created_ts
            if elapsed < self._cooldown_seconds:
                logger.warning(
                    "PACE session %s cooldown not met: %.1fs < %ds",
                    session_id,
                    elapsed,
                    _COOLDOWN_SECONDS,
                )
                return session, False

        if session.status not in ("preview", "awaiting_double_confirm"):
            logger.warning(
                "Cannot confirm PACE session %s — status is '%s'",
                session_id,
                session.status,
            )
            return session, False

        session.confirmed_count += 1

        if session.requires_double_confirm and session.confirmed_count < 2:
            session.status = "awaiting_double_confirm"
            logger.info(
                "PACE session %s: first confirmation received (double-confirm required)",
                session_id,
            )
            return session, False

        # Ready to execute
        return session, True

    async def execute_session(
        self,
        session_id: str,
        jwt_token: str,
    ) -> PaceSession | None:
        """Execute a confirmed PACE session.

        Runs all steps sequentially. Stops on first failure for write
        operations. Updates step and session statuses as it goes.

        For double_confirm sessions, call confirm_session() first to
        verify both confirmations have been received.

        Args:
            session_id: The session to execute.
            jwt_token: The user's JWT for authorization.

        Returns:
            The updated PaceSession, or None if not found/expired.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        if session.status not in ("preview", "awaiting_double_confirm"):
            logger.warning(
                "Cannot execute PACE session %s — status is '%s'",
                session_id,
                session.status,
            )
            return session

        # Double-confirm guard: must have 2 confirmations
        if session.requires_double_confirm and session.confirmed_count < 2:
            logger.warning(
                "Cannot execute double-confirm PACE session %s — only %d/2 confirmations",
                session_id,
                session.confirmed_count,
            )
            return session

        from hr_advisory.shadow.executor import ShadowExecutor, _get_shared_executor
        from hr_advisory.shadow.tool_registry import ToolDefinition

        executor = _get_shared_executor()
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
                trust_level=session.trust_level,
                description=step.description,
                is_mcp=step.method.upper() == "MCP",
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
        session._completed_ts = time.monotonic()

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

        if session.status not in ("preview", "awaiting_double_confirm"):
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
