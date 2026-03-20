"""T479: PACE session manager tests for the Shadow Agent.

Tests the PaceManager, PaceSession, and PaceStep dataclasses including:
- Session creation with different trust levels
- Session expiry after TTL
- Session cancellation
- Double confirmation flow
- Single confirm for propose/always_propose
- LRU eviction when max_sessions reached
- Undo window timing
- Expired session cleanup
- Session serialization (to_dict)
"""

from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock

import pytest

# Prevent Kaizen import chain
_kaizen_mods = [
    "kaizen",
    "kaizen.core",
    "kaizen.core.base_agent",
    "kaizen.memory",
    "kaizen.config",
    "kaizen.config.providers",
    "kaizen.signatures",
    "kaizen.core.workflow_generator",
    "kaizen.nodes",
    "kaizen.nodes.ai",
    "kaizen.nodes.ai.llm_agent",
]
for _m in _kaizen_mods:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

from hr_advisory.shadow.pace import (
    PaceManager,
    PaceSession,
    PaceStep,
    _MAX_SESSIONS,
    _SESSION_TTL_SECONDS,
    _UNDO_WINDOW_SECONDS,
)


# ── Helpers ──────────────────────────────────────────────────────


def _make_step(desc: str = "Test step", method: str = "POST") -> PaceStep:
    """Create a minimal PaceStep for testing."""
    return PaceStep(
        description=desc,
        tool_module="employees",
        tool_action="create",
        method=method,
        path="/employees",
        params={"name": "John"},
    )


def _create_session(
    mgr: PaceManager,
    user_id: str = "user1",
    trust_level: str = "propose",
    steps: list[PaceStep] | None = None,
) -> PaceSession:
    """Create a session with sensible defaults."""
    if steps is None:
        steps = [_make_step()]
    return mgr.create_session(
        user_id=user_id,
        intent_module="employees",
        intent_action="create",
        confirmation_message="Create employee John?",
        steps=steps,
        trust_level=trust_level,
    )


# =========================================================================
# PaceStep Tests
# =========================================================================


class TestPaceStep:
    """PaceStep construction and serialization."""

    def test_create_step(self) -> None:
        step = _make_step("Create employee")
        assert step.description == "Create employee"
        assert step.tool_module == "employees"
        assert step.tool_action == "create"
        assert step.method == "POST"
        assert step.path == "/employees"
        assert step.status == "pending"

    def test_step_default_status(self) -> None:
        step = _make_step()
        assert step.status == "pending"

    def test_step_to_dict(self) -> None:
        step = _make_step("Test step")
        d = step.to_dict()
        assert d["description"] == "Test step"
        assert d["tool_module"] == "employees"
        assert d["tool_action"] == "create"
        assert d["method"] == "POST"
        assert d["path"] == "/employees"
        assert d["params"] == {"name": "John"}
        assert d["status"] == "pending"

    def test_step_status_mutation(self) -> None:
        step = _make_step()
        step.status = "executing"
        assert step.status == "executing"
        step.status = "done"
        assert step.status == "done"


# =========================================================================
# PaceSession Creation Tests
# =========================================================================


class TestPaceSessionCreation:
    """PaceSession creation with various trust levels."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_create_session_propose(self) -> None:
        session = _create_session(self.mgr, trust_level="propose")
        assert session.status == "preview"
        assert session.trust_level == "propose"
        assert session.confirmed_count == 0

    def test_create_session_always_propose(self) -> None:
        session = _create_session(self.mgr, trust_level="always_propose")
        assert session.status == "preview"
        assert session.trust_level == "always_propose"

    def test_create_session_double_confirm(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        assert session.status == "preview"
        assert session.trust_level == "double_confirm"
        assert session.requires_double_confirm is True

    def test_session_has_unique_id(self) -> None:
        s1 = _create_session(self.mgr)
        s2 = _create_session(self.mgr)
        assert s1.id != s2.id

    def test_session_has_created_at(self) -> None:
        session = _create_session(self.mgr)
        assert session.created_at != ""
        assert "T" in session.created_at  # ISO format

    def test_session_stores_user_id(self) -> None:
        session = _create_session(self.mgr, user_id="alice")
        assert session.user_id == "alice"

    def test_session_stores_intent(self) -> None:
        session = _create_session(self.mgr)
        assert session.intent_module == "employees"
        assert session.intent_action == "create"

    def test_session_stores_confirmation_message(self) -> None:
        session = _create_session(self.mgr)
        assert session.confirmation_message == "Create employee John?"

    def test_session_stores_steps(self) -> None:
        steps = [_make_step("Step 1"), _make_step("Step 2")]
        session = _create_session(self.mgr, steps=steps)
        assert len(session.steps) == 2

    def test_session_completed_at_initially_none(self) -> None:
        session = _create_session(self.mgr)
        assert session.completed_at is None

    def test_session_results_initially_empty(self) -> None:
        session = _create_session(self.mgr)
        assert session.results == []


# =========================================================================
# Session Retrieval Tests
# =========================================================================


class TestSessionRetrieval:
    """Session get/find operations."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_get_session_by_id(self) -> None:
        session = _create_session(self.mgr)
        retrieved = self.mgr.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_nonexistent_session(self) -> None:
        result = self.mgr.get_session("nonexistent-id")
        assert result is None

    def test_get_user_sessions(self) -> None:
        _create_session(self.mgr, user_id="alice")
        _create_session(self.mgr, user_id="alice")
        _create_session(self.mgr, user_id="bob")
        alice_sessions = self.mgr.get_user_sessions("alice")
        assert len(alice_sessions) == 2

    def test_get_user_sessions_with_status_filter(self) -> None:
        s1 = _create_session(self.mgr, user_id="alice")
        _create_session(self.mgr, user_id="alice")
        self.mgr.cancel_session(s1.id)
        preview_sessions = self.mgr.get_user_sessions("alice", status="preview")
        assert len(preview_sessions) == 1

    def test_get_user_sessions_empty(self) -> None:
        result = self.mgr.get_user_sessions("nobody")
        assert result == []


# =========================================================================
# Session Expiry Tests
# =========================================================================


class TestSessionExpiry:
    """Session TTL and expiry behavior."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_session_not_expired_immediately(self) -> None:
        session = _create_session(self.mgr)
        assert session.is_expired() is False

    def test_session_expires_after_ttl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = _create_session(self.mgr)
        # Fast-forward monotonic time past TTL
        original_ts = session._created_ts
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 1)
        assert session.is_expired() is True

    def test_expired_session_returns_none_from_get(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = _create_session(self.mgr)
        original_ts = session._created_ts
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 1)
        result = self.mgr.get_session(session.id)
        assert result is None

    def test_completed_sessions_dont_expire(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = _create_session(self.mgr)
        session.status = "done"
        original_ts = session._created_ts
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 100)
        assert session.is_expired() is False

    def test_failed_sessions_dont_expire(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = _create_session(self.mgr)
        session.status = "failed"
        original_ts = session._created_ts
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 100)
        assert session.is_expired() is False

    def test_cancelled_sessions_dont_expire(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = _create_session(self.mgr)
        session.status = "cancelled"
        original_ts = session._created_ts
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 100)
        assert session.is_expired() is False


# =========================================================================
# Session Cancellation Tests
# =========================================================================


class TestSessionCancellation:
    """Session cancellation behavior."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_cancel_preview_session(self) -> None:
        session = _create_session(self.mgr)
        result = self.mgr.cancel_session(session.id)
        assert result is True
        assert session.status == "cancelled"

    def test_cancel_sets_completed_at(self) -> None:
        session = _create_session(self.mgr)
        self.mgr.cancel_session(session.id)
        assert session.completed_at is not None

    def test_cancel_sets_step_status(self) -> None:
        session = _create_session(self.mgr, steps=[_make_step(), _make_step()])
        self.mgr.cancel_session(session.id)
        for step in session.steps:
            assert step.status == "cancelled"

    def test_cannot_cancel_executing_session(self) -> None:
        session = _create_session(self.mgr)
        session.status = "executing"
        result = self.mgr.cancel_session(session.id)
        assert result is False

    def test_cannot_cancel_done_session(self) -> None:
        session = _create_session(self.mgr)
        session.status = "done"
        result = self.mgr.cancel_session(session.id)
        assert result is False

    def test_cannot_cancel_nonexistent_session(self) -> None:
        result = self.mgr.cancel_session("nonexistent-id")
        assert result is False

    def test_cannot_cancel_already_cancelled_session(self) -> None:
        session = _create_session(self.mgr)
        self.mgr.cancel_session(session.id)
        result = self.mgr.cancel_session(session.id)
        assert result is False

    def test_only_pending_steps_cancelled(self) -> None:
        """Steps already marked done should not be overwritten to cancelled."""
        session = _create_session(self.mgr, steps=[_make_step(), _make_step()])
        session.steps[0].status = "done"
        self.mgr.cancel_session(session.id)
        assert session.steps[0].status == "done"
        assert session.steps[1].status == "cancelled"


# =========================================================================
# Double Confirmation Flow
# =========================================================================


class TestDoubleConfirmationFlow:
    """Double-confirm trust level requires two confirmations."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_first_confirm_transitions_to_awaiting(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        returned_session, ready = self.mgr.confirm_session(session.id)
        assert returned_session is not None
        assert returned_session.status == "awaiting_double_confirm"
        assert returned_session.confirmed_count == 1
        assert ready is False

    def test_second_confirm_makes_ready(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        self.mgr.confirm_session(session.id)  # first
        returned_session, ready = self.mgr.confirm_session(session.id)  # second
        assert returned_session is not None
        assert returned_session.confirmed_count == 2
        assert ready is True

    def test_requires_double_confirm_property(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        assert session.requires_double_confirm is True

    def test_non_double_confirm_session(self) -> None:
        session = _create_session(self.mgr, trust_level="propose")
        assert session.requires_double_confirm is False


# =========================================================================
# Single Confirmation Flow (propose, always_propose)
# =========================================================================


class TestSingleConfirmationFlow:
    """propose and always_propose require only one confirmation."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_propose_single_confirm(self) -> None:
        session = _create_session(self.mgr, trust_level="propose")
        returned_session, ready = self.mgr.confirm_session(session.id)
        assert returned_session is not None
        assert returned_session.confirmed_count == 1
        assert ready is True

    def test_always_propose_single_confirm(self) -> None:
        session = _create_session(self.mgr, trust_level="always_propose")
        returned_session, ready = self.mgr.confirm_session(session.id)
        assert returned_session is not None
        assert returned_session.confirmed_count == 1
        assert ready is True

    def test_confirm_nonexistent_session(self) -> None:
        returned_session, ready = self.mgr.confirm_session("nonexistent")
        assert returned_session is None
        assert ready is False

    def test_confirm_already_done_session(self) -> None:
        session = _create_session(self.mgr)
        session.status = "done"
        returned_session, ready = self.mgr.confirm_session(session.id)
        assert returned_session is not None
        assert ready is False

    def test_confirm_cancelled_session(self) -> None:
        session = _create_session(self.mgr)
        self.mgr.cancel_session(session.id)
        returned_session, ready = self.mgr.confirm_session(session.id)
        assert returned_session is not None
        assert ready is False


# =========================================================================
# LRU Eviction Tests
# =========================================================================


class TestLRUEviction:
    """LRU eviction when max sessions reached."""

    def test_eviction_at_capacity(self) -> None:
        mgr = PaceManager(max_sessions=3)
        s1 = _create_session(mgr, user_id="user1")
        s2 = _create_session(mgr, user_id="user2")
        s3 = _create_session(mgr, user_id="user3")
        s1_id = s1.id

        # Creating a 4th session should evict the oldest (s1)
        s4 = _create_session(mgr, user_id="user4")

        assert mgr.get_session(s1_id) is None  # evicted
        assert mgr.get_session(s2.id) is not None
        assert mgr.get_session(s3.id) is not None
        assert mgr.get_session(s4.id) is not None

    def test_eviction_keeps_newest(self) -> None:
        mgr = PaceManager(max_sessions=2)
        s1 = _create_session(mgr)
        s2 = _create_session(mgr)
        s3 = _create_session(mgr)

        assert mgr.get_session(s1.id) is None
        assert mgr.get_session(s2.id) is not None
        assert mgr.get_session(s3.id) is not None

    def test_default_max_sessions(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        assert mgr._max_sessions == _MAX_SESSIONS


# =========================================================================
# Undo Window Tests
# =========================================================================


class TestUndoWindow:
    """Undo window behavior after session completion."""

    def test_not_undoable_before_completion(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        session = _create_session(mgr)
        assert session.is_undoable() is False

    def test_undoable_immediately_after_completion(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        session = _create_session(mgr)
        session.status = "done"
        session._completed_ts = time.monotonic()
        assert session.is_undoable() is True

    def test_not_undoable_after_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        session = _create_session(mgr)
        session.status = "done"
        completed_ts = time.monotonic()
        session._completed_ts = completed_ts
        monkeypatch.setattr(time, "monotonic", lambda: completed_ts + _UNDO_WINDOW_SECONDS + 1)
        assert session.is_undoable() is False

    def test_undoable_within_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        session = _create_session(mgr)
        session.status = "done"
        completed_ts = time.monotonic()
        session._completed_ts = completed_ts
        # 5 seconds into the 8-second window
        monkeypatch.setattr(time, "monotonic", lambda: completed_ts + 5)
        assert session.is_undoable() is True

    def test_not_undoable_if_failed(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        session = _create_session(mgr)
        session.status = "failed"
        session._completed_ts = time.monotonic()
        assert session.is_undoable() is False

    def test_not_undoable_if_cancelled(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        session = _create_session(mgr)
        session.status = "cancelled"
        session._completed_ts = time.monotonic()
        assert session.is_undoable() is False

    def test_not_undoable_if_completed_ts_zero(self) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        session = _create_session(mgr)
        session.status = "done"
        assert session._completed_ts == 0.0
        assert session.is_undoable() is False


# =========================================================================
# Session Serialization (to_dict)
# =========================================================================


class TestSessionSerialization:
    """PaceSession.to_dict output validation."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_to_dict_has_required_keys(self) -> None:
        session = _create_session(self.mgr)
        d = session.to_dict()
        required_keys = {
            "id",
            "user_id",
            "intent_module",
            "intent_action",
            "confirmation_message",
            "steps",
            "trust_level",
            "status",
            "created_at",
            "completed_at",
            "results",
            "confirmed_count",
            "requires_double_confirm",
            "is_undoable",
        }
        assert required_keys.issubset(d.keys()), f"Missing keys: {required_keys - d.keys()}"

    def test_to_dict_trust_level(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        d = session.to_dict()
        assert d["trust_level"] == "double_confirm"

    def test_to_dict_confirmed_count(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        self.mgr.confirm_session(session.id)
        d = session.to_dict()
        assert d["confirmed_count"] == 1

    def test_to_dict_requires_double_confirm(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        d = session.to_dict()
        assert d["requires_double_confirm"] is True

    def test_to_dict_not_double_confirm(self) -> None:
        session = _create_session(self.mgr, trust_level="propose")
        d = session.to_dict()
        assert d["requires_double_confirm"] is False

    def test_to_dict_is_undoable(self) -> None:
        session = _create_session(self.mgr)
        d = session.to_dict()
        assert d["is_undoable"] is False  # not done yet

    def test_to_dict_steps_serialized(self) -> None:
        steps = [_make_step("S1"), _make_step("S2")]
        session = _create_session(self.mgr, steps=steps)
        d = session.to_dict()
        assert len(d["steps"]) == 2
        assert d["steps"][0]["description"] == "S1"
        assert d["steps"][1]["description"] == "S2"

    def test_to_dict_status_reflects_cancel(self) -> None:
        session = _create_session(self.mgr)
        self.mgr.cancel_session(session.id)
        d = session.to_dict()
        assert d["status"] == "cancelled"


# =========================================================================
# Expired Session Cleanup
# =========================================================================


class TestExpiredSessionCleanup:
    """_cleanup_expired removes expired sessions."""

    def test_cleanup_removes_expired(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        s1 = _create_session(mgr)
        original_ts = s1._created_ts

        # Fast-forward time past TTL
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 1)

        mgr._cleanup_expired()
        assert s1.id not in mgr._sessions

    def test_cleanup_keeps_active(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        s1 = _create_session(mgr)
        original_ts = s1._created_ts

        # Still within TTL
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS - 10)

        mgr._cleanup_expired()
        assert s1.id in mgr._sessions

    def test_cleanup_keeps_completed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mgr = PaceManager(cooldown_seconds=0)
        s1 = _create_session(mgr)
        s1.status = "done"
        original_ts = s1._created_ts

        # Far past TTL, but completed sessions don't expire
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 9999)

        mgr._cleanup_expired()
        assert s1.id in mgr._sessions


# =========================================================================
# Cannot Execute Without Sufficient Confirmations
# =========================================================================


class TestExecutionGuards:
    """Sessions must not be executable without proper confirmation."""

    def setup_method(self) -> None:
        self.mgr = PaceManager(cooldown_seconds=0)

    def test_double_confirm_needs_two_confirmations(self) -> None:
        """A double_confirm session with only 1 confirmation should not be ready."""
        session = _create_session(self.mgr, trust_level="double_confirm")
        _, ready = self.mgr.confirm_session(session.id)
        assert ready is False
        assert session.confirmed_count == 1

    def test_double_confirm_ready_after_two(self) -> None:
        session = _create_session(self.mgr, trust_level="double_confirm")
        self.mgr.confirm_session(session.id)
        _, ready = self.mgr.confirm_session(session.id)
        assert ready is True
        assert session.confirmed_count == 2

    def test_propose_ready_after_one(self) -> None:
        session = _create_session(self.mgr, trust_level="propose")
        _, ready = self.mgr.confirm_session(session.id)
        assert ready is True

    def test_expired_session_cannot_be_confirmed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = _create_session(self.mgr)
        original_ts = session._created_ts
        monkeypatch.setattr(time, "monotonic", lambda: original_ts + _SESSION_TTL_SECONDS + 1)
        returned_session, ready = self.mgr.confirm_session(session.id)
        assert returned_session is None
        assert ready is False
